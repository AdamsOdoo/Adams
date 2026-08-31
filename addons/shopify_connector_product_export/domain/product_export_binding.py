"""Binding, duplicate-risk, and strict variant-identity policy for P13."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._support import (
    BindingConflictError,
    DuplicateRiskError,
    ProductExportPolicyError,
    fail,
    first,
    freeze,
    freeze_mapping,
    gid,
    mapping,
    sequence,
    text,
)
from .product_export_authority import desired_variant_fields, validate_variant_fields


class ExportPath(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class BindingDecision:
    path: ExportPath
    reason_code: str
    product_gid: str | None = None
    binding_present: bool = False
    requires_review: bool = False
    evidence: Mapping[str, Any] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", ExportPath(self.path))
        if self.product_gid is not None:
            object.__setattr__(self, "product_gid", gid(self.product_gid, "product_gid", kind="Product"))
        object.__setattr__(self, "evidence", freeze_mapping(dict(self.evidence) if isinstance(self.evidence, Mapping) else {}))

    @property
    def blocked(self) -> bool:
        return self.path is ExportPath.BLOCKED

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path.value,
            "reason_code": self.reason_code,
            "product_gid": self.product_gid,
            "binding_present": self.binding_present,
            "requires_review": self.requires_review,
            "evidence": dict(self.evidence),
        }


def _gid_from_binding(binding: Mapping[str, Any] | None) -> str | None:
    if not isinstance(binding, Mapping):
        return None
    value = first(binding, "product_gid", "shopify_gid", "gid", default=None)
    if value in (None, ""):
        return None
    return gid(value, "binding.product_gid", kind="Product")


def _remote_id(remote_product: Mapping[str, Any] | None) -> str | None:
    if not isinstance(remote_product, Mapping):
        return None
    value = first(remote_product, "id", "product_gid", "gid", default=None)
    if value in (None, ""):
        return None
    return gid(value, "remote_product.id", kind="Product")


def _has_rows(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, Mapping):
        for key in ("nodes", "items", "matches", "products"):
            if key in value:
                return _has_rows(value[key])
        return bool(value)
    if isinstance(value, (str, bytes)):
        return bool(value)
    try:
        return bool(len(value))
    except TypeError:
        return bool(value)


def decide_create_or_update(
    *,
    store_id: str,
    template_id: str | int,
    binding: Mapping[str, Any] | None = None,
    remote_product: Mapping[str, Any] | None = None,
    remote_by_custom_id: Any = None,
    remote_by_sku: Any = None,
) -> BindingDecision:
    """Choose exactly one V1 path from binding and fresh identity evidence.

    A local binding is authoritative for updates.  If it points at a product
    that a fresh read cannot find, the safe result is review—not a new create.
    A no-binding create is allowed only when all custom-id and SKU collision
    searches are empty.
    """

    store = text(store_id, "store_id", max_length=256)
    if isinstance(template_id, bool) or not isinstance(template_id, (str, int)):
        fail("invalid_template_id", "template_id must be a string or strict integer.")
    template = text(str(template_id), "template_id", max_length=256)
    binding_gid = _gid_from_binding(binding)
    remote_gid = _remote_id(remote_product)
    evidence = {"store_id": store, "template_id": template}

    if binding_gid:
        evidence["bound_product_gid"] = binding_gid
        if remote_product is None:
            return BindingDecision(ExportPath.BLOCKED, "bound_product_missing_remotely", binding_gid, True, True, evidence)
        if remote_gid is None:
            return BindingDecision(ExportPath.BLOCKED, "bound_product_identity_unreadable", binding_gid, True, True, evidence)
        if remote_gid != binding_gid:
            evidence["observed_product_gid"] = remote_gid
            return BindingDecision(ExportPath.BLOCKED, "binding_conflict", binding_gid, True, True, evidence)
        return BindingDecision(ExportPath.UPDATE, "bound_product", binding_gid, True, False, evidence)

    if remote_product is not None:
        if remote_gid:
            evidence["observed_product_gid"] = remote_gid
        return BindingDecision(ExportPath.BLOCKED, "remote_product_without_binding", remote_gid, False, True, evidence)
    if _has_rows(remote_by_custom_id):
        return BindingDecision(ExportPath.BLOCKED, "custom_id_duplicate_risk", None, False, True, {**evidence, "matches": remote_by_custom_id})
    if _has_rows(remote_by_sku):
        return BindingDecision(ExportPath.BLOCKED, "sku_duplicate_risk", None, False, True, {**evidence, "matches": remote_by_sku})
    return BindingDecision(ExportPath.CREATE, "no_binding_or_identity_collision", None, False, False, evidence)


def choose_export_path(**kwargs: Any) -> BindingDecision:
    return decide_create_or_update(**kwargs)


def decide_export_path(**kwargs: Any) -> BindingDecision:
    return decide_create_or_update(**kwargs)


@dataclass(frozen=True)
class VariantChange:
    variant_gid: str
    fields: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "variant_gid", gid(self.variant_gid, "variant_gid", kind="ProductVariant"))
        object.__setattr__(self, "fields", freeze_mapping(dict(mapping(self.fields, "variant.fields") or {})))

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.variant_gid, **dict(self.fields)}


@dataclass(frozen=True)
class VariantCreate:
    fields: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", freeze_mapping(dict(mapping(self.fields, "variant.fields") or {})))

    @property
    def sku(self) -> str:
        inventory = self.fields.get("inventoryItem")
        if isinstance(inventory, Mapping):
            value = inventory.get("sku")
        else:
            value = self.fields.get("sku")
        if value in (None, ""):
            return ""
        return text(value, "variant.sku", allow_empty=True, max_length=512).strip()

    def as_dict(self) -> dict[str, Any]:
        return dict(self.fields)


@dataclass(frozen=True)
class VariantPlan:
    updates: tuple[VariantChange, ...]
    creates: tuple[VariantCreate, ...]
    unowned_remote_variant_gids: tuple[str, ...] = ()
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        if isinstance(self.updates, (str, bytes, Mapping)) or not isinstance(self.updates, (list, tuple)):
            fail("invalid_variant_plan", "variant updates must be a sequence.")
        if isinstance(self.creates, (str, bytes, Mapping)) or not isinstance(self.creates, (list, tuple)):
            fail("invalid_variant_plan", "variant creates must be a sequence.")
        if isinstance(self.unowned_remote_variant_gids, (str, bytes, Mapping)) or not isinstance(self.unowned_remote_variant_gids, (list, tuple)):
            fail("invalid_variant_plan", "unowned variant identities must be a sequence.")
        if not isinstance(self.updates, tuple):
            object.__setattr__(self, "updates", tuple(self.updates))
        if not isinstance(self.creates, tuple):
            object.__setattr__(self, "creates", tuple(self.creates))
        if any(not isinstance(row, VariantChange) for row in self.updates):
            fail("invalid_variant_plan", "variant updates must be VariantChange values.")
        if any(not isinstance(row, VariantCreate) for row in self.creates):
            fail("invalid_variant_plan", "variant creates must be VariantCreate values.")
        normalized_unowned = tuple(gid(value, "unowned_remote_variant_gid", kind="ProductVariant") for value in self.unowned_remote_variant_gids)
        object.__setattr__(self, "unowned_remote_variant_gids", normalized_unowned)
        if self.blocked_reason is not None:
            object.__setattr__(self, "blocked_reason", text(self.blocked_reason, "blocked_reason", max_length=256))

    @property
    def blocked(self) -> bool:
        return self.blocked_reason is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "updates": [row.as_dict() for row in self.updates],
            "creates": [row.as_dict() for row in self.creates],
            "unowned_remote_variant_gids": list(self.unowned_remote_variant_gids),
            "blocked_reason": self.blocked_reason,
        }


def _variant_id(value: Mapping[str, Any]) -> str | None:
    raw = first(value, "id", "shopify_gid", "variant_gid", default=None)
    if raw in (None, ""):
        return None
    return gid(raw, "variant.id", kind="ProductVariant")


def _variant_sku(value: Mapping[str, Any]) -> str:
    raw = first(value, "sku", default=None)
    if raw not in (None, ""):
        return text(raw, "variant.sku", allow_empty=True, max_length=512).strip()
    inventory = value.get("inventoryItem")
    if isinstance(inventory, Mapping):
        raw = inventory.get("sku")
        if raw not in (None, ""):
            return text(raw, "variant.inventoryItem.sku", allow_empty=True, max_length=512).strip()
    return ""


def _remote_variants(remote_variants: Iterable[Mapping[str, Any]]) -> tuple[Mapping[str, Any], ...]:
    rows = sequence(list(remote_variants), "remote_variants", maximum=100)
    result: list[Mapping[str, Any]] = []
    for index, row in enumerate(rows):
        result.append(mapping(row, f"remote_variants[{index}]") or {})
    return tuple(result)


def validate_create_variant_identities(
    variants: Iterable[Mapping[str, Any]],
    *,
    remote_variants: Iterable[Mapping[str, Any]] = (),
) -> None:
    """Require a SKU for existing-product creates and reject collisions."""

    local = [mapping(row, "variant") or {} for row in variants]
    remotes = _remote_variants(remote_variants)
    local_skus: list[str] = []
    remote_skus = {_variant_sku(row) for row in remotes if _variant_sku(row)}
    for index, row in enumerate(local):
        sku = _variant_sku(row)
        if not sku:
            raise DuplicateRiskError("missing_variant_sku", "A new variant on an existing product requires a SKU to avoid duplicate identity.", details={"index": index})
        if sku in local_skus or sku in remote_skus:
            raise DuplicateRiskError("duplicate_variant_sku", "duplicate variant SKU is already present on the product.", details={"sku": sku, "index": index})
        local_skus.append(sku)


def validate_product_create_variant_identities(variants: Iterable[Mapping[str, Any]]) -> None:
    """Require a stable SKU/barcode and uniqueness on a new product create."""

    seen: dict[tuple[str, str], int] = {}
    for index, raw in enumerate(variants):
        row = mapping(raw, "create_variant") or {}
        sku = _variant_sku(row)
        raw_barcode = first(row, "barcode", default="")
        barcode = "" if raw_barcode in (None, "") else text(raw_barcode, "variant.barcode", allow_empty=True, max_length=512).strip()
        if not sku and not barcode:
            raise DuplicateRiskError(
                "missing_variant_identity",
                "A new product variant requires a SKU or barcode to avoid duplicate identity.",
                details={"index": index},
            )
        for label, value in (("sku", sku), ("barcode", barcode)):
            if value:
                key = (label, value)
                if key in seen:
                    raise DuplicateRiskError(
                        "duplicate_variant_identity",
                        f"duplicate variant {label} would make product create ambiguous.",
                        details={"field": label, "value": value, "first_index": seen[key], "index": index},
                    )
                seen[key] = index


def plan_variant_operations(
    local_variants: Iterable[Mapping[str, Any]],
    *,
    remote_variants: Iterable[Mapping[str, Any]] = (),
    authority: Mapping[str, Any] | None = None,
    existing_product: bool = True,
) -> VariantPlan:
    """Plan strict-ID updates and SKU-required creates without fuzzy matching."""

    local = [mapping(row, "local_variant") or {} for row in local_variants]
    remote = _remote_variants(remote_variants)
    remote_variant_ids = [_variant_id(row) for row in remote]
    present_remote_ids = [value for value in remote_variant_ids if value is not None]
    if len(present_remote_ids) != len(set(present_remote_ids)):
        return VariantPlan((), (), tuple(sorted(set(present_remote_ids))), "duplicate_remote_variant_identity")
    by_id = {
        variant_id: row
        for variant_id, row in zip(remote_variant_ids, remote)
        if variant_id is not None
    }
    remote_ids = set(by_id)
    updates: list[VariantChange] = []
    creates: list[VariantCreate] = []
    bound_ids: set[str] = set()
    for index, row in enumerate(local):
        variant_gid = _variant_id(row)
        if variant_gid:
            if variant_gid in bound_ids:
                return VariantPlan((), (), tuple(sorted(remote_ids - bound_ids)), "duplicate_local_variant_binding")
            bound_ids.add(variant_gid)
            if variant_gid not in by_id:
                return VariantPlan((), (), tuple(sorted(remote_ids - bound_ids)), "bound_variant_missing_remotely")
            fields = desired_variant_fields(row, authority=authority, require_id=True)
            fields.pop("id", None)
            if fields:
                updates.append(VariantChange(variant_gid, fields))
            continue
        fields = desired_variant_fields(row, authority=authority, require_id=False)
        creates.append(VariantCreate(fields))
    if creates:
        if existing_product:
            validate_create_variant_identities((item.as_dict() for item in creates), remote_variants=remote)
        else:
            validate_product_create_variant_identities((item.as_dict() for item in creates))
    unowned = tuple(sorted(remote_ids - bound_ids))
    return VariantPlan(tuple(updates), tuple(creates), unowned, None)


__all__ = [
    "BindingDecision", "ExportPath", "VariantChange", "VariantCreate", "VariantPlan",
    "choose_export_path", "decide_create_or_update", "decide_export_path",
    "plan_variant_operations", "validate_create_variant_identities",
    "validate_product_create_variant_identities",
]
