"""Actually EXECUTE the connector's HOOT unit tests -- every one of them.

A `.test.js` file listed in `web.assets_unit_tests` is compiled into the unit
bundle and is then run by whoever opens `/web/tests`. Nothing in this
repository opened it. `shopify_connector_dashboard.test.js` has shipped since
U0 and, as far as any durable record shows, had never been executed -- a test
file that is never run is documentation with a misleading extension.

TD-009, and why this file now runs BOTH suites
----------------------------------------------
The first version of this runner was scoped to the export suite because the
U0 dashboard suite failed to register with `HootError: error while registering
suite "shopify_connector_dashboard"` for a cause nobody had identified. The
cause is now identified and fixed, and it was never in the dashboard test:

    Error while loading "@shopify_connector_core/js/tours/shopify_connector_u0_tour":
    TypeError: Cannot destructure property 'stepUtils' of 'require(...)' as it
    is undefined.

`web.assets_unit_tests_setup` includes the whole of `web.assets_backend`, and
HOOT builds a per-suite module set from the test file's addon plus that addon's
DECLARED Odoo dependencies, then starts every module in it
(`web/static/tests/_framework/module_set.hoot.js::defineModuleSet`). `web_tour`
is not a declared dependency of `shopify_connector_core`, so
`@web_tour/tour_utils` was filtered out of the set while the tour that imports
it was not -- the tour threw, the module set failed, and the suite that merely
shared the bundle could not register. The tours now live in `web.assets_tests`,
which is Odoo's own home for `HttpCase` tours and is in no unit-test bundle.

Each suite gets its OWN browser run, deliberately. A single run filtered to the
shared `shopify connector` prefix also matches unrelated upstream suites by
fuzzy text (it picked up `@web/search/search_panel_desktop`), which makes an
exact executed-count assertion impossible and hides which suite failed.

Tagged `-standard` because it boots a browser and builds the full unit asset
bundle, which is exactly the cost profile the repository's non-standard tag
list exists to keep out of the ordinary pass. `tools/run_connector_suite.sh`
runs the non-standard tags explicitly, so tagging it out is not the same as
never running it.
"""

import logging
import pathlib
import re

from odoo.tests import tagged
from odoo.tests.common import HttpCase

_logger = logging.getLogger(__name__)

#: HOOT's own end-of-run marker. Without it a suite that silently failed to
#: load would look like a pass, which is the failure mode this test exists to
#: remove.
HOOT_SUCCESS = "[HOOT] Test suite succeeded"

#: Every connector HOOT suite, by the exact `describe()` name it registers
#: under, mapped to the exact number of tests it must execute.
#:
#: The counts are EXACT on purpose. A `>=` here would let a suite lose tests
#: silently, which is the same class of defect as a suite that never ran. When
#: you legitimately add or remove a HOOT test, update the number here in the
#: same commit -- that is the point.
EXPECTED_SUITES = {
    'shopify connector dashboard': 8,
    'shopify connector export diff': 11,
    # S1 (2026-07-27): the guided setup client action. Wave 5 (2026-07-29)
    # raised this from 9 to 17: the twelve-step order, semantic-key
    # navigation, the conditional location step, the credential guidance, the
    # five readiness presentation states, staleness and the pending-refresh
    # disclosure are all client-rendered, so each is a mounted-component
    # assertion rather than a server one. The merchant-operability closure
    # (same day) raised it to 20: the credential step's two-path chooser --
    # the Dev Dashboard default with its same-organization/24-hour copy, the
    # offline path's three-value disclosure, the stored-mode reopen, and the
    # client-secret never-in-state proof -- are each client-rendered too.
    # The Batch 1 UI completion (2026-07-30) raised it to 30: the location
    # step's bounded search is a CLIENT protocol -- busy discipline, the
    # server-issued continuation and `next_offset`, per-identity
    # deduplication, revalidation of an off-screen selection, the in-place
    # row update after a mapping, and four distinct empty states -- and none
    # of those properties is observable from the server or from a tour. The
    # first-run Sales Dashboard setup CTA adds the 31st client assertion.
    # The location-discovery polish (2026-08-15) raised it to 33: opening the
    # required location step starts discovery automatically, and Continue
    # remains blocked until every active Shopify location is mapped.
    'shopify connector setup wizard': 33,
}

