"""Framework-free source contracts for the shared V2 mutation seam."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE_MODELS = ROOT / 'addons' / 'shopify_connector_core' / 'models'
INVENTORY_MODELS = ROOT / 'addons' / 'shopify_connector_inventory' / 'models'
WEBHOOK_MODELS = ROOT / 'addons' / 'shopify_connector_webhook' / 'models'


def _source(path):
    return path.read_text(encoding='utf-8')


def _method(source, name):
    tree = ast.parse(source)
    return next(
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == name
    )


class TestV2MutationSeam(unittest.TestCase):

    def test_protected_models_contain_no_shared_v2_dispatch_or_identity(self):
        dispatch = _source(CORE_MODELS / 'shopify_connector_job_dispatch.py')
        attempt = _source(
            CORE_MODELS / 'shopify_connector_mutation_attempt.py'
        )
        for name in (
            '_get_v2_job_types', '_get_v2_mutation_job_types',
            '_v2_admit_mutation_job', '_v2_scope_mismatch',
            'expected_configuration_generation',
        ):
            self.assertNotIn(name, dispatch if 'job' in name else attempt)
        self.assertNotIn('run_id = fields.Many2one', attempt)

    def test_identity_extension_owns_server_derived_fields_and_c2(self):
        source = _source(
            CORE_MODELS / 'shopify_connector_mutation_attempt_v2_runtime.py'
        )
        self.assertIn("_inherit = 'shopify.connector.mutation.attempt'", source)
        self.assertIn('run_id = fields.Many2one', source)
        self.assertIn('expected_configuration_generation = fields.Integer', source)
        self.assertIn("values['run_id'] = run.id", source)
        self.assertIn("values['expected_configuration_generation']", source)
        self.assertIn("_v2_admit_mutation_job(job, phase='c2')", source)
        self.assertIn("'run_id', 'expected_configuration_generation'", source)

    def test_dispatch_seam_fences_c1_c3_and_keeps_network_out(self):
        path = CORE_MODELS / 'shopify_connector_v2_mutation_dispatch.py'
        source = _source(path)
        self.assertIn("_inherit = 'shopify.connector.job.dispatch'", source)
        for name in (
            '_get_v2_job_types', '_get_v2_mutation_job_types',
            '_v2_admit_mutation_job', '_block_v2_admission',
        ):
            self.assertIn('def %s' % name, source)
        c1 = ast.get_source_segment(source, _method(source, '_drain_mutation_one'))
        c3 = ast.get_source_segment(
            source, _method(source, '_apply_validated_consequence')
        )
        self.assertLess(
            c1.index("_v2_admit_mutation_job(job, phase='c1')"),
            c1.index('super()._drain_mutation_one'),
        )
        self.assertLess(
            c3.index("phase='c3'"), c3.index('super()._apply_validated_consequence'),
        )
        for forbidden in ('execute_business', 'requests.', 'graphql'):
            self.assertNotIn(forbidden, source)
        self.assertIn('_v2_assert_transport_admission', source)
        transport = ast.get_source_segment(
            source, _method(source, '_validated_mutation_strategy')
        )
        self.assertLess(
            transport.index('_v2_assert_transport_admission'),
            transport.index("return transport(request, attempt_context)"),
        )
        self.assertIn("side_cr.commit()", ast.get_source_segment(
            source, _method(source, '_v2_assert_transport_admission')
        ))
        c3_source = ast.get_source_segment(
            source, _method(source, '_commit_mutation_outcome_c3')
        )
        self.assertIn('_v2_force_reconcile_consequence', c3_source)
        self.assertIn("'uncertain'", c3_source)
        self.assertIn("'direct', forced", c3_source)

    def test_claim_and_stale_sweep_are_additive_and_no_replay(self):
        claim = _source(CORE_MODELS / 'shopify_connector_v2_runtime.py')
        sweep = _source(CORE_MODELS / 'shopify_connector_stale_owner_sweep.py')
        self.assertIn("('run_id', '=', False)", claim)
        self.assertIn("('run_id', '!=', False)", claim)
        self.assertIn("('job_type', 'in', v2_types)", claim)
        self.assertIn("_recover_committed_attempt_to_reconciliation", sweep)
        self.assertIn("'stale_owner_post_c2'", sweep)
        self.assertIn("'Stale V2 owner had no committed attempt; safely requeued.'", sweep)
        self.assertIn('attempt.transport_attempted', sweep)
        self.assertIn("'retry_waiting'", sweep)
        sweep_method = ast.get_source_segment(
            sweep, _method(sweep, '_sweep_v2_mutation_owners')
        )
        self.assertLess(
            sweep_method.index("attempt = Attempt.search"),
            sweep_method.index("_v2_admit_mutation_job(job, phase='stale')"),
        )
        self.assertLess(
            sweep_method.index("if attempt:"),
            sweep_method.index("_v2_admit_mutation_job(job, phase='stale')"),
        )
        self.assertIn("('mutation_domain', 'in'", sweep_method)
        self.assertIn("attempt_candidates.mapped('job_id')", sweep_method)
        self.assertNotIn("('attempt_token', '=', job.current_attempt_token)", sweep_method)

    def test_c2_identity_is_canonicalized_from_locked_store(self):
        attempt = _source(
            CORE_MODELS / 'shopify_connector_mutation_attempt_v2_runtime.py'
        )
        dispatch = _source(CORE_MODELS / 'shopify_connector_v2_mutation_dispatch.py')
        self.assertIn('_v2_locked_scope(job)', attempt)
        self.assertIn("store.connection_generation", attempt)
        self.assertIn("store.shop_domain", attempt)
        self.assertIn("The mutation attempt connection snapshot is stale.", attempt)
        self.assertIn("The mutation attempt store identity is stale.", attempt)
        self.assertIn("Prepared V2 connection generation is stale.", dispatch)
        self.assertIn("Prepared V2 store identity is stale.", dispatch)
        gate = ast.get_source_segment(
            dispatch, _method(dispatch, '_v2_assert_transport_admission')
        )
        self.assertIn('_v2_admit_mutation_job', gate)
        scope = _source(
            CORE_MODELS / 'shopify_connector_mutation_attempt_v2_runtime.py'
        )
        for field in (
            'current_attempt_token', 'attempt_token', 'mutation_domain',
            'transport_attempted', 'expected_connection_generation',
            'expected_configuration_generation',
        ):
            self.assertIn(field, gate if field in {
                'current_attempt_token', 'attempt_token', 'mutation_domain',
                'transport_attempted',
            } else scope)
        classifier = ast.get_source_segment(
            dispatch, _method(dispatch, '_is_v2_mutation_job')
        )
        self.assertIn("attempt.mutation_domain in registered", classifier)
        self.assertIn("getattr(attempt, 'run_id', False)", classifier)
        self.assertIn("getattr(job, 'lane', False)", classifier)
        mismatch = ast.get_source_segment(
            scope, _method(scope, '_v2_scope_mismatch')
        )
        self.assertIn("attempt.mutation_domain != job.job_type", mismatch)
        self.assertIn("job.run_id != run", mismatch)

    def test_api_client_rechecks_full_fence_at_real_send_stage(self):
        extension = _source(
            CORE_MODELS / 'shopify_connector_api_client_v2_runtime.py'
        )
        self.assertIn(
            "_inherit = 'shopify.connector.api.client'", extension,
        )
        self.assertIn('def _v2_admit_mutation_side', extension)
        self.assertIn('def _admit_mutation', extension)
        self.assertIn("phase='c2', attempt=attempt", extension)
        self.assertIn('_v2_assert_transport_admission', extension)
        side = ast.get_source_segment(
            extension, _method(extension, '_v2_admit_mutation_side')
        )
        for field in (
            'owner_worker_ref', 'current_attempt_token', 'attempt_token',
            'mutation_domain', 'transport_attempted',
            'expected_connection_generation',
            'expected_configuration_generation',
            'expected_store_identity',
        ):
            self.assertIn(field, side)
        admit = ast.get_source_segment(
            extension, _method(extension, '_admit_mutation')
        )
        self.assertLess(
            admit.index('_v2_admit_mutation_side'),
            admit.index('super()._admit_mutation'),
        )
        self.assertLess(
            extension.index('side_cr.commit()'),
            extension.index('def _validate_graphql_operation'),
        )
        validation = ast.get_source_segment(
            extension, _method(extension, '_validate_graphql_operation')
        )
        self.assertLess(
            validation.index('super()._validate_graphql_operation'),
            validation.index('_v2_assert_transport_admission'),
        )
        client = _source(CORE_MODELS / 'shopify_connector_api_client.py')
        send = ast.get_source_segment(client, _method(client, '_send'))
        self.assertLess(
            send.index('self._validate_graphql_operation'),
            send.index('requests.post'),
        )
        self.assertIn("job, attempt=attempt", extension)

    def test_v2_admission_proves_lineage_before_credential_access(self):
        extension = _source(
            CORE_MODELS / 'shopify_connector_api_client_v2_runtime.py'
        )
        mutation = ast.get_source_segment(
            extension, _method(extension, '_v2_admit_mutation_side')
        )
        self.assertLess(
            mutation.index('_v2_preflight_mutation_lineage'),
            mutation.index('_ensure_access_token'),
        )
        self.assertLess(
            mutation.index('_v2_mutation_lineage_matches'),
            mutation.index('_get_access_token'),
        )
        reconciliation = ast.get_source_segment(
            extension, _method(extension, '_admit_v2_reconciliation_read')
        )
        self.assertLess(
            reconciliation.index('_v2_preflight_reconciliation_lineage'),
            reconciliation.index('_ensure_access_token'),
        )
        self.assertNotIn('browse(store_id)', reconciliation)
        self.assertNotIn('expected_connection_generation', reconciliation)
        preflight = ast.get_source_segment(
            extension,
            _method(extension, '_v2_preflight_reconciliation_lineage'),
        )
        self.assertIn('_v2_reconciliation_lineage_matches', preflight)
        self.assertIn("attempt.observed_outcome == 'uncertain'", extension)

    def test_queued_v2_c2_evidence_has_one_reconciliation_recovery_path(self):
        dispatch = _source(
            CORE_MODELS / 'shopify_connector_v2_mutation_dispatch.py'
        )
        recovery = ast.get_source_segment(
            dispatch, _method(dispatch, '_v2_recover_queued_c2_attempt')
        )
        candidate = ast.get_source_segment(
            dispatch, _method(dispatch, '_v2_queued_c2_attempt')
        )
        drain = ast.get_source_segment(
            dispatch, _method(dispatch, '_drain_mutation_one')
        )
        generic = ast.get_source_segment(
            dispatch, _method(dispatch, '_dispatch_one')
        )
        self.assertIn('def _v2_queued_c2_attempt', dispatch)
        self.assertIn('transport_attempted is True', candidate)
        self.assertIn("observed_outcome in ('pending', 'uncertain')", candidate)
        self.assertIn('_recover_committed_attempt_to_reconciliation', recovery)
        self.assertIn("('mutation_attempt_id', '=', attempt.id)", recovery)
        self.assertIn('Malformed durable V2 C2 evidence', recovery)
        self.assertLess(
            drain.index('_v2_recover_queued_c2_attempt'),
            drain.index("phase='c1'"),
        )
        self.assertIn('_v2_recover_queued_c2_attempt', generic)
        admission = ast.get_source_segment(
            dispatch, _method(dispatch, '_v2_admit_mutation_job')
        )
        self.assertLess(
            admission.index('_v2_queued_c2_attempt'),
            admission.index('_is_v2_mutation_job'),
        )

    def test_reconciliation_uses_durable_lineage_and_query_only_admission(self):
        dispatch = _source(
            CORE_MODELS / 'shopify_connector_v2_mutation_dispatch.py'
        )
        ensure = ast.get_source_segment(
            dispatch, _method(dispatch, '_ensure_reconciliation_job')
        )
        self.assertIn("getattr(attempt, 'run_id', False)", ensure)
        self.assertIn("store.connection_generation", ensure)
        self.assertIn("settings.configuration_generation", ensure)

        readback = _source(
            WEBHOOK_MODELS
            / 'shopify_connector_webhook_subscription_v2_reconciliation.py'
        )
        delegate = ast.get_source_segment(
            readback, _method(readback, 'read')
        )
        self.assertIn('_execute_v2_reconciliation_read', delegate)
        reconcile = ast.get_source_segment(
            readback, _method(readback, '_reconcile_subscription_mutation')
        )
        self.assertIn('if not attempt.run_id', reconcile)
        self.assertIn('_v2_assert_reconciliation_readback', reconcile)
        self.assertNotIn('_v2_assert_job', reconcile)

        client = _source(
            CORE_MODELS / 'shopify_connector_api_client_v2_runtime.py'
        )
        admission = ast.get_source_segment(
            client, _method(client, '_admit_v2_reconciliation_read')
        )
        self.assertIn("attempt.expected_store_identity", admission)
        self.assertIn("attempt.observed_outcome != 'uncertain'", admission)
        self.assertNotIn('v2_runtime_mode', admission)
        self.assertNotIn('expected_connection_generation', admission)

    def test_manual_resolution_and_p11_reconciliation_lock_job_before_attempt(self):
        """The mutation lock root is always the original job.

        These are source-level guards for a deadlock class that a dependency-
        free suite cannot reproduce with PostgreSQL.  C2/C3/recovery already
        acquire job -> attempt; manual resolution and P11 reconciliation must
        not acquire the attempt first and then write the job.
        """
        attempt_source = _source(
            CORE_MODELS / 'shopify_connector_mutation_attempt.py'
        )
        action = ast.get_source_segment(
            attempt_source,
            _method(attempt_source, 'action_resolve_mutation_attempt'),
        )
        identity_source = _source(
            CORE_MODELS / 'shopify_connector_mutation_attempt_v2_runtime.py'
        )
        lock_helper = ast.get_source_segment(
            identity_source,
            _method(identity_source, '_lock_with_original_job'),
        )
        lock_calls = sorted(
            (
                node.lineno,
                ast.unparse(node.func.value),
            )
            for node in ast.walk(ast.parse(lock_helper))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'try_lock_for_update'
            )
        )
        self.assertGreaterEqual(len(lock_calls), 2)
        self.assertIn("Job = self.env['shopify.connector.job']", lock_helper)
        self.assertEqual(lock_calls[0][1], 'Job.browse(original_job.id).sudo()')
        self.assertEqual(lock_calls[1][1], 'self.sudo()')
        self.assertIn('self._lock_with_original_job(self.job_id)', action)
        self.assertNotIn('attempt = self.try_lock_for_update()', action)
        self.assertNotIn('reconciliation_jobs', action)
        self.assertNotIn("('mutation_attempt_id', '=', attempt.id)", action)
        self.assertIn('durable cancellation authority', action)

        dispatch_source = _source(
            CORE_MODELS / 'shopify_connector_job_dispatch.py'
        )
        reconcile = ast.get_source_segment(
            dispatch_source,
            _method(
                dispatch_source,
                '_handle_mutation_dispatch_selftest_reconcile',
            ),
        )
        original_lock = reconcile.index(
            'attempt._lock_with_original_job(original)'
        )
        first_attempt_state_read = reconcile.index(
            'attempt.effective_disposition()'
        )
        self.assertLess(original_lock, first_attempt_state_read)
        self.assertIn('original, attempt = locked_lineage', reconcile)

        p11_path = (
            WEBHOOK_MODELS
            / 'shopify_connector_webhook_subscription_v2_dispatch.py'
        )
        p11_source = _source(p11_path)
        ensure = ast.get_source_segment(
            p11_source, _method(p11_source, '_ensure_reconciliation_job'),
        )
        p11_locks = sorted(
            (
                node.lineno,
                ast.unparse(node.func.value),
            )
            for node in ast.walk(ast.parse(ensure))
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'try_lock_for_update'
            )
        )
        self.assertGreaterEqual(len(p11_locks), 2)
        self.assertEqual(p11_locks[0][1], 'Job.browse(original_job.id).sudo()')
        self.assertIn('shopify.connector.mutation.attempt', p11_locks[1][1])
        self.assertLess(
            ensure.index('locked_original_job'),
            ensure.index('locked_attempt'),
        )

        # The generic and inventory reconciliation seams must obey the same
        # order.  The P11 override is not the only caller: a direct recovery
        # or inventory-domain call must not reintroduce attempt -> original.
        core_ensure = ast.get_source_segment(
            dispatch_source,
            _method(dispatch_source, '_ensure_reconciliation_job'),
        )
        self.assertIn(
            'attempt._lock_with_original_job(original_job)', core_ensure,
        )
        for path in (
            INVENTORY_MODELS / 'shopify_connector_inventory_service.py',
        ):
            source = _source(path)
            generic_ensure = ast.get_source_segment(
                source, _method(source, '_ensure_reconciliation_job'),
            )
            generic_locks = sorted(
                (
                    node.lineno,
                    ast.unparse(node.func.value),
                )
                for node in ast.walk(ast.parse(generic_ensure))
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'try_lock_for_update'
                )
            )
            with self.subTest(path=path.name):
                self.assertGreaterEqual(len(generic_locks), 2)
                self.assertEqual(
                    generic_locks[0][1], 'Job.browse(original_job.id)',
                )
                self.assertIn(
                    'shopify.connector.mutation.attempt',
                    generic_locks[1][1],
                )
                self.assertLess(
                    generic_ensure.index('locked_original_job'),
                    generic_ensure.index('locked_attempt'),
                )

    def test_p11_run_projection_uses_blocking_run_lock_after_scope_locks(self):
        """Concurrent terminal projectors serialize their shared run state."""
        p11_source = _source(
            WEBHOOK_MODELS
            / 'shopify_connector_webhook_subscription_v2_dispatch.py'
        )
        projection = ast.get_source_segment(
            p11_source, _method(p11_source, '_v2_project_run'),
        )
        self.assertIn('WHERE id = %s FOR UPDATE', projection)
        self.assertNotIn('FOR UPDATE SKIP LOCKED', projection)
        self.assertLess(
            projection.index('flush_model'),
            projection.index('FOR UPDATE'),
        )
        self.assertLess(
            projection.index('FOR UPDATE'),
            projection.index('SELECT state, COUNT(*)'),
        )

    def test_durable_attempt_blocks_generic_redispatch(self):
        source = _source(
            CORE_MODELS / 'shopify_connector_v2_mutation_dispatch.py'
        )
        dispatch = ast.get_source_segment(
            source, _method(source, '_dispatch_one')
        )
        self.assertLess(
            dispatch.index("('run_id', '!=', False)"),
            dispatch.index('super()._dispatch_one'),
        )
        self.assertIn('_recover_committed_attempt_to_reconciliation', dispatch)

    def test_live_retry_never_schedules_beyond_the_window(self):
        source = _source(CORE_MODELS / 'shopify_connector_job_dispatch.py')
        method = ast.get_source_segment(
            source, _method(source, '_schedule_retry_or_fail')
        )
        self.assertEqual(method.count('now = fields.Datetime.now()'), 1)
        self.assertIn('timedelta(seconds=RETRY_WINDOW_SECONDS)', method)
        self.assertIn('if next_retry_at > deadline:', method)

    def test_p11_registration_is_super_additive_and_subscription_scoped(self):
        source = _source(
            WEBHOOK_MODELS
            / 'shopify_connector_webhook_subscription_v2_dispatch.py'
        )
        self.assertIn('frozenset(super()._get_v2_job_types())', source)
        self.assertIn('frozenset(super()._get_v2_mutation_job_types())', source)
        self.assertIn('V2_SUBSCRIPTION_MUTATIONS', source)
        self.assertIn('return super()._claimable_domain', source)
        self.assertIn('super()._sweep_v2_mutation_owners', source)
        self.assertNotIn("('run_id', '=', False)", source)


if __name__ == '__main__':
    unittest.main()
