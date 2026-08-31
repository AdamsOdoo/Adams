"""Pure contracts for the P15 store-administration boundary.

The legacy Odoo models remain the source of truth.  This module contains only
the small value objects and deterministic helpers used by the P15 adapters:
canonical Shopify identity, optimistic-concurrency fingerprints, lifecycle
admission, capacity, and the typed admin/read projections.  Keeping these
rules importable without Odoo makes the dangerous parts easy to characterize
in the dependency-free test lane.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, fields as dataclass_fields
from datetime import datetime, timedelta
from typing import Any

from .dto import (
    AllowedActionDTO,
    StoreSummaryDTO,
    WorkflowSummaryDTO,
)
from .immutability import freeze_value, to_plain
from .states import (
    CommandStatus,
    Role,
    SetupStepKey,
    StoreActivationState,
    StoreConnectionState,
    StoreConfigurationState,
    RuntimeHealth,
    WorkflowReadiness,
)


# Shopify permanent domains are one lowercase shop handle plus the fixed
# suffix.  The handle is a DNS label (63 bytes maximum and no trailing '-').
# A strict identity is important: the value is later used as an HTTPS host and
# compared byte-for-byte with Shopify's ``myshopifyDomain`` response.
SHOPIFY_DOMAIN_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$",
)

SUPPORTED_STORE_CAPACITY = 10
MAX_SUPPORTED_STORES = SUPPORTED_STORE_CAPACITY

_UTC = timedelta(0)
_FINGERPRINT_EXCLUDED_KEYS = frozenset({
    "generated_at",
    "requested_at",
    "correlation_id",
    "timestamp",
    "created_at",
    "updated_at",
    "display_label",
    "label",
})
_RAW_SECRET_KEYS = frozenset({
    "access_token",
    "client_secret",
    "client_secret_value",
    "password",
    "secret",
})


class StoreAdminContractError(ValueError):
    """Base error for invalid P15 pure contract input."""


class StoreCapacityExceeded(StoreAdminContractError):
    """Raised before a store create would exceed the supported profile."""


class LifecycleTransitionError(StoreAdminContractError):
    """Raised when a lifecycle command cannot move between two states."""


def canonical_shop_domain(value: str) -> str:
    """Return the one canonical Shopify domain representation.

    User-entered outer whitespace and case are normalized, but schemes,
    paths, ports, trailing dots, Unicode/underscore labels and subdomains are
    rejected.  The returned string is suitable for both the transport host
    and exact remote-identity comparisons.
    """

    if not isinstance(value, str):
        raise TypeError("shop_domain must be a string")
    candidate = value.strip().lower()
    if not SHOPIFY_DOMAIN_RE.fullmatch(candidate):
        raise StoreAdminContractError(
            "shop_domain must be a canonical *.myshopify.com domain"
        )
    return candidate


def is_canonical_shop_domain(value: Any) -> bool:
    """Whether ``value`` is already canonical, without raising."""

    if not isinstance(value, str):
        return False
    try:
        return canonical_shop_domain(value) == value
    except (TypeError, ValueError):
        return False


def _json_value(value: Any, path: str = "$") -> Any:
    """Normalize a JSON-shaped fingerprint input without lossy coercion."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        # ``allow_nan=False`` below supplies the final guard; rejecting here
        # gives a stable contract error rather than platform-specific JSON.
        if value != value or value in (float("inf"), float("-inf")):
            raise StoreAdminContractError(f"{path} must be finite")
        return value
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != _UTC:
            raise StoreAdminContractError(f"{path} must be UTC")
        return value.isoformat()
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise StoreAdminContractError(
                    f"{path} contains a non-empty string key requirement"
                )
            if key in _FINGERPRINT_EXCLUDED_KEYS:
                continue
            result[key] = _json_value(item, f"{path}.{key}")
        return result
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [
            _json_value(item, f"{path}[{index}]")
            for index, item in enumerate(value)
        ]
    raise StoreAdminContractError(
        f"{path} contains unsupported {type(value).__name__}"
    )


