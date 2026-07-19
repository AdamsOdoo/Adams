import uuid

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestMutationReconciliation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 reconciliation test',
            'shop_domain': 'layer2-reconcile-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']

    def _fixture(self):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
            'owner_worker_ref': 'test:1',
            'running_since': fields.Datetime.now(),
        })
        attempt = self.Attempt.with_context(
            shopify_layer2_c2_side_cursor=True,
        )._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': 'mutation_dispatch_selftest',
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        attempt._record_direct_outcome('uncertain')
        reconciliation = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'mutation_dispatch_selftest_reconcile',
            'state': 'running',
            'payload_hash': 'reconcile:%s' % token,
            'mutation_attempt_id': attempt.id,
        })
        return job, attempt, reconciliation

    def test_applied_resolution_completes_without_resend(self):
        job, attempt, reconciliation = self._fixture()
        attempt._record_reconciliation_result(
            'applied', False, evidence={'read': 'synthetic'},
        )
        self.assertEqual(attempt.effective_disposition(), 'applied')
        self.assertEqual(job.state, 'succeeded')
        self.assertEqual(attempt.resolution_source, 'reconciliation_read')
        self.assertEqual(reconciliation.state, 'running')

    def test_not_applied_resolution_makes_new_attempt_eligible(self):
        job, attempt, _reconciliation = self._fixture()
        attempt._record_reconciliation_result('not_applied', False)
        self.assertEqual(attempt.effective_disposition(), 'not_applied')
        self.assertEqual(job.state, 'retry_waiting')
        self.assertFalse(job.reconciliation_pending_until)

    def test_inconclusive_cap_is_per_attempt_and_fail_closed(self):
        job, attempt, reconciliation = self._fixture()
        for count in range(1, 4):
            if reconciliation.state != 'running':
                reconciliation.sudo().write({'state': 'running'})
            self.assertEqual(
                attempt._record_inconclusive_reconciliation(reconciliation),
                count,
            )
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'duplicate_risk')
        self.assertFalse(attempt.resolution_disposition)

    def test_exact_reconciliation_link_is_required(self):
        with self.assertRaises(ValidationError):
            self.Job.sudo().create({
                'store_id': self.store.id,
                'job_source': 'reconciliation',
                'job_type': 'mutation_dispatch_selftest_reconcile',
                'state': 'queued',
                'payload_hash': uuid.uuid4().hex,
            })
