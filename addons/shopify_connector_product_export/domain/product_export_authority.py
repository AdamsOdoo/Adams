"""V1 product/variant field authority and protected-field policy.

This module deliberately contains no Shopify or ORM imports.  It turns an
Odoo observation plus an explicit authority configuration into the small
allowlisted write surface used by the P08 gateways.  Missing optional Odoo
values are omitted, which is important: omission is not an instruction to
clear a merchant-owned value.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from ._support import (
    FORBIDDEN_UPDATE_KEYS,
    PRODUCT_SCALAR_ALLOWLIST,
    PROTECTED_PRODUCT_FIELDS,
    PROTECTED_VARIANT_FIELDS,
    VARIANT_FIELD_ALLOWLIST,
    ProductExportPolicyError,
    ProtectedFieldError,
    fail,
    first,
    freeze,
    freeze_mapping,
    gid,
    mapping,
    money,
    money_equal,
    sequence,
    tags,
    text,
)


class FieldAuthority(str, Enum):
    """Who may author a field in this export intent."""

    ODOO = "odoo"
    SHOPIFY = "shopify"
    PROTECTED = "protected"
    DISABLED = "disabled"


def _authority_map(authority: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if authority is None:
        return {}
    if not isinstance(authority, Mapping):
        fail("invalid_authority", "authority must be an object.")
    nested = authority.get("fields")
    if isinstance(nested, Mapping):
        merged = {key: value for key, value in authority.items() if key != "fields"}
        merged.update(nested)
        return merged
    return authority


def authority_snapshot(authority: Mapping[str, Any] | None) -> Mapping[str, Any]:
    """Return an immutable authority snapshot; omission means deny all writes."""

    if authority is None:
        return freeze_mapping({})
    values = mapping(authority, "authority") or {}
    nested = values.get("fields")
    if nested is not None and not isinstance(nested, Mapping):
        fail("invalid_authority", "authority.fields must be an object.")
    # Resolve every supplied field now so a malformed snapshot cannot be
    # persisted in an intent and interpreted differently by a later worker.
    for field in _authority_map(values):
        if field in {
            "fields", "price_source_of_truth", "price_authority",
            "shopify_export_description_managed", "shopify_export_vendor_managed",
            "shopify_export_product_type_managed", "shopify_export_tags_managed",
            "shopify_export_status_managed",
        }:
            continue
        _authority_value(values, field)
    if "price_source_of_truth" in values:
        source = values["price_source_of_truth"]
        if source not in ("odoo", "odoo_authoritative", "shopify", "shopify_observed", None):
            fail("invalid_authority", "price_source_of_truth is not supported.")
    if "price_authority" in values:
        source = values["price_authority"]
        if source not in ("odoo", "odoo_authoritative", "shopify", "shopify_observed", None):
            fail("invalid_authority", "price_authority is not supported.")
    def normalize(value: Any) -> Any:
        if isinstance(value, FieldAuthority):
            return value.value
        if isinstance(value, Mapping):
            return {key: normalize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [normalize(item) for item in value]
        return value

    return freeze_mapping(normalize(dict(values)))


def _authority_value(authority: Mapping[str, Any] | None, field: str) -> str | None:
    values = _authority_map(authority)
    raw = values.get(field)
    managed_aliases = {
        "status": "shopify_export_status_managed",
        "descriptionHtml": "shopify_export_description_managed",
        "description": "shopify_export_description_managed",
        "description_html": "shopify_export_description_managed",
        "vendor": "shopify_export_vendor_managed",
        "productType": "shopify_export_product_type_managed",
        "product_type": "shopify_export_product_type_managed",
        "tags": "shopify_export_tags_managed",
    }
    if raw is None and managed_aliases.get(field) in values:
        raw = values[managed_aliases[field]]
    if raw is None and field in {"descriptionHtml", "description", "description_html"}:
        raw = first(values, "descriptionHtml", "description", "description_html")
    if isinstance(raw, FieldAuthority):
        return raw.value
    if isinstance(raw, bool):
        return FieldAuthority.ODOO.value if raw else FieldAuthority.DISABLED.value
    if raw is None:
        return None
    if not isinstance(raw, str):
        fail("invalid_authority", f"authority for {field} must be a supported string.")
    try:
        return FieldAuthority(raw).value
    except ValueError as exc:
        raise ProductExportPolicyError("invalid_authority", f"authority for {field} is not supported.") from exc


def _managed(authority: Mapping[str, Any] | None, field: str, *, default: bool = False) -> bool:
    value = _authority_value(authority, field)
    return value == FieldAuthority.ODOO.value or (value is None and default)


def validate_protected_field(field: str, value: Any = None, *, variant: bool = False) -> None:
    """Reject a protected field, including protected nested inventory keys."""

    protected = PROTECTED_VARIANT_FIELDS if variant else FORBIDDEN_UPDATE_KEYS
    if field in protected or field in PROTECTED_PRODUCT_FIELDS or field in PROTECTED_VARIANT_FIELDS:
        raise ProtectedFieldError(
            "protected_field",
            f"protected field {field} is merchant-owned and cannot be authored by product export.",
            details={"field": field, "variant": variant},
        )
    if isinstance(value, Mapping):
        for nested in value:
            if nested in PROTECTED_PRODUCT_FIELDS or nested in PROTECTED_VARIANT_FIELDS:
                raise ProtectedFieldError(
                    "protected_field",
                    f"protected field {field}.{nested} is merchant-owned and cannot be authored by product export.",
                    details={"field": f"{field}.{nested}", "variant": variant},
                )


def validate_export_fields(
    product_fields: Mapping[str, Any] | None = None,
    variant_fields: Iterable[Mapping[str, Any]] = (),
) -> None:
    """Validate an input write surface before any diff or sequence is built."""

    product = mapping(product_fields or {}, "product_fields") or {}
    unknown = set(product) - PRODUCT_SCALAR_ALLOWLIST
    protected = unknown & set(FORBIDDEN_UPDATE_KEYS)
    if protected:
        field = sorted(protected)[0]
        validate_protected_field(field, product[field])
    if unknown:
        fail("unsupported_field", f"product_fields contains unsupported field {sorted(unknown)[0]}.")
    for index, raw in enumerate(variant_fields):
        row = mapping(raw, f"variant_fields[{index}]") or {}
        unknown_variant = set(row) - VARIANT_FIELD_ALLOWLIST
        protected_variant = unknown_variant & set(PROTECTED_VARIANT_FIELDS | FORBIDDEN_UPDATE_KEYS)
        if protected_variant:
            field = sorted(protected_variant)[0]
            validate_protected_field(field, row[field], variant=True)
        if unknown_variant:
            fail("unsupported_field", f"variant_fields[{index}] contains unsupported field {sorted(unknown_variant)[0]}.")
        if "inventoryItem" in row:
            item = mapping(row["inventoryItem"], f"variant_fields[{index}].inventoryItem") or {}
            if set(item) != {"sku"}:
                validate_protected_field(next(iter(set(item) - {"sku"}), "inventoryItem"), item, variant=True)
                fail("unsupported_field", "inventoryItem accepts sku only.")


def _source_value(source: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    return first(source, *names, default=default)


def desired_product_scalars(
    product: Mapping[str, Any],
    *,
    authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the exact V1 scalar payload, with omission preserving Shopify data."""

    source = mapping(product, "product") or {}
    for protected in sorted(set(source) & set(FORBIDDEN_UPDATE_KEYS)):
        validate_protected_field(protected, source[protected])
    validate_export_fields({key: value for key, value in source.items() if key in PRODUCT_SCALAR_ALLOWLIST})
    result: dict[str, Any] = {}

    title = _source_value(source, "title", "name", default="")
    result["title"] = text(title, "title", allow_empty=True, max_length=65_536)

    aliases = {
        "descriptionHtml": ("descriptionHtml", "description_html", "description"),
        "vendor": ("vendor", "brand"),
        "productType": ("productType", "product_type"),
    }
    for field, names in aliases.items():
        value = _source_value(source, *names)
        if value not in (None, ""):
            result[field] = text(value, field, allow_empty=True)
        elif value == "" and _managed(authority, field):
            result[field] = ""

    raw_tags = _source_value(source, "tags", default=None)
    if raw_tags not in (None, "", []):
        result["tags"] = tags(raw_tags)
    elif raw_tags == [] and _managed(authority, "tags"):
        result["tags"] = []

    raw_status = _source_value(source, "status", default=None)
    if raw_status not in (None, "") and _managed(authority, "status"):
        status_map = {"draft": "DRAFT", "active": "ACTIVE", "archived": "ARCHIVED"}
        status_key = str(raw_status).strip().lower()
        if status_key not in status_map:
            fail("invalid_status", "status must be draft, active, or archived.")
        result["status"] = status_map[status_key]
    return result


