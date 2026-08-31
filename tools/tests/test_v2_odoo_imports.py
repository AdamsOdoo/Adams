"""Dependency-free guards for Odoo addon import resolution."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


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


if __name__ == "__main__":
    unittest.main()