def canonical_json(value: Mapping[str, Any]) -> str:
    """Encode a deterministic, timestamp/display-label-free JSON payload."""

    if not isinstance(value, Mapping):
        raise TypeError("fingerprint payload must be a mapping")
    normalized = _json_value(value)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def configuration_fingerprint(payload: Mapping[str, Any]) -> str:
    """Return the stable SHA-256 configuration/readiness fingerprint."""

    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def store_configuration_fingerprint(
    *,
    store_id: int,
    company_id: int,
    generation: int,
    operation: str,
    values: Mapping[str, Any],
    preconditions: Mapping[str, Any] | None = None,
) -> str:
    """Fingerprint one store-scoped command snapshot.

    Store/company identity, generation, operation, values and explicit
    preconditions are included.  The canonical encoder excludes only
    timestamps/correlation/display labels; it never drops a business value.
    """

    return configuration_fingerprint({
        "store_id": store_id,
        "company_id": company_id,
        "generation": generation,
        "operation": operation,
        "values": values,
        "preconditions": preconditions or {},
    })


def ensure_store_capacity(
    current_count: int,
    requested_delta: int = 1,
    *,
    capacity: int = SUPPORTED_STORE_CAPACITY,
) -> int:
    """Fail closed unless the resulting database store count is supported."""

    if isinstance(current_count, bool) or not isinstance(current_count, int):
        raise TypeError("current_count must be an integer")
    if isinstance(requested_delta, bool) or not isinstance(requested_delta, int):
        raise TypeError("requested_delta must be an integer")
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
        raise ValueError("capacity must be a positive integer")
    if current_count < 0 or requested_delta < 0:
        raise ValueError("store counts cannot be negative")
    resulting = current_count + requested_delta
    if resulting > capacity:
        raise StoreCapacityExceeded(
            "This database supports at most %d Shopify stores; the requested "
            "operation would create %d." % (capacity, resulting)
        )
    return resulting


LIFECYCLE_TRANSITIONS = {
    "setup_incomplete": frozenset(("connected", "disconnecting")),
    "connected": frozenset(("reconnect_needed", "disconnecting")),
    "reconnect_needed": frozenset(("connected", "disconnecting")),
    "disconnecting": frozenset(("disconnected",)),
    "disconnected": frozenset(),
}

# Connection lifecycle and operator activation are intentionally separate
# dimensions.  A paused store may remain connected for diagnostics, while a
# retired store cannot be resumed without a new explicit setup/reconnect
# decision.  The service layer adds the safety precondition that retirement
# is only legal after disconnected quiescence.
ACTIVATION_TRANSITIONS = {
    "draft": frozenset(("active", "retired")),
    "active": frozenset(("paused", "retired")),
    "paused": frozenset(("active", "retired")),
    "retired": frozenset(),
}


def lifecycle_transition(current: str, target: str) -> str:
    """Validate the one-way lifecycle state machine and return ``target``."""

    if current not in LIFECYCLE_TRANSITIONS:
        raise LifecycleTransitionError("unknown current lifecycle state")
    if target not in LIFECYCLE_TRANSITIONS:
        raise LifecycleTransitionError("unknown target lifecycle state")
    if current == target:
        return target
    if target not in LIFECYCLE_TRANSITIONS[current]:
        raise LifecycleTransitionError(
            "lifecycle transition %s -> %s is not permitted" % (current, target)
        )
    return target


def activation_transition(current: str, target: str) -> str:
    """Validate the independent operator activation state machine."""

    if current not in ACTIVATION_TRANSITIONS:
        raise LifecycleTransitionError("unknown current activation state")
    if target not in ACTIVATION_TRANSITIONS:
        raise LifecycleTransitionError("unknown target activation state")
    if current == target:
        return target
    if target not in ACTIVATION_TRANSITIONS[current]:
        raise LifecycleTransitionError(
            "activation transition %s -> %s is not permitted" % (current, target)
        )
    return target


def require_setup_step_key(value: str) -> str:
    """Validate a durable semantic setup key; numeric ordinals are rejected."""

    if isinstance(value, SetupStepKey):
        return value.value
    if not isinstance(value, str):
        raise TypeError("setup step key must be a string")
    try:
        return SetupStepKey(value).value
    except ValueError as exc:
        raise StoreAdminContractError("unsupported setup step key") from exc


