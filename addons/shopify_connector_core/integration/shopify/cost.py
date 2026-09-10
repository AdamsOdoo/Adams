"""Typed Shopify GraphQL cost and throttle observations.

This module owns only the response telemetry value objects.  It has no
transport or Odoo dependency, so callers can use the observations in pure
contract tests and later backpressure/reconciliation code without importing
the executor implementation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


def _number(value: Any) -> int | float | None:
    """Return finite numeric Shopify telemetry, preserving integer values."""

    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Shopify cost telemetry must be finite")
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(parsed):
            raise ValueError("Shopify cost telemetry must be finite")
        return int(parsed) if parsed.is_integer() else parsed
    return None


def _validate_finite_number(value: Any, field_name: str) -> None:
    """Reject impossible direct constructor values.

    Shopify JSON payload parsing already routes through :func:`_number`, but
    these dataclasses are also public typed values and can be constructed
    directly by callers.  Keep that path subject to the same finite-number
    contract without coercing valid integer/float observations.
    """

    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("%s must be a finite number or None" % field_name)
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("%s must be a finite number" % field_name)


@dataclass(frozen=True, slots=True)
class ThrottleStatus:
    """Typed Shopify leaky-bucket observation."""

    maximum_available: int | float | None = None
    currently_available: int | float | None = None
    restore_rate: int | float | None = None

    def __post_init__(self) -> None:
        _validate_finite_number(
            self.maximum_available, "maximum_available"
        )
        _validate_finite_number(
            self.currently_available, "currently_available"
        )
        _validate_finite_number(self.restore_rate, "restore_rate")

    @classmethod
    def from_payload(cls, payload: Any) -> "ThrottleStatus | None":
        if not isinstance(payload, Mapping):
            return None
        result = cls(
            _number(payload.get("maximumAvailable")),
            _number(payload.get("currentlyAvailable")),
            _number(payload.get("restoreRate")),
        )
        if all(value is None for value in (
            result.maximum_available,
            result.currently_available,
            result.restore_rate,
        )):
            return None
        return result

    @property
    def maximumAvailable(self) -> int | float | None:
        return self.maximum_available

    @property
    def currentlyAvailable(self) -> int | float | None:
        return self.currently_available

    @property
    def restoreRate(self) -> int | float | None:
        return self.restore_rate

    def as_dict(self) -> dict[str, int | float | None]:
        return {
            "maximumAvailable": self.maximum_available,
            "currentlyAvailable": self.currently_available,
            "restoreRate": self.restore_rate,
        }


@dataclass(frozen=True, slots=True)
class CostMetadata:
    """Requested/actual GraphQL cost plus the returned throttle bucket."""

    requested_query_cost: int | float | None = None
    actual_query_cost: int | float | None = None
    throttle_status: ThrottleStatus | None = None

    def __post_init__(self) -> None:
        _validate_finite_number(
            self.requested_query_cost, "requested_query_cost"
        )
        _validate_finite_number(self.actual_query_cost, "actual_query_cost")
        if (
            self.throttle_status is not None
            and not isinstance(self.throttle_status, ThrottleStatus)
        ):
            raise TypeError("throttle_status must be ThrottleStatus or None")

    @classmethod
    def from_payload(cls, payload: Any) -> "CostMetadata | None":
        if not isinstance(payload, Mapping):
            return None
        throttle = ThrottleStatus.from_payload(payload.get("throttleStatus"))
        result = cls(
            _number(payload.get("requestedQueryCost")),
            _number(payload.get("actualQueryCost")),
            throttle,
        )
        if (
            result.requested_query_cost is None
            and result.actual_query_cost is None
            and result.throttle_status is None
        ):
            return None
        return result

    @classmethod
    def from_result_payload(cls, payload: Any) -> "CostMetadata | None":
        """Parse either a cost object or a legacy result's throttle object."""

        if not isinstance(payload, Mapping):
            return None
        if (
            "throttleStatus" in payload
            or "requestedQueryCost" in payload
            or "actualQueryCost" in payload
        ):
            return cls.from_payload(payload)
        throttle = ThrottleStatus.from_payload(payload)
        return cls(None, None, throttle) if throttle else None

    @property
    def requested_cost(self) -> int | float | None:
        return self.requested_query_cost

    @property
    def actual_cost(self) -> int | float | None:
        return self.actual_query_cost

    @property
    def requestedQueryCost(self) -> int | float | None:
        return self.requested_query_cost

    @property
    def actualQueryCost(self) -> int | float | None:
        return self.actual_query_cost

    @property
    def maximum_available(self) -> int | float | None:
        return self.throttle_status.maximum_available if self.throttle_status else None

    @property
    def currently_available(self) -> int | float | None:
        return self.throttle_status.currently_available if self.throttle_status else None

    @property
    def restore_rate(self) -> int | float | None:
        return self.throttle_status.restore_rate if self.throttle_status else None

    def as_dict(self) -> dict[str, Any]:
        return {
            "requestedQueryCost": self.requested_query_cost,
            "actualQueryCost": self.actual_query_cost,
            "throttleStatus": (
                self.throttle_status.as_dict() if self.throttle_status else None
            ),
        }


__all__ = ["CostMetadata", "ThrottleStatus"]
