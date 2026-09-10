"""Frozen, JSON-shaped read DTO contracts.

The DTOs are intentionally boring value objects.  They do not query Odoo,
perform authorization, call Shopify or persist a second source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Mapping

from .identifiers import require_key, require_run_ref
from .immutability import freeze_value, to_plain
from .states import (
    OperationMode,
    Role,
    RunState,
    RuntimeHealth,
    SetupStepKey,
    StoreActivationState,
    StoreConfigurationState,
    StoreConnectionState,
    WorkflowReadiness,
)


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value


def _map(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise TypeError(f"{field_name} keys must be non-empty strings")
    return freeze_value(dict(value))


def _enum_value(value: Any, enum_type: type, field_name: str) -> str:
    """Normalize one locked string enum without leaking enum objects."""

    try:
        member = value if isinstance(value, enum_type) else enum_type(value)
    except (TypeError, ValueError) as exc:
        values = ", ".join(repr(item.value) for item in enum_type)
        raise ValueError(f"{field_name} must be one of: {values}") from exc
    return member.value


def _actions(value: tuple["AllowedActionDTO", ...] | list["AllowedActionDTO"]):
    result = tuple(value)
    if any(not isinstance(item, AllowedActionDTO) for item in result):
        raise TypeError("allowed_actions must contain AllowedActionDTO values")
    return result


@dataclass(frozen=True, slots=True)
class ResponseEnvelope:
    """Common envelope required by every composed read response."""

    contract_version: int
    generated_at: datetime
    data_through: datetime
    store_generation: int
    correlation_id: str
    data: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.contract_version, bool) or self.contract_version != 1:
            raise ValueError("only contract_version 1 is supported")
        _utc(self.generated_at, "generated_at")
        _utc(self.data_through, "data_through")
        if self.data_through > self.generated_at:
            raise ValueError("data_through cannot be later than generated_at")
        if not isinstance(self.store_generation, int) or isinstance(self.store_generation, bool):
            raise TypeError("store_generation must be an integer")
        if self.store_generation < 0:
            raise ValueError("store_generation cannot be negative")
        if not isinstance(self.correlation_id, str) or not self.correlation_id.strip():
            raise ValueError("correlation_id must be non-empty")
        object.__setattr__(self, "data", _map(self.data, "data"))

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "contract_version": self.contract_version,
            "generated_at": self.generated_at.isoformat(),
            "data_through": self.data_through.isoformat(),
            "store_generation": self.store_generation,
            "correlation_id": self.correlation_id,
            "data": self.data,
        })


CommonEnvelope = ResponseEnvelope
ReadEnvelope = ResponseEnvelope


@dataclass(frozen=True, slots=True)
class AllowedActionDTO:
    key: str
    label: str
    item_ref: str | None = None
    required_role: str | None = None
    requires_reason: bool = False
    input_schema: Mapping[str, Any] = field(default_factory=dict)
    consequence: str | None = None
    # Native targets are produced by the authorized server projection.  The
    # client may select this target, but it must never construct a model,
    # domain, or action dictionary of its own.
    target: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        require_key(self.key, "action key")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("action label must be non-empty")
        if self.item_ref is not None and not isinstance(self.item_ref, str):
            raise TypeError("item_ref must be a string or None")
        if self.required_role is not None:
            object.__setattr__(
                self,
                "required_role",
                _enum_value(self.required_role, Role, "required_role"),
            )
        if not isinstance(self.requires_reason, bool):
            raise TypeError("requires_reason must be bool")
        object.__setattr__(self, "input_schema", _map(self.input_schema, "input_schema"))
        if self.target is not None:
            object.__setattr__(self, "target", _map(self.target, "target"))


@dataclass(frozen=True, slots=True)
class StoreSummaryDTO:
    id: int
    name: str
    shop_domain: str
    company: Mapping[str, Any]
    connection: str
    configuration: str
    activation: str
    runtime_health: str

    def __post_init__(self) -> None:
        if not isinstance(self.id, int) or isinstance(self.id, bool) or self.id <= 0:
            raise ValueError("store id must be a positive integer")
        for name in ("name", "shop_domain", "connection", "configuration", "activation", "runtime_health"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be non-empty")
        object.__setattr__(
            self,
            "connection",
            _enum_value(self.connection, StoreConnectionState, "connection"),
        )
        object.__setattr__(
            self,
            "configuration",
            _enum_value(self.configuration, StoreConfigurationState, "configuration"),
        )
        object.__setattr__(
            self,
            "activation",
            _enum_value(self.activation, StoreActivationState, "activation"),
        )
        object.__setattr__(
            self,
            "runtime_health",
            _enum_value(self.runtime_health, RuntimeHealth, "runtime_health"),
        )
        object.__setattr__(self, "company", _map(self.company, "company"))


@dataclass(frozen=True, slots=True)
class HealthDTO:
    title: str
    reason: str
    severity: str
    observed_at: datetime
    next_check_at: datetime | None
    score: int | None
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("health title must be non-empty")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("health reason must be non-empty")
        if self.severity not in {"critical", "warning", "info"}:
            raise ValueError("severity must be critical, warning or info")
        _utc(self.observed_at, "observed_at")
        if self.next_check_at is not None:
            _utc(self.next_check_at, "next_check_at")
        if self.score is not None and (not isinstance(self.score, int) or isinstance(self.score, bool)):
            raise TypeError("score must be an integer or None")
        object.__setattr__(self, "allowed_actions", _actions(self.allowed_actions))


@dataclass(frozen=True, slots=True)
class WorkflowSummaryDTO:
    key: str
    label: str
    readiness: str
    health: str
    freshness: Mapping[str, Any]
    attention_count: int
    latest_run_ref: str | None

    def __post_init__(self) -> None:
        require_key(self.key, "workflow key")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("workflow label must be non-empty")
        object.__setattr__(
            self,
            "readiness",
            _enum_value(self.readiness, WorkflowReadiness, "readiness"),
        )
        object.__setattr__(
            self,
            "health",
            _enum_value(self.health, RuntimeHealth, "health"),
        )
        if not isinstance(self.attention_count, int) or isinstance(self.attention_count, bool) or self.attention_count < 0:
            raise ValueError("attention_count must be a non-negative integer")
        if self.latest_run_ref is not None:
            require_run_ref(self.latest_run_ref)
        object.__setattr__(self, "freshness", _map(self.freshness, "freshness"))


@dataclass(frozen=True, slots=True)
class ActivityDTO:
    window_days: int
    succeeded: int
    held: int
    series: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        for name in ("window_days", "succeeded", "held"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")
        object.__setattr__(self, "series", tuple(_map(item, "series item") for item in self.series))


@dataclass(frozen=True, slots=True)
class OverviewDTO:
    store: StoreSummaryDTO
    health: HealthDTO
    workflows: tuple[WorkflowSummaryDTO, ...]
    attention: Mapping[str, Any]
    activity: ActivityDTO
    permissions: Mapping[str, Any]
    allowed_stores: tuple[Mapping[str, Any], ...] = ()
    all_stores: Mapping[str, Any] = field(
        default_factory=lambda: {"allowed": False, "read_only": True, "selected": False},
    )
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.store, StoreSummaryDTO):
            raise TypeError("store must be StoreSummaryDTO")
        if not isinstance(self.health, HealthDTO):
            raise TypeError("health must be HealthDTO")
        if not isinstance(self.activity, ActivityDTO):
            raise TypeError("activity must be ActivityDTO")
        object.__setattr__(self, "workflows", tuple(self.workflows))
        if any(not isinstance(item, WorkflowSummaryDTO) for item in self.workflows):
            raise TypeError("workflows must contain WorkflowSummaryDTO values")
        object.__setattr__(self, "attention", _map(self.attention, "attention"))
        object.__setattr__(self, "permissions", _map(self.permissions, "permissions"))
        object.__setattr__(
            self,
            "allowed_stores",
            tuple(_map(item, "allowed_stores item") for item in self.allowed_stores),
        )
        object.__setattr__(self, "all_stores", _map(self.all_stores, "all_stores"))
        object.__setattr__(self, "allowed_actions", _actions(self.allowed_actions))


@dataclass(frozen=True, slots=True)
class AttentionItemDTO:
    item_ref: str
    state_version: int
    provider: str
    workflow: str
    severity: str
    title: str
    impact_summary: str
    age_seconds: int
    owner_role: str
    store_id: int
    run_ref: str | None
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.item_ref, str) or not self.item_ref.strip():
            raise ValueError("item_ref must be non-empty")
        if not isinstance(self.state_version, int) or isinstance(self.state_version, bool) or self.state_version <= 0:
            raise ValueError("state_version must be positive")
        require_key(self.provider, "provider")
        require_key(self.workflow, "workflow")
        if self.severity not in {"critical", "warning", "info"}:
            raise ValueError("severity must be critical, warning or info")
        for name in ("title", "impact_summary", "owner_role"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be non-empty")
        object.__setattr__(self, "owner_role", _enum_value(self.owner_role, Role, "owner_role"))
        if not isinstance(self.age_seconds, int) or isinstance(self.age_seconds, bool) or self.age_seconds < 0:
            raise ValueError("age_seconds must be non-negative")
        if not isinstance(self.store_id, int) or isinstance(self.store_id, bool) or self.store_id <= 0:
            raise ValueError("store_id must be positive")
        if self.run_ref is not None:
            require_run_ref(self.run_ref)
        object.__setattr__(self, "allowed_actions", _actions(self.allowed_actions))


@dataclass(frozen=True, slots=True)
class EvidenceGroupDTO:
    key: str
    label: str
    rows: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        require_key(self.key, "evidence group key")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("evidence group label must be non-empty")
        object.__setattr__(self, "rows", tuple(_map(item, "evidence row") for item in self.rows))


@dataclass(frozen=True, slots=True)
class AttentionDetailDTO(AttentionItemDTO):
    what_happened: str = ""
    impact: Mapping[str, Any] = field(default_factory=dict)
    evidence_groups: tuple[EvidenceGroupDTO, ...] = ()
    history: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        # Call explicitly because ``@dataclass(slots=True)`` creates a
        # replacement class and zero-argument ``super()`` is not reliable in
        # the generated subclass method on supported Python versions.
        AttentionItemDTO.__post_init__(self)
        if not isinstance(self.what_happened, str) or not self.what_happened.strip():
            raise ValueError("what_happened must be non-empty")
        object.__setattr__(self, "impact", _map(self.impact, "impact"))
        object.__setattr__(self, "evidence_groups", tuple(self.evidence_groups))
        if any(not isinstance(item, EvidenceGroupDTO) for item in self.evidence_groups):
            raise TypeError("evidence_groups must contain EvidenceGroupDTO values")
        object.__setattr__(self, "history", tuple(_map(item, "history item") for item in self.history))


@dataclass(frozen=True, slots=True)
class TimelineEventDTO:
    event_id: int
    occurred_at: datetime
    kind: str
    tone: str
    title: str
    detail: str
    technical_detail_available: bool

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, int) or isinstance(self.event_id, bool) or self.event_id <= 0:
            raise ValueError("event_id must be positive")
        _utc(self.occurred_at, "occurred_at")
        for name in ("kind", "tone", "title", "detail"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be non-empty")
        if not isinstance(self.technical_detail_available, bool):
            raise TypeError("technical_detail_available must be bool")


@dataclass(frozen=True, slots=True)
class RunDTO:
    run_ref: str
    display_name: str
    state: str | RunState
    workflow: str
    operation: str
    store: Mapping[str, Any]
    trigger: Mapping[str, Any]
    scope: Mapping[str, Any]
    configuration_generation: int
    result: Mapping[str, Any]
    jobs: tuple[Mapping[str, Any], ...]
    timeline: tuple[TimelineEventDTO, ...]
    affected_records: tuple[Mapping[str, Any], ...]
    allowed_actions: tuple[AllowedActionDTO, ...] = ()
    truncation: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_run_ref(self.run_ref)
        if not isinstance(self.display_name, str) or not self.display_name.strip():
            raise ValueError("display_name must be non-empty")
        for name in ("workflow", "operation"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be non-empty")
        require_key(self.workflow, "workflow")
        require_key(self.operation, "operation")
        state = self.state.value if isinstance(self.state, RunState) else self.state
        if state not in {item.value for item in RunState}:
            raise ValueError(f"unknown run state: {state!r}")
        if not isinstance(self.configuration_generation, int) or isinstance(self.configuration_generation, bool) or self.configuration_generation < 0:
            raise ValueError("configuration_generation must be non-negative")
        object.__setattr__(self, "state", state)
        for name in ("store", "trigger", "scope", "result"):
            object.__setattr__(self, name, _map(getattr(self, name), name))
        object.__setattr__(self, "jobs", tuple(_map(item, "job") for item in self.jobs))
        object.__setattr__(self, "timeline", tuple(self.timeline))
        if any(not isinstance(item, TimelineEventDTO) for item in self.timeline):
            raise TypeError("timeline must contain TimelineEventDTO values")
        object.__setattr__(self, "affected_records", tuple(_map(item, "affected record") for item in self.affected_records))
        object.__setattr__(self, "allowed_actions", _actions(self.allowed_actions))
        object.__setattr__(self, "truncation", _map(self.truncation, "truncation"))


@dataclass(frozen=True, slots=True)
class SetupStepDTO:
    step_key: str
    state: str
    completed_at: datetime | None
    blocking_count: int
    next_route: str | None
    display_ordinal: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "step_key",
            _enum_value(self.step_key, SetupStepKey, "step_key"),
        )
        if not isinstance(self.state, str) or not self.state.strip():
            raise ValueError("step state must be non-empty")
        if self.completed_at is not None:
            _utc(self.completed_at, "completed_at")
        if not isinstance(self.blocking_count, int) or isinstance(self.blocking_count, bool) or self.blocking_count < 0:
            raise ValueError("blocking_count must be non-negative")
        if self.next_route is not None and (not isinstance(self.next_route, str) or not self.next_route.strip()):
            raise ValueError("next_route must be non-empty or None")
        if self.display_ordinal is not None and (not isinstance(self.display_ordinal, int) or isinstance(self.display_ordinal, bool) or self.display_ordinal < 1):
            raise ValueError("display_ordinal must be positive or None")


@dataclass(frozen=True, slots=True)
class SetupDTO:
    store: Mapping[str, Any]
    steps: tuple[SetupStepDTO, ...]
    current_step: SetupStepDTO | None
    readiness_groups: tuple[Mapping[str, Any], ...]
    activation_preview: Mapping[str, Any]
    permissions: Mapping[str, Any]
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "store", _map(self.store, "store"))
        object.__setattr__(self, "steps", tuple(self.steps))
        if any(not isinstance(item, SetupStepDTO) for item in self.steps):
            raise TypeError("steps must contain SetupStepDTO values")
        keys = [item.step_key for item in self.steps]
        if len(keys) != len(set(keys)):
            raise ValueError("setup step_key values must be unique")
        if self.current_step is not None and not isinstance(self.current_step, SetupStepDTO):
            raise TypeError("current_step must be SetupStepDTO or None")
        if self.current_step is not None and self.current_step.step_key not in keys:
            raise ValueError("current_step must be one of the supplied steps")
        object.__setattr__(self, "readiness_groups", tuple(_map(item, "readiness group") for item in self.readiness_groups))
        object.__setattr__(self, "activation_preview", _map(self.activation_preview, "activation_preview"))
        object.__setattr__(self, "permissions", _map(self.permissions, "permissions"))
        object.__setattr__(self, "allowed_actions", _actions(self.allowed_actions))


@dataclass(frozen=True, slots=True)
class OperationOptionDTO:
    """One currently supported P15 operation-launcher option.

    The first backend slice is deliberately narrower than the long-term V2
    operation contract: every option is an Administrator-only exact-store
    read/scan or reconciliation control, with no filters or preview/mutation
    mode.  Keeping these constraints in the DTO prevents an adapter from
    advertising a capability that the named command cannot safely execute.
    """

    operation_key: str
    label: str
    workflow: str
    mode: str
    required_role: str | None
    available_scopes: tuple[str, ...]
    filter_schema: Mapping[str, Any]
    source_of_truth_summary: str
    side_effect_summary: str
    readiness: str
    disabled_reason: str | None = None

    def __post_init__(self) -> None:
        require_key(self.operation_key, "operation_key")
        for name in ("label", "workflow", "source_of_truth_summary", "side_effect_summary", "readiness"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be non-empty")
        require_key(self.workflow, "workflow")
        mode = _enum_value(self.mode, OperationMode, "mode")
        if mode not in (
            OperationMode.READ.value,
            OperationMode.RECONCILIATION.value,
        ):
            raise ValueError(
                "P15 operation options support read or reconciliation only"
            )
        object.__setattr__(self, "mode", mode)
        if self.required_role is not None:
            object.__setattr__(
                self,
                "required_role",
                _enum_value(self.required_role, Role, "required_role"),
            )
        object.__setattr__(
            self,
            "readiness",
            _enum_value(self.readiness, WorkflowReadiness, "readiness"),
        )
        if isinstance(self.available_scopes, (str, bytes)) or not isinstance(
            self.available_scopes, (list, tuple)
        ):
            raise TypeError("available_scopes must be a sequence of strings")
        if any(not isinstance(item, str) or not item.strip() for item in self.available_scopes):
            raise ValueError("available_scopes must contain non-empty strings")
        scopes = tuple(self.available_scopes)
        if scopes != ("store",):
            raise ValueError(
                "P15 operation options support the exact store scope only"
            )
        object.__setattr__(self, "available_scopes", scopes)
        filter_schema = _map(self.filter_schema, "filter_schema")
        if filter_schema:
            raise ValueError(
                "P15 operation options do not support client filters yet"
            )
        object.__setattr__(self, "filter_schema", filter_schema)
        if self.disabled_reason is not None and (not isinstance(self.disabled_reason, str) or not self.disabled_reason.strip()):
            raise ValueError("disabled_reason must be non-empty or None")


__all__ = [
    "AllowedActionDTO",
    "AttentionDetailDTO",
    "AttentionItemDTO",
    "ActivityDTO",
    "CommonEnvelope",
    "EvidenceGroupDTO",
    "HealthDTO",
    "OperationOptionDTO",
    "OverviewDTO",
    "ReadEnvelope",
    "ResponseEnvelope",
    "RunDTO",
    "SetupDTO",
    "SetupStepDTO",
    "StoreSummaryDTO",
    "TimelineEventDTO",
    "WorkflowSummaryDTO",
]
