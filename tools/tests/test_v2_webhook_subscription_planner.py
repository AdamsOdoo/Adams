"""Cheap pure tests for the P11 webhook desired-state planner."""

from __future__ import annotations

import hashlib
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


for _addon in ("shopify_connector_core", "shopify_connector_webhook"):
    _root = ROOT / "addons" / _addon
    _namespace(_addon, _root)
    _namespace(_addon + ".domain", _root / "domain")
    _namespace(_addon + ".integration", _root / "integration")
    _namespace(_addon + ".integration.shopify", _root / "integration" / "shopify")

# The P07 read gateway is intentionally loaded through the canonical Odoo
# addon namespace.  These namespaces are package-only test shims; importing
# the DTOs still performs no Odoo or network work.
_namespace("odoo", ROOT)
_namespace("odoo.addons", ROOT / "addons")
_namespace("odoo.addons.shopify_connector_core", ROOT / "addons" / "shopify_connector_core")
_namespace(
    "odoo.addons.shopify_connector_core.domain",
    ROOT / "addons" / "shopify_connector_core" / "domain",
)


from shopify_connector_webhook.integration.shopify.webhook_subscription_planner import (  # noqa: E402
    MAX_CURRENT_SUBSCRIPTIONS,
    MAX_GRANTED_SCOPES,
    MAX_TOPIC_SPECS,
    SubscriptionPlan,
    WebhookSubscriptionObserved,
    WebhookSubscriptionPlanner,
    WebhookSubscriptionPlannerError,
    WebhookTopicSpec,
    plan_webhook_subscriptions,
)
from shopify_connector_webhook.integration.shopify.webhook_subscription_contract_adapter import (  # noqa: E402
    P08_CALLBACK_URL_DIGEST_KEY,
    P11_CALLBACK_URI_DIGEST_KEY,
    adapt_p07_collection,
    adapt_p07_subscription,
    adapt_p08_target,
    adapt_p08_targets,
)
from shopify_connector_webhook.integration.shopify.webhook_subscription_mutation_gateway import (  # noqa: E402
    WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
    WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
)
from shopify_connector_webhook.integration.shopify.webhook_subscription_read_gateway import (  # noqa: E402
    WebhookSubscriptionCollectionDTO,
    WebhookSubscriptionDTO,
    WebhookSubscriptionPageDTO,
)


CALLBACK_URI = "https://connector.example/webhook?secret=fixture-only"
CALLBACK_DIGEST = hashlib.sha256(CALLBACK_URI.encode("utf-8")).hexdigest()
TOPIC = "ORDERS_CREATE"
OTHER_TOPIC = "PRODUCTS_UPDATE"


def _observed(
    number: int = 1,
    *,
    topic: str = TOPIC,
    digest: str | None = CALLBACK_DIGEST,
    api_version: str = "2026-07",
    format_value: str = "JSON",
    include_fields: tuple[str, ...] = ("admin_graphql_api_id",),
) -> WebhookSubscriptionObserved:
    return WebhookSubscriptionObserved(
        f"gid://shopify/WebhookSubscription/{number}",
        topic,
        digest,
        api_version,
        format_value,
        include_fields,
    )


