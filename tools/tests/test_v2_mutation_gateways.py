"""Cheap, pure P08 mutation-gateway parity and uncertainty tests.

These tests intentionally load addon packages as namespace packages.  Importing
an Odoo addon initializer would pull in the ORM and defeat the point of the
unwired gateway seam.  Every transport fake records calls and returns one
response; the tests assert that a gateway never retries or performs a hidden
readback.
"""

from __future__ import annotations

import ast
from dataclasses import replace
import re
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _namespace(name: str, path: Path) -> None:
    package = sys.modules.get(name)
    if package is None:
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        package.__package__ = name
        sys.modules[name] = package


for _addon in (
    "shopify_connector_core",
    "shopify_connector_inventory",
    "shopify_connector_fulfillment",
    "shopify_connector_webhook",
    "shopify_connector_product_export",
):
    _root = ROOT / "addons" / _addon
    _namespace(_addon, _root)
    _namespace(_addon + ".domain", _root / "domain")
    _namespace(_addon + ".integration", _root / "integration")
    _namespace(_addon + ".integration.shopify", _root / "integration" / "shopify")


from shopify_connector_core.integration.shopify.mutation_contracts import (  # noqa: E402
    MutationGatewayError,
    MutationOutcome,
    MutationShapeError,
    MutationTransportError,
)
from shopify_connector_core.domain.immutability import to_plain  # noqa: E402
from shopify_connector_fulfillment.integration.shopify.fulfillment_mutation_gateway import (  # noqa: E402
    FULFILLMENT_CREATE_DOCUMENT,
    FULFILLMENT_CREATE_OPERATION,
    FULFILLMENT_MUTATION_REGISTRY,
    FULFILLMENT_TRACKING_UPDATE_DOCUMENT,
    FULFILLMENT_TRACKING_UPDATE_OPERATION,
    FulfillmentMutationGateway,
)
from shopify_connector_inventory.integration.shopify.inventory_mutation_gateway import (  # noqa: E402
    INVENTORY_ACTIVATE_DOCUMENT,
    INVENTORY_ACTIVATE_OPERATION,
    INVENTORY_MUTATION_REGISTRY,
    INVENTORY_SET_QUANTITIES_DOCUMENT,
    INVENTORY_SET_QUANTITIES_OPERATION,
    InventoryMutationGateway,
)
from shopify_connector_inventory.domain.inventory_mutation import InventoryPairScope  # noqa: E402
from shopify_connector_product_export.integration.shopify.product_export_mutation_gateway import (  # noqa: E402
    BINDING_NAMESPACE_OPERATION,
    PRODUCT_CREATE_DOCUMENT,
    PRODUCT_CREATE_OPERATION,
    PRODUCT_EXPORT_MUTATION_REGISTRY,
    PRODUCT_UPDATE_DOCUMENT,
    VARIANTS_CREATE_DOCUMENT,
    VARIANTS_CREATE_OPERATION,
    VARIANTS_UPDATE_DOCUMENT,
    VARIANTS_UPDATE_OPERATION,
    ProductExportMutationGateway,
)
from shopify_connector_product_export.integration.shopify.product_media_mutation_gateway import (  # noqa: E402
    MEDIA_ASSOCIATE_OPERATION,
    MEDIA_ASSOCIATE_DOCUMENT,
    MEDIA_FILE_CREATE_OPERATION,
    MEDIA_FILE_CREATE_DOCUMENT,
    MEDIA_STAGE_DOCUMENT,
    MEDIA_STAGE_OPERATION,
    PRODUCT_MEDIA_MUTATION_REGISTRY,
    ProductMediaMutationGateway,
)
from shopify_connector_webhook.integration.shopify.webhook_subscription_mutation_gateway import (  # noqa: E402
    WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT,
    WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT,
    WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
    WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
    WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
    WebhookSubscriptionMutationGateway,
)


