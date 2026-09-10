"""Pure bounded retry policy constants and calculations."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """The accepted eligible technical retry schedule.

    The policy computes the deterministic exponential component.  Applying a
    random jitter sample is an execution concern and therefore intentionally
    not performed by this inert contract package.
    """

    base_delay_seconds: int = 30
    multiplier: int = 2
    max_delay_seconds: int = 30 * 60
    jitter_ratio: float = 0.20
    max_scheduled_retries: int = 12
    window_seconds: int = 24 * 60 * 60

    def __post_init__(self) -> None:
        for name in (
            "base_delay_seconds",
            "multiplier",
            "max_delay_seconds",
            "max_scheduled_retries",
            "window_seconds",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be an integer")
        if isinstance(self.jitter_ratio, bool) or not isinstance(
            self.jitter_ratio, (int, float)
        ):
            raise TypeError("jitter_ratio must be a number")
        if self.base_delay_seconds <= 0:
            raise ValueError("base_delay_seconds must be positive")
        if self.multiplier < 1:
            raise ValueError("multiplier must be at least one")
        if self.max_delay_seconds < self.base_delay_seconds:
            raise ValueError("max_delay_seconds cannot be below the base delay")
        if not isfinite(self.jitter_ratio) or not 0 <= self.jitter_ratio <= 1:
            raise ValueError("jitter_ratio must be between zero and one")
        if self.max_scheduled_retries <= 0:
            raise ValueError("max_scheduled_retries must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

    @property
    def max_attempts(self) -> int:
        """Compatibility spelling for consumers that count scheduled attempts."""

        return self.max_scheduled_retries

    def delay_seconds(self, retry_number: int) -> int:
        """Return the capped exponential component for a 1-based retry number."""

        if isinstance(retry_number, bool) or not isinstance(retry_number, int):
            raise TypeError("retry_number must be an integer")
        if retry_number < 1:
            raise ValueError("retry_number is 1-based")
        if retry_number > self.max_scheduled_retries:
            raise ValueError(
                "retry_number exceeds max_scheduled_retries; no retry is scheduled"
            )

        # Do not evaluate ``multiplier ** retry_number`` directly.  A malformed
        # caller-provided number must not allocate an unbounded integer merely
        # to discover that the result is capped.
        delay = self.base_delay_seconds
        for _ in range(retry_number - 1):
            if delay >= self.max_delay_seconds:
                return self.max_delay_seconds
            delay = min(self.max_delay_seconds, delay * self.multiplier)
        return delay

    def jitter_bounds(self, retry_number: int) -> tuple[float, float]:
        """Return the inclusive lower/upper jitter bounds for a retry."""

        delay = self.delay_seconds(retry_number)
        delta = delay * self.jitter_ratio
        return (delay - delta, delay + delta)


DEFAULT_RETRY_POLICY = RetryPolicy()

# Named constants make the locked values easy for static checks to inspect
# without requiring callers to instantiate the policy.
RETRY_BASE_SECONDS = DEFAULT_RETRY_POLICY.base_delay_seconds
RETRY_MULTIPLIER = DEFAULT_RETRY_POLICY.multiplier
RETRY_MAX_SECONDS = DEFAULT_RETRY_POLICY.max_delay_seconds
RETRY_JITTER_RATIO = DEFAULT_RETRY_POLICY.jitter_ratio
MAX_SCHEDULED_RETRIES = DEFAULT_RETRY_POLICY.max_scheduled_retries
RETRY_WINDOW_SECONDS = DEFAULT_RETRY_POLICY.window_seconds


__all__ = [
    "DEFAULT_RETRY_POLICY",
    "MAX_SCHEDULED_RETRIES",
    "RETRY_BASE_SECONDS",
    "RETRY_JITTER_RATIO",
    "RETRY_MAX_SECONDS",
    "RETRY_MULTIPLIER",
    "RETRY_WINDOW_SECONDS",
    "RetryPolicy",
]
