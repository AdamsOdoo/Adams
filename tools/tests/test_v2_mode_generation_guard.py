"""Execute the actual mode-service input guard without an Odoo registry.

These checks prove rejection before cursor access, not PostgreSQL CAS locking.
The native mode-control regression remains the ORM/audit integration gate.
"""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parents[2] / (
    'addons/shopify_connector_core/models/shopify_connector_store_settings_v2.py'
)
TREE = ast.parse(SOURCE.read_text())
METHOD = next(node for node in ast.walk(TREE)
              if isinstance(node, ast.FunctionDef)
              and node.name == '_set_v2_modes_service')


class ValidationError(Exception):
    pass


NAMESPACE = {
    'AccessError': PermissionError,
    'ValidationError': ValidationError,
    'V2_MODE_KEYS': {'v2_runtime_mode': {'legacy', 'read_only'}},
    'redact': lambda value: value,
}
exec(compile(ast.Module(body=[METHOD], type_ignores=[]), str(SOURCE), 'exec'),
     NAMESPACE)


class TestV2ModeGenerationGuard(unittest.TestCase):
    def setUp(self):
        self.cursor = Mock()
        self.cursor.fetchone.return_value = (0,)
        self.owner = SimpleNamespace(
            ensure_one=Mock(),
            env=SimpleNamespace(
                user=SimpleNamespace(has_group=lambda group: True),
                company=7, cr=self.cursor,
            ),
            company_id=7, id=11, v2_runtime_mode='legacy',
            invalidate_recordset=Mock(),
        )

    def invoke(self, generation):
        return NAMESPACE['_set_v2_modes_service'](
            self.owner, {'v2_runtime_mode': 'legacy'},
            reason='Generation guard test',
            expected_configuration_generation=generation,
        )

    def test_malformed_generation_is_rejected_before_database_access(self):
        for value in (
            None, False, True, '0', 0.0, 0.9, -1,
            float('nan'), float('inf'), float('-inf'),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValidationError, 'non-negative integer'):
                    self.invoke(value)
                self.assertEqual(self.cursor.mock_calls, [])
                self.owner.invalidate_recordset.assert_not_called()

    def test_zero_integer_reaches_locked_comparison(self):
        self.assertIs(self.invoke(0), self.owner)
        self.cursor.execute.assert_called_once()
        query, params = self.cursor.execute.call_args.args
        self.assertIn('FOR UPDATE', query)
        self.assertEqual(params, [11])

    def test_valid_but_stale_integer_still_conflicts(self):
        with self.assertRaisesRegex(ValidationError, 'configuration changed'):
            self.invoke(1)
        self.cursor.execute.assert_called_once()
        self.owner.invalidate_recordset.assert_not_called()


if __name__ == '__main__':
    unittest.main()
