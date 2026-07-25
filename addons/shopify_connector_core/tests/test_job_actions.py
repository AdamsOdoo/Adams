import ast
import os
import uuid

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestJobActions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'JOB-ACTIONS test store',
            'shop_domain': 'job-actions-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.auditor = cls._role_user(
            'auditor', 'group_shopify_connector_auditor',
        )
        cls.operator = cls._role_user(
            'operator', 'group_shopify_connector_operator',
        )
        cls.reviewer = cls._role_user(
            'reviewer', 'group_shopify_connector_reviewer',
        )
        cls.admin = cls._role_user(
            'admin', 'group_shopify_connector_admin',
        )

    @classmethod
    def _role_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'JOB-ACTIONS %s' % label,
            'login': 'job_actions_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _job(self, state, retry_count=3):
        values = {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': state,
            'payload_hash': str(uuid.uuid4()),
            'retry_count': retry_count,
        }
        if state == 'blocked_manual_review':
            values.update({
                'error_class': 'duplicate_risk',
                'manual_review_subreason': 'duplicate_risk',
            })
        return self.Job.create(values)

    def _manual_logs(self, job):
        return self.JobLog.search([
            ('job_id', '=', job.id),
            ('event_type', '=', 'manual_action'),
        ])

    def test_manual_retry_all_allowed_states_and_exact_audit(self):
        cases = (
            ('failed_retryable', self.operator),
            ('failed_final', self.operator),
            ('blocked_manual_review', self.reviewer),
            ('skipped', self.operator),
        )
        for state, user in cases:
            job = self._job(state)
            job.with_user(user).action_manual_retry()
            job.invalidate_recordset()
            self.assertEqual(job.state, 'queued', state)
            self.assertEqual(job.retry_count, 0, state)
            self.assertFalse(job.finished_at, state)
            self.assertFalse(job.manual_review_subreason, state)
            logs = self._manual_logs(job)
            self.assertEqual(len(logs), 1, state)
            self.assertEqual(logs.from_state, state)
            self.assertEqual(logs.to_state, 'queued')
            self.assertEqual(logs.actor_uid, user)
            self.assertIn('manually re-queued', logs.message)

    def test_manual_retry_role_boundaries(self):
        blocked = self._job('blocked_manual_review')
        with self.assertRaises(AccessError):
            blocked.with_user(self.operator).action_manual_retry()
        blocked.invalidate_recordset()
        self.assertEqual(blocked.state, 'blocked_manual_review')
        self.assertFalse(self._manual_logs(blocked))

        retryable = self._job('failed_retryable')
        for user in (self.auditor, self.reviewer):
            with self.assertRaises(AccessError):
                retryable.with_user(user).action_manual_retry()
        retryable.invalidate_recordset()
        self.assertEqual(retryable.state, 'failed_retryable')
        self.assertFalse(self._manual_logs(retryable))

        admin_blocked = self._job('blocked_manual_review')
        admin_blocked.with_user(self.admin).action_manual_retry()
        self.assertEqual(admin_blocked.state, 'queued')
        admin_failed = self._job('failed_final')
        admin_failed.with_user(self.admin).action_manual_retry()
        self.assertEqual(admin_failed.state, 'queued')

    def test_manual_retry_illegal_states_do_not_write(self):
        for state in ('draft', 'queued', 'running', 'succeeded', 'cancelled'):
            job = self._job(state)
            retry_before = job.retry_count
            with self.assertRaises(UserError):
                job.with_user(self.operator).action_manual_retry()
            job.invalidate_recordset()
            self.assertEqual(job.state, state)
            self.assertEqual(job.retry_count, retry_before)
            self.assertFalse(self._manual_logs(job))

    def test_cancel_all_non_terminal_states_and_exact_audit(self):
        for state in ('draft', 'queued', 'running', 'retry_waiting'):
            job = self._job(state)
            reason = 'Cancel %s after operator review' % state
            job.with_user(self.operator).action_cancel(reason)
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled', state)
            self.assertEqual(job.cancel_reason, reason, state)
            self.assertTrue(job.finished_at, state)
            logs = self._manual_logs(job)
            self.assertEqual(len(logs), 1, state)
            self.assertEqual(logs.from_state, state)
            self.assertEqual(logs.to_state, 'cancelled')
            self.assertEqual(logs.actor_uid, self.operator)
            self.assertIn(reason, logs.message)

    def test_cancel_requires_non_empty_reason_without_write(self):
        for reason in (False, None, '', '   ', 0):
            job = self._job('queued')
            with self.assertRaises(UserError):
                job.with_user(self.operator).action_cancel(reason)
            job.invalidate_recordset()
            self.assertEqual(job.state, 'queued')
            self.assertFalse(job.cancel_reason)
            self.assertFalse(self._manual_logs(job))

    def test_cancel_role_boundary(self):
        for user in (self.auditor, self.reviewer):
            job = self._job('queued')
            with self.assertRaises(AccessError):
                job.with_user(user).action_cancel('not authorized')
            job.invalidate_recordset()
            self.assertEqual(job.state, 'queued')
            self.assertFalse(self._manual_logs(job))
        admin_job = self._job('queued')
        admin_job.with_user(self.admin).action_cancel('admin decision')
        self.assertEqual(admin_job.state, 'cancelled')

    def test_cancel_terminal_and_recovery_states_do_not_write(self):
        for state in (
            'succeeded', 'failed_final', 'skipped', 'cancelled',
            'failed_retryable', 'blocked_manual_review',
        ):
            job = self._job(state)
            with self.assertRaises(UserError):
                job.with_user(self.operator).action_cancel('not legal here')
            job.invalidate_recordset()
            self.assertEqual(job.state, state)
            self.assertFalse(job.cancel_reason)
            self.assertFalse(self._manual_logs(job))

    def test_source_signatures_have_no_force_or_bypass_parameter(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
            'shopify_connector_job_actions.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=path)
        methods = {
            node.name: [arg.arg for arg in node.args.args]
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }
        self.assertEqual(methods['action_manual_retry'], ['self'])
        self.assertEqual(methods['action_cancel'], ['self', 'reason'])
        for args in methods.values():
            self.assertNotIn('force', args)
            self.assertNotIn('bypass', args)

    def test_source_scope_is_additive_with_two_sec1_sudo_sites(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
            'shopify_connector_job_actions.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=path)
        public_methods = [
            node.name for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and not node.name.startswith('_')
        ]
        sudo_calls = [
            node for node in ast.walk(tree)
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'sudo'
            )
        ]
        self.assertEqual(
            sorted(public_methods),
            ['action_cancel', 'action_manual_retry'],
        )
        self.assertEqual(len(sudo_calls), 2)
