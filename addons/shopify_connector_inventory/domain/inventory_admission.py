"""Pure P12 admission policy for inventory mutation intents.

The policy is intentionally separate from the payload and evidence DTOs.  It
only answers whether an already-typed intent has enough current V1 evidence to
be handed to the request adapter; it never reads Odoo, calls Shopify or
persists a decision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import Enum
from typing import Any

from shopify_connector_core.domain.immutability import freeze_value, to_plain

from .inventory_mutation import (
    DEFAULT_MAX_OBSERVATION_AGE_SECONDS,
    INVENTORY_ACTIVATE_OPERATION,
    MAX_CAS_RETRY_ORDINAL,
    InventoryMappingSnapshot,
    InventoryMutationPayload,
    InventoryPairObservation,
    _timestamp,
    _utc,
    canonical_preview_fingerprint,
)


_SHA256_HEX_LENGTH = 64


class AdmissionReason(str, Enum):
    """Stable machine reasons for a fail-closed admission decision."""

    ADMITTED = "admitted"
    MAPPING_MISSING = "mapping_missing"
    MAPPING_INVALID = "mapping_invalid"
    MAPPING_DISABLED = "mapping_disabled"
    STORE_SCOPE_MISMATCH = "store_scope_mismatch"
    OBSERVATION_MISSING = "observation_missing"
    OBSERVATION_STALE = "observation_stale"
    OBSERVATION_INVALID = "observation_invalid"
    OBSERVATION_PAIR_MISMATCH = "observation_pair_mismatch"
    STORE_IDENTITY_MISMATCH = "store_identity_mismatch"
    INVENTORY_ITEM_MISSING = "inventory_item_missing"
    INVENTORY_ITEM_UNTRACKED = "inventory_item_untracked"
    INVENTORY_LEVEL_MISSING = "inventory_level_missing"
    ACTIVATION_SUPERSEDED = "activation_superseded"
    CONFIRMATION_REQUIRED = "confirmation_required"
    PREVIEW_REQUIRED = "preview_required"
    PREVIEW_STALE = "preview_stale"
    GENERATION_MISSING = "generation_missing"
    STALE_GENERATION = "stale_generation"
    INVALID_QUANTITY = "invalid_quantity"
    CAS_PRECONDITION_MISSING = "cas_precondition_missing"
    CAS_PRECONDITION_STALE = "cas_precondition_stale"
    CAS_RETRY_EXHAUSTED = "cas_retry_exhausted"
    OPERATION_SCOPE_CONFLICT = "operation_scope_conflict"
    UNCERTAIN_REQUIRES_READBACK = "uncertain_requires_readback"


def _mapping_value(
    value: InventoryMappingSnapshot | Mapping[str, Any] | None,
) -> InventoryMappingSnapshot | None:
    if value is None or isinstance(value, InventoryMappingSnapshot):
        return value
    return InventoryMappingSnapshot.from_mapping(value)


def _observation_value(
    value: InventoryPairObservation | Mapping[str, Any] | None,
) -> InventoryPairObservation | None:
    if value is None or isinstance(value, InventoryPairObservation):
        return value
    return InventoryPairObservation.from_mapping(value)


@dataclass(frozen=True, slots=True)
class AdmissionDecision:
    """A pure, auditable answer to "may this mutation be admitted?"""

    allowed: bool
    reason: str | AdmissionReason
    message: str
    operation_scope_key: str | None
    preview_fingerprint: str | None = None
    retryable: bool = False
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        reason = self.reason.value if isinstance(self.reason, AdmissionReason) else self.reason
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("admission reason must be non-empty")
        if not isinstance(self.allowed, bool) or not isinstance(self.retryable, bool):
            raise TypeError("admission booleans must be bool")
        if not isinstance(self.message, str) or not self.message.strip() or len(self.message) > 2048:
            raise ValueError("admission.message must be a bounded non-empty string")
        if self.operation_scope_key is not None:
            if not isinstance(self.operation_scope_key, str) or not self.operation_scope_key.strip() or len(self.operation_scope_key) > 512:
                raise ValueError("operation_scope_key must be a bounded non-empty string")
        if self.preview_fingerprint is not None:
            if not isinstance(self.preview_fingerprint, str) or len(self.preview_fingerprint) != _SHA256_HEX_LENGTH:
                raise ValueError("admission preview_fingerprint must be lowercase SHA-256")
            if any(char not in "0123456789abcdef" for char in self.preview_fingerprint):
                raise ValueError("admission preview_fingerprint must be lowercase SHA-256")
        if not isinstance(self.details, Mapping):
            raise TypeError("admission.details must be an object")
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "details", freeze_value(dict(self.details)))

    @property
    def code(self) -> str:
        return self.reason

    @property
    def is_admitted(self) -> bool:
        return self.allowed

    def as_dict(self) -> dict[str, Any]:
        return to_plain({
            "allowed": self.allowed,
            "reason": self.reason,
            "message": self.message,
            "operation_scope_key": self.operation_scope_key,
            "preview_fingerprint": self.preview_fingerprint,
            "retryable": self.retryable,
            "details": self.details,
        })


