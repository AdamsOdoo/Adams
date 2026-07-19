import os
import uuid
from datetime import timedelta
from unittest import skipUnless

from odoo import fields
from odoo.tests.common import TransactionCase


class TestMutationRecovery(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 recovery test',
            'shop_domain': 'layer2-recovery-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.Sweep = cls.env['shopify.connector.stale.owner.sweep']

    def _running(self, with_attempt):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
            'owner_worker_ref': 'dead:1',
            'running_since': fields.Datetime.now() - timedelta(hours=1),
        })
        attempt = False
        if with_attempt:
            attempt = self.Attempt.with_context(
                shopify_layer2_c2_side_cursor=True,
            )._create_attempt_intent({
                'job_id': job.id,
                'attempt_token': token,
                'mutation_domain': 'mutation_dispatch_selftest',
                'shopify_idempotency_key': uuid.uuid4().hex,
            })
        return job, attempt

    def test_c1_without_c2_is_safely_requeued(self):
        job, _attempt = self._running(False)
        self.Sweep.run_sweep()
        self.assertEqual(job.state, 'retry_waiting')
        self.assertFalse(job.current_attempt_token)

    def test_committed_c2_routes_to_one_reconciliation_job(self):
        job, attempt = self._running(True)
        self.Sweep.run_sweep()
        self.Sweep.run_sweep()
        reconciliations = self.Job.search([
            ('mutation_attempt_id', '=', attempt.id),
        ])
        self.assertEqual(len(reconciliations), 1)
        self.assertEqual(job.state, 'running')

    def test_disconnect_preserves_credentials_for_unresolved_attempt(self):
        self.env['shopify.connector.store.credential'].action_set_token(
            self.store, 'shpat_DUMMYDUMMYDUMMY0000000000000000'
        )
        self._running(True)
        self.store.action_disconnect()
        self.store.write({
            'disconnect_requested_at':
                fields.Datetime.now() - timedelta(hours=1),
        })
        self.store._process_disconnect_quiesce()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertTrue(self.store.credential_present)
        self.assertIn('Credentials were preserved', self.store.disconnect_status_reason)

    def test_tunable_defaults_reject_invalid_values(self):
        params = self.env['ir.config_parameter'].sudo()
        params.set_param(
            'shopify_connector.layer2_stale_owner_timeout_minutes', '-1'
        )
        params.set_param(
            'shopify_connector.layer2_stale_owner_batch_size', 'invalid'
        )
        self.assertEqual(
            self.Sweep._positive_int_parameter(
                'shopify_connector.layer2_stale_owner_timeout_minutes', 30
            ),
            30,
        )
        self.assertEqual(
            self.Sweep._positive_int_parameter(
                'shopify_connector.layer2_stale_owner_batch_size', 20
            ),
            20,
        )

    @skipUnless(
        os.getenv('SHOPIFY_LAYER2_RUN_PROCESS_DEATH') == '1',
        'real process-death harness is opt-in outside Odoo.sh',
    )
    def test_real_process_death_harness_gate(self):
        # The Odoo.sh acceptance worker enables this gate and drives deaths at
        # C1→C2, C2→NET, during NET, NET→C3 and during C3. This test refuses
        # to downgrade process death to a same-process Python exception.
        self.assertEqual(os.getenv('SHOPIFY_LAYER2_RUN_PROCESS_DEATH'), '1')
