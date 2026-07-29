from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_package import REQUIRED_TECHNICAL_MODULES


@tagged('post_install', '-at_install')
class TestUninstallGuard(TransactionCase):
    """Exercises `IrModuleModuleUninstallGuard.button_uninstall` directly.

    Deliberately calls the DEFERRED `button_uninstall` (a plain state write,
    safe inside a rolled-back test transaction), never
    `button_immediate_uninstall`/the `base.module.uninstall` wizard's
    `action_uninstall` -- both delegate to `button_immediate_uninstall`,
    which raises `RuntimeError` for ANY module operation inside a test
    (`modules.module.current_test`, see `_button_immediate_function`)
    before this guard would ever run. The guard logic under test here is
    identical either way (the immediate variant calls this same
    `button_uninstall`); the real end-to-end proof through the immediate/
    wizard/RPC paths is the disposable-database harness
    (`tools/shopify_connector_package_lifecycle_check.py`), which this test
    class complements rather than duplicates.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Module = cls.env['ir.module.module'].sudo()

    def _module(self, name):
        return self.Module.search([('name', '=', name)])

    def test_direct_uninstall_of_a_technical_module_alone_is_refused(self):
        core = self._module('shopify_connector_core')
        with self.assertRaises(UserError) as cm:
            core.button_uninstall()
        self.assertIn('shopify_connector_core', str(cm.exception))
        self.assertIn('Shopify Connector', str(cm.exception))
        core.invalidate_recordset()
        self.assertEqual(core.state, 'installed')

    def test_direct_uninstall_of_each_technical_module_alone_is_refused(self):
        for name in REQUIRED_TECHNICAL_MODULES:
            with self.subTest(module=name):
                module = self._module(name)
                with self.assertRaises(UserError):
                    module.button_uninstall()
                module.invalidate_recordset()
                self.assertEqual(module.state, 'installed')

    def test_crafted_co_selection_with_a_standard_app_is_still_refused(self):
        core = self._module('shopify_connector_core')
        stock = self._module('stock')
        combo = core + stock
        with self.assertRaises(UserError):
            combo.button_uninstall()
        core.invalidate_recordset()
        stock.invalidate_recordset()
        self.assertEqual(core.state, 'installed')
        self.assertEqual(stock.state, 'installed')

    def test_uninstalling_the_umbrella_package_is_allowed(self):
        package = self._module('shopify_connector')
        # Must not raise; must cascade through Odoo's own
        # downstream_dependencies (every technical module depends on the
        # package, see docs/03-architecture/single-package-lifecycle.md).
        package.button_uninstall()
        package.invalidate_recordset()
        self.assertEqual(package.state, 'to remove')
        for name in REQUIRED_TECHNICAL_MODULES:
            module = self._module(name)
            module.invalidate_recordset()
            self.assertEqual(
                module.state, 'to remove',
                "%s must be swept into the package's own uninstall cascade" % name,
            )

    def test_legitimate_standard_dependency_removal_is_unaffected(self):
        # A root selection with zero connector modules must pass straight
        # through to Odoo's own behaviour, untouched by this guard.
        stock = self._module('stock')
        stock.button_uninstall()
        stock.invalidate_recordset()
        self.assertEqual(stock.state, 'to remove')
        inventory = self._module('shopify_connector_inventory')
        inventory.invalidate_recordset()
        self.assertEqual(
            inventory.state, 'to remove',
            "Odoo's own cascade must still reach the dependent technical module",
        )
        # The package and core, upstream of the removed standard app, must
        # be untouched by this same call.
        core = self._module('shopify_connector_core')
        package = self._module('shopify_connector')
        core.invalidate_recordset()
        package.invalidate_recordset()
        self.assertEqual(core.state, 'installed')
        self.assertEqual(package.state, 'installed')
