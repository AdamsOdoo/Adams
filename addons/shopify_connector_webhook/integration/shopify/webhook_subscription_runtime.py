"""Pure P11 mutation-runtime boundary for connector-owned subscriptions.

The Odoo adapter uses the same sequence through the existing Layer-2 job
dispatcher.  This small contract makes that sequence executable and testable
without Odoo: validate a store-scoped admission, commit intent, invoke one
P08 gateway call, and settle certainty only from an optional readback.

No class in this module reads credentials, performs HTTP, writes an ORM row or
retries a remote operation.  A ledger supplied by the caller is the durable
intent boundary; a readback supplied by the caller is read-only evidence.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from odoo.addons.shopify_connector_core.domain.immutability import freeze_value, to_plain
from odoo.addons.shopify_connector_core.domain.runtime_modes import runtime_mode_includes
from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
    MutationOutcome,
    MutationRequest,
    MutationResult,
)

from .webhook_subscription_mutation_gateway import (
    WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
    WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
)


RUNTIME_MODE = "subscriptions"
ACTIVE_RUN_STATES = frozenset(("admitted", "running", "waiting"))
MUTATION_OPERATIONS = frozenset((
    WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
    WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
))
RUNTIME_DECISIONS = frozenset((
    "applied",
    "blocked",
    "duplicate",
    "failed_clean",
    "not_applied",
    "uncertain",
    "verification_required",
))
READBACK_VERDICTS = frozenset((
    "applied",
    "blocked",
    "inconclusive",
    "not_applied",
))


class SubscriptionRuntimeError(ValueError):
    """A runtime admission, ledger or readback contract is invalid."""

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not code or not code.replace("_", "").isalnum():
            raise ValueError("runtime error code must be a safe token")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("runtime error message must be non-empty")
        self.code = code
        self.message = message[:2048]
        super().__init__(self.message)


def _positive_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise SubscriptionRuntimeError(
            "invalid_admission", f"{field_name} must be a positive integer."
        )
    return value


def _generation(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SubscriptionRuntimeError(
            "invalid_admission", f"{field_name} must be a non-negative integer."
        )
    return value


def _safe_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SubscriptionRuntimeError(
            "invalid_evidence", f"{field_name} must be a JSON object."
        )
    try:
        return freeze_value(dict(value))
    except (TypeError, ValueError) as exc:
        raise SubscriptionRuntimeError(
            "invalid_evidence", f"{field_name} is not JSON-safe."
        ) from exc


@dataclass(frozen=True, slots=True)
class SubscriptionRuntimeAdmission:
    """Immutable store/run snapshot checked before intent or transport."""

    runtime_mode: str
    store_id: int
    company_id: int
    expected_connection_generation: int
    current_connection_generation: int
    expected_configuration_generation: int
    current_configuration_generation: int
    store_state: str = "connected"
    run_state: str = "admitted"
    cancel_requested: bool = False

    def __post_init__(self) -> None:
        if not runtime_mode_includes(self.runtime_mode, RUNTIME_MODE):
            raise SubscriptionRuntimeError(
                "runtime_mode",
                "Subscription mutations require subscriptions capability.",
            )
        _positive_int(self.store_id, "store_id")
        _positive_int(self.company_id, "company_id")
        _generation(self.expected_connection_generation, "expected_connection_generation")
        _generation(self.current_connection_generation, "current_connection_generation")
        _generation(self.expected_configuration_generation, "expected_configuration_generation")
        _generation(self.current_configuration_generation, "current_configuration_generation")
        if self.store_state != "connected":
            raise SubscriptionRuntimeError(
                "store_state", "Subscription mutations require a connected store."
            )
        if self.run_state not in ACTIVE_RUN_STATES:
            raise SubscriptionRuntimeError(
                "run_state", "Subscription mutations require an active run."
            )
        if not isinstance(self.cancel_requested, bool):
            raise SubscriptionRuntimeError(
                "invalid_admission", "cancel_requested must be boolean."
            )
        if self.cancel_requested:
            raise SubscriptionRuntimeError(
                "cancel_requested", "A cancelled run cannot admit a mutation."
            )
        if self.expected_connection_generation != self.current_connection_generation:
            raise SubscriptionRuntimeError(
                "stale_generation", "The store connection generation changed."
            )
        if self.expected_configuration_generation != self.current_configuration_generation:
            raise SubscriptionRuntimeError(
                "stale_generation", "The store configuration generation changed."
            )


@dataclass(frozen=True, slots=True)
class SubscriptionReadback:
    """One safe readback verdict; raw Shopify rows never cross this type."""

    verdict: str
    reason: str
    ownership: str = "connector"
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.verdict not in READBACK_VERDICTS:
            raise SubscriptionRuntimeError(
                "invalid_readback", "Unsupported subscription readback verdict."
            )
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise SubscriptionRuntimeError(
                "invalid_readback", "Readback reason must be non-empty."
            )
        if not isinstance(self.ownership, str) or not self.ownership.strip():
            raise SubscriptionRuntimeError(
                "invalid_readback", "Readback ownership must be non-empty."
            )
        if self.verdict == "applied" and self.ownership != "connector":
            raise SubscriptionRuntimeError(
                "invalid_readback", "Only connector-owned evidence may be applied."
            )
        object.__setattr__(self, "evidence", _safe_mapping(self.evidence, "evidence"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "reason": self.reason[:2048],
            "ownership": self.ownership[:64],
            "evidence": to_plain(self.evidence),
        }


@dataclass(frozen=True, slots=True)
class SubscriptionRuntimeResult:
    """Immutable outcome returned by one runtime pass."""

    decision: str
    operation_key: str
    intent_fingerprint: str
    readback_required: bool
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision not in RUNTIME_DECISIONS:
            raise SubscriptionRuntimeError(
                "invalid_result", "Unsupported subscription runtime decision."
            )
        if self.operation_key not in MUTATION_OPERATIONS:
            raise SubscriptionRuntimeError(
                "invalid_result", "Subscription runtime operation is not allowlisted."
            )
        if not isinstance(self.intent_fingerprint, str) or not self.intent_fingerprint:
            raise SubscriptionRuntimeError(
                "invalid_result", "The intent fingerprint is required."
            )
        if not isinstance(self.readback_required, bool):
            raise SubscriptionRuntimeError(
                "invalid_result", "readback_required must be boolean."
            )
        object.__setattr__(self, "evidence", _safe_mapping(self.evidence, "evidence"))

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "operation_key": self.operation_key,
            "intent_fingerprint": self.intent_fingerprint,
            "readback_required": self.readback_required,
            "evidence": to_plain(self.evidence),
        }


class SubscriptionIntentLedger(Protocol):
    """Durable-intent port used by the pure runtime and fake-ledger tests."""

    def find(self, intent_fingerprint: str) -> Mapping[str, Any] | None:
        ...

    def commit_intent(self, request: MutationRequest) -> bool:
        ...

    def record_outcome(
        self,
        intent_fingerprint: str,
        outcome: str,
        evidence: Mapping[str, Any],
    ) -> None:
        ...


Readback = Callable[[MutationRequest, MutationResult], SubscriptionReadback]


class SubscriptionMutationRuntime:
    """Execute one admitted subscription mutation without blind replay."""

    def __init__(self, gateway: Any, ledger: SubscriptionIntentLedger) -> None:
        if not callable(getattr(gateway, "execute", None)):
            raise TypeError("gateway must provide execute(request)")
        for method in ("find", "commit_intent", "record_outcome"):
            if not callable(getattr(ledger, method, None)):
                raise TypeError("ledger is missing %s" % method)
        self.gateway = gateway
        self.ledger = ledger

    @staticmethod
    def _evidence(result: MutationResult) -> dict[str, Any]:
        evidence = dict(to_plain(result.evidence))
        evidence.update({
            "operation_key": result.operation_key,
            "outcome": result.outcome,
        })
        if result.error_code:
            evidence["error_code"] = result.error_code
        return evidence

    def execute(
        self,
        request: MutationRequest,
        admission: SubscriptionRuntimeAdmission,
        *,
        readback: Readback | None = None,
    ) -> SubscriptionRuntimeResult:
        if not isinstance(request, MutationRequest):
            raise TypeError("request must be MutationRequest")
        if request.operation_key not in MUTATION_OPERATIONS:
            raise SubscriptionRuntimeError(
                "operation_not_supported", "Only subscription mutations are admitted."
            )
        # Admission is intentionally repeated at the execution boundary so a
        # caller cannot commit an intent using a stale store/run snapshot.
        if not isinstance(admission, SubscriptionRuntimeAdmission):
            raise TypeError("admission must be SubscriptionRuntimeAdmission")
        fingerprint = request.intent.fingerprint
        existing = self.ledger.find(fingerprint)
        if existing is not None:
            return SubscriptionRuntimeResult(
                "duplicate",
                request.operation_key,
                fingerprint,
                bool(existing.get("readback_required", True)),
                {"ledger": "existing_intent"},
            )
        try:
            committed = self.ledger.commit_intent(request)
        except Exception as exc:
            # A failed durable commit is a local failure.  No delegate call is
            # made and the exception text never becomes operator evidence.
            raise SubscriptionRuntimeError(
                "intent_commit_failed", "Durable mutation intent was not committed."
            ) from exc
        if not committed:
            return SubscriptionRuntimeResult(
                "duplicate",
                request.operation_key,
                fingerprint,
                True,
                {"ledger": "concurrent_intent"},
            )

        result = self.gateway.execute(request)
        if not isinstance(result, MutationResult):
            raise SubscriptionRuntimeError(
                "invalid_result", "The mutation gateway returned an invalid result."
            )
        evidence = self._evidence(result)
        if result.outcome == MutationOutcome.FAILED_CLEAN.value:
            self.ledger.record_outcome(fingerprint, result.outcome, evidence)
            return SubscriptionRuntimeResult(
                "failed_clean", request.operation_key, fingerprint, False, evidence
            )

        # A successful GraphQL payload is still only an acknowledgement.  The
        # durable state remains uncertain until the readback proves exact
        # topic/callback/API/format/filter identity (or exact absence on delete).
        self.ledger.record_outcome(fingerprint, MutationOutcome.UNCERTAIN.value, evidence)
        if readback is None:
            return SubscriptionRuntimeResult(
                "verification_required", request.operation_key, fingerprint, True, evidence
            )
        try:
            observation = readback(request, result)
        except SubscriptionRuntimeError:
            raise
        except Exception as exc:
            raise SubscriptionRuntimeError(
                "readback_failed", "Subscription readback could not be classified."
            ) from exc
        if not isinstance(observation, SubscriptionReadback):
            raise SubscriptionRuntimeError(
                "invalid_readback", "Readback must return SubscriptionReadback."
            )
        evidence["readback"] = observation.as_dict()
        if observation.verdict == "applied":
            self.ledger.record_outcome(fingerprint, "applied", evidence)
            return SubscriptionRuntimeResult(
                "applied", request.operation_key, fingerprint, False, evidence
            )
        if observation.verdict == "not_applied":
            self.ledger.record_outcome(fingerprint, "not_applied", evidence)
            return SubscriptionRuntimeResult(
                "not_applied", request.operation_key, fingerprint, False, evidence
            )
        if observation.verdict == "blocked":
            self.ledger.record_outcome(fingerprint, "blocked", evidence)
            return SubscriptionRuntimeResult(
                "blocked", request.operation_key, fingerprint, False, evidence
            )
        return SubscriptionRuntimeResult(
            "uncertain", request.operation_key, fingerprint, True, evidence
        )


__all__ = [
    "ACTIVE_RUN_STATES",
    "MUTATION_OPERATIONS",
    "RUNTIME_MODE",
    "SubscriptionIntentLedger",
    "SubscriptionMutationRuntime",
    "SubscriptionReadback",
    "SubscriptionRuntimeAdmission",
    "SubscriptionRuntimeError",
    "SubscriptionRuntimeResult",
]
