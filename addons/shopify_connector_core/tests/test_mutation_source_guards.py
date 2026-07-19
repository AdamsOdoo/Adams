import ast
import os
import re
from pathlib import Path

from odoo.tests.common import TransactionCase

from ..models import shopify_connector_job_dispatch
from ..models import shopify_connector_mutation_attempt


RAW_HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'request'}


class TestMutationSourceGuards(TransactionCase):

    def _addon_root(self):
        return Path(__file__).resolve().parents[2]

    def _python_files(self):
        return sorted(
            path for path in self._addon_root().glob(
                'shopify_connector_*/**/*.py'
            )
            if 'tests' not in path.parts
        )

    def test_repo_wide_raw_transport_guard(self):
        violations = []
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            parents = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if not (
                    isinstance(func, ast.Attribute)
                    and func.attr in RAW_HTTP_METHODS
                    and isinstance(func.value, ast.Name)
                    and func.value.id == 'requests'
                ):
                    continue
                relative = str(path.relative_to(self._addon_root()))
                owner = parents.get(node)
                while owner and not isinstance(owner, ast.FunctionDef):
                    owner = parents.get(owner)
                owner_name = owner.name if owner else False
                allowed = (
                    relative.endswith(
                        'shopify_connector_core/models/'
                        'shopify_connector_api_client.py'
                    )
                    and func.attr == 'post'
                    and owner_name == '_send'
                ) or (
                    relative.endswith(
                        'shopify_connector_product/models/'
                        'shopify_connector_product_importer.py'
                    )
                    and func.attr == 'get'
                )
                if not allowed:
                    violations.append((relative, node.lineno, func.attr))
        self.assertFalse(violations, violations)

    def test_mutation_literals_require_guarded_transport_or_selftest(self):
        violations = []
        pattern = re.compile(r'\bmutation\s+[A-Za-z_][A-Za-z0-9_]*\s*[({]')
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            parents = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and pattern.search(node.value)
                ):
                    relative = str(path.relative_to(self._addon_root()))
                    owner = parents.get(node)
                    while owner and not isinstance(owner, ast.FunctionDef):
                        owner = parents.get(owner)
                    selftest = (
                        relative.endswith(
                            'shopify_connector_core/models/'
                            'shopify_connector_job_dispatch.py'
                        )
                        and owner
                        and owner.name
                        == '_prepare_preconditions_mutation_selftest'
                    )
                    owner_calls = list(ast.walk(owner)) if owner else []
                    guarded = any(
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == 'execute_business'
                        and any(
                            keyword.arg == 'mutation_context'
                            for keyword in call.keywords
                        )
                        for call in owner_calls
                    )
                    legacy = any(
                        isinstance(call, ast.Call)
                        and isinstance(call.func, ast.Attribute)
                        and call.func.attr == 'execute'
                        for call in owner_calls
                    )
                    if not selftest and (not guarded or legacy):
                        violations.append((relative, node.lineno))
        self.assertFalse(violations, violations)

    def test_no_production_direct_send_caller(self):
        violations = []
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'))
            relative = str(path.relative_to(self._addon_root()))
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == '_send'
                ):
                    continue
                if not relative.endswith(
                    'shopify_connector_core/models/'
                    'shopify_connector_api_client.py'
                ):
                    violations.append((relative, node.lineno))
        self.assertFalse(violations, violations)

    def test_attempt_write_surface_is_closed_and_unlink_forbidden(self):
        source = Path(
            shopify_connector_mutation_attempt.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        class_node = next(
            node for node in tree.body
            if isinstance(node, ast.ClassDef)
            and node.name == 'ShopifyConnectorMutationAttempt'
        )
        methods = {
            node.name for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        required = {
            '_create_attempt_intent',
            '_record_direct_outcome',
            '_record_reconciliation_result',
            '_record_inconclusive_reconciliation',
            'action_resolve_mutation_attempt',
            '_mask_terminal_evidence',
        }
        self.assertTrue(required <= methods)
        self.assertIn('unlink', methods)
        self.assertIn('can never be deleted', source)

    def test_no_attempt_direct_write_call_outside_closed_surface(self):
        allowed_attempt_methods = {
            'create', 'write',
            '_create_attempt_intent',
            '_record_direct_outcome',
            '_record_reconciliation_result',
            '_record_inconclusive_reconciliation',
            'action_resolve_mutation_attempt',
            '_mask_terminal_evidence',
        }
        violations = []
        for path in self._python_files():
            source = path.read_text(encoding='utf-8')
            tree = ast.parse(source, filename=str(path))
            parents = {}
            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in {'create', 'write', 'unlink'}
                ):
                    continue
                target = node.func.value
                target_name = target.id if isinstance(target, ast.Name) else ''
                target_source = ast.unparse(target)
                is_attempt_target = target_name.lower() in {
                    'attempt', 'attempts', 'self',
                } or '._surface(' in target_source
                if path.name == 'shopify_connector_mutation_attempt.py':
                    is_attempt_target = is_attempt_target or target_source.startswith(
                        'super()'
                    )
                if not is_attempt_target:
                    continue
                owner = parents.get(node)
                while owner and not isinstance(owner, ast.FunctionDef):
                    owner = parents.get(owner)
                owner_name = owner.name if owner else False
                if owner_name not in allowed_attempt_methods:
                    violations.append((
                        str(path.relative_to(self._addon_root())),
                        node.lineno,
                        owner_name,
                        node.func.attr,
                    ))
        self.assertFalse(violations, violations)

    def test_zero_real_mutation_domain_and_calls(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        self.assertNotIn('inventorySetQuantities', source)
        self.assertNotIn('inventoryActivate', source)
        self.assertNotIn('fulfillmentCreate', source)
        self.assertIn("'transport': 'synthetic_stub'", source)
        self.assertNotIn('_get_access_token', source)
        self.assertNotIn('requests.', source)

    def test_exact_strategy_shape_and_process_death_escape(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        tree = ast.parse(source)
        expected = {
            'reconciliation_job_type', 'prepare_local',
            'prepare_preconditions', 'transport',
            'classify_direct_result', 'reconcile', 'apply_consequence',
        }
        self.assertEqual(
            shopify_connector_job_dispatch.MUTATION_STRATEGY_KEYS,
            frozenset(expected),
        )
        wrapper = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_drain_mutation_one'
        )
        caught = {
            ast.unparse(handler.type)
            for handler in ast.walk(wrapper)
            if isinstance(handler, ast.ExceptHandler) and handler.type
        }
        self.assertNotIn('BaseException', caught)
        precondition = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_prepare_preconditions_mutation_selftest'
        )
        precondition_source = ast.unparse(precondition)
        self.assertNotIn('self.env', precondition_source)
        self.assertNotIn('_send', precondition_source)
