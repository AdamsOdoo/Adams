"""Cheap P11 runtime tests with a fake durable ledger.

The ORM adapter is intentionally exercised separately by Odoo's transaction
suite.  These tests prove the invariant that remains true at either boundary:
admission precedes intent, intent precedes one gateway call, and uncertainty
never becomes an automatic second mutation.
"""

from __future__ import annotations

import ast
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


from shopify_connector_core.integration.shopify.mutation_contracts import (  # noqa: E402
    MutationTransportError,
)
from shopify_connector_webhook.integration.shopify.webhook_subscription_mutation_gateway import (  # noqa: E402
    WebhookSubscriptionMutationGateway,
    WEBHOOK_SUBSCRIPTION_CREATE_OPERATION,
    WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
)
from shopify_connector_webhook.integration.shopify.webhook_subscription_runtime import (  # noqa: E402
    SubscriptionMutationRuntime,
    SubscriptionReadback,
    SubscriptionRuntimeAdmission,
    SubscriptionRuntimeError,
)


CALLBACK = "https://connector.example/webhook?secret=fixture-secret"
SUBSCRIPTION = "gid://shopify/WebhookSubscription/7"


def _response(*, errors=None, subscription=SUBSCRIPTION):
    payload = {
        "webhookSubscription": {
            "id": subscription,
            "topic": "ORDERS_CREATE",
            "uri": CALLBACK,
            "apiVersion": {
                "handle": "2026-07",
                "displayName": "July 2026",
                "supported": True,
            },
            "format": "JSON",
            "includeFields": ["id"],
        },
        "userErrors": errors or [],
    }
    return {"data": {"webhookSubscriptionCreate": payload}}


class Delegate:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def execute(self, operation, variables):
        self.calls.append((operation, variables))
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


class Ledger:
    def __init__(self, *, existing=None, commit=True):
        self.existing = existing
        self.commit = commit
        self.events = []
        self.intents = []
        self.outcomes = []

    def find(self, fingerprint):
        self.events.append(("find", fingerprint))
        return self.existing

    def commit_intent(self, request):
        self.events.append(("commit", request.intent.fingerprint))
        if isinstance(self.commit, BaseException):
            raise self.commit
        if self.commit:
            self.intents.append(request.intent.as_dict())
        return self.commit

    def record_outcome(self, fingerprint, outcome, evidence):
        self.events.append(("outcome", outcome))
        self.outcomes.append((fingerprint, outcome, dict(evidence)))


def _admission(**changes):
    values = {
        "runtime_mode": "subscriptions",
        "store_id": 11,
        "company_id": 3,
        "expected_connection_generation": 4,
        "current_connection_generation": 4,
        "expected_configuration_generation": 8,
        "current_configuration_generation": 8,
    }
    values.update(changes)
    return SubscriptionRuntimeAdmission(**values)


