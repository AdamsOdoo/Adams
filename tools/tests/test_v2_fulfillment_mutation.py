"""Dependency-free P14 fulfillment contract, fault and race evidence."""

from __future__ import annotations

import sys
import threading
import time
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _namespace(name: str, path: Path) -> None:
    module = sys.modules.get(name)
    if module is None:
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        module.__package__ = name
        sys.modules[name] = module


for _addon in ("shopify_connector_core", "shopify_connector_fulfillment"):
    _root = ROOT / "addons" / _addon
    _namespace(_addon, _root)
    _namespace(_addon + ".domain", _root / "domain")
    _namespace(_addon + ".application", _root / "application")
    _namespace(_addon + ".integration", _root / "integration")
    _namespace(_addon + ".integration.shopify", _root / "integration" / "shopify")
    _namespace(_addon + ".runtime", _root / "runtime")


from shopify_connector_core.integration.shopify.mutation_contracts import (  # noqa: E402
    MutationOutcome,
    MutationResult,
    MutationTransportError,
)
from shopify_connector_fulfillment.domain.fulfillment_admission import (  # noqa: E402
    FulfillmentAdmissionPolicy,
)
from shopify_connector_fulfillment.domain.fulfillment_mutation import (  # noqa: E402
    FULFILLMENT_CREATE_OPERATION,
    FULFILLMENT_TRACKING_UPDATE_OPERATION,
    AdmissionReason,
    FulfillmentBindingEvidence,
    FulfillmentLocationEvidence,
    FulfillmentMutationPayload,
    NotificationEvidence,
    canonical_fulfillment_fingerprint,
    derive_fulfillment_operation_scope,
    notification_evidence,
)
from shopify_connector_fulfillment.domain.fulfillment_readback import (  # noqa: E402
    FulfillmentReadback,
    ReadbackOutcome,
    evaluate_fulfillment_readback,
)
from shopify_connector_fulfillment.integration.shopify.fulfillment_mutation_adapter import (  # noqa: E402
    FulfillmentMutationRequestAdapter,
)
from shopify_connector_fulfillment.integration.shopify.fulfillment_mutation_gateway import (  # noqa: E402
    FULFILLMENT_MUTATION_REGISTRY,
    FulfillmentMutationGateway,
)
from shopify_connector_fulfillment.runtime.fulfillment_mutation_runtime import (  # noqa: E402
    FulfillmentMutationRuntime,
    FulfillmentRuntimeError,
    FulfillmentRuntimeAdmission,
)
from shopify_connector_fulfillment.application.fulfillment_mutation import (  # noqa: E402
    FulfillmentMutationApplication,
)


SHOP = "p14-demo.myshopify.com"
STORE_ID = 11
COMPANY_ID = 3
PICKING_ID = 77
ORDER = "gid://shopify/Order/100"
FULFILLMENT_ORDER = "gid://shopify/FulfillmentOrder/200"
FO_LINE = "gid://shopify/FulfillmentOrderLineItem/300"
FULFILLMENT = "gid://shopify/Fulfillment/400"
TRACKING = {"company": "Carrier", "number": "TRACK-1", "url": "https://carrier.example/1"}


def _create_payload(**changes) -> FulfillmentMutationPayload:
    values = {
        "store_id": STORE_ID,
        "company_id": COMPANY_ID,
        "expected_connection_generation": 4,
        "expected_store_identity": SHOP,
        "operation": FULFILLMENT_CREATE_OPERATION,
        "picking_id": PICKING_ID,
        "target_gid": FULFILLMENT_ORDER,
        "order_gid": ORDER,
        "line_items_by_fulfillment_order": ({
            "fulfillmentOrderId": FULFILLMENT_ORDER,
            "fulfillmentOrderLineItems": ({"id": FO_LINE, "quantity": 1},),
        },),
        "notify_customer": False,
        "notification_evidence": notification_evidence(False, default_enabled=False, confirmed=False),
        "expected_configuration_generation": 8,
        "current_connection_generation": 4,
        "current_configuration_generation": 8,
        "current_store_identity": SHOP,
        "current_store_id": STORE_ID,
        "current_company_id": COMPANY_ID,
        "binding_evidence": FulfillmentBindingEvidence("absent", STORE_ID, COMPANY_ID, PICKING_ID, ORDER),
        "location_evidence": FulfillmentLocationEvidence("gid://shopify/Location/500", STORE_ID, True, True),
        "fulfillment_order_observations": (_fo_fact(),),
        "eligibility_snapshot_complete": True,
        "eligibility_snapshot_store_identity": SHOP,
        "eligibility_snapshot_order_gid": ORDER,
        "remaining_before": {FO_LINE: 2},
        "snapshot_taken_at": "2026-08-31T00:00:00Z",
    }
    values.update(changes)
    return FulfillmentMutationPayload(**values)


