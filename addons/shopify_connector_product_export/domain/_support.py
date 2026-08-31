"""Small dependency-free helpers shared by the P13 policy modules."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from types import MappingProxyType
from typing import Any

SHOPIFY_API_VERSION = "2026-07"
PREVIEW_VALIDITY_HOURS = 24
MAX_PRODUCT_OPTIONS = 3
MAX_EXPORT_VARIANTS = 100
MAX_MEDIA_ITEMS = 100

PRODUCT_SCALAR_ALLOWLIST = frozenset(
    {"title", "descriptionHtml", "vendor", "productType", "tags", "status"}
)
VARIANT_FIELD_ALLOWLIST = frozenset(
    {"id", "price", "compareAtPrice", "barcode", "inventoryItem", "optionValues"}
)
PROTECTED_PRODUCT_FIELDS = frozenset(
    {
        "collections", "collectionsToJoin", "collectionsToLeave", "metafields",
        "files", "media", "variants", "productOptions", "inventoryQuantities",
        "quantityAdjustments", "mediaId", "mediaSrc",
    }
)
PROTECTED_VARIANT_FIELDS = frozenset(
    {"tracked", "inventoryQuantities", "quantityAdjustments", "inventoryItemId"}
)
FORBIDDEN_UPDATE_KEYS = PROTECTED_PRODUCT_FIELDS | PROTECTED_VARIANT_FIELDS

PRODUCT_CREATE_OPERATION = "product_export.create"
PRODUCT_UPDATE_OPERATION = "product_export.update"
VARIANTS_UPDATE_OPERATION = "product_export.variants_update"
VARIANTS_CREATE_OPERATION = "product_export.variants_create"
BINDING_NAMESPACE_OPERATION = "product_export.binding_namespace"
BINDING_DEFINITION_READ_OPERATION = "product_export.binding_definition.read"
MEDIA_STAGE_OPERATION = "product_export.media_stage"
MEDIA_FILE_CREATE_OPERATION = "product_export.media_file_create"
MEDIA_ASSOCIATE_OPERATION = "product_export.media_associate"

STEP_BINDING_NAMESPACE = "product_export_binding_namespace"
STEP_BINDING_NAMESPACE_DECISION = "product_export_binding_namespace_decision"
STEP_BINDING_NAMESPACE_READBACK = "product_export_binding_namespace_readback"
STEP_CREATE = "product_export_create"
STEP_UPDATE = "product_export_update"
STEP_VARIANTS_UPDATE = "product_export_variants_update"
STEP_VARIANTS_CREATE = "product_export_variants_create"
STEP_MEDIA_STAGE = "product_export_media_stage"
STEP_MEDIA_UPLOAD = "product_export_media_upload"
STEP_MEDIA_FILE_CREATE = "product_export_media_file_create"
STEP_MEDIA_POLL = "product_export_media_poll"
STEP_MEDIA_ASSOCIATE = "product_export_media_associate"

_GID = re.compile(r"^gid://shopify/[A-Za-z][A-Za-z0-9_]*/[1-9][0-9]*$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9_.:-]{0,127}$")


class ProductExportPolicyError(ValueError):
    """A value cannot safely authorize a product export."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        if not isinstance(code, str) or not _TOKEN.fullmatch(code):
            raise ValueError("policy error code must be a safe token")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("policy error message must be non-empty")
        self.code, self.message = code, message[:4096]
        self.details = freeze_mapping(details or {})
        super().__init__(self.message)


class ProtectedFieldError(ProductExportPolicyError):
    """A protected Shopify field was presented as an export write."""


class DuplicateRiskError(ProductExportPolicyError):
    """A create could produce a second remote entity."""


class BindingConflictError(ProductExportPolicyError):
    """Local and remote identity evidence contradicts itself."""


class StalePreviewError(ProductExportPolicyError):
    """A preview no longer describes the state to be written."""

    @property
    def reason(self) -> str:
        return str(self.details.get("reason") or "stale_preview")


def fail(code: str, message: str, *, details: Mapping[str, Any] | None = None) -> None:
    raise ProductExportPolicyError(code, message, details=details)


def freeze(value: Any) -> Any:
    """Copy JSON-shaped values into immutable values."""
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) or not key for key in value):
            fail("invalid_json", "Policy mapping keys must be non-empty strings.")
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze(item) for item in value)
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            fail("invalid_json", "Policy values cannot contain NaN or infinity.")
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    fail("invalid_json", "Policy values must be JSON-shaped.")


def plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            fail("invalid_json", "Policy values cannot contain NaN or infinity.")
        return value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    fail("invalid_json", "Policy values must be JSON-shaped.")


def freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        fail("invalid_mapping", "Expected an object.")
    frozen = freeze(dict(value))
    if not isinstance(frozen, Mapping):
        fail("invalid_mapping", "Expected an object.")
    return frozen


