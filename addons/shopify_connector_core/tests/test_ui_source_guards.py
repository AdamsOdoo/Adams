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

import ast
import os
import shutil
import tempfile

from odoo.tests.common import TransactionCase, tagged


def _dotted_name(node):
    """Best-effort dotted-name string for an AST base/decorator expression
    (e.g. ``http.Controller`` -> ``"http.Controller"``, ``Controller`` ->
    ``"Controller"``). Returns ``None`` for anything else (a call result,
    a subscript, etc.) -- those are never a controller base or route
    decorator, so they are simply not matched.
    """
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return ('%s.%s' % (base, node.attr)) if base else node.attr
    if isinstance(node, ast.Name):
        return node.id
    return None


def controller_route_oauth_surfaces(path):
    """Structurally scan one production ``.py`` file's AST for a controller
    class, an ``http.route``-decorated function, or an OAuth-surface import.

    Stage R2 correction (independent review 5049668193 material P2): the
    prior guard matched a raw filename prefix and a raw text substring, so a
    controller/route added under any other filename -- or renamed to dodge
    the substring -- was walked but never actually checked. This scans the
    AST instead: a real ``class X(http.Controller)`` / ``class X(Controller)``
    definition, a real ``@http.route(...)`` / ``@route(...)`` decorator, or a
    real ``import``/``from ... import ...`` of an OAuth-named module -- never
    a filename, a comment, or a docstring, so it cannot be defeated by
    renaming a file and does not false-positive on this module's own
    legitimate prose ("no OAuth", "client_secret" as a redaction-key name).
    Returns a list of human-readable violation descriptions (empty if none).
    """
    with open(path, encoding='utf-8') as fh:
        source = fh.read()
    tree = ast.parse(source, filename=path)
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                dotted = _dotted_name(base) or ''
                if dotted == 'Controller' or dotted.endswith('.Controller'):
                    violations.append(
                        'class %s inherits from an http.Controller base '
                        '(%s)' % (node.name, dotted))
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                func = dec.func if isinstance(dec, ast.Call) else dec
                dotted = _dotted_name(func) or ''
                if dotted == 'route' or dotted.endswith('.route'):
                    violations.append(
                        'function %s is decorated with an http.route '
                        '(%s)' % (node.name, dotted))
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [getattr(node, 'module', None)]
            names += [alias.name for alias in node.names]
            for mod_name in names:
                if mod_name and 'oauth' in mod_name.lower():
                    violations.append(
                        'imports the OAuth-named module %r' % mod_name)
    return violations


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

    def _iter_production_python_files(self):
        """Every shipped production ``.py`` file under the addon root.

        Structurally excludes the ``tests/`` package and ``__pycache__`` (by
        directory identity, not by name-prefix guessing), so this guard's own
        file is excluded because it lives in ``tests/``, not via a
        self-exclusion special case.
        """
        for root, dirs, files in os.walk(self.addon_root):
            dirs[:] = [d for d in dirs if d not in ('tests', '__pycache__')]
            for name in files:
                if name.endswith('.py'):
                    yield os.path.join(root, name)

    # ------------------------------------------------------------------ #
    def test_single_owl_surface(self):
        """One client action per accepted Owl surface, and no more.

        U0 accepted exactly one: the dashboard. S1 (2026-07-27) adds the
        second and last core-owned one, the guided setup wizard -- an accepted
        MVP screen in its own right (premium UX master specification §3 "S1 --
        Setup wizard"; DEC-012 §1). The guard is kept as an exact inventory
        rather than relaxed to a count, so a THIRD surface still has to be a
        decision somebody makes on purpose.
        """
        expected_actions = {
            'shopify_connector_dashboard.js': 'shopify_connector_dashboard',
            'shopify_connector_setup_wizard.js':
                'shopify_connector_setup_wizard',
        }
        for filename, tag in expected_actions.items():
            js = self._read('static', 'src', 'js', filename)
            self.assertEqual(
                js.count('registry.category("actions").add('), 1,
                "%s must register exactly one Owl client action." % filename,
            )
            self.assertIn(
                '"%s"' % tag, js,
                "%s must register the accepted client-action tag." % filename,
            )
        js_dir = os.path.join(self.addon_root, 'static', 'src', 'js')
        top_level_js = [f for f in os.listdir(js_dir) if f.endswith('.js')]
        self.assertEqual(
            sorted(top_level_js), sorted(expected_actions),
            "Only the accepted Owl surfaces may live at static/src/js top "
            "level.",
        )

    def test_no_controller_or_webhook_or_oauth(self):
        """No HTTP controller / route(webhook) / OAuth surface anywhere in
        the shipped production tree.

        Stage R2 correction (independent review 5049668193 material P2): the
        prior guard only ran its ``assertNotIn`` checks on ``.py`` files
        whose NAME started with one of four hard-coded prefixes -- every
        other production file (including this very commit's own
        ``shopify_connector_store.py``) was walked but never actually
        checked, and a controller/route added under a fifth filename would
        have been silently invisible to it. This scans every production
        ``.py`` file unconditionally (``tests/``/``__pycache__`` are excluded
        structurally, not by name) and detects a real controller class /
        ``@route`` decorator / OAuth-named import via the AST, so it cannot
        be defeated by choosing a different filename and does not
        false-positive on this module's own prose.
        """
        self.assertFalse(self._exists('controllers'),
                         "U0 must not add a controllers/ package.")
        violations = []
        for path in self._iter_production_python_files():
            for message in controller_route_oauth_surfaces(path):
                violations.append('%s: %s' % (
                    os.path.relpath(path, self.addon_root), message))
        self.assertEqual(
            violations, [],
            "Production-tree controller/route/OAuth surface(s) found: %s"
            % violations)

    def test_source_guard_rejects_synthetic_controller_fixture(self):
        """The structural guard genuinely rejects an unsafe fixture -- even
        under a filename that would have dodged the old four-prefix gate --
        proving it is a real AST check and not a disguised filename/text
        match."""
        fixture_source = (
            "from odoo import http\n\n"
            "class NotAControllerSoundingName(http.Controller):\n"
            "    @http.route('/shopify_connector/oauth/callback', auth='public')\n"
            "    def callback(self, **kw):\n"
            "        return 'ok'\n"
        )
        tmp_dir = tempfile.mkdtemp()
        try:
            fixture_path = os.path.join(tmp_dir, 'zzz_totally_unsuspicious_name.py')
            with open(fixture_path, 'w', encoding='utf-8') as fh:
                fh.write(fixture_source)
            violations = controller_route_oauth_surfaces(fixture_path)
        finally:
            shutil.rmtree(tmp_dir)
        self.assertTrue(
            violations,
            "The guard must reject a synthetic controller/route fixture "
            "regardless of its filename.")

    def test_sparkline_conveys_more_than_colour(self):
        """Non-colour-alone charting, carried forward to Store 360 (the same
        R2 principle the 7-day sparkline satisfied before the trend chart
        replaced it): the trend must carry a full textual equivalent OUTSIDE
        the decorative ``role="img"`` bars (a real data table), and the
        previous-period series must be textured, never colour-alone.
        """
        xml = self._read('static', 'src', 'xml', 'shopify_connector_dashboard.xml')
        self.assertIn(
            'sc360-chart-table', xml,
            "The trend chart must carry a data-table equivalent.")
        self.assertIn(
            'bucket.value', xml,
            "The table equivalent must include the current-period value.")
        self.assertIn(
            'bucket.previous', xml,
            "The table equivalent must include the previous-period value.")
        scss = self._read('static', 'src', 'scss', 'shopify_connector_dashboard.scss')
        self.assertIn(
            'repeating-linear-gradient', scss,
            "The previous-period series must carry a non-colour (textured) "
            "fill, not just a different colour from the current bars.")

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
            # S1 (2026-07-27): the guided setup client action, its
            # Configuration menu and the re-run button on the store form. An
            # accepted MVP screen, so it joins the allowlist rather than
            # dissolving it.
            'shopify_connector_setup_views.xml',
            # Batch 2 checkpoint 1: the canonical per-store configuration
            # surface (Configuration -> Store Settings). It renders existing
            # settings fields that had no merchant-reachable route after
            # onboarding; it adds no client action, no controller and no
            # second setup flow. An accepted MVP screen, so it joins the
            # allowlist rather than dissolving it.
            'shopify_connector_store_settings_views.xml',
            # Store 360 slice: zero-schema list/graph/pivot analysis over the
            # job model under its native rules — no client action, no
            # controller, no new model. An accepted Store 360 deliverable,
            # so it joins the allowlist rather than dissolving it.
            'shopify_connector_job_analysis_views.xml',
        }
        present = {f for f in os.listdir(views_dir) if f.endswith('.xml')}
        self.assertEqual(
            present, allowed_views,
            "Only the U0-allowlisted view files may exist; found %s" % (present - allowed_views),
        )
        forbidden_tokens = ('fulfillment', 'setup_wizard', 'matching', 'mapping', 'export_preview')
        # The setup views file IS the setup wizard, so the token check runs
        # over every other file -- the guard exists to stop out-of-scope UI
        # leaking into the U0 files, not to forbid an accepted screen from
        # naming itself.
        # Batch 2 checkpoint 1, same principle, narrower carve-out. The
        # canonical Store Settings form renders `fulfillment_domain_enabled`
        # -- one of the FOUR sync-domain flags core declares on its own
        # settings model -- and its prose names Fulfillment Settings as the
        # surface owning the mode fields this one deliberately does not
        # duplicate. Neither is out-of-scope UI leaking into core; core is
        # naming a field it owns. So `fulfillment` alone is exempted for that
        # one file, per-token rather than per-file: `setup_wizard`,
        # `matching`, `mapping` and `export_preview` stay enforced there, and
        # every token stays enforced everywhere else.
        token_exemptions = {
            'shopify_connector_store_settings_views.xml': {'fulfillment'},
        }
        for f in present - {'shopify_connector_setup_views.xml'}:
            text = open(os.path.join(views_dir, f), encoding='utf-8').read().lower()
            exempt = token_exemptions.get(f, frozenset())
            for token in forbidden_tokens:
                if token in exempt:
                    continue
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
