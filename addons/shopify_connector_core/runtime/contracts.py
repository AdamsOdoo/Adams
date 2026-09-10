"""Immutable outcomes returned by explicit runtime handler contracts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Union

from ..domain.immutability import freeze_value
from .p10_decisions import KNOWN_ERROR_CLASSES

def _observations(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("observations must be a mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise TypeError("observation keys must be non-empty strings")
    return freeze_value(dict(value))


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value


@dataclass(frozen=True, slots=True)
class Succeeded:
    observations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "observations", _observations(self.observations))


@dataclass(frozen=True, slots=True)
class Skipped:
    reason: str
    observations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("skip reason must be non-empty")
        object.__setattr__(self, "observations", _observations(self.observations))


@dataclass(frozen=True, slots=True)
class Retryable:
    error_class: str
    retry_at: datetime
    observations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.error_class, str) or not self.error_class.strip():
            raise ValueError("error_class must be non-empty")
        _utc(self.retry_at, "retry_at")
        object.__setattr__(self, "observations", _observations(self.observations))


@dataclass(frozen=True, slots=True)
class NeedsVerification:
    mutation_attempt_id: int | str
    plan: str | Mapping[str, Any]
    observations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.mutation_attempt_id, bool) or not isinstance(
            self.mutation_attempt_id, (int, str)
        ):
            raise TypeError("mutation_attempt_id must be an integer or string")
        if isinstance(self.mutation_attempt_id, int) and self.mutation_attempt_id <= 0:
            raise ValueError("mutation_attempt_id must be positive")
        if isinstance(self.mutation_attempt_id, str) and not self.mutation_attempt_id.strip():
            raise ValueError("mutation_attempt_id must be non-empty")
        if isinstance(self.plan, str):
            if not self.plan.strip():
                raise ValueError("verification plan must be non-empty")
        elif isinstance(self.plan, Mapping):
            object.__setattr__(self, "plan", freeze_value(dict(self.plan)))
        else:
            raise TypeError("verification plan must be a string or mapping")
        object.__setattr__(self, "observations", _observations(self.observations))


@dataclass(frozen=True, slots=True)
class NeedsReview:
    reason_code: str
    required_action: str
    observations: Mapping[str, Any] = field(default_factory=dict)
    error_class: str | None = None

    def __post_init__(self) -> None:
        for name in ("reason_code", "required_action"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name).strip():
                raise ValueError(f"{name} must be non-empty")
        if self.error_class is not None:
            if not isinstance(self.error_class, str):
                raise TypeError("error_class must be a string or None")
            if not self.error_class.strip():
                raise ValueError("error_class must be non-empty when supplied")
            if self.error_class not in KNOWN_ERROR_CLASSES:
                raise ValueError("error_class must be an allowlisted source class")
        object.__setattr__(self, "observations", _observations(self.observations))


@dataclass(frozen=True, slots=True)
class TerminalFailure:
    error_class: str
    no_safe_action: bool
    observations: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.error_class, str) or not self.error_class.strip():
            raise ValueError("error_class must be non-empty")
        if not isinstance(self.no_safe_action, bool):
            raise TypeError("no_safe_action must be bool")
        object.__setattr__(self, "observations", _observations(self.observations))


HandlerResult = Union[
    Succeeded,
    Skipped,
    Retryable,
    NeedsVerification,
    NeedsReview,
    TerminalFailure,
]


__all__ = [
    "HandlerResult",
    "NeedsReview",
    "NeedsVerification",
    "Retryable",
    "Skipped",
    "Succeeded",
    "TerminalFailure",
]
