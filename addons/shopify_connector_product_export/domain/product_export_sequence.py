"""Deterministic scope, fingerprint, and mutation-sequence planning for P13."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from ._support import (
    BINDING_DEFINITION_READ_OPERATION,
    BINDING_NAMESPACE_OPERATION,
    MEDIA_ASSOCIATE_OPERATION,
    MEDIA_FILE_CREATE_OPERATION,
    MEDIA_STAGE_OPERATION,
    PRODUCT_CREATE_OPERATION,
    PRODUCT_UPDATE_OPERATION,
    STEP_BINDING_NAMESPACE,
    STEP_BINDING_NAMESPACE_DECISION,
    STEP_BINDING_NAMESPACE_READBACK,
    STEP_CREATE,
    STEP_MEDIA_ASSOCIATE,
    STEP_MEDIA_FILE_CREATE,
    STEP_MEDIA_POLL,
    STEP_MEDIA_STAGE,
    STEP_MEDIA_UPLOAD,
    STEP_UPDATE,
    STEP_VARIANTS_CREATE,
    STEP_VARIANTS_UPDATE,
    VARIANTS_CREATE_OPERATION,
    VARIANTS_UPDATE_OPERATION,
    ProductExportPolicyError,
    canonical_fingerprint,
    fail,
    first,
    freeze_mapping,
    gid,
    money,
    mapping,
    parse_datetime,
    sequence,
    sha256_text,
    text,
    utc,
)
from .product_export_authority import authority_snapshot, validate_authoritative_payload, validate_export_fields, validate_options
from .product_export_binding import ExportPath, VariantPlan
from .product_export_readback import BindingNamespaceReadEvidence


def scope_key(
    store_id: str,
    product_gid: str | None = None,
    template_id: str | int | None = None,
    *,
    operation: str = "product",
    media_role: str | None = None,
    checksum: str | None = None,
) -> str:
    """Derive the durable product scope; callers cannot supply an arbitrary key."""

    store = text(store_id, "store_id", max_length=256)
    if template_id is not None and (isinstance(template_id, bool) or not isinstance(template_id, (str, int))):
        fail("invalid_template_id", "template_id must be a string or strict integer.")
    if product_gid:
        target = gid(product_gid, "product_gid", kind="Product")
    elif template_id is not None:
        target = "template:" + text(str(template_id), "template_id", max_length=256)
    else:
        fail("missing_scope_target", "A product GID or template ID is required for export scope.")
    parts = ["product", store, target]
    if operation != "product":
        parts.append(text(operation, "operation", max_length=128))
    if media_role:
        parts.append("media:" + text(media_role, "media_role", max_length=128))
    if checksum:
        parts.append("sha256:" + sha256_text(text(checksum, "checksum", max_length=65_536))[:24])
    return ":".join(parts)


def derive_scope_key(*args: Any, **kwargs: Any) -> str:
    return scope_key(*args, **kwargs)


def server_derived_scope(*args: Any, **kwargs: Any) -> str:
    return scope_key(*args, **kwargs)


_EPHEMERAL_FINGERPRINT_KEYS = frozenset(
    {
        "timestamp", "created_at", "createdat", "updated_at", "updatedat",
        "captured_at", "capturedat", "previewed_at", "previewedat",
        "expires_at", "expiresat", "display_label", "displaylabel",
        "display_name", "displayname", "correlation_id", "correlationid",
        "request_id", "requestid",
    }
)


def _stable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _stable(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
            if str(key).lower() not in _EPHEMERAL_FINGERPRINT_KEYS
        }
    if isinstance(value, (list, tuple)):
        return [_stable(item) for item in value]
    return value


def _timestamp(value: Any, name: str) -> str | None:
    if value is None:
        return None
    parsed = parse_datetime(value)
    if parsed is None:
        fail("invalid_datetime", f"{name} must be an ISO-8601 timestamp.")
    return utc(parsed, name).isoformat()


def intent_fingerprint(
    *,
    store_id: str,
    connection_generation: int,
    operation: str,
    target: Mapping[str, Any],
    business_values: Mapping[str, Any],
    preconditions: Mapping[str, Any] | None = None,
    scope: str | None = None,
) -> str:
    """Hash reviewed business intent and relevant preconditions deterministically."""

    if isinstance(connection_generation, bool) or not isinstance(connection_generation, int) or connection_generation < 0:
        fail("invalid_generation", "connection_generation must be a non-negative integer.")
    store = text(store_id, "store_id", max_length=256)
    operation_value = text(operation, "operation", max_length=128)
    target_value = freeze_mapping(target)
    business_value = freeze_mapping(business_values)
    document = {
        "store_id": store,
        "connection_generation": connection_generation,
        "operation": operation_value,
        "scope": scope or "",
        "target": _stable(target_value),
        "business_values": _stable(business_value),
        "preconditions": _stable(freeze_mapping(preconditions or {})),
    }
    if scope and (target_value.get("product_gid") or target_value.get("template_id")):
        expected_scope = scope_key(
            store,
            target_value.get("product_gid"),
            target_value.get("template_id"),
        )
        if scope != expected_scope:
            fail("invalid_scope", "scope is not the server-derived product scope.")
    return canonical_fingerprint(document)


def derive_intent_fingerprint(**kwargs: Any) -> str:
    return intent_fingerprint(**kwargs)


@dataclass(frozen=True)
class MediaCandidate:
    filename: str
    checksum: str
    alt: str = ""
    mime_type: str = "image/png"
    source_key: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "filename", text(self.filename, "media.filename", max_length=1024))
        object.__setattr__(self, "checksum", text(self.checksum, "media.checksum", max_length=65_536))
        object.__setattr__(self, "alt", text(self.alt, "media.alt", allow_empty=True, max_length=1024))
        mime_type = text(self.mime_type, "media.mime_type", max_length=128)
        if mime_type != "image/png":
            fail("unsupported_media_type", "P13 media export only supports image/png.")
        object.__setattr__(self, "mime_type", mime_type)
        if self.source_key is not None:
            object.__setattr__(self, "source_key", text(self.source_key, "media.source_key", max_length=256))

    def as_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "checksum": self.checksum,
            "alt": self.alt,
            "mime_type": self.mime_type,
            "source_key": self.source_key,
        }


@dataclass(frozen=True)
class MediaPlan:
    candidates: tuple[MediaCandidate, ...]
    skipped_reason: str | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.candidates) and self.skipped_reason is None


def plan_media(
    media: Iterable[Mapping[str, Any] | MediaCandidate],
    *,
    source_of_truth: str | None,
    existing_product: bool,
) -> MediaPlan:
    """Apply V1 append-only media gating; create previews never send media."""

    if not isinstance(existing_product, bool):
        fail("invalid_boolean", "existing_product must be a strict boolean.")
    if source_of_truth not in ("odoo", "odoo_authoritative"):
        return MediaPlan((), "media_source_not_odoo")
    if not existing_product:
        return MediaPlan((), "media_deferred_until_product_binding")
    rows = sequence(list(media), "media", maximum=100)
    candidates: list[MediaCandidate] = []
    seen: set[tuple[str, str]] = set()
    for index, raw in enumerate(rows):
        if isinstance(raw, MediaCandidate):
            candidate = raw
        else:
            row = raw if isinstance(raw, Mapping) else {}
            candidate = MediaCandidate(
                filename=first(row, "filename", "name", default=""),
                checksum=first(row, "checksum", "sha256", "content_hash", default=""),
                alt=first(row, "alt", "alt_text", default=""),
                mime_type=first(row, "mime_type", "mimeType", default="image/png"),
                source_key=first(row, "source_key", "id", default=None),
            )
        key = (candidate.filename, candidate.checksum)
        if key in seen:
            fail("duplicate_media_candidate", "A media file occurs more than once in one export intent.", details={"filename": candidate.filename})
        seen.add(key)
        candidates.append(candidate)
    return MediaPlan(tuple(candidates))


@dataclass(frozen=True)
class MutationStep:
    sequence: int
    step: str
    operation: str
    scope: str
    target: Mapping[str, Any]
    business_values: Mapping[str, Any]
    idempotency_key: str
    remote_send: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence <= 0:
            fail("invalid_sequence", "Mutation sequence numbers start at one.")
        object.__setattr__(self, "step", text(self.step, "step", max_length=256))
        object.__setattr__(self, "operation", text(self.operation, "operation", max_length=256))
        object.__setattr__(self, "scope", text(self.scope, "scope", max_length=1024))
        object.__setattr__(self, "target", freeze_mapping(dict(mapping(self.target, "target") or {})))
        object.__setattr__(self, "business_values", freeze_mapping(dict(mapping(self.business_values, "business_values") or {})))
        object.__setattr__(self, "idempotency_key", text(self.idempotency_key, "idempotency_key", max_length=512))
        if not isinstance(self.remote_send, bool):
            fail("invalid_boolean", "remote_send must be a strict boolean.")

    @property
    def send_once_key(self) -> str:
        return self.idempotency_key

    def as_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "step": self.step,
            "operation": self.operation,
            "scope": self.scope,
            "target": dict(self.target),
            "business_values": dict(self.business_values),
            "idempotency_key": self.idempotency_key,
            "remote_send": self.remote_send,
        }


@dataclass(frozen=True)
class ExportSequence:
    path: ExportPath
    fingerprint: str
    scope: str
    steps: tuple[MutationStep, ...]
    blocked_reason: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "path", ExportPath(self.path))
        if not isinstance(self.fingerprint, str) or len(self.fingerprint) != 64 or any(char not in "0123456789abcdef" for char in self.fingerprint):
            fail("invalid_fingerprint", "fingerprint must be a lowercase SHA-256 digest.")
        object.__setattr__(self, "scope", text(self.scope, "scope", max_length=1024))
        object.__setattr__(self, "steps", tuple(self.steps))
        if any(not isinstance(step, MutationStep) for step in self.steps):
            fail("invalid_sequence", "Export steps must be MutationStep values.")
        if self.path is ExportPath.BLOCKED and self.steps:
            fail("blocked_sequence", "A blocked export cannot contain mutation steps.")
        expected = tuple(range(1, len(self.steps) + 1))
        if tuple(step.sequence for step in self.steps) != expected:
            fail("invalid_sequence", "Export mutation steps must be contiguous and ordered.")
        if self.blocked_reason is not None:
            object.__setattr__(self, "blocked_reason", text(self.blocked_reason, "blocked_reason", max_length=256))

    @property
    def remote_send_count(self) -> int:
        return sum(1 for step in self.steps if step.remote_send)

    def as_dict(self) -> dict[str, Any]:
        return {
            "path": self.path.value,
            "fingerprint": self.fingerprint,
            "scope": self.scope,
            "steps": [step.as_dict() for step in self.steps],
            "blocked_reason": self.blocked_reason,
        }


def _step(
    *,
    sequence_number: int,
    step_name: str,
    operation: str,
    scope: str,
    target: Mapping[str, Any],
    business_values: Mapping[str, Any],
    fingerprint: str,
    remote_send: bool = True,
) -> MutationStep:
    idempotency = canonical_fingerprint(
        {"intent": fingerprint, "sequence": sequence_number, "operation": operation, "target": _stable(target)}
    )
    return MutationStep(sequence_number, step_name, operation, scope, target, business_values, idempotency, remote_send)


def plan_export_sequence(
    *,
    path: ExportPath | str,
    store_id: str,
    template_id: str | int,
    connection_generation: int,
    expected_store_identity: str | None = None,
    product_gid: str | None = None,
    product_scalars: Mapping[str, Any] | None = None,
    variant_plan: VariantPlan | None = None,
    product_options: Iterable[Mapping[str, Any]] = (),
    media: Iterable[Mapping[str, Any] | MediaCandidate] = (),
    media_source_of_truth: str | None = None,
    binding_namespace_ready: bool = False,
    binding_namespace_evidence: BindingNamespaceReadEvidence | None = None,
    authority: Mapping[str, Any] | None = None,
    preconditions: Mapping[str, Any] | None = None,
    business_values: Mapping[str, Any] | None = None,
    source_write_date: Any = None,
    remote_updated_at: Any = None,
    reviewed_fingerprint: str | None = None,
) -> ExportSequence:
    """Build the one-send-per-intent sequence used by the application layer."""

    export_path = ExportPath(path)
    if isinstance(template_id, bool) or not isinstance(template_id, (str, int)):
        fail("invalid_template_id", "template_id must be a string or strict integer.")
    if not isinstance(binding_namespace_ready, bool):
        fail("invalid_boolean", "binding_namespace_ready must be a strict boolean.")
    namespace_evidence = BindingNamespaceReadEvidence.from_value(binding_namespace_evidence)
    if binding_namespace_ready and namespace_evidence is None:
        fail("binding_namespace_evidence_required", "Binding namespace readiness requires server-attested read evidence.")
    if namespace_evidence is not None:
        if expected_store_identity is None:
            fail("binding_namespace_scope_required", "Expected Shopify store identity is required with binding namespace evidence.")
        expected_identity = text(expected_store_identity, "expected_store_identity", max_length=512)
        if namespace_evidence.store_identity != expected_identity:
            fail("binding_namespace_scope_mismatch", "Binding namespace evidence is for another Shopify store.")
        if namespace_evidence.connection_generation != connection_generation:
            fail("stale_binding_evidence", "Binding namespace evidence is for another connection generation.")
        binding_namespace_ready = True
    authority_values = authority_snapshot(authority)
    scope = scope_key(store_id, product_gid, template_id)
    media_rows = list(media)
    update_rows = [row.as_dict() for row in (variant_plan.updates if variant_plan else ())]
    create_rows = [row.as_dict() for row in (variant_plan.creates if variant_plan else ())]
    scalar_rows = dict(product_scalars or {})
    option_rows = [dict(row) for row in product_options]
    validate_export_fields(scalar_rows, update_rows + create_rows)
    if option_rows:
        validate_options(option_rows)
    validate_authoritative_payload(authority_values, scalar_rows, update_rows + create_rows, option_rows)
    source_timestamp = _timestamp(source_write_date, "source_write_date")
    remote_timestamp = _timestamp(remote_updated_at, "remote_updated_at")
    if export_path in {ExportPath.CREATE, ExportPath.UPDATE} and source_timestamp is None:
        fail("missing_freshness", "Product export requires a source write timestamp from the reviewed preview.")
    if export_path is ExportPath.UPDATE and remote_timestamp is None:
        fail("missing_freshness", "Product update requires the observed Shopify updated timestamp from the reviewed preview.")
    values: dict[str, Any] = {
        "template_id": str(template_id),
        "product_gid": product_gid,
        "path": export_path.value,
        "scalar_fields": scalar_rows,
        "variant_updates": update_rows,
        "variant_creates": create_rows,
        "product_options": option_rows,
        "media": [row.as_dict() if isinstance(row, MediaCandidate) else dict(row) for row in media_rows],
        "media_source_of_truth": media_source_of_truth,
        "binding_namespace_ready": binding_namespace_ready,
        "binding_namespace_evidence": namespace_evidence.as_dict() if namespace_evidence else None,
        "authority": dict(authority_values),
        "variant_blocked_reason": variant_plan.blocked_reason if variant_plan else None,
        "unowned_remote_variant_gids": list(variant_plan.unowned_remote_variant_gids) if variant_plan else [],
        "source_write_date": source_timestamp,
        "remote_updated_at": remote_timestamp,
    }
    extras = dict(business_values or {})
    protected_business_keys = {
        "template_id", "product_gid", "path", "scalar_fields", "variant_updates",
        "variant_creates", "product_options", "media", "media_source_of_truth",
        "binding_namespace_ready", "binding_namespace_evidence", "authority", "variant_blocked_reason",
        "unowned_remote_variant_gids", "source_write_date", "remote_updated_at",
    }
    collision = sorted(set(extras) & protected_business_keys)
    if collision:
        fail("server_derived_value", f"business_values cannot override {collision[0]}.")
    values.update(extras)
    computed = intent_fingerprint(
        store_id=store_id,
        connection_generation=connection_generation,
        operation="product_export",
        target={"product_gid": product_gid, "template_id": str(template_id)},
        business_values=values,
        preconditions=preconditions,
        scope=scope,
    )
    fingerprint = computed
    if reviewed_fingerprint is not None:
        if not isinstance(reviewed_fingerprint, str) or len(reviewed_fingerprint) != 64 or any(char not in "0123456789abcdef" for char in reviewed_fingerprint):
            fail("invalid_fingerprint", "reviewed_fingerprint must be a lowercase SHA-256 digest.")
        if reviewed_fingerprint != computed:
            fail("stale_preview", "reviewed_fingerprint does not match server-derived intent.")

    if variant_plan and variant_plan.blocked:
        return ExportSequence(ExportPath.BLOCKED, fingerprint, scope, (), variant_plan.blocked_reason)
    if export_path is ExportPath.BLOCKED:
        return ExportSequence(export_path, fingerprint, scope, (), "blocked_by_policy")
    if export_path is ExportPath.CREATE and product_gid:
        return ExportSequence(export_path, fingerprint, scope, (), "create_requires_unbound_product")
    if export_path is ExportPath.UPDATE and not product_gid:
        return ExportSequence(export_path, fingerprint, scope, (), "update_requires_product_binding")

    steps: list[MutationStep] = []
    number = 1
    if export_path is ExportPath.CREATE:
        decision = {
            "decision": "ready" if binding_namespace_ready else "bootstrap_required",
            "server_attested": namespace_evidence is not None,
            "evidence": namespace_evidence.as_dict() if namespace_evidence else None,
        }
        steps.append(_step(
            sequence_number=number,
            step_name=STEP_BINDING_NAMESPACE_DECISION,
            operation="product_export.binding_namespace.decision",
            scope=scope_key(store_id, template_id=template_id, operation="binding"),
            target={"template_id": str(template_id)},
            business_values=decision,
            fingerprint=fingerprint,
            remote_send=False,
        ))
        number += 1
        if not binding_namespace_ready:
            steps.append(_step(sequence_number=number, step_name=STEP_BINDING_NAMESPACE, operation=BINDING_NAMESPACE_OPERATION, scope=scope_key(store_id, template_id=template_id, operation="binding"), target={"template_id": str(template_id)}, business_values={"template_id": str(template_id)}, fingerprint=fingerprint))
            number += 1
            steps.append(_step(
                sequence_number=number,
                step_name=STEP_BINDING_NAMESPACE_READBACK,
                operation=BINDING_DEFINITION_READ_OPERATION,
                scope=scope_key(store_id, template_id=template_id, operation="binding"),
                target={"template_id": str(template_id)},
                business_values={"decision": "verify_bootstrap"},
                fingerprint=fingerprint,
                remote_send=False,
            ))
            return ExportSequence(export_path, fingerprint, scope, tuple(steps), "binding_namespace_readback_required")
        steps.append(_step(sequence_number=number, step_name=STEP_CREATE, operation=PRODUCT_CREATE_OPERATION, scope=scope, target={"template_id": str(template_id)}, business_values=values, fingerprint=fingerprint))
    else:
        scalars = scalar_rows
        if scalars:
            steps.append(_step(sequence_number=number, step_name=STEP_UPDATE, operation=PRODUCT_UPDATE_OPERATION, scope=scope, target={"product_gid": product_gid}, business_values=scalars, fingerprint=fingerprint))
            number += 1
        if variant_plan and variant_plan.updates:
            steps.append(_step(sequence_number=number, step_name=STEP_VARIANTS_UPDATE, operation=VARIANTS_UPDATE_OPERATION, scope=scope, target={"product_gid": product_gid}, business_values={"variants": [row.as_dict() for row in variant_plan.updates]}, fingerprint=fingerprint))
            number += 1
        if variant_plan and variant_plan.creates:
            steps.append(_step(sequence_number=number, step_name=STEP_VARIANTS_CREATE, operation=VARIANTS_CREATE_OPERATION, scope=scope, target={"product_gid": product_gid}, business_values={"variants": [row.as_dict() for row in variant_plan.creates]}, fingerprint=fingerprint))
            number += 1
        media_plan = plan_media(media_rows, source_of_truth=media_source_of_truth, existing_product=True)
        for candidate in media_plan.candidates:
            media_scope = scope_key(store_id, product_gid, template_id, operation="media", media_role=candidate.filename, checksum=candidate.checksum)
            target = {"product_gid": product_gid, "filename": candidate.filename, "checksum": candidate.checksum}
            business = candidate.as_dict()
            steps.append(_step(sequence_number=number, step_name=STEP_MEDIA_STAGE, operation=MEDIA_STAGE_OPERATION, scope=media_scope, target=target, business_values=business, fingerprint=fingerprint)); number += 1
            steps.append(_step(sequence_number=number, step_name=STEP_MEDIA_UPLOAD, operation="product_export.media_upload", scope=media_scope, target=target, business_values=business, fingerprint=fingerprint, remote_send=False)); number += 1
            steps.append(_step(sequence_number=number, step_name=STEP_MEDIA_FILE_CREATE, operation=MEDIA_FILE_CREATE_OPERATION, scope=media_scope, target=target, business_values=business, fingerprint=fingerprint)); number += 1
            steps.append(_step(sequence_number=number, step_name=STEP_MEDIA_POLL, operation="product_export.media_file_create.read", scope=media_scope, target=target, business_values=business, fingerprint=fingerprint, remote_send=False)); number += 1
            steps.append(_step(sequence_number=number, step_name=STEP_MEDIA_ASSOCIATE, operation=MEDIA_ASSOCIATE_OPERATION, scope=media_scope, target=target, business_values=business, fingerprint=fingerprint)); number += 1
    return ExportSequence(export_path, fingerprint, scope, tuple(steps))


def plan_export(**kwargs: Any) -> ExportSequence:
    return plan_export_sequence(**kwargs)


__all__ = [
    "ExportSequence", "MediaCandidate", "MediaPlan", "MutationStep", "derive_intent_fingerprint",
    "derive_scope_key", "intent_fingerprint", "plan_export", "plan_export_sequence", "plan_media",
    "scope_key", "server_derived_scope",
]
