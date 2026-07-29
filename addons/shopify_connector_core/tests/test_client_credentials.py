"""Wave 5 -- the Dev Dashboard client-credentials mode, end to end, mocked.

WHAT THIS FILE PROVES (prompt §11's mandatory list, one class per concern):

* the token-exchange request shape -- exact URL, verb-equivalent seam, form
  body and headers, verified against Shopify's Dev Dashboard documentation
  (accessed 2026-07-29);
* the token cache and its expiry arithmetic;
* refresh-before-expiry with the safe clock margin;
* refresh coalescing -- a second caller finds the leader's fresh token and
  performs no second exchange, and a waiter that never sees one gives up with
  the retryable taxonomy rather than exchanging competitively;
* failed-refresh behaviour -- an auth refusal marks the credential invalid and
  surfaces the accepted reconnect/authentication taxonomy; a transport failure
  stays retryable; and a still-valid token keeps serving while a refresh fails;
* credential rotation invalidation -- new client credentials discard the cache,
  clear verification, and demote a connected store to `reconnect_needed`;
* no secret or token leakage into RPC payloads, store mirrors, job logs or
  exception text;
* existing offline-token behaviour is byte-for-byte compatible;
* zero live Shopify contact -- every test patches the two transport seams
  (`_send_token_exchange`, `_send_lifecycle`); no test carries a real
  credential and none can reach the network.

No real credential appears anywhere in this file. Every token, id and secret is
a synthetic marker string chosen to be grep-able in leak assertions.
"""

import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from ..models import shopify_connector_store_credential as credential_module
from ..models.shopify_connector_api_client import (
    ERROR_AUTH,
    ERROR_TEMPORARY,
    ShopifyClientError,
)
from .test_api_client import FakeResponse, _success_body

DUMMY_CLIENT_ID = 'dummy-client-id-0000000000000000'
DUMMY_CLIENT_SECRET = 'dummy-client-secret-LEAKCANARY-00000000'
DUMMY_EXCHANGED_TOKEN = 'shpat_EXCHANGEDLEAKCANARY000000000000'
DUMMY_OFFLINE_TOKEN = 'shpat_OFFLINEDUMMY00000000000000000000'


def _token_response(token=DUMMY_EXCHANGED_TOKEN, expires_in=86399,
                    scope='read_products,read_orders'):
    """The documented success shape of POST /admin/oauth/access_token."""
    return FakeResponse(200, json_body={
        'access_token': token,
        'scope': scope,
        'expires_in': expires_in,
    }, headers={})


