"""Immutable, server-derived product-export payloads and sequences.

This module owns validation and fingerprint construction only.  It does not
send requests, read Odoo, persist intents, or import a concrete gateway.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ..domain._support import (
    fail,
    first,
    freeze_mapping,
    gid,
    mapping,
    parse_datetime,
    text,
    utc,
)
from ..domain.product_export_authority import (
    authority_snapshot,
    validate_export_fields,
    validate_authoritative_payload,
    validate_options,
)
from ..domain.product_export_binding import (
    ExportPath,
    VariantChange,
    VariantCreate,
    VariantPlan,
    validate_create_variant_identities,
    validate_product_create_variant_identities,
)
from ..domain.product_export_sequence import (
    ExportSequence,
    MediaCandidate,
    intent_fingerprint,
    plan_export_sequence,
    scope_key,
)
from ..domain.product_export_readback import BindingNamespaceReadEvidence


def _date(value: Any, name: str) -> datetime | None:
    if value is None:
        return None
    result = parse_datetime(value)
    if result is None:
        fail("invalid_datetime", f"{name} must be an ISO-8601 timestamp.")
    return utc(result, name)


def _as_candidate(value: Any, index: int) -> MediaCandidate:
    if isinstance(value, MediaCandidate):
        return value
    row = mapping(value, f"media[{index}]") or {}
    return MediaCandidate(
        filename=first(row, "filename", "name", default=""),
        checksum=first(row, "checksum", "sha256", "content_hash", default=""),
        alt=first(row, "alt", "alt_text", default=""),
        mime_type=first(row, "mime_type", "mimeType", default="image/png"),
        source_key=first(row, "source_key", "id", default=None),
    )


def _row_sequence(value: Any, name: str, *, maximum: int = 100) -> tuple[Mapping[str, Any], ...]:
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Sequence):
        fail("invalid_sequence", f"{name} must be a bounded sequence of objects.")
    if len(value) > maximum:
        fail("input_too_large", f"{name} exceeds its safety bound.")
    return tuple(mapping(row, f"{name}[{index}]") or {} for index, row in enumerate(value))


@dataclass(frozen=True)
class ProductExportPayload:
    """Immutable product-export intent handed to a future runtime adapter."""

    store_id: str
    store_identity: str
    connection_generation: int
    template_id: str
    path: ExportPath
    product_gid: str | None
    scalar_fields: Mapping[str, Any] = field(default_factory=dict)
    variant_updates: tuple[Mapping[str, Any], ...] = ()
    variant_creates: tuple[Mapping[str, Any], ...] = ()
    product_options: tuple[Mapping[str, Any], ...] = ()
    media: tuple[MediaCandidate, ...] = ()
    media_source_of_truth: str | None = None
    binding_namespace_ready: bool = False
    binding_namespace_evidence: BindingNamespaceReadEvidence | None = None
    preconditions: Mapping[str, Any] = field(default_factory=dict)
    source_write_date: datetime | None = None
    remote_updated_at: datetime | None = None
    scope: str = ""
    fingerprint: str = ""
    authority: Mapping[str, Any] = field(default_factory=dict)
    variant_blocked_reason: str | None = None
    unowned_remote_variant_gids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "store_id", text(self.store_id, "store_id", max_length=256))
        object.__setattr__(self, "store_identity", text(self.store_identity, "store_identity", max_length=512))
        if isinstance(self.connection_generation, bool) or not isinstance(self.connection_generation, int) or self.connection_generation < 0:
            fail("invalid_generation", "connection_generation must be a non-negative integer.")
        if isinstance(self.template_id, bool) or not isinstance(self.template_id, (str, int)):
            fail("invalid_template_id", "template_id must be a string or strict integer.")
        object.__setattr__(self, "template_id", text(str(self.template_id), "template_id", max_length=256))
        object.__setattr__(self, "path", ExportPath(self.path))
        if self.product_gid is not None:
            object.__setattr__(self, "product_gid", gid(self.product_gid, "product_gid", kind="Product"))

        scalars = dict(freeze_mapping(dict(mapping(self.scalar_fields, "scalar_fields") or {})))
        validate_export_fields(scalars)
        object.__setattr__(self, "scalar_fields", freeze_mapping(scalars))
        updates = tuple(freeze_mapping(dict(row)) for row in _row_sequence(self.variant_updates, "variant_updates"))
        creates = tuple(freeze_mapping(dict(row)) for row in _row_sequence(self.variant_creates, "variant_creates"))
        validate_export_fields({}, updates + creates)
        if self.path is ExportPath.UPDATE:
            missing = [index for index, row in enumerate(updates) if not row.get("id")]
            if missing:
                fail("missing_variant_binding", "Existing variant updates require canonical variant IDs.", details={"indexes": missing})
            if creates:
                validate_create_variant_identities(creates)
        if self.path is ExportPath.CREATE:
            if updates:
                fail("invalid_create_variants", "Product create cannot carry existing-variant updates.")
            bound = [index for index, row in enumerate(creates) if row.get("id")]
            if bound:
                fail("unexpected_variant_binding", "Product create variants cannot carry existing Shopify IDs.", details={"indexes": bound})
            if creates:
                validate_product_create_variant_identities(creates)
        object.__setattr__(self, "variant_updates", updates)
        object.__setattr__(self, "variant_creates", creates)

        options = tuple(freeze_mapping(dict(row)) for row in _row_sequence(self.product_options, "product_options", maximum=3))
        if options:
            validate_options(options)
        object.__setattr__(self, "product_options", options)
        candidates = tuple(_as_candidate(row, index) for index, row in enumerate(self.media))
        if len(candidates) > 100:
            fail("input_too_large", "media exceeds its safety bound.")
        object.__setattr__(self, "media", candidates)
        if self.media_source_of_truth is not None:
            object.__setattr__(self, "media_source_of_truth", text(self.media_source_of_truth, "media_source_of_truth", max_length=64))
        if not isinstance(self.binding_namespace_ready, bool):
            fail("invalid_boolean", "binding_namespace_ready must be a strict boolean.")
        namespace_evidence = BindingNamespaceReadEvidence.from_value(self.binding_namespace_evidence)
        if self.binding_namespace_ready and namespace_evidence is None:
            fail("binding_namespace_evidence_required", "Binding namespace readiness requires server-attested read evidence.")
        if namespace_evidence is not None:
            if namespace_evidence.store_identity != self.store_identity:
                fail("binding_namespace_scope_mismatch", "Binding namespace evidence is for another Shopify store.")
            if namespace_evidence.connection_generation != self.connection_generation:
                fail("stale_binding_evidence", "Binding namespace evidence is for another connection generation.")
            object.__setattr__(self, "binding_namespace_ready", True)
        object.__setattr__(self, "binding_namespace_evidence", namespace_evidence)
        authority_values = authority_snapshot(self.authority)
        validate_authoritative_payload(authority_values, scalars, updates + creates, options)
        object.__setattr__(self, "authority", authority_values)
        if self.variant_blocked_reason is not None:
            object.__setattr__(self, "variant_blocked_reason", text(self.variant_blocked_reason, "variant_blocked_reason", max_length=256))
        normalized_unowned = tuple(gid(value, "unowned_remote_variant_gid", kind="ProductVariant") for value in self.unowned_remote_variant_gids)
        object.__setattr__(self, "unowned_remote_variant_gids", normalized_unowned)
        object.__setattr__(self, "preconditions", freeze_mapping(dict(mapping(self.preconditions, "preconditions") or {})))
        source_date = _date(self.source_write_date, "source_write_date")
        remote_date = _date(self.remote_updated_at, "remote_updated_at")
        if self.path in {ExportPath.CREATE, ExportPath.UPDATE} and source_date is None:
            fail("missing_freshness", "Product export requires a source write timestamp from the reviewed preview.")
        if self.path is ExportPath.UPDATE and remote_date is None:
            fail("missing_freshness", "Product update requires the observed Shopify updated timestamp from the reviewed preview.")
        object.__setattr__(self, "source_write_date", source_date)
        object.__setattr__(self, "remote_updated_at", remote_date)

        expected_scope = scope_key(self.store_id, self.product_gid, self.template_id)
        if self.scope and self.scope != expected_scope:
            fail("invalid_scope", "scope is server-derived and does not match this payload.")
        object.__setattr__(self, "scope", expected_scope)
        computed = intent_fingerprint(
            store_id=self.store_id,
            connection_generation=self.connection_generation,
            operation="product_export",
            target={"product_gid": self.product_gid, "template_id": self.template_id},
            business_values=self.business_values,
            preconditions=self.preconditions,
            scope=expected_scope,
        )
        if self.fingerprint:
            if len(self.fingerprint) != 64 or any(char not in "0123456789abcdef" for char in self.fingerprint):
                fail("invalid_fingerprint", "fingerprint must be a lowercase SHA-256 digest.")
            if self.fingerprint != computed:
                fail("stale_preview", "fingerprint does not match server-derived business intent.")
        object.__setattr__(self, "fingerprint", computed)
        if self.path is ExportPath.UPDATE and self.product_gid is None:
            fail("missing_product_binding", "update payloads require a canonical product GID.")
        if self.path is ExportPath.CREATE and self.product_gid is not None:
            fail("unexpected_product_binding", "create payloads cannot carry a product GID.")

    @property
    def business_values(self) -> dict[str, Any]:
        return {
            "template_id": self.template_id,
            "product_gid": self.product_gid,
            "path": self.path.value,
            "scalar_fields": dict(self.scalar_fields),
            "variant_updates": [dict(row) for row in self.variant_updates],
            "variant_creates": [dict(row) for row in self.variant_creates],
            "product_options": [dict(row) for row in self.product_options],
            "media": [row.as_dict() for row in self.media],
            "media_source_of_truth": self.media_source_of_truth,
            "binding_namespace_ready": self.binding_namespace_ready,
            "binding_namespace_evidence": self.binding_namespace_evidence.as_dict() if self.binding_namespace_evidence else None,
            "authority": dict(self.authority),
            "variant_blocked_reason": self.variant_blocked_reason,
            "unowned_remote_variant_gids": list(self.unowned_remote_variant_gids),
            "source_write_date": self.source_write_date.isoformat() if self.source_write_date else None,
            "remote_updated_at": self.remote_updated_at.isoformat() if self.remote_updated_at else None,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.business_values,
            "store_id": self.store_id,
            "store_identity": self.store_identity,
            "connection_generation": self.connection_generation,
            "preconditions": dict(self.preconditions),
            "scope": self.scope,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProductExportPayload":
        row = mapping(value, "payload") or {}
        raw_template = row.get("template_id", "")
        if isinstance(raw_template, bool) or not isinstance(raw_template, (str, int)):
            fail("invalid_template_id", "template_id must be a string or strict integer.")
        return cls(
            store_id=row.get("store_id", ""),
            store_identity=row.get("store_identity", row.get("store_id", "")),
            connection_generation=row.get("connection_generation", row.get("generation", -1)),
            template_id=str(raw_template),
            path=ExportPath(row.get("path", "blocked")),
            product_gid=row.get("product_gid"),
            scalar_fields=row.get("scalar_fields", row.get("product_scalars", {})),
            variant_updates=row.get("variant_updates", ()),
            variant_creates=row.get("variant_creates", ()),
            product_options=row.get("product_options", ()),
            media=row.get("media", ()),
            media_source_of_truth=row.get("media_source_of_truth"),
            binding_namespace_ready=row.get("binding_namespace_ready", False),
            binding_namespace_evidence=row.get("binding_namespace_evidence"),
            authority=row.get("authority", {}),
            variant_blocked_reason=row.get("variant_blocked_reason"),
            unowned_remote_variant_gids=row.get("unowned_remote_variant_gids", ()),
            preconditions=row.get("preconditions", {}),
            source_write_date=row.get("source_write_date"),
            remote_updated_at=row.get("remote_updated_at"),
            scope=row.get("scope", ""),
            fingerprint=row.get("fingerprint", ""),
        )


def build_export_payload(
    *,
    store_id: str,
    store_identity: str,
    connection_generation: int,
    template_id: str | int,
    path: ExportPath | str,
    product_gid: str | None = None,
    scalar_fields: Mapping[str, Any] | None = None,
    variant_plan: VariantPlan | None = None,
    variant_updates: Sequence[Mapping[str, Any]] = (),
    variant_creates: Sequence[Mapping[str, Any]] = (),
    product_options: Sequence[Mapping[str, Any]] = (),
    media: Sequence[Mapping[str, Any] | MediaCandidate] = (),
    media_source_of_truth: str | None = None,
    binding_namespace_ready: bool = False,
    binding_namespace_evidence: BindingNamespaceReadEvidence | None = None,
    authority: Mapping[str, Any] | None = None,
    preconditions: Mapping[str, Any] | None = None,
    source_write_date: datetime | str | None = None,
    remote_updated_at: datetime | str | None = None,
    reviewed_fingerprint: str | None = None,
) -> ProductExportPayload:
    if isinstance(template_id, bool) or not isinstance(template_id, (str, int)):
        fail("invalid_template_id", "template_id must be a string or strict integer.")
    export_path = ExportPath(path)
    if not isinstance(binding_namespace_ready, bool):
        fail("invalid_boolean", "binding_namespace_ready must be a strict boolean.")
    plan = variant_plan
    if plan is not None:
        variant_updates = tuple(row.as_dict() for row in plan.updates)
        variant_creates = tuple(row.as_dict() for row in plan.creates)
    variant_updates = _row_sequence(variant_updates, "variant_updates")
    variant_creates = _row_sequence(variant_creates, "variant_creates")
    product_option_rows = _row_sequence(product_options, "product_options", maximum=3)
    authority_values = authority_snapshot(authority)
    namespace_evidence = BindingNamespaceReadEvidence.from_value(binding_namespace_evidence)
    if binding_namespace_ready and namespace_evidence is None:
        fail("binding_namespace_evidence_required", "Binding namespace readiness requires server-attested read evidence.")
    if namespace_evidence is not None:
        binding_namespace_ready = True
    candidates = tuple(_as_candidate(row, index) for index, row in enumerate(media))
    source_date = _date(source_write_date, "source_write_date")
    remote_date = _date(remote_updated_at, "remote_updated_at")
    scalar_values = dict(mapping(scalar_fields or {}, "scalar_fields") or {})
    precondition_values = dict(mapping(preconditions or {}, "preconditions") or {})
    scope = scope_key(store_id, product_gid, template_id)
    business = {
        "template_id": str(template_id),
        "product_gid": product_gid,
        "path": export_path.value,
        "scalar_fields": scalar_values,
        "variant_updates": [dict(row) for row in variant_updates],
        "variant_creates": [dict(row) for row in variant_creates],
        "product_options": [dict(row) for row in product_option_rows],
        "media": [row.as_dict() for row in candidates],
        "media_source_of_truth": media_source_of_truth,
        "binding_namespace_ready": binding_namespace_ready,
        "binding_namespace_evidence": namespace_evidence.as_dict() if namespace_evidence else None,
        "authority": dict(authority_values),
        "variant_blocked_reason": plan.blocked_reason if plan else None,
        "unowned_remote_variant_gids": list(plan.unowned_remote_variant_gids) if plan else [],
        "source_write_date": source_date.isoformat() if source_date else None,
        "remote_updated_at": remote_date.isoformat() if remote_date else None,
    }
    computed = intent_fingerprint(
        store_id=store_id,
        connection_generation=connection_generation,
        operation="product_export",
        target={"product_gid": product_gid, "template_id": str(template_id)},
        business_values=business,
        preconditions=precondition_values,
        scope=scope,
    )
    if reviewed_fingerprint is not None:
        if not isinstance(reviewed_fingerprint, str) or len(reviewed_fingerprint) != 64 or any(char not in "0123456789abcdef" for char in reviewed_fingerprint):
            fail("invalid_fingerprint", "reviewed_fingerprint must be a lowercase SHA-256 digest.")
        if reviewed_fingerprint != computed:
            fail("stale_preview", "The reviewed product export fingerprint does not match server-derived intent.")
    return ProductExportPayload(
        store_id=store_id,
        store_identity=store_identity,
        connection_generation=connection_generation,
        template_id=str(template_id),
        path=export_path,
        product_gid=product_gid,
        scalar_fields=scalar_values,
        variant_updates=tuple(variant_updates),
        variant_creates=tuple(variant_creates),
        product_options=tuple(product_option_rows),
        media=candidates,
        media_source_of_truth=media_source_of_truth,
        binding_namespace_ready=binding_namespace_ready,
        binding_namespace_evidence=namespace_evidence,
        authority=authority_values,
        variant_blocked_reason=plan.blocked_reason if plan else None,
        unowned_remote_variant_gids=plan.unowned_remote_variant_gids if plan else (),
        preconditions=precondition_values,
        source_write_date=source_date,
        remote_updated_at=remote_date,
        scope=scope,
        fingerprint=computed,
    )


make_product_export_payload = build_export_payload


def build_export_sequence(payload: ProductExportPayload) -> ExportSequence:
    """Rebuild the deterministic sequence from one immutable payload."""

    if not isinstance(payload, ProductExportPayload):
        fail("invalid_request_plan", "payload must be ProductExportPayload.")
    variant_plan = VariantPlan(
        tuple(VariantChange(row["id"], {key: value for key, value in row.items() if key != "id"}) for row in payload.variant_updates),
        tuple(VariantCreate(dict(row)) for row in payload.variant_creates),
        payload.unowned_remote_variant_gids,
        payload.variant_blocked_reason,
    )
    return plan_export_sequence(
        path=payload.path,
        store_id=payload.store_id,
        template_id=payload.template_id,
        connection_generation=payload.connection_generation,
        expected_store_identity=payload.store_identity,
        product_gid=payload.product_gid,
        product_scalars=payload.scalar_fields,
        variant_plan=variant_plan,
        product_options=payload.product_options,
        media=payload.media,
        media_source_of_truth=payload.media_source_of_truth,
        binding_namespace_ready=payload.binding_namespace_ready,
        binding_namespace_evidence=payload.binding_namespace_evidence,
        authority=payload.authority,
        preconditions=payload.preconditions,
        source_write_date=payload.source_write_date,
        remote_updated_at=payload.remote_updated_at,
        reviewed_fingerprint=payload.fingerprint,
    )


sequence_for_payload = build_export_sequence


__all__ = [
    "ProductExportPayload",
    "build_export_payload",
    "build_export_sequence",
    "make_product_export_payload",
    "sequence_for_payload",
]
