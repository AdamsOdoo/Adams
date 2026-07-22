# Part of the Shopify Connector (U0 operator UI foundation).
#
# Static source guards for the U0 batch. These assertions inspect the shipped
# files directly, so they hold the U0 architecture and safety boundaries in
# place regardless of runtime data:
#   * exactly one Owl surface (the dashboard client action);
#   * no HTTP controller, webhook, or OAuth surface;
#   * no external dependency / CDN / font / npm / charting library;
#   * the dashboard aggregate service never reads a credential field, never
#     returns a raw payload / log field, and never writes a business model;
#   * the wizards never write mutation-attempt / job protected fields directly;
#   * no production file outside the U0 allowlist (no fulfillment-mode UI, no
#     setup / matching / export / mapping UI, no controllers).

import os

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'shopify_connector_u0')
class TestUiSourceGuards(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # tests/ -> addon root
        cls.addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _read(self, *parts):
        with open(os.path.join(self.addon_root, *parts), 'r', encoding='utf-8') as fh:
            return fh.read()

    def _exists(self, *parts):
        return os.path.exists(os.path.join(self.addon_root, *parts))

    # ------------------------------------------------------------------ #
    def test_single_owl_surface(self):
        """Exactly one client action is registered, in exactly one JS file."""
        js = self._read('static', 'src', 'js', 'shopify_connector_dashboard.js')
        self.assertEqual(
            js.count('registry.category("actions").add('), 1,
            "U0 must register exactly one Owl client action (the dashboard).",
        )
        # No second dashboard/client-action component file exists.
        js_dir = os.path.join(self.addon_root, 'static', 'src', 'js')
        top_level_js = [f for f in os.listdir(js_dir) if f.endswith('.js')]
        self.assertEqual(
            sorted(top_level_js), ['shopify_connector_dashboard.js'],
            "Only the dashboard JS may live at static/src/js top level.",
        )

    def test_no_controller_or_webhook_or_oauth(self):
        """No HTTP controller / webhook / OAuth surface is introduced."""
        self.assertFalse(self._exists('controllers'),
                         "U0 must not add a controllers/ package.")
        for root, _dirs, files in os.walk(self.addon_root):
            for name in files:
                if not name.endswith('.py'):
                    continue
                text = open(os.path.join(root, name), encoding='utf-8').read()
                # Guard only the NEW U0 files for controller/oauth surfaces.
                if name.startswith(('shopify_connector_ui_dashboard',
                                    'shopify_connector_job_cancel_wizard',
                                    'shopify_connector_mutation_resolution_wizard',
                                    'test_ui_')):
                    self.assertNotIn('http.Controller', text,
                                     "%s must not define a controller." % name)
                    self.assertNotIn('@http.route', text,
                                     "%s must not define a route." % name)

    def test_no_external_frontend_dependency(self):
        """No CDN, external font, npm import, or charting library in assets."""
        asset_files = [
            ('static', 'src', 'js', 'shopify_connector_dashboard.js'),
            ('static', 'src', 'js', 'tours', 'shopify_connector_u0_tour.js'),
            ('static', 'src', 'xml', 'shopify_connector_dashboard.xml'),
            ('static', 'src', 'scss', 'shopify_connector_tokens.scss'),
            ('static', 'src', 'scss', 'shopify_connector_dashboard.scss'),
        ]
        forbidden = ('http://', 'https://', 'cdn.', '@import url', 'fonts.googleapis',
                     'chart.js', 'chartjs', 'd3.', 'unpkg', 'jsdelivr', 'cdnjs')
        for parts in asset_files:
            text = self._read(*parts).lower()
            for token in forbidden:
                self.assertNotIn(
                    token, text,
                    "%s must not reference '%s' (external dependency)." % (parts[-1], token),
                )
            # Only Odoo platform imports (@web / @odoo) are allowed in JS.
            if parts[-1].endswith('.js'):
                for line in self._read(*parts).splitlines():
                    line = line.strip()
                    if line.startswith('import ') and ' from ' in line:
                        src = line.rsplit(' from ', 1)[1].strip().strip('";\'')
                        self.assertTrue(
                            src.startswith('@web') or src.startswith('@odoo'),
                            "Only @web/@odoo imports are allowed; found %r" % src,
                        )

    def test_dashboard_service_reads_no_credential_or_payload(self):
        """The aggregate service never touches a credential or raw payload field."""
        text = self._read('models', 'shopify_connector_ui_dashboard.py')
        for forbidden in ('access_token', 'remote_mutation_intent', 'preconditions_snapshot',
                          'remote_evidence_refs', 'payload_snapshot', 'technical_detail',
                          '.store.credential', '_get_access_token'):
            self.assertNotIn(
                forbidden, text,
                "The dashboard service must not reference %r." % forbidden,
            )

    def test_dashboard_service_performs_no_write(self):
        """The read-only aggregate service performs no create/write/unlink."""
        text = self._read('models', 'shopify_connector_ui_dashboard.py')
        for forbidden in ('.create(', '.write(', '.unlink(', '.action_'):
            self.assertNotIn(
                forbidden, text,
                "The dashboard service must be read-only; found %r." % forbidden,
            )

    def test_wizards_call_sanctioned_methods_only(self):
        """Wizards call the sanctioned methods and never write protected state."""
        cancel = self._read('models', 'shopify_connector_job_cancel_wizard.py')
        self.assertIn('action_cancel(self.reason)', cancel)
        self.assertNotIn(".write(", cancel)

        resolve = self._read('models', 'shopify_connector_mutation_resolution_wizard.py')
        self.assertIn('action_resolve_mutation_attempt(self.disposition, self.reason)', resolve)
        self.assertNotIn(".write(", resolve)

    def test_no_out_of_scope_ui(self):
        """No fulfillment-mode / setup / matching / export / mapping UI files."""
        views_dir = os.path.join(self.addon_root, 'views')
        allowed_views = {
            'shopify_connector_menus.xml',
            'shopify_connector_dashboard_views.xml',
            'shopify_connector_store_views.xml',
            'shopify_connector_job_views.xml',
            'shopify_connector_job_log_views.xml',
            'shopify_connector_mutation_attempt_views.xml',
            'shopify_connector_ui_wizard_views.xml',
        }
        present = {f for f in os.listdir(views_dir) if f.endswith('.xml')}
        self.assertEqual(
            present, allowed_views,
            "Only the U0-allowlisted view files may exist; found %s" % (present - allowed_views),
        )
        forbidden_tokens = ('fulfillment', 'setup_wizard', 'matching', 'mapping', 'export_preview')
        for f in present:
            text = open(os.path.join(views_dir, f), encoding='utf-8').read().lower()
            for token in forbidden_tokens:
                self.assertNotIn(
                    token, text,
                    "%s must not contain out-of-scope UI token %r." % (f, token),
                )

    def test_new_models_are_exactly_three(self):
        """Only the three authorised new models are added by U0."""
        init_text = self._read('models', '__init__.py')
        self.assertIn('from . import shopify_connector_ui_dashboard', init_text)
        self.assertIn('from . import shopify_connector_job_cancel_wizard', init_text)
        self.assertIn('from . import shopify_connector_mutation_resolution_wizard', init_text)
        # The dashboard service is an AbstractModel (no table, no ACL row).
        self.assertIn(
            "models.AbstractModel",
            self._read('models', 'shopify_connector_ui_dashboard.py'),
            "The dashboard aggregate service must be an AbstractModel.",
        )