class InventoryAdmissionPolicy:
    """Evaluate V1-compatible mapping, observation and authority gates."""

    def __init__(self, *, max_observation_age_seconds: int = DEFAULT_MAX_OBSERVATION_AGE_SECONDS) -> None:
        if isinstance(max_observation_age_seconds, bool) or not isinstance(max_observation_age_seconds, int) or max_observation_age_seconds <= 0:
            raise ValueError("max_observation_age_seconds must be positive")
        self.max_observation_age_seconds = max_observation_age_seconds

    @staticmethod
    def operation_scope(payload: InventoryMutationPayload) -> str:
        if not isinstance(payload, InventoryMutationPayload):
            raise TypeError("payload must be InventoryMutationPayload")
        return payload.operation_scope_key

    def _blocked(
        self,
        payload: InventoryMutationPayload,
        reason: AdmissionReason,
        message: str,
        *,
        fingerprint: str | None = None,
        retryable: bool = False,
        **details: Any,
    ) -> AdmissionDecision:
        return AdmissionDecision(False, reason, message, payload.operation_scope_key, fingerprint, retryable, details)

    def evaluate(
        self,
        payload: InventoryMutationPayload,
        *,
        mapping: InventoryMappingSnapshot | Mapping[str, Any] | None = None,
        observation: InventoryPairObservation | Mapping[str, Any] | None = None,
        current_generation: int | None = None,
        current_store_identity: str | None = None,
        active_operation_scopes: Sequence[str] = (),
        preview_fingerprint: str | None = None,
        now: datetime | None = None,
        requested_scope_key: str | None = None,
        remote_uncertain: bool = False,
    ) -> AdmissionDecision:
        if not isinstance(payload, InventoryMutationPayload):
            raise TypeError("payload must be InventoryMutationPayload")
        scope = payload.operation_scope_key
        if requested_scope_key is not None and requested_scope_key != scope:
            return self._blocked(payload, AdmissionReason.STORE_SCOPE_MISMATCH, "Operation scope is server-derived and does not match this item/location pair.")
        if remote_uncertain:
            return self._blocked(payload, AdmissionReason.UNCERTAIN_REQUIRES_READBACK, "An uncertain remote write must be read back before another mutation is admitted.")

        mapping = _mapping_value(payload.mapping if mapping is None else mapping)
        if mapping is None:
            return self._blocked(payload, AdmissionReason.MAPPING_MISSING, "An explicit Shopify-to-Odoo location mapping is required before inventory work.")
        if mapping.store_id != payload.store_id or mapping.company_id != payload.company_id:
            return self._blocked(payload, AdmissionReason.STORE_SCOPE_MISMATCH, "The location mapping belongs to a different store or company.")
        if mapping.shopify_location_gid != payload.location_gid:
            return self._blocked(payload, AdmissionReason.MAPPING_INVALID, "The location mapping is not for the exact requested Shopify location.")
        if not mapping.one_to_one or not mapping.active:
            return self._blocked(payload, AdmissionReason.MAPPING_INVALID, "The inventory location mapping is not an active one-to-one mapping.")
        if not mapping.push_enabled:
            return self._blocked(payload, AdmissionReason.MAPPING_DISABLED, "Inventory push is disabled for this mapped location.")

        observation = _observation_value(payload.observation if observation is None else observation)
        if observation is None:
            return self._blocked(payload, AdmissionReason.OBSERVATION_MISSING, "A current Shopify item/location observation is required before mutation.")
        live_identity = current_store_identity if current_store_identity is not None else payload.current_store_identity
        if observation.store_identity != payload.expected_store_identity or (live_identity is not None and observation.store_identity != live_identity):
            return self._blocked(payload, AdmissionReason.STORE_IDENTITY_MISMATCH, "The Shopify observation belongs to a different store identity.")
        if observation.inventory_item_gid != payload.inventory_item_gid or observation.location_gid != payload.location_gid:
            return self._blocked(payload, AdmissionReason.OBSERVATION_PAIR_MISMATCH, "The Shopify observation does not prove the exact requested item/location pair.")
        if not observation.fresh:
            return self._blocked(payload, AdmissionReason.OBSERVATION_STALE, "The Shopify pair observation is stale and must be refreshed.")
        if observation.observed_at is not None and now is not None:
            now = _utc(now, "now")
            observed_at = _timestamp(observation.observed_at, "observation.observed_at", strict=False)
            if observed_at is None or observed_at > now or (now - observed_at).total_seconds() > self.max_observation_age_seconds:
                return self._blocked(payload, AdmissionReason.OBSERVATION_STALE, "The Shopify pair observation is outside the current freshness window.")
        if not observation.item_exists:
            return self._blocked(payload, AdmissionReason.INVENTORY_ITEM_MISSING, "The Shopify InventoryItem identity no longer exists; manual review is required.")
        if observation.tracked is not True:
            return self._blocked(payload, AdmissionReason.INVENTORY_ITEM_UNTRACKED, "The Shopify InventoryItem is not tracked; no quantity mutation is safe.")

        current_generation = payload.current_generation if current_generation is None else current_generation
        if current_generation is None:
            return self._blocked(payload, AdmissionReason.GENERATION_MISSING, "The current connection generation is required before mutation admission.")
        if isinstance(current_generation, bool) or not isinstance(current_generation, int) or current_generation < 0:
            raise ValueError("current_generation must be a non-negative integer")
        if current_generation != payload.expected_generation:
            return self._blocked(payload, AdmissionReason.STALE_GENERATION, "The store connection generation changed; refresh the intent before sending.")

        operation = payload.operation
        target = payload.normalized_target_quantity
        if target is None:
            return self._blocked(payload, AdmissionReason.INVALID_QUANTITY, "Inventory quantity must be a non-negative integral value; meaningful fractions are refused.")
        if operation == INVENTORY_ACTIVATE_OPERATION:
            if target != 0:
                return self._blocked(payload, AdmissionReason.INVALID_QUANTITY, "Inventory activation preserves the V1 zero baseline.")
            if observation.level_exists:
                return self._blocked(payload, AdmissionReason.ACTIVATION_SUPERSEDED, "A Shopify InventoryLevel already exists; activation must not reset it.")
        else:
            if not observation.level_exists:
                return self._blocked(payload, AdmissionReason.INVENTORY_LEVEL_MISSING, "A Shopify InventoryLevel is absent; activate the exact pair before setting quantities.")
            if payload.change_from_quantity is None:
                return self._blocked(payload, AdmissionReason.CAS_PRECONDITION_MISSING, "A strict current Shopify quantity is required as changeFromQuantity.")
            if observation.available != payload.change_from_quantity:
                return self._blocked(payload, AdmissionReason.CAS_PRECONDITION_STALE, "The Shopify available quantity changed since the CAS snapshot; refresh before sending.")

        # A confirmed row is not automatically a continuous mutation: the
        # first mutation after confirmation still needs the preview evidence.
        # ``is_first_push`` also treats every unconfirmed state as first-push,
        # so a caller cannot bypass the guard by clearing the convenience
        # flag.  Later continuous payloads explicitly set
        # ``first_push_required=False`` and retain the V1 fresh-observation /
        # CAS gates without requiring a stale preview artifact.
        if payload.is_first_push and (
            payload.first_push_state != "confirmed"
            or payload.first_push_confirmation is None
        ):
            return self._blocked(
                payload,
                AdmissionReason.CONFIRMATION_REQUIRED,
                "A server-attested Administrator first-push confirmation is required before any Odoo-authoritative write.",
            )
        fingerprint = canonical_preview_fingerprint(replace(payload, mapping=mapping, observation=observation, current_generation=current_generation, current_store_identity=live_identity))
        supplied_fingerprint = payload.preview_fingerprint if preview_fingerprint is None else preview_fingerprint
        if payload.is_first_push:
            if supplied_fingerprint is None:
                return self._blocked(payload, AdmissionReason.PREVIEW_REQUIRED, "A current preview fingerprint is required before mutation admission.", fingerprint=fingerprint)
            if supplied_fingerprint != fingerprint:
                return self._blocked(payload, AdmissionReason.PREVIEW_STALE, "The mapping, observation, generation or target changed since the preview; regenerate it before sending.", fingerprint=fingerprint)
        if payload.cas_retry_ordinal > MAX_CAS_RETRY_ORDINAL:
            return self._blocked(payload, AdmissionReason.CAS_RETRY_EXHAUSTED, "The bounded V1 CAS replacement ceiling has been reached; manual review is required.", fingerprint=fingerprint)
        if scope in ({active_operation_scopes} if isinstance(active_operation_scopes, str) else set(active_operation_scopes or ())):
            return self._blocked(payload, AdmissionReason.OPERATION_SCOPE_CONFLICT, "Another non-terminal inventory operation already owns this exact pair scope.", fingerprint=fingerprint)
        return AdmissionDecision(
            True,
            AdmissionReason.ADMITTED,
            "Inventory mutation admitted with exact pair, mapping, observation, generation and preview evidence.",
            scope,
            fingerprint,
            False,
            {
                "operation": operation,
                "target_quantity": target,
                "change_from_quantity": payload.change_from_quantity,
                "first_push_state": payload.first_push_state,
            },
        )


def evaluate_inventory_admission(payload: InventoryMutationPayload, **kwargs: Any) -> AdmissionDecision:
    """Convenience function for application adapters and pure tests."""

    return InventoryAdmissionPolicy().evaluate(payload, **kwargs)


__all__ = [
    "AdmissionDecision",
    "AdmissionReason",
    "InventoryAdmissionPolicy",
    "evaluate_inventory_admission",
]
