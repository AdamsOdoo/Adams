"""U1 source/XML guards.

These assert the properties that make U1 safe by construction, straight off the
files, so a future edit that reintroduces a forbidden surface fails here rather
than in review:

  * no protected / sensitive field is rendered on any U1 template;
  * the wizards are display-and-delegate only -- no eligibility, blocker or
    review-required determination, no Job creation, no mutation, no Shopify
    call, no protected write;
  * no controller / webhook / OAuth / cron is introduced;
  * no SEC-3 quarantine control and no call to the release action anywhere;
  * no A2 badge and no synthesised "Delivered" claim;
  * U1 buttons name only sanctioned public actions.
"""

import ast
import re
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

# Contract section 9: never rendered anywhere in U1, on any template.
NEVER_RENDER_FIELDS = (
    'remote_mutation_intent', 'preconditions_snapshot', 'shopify_idempotency_key',
    'remote_evidence_refs', 'fulfillment_mode_switch_nonce', 'mode_switch_nonce',
    'state_snapshot', 'tracking_snapshot', 'tracking_numbers_snapshot',
    'tracking_urls_snapshot',
)
FINGERPRINT_FIELD = re.compile(r'name="[a-z0-9_]*_fingerprint"')

# The only public actions any U1 button may name (contract section 6), plus the
# two wizard entry points that delegate to them.
SANCTIONED_BUTTON_METHODS = frozenset((
    'action_start_mode2_switch', 'action_retry_mode2_switch',
    'action_rollback_to_mode1',
    'action_release_fulfillment_review', 'action_import_tracking',
    'action_acknowledge_external', 'action_validate_proposed',
    'action_confirm',
))

# Engine internals U1 must never invoke (contract section 7), plus the
# out-of-scope SEC-3 remediation action (Delta 4).
FORBIDDEN_CALLS = (
    '_release_blocked_mutation', '_find_single_blocked_mutation',
    '_handoff_replacement', '_enqueue_once', '_enqueue_picking_admission',
    '_enqueue_tracking_admission', '_observe_fulfillment', '_evaluate_mode2',
    '_apply_mode2', '_recover_pre_c2_failure',
    'action_sec3_release_scope_quarantine',
)


def _strip_xml_comments(source):
    """Guards must judge what is RENDERED, not what is explained.

    A comment describing the rule ("Delivered is never claimed...") is not a
    claim, and a comment naming a forbidden action is not a call to it. Scanning
    prose made these guards fire on their own documentation, which trains a
    maintainer to delete the explanation instead of the violation.
    """
    return re.sub(r'<!--.*?-->', '', source, flags=re.S)


