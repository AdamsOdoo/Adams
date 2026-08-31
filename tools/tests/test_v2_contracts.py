"""Dependency-free contract tests for the inert V2 P01 skeleton."""

from __future__ import annotations

import importlib
import json
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = REPO_ROOT / "addons" / "shopify_connector_core"


def _import_core_without_odoo() -> None:
    """Expose only the new package tree, bypassing the Odoo addon loader.

    The existing addon root imports ``models`` by design.  P01 contracts must
    be testable without Odoo, so the test supplies a namespace package for the
    pure contract modules instead of executing that legacy root initializer.
    """

    package = sys.modules.get("shopify_connector_core")
    if package is None:
        package = types.ModuleType("shopify_connector_core")
        package.__path__ = [str(CORE_ROOT)]
        package.__package__ = "shopify_connector_core"
        sys.modules["shopify_connector_core"] = package


_import_core_without_odoo()

from shopify_connector_core.application.command_contracts import (  # noqa: E402
    CommandEnvelope,
    CommandResult,
)
from shopify_connector_core.domain.authorization import (  # noqa: E402
    ROLE_CAPABILITIES,
    capability_for,
)
from shopify_connector_core.domain.dto import (  # noqa: E402
    AllowedActionDTO,
    AttentionDetailDTO,
    EvidenceGroupDTO,
    OperationOptionDTO,
    ResponseEnvelope,
    RunDTO,
    SetupDTO,
    SetupStepDTO,
    StoreSummaryDTO,
    WorkflowSummaryDTO,
)
from shopify_connector_core.domain.errors import ErrorCode, ProblemError  # noqa: E402
from shopify_connector_core.domain.immutability import to_plain  # noqa: E402
from shopify_connector_core.domain.registry import (  # noqa: E402
    DuplicateRegistryKey,
    Registry,
    RegistryFrozen,
    UnknownRegistryKey,
)
from shopify_connector_core.domain.retry_policy import DEFAULT_RETRY_POLICY, RetryPolicy  # noqa: E402
from shopify_connector_core.domain.states import (  # noqa: E402
    OperationMode,
    Role,
    SETUP_STEP_KEYS,
    SUPPORTED_STORE_CAPACITY,
)
from shopify_connector_core.integration.shopify.operation_registry import (  # noqa: E402
    ReadbackMetadata,
    ShopifyOperationRegistry,
    ShopifyOperationSpec,
    SideEffectMetadata,
)
from shopify_connector_core.runtime.contracts import (  # noqa: E402
    NeedsReview,
    NeedsVerification,
    Retryable,
    Skipped,
    Succeeded,
    TerminalFailure,
)
from shopify_connector_core.runtime.registries import (  # noqa: E402
    AttentionProviderSpec,
    AttentionRegistry,
    HandlerRegistry,
    JobHandlerSpec,
)


UTC = timezone.utc
NOW = datetime(2026, 8, 30, 12, 0, tzinfo=UTC)


