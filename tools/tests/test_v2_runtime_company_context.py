"""Execute the transaction boundary; native tests own Odoo membership proof."""
import ast
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parents[2] / (
    'addons/shopify_connector_core/models/shopify_connector_v2_runtime_repository.py'
)
TREE = ast.parse(SOURCE.read_text())
METHODS = [node for node in ast.walk(TREE)
           if isinstance(node, ast.FunctionDef)
           and node.name in ('_transaction', '_company_ids')]


class TestRuntimeCompanyContext(unittest.TestCase):
    def make_owner(self, env, factory):
        namespace = {'contextmanager': contextmanager, 'SUPERUSER_ID': 1,
                     'api': SimpleNamespace(Environment=factory)}
        exec(compile(ast.Module(body=METHODS, type_ignores=[]), str(SOURCE), 'exec'),
             namespace)
        return SimpleNamespace(env=env, _company_ids=namespace['_company_ids']), namespace

    def test_invalid_caller_company_is_rejected_before_cursor_or_elevation(self):
        class InvalidCaller:
            registry = Mock()
            context = {'allowed_company_ids': [99]}

            @property
            def companies(self):
                raise PermissionError('Caller does not belong to company 99')

        env = InvalidCaller()
        factory = Mock()
        owner, namespace = self.make_owner(env, factory)
        with self.assertRaises(PermissionError):
            with namespace['_transaction'](owner):
                self.fail('An unauthorized transaction was opened')
        env.registry.cursor.assert_not_called()
        factory.assert_not_called()

    def test_root_receives_validated_caller_companies_even_without_context_key(self):
        for context in ({}, {'allowed_company_ids': [7, 9]}):
            with self.subTest(context=context):
                ids = [7] if not context else [7, 9]
                cursor, side = Mock(), Mock()
                env = SimpleNamespace(
                    context=context.copy(), companies=SimpleNamespace(ids=ids),
                    company=SimpleNamespace(id=7),
                    registry=SimpleNamespace(cursor=Mock(return_value=cursor)),
                )
                factory = Mock(return_value=side)
                owner, namespace = self.make_owner(env, factory)
                with namespace['_transaction'](owner) as result:
                    self.assertIs(result, side)
                factory.assert_called_once_with(cursor, 1, {'allowed_company_ids': ids})
                self.assertEqual(env.context, context)
                side.flush_all.assert_called_once()
                cursor.commit.assert_called_once()
                cursor.close.assert_called_once()

    def test_environment_construction_failure_closes_cursor(self):
        cursor = Mock()
        env = SimpleNamespace(
            context={}, companies=SimpleNamespace(ids=[7]),
            registry=SimpleNamespace(cursor=Mock(return_value=cursor)),
        )
        factory = Mock(side_effect=RuntimeError('environment initialization failed'))
        owner, namespace = self.make_owner(env, factory)
        with self.assertRaises(RuntimeError):
            with namespace['_transaction'](owner):
                self.fail('A failed environment was yielded')
        cursor.rollback.assert_called_once()
        cursor.close.assert_called_once()
        cursor.commit.assert_not_called()
