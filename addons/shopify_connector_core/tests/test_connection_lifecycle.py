import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_job import BUSINESS_JOB_SOURCES, TERMINAL_JOB_STATES
from .test_api_client import FakeResponse, _success_body

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
CORE_JOB_SOURCES_NOT_GATED = ('setup_readiness_check', 'export_preview_dry_run')
NON_CONNECTED_STATES = ('setup_incomplete', 'reconnect_needed', 'disconnected')


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
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', lambda self, store, body: response):
            return self._store().action_test_connection()

    def _run_reconnect(self, test_connection_response, readiness_result, call_log=None):
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
            type(Client), '_send', lambda self, store, body: test_connection_response
        ), patch.object(
            type(ReadinessCheck), 'run_for_store', fake_run_for_store
        ):
            self._store().action_reconnect()
        return call_log

    # ------------------------------------------------------------------
    # action_activate
    # ------------------------------------------------------------------

    def test_activate_succeeds_with_pass_and_pass(self):
        self._set_token()
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': fields.Datetime.now(),
        })
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
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'warning',
            'credential_last_verified_at': fields.Datetime.now(),
        })
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
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': fields.Datetime.now(),
        })
        self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'connected')

        self._store().action_disconnect()
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
        # ChatGPT review (PR #121): action_replace_token clears
        # credential_last_verified_at on every token swap but does not
        # reset last_test_connection_result/last_readiness_result, so a
        # replaced token could otherwise activate on pass/pass evidence
        # recorded for the PREVIOUS token -- exactly the "never infer
        # connection success" violation credential_last_verified_at
        # exists to close.
        self._set_token()
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': fields.Datetime.now(),
        })
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
        # The stale mirrors are untouched by the token replacement --
        # still 'pass'/'pass', but they no longer describe the current
        # credential.
        self.assertEqual(self.store.last_test_connection_result, 'pass')
        self.assertEqual(self.store.last_readiness_result, 'pass')

        with self.assertRaises(UserError):
            self._store().action_activate()
        self.store.invalidate_recordset()
        self.assertNotEqual(self.store.state, 'connected')
        self.assertEqual(len(self._audit_jobs()), len(audit_jobs_before))

    # ------------------------------------------------------------------
    # action_disconnect
    # ------------------------------------------------------------------

    def test_disconnect_clears_credential_value(self):
        self._set_token()
        self._store().action_disconnect()
        credential = self._get_credential()
        self.assertFalse(credential.access_token)
        self.assertEqual(credential.credential_state, 'absent')
        self.store.invalidate_recordset()
        self.assertFalse(self.store.credential_present)

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
        self.store.write({'state': 'connected'})
        self._store().action_disconnect()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnected')

    def test_disconnect_cancels_non_terminal_business_jobs(self):
        self.store.write({'state': 'connected'})
        jobs = [
            self._create_job('manual_sync', state='draft'),
            self._create_job('webhook', state='queued'),
            self._create_job('scheduled_sync', state='running'),
        ]
        self._store().action_disconnect()
        for job in jobs:
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled')
            self.assertEqual(job.cancel_reason, 'Store disconnected.')
            self.assertTrue(job.finished_at)
            logs = self._logs_for(job)
            cancel_logs = logs.filtered(lambda l: l.to_state == 'cancelled')
            self.assertTrue(cancel_logs)
            self.assertEqual(cancel_logs[0].event_type, 'state_change')

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
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='draft')
        self._store().action_disconnect()
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        logs_after_first = self._logs_for(job)
        audit_count_after_first = len(self._audit_jobs())

        # Second call must not raise, must not re-touch the already-
        # cancelled job, and must not corrupt the credential mirror.
        self._store().action_disconnect()
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnected')
        job.invalidate_recordset()
        self.assertEqual(job.state, 'cancelled')
        self.assertEqual(len(self._logs_for(job)), len(logs_after_first))
        credential = self._get_credential()
        self.assertFalse(credential.access_token)
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
        job = self._create_job('manual_sync', state='draft')
        # Race: the store disconnects after enqueue but before start.
        self.store.write({'state': 'disconnected'})
        with self.assertRaises(ValidationError):
            job.write({'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'draft')

    def test_business_job_running_succeeds_when_connected(self):
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='draft')
        job.write({'state': 'running'})
        self.assertEqual(job.state, 'running')

    def test_business_job_running_blocked_when_job_source_changed_in_same_write(self):
        # A job created under a core (ungated) source must not be able
        # to bypass the gate by changing job_source to a business source
        # in the very same write() call that also sets state='running'.
        self.store.write({'state': 'disconnected'})
        job = self._create_job(
            'setup_readiness_check', job_type='core_manual_maintenance',
            state='draft',
        )
        with self.assertRaises(ValidationError):
            job.write({'job_source': 'manual_sync', 'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'draft')

    def test_business_job_running_blocked_when_store_id_changed_in_same_write(self):
        # Symmetric bypass attempt via store_id instead of job_source.
        other_store = self.env['shopify.connector.store'].create({
            'name': 'Other Disconnected Store',
            'shop_domain': 'other-disconnected-store.myshopify.com',
            'api_version': '2026-07',
            'state': 'disconnected',
        })
        self.store.write({'state': 'connected'})
        job = self._create_job('manual_sync', state='draft')
        with self.assertRaises(ValidationError):
            job.write({'store_id': other_store.id, 'state': 'running'})
        job.invalidate_recordset()
        self.assertEqual(job.state, 'draft')

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
            state='draft',
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
    # No secret leakage across lifecycle actions
    # ------------------------------------------------------------------

    def test_no_secret_leakage_across_lifecycle_actions(self):
        self._set_token()
        self.store.write({
            'last_test_connection_result': 'pass',
            'last_readiness_result': 'pass',
            'credential_last_verified_at': fields.Datetime.now(),
        })
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
