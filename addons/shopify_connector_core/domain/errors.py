"""Public, normalized problem contracts for V2 RPC boundaries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Any

from .immutability import freeze_value, to_plain
from .states import _ValueEnum


class ErrorCode(_ValueEnum):
    VALIDATION_ERROR = "validation_error"
    ACCESS_DENIED = "access_denied"
    STORE_SCOPE_MISMATCH = "store_scope_mismatch"
    STALE_GENERATION = "stale_generation"
    STATE_CONFLICT = "state_conflict"
    READINESS_BLOCKED = "readiness_blocked"
    OPERATION_CONFLICT = "operation_conflict"
    DUPLICATE_COMMAND = "duplicate_command"
    PREVIEW_STALE = "preview_stale"
    SHOPIFY_THROTTLED = "shopify_throttled"
    SHOPIFY_UNAVAILABLE = "shopify_unavailable"
    SHOPIFY_AUTH_REQUIRED = "shopify_auth_required"
    SHOPIFY_VALIDATION = "shopify_validation"
    VERIFICATION_REQUIRED = "verification_required"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    TERMINAL_FAILURE = "terminal_failure"
    CONTRACT_VERSION_UNSUPPORTED = "contract_version_unsupported"


PUBLIC_ERROR_CODES = tuple(item.value for item in ErrorCode)

# Compatibility names used by the first inert client contract.  They are
# accepted at the boundary and immediately represented by the documentation's
# canonical code; no second public vocabulary is emitted.
ERROR_CODE_ALIASES = {
    "throttled": ErrorCode.SHOPIFY_THROTTLED.value,
    "service_unavailable": ErrorCode.SHOPIFY_UNAVAILABLE.value,
    "authentication_failed": ErrorCode.SHOPIFY_AUTH_REQUIRED.value,
    "manual_review": ErrorCode.MANUAL_REVIEW_REQUIRED.value,
    "unsupported": ErrorCode.CONTRACT_VERSION_UNSUPPORTED.value,
}


def canonical_error_code(value: str | ErrorCode) -> str:
    """Return a documented error code while accepting legacy aliases."""
    code = value.value if isinstance(value, ErrorCode) else value
    if not isinstance(code, str):
        raise ValueError(f"unknown public error code: {code!r}")
    code = ERROR_CODE_ALIASES.get(code, code)
    if code not in PUBLIC_ERROR_CODES:
        raise ValueError(f"unknown public error code: {code!r}")
    return code


def _mapping(value: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{field_name} must be a mapping")
    if any(not isinstance(key, str) or not key for key in value):
        raise TypeError(f"{field_name} keys must be non-empty strings")
    return freeze_value(dict(value))


@dataclass(frozen=True, slots=True)
class ProblemError:
    """The only error shape exposed by a public V2 RPC contract."""

    code: str | ErrorCode
    title: str
    detail: str
    retryable: bool
    field_errors: Mapping[str, Any] = field(default_factory=dict)
    attention_ref: str | None = None
    run_ref: str | None = None
    correlation_id: str = ""

    def __post_init__(self) -> None:
        code = canonical_error_code(self.code)
        if not isinstance(self.title, str) or not self.title.strip():
            raise ValueError("title must be non-empty")
        if not isinstance(self.detail, str) or not self.detail.strip():
            raise ValueError("detail must be non-empty")
        if not isinstance(self.retryable, bool):
            raise TypeError("retryable must be bool")
        if not isinstance(self.correlation_id, str) or not self.correlation_id.strip():
            raise ValueError("correlation_id must be non-empty")
        for name, value in (
            ("attention_ref", self.attention_ref),
            ("run_ref", self.run_ref),
        ):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} must be a non-empty string or None")
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "field_errors", _mapping(self.field_errors, "field_errors"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "title": self.title,
            "detail": self.detail,
            "retryable": self.retryable,
            "field_errors": to_plain(self.field_errors),
            "attention_ref": self.attention_ref,
            "run_ref": self.run_ref,
            "correlation_id": self.correlation_id,
        }


# Descriptive aliases keep the public shape discoverable without duplicating
# the contract or allowing a second error vocabulary.
NormalizedError = ProblemError
ErrorDTO = ProblemError


__all__ = [
    "ErrorCode",
    "ERROR_CODE_ALIASES",
    "ErrorDTO",
    "NormalizedError",
    "ProblemError",
    "PUBLIC_ERROR_CODES",
    "canonical_error_code",
]
