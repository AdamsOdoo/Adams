"""Fault and contract tests for the bounded P10 coordinator shell."""

from __future__ import annotations

import json
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"
if "shopify_connector_core" not in sys.modules:
    package = types.ModuleType("shopify_connector_core")
    package.__path__ = [str(CORE)]
    package.__package__ = "shopify_connector_core"
    sys.modules["shopify_connector_core"] = package

from shopify_connector_core.runtime.contracts import (  # noqa: E402
    NeedsReview,
    NeedsVerification,
    Retryable,
    Succeeded,
)
from shopify_connector_core.runtime.p10_coordinator import (  # noqa: E402
    CLAIM_TRANSACTION,
    ClaimedWork,
    FINALIZE_TRANSACTION,
    ReadOnlyAdmissionRequest,
    ReadOnlyCoordinator,
    ReadOnlyHandlerRegistry,
    ReadOnlyHandlerSpec,
    READ_ONLY_OPERATION_KINDS,
    RuntimeBoundaryError,
    admit_read_only,
)
from shopify_connector_core.runtime.p10_priority import MAX_CLAIM_BATCH  # noqa: E402


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def claim(job_id=1, handler_key="core.read", *, worker="worker:test", mutation=False):
    return ClaimedWork(
        job_id=job_id,
        store_id=1,
        attempt_no=1,
        claim_token=str(uuid4()),
        worker_ref=worker,
        handler_key=handler_key,
        lane="interactive",
        expected_generation=4,
        payload={"page": 1, "workflow": "core", "operation": "read.test"},
        mutation=mutation,
    )


def handler_spec(handler_key, handler, **values):
    values.setdefault("allowed_workflows", ("core",))
    values.setdefault("allowed_operations", ("read.test",))
    return ReadOnlyHandlerSpec(handler_key, handler, **values)


class FakeRepository:
    def __init__(self, claims=()):
        self.claims = tuple(claims)
        self.events = []
        self.finalized = []
        self.fail_finalize = False

    def claim_due(self, *, now, worker_ref, limit, phase, handler_keys):
        self.events.append((
            "claim", now, worker_ref, limit, phase, tuple(handler_keys),
        ))
        return self.claims

    def finalize_attempt(self, *, claim, result, finished_at, phase):
        self.events.append(("finalize", claim.job_id, finished_at, phase))
        if self.fail_finalize:
            raise RuntimeError("database unavailable")
        self.finalized.append((claim, result))


class TestClaimedWork(unittest.TestCase):
    def test_claim_is_immutable_json_safe_and_read_only(self):
        value = claim()
        with self.assertRaises(TypeError):
            value.payload["new"] = True  # type: ignore[index]
        with self.assertRaises((TypeError, AttributeError)):
            value.job_id = 2  # type: ignore[misc]
        with self.assertRaises(ValueError):
            claim(mutation=True)
        with self.assertRaises(ValueError):
            ClaimedWork(1, 1, 1, "not-a-token", "worker", "core.read", "interactive", 0)


