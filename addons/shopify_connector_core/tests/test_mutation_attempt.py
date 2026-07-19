import uuid

import psycopg2

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import (
    ATTEMPT_WRITE_CONTEXT,
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
    CREATE_SURFACE,
    WRITE_SURFACES,
    canonical_sha256,
)


class TestMutationAttempt(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 attempt test',
            'shop_domain': 'layer2-attempt-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.job = cls.env['shopify.connector.job'].sudo().create({
            'store_id': cls.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'mutation_dispatch_selftest',
            'expected_connection_generation':
                cls.store.connection_generation,
            'state': 'running',
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': 'attempt-token',
            'owner_worker_ref': 'test:1',
            'running_since': fields.Datetime.now(),
        })
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']

    def _create_for(
        self, job, token='attempt-token',
        mutation_domain='mutation_dispatch_selftest',
    ):
        return self.Attempt.with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': mutation_domain,
            'expected_connection_generation':
                job.store_id.connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
            'remote_mutation_intent': {'job_id': job.id},
            'preconditions_snapshot': {
                'generation': job.store_id.connection_generation,
            },
            'business_intent_fingerprint': canonical_sha256({'a': 1}),
            'exact_request_fingerprint': canonical_sha256({'b': 2}),
            'shopify_idempotency_key': uuid.uuid4().hex,
        })

    def _create(self, token='attempt-token'):
        return self._create_for(self.job, token)

    def _job(self, state, job_type, current_token):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': job_type,
            'expected_connection_generation':
                self.store.connection_generation,
            'state': state,
            'payload_hash': uuid.uuid4().hex,
            'current_attempt_token': current_token,
            'owner_worker_ref': 'c2-refusal',
            'running_since': (
                fields.Datetime.now() if state == 'running' else False
            ),
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
            attempt.sudo().with_context(**{
                ATTEMPT_WRITE_CONTEXT: CREATE_SURFACE,
            }).write({'resolution_reason': 'create surface bypass'})
        with self.assertRaises(AccessError):
            attempt.write({'resolution_reason': 'forged'})
        with self.assertRaises(AccessError):
            attempt.unlink()
        self.assertTrue(attempt.exists())

    def test_identity_is_immutable_through_every_write_surface(self):
        attempt = self._create()
        for surface in WRITE_SURFACES:
            with self.assertRaises(ValidationError, msg=surface):
                attempt._surface(surface).write({
                    'attempt_token': uuid.uuid4().hex,
                })

    def test_same_job_with_different_token_is_structurally_rejected(self):
        self._create()
        self.job.sudo().write({'current_attempt_token': 'second-token'})
        with self.assertRaises(psycopg2.IntegrityError):
            with self.env.cr.savepoint():
                self._create('second-token')

    def test_c2_validates_job_token_state_and_domain(self):
        cases = (
            (
                self._job(
                    'queued', 'mutation_dispatch_selftest', 'queued-token',
                ),
                'queued-token',
                'mutation_dispatch_selftest',
            ),
            (
                self._job(
                    'running', 'mutation_dispatch_selftest', 'owner-token',
                ),
                'wrong-token',
                'mutation_dispatch_selftest',
            ),
            (
                self._job(
                    'running', 'core_dispatch_selftest', 'domain-token',
                ),
                'domain-token',
                'mutation_dispatch_selftest',
            ),
        )
        for job, token, domain in cases:
            with self.assertRaises(ValidationError):
                self._create_for(job, token, domain)

    def test_recovery_transition_is_bounded_idempotent_and_unresolved(self):
        attempt = self._create()
        attempt._record_direct_outcome(
            'uncertain', evidence={'request_id': 'synthetic'},
        )
        direct = attempt.remote_evidence_refs['direct']
        attempt._record_recovery_uncertain(
            'post_c2_owner_recovery', 'dispatcher_recovery',
        )
        attempt._record_recovery_uncertain(
            'post_c2_owner_recovery', 'dispatcher_recovery',
        )
        self.assertEqual(attempt.observed_outcome, 'uncertain')
        self.assertFalse(attempt.resolved_at)
        self.assertFalse(attempt.resolution_disposition)
        self.assertEqual(attempt.remote_evidence_refs['direct'], direct)
        self.assertEqual(len(attempt.remote_evidence_refs['recovery']), 1)
        self.assertEqual(
            set(attempt.remote_evidence_refs['recovery'][0]),
            {'window', 'source', 'at', 'job_id', 'attempt_id'},
        )

    def test_pending_recovery_transitions_once_and_refuses_resolved(self):
        attempt = self._create()
        attempt._record_recovery_uncertain(
            'stale_owner_post_c2', 'stale_owner_sweep',
        )
        self.assertEqual(attempt.observed_outcome, 'uncertain')
        self.assertFalse(attempt.resolved_at)
        self.assertEqual(len(attempt.remote_evidence_refs['recovery']), 1)
        attempt.action_resolve_mutation_attempt(
            'applied', 'Synthetic recovery verdict.'
        )
        with self.assertRaises(ValidationError):
            attempt._record_recovery_uncertain(
                'stale_owner_post_c2', 'stale_owner_sweep',
            )

    def test_recovery_refuses_direct_terminal_outcomes(self):
        for outcome in ('succeeded', 'failed_clean'):
            token = '%s-token' % outcome
            job = self._job(
                'running', 'mutation_dispatch_selftest', token,
            )
            attempt = self._create_for(job, token)
            attempt._record_direct_outcome(outcome)
            with self.assertRaises(ValidationError):
                attempt._record_recovery_uncertain(
                    'post_c2_owner_recovery', 'dispatcher_recovery',
                )

    def test_manual_resolution_preserves_all_prior_evidence_sections(self):
        attempt = self._create()
        attempt._record_direct_outcome(
            'uncertain', evidence={'request_id': 'synthetic'},
        )
        attempt._record_recovery_uncertain(
            'post_c2_owner_recovery', 'dispatcher_recovery',
        )
        attempt._record_inconclusive_reconciliation({
            'read': 'synthetic',
        })
        before = attempt._evidence_sections()
        attempt.action_resolve_mutation_attempt(
            'applied', 'Verified synthetic evidence.'
        )
        evidence = attempt.remote_evidence_refs
        self.assertEqual(evidence['direct'], before['direct'])
        self.assertEqual(evidence['recovery'], before['recovery'])
        self.assertEqual(
            evidence['reconciliation'], before['reconciliation'],
        )
        self.assertEqual(len(evidence['manual_resolution']), 1)
        self.assertEqual(
            evidence['manual_resolution'][0]['disposition'], 'applied',
        )

    def test_resolution_tuple_and_effective_timestamp_are_atomic(self):
        attempt = self._create()
        attempt._record_direct_outcome('uncertain')
        self.assertFalse(attempt.resolved_at)
        with self.assertRaises(ValidationError):
            with self.env.cr.savepoint():
                attempt._surface(
                    'action_resolve_mutation_attempt'
                ).write({
                    'resolution_disposition': 'applied',
                })
        attempt.action_resolve_mutation_attempt(
            'applied', 'Synthetic external verification.'
        )
        self.assertTrue(attempt.resolved_at)

    def test_unknown_mutation_domain_fails_before_c2(self):
        with self.assertRaises(ValidationError):
            self.Attempt.with_context(**{
                C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
            })._create_attempt_intent({
                'job_id': self.job.id,
                'attempt_token': uuid.uuid4().hex,
                'mutation_domain': 'inventory_real_domain_forbidden',
            })
