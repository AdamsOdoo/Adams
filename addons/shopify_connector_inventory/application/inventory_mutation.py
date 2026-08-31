"""P12 application composition over pure inventory contracts.

The application layer depends on an injected request adapter port.  The
concrete Shopify adapter lives under ``integration/shopify`` so dependency
direction stays explicit: application decides admission and sequencing, while
the integration edge owns the P08 gateway request shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from ..domain.inventory_admission import AdmissionDecision, AdmissionReason, InventoryAdmissionPolicy
from ..domain.inventory_mutation import (
    FirstPushConfirmation,
    InventoryMutationPayload,
    _register_confirmation_capability,
)
from ..domain.inventory_readback import ReadbackDecision, evaluate_inventory_readback


def _make_confirmation_factory():
    """Create the only local constructor for an accepted confirmation.

    The capability is kept in this application-owned closure.  The domain
    value object accepts it by identity, while its ordinary constructor and
    the old public-looking ``_from_server`` helper cannot mint evidence.
    A real Odoo adapter must call this factory only after it has read and
    authorized the durable confirmation row.
    """

    capability = object()
    _register_confirmation_capability(capability)

    def build(
        confirmation_id: int,
        confirmed_by_uid: int,
        confirmed_at: datetime | str,
        evidence_ref: str,
    ) -> FirstPushConfirmation:
        return FirstPushConfirmation(
            confirmation_id,
            confirmed_by_uid,
            confirmed_at,  # type: ignore[arg-type]
            evidence_ref,
            capability,
        )

    return build


# Private on purpose: issuance is an application/integration responsibility,
# not a domain API.  Validation of the durable row still happens at the
# injected ``confirmation_validator`` boundary before a request is prepared.
_build_attested_confirmation = _make_confirmation_factory()


@runtime_checkable
class InventoryMutationRequest(Protocol):
    """Application-owned request seam implemented by an integration adapter."""

    @property
    def operation_key(self) -> str:
        ...


@runtime_checkable
class InventoryMutationResult(Protocol):
    """Application-owned normalized result seam implemented by an adapter."""

    @property
    def outcome(self) -> str:
        ...


def _require_request(value: Any) -> InventoryMutationRequest:
    if not isinstance(value, InventoryMutationRequest):
        raise TypeError("request must implement InventoryMutationRequest")
    operation_key = value.operation_key
    if not isinstance(operation_key, str) or not operation_key.strip():
        raise TypeError("request.operation_key must be a non-empty string")
    return value


def _require_result(value: Any) -> InventoryMutationResult:
    if not isinstance(value, InventoryMutationResult):
        raise TypeError("adapter result must implement InventoryMutationResult")
    outcome = value.outcome
    if not isinstance(outcome, str) or not outcome.strip():
        raise TypeError("result.outcome must be a non-empty string")
    return value


class InventoryMutationRequestPort(Protocol):
    """Request adapter supplied by the integration edge at runtime."""

    def build_request(
        self,
        payload: InventoryMutationPayload,
        *,
        idempotency_key: str | None = None,
        database_uuid: str | None = None,
        job_id: int | None = None,
        reference_document_uri: str | None = None,
        snapshot_taken_at: datetime | str | None = None,
    ) -> InventoryMutationRequest:
        ...

    def execute_once(self, request: InventoryMutationRequest) -> InventoryMutationResult:
        ...


class InventoryFirstPushConfirmationPort(Protocol):
    """Trusted application boundary for server-side confirmation validation."""

    def validate(
        self,
        payload: InventoryMutationPayload,
        confirmation: FirstPushConfirmation,
    ) -> bool:
        """Return true only when durable actor/evidence has been verified."""


@dataclass(frozen=True, slots=True)
class PreparedInventoryMutation:
    """Admission result plus an optional request, with no transport effect."""

    decision: AdmissionDecision
    request: InventoryMutationRequest | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, AdmissionDecision):
            raise TypeError("decision must be AdmissionDecision")
        if self.request is not None:
            _require_request(self.request)
        if self.decision.allowed != (self.request is not None):
            raise ValueError("an admitted decision must have a request and a blocked decision must not")


class InventoryMutationApplication:
    """Compose admission, request construction and verification only."""

    def __init__(
        self,
        adapter: InventoryMutationRequestPort,
        *,
        policy: InventoryAdmissionPolicy | None = None,
        confirmation_validator: InventoryFirstPushConfirmationPort | None = None,
    ) -> None:
        if not callable(getattr(adapter, "build_request", None)) or not callable(getattr(adapter, "execute_once", None)):
            raise TypeError("adapter must provide build_request and execute_once")
        if confirmation_validator is not None and not callable(getattr(confirmation_validator, "validate", None)):
            raise TypeError("confirmation_validator must provide validate(payload, confirmation)")
        self.adapter = adapter
        self.policy = policy or InventoryAdmissionPolicy()
        self.confirmation_validator = confirmation_validator

    def admit(self, payload: InventoryMutationPayload, **kwargs: Any) -> AdmissionDecision:
        if isinstance(payload, InventoryMutationPayload) and payload.is_first_push:
            confirmation = payload.first_push_confirmation
            validator = self.confirmation_validator
            if confirmation is None or validator is None:
                return AdmissionDecision(
                    False,
                    AdmissionReason.CONFIRMATION_REQUIRED,
                    "A trusted application confirmation validator and server-attested first-push evidence are required before sending.",
                    payload.operation_scope_key,
                )
            try:
                validated = validator.validate(payload, confirmation)
            except Exception:
                # A failed validator is an authority failure, not a reason to
                # continue with the side effect.  Keep adapter details out of
                # the public decision.
                validated = False
            if validated is not True:
                return AdmissionDecision(
                    False,
                    AdmissionReason.CONFIRMATION_REQUIRED,
                    "The application could not validate the server-attested first-push confirmation.",
                    payload.operation_scope_key,
                )
        return self.policy.evaluate(payload, **kwargs)

    def prepare(
        self,
        payload: InventoryMutationPayload,
        *,
        idempotency_key: str | None = None,
        database_uuid: str | None = None,
        job_id: int | None = None,
        reference_document_uri: str | None = None,
        snapshot_taken_at: datetime | str | None = None,
        **admission_kwargs: Any,
    ) -> PreparedInventoryMutation:
        decision = self.admit(payload, **admission_kwargs)
        if not decision.allowed:
            return PreparedInventoryMutation(decision)
        request = self.adapter.build_request(
            payload,
            idempotency_key=idempotency_key,
            database_uuid=database_uuid,
            job_id=job_id,
            reference_document_uri=reference_document_uri,
            snapshot_taken_at=snapshot_taken_at,
        )
        return PreparedInventoryMutation(decision, request)

    def execute_once(self, request: InventoryMutationRequest) -> InventoryMutationResult:
        request = _require_request(request)
        return _require_result(self.adapter.execute_once(request))

    def evaluate_readback(
        self,
        payload: InventoryMutationPayload,
        observation: Mapping[str, Any] | Any | None,
        *,
        transport_at: datetime | str | None = None,
    ) -> ReadbackDecision:
        return evaluate_inventory_readback(payload, observation, transport_at=transport_at)


InventoryMutationHandler = InventoryMutationApplication


__all__ = [
    "InventoryMutationApplication",
    "InventoryMutationHandler",
    "InventoryFirstPushConfirmationPort",
    "InventoryMutationRequest",
    "InventoryMutationRequestPort",
    "InventoryMutationResult",
    "PreparedInventoryMutation",
]