def to_plain(value: Any) -> Any:
    return plain(value)


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(plain(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ProductExportPolicyError("invalid_json", "Policy values could not be canonicalized.") from exc


def canonical_fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        fail("invalid_integer", f"{name} must be a positive integer.")
    return value


def non_negative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        fail("invalid_integer", f"{name} must be a non-negative integer.")
    return value


def text(value: Any, name: str, *, allow_empty: bool = False, max_length: int = 65536) -> str:
    if not isinstance(value, str) or len(value) > max_length or (not allow_empty and not value.strip()):
        fail("invalid_text", f"{name} must be a bounded{' non-empty' if not allow_empty else ''} string.")
    return value


def gid(value: Any, name: str, *, kind: str | None = None) -> str:
    value = text(value, name, max_length=256)
    if not _GID.fullmatch(value) or (kind and f"/shopify/{kind}/" not in value):
        fail("invalid_gid", f"{name} must be a canonical Shopify GID.")
    return value


def mapping(value: Any, name: str, *, optional: bool = False) -> Mapping[str, Any] | None:
    if value is None and optional:
        return None
    if not isinstance(value, Mapping):
        fail("invalid_mapping", f"{name} must be an object.")
    return value


def sequence(value: Any, name: str, *, maximum: int = MAX_EXPORT_VARIANTS) -> list[Any]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        fail("invalid_sequence", f"{name} must be a bounded sequence.")
    if len(value) > maximum:
        fail("input_too_large", f"{name} exceeds its safety bound.")
    return list(value)


def first(value: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in value:
            return value[name]
    return default


def enum_value(value: Any, enum_type: type, name: str) -> str:
    try:
        return (value if isinstance(value, enum_type) else enum_type(value)).value
    except (TypeError, ValueError) as exc:
        raise ProductExportPolicyError("invalid_value", f"{name} is not supported.") from exc


def money(value: Any, name: str = "money") -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        fail("invalid_money", f"{name} must be a decimal value.")
    try:
        result = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError) as exc:
        raise ProductExportPolicyError("invalid_money", f"{name} is not a decimal value.") from exc
    if not result.is_finite():
        fail("invalid_money", f"{name} must be finite.")
    return format(result, ".2f")


def money_equal(left: Any, right: Any) -> bool:
    try:
        return Decimal(str(left or "0")).quantize(Decimal("0.01")) == Decimal(str(right or "0")).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return False


def tags(value: Any, name: str = "tags") -> list[str]:
    if value in (None, False):
        return []
    if isinstance(value, str):
        value = value.split(",")
    values = sequence(value, name, maximum=1_000)
    result = []
    for item in values:
        if not isinstance(item, str) or not item.strip() or len(item) > 256:
            fail("invalid_tags", f"{name} must contain bounded non-empty strings.")
        result.append(item.strip())
    return result


def utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() != timedelta(0):
        fail("invalid_datetime", f"{name} must be timezone-aware UTC.")
    return value


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        return result if result.tzinfo else result.replace(tzinfo=timezone.utc)
    return None


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "BINDING_NAMESPACE_OPERATION", "FORBIDDEN_UPDATE_KEYS", "MAX_EXPORT_VARIANTS",
    "MAX_MEDIA_ITEMS", "MAX_PRODUCT_OPTIONS", "MEDIA_ASSOCIATE_OPERATION",
    "MEDIA_FILE_CREATE_OPERATION", "MEDIA_STAGE_OPERATION", "PREVIEW_VALIDITY_HOURS",
    "PRODUCT_CREATE_OPERATION", "PRODUCT_SCALAR_ALLOWLIST", "PRODUCT_UPDATE_OPERATION",
    "PROTECTED_PRODUCT_FIELDS", "PROTECTED_VARIANT_FIELDS", "SHOPIFY_API_VERSION",
    "STEP_BINDING_NAMESPACE", "STEP_CREATE", "STEP_MEDIA_ASSOCIATE", "STEP_MEDIA_FILE_CREATE",
    "STEP_MEDIA_POLL", "STEP_MEDIA_STAGE", "STEP_MEDIA_UPLOAD", "STEP_UPDATE",
    "STEP_VARIANTS_CREATE", "STEP_VARIANTS_UPDATE", "VARIANT_FIELD_ALLOWLIST",
    "VARIANTS_CREATE_OPERATION", "VARIANTS_UPDATE_OPERATION", "BindingConflictError",
    "DuplicateRiskError", "ProductExportPolicyError", "ProtectedFieldError", "StalePreviewError",
    "canonical_fingerprint", "canonical_json", "enum_value", "fail", "first", "freeze",
    "freeze_mapping", "gid", "mapping", "money", "money_equal", "non_negative_int", "parse_datetime",
    "plain", "positive_int", "sequence", "sha256_text", "tags", "text", "to_plain", "utc",
]
