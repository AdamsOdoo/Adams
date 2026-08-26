import ast
import inspect
import json
from unittest.mock import patch

import requests

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models import shopify_connector_api_client as client_module
from ..models.shopify_connector_api_client import (
    ERROR_API_VERSION,
    ERROR_AUTH,
    ERROR_DATA_SHAPE,
    ERROR_TEMPORARY,
    ERROR_THROTTLE,
    ERROR_UNKNOWN,
    ShopifyClientError,
)
from ..tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
    admin_graphql_endpoint,
)

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


def _public_api_guard_violations(source):
    tree = ast.parse(source)
    class_node = next(
        node for node in tree.body
        if isinstance(node, ast.ClassDef)
        and node.name == 'ShopifyConnectorApiClient'
    )
    methods = {
        node.name: node for node in class_node.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_')
    }
    violations = []
    if set(methods) != {
        'execute', 'execute_business', 'execute_business_read',
    }:
        violations.append(('public_surface', tuple(sorted(methods))))
    for name, required_calls in {
        'execute': {'_validate_graphql_operation'},
        'execute_business': {
            '_validate_graphql_operation', '_admit_mutation',
        },
        'execute_business_read': {
            '_validate_graphql_operation', '_admit_business_read',
        },
    }.items():
        method = methods.get(name)
        calls = {
            node.func.attr for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        } if method else set()
        if not required_calls <= calls:
            violations.append((name, tuple(sorted(required_calls - calls))))
    return violations


class FakeResponse:
    """Minimal stand-in for a `requests.Response` used by the `_send()`
    transport-injection seam -- no network call is ever made in this
    test module."""

    def __init__(
        self, status_code, json_body=None, headers=None, text=None,
        json_error=False,
    ):
        self.status_code = status_code
        # The API-version ruling (2026-07-26) makes `_normalize_response` fail
        # closed on a response with no `X-Shopify-API-Version` header, so the
        # default fixture states the version it is pretending to have been
        # served by. Tests that exercise the version gate itself pass
        # `headers` explicitly, including `{}` for the missing-header case.
        self.headers = {
            API_VERSION_RESPONSE_HEADER: SHOPIFY_API_VERSION,
        } if headers is None else headers
        self._json_body = json_body
        self._json_error = json_error
        if text is not None:
            self.text = text
        elif json_body is not None:
            self.text = json.dumps(json_body)
        else:
            self.text = ''

    def json(self):
        if self._json_error:
            raise ValueError('malformed JSON body')
        return self._json_body