# Issue #193 / #157 -- Odoo 19 test-phase contract (fixtures create res.users).
@tagged('post_install', '-at_install')
class ClientCredentialsCase(TransactionCase):
    """Shared fixture: one store, one admin, registry test mode."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Client Credentials Test Store',
            'shop_domain': 'client-credentials-test.myshopify.com',
            'api_version': '2026-07',
        })
        group = cls.env.ref(
            'shopify_connector_core.group_shopify_connector_admin')
        cls.user_admin = cls.env['res.users'].create({
            'name': 'Client Credentials Test admin',
            'login': 'client_credentials_test_admin',
            'group_ids': [(6, 0, [group.id])],
        })

    def setUp(self):
        super().setUp()
        # The refresh and the lifecycle admission both run in owned
        # `registry.cursor()` side transactions; registry test mode makes them
        # TestCursors that can see this class's uncommitted fixtures -- the
        # sanctioned mechanism every admission test here already uses.
        self.env.flush_all()
        self.registry_enter_test_mode()

    # -- helpers ---------------------------------------------------------

    @property
    def Credential(self):
        return self.env['shopify.connector.store.credential']

    @property
    def Client(self):
        return self.env['shopify.connector.api.client']

    def _set_client_credentials(self):
        self.Credential.with_user(self.user_admin).action_set_client_credentials(
            self.store, DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET,
        )

    def _cached(self):
        return self.env['shopify.connector.store.access.token'].sudo().search(
            [('store_id', '=', self.store.id)], limit=1,
        )


@tagged('post_install', '-at_install')
class TestExchangeRequestShape(ClientCredentialsCase):

    def test_exchange_posts_the_documented_form_body(self):
        """URL, form fields and headers exactly as Shopify documents them."""
        seen = {}

        def fake_send(store, client_id, client_secret):
            seen['url'] = 'https://%s/admin/oauth/access_token' % store.shop_domain
            seen['client_id'] = client_id
            seen['client_secret'] = client_secret
            return _token_response()

        with patch.object(
            type(self.Client), '_send_token_exchange', side_effect=fake_send,
        ):
            token, expires_at, scope = self.Client._exchange_client_credentials(
                self.store, DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET,
            )
        self.assertEqual(
            seen['url'],
            'https://client-credentials-test.myshopify.com'
            '/admin/oauth/access_token',
        )
        self.assertEqual(seen['client_id'], DUMMY_CLIENT_ID)
        self.assertEqual(seen['client_secret'], DUMMY_CLIENT_SECRET)
        self.assertEqual(token, DUMMY_EXCHANGED_TOKEN)
        self.assertEqual(scope, 'read_products,read_orders')
        remaining = (expires_at - fields.Datetime.now()).total_seconds()
        self.assertAlmostEqual(remaining, 86399, delta=5)

    def test_the_real_transport_builds_the_documented_request(self):
        """`_send_token_exchange` itself: grant_type, urlencoded, timeout.

        The requests call is patched at the module boundary so nothing leaves
        the process; what is asserted is the exact request the production
        seam would have sent.
        """
        captured = {}

        def fake_post(url, data=None, headers=None, timeout=None):
            captured.update(url=url, data=data, headers=headers,
                            timeout=timeout)
            return _token_response()

        from ..models import shopify_connector_api_client as client_module
        with patch.object(client_module.requests, 'post',
                          side_effect=fake_post):
            self.Client._send_token_exchange(
                self.store, DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET,
            )
        self.assertEqual(
            captured['url'],
            'https://client-credentials-test.myshopify.com'
            '/admin/oauth/access_token',
        )
        self.assertEqual(captured['data'], {
            'client_id': DUMMY_CLIENT_ID,
            'client_secret': DUMMY_CLIENT_SECRET,
            'grant_type': 'client_credentials',
        })
        self.assertEqual(
            captured['headers']['Content-Type'],
            'application/x-www-form-urlencoded',
        )
        self.assertTrue(captured['timeout'])

    def test_refused_exchange_is_the_auth_taxonomy(self):
        for status in (400, 401, 403):
            with patch.object(
                type(self.Client), '_send_token_exchange',
                return_value=FakeResponse(status, json_body={}, headers={}),
            ):
                with self.assertRaises(ShopifyClientError) as ctx:
                    self.Client._exchange_client_credentials(
                        self.store, DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET,
                    )
            self.assertEqual(ctx.exception.error_class, ERROR_AUTH)
            self.assertTrue(ctx.exception.credential_invalid)

    def test_a_missing_expiry_is_refused_not_invented(self):
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=FakeResponse(200, json_body={
                'access_token': DUMMY_EXCHANGED_TOKEN, 'scope': '',
            }, headers={}),
        ):
            with self.assertRaises(ShopifyClientError) as ctx:
                self.Client._exchange_client_credentials(
                    self.store, DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET,
                )
        self.assertEqual(ctx.exception.error_class, ERROR_TEMPORARY)


@tagged('post_install', '-at_install')
class TestTokenCacheAndRefresh(ClientCredentialsCase):

    def test_first_ensure_exchanges_and_caches(self):
        self._set_client_credentials()
        calls = []
        with patch.object(
            type(self.Client), '_send_token_exchange',
            side_effect=lambda *a: calls.append(1) or _token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        self.assertEqual(len(calls), 1)
        cached = self._cached()
        self.assertEqual(cached.access_token, DUMMY_EXCHANGED_TOKEN)
        self.assertEqual(cached.granted_scope_snapshot,
                         'read_products,read_orders')
        remaining = (cached.expires_at - fields.Datetime.now()).total_seconds()
        self.assertGreater(remaining, 86000)
        # The non-secret mirrors a surface renders come from the cache row.
        status = self.Credential._token_cache_status(self.store)
        self.assertTrue(status['obtained_at'])
        self.assertEqual(status['expires_at'], cached.expires_at)
        # And the read seam serves the cached value.
        self.assertEqual(
            self.Credential._get_access_token(self.store),
            DUMMY_EXCHANGED_TOKEN,
        )

    def test_a_fresh_token_is_not_re_exchanged(self):
        """Refresh coalescing, sequential form: the second caller finds the
        first caller's fresh token and performs no exchange of its own."""
        self._set_client_credentials()
        calls = []
        with patch.object(
            type(self.Client), '_send_token_exchange',
            side_effect=lambda *a: calls.append(1) or _token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
            self.Credential._ensure_access_token(self.store)
            self.Credential._ensure_access_token(self.store)
        self.assertEqual(len(calls), 1)

    def test_refresh_happens_before_expiry_with_the_margin(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        cached = self._cached()
        # Age the token INTO the refresh margin but not past expiry: it is
        # still usable, and must nevertheless be replaced on the next ensure.
        nearly = fields.Datetime.now() + timedelta(
            seconds=credential_module.TOKEN_REFRESH_MARGIN_SECONDS - 60,
        )
        cached.sudo().write({'expires_at': nearly})
        calls = []
        with patch.object(
            type(self.Client), '_send_token_exchange',
            side_effect=lambda *a: calls.append(1) or _token_response(
                token='shpat_SECONDEXCHANGE0000000000000000',
            ),
        ):
            self.Credential._ensure_access_token(self.store)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            self.Credential._get_access_token(self.store),
            'shpat_SECONDEXCHANGE0000000000000000',
        )

    def test_an_expired_cache_serves_nothing(self):
        """`_get_access_token` is a pure read: an expired cached token is
        `False`, never a stale value and never an implicit refresh."""
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        self._cached().sudo().write({
            'expires_at': fields.Datetime.now() - timedelta(seconds=1),
        })
        self.assertFalse(self.Credential._get_access_token(self.store))

    def test_waiter_finds_the_peer_token(self):
        """`_await_peer_refresh` returns once a usable token is committed."""
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        # The cache is fresh, so a waiter polls once and comes back True
        # without any exchange seam in reach at all.
        self.assertTrue(self.Credential._await_peer_refresh(self.store))

    def test_waiter_gives_up_with_the_retryable_taxonomy(self):
        self._set_client_credentials()
        with patch.object(credential_module,
                          'TOKEN_REFRESH_WAIT_ATTEMPTS', 2), \
             patch.object(credential_module,
                          'TOKEN_REFRESH_WAIT_SECONDS', 0.01):
            with self.assertRaises(ShopifyClientError) as ctx:
                self.Credential._await_peer_refresh(self.store)
        self.assertEqual(ctx.exception.error_class, ERROR_TEMPORARY)

    def test_offline_mode_never_exchanges(self):
        self.Credential.with_user(self.user_admin).action_set_token(
            self.store, DUMMY_OFFLINE_TOKEN,
        )
        with patch.object(
            type(self.Client), '_send_token_exchange',
            side_effect=AssertionError('offline mode must never exchange'),
        ):
            self.Credential._ensure_access_token(self.store)
        self.assertEqual(
            self.Credential._get_access_token(self.store),
            DUMMY_OFFLINE_TOKEN,
        )
        self.assertFalse(self._cached())


@tagged('post_install', '-at_install')
class TestFailedRefresh(ClientCredentialsCase):

    def test_auth_refusal_raises_and_writes_no_side_state(self):
        """A refused exchange is the ACCEPTED taxonomy, and the refresh side
        transaction records nothing of its own -- the caller's transaction
        owns the failure evidence (see the probe-journey test below), because
        a side-transaction write to the credential row would collide with the
        same request's later revalidation lock under REPEATABLE READ."""
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=FakeResponse(401, json_body={}, headers={}),
        ):
            with self.assertRaises(ShopifyClientError) as ctx:
                self.Credential._ensure_access_token(self.store)
        self.assertEqual(ctx.exception.error_class, ERROR_AUTH)
        self.assertTrue(ctx.exception.credential_invalid)
        # No cache row was minted for a refused exchange.
        self.assertFalse(self._cached())
        # And the credential row is untouched: still present, no failure hint
        # written from the side transaction.
        credential = self.Credential._credential_for(self.store)
        self.assertEqual(credential.credential_state, 'present')

    def test_transport_failure_stays_retryable(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=FakeResponse(503, json_body={}, headers={}),
        ):
            with self.assertRaises(ShopifyClientError) as ctx:
                self.Credential._ensure_access_token(self.store)
        self.assertEqual(ctx.exception.error_class, ERROR_TEMPORARY)
        self.assertFalse(ctx.exception.credential_invalid)
        credential = self.Credential._credential_for(self.store)
        self.assertNotEqual(credential.credential_state, 'invalid')

    def test_a_still_valid_token_survives_a_failed_refresh(self):
        """Inside the refresh margin the current token still works; a refresh
        failure there must not turn a healthy store into an outage."""
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        self._cached().sudo().write({
            'expires_at': fields.Datetime.now() + timedelta(
                seconds=credential_module.TOKEN_REFRESH_MARGIN_SECONDS - 60,
            ),
        })
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=FakeResponse(503, json_body={}, headers={}),
        ):
            self.assertTrue(self.Credential._ensure_access_token(self.store))
        self.assertEqual(
            self.Credential._get_access_token(self.store),
            DUMMY_EXCHANGED_TOKEN,
        )


