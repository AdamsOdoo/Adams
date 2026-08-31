"""Dependency-free P12 inventory admission, adapter and readback tests.

The fake ledger is deliberately the only remote-shaped test double.  It is
wrapped by the stable P08 ``InventoryMutationGateway`` so these tests prove
the vertical slice does not add a second transport call or a blind retry.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _namespace(name: str, path: Path) -> None:
    package = sys.modules.get(name)
    if package is None:
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        package.__package__ = name
        sys.modules[name] = package


_namespace("odoo", ROOT)
_namespace("odoo.addons", ROOT / "addons")

for _addon in ("shopify_connector_core", "shopify_connector_inventory"):
    _root = ROOT / "addons" / _addon
    _prefix = "odoo.addons." + _addon
    _namespace(_prefix, _root)
    _namespace(_prefix + ".domain", _root / "domain")
    _namespace(_prefix + ".integration", _root / "integration")
    _namespace(_prefix + ".integration.shopify", _root / "integration" / "shopify")
    _namespace(_prefix + ".application", _root / "application")


from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (  # noqa: E402
    MutationOutcome,
    MutationTransportError,
)
from odoo.addons.shopify_connector_inventory.application.inventory_mutation import (  # noqa: E402
    InventoryMutationApplication,
    _build_attested_confirmation,
)
from odoo.addons.shopify_connector_inventory.integration.shopify.inventory_mutation_adapter import (  # noqa: E402
    InventoryMutationAdapterError,
    InventoryMutationRequestAdapter,
)
from odoo.addons.shopify_connector_inventory.domain.inventory_coalescing import (  # noqa: E402
    CoalescingAction,
    decide_inventory_coalescing,
)
from odoo.addons.shopify_connector_inventory.domain.inventory_admission import (  # noqa: E402
    AdmissionReason,
    InventoryAdmissionPolicy,
)
from odoo.addons.shopify_connector_inventory.domain.inventory_mutation import (  # noqa: E402
    FirstPushConfirmation,
    InventoryMappingSnapshot,
    InventoryMutationPayload,
    InventoryPairScope,
    InventoryPairObservation,
    canonical_preview_fingerprint,
    derive_inventory_operation_scope,
)
from odoo.addons.shopify_connector_inventory.domain.inventory_readback import (  # noqa: E402
    ReadbackOutcome,
    evaluate_inventory_readback,
)


ITEM = "gid://shopify/InventoryItem/10"
LOCATION = "gid://shopify/Location/20"
OTHER_LOCATION = "gid://shopify/Location/21"
LEVEL = "gid://shopify/InventoryLevel/30"
DOMAIN = "p12-test.myshopify.com"
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)
SCOPE = InventoryPairScope(7, ITEM, LOCATION)


def _confirmation(*, confirmation_id=701, actor_uid=42, confirmed_at=NOW, evidence_ref="first-push/701"):
    # The application-owned private factory models the trusted
    # application/integration adapter; ordinary domain callers cannot mint an
    # accepted attestation by calling the DTO constructor or a classmethod.
    return _build_attested_confirmation(confirmation_id, actor_uid, confirmed_at, evidence_ref)


class FakeLedger:
    """One-call P08 delegate; it may return a response or a transport fault."""

    def __init__(self, response):
        self.response = response
        self.calls = []

    def execute(self, operation, variables):
        self.calls.append((operation, variables))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def _mapping(location_gid=LOCATION):
    return InventoryMappingSnapshot(
        store_id=7,
        mapping_id=70,
        company_id=3,
        shopify_location_gid=location_gid,
        odoo_location_id=700,
    )


def _observation(
    *,
    location_gid=LOCATION,
    level_exists=True,
    available=5,
    updated_at="2026-08-30T11:59:00Z",
    item_exists=True,
    tracked=True,
    fresh=True,
    observed_at=NOW,
):
    return InventoryPairObservation(
        store_identity=DOMAIN,
        item_exists=item_exists,
        tracked=tracked,
        level_exists=level_exists,
        inventory_item_gid=ITEM,
        location_gid=location_gid,
        inventory_level_gid=LEVEL if level_exists else None,
        available=available if level_exists else None,
        updated_at=updated_at if level_exists else None,
        observed_at=observed_at,
        fresh=fresh,
    )


def _payload(
    *,
    operation="inventory_set_quantities",
    target=10,
    change_from=5,
    mapping=_mapping(),
    observation=_observation(),
    state="confirmed",
    generation=4,
    current_generation=4,
    current_store_identity=None,
    fingerprint=True,
    reference="odoo://dbuuid/shopify.connector.job/700",
    first_push_required=False,
    first_push_confirmation=None,
):
    payload = InventoryMutationPayload(
        store_id=7,
        company_id=3,
        expected_generation=generation,
        current_generation=current_generation,
        expected_store_identity=DOMAIN,
        operation=operation,
        inventory_item_gid=ITEM,
        location_gid=LOCATION,
        target_quantity=target,
        change_from_quantity=change_from,
        reference_document_uri=reference,
        mapping=mapping,
        observation=observation,
        first_push_state=state,
        preview_fingerprint=None,
        current_store_identity=current_store_identity,
        first_push_required=first_push_required,
        first_push_confirmation=first_push_confirmation,
        idempotency_key="p12-idempotency",
        snapshot_taken_at=NOW,
    )
    if fingerprint:
        payload = replace(payload, preview_fingerprint=canonical_preview_fingerprint(payload))
    return payload


class AdmissionTests(unittest.TestCase):
    def test_server_derives_one_exact_pair_scope(self):
        self.assertEqual(
            derive_inventory_operation_scope(7, ITEM, LOCATION),
            "inventory_pair:7:%s:%s" % (ITEM, LOCATION),
        )

    def test_missing_mapping_observation_and_confirmation_fail_closed(self):
        policy = InventoryAdmissionPolicy()
        cases = (
            (_payload(mapping=None), AdmissionReason.MAPPING_MISSING.value),
            (_payload(observation=None), AdmissionReason.OBSERVATION_MISSING.value),
            (_payload(state="previewed"), AdmissionReason.CONFIRMATION_REQUIRED.value),
        )
        for payload, reason in cases:
            with self.subTest(reason=reason):
                decision = policy.evaluate(payload)
                self.assertFalse(decision.allowed)
                self.assertEqual(decision.reason, reason)
        bypass_attempt = replace(_payload(state="pending"), first_push_required=False)
        self.assertEqual(
            policy.evaluate(bypass_attempt).reason,
            AdmissionReason.CONFIRMATION_REQUIRED.value,
        )

    def test_stale_preview_mapping_observation_and_generation_are_rejected(self):
        payload = _payload(first_push_required=True, first_push_confirmation=_confirmation())
        stale = replace(
            payload,
            mapping=_mapping(OTHER_LOCATION),
            observation=_observation(location_gid=OTHER_LOCATION),
        )
        self.assertEqual(
            InventoryAdmissionPolicy().evaluate(stale).reason,
            AdmissionReason.MAPPING_INVALID.value,
        )
        changed_generation = _payload(current_generation=5)
        self.assertEqual(
            InventoryAdmissionPolicy().evaluate(changed_generation).reason,
            AdmissionReason.STALE_GENERATION.value,
        )
        changed_target = replace(payload, target_quantity=11)
        self.assertEqual(
            InventoryAdmissionPolicy().evaluate(changed_target).reason,
            AdmissionReason.PREVIEW_STALE.value,
        )
        refreshed_observation = replace(
            _observation(available=5), observed_at=NOW - timedelta(minutes=1),
        )
        self.assertTrue(
            InventoryAdmissionPolicy().evaluate(payload, observation=refreshed_observation).allowed,
        )
        no_fingerprint = _payload(
            fingerprint=False,
            first_push_required=True,
            first_push_confirmation=_confirmation(),
        )
        self.assertEqual(
            InventoryAdmissionPolicy().evaluate(no_fingerprint).reason,
            AdmissionReason.PREVIEW_REQUIRED.value,
        )
        continuous = replace(no_fingerprint, first_push_required=False)
        self.assertTrue(InventoryAdmissionPolicy().evaluate(continuous).allowed)

    def test_first_push_confirmation_is_attested_and_application_validates_it(self):
        first_push = _payload(
            first_push_required=True,
            first_push_confirmation=_confirmation(),
        )
        with self.assertRaises(ValueError):
            FirstPushConfirmation(701, 42, NOW, "first-push/701")
        self.assertFalse(hasattr(FirstPushConfirmation, "_from_server"))
        for timestamp in ("2026-08-30T12:00:00", "2026-08-30T12:00:00+01:00"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ValueError):
                    FirstPushConfirmation(701, 42, timestamp, "first-push/701", object())
        self.assertEqual(
            InventoryAdmissionPolicy().evaluate(first_push).reason,
            AdmissionReason.ADMITTED.value,
        )

        class Validator:
            def __init__(self, accepted):
                self.accepted = accepted
                self.calls = []

            def validate(self, payload, confirmation):
                self.calls.append((payload, confirmation))
                return self.accepted

        adapter = type(
            "Adapter",
            (),
            {
                "build_request": lambda self, payload, **kwargs: type("Request", (), {"operation_key": "inventory.set_quantities"})(),
                "execute_once": lambda self, request: type("Result", (), {"outcome": "succeeded"})(),
            },
        )()
        denied = InventoryMutationApplication(adapter)
        self.assertEqual(denied.admit(first_push).reason, AdmissionReason.CONFIRMATION_REQUIRED.value)
        validator = Validator(True)
        admitted = InventoryMutationApplication(adapter, confirmation_validator=validator)
        self.assertTrue(admitted.admit(first_push).allowed)
        self.assertEqual(len(validator.calls), 1)

    def test_fingerprint_excludes_all_observation_clock_and_freshness_values(self):
        first = _payload(first_push_required=True, first_push_confirmation=_confirmation())
        changed = replace(
            first,
            observation=replace(
                first.observation,
                updated_at="2026-08-30T13:30:00+00:00",
                observed_at="2026-08-30T13:31:00+00:00",
                fresh=False,
            ),
        )
        self.assertEqual(canonical_preview_fingerprint(first), canonical_preview_fingerprint(changed))
        confirmation_clock_changed = replace(
            first,
            first_push_confirmation=_confirmation(confirmed_at="2026-08-30T18:00:00Z"),
        )
        self.assertEqual(canonical_preview_fingerprint(first), canonical_preview_fingerprint(confirmation_clock_changed))

    def test_cas_requires_fresh_exact_observation(self):
        changed = _payload(observation=_observation(available=6))
        decision = InventoryAdmissionPolicy().evaluate(changed)
        self.assertEqual(decision.reason, AdmissionReason.CAS_PRECONDITION_STALE.value)

        stale = _payload(observation=_observation(fresh=False))
        self.assertEqual(
            InventoryAdmissionPolicy().evaluate(stale).reason,
            AdmissionReason.OBSERVATION_STALE.value,
        )
        for observed_at in ("2026-08-30T11:59:00", "2026-08-30T12:59:00+01:00"):
            with self.subTest(observed_at=observed_at):
                invalid_clock = _payload(observation=_observation(observed_at=observed_at))
                self.assertEqual(
                    InventoryAdmissionPolicy().evaluate(invalid_clock, now=NOW).reason,
                    AdmissionReason.OBSERVATION_STALE.value,
                )

    def test_current_store_identity_is_an_admission_precondition(self):
        payload = _payload(current_store_identity="other.myshopify.com")
        decision = InventoryAdmissionPolicy().evaluate(payload)
        self.assertEqual(decision.reason, AdmissionReason.STORE_IDENTITY_MISMATCH.value)

    def test_activation_preserves_zero_and_never_resets_existing_level(self):
        no_level = _payload(
            operation="inventory_activate",
            target=0,
            change_from=None,
            observation=_observation(level_exists=False),
        )
        self.assertTrue(InventoryAdmissionPolicy().evaluate(no_level).allowed)
        existing_level = _payload(operation="inventory_activate", target=0)
        self.assertEqual(
            InventoryAdmissionPolicy().evaluate(existing_level).reason,
            AdmissionReason.ACTIVATION_SUPERSEDED.value,
        )


class CoalescingTests(unittest.TestCase):
    def test_rapid_changes_coalesce_last_value_for_exact_scope(self):
        payload = _payload(target=12)
        decision = decide_inventory_coalescing(
            payload,
            active_operation_scopes=(payload.operation_scope_key,),
            pending_target_quantity=9,
        )
        self.assertEqual(decision.action, CoalescingAction.COALESCE.value)
        self.assertEqual(decision.effective_target_quantity, 12)
        self.assertFalse(decision.safe_to_send)
        other = replace(
            _payload(target=12, mapping=_mapping(OTHER_LOCATION), observation=_observation(location_gid=OTHER_LOCATION)),
            location_gid=OTHER_LOCATION,
        )
        self.assertEqual(
            decide_inventory_coalescing(other, active_operation_scopes=(payload.operation_scope_key,)).action,
            CoalescingAction.ENQUEUE.value,
        )

    def test_uncertain_write_is_never_replayed_by_coalescer(self):
        decision = decide_inventory_coalescing(_payload(), remote_uncertain=True)
        self.assertEqual(decision.action, CoalescingAction.REJECT.value)
        self.assertFalse(decision.safe_to_send)

    def test_observed_zero_is_skipped_even_without_a_persisted_baseline(self):
        payload = _payload(target=0)
        decision = decide_inventory_coalescing(
            payload, current_available=0, last_pushed_available=0, last_pushed_at=None,
        )
        self.assertEqual(decision.action, CoalescingAction.SKIP.value)

    def test_never_pushed_target_without_observation_is_enqueued(self):
        payload = _payload(target=0)
        decision = decide_inventory_coalescing(
            payload, current_available=None, last_pushed_available=0, last_pushed_at=None,
        )
        self.assertEqual(decision.action, CoalescingAction.ENQUEUE.value)

    def test_naive_or_non_utc_pushed_at_cannot_establish_a_baseline(self):
        payload = _payload(target=10)
        for timestamp in ("2026-08-30T12:00:00", "2026-08-30T12:00:00+01:00", "not-a-timestamp"):
            with self.subTest(timestamp=timestamp):
                decision = decide_inventory_coalescing(
                    payload,
                    current_available=None,
                    last_pushed_available=10,
                    last_pushed_at=timestamp,
                )
                self.assertEqual(decision.action, CoalescingAction.ENQUEUE.value)


class AdapterAndLedgerTests(unittest.TestCase):
    def _set_response(self, quantity=10):
        return {"data": {"inventorySetQuantities": {
            "inventoryAdjustmentGroup": {
                "reason": "correction",
                "referenceDocumentUri": "odoo://dbuuid/shopify.connector.job/700",
                "changes": [{"name": "available", "delta": quantity - 5, "quantityAfterChange": quantity}],
            },
            "userErrors": [],
        }}}

    def test_build_is_wire_parity_and_has_no_call_until_execute(self):
        ledger = FakeLedger(self._set_response())
        adapter = InventoryMutationRequestAdapter(ledger, expected_store_id=7)
        request = adapter.build_request(_payload())
        self.assertEqual(ledger.calls, [])
        self.assertEqual(request.operation_key, "inventory.set_quantities")
        self.assertEqual(request.intent.operation_scope_key, "inventory_pair:7:%s:%s" % (ITEM, LOCATION))
        variables = request.variables
        self.assertEqual(variables["input"]["quantities"][0]["quantity"], 10)
        self.assertEqual(variables["input"]["quantities"][0]["changeFromQuantity"], 5)
        result = adapter.execute_once(request)
        self.assertEqual(result.outcome, MutationOutcome.SUCCEEDED.value)
        self.assertEqual(len(ledger.calls), 1)

    def test_timeout_before_and_after_send_are_distinct_and_single_call(self):
        for error, expected_outcome, expected_code in (
            (MutationTransportError(after_send=False), MutationOutcome.FAILED_CLEAN.value, "transport_not_sent"),
            (MutationTransportError(after_send=True), MutationOutcome.UNCERTAIN.value, "shopify_temporary_server_network"),
        ):
            ledger = FakeLedger(error)
            adapter = InventoryMutationRequestAdapter(ledger, expected_store_id=7)
            result = adapter.execute_once(adapter.build_request(_payload()))
            self.assertEqual(result.outcome, expected_outcome)
            self.assertEqual(result.error_code, expected_code)
            self.assertEqual(len(ledger.calls), 1)

    def test_snapshot_timestamp_rejects_malformed_naive_or_non_utc_strings(self):
        adapter = InventoryMutationRequestAdapter(FakeLedger(None), expected_store_id=7)
        for timestamp in (
            "not-a-timestamp",
            "2026-08-30T12:00:00",
            "2026-08-30T12:00:00+01:00",
        ):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(InventoryMutationAdapterError):
                    adapter.build_request(_payload(), snapshot_taken_at=timestamp)

    def test_activation_request_uses_v1_zero_baseline(self):
        ledger = FakeLedger({"data": {"inventoryActivate": {
            "inventoryLevel": {"id": LEVEL, "item": {"id": ITEM}, "location": {"id": LOCATION}, "quantities": [{"name": "available", "quantity": 0}]},
            "userErrors": [],
        }}})
        payload = _payload(
            operation="inventory_activate", target=0, change_from=None,
            observation=_observation(level_exists=False),
        )
        request = InventoryMutationRequestAdapter(ledger, expected_store_id=7).build_request(payload)
        self.assertEqual(request.variables["available"], 0)
        self.assertEqual(InventoryMutationRequestAdapter(ledger, expected_store_id=7).gateway.registry.require_operation("inventory.activate").readback.operation_key, "inventory.pair.read")


class ReadbackTests(unittest.TestCase):
    def test_exact_pair_readback_matrix_for_set_quantities(self):
        payload = _payload()
        applied = evaluate_inventory_readback(payload, _observation(available=10), transport_at=NOW)
        self.assertEqual(applied.outcome, ReadbackOutcome.APPLIED.value)
        unchanged = evaluate_inventory_readback(
            payload,
            _observation(available=5, updated_at="2026-08-30T11:59:00Z"),
            transport_at="2026-08-30T12:00:00Z",
        )
        self.assertEqual(unchanged.outcome, ReadbackOutcome.NOT_APPLIED.value)
        self.assertTrue(unchanged.safe_to_replay)
        ambiguous = evaluate_inventory_readback(payload, _observation(available=7, updated_at=None), transport_at=NOW)
        self.assertEqual(ambiguous.outcome, ReadbackOutcome.INCONCLUSIVE.value)
        self.assertFalse(ambiguous.safe_to_replay)
        malformed_timestamp = evaluate_inventory_readback(
            payload,
            _observation(available=5, updated_at="not-a-timestamp"),
            transport_at=NOW,
        )
        self.assertEqual(malformed_timestamp.outcome, ReadbackOutcome.INCONCLUSIVE.value)
        self.assertFalse(malformed_timestamp.safe_to_replay)
        for timestamp in ("2026-08-30T11:59:00", "2026-08-30T12:59:00+01:00"):
            with self.subTest(timestamp=timestamp):
                non_utc = evaluate_inventory_readback(
                    payload,
                    _observation(available=5, updated_at=timestamp),
                    transport_at=NOW,
                )
                self.assertEqual(non_utc.outcome, ReadbackOutcome.INCONCLUSIVE.value)
                self.assertFalse(non_utc.safe_to_replay)

    def test_wrong_pair_never_proves_absence(self):
        payload = _payload()
        wrong = _observation(location_gid=OTHER_LOCATION)
        result = evaluate_inventory_readback(payload, wrong, transport_at=NOW)
        self.assertEqual(result.outcome, ReadbackOutcome.INCONCLUSIVE.value)
        self.assertFalse(result.exact_pair)
        self.assertFalse(result.safe_to_replay)

    def test_activation_readback_distinguishes_missing_zero_and_unexplained(self):
        payload = _payload(operation="inventory_activate", target=0, change_from=None, observation=_observation(level_exists=False))
        missing = evaluate_inventory_readback(payload, _observation(level_exists=False), transport_at=NOW)
        self.assertEqual(missing.outcome, ReadbackOutcome.NOT_APPLIED.value)
        self.assertTrue(missing.safe_to_replay)
        applied = evaluate_inventory_readback(payload, _observation(available=0), transport_at=NOW)
        self.assertEqual(applied.outcome, ReadbackOutcome.APPLIED.value)
        unexplained = evaluate_inventory_readback(payload, _observation(available=3), transport_at=NOW)
        self.assertEqual(unexplained.outcome, ReadbackOutcome.INCONCLUSIVE.value)


class CompositionTests(unittest.TestCase):
    def test_prepare_calls_no_ledger_and_execute_is_explicit(self):
        ledger = FakeLedger({"data": {"inventorySetQuantities": {
            "inventoryAdjustmentGroup": {
                "reason": "correction",
                "referenceDocumentUri": "odoo://dbuuid/shopify.connector.job/700",
                "changes": [{"name": "available", "quantityAfterChange": 10}],
            },
            "userErrors": [],
        }}})
        payload = _payload()
        app = InventoryMutationApplication(InventoryMutationRequestAdapter(ledger, expected_store_id=7))
        prepared = app.prepare(payload)
        self.assertTrue(prepared.decision.allowed)
        self.assertIsNotNone(prepared.request)
        self.assertEqual(ledger.calls, [])
        app.execute_once(prepared.request)
        self.assertEqual(len(ledger.calls), 1)

    def test_application_request_seam_has_no_integration_contract_dependency(self):
        source = (ROOT / "addons/shopify_connector_inventory/application/inventory_mutation.py").read_text(encoding="utf-8")
        self.assertNotIn("shopify_connector_core.integration", source)

    def test_p12_slice_remains_unwired_from_the_production_addon_initializer(self):
        for relative in (
            "addons/shopify_connector_inventory/__init__.py",
            "addons/shopify_connector_inventory/models/__init__.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertNotIn("inventory_mutation", source, relative)
            self.assertNotIn("InventoryMutationApplication", source, relative)

    def test_uncertain_result_does_not_trigger_hidden_replay(self):
        ledger = FakeLedger(MutationTransportError(after_send=True))
        adapter = InventoryMutationRequestAdapter(ledger, expected_store_id=7)
        request = adapter.build_request(_payload())
        result = adapter.execute_once(request)
        self.assertEqual(result.outcome, MutationOutcome.UNCERTAIN.value)
        self.assertEqual(len(ledger.calls), 1)


if __name__ == "__main__":
    unittest.main()
