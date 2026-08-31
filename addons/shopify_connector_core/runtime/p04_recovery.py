"""Pure contracts for the bounded P04 recovery command boundary.

The application adapter is intentionally small, but it still needs one place
where the client-controlled part of a recovery command is made strict.  This
module owns that value-level contract only.  It does not know Odoo records,
does not choose a business transition and never performs a remote request.

The Odoo facade performs the second (authoritative) validation against the
fresh attention DTO and the owning service immediately before delegating an
action.  Keeping these checks separate is useful: this module can be tested
without a database, while the facade remains the only place that can enforce
company/store/role/generation scope.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from ..domain.immutability import freeze_value, to_plain
from ..domain.identifiers import require_key, require_run_ref


class RecoveryContractError(ValueError):
    """A client recovery payload is not part of the closed contract."""


# Provider names are code-owned.  A caller may select an action only after
# the current provider has advertised that exact action.  Providers without a
# core recovery service stay in this map with an empty action tuple: that is a
# deliberate fail-closed result, not an invitation to reflect over a model.
PROVIDER_ACTIONS = MappingProxyType({
    # ``open_*`` actions are included because they are part of the read DTO
    # vocabulary.  The command adapter treats them as navigation-only and
    # never turns them into a write.
    "manual_review_job": ("open_run", "retry_job", "resolve_manual_review"),
    "mutation_uncertainty": ("open_run", "resolve_mutation"),
    "product_match": ("open_match_decision",),
    "inventory_mapping": ("map_location_and_preview",),
    "fulfillment_review": ("open_fulfillment_review",),
    "readiness_failure": ("repair_setup",),
})

ACTION_INPUT_KEYS = MappingProxyType({
    "open_run": frozenset(),
    "retry_job": frozenset(),
    "resolve_manual_review": frozenset(),
    "resolve_mutation": frozenset(("disposition",)),
    "cancel_job": frozenset(),
    "open_match_decision": frozenset(),
    "map_location_and_preview": frozenset(),
    "open_fulfillment_review": frozenset(),
    "repair_setup": frozenset(),
})

ACTION_REQUIRED_REASON = frozenset((
    "resolve_manual_review",
    "resolve_mutation",
    "cancel_job",
))

ACTION_REQUIRED_ROLE = MappingProxyType({
    "retry_job": "operator",
    "resolve_manual_review": "administrator",
    "resolve_mutation": "administrator",
    "cancel_job": "administrator",
})

_ATTENTION_REF_RE = re.compile(
    r"^attn:(?P<provider>[a-z][a-z0-9_.:-]*):"
    r"(?P<source>[1-9][0-9]*):(?P<version>[1-9][0-9]*)$"
)

_JOB_REF_RE = re.compile(r"^(?P<prefix>job|run):(?P<id>[1-9][0-9]*)$")

_MAX_REASON_CHARS = 512


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise RecoveryContractError(f"{name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RecoveryContractError(f"{name} must be a non-negative integer")
    return value


def parse_attention_ref(value: str) -> tuple[str, int, int]:
    """Parse one opaque attention reference without touching a model name."""

    if not isinstance(value, str):
        raise RecoveryContractError("item_ref must be a string")
    match = _ATTENTION_REF_RE.fullmatch(value)
    if not match:
        raise RecoveryContractError("item_ref is invalid")
    provider = match.group("provider")
    if provider not in PROVIDER_ACTIONS:
        raise RecoveryContractError("item_ref provider is not supported")
    return provider, int(match.group("source")), int(match.group("version"))


def parse_run_ref(value: str | int) -> tuple[str, int]:
    """Accept the staged ``job:<id>`` and ``run:<id>`` identities only."""

    if isinstance(value, int) and not isinstance(value, bool):
        if value <= 0:
            raise RecoveryContractError("job id must be positive")
        return "job", value
    if not isinstance(value, str):
        raise RecoveryContractError("job reference must be a string")
    try:
        require_run_ref(value)
    except (TypeError, ValueError) as exc:
        raise RecoveryContractError("job reference is invalid") from exc
    match = _JOB_REF_RE.fullmatch(value)
    if not match:  # Defensive: require_run_ref is the public validator.
        raise RecoveryContractError("job reference is invalid")
    return match.group("prefix"), int(match.group("id"))


def _reason(value: Any, *, required: bool) -> str | None:
    if value is None or value is False or value == "":
        if required:
            raise RecoveryContractError("a non-empty reason is required")
        return None
    if not isinstance(value, str):
        raise RecoveryContractError("reason must be a string")
    value = value.strip()
    if not value:
        if required:
            raise RecoveryContractError("a non-empty reason is required")
        return None
    if len(value) > _MAX_REASON_CHARS:
        raise RecoveryContractError("reason is too long")
    return value


def _strict_inputs(action_key: str, value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RecoveryContractError("inputs must be a mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise RecoveryContractError("input keys must be non-empty strings")
    expected = ACTION_INPUT_KEYS.get(action_key)
    if expected is None:
        raise RecoveryContractError("action is not supported")
    if set(value) != set(expected):
        raise RecoveryContractError("inputs do not match the action contract")
    if action_key == "resolve_mutation":
        disposition = value.get("disposition")
        if disposition not in ("applied", "not_applied"):
            raise RecoveryContractError("mutation disposition is invalid")
    try:
        return freeze_value(dict(value))
    except (TypeError, ValueError) as exc:
        raise RecoveryContractError("inputs must be JSON-safe") from exc


def require_provider_action(provider: str, action_key: str) -> None:
    """Require a statically registered provider/action pair."""

    if provider not in PROVIDER_ACTIONS:
        raise RecoveryContractError("provider is not supported")
    if not isinstance(action_key, str):
        raise RecoveryContractError("action_key must be a string")
    try:
        require_key(action_key, "action_key")
    except (TypeError, ValueError) as exc:
        raise RecoveryContractError("action_key is invalid") from exc
    if action_key not in PROVIDER_ACTIONS[provider]:
        raise RecoveryContractError("action is not allowed for this provider")


@dataclass(frozen=True, slots=True)
class AttentionCommand:
    """Immutable, JSON-shaped command payload for ``resolve_attention_v1``."""

    item_ref: str
    state_version: int
    action_key: str
    inputs: Mapping[str, Any] = field(default_factory=dict)
    reason: str | None = None

    def __post_init__(self) -> None:
        provider, _source_id, ref_version = parse_attention_ref(self.item_ref)
        if self.state_version != ref_version:
            raise RecoveryContractError(
                "state_version must match the attention reference"
            )
        _positive_int(self.state_version, "state_version")
        require_provider_action(provider, self.action_key)
        object.__setattr__(
            self,
            "inputs",
            _strict_inputs(self.action_key, self.inputs),
        )
        object.__setattr__(
            self,
            "reason",
            _reason(
                self.reason,
                required=self.action_key in ACTION_REQUIRED_REASON,
            ),
        )

    @property
    def provider(self) -> str:
        return parse_attention_ref(self.item_ref)[0]

    @property
    def source_id(self) -> int:
        return parse_attention_ref(self.item_ref)[1]

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "item_ref": self.item_ref,
            "state_version": self.state_version,
            "action_key": self.action_key,
            "inputs": self.inputs,
            "reason": self.reason,
        })

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "AttentionCommand":
        if not isinstance(value, Mapping):
            raise RecoveryContractError("recovery payload must be a mapping")
        allowed = {"item_ref", "state_version", "action_key", "inputs", "reason"}
        unknown = set(value) - allowed
        if unknown:
            raise RecoveryContractError("recovery payload contains unsupported fields")
        required = {"item_ref", "state_version", "action_key"}
        missing = required - set(value)
        if missing:
            raise RecoveryContractError("recovery payload is missing required fields")
        return cls(
            item_ref=value["item_ref"],
            state_version=value["state_version"],
            action_key=value["action_key"],
            inputs=value.get("inputs", {}),
            reason=value.get("reason"),
        )


@dataclass(frozen=True, slots=True)
class GenerationSnapshot:
    """The two epochs that a V2 action must carry and revalidate."""

    connection_generation: int
    configuration_generation: int

    def __post_init__(self) -> None:
        _nonnegative_int(self.connection_generation, "connection_generation")
        _nonnegative_int(
            self.configuration_generation,
            "configuration_generation",
        )

    def matches(self, *, connection_generation: int, configuration_generation: int) -> bool:
        return (
            self.connection_generation == connection_generation
            and self.configuration_generation == configuration_generation
        )


def mutation_action_is_safe(observed_outcome: Any, action_key: str) -> bool:
    """Return whether an action can proceed without replaying a mutation.

    P04 only exposes the explicit mutation-resolution action.  All generic
    retry/cancel paths are fenced whenever immutable mutation evidence exists;
    an uncertain outcome is never treated as an ordinary failed job.
    """

    if action_key == "resolve_mutation":
        return observed_outcome == "uncertain"
    return observed_outcome in (None, False, "")


def cancellation_requires_quiescence(state: str, has_mutation_evidence: bool) -> bool:
    """Whether cancellation must wait for a worker/readback boundary."""

    if has_mutation_evidence:
        return True
    return state in ("running", "retry_waiting")


__all__ = [
    "ACTION_INPUT_KEYS",
    "ACTION_REQUIRED_REASON",
    "ACTION_REQUIRED_ROLE",
    "AttentionCommand",
    "GenerationSnapshot",
    "PROVIDER_ACTIONS",
    "RecoveryContractError",
    "cancellation_requires_quiescence",
    "mutation_action_is_safe",
    "parse_attention_ref",
    "parse_run_ref",
    "require_provider_action",
]