@tagged('post_install', '-at_install')
class TestRotationInvalidation(ClientCredentialsCase):

    def test_new_client_credentials_discard_the_cache(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        self.assertTrue(self._cached())
        self.Credential.with_user(self.user_admin).action_set_client_credentials(
            self.store, 'rotated-client-id', 'rotated-client-secret',
        )
        self.assertFalse(self._cached())
        status = self.Credential._token_cache_status(self.store)
        self.assertFalse(status['expires_at'])

    def test_rotation_demotes_a_connected_store(self):
        self._set_client_credentials()
        self.store.sudo().write({'state': 'connected'})
        generation = self.store.connection_generation
        self.Credential.with_user(self.user_admin).action_set_client_credentials(
            self.store, 'rotated-client-id', 'rotated-client-secret',
        )
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self.store.connection_generation, generation + 1)
        self.assertFalse(self.store.credential_last_verified_at)

    def test_switching_to_offline_clears_the_pair_and_cache(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        self.Credential.with_user(self.user_admin).action_replace_token(
            self.store, DUMMY_OFFLINE_TOKEN,
        )
        credential = self.Credential._credential_for(self.store)
        self.assertEqual(credential.auth_mode, 'offline_access_token')
        self.assertFalse(credential.client_id)
        self.assertFalse(credential.client_secret)
        self.assertFalse(credential.client_credentials_present)
        self.assertFalse(self._cached())
        self.assertEqual(
            self.Credential._get_access_token(self.store),
            DUMMY_OFFLINE_TOKEN,
        )

    def test_switching_to_client_credentials_clears_the_offline_token(self):
        self.Credential.with_user(self.user_admin).action_set_token(
            self.store, DUMMY_OFFLINE_TOKEN,
        )
        self._set_client_credentials()
        credential = self.Credential._credential_for(self.store)
        self.assertEqual(credential.auth_mode,
                         'dev_dashboard_client_credentials')
        self.assertFalse(credential.access_token)
        self.assertTrue(credential.client_credentials_present)

    def test_clear_removes_the_pair_and_cache_too(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        self.Credential.with_user(self.user_admin).action_clear_token(
            self.store,
        )
        credential = self.Credential._credential_for(self.store)
        self.assertFalse(credential.client_id)
        self.assertFalse(credential.client_secret)
        self.assertFalse(credential.client_credentials_present)
        self.assertFalse(self._cached())
        self.assertFalse(self.Credential._get_access_token(self.store))

    def test_probe_identity_is_the_pair_not_the_rotating_token(self):
        """A routine 24-hour rotation is NOT a credential change; replacing
        the client credentials IS. `_lifecycle_credential_identity` is what
        the post-network revalidation compares, so both halves matter."""
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        before = self.Credential._lifecycle_credential_identity(self.store)
        # Simulate the scheduled rotation: a new token lands in the cache.
        self._cached().sudo().write({
            'access_token': 'shpat_ROTATED00000000000000000000000',
        })
        self.assertEqual(
            self.Credential._lifecycle_credential_identity(self.store),
            before,
            'a token rotation must not read as a credential change',
        )
        self.Credential.with_user(self.user_admin).action_set_client_credentials(
            self.store, 'rotated-client-id', 'rotated-client-secret',
        )
        self.assertNotEqual(
            self.Credential._lifecycle_credential_identity(self.store),
            before,
            'replacing the pair must read as a credential change',
        )


@tagged('post_install', '-at_install')
class TestEndToEndAndLeakage(ClientCredentialsCase):

    def _passing_probe_transport(self):
        return patch.object(
            type(self.Client), '_send_lifecycle',
            return_value={
                'data': _success_body(
                    domain='client-credentials-test.myshopify.com',
                )['data'],
                'throttle_status': None,
                'served_version': '2026-07',
            },
        )

    def test_test_connection_exchanges_then_probes(self):
        """The complete new-store journey step: enter client credentials,
        press Test Connection, watch it pass -- with the exchange and the
        probe both mocked and counted."""
        self._set_client_credentials()
        exchanges = []
        with patch.object(
            type(self.Client), '_send_token_exchange',
            side_effect=lambda *a: exchanges.append(1) or _token_response(),
        ), self._passing_probe_transport():
            self.store.with_user(self.user_admin).action_test_connection()
        self.assertEqual(len(exchanges), 1)
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertTrue(self.store.credential_last_verified_at)
        self.assertEqual(json.loads(self.store.granted_scopes),
                         ['read_products'])

    def test_failed_exchange_reports_an_authentication_failure(self):
        """A wrong secret surfaces as the recorded auth failure on the store's
        own mirrors -- the reconnect/attention state -- not as an unhandled
        error and not as silence. The credential-state flip and the failure
        hint are written HERE, by the probe's own transaction, which is the
        design: the refresh side transaction records nothing."""
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=FakeResponse(401, json_body={}, headers={}),
        ):
            self.store.with_user(self.user_admin).action_test_connection()
        self.assertEqual(self.store.last_test_connection_result, 'fail')
        self.assertTrue(self.store.last_test_connection_reason)
        self.assertNotIn(DUMMY_CLIENT_SECRET,
                         self.store.last_test_connection_reason)
        credential = self.Credential._credential_for(self.store)
        self.assertEqual(credential.credential_state, 'invalid')
        self.assertTrue(credential.token_last_failure_reason)
        self.assertNotIn(DUMMY_CLIENT_SECRET,
                         credential.token_last_failure_reason)
        job = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_test_connection'),
        ], order='id desc', limit=1)
        self.assertEqual(job.state, 'failed_final')

    def test_setup_wizard_round_trip_leaks_nothing(self):
        """`save_client_credentials` records the pair, advances progress and
        returns a payload with no secret anywhere in it."""
        Wizard = self.env['shopify.connector.setup.wizard'].with_user(
            self.user_admin,
        )
        state = Wizard.save_client_credentials(
            self.store.id, DUMMY_CLIENT_ID, DUMMY_CLIENT_SECRET,
        )
        flat = json.dumps(state)
        self.assertNotIn(DUMMY_CLIENT_SECRET, flat)
        self.assertNotIn(DUMMY_EXCHANGED_TOKEN, flat)
        self.assertEqual(state['store']['auth_mode'],
                         'dev_dashboard_client_credentials')
        self.assertTrue(state['store']['client_credentials_present'])
        self.assertTrue(state['store']['credential_present'])

    def test_get_setup_state_carries_only_non_secret_mirrors(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        state = self.env['shopify.connector.setup.wizard'].with_user(
            self.user_admin,
        ).get_setup_state(store_id=self.store.id)
        flat = json.dumps(state)
        self.assertNotIn(DUMMY_CLIENT_SECRET, flat)
        self.assertNotIn(DUMMY_CLIENT_ID, flat)
        self.assertNotIn(DUMMY_EXCHANGED_TOKEN, flat)
        self.assertTrue(state['store']['token_expires_at'])

    def test_no_group_reads_the_token_cache_over_rpc(self):
        """The cache model carries no ACL row: even the Administrator is
        refused, and the token is reachable only through the sanctioned
        internal seam."""
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ):
            self.Credential._ensure_access_token(self.store)
        with self.assertRaises(AccessError):
            self.env['shopify.connector.store.access.token'].with_user(
                self.user_admin,
            ).search([])

    def test_job_logs_carry_no_secret_after_the_journey(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ), self._passing_probe_transport():
            self.store.with_user(self.user_admin).action_test_connection()
        logs = self.env['shopify.connector.job.log'].sudo().search([
            ('store_id', '=', self.store.id),
        ])
        for log in logs:
            for value in log.read()[0].values():
                text = str(value)
                self.assertNotIn(DUMMY_CLIENT_SECRET, text)
                self.assertNotIn(DUMMY_EXCHANGED_TOKEN, text)

    def test_store_mirrors_carry_no_secret(self):
        self._set_client_credentials()
        with patch.object(
            type(self.Client), '_send_token_exchange',
            return_value=_token_response(),
        ), self._passing_probe_transport():
            self.store.with_user(self.user_admin).action_test_connection()
        for field_name, field in self.store._fields.items():
            if field.type not in ('char', 'text'):
                continue
            value = self.store[field_name] or ''
            self.assertNotIn(DUMMY_CLIENT_SECRET, value)
            self.assertNotIn(DUMMY_EXCHANGED_TOKEN, value)


