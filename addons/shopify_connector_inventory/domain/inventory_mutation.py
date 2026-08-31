"""Pure P12 inventory mutation payload and evidence contracts.

This module owns the typed intent, exact pair scope, observation/mapping
snapshots and canonical preview fingerprint used before the V1 inventory
service reaches a Shopify write.  Admission itself lives in
``inventory_admission`` so each pure production module remains comfortably
below the change-size ceiling.  Nothing here has an Odoo, database, transport,
credential or job-runtime dependency.  The existing V1 service remains
authoritative until an application/runtime adapter is wired in.

The contracts preserve the important V1 invariants:

* one exact ``InventoryItem``/``Location`` pair owns one operation scope;
* location mapping and store/company identity are explicit, never inferred;
* Shopify pair observation is current and identity-checked before a mutation;
* a first push needs preview evidence and explicit Administrator confirmation;
* quantities are non-negative integral values and set-quantity uses CAS;
* uncertain writes are resolved by an exact pair readback and are never
  replayed blindly.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from math import isfinite
from typing import Any

from shopify_connector_core.domain.immutability import freeze_value, to_plain


INVENTORY_ACTIVATE_OPERATION = "inventory_activate"
INVENTORY_SET_QUANTITIES_OPERATION = "inventory_set_quantities"
INVENTORY_PAIR_SCOPE_PREFIX = "inventory_pair"
MAX_CAS_RETRY_ORDINAL = 3
QUANTITY_INTEGRALITY_TOLERANCE = 1e-4
DEFAULT_MAX_OBSERVATION_AGE_SECONDS = 15 * 60

_GID = re.compile(
    r"^gid://shopify/(?P<kind>[A-Za-z][A-Za-z0-9_]*)/(?P<id>[1-9][0-9]*)$"
)
_SHOP_DOMAIN = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$"
)
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class InventoryMutationOperation(str, Enum):
    """The two V1 inventory mutation domains, kept as job/domain values."""

    ACTIVATE = INVENTORY_ACTIVATE_OPERATION
    SET_QUANTITIES = INVENTORY_SET_QUANTITIES_OPERATION


class CoalescingAction(str, Enum):
    """Disposition for a local event after admission checks."""

    ENQUEUE = "enqueue"
    COALESCE = "coalesce"
    SKIP = "skip"
    REJECT = "reject"


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")
    return value


def _nonnegative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer")
    return value


def _strict_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be a strict integer")
    return value


def _text(value: Any, field_name: str, *, max_length: int = 2048) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValueError(f"{field_name} must be a bounded non-empty string")
    return value


def _gid(value: Any, kind: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a canonical Shopify GID")
    match = _GID.fullmatch(value)
    if match is None or match.group("kind") != kind:
        raise ValueError(f"{field_name} must be a canonical Shopify {kind} GID")
    return value

def _shop_domain(value: Any, field_name: str = "store_identity") -> str:
    if not isinstance(value, str) or not _SHOP_DOMAIN.fullmatch(value):
        raise ValueError(f"{field_name} must be a canonical myshopify.com domain")
    return value

def _operation(value: Any) -> str:
    try:
        return value.value if isinstance(value, InventoryMutationOperation) else InventoryMutationOperation(value).value
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unsupported inventory mutation operation: {value!r}") from exc


def _utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must be a datetime or ISO timestamp")
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return value

def _timestamp(value: Any, field_name: str, *, allow_none: bool = True, strict: bool = True) -> datetime | None:
    if value is None or value is False or value == "":
        if allow_none:
            return None
        raise ValueError(f"{field_name} is required")
    if isinstance(value, datetime):
        try:
            return _utc(value, field_name)
        except (TypeError, ValueError):
            if not strict:
                return None
            raise
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be an ISO timestamp")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except (TypeError, ValueError, OverflowError) as exc:
        if not strict:
            return None
        raise ValueError(f"{field_name} must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if not strict:
            return None
        raise ValueError(f"{field_name} must include a timezone")
    if parsed.utcoffset() != timedelta(0):
        if not strict:
            return None
        raise ValueError(f"{field_name} must be timezone-aware UTC")
    return parsed.astimezone(timezone.utc)


def integral_quantity(value: Any, field_name: str = "quantity") -> int | None:
    """Return a safe integral quantity or ``None`` for a meaningful fraction.

    V1 derives quantities from Odoo floats, clamps negative ``free_qty`` to
    zero, accepts harmless floating point noise around a whole number, and
    refuses to round a meaningful fraction.  Shopify-side quantities remain
    strict integers and are validated separately by the P08 gateway.
    """

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not isfinite(value):
        return None
    if value < 0:
        return 0
    rounded = round(value)
    if abs(value - rounded) <= QUANTITY_INTEGRALITY_TOLERANCE:
        return int(rounded)
    return None


@dataclass(frozen=True, slots=True)
class InventoryPairScope:
    """Validated, store-bound identity for one inventory item/location pair.

    A scope is an authority object, not a caller-supplied string.  The
    gateway accepts this object so an arbitrary scope cannot be smuggled into
    the durable intent or cause two unrelated pairs to coalesce.
    """

    store_id: int
    inventory_item_gid: str
    location_gid: str

    def __post_init__(self) -> None:
        _positive_int(self.store_id, "scope.store_id")
        _gid(self.inventory_item_gid, "InventoryItem", "scope.inventory_item_gid")
        _gid(self.location_gid, "Location", "scope.location_gid")

    @property
    def operation_scope_key(self) -> str:
        return f"{INVENTORY_PAIR_SCOPE_PREFIX}:{self.store_id}:{self.inventory_item_gid}:{self.location_gid}"

    @property
    def key(self) -> str:
        """Short alias for application/runtime ports."""

        return self.operation_scope_key

    def as_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "inventory_item_gid": self.inventory_item_gid,
            "location_gid": self.location_gid,
            "operation_scope_key": self.operation_scope_key,
        }


def derive_inventory_operation_scope(
    store_id: int,
    inventory_item_gid: str,
    location_gid: str,
) -> str:
    """Derive V1's exact server-owned pair scope literal.

    The scope deliberately excludes operation type: activation and quantity
    set for one pair serialize behind one another.  Callers that cross the
    gateway boundary must carry the validated :class:`InventoryPairScope`
    object instead of choosing a custom string.
    """

    return InventoryPairScope(store_id, inventory_item_gid, location_gid).operation_scope_key


@dataclass(frozen=True, slots=True)
class InventoryMappingSnapshot:
    """Immutable exact location-mapping evidence supplied by an adapter."""

    store_id: int
    mapping_id: int
    company_id: int | None
    shopify_location_gid: str
    odoo_location_id: int
    status: str = "active"
    push_enabled: bool = True
    one_to_one: bool = True

    def __post_init__(self) -> None:
        _positive_int(self.store_id, "mapping.store_id")
        _positive_int(self.mapping_id, "mapping.mapping_id")
        if self.company_id is not None:
            _positive_int(self.company_id, "mapping.company_id")
        _gid(self.shopify_location_gid, "Location", "mapping.shopify_location_gid")
        _positive_int(self.odoo_location_id, "mapping.odoo_location_id")
        if self.status not in {"active", "inactive", "review", "stale", "manually_overridden"}:
            raise ValueError("mapping.status is not supported")
        if not isinstance(self.push_enabled, bool):
            raise TypeError("mapping.push_enabled must be bool")
        if not isinstance(self.one_to_one, bool):
            raise TypeError("mapping.one_to_one must be bool")

    @property
    def active(self) -> bool:
        return self.status == "active"

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "InventoryMappingSnapshot":
        if not isinstance(value, Mapping):
            raise TypeError("mapping must be an object")
        active = value.get("active")
        status = value.get("status", "active")
        if active is not None:
            if not isinstance(active, bool):
                raise TypeError("mapping.active must be bool")
            status = "active" if active else "inactive"
        return cls(
            store_id=value.get("store_id"),
            mapping_id=value.get("mapping_id", value.get("id", 1)),
            company_id=value.get("company_id"),
            shopify_location_gid=value.get("shopify_location_gid", value.get("shopify_gid")),
            odoo_location_id=value.get("odoo_location_id"),
            status=status,
            push_enabled=value.get("push_enabled", True),
            one_to_one=value.get("one_to_one", True),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "store_id": self.store_id,
            "mapping_id": self.mapping_id,
            "company_id": self.company_id,
            "shopify_location_gid": self.shopify_location_gid,
            "odoo_location_id": self.odoo_location_id,
            "status": self.status,
            "push_enabled": self.push_enabled,
            "one_to_one": self.one_to_one,
        }


@dataclass(frozen=True, slots=True)
class InventoryPairObservation:
    """Normalized current Shopify state for exactly one item/location pair."""

    store_identity: str
    item_exists: bool
    tracked: bool | None
    level_exists: bool
    inventory_item_gid: str | None = None
    location_gid: str | None = None
    inventory_level_gid: str | None = None
    available: int | None = None
    updated_at: datetime | str | None = None
    observed_at: datetime | str | None = None
    fresh: bool = True

    def __post_init__(self) -> None:
        _shop_domain(self.store_identity)
        for name in ("item_exists", "level_exists", "fresh"):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"observation.{name} must be bool")
        if self.tracked is not None and not isinstance(self.tracked, bool):
            raise TypeError("observation.tracked must be bool or None")
        if self.inventory_item_gid is not None:
            _gid(self.inventory_item_gid, "InventoryItem", "observation.inventory_item_gid")
        if self.location_gid is not None:
            _gid(self.location_gid, "Location", "observation.location_gid")
        if not self.item_exists:
            if self.tracked is not None or self.level_exists:
                raise ValueError("a missing inventory item cannot have level state")
            if self.inventory_level_gid is not None or self.available is not None:
                raise ValueError("a missing inventory item cannot have level data")
        elif self.tracked is None:
            raise ValueError("an existing inventory item needs tracked state")
        if self.level_exists:
            if self.inventory_level_gid is None or self.available is None:
                raise ValueError("an existing level needs identity and quantity")
            _gid(self.inventory_level_gid, "InventoryLevel", "observation.inventory_level_gid")
            _strict_int(self.available, "observation.available")
        elif self.inventory_level_gid is not None or self.available is not None:
            raise ValueError("a missing inventory level cannot have level data")
        # Preserve malformed Shopify timestamps as inconclusive evidence.
        _timestamp(self.updated_at, "observation.updated_at", strict=False)
        _timestamp(self.observed_at, "observation.observed_at", strict=False)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "InventoryPairObservation":
        if not isinstance(value, Mapping):
            raise TypeError("observation must be an object")
        return cls(
            store_identity=value.get("store_identity", value.get("store_domain")),
            item_exists=value.get("item_exists", False),
            tracked=value.get("tracked"),
            level_exists=value.get("level_exists", False),
            inventory_item_gid=value.get("inventory_item_gid", value.get("item_gid")),
            location_gid=value.get("location_gid"),
            inventory_level_gid=value.get("inventory_level_gid"),
            available=value.get("available"),
            updated_at=value.get("updated_at"),
            observed_at=value.get("observed_at"),
            fresh=value.get("fresh", True),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "store_identity": self.store_identity,
            "item_exists": self.item_exists,
            "tracked": self.tracked,
            "level_exists": self.level_exists,
            "inventory_item_gid": self.inventory_item_gid,
            "location_gid": self.location_gid,
            "inventory_level_gid": self.inventory_level_gid,
            "available": self.available,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
            "observed_at": self.observed_at.isoformat() if isinstance(self.observed_at, datetime) else self.observed_at,
            "fresh": self.fresh,
        }


# The shorter name is useful at application boundaries and mirrors the V1
# vocabulary without creating a second DTO implementation.
InventoryObservation = InventoryPairObservation


# The application layer registers one opaque construction capability when it
# is imported.  Keeping the capability out of this module's public API means
# a domain caller cannot manufacture an accepted first-push confirmation by
# calling a convenience constructor.  The registration is one-way so a later
# caller cannot replace the trusted capability with its own object.
_REGISTERED_CONFIRMATION_CAPABILITY: object | None = None


def _register_confirmation_capability(capability: object) -> None:
    """Bind the domain value object to the application-owned capability."""

    global _REGISTERED_CONFIRMATION_CAPABILITY
    if not isinstance(capability, object):  # pragma: no cover - all Python values are objects
        raise TypeError("confirmation capability must be an object")
    if _REGISTERED_CONFIRMATION_CAPABILITY is not None:
        if _REGISTERED_CONFIRMATION_CAPABILITY is not capability:
            raise RuntimeError("first-push confirmation capability is already bound")
        return
    _REGISTERED_CONFIRMATION_CAPABILITY = capability


@dataclass(frozen=True, slots=True)
class FirstPushConfirmation:
    """Immutable server-attested first-push actor/evidence contract.

    The domain can carry and fingerprint the evidence, but it cannot mint an
    attestation.  The application-owned factory is used only after a trusted
    server adapter validates the durable confirmation row and actor.  The
    application still validates the confirmation at its write boundary; a DTO
    alone is never authorization.
    """

    confirmation_id: int
    confirmed_by_uid: int
    confirmed_at: datetime
    evidence_ref: str
    _attestation: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _positive_int(self.confirmation_id, "first_push_confirmation.confirmation_id")
        _positive_int(self.confirmed_by_uid, "first_push_confirmation.confirmed_by_uid")
        confirmed_at = _timestamp(
            self.confirmed_at,
            "first_push_confirmation.confirmed_at",
            allow_none=False,
            strict=True,
        )
        if confirmed_at is None:  # pragma: no cover - guarded by allow_none=False
            raise ValueError("first_push_confirmation.confirmed_at is required")
        _text(self.evidence_ref, "first_push_confirmation.evidence_ref", max_length=512)
        if (
            _REGISTERED_CONFIRMATION_CAPABILITY is None
            or self._attestation is not _REGISTERED_CONFIRMATION_CAPABILITY
        ):
            raise ValueError("first-push confirmation must be application-attested")
        object.__setattr__(self, "confirmed_at", confirmed_at)

    def fingerprint_dict(self) -> dict[str, Any]:
        """Return stable actor/evidence identity without mutable clock data."""

        return {
            "confirmation_id": self.confirmation_id,
            "confirmed_by_uid": self.confirmed_by_uid,
            "evidence_ref": self.evidence_ref,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.fingerprint_dict(),
            "confirmed_at": self.confirmed_at.isoformat(),
        }


@dataclass(frozen=True, slots=True)
class InventoryMutationPayload:
    """Typed, store-scoped mutation intent plus its admission evidence."""

    store_id: int
    company_id: int
    expected_generation: int
    expected_store_identity: str
    operation: str | InventoryMutationOperation
    inventory_item_gid: str
    location_gid: str
    target_quantity: int | float
    change_from_quantity: int | None = None
    reference_document_uri: str | None = None
    mapping: InventoryMappingSnapshot | Mapping[str, Any] | None = None
    observation: InventoryPairObservation | Mapping[str, Any] | None = None
    first_push_state: str = "pending"
    preview_fingerprint: str | None = None
    current_generation: int | None = None
    current_store_identity: str | None = None
    cas_retry_ordinal: int = 0
    first_push_required: bool = True
    idempotency_key: str | None = None
    snapshot_taken_at: datetime | str | None = None
    first_push_confirmation: FirstPushConfirmation | None = None

    def __post_init__(self) -> None:
        _positive_int(self.store_id, "store_id")
        _positive_int(self.company_id, "company_id")
        _nonnegative_int(self.expected_generation, "expected_generation")
        if self.current_generation is not None:
            _nonnegative_int(self.current_generation, "current_generation")
        _shop_domain(self.expected_store_identity, "expected_store_identity")
        if self.current_store_identity is not None:
            _shop_domain(self.current_store_identity, "current_store_identity")
        object.__setattr__(self, "operation", _operation(self.operation))
        _gid(self.inventory_item_gid, "InventoryItem", "inventory_item_gid")
        _gid(self.location_gid, "Location", "location_gid")
        if isinstance(self.target_quantity, bool) or not isinstance(self.target_quantity, (int, float)):
            raise TypeError("target_quantity must be a number")
        if not isfinite(self.target_quantity) or self.target_quantity < 0:
            raise ValueError("target_quantity must be a finite non-negative number")
        if self.change_from_quantity is not None:
            _strict_int(self.change_from_quantity, "change_from_quantity")
        if self.reference_document_uri is not None:
            _text(self.reference_document_uri, "reference_document_uri")
        if self.first_push_state not in {"pending", "previewed", "confirmed"}:
            raise ValueError("first_push_state is not supported")
        if self.preview_fingerprint is not None and not _SHA256.fullmatch(self.preview_fingerprint):
            raise ValueError("preview_fingerprint must be lowercase SHA-256")
        _nonnegative_int(self.cas_retry_ordinal, "cas_retry_ordinal")
        if self.cas_retry_ordinal > MAX_CAS_RETRY_ORDINAL:
            raise ValueError("cas_retry_ordinal exceeds the V1 safety ceiling")
        if not isinstance(self.first_push_required, bool):
            raise TypeError("first_push_required must be bool")
        if self.first_push_confirmation is not None and not isinstance(self.first_push_confirmation, FirstPushConfirmation):
            raise TypeError("first_push_confirmation must be server-attested FirstPushConfirmation or None")
        if self.idempotency_key is not None:
            _text(self.idempotency_key, "idempotency_key", max_length=512)
        _timestamp(self.snapshot_taken_at, "snapshot_taken_at")
        mapping = self.mapping
        if mapping is not None and not isinstance(mapping, InventoryMappingSnapshot):
            mapping = InventoryMappingSnapshot.from_mapping(mapping)
        object.__setattr__(self, "mapping", mapping)
        observation = self.observation
        if observation is not None and not isinstance(observation, InventoryPairObservation):
            observation = InventoryPairObservation.from_mapping(observation)
        object.__setattr__(self, "observation", observation)

    @property
    def operation_scope_key(self) -> str:
        return derive_inventory_operation_scope(
            self.store_id, self.inventory_item_gid, self.location_gid,
        )

    @property
    def normalized_target_quantity(self) -> int | None:
        return integral_quantity(self.target_quantity)

    @property
    def is_first_push(self) -> bool:
        # A confirmed first-push row is still the first mutation until the
        # runtime records that its one-time ceremony has been consumed.  The
        # state guard prevents a caller from turning an unconfirmed row into
        # continuous work by setting ``first_push_required=False``.
        return self.first_push_required or self.first_push_state != "confirmed"

    def business_intent(self) -> dict[str, Any]:
        operation_key = (
            "inventory.activate"
            if self.operation == INVENTORY_ACTIVATE_OPERATION
            else "inventory.set_quantities"
        )
        result = {
            "operation": self.operation,
            "operation_key": operation_key,
            "store_id": self.store_id,
            "company_id": self.company_id,
            "expected_generation": self.expected_generation,
            "current_generation": self.current_generation,
            "expected_store_identity": self.expected_store_identity,
            "current_store_identity": self.current_store_identity,
            "mutation_domain": self.operation,
            "inventory_item_gid": self.inventory_item_gid,
            "location_gid": self.location_gid,
            "target_quantity": self.normalized_target_quantity,
            "change_from_quantity": self.change_from_quantity,
        }
        if self.operation == INVENTORY_ACTIVATE_OPERATION:
            result["initial_available"] = 0
        return result

    def preconditions_snapshot(self) -> dict[str, Any]:
        result = self.business_intent()
        if self.snapshot_taken_at is not None:
            result["snapshot_taken_at"] = (
                self.snapshot_taken_at.isoformat()
                if isinstance(self.snapshot_taken_at, datetime)
                else self.snapshot_taken_at
            )
        return result

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "store_id": self.store_id,
            "company_id": self.company_id,
            "expected_generation": self.expected_generation,
            "expected_store_identity": self.expected_store_identity,
            "current_generation": self.current_generation,
            "current_store_identity": self.current_store_identity,
            "operation": self.operation,
            "inventory_item_gid": self.inventory_item_gid,
            "location_gid": self.location_gid,
            "operation_scope_key": self.operation_scope_key,
            "target_quantity": self.target_quantity,
            "normalized_target_quantity": self.normalized_target_quantity,
            "change_from_quantity": self.change_from_quantity,
            "reference_document_uri": self.reference_document_uri,
            "mapping": self.mapping.as_dict() if self.mapping else None,
            "observation": self.observation.as_dict() if self.observation else None,
            "first_push_state": self.first_push_state,
            "preview_fingerprint": self.preview_fingerprint,
            "cas_retry_ordinal": self.cas_retry_ordinal,
            "first_push_required": self.first_push_required,
            "first_push_confirmation": self.first_push_confirmation.as_dict() if self.first_push_confirmation else None,
        })


@dataclass(frozen=True, slots=True)
class InventoryPreview:
    """Current preview evidence and its canonical fingerprint."""

    payload: InventoryMutationPayload
    generated_at: datetime
    fingerprint: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.payload, InventoryMutationPayload):
            raise TypeError("preview.payload must be InventoryMutationPayload")
        _utc(self.generated_at, "preview.generated_at")
        computed = canonical_preview_fingerprint(self.payload)
        if self.fingerprint and self.fingerprint != computed:
            raise ValueError("preview fingerprint does not match its evidence")
        object.__setattr__(self, "fingerprint", computed)

    def as_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at.isoformat(),
            "fingerprint": self.fingerprint,
            "payload": self.payload.as_dict(),
        }


def _fingerprint_material(payload: InventoryMutationPayload) -> dict[str, Any]:
    # Fingerprints bind authority and business facts, not clocks or freshness
    # hints.  In particular, a readback timestamp changing between preview
    # and admission must not turn an otherwise identical intent into a new
    # mutation; freshness is independently revalidated by admission/readback.
    mapping = payload.mapping.as_dict() if payload.mapping else None
    observation = None
    if payload.observation:
        raw_observation = payload.observation.as_dict()
        observation = {
            key: raw_observation[key]
            for key in (
                "store_identity",
                "item_exists",
                "tracked",
                "level_exists",
                "inventory_item_gid",
                "location_gid",
                "inventory_level_gid",
                "available",
            )
        }
    return {
        "contract_version": 1,
        "store_id": payload.store_id,
        "company_id": payload.company_id,
        "expected_generation": payload.expected_generation,
        "expected_store_identity": payload.expected_store_identity,
        "current_generation": payload.current_generation,
        "current_store_identity": payload.current_store_identity,
        "operation": payload.operation,
        "operation_scope_key": payload.operation_scope_key,
        "inventory_item_gid": payload.inventory_item_gid,
        "location_gid": payload.location_gid,
        "target_quantity": payload.normalized_target_quantity,
        "change_from_quantity": payload.change_from_quantity,
        "mapping": mapping,
        "observation": observation,
        "first_push_confirmation": (
            payload.first_push_confirmation.fingerprint_dict()
            if payload.first_push_confirmation is not None
            else None
        ),
    }


def canonical_preview_fingerprint(payload: InventoryMutationPayload) -> str:
    """Hash all authority/mapping/observation inputs, excluding mutable keys."""

    if not isinstance(payload, InventoryMutationPayload):
        raise TypeError("payload must be InventoryMutationPayload")
    material = freeze_value(_fingerprint_material(payload))
    encoded = json.dumps(to_plain(material), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
