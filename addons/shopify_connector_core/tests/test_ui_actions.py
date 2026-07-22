# Part of the Shopify Connector (U0 operator UI foundation).
#
# Behavioural tests for the U0 safe actions and wizards. Every UI action targets
# an existing sanctioned method; these tests prove the wizards defer to those
# methods (never writing state directly), that valid/invalid states behave
# correctly, that a mutation-evidence-linked job refuses generic retry, and that
# store lifecycle/test preconditions hold. No Shopify request is ever made:
# only failing preconditions of test-connection are exercised.

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiActions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env['shopify.connector.store'].sudo()
        cls.Job = cls.env['shopify.connector.job'].sudo()
        cls._seq = 0
        cls.admin = new_test_user(
            cls.env, login='u0_act_admin',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_admin')
        cls.operator = new_test_user(
            cls.env, login='u0_act_op',
            groups='base.group_user,shopify_connector_core.group_shopify_connector_operator')
        cls.store = cls._make_store()

    @classmethod
    def _make_store(cls, state='connected', credential_present=True, **extra):
        cls._seq += 1
        vals = {'name': 'S%d' % cls._seq, 'shop_domain': 'u0-act-%d.myshopify.com' % cls._seq,
                'api_version': '2025-01', 'state': state, 'credential_present': credential_present}
        vals.update(extra)
        return cls.Store.create(vals)

    def _make_job(self, state):
        self.__class__._seq += 1
        vals = {'store_id': self.store.id, 'job_source': 'setup_readiness_check',
                'job_type': 'core_manual_maintenance', 'state': state,
                'payload_hash': 'u0-act-%d' % self._seq}
        if state == 'blocked_manual_review':
            vals['manual_review_subreason'] = 'ambiguous_match'
        if state in ('succeeded', 'failed_final', 'skipped', 'cancelled'):
            vals['finished_at'] = fields.Datetime.now()
        return self.Job.create(vals)

    def _make_attempt(self, job, observed_outcome='uncertain'):
        """Create a mutation attempt via the model's own write-surface context.

        Skips the test if the Layer 2 create-surface constants are not
        importable in this build (keeps the module importable regardless).
        """
        try:
            from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
                ATTEMPT_WRITE_CONTEXT, CREATE_SURFACE, C2_SENTINEL_CONTEXT, C2_SIDE_CURSOR_SENTINEL,
            )
        except Exception:  # pragma: no cover - build-shape guard
            self.skipTest("Layer 2 mutation-attempt create surface not importable in this build")
        self.__class__._seq += 1
        ctx = {ATTEMPT_WRITE_CONTEXT: CREATE_SURFACE, C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL}
        return self.env['shopify.connector.mutation.attempt'].sudo().with_context(**ctx).create({
            'job_id': job.id,
            'attempt_token': 'u0-tok-%d' % self._seq,
            'mutation_domain': 'inventory',
            'observed_outcome': observed_outcome,
        })

    # ------------------------------------------------------------------ #
    #  retry
    # ------------------------------------------------------------------ #
    def test_retry_from_all_valid_states(self):
        for state in ('failed_retryable', 'failed_final', 'blocked_manual_review', 'skipped'):
            job = self._make_job(state)
            job.with_user(self.admin).action_manual_retry()
            self.assertEqual(job.state, 'queued', "retry from %s should re-queue" % state)

    def test_retry_from_invalid_state_refused(self):
        job = self._make_job('queued')
        with self.assertRaises(UserError):
            job.with_user(self.admin).action_manual_retry()

    def test_mutation_evidence_job_refuses_generic_retry(self):
        job = self._make_job('failed_retryable')
        self._make_attempt(job)  # links evidence via reverse job_id
        job.invalidate_recordset()
        with self.assertRaises(UserError):
            job.with_user(self.admin).action_manual_retry()

    # ------------------------------------------------------------------ #
    #  cancel wizard
    # ------------------------------------------------------------------ #
    def test_cancel_reason_required(self):
        job = self._make_job('queued')
        wiz = self.env['shopify.connector.job.cancel.wizard'].with_user(self.operator).create(
            {'job_id': job.id, 'reason': '   '})
        with self.assertRaises(UserError):
            wiz.action_confirm()

    def test_cancel_records_reason(self):
        job = self._make_job('queued')
        wiz = self.env['shopify.connector.job.cancel.wizard'].with_user(self.operator).create(
            {'job_id': job.id, 'reason': 'duplicate request'})
        wiz.action_confirm()
        self.assertEqual(job.state, 'cancelled')
        self.assertTrue(job.cancel_reason)

    def test_cancel_wizard_defers_to_server_state_check(self):
        # A terminal job cannot be cancelled; the wizard must surface the
        # server's refusal rather than mutating state itself.
        job = self._make_job('succeeded')
        wiz = self.env['shopify.connector.job.cancel.wizard'].with_user(self.operator).create(
            {'job_id': job.id, 'reason': 'too late'})
        with self.assertRaises(UserError):
            wiz.action_confirm()
        self.assertEqual(job.state, 'succeeded')

    # ------------------------------------------------------------------ #
    #  mutation resolution wizard
    # ------------------------------------------------------------------ #
    def test_mutation_resolution_input_validation(self):
        job = self._make_job('blocked_manual_review')
        attempt = self._make_attempt(job, observed_outcome='uncertain')
        Wizard = self.env['shopify.connector.mutation.resolution.wizard'].with_user(self.admin)
        # empty reason
        wiz = Wizard.create({'mutation_attempt_id': attempt.id, 'disposition': 'applied', 'reason': '  '})
        with self.assertRaises(UserError):
            wiz.action_confirm()

    def test_mutation_resolution_applies(self):
        job = self._make_job('blocked_manual_review')
        attempt = self._make_attempt(job, observed_outcome='uncertain')
        wiz = self.env['shopify.connector.mutation.resolution.wizard'].with_user(self.admin).create(
            {'mutation_attempt_id': attempt.id, 'disposition': 'applied', 'reason': 'confirmed in Shopify admin'})
        wiz.action_confirm()
        attempt.invalidate_recordset()
        self.assertEqual(attempt.resolution_disposition, 'applied')

    def test_mutation_resolution_denied_for_operator(self):
        job = self._make_job('blocked_manual_review')
        attempt = self._make_attempt(job, observed_outcome='uncertain')
        with self.assertRaises(AccessError):
            attempt.with_user(self.operator).action_resolve_mutation_attempt('applied', 'x')

    # ------------------------------------------------------------------ #
    #  store lifecycle preconditions (no Shopify call is triggered)
    # ------------------------------------------------------------------ #
    def test_test_connection_requires_credential(self):
        store = self._make_store(credential_present=False)
        with self.assertRaises(UserError):
            store.with_user(self.admin).action_test_connection()

    def test_test_connection_unavailable_when_disconnected(self):
        store = self._make_store(state='disconnected', credential_present=True)
        with self.assertRaises(UserError):
            store.with_user(self.admin).action_test_connection()