def _price_authoritative(authority: Mapping[str, Any] | None) -> bool:
    values = _authority_map(authority)
    source = first(values, "price_source_of_truth", "price_authority", default=None)
    if source is None:
        return _managed(authority, "price", default=False)
    return source in ("odoo", "odoo_authoritative", FieldAuthority.ODOO, FieldAuthority.ODOO.value)


def authority_allows_field(authority: Mapping[str, Any] | None, field: str) -> bool:
    """Whether one requested payload field is explicitly Odoo-authoritative."""

    if field in {"price", "compareAtPrice"}:
        return _price_authoritative(authority)
    if field == "inventoryItem":
        return _authority_value(authority, "sku") == FieldAuthority.ODOO.value or _authority_value(authority, field) == FieldAuthority.ODOO.value
    return _authority_value(authority, field) == FieldAuthority.ODOO.value


def validate_authoritative_payload(
    authority: Mapping[str, Any] | None,
    scalar_fields: Mapping[str, Any],
    variant_rows: Sequence[Mapping[str, Any]],
    product_options: Sequence[Mapping[str, Any]] = (),
) -> None:
    """Reject writes that are not explicitly enabled by the authority snapshot."""

    for field in scalar_fields:
        if not authority_allows_field(authority, field):
            fail("authority_required", f"{field} is not explicitly Odoo-authoritative.", details={"field": field})
    for row in variant_rows:
        for field in row:
            if field == "id":
                continue
            authority_field = "sku" if field == "inventoryItem" else field
            if not authority_allows_field(authority, authority_field):
                fail("authority_required", f"{field} is not explicitly Odoo-authoritative.", details={"field": field})
    if product_options and not authority_allows_field(authority, "productOptions"):
        fail("authority_required", "product options require explicit Odoo authority.", details={"field": "productOptions"})