def _tracking_payload(**changes) -> FulfillmentMutationPayload:
    values = {
        "store_id": STORE_ID,
        "company_id": COMPANY_ID,
        "expected_connection_generation": 4,
        "expected_store_identity": SHOP,
        "operation": FULFILLMENT_TRACKING_UPDATE_OPERATION,
        "picking_id": PICKING_ID,
        "target_gid": FULFILLMENT,
        "fulfillment_gid": FULFILLMENT,
        "tracking_info_input": TRACKING,
        "notify_customer": False,
        "notification_evidence": notification_evidence(False, default_enabled=False, confirmed=False),
        "expected_configuration_generation": 8,
        "current_connection_generation": 4,
        "current_configuration_generation": 8,
        "current_store_identity": SHOP,
        "current_store_id": STORE_ID,
        "current_company_id": COMPANY_ID,
        "order_gid": ORDER,
        "binding_evidence": FulfillmentBindingEvidence("present", STORE_ID, COMPANY_ID, PICKING_ID, ORDER, FULFILLMENT),
    }
    values.update(changes)
    return FulfillmentMutationPayload(**values)


def _fo_fact(*, fo_gid=FULFILLMENT_ORDER, line_gid=FO_LINE, status="OPEN", action="CREATE_FULFILLMENT", location="gid://shopify/Location/500", remaining=1):
    return {
        "id": fo_gid,
        "status": status,
        "supportedActions": [{"action": action}] if action else [],
        "assignedLocation": {"location": {"id": location}} if location else None,
        "line_items": [{"id": line_gid, "remainingQuantity": remaining}],
    }


def _admission(**changes) -> FulfillmentRuntimeAdmission:
    values = {
        "runtime_mode": "fulfillment",
        "store_id": STORE_ID,
        "company_id": COMPANY_ID,
        "expected_connection_generation": 4,
        "current_connection_generation": 4,
        "expected_configuration_generation": 8,
        "current_configuration_generation": 8,
        "expected_store_identity": SHOP,
        "notification_evidence": notification_evidence(False, default_enabled=False, confirmed=False),
    }
    values.update(changes)
    return FulfillmentRuntimeAdmission(**values)


