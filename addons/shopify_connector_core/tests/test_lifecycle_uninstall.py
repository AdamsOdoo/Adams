import ast
import os
import uuid

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)


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
class TestLifecycleUninstall(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'LC-1 lifecycle store',
            'shop_domain': 'lc1-lifecycle.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']

    def _job(self, state='queued', job_type='core_dispatch_selftest', **extra):
        values = {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': job_type,
            'state': state,
            'payload_hash': str(uuid.uuid4()),
        }
        values.update(extra)
        return self.Job.create(values)

    def test_original_job_type_is_set_once_at_create(self):
        job = self._job()
        self.assertEqual(job.original_job_type, 'core_dispatch_selftest')
        self.assertTrue(self.Job._fields['original_job_type'].index)
        self.assertTrue(self.Job._fields['original_job_type'].readonly)

    def test_original_job_type_cannot_be_forged_at_create(self):
        job = self._job(original_job_type='forged')
        self.assertEqual(job.original_job_type, 'core_dispatch_selftest')

    def test_terminal_jobs_are_retyped_without_log_loss(self):
        for state in TERMINAL_JOB_STATES:
            job = self._job(state=state)
            self.JobLog._system_append(job, 'note', 'pre-uninstall audit')
            before_ids = self.JobLog.search([('job_id', '=', job.id)]).ids
            job._reassign_to_historic_job_type()
            job.invalidate_recordset()
            self.assertEqual(job.state, state)
            self.assertEqual(job.job_type, 'historic_domain_job')
            self.assertEqual(job.original_job_type, 'core_dispatch_selftest')
            self.assertEqual(
                self.JobLog.search([('job_id', '=', job.id)]).ids,
                before_ids,
            )

    def test_non_terminal_jobs_are_cancelled_audited_then_retyped(self):
        cases = (
            ('draft', {}),
            ('queued', {}),
            ('running', {'started_at': fields.Datetime.now()}),
            ('retry_waiting', {'next_retry_at': fields.Datetime.now()}),
            ('failed_retryable', {}),
            (
                'blocked_manual_review',
                {
                    'manual_review_subreason': 'duplicate_risk',
                    'error_class': 'duplicate_risk',
                },
            ),
        )
        for state, extra in cases:
            job = self._job(state=state, **extra)
            job._reassign_to_historic_job_type()
            job.invalidate_recordset()
            self.assertEqual(job.state, 'cancelled')
            self.assertEqual(job.job_type, 'historic_domain_job')
            self.assertEqual(job.original_job_type, 'core_dispatch_selftest')
            self.assertTrue(job.cancel_reason)
            self.assertTrue(job.finished_at)
            self.assertFalse(job.manual_review_subreason)
            logs = self.JobLog.search([
                ('job_id', '=', job.id),
                ('event_type', '=', 'manual_action'),
            ])
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs.from_state, state)
            self.assertEqual(logs.to_state, 'cancelled')
            self.assertEqual(logs.actor_uid, self.env.user)

    def test_reassignment_is_idempotent_and_preserves_original_type(self):
        job = self._job()
        job._reassign_to_historic_job_type()
        first_log_ids = self.JobLog.search([('job_id', '=', job.id)]).ids
        job._reassign_to_historic_job_type()
        job.invalidate_recordset()
        self.assertEqual(job.original_job_type, 'core_dispatch_selftest')
        self.assertEqual(
            self.JobLog.search([('job_id', '=', job.id)]).ids,
            first_log_ids,
        )

    def test_dispatcher_refuses_direct_historic_job(self):
        # `_dispatch_one` is entered only after the dispatcher owns a running job.
        job = self._job(state='running', job_type='historic_domain_job')
        self.Dispatch._dispatch_one(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(job.error_class, 'unknown_system_error')
        self.assertIn(
            'audit-only',
            self.JobLog.search(
                [('job_id', '=', job.id)], order='id desc', limit=1,
            ).message,
        )

    def test_domain_selection_ondelete_uses_historic_callable(self):
        addons_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        for module, filename, job_type in (
            (
                'shopify_connector_product',
                'shopify_connector_product_importer.py',
                'product_import_sync',
            ),
            (
                'shopify_connector_sale',
                'shopify_connector_customer_importer.py',
                'customer_import_sync',
            ),
        ):
            path = os.path.join(addons_dir, module, 'models', filename)
            with open(path, encoding='utf-8') as source_file:
                tree = ast.parse(source_file.read())
            matching = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.Constant)
                and node.value == job_type
            ]
            self.assertTrue(matching, '%s registration is missing' % job_type)
            with open(path, encoding='utf-8') as source_file:
                source = source_file.read()
            self.assertIn(
                "'%s': lambda recs: "
                "recs._reassign_to_historic_job_type()" % job_type,
                source,
            )
            self.assertNotIn("'%s': 'cascade'" % job_type, source)

    def test_post_migration_is_additive_and_idempotent(self):
        module_dir = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(
            module_dir, 'migrations', '19.0.1.8.0', 'post-migrate.py',
        )
        with open(path, encoding='utf-8') as source_file:
            source = source_file.read()
        tree = ast.parse(source)
        self.assertIn('WHERE original_job_type IS NULL', source)
        self.assertIn('SET original_job_type = job_type', source)
        self.assertNotIn('DELETE FROM', source.upper())
        self.assertNotIn('DROP ', source.upper())
        self.assertTrue(any(
            isinstance(node, ast.FunctionDef) and node.name == 'migrate'
            for node in ast.walk(tree)
        ))

    def test_no_business_ondelete_or_log_unlink_is_introduced(self):
        job_source = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'models', 'shopify_connector_job.py',
        )
        with open(job_source, encoding='utf-8') as source_file:
            source = source_file.read()
        method = next(
            node for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef)
            and node.name == '_reassign_to_historic_job_type'
        )
        calls = [
            node for node in ast.walk(method)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        ]
        self.assertFalse(any(call.func.attr == 'unlink' for call in calls))
        self.assertEqual(
            len([call for call in calls if call.func.attr == 'sudo']),
            2,
        )
