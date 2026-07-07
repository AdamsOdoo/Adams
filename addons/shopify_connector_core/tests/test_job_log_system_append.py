import ast
import os

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class TestJobLogSystemAppend(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Job Log System Append Test Store',
            'shop_domain': 'job-log-system-append-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.user_operator = cls._create_group_user(
            'operator', 'group_shopify_connector_operator'
        )

    @classmethod
    def _create_group_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'Job Log System Append Test %s' % label,
            'login': 'job_log_system_append_test_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _create_job(self):
        job = self.env['shopify.connector.job'].create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_manual_maintenance',
            'state': 'running',
        })
        # Guards the Odoo 19 idempotency_key NOT NULL production fix:
        # every created job must end up with a populated key.
        self.assertTrue(job.idempotency_key)
        return job

    # 29. _system_append creates exactly one row with the given fields.
    def test_system_append_creates_one_row(self):
        job = self._create_job()
        JobLog = self.env['shopify.connector.job.log']
        before = JobLog.search_count([('job_id', '=', job.id)])
        JobLog._system_append(
            job, 'attempt', 'Hello world.',
            technical_detail='detail', from_state='running',
            to_state='succeeded',
        )
        rows = JobLog.search([('job_id', '=', job.id)], order='id asc')
        self.assertEqual(len(rows), before + 1)
        row = rows[-1]
        self.assertEqual(row.event_type, 'attempt')
        self.assertEqual(row.from_state, 'running')
        self.assertEqual(row.to_state, 'succeeded')
        self.assertEqual(row.message, 'Hello world.')
        self.assertEqual(row.technical_detail, 'detail')

    # 30. Elevation, not a widened ACL, is what makes indirect append work.
    def test_non_admin_indirect_append_succeeds_but_direct_create_denied(self):
        job = self._create_job()
        JobLog = self.env['shopify.connector.job.log']
        JobLog_as_operator = JobLog.with_user(self.user_operator)
        with self.assertRaises(AccessError):
            JobLog_as_operator.create({
                'job_id': job.id,
                'event_type': 'note',
                'message': 'direct create attempt',
            })
        before = JobLog.search_count([('job_id', '=', job.id)])
        JobLog_as_operator._system_append(
            job, 'note', 'Indirect append via the sanctioned elevation.',
        )
        after = JobLog.search_count([('job_id', '=', job.id)])
        self.assertEqual(after, before + 1)

    # 31. Source-level guard: exactly two sudo( occurrences in the whole diff.
    def test_source_level_two_sudo_sites_total(self):
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )
        sudo_call_sites = []
        for filename in sorted(os.listdir(models_dir)):
            if not filename.endswith('.py'):
                continue
            path = os.path.join(models_dir, filename)
            with open(path, 'r', encoding='utf-8') as source_file:
                tree = ast.parse(source_file.read(), filename=filename)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'sudo'
                ):
                    sudo_call_sites.append(filename)
        self.assertEqual(
            sorted(sudo_call_sites),
            [
                'shopify_connector_job_log.py',
                'shopify_connector_store_credential.py',
            ],
        )

    # 32. Redaction: a dummy token passed to _system_append is never persisted.
    def test_redaction_of_message_technical_detail_payload_snapshot(self):
        job = self._create_job()
        JobLog = self.env['shopify.connector.job.log']
        JobLog._system_append(
            job, 'note',
            'token %s in message' % DUMMY_TOKEN,
            technical_detail='token %s in detail' % DUMMY_TOKEN,
            payload_snapshot='token %s in snapshot' % DUMMY_TOKEN,
        )
        row = JobLog.search(
            [('job_id', '=', job.id)], order='id desc', limit=1,
        )
        self.assertNotIn(DUMMY_TOKEN, row.message)
        self.assertNotIn(DUMMY_TOKEN, row.technical_detail)
        self.assertNotIn(DUMMY_TOKEN, row.payload_snapshot)
