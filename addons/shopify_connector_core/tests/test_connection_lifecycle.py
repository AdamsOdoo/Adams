import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_job import BUSINESS_JOB_SOURCES, TERMINAL_JOB_STATES
from .test_api_client import FakeResponse, _success_body

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
CORE_JOB_SOURCES_NOT_GATED = ('setup_readiness_check', 'export_preview_dry_run')
NON_CONNECTED_STATES = ('setup_incomplete', 'reconnect_needed', 'disconnected')


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
class TestConnectionLifecycle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Connection Lifecycle Test Store',
            'shop_domain': 'connection-lifecycle-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.user_admin = cls._create_group_user(
            'admin', 'group_shopify_connector_admin'
        )
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.Credential = cls.env['shopify.connector.store.credential']

    def setUp(self):
        super().setUp()
        # CORE-R2 (review 4691182306 #1): `action_test_connection` /
        # `action_reconnect` now route through `_admit_lifecycle`, which captures
        # its one-token snapshot in an OWNED `registry.cursor()` side transaction
        # (store-row FOR SHARE), exactly like business `_admit`. A plain
        # TransactionCase side cursor is a genuinely independent connection that
        # cannot see this class's uncommitted fixture; entering registry test mode
        # makes every `registry.cursor()` reuse the single test connection as a
        # TestCursor so the fixture is visible cross-cursor -- the sanctioned
        # mechanism `TestBusinessAdmission` already uses. Packet-§4 seam-compat
        # (transport-seam contract change): no assertion changed. Genuine
        # cross-connection admission-vs-disconnect behaviour is proven by the
        # genuine lifecycle-race classes in test_disconnect_quiescence.py.
        self.env.flush_all()
        self.registry_enter_test_mode()

    @classmethod
    def _create_group_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'Connection Lifecycle Test %s' % label,
            'login': 'connection_lifecycle_test_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    # ------------------------------------------------------------------
    # Shared fixtures/helpers
    # ------------------------------------------------------------------

    def _store(self):
        return self.store.with_user(self.user_admin)

    def _set_token(self):
        self.Credential.with_user(self.user_admin).action_set_token(
            self.store, DUMMY_TOKEN
        )

    def _get_credential(self):
        return self.Credential.search(
            [('store_id', '=', self.store.id)], limit=1
        )

    def _create_job(self, job_source, job_type='core_manual_maintenance', state='draft', **extra):
        vals = {
            'store_id': self.store.id,
            'job_source': job_source,
            'job_type': job_type,
            'state': state,
            'payload_hash': str(uuid.uuid4()),
        }
        vals.update(extra)
        return self.Job.create(vals)

    def _logs_for(self, job):
        return self.JobLog.search([('job_id', '=', job.id)], order='id asc')

    def _audit_jobs(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_source', '=', 'setup_readiness_check'),
            ('job_type', '=', 'core_manual_maintenance'),
        ])

    def _run_test_connection(self, response):
        # CORE-R2 (review 4690804619 #1): the lifecycle probe passes its one token
        # snapshot to `_send(store, body, token)`, so the transport-seam fake
        # accepts the token argument.
        Client = self.env['shopify.connector.api.client']
        with patch.object(
            type(Client), '_send',
            lambda self, store, body, token=None: response,
        ):
            return self._store().action_test_connection()

    def _run_reconnect(self, test_connection_response, readiness_result,
                       call_log=None, entry_state='reconnect_needed'):
        # CORE-R2 (AR-047; review 4690639375 #2): action_reconnect probes via the
        # INTERNAL purpose 'reconnect_probe', whose frozen matrix permits only
        # reconnect_needed / disconnected. Put the store in a valid reconnect
        # entry state first (default reconnect_needed; pass 'disconnected' to
        # exercise reconnect after a completed disconnect).
        self.store.write({'state': entry_state})
        Client = self.env['shopify.connector.api.client']
        ReadinessCheck = self.env['shopify.connector.readiness.check']
        if call_log is None:
            call_log = []

        def fake_run_for_store(rc_self, store):
            call_log.append(store.id)
            store.write({
                'last_readiness_result': readiness_result,
                'last_readiness_at': fields.Datetime.now(),
            })
            return {'job': None, 'overall_result': readiness_result, 'checks': []}

        with patch.object(
            type(Client), '_send',
            lambda self, store, body, token=None: test_connection_response,
        ), patch.object(
            type(ReadinessCheck), 'run_for_store', fake_run_for_store
        ):
            self._store().action_reconnect()
        return call_log

    # ------------------------------------------------------------------
    # action_activate
    # ------------------------------------------------------------------

    def _seed_verified_evidence(self, readiness_result='pass', readiness_at=None):
        # Shared helper: seeds a fully fresh, activate-eligible evidence
        # set -- credential_last_verified_at and last_readiness_at
        # default to the SAME timestamp so last_readiness_at >=
        # credential_last_verified_at holds deterministically (equal
        # timestamps satisfy the freshness check).
        now = fields.Datetime.now()
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': readiness_result,
            'credential_last_verified_at': now,
            'last_readiness_at': readiness_at if readiness_at is not None else now,
        })
        return now

    def test_activate_succeeds_with_pass_and_pass(self):
        self._set_token()
        self._seed_verified_evidence(readiness_result='pass')
        self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')
        audit_jobs = self._audit_jobs()
        self.assertEqual(len(audit_jobs), 1)
        self.assertEqual(audit_jobs.state, 'succeeded')
        logs = self._logs_for(audit_jobs)
        self.assertTrue(any(log.event_type == 'manual_action' for log in logs))

    def test_activate_succeeds_with_pass_and_warning(self):
        self._set_token()
        self._seed_verified_evidence(readiness_result='warning')
        self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')

    def test_activate_rejects_missing_evidence_leaves_state_unchanged(self):
        self.assertFalse(self.store.last_test_connection_result)
        self.assertFalse(self.store.last_readiness_result)
        jobs_before = self._audit_jobs()
        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'setup_incomplete')
        self.assertEqual(self._audit_jobs(), jobs_before)

    def test_activate_rejects_failing_evidence_leaves_state_unchanged(self):
        self._set_token()
        self.store.write({
            'state': 'reconnect_needed',
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'fail',
            'credential_last_verified_at': fields.Datetime.now(),
        })
        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')

    def test_activate_rejects_fail_test_connection_even_with_pass_readiness(self):
        self._set_token()
        self.store.write({
            'last_test_connection_result': 'fail',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': fields.Datetime.now(),
        })
        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')

    def test_activate_rejects_missing_credential(self):
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
        })
        self.assertFalse(self.store.credential_present)
        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')

    def test_activate_rejects_stale_evidence_after_disconnect(self):
        # The exact race the credential-presence guard exists to close:
        # activate once (pass/pass -> connected), disconnect (credential
        # cleared, but the last_test_connection_result/last_readiness_
        # result mirrors are untouched by disconnect), then activate
        # again -- must NOT silently reconnect on the now-stale mirrors.
        self._set_token()
        self._seed_verified_evidence()
        self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')

        # CORE-R2 (AR-047): two-phase disconnect -> `disconnecting`, then the
        # controller finalizes -> `disconnected` and clears the credential. The
        # last_test_connection_result/last_readiness_result mirrors are NOT reset.
        self._store().action_disconnect()
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnected')
        self.assertFalse(self.store.credential_present)
        # Stale mirrors are still 'pass'/'pass' -- disconnect does not
        # reset them.
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertEqual(self.store.last_readiness_result, 'pass')

        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')
        self.assertEqual(self.store.state, 'disconnected')

    def test_activate_rejects_stale_evidence_after_credential_replace(self):
        # ChatGPT review (PR #121, Revision 5): action_replace_token
        # clears credential_last_verified_at on every token swap but
        # does not reset last_test_connection_result/last_readiness_
        # result, so a replaced token could otherwise activate on
        # pass/pass evidence recorded for the PREVIOUS token -- exactly
        # the "never infer connection success" violation
        # credential_last_verified_at exists to close. Odoo.sh runtime
        # exposed a lifecycle state invalidation gap on top of that:
        # action_replace_token() left store.state == 'connected' even
        # though the credential backing that state had just changed --
        # a connected store must not remain connected after its
        # credential is replaced, since business-job gating keys off
        # store.state. action_replace_token() now also moves a
        # 'connected' store to 'reconnect_needed'.
        self._set_token()
        self._seed_verified_evidence()
        self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')
        audit_jobs_before = self._audit_jobs()

        self.Credential.with_user(self.user_admin).action_replace_token(
            self.store, DUMMY_TOKEN + 'REPLACED'
        )
        self.store.invalidate_recordset()
        self.assertTrue(self.store.credential_present)
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertEqual(self.store.state, 'reconnect_needed')
        # The stale mirrors are untouched by the token replacement --
        # still 'pass'/'pass', but they no longer describe the current
        # credential.
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertEqual(self.store.last_readiness_result, 'pass')
        # action_replace_token() itself creates no job/log rows -- the
        # state move above is a credential-service side effect, not an
        # audited lifecycle action.
        self.assertEqual(len(self._audit_jobs()), len(audit_jobs_before))

        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(len(self._audit_jobs()), len(audit_jobs_before))

    def test_activate_rejects_stale_evidence_after_action_set_token_update(self):
        # Odoo.sh runtime revision (PR #121): the credential.write_date
        # freshness comparison this test originally exercised proved
        # brittle against real DB write timing and was removed. The
        # stale-evidence path via action_set_token() is now closed at
        # the credential-service source instead: action_set_token()
        # itself clears credential_last_verified_at on every set/update
        # (including updating an EXISTING credential row, e.g.
        # re-entering/correcting a token) -- so a token silently
        # overwritten via action_set_token() can no longer activate on
        # pass/pass evidence recorded for the value it replaced.
        # Revision 5: action_set_token() now also performs the
        # store.state invalidation itself (connected -> reconnect_
        # needed) -- no manual state move is done here anymore, this
        # test proves the credential service does it.
        self._set_token()
        self._seed_verified_evidence()
        self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')
        audit_jobs_before = self._audit_jobs()

        self.Credential.with_user(self.user_admin).action_set_token(
            self.store, DUMMY_TOKEN + 'OVERWRITTEN'
        )
        self.store.invalidate_recordset()
        self.assertTrue(self.store.credential_present)
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertEqual(self.store.state, 'reconnect_needed')
        # The stale mirrors are untouched by the token overwrite -- still
        # 'pass'/'pass', but they no longer describe the current
        # credential.
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertEqual(self.store.last_readiness_result, 'pass')
        # action_set_token() itself creates no job/log rows -- the state
        # move above is a credential-service side effect, not an audited
        # lifecycle action.
        self.assertEqual(len(self._audit_jobs()), len(audit_jobs_before))

        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(len(self._audit_jobs()), len(audit_jobs_before))

    def test_activate_rejects_stale_readiness_evidence_before_verification(self):
        # Readiness-freshness guard: a readiness pass recorded BEFORE the
        # current credential was verified must not count as evidence for
        # it -- otherwise stale readiness evidence from an old
        # credential/test-connection cycle could carry an activation for
        # a credential it never actually validated against. Deterministic
        # setup (explicit 10-minute gap) avoids same-second flakiness.
        self._set_token()
        verified_at = fields.Datetime.now()
        old_readiness_at = verified_at - timedelta(minutes=10)
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'last_readiness_at': old_readiness_at,
            'credential_last_verified_at': verified_at,
        })
        jobs_before = self._audit_jobs()
        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')
        self.assertEqual(self._audit_jobs(), jobs_before)

    def test_activate_rejects_missing_readiness_at(self):
        self._set_token()
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': fields.Datetime.now(),
        })
        self.assertFalse(self.store.last_readiness_at)
        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')

    # ------------------------------------------------------------------
    # Credential-service lifecycle state invalidation (direct calls,
    # not via action_disconnect())
    # ------------------------------------------------------------------

    def test_credential_service_clear_token_on_connected_requests_disconnect(self):
        # CORE-R2 (reviews 4690804619 #2 + 4690807427): calling the credential
        # service's action_clear_token() directly on a `connected` store must NOT
        # clear immediately -- an admitted lease can outlive admission's brief
        # FOR SHARE. It routes through the accepted two-phase disconnect
        # (state -> disconnecting, credential still present, one epoch bump); the
        # quiescence controller performs the actual clear at `completed`.
        self._set_token()
        self._seed_verified_evidence()
        self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')
        gen_before = self.store.connection_generation

        self.Credential.with_user(self.user_admin).action_clear_token(
            self.store
        )
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.disconnect_status, 'requested')
        self.assertTrue(self.store.credential_present)   # not cleared yet
        self.assertEqual(self.store.connection_generation, gen_before + 1)

        # The controller finalizes (zero committed leases) and clears then.
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnected')
        self.assertFalse(self.store.credential_present)

    # ------------------------------------------------------------------
    # action_disconnect
    # ------------------------------------------------------------------

    def test_disconnect_clears_credential_value(self):
        # CORE-R2 (AR-047): two-phase disconnect -- Phase 1 keeps the credential
        # (state -> disconnecting); the quiescence controller clears it at the
        # `completed` finalize once the store has zero committed call leases.
        self._set_token()
        self.store.write({'state': 'connected'})
        self._store().action_disconnect()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertTrue(self.store.credential_present)      # not cleared in Phase 1
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        credential = self._get_credential()
        self.assertFalse(credential.access_token)
        self.assertEqual(credential.credential_state, 'absent')
        self.store.invalidate_recordset()
        self.assertFalse(self.store.credential_present)
        self.assertEqual(self.store.state, 'disconnected')

    def test_disconnect_preserves_credential_row(self):
        self._set_token()
        self.Credential.with_user(self.user_admin).action_replace_token(
            self.store, DUMMY_TOKEN + 'X'
        )
        self.store.invalidate_recordset()
        replaced_at = self.store.credential_last_replaced_at
        self.assertTrue(replaced_at)
        self._store().action_disconnect()
        credential = self._get_credential()
        self.assertEqual(len(credential), 1)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.credential_last_replaced_at, replaced_at)

    def test_disconnect_sets_state_disconnected(self):
        # CORE-R2 (AR-047): Phase 1 moves the store to `disconnecting`; the
        # quiescence controller finalizes it to `disconnected`.
        self.store.write({'state': 'connected'})
        self._store().action_disconnect()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.disconnect_status, 'requested')
        self.env['shopify.connector.store']._run_disconnect_quiesce()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnected')
        self.assertEqual(self.store.disconnect_status, 'completed')

    def test_disconnect_cancels_non_terminal_business_jobs(self):
        # CORE-R2 (AR-047): the two-phase Phase-1 sweep is the non-blocking A/B
        # sweep -- it cancels only the queued/retry_waiting business jobs (the
        # cancellable rows) with reason 'Store disconnecting.', and never writes
        # a running/claimed row (that row is represented by its admission lease
        # and handled by the controller/timeout).
        self.store.write({'state': 'connected'})
        queued = self._create_job('webhook', state='queued')
        retry = self._create_job(
            'manual_sync', state='retry_waiting',
            next_retry_at=fields.Datetime.now(), retry_count=1,
        )
        running = self._create_job('scheduled_sync', state='running')
        self._store().action_disconnect()
        for job in (queued, retry):
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled')
            self.assertEqual(job.cancel_reason, 'Store disconnecting.')
            self.assertTrue(job.finished_at)
            logs = self._logs_for(job)
            cancel_logs = logs.filtered(lambda l: l.to_state == 'cancelled')
            self.assertTrue(cancel_logs)
            self.assertEqual(cancel_logs[0].event_type, 'state_change')
        # The running job is not an A/B candidate -> left untouched, never
        # written (no locked running-job row write).
        running.invalidate_recordset()
        self.assertEqual(running.state, 'running')
        self.assertFalse(running.cancel_reason)

    def test_disconnect_does_not_cancel_core_jobs(self):
        self.store.write({'state': 'setup_incomplete'})
        readiness_job = self._create_job(
            'setup_readiness_check', job_type='core_readiness_check',
            state='running',
        )
        test_conn_job = self._create_job(
            'setup_readiness_check', job_type='core_test_connection',
            state='running',
        )
        preview_job = self._create_job(
            'export_preview_dry_run', job_type='core_manual_maintenance',
            state='draft',
        )
        self.store.write({'state': 'connected'})
        self._store().action_disconnect()
        for job in (readiness_job, test_conn_job, preview_job):
            job.invalidate_recordset()
            self.assertNotEqual(job.state, 'cancelled')
            self.assertFalse(job.cancel_reason)

    def test_disconnect_does_not_alter_terminal_jobs(self):
        self.store.write({'state': 'connected'})
        succeeded_job = self._create_job('manual_sync', state='succeeded')
        failed_job = self._create_job('reconciliation', state='failed_final')
        skipped_job = self._create_job('odoo_event', state='skipped', trigger_origin='inventory_stock_change')
        self._store().action_disconnect()
        for job in (succeeded_job, failed_job, skipped_job):
            job.invalidate_recordset()
            self.assertIn(job.state, TERMINAL_JOB_STATES)
            self.assertFalse(job.cancel_reason)

    def test_disconnect_is_idempotent(self):
        # CORE-R2 (AR-047): a repeated disconnect while already `disconnecting`
        # is an audited idempotent no-op -- no re-sweep of the already-cancelled
        # job, no second generation bump, exactly one more audit job.
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='queued')
        self._store().action_disconnect()
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        gen_after_first = self.store.connection_generation
        logs_after_first = self._logs_for(job)
        audit_count_after_first = len(self._audit_jobs())

        # Second call must not raise, must not re-touch the already-
        # cancelled job, and must not re-bump the generation.
        self._store().action_disconnect()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.connection_generation, gen_after_first)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(len(self._logs_for(job)), len(logs_after_first))
        # The second call is an audited no-op: exactly one more audit
        # job is recorded, nothing errors.
        self.assertEqual(len(self._audit_jobs()), audit_count_after_first + 1)

    # ------------------------------------------------------------------
    # Business job enqueue-time gating (create())
    # ------------------------------------------------------------------

    def test_business_job_create_blocked_when_not_connected(self):
        for state in NON_CONNECTED_STATES:
            self.store.write({'state': state})
            for job_source in BUSINESS_JOB_SOURCES:
                extra = {}
                if job_source == 'odoo_event':
                    extra['trigger_origin'] = 'inventory_stock_change'
                with self.assertRaises(ValidationError):
                    self._create_job(job_source, state='draft', **extra)

    def test_business_job_create_succeeds_when_connected(self):
        self.store.write({'state': 'connected'})
        for job_source in BUSINESS_JOB_SOURCES:
            extra = {}
            if job_source == 'odoo_event':
                extra['trigger_origin'] = 'inventory_stock_change'
            job = self._create_job(job_source, state='draft', **extra)
            self.assertTrue(job.id)

    def test_core_jobs_creatable_when_not_connected(self):
        for state in NON_CONNECTED_STATES:
            self.store.write({'state': state})
            for job_source in CORE_JOB_SOURCES_NOT_GATED:
                job = self._create_job(
                    job_source, job_type='core_manual_maintenance',
                    state='running',
                )
                self.assertTrue(job.id)

    # ------------------------------------------------------------------
    # Business job execution-time gating (write() to 'running')
    # ------------------------------------------------------------------

    def test_business_job_running_blocked_when_not_connected(self):
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='queued')
        # Race: the store disconnects after enqueue but before start.
        self.store.write({'state': 'disconnected'})
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

    def test_business_job_running_succeeds_when_connected(self):
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='queued')
        job.write({'state': 'running'})
        self.assertEqual(job.state, 'running')

    def test_business_job_running_blocked_when_job_source_changed_in_same_write(self):
        # A job created under a core (ungated) source must not be able
        # to bypass the gate by changing job_source to a business source
        # in the very same write() call that also sets state='running'.
        self.store.write({'state': 'disconnected'})
        job = self._create_job(
            'setup_readiness_check', job_type='core_manual_maintenance',
            state='queued',
        )
        with self.assertRaises(ValidationError):
            job.write({'job_source': 'manual_sync', 'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

    def test_business_job_running_blocked_when_store_id_changed_in_same_write(self):
        # Symmetric bypass attempt via store_id instead of job_source.
        other_store = self.env['shopify.connector.store'].create({
            'name': 'Other Disconnected Store',
            'shop_domain': 'other-disconnected-store.myshopify.com',
            'api_version': '2026-07',
            'state': 'disconnected',
        })
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='queued')
        with self.assertRaises(ValidationError):
            job.write({'store_id': other_store.id, 'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'queued')

    def test_business_job_can_be_cancelled_when_not_connected(self):
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='draft')
        self.store.write({'state': 'disconnected'})
        job.write({
            'state': 'cancelled',
            'cancel_reason': 'Manual test cancel.',
            'finished_at': fields.Datetime.now(),
        })
        self.assertEqual(job.state, 'cancelled')

    def test_core_job_running_never_gated(self):
        self.store.write({'state': 'disconnected'})
        job = self._create_job(
            'setup_readiness_check', job_type='core_test_connection',
            state='queued',
        )
        job.write({'state': 'running'})
        self.assertEqual(job.state, 'running')

    # ------------------------------------------------------------------
    # action_mark_reconnect_needed
    # ------------------------------------------------------------------

    def test_mark_reconnect_needed_sets_state_keeps_credential(self):
        self._set_token()
        self.store.write({'state': 'connected'})
        self._store().action_mark_reconnect_needed(reason='test signal')
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertTrue(self.store.credential_present)
        credential = self._get_credential()
        self.assertEqual(credential.access_token, DUMMY_TOKEN)

    def test_mark_reconnect_needed_is_idempotent(self):
        self._store().action_mark_reconnect_needed()
        self._store().action_mark_reconnect_needed()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')

    # ------------------------------------------------------------------
    # action_test_connection auto-transition wiring
    # ------------------------------------------------------------------

    def test_test_connection_auth_failure_sets_reconnect_needed(self):
        self._set_token()
        self.store.write({'state': 'connected'})
        response = FakeResponse(200, json_body={
            'errors': [{
                'message': 'Access denied',
                'extensions': {'code': 'ACCESS_DENIED'},
            }],
        })
        self._run_test_connection(response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self._get_credential().credential_state, 'invalid')

    def test_test_connection_shop_state_failure_also_sets_reconnect_needed(self):
        self._set_token()
        self.store.write({'state': 'connected'})
        response = FakeResponse(423, text='Locked')
        self._run_test_connection(response)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        # A shop-state failure never flips credential_state (unchanged
        # Task 003 behavior).
        self.assertEqual(self._get_credential().credential_state, 'present')

    def test_test_connection_success_does_not_auto_activate(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        self._run_test_connection(response)
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')

    # ------------------------------------------------------------------
    # action_reconnect
    # ------------------------------------------------------------------

    def test_reconnect_missing_credential_does_not_connect(self):
        # ChatGPT review (PR #121): with no credential present,
        # action_reconnect() must not raise after writing state/audit --
        # a raised exception in normal Odoo RPC/service execution can
        # roll back those very writes. It persists reconnect_needed +
        # the audit job and returns None instead.
        self.assertFalse(self.store.credential_present)
        result = self._store().action_reconnect()
        self.assertIsNone(result)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertFalse(self.store.credential_present)
        self.assertEqual(len(self._audit_jobs()), 1)
        test_connection_jobs = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_test_connection'),
        ])
        self.assertFalse(test_connection_jobs)
        readiness_jobs = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_readiness_check'),
        ])
        self.assertFalse(readiness_jobs)

    def test_reconnect_connects_when_both_pass(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        call_log = self._run_reconnect(response, 'pass')
        self.assertEqual(call_log, [self.store.id])
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertEqual(self.store.last_readiness_result, 'pass')

    def test_reconnect_connects_with_readiness_warning(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        self._run_reconnect(response, 'warning')
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')

    def test_reconnect_remains_reconnect_needed_when_evidence_fails(self):
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        call_log = self._run_reconnect(response, 'fail')
        self.assertEqual(call_log, [self.store.id])
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertNotEqual(self.store.state, 'connected')

    def test_reconnect_remains_reconnect_needed_on_test_connection_failure(self):
        self._set_token()
        response = FakeResponse(423, text='Locked')
        self._run_reconnect(response, 'pass')
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        # A shop-state/auth-classified test-connection failure is already
        # handled by action_test_connection()'s own auto-transition
        # (action_mark_reconnect_needed) -- action_reconnect() must not
        # redundantly re-write the state and create a second audit job
        # for the same logical attempt.
        self.assertEqual(len(self._audit_jobs()), 1)

    def test_reconnect_does_not_double_audit_on_credential_invalid_failure(self):
        self._set_token()
        response = FakeResponse(200, json_body={
            'errors': [{
                'message': 'Access denied',
                'extensions': {'code': 'ACCESS_DENIED'},
            }],
        })
        self._run_reconnect(response, 'pass')
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(len(self._audit_jobs()), 1)

    def test_reconnect_audits_once_on_identity_mismatch_failure(self):
        # Identity mismatch (odoo_validation_configuration) is NOT an
        # auth-classified failure, so action_test_connection() does not
        # auto-transition -- action_reconnect()'s own else-branch must
        # still fire exactly once to move the store to reconnect_needed.
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain='different-shop.myshopify.com')
        )
        self._run_reconnect(response, 'pass')
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(len(self._audit_jobs()), 1)

    # ------------------------------------------------------------------
    # CORE-R2 (AR-047; review 4690639375 #2): reconnect_probe vs test_connection
    # ------------------------------------------------------------------

    def test_reconnect_from_completed_disconnected_connects(self):
        # Reconnect after a completed disconnect (state 'disconnected', a
        # credential re-entered) must work via purpose='reconnect_probe'.
        self._set_token()
        response = FakeResponse(
            200, json_body=_success_body(domain=self.store.shop_domain)
        )
        self._run_reconnect(response, 'pass', entry_state='disconnected')
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')

    def test_test_connection_refused_from_disconnected(self):
        # Ordinary Test Connection uses purpose='test_connection', whose matrix
        # excludes 'disconnected' -> refused (Reconnect is the recovery path).
        self._set_token()
        self.store.write({'state': 'disconnected'})
        with self.assertRaises(UserError):
            self._store().action_test_connection()
        # No dangling test-connection job was created by the refused attempt.
        self.assertFalse(self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_test_connection'),
        ]))

    # ------------------------------------------------------------------
    # No secret leakage across lifecycle actions
    # ------------------------------------------------------------------

    def test_no_secret_leakage_across_lifecycle_actions(self):
        self._set_token()
        self._seed_verified_evidence()
        self._store().action_activate()
        self._store().action_disconnect()
        jobs = self.Job.search([('store_id', '=', self.store.id)])
        logs = self.JobLog.search([('job_id', 'in', jobs.ids)])
        for recordset in (self.store, jobs, logs):
            fields_info = recordset.fields_get()
            for field_name, info in fields_info.items():
                if info['type'] not in ('char', 'text'):
                    continue
                for rec in recordset:
                    value = rec[field_name]
                    if value:
                        self.assertNotIn(DUMMY_TOKEN, value)
