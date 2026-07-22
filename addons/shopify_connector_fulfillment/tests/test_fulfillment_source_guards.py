import ast
import re
from pathlib import Path

from odoo.tests.common import TransactionCase

RAW_HTTP_METHODS = {'get', 'post', 'put', 'patch', 'delete', 'request'}
GRAPHQL_MUTATION_LITERAL = re.compile(
    r'(?:^|[\r\n])\s*mutation\s+[A-Za-z_][A-Za-z0-9_]*\s*[({]'
)
FORBIDDEN_LEGACY = (
    'fulfillmentCreateV2', 'fulfillmentTrackingInfoUpdateV2',
    'FulfillmentV2Input',
)
FORBIDDEN_HOLD_MUTATIONS = (
    'fulfillmentOrderMove', 'fulfillmentOrderHold', 'fulfillmentOrderReleaseHold',
)

# The exact ten frozen job types (packet §11.2). No per-domain reconcile; no
# fulfillment_review_release job type.
TEN_JOB_TYPES = frozenset((
    'fulfillment_picking_admission', 'fulfillment_create',
    'fulfillment_tracking_admission', 'fulfillment_tracking_update',
    'fulfillment_mutation_reconcile', 'fulfillment_inbound_observation',
    'fulfillment_reconciliation_check', 'fulfillment_reconnect_catchup',
    'fulfillment_mode_switch_scan', 'fulfillment_mode2_evaluation',
))

# The exact enumerated production + test file allowlist (§2/§5).
ALLOWED_MODEL_FILES = frozenset((
    '__init__.py', 'shopify_connector_fulfillment_binding.py',
    'shopify_connector_fulfillment_inbound_evidence.py',
    'shopify_connector_store_settings.py', 'shopify_connector_job.py',
    'shopify_connector_readiness_check.py',
    'shopify_connector_fulfillment_reader.py',
    'shopify_connector_fulfillment_admission.py',
    'shopify_connector_fulfillment_create_strategy.py',
    'shopify_connector_fulfillment_tracking_strategy.py',
    'shopify_connector_fulfillment_inbound.py',
    'shopify_connector_fulfillment_review.py',
    'shopify_connector_fulfillment_mode2.py',
    'shopify_connector_fulfillment_scans.py',
    'shopify_connector_job_dispatch.py', 'stock_picking.py',
))
ALLOWED_TEST_FILES = frozenset((
    '__init__.py', 'test_fulfillment_binding.py',
    'test_fulfillment_inbound_evidence.py', 'test_fulfillment_trigger.py',
    'test_fulfillment_admission.py', 'test_fulfillment_reader_pagination.py',
    'test_fulfillment_matching.py', 'test_fulfillment_location_resolution.py',
    'test_fulfillment_create_strategy.py', 'test_fulfillment_tracking_strategy.py',
    'test_fulfillment_idempotency.py', 'test_fulfillment_inbound_classification.py',
    'test_fulfillment_mode2_engine.py', 'test_fulfillment_mode_switch.py',
    'test_fulfillment_scans.py', 'test_fulfillment_review_release.py',
    'test_fulfillment_cod_interplay.py', 'test_fulfillment_state_model.py',
    'test_fulfillment_lifecycle.py', 'test_fulfillment_readiness.py',
    'test_fulfillment_vocabulary_guard.py', 'test_fulfillment_source_guards.py',
    'test_fulfillment_concurrency.py',
    'runtime_layer2_fulfillment_concurrency_harness.py',
))


