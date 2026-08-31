"""Static integration guards for the P07 compatibility cutover.

The optional domain addons are not installed in the dependency-free tooling
lane.  These checks therefore prove the wiring shape without importing Odoo:
canonical addon imports, explicit call-site delegation, and the deliberate
location-sync boundary whose writes currently share the V1 read lease.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "addons/shopify_connector_core/models/shopify_connector_domain_read_gateway.py"


MIGRATED_CALLS = {
    "addons/shopify_connector_inventory/models/shopify_connector_inventory_p07_read_adapter.py": (
        "_read_shopify_inventory_pair",
    ),
    "addons/shopify_connector_inventory_webhook/models/shopify_connector_inventory_observation_p07_read_adapter.py": (
        "_read_inventory_level",
    ),
    "addons/shopify_connector_fulfillment/models/shopify_connector_fulfillment_p07_read_adapter.py": (
        "_read_fulfillment_orders",
        "_read_order_fulfillments",
        "_read_fulfillment",
        "_read_fulfillments_batch",
    ),
    "addons/shopify_connector_webhook/models/shopify_connector_webhook_p07_read_adapter.py": (
        "_read_actual_subscriptions",
    ),
}


def _methods(source: str) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(source)
    return {
        node.name: node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _call_attributes(node: ast.AST) -> set[str]:
    return {
        child.func.attr
        for child in ast.walk(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
    }


class P07ReadIntegrationTests(unittest.TestCase):
    def test_domain_gateways_use_one_canonical_core_namespace(self):
        for relative in (
            "addons/shopify_connector_inventory/integration/__init__.py",
            "addons/shopify_connector_inventory/integration/shopify/__init__.py",
            "addons/shopify_connector_fulfillment/integration/__init__.py",
            "addons/shopify_connector_fulfillment/integration/shopify/__init__.py",
            "addons/shopify_connector_webhook/integration/__init__.py",
            "addons/shopify_connector_webhook/integration/shopify/__init__.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)
        for relative in (
            "addons/shopify_connector_inventory/integration/shopify/inventory_read_gateway.py",
            "addons/shopify_connector_fulfillment/integration/shopify/fulfillment_read_gateway.py",
            "addons/shopify_connector_webhook/integration/shopify/webhook_subscription_read_gateway.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            # Odoo-loaded adapters use the canonical addon namespace.  Pure
            # V2 gateways may use the package namespace so the dependency
            # policy can inspect them without importing the Odoo framework.
            self.assertTrue(
                "from odoo.addons.shopify_connector_core.domain.immutability"
                in source
                or "from shopify_connector_core.domain.immutability" in source
            )

    def test_every_migrated_read_method_has_explicit_reversible_delegate(self):
        for relative, names in MIGRATED_CALLS.items():
            source = (ROOT / relative).read_text(encoding="utf-8")
            methods = _methods(source)
            for name in names:
                with self.subTest(file=relative, method=name):
                    self.assertIn(name, methods)
                    body = ast.get_source_segment(source, methods[name]) or ""
                    self.assertIn("shopify.connector.read.gateway", body)
                    self.assertIn("P07_LEGACY_CONTEXT_KEY", body)

    def test_adapter_is_query_only_and_owns_no_persistent_or_remote_policy(self):
        source = ADAPTER.read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = _call_attributes(tree)
        self.assertFalse(calls & {"create", "write", "unlink", "sudo"})
        self.assertIn("execute_business_read", calls)
        self.assertIn("execute_business", calls)
        self.assertIn("_admit_lifecycle", calls)
        self.assertIn("_send_lifecycle", calls)
        self.assertIn("_assert_store", calls)
        self.assertIn("_store_mode", calls)
        for operation in (
            "InventoryPairRead",
            "InventoryObservation",
            "ConnectorFulfillmentOrdersForOrder",
            "ConnectorOrderFulfillments",
            "ConnectorFulfillmentNode",
            "ConnectorFulfillmentNodes",
            "ConnectorWebhookSubscriptions",
        ):
            self.assertIn(operation, source)

    def test_location_cache_sync_remains_explicitly_legacy(self):
        # This V1 method writes location cache rows while the page's
        # execute_business_read context is open.  The P07 adapter intentionally
        # has no fake replacement that would change that lease lifetime.
        source = (
            ROOT
            / "addons/shopify_connector_inventory/models/shopify_connector_inventory_service.py"
        ).read_text(encoding="utf-8")
        method = _methods(source)["_handle_inventory_location_sync"]
        body = ast.get_source_segment(source, method) or ""
        self.assertIn("execute_business_read", body)
        self.assertIn("Location.sudo().create", body)
        self.assertNotIn("read_inventory_locations", ADAPTER.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
