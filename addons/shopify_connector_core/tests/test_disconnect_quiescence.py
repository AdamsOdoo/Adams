"""CORE-R2 foundation-slice tests (AR-047, gate `4952145926`).

These tests exercise the *admission half* of the CORE-R2 disconnect-quiescence
mechanism delivered in this slice: the committed `shopify.connector.call.lease`
model, the `execute_business` context-manager, the `_admit` store-row-locked
admission, `_release_lease`, the single-token `_send` contract, and the
enqueue-time connection-epoch capture. They do NOT test the disconnect
controller, `disconnecting` lifecycle, or `timed_out`/`completed` finalization —
those are deliberately later CORE-R2 slices.

Two test styles are used, on purpose:

* `TransactionCase` tests drive the **real production** `execute_business`/
  `_admit`/`_send`/`_release_lease` path. Under Odoo test mode the side cursor
  that `_admit` opens (`registry.cursor()`) is a `TestCursor` sharing the single
  test connection, so these prove the admission *logic* (gate, ordering,
  token-once, release) but cannot prove genuine cross-connection independence.
* `TestGenuineConcurrencyPrimitives` opens **genuine independent PostgreSQL
  connections** via `odoo.sql_db.db_connect` (never `registry.cursor()`) to prove
  the DB-level coordination primitives `_admit` relies on: an independently
  committed lease survives a caller's rollback, two `FOR SHARE` admissions on one
  store row do not conflict, and lease keys are distinct. Fixtures there are
  committed and torn down with durable, fail-loud cleanup.

No live Shopify call is made; the only transport seam replaced is `_send`. No
lifecycle/state monkeypatch and no test-only timing hook is used.
"""

import inspect
import re
import uuid
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..models import shopify_connector_api_client as client_module
from ..models.shopify_connector_api_client import ShopifyQuiescedError

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
    """A fake `_send` that records what it was handed and returns a sentinel.

    Mirrors the transport-injection seam of the existing api-client tests: it
    replaces ONLY `_send`, makes no network call, and never reads credentials.
    """

    def fake_send(self, store, body, token=None):
        captured.setdefault('calls', []).append(1)
        captured['token'] = token
        captured['body'] = body
        return {'data': {'ok': True}, 'throttle_status': None}

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


