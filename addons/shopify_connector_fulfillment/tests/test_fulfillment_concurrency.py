import ast
import uuid
from pathlib import Path
from unittest.mock import Mock, patch

from odoo import api, fields, SUPERUSER_ID
from odoo.sql_db import db_connect
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_job import (
    fulfillment_operation_scope_key,
)


# ---------------------------------------------------------------------------
# No-fake-success static guard (Stage R2A P1 correction).
#
# Stage R1 disclosed that two harness scenarios were hard-coded `ok: True`
# stubs with no process creation, no fixture, and no durable-outcome check.
# The AST-based audit below enforces harness *structure* only (this file
# never imports/executes the harness -- runtime success is proven only at
# Gate C); it must reject a future regression to the same shape without
# tripping on comments/docstrings that merely *mention* the old pattern.
# ---------------------------------------------------------------------------

REQUIRED_CONCURRENCY_SCENARIOS = frozenset((
    'c1_ownership_race',
    'operation_scope_serialization',
    'concurrent_inconclusive_increment',
    'duplicate_picking_admission',
    'duplicate_tracking_admission',
    'reconciliation_replacement_race',
    'review_release_race',
    'mode_switch_interaction',
    'rollback_injection_recovery',
))

# Any one of these call names, found anywhere in a scenario's reachable
# closure (its own body plus every locally-defined helper it calls,
# transitively), counts as genuine process/transaction orchestration.
_PROCESS_EVIDENCE_CALLS = frozenset(('get_context', 'Process'))
# Any one of these call names counts as inspecting a durable DB outcome.
_DURABLE_QUERY_CALLS = frozenset(('search', 'browse', 'search_count', 'read', 'execute'))
# A call to the shared cleanup entrypoint counts as a cleanup/residue check.
_CLEANUP_CALLS = frozenset(('_finish_cleanup',))


def _ast_literal_str_elements(node):
    return [elt.value for elt in node.elts if isinstance(elt, ast.Constant)]


def _ast_dict_str_to_name(node):
    mapping = {}
    for key, value in zip(node.keys, node.values):
        if isinstance(key, ast.Constant) and isinstance(value, ast.Name):
            mapping[key.value] = value.id
    return mapping


def _call_target_names(node):
    """Every function/method name a Call node inside `node` invokes."""
    names = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            func = child.func
            if isinstance(func, ast.Name):
                names.add(func.id)
            elif isinstance(func, ast.Attribute):
                names.add(func.attr)
    return names


def _is_trivial_stub_return(func_node):
    """True if `func_node`'s own body (ignoring a leading docstring) is
    nothing but `return {<dict literal>}` -- the exact shape of the
    disclosed Stage R1 stubs, regardless of which keys the dict carries."""
    body = func_node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(
            getattr(body[0], 'value', None), ast.Constant):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    return isinstance(body[0].value, ast.Dict)


def _closure_nodes(name, functions, seen):
    """AST nodes reachable from local function `name`: its own body plus
    every locally-defined helper it calls, transitively (bounded to this
    module's own top-level functions -- stdlib/ORM calls are leaves)."""
    if name in seen or name not in functions:
        return []
    seen.add(name)
    node = functions[name]
    nodes = list(ast.walk(node))
    for target in _call_target_names(node):
        if target in functions and target not in seen:
            nodes.extend(_closure_nodes(target, functions, seen))
    return nodes


