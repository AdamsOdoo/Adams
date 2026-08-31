"""P08 inventory mutation gateway, kept unwired behind the V1 runtime.

The two operation documents and their request/result shapes are copied from
the accepted V1 inventory strategy.  This module is intentionally a pure
adapter: a caller supplies durable intent/precondition evidence and one
already-authorized delegate.  It performs no Odoo work, credential lookup,
retry, reconciliation read or HTTP request.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odoo.addons.shopify_connector_core.domain.immutability import to_plain
from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
    DurableIntentDescriptor,
    MutationGateway,
    MutationGatewayError,
    MutationOutcome,
    MutationRequest,
    MutationResult,
    MutationShapeError,
    ReadbackPlanDescriptor,
    freeze_json,
    parse_user_errors,
    require_gid,
    require_integer,
    require_text,
    response_data,
)
from odoo.addons.shopify_connector_core.integration.shopify.operation_registry import (
    ReadbackMetadata,
    ShopifyOperationRegistry,
    ShopifyOperationSpec,
    SideEffectMetadata,
)

from .inventory_documents import INVENTORY_PAIR_QUERY
from ...domain.inventory_mutation import InventoryPairScope


SHOPIFY_API_VERSION = "2026-07"
INVENTORY_ACTIVATE_OPERATION = "inventory.activate"
INVENTORY_SET_QUANTITIES_OPERATION = "inventory.set_quantities"
INVENTORY_PAIR_READ_OPERATION = "inventory.pair.read"

INVENTORY_ACTIVATE_DOCUMENT = (
    "mutation InventoryActivate($inventoryItemId: ID!, "
    "$locationId: ID!, $available: Int!, "
    "$idempotencyKey: String!) { "
    "inventoryActivate(inventoryItemId: $inventoryItemId, "
    "locationId: $locationId, available: $available, "
    "stockAtLegacyLocation: false) "
    "@idempotent(key: $idempotencyKey) { "
    "inventoryLevel { id item { id } location { id } "
    "quantities(names: [\"available\"]) { name quantity } } "
    "userErrors { field message } } }"
)
INVENTORY_SET_QUANTITIES_DOCUMENT = (
    "mutation InventorySetQuantities($input: "
    "InventorySetQuantitiesInput!, $idempotencyKey: String!) { "
    "inventorySetQuantities(input: $input) "
    "@idempotent(key: $idempotencyKey) { "
    "inventoryAdjustmentGroup { reason referenceDocumentUri "
    "changes { name delta quantityAfterChange } } "
    "userErrors { code field message } } }"
)


def _query_spec() -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        INVENTORY_PAIR_READ_OPERATION,
        "InventoryPairRead",
        "query",
        SHOPIFY_API_VERSION,
        INVENTORY_PAIR_QUERY,
        {"itemId": "ID!", "locationId": "ID!"},
        "InventoryPairDTO",
        "GraphQLError",
        SideEffectMetadata("observe", "Reads one inventory item/location pair for mutation verification.", False),
        fixture_keys=("inventory_pair_applied", "inventory_pair_not_applied", "inventory_pair_inconclusive"),
    )


def _mutation_spec(
    key: str,
    name: str,
    document: str,
    variables: Mapping[str, Any],
    side_effect: SideEffectMetadata,
) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        key,
        name,
        "mutation",
        SHOPIFY_API_VERSION,
        document,
        variables,
        "InventoryMutationResult",
        "GraphQLError",
        side_effect,
        ReadbackMetadata(
            True,
            INVENTORY_PAIR_READ_OPERATION,
            "read the exact inventory item/location pair after a possible send",
            "The pair read proves the requested quantity or confirms that no level was applied; it never resends the mutation.",
        ),
        cost_expectation={"mode": "observed", "request_count": 1},
        fixture_keys=("success", "user_errors", "top_level_error", "timeout_before_send", "timeout_after_send", "malformed_result"),
    )


INVENTORY_MUTATION_REGISTRY = ShopifyOperationRegistry(
    (
        _query_spec(),
        _mutation_spec(
            INVENTORY_ACTIVATE_OPERATION,
            "InventoryActivate",
            INVENTORY_ACTIVATE_DOCUMENT,
            {"inventoryItemId": "ID!", "locationId": "ID!", "available": "Int!", "idempotencyKey": "String!"},
            SideEffectMetadata("create", "Activates one Shopify inventory item at one location with an accepted zero baseline.", True),
        ),
        _mutation_spec(
            INVENTORY_SET_QUANTITIES_OPERATION,
            "InventorySetQuantities",
            INVENTORY_SET_QUANTITIES_DOCUMENT,
            {"input": "InventorySetQuantitiesInput!", "idempotencyKey": "String!"},
            SideEffectMetadata("update", "Sets one Shopify inventory item/location available quantity using the V1 CAS input.", True),
        ),
    )
)
INVENTORY_MUTATION_REGISTRY.freeze()


def _intent(
    operation_key: str,
    scope: InventoryPairScope | None,
    business_intent: Mapping[str, Any] | None,
    preconditions: Mapping[str, Any] | None,
    idempotency_key: str,
    defaults: Mapping[str, Any],
    *,
    expected_store_id: int,
    contract_context: Mapping[str, Any] | None = None,
) -> DurableIntentDescriptor:
    if not isinstance(scope, InventoryPairScope):
        raise MutationGatewayError(
            "invalid_operation_scope",
            "A validated store-bound InventoryPairScope is required; arbitrary scope strings are rejected.",
        )
    if (
        scope.store_id != expected_store_id
        or
        scope.inventory_item_gid != defaults["inventory_item_gid"]
        or scope.location_gid != defaults["location_gid"]
    ):
        raise MutationGatewayError(
            "invalid_operation_scope",
            "Operation scope must prove the exact expected store and item/location pair.",
        )
    context = dict(contract_context or {})
    allowed_context = {
        "company_id",
        "expected_generation",
        "current_generation",
        "expected_store_identity",
        "current_store_identity",
        "snapshot_taken_at",
    }
    if set(context) - allowed_context:
        raise MutationGatewayError(
            "invalid_intent",
            "contract_context contains fields outside the inventory contract.",
        )
    company_id = context.get("company_id")
    if company_id is not None:
        require_integer(company_id, "company_id", minimum=1)
    for field_name in ("expected_generation", "current_generation"):
        value = context.get(field_name)
        if value is not None:
            require_integer(value, field_name, minimum=0)
    for field_name in ("expected_store_identity", "current_store_identity", "snapshot_taken_at"):
        value = context.get(field_name)
        if value is not None:
            require_text(value, field_name, max_length=2048)

    # The gateway owns the canonical evidence shape.  A caller may omit the
    # maps and let this layer materialize them, but once supplied they must be
    # an exact equality match: no missing, extra or contradictory operation,
    # store, generation, pair, target or CAS fields can enter the durable
    # intent descriptor.
    canonical = {
        "operation": defaults["mutation_domain"],
        "operation_key": operation_key,
        "mutation_domain": defaults["mutation_domain"],
        "store_id": expected_store_id,
        "company_id": company_id,
        "expected_generation": context.get("expected_generation"),
        "current_generation": context.get("current_generation"),
        "expected_store_identity": context.get("expected_store_identity"),
        "current_store_identity": context.get("current_store_identity"),
        "inventory_item_gid": defaults["inventory_item_gid"],
        "location_gid": defaults["location_gid"],
    }
    if defaults["mutation_domain"] == "inventory_activate":
        canonical.update({
            "target_quantity": 0,
            "change_from_quantity": None,
            "initial_available": 0,
        })
    else:
        canonical.update({
            "target_quantity": defaults["target_quantity"],
            "change_from_quantity": defaults["change_from_quantity"],
        })
    preconditions_canonical = {
        **canonical,
        "snapshot_taken_at": context.get("snapshot_taken_at"),
    }

    def exact_evidence(
        evidence_name: str,
        evidence: Mapping[str, Any] | None,
        expected: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        if evidence is None:
            return expected
        if not isinstance(evidence, Mapping):
            raise MutationGatewayError(
                "invalid_intent",
                f"{evidence_name} must be an object with the canonical inventory fields.",
            )
        try:
            normalized = to_plain(freeze_json(dict(evidence), evidence_name))
        except MutationGatewayError as exc:
            raise MutationGatewayError(
                "invalid_intent",
                f"{evidence_name} is not valid bounded JSON evidence.",
            ) from exc
        if normalized != dict(expected):
            raise MutationGatewayError(
                "invalid_intent",
                f"{evidence_name} must exactly match the wire operation, store, generations, pair and quantity CAS.",
            )
        return expected

    business = exact_evidence("business_intent", business_intent, canonical)
    precondition = exact_evidence("preconditions_snapshot", preconditions, preconditions_canonical)
    return DurableIntentDescriptor(
        operation_key,
        scope.operation_scope_key,
        business,
        precondition,
        idempotency_key,
    )


def _request(
    operation: ShopifyOperationSpec,
    variables: Mapping[str, Any],
    intent: DurableIntentDescriptor,
    target: Mapping[str, Any],
) -> MutationRequest:
    return MutationRequest(
        operation,
        variables,
        intent,
        ReadbackPlanDescriptor.from_metadata(operation.readback, target),
    )


def _safe_evidence(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Keep response evidence to JSON-shaped, bounded non-secret facts."""

    return to_plain(freeze_json(dict(value), "evidence"))


