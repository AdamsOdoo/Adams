"""Pure mixed-drain capacity accounting for the P10 runtime."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def reserve_capacity_after_v2(
    capacity: int,
    report: Mapping[str, Any],
) -> tuple[int, int]:
    """Return ``(legacy_capacity, finalized_count)`` after a V2 pass.

    A claimed item has already consumed one worker/request slot even when
    finalization is delayed or fails.  Counting only finalized items would
    let a mixed cron pass exceed its configured cap.  The report is validated
    strictly because this helper sits at a scheduler boundary; malformed
    accounting fails closed instead of silently running extra legacy work.
    """
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
        raise ValueError("capacity must be a positive integer")
    if not isinstance(report, Mapping):
        raise TypeError("V2 report must be a mapping")
    claimed = report.get("claimed_count")
    finalized = report.get("finalized_count")
    for name, value in (("claimed_count", claimed), ("finalized_count", finalized)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if claimed > capacity:
        raise ValueError("V2 claimed count exceeds mixed-drain capacity")
    if finalized > claimed:
        raise ValueError("V2 finalized count exceeds claimed count")
    return capacity - claimed, finalized


__all__ = ["reserve_capacity_after_v2"]
