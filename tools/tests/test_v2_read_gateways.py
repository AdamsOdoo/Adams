"""Dependency-free P06 gateway contracts, parity, and bound tests."""

from __future__ import annotations

import json
import re
import sys
import types
import unittest
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = ROOT / "addons" / "shopify_connector_core"
PRODUCT_ROOT = ROOT / "addons" / "shopify_connector_product"
SALE_ROOT = ROOT / "addons" / "shopify_connector_sale"


def _namespace(name: str, path: Path) -> None:
    package = types.ModuleType(name)
    package.__path__ = [str(path)]
    package.__package__ = name
    sys.modules[name] = package


# Odoo addon initializers import the ORM.  P06 contracts are intentionally
# pure, so the test lane exposes only their package paths as namespaces.
_namespace("odoo", ROOT)
_namespace("odoo.addons", ROOT / "addons")
_namespace("odoo.addons.shopify_connector_core", CORE_ROOT)
_namespace("odoo.addons.shopify_connector_core.domain", CORE_ROOT / "domain")
_namespace("odoo.addons.shopify_connector_core.integration", CORE_ROOT / "integration")
_namespace(
    "odoo.addons.shopify_connector_core.integration.shopify",
    CORE_ROOT / "integration" / "shopify",
)
_namespace("shopify_connector_core", CORE_ROOT)
_namespace("shopify_connector_core.domain", CORE_ROOT / "domain")
_namespace("shopify_connector_core.integration", CORE_ROOT / "integration")
_namespace("shopify_connector_core.integration.shopify", CORE_ROOT / "integration" / "shopify")
_namespace("shopify_connector_product", PRODUCT_ROOT)
_namespace("shopify_connector_product.integration", PRODUCT_ROOT / "integration")
_namespace("shopify_connector_product.integration.shopify", PRODUCT_ROOT / "integration" / "shopify")
_namespace("shopify_connector_sale", SALE_ROOT)
_namespace("shopify_connector_sale.integration", SALE_ROOT / "integration")
_namespace("shopify_connector_sale.integration.shopify", SALE_ROOT / "integration" / "shopify")

from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import (  # noqa: E402
    CursorProgress,
    MoneyDTO,
    ReadCompatibilityAdapter,
    ReadGatewayError,
    ReadGatewayMode,
    ReadOperation,
    response_data,
)
from odoo.addons.shopify_connector_core.integration.shopify.read_comparison import (  # noqa: E402
    REPLAY_SAFE_READ_OPERATIONS,
    ReadComparisonEvidence,
    compare_values,
    should_compare,
)
from odoo.addons.shopify_connector_core.integration.shopify.read_gateway import (  # noqa: E402
    LocationReadGateway,
    StoreCapabilityReadGateway,
)
from shopify_connector_product.integration.shopify.read_gateway import (  # noqa: E402
    ProductReadGateway,
    PRODUCT_READ_OPERATION,
    PRODUCT_SCAN_OPERATION,
)
import shopify_connector_product.integration.shopify.read_gateway as product_read_module  # noqa: E402
from shopify_connector_sale.integration.shopify.read_gateway import (  # noqa: E402
    CUSTOMER_READ_OPERATION,
    ORDER_HEADER_OPERATION,
    ORDER_SCAN_OPERATION,
    CustomerReadGateway,
    OrderReadGateway,
)
import shopify_connector_sale.integration.shopify.read_dto as sale_dto_module  # noqa: E402


