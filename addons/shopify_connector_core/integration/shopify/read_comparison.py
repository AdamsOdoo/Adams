"""Bounded, payload-free comparison helpers for the P06 read migration.

The comparison path is deliberately observational.  It can sample the same
replay-safe *query* through legacy and typed gateways, but it never accepts a
mutation operation and it never stores either response.  Only deterministic
SHA-256 digests and the equality result are suitable for durable evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ...domain.immutability import to_plain


# This is a bounded migration probe, not a workload multiplier.  One stable
# sample in every 100 requests gives enough coverage during a pilot while
# preserving the legacy request rate for the other 99 requests.
DEFAULT_SAMPLE_MODULUS = 100
MAX_SAMPLE_MODULUS = 10_000
_DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")

# These names are the exact read operations extracted in P06.  Keeping the
# allowlist here prevents a future caller from accidentally comparing a write
# or an unbounded/unknown operation.
REPLAY_SAFE_READ_OPERATIONS = frozenset(
    {
        "ConnectorTestConnection",
        "ConnectorFulfillmentLocations",
        "ConnectorProductScan",
        "ConnectorProductImport",
        "ConnectorCustomerImport",
        "ConnectorOrderScan",
        "ConnectorOrderHeader",
        "ConnectorOrderLineItemsPage",
        "ConnectorOrderShippingLinesPage",
        "ConnectorOrderDiscountApplicationsPage",
        # P07 domain read gateways.  These are query-only documents whose
        # typed paths are replay-safe; mutation and lifecycle policy remain
        # outside this comparison allowlist.
        "InventoryPairRead",
        "InventoryObservation",
        "LocationsSync",
        "ConnectorFulfillmentOrdersForOrder",
        "ConnectorFulfillmentOrderLines",
        "ConnectorOrderFulfillments",
        "ConnectorFulfillmentNode",
        "ConnectorFulfillmentNodes",
        "ConnectorWebhookSubscriptions",
    }
)


def _canonical(value: Any) -> str:
    """Serialize a normalized value without accepting arbitrary objects."""

    if hasattr(value, "as_dict") and callable(value.as_dict):
        value = value.as_dict()
    value = to_plain(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("comparison value is not JSON-safe") from exc


def safe_digest(value: Any) -> str:
    """Return a payload-free SHA-256 digest of one normalized result."""

    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _comparison_value(value: Any) -> Any:
    # ReadResult carries observation/request metadata that can legitimately
    # differ between two requests.  Compare the business DTO only; if a
    # caller supplies a plain value, compare that value directly.
    return getattr(value, "value", value)


def _sample_key(store_key: Any, operation_name: str, variables: Mapping[str, Any] | None) -> str:
    if not isinstance(operation_name, str) or operation_name not in REPLAY_SAFE_READ_OPERATIONS:
        raise ValueError("operation is not an allowlisted replay-safe read")
    if not isinstance(store_key, (str, int)) or isinstance(store_key, bool):
        raise TypeError("store_key must be a non-boolean string or integer")
    variables = {} if variables is None else variables
    if not isinstance(variables, Mapping):
        raise TypeError("comparison variables must be a mapping")
    return _canonical({
        "store": str(store_key),
        "operation": operation_name,
        "variables": variables,
    })


def should_compare(
    store_key: Any,
    operation_name: str,
    variables: Mapping[str, Any] | None = None,
    *,
    modulus: int = DEFAULT_SAMPLE_MODULUS,
) -> bool:
    """Choose a stable bounded sample without persisting client data."""

    if isinstance(modulus, bool) or not isinstance(modulus, int) or not 1 <= modulus <= MAX_SAMPLE_MODULUS:
        raise ValueError("comparison modulus is outside its safe bound")
    key = _sample_key(store_key, operation_name, variables)
    value = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:16], 16)
    return value % modulus == 0


@dataclass(frozen=True, slots=True)
class ReadComparisonEvidence:
    """Safe comparison metadata; no raw payload or PII is retained."""

    operation_name: str
    sampled: bool
    equal: bool
    legacy_digest: str | None
    typed_digest: str | None
    typed_error: bool = False

    def __post_init__(self) -> None:
        if self.operation_name not in REPLAY_SAFE_READ_OPERATIONS:
            raise ValueError("operation is not an allowlisted replay-safe read")
        if not isinstance(self.sampled, bool) or not isinstance(self.equal, bool):
            raise TypeError("comparison flags must be bool")
        if not isinstance(self.typed_error, bool):
            raise TypeError("typed_error must be bool")
        for name in ("legacy_digest", "typed_digest"):
            value = getattr(self, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"{name} must be a digest or None")
            if value is not None and not _DIGEST_RE.fullmatch(value):
                raise ValueError(f"{name} must be a SHA-256 digest")
        if not self.sampled and (
            self.legacy_digest is not None
            or self.typed_digest is not None
            or not self.equal
            or self.typed_error
        ):
            raise ValueError("an unsampled comparison cannot carry typed evidence")
        if self.sampled and self.legacy_digest is None:
            raise ValueError("a sampled comparison requires a legacy digest")
        if self.sampled and self.typed_digest is None and not self.typed_error:
            raise ValueError("a sampled comparison requires a typed digest")
        if self.equal != (
            self.legacy_digest is not None
            and self.typed_digest is not None
            and self.legacy_digest == self.typed_digest
        ) and self.sampled:
            raise ValueError("comparison equality does not match its digests")

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_name": self.operation_name,
            "sampled": self.sampled,
            "equal": self.equal,
            "legacy_digest": self.legacy_digest,
            "typed_digest": self.typed_digest,
            "typed_error": self.typed_error,
        }


def compare_values(
    operation_name: str,
    legacy_value: Any,
    typed_value: Any,
) -> ReadComparisonEvidence:
    """Compare two normalized read values and return digest-only evidence."""

    legacy_digest = safe_digest(_comparison_value(legacy_value))
    typed_digest = safe_digest(_comparison_value(typed_value))
    return ReadComparisonEvidence(
        operation_name,
        True,
        legacy_digest == typed_digest,
        legacy_digest,
        typed_digest,
    )


__all__ = [
    "DEFAULT_SAMPLE_MODULUS",
    "MAX_SAMPLE_MODULUS",
    "REPLAY_SAFE_READ_OPERATIONS",
    "ReadComparisonEvidence",
    "compare_values",
    "safe_digest",
    "should_compare",
]
