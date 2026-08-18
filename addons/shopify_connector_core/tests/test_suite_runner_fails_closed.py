"""TD-010 regression guard: the evidence instrument must fail closed.

`tools/run_connector_suite.sh` is this repository's evidence instrument. Before
this change it could report `0 failed, 0 error(s)` for a run in which every
browser test SKIPPED -- because `websocket-client` was absent, or because no
Chrome was resolvable -- and a skip is not a failure to unittest. Any browser
claim quoted from such a run was unsound.

The runner now installs the dependency, resolves the browser explicitly,
proves both before running, and inspects every pass's log for unexpected
skips, missing tours and missing HOOT markers.

None of that is worth anything unless the checks FAIL when they should, so the
runner carries a `--self-test` mode that drives them against synthetic logs and
asserts each one rejects the log it is supposed to reject. This test runs that
mode inside the ordinary suite, so the guard cannot rot: if someone weakens a
check, this goes red on the next run rather than the next incident.

It needs no database, no browser and no network -- only bash -- which is why it
is an ordinary `TransactionCase` rather than another `-standard` browser class.
"""

import pathlib
import subprocess

from odoo.tests.common import TransactionCase, tagged

RUNNER = (pathlib.Path(__file__).resolve().parents[3]
          / 'tools' / 'run_connector_suite.sh')


# Issue #193 / #157 -- Odoo 19 test-phase contract; see the core suites.
@tagged('post_install', '-at_install')
class TestSuiteRunnerFailsClosed(TransactionCase):

    def test_runner_self_test_passes(self):
        """Every fail-closed assertion in the runner holds."""
        self.assertTrue(RUNNER.is_file(), 'suite runner not found at %s' % RUNNER)
        result = subprocess.run(
            ['bash', str(RUNNER), '--self-test'],
            capture_output=True, text=True, timeout=300,
        )
        self.assertEqual(
            result.returncode, 0,
            'run_connector_suite.sh --self-test failed, which means the '
            'runner no longer fails closed on missing browser evidence '
            '(TD-010).\n--- stdout ---\n%s\n--- stderr ---\n%s'
            % (result.stdout[-8000:], result.stderr[-4000:]),
        )
        # A self-test that silently stopped asserting would also exit 0.
        self.assertIn(
            'all fail-closed assertions hold', result.stdout,
            'the self-test exited 0 without reporting that it ran its '
            'assertions; it may have been short-circuited',
        )
        for expected in (
            'webhook addon is installed and selected by the suite',
            'an unsanctioned skip is an evidence failure',
            'the sanctioned test skipping for a DIFFERENT reason still fails',
            'a required tour that never ran fails even when marker counts add up',
            'required tours with no success markers fail',
            'a HOOT suite with no verified evidence line fails',
            'preflight aborts on an unresolvable browser',
            'preflight aborts when websocket-client is absent',
            'browser probe cleanup is bounded and path-scoped',
            'browser probe cleanup rejects broad paths',
        ):
            self.assertIn(
                'self-test PASS: %s' % expected, result.stdout,
                'the runner self-test no longer covers %r' % expected,
            )

    def test_browser_probe_cleanup_is_bounded_and_path_scoped(self):
        """CDP probe cleanup cannot race into an unsafe broad deletion."""
        text = RUNNER.read_text()
        self.assertIn('cleanup_browser_probe_dir', text)
        self.assertIn('PROBE_CLEANUP_ATTEMPTS=8', text)
        self.assertIn('rm -rf -- "$probe_dir"', text)
        self.assertIn('mktemp -d /tmp/shopify-connector-cdp.XXXXXX', text)
        self.assertIn('relative != shopify-connector-cdp.*', text)
        self.assertIn('cleanup_browser_probe_dir "/tmp"', text)

    def test_runner_selects_webhook_addon_for_fresh_warm_and_standard_passes(self):
        """The W1 addon cannot disappear from a green suite by list drift."""
        text = RUNNER.read_text()
        self.assertRegex(
            text, r'(?m)^MODULES="[^"]*shopify_connector_webhook',
        )
        self.assertRegex(
            text, r'(?m)^STANDARD_TAGS="[^"]*/shopify_connector_webhook',
        )
        self.assertIn(
            'verify_connector_module_inventory', text,
            'fresh/warm suite must fail closed when the addon is omitted',
        )

    def test_runner_declares_exactly_one_sanctioned_skip(self):
        """The skip allowance is bound to an identity, not to a count.

        A "one skip is allowed" rule would let any test skip, which is the
        hole TD-010 is about. The allowance must name the exact test and the
        exact reason.
        """
        text = RUNNER.read_text()
        self.assertIn(
            'ALLOWED_SKIP_TEST="TestMutationRecovery.'
            'test_real_process_death_harness"', text,
            'the sanctioned skip must be bound to that exact test identity',
        )
        self.assertIn(
            'ALLOWED_SKIP_REASON="real process-death harness is opt-in '
            'outside Odoo.sh"', text,
            'the sanctioned skip must be bound to that exact reason',
        )

    def test_runner_installs_websocket_client_on_every_run(self):
        """Not only when the venv is created.

        A cached venv built before this change would otherwise keep skipping
        every browser test while reporting green, which is precisely the
        defect -- and the one most likely to survive the fix.
        """
        text = RUNNER.read_text()
        install = text.index('pip" install --quiet websocket-client')
        venv_guard = text.index('if [[ ! -x "$VENV/bin/python" ]]; then')
        venv_end = text.index('fi', text.index('requirements.txt"', venv_guard))
        self.assertGreater(
            install, venv_end,
            'the websocket-client install sits inside the venv-creation '
            'branch, so a cached venv never gets it',
        )