def _success_body(domain='api-client-test.myshopify.com'):
    return {
        'data': {
            'shop': {
                'id': 'gid://shopify/Shop/1',
                'name': 'Test Shop',
                'myshopifyDomain': domain,
            },
            'currentAppInstallation': {
                'accessScopes': [{'handle': 'read_products'}],
            },
        },
    }


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestApiClient(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'API Client Test Store',
            'shop_domain': 'api-client-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN
        )
        cls.Client = cls.env['shopify.connector.api.client']

    def setUp(self):
        super().setUp()
        # CORE-R2 (review 4691182306 #1): `_admit_lifecycle` now captures its
        # snapshot in an OWNED `registry.cursor()` side transaction (store-row
        # FOR SHARE), exactly like business `_admit`. Under a plain TransactionCase
        # that side cursor is a genuinely independent connection that cannot see
        # this class's uncommitted fixture; entering registry test mode makes every
        # `registry.cursor()` reuse the single test connection as a TestCursor so
        # the fixture is visible cross-cursor -- the sanctioned mechanism
        # `TestBusinessAdmission` already uses for business `_admit`. This is a
        # packet-§4 seam-compat adaptation: no assertion changed. Genuine
        # cross-connection admission-vs-disconnect behaviour is proven by the
        # genuine lifecycle-race classes in test_disconnect_quiescence.py. The
        # execute()/_send_lifecycle direct tests open no side cursor, so test mode
        # is transparent to them.
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _execute_with(self, fake_send):
        with patch.object(type(self.Client), '_send', fake_send):
            return self.Client.execute(self.store, 'query { shop { id } }')

    def _raises_with(self, response):
        with self.assertRaises(ShopifyClientError) as catcher:
            self._execute_with(lambda self, store, body, r=response: r)
        return catcher.exception

    # 1. Success fixture -> execute() returns parsed data, no exception.
    def test_success_fixture_returns_parsed_data(self):
        response = FakeResponse(200, json_body=_success_body())
        result = self._execute_with(lambda self, store, body: response)
        # The served version is reported on every success and is always the
        # verified constant: there is no fall-forward result shape any more.
        self.assertEqual(result['served_version'], SHOPIFY_API_VERSION)
        self.assertNotIn('version_fallforward', result)
        self.assertEqual(result['data']['shop']['name'], 'Test Shop')
        self.assertEqual(
            result['data']['currentAppInstallation']['accessScopes'],
            [{'handle': 'read_products'}],
        )

    # 2. ACCESS_DENIED (200-OK GraphQL error).
    def test_access_denied_graphql_error(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Access denied',
                'extensions': {'code': 'ACCESS_DENIED'},
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertTrue(exc.credential_invalid)

    # 3. THROTTLED (fixture marked unofficial/unconfirmed shape).
    def test_throttled_graphql_error_unofficial_shape(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            # unofficial/unconfirmed shape -- Open question #1/#3,
            # credential-connection-api-client-planning.md.
            'errors': [{
                'message': 'Throttled',
                'extensions': {'code': 'THROTTLED'},
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_THROTTLE)
        self.assertFalse(exc.credential_invalid)

    # 4. MAX_COST_EXCEEDED (official sample shape) -> unknown_system_error.
    def test_max_cost_exceeded_maps_to_unknown(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Query cost exceeded',
                'extensions': {
                    'code': 'MAX_COST_EXCEEDED', 'cost': 1200, 'maxCost': 1000,
                },
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_UNKNOWN)

    def test_graphql_selection_mismatch_maps_to_existing_data_shape_class(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': (
                    "Field 'apiVersion' must have a selection of subfields."
                ),
                'extensions': {
                    'code': 'selectionMismatch',
                    'typeName': 'WebhookSubscription',
                    'fieldName': 'apiVersion',
                },
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_DATA_SHAPE)
        self.assertFalse(exc.credential_invalid)
        self.assertNotIn('shpat_', exc.reason)
        self.assertIn('HTTP 200', exc.technical_detail)

    # 5. INTERNAL_SERVER_ERROR + requestId -> requestId in technical_detail.
    def test_internal_server_error_includes_request_id(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Internal error',
                'extensions': {
                    'code': 'INTERNAL_SERVER_ERROR', 'requestId': 'req-abc-123',
                },
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_TEMPORARY)
        self.assertIn('req-abc-123', exc.technical_detail)

    # 6. HTTP 401 -> auth, credential_invalid True (unconfirmed HTTP shape).
    def test_http_401_maps_to_auth_credential_invalid(self):
        exc = self._raises_with(FakeResponse(401, text='Unauthorized'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertTrue(exc.credential_invalid)

    # 7. HTTP 402 -> auth, credential_invalid False, billing/payment reason.
    def test_http_402_frozen_shop(self):
        exc = self._raises_with(FakeResponse(402, text='Payment required'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('billing/payment', exc.reason)

    # 8. HTTP 423 -> auth, credential_invalid False, locked reason.
    def test_http_423_locked_shop(self):
        exc = self._raises_with(FakeResponse(423, text='Locked'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('locked', exc.reason.lower())

    # 9. HTTP 403 -> auth, credential_invalid False, fraudulent reason.
    def test_http_403_fraudulent_store(self):
        exc = self._raises_with(FakeResponse(403, text='Fraudulent store'))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('fraudulent', exc.reason.lower())

    # 10. SHOP_INACTIVE -> auth, credential_invalid False, inactive reason.
    def test_shop_inactive(self):
        exc = self._raises_with(FakeResponse(200, json_body={
            'errors': [{
                'message': 'Shop inactive',
                'extensions': {'code': 'SHOP_INACTIVE'},
            }],
        }))
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertFalse(exc.credential_invalid)
        self.assertIn('inactive', exc.reason.lower())

    # 11. HTTP 429 -> throttling.
    def test_http_429_throttled(self):
        exc = self._raises_with(FakeResponse(429, text='Too Many Requests'))
        self.assertEqual(exc.error_class, ERROR_THROTTLE)

    # 12. HTTP 500 -> temporary/network.
    def test_http_500_temporary(self):
        exc = self._raises_with(FakeResponse(500, text='Internal Server Error'))
        self.assertEqual(exc.error_class, ERROR_TEMPORARY)

    # 13. Timeout (simulated) -> temporary/network.
    def test_timeout_simulated(self):
        def raise_timeout(self, store, body):
            raise requests.exceptions.ConnectTimeout('simulated connect timeout')

        with self.assertRaises(ShopifyClientError) as catcher:
            self._execute_with(raise_timeout)
        self.assertEqual(catcher.exception.error_class, ERROR_TEMPORARY)

    # 14. Malformed JSON body -> unknown_system_error.
    def test_malformed_json_body(self):
        exc = self._raises_with(
            FakeResponse(200, text='not json', json_error=True)
        )
        self.assertEqual(exc.error_class, ERROR_UNKNOWN)

    # 15. X-Shopify-API-Version mismatch -> FAILS CLOSED (2026-07-26 ruling).
    #
    # This assertion is the inverse of what it was. The former
    # `test_version_fallforward_no_exception` proved that a response Shopify
    # served on a DIFFERENT API version was returned to the caller as a
    # success carrying a `version_fallforward` marker. Under the 2026-07-26
    # control-room ruling that is no longer acceptable: a mutation built
    # against 2026-07 semantics and executed against another version's
    # semantics must never be reported as applied, so the response is refused
    # before any caller sees it.
    def test_version_mismatch_fails_closed(self):
        response = FakeResponse(
            200, json_body=_success_body(),
            headers={API_VERSION_RESPONSE_HEADER: '2026-10'},
        )
        exc = self._raises_with(response)
        self.assertEqual(exc.error_class, ERROR_API_VERSION)
        # The served and expected versions may appear in the technical
        # detail; a token, a header value or a credential never may.
        self.assertIn('2026-10', exc.technical_detail)
        self.assertNotIn(DUMMY_TOKEN, exc.technical_detail)
        self.assertNotIn(DUMMY_TOKEN, str(exc))

    # 15b. A response with NO version header is the same uncertainty without
    # the evidence, and is refused for the same reason.
    def test_missing_version_header_fails_closed(self):
        exc = self._raises_with(
            FakeResponse(200, json_body=_success_body(), headers={})
        )
        self.assertEqual(exc.error_class, ERROR_API_VERSION)
        self.assertIn(SHOPIFY_API_VERSION, exc.technical_detail)
        self.assertNotIn(DUMMY_TOKEN, exc.technical_detail)

    # 15c. The endpoint is built from the centralized constant, so a store row
    # can never redirect a verified request at an unverified schema.
    def test_endpoint_uses_the_centralized_constant(self):
        self.assertEqual(
            admin_graphql_endpoint('example.myshopify.com'),
            'https://example.myshopify.com/admin/api/%s/graphql.json' % (
                SHOPIFY_API_VERSION,
            ),
        )
        captured = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            captured['url'] = url
            captured['headers'] = headers
            return FakeResponse(200, json_body=_success_body())

        with patch.object(client_module.requests, 'post', fake_post):
            self.Client.execute(self.store, 'query { shop { id } }')
        self.assertEqual(
            captured['url'],
            'https://%s/admin/api/%s/graphql.json' % (
                self.store.shop_domain, SHOPIFY_API_VERSION,
            ),
        )

    # 15d. A store whose recorded version disagrees with the connector
    # constant is refused BEFORE any request is sent.
    def test_store_version_disagreement_refuses_before_send(self):
        """Defence in depth, kept after TD-008 closed the ORM route.

        TD-008 makes a divergent `api_version` unreachable through the
        ORM: `_check_api_version_is_the_connector_constant` refuses it on
        create, write, `sudo()`, RPC and import alike. That is the primary
        fix, and it is what makes this state a HISTORIC row rather than a
        reachable one.

        The client's own pre-send check still matters and is still
        asserted, because a database upgraded from before that constraint
        can contain exactly such a row. Planted in SQL for the same reason
        `TestSec3HistoricRows` plants a company-less store: the ORM
        (correctly) refuses to create the shape being tested, and refusing
        to test it would mean the deeper guard is never exercised.
        """
        self.env.cr.execute(
            'UPDATE shopify_connector_store SET api_version = %s '
            'WHERE id = %s', ('2025-01', self.store.id),
        )
        self.store.invalidate_recordset()
        self.assertEqual(self.store.api_version, '2025-01')
        sent = []

        def fake_post(url, json=None, headers=None, timeout=None):
            sent.append(url)
            return FakeResponse(200, json_body=_success_body())

        with patch.object(client_module.requests, 'post', fake_post):
            with self.assertRaises(ShopifyClientError) as catcher:
                self.Client.execute(self.store, 'query { shop { id } }')
        self.assertEqual(catcher.exception.error_class, ERROR_API_VERSION)
        self.assertFalse(sent, 'no request may be sent on a version mismatch')

    # 16. The five permission-scope-auth reasons are pairwise distinct.
    def test_five_permission_scope_auth_reasons_pairwise_distinct(self):
        fixtures = {
            '402': FakeResponse(402, text='Payment required'),
            '423': FakeResponse(423, text='Locked'),
            '403': FakeResponse(403, text='Fraudulent'),
            'SHOP_INACTIVE': FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'SHOP_INACTIVE'},
                }],
            }),
            'ACCESS_DENIED': FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'ACCESS_DENIED'},
                }],
            }),
        }
        reasons = {label: self._raises_with(response).reason
                   for label, response in fixtures.items()}
        self.assertEqual(len(set(reasons.values())), len(reasons))

    # 17. Redaction: dummy token embedded in an error body/text.
    def test_redaction_of_dummy_token_in_error_body(self):
        leaking_token = 'shpat_DUMMYDUMMYDUMMY9999999999999999'
        exc = self._raises_with(
            FakeResponse(500, text='Internal error, token=%s' % leaking_token)
        )
        self.assertNotIn(leaking_token, str(exc))
        self.assertNotIn(leaking_token, exc.reason)
        self.assertNotIn(leaking_token, exc.technical_detail or '')

    # 18. Public surface and exact accepted Layer 2 mutation boundary.
    def test_read_only_guarantee(self):
        source = inspect.getsource(client_module)
        public_methods = {
            name for name, value in vars(
                client_module.ShopifyConnectorApiClient
            ).items()
            if callable(value) and not name.startswith('_')
        }
        # Business mutations and reads have separate guarded context managers.
        self.assertEqual(
            public_methods,
            {'execute', 'execute_business', 'execute_business_read'},
        )
        self.assertFalse(_public_api_guard_violations(source))

    def test_read_only_entry_points_refuse_mutation_before_transport(self):
        mutation = 'mutation Unsafe($id: ID!) { shop { id } }'
        ClientClass = type(self.Client)
        CredentialClass = type(
            self.env['shopify.connector.store.credential']
        )
        Lease = self.env['shopify.connector.call.lease']
        before = Lease.search_count([])
        with patch.object(
            CredentialClass, '_get_access_token',
            side_effect=AssertionError('credential read forbidden'),
        ) as credential, patch.object(
            ClientClass, '_send',
            side_effect=AssertionError('transport forbidden'),
        ) as transport:
            with self.assertRaises(UserError):
                self.Client.execute(self.store, mutation, {'id': 'x'})
            with self.assertRaises(UserError):
                self.Client._send_lifecycle(
                    self.store, mutation, DUMMY_TOKEN, {'id': 'x'},
                )
        credential.assert_not_called()
        transport.assert_not_called()
        self.assertEqual(Lease.search_count([]), before)

    def test_business_mutation_without_layer2_context_fails_before_admission(self):
        mutation = 'mutation Unsafe($id: ID!) { shop { id } }'
        ClientClass = type(self.Client)
        with patch.object(
            ClientClass, '_admit_mutation',
            side_effect=AssertionError('admission forbidden'),
        ) as admit, patch.object(
            ClientClass, '_send',
            side_effect=AssertionError('transport forbidden'),
        ) as transport:
            with self.assertRaises(UserError):
                with self.Client.execute_business(
                    False, self.store, mutation, {'id': 'x'},
                ):
                    pass
        admit.assert_not_called()
        transport.assert_not_called()

    def test_business_read_refuses_mutation_before_admission(self):
        mutation = 'mutation Unsafe($id: ID!) { shop { id } }'
        ClientClass = type(self.Client)
        with patch.object(
            ClientClass, '_admit_business_read',
            side_effect=AssertionError('read admission forbidden'),
        ) as admit:
            with self.assertRaises(UserError):
                with self.Client.execute_business_read(
                    False, self.store, mutation, {'id': 'x'}, purpose='inventory',
                ):
                    pass
        admit.assert_not_called()

    def test_business_read_releases_only_after_caller_body(self):
        ClientClass = type(self.Client)
        released = []

        def fake_send(self, store, body, token=None):
            return FakeResponse(200, json_body=_success_body())

        with patch.object(
            ClientClass, '_admit_business_read', return_value=('lease', 'token'),
        ), patch.object(ClientClass, '_send', fake_send), patch.object(
            ClientClass, '_release_lease', side_effect=released.append,
        ):
            with self.Client.execute_business_read(
                object(), self.store, 'query { shop { id } }',
                purpose='inventory',
            ) as result:
                self.assertEqual(released, [])
                self.assertIn('data', result)
            self.assertEqual(released, ['lease'])

    def test_public_api_guard_detector_rejects_extra_mutation_method(self):
        source = inspect.getsource(client_module)
        unsafe = source.replace(
            '    @api.model\n    def execute(self, store, query, variables=None):',
            "    @api.model\n"
            "    def unsafe_mutation(self, store):\n"
            "        return self._send(store, {'query': 'mutation Unsafe { x }'})\n"
            "\n"
            "    @api.model\n"
            "    def execute(self, store, query, variables=None):",
            1,
        )
        self.assertTrue(_public_api_guard_violations(unsafe))

    # 20 (CORE-R2 regression). execute() preserves the two-arg `_send` seam.
    # The token-snapshot change makes `_send(store, body, token=None)`; the
    # legacy execute() path must still call it as `_send(store, body)` (reading
    # the token itself), so the transport-seam tests that patch a two-arg
    # `_send` keep working and existing execute() callers stay operational.
    def test_execute_preserves_two_arg_send_seam(self):
        received = {}

        def fake_send(self, store, body, *extra):
            received['extra'] = extra
            return FakeResponse(200, json_body=_success_body())

        result = self._execute_with(fake_send)
        self.assertEqual(received['extra'], ())
        self.assertEqual(result['data']['shop']['name'], 'Test Shop')

    # 21 (CORE-R2 review 4690804619 #1). `_send_lifecycle` passes the EXACT
    # snapshot token to `_send` -- the transport re-reads no credential.
    def test_send_lifecycle_passes_snapshot_token_to_send(self):
        captured = {}

        def spy_send(self, store, body, token=None):
            captured['token'] = token
            return FakeResponse(200, json_body=_success_body())

        with patch.object(type(self.Client), '_send', spy_send):
            result = self.Client._send_lifecycle(
                self.store, 'query { shop { id } }', DUMMY_TOKEN,
            )
        self.assertEqual(captured['token'], DUMMY_TOKEN)
        self.assertEqual(result['data']['shop']['name'], 'Test Shop')

    # 22 (CORE-R2 review 4690804619 #1). `_admit_lifecycle` reads the token EXACTLY
    # once (the snapshot), captures the credential id/version + store generation +
    # the purpose matrix, and fails closed outside that matrix.
    def test_admit_lifecycle_snapshots_token_once(self):
        reads = []
        Cred = type(self.env['shopify.connector.store.credential'])

        def counting(self, store):
            reads.append(1)
            return DUMMY_TOKEN

        with patch.object(Cred, '_get_access_token', counting):
            snapshot = self.Client._admit_lifecycle(
                self.store, 'test_connection',
            )
        self.assertEqual(snapshot['token'], DUMMY_TOKEN)
        self.assertEqual(reads, [1])                 # one token read only
        self.assertTrue(snapshot['credential_id'])
        self.assertEqual(snapshot['generation'], self.store.connection_generation)
        self.assertEqual(
            snapshot['allowed_states'],
            ('setup_incomplete', 'connected', 'reconnect_needed'),
        )

    def test_admit_lifecycle_refuses_state_outside_matrix(self):
        self.store.write({'state': 'disconnected'})
        with self.assertRaises(UserError):
            self.Client._admit_lifecycle(self.store, 'test_connection')

    # 19. No credential leak across every fixture used above.
    def test_no_credential_leak_across_fixtures(self):
        fixtures = [
            FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'ACCESS_DENIED'},
                }],
            }),
            FakeResponse(401, text='Unauthorized %s' % DUMMY_TOKEN),
            FakeResponse(402, text='Payment required %s' % DUMMY_TOKEN),
            FakeResponse(500, text='Server error %s' % DUMMY_TOKEN),
        ]
        for response in fixtures:
            exc = self._raises_with(response)
            self.assertNotIn(DUMMY_TOKEN, str(exc))
            self.assertNotIn(DUMMY_TOKEN, exc.reason)
            self.assertNotIn(DUMMY_TOKEN, exc.technical_detail or '')
