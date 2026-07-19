import uuid
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


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
        attempt = self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
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

    def test_resolution_preserves_direct_and_appends_read_evidence(self):
        job, attempt, reconciliation = self._fixture()
        direct = attempt.remote_evidence_refs['direct']
        attempt._record_reconciliation_result(
            'applied', evidence={'read': 'synthetic'},
        )
        self.assertEqual(attempt.effective_disposition(), 'applied')
        self.assertEqual(job.state, 'running')
        self.assertEqual(attempt.resolution_source, 'reconciliation_read')
        self.assertEqual(attempt.remote_evidence_refs['direct'], direct)
        self.assertEqual(len(
            attempt.remote_evidence_refs['reconciliation']
        ), 1)
        self.assertEqual(reconciliation.state, 'running')

    def test_not_applied_resolution_never_requeues_same_job(self):
        job, attempt, _reconciliation = self._fixture()
        attempt._record_reconciliation_result('not_applied', {})
        self.assertEqual(attempt.effective_disposition(), 'not_applied')
        self.assertEqual(job.state, 'running')

    def test_inconclusive_cap_is_per_attempt_and_fail_closed(self):
        job, attempt, reconciliation = self._fixture()
        for count in range(1, 4):
            if reconciliation.state != 'running':
                reconciliation.sudo().write({'state': 'running'})
            self.assertEqual(
                attempt._record_inconclusive_reconciliation({
                    'read': 'synthetic', 'count': count,
                }),
                count,
            )
        self.assertEqual(job.state, 'running')
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

    def test_store_identity_mismatch_blocks_original_without_verdict(self):
        job, attempt, reconciliation = self._fixture()
        Dispatch = self.env['shopify.connector.job.dispatch']
        strategy = dict(Dispatch._get_reconciliation_strategies()[
            attempt.mutation_domain
        ])
        strategy['reconcile'] = lambda _attempt: {
            'verdict': 'applied',
            'observed_store_identity': 'different-shop.myshopify.com',
            'action': 'succeed',
            'error_class': False,
            'manual_review_subreason': False,
            'message': 'Synthetic mismatched identity.',
            'evidence': {'read': 'synthetic'},
        }
        with patch.object(
            type(Dispatch), '_get_reconciliation_strategies',
            return_value={attempt.mutation_domain: strategy},
        ):
            Dispatch._handle_mutation_dispatch_selftest_reconcile(
                reconciliation
            )
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.error_class, 'store_identity_mismatch')
        self.assertFalse(attempt.resolution_disposition)

    def test_missing_strategy_routes_original_job_not_read_job(self):
        job, attempt, reconciliation = self._fixture()
        Dispatch = self.env['shopify.connector.job.dispatch']
        with patch.object(
            type(Dispatch), '_get_reconciliation_strategies',
            return_value={},
        ):
            Dispatch._handle_mutation_dispatch_selftest_reconcile(
                reconciliation
            )
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.error_class, 'no_reconciliation_strategy')
        self.assertEqual(reconciliation.state, 'running')
        self.assertFalse(attempt.resolution_disposition)

    def test_callback_failure_rolls_back_job_and_created_child(self):
        job, attempt, reconciliation = self._fixture()
        Dispatch = self.env['shopify.connector.job.dispatch']
        strategy = dict(Dispatch._get_reconciliation_strategies()[
            attempt.mutation_domain
        ])
        marker = 'callback-child:%s' % uuid.uuid4().hex

        def failing_callback(*_args, **_kwargs):
            self.Job.sudo().create({
                'store_id': self.store.id,
                'job_source': 'setup_readiness_check',
                'job_type': 'setup_readiness_check',
                'state': 'queued',
                'payload_hash': marker,
            })
            raise RuntimeError('synthetic callback rollback')

        strategy['apply_consequence'] = failing_callback
        consequence = {
            'observed_outcome': 'uncertain',
            'error_class': False,
            'manual_review_subreason': False,
            'action': 'succeed',
            'message': 'Synthetic applied verdict.',
            'evidence': {},
        }
        with self.assertRaises(RuntimeError):
            with self.env.cr.savepoint():
                Dispatch._apply_validated_consequence(
                    job, attempt, 'reconciliation', consequence, strategy,
                    reconciliation_job=reconciliation,
                )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.Job.search_count([
            ('payload_hash', '=', marker),
        ]))

    def test_historic_reconciliation_keeps_attempt_evidence_link(self):
        _job, attempt, reconciliation = self._fixture()
        reconciliation.sudo().write({'job_type': 'historic_domain_job'})
        self.assertEqual(reconciliation.mutation_attempt_id, attempt)
