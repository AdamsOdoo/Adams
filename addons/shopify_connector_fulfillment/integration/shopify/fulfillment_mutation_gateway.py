"""P08 fulfillment mutation gateway behind the accepted V1 runtime.

The create and tracking-update documents, variable names and positive-result
rules mirror the current FulfillmentOrder strategy.  This adapter does not
select fulfillment orders, read Odoo pickings, retrieve credentials, perform
HTTP, retry or read Shopify after a possible send.  Those responsibilities
remain in the legacy admission/runtime until a later vertical-slice cutover.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
    DurableIntentDescriptor,
    MutationGateway,
    MutationGatewayError,
    MutationOutcome,
    MutationRequest,
    MutationShapeError,
    ReadbackPlanDescriptor,
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

from .fulfillment_documents import (
    FULFILLMENT_NODE_QUERY,
    ORDER_FULFILLMENTS_QUERY as FULFILLMENT_ORDER_FULFILLMENTS_QUERY,
)


SHOPIFY_API_VERSION = "2026-07"
FULFILLMENT_CREATE_OPERATION = "fulfillment.create"
FULFILLMENT_TRACKING_UPDATE_OPERATION = "fulfillment.tracking_update"
FULFILLMENT_ORDER_FULFILLMENTS_READ_OPERATION = "fulfillment.order_fulfillments.read"
FULFILLMENT_NODE_READ_OPERATION = "fulfillment.node.read"
MAX_TRACKING_ITEMS = 50

FULFILLMENT_CREATE_DOCUMENT = (
    "mutation ConnectorFulfillmentCreate($fulfillment: FulfillmentInput!) { "
    "fulfillmentCreate(fulfillment: $fulfillment) { "
    "fulfillment { id status trackingInfo { number url company } } "
    "userErrors { field message } } }"
)
FULFILLMENT_TRACKING_UPDATE_DOCUMENT = (
    "mutation ConnectorFulfillmentTrackingInfoUpdate($fulfillmentId: ID!, "
    "$trackingInfoInput: FulfillmentTrackingInput!, $notifyCustomer: Boolean) { "
    "fulfillmentTrackingInfoUpdate(fulfillmentId: $fulfillmentId, "
    "trackingInfoInput: $trackingInfoInput, notifyCustomer: $notifyCustomer) { "
    "fulfillment { id status trackingInfo { number url company } } "
    "userErrors { field message } } }"
)
def _read_spec(key: str, name: str, document: str, variables: Mapping[str, Any], summary: str) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        key, name, "query", SHOPIFY_API_VERSION, document, variables,
        "FulfillmentReadResult", "GraphQLError",
        SideEffectMetadata("observe", summary, False),
        fixture_keys=("readback_applied", "readback_not_applied", "readback_inconclusive"),
    )


def _mutation_spec(key: str, name: str, document: str, variables: Mapping[str, Any], side_effect: SideEffectMetadata, read_key: str, strategy: str, summary: str) -> ShopifyOperationSpec:
    return ShopifyOperationSpec(
        key, name, "mutation", SHOPIFY_API_VERSION, document, variables,
        "FulfillmentMutationResult", "GraphQLError", side_effect,
        ReadbackMetadata(True, read_key, strategy, summary),
        cost_expectation={"mode": "observed", "request_count": 1},
        fixture_keys=("success", "user_errors", "top_level_error", "timeout_before_send", "timeout_after_send", "malformed_result"),
    )


FULFILLMENT_MUTATION_REGISTRY = ShopifyOperationRegistry(
    (
        _read_spec(
            FULFILLMENT_ORDER_FULFILLMENTS_READ_OPERATION,
            "ConnectorOrderFulfillments",
            FULFILLMENT_ORDER_FULFILLMENTS_QUERY,
            {"orderId": "ID!"},
            "Reads the order fulfillment result after fulfillmentCreate.",
        ),
        _read_spec(
            FULFILLMENT_NODE_READ_OPERATION,
            "ConnectorFulfillmentNode",
            FULFILLMENT_NODE_QUERY,
            {"id": "ID!"},
            "Reads the exact fulfillment after trackingInfoUpdate.",
        ),
        _mutation_spec(
            FULFILLMENT_CREATE_OPERATION,
            "ConnectorFulfillmentCreate",
            FULFILLMENT_CREATE_DOCUMENT,
            {"fulfillment": "FulfillmentInput!"},
            SideEffectMetadata("create", "Creates one Shopify fulfillment for the selected FulfillmentOrder lines.", True),
            FULFILLMENT_ORDER_FULFILLMENTS_READ_OPERATION,
            "read_order_fulfillments",
            "Read the order's exact fulfillment list and line evidence; an uncertain create is never resent.",
        ),
        _mutation_spec(
            FULFILLMENT_TRACKING_UPDATE_OPERATION,
            "ConnectorFulfillmentTrackingInfoUpdate",
            FULFILLMENT_TRACKING_UPDATE_DOCUMENT,
            {"fulfillmentId": "ID!", "trackingInfoInput": "FulfillmentTrackingInput!", "notifyCustomer": "Boolean"},
            SideEffectMetadata("notify", "Updates tracking on one existing Shopify fulfillment with an explicit notification value.", True),
            FULFILLMENT_NODE_READ_OPERATION,
            "read_fulfillment",
            "Read the exact fulfillment and tracking result; an uncertain update is never resent.",
        ),
    )
)
FULFILLMENT_MUTATION_REGISTRY.freeze()


def _intent(operation_key: str, scope: str | None, business: Mapping[str, Any] | None, preconditions: Mapping[str, Any] | None, idempotency_key: str, defaults: Mapping[str, Any], target: Mapping[str, Any]) -> DurableIntentDescriptor:
    return DurableIntentDescriptor(
        operation_key,
        scope or "fulfillment:" + str(target.get("fulfillment_gid") or target.get("order_gid")),
        business if business is not None else defaults,
        preconditions if preconditions is not None else defaults,
        idempotency_key,
    )


def _request(spec: ShopifyOperationSpec, variables: Mapping[str, Any], intent: DurableIntentDescriptor, target: Mapping[str, Any]) -> MutationRequest:
    return MutationRequest(spec, variables, intent, ReadbackPlanDescriptor.from_metadata(spec.readback, target))


def _tracking_info(value: Any, field_name: str = "tracking_info") -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MutationGatewayError("invalid_tracking_info", f"{field_name} must be a list or None.")
    normalized: list[dict[str, Any]] = []
    for entry in value:
        if not isinstance(entry, Mapping):
            raise MutationGatewayError("invalid_tracking_info", f"{field_name} entries must be objects.")
        item: dict[str, Any] = {}
        for key in ("number", "url", "company"):
            if key in entry:
                item[key] = require_text(entry[key], f"{field_name}.{key}", max_length=2048)
        if not item:
            raise MutationGatewayError("invalid_tracking_info", f"{field_name} entries must contain tracking data.")
        normalized.append(item)
    return normalized


def _tracking_input(value: Any) -> dict[str, Any]:
    """Validate the V1 ``FulfillmentInput.trackingInfo`` object exactly."""

    if not isinstance(value, Mapping) or not value:
        raise MutationGatewayError("invalid_tracking_info", "tracking_info must be a non-empty object.")
    allowed = {"company", "number", "numbers", "url", "urls"}
    if set(value) - allowed:
        raise MutationGatewayError("invalid_tracking_info", "tracking_info contains an unsupported field.")
    normalized: dict[str, Any] = {}
    for key, item in value.items():
        if key in {"numbers", "urls"}:
            if not isinstance(item, (list, tuple)) or not item or len(item) > MAX_TRACKING_ITEMS or any(not isinstance(entry, str) or not entry.strip() for entry in item):
                raise MutationGatewayError("invalid_tracking_info", f"tracking_info.{key} must be a non-empty string list.")
            normalized[key] = list(item)
        else:
            normalized[key] = require_text(item, f"tracking_info.{key}", max_length=2048)
    return normalized


def _normalize_tracking_response(value: Any) -> list[dict[str, Any]]:
    # Shopify returns trackingInfo as a list in the selected mutation shape.
    # ``None`` is a valid empty state on a fulfillment without tracking.
    return _tracking_info(value, "trackingInfo")


class FulfillmentMutationGateway(MutationGateway):
    """Typed, one-call adapter for the two V1 fulfillment writes."""

    def build_create(
        self,
        order_gid: str,
        line_items_by_fulfillment_order: Sequence[Mapping[str, Any]],
        notify_customer: bool,
        *,
        tracking_info: Mapping[str, Any] | None = None,
        idempotency_key: str,
        operation_scope_key: str | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        order_gid = require_gid(order_gid, "Order", "order_gid")
        if not isinstance(notify_customer, bool):
            raise MutationGatewayError("invalid_boolean", "notify_customer must be bool.")
        if not isinstance(line_items_by_fulfillment_order, Sequence) or isinstance(line_items_by_fulfillment_order, (str, bytes, Mapping)) or not line_items_by_fulfillment_order:
            raise MutationGatewayError("invalid_line_items", "line_items_by_fulfillment_order must be a non-empty sequence.")
        rows: list[dict[str, Any]] = []
        for row in line_items_by_fulfillment_order:
            if not isinstance(row, Mapping) or set(row) != {"fulfillmentOrderId", "fulfillmentOrderLineItems"}:
                raise MutationGatewayError("invalid_line_items", "each fulfillment-order row must use the V1 keys exactly.")
            fo_gid = require_gid(row.get("fulfillmentOrderId"), "FulfillmentOrder", "fulfillmentOrderId")
            entries = row.get("fulfillmentOrderLineItems")
            if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes, Mapping)) or not entries:
                raise MutationGatewayError("invalid_line_items", "fulfillmentOrderLineItems must be a non-empty sequence.")
            normalized_entries: list[dict[str, Any]] = []
            for entry in entries:
                if not isinstance(entry, Mapping) or set(entry) != {"id", "quantity"}:
                    raise MutationGatewayError("invalid_line_items", "fulfillment-order line items must use id and quantity only.")
                normalized_entries.append({
                    "id": require_gid(entry.get("id"), "FulfillmentOrderLineItem", "fulfillmentOrderLineItems.id"),
                    "quantity": require_integer(entry.get("quantity"), "fulfillmentOrderLineItems.quantity", minimum=1),
                })
            rows.append({"fulfillmentOrderId": fo_gid, "fulfillmentOrderLineItems": normalized_entries})
        normalized_tracking = None if tracking_info is None else _tracking_input(tracking_info)
        fulfillment: dict[str, Any] = {"lineItemsByFulfillmentOrder": rows, "notifyCustomer": notify_customer}
        if normalized_tracking:
            # The V1 builder carries this exact object on the wire. Do not
            # convert it to the response-oriented list representation.
            fulfillment["trackingInfo"] = normalized_tracking
        defaults = {"mutation_domain": "fulfillment_create", "order_gid": order_gid, "line_items_by_fo": rows, "notify_customer": notify_customer}
        target = {"order_gid": order_gid}
        intent = _intent(FULFILLMENT_CREATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(FULFILLMENT_CREATE_OPERATION), {"fulfillment": fulfillment}, intent, target)

    def build_tracking_update(
        self,
        fulfillment_gid: str,
        tracking_info_input: Mapping[str, Any],
        notify_customer: bool,
        *,
        idempotency_key: str,
        operation_scope_key: str | None = None,
        business_intent: Mapping[str, Any] | None = None,
        preconditions_snapshot: Mapping[str, Any] | None = None,
    ) -> MutationRequest:
        fulfillment_gid = require_gid(fulfillment_gid, "Fulfillment", "fulfillment_gid")
        if not isinstance(tracking_info_input, Mapping) or not tracking_info_input:
            raise MutationGatewayError("invalid_tracking_info", "tracking_info_input must be a non-empty object.")
        allowed = {"company", "number", "numbers", "url", "urls"}
        if set(tracking_info_input) - allowed:
            raise MutationGatewayError("invalid_tracking_info", "tracking_info_input contains an unsupported field.")
        normalized: dict[str, Any] = {}
        for key, value in tracking_info_input.items():
            if key in {"numbers", "urls"}:
                if not isinstance(value, (list, tuple)) or not value or len(value) > MAX_TRACKING_ITEMS or any(not isinstance(item, str) or not item.strip() for item in value):
                    raise MutationGatewayError("invalid_tracking_info", f"tracking_info_input.{key} must be a non-empty string list.")
                normalized[key] = list(value)
            else:
                normalized[key] = require_text(value, f"tracking_info_input.{key}", max_length=2048)
        if not isinstance(notify_customer, bool):
            raise MutationGatewayError("invalid_boolean", "notify_customer must be bool.")
        require_text(idempotency_key, "idempotency_key", max_length=512)
        variables = {"fulfillmentId": fulfillment_gid, "trackingInfoInput": normalized, "notifyCustomer": notify_customer}
        defaults = {"mutation_domain": "fulfillment_tracking_update", "fulfillment_gid": fulfillment_gid, "tracking_info": normalized, "notify_customer": notify_customer}
        target = {"fulfillment_gid": fulfillment_gid}
        intent = _intent(FULFILLMENT_TRACKING_UPDATE_OPERATION, operation_scope_key, business_intent, preconditions_snapshot, idempotency_key, defaults, target)
        return _request(self.registry.require_operation(FULFILLMENT_TRACKING_UPDATE_OPERATION), variables, intent, target)

    def _normalize_response(self, request: MutationRequest, response: Mapping[str, Any]):
        data = response_data(response)
        if request.operation_key == FULFILLMENT_CREATE_OPERATION:
            payload = data.get("fulfillmentCreate")
            name = "fulfillmentCreate"
        elif request.operation_key == FULFILLMENT_TRACKING_UPDATE_OPERATION:
            payload = data.get("fulfillmentTrackingInfoUpdate")
            name = "fulfillmentTrackingInfoUpdate"
        else:
            raise MutationGatewayError("operation_not_supported", "Fulfillment mutation operation is not supported by this gateway.")
        if not isinstance(payload, Mapping):
            raise MutationShapeError("missing_payload", f"{name} payload is missing.")
        errors = parse_user_errors(payload.get("userErrors"))
        fulfillment = payload.get("fulfillment")
        if errors:
            # Preserve V1's synchronous rejection semantics for a pure error
            # response, while routing a response that also contains a
            # fulfillment object to readback instead of guessing which side
            # effects happened.
            if fulfillment is not None:
                return self._result(
                    request,
                    MutationOutcome.UNCERTAIN,
                    "ambiguous_user_errors",
                    f"Shopify returned fulfillment data alongside errors from {name}; verification is required.",
                    user_errors=errors,
                )
            return self._result(request, MutationOutcome.FAILED_CLEAN, "shopify_user_errors_validation", f"Shopify rejected {name}.", user_errors=errors)
        if not isinstance(fulfillment, Mapping):
            raise MutationShapeError("missing_success_payload", f"{name} returned no fulfillment object.")
        fulfillment_gid = require_gid(fulfillment.get("id"), "Fulfillment", "fulfillment.id")
        status = fulfillment.get("status")
        if not isinstance(status, str) or not status.strip():
            raise MutationShapeError("invalid_success_payload", f"{name} returned no fulfillment status.")
        if request.operation_key == FULFILLMENT_CREATE_OPERATION and status != "SUCCESS":
            raise MutationShapeError("invalid_success_payload", "fulfillmentCreate returned a fulfillment that is not SUCCESS.")
        tracking = _normalize_tracking_response(fulfillment.get("trackingInfo"))
        normalized = {"fulfillment": {"id": fulfillment_gid, "status": status, "tracking_info": tracking}}
        return self._result(request, MutationOutcome.SUCCEEDED, None, f"Shopify accepted {name}; verification remains required.", payload=normalized)


__all__ = [
    "FULFILLMENT_CREATE_DOCUMENT",
    "FULFILLMENT_CREATE_OPERATION",
    "FULFILLMENT_MUTATION_REGISTRY",
    "FULFILLMENT_NODE_QUERY",
    "FULFILLMENT_NODE_READ_OPERATION",
    "FULFILLMENT_ORDER_FULFILLMENTS_QUERY",
    "FULFILLMENT_ORDER_FULFILLMENTS_READ_OPERATION",
    "FULFILLMENT_TRACKING_UPDATE_DOCUMENT",
    "FULFILLMENT_TRACKING_UPDATE_OPERATION",
    "FulfillmentMutationGateway",
]