class TestCommandAndReadContracts(unittest.TestCase):
    def test_command_envelope_is_frozen_and_scoped(self):
        envelope = CommandEnvelope(
            contract_version=1,
            command_id=uuid4(),
            command_name="start_operation_v1",
            store_id=7,
            company_id=2,
            expected_generation=18,
            actor_uid=11,
            trigger="user",
            requested_at=NOW,
            payload={"operation_key": "product_import"},
        )
        self.assertEqual(envelope.trigger, "user")
        with self.assertRaises(TypeError):
            envelope.payload["extra"] = True  # type: ignore[index]
        with self.assertRaises(Exception):
            envelope.store_id = 8  # type: ignore[misc]
        self.assertEqual(envelope.as_dict()["command_id"], str(envelope.command_id))

    def test_nested_payload_and_result_mappings_are_immutable(self):
        payload = {"filters": {"status": "pending"}, "lines": [{"sku": "SKU-1"}]}
        envelope = CommandEnvelope(
            1, uuid4(), "start_operation_v1", 1, 1, 0, 11, "user", NOW, payload
        )
        payload["filters"]["status"] = "changed"
        self.assertEqual(envelope.payload["filters"]["status"], "pending")
        with self.assertRaises(TypeError):
            envelope.payload["filters"]["status"] = "changed"  # type: ignore[index]
        with self.assertRaises(TypeError):
            envelope.payload["lines"][0]["sku"] = "changed"  # type: ignore[index]
        self.assertEqual(envelope.as_dict()["payload"]["filters"]["status"], "pending")

        result = {"summary": {"count": 1}, "records": [{"id": "gid://shopify/Product/1"}]}
        run = RunDTO(
            "run:1", "Product import", "requested", "product", "import",
            {}, {}, {}, 0, result, (), (), ()
        )
        with self.assertRaises(TypeError):
            run.result["summary"]["count"] = 2  # type: ignore[index]

    def test_system_trigger_is_the_only_actorless_trigger(self):
        with self.assertRaises(ValueError):
            CommandEnvelope(
                1, uuid4(), "test_connection_v1", 1, 1, 0, None, "user", NOW, {}
            )
        envelope = CommandEnvelope(
            1, uuid4(), "test_connection_v1", 1, 1, 0, None, "system", NOW, {}
        )
        self.assertEqual(envelope.trigger, "system")

    def test_command_result_and_common_envelope_are_frozen_contracts(self):
        result = CommandResult("accepted", "run:392", None, "Admitted", None)
        self.assertEqual(result.as_dict()["status"], "accepted")
        response = ResponseEnvelope(1, NOW, NOW, 18, "sc_01", {"result": result.as_dict()})
        self.assertEqual(response.as_dict()["contract_version"], 1)
        self.assertEqual(json.loads(json.dumps(response.as_dict()))["data"]["result"]["status"], "accepted")
        with self.assertRaises(ValueError):
            ResponseEnvelope(2, NOW, NOW, 18, "sc_01", {})
        with self.assertRaises(ValueError):
            ResponseEnvelope(1, NOW, NOW.replace(hour=13), 18, "sc_01", {})

    def test_nested_contract_values_are_json_safe_and_reject_invalid_values(self):
        with self.assertRaises(TypeError):
            CommandEnvelope(
                1, uuid4(), "start_operation_v1", 1, 1, 0, 11, "user", NOW,
                {"nested": {"bad": object()}},
            )
        with self.assertRaises(TypeError):
            CommandEnvelope(
                1, uuid4(), "start_operation_v1", 1, 1, 0, 11, "user", NOW,
                {"nested": {1: "not a contract key"}},
            )
        with self.assertRaises(ValueError):
            CommandEnvelope(
                1, uuid4(), "start_operation_v1", 1, 1, 0, 11, "user", NOW,
                {"number": float("nan")},
            )
        plain = to_plain({"role": Role.OPERATOR, "command_id": uuid4(), "at": NOW})
        self.assertEqual(plain["role"], "operator")
        self.assertIsInstance(plain["command_id"], str)
        self.assertEqual(plain["at"], NOW.isoformat())
        with self.assertRaises(ValueError):
            to_plain(datetime(2026, 8, 30, 12, 0))
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        with self.assertRaises(ValueError):
            to_plain(cyclic)
        with self.assertRaises(ValueError):
            CommandEnvelope(
                1, uuid4(), "start_operation_v1", 1, 1, 0, 11, "user", NOW, cyclic,
            )

    def test_public_problem_shape_has_only_stable_error_codes(self):
        problem = ProblemError(
            ErrorCode.STATE_CONFLICT,
            "This item changed",
            "Refresh before resolving it.",
            False,
            {"state_version": "stale"},
            "attn:inventory:7:3",
            "run:392",
            "sc_01",
        )
        self.assertEqual(problem.code, "state_conflict")
        with self.assertRaises(ValueError):
            ProblemError("raw_exception", "x", "y", False, {}, None, None, "sc_01")


