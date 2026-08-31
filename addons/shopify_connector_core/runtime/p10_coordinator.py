"""Bounded, read-only P10 coordinator contracts.

The coordinator is intentionally a small orchestration shell.  A repository
adapter performs a bounded, row-locking claim transaction and a separate
bounded finalization transaction.  A registered read handler runs only after
the claim transaction has returned, so Shopify reads cannot execute while the
claim/finalize transaction is open.  This module has no transport, ORM,
thread, queue or sleep dependency.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol
from uuid import UUID

from ..domain.immutability import freeze_value, to_plain
from ..domain.identifiers import require_key
from ..domain.states import PriorityLane
from .contracts import (
    HandlerResult,
    NeedsReview,
    NeedsVerification,
    Retryable,
    Skipped,
    Succeeded,
    TerminalFailure,
)
from .p10_decisions import KNOWN_ERROR_CLASSES
from .p10_admission import (
    READ_ONLY_RUNTIME_MODE,
    ReadOnlyAdmissionDecision,
    ReadOnlyAdmissionRequest,
    admit_read_only,
)
from .p10_priority import MAX_CLAIM_BATCH


CLAIM_TRANSACTION = "claim_transaction"
EXECUTION_PHASE = "execution"
FINALIZE_TRANSACTION = "finalize_transaction"
_UTC = timedelta(0)

# P10 deliberately keeps the handler vocabulary small and explicit.  The
# category is descriptive metadata used by addon registration seams; it is
# not a fallback lookup key and it never changes the claim/finalize protocol.
# Domain addons can therefore register their own import/scan/reconciliation
# readers without making core import a domain module.
READ_ONLY_OPERATION_KINDS = frozenset({
    "diagnostic",
    "import",
    "scan",
    "reconciliation",
})


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


def _lane(value: str | PriorityLane) -> str:
    value = value.value if isinstance(value, PriorityLane) else value
    if not isinstance(value, str) or value not in {
        item.value for item in PriorityLane
    }:
        raise ValueError(f"unsupported priority lane: {value!r}")
    return value


def _claim_token(value: str) -> str:
    if isinstance(value, UUID):
        value = str(value)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("claim_token must be an opaque UUID")
    try:
        UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("claim_token must be an opaque UUID") from exc
    return value


def _worker_ref(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > 128:
        raise ValueError("worker_ref must be a bounded non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class ClaimedWork:
    """Non-secret work handed from a committed claim to a read handler."""

    job_id: int
    store_id: int
    attempt_no: int
    claim_token: str | UUID
    worker_ref: str
    handler_key: str
    lane: str | PriorityLane
    expected_generation: int
    payload: Mapping[str, Any] = field(default_factory=dict)
    operation_scope_key: str | None = None
    mutation: bool = False
    # The connection epoch is retained in ``expected_generation`` for the
    # original P10 contract.  Configuration is an independent fence: changing
    # a store's V2 mode/settings must not let an already-admitted read cross
    # that policy boundary.  A default keeps existing pure fixtures/source
    # compatibility while Odoo adapters always populate the real value.
    expected_configuration_generation: int = 0
    run_id: int | None = None
    company_id: int | None = None

    def __post_init__(self) -> None:
        _positive_int(self.job_id, "job_id")
        _positive_int(self.store_id, "store_id")
        _positive_int(self.attempt_no, "attempt_no")
        object.__setattr__(self, "claim_token", _claim_token(self.claim_token))
        object.__setattr__(self, "worker_ref", _worker_ref(self.worker_ref))
        require_key(self.handler_key, "handler_key")
        object.__setattr__(self, "lane", _lane(self.lane))
        _non_negative_int(self.expected_generation, "expected_generation")
        _non_negative_int(
            self.expected_configuration_generation,
            "expected_configuration_generation",
        )
        for name in ("run_id", "company_id"):
            value = getattr(self, name)
            if value is not None:
                _positive_int(value, name)
        if not isinstance(self.payload, Mapping):
            raise TypeError("payload must be a mapping")
        object.__setattr__(self, "payload", freeze_value(dict(self.payload)))
        if self.operation_scope_key is not None:
            if (
                not isinstance(self.operation_scope_key, str)
                or not self.operation_scope_key.strip()
            ):
                raise ValueError("operation_scope_key must be non-empty or None")
        if not isinstance(self.mutation, bool):
            raise TypeError("mutation must be bool")
        if self.mutation:
            raise ValueError("P10 read-only work cannot carry a mutation handler")


class UnknownReadHandler(LookupError):
    """Raised when no explicit read-only handler is registered."""


@dataclass(frozen=True, slots=True)
class ReadOnlyHandlerSpec:
    """One explicit non-mutation handler registration.

    ``operation_kind`` is intentionally metadata rather than dispatch
    behavior.  The handler key remains the only lookup identity, so a domain
    addon must register each read operation explicitly.  The current P10
    executor is local-only: a handler that needs Shopify I/O must first gain a
    claim-fenced transport seam; registering a callable here does not itself
    provide that fence.
    """

    handler_key: str
    handler: Callable[[ClaimedWork], HandlerResult]
    mutation: bool = False
    operation_kind: str = "diagnostic"

    def __post_init__(self) -> None:
        require_key(self.handler_key, "handler_key")
        if not callable(self.handler):
            raise TypeError("handler must be callable")
        if not isinstance(self.mutation, bool):
            raise TypeError("mutation must be bool")
        if self.mutation:
            raise ValueError("mutation handlers are not admitted by P10")
        if (
            not isinstance(self.operation_kind, str)
            or self.operation_kind not in READ_ONLY_OPERATION_KINDS
        ):
            raise ValueError(
                "unsupported read-only operation kind: %r"
                % (self.operation_kind,)
            )


class ReadOnlyHandlerRegistry:
    """Explicit registry with no fallback or model/method reflection."""

    def __init__(self, specs: Sequence[ReadOnlyHandlerSpec] = ()) -> None:
        if not isinstance(specs, Sequence) or isinstance(specs, (str, bytes)):
            raise TypeError("specs must be a bounded sequence")
        if len(specs) > MAX_CLAIM_BATCH:
            raise ValueError("handler registry exceeds its bound")
        self._handlers: dict[str, ReadOnlyHandlerSpec] = {}
        for spec in specs:
            self.register(spec)

    def register(self, spec: ReadOnlyHandlerSpec) -> None:
        if not isinstance(spec, ReadOnlyHandlerSpec):
            raise TypeError("registry accepts ReadOnlyHandlerSpec values only")
        if spec.handler_key in self._handlers:
            raise ValueError("duplicate read-only handler key")
        self._handlers[spec.handler_key] = spec

    def require(self, handler_key: str) -> ReadOnlyHandlerSpec:
        require_key(handler_key, "handler_key")
        try:
            return self._handlers[handler_key]
        except KeyError as exc:
            raise UnknownReadHandler(handler_key) from exc

    def keys(self) -> tuple[str, ...]:
        """Return the bounded explicit key snapshot for admission/claiming."""
        return tuple(self._handlers)


class ReadOnlyRuntimeRepository(Protocol):
    """Adapter contract for two short DB-only transactions.

    ``claim_due`` must perform only bounded row selection, scope/generation/
    cancellation rechecks, attempt allocation and claim persistence.  It must
    not invoke a handler or any transport.  ``finalize_attempt`` must perform
    only claim ownership rechecks and durable outcome/evidence persistence.  A
    Shopify read belongs to the execution phase between the two calls.
    """

    def claim_due(
        self,
        *,
        now: datetime,
        worker_ref: str,
        limit: int,
        phase: str,
    ) -> Sequence[ClaimedWork]:
        """Return at most ``limit`` committed, read-only claims.

        ``phase`` must be ``CLAIM_TRANSACTION``.  It lets an adapter assert
        that this method is used only for its short DB-only transaction.
        """

    def finalize_attempt(
        self,
        *,
        claim: ClaimedWork,
        result: HandlerResult,
        finished_at: datetime,
        phase: str,
    ) -> None:
        """Persist one result in a short transaction with no network I/O."""

    def commit(self, *, phase: str) -> None:
        """Close the adapter's transaction boundary for ``phase``.

        Odoo adapters may use a side cursor and therefore complete the
        boundary inside ``claim_due``/``finalize_attempt``; such adapters
        expose a validating no-op here.  The hook keeps ordering explicit for
        adapters that retain a caller-owned cursor.
        """

    def rollback(self, *, phase: str) -> None:
        """Best-effort cleanup after a boundary failure."""


@dataclass(frozen=True, slots=True)
class BatchItemReport:
    """Safe per-job projection of a coordinator pass."""

    job_id: int
    attempt_no: int
    outcome: str
    finalized: bool
    reason_code: str

    def __post_init__(self) -> None:
        _positive_int(self.job_id, "job_id")
        _positive_int(self.attempt_no, "attempt_no")
        if self.outcome not in {
            "succeeded", "skipped", "retryable", "verification_required",
            "manual_review", "failed_terminal",
        }:
            raise ValueError("unsupported batch outcome")
        if not isinstance(self.finalized, bool):
            raise TypeError("finalized must be bool")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "job_id": self.job_id,
            "attempt_no": self.attempt_no,
            "outcome": self.outcome,
            "finalized": self.finalized,
            "reason_code": self.reason_code,
        })


@dataclass(frozen=True, slots=True)
class BatchReport:
    """Immutable bounded coordinator result."""

    worker_ref: str
    started_at: datetime
    finished_at: datetime
    claimed_count: int
    finalized_count: int
    items: tuple[BatchItemReport, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "worker_ref", _worker_ref(self.worker_ref))
        _utc(self.started_at, "started_at")
        _utc(self.finished_at, "finished_at")
        if self.finished_at < self.started_at:
            raise ValueError("finished_at cannot precede started_at")
        for name in ("claimed_count", "finalized_count"):
            _non_negative_int(getattr(self, name), name)
        items = tuple(self.items)
        if len(items) > MAX_CLAIM_BATCH:
            raise ValueError("batch report exceeds its bound")
        if any(not isinstance(item, BatchItemReport) for item in items):
            raise TypeError("items must contain BatchItemReport values")
        if self.claimed_count != len(items):
            raise ValueError("claimed_count must match item count")
        if self.finalized_count > self.claimed_count:
            raise ValueError("finalized_count cannot exceed claimed_count")
        object.__setattr__(self, "items", items)

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "worker_ref": self.worker_ref,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "claimed_count": self.claimed_count,
            "finalized_count": self.finalized_count,
            "items": [item.as_dict() for item in self.items],
        })


class RuntimeBoundaryError(RuntimeError):
    """A repository contract violation that must fail the drain pass closed."""


def _commit_boundary(repository: ReadOnlyRuntimeRepository, phase: str) -> None:
    """Invoke an adapter's explicit commit hook when it provides one.

    The original pure fake repositories intentionally do not own a database
    cursor, so the hook remains optional for compatibility.  A production
    Odoo adapter implements it (usually as a validating no-op when it uses
    short-lived side cursors).
    """

    commit = getattr(repository, "commit", None)
    if commit is None:
        return
    if not callable(commit):
        raise RuntimeBoundaryError("repository commit boundary is not callable")
    try:
        commit(phase=phase)
    except Exception as exc:
        raise RuntimeBoundaryError("repository commit boundary failed") from exc


def _rollback_boundary(repository: ReadOnlyRuntimeRepository, phase: str) -> None:
    rollback = getattr(repository, "rollback", None)
    if rollback is None:
        return
    if not callable(rollback):
        raise RuntimeBoundaryError(
            "repository rollback boundary is not callable"
        )
    try:
        rollback(phase=phase)
    except Exception as exc:
        raise RuntimeBoundaryError(
            "repository rollback boundary failed"
        ) from exc


def _result_projection(result: HandlerResult) -> tuple[str, str]:
    if isinstance(result, Succeeded):
        return "succeeded", "succeeded"
    if isinstance(result, Skipped):
        return "skipped", "skipped"
    if isinstance(result, Retryable):
        return "retryable", result.error_class
    if isinstance(result, NeedsVerification):
        return "verification_required", "verification_required"
    if isinstance(result, NeedsReview):
        return "manual_review", result.reason_code
    if isinstance(result, TerminalFailure):
        return "failed_terminal", result.error_class
    raise TypeError("read handler returned an unsupported result")


def _normalize_result(result: HandlerResult, now: datetime) -> HandlerResult:
    """Turn malformed retry output into a safe manual-review outcome."""

    if isinstance(result, Retryable):
        if result.error_class not in KNOWN_ERROR_CLASSES:
            return NeedsReview(
                "unknown_error_class",
                "The read operation returned an unregistered error class.",
            )
        if result.retry_at <= now:
            return NeedsReview(
                "invalid_retry_schedule",
                "The read operation returned an invalid retry schedule.",
            )
    return result


@dataclass(frozen=True, slots=True)
class ReadOnlyCoordinator:
    """Claim, execute and finalize at most one bounded read-only batch."""

    repository: ReadOnlyRuntimeRepository
    handlers: ReadOnlyHandlerRegistry
    worker_ref: str
    max_batch: int = MAX_CLAIM_BATCH

    def __post_init__(self) -> None:
        if (
            not hasattr(self.repository, "claim_due")
            or not hasattr(self.repository, "finalize_attempt")
        ):
            raise TypeError("repository must implement the read-only runtime protocol")
        if not isinstance(self.handlers, ReadOnlyHandlerRegistry):
            raise TypeError("handlers must be a ReadOnlyHandlerRegistry")
        object.__setattr__(self, "worker_ref", _worker_ref(self.worker_ref))
        if (
            isinstance(self.max_batch, bool)
            or not isinstance(self.max_batch, int)
            or not 0 < self.max_batch <= MAX_CLAIM_BATCH
        ):
            raise ValueError(f"max_batch must be between 1 and {MAX_CLAIM_BATCH}")

    def _claims(self, now: datetime, limit: int) -> tuple[ClaimedWork, ...]:
        claims = self.repository.claim_due(
            now=now,
            worker_ref=self.worker_ref,
            limit=limit,
            phase=CLAIM_TRANSACTION,
        )
        if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
            raise RuntimeBoundaryError("claim repository returned an unbounded result")
        if len(claims) > limit:
            raise RuntimeBoundaryError("claim repository exceeded the requested batch")
        seen_jobs: set[int] = set()
        seen_tokens: set[str] = set()
        for claim in claims:
            if not isinstance(claim, ClaimedWork):
                raise RuntimeBoundaryError("claim repository returned an invalid claim")
            if claim.worker_ref != self.worker_ref:
                raise RuntimeBoundaryError("claim worker identity does not match")
            if claim.job_id in seen_jobs or claim.claim_token in seen_tokens:
                raise RuntimeBoundaryError("claim repository returned duplicate identity")
            seen_jobs.add(claim.job_id)
            seen_tokens.add(claim.claim_token)
        return tuple(claims)

    def run_once(self, *, now: datetime, limit: int | None = None) -> BatchReport:
        """Run one bounded pass; handler execution is outside DB boundaries."""

        _utc(now, "now")
        if limit is None:
            limit = self.max_batch
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 < limit <= self.max_batch:
            raise ValueError(f"limit must be between 1 and {self.max_batch}")

        claims = self._claims(now, limit)
        # The claim transaction must be complete before the first handler is
        # entered.  Side-cursor adapters have already committed and simply
        # validate this phase; caller-owned adapters commit here.
        _commit_boundary(self.repository, CLAIM_TRANSACTION)
        reports: list[BatchItemReport] = []
        finalized = 0
        for claim in claims:
            try:
                spec = self.handlers.require(claim.handler_key)
                result = spec.handler(claim)
                if not isinstance(result, (
                    Succeeded, Skipped, Retryable, NeedsVerification,
                    NeedsReview, TerminalFailure,
                )):
                    raise TypeError("unsupported handler result")
                result = _normalize_result(result, now)
            except UnknownReadHandler:
                result = NeedsReview(
                    "unknown_read_handler",
                    "Register the read operation before admitting this job.",
                    {"handler_key": claim.handler_key},
                )
            except Exception:
                # Never persist an exception string: it can contain payload,
                # credentials or customer data.  The durable adapter may add
                # its own redacted technical event around this safe outcome.
                result = NeedsReview(
                    "read_handler_exception",
                    "The read operation failed; inspect the redacted run evidence.",
                    {"handler_key": claim.handler_key},
                )

            try:
                outcome, reason = _result_projection(result)
                self.repository.finalize_attempt(
                    claim=claim,
                    result=result,
                    finished_at=now,
                    phase=FINALIZE_TRANSACTION,
                )
            except Exception as exc:
                _rollback_boundary(self.repository, FINALIZE_TRANSACTION)
                raise RuntimeBoundaryError(
                    "finalization failed for a claimed read job"
                ) from exc
            # Finalization is its own short transaction.  A side-cursor
            # adapter has already committed before returning; a caller-owned
            # adapter closes the boundary here.
            _commit_boundary(self.repository, FINALIZE_TRANSACTION)
            finalized += 1
            reports.append(BatchItemReport(
                job_id=claim.job_id,
                attempt_no=claim.attempt_no,
                outcome=outcome,
                finalized=True,
                reason_code=reason,
            ))

        return BatchReport(
            worker_ref=self.worker_ref,
            started_at=now,
            finished_at=now,
            claimed_count=len(claims),
            finalized_count=finalized,
            items=tuple(reports),
        )


__all__ = [
    "BatchItemReport",
    "BatchReport",
    "CLAIM_TRANSACTION",
    "ClaimedWork",
    "EXECUTION_PHASE",
    "FINALIZE_TRANSACTION",
    "READ_ONLY_RUNTIME_MODE",
    "ReadOnlyAdmissionDecision",
    "ReadOnlyAdmissionRequest",
    "ReadOnlyCoordinator",
    "ReadOnlyHandlerRegistry",
    "ReadOnlyHandlerSpec",
    "ReadOnlyRuntimeRepository",
    "READ_ONLY_OPERATION_KINDS",
    "RuntimeBoundaryError",
    "UnknownReadHandler",
    "admit_read_only",
]
