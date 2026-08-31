"""Dependency-free fault matrix for the P10 network-read claim fence."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import sys
import types
import unittest
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "addons" / "shopify_connector_core"
if "shopify_connector_core" not in sys.modules:
    package = types.ModuleType("shopify_connector_core")
    package.__path__ = [str(CORE)]
    package.__package__ = "shopify_connector_core"
    sys.modules["shopify_connector_core"] = package

from shopify_connector_core.runtime.p10_claim_fence import (  # noqa: E402
    AttemptClaimState,
    JobClaimState,
    ReadClaimSnapshot,
    RunClaimState,
    SettingsClaimState,
    StoreClaimState,
    read_claim_matches,
)
from shopify_connector_core.runtime.p10_coordinator import ClaimedWork  # noqa: E402


def _claim(**overrides):
    values = {
        "job_id": 41,
        "store_id": 7,
        "company_id": 3,
        "run_id": 12,
        "attempt_no": 2,
        "claim_token": str(uuid4()),
        "worker_ref": "worker:test",
        "handler_key": "product_scan",
        "lane": "interactive",
        "expected_generation": 4,
        "expected_configuration_generation": 9,
        "operation_scope_key": "product:scan",
    }
    values.update(overrides)
    return ClaimedWork(**values)


def _snapshot(claim, *, mode="read_only"):
    return ReadClaimSnapshot(
        job=JobClaimState(
            id=claim.job_id,
            store_id=claim.store_id,
            company_id=claim.company_id,
            job_type=claim.handler_key,
            job_source="v2_run",
            state="running",
            claim_token=claim.claim_token,
            worker_ref=claim.worker_ref,
            connection_generation=claim.expected_generation,
            configuration_generation=claim.expected_configuration_generation,
            run_id=claim.run_id,
            lane=claim.lane,
            operation_scope_key=claim.operation_scope_key,
            mutation_attempt_id=None,
        ),
        attempt=AttemptClaimState(
            attempt_no=claim.attempt_no,
            claim_token=claim.claim_token,
            worker_ref=claim.worker_ref,
            outcome="running",
            run_id=claim.run_id,
        ),
        run=RunClaimState(
            store_id=claim.store_id,
            company_id=claim.company_id,
            state="running",
            cancel_requested_at=None,
            connection_generation=claim.expected_generation,
            configuration_generation=claim.expected_configuration_generation,
        ),
        store=StoreClaimState(
            company_id=claim.company_id,
            state="connected",
            connection_generation=claim.expected_generation,
            shop_domain="example.myshopify.com",
            api_version="2026-07",
        ),
        settings=SettingsClaimState(
            company_id=claim.company_id,
            configuration_generation=claim.expected_configuration_generation,
            runtime_mode=mode,
        ),
    )


class P10ReadClaimFenceTests(unittest.TestCase):
    def test_exact_claim_and_every_cumulative_mode_are_accepted(self):
        claim = _claim()
        for mode in (
            "read_only",
            "subscriptions",
            "inventory",
            "product_export",
            "fulfillment",
            "all",
        ):
            with self.subTest(mode=mode):
                self.assertTrue(
                    read_claim_matches(_snapshot(claim, mode=mode), claim, (3,))
                )

    def test_every_identity_lifecycle_and_generation_fence_fails_closed(self):
        claim = _claim()
        good = _snapshot(claim)
        bad_components = (
            ("job", {"id": 99}),
            ("job", {"store_id": 99}),
            ("job", {"company_id": 99}),
            ("job", {"job_type": "order_scan"}),
            ("job", {"state": "queued"}),
            ("job", {"claim_token": str(uuid4())}),
            ("job", {"worker_ref": "worker:other"}),
            ("job", {"connection_generation": 5}),
            ("job", {"configuration_generation": 10}),
            ("job", {"run_id": 99}),
            ("job", {"lane": "background"}),
            ("job", {"operation_scope_key": "other:scope"}),
            ("job", {"mutation_attempt_id": 1}),
            ("attempt", {"attempt_no": 3}),
            ("attempt", {"claim_token": str(uuid4())}),
            ("attempt", {"worker_ref": "worker:other"}),
            ("attempt", {"outcome": "claimed"}),
            ("attempt", {"run_id": 99}),
            ("run", {"store_id": 99}),
            ("run", {"company_id": 99}),
            ("run", {"state": "cancelled"}),
            ("run", {"cancel_requested_at": "2026-08-31 12:00:00"}),
            ("run", {"connection_generation": 5}),
            ("run", {"configuration_generation": 10}),
            ("store", {"company_id": 99}),
            ("store", {"state": "disconnected"}),
            ("store", {"connection_generation": 5}),
            ("store", {"shop_domain": None}),
            ("store", {"api_version": None}),
            ("settings", {"company_id": 99}),
            ("settings", {"configuration_generation": 10}),
            ("settings", {"runtime_mode": "legacy"}),
        )
        for component_name, changes in bad_components:
            bad_component = replace(
                getattr(good, component_name), **changes,
            )
            bad = replace(good, **{component_name: bad_component})
            with self.subTest(component=component_name, changes=changes):
                self.assertFalse(read_claim_matches(bad, claim, (3,)))
        self.assertFalse(read_claim_matches(good, claim, (4,)))
        self.assertFalse(read_claim_matches(object(), claim, (3,)))

    def test_incomplete_claim_identity_is_never_network_capable(self):
        claim = _claim(run_id=None, company_id=None)
        self.assertFalse(read_claim_matches(_snapshot(claim), claim, (3,)))

    def test_transport_uses_ordered_locks_and_fresh_endpoint_snapshot(self):
        base = (
            CORE / "models" / "shopify_connector_api_client.py"
        ).read_text(encoding="utf-8")
        extension = (
            CORE / "models" / "shopify_connector_api_client_v2_read_claim.py"
        ).read_text(encoding="utf-8")
        init_source = (CORE / "models" / "__init__.py").read_text(encoding="utf-8")

        admit = base[base.index("    def _admit_business_read"):]
        self.assertLess(
            admit.index("_preflight_business_read_claim"),
            admit.index("_ensure_access_token"),
        )
        self.assertLess(
            admit.index("_claimed_business_read_values"),
            admit.index("shopify.connector.call.lease"),
        )
        lock_markers = (
            "FROM shopify_connector_job\n",
            "FROM shopify_connector_job_attempt\n",
            "FROM shopify_connector_run\n",
            "FROM shopify_connector_store\n",
            "FROM shopify_connector_store_settings\n",
        )
        positions = tuple(extension.index(marker) for marker in lock_markers)
        self.assertEqual(positions, tuple(sorted(positions)))
        self.assertEqual(extension.count("FOR SHARE"), 5)
        self.assertNotIn("FOR SHARE OF", extension)
        self.assertIn(
            "snapshot.endpoint != preflight_snapshot.endpoint", extension,
        )
        self.assertIn("_send(transport_store, body, token)", base)
        self.assertIn("_normalize_response(transport_store, response)", base)
        self.assertLess(
            init_source.index("from . import shopify_connector_api_client\n"),
            init_source.index(
                "from . import shopify_connector_api_client_v2_read_claim"
            ),
        )


if __name__ == "__main__":
    unittest.main()
