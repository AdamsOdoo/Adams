"""Pure application composition for the P14 fulfillment mutation slice."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from ..domain.fulfillment_admission import FulfillmentAdmissionPolicy
from ..domain.fulfillment_mutation import AdmissionDecision, FulfillmentMutationPayload
from ..domain.fulfillment_readback import FulfillmentReadback, evaluate_fulfillment_readback


@runtime_checkable
class FulfillmentMutationRequest(Protocol):
    """Application-owned request seam implemented by the Shopify adapter."""

    @property
    def operation_key(self) -> str:
        ...


@runtime_checkable
class FulfillmentMutationResult(Protocol):
    """Application-owned normalized result seam implemented by an adapter."""

    @property
    def outcome(self) -> str:
        ...


class FulfillmentMutationRequestPort(Protocol):
    def build_request(self, payload: FulfillmentMutationPayload, *, idempotency_key: str | None = None) -> FulfillmentMutationRequest:
        ...


@dataclass(frozen=True, slots=True)
class PreparedFulfillmentMutation:
    """An admitted payload and immutable request, without transport."""

    decision: AdmissionDecision
    request: FulfillmentMutationRequest | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.decision, AdmissionDecision):
            raise TypeError("decision must be AdmissionDecision")
        if self.request is not None and not isinstance(self.request, FulfillmentMutationRequest):
            raise TypeError("request must implement FulfillmentMutationRequest or be None")
        if self.decision.allowed != (self.request is not None):
            raise ValueError("admitted decisions require a request")


class FulfillmentMutationApplication:
    """Admit and construct requests; a runtime owns durable sequencing."""

    def __init__(self, adapter: FulfillmentMutationRequestPort, *, policy: FulfillmentAdmissionPolicy | None = None) -> None:
        if not callable(getattr(adapter, "build_request", None)):
            raise TypeError("adapter must provide build_request")
        self.adapter = adapter
        self.policy = policy or FulfillmentAdmissionPolicy()

    def admit(self, payload: FulfillmentMutationPayload, **kwargs: Any) -> AdmissionDecision:
        return self.policy.evaluate(payload, **kwargs)

    def prepare(self, payload: FulfillmentMutationPayload, *, idempotency_key: str | None = None, **admission_kwargs: Any) -> PreparedFulfillmentMutation:
        decision = self.admit(payload, **admission_kwargs)
        if not decision.allowed:
            return PreparedFulfillmentMutation(decision)
        return PreparedFulfillmentMutation(decision, self.adapter.build_request(payload, idempotency_key=idempotency_key))

    def execute_once(self, request: FulfillmentMutationRequest) -> FulfillmentMutationResult:
        raise RuntimeError("Direct fulfillment transport is fenced; use FulfillmentMutationRuntime with a durable ledger.")

    def evaluate_readback(self, payload: FulfillmentMutationPayload, observation: Mapping[str, Any] | None, *, inconclusive_count: int | None = None) -> FulfillmentReadback:
        return evaluate_fulfillment_readback(payload, observation, inconclusive_count=inconclusive_count)


FulfillmentMutationHandler = FulfillmentMutationApplication

__all__ = [
    "FulfillmentMutationApplication",
    "FulfillmentMutationHandler",
    "FulfillmentMutationRequest",
    "FulfillmentMutationRequestPort",
    "FulfillmentMutationResult",
    "PreparedFulfillmentMutation",
]
