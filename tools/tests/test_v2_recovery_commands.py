"""Dependency-free tests for the P04 recovery command contracts."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = REPO_ROOT / "addons" / "shopify_connector_core"
package = sys.modules.get("shopify_connector_core")
if package is None:
    package = types.ModuleType("shopify_connector_core")
    package.__path__ = [str(CORE_ROOT)]
    package.__package__ = "shopify_connector_core"
    sys.modules["shopify_connector_core"] = package

from shopify_connector_core.runtime.p04_recovery import (  # noqa: E402
    AttentionCommand,
    GenerationSnapshot,
    RecoveryContractError,
    cancellation_requires_quiescence,
    mutation_action_is_safe,
    parse_attention_ref,
    parse_run_ref,
)


class TestP04RecoveryContracts(unittest.TestCase):
    def test_attention_command_is_immutable_and_exact(self):
        command = AttentionCommand(
            "attn:manual_review_job:7:11",
            11,
            "resolve_manual_review",
            {},
            "The mapping was verified by the merchant.",
        )
        self.assertEqual(command.provider, "manual_review_job")
        self.assertEqual(command.source_id, 7)
        with self.assertRaises(TypeError):
            command.inputs["extra"] = True  # type: ignore[index]
        with self.assertRaises(RecoveryContractError):
            AttentionCommand(
                "attn:manual_review_job:7:11", 10, "resolve_manual_review", {}, "x"
            )

    def test_attention_payload_rejects_unknown_keys_and_unsafe_inputs(self):
        with self.assertRaises(RecoveryContractError):
            AttentionCommand.from_mapping({
                "item_ref": "attn:manual_review_job:7:11",
                "state_version": 11,
                "action_key": "resolve_manual_review",
                "unexpected": True,
            })
        with self.assertRaises(RecoveryContractError):
            AttentionCommand(
                "attn:mutation_uncertainty:7:11",
                11,
                "resolve_mutation",
                {"disposition": "applied", "extra": "no"},
                "verified",
            )
        with self.assertRaises(RecoveryContractError):
            AttentionCommand(
                "attn:mutation_uncertainty:7:11",
                11,
                "resolve_mutation",
                {"disposition": "applied"},
                "",
            )
        with self.assertRaises(RecoveryContractError):
            AttentionCommand(
                "attn:mutation_uncertainty:7:11",
                11,
                "resolve_mutation",
                {"disposition": True},
                "verified",
            )

    def test_navigation_and_optional_provider_actions_are_known_but_closed(self):
        # The UI may return these keys, but the Odoo adapter has no core write
        # service for them.  Keeping them in the vocabulary lets the adapter
        # return a deterministic blocked result instead of accepting reflection.
        for provider, action in (
            ("manual_review_job", "open_run"),
            ("product_match", "open_match_decision"),
            ("inventory_mapping", "map_location_and_preview"),
            ("fulfillment_review", "open_fulfillment_review"),
            ("readiness_failure", "repair_setup"),
        ):
            command = AttentionCommand(
                f"attn:{provider}:7:11", 11, action, {}, None
            )
            self.assertEqual(command.action_key, action)

    def test_run_references_are_bounded_and_do_not_accept_bool_ids(self):
        self.assertEqual(parse_run_ref("job:7"), ("job", 7))
        self.assertEqual(parse_run_ref("run:9"), ("run", 9))
        self.assertEqual(parse_run_ref(7), ("job", 7))
        for value in (True, False, "job:0", "model:7", "run:1:extra", object()):
            with self.subTest(value=value):
                with self.assertRaises(RecoveryContractError):
                    parse_run_ref(value)
        with self.assertRaises(RecoveryContractError):
            parse_attention_ref("attn:unknown_provider:7:11")

    def test_generations_are_nonnegative_and_exact(self):
        snapshot = GenerationSnapshot(4, 8)
        self.assertTrue(snapshot.matches(connection_generation=4, configuration_generation=8))
        self.assertFalse(snapshot.matches(connection_generation=5, configuration_generation=8))
        with self.assertRaises(RecoveryContractError):
            GenerationSnapshot(-1, 0)
        with self.assertRaises(RecoveryContractError):
            GenerationSnapshot(0, True)

    def test_uncertain_mutation_has_only_explicit_resolution(self):
        self.assertTrue(mutation_action_is_safe("uncertain", "resolve_mutation"))
        self.assertFalse(mutation_action_is_safe("uncertain", "retry_job"))
        self.assertFalse(mutation_action_is_safe("uncertain", "cancel_job"))
        self.assertTrue(mutation_action_is_safe(None, "retry_job"))

    def test_cancellation_waits_for_running_or_evidence_linked_work(self):
        self.assertFalse(cancellation_requires_quiescence("queued", False))
        self.assertTrue(cancellation_requires_quiescence("running", False))
        self.assertTrue(cancellation_requires_quiescence("queued", True))


if __name__ == "__main__":
    unittest.main()