class AdmissionTests(unittest.TestCase):
    def test_create_and_tracking_admit_with_explicit_notification_evidence(self):
        policy = FulfillmentAdmissionPolicy()
        create = policy.evaluate(_create_payload())
        tracking = policy.evaluate(_tracking_payload())
        self.assertTrue(create.allowed)
        self.assertTrue(tracking.allowed)
        self.assertEqual(create.reason, AdmissionReason.ADMITTED.value)
        self.assertEqual(create.details["notification_evidence"]["effective"], False)

    def test_all_mode_is_allowed_but_legacy_and_stale_fences_block(self):
        policy = FulfillmentAdmissionPolicy()
        self.assertTrue(policy.evaluate(_create_payload(runtime_mode="all")).allowed)
        self.assertEqual(policy.evaluate(_create_payload(), runtime_mode="legacy").reason, AdmissionReason.MODE_MISMATCH.value)
        self.assertEqual(policy.evaluate(_create_payload(), current_connection_generation=5).reason, AdmissionReason.STALE_GENERATION.value)
        self.assertEqual(policy.evaluate(_create_payload(), current_configuration_generation=9).reason, AdmissionReason.STALE_CONFIGURATION_GENERATION.value)
        self.assertEqual(policy.evaluate(_create_payload(), current_store_id=12).reason, AdmissionReason.STORE_ID_MISMATCH.value)
        self.assertEqual(policy.evaluate(_create_payload(), current_company_id=4).reason, AdmissionReason.COMPANY_ID_MISMATCH.value)
        self.assertEqual(policy.evaluate(_create_payload(), current_store_identity="other.myshopify.com").reason, AdmissionReason.STORE_IDENTITY_MISMATCH.value)

    def test_notification_confirmation_and_missing_evidence_fail_closed(self):
        policy = FulfillmentAdmissionPolicy()
        missing = policy.evaluate(_create_payload(notification_evidence=None))
        self.assertEqual(missing.reason, AdmissionReason.NOTIFICATION_EVIDENCE_MISSING.value)
        unconfirmed = policy.evaluate(_create_payload(notification_evidence=NotificationEvidence(True, True, False), notify_customer=True))
        self.assertEqual(unconfirmed.reason, AdmissionReason.NOTIFICATION_CONFIRMATION_MISSING.value)
        mismatch = policy.evaluate(_create_payload(notification_evidence=NotificationEvidence(False, False, False), notify_customer=True))
        self.assertEqual(mismatch.reason, AdmissionReason.NOTIFICATION_MISMATCH.value)

    def test_v1_fulfillment_order_status_action_location_and_quantity_matrix(self):
        policy = FulfillmentAdmissionPolicy()
        self.assertTrue(policy.evaluate(_create_payload(fulfillment_order_observations=(_fo_fact(),))).allowed)
        for kwargs, expected in (
            ({"status": "ON_HOLD"}, AdmissionReason.FULFILLMENT_ORDER_BLOCKED),
            ({"status": "CANCELLED"}, AdmissionReason.FULFILLMENT_ORDER_INELIGIBLE),
            ({"action": None}, AdmissionReason.FULFILLMENT_ORDER_INELIGIBLE),
            ({"location": None}, AdmissionReason.FULFILLMENT_ORDER_LOCATION),
            ({"remaining": 0}, AdmissionReason.FULFILLMENT_ORDER_QUANTITY),
        ):
            with self.subTest(expected=expected):
                self.assertEqual(policy.evaluate(_create_payload(fulfillment_order_observations=(_fo_fact(**kwargs),))).reason, expected.value)
        other = dict(_fo_fact())
        other["id"] = "gid://shopify/FulfillmentOrder/201"
        other["assignedLocation"] = {"location": {"id": "gid://shopify/Location/501"}}
        second_line = {"id": "gid://shopify/FulfillmentOrderLineItem/301", "quantity": 1}
        other["line_items"] = [{"id": second_line["id"], "remainingQuantity": 1}]
        payload = _create_payload(
            line_items_by_fulfillment_order=(
                _create_payload().line_items_by_fulfillment_order[0],
                {"fulfillmentOrderId": other["id"], "fulfillmentOrderLineItems": (second_line,)},
            ),
            fulfillment_order_observations=(_fo_fact(), other),
        )
        self.assertEqual(policy.evaluate(payload).reason, AdmissionReason.LOCATION_EVIDENCE_MISMATCH.value)

    def test_binding_scope_and_domain_fences(self):
        policy = FulfillmentAdmissionPolicy()
        present = FulfillmentBindingEvidence("present", STORE_ID, COMPANY_ID, PICKING_ID, ORDER, FULFILLMENT)
        absent = FulfillmentBindingEvidence("absent", STORE_ID, COMPANY_ID, PICKING_ID, ORDER)
        self.assertEqual(policy.evaluate(_create_payload(binding_evidence=present)).reason, AdmissionReason.DUPLICATE_BINDING.value)
        self.assertEqual(policy.evaluate(_tracking_payload(binding_evidence=absent)).reason, AdmissionReason.BINDING_MISSING.value)
        self.assertEqual(policy.evaluate(_tracking_payload(tracking_info_input=None)).reason, AdmissionReason.TRACKING_MISSING.value)
        payload = _create_payload()
        self.assertEqual(policy.evaluate(payload, active_operation_scopes=(payload.operation_scope_key,)).reason, AdmissionReason.OPERATION_SCOPE_CONFLICT.value)
        self.assertEqual(policy.evaluate(_create_payload(), fulfillment_domain_enabled=False).reason, AdmissionReason.DOMAIN_DISABLED.value)
        self.assertEqual(policy.evaluate(_create_payload(), remote_uncertain=True).reason, AdmissionReason.UNCERTAIN_REQUIRES_READBACK.value)

    def test_missing_snapshot_location_or_binding_never_admits(self):
        policy = FulfillmentAdmissionPolicy()
        self.assertEqual(policy.evaluate(_create_payload(fulfillment_order_observations=())).reason, AdmissionReason.FULFILLMENT_ORDER_SNAPSHOT_MISSING.value)
        self.assertEqual(policy.evaluate(_create_payload(eligibility_snapshot_complete=False)).reason, AdmissionReason.FULFILLMENT_ORDER_SNAPSHOT_INCOMPLETE.value)
        self.assertEqual(policy.evaluate(_create_payload(location_evidence=FulfillmentLocationEvidence("gid://shopify/Location/500", STORE_ID, False, True))).reason, AdmissionReason.LOCATION_EVIDENCE_MISMATCH.value)
        self.assertEqual(policy.evaluate(_create_payload(binding_evidence=None)).reason, AdmissionReason.BINDING_IDENTITY_MISSING.value)
        self.assertEqual(policy.evaluate(_tracking_payload(binding_evidence=FulfillmentBindingEvidence("present", STORE_ID, COMPANY_ID, PICKING_ID + 1, ORDER, FULFILLMENT))).reason, AdmissionReason.BINDING_IDENTITY_MISMATCH.value)

    def test_any_blocking_sibling_is_rejected_even_if_not_selected(self):
        sibling = _fo_fact(fo_gid="gid://shopify/FulfillmentOrder/201", line_gid="gid://shopify/FulfillmentOrderLineItem/301", status="ON_HOLD")
        result = FulfillmentAdmissionPolicy().evaluate(_create_payload(fulfillment_order_observations=(_fo_fact(), sibling)))
        self.assertEqual(result.reason, AdmissionReason.FULFILLMENT_ORDER_BLOCKED.value)

    def test_create_scope_is_one_per_picking_and_fingerprint_ignores_timestamp(self):
        other_fo = "gid://shopify/FulfillmentOrder/201"
        other_line = "gid://shopify/FulfillmentOrderLineItem/301"
        first = _create_payload()
        second = _create_payload(
            target_gid=other_fo,
            line_items_by_fulfillment_order=({"fulfillmentOrderId": other_fo, "fulfillmentOrderLineItems": ({"id": other_line, "quantity": 1},)},),
            binding_evidence=FulfillmentBindingEvidence("absent", STORE_ID, COMPANY_ID, PICKING_ID, ORDER),
            fulfillment_order_observations=(_fo_fact(fo_gid=other_fo, line_gid=other_line),),
        )
        self.assertEqual(first.operation_scope_key, second.operation_scope_key)
        self.assertEqual(first.operation_scope_key, derive_fulfillment_operation_scope(FULFILLMENT_CREATE_OPERATION, STORE_ID, PICKING_ID))
        self.assertEqual(canonical_fulfillment_fingerprint(_create_payload(snapshot_taken_at="2026-08-31T00:00:00Z")), canonical_fulfillment_fingerprint(_create_payload(snapshot_taken_at="2026-08-31T00:00:01Z")))


