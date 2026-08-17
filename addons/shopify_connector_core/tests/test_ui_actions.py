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
from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)


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
                'api_version': SHOPIFY_API_VERSION, 'state': state, 'credential_present': credential_present}
        vals.update(extra)
        return cls.Store.create(vals)

    def _make_job(self, state, **extra):
        self.__class__._seq += 1
        vals = {'store_id': self.store.id, 'job_source': 'setup_readiness_check',
                'job_type': 'core_manual_maintenance', 'state': state,
                'payload_hash': 'u0-act-%d' % self._seq}
        if state == 'blocked_manual_review':
            vals['manual_review_subreason'] = 'ambiguous_match'
        if state in ('succeeded', 'failed_final', 'skipped', 'cancelled'):
            vals['finished_at'] = fields.Datetime.now()
        vals.update(extra)
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
            # Use the core self-test mutation domain: it is the only strategy
            # guaranteed registered regardless of which domain addons run, so
            # the resolution consequence path resolves a valid strategy. (The
            # bare 'inventory' domain does not exist -- the inventory addon
            # registers 'inventory_set_quantities' / 'inventory_activate'.)
            'mutation_domain': 'mutation_dispatch_selftest',
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

    def test_attention_projection_prioritizes_human_owned_cases(self):
        blocked = self._make_job('blocked_manual_review')
        final = self._make_job(
            'failed_final', error_class='shopify_permission_scope_auth'
        )
        retryable = self._make_job(
            'failed_retryable', error_class='mapping_missing'
        )
        self.assertGreater(blocked.attention_priority, final.attention_priority)
        self.assertGreater(final.attention_priority, retryable.attention_priority)
        self.assertEqual(blocked.attention_owner, 'Administrator decision')
        self.assertNotIn('Reviewer', blocked.attention_owner)
        self.assertIn('Administrator', blocked.attention_next_action)
        self.assertEqual(blocked.recovery_owner, blocked.attention_owner)
        self.assertEqual(blocked.recovery_next_action, blocked.attention_next_action)
        self.assertIn('Ambiguous Match', blocked.attention_reason)
        self.assertIn('Retry', retryable.attention_next_action)

    def test_attention_case_routes_mutation_evidence_to_the_exact_attempt(self):
        job = self._make_job('blocked_manual_review')
        attempt = self._make_attempt(job)
        action = job.with_user(self.admin).action_open_attention_case()
        self.assertEqual(action['res_model'], attempt._name)
        self.assertEqual(action['res_id'], attempt.id)
        self.assertEqual(action['view_mode'], 'form')

    def test_attention_case_routes_a_business_target_without_sudo(self):
        job = self._make_job(
            'failed_retryable',
            error_class='odoo_validation_configuration',
            res_model=self.store._name,
            res_id=self.store.id,
        )
        action = job.with_user(self.admin).action_open_attention_case()
        self.assertEqual(action['res_model'], self.store._name)
        self.assertEqual(action['res_id'], self.store.id)
        self.assertEqual(action['view_mode'], 'form')

    def test_runs_and_attention_actions_have_distinct_populations(self):
        runs = self.env.ref(
            'shopify_connector_core.action_shopify_connector_sync_center'
        )
        attention = self.env.ref(
            'shopify_connector_core.action_shopify_connector_error_center'
        )
        self.assertEqual(
            eval(runs.domain or '[]'), [],  # noqa: S307 -- static XML literal
            'Runs & Recovery must show every run.',
        )
        self.assertEqual(
            eval(attention.domain),  # noqa: S307 -- static XML literal
            [(
                'state', 'in',
                ('blocked_manual_review', 'failed_final', 'failed_retryable'),
            )],
        )
        self.assertNotIn('retry_waiting', attention.domain)

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

    # Stage R2 correction (independent review 5049668193 material P2): the
    # wizard must be REFUSED by the sanctioned server method -- not silently
    # accepted -- when the attempt is not `uncertain`, and the refusal must
    # leave the attempt and its owning job completely unchanged. Only the
    # success path (`test_mutation_resolution_applies`) and input-validation
    # path were previously exercised through the wizard; neither business-rule
    # refusal branch was.
    def test_mutation_resolution_wizard_refuses_non_uncertain_attempt(self):
        job = self._make_job('blocked_manual_review')
        attempt = self._make_attempt(job, observed_outcome='pending')
        job_state_before = job.state
        wiz = self.env['shopify.connector.mutation.resolution.wizard'].with_user(self.admin).create(
            {'mutation_attempt_id': attempt.id, 'disposition': 'applied',
             'reason': 'confirmed in Shopify admin'})
        with self.assertRaises(UserError):
            wiz.action_confirm()
        attempt.invalidate_recordset()
        job.invalidate_recordset()
        self.assertFalse(attempt.resolution_disposition)
        self.assertFalse(attempt.resolution_reason)
        self.assertEqual(job.state, job_state_before)

    def test_mutation_resolution_wizard_refuses_already_resolved_attempt(self):
        job = self._make_job('blocked_manual_review')
        attempt = self._make_attempt(job, observed_outcome='uncertain')
        # The first resolution goes through the sanctioned method directly
        # (not the wizard) so the "already resolved" precondition is genuine.
        attempt.with_user(self.admin).action_resolve_mutation_attempt(
            'applied', 'first resolution')
        attempt.invalidate_recordset()
        job.invalidate_recordset()
        disposition_before = attempt.resolution_disposition
        reason_before = attempt.resolution_reason
        job_state_before = job.state
        wiz = self.env['shopify.connector.mutation.resolution.wizard'].with_user(self.admin).create(
            {'mutation_attempt_id': attempt.id, 'disposition': 'not_applied',
             'reason': 'second attempt should be refused'})
        with self.assertRaises(UserError):
            wiz.action_confirm()
        attempt.invalidate_recordset()
        job.invalidate_recordset()
        self.assertEqual(attempt.resolution_disposition, disposition_before)
        self.assertEqual(attempt.resolution_reason, reason_before)
        self.assertEqual(job.state, job_state_before)

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
