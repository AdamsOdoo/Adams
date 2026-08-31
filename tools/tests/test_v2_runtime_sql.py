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
        query, params = build_claim_statement(
            NOW, (7, 11), 3, ("core.read", "product.scan"),
        )
        self.assertEqual(len(params), query.count("%s"))
        self.assertEqual(params[0], ("core.read", "product.scan"))
        self.assertEqual(params[1:5], (NOW.replace(tzinfo=None),) * 4)
        self.assertEqual(
            params[5],
            ("read_only", "subscriptions", "inventory", "product_export",
             "fulfillment", "all"),
        )
        self.assertEqual(params[6], (7, 11))
        self.assertEqual(params[7], NOW.replace(tzinfo=None))
        self.assertEqual(params[8], 3)
        self.assertIn("j.job_type IN %s", query)
        self.assertLess(query.index("s.company_id IN %s"), query.index("ORDER BY"))
        self.assertIn("FOR UPDATE OF j SKIP LOCKED", query)
        self.assertIn("LIMIT %s", query)

    def test_claim_statement_contains_both_generation_fences(self):
        query, _params = build_claim_statement(
            NOW, (1,), 1, ("core.read",),
        )
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
            build_claim_statement(NOW, (), 1, ("core.read",))
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (1,), 0, ("core.read",))
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (1,), 101, ("core.read",))
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (True,), 1, ("core.read",))
        with self.assertRaises(ValueError):
            build_claim_statement(
                NOW.replace(tzinfo=None), (1,), 1, ("core.read",),
            )

    def test_claim_statement_rejects_missing_or_unbounded_handler_allowlist(self):
        with self.assertRaises((TypeError, ValueError)):
            build_claim_statement(NOW, (1,), 1, ())
        with self.assertRaises((TypeError, ValueError)):
            build_claim_statement(NOW, (1,), 1, "core.read")
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (1,), 1, ("core.read", "core.read"))
        with self.assertRaises(ValueError):
            build_claim_statement(NOW, (1,), 1, ("Core.Read",))

    def test_pre_c2_mutation_rows_are_outside_the_sql_allowlist(self):
        """A V2 mutation job cannot become P10 work before C2 evidence."""
        query, params = build_claim_statement(
            NOW, (1,), 5, ("core.read", "product.scan"),
        )
        self.assertEqual(params[0], ("core.read", "product.scan"))
        self.assertIn("j.job_type IN %s", query)
        self.assertIn("j.mutation_attempt_id IS NULL", query)
        with self.assertRaises((TypeError, ValueError)):
            build_claim_statement(
                NOW, (1,), ("core.read", "product.scan"), 5,
            )

    def test_lock_and_cancellation_source_contracts_are_fail_closed(self):
        repository = (
            CORE / "models" / "shopify_connector_v2_runtime_repository.py"
        ).read_text(encoding="utf-8")
        stale = (
            CORE / "models" / "shopify_connector_v2_runtime_stale.py"
        ).read_text(encoding="utf-8")
        batch_locks = (
            CORE / "runtime" / "p10_repository_locks.py"
        ).read_text(encoding="utf-8")
        for source in (repository, stale):
            self.assertNotIn("FOR UPDATE OF a, r, s, ss SKIP LOCKED", source)
            self.assertIn("FOR UPDATE", source)
        self.assertIn("def _lock_claim_batch_scopes", repository)
        self.assertIn("handler_keys", repository)
        self.assertIn("unregistered_read_handler", stale)
        self.assertIn("ORDER BY store_id, id FOR UPDATE", stale)
        lock_positions = tuple(batch_locks.index(marker) for marker in (
            "FROM shopify_connector_job_attempt",
            "FROM shopify_connector_run",
            "FROM shopify_connector_store\n",
            "FROM shopify_connector_store_settings",
        ))
        self.assertEqual(lock_positions, tuple(sorted(lock_positions)))
        self.assertIn("def _finish_cancelled_stale", stale)
        cancellation = stale[stale.index("if run.cancel_requested_at:"):]
        self.assertIn("_finish_cancelled_stale", cancellation)
        self.assertIn("processed += 1", cancellation)
        cancel_source = (
            CORE / "models" / "shopify_connector_recovery_cancellation.py"
        ).read_text(encoding="utf-8")
        cancel_lock = cancel_source[
            cancel_source.index("def _recovery_lock_cancel_scope"):
            cancel_source.index("def _recovery_cancel_v2_or_legacy")
        ]
        self.assertLess(
            cancel_lock.index("FROM shopify_connector_job"),
            cancel_lock.index("FROM shopify_connector_run"),
        )
        self.assertIn("FOR UPDATE SKIP LOCKED", cancel_lock)

    def test_legacy_dispatch_has_a_composed_run_link_fence(self):
        fence = (
            CORE / "models" / "shopify_connector_job_v2_claim_fence.py"
        ).read_text(encoding="utf-8")
        init_source = (CORE / "models" / "__init__.py").read_text(
            encoding="utf-8",
        )
        self.assertIn("_get_v2_job_types()", fence)
        self.assertIn('(\"run_id\", \"=\", False)', fence)
        self.assertIn("job.job_type in registered", fence)
        self.assertIn("MAX_CLAIM_BATCH", fence)
        self.assertIn("shopify_connector_job_v2_claim_fence", init_source)


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