class P11RuntimeTests(unittest.TestCase):
    def test_orm_reconcile_passes_stored_granted_scope_snapshot_to_planner(self):
        source = (
            ROOT
            / "addons"
            / "shopify_connector_webhook"
            / "models"
            / "shopify_connector_webhook_subscription_v2_reconciliation.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        reconcile = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_reconcile_store"
        )
        planner_calls = [
            node
            for node in ast.walk(reconcile)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "plan_webhook_subscriptions"
        ]
        self.assertEqual(len(planner_calls), 1)
        granted_scopes = next(
            (
                keyword.value
                for keyword in planner_calls[0].keywords
                if keyword.arg == "granted_scopes"
            ),
            None,
        )
        self.assertIsInstance(granted_scopes, ast.Call)
        self.assertIsInstance(granted_scopes.func, ast.Attribute)
        self.assertEqual(granted_scopes.func.attr, "_v2_granted_scopes")
        self.assertEqual(len(granted_scopes.args), 1)
        self.assertIsInstance(granted_scopes.args[0], ast.Name)
        self.assertEqual(granted_scopes.args[0].id, "store")

    def _request(self, delegate=None):
        gateway = WebhookSubscriptionMutationGateway(
            delegate or Delegate(_response()),
            WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
        )
        return gateway.build_create(
            "ORDERS_CREATE",
            CALLBACK,
            include_fields=("id",),
            idempotency_key="runtime-1",
            operation_scope_key="webhook_subscription:11",
            business_intent={
                "action": "create",
                "subscription_id": 11,
                "callback_url_digest": hashlib.sha256(
                    CALLBACK.encode("utf-8")
                ).hexdigest(),
            },
            preconditions_snapshot={
                "expected_connection_generation": 4,
                "expected_configuration_generation": 8,
            },
        )

    def test_intent_is_committed_before_one_delegate_call_and_requires_readback(self):
        delegate = Delegate(_response())
        ledger = Ledger()
        result = SubscriptionMutationRuntime(
            WebhookSubscriptionMutationGateway(
                delegate, WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
            ),
            ledger,
        ).execute(self._request(delegate), _admission())
        self.assertEqual(result.decision, "verification_required")
        self.assertTrue(result.readback_required)
        self.assertEqual(len(delegate.calls), 1)
        self.assertEqual([event[0] for event in ledger.events[:2]], ["find", "commit"])
        self.assertEqual(ledger.events[2][0], "outcome")
        self.assertEqual(ledger.outcomes[0][1], "uncertain")
        self.assertNotIn("fixture-secret", str(result.as_dict()))

    def test_readback_can_apply_or_block_external_ownership_without_resend(self):
        for observation, expected in (
            (SubscriptionReadback("applied", "exact connector-owned match"), "applied"),
            (SubscriptionReadback("blocked", "callback belongs to another owner", ownership="external"), "blocked"),
        ):
            with self.subTest(expected=expected):
                delegate = Delegate(_response())
                ledger = Ledger()
                result = SubscriptionMutationRuntime(
                    WebhookSubscriptionMutationGateway(
                        delegate, WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
                    ),
                    ledger,
                ).execute(
                    self._request(delegate),
                    _admission(),
                    readback=lambda request, mutation: observation,
                )
                self.assertEqual(result.decision, expected)
                self.assertFalse(result.readback_required)
                self.assertEqual(len(delegate.calls), 1)
                self.assertEqual(ledger.outcomes[-1][1], expected)

    def test_timeout_before_send_is_clean_and_timeout_after_send_is_uncertain(self):
        for error, expected, required in (
            (MutationTransportError(after_send=False), "failed_clean", False),
            (MutationTransportError(after_send=True), "verification_required", True),
        ):
            with self.subTest(expected=expected):
                delegate = Delegate(error)
                ledger = Ledger()
                result = SubscriptionMutationRuntime(
                    WebhookSubscriptionMutationGateway(
                        delegate, WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
                    ),
                    ledger,
                ).execute(self._request(delegate), _admission())
                self.assertEqual(result.decision, expected)
                self.assertEqual(result.readback_required, required)
                self.assertEqual(len(delegate.calls), 1)

    def test_duplicate_or_commit_failure_never_calls_delegate(self):
        delegate = Delegate(_response())
        existing = Ledger(existing={"readback_required": True})
        result = SubscriptionMutationRuntime(
            WebhookSubscriptionMutationGateway(
                delegate, WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
            ),
            existing,
        ).execute(self._request(delegate), _admission())
        self.assertEqual(result.decision, "duplicate")
        self.assertEqual(delegate.calls, [])

        failed = Ledger(commit=RuntimeError("credential-secret"))
        with self.assertRaisesRegex(SubscriptionRuntimeError, "not committed"):
            SubscriptionMutationRuntime(
                WebhookSubscriptionMutationGateway(
                    delegate, WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
                ),
                failed,
            ).execute(self._request(delegate), _admission())
        self.assertEqual(delegate.calls, [])
        self.assertNotIn("credential-secret", str(failed.outcomes))

    def test_admission_fences_mode_state_and_generations_before_ledger(self):
        invalid = (
            {"runtime_mode": "legacy"},
            {"store_state": "disconnected"},
            {"run_state": "cancelled"},
            {"expected_connection_generation": 3},
            {"current_configuration_generation": 9},
        )
        for change in invalid:
            with self.subTest(change=change):
                with self.assertRaises(SubscriptionRuntimeError):
                    _admission(**change)

    def test_result_and_admission_are_immutable(self):
        admission = _admission()
        with self.assertRaisesRegex((AttributeError, TypeError), ""):
            admission.store_id = 22

        request = self._request()
        result = SubscriptionMutationRuntime(
            WebhookSubscriptionMutationGateway(
                Delegate(_response()), WEBHOOK_SUBSCRIPTION_MUTATION_REGISTRY,
            ),
            Ledger(),
        ).execute(request, admission)
        with self.assertRaisesRegex((AttributeError, TypeError), ""):
            result.decision = "applied"


if __name__ == "__main__":
    unittest.main()
