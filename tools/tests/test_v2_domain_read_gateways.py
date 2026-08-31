"""Pure contract, parity and fault tests for the P07 read gateways."""

from __future__ import annotations

import ast
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"


def _pure_core_namespace() -> None:
    # Production Odoo imports resolve addon modules below ``odoo.addons``.
    # Mirror that namespace in the dependency-light pure test so the module
    # object tested here is the same one the installed addon will load.
    namespaces = (
        ("odoo", ROOT),
        ("odoo.addons", ROOT / "addons"),
        ("odoo.addons.shopify_connector_core", CORE),
        ("odoo.addons.shopify_connector_core.domain", CORE / "domain"),
        # Pure V2 adapters are also importable through their package namespace
        # in dependency-free tests.  Production Odoo adapters may retain the
        # canonical ``odoo.addons`` spelling; both resolve the same contracts.
        ("shopify_connector_core", CORE),
        ("shopify_connector_core.domain", CORE / "domain"),
        ("odoo.addons.shopify_connector_inventory", ROOT / "addons/shopify_connector_inventory"),
        ("odoo.addons.shopify_connector_inventory.integration", ROOT / "addons/shopify_connector_inventory/integration"),
        ("odoo.addons.shopify_connector_inventory.integration.shopify", ROOT / "addons/shopify_connector_inventory/integration/shopify"),
        ("odoo.addons.shopify_connector_fulfillment", ROOT / "addons/shopify_connector_fulfillment"),
        ("odoo.addons.shopify_connector_fulfillment.integration", ROOT / "addons/shopify_connector_fulfillment/integration"),
        ("odoo.addons.shopify_connector_fulfillment.integration.shopify", ROOT / "addons/shopify_connector_fulfillment/integration/shopify"),
        ("odoo.addons.shopify_connector_webhook", ROOT / "addons/shopify_connector_webhook"),
        ("odoo.addons.shopify_connector_webhook.integration", ROOT / "addons/shopify_connector_webhook/integration"),
        ("odoo.addons.shopify_connector_webhook.integration.shopify", ROOT / "addons/shopify_connector_webhook/integration/shopify"),
    )
    for name, path in namespaces:
        package = sys.modules.get(name)
        if package is None:
            package = types.ModuleType(name)
            package.__path__ = [str(path)]
            package.__package__ = name
            sys.modules[name] = package


def _load(name: str, path: Path):
    _pure_core_namespace()
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


INV = _load(
    "odoo.addons.shopify_connector_inventory.integration.shopify.inventory_read_gateway",
    ROOT / "addons/shopify_connector_inventory/integration/shopify/inventory_read_gateway.py",
)
FUL = _load(
    "odoo.addons.shopify_connector_fulfillment.integration.shopify.fulfillment_read_gateway",
    ROOT / "addons/shopify_connector_fulfillment/integration/shopify/fulfillment_read_gateway.py",
)
WEB = _load(
    "odoo.addons.shopify_connector_webhook.integration.shopify.webhook_subscription_read_gateway",
    ROOT / "addons/shopify_connector_webhook/integration/shopify/webhook_subscription_read_gateway.py",
)


DOMAIN = "northwind.myshopify.com"
UTC = timezone.utc


def _response(data, **extra):
    envelope = {"data": data, "served_version": "2026-07"}
    envelope.update(extra)
    return envelope


class Delegate:
    """Deterministic one-call-per-page fake; payloads are never mutated."""

    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def read(self, operation, variables):
        self.calls.append((operation, dict(variables)))
        response = self.responses.get((operation, variables.get("cursor"), variables.get("foCursor"), variables.get("lineCursor"), variables.get("after")))
        if response is None:
            response = self.responses.get(operation)
        if callable(response):
            response = response(variables)
        if isinstance(response, Exception):
            raise response
        return response


def _pair_response(item=1, location=2, level=3, available=8, updated="2026-08-30T12:00:00Z"):
    return _response({"shop": {"myshopifyDomain": DOMAIN}, "inventoryItem": {
        "id": f"gid://shopify/InventoryItem/{item}", "tracked": True,
        "inventoryLevel": {"id": f"gid://shopify/InventoryLevel/{level}?inventory_item_id={item}",
                            "item": {"id": f"gid://shopify/InventoryItem/{item}"},
                            "location": {"id": f"gid://shopify/Location/{location}"},
                            "quantities": [{"name": "available", "quantity": available, "updatedAt": updated}]},
    }})