class TestCoordinator(unittest.TestCase):
    def registry(self, handler):
        return ReadOnlyHandlerRegistry((handler_spec("core.read", handler),))

    def test_claim_then_handler_then_finalize_order_is_explicit(self):
        repo = FakeRepository((claim(),))
        events = []

        def handler(item):
            events.append(("handler", item.job_id, len(repo.finalized)))
            return Succeeded({"rows": 1})

        report = ReadOnlyCoordinator(repo, self.registry(handler), "worker:test").run_once(now=NOW)
        self.assertEqual(report.claimed_count, 1)
        self.assertEqual(report.finalized_count, 1)
        self.assertEqual(events, [("handler", 1, 0)])
        self.assertEqual([item[0] for item in repo.events], ["claim", "finalize"])
        self.assertEqual(repo.events[0][4], CLAIM_TRANSACTION)
        self.assertEqual(repo.events[1][3], FINALIZE_TRANSACTION)
        self.assertEqual(repo.events[0][5], ("core.read",))
        self.assertEqual(report.items[0].outcome, "succeeded")
        json.dumps(report.as_dict())

    def test_handler_outcomes_are_durable_and_not_replayed_by_coordinator(self):
        outcomes = iter((
            Retryable("shopify_throttling_rate_limit", NOW + timedelta(seconds=30)),
            NeedsVerification(7, "readback"),
            NeedsReview("mapping_missing", "Map the record"),
        ))
        claims = tuple(claim(index, worker="worker:test") for index in range(1, 4))
        repo = FakeRepository(claims)
        report = ReadOnlyCoordinator(
            repo,
            self.registry(lambda _item: next(outcomes)),
            "worker:test",
            max_batch=3,
        ).run_once(now=NOW, limit=3)
        self.assertEqual(
            [item.outcome for item in report.items],
            ["retryable", "verification_required", "manual_review"],
        )
        self.assertEqual(len(repo.finalized), 3)

    def test_malformed_retry_preserves_a_known_source_error_class(self):
        repo = FakeRepository((claim(),))
        ReadOnlyCoordinator(
            repo,
            self.registry(lambda _item: Retryable(
                "shopify_throttling_rate_limit", NOW,
            )),
            "worker:test",
        ).run_once(now=NOW)
        result = repo.finalized[0][1]
        self.assertIsInstance(result, NeedsReview)
        self.assertEqual(result.reason_code, "invalid_retry_schedule")
        self.assertEqual(
            result.error_class, "shopify_throttling_rate_limit",
        )

    def test_unknown_retry_class_is_normalized_without_persisting_it(self):
        repo = FakeRepository((claim(),))
        ReadOnlyCoordinator(
            repo,
            self.registry(lambda _item: Retryable(
                "unregistered_remote_error", NOW + timedelta(seconds=30),
            )),
            "worker:test",
        ).run_once(now=NOW)
        result = repo.finalized[0][1]
        self.assertIsInstance(result, NeedsReview)
        self.assertEqual(result.reason_code, "unknown_error_class")
        self.assertEqual(result.error_class, "unknown_system_error")

    def test_unknown_or_raising_handler_fails_closed_to_manual_review(self):
        unknown_repo = FakeRepository((claim(handler_key="core.unknown"),))
        unknown = ReadOnlyCoordinator(
            unknown_repo, self.registry(lambda _item: Succeeded()), "worker:test"
        ).run_once(now=NOW)
        self.assertEqual(unknown.items[0].reason_code, "unknown_read_handler")
        raising_repo = FakeRepository((claim(),))
        raising = ReadOnlyCoordinator(
            raising_repo,
            self.registry(lambda _item: (_ for _ in ()).throw(RuntimeError("secret payload"))),
            "worker:test",
        ).run_once(now=NOW)
        self.assertEqual(raising.items[0].reason_code, "read_handler_exception")
        self.assertNotIn("secret payload", str(raising.as_dict()))

    def test_handler_is_never_called_for_a_different_run_contract(self):
        invoked = []
        item = claim()
        mismatched = ClaimedWork(
            job_id=item.job_id,
            store_id=item.store_id,
            attempt_no=item.attempt_no,
            claim_token=item.claim_token,
            worker_ref=item.worker_ref,
            handler_key=item.handler_key,
            lane=item.lane,
            expected_generation=item.expected_generation,
            payload={"workflow": "product", "operation": "product.import.scan"},
        )
        repo = FakeRepository((mismatched,))
        report = ReadOnlyCoordinator(
            repo,
            self.registry(lambda _item: invoked.append(True) or Succeeded()),
            "worker:test",
        ).run_once(now=NOW)
        self.assertEqual(invoked, [])
        self.assertEqual(report.items[0].reason_code, "handler_run_mismatch")
        self.assertIsInstance(repo.finalized[0][1], NeedsReview)

    def test_claim_batch_is_bounded_and_identity_is_checked(self):
        too_many = FakeRepository(tuple(claim(index) for index in range(1, MAX_CLAIM_BATCH + 2)))
        coordinator = ReadOnlyCoordinator(
            too_many,
            self.registry(lambda _item: Succeeded()),
            "worker:test",
        )
        with self.assertRaises(RuntimeBoundaryError):
            coordinator.run_once(now=NOW)
        foreign = FakeRepository((claim(worker="worker:other"),))
        with self.assertRaises(RuntimeBoundaryError):
            ReadOnlyCoordinator(
                foreign, self.registry(lambda _item: Succeeded()), "worker:test"
            ).run_once(now=NOW)
        duplicate = claim(1)
        duplicate_repo = FakeRepository((duplicate, duplicate))
        with self.assertRaises(RuntimeBoundaryError):
            ReadOnlyCoordinator(
                duplicate_repo, self.registry(lambda _item: Succeeded()), "worker:test"
            ).run_once(now=NOW)

    def test_finalization_failure_is_not_reported_as_success(self):
        repo = FakeRepository((claim(),))
        repo.fail_finalize = True
        with self.assertRaises(RuntimeBoundaryError):
            ReadOnlyCoordinator(
                repo, self.registry(lambda _item: Succeeded()), "worker:test"
            ).run_once(now=NOW)

    def test_admission_requires_explicit_read_only_handler(self):
        handlers = self.registry(lambda _item: Succeeded())
        request = ReadOnlyAdmissionRequest(
            runtime_mode="read_only",
            handler_key="core.read",
            store_id=1,
            company_id=1,
            expected_generation=0,
        )
        self.assertEqual(admit_read_only(request, handlers).action, "admit")
        cancelled = ReadOnlyAdmissionRequest(
            runtime_mode="read_only",
            handler_key="core.read",
            store_id=1,
            company_id=1,
            expected_generation=0,
            cancel_requested=True,
        )
        self.assertEqual(admit_read_only(cancelled, handlers).action, "reject")
        self.assertEqual(
            admit_read_only(
                ReadOnlyAdmissionRequest(
                    runtime_mode="read_only",
                    handler_key="core.other",
                    store_id=1,
                    company_id=1,
                    expected_generation=0,
                ),
                handlers,
            ).reason_code,
            "unknown_read_handler",
        )
        with self.assertRaises(ValueError):
            ReadOnlyAdmissionRequest("execute", "core.read", 1, 1, 0)

    def test_mutation_handlers_cannot_enter_registry(self):
        with self.assertRaises(ValueError):
            handler_spec("core.write", lambda _item: Succeeded(), mutation=True)
        with self.assertRaises(ValueError):
            ReadOnlyHandlerRegistry(tuple(
                handler_spec("core.read", lambda _item: Succeeded())
                for _ in range(MAX_CLAIM_BATCH + 1)
            ))
        registry = ReadOnlyHandlerRegistry()
        for index in range(MAX_CLAIM_BATCH):
            registry.register(handler_spec(
                "core.read.%d" % index, lambda _item: Succeeded(),
            ))
        with self.assertRaises(ValueError):
            registry.register(handler_spec(
                "core.read.too_many", lambda _item: Succeeded(),
            ))

    def test_handler_registration_has_explicit_read_operation_kind(self):
        self.assertEqual(
            READ_ONLY_OPERATION_KINDS,
            frozenset(("diagnostic", "import", "scan", "reconciliation")),
        )
        specs = tuple(
            handler_spec(
                "core.%s" % kind,
                lambda _item: Succeeded(),
                operation_kind=kind,
            )
            for kind in sorted(READ_ONLY_OPERATION_KINDS)
        )
        registry = ReadOnlyHandlerRegistry(specs)
        self.assertEqual(registry.keys(), tuple(spec.handler_key for spec in specs))
        with self.assertRaises(ValueError):
            handler_spec(
                "core.mutation-kind",
                lambda _item: Succeeded(),
                operation_kind="mutation",
            )

    def test_production_runtime_has_additive_domain_seam_without_domain_imports(self):
        source = (CORE / "models" / "shopify_connector_v2_runtime.py").read_text()
        self.assertIn("_extend_v2_read_only_handler_specs", source)
        self.assertIn("_handler_registry", source)
        self.assertNotIn("_get_v2_read_only_job_types", source)
        self.assertNotIn("_get_v2_read_only_handler_keys", source)
        self.assertNotIn("shopify_connector_product", source)
        self.assertNotIn("shopify_connector_sale", source)
        self.assertNotIn("execute_business(", source)
        self.assertNotIn("requests.", source)


if __name__ == "__main__":
    unittest.main()
