"""Cheap pure tests for P10 safety decisions."""

from __future__ import annotations

import json
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"
if "shopify_connector_core" not in sys.modules:
    package = types.ModuleType("shopify_connector_core")
    package.__path__ = [str(CORE)]
    package.__package__ = "shopify_connector_core"
    sys.modules["shopify_connector_core"] = package

from shopify_connector_core.domain.states import AttemptOutcome, JobState  # noqa: E402
from shopify_connector_core.runtime.p10_decisions import (  # noqa: E402
    DependencyNode,
    RetryObservation,
    StaleOwnerInput,
    StaleOwnerPolicy,
    decide_cancellation,
    decide_dependency,
    decide_retry,
    find_dependency_cycle,
    project_run_state,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class TestDependencies(unittest.TestCase):
    def test_no_dependency_and_satisfied_dependency_are_ready(self):
        self.assertEqual(decide_dependency(None, None).action, "ready")
        decision = decide_dependency(10, "succeeded")
        self.assertEqual(decision.action, "ready")
        self.assertEqual(decision.reason_code, "dependency_satisfied")

    def test_incomplete_dependency_waits_and_terminal_dependency_blocks(self):
        self.assertEqual(decide_dependency(10, "running").action, "wait")
        self.assertEqual(decide_dependency(10, "retry_waiting").action, "wait")
        self.assertEqual(decide_dependency(10, "failed_final").action, "blocked")
        self.assertEqual(decide_dependency(10, "cancelled").action, "blocked")

    def test_unknown_or_inconsistent_dependency_fails_closed(self):
        self.assertEqual(decide_dependency(None, "running").action, "manual_review")
        self.assertEqual(decide_dependency(10, "future_state").action, "manual_review")
        with self.assertRaises(ValueError):
            decide_dependency(True, "succeeded")

    def test_dependency_cycle_detection_is_bounded_and_deterministic(self):
        cycle = find_dependency_cycle([
            DependencyNode(3, 4),
            DependencyNode(4, 5),
            DependencyNode(5, 3),
        ])
        self.assertEqual(cycle, (3, 4, 5))
        self.assertEqual(find_dependency_cycle([DependencyNode(1, 99)]), ())
        with self.assertRaises(ValueError):
            find_dependency_cycle([DependencyNode(index, None) for index in range(1, 6)], max_nodes=4)


class TestCancellation(unittest.TestCase):
    def test_cancellation_is_explicit_and_does_not_claim_remote_undo(self):
        self.assertEqual(
            decide_cancellation("queued", cancel_requested=False).action,
            "not_requested",
        )
        decision = decide_cancellation(
            "queued", cancel_requested=True, remote_outcome="not_attempted"
        )
        self.assertEqual(decision.action, "cancel")
        self.assertEqual(decision.target_state, "cancelled")
        self.assertEqual(
            decide_cancellation("succeeded", cancel_requested=True).action,
            "already_terminal",
        )

    def test_unresolved_or_succeeded_remote_outcome_requires_review(self):
        decision = decide_cancellation(
            "running", cancel_requested=True, remote_outcome="uncertain"
        )
        self.assertEqual(decision.action, "verify")
        self.assertEqual(decision.target_state, "blocked_manual_review")
        decision = decide_cancellation(
            "running", cancel_requested=True, remote_outcome="succeeded"
        )
        self.assertEqual(decision.action, "manual_review")
        with self.assertRaises(TypeError):
            decide_cancellation("running", cancel_requested=1)


class TestRetryPolicy(unittest.TestCase):
    def observation(self, **kwargs):
        values = {
            "error_class": "shopify_throttling_rate_limit",
            "remote_outcome": "not_attempted",
            "retry_count": 0,
            "first_attempt_at": NOW,
            "now": NOW,
        }
        values.update(kwargs)
        return RetryObservation(**values)

    def test_retry_schedule_preserves_locked_exponential_bounds(self):
        decision = decide_retry(self.observation(jitter_fraction=0.2))
        self.assertEqual(decision.action, "retry")
        self.assertEqual(decision.retry_number, 1)
        self.assertEqual(decision.delay_seconds, 36.0)
        self.assertEqual(decision.retry_at, NOW + timedelta(seconds=36))
        decision = decide_retry(self.observation(retry_count=3, jitter_fraction=-0.2))
        self.assertEqual(decision.retry_number, 4)
        self.assertEqual(decision.delay_seconds, 192.0)
        json.dumps(decision.as_dict())

    def test_uncertain_mutation_is_verified_even_for_transient_error(self):
        decision = decide_retry(self.observation(remote_outcome="uncertain"))
        self.assertEqual(decision.action, "verify")
        self.assertEqual(decision.reason_code, "remote_outcome_uncertain")
        self.assertEqual(decide_retry(self.observation(remote_outcome="succeeded")).action, "complete")

    def test_manual_fix_unknown_and_cap_are_never_automatically_retried(self):
        self.assertEqual(
            decide_retry(self.observation(error_class="mapping_missing")).action,
            "manual_fix",
        )
        self.assertEqual(
            decide_retry(self.observation(error_class="not_registered")).action,
            "manual_review",
        )
        self.assertEqual(
            decide_retry(self.observation(retry_count=12)).reason_code,
            "retry_cap_exhausted",
        )
        self.assertEqual(
            decide_retry(self.observation(now=NOW + timedelta(hours=25))).reason_code,
            "retry_window_exhausted",
        )

    def test_retry_inputs_reject_bool_nonfinite_and_invalid_remote_values(self):
        with self.assertRaises((TypeError, ValueError)):
            RetryObservation("x", "not_attempted", True, NOW, NOW)
        with self.assertRaises((TypeError, ValueError)):
            RetryObservation("x", "not_attempted", 0, NOW, NOW, float("nan"))
        with self.assertRaises(ValueError):
            RetryObservation("x", "not_known", 0, NOW, NOW)


class TestStaleOwner(unittest.TestCase):
    def evidence(self, **kwargs):
        values = {
            "job_id": 1,
            "attempt_id": 2,
            "attempt_outcome": AttemptOutcome.RUNNING,
            "claimed_at": NOW - timedelta(seconds=100),
            "heartbeat_at": NOW - timedelta(seconds=100),
            "now": NOW,
            "remote_outcome": "none",
        }
        values.update(kwargs)
        return StaleOwnerInput(**values)

    def test_current_owner_is_kept(self):
        decision = StaleOwnerPolicy().decide(self.evidence())
        self.assertEqual(decision.action, "keep")
        self.assertFalse(decision.owner_lost)

    def test_stale_owner_recovers_only_when_remote_effect_is_certainly_absent(self):
        decision = StaleOwnerPolicy().decide(self.evidence(
            claimed_at=NOW - timedelta(seconds=500),
            heartbeat_at=NOW - timedelta(seconds=500),
            remote_outcome="not_attempted",
        ))
        self.assertEqual(decision.action, "recover")
        self.assertTrue(decision.owner_lost)
        decision = StaleOwnerPolicy().decide(self.evidence(
            claimed_at=NOW - timedelta(seconds=500),
            heartbeat_at=NOW - timedelta(seconds=500),
            remote_outcome="uncertain",
        ))
        self.assertEqual(decision.action, "verify")

    def test_stale_owner_cap_and_invalid_heartbeat_quarantine(self):
        decision = StaleOwnerPolicy(max_recoveries=1).decide(self.evidence(
            claimed_at=NOW - timedelta(seconds=500),
            heartbeat_at=NOW - timedelta(seconds=500),
            recovery_count=1,
        ))
        self.assertEqual(decision.action, "quarantine")
        decision = StaleOwnerPolicy().decide(self.evidence(heartbeat_at=None))
        self.assertEqual(decision.action, "quarantine")
        decision = StaleOwnerPolicy().decide(self.evidence(
            heartbeat_at=NOW + timedelta(seconds=1),
        ))
        self.assertEqual(decision.action, "quarantine")
        decision = StaleOwnerPolicy().decide(self.evidence(
            attempt_outcome=AttemptOutcome.SUCCEEDED,
        ))
        self.assertEqual(decision.action, "terminal")


class TestRunProjection(unittest.TestCase):
    def test_mixed_terminal_children_are_partial_success(self):
        self.assertEqual(
            project_run_state({
                "succeeded": 3,
                "skipped": 1,
                "failed_final": 2,
            }),
            "partially_succeeded",
        )

    def test_terminal_projection_is_deterministic_for_all_outcomes(self):
        self.assertEqual(
            project_run_state({"failed_final": 2}),
            "failed_terminal",
        )
        self.assertEqual(
            project_run_state({"succeeded": 2, "skipped": 1}),
            "succeeded",
        )
        self.assertEqual(
            project_run_state({"cancelled": 2}, cancel_requested=True),
            "cancelled",
        )

    def test_unresolved_children_have_safety_precedence(self):
        self.assertEqual(
            project_run_state({
                "succeeded": 1,
                "failed_final": 1,
                "queued": 1,
            }),
            "waiting",
        )
        self.assertEqual(
            project_run_state({"running": 1, "blocked_manual_review": 1}),
            "blocked_manual_review",
        )
        self.assertEqual(
            project_run_state({"running": 1, "failed_retryable": 1}),
            "running",
        )

    def test_projection_rejects_unknown_or_invalid_counts(self):
        with self.assertRaises(ValueError):
            project_run_state({"future_state": 1})
        with self.assertRaises(ValueError):
            project_run_state({"succeeded": -1})
        with self.assertRaises((TypeError, ValueError)):
            project_run_state({"succeeded": True})
        with self.assertRaises(TypeError):
            project_run_state({"succeeded": 1}, cancel_requested=1)


if __name__ == "__main__":
    unittest.main()
