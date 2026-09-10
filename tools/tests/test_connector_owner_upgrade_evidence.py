"""Failure boundaries for owner-version/migration preservation qualification."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('owner_evidence', ROOT / 'tools/connector_owner_upgrade_evidence.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class TestOwnerUpgradeEvidence(unittest.TestCase):
    def setUp(self):
        self.evidence = {'target_versions': {'shopify_connector_core': '19.0.1.33.0'},
                         'identities_before': {'shopify_connector_job': [{'id': 4, 'store_id': 2}]},
                         'expected_migrations': [['shopify_connector_core', '19.0.1.32.0', 'pre-migrate']]}
        self.log = 'module shopify_connector_core: Running upgrade [>19.0.1.32.0] pre-migrate \n'

    def verify(self, **overrides):
        helper.verify(self.evidence, overrides.get('current', self.evidence['target_versions']),
                      overrides.get('after', self.evidence['identities_before']), overrides.get('log', self.log))

    def test_actual_script_version_and_preserved_identity_pass(self):
        self.verify()

    def test_correct_versions_without_actual_migration_fail(self):
        with self.assertRaisesRegex(ValueError, 'migration did not execute'):
            self.verify(log='module shopify_connector_core loaded')

    def test_wrong_script_version_fails(self):
        with self.assertRaises(ValueError):
            self.verify(log=self.log.replace('19.0.1.32.0', '19.0.1.3.0'))

    def test_missing_or_stale_owner_fails(self):
        for current in ({}, {'shopify_connector_core': '19.0.1.23.0'}):
            with self.subTest(current=current), self.assertRaisesRegex(ValueError, 'owner version mismatch'):
                self.verify(current=current)

    def test_deleted_or_reassigned_identity_fails(self):
        for after in ({}, {'shopify_connector_job': [{'id': 4, 'store_id': 3}]}):
            with self.subTest(after=after), self.assertRaisesRegex(ValueError, 'identity/relationship changed'):
                self.verify(after=after)

    def test_legitimate_added_rows_do_not_fail(self):
        after = copy.deepcopy(self.evidence['identities_before'])
        after['shopify_connector_job'].append({'id': 5, 'store_id': 2})
        self.verify(after=after)

    def test_plan_includes_only_actual_installed_owner_migrations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for module in ('core', 'webhook', 'inventory'):
                addon = root / 'addons' / ('shopify_connector_' + module)
                (addon / 'migrations/19.0.1.2.0').mkdir(parents=True)
                (addon / '__manifest__.py').write_text("{'version': '19.0.1.2.0'}")
                (addon / 'migrations/19.0.1.2.0/post-migrate.py').write_text('')
            plan = helper.plan(root, {'shopify_connector_core': '19.0.1.1.0', 'shopify_connector_webhook': '19.0.1.1.0'})
            self.assertEqual(len(plan['expected_migrations']), 2)
            self.assertNotIn('shopify_connector_inventory', plan['target_versions'])


if __name__ == '__main__':
    unittest.main()
