import ast
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    ERROR_CLASS_SELECTION,
    MANUAL_REVIEW_SUBREASON_SELECTION,
)
from odoo.addons.shopify_connector_fulfillment.models import (
    shopify_connector_fulfillment_inbound_evidence as evidence_model,
)

REVIEW_REASON_SELECTION = evidence_model.REVIEW_REASON_SELECTION

# Theme G: the exact, finite set of call/dict shapes through which this
# addon's production code can persist a literal onto a CORE
# `shopify.connector.job.error_class` / `.manual_review_subreason` (as
# opposed to the domain-only `review_reason` written onto evidence records,
# a different field entirely — e.g. `_open_review(evidence, 'binding_conflict')`
# does not match any shape below). Each entry names the callable and the
# zero-indexed positional argument slot(s) that carry an error-class-like
# literal.
_ERROR_CLASS_CALL_SHAPES = {
    'JobHandlerError': (0,),
    'FulfillmentReadError': (0,),
    'FulfillmentPreC2FailClosedError': (0,),
    '_fail_closed_pre_c2': (0,),
    '_uncertain_consequence': (0,),
    '_transition_failed_final': (0,),
    '_block_original_job': (1, 2),
}
_ERROR_CLASS_DICT_KEYS = frozenset(('error_class', 'manual_review_subreason'))


def _module_level_constants(tree):
    """Name -> literal string value, for every simple `NAME = 'literal'`
    module-level assignment (resolves e.g. `ERROR_CLASS_TEMPORARY =
    'shopify_temporary_server_network'` so a call site passing the NAME is
    still genuinely traced back to its literal value)."""
    constants = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign) and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            constants[node.targets[0].id] = node.value.value
    return constants