class InventoryMutationGateway(MutationGateway):
    """Build and classify the exact V1 inventory mutations."""

    def __init__(
        self,
        delegate: Any,
        registry: ShopifyOperationRegistry,
        *,
        expected_store_id: int,
    ) -> None:
        super().__init__(delegate, registry)
        self.expected_store_id = require_integer(expected_store_id, "expected_store_id", minimum=1)

    def build_activate(
        self,
        inventory_item_gid: str,
        location_gid: str,
        *,
        idempotency_key: str,
        operation_scope_key: InventoryPairScope | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
        contract_context: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        item_gid = require_gid(inventory_item_gid, "InventoryItem", "inventory_item_gid")
        loc_gid = require_gid(location_gid, "Location", "location_gid")
        require_text(idempotency_key, "idempotency_key", max_length=512)
        defaults = {
            "mutation_domain": "inventory_activate",
            "inventory_item_gid": item_gid,
            "location_gid": loc_gid,
            "initial_available": 0,
        }
        intent = _intent(
            INVENTORY_ACTIVATE_OPERATION,
            operation_scope_key,
            business_intent,
            preconditions_snapshot,
            idempotency_key,
            defaults,
            expected_store_id=self.expected_store_id,
            contract_context=contract_context,
        )
        variables = {
            "inventoryItemId": item_gid,
            "locationId": loc_gid,
            "available": 0,
            "idempotencyKey": idempotency_key,
        }
        return _request(
            self.registry.require_operation(INVENTORY_ACTIVATE_OPERATION),
            variables,
            intent,
            {"inventory_item_gid": item_gid, "location_gid": loc_gid},
        )

    def build_set_quantities(
        self,
        inventory_item_gid: str,
        location_gid: str,
        quantity: int,
        change_from_quantity: int,
        *,
        reference_document_uri: str,
        idempotency_key: str,
        operation_scope_key: InventoryPairScope | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
        contract_context: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        item_gid = require_gid(inventory_item_gid, "InventoryItem", "inventory_item_gid")
        loc_gid = require_gid(location_gid, "Location", "location_gid")
        target = require_integer(quantity, "quantity", minimum=0)
        observed = require_integer(change_from_quantity, "change_from_quantity")
        require_text(reference_document_uri, "reference_document_uri", max_length=2048)
        require_text(idempotency_key, "idempotency_key", max_length=512)
        defaults = {
            "mutation_domain": "inventory_set_quantities",
            "inventory_item_gid": item_gid,
            "location_gid": loc_gid,
            "target_quantity": target,
            "change_from_quantity": observed,
        }
        intent = _intent(
            INVENTORY_SET_QUANTITIES_OPERATION,
            operation_scope_key,
            business_intent,
            preconditions_snapshot,
            idempotency_key,
            defaults,
            expected_store_id=self.expected_store_id,
            contract_context=contract_context,
        )
        variables = {
            "input": {
                "name": "available",
                "reason": "correction",
                "referenceDocumentUri": reference_document_uri,
                "quantities": [{
                    "inventoryItemId": item_gid,
                    "locationId": loc_gid,
                    "quantity": target,
                    "changeFromQuantity": observed,
                }],
            },
            "idempotencyKey": idempotency_key,
        }
        return _request(
            self.registry.require_operation(INVENTORY_SET_QUANTITIES_OPERATION),
            variables,
            intent,
            {"inventory_item_gid": item_gid, "location_gid": loc_gid, "target_quantity": target},
        )

    def _normalize_response(self, request: MutationRequest, response: Mapping[str, Any]) -> MutationResult:
        data = response_data(response)
        if request.operation_key == INVENTORY_ACTIVATE_OPERATION:
            payload = data.get("inventoryActivate")
            if not isinstance(payload, Mapping):
                raise MutationShapeError("missing_payload", "inventoryActivate payload is missing.")
            errors = parse_user_errors(payload.get("userErrors"))
            level = payload.get("inventoryLevel")
            if errors:
                if level is not None:
                    return self._result(request, MutationOutcome.UNCERTAIN, "ambiguous_user_errors", "Shopify returned errors alongside an inventory level; verification is required.", user_errors=errors)
                return self._result(request, MutationOutcome.FAILED_CLEAN, "shopify_user_errors_validation", "Shopify rejected inventory activation.", user_errors=errors)
            if not isinstance(level, Mapping):
                raise MutationShapeError("missing_success_payload", "inventoryActivate returned no inventory level.")
            normalized = self._activate_level(level, request)
            return self._result(request, MutationOutcome.SUCCEEDED, None, "Shopify accepted inventory activation; verification remains required.", payload=normalized)
        if request.operation_key == INVENTORY_SET_QUANTITIES_OPERATION:
            payload = data.get("inventorySetQuantities")
            if not isinstance(payload, Mapping):
                raise MutationShapeError("missing_payload", "inventorySetQuantities payload is missing.")
            errors = parse_user_errors(payload.get("userErrors"))
            group = payload.get("inventoryAdjustmentGroup")
            if errors:
                if group is not None:
                    return self._result(request, MutationOutcome.UNCERTAIN, "ambiguous_user_errors", "Shopify returned errors alongside an inventory adjustment; verification is required.", user_errors=errors)
                code = "concurrency_race_conflict" if any(item.code == "CHANGE_FROM_QUANTITY_STALE" for item in errors) else "shopify_user_errors_validation"
                return self._result(request, MutationOutcome.FAILED_CLEAN, code, "Shopify rejected the inventory quantity change.", user_errors=errors)
            if not isinstance(group, Mapping):
                raise MutationShapeError("missing_success_payload", "inventorySetQuantities returned no adjustment group.")
            normalized = self._adjustment_group(group, request)
            return self._result(request, MutationOutcome.SUCCEEDED, None, "Shopify accepted the inventory quantity change; verification remains required.", payload=normalized)
        raise MutationGatewayError("operation_not_supported", "Inventory mutation operation is not supported by this gateway.")

    def _activate_level(self, level: Mapping[str, Any], request: MutationRequest) -> Mapping[str, Any]:
        item_gid = request.variables["inventoryItemId"]
        location_gid = request.variables["locationId"]
        level_gid = require_gid(level.get("id"), "InventoryLevel", "inventory_level_gid")
        item = level.get("item")
        location = level.get("location")
        if not isinstance(item, Mapping) or item.get("id") != item_gid or not isinstance(location, Mapping) or location.get("id") != location_gid:
            raise MutationShapeError("identity_mismatch", "inventoryActivate returned a different item or location identity.")
        quantities = level.get("quantities")
        if not isinstance(quantities, list) or len(quantities) != 1 or not isinstance(quantities[0], Mapping) or quantities[0].get("name") != "available":
            raise MutationShapeError("invalid_success_payload", "inventoryActivate did not return exactly one available quantity.")
        available = require_integer(quantities[0].get("quantity"), "inventoryLevel.available")
        if available != 0:
            raise MutationShapeError("invalid_success_payload", "inventoryActivate did not prove the accepted zero baseline.")
        return {"inventory_level_gid": level_gid, "inventory_item_gid": item_gid, "location_gid": location_gid, "available": available}

    def _adjustment_group(self, group: Mapping[str, Any], request: MutationRequest) -> Mapping[str, Any]:
        reason = group.get("reason")
        reference = group.get("referenceDocumentUri")
        expected_reference = request.variables["input"]["referenceDocumentUri"]
        if not isinstance(reason, str) or reason != "correction" or not isinstance(reference, str) or reference != expected_reference:
            raise MutationShapeError("invalid_success_payload", "inventorySetQuantities returned mismatched adjustment metadata.")
        changes = group.get("changes")
        if not isinstance(changes, list) or len(changes) != 1 or not isinstance(changes[0], Mapping) or changes[0].get("name") != "available":
            raise MutationShapeError("invalid_success_payload", "inventorySetQuantities did not return exactly one available change.")
        change = changes[0]
        quantity_after = require_integer(change.get("quantityAfterChange"), "quantityAfterChange")
        expected = request.variables["input"]["quantities"][0]["quantity"]
        if quantity_after != expected:
            raise MutationShapeError("invalid_success_payload", "inventorySetQuantities returned a different quantity than requested.")
        normalized_change = {"name": "available", "quantity_after_change": quantity_after}
        if "delta" in change:
            normalized_change["delta"] = require_integer(change.get("delta"), "delta")
        return {"reason": reason, "reference_document_uri": reference, "changes": [normalized_change]}


__all__ = [
    "INVENTORY_ACTIVATE_DOCUMENT",
    "INVENTORY_ACTIVATE_OPERATION",
    "INVENTORY_MUTATION_REGISTRY",
    "INVENTORY_PAIR_QUERY",
    "INVENTORY_PAIR_READ_OPERATION",
    "INVENTORY_SET_QUANTITIES_DOCUMENT",
    "INVENTORY_SET_QUANTITIES_OPERATION",
    "InventoryMutationGateway",
]