def _level_response(item=1, location=2, level=3, available=8):
    return _response({"shop": {"myshopifyDomain": DOMAIN}, "inventoryLevel": {
        "id": f"gid://shopify/InventoryLevel/{level}?inventory_item_id={item}",
        "item": {"id": f"gid://shopify/InventoryItem/{item}", "tracked": True},
        "location": {"id": f"gid://shopify/Location/{location}"},
        "quantities": [{"name": "available", "quantity": available, "updatedAt": "2026-08-30T12:00:00+00:00"}],
    }})


def _location_page(cursor=None, has_next=False, number=1):
    edge = {"cursor": f"cursor-{number}", "node": {"id": f"gid://shopify/Location/{number}", "name": f"Warehouse {number}"}}
    return _response({"shop": {"myshopifyDomain": DOMAIN}, "locations": {
        "edges": [edge], "pageInfo": {"hasNextPage": has_next},
    }})


def _fo_page(order=1, cursor=None, has_next=False, number=1):
    fo = {"id": f"gid://shopify/FulfillmentOrder/{number}", "status": "OPEN",
          "requestStatus": None, "assignedLocation": None, "supportedActions": [{"action": "CREATE_FULFILLMENT"}]}
    return _response({"order": {"id": f"gid://shopify/Order/{order}", "fulfillmentOrders": {
        "nodes": [fo], "pageInfo": {"hasNextPage": has_next, "endCursor": f"fo-{number}" if has_next else None},
    }}})


def _line_page(fo=1, has_next=False, number=1):
    line = {"id": f"gid://shopify/FulfillmentOrderLineItem/{number}", "remainingQuantity": 2,
            "lineItem": {"id": f"gid://shopify/LineItem/{number}"}}
    return _response({"fulfillmentOrder": {"id": f"gid://shopify/FulfillmentOrder/{fo}", "lineItems": {
        "nodes": [line], "pageInfo": {"hasNextPage": has_next, "endCursor": f"line-{number}" if has_next else None},
    }}})


