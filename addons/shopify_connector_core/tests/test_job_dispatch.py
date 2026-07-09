import ast
import os
import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class TestJobDispatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Job Dispatch Test Store',
            'shop_domain': 'job-dispatch-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']

    def _create_selftest_job(
        self, job_source='setup_readiness_check', state='queued', **extra,
    ):
        vals = {
            'store_id': self.store.id,
            'job_source': job_source,
            'job_type': 'core_dispatch_selftest',
            'state': state,
            'payload_hash': str(uuid.uuid4()),
        }
        vals.update(extra)
        return self.Job.create(vals)

    def _logs_for(self, job):
        return self.JobLog.search([('job_id', '=', job.id)], order='id asc')

    # ------------------------------------------------------------------
    # Execution claim guard (code-level proof only -- NOT a claim of
    # real concurrent-worker safety; TransactionCase cannot exercise
    # real concurrent workers, per sync-engine-open-questions.md open
    # question 24).
    # ------------------------------------------------------------------

    def test_claim_locks_and_returns_uncontended_queued_jobs(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        claimed = self.Job._claim_for_dispatch(20)
        self.assertIn(job.id, claimed.ids)

    def test_claim_returns_due_retry_waiting_jobs(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(
            state='retry_waiting',
            next_retry_at=fields.Datetime.now() - timedelta(seconds=1),
            retry_count=1,
        )
        claimed = self.Job._claim_for_dispatch(20)
        self.assertIn(job.id, claimed.ids)

    def test_claim_excludes_not_yet_due_retry_waiting_jobs(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(
            state='retry_waiting',
            next_retry_at=fields.Datetime.now() + timedelta(hours=1),
            retry_count=1,
        )
        claimed = self.Job._claim_for_dispatch(20)
        self.assertNotIn(job.id, claimed.ids)

    def test_claim_excludes_running_and_terminal_jobs(self):
        self.store.write({'state': 'connected'})
        running_job = self._create_selftest_job(state='running')
        succeeded_job = self._create_selftest_job(state='succeeded')
        claimed = self.Job._claim_for_dispatch(20)
        self.assertNotIn(running_job.id, claimed.ids)
        self.assertNotIn(succeeded_job.id, claimed.ids)

    def test_claim_never_returns_more_than_limit(self):
        self.store.write({'state': 'connected'})
        for _ in range(3):
            self._create_selftest_job(state='queued')
        claimed = self.Job._claim_for_dispatch(2)
        self.assertLessEqual(len(claimed), 2)

    def test_claim_skips_row_already_locked_by_a_concurrent_attempt(self):
        """Code-level proof only. Stubs `try_lock_for_update()` to
        return only a subset of the candidate rows -- exactly the
        contract Odoo's own official "Writing cron functions"
        documentation describes for that method (silently skip an
        already-locked row via SKIP LOCKED) -- proving
        `_claim_for_dispatch()` treats an unlocked row as "not claimed
        this pass," never an error, and never claims it anyway. This
        does not, and cannot, prove real multi-worker/multi-server
        safety -- see the Task 006C gate-opening proposal §4/§8.
        """
        self.store.write({'state': 'connected'})
        job_a = self._create_selftest_job(state='queued')
        job_b = self._create_selftest_job(state='queued')

        def fake_try_lock_for_update(recordset):
            # Simulate job_b already being locked by a concurrent
            # drain-loop claim attempt: only job_a's lock succeeds.
            return recordset.filtered(lambda j: j.id == job_a.id)

        with patch.object(
            type(self.Job), 'try_lock_for_update', fake_try_lock_for_update,
        ):
            claimed = self.Job._claim_for_dispatch(20)
        self.assertEqual(claimed.ids, [job_a.id])
        self.assertNotIn(job_b.id, claimed.ids)

    def test_claim_all_rows_locked_returns_empty_not_an_error(self):
        self.store.write({'state': 'connected'})
        self._create_selftest_job(state='queued')

        def fake_try_lock_for_update(recordset):
            return recordset.browse()

        with patch.object(
            type(self.Job), 'try_lock_for_update', fake_try_lock_for_update,
        ):
            claimed = self.Job._claim_for_dispatch(20)
        self.assertFalse(claimed)

    # ------------------------------------------------------------------
    # Handler registry dispatch (extension seam) + missing handler.
    # ------------------------------------------------------------------

    def test_core_handler_runs_and_succeeds_without_override(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        self.assertTrue(job.finished_at)
        logs = self._logs_for(job)
        self.assertTrue(any(log.to_state == 'succeeded' for log in logs))

    def test_extension_seam_overrides_handler_without_modifying_core(self):
        """Mirrors the existing
        test_extension_seam_registers_check_without_modifying_core
        precedent: classic `_inherit` + `super()` + dict-merge, never a
        wholesale replacement of the registry method's own contract."""
        DispatchModel = self.env.registry['shopify.connector.job.dispatch']
        original_get_handlers = DispatchModel._get_handlers
        calls = []

        def _extended_get_handlers(self):
            handlers = dict(original_get_handlers(self))
            handlers['core_dispatch_selftest'] = (
                lambda job: calls.append(job.id)
            )
            return handlers

        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        with patch.object(
            DispatchModel, '_get_handlers', _extended_get_handlers,
        ):
            self.Dispatch.run_drain(20)
        self.assertEqual(calls, [job.id])
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')

    def test_missing_handler_fails_safely_to_failed_final(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        with patch.object(
            type(self.Dispatch), '_get_handlers', lambda self: {},
        ):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(job.error_class, 'unknown_system_error')

    # ------------------------------------------------------------------
    # Execution-time store-state recheck (checkpoint 3, SRR-03
    # narrowing) -- extends test_business_job_running_blocked_when_
    # not_connected to the new dispatch code path.
    # ------------------------------------------------------------------

    def test_execution_time_store_state_recheck_skips_when_disconnected_between_start_and_dispatch(self):
        self.store.write({'state': 'connected'})
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': 'core_dispatch_selftest',
            'state': 'draft',
            'payload_hash': str(uuid.uuid4()),
        })
        self.assertTrue(self.Dispatch._start_running(job))
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')

        # The exact race checkpoint 3 narrows: the store disconnects
        # strictly between the start-running transition (checkpoint 2)
        # and the handler being invoked.
        self.store.write({'state': 'disconnected'})
        calls = []
        with patch.object(
            type(self.Dispatch), '_get_handlers',
            lambda self: {
                'core_dispatch_selftest': lambda job: calls.append(job.id),
            },
        ):
            self.Dispatch._invoke_handler(job)
        self.assertEqual(calls, [])
        job.invalidate_recordset()
        self.assertEqual(job.state, 'skipped')

    def test_execution_time_store_state_recheck_does_not_gate_core_sources(self):
        # core_dispatch_selftest under a core (non-business) job_source
        # is never gated by store state, even at checkpoint 3 --
        # unchanged behavior for the three pre-existing core job_types.
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(
            job_source='setup_readiness_check', state='draft',
        )
        self.assertTrue(self.Dispatch._start_running(job))
        self.store.write({'state': 'disconnected'})
        self.Dispatch._invoke_handler(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')

    # ------------------------------------------------------------------
    # Start-gating (checkpoint 2) failures are visible and audited, not
    # silent -- a job blocked at start time must not remain indefinitely
    # queued/retry_waiting with no observable outcome.
    # ------------------------------------------------------------------

    def test_start_running_blocked_by_store_state_becomes_visible_audited(self):
        self.store.write({'state': 'connected'})
        job = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': 'core_dispatch_selftest',
            'state': 'draft',
            'payload_hash': str(uuid.uuid4()),
        })
        # The store disconnects strictly before the start-running
        # transition is even attempted (unlike the checkpoint-3 tests
        # above, which disconnect strictly after it succeeds).
        self.store.write({'state': 'disconnected'})
        result = self.Dispatch._start_running(job)
        self.assertFalse(result)
        job.invalidate_recordset()
        self.assertNotIn(job.state, ('queued', 'retry_waiting', 'draft'))
        self.assertEqual(job.state, 'failed_retryable')
        self.assertEqual(job.error_class, 'odoo_validation_configuration')
        self.assertTrue(job.finished_at)
        logs = self._logs_for(job)
        self.assertTrue(logs)
        self.assertTrue(
            any(log.to_state == 'failed_retryable' for log in logs)
        )

    def test_start_running_blocked_by_domain_flag_becomes_visible_audited(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='draft')
        JobModel = self.env.registry['shopify.connector.job']

        def _fake_domain_flag_for_job_type(self, job_type):
            return 'product_domain_enabled'

        with patch.object(
            JobModel, '_domain_flag_for_job_type',
            _fake_domain_flag_for_job_type,
        ):
            result = self.Dispatch._start_running(job)
        self.assertFalse(result)
        job.invalidate_recordset()
        self.assertNotIn(job.state, ('queued', 'retry_waiting', 'draft'))
        self.assertEqual(job.state, 'failed_retryable')
        self.assertEqual(job.error_class, 'odoo_validation_configuration')
        self.assertTrue(job.finished_at)
        logs = self._logs_for(job)
        self.assertTrue(logs)
        self.assertTrue(
            any(log.to_state == 'failed_retryable' for log in logs)
        )

    # ------------------------------------------------------------------
    # Execution-time domain-enabled recheck (fail-safe only, DEC-013
    # §I.3) -- synthetic/test-only flag mapping, never a live domain
    # flag, per implementation-scope §F item 5.
    # ------------------------------------------------------------------

    def test_execution_time_domain_enabled_recheck_blocks_and_unblocks_start(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='draft')
        JobModel = self.env.registry['shopify.connector.job']

        def _fake_domain_flag_for_job_type(self, job_type):
            if job_type == 'core_dispatch_selftest':
                return 'product_domain_enabled'
            return None

        with patch.object(
            JobModel, '_domain_flag_for_job_type',
            _fake_domain_flag_for_job_type,
        ):
            with self.assertRaises(ValidationError):
                job.write({'state': 'running'})
            job.invalidate_recordset()
            self.assertEqual(job.state, 'draft')

            self.env['shopify.connector.store.settings'].create({
                'store_id': self.store.id,
                'product_domain_enabled': True,
            })
            job.write({'state': 'running'})
        self.assertEqual(job.state, 'running')

    def test_execution_time_domain_enabled_recheck_never_alters_enqueue_time_decision(self):
        # The hook only runs inside write()'s state -> 'running' branch
        # -- create() is completely untouched by it, proving it cannot
        # alter an enqueue-time decision.
        self.store.write({'state': 'disconnected'})
        JobModel = self.env.registry['shopify.connector.job']

        def _fake_domain_flag_for_job_type(self, job_type):
            return 'product_domain_enabled'

        with patch.object(
            JobModel, '_domain_flag_for_job_type',
            _fake_domain_flag_for_job_type,
        ):
            # A core (non-business) source is still creatable while
            # disconnected -- the hook does not run at create() time at
            # all, so this must succeed exactly as before.
            job = self._create_selftest_job(
                job_source='setup_readiness_check', state='draft',
            )
        self.assertTrue(job.id)

    def test_domain_flag_defaults_to_none_for_every_shipped_job_type(self):
        Job = self.Job
        for job_type in (
            'core_readiness_check', 'core_manual_maintenance',
            'core_test_connection', 'core_dispatch_selftest',
        ):
            self.assertIsNone(Job._domain_flag_for_job_type(job_type))

    # ------------------------------------------------------------------
    # Disconnect cancels/blocks jobs reachable via the new dispatcher
    # states -- extends test_disconnect_cancels_non_terminal_business_
    # jobs; action_disconnect() itself is unmodified.
    # ------------------------------------------------------------------

    def test_disconnect_cancels_business_jobs_in_new_dispatch_states(self):
        self.store.write({'state': 'connected'})
        scenarios = (
            ('retry_waiting', {
                'next_retry_at': fields.Datetime.now(), 'retry_count': 1,
            }),
            ('failed_retryable', {}),
            ('blocked_manual_review', {
                'manual_review_subreason': 'ambiguous_match',
            }),
        )
        for state, extra in scenarios:
            self.store.write({'state': 'connected'})
            job = self.Job.create({
                'store_id': self.store.id,
                'job_source': 'manual_sync',
                'job_type': 'core_dispatch_selftest',
                'state': 'draft',
                'payload_hash': str(uuid.uuid4()),
            })
            job.write(dict({'state': state}, **extra))
            self.store.action_disconnect()
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled', state)

    # ------------------------------------------------------------------
    # Logs appended through sanctioned path only + no direct
    # job.log.create() call anywhere in the new code (source-level).
    # ------------------------------------------------------------------

    def test_every_dispatch_write_path_logs_via_system_append(self):
        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')
        self.Dispatch.run_drain(20)
        logs = self._logs_for(job)
        self.assertGreaterEqual(len(logs), 2)
        self.assertEqual(logs.mapped('event_type'), ['attempt', 'attempt'])

    def _find_new_model_files(self):
        return (
            os.path.join(self._models_dir(), 'shopify_connector_job_enqueue.py'),
            os.path.join(self._models_dir(), 'shopify_connector_job_dispatch.py'),
        )

    def _changed_production_files(self):
        # All three production Python files this task touches, including
        # the modified (not merely new) shopify_connector_job.py -- used
        # by guards that must cover every changed file, not only the two
        # brand-new ones (e.g. the no-live-Shopify-call guard below).
        return (
            os.path.join(self._models_dir(), 'shopify_connector_job.py'),
        ) + self._find_new_model_files()

    def _models_dir(self):
        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )

    def _env_model_name(self, value_node):
        if not isinstance(value_node, ast.Subscript):
            return None
        slice_node = value_node.slice
        if isinstance(slice_node, ast.Constant):
            return slice_node.value
        return None

    def test_source_level_job_dispatch_never_calls_create(self):
        """AST guard: shopify_connector_job_dispatch.py never calls
        `.create(` on anything -- every write path goes through
        job.write()/state-transition helpers and
        job.log._system_append() only."""
        path = os.path.join(
            self._models_dir(), 'shopify_connector_job_dispatch.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=path)
        offenders = [
            node for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'create'
            )
        ]
        self.assertEqual(offenders, [])

    def test_source_level_job_enqueue_only_creates_job_model(self):
        """AST guard: shopify_connector_job_enqueue.py's only `.create(`
        call targets `shopify.connector.job` -- never job.log, never
        anything else."""
        path = os.path.join(
            self._models_dir(), 'shopify_connector_job_enqueue.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=path)
        create_targets = []
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'create'
            ):
                create_targets.append(self._env_model_name(node.func.value))
        self.assertEqual(create_targets, ['shopify.connector.job'])

    def test_source_level_no_sudo_in_new_files(self):
        """No new sudo() site is introduced -- the existing
        test_source_level_two_sudo_sites_total guard (test_job_log_
        system_append.py) already fixes the total at exactly two
        pre-existing sites; this is a same-guarantee, targeted check on
        just this task's own new files."""
        for path in self._find_new_model_files():
            with open(path, 'r', encoding='utf-8') as source_file:
                tree = ast.parse(source_file.read(), filename=path)
            offenders = [
                node for node in ast.walk(tree)
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'sudo'
                )
            ]
            self.assertEqual(offenders, [], path)

    # ------------------------------------------------------------------
    # No live Shopify call anywhere in this task's changed production
    # files (source-level).
    # ------------------------------------------------------------------

    def test_source_level_no_shopify_api_client_reference_in_changed_production_files(self):
        """Stronger than a per-test mocking sample: none of this task's
        three changed production files -- the modified
        shopify_connector_job.py, and the two new
        shopify_connector_job_enqueue.py/shopify_connector_job_
        dispatch.py -- references the Shopify API client at all, so no
        test exercising them could reach a live call regardless of what
        any individual test does or does not mock. (The test files
        themselves legitimately reference `shopify.connector.api.client`
        in order to patch/assert it is never called -- mirroring
        `test_readiness_check_never_calls_shopify_api_client` -- so they
        are intentionally not scanned here; see
        test_no_live_shopify_call_during_a_real_drain_run and
        test_job_enqueue.py's own equivalent for the corresponding
        behavioral proof.)
        """
        for path in self._changed_production_files():
            with open(path, 'r', encoding='utf-8') as source_file:
                content = source_file.read()
            self.assertNotIn('shopify.connector.api.client', content, path)
            self.assertNotIn('.execute(', content, path)

    def test_no_live_shopify_call_during_a_real_drain_run(self):
        Client = self.env['shopify.connector.api.client']

        def _fail_if_called(self, store, query, variables=None):
            raise AssertionError(
                'Dispatch must never call the Shopify API client.'
            )

        self.store.write({'state': 'connected'})
        self._create_selftest_job(state='queued')
        with patch.object(type(Client), 'execute', _fail_if_called):
            self.Dispatch.run_drain(20)

    # ------------------------------------------------------------------
    # Secrets redacted.
    # ------------------------------------------------------------------

    def test_secrets_redacted_in_dispatch_failure_path(self):
        from ..models.shopify_connector_job_dispatch import JobHandlerError

        self.store.write({'state': 'connected'})
        job = self._create_selftest_job(state='queued')

        def _raise_with_secret(self, job):
            raise JobHandlerError(
                'unknown_system_error',
                'failure mentioning token %s' % DUMMY_TOKEN,
                technical_detail='detail mentioning token %s' % DUMMY_TOKEN,
            )

        with patch.object(
            type(self.Dispatch), '_get_handlers',
            lambda self: {'core_dispatch_selftest': _raise_with_secret},
        ):
            self.Dispatch.run_drain(20)
        job.invalidate_recordset()
        logs = self._logs_for(job)
        for recordset in (job, logs):
            fields_info = recordset.fields_get()
            for field_name, info in fields_info.items():
                if info['type'] not in ('char', 'text'):
                    continue
                for rec in recordset:
                    value = rec[field_name]
                    if value:
                        self.assertNotIn(DUMMY_TOKEN, value)