def _resolve_literal(node, constants):
    """A Constant string's own value, or a Name's resolved module-level
    constant value, or None when the argument is neither (e.g. `exc.
    error_class`, `False`, `None`, a runtime variable) — never guessed."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in constants:
        return constants[node.id]
    return None


def _call_name(call_node):
    func = call_node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _persisted_core_classes_in_source(source):
    """AST-derive the actual, exhaustive set of core error_class /
    manual_review_subreason literals this addon's production source can
    persist onto a `shopify.connector.job` — never hand-maintained, so a new
    call site can never silently go uncounted (Theme G)."""
    tree = ast.parse(source)
    constants = _module_level_constants(tree)
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node)
            slots = _ERROR_CLASS_CALL_SHAPES.get(name)
            if slots:
                for slot in slots:
                    if slot < len(node.args):
                        literal = _resolve_literal(node.args[slot], constants)
                        if literal:
                            found.add(literal)
            # Keyword form: JobHandlerError(error_class=..., ...) and similar.
            for keyword in node.keywords:
                if keyword.arg in _ERROR_CLASS_DICT_KEYS:
                    literal = _resolve_literal(keyword.value, constants)
                    if literal:
                        found.add(literal)
        elif isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and key.value in _ERROR_CLASS_DICT_KEYS
                ):
                    literal = _resolve_literal(value, constants)
                    if literal:
                        found.add(literal)
    return found


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestFulfillmentVocabularyGuard(TransactionCase):
    """Cross-registry vocabulary containment (DEC-038 §7.2) — genuine,
    source-derived (Theme G correction).

    The fulfillment domain owns its own review-case vocabulary
    (``REVIEW_REASON_SELECTION``), but every ``error_class`` /
    ``manual_review_subreason`` it ever *persists on a core job* must be a
    value the core registries already accept. Both containment directions
    are asserted: every literal this addon's production source can actually
    persist must be in the merged core registry (catches inventing a
    nonexistent core class), AND the genuinely AST-derived persisted set is
    used directly — not a hand-maintained allowlist that could silently omit
    a real persisted class (the prior, tautological version of this guard
    missed `unknown_system_error`, genuinely persisted via
    `job._transition_failed_final` in this addon's own
    `shopify_connector_job_dispatch.py`).
    """

    def setUp(self):
        super().setUp()
        self.core_error_classes = {value for value, _ in ERROR_CLASS_SELECTION}
        self.core_subreasons = {
            value for value, _ in MANUAL_REVIEW_SUBREASON_SELECTION
        }
        self.merged_core = self.core_error_classes | self.core_subreasons
        self.domain_review_reasons = {
            value for value, _ in REVIEW_REASON_SELECTION
        }

    def _addon_root(self):
        return Path(__file__).resolve().parents[1]

    def _persisted_core_classes(self):
        found = set()
        for path in sorted((self._addon_root() / 'models').glob('*.py')):
            found |= _persisted_core_classes_in_source(
                path.read_text(encoding='utf-8')
            )
        return found

    def test_every_ast_derived_persisted_class_is_in_merged_core_registry(self):
        # Direction 1: nothing this addon's source actually persists may be
        # a core class that doesn't exist.
        persisted = self._persisted_core_classes()
        self.assertTrue(persisted, 'the AST scan found zero persisted classes')
        missing = persisted - self.merged_core
        self.assertEqual(
            missing, set(),
            'Fulfillment persists core classes absent from the merged core '
            'registries: %s' % sorted(missing),
        )

    def test_unknown_system_error_is_detected_as_genuinely_persisted(self):
        # Direction 2: the genuine AST scan must find every real call site,
        # not just the ones a hand-typed allowlist happened to name. This is
        # the exact omission the prior tautological guard structurally could
        # not detect (job_dispatch.py's `_transition_failed_final(
        # 'unknown_system_error', ...)` reconcile-link-missing path).
        persisted = self._persisted_core_classes()
        self.assertIn('unknown_system_error', persisted)
        self.assertIn('unknown_system_error', self.merged_core)

    def test_scan_rejects_a_synthetic_incomplete_allowlist(self):
        # Demonstrates the exact structural blind spot that made the prior
        # guard's omission undetectable: a hand-typed allowlist missing a
        # genuinely persisted class still satisfies a direction-1-only
        # containment check (allowlist subset-of-core) — that check alone
        # can never catch its own incompleteness. Comparing it against the
        # genuine AST-derived set (direction 2) proves the omission.
        persisted = self._persisted_core_classes()
        synthetic_incomplete_allowlist = frozenset(
            persisted - {'unknown_system_error'}
        )
        self.assertTrue(
            synthetic_incomplete_allowlist <= self.merged_core,
            'the synthetic allowlist should still (wrongly) look complete '
            'under a direction-1-only check',
        )
        self.assertFalse(
            persisted <= synthetic_incomplete_allowlist,
            'the genuine AST-derived set must expose the synthetic '
            'allowlist as incomplete',
        )

    def test_over_fulfillment_absent_from_both_core_registries(self):
        # Removed vocabulary: never re-introduced into either core registry.
        self.assertNotIn('over_fulfillment', self.core_error_classes)
        self.assertNotIn('over_fulfillment', self.core_subreasons)
        self.assertNotIn('over_fulfillment', self.merged_core)

    def test_quantity_overrun_is_domain_only(self):
        # The overrun review case is a DOMAIN review reason, separate from core.
        self.assertIn('quantity_overrun', self.domain_review_reasons)
        self.assertNotIn('quantity_overrun', self.core_error_classes)
        self.assertNotIn('quantity_overrun', self.core_subreasons)

    def test_quantity_overrun_maps_to_core_ambiguous_match(self):
        # DEC-038 §7.2 / evidence module docstring: a quantity-overrun review
        # case persists the core error_class 'ambiguous_match' on any core job
        # (there is no 'over_fulfillment' core class to persist). Verified
        # against the genuine AST-derived set (no tautological self-compare).
        self.assertIn('quantity_overrun', self.domain_review_reasons)
        self.assertIn('ambiguous_match', self._persisted_core_classes())
        self.assertIn('ambiguous_match', self.core_error_classes)
        self.assertIn('ambiguous_match', self.merged_core)

    def test_notification_confirmation_missing_in_both_core_registries(self):
        # This one IS a genuine core value present in BOTH registries.
        self.assertIn(
            'fulfillment_notification_confirmation_missing',
            self.core_error_classes,
        )
        self.assertIn(
            'fulfillment_notification_confirmation_missing',
            self.core_subreasons,
        )

    # ------------------------------------------------------------------
    # Theme H: the new Mode-1 review-reason value is registered here.
    # ------------------------------------------------------------------

    def test_external_fulfillment_observed_registered_and_distinct(self):
        self.assertIn(
            'external_fulfillment_observed', self.domain_review_reasons,
        )
        reasons = [value for value, _ in REVIEW_REASON_SELECTION]
        self.assertEqual(len(reasons), len(set(reasons)))
        self.assertEqual(len(reasons), 21)
        # Distinct from the two values it must never collide with.
        self.assertNotEqual(
            'external_fulfillment_observed', 'remote_state_changed',
        )
        self.assertNotEqual(
            'external_fulfillment_observed', 'mode_not_enabled',
        )
