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
        self.assertEqual(evidence.reconciled_state, 'observed')
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
        # The harness is NOT imported by the test package.
        init_source = path.with_name('__init__.py').read_text('utf-8')
        self.assertNotIn(
            'runtime_layer2_fulfillment_concurrency_harness', init_source)
