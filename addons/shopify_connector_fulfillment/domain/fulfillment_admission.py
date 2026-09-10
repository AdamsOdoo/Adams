"""Pure admission policy for the P14 fulfillment command."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .fulfillment_mutation import (
    ACTIVE_RUN_STATES,
    CREATE_FULFILLMENT_ACTION,
    FO_BLOCKING_STATUSES,
    FO_ELIGIBLE_STATUSES,
    FULFILLMENT_CREATE_OPERATION,
    FULFILLMENT_RUNTIME_MODES,
    AdmissionDecision,
    AdmissionReason,
    FulfillmentMutationPayload,
    _domain,
    _gid,
    _nonnegative_int,
    _positive_int,
)


def _selection_reason(payload: FulfillmentMutationPayload) -> tuple[AdmissionReason, str] | None:
    if payload.operation != FULFILLMENT_CREATE_OPERATION:
        return None
    if not payload.line_items_by_fulfillment_order:
        return AdmissionReason.LINE_ITEMS_MISSING, "At least one shipped FulfillmentOrder line is required."
    if not payload.fulfillment_order_observations:
        return AdmissionReason.FULFILLMENT_ORDER_SNAPSHOT_MISSING, "A complete fresh FulfillmentOrder eligibility snapshot is required."
    if not payload.eligibility_snapshot_complete:
        return AdmissionReason.FULFILLMENT_ORDER_SNAPSHOT_INCOMPLETE, "The FulfillmentOrder eligibility snapshot is not marked complete."
    if payload.snapshot_taken_at is None or (isinstance(payload.snapshot_taken_at, str) and not payload.snapshot_taken_at.strip()):
        return AdmissionReason.FULFILLMENT_ORDER_SNAPSHOT_MISSING, "The fresh eligibility snapshot timestamp is required."
    if payload.eligibility_snapshot_store_identity != payload.expected_store_identity:
        return AdmissionReason.FULFILLMENT_ORDER_SNAPSHOT_INCOMPLETE, "The eligibility snapshot does not identify the expected Shopify store."
    if payload.eligibility_snapshot_order_gid != payload.order_gid:
        return AdmissionReason.FULFILLMENT_ORDER_SNAPSHOT_INCOMPLETE, "The eligibility snapshot does not identify the requested Shopify order."
    location_evidence = payload.location
    if location_evidence is None:
        return AdmissionReason.LOCATION_EVIDENCE_MISSING, "An active core-cache location proof is required."
    if location_evidence.store_id != payload.store_id or not location_evidence.cache_present or not location_evidence.active:
        return AdmissionReason.LOCATION_EVIDENCE_MISMATCH, "The fulfillment location is not an active exact row in the core location cache."
    by_id = {item.get("id"): item for item in payload.fulfillment_order_observations if isinstance(item.get("id"), str)}
    selected_ids = {row["fulfillmentOrderId"] for row in payload.line_items_by_fulfillment_order}
    if not selected_ids.issubset(by_id):
        return AdmissionReason.FULFILLMENT_ORDER_INELIGIBLE, "Every selected FulfillmentOrder must be present in the fresh eligibility snapshot."
    locations: set[str] = set()
    # V1 intentionally blocks a mixed order containing any hold/scheduled/
    # incomplete FulfillmentOrder.  Do this before selecting the shipped rows
    # so a client cannot hide a blocking sibling by omitting it from its lines.
    for fact in by_id.values():
        if fact.get("status") in FO_BLOCKING_STATUSES:
            return AdmissionReason.FULFILLMENT_ORDER_BLOCKED, f"FulfillmentOrder status {fact.get('status')!r} is not safe to mutate."
    for row in payload.line_items_by_fulfillment_order:
        fo_gid = row["fulfillmentOrderId"]
        fact = by_id.get(fo_gid)
        if fact is None:
            return AdmissionReason.FULFILLMENT_ORDER_INELIGIBLE, "The selected FulfillmentOrder was not in the fresh eligibility snapshot."
        status = fact.get("status")
        if status not in FO_ELIGIBLE_STATUSES:
            return AdmissionReason.FULFILLMENT_ORDER_INELIGIBLE, "The selected FulfillmentOrder is not eligible for creation."
        actions = {(action or {}).get("action") for action in (fact.get("supportedActions") or []) if isinstance(action, Mapping)}
        if CREATE_FULFILLMENT_ACTION not in actions:
            return AdmissionReason.FULFILLMENT_ORDER_INELIGIBLE, "The selected FulfillmentOrder does not support CREATE_FULFILLMENT."
        assigned = fact.get("assignedLocation")
        location = assigned.get("location") if isinstance(assigned, Mapping) else None
        location_gid = location.get("id") if isinstance(location, Mapping) else None
        if location_gid is None:
            return AdmissionReason.FULFILLMENT_ORDER_LOCATION, "Every selected FulfillmentOrder needs an exact assigned location."
        try:
            _gid(location_gid, "Location", "assignedLocation.location.id")
        except ValueError:
            return AdmissionReason.FULFILLMENT_ORDER_LOCATION, "The selected FulfillmentOrder location is malformed."
        if location_gid != location_evidence.location_gid:
            return AdmissionReason.LOCATION_EVIDENCE_MISMATCH, "The selected FulfillmentOrder location does not match the active cached location proof."
        locations.add(location_gid)
        available = {line.get("id"): line.get("remainingQuantity") for line in (fact.get("line_items") or []) if isinstance(line, Mapping)}
        for entry in row["fulfillmentOrderLineItems"]:
            remaining = available.get(entry["id"])
            if isinstance(remaining, bool) or not isinstance(remaining, int) or remaining < entry["quantity"]:
                return AdmissionReason.FULFILLMENT_ORDER_QUANTITY, "Requested fulfillment quantity exceeds the fresh remaining quantity."
    if len(locations) > 1:
        return AdmissionReason.FULFILLMENT_ORDER_LOCATION, "All shipped FulfillmentOrders must share one exact Shopify location."
    return None


class FulfillmentAdmissionPolicy:
    """Fail closed on lifecycle, tenant, selection and notification fences."""

    @staticmethod
    def _blocked(payload: FulfillmentMutationPayload, reason: AdmissionReason, message: str, **details: Any) -> AdmissionDecision:
        return AdmissionDecision(False, reason, message, payload.operation_scope_key, details)

    def evaluate(self, payload: FulfillmentMutationPayload, *, current_store_id: int | None = None, current_company_id: int | None = None, current_connection_generation: int | None = None, current_configuration_generation: int | None = None, current_store_identity: str | None = None, runtime_mode: str | None = None, store_state: str | None = None, run_state: str | None = None, cancel_requested: bool | None = None, fulfillment_domain_enabled: bool | None = None, active_operation_scopes: Sequence[str] = (), requested_scope_key: str | None = None, remote_uncertain: bool = False) -> AdmissionDecision:
        if not isinstance(payload, FulfillmentMutationPayload):
            raise TypeError("payload must be FulfillmentMutationPayload")
        scope = payload.operation_scope_key
        if remote_uncertain:
            return self._blocked(payload, AdmissionReason.UNCERTAIN_REQUIRES_READBACK, "An uncertain fulfillment mutation must be read back before another send.")
        requested_scope_key = payload.requested_scope_key if requested_scope_key is None else requested_scope_key
        if requested_scope_key is not None and requested_scope_key != scope:
            return self._blocked(payload, AdmissionReason.SCOPE_MISMATCH, "The operation scope is server-derived and does not match this fulfillment.")
        if (runtime_mode if runtime_mode is not None else payload.runtime_mode) not in FULFILLMENT_RUNTIME_MODES:
            return self._blocked(payload, AdmissionReason.MODE_MISMATCH, "Fulfillment mutations require fulfillment or all runtime mode.")
        if (payload.fulfillment_domain_enabled if fulfillment_domain_enabled is None else fulfillment_domain_enabled) is not True:
            return self._blocked(payload, AdmissionReason.DOMAIN_DISABLED, "The fulfillment domain is not enabled for this store.")
        if (store_state if store_state is not None else payload.store_state) != "connected":
            return self._blocked(payload, AdmissionReason.STORE_NOT_CONNECTED, "Fulfillment mutations require a connected store.")
        if (run_state if run_state is not None else payload.run_state) not in ACTIVE_RUN_STATES:
            return self._blocked(payload, AdmissionReason.RUN_NOT_ACTIVE, "Fulfillment mutations require an active run.")
        if payload.cancel_requested if cancel_requested is None else cancel_requested:
            return self._blocked(payload, AdmissionReason.CANCELLATION_REQUESTED, "A cancelled run cannot admit a fulfillment mutation.")
        store_id = payload.current_store_id if current_store_id is None else current_store_id
        company_id = payload.current_company_id if current_company_id is None else current_company_id
        if store_id is None:
            return self._blocked(payload, AdmissionReason.STORE_ID_MISMATCH, "The current store identity is required before mutation admission.")
        if company_id is None:
            return self._blocked(payload, AdmissionReason.COMPANY_ID_MISMATCH, "The current company identity is required before mutation admission.")
        try:
            _positive_int(store_id, "current_store_id")
            _positive_int(company_id, "current_company_id")
        except ValueError as exc:
            return self._blocked(payload, AdmissionReason.COMPANY_ID_MISMATCH, str(exc))
        if store_id != payload.store_id:
            return self._blocked(payload, AdmissionReason.STORE_ID_MISMATCH, "The current store does not own this fulfillment intent.")
        if company_id != payload.company_id:
            return self._blocked(payload, AdmissionReason.COMPANY_ID_MISMATCH, "The current company does not own this fulfillment intent.")
        identity = payload.current_store_identity if current_store_identity is None else current_store_identity
        if identity is None:
            return self._blocked(payload, AdmissionReason.STORE_IDENTITY_MISSING, "The current Shopify shop identity is required before mutation admission.")
        try:
            identity = _domain(identity, "current_store_identity")
        except ValueError as exc:
            return self._blocked(payload, AdmissionReason.STORE_IDENTITY_MISMATCH, str(exc))
        if identity != payload.expected_store_identity:
            return self._blocked(payload, AdmissionReason.STORE_IDENTITY_MISMATCH, "The current Shopify shop identity changed.")
        connection = payload.current_connection_generation if current_connection_generation is None else current_connection_generation
        if connection is None:
            return self._blocked(payload, AdmissionReason.GENERATION_MISSING, "The current connection generation is required before mutation admission.")
        try:
            _nonnegative_int(connection, "current_connection_generation")
        except ValueError as exc:
            return self._blocked(payload, AdmissionReason.GENERATION_MISSING, str(exc))
        if connection != payload.expected_connection_generation:
            return self._blocked(payload, AdmissionReason.STALE_GENERATION, "The store connection generation changed; refresh the intent.")
        config = payload.current_configuration_generation if current_configuration_generation is None else current_configuration_generation
        if config is None:
            return self._blocked(payload, AdmissionReason.CONFIGURATION_GENERATION_MISSING, "The current configuration generation is required before mutation admission.")
        try:
            _nonnegative_int(config, "current_configuration_generation")
        except ValueError as exc:
            return self._blocked(payload, AdmissionReason.CONFIGURATION_GENERATION_MISSING, str(exc))
        if config != payload.expected_configuration_generation:
            return self._blocked(payload, AdmissionReason.STALE_CONFIGURATION_GENERATION, "The store fulfillment configuration changed; refresh the intent.")
        binding = payload.binding
        if binding is None:
            return self._blocked(payload, AdmissionReason.BINDING_IDENTITY_MISSING, "An exact store/company/picking/order binding snapshot is required.")
        if (binding.store_id, binding.company_id, binding.picking_id) != (payload.store_id, payload.company_id, payload.picking_id) or binding.order_gid != payload.order_gid:
            return self._blocked(payload, AdmissionReason.BINDING_IDENTITY_MISMATCH, "The binding snapshot does not belong to this store, company, picking or order.")
        if payload.operation == FULFILLMENT_CREATE_OPERATION:
            if payload.order_gid is None:
                return self._blocked(payload, AdmissionReason.ORDER_MISSING, "An exact Shopify order binding is required for creation.")
            if not payload.line_items_by_fulfillment_order:
                return self._blocked(payload, AdmissionReason.LINE_ITEMS_MISSING, "At least one exact FulfillmentOrder line is required.")
            if binding.state != "absent" or binding.fulfillment_gid is not None:
                return self._blocked(payload, AdmissionReason.DUPLICATE_BINDING, "This picking already owns a fulfillment binding.")
            selection = _selection_reason(payload)
            if selection is not None:
                return self._blocked(payload, selection[0], selection[1])
        elif payload.fulfillment_gid is None:
            return self._blocked(payload, AdmissionReason.FULFILLMENT_MISSING, "An exact Shopify fulfillment binding is required for tracking update.")
        elif binding.state != "present" or binding.fulfillment_gid != payload.fulfillment_gid:
            return self._blocked(payload, AdmissionReason.BINDING_MISSING, "The exact fulfillment binding no longer exists for this picking.")
        elif not payload.tracking_info_input:
            return self._blocked(payload, AdmissionReason.TRACKING_MISSING, "Tracking information is required for an update.")
        evidence = payload.notification
        if evidence is None:
            return self._blocked(payload, AdmissionReason.NOTIFICATION_EVIDENCE_MISSING, "The effective notify_customer value must be accompanied by explicit evidence.")
        if evidence.default_enabled and not evidence.confirmed:
            return self._blocked(payload, AdmissionReason.NOTIFICATION_CONFIRMATION_MISSING, "Customer notification is enabled but not confirmed for this store.")
        if evidence.effective != payload.notify_customer or evidence.expected_effective != payload.notify_customer:
            return self._blocked(payload, AdmissionReason.NOTIFICATION_MISMATCH, "The effective notification value does not match its confirmed store setting.")
        if scope in set(active_operation_scopes):
            return self._blocked(payload, AdmissionReason.OPERATION_SCOPE_CONFLICT, "Another non-terminal fulfillment operation owns this exact scope.")
        return AdmissionDecision(True, AdmissionReason.ADMITTED, "Fulfillment mutation admitted with exact tenant, lifecycle, scope, selection and notification evidence.", scope, {"operation": payload.operation, "shopify_operation_key": payload.shopify_operation_key, "notify_customer": payload.notify_customer, "notification_evidence": evidence.as_dict()})


evaluate_fulfillment_admission = FulfillmentAdmissionPolicy().evaluate

__all__ = ["FulfillmentAdmissionPolicy", "evaluate_fulfillment_admission"]