class AdapterTests(unittest.TestCase):
    def test_p08_create_wire_preserves_notify_and_has_no_shopify_idempotent_directive(self):
        adapter = FulfillmentMutationRequestAdapter(lambda operation, variables: {})
        request = adapter.build_request(_create_payload(notify_customer=True, notification_evidence=NotificationEvidence(True, True, True)))
        self.assertEqual(request.variables["fulfillment"]["notifyCustomer"], True)
        self.assertNotIn("@idempotent", request.operation.document)
        self.assertEqual(request.intent.business_intent["notification_evidence"]["effective"], True)
        self.assertEqual(request.intent.operation_scope_key, _create_payload().operation_scope_key)

    def test_p08_tracking_wire_preserves_explicit_notify_and_input(self):
        adapter = FulfillmentMutationRequestAdapter(lambda operation, variables: {})
        request = adapter.build_request(_tracking_payload(notify_customer=True, notification_evidence=NotificationEvidence(True, True, True)))
        self.assertEqual(request.variables["notifyCustomer"], True)
        self.assertEqual(request.variables["trackingInfoInput"]["number"], "TRACK-1")
        self.assertEqual(request.readback.operation_key, "fulfillment.node.read")

    def test_frozen_multi_tracking_lists_are_restored_to_wire_lists_strictly(self):
        adapter = FulfillmentMutationRequestAdapter(lambda operation, variables: {})
        request = adapter.build_request(_tracking_payload(tracking_info_input={"numbers": ["A", "B"]}))
        self.assertEqual(list(request.variables["trackingInfoInput"]["numbers"]), ["A", "B"])
        with self.assertRaises(ValueError):
            adapter.build_request(_tracking_payload(tracking_info_input={"numbers": ["A", 3]}))

    def test_application_direct_transport_is_fenced(self):
        app = FulfillmentMutationApplication(FulfillmentMutationRequestAdapter(lambda operation, variables: {}))
        with self.assertRaises(RuntimeError):
            app.execute_once(_request())


class FakeGateway:
    def __init__(self, result=None, *, delay=0):
        self.result = result
        self.delay = delay
        self.calls = []
        self.lock = threading.Lock()

    def execute_once(self, request):
        if self.delay:
            time.sleep(self.delay)
        with self.lock:
            self.calls.append(request)
        if isinstance(self.result, BaseException):
            raise self.result
        result = self.result
        if callable(result):
            return result(request)
        return result or MutationResult(request.operation_key, request.operation_name, MutationOutcome.SUCCEEDED, None, "accepted", payload={"fulfillment": {"id": FULFILLMENT, "status": "SUCCESS"}}, evidence={})


