"""Dependency-free characterization for the P06 product scan call site.

The Odoo registry is unavailable in this lane, so production wiring is checked
with AST assertions while the normalized page adapter is exercised with the
same deterministic fixture shape used by the pure P06 gateway tests.
"""

from __future__ import annotations

import ast
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = ROOT / "addons" / "shopify_connector_core"
PRODUCT_ROOT = ROOT / "addons" / "shopify_connector_product"


def _namespace(name: str, path: Path) -> None:
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    package.__package__ = name
    sys.modules[name] = package


# Import the pure product boundary without loading Odoo's module initializer.
_namespace("odoo", ROOT)
_namespace("odoo.addons", ROOT / "addons")
_namespace("odoo.addons.shopify_connector_core", CORE_ROOT)
_namespace("odoo.addons.shopify_connector_core.domain", CORE_ROOT / "domain")
_namespace("odoo.addons.shopify_connector_core.integration", CORE_ROOT / "integration")
_namespace(
    "odoo.addons.shopify_connector_core.integration.shopify",
    CORE_ROOT / "integration" / "shopify",
)
_namespace("shopify_connector_product", PRODUCT_ROOT)
_namespace("shopify_connector_product.integration", PRODUCT_ROOT / "integration")
_namespace(
    "shopify_connector_product.integration.shopify",
    PRODUCT_ROOT / "integration" / "shopify",
)

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import (  # noqa: E402
    ReadCompatibilityAdapter,
    ReadGatewayError,
    ReadGatewayMode,
)
from shopify_connector_product.integration.shopify.read_gateway import (  # noqa: E402
    PRODUCT_SCAN_OPERATION,
    ProductReadGateway,
    scan_page_from_gateway_result,
)


SCAN_SOURCE = PRODUCT_ROOT / "models" / "shopify_connector_product_scan.py"
SCAN_P06_SOURCE = (
    PRODUCT_ROOT / "models" / "shopify_connector_product_scan_p06.py"
)


class _Source:
    def __init__(self, response):
        self.response = response

    def response_for(self, _variables):
        return self.response


class _Legacy:
    def __init__(self, source):
        self.source = source
        self.calls = []

    def execute(self, store, document, variables):
        self.calls.append((store, document, dict(variables)))
        return self.source.response_for(variables)


class _Typed:
    def __init__(self, source):
        self.source = source
        self.calls = []

    def execute_read(self, store, operation, variables):
        self.calls.append((store, operation, dict(variables)))
        return self.source.response_for(variables)


def _envelope(data):
    return {
        "data": data,
        "served_version": "2026-07",
        "cost": {"requestedQueryCost": 7, "actualQueryCost": 5},
    }


def _scan_response(*, has_next=False, end_cursor=None):
    return _envelope({
        "products": {
            "edges": [{
                "cursor": "edge-1",
                "node": {
                    "id": "gid://shopify/Product/1",
                    "updatedAt": "2026-08-30T12:00:00Z",
                    "status": "ACTIVE",
                },
            }],
            "pageInfo": {"hasNextPage": has_next, "endCursor": end_cursor},
        },
    })


def _adapter(response):
    source = _Source(response)
    legacy = _Legacy(source)
    typed = _Typed(source)
    document = "query ConnectorProductScan($first: Int!, $after: String, $query: String!) { products(first: $first, after: $after, query: $query) { edges { cursor node { id updatedAt status } } pageInfo { hasNextPage endCursor } } }"
    adapter = ReadCompatibilityAdapter(
        legacy,
        {"ConnectorProductScan": document},
        typed_delegate=typed,
    )
    return adapter, legacy, typed


class TestProductReadCallSite(unittest.TestCase):
    def test_scan_call_site_has_explicit_legacy_and_gateway_routes(self):
        source = SCAN_P06_SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(source)
        methods = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertIn("_read_product_scan_page", methods)
        body = ast.get_source_segment(source, methods["_read_product_scan_page"])
        self.assertIn("shopify.connector.read.gateway", body)
        self.assertIn("read_product_page", body)
        self.assertIn("super()._read_product_scan_page", body)
        legacy_source = SCAN_SOURCE.read_text(encoding="utf-8")
        legacy_tree = ast.parse(legacy_source)
        legacy_method = next(
            node for node in ast.walk(legacy_tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "_read_product_scan_page"
        )
        legacy_body = ast.get_source_segment(legacy_source, legacy_method)
        self.assertIn("execute_business", legacy_body)
        self.assertIn("PRODUCT_SCAN_QUERY", legacy_body)
        self.assertNotIn("create(", legacy_body)
        self.assertNotIn("write(", legacy_body)

    def test_normalized_scan_page_preserves_cursor_and_identity_contract(self):
        adapter, legacy, typed = _adapter(
            _scan_response(has_next=True, end_cursor="cursor-1")
        )
        legacy_result = ProductReadGateway(adapter).read_product_page(
            "store", query="updated_at:<=2026-08-30T12:00:00Z"
        )
        typed_result = ProductReadGateway(
            adapter.for_mode(ReadGatewayMode.TYPED)
        ).read_product_page("store", query="updated_at:<=2026-08-30T12:00:00Z")
        self.assertEqual(legacy_result.as_dict(), typed_result.as_dict())
        normalized = scan_page_from_gateway_result(typed_result.as_dict())
        self.assertEqual(normalized["nodes"][0]["id"], "gid://shopify/Product/1")
        self.assertEqual(normalized["end_cursor"], "cursor-1")
        self.assertTrue(normalized["has_next"])
        self.assertEqual(len(legacy.calls), 1)
        self.assertEqual(len(typed.calls), 1)

    def test_normalized_scan_page_rejects_terminal_cursor_and_bad_operation(self):
        adapter, _legacy, _typed = _adapter(_scan_response())
        result = ProductReadGateway(adapter).read_product_page("store")
        payload = result.as_dict()
        payload["value"]["next_cursor"] = "cursor-on-terminal"
        with self.assertRaises(ReadGatewayError):
            scan_page_from_gateway_result(payload)
        payload = result.as_dict()
        payload["operation_name"] = "ConnectorProductImport"
        with self.assertRaises(ReadGatewayError):
            scan_page_from_gateway_result(payload)

    def test_scan_operation_remains_explicitly_bounded(self):
        self.assertEqual(PRODUCT_SCAN_OPERATION.page_size, 100)
        self.assertEqual(PRODUCT_SCAN_OPERATION.max_pages, 10)
        self.assertEqual(PRODUCT_SCAN_OPERATION.max_items, 1000)


if __name__ == "__main__":
    unittest.main()
