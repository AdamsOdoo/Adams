"""Conservative, pure readback decisions for P14 fulfillment writes."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any

from shopify_connector_core.domain.immutability import freeze_value, to_plain

from .fulfillment_mutation import (
    FULFILLMENT_CREATE_OPERATION,
    FULFILLMENT_TRACKING_UPDATE_OPERATION,
    MAX_INCONCLUSIVE_READS,
    MAX_TRACKING_ITEMS,
    FulfillmentMutationPayload,
    _gid,
    canonical_fulfillment_fingerprint,
)


_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ReadbackOutcome(str, Enum):
    APPLIED = "applied"
    NOT_APPLIED = "not_applied"
    INCONCLUSIVE = "inconclusive"


def _operation(value: Any) -> str:
    if hasattr(value, "value"):
        value = value.value
    if value not in (FULFILLMENT_CREATE_OPERATION, FULFILLMENT_TRACKING_UPDATE_OPERATION):
        raise ValueError("unsupported fulfillment readback operation")
    return value


def _map(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be an object")
    return freeze_value(dict(value))


def _tracking(value: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Normalize V1 input and Shopify response without coercing values."""
    if value is None:
        return ()
    if isinstance(value, Mapping):
        rows = (value,)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, Mapping)):
        rows = value
    else:
        raise ValueError("tracking data must be an object or object sequence")
    result: list[tuple[str, tuple[str, ...]]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise ValueError("tracking data entries must be objects")
        allowed = {"company", "number", "numbers", "url", "urls"}
        if set(row) - allowed:
            raise ValueError("tracking data contains an unsupported field")
        for key in ("number", "numbers", "url", "urls", "company"):
            item = row.get(key)
            if item is None:
                continue
            if key in {"numbers", "urls"}:
                if not isinstance(item, Sequence) or isinstance(item, (str, bytes, Mapping)) or not item:
                    raise ValueError("tracking list must be a non-empty sequence")
                values = item
            else:
                if not isinstance(item, str) or not item.strip():
                    raise ValueError("tracking scalar must be a non-empty string")
                values = (item,)
            if len(values) > MAX_TRACKING_ITEMS or any(not isinstance(entry, str) or not entry.strip() or len(entry) > 2048 for entry in values):
                raise ValueError("tracking values must remain strings")
            result.append((key, tuple(values)))
    return tuple(sorted(result))


def _fulfilled_lines(observation: Mapping[str, Any]) -> Mapping[str, int] | None:
    for key in ("remaining_after", "remaining", "fulfillment_remaining"):
        value = observation.get(key)
        if isinstance(value, Mapping):
            result: dict[str, int] = {}
            for line_id, quantity in value.items():
                if isinstance(line_id, str) and isinstance(quantity, int) and not isinstance(quantity, bool) and quantity >= 0:
                    try:
                        _gid(line_id, "FulfillmentOrderLineItem", "remaining_after.id")
                    except ValueError:
                        continue
                    result[line_id] = quantity
            if len(result) == len(value):
                return result
    return None


@dataclass(frozen=True, slots=True)
class FulfillmentReadback:
    """A redacted certainty decision; it never authorizes a replay."""

    operation: str
    outcome: str | ReadbackOutcome
    operation_scope_key: str
    reason: str
    message: str
    intent_fingerprint: str = ""
    safe_to_replay: bool = False
    exact_identity: bool = False
    fulfillment_gid: str | None = None
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation", _operation(self.operation))
        try:
            outcome = self.outcome.value if isinstance(self.outcome, ReadbackOutcome) else ReadbackOutcome(self.outcome).value
        except (TypeError, ValueError) as exc:
            raise ValueError("unsupported fulfillment readback outcome") from exc
        object.__setattr__(self, "outcome", outcome)
        if not isinstance(self.operation_scope_key, str) or not self.operation_scope_key.strip():
            raise ValueError("operation_scope_key must be non-empty")
        for field_name in ("reason", "message"):
            if not isinstance(getattr(self, field_name), str) or not getattr(self, field_name).strip():
                raise ValueError(f"{field_name} must be non-empty")
        if not isinstance(self.safe_to_replay, bool) or not isinstance(self.exact_identity, bool):
            raise TypeError("readback flags must be bool")
        if not isinstance(self.intent_fingerprint, str) or not _SHA256.fullmatch(self.intent_fingerprint):
            raise ValueError("intent_fingerprint must be lowercase SHA-256")
        if self.safe_to_replay:
            raise ValueError("fulfillment readback never authorizes blind replay")
        if self.fulfillment_gid is not None:
            _gid(self.fulfillment_gid, "Fulfillment", "fulfillment_gid")
        object.__setattr__(self, "evidence", _map(self.evidence, "evidence"))

    @property
    def verdict(self) -> str:
        return self.outcome

    @property
    def replay_allowed(self) -> bool:
        return False

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "operation": self.operation,
            "outcome": self.outcome,
            "verdict": self.outcome,
            "operation_scope_key": self.operation_scope_key,
            "reason": self.reason,
            "message": self.message,
            "intent_fingerprint": self.intent_fingerprint,
            "safe_to_replay": False,
            "exact_identity": self.exact_identity,
            "fulfillment_gid": self.fulfillment_gid,
            "evidence": self.evidence,
        })


