import ast
import os

from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase

DUMMY_TOKEN_1 = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
DUMMY_TOKEN_2 = 'shpat_DUMMYDUMMYDUMMY1111111111111111'


class TestCredentialService(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Credential Service Test Store',
            'shop_domain': 'credential-service-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.user_auditor = cls._create_group_user(
            'auditor', 'group_shopify_connector_auditor'
        )
        cls.user_operator = cls._create_group_user(
            'operator', 'group_shopify_connector_operator'
        )
        cls.user_reviewer = cls._create_group_user(
            'reviewer', 'group_shopify_connector_reviewer'
        )
        cls.user_admin = cls._create_group_user(
            'admin', 'group_shopify_connector_admin'
        )

    @classmethod
    def _create_group_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'Credential Service Test %s' % label,
            'login': 'credential_service_test_%s' % label,
            'groups_id': [(6, 0, [group.id])],
        })

    def _credential_as_admin(self):
        return self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        )

    def _assert_dummy_absent_except_access_token(self, token):
        store_fields = self.store.fields_get()
        for field_name, field_info in store_fields.items():
            if field_info['type'] not in ('char', 'text'):
                continue
            value = self.store[field_name]
            if value:
                self.assertNotIn(token, value)
        credential = self._credential_as_admin().search(
            [('store_id', '=', self.store.id)]
        )
        if not credential:
            return
        credential_fields = credential.fields_get()
        for field_name, field_info in credential_fields.items():
            if field_name == 'access_token':
                continue
            if field_info['type'] not in ('char', 'text'):
                continue
            value = credential[field_name]
            if value:
                self.assertNotIn(token, value)

    def test_action_set_token_creates_row_and_mirrors(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(len(credential), 1)
        self.assertEqual(credential.credential_state, 'present')
        self.store.invalidate_recordset()
        self.assertTrue(self.store.credential_present)
        self._assert_dummy_absent_except_access_token(DUMMY_TOKEN_1)

    def test_action_replace_token_stamps_and_resets_verification(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({
            'credential_last_verified_at': '2026-07-07 00:00:00',
        })
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertTrue(self.store.credential_last_replaced_at)
        self.assertFalse(self.store.credential_last_verified_at)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.access_token, DUMMY_TOKEN_2)
        self._assert_dummy_absent_except_access_token(DUMMY_TOKEN_2)

    def test_action_clear_token_empties_and_preserves_history(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        replaced_at = self.store.credential_last_replaced_at
        Credential.action_clear_token(self.store)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(len(credential), 1)
        self.assertFalse(credential.access_token)
        self.assertEqual(credential.credential_state, 'absent')
        self.store.invalidate_recordset()
        self.assertFalse(self.store.credential_present)
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertFalse(self.store.credential_last_failure_reason)
        self.assertEqual(self.store.credential_last_replaced_at, replaced_at)
        self._assert_dummy_absent_except_access_token(DUMMY_TOKEN_2)

    def test_action_clear_token_idempotent_with_no_existing_row(self):
        Credential = self._credential_as_admin()
        Credential.action_clear_token(self.store)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertFalse(credential)

    def test_duplicate_credential_row_for_same_store_raises(self):
        Credential = self._credential_as_admin()
        Credential.create({'store_id': self.store.id})
        with self.assertRaises(ValidationError):
            Credential.create({'store_id': self.store.id})

    def test_empty_or_non_string_value_raises_without_echoing(self):
        Credential = self._credential_as_admin()
        for bad_value in ('', None, 12345):
            with self.assertRaises(ValidationError) as catcher:
                Credential.action_set_token(self.store, bad_value)
            self.assertNotIn(str(bad_value), str(catcher.exception))
            with self.assertRaises(ValidationError) as catcher:
                Credential.action_replace_token(self.store, bad_value)
            self.assertNotIn(str(bad_value), str(catcher.exception))

    def test_stamps_based_audit_reflects_acting_admin(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.create_uid, self.user_admin)
        self.assertEqual(credential.write_uid, self.user_admin)
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        credential.invalidate_recordset()
        self.assertEqual(credential.write_uid, self.user_admin)
        self.assertTrue(credential.write_date)

    def test_no_job_or_job_log_rows_written(self):
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job_count_before = Job.search_count([])
        job_log_count_before = JobLog.search_count([])
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        Credential.action_clear_token(self.store)
        self.assertEqual(Job.search_count([]), job_count_before)
        self.assertEqual(JobLog.search_count([]), job_log_count_before)

    def test_get_access_token_internal_and_write_paths_denied_for_non_admin(self):
        Credential = self.env['shopify.connector.store.credential']
        self._credential_as_admin().action_set_token(self.store, DUMMY_TOKEN_1)
        self.assertEqual(
            Credential._get_access_token(self.store), DUMMY_TOKEN_1
        )
        credential_as_operator = Credential.with_user(self.user_operator)
        with self.assertRaises(AccessError):
            credential_as_operator.action_set_token(self.store, DUMMY_TOKEN_2)
        with self.assertRaises(AccessError):
            credential_as_operator.action_replace_token(
                self.store, DUMMY_TOKEN_2
            )
        with self.assertRaises(AccessError):
            credential_as_operator.action_clear_token(self.store)

    def test_source_level_single_sudo_guard(self):
        # AST-based, not a text grep: docstrings are required to explain
        # `sudo()` in prose (per this task's own docstring contract), so a
        # substring count would false-positive on them. Only real
        # `<expr>.sudo(...)` call sites count.
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
            sudo_call_sites, ['shopify_connector_store_credential.py']
        )

    def test_all_service_methods_decorated_with_api_model(self):
        # AST-based, matching the sudo guard's approach: proves the
        # decorator is actually present on each method definition, not
        # just mentioned somewhere in the file.
        target_methods = {
            'action_set_token',
            'action_replace_token',
            'action_clear_token',
            '_get_access_token',
        }
        credential_model_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
            'shopify_connector_store_credential.py',
        )
        with open(credential_model_path, 'r', encoding='utf-8') as source_file:
            tree = ast.parse(
                source_file.read(), filename=credential_model_path
            )
        decorated_methods = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in target_methods:
                for decorator in node.decorator_list:
                    if (
                        isinstance(decorator, ast.Attribute)
                        and decorator.attr == 'model'
                        and isinstance(decorator.value, ast.Name)
                        and decorator.value.id == 'api'
                    ):
                        decorated_methods.add(node.name)
        self.assertEqual(decorated_methods, target_methods)
