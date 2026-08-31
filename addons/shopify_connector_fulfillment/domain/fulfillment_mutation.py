"""Pure P14 fulfillment command, evidence and identity contracts."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from odoo.addons.shopify_connector_core.domain.immutability import freeze_value, to_plain


FULFILLMENT_CREATE_OPERATION = "fulfillment_create"
FULFILLMENT_TRACKING_UPDATE_OPERATION = "fulfillment_tracking_update"
SHOPIFY_FULFILLMENT_CREATE_OPERATION = "fulfillment.create"
SHOPIFY_FULFILLMENT_TRACKING_UPDATE_OPERATION = "fulfillment.tracking_update"
FULFILLMENT_RUNTIME_MODE = "fulfillment"
FULFILLMENT_ALL_RUNTIME_MODE = "all"
FULFILLMENT_RUNTIME_MODES = frozenset((FULFILLMENT_RUNTIME_MODE, FULFILLMENT_ALL_RUNTIME_MODE))
ACTIVE_RUN_STATES = frozenset(("admitted", "running", "waiting"))
FO_ELIGIBLE_STATUSES = frozenset(("OPEN", "IN_PROGRESS"))
FO_BLOCKING_STATUSES = frozenset(("ON_HOLD", "SCHEDULED", "INCOMPLETE"))
CREATE_FULFILLMENT_ACTION = "CREATE_FULFILLMENT"
MAX_FULFILLMENT_ORDERS = 100
MAX_LINE_ITEMS = 500
MAX_TRACKING_ITEMS = 50
MAX_READBACK_FULFILLMENTS = 250
MAX_INCONCLUSIVE_READS = 3

_GID = re.compile(r"^gid://shopify/(?P<kind>[A-Za-z][A-Za-z0-9_]*)/(?P<id>[1-9][0-9]*)$")
_SHOP_DOMAIN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$")
_TOKEN = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,127}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class FulfillmentMutationOperation(str, Enum):
    CREATE = FULFILLMENT_CREATE_OPERATION
    TRACKING_UPDATE = FULFILLMENT_TRACKING_UPDATE_OPERATION


class AdmissionReason(str, Enum):
    ADMITTED = "admitted"
    OPERATION_NOT_SUPPORTED = "operation_not_supported"
    DOMAIN_DISABLED = "fulfillment_domain_disabled"
    MODE_MISMATCH = "runtime_mode_mismatch"
    STORE_NOT_CONNECTED = "store_not_connected"
    RUN_NOT_ACTIVE = "run_not_active"
    CANCELLATION_REQUESTED = "cancellation_requested"
    STORE_ID_MISMATCH = "store_id_mismatch"
    COMPANY_ID_MISMATCH = "company_id_mismatch"
    STORE_IDENTITY_MISSING = "store_identity_missing"
    STORE_IDENTITY_MISMATCH = "store_identity_mismatch"
    GENERATION_MISSING = "generation_missing"
    STALE_GENERATION = "stale_generation"
    CONFIGURATION_GENERATION_MISSING = "configuration_generation_missing"
    STALE_CONFIGURATION_GENERATION = "stale_configuration_generation"
    SCOPE_MISMATCH = "operation_scope_mismatch"
    OPERATION_SCOPE_CONFLICT = "operation_scope_conflict"
    UNCERTAIN_REQUIRES_READBACK = "uncertain_requires_readback"
    ORDER_MISSING = "order_mapping_missing"
    FULFILLMENT_MISSING = "fulfillment_mapping_missing"
    BINDING_MISSING = "fulfillment_binding_missing"
    DUPLICATE_BINDING = "duplicate_fulfillment_binding"
    LINE_ITEMS_MISSING = "line_items_missing"
    LINE_ITEMS_INVALID = "line_items_invalid"
    TRACKING_MISSING = "tracking_info_missing"
    TRACKING_INVALID = "tracking_info_invalid"
    FULFILLMENT_ORDER_BLOCKED = "fulfillment_order_blocked"
    FULFILLMENT_ORDER_INELIGIBLE = "fulfillment_order_ineligible"
    FULFILLMENT_ORDER_LOCATION = "fulfillment_order_location_mismatch"
    FULFILLMENT_ORDER_QUANTITY = "fulfillment_order_quantity_mismatch"
    FULFILLMENT_ORDER_SNAPSHOT_MISSING = "fulfillment_order_snapshot_missing"
    FULFILLMENT_ORDER_SNAPSHOT_INCOMPLETE = "fulfillment_order_snapshot_incomplete"
    LOCATION_EVIDENCE_MISSING = "fulfillment_location_evidence_missing"
    LOCATION_EVIDENCE_MISMATCH = "fulfillment_location_evidence_mismatch"
    BINDING_IDENTITY_MISSING = "fulfillment_binding_identity_missing"
    BINDING_IDENTITY_MISMATCH = "fulfillment_binding_identity_mismatch"
    NOTIFICATION_EVIDENCE_MISSING = "notification_evidence_missing"
    NOTIFICATION_CONFIRMATION_MISSING = "fulfillment_notification_confirmation_missing"
    NOTIFICATION_MISMATCH = "notification_value_mismatch"


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _text(value: Any, field_name: str, *, max_length: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{field_name} must be a bounded non-empty string")
    return value


def _boolean(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{field_name} must be bool")
    return value


def _gid(value: Any, kind: str, field_name: str) -> str:
    match = _GID.fullmatch(value) if isinstance(value, str) else None
    if match is None or match.group("kind") != kind:
        raise ValueError(f"{field_name} must be a canonical Shopify {kind} GID")
    return value


def _domain(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or _SHOP_DOMAIN.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a canonical myshopify.com domain")
    return value


def _operation(value: Any) -> str:
    aliases = {FULFILLMENT_CREATE_OPERATION: FULFILLMENT_CREATE_OPERATION, SHOPIFY_FULFILLMENT_CREATE_OPERATION: FULFILLMENT_CREATE_OPERATION, FULFILLMENT_TRACKING_UPDATE_OPERATION: FULFILLMENT_TRACKING_UPDATE_OPERATION, SHOPIFY_FULFILLMENT_TRACKING_UPDATE_OPERATION: FULFILLMENT_TRACKING_UPDATE_OPERATION}
    try:
        return value.value if isinstance(value, FulfillmentMutationOperation) else aliases[value]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"unsupported fulfillment mutation operation: {value!r}") from exc


def shopify_operation_key(value: Any) -> str:
    return SHOPIFY_FULFILLMENT_CREATE_OPERATION if _operation(value) == FULFILLMENT_CREATE_OPERATION else SHOPIFY_FULFILLMENT_TRACKING_UPDATE_OPERATION


def derive_fulfillment_operation_scope(operation: str | FulfillmentMutationOperation, store_id: int, picking_id: int, target_gid: str | None = None) -> str:
    operation = _operation(operation)
    _positive_int(store_id, "store_id")
    _positive_int(picking_id, "picking_id")
    if operation == FULFILLMENT_CREATE_OPERATION:
        # One Odoo picking is one Shopify fulfillment event, even when the
        # event spans multiple FulfillmentOrders.  The target FO is evidence,
        # never part of the conflict key.
        return f"fulfillment:{store_id}:{picking_id}"
    _gid(target_gid, "Fulfillment", "target_gid")
    return f"tracking:{store_id}:{target_gid}"


@dataclass(frozen=True, slots=True)
class FulfillmentBindingEvidence:
    """Authoritative binding snapshot, including an explicit absence state."""

    state: str
    store_id: int
    company_id: int
    picking_id: int
    order_gid: str
    fulfillment_gid: str | None = None

    def __post_init__(self) -> None:
        if self.state not in {"absent", "present"}:
            raise ValueError("binding evidence state must be absent or present")
        _positive_int(self.store_id, "binding.store_id")
        _positive_int(self.company_id, "binding.company_id")
        _positive_int(self.picking_id, "binding.picking_id")
        _gid(self.order_gid, "Order", "binding.order_gid")
        if self.state == "present":
            _gid(self.fulfillment_gid, "Fulfillment", "binding.fulfillment_gid")
        elif self.fulfillment_gid is not None:
            raise ValueError("an absent binding cannot contain a fulfillment GID")

    @classmethod
    def from_value(cls, value: "FulfillmentBindingEvidence | Mapping[str, Any] | None") -> "FulfillmentBindingEvidence | None":
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("binding_evidence must be an object")
        if set(value) != {"state", "store_id", "company_id", "picking_id", "order_gid", "fulfillment_gid"}:
            raise ValueError("binding_evidence must use the exact identity fields")
        return cls(
            value.get("state"),
            value.get("store_id"),
            value.get("company_id"),
            value.get("picking_id"),
            value.get("order_gid"),
            value.get("fulfillment_gid"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "store_id": self.store_id,
            "company_id": self.company_id,
            "picking_id": self.picking_id,
            "order_gid": self.order_gid,
            "fulfillment_gid": self.fulfillment_gid,
        }


@dataclass(frozen=True, slots=True)
class FulfillmentLocationEvidence:
    """The exact active location row read from the core cache."""

    location_gid: str
    store_id: int
    active: bool
    cache_present: bool
    source: str = "core_location_cache"

    def __post_init__(self) -> None:
        _gid(self.location_gid, "Location", "location_evidence.location_gid")
        _positive_int(self.store_id, "location_evidence.store_id")
        _boolean(self.active, "location_evidence.active")
        _boolean(self.cache_present, "location_evidence.cache_present")
        if self.source != "core_location_cache":
            raise ValueError("location evidence must come from the core location cache")

    @classmethod
    def from_value(cls, value: "FulfillmentLocationEvidence | Mapping[str, Any] | None") -> "FulfillmentLocationEvidence | None":
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("location_evidence must be an object")
        allowed = {"location_gid", "id", "store_id", "active", "isActive", "cache_present", "present", "source"}
        if set(value) - allowed or ("location_gid" in value and "id" in value and value["location_gid"] != value["id"]) or ("active" in value and "isActive" in value and value["active"] != value["isActive"]) or ("cache_present" in value and "present" in value and value["cache_present"] != value["present"]):
            raise ValueError("location_evidence contains conflicting or unsupported fields")
        return cls(
            value.get("location_gid", value.get("id")),
            value.get("store_id"),
            value.get("active", value.get("isActive")),
            value.get("cache_present", value.get("present", False)),
            value.get("source", "core_location_cache"),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "location_gid": self.location_gid,
            "store_id": self.store_id,
            "active": self.active,
            "cache_present": self.cache_present,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class NotificationEvidence:
    effective: bool
    default_enabled: bool
    confirmed: bool
    source: str = "store_settings"

    def __post_init__(self) -> None:
        _boolean(self.effective, "notification.effective")
        _boolean(self.default_enabled, "notification.default_enabled")
        _boolean(self.confirmed, "notification.confirmed")
        _text(self.source, "notification.source", max_length=128)

    @property
    def expected_effective(self) -> bool:
        return self.default_enabled and self.confirmed

    def as_dict(self) -> dict[str, Any]:
        return {"effective": self.effective, "default_enabled": self.default_enabled, "confirmed": self.confirmed, "source": self.source}

    @classmethod
    def from_value(cls, value: "NotificationEvidence | Mapping[str, Any] | None") -> "NotificationEvidence | None":
        if value is None:
            return None
        if isinstance(value, cls):
            return value
        if not isinstance(value, Mapping):
            raise TypeError("notification_evidence must be an object")
        allowed = {"effective", "notify_customer", "default_enabled", "notification_default_enabled", "confirmed", "notification_confirmed", "source"}
        if set(value) - allowed:
            raise ValueError("notification_evidence contains an unsupported field")
        effective = value.get("effective", value.get("notify_customer"))
        default_enabled = value.get("default_enabled", value.get("notification_default_enabled"))
        confirmed = value.get("confirmed", value.get("notification_confirmed"))
        if "effective" in value and "notify_customer" in value and value["effective"] != value["notify_customer"]:
            raise ValueError("notification effective aliases disagree")
        if "default_enabled" in value and "notification_default_enabled" in value and value["default_enabled"] != value["notification_default_enabled"]:
            raise ValueError("notification default aliases disagree")
        if "confirmed" in value and "notification_confirmed" in value and value["confirmed"] != value["notification_confirmed"]:
            raise ValueError("notification confirmation aliases disagree")
        return cls(effective, default_enabled, confirmed, value.get("source", "store_settings"))


def notification_evidence(notify_customer: bool, *, default_enabled: bool, confirmed: bool, source: str = "store_settings") -> NotificationEvidence:
    return NotificationEvidence(notify_customer, default_enabled, confirmed, source)


def _tracking_info(value: Any, field_name: str) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping) or not value:
        raise ValueError(f"{field_name} must be a non-empty object")
    allowed = {"company", "number", "numbers", "url", "urls"}
    if set(value) - allowed:
        raise ValueError(f"{field_name} contains an unsupported field")
    result: dict[str, Any] = {}
    for key, item in value.items():
        if key in {"numbers", "urls"}:
            if not isinstance(item, Sequence) or isinstance(item, (str, bytes, Mapping)) or not item or len(item) > MAX_TRACKING_ITEMS or any(not isinstance(entry, str) or not entry.strip() or len(entry) > 2048 for entry in item):
                raise ValueError(f"{field_name}.{key} must be a bounded non-empty string list")
            result[key] = list(item)
        else:
            result[key] = _text(item, f"{field_name}.{key}")
    return result


def _line_items(value: Any) -> Any:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, Mapping)) or not value or len(value) > MAX_FULFILLMENT_ORDERS:
        raise ValueError("line_items_by_fulfillment_order must be a bounded non-empty sequence")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    seen_fulfillment_orders: set[str] = set()
    count = 0
    for row in value:
        if not isinstance(row, Mapping) or set(row) != {"fulfillmentOrderId", "fulfillmentOrderLineItems"}:
            raise ValueError("fulfillment-order rows must use the V1 keys exactly")
        entries = row["fulfillmentOrderLineItems"]
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes, Mapping)) or not entries or len(entries) > MAX_LINE_ITEMS:
            raise ValueError("fulfillmentOrderLineItems must be a bounded non-empty sequence")
        normalized: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, Mapping) or set(entry) != {"id", "quantity"}:
                raise ValueError("fulfillment-order line items must use id and quantity only")
            line_id = _gid(entry["id"], "FulfillmentOrderLineItem", "fulfillmentOrderLineItems.id")
            if line_id in seen or isinstance(entry["quantity"], bool) or not isinstance(entry["quantity"], int) or entry["quantity"] < 1:
                raise ValueError("fulfillment-order lines must be unique positive quantities")
            seen.add(line_id)
            normalized.append({"id": line_id, "quantity": entry["quantity"]})
            count += 1
        fulfillment_order_gid = _gid(row["fulfillmentOrderId"], "FulfillmentOrder", "fulfillmentOrderId")
        if fulfillment_order_gid in seen_fulfillment_orders:
            raise ValueError("fulfillment-order rows must be unique")
        seen_fulfillment_orders.add(fulfillment_order_gid)
        rows.append({"fulfillmentOrderId": fulfillment_order_gid, "fulfillmentOrderLineItems": normalized})
    if count > MAX_LINE_ITEMS:
        raise ValueError("fulfillment line-item count exceeds its bound")
    return freeze_value(rows)


def _remaining(value: Any) -> Any:
    if value is None:
        return {}
    if not isinstance(value, Mapping) or len(value) > MAX_LINE_ITEMS:
        raise ValueError("remaining_before must be a bounded object")
    result: dict[str, int] = {}
    for line_id, quantity in value.items():
        _gid(line_id, "FulfillmentOrderLineItem", "remaining_before.id")
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
            raise ValueError("remaining_before quantities must be non-negative integers")
        result[line_id] = quantity
    return freeze_value(result)


def _facts(value: Any) -> Any:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, Mapping)) or len(value) > MAX_FULFILLMENT_ORDERS or any(not isinstance(item, Mapping) for item in value):
        raise ValueError("fulfillment_order_observations must be a bounded object sequence")
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in value:
        if set(item) != {"id", "status", "supportedActions", "assignedLocation", "line_items"}:
            raise ValueError("fulfillment-order observations must use the exact normalized fields")
        fo_gid = _gid(item["id"], "FulfillmentOrder", "fulfillment_order_observations.id")
        if fo_gid in seen:
            raise ValueError("fulfillment-order observations must have unique IDs")
        seen.add(fo_gid)
        status = item["status"]
        if not isinstance(status, str) or not status.strip() or len(status) > 64:
            raise ValueError("fulfillment-order observation status must be a bounded string")
        actions = item["supportedActions"]
        if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes, Mapping)) or len(actions) > 16:
            raise ValueError("supportedActions must be a bounded sequence")
        normalized_actions: list[dict[str, str]] = []
        for action in actions:
            if not isinstance(action, Mapping) or set(action) != {"action"} or not isinstance(action["action"], str) or not action["action"].strip():
                raise ValueError("supportedActions entries must contain one non-empty action string")
            normalized_actions.append({"action": action["action"]})
        assigned = item["assignedLocation"]
        if assigned is not None:
            if not isinstance(assigned, Mapping) or set(assigned) != {"location"}:
                raise ValueError("assignedLocation must contain only location")
            location = assigned["location"]
            if location is not None:
                if not isinstance(location, Mapping) or set(location) != {"id"}:
                    raise ValueError("assignedLocation.location must contain only id")
                _gid(location["id"], "Location", "assignedLocation.location.id")
        line_items = item["line_items"]
        if not isinstance(line_items, Sequence) or isinstance(line_items, (str, bytes, Mapping)) or not line_items or len(line_items) > MAX_LINE_ITEMS:
            raise ValueError("line_items must be a bounded non-empty sequence")
        normalized_lines: list[dict[str, Any]] = []
        line_seen: set[str] = set()
        for line in line_items:
            if not isinstance(line, Mapping) or set(line) != {"id", "remainingQuantity"}:
                raise ValueError("line_items entries must use id and remainingQuantity exactly")
            line_gid = _gid(line["id"], "FulfillmentOrderLineItem", "line_items.id")
            if line_gid in line_seen:
                raise ValueError("line_items IDs must be unique per FulfillmentOrder")
            line_seen.add(line_gid)
            quantity = line["remainingQuantity"]
            if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 0:
                raise ValueError("remainingQuantity must be a non-negative integer")
            normalized_lines.append({"id": line_gid, "remainingQuantity": quantity})
        normalized.append({
            "id": fo_gid,
            "status": status,
            "supportedActions": normalized_actions,
            "assignedLocation": freeze_value(dict(assigned)) if assigned is not None else None,
            "line_items": normalized_lines,
        })
    return freeze_value(normalized)


@dataclass(frozen=True, slots=True)
class FulfillmentMutationPayload:
    store_id: int
    company_id: int
    expected_connection_generation: int
    expected_store_identity: str
    operation: str | FulfillmentMutationOperation
    picking_id: int
    target_gid: str | None = None
    order_gid: str | None = None
    fulfillment_gid: str | None = None
    line_items_by_fulfillment_order: Sequence[Mapping[str, Any]] = ()
    tracking_info: Mapping[str, Any] | None = None
    tracking_info_input: Mapping[str, Any] | None = None
    notify_customer: bool = False
    notification_evidence: NotificationEvidence | Mapping[str, Any] | None = None
    notification_default_enabled: bool | None = None
    notification_confirmed: bool | None = None
    expected_configuration_generation: int = 0
    current_connection_generation: int | None = None
    current_configuration_generation: int | None = None
    current_store_identity: str | None = None
    current_store_id: int | None = None
    current_company_id: int | None = None
    runtime_mode: str = FULFILLMENT_RUNTIME_MODE
    store_state: str = "connected"
    run_state: str = "admitted"
    cancel_requested: bool = False
    fulfillment_domain_enabled: bool = True
    binding_evidence: FulfillmentBindingEvidence | Mapping[str, Any] | None = None
    location_evidence: FulfillmentLocationEvidence | Mapping[str, Any] | None = None
    fulfillment_order_observations: Sequence[Mapping[str, Any]] = ()
    eligibility_snapshot_complete: bool = False
    eligibility_snapshot_store_identity: str | None = None
    eligibility_snapshot_order_gid: str | None = None
    remaining_before: Mapping[str, int] | None = None
    idempotency_key: str | None = None
    requested_scope_key: str | None = None
    snapshot_taken_at: datetime | str | None = None
    inconclusive_read_count: int = 0

    def __post_init__(self) -> None:
        _positive_int(self.store_id, "store_id")
        _positive_int(self.company_id, "company_id")
        _positive_int(self.picking_id, "picking_id")
        _nonnegative_int(self.expected_connection_generation, "expected_connection_generation")
        _nonnegative_int(self.expected_configuration_generation, "expected_configuration_generation")
        for name in ("current_connection_generation", "current_configuration_generation"):
            value = getattr(self, name)
            if value is not None:
                _nonnegative_int(value, name)
        _domain(self.expected_store_identity, "expected_store_identity")
        if self.current_store_identity is not None:
            _domain(self.current_store_identity, "current_store_identity")
        for name in ("current_store_id", "current_company_id"):
            value = getattr(self, name)
            if value is not None:
                _positive_int(value, name)
        operation = _operation(self.operation)
        object.__setattr__(self, "operation", operation)
        target = self.target_gid or self.fulfillment_gid
        if target is None:
            raise ValueError("target_gid is required")
        _gid(target, "FulfillmentOrder" if operation == FULFILLMENT_CREATE_OPERATION else "Fulfillment", "target_gid")
        object.__setattr__(self, "target_gid", target)
        if self.order_gid is not None:
            _gid(self.order_gid, "Order", "order_gid")
        if self.fulfillment_gid is not None:
            _gid(self.fulfillment_gid, "Fulfillment", "fulfillment_gid")
        if operation == FULFILLMENT_CREATE_OPERATION and self.order_gid is None:
            raise ValueError("order_gid is required for fulfillment create")
        if operation == FULFILLMENT_TRACKING_UPDATE_OPERATION:
            if self.order_gid is None:
                raise ValueError("order_gid is required for fulfillment tracking update")
            if self.fulfillment_gid is None:
                object.__setattr__(self, "fulfillment_gid", target)
        _boolean(self.notify_customer, "notify_customer")
        evidence = NotificationEvidence.from_value(self.notification_evidence)
        if evidence is None and self.notification_default_enabled is not None and self.notification_confirmed is not None:
            evidence = NotificationEvidence(self.notify_customer, self.notification_default_enabled, self.notification_confirmed)
        if evidence is not None:
            object.__setattr__(self, "notification_evidence", evidence)
        for name in ("notification_default_enabled", "notification_confirmed"):
            value = getattr(self, name)
            if value is not None:
                _boolean(value, name)
        if evidence is not None and self.notification_default_enabled is not None and evidence.default_enabled != self.notification_default_enabled:
            raise ValueError("notification default evidence disagrees with the explicit setting")
        if evidence is not None and self.notification_confirmed is not None and evidence.confirmed != self.notification_confirmed:
            raise ValueError("notification confirmation evidence disagrees with the explicit setting")
        object.__setattr__(self, "line_items_by_fulfillment_order", _line_items(self.line_items_by_fulfillment_order) if self.line_items_by_fulfillment_order else ())
        object.__setattr__(self, "tracking_info", freeze_value(_tracking_info(self.tracking_info, "tracking_info")) if self.tracking_info is not None else None)
        object.__setattr__(self, "tracking_info_input", freeze_value(_tracking_info(self.tracking_info_input, "tracking_info_input")) if self.tracking_info_input is not None else None)
        binding = FulfillmentBindingEvidence.from_value(self.binding_evidence)
        if binding is not None:
            object.__setattr__(self, "binding_evidence", binding)
        location = FulfillmentLocationEvidence.from_value(self.location_evidence)
        if location is not None:
            object.__setattr__(self, "location_evidence", location)
        object.__setattr__(self, "fulfillment_order_observations", _facts(self.fulfillment_order_observations))
        object.__setattr__(self, "remaining_before", _remaining(self.remaining_before))
        if self.runtime_mode not in FULFILLMENT_RUNTIME_MODES or self.store_state != "connected" or self.run_state not in ACTIVE_RUN_STATES:
            raise ValueError("runtime/store/run state is not allowed")
        _boolean(self.cancel_requested, "cancel_requested")
        _boolean(self.fulfillment_domain_enabled, "fulfillment_domain_enabled")
        _boolean(self.eligibility_snapshot_complete, "eligibility_snapshot_complete")
        if self.eligibility_snapshot_store_identity is not None:
            _domain(self.eligibility_snapshot_store_identity, "eligibility_snapshot_store_identity")
        if self.eligibility_snapshot_order_gid is not None:
            _gid(self.eligibility_snapshot_order_gid, "Order", "eligibility_snapshot_order_gid")
        if operation == FULFILLMENT_CREATE_OPERATION:
            if self.target_gid not in {row["fulfillmentOrderId"] for row in self.line_items_by_fulfillment_order}:
                raise ValueError("target_gid must identify one selected FulfillmentOrder")
        elif self.target_gid != self.fulfillment_gid:
            raise ValueError("target_gid and fulfillment_gid must identify the same fulfillment")
        for name in ("idempotency_key", "requested_scope_key"):
            value = getattr(self, name)
            if value is not None:
                _text(value, name, max_length=512)
        if self.snapshot_taken_at is not None and not isinstance(self.snapshot_taken_at, (datetime, str)):
            raise TypeError("snapshot_taken_at must be a timestamp")
        _nonnegative_int(self.inconclusive_read_count, "inconclusive_read_count")

    @property
    def operation_scope_key(self) -> str:
        return derive_fulfillment_operation_scope(self.operation, self.store_id, self.picking_id, self.target_gid or "")

    @property
    def shopify_operation_key(self) -> str:
        return shopify_operation_key(self.operation)

    @property
    def notification(self) -> NotificationEvidence | None:
        return NotificationEvidence.from_value(self.notification_evidence)

    @property
    def binding(self) -> FulfillmentBindingEvidence | None:
        return FulfillmentBindingEvidence.from_value(self.binding_evidence)

    @property
    def location(self) -> FulfillmentLocationEvidence | None:
        return FulfillmentLocationEvidence.from_value(self.location_evidence)

    def business_intent(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "mutation_domain": self.operation,
            "store_id": self.store_id,
            "company_id": self.company_id,
            "picking_id": self.picking_id,
            "operation_scope_key": self.operation_scope_key,
            "notify_customer": self.notify_customer,
            "notification_evidence": self.notification.as_dict() if self.notification else None,
            "binding_evidence": self.binding.as_dict() if self.binding else None,
        }
        if self.operation == FULFILLMENT_CREATE_OPERATION:
            result.update({
                "order_gid": self.order_gid,
                "target_fo_gid": self.target_gid,
                "fulfillment_order_gids": [row["fulfillmentOrderId"] for row in self.line_items_by_fulfillment_order],
                "line_items_by_fo": to_plain(self.line_items_by_fulfillment_order),
                "tracking_info": to_plain(self.tracking_info),
            })
        else:
            result.update({
                "order_gid": self.order_gid,
                "fulfillment_gid": self.fulfillment_gid or self.target_gid,
                "tracking_info": to_plain(self.tracking_info_input),
            })
        return result

    def preconditions_snapshot(self) -> dict[str, Any]:
        # ``snapshot_taken_at`` is audit evidence, not identity material.  It
        # must never make an otherwise identical command a new mutation.
        return {
            "store_id": self.store_id,
            "company_id": self.company_id,
            "expected_connection_generation": self.expected_connection_generation,
            "current_connection_generation": self.current_connection_generation,
            "expected_configuration_generation": self.expected_configuration_generation,
            "current_configuration_generation": self.current_configuration_generation,
            "expected_store_identity": self.expected_store_identity,
            "current_store_identity": self.current_store_identity,
            "runtime_mode": self.runtime_mode,
            "notify_customer": self.notify_customer,
            "notification_evidence": self.notification.as_dict() if self.notification else None,
            "binding_evidence": self.binding.as_dict() if self.binding else None,
            "location_evidence": self.location.as_dict() if self.location else None,
            "eligibility_snapshot_complete": self.eligibility_snapshot_complete,
            "eligibility_snapshot_store_identity": self.eligibility_snapshot_store_identity,
            "eligibility_snapshot_order_gid": self.eligibility_snapshot_order_gid,
            "remaining_before": to_plain(self.remaining_before),
        }

    def as_dict(self) -> dict[str, Any]:
        return to_plain({"store_id": self.store_id, "company_id": self.company_id, "expected_connection_generation": self.expected_connection_generation, "expected_configuration_generation": self.expected_configuration_generation, "current_connection_generation": self.current_connection_generation, "current_configuration_generation": self.current_configuration_generation, "expected_store_identity": self.expected_store_identity, "current_store_identity": self.current_store_identity, "runtime_mode": self.runtime_mode, "operation": self.operation, "shopify_operation_key": self.shopify_operation_key, "picking_id": self.picking_id, "target_gid": self.target_gid, "order_gid": self.order_gid, "fulfillment_gid": self.fulfillment_gid, "operation_scope_key": self.operation_scope_key, "line_items_by_fulfillment_order": self.line_items_by_fulfillment_order, "tracking_info": self.tracking_info, "tracking_info_input": self.tracking_info_input, "notify_customer": self.notify_customer, "notification_evidence": self.notification.as_dict() if self.notification else None, "binding_evidence": self.binding.as_dict() if self.binding else None, "location_evidence": self.location.as_dict() if self.location else None, "fulfillment_order_observations": self.fulfillment_order_observations, "eligibility_snapshot_complete": self.eligibility_snapshot_complete, "eligibility_snapshot_store_identity": self.eligibility_snapshot_store_identity, "eligibility_snapshot_order_gid": self.eligibility_snapshot_order_gid, "remaining_before": self.remaining_before, "idempotency_key": self.idempotency_key, "snapshot_taken_at": self.snapshot_taken_at.isoformat() if isinstance(self.snapshot_taken_at, datetime) else self.snapshot_taken_at})


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    allowed: bool
    reason: str | AdmissionReason
    message: str
    operation_scope_key: str | None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        reason = self.reason.value if isinstance(self.reason, AdmissionReason) else self.reason
        if not isinstance(reason, str) or not _TOKEN.fullmatch(reason):
            raise ValueError("admission reason must be a safe token")
        _boolean(self.allowed, "admission.allowed")
        _text(self.message, "admission.message")
        if self.operation_scope_key is not None:
            _text(self.operation_scope_key, "operation_scope_key", max_length=512)
        if not isinstance(self.details, Mapping):
            raise TypeError("admission.details must be an object")
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "details", freeze_value(dict(self.details)))

    @property
    def code(self) -> str:
        return self.reason

    @property
    def is_admitted(self) -> bool:
        return self.allowed

    def as_dict(self) -> dict[str, Any]:
        return to_plain({"allowed": self.allowed, "reason": self.reason, "message": self.message, "operation_scope_key": self.operation_scope_key, "details": self.details})


def canonical_fulfillment_fingerprint(payload: FulfillmentMutationPayload) -> str:
    if not isinstance(payload, FulfillmentMutationPayload):
        raise TypeError("payload must be FulfillmentMutationPayload")
    material = {"contract_version": 1, "business_intent": payload.business_intent(), "preconditions_snapshot": payload.preconditions_snapshot()}
    encoded = json.dumps(to_plain(freeze_value(material)), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


__all__ = [
    "ACTIVE_RUN_STATES", "AdmissionDecision", "AdmissionReason", "CREATE_FULFILLMENT_ACTION", "FO_BLOCKING_STATUSES", "FO_ELIGIBLE_STATUSES", "FULFILLMENT_ALL_RUNTIME_MODE", "FULFILLMENT_CREATE_OPERATION", "FULFILLMENT_RUNTIME_MODE", "FULFILLMENT_RUNTIME_MODES", "FULFILLMENT_TRACKING_UPDATE_OPERATION", "FulfillmentBindingEvidence", "FulfillmentLocationEvidence", "FulfillmentMutationOperation", "FulfillmentMutationPayload", "NotificationEvidence", "SHOPIFY_FULFILLMENT_CREATE_OPERATION", "SHOPIFY_FULFILLMENT_TRACKING_UPDATE_OPERATION", "canonical_fulfillment_fingerprint", "derive_fulfillment_operation_scope", "notification_evidence", "shopify_operation_key",
]
