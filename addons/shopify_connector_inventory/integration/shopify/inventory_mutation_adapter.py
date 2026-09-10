"""Typed request-construction adapter for the stable P08 inventory gateway.

This adapter belongs at the Shopify integration edge because it imports the
P08 gateway.  It only builds immutable requests or, when explicitly asked,
executes one through that gateway; admission, retries and readback remain
application/domain responsibilities.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
    MutationRequest,
    MutationResult,
)

from ...domain.inventory_mutation import InventoryMutationPayload, InventoryPairScope
from .inventory_mutation_gateway import (
    INVENTORY_MUTATION_REGISTRY,
    InventoryMutationGateway,
)


class InventoryMutationAdapterError(ValueError):
    """A pure request-construction input cannot satisfy V1's contract."""

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("adapter error code must be non-empty")
        super().__init__(message)
        self.code = code
        self.message = message


def _utc_timestamp(value: datetime | str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise InventoryMutationAdapterError("invalid_timestamp", "snapshot_taken_at must be timezone-aware UTC.")
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, str) and value.strip():
        text = value.strip()
        text = text[:-1] + "+00:00" if text.endswith("Z") else text
        try:
            parsed = datetime.fromisoformat(text)
        except (TypeError, ValueError, OverflowError) as exc:
            raise InventoryMutationAdapterError("invalid_timestamp", "snapshot_taken_at must be an ISO timestamp.") from exc
        if parsed.tzinfo is None:
            raise InventoryMutationAdapterError("invalid_timestamp", "snapshot_taken_at must include an explicit UTC offset.")
        if parsed.utcoffset() != timedelta(0):
            raise InventoryMutationAdapterError("invalid_timestamp", "snapshot_taken_at must be UTC.")
        return parsed.astimezone(timezone.utc).isoformat()
    raise InventoryMutationAdapterError("invalid_timestamp", "snapshot_taken_at must be an ISO timestamp.")


@dataclass(frozen=True, slots=True)
class InventoryMutationRequestAdapter:
    """Build exact P08 requests and optionally execute exactly one of them."""

    gateway: InventoryMutationGateway

    def __init__(
        self,
        gateway_or_delegate: InventoryMutationGateway | Callable[..., Any] | Any,
        *,
        expected_store_id: int | None = None,
    ) -> None:
        if isinstance(gateway_or_delegate, InventoryMutationGateway):
            selected = gateway_or_delegate
            if expected_store_id is not None and expected_store_id != selected.expected_store_id:
                raise InventoryMutationAdapterError(
                    "store_scope_mismatch",
                    "The adapter store does not match the already-bound mutation gateway.",
                )
        else:
            if isinstance(expected_store_id, bool) or not isinstance(expected_store_id, int) or expected_store_id <= 0:
                raise InventoryMutationAdapterError(
                    "missing_store_scope",
                    "An expected store ID is required when the adapter creates its gateway.",
                )
            selected = InventoryMutationGateway(
                gateway_or_delegate,
                INVENTORY_MUTATION_REGISTRY,
                expected_store_id=expected_store_id,
            )
        object.__setattr__(self, "gateway", selected)

    @staticmethod
    def _reference_document_uri(
        payload: InventoryMutationPayload,
        *,
        database_uuid: str | None,
        job_id: int | None,
        reference_document_uri: str | None,
    ) -> str:
        if reference_document_uri is not None:
            if not isinstance(reference_document_uri, str) or not reference_document_uri.strip():
                raise InventoryMutationAdapterError("invalid_reference", "reference_document_uri must be non-empty.")
            return reference_document_uri
        if payload.reference_document_uri:
            return payload.reference_document_uri
        if not isinstance(database_uuid, str) or not database_uuid.strip():
            raise InventoryMutationAdapterError("missing_reference", "A stable database UUID is required for the V1 reference URI.")
        if isinstance(job_id, bool) or not isinstance(job_id, int) or job_id <= 0:
            raise InventoryMutationAdapterError("missing_reference", "A positive job ID is required for the V1 reference URI.")
        return f"odoo://{database_uuid}/shopify.connector.job/{job_id}"

    @staticmethod
    def _preconditions(
        payload: InventoryMutationPayload,
        *,
        snapshot_taken_at: datetime | str | None,
    ) -> Mapping[str, Any]:
        timestamp = _utc_timestamp(snapshot_taken_at if snapshot_taken_at is not None else payload.snapshot_taken_at)
        result = payload.preconditions_snapshot()
        result["snapshot_taken_at"] = timestamp
        return result

    def build_request(
        self,
        payload: InventoryMutationPayload,
        *,
        idempotency_key: str | None = None,
        database_uuid: str | None = None,
        job_id: int | None = None,
        reference_document_uri: str | None = None,
        snapshot_taken_at: datetime | str | None = None,
    ) -> MutationRequest:
        """Construct one immutable P08 request; never invoke its delegate."""

        if not isinstance(payload, InventoryMutationPayload):
            raise TypeError("payload must be InventoryMutationPayload")
        target = payload.normalized_target_quantity
        if target is None:
            raise InventoryMutationAdapterError("invalid_quantity", "Inventory quantity must be integral within the V1 tolerance.")
        key = idempotency_key if idempotency_key is not None else payload.idempotency_key
        if not isinstance(key, str) or not key.strip():
            raise InventoryMutationAdapterError("missing_idempotency_key", "A request-owned idempotency key is required.")
        # Carry the validated scope object across the integration seam.  The
        # gateway rejects strings so a caller cannot substitute a foreign
        # scope for this exact store/item/location pair.
        scope = InventoryPairScope(
            payload.store_id,
            payload.inventory_item_gid,
            payload.location_gid,
        )
        business_intent = payload.business_intent()
        preconditions = self._preconditions(payload, snapshot_taken_at=snapshot_taken_at)
        contract_context = {
            "company_id": payload.company_id,
            "expected_generation": payload.expected_generation,
            "current_generation": payload.current_generation,
            "expected_store_identity": payload.expected_store_identity,
            "current_store_identity": payload.current_store_identity,
            "snapshot_taken_at": preconditions["snapshot_taken_at"],
        }
        if payload.operation == "inventory_activate":
            if target != 0:
                raise InventoryMutationAdapterError("invalid_quantity", "Inventory activation preserves the V1 zero baseline.")
            return self.gateway.build_activate(
                payload.inventory_item_gid,
                payload.location_gid,
                idempotency_key=key,
                operation_scope_key=scope,
                business_intent=business_intent,
                preconditions_snapshot=preconditions,
                contract_context=contract_context,
            )
        if payload.change_from_quantity is None:
            raise InventoryMutationAdapterError("missing_cas", "A strict changeFromQuantity is required for inventorySetQuantities.")
        uri = self._reference_document_uri(
            payload,
            database_uuid=database_uuid,
            job_id=job_id,
            reference_document_uri=reference_document_uri,
        )
        return self.gateway.build_set_quantities(
            payload.inventory_item_gid,
            payload.location_gid,
            target,
            payload.change_from_quantity,
            reference_document_uri=uri,
            idempotency_key=key,
            operation_scope_key=scope,
            business_intent=business_intent,
            preconditions_snapshot=preconditions,
            contract_context=contract_context,
        )

    build = build_request

    def execute_once(self, request: MutationRequest) -> MutationResult:
        """Send one request through P08; retries/readback belong above here."""

        if not isinstance(request, MutationRequest):
            raise TypeError("request must be MutationRequest")
        return self.gateway.execute_once(request)

    execute = execute_once


__all__ = ["InventoryMutationAdapterError", "InventoryMutationRequestAdapter"]
