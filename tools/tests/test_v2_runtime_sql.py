"""Cheap, framework-free tests for P10 SQL and mixed-drain boundaries."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"
if "shopify_connector_core" not in sys.modules:
    package = types.ModuleType("shopify_connector_core")
    package.__path__ = [str(CORE)]
    package.__package__ = "shopify_connector_core"
    sys.modules["shopify_connector_core"] = package

from shopify_connector_core.runtime.p10_capacity import (  # noqa: E402
    reserve_capacity_after_v2,
)
from shopify_connector_core.runtime.p10_sql import (  # noqa: E402
    build_claim_statement,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class TestClaimStatement(unittest.TestCase):
    def test_parameter_order_matches_sql_text(self):
        query, params = build_claim_statement(NOW, (7, 11), 3)
        self.assertEqual(len(params), query.count("%s"))
        self.assertEqual(params[:4], (NOW.replace(tzinfo=None),) * 4)
        self.assertEqual(
            params[4],
            ("read_only", "subscriptions", "inventory", "product_export",
             "fulfillment", "all"),
        )
        self.assertEqual(params[5], (7, 11))
        self.assertEqual(params[6], NOW.replace(tzinfo=None))
        self.assertEqual(params[7], 3)
        self.assertLess(query.index("s.company_id IN %s"), query.index("ORDER BY"))
        self.assertIn("FOR UPDATE OF j, r, s, ss SKIP LOCKED", query)
        self.assertIn("LIMIT %s", query)

    def test_claim_statement_contains_both_generation_fences(self):
        query, _params = build_claim_statement(NOW, (1,), 1)
        self.assertIn(
            "j.expected_connection_generation = s.connection_generation",
            query,
        )
        self.assertIn(
            "r.expected_connection_generation = s.connection_generation",
            query,
        )
        self.assertIn(
            "j.expected_configuration_generation =\n               ss.configuration_generation",
            query,
        )
        self.assertIn(
            "r.expected_configuration_generation =\n               ss.configuration_generation",
            query,
        )
        self.assertIn("ss.v2_runtime_mode IN %s", query)
        self.assertIn("j.mutation_attempt_id IS NULL", query)
        self.assertIn("dep.state IN ('succeeded', 'skipped')", query)

    def test_claim_statement_rejects_unbounded_or_ambiguous_inputs(self):
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (), 1)
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (1,), 0)
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (1,), 101)
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (True,), 1)
        with self.assertRaises(ValueError):
            build_claim_statement(NOW.replace(tzinfo=None), (1,), 1)


class TestMixedDrainCapacity(unittest.TestCase):
    def test_finalization_failure_still_reserves_claimed_capacity(self):
        # A claimed item consumed a worker/request slot even though no item
        # reached finalized_count.  The legacy dispatcher gets no capacity in
        # this pass, so a transient finalization failure cannot overrun cap.
        self.assertEqual(
            reserve_capacity_after_v2(
                5,
                {"claimed_count": 5, "finalized_count": 0},
            ),
            (0, 0),
        )

    def test_partial_v2_batch_reserves_claims_and_reports_finalized(self):
        self.assertEqual(
            reserve_capacity_after_v2(
                5,
                {"claimed_count": 3, "finalized_count": 2},
            ),
            (2, 2),
        )

    def test_malformed_report_fails_closed(self):
        for report in (
            {"claimed_count": True, "finalized_count": 0},
            {"claimed_count": 2, "finalized_count": 3},
            {"claimed_count": 6, "finalized_count": 0},
            {"claimed_count": 1},
        ):
            with self.assertRaises((TypeError, ValueError)):
                reserve_capacity_after_v2(5, report)


if __name__ == "__main__":
    unittest.main()
