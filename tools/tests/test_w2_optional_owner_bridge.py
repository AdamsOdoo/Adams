"""No Odoo import needed: verify hook dispatch at the optional SQL boundary.

Native install/schema tests remain necessary; this cursor records the actual
hook's statements to detect accidental export access in a Lite schema.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest


HOOK_PATH = Path(__file__).resolve().parents[2] / (
    'addons/shopify_connector_product_webhook/pre_init.py'
)
SPEC = importlib.util.spec_from_file_location('w2_pre_init', HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


class BridgeCursor:
    def __init__(self, export_installed):
        self.export_installed = export_installed
        self.statements = []
        self.rows = []

    def execute(self, query, params=None):
        self.statements.append((query, params))
        if query.startswith('SELECT EXISTS'):
            self.rows = [(self.export_installed,)]
        elif query.startswith('SELECT to_regclass'):
            self.rows = [('present',)]
        elif 'SELECT column_name, udt_name' in query:
            table, names = params
            if table == 'shopify_connector_webhook_subscription':
                self.rows = [(name, 'jsonb') for name in names]
            else:
                types = dict(HOOK._ADDITIVE_COLUMNS[table])
                self.rows = [(name, HOOK._SQL_UDT[types[name]]) for name in names]
        else:
            self.rows = []

    def fetchone(self):
        return self.rows[0]

    def fetchall(self):
        return self.rows


class TestW2OptionalOwnerBridge(unittest.TestCase):
    def test_lite_never_alters_or_seeds_export_columns(self):
        cursor = BridgeCursor(export_installed=False)
        HOOK.pre_init_hook(SimpleNamespace(cr=cursor))
        writes = [query for query, _ in cursor.statements
                  if not query.startswith('SELECT')]
        self.assertFalse(any('product_template' in query for query in writes))
        self.assertTrue(any('UPDATE shopify_connector_store_settings' in query
                            for query in writes))

    def test_installed_export_keeps_managed_status_and_import_seed(self):
        cursor = BridgeCursor(export_installed=True)
        HOOK.pre_init_hook(SimpleNamespace(cr=cursor))
        writes = '\n'.join(query for query, _ in cursor.statements
                           if not query.startswith('SELECT'))
        self.assertIn('ADD COLUMN IF NOT EXISTS "shopify_export_status_managed"', writes)
        self.assertIn('SET shopify_export_status_managed = TRUE', writes)
        self.assertIn('shopify_export_status_managed = FALSE', writes)


if __name__ == '__main__':
    unittest.main()