class FakeLedger:
    """A tiny atomic scope/attempt ledger; no lock spans gateway transport."""

    def __init__(self):
        self.rows = {}
        self.events = []
        self.lock = threading.Lock()

    def find(self, fingerprint):
        with self.lock:
            self.events.append(("find", fingerprint))
            row = self.rows.get(fingerprint)
            return dict(row) if row is not None else None

    def claim_intent(self, request):
        with self.lock:
            self.events.append(("claim", request.intent.fingerprint))
            if request.intent.fingerprint in self.rows:
                return None
            scope = request.intent.operation_scope_key
            if any(row.get("operation_scope_key") == scope and not row.get("terminal") for row in self.rows.values()):
                return None
            token = f"claim-{len(self.rows) + 1}"
            self.rows[request.intent.fingerprint] = {"outcome": "in_flight", "readback_required": True, "terminal": False, "operation_scope_key": scope, "claim_token": token, "transport_attempted": False, "inconclusive_read_count": 0, "evidence": {}}
            return token

    def claim_transport_attempt(self, fingerprint, claim_token):
        with self.lock:
            row = self.rows.get(fingerprint)
            self.events.append(("attempt", fingerprint))
            if row is None or row.get("claim_token") != claim_token or row.get("transport_attempted"):
                return False
            row["transport_attempted"] = True
            return True

    def record_outcome(self, fingerprint, outcome, evidence, *, claim_token):
        with self.lock:
            self.events.append(("outcome", outcome))
            row = self.rows.get(fingerprint)
            if row is None or row.get("claim_token") != claim_token or row.get("terminal"):
                return False
            row.update({"outcome": outcome, "readback_required": outcome in {"uncertain", "verification_required"}, "terminal": outcome in {"applied", "failed_clean", "not_applied", "blocked", "manual_review"}, "evidence": dict(evidence)})
            return True

    def settle_outcome(self, fingerprint, outcome, evidence):
        with self.lock:
            self.events.append(("settle", outcome))
            row = self.rows.get(fingerprint)
            if row is None or row.get("terminal"):
                return False
            row.update({"outcome": outcome, "readback_required": outcome == "uncertain", "terminal": outcome in {"applied", "failed_clean", "not_applied", "blocked", "manual_review"}, "evidence": dict(evidence)})
            return True

    def increment_inconclusive(self, fingerprint):
        with self.lock:
            row = self.rows.get(fingerprint)
            if row is None:
                raise KeyError(fingerprint)
            row["inconclusive_read_count"] = row.get("inconclusive_read_count", 0) + 1
            self.events.append(("inconclusive", row["inconclusive_read_count"]))
            return row["inconclusive_read_count"]


class CommitFailureLedger(FakeLedger):
    def claim_intent(self, request):
        raise RuntimeError("fixture commit failure")


def _request(payload=None):
    payload = payload or _create_payload()
    return FulfillmentMutationRequestAdapter(lambda operation, variables: {}).build_request(payload)


def _readback(request, outcome=ReadbackOutcome.APPLIED, **evidence):
    operation = FULFILLMENT_CREATE_OPERATION if request.operation_key == "fulfillment.create" else FULFILLMENT_TRACKING_UPDATE_OPERATION
    return FulfillmentReadback(operation, outcome, request.intent.operation_scope_key, "fixture", "fixture readback", intent_fingerprint=request.intent.fingerprint, fulfillment_gid=FULFILLMENT, evidence=evidence)


