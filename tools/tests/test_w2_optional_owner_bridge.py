"""Decision19: read-only owner-version preflight replaces the schema bridge."""
import importlib.util
from pathlib import Path
import unittest

HOOK_PATH = Path(__file__).resolve().parents[2] / (
    'addons/shopify_connector_product_webhook/pre_init.py'
)
SPEC = importlib.util.spec_from_file_location('w2_pre_init', HOOK_PATH)
HOOK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HOOK)


class OwnerCursor:
    def __init__(self, rows):
        self.rows = rows
        self.statements = []

    def execute(self, query, params):
        self.statements.append((query, params))
        if not query.startswith('SELECT ') or 'FROM ir_module_module ' not in query:
            raise AssertionError('Preflight must only read stable module metadata')

    def fetchall(self):
        return self.rows


class TestW2OwnerUpgradePreflight(unittest.TestCase):
    def test_current_installed_owners_pass_without_schema_reads_or_writes(self):
        cursor = OwnerCursor([('shopify_connector_core', '19.0.1.33.0', 'installed')])
        seen = []
        def manifest(name):
            seen.append(name)
            return {'version': '19.0.1.33.0'}
        HOOK.check_owner_versions(cursor, manifest)
        self.assertEqual(seen, ['shopify_connector_core'])
        self.assertEqual(len(cursor.statements), 1)
        self.assertIn("state IN ('installed', 'to upgrade', 'to remove')", cursor.statements[0][0])
        self.assertEqual(cursor.statements[0][1][1], 'shopify_connector_product_webhook')

    def test_old_or_newer_owner_version_is_refused_with_specific_recovery(self):
        for installed in ('19.0.1.23.0', '19.0.1.99.0'):
            with self.subTest(installed=installed):
                cursor = OwnerCursor([('shopify_connector_core', installed, 'installed')])
                with self.assertRaisesRegex(RuntimeError, 'normal versioned upgrade') as caught:
                    HOOK.check_owner_versions(cursor, lambda name: {'version': '19.0.1.33.0'})
                self.assertIn(installed, str(caught.exception))
                self.assertIn('do not downgrade', str(caught.exception))
                self.assertEqual(len(cursor.statements), 1)

    def test_pending_owner_transitions_are_not_treated_as_completed_upgrades(self):
        for state in ('to upgrade', 'to remove'):
            with self.subTest(state=state), self.assertRaisesRegex(RuntimeError, state):
                HOOK.check_owner_versions(OwnerCursor([
                    ('shopify_connector_core', '19.0.1.33.0', state),
                ]), lambda name: {'version': '19.0.1.33.0'})

    def test_missing_installed_owner_source_fails_closed(self):
        with self.assertRaisesRegex(RuntimeError, 'source unavailable'):
            HOOK.check_owner_versions(OwnerCursor([
                ('shopify_connector_export', '19.0.1.0.0', 'installed'),
            ]), lambda name: {})

    def test_fresh_install_does_not_require_uninstalled_optional_owners(self):
        HOOK.check_owner_versions(OwnerCursor([]), lambda name: self.fail(name))


if __name__ == '__main__':
    unittest.main()
