"""Cheap source guards for P11 cumulative and fail-closed ORM wiring."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WEBHOOK = ROOT / "addons/shopify_connector_webhook"
RUNTIME = WEBHOOK / "models/shopify_connector_webhook_subscription_v2_runtime.py"
RECONCILE = WEBHOOK / "models/shopify_connector_webhook_subscription_v2_reconciliation.py"
LEGACY = WEBHOOK / "models/shopify_connector_webhook_subscription.py"
DISPATCH = WEBHOOK / "models/shopify_connector_webhook_dispatch.py"


def _method(path: Path, name: str) -> str:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    node = next(
        item for item in ast.walk(tree)
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    return ast.get_source_segment(source, node) or ""


class P11OrmSafetyTests(unittest.TestCase):
    def test_all_subscription_routes_use_the_cumulative_lattice(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("runtime_mode_includes", source)
        self.assertNotIn("v2_runtime_mode == 'subscriptions'", source)
        self.assertNotIn("v2_runtime_mode != 'subscriptions'", source)
        admission = _method(RUNTIME, "_enqueue_v2_subscription_mutation")
        self.assertIn("settings.v2_runtime_mode", admission)

    def test_global_planner_block_returns_before_any_enqueue(self):
        body = _method(RECONCILE, "_reconcile_store")
        blocked = body.index("if plan.blocked:")
        guarded_return = body.index("return expected", blocked)
        enqueue = body.index("self._enqueue_subscription_mutation", guarded_return)
        self.assertLess(blocked, guarded_return)
        self.assertLess(guarded_return, enqueue)
        self.assertIn("plan.require_executable()", body)

    def test_retired_topic_delete_requires_fresh_callback_ownership(self):
        cleanup = _method(LEGACY, "_reconcile_registry_removed_subscriptions")
        self.assertIn("subscription.expected_callback_url_digest", cleanup)
        self.assertIn("remote_topic != subscription.topic_enum", cleanup)
        runtime_target = _method(RUNTIME, "_v2_mutation_subscription")
        self.assertIn("removed_cleanup_owned", runtime_target)
        self.assertNotIn(
            "if not (removed_cleanup or stale_callback_cleanup",
            runtime_target,
        )

    def test_typed_subscription_read_errors_keep_deliberate_taxonomy(self):
        source = DISPATCH.read_text(encoding="utf-8")
        handler = _method(DISPATCH, "_handle_webhook_subscription_reconcile")
        self.assertIn("WebhookSubscriptionReadError", source)
        self.assertIn("except WebhookSubscriptionReadError", handler)
        self.assertIn("shopify_temporary_server_network", handler)
        self.assertIn("data_shape_schema_mismatch", handler)


if __name__ == "__main__":
    unittest.main()