class TestBusinessAdmission(TransactionCase):
    """The real `execute_business`/`_admit`/`_release_lease` admission path."""

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

    # --- Refusals (fail closed; no lease, no _send) ---------------------

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

    # --- Admission success + token + ordering + release ----------------

    # 8/16. Token is read exactly once (at admission) and handed to _send.
    def test_token_read_once_and_passed_to_send(self):
        job = self._make_job()
        Cred = type(self.env['shopify.connector.store.credential'])
        reads = []
        captured = {}

        def counting_get(cred_self, store):
            reads.append(1)
            return 'TOKEN_SNAPSHOT_XYZ'

        self.env.flush_all()
        with patch.object(Cred, '_get_access_token', counting_get):
            with patch.object(type(self.Client), '_send', _ok_send(captured)):
                with self.Client.execute_business(job, self.store, 'q'):
                    pass
        self.assertEqual(reads, [1])                       # exactly once
        self.assertEqual(captured['token'], 'TOKEN_SNAPSHOT_XYZ')  # 16

    # 17. _send does not reread credentials when given a token; reads when not.
    def test_send_reads_credential_only_when_token_absent(self):
        from .test_api_client import FakeResponse
        Client = self.Client
        Cred = type(self.env['shopify.connector.store.credential'])
        posted = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            posted['headers'] = headers
            return FakeResponse(200, json_body={'data': {}})

        reads = []

        def counting_get(cred_self, store):
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
            return {'data': {}, 'throttle_status': None}

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

    # 12. Exception exit releases the lease and re-raises.
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
class TestGenuineConcurrencyPrimitives(TransactionCase):
    """DB-level coordination primitives via genuine independent connections.

    These use `odoo.sql_db.db_connect` (real, pooled connections), never
    `registry.cursor()` — which under test mode shares the single test
    connection and therefore cannot demonstrate cross-transaction independence.
    They exercise the exact PostgreSQL sequence `_admit` performs (store-row
    `FOR SHARE`, lease `INSERT`, independent `COMMIT`), proving the guarantees
    the admission relies on. The full two-server production-path proof (T-19)
    remains the deferred Odoo.sh runtime item (SRR-09 / RR-4).

    Fixtures are committed and torn down with durable, fail-loud cleanup; every
    connection sets a bounded `statement_timeout` so a wrongly-blocking lock
    fails the test rather than hanging.
    """

    STATEMENT_TIMEOUT_MS = 10000

    def _real_cursor(self, dbname):
        cr = db_connect(dbname).cursor()
        # SET LOCAL (not session): the bound covers this cursor's single
        # transaction (the potentially-blocking FOR SHARE + insert, up to its
        # commit) and auto-resets at transaction end, so it never leaks onto the
        # pooled connection for a later reuse.
        cr.execute("SET LOCAL statement_timeout = %s" % self.STATEMENT_TIMEOUT_MS)
        return cr

    def _make_committed_store(self, dbname):
        """Create a connected store on a genuine independent connection."""
        setup_cr = db_connect(dbname).cursor()
        try:
            env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Genuine Concurrency Store',
                'shop_domain': 'genuine-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07',
                'state': 'connected',
            })
            store_id = store.id
            setup_cr.commit()
            return store_id
        finally:
            setup_cr.close()

    def _raw_insert_lease(self, cr, store_id, lease_key, job_id=1):
        cr.execute(
            "INSERT INTO shopify_connector_call_lease "
            "(store_id, lease_key, job_id, worker_ref, admitted_at, expires_at) "
            "VALUES (%s, %s, %s, %s, (now() at time zone 'UTC'), "
            "((now() at time zone 'UTC') + interval '300 seconds'))",
            (store_id, lease_key, job_id, 'genuine-test'),
        )

    def _cleanup(self, dbname, store_id):
        """Durable teardown; deliberately does NOT swallow failures."""
        if not store_id:
            return
        cr = db_connect(dbname).cursor()
        try:
            cr.execute(
                "SET LOCAL statement_timeout = %s" % self.STATEMENT_TIMEOUT_MS
            )
            cr.execute(
                "DELETE FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,),
            )
            cr.execute(
                "DELETE FROM shopify_connector_store WHERE id = %s", (store_id,)
            )
            cr.commit()
        finally:
            cr.close()

    # 13. A committed lease survives the caller transaction's rollback.
    def test_committed_lease_survives_caller_rollback(self):
        dbname = self.env.cr.dbname
        store_id = None
        cursors = []
        lease_key = uuid.uuid4().hex
        try:
            store_id = self._make_committed_store(dbname)
            caller = self._real_cursor(dbname)
            admit = self._real_cursor(dbname)
            observer = self._real_cursor(dbname)
            cursors = [caller, admit, observer]
            # Caller opens a transaction (its own business work).
            caller.execute(
                "SELECT id FROM shopify_connector_store WHERE id = %s",
                (store_id,),
            )
            caller.fetchone()
            # Admission commits a lease on an INDEPENDENT transaction.
            self._raw_insert_lease(admit, store_id, lease_key)
            admit.commit()
            # The caller then rolls its whole transaction back.
            caller.rollback()
            # A fresh observer transaction still sees the committed lease.
            observer.execute(
                "SELECT count(*) FROM shopify_connector_call_lease "
                "WHERE lease_key = %s",
                (lease_key,),
            )
            self.assertEqual(observer.fetchone()[0], 1)
            observer.commit()
        finally:
            for cr in cursors:
                cr.close()
            self._cleanup(dbname, store_id)

    # 14/15. Two FOR SHARE admissions on one store both commit distinct leases.
    def test_two_concurrent_admissions_commit_distinct_leases(self):
        dbname = self.env.cr.dbname
        store_id = None
        cursors = []
        try:
            store_id = self._make_committed_store(dbname)
            worker_a = self._real_cursor(dbname)
            worker_b = self._real_cursor(dbname)
            observer = self._real_cursor(dbname)
            cursors = [worker_a, worker_b, observer]
            # Both take FOR SHARE on the SAME store row. If FOR SHARE
            # self-conflicted, worker_b would block and its statement_timeout
            # would fail the test rather than hang.
            worker_a.execute(
                "SELECT id FROM shopify_connector_store WHERE id = %s FOR SHARE",
                (store_id,),
            )
            worker_a.fetchone()
            worker_b.execute(
                "SELECT id FROM shopify_connector_store WHERE id = %s FOR SHARE",
                (store_id,),
            )
            worker_b.fetchone()
            # Both insert their own lease under the shared lock and commit.
            self._raw_insert_lease(worker_a, store_id, uuid.uuid4().hex)
            self._raw_insert_lease(worker_b, store_id, uuid.uuid4().hex)
            worker_a.commit()
            worker_b.commit()
            observer.execute(
                "SELECT count(*), count(distinct lease_key) "
                "FROM shopify_connector_call_lease WHERE store_id = %s",
                (store_id,),
            )
            total, distinct = observer.fetchone()
            self.assertEqual(total, 2)      # 14: both committed
            self.assertEqual(distinct, 2)   # 15: distinct keys
            observer.commit()
        finally:
            for cr in cursors:
                cr.close()
            self._cleanup(dbname, store_id)
