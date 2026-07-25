import ast
import inspect
import textwrap
import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models import shopify_connector_job_dispatch as dispatch_module
from ..models.shopify_connector_mutation_attempt import canonical_sha256
from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


def _direct_statement_call_indices(function_node, predicate):
    """Return only direct expression-statement calls in a function body."""
    matches = []
    for index, statement in enumerate(function_node.body):
        if not isinstance(statement, ast.Expr):
            continue
        value = statement.value
        if isinstance(value, ast.Call) and predicate(value):
            matches.append(index)
    return matches


# Issue #193 / #157 -- DOCUMENTED EXEMPTION from the post_install test-phase
# contract (docs/05-qa/odoo19-test-phase-contract.md), recorded in
# `test_phase_contract.EXEMPTIONS`.
#
# `test_synthetic_registry_is_complete_and_domain_neutral` asserts that the CORE
# mutation registry carries no domain strategy -- that is a module-boundary
# assertion which is only meaningful while `shopify_connector_core` is loaded and
# the inventory/fulfillment modules are not. Moving it to post_install makes the
# assertion vacuous-then-false: every module is loaded, so `inventory_*` and
# `fulfillment_*` strategies are legitimately registered and the test fails.
#
# The exemption is safe because this class's fixtures create only connector-owned
# rows (store/job/job.log). It creates no res.users, res.partner or
# product.template, so it cannot hit the #193 NOT NULL family. Verified by the
# runtime baseline: this class was green in the pre-correction warm run.
@tagged('at_install', '-post_install')
class TestMutationDispatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 dispatch test',
            'shop_domain': 'layer2-dispatch-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Job = cls.env['shopify.connector.job']

    def _job(self, **extra):
        values = {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                self.store.connection_generation,
            'state': 'queued',
            'payload_hash': uuid.uuid4().hex,
        }
        values.update(extra)
        return self.Job.sudo().create(values)

    def test_synthetic_registry_is_complete_and_domain_neutral(self):
        handlers = self.Dispatch._get_handlers()
        policies = self.Dispatch._get_replay_policies()
        strategies = self.Dispatch._get_reconciliation_strategies()
        self.assertIn('mutation_dispatch_selftest', strategies)
        self.assertIn('mutation_dispatch_selftest', handlers)
        self.assertIn('mutation_dispatch_selftest', policies)
        strategy = strategies['mutation_dispatch_selftest']
        self.assertEqual(strategy['reconciliation_job_type'],
            'mutation_dispatch_selftest_reconcile',
        )
        self.assertEqual(set(strategy), dispatch_module.MUTATION_STRATEGY_KEYS)
        self.assertNotIn('inventory', ' '.join(strategies))
        self.assertNotIn('fulfillment', ' '.join(strategies))

    def test_request_fingerprints_separate_business_and_transport(self):
        job = self._job()
        strategy = self.Dispatch._validated_mutation_strategy(job.job_type)
        local = strategy['prepare_local'](job)
        first = strategy['prepare_preconditions'](local, {
            'job_id': job.id,
            'attempt_token': uuid.uuid4().hex,
        })
        second = dict(first)
        second['shopify_idempotency_key'] = uuid.uuid4().hex
        second['variables'] = dict(first['variables'])
        second['variables']['idempotencyKey'] = (
            second['shopify_idempotency_key']
        )
        self.assertEqual(
            canonical_sha256(first['business_intent']),
            canonical_sha256(second['business_intent']),
        )
        self.assertNotEqual(
            canonical_sha256({
                'operation': first['operation'],
                'variables': first['variables'],
            }),
            canonical_sha256({
                'operation': second['operation'],
                'variables': second['variables'],
            }),
        )

    def test_idempotency_and_throttle_classification(self):
        cases = {
            'IDEMPOTENCY_CONCURRENT_REQUEST': (
                'uncertain', 'concurrency_race_conflict', False, 'reconcile',
            ),
            'THROTTLED': (
                'uncertain', 'shopify_throttling_rate_limit',
                False, 'reconcile',
            ),
            'IDEMPOTENCY_KEY_PARAMETER_MISMATCH': (
                'uncertain', 'idempotency_contract_violation',
                'idempotency_contract_violation', 'block_manual_review',
            ),
            'IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED': (
                'uncertain', 'idempotency_contract_violation',
                'idempotency_contract_violation', 'block_manual_review',
            ),
        }
        for code, expected in cases.items():
            evidence = {'request_id': code.lower()}
            result = self.Dispatch._classify_direct_mutation_selftest({
                'error_code': code,
                'evidence': evidence,
            })
            self.assertEqual((
                result['observed_outcome'], result['error_class'],
                result['manual_review_subreason'], result['action'],
            ), expected)
            self.assertEqual(result['evidence'], evidence)
            self.assertNotIn('retry', result['action'])

    def test_malformed_strategy_and_consequence_fail_closed(self):
        with patch.object(
            type(self.Dispatch), '_get_reconciliation_strategies',
            return_value={'bad': {'transport': lambda *_args: None}},
        ):
            with self.assertRaises(ValidationError):
                self.Dispatch._validated_mutation_strategy('bad')
        with self.assertRaises(ValidationError):
            self.Dispatch._validate_job_consequence({
                'observed_outcome': 'failed_clean',
                'error_class': 'unknown_unregistered_value',
                'manual_review_subreason': False,
                'action': 'retry',
                'message': 'forbidden retry',
                'evidence': {},
            }, 'direct')

    def test_registered_consequences_have_no_same_job_retry_action(self):
        failed_clean = self.Dispatch._validate_job_consequence({
            'observed_outcome': 'failed_clean',
            'error_class': 'shopify_user_errors_validation',
            'manual_review_subreason': False,
            'action': 'fail_final',
            'message': 'Synthetic clean refusal.',
            'evidence': {},
        }, 'direct')
        not_applied = self.Dispatch._validate_reconciliation_result({
            'verdict': 'not_applied',
            'observed_store_identity': self.store.shop_domain,
            'action': 'cancel',
            'error_class': False,
            'manual_review_subreason': False,
            'message': 'Synthetic read proved not applied.',
            'evidence': {},
        })
        self.assertEqual(failed_clean['action'], 'fail_final')
        self.assertEqual(not_applied['consequence']['action'], 'cancel')
        self.assertNotIn('retry', dispatch_module.DIRECT_ACTIONS)
        self.assertNotIn('retry', dispatch_module.RECONCILIATION_ACTIONS)

    def test_layer2_sequence_commits_before_precondition_and_transport(self):
        source = textwrap.dedent(inspect.getsource(
            dispatch_module.ShopifyConnectorJobDispatch._drain_mutation_one
        ))
        fn = ast.parse(source).body[0]

        def call_line(predicate):
            matches = [
                node.lineno for node in ast.walk(fn)
                if isinstance(node, ast.Call) and predicate(node)
            ]
            self.assertEqual(len(matches), 1)
            return matches[0]

        strategy_call = lambda key: (
            lambda call: isinstance(call.func, ast.Subscript)
            and isinstance(call.func.slice, ast.Constant)
            and call.func.slice.value == key
        )
        direct_commit = _direct_statement_call_indices(
            fn,
            lambda call: isinstance(call.func, ast.Attribute)
            and call.func.attr == 'commit',
        )
        self.assertEqual(len(direct_commit), 1)
        positions = [
            call_line(strategy_call('prepare_local')),
            fn.body[direct_commit[0]].lineno,
            call_line(strategy_call('prepare_preconditions')),
            call_line(
                lambda call: isinstance(call.func, ast.Attribute)
                and call.func.attr == '_commit_attempt_intent_c2'
            ),
            call_line(strategy_call('transport')),
            call_line(
                lambda call: isinstance(call.func, ast.Attribute)
                and call.func.attr == '_commit_mutation_outcome_c3'
            ),
        ]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(set(positions)), len(positions))
        DispatchClass = dispatch_module.ShopifyConnectorJobDispatch
        c2_source = inspect.getsource(
            DispatchClass._commit_attempt_intent_c2
        )
        c3_source = inspect.getsource(
            DispatchClass._commit_mutation_outcome_c3
        )
        self.assertIn('self.env.registry.cursor()', c2_source)
        self.assertIn('side_cr.commit()', c2_source)
        self.assertIn('side_cr.close()', c2_source)
        self.assertIn('self.env.transaction.reset()', c3_source)
        self.assertNotIn('except BaseException', source)

    def test_direct_commit_detector_ignores_nested_recovery_commits(self):
        fn = ast.parse(textwrap.dedent('''
            def sample(self):
                self.prepare_local()
                self.env.cr.commit()
                try:
                    self.prepare_preconditions()
                except Exception:
                    self.env.cr.commit()
                if self.needs_recovery:
                    self.env.cr.commit()
                with self.recovery_context():
                    self.env.cr.commit()
        ''')).body[0]
        matches = _direct_statement_call_indices(
            fn,
            lambda call: isinstance(call.func, ast.Attribute)
            and call.func.attr == 'commit',
        )
        self.assertEqual(matches, [1])
        direct_statement = fn.body[matches[0]]
        self.assertIsInstance(direct_statement, ast.Expr)
        self.assertEqual(
            ast.unparse(direct_statement.value), 'self.env.cr.commit()'
        )
        all_commit_calls = [
            node for node in ast.walk(fn)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'commit'
        ]
        self.assertEqual(len(all_commit_calls), 4)

    def test_reconciliation_pending_gate_blocks_claim(self):
        job = self._job(
            reconciliation_pending_until=(
                fields.Datetime.now() + dispatch_module.timedelta(hours=1)
            ),
        )
        self.assertNotIn(job, self.Job._claim_for_dispatch(20))

    def test_existing_attempt_evidence_blocks_redispatch_before_c1(self):
        token = uuid.uuid4().hex
        job = self._job(
            state='running', current_attempt_token=token,
            owner_worker_ref='evidence:1',
            running_since=fields.Datetime.now(),
        )
        self.env['shopify.connector.mutation.attempt'].with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation':
                self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        with patch.object(
            type(self.Dispatch), '_transport_mutation_dispatch_selftest',
            side_effect=AssertionError('transport must not run'),
        ) as transport:
            blocked = self.Dispatch._preflight_existing_attempt_evidence(job)
        self.assertTrue(blocked)
        transport.assert_not_called()
        self.assertEqual(self.env[
            'shopify.connector.mutation.attempt'
        ].search_count([('job_id', '=', job.id)]), 1)
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'duplicate_risk')

    def test_non_mutation_dispatch_path_remains_present(self):
        source = inspect.getsource(
            dispatch_module.ShopifyConnectorJobDispatch._drain_one
        )
        self.assertIn('self._dispatch_one(claimed)', source)
        self.assertIn('self._drain_mutation_one(claimed)', source)
