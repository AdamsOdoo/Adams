"""Bounded stale-owner recovery policy for the P10 runtime."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ..domain.immutability import to_plain
from ..domain.states import AttemptOutcome


_UTC = timedelta(0)
_REMOTE_OUTCOMES = frozenset((
    "none", "not_attempted", "pre_send", "failed_clean", "pending",
    "in_flight", "uncertain", "succeeded",
))
_ACTIVE_ATTEMPT_OUTCOMES = frozenset((
    AttemptOutcome.CLAIMED.value,
    AttemptOutcome.RUNNING.value,
))


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() != _UTC:
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _finite_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field_name} must be finite") from exc
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


@dataclass(frozen=True, slots=True)
class StaleOwnerInput:
    """The bounded evidence used by the stale-owner sweep."""

    job_id: int
    attempt_id: int
    attempt_outcome: str | AttemptOutcome
    claimed_at: datetime
    heartbeat_at: datetime | None
    now: datetime
    remote_outcome: str
    recovery_count: int = 0

    def __post_init__(self) -> None:
        _positive_int(self.job_id, "job_id")
        _positive_int(self.attempt_id, "attempt_id")
        outcome = (
            self.attempt_outcome.value
            if isinstance(self.attempt_outcome, AttemptOutcome)
            else self.attempt_outcome
        )
        if (
            not isinstance(outcome, str)
            or outcome not in {item.value for item in AttemptOutcome}
        ):
            raise ValueError(f"unknown attempt outcome: {outcome!r}")
        object.__setattr__(self, "attempt_outcome", outcome)
        _utc(self.claimed_at, "claimed_at")
        if self.heartbeat_at is not None:
            _utc(self.heartbeat_at, "heartbeat_at")
        _utc(self.now, "now")
        _non_negative_int(self.recovery_count, "recovery_count")
        if self.remote_outcome not in _REMOTE_OUTCOMES:
            raise ValueError(f"unknown remote outcome: {self.remote_outcome!r}")


@dataclass(frozen=True, slots=True)
class StaleOwnerDecision:
    """Stale-owner action returned to the lease/recovery adapter."""

    action: str
    reason_code: str
    stale_for_seconds: float
    owner_lost: bool

    def __post_init__(self) -> None:
        if self.action not in {"keep", "recover", "verify", "quarantine", "terminal"}:
            raise ValueError("unsupported stale-owner action")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty")
        _finite_number(self.stale_for_seconds, "stale_for_seconds")
        if self.stale_for_seconds < 0:
            raise ValueError("stale_for_seconds cannot be negative")
        if not isinstance(self.owner_lost, bool):
            raise TypeError("owner_lost must be bool")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "action": self.action,
            "reason_code": self.reason_code,
            "stale_for_seconds": self.stale_for_seconds,
            "owner_lost": self.owner_lost,
        })


@dataclass(frozen=True, slots=True)
class StaleOwnerPolicy:
    """Bounded lease policy; uncertain remote outcomes never auto-replay."""

    lease_seconds: int = 300
    heartbeat_grace_seconds: int = 60
    max_recoveries: int = 2

    def __post_init__(self) -> None:
        for name in ("lease_seconds", "heartbeat_grace_seconds", "max_recoveries"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        if self.lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        if self.max_recoveries <= 0:
            raise ValueError("max_recoveries must be positive")

    def decide(self, evidence: StaleOwnerInput) -> StaleOwnerDecision:
        if not isinstance(evidence, StaleOwnerInput):
            raise TypeError("evidence must be StaleOwnerInput")
        if evidence.now < evidence.claimed_at:
            return StaleOwnerDecision("quarantine", "clock_before_claim", 0, False)
        if evidence.heartbeat_at is not None and evidence.heartbeat_at < evidence.claimed_at:
            return StaleOwnerDecision("quarantine", "heartbeat_before_claim", 0, False)
        if evidence.heartbeat_at is not None and evidence.heartbeat_at > evidence.now:
            return StaleOwnerDecision("quarantine", "heartbeat_from_future", 0, False)
        if evidence.attempt_outcome not in _ACTIVE_ATTEMPT_OUTCOMES:
            return StaleOwnerDecision("terminal", "attempt_not_active", 0, False)
        if (
            evidence.attempt_outcome == AttemptOutcome.RUNNING.value
            and evidence.heartbeat_at is None
        ):
            return StaleOwnerDecision("quarantine", "running_attempt_has_no_heartbeat", 0, False)

        last_activity = evidence.heartbeat_at or evidence.claimed_at
        stale_for = max(0.0, (evidence.now - last_activity).total_seconds())
        threshold = self.lease_seconds + self.heartbeat_grace_seconds
        if stale_for <= threshold:
            return StaleOwnerDecision("keep", "owner_lease_current", stale_for, False)
        if evidence.recovery_count >= self.max_recoveries:
            return StaleOwnerDecision("quarantine", "stale_recovery_cap_exhausted", stale_for, True)

        if evidence.remote_outcome in {"pending", "in_flight", "uncertain", "succeeded"}:
            return StaleOwnerDecision("verify", "stale_owner_requires_readback", stale_for, True)
        if evidence.remote_outcome in {"none", "not_attempted", "pre_send", "failed_clean"}:
            return StaleOwnerDecision("recover", "stale_owner_recoverable", stale_for, True)
        return StaleOwnerDecision("quarantine", "unknown_remote_outcome", stale_for, True)


__all__ = ["StaleOwnerDecision", "StaleOwnerInput", "StaleOwnerPolicy"]