class InventoryGatewayTests(unittest.TestCase):
    def test_pair_has_exact_v1_output_and_one_delegate_call(self):
        delegate = Delegate({INV.INVENTORY_PAIR_OPERATION: _pair_response()})
        dto = INV.InventoryReadGateway(delegate, store_domain=DOMAIN).read_inventory_pair(
            "gid://shopify/InventoryItem/1", "gid://shopify/Location/2"
        )
        self.assertEqual(dto.to_legacy_dict(), {
            "store_identity": DOMAIN, "item_exists": True, "tracked": True,
            "level_exists": True, "inventory_level_gid": "gid://shopify/InventoryLevel/3?inventory_item_id=1",
            "available": 8, "updated_at": "2026-08-30T12:00:00Z",
        })
        self.assertEqual(len(delegate.calls), 1)
        self.assertEqual(delegate.calls[0][0], INV.INVENTORY_PAIR_OPERATION)

    def test_pair_generated_parity_and_missing_item(self):
        for number in range(1, 101):
            delegate = Delegate({INV.INVENTORY_PAIR_OPERATION: _pair_response(item=number, location=number + 100, level=number + 200, available=number)})
            dto = INV.InventoryReadGateway(delegate).read_inventory_pair(
                f"gid://shopify/InventoryItem/{number}", f"gid://shopify/Location/{number + 100}"
            )
            self.assertEqual(dto.to_legacy_dict()["available"], number)
        missing = _response({"shop": {"myshopifyDomain": DOMAIN}, "inventoryItem": None})
        dto = INV.InventoryReadGateway(Delegate({INV.INVENTORY_PAIR_OPERATION: missing})).read_inventory_pair(
            "gid://shopify/InventoryItem/1", "gid://shopify/Location/2"
        )
        self.assertEqual(dto.to_legacy_dict(), {"store_identity": DOMAIN, "item_exists": False, "tracked": None, "level_exists": False, "inventory_level_gid": None, "available": None, "updated_at": False})

    def test_pair_rejects_wrong_identity_duplicate_or_boolean_quantity(self):
        for response in (
            _response({"shop": {"myshopifyDomain": DOMAIN}, "inventoryItem": {"id": "gid://shopify/InventoryItem/9", "tracked": True}}),
            _pair_response(available=True),
        ):
            with self.assertRaises(INV.InventoryReadError):
                INV.InventoryReadGateway(Delegate({INV.INVENTORY_PAIR_OPERATION: response})).read_inventory_pair(
                    "gid://shopify/InventoryItem/1", "gid://shopify/Location/2"
                )
        duplicate = _pair_response()
        duplicate["data"]["inventoryItem"]["inventoryLevel"]["quantities"].append({"name": "available", "quantity": 8})
        with self.assertRaises(INV.InventoryReadError):
            INV.InventoryReadGateway(Delegate({INV.INVENTORY_PAIR_OPERATION: duplicate})).read_inventory_pair(
                "gid://shopify/InventoryItem/1", "gid://shopify/Location/2"
            )

    def test_inventory_level_requires_authoritative_timestamp_and_identity(self):
        delegate = Delegate({INV.INVENTORY_LEVEL_OPERATION: _level_response()})
        dto = INV.InventoryReadGateway(delegate, store_domain=DOMAIN).read_inventory_level(
            "gid://shopify/InventoryLevel/3?inventory_item_id=1"
        )
        self.assertEqual(dto.to_legacy_dict()["available"], 8)
        self.assertEqual(dto.source_updated_at, datetime(2026, 8, 30, 12, tzinfo=UTC))
        malformed = _level_response()
        malformed["data"]["inventoryLevel"]["quantities"][0]["updatedAt"] = "2026-08-30 12:00:00"
        with self.assertRaises(INV.InventoryReadError):
            INV.InventoryReadGateway(Delegate({INV.INVENTORY_LEVEL_OPERATION: malformed})).read_inventory_level(
                "gid://shopify/InventoryLevel/3?inventory_item_id=1"
            )

    def test_locations_are_bounded_and_cursored_one_call_per_page(self):
        def response(variables):
            return _location_page(has_next=variables.get("cursor") is None, number=1 if variables.get("cursor") is None else 2)
        delegate = Delegate({INV.LOCATIONS_OPERATION: response})
        result = INV.InventoryReadGateway(delegate, max_pages=2).read_all_locations()
        self.assertEqual([item.gid for item in result], ["gid://shopify/Location/1", "gid://shopify/Location/2"])
        self.assertEqual(len(delegate.calls), 2)
        self.assertEqual(delegate.calls[1][1]["cursor"], "cursor-1")
        repeated = Delegate({INV.LOCATIONS_OPERATION: _response({"shop": {"myshopifyDomain": DOMAIN}, "locations": {"edges": [{"cursor": "same", "node": {"id": "gid://shopify/Location/1", "name": "A"}}], "pageInfo": {"hasNextPage": True}}})})
        with self.assertRaises(INV.InventoryReadError):
            INV.InventoryReadGateway(repeated, max_pages=2).read_all_locations()
        oversized = _location_page()
        oversized["data"]["locations"]["edges"] *= INV.MAX_PAGE_SIZE + 1
        with self.assertRaises(INV.InventoryReadError):
            INV.InventoryReadGateway(
                Delegate({INV.LOCATIONS_OPERATION: oversized})
            ).read_locations_page()


