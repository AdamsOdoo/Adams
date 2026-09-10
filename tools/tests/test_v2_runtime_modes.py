"""Dependency-free contract for cumulative V2 rollout modes."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"
for name, path in (
    ("shopify_connector_core", CORE),
    ("shopify_connector_core.domain", CORE / "domain"),
):
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    package.__package__ = name
    sys.modules[name] = package

from shopify_connector_core.domain.runtime_modes import (  # noqa: E402
    V2_RUNTIME_CAPABILITIES,
    V2_RUNTIME_MODE_ORDER,
    runtime_mode_includes,
    runtime_modes_including,
)


class RuntimeModeLatticeTests(unittest.TestCase):
    def test_every_rung_is_cumulative_and_all_contains_every_capability(self):
        for capability in V2_RUNTIME_CAPABILITIES:
            allowed = runtime_modes_including(capability)
            self.assertEqual(
                allowed,
                V2_RUNTIME_MODE_ORDER[
                    V2_RUNTIME_MODE_ORDER.index(capability):
                ],
            )
            self.assertTrue(runtime_mode_includes("all", capability))
            self.assertFalse(runtime_mode_includes("legacy", capability))

    def test_complete_expected_matrix(self):
        expected = {
            "legacy": (),
            "read_only": ("read_only",),
            "subscriptions": ("read_only", "subscriptions"),
            "inventory": ("read_only", "subscriptions", "inventory"),
            "product_export": (
                "read_only", "subscriptions", "inventory", "product_export",
            ),
            "fulfillment": V2_RUNTIME_CAPABILITIES,
            "all": V2_RUNTIME_CAPABILITIES,
        }
        for mode, capabilities in expected.items():
            with self.subTest(mode=mode):
                self.assertEqual(
                    tuple(
                        capability for capability in V2_RUNTIME_CAPABILITIES
                        if runtime_mode_includes(mode, capability)
                    ),
                    capabilities,
                )

    def test_unknown_modes_and_non_capability_rungs_fail_closed(self):
        for current, capability in (
            ("future", "read_only"),
            ("legacy", "legacy"),
            ("all", "all"),
        ):
            with self.subTest(current=current, capability=capability):
                with self.assertRaises(ValueError):
                    runtime_mode_includes(current, capability)


if __name__ == "__main__":
    unittest.main()
