"""CORE-R2 foundation-slice tests (AR-047, gate `4952145926`; correction review
`4680664964`).

These tests exercise the *admission half* of the CORE-R2 disconnect-quiescence
mechanism delivered in this slice: the committed `shopify.connector.call.lease`
model, the `execute_business` context-manager (with its `execute()`-parity
response/error contract and deterministic exception precedence), the `_admit`
store-row-locked admission, `_release_lease`, the single-token `_send` contract,
and the enqueue-time connection-epoch capture. They do NOT test the disconnect
controller, `disconnecting` lifecycle, or `timed_out`/`completed` finalization —
those are deliberately later CORE-R2 slices.

Two test styles are used, on purpose:

* `TransactionCase` classes drive the **real production** `execute_business`/
  `_admit`/`_send`/`_release_lease` path. Under Odoo test mode the side cursor
  that `_admit` opens (`registry.cursor()`) is a `TestCursor` sharing the single
  test connection, so these prove the admission *logic* (gate, ordering,
  token-once, API-parity, precedence, release) but cannot prove genuine
  cross-connection independence.
* `TestGenuineRealAdmission` (correction review `4680664964`, blocker 2) invokes
  the **real** `execute_business`/`_admit`/lease-ORM/credential/`_release_lease`
  path from genuine independent connections (`odoo.sql_db.db_connect`, never
  `registry.cursor()` for the worker/observer cursors). To let the production
  `_admit`'s own `registry.cursor()` side transaction commit to the real database
  — so an independent observer connection can see it — those tests patch the
  registry cursor factory to hand out real pooled cursors for the bounded test
  window. Raw SQL is used only for bounded observation and cleanup, never to
  create the lease under test. Fixtures are committed and torn down with durable,
  fail-loud, bounded cleanup and a fresh zero-residue verification.

No live Shopify call is made; the only transport seam replaced is `_send` (plus,
for the two exception-precedence tests, an injected `_release_lease` fault). No
lifecycle/state monkeypatch and no test-only timing hook is used.
"""

import ast
import importlib
import inspect
import queue
import re
import textwrap
import threading
import traceback
import uuid
from datetime import timedelta
from unittest.mock import patch

import psycopg2

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import UserError, ValidationError
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..models import shopify_connector_api_client as client_module
from ..models import shopify_connector_store as store_module
from ..models.shopify_connector_api_client import (
    ERROR_AUTH,
    ERROR_TEMPORARY,
    REASON_TOKEN_INVALID,
    ShopifyClientError,
    ShopifyQuiescedError,
)
from ..models.shopify_connector_job_dispatch import (
    DISCONNECT_QUIESCE_TIMEOUT,
    POLL_DELAY,
)
from .test_api_client import FakeResponse, _success_body

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'

# The "business" fields the lease table is allowed to carry (everything else is
# an ORM magic column). Deliberately no token/credential/query/payload column.
EXPECTED_LEASE_FIELDS = {
    'store_id', 'lease_key', 'job_id', 'worker_ref', 'admitted_at', 'expires_at',
}
FORBIDDEN_LEASE_SUBSTRINGS = (
    'token', 'credential', 'secret', 'query', 'variable', 'payload', 'body',
    'customer', 'product', 'password',
)
# ORM magic/log-access columns, excluded when checking the declared business
# shape (explicit set, not `field.automatic`, so the assertion is deterministic
# across Odoo point releases).
MAGIC_FIELDS = {
    'id', 'display_name', 'create_uid', 'create_date', 'write_uid',
    'write_date', '__last_update',
}


def _ok_send(captured):
    """A fake `_send` that records what it was handed and returns a real
    `FakeResponse` (200 OK) so `execute_business`'s `_normalize_response` runs
    exactly as it does for `execute()`.

    Replaces ONLY `_send`, makes no network call, and never reads credentials.
    """

    def fake_send(self, store, body, token=None):
        captured.setdefault('calls', []).append(1)
        captured['token'] = token
        captured['body'] = body
        return FakeResponse(200, json_body={'data': {'ok': True}})

    return fake_send


