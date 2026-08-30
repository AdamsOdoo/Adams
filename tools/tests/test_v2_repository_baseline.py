import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools import v2_repository_baseline as baseline


class TestV2RepositoryBaseline(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self._write(
            "addons/shopify_connector_core/__manifest__.py",
            "{'name': 'Core', 'version': '1.0', 'depends': ['base'], "
            "'data': ['security/access.csv', 'views/ui.xml'], "
            "'uninstall_hook': 'uninstall_hook'}\n",
        )
        self._write(
            "addons/shopify_connector_core/models/store.py",
            "from odoo import api, fields, models\n"
            "SHOPIFY_API_VERSION = '2026-07'\n"
            "QUERY = '''query StoreIdentity($id: ID!) { shop { id } }'''\n"
            "class Store(models.Model):\n"
            "    _name = 'shopify.connector.store'\n"
            "    name = fields.Char(required=True, index=True)\n"
            "    state = fields.Selection([('draft', 'Draft')], store=True)\n"
            "    _name_unique = models.Constraint('UNIQUE(name)', 'unique')\n"
            "    @api.constrains('name')\n"
            "    def _check_name(self):\n"
            "        pass\n"
            "    def action_open(self):\n"
            "        return True\n",
        )
        self._write(
            "addons/shopify_connector_core/tests/test_cross_import.py",
            "from odoo.addons.shopify_connector_product.models import product\n",
        )
        self._write(
            "addons/shopify_connector_core/security/access.csv",
            "id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink\n"
            "access_store,store,model_shopify_connector_store,base.group_user,1,0,0,0\n",
        )
        self._write(
            "addons/shopify_connector_core/views/ui.xml",
            "<odoo>"
            "<record id='action_store' model='ir.actions.act_window'/>"
            "<menuitem id='menu_store' action='action_store'/>"
            "<record id='cron_store' model='ir.cron'><field name='code'>model.run()</field></record>"
            "</odoo>\n",
        )
        self._write(
            "addons/shopify_connector_core/static/src/js/tours/store.js",
            "const tours = registry.category('web_tour.tours');\n"
            "tours.add(\n  'store_tour', { steps: () => [] });\n",
        )
        self._write(
            "addons/shopify_connector_product/__manifest__.py",
            "{'name': 'Product', 'version': '1.0', "
            "'depends': ['shopify_connector_core'], 'data': []}\n",
        )
        self._write(
            "addons/shopify_connector_product/models/product.py",
            "from odoo import fields, models\n"
            "from odoo.addons.shopify_connector_core.models.store import QUERY\n"
            "MUTATION = '''mutation ProductCreate($input: ProductInput!) { "
            "productCreate(product: $input) { userErrors { message } } }'''\n"
            "class Product(models.Model):\n"
            "    _name = 'shopify.connector.product'\n"
            "    store_id = fields.Many2one('shopify.connector.store', required=True)\n",
        )
        self._write(
            "tools/perf0_baseline.py",
            "SCENARIOS = ('job_enqueue', 'job_drain')\n",
        )
        self._write(
            "docs/v2/09-test-observability-release-blueprint.md",
            "## 7. Performance budgets\n\n"
            "| Operation | Budget |\n| --- | --- |\n| Overview | p95 <= 1s |\n\n"
            "## 8. SLOs\n",
        )
        self._git("init")
        self._git("config", "user.name", "test")
        self._git("config", "user.email", "test@example.invalid")
        self._git("add", ".")
        self._git("commit", "-m", "fixture")

    def tearDown(self):
        self.tempdir.cleanup()

    def _write(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _git(self, *args):
        subprocess.run(
            ["git", *args], cwd=self.root, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )

    def test_inventory_is_deterministic_and_test_import_does_not_create_cycle(self):
        first = baseline.build_outputs(self.root, "HEAD")
        second = baseline.build_outputs(self.root, "HEAD")
        self.assertEqual(first, second)
        graph = first["dependency-graph.json"]
        self.assertEqual(graph["cycles"], [])
        self.assertEqual(
            [(edge["from"], edge["to"]) for edge in graph["test_cross_addon_imports"]],
            [("shopify_connector_core", "shopify_connector_product")],
        )
        compatibility = first["compatibility-baseline.json"]
        store = next(model for model in compatibility["models"] if model["name"] == "shopify.connector.store")
        self.assertEqual(store["table"], "shopify_connector_store")
        self.assertEqual([field["name"] for field in store["fields"]], ["name", "state"])
        self.assertEqual(store["constraints"][0]["name"], "_name_unique")

    def test_graphql_and_ui_surfaces_are_named(self):
        outputs = baseline.build_outputs(self.root, "HEAD")
        operations = outputs["shopify-operation-inventory.json"]
        self.assertEqual(operations["api_version_literal"], "2026-07")
        self.assertEqual(
            [(item["kind"], item["name"]) for item in operations["operations"]],
            [("mutation", "ProductCreate"), ("query", "StoreIdentity")],
        )
        self.assertIn("| Registered tours | 1 |", outputs["ui-task-baseline.md"])
        self.assertIn("`store_tour`", outputs["ui-task-baseline.md"])

    def test_check_fails_on_surface_drift_but_ignores_source_sha(self):
        output_dir = self.root / "docs/v2/evidence"
        frozen = baseline.build_outputs(self.root, "HEAD")
        baseline._write_outputs(output_dir, frozen)
        baseline._check_outputs(output_dir, baseline.build_outputs(self.root, "HEAD"))
        model_path = self.root / "addons/shopify_connector_core/models/store.py"
        model_path.write_text(
            model_path.read_text(encoding="utf-8").replace(
                "    name = fields.Char", "    code = fields.Char()\n    name = fields.Char"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(baseline.BaselineError, "compatibility drift"):
            baseline._check_outputs(output_dir, baseline.build_outputs(self.root, "HEAD"))

    def test_json_outputs_are_serializable(self):
        outputs = baseline.build_outputs(self.root, "HEAD")
        for name, value in outputs.items():
            if name.endswith(".json"):
                json.dumps(value, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
