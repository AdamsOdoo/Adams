import uuid
from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


class TestMutationRetention(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 retention test',
            'shop_domain': 'layer2-retention-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.Retention = cls.env['shopify.connector.pii.retention']
        cls.admin = cls.env['res.users'].create({
            'name': 'Layer 2 retention administrator',
            'login': 'layer2_retention_admin_%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref(
                    'shopify_connector_core.'
                    'group_shopify_connector_admin'
                ).id,
            ])],
        })

    def _attempt(self, outcome='succeeded'):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                self.store.connection_generation,
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
        })
        attempt = self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {'target': 'gid://synthetic/1'},
            'preconditions_snapshot': {'quantity': 1},
            'remote_evidence_refs': {'request_id': 'synthetic'},
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        attempt._record_direct_outcome(outcome)
        return attempt

    def test_mask_preserves_identity_and_outcomes(self):
        attempt = self._attempt()
        identity = attempt.read([
            'job_id', 'attempt_token', 'mutation_domain',
            'business_intent_fingerprint', 'exact_request_fingerprint',
            'observed_outcome',
        ])[0]
        attempt._mask_terminal_evidence()
        self.assertEqual(attempt.remote_mutation_intent, {'masked': True})
        self.assertEqual(attempt.preconditions_snapshot, {'masked': True})
        self.assertEqual(attempt.remote_evidence_refs, {'masked': True})
        after = attempt.read(list(identity))[0]
        self.assertEqual(identity, after)

    def test_resolved_uncertain_is_masked_after_window(self):
        attempt = self._attempt('uncertain')
        attempt._record_recovery_uncertain(
            'post_c2_owner_recovery', 'dispatcher_recovery',
        )
        attempt._record_inconclusive_reconciliation({
            'read_ref': 'synthetic',
        })
        attempt.with_user(self.admin).action_resolve_mutation_attempt(
            'applied', 'Synthetic external evidence.'
        )
        before = attempt.remote_evidence_refs
        self.assertEqual(set(before), {
            'direct', 'recovery', 'reconciliation', 'manual_resolution',
        })
        self.assertTrue(before['manual_resolution'])
        self.assertTrue(before['recovery'])
        self.assertTrue(before['reconciliation'])
        self.env.cr.execute(
            'UPDATE shopify_connector_mutation_attempt '
            'SET resolved_at = %s WHERE id = %s',
            (fields.Datetime.now() - timedelta(days=181), attempt.id),
        )
        attempt.invalidate_recordset()
        preserved_fields = [
            'job_id', 'attempt_token', 'mutation_domain',
            'business_intent_fingerprint', 'exact_request_fingerprint',
            'observed_outcome', 'resolution_disposition',
            'resolution_source', 'resolution_reason', 'resolution_uid',
            'resolution_at', 'resolved_at',
        ]
        preserved = attempt.read(preserved_fields)[0]
        self.assertEqual(self.Retention._run_attempt_evidence_masking(), 1)
        self.assertEqual(attempt.remote_mutation_intent, {'masked': True})
        self.assertEqual(attempt.read(preserved_fields)[0], preserved)
        self.assertTrue(attempt.exists())

    def test_unresolved_uncertain_is_never_masked(self):
        attempt = self._attempt('uncertain')
        before = attempt.remote_mutation_intent
        attempt._mask_terminal_evidence()
        self.assertEqual(attempt.remote_mutation_intent, before)

    def test_retention_default_and_invalid_override(self):
        params = self.env['ir.config_parameter'].sudo()
        self.assertEqual(self.Retention._attempt_evidence_retention_days(), 180)
        for value in ('invalid', '0', '-1'):
            params.set_param(
                'shopify_connector.layer2_attempt_evidence_retention_days',
                value,
            )
            self.assertEqual(
                self.Retention._attempt_evidence_retention_days(), 180
            )
        params.set_param(
            'shopify_connector.layer2_attempt_evidence_retention_days', '7'
        )
        self.assertEqual(self.Retention._attempt_evidence_retention_days(), 7)
