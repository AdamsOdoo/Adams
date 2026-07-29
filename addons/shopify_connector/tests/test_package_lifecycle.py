from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_package import REQUIRED_TECHNICAL_MODULES


@tagged('post_install', '-at_install')
class TestPackageLifecycle(TransactionCase):
    """Unit-level proof of the package model's own state machine.

    Deliberately does NOT call any real `button_install`/`button_uninstall`
    (forbidden inside a test transaction -- `modules.module.current_test`,
    see `ir_module.py::_button_immediate_function`). Instead it simulates a
    missing technical module by writing `ir.module.module.state` directly
    (an ordinary rolled-back ORM write, not a module operation), which is
    enough to exercise every branch of `_compute_integrity`/
    `_apply_detected_state`/`assert_healthy` without touching the registry.
    The REAL cascade -- Odoo actually uninstalling a technical module when a
    standard dependency is removed -- is proved separately by the disposable-
    database harness (`tools/shopify_connector_package_lifecycle_check.py`),
    which this test suite cannot and does not substitute for.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Package = cls.env['shopify.connector.package']
        cls.Module = cls.env['ir.module.module'].sudo()

    def setUp(self):
        super().setUp()
        # Every state-changing method on this model persists via an
        # independent `registry.cursor()` side transaction (see
        # `_commit_via_side_cursor`'s docstring). Without registry test
        # mode that side cursor is a genuinely separate connection: the
        # package singleton it creates on the very first call would be
        # REALLY committed and would leak into every later test in this
        # class (and beyond) instead of rolling back with the rest of the
        # test's fixtures, and a same-row write immediately after an
        # uncommitted write in this test's own transaction would simply
        # hang waiting for a lock this same test is holding. Test mode
        # makes every `registry.cursor()` reuse this one test connection
        # instead (the same fix `test_api_client.py` applies).
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _break_module(self, name, state='uninstalled'):
        module = self.Module.search([('name', '=', name)])
        module.write({'state': state})
        return module

    def test_fresh_singleton_is_healthy_when_everything_installed(self):
        record = self.Package._get_singleton()
        integrity, _effective_state = record._apply_detected_state()
        self.assertTrue(integrity['healthy'])
        self.assertEqual(record.state, 'healthy')
        self.assertFalse(record.missing_technical_modules)

    def test_get_singleton_is_idempotent(self):
        first = self.Package._get_singleton()
        second = self.Package._get_singleton()
        self.assertEqual(first.id, second.id)
        self.assertEqual(self.Package.search_count([]), 1)

    def test_assert_healthy_passes_silently_when_healthy(self):
        # Must not raise.
        self.Package.assert_healthy()

    def test_missing_technical_module_pauses_and_reports_missing_app(self):
        # Break both the technical module AND its standard Odoo dependency
        # -- the ordinary dependency-loss shape a real `stock` uninstall
        # cascade produces (proved end-to-end by the disposable-database
        # harness). Breaking only the technical module is covered by
        # test_abnormal_partial_state_falls_back_to_technical_module_name
        # below.
        #
        # The state-mutating call (`_apply_detected_state`) is invoked
        # directly here, OUTSIDE any `assertRaises` block, on purpose:
        # Odoo's own `TransactionCase.assertRaises` takes a savepoint
        # before its body and rolls it back the instant the expected
        # exception fires (`odoo/tests/common.py::_assertRaises`), which
        # would silently undo this same write if it were made inside that
        # block. That savepoint rollback is a test-harness artifact -- in
        # real production the state persists via a genuinely separate,
        # already-committed connection (`_commit_via_side_cursor`) that a
        # later exception/rollback elsewhere in the SAME request cannot
        # touch; the disposable-database harness
        # (tools/shopify_connector_package_lifecycle_check.sh) is what
        # proves that property end-to-end. This test asserts the pause
        # LOGIC; `test_assert_healthy_raises_with_the_correct_message`
        # below asserts the exception separately.
        self._break_module('shopify_connector_inventory')
        self._break_module('stock')
        record = self.Package._get_singleton()
        integrity, _effective_state = record._apply_detected_state()
        self.assertFalse(integrity['healthy'])
        self.assertEqual(record.state, 'dependency_paused')
        self.assertIn('shopify_connector_inventory', record.missing_technical_modules)
        self.assertIn('Inventory', record.missing_standard_apps)
        self.assertTrue(record.paused_at)
        self.assertEqual(record.prior_state, 'healthy')

    def test_assert_healthy_raises_with_the_correct_message(self):
        self._break_module('shopify_connector_inventory')
        self._break_module('stock')
        with self.assertRaises(UserError) as cm:
            self.Package.assert_healthy()
        self.assertIn('paused', str(cm.exception))
        self.assertIn('Inventory', str(cm.exception))

    def test_abnormal_partial_state_falls_back_to_technical_module_name(self):
        # The technical module alone goes missing while its standard Odoo
        # dependency is untouched (Section 11: an abnormal partial state,
        # not an ordinary dependency loss) -- `missing_standard_apps` is
        # correctly empty, so the message must fall back to naming the
        # technical component directly rather than a bare "unknown".
        self._break_module('shopify_connector_inventory')
        with self.assertRaises(UserError) as cm:
            self.Package.assert_healthy()
        self.assertIn('paused', str(cm.exception))
        self.assertIn('shopify_connector_inventory', str(cm.exception))
        self.assertNotIn('unknown', str(cm.exception))
        record = self.Package._get_singleton()
        self.assertFalse(record.missing_standard_apps)

    def test_pause_state_is_sticky_until_explicit_resume(self):
        # See test_missing_technical_module_pauses_and_reports_missing_app
        # for why the state-mutating calls below run outside `assertRaises`.
        self._break_module('shopify_connector_inventory')
        record = self.Package._get_singleton()
        record._apply_detected_state()
        self.assertEqual(record.state, 'dependency_paused')
        # Restore the module row directly (simulating the technical module
        # coming back) WITHOUT calling the explicit resume action.
        self._break_module('shopify_connector_inventory', state='installed')
        record._apply_detected_state()
        self.assertEqual(
            record.state, 'dependency_paused',
            "state must never auto-heal back to healthy on its own",
        )
        with self.assertRaises(UserError):
            self.Package.assert_healthy()

    def test_action_confirm_resume_requires_genuine_integrity(self):
        self._break_module('shopify_connector_inventory')
        record = self.Package._get_singleton()
        record._apply_detected_state()
        self.assertEqual(record.state, 'dependency_paused')
        with self.assertRaises(UserError):
            record.action_confirm_resume()
        record.invalidate_recordset()
        self.assertEqual(
            record.state, 'dependency_paused',
            "a refused resume must not have changed anything",
        )
        self._break_module('shopify_connector_inventory', state='installed')
        record.action_confirm_resume()
        self.assertEqual(record.state, 'healthy')
        self.assertTrue(record.resumed_at)
        self.assertEqual(record.resumed_by_uid, self.env.user)

    def test_action_restore_suite_refuses_while_standard_app_missing(self):
        self._break_module('stock', state='uninstalled')
        self._break_module('shopify_connector_inventory')
        record = self.Package._get_singleton()
        record._apply_detected_state()
        with self.assertRaises(UserError) as cm:
            record.action_restore_suite()
        self.assertIn('Inventory', str(cm.exception))

    def test_action_restore_suite_is_a_noop_when_already_healthy(self):
        record = self.Package._get_singleton()
        integrity = record.action_restore_suite()
        self.assertTrue(integrity['healthy'])
        self.assertEqual(record.state, 'healthy')

    def test_required_technical_modules_matches_verified_manifest_graph(self):
        # Guards against the constant silently drifting from the actual
        # addons on disk (Section 5/6: never treat a hand-maintained list
        # as final without verifying it against the real manifests).
        self.assertEqual(
            set(REQUIRED_TECHNICAL_MODULES),
            {
                'shopify_connector_core',
                'shopify_connector_product',
                'shopify_connector_product_export',
                'shopify_connector_sale',
                'shopify_connector_inventory',
                'shopify_connector_fulfillment',
            },
        )
        for name in REQUIRED_TECHNICAL_MODULES:
            module = self.Module.search([('name', '=', name)])
            self.assertTrue(module, "%s must exist as an installable module" % name)

    def test_non_admin_cannot_run_restore_workflow(self):
        internal_user = self.env['res.users'].create({
            'name': 'Non Admin', 'login': 'non_admin_pkg_test',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        record = self.Package._get_singleton()
        with self.assertRaises(UserError):
            record.with_user(internal_user).action_recheck_dependencies()
        with self.assertRaises(UserError):
            record.with_user(internal_user).action_restore_suite()
        with self.assertRaises(UserError):
            record.with_user(internal_user).action_confirm_resume()