class TestLockedVocabulary(unittest.TestCase):
    def test_roles_capacity_setup_keys_and_retry_policy(self):
        self.assertEqual(SUPPORTED_STORE_CAPACITY, 10)
        self.assertEqual(
            set(ROLE_CAPABILITIES),
            {Role.ADMINISTRATOR, Role.OPERATOR, Role.REVIEWER, Role.AUDITOR},
        )
        self.assertTrue(capability_for(Role.OPERATOR).can_resolve)
        self.assertTrue(capability_for(Role.REVIEWER).can_resolve)
        self.assertFalse(capability_for(Role.REVIEWER).can_configure)
        self.assertFalse(capability_for(Role.REVIEWER).can_operate)
        self.assertFalse(capability_for(Role.AUDITOR).can_resolve)
        self.assertEqual(len(SETUP_STEP_KEYS), 12)
        self.assertEqual(DEFAULT_RETRY_POLICY.base_delay_seconds, 30)
        self.assertEqual(DEFAULT_RETRY_POLICY.multiplier, 2)
        self.assertEqual(DEFAULT_RETRY_POLICY.max_delay_seconds, 1800)
        self.assertEqual(DEFAULT_RETRY_POLICY.jitter_ratio, 0.20)
        self.assertEqual(DEFAULT_RETRY_POLICY.max_scheduled_retries, 12)
        self.assertEqual(DEFAULT_RETRY_POLICY.window_seconds, 86400)
        self.assertEqual(DEFAULT_RETRY_POLICY.delay_seconds(1), 30)
        self.assertEqual(DEFAULT_RETRY_POLICY.delay_seconds(7), 1800)
        self.assertEqual(DEFAULT_RETRY_POLICY.jitter_bounds(1), (24.0, 36.0))

    def test_setup_step_address_is_semantic_not_ordinal(self):
        step = SetupStepDTO("credential", "complete", NOW, 0, None, 3)
        self.assertEqual(step.step_key, "credential")
        with self.assertRaises(ValueError):
            SetupStepDTO("3", "complete", NOW, 0, None, 3)
        dto = SetupDTO({}, (step,), step, (), {}, {})
        self.assertEqual(dto.current_step.step_key, "credential")
        with self.assertRaises(ValueError):
            SetupDTO({}, (step, step), step, (), {}, {})
        with self.assertRaises(ValueError):
            SetupDTO({}, (step,), SetupStepDTO("identity", "complete", NOW, 0, None), (), {}, {})

    def test_locked_state_role_and_operation_mode_values_fail_closed(self):
        with self.assertRaises(ValueError):
            AllowedActionDTO("operate", "Operate", required_role="superuser")
        with self.assertRaises(ValueError):
            RunDTO("run:2", "Run", "not_a_run_state", "product", "import", {}, {}, {}, 0, {}, (), (), ())
        store = StoreSummaryDTO(
            1, "Store", "store.myshopify.com", {"id": 1},
            "connected", "valid", "active", "healthy",
        )
        with self.assertRaises(ValueError):
            StoreSummaryDTO(1, "Store", "store.myshopify.com", {}, "broken", "valid", "active", "healthy")
        workflow = WorkflowSummaryDTO("product", "Product", "ready", "healthy", {}, 0, None)
        self.assertEqual(workflow.readiness, "ready")
        option = OperationOptionDTO(
            "product.import", "Import", "product", OperationMode.READ,
            Role.OPERATOR.value, ("store",), {}, "Shopify", "No write", "ready",
        )
        self.assertEqual(option.mode, "read")
        self.assertEqual(store.connection, "connected")
        with self.assertRaises(TypeError):
            OperationOptionDTO(
                "product.import", "Import", "product", OperationMode.READ,
                Role.OPERATOR.value, "store", {}, "Shopify", "No write",
                "ready",
            )

    def test_retry_policy_rejects_bool_and_out_of_range_inputs(self):
        with self.assertRaises(TypeError):
            RetryPolicy(base_delay_seconds=True)
        with self.assertRaises(TypeError):
            RetryPolicy(jitter_ratio=True)
        with self.assertRaises(TypeError):
            DEFAULT_RETRY_POLICY.delay_seconds(True)
        with self.assertRaises(ValueError):
            DEFAULT_RETRY_POLICY.delay_seconds(13)
        # Rejection occurs before any exponentiation/loop proportional to this
        # attacker-controlled value.
        with self.assertRaises(ValueError):
            DEFAULT_RETRY_POLICY.delay_seconds(10**100)


