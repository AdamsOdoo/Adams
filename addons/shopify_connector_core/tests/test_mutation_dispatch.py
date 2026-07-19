import inspect
import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..models import shopify_connector_job_dispatch as dispatch_module
from ..models.shopify_connector_mutation_attempt import canonical_sha256
from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


class TestMutationDispatch(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 dispatch test',
            'shop_domain': 'layer2-dispatch-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
        })
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Job = cls.env['shopify.connector.job']

    def _job(self, **extra):
        values = {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
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
        for code in ('IDEMPOTENCY_CONCURRENT_REQUEST', 'THROTTLED'):
            self.assertEqual(
                self.Dispatch._classify_direct_mutation_selftest(
                    {'error_code': code}
                )['observed_outcome'], 'uncertain',
            )
        for code in (
            'IDEMPOTENCY_KEY_PARAMETER_MISMATCH',
            'IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED',
        ):
            self.assertEqual(
                self.Dispatch._classify_direct_mutation_selftest(
                    {'error_code': code}
                )['action'], 'block_manual_review',
            )

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

    def test_layer2_sequence_commits_before_precondition_and_transport(self):
        source = inspect.getsource(
            dispatch_module.ShopifyConnectorJobDispatch._drain_mutation_one
        )
        positions = [source.index(token) for token in (
            "strategy['prepare_local']", 'self.env.cr.commit()',
            "strategy['prepare_preconditions']",
            'self._commit_attempt_intent_c2', "strategy['transport']",
            'self._commit_mutation_outcome_c3',
        )]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn('except BaseException', source)

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
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        self.Dispatch._drain_mutation_one(job)
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'duplicate_risk')

    def test_non_mutation_dispatch_path_remains_present(self):
        source = inspect.getsource(
            dispatch_module.ShopifyConnectorJobDispatch._drain_one
        )
        self.assertIn('self._dispatch_one(claimed)', source)
        self.assertIn('self._drain_mutation_one(claimed)', source)
