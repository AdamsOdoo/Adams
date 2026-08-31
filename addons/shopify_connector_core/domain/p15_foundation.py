"""Pure contracts for the small P15 foundation closure.

This module deliberately has no Odoo import.  It is the shared vocabulary
for the named operation seam, semantic setup payloads, activation lifecycle,
and bounded command-result replay.  Adapters still own authorization and
the legacy services remain the source of truth for every operation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .immutability import to_plain


MAX_COMMAND_RESULT_BYTES = 32 * 1024
MAX_COMMAND_RESULT_ITEMS = 128
MAX_COMMAND_RESULT_TEXT = 2000
MAX_COMMAND_RESULT_DEPTH = 8


# The registry is intentionally small.  Every entry is already implemented
# by a named legacy read/diagnostic or reconciliation service.  In particular
# no inventory push, product export, fulfillment mutation, or generic model
# dispatch may be added by merely putting a string in a request payload.
READ_ONLY_OPERATION_SPECS = (
    {
        "key": "core_readiness_check",
        "label": "Run readiness checks",
        "job_type": "core_readiness_check",
        "mode": "read",
        "requires_connected": False,
    },
    {
        "key": "core_test_connection",
        "label": "Test connection",
        "job_type": "core_test_connection",
        "mode": "read",
        "requires_connected": False,
    },
    {
        "key": "product_import_scan",
        "label": "Scan Shopify products",
        "job_type": "product_import_scan",
        "mode": "read",
        "requires_connected": True,
    },
    {
        "key": "inventory_location_sync",
        "label": "Refresh Shopify locations",
        "job_type": "inventory_location_sync",
        "mode": "read",
        "requires_connected": True,
    },
    {
        "key": "fulfillment_reconciliation_check",
        "label": "Reconcile fulfillment evidence",
        "job_type": "fulfillment_reconciliation_check",
        "mode": "reconciliation",
        "requires_connected": True,
    },
)

READ_ONLY_OPERATION_BY_KEY = {
    item["key"]: item for item in READ_ONLY_OPERATION_SPECS
}


# A step may only persist values which have an existing owner in the legacy
# settings model, or a deliberately boring acknowledgement used by a step
# whose owner is an optional domain addon.  Credentials and arbitrary record
# ids are never accepted here.  The Odoo adapter intersects the field entries
# with installed fields and applies the field's own type/selection checks.
SETUP_STEP_PAYLOAD_FIELDS = {
    "welcome": frozenset(),
    "identity": frozenset(),
    "credential": frozenset(),
    "scopes": frozenset(("acknowledged",)),
    "test_connection": frozenset(),
    "directions": frozenset((
        "product_domain_enabled",
        "product_export_domain_enabled",
        "sale_domain_enabled",
        "inventory_domain_enabled",
        "fulfillment_domain_enabled",
    )),
    "location_mapping": frozenset(("acknowledged",)),
    "source_of_truth": frozenset((
        "product_first_sync_source",
        "price_source_of_truth",
        "media_source_of_truth",
    )),
    "notification": frozenset(("notification_default_enabled",)),
    "first_push": frozenset(("inventory_scheduled_sync_enabled",)),
    "final_readiness": frozenset(),
    "review": frozenset(),
}

_SECRET_KEY_PARTS = (
    "token", "secret", "password", "credential", "authorization",
)


def operation_spec(operation_key: Any) -> Mapping[str, Any]:
    """Return a copy of one registered read-only operation, or fail closed."""

    if not isinstance(operation_key, str):
        raise ValueError("operation_key must be a string")
    spec = READ_ONLY_OPERATION_BY_KEY.get(operation_key)
    if spec is None:
        raise ValueError("operation is not registered")
    return dict(spec)


def validate_setup_payload(step_key: Any, values: Any) -> dict[str, Any]:
    """Validate the shape and closed keys of one semantic setup payload.

    Type and selection validation for settings-backed fields belongs to the
    Odoo field metadata.  This pure guard still rejects arbitrary nested
    structures, credentials, and unsupported step/key combinations before an
    adapter can persist anything.
    """

    if not isinstance(step_key, str) or step_key not in SETUP_STEP_PAYLOAD_FIELDS:
        raise ValueError("unsupported setup step")
    if values in (None, False):
        values = {}
    if not isinstance(values, Mapping):
        raise TypeError("setup values must be a mapping")
    if any(not isinstance(key, str) or not key for key in values):
        raise TypeError("setup value keys must be non-empty strings")
    allowed = SETUP_STEP_PAYLOAD_FIELDS[step_key]
    unknown = set(values) - allowed
    if unknown:
        raise ValueError("setup payload contains unsupported fields")
    normalized = {}
    for key, value in values.items():
        if key == "acknowledged":
            if not isinstance(value, bool):
                raise TypeError("acknowledged must be boolean")
            normalized[key] = value
            continue
        if any(part in key.casefold() for part in _SECRET_KEY_PARTS):
            raise ValueError("setup payload cannot contain credential material")
        if isinstance(value, (Mapping, list, tuple)):
            raise TypeError("settings payload values must be scalar")
        if not isinstance(value, (str, bool, int, float)) and value is not None:
            raise TypeError("setup payload value is not JSON-shaped")
        normalized[key] = value
    return normalized


def activation_transition(current: str, target: str) -> str:
    """Validate the reversible activation dimension independently of connect."""

    transitions = {
        "draft": frozenset(("active", "retired")),
        "active": frozenset(("paused", "retired")),
        "paused": frozenset(("active", "retired")),
        "retired": frozenset(),
    }
    if current not in transitions or target not in transitions:
        raise ValueError("unknown activation state")
    if current == target:
        return target
    if target not in transitions[current]:
        raise ValueError("activation transition is not permitted")
    return target


def command_scope_key(company_id: int, store_id: int | None) -> str:
    """Normalize the nullable create scope for a durable uniqueness key."""

    if isinstance(company_id, bool) or not isinstance(company_id, int) or company_id <= 0:
        raise ValueError("company_id must be positive")
    if store_id is None:
        return "company:%d" % company_id
    if isinstance(store_id, bool) or not isinstance(store_id, int) or store_id <= 0:
        raise ValueError("store_id must be positive")
    return "store:%d" % store_id


def command_request_fingerprint(
    *, company_id: int, store_id: int | None, command_id: str,
    command_name: str, payload: Mapping[str, Any], expected_generation: int,
) -> str:
    """Fingerprint identity + payload without storing secrets or timestamps."""

    if (
        isinstance(expected_generation, bool)
        or not isinstance(expected_generation, int)
        or expected_generation < 0
    ):
        raise ValueError("expected_generation must be a nonnegative integer")

    body = {
        "company_id": company_id,
        "store_scope": command_scope_key(company_id, store_id),
        "command_id": command_id,
        "command_name": command_name,
        # Reusing a command id after the connection/configuration contract
        # advances is not the same request, even when the visible payload is
        # byte-identical.  Bind the server-validated generation so a stale
        # durable result cannot be replayed into a newer store state.
        "expected_generation": expected_generation,
        # CommandEnvelope freezes nested payloads as mapping proxies/tuples;
        # normalize those immutable containers before hashing so the replay
        # key is stable for both typed and plain mapping callers.
        "payload": to_plain(payload),
    }
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
        .encode("utf-8")
    ).hexdigest()


def sanitize_command_result(value: Any) -> tuple[Any, str]:
    """Return a bounded JSON result and its canonical representation.

    The result is intentionally stricter than the general UI serializer.  It
    accepts only the small acknowledgement-shaped dicts emitted by named
    commands, rejects raw credential keys recursively, and caps both nesting
    breadth and encoded size before durable storage.
    """

    def visit(item: Any, path: str = "$", depth: int = 0) -> Any:
        if depth > MAX_COMMAND_RESULT_DEPTH:
            raise ValueError("command result is nested too deeply")
        if item is None or isinstance(item, (str, bool, int, float)):
            if isinstance(item, float) and (item != item or item in (float("inf"), float("-inf"))):
                raise ValueError("command result contains a non-finite number")
            if isinstance(item, str) and len(item) > MAX_COMMAND_RESULT_TEXT:
                raise ValueError("command result text is too long")
            return item
        if isinstance(item, Mapping):
            if len(item) > MAX_COMMAND_RESULT_ITEMS:
                raise ValueError("command result contains too many fields")
            result = {}
            for key, child in item.items():
                if not isinstance(key, str) or not key:
                    raise TypeError("command result keys must be strings")
                normalized = key.casefold()
                if any(part in normalized for part in _SECRET_KEY_PARTS):
                    raise ValueError("command result contains credential material")
                result[key] = visit(child, "%s.%s" % (path, key), depth + 1)
            return result
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            if len(item) > MAX_COMMAND_RESULT_ITEMS:
                raise ValueError("command result contains too many items")
            return [
                visit(child, "%s[%d]" % (path, index), depth + 1)
                for index, child in enumerate(item)
            ]
        raise TypeError("command result is not JSON-shaped")

    normalized = visit(value)
    encoded = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )
    if len(encoded.encode("utf-8")) > MAX_COMMAND_RESULT_BYTES:
        raise ValueError("command result exceeds the bounded replay size")
    return normalized, encoded


__all__ = [
    "MAX_COMMAND_RESULT_BYTES",
    "MAX_COMMAND_RESULT_ITEMS",
    "MAX_COMMAND_RESULT_TEXT",
    "MAX_COMMAND_RESULT_DEPTH",
    "READ_ONLY_OPERATION_BY_KEY",
    "READ_ONLY_OPERATION_SPECS",
    "SETUP_STEP_PAYLOAD_FIELDS",
    "activation_transition",
    "command_request_fingerprint",
    "command_scope_key",
    "operation_spec",
    "sanitize_command_result",
    "validate_setup_payload",
]
