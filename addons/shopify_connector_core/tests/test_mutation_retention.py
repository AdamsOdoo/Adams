import uuid
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestMutationRetention(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 retention test',
            'shop_domain': 'layer2-retention-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']
        cls.Retention = cls.env['shopify.connector.pii.retention']

    def _attempt(self, outcome='succeeded'):
        token = uuid.uuid4().hex
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': token,
        })
        attempt = self.Attempt.with_context(
            shopify_layer2_c2_side_cursor=True,
        )._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': 'mutation_dispatch_selftest',
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

    def test_uncertain_attempt_is_never_masked_even_after_resolution(self):
        attempt = self._attempt('uncertain')
        before = attempt.remote_mutation_intent
        attempt._surface('action_resolve_mutation_attempt').write({
            'resolution_disposition': 'applied',
            'resolution_source': 'manual_admin',
            'resolution_reason': 'synthetic evidence',
            'resolution_uid': self.env.uid,
            'resolution_at': fields.Datetime.now(),
        })
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
