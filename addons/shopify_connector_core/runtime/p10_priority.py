"""Pure scheduling and Shopify-cost decisions for the P10 runtime.

This module deliberately has no Odoo or transport imports.  The Odoo adapter
maps its bounded SQL result into :class:`PriorityJob`, asks these functions
for an order/cost decision, and persists the returned values in a short
transaction.  Nothing in this module sleeps, performs I/O, or mutates a
record.

The lane and aging rule is a compatibility contract rather than a tunable UI
setting: safety verification is always first, and waiting work can age only
as high as the interactive lane.  The cost governor is observational.  It
can defer work, but it can never override readiness, tenant, generation or
operation-scope checks performed by the caller.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import MappingProxyType
from typing import Any

from ..domain.immutability import to_plain
from ..domain.states import JobState, PriorityLane


LANE_ORDER = (
    PriorityLane.SAFETY_VERIFICATION.value,
    PriorityLane.INTERACTIVE.value,
    PriorityLane.WEBHOOK.value,
    PriorityLane.ODOO_EVENT.value,
    PriorityLane.SCHEDULED.value,
    PriorityLane.RECONCILIATION.value,
)
LANE_RANK = MappingProxyType({lane: rank for rank, lane in enumerate(LANE_ORDER)})
AGING_INTERVAL_SECONDS = 15 * 60
AGING_CEILING_RANK = LANE_RANK[PriorityLane.INTERACTIVE.value]
DUE_JOB_STATES = frozenset((JobState.QUEUED.value, JobState.RETRY_WAITING.value))
MAX_PRIORITY_INPUT = 1_000
MAX_CLAIM_BATCH = 100

_UTC = timedelta(0)


def _utc(value: datetime, field_name: str = "timestamp") -> datetime:
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


def _finite_number(value: Any, field_name: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be a finite number")
    try:
        value = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not math.isfinite(value) or (positive and value <= 0) or (not positive and value < 0):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{field_name} must be a finite {qualifier} number")
    return value


def _lane(value: str | PriorityLane) -> str:
    value = value.value if isinstance(value, PriorityLane) else value
    if not isinstance(value, str) or value not in LANE_RANK:
        raise ValueError(f"unsupported priority lane: {value!r}")
    return value


def _state(value: str | JobState) -> str:
    value = value.value if isinstance(value, JobState) else value
    if not isinstance(value, str) or value not in {
        item.value for item in JobState
    }:
        raise ValueError(f"unsupported job state: {value!r}")
    return value


@dataclass(frozen=True, slots=True)
class PriorityJob:
    """The bounded, non-secret fields needed to order one due job."""

    job_id: int
    store_id: int
    lane: str | PriorityLane
    lane_priority: int
    available_at: datetime
    state: str | JobState
    blocked_by_job_id: int | None = None
    cancel_requested: bool = False
    sequence: int = 0

    def __post_init__(self) -> None:
        _positive_int(self.job_id, "job_id")
        _positive_int(self.store_id, "store_id")
        object.__setattr__(self, "lane", _lane(self.lane))
        _non_negative_int(self.lane_priority, "lane_priority")
        _utc(self.available_at, "available_at")
        object.__setattr__(self, "state", _state(self.state))
        if self.blocked_by_job_id is not None:
            _positive_int(self.blocked_by_job_id, "blocked_by_job_id")
            if self.blocked_by_job_id == self.job_id:
                raise ValueError("a job cannot depend on itself")
        if not isinstance(self.cancel_requested, bool):
            raise TypeError("cancel_requested must be bool")
        _non_negative_int(self.sequence, "sequence")


def effective_lane_rank(job: PriorityJob, now: datetime) -> int:
    """Return the deterministic lane rank after bounded priority aging.

    One rank is gained for every fifteen minutes of waiting.  A non-safety
    lane is clamped at the interactive rank (1); in particular, no aged job
    can outrank safety verification (rank 0).
    """

    _utc(now, "now")
    waiting_seconds = max(0.0, (now - job.available_at).total_seconds())
    age_steps = int(waiting_seconds // AGING_INTERVAL_SECONDS)
    rank = LANE_RANK[job.lane]
    if rank == LANE_RANK[PriorityLane.SAFETY_VERIFICATION.value]:
        return rank
    return max(AGING_CEILING_RANK, rank - age_steps)


def priority_key(job: PriorityJob, now: datetime) -> tuple[int, datetime, int, int]:
    """Return the stable SQL-compatible ordering key for one job."""

    return (effective_lane_rank(job, now), job.available_at, job.lane_priority, job.job_id)


def select_due_jobs(
    jobs: Sequence[PriorityJob],
    *,
    now: datetime,
    limit: int = MAX_CLAIM_BATCH,
) -> tuple[PriorityJob, ...]:
    """Select and order a bounded due batch.

    The adapter should issue a bounded ``FOR UPDATE SKIP LOCKED`` query first;
    this pure helper is intentionally bounded as well so a caller cannot
    accidentally turn a scheduler pass into an unbounded in-memory scan.
    """

    _utc(now, "now")
    if not isinstance(jobs, Sequence) or isinstance(jobs, (str, bytes)):
        raise TypeError("jobs must be a bounded sequence")
    if len(jobs) > MAX_PRIORITY_INPUT:
        raise ValueError("the priority candidate set exceeds its bound")
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError("limit must be an integer")
    if limit <= 0 or limit > MAX_CLAIM_BATCH:
        raise ValueError(f"limit must be between 1 and {MAX_CLAIM_BATCH}")

    seen: set[int] = set()
    due: list[PriorityJob] = []
    for job in jobs:
        if not isinstance(job, PriorityJob):
            raise TypeError("jobs must contain PriorityJob values")
        if job.job_id in seen:
            raise ValueError("duplicate job IDs are not safe to order")
        seen.add(job.job_id)
        if (
            job.state in DUE_JOB_STATES
            and job.available_at <= now
            and job.blocked_by_job_id is None
            and not job.cancel_requested
        ):
            due.append(job)
    due.sort(key=lambda item: priority_key(item, now))
    return tuple(due[:limit])


@dataclass(frozen=True, slots=True)
class CostObservation:
    """The last bounded Shopify cost extension observed for one store."""

    available_cost: float | int
    maximum_cost: float | int
    restore_rate: float | int
    observed_at: datetime

    def __post_init__(self) -> None:
        available = _finite_number(self.available_cost, "available_cost")
        maximum = _finite_number(self.maximum_cost, "maximum_cost", positive=True)
        restore = _finite_number(self.restore_rate, "restore_rate")
        if available > maximum:
            raise ValueError("available_cost cannot exceed maximum_cost")
        _utc(self.observed_at, "observed_at")
        object.__setattr__(self, "available_cost", available)
        object.__setattr__(self, "maximum_cost", maximum)
        object.__setattr__(self, "restore_rate", restore)


@dataclass(frozen=True, slots=True)
class CostDecision:
    """An immutable no-sleep scheduling result from :class:`CostGovernor`."""

    action: str
    reason_code: str
    estimated_cost: float
    safety_reserve: float
    available_cost: float | None
    projected_available_cost: float | None
    not_before: datetime | None
    delay_seconds: float
    capped: bool

    def __post_init__(self) -> None:
        if self.action not in {"allow", "defer", "manual_review"}:
            raise ValueError("unsupported cost decision action")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty")
        _finite_number(self.estimated_cost, "estimated_cost", positive=True)
        _finite_number(self.safety_reserve, "safety_reserve")
        for name in ("available_cost", "projected_available_cost"):
            value = getattr(self, name)
            if value is not None:
                _finite_number(value, name)
        if self.not_before is not None:
            _utc(self.not_before, "not_before")
        _finite_number(self.delay_seconds, "delay_seconds")
        if not isinstance(self.capped, bool):
            raise TypeError("capped must be bool")
        if self.action == "allow" and self.delay_seconds != 0:
            raise ValueError("an allowed request cannot have a delay")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "action": self.action,
            "reason_code": self.reason_code,
            "estimated_cost": self.estimated_cost,
            "safety_reserve": self.safety_reserve,
            "available_cost": self.available_cost,
            "projected_available_cost": self.projected_available_cost,
            "not_before": self.not_before,
            "delay_seconds": self.delay_seconds,
            "capped": self.capped,
        })


@dataclass(frozen=True, slots=True)
class CostGovernor:
    """Compute a bounded defer/allow decision without sleeping or I/O."""

    safety_reserve: float | int = 0
    unknown_delay_seconds: int = 60
    max_wait_seconds: int = 60 * 60

    def __post_init__(self) -> None:
        reserve = _finite_number(self.safety_reserve, "safety_reserve")
        if isinstance(self.unknown_delay_seconds, bool) or not isinstance(
            self.unknown_delay_seconds, int
        ) or self.unknown_delay_seconds <= 0:
            raise ValueError("unknown_delay_seconds must be a positive integer")
        if isinstance(self.max_wait_seconds, bool) or not isinstance(
            self.max_wait_seconds, int
        ) or self.max_wait_seconds <= 0:
            raise ValueError("max_wait_seconds must be a positive integer")
        object.__setattr__(self, "safety_reserve", reserve)

    def decide(
        self,
        observation: CostObservation | None,
        *,
        estimated_cost: float | int,
        now: datetime,
    ) -> CostDecision:
        _utc(now, "now")
        estimated = _finite_number(estimated_cost, "estimated_cost", positive=True)
        reserve = float(self.safety_reserve)
        if observation is None:
            return CostDecision(
                action="defer",
                reason_code="cost_budget_unknown",
                estimated_cost=estimated,
                safety_reserve=reserve,
                available_cost=None,
                projected_available_cost=None,
                not_before=now + timedelta(seconds=self.unknown_delay_seconds),
                delay_seconds=float(self.unknown_delay_seconds),
                capped=False,
            )

        if observation.observed_at > now:
            return CostDecision(
                action="manual_review",
                reason_code="cost_observation_from_future",
                estimated_cost=estimated,
                safety_reserve=reserve,
                available_cost=observation.available_cost,
                projected_available_cost=observation.available_cost,
                not_before=None,
                delay_seconds=0,
                capped=False,
            )

        required = estimated + reserve
        if required > observation.maximum_cost:
            return CostDecision(
                action="manual_review",
                reason_code="cost_request_exceeds_bucket",
                estimated_cost=estimated,
                safety_reserve=reserve,
                available_cost=observation.available_cost,
                projected_available_cost=observation.available_cost,
                not_before=None,
                delay_seconds=0,
                capped=False,
            )

        elapsed = max(0.0, (now - observation.observed_at).total_seconds())
        projected = min(
            observation.maximum_cost,
            observation.available_cost + elapsed * observation.restore_rate,
        )
        if projected >= required:
            return CostDecision(
                action="allow",
                reason_code="cost_budget_available",
                estimated_cost=estimated,
                safety_reserve=reserve,
                available_cost=observation.available_cost,
                projected_available_cost=projected,
                not_before=now,
                delay_seconds=0,
                capped=False,
            )

        if observation.restore_rate <= 0:
            return CostDecision(
                action="manual_review",
                reason_code="cost_budget_not_restoring",
                estimated_cost=estimated,
                safety_reserve=reserve,
                available_cost=observation.available_cost,
                projected_available_cost=projected,
                not_before=None,
                delay_seconds=0,
                capped=False,
            )

        delay = (required - projected) / observation.restore_rate
        bounded_delay = min(float(self.max_wait_seconds), delay)
        return CostDecision(
            action="defer",
            reason_code="cost_budget_wait",
            estimated_cost=estimated,
            safety_reserve=reserve,
            available_cost=observation.available_cost,
            projected_available_cost=projected,
            not_before=now + timedelta(seconds=bounded_delay),
            delay_seconds=bounded_delay,
            capped=delay > bounded_delay,
        )


__all__ = [
    "AGING_CEILING_RANK",
    "AGING_INTERVAL_SECONDS",
    "CostDecision",
    "CostGovernor",
    "CostObservation",
    "DUE_JOB_STATES",
    "LANE_ORDER",
    "MAX_CLAIM_BATCH",
    "MAX_PRIORITY_INPUT",
    "PriorityJob",
    "effective_lane_rank",
    "priority_key",
    "select_due_jobs",
]
