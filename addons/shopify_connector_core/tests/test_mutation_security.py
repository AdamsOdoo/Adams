import json
import uuid

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase

from ..models.shopify_connector_mutation_attempt import (
    ATTEMPT_WRITE_CONTEXT,
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
)


class TestMutationSecurity(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Layer 2 security test',
            'shop_domain': 'layer2-security-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.roles = {}
        for label, group in (
            ('auditor', 'group_shopify_connector_auditor'),
            ('operator', 'group_shopify_connector_operator'),
            ('reviewer', 'group_shopify_connector_reviewer'),
            ('admin', 'group_shopify_connector_admin'),
        ):
            cls.roles[label] = cls.env['res.users'].create({
                'name': 'Layer 2 %s' % label,
                'login': 'layer2_%s_%s' % (label, uuid.uuid4().hex),
                'group_ids': [(6, 0, [
                    cls.env.ref('base.group_user').id,
                    cls.env.ref('shopify_connector_core.%s' % group).id,
                ])],
            })
        cls.Job = cls.env['shopify.connector.job']
        cls.Attempt = cls.env['shopify.connector.mutation.attempt']

    def _fixture(self):
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
            'owner_worker_ref': 'test:1',
            'running_since': fields.Datetime.now(),
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
            'shopify_idempotency_key': uuid.uuid4().hex,
        })
        return job, attempt

    def test_all_roles_read_but_cannot_create_write_or_unlink(self):
        job, attempt = self._fixture()
        for label, user in self.roles.items():
            self.assertTrue(attempt.with_user(user).read(['attempt_token']))
            with self.assertRaises(AccessError, msg=label):
                self.Attempt.with_user(user).create({
                    'job_id': job.id,
                    'attempt_token': uuid.uuid4().hex,
                    'mutation_domain': 'mutation_dispatch_selftest',
                })
            with self.assertRaises(AccessError, msg=label):
                attempt.with_user(user).write({'resolution_reason': 'forged'})
            with self.assertRaises(AccessError, msg=label):
                attempt.with_user(user).with_context(**{
                    ATTEMPT_WRITE_CONTEXT: '_record_recovery_uncertain',
                }).write({'observed_outcome': 'uncertain'})
            with self.assertRaises(AccessError, msg=label):
                attempt.with_user(user).unlink()

    def test_only_administrator_can_resolve_with_reason(self):
        _job, attempt = self._fixture()
        attempt._record_direct_outcome('uncertain')
        with self.assertRaises(AccessError):
            attempt.with_user(self.roles['reviewer']).action_resolve_mutation_attempt(
                'applied', 'reviewer bypass'
            )
        with self.assertRaises(UserError):
            attempt.with_user(self.roles['admin']).action_resolve_mutation_attempt(
                'applied', ''
            )
        attempt.with_user(self.roles['admin']).action_resolve_mutation_attempt(
            'applied', 'Verified against external evidence.'
        )
        self.assertEqual(attempt.resolution_source, 'manual_admin')
        self.assertEqual(attempt.effective_disposition(), 'applied')

    def test_manual_resolution_evidence_is_safe_and_redacted(self):
        _job, attempt = self._fixture()
        attempt._record_direct_outcome(
            'uncertain', evidence={'request_id': 'safe-request-ref'},
        )
        attempt._record_recovery_uncertain(
            'post_c2_owner_recovery', 'dispatcher_recovery',
        )
        attempt._record_inconclusive_reconciliation({
            'read_ref': 'safe-read-ref',
        })
        before = attempt._evidence_sections()
        unsafe_reason = (
            'Verified token shpat_DUMMYDUMMYDUMMY0000000000000000 '
            'for person@example.com'
        )
        attempt.with_user(
            self.roles['admin']
        ).action_resolve_mutation_attempt('applied', unsafe_reason)
        evidence = attempt.remote_evidence_refs
        serialized = json.dumps(evidence, sort_keys=True)
        self.assertEqual(evidence['direct'], before['direct'])
        self.assertEqual(evidence['recovery'], before['recovery'])
        self.assertEqual(
            evidence['reconciliation'], before['reconciliation'],
        )
        self.assertEqual(len(evidence['manual_resolution']), 1)
        manual = evidence['manual_resolution'][0]
        self.assertEqual(set(manual), {
            'actor_uid', 'disposition', 'at', 'reason',
        })
        self.assertEqual(manual['actor_uid'], self.roles['admin'].id)
        self.assertEqual(manual['disposition'], 'applied')
        self.assertNotIn('shpat_DUMMY', serialized)
        self.assertNotIn('person@example.com', serialized)
        self.assertNotIn('shpat_DUMMY', attempt.resolution_reason)
        self.assertNotIn('person@example.com', attempt.resolution_reason)

    def test_generic_retry_and_review_actions_refuse_mutation_jobs(self):
        job, attempt = self._fixture()
        attempt._record_direct_outcome('uncertain')
        job.sudo().write({
            'state': 'blocked_manual_review',
            'error_class': 'duplicate_risk',
            'manual_review_subreason': 'duplicate_risk',
        })
        with self.assertRaises(UserError):
            job.with_user(self.roles['admin']).action_manual_retry()
        with self.assertRaises(UserError):
            job.with_user(self.roles['admin']).action_resolve_manual_review()
        with self.assertRaises(UserError):
            job.with_user(self.roles['admin']).action_cancel('No resend')
        job.sudo().write({
            'error_class': 'store_identity_mismatch',
            'manual_review_subreason': 'store_identity_mismatch',
        })
        with self.assertRaises(UserError):
            job.with_user(self.roles['admin']).action_manual_retry()
        with self.assertRaises(UserError):
            job.with_user(self.roles['admin']).action_resolve_manual_review()
