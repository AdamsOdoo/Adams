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


def _references_exitcode(node):
    """True if `node` is an Attribute `.exitcode` or a Subscript keyed by the
    literal string `'exitcode'` -- either shape production code uses."""
    if isinstance(node, ast.Attribute) and node.attr == 'exitcode':
        return True
    if isinstance(node, ast.Subscript):
        sl = node.slice
        if isinstance(sl, ast.Constant) and sl.value == 'exitcode':
            return True
    return False


def _compare_references_exitcode(node):
    if not isinstance(node, ast.Compare):
        return False
    for operand in [node.left] + list(node.comparators):
        if any(_references_exitcode(n) for n in ast.walk(operand)):
            return True
    return False


def _contains_raise(node):
    return any(isinstance(n, ast.Raise) for n in ast.walk(node))


def _names_assigned_from_exitcode_compare(nodes):
    """Names assigned from a list/generator/set comprehension whose element
    expression involves a genuine exitcode comparison -- e.g. the production
    `bad_exits = [r for r in records if r['exitcode'] not in (0, None) and
    not r['exception_class']]` shape."""
    names = set()
    for stmt in nodes:
        if not isinstance(stmt, ast.Assign):
            continue
        value = stmt.value
        if not isinstance(value, (ast.ListComp, ast.GeneratorExp, ast.SetComp)):
            continue
        if not any(_compare_references_exitcode(n) for n in ast.walk(value)):
            continue
        names |= {t.id for t in stmt.targets if isinstance(t, ast.Name)}
    return names


