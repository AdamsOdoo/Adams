"""Pure read-only admission contract for the P10 canary runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..domain.immutability import to_plain
from ..domain.identifiers import require_key


READ_ONLY_RUNTIME_MODE = "read_only"


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


class ReadHandlerLookup(Protocol):
    def require(self, handler_key: str) -> object:
        """Resolve an explicit handler or raise a lookup error."""


@dataclass(frozen=True, slots=True)
class ReadOnlyAdmissionRequest:
    """The small pre-admission shape used before creating a V2 run/job."""

    runtime_mode: str
    handler_key: str
    store_id: int
    company_id: int
    expected_generation: int
    cancel_requested: bool = False
    # Configuration changes are an independent fence from the connection
    # epoch.  The Odoo adapter supplies both snapshots; the default keeps the
    # original pure admission fixtures source-compatible.
    expected_configuration_generation: int = 0

    def __post_init__(self) -> None:
        if self.runtime_mode != READ_ONLY_RUNTIME_MODE:
            raise ValueError("runtime_mode is not the read-only canary mode")
        require_key(self.handler_key, "handler_key")
        _positive_int(self.store_id, "store_id")
        _positive_int(self.company_id, "company_id")
        _non_negative_int(self.expected_generation, "expected_generation")
        _non_negative_int(
            self.expected_configuration_generation,
            "expected_configuration_generation",
        )
        if not isinstance(self.cancel_requested, bool):
            raise TypeError("cancel_requested must be bool")


@dataclass(frozen=True, slots=True)
class ReadOnlyAdmissionDecision:
    """Safe result of explicit read-only handler admission."""

    action: str
    reason_code: str

    def __post_init__(self) -> None:
        if self.action not in {"admit", "reject"}:
            raise ValueError("unsupported admission action")
        if not isinstance(self.reason_code, str) or not self.reason_code.strip():
            raise ValueError("reason_code must be non-empty")

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "action": self.action,
            "reason_code": self.reason_code,
        })


def admit_read_only(
    request: ReadOnlyAdmissionRequest,
    handlers: ReadHandlerLookup,
) -> ReadOnlyAdmissionDecision:
    """Fail closed unless mode and handler are explicitly read-only."""

    if not isinstance(request, ReadOnlyAdmissionRequest):
        raise TypeError("request must be a ReadOnlyAdmissionRequest")
    if not hasattr(handlers, "require"):
        raise TypeError("handlers must resolve named handlers")
    if request.cancel_requested:
        return ReadOnlyAdmissionDecision("reject", "cancellation_requested")
    try:
        handlers.require(request.handler_key)
    except LookupError:
        return ReadOnlyAdmissionDecision("reject", "unknown_read_handler")
    return ReadOnlyAdmissionDecision("admit", "read_only_handler_admitted")


__all__ = [
    "READ_ONLY_RUNTIME_MODE",
    "ReadHandlerLookup",
    "ReadOnlyAdmissionDecision",
    "ReadOnlyAdmissionRequest",
    "admit_read_only",
]
