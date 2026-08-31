"""Small recursive helpers for immutable JSON-shaped contract values.

The public contract objects cross an Odoo RPC boundary eventually, so this
module deliberately accepts only the JSON data model.  Keeping that rule in a
single helper prevents each DTO/command from accidentally accepting a
``datetime``, recordset, ``Decimal`` or other Python object in a nested field.
Typed values which live outside a JSON mapping (for example a command UUID or
an envelope timestamp) are serialized explicitly by their owning contract and
are handled by :func:`to_plain` when a plain response is requested.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
from enum import Enum
from math import isfinite
from types import MappingProxyType
from typing import Any
from uuid import UUID


def _freeze(value: Any, path: str, ancestors: set[int] | None = None) -> Any:
    """Validate and recursively freeze one JSON-shaped value."""

    if ancestors is None:
        ancestors = set()
    # bool is intentionally checked before int: booleans are valid JSON
    # primitives, while callers that expect an integer perform their own
    # stricter field validation.
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} must contain a finite JSON number")
        return value
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in ancestors:
            raise ValueError(f"{path} contains a cyclic contract value")
        ancestors.add(identity)
        try:
            frozen: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str) or not key:
                    raise TypeError(f"{path} contains a non-empty string key requirement")
                frozen[key] = _freeze(item, f"{path}.{key}", ancestors)
            return MappingProxyType(frozen)
        finally:
            ancestors.remove(identity)
    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in ancestors:
            raise ValueError(f"{path} contains a cyclic contract value")
        ancestors.add(identity)
        try:
            return tuple(
                _freeze(item, f"{path}[{index}]", ancestors)
                for index, item in enumerate(value)
            )
        finally:
            ancestors.remove(identity)
    raise TypeError(
        f"{path} contains unsupported {type(value).__name__}; "
        "contract values must be JSON-shaped"
    )


def freeze_value(value: Any) -> Any:
    """Copy JSON-shaped containers into immutable equivalents.

    Contract objects are frozen dataclasses, but a shallow mapping proxy would
    still allow mutation through a nested dictionary or list.  V2 payloads
    are JSON-shaped, so mappings and sequences are recursively validated and
    frozen.  Unsupported Python objects are rejected instead of being carried
    to a later serializer.
    """

    return _freeze(value, "$")


def _plain(value: Any, path: str, ancestors: set[int] | None = None) -> Any:
    """Convert immutable/native contract values into JSON-compatible values.

    UUID, enum and aware-UTC datetime conversion is intentionally explicit.
    These types are useful for typed fields such as command IDs and timestamps
    but are not accepted as arbitrary nested payload values by
    :func:`freeze_value`.
    """

    if ancestors is None:
        ancestors = set()
    if isinstance(value, Enum):
        return _plain(value.value, path, ancestors)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() != timedelta(0):
            raise ValueError(f"{path} datetime must be timezone-aware UTC")
        return value.isoformat()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError(f"{path} must contain a finite JSON number")
        return value
    if isinstance(value, Mapping):
        identity = id(value)
        if identity in ancestors:
            raise ValueError(f"{path} contains a cyclic contract value")
        ancestors.add(identity)
        try:
            plain: dict[str, Any] = {}
            for key, item in value.items():
                if not isinstance(key, str) or not key:
                    raise TypeError(f"{path} contains a non-empty string key requirement")
                plain[key] = _plain(item, f"{path}.{key}", ancestors)
            return plain
        finally:
            ancestors.remove(identity)
    if isinstance(value, (list, tuple)):
        identity = id(value)
        if identity in ancestors:
            raise ValueError(f"{path} contains a cyclic contract value")
        ancestors.add(identity)
        try:
            return [_plain(item, f"{path}[{index}]", ancestors) for index, item in enumerate(value)]
        finally:
            ancestors.remove(identity)
    raise TypeError(
        f"{path} contains unsupported {type(value).__name__}; "
        "cannot serialize contract value"
    )


def to_plain(value: Any) -> Any:
    """Convert contract values back to JSON-compatible plain values.

    Unlike ``dataclasses.asdict`` this function does not traverse arbitrary
    Python objects.  Rejecting an unsupported value is safer than silently
    stringifying a record, secret or exception at the RPC boundary.
    """

    return _plain(value, "$")


__all__ = ["freeze_value", "to_plain"]