class TestCallLeaseModelSchema(TransactionCase):
    """The lease table shape + the client source-level guards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lease = cls.env['shopify.connector.call.lease']

    # 1. Lease model has no token/credential/query/payload field.
    def test_lease_has_no_secret_or_payload_field(self):
        field_names = set(self.Lease._fields)
        for fname in field_names:
            for bad in FORBIDDEN_LEASE_SUBSTRINGS:
                self.assertNotIn(
                    bad, fname.lower(),
                    'lease field %r must not reference %r' % (fname, bad),
                )
        # The declared (non-magic) columns are exactly the coordination minimum.
        business = set(self.Lease._fields) - MAGIC_FIELDS
        self.assertEqual(business, EXPECTED_LEASE_FIELDS)

    # 2. job_id is Integer, not Many2one; store_id is the only Many2one.
    def test_job_id_is_integer_not_m2o(self):
        self.assertEqual(self.Lease._fields['job_id'].type, 'integer')
        self.assertEqual(self.Lease._fields['store_id'].type, 'many2one')
        self.assertEqual(self.Lease._fields['store_id'].comodel_name,
                         'shopify.connector.store')

    # 3a. Lease key is unique (opacity is proven at admission, below).
    @mute_logger('odoo.sql_db')
    def test_lease_key_is_unique(self):
        store = self.env['shopify.connector.store'].create({
            'name': 'Lease Uniq Store',
            'shop_domain': 'lease-uniq-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
        })
        now = fields.Datetime.now()
        vals = {
            'store_id': store.id, 'lease_key': 'dup-key', 'job_id': 1,
            'admitted_at': now, 'expires_at': now,
        }
        self.Lease.create(vals)
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Lease.create(dict(vals))

    # 21. No advisory lock anywhere in the client; FOR SHARE is the primitive.
    def test_no_advisory_lock_in_client_source(self):
        source = inspect.getsource(client_module)
        self.assertNotIn('advisory', source.lower())
        self.assertNotIn('pg_advisory', source.lower())
        self.assertIn('FOR SHARE', source)

    # 22. No request/main cursor commit: every .commit()/.rollback() is on the
    # owned side cursor, never on self.env.cr / self._cr.
    def test_no_main_cursor_commit_in_client_source(self):
        source = inspect.getsource(client_module)
        self.assertNotIn('self.env.cr.commit', source)
        self.assertNotIn('self._cr.commit', source)
        self.assertNotIn('self.env.cr.rollback', source)
        committed = re.findall(r'(\w+)\.commit\(\)', source)
        self.assertTrue(committed, 'expected side-cursor commits to exist')
        self.assertTrue(
            all(name == 'side_cr' for name in committed),
            'only the owned side cursor may commit; found: %s' % committed,
        )

    # 20b. execute_business is the sole new public method; no mutation string.
    def test_public_surface_adds_only_execute_business(self):
        public = {
            name for name, value in vars(
                client_module.ShopifyConnectorApiClient
            ).items()
            if callable(value) and not name.startswith('_')
        }
        self.assertEqual(public, {'execute', 'execute_business'})
        self.assertIsNone(
            re.search(r'\bmutation\s*[\{\(]', inspect.getsource(client_module))
        )

    # API-parity source guards (review 4680664964, blocker 1): execute_business
    # normalizes like execute(), keeps the two-arg legacy seam, uses the explicit
    # captured token, and carries the RRequestException->temporary taxonomy.
    def test_execute_business_source_normalizes_and_preserves_seam(self):
        source = inspect.getsource(client_module)
        self.assertIn('_normalize_response(store, response)', source)
        self.assertIn('self._send(store, body)', source)          # legacy 2-arg
        self.assertIn('self._send(store, body, token)', source)   # business 3-arg
        self.assertIn('REASON_TEMPORARY', source)


class TestBusinessAdmission(TransactionCase):
    """The real `execute_business`/`_admit`/`_release_lease` admission path,
    including the `execute()`-parity contract and exception precedence."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Client = cls.env['shopify.connector.api.client']
        cls.Lease = cls.env['shopify.connector.call.lease']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Admission Store',
            'shop_domain': 'admission-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.env['shopify.connector.store.credential'].action_set_token(
            cls.store, DUMMY_TOKEN
        )
        # action_set_token() demotes a `connected` store to `reconnect_needed`
        # (a credential change invalidates the connected state); re-assert
        # `connected` so business enqueue + admission gates pass, mirroring the
        # canonical pattern in the existing dispatch/retry tests.
        cls.store.write({'state': 'connected'})
        cls.env.flush_all()

    def setUp(self):
        super().setUp()
        # CORE-R2 admission runs its gate/lease insert on a side transaction it
        # opens itself via `self.env.registry.cursor()` (durable, independent —
        # the invariant proven cross-connection by TestGenuineRealAdmission). A
        # plain TransactionCase does NOT patch the registry, so that call returns
        # a genuinely independent connection which cannot see this class's
        # *uncommitted* fixture store/job — `_admit`'s `SELECT ... FOR SHARE`
        # then finds `row is None` and fails closed with ShopifyQuiescedError.
        # `enter_registry_test_mode` (Odoo's sanctioned mechanism) makes every
        # `registry.cursor()` reuse the single test connection as a TestCursor,
        # so the fixture and the committed lease are visible cross-cursor — the
        # exact "TestCursor sharing the single test connection" this module's
        # docstring relies on to prove the admission *logic*. It changes no
        # production behaviour (real stores are committed) and is auto-left on
        # teardown; genuine cross-connection independence stays proven by
        # TestGenuineRealAdmission.
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _make_job(self, store=None):
        store = store or self.store
        return self.env['shopify.connector.job.enqueue'].enqueue(
            store, 'manual_sync', 'core_dispatch_selftest',
            payload_hash=uuid.uuid4().hex,
        )

    def _lease_count(self, store=None):
        store = store or self.store
        return self.Lease.search_count([('store_id', '=', store.id)])

    # --- Gate refusals (fail closed; no lease, no _send) ---------------

    # 4. Missing job is refused.
    def test_missing_job_refused(self):
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(False, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # 5. Wrong-store job is refused.
    def test_wrong_store_job_refused(self):
        other = self.env['shopify.connector.store'].create({
            'name': 'Other Store',
            'shop_domain': 'other-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        job_other = self._make_job(store=other)
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(job_other, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # 6. Disconnected store is refused.
    def test_disconnected_store_refused(self):
        job = self._make_job()
        self.store.write({'state': 'disconnected'})
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(job, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # 7. Generation mismatch is refused.
    def test_generation_mismatch_refused(self):
        job = self._make_job()  # captures the store's current epoch at enqueue
        # Bump the store epoch PAST the job's captured value to force a mismatch,
        # regardless of the fixture's base epoch (CORE-R2 review 4690639375 #3:
        # a connected `action_set_token` now bumps the epoch, so the setUpClass
        # fixture is no longer necessarily at 0 -- derive the mismatch from the
        # job's own captured generation rather than a hard-coded 0->1).
        self.store.write({
            'connection_generation': job.expected_connection_generation + 1,
        })
        self.env.flush_all()
        with self.assertRaises(ShopifyQuiescedError):
            with self.Client.execute_business(job, self.store, 'q'):
                pass
        self.assertEqual(self._lease_count(), 0)

    # --- execute()-parity contract (review 4680664964, blocker 1) ------

    # C1. Missing shop_domain/api_version -> same UserError as execute();
    # no lease, no _send (checked before admission).
    def test_missing_store_config_raises_user_error_before_admission(self):
        job = self._make_job()
        self.env.flush_all()

        class _StubStore:
            def __init__(self, shop_domain, api_version, sid):
                self.shop_domain = shop_domain
                self.api_version = api_version
                self.id = sid

        sent = []

        def spy_send(self, store, body, token=None):
            sent.append(1)
            return FakeResponse(200, json_body={'data': {}})

        with patch.object(type(self.Client), '_send', spy_send):
            for stub in (
                _StubStore(False, '2026-07', self.store.id),
                _StubStore('x.myshopify.com', False, self.store.id),
            ):
                with self.assertRaises(UserError):
                    with self.Client.execute_business(job, stub, 'q'):
                        pass
        self.assertEqual(sent, [])
        self.assertEqual(self._lease_count(), 0)

    # C2. Missing credential -> accepted ShopifyClientError taxonomy, before any
    # lease or _send, with exactly one credential read.
    def test_missing_credential_raises_shopify_client_error(self):
        nocred = self.env['shopify.connector.store'].create({
            'name': 'No Credential Store',
            'shop_domain': 'nocred-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        job = self._make_job(store=nocred)
        Cred = type(self.env['shopify.connector.store.credential'])
        reads = []
        sent = []

        def counting_empty(self, store):
            reads.append(1)
            return False

        def spy_send(self, store, body, token=None):
            sent.append(1)
            return FakeResponse(200, json_body={'data': {}})

        self.env.flush_all()
        with patch.object(Cred, '_get_access_token', counting_empty):
            with patch.object(type(self.Client), '_send', spy_send):
                with self.assertRaises(ShopifyClientError) as caught:
                    with self.Client.execute_business(job, nocred, 'q'):
                        pass
        exc = caught.exception
        self.assertEqual(exc.error_class, ERROR_AUTH)
        self.assertTrue(exc.credential_invalid)
        self.assertEqual(exc.reason, REASON_TOKEN_INVALID)
        self.assertEqual(sent, [])          # no _send
        self.assertEqual(reads, [1])        # exactly one credential read
        self.assertEqual(self._lease_count(nocred), 0)   # no lease

    # C3. Success yields the SAME normalized dict shape as execute(); lease held
    # through normalization and the caller body, released after.
    def test_success_yields_normalized_dict_like_execute(self):
        job = self._make_job()
        success = _success_body(domain=self.store.shop_domain)

        def ok_send(self, store, body, token=None):
            return FakeResponse(200, json_body=success)

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', ok_send):
            with self.Client.execute_business(job, self.store, 'q') as result:
                self.assertIn('data', result)
                self.assertIn('throttle_status', result)
                self.assertEqual(
                    result['data']['shop']['myshopifyDomain'],
                    self.store.shop_domain,
                )
                self.assertEqual(self._lease_count(), 1)   # held through body
        self.assertEqual(self._lease_count(), 0)           # released after

    # C4/#6. requests.RequestException -> ERROR_TEMPORARY; lease released (even
    # on a pre-yield failure); no token/header/body in the raised error.
    def test_request_exception_mapped_to_temporary_and_releases(self):
        job = self._make_job()

        def raising_send(self, store, body, token=None):
            raise client_module.requests.exceptions.ConnectTimeout(
                'net down token=%s' % DUMMY_TOKEN
            )

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', raising_send):
            with self.assertRaises(ShopifyClientError) as caught:
                with self.Client.execute_business(job, self.store, 'q'):
                    pass
        exc = caught.exception
        self.assertEqual(exc.error_class, ERROR_TEMPORARY)
        self.assertNotIn(DUMMY_TOKEN, str(exc))
        self.assertNotIn(DUMMY_TOKEN, exc.technical_detail or '')
        self.assertEqual(self._lease_count(), 0)           # released

    # C5. GraphQL/auth error passes through _normalize_response; accepted
    # ShopifyClientError taxonomy is preserved; lease released.
    def test_graphql_error_normalized_taxonomy_preserved_and_releases(self):
        job = self._make_job()

        def denied_send(self, store, body, token=None):
            return FakeResponse(200, json_body={
                'errors': [{
                    'message': 'x', 'extensions': {'code': 'ACCESS_DENIED'},
                }],
            })

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', denied_send):
            with self.assertRaises(ShopifyClientError) as caught:
                with self.Client.execute_business(job, self.store, 'q'):
                    pass
        self.assertEqual(caught.exception.error_class, ERROR_AUTH)
        self.assertTrue(caught.exception.credential_invalid)
        self.assertEqual(self._lease_count(), 0)

    # --- token-once / ordering / release -------------------------------

    # 8/16. Token read exactly once (at admission) and handed to _send.
    def test_token_read_once_and_passed_to_send(self):
        job = self._make_job()
        Cred = type(self.env['shopify.connector.store.credential'])
        reads = []
        captured = {}

        def counting_get(self, store):
            reads.append(1)
            return 'TOKEN_SNAPSHOT_XYZ'

        self.env.flush_all()
        with patch.object(Cred, '_get_access_token', counting_get):
            with patch.object(type(self.Client), '_send', _ok_send(captured)):
                with self.Client.execute_business(job, self.store, 'q'):
                    pass
        self.assertEqual(reads, [1])                        # exactly once
        self.assertEqual(captured['token'], 'TOKEN_SNAPSHOT_XYZ')

    # 17. _send does not reread credentials when given a token; reads when not.
    def test_send_reads_credential_only_when_token_absent(self):
        Client = self.Client
        Cred = type(self.env['shopify.connector.store.credential'])
        posted = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            posted['headers'] = headers
            return FakeResponse(200, json_body={'data': {}})

        reads = []

        def counting_get(self, store):
            reads.append(1)
            return 'TOKEN_FROM_CRED'

        with patch.object(client_module.requests, 'post', fake_post):
            with patch.object(Cred, '_get_access_token', counting_get):
                Client._send(self.store, {'query': 'q'}, token='SNAP')
                self.assertEqual(reads, [])                 # no reread
                self.assertEqual(
                    posted['headers']['X-Shopify-Access-Token'], 'SNAP'
                )
                Client._send(self.store, {'query': 'q'})
                self.assertEqual(reads, [1])                # legacy path reads
                self.assertEqual(
                    posted['headers']['X-Shopify-Access-Token'],
                    'TOKEN_FROM_CRED',
                )

    # 3b/9/10. Opaque key; lease committed before _send begins; visible in body.
    def test_lease_opaque_committed_before_send_and_visible_in_context(self):
        job = self._make_job()
        seen = {}

        def fake_send(self_, store, body, token=None):
            seen['count_at_send'] = self.Lease.search_count(
                [('store_id', '=', store.id)]
            )
            return FakeResponse(200, json_body={'data': {}})

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', fake_send):
            with self.Client.execute_business(job, self.store, 'q') as result:
                seen['count_in_body'] = self._lease_count()
                lease = self.Lease.search([('store_id', '=', self.store.id)])
                seen['key'] = lease.lease_key
                self.assertEqual(result['data'], {})
        self.assertEqual(seen['count_at_send'], 1)   # 9: committed before send
        self.assertEqual(seen['count_in_body'], 1)   # 10: visible in context
        # 3b: opaque key. It is a genuine random uuid4 (version nibble == 4,
        # RFC-4122 variant), so it encodes no store id, job id, or token and
        # carries no recoverable business identity. NOTE: a decimal id such as
        # `str(store.id)` (e.g. '15') can appear inside a random 32-char hex key
        # purely by chance, so a substring assertion on the id is mathematically
        # unsound and intermittently fails — the uuid4-version/variant check is
        # the correct, deterministic opacity proof. The token is long and random,
        # so its non-containment remains a valid (security-critical) guard.
        self.assertRegex(seen['key'], r'^[0-9a-f]{32}$')
        parsed_key = uuid.UUID(seen['key'])
        self.assertEqual(parsed_key.version, 4)
        self.assertEqual(parsed_key.variant, uuid.RFC_4122)
        self.assertNotIn(DUMMY_TOKEN, seen['key'])

    # 11. Normal exit releases the lease.
    def test_normal_exit_releases_lease(self):
        job = self._make_job()
        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with self.Client.execute_business(job, self.store, 'q'):
                self.assertEqual(self._lease_count(), 1)
        self.assertEqual(self._lease_count(), 0)

    # 7/12. Caller-body exception releases the lease and re-raises unchanged.
    def test_exception_exit_releases_and_reraises(self):
        job = self._make_job()

        class Boom(Exception):
            pass

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with self.assertRaises(Boom):
                with self.Client.execute_business(job, self.store, 'q'):
                    self.assertEqual(self._lease_count(), 1)
                    raise Boom()
        self.assertEqual(self._lease_count(), 0)

    # --- deterministic exception precedence (review 4680664964, blocker 3) ---

    # C8. Successful body + release failure -> the release error propagates.
    def test_release_failure_after_successful_body_propagates(self):
        job = self._make_job()

        class ReleaseBoom(Exception):
            pass

        def failing_release(self, lease_key):
            raise ReleaseBoom('release failed')

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with patch.object(type(self.Client), '_release_lease',
                              failing_release):
                with self.assertRaises(ReleaseBoom):
                    with self.Client.execute_business(job, self.store,
                                                      'q') as result:
                        self.assertEqual(result['data'], {'ok': True})

    # C9. Body error + release error -> body error stays primary; release error
    # is chained as its cause (classification not replaced).
    def test_body_error_with_release_failure_preserves_primary(self):
        job = self._make_job()

        class BodyBoom(Exception):
            pass

        class ReleaseBoom(Exception):
            pass

        def failing_release(self, lease_key):
            raise ReleaseBoom('release failed')

        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with patch.object(type(self.Client), '_release_lease',
                              failing_release):
                with self.assertRaises(BodyBoom) as caught:
                    with self.Client.execute_business(job, self.store, 'q'):
                        raise BodyBoom('body failed')
        self.assertIsInstance(caught.exception.__cause__, ReleaseBoom)

    # C10. Successful release uses a BARE re-raise: the SAME caller exception
    # object propagates with its ORIGINAL traceback (incl. the body raise site),
    # release runs exactly once, and there is no chained cause (review
    # `4681564744`).
    def test_body_exception_bare_reraise_preserves_traceback_and_releases_once(
            self):
        job = self._make_job()

        class Boom(Exception):
            pass

        raised = Boom('body failed')
        releases = []
        real_release = type(self.Client)._release_lease

        def counting_release(client_self, lease_key):
            releases.append(1)
            return real_release(client_self, lease_key)

        self.env.flush_all()
        captured_exc = None
        captured_tb_text = ''
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with patch.object(type(self.Client), '_release_lease',
                              counting_release):
                try:
                    with self.Client.execute_business(job, self.store, 'q'):
                        raise raised
                except Boom as exc:
                    # Capture the LIVE exception + traceback in the real handler.
                    # unittest's assertRaises stores the exception via
                    # `with_traceback(None)`, which would strip __traceback__ and
                    # make the "body raise site kept" assertion vacuous (it always
                    # sees ''). Capturing here proves the bare re-raise preserved
                    # the SAME object AND its ORIGINAL traceback (incl. the body
                    # raise site) — a stronger check than the assertRaises form.
                    captured_exc = exc
                    captured_tb_text = ''.join(
                        traceback.format_tb(exc.__traceback__))
        self.assertIsNotNone(captured_exc, 'Boom did not propagate')
        self.assertIs(captured_exc, raised)               # same object/identity
        self.assertIsNone(captured_exc.__cause__)         # release ok -> no chain
        self.assertEqual(releases, [1])                   # released exactly once
        self.assertIn(                                    # body raise site kept
            'test_body_exception_bare_reraise', captured_tb_text)
        self.assertEqual(self._lease_count(), 0)          # lease released

    # 18. Token never appears in any lease field.
    def test_token_never_appears_in_lease_rows(self):
        job = self._make_job()
        captured = {}
        self.env.flush_all()
        with patch.object(type(self.Client), '_send', _ok_send(captured)):
            with self.Client.execute_business(job, self.store, 'q'):
                leases = self.Lease.search([('store_id', '=', self.store.id)])
                self.assertEqual(len(leases), 1)
                for lease in leases:
                    for fname, field in lease._fields.items():
                        if field.type in ('char', 'text'):
                            value = lease[fname]
                            if value:
                                self.assertNotIn(DUMMY_TOKEN, value)


@tagged('post_install', '-at_install')
class TestGenuineRealAdmission(TransactionCase):
    """Genuine independent-connection tests of the REAL execute_business/_admit
    path (correction review `4680664964`, blocker 2).

    Each worker owns a `db_connect` main cursor + Environment created AFTER the
    fixtures commit (so, under Odoo's REPEATABLE READ snapshot, it sees them).
    `execute_business`/`_admit`/the lease ORM/`_get_access_token`/`_release_lease`
    are the REAL production code. The production `_admit` opens its own
    `registry.cursor()` side transaction — the mechanism under test — which is
    made genuinely independent (real pooled cursor, real commit, observable
    cross-connection) by patching the registry cursor factory for the bounded
    test window. Raw SQL is used only to OBSERVE committed leases and to clean up;
    it never creates the lease under test. The full two-server production-path
    proof (packet T-19) remains a deferred Odoo.sh runtime item (SRR-09 / RR-4).
    """

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    BOUND_SECONDS = 20

    # --- genuine-connection helpers ------------------------------------

    def _open_bounded(self, dbname):
        """Open a genuine pooled cursor and apply BOTH transaction-local
        PostgreSQL limits (statement_timeout + lock_timeout) via parameterized
        `set_config(..., true)`. If the bound setup fails, close the cursor and
        re-raise; return only after a successful setup — so no genuine worker or
        production side cursor is ever left unbounded (review `4681564744`)."""
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _real_registry_cursor(self, dbname):
        """A registry.cursor() replacement handing out **bounded** real pooled
        cursors, so every production `_admit`/`_release_lease` side transaction is
        time-bounded. Accepts/ignores any registry.cursor() args (e.g.
        readonly=)."""
        return lambda *args, **kwargs: self._open_bounded(dbname)

    def _sanitize(self, exc, phase):
        """A type-only, non-sensitive finding for a worker-thread failure.

        Records ONLY the fixed `phase`, the exception TYPE NAME, and (when it is a
        connector error) the safe fixed `error_class` enum — never `str`/`repr` of
        the exception, SQL, paths, credentials, payloads, or tokens.
        """
        error_class = getattr(exc, 'error_class', None)
        return {
            'phase': phase,
            'type': type(exc).__name__,
            'error_class': error_class if isinstance(error_class, str) else None,
        }

    def _safe_worker_teardown(self, wcr, diagnostics):
        """Roll back + close a worker cursor, surfacing (never swallowing) each
        failure as a SEPARATE sanitized finding so one cannot hide the other."""
        if wcr is None:
            return
        try:
            wcr.rollback()
        except BaseException as exc:
            diagnostics.put(self._sanitize(exc, 'rollback'))
        try:
            wcr.close()
        except BaseException as exc:
            diagnostics.put(self._sanitize(exc, 'cursor_close'))

    def _drain(self, diagnostics):
        """Collect all sanitized findings from the thread-safe queue."""
        findings = []
        while True:
            try:
                findings.append(diagnostics.get_nowait())
            except queue.Empty:
                break
        return findings

    def _assert_workers_dead(self, threads):
        """Fail loudly (fixed, non-sensitive message) if any worker is alive."""
        alive = sum(1 for t in threads if t is not None and t.is_alive())
        self.assertEqual(
            alive, 0, 'worker thread still alive at the cleanup boundary')

    def _commit_fixtures(self, dbname, n_jobs):
        """On an independent (bounded) connection, create+commit a connected
        store, its credential, and `n_jobs` matching business jobs."""
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Real Admission Store',
                'shop_domain': 'genuine-real-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN
            )
            # action_set_token() demotes `connected` -> `reconnect_needed`;
            # re-assert `connected` before enqueue/admission (see setUpClass).
            store.write({'state': 'connected'})
            job_ids = []
            for _ in range(n_jobs):
                job = env['shopify.connector.job.enqueue'].enqueue(
                    store, 'manual_sync', 'core_dispatch_selftest',
                    payload_hash=uuid.uuid4().hex,
                )
                job_ids.append(job.id)
            store_id = store.id
            setup.commit()
            return store_id, job_ids
        finally:
            setup.close()

    def _committed_lease_rows(self, dbname, store_id):
        """Observe committed leases from a fresh, bounded independent connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT lease_key, job_id FROM shopify_connector_call_lease "
                "WHERE store_id = %s ORDER BY lease_key", (store_id,))
            rows = obs.fetchall()
            obs.rollback()
            return rows
        finally:
            obs.close()

    def _cleanup(self, dbname, store_id, job_ids):
        """Durable, bounded, fail-loud teardown + fresh zero-residue check.

        Deletes job logs BEFORE jobs (FK `ondelete='restrict'`), then leases,
        jobs, credential, store. DELETEs are not swallowed → fail-loud."""
        if store_id is None:
            return
        cr = self._open_bounded(dbname)
        try:
            if job_ids:
                cr.execute(
                    "DELETE FROM shopify_connector_job_log "
                    "WHERE job_id = ANY(%s)", (list(job_ids),))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            if job_ids:
                cr.execute(
                    "DELETE FROM shopify_connector_job WHERE id = ANY(%s)",
                    (list(job_ids),))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        self._assert_zero_residue(dbname, store_id, job_ids)

    def _assert_zero_residue(self, dbname, store_id, job_ids):
        """Fresh, bounded verifier: zero leases, stores, credentials, jobs, AND
        job logs for the synthetic job ids. Uses unittest assertions with fixed,
        non-sensitive messages; always closes the verifier cursor."""
        v = self._open_bounded(dbname)
        try:
            v.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            self.assertEqual(v.fetchone()[0], 0, 'lease residue after cleanup')
            v.execute(
                "SELECT count(*) FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            self.assertEqual(v.fetchone()[0], 0, 'store residue after cleanup')
            v.execute(
                "SELECT count(*) FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            self.assertEqual(
                v.fetchone()[0], 0, 'credential residue after cleanup')
            if job_ids:
                v.execute(
                    "SELECT count(*) FROM shopify_connector_job "
                    "WHERE id = ANY(%s)", (list(job_ids),))
                self.assertEqual(v.fetchone()[0], 0, 'job residue after cleanup')
                v.execute(
                    "SELECT count(*) FROM shopify_connector_job_log "
                    "WHERE job_id = ANY(%s)", (list(job_ids),))
                self.assertEqual(
                    v.fetchone()[0], 0, 'job-log residue after cleanup')
            v.rollback()
        finally:
            v.close()

    # B. Real single admission: lease committed before _send, visible in the
    # context, and released on exit — all observed cross-connection.
    def test_real_admission_visible_before_send_and_released(self):
        dbname = self.env.cr.dbname
        store_id = None
        job_ids = []
        worker_cr = None
        try:
            store_id, job_ids = self._commit_fixtures(dbname, n_jobs=1)
            worker_cr = self._open_bounded(dbname)
            worker_env = api.Environment(worker_cr, SUPERUSER_ID, {})
            store = worker_env['shopify.connector.store'].browse(store_id)
            job = worker_env['shopify.connector.job'].browse(job_ids[0])
            Client = worker_env['shopify.connector.api.client']
            observed = {}

            # `client_self` is the api-client recordset bound by `self._send(...)`;
            # the test instance's `self` (for the observer helper) is captured by
            # closure.
            def observing_send(client_self, store_arg, body, token=None):
                observed['token'] = token
                observed['during_send'] = self._committed_lease_rows(
                    dbname, store_id)
                return FakeResponse(200, json_body={'data': {'ok': True}})

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', observing_send):
                    with Client.execute_business(
                            job, store, 'query { shop { id } }') as result:
                        observed['in_body'] = self._committed_lease_rows(
                            dbname, store_id)
                        observed['result'] = result
            observed['after'] = self._committed_lease_rows(dbname, store_id)

            self.assertEqual(len(observed['during_send']), 1)   # committed pre-send
            key, jid = observed['during_send'][0]
            self.assertEqual(jid, job_ids[0])
            self.assertRegex(key, r'^[0-9a-f]{32}$')            # opaque
            self.assertEqual(observed['token'], DUMMY_TOKEN)    # real snapshot
            self.assertEqual(len(observed['in_body']), 1)       # visible in ctx
            self.assertEqual(observed['result']['data'], {'ok': True})  # normalized
            self.assertEqual(len(observed['after']), 0)         # released on exit
        finally:
            if worker_cr is not None:
                worker_cr.rollback()
                worker_cr.close()
            self._cleanup(dbname, store_id, job_ids)

    # C. Real caller-rollback independence: the committed lease survives the
    # worker's own main-transaction rollback, then releases on context exit.
    def test_real_admission_survives_caller_rollback(self):
        dbname = self.env.cr.dbname
        store_id = None
        job_ids = []
        worker_cr = None
        try:
            store_id, job_ids = self._commit_fixtures(dbname, n_jobs=1)
            worker_cr = self._open_bounded(dbname)
            worker_env = api.Environment(worker_cr, SUPERUSER_ID, {})
            store = worker_env['shopify.connector.store'].browse(store_id)
            job = worker_env['shopify.connector.job'].browse(job_ids[0])
            Client = worker_env['shopify.connector.api.client']
            observed = {}

            def ok_send(client_self, store_arg, body, token=None):
                return FakeResponse(200, json_body={'data': {'ok': True}})

            with patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', ok_send):
                    with Client.execute_business(
                            job, store, 'query { shop { id } }'):
                        # the caller's OWN main transaction rolls back mid-context
                        worker_cr.rollback()
                        observed['after_rollback'] = self._committed_lease_rows(
                            dbname, store_id)
            observed['after_exit'] = self._committed_lease_rows(dbname, store_id)

            self.assertEqual(len(observed['after_rollback']), 1)  # independent
            self.assertEqual(observed['after_rollback'][0][1], job_ids[0])
            self.assertEqual(len(observed['after_exit']), 0)      # released
        finally:
            if worker_cr is not None:
                worker_cr.rollback()
                worker_cr.close()
            self._cleanup(dbname, store_id, job_ids)

    # D. Two REAL concurrent admissions on one store: both enter without
    # blocking, both leases coexist with distinct keys and correct job ids, both
    # release.
    def test_two_real_concurrent_admissions_commit_distinct_leases(self):
        dbname = self.env.cr.dbname
        store_id = None
        job_ids = []
        release_gate = threading.Event()
        diagnostics = queue.Queue()      # thread-safe, sanitized worker findings
        t1 = t2 = None
        try:
            store_id, job_ids = self._commit_fixtures(dbname, n_jobs=2)
            both_admitted = threading.Semaphore(0)

            def blocking_send(client_self, store_arg, body, token=None):
                # this worker's _admit has already committed its lease
                both_admitted.release()
                if not release_gate.wait(timeout=self.BOUND_SECONDS):
                    raise AssertionError('release_gate not set within bound')
                return FakeResponse(200, json_body={'data': {'ok': True}})

            def worker(job_id):
                wcr = None
                try:
                    threading.current_thread().dbname = dbname
                    wcr = self._open_bounded(dbname)
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    store = wenv['shopify.connector.store'].browse(store_id)
                    job = wenv['shopify.connector.job'].browse(job_id)
                    client = wenv['shopify.connector.api.client']
                    with client.execute_business(
                            job, store, 'query { shop { id } }'):
                        pass
                except BaseException as exc:     # fail loud, sanitized (type-only)
                    diagnostics.put(self._sanitize(exc, 'worker_body'))
                finally:
                    self._safe_worker_teardown(wcr, diagnostics)

            Client = self.env['shopify.connector.api.client']
            got1 = got2 = False
            rows = None
            # DEADLOCK FIX (pre-existing, framework-level). Odoo's ThreadedServer
            # holds the reentrant `Registry._lock` for the ENTIRE preload /
            # post_install phase (service/server.py `run`: `with Registry._lock:
            # ... preload_registries()`, which runs this suite). A spawned worker's
            # `api.Environment(wcr, ...)` calls `Registry(cr.dbname)` ->
            # `Registry.__new__` -> `with cls._lock:`, which blocks forever on that
            # main-thread-held lock (a different thread cannot acquire it). The
            # single-threaded genuine tests above avoid this only because they build
            # the Environment in the MAIN thread, reentrantly reacquiring the lock it
            # already owns. Decouple the worker threads with a fresh registry lock
            # for the bounded window: the registry is fully built and stable here
            # (workers only do a cached read-only `registries[db_name]` lookup, never
            # a rebuild), so this preserves real mutual exclusion among the test
            # threads and weakens nothing — it is the same lock decoupling Odoo's own
            # `_registry_test_mode_patches` performs. Without it the REAL admission
            # code under test never even runs (workers die at Environment creation).
            with patch.object(type(self.registry), '_lock', threading.RLock()), \
                 patch.object(self.registry, 'cursor',
                              self._real_registry_cursor(dbname)):
                with patch.object(type(Client), '_send', blocking_send):
                    t1 = threading.Thread(
                        target=worker, args=(job_ids[0],), daemon=True)
                    t2 = threading.Thread(
                        target=worker, args=(job_ids[1],), daemon=True)
                    t1.start()
                    t2.start()
                    try:
                        got1 = both_admitted.acquire(timeout=self.BOUND_SECONDS)
                        got2 = both_admitted.acquire(timeout=self.BOUND_SECONDS)
                        if got1 and got2:
                            # both leases coexist right now (workers parked at seam)
                            rows = self._committed_lease_rows(dbname, store_id)
                    finally:
                        # unblock, JOIN, and PROVE both dead BEFORE the patch is
                        # restored — a live worker must never run under the
                        # restored (shared test-cursor) registry factory.
                        release_gate.set()
                        t1.join(timeout=self.BOUND_SECONDS)
                        t2.join(timeout=self.BOUND_SECONDS)
                        self._assert_workers_dead((t1, t2))
            after = self._committed_lease_rows(dbname, store_id)

            # Sanitized worker findings first (surfaces any worker error as
            # type-only evidence), then the overlap/lease assertions.
            findings = self._drain(diagnostics)
            self.assertEqual(
                findings, [], 'sanitized worker findings: %s' % findings)
            self.assertTrue(
                got1 and got2, 'both real admissions did not overlap within bound')
            self.assertIsNotNone(rows, 'no coexisting-lease snapshot captured')
            self.assertEqual(len(rows), 2)                       # both committed
            self.assertEqual(len({r[0] for r in rows}), 2)       # distinct keys
            self.assertEqual({r[1] for r in rows}, set(job_ids))  # correct jobs
            self.assertEqual(len(after), 0)                      # both released
        finally:
            # repeat the termination guarantee after final joins, THEN clean up —
            # cleanup must never begin while a worker may still be live.
            release_gate.set()
            for t in (t1, t2):
                if t is not None:
                    t.join(timeout=self.BOUND_SECONDS)
            self._assert_workers_dead((t1, t2))
            self._cleanup(dbname, store_id, job_ids)

    # --- focused hardening tests (review 4681564744) -------------------

    # H1/H2. Every genuine cursor (worker main + production side, via the factory)
    # gets both transaction-local timeouts.
    def test_open_bounded_applies_both_timeouts(self):
        dbname = self.env.cr.dbname
        cr = self._open_bounded(dbname)
        try:
            cr.execute("SELECT current_setting('statement_timeout'), "
                       "current_setting('lock_timeout')")
            statement_timeout, lock_timeout = cr.fetchone()
            self.assertNotEqual(statement_timeout, '0')   # applied (non-default)
            self.assertNotEqual(lock_timeout, '0')        # applied (non-default)
            cr.rollback()
        finally:
            cr.close()
        # The patched registry factory routes through the same bounded helper.
        factory = self._real_registry_cursor(dbname)
        side = factory()
        try:
            side.execute("SELECT current_setting('statement_timeout'), "
                         "current_setting('lock_timeout')")
            st2, lt2 = side.fetchone()
            self.assertNotEqual(st2, '0')
            self.assertNotEqual(lt2, '0')
            side.rollback()
        finally:
            side.close()

    # H3. A failure while configuring a cursor closes that cursor.
    def test_open_bounded_closes_cursor_on_setup_failure(self):
        closed = []

        class _BoomCursor:
            def execute(self, *args, **kwargs):
                raise RuntimeError('boom during timeout setup')

            def close(self):
                closed.append(True)

        class _Conn:
            def cursor(self, *args, **kwargs):
                return _BoomCursor()

        mod = importlib.import_module(type(self).__module__)
        with patch.object(mod, 'db_connect', lambda *a, **k: _Conn()):
            with self.assertRaises(RuntimeError):
                self._open_bounded('anydb')
        self.assertEqual(closed, [True])   # the cursor was closed on failure

    # H4/H5. Worker rollback AND close failures both reach the parent as
    # SEPARATE, type-only sanitized findings — no raw text/SQL/paths/tokens.
    def test_worker_teardown_surfaces_sanitized_rollback_and_close(self):
        findings_q = queue.Queue()

        class _BadCursor:
            def rollback(self):
                raise RuntimeError('rollback boom /var/lib shpat_SECRET SELECT 1')

            def close(self):
                raise RuntimeError('close boom /etc token=shpat_SECRET DELETE')

        self._safe_worker_teardown(_BadCursor(), findings_q)
        findings = self._drain(findings_q)
        self.assertEqual({f['phase'] for f in findings},
                         {'rollback', 'cursor_close'})   # both, separately
        for finding in findings:
            self.assertEqual(finding['type'], 'RuntimeError')
            self.assertIsNone(finding['error_class'])
            blob = repr(finding)
            for leak in ('shpat_', 'SECRET', 'SELECT', 'DELETE', '/var', '/etc',
                         'boom', 'token'):
                self.assertNotIn(leak, blob)

    # H5b. _sanitize is strictly type-only, including for a connector error.
    def test_sanitize_is_type_only(self):
        exc = ShopifyClientError(
            error_class=ERROR_TEMPORARY,
            reason='secret shpat_LEAK', technical_detail='SELECT * secret /path')
        finding = self._sanitize(exc, 'worker_body')
        self.assertEqual(finding['phase'], 'worker_body')
        self.assertEqual(finding['type'], 'ShopifyClientError')
        self.assertEqual(finding['error_class'], ERROR_TEMPORARY)  # safe enum
        blob = repr(finding)
        for leak in ('shpat_', 'LEAK', 'SELECT', 'secret', '/path'):
            self.assertNotIn(leak, blob)

    # H6. The termination guarantee fails loudly on a live worker.
    def test_assert_workers_dead_fails_loud_on_live_worker(self):
        gate = threading.Event()
        thread = threading.Thread(target=gate.wait, daemon=True)
        thread.start()
        try:
            with self.assertRaises(AssertionError):
                self._assert_workers_dead((thread,))
        finally:
            gate.set()
            thread.join(timeout=self.BOUND_SECONDS)
        self._assert_workers_dead((thread,))   # now dead -> no raise

    # H7. The fresh zero-residue verifier checks job-log rows (and cleanup deletes
    # job logs before jobs). A runtime orphan job-log cannot exist (FK
    # ondelete='restrict'), so this guards the verifier/cleanup shape statically.
    def test_zero_residue_verifies_job_logs(self):
        residue_src = inspect.getsource(type(self)._assert_zero_residue)
        self.assertIn('shopify_connector_job_log', residue_src)
        self.assertIn('job-log residue after cleanup', residue_src)
        cleanup_src = inspect.getsource(type(self)._cleanup)
        self.assertIn('shopify_connector_job_log', cleanup_src)
        self.assertLess(
            cleanup_src.index('shopify_connector_job_log'),
            cleanup_src.index('DELETE FROM shopify_connector_job WHERE'),
            'job logs must be deleted before jobs (FK restrict)')


# ======================================================================
# CORE-R2 Foundation Slice 2A — disconnect lifecycle, quiescence
# controller, timeout finalization, credential-clear ordering.
#
# These classes exercise the Slice-2A production path: the two-phase
# `action_disconnect`, the `_run_disconnect_quiesce` controller + one-store
# selection, direction-C lease interpretation, `completed`/`timed_out`
# finalization + credential-clear ordering, and the delayed re-poll. The
# TransactionCase classes drive the real production methods (single
# connection); genuine cross-connection controller *selection* (locked-first
# / all-locked) is proven by `TestDisconnectControllerSelectionGenuine` using
# independent `db_connect` connections, mirroring `TestGenuineRealAdmission`.
# No live Shopify call, no lifecycle/state monkeypatch, no test-only timing
# hook (timeout is exercised by writing `disconnect_requested_at` -- a data
# value, not a clock fake).
# ======================================================================


class _DisconnectHelpers:
    """Shared fixtures/helpers for the Slice 2A tests (mixin, not a TestCase)."""

    def _make_store(self, state='connected', **vals):
        base = {
            'name': 'Disc Store',
            'shop_domain': 'disc-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': state,
        }
        base.update(vals)
        return self.env['shopify.connector.store'].create(base)

    def _connected_with_token(self):
        store = self._make_store(state='connected')
        # action_set_token demotes a connected store to reconnect_needed; re-
        # assert connected (the canonical fixture pattern used across the suite).
        self.env['shopify.connector.store.credential'].action_set_token(
            store, DUMMY_TOKEN
        )
        store.write({'state': 'connected'})
        return store

    def _credential(self, store):
        return self.env['shopify.connector.store.credential'].search(
            [('store_id', '=', store.id)], limit=1
        )

    def _disconnecting_store(self, requested_at=None, with_credential=False):
        store = (
            self._connected_with_token() if with_credential
            else self._make_store(state='connected')
        )
        store.write({
            'state': 'disconnecting',
            'disconnect_status': 'requested',
            'disconnect_requested_at': requested_at or fields.Datetime.now(),
        })
        return store

    def _make_lease(self, store, admitted_at=None, expires_at=None, job_id=1):
        now = fields.Datetime.now()
        return self.env['shopify.connector.call.lease'].create({
            'store_id': store.id,
            'lease_key': uuid.uuid4().hex,
            'job_id': job_id,
            'admitted_at': admitted_at or now,
            'expires_at': expires_at or (now + timedelta(seconds=300)),
        })

    def _lease_count(self, store):
        return self.env['shopify.connector.call.lease'].search_count(
            [('store_id', '=', store.id)]
        )

    def _audit_jobs(self, store):
        return self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_source', '=', 'setup_readiness_check'),
            ('job_type', '=', 'core_manual_maintenance'),
        ])

    def _disconnect_cron(self):
        return self.env.ref(
            'shopify_connector_core.ir_cron_shopify_connector_disconnect_quiesce'
        )

    def _cron_triggers(self, cron):
        return self.env['ir.cron.trigger'].search([('cron_id', '=', cron.id)])


class TestDisconnectPhase1(_DisconnectHelpers, TransactionCase):
    """Phase-1 two-phase `action_disconnect` + lifecycle request matrix.

    Controlled (single test connection). Review 4691182306 #1 made
    `_admit_lifecycle` capture its snapshot in an OWNED `registry.cursor()` side
    transaction (store-row FOR SHARE); registry test mode makes that side cursor a
    TestCursor sharing this test's connection so the in-test fixtures are visible
    cross-cursor (the mechanism `TestBusinessAdmission` uses for business
    `_admit`). Genuine cross-connection admission-vs-disconnect ordering is proven
    by `TestLifecycleAdmissionRaceGenuine`."""

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    # 1. connected -> disconnecting request (NOT disconnected; credential kept).
    def test_connected_moves_to_disconnecting(self):
        store = self._connected_with_token()
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.disconnect_status, 'requested')
        self.assertTrue(store.disconnect_requested_at)
        self.assertEqual(store.disconnect_requested_by, self.env.user)
        # Credential is NOT cleared in Phase 1 (analysis §15).
        self.assertTrue(store.credential_present)
        self.assertTrue(self._credential(store).access_token)
        self.assertFalse(store.disconnect_completed_at)

    # 2. generation increments exactly once.
    def test_disconnect_bumps_generation_exactly_once(self):
        store = self._make_store(state='connected')
        self.assertEqual(store.connection_generation, 0)
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.connection_generation, 1)

    # 3. repeated disconnect is an audited idempotent no-op.
    def test_repeated_disconnect_is_audited_noop(self):
        store = self._make_store(state='connected')
        store.action_disconnect()
        store.invalidate_recordset()
        gen_after_first = store.connection_generation
        audits_after_first = len(self._audit_jobs(store))
        # Second call: no state change, NO second generation bump, one more
        # audited no-op.
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.connection_generation, gen_after_first)
        self.assertEqual(len(self._audit_jobs(store)), audits_after_first + 1)
        # A third call on an already-disconnected store is also a no-op.
        store.write({'state': 'disconnected'})
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertEqual(store.connection_generation, gen_after_first)

    # Phase-1 A/B sweep cancels queued/retry_waiting business jobs only.
    def test_phase1_sweeps_queued_and_retry_waiting_only(self):
        store = self._make_store(state='connected')
        Job = self.env['shopify.connector.job']
        queued = Job.create({
            'store_id': store.id, 'job_source': 'manual_sync',
            'job_type': 'core_dispatch_selftest', 'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
        })
        retry = Job.create({
            'store_id': store.id, 'job_source': 'webhook',
            'job_type': 'core_dispatch_selftest', 'state': 'draft',
            'payload_hash': uuid.uuid4().hex,
        })
        retry.write({
            'state': 'retry_waiting', 'next_retry_at': fields.Datetime.now(),
            'retry_count': 1,
        })
        store.action_disconnect()
        for job in (queued, retry):
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled')
            self.assertEqual(job.cancel_reason, 'Store disconnecting.')

    # 18. Phase-1 sweep never writes a running/claimed business job row.
    def test_phase1_sweep_never_writes_running_job(self):
        store = self._make_store(state='connected')
        running = self.env['shopify.connector.job'].create({
            'store_id': store.id, 'job_source': 'scheduled_sync',
            'job_type': 'core_dispatch_selftest', 'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'started_at': fields.Datetime.now(),
        })
        store.action_disconnect()
        running.invalidate_recordset()
        # The running row is not a sweep candidate (domain is queued/
        # retry_waiting) -> left untouched, never cancelled, never written.
        self.assertEqual(running.state, 'running')
        self.assertFalse(running.cancel_reason)

    # 19. disconnecting is non-startable for business jobs.
    def test_disconnecting_business_job_not_startable(self):
        store = self._make_store(state='connected')
        job = self.env['shopify.connector.job'].create({
            'store_id': store.id, 'job_source': 'manual_sync',
            'job_type': 'core_dispatch_selftest', 'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
        })
        # Move to disconnecting WITHOUT the Phase-1 sweep, so the job survives to
        # attempt a start.
        store.write({'state': 'disconnecting'})
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

    # 20. action_test_connection is refused while disconnecting.
    def test_action_test_connection_refused_while_disconnecting(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            store.action_test_connection()
        # No audit/test job was created by the refused attempt.
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_test_connection'),
        ]))

    # 20. _admit_lifecycle (PRIVATE -- no RPC-exposed purpose, reviews 4690639375
    # #2 + 4690804619 #1) enforces the purpose->state matrix and returns the one
    # credential snapshot: `disconnecting` refuses every purpose; `test_connection`
    # excludes `disconnected`; `reconnect_probe` permits it.
    def test_admit_lifecycle_private_matrix_enforcement(self):
        Client = self.env['shopify.connector.api.client']
        store = self._connected_with_token()
        store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'test_connection')
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'reconnect_probe')
        # Unknown purpose fails closed.
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'not_a_purpose')
        # test_connection excludes `disconnected`; reconnect_probe permits it.
        store.write({'state': 'disconnected'})
        with self.assertRaises(UserError):
            Client._admit_lifecycle(store, 'test_connection')
        # reconnect_probe from disconnected passes the matrix and returns a
        # one-token snapshot (no transport needed for the gate).
        snapshot = Client._admit_lifecycle(store, 'reconnect_probe')
        self.assertEqual(snapshot['token'], DUMMY_TOKEN)
        self.assertEqual(
            snapshot['allowed_states'], ('reconnect_needed', 'disconnected'))

    # The purpose-carrying lifecycle entries are PRIVATE (not RPC-exposed); the
    # former `_execute_lifecycle` was split into `_admit_lifecycle`/`_send_lifecycle`.
    def test_lifecycle_helpers_are_private(self):
        Client = type(self.env['shopify.connector.api.client'])
        self.assertTrue(hasattr(Client, '_admit_lifecycle'))
        self.assertTrue(hasattr(Client, '_send_lifecycle'))
        self.assertFalse(hasattr(Client, 'execute_lifecycle'))
        self.assertFalse(hasattr(Client, '_execute_lifecycle'))

    # Activation and reconnect lifecycle operations are refused during
    # disconnecting (matrix §8).
    def test_activate_and_reconnect_refused_while_disconnecting(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            store.action_activate()
        with self.assertRaises(UserError):
            store.action_reconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')

    # A successful activation bumps the generation exactly once (matrix §8).
    def test_activation_bumps_generation(self):
        store = self._connected_with_token()
        store.write({'state': 'reconnect_needed'})
        now = fields.Datetime.now()
        store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': now,
            'last_readiness_at': now,
        })
        gen_before = store.connection_generation
        store.action_activate()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'connected')
        self.assertEqual(store.connection_generation, gen_before + 1)


class TestQuiescenceController(_DisconnectHelpers, TransactionCase):
    """The `_run_disconnect_quiesce` controller + direction-C finalization."""

    # 5 / 23. zero leases -> completed -> credential cleared -> disconnected.
    def test_zero_leases_completes_clears_credential(self):
        store = self._connected_with_token()
        store.action_disconnect()                    # -> disconnecting
        self.assertEqual(self._lease_count(store), 0)
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertEqual(store.disconnect_status, 'completed')
        self.assertTrue(store.disconnect_completed_at)
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)
        self.assertEqual(self._credential(store).credential_state, 'absent')

    # 4. credential remains present while leases exist before timeout.
    def test_credential_present_while_leases_before_timeout(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.disconnect_status, 'quiescing')
        self.assertTrue(store.credential_present)
        self.assertTrue(self._credential(store).access_token)

    # 6. one live lease -> quiescing, no credential clear, snapshot written.
    def test_one_live_lease_quiescing(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'quiescing')
        self.assertEqual(store.disconnect_open_lease_count, 1)
        self.assertTrue(store.disconnect_oldest_admitted_at)
        self.assertTrue(store.credential_present)

    # 7. one EXPIRED, unreleased lease still -> quiescing before timeout
    # (direction C: expired = unknown/live, still counts).
    def test_expired_lease_still_quiescing_before_timeout(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        now = fields.Datetime.now()
        self._make_lease(
            store,
            admitted_at=now - timedelta(seconds=600),
            expires_at=now - timedelta(seconds=1),      # already expired
        )
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'quiescing')
        self.assertEqual(store.disconnect_open_lease_count, 1)
        self.assertTrue(store.credential_present)       # never reaped -> no clear
        self.assertNotEqual(store.disconnect_status, 'completed')

    # 8 / 24. lease rows at the deadline -> timed_out, never completed, distinct.
    def test_leases_at_deadline_timed_out(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'timed_out')
        self.assertEqual(store.state, 'disconnected')
        self.assertNotEqual(store.disconnect_status, 'completed')

    # 9. timed_out finalization clears the credential.
    def test_timed_out_clears_credential(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    # 10. timed_out lease cleanup occurs ONLY AFTER finalization.
    def test_timed_out_cleans_leases_only_after_finalize(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        self._make_lease(store, job_id=2)
        self.assertEqual(self._lease_count(store), 2)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        # Snapshot recorded the outstanding count BEFORE cleanup...
        self.assertEqual(store.disconnect_open_lease_count, 2)
        self.assertEqual(store.disconnect_status, 'timed_out')
        # ...and the residual rows are cleaned up only after timed_out finalize.
        self.assertEqual(self._lease_count(store), 0)

    # 23. `completed` requires exactly zero lease rows.
    def test_completed_requires_zero_lease_rows(self):
        store = self._disconnecting_store(
            requested_at=fields.Datetime.now(), with_credential=True
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertNotEqual(store.disconnect_status, 'completed')
        self.assertNotEqual(store.state, 'disconnected')

    # 11 / 12. still-quiescing store schedules a DELAYED re-poll
    # (at >= now + POLL_DELAY), never an immediate/busy re-trigger.
    def test_quiescing_schedules_delayed_repoll(self):
        store = self._disconnecting_store(requested_at=fields.Datetime.now())
        self._make_lease(store)
        cron = self._disconnect_cron()
        self._cron_triggers(cron).unlink()          # isolate this pass's trigger
        before = fields.Datetime.now()
        store._process_disconnect_quiesce()
        after = fields.Datetime.now()
        triggers = self._cron_triggers(cron)
        self.assertTrue(triggers, 'a delayed re-poll trigger must be scheduled')
        for trig in triggers:
            # delayed by >= POLL_DELAY (no immediate same-store re-trigger)...
            self.assertGreaterEqual(trig.call_at, before + POLL_DELAY)
            # ...and not further out than one POLL_DELAY from this pass.
            self.assertLessEqual(
                trig.call_at, after + POLL_DELAY + timedelta(seconds=5)
            )

    # 14. exactly one store is processed per controller invocation.
    def test_one_store_per_invocation(self):
        now = fields.Datetime.now()
        store_a = self._disconnecting_store(
            requested_at=now - timedelta(seconds=20)     # older -> selected first
        )
        store_b = self._disconnecting_store(
            requested_at=now - timedelta(seconds=5)
        )
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store_a.invalidate_recordset()
        store_b.invalidate_recordset()
        self.assertEqual(store_a.state, 'disconnected')  # processed (0 leases)
        self.assertEqual(store_b.state, 'disconnecting')  # untouched this pass

    # 16. duplicate controller invocation is idempotent (no double-finalize).
    def test_controller_duplicate_invocation_idempotent(self):
        store = self._connected_with_token()
        store.action_disconnect()
        Controller = self.env['shopify.connector.store']
        Controller._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'completed')
        completed_at = store.disconnect_completed_at
        audits_before = len(self._audit_jobs(store))
        # A second pass must not re-finalize the now-disconnected store.
        Controller._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'completed')
        self.assertEqual(store.disconnect_completed_at, completed_at)
        self.assertEqual(len(self._audit_jobs(store)), audits_before)

    # 22. no token/credential enters the disconnect status/snapshot/audit.
    def test_no_secret_in_disconnect_fields_and_audit(self):
        store = self._disconnecting_store(
            requested_at=(
                fields.Datetime.now()
                - DISCONNECT_QUIESCE_TIMEOUT - timedelta(minutes=1)
            ),
            with_credential=True,
        )
        self._make_lease(store)
        store._process_disconnect_quiesce()            # -> timed_out, snapshot
        store.invalidate_recordset()
        self.assertEqual(store.disconnect_status, 'timed_out')
        # Store char/text fields carry no token...
        for fname, field in store._fields.items():
            if field.type in ('char', 'text') and store[fname]:
                self.assertNotIn(DUMMY_TOKEN, store[fname])
        # ...nor do the audit jobs/logs for this store.
        jobs = self.env['shopify.connector.job'].search(
            [('store_id', '=', store.id)]
        )
        logs = self.env['shopify.connector.job.log'].search(
            [('job_id', 'in', jobs.ids)]
        )
        for recs in (jobs, logs):
            for rec in recs:
                for fname, field in rec._fields.items():
                    if field.type in ('char', 'text') and rec[fname]:
                        self.assertNotIn(DUMMY_TOKEN, rec[fname])


class TestDisconnectSourceGuards(_DisconnectHelpers, TransactionCase):
    """Source-level guards for the Slice 2A store controller/lifecycle."""

    # 17. No explicit request/main-cursor commit anywhere in the store model.
    def test_no_main_cursor_commit_in_store_source(self):
        src = inspect.getsource(store_module)
        self.assertNotIn('self.env.cr.commit', src)
        self.assertNotIn('self._cr.commit', src)
        self.assertNotIn('self.env.cr.rollback', src)
        self.assertNotIn('.commit()', src)

    # Controller selection is the corrected FOR UPDATE SKIP LOCKED LIMIT 1.
    def test_controller_uses_skip_locked_limit_one(self):
        src = inspect.getsource(
            store_module.ShopifyConnectorStore._run_disconnect_quiesce
        )
        self.assertIn('try_lock_for_update(limit=1)', src)

    # The generation-changing lifecycle lock is a BLOCKING FOR NO KEY UPDATE
    # (never SKIP LOCKED -- a lifecycle transition must wait, not be skipped).
    def test_lifecycle_lock_is_blocking_for_no_key_update(self):
        src = inspect.getsource(
            store_module.ShopifyConnectorStore._lock_store_for_lifecycle
        )
        self.assertIn('FOR NO KEY UPDATE', src)
        self.assertNotIn('SKIP LOCKED', src)

    # Delayed re-poll uses _trigger(at=...); no immediate same-store re-trigger
    # from a quiescing pass; no busy loop / sleep anywhere.
    def test_delayed_repoll_and_no_busy_loop(self):
        proc_src = inspect.getsource(
            store_module.ShopifyConnectorStore._process_disconnect_quiesce
        )
        self.assertIn('POLL_DELAY', proc_src)
        trig_src = inspect.getsource(
            store_module.ShopifyConnectorStore._trigger_disconnect_controller
        )
        self.assertIn('_trigger(at=at)', trig_src)
        module_src = inspect.getsource(store_module)
        self.assertNotIn('while True', module_src)
        self.assertNotIn('time.sleep', module_src)
        self.assertNotIn('import time', module_src)

    # 21. Credential clear follows the store -> credential lock order: the
    # controller takes the store FOR UPDATE (selection) BEFORE any finalize calls
    # the controller-only PRIVATE clear primitive; it must NOT call the public
    # action_clear_token (which refuses a `disconnecting` store); Phase 1 never
    # clears the credential (review 4690804619 #2).
    def test_store_then_credential_clear_order(self):
        controller_src = inspect.getsource(
            store_module.ShopifyConnectorStore._run_disconnect_quiesce
        )
        self.assertIn('try_lock_for_update(limit=1)', controller_src)
        for name in (
            '_finalize_disconnect_completed', '_finalize_disconnect_timed_out',
        ):
            fsrc = inspect.getsource(
                getattr(store_module.ShopifyConnectorStore, name)
            )
            self.assertIn('_clear_token_under_store_lock', fsrc)
            self.assertNotIn('action_clear_token', fsrc)
        phase1 = inspect.getsource(
            store_module.ShopifyConnectorStore.action_disconnect
        )
        self.assertNotIn('action_clear_token', phase1)
        self.assertNotIn('_clear_token_under_store_lock', phase1)

    # The controller / finalization make NO Shopify call.
    def test_controller_makes_no_shopify_call(self):
        for name in (
            '_run_disconnect_quiesce', '_process_disconnect_quiesce',
            '_finalize_disconnect_completed', '_finalize_disconnect_timed_out',
        ):
            src = inspect.getsource(
                getattr(store_module.ShopifyConnectorStore, name)
            )
            for forbidden in (
                '_send', 'requests', '.execute(', 'execute_business',
                'execute_lifecycle',
            ):
                self.assertNotIn(forbidden, src)


@tagged('post_install', '-at_install')
class TestDisconnectControllerSelectionGenuine(TransactionCase):
    """Genuine cross-connection controller selection (proofs 13 + 15).

    A locked first store must not block a later unlocked one, and an all-locked
    set must be a safe no-op. Both need a *second* connection to hold a real
    row lock, so this uses independent `db_connect` connections (mirroring
    `TestGenuineRealAdmission`): fixtures are committed on a bounded connection,
    one/both stores are locked `FOR UPDATE` on a second bounded connection, the
    real `_run_disconnect_quiesce` runs on a worker connection, results are
    observed on a fresh connection, and teardown is bounded + fail-loud.
    """

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000

    def _open_bounded(self, dbname):
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _commit_two_disconnecting_stores(self, dbname):
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            now = fields.Datetime.now()
            ids = []
            # store_a is the OLDER request -> ordered first by the controller.
            for offset in (20, 5):
                store = env['shopify.connector.store'].create({
                    'name': 'Genuine Disc Store',
                    'shop_domain': 'genuine-disc-%s.myshopify.com'
                    % uuid.uuid4().hex,
                    'api_version': '2026-07',
                    'state': 'disconnecting',
                    'disconnect_status': 'requested',
                    'disconnect_requested_at': now - timedelta(seconds=offset),
                })
                env['shopify.connector.call.lease'].create({
                    'store_id': store.id,
                    'lease_key': uuid.uuid4().hex,
                    'job_id': 1,
                    'admitted_at': now,
                    'expires_at': now + timedelta(seconds=300),
                })
                ids.append(store.id)
            setup.commit()
            return ids
        finally:
            setup.close()

    def _status(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT disconnect_status FROM shopify_connector_store "
                "WHERE id = %s", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _cleanup(self, dbname, store_ids):
        if not store_ids:
            return
        cr = self._open_bounded(dbname)
        try:
            cr.execute(
                "DELETE FROM ir_cron_trigger WHERE cron_id IN "
                "(SELECT res_id FROM ir_model_data WHERE module = "
                "'shopify_connector_core' AND name = "
                "'ir_cron_shopify_connector_disconnect_quiesce')")
            cr.execute(
                "DELETE FROM shopify_connector_call_lease "
                "WHERE store_id = ANY(%s)", (list(store_ids),))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = ANY(%s)",
                (list(store_ids),))
            cr.commit()
        finally:
            cr.close()
        verifier = self._open_bounded(dbname)
        try:
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_store "
                "WHERE id = ANY(%s)", (list(store_ids),))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'store residue after cleanup')
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = ANY(%s)", (list(store_ids),))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'lease residue after cleanup')
            verifier.rollback()
        finally:
            verifier.close()

    def _run_controller_worker(self, dbname):
        worker = self._open_bounded(dbname)
        try:
            wenv = api.Environment(worker, SUPERUSER_ID, {})
            wenv['shopify.connector.store']._run_disconnect_quiesce()
            worker.commit()
        finally:
            worker.close()

    # 13. A locked first store does not block a later unlocked store.
    def test_locked_first_store_does_not_block_later(self):
        dbname = self.env.cr.dbname
        store_ids = []
        lock_cr = None
        try:
            store_ids = self._commit_two_disconnecting_stores(dbname)
            id_a, id_b = store_ids
            # Hold FOR UPDATE on the FIRST (older) store on an independent
            # connection.
            lock_cr = self._open_bounded(dbname)
            lock_cr.execute(
                "SELECT id FROM shopify_connector_store WHERE id = %s "
                "FOR UPDATE", (id_a,))
            lock_cr.fetchone()
            # The controller must skip the locked A and process B.
            self._run_controller_worker(dbname)
            self.assertEqual(self._status(dbname, id_b), 'quiescing')  # processed
            self.assertEqual(self._status(dbname, id_a), 'requested')  # skipped
        finally:
            if lock_cr is not None:
                lock_cr.rollback()
                lock_cr.close()
            self._cleanup(dbname, store_ids)

    # 15. All eligible stores locked -> the controller is a safe no-op.
    def test_all_locked_is_safe_noop(self):
        dbname = self.env.cr.dbname
        store_ids = []
        lock_cr = None
        try:
            store_ids = self._commit_two_disconnecting_stores(dbname)
            lock_cr = self._open_bounded(dbname)
            lock_cr.execute(
                "SELECT id FROM shopify_connector_store WHERE id = ANY(%s) "
                "FOR UPDATE", (list(store_ids),))
            lock_cr.fetchall()
            # Every eligible row is locked -> this pass processes nothing.
            self._run_controller_worker(dbname)
            for sid in store_ids:
                self.assertEqual(self._status(dbname, sid), 'requested')
        finally:
            if lock_cr is not None:
                lock_cr.rollback()
                lock_cr.close()
            self._cleanup(dbname, store_ids)


class TestLifecycleRaceCorrections(_DisconnectHelpers, TransactionCase):
    """CORE-R2 review 4690639375 #1/#2: activation/reconnect TOCTOU + the
    reconnect_probe path. Controlled tests driving the REAL production
    `action_activate`/`action_reconnect`; the racing disconnect is a genuine
    `action_disconnect` injected at the sanctioned `_send` transport seam (never
    a lifecycle/state monkeypatch). Single test connection: registry test mode
    makes the `_admit_lifecycle` side cursor (review 4691182306 #1) a TestCursor
    sharing this connection so the in-test fixtures are visible cross-cursor."""

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _seed_activation_evidence(self, store):
        now = fields.Datetime.now()
        store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': now,
            'last_readiness_at': now,
        })

    def _fake_readiness_pass(self):
        def fake_run_for_store(rc_self, store):
            store.write({
                'last_readiness_result': 'pass',
                'last_readiness_at': fields.Datetime.now(),
            })
            return {'job': None, 'overall_result': 'pass', 'checks': []}
        return fake_run_for_store

    # Activation must refuse a store a disconnect already won, without a second
    # generation bump and without an activation audit (TOCTOU-safe under lock).
    def test_activation_refuses_when_disconnect_won(self):
        store = self._connected_with_token()
        self._seed_activation_evidence(store)
        store.action_disconnect()                    # -> disconnecting, gen +1
        store.invalidate_recordset()
        gen_after_disconnect = store.connection_generation
        audits_before = len(self._audit_jobs(store))
        with self.assertRaises(UserError):
            store.action_activate()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')          # not overwritten
        self.assertEqual(
            store.connection_generation, gen_after_disconnect)  # no 2nd bump
        self.assertEqual(
            len(self._audit_jobs(store)), audits_before)        # no activation audit

    # Reconnect must refuse to overwrite a disconnect that won DURING the probe.
    def test_reconnect_refuses_when_disconnect_wins_during_probe(self):
        store = self._connected_with_token()
        store.write({'state': 'reconnect_needed'})
        store.invalidate_recordset()
        gen_before = store.connection_generation
        Client = self.env['shopify.connector.api.client']
        ReadinessCheck = self.env['shopify.connector.readiness.check']

        def racing_send(client_self, store_arg, body, token=None):
            # A REAL one-way disconnect wins the race during the probe's call.
            store.action_disconnect()
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        with patch.object(type(Client), '_send', racing_send), \
             patch.object(type(ReadinessCheck), 'run_for_store',
                          self._fake_readiness_pass()):
            store.action_reconnect()
        store.invalidate_recordset()
        # Disconnect won -> reconnect must NOT overwrite it.
        self.assertEqual(store.state, 'disconnecting')
        self.assertEqual(store.disconnect_status, 'requested')
        # Only the injected disconnect bumped the epoch (+1); reconnect bumped none.
        self.assertEqual(store.connection_generation, gen_before + 1)

    # Reconnect from a completed `disconnected` store (unchanged epoch) succeeds
    # via reconnect_probe -- NOT refused by a blanket `disconnected` check.
    def test_reconnect_from_disconnected_connects(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnected'})
        store.invalidate_recordset()
        gen_before = store.connection_generation
        Client = self.env['shopify.connector.api.client']
        ReadinessCheck = self.env['shopify.connector.readiness.check']

        def ok_send(client_self, store_arg, body, token=None):
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        with patch.object(type(Client), '_send', ok_send), \
             patch.object(type(ReadinessCheck), 'run_for_store',
                          self._fake_readiness_pass()):
            store.action_reconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'connected')
        self.assertEqual(store.connection_generation, gen_before + 1)


class TestLifecycleProbeSupersession(_DisconnectHelpers, TransactionCase):
    """CORE-R2 reviews 4690804619 #1 + 4691182306: the lifecycle probe binds to
    ONE credential snapshot (single token read, credential id/version, store
    generation), issues the request with exactly that token via
    `_send(store, body, token)`, and after the network result revalidates
    state/generation/credential id+version+value under the store->credential
    locks. A lifecycle or credential change that wins DURING the probe must be
    detected: the response is discarded, the probe job is audited `cancelled`
    ('superseded'), and NO verification/failure mirror or credential state is
    written.

    **Controlled seam-injection tests, NOT genuine concurrency (review
    4691182306 #2).** The racing change is injected at the sanctioned `_send`
    transport seam within a single test connection; registry test mode makes the
    `_admit_lifecycle` side cursor (review 4691182306 #1) a TestCursor sharing that
    connection, so these prove the snapshot/revalidation LOGIC but not
    distinct-backend independence. Genuine cross-connection admission-vs-disconnect
    ordering (both orders, distinct PIDs) is proven by
    `TestLifecycleAdmissionRaceGenuine`."""

    def setUp(self):
        super().setUp()
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _probe_job(self, store):
        return self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_test_connection'),
        ], order='id desc', limit=1)

    def _run_probe(self, store, send_fake):
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', send_fake):
            store.action_test_connection()

    def _replace_during_send(self, store, new_token):
        def racing_send(client_self, s, body, token=None):
            self.env['shopify.connector.store.credential'].action_replace_token(
                store, new_token)
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))
        return racing_send

    def test_send_lifecycle_receives_exact_snapshot_token(self):
        # Review §4: the request uses EXACTLY the admitted snapshot token -- the
        # transport is handed the token, never left to re-read the credential.
        store = self._connected_with_token()
        captured = {}

        def spy_send(client_self, s, body, token=None):
            captured['token'] = token
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        self._run_probe(store, spy_send)
        self.assertEqual(captured.get('token'), DUMMY_TOKEN)

    def test_probe_not_superseded_applies_pass_mirror(self):
        # Snapshot unchanged through the probe -> the result is applied normally
        # (guards against a false-positive supersede).
        store = self._connected_with_token()

        def ok_send(client_self, s, body, token=None):
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        self._run_probe(store, ok_send)
        store.invalidate_recordset()
        job = self._probe_job(store)
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(store.last_test_connection_result, 'pass')
        self.assertTrue(store.credential_last_verified_at)

    def test_test_connection_superseded_by_credential_replace(self):
        # A connected replace bumps the epoch -> generation mismatch supersedes.
        store = self._connected_with_token()
        self._run_probe(store, self._replace_during_send(store, DUMMY_TOKEN + 'N'))
        store.invalidate_recordset()
        job = self._probe_job(store)
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)
        # No pass mirror / verification stamp written from the stale result.
        self.assertNotEqual(store.last_test_connection_result, 'pass')
        self.assertFalse(store.credential_last_verified_at)

    def test_test_connection_superseded_by_disconnect(self):
        store = self._connected_with_token()

        def racing_send(client_self, s, body, token=None):
            store.action_disconnect()
            return FakeResponse(
                200, json_body=_success_body(domain=store.shop_domain))

        self._run_probe(store, racing_send)
        store.invalidate_recordset()
        job = self._probe_job(store)
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)
        self.assertEqual(store.state, 'disconnecting')
        self.assertNotEqual(store.last_test_connection_result, 'pass')

    def test_auth_failure_superseded_does_not_invalidate_replaced_token(self):
        # The exact hazard review 4690804619 #1 names: an OLD-token failure must
        # not invalidate a token that was REPLACED during the probe.
        store = self._connected_with_token()

        def racing_send(client_self, s, body, token=None):
            self.env['shopify.connector.store.credential'].action_replace_token(
                store, DUMMY_TOKEN + 'N')
            return FakeResponse(200, json_body={
                'errors': [{
                    'message': 'Access denied',
                    'extensions': {'code': 'ACCESS_DENIED'},
                }],
            })

        self._run_probe(store, racing_send)
        store.invalidate_recordset()
        job = self._probe_job(store)
        # Superseded -> cancelled, NOT failed_final; the new token is intact.
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)
        credential = self._credential(store)
        self.assertEqual(credential.access_token, DUMMY_TOKEN + 'N')
        self.assertNotEqual(credential.credential_state, 'invalid')

    def test_reconnect_superseded_by_credential_replace_aborts(self):
        # A reconnect_needed replace does NOT bump the epoch, so the credential
        # value revalidation is what supersedes; the reconnect then aborts BEFORE
        # readiness / finalize.
        store = self._connected_with_token()
        store.write({'state': 'reconnect_needed'})
        store.invalidate_recordset()
        Client = self.env['shopify.connector.api.client']
        ReadinessCheck = self.env['shopify.connector.readiness.check']
        readiness_calls = []

        def fake_readiness(rc_self, s):
            readiness_calls.append(s.id)
            return {'job': None, 'overall_result': 'pass', 'checks': []}

        with patch.object(
            type(Client), '_send',
            self._replace_during_send(store, DUMMY_TOKEN + 'N'),
        ), patch.object(
            type(ReadinessCheck), 'run_for_store', fake_readiness
        ):
            store.action_reconnect()
        store.invalidate_recordset()
        self.assertEqual(readiness_calls, [])          # aborted before readiness
        self.assertNotEqual(store.state, 'connected')
        job = self._probe_job(store)
        self.assertEqual(job.state, 'cancelled')
        self.assertIn('superseded', job.cancel_reason)


class TestCredentialClearPolicy(_DisconnectHelpers, TransactionCase):
    """CORE-R2 reviews 4690804619 #2 + 4690807427: the public/manual credential
    clear never bypasses two-phase quiescence. A live/recoverable store routes
    through `action_disconnect` and is cleared only by the controller at
    `completed`/`timed_out`; `disconnecting` is refused; only setup_incomplete /
    disconnected clear directly. An admitted lease keeps the credential present
    until the controller observes zero holders (no premature clear).

    **Controlled tests, NOT genuine concurrency (review 4691182306 #2).** These
    drive the REAL `action_clear_token`/`action_disconnect`/controller on a single
    test connection with a synthetic committed lease row; they prove the
    clear-policy LOGIC and the state/credential/generation sequence, but not
    distinct-backend independence. None of them opens a side cursor (no
    `_admit_lifecycle`), so registry test mode is unnecessary here. Genuine
    cross-connection public-clear-vs-business-admission ordering (both orders,
    distinct PIDs, real committed `execute_business` lease) is proven by
    `TestPublicClearAdmissionRaceGenuine`."""

    def test_public_clear_connected_defers_to_controller_no_premature_clear(self):
        # The linearization proof: a public clear on a connected store with an
        # outstanding committed lease must NOT clear the credential until the
        # controller reaches `completed` (zero holders).
        store = self._connected_with_token()
        lease = self._make_lease(store)
        self.env['shopify.connector.store.credential'].action_clear_token(store)
        store.invalidate_recordset()
        # Two-phase requested; credential still present while the lease is open.
        self.assertEqual(store.state, 'disconnecting')
        self.assertTrue(store.credential_present)
        self.assertEqual(self._credential(store).access_token, DUMMY_TOKEN)

        # Controller pass with the lease still open -> quiescing, still not cleared.
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        self.assertTrue(store.credential_present)
        self.assertEqual(self._credential(store).access_token, DUMMY_TOKEN)

        # Holder releases -> next controller pass finalizes and clears then.
        lease.unlink()
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertEqual(store.disconnect_status, 'completed')
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    def test_public_clear_refused_while_disconnecting(self):
        store = self._connected_with_token()
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnecting')
        with self.assertRaises(UserError):
            self.env['shopify.connector.store.credential'].action_clear_token(
                store)
        store.invalidate_recordset()
        # Credential untouched by the refused clear.
        self.assertTrue(store.credential_present)
        self.assertEqual(self._credential(store).access_token, DUMMY_TOKEN)

    def test_public_clear_direct_from_setup_incomplete(self):
        store = self._make_store(state='setup_incomplete')
        self.env['shopify.connector.store.credential'].action_set_token(
            store, DUMMY_TOKEN)
        self.env['shopify.connector.store.credential'].action_clear_token(store)
        store.invalidate_recordset()
        self.assertEqual(store.state, 'setup_incomplete')
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    def test_public_clear_direct_from_disconnected(self):
        store = self._connected_with_token()
        store.write({'state': 'disconnected'})
        self.env['shopify.connector.store.credential'].action_clear_token(store)
        store.invalidate_recordset()
        self.assertEqual(store.state, 'disconnected')
        self.assertFalse(store.credential_present)
        self.assertFalse(self._credential(store).access_token)

    def test_action_disconnect_uses_locked_generation_directly(self):
        # Review §11: the Phase-1 write bumps to locked_generation + 1 from the
        # value returned under the lock (exactly one bump).
        store = self._connected_with_token()
        store.invalidate_recordset()
        gen_before = store.connection_generation
        store.action_disconnect()
        store.invalidate_recordset()
        self.assertEqual(store.connection_generation, gen_before + 1)


@tagged('post_install', '-at_install')
class TestCredentialReplacementRaceGenuine(TransactionCase):
    """CORE-R2 review 4690639375 #3 (§6.8/§6.9): genuine admission-vs-replacement
    linearization through the REAL `execute_business`/`_admit` boundary and the
    REAL `action_replace_token`, on independent `db_connect` connections (the
    production `_admit` side transaction is made genuinely independent by patching
    the registry cursor factory for the bounded window, mirroring
    `TestGenuineRealAdmission`). Raw SQL is used only for observation/cleanup."""

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    NEW_TOKEN = 'shpat_DUMMYDUMMYDUMMY2222222222222222'

    def _open_bounded(self, dbname):
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _real_registry_cursor(self, dbname):
        return lambda *args, **kwargs: self._open_bounded(dbname)

    def _commit_connected_fixture(self, dbname):
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Cred Race Store',
                'shop_domain': 'cred-race-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN)
            # action_set_token demotes connected -> reconnect_needed; re-assert.
            store.write({'state': 'connected'})
            job = env['shopify.connector.job.enqueue'].enqueue(
                store, 'manual_sync', 'core_dispatch_selftest',
                payload_hash=uuid.uuid4().hex,
            )
            ids = (store.id, job.id)
            setup.commit()
            return ids
        finally:
            setup.close()

    def _observe(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, connection_generation FROM "
                "shopify_connector_store WHERE id = %s", (store_id,))
            store_row = obs.fetchone()
            obs.execute(
                "SELECT access_token FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cred_row = obs.fetchone()
            obs.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            lease_count = obs.fetchone()[0]
            obs.rollback()
            return store_row, cred_row, lease_count
        finally:
            obs.close()

    def _cleanup(self, dbname, store_id, job_id):
        if store_id is None:
            return
        cr = self._open_bounded(dbname)
        try:
            if job_id is not None:
                cr.execute(
                    "DELETE FROM shopify_connector_job_log WHERE job_id = %s",
                    (job_id,))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,))
            if job_id is not None:
                cr.execute(
                    "DELETE FROM shopify_connector_job WHERE id = %s", (job_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        verifier = self._open_bounded(dbname)
        try:
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'store residue after cleanup')
            verifier.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            self.assertEqual(
                verifier.fetchone()[0], 0, 'lease residue after cleanup')
            verifier.rollback()
        finally:
            verifier.close()

    # 6.9. Replacement winning FIRST: an old-generation admission fails closed
    # and never captures the newly-replaced token.
    def test_replacement_first_old_generation_admission_fails_closed(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        try:
            store_id, job_id = self._commit_connected_fixture(dbname)
            # Replacement commits first on an independent connection: connected ->
            # reconnect_needed, generation bumped, new token stored.
            repl = self._open_bounded(dbname)
            try:
                renv = api.Environment(repl, SUPERUSER_ID, {})
                renv['shopify.connector.store.credential'].action_replace_token(
                    renv['shopify.connector.store'].browse(store_id),
                    self.NEW_TOKEN,
                )
                repl.commit()
            finally:
                repl.close()
            # The old-generation admission now runs against the committed replace.
            worker = self._open_bounded(dbname)
            captured = {}
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def spy_send(client_self, s, b, token=None):
                    captured['token'] = token
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', spy_send):
                        with self.assertRaises(ShopifyQuiescedError):
                            with Client.execute_business(job, store, 'q'):
                                pass
                worker.rollback()
            finally:
                worker.close()
            # Fail-closed: no _send, so the new token was never captured...
            self.assertNotIn('token', captured)
            # ...and no lease was committed for the refused admission.
            _store_row, cred_row, lease_count = self._observe(dbname, store_id)
            self.assertEqual(lease_count, 0)
            self.assertEqual(cred_row[0], self.NEW_TOKEN)   # replace won
        finally:
            self._cleanup(dbname, store_id, job_id)

    # 6.8. Admission FIRST: it commits its lease and captures the OLD token; a
    # replacement during the call proceeds afterward and the in-flight call keeps
    # its captured old token (single in-memory snapshot).
    def test_admission_first_uses_old_token_then_replacement_proceeds(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        try:
            store_id, job_id = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname)
            captured = {}
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def racing_send(client_self, s, b, token=None):
                    # The lease is already committed (old gen, old token captured)
                    # before _send. A replacement now runs on an INDEPENDENT
                    # connection; it does not block (admission's FOR SHARE already
                    # released) and bumps the epoch.
                    captured['token'] = token
                    repl = self._open_bounded(dbname)
                    try:
                        renv = api.Environment(repl, SUPERUSER_ID, {})
                        renv[
                            'shopify.connector.store.credential'
                        ].action_replace_token(
                            renv['shopify.connector.store'].browse(store_id),
                            self.NEW_TOKEN,
                        )
                        repl.commit()
                    finally:
                        repl.close()
                    captured['lease_during'] = self._observe(dbname, store_id)[2]
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', racing_send):
                        with Client.execute_business(job, store, 'q') as result:
                            self.assertEqual(result['data'], {})
                worker.rollback()
            finally:
                worker.close()
            # The admitted call used its captured OLD token, never the replacement.
            self.assertEqual(captured['token'], DUMMY_TOKEN)
            self.assertEqual(captured['lease_during'], 1)   # lease held during call
            store_row, cred_row, lease_count = self._observe(dbname, store_id)
            self.assertEqual(cred_row[0], self.NEW_TOKEN)   # replace proceeded
            self.assertEqual(store_row[0], 'reconnect_needed')
            self.assertEqual(lease_count, 0)                # released on exit
        finally:
            self._cleanup(dbname, store_id, job_id)


class TestLifecycleAdmissionSourceGuards(TransactionCase):
    """CORE-R2 review 4691182306 #1 -- source guards for the ATOMIC lifecycle
    admission: `_admit_lifecycle` captures its snapshot in a short OWNED side
    transaction (store-row FOR SHARE) that commits/closes BEFORE the network call,
    creates NO call lease, hands the exact snapshot token to the transport, and its
    result still flows through the post-network revalidation. These are pure source
    assertions (no side cursor); genuine behaviour is proven by
    `TestLifecycleAdmissionRaceGenuine`."""

    def _admit_src(self):
        return inspect.getsource(
            client_module.ShopifyConnectorApiClient._admit_lifecycle)

    def _probe_src(self):
        return inspect.getsource(
            store_module.ShopifyConnectorStore._run_connection_probe)

    def test_admit_lifecycle_owns_a_side_cursor(self):
        src = self._admit_src()
        self.assertIn('self.env.registry.cursor()', src)
        self.assertIn('side_cr', src)

    def test_admit_lifecycle_executes_store_for_share(self):
        src = self._admit_src()
        self.assertIn('FOR SHARE', src)
        self.assertIn('FROM shopify_connector_store', src)

    def test_admit_lifecycle_fresh_matrix_check_under_lock(self):
        # The matrix state check reads the value returned by the FOR SHARE SELECT
        # (fresh under the lock), not a cached `store.state`.
        src = self._admit_src()
        self.assertIn('state, generation = row', src)
        self.assertIn('if state not in allowed_states:', src)

    def test_admit_lifecycle_single_token_read_under_lock(self):
        src = self._admit_src()
        self.assertEqual(src.count('_get_access_token('), 1)

    def test_admit_lifecycle_only_side_cursor_commit_and_rollback(self):
        src = self._admit_src()
        self.assertIn('side_cr.commit()', src)
        self.assertIn('side_cr.rollback()', src)
        self.assertNotIn('self.env.cr.commit', src)
        self.assertNotIn('self._cr.commit', src)
        committed = re.findall(r'(\w+)\.commit\(\)', src)
        self.assertTrue(committed)
        self.assertTrue(all(name == 'side_cr' for name in committed),
                        'only the owned side cursor may commit; found %s' % committed)
        rolled = re.findall(r'(\w+)\.rollback\(\)', src)
        self.assertTrue(all(name == 'side_cr' for name in rolled),
                        'only the owned side cursor may rollback; found %s' % rolled)

    def test_admit_lifecycle_creates_no_lease(self):
        src = self._admit_src()
        self.assertNotIn('call.lease', src)
        self.assertNotIn('lease_key', src)
        self.assertNotIn('.create(', src)

    def test_admit_lifecycle_commits_and_closes_before_transport(self):
        # The side transaction commits and the cursor closes INSIDE
        # `_admit_lifecycle`; the transport (`_send_lifecycle`) is a SEPARATE call
        # in `_run_connection_probe` that runs only AFTER `_admit_lifecycle`
        # returns -> no lock spans the network call.
        src = self._admit_src()
        self.assertIn('side_cr.commit()', src)
        self.assertIn('side_cr.close()', src)
        self.assertLess(src.index('side_cr.commit()'), src.index('return snapshot'))
        # No transport CALL inside the admission (the FOR SHARE must not span the
        # network). Inspect actual call nodes, so a docstring mention of
        # `_send_lifecycle` is NOT a false positive.
        fn = ast.parse(textwrap.dedent(src)).body[0]
        called = {
            n.func.attr for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        }
        self.assertNotIn('_send', called)
        self.assertNotIn('_send_lifecycle', called)
        probe = self._probe_src()
        self.assertLess(
            probe.index('_admit_lifecycle'), probe.index('_send_lifecycle'),
            'admission must complete before the transport call')

    def test_probe_passes_exact_snapshot_token_to_send(self):
        probe = self._probe_src()
        self.assertIn("snapshot['token']", probe)
        send_src = inspect.getsource(
            client_module.ShopifyConnectorApiClient._send_lifecycle)
        self.assertIn('self._send(store, body, token)', send_src)

    def test_post_network_revalidation_remains(self):
        probe = self._probe_src()
        self.assertIn('_lifecycle_probe_superseded(snapshot)', probe)
        reval = inspect.getsource(
            store_module.ShopifyConnectorStore._lifecycle_probe_superseded)
        self.assertIn('_lock_store_for_lifecycle', reval)
        self.assertIn('_lifecycle_credential_version', reval)
        self.assertIn("snapshot['generation']", reval)
        self.assertIn("snapshot['token']", reval)

    def test_admission_refusal_before_send_is_superseded(self):
        # A matrix refusal under the lock (disconnect won before the FOR SHARE)
        # is caught and audited as superseded, with no network issued.
        probe = self._probe_src()
        self.assertIn('except UserError:', probe)
        self.assertIn('_audit_probe_superseded(job)', probe)


class _GenuineRaceHelpers:
    """Shared GENUINE independent-connection helpers (mixin; mirrors
    `TestGenuineRealAdmission` / `TestCredentialReplacementRaceGenuine`): real
    pooled `db_connect` connections, bounded (statement_timeout + lock_timeout),
    with distinct backend PIDs. Raw SQL is used ONLY to commit fixtures, OBSERVE
    committed state, and clean up -- never to create the row under test."""

    STATEMENT_TIMEOUT_MS = 10000
    LOCK_TIMEOUT_MS = 8000
    BOUND_SECONDS = 20

    def _open_bounded(self, dbname, read_committed=False, lock_timeout_ms=None):
        """Open a genuine pooled cursor with BOTH transaction-local PostgreSQL
        limits. `read_committed=True` (first statement of the transaction) lets a
        single-shot genuine test observe the post-network FOR NO KEY UPDATE
        revalidation against a concurrently-committed disconnect WITHOUT the
        production request-level serialization-failure retry (production runs
        REPEATABLE READ + that retry; both converge on discarding the stale probe
        result). `lock_timeout_ms` overrides the default lock timeout for the
        lock-attribution proof."""
        cr = db_connect(dbname).cursor()
        try:
            if read_committed:
                cr.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            lt = self.LOCK_TIMEOUT_MS if lock_timeout_ms is None else lock_timeout_ms
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(lt)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _backend_pid(self, cr):
        cr.execute("SELECT pg_backend_pid()")
        return cr.fetchone()[0]

    def _real_registry_cursor(self, dbname):
        """registry.cursor() replacement handing out bounded real pooled cursors,
        so the production side transactions (`_admit`/`_admit_lifecycle`/
        `_release_lease`) are genuinely independent and time-bounded."""
        return lambda *args, **kwargs: self._open_bounded(dbname)

    def _recording_registry_cursor(self, dbname, pids, lock_timeout_ms=None):
        """As `_real_registry_cursor`, but records each handed-out cursor's backend
        PID so the production side transaction's backend is observably distinct."""
        def factory(*args, **kwargs):
            cr = self._open_bounded(dbname, lock_timeout_ms=lock_timeout_ms)
            pids.append(self._backend_pid(cr))
            return cr
        return factory

    def _sanitize(self, exc, phase):
        error_class = getattr(exc, 'error_class', None)
        return {
            'phase': phase,
            'type': type(exc).__name__,
            'error_class': error_class if isinstance(error_class, str) else None,
        }

    def _drain(self, q):
        findings = []
        while True:
            try:
                findings.append(q.get_nowait())
            except queue.Empty:
                break
        return findings

    def _assert_workers_dead(self, threads):
        alive = sum(1 for t in threads if t is not None and t.is_alive())
        self.assertEqual(
            alive, 0, 'worker thread still alive at the cleanup boundary')

    def _commit_connected_fixture(self, dbname, with_job=False):
        """Create+commit a connected store, its credential, and (optionally) one
        matching business job on an independent bounded connection. Returns
        `(store_id, shop_domain, job_id)`."""
        setup = self._open_bounded(dbname)
        try:
            env = api.Environment(setup, SUPERUSER_ID, {})
            shop_domain = 'genuine-lifecycle-%s.myshopify.com' % uuid.uuid4().hex
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Lifecycle Race Store',
                'shop_domain': shop_domain,
                'api_version': '2026-07',
                'state': 'connected',
            })
            env['shopify.connector.store.credential'].action_set_token(
                store, DUMMY_TOKEN)
            # action_set_token demotes connected -> reconnect_needed; re-assert.
            store.write({'state': 'connected'})
            job_id = None
            if with_job:
                job = env['shopify.connector.job.enqueue'].enqueue(
                    store, 'manual_sync', 'core_dispatch_selftest',
                    payload_hash=uuid.uuid4().hex,
                )
                job_id = job.id
            store_id = store.id
            setup.commit()
            return store_id, shop_domain, job_id
        finally:
            setup.close()

    def _observe_store(self, dbname, store_id):
        """(state, connection_generation, last_test_connection_result,
        credential_last_verified_at, credential_present) from a fresh connection."""
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, connection_generation, "
                "last_test_connection_result, credential_last_verified_at, "
                "credential_present FROM shopify_connector_store WHERE id = %s",
                (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row
        finally:
            obs.close()

    def _observe_credential_token(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT access_token FROM shopify_connector_store_credential "
                "WHERE store_id = %s", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row[0] if row else None
        finally:
            obs.close()

    def _observe_latest_probe_job(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT state, cancel_reason FROM shopify_connector_job "
                "WHERE store_id = %s AND job_type = 'core_test_connection' "
                "ORDER BY id DESC LIMIT 1", (store_id,))
            row = obs.fetchone()
            obs.rollback()
            return row
        finally:
            obs.close()

    def _lease_count(self, dbname, store_id):
        obs = self._open_bounded(dbname)
        try:
            obs.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE store_id = %s", (store_id,))
            n = obs.fetchone()[0]
            obs.rollback()
            return n
        finally:
            obs.close()

    def _cleanup(self, dbname, store_id):
        """Durable, bounded, fail-loud teardown + fresh zero-residue check
        (job logs before jobs for the FK restrict)."""
        if store_id is None:
            return
        cr = self._open_bounded(dbname)
        try:
            # Disconnect requests + quiescing controller passes schedule cron
            # triggers (action_disconnect / delayed re-poll); job enqueue may
            # schedule the drain cron. Remove both so no cron-trigger residue
            # survives (matching TestDisconnectControllerSelectionGenuine).
            cr.execute(
                "DELETE FROM ir_cron_trigger WHERE cron_id IN "
                "(SELECT res_id FROM ir_model_data WHERE module = "
                "'shopify_connector_core' AND name IN "
                "('ir_cron_shopify_connector_disconnect_quiesce', "
                "'ir_cron_shopify_connector_job_dispatch_drain'))")
            cr.execute(
                "DELETE FROM shopify_connector_job_log WHERE job_id IN "
                "(SELECT id FROM shopify_connector_job WHERE store_id = %s)",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_job WHERE store_id = %s", (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store_credential WHERE store_id = %s",
                (store_id,))
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,))
            cr.commit()
        finally:
            cr.close()
        self._assert_zero_residue(dbname, store_id)

    def _assert_zero_residue(self, dbname, store_id):
        v = self._open_bounded(dbname)
        try:
            for table, col, label in (
                ('shopify_connector_call_lease', 'store_id', 'lease'),
                ('shopify_connector_store', 'id', 'store'),
                ('shopify_connector_store_credential', 'store_id', 'credential'),
                ('shopify_connector_job', 'store_id', 'job'),
            ):
                v.execute(
                    "SELECT count(*) FROM %s WHERE %s = %%s" % (table, col),
                    (store_id,))
                self.assertEqual(
                    v.fetchone()[0], 0, '%s residue after cleanup' % label)
            v.rollback()
        finally:
            v.close()


@tagged('post_install', '-at_install')
class TestLifecycleAdmissionRaceGenuine(_GenuineRaceHelpers, TransactionCase):
    """CORE-R2 review 4691182306 #1/#2 -- GENUINE independent-transaction proof
    that the atomic lifecycle admission (`_admit_lifecycle`, a store-row FOR SHARE
    side transaction) linearizes a connection probe against `action_disconnect`
    across DISTINCT PostgreSQL backends. Proves both orders (admission-first,
    disconnect-first), that a disconnect-first order issues ZERO transport calls,
    that an admission-first order finishes with its exact captured OLD token and is
    then discarded as superseded with NO mirror written, that the admission takes a
    store-row lock conflicting with the lifecycle FOR NO KEY UPDATE, and a final
    THREADED case proving genuine simultaneity via the accepted Registry._lock
    bounded-window pattern.

    The production side transaction's own `registry.cursor()` is made genuinely
    independent (real bounded pooled cursor, distinct backend, committed) by
    patching the registry cursor factory for the bounded window (mirroring
    `TestGenuineRealAdmission`). Deterministic orderings are established by
    controlling which independent transaction commits first; the threaded case
    adds real wall-clock concurrency. Raw SQL only observes/cleans up. The full
    two-server production proof (T-19) remains a deferred Odoo.sh item (SRR-09)."""

    # A. Disconnect wins FIRST -> the admission FOR SHARE (fresh, distinct backend)
    # reads the committed `disconnecting` row the worker's stale snapshot did not
    # see, refuses UNDER the lock, and issues ZERO transport calls.
    def test_disconnect_first_probe_superseded_zero_transport(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        send_calls = []
        try:
            store_id, _domain, _job = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                worker_pid = self._backend_pid(worker)
                store = wenv['shopify.connector.store'].browse(store_id)
                self.assertEqual(store.state, 'connected')   # fix stale snapshot
                Client = wenv['shopify.connector.api.client']

                disc = self._open_bounded(dbname)
                try:
                    denv = api.Environment(disc, SUPERUSER_ID, {})
                    pids.append(self._backend_pid(disc))
                    denv['shopify.connector.store'].browse(
                        store_id).action_disconnect()
                    disc.commit()
                finally:
                    disc.close()

                def spy_send(client_self, s, body, token=None):
                    send_calls.append(1)
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._recording_registry_cursor(dbname, pids)):
                    with patch.object(type(Client), '_send', spy_send):
                        store.action_test_connection()
                # The pre-check passed on the worker's stale 'connected' snapshot;
                # the admission side cursor's FOR SHARE read committed
                # 'disconnecting' (distinct backend) and refused -> superseded,
                # no transport.
                job = wenv['shopify.connector.job'].search([
                    ('store_id', '=', store_id),
                    ('job_type', '=', 'core_test_connection'),
                ], order='id desc', limit=1)
                self.assertEqual(job.state, 'cancelled')
                self.assertIn('superseded', job.cancel_reason)
                worker.rollback()
            finally:
                worker.close()
            self.assertEqual(send_calls, [])                        # ZERO transport
            self.assertGreaterEqual(len(set(pids + [worker_pid])), 2)  # distinct PIDs
            self.assertEqual(self._lease_count(dbname, store_id), 0)   # no lease
        finally:
            self._cleanup(dbname, store_id)

    # B. Admission wins FIRST -> it captures the OLD token/generation; a disconnect
    # committed on a distinct backend during the call is caught by the post-network
    # revalidation: the probe finishes with its captured OLD token but the stale
    # result is discarded (superseded) with NO mirror written.
    def test_admission_first_uses_old_token_then_disconnect_supersedes(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        captured = {}
        try:
            store_id, shop_domain, _job = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname, read_committed=True)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                worker_pid = self._backend_pid(worker)
                store = wenv['shopify.connector.store'].browse(store_id)
                Client = wenv['shopify.connector.api.client']

                def racing_send(client_self, s, body, token=None):
                    # Admission already committed its FOR SHARE snapshot (old gen,
                    # old token). A REAL one-way disconnect now wins on an
                    # INDEPENDENT connection; it does not block (the admission
                    # FOR SHARE released at commit) and bumps the generation.
                    captured['token'] = token
                    disc = self._open_bounded(dbname)
                    try:
                        denv = api.Environment(disc, SUPERUSER_ID, {})
                        pids.append(self._backend_pid(disc))
                        denv['shopify.connector.store'].browse(
                            store_id).action_disconnect()
                        disc.commit()
                    finally:
                        disc.close()
                    return FakeResponse(
                        200, json_body=_success_body(domain=shop_domain))

                with patch.object(self.registry, 'cursor',
                                  self._recording_registry_cursor(dbname, pids)):
                    with patch.object(type(Client), '_send', racing_send):
                        store.action_test_connection()
                # The admitted probe finished with EXACTLY its captured OLD token.
                self.assertEqual(captured['token'], DUMMY_TOKEN)
                # The post-network revalidation discarded the stale result.
                job = wenv['shopify.connector.job'].search([
                    ('store_id', '=', store_id),
                    ('job_type', '=', 'core_test_connection'),
                ], order='id desc', limit=1)
                self.assertEqual(job.state, 'cancelled')
                self.assertIn('superseded', job.cancel_reason)
                store.invalidate_recordset()
                self.assertEqual(store.state, 'disconnecting')  # disconnect won
                self.assertNotEqual(store.last_test_connection_result, 'pass')
                self.assertFalse(store.credential_last_verified_at)  # no mirror
                worker.rollback()
            finally:
                worker.close()
            self.assertGreaterEqual(len(set(pids + [worker_pid])), 2)  # distinct PIDs
            # Credential value intact (disconnect does not clear until the
            # controller finalizes); the superseded probe wrote no credential state.
            self.assertEqual(
                self._observe_credential_token(dbname, store_id), DUMMY_TOKEN)
        finally:
            self._cleanup(dbname, store_id)

    # Store-row lock attribution: the admission FOR SHARE conflicts with a held
    # lifecycle FOR NO KEY UPDATE (distinct backend) -> it blocks and hits its
    # bounded lock_timeout; once the holder releases, the admission succeeds.
    def test_admission_for_share_conflicts_with_lifecycle_update_lock(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        try:
            store_id, _domain, _job = self._commit_connected_fixture(dbname)
            worker = self._open_bounded(dbname)
            holder = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                Client = wenv['shopify.connector.api.client']
                holder_pid = self._backend_pid(holder)
                # An independent connection holds the conflicting lifecycle update
                # lock (FOR NO KEY UPDATE) on the store row, uncommitted.
                holder.execute(
                    "SELECT id FROM shopify_connector_store WHERE id = %s "
                    "FOR NO KEY UPDATE", (store_id,))
                # The admission FOR SHARE must BLOCK on that lock and hit its
                # bounded lock_timeout -> raises (proving it takes a conflicting
                # store-row lock, on a distinct backend).
                with patch.object(
                    self.registry, 'cursor',
                    self._recording_registry_cursor(
                        dbname, pids, lock_timeout_ms=500)):
                    with self.assertRaises(psycopg2.OperationalError):
                        Client._admit_lifecycle(store, 'test_connection')
                # Release the holder -> the admission now succeeds (it was the lock).
                holder.rollback()
                with patch.object(self.registry, 'cursor',
                                  self._recording_registry_cursor(dbname, pids)):
                    snapshot = Client._admit_lifecycle(store, 'test_connection')
                self.assertEqual(snapshot['token'], DUMMY_TOKEN)
                worker.rollback()
            finally:
                holder.rollback()
                holder.close()
                worker.close()
            self.assertGreaterEqual(len(set(pids + [holder_pid])), 2)  # distinct PIDs
        finally:
            self._cleanup(dbname, store_id)

    # Genuine SIMULTANEITY (threaded): a worker admits and parks at the transport
    # seam on one backend while a disconnect commits on another; the worker's
    # post-network revalidation then supersedes the stale result. Uses the accepted
    # Registry._lock bounded-window pattern; no cursor/Environment is passed
    # between threads.
    def test_genuine_concurrent_admission_superseded_by_disconnect(self):
        dbname = self.env.cr.dbname
        store_id = None
        pids = []
        parked = threading.Semaphore(0)
        gate = threading.Event()
        diagnostics = queue.Queue()
        results = queue.Queue()
        worker_thread = None
        try:
            store_id, shop_domain, _job = self._commit_connected_fixture(dbname)

            def blocking_send(client_self, s, body, token=None):
                # Admission already committed; signal parked, then wait for the
                # disconnect to commit on the other backend.
                results.put({'token': token})
                parked.release()
                if not gate.wait(timeout=self.BOUND_SECONDS):
                    raise AssertionError('gate not set within bound')
                return FakeResponse(
                    200, json_body=_success_body(domain=shop_domain))

            def worker():
                wcr = None
                try:
                    threading.current_thread().dbname = dbname
                    wcr = self._open_bounded(dbname, read_committed=True)
                    worker_pid = self._backend_pid(wcr)
                    wenv = api.Environment(wcr, SUPERUSER_ID, {})
                    store = wenv['shopify.connector.store'].browse(store_id)
                    store.action_test_connection()
                    job = wenv['shopify.connector.job'].search([
                        ('store_id', '=', store_id),
                        ('job_type', '=', 'core_test_connection'),
                    ], order='id desc', limit=1)
                    store.invalidate_recordset()
                    results.put({
                        'worker_pid': worker_pid,
                        'job_state': job.state,
                        'cancel': job.cancel_reason or '',
                        'mirror': store.last_test_connection_result or '',
                    })
                except BaseException as exc:
                    diagnostics.put(self._sanitize(exc, 'worker_body'))
                finally:
                    if wcr is not None:
                        try:
                            wcr.rollback()
                        except BaseException as exc:
                            diagnostics.put(self._sanitize(exc, 'rollback'))
                        try:
                            wcr.close()
                        except BaseException as exc:
                            diagnostics.put(self._sanitize(exc, 'cursor_close'))

            Client = self.env['shopify.connector.api.client']
            disc_pid = None
            with patch.object(type(self.registry), '_lock', threading.RLock()), \
                 patch.object(self.registry, 'cursor',
                              self._recording_registry_cursor(dbname, pids)):
                with patch.object(type(Client), '_send', blocking_send):
                    worker_thread = threading.Thread(target=worker, daemon=True)
                    worker_thread.start()
                    try:
                        got = parked.acquire(timeout=self.BOUND_SECONDS)
                        if got:
                            # Worker admitted + parked at transport. Disconnect wins
                            # NOW, concurrently, on an independent backend (the
                            # worker holds its own connection open, so this is a
                            # genuinely distinct backend PID).
                            disc = self._open_bounded(dbname)
                            try:
                                denv = api.Environment(disc, SUPERUSER_ID, {})
                                disc_pid = self._backend_pid(disc)
                                pids.append(disc_pid)
                                denv['shopify.connector.store'].browse(
                                    store_id).action_disconnect()
                                disc.commit()
                            finally:
                                disc.close()
                    finally:
                        gate.set()
                        worker_thread.join(timeout=self.BOUND_SECONDS)
                        self._assert_workers_dead((worker_thread,))
            findings = self._drain(diagnostics)
            self.assertEqual(findings, [], 'worker findings: %s' % findings)
            self.assertTrue(got, 'worker did not park at the transport within bound')
            # First queue item is the parked-token; second is the outcome.
            first = results.get_nowait()
            self.assertEqual(first['token'], DUMMY_TOKEN)   # exact captured token
            outcome = results.get_nowait()
            self.assertEqual(outcome['job_state'], 'cancelled')
            self.assertIn('superseded', outcome['cancel'])
            self.assertNotEqual(outcome['mirror'], 'pass')  # no mirror written
            # Genuinely distinct backends: the parked worker (its own held-open
            # connection) and the concurrent disconnect ran on different PIDs.
            self.assertIsNotNone(disc_pid)
            self.assertNotEqual(outcome['worker_pid'], disc_pid)
        finally:
            gate.set()
            if worker_thread is not None:
                worker_thread.join(timeout=self.BOUND_SECONDS)
                self._assert_workers_dead((worker_thread,))
            self._cleanup(dbname, store_id)


@tagged('post_install', '-at_install')
class TestPublicClearAdmissionRaceGenuine(_GenuineRaceHelpers, TransactionCase):
    """CORE-R2 review 4691182306 #2 (§6) -- GENUINE independent-transaction proof
    of the public-clear vs business-admission linearization through the REAL
    `execute_business`/`_admit` boundary and the REAL public `action_clear_token`,
    on distinct PostgreSQL backends. Proves both orders: business admission first
    (the public clear requests two-phase disconnect, the credential is PRESERVED
    while the committed lease is open, and the controller clears it only after the
    lease releases -- one generation bump); public clear first (a later
    old-generation business admission FAILS CLOSED with no lease and no transport,
    and the credential remains until the controller finalizes)."""

    # A. Business admission wins FIRST: the committed lease outlives admission's
    # brief FOR SHARE; a public clear requests two-phase disconnect and clears
    # NOTHING until the controller reaches `completed` (zero holders).
    def test_business_admission_first_defers_clear_until_release(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        captured = {}
        try:
            store_id, shop_domain, job_id = self._commit_connected_fixture(
                dbname, with_job=True)
            initial = self._observe_store(dbname, store_id)
            initial_gen = initial[1]
            worker = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def racing_send(client_self, s, body, token=None):
                    # Business lease already committed (old token captured). A public
                    # clear on the CONNECTED store runs on an INDEPENDENT connection:
                    # it routes through two-phase action_disconnect and clears
                    # NOTHING now.
                    captured['token'] = token
                    clr = self._open_bounded(dbname)
                    try:
                        cenv = api.Environment(clr, SUPERUSER_ID, {})
                        cenv['shopify.connector.store.credential'].action_clear_token(
                            cenv['shopify.connector.store'].browse(store_id))
                        clr.commit()
                    finally:
                        clr.close()
                    # A controller pass with the lease still open -> quiescing,
                    # credential PRESERVED.
                    ctrl = self._open_bounded(dbname)
                    try:
                        ctenv = api.Environment(ctrl, SUPERUSER_ID, {})
                        ctenv['shopify.connector.store']._run_disconnect_quiesce()
                        ctrl.commit()
                    finally:
                        ctrl.close()
                    captured['during'] = self._observe_store(dbname, store_id)
                    captured['token_during'] = self._observe_credential_token(
                        dbname, store_id)
                    captured['lease_during'] = self._lease_count(dbname, store_id)
                    return FakeResponse(
                        200, json_body=_success_body(domain=shop_domain))

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', racing_send):
                        with Client.execute_business(job, store, 'q') as result:
                            self.assertEqual(
                                result['data']['shop']['id'],
                                'gid://shopify/Shop/1')
                worker.rollback()
            finally:
                worker.close()
            # During the call: two-phase requested, credential PRESERVED, lease open.
            self.assertEqual(captured['token'], DUMMY_TOKEN)
            self.assertEqual(captured['during'][0], 'disconnecting')  # state
            self.assertEqual(captured['token_during'], DUMMY_TOKEN)   # NOT cleared
            self.assertEqual(captured['lease_during'], 1)             # lease open
            # After the business call exits (lease released), the controller
            # finalizes and clears the credential -- ONE generation bump total.
            ctrl = self._open_bounded(dbname)
            try:
                ctenv = api.Environment(ctrl, SUPERUSER_ID, {})
                ctenv['shopify.connector.store']._run_disconnect_quiesce()
                ctrl.commit()
            finally:
                ctrl.close()
            final = self._observe_store(dbname, store_id)
            self.assertEqual(final[0], 'disconnected')                # state
            self.assertEqual(final[1], initial_gen + 1)               # ONE bump
            self.assertFalse(
                self._observe_credential_token(dbname, store_id))     # cleared NOW
            self.assertEqual(self._lease_count(dbname, store_id), 0)
        finally:
            self._cleanup(dbname, store_id)

    # B. Public clear wins FIRST: it requests two-phase disconnect (gen +1,
    # credential preserved); a later old-generation business admission FAILS CLOSED
    # (no lease, no transport), and the credential remains until finalization.
    def test_public_clear_first_business_admission_fails_closed(self):
        dbname = self.env.cr.dbname
        store_id = job_id = None
        captured = {}
        try:
            store_id, _domain, job_id = self._commit_connected_fixture(
                dbname, with_job=True)
            clr = self._open_bounded(dbname)
            try:
                cenv = api.Environment(clr, SUPERUSER_ID, {})
                cenv['shopify.connector.store.credential'].action_clear_token(
                    cenv['shopify.connector.store'].browse(store_id))
                clr.commit()
            finally:
                clr.close()
            worker = self._open_bounded(dbname)
            try:
                wenv = api.Environment(worker, SUPERUSER_ID, {})
                store = wenv['shopify.connector.store'].browse(store_id)
                job = wenv['shopify.connector.job'].browse(job_id)
                Client = wenv['shopify.connector.api.client']

                def spy_send(client_self, s, b, token=None):
                    captured['token'] = token
                    return FakeResponse(200, json_body={'data': {}})

                with patch.object(self.registry, 'cursor',
                                  self._real_registry_cursor(dbname)):
                    with patch.object(type(Client), '_send', spy_send):
                        with self.assertRaises(ShopifyQuiescedError):
                            with Client.execute_business(job, store, 'q'):
                                pass
                worker.rollback()
            finally:
                worker.close()
            self.assertNotIn('token', captured)                       # no transport
            self.assertEqual(self._lease_count(dbname, store_id), 0)  # no lease
            row = self._observe_store(dbname, store_id)
            self.assertEqual(row[0], 'disconnecting')                 # clear won
            # Credential remains until the controller finalizes (not cleared by the
            # clear request, not by the refused admission).
            self.assertEqual(
                self._observe_credential_token(dbname, store_id), DUMMY_TOKEN)
        finally:
            self._cleanup(dbname, store_id)
