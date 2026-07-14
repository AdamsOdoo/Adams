import ast
import os

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger

from ..models import shopify_connector_store_credential as credential_module
# Reusable AST source-guard helpers (control-room review 4692156428). Defined
# once in test_disconnect_quiescence (imported earlier by tests/__init__.py,
# mirroring the existing `from .test_api_client import ...` convention) so the
# executable-AST inspection is shared, not duplicated.
from .test_disconnect_quiescence import (
    guard_called_names,
    guard_fn_ast,
    guard_min_call_lineno,
    guard_str_constants,
)

DUMMY_TOKEN_1 = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
DUMMY_TOKEN_2 = 'shpat_DUMMYDUMMYDUMMY1111111111111111'
CREDENTIAL_VALUE_ERROR_MESSAGE = 'A non-empty credential value is required.'


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
            'group_ids': [(6, 0, [group.id])],
        })

    def _credential_as_admin(self):
        return self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        )

    def search_credential(self):
        return self._credential_as_admin().search(
            [('store_id', '=', self.store.id)], limit=1
        )

    def _assert_dummy_absent_except_access_token(self, token):
        # fields_get() here is schema enumeration only (which char/text
        # fields exist), not a security oracle -- the actual assertion is
        # the value-content scan below, run as admin against already-
        # fetched records, unrelated to any ACL/visibility check.
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

    def test_action_set_token_update_on_connected_store_moves_to_reconnect_needed(self):
        # PR #121 Revision 5: credential mutation must invalidate
        # store.state, not just credential_last_verified_at --
        # business-job gating keys off store.state, so a 'connected'
        # store must not remain 'connected' after its token is
        # silently overwritten via action_set_token().
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({
            'state': 'connected',
            'credential_last_verified_at': '2026-07-07 00:00:00',
        })
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job_count_before = Job.search_count([])
        job_log_count_before = JobLog.search_count([])

        Credential.action_set_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertEqual(Job.search_count([]), job_count_before)
        self.assertEqual(JobLog.search_count([]), job_log_count_before)

    def test_action_replace_token_on_connected_store_moves_to_reconnect_needed(self):
        # PR #121 Revision 5: same invalidation requirement as
        # action_set_token(), for the replace path.
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({
            'state': 'connected',
            'credential_last_verified_at': '2026-07-07 00:00:00',
        })
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job_count_before = Job.search_count([])
        job_log_count_before = JobLog.search_count([])

        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertFalse(self.store.credential_last_verified_at)
        self.assertEqual(Job.search_count([]), job_count_before)
        self.assertEqual(JobLog.search_count([]), job_log_count_before)

    # ------------------------------------------------------------------
    # CORE-R2 (AR-047; review 4690639375 #3): store->credential lock order,
    # refuse-while-disconnecting, and connected-replacement epoch bump.
    # ------------------------------------------------------------------

    def test_set_token_refused_while_disconnecting(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnecting', 'connection_generation': 3})
        with self.assertRaises(UserError):
            Credential.action_set_token(self.store, DUMMY_TOKEN_2)
        # Original credential, mirrors, and generation are all unchanged.
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.connection_generation, 3)

    def test_replace_token_refused_while_disconnecting(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnecting', 'connection_generation': 3})
        with self.assertRaises(UserError):
            Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.connection_generation, 3)

    def test_connected_set_token_bumps_generation_exactly_once(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'connected', 'connection_generation': 5})
        Credential.action_set_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self.store.connection_generation, 6)
        self.assertFalse(self.store.credential_last_verified_at)

    def test_connected_replace_token_bumps_generation_exactly_once(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'connected', 'connection_generation': 5})
        Credential.action_replace_token(self.store, DUMMY_TOKEN_2)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self.store.connection_generation, 6)
        self.assertTrue(self.store.credential_last_replaced_at)

    def test_non_connected_set_token_does_not_bump_generation(self):
        # A set/replace on a non-connected, non-disconnecting store preserves the
        # state and adds NO extra generation bump (review §5.8).
        Credential = self._credential_as_admin()
        self.store.write({'state': 'reconnect_needed', 'connection_generation': 7})
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'reconnect_needed')
        self.assertEqual(self.store.connection_generation, 7)

    def test_mutate_token_locks_store_before_credential_source(self):
        # store -> credential global lock order: _mutate_token takes the store
        # update lock (store._lock_store_for_lifecycle) BEFORE it reads/writes the
        # credential row, refuses while disconnecting, and uses no sudo().
        #
        # AST-robust (control-room review 4692156428): inspect the EXECUTABLE
        # body -- not raw source text -- so the method docstring's "normal ACL,
        # **no `sudo()`**" prose is NOT a false positive. All three original
        # safety assertions are preserved, now evaluated against real code.
        fn = guard_fn_ast(
            credential_module.ShopifyConnectorStoreCredential._mutate_token
        )
        lock_line = guard_min_call_lineno(fn, '_lock_store_for_lifecycle')
        search_line = guard_min_call_lineno(fn, 'search', receiver_name='self')
        self.assertIsNotNone(lock_line, 'the store lifecycle lock must be taken')
        self.assertIsNotNone(search_line, 'the credential row must be searched')
        self.assertLess(
            lock_line, search_line,
            'the store row must be locked before the credential row is read/written',
        )
        # refuse-while-disconnecting: the executable code compares the freshly
        # locked state against the 'disconnecting' literal.
        self.assertIn('disconnecting', guard_str_constants(fn))
        # no sudo() call anywhere in the mutation path (docstring prose excluded).
        self.assertNotIn('sudo', guard_called_names(fn))

    def test_action_clear_token_on_connected_store_requests_two_phase_disconnect(self):
        # CORE-R2 (reviews 4690804619 #2 + 4690807427): public clear on a
        # `connected` store must NOT clear immediately (an admitted lease can
        # outlive admission's FOR SHARE). It routes through the accepted two-phase
        # disconnect: state -> `disconnecting`, credential STILL present, exactly
        # one epoch bump, an audited request -- the controller clears at finalize.
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'connected'})
        self.store.invalidate_recordset()
        gen_before = self.store.connection_generation

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.disconnect_status, 'requested')
        self.assertTrue(self.store.credential_present)   # NOT cleared yet
        self.assertEqual(self.store.connection_generation, gen_before + 1)
        credential = self.search_credential()
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)

    def test_action_clear_token_on_reconnect_needed_store_requests_two_phase_disconnect(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'reconnect_needed'})
        self.store.invalidate_recordset()
        gen_before = self.store.connection_generation

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        self.assertEqual(self.store.disconnect_status, 'requested')
        self.assertTrue(self.store.credential_present)   # NOT cleared yet
        self.assertEqual(self.store.connection_generation, gen_before + 1)
        credential = self.search_credential()
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)

    def test_action_clear_token_refused_while_disconnecting(self):
        # Public clear must refuse while a disconnect is in progress -- the
        # controller owns the clear at completed/timed_out.
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnecting'})
        with self.assertRaises(UserError):
            Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnecting')
        # Credential untouched by the refused clear.
        credential = self.search_credential()
        self.assertEqual(credential.access_token, DUMMY_TOKEN_1)
        self.assertTrue(self.store.credential_present)

    def test_action_clear_token_direct_clear_from_setup_incomplete(self):
        # A never-connected store has no active-business-call posture, so the
        # public clear empties the credential directly (no disconnect request).
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.assertEqual(self.store.state, 'setup_incomplete')
        Job = self.env['shopify.connector.job']
        job_count_before = Job.search_count([])

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'setup_incomplete')
        self.assertFalse(self.store.credential_present)
        credential = self.search_credential()
        self.assertFalse(credential.access_token)
        self.assertEqual(credential.credential_state, 'absent')
        # A direct clear is not an audited lifecycle action -- no job rows.
        self.assertEqual(Job.search_count([]), job_count_before)

    def test_action_clear_token_direct_clear_from_disconnected(self):
        Credential = self._credential_as_admin()
        Credential.action_set_token(self.store, DUMMY_TOKEN_1)
        self.store.write({'state': 'disconnected'})
        Job = self.env['shopify.connector.job']
        job_count_before = Job.search_count([])

        Credential.action_clear_token(self.store)
        self.store.invalidate_recordset()
        self.assertEqual(self.store.state, 'disconnected')
        self.assertFalse(self.store.credential_present)
        self.assertEqual(Job.search_count([]), job_count_before)

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

    # mute_logger: the second create() below intentionally triggers the
    # store_id UNIQUE constraint (shopify_connector_store_credential_
    # store_id_uniq); without muting, Odoo's `odoo.sql_db` logger emits
    # an avoidable ERROR-level "bad query" line for this expected failure.
    @mute_logger('odoo.sql_db')
    def test_duplicate_credential_row_for_same_store_raises(self):
        # A fresh, test-local store (not the shared class-level
        # `self.store`) so this scenario can never collide with a
        # credential row another test method left on the class store.
        Credential = self._credential_as_admin()
        store = self.env['shopify.connector.store'].create({
            'name': 'Duplicate Credential Test Store',
            'shop_domain': 'duplicate-credential-test.myshopify.com',
            'api_version': '2026-07',
        })
        Credential.create({'store_id': store.id})
        # The second create()'s UNIQUE(store_id) violation is a raw
        # database-level error (Odoo 19 `models.Constraint`, not a Python
        # `@api.constrains` ValidationError) -- run it under its own
        # savepoint so the expected failure does not poison the rest of
        # this test's transaction, mirroring the existing
        # `test_core_readiness_check_untouched_still_collides` pattern for
        # the job model's own unique constraint.
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                Credential.create({'store_id': store.id})

    def test_empty_or_non_string_value_raises_without_echoing(self):
        Credential = self._credential_as_admin()
        for bad_value in ('', None, 12345):
            with self.assertRaises(ValidationError) as catcher:
                Credential.action_set_token(self.store, bad_value)
            self.assertEqual(
                str(catcher.exception), CREDENTIAL_VALUE_ERROR_MESSAGE
            )
            with self.assertRaises(ValidationError) as catcher:
                Credential.action_replace_token(self.store, bad_value)
            self.assertEqual(
                str(catcher.exception), CREDENTIAL_VALUE_ERROR_MESSAGE
            )

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

    def test_source_level_sanctioned_sudo_sites_guard(self):
        # AST-based, not a text grep: docstrings are required to explain
        # `sudo()` in prose (per this task's own docstring contract), so a
        # substring count would false-positive on them. Only real
        # `<expr>.sudo(...)` call sites count.
        #
        # Exactly three sanctioned sudo() sites are expected as of Task
        # CORE-R1 (gate amendment `4948368039`): the pre-existing Task 002
        # `_get_access_token` accessor (`shopify_connector_store_
        # credential.py`), the Task 003 job-log `_system_append`
        # system-append writer (`shopify_connector_job_log.py`), and the
        # CORE-R1 narrow, read-only readiness drain-cron read
        # (`shopify_connector_readiness_check.py`, `_drain_cron_active_
        # state`). Any fourth site is a review failure -- this guard must
        # not be weakened (exact-list equality, no `>= 3`/substring/
        # wildcard/count-only relaxation).
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
                'shopify_connector_readiness_check.py',
                'shopify_connector_store_credential.py',
            ],
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
