"""Actually EXECUTE the connector's HOOT unit tests.

A `.test.js` file listed in `web.assets_unit_tests` is compiled into the unit
bundle and is then run by whoever opens `/web/tests`. Nothing in this
repository opened it. `shopify_connector_dashboard.test.js` has shipped since
U0 and, as far as any durable record shows, had never been executed — a test
file that is never run is documentation with a misleading extension.

This runner opens the HOOT suite headlessly, filtered to the connector's own
suites, and fails on any failing assertion. The filter is deliberately the
shared `shopify connector` prefix rather than the export suite alone, so the
one runner covers both the U0 dashboard suite and the U3 export-diff suite;
running the entire Odoo unit bundle here would take an hour and test code this
repository does not own.

Tagged `-standard` because it boots a browser and builds the full unit asset
bundle, which is exactly the cost profile the repository's non-standard tag
list exists to keep out of the ordinary pass. `tools/run_connector_suite.sh`
runs the non-standard tags explicitly, so tagging it out is not the same as
never running it.
"""

from odoo.tests import tagged
from odoo.tests.common import HttpCase

# The `describe()` prefix both connector HOOT suites share.
HOOT_FILTER = 'shopify connector export diff'


@tagged('-at_install', 'post_install', '-standard', 'shopify_connector_hoot')
class TestConnectorHootSuite(HttpCase):

    def test_connector_hoot_suites_pass(self):
        """Run the connector HOOT suites in a real browser.

        `success_signal` is HOOT's own end-of-run marker. Without it a suite
        that silently failed to load would look like a pass, which is the
        failure mode this test exists to remove.
        """
        self.browser_js(
            '/web/tests?headless&loglevel=2&preset=desktop&timeout=15000'
            '&filter=%s' % HOOT_FILTER.replace(' ', '%20'),
            "", "",
            login='admin',
            timeout=900,
            success_signal="[HOOT] Test suite succeeded",
        )
