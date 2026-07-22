# Part of the Shopify Connector (U0 operator UI foundation).
#
# Role / visibility matrix + negative direct-call tests. Proves that button
# visibility and server-side denial agree: a role that must not see an action
# also cannot invoke it directly over ORM/RPC. A hidden button is never the
# security control -- the server method / ACL is.
#
# Matrix under test (all four roles read every operator surface):
#   Auditor     -> read only; no retry / cancel / review / resolve / lifecycle.
#   Operator    -> ordinary retry + cancel; no blocked-review; no mutation resolve.
#   Reviewer    -> blocked-review resolve/retry; no ordinary Operator cancel;
#                  no mutation resolve.
#   Administrator -> everything sanctioned; still no protected-field write.

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiVisibilityMatrix(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Store = cls.env['shopify.connector.store'].sudo()
        cls.Job = cls.env['shopify.connector.job'].sudo()
        cls._seq = 0
        cls.store = cls._make_store()
        cls.users = {
            role: new_test_user(
                cls.env, login='u0_%s' % role,
                groups='base.group_user,shopify_connector_core.group_shopify_connector_%s' % role,
            )
            for role in ('auditor', 'operator', 'reviewer', 'admin')
        }
        cls.plain = new_test_user(cls.env, login='u0_plain', groups='base.group_user')

    @classmethod
    def _make_store(cls, state='connected', **extra):
        cls._seq += 1
        vals = {'name': 'S%d' % cls._seq, 'shop_domain': 'u0-vis-%d.myshopify.com' % cls._seq,
                'api_version': '2025-01', 'state': state, 'credential_present': True}
        vals.update(extra)
        return cls.Store.create(vals)

    def _make_job(self, state):
        self.__class__._seq += 1
        vals = {'store_id': self.store.id, 'job_source': 'setup_readiness_check',
                'job_type': 'core_manual_maintenance', 'state': state,
                'payload_hash': 'u0-vis-%d' % self._seq}
        if state == 'blocked_manual_review':
            vals['manual_review_subreason'] = 'ambiguous_match'
        if state in ('succeeded', 'failed_final', 'skipped', 'cancelled'):
            vals['finished_at'] = fields.Datetime.now()
        return self.Job.create(vals)

    # ------------------------------------------------------------------ #
    #  read surfaces
    # ------------------------------------------------------------------ #
    def test_all_roles_read_operator_surfaces(self):
        for role, user in self.users.items():
            for model in ('shopify.connector.store', 'shopify.connector.job',
                          'shopify.connector.job.log', 'shopify.connector.mutation.attempt'):
                # Must not raise.
                self.env[model].with_user(user).search_count([])

    def test_non_connector_user_has_no_root_menu(self):
        root = self.env.ref('shopify_connector_core.menu_shopify_connector_root')
        auditor = self.env.ref('shopify_connector_core.group_shopify_connector_auditor')
        self.assertIn(auditor, root.groups_id)
        self.assertFalse(self.plain.has_group('shopify_connector_core.group_shopify_connector_auditor'))

    def test_non_admin_cannot_read_credential(self):
        for role in ('auditor', 'operator', 'reviewer'):
            with self.assertRaises(AccessError):
                self.env['shopify.connector.store.credential'].with_user(
                    self.users[role]).search_count([])

    # ------------------------------------------------------------------ #
    #  retry matrix
    # ------------------------------------------------------------------ #
    def test_retry_ordinary_permissions(self):
        # Operator and Admin may retry a failed_retryable job; Auditor/Reviewer may not.
        for role in ('operator', 'admin'):
            job = self._make_job('failed_retryable')
            job.with_user(self.users[role]).action_manual_retry()
            self.assertEqual(job.state, 'queued')
        for role in ('auditor', 'reviewer'):
            job = self._make_job('failed_retryable')
            with self.assertRaises(AccessError):
                job.with_user(self.users[role]).action_manual_retry()

    def test_retry_blocked_review_permissions(self):
        # Reviewer and Admin may retry a blocked_manual_review job; Operator/Auditor may not.
        for role in ('reviewer', 'admin'):
            job = self._make_job('blocked_manual_review')
            job.with_user(self.users[role]).action_manual_retry()
            self.assertEqual(job.state, 'queued')
        for role in ('auditor', 'operator'):
            job = self._make_job('blocked_manual_review')
            with self.assertRaises(AccessError):
                job.with_user(self.users[role]).action_manual_retry()

    # ------------------------------------------------------------------ #
    #  cancel matrix (via the wizard)
    # ------------------------------------------------------------------ #
    def test_cancel_permissions(self):
        Wizard = self.env['shopify.connector.job.cancel.wizard']
        for role in ('operator', 'admin'):
            job = self._make_job('queued')
            wiz = Wizard.with_user(self.users[role]).create({'job_id': job.id, 'reason': 'no longer needed'})
            wiz.action_confirm()
            self.assertEqual(job.state, 'cancelled')
        # Auditor/Reviewer are not in the operator group -> no wizard ACL.
        for role in ('auditor', 'reviewer'):
            job = self._make_job('queued')
            with self.assertRaises(AccessError):
                Wizard.with_user(self.users[role]).create({'job_id': job.id, 'reason': 'x'})

    # ------------------------------------------------------------------ #
    #  manual-review resolution matrix
    # ------------------------------------------------------------------ #
    def test_resolve_manual_review_permissions(self):
        for role in ('reviewer', 'admin'):
            job = self._make_job('blocked_manual_review')
            job.with_user(self.users[role]).action_resolve_manual_review()
            self.assertEqual(job.state, 'queued')
        for role in ('auditor', 'operator'):
            job = self._make_job('blocked_manual_review')
            with self.assertRaises(AccessError):
                job.with_user(self.users[role]).action_resolve_manual_review()

    # ------------------------------------------------------------------ #
    #  mutation resolution wizard is Administrator-only
    # ------------------------------------------------------------------ #
    def test_mutation_resolution_wizard_admin_only(self):
        Wizard = self.env['shopify.connector.mutation.resolution.wizard']
        for role in ('auditor', 'operator', 'reviewer'):
            with self.assertRaises(AccessError):
                Wizard.with_user(self.users[role]).create({})
        # Admin can create the transient wizard (create ACL present).
        Wizard.with_user(self.users['admin']).create({})

    # ------------------------------------------------------------------ #
    #  protected-field write stays denied even for Admin (non-sudo)
    # ------------------------------------------------------------------ #
    def test_protected_field_write_denied_for_admin(self):
        job = self._make_job('failed_final')
        with self.assertRaises(AccessError):
            job.with_user(self.users['admin']).write({'state': 'queued'})