ReadbackDecision = FulfillmentReadback


def _decision(payload: FulfillmentMutationPayload, outcome: ReadbackOutcome, reason: str, message: str, *, exact: bool = False, fulfillment_gid: str | None = None, count: int | None = None, **evidence: Any) -> FulfillmentReadback:
    notification = payload.notification
    evidence.update({
        "notify_customer": payload.notify_customer,
        "notification_evidence": notification.as_dict() if notification else None,
    })
    if count is not None:
        evidence["inconclusive_read_count"] = count
        if count >= MAX_INCONCLUSIVE_READS:
            evidence["manual_review"] = True
    return FulfillmentReadback(payload.operation, outcome, payload.operation_scope_key, reason, message, intent_fingerprint=canonical_fulfillment_fingerprint(payload), exact_identity=exact, fulfillment_gid=fulfillment_gid, evidence=evidence)


def _webhook_only(observation: Mapping[str, Any]) -> bool:
    source = observation.get("source", observation.get("evidence_source"))
    independent = observation.get("independent_readback")
    if independent is not None and not isinstance(independent, bool):
        return True
    return independent is not True or bool(observation.get("webhook_only") or source in {"webhook", "webhook_hint"})


def _readback_source_reason(observation: Mapping[str, Any]) -> tuple[str, str]:
    source = observation.get("source", observation.get("evidence_source"))
    if source in {"webhook", "webhook_hint"} or observation.get("webhook_only"):
        return "webhook_hint_only", "A fulfillment webhook is only a hint; an independent readback is required."
    return "independent_readback_missing", "A readback must be explicitly marked as an independent Shopify read."


def _exact_line_effect(payload: FulfillmentMutationPayload, observation: Mapping[str, Any]) -> tuple[bool, str]:
    before = payload.remaining_before
    after = _fulfilled_lines(observation)
    requested = {entry["id"]: entry["quantity"] for row in payload.line_items_by_fulfillment_order for entry in row["fulfillmentOrderLineItems"]}
    if not before or after is None:
        return False, "The readback lacks exact before/after remaining-quantity evidence."
    for line_id, quantity in requested.items():
        if line_id not in before or line_id not in after or after[line_id] != before[line_id] - quantity:
            return False, "The readback does not prove the requested line quantity effect."
    return True, ""


def _gid_set(value: Any, kind: str) -> set[str] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, Mapping)):
        return None
    result: set[str] = set()
    for item in value:
        try:
            result.add(_gid(item, kind, "readback identity"))
        except ValueError:
            return None
    return result


def _create(payload: FulfillmentMutationPayload, observation: Mapping[str, Any], count: int | None) -> FulfillmentReadback:
    if _webhook_only(observation):
        reason, message = _readback_source_reason(observation)
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, reason, message, count=count)
    if observation.get("store_identity") != payload.expected_store_identity:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "store_identity_mismatch", "Readback did not prove the expected Shopify store.", observed_store_identity=observation.get("store_identity"), count=count)
    observed_order = observation.get("order_gid", observation.get("order_id"))
    if observed_order != payload.order_gid:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "order_identity_mismatch", "Readback did not prove the requested Shopify order.", count=count)
    rows = observation.get("fulfillments", observation.get("nodes"))
    if rows is None and isinstance(observation.get("fulfillment"), Mapping):
        rows = (observation["fulfillment"],)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, Mapping)):
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillments_missing", "The bounded fulfillment list is missing; absence is not proof.", count=count)
    if len(rows) > 250:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_list_too_large", "The fulfillment readback exceeded its bounded result size.", count=count)
    observed_gid = observation.get("fulfillment_gid")
    try:
        _gid(observed_gid, "Fulfillment", "fulfillment_gid")
    except ValueError:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_identity_missing", "The create readback must identify the exact created fulfillment GID.", count=count)
    selected_fo_ids = {row["fulfillmentOrderId"] for row in payload.line_items_by_fulfillment_order}
    observed_fo_ids = observation.get("fulfillment_order_ids", observation.get("fulfillmentOrderIds"))
    if _gid_set(observed_fo_ids, "FulfillmentOrder") != selected_fo_ids:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_order_identity_missing", "The create readback did not prove the exact selected FulfillmentOrders.", count=count)
    related_rows = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        row_fo_ids = row.get("fulfillmentOrderIds", row.get("fulfillment_order_ids"))
        if row_fo_ids is None and row.get("fulfillmentOrderId") is not None:
            row_fo_ids = (row.get("fulfillmentOrderId"),)
        row_gid_set = _gid_set(row_fo_ids, "FulfillmentOrder")
        if row_gid_set is not None and row_gid_set & selected_fo_ids:
            related_rows.append(row)
    if len(related_rows) > 1:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_match_ambiguous", "More than one fulfillment claims the selected FulfillmentOrders.", match_count=len(related_rows), count=count)
    matches = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        if row.get("id") == observed_gid:
            row_fo_ids = row.get("fulfillmentOrderIds", row.get("fulfillment_order_ids"))
            if row_fo_ids is None and row.get("fulfillmentOrderId") is not None:
                row_fo_ids = (row.get("fulfillmentOrderId"),)
            if row_fo_ids is not None and _gid_set(row_fo_ids, "FulfillmentOrder") != selected_fo_ids:
                continue
            matches.append(row)
    if len(matches) != 1:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_match_ambiguous" if len(matches) > 1 else "fulfillment_not_proven", "Readback did not prove exactly one connector fulfillment for this intent.", match_count=len(matches), count=count)
    match = matches[0]
    gid = match.get("id")
    if match.get("status") != "SUCCESS":
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_status_unexplained", "The matched fulfillment is not in the V1 SUCCESS state.", exact=True, fulfillment_gid=gid, count=count)
    desired_tracking = _tracking(payload.tracking_info)
    try:
        actual_tracking = _tracking(match.get("trackingInfo", match.get("tracking_info")))
    except (TypeError, ValueError):
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "tracking_shape_invalid", "The fulfillment readback tracking shape is malformed.", exact=True, fulfillment_gid=gid, count=count)
    if desired_tracking:
        if actual_tracking != desired_tracking:
            return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "tracking_mismatch", "The exact fulfillment exists but tracking evidence differs from the intent.", exact=True, fulfillment_gid=gid, count=count)
    exact_lines, line_message = _exact_line_effect(payload, observation)
    if not exact_lines:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "line_effect_unexplained", line_message, exact=True, fulfillment_gid=gid, count=count)
    return _decision(payload, ReadbackOutcome.APPLIED, "fulfillment_observed", "The independent readback proves the requested fulfillment exactly.", exact=True, fulfillment_gid=gid, count=count, remote_status=match.get("status"), tracking_observed=bool(actual_tracking))


