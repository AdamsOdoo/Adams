"""Execute the real SQL-builder method without importing the Odoo registry.

This tests cursor sequencing and returned identities, not PostgreSQL locking.
Native TestV2RuntimeAdapter and independent-connection regressions remain gates.
"""
import ast
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / (
    'addons/shopify_connector_core/models/shopify_connector_v2_runtime_stale.py'
)
TREE = ast.parse(SOURCE.read_text())
METHOD = next(node for node in ast.walk(TREE)
              if isinstance(node, ast.FunctionDef) and node.name == '_stale_sql')
NAMESPACE = {
    '_db_datetime': lambda value: value,
    'V2_READ_ONLY_RUNTIME_MODES': ('read_only',),
}
exec(compile(ast.Module(body=[METHOD], type_ignores=[]), str(SOURCE), 'exec'),
     NAMESPACE)


class Cursor:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def execute(self, query, params):
        self.calls.append((query, params))

    def fetchall(self):
        return self.responses[len(self.calls) - 1]

    def fetchone(self):
        rows = self.fetchall()
        return rows[0] if rows else None


class TestStaleAdapterQueryContract(unittest.TestCase):
    def invoke(self, cursor):
        owner = SimpleNamespace(_company_ids=lambda env: (7,))
        return NAMESPACE['_stale_sql'](
            owner, SimpleNamespace(cr=cursor), datetime(2026, 9, 8), 1,
            ('core_dispatch_selftest',),
        )

    def test_current_contract_preserves_registered_and_removed_handler_status(self):
        for registered in (True, False):
            with self.subTest(registered=registered):
                detail = tuple(range(15))
                cursor = Cursor([
                    [(41, 'claim', 12, 7, 'core_dispatch_selftest', registered)],
                    [(91,)], [(12,)], [(7,)], [(33, 7)], [detail],
                ])
                result = self.invoke(cursor)
                self.assertEqual(result, (
                    detail + ('core_dispatch_selftest', registered),
                ))
                self.assertEqual(len(cursor.calls), 6)
                self.assertEqual(cursor.calls[0][1][0], ('core_dispatch_selftest',))
                self.assertEqual(cursor.calls[0][1][-1], 1)
                self.assertEqual(cursor.calls[2][1], [(12,)])
                self.assertEqual(cursor.calls[3][1], [(7,)])
                self.assertEqual(cursor.calls[4][1], [(7,)])
                self.assertEqual(cursor.calls[5][1][:4], [91, 'claim', 33, 41])

    def test_missing_attempt_stops_without_acquiring_parent_locks(self):
        cursor = Cursor([
            [(41, 'claim', 12, 7, 'core_dispatch_selftest', True)], [],
        ])
        self.assertEqual(self.invoke(cursor), ())
        self.assertEqual(len(cursor.calls), 2)

    def test_missing_scope_parent_does_not_return_unfenced_detail(self):
        cursor = Cursor([
            [(41, 'claim', 12, 7, 'core_dispatch_selftest', True)],
            [(91,)], [(12,)], [(7,)], [],
        ])
        self.assertEqual(self.invoke(cursor), ())
        self.assertEqual(len(cursor.calls), 5)


if __name__ == '__main__':
    unittest.main()
