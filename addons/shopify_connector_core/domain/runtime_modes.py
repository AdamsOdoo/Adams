"""Ordered V2 runtime capability lattice shared by every rollout adapter."""

from __future__ import annotations


V2_RUNTIME_MODE_ORDER = (
    "legacy",
    "read_only",
    "subscriptions",
    "inventory",
    "product_export",
    "fulfillment",
    "all",
)
V2_RUNTIME_CAPABILITIES = V2_RUNTIME_MODE_ORDER[1:-1]
_MODE_RANK = {mode: rank for rank, mode in enumerate(V2_RUNTIME_MODE_ORDER)}


def _mode(value: str, field_name: str) -> str:
    if not isinstance(value, str) or value not in _MODE_RANK:
        raise ValueError("%s is not a supported V2 runtime mode" % field_name)
    return value


def runtime_mode_includes(current_mode: str, capability: str) -> bool:
    """Whether one store mode contains the named cumulative capability."""

    current_mode = _mode(current_mode, "current_mode")
    capability = _mode(capability, "capability")
    if capability not in V2_RUNTIME_CAPABILITIES:
        raise ValueError("capability must name a cumulative V2 runtime rung")
    return _MODE_RANK[current_mode] >= _MODE_RANK[capability]


def runtime_modes_including(capability: str) -> tuple[str, ...]:
    """Return the code-owned SQL/ORM allowlist for one capability rung."""

    return tuple(
        mode for mode in V2_RUNTIME_MODE_ORDER
        if runtime_mode_includes(mode, capability)
    )


__all__ = [
    "V2_RUNTIME_CAPABILITIES",
    "V2_RUNTIME_MODE_ORDER",
    "runtime_mode_includes",
    "runtime_modes_including",
]
