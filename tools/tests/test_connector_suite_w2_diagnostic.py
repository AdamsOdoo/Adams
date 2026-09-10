"""Diagnostic selection and durable stage evidence, without Odoo or PostgreSQL."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = (ROOT / 'tools/run_connector_suite.sh').read_text()
WORKFLOW = (ROOT / '.github/workflows/connector-tests.yml').read_text()


class TestW2Diagnostic(unittest.TestCase):
    def select(self, *args):
        parser = RUNNER[RUNNER.index('RUN_FRESH=1'):RUNNER.index('# --- Browser resolution')]
        script = 'set -eu\nMODULES=fixture\n' + parser + '''
printf '%s:%s:%s:%s:%s:%s:%s' "$CAMPAIGN_SCOPE" "$RUN_FRESH" "$RUN_WARM" "$RUN_NONSTANDARD" "$RUN_MIGRATION" "$RUN_META_INSTALL" "$RUN_W2_OWNER_UPGRADE"
'''
        return subprocess.run(['bash', '-c', script, 'runner', *args], capture_output=True, text=True)

    def test_default_keeps_every_full_lane(self):
        result = self.select()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'full:1:1:1:1:1:1')

    def test_diagnostic_only_selects_owner_upgrade(self):
        result = self.select('--w2-owner-upgrade-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, 'w2-owner-upgrade-diagnostic:0:0:0:0:0:1')

    def test_diagnostic_rejects_conflicting_options_in_either_order(self):
        for args in [('--w2-owner-upgrade-only', '--skip-w2-owner-upgrade'),
                     ('--fresh-only', '--w2-owner-upgrade-only')]:
            with self.subTest(args=args):
                self.assertEqual(self.select(*args).returncode, 2)

    def test_durable_stage_overwrites_running_with_precise_failure(self):
        helper = RUNNER[RUNNER.index('w2_stage() {'):RUNNER.index('if [[ $RUN_W2_OWNER_UPGRADE -eq 1 ]]')]
        with tempfile.TemporaryDirectory() as directory:
            script = f'ARTIFACT_DIR={directory!r}\nlog() {{ :; }}\n' + helper + '''
w2_stage upgrade-installed-owners w2-owner-upgrade.log
w2_stage "$W2_OWNER_UPGRADE_STAGE" "$W2_OWNER_UPGRADE_STAGE_LOG" fail
'''
            result = subprocess.run(['bash', '-ec', script], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            evidence = json.loads((Path(directory) / 'w2-owner-upgrade-stage.json').read_text())
            self.assertEqual(evidence, {'stage': 'upgrade-installed-owners', 'status': 'fail',
                                        'log': 'w2-owner-upgrade.log'})

    def test_workflow_orders_diagnostic_before_expensive_lanes(self):
        diagnostic = WORKFLOW.index('- name: Diagnose owner upgrade')
        focus = WORKFLOW.index('- name: Run focused native prerequisite')
        full = WORKFLOW.index('- name: Run the connector suite')
        self.assertLess(diagnostic, focus)
        self.assertLess(focus, full)
        self.assertNotIn('if:', WORKFLOW[diagnostic:focus])
        self.assertIn('ARTIFACT_DIR: ${{ github.workspace }}/ci-artifacts/w2-diagnostic', WORKFLOW[diagnostic:focus])
        self.assertIn("if: inputs.campaign != 'w2-owner-upgrade'", WORKFLOW[focus:full])
        self.assertIn("if: inputs.campaign != 'w2-owner-upgrade'", WORKFLOW[full:WORKFLOW.index('- name: Publish durable artifacts')])
        uploads = WORKFLOW[WORKFLOW.index('          path: |'):WORKFLOW.index('          retention-days:')]
        for filename in ('w2-owner-upgrade-stage.json', 'w2-owner-upgrade-evidence.json', 'w2-preservation.json'):
            self.assertIn('ci-artifacts/' + filename, uploads)
            self.assertIn('ci-artifacts/w2-diagnostic/' + filename, uploads)
        self.assertNotIn('*.json', uploads)
        self.assertNotIn('.dump', uploads)
        self.assertNotIn('.conf', uploads)


if __name__ == '__main__':
    unittest.main()
