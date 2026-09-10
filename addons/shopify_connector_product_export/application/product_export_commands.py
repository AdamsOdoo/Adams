"""Typed product-export commands and inert request materialization.

The application layer owns authorization/freshness checks and turns a frozen
payload into gateway requests.  It never performs HTTP, ORM reads/writes,
durable persistence, retries, or reconciliation itself.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Protocol
from uuid import UUID

from ..domain._support import (
    BINDING_DEFINITION_READ_OPERATION,
    BINDING_NAMESPACE_OPERATION,
    MEDIA_ASSOCIATE_OPERATION,
    MEDIA_FILE_CREATE_OPERATION,
    MEDIA_STAGE_OPERATION,
    PRODUCT_CREATE_OPERATION,
    PRODUCT_UPDATE_OPERATION,
    VARIANTS_CREATE_OPERATION,
    VARIANTS_UPDATE_OPERATION,
    fail,
    gid,
    text,
)
from ..domain.product_export_preview import PreviewSnapshot, reject_stale_preview
from ..domain.product_export_readback import ReadbackResult, ReadbackVerdict
from ..domain.product_export_sequence import ExportSequence, MutationStep
from .product_export_payloads import (
    ProductExportPayload,
    build_export_payload,
    build_export_sequence,
    make_product_export_payload,
    sequence_for_payload,
)


class ProductMutationGatewayPort(Protocol):
    """Shape implemented by the stable P08 product gateway."""

    def build_binding_namespace(self, **kwargs: Any) -> Any: ...
    def build_create(self, product_input: Mapping[str, Any], template_id: str | int, **kwargs: Any) -> Any: ...
    def build_update(self, product_gid: str, product_input: Mapping[str, Any], **kwargs: Any) -> Any: ...
    def build_variants_update(self, product_gid: str, variants: Sequence[Mapping[str, Any]], **kwargs: Any) -> Any: ...
    def build_variants_create(self, product_gid: str, variants: Sequence[Mapping[str, Any]], **kwargs: Any) -> Any: ...


class ProductMediaGatewayPort(Protocol):
    """Shape implemented by the stable P08 product-media gateway."""

    def build_stage(self, filename: str, **kwargs: Any) -> Any: ...
    def build_file_create(self, staged_resource_url: str, filename: str, **kwargs: Any) -> Any: ...
    def build_associate(self, file_gid: str, product_gid: str, **kwargs: Any) -> Any: ...


@dataclass(frozen=True)
class DurableMediaProgress:
    """Progress loaded from a durable ledger for one exact media sub-sequence."""

    sequence_fingerprint: str
    media_scope: str
    completed_step_keys: tuple[str, ...]
    file_gid: str
    file_readback: ReadbackResult

    def __post_init__(self) -> None:
        if not isinstance(self.sequence_fingerprint, str) or len(self.sequence_fingerprint) != 64 or any(char not in "0123456789abcdef" for char in self.sequence_fingerprint):
            fail("invalid_media_progress", "Durable media progress requires the exact sequence fingerprint.")
        object.__setattr__(self, "media_scope", text(self.media_scope, "media_scope", max_length=1024))
        if isinstance(self.completed_step_keys, (str, bytes)) or not isinstance(self.completed_step_keys, (list, tuple)):
            fail("invalid_media_progress", "completed media step keys must be a sequence.")
        keys = tuple(text(value, "completed_step_key", max_length=512) for value in self.completed_step_keys)
        if len(keys) != len(set(keys)):
            fail("invalid_media_progress", "completed media step keys must be unique.")
        object.__setattr__(self, "completed_step_keys", keys)
        object.__setattr__(self, "file_gid", gid(self.file_gid, "file_gid", kind="File"))
        if not isinstance(self.file_readback, ReadbackResult):
            fail("invalid_media_progress", "Durable media progress requires a typed File readback.")
        if (
            self.file_readback.operation != MEDIA_FILE_CREATE_OPERATION
            or self.file_readback.verdict is not ReadbackVerdict.APPLIED
            or self.file_readback.matched != (self.file_gid,)
            or self.file_readback.store_identity is None
        ):
            fail("invalid_media_progress", "Durable media progress requires an applied exact-store File identity readback.")


class DurableMediaProgressPort(Protocol):
    """Trusted server port that loads committed progress, never UI materialization."""

    def load_verified(self, *, sequence_fingerprint: str, media_scope: str) -> DurableMediaProgress | None: ...


def _uuid_text(value: Any, name: str) -> str:
    value = text(value, name, max_length=36)
    try:
        parsed = UUID(value)
    except (AttributeError, ValueError) as exc:
        fail("invalid_uuid", f"{name} must be a canonical UUID.")
        raise AssertionError from exc
    canonical = str(parsed)
    if value != canonical:
        fail("invalid_uuid", f"{name} must be a lowercase hyphenated UUID.")
    return canonical


@dataclass(frozen=True)
class ProductExportCommand:
    operation: str
    payload: ProductExportPayload
    command_id: str
    actor_role: str
    expected_generation: int | None = None
    expected_fingerprint: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.operation, str) or self.operation not in {"preview", "apply"}:
            fail("invalid_command", "operation must be preview or apply.")
        if not isinstance(self.payload, ProductExportPayload):
            fail("invalid_command", "payload must be ProductExportPayload.")
        object.__setattr__(self, "command_id", _uuid_text(self.command_id, "command_id"))
        object.__setattr__(self, "actor_role", text(self.actor_role, "actor_role", max_length=64))
        if self.expected_generation is None:
            object.__setattr__(self, "expected_generation", self.payload.connection_generation)
        if isinstance(self.expected_generation, bool) or not isinstance(self.expected_generation, int) or self.expected_generation < 0:
            fail("invalid_generation", "expected_generation must be a non-negative integer.")
        if not self.expected_fingerprint:
            object.__setattr__(self, "expected_fingerprint", self.payload.fingerprint)
        if self.expected_fingerprint != self.payload.fingerprint:
            fail("stale_preview", "command fingerprint does not match payload fingerprint.")

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ProductExportCommand":
        if not isinstance(value, Mapping):
            fail("invalid_mapping", "command must be an object.")
        payload = value.get("payload")
        if not isinstance(payload, ProductExportPayload):
            payload = ProductExportPayload.from_mapping(payload or {})
        return cls(
            operation=value.get("operation", "preview"),
            payload=payload,
            command_id=value.get("command_id", value.get("id", "")),
            actor_role=value.get("actor_role", value.get("role", "")),
            expected_generation=value.get("expected_generation", payload.connection_generation),
            expected_fingerprint=value.get("expected_fingerprint", payload.fingerprint),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "payload": self.payload.as_dict(),
            "command_id": self.command_id,
            "actor_role": self.actor_role,
            "expected_generation": self.expected_generation,
            "expected_fingerprint": self.expected_fingerprint,
        }


def _same_datetime(left: datetime | None, right: datetime | None) -> bool:
    if left is None or right is None:
        return left is right
    return left == right


def validate_command(
    command: ProductExportCommand,
    *,
    current_generation: int,
    current_fingerprint: str | None = None,
    preview: PreviewSnapshot | None = None,
    now: datetime | None = None,
    current_source_write_date: datetime | None = None,
    current_remote_updated_at: datetime | None = None,
    current_store_id: str | None = None,
) -> ProductExportCommand:
    if not isinstance(command, ProductExportCommand):
        fail("invalid_command", "command must be ProductExportCommand.")
    if isinstance(current_generation, bool) or not isinstance(current_generation, int) or current_generation < 0:
        fail("invalid_generation", "current_generation must be a non-negative integer.")
    if command.operation == "apply" and command.actor_role not in {"admin", "administrator"}:
        fail("forbidden", "Only an administrator may apply a product export.")
    if command.expected_generation != current_generation:
        fail("stale_preview", "The connection generation changed since preview.")
    if current_fingerprint is not None and current_fingerprint != command.expected_fingerprint:
        fail("stale_preview", "The product export fingerprint changed since preview.")
    if command.operation != "apply":
        return command
    if preview is None:
        fail("preview_required", "An exact confirmed preview is required before product export apply.")
    if now is None:
        fail("invalid_datetime", "now is required when validating a product export preview.")
    if current_fingerprint is None:
        fail("stale_preview", "The current server-derived fingerprint is required before apply.")
    if current_store_id is None:
        fail("store_scope_required", "The current store identity is required before apply.")
    if current_store_id is not None and current_store_id != command.payload.store_id:
        fail("store_scope_mismatch", "The current store does not match the command payload.")
    if preview.scope is None:
        fail("preview_scope_required", "The confirmed preview must carry the server-derived scope.")
    if preview.product_gid != command.payload.product_gid:
        fail("stale_preview", "The confirmed preview product identity does not match the command.")
    if not _same_datetime(preview.source_write_date, command.payload.source_write_date):
        fail("stale_preview", "The confirmed preview source timestamp does not match the command.")
    if not _same_datetime(preview.remote_updated_at, command.payload.remote_updated_at):
        fail("stale_preview", "The confirmed preview Shopify timestamp does not match the command.")
    if command.payload.source_write_date is not None and current_source_write_date is None:
        fail("freshness_required", "The current source timestamp is required before apply.")
    if command.payload.remote_updated_at is not None and current_remote_updated_at is None:
        fail("freshness_required", "The current Shopify timestamp is required before apply.")
    reject_stale_preview(
        preview,
        now=now,
        expected_fingerprint=command.expected_fingerprint,
        current_generation=current_generation,
        current_source_write_date=current_source_write_date,
        current_remote_updated_at=current_remote_updated_at,
        current_store_id=command.payload.store_id if current_store_id is None else current_store_id,
        current_scope=command.payload.scope,
    )
    return command


@dataclass(frozen=True)
class GatewayRequest:
    step: MutationStep
    request: Any | None
    disposition: str = "ready"
    reason_code: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.step, MutationStep):
            fail("invalid_request_plan", "GatewayRequest.step must be MutationStep.")
        if self.disposition not in {"ready", "deferred", "blocked"}:
            fail("invalid_request_plan", "GatewayRequest disposition is unsupported.")
        if self.disposition == "ready" and self.request is None and self.step.remote_send:
            fail("invalid_request_plan", "A remote-send step cannot be ready without a request.")
        if self.reason_code is not None:
            object.__setattr__(self, "reason_code", text(self.reason_code, "reason_code", max_length=128))

    @property
    def remote_send(self) -> bool:
        return self.disposition == "ready" and self.step.remote_send and self.request is not None

    @property
    def deferred(self) -> bool:
        return self.disposition == "deferred"

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step.as_dict(),
            "disposition": self.disposition,
            "reason_code": self.reason_code,
        }


def _gateway_kwargs(step: MutationStep, payload: ProductExportPayload) -> dict[str, Any]:
    return {
        "idempotency_key": step.idempotency_key,
        "operation_scope_key": step.scope,
        "business_intent": dict(step.business_values),
        "preconditions_snapshot": dict(payload.preconditions),
    }


def _create_variant_input(row: Mapping[str, Any], *, product_options: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    result = dict(row)
    inventory = result.pop("inventoryItem", None)
    if isinstance(inventory, Mapping) and "sku" in inventory:
        result["sku"] = inventory["sku"]
    if product_options:
        options = result.get("optionValues")
        if not isinstance(options, Sequence) or isinstance(options, (str, bytes)) or not options:
            fail("invalid_variant_options", "Each structured create variant requires optionValues.")
    elif "optionValues" not in result:
        result["optionValues"] = [{"optionName": "Title", "name": "Default Title"}]
    return result


def _deferred(step: MutationStep, reason_code: str) -> GatewayRequest:
    return GatewayRequest(step, None, "deferred", reason_code)


def build_gateway_requests(
    payload: ProductExportPayload,
    sequence: ExportSequence,
    product_gateway: ProductMutationGatewayPort,
    media_gateway: ProductMediaGatewayPort | None = None,
    *,
    materialized_media: Mapping[str, Mapping[str, Any]] | None = None,
    durable_media_progress: DurableMediaProgressPort | None = None,
) -> tuple[GatewayRequest, ...]:
    """Materialize typed requests only; no request is sent from this function."""

    if not isinstance(payload, ProductExportPayload) or not isinstance(sequence, ExportSequence):
        fail("invalid_request_plan", "payload and sequence are required typed contracts.")
    expected_sequence = build_export_sequence(payload)
    if sequence != expected_sequence:
        fail("stale_preview", "sequence does not exactly match the server-derived payload intent.")
    if materialized_media is not None and not isinstance(materialized_media, Mapping):
        fail("invalid_mapping", "materialized_media must be an object.")
    materialized = materialized_media or {}
    requests: list[GatewayRequest] = []
    for step in sequence.steps:
        kwargs = _gateway_kwargs(step, payload)
        request: Any | None = None
        if step.operation == "product_export.binding_namespace.decision":
            requests.append(GatewayRequest(step, None))
            continue
        if step.operation == BINDING_DEFINITION_READ_OPERATION:
            requests.append(_deferred(step, "binding_namespace_readback_required"))
            continue
        if step.operation == BINDING_NAMESPACE_OPERATION:
            request = product_gateway.build_binding_namespace(**kwargs)
        elif step.operation == PRODUCT_CREATE_OPERATION:
            product_input = dict(payload.scalar_fields)
            structured_options = bool(payload.product_options)
            normalized_options = []
            if structured_options:
                from ..domain.product_export_authority import validate_options  # noqa: PLC0415
                normalized_options = validate_options(payload.product_options)
            if not normalized_options and payload.variant_creates:
                normalized_options = [{"name": "Title", "values": [{"name": "Default Title"}]}]
            if normalized_options:
                product_input["productOptions"] = normalized_options
            if payload.variant_creates:
                product_input["variants"] = [_create_variant_input(row, product_options=normalized_options if structured_options else ()) for row in payload.variant_creates]
            request = product_gateway.build_create(product_input, payload.template_id, **kwargs)
        elif step.operation == PRODUCT_UPDATE_OPERATION:
            request = product_gateway.build_update(payload.product_gid or "", dict(payload.scalar_fields), **kwargs)
        elif step.operation == VARIANTS_UPDATE_OPERATION:
            request = product_gateway.build_variants_update(payload.product_gid or "", [dict(row) for row in payload.variant_updates], **kwargs)
        elif step.operation == VARIANTS_CREATE_OPERATION:
            normalized_options = []
            if payload.product_options:
                from ..domain.product_export_authority import validate_options  # noqa: PLC0415
                normalized_options = validate_options(payload.product_options)
            request = product_gateway.build_variants_create(payload.product_gid or "", [_create_variant_input(row, product_options=normalized_options) for row in payload.variant_creates], **kwargs)
        elif step.operation == MEDIA_STAGE_OPERATION:
            if media_gateway is None:
                fail("missing_media_gateway", "A media gateway is required for media staging.")
            request = media_gateway.build_stage(step.target["filename"], **kwargs)
        elif step.operation == "product_export.media_upload":
            requests.append(_deferred(step, "media_upload_runtime_required"))
            continue
        elif step.operation == MEDIA_FILE_CREATE_OPERATION:
            if media_gateway is None:
                fail("missing_media_gateway", "A media gateway is required for media file creation.")
            row = materialized.get(step.target["filename"]) or materialized.get(step.target["checksum"])
            if not isinstance(row, Mapping) or not row.get("staged_resource_url"):
                requests.append(_deferred(step, "media_stage_materialization_required"))
                continue
            request = media_gateway.build_file_create(
                row["staged_resource_url"],
                step.target["filename"],
                alt=row.get("alt", ""),
                **kwargs,
            )
        elif step.operation == "product_export.media_file_create.read":
            requests.append(_deferred(step, "media_file_create_readback_required"))
            continue
        elif step.operation == MEDIA_ASSOCIATE_OPERATION:
            if media_gateway is None:
                fail("missing_media_gateway", "A media gateway is required for media association.")
            if durable_media_progress is None or not callable(getattr(durable_media_progress, "load_verified", None)):
                requests.append(_deferred(step, "durable_media_progress_required"))
                continue
            progress = durable_media_progress.load_verified(
                sequence_fingerprint=sequence.fingerprint,
                media_scope=step.scope,
            )
            if progress is None:
                requests.append(_deferred(step, "media_file_readback_required"))
                continue
            if not isinstance(progress, DurableMediaProgress):
                fail("invalid_media_progress", "The durable media progress port returned an unsupported value.")
            required_operations = (
                MEDIA_STAGE_OPERATION,
                "product_export.media_upload",
                MEDIA_FILE_CREATE_OPERATION,
                "product_export.media_file_create.read",
            )
            prerequisite_steps = tuple(
                candidate
                for candidate in sequence.steps
                if candidate.scope == step.scope and candidate.sequence < step.sequence
                and candidate.operation in required_operations
            )
            if tuple(candidate.operation for candidate in prerequisite_steps) != required_operations:
                fail("invalid_media_sequence", "Media association prerequisites are missing or out of order.")
            required_keys = {candidate.idempotency_key for candidate in prerequisite_steps}
            if (
                progress.sequence_fingerprint != sequence.fingerprint
                or progress.media_scope != step.scope
                or progress.file_readback.store_identity != payload.store_identity
                or not required_keys.issubset(progress.completed_step_keys)
            ):
                requests.append(_deferred(step, "media_prerequisites_not_durable"))
                continue
            request = media_gateway.build_associate(progress.file_gid, payload.product_gid or "", **kwargs)
        else:
            fail("unsupported_step", f"Unsupported product-export sequence operation: {step.operation}.")
        requests.append(GatewayRequest(step, request))
    return tuple(requests)


build_mutation_requests = build_gateway_requests
requests_for_sequence = build_gateway_requests


class FakeMutationLedger:
    """Deterministic test seam: an intent key is attempted at most once."""

    def __init__(self) -> None:
        self._attempts: dict[str, Any] = {}
        self._calls: list[str] = []

    @property
    def calls(self) -> tuple[str, ...]:
        return tuple(self._calls)

    def send_once(self, intent_key: str, sender: Callable[[], Any]) -> Any:
        key = text(intent_key, "intent_key", max_length=512)
        if key in self._attempts:
            return self._attempts[key]
        self._attempts[key] = None
        self._calls.append(key)
        try:
            result = sender()
        except Exception:
            # The key remains claimed; callers must reconcile uncertainty.
            raise
        self._attempts[key] = result
        return result


__all__ = [
    "FakeMutationLedger",
    "DurableMediaProgress",
    "DurableMediaProgressPort",
    "GatewayRequest",
    "ProductExportCommand",
    "ProductExportPayload",
    "ProductMediaGatewayPort",
    "ProductMutationGatewayPort",
    "build_export_payload",
    "build_export_sequence",
    "build_gateway_requests",
    "build_mutation_requests",
    "make_product_export_payload",
    "requests_for_sequence",
    "sequence_for_payload",
    "validate_command",
]
