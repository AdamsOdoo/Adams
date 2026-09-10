"""Dependency-free source guards for the P15 private replay seam."""

import ast
from pathlib import Path
import sys
import types
import unittest


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = REPO_ROOT / "addons" / "shopify_connector_core"
RESULT_SOURCE = (
    REPO_ROOT / "addons" / "shopify_connector_core" / "models"
    / "shopify_connector_command_result.py"
)
REPLAY_SOURCE = (
    REPO_ROOT / "addons" / "shopify_connector_core" / "models"
    / "shopify_connector_p15_command_replay.py"
)
OPERATIONS_SOURCE = (
    REPO_ROOT / "addons" / "shopify_connector_core" / "models"
    / "shopify_connector_p15_operations.py"
)
ACL_SOURCE = (
    REPO_ROOT / "addons" / "shopify_connector_core" / "security"
    / "ir.model.access.csv"
)

if "shopify_connector_core" not in sys.modules:
    package = types.ModuleType("shopify_connector_core")
    package.__path__ = [str(CORE_ROOT)]
    package.__package__ = "shopify_connector_core"
    sys.modules["shopify_connector_core"] = package

from shopify_connector_core.domain.p15_foundation import (  # noqa: E402
    MAX_COMMAND_RESULT_DEPTH,
    sanitize_command_result,
)


class TestP15CommandResultSourceGuards(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.result_text = RESULT_SOURCE.read_text(encoding="utf-8")
        cls.result_tree = ast.parse(cls.result_text)
        cls.replay_text = REPLAY_SOURCE.read_text(encoding="utf-8")
        cls.operation_text = OPERATIONS_SOURCE.read_text(encoding="utf-8")
        cls.acl_text = ACL_SOURCE.read_text(encoding="utf-8")

    def test_result_helpers_are_private_and_capability_gated(self):
        function_names = {
            node.name
            for node in ast.walk(self.result_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        self.assertNotIn("lock_scope", function_names)
        self.assertNotIn("find_for_command", function_names)
        self.assertNotIn("record_for_command", function_names)
        for name in ("_lock_scope", "_find_for_command", "_record_for_command"):
            method = next(
                node for node in ast.walk(self.result_tree)
                if isinstance(node, ast.FunctionDef) and node.name == name
            )
            args = {arg.arg for arg in method.args.args + method.args.kwonlyargs}
            self.assertIn("service_capability", args)
            self.assertTrue(any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_require_service_capability"
                for node in ast.walk(method)
            ))

    def test_create_write_unlink_require_the_opaque_service_context(self):
        for name in ("create", "write", "unlink"):
            method = next(
                node for node in ast.walk(self.result_tree)
                if isinstance(node, ast.FunctionDef) and node.name == name
            )
            self.assertTrue(any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "_service_context_is_open"
                for node in ast.walk(method)
            ), name)
        self.assertIn("_COMMAND_RESULT_SERVICE_CAPABILITY = object()", self.result_text)
        self.assertIn("is _COMMAND_RESULT_SERVICE_CAPABILITY", self.result_text)
        self.assertIn("MAX_COMMAND_RESULT_DEPTH", self.result_text)

    def test_replay_model_has_no_direct_role_read_acl(self):
        self.assertNotIn("model_shopify_connector_command_result", self.acl_text)

    def test_durable_status_vocabulary_accepts_business_duplicates(self):
        self.assertIn('(\"duplicate\", \"Duplicate\")', self.result_text)

    def test_adversarial_nesting_fails_with_bounded_value_error(self):
        value = "leaf"
        for _index in range(MAX_COMMAND_RESULT_DEPTH + 50):
            value = {"nested": value}
        with self.assertRaisesRegex(ValueError, "nested too deeply"):
            sanitize_command_result(value)

        cyclic = {}
        cyclic["self"] = cyclic
        with self.assertRaisesRegex(ValueError, "nested too deeply"):
            sanitize_command_result(cyclic)

    def test_replay_adapter_uses_only_private_helpers_and_capability(self):
        self.assertNotIn(".lock_scope(", self.replay_text)
        self.assertNotIn(".find_for_command(", self.replay_text)
        self.assertNotIn(".record_for_command(", self.replay_text)
        for name in ("_lock_scope", "_find_for_command", "_record_for_command"):
            self.assertIn(".%s(" % name, self.replay_text)
        self.assertGreaterEqual(
            self.replay_text.count("_COMMAND_RESULT_SERVICE_CAPABILITY"), 4,
        )

    def test_operation_launcher_is_closed_to_scope_filters_and_dispatch_names(self):
        self.assertIn(
            'unknown = set(payload) - {"operation_key"}',
            self.operation_text,
        )
        self.assertIn("operation_spec(payload.get(\"operation_key\"))", self.operation_text)
        self.assertNotIn("getattr(self.env", self.operation_text)
        self.assertNotIn("payload.get(\"model\")", self.operation_text)
        self.assertNotIn("payload.get(\"method\")", self.operation_text)


if __name__ == "__main__":
    unittest.main()