def desired_variant_fields(
    variant: Mapping[str, Any],
    *,
    authority: Mapping[str, Any] | None = None,
    require_id: bool = False,
) -> dict[str, Any]:
    """Return V1-owned fields for one existing or new variant."""

    source = mapping(variant, "variant") or {}
    source_allowlist = {
        "id", "shopify_gid", "variant_gid", "sku", "barcode", "price",
        "compareAtPrice", "compare_at_price", "optionValues", "option_values",
        "inventoryItem",
    }
    unknown_source = set(source) - source_allowlist
    protected_source = unknown_source & set(PROTECTED_VARIANT_FIELDS | FORBIDDEN_UPDATE_KEYS)
    if protected_source:
        field = sorted(protected_source)[0]
        validate_protected_field(field, source[field], variant=True)
    if unknown_source:
        fail("unsupported_field", f"variant contains unsupported field {sorted(unknown_source)[0]}.")
    if "inventoryItem" in source:
        item = mapping(source["inventoryItem"], "variant.inventoryItem") or {}
        if set(item) != {"sku"}:
            bad = next(iter(set(item) - {"sku"}), "inventoryItem")
            validate_protected_field(bad, item.get(bad), variant=True)
            fail("unsupported_field", "variant.inventoryItem accepts sku only.")
    result: dict[str, Any] = {}
    raw_id = _source_value(source, "id", "shopify_gid")
    if raw_id is not None:
        result["id"] = gid(raw_id, "variant.id", kind="ProductVariant")
    elif require_id:
        fail("missing_variant_binding", "An existing variant update requires its Shopify GID.")

    raw_barcode = _source_value(source, "barcode")
    if raw_barcode not in (None, ""):
        result["barcode"] = text(raw_barcode, "variant.barcode", allow_empty=True, max_length=512)
    raw_sku = _source_value(source, "sku")
    if raw_sku not in (None, ""):
        result["inventoryItem"] = {"sku": text(raw_sku, "variant.sku", allow_empty=True, max_length=512)}

    option_values = _source_value(source, "optionValues", "option_values")
    if option_values not in (None, []):
        result["optionValues"] = validate_variant_options(option_values, "variant.optionValues")

    if _price_authoritative(authority):
        raw_price = _source_value(source, "price")
        if raw_price is not None:
            result["price"] = money(raw_price, "variant.price")
        raw_compare = _source_value(source, "compareAtPrice", "compare_at_price")
        if raw_compare not in (None, "", 0, 0.0, "0", "0.00"):
            result["compareAtPrice"] = money(raw_compare, "variant.compareAtPrice")
    return result


def _same(field: str, expected: Any, observed: Any) -> bool:
    if field in {"price", "compareAtPrice"}:
        return money_equal(expected, observed)
    if field == "inventoryItem":
        expected = expected.get("sku") if isinstance(expected, Mapping) else expected
        observed = observed.get("sku") if isinstance(observed, Mapping) else observed
    if field == "tags":
        return list(expected or []) == list(observed or [])
    return expected == observed


