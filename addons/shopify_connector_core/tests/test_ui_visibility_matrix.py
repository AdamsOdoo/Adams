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

from unittest.mock import patch

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
        # Odoo 19: ir.ui.menu exposes the access groups as `group_ids`
        # (the pre-19 `groups_id` name was removed).
        self.assertIn(auditor, root.group_ids)
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
        # The create ACL is the security control under test. Check it directly:
        # the wizard's mutation_attempt_id/disposition/reason are all required,
        # so a bare create({}) would raise a NOT NULL error unrelated to the
        # ACL. Auditor/Operator/Reviewer lack the create ACL; Admin holds it.
        for role in ('auditor', 'operator', 'reviewer'):
            with self.assertRaises(AccessError):
                Wizard.with_user(self.users[role]).check_access('create')
        Wizard.with_user(self.users['admin']).check_access('create')

    # ------------------------------------------------------------------ #
    #  protected-field write stays denied even for Admin (non-sudo)
    # ------------------------------------------------------------------ #
    def test_protected_field_write_denied_for_admin(self):
        job = self._make_job('failed_final')
        with self.assertRaises(AccessError):
            job.with_user(self.users['admin']).write({'state': 'queued'})

    # ------------------------------------------------------------------ #
    #  Stage R1/R2: all FIVE public store lifecycle/probe actions --
    #  including `action_mark_reconnect_needed`, the Stage R2 correction for
    #  independent review 5049668193's confirmed P1 -- are Administrator-only
    #  at the server boundary. A read-only role (Auditor/Operator/Reviewer)
    #  and a plain user are denied with AccessError on a direct ORM/RPC call
    #  -- before the lifecycle lock, any audit Job/JobLog row, the Shopify
    #  transport, or any store/credential field change. The hidden button is
    #  never the control; the server method is.
    #
    #  Stage R1's version of this test only asserted the bare AccessError
    #  type for four actions -- independent review 5049668193 flagged that a
    #  future reorder moving the boundary check AFTER the lock/audit-job
    #  creation would still pass it (the eventual ACL-gated write still
    #  raises), silently reintroducing the pre-fix defect class. This version
    #  adds explicit zero-delta proof for the lifecycle lock, the Shopify
    #  transport, the audit Job/JobLog count, and every store/credential
    #  field, for every one of the five actions and (where the action's own
    #  branching matters) every reachable store state -- including
    #  `action_mark_reconnect_needed`'s own dangerous branch: a store already
    #  `disconnecting`/`disconnected`, where the unguarded method used to
    #  return `None` with **no exception at all** after creating a sudo()
    #  audit job.
    # ------------------------------------------------------------------ #
    def _make_credentialed_store(self, state):
        store = self._make_store(state=state, credential_present=True)
        self.env['shopify.connector.store.credential'].sudo().create({
            'store_id': store.id,
            'access_token': 'shpat_dummydummydummy0000000000000',
            'credential_state': 'present',
        })
        return store

    def _credential_of(self, store):
        return self.env['shopify.connector.store.credential'].sudo().search(
            [('store_id', '=', store.id)], limit=1)

    def test_store_lifecycle_actions_admin_only_direct_call(self):
        Store = type(self.Store)
        Client = type(self.env['shopify.connector.api.client'])
        Job = self.Job
        JobLog = self.env['shopify.connector.job.log'].sudo()

        scenarios = (
            ('action_test_connection', 'connected'),
            ('action_activate', 'connected'),
            ('action_disconnect', 'connected'),
            # The already-disconnecting audited-no-op branch: pre-Stage-R1
            # this created a sudo() audit job with no denial either.
            ('action_disconnect', 'disconnecting'),
            ('action_reconnect', 'disconnected'),
            ('action_mark_reconnect_needed', 'connected'),
            # The two dangerous branches this Stage R2 correction closes.
            ('action_mark_reconnect_needed', 'disconnecting'),
            ('action_mark_reconnect_needed', 'disconnected'),
        )
        non_admin = (self.users['auditor'], self.users['operator'],
                     self.users['reviewer'], self.plain)

        lock_calls = []
        send_calls = []
        original_lock = Store._lock_store_for_lifecycle

        def counting_lock(inner_self):
            lock_calls.append(1)
            return original_lock(inner_self)

        def fake_send(inner_self, store, body, token=None):
            send_calls.append(1)
            raise AssertionError(
                'The Shopify transport must never be reached before the '
                'Administrator boundary denies a non-admin caller.'
            )

        for action, state in scenarios:
            for user in non_admin:
                store = self._make_credentialed_store(state)
                credential = self._credential_of(store)
                jobs0 = Job.search_count([('store_id', '=', store.id)])
                logs0 = JobLog.search_count([('store_id', '=', store.id)])
                state0 = store.state
                gen0 = store.connection_generation
                disc0 = store.disconnect_status
                cred_state0 = credential.credential_state
                cred_token0 = credential.access_token
                lock_calls.clear()
                send_calls.clear()

                with patch.object(Store, '_lock_store_for_lifecycle', counting_lock), \
                        patch.object(Client, '_send', fake_send):
                    with self.assertRaises(
                        AccessError,
                        msg='%s/%s should deny %s' % (action, state, user.login),
                    ):
                        getattr(store.with_user(user), action)()

                store.invalidate_recordset()
                credential.invalidate_recordset()
                label = '%s on a %s store (role=%s)' % (action, state, user.login)
                self.assertEqual(
                    lock_calls, [],
                    '%s reached the lifecycle lock before denial' % label)
                self.assertEqual(
                    send_calls, [],
                    '%s reached the Shopify transport before denial' % label)
                self.assertEqual(
                    Job.search_count([('store_id', '=', store.id)]), jobs0,
                    '%s created a Job before denial' % label)
                self.assertEqual(
                    JobLog.search_count([('store_id', '=', store.id)]), logs0,
                    '%s created a JobLog before denial' % label)
                self.assertEqual(
                    store.state, state0, '%s mutated store.state' % label)
                self.assertEqual(
                    store.connection_generation, gen0,
                    '%s mutated connection_generation' % label)
                self.assertEqual(
                    store.disconnect_status, disc0,
                    '%s mutated disconnect_status' % label)
                self.assertEqual(
                    credential.credential_state, cred_state0,
                    '%s mutated credential_state' % label)
                self.assertEqual(
                    credential.access_token, cred_token0,
                    '%s mutated the credential access_token' % label)

        # Administrator passes the boundary guard for all five actions
        # (admits; raises nothing) -- the guard itself is action-agnostic.
        admin_store = self._make_credentialed_store('connected')
        admin_store.with_user(
            self.users['admin'])._ensure_connector_admin_boundary()