OPERATION_SOURCES = {
    "ConnectorTestConnection": "addons/shopify_connector_core/models/shopify_connector_store.py",
    "ConnectorFulfillmentLocations": "addons/shopify_connector_fulfillment/integration/shopify/fulfillment_read_gateway.py",
    "ConnectorProductScan": "addons/shopify_connector_product/models/shopify_connector_product_scan.py",
    "ConnectorProductImport": "addons/shopify_connector_product/models/shopify_connector_product_importer.py",
    "ConnectorCustomerImport": "addons/shopify_connector_sale/models/shopify_connector_customer_importer.py",
    "ConnectorOrderScan": "addons/shopify_connector_sale/models/shopify_connector_order_scan.py",
    "ConnectorOrderHeader": "addons/shopify_connector_sale/models/shopify_connector_order_importer.py",
    "ConnectorOrderLineItemsPage": "addons/shopify_connector_sale/models/shopify_connector_order_importer.py",
    "ConnectorOrderShippingLinesPage": "addons/shopify_connector_sale/models/shopify_connector_order_importer.py",
    "ConnectorOrderDiscountApplicationsPage": "addons/shopify_connector_sale/models/shopify_connector_order_importer.py",
}


def _query_document(source: str, operation_name: str) -> str:
    """Extract the checked-in query body without importing an Odoo model."""

    text = (ROOT / source).read_text(encoding="utf-8")
    match = re.search(r"\bquery\s+" + re.escape(operation_name) + r"\b", text)
    if match is None:
        raise AssertionError(f"missing checked-in operation {operation_name}")
    opening = text.find("{", match.end())
    if opening < 0:
        raise AssertionError(f"operation {operation_name} has no selection set")
    depth = 0
    in_string = False
    escaped = False
    for index in range(opening, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : index + 1]
    raise AssertionError(f"operation {operation_name} has an unbalanced selection set")


OPERATION_DOCUMENTS = {
    name: _query_document(source, name) for name, source in OPERATION_SOURCES.items()
}


class _FixtureSource:
    def __init__(self) -> None:
        self.responses: dict[str, object] = {}

    def set(self, operation_name: str, response: object) -> None:
        self.responses[operation_name] = response

    def response(self, operation_name: str, variables: dict[str, object]) -> object:
        value = self.responses.get(operation_name)
        if callable(value):
            return value(variables)
        return value


class _LegacyDelegate:
    def __init__(self, source: _FixtureSource) -> None:
        self.source = source
        self.calls: list[tuple[object, str, dict[str, object]]] = []

    def execute(self, store: object, document: str, variables: dict[str, object]) -> object:
        name = re.search(r"\bquery\s+([_A-Za-z][_A-Za-z0-9]*)\b", document).group(1)
        self.calls.append((store, document, dict(variables)))
        return self.source.response(name, variables)


class _TypedDelegate:
    def __init__(self, source: _FixtureSource) -> None:
        self.source = source
        self.calls: list[tuple[object, ReadOperation, dict[str, object]]] = []

    def execute_read(self, store: object, operation: ReadOperation, variables: dict[str, object]) -> object:
        self.calls.append((store, operation, dict(variables)))
        return self.source.response(operation.operation_name, variables)


def _adapter(source: _FixtureSource) -> tuple[ReadCompatibilityAdapter, _LegacyDelegate, _TypedDelegate]:
    legacy = _LegacyDelegate(source)
    typed = _TypedDelegate(source)
    return ReadCompatibilityAdapter(legacy, OPERATION_DOCUMENTS, typed_delegate=typed), legacy, typed


def _envelope(data: dict[str, object]) -> dict[str, object]:
    return {
        "data": data,
        "served_version": "2026-07",
        "cost": {
            "requestedQueryCost": 7,
            "actualQueryCost": 5,
            "throttleStatus": {
                "maximumAvailable": 1000,
                "currentlyAvailable": 995,
                "restoreRate": 50,
            },
        },
        "request_id": "request-p06-fixture",
    }