class RuntimeTests(unittest.TestCase):
    def _runtime(self, gateway=None, ledger=None):
        return FulfillmentMutationRuntime(gateway or FakeGateway(), ledger or FakeLedger())

    def test_commit_precedes_one_send_and_success_requires_readback(self):
        gateway = FakeGateway()
        ledger = FakeLedger()
        result = self._runtime(gateway, ledger).execute(_request(), _admission())
        self.assertEqual(result.decision, "verification_required")
        self.assertTrue(result.readback_required)
        self.assertEqual(len(gateway.calls), 1)
        self.assertEqual([event[0] for event in ledger.events[:3]], ["find", "claim", "attempt"])
        self.assertEqual(ledger.rows[result.intent_fingerprint]["outcome"], "uncertain")
        self.assertFalse("TRACK-1" in str(result.as_dict()))

    def test_runtime_requires_effective_notification_evidence(self):
        with self.assertRaises(FulfillmentRuntimeError) as raised:
            _admission(notification_evidence=None)
        self.assertEqual(raised.exception.code, "notification_evidence_missing")

    def test_clean_before_send_failure_is_terminal_and_after_send_is_uncertain(self):
        clean = self._runtime(FakeGateway(MutationTransportError(after_send=False)), FakeLedger()).execute(_request(), _admission())
        self.assertEqual(clean.decision, "failed_clean")
        self.assertTrue(clean.terminal)
        after = self._runtime(FakeGateway(MutationTransportError(after_send=True)), FakeLedger()).execute(_request(), _admission())
        self.assertEqual(after.decision, "verification_required")
        self.assertTrue(after.readback_required)

    def test_durable_commit_failure_stops_before_transport(self):
        gateway = FakeGateway()
        with self.assertRaises(FulfillmentRuntimeError) as raised:
            self._runtime(gateway, CommitFailureLedger()).execute(_request(), _admission())
        self.assertEqual(raised.exception.code, "intent_claim_failed")
        self.assertEqual(gateway.calls, [])

    def test_duplicate_intent_and_commit_race_never_send_twice(self):
        gateway = FakeGateway(delay=0.01)
        ledger = FakeLedger()
        runtime = self._runtime(gateway, ledger)
        request = _request()
        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(runtime.execute, request, _admission()) for _ in range(2)]
            results = [future.result(timeout=2) for future in futures]
        self.assertEqual(len(gateway.calls), 1)
        self.assertCountEqual([result.decision for result in results], ["verification_required", "duplicate"])
        self.assertEqual(sum(event[0] == "claim" for event in ledger.events), 1)

    def test_existing_terminal_projection_is_deterministic_and_no_blind_replay(self):
        gateway = FakeGateway()
        ledger = FakeLedger()
        runtime = self._runtime(gateway, ledger)
        request = _request()
        first = runtime.execute(request, _admission(), readback=lambda req, result: _readback(req))
        second = runtime.execute(request, _admission())
        self.assertEqual(first.decision, "applied")
        self.assertEqual(second.decision, "duplicate")
        self.assertTrue(second.terminal)
        self.assertEqual(len(gateway.calls), 1)

    def test_webhook_hint_then_readback_race_has_one_terminal_effect(self):
        gateway = FakeGateway()
        ledger = FakeLedger()
        runtime = self._runtime(gateway, ledger)
        request = _request()
        webhook = runtime.execute(request, _admission(), readback=lambda req, result: _readback(req, ReadbackOutcome.INCONCLUSIVE, webhook_only=True, source="webhook"))
        self.assertEqual(webhook.decision, "uncertain")
        applied = runtime.settle_readback(request, _readback(request))
        late = runtime.settle_readback(request, _readback(request, ReadbackOutcome.INCONCLUSIVE, webhook_only=True, source="webhook"))
        duplicate = runtime.execute(request, _admission())
        self.assertEqual(applied.decision, "applied")
        self.assertEqual(late.decision, "duplicate")
        self.assertEqual(ledger.rows[request.intent.fingerprint]["outcome"], "applied")
        self.assertEqual(duplicate.decision, "duplicate")
        self.assertTrue(duplicate.terminal)
        self.assertEqual(len(gateway.calls), 1)

    def test_same_picking_different_fo_scope_cannot_send_twice(self):
        other_fo = "gid://shopify/FulfillmentOrder/201"
        other_line = "gid://shopify/FulfillmentOrderLineItem/301"
        payload = _create_payload(
            target_gid=other_fo,
            line_items_by_fulfillment_order=({"fulfillmentOrderId": other_fo, "fulfillmentOrderLineItems": ({"id": other_line, "quantity": 1},)},),
            binding_evidence=FulfillmentBindingEvidence("absent", STORE_ID, COMPANY_ID, PICKING_ID, ORDER),
            fulfillment_order_observations=(_fo_fact(fo_gid=other_fo, line_gid=other_line),),
        )
        gateway = FakeGateway()
        ledger = FakeLedger()
        runtime = self._runtime(gateway, ledger)
        first = runtime.execute(_request(), _admission())
        second = runtime.execute(_request(payload), _admission())
        self.assertEqual(first.decision, "verification_required")
        self.assertEqual(second.decision, "duplicate")
        self.assertEqual(second.evidence["ledger"], "operation_scope_conflict")
        self.assertEqual(len(gateway.calls), 1)

    def test_readback_fingerprint_mismatch_is_rejected(self):
        request = _request()
        bad = FulfillmentReadback(FULFILLMENT_CREATE_OPERATION, ReadbackOutcome.APPLIED, request.intent.operation_scope_key, "fixture", "fixture", intent_fingerprint="0" * 64, fulfillment_gid=FULFILLMENT)
        with self.assertRaises(FulfillmentRuntimeError) as raised:
            self._runtime(FakeGateway(), FakeLedger()).settle_readback(request, bad)
        self.assertEqual(raised.exception.code, "readback_mismatch")

    def test_not_applied_readback_is_terminal_but_never_replayed(self):
        gateway = FakeGateway()
        ledger = FakeLedger()
        runtime = self._runtime(gateway, ledger)
        request = _request()
        result = runtime.execute(request, _admission(), readback=lambda req, raw: _readback(req, ReadbackOutcome.NOT_APPLIED))
        retry = runtime.execute(request, _admission())
        self.assertEqual(result.decision, "not_applied")
        self.assertEqual(retry.decision, "duplicate")
        self.assertEqual(len(gateway.calls), 1)

    def test_manual_review_cap_is_terminal_and_notification_evidence_is_persisted(self):
        gateway = FakeGateway()
        ledger = FakeLedger()
        runtime = self._runtime(gateway, ledger)
        request = _request()
        result = runtime.execute(request, _admission(), readback=lambda req, raw: _readback(req, ReadbackOutcome.INCONCLUSIVE, inconclusive_read_count=999))
        self.assertEqual(result.decision, "uncertain")
        self.assertFalse(result.terminal)
        result = runtime.settle_readback(request, _readback(request, ReadbackOutcome.INCONCLUSIVE, manual_review=True))
        self.assertEqual(result.decision, "uncertain")
        result = runtime.settle_readback(request, _readback(request, ReadbackOutcome.INCONCLUSIVE, manual_review=True))
        self.assertEqual(result.decision, "manual_review")
        self.assertTrue(result.terminal)
        self.assertFalse(result.readback_required)
        persisted = ledger.rows[request.intent.fingerprint]["evidence"]
        self.assertIn("notification_evidence", persisted)
        self.assertEqual(persisted["notification_evidence"]["effective"], False)


