import contextlib
import io
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
            "STATE_SELECTION = [('draft', 'Draft'), ('active', 'Active')]\n"
            "STATE_SELECTION_ADD = [('archived', 'Archived')]\n"
            "DYNAMIC_SELECTION = build_selection()\n"
            "DYNAMIC_SELECTION_ADD = get_additions()\n"
            "PRODUCTION_DDL = 'CREATE INDEX production_store_idx ON shopify_connector_store (name)'\n"
            "QUERY = '''query StoreIdentity($id: ID!) { shop { id } }'''\n"
            "ANONYMOUS = '''query { shop { id } }'''\n"
            "class Store(models.Model):\n"
            "    _name = 'shopify.connector.store'\n"
            "    name = fields.Char(required=True, index=True)\n"
            "    state = fields.Selection(STATE_SELECTION, selection_add=STATE_SELECTION_ADD, store=True)\n"
            "    _name_unique = models.Constraint('UNIQUE(name)', 'unique')\n"
            "    _name_idx = models.UniqueIndex('name')\n"
            "    @api.constrains('name')\n"
            "    def _check_name(self):\n"
            "        pass\n"
            "    def action_open(self):\n"
            "        return True\n",
        )
        self._write(
            "addons/shopify_connector_core/models/store_extension.py",
            "from odoo import fields, models\n"
            "class StoreExtension(models.Model):\n"
            "    _inherit = 'shopify.connector.store'\n"
            "    extension_field = fields.Char()\n"
            "    dynamic_state = fields.Selection(selection=DYNAMIC_SELECTION, selection_add=DYNAMIC_SELECTION_ADD)\n"
            "class StoreService(models.AbstractModel):\n"
            "    _name = 'shopify.connector.store.service'\n"
            "class StoreWizard(models.TransientModel):\n"
            "    _name = 'shopify.connector.store.wizard'\n",
        )
        self._write(
            "addons/shopify_connector_core/migrations/1.0/post-migrate.py",
            "DDL = 'CREATE UNIQUE INDEX IF NOT EXISTS migration_unique_idx ON shopify_connector_store (name)'\n"
            "class HistoricalModel:\n"
            "    _name = 'not.a.runtime.model'\n",
        )
        self._write(
            "addons/shopify_connector_core/migrations/1.0/extra.sql",
            "CREATE INDEX migration_sql_idx ON shopify_connector_store (name);\n",
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
        self.assertEqual(compatibility["schema_version"], baseline.SCHEMA_VERSION)
        store = next(model for model in compatibility["models"] if model["name"] == "shopify.connector.store")
        self.assertEqual(store["table"], "shopify_connector_store")
        self.assertEqual(store["model_kind"], "model")
        self.assertEqual([field["name"] for field in store["fields"]], ["name", "state"])
        self.assertEqual(
            [constraint["name"] for constraint in store["constraints"]],
            ["_name_idx", "_name_unique"],
        )
        self.assertEqual(
            next(
                constraint for constraint in store["constraints"]
                if constraint["name"] == "_name_idx"
            )["kind"],
            "uniqueindex",
        )
        extension = next(model for model in compatibility["models"] if model["class"] == "StoreExtension")
        self.assertEqual(extension["model_kind"], "model")
        self.assertIsNone(extension["name"])
        self.assertIsNone(extension["table"])
        abstract = next(model for model in compatibility["models"] if model["class"] == "StoreService")
        self.assertEqual(abstract["model_kind"], "abstract")
        self.assertIsNone(abstract["table"])
        transient = next(model for model in compatibility["models"] if model["class"] == "StoreWizard")
        self.assertEqual(transient["model_kind"], "transient")
        self.assertEqual(transient["table"], "shopify_connector_store_wizard")

    def test_selection_constants_additions_and_unresolved_expressions_are_preserved(self):
        outputs = baseline.build_outputs(self.root, "HEAD")
        models = outputs["compatibility-baseline.json"]["models"]
        store = next(model for model in models if model["name"] == "shopify.connector.store")
        state = next(field for field in store["fields"] if field["name"] == "state")
        self.assertEqual(state["selection_values"], ["draft", "active"])
        self.assertEqual(state["selection_expression"], None)
        self.assertEqual(state["selection_add_values"], ["archived"])
        self.assertEqual(state["selection_add_expression"], None)
        extension = next(model for model in models if model["class"] == "StoreExtension")
        dynamic = next(field for field in extension["fields"] if field["name"] == "dynamic_state")
        self.assertIsNone(dynamic["selection_values"])
        self.assertEqual(dynamic["selection_expression"], "DYNAMIC_SELECTION")
        self.assertIsNone(dynamic["selection_add_values"])
        self.assertEqual(dynamic["selection_add_expression"], "DYNAMIC_SELECTION_ADD")

    def test_raw_indexes_include_migrations_but_migration_classes_are_not_models(self):
        outputs = baseline.build_outputs(self.root, "HEAD")
        compatibility = outputs["compatibility-baseline.json"]
        indexes = compatibility["raw_sql_indexes"]
        self.assertCountEqual(
            [item["name"] for item in indexes],
            ["migration_unique_idx", "migration_sql_idx", "production_store_idx"],
        )
        self.assertEqual(
            next(item for item in indexes if item["name"] == "migration_unique_idx")["unique"],
            True,
        )
        self.assertFalse(any(model["class"] == "HistoricalModel" for model in compatibility["models"]))

    def test_graphql_and_ui_surfaces_are_named(self):
        outputs = baseline.build_outputs(self.root, "HEAD")
        operations = outputs["shopify-operation-inventory.json"]
        self.assertEqual(operations["schema_version"], baseline.SCHEMA_VERSION)
        self.assertEqual(operations["api_version_literal"], "2026-07")
        self.assertCountEqual(
            [(item["kind"], item["name"]) for item in operations["operations"]],
            [("query", None), ("mutation", "ProductCreate"), ("query", "StoreIdentity")],
        )
        self.assertEqual(operations["operation_count"], 3)
        self.assertEqual(operations["anonymous_operation_count"], 1)
        self.assertIn("| Registered tours | 1 |", outputs["ui-task-baseline.md"])
        self.assertIn("`store_tour`", outputs["ui-task-baseline.md"])

    def test_build_fails_on_tracked_connector_surface_drift(self):
        output_dir = self.root / "docs/v2/evidence"
        model_path = self.root / "addons/shopify_connector_core/models/store.py"
        model_path.write_text(
            model_path.read_text(encoding="utf-8").replace(
                "    name = fields.Char", "    code = fields.Char()\n    name = fields.Char"
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(baseline.BaselineError, "connector addon working-tree mismatch"):
            baseline.build_outputs(self.root, "HEAD")

    def test_build_fails_on_deleted_and_untracked_connector_files(self):
        deleted_path = self.root / "addons/shopify_connector_core/models/store.py"
        deleted_path.unlink()
        with self.assertRaisesRegex(baseline.BaselineError, "store.py"):
            baseline.build_outputs(self.root, "HEAD")

        # A fresh fixture is not needed: the deletion already proves the
        # tracked path check; this untracked path check is independently
        # observable in the same fail-closed error.
        self._write(
            "addons/shopify_connector_core/models/new_untracked.py",
            "# relevant connector source\n",
        )
        with self.assertRaisesRegex(baseline.BaselineError, "new_untracked.py"):
            baseline.build_outputs(self.root, "HEAD")

    def test_check_requires_matching_frozen_source_sha(self):
        frozen = baseline.build_outputs(self.root, "HEAD")
        output_dir = self.root / "docs/v2/evidence"
        baseline._write_outputs(output_dir, frozen)
        for name in baseline.OUTPUT_NAMES:
            path = output_dir / name
            if name.endswith(".json"):
                payload = json.loads(path.read_text(encoding="utf-8"))
                payload["source_ref"] = "published-code-ref"
                path.write_text(json.dumps(payload), encoding="utf-8")
            else:
                path.write_text(
                    path.read_text(encoding="utf-8").replace(
                        f"- Source ref: `{frozen[name].split('`')[1]}`",
                        "- Source ref: `published-code-ref`",
                    ),
                    encoding="utf-8",
                )
        baseline._check_outputs(output_dir, frozen)
        path = output_dir / "compatibility-baseline.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["source_sha"] = "0" * 64
        path.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(baseline.BaselineError, "source SHA mismatch"):
            baseline._check_outputs(output_dir, frozen)

    def test_check_uses_frozen_source_sha_after_docs_commit_but_rejects_addon_change(self):
        code_sha = baseline._git(self.root, "rev-parse", "HEAD")
        frozen = baseline.build_outputs(self.root, code_sha)
        output_dir = self.root / "docs/v2/evidence"
        baseline._write_outputs(output_dir, frozen)

        self._write("docs/publication-note.md", "docs-only publication\n")
        self._git("add", "docs/publication-note.md")
        self._git("commit", "-m", "docs publication")
        self.assertEqual(
            baseline.main(
                ["--repo-root", str(self.root), "--output-dir", str(output_dir), "--check"]
            ),
            0,
        )

        model_path = self.root / "addons/shopify_connector_core/models/store.py"
        model_path.write_text(
            model_path.read_text(encoding="utf-8") + "\n# addon change after code commit\n",
            encoding="utf-8",
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                baseline.main(
                    ["--repo-root", str(self.root), "--output-dir", str(output_dir), "--check"]
                ),
                1,
            )

    def test_json_outputs_are_serializable(self):
        outputs = baseline.build_outputs(self.root, "HEAD")
        for name, value in outputs.items():
            if name.endswith(".json"):
                json.dumps(value, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
