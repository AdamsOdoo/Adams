"""Identity boundaries of the Adams-owned external adapter; no private source."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('work_harness', ROOT / 'scripts/work-harness.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class AdapterIdentityTests(unittest.TestCase):
    def test_candidate_identity_cannot_be_overridden_by_abbreviations(self):
        revision = json.loads((ROOT / '.odoo-harness/connection.json').read_text())['toolkit_commit']
        with tempfile.TemporaryDirectory() as directory:
            toolkit = Path(directory).resolve()
            def git(root, *args):
                if args == ('remote', 'get-url', 'origin'):
                    return 'https://github.com/' + ('AdamsOdoo/Adams.git' if root == ROOT else 'MostafaEssamm12/Odoo.git')
                return revision if args == ('rev-parse', 'HEAD') else ''
            for flag in ('--candidate', '--cand', '--candidate=x', '--expected-comm', '--expected-commit=x'):
                with self.subTest(flag=flag), patch.object(adapter, 'git', side_effect=git), \
                        patch.dict('os.environ', {'ODOO_HARNESS_HOME': str(toolkit)}), \
                        patch('sys.argv', ['work-harness.py', 'test', flag, 'x']), \
                        patch.object(adapter.subprocess, 'call') as execute:
                    with self.assertRaisesRegex(ValueError, 'do not override'):
                        adapter.main()
                    execute.assert_not_called()

    def test_missing_checkout_fails_before_execution(self):
        with patch.object(adapter, 'git', return_value='https://github.com/AdamsOdoo/Adams.git'), \
                patch.dict('os.environ', {}, clear=True), patch('sys.argv', ['work-harness.py', 'doctor']), \
                patch.object(adapter.subprocess, 'call') as execute:
            with self.assertRaisesRegex(ValueError, 'Set ODOO_HARNESS_HOME'):
                adapter.main()
            execute.assert_not_called()