class P11PlannerTests(unittest.TestCase):
    def test_empty_store_plans_one_create_with_p08_contract_and_no_uri(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC, required_scopes=("read_orders",), include_fields=("admin_graphql_api_id",))],
            [],
            callback_uri=CALLBACK_URI,
            granted_scopes=["read_orders"],
        )
        self.assertIsInstance(plan, SubscriptionPlan)
        self.assertEqual(plan.status, "planned")
        self.assertFalse(plan.blocked)
        self.assertEqual([item.action for item in plan.decisions], ["create"])
        decision = plan.decisions[0]
        self.assertEqual(decision.operation_key, "webhook.subscription.create")
        self.assertEqual(decision.readback["operation_key"], "webhook.subscriptions.read")
        self.assertEqual(decision.target["callback_uri_digest"], CALLBACK_DIGEST)
        self.assertNotIn("fixture-only", str(plan.as_dict()))
        self.assertEqual(len(plan.fingerprint), 64)

    def test_reordering_topics_current_rows_and_scopes_is_byte_deterministic(self):
        topics = [
            WebhookTopicSpec(OTHER_TOPIC, required_scopes=("read_products",)),
            WebhookTopicSpec(TOPIC, required_scopes=("read_orders",)),
        ]
        first = plan_webhook_subscriptions(
            topics,
            [_observed(2, topic=OTHER_TOPIC), _observed(1)],
            callback_uri=CALLBACK_URI,
            granted_scopes=("read_products", "read_orders"),
        )
        second = plan_webhook_subscriptions(
            list(reversed(topics)),
            [_observed(1), _observed(2, topic=OTHER_TOPIC)],
            callback_uri_digest=CALLBACK_DIGEST,
            granted_scopes=("read_orders", "read_products"),
        )
        self.assertEqual(first.as_dict(), second.as_dict())

    def test_exact_current_state_keeps_one_and_v1_field_subset_is_healthy(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC, include_fields=("id",))],
            [_observed(7, include_fields=("admin_graphql_api_id", "id", "extra"))],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertEqual(plan.status, "converged")
        self.assertEqual([(item.action, item.reason_code) for item in plan.decisions], [("keep", "already_desired")])

    def test_duplicate_exact_rows_delete_only_deterministic_owned_extra(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(9), _observed(3)],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertEqual([(item.action, item.subscription_gid) for item in plan.decisions], [
            ("keep", "gid://shopify/WebhookSubscription/3"),
            ("delete", "gid://shopify/WebhookSubscription/9"),
        ])
        self.assertEqual(plan.decisions[1].reason_code, "duplicate_owned_subscription")
        self.assertEqual(plan.decisions[1].operation_key, "webhook.subscription.delete")

    def test_stale_api_version_is_delete_then_create_after_all_readbacks(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(12, api_version="2025-10")],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertEqual([item.action for item in plan.decisions], ["delete", "create"])
        delete, create = plan.decisions
        self.assertEqual(delete.reason_code, "stale_api_version")
        self.assertEqual(create.reason_code, "replace_stale_owned_subscription")
        self.assertEqual(create.depends_on, (delete.key,))
        self.assertEqual(delete.target["subscription_gid"], "gid://shopify/WebhookSubscription/12")

    def test_stale_format_and_fields_are_owned_replacements(self):
        for observed, reason in (
            (_observed(20, format_value="XML"), "stale_format"),
            (_observed(21, include_fields=("other",)), "stale_include_fields"),
        ):
            with self.subTest(reason=reason):
                plan = plan_webhook_subscriptions(
                    [WebhookTopicSpec(TOPIC, include_fields=("id",))],
                    [observed],
                    callback_uri_digest=CALLBACK_DIGEST,
                )
                self.assertEqual(plan.decisions[0].reason_code, reason)
                self.assertEqual(plan.decisions[1].action, "create")

    def test_malformed_format_is_blocked_but_structural_unsupported_format_replaces(self):
        malformed = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(22, format_value=" XML ")],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertTrue(malformed.blocked)
        self.assertEqual(malformed.decisions[0].reason_code, "malformed_observation")
        self.assertEqual(malformed.mutations, ())

        unsupported = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(23, format_value="XML")],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertFalse(unsupported.blocked)
        self.assertEqual(unsupported.decisions[0].reason_code, "stale_format")
        self.assertEqual([item.action for item in unsupported.mutations], ["delete", "create"])

    def test_callback_drift_and_unknown_topic_are_blocks_with_no_mutation(self):
        external_digest = "a" * 64
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(1, digest=external_digest), _observed(2, topic=OTHER_TOPIC)],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertTrue(plan.blocked)
        self.assertEqual({item.reason_code for item in plan.decisions}, {"callback_mismatch", "unrecognized_topic"})
        self.assertEqual(plan.mutations, ())

    def test_disabled_topic_deletes_only_matching_connector_callback(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC, enabled=False)],
            [_observed(1), _observed(2, digest="b" * 64)],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertEqual([(item.action, item.reason_code) for item in plan.decisions], [
            ("block", "callback_mismatch"),
            ("block", "cleanup_blocked_by_drift"),
        ])
        self.assertEqual(plan.mutations, ())
        self.assertEqual(plan.decisions[0].ownership, "external")
        self.assertEqual(plan.decisions[1].ownership, "connector")

    def test_missing_scope_blocks_topic_without_creating_or_deleting(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC, required_scopes=("read_orders", "write_orders"))],
            [_observed(4)],
            callback_uri_digest=CALLBACK_DIGEST,
            granted_scopes=("read_orders",),
        )
        self.assertTrue(plan.blocked)
        self.assertEqual(plan.decisions[0].reason_code, "missing_scopes")
        self.assertEqual(plan.mutations, ())

    def test_missing_scopes_do_not_hide_other_topic_drift_diagnostics(self):
        plan = plan_webhook_subscriptions(
            [
                WebhookTopicSpec(TOPIC, required_scopes=("read_orders",)),
                WebhookTopicSpec(OTHER_TOPIC, required_scopes=("read_products",)),
            ],
            [_observed(40, digest="b" * 64, topic=TOPIC)],
            callback_uri_digest=CALLBACK_DIGEST,
            granted_scopes=(),
        )
        reasons = {item.reason_code for item in plan.decisions}
        self.assertTrue(plan.blocked)
        self.assertIn("callback_mismatch", reasons)
        self.assertIn("missing_scopes", reasons)
        self.assertEqual(plan.mutations, ())

    def test_incomplete_read_is_global_fail_closed_plan(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(4)],
            callback_uri_digest=CALLBACK_DIGEST,
            current_complete=False,
        )
        self.assertTrue(plan.blocked)
        self.assertEqual(plan.decisions[0].reason_code, "current_state_uncertain")
        self.assertEqual(plan.mutations, ())

    def test_malformed_api_observation_blocks_without_replacement(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(5, api_version="unstable")],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertTrue(plan.blocked)
        self.assertEqual(plan.decisions[0].reason_code, "malformed_observation")
        self.assertEqual(plan.mutations, ())

    def test_duplicate_identity_is_global_uncertainty_and_never_mutates(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(8), _observed(8, api_version="2025-10")],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertTrue(plan.blocked)
        self.assertEqual(plan.decisions[0].reason_code, "duplicate_subscription_identity")
        self.assertEqual(plan.mutations, ())

    def test_duplicate_identity_blocker_keys_are_unique_and_one_per_gid(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [
                _observed(8),
                _observed(8, api_version="2025-10"),
                _observed(8, format_value="XML"),
                _observed(9),
                _observed(9, digest="b" * 64),
            ],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        blockers = [item for item in plan.decisions if item.reason_code == "duplicate_subscription_identity"]
        self.assertEqual(len(blockers), 2)
        self.assertEqual(len({item.key for item in blockers}), len(blockers))

    def test_p07_like_mapping_rejects_raw_uri_and_retains_only_digest(self):
        with self.assertRaises(WebhookSubscriptionPlannerError) as context:
            plan_webhook_subscriptions(
                [WebhookTopicSpec(TOPIC)],
                [{
                    "id": "gid://shopify/WebhookSubscription/1",
                    "topic": TOPIC,
                    "uri": CALLBACK_URI,
                    "observed_api_version": "2026-07",
                    "format": "JSON",
                    "include_fields": [],
                }],
                callback_uri=CALLBACK_URI,
            )
        self.assertEqual(context.exception.code, "raw_uri_forbidden")
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [{
                "id": "gid://shopify/WebhookSubscription/1",
                "topic": TOPIC,
                "uri_digest": CALLBACK_DIGEST,
                "observed_api_version": "2026-07",
                "format": "JSON",
                "include_fields": [],
            }],
            callback_uri=CALLBACK_URI,
        )
        self.assertNotIn("fixture-only", str(plan.as_dict()))

    def test_legacy_false_digest_is_adapted_to_unknown_identity(self):
        observed = adapt_p07_subscription({
            "id": "gid://shopify/WebhookSubscription/25",
            "topic": TOPIC,
            "uri_digest": False,
            "observed_api_version": "2026-07",
            "format": "JSON",
            "include_fields": [],
        })
        self.assertIsNone(observed.uri_digest)
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [observed],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertTrue(plan.blocked)
        self.assertEqual(plan.decisions[0].reason_code, "unknown_callback_identity")

    def test_direct_p07_dto_collection_is_accepted_but_page_and_start_cursor_are_rejected(self):
        dto = WebhookSubscriptionDTO(
            "gid://shopify/WebhookSubscription/26",
            TOPIC,
            CALLBACK_DIGEST,
            "2026-07",
            "JSON",
            ("id",),
        )
        collection = WebhookSubscriptionCollectionDTO((dto,), "northwind.myshopify.com", None)
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC, include_fields=("id",))],
            collection,
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertEqual(plan.status, "converged")
        with self.assertRaises(WebhookSubscriptionPlannerError) as page_error:
            plan_webhook_subscriptions(
                [WebhookTopicSpec(TOPIC)],
                WebhookSubscriptionPageDTO((dto,), "northwind.myshopify.com", False, None),
                callback_uri_digest=CALLBACK_DIGEST,
            )
        self.assertEqual(page_error.exception.code, "partial_read")
        class StartedCollection:
            items = (dto,)
            complete = True
            start_cursor = "cursor-1"

        with self.assertRaises(WebhookSubscriptionPlannerError) as started_error:
            plan_webhook_subscriptions(
                [WebhookTopicSpec(TOPIC)],
                StartedCollection(),
                callback_uri_digest=CALLBACK_DIGEST,
            )
        self.assertEqual(started_error.exception.code, "partial_read")
        with self.assertRaises(WebhookSubscriptionPlannerError) as cursor_error:
            plan_webhook_subscriptions(
                [WebhookTopicSpec(TOPIC)],
                collection,
                callback_uri_digest=CALLBACK_DIGEST,
                current_start_cursor="cursor-1",
            )
        self.assertEqual(cursor_error.exception.code, "partial_read")

    def test_p07_collection_adapter_rejects_incomplete_collection_and_enforces_custom_bound(self):
        dto = WebhookSubscriptionDTO(
            "gid://shopify/WebhookSubscription/27",
            TOPIC,
            CALLBACK_DIGEST,
            "2026-07",
            "JSON",
            (),
        )
        class IncompleteCollection:
            items = (dto,)
            complete = False

        with self.assertRaises(WebhookSubscriptionPlannerError) as incomplete:
            adapt_p07_collection(IncompleteCollection())
        self.assertEqual(incomplete.exception.code, "partial_read")
        with self.assertRaises(WebhookSubscriptionPlannerError) as oversized:
            adapt_p07_collection((dto, dto), maximum=1)
        self.assertEqual(oversized.exception.code, "input_too_large")

    def test_p07_spaced_include_field_is_rejected_instead_of_converging(self):
        dto = WebhookSubscriptionDTO(
            "gid://shopify/WebhookSubscription/28",
            TOPIC,
            CALLBACK_DIGEST,
            "2026-07",
            "JSON",
            (" id ",),
        )
        with self.assertRaises(WebhookSubscriptionPlannerError) as context:
            adapt_p07_subscription(dto)
        self.assertEqual(context.exception.code, "invalid_input")

    def test_p08_adapter_maps_callback_names_and_guards_blocked_plans(self):
        plan = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        create = plan.decisions[0]
        target = adapt_p08_target(create)
        self.assertEqual(target["operation_key"], WEBHOOK_SUBSCRIPTION_CREATE_OPERATION)
        self.assertEqual(target[P08_CALLBACK_URL_DIGEST_KEY], CALLBACK_DIGEST)
        self.assertNotIn(P11_CALLBACK_URI_DIGEST_KEY, target)
        self.assertEqual(adapt_p08_targets(plan), (target,))

        stale = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(29, api_version="2025-10")],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        targets = adapt_p08_targets(stale)
        self.assertEqual(
            [item["operation_key"] for item in targets],
            [WEBHOOK_SUBSCRIPTION_DELETE_OPERATION, WEBHOOK_SUBSCRIPTION_CREATE_OPERATION],
        )
        self.assertTrue(all(P08_CALLBACK_URL_DIGEST_KEY in item for item in targets))

        blocked = plan_webhook_subscriptions(
            [WebhookTopicSpec(TOPIC)],
            [_observed(30, digest="c" * 64)],
            callback_uri_digest=CALLBACK_DIGEST,
        )
        self.assertEqual(blocked.mutations, ())
        with self.assertRaises(WebhookSubscriptionPlannerError) as context:
            adapt_p08_targets(blocked)
        self.assertEqual(context.exception.code, "plan_blocked")

    def test_bounds_and_duplicate_desired_topics_fail_before_planning(self):
        with self.assertRaises(WebhookSubscriptionPlannerError) as context:
            plan_webhook_subscriptions(
                [WebhookTopicSpec(TOPIC), WebhookTopicSpec(TOPIC)],
                [],
                callback_uri=CALLBACK_URI,
            )
        self.assertEqual(context.exception.code, "duplicate_topic")
        planner = WebhookSubscriptionPlanner(
            max_topic_specs=1,
            max_current_subscriptions=1,
        )
        with self.assertRaises(WebhookSubscriptionPlannerError):
            planner.plan(
                [WebhookTopicSpec(TOPIC), WebhookTopicSpec(OTHER_TOPIC)],
                [],
                callback_uri=CALLBACK_URI,
            )
        with self.assertRaises(WebhookSubscriptionPlannerError):
            planner.plan(
                [WebhookTopicSpec(TOPIC)],
                [_observed(1), _observed(2)],
                callback_uri=CALLBACK_URI,
            )

    def test_callback_identity_is_validated_without_echoing_the_uri(self):
        with self.assertRaises(WebhookSubscriptionPlannerError) as context:
            plan_webhook_subscriptions([WebhookTopicSpec(TOPIC)], [], callback_uri="http://private-secret")
        self.assertEqual(context.exception.code, "invalid_callback_identity")
        self.assertNotIn("private-secret", str(context.exception))
        with self.assertRaises(WebhookSubscriptionPlannerError):
            plan_webhook_subscriptions([WebhookTopicSpec(TOPIC)], [], callback_uri=CALLBACK_URI, callback_uri_digest="a" * 64)


class P11BoundConstantsTests(unittest.TestCase):
    def test_bounds_are_positive_and_consistent_with_upstream_contracts(self):
        self.assertEqual(MAX_CURRENT_SUBSCRIPTIONS, 2_000)
        self.assertGreater(MAX_GRANTED_SCOPES, 0)
        self.assertGreater(MAX_TOPIC_SPECS, 0)


if __name__ == "__main__":
    unittest.main()
