"""Static CI contract for candidate-only DEC-029 meta-addon installs."""

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "tools" / "run_connector_suite.sh"


class TestConnectorSuiteMetaInstallContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = RUNNER.read_text(encoding="utf-8")

    def test_candidate_meta_addons_are_installed_as_a_separate_pass(self):
        self.assertIn(
            'META_MODULES="shopify_connector_lite,shopify_connector_full"',
            self.runner,
        )
        self.assertIn("run_meta_install_edition lite shopify_connector_lite", self.runner)
        self.assertIn("run_meta_install_edition full shopify_connector_full", self.runner)
        self.assertIn(
            'META_LITE_EXPECTED="shopify_connector_lite,shopify_connector_core,shopify_connector_product,shopify_connector_sale,shopify_connector_webhook,shopify_connector_product_webhook,shopify_connector_sale_webhook"',
            self.runner,
        )
        self.assertIn(
            'META_FULL_EXPECTED="shopify_connector_full,shopify_connector_core,shopify_connector_product,shopify_connector_sale,shopify_connector_inventory,shopify_connector_fulfillment,shopify_connector_product_export,shopify_connector_webhook,shopify_connector_product_webhook,shopify_connector_sale_webhook,shopify_connector_inventory_webhook,shopify_connector_fulfillment_webhook"',
            self.runner,
        )
        self.assertIn('RUN_META_INSTALL=1', self.runner)
        self.assertIn('--skip-meta-install', self.runner)
        self.assertIn('run_meta_install || true', self.runner)
        self.assertIn('"dec029_meta_install"', self.runner)

    def test_old_tree_migration_set_excludes_new_meta_addons(self):
        self.assertIn('MIGRATION_MODULES="$MODULES"', self.runner)
        migration_start = self.runner.index(
            "# --- Pass 2b: genuine version-to-version migrations"
        )
        migration_end = self.runner.index("# --- Pass 3: the non-standard tag suite")
        migration_block = self.runner[migration_start:migration_end]
        for meta in ("shopify_connector_lite", "shopify_connector_full"):
            self.assertNotIn(meta, migration_block)
        self.assertIn('-i "${MIGRATION_MODULES},${EXTRA_MODULES}"', migration_block)
        self.assertIn('-u "$MIGRATION_MODULES"', migration_block)

    def test_meta_install_checks_the_entire_expected_module_set(self):
        start = self.runner.index("run_meta_install_edition()")
        end = self.runner.index("run_meta_install()", start)
        function = self.runner[start:end]
        self.assertIn('run_odoo "$db" "$logfile" -i "$meta"', function)
        self.assertIn("SELECT state FROM ir_module_module", function)
        self.assertIn('[[ "$state" != "installed" ]]', function)
        self.assertIn('META_LITE_EXPECTED=', self.runner)
        self.assertIn('META_FULL_EXPECTED=', self.runner)


if __name__ == "__main__":
    unittest.main()