#: Maps a `.test.js` file to the suite name it is expected to contribute, so
#: `test_every_hoot_file_is_executed` can prove the inventory above is
#: complete rather than merely self-consistent.
EXPECTED_FILES = {
    'shopify_connector_dashboard.test.js': 'shopify connector dashboard',
    'shopify_connector_export_diff.test.js': 'shopify connector export diff',
    'shopify_connector_setup_wizard.test.js':
        'shopify connector setup wizard',
}

#: `[HOOT] "<suite path>" ended (passed: <n> / time: <ms> ms)`
#: The suite path is the full `@addon/module/describe-name` chain, so the
#: connector suite name appears as its last segment.
R_SUITE_ENDED = re.compile(
    r'"(?P<path>[^"]*?/(?P<name>[^"/]+))"\s+ended.*?\(passed:\s*(?P<passed>\d+)'
)


def _connector_hoot_files():
    # .../addons/shopify_connector_product_export/tests/test_u3_hoot_suite.py
    #   parents[0] = tests, parents[1] = the addon, parents[2] = addons
    addons = pathlib.Path(__file__).resolve().parents[2]
    return sorted(addons.glob('shopify_connector_*/static/tests/*.test.js'))


@tagged('post_install', '-at_install', '-standard', 'shopify_connector_hoot')
class TestConnectorHootSuite(HttpCase):

    def _run_suite(self, suite_name, expected_passed):
        """Run one HOOT suite in a real browser and assert what it executed.

        Returns the captured browser log so a caller can assert further.
        """
        url = (
            '/web/tests?headless&loglevel=2&preset=desktop&timeout=15000'
            '&filter=%s' % suite_name.replace(' ', '%20')
        )
        # The browser's console is logged to `<test logger>.browser`, so
        # capturing the root logger captures HOOT's own per-suite report. That
        # report is the only place the executed COUNT appears; `browser_js`
        # itself only proves the success signal was seen.
        with self.assertLogs(level='INFO') as captured:
            self.browser_js(
                url, "", "",
                login='admin',
                timeout=900,
                success_signal=HOOT_SUCCESS,
            )
        blob = '\n'.join(captured.output)

        self.assertIn(
            HOOT_SUCCESS, blob,
            'HOOT never emitted its success marker for suite %r. A run that '
            'cannot prove it finished is not evidence that it passed.'
            % suite_name,
        )

        ended = {
            match.group('name'): int(match.group('passed'))
            for match in R_SUITE_ENDED.finditer(blob)
        }
        self.assertIn(
            suite_name, ended,
            'HOOT never reported suite %r as ended. It either failed to '
            'register or the filter matched nothing -- both of which report '
            '0 failed, 0 error(s) if nobody checks. Suites seen: %s'
            % (suite_name, sorted(ended)),
        )
        self.assertEqual(
            ended[suite_name], expected_passed,
            'HOOT suite %r executed %d tests, expected exactly %d. If you '
            'added or removed a test, update EXPECTED_SUITES in this file in '
            'the same commit.' % (suite_name, ended[suite_name], expected_passed),
        )

        # Re-emit the evidence OUTSIDE the `assertLogs` block.
        #
        # `assertLogs` installs its own handler and sets `propagate = False`
        # for the duration, so every HOOT console line it captures is absent
        # from the run log on disk. `tools/run_connector_suite.sh` verifies
        # browser evidence by reading that log, and evidence a reader cannot
        # find is not evidence. This line is the runner's contract; keep it
        # and `verify_hoot_evidence` in the runner in step.
        _logger.info(
            'CONNECTOR-HOOT-EVIDENCE suite="%s" passed=%d marker=ok',
            suite_name, ended[suite_name],
        )
        return blob

    def test_u0_dashboard_hoot_suite_passes(self):
        """TD-009: the U0 dashboard suite registers, executes and passes.

        This is the suite that had never run once since U0 shipped.
        """
        self._run_suite('shopify connector dashboard',
                        EXPECTED_SUITES['shopify connector dashboard'])

    def test_u3_export_diff_hoot_suite_passes(self):
        """The S7 export-diff Owl component's unit suite."""
        self._run_suite('shopify connector export diff',
                        EXPECTED_SUITES['shopify connector export diff'])

    def test_s1_setup_wizard_hoot_suite_passes(self):
        """The S1 guided-setup Owl component's unit suite.

        Lives in this runner rather than in core for the same reason the
        dashboard suite does: one place runs every connector HOOT suite, so a
        suite cannot be added and left unexecuted.
        """
        self._run_suite('shopify connector setup wizard',
                        EXPECTED_SUITES['shopify connector setup wizard'])

    def test_every_hoot_file_is_executed(self):
        """No connector HOOT file may exist that this runner does not run.

        The regression guard TD-009 asks for. Narrowing the runner's filter to
        dodge a broken suite is exactly what happened before; if a suite stops
        being executed -- or a new `.test.js` is added and never wired in --
        this fails instead of silently reducing coverage.
        """
        found = {path.name for path in _connector_hoot_files()}
        self.assertTrue(
            found,
            'No connector `.test.js` files were discovered at all; this guard '
            'is vacuous and the glob is wrong.',
        )
        self.assertEqual(
            found, set(EXPECTED_FILES),
            'The connector HOOT files on disk do not match the inventory this '
            'runner executes. Add the new file to EXPECTED_FILES and its suite '
            'to EXPECTED_SUITES (with a test method that runs it), or remove '
            'the stale entry.',
        )
        for filename, suite_name in EXPECTED_FILES.items():
            self.assertIn(
                suite_name, EXPECTED_SUITES,
                '%s maps to suite %r, which has no expected count.'
                % (filename, suite_name),
            )
        # Every expected suite must have a test method that actually runs it.
        source = pathlib.Path(__file__).read_text()
        for suite_name in EXPECTED_SUITES:
            self.assertIn(
                "_run_suite('%s'" % suite_name, source,
                'Suite %r is declared in EXPECTED_SUITES but no test method '
                'in this file executes it, so it would never run.'
                % suite_name,
            )

    def test_tours_are_not_in_a_unit_test_bundle(self):
        """TD-009 regression guard, at the cause rather than the symptom.

        A tour in a bundle the HOOT module set is built from lands in that
        set and fails the whole of it, because `@web_tour/tour_utils` is
        filtered out while the tour importing it is not. That is what
        stopped the dashboard suite registering.

        Every bundle `web.assets_unit_tests_setup` draws from has to be
        checked, not just `web.assets_backend`. At the pinned Odoo,
        `addons/web/__manifest__.py` includes BOTH:

            ('include', 'web.assets_backend'),
            ('include', 'web.assets_backend_lazy'),

        so a tour in `assets_backend_lazy` recreates TD-009 identically. The
        earlier version of this guard matched only `'web.assets_backend'`
        with a trailing quote, so `assets_backend_lazy` could never match it,
        and `web.assets_unit_tests` itself was never inspected either.

        The offender test is on CONTENT as well as path. `/tours/` alone
        misses a tour that does not live in a `tours/` directory, and the
        trigger is the `@web_tour` import, not the directory name.
        """
        addons = pathlib.Path(__file__).resolve().parents[2]
        unsafe_bundles = (
            'web.assets_backend',
            'web.assets_backend_lazy',
            'web.assets_unit_tests',
            'web.assets_unit_tests_setup',
        )
        offenders = []
        for manifest in sorted(addons.glob('shopify_connector_*/__manifest__.py')):
            text = manifest.read_text()
            for bundle in unsafe_bundles:
                block = re.search(
                    r"'%s'\s*:\s*\[(.*?)\n\s*\]" % re.escape(bundle),
                    text, re.S,
                )
                if not block:
                    continue
                listed = block.group(1)
                for entry in re.findall(r"'([^']+\.js)'", listed):
                    if '/tours/' in entry or entry.endswith('_tour.js'):
                        offenders.append(
                            '%s -> %s: %s' % (
                                manifest.parent.name, bundle, entry,
                            )
                        )
                        continue
                    # A tour is anything importing `@web_tour`, wherever it
                    # sits. Resolve `<addon>/static/...` against the tree.
                    parts = entry.split('/', 1)
                    if len(parts) != 2:
                        continue
                    path = addons / parts[0] / parts[1]
                    if path.is_file() and '@web_tour' in path.read_text():
                        offenders.append(
                            '%s -> %s: %s (imports @web_tour)' % (
                                manifest.parent.name, bundle, entry,
                            )
                        )
        self.assertFalse(offenders, (
            'These manifests put a tour in a bundle the HOOT module set is '
            'built from, which breaks unit-suite registration for the whole '
            'addon (TD-009). Move it to `web.assets_tests`:\n  %s'
            % '\n  '.join(offenders)))
