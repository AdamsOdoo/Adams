"""Versioned command envelopes and results for the V2 application boundary."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

from ..domain.identifiers import require_key, require_run_ref
from ..domain.immutability import freeze_value, to_plain
from ..domain.states import CommandStatus, TriggerType


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value


def _payload(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("payload must be a mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise TypeError("payload keys must be non-empty strings")
    return freeze_value(dict(value))


@dataclass(frozen=True, slots=True)
class CommandEnvelope:
    """Caller-supplied immutable command identity and scoped payload."""

    contract_version: int
    command_id: UUID
    command_name: str
    store_id: int
    company_id: int
    expected_generation: int
    actor_uid: int | None
    trigger: str | TriggerType
    requested_at: datetime
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.contract_version, bool) or self.contract_version != 1:
            raise ValueError("only contract_version 1 is supported")
        if not isinstance(self.command_id, UUID):
            raise TypeError("command_id must be UUID")
        require_key(self.command_name, "command_name")
        for name in ("store_id", "company_id"):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if not isinstance(self.expected_generation, int) or isinstance(self.expected_generation, bool):
            raise TypeError("expected_generation must be an integer")
        if self.expected_generation < 0:
            raise ValueError("expected_generation cannot be negative")
        trigger = self.trigger.value if isinstance(self.trigger, TriggerType) else self.trigger
        if trigger not in {item.value for item in TriggerType}:
            raise ValueError(f"unsupported trigger: {trigger!r}")
        if self.actor_uid is None and trigger != TriggerType.SYSTEM.value:
            raise ValueError("actor_uid may be None only for a system trigger")
        if self.actor_uid is not None and (
            not isinstance(self.actor_uid, int)
            or isinstance(self.actor_uid, bool)
            or self.actor_uid <= 0
        ):
            raise ValueError("actor_uid must be a positive integer or None")
        _utc(self.requested_at, "requested_at")
        object.__setattr__(self, "trigger", trigger)
        object.__setattr__(self, "payload", _payload(self.payload))

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "command_id": str(self.command_id),
            "command_name": self.command_name,
            "store_id": self.store_id,
            "company_id": self.company_id,
            "expected_generation": self.expected_generation,
            "actor_uid": self.actor_uid,
            "trigger": self.trigger,
            "requested_at": self.requested_at.isoformat(),
            "payload": to_plain(self.payload),
        }


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Safe command acknowledgement; never a raw remote response."""

    status: str | CommandStatus
    run_ref: str | None
    attention_ref: str | None
    message: str
    conflict_version: int | None

    def __post_init__(self) -> None:
        status = self.status.value if isinstance(self.status, CommandStatus) else self.status
        if status not in {item.value for item in CommandStatus}:
            raise ValueError(f"unsupported command status: {status!r}")
        for name in ("run_ref", "attention_ref"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be non-empty or None")
        if self.run_ref is not None:
            require_run_ref(self.run_ref)
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be non-empty")
        if self.conflict_version is not None and (
            not isinstance(self.conflict_version, int)
            or isinstance(self.conflict_version, bool)
            or self.conflict_version < 0
        ):
            raise ValueError("conflict_version must be non-negative or None")
        object.__setattr__(self, "status", status)

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "status": self.status,
            "message": self.message,
            "run_ref": self.run_ref,
            "attention_ref": self.attention_ref,
            "conflict_version": self.conflict_version,
        })


__all__ = ["CommandEnvelope", "CommandResult"]
