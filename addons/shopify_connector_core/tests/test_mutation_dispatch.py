import inspect
import uuid

from odoo import fields
from odoo.tests.common import TransactionCase

from ..models import shopify_connector_job_dispatch as dispatch_module
from ..models.shopify_connector_mutation_attempt import canonical_sha256


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
        self.assertEqual(
            strategies['mutation_dispatch_selftest'][
                'reconciliation_job_type'
            ],
            'mutation_dispatch_selftest_reconcile',
        )
        self.assertNotIn('inventory', ' '.join(strategies))
        self.assertNotIn('fulfillment', ' '.join(strategies))

    def test_request_fingerprints_separate_business_and_transport(self):
        job = self._job()
        first = self.Dispatch._prepare_mutation_dispatch_selftest(job)
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
                self.Dispatch._classify_mutation_result(
                    {'error_code': code}
                ),
                'uncertain',
            )
        for code in (
            'IDEMPOTENCY_KEY_PARAMETER_MISMATCH',
            'IDEMPOTENCY_PREVIOUS_ATTEMPT_FAILED',
        ):
            self.assertEqual(
                self.Dispatch._classify_mutation_result(
                    {'error_code': code}
                ),
                'contract_violation',
            )

    def test_reconciliation_pending_gate_blocks_claim(self):
        job = self._job(
            reconciliation_pending_until=(
                fields.Datetime.now() + dispatch_module.timedelta(hours=1)
            ),
        )
        self.assertNotIn(job, self.Job._claim_for_dispatch(20))

    def test_non_mutation_dispatch_path_remains_present(self):
        source = inspect.getsource(
            dispatch_module.ShopifyConnectorJobDispatch._drain_one
        )
        self.assertIn('self._dispatch_one(claimed)', source)
        self.assertIn('self._drain_mutation_one(claimed)', source)
