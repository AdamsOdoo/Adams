"""Immutable typed values used by the Shopify GraphQL boundary."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from ...domain.immutability import freeze_value, to_plain
from .cost import CostMetadata, ThrottleStatus
from .transport import SHOPIFY_API_VERSION, redact


MAX_COST_EXCEEDED = "MAX_COST_EXCEEDED"


def _header(headers: Any, name: str) -> Any:
    """Read a response header with HTTP's case-insensitive spelling rules."""

    if not isinstance(headers, Mapping):
        return None
    value = headers.get(name)
    if value is not None:
        return value
    wanted = name.lower()
    for key, candidate in headers.items():
        if str(key).lower() == wanted:
            return candidate
    return None


def _safe_request_id(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value)
    return redact(value[:256]) if value else None


def _freeze_json(value: Any, field_name: str = "value") -> Any:
    """Validate JSON-shaped values and freeze every nested container."""

    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("%s contains a non-finite number" % field_name)
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("%s mapping keys must be strings" % field_name)
        return freeze_value({
            key: _freeze_json(item, "%s.%s" % (field_name, key))
            for key, item in value.items()
        })
    if isinstance(value, (list, tuple)):
        return tuple(
            _freeze_json(item, "%s[%s]" % (field_name, index))
            for index, item in enumerate(value)
        )
    raise TypeError("%s contains a non-JSON value" % field_name)


@dataclass(frozen=True, slots=True)
class GraphQLError:
    """Safe typed representation of one top-level GraphQL error."""

    message: str = field(repr=False)
    code: str | None = None
    path: tuple[Any, ...] = ()
    request_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", redact(str(self.message))[:2048])
        object.__setattr__(
            self,
            "code",
            redact(str(self.code))[:128] if self.code is not None else None,
        )
        path = tuple(self.path or ())
        for item in path:
            if isinstance(item, bool) or not isinstance(item, (str, int)):
                raise TypeError(
                    "error.path must contain only JSON string/integer values"
                )
        object.__setattr__(self, "path", path)
        object.__setattr__(self, "request_id", _safe_request_id(self.request_id))

    def as_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "code": self.code,
            "path": list(self.path),
            "request_id": self.request_id,
        }


@dataclass(frozen=True, slots=True)
class GraphQLUserError:
    """Mutation ``userErrors`` item normalized without changing legacy success."""

    message: str = field(repr=False)
    field: tuple[str, ...] = ()
    code: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "message", redact(str(self.message))[:2048])
        field = tuple(self.field or ())
        if any(not isinstance(value, str) for value in field):
            raise TypeError("user error fields must be strings")
        object.__setattr__(self, "field", tuple(redact(value) for value in field))
        object.__setattr__(
            self,
            "code",
            redact(str(self.code)) if self.code is not None else None,
        )

    @property
    def fields(self) -> tuple[str, ...]:
        return self.field

    def as_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "field": list(self.field),
            "code": self.code,
        }


@dataclass(frozen=True, slots=True)
class GraphQLResult:
    """Normalized result returned by the typed executor."""

    data: Any = field(default=None, repr=False)
    errors: tuple[GraphQLError, ...] = ()
    user_errors: tuple[GraphQLUserError, ...] = ()
    cost: CostMetadata | None = None
    request_id: str | None = None
    served_version: str = SHOPIFY_API_VERSION
    status_code: int = 200

    def __post_init__(self) -> None:
        if any(not isinstance(error, GraphQLError) for error in self.errors):
            raise TypeError("errors must contain GraphQLError values")
        if any(not isinstance(error, GraphQLUserError) for error in self.user_errors):
            raise TypeError("user_errors must contain GraphQLUserError values")
        if self.cost is not None and not isinstance(self.cost, CostMetadata):
            raise TypeError("cost must be CostMetadata or None")
        if self.served_version != SHOPIFY_API_VERSION:
            raise ValueError("served_version must equal the pinned connector version")
        if not isinstance(self.data, Mapping):
            raise TypeError("data must be a JSON object")
        data = _freeze_json(self.data, "data")
        object.__setattr__(self, "data", data)
        object.__setattr__(self, "errors", tuple(self.errors))
        object.__setattr__(self, "user_errors", tuple(self.user_errors))
        object.__setattr__(self, "request_id", _safe_request_id(self.request_id))

    @property
    def throttle_status(self) -> ThrottleStatus | None:
        return self.cost.throttle_status if self.cost else None

    @property
    def requested_query_cost(self) -> int | float | None:
        return self.cost.requested_query_cost if self.cost else None

    @property
    def actual_query_cost(self) -> int | float | None:
        return self.cost.actual_query_cost if self.cost else None

    @property
    def requested_cost(self) -> int | float | None:
        return self.requested_query_cost

    @property
    def actual_cost(self) -> int | float | None:
        return self.actual_query_cost

    def as_dict(self) -> dict[str, Any]:
        return {
            "data": to_plain(self.data),
            "errors": [error.as_dict() for error in self.errors],
            "user_errors": [error.as_dict() for error in self.user_errors],
            "cost": self.cost.as_dict() if self.cost else None,
            "throttle_status": (
                self.throttle_status.as_dict() if self.throttle_status else None
            ),
            "request_id": self.request_id,
            "served_version": self.served_version,
            "status_code": self.status_code,
        }

    def to_legacy_dict(self) -> dict[str, Any]:
        result = {
            "data": to_plain(self.data),
            "throttle_status": (
                self.throttle_status.as_dict() if self.throttle_status else None
            ),
            "served_version": self.served_version,
        }
        if self.cost is not None:
            result["cost"] = self.cost.as_dict()
        if self.request_id is not None:
            result["request_id"] = self.request_id
        return result


class ShopifyGraphQLExecutionError(Exception):
    """Normalized typed error with legacy class and Shopify code side by side."""

    def __init__(
        self,
        error_class: str,
        reason: str,
        technical_detail: str = "",
        *,
        error_code: str | None = None,
        request_id: str | None = None,
        cost: CostMetadata | None = None,
        credential_invalid: bool = False,
        status_code: int | None = None,
        extra_secrets: tuple[str, ...] = (),
    ) -> None:
        self.error_class = error_class
        self.classification = error_class
        safe_code = (
            redact(str(error_code), extra_secrets=extra_secrets)[:128]
            if error_code is not None
            else None
        )
        self.error_code = safe_code
        self.code = safe_code
        self.shopify_error_code = safe_code
        self.classification_code = safe_code
        self.reason = redact(reason, extra_secrets=extra_secrets)
        self.technical_detail = (
            redact(technical_detail, extra_secrets=extra_secrets)
            if technical_detail
            else technical_detail
        )
        self.request_id = _safe_request_id(request_id)
        if self.request_id:
            self.request_id = redact(self.request_id, extra_secrets=extra_secrets)
        self.cost = cost
        self.credential_invalid = credential_invalid
        self.status_code = status_code
        super().__init__(self.reason)

    @property
    def is_cost_exceeded(self) -> bool:
        return self.error_code == MAX_COST_EXCEEDED

    @property
    def is_max_cost_exceeded(self) -> bool:
        return self.is_cost_exceeded

    def __str__(self) -> str:
        return self.reason


__all__ = [
    "GraphQLError",
    "GraphQLResult",
    "GraphQLUserError",
    "MAX_COST_EXCEEDED",
    "ShopifyGraphQLExecutionError",
]
