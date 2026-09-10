"""Cheap pure tests for the P10 lane and cost policies."""

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

from shopify_connector_core.domain.states import PriorityLane  # noqa: E402
from shopify_connector_core.runtime.p10_priority import (  # noqa: E402
    AGING_CEILING_RANK,
    AGING_INTERVAL_SECONDS,
    MAX_CLAIM_BATCH,
    MAX_PRIORITY_INPUT,
    CostGovernor,
    CostObservation,
    PriorityJob,
    effective_lane_rank,
    select_due_jobs,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


def job(job_id, lane, *, age=0, state="queued", priority=10, **kwargs):
    return PriorityJob(
        job_id=job_id,
        store_id=1,
        lane=lane,
        lane_priority=priority,
        available_at=NOW - timedelta(seconds=age),
        state=state,
        **kwargs,
    )


class TestPriorityAging(unittest.TestCase):
    def test_lanes_are_locked_and_safety_is_always_first(self):
        lanes = [
            job(1, PriorityLane.RECONCILIATION, age=24 * 3600),
            job(2, PriorityLane.SAFETY_VERIFICATION, age=0),
            job(3, PriorityLane.INTERACTIVE, age=0),
            job(4, PriorityLane.WEBHOOK, age=0),
            job(5, PriorityLane.ODOO_EVENT, age=0),
            job(6, PriorityLane.SCHEDULED, age=0),
        ]
        selected = select_due_jobs(lanes, now=NOW, limit=MAX_CLAIM_BATCH)
        self.assertEqual([item.job_id for item in selected], [2, 1, 3, 4, 5, 6])

    def test_aging_is_one_step_per_fifteen_minutes_and_caps_at_interactive(self):
        scheduled = job(1, PriorityLane.SCHEDULED, age=AGING_INTERVAL_SECONDS - 1)
        self.assertEqual(effective_lane_rank(scheduled, NOW), 4)
        scheduled = job(1, PriorityLane.SCHEDULED, age=AGING_INTERVAL_SECONDS)
        self.assertEqual(effective_lane_rank(scheduled, NOW), 3)
        scheduled = job(1, PriorityLane.SCHEDULED, age=3 * AGING_INTERVAL_SECONDS)
        self.assertEqual(effective_lane_rank(scheduled, NOW), AGING_CEILING_RANK)
        safety = job(1, PriorityLane.SAFETY_VERIFICATION, age=48 * 3600)
        self.assertEqual(effective_lane_rank(safety, NOW), 0)

    def test_due_selection_filters_future_blocked_cancelled_and_nonqueued(self):
        values = [
            job(1, PriorityLane.INTERACTIVE),
            job(2, PriorityLane.INTERACTIVE, age=-60),
            job(3, PriorityLane.INTERACTIVE, blocked_by_job_id=77),
            job(4, PriorityLane.INTERACTIVE, cancel_requested=True),
            job(5, PriorityLane.INTERACTIVE, state="running"),
        ]
        self.assertEqual([item.job_id for item in select_due_jobs(values, now=NOW)], [1])

    def test_due_order_is_deterministic_by_availability_priority_and_id(self):
        values = [
            job(3, PriorityLane.INTERACTIVE, priority=2),
            job(2, PriorityLane.INTERACTIVE, priority=1),
            job(1, PriorityLane.INTERACTIVE, priority=1),
        ]
        self.assertEqual([item.job_id for item in select_due_jobs(values, now=NOW)], [1, 2, 3])

    def test_input_and_batch_bounds_fail_closed(self):
        values = [job(index + 1, PriorityLane.SCHEDULED) for index in range(MAX_PRIORITY_INPUT + 1)]
        with self.assertRaises(ValueError):
            select_due_jobs(values, now=NOW)
        with self.assertRaises(ValueError):
            select_due_jobs([job(1, PriorityLane.SCHEDULED)], now=NOW, limit=MAX_CLAIM_BATCH + 1)
        with self.assertRaises(TypeError):
            select_due_jobs([job(1, PriorityLane.SCHEDULED)], now=NOW, limit=True)


class TestCostGovernor(unittest.TestCase):
    def test_unknown_budget_defers_without_sleeping(self):
        decision = CostGovernor().decide(None, estimated_cost=10, now=NOW)
        self.assertEqual(decision.action, "defer")
        self.assertEqual(decision.reason_code, "cost_budget_unknown")
        self.assertEqual(decision.delay_seconds, 60)
        json.dumps(decision.as_dict())

    def test_available_budget_is_allowed_and_restoration_is_projected(self):
        observation = CostObservation(available_cost=80, maximum_cost=100, restore_rate=2, observed_at=NOW)
        allowed = CostGovernor(safety_reserve=5).decide(
            observation, estimated_cost=90, now=NOW + timedelta(seconds=10)
        )
        self.assertEqual(allowed.action, "allow")
        self.assertEqual(allowed.projected_available_cost, 100)
        waiting = CostGovernor(safety_reserve=5).decide(
            observation, estimated_cost=94, now=NOW
        )
        self.assertEqual(waiting.action, "defer")
        self.assertAlmostEqual(waiting.delay_seconds, 9.5)
        self.assertEqual(waiting.not_before, NOW + timedelta(seconds=9.5))

    def test_budget_that_cannot_restore_or_fit_is_manual_review(self):
        no_restore = CostObservation(available_cost=1, maximum_cost=100, restore_rate=0, observed_at=NOW)
        decision = CostGovernor().decide(no_restore, estimated_cost=2, now=NOW)
        self.assertEqual(decision.action, "manual_review")
        self.assertEqual(decision.reason_code, "cost_budget_not_restoring")
        too_large = CostObservation(available_cost=100, maximum_cost=100, restore_rate=1, observed_at=NOW)
        decision = CostGovernor(safety_reserve=1).decide(too_large, estimated_cost=100, now=NOW)
        self.assertEqual(decision.reason_code, "cost_request_exceeds_bucket")

    def test_bad_cost_values_and_future_observation_fail_closed(self):
        for value in (True, float("nan"), float("inf"), -1):
            with self.assertRaises((TypeError, ValueError)):
                CostObservation(value, 100, 1, NOW)
        with self.assertRaises((TypeError, ValueError)):
            CostGovernor().decide(None, estimated_cost=True, now=NOW)
        future = CostObservation(10, 100, 1, NOW + timedelta(seconds=1))
        decision = CostGovernor().decide(future, estimated_cost=1, now=NOW)
        self.assertEqual(decision.action, "manual_review")
        self.assertEqual(decision.reason_code, "cost_observation_from_future")


if __name__ == "__main__":
    unittest.main()
