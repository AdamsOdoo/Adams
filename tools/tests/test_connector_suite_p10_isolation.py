"""Exercise the disposable P10 runner boundary without a database server."""

from pathlib import Path
import ast
import os
import re
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
RUNNER = (ROOT / 'tools/run_connector_suite.sh').read_text()


class TestP10DisposableLane(unittest.TestCase):
    def run_lane(self, *, test_status=0, clone_status=0, drop_status=0):
        start = RUNNER.index('    run_p10_disposable() (')
        end = RUNNER.index('    if run_p10_disposable;', start)
        function = RUNNER[start:end]
        with tempfile.TemporaryDirectory() as artifact_dir:
            script = f'''
set -eu
ARTIFACT_DIR={artifact_dir!r}
TEMPLATE_DB=connector_template
MODULES=fixture_modules
P10_TAG=shopify_connector_v2_runtime_concurrency
clone_db() {{ echo "clone:$1:$2"; return {clone_status}; }}
dropdb() {{ echo "drop:$2"; return {drop_status}; }}
run_odoo() {{ echo "run:$1:$CONNECTOR_P10_DISPOSABLE_DB:$6"; return {test_status}; }}
{function}
if run_p10_disposable; then exit 0; else exit 1; fi
'''
            return subprocess.run(['bash', '-c', script], text=True,
                                  capture_output=True, check=False)

    def test_success_uses_matching_marker_and_disposes_database(self):
        result = self.run_lane()
        self.assertEqual(result.returncode, 0, result.stderr)
        database = re.search(r'clone:connector_template:(connector_p10_\d+)',
                             result.stdout).group(1)
        self.assertIn(f'run:{database}:{database}:--test-tags', result.stdout)
        self.assertIn(f'drop:{database}', result.stdout)

    def test_failure_still_disposes_database_and_remains_failed(self):
        result = self.run_lane(test_status=1)
        self.assertEqual(result.returncode, 1)
        self.assertIn('drop:connector_p10_', result.stdout)

    def test_clone_failure_disposes_partial_database_without_running_tests(self):
        result = self.run_lane(clone_status=1)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('run:', result.stdout)
        self.assertIn('drop:connector_p10_', result.stdout)

    def test_cleanup_failure_cannot_report_pass(self):
        result = self.run_lane(drop_status=1)
        self.assertEqual(result.returncode, 1)

    def test_authoritative_inventory_retains_p10_in_separate_lane(self):
        inventory = re.search(r'^NONSTANDARD_TAGS="([^"]+)"', RUNNER,
                              re.MULTILINE).group(1).split(',')
        self.assertEqual(inventory.count('shopify_connector_v2_runtime_concurrency'), 1)
        self.assertIn('--test-tags "$SHARED_NONSTANDARD_TAGS"', RUNNER)
        self.assertIn('--test-tags "$P10_TAG"', RUNNER)
        self.assertIn('P10 runtime: missing ${test_name}', RUNNER)
        self.assertIn('"missing": $((P10_EXPECTED - P10_EXECUTED))', RUNNER)

    def test_company_fixture_refuses_unmarked_or_wrong_database(self):
        source = ROOT / 'addons/shopify_connector_core/tests/v2_runtime_concurrency_support.py'
        tree = ast.parse(source.read_text())
        fixture_class = next(node for node in tree.body
                             if isinstance(node, ast.ClassDef)
                             and node.name == 'V2RuntimeFixtureMixin')
        guard = next(node for node in fixture_class.body
                     if isinstance(node, ast.FunctionDef)
                     and node.name == '_require_disposable_database')
        namespace = {'os': os}
        exec(compile(ast.Module(body=[guard], type_ignores=[]), str(source), 'exec'),
             namespace)
        check = namespace['_require_disposable_database']
        for database, marker in [('live', 'live'), ('connector_p10_1', ''),
                                 ('connector_p10_1', 'connector_p10_2')]:
            with self.subTest(database=database, marker=marker), patch.dict(
                os.environ, {'CONNECTOR_P10_DISPOSABLE_DB': marker},
            ), self.assertRaises(AssertionError):
                check(SimpleNamespace(env=SimpleNamespace(cr=SimpleNamespace(dbname=database))))
        with patch.dict(os.environ, {'CONNECTOR_P10_DISPOSABLE_DB': 'connector_p10_1'}):
            check(SimpleNamespace(env=SimpleNamespace(cr=SimpleNamespace(dbname='connector_p10_1'))))


if __name__ == '__main__':
    unittest.main()
