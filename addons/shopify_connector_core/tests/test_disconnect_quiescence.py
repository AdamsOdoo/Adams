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

import importlib
import inspect
import queue
import re
import threading
import traceback
import uuid
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import UserError
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..models import shopify_connector_api_client as client_module
from ..models.shopify_connector_api_client import (
    ERROR_AUTH,
    ERROR_TEMPORARY,
    REASON_TOKEN_INVALID,
    ShopifyClientError,
    ShopifyQuiescedError,
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
        job = self._make_job()  # captured expected_connection_generation == 0
        self.store.write({'connection_generation': 1})
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
        # 3b: opaque key (uuid4 hex; carries no store/job/token substring).
        self.assertRegex(seen['key'], r'^[0-9a-f]{32}$')
        self.assertNotIn(str(self.store.id), seen['key'])
        self.assertNotIn(str(job.id), seen['key'])
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
        with patch.object(type(self.Client), '_send', _ok_send({})):
            with patch.object(type(self.Client), '_release_lease',
                              counting_release):
                with self.assertRaises(Boom) as caught:
                    with self.Client.execute_business(job, self.store, 'q'):
                        raise raised
        self.assertIs(caught.exception, raised)           # same object/identity
        self.assertIsNone(caught.exception.__cause__)     # release ok -> no chain
        self.assertEqual(releases, [1])                   # released exactly once
        tb_text = ''.join(traceback.format_tb(caught.exception.__traceback__))
        self.assertIn(                                    # body raise site kept
            'test_body_exception_bare_reraise', tb_text)
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
            with patch.object(self.registry, 'cursor',
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
