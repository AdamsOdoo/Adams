"""Dependency-free guards for Odoo addon import resolution."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "addons"
ADDON_NAMES = {
    path.name
    for path in ADDONS.iterdir()
    if path.is_dir() and path.name.startswith("shopify_connector_")
}


def _bare_cross_addon_imports(path: Path) -> list[tuple[int, str]]:
    """Return cross-addon imports that bypass Odoo's addon namespace."""

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    addon = path.relative_to(ADDONS).parts[0]
    violations: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported_addon = module.split(".", 1)[0]
            if imported_addon in ADDON_NAMES and imported_addon != addon:
                violations.append((node.lineno, module))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imported_addon = alias.name.split(".", 1)[0]
                if imported_addon in ADDON_NAMES and imported_addon != addon:
                    violations.append((node.lineno, alias.name))
    return violations


class OdooAddonImportTests(unittest.TestCase):
    def test_production_imports_use_odoo_addon_namespace(self):
        violations: list[str] = []
        for path in sorted(ADDONS.rglob("*.py")):
            if "tests" in path.parts:
                continue
            for line, module in _bare_cross_addon_imports(path):
                violations.append(f"{path.relative_to(ROOT)}:{line}: {module}")
        self.assertEqual(violations, [], "bare cross-addon imports found:\n" + "\n".join(violations))


class OdooRuntimeCompatibilityTests(unittest.TestCase):
    """Dependency-free guards for pinned Odoo 19 registry/view contracts."""

    def test_run_search_group_uses_pinned_odoo_19_attributes(self):
        path = ADDONS / "shopify_connector_core/views/shopify_connector_runtime_views.xml"
        root = ElementTree.parse(path).getroot()
        search_groups = root.findall(".//search/group")
        self.assertEqual(len(search_groups), 1)
        # Pinned Odoo 19 common.rng rejects these legacy attributes.
        self.assertNotIn("expand", search_groups[0].attrib)
        self.assertNotIn("string", search_groups[0].attrib)

    def test_sec3_init_sweep_skips_models_whose_table_is_not_installed(self):
        path = ADDONS / "shopify_connector_core/models/shopify_connector_scope_mixin.py"
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_sec3_quarantine_scope_mismatches"
        )
        segment = ast.get_source_segment(source, method) or ""
        guard = segment.index("if not table_exists(self.env.cr, self._table)")
        search = segment.index("self.sudo().search")
        self.assertLess(guard, search)


if __name__ == "__main__":
    unittest.main()
