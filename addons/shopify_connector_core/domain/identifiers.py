"""Small value validators for opaque and tenant-scoped identifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass


_KEY = re.compile(r"^[a-z][a-z0-9_.:-]*$")
_RUN_REF = re.compile(r"^(?:job|run):[1-9][0-9]*$")
_GID = re.compile(r"^gid://shopify/[A-Za-z][A-Za-z0-9_]*/[1-9][0-9]*$")


def require_key(value: str, field_name: str = "key") -> str:
    if not isinstance(value, str) or not _KEY.fullmatch(value):
        raise ValueError(f"{field_name} must be a lower-case registry key")
    return value


def require_run_ref(value: str) -> str:
    if not isinstance(value, str) or not _RUN_REF.fullmatch(value):
        raise ValueError("run_ref must be an opaque job:<id> or run:<id> reference")
    return value


def require_shopify_gid(value: str) -> str:
    if not isinstance(value, str) or not _GID.fullmatch(value):
        raise ValueError("Shopify identity must be a canonical GID")
    return value


@dataclass(frozen=True, slots=True)
class RunReference:
    value: str

    def __post_init__(self) -> None:
        require_run_ref(self.value)

    def __str__(self) -> str:
        return self.value


__all__ = [
    "RunReference",
    "require_key",
    "require_run_ref",
    "require_shopify_gid",
]