class FulfillmentGatewayTests(unittest.TestCase):
    def test_fulfillment_order_and_lines_paginate_with_exact_legacy_shape(self):
        def response(operation, variables):
            if operation == FUL.FULFILLMENT_ORDERS_OPERATION:
                return _fo_page(has_next=variables.get("foCursor") is None, number=1 if variables.get("foCursor") is None else 2)
            number = int(variables["foId"].rsplit("/", 1)[1])
            return _line_page(fo=number, has_next=False, number=number)
        delegate = Delegate()
        def read(operation, variables):
            delegate.calls.append((operation, dict(variables)))
            return response(operation, variables)
        delegate.read = read
        result = FUL.FulfillmentReadGateway(delegate, max_pages=2).read_fulfillment_orders("gid://shopify/Order/1")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].to_legacy_dict()["line_items"][0]["remainingQuantity"], 2)
        self.assertEqual(len(delegate.calls), 4)

    def test_order_fulfillments_reject_incomplete_list_and_preserve_records(self):
        record = {"id": "gid://shopify/Fulfillment/1", "status": "SUCCESS", "displayStatus": "FULFILLED", "trackingInfo": None,
                  "fulfillmentLineItems": {"pageInfo": {"hasNextPage": False, "endCursor": "terminal-line-cursor"}, "nodes": []}}
        response = _response({"order": {"id": "gid://shopify/Order/1", "fulfillments": [record]}})
        dto = FUL.FulfillmentReadGateway(Delegate({FUL.ORDER_FULFILLMENTS_OPERATION: response})).read_order_fulfillments("gid://shopify/Order/1")[0]
        self.assertEqual(dto.to_legacy_dict()["id"], record["id"])
        self.assertEqual(
            dto.to_legacy_dict()["fulfillmentLineItems"]["pageInfo"]["endCursor"],
            "terminal-line-cursor",
        )
        bad = _response({"order": {"id": "gid://shopify/Order/1", "fulfillments": [dict(record, fulfillmentLineItems={"pageInfo": {"hasNextPage": True}, "nodes": []})]}})
        with self.assertRaises(FUL.FulfillmentReadError):
            FUL.FulfillmentReadGateway(Delegate({FUL.ORDER_FULFILLMENTS_OPERATION: bad})).read_order_fulfillments("gid://shopify/Order/1")

    def test_batch_is_bounded_and_each_batch_is_one_call(self):
        gids = [f"gid://shopify/Fulfillment/{n}" for n in range(1, 52)]

        def response(_operation, variables):
            return _response({"nodes": [None for _ in variables["ids"]]})

        delegate = Delegate()
        def read(operation, variables):
            delegate.calls.append((operation, dict(variables)))
            return response(operation, variables)
        delegate.read = read
        result = FUL.FulfillmentReadGateway(delegate).read_fulfillments_batch(gids)
        self.assertEqual(len(result), 51)
        self.assertEqual(len(delegate.calls), 2)
        with self.assertRaises(FUL.FulfillmentReadError):
            FUL.FulfillmentReadGateway(delegate).read_fulfillments_batch(
                [
                    f"gid://shopify/Fulfillment/{number}"
                    for number in range(1, FUL.MAX_BATCH_ITEMS + 2)
                ]
            )
        with self.assertRaises(FUL.FulfillmentReadError):
            FUL.FulfillmentReadGateway(delegate).read_fulfillments_batch(
                "gid://shopify/Fulfillment/1"
            )

    def test_page_faults_never_treat_has_next_without_cursor_as_complete(self):
        response = _fo_page(has_next=True)
        response["data"]["order"]["fulfillmentOrders"]["pageInfo"]["endCursor"] = None
        with self.assertRaises(FUL.FulfillmentReadError):
            FUL.FulfillmentReadGateway(Delegate({FUL.FULFILLMENT_ORDERS_OPERATION: response})).read_fulfillment_orders_page("gid://shopify/Order/1")


