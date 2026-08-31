"""Framework-free checks for the bounded P06 sale read integration.

The Odoo registry is not available in this lane. These checks therefore lock
the production call-site seam and its compatibility shape without importing a
model or exercising a Shopify request. Pure DTO/gateway parity remains in
``test_v2_read_gateways.py``.
"""

from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCAN = ROOT / "addons/shopify_connector_sale/models/shopify_connector_order_scan.py"
SCAN_P06 = (
    ROOT
    / "addons/shopify_connector_sale/models/shopify_connector_order_scan_p06.py"
)


def _method(source: str, name: str) -> ast.FunctionDef:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError("missing method %s" % name)


class P06SaleReadIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = SCAN.read_text(encoding="utf-8")
        cls.tree = ast.parse(cls.source, filename=str(SCAN))
        cls.p06_source = SCAN_P06.read_text(encoding="utf-8")

    def test_order_scan_has_explicit_legacy_rollback_and_typed_route(self):
        body = ast.get_source_segment(
            self.p06_source,
            _method(self.p06_source, "_read_order_scan_page"),
        ) or ""
        self.assertIn("_store_mode", body)
        self.assertIn("== 'legacy'", body)
        self.assertIn("super()._read_order_scan_page", body)
        self.assertIn("read_order_scan_page", body)
        self.assertIn("_page_from_p06_gateway", body)
        legacy = ast.get_source_segment(
            self.source, _method(self.source, "_read_order_scan_page"),
        ) or ""
        self.assertIn("execute_business", legacy)

    def test_typed_page_adapter_preserves_scan_classification_fields(self):
        body = ast.get_source_segment(
            self.p06_source,
            _method(self.p06_source, "_page_from_p06_gateway"),
        ) or ""
        for key in (
            "gid", "updated_at", "created_at", "edited", "test",
            "cancelled_at", "display_financial_status",
        ):
            self.assertIn("item.get('%s')" % key, body)
        self.assertIn("'updatedAt'", body)
        self.assertIn("'createdAt'", body)
        self.assertIn("'displayFinancialStatus'", body)
        self.assertIn("'next_cursor'", body)
        self.assertIn("typed-edge:", body)
        self.assertIn("operation_name", body)
        self.assertIn("operation_mismatch", body)

    def test_scan_read_seam_is_query_only_and_payload_free(self):
        p06_names = {
            node.func.attr
            for node in ast.walk(
                _method(self.p06_source, "_read_order_scan_page")
            )
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertIn("read_order_scan_page", p06_names)
        self.assertNotIn("execute", p06_names)
        # The newly routed branch can classify and enqueue existing jobs, but
        # it must not introduce an Odoo/Shopify mutation operation of its own.
        self.assertNotIn("create", p06_names)
        self.assertNotIn("write", p06_names)
        self.assertNotIn("unlink", p06_names)
        self.assertNotIn("sudo", p06_names)


if __name__ == "__main__":
    unittest.main()
