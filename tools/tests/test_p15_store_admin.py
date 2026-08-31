"""Dependency-free characterization tests for the P15 admin contracts."""

from __future__ import annotations

import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = REPO_ROOT / "addons" / "shopify_connector_core"


def _import_core_without_odoo() -> None:
    """Load pure contracts without executing the Odoo addon initializer."""

    package = sys.modules.get("shopify_connector_core")
    if package is None:
        package = types.ModuleType("shopify_connector_core")
        package.__path__ = [str(CORE_ROOT)]
        package.__package__ = "shopify_connector_core"
        sys.modules["shopify_connector_core"] = package


_import_core_without_odoo()

from shopify_connector_core.domain.dto import (  # noqa: E402
    StoreSummaryDTO,
    WorkflowSummaryDTO,
)
from shopify_connector_core.domain.store_admin import (  # noqa: E402
    ReadinessCheckDTO,
    ReadinessDTO,
    StoreAdminContractError,
    StoreCapacityExceeded,
    StoreSettingsDTO,
    canonical_shop_domain,
    dto_as_dict,
    ensure_store_capacity,
    lifecycle_transition,
    store_configuration_fingerprint,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class TestP15StoreAdminContracts(unittest.TestCase):

    def test_migration_never_invents_irreversible_retirement(self):
        migration = (
            CORE_ROOT / "migrations" / "19.0.1.32.0" / "post-migrate.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("WHEN state = 'disconnected' THEN 'retired'", migration)
        self.assertIn("WHEN state = 'connected' THEN 'active'", migration)
        self.assertIn("ELSE 'draft' END", migration)

    def test_canonical_shop_domain_is_one_exact_identity(self):
        self.assertEqual(
            canonical_shop_domain("  Demo-Shop.MYSHOPIFY.COM  "),
            "demo-shop.myshopify.com",
        )
        for value in (
            "https://demo.myshopify.com",
            "demo.myshopify.com/path",
            "demo.myshopify.com.",
            "demo_shop.myshopify.com",
            "demo.example.myshopify.com",
        ):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    canonical_shop_domain(value)

    def test_fingerprint_excludes_display_and_clock_fields_only(self):
        base = {
            "store_id": 7,
            "company_id": 3,
            "generation": 4,
            "operation": "settings_group:orders",
            "values": {"order_import_window": 30},
            "display_label": "Orders",
            "generated_at": NOW.isoformat(),
        }
        changed_display = dict(base, display_label="Translated Orders")
        changed_value = dict(base, values={"order_import_window": 31})
        self.assertEqual(
            store_configuration_fingerprint(
                store_id=7,
                company_id=3,
                generation=4,
                operation="settings_group:orders",
                values=base["values"],
            ),
            store_configuration_fingerprint(
                store_id=7,
                company_id=3,
                generation=4,
                operation="settings_group:orders",
                values=changed_display["values"],
            ),
        )
        self.assertNotEqual(
            store_configuration_fingerprint(
                store_id=7,
                company_id=3,
                generation=4,
                operation="settings_group:orders",
                values=base["values"],
            ),
            store_configuration_fingerprint(
                store_id=7,
                company_id=3,
                generation=4,
                operation="settings_group:orders",
                values=changed_value["values"],
            ),
        )

    def test_capacity_is_fail_closed_at_ten(self):
        self.assertEqual(ensure_store_capacity(9), 10)
        self.assertEqual(ensure_store_capacity(10, requested_delta=0), 10)
        with self.assertRaises(StoreCapacityExceeded):
            ensure_store_capacity(10)
        with self.assertRaises(ValueError):
            ensure_store_capacity(-1)

    def test_lifecycle_and_dto_contracts_are_strict(self):
        self.assertEqual(lifecycle_transition("setup_incomplete", "connected"), "connected")
        with self.assertRaises(ValueError):
            lifecycle_transition("disconnected", "connected")

        store = StoreSummaryDTO(
            7,
            "Demo",
            "demo.myshopify.com",
            {"id": 3, "name": "Company"},
            "connected",
            "valid",
            "active",
            "healthy",
        )
        readiness = ReadinessDTO(
            7,
            "pass",
            NOW,
            False,
            (ReadinessCheckDTO("identity", "essential", "pass", "ok"),),
            "a" * 64,
        )
        settings = StoreSettingsDTO(
            7,
            3,
            4,
            (),
            {"product_domain_enabled": True},
            "b" * 64,
        )
        self.assertEqual(dto_as_dict(settings)["configuration_generation"], 4)
        self.assertIsInstance(WorkflowSummaryDTO("product", "Products", "ready", "healthy", {}, 0, None), WorkflowSummaryDTO)
        # A raw secret must not be representable in the admin settings DTO,
        # even if a future adapter accidentally passes one through.
        with self.assertRaises(StoreAdminContractError):
            StoreSettingsDTO(
                7,
                3,
                4,
                (),
                {"access_token": "shpat_should_never_render"},
                "b" * 64,
            )
        self.assertEqual(readiness.store_id, store.id)


if __name__ == "__main__":
    unittest.main()