class WebhookGatewayTests(unittest.TestCase):
    def _page(self, cursor=None, has_next=False, number=1):
        node = {"id": f"gid://shopify/WebhookSubscription/{number}", "topic": "ORDERS_CREATE", "uri": "https://connector.example/webhook?secret=never-return", "format": "JSON", "includeFields": ["id", "admin_graphql_api_id", "id"], "apiVersion": {"handle": "2026-07", "displayName": "July 2026", "supported": True}}
        return _response({"shop": {"myshopifyDomain": DOMAIN}, "webhookSubscriptions": {"nodes": [node], "pageInfo": {"hasNextPage": has_next, "endCursor": f"web-{number}" if has_next else None}}})

    def test_subscription_page_hashes_uri_and_matches_v1_keys(self):
        delegate = Delegate({WEB.SUBSCRIPTIONS_OPERATION: self._page()})
        page = WEB.WebhookSubscriptionReadGateway(delegate, store_domain=DOMAIN).read_page()
        legacy = page.to_legacy_list()[0]
        self.assertEqual(set(legacy), {"id", "topic", "uri_digest", "observed_api_version", "format", "include_fields"})
        self.assertNotIn("secret", str(legacy))
        self.assertEqual(legacy["include_fields"], ["admin_graphql_api_id", "id"])
        self.assertEqual(len(delegate.calls), 1)

    def test_subscription_pagination_checkpoint_and_faults(self):
        def response(variables):
            return self._page(number=1 if variables.get("after") is None else 2, has_next=variables.get("after") is None)
        delegate = Delegate({WEB.SUBSCRIPTIONS_OPERATION: response})
        result = WEB.WebhookSubscriptionReadGateway(delegate, max_pages=2).read_all()
        self.assertEqual(len(result.items), 2)
        self.assertEqual(result.checkpoint, "web-1")
        self.assertEqual(len(delegate.calls), 2)
        malformed = self._page()
        malformed["data"]["webhookSubscriptions"]["nodes"][0]["apiVersion"] = {"handle": "2026-07", "displayName": "July", "supported": "yes"}
        with self.assertRaises(WEB.WebhookSubscriptionReadError):
            WEB.WebhookSubscriptionReadGateway(Delegate({WEB.SUBSCRIPTIONS_OPERATION: malformed})).read_page()
        oversized = self._page()
        oversized["data"]["webhookSubscriptions"]["nodes"] *= 2
        with self.assertRaises(WEB.WebhookSubscriptionReadError):
            WEB.WebhookSubscriptionReadGateway(
                Delegate({WEB.SUBSCRIPTIONS_OPERATION: oversized})
            ).read_page(first=1)


class StructuralP07Tests(unittest.TestCase):
    def test_every_domain_fails_closed_on_version_errors_and_telemetry(self):
        cases = (
            (
                INV.InventoryReadGateway,
                INV.INVENTORY_PAIR_OPERATION,
                lambda gateway: gateway.read_inventory_pair(
                    "gid://shopify/InventoryItem/1",
                    "gid://shopify/Location/2",
                ),
                _pair_response(),
                INV.InventoryReadError,
            ),
            (
                FUL.FulfillmentReadGateway,
                FUL.FULFILLMENT_ORDERS_OPERATION,
                lambda gateway: gateway.read_fulfillment_orders_page(
                    "gid://shopify/Order/1"
                ),
                _fo_page(),
                FUL.FulfillmentReadError,
            ),
            (
                WEB.WebhookSubscriptionReadGateway,
                WEB.SUBSCRIPTIONS_OPERATION,
                lambda gateway: gateway.read_page(),
                WebhookGatewayTests()._page(),
                WEB.WebhookSubscriptionReadError,
            ),
        )
        for gateway_type, operation, invoke, valid, error_type in cases:
            for mutation in (
                lambda value: value.pop("served_version"),
                lambda value: value.update(served_version="2025-10"),
                lambda value: value.update(errors=[{"message": "denied"}]),
                lambda value: value.update(errors={"message": "malformed"}),
                lambda value: value.update(extensions={"cost": "malformed"}),
            ):
                envelope = dict(valid)
                mutation(envelope)
                with self.subTest(gateway=gateway_type.__name__, envelope=envelope):
                    gateway = gateway_type(Delegate({operation: envelope}))
                    with self.assertRaises(error_type):
                        invoke(gateway)

    def test_operation_allowlists_are_query_only_and_sources_have_no_odoo_mutations(self):
        for module in (INV, FUL, WEB):
            self.assertTrue(module.READ_OPERATION_KEYS)
            gateway = next(value for value in vars(module).values() if isinstance(value, type) and value.__name__.endswith("ReadGateway"))
            for document in gateway.operation_documents.values():
                self.assertTrue(document.lstrip().startswith("query"))
                self.assertNotIn("mutation ", document)
            source = Path(module.__file__).read_text(encoding="utf-8")
            self.assertTrue(
                "from shopify_connector_core." in source
                or "from odoo.addons.shopify_connector_core." in source
            )
            tree = ast.parse(source)
            calls = [node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)]
            self.assertFalse(set(calls) & {"create", "write", "unlink", "sudo"})


if __name__ == "__main__":
    unittest.main()