class TestRegistries(unittest.TestCase):
    def test_registry_is_duplicate_safe_unknown_safe_and_freezable(self):
        registry = Registry[int]((("one", 1),))
        with self.assertRaises(DuplicateRegistryKey):
            registry.register("one", 2)
        with self.assertRaises(UnknownRegistryKey):
            registry.require("missing")
        registry.freeze()
        with self.assertRaises(RegistryFrozen):
            registry.register("two", 2)
        self.assertEqual(registry.snapshot()["one"], 1)

    def test_bulk_registration_is_atomic_for_generic_and_typed_registries(self):
        registry = Registry[int]((("existing", 1),))
        with self.assertRaises(DuplicateRegistryKey):
            registry.register_many((("new", 2), ("existing", 3)))
        self.assertEqual(registry.keys(), ("existing",))
        with self.assertRaises(DuplicateRegistryKey):
            registry.register_many((("same", 2), ("same", 3)))
        self.assertEqual(registry.keys(), ("existing",))

        first = JobHandlerSpec(
            "catalog.read", "shopify_connector_product", "scheduled",
            False, None, (), dict, lambda: None,
        )
        duplicate = JobHandlerSpec(
            "catalog.read", "shopify_connector_product", "interactive",
            False, None, (), dict, lambda: None,
        )
        handlers = HandlerRegistry(())
        with self.assertRaises(DuplicateRegistryKey):
            handlers.register_many((first, duplicate))
        self.assertEqual(handlers.keys(), ())

        provider = AttentionProviderSpec(
            "catalog.review", "product", lambda: None,
        )
        duplicate_provider = AttentionProviderSpec(
            "catalog.review", "product", lambda: None,
        )
        providers = AttentionRegistry(())
        with self.assertRaises(DuplicateRegistryKey):
            providers.register_many((provider, duplicate_provider))
        self.assertEqual(providers.keys(), ())

    def test_operation_registry_requires_named_mutation_and_readback(self):
        read = ShopifyOperationSpec(
            "store.identity",
            "StoreIdentity",
            "query",
            "2026-07",
            "query StoreIdentity { shop { id } }",
            {},
            "StoreResult",
            "GraphQLError",
            SideEffectMetadata("observe", "Reads the shop identity.", False),
        )
        mutation = ShopifyOperationSpec(
            "product.update",
            "ProductUpdate",
            "mutation",
            "2026-07",
            "mutation ProductUpdate($id: ID!) { productUpdate(product: {id: $id}) { userErrors { message } } }",
            {"id": "ID!"},
            "ProductResult",
            "GraphQLError",
            SideEffectMetadata("update", "Updates one product.", True),
            ReadbackMetadata(True, "product.read", "read the canonical product GID", "Confirm product state."),
        )
        product_read = ShopifyOperationSpec(
            "product.read",
            "ProductRead",
            "query",
            "2026-07",
            "query ProductRead($id: ID!) { product(id: $id) { id } }",
            {"id": "ID!"},
            "ProductResult",
            "GraphQLError",
            SideEffectMetadata("observe", "Reads the canonical product.", False),
        )
        registry = ShopifyOperationRegistry((read, product_read))
        registry.register_many((mutation,))
        self.assertIs(registry.require_operation("product.update"), mutation)
        with self.assertRaises(DuplicateRegistryKey):
            registry.register(read)
        with self.assertRaises(UnknownRegistryKey):
            registry.require_operation("unknown")
        with self.assertRaises(ValueError):
            ShopifyOperationSpec(
                "unsafe.operation",
                "Unnamed",
                "mutation",
                "2026-07",
                "mutation { productUpdate { userErrors { message } } }",
                {},
                "Result",
                "Error",
                SideEffectMetadata("update", "Updates a product.", True),
            )

    def test_operation_documents_and_readbacks_are_exact_and_immutable(self):
        with self.assertRaises(ValueError):
            ShopifyOperationSpec(
                "product.read", "ProductRead", "query", "2026-07",
                "query ProductRead { product { id } } query Other { shop { id } }",
                {}, "Result", "Error", SideEffectMetadata("observe", "Read", False),
            )
        with self.assertRaises(ValueError):
            ShopifyOperationSpec(
                "product.read", "ProductRead", "query", "2026-07",
                "query ProductRead($id: ID!) { product(id: $id) { id } }",
                {}, "Result", "Error", SideEffectMetadata("observe", "Read", False),
            )
        with self.assertRaises(ValueError):
            ShopifyOperationSpec(
                "product.read", "ProductRead", "query", "2026-07",
                "query ProductRead { product { id } }",
                {}, "Result", "Error", SideEffectMetadata("observe", "Read", False),
                ReadbackMetadata(False, None, "read", "not allowed"),
            )
        readback = ReadbackMetadata(True, "product.read", "Read once", "Confirm", ["applied", "not_applied"])
        self.assertEqual(readback.outcomes, ("applied", "not_applied"))
        with self.assertRaises(Exception):
            readback.outcomes += ("inconclusive",)  # type: ignore[misc]
        with self.assertRaises(ValueError):
            ReadbackMetadata(True, "product.read", "Read", "Confirm", ["applied", "applied"])

    def test_refund_and_payout_extensions_register_additively(self):
        def spec(key, name, operation_type, document, variables, side_effect, readback=None):
            return ShopifyOperationSpec(
                key, name, operation_type, "2026-07", document, variables,
                "Result", "GraphQLError", side_effect, readback or ReadbackMetadata(),
            )

        refund_read = spec(
            "refund.read", "RefundEvidence", "query",
            "query RefundEvidence($id: ID!) { order(id: $id) { id } }", {"id": "ID!"},
            SideEffectMetadata("observe", "Reads refund evidence.", False),
        )
        payout_read = spec(
            "payout.read", "PayoutEvidence", "query",
            "query PayoutEvidence($id: ID!) { shop { id } }", {"id": "ID!"},
            SideEffectMetadata("observe", "Reads payout evidence.", False),
        )
        refund_mutation = spec(
            "refund.create", "RefundCreate", "mutation",
            "mutation RefundCreate($id: ID!) { order(id: $id) { id } }", {"id": "ID!"},
            SideEffectMetadata("create", "Creates a refund after policy approval.", True),
            ReadbackMetadata(True, "refund.read", "Read the refund evidence.", "Confirm refund state."),
        )
        payout_mutation = spec(
            "payout.reconcile", "PayoutReconcile", "mutation",
            "mutation PayoutReconcile($id: ID!) { shop { id } }", {"id": "ID!"},
            SideEffectMetadata("reconcile", "Reconciles a payout after accounting approval.", True),
            ReadbackMetadata(True, "payout.read", "Read the payout evidence.", "Confirm payout state."),
        )
        operations = ShopifyOperationRegistry((refund_mutation, refund_read, payout_mutation, payout_read))
        self.assertIs(operations.require_operation("payout.reconcile"), payout_mutation)
        handlers = HandlerRegistry(())
        handlers.register_many((
            JobHandlerSpec(
                "refund.create", "shopify_connector_refund", "interactive", True,
                Role.ADMINISTRATOR.value, ("refund.read",), dict, lambda: None, lambda: None,
            ),
            JobHandlerSpec(
                "payout.reconcile", "shopify_connector_payout", "reconciliation", True,
                Role.ADMINISTRATOR.value, ("payout.read",), dict, lambda: None, lambda: None,
            ),
        ))
        providers = AttentionRegistry((
            AttentionProviderSpec("refund.review", "refund", lambda: None),
            AttentionProviderSpec("payout.review", "payout", lambda: None),
        ))
        self.assertEqual(handlers.require_handler("payout.reconcile").required_role, "administrator")
        self.assertEqual(providers.require_provider("refund.review").workflow, "refund")

    def test_operation_registry_rejects_dangling_or_duplicate_graphql_names_atomically(self):
        query = ShopifyOperationSpec(
            "product.read", "ProductRead", "query", "2026-07",
            "query ProductRead { product { id } }", {}, "Result", "Error",
            SideEffectMetadata("observe", "Read", False),
        )
        mutation = ShopifyOperationSpec(
            "product.update", "ProductUpdate", "mutation", "2026-07",
            "mutation ProductUpdate { productUpdate { userErrors { message } } }", {},
            "Result", "Error", SideEffectMetadata("update", "Update", True),
            ReadbackMetadata(True, "missing.read", "Read", "Confirm"),
        )
        registry = ShopifyOperationRegistry((query,))
        with self.assertRaises(ValueError):
            registry.register(mutation)
        self.assertEqual(registry.keys(), ("product.read",))
        duplicate_name = ShopifyOperationSpec(
            "other.read", "ProductRead", "query", "2026-07",
            "query ProductRead { shop { id } }", {}, "Result", "Error",
            SideEffectMetadata("observe", "Read", False),
        )
        with self.assertRaises(DuplicateRegistryKey):
            registry.register(duplicate_name)

    def test_handler_and_attention_registries_are_explicit(self):
        handler_factory = lambda: None
        verify_factory = lambda: None
        handler = JobHandlerSpec(
            "inventory_push",
            "shopify_connector_inventory",
            "odoo_event",
            True,
            None,
            ("inventory.mapping",),
            dict,
            handler_factory,
            verify_factory,
        )
        attention = AttentionProviderSpec(
            "inventory.mapping",
            "inventory",
            lambda: None,
            ("map_location",),
        )
        second_handler = JobHandlerSpec(
            "inventory_pull",
            "shopify_connector_inventory",
            "scheduled",
            False,
            None,
            ("inventory.mapping",),
            dict,
            handler_factory,
        )
        second_attention = AttentionProviderSpec(
            "inventory.conflict",
            "inventory",
            lambda: None,
            ("resolve_conflict",),
        )
        handlers = HandlerRegistry((handler,))
        providers = AttentionRegistry((attention,))
        handlers.register_many((second_handler,))
        providers.register_many((second_attention,))
        self.assertIs(handlers.require_handler("inventory_push"), handler)
        self.assertIs(providers.require_provider("inventory.mapping"), attention)
        self.assertIs(handlers.require_handler("inventory_pull"), second_handler)
        self.assertIs(providers.require_provider("inventory.conflict"), second_attention)
        with self.assertRaises(ValueError):
            JobHandlerSpec("unsafe", "core", "odoo_event", True, None, (), dict, handler_factory)
        with self.assertRaises(ValueError):
            JobHandlerSpec(
                "unsafe_role", "core", "odoo_event", True, "superuser",
                (), dict, handler_factory, verify_factory,
            )
        with self.assertRaises(TypeError):
            JobHandlerSpec(
                "unsafe_keys", "core", "scheduled", False, None,
                "readiness.key", dict, handler_factory,
            )
        with self.assertRaises(TypeError):
            AttentionProviderSpec(
                "unsafe.actions", "core", lambda: None, "retry_job",
            )