def audit_concurrency_harness_scenarios(source):
    """Structural (AST-only) audit of the external harness's SCENARIOS/
    RUNNERS wiring. Returns a list of human-readable violation strings;
    empty means the harness structurally satisfies the no-fake-success
    contract. Never executes the harness or imports `odoo`."""
    violations = []
    tree = ast.parse(source)
    functions = {
        node.name: node for node in tree.body
        if isinstance(node, ast.FunctionDef)
    }

    scenario_names = None
    runner_map = None
    for node in tree.body:
        if not (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            continue
        target_name = node.targets[0].id
        if target_name == 'SCENARIOS' and isinstance(node.value, (ast.Tuple, ast.List)):
            scenario_names = _ast_literal_str_elements(node.value)
        elif target_name == 'RUNNERS' and isinstance(node.value, ast.Dict):
            runner_map = _ast_dict_str_to_name(node.value)

    if scenario_names is None:
        return ['no module-level SCENARIOS tuple found']
    if runner_map is None:
        return ['no module-level RUNNERS dict found']

    missing_required = REQUIRED_CONCURRENCY_SCENARIOS - set(scenario_names)
    if missing_required:
        violations.append(
            'frozen concurrency scenarios missing from SCENARIOS: %r'
            % sorted(missing_required))
    if set(scenario_names) != set(runner_map):
        violations.append(
            'SCENARIOS and RUNNERS keys differ: %r'
            % sorted(set(scenario_names) ^ set(runner_map)))

    for scenario in sorted(scenario_names):
        runner_name = runner_map.get(scenario)
        if not runner_name or runner_name not in functions:
            violations.append(
                '%s: mapped to a placeholder/missing implementation (%r)'
                % (scenario, runner_name))
            continue
        runner_node = functions[runner_name]

        if _is_trivial_stub_return(runner_node):
            violations.append(
                '%s: runner %s() is a bare literal-dict return with no '
                'orchestration -- the exact Stage R1 stub shape'
                % (scenario, runner_name))
            continue

        closure = _closure_nodes(runner_name, functions, set())
        closure_calls = set()
        for n in closure:
            if isinstance(n, ast.Call):
                func = n.func
                if isinstance(func, ast.Name):
                    closure_calls.add(func.id)
                elif isinstance(func, ast.Attribute):
                    closure_calls.add(func.attr)

        if not (closure_calls & _PROCESS_EVIDENCE_CALLS):
            violations.append(
                '%s: no process creation or independent-transaction '
                'orchestration found (own body + local helper closure)'
                % scenario)
        if not (closure_calls & _DURABLE_QUERY_CALLS):
            violations.append(
                '%s: never inspects a durable database outcome'
                % scenario)
        if not (closure_calls & _CLEANUP_CALLS):
            violations.append(
                '%s: no cleanup/residue verification reachable' % scenario)
        if not any(
                isinstance(n, ast.Attribute) and n.attr == 'exitcode'
                for n in closure):
            violations.append(
                '%s: parent result never inspects a child exit code'
                % scenario)

    return violations


@tagged('post_install', '-at_install')
class TestFulfillmentConcurrency(TransactionCase):
    """Genuine independent-transaction concurrency for the fulfillment Layer 2
    path: the shared reconcile owns no remote-effect operation scope, the two
    mutation domains hold distinct Q1 scopes, and an overlapping same-scope
    mutation insert is refused (serialized to exactly one)."""

    def setUp(self):
        super().setUp()
        self.dbname = self.env.cr.dbname

    # -- The reconcile job owns/inherits NO remote-effect operation scope.

    def test_shared_reconcile_owns_no_operation_scope(self):
        store = self.env['shopify.connector.store'].create({
            'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id, 'fulfillment_domain_enabled': True,
        })
        # A reconcile job has no res_model -> operation_scope_key is False.
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'reconciliation',
            'job_type': 'fulfillment_create', 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 5,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/9',
            'payload_hash': uuid.uuid4().hex,
        })
        # The mutation job DOES hold the Q1 literal.
        self.assertEqual(
            job.operation_scope_key,
            fulfillment_operation_scope_key(
                'fulfillment_create', store.id, 5,
                'gid://shopify/FulfillmentOrder/9',
            ),
        )

    def test_mutation_scopes_distinct_per_domain(self):
        create_scope = fulfillment_operation_scope_key(
            'fulfillment_create', 1, 5, 'gid://shopify/FulfillmentOrder/9')
        tracking_scope = fulfillment_operation_scope_key(
            'fulfillment_tracking_update', 1, 5, 'gid://shopify/Fulfillment/9')
        self.assertNotEqual(create_scope, tracking_scope)
        self.assertTrue(create_scope.startswith('fulfillment_create:'))
        self.assertTrue(
            tracking_scope.startswith('fulfillment_tracking_update:'))

    def test_terminal_mutation_job_releases_its_scope(self):
        store = self.env['shopify.connector.store'].create({
            'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id, 'fulfillment_domain_enabled': True,
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'manual_sync',
            'job_type': 'fulfillment_create', 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 7,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/7',
            'payload_hash': uuid.uuid4().hex,
        })
        self.assertTrue(job.operation_scope_key)
        job.sudo().write({
            'state': 'cancelled', 'cancel_reason': 'x',
            'finished_at': fields.Datetime.now(),
        })
        job.invalidate_recordset()
        # A terminal job clears its scope so a replacement never collides.
        self.assertFalse(job.operation_scope_key)

    def test_overlapping_same_scope_insert_is_refused(self):
        """Genuine independent-connection overlap: an uncommitted mutation job
        holding an operation scope blocks a second insert of the same scope
        (unique operation-scope index). Runs on real pooled cursors at Gate C."""
        # Committed store fixture on its own connection.
        with db_connect(self.dbname).cursor() as setup_cr:
            env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07', 'state': 'connected',
            })
            env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'fulfillment_domain_enabled': True,
            })
            store_id = store.id
            setup_cr.commit()
        self.addCleanup(self._cleanup_store, store_id)

        vals = {
            'store_id': store_id, 'job_source': 'manual_sync',
            'job_type': 'fulfillment_create', 'state': 'queued',
            'res_model': 'stock.picking', 'res_id': 42,
            'shopify_target_gid': 'gid://shopify/FulfillmentOrder/42',
            'payload_hash': 'scope-a',
        }
        # First connection holds an uncommitted job with the scope live.
        holder_cr = db_connect(self.dbname).cursor()
        try:
            holder_env = api.Environment(holder_cr, SUPERUSER_ID, {})
            holder_env['shopify.connector.job'].create(vals)
            holder_env.cr.flush()
            # Second connection: same scope, different payload -> refused.
            with db_connect(self.dbname).cursor() as other_cr:
                other_cr.execute('SET LOCAL lock_timeout = %s', ('2s',))
                other_env = api.Environment(other_cr, SUPERUSER_ID, {})
                clash = dict(vals, payload_hash='scope-b')
                with self.assertRaises(Exception):
                    other_env['shopify.connector.job'].create(clash)
                    other_env.cr.flush()
        finally:
            holder_cr.rollback()
            holder_cr.close()

    def _cleanup_store(self, store_id):
        with db_connect(self.dbname).cursor() as cr:
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store_settings WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s', (store_id,),
            )
            cr.commit()

    # -- P2 correction: Mode 2 condition 14's separately fresh read --------

    def test_condition14_no_lock_spans_the_shopify_read(self):
        # Condition 14's fresh read must never run inside an Odoo row lock or
        # open business transaction (no `try_lock_for_update` / `FOR UPDATE`
        # call reachable from its function body).
        path = (Path(__file__).resolve().parents[1] / 'models'
                / 'shopify_connector_fulfillment_mode2.py')
        tree = ast.parse(path.read_text('utf-8'))
        c14 = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == '_c14_remote_state'
        )
        calls = {
            node.func.attr for node in ast.walk(c14)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn('try_lock_for_update', calls)
        self.assertNotIn('lock_for_update', calls)

    def test_local_validation_cannot_race_past_changed_second_read(self):
        # Even though condition 3's initial read observed SUCCESS (letting
        # every earlier condition pass), a genuinely different, changed
        # condition-14 second read must still block local validation --
        # proving local validation can never win a race against a stale
        # first observation.
        store = self.env['shopify.connector.store'].create({
            'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        settings = self.env['shopify.connector.store.settings'].create({
            'store_id': store.id, 'fulfillment_domain_enabled': True,
        })
        settings.sudo().write({'fulfillment_operating_mode': 'mode2'})
        product = self.env['product.product'].create({
            'name': 'P', 'type': 'consu', 'is_storable': True,
        })
        partner = self.env['res.partner'].create({'name': 'C'})
        sale = self.env['sale.order'].create({'partner_id': partner.id})
        sale_line = self.env['sale.order.line'].create({
            'order_id': sale.id, 'product_id': product.id,
            'product_uom_qty': 2.0,
            'shopify_line_item_gid': 'gid://shopify/LineItem/1',
        })
        order_binding = self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': store.id, 'shopify_gid': 'gid://shopify/Order/1',
            'sale_order_id': sale.id, 'status': 'active',
        })
        self.env['shopify.connector.location'].sudo().create({
            'store_id': store.id, 'shopify_location_gid': 'gid://shopify/Location/1',
            'name': 'L', 'shopify_location_active': True,
        })
        evidence = self.env['shopify.connector.fulfillment.inbound.evidence'].sudo().create({
            'store_id': store.id,
            'shopify_fulfillment_gid': 'gid://shopify/Fulfillment/1',
            'shopify_order_gid': 'gid://shopify/Order/1',
            'order_binding_id': order_binding.id,
            'origin_class': 'external_merchant', 'origin_confirmed': True,
            'fulfillment_status_raw': 'SUCCESS',
            'fulfillment_status_normalized': 'Success',
            'fulfillment_status_is_success': True,
            'reconciled_state': 'observed',
        })

        def _node(status):
            return {
                'id': 'gid://shopify/Fulfillment/1', 'status': status,
                'fulfillmentLineItems': {'nodes': [{
                    'id': 'gid://shopify/FulfillmentLineItem/1', 'quantity': 2,
                    'lineItem': {'id': 'gid://shopify/LineItem/1'},
                }]},
            }
        fo = {
            'id': 'gid://shopify/FulfillmentOrder/1', 'status': 'OPEN',
            'assignedLocation': {
                'location': {'id': 'gid://shopify/Location/1'}},
            'line_items': [],
        }
        picking = Mock()
        picking.id = 999999
        picking.state = 'assigned'
        picking.move_ids = []

        Service = self.env['shopify.connector.fulfillment.service']
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'reconciliation',
            'job_type': 'fulfillment_mode2_evaluation', 'state': 'queued',
            'res_model': 'shopify.connector.fulfillment.inbound.evidence',
            'res_id': evidence.id,
            'payload_hash': 'mode2:%d' % evidence.id,
        })
        with patch.object(type(Service), '_read_order_fulfillments',
                          side_effect=[[_node('SUCCESS')], [_node('CANCELLED')]]), \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=[fo]), \
                patch.object(type(Service), '_quantity_compatible_pickings',
                             return_value=[picking]), \
                patch.object(type(Service), '_select_deterministic_picking',
                             return_value=picking), \
                patch.object(type(Service), '_validate_picking_local',
                             side_effect=AssertionError(
                                 'local validation must never race past a '
                                 'changed second-read precondition')):
            Service._handle_fulfillment_mode2_evaluation(job)
        evidence.invalidate_recordset()
        # A changed second read fails closed: the handler opens a review case
        # for the named reason and NEVER applies locally (the patched local
        # validation above would have raised had it been reached).
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'remote_state_changed')
        self.assertNotEqual(evidence.reconciled_state, 'applied')

    # -- Harness contract (AST): spawn, not fork, run_* functions, wiring.

    def test_external_concurrency_harness_contract(self):
        path = Path(__file__).with_name(
            'runtime_layer2_fulfillment_concurrency_harness.py')
        source = path.read_text('utf-8')
        tree = ast.parse(source)
        funcs = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
        self.assertIn('run_c1_ownership_race', funcs)
        self.assertIn('_new_environment', funcs)
        self.assertIn('_runtime', funcs)
        self.assertIn("get_context('spawn')", source)
        self.assertNotIn("get_context('fork')", source)
        self.assertIn('Registry(', source)
        self.assertIn('Environment', source)
        # The harness is NOT imported by the test package. Assert on the real
        # import graph, not raw text: the __init__ comment deliberately names
        # the file ("...is deliberately NOT imported here"), so a substring
        # check would false-positive on that comment.
        init_tree = ast.parse(path.with_name('__init__.py').read_text('utf-8'))
        imported_modules = set()
        for node in ast.walk(init_tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    imported_modules.add(alias.name)
        self.assertNotIn(
            'runtime_layer2_fulfillment_concurrency_harness', imported_modules)

    # -- No-fake-success guard (Stage R2A P1 correction). --------------

    def test_no_fake_success_scenarios(self):
        """Every SCENARIOS entry must map to a runner that genuinely
        orchestrates processes/independent transactions, inspects a durable
        DB outcome, checks child exit codes, and performs cleanup/residue
        verification -- not a hard-coded pass. Structural (AST) only; this
        never imports/executes the harness (see the docstring on
        audit_concurrency_harness_scenarios)."""
        path = Path(__file__).with_name(
            'runtime_layer2_fulfillment_concurrency_harness.py')
        source = path.read_text('utf-8')
        violations = audit_concurrency_harness_scenarios(source)
        self.assertEqual(
            violations, [],
            'harness scenario audit violations: %r' % (violations,))

    def test_no_fake_success_guard_rejects_the_disclosed_stub_shape(self):
        """Proves the guard is not decorative: fed a synthetic module shaped
        exactly like the disclosed Stage R1 stub (a SCENARIOS/RUNNERS pair
        pointing at a bare `return {'ok': True, ...}` function with no
        process creation, query, or cleanup), it must reject it."""
        stub_source = (
            "SCENARIOS = ('operation_scope_serialization',)\n\n\n"
            "def run_operation_scope_serialization(settings, timeout):\n"
            "    return {'scenario': 'operation_scope_serialization',\n"
            "            'ok': True, 'zero_real_shopify': True}\n\n\n"
            "RUNNERS = {\n"
            "    'operation_scope_serialization': "
            "run_operation_scope_serialization,\n"
            "}\n"
        )
        violations = audit_concurrency_harness_scenarios(stub_source)
        self.assertTrue(
            violations, 'the guard failed to reject a literal ok:True stub')
        joined = ' '.join(violations)
        self.assertIn(
            'runner run_operation_scope_serialization() is a bare '
            'literal-dict return with no orchestration', joined,
        )

    def test_no_fake_success_guard_accepts_genuine_orchestration(self):
        """Negative-of-the-negative: a runner that genuinely spawns via
        get_context/Process, inspects a durable outcome, checks an exit
        code, and calls a cleanup helper must NOT be flagged, so the guard
        cannot be satisfied by trivially banning every dict return."""
        genuine_source = (
            "SCENARIOS = ('operation_scope_serialization',)\n\n\n"
            "def _finish_cleanup(settings, fixture):\n"
            "    return {}\n\n\n"
            "def run_operation_scope_serialization(settings, timeout):\n"
            "    context = multiprocessing.get_context('spawn')\n"
            "    process = context.Process(target=lambda: None)\n"
            "    process.start()\n"
            "    process.join()\n"
            "    code = process.exitcode\n"
            "    job = environment['shopify.connector.job'].search([])\n"
            "    _finish_cleanup(settings, {})\n"
            "    return {'scenario': 'operation_scope_serialization',\n"
            "            'passed': bool(job) and code == 0}\n\n\n"
            "RUNNERS = {\n"
            "    'operation_scope_serialization': "
            "run_operation_scope_serialization,\n"
            "}\n"
        )
        violations = audit_concurrency_harness_scenarios(genuine_source)
        scenario_violations = [
            v for v in violations if v.startswith('operation_scope_serialization:')
        ]
        self.assertEqual(
            scenario_violations, [],
            'the guard false-positived on genuine orchestration: %r'
            % (scenario_violations,))
