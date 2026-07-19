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
        return sorted(self._addon_root().glob('shopify_connector_*/**/*.py'))

    def test_repo_wide_raw_transport_guard(self):
        violations = []
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
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
                allowed = (
                    relative.endswith(
                        'shopify_connector_core/models/'
                        'shopify_connector_api_client.py'
                    )
                    and func.attr == 'post'
                ) or (
                    relative.endswith(
                        'shopify_connector_product/models/product_importer.py'
                    )
                    and func.attr == 'get'
                )
                if not allowed:
                    violations.append((relative, node.lineno, func.attr))
        self.assertFalse(violations, violations)

    def test_graphql_mutation_literals_exist_only_in_layer2_wrapper(self):
        violations = []
        pattern = re.compile(r'\bmutation\s+[A-Za-z_][A-Za-z0-9_]*\s*[({]')
        for path in self._python_files():
            tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                    and pattern.search(node.value)
                ):
                    relative = str(path.relative_to(self._addon_root()))
                    if not relative.endswith(
                        'shopify_connector_core/models/'
                        'shopify_connector_job_dispatch.py'
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

    def test_zero_real_mutation_domain_and_calls(self):
        source = Path(
            shopify_connector_job_dispatch.__file__
        ).read_text(encoding='utf-8')
        self.assertNotIn('inventorySetQuantities', source)
        self.assertNotIn('inventoryActivate', source)
        self.assertNotIn('fulfillmentCreate', source)
        self.assertIn("'transport': 'synthetic_stub'", source)
