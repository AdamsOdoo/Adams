"""Pure P14 durable-intent runtime: commit, one send, then readback."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from shopify_connector_core.domain.immutability import freeze_value, to_plain
from shopify_connector_core.integration.shopify.mutation_contracts import (
    MutationOutcome,
    MutationRequest,
    MutationResult,
    MutationTransportError,
)

from ..domain.fulfillment_mutation import (
    ACTIVE_RUN_STATES,
    FULFILLMENT_ALL_RUNTIME_MODE,
    FULFILLMENT_CREATE_OPERATION,
    FULFILLMENT_RUNTIME_MODE,
    FULFILLMENT_RUNTIME_MODES,
    FULFILLMENT_TRACKING_UPDATE_OPERATION,
    NotificationEvidence,
    FulfillmentBindingEvidence,
    FulfillmentLocationEvidence,
    MAX_INCONCLUSIVE_READS,
    _domain,
    derive_fulfillment_operation_scope,
)
from ..domain.fulfillment_readback import FulfillmentReadback, ReadbackOutcome


MUTATION_OPERATIONS = frozenset((
    "fulfillment.create",
    "fulfillment.tracking_update",
))
RUNTIME_DECISIONS = frozenset((
    "applied", "blocked", "duplicate", "failed_clean", "not_applied",
    "uncertain", "verification_required", "manual_review",
))


class FulfillmentRuntimeError(ValueError):
    """Safe runtime contract error; raw transport details never escape."""

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not code or not code.replace("_", "").replace("-", "").isalnum():
            raise ValueError("runtime error code must be a safe token")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("runtime error message must be non-empty")
        self.code = code[:128]
        self.message = message[:2048]
        super().__init__(self.message)


def _positive(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise FulfillmentRuntimeError("invalid_admission", f"{field_name} must be a positive integer.")


def _generation(value: Any, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FulfillmentRuntimeError("invalid_admission", f"{field_name} must be a non-negative integer.")


def _safe_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise FulfillmentRuntimeError("invalid_evidence", f"{field_name} must be an object.")
    try:
        return freeze_value(dict(value))
    except (TypeError, ValueError) as exc:
        raise FulfillmentRuntimeError("invalid_evidence", f"{field_name} is not JSON-safe.") from exc


def _claim_token(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 256:
        raise FulfillmentRuntimeError("claim_failed", "The durable claim token is malformed.")
    return value


@dataclass(frozen=True, slots=True)
class FulfillmentRuntimeAdmission:
    runtime_mode: str
    store_id: int
    company_id: int
    expected_connection_generation: int
    current_connection_generation: int
    expected_configuration_generation: int
    current_configuration_generation: int
    expected_store_identity: str
    current_store_identity: str | None = None
    current_store_id: int | None = None
    current_company_id: int | None = None
    store_state: str = "connected"
    run_state: str = "admitted"
    cancel_requested: bool = False
    fulfillment_domain_enabled: bool = True
    notification_evidence: NotificationEvidence | Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.runtime_mode not in FULFILLMENT_RUNTIME_MODES:
            raise FulfillmentRuntimeError("runtime_mode", "Fulfillment mutations require fulfillment or all mode.")
        for value, name in ((self.store_id, "store_id"), (self.company_id, "company_id")):
            _positive(value, name)
        for value, name in ((self.expected_connection_generation, "expected_connection_generation"), (self.current_connection_generation, "current_connection_generation"), (self.expected_configuration_generation, "expected_configuration_generation"), (self.current_configuration_generation, "current_configuration_generation")):
            _generation(value, name)
        try:
            _domain(self.expected_store_identity, "expected_store_identity")
            if self.current_store_identity is not None:
                _domain(self.current_store_identity, "current_store_identity")
        except ValueError as exc:
            raise FulfillmentRuntimeError("store_identity", "The Shopify store identity is malformed.") from exc
        if self.current_store_id is not None:
            _positive(self.current_store_id, "current_store_id")
        if self.current_company_id is not None:
            _positive(self.current_company_id, "current_company_id")
        if self.store_state != "connected":
            raise FulfillmentRuntimeError("store_state", "Fulfillment mutations require a connected store.")
        if self.run_state not in ACTIVE_RUN_STATES:
            raise FulfillmentRuntimeError("run_state", "Fulfillment mutations require an active run.")
        if not isinstance(self.cancel_requested, bool) or self.cancel_requested:
            raise FulfillmentRuntimeError("cancel_requested", "A cancelled run cannot admit a fulfillment mutation.")
        if self.fulfillment_domain_enabled is not True:
            raise FulfillmentRuntimeError("domain_disabled", "The fulfillment domain is not enabled.")
        evidence = NotificationEvidence.from_value(self.notification_evidence)
        if evidence is None:
            raise FulfillmentRuntimeError("notification_evidence_missing", "Explicit notification evidence is required at runtime admission.")
        if evidence.effective != evidence.expected_effective:
            raise FulfillmentRuntimeError("notification_mismatch", "Notification evidence is not consistent with its confirmed store setting.")
        object.__setattr__(self, "notification_evidence", evidence)
        if self.expected_connection_generation != self.current_connection_generation:
            raise FulfillmentRuntimeError("stale_generation", "The store connection generation changed.")
        if self.expected_configuration_generation != self.current_configuration_generation:
            raise FulfillmentRuntimeError("stale_configuration_generation", "The fulfillment configuration generation changed.")
        if (self.current_store_id if self.current_store_id is not None else self.store_id) != self.store_id or (self.current_company_id if self.current_company_id is not None else self.company_id) != self.company_id:
            raise FulfillmentRuntimeError("tenant_mismatch", "The current store/company does not own this intent.")
        if (self.current_store_identity if self.current_store_identity is not None else self.expected_store_identity) != self.expected_store_identity:
            raise FulfillmentRuntimeError("store_identity_mismatch", "The Shopify store identity changed.")

    def assert_request(self, request: MutationRequest) -> None:
        if not isinstance(request, MutationRequest) or request.operation_key not in MUTATION_OPERATIONS:
            raise FulfillmentRuntimeError("operation_not_supported", "The request is not a registered fulfillment mutation.")
        intent = _safe_mapping(request.intent.business_intent, "business_intent")
        preconditions = _safe_mapping(request.intent.preconditions_snapshot, "preconditions_snapshot")
        if intent.get("store_id") != self.store_id or intent.get("company_id") != self.company_id:
            raise FulfillmentRuntimeError("tenant_mismatch", "The durable intent is owned by another store/company.")
        operation = _domain_operation(request.operation_key)
        if intent.get("mutation_domain") != operation:
            raise FulfillmentRuntimeError("operation_not_supported", "The durable intent operation does not match its registered request.")
        if request.intent.operation_scope_key != intent.get("operation_scope_key"):
            raise FulfillmentRuntimeError("scope_mismatch", "The durable intent scope is not canonical.")
        target = intent.get("target_fo_gid") if operation == FULFILLMENT_CREATE_OPERATION else intent.get("fulfillment_gid")
        try:
            canonical_scope = derive_fulfillment_operation_scope(operation, self.store_id, intent.get("picking_id"), target)
        except (TypeError, ValueError) as exc:
            raise FulfillmentRuntimeError("scope_mismatch", "The durable intent scope facts are malformed.") from exc
        if request.intent.operation_scope_key != canonical_scope:
            raise FulfillmentRuntimeError("scope_mismatch", "The durable intent scope is not server-derived.")
        if preconditions.get("expected_connection_generation") != self.expected_connection_generation or preconditions.get("current_connection_generation") != self.current_connection_generation:
            raise FulfillmentRuntimeError("stale_generation", "The request generation does not match the admitted generation.")
        if preconditions.get("expected_configuration_generation") != self.expected_configuration_generation or preconditions.get("current_configuration_generation") != self.current_configuration_generation:
            raise FulfillmentRuntimeError("stale_configuration_generation", "The request configuration generation is stale.")
        if preconditions.get("expected_store_identity") != self.expected_store_identity or preconditions.get("current_store_identity") not in (None, self.expected_store_identity):
            raise FulfillmentRuntimeError("store_identity_mismatch", "The request Shopify store identity is stale.")
        if preconditions.get("runtime_mode") not in FULFILLMENT_RUNTIME_MODES:
            raise FulfillmentRuntimeError("runtime_mode", "The request runtime mode is not allowed.")
        try:
            binding = FulfillmentBindingEvidence.from_value(intent.get("binding_evidence"))
        except (TypeError, ValueError) as exc:
            raise FulfillmentRuntimeError("binding_identity_mismatch", "The durable intent binding identity is malformed.") from exc
        if binding is None or (binding.store_id, binding.company_id, binding.picking_id) != (self.store_id, self.company_id, intent.get("picking_id")) or binding.order_gid != intent.get("order_gid"):
            raise FulfillmentRuntimeError("binding_identity_mismatch", "The durable intent binding identity is not exact.")
        if operation == FULFILLMENT_CREATE_OPERATION and binding.state != "absent":
            raise FulfillmentRuntimeError("duplicate_binding", "A create intent must carry an explicit absent binding proof.")
        if operation == FULFILLMENT_TRACKING_UPDATE_OPERATION and (binding.state != "present" or binding.fulfillment_gid != intent.get("fulfillment_gid")):
            raise FulfillmentRuntimeError("binding_identity_mismatch", "The tracking intent binding identity is not exact.")
        if operation == FULFILLMENT_CREATE_OPERATION:
            try:
                location = FulfillmentLocationEvidence.from_value(preconditions.get("location_evidence"))
            except (TypeError, ValueError) as exc:
                raise FulfillmentRuntimeError("location_evidence_missing", "The create intent location evidence is malformed.") from exc
            if location is None or location.store_id != self.store_id or not location.active or not location.cache_present:
                raise FulfillmentRuntimeError("location_evidence_missing", "The create intent lacks active exact location cache evidence.")
            if not preconditions.get("eligibility_snapshot_complete") or preconditions.get("eligibility_snapshot_store_identity") != self.expected_store_identity or preconditions.get("eligibility_snapshot_order_gid") != intent.get("order_gid"):
                raise FulfillmentRuntimeError("eligibility_snapshot_missing", "The create intent lacks a complete current eligibility snapshot.")
        notify = intent.get("notify_customer")
        evidence = NotificationEvidence.from_value(intent.get("notification_evidence"))
        if not isinstance(notify, bool) or evidence is None or evidence.effective != notify or evidence.expected_effective != notify:
            raise FulfillmentRuntimeError("notification_evidence_missing", "Explicit notify_customer evidence is required.")
        if evidence != NotificationEvidence.from_value(self.notification_evidence) or preconditions.get("notification_evidence") != evidence.as_dict():
            raise FulfillmentRuntimeError("notification_mismatch", "The request notification evidence changed after admission.")


@dataclass(frozen=True, slots=True)
class FulfillmentRuntimeResult:
    decision: str
    operation_key: str
    intent_fingerprint: str
    readback_required: bool
    operation_scope_key: str = ""
    terminal: bool = False
    evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.decision not in RUNTIME_DECISIONS:
            raise FulfillmentRuntimeError("invalid_result", "Unsupported fulfillment runtime decision.")
        if self.operation_key not in MUTATION_OPERATIONS:
            raise FulfillmentRuntimeError("invalid_result", "Fulfillment operation is not allowlisted.")
        if not isinstance(self.intent_fingerprint, str) or not self.intent_fingerprint:
            raise FulfillmentRuntimeError("invalid_result", "The intent fingerprint is required.")
        if not isinstance(self.readback_required, bool) or not isinstance(self.terminal, bool):
            raise FulfillmentRuntimeError("invalid_result", "Runtime flags must be boolean.")
        if not isinstance(self.operation_scope_key, str) or not self.operation_scope_key.strip():
            raise FulfillmentRuntimeError("invalid_result", "The operation scope is required.")
        object.__setattr__(self, "evidence", _safe_mapping(self.evidence, "evidence"))

    def as_dict(self) -> dict[str, Any]:
        return to_plain({"decision": self.decision, "operation_key": self.operation_key, "intent_fingerprint": self.intent_fingerprint, "operation_scope_key": self.operation_scope_key, "readback_required": self.readback_required, "terminal": self.terminal, "evidence": self.evidence})


class FulfillmentIntentLedger(Protocol):
    def find(self, intent_fingerprint: str) -> Mapping[str, Any] | None:
        ...

    def claim_intent(self, request: MutationRequest) -> str | None:
        """Atomically persist the intent and reserve its non-terminal scope."""
        ...

    def claim_transport_attempt(self, intent_fingerprint: str, claim_token: str) -> bool:
        """Atomically mark the one permitted remote transport attempt."""
        ...

    def record_outcome(self, intent_fingerprint: str, outcome: str, evidence: Mapping[str, Any], *, claim_token: str) -> bool:
        """Record a non-terminal/direct outcome while owning the claim."""
        ...

    def settle_outcome(self, intent_fingerprint: str, outcome: str, evidence: Mapping[str, Any]) -> bool:
        """CAS a readback outcome; terminal rows cannot be overwritten."""
        ...

    def increment_inconclusive(self, intent_fingerprint: str) -> int:
        """Atomically increment and return the durable readback count."""
        ...


Readback = Callable[[MutationRequest, MutationResult], FulfillmentReadback]


class FulfillmentMutationRuntime:
    """Durable sequence with no retry and no lock held during transport."""

    def __init__(self, gateway: Any, ledger: FulfillmentIntentLedger) -> None:
        if not callable(getattr(gateway, "execute_once", None)) and not callable(getattr(gateway, "execute", None)):
            raise TypeError("gateway must provide execute_once(request)")
        for method in ("find", "claim_intent", "claim_transport_attempt", "record_outcome", "settle_outcome", "increment_inconclusive"):
            if not callable(getattr(ledger, method, None)):
                raise TypeError(f"ledger is missing {method}")
        self.gateway = gateway
        self.ledger = ledger

    @staticmethod
    def _result_evidence(request: MutationRequest, result: MutationResult | None = None, **extra: Any) -> dict[str, Any]:
        intent = request.intent.business_intent
        evidence = {"operation_key": request.operation_key, "operation_scope_key": request.intent.operation_scope_key, "notify_customer": intent.get("notify_customer"), "notification_evidence": intent.get("notification_evidence")}
        if result is not None:
            evidence.update(to_plain(result.evidence))
            evidence["outcome"] = result.outcome
            if result.error_code:
                evidence["error_code"] = result.error_code
        evidence.update(extra)
        return evidence

    def _runtime_result(self, request: MutationRequest, decision: str, readback_required: bool, *, terminal: bool = False, **evidence: Any) -> FulfillmentRuntimeResult:
        return FulfillmentRuntimeResult(decision, request.operation_key, request.intent.fingerprint, readback_required, request.intent.operation_scope_key, terminal, self._result_evidence(request, **evidence))

    def _record(self, request: MutationRequest, outcome: str, evidence: Mapping[str, Any], *, claim_token: str) -> bool:
        try:
            accepted = self.ledger.record_outcome(request.intent.fingerprint, outcome, evidence, claim_token=claim_token)
        except Exception as exc:
            raise FulfillmentRuntimeError("outcome_record_failed", "Durable fulfillment outcome could not be recorded.") from exc
        if not isinstance(accepted, bool):
            raise FulfillmentRuntimeError("outcome_record_failed", "The ledger did not return an outcome claim result.")
        return accepted

    def _existing(self, request: MutationRequest, existing: Mapping[str, Any], *, marker: str) -> FulfillmentRuntimeResult:
        outcome = existing.get("outcome")
        terminal = bool(existing.get("terminal", outcome in {"applied", "failed_clean", "not_applied", "blocked", "manual_review"}))
        waiting = not terminal
        return self._runtime_result(request, "duplicate", bool(existing.get("readback_required", waiting)), terminal=terminal, ledger=marker, existing_outcome=outcome, existing_evidence=existing.get("evidence", {}))

    def execute(self, request: MutationRequest, admission: FulfillmentRuntimeAdmission, *, readback: Readback | None = None) -> FulfillmentRuntimeResult:
        if not isinstance(admission, FulfillmentRuntimeAdmission):
            raise TypeError("admission must be FulfillmentRuntimeAdmission")
        admission.assert_request(request)
        fingerprint = request.intent.fingerprint
        existing = self.ledger.find(fingerprint)
        if existing is not None:
            return self._existing(request, existing, marker="existing_intent")
        try:
            claim_token = self.ledger.claim_intent(request)
        except Exception as exc:
            raise FulfillmentRuntimeError("intent_claim_failed", "Durable fulfillment intent was not claimed.") from exc
        if claim_token is None:
            existing = self.ledger.find(fingerprint)
            if existing is not None:
                return self._existing(request, existing, marker="concurrent_intent")
            return self._runtime_result(request, "duplicate", True, ledger="operation_scope_conflict")
        _claim_token(claim_token)
        try:
            attempted = self.ledger.claim_transport_attempt(fingerprint, claim_token)
        except Exception as exc:
            raise FulfillmentRuntimeError("transport_claim_failed", "The one permitted fulfillment transport attempt could not be claimed.") from exc
        if attempted is not True:
            existing = self.ledger.find(fingerprint)
            if existing is not None:
                return self._existing(request, existing, marker="transport_claim_conflict")
            return self._runtime_result(request, "duplicate", True, ledger="transport_claim_conflict")
        try:
            call = getattr(self.gateway, "execute_once", None) or getattr(self.gateway, "execute")
            result = call(request)
        except MutationTransportError as exc:
            if exc.after_send is False:
                evidence = self._result_evidence(request, transport="not_sent")
                self._record(request, MutationOutcome.FAILED_CLEAN.value, evidence, claim_token=claim_token)
                return self._runtime_result(request, "failed_clean", False, terminal=True, transport="not_sent")
            evidence = self._result_evidence(request, transport="uncertain")
            self._record(request, MutationOutcome.UNCERTAIN.value, evidence, claim_token=claim_token)
            return self._runtime_result(request, "verification_required", True, transport="uncertain")
        except Exception:
            evidence = self._result_evidence(request, transport="exception")
            self._record(request, MutationOutcome.UNCERTAIN.value, evidence, claim_token=claim_token)
            return self._runtime_result(request, "verification_required", True, transport="uncertain")
        if not isinstance(result, MutationResult):
            evidence = self._result_evidence(request, transport="invalid_result")
            self._record(request, MutationOutcome.UNCERTAIN.value, evidence, claim_token=claim_token)
            return self._runtime_result(request, "verification_required", True, transport="invalid_result")
        if result.outcome == MutationOutcome.FAILED_CLEAN.value:
            evidence = self._result_evidence(request, result)
            self._record(request, result.outcome, evidence, claim_token=claim_token)
            return self._runtime_result(request, "failed_clean", False, terminal=True, result_evidence=evidence)
        evidence = self._result_evidence(request, result)
        self._record(request, MutationOutcome.UNCERTAIN.value, evidence, claim_token=claim_token)
        if readback is None:
            return self._runtime_result(request, "verification_required", True, result_evidence=evidence)
        try:
            verdict = readback(request, result)
        except Exception as exc:
            raise FulfillmentRuntimeError("readback_failed", "Fulfillment readback could not be classified.") from exc
        return self.settle_readback(request, verdict)

    def settle_readback(self, request: MutationRequest, verdict: FulfillmentReadback) -> FulfillmentRuntimeResult:
        if not isinstance(request, MutationRequest):
            raise TypeError("request must be MutationRequest")
        if not isinstance(verdict, FulfillmentReadback):
            raise FulfillmentRuntimeError("invalid_readback", "Readback must return FulfillmentReadback.")
        if verdict.intent_fingerprint != request.intent.fingerprint or verdict.operation != _domain_operation(request.operation_key) or verdict.operation_scope_key != request.intent.operation_scope_key:
            raise FulfillmentRuntimeError("readback_mismatch", "Readback does not identify this fulfillment intent.")
        existing = self.ledger.find(request.intent.fingerprint)
        if existing is not None and bool(existing.get("terminal")):
            return self._existing(request, existing, marker="terminal_race")
        evidence = self._result_evidence(request, readback=verdict.as_dict())
        if verdict.outcome == ReadbackOutcome.APPLIED.value:
            if not self.ledger.settle_outcome(request.intent.fingerprint, "applied", evidence):
                existing = self.ledger.find(request.intent.fingerprint)
                if existing is not None:
                    return self._existing(request, existing, marker="terminal_race")
                raise FulfillmentRuntimeError("readback_race", "The fulfillment intent disappeared during readback settlement.")
            return self._runtime_result(request, "applied", False, terminal=True, readback=verdict.as_dict())
        if verdict.outcome == ReadbackOutcome.NOT_APPLIED.value:
            if not self.ledger.settle_outcome(request.intent.fingerprint, "not_applied", evidence):
                existing = self.ledger.find(request.intent.fingerprint)
                if existing is not None:
                    return self._existing(request, existing, marker="terminal_race")
                raise FulfillmentRuntimeError("readback_race", "The fulfillment intent disappeared during readback settlement.")
            return self._runtime_result(request, "not_applied", False, terminal=True, readback=verdict.as_dict())
        try:
            count = self.ledger.increment_inconclusive(request.intent.fingerprint)
        except Exception as exc:
            raise FulfillmentRuntimeError("readback_count_failed", "The inconclusive readback count could not be persisted.") from exc
        if isinstance(count, bool) or not isinstance(count, int) or count < 1:
            raise FulfillmentRuntimeError("readback_count_failed", "The ledger returned an invalid inconclusive readback count.")
        manual = count >= MAX_INCONCLUSIVE_READS
        evidence = dict(evidence)
        readback_evidence = dict(verdict.as_dict())
        readback_evidence["evidence"] = dict(readback_evidence.get("evidence", {}))
        readback_evidence["evidence"]["inconclusive_read_count"] = count
        readback_evidence["evidence"]["manual_review"] = manual
        evidence["readback"] = readback_evidence
        if not self.ledger.settle_outcome(request.intent.fingerprint, "manual_review" if manual else "uncertain", evidence):
            existing = self.ledger.find(request.intent.fingerprint)
            if existing is not None:
                return self._existing(request, existing, marker="terminal_race")
            raise FulfillmentRuntimeError("readback_race", "The fulfillment intent disappeared during readback settlement.")
        return self._runtime_result(
            request,
            "manual_review" if manual else "uncertain",
            not manual,
            terminal=manual,
            readback=verdict.as_dict(),
        )

    resolve_readback = settle_readback


def _domain_operation(operation_key: str) -> str:
    return FULFILLMENT_CREATE_OPERATION if operation_key == "fulfillment.create" else FULFILLMENT_TRACKING_UPDATE_OPERATION


__all__ = [
    "FulfillmentIntentLedger", "FulfillmentMutationRuntime", "FulfillmentRuntimeAdmission", "FulfillmentRuntimeError", "FulfillmentRuntimeResult", "MUTATION_OPERATIONS", "Readback", "RUNTIME_DECISIONS",
]