class TestDTOAndHandlerOutcomes(unittest.TestCase):
    def test_attention_detail_and_handler_outcomes_are_frozen(self):
        action = AllowedActionDTO("open_attention", "Open review")
        detail = AttentionDetailDTO(
            "attn:inventory:7:3",
            3,
            "inventory.mapping",
            "inventory",
            "critical",
            "Mapping required",
            "One pair is held.",
            42,
            "reviewer",
            7,
            "run:392",
            (action,),
            "A location has no approved mapping.",
            {"held_records": 1},
            (EvidenceGroupDTO("incoming", "Incoming evidence", ()),),
            (),
        )
        self.assertEqual(detail.allowed_actions[0].key, "open_attention")
        self.assertEqual(Succeeded({}).observations, {})
        self.assertEqual(Skipped("already handled").reason, "already handled")
        self.assertEqual(Retryable("shopify_throttled", NOW).retry_at, NOW)
        self.assertEqual(NeedsVerification(7, "readback").mutation_attempt_id, 7)
        self.assertEqual(NeedsReview("ambiguous", "choose a match").reason_code, "ambiguous")
        self.assertFalse(TerminalFailure("shopify_validation", True).observations)
        with self.assertRaises(Exception):
            detail.title = "changed"  # type: ignore[misc]

    def test_needs_review_keeps_observations_as_third_positional_argument(self):
        observations = {"source": "handler"}
        review = NeedsReview("ambiguous", "choose a match", observations)
        self.assertEqual(review.observations["source"], "handler")
        self.assertIsNone(review.error_class)

    def test_needs_review_accepts_allowlisted_source_error_class_and_is_frozen(self):
        review = NeedsReview(
            "ambiguous",
            "choose a match",
            {},
            error_class="mapping_missing",
        )
        self.assertEqual(review.error_class, "mapping_missing")
        with self.assertRaises(Exception):
            review.error_class = "duplicate_risk"  # type: ignore[misc]

    def test_needs_review_rejects_invalid_source_error_class_values(self):
        with self.assertRaises(TypeError):
            NeedsReview("ambiguous", "choose a match", error_class=7)
        for value in ("", "   "):
            with self.subTest(value=value), self.assertRaises(ValueError):
                NeedsReview("ambiguous", "choose a match", error_class=value)
        with self.assertRaises(ValueError):
            NeedsReview(
                "ambiguous",
                "choose a match",
                error_class="unregistered_source_error",
            )


if __name__ == "__main__":
    unittest.main()
