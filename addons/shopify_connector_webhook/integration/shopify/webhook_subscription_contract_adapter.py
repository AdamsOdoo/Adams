"""Explicit naming/shape adapter between P07 facts and P08 mutations.

P07 calls the redacted callback identity ``uri_digest``.  P11's desired state
uses ``callback_uri_digest`` while P08's durable mutation intent uses the
legacy-compatible ``callback_url_digest`` key.  Keeping that translation in
one pure module prevents a future runtime adapter from silently comparing
different identities.  No raw URI is accepted or returned here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .webhook_subscription_mutation_gateway import (
    WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
    WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
)
from .webhook_subscription_planner_contracts import (
    MAX_CURRENT_SUBSCRIPTIONS,
    WebhookSubscriptionDecision,
    WebhookSubscriptionObserved,
    WebhookSubscriptionPlan,
    WebhookSubscriptionPlannerError,
    bounded_items,
    fail,
)


P07_URI_DIGEST_KEY = "uri_digest"
P11_CALLBACK_URI_DIGEST_KEY = "callback_uri_digest"
P08_CALLBACK_URL_DIGEST_KEY = "callback_url_digest"


def adapt_p07_subscription(value: Any) -> WebhookSubscriptionObserved:
    """Convert one P07 DTO/legacy-safe mapping to the P11 observation."""

    if isinstance(value, WebhookSubscriptionObserved):
        return value
    if isinstance(value, Mapping):
        return WebhookSubscriptionObserved.from_mapping(value)
    names = ("id", "topic", "uri_digest", "observed_api_version", "format", "include_fields")
    if all(hasattr(value, name) for name in names):
        return WebhookSubscriptionObserved(
            value.id,
            value.topic,
            value.uri_digest,
            value.observed_api_version,
            value.format,
            value.include_fields,
        )
    raise WebhookSubscriptionPlannerError(
        "invalid_observation", "Observed subscription is not a P07 safe DTO."
    )


def adapt_p07_collection(
    value: Any,
    *,
    maximum: int = MAX_CURRENT_SUBSCRIPTIONS,
) -> tuple[WebhookSubscriptionObserved, ...]:
    """Accept only a complete P07 collection, never a page or partial read."""

    if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= MAX_CURRENT_SUBSCRIPTIONS:
        fail("invalid_bound", "P07 collection bound is outside its safety limit.")
    if isinstance(value, (str, bytes, Mapping)):
        fail("invalid_observation", "current_subscriptions must be a P07 collection.")
    if hasattr(value, "has_next_page") or hasattr(value, "next_cursor"):
        fail("partial_read", "A P07 subscription page cannot establish complete state.")
    start_cursor = getattr(value, "start_cursor", None)
    if start_cursor is not None:
        fail("partial_read", "A subscription read with a starting cursor is incomplete.")
    complete = getattr(value, "complete", True)
    if not isinstance(complete, bool):
        fail("invalid_observation", "Read completeness must be a boolean.")
    if not complete:
        fail("partial_read", "A P07 subscription collection is incomplete.")
    source = getattr(value, "items", value)
    if callable(source):
        fail("partial_read", "A P07 subscription page cannot establish complete state.")
    return tuple(
        adapt_p07_subscription(item)
        for item in bounded_items(source, "current_subscriptions", maximum)
    )


def adapt_p08_target(decision: WebhookSubscriptionDecision) -> dict[str, Any]:
    """Return a safe P08 target using its exact legacy intent key names."""

    if not isinstance(decision, WebhookSubscriptionDecision):
        fail("invalid_plan", "P08 target conversion requires a subscription decision.")
    if decision.action == "create":
        return {
            "operation_key": WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
            "topic": decision.topic,
            P08_CALLBACK_URL_DIGEST_KEY: decision.callback_uri_digest,
            "expected_api_version": decision.expected_api_version,
            "expected_include_fields": list(decision.expected_include_fields),
            "depends_on": list(decision.depends_on),
        }
    if decision.action == "delete":
        return {
            "operation_key": WEBHOOK_SUBSCRIPTION_DELETE_OPERATION,
            "subscription_gid": decision.subscription_gid,
            "topic": decision.topic,
            P08_CALLBACK_URL_DIGEST_KEY: decision.observed_uri_digest,
        }
    fail("plan_not_executable", "Only create/delete decisions have P08 mutation targets.")


def adapt_p08_targets(plan: WebhookSubscriptionPlan) -> tuple[dict[str, Any], ...]:
    """Convert executable plan mutations, guarded globally by the plan."""

    if not isinstance(plan, WebhookSubscriptionPlan):
        fail("invalid_plan", "P08 target conversion requires a subscription plan.")
    return tuple(adapt_p08_target(item) for item in plan.require_executable())


__all__ = [
    "P07_URI_DIGEST_KEY",
    "P08_CALLBACK_URL_DIGEST_KEY",
    "P11_CALLBACK_URI_DIGEST_KEY",
    "adapt_p07_collection",
    "adapt_p07_subscription",
    "adapt_p08_target",
    "adapt_p08_targets",
]