class ReadbackTests(unittest.TestCase):
    def test_create_tracking_and_no_tracking_readbacks_are_exact(self):
        tracked = _create_payload(tracking_info=TRACKING)
        tracked_observation = {"independent_readback": True, "store_identity": SHOP, "order_gid": ORDER, "fulfillment_gid": FULFILLMENT, "fulfillment_order_ids": [FULFILLMENT_ORDER], "fulfillments": [{"id": FULFILLMENT, "status": "SUCCESS", "trackingInfo": TRACKING}], "remaining_after": {FO_LINE: 1}}
        self.assertEqual(evaluate_fulfillment_readback(tracked, tracked_observation).outcome, ReadbackOutcome.APPLIED.value)
        no_tracking = _create_payload(remaining_before={FO_LINE: 2})
        no_tracking_observation = {"independent_readback": True, "store_identity": SHOP, "order_gid": ORDER, "fulfillment_gid": FULFILLMENT, "fulfillment_order_ids": [FULFILLMENT_ORDER], "fulfillments": [{"id": FULFILLMENT, "status": "SUCCESS"}], "remaining_after": {FO_LINE: 1}}
        self.assertEqual(evaluate_fulfillment_readback(no_tracking, no_tracking_observation).outcome, ReadbackOutcome.APPLIED.value)

    def test_duplicate_or_webhook_only_readback_is_inconclusive(self):
        payload = _create_payload(tracking_info=TRACKING)
        rows = [{"id": FULFILLMENT, "status": "SUCCESS", "trackingInfo": TRACKING, "fulfillmentOrderId": FULFILLMENT_ORDER}, {"id": "gid://shopify/Fulfillment/401", "status": "SUCCESS", "trackingInfo": TRACKING, "fulfillmentOrderId": FULFILLMENT_ORDER}]
        duplicate = evaluate_fulfillment_readback(payload, {"independent_readback": True, "store_identity": SHOP, "order_gid": ORDER, "fulfillment_gid": FULFILLMENT, "fulfillment_order_ids": [FULFILLMENT_ORDER], "remaining_after": {FO_LINE: 1}, "fulfillments": rows})
        webhook = evaluate_fulfillment_readback(payload, {"source": "webhook", "webhook_only": True, "fulfillment_gid": FULFILLMENT})
        self.assertEqual(duplicate.outcome, ReadbackOutcome.INCONCLUSIVE.value)
        self.assertEqual(webhook.reason, "webhook_hint_only")
        self.assertFalse(webhook.safe_to_replay)

    def test_tracking_readback_identity_and_cancelled_fences(self):
        payload = _tracking_payload()
        exact = evaluate_fulfillment_readback(payload, {"independent_readback": True, "store_identity": SHOP, "order_gid": ORDER, "id": FULFILLMENT, "status": "SUCCESS", "trackingInfo": TRACKING})
        cancelled = evaluate_fulfillment_readback(payload, {"independent_readback": True, "store_identity": SHOP, "order_gid": ORDER, "id": FULFILLMENT, "status": "CANCELLED", "trackingInfo": TRACKING})
        self.assertEqual(exact.outcome, ReadbackOutcome.APPLIED.value)
        self.assertEqual(cancelled.outcome, ReadbackOutcome.INCONCLUSIVE.value)
        self.assertFalse(cancelled.safe_to_replay)

    def test_inconclusive_cap_sets_manual_review_evidence(self):
        result = evaluate_fulfillment_readback(_create_payload(), None, inconclusive_count=3)
        self.assertEqual(result.outcome, ReadbackOutcome.INCONCLUSIVE.value)
        self.assertTrue(result.evidence["manual_review"])

    def test_readback_requires_independent_store_order_and_exact_line_identity(self):
        payload = _create_payload(tracking_info=TRACKING)
        base = {"fulfillment_gid": FULFILLMENT, "fulfillment_order_ids": [FULFILLMENT_ORDER], "fulfillments": [{"id": FULFILLMENT, "status": "SUCCESS", "trackingInfo": TRACKING}], "remaining_after": {FO_LINE: 1}}
        self.assertEqual(evaluate_fulfillment_readback(payload, dict(base, independent_readback=True, store_identity=SHOP)).reason, "order_identity_mismatch")
        self.assertEqual(evaluate_fulfillment_readback(payload, dict(base, independent_readback=True, store_identity=SHOP, order_gid=ORDER)).outcome, ReadbackOutcome.APPLIED.value)
        unrelated = dict(base, independent_readback=True, store_identity=SHOP, order_gid=ORDER, fulfillments=[{"id": "gid://shopify/Fulfillment/999", "status": "SUCCESS", "trackingInfo": TRACKING}])
        self.assertEqual(evaluate_fulfillment_readback(payload, unrelated).outcome, ReadbackOutcome.INCONCLUSIVE.value)
        self.assertEqual(evaluate_fulfillment_readback(payload, dict(base, store_identity=SHOP, order_gid=ORDER)).reason, "independent_readback_missing")

    def test_malformed_remote_tracking_is_not_string_coerced(self):
        payload = _create_payload(tracking_info=TRACKING)
        observation = {"independent_readback": True, "store_identity": SHOP, "order_gid": ORDER, "fulfillment_gid": FULFILLMENT, "fulfillment_order_ids": [FULFILLMENT_ORDER], "remaining_after": {FO_LINE: 1}, "fulfillments": [{"id": FULFILLMENT, "status": "SUCCESS", "trackingInfo": {"company": "Carrier", "number": 1, "url": "https://carrier.example/1"}}]}
        self.assertEqual(evaluate_fulfillment_readback(payload, observation).outcome, ReadbackOutcome.INCONCLUSIVE.value)