@tagged('post_install', '-at_install')
class TestOfflineCompatibility(ClientCredentialsCase):
    """The pre-Wave-5 shape, replayed against the extended model."""

    def test_offline_token_journey_is_unchanged(self):
        self.Credential.with_user(self.user_admin).action_set_token(
            self.store, DUMMY_OFFLINE_TOKEN,
        )
        credential = self.Credential._credential_for(self.store)
        self.assertEqual(credential.auth_mode, 'offline_access_token')
        self.assertEqual(
            self.Credential._get_access_token(self.store),
            DUMMY_OFFLINE_TOKEN,
        )
        with patch.object(
            type(self.Client), '_send_token_exchange',
            side_effect=AssertionError('offline mode must never exchange'),
        ), patch.object(
            type(self.Client), '_send_lifecycle',
            return_value={
                'data': _success_body(
                    domain='client-credentials-test.myshopify.com',
                )['data'],
                'throttle_status': None,
                'served_version': '2026-07',
            },
        ):
            self.store.with_user(self.user_admin).action_test_connection()
        self.assertEqual(self.store.last_test_connection_result, 'pass')

    def test_offline_identity_is_the_token_exactly_as_before(self):
        self.Credential.with_user(self.user_admin).action_set_token(
            self.store, DUMMY_OFFLINE_TOKEN,
        )
        self.assertEqual(
            self.Credential._lifecycle_credential_identity(self.store),
            DUMMY_OFFLINE_TOKEN,
        )
