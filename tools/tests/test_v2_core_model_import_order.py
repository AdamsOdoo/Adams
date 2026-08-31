"""Source guards for Odoo model-owner registration order."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODELS_INIT = ROOT / "addons/shopify_connector_core/models/__init__.py"


def _relative_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: list[str] = []
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level != 1:
            continue
        names.extend(alias.name for alias in node.names)
    return names


class CoreModelImportOrderTests(unittest.TestCase):
    def test_application_facade_owner_precedes_every_known_extension(self):
        imports = _relative_imports(MODELS_INIT)
        owner_index = imports.index("shopify_connector_application_facade")
        extensions = (
            "shopify_connector_p15_command_replay",
            "shopify_connector_recovery_commands",
            "shopify_connector_recovery_job",
            "shopify_connector_recovery_cancellation",
            "shopify_connector_recovery_replay",
            "shopify_connector_p15_operations",
            "shopify_connector_p15_setup_commands",
            "shopify_connector_p15_admin",
        )
        for extension in extensions:
            with self.subTest(extension=extension):
                self.assertGreater(imports.index(extension), owner_index)

    def test_scope_owner_precedes_transitive_api_client_models(self):
        imports = _relative_imports(MODELS_INIT)
        self.assertLess(
            imports.index("shopify_connector_scope_mixin"),
            imports.index("shopify_connector_api_client"),
        )


if __name__ == "__main__":
    unittest.main()
