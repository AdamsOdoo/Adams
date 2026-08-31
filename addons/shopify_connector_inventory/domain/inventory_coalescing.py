"""Pure last-value-wins coalescing for inventory pair events.

The V1 service writes the newest Odoo available quantity to one pending field
and admits no second non-terminal pair job.  This module describes that
decision without reading or writing Odoo and without deciding whether a
remote mutation is safe after an uncertain response.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from shopify_connector_core.domain.immutability import freeze_value, to_plain

from .inventory_admission import AdmissionReason
from .inventory_mutation import CoalescingAction, InventoryMutationPayload, _timestamp, integral_quantity


@dataclass(frozen=True, slots=True)
class CoalescingDecision:
    """Last-value-wins decision for rapid local stock changes."""

    action: str | CoalescingAction
    operation_scope_key: str
    effective_target_quantity: int | None
    reason: str
    safe_to_send: bool
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        try:
            action = self.action.value if isinstance(self.action, CoalescingAction) else CoalescingAction(self.action).value
        except (TypeError, ValueError) as exc:
            raise ValueError("unsupported coalescing action") from exc
        if not isinstance(self.operation_scope_key, str) or not self.operation_scope_key.strip():
            raise ValueError("operation_scope_key must be non-empty")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("coalescing.reason must be non-empty")
        if self.effective_target_quantity is not None:
            if isinstance(self.effective_target_quantity, bool) or not isinstance(self.effective_target_quantity, int) or self.effective_target_quantity < 0:
                raise ValueError("effective_target_quantity must be a non-negative integer")
        if not isinstance(self.safe_to_send, bool):
            raise TypeError("coalescing.safe_to_send must be bool")
        object.__setattr__(self, "action", action)
        object.__setattr__(self, "details", freeze_value(dict(self.details)))

    @property
    def code(self) -> str:
        return self.action

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "action": self.action,
            "operation_scope_key": self.operation_scope_key,
            "effective_target_quantity": self.effective_target_quantity,
            "reason": self.reason,
            "safe_to_send": self.safe_to_send,
            "details": self.details,
        })


def decide_inventory_coalescing(
    payload: InventoryMutationPayload,
    *,
    active_operation_scopes: Sequence[str] = (),
    pending_target_quantity: int | float | None = None,
    current_available: int | None = None,
    last_pushed_available: int | float | None = None,
    last_pushed_at: datetime | str | bool | None = None,
    remote_uncertain: bool = False,
) -> CoalescingDecision:
    """Coalesce duplicate pair work without ever replaying uncertain writes."""

    if not isinstance(payload, InventoryMutationPayload):
        raise TypeError("payload must be InventoryMutationPayload")
    scope = payload.operation_scope_key
    target = payload.normalized_target_quantity
    if remote_uncertain:
        return CoalescingDecision(
            CoalescingAction.REJECT, scope, target,
            "An uncertain remote outcome requires exact readback before resubmit.", False,
            {"reason": AdmissionReason.UNCERTAIN_REQUIRES_READBACK.value},
        )
    if target is None:
        return CoalescingDecision(
            CoalescingAction.REJECT, scope, None,
            "Meaningful fractional or invalid quantities cannot be coalesced.", False,
            {"reason": AdmissionReason.INVALID_QUANTITY.value},
        )
    if scope in _scope_set(active_operation_scopes):
        pending = integral_quantity(pending_target_quantity) if pending_target_quantity is not None else None
        return CoalescingDecision(
            CoalescingAction.COALESCE, scope, target,
            "An existing non-terminal pair job owns this scope; the newest target wins.", False,
            {"previous_target_quantity": pending, "last_value_wins": True},
        )
    if current_available is not None and (isinstance(current_available, bool) or not isinstance(current_available, int)):
        raise ValueError("current_available must be a strict integer")
    pushed = integral_quantity(last_pushed_available) if last_pushed_available is not None else None
    has_pushed_baseline = _usable_timestamp(last_pushed_at)
    if target == current_available:
        return CoalescingDecision(
            CoalescingAction.SKIP, scope, target,
            "The current observed Shopify quantity already equals the target.", False,
            {"current_available": current_available},
        )
    if has_pushed_baseline and pushed == target:
        return CoalescingDecision(
            CoalescingAction.SKIP, scope, target,
            "The target equals the last successfully pushed quantity.", False,
            {"last_pushed_available": pushed},
        )
    return CoalescingDecision(
        CoalescingAction.ENQUEUE, scope, target,
        "No non-terminal pair scope exists; enqueue one bounded inventory mutation.", True,
        {"last_pushed_available": pushed, "last_pushed_at": has_pushed_baseline},
    )


# Short aliases keep the pure API easy to discover from an application port.
CoalesceDecision = CoalescingDecision


def _scope_set(values: Sequence[str] | str | None) -> set[str]:
    if values is None:
        return set()
    if isinstance(values, str):
        return {values}
    return set(values)


def _usable_timestamp(value: datetime | str | bool | None) -> bool:
    """Only a parseable persisted send time can establish a baseline."""

    try:
        return _timestamp(value, "last_pushed_at", strict=True) is not None
    except (TypeError, ValueError, OverflowError):
        return False


__all__ = ["CoalesceDecision", "CoalescingDecision", "decide_inventory_coalescing"]