def _strip_python_prose(source):
    """Remove docstrings and comments, leaving executable code."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            if (node.body and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)):
                node.body.pop(0)
    return ast.unparse(tree)


@tagged('post_install', '-at_install')
class TestUiSourceGuards(TransactionCase):

    def _addon_root(self):
        return Path(__file__).resolve().parents[1]

    def _ui_xml_files(self):
        root = self._addon_root()
        return sorted(
            list((root / 'views').glob('*.xml'))
            + list((root / 'wizards').glob('*.xml'))
        )

    def _wizard_py_files(self):
        return sorted(
            p for p in (self._addon_root() / 'wizards').glob('*.py')
            if p.name != '__init__.py'
        )

    # ---------------------------------------------------------------- redaction

    def test_no_protected_field_is_rendered(self):
        violations = []
        for path in self._ui_xml_files():
            source = _strip_xml_comments(path.read_text(encoding='utf-8'))
            for field in NEVER_RENDER_FIELDS:
                if 'name="%s"' % field in source:
                    violations.append((path.name, field))
            if FINGERPRINT_FIELD.search(source):
                violations.append((path.name, '*_fingerprint'))
        self.assertFalse(violations, 'Protected field rendered: %s' % violations)

    def test_no_sec3_quarantine_control_is_offered(self):
        """The flag may be READ to explain a withheld row; it is never a control,
        and the release action is never offered."""
        violations = []
        for path in self._ui_xml_files():
            source = _strip_xml_comments(path.read_text(encoding='utf-8'))
            if 'action_sec3_release_scope_quarantine' in source:
                violations.append((path.name, 'release action offered'))
            # A quarantine control would be a writable field or a button naming
            # it. Every occurrence must be inside an `invisible=` guard.
            for match in re.finditer(r'name="sec3_scope_quarantined"', source):
                violations.append((path.name, 'quarantine rendered as a field'))
        self.assertFalse(violations, violations)

    # ----------------------------------------------------- status/badge honesty

    def test_no_a2_fulfillment_order_status_badge(self):
        """A2 has no backing field, so no A2 surface may exist."""
        violations = []
        for path in self._ui_xml_files():
            source = _strip_xml_comments(path.read_text(encoding='utf-8'))
            if re.search(r'name="[a-z0-9_]*fulfillment_order_status[a-z0-9_]*"', source):
                violations.append(path.name)
        self.assertFalse(violations, violations)

    def test_delivered_is_never_offered_as_a_supported_state(self):
        """`delivered_inconsistency` may be rendered as the INCONSISTENCY case.

        What must not exist is a plain "Delivered" claim, i.e. the word used as
        a status a user could read as proven delivery. Every occurrence of
        "Delivered" in a U1 template must sit next to the words that say the
        Odoo delivery is NOT validated.
        """
        violations = []
        for path in self._ui_xml_files():
            for line_no, line in enumerate(
                _strip_xml_comments(path.read_text(encoding='utf-8')).splitlines(),
                start=1,
            ):
                if 'Delivered' not in line:
                    continue
                lowered = line.lower()
                qualified = (
                    'not validated' in lowered
                    or 'mismatch' in lowered
                    or 'delivered_inconsistency' in lowered
                    or 'per carrier' in lowered
                )
                if not qualified:
                    violations.append((path.name, line_no, line.strip()[:70]))
        self.assertFalse(
            violations,
            'Unqualified "Delivered" claim: %s' % violations,
        )

    # ------------------------------------------------- display-and-delegate

    def test_wizards_create_no_job_and_perform_no_mutation(self):
        violations = []
        for path in self._wizard_py_files():
            tree = ast.parse(path.read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Attribute):
                    if func.attr in FORBIDDEN_CALLS:
                        violations.append((path.name, func.attr))
                    # A wizard may not create or write business records.
                    if func.attr in ('create', 'write', 'unlink'):
                        violations.append((path.name, func.attr))
        self.assertFalse(
            violations,
            'A wizard performs a forbidden operation: %s' % violations,
        )

    def test_wizards_never_call_shopify_or_read_a_credential(self):
        violations = []
        for path in self._wizard_py_files():
            source = _strip_python_prose(path.read_text(encoding='utf-8')).lower()
            for needle in ('graphql', 'requests.', 'access_token', 'credential',
                           'myshopify.com', 'urlopen', 'http'):
                if needle in source:
                    violations.append((path.name, needle))
        self.assertFalse(violations, violations)

    def test_wizards_use_no_sudo(self):
        """A display-and-delegate wizard reads with the caller's own rights, so
        record rules -- including the SEC-3 fail-closed rules -- apply."""
        violations = []
        for path in self._wizard_py_files():
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'sudo'
                ):
                    violations.append(path.name)
        self.assertFalse(violations, 'A wizard uses sudo(): %s' % violations)

    def test_wizard_reads_are_bounded(self):
        """Every search/search_count on a confirmation screen carries a limit."""
        unbounded = []
        for path in self._wizard_py_files():
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8'))):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr in ('search', 'search_count', 'search_read')
                ):
                    if not any(kw.arg == 'limit' for kw in node.keywords):
                        unbounded.append((path.name, node.func.attr, node.lineno))
        self.assertFalse(unbounded, 'Unbounded read in a wizard: %s' % unbounded)

    # ---------------------------------------------------------- no new surface

    def test_u1_introduces_no_controller_webhook_oauth_or_cron(self):
        root = self._addon_root()
        self.assertFalse(
            (root / 'controllers').exists(),
            'U1 must not add a controllers package.',
        )
        violations = []
        for path in self._wizard_py_files():
            source = _strip_python_prose(path.read_text(encoding='utf-8'))
            for needle in ('odoo.http', '@route', 'oauth', 'webhook'):
                if needle in source.lower():
                    violations.append((path.name, needle))
        # No new cron: the only cron data file is the Wave 4 one.
        crons = sorted(p.name for p in (root / 'data').glob('*.xml'))
        self.assertEqual(
            crons, ['shopify_connector_fulfillment_cron.xml'],
            'U1 must not add a data/cron file; found %s' % crons,
        )
        self.assertFalse(violations, violations)

    def test_buttons_name_only_sanctioned_methods(self):
        violations = []
        for path in self._ui_xml_files():
            source = path.read_text(encoding='utf-8')
            for match in re.finditer(
                r'<button[^>]*?name="([a-zA-Z_][a-zA-Z0-9_]*)"[^>]*?type="object"',
                _strip_xml_comments(source), re.S,
            ):
                if match.group(1) not in SANCTIONED_BUTTON_METHODS:
                    violations.append((path.name, match.group(1)))
        self.assertFalse(
            violations,
            'Button wired to a non-sanctioned method: %s' % violations,
        )

    def test_no_owl_production_surface_or_external_asset(self):
        root = self._addon_root()
        js = sorted((root / 'static').rglob('*.js')) if (root / 'static').exists() else []
        production_js = [p for p in js if 'tests' not in p.parts]
        self.assertFalse(
            production_js,
            'PD-7 excludes fulfillment from Owl; found %s' % production_js,
        )
        violations = []
        for path in self._ui_xml_files():
            source = _strip_xml_comments(path.read_text(encoding='utf-8'))
            for needle in ('https://', 'http://', 'cdn.', '.woff'):
                if needle in source:
                    violations.append((path.name, needle))
        self.assertFalse(violations, 'External asset reference: %s' % violations)
