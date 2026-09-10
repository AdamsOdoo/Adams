"""Pure P10 retry, dependency, cancellation and lease decisions.

The coordinator asks these policies for an immutable decision and then lets an
Odoo adapter persist that decision.  They intentionally contain no ORM,
network, wall-clock, random or sleep calls.  A caller supplies ``now`` (and,
if desired, a jitter sample) so tests and fault injection remain deterministic.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from ..domain.immutability import to_plain
from ..domain.retry_policy import DEFAULT_RETRY_POLICY, RetryPolicy
from ..domain.states import JobState
from .p10_stale_owner import StaleOwnerDecision, StaleOwnerInput, StaleOwnerPolicy


_UTC = timedelta(0)
_AUTO_RETRY_ERROR_CLASSES = frozenset((
    "shopify_throttling_rate_limit",
    "shopify_temporary_server_network",
    "concurrency_race_conflict",
))
_MANUAL_FIX_ERROR_CLASSES = frozenset((
    "shopify_permission_scope_auth",
    "shopify_user_errors_validation",
    "odoo_validation_configuration",
    "mapping_missing",
    "data_shape_schema_mismatch",
    "financial_total_mismatch",
))
_MANUAL_REVIEW_ERROR_CLASSES = frozenset((
    "ambiguous_match",
    "binding_conflict",
    "duplicate_risk",
    "no_reconciliation_strategy",
    "idempotency_contract_violation",
    "store_identity_mismatch",
    "destructive_write_guard_blocked",
    "inventory_location_missing",
    "fulfillment_notification_confirmation_missing",
    "unknown_system_error",
))
KNOWN_ERROR_CLASSES = frozenset(
    _AUTO_RETRY_ERROR_CLASSES
    | _MANUAL_FIX_ERROR_CLASSES
    | _MANUAL_REVIEW_ERROR_CLASSES
)

_REMOTE_OUTCOMES = frozenset((
    "none",
    "not_attempted",
    "pre_send",
    "failed_clean",
    "pending",
    "in_flight",
    "uncertain",
    "succeeded",
))
_DEPENDENCY_STATES = frozenset(
    item.value for item in JobState
) | frozenset(("admitted", "requested", "waiting"))
_TERMINAL_JOB_STATES = frozenset((
    JobState.SUCCEEDED.value,
    JobState.FAILED_FINAL.value,
    JobState.SKIPPED.value,
    JobState.CANCELLED.value,
))
_RUN_COUNT_KEYS = frozenset((
    "draft",
    "queued",
    "running",
    "retry_waiting",
    "failed_retryable",
    "failed_final",
    "blocked_manual_review",
    "succeeded",
    "skipped",
    "cancelled",
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


def project_run_state(
    counts: Mapping[str, int],
    *,
    cancel_requested: bool = False,
) -> str:
    """Project one run state from its bounded child-job state counts.

    The projection is deliberately deterministic and contains no ORM or I/O.
    A terminal failure mixed with at least one successful or policy-approved
    skipped child is reported as ``partially_succeeded``; a run containing
    only terminal failures is ``failed_terminal``.  Any unresolved child
    state wins over terminal projection, with manual review taking precedence
    over active work so the operator sees the blocking action first.
    """
    if not isinstance(counts, Mapping):
        raise TypeError("run state counts must be a mapping")
    if any(key not in _RUN_COUNT_KEYS for key in counts):
        raise ValueError("run state counts contain an unknown state")
    normalized = {}
    for key, value in counts.items():
        _non_negative_int(value, "run state count for %s" % key)
        normalized[key] = value
    if not isinstance(cancel_requested, bool):
        raise TypeError("cancel_requested must be bool")

    active = sum(
        normalized.get(state, 0)
        for state in ("draft", "queued", "running", "retry_waiting")
    )
    if normalized.get("blocked_manual_review", 0):
        return "blocked_manual_review"
    if normalized.get("running", 0):
        return "running"
    if (
        normalized.get("queued", 0)
        or normalized.get("retry_waiting", 0)
        or normalized.get("draft", 0)
    ):
        return "waiting"
    if normalized.get("failed_retryable", 0):
        return "failed_retryable"
    if normalized.get("failed_final", 0):
        if normalized.get("succeeded", 0) or normalized.get("skipped", 0):
            return "partially_succeeded"
        return "failed_terminal"
    if cancel_requested:
        return "cancelled"
    if active == 0:
        return "succeeded"
    return "waiting"


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
class RetryObservation:
    """Classified outcome used to decide whether a read job may be retried."""

    error_class: str
    remote_outcome: str
    retry_count: int
    first_attempt_at: datetime
    now: datetime
    jitter_fraction: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.error_class, str) or not self.error_class.strip():
            raise ValueError("error_class must be non-empty")
        if self.remote_outcome not in _REMOTE_OUTCOMES:
            raise ValueError(f"unknown remote outcome: {self.remote_outcome!r}")
        _non_negative_int(self.retry_count, "retry_count")
        _utc(self.first_attempt_at, "first_attempt_at")
        _utc(self.now, "now")
        if self.now < self.first_attempt_at:
            raise ValueError("now cannot precede first_attempt_at")
        jitter = _finite_number(self.jitter_fraction, "jitter_fraction")
        if not -DEFAULT_RETRY_POLICY.jitter_ratio <= jitter <= DEFAULT_RETRY_POLICY.jitter_ratio:
            raise ValueError("jitter_fraction exceeds the locked jitter bound")
        object.__setattr__(self, "jitter_fraction", jitter)


@dataclass(frozen=True, slots=True)
class RetryDecision:
    """Safe retry/verification routing result."""

    action: str
    reason_code: str
    error_class: str
    retry_at: datetime | None = None
    retry_number: int | None = None
    delay_seconds: float | None = None
    jitter_fraction: float = 0.0

    def __post_init__(self) -> None:
        if self.action not in {
            "retry", "verify", "manual_fix", "manual_review",
            "complete", "terminal",
        }:
            raise ValueError("unsupported retry decision action")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty")
        if not isinstance(self.error_class, str) or not self.error_class.strip():
            raise ValueError("error_class must be non-empty")
        if self.retry_at is not None:
            _utc(self.retry_at, "retry_at")
        if self.retry_number is not None:
            _positive_int(self.retry_number, "retry_number")
        if self.delay_seconds is not None:
            _finite_number(self.delay_seconds, "delay_seconds")
            if self.delay_seconds < 0:
                raise ValueError("delay_seconds cannot be negative")
        jitter = _finite_number(self.jitter_fraction, "jitter_fraction")
        if not -DEFAULT_RETRY_POLICY.jitter_ratio <= jitter <= DEFAULT_RETRY_POLICY.jitter_ratio:
            raise ValueError("jitter_fraction exceeds the locked jitter bound")
        if self.action == "retry" and (
            self.retry_at is None
            or self.retry_number is None
            or self.delay_seconds is None
        ):
            raise ValueError("a retry decision requires a schedule")
        object.__setattr__(self, "jitter_fraction", jitter)

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "action": self.action,
            "reason_code": self.reason_code,
            "error_class": self.error_class,
            "retry_at": self.retry_at,
            "retry_number": self.retry_number,
            "delay_seconds": self.delay_seconds,
            "jitter_fraction": self.jitter_fraction,
        })


def decide_retry(
    observation: RetryObservation,
    *,
    policy: RetryPolicy = DEFAULT_RETRY_POLICY,
) -> RetryDecision:
    """Route one classified failure using the accepted bounded retry policy.

    Only the known automatic-transient classes are scheduled automatically.
    A possible-after-send outcome always goes to verification, regardless of
    its error class.  Unknown classes and exhausted windows fail closed into
    manual review; they are never blindly retried.
    """

    if not isinstance(observation, RetryObservation):
        raise TypeError("observation must be a RetryObservation")
    if not isinstance(policy, RetryPolicy):
        raise TypeError("policy must be a RetryPolicy")

    if observation.remote_outcome in {"pending", "in_flight", "uncertain"}:
        return RetryDecision(
            action="verify",
            reason_code="remote_outcome_uncertain",
            error_class=observation.error_class,
        )
    if observation.remote_outcome == "succeeded":
        return RetryDecision(
            action="complete",
            reason_code="remote_outcome_succeeded",
            error_class=observation.error_class,
        )
    if observation.error_class not in KNOWN_ERROR_CLASSES:
        return RetryDecision(
            action="manual_review",
            reason_code="unknown_error_class",
            error_class=observation.error_class,
        )
    if observation.error_class in _MANUAL_REVIEW_ERROR_CLASSES:
        return RetryDecision(
            action="manual_review",
            reason_code="manual_review_required",
            error_class=observation.error_class,
        )
    if observation.error_class in _MANUAL_FIX_ERROR_CLASSES:
        return RetryDecision(
            action="manual_fix",
            reason_code="manual_fix_then_retry",
            error_class=observation.error_class,
        )

    # Only the automatic transient family reaches the scheduler.
    retry_number = observation.retry_count + 1
    if retry_number > policy.max_scheduled_retries:
        return RetryDecision(
            action="manual_review",
            reason_code="retry_cap_exhausted",
            error_class=observation.error_class,
            retry_number=retry_number,
        )
    elapsed = (observation.now - observation.first_attempt_at).total_seconds()
    if elapsed > policy.window_seconds:
        return RetryDecision(
            action="manual_review",
            reason_code="retry_window_exhausted",
            error_class=observation.error_class,
            retry_number=retry_number,
        )
    base_delay = policy.delay_seconds(retry_number)
    delay = base_delay * (1.0 + observation.jitter_fraction)
    retry_at = observation.now + timedelta(seconds=delay)
    deadline = observation.first_attempt_at + timedelta(seconds=policy.window_seconds)
    if retry_at > deadline:
        return RetryDecision(
            action="manual_review",
            reason_code="retry_window_would_be_exceeded",
            error_class=observation.error_class,
            retry_number=retry_number,
            delay_seconds=delay,
            jitter_fraction=observation.jitter_fraction,
        )
    return RetryDecision(
        action="retry",
        reason_code="retry_scheduled",
        error_class=observation.error_class,
        retry_at=retry_at,
        retry_number=retry_number,
        delay_seconds=delay,
        jitter_fraction=observation.jitter_fraction,
    )


@dataclass(frozen=True, slots=True)
class DependencyDecision:
    """Whether a job may run given its one explicit dependency."""

    action: str
    reason_code: str
    blocked_by_job_id: int | None = None

    def __post_init__(self) -> None:
        if self.action not in {"ready", "wait", "blocked", "manual_review"}:
            raise ValueError("unsupported dependency decision action")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty")
        if self.blocked_by_job_id is not None:
            _positive_int(self.blocked_by_job_id, "blocked_by_job_id")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "action": self.action,
            "reason_code": self.reason_code,
            "blocked_by_job_id": self.blocked_by_job_id,
        })


def decide_dependency(
    blocked_by_job_id: int | None,
    dependency_state: str | None,
) -> DependencyDecision:
    """Resolve one dependency without guessing when the state is unknown."""

    if blocked_by_job_id is not None:
        _positive_int(blocked_by_job_id, "blocked_by_job_id")
    if blocked_by_job_id is None and dependency_state is None:
        return DependencyDecision("ready", "no_dependency")
    if blocked_by_job_id is None:
        return DependencyDecision("manual_review", "dependency_reference_missing")
    if dependency_state not in _DEPENDENCY_STATES:
        return DependencyDecision(
            "manual_review", "unknown_dependency_state", blocked_by_job_id,
        )
    if dependency_state in {JobState.SUCCEEDED.value, JobState.SKIPPED.value}:
        return DependencyDecision("ready", "dependency_satisfied", blocked_by_job_id)
    if dependency_state in _TERMINAL_JOB_STATES:
        return DependencyDecision("blocked", "dependency_terminal", blocked_by_job_id)
    return DependencyDecision("wait", "dependency_incomplete", blocked_by_job_id)


@dataclass(frozen=True, slots=True)
class DependencyNode:
    """A small graph projection used to reject dependency cycles."""

    job_id: int
    blocked_by_job_id: int | None = None

    def __post_init__(self) -> None:
        _positive_int(self.job_id, "job_id")
        if self.blocked_by_job_id is not None:
            _positive_int(self.blocked_by_job_id, "blocked_by_job_id")
            if self.blocked_by_job_id == self.job_id:
                raise ValueError("a job cannot depend on itself")


def find_dependency_cycle(
    nodes: Sequence[DependencyNode],
    *,
    max_nodes: int = 1_000,
) -> tuple[int, ...]:
    """Return one deterministic cycle, or an empty tuple.

    Missing references are allowed because a bounded worker batch may contain
    only one side of a dependency.  The Odoo adapter must resolve missing
    references in its admission query; this helper only checks the projected
    graph it was given.
    """

    if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes)):
        raise TypeError("nodes must be a bounded sequence")
    if isinstance(max_nodes, bool) or not isinstance(max_nodes, int) or max_nodes <= 0:
        raise ValueError("max_nodes must be a positive integer")
    if len(nodes) > max_nodes:
        raise ValueError("dependency graph exceeds its bound")
    graph: dict[int, int] = {}
    for node in nodes:
        if not isinstance(node, DependencyNode):
            raise TypeError("nodes must contain DependencyNode values")
        if node.job_id in graph:
            raise ValueError("dependency graph contains duplicate job IDs")
        if node.blocked_by_job_id is not None:
            graph[node.job_id] = node.blocked_by_job_id

    for start in sorted(graph):
        path: list[int] = []
        positions: dict[int, int] = {}
        current: int | None = start
        while current in graph:
            if current in positions:
                return tuple(path[positions[current]:])
            positions[current] = len(path)
            path.append(current)
            current = graph[current]
    return ()


@dataclass(frozen=True, slots=True)
class CancellationDecision:
    """Safe local cancellation outcome; never claims a remote undo."""

    action: str
    reason_code: str
    target_state: str | None

    def __post_init__(self) -> None:
        if self.action not in {
            "not_requested", "already_terminal", "cancel", "verify", "manual_review",
        }:
            raise ValueError("unsupported cancellation action")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty")
        if self.target_state is not None and self.target_state not in {
            JobState.CANCELLED.value,
            JobState.BLOCKED_MANUAL_REVIEW.value,
        }:
            raise ValueError("unsupported cancellation target state")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "action": self.action,
            "reason_code": self.reason_code,
            "target_state": self.target_state,
        })


def decide_cancellation(
    job_state: str | JobState,
    *,
    cancel_requested: bool,
    remote_outcome: str = "none",
) -> CancellationDecision:
    """Decide local cancellation while preserving remote uncertainty."""

    state = job_state.value if isinstance(job_state, JobState) else job_state
    if state not in {item.value for item in JobState}:
        raise ValueError(f"unknown job state: {state!r}")
    if not isinstance(cancel_requested, bool):
        raise TypeError("cancel_requested must be bool")
    if remote_outcome not in _REMOTE_OUTCOMES:
        return CancellationDecision("manual_review", "unknown_remote_outcome", None)
    if not cancel_requested:
        return CancellationDecision("not_requested", "cancellation_not_requested", None)
    if state in _TERMINAL_JOB_STATES:
        return CancellationDecision("already_terminal", "job_already_terminal", None)
    if remote_outcome in {"pending", "in_flight", "uncertain", "succeeded"}:
        if remote_outcome == "succeeded":
            return CancellationDecision(
                "manual_review",
                "remote_write_already_succeeded",
                JobState.BLOCKED_MANUAL_REVIEW.value,
            )
        return CancellationDecision(
            "verify", "remote_outcome_unresolved", JobState.BLOCKED_MANUAL_REVIEW.value,
        )
    return CancellationDecision("cancel", "local_work_cancelled", JobState.CANCELLED.value)


__all__ = [
    "CancellationDecision",
    "DependencyDecision",
    "DependencyNode",
    "KNOWN_ERROR_CLASSES",
    "RetryDecision",
    "RetryObservation",
    "StaleOwnerDecision",
    "StaleOwnerInput",
    "StaleOwnerPolicy",
    "decide_cancellation",
    "decide_dependency",
    "decide_retry",
    "find_dependency_cycle",
    "project_run_state",
]