def _tracking_update(payload: FulfillmentMutationPayload, observation: Mapping[str, Any], count: int | None) -> FulfillmentReadback:
    if _webhook_only(observation):
        reason, message = _readback_source_reason(observation)
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, reason, message, count=count)
    if observation.get("store_identity") != payload.expected_store_identity:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "store_identity_mismatch", "Readback did not prove the expected Shopify store.", count=count)
    if observation.get("order_gid", observation.get("order_id")) != payload.order_gid:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "order_identity_mismatch", "Readback did not prove the requested Shopify order.", count=count)
    node = observation.get("fulfillment", observation)
    try:
        node_gid = node.get("id") if isinstance(node, Mapping) else None
        _gid(node_gid, "Fulfillment", "fulfillment.id")
    except ValueError:
        node_gid = None
    if node_gid != payload.fulfillment_gid:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_identity_mismatch", "Readback did not prove the exact fulfillment binding.", count=count)
    if not isinstance(node.get("status"), str) or not node.get("status").strip():
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_status_missing", "Readback did not include an exact fulfillment status.", count=count)
    if node.get("status") == "CANCELLED":
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "fulfillment_cancelled", "A cancelled fulfillment cannot prove a tracking update.", exact=True, fulfillment_gid=payload.fulfillment_gid, count=count)
    expected = _tracking(payload.tracking_info_input)
    try:
        actual = _tracking(node.get("trackingInfo", node.get("tracking_info")))
    except (TypeError, ValueError):
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "tracking_shape_invalid", "The fulfillment readback tracking shape is malformed.", exact=True, fulfillment_gid=payload.fulfillment_gid, count=count)
    if actual != expected:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "tracking_not_observed", "The exact fulfillment readback does not contain the requested tracking evidence.", exact=True, fulfillment_gid=payload.fulfillment_gid, count=count)
    return _decision(payload, ReadbackOutcome.APPLIED, "tracking_observed", "The independent readback proves the requested tracking state.", exact=True, fulfillment_gid=payload.fulfillment_gid, count=count, tracking_observed=True)


def evaluate_fulfillment_readback(payload: FulfillmentMutationPayload, observation: Mapping[str, Any] | None, *, inconclusive_count: int | None = None) -> FulfillmentReadback:
    if not isinstance(payload, FulfillmentMutationPayload):
        raise TypeError("payload must be FulfillmentMutationPayload")
    count = payload.inconclusive_read_count if inconclusive_count is None else inconclusive_count
    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
        raise ValueError("inconclusive_count must be a non-negative integer")
    if observation is None:
        return _decision(payload, ReadbackOutcome.INCONCLUSIVE, "observation_missing", "No independent fulfillment readback was returned; no replay is safe.", count=count)
    observation = _map(observation, "observation")
    if payload.operation == FULFILLMENT_CREATE_OPERATION:
        return _create(payload, observation, count)
    return _tracking_update(payload, observation, count)


__all__ = [
    "FulfillmentReadback",
    "ReadbackDecision",
    "ReadbackOutcome",
    "evaluate_fulfillment_readback",
]
