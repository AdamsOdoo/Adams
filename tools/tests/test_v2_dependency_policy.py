"""Dependency-free tests for the V2 package boundary checker."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.v2_dependency_policy import check_package


class TestV2DependencyPolicy(unittest.TestCase):
    def _tree(self, files: dict[str, str]) -> Path:
        directory = Path(tempfile.mkdtemp(prefix="v2-dependency-policy-"))
        for name, source in files.items():
            path = directory / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        return directory

    def test_valid_layer_direction_and_integration_network_are_allowed(self):
        root = self._tree({
            "domain/policy.py": "VALUE = 1\n",
            "tools/api_version.py": "VERSION = '2026-07'\n",
            "integration/shopify/transport.py": "import requests\n",
            "integration/shopify/gateway.py": "from ...tools.api_version import VERSION\n",
            "runtime/coordinator.py": "from ..domain import policy\nfrom ..integration.shopify import transport\n",
            "application/commands.py": "from ..domain import policy\nfrom ..runtime import coordinator\n",
        })
        self.assertEqual(check_package(root), [])

    def test_reverse_import_and_network_outside_integration_fail_closed(self):
        root = self._tree({
            "domain/policy.py": "from ..application import commands\n",
            "application/commands.py": "import requests\nrequests.get('https://example.invalid')\nfrom requests import get\nget('https://example.invalid')\n",
            "integration/shopify/transport.py": "from ..domain import policy\n",
        })
        violations = check_package(root)
        rules = {item.rule for item in violations}
        self.assertIn("reverse-import", rules)
        self.assertIn("direct-network", rules)
        self.assertTrue(all(item.path for item in violations))

    def test_relative_reverse_import_and_urllib_request_are_detected(self):
        root = self._tree({
            "domain/bad.py": "from ..runtime import coordinator\n",
            "domain/bad_network.py": "from urllib.request import urlopen\n",
        })
        violations = check_package(root)
        self.assertEqual(
            {(item.path, item.rule) for item in violations},
            {
                ("domain/bad_network.py", "direct-network"),
                ("domain/bad.py", "reverse-import"),
            },
        )

    def test_framework_and_nonlayer_internal_imports_are_rejected(self):
        root = self._tree({
            "domain/framework.py": "from odoo import models\n",
            "domain/legacy.py": "from ..models import shopify_connector_store\n",
            "application/support.py": "from ..tools import redaction\n",
        })
        violations = check_package(root)
        self.assertIn("framework-import", {item.rule for item in violations})
        self.assertGreaterEqual(
            sum(item.rule == "forbidden-internal-import" for item in violations),
            2,
        )

    def test_application_cannot_import_any_integration_contract_directly(self):
        root = self._tree({
            "application/commands.py": (
                "from another_addon.integration.shopify.contracts import Request\n"
                "from ..integration.shopify import gateway\n"
            ),
        })
        violations = check_package(root)
        self.assertEqual(
            sum(item.rule == "application-integration-import" for item in violations),
            2,
        )

    def test_canonical_core_pure_contract_import_is_allowed(self):
        root = self._tree({
            "integration/shopify/gateway.py": (
                "from odoo.addons.shopify_connector_core.domain.immutability "
                "import to_plain\n"
                "from odoo import models\n"
            ),
        })
        violations = check_package(root)
        self.assertEqual(
            [(item.rule, item.import_name) for item in violations],
            [("framework-import", "odoo")],
        )

    def test_same_layer_cycles_are_reported(self):
        root = self._tree({
            "domain/first.py": "from .second import VALUE\nVALUE = 1\n",
            "domain/second.py": "from .first import VALUE\nVALUE = 2\n",
        })
        violations = check_package(root)
        cycles = [item for item in violations if item.rule == "same-layer-cycle"]
        self.assertEqual(len(cycles), 2)
        self.assertTrue(all("first" in item.message and "second" in item.message for item in cycles))

    def test_cycle_scan_is_bounded(self):
        root = self._tree({
            **{
                "domain/module_%03d.py" % index: "VALUE = %d\n" % index
                for index in range(513)
            },
        })
        violations = check_package(root)
        self.assertIn("cycle-analysis-limit", {item.rule for item in violations})


if __name__ == "__main__":
    unittest.main()