class DeterministicStressTests(unittest.TestCase):
    def test_2000_exact_candidate_intents_are_stable_and_unique(self):
        policy = FulfillmentAdmissionPolicy()
        fingerprints = []
        for index in range(2000):
            order = f"gid://shopify/Order/{1000 + index}"
            fo = f"gid://shopify/FulfillmentOrder/{2000 + index}"
            line = f"gid://shopify/FulfillmentOrderLineItem/{3000 + index}"
            payload = _create_payload(
                picking_id=1000 + index,
                order_gid=order,
                target_gid=fo,
                line_items_by_fulfillment_order=({"fulfillmentOrderId": fo, "fulfillmentOrderLineItems": ({"id": line, "quantity": 1},)},),
                binding_evidence=FulfillmentBindingEvidence("absent", STORE_ID, COMPANY_ID, 1000 + index, order),
                fulfillment_order_observations=(_fo_fact(fo_gid=fo, line_gid=line),),
                eligibility_snapshot_order_gid=order,
                remaining_before={line: 2},
            )
            self.assertTrue(policy.evaluate(payload).allowed)
            fingerprints.append(canonical_fulfillment_fingerprint(payload))
        self.assertEqual(len(fingerprints), 2000)
        self.assertEqual(len(set(fingerprints)), 2000)


if __name__ == "__main__":
    unittest.main()