@dataclass(frozen=True)
class FieldDecision:
    field: str
    authority: FieldAuthority
    requested: Any
    observed: Any
    changed: bool
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "authority", FieldAuthority(self.authority))
        object.__setattr__(self, "requested", freeze(self.requested))
        object.__setattr__(self, "observed", freeze(self.observed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "field": self.field,
            "authority": self.authority.value,
            "requested": self.requested,
            "observed": self.observed,
            "changed": self.changed,
            "reason": self.reason,
        }


def field_authority_diff(
    desired: Mapping[str, Any],
    observed: Mapping[str, Any] | None = None,
    *,
    authority: Mapping[str, Any] | None = None,
) -> tuple[FieldDecision, ...]:
    """Describe only Odoo-authoritative differences; Shopify fields are disclosed."""

    desired_map = mapping(desired, "desired") or {}
    observed_map = mapping(observed or {}, "observed") or {}
    decisions: list[FieldDecision] = []
    for field in sorted(set(desired_map) | set(observed_map)):
        if field in FORBIDDEN_UPDATE_KEYS:
            validate_protected_field(field, desired_map.get(field))
        raw_auth = _authority_value(authority, field)
        auth = FieldAuthority.SHOPIFY if raw_auth is None else FieldAuthority(raw_auth)
        requested = desired_map.get(field)
        current = observed_map.get(field)
        changed = field in desired_map and not _same(field, requested, current)
        reason = "odoo_authoritative_change" if changed and auth is FieldAuthority.ODOO else "merchant_owned_or_unchanged"
        decisions.append(FieldDecision(field, auth, requested, current, changed and auth is FieldAuthority.ODOO, reason))
    return tuple(decisions)


def eligible_scalar_payload(
    desired: Mapping[str, Any],
    *,
    observed: Mapping[str, Any] | None = None,
    authority: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Filter a reviewed diff to the fields allowed in productUpdate."""

    result: dict[str, Any] = {}
    for decision in field_authority_diff(desired, observed or {}, authority=authority):
        if decision.changed:
            result[decision.field] = decision.requested
    validate_export_fields(result)
    return result


def validate_variant_fields(variants: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    result: list[dict[str, Any]] = []
    for index, variant in enumerate(variants):
        row = desired_variant_fields(variant, require_id=False)
        validate_export_fields({}, (row,))
        result.append(row)
    return tuple(result)


def validate_options(value: Any, name: str = "productOptions") -> list[dict[str, Any]]:
    rows = sequence(value, name, maximum=3)
    result: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        row = mapping(raw, f"{name}[{index}]") or {}
        if set(row) != {"name", "values"}:
            fail("invalid_options", f"{name}[{index}] must contain name and values only.")
        option_name = text(row["name"], f"{name}[{index}].name", max_length=256)
        values = sequence(row["values"], f"{name}[{index}].values", maximum=100)
        if not values:
            fail("invalid_options", f"{name}[{index}].values cannot be empty.")
        normalized_values: list[dict[str, str]] = []
        for item in values:
            if isinstance(item, str):
                item_name = item
            else:
                item_name = first(mapping(item, "option value") or {}, "name")
            normalized_values.append({"name": text(item_name, "option value name", max_length=256)})
        result.append({"name": option_name, "values": normalized_values})
    return result


def validate_variant_options(value: Any, name: str = "variant.optionValues") -> list[dict[str, str]]:
    rows = sequence(value, name, maximum=3)
    result: list[dict[str, str]] = []
    for index, raw in enumerate(rows):
        row = mapping(raw, f"{name}[{index}]") or {}
        if set(row) != {"optionName", "name"}:
            fail("invalid_variant_options", f"{name}[{index}] must contain optionName and name only.")
        result.append({
            "optionName": text(row["optionName"], f"{name}[{index}].optionName", max_length=256),
            "name": text(row["name"], f"{name}[{index}].name", max_length=256),
        })
    return result


def validate_option_identity(
    desired: Iterable[Mapping[str, Any]],
    observed: Iterable[Mapping[str, Any]],
) -> None:
    """Reject option-set divergence; option position is part of variant identity."""

    wanted = validate_options(list(desired), "desired_options")
    observed_rows = []
    for row in observed:
        if isinstance(row, Mapping) and "optionValues" in row and "values" not in row:
            values = row.get("optionValues") or []
            observed_rows.append({"name": row.get("name"), "values": [
                item.get("name") if isinstance(item, Mapping) else item for item in values
            ]})
        else:
            observed_rows.append(row)
    current = validate_options(observed_rows, "observed_options")
    if wanted != current:
        raise ProductExportPolicyError(
            "product_options_conflict",
            "Shopify product options diverged from the reviewed export options.",
            details={"desired": wanted, "observed": current},
        )


__all__ = [
    "FieldAuthority", "FieldDecision", "authority_allows_field", "authority_snapshot",
    "validate_authoritative_payload",
    "desired_product_scalars", "desired_variant_fields",
    "eligible_scalar_payload", "field_authority_diff", "validate_export_fields",
    "validate_option_identity", "validate_options", "validate_protected_field", "validate_variant_fields",
    "validate_variant_options",
]