def _positive_int(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise StoreAdminContractError(f"{name} must be a positive integer")


def _non_negative_int(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise StoreAdminContractError(f"{name} must be a non-negative integer")


def _utc(value: Any, name: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be datetime")
    if value.tzinfo is None or value.utcoffset() != _UTC:
        raise ValueError(f"{name} must be timezone-aware UTC")


def _text(value: Any, name: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    if not isinstance(value, str) or not value.strip():
        raise StoreAdminContractError(f"{name} must be non-empty")


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return freeze_value(dict(value))


def _reject_raw_secret_keys(value: Any, path: str = "$") -> None:
    """Reject credential material before it can enter an admin DTO.

    Presence/verification booleans are intentionally valid DTO values.  Raw
    credential names are not: keeping this invariant in the pure contracts
    protects future adapters in addition to the current Odoo projection.
    """

    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                continue
            normalized = key.casefold()
            if (
                normalized in _RAW_SECRET_KEYS
                or normalized.endswith("_access_token")
                or normalized.endswith("_client_secret")
            ):
                raise StoreAdminContractError(
                    "%s contains raw credential material" % path
                )
            _reject_raw_secret_keys(item, "%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_raw_secret_keys(item, "%s[%d]" % (path, index))


@dataclass(frozen=True, slots=True)
class SettingsFieldDTO:
    """One typed, non-secret effective settings value."""

    key: str
    value: Any
    value_type: str
    source: str = "store_settings"
    schema: Mapping[str, Any] = field(default_factory=dict)
    readiness_impact: bool = False
    last_changed_at: datetime | None = None

    def __post_init__(self) -> None:
        _text(self.key, "settings field key")
        _reject_raw_secret_keys({self.key: self.value}, "settings field")
        if self.value_type not in {
            "boolean", "integer", "number", "selection", "reference", "text",
        }:
            raise StoreAdminContractError("unsupported settings value_type")
        _text(self.source, "settings field source")
        if not isinstance(self.readiness_impact, bool):
            raise TypeError("readiness_impact must be bool")
        _utc(self.last_changed_at, "last_changed_at", optional=True)
        object.__setattr__(self, "schema", _mapping(self.schema, "schema"))
        # The value must be JSON-shaped.  This deliberately rejects an Odoo
        # recordset accidentally crossing the typed boundary.
        object.__setattr__(self, "value", freeze_value(self.value))


@dataclass(frozen=True, slots=True)
class SettingsGroupDTO:
    """One registered logical settings group and its revision fingerprint."""

    key: str
    label: str
    revision: int
    fingerprint: str
    fields: tuple[SettingsFieldDTO, ...] = ()
    readiness_impact: bool = False
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        _text(self.key, "settings group key")
        _text(self.label, "settings group label")
        _non_negative_int(self.revision, "settings group revision")
        if not re.fullmatch(r"[0-9a-f]{64}", self.fingerprint or ""):
            raise StoreAdminContractError("settings fingerprint must be SHA-256")
        object.__setattr__(self, "fields", tuple(self.fields))
        if any(not isinstance(item, SettingsFieldDTO) for item in self.fields):
            raise TypeError("settings fields must contain SettingsFieldDTO")
        if len({item.key for item in self.fields}) != len(self.fields):
            raise StoreAdminContractError("settings field keys must be unique")
        if not isinstance(self.readiness_impact, bool):
            raise TypeError("readiness_impact must be bool")
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        if any(not isinstance(item, AllowedActionDTO) for item in self.allowed_actions):
            raise TypeError("allowed_actions must contain AllowedActionDTO")


@dataclass(frozen=True, slots=True)
class StoreSettingsDTO:
    """Typed settings projection for exactly one store."""

    store_id: int
    company_id: int
    configuration_generation: int
    groups: tuple[SettingsGroupDTO, ...]
    effective_values: Mapping[str, Any]
    fingerprint: str
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        _positive_int(self.store_id, "store_id")
        _positive_int(self.company_id, "company_id")
        _non_negative_int(self.configuration_generation, "configuration_generation")
        object.__setattr__(self, "groups", tuple(self.groups))
        if any(not isinstance(item, SettingsGroupDTO) for item in self.groups):
            raise TypeError("groups must contain SettingsGroupDTO")
        if len({item.key for item in self.groups}) != len(self.groups):
            raise StoreAdminContractError("settings group keys must be unique")
        object.__setattr__(
            self, "effective_values", _mapping(self.effective_values, "effective_values")
        )
        _reject_raw_secret_keys(self.effective_values, "effective_values")
        if not re.fullmatch(r"[0-9a-f]{64}", self.fingerprint or ""):
            raise StoreAdminContractError("settings fingerprint must be SHA-256")
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        if any(not isinstance(item, AllowedActionDTO) for item in self.allowed_actions):
            raise TypeError("allowed_actions must contain AllowedActionDTO")


@dataclass(frozen=True, slots=True)
class ReadinessCheckDTO:
    """One core or registered-domain readiness result."""

    code: str
    tier: str
    result: str
    reason: str
    not_applicable: bool = False
    owner: str = "core"

    def __post_init__(self) -> None:
        _text(self.code, "readiness code")
        if self.tier not in {"essential", "warning"}:
            raise StoreAdminContractError("readiness tier is invalid")
        if self.result not in {"pass", "fail", "warning", "not_proven"}:
            raise StoreAdminContractError("readiness result is invalid")
        _text(self.reason, "readiness reason")
        if not isinstance(self.not_applicable, bool):
            raise TypeError("not_applicable must be bool")
        _text(self.owner, "readiness owner")


@dataclass(frozen=True, slots=True)
class ReadinessDTO:
    """Bounded readiness snapshot with its configuration fingerprint."""

    store_id: int
    overall_result: str
    checked_at: datetime | None
    stale: bool
    checks: tuple[ReadinessCheckDTO, ...]
    fingerprint: str
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        _positive_int(self.store_id, "store_id")
        if self.overall_result not in {"pass", "fail", "warning", "not_run"}:
            raise StoreAdminContractError("overall readiness result is invalid")
        _utc(self.checked_at, "checked_at", optional=True)
        if not isinstance(self.stale, bool):
            raise TypeError("stale must be bool")
        object.__setattr__(self, "checks", tuple(self.checks))
        if any(not isinstance(item, ReadinessCheckDTO) for item in self.checks):
            raise TypeError("checks must contain ReadinessCheckDTO")
        if len({item.code for item in self.checks}) != len(self.checks):
            raise StoreAdminContractError("readiness codes must be unique")
        if not re.fullmatch(r"[0-9a-f]{64}", self.fingerprint or ""):
            raise StoreAdminContractError("readiness fingerprint must be SHA-256")
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        if any(not isinstance(item, AllowedActionDTO) for item in self.allowed_actions):
            raise TypeError("allowed_actions must contain AllowedActionDTO")


@dataclass(frozen=True, slots=True)
class StoreListItemDTO:
    """One safe store-list item; no credential material is representable."""

    store: StoreSummaryDTO
    connection_generation: int
    workflows: tuple[WorkflowSummaryDTO, ...]
    setup_continuation: Mapping[str, Any]
    freshness: Mapping[str, Any]
    attention_count: int = 0
    allowed_actions: tuple[AllowedActionDTO, ...] = ()
    attention_truncated: bool = False
    attention_partial: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.store, StoreSummaryDTO):
            raise TypeError("store must be StoreSummaryDTO")
        _non_negative_int(self.connection_generation, "connection_generation")
        object.__setattr__(self, "workflows", tuple(self.workflows))
        if any(not isinstance(item, WorkflowSummaryDTO) for item in self.workflows):
            raise TypeError("workflows must contain WorkflowSummaryDTO")
        object.__setattr__(
            self, "setup_continuation", _mapping(self.setup_continuation, "setup_continuation")
        )
        object.__setattr__(self, "freshness", _mapping(self.freshness, "freshness"))
        _non_negative_int(self.attention_count, "attention_count")
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        if any(not isinstance(item, AllowedActionDTO) for item in self.allowed_actions):
            raise TypeError("allowed_actions must contain AllowedActionDTO")
        if not isinstance(self.attention_truncated, bool):
            raise TypeError("attention_truncated must be bool")
        if not isinstance(self.attention_partial, bool):
            raise TypeError("attention_partial must be bool")


@dataclass(frozen=True, slots=True)
class StoreListDTO:
    """Bounded, active-company store list response payload."""

    stores: tuple[StoreListItemDTO, ...]
    limit: int
    next_cursor: str | None
    has_more: bool
    capacity: Mapping[str, Any]
    allowed_actions: tuple[AllowedActionDTO, ...] = ()
    can_create_store: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "stores", tuple(self.stores))
        if any(not isinstance(item, StoreListItemDTO) for item in self.stores):
            raise TypeError("stores must contain StoreListItemDTO")
        if isinstance(self.limit, bool) or not isinstance(self.limit, int) or self.limit <= 0:
            raise StoreAdminContractError("limit must be positive")
        if self.next_cursor is not None:
            _text(self.next_cursor, "next_cursor")
        if not isinstance(self.has_more, bool):
            raise TypeError("has_more must be bool")
        object.__setattr__(self, "capacity", _mapping(self.capacity, "capacity"))
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        if any(not isinstance(item, AllowedActionDTO) for item in self.allowed_actions):
            raise TypeError("allowed_actions must contain AllowedActionDTO")
        if not isinstance(self.can_create_store, bool):
            raise TypeError("can_create_store must be bool")


# Names used by early P15 consumers; keeping aliases avoids forcing clients to
# know whether a method calls the object a response or a payload.
StoreListResponseDTO = StoreListDTO


@dataclass(frozen=True, slots=True)
class StoreAdminSummaryDTO:
    """Administrator-safe 360 projection for one exact store."""

    store: StoreSummaryDTO
    connection_generation: int
    configuration_generation: int
    lifecycle: Mapping[str, Any]
    credentials: Mapping[str, Any]
    capabilities: Mapping[str, Any]
    webhooks: Mapping[str, Any]
    readiness: ReadinessDTO
    identity_immutability: Mapping[str, Any]
    allowed_actions: tuple[AllowedActionDTO, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.store, StoreSummaryDTO):
            raise TypeError("store must be StoreSummaryDTO")
        _non_negative_int(self.connection_generation, "connection_generation")
        _non_negative_int(self.configuration_generation, "configuration_generation")
        for name in (
            "lifecycle", "credentials", "capabilities", "webhooks",
            "identity_immutability",
        ):
            object.__setattr__(self, name, _mapping(getattr(self, name), name))
        _reject_raw_secret_keys(self.credentials, "credentials")
        if not isinstance(self.readiness, ReadinessDTO):
            raise TypeError("readiness must be ReadinessDTO")
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        if any(not isinstance(item, AllowedActionDTO) for item in self.allowed_actions):
            raise TypeError("allowed_actions must contain AllowedActionDTO")


@dataclass(frozen=True, slots=True)
class StoreSetupDTO:
    """Resumable setup projection addressed only by semantic step keys."""

    store_id: int
    resume_step_key: str
    resume_step: int
    steps: tuple[Mapping[str, Any], ...]
    readiness: ReadinessDTO
    configuration_generation: int
    activation_preview: Mapping[str, Any]
    allowed_actions: tuple[AllowedActionDTO, ...] = ()
    step_values: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _positive_int(self.store_id, "store_id")
        object.__setattr__(self, "resume_step_key", require_setup_step_key(self.resume_step_key))
        if isinstance(self.resume_step, bool) or not isinstance(self.resume_step, int) or self.resume_step <= 0:
            raise StoreAdminContractError("resume_step must be positive")
        object.__setattr__(self, "steps", tuple(_mapping(item, "setup step") for item in self.steps))
        if not isinstance(self.readiness, ReadinessDTO):
            raise TypeError("readiness must be ReadinessDTO")
        _non_negative_int(self.configuration_generation, "configuration_generation")
        object.__setattr__(
            self, "activation_preview", _mapping(self.activation_preview, "activation_preview")
        )
        object.__setattr__(self, "step_values", _mapping(self.step_values, "step_values"))
        _reject_raw_secret_keys(self.step_values, "step_values")
        object.__setattr__(self, "allowed_actions", tuple(self.allowed_actions))
        if any(not isinstance(item, AllowedActionDTO) for item in self.allowed_actions):
            raise TypeError("allowed_actions must contain AllowedActionDTO")


def dto_as_dict(value: Any) -> Any:
    """Strict recursive conversion for pure tests and non-Odoo callers."""

    if hasattr(value, "__dataclass_fields__"):
        return {
            item.name: dto_as_dict(getattr(value, item.name))
            for item in dataclass_fields(value)
        }
    if isinstance(value, Mapping):
        return {key: dto_as_dict(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [dto_as_dict(item) for item in value]
    return to_plain(value)


__all__ = [
    "LifecycleTransitionError",
    "LIFECYCLE_TRANSITIONS",
    "ACTIVATION_TRANSITIONS",
    "MAX_SUPPORTED_STORES",
    "ReadinessCheckDTO",
    "ReadinessDTO",
    "SUPPORTED_STORE_CAPACITY",
    "SHOPIFY_DOMAIN_RE",
    "SettingsFieldDTO",
    "SettingsGroupDTO",
    "StoreAdminContractError",
    "StoreAdminSummaryDTO",
    "StoreCapacityExceeded",
    "StoreListDTO",
    "StoreListItemDTO",
    "StoreListResponseDTO",
    "StoreSettingsDTO",
    "StoreSetupDTO",
    "canonical_json",
    "canonical_shop_domain",
    "configuration_fingerprint",
    "dto_as_dict",
    "ensure_store_capacity",
    "is_canonical_shop_domain",
    "lifecycle_transition",
    "activation_transition",
    "require_setup_step_key",
    "store_configuration_fingerprint",
]
