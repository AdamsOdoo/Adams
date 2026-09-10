"""Exercise owner-upgrade lane command ordering and failure propagation."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNNER = (ROOT / 'tools/run_connector_suite.sh').read_text()
FUNCTION = RUNNER[RUNNER.index('    run_w2_owner_upgrade() {'):RUNNER.index('    if run_w2_owner_upgrade; then')]


class TestOwnerUpgradeLane(unittest.TestCase):
    def run_lane(self, fail='none'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'bin').mkdir()
            (path / 'bin/python').write_text('#!/bin/sh\nexit 0\n')
            (path / 'bin/python').chmod(0o755)
            (path / 'conf').write_text('addons_path = old\n')
            script = f'''
set -euo pipefail
ARTIFACT_DIR={directory!r}
VENV="$ARTIFACT_DIR"
CONF="$ARTIFACT_DIR/conf"
REPO_ROOT="$ARTIFACT_DIR"
ODOO_SRC=odoo
W2_OWNER_UPGRADE_ORIGIN=7443250ae42a0c3fadba9bf0ef9991e1826b77b5
W1_ONLY_MODULES=shopify_connector_core,shopify_connector_webhook
EXTRA_MODULES=account,stock
W1_WEBHOOK_VERSION=19.0.1.4.0
W2_PRODUCT_WEBHOOK_VERSION=19.0.0.4.0
W2_OWNER_UPGRADE_TEST_TAGS=fixture
EVIDENCE_ERRORS=()
FAIL={fail!r}
w2_stage() {{ W2_OWNER_UPGRADE_STAGE="$1"; echo "stage:$1"; }}
git() {{ return 0; }}
tar() {{ cat >/dev/null; }}
createdb() {{ return 0; }}
dropdb() {{ return 0; }}
pg_dump() {{ [[ "$FAIL" != backup ]]; }}
pg_restore() {{ [[ "$FAIL" != restore ]]; }}
run_odoo_with_conf() {{ return 0; }}
psql() {{
  if [[ "$*" == *'count(*)'* ]]; then echo 0;
  elif [[ "$*" == *shopify_connector_product_webhook* ]]; then echo "$W2_PRODUCT_WEBHOOK_VERSION";
  elif [[ -f "$ARTIFACT_DIR/upgraded" ]]; then echo "$W1_WEBHOOK_VERSION";
  else echo 19.0.1.0.0; fi
}}
python3() {{
  if [[ "$2" == before ]]; then echo shopify_connector_core,shopify_connector_webhook;
  else [[ "$FAIL" != evidence ]]; fi
}}
w2_preservation_fixture() {{ echo "fixture:$1"; [[ "$FAIL" != preservation ]]; }}
run_odoo() {{
  echo "odoo:$3:$4"
  case "$2" in
    *repeat.log) [[ "$FAIL" != repeat ]] || return 1 ;;
    *owner-upgrade.log) [[ "$FAIL" != upgrade ]] || return 1; touch "$ARTIFACT_DIR/upgraded" ;;
    *install.log) [[ "$FAIL" != install ]] || return 1 ;;
  esac
  echo '0 failed, 0 error(s) of 18 tests' > "$2"
}}
migration_lines() {{ [[ "$FAIL" != rerun_migration ]] || echo 'unexpected migration'; return 0; }}
verify_no_unexpected_skips() {{ if [[ "$FAIL" == skip ]]; then EVIDENCE_ERRORS+=(skip); fi; }}
result_line() {{ echo '18 tests passed'; }}
{FUNCTION}
if run_w2_owner_upgrade; then exit 0; else exit 1; fi
'''
            return subprocess.run(['bash', '-c', script], capture_output=True, text=True)

    def test_owner_upgrade_precedes_install_and_repeat(self):
        result = self.run_lane()
        self.assertEqual(result.returncode, 0, result.stderr)
        commands = [x for x in result.stdout.splitlines() if x.startswith('odoo:')]
        self.assertEqual(commands, ['odoo:-u:shopify_connector_core,shopify_connector_webhook',
                                    'odoo:-i:shopify_connector_product_webhook',
                                    'odoo:-u:shopify_connector_core,shopify_connector_webhook,shopify_connector_product_webhook'])
        self.assertEqual(result.stdout.count('fixture:verify'), 3)

    def test_every_qualification_failure_propagates(self):
        stages = {
            'backup': 'backup-old-database', 'restore': 'restore-old-database',
            'upgrade': 'upgrade-installed-owners', 'install': 'install-w2',
            'repeat': 'repeat-owner-and-w2-upgrade', 'preservation': 'seed-preservation-fixture',
            'evidence': 'verify-owner-migrations', 'skip': 'verify-w2-tests',
            'rerun_migration': 'verify-w2-tests',
        }
        for failure, stage in stages.items():
            with self.subTest(failure=failure):
                result = self.run_lane(failure)
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                reported = [line for line in result.stdout.splitlines() if line.startswith('stage:')]
                self.assertEqual(reported[-1], 'stage:' + stage)


if __name__ == '__main__':
    unittest.main()