ITEM = "gid://shopify/InventoryItem/1"
LOCATION = "gid://shopify/Location/2"
SCOPE = InventoryPairScope(1, ITEM, LOCATION)
PRODUCT = "gid://shopify/Product/3"
VARIANT = "gid://shopify/ProductVariant/4"
FULFILLMENT = "gid://shopify/Fulfillment/5"
FILE = "gid://shopify/File/6"
SUBSCRIPTION = "gid://shopify/WebhookSubscription/7"


class Delegate:
    """One-call fake delegate; response may be an exception or callable."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def execute(self, operation, variables):
        self.calls.append((operation, variables))
        if isinstance(self.response, BaseException):
            raise self.response
        if callable(self.response):
            return self.response(operation, variables)
        return self.response


def _response(data, *, errors=None):
    result = {"data": data}
    if errors is not None:
        result["errors"] = errors
    return result


def _user_error(code="INVALID", field=("input",)):
    return {"code": code, "field": list(field), "message": "fixture rejection; never persisted"}


def _activate_response(level=0):
    return _response({
        "inventoryActivate": {
            "inventoryLevel": {
                "id": "gid://shopify/InventoryLevel/8",
                "item": {"id": ITEM},
                "location": {"id": LOCATION},
                "quantities": [{"name": "available", "quantity": level}],
            },
            "userErrors": [],
        }
    })


def _set_quantity_response(quantity=9):
    return _response({
        "inventorySetQuantities": {
            "inventoryAdjustmentGroup": {
                "reason": "correction",
                "referenceDocumentUri": "odoo://inventory/1",
                "changes": [{"name": "available", "delta": 1, "quantityAfterChange": quantity}],
            },
            "userErrors": [],
        }
    })


def _product_response(product=PRODUCT, variant=VARIANT):
    return _response({
        "productSet": {
            "product": {
                "id": product,
                "handle": "fixture-product",
                "title": "Fixture product",
                "status": "ACTIVE",
                "updatedAt": "2026-08-30T12:00:00Z",
                "descriptionHtml": "<p>Fixture</p>",
                "vendor": "Odoo",
                "productType": "Connector",
                "tags": ["odoo"],
                "variants": {"nodes": [{"id": variant, "sku": "SKU-1", "barcode": "123", "price": "9.00", "compareAtPrice": None, "inventoryItem": {"id": "gid://shopify/InventoryItem/11", "sku": "SKU-1", "tracked": True}, "selectedOptions": [{"name": "Title", "value": "Default Title"}]}]},
            },
            "userErrors": [],
        }
    })


class RegistryContractTests(unittest.TestCase):
    def test_every_mutation_has_registered_readback_and_one_call_budget(self):
        for registry in (
            INVENTORY_MUTATION_REGISTRY,
            FULFILLMENT_MUTATION_REGISTRY,
            WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
            PRODUCT_EXPORT_MUTATION_REGISTRY,
            PRODUCT_MEDIA_MUTATION_REGISTRY,
        ):
            for spec in registry.values():
                if spec.operation_type != "mutation":
                    continue
                self.assertTrue(spec.side_effect.remote)
                self.assertTrue(spec.readback.required)
                readback = registry.require_operation(spec.readback.operation_key)
                self.assertEqual(readback.operation_type, "query")
                self.assertEqual(spec.cost_expectation["request_count"], 1)
                self.assertIn("timeout_before_send", spec.fixture_keys)
                self.assertIn("timeout_after_send", spec.fixture_keys)

    def test_reviewed_documents_are_registered_with_exact_names(self):
        self.assertEqual(INVENTORY_MUTATION_REGISTRY.require_operation(INVENTORY_ACTIVATE_OPERATION).document, INVENTORY_ACTIVATE_DOCUMENT)
        self.assertEqual(FULFILLMENT_MUTATION_REGISTRY.require_operation(FULFILLMENT_CREATE_OPERATION).document, FULFILLMENT_CREATE_DOCUMENT)
        self.assertEqual(PRODUCT_EXPORT_MUTATION_REGISTRY.require_operation(PRODUCT_CREATE_OPERATION).document, PRODUCT_CREATE_DOCUMENT)
        self.assertEqual(PRODUCT_MEDIA_MUTATION_REGISTRY.require_operation(MEDIA_STAGE_OPERATION).document, MEDIA_STAGE_DOCUMENT)

    def test_legacy_runtime_uses_each_canonical_mutation_document(self):
        cases = (
            (INVENTORY_MUTATION_REGISTRY, INVENTORY_ACTIVATE_OPERATION, "InventoryActivate", "addons/shopify_connector_inventory/models/shopify_connector_inventory_service.py", INVENTORY_ACTIVATE_DOCUMENT, "INVENTORY_ACTIVATE_DOCUMENT"),
            (INVENTORY_MUTATION_REGISTRY, INVENTORY_SET_QUANTITIES_OPERATION, "InventorySetQuantities", "addons/shopify_connector_inventory/models/shopify_connector_inventory_service.py", INVENTORY_SET_QUANTITIES_DOCUMENT, "INVENTORY_SET_QUANTITIES_DOCUMENT"),
            (FULFILLMENT_MUTATION_REGISTRY, FULFILLMENT_CREATE_OPERATION, "ConnectorFulfillmentCreate", "addons/shopify_connector_fulfillment/models/shopify_connector_fulfillment_create_strategy.py", FULFILLMENT_CREATE_DOCUMENT, "FULFILLMENT_CREATE_DOCUMENT"),
            (FULFILLMENT_MUTATION_REGISTRY, FULFILLMENT_TRACKING_UPDATE_OPERATION, "ConnectorFulfillmentTrackingInfoUpdate", "addons/shopify_connector_fulfillment/models/shopify_connector_fulfillment_tracking_strategy.py", FULFILLMENT_TRACKING_UPDATE_DOCUMENT, "FULFILLMENT_TRACKING_UPDATE_DOCUMENT"),
            (WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY, WEBHOOK_SUBSCRIPTION_CREATE_OPERATION, "ConnectorWebhookSubscriptionCreate", "addons/shopify_connector_webhook/models/shopify_connector_webhook_subscription.py", WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT, "WEBHOOK_SUBSCRIPTION_CREATE_DOCUMENT"),
            (WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY, WEBHOOK_SUBSCRIPTION_DELETE_OPERATION, "ConnectorWebhookSubscriptionDelete", "addons/shopify_connector_webhook/models/shopify_connector_webhook_subscription.py", WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT, "WEBHOOK_SUBSCRIPTION_DELETE_DOCUMENT"),
            (PRODUCT_EXPORT_MUTATION_REGISTRY, BINDING_NAMESPACE_OPERATION, "ProductExportBindingNamespace", "addons/shopify_connector_product_export/models/shopify_connector_product_export_service.py", PRODUCT_EXPORT_MUTATION_REGISTRY.require_operation(BINDING_NAMESPACE_OPERATION).document, "BINDING_NAMESPACE_DOCUMENT"),
            (PRODUCT_EXPORT_MUTATION_REGISTRY, PRODUCT_CREATE_OPERATION, "ProductExportCreate", "addons/shopify_connector_product_export/models/shopify_connector_product_export_service.py", PRODUCT_CREATE_DOCUMENT, "PRODUCT_CREATE_DOCUMENT"),
            (PRODUCT_EXPORT_MUTATION_REGISTRY, "product_export.update", "ProductExportUpdate", "addons/shopify_connector_product_export/models/shopify_connector_product_export_service.py", PRODUCT_UPDATE_DOCUMENT, "PRODUCT_UPDATE_DOCUMENT"),
            (PRODUCT_EXPORT_MUTATION_REGISTRY, VARIANTS_UPDATE_OPERATION, "ProductExportVariantsUpdate", "addons/shopify_connector_product_export/models/shopify_connector_product_export_service.py", VARIANTS_UPDATE_DOCUMENT, "VARIANTS_UPDATE_DOCUMENT"),
            (PRODUCT_EXPORT_MUTATION_REGISTRY, VARIANTS_CREATE_OPERATION, "ProductExportVariantsCreate", "addons/shopify_connector_product_export/models/shopify_connector_product_export_service.py", VARIANTS_CREATE_DOCUMENT, "VARIANTS_CREATE_DOCUMENT"),
            (PRODUCT_MEDIA_MUTATION_REGISTRY, MEDIA_STAGE_OPERATION, "ProductExportMediaStage", "addons/shopify_connector_product_export/models/shopify_connector_media_export_service.py", MEDIA_STAGE_DOCUMENT, "MEDIA_STAGE_DOCUMENT"),
            (PRODUCT_MEDIA_MUTATION_REGISTRY, MEDIA_FILE_CREATE_OPERATION, "ProductExportMediaFileCreate", "addons/shopify_connector_product_export/models/shopify_connector_media_export_service.py", MEDIA_FILE_CREATE_DOCUMENT, "MEDIA_FILE_CREATE_DOCUMENT"),
            (PRODUCT_MEDIA_MUTATION_REGISTRY, MEDIA_ASSOCIATE_OPERATION, "ProductExportMediaAssociate", "addons/shopify_connector_product_export/models/shopify_connector_media_export_service.py", MEDIA_ASSOCIATE_DOCUMENT, "MEDIA_ASSOCIATE_DOCUMENT"),
        )
        for registry, operation_key, operation_name, source, expected, symbol in cases:
            legacy_source = (ROOT / source).read_text(encoding="utf-8")
            self.assertNotIn("mutation " + operation_name, legacy_source)
            self.assertGreaterEqual(legacy_source.count(symbol), 2, symbol)
            spec = registry.require_operation(operation_key)
            self.assertEqual(spec.operation_name, operation_name)
            self.assertEqual(spec.document, expected)


class MutationGatewayFaultTests(unittest.TestCase):
    def _activate_request(self):
        return InventoryMutationGateway(Delegate(None), INVENTORY_MUTATION_REGISTRY, expected_store_id=1).build_activate(
            ITEM, LOCATION, idempotency_key="intent-1", operation_scope_key=SCOPE
        )

    def test_success_is_normalized_immutable_and_delegate_is_called_once(self):
        delegate = Delegate(_activate_response())
        gateway = InventoryMutationGateway(delegate, INVENTORY_MUTATION_REGISTRY, expected_store_id=1)
        request = gateway.build_activate(ITEM, LOCATION, idempotency_key="intent-1", operation_scope_key=SCOPE)
        result = gateway.execute(request)
        self.assertEqual(result.outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(delegate.calls), 1)
        self.assertEqual(delegate.calls[0][1]["idempotencyKey"], "intent-1")
        self.assertEqual(request.readback.operation_key, "inventory.pair.read")
        self.assertEqual(len(request.intent.fingerprint), 64)
        with self.assertRaises(TypeError):
            request.variables["available"] = 2
        with self.assertRaises(TypeError):
            result.payload["available"] = 2

    def test_user_errors_are_clean_and_remote_message_is_not_returned(self):
        response = _response({"inventoryActivate": {"inventoryLevel": None, "userErrors": [_user_error()]}})
        delegate = Delegate(response)
        request = InventoryMutationGateway(delegate, INVENTORY_MUTATION_REGISTRY, expected_store_id=1).build_activate(ITEM, LOCATION, idempotency_key="intent-2", operation_scope_key=SCOPE)
        result = InventoryMutationGateway(delegate, INVENTORY_MUTATION_REGISTRY, expected_store_id=1).execute(request)
        self.assertEqual(result.outcome, MutationOutcome.FAILED_CLEAN.value)
        self.assertEqual(result.user_errors[0].code, "INVALID")
        self.assertNotIn("fixture rejection", str(result.as_dict()))
        self.assertEqual(len(delegate.calls), 1)

    def test_top_level_error_timeout_before_after_and_malformed_are_fail_closed(self):
        for response, expected, code in (
            (_response({}, errors=[{"extensions": {"code": "INTERNAL"}}]), MutationOutcome.UNCERTAIN.value, "top_level_graphql_error"),
            (TimeoutError("network"), MutationOutcome.UNCERTAIN.value, "shopify_temporary_server_network"),
            (MutationTransportError(after_send=False), MutationOutcome.FAILED_CLEAN.value, "transport_not_sent"),
            (MutationTransportError(after_send=True), MutationOutcome.UNCERTAIN.value, "shopify_temporary_server_network"),
            (_response({"inventoryActivate": {"userErrors": []}}), MutationOutcome.UNCERTAIN.value, "missing_success_payload"),
            (RuntimeError("secret transport detail"), MutationOutcome.UNCERTAIN.value, "shopify_temporary_server_network"),
        ):
            delegate = Delegate(response)
            gateway = InventoryMutationGateway(delegate, INVENTORY_MUTATION_REGISTRY, expected_store_id=1)
            result = gateway.execute(gateway.build_activate(ITEM, LOCATION, idempotency_key="fault-key", operation_scope_key=SCOPE))
            self.assertEqual(result.outcome, expected)
            self.assertEqual(result.error_code, code)
            self.assertNotIn("secret transport detail", str(result.as_dict()))
            self.assertEqual(len(delegate.calls), 1)

    def test_counterfeit_same_document_spec_cannot_cross_the_registry_boundary(self):
        delegate = Delegate(_activate_response())
        gateway = InventoryMutationGateway(delegate, INVENTORY_MUTATION_REGISTRY, expected_store_id=1)
        request = gateway.build_activate(ITEM, LOCATION, idempotency_key="counterfeit", operation_scope_key=SCOPE)
        counterfeit = replace(request.operation, result="CounterfeitResultType")
        counterfeit_request = replace(request, operation=counterfeit)
        with self.assertRaises(MutationGatewayError):
            gateway.execute(counterfeit_request)
        self.assertEqual(delegate.calls, [])

    def test_input_validation_makes_no_delegate_call_and_rejects_noncanonical_gids(self):
        delegate = Delegate(None)
        gateway = InventoryMutationGateway(delegate, INVENTORY_MUTATION_REGISTRY, expected_store_id=1)
        with self.assertRaises(ValueError):
            gateway.build_activate("InventoryItem/1", LOCATION, idempotency_key="bad")
        with self.assertRaises(ValueError):
            gateway.build_set_quantities(ITEM, LOCATION, True, 0, reference_document_uri="odoo://x", idempotency_key="bad", operation_scope_key=SCOPE)
        self.assertEqual(delegate.calls, [])

    def test_scope_must_be_an_exact_validated_pair_object(self):
        gateway = InventoryMutationGateway(Delegate(None), INVENTORY_MUTATION_REGISTRY, expected_store_id=1)
        with self.assertRaises(MutationGatewayError):
            gateway.build_activate(ITEM, LOCATION, idempotency_key="arbitrary", operation_scope_key="inventory_pair:1:foreign")
        with self.assertRaises(MutationGatewayError):
            gateway.build_activate(ITEM, LOCATION, idempotency_key="missing")
        with self.assertRaises(MutationGatewayError):
            gateway.build_activate(
                ITEM,
                LOCATION,
                idempotency_key="wrong-pair",
                operation_scope_key=InventoryPairScope(1, ITEM, "gid://shopify/Location/3"),
            )
        with self.assertRaises(MutationGatewayError):
            gateway.build_activate(
                ITEM,
                LOCATION,
                idempotency_key="foreign-store",
                operation_scope_key=InventoryPairScope(2, ITEM, LOCATION),
            )
        with self.assertRaises(MutationGatewayError):
            gateway.build_activate(
                ITEM,
                LOCATION,
                idempotency_key="foreign-evidence",
                operation_scope_key=SCOPE,
                business_intent={
                    "mutation_domain": "inventory_activate",
                    "inventory_item_gid": ITEM,
                    "location_gid": "gid://shopify/Location/3",
                    "initial_available": 0,
                },
            )

    def test_supplied_intent_and_preconditions_must_equal_wire_contract(self):
        gateway = InventoryMutationGateway(Delegate(None), INVENTORY_MUTATION_REGISTRY, expected_store_id=1)
        baseline = gateway.build_set_quantities(
            ITEM,
            LOCATION,
            9,
            8,
            reference_document_uri="odoo://inventory/1",
            idempotency_key="intent-contract",
            operation_scope_key=SCOPE,
        )

        omitted = to_plain(baseline.intent.business_intent)
        omitted.pop("location_gid")
        with self.assertRaises(MutationGatewayError):
            gateway.build_set_quantities(
                ITEM,
                LOCATION,
                9,
                8,
                reference_document_uri="odoo://inventory/1",
                idempotency_key="intent-omission",
                operation_scope_key=SCOPE,
                business_intent=omitted,
            )

        contradictory = to_plain(baseline.intent.business_intent)
        contradictory["target_quantity"] = 10
        with self.assertRaises(MutationGatewayError):
            gateway.build_set_quantities(
                ITEM,
                LOCATION,
                9,
                8,
                reference_document_uri="odoo://inventory/1",
                idempotency_key="intent-contradiction",
                operation_scope_key=SCOPE,
                business_intent=contradictory,
            )

        contradictory_preconditions = to_plain(baseline.intent.preconditions_snapshot)
        contradictory_preconditions["change_from_quantity"] = 7
        with self.assertRaises(MutationGatewayError):
            gateway.build_set_quantities(
                ITEM,
                LOCATION,
                9,
                8,
                reference_document_uri="odoo://inventory/1",
                idempotency_key="precondition-contradiction",
                operation_scope_key=SCOPE,
                preconditions_snapshot=contradictory_preconditions,
            )


class DomainParityTests(unittest.TestCase):
    def test_inventory_set_quantities_preserves_v1_wire_shape(self):
        delegate = Delegate(_set_quantity_response())
        gateway = InventoryMutationGateway(delegate, INVENTORY_MUTATION_REGISTRY, expected_store_id=1)
        request = gateway.build_set_quantities(
            ITEM,
            LOCATION,
            9,
            8,
            reference_document_uri="odoo://inventory/1",
            idempotency_key="inv-set-1",
            operation_scope_key=SCOPE,
        )
        self.assertEqual(to_plain(request.variables), {
            "input": {
                "name": "available",
                "reason": "correction",
                "referenceDocumentUri": "odoo://inventory/1",
                "quantities": [{"inventoryItemId": ITEM, "locationId": LOCATION, "quantity": 9, "changeFromQuantity": 8}],
            },
            "idempotencyKey": "inv-set-1",
        })
        result = gateway.execute(request)
        self.assertEqual(result.outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(delegate.calls), 1)

    def test_fulfillment_tracking_and_product_create_use_one_delegate_call(self):
        fulfillment_response = _response({
            "fulfillmentTrackingInfoUpdate": {
                "fulfillment": {"id": FULFILLMENT, "status": "SUCCESS", "trackingInfo": [{"number": "T-1", "url": "https://carrier.test/T-1", "company": "Carrier"}]},
                "userErrors": [],
            }
        })
        fulfillment_delegate = Delegate(fulfillment_response)
        fulfillment_gateway = FulfillmentMutationGateway(fulfillment_delegate, FULFILLMENT_MUTATION_REGISTRY)
        fulfillment_request = fulfillment_gateway.build_tracking_update(
            FULFILLMENT, {"number": "T-1", "url": "https://carrier.test/T-1"}, False, idempotency_key="fulfill-1"
        )
        self.assertEqual(fulfillment_request.operation_key, FULFILLMENT_TRACKING_UPDATE_OPERATION)
        self.assertEqual(fulfillment_gateway.execute(fulfillment_request).outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(fulfillment_delegate.calls), 1)

        product_delegate = Delegate(_product_response())
        product_gateway = ProductExportMutationGateway(product_delegate, PRODUCT_EXPORT_MUTATION_REGISTRY)
        product_request = product_gateway.build_create(
            {"title": "Fixture", "tags": ["odoo"], "variants": [{"sku": "SKU-1"}]},
            42,
            idempotency_key="product-1",
        )
        self.assertEqual(product_request.operation_key, PRODUCT_CREATE_OPERATION)
        self.assertEqual(product_gateway.execute(product_request).outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(product_delegate.calls), 1)

    def test_webhook_create_delete_and_media_requests_are_redacted_in_results(self):
        webhook_response = _response({
            "webhookSubscriptionCreate": {
                "webhookSubscription": {
                    "id": SUBSCRIPTION,
                    "topic": "ORDERS_CREATE",
                    "uri": "https://connector.test/webhook?secret=fixture-secret",
                    "apiVersion": {"handle": "2026-07", "displayName": "July 2026", "supported": True},
                    "format": "JSON",
                    "includeFields": ["id"],
                },
                "userErrors": [],
            }
        })
        from shopify_connector_webhook.integration.shopify.webhook_subscription_mutation_gateway import (  # noqa: PLC0415
            WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
        )
        webhook_delegate = Delegate(webhook_response)
        webhook_gateway = WebhookSubscriptionMutationGateway(webhook_delegate, WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY)
        webhook_request = webhook_gateway.build_create("ORDERS_CREATE", "https://connector.test/webhook?secret=fixture-secret", idempotency_key="webhook-1")
        webhook_result = webhook_gateway.execute(webhook_request)
        self.assertEqual(webhook_request.operation_key, WEBHOOK_SUBSCRIPTION_CREATE_OPERATION)
        self.assertNotIn("fixture-secret", str(webhook_result.as_dict()))
        self.assertEqual(len(webhook_delegate.calls), 1)
        delete_delegate = Delegate(_response({"webhookSubscriptionDelete": {"deletedWebhookSubscriptionId": SUBSCRIPTION, "userErrors": []}}))
        delete_gateway = WebhookSubscriptionMutationGateway(delete_delegate, WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY)
        delete_request = delete_gateway.build_delete(SUBSCRIPTION, idempotency_key="webhook-2")
        self.assertEqual(delete_gateway.execute(delete_request).outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(delete_delegate.calls), 1)

        media_stage_delegate = Delegate(_response({
            "stagedUploadsCreate": {
                "stagedTargets": [{
                    "url": "https://uploads.test/signed?token=secret",
                    "resourceUrl": "https://cdn.test/resource/signed",
                    "parameters": [{"name": "key", "value": "private-value"}],
                }],
                "userErrors": [],
            }
        }))
        media_gateway = ProductMediaMutationGateway(media_stage_delegate, PRODUCT_MEDIA_MUTATION_REGISTRY)
        media_result = media_gateway.execute(media_gateway.build_stage("odoo-42-abcd.png", idempotency_key="media-1"))
        self.assertEqual(media_result.outcome, MutationOutcome.SUCCEEDED.value)
        self.assertNotIn("token=secret", str(media_result.as_dict()))
        self.assertNotIn("private-value", str(media_result.as_dict()))
        self.assertEqual(len(media_stage_delegate.calls), 1)

        media_file_delegate = Delegate(_response({"fileCreate": {"files": [{"id": FILE, "fileStatus": "PROCESSING", "alt": "Fixture"}], "userErrors": []}}))
        media_file_gateway = ProductMediaMutationGateway(media_file_delegate, PRODUCT_MEDIA_MUTATION_REGISTRY)
        media_file_request = media_file_gateway.build_file_create("https://cdn.test/resource/signed", "odoo-42-abcd.png", alt="Fixture", idempotency_key="media-2")
        self.assertEqual(media_file_gateway.execute(media_file_request).outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(media_file_delegate.calls), 1)

        media_assoc_delegate = Delegate(_response({"fileUpdate": {"files": [{"id": FILE, "fileStatus": "READY", "alt": "Fixture"}], "userErrors": []}}))
        media_assoc_gateway = ProductMediaMutationGateway(media_assoc_delegate, PRODUCT_MEDIA_MUTATION_REGISTRY)
        media_assoc_request = media_assoc_gateway.build_associate(FILE, PRODUCT, idempotency_key="media-3")
        self.assertEqual(media_assoc_gateway.execute(media_assoc_request).outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(media_assoc_delegate.calls), 1)

    def test_partial_success_with_user_errors_is_always_uncertain(self):
        cases = (
            (
                InventoryMutationGateway,
                INVENTORY_MUTATION_REGISTRY,
                lambda gateway: gateway.build_activate(ITEM, LOCATION, idempotency_key="partial-inventory", operation_scope_key=SCOPE),
                _response({"inventoryActivate": {"inventoryLevel": {"id": "gid://shopify/InventoryLevel/8"}, "userErrors": [_user_error()]}}),
            ),
            (
                FulfillmentMutationGateway,
                FULFILLMENT_MUTATION_REGISTRY,
                lambda gateway: gateway.build_tracking_update(FULFILLMENT, {"number": "T-1"}, False, idempotency_key="partial-fulfillment"),
                _response({"fulfillmentTrackingInfoUpdate": {"fulfillment": {"id": FULFILLMENT, "status": "SUCCESS"}, "userErrors": [{"field": ["trackingInfoInput"], "message": "rejected"}]}}),
            ),
            (
                WebhookSubscriptionMutationGateway,
                WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
                lambda gateway: gateway.build_create("ORDERS_CREATE", "https://connector.test/webhook", idempotency_key="partial-webhook"),
                _response({"webhookSubscriptionCreate": {"webhookSubscription": {"id": SUBSCRIPTION}, "userErrors": [{"field": ["topic"], "message": "rejected"}]}}),
            ),
            (
                ProductExportMutationGateway,
                PRODUCT_EXPORT_MUTATION_REGISTRY,
                lambda gateway: gateway.build_create({"title": "Fixture"}, 42, idempotency_key="partial-product"),
                _response({"productSet": {"product": {"id": PRODUCT}, "userErrors": [_user_error()]}}),
            ),
            (
                ProductMediaMutationGateway,
                PRODUCT_MEDIA_MUTATION_REGISTRY,
                lambda gateway: gateway.build_stage("fixture.png", idempotency_key="partial-media"),
                _response({"stagedUploadsCreate": {"stagedTargets": [{"url": "https://upload.test/a", "resourceUrl": "https://upload.test/b"}], "userErrors": [{"field": ["input"], "message": "rejected"}]}}),
            ),
        )
        for gateway_type, registry, build, response in cases:
            delegate = Delegate(response)
            gateway = (
                gateway_type(delegate, registry, expected_store_id=1)
                if gateway_type is InventoryMutationGateway
                else gateway_type(delegate, registry)
            )
            result = gateway.execute(build(gateway))
            self.assertEqual(result.outcome, MutationOutcome.UNCERTAIN.value, gateway_type.__name__)
            self.assertEqual(result.error_code, "ambiguous_user_errors", gateway_type.__name__)
            self.assertEqual(len(delegate.calls), 1)


class StructuralPurityTests(unittest.TestCase):
    def test_new_gateway_modules_have_no_transport_orm_or_secret_access(self):
        paths = (
            ROOT / "addons/shopify_connector_core/integration/shopify/mutation_contracts.py",
            ROOT / "addons/shopify_connector_inventory/integration/shopify/inventory_mutation_gateway.py",
            ROOT / "addons/shopify_connector_fulfillment/integration/shopify/fulfillment_mutation_gateway.py",
            ROOT / "addons/shopify_connector_webhook/integration/shopify/webhook_subscription_mutation_gateway.py",
            ROOT / "addons/shopify_connector_product_export/integration/shopify/product_export_mutation_gateway.py",
            ROOT / "addons/shopify_connector_product_export/integration/shopify/product_media_mutation_gateway.py",
        )
        forbidden_imports = {"odoo", "requests", "httpx", "urllib3", "psycopg2"}
        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imports.update(alias.name.split(".", 1)[0] for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imports.add(node.module.split(".", 1)[0])
            self.assertTrue(forbidden_imports.isdisjoint(imports), path.name)
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("access_token", text, path.name)
            self.assertNotIn("execute_business", text, path.name)


if __name__ == "__main__":
    unittest.main()
