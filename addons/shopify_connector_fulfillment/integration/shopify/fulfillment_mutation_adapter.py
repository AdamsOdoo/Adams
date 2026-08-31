"""P14 request adapter around the existing P08 fulfillment gateway."""

from __future__ import annotations

from dataclasses import dataclass

from shopify_connector_core.integration.shopify.mutation_contracts import MutationRequest, MutationResult

from ...domain.fulfillment_mutation import (
    FULFILLMENT_CREATE_OPERATION,
    FULFILLMENT_TRACKING_UPDATE_OPERATION,
    FulfillmentMutationPayload,
    canonical_fulfillment_fingerprint,
)
from .fulfillment_mutation_gateway import FULFILLMENT_MUTATION_REGISTRY, FulfillmentMutationGateway


class FulfillmentMutationAdapterError(ValueError):
    """Request construction failed before any remote call."""

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("adapter error code must be non-empty")
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class FulfillmentMutationRequestAdapter:
    """Build one exact P08 request and execute it at most once."""

    gateway: FulfillmentMutationGateway

    def __init__(self, gateway_or_delegate: FulfillmentMutationGateway | object) -> None:
        if isinstance(gateway_or_delegate, FulfillmentMutationGateway):
            gateway = gateway_or_delegate
        else:
            gateway = FulfillmentMutationGateway(gateway_or_delegate, FULFILLMENT_MUTATION_REGISTRY)
        object.__setattr__(self, "gateway", gateway)

    @staticmethod
    def _key(payload: FulfillmentMutationPayload, requested: str | None) -> str:
        key = requested or payload.idempotency_key or canonical_fulfillment_fingerprint(payload)
        if not isinstance(key, str) or not key.strip():
            raise FulfillmentMutationAdapterError("missing_idempotency_key", "A durable fulfillment idempotency key is required.")
        return key

    def build_request(self, payload: FulfillmentMutationPayload, *, idempotency_key: str | None = None) -> MutationRequest:
        if not isinstance(payload, FulfillmentMutationPayload):
            raise TypeError("payload must be FulfillmentMutationPayload")
        key = self._key(payload, idempotency_key)
        scope = payload.operation_scope_key
        if payload.operation == FULFILLMENT_CREATE_OPERATION:
            if payload.order_gid is None or not payload.line_items_by_fulfillment_order:
                raise FulfillmentMutationAdapterError("invalid_create", "Fulfillment create requires order and line evidence.")
            return self.gateway.build_create(
                payload.order_gid,
                payload.line_items_by_fulfillment_order,
                payload.notify_customer,
                tracking_info=payload.tracking_info,
                idempotency_key=key,
                operation_scope_key=scope,
                business_intent=payload.business_intent(),
                preconditions_snapshot=payload.preconditions_snapshot(),
            )
        if payload.operation == FULFILLMENT_TRACKING_UPDATE_OPERATION:
            if payload.fulfillment_gid is None or not payload.tracking_info_input:
                raise FulfillmentMutationAdapterError("invalid_tracking_update", "Tracking update requires a fulfillment and tracking input.")
            return self.gateway.build_tracking_update(
                payload.fulfillment_gid,
                payload.tracking_info_input,
                payload.notify_customer,
                idempotency_key=key,
                operation_scope_key=scope,
                business_intent=payload.business_intent(),
                preconditions_snapshot=payload.preconditions_snapshot(),
            )
        raise FulfillmentMutationAdapterError("operation_not_supported", "Unsupported fulfillment mutation operation.")

    build = build_request

    def execute_once(self, request: MutationRequest) -> MutationResult:
        if not isinstance(request, MutationRequest):
            raise TypeError("request must be MutationRequest")
        return self.gateway.execute_once(request)

    execute = execute_once


FulfillmentMutationAdapter = FulfillmentMutationRequestAdapter

__all__ = [
    "FulfillmentMutationAdapter",
    "FulfillmentMutationAdapterError",
    "FulfillmentMutationRequestAdapter",
]