def _product_scan_fixture(index: int) -> dict[str, object]:
    return _envelope({
        "products": {
            "edges": [{
                "cursor": f"product-edge-{index}",
                "node": {
                    "id": f"gid://shopify/Product/{index + 1}",
                    "updatedAt": f"2026-08-30T12:{index // 60:02d}:{index % 60:02d}Z",
                    "status": ("active", "archived", "draft", "unlisted")[index % 4],
                },
            }],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    })


def _customer_fixture(index: int) -> dict[str, object]:
    return _envelope({
        "customer": {
            "id": f"gid://shopify/Customer/{index + 1}",
            "firstName": f"Ada{index}",
            "lastName": "Lovelace",
            "displayName": f"Ada Lovelace {index}",
            "defaultEmailAddress": {"emailAddress": f"ada{index}@example.test"},
            "defaultPhoneNumber": {"phoneNumber": f"+1555000{index:04d}"},
            "defaultAddress": {
                "address1": "Analytical Engine Way",
                "address2": None,
                "city": "London",
                "zip": "NW1",
                "provinceCode": None,
                "countryCodeV2": "GB",
            },
            "updatedAt": "2026-08-30T12:00:00Z",
        }
    })


def _order_scan_fixture(index: int) -> dict[str, object]:
    return _envelope({
        "orders": {
            "edges": [{
                "cursor": f"order-edge-{index}",
                "node": {
                    "id": f"gid://shopify/Order/{index + 1}",
                    "updatedAt": "2026-08-30T12:00:00Z",
                    "createdAt": "2026-08-30T11:00:00Z",
                    "edited": bool(index % 2),
                    "test": False,
                    "cancelledAt": None,
                    "displayFinancialStatus": "PAID",
                },
            }],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    })


def _location_fixture(cursor: str | None) -> dict[str, object]:
    if cursor is None:
        return _envelope({
            "locations": {
                "nodes": [{"id": "gid://shopify/Location/1", "name": "Main", "isActive": True}],
                "pageInfo": {"hasNextPage": True, "endCursor": "loc-cursor-1"},
            }
        })
    return _envelope({
        "locations": {
            "nodes": [{"id": "gid://shopify/Location/2", "name": "Overflow", "isActive": False}],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    })


def _order_header_fixture() -> dict[str, object]:
    return _envelope({
        "order": {
            "id": "gid://shopify/Order/77",
            "name": "#1077",
            "legacyResourceId": "77",
            "createdAt": "2026-08-30T11:00:00Z",
            "processedAt": "2026-08-30T11:01:00Z",
            "updatedAt": "2026-08-30T12:00:00Z",
            "edited": False,
            "test": False,
            "currencyCode": "USD",
            "presentmentCurrencyCode": "USD",
            "taxesIncluded": True,
            "confirmed": True,
            "closed": False,
            "closedAt": None,
            "cancelledAt": None,
            "cancelReason": None,
            "displayFinancialStatus": "PAID",
            "displayFulfillmentStatus": "UNFULFILLED",
            "email": "buyer@example.test",
            "paymentGatewayNames": ["shopify_payments"],
            "transactions": [],
            "customer": {
                "id": "gid://shopify/Customer/9",
                "firstName": "Ada",
                "lastName": "Lovelace",
                "defaultEmailAddress": {"emailAddress": "buyer@example.test"},
                "defaultPhoneNumber": None,
            },
            "billingAddress": None,
            "shippingAddress": None,
            "totalPriceSet": None,
            "subtotalPriceSet": None,
            "totalTaxSet": None,
            "totalDiscountsSet": None,
            "totalShippingPriceSet": None,
            "totalTipReceivedSet": None,
            "currentTotalPriceSet": None,
            "currentTotalTaxSet": None,
            "currentShippingPriceSet": None,
            "currentTotalAdditionalFeesSet": None,
            "currentTotalDutiesSet": None,
            "totalCashRoundingAdjustment": None,
            "taxLines": [],
            "lineItems": {
                "edges": [{
                    "cursor": "line-edge-1",
                    "node": {
                        "id": "gid://shopify/LineItem/1",
                        "name": "Analytical Engine",
                        "title": "Analytical Engine",
                        "variantTitle": None,
                        "quantity": 1,
                        "currentQuantity": 1,
                        "sku": "AE-1",
                        "isGiftCard": False,
                        "requiresShipping": True,
                        "taxable": True,
                        "variant": {"id": "gid://shopify/ProductVariant/1"},
                        "product": {"id": "gid://shopify/Product/1"},
                        "originalUnitPriceSet": None,
                        "originalTotalSet": None,
                        "discountedUnitPriceSet": None,
                        "discountedTotalSet": None,
                        "discountedUnitPriceAfterAllDiscountsSet": None,
                        "discountAllocations": [],
                        "taxLines": [],
                    },
                }],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            },
            "shippingLines": {
                "edges": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            },
            "discountApplications": {
                "edges": [],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            },
        }
    })


class TestP06ReadGatewayContracts(unittest.TestCase):
    def test_odoo_wired_cross_addon_imports_use_one_canonical_package(self):
        for path in (
            PRODUCT_ROOT / "integration" / "shopify" / "read_gateway.py",
            SALE_ROOT / "integration" / "shopify" / "read_dto.py",
            SALE_ROOT / "integration" / "shopify" / "read_gateway.py",
        ):
            source = path.read_text(encoding="utf-8")
            self.assertIn("odoo.addons.shopify_connector_core", source, path)
            self.assertNotIn("from shopify_connector_core.", source, path)
        adapter_source = (
            CORE_ROOT / "models" / "shopify_connector_read_gateway.py"
        ).read_text(encoding="utf-8")
        product_adapter_source = (
            PRODUCT_ROOT / "models" / "shopify_connector_read_gateway.py"
        ).read_text(encoding="utf-8")
        sale_adapter_source = (
            SALE_ROOT / "models" / "shopify_connector_read_gateway.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import requests", adapter_source)
        self.assertNotIn(".sudo(", adapter_source)
        self.assertIn("self.env.registry.cursor()", adapter_source)
        self.assertIn("_record_comparison(job, evidence, claim=claim)", adapter_source)
        self.assertLess(
            adapter_source.index("append(side_env, side_job)"),
            adapter_source.index("cursor.commit()"),
        )
        for method in ("read_store_capability", "read_location_page"):
            self.assertIn("def %s" % method, adapter_source)
        for method in ("read_product_page", "read_product"):
            self.assertIn("def %s" % method, product_adapter_source)
            self.assertNotIn("def %s" % method, adapter_source)
        for method in ("read_customer", "read_order_scan_page", "read_order_header"):
            self.assertIn("def %s" % method, sale_adapter_source)
            self.assertNotIn("def %s" % method, adapter_source)

        # Importing through an installed Odoo addon path must resolve the same
        # contract module object used by product/sale gateways.  A duplicate
        # top-level addon import would make isinstance checks fail only after
        # registry loading, so keep this as an explicit smoke assertion.
        canonical_contracts = sys.modules[
            "odoo.addons.shopify_connector_core.integration.shopify.read_contracts"
        ]
        self.assertIs(product_read_module.ReadCompatibilityAdapter,
                      canonical_contracts.ReadCompatibilityAdapter)
        self.assertIs(sale_dto_module.MoneyDTO, canonical_contracts.MoneyDTO)

    def test_compare_reads_is_deterministic_bounded_and_payload_free(self):
        self.assertEqual(
            should_compare("store-a", "ConnectorProductScan", {}, modulus=2),
            should_compare("store-a", "ConnectorProductScan", {}, modulus=2),
        )
        # The stable predicate must not vary with dictionary insertion order.
        self.assertEqual(
            should_compare(7, "ConnectorOrderScan", {"after": None, "first": 100}, modulus=7),
            should_compare(7, "ConnectorOrderScan", {"first": 100, "after": None}, modulus=7),
        )
        evidence = compare_values(
            "ConnectorCustomerImport",
            {"email": "private@example.test", "id": "gid://shopify/Customer/1"},
            {"email": "private@example.test", "id": "gid://shopify/Customer/1"},
        )
        self.assertTrue(evidence.equal)
        self.assertNotIn("private@example.test", json.dumps(evidence.as_dict()))
        with self.assertRaises(ValueError):
            should_compare("store-a", "MutationNotAllowed", {}, modulus=2)
        with self.assertRaises(ValueError):
            ReadComparisonEvidence(
                "ConnectorOrderScan", False, True, "0" * 64, None,
            )
        self.assertIn("ConnectorOrderHeader", REPLAY_SAFE_READ_OPERATIONS)

    def test_operation_names_are_existing_read_documents_only(self):
        operations = {
            "ConnectorTestConnection",
            "ConnectorFulfillmentLocations",
            PRODUCT_SCAN_OPERATION.operation_name,
            PRODUCT_READ_OPERATION.operation_name,
            CUSTOMER_READ_OPERATION.operation_name,
            ORDER_SCAN_OPERATION.operation_name,
            ORDER_HEADER_OPERATION.operation_name,
            "ConnectorOrderLineItemsPage",
            "ConnectorOrderShippingLinesPage",
            "ConnectorOrderDiscountApplicationsPage",
        }
        inventory = json.loads((ROOT / "docs/v2/evidence/shopify-operation-inventory.json").read_text(encoding="utf-8"))
        available = {item["name"] for item in inventory["operations"] if item["kind"] == "query"}
        self.assertTrue(operations <= available)
        self.assertFalse(operations - available)
        self.assertTrue(all(document.lstrip().startswith("query ") for document in OPERATION_DOCUMENTS.values()))

    def test_one_legacy_delegate_call_and_safe_core_reads(self):
        source = _FixtureSource()
        source.set("ConnectorTestConnection", _envelope({
            "shop": {"id": "gid://shopify/Shop/1", "name": "Demo", "myshopifyDomain": "demo.myshopify.com"},
            "currentAppInstallation": {"accessScopes": [{"handle": "read_products"}, {"handle": "read_orders"}]},
        }))
        legacy_adapter, legacy, _typed = _adapter(source)
        result = StoreCapabilityReadGateway(legacy_adapter).read("store-1")
        self.assertEqual(len(legacy.calls), 1)
        self.assertEqual(result.value.as_dict()["store"]["gid"], "gid://shopify/Shop/1")
        self.assertEqual(result.observation.actual_query_cost, 5)
        self.assertEqual(json.loads(json.dumps(result.as_dict()))["value"]["granted_scopes"], ["read_orders", "read_products"])

    def test_response_envelope_is_strict_and_version_pinned(self):
        malformed = (
            {"data": {}, "served_version": "2026-07", "extensions": []},
            {"data": {}, "served_version": "2026-07", "errors": {}},
            {"data": [], "served_version": "2026-07"},
            {"data": {}, "served_version": "2025-10"},
            {"data": {}, "extensions": {}},
            {"data": {}, "served_version": "2026-07", "extensions": {"cost": []}},
            {"data": {}, "served_version": "2026-07", "cost": "not-a-cost"},
        )
        for envelope in malformed:
            with self.subTest(envelope=envelope), self.assertRaises(ReadGatewayError):
                response_data(envelope, "ConnectorTestConnection")

    def test_identity_validation_happens_before_delegate_and_errors_are_safe(self):
        source = _FixtureSource()
        source.set("ConnectorProductImport", _envelope({"product": None}))
        adapter, legacy, _typed = _adapter(source)
        with self.assertRaises(ReadGatewayError):
            ProductReadGateway(adapter).read_product("store", "not-a-shopify-gid")
        self.assertEqual(legacy.calls, [])

        class _FailingDelegate:
            def execute(self, _store, _document, _variables):
                raise RuntimeError("access token should never be exposed")

        failing = ReadCompatibilityAdapter(_FailingDelegate(), OPERATION_DOCUMENTS)
        with self.assertRaises(ReadGatewayError) as context:
            failing.execute("store", PRODUCT_SCAN_OPERATION, {"first": 100, "after": None, "query": ""})
        self.assertEqual(context.exception.code, "delegate_failure")
        self.assertNotIn("access token", str(context.exception))

    def test_locations_are_bounded_and_cursor_progress_is_explicit(self):
        source = _FixtureSource()
        source.set("ConnectorFulfillmentLocations", lambda variables: _location_fixture(variables.get("cursor")))
        adapter, legacy, _typed = _adapter(source)
        progress = CursorProgress(max_pages=2, max_items=2)
        gateway = LocationReadGateway(adapter)
        first = gateway.read_page("store", progress=progress)
        second = gateway.read_page("store", cursor=first.value.next_cursor, progress=progress)
        self.assertEqual([item.gid for item in first.value.items], ["gid://shopify/Location/1"])
        self.assertFalse(second.value.has_more)
        self.assertEqual(progress.pages, 2)
        self.assertEqual(len(legacy.calls), 2)
        source.set("ConnectorFulfillmentLocations", _envelope({
            "locations": {
                "nodes": [],
                "pageInfo": {"hasNextPage": True, "endCursor": "same"},
            }
        }))
        bad_progress = CursorProgress(max_pages=2)
        with self.assertRaises(ReadGatewayError):
            gateway.read_page("store", cursor="same", progress=bad_progress)

    def test_product_variants_are_typed_and_variant_page_has_bound(self):
        source = _FixtureSource()
        source.set("ConnectorProductImport", _envelope({
            "product": {
                "id": "gid://shopify/Product/3",
                "title": "Engine",
                "status": "ACTIVE",
                "descriptionHtml": "<p>text</p>",
                "vendor": "Adams",
                "productType": "Machine",
                "tags": ["featured"],
                "updatedAt": "2026-08-30T12:00:00Z",
                "featuredImage": {"url": "https://cdn.example.test/engine.png"},
                "options": [{
                    "id": "gid://shopify/ProductOption/1",
                    "name": "Size",
                    "position": 1,
                    "optionValues": [{"id": "gid://shopify/ProductOptionValue/1", "name": "Large"}],
                }],
                "variants": {
                    "nodes": [{
                        "id": "gid://shopify/ProductVariant/4",
                        "sku": "ENG-L",
                        "barcode": None,
                        "price": "19.99",
                        "compareAtPrice": "25.00",
                        "selectedOptions": [{"name": "Size", "value": "Large"}],
                        "image": None,
                        "inventoryItem": {"id": "gid://shopify/InventoryItem/4", "tracked": False},
                    }],
                    "pageInfo": {"hasNextPage": False, "endCursor": None},
                },
            }
        }))
        adapter, legacy, _typed = _adapter(source)
        result = ProductReadGateway(adapter).read_product("store", "gid://shopify/Product/3")
        self.assertEqual(len(legacy.calls), 1)
        self.assertEqual(result.value.variants.items[0].price, "19.99")
        self.assertEqual(result.value.variants.items[0].compare_at_price, "25.00")
        self.assertFalse(result.value.variants.items[0].inventory_tracked)
        self.assertTrue(result.value.variants.items[0].inventory_tracked_known)
        self.assertEqual(json.loads(json.dumps(result.as_dict()))["value"]["variants"]["items"][0]["sku"], "ENG-L")
        with self.assertRaises(TypeError):
            result.value.variants.items[0] = None  # type: ignore[index]

    def test_order_header_and_customer_preserve_evidence_without_writes(self):
        source = _FixtureSource()
        source.set("ConnectorCustomerImport", _customer_fixture(1))
        source.set("ConnectorOrderHeader", _order_header_fixture())
        adapter, legacy, _typed = _adapter(source)
        customer = CustomerReadGateway(adapter).read_customer("store", "gid://shopify/Customer/2")
        order = OrderReadGateway(adapter).read_order_header("store", "gid://shopify/Order/77")
        self.assertEqual(customer.value.default_address.country_code, "GB")
        self.assertEqual(order.value.line_items.items[0].sku, "AE-1")
        self.assertEqual(order.value.customer.email, "buyer@example.test")
        self.assertEqual(len(legacy.calls), 2)
        serialized = json.dumps(order.as_dict())
        self.assertIn("gid://shopify/Order/77", serialized)
        with self.assertRaises(TypeError):
            order.value.totals["new"] = None  # type: ignore[index]

    def test_typed_mode_and_rollback_keep_normalized_output_and_call_once(self):
        source = _FixtureSource()
        source.set("ConnectorProductScan", _product_scan_fixture(1))
        adapter, legacy, typed = _adapter(source)
        typed_gateway = ProductReadGateway(adapter.for_mode(ReadGatewayMode.TYPED))
        legacy_gateway = ProductReadGateway(adapter.rollback())
        typed_result = typed_gateway.read_product_page("store")
        legacy_result = legacy_gateway.read_product_page("store")
        self.assertEqual(typed_result.as_dict(), legacy_result.as_dict())
        self.assertEqual(len(typed.calls), 1)
        self.assertEqual(len(legacy.calls), 1)
        self.assertTrue(adapter.rollback().is_legacy)

    def test_cursor_loop_and_page_limit_fail_closed(self):
        source = _FixtureSource()
        source.set("ConnectorProductScan", _envelope({
            "products": {
                "edges": [{"cursor": "edge-1", "node": {"id": "gid://shopify/Product/1", "updatedAt": "2026-08-30T12:00:00Z", "status": "active"}}],
                "pageInfo": {"hasNextPage": True, "endCursor": "same"},
            }
        }))
        adapter, _legacy, _typed = _adapter(source)
        progress = CursorProgress(max_pages=1)
        gateway = ProductReadGateway(adapter)
        first = gateway.read_product_page("store", progress=progress)
        with self.assertRaises(ReadGatewayError):
            gateway.read_product_page("store", cursor=first.value.next_cursor, progress=progress)

    def test_page_and_item_bounds_fail_closed_before_continuation(self):
        source = _FixtureSource()
        source.set("ConnectorProductScan", _envelope({
            "products": {
                "edges": [
                    {
                        "cursor": f"edge-{index}",
                        "node": {
                            "id": f"gid://shopify/Product/{index + 1}",
                            "updatedAt": "2026-08-30T12:00:00Z",
                            "status": "active",
                        },
                    }
                    for index in range(101)
                ],
                "pageInfo": {"hasNextPage": False, "endCursor": None},
            }
        }))
        adapter, _legacy, _typed = _adapter(source)
        with self.assertRaises(ReadGatewayError) as context:
            ProductReadGateway(adapter).read_product_page("store")
        self.assertEqual(context.exception.code, "page_size")

        progress = CursorProgress(max_pages=2, max_items=1)
        progress.accept(cursor=None, has_more=False, next_cursor=None, item_count=1)
        with self.assertRaises(ReadGatewayError) as context:
            progress.accept(cursor=None, has_more=False, next_cursor=None, item_count=1)
        self.assertEqual(context.exception.code, "item_limit")

    def test_cursor_bounds_are_checked_before_the_delegate(self):
        source = _FixtureSource()
        source.set("ConnectorProductScan", _product_scan_fixture(1))
        adapter, legacy, _typed = _adapter(source)
        with self.assertRaises(ReadGatewayError) as context:
            ProductReadGateway(adapter).read_product_page("store", cursor="x" * 513)
        self.assertEqual(context.exception.code, "cursor_invalid")
        self.assertEqual(legacy.calls, [])

    def test_strict_numeric_and_money_boundaries_reject_booleans_and_partial_sides(self):
        with self.assertRaises(ReadGatewayError):
            response_data(
                {"data": {}, "served_version": "2026-07", "cost": {"actualQueryCost": False}},
                "ConnectorTestConnection",
            )
        with self.assertRaises(ValueError):
            from odoo.addons.shopify_connector_core.integration.shopify.read_contracts import ReadPage, ReadObservation
            ReadPage((), None, None, False, 2, 1, ReadObservation(served_version="2026-07"))
        with self.assertRaises(ValueError):
            MoneyDTO("1.00", "usd")
        with self.assertRaises(ValueError):
            MoneyDTO("1.00", None)

    def test_v1_numeric_tax_rates_are_normalized_without_float_artifacts(self):
        from shopify_connector_sale.integration.shopify.read_dto import TaxLineEvidenceDTO

        line = TaxLineEvidenceDTO("VAT", "shopify", 0.05, 5.0, False, None)
        self.assertEqual(line.rate, "0.05")
        self.assertEqual(line.rate_percentage, "5.0")
        self.assertEqual(json.loads(json.dumps(line.as_dict()))["rate_percentage"], "5.0")
        with self.assertRaises(ReadGatewayError):
            TaxLineEvidenceDTO("VAT", "shopify", True, 5.0, False, None)

    def test_product_price_and_optional_position_reject_boolean_values(self):
        from shopify_connector_product.integration.shopify.read_gateway import _optional_int, _price

        with self.assertRaises(ReadGatewayError):
            _optional_int(False, "position")
        with self.assertRaises(ReadGatewayError):
            _price(True)
        with self.assertRaises(ReadGatewayError):
            _price(19.99)
        with self.assertRaises(ReadGatewayError):
            _price("NaN")
        self.assertEqual(_price("19.9900"), "19.9900")

    def test_product_and_variant_identity_cannot_overlap_across_pages(self):
        source = _FixtureSource()
        source.set("ConnectorProductScan", lambda variables: _envelope({
            "products": {
                "edges": [{
                    "cursor": "first-edge" if variables.get("after") is None else "second-edge",
                    "node": {
                        "id": "gid://shopify/Product/1",
                        "updatedAt": "2026-08-30T12:00:00Z",
                        "status": "active",
                    },
                }],
                "pageInfo": {
                    "hasNextPage": variables.get("after") is None,
                    "endCursor": "next-product" if variables.get("after") is None else None,
                },
            }
        }))
        adapter, _legacy, _typed = _adapter(source)
        progress = CursorProgress(max_pages=2)
        gateway = ProductReadGateway(adapter)
        first = gateway.read_product_page("store", progress=progress)
        with self.assertRaises(ReadGatewayError) as context:
            gateway.read_product_page("store", cursor=first.value.next_cursor, progress=progress)
        self.assertEqual(context.exception.code, "identity_duplicate")

    def test_generated_1000_fixture_parity_for_core_product_and_sale_reads(self):
        source = _FixtureSource()
        adapter, _legacy, _typed = _adapter(source)
        legacy_product = ProductReadGateway(adapter.rollback())
        typed_product = ProductReadGateway(adapter.for_mode(ReadGatewayMode.TYPED))
        legacy_customer = CustomerReadGateway(adapter.rollback())
        typed_customer = CustomerReadGateway(adapter.for_mode(ReadGatewayMode.TYPED))
        legacy_order = OrderReadGateway(adapter.rollback())
        typed_order = OrderReadGateway(adapter.for_mode(ReadGatewayMode.TYPED))
        rng = random.Random(20260830)
        for index in range(1000):
            # The seed and generated index are recorded in the test itself so
            # a parity failure is reproducible without a fixture artifact.
            generated = index + rng.randrange(0, 10000)
            source.set("ConnectorProductScan", _product_scan_fixture(generated))
            source.set("ConnectorCustomerImport", _customer_fixture(generated))
            source.set("ConnectorOrderScan", _order_scan_fixture(generated))
            product_legacy = legacy_product.read_product_page("store")
            product_typed = typed_product.read_product_page("store")
            customer_legacy = legacy_customer.read_customer("store", f"gid://shopify/Customer/{generated + 1}")
            customer_typed = typed_customer.read_customer("store", f"gid://shopify/Customer/{generated + 1}")
            order_legacy = legacy_order.read_order_scan_page("store")
            order_typed = typed_order.read_order_scan_page("store")
            self.assertEqual(product_legacy.as_dict(), product_typed.as_dict(), generated)
            self.assertEqual(customer_legacy.as_dict(), customer_typed.as_dict(), generated)
            self.assertEqual(order_legacy.as_dict(), order_typed.as_dict(), generated)


if __name__ == "__main__":
    unittest.main()