def _string_constants(tree):
    return [
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


class TestFulfillmentSourceGuards(TransactionCase):

    def _addon_root(self):
        return Path(__file__).resolve().parents[1]

    def _model_files(self):
        return sorted((self._addon_root() / 'models').glob('*.py'))

    def _model_sources(self):
        return {p: p.read_text(encoding='utf-8') for p in self._model_files()}

    # -- RA-022: no legacy V2/REST/Order-Fulfillment surface in production docs

    def test_no_legacy_v2_fulfillment_surface(self):
        violations = []
        for path, source in self._model_sources().items():
            for literal in _string_constants(ast.parse(source)):
                if any(name in literal for name in FORBIDDEN_LEGACY):
                    violations.append((path.name, literal[:40]))
        self.assertFalse(violations, violations)

    def test_no_hold_or_move_mutations_in_production(self):
        violations = []
        for path, source in self._model_sources().items():
            for literal in _string_constants(ast.parse(source)):
                if any(name in literal for name in FORBIDDEN_HOLD_MUTATIONS):
                    violations.append((path.name, literal[:40]))
        self.assertFalse(violations, violations)

    # -- RA-023: explicit FulfillmentOrder line lists in the create document

    def test_create_document_uses_explicit_line_lists(self):
        from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_create_strategy import (  # noqa: E501
            FULFILLMENT_CREATE_DOCUMENT,
        )
        self.assertIn('lineItemsByFulfillmentOrder', FULFILLMENT_CREATE_DOCUMENT)
        self.assertIn('fulfillmentCreate', FULFILLMENT_CREATE_DOCUMENT)

    # -- No @idempotent in any fulfillment operation string

    def test_no_idempotent_directive_in_operations(self):
        violations = []
        for path, source in self._model_sources().items():
            for literal in _string_constants(ast.parse(source)):
                if '@idempotent' in literal:
                    violations.append((path.name, literal[:40]))
        self.assertFalse(violations, violations)

    # -- No qty_done / quantity_done field access (Odoo 19)

    def test_no_qty_done_field_access(self):
        violations = []
        for path, source in self._model_sources().items():
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Attribute) and node.attr in (
                    'qty_done', 'quantity_done',
                ):
                    violations.append((path.name, node.lineno))
        self.assertFalse(violations, violations)

    # -- No inventory coupling: never query shopify.connector.location.mapping

    def test_no_location_mapping_access(self):
        violations = []
        for path, source in self._model_sources().items():
            for node in ast.walk(ast.parse(source)):
                if (
                    isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and node.slice.value == 'shopify.connector.location.mapping'
                ):
                    violations.append((path.name, node.lineno))
        self.assertFalse(violations, violations)

    # -- No raw transport: no requests.<verb>, no _send call, no .execute() for
    #    mutations (mutations only through execute_business).

    def test_no_raw_transport(self):
        violations = []
        for path, source in self._model_sources().items():
            for node in ast.walk(ast.parse(source)):
                if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)):
                    continue
                attr = node.func.attr
                if attr == '_send':
                    violations.append((path.name, node.lineno, '_send'))
                if (
                    attr in RAW_HTTP_METHODS
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == 'requests'
                ):
                    violations.append((path.name, node.lineno, 'requests.%s' % attr))
        self.assertFalse(violations, violations)

    # -- Mutation documents are only reachable through the guarded transport.

    def test_fulfillment_mutation_documents_are_guarded(self):
        # The fulfillment GraphQL mutations live only in the two strategy files
        # as module constants, and are only ever passed to
        # client.execute_business(..., mutation_context=...) in the paired
        # _transport_* method.
        strategy_files = {
            'shopify_connector_fulfillment_create_strategy.py',
            'shopify_connector_fulfillment_tracking_strategy.py',
        }
        for path, source in self._model_sources().items():
            for literal in _string_constants(ast.parse(source)):
                if 'fulfillmentCreate(' in literal or (
                    'fulfillmentTrackingInfoUpdate(' in literal
                ):
                    self.assertIn(
                        path.name, strategy_files,
                        'Fulfillment mutation document found outside a strategy '
                        'file: %s' % path.name,
                    )
        for name in strategy_files:
            source = (self._addon_root() / 'models' / name).read_text('utf-8')
            self.assertIn('execute_business', source)
            self.assertIn('mutation_context', source)

    # -- Registry: exactly the ten frozen job types; shared reconcile only.

    def test_exactly_ten_fulfillment_job_types_registered(self):
        Dispatch = self.env['shopify.connector.job.dispatch']
        handlers = set(Dispatch._get_handlers())
        replay = set(Dispatch._get_replay_policies())
        fulfillment_handlers = {h for h in handlers if h.startswith('fulfillment_')}
        self.assertEqual(fulfillment_handlers, TEN_JOB_TYPES)
        self.assertTrue(TEN_JOB_TYPES <= replay)
        # No per-domain reconcile, no review-release job type.
        self.assertNotIn('fulfillment_create_reconcile', handlers)
        self.assertNotIn('fulfillment_tracking_reconcile', handlers)
        self.assertNotIn('fulfillment_review_release', handlers)
        # The two mutation domains share the one reconcile job type.
        strategies = Dispatch._get_reconciliation_strategies()
        reconcile_types = {
            strategies[d]['reconciliation_job_type']
            for d in ('fulfillment_create', 'fulfillment_tracking_update')
        }
        self.assertEqual(reconcile_types, {'fulfillment_mutation_reconcile'})

    # -- No Wave 4 job admits from job_source='webhook'.

    def test_no_webhook_source_enqueued(self):
        violations = []
        for path, source in self._model_sources().items():
            for node in ast.walk(ast.parse(source)):
                if (
                    isinstance(node, ast.Constant)
                    and node.value == 'webhook'
                ):
                    violations.append((path.name, node.lineno))
        self.assertFalse(violations, violations)

    # -- P2 correction: condition 14's separately fresh read uses only the
    #    sanctioned read-only reader path; no raw transport; no mutation
    #    document reachable from it.

    def _condition14_function_node(self):
        source = (self._addon_root() / 'models'
                  / 'shopify_connector_fulfillment_mode2.py').read_text('utf-8')
        tree = ast.parse(source)
        return next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == '_c14_remote_state'
        )

    def test_condition14_uses_only_sanctioned_read_methods(self):
        c14 = self._condition14_function_node()
        calls = {
            node.func.attr for node in ast.walk(c14)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        # It must actually perform its own read through the sanctioned
        # read-only reader/location-resolution methods...
        self.assertTrue(
            calls & {'_read_order_fulfillments', '_read_fulfillment_orders',
                      '_resolve_single_location'},
        )
        # ...and never through raw transport or the mutation-execution path.
        self.assertNotIn('_send', calls)
        self.assertNotIn('execute_business', calls)
        self.assertNotIn('execute', calls)

    def test_condition14_contains_no_mutation_document(self):
        c14 = self._condition14_function_node()
        literals = [
            node.value for node in ast.walk(c14)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        ]
        for literal in literals:
            self.assertNotRegex(literal.lower(), r'\bmutation\b')
            self.assertNotIn('fulfillmentcreate(', literal.lower())
            self.assertNotIn('fulfillmenttrackinginfoupdate(', literal.lower())

    # -- File-boundary guard: nothing outside the §2/§5 enumerated allowlist.

    def test_file_boundary_allowlist(self):
        root = self._addon_root()
        model_files = {p.name for p in (root / 'models').glob('*.py')}
        self.assertTrue(
            model_files <= ALLOWED_MODEL_FILES,
            'Unexpected model file(s): %s' % (model_files - ALLOWED_MODEL_FILES),
        )
        test_files = {p.name for p in (root / 'tests').glob('*.py')}
        self.assertTrue(
            test_files <= ALLOWED_TEST_FILES,
            'Unexpected test file(s): %s' % (test_files - ALLOWED_TEST_FILES),
        )
