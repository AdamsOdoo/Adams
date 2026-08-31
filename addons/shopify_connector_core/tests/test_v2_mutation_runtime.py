"""Odoo checks for the additive V2 mutation-attempt identity seam."""

import uuid

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
    CREATE_SURFACE,
    canonical_sha256,
)


@tagged('post_install', '-at_install')
class TestV2MutationRuntime(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].sudo().create({
            'name': 'V2 mutation seam %s' % uuid.uuid4().hex,
            'shop_domain': 'v2-seam-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.job = cls.env['shopify.connector.job'].sudo().create({
            'store_id': cls.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': 'v2-seam-token',
            'owner_worker_ref': 'v2-seam-test',
            'running_since': fields.Datetime.now(),
            'expected_connection_generation': cls.store.connection_generation,
        })
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']

    def _create_attempt(self):
        return self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': self.job.id,
            'attempt_token': self.job.current_attempt_token,
            'mutation_domain': self.job.job_type,
            'expected_connection_generation': self.store.connection_generation,
            'expected_store_identity': self.store.shop_domain,
            'remote_mutation_intent': {'job_id': self.job.id},
            'preconditions_snapshot': {'generation': 0},
            'business_intent_fingerprint': canonical_sha256({'seam': True}),
            'exact_request_fingerprint': canonical_sha256({'seam': True}),
            'shopify_idempotency_key': uuid.uuid4().hex,
        })

    def test_v2_identity_fields_are_optional_readonly_and_defaulted(self):
        fields_map = self.Attempt._fields
        self.assertIn('run_id', fields_map)
        self.assertIn('expected_configuration_generation', fields_map)
        self.assertTrue(fields_map['run_id'].readonly)
        self.assertTrue(fields_map['expected_configuration_generation'].readonly)
        self.assertFalse(fields_map['run_id'].required)
        self.assertEqual(fields_map['expected_configuration_generation'].default, 0)

    def test_legacy_c2_keeps_identity_empty_and_immutable(self):
        attempt = self._create_attempt()
        self.assertFalse(attempt.run_id)
        self.assertEqual(attempt.expected_configuration_generation, 0)
        with self.assertRaises(ValidationError):
            attempt._surface(CREATE_SURFACE).write({'run_id': self.job.id})
        with self.assertRaises(ValidationError):
            attempt._surface(CREATE_SURFACE).write({
                'expected_configuration_generation': 1,
            })

    def test_c3_scope_failure_is_a_reconciliation_consequence(self):
        consequence = self.env[
            'shopify.connector.job.dispatch'
        ]._v2_force_reconcile_consequence({
            'observed_outcome': 'succeeded',
            'error_class': False,
            'manual_review_subreason': False,
            'action': 'succeed',
            'message': 'synthetic direct result',
            'evidence': {'request_id': 'synthetic'},
            'domain_payload': {'safe': True},
        })
        self.assertEqual(consequence['observed_outcome'], 'uncertain')
        self.assertEqual(consequence['action'], 'reconcile')
        self.assertEqual(consequence['error_class'], 'store_identity_mismatch')
        self.assertEqual(
            consequence['evidence']['v2_c3_admission'],
            'reconciliation_required',
        )

    def test_api_client_has_full_v2_admit_and_send_stage_hooks(self):
        client = self.env['shopify.connector.api.client']
        self.assertTrue(callable(client._v2_admit_mutation_side))
        self.assertTrue(callable(client._admit_mutation))
        self.assertTrue(callable(client._validate_graphql_operation))
