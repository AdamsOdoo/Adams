import uuid

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import canonical_sha256


class TestMutationAttempt(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 attempt test',
            'shop_domain': 'layer2-attempt-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
        })
        cls.job = cls.env['shopify.connector.job'].sudo().create({
            'store_id': cls.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': 'attempt-token',
            'owner_worker_ref': 'test:1',
            'running_since': fields.Datetime.now(),
        })
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']

    def _create(self, token='attempt-token'):
        return self.Attempt.with_context(
            shopify_layer2_c2_side_cursor=True,
        )._create_attempt_intent({
            'job_id': self.job.id,
            'attempt_token': token,
            'mutation_domain': 'mutation_dispatch_selftest',
            'expected_connection_generation': 0,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {'job_id': self.job.id},
            'preconditions_snapshot': {'generation': 0},
            'business_intent_fingerprint': canonical_sha256({'a': 1}),
            'exact_request_fingerprint': canonical_sha256({'b': 2}),
            'shopify_idempotency_key': uuid.uuid4().hex,
        })

    def test_exact_schema_and_attempt_owned_transport(self):
        attempt = self._create()
        self.assertEqual(attempt.job_id, self.job)
        self.assertEqual(attempt.store_id, self.store)
        self.assertTrue(attempt.transport_attempted)
        self.assertEqual(attempt.observed_outcome, 'pending')
        self.assertTrue(attempt.transport_at)
        self.assertTrue(attempt.idempotency_valid_until)
        self.assertEqual(
            attempt.idempotency_valid_until - attempt.transport_at,
            fields.Datetime.to_datetime('1970-01-01 23:00:00')
            - fields.Datetime.to_datetime('1970-01-01 00:00:00'),
        )

    def test_canonical_fingerprint_is_key_order_independent(self):
        self.assertEqual(
            canonical_sha256({'a': 1, 'b': [2, 3]}),
            canonical_sha256({'b': [2, 3], 'a': 1}),
        )
        self.assertNotEqual(
            canonical_sha256({'idempotencyKey': 'a'}),
            canonical_sha256({'idempotencyKey': 'b'}),
        )

    def test_observed_outcome_is_immutable(self):
        attempt = self._create()
        attempt._record_direct_outcome('uncertain', evidence={'request_id': 'x'})
        with self.assertRaises(ValidationError):
            attempt._record_direct_outcome('succeeded')
        self.assertEqual(attempt.observed_outcome, 'uncertain')

    def test_effective_disposition_contract(self):
        attempt = self._create()
        self.assertEqual(attempt.effective_disposition(), 'unresolved')
        attempt._record_direct_outcome('failed_clean')
        self.assertEqual(attempt.effective_disposition(), 'not_applied')

    def test_direct_create_write_and_unlink_are_closed(self):
        values = {
            'job_id': self.job.id,
            'attempt_token': uuid.uuid4().hex,
            'mutation_domain': 'mutation_dispatch_selftest',
        }
        with self.assertRaises(AccessError):
            self.Attempt.create(values)
        attempt = self._create()
        with self.assertRaises(AccessError):
            attempt.write({'resolution_reason': 'forged'})
        with self.assertRaises(AccessError):
            attempt.unlink()
        self.assertTrue(attempt.exists())

    def test_unknown_mutation_domain_fails_before_c2(self):
        with self.assertRaises(ValidationError):
            self.Attempt.with_context(
                shopify_layer2_c2_side_cursor=True,
            )._create_attempt_intent({
                'job_id': self.job.id,
                'attempt_token': uuid.uuid4().hex,
                'mutation_domain': 'inventory_real_domain_forbidden',
            })