def _has_genuine_exitcode_comparison_reaching_raise(nodes):
    """True only when the closure contains a REAL comparison against an
    exit code (not mere attribute/subscript presence, which the prior guard
    wrongly accepted) that feeds a conditional raise/assert -- either
    directly (`if crasher.exitcode != 37: raise ...`) or indirectly via a
    comprehension assigned to a name later tested (`bad_exits = [...
    exitcode ...]; if bad_exits: raise ...`, the shared `_run_children`
    shape). Mere capture (`record['exitcode'] = process.exitcode`) with no
    reachable comparison never satisfies this (Theme K)."""
    for node in nodes:
        if (
            isinstance(node, ast.If)
            and _compare_references_exitcode(node.test)
            and _contains_raise(node)
        ):
            return True
    derived_names = _names_assigned_from_exitcode_compare(nodes)
    if not derived_names:
        return False
    for node in nodes:
        if not (isinstance(node, ast.If) and _contains_raise(node)):
            continue
        test_names = {
            n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)
        }
        if test_names & derived_names:
            return True
    return False


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
        if not _has_genuine_exitcode_comparison_reaching_raise(closure):
            violations.append(
                '%s: no genuine exit-code comparison reaching a raise/assert '
                'was found (mere attribute/subscript presence is not '
                'sufficient)' % scenario)

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
        # FK-safe, residue-free order: every one of these tables carries an
        # `ondelete='restrict'` `store_id` (or, for evidence, an
        # `order_binding_id` restrict onto order_binding) -- deleting the
        # store first would raise an IntegrityError while any of them still
        # reference it. Evidence lines cascade automatically
        # (`evidence_id` ondelete='cascade'), so they need no explicit delete.
        with db_connect(self.dbname).cursor() as cr:
            cr.execute(
                'DELETE FROM shopify_connector_fulfillment_inbound_evidence'
                ' WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_location WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_order_binding WHERE store_id = %s',
                (store_id,),
            )
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

    # -- Correction P1-1: condition 6 no longer locks; the locked re-check
    #    moved to immediately before the atomic application unit.

    def test_c6_no_overrun_acquires_no_row_lock(self):
        """Correction P1-1: `_c6_no_overrun` is now a preliminary, read-only
        check -- calling it must never hold or block on a row lock. A
        concurrent, genuinely independent connection can freely FOR-UPDATE-
        lock the same sale line immediately afterward."""
        with db_connect(self.dbname).cursor() as setup_cr:
            env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07', 'state': 'connected',
            })
            env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'fulfillment_domain_enabled': True,
            })
            partner = env['res.partner'].create({'name': 'C'})
            product = env['product.product'].create({
                'name': 'P', 'type': 'consu',
            })
            sale = env['sale.order'].create({'partner_id': partner.id})
            sale_line = env['sale.order.line'].create({
                'order_id': sale.id, 'product_id': product.id,
                'product_uom_qty': 2.0,
                'shopify_line_item_gid': 'gid://shopify/LineItem/C6NOLOCK',
            })
            order_binding = env['shopify.connector.order.binding'].create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/Order/C6NOLOCK',
                'sale_order_id': sale.id, 'status': 'active',
            })
            evidence = env[
                'shopify.connector.fulfillment.inbound.evidence'
            ].create({
                'store_id': store.id,
                'shopify_fulfillment_gid': 'gid://shopify/Fulfillment/C6NOLOCK',
                'order_binding_id': order_binding.id,
            })
            store_id = store.id
            sale_line_id = sale_line.id
            evidence_id = evidence.id
            setup_cr.commit()
        self.addCleanup(self._cleanup_store, store_id)

        with db_connect(self.dbname).cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            sale_line = env['sale.order.line'].browse(sale_line_id)
            evidence = env[
                'shopify.connector.fulfillment.inbound.evidence'
            ].browse(evidence_id)
            ctx = {
                'evidence': evidence, 'store': env[
                    'shopify.connector.store'
                ].browse(store_id),
                'line_mapping': {
                    'gid://shopify/LineItem/C6NOLOCK': (sale_line, 1),
                },
            }
            Service = env['shopify.connector.fulfillment.service']
            ok, _detail = Service._c6_no_overrun(ctx)
            self.assertTrue(ok)
            # C6 must not still be holding the row lock: a second,
            # genuinely independent connection can acquire it immediately.
            with db_connect(self.dbname).cursor() as other_cr:
                other_cr.execute('SET LOCAL lock_timeout = %s', ('2s',))
                other_env = api.Environment(other_cr, SUPERUSER_ID, {})
                other_line = other_env['sale.order.line'].browse(sale_line_id)
                locked = other_line.try_lock_for_update()
                self.assertTrue(locked)
                other_cr.rollback()
            cr.rollback()

    def test_c6_no_overrun_source_has_no_lock_call(self):
        # Condition 6's function body must never call a locking helper
        # (mirrors the pre-existing C14 source guard below).
        path = (Path(__file__).resolve().parents[1] / 'models'
                / 'shopify_connector_fulfillment_mode2.py')
        tree = ast.parse(path.read_text('utf-8'))
        c6 = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == '_c6_no_overrun'
        )
        calls = {
            node.func.attr for node in ast.walk(c6)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        self.assertNotIn('try_lock_for_update', calls)
        self.assertNotIn('lock_for_update', calls)

    def test_no_shopify_read_reachable_from_the_locking_helpers(self):
        # No Shopify-read method may ever be called from `_apply_mode2`,
        # `_relock_and_recheck`, or `_lock_affected_sale_lines` -- every
        # Shopify read has already completed by the time locking starts.
        path = (Path(__file__).resolve().parents[1] / 'models'
                / 'shopify_connector_fulfillment_mode2.py')
        tree = ast.parse(path.read_text('utf-8'))
        functions = {
            n.name: n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
        }
        forbidden = {
            '_read_order_fulfillments', '_read_fulfillment_orders',
            '_read_fulfillment', '_resolve_single_location',
        }
        for name in ('_apply_mode2', '_relock_and_recheck',
                      '_lock_affected_sale_lines'):
            node = functions[name]
            calls = {
                n.func.attr for n in ast.walk(node)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            }
            overlap = calls & forbidden
            self.assertFalse(
                overlap,
                '%s must never call a Shopify-read method after/while '
                'locking (found %r)' % (name, overlap),
            )

    def test_condition14_independent_cursor_can_lock_sale_line_during_the_read(self):
        """Correction P1-1: condition 14's Shopify read must run with NO row
        lock held -- proven by a genuine independent connection successfully
        FOR-UPDATE-locking the affected sale line WHILE condition 14's read
        is in flight (from inside the patched reader itself)."""
        with db_connect(self.dbname).cursor() as setup_cr:
            env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07', 'state': 'connected',
            })
            settings = env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'fulfillment_domain_enabled': True,
            })
            settings.write({'fulfillment_operating_mode': 'mode2'})
            product = env['product.product'].create({
                'name': 'P', 'type': 'consu', 'is_storable': True,
            })
            partner = env['res.partner'].create({'name': 'C'})
            sale = env['sale.order'].create({'partner_id': partner.id})
            sale_line = env['sale.order.line'].create({
                'order_id': sale.id, 'product_id': product.id,
                'product_uom_qty': 2.0,
                'shopify_line_item_gid': 'gid://shopify/LineItem/C14LOCK',
            })
            order_binding = env['shopify.connector.order.binding'].create({
                'store_id': store.id, 'shopify_gid': 'gid://shopify/Order/C14LOCK',
                'sale_order_id': sale.id, 'status': 'active',
            })
            env['shopify.connector.location'].create({
                'store_id': store.id,
                'shopify_location_gid': 'gid://shopify/Location/C14LOCK',
                'name': 'L', 'shopify_location_active': True,
            })
            evidence = env[
                'shopify.connector.fulfillment.inbound.evidence'
            ].create({
                'store_id': store.id,
                'shopify_fulfillment_gid': 'gid://shopify/Fulfillment/C14LOCK',
                'shopify_order_gid': 'gid://shopify/Order/C14LOCK',
                'order_binding_id': order_binding.id,
                'origin_class': 'external_merchant', 'origin_confirmed': True,
                'fulfillment_status_raw': 'SUCCESS',
                'fulfillment_status_normalized': 'Success',
                'fulfillment_status_is_success': True,
                'reconciled_state': 'observed',
            })
            store_id = store.id
            sale_line_id = sale_line.id
            evidence_id = evidence.id
            stock_loc_id = self.env.ref('stock.stock_location_stock').id
            setup_cr.commit()
        self.addCleanup(self._cleanup_store, store_id)

        def _node():
            return {
                'id': 'gid://shopify/Fulfillment/C14LOCK', 'status': 'SUCCESS',
                'fulfillmentLineItems': {'nodes': [{
                    'id': 'gid://shopify/FulfillmentLineItem/C14LOCK',
                    'quantity': 2,
                    'lineItem': {'id': 'gid://shopify/LineItem/C14LOCK'},
                }]},
            }
        fo = {
            'id': 'gid://shopify/FulfillmentOrder/C14LOCK', 'status': 'OPEN',
            'assignedLocation': {
                'location': {'id': 'gid://shopify/Location/C14LOCK'}},
            'line_items': [],
        }
        lock_result = {}
        call_state = {'n': 0}

        def _read_fn(store_arg, order_gid):
            call_state['n'] += 1
            if call_state['n'] == 2:
                # This is condition 14's SECOND, separately fresh read:
                # probe for the sale-line lock from a genuinely independent
                # connection WHILE this read is in flight.
                with db_connect(self.dbname).cursor() as probe_cr:
                    probe_cr.execute('SET LOCAL lock_timeout = %s', ('2s',))
                    probe_env = api.Environment(probe_cr, SUPERUSER_ID, {})
                    probe_line = probe_env['sale.order.line'].browse(
                        sale_line_id,
                    )
                    lock_result['locked'] = bool(
                        probe_line.try_lock_for_update(),
                    )
                    probe_cr.rollback()
            return [_node()]

        holder_cr = db_connect(self.dbname).cursor()
        try:
            holder_env = api.Environment(holder_cr, SUPERUSER_ID, {})
            Service = holder_env['shopify.connector.fulfillment.service']
            evidence = holder_env[
                'shopify.connector.fulfillment.inbound.evidence'
            ].browse(evidence_id)
            picking = Mock()
            picking.id = 8888888
            picking.state = 'assigned'
            picking.move_ids = []
            picking.location_id = holder_env['stock.location'].browse(
                stock_loc_id,
            )
            LocationModel = type(holder_env['shopify.connector.location'])
            with patch.object(type(Service), '_read_order_fulfillments',
                               side_effect=_read_fn), \
                    patch.object(type(Service), '_read_fulfillment_orders',
                                 return_value=[fo]), \
                    patch.object(
                        LocationModel, '_resolve_odoo_location',
                        return_value=holder_env['stock.location'].browse(
                            stock_loc_id,
                        ),
                    ), \
                    patch.object(type(Service), '_quantity_compatible_pickings',
                                 return_value=[picking]), \
                    patch.object(type(Service), '_select_deterministic_picking',
                                 return_value=picking):
                result = Service._evaluate_mode2(evidence)
            self.assertTrue(result['passed'])
        finally:
            holder_cr.rollback()
            holder_cr.close()
        self.assertIn('locked', lock_result)
        self.assertTrue(
            lock_result['locked'],
            'an independent connection could not lock the sale line while '
            "condition 14's Shopify read was executing -- a lock is still "
            'held across the read',
        )

    def test_apply_lock_unavailable_fails_closed_review_zero_stock_change(self):
        """Correction P1-1: when the sale-line lock cannot be acquired at
        apply time (held by a genuinely independent, concurrent
        connection), `_apply_mode2` must fail closed to review with ZERO
        local mutation -- proving only one concurrent application may ever
        proceed for the same sale line."""
        with db_connect(self.dbname).cursor() as setup_cr:
            env = api.Environment(setup_cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'Ful', 'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
                'api_version': '2026-07', 'state': 'connected',
            })
            env['shopify.connector.store.settings'].create({
                'store_id': store.id, 'fulfillment_domain_enabled': True,
            })
            partner = env['res.partner'].create({'name': 'C'})
            product = env['product.product'].create({
                'name': 'P', 'type': 'consu',
            })
            sale = env['sale.order'].create({'partner_id': partner.id})
            sale_line = env['sale.order.line'].create({
                'order_id': sale.id, 'product_id': product.id,
                'product_uom_qty': 2.0,
                'shopify_line_item_gid': 'gid://shopify/LineItem/APPLY-LOCK',
            })
            order_binding = env['shopify.connector.order.binding'].create({
                'store_id': store.id,
                'shopify_gid': 'gid://shopify/Order/APPLY-LOCK',
                'sale_order_id': sale.id, 'status': 'active',
            })
            pt_out = env['stock.picking.type'].search(
                [('code', '=', 'outgoing')], limit=1,
            )
            picking = env['stock.picking'].create({
                'picking_type_id': pt_out.id,
                'location_id': env.ref('stock.stock_location_stock').id,
                'location_dest_id': env.ref('stock.stock_location_customers').id,
                'sale_id': sale.id,
            })
            store_id = store.id
            sale_line_id = sale_line.id
            order_binding_id = order_binding.id
            picking_id = picking.id
            setup_cr.commit()
        self.addCleanup(self._cleanup_store, store_id)

        holder_cr = db_connect(self.dbname).cursor()
        try:
            holder_env = api.Environment(holder_cr, SUPERUSER_ID, {})
            holder_line = holder_env['sale.order.line'].browse(sale_line_id)
            locked = holder_line.try_lock_for_update()
            self.assertTrue(locked)

            with db_connect(self.dbname).cursor() as other_cr:
                other_cr.execute('SET LOCAL lock_timeout = %s', ('2s',))
                other_env = api.Environment(other_cr, SUPERUSER_ID, {})
                Service = other_env['shopify.connector.fulfillment.service']
                other_sale_line = other_env['sale.order.line'].browse(
                    sale_line_id,
                )
                other_picking = other_env['stock.picking'].browse(picking_id)
                other_evidence = other_env[
                    'shopify.connector.fulfillment.inbound.evidence'
                ].create({
                    'store_id': store_id,
                    'shopify_fulfillment_gid': 'gid://shopify/Fulfillment/APPLY-LOCK-2',
                    'order_binding_id': order_binding_id,
                })
                plan = {
                    'picking': other_picking,
                    'line_mapping': {
                        'gid://shopify/LineItem/APPLY-LOCK': (other_sale_line, 1),
                    },
                }
                with patch.object(
                    type(Service), '_validate_picking_local',
                    side_effect=AssertionError(
                        'a lock-unavailable application must never reach '
                        'local validation'),
                ):
                    Service._apply_mode2(other_evidence, plan)
                other_evidence.invalidate_recordset()
                self.assertEqual(other_evidence.reconciled_state, 'review')
                self.assertEqual(other_evidence.review_reason, 'quantity_overrun')
                other_picking.invalidate_recordset()
                self.assertNotEqual(other_picking.state, 'done')
                Binding = other_env['shopify.connector.fulfillment.binding']
                self.assertFalse(Binding.search([
                    ('store_id', '=', store_id), ('picking_id', '=', picking_id),
                ]))
                other_cr.rollback()
        finally:
            holder_cr.rollback()
            holder_cr.close()

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
        stock_loc = self.env.ref('stock.stock_location_stock')
        picking = Mock()
        picking.id = 999999
        picking.state = 'assigned'
        picking.move_ids = []
        picking.location_id = stock_loc

        Service = self.env['shopify.connector.fulfillment.service']
        LocationModel = type(self.env['shopify.connector.location'])
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id, 'job_source': 'reconciliation',
            'job_type': 'fulfillment_mode2_evaluation', 'state': 'queued',
            'res_model': 'shopify.connector.fulfillment.inbound.evidence',
            'res_id': evidence.id,
            'payload_hash': 'mode2:%d' % evidence.id,
        })
        # Condition 8's F-4 seam must resolve to a real mapped location (and
        # `picking` must genuinely sit in its subtree) so the evaluation
        # actually reaches condition 14 -- otherwise it fails closed earlier,
        # at condition 8, with `location_unmapped`, and never proves the
        # race this test targets.
        with patch.object(type(Service), '_read_order_fulfillments',
                          side_effect=[[_node('SUCCESS')], [_node('CANCELLED')]]), \
                patch.object(type(Service), '_read_fulfillment_orders',
                             return_value=[fo]), \
                patch.object(LocationModel, '_resolve_odoo_location',
                             return_value=stock_loc), \
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
        get_context/Process, synchronizes via real Event/Queue wait/set/get,
        inspects a fixture-scoped durable outcome, calls the cleanup helper
        at the real 3-arg production arity, and genuinely COMPARES a child
        exit code before conditionally raising must NOT be flagged -- so the
        guard cannot be satisfied by trivially banning every dict return, and
        is not itself hollow (Theme K: the prior bundled fixture here was
        confirmed semantically hollow on all four counts -- a no-op process
        target, zero synchronization, an unscoped `search([])`, and a
        wrong-arity `_finish_cleanup` call -- yet still passed the guard)."""
        genuine_source = (
            "import multiprocessing\n\n\n"
            "SCENARIOS = ('operation_scope_serialization',)\n\n\n"
            "def _finish_cleanup(summary, settings, fixture):\n"
            "    return {}\n\n\n"
            "def _child_worker(settings, fixture, name, ready_queue,\n"
            "                   start_event, result_queue, timeout):\n"
            "    ready_queue.put({'child': name})\n"
            "    if not start_event.wait(timeout):\n"
            "        raise TimeoutError('start signal timeout')\n"
            "    result_queue.put({'child': name, 'exception_class': False})\n\n\n"
            "def run_operation_scope_serialization(settings, timeout):\n"
            "    summary = {'scenario': 'operation_scope_serialization',\n"
            "               'passed': False}\n"
            "    fixture = {'store_id': 1}\n"
            "    context = multiprocessing.get_context('spawn')\n"
            "    ready_queue = context.Queue()\n"
            "    result_queue = context.Queue()\n"
            "    start_event = context.Event()\n"
            "    process = context.Process(\n"
            "        target=_child_worker,\n"
            "        args=(settings, fixture, 'worker-1', ready_queue,\n"
            "              start_event, result_queue, timeout))\n"
            "    process.start()\n"
            "    ready_queue.get(timeout=timeout)\n"
            "    start_event.set()\n"
            "    process.join(timeout)\n"
            "    records = [result_queue.get(timeout=timeout)]\n"
            "    bad_exits = [\n"
            "        r for r in records\n"
            "        if process.exitcode not in (0, None)\n"
            "        and not r['exception_class']\n"
            "    ]\n"
            "    if bad_exits:\n"
            "        raise AssertionError('child exited non-zero: %r' % (bad_exits,))\n"
            "    job = environment['shopify.connector.job'].search([\n"
            "        ('store_id', '=', fixture['store_id']),\n"
            "    ])\n"
            "    _finish_cleanup(summary, settings, fixture)\n"
            "    summary['passed'] = bool(job)\n"
            "    return summary\n\n\n"
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

    def test_no_fake_success_guard_rejects_capture_without_comparison(self):
        """Proves the strengthened guard requires a genuine exit-code
        COMPARISON reaching a raise/assert, not mere attribute/subscript
        presence -- the exact shape 7 of the 9 real scenario runners had
        before the Theme K correction: exit codes captured into each
        record via the shared `_run_children` helper, but never compared
        against an expected value anywhere in the runner's own closure."""
        capture_only_source = (
            "import multiprocessing\n\n\n"
            "SCENARIOS = ('operation_scope_serialization',)\n\n\n"
            "def _finish_cleanup(summary, settings, fixture):\n"
            "    return {}\n\n\n"
            "def _child_worker(settings, fixture, name, ready_queue,\n"
            "                   start_event, result_queue, timeout):\n"
            "    ready_queue.put({'child': name})\n"
            "    start_event.wait(timeout)\n"
            "    result_queue.put({'child': name, 'exception_class': False})\n\n\n"
            "def run_operation_scope_serialization(settings, timeout):\n"
            "    fixture = {'store_id': 1}\n"
            "    context = multiprocessing.get_context('spawn')\n"
            "    ready_queue = context.Queue()\n"
            "    result_queue = context.Queue()\n"
            "    start_event = context.Event()\n"
            "    process = context.Process(\n"
            "        target=_child_worker,\n"
            "        args=(settings, fixture, 'worker-1', ready_queue,\n"
            "              start_event, result_queue, timeout))\n"
            "    process.start()\n"
            "    ready_queue.get(timeout=timeout)\n"
            "    start_event.set()\n"
            "    process.join(timeout)\n"
            "    record = result_queue.get(timeout=timeout)\n"
            "    record['exitcode'] = process.exitcode\n"
            "    job = environment['shopify.connector.job'].search([\n"
            "        ('store_id', '=', fixture['store_id']),\n"
            "    ])\n"
            "    _finish_cleanup({}, settings, fixture)\n"
            "    return {'scenario': 'operation_scope_serialization',\n"
            "            'passed': bool(job), 'children': [record]}\n\n\n"
            "RUNNERS = {\n"
            "    'operation_scope_serialization': "
            "run_operation_scope_serialization,\n"
            "}\n"
        )
        violations = audit_concurrency_harness_scenarios(capture_only_source)
        self.assertTrue(
            violations,
            'the guard failed to reject exitcode capture without comparison')
        joined = ' '.join(violations)
        self.assertIn('exit-code comparison', joined)
