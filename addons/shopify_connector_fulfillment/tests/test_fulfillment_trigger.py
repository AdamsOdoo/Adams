import ast
import uuid
from pathlib import Path
from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestFulfillmentTrigger(TransactionCase):
    """D-014-3: stock.picking is the odoo_event trigger surface.

    `_is_fulfillment_admission_eligible()` is True only for the final
    customer-bound outgoing leg of an imported order (outgoing + customer
    destination + state 'done' + sale_id). `_action_done` enqueues a
    picking admission for an eligible validation; the `write()` seam enqueues
    a tracking admission when a tracking field changes on a bound picking; and
    the domain flag gates picking admission entirely.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'P1', 'type': 'consu',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'C'})
        cls.sale = cls.env['sale.order'].create({'partner_id': cls.partner.id})
        cls.order_binding = cls.env['shopify.connector.order.binding'].sudo().create({
            'store_id': cls.store.id, 'shopify_gid': 'gid://shopify/Order/900',
            'sale_order_id': cls.sale.id, 'status': 'active',
        })
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')
        cls.supplier_loc = cls.env.ref('stock.stock_location_suppliers')
        # Correction P1-3: an ordinary warehouse user with normal stock
        # permissions and NO Shopify connector group whatsoever.
        cls.stock_user = cls.env['res.users'].create({
            'name': 'FUL Stock User',
            'login': 'ful-stockuser-%s' % uuid.uuid4().hex,
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('stock.group_stock_user').id,
            ])],
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _picking_type(self, code):
        return self.env['stock.picking.type'].search(
            [('code', '=', code)], limit=1,
        )

    def _make_picking(self, code, source, dest, state='done'):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self._picking_type(code).id,
            'location_id': source.id,
            'location_dest_id': dest.id,
            'sale_id': self.sale.id,
        })
        if state:
            picking.write({'state': state})
        return picking

    def _deliverable_picking(self):
        picking = self.env['stock.picking'].create({
            'picking_type_id': self._picking_type('outgoing').id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
        })
        # In Odoo 19 stock.picking.sale_id is COMPUTED from
        # move_ids.sale_line_id.order_id (a direct sale_id write is overwritten
        # by the compute), so the delivery move must carry a real sale line for
        # the order to resolve and be admission-eligible.
        sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': self.product.id,
            'product_uom_qty': 2.0,
        })
        self.env['stock.move'].create({
            # Odoo 19 removed stock.move.name (computed `reference` instead).
            'product_id': self.product.id,
            'product_uom_qty': 2.0, 'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_line_id': sale_line.id,
        })
        return picking

    # ------------------------------------------------------------------
    # Eligibility predicate
    # ------------------------------------------------------------------

    def test_eligible_outgoing_customer_done_with_sale(self):
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.customer_loc, state='done',
        )
        self.assertTrue(picking._is_fulfillment_admission_eligible())

    def test_not_eligible_when_incoming(self):
        # Incoming leg: picking_type_code != 'outgoing'.
        picking = self._make_picking(
            'incoming', self.supplier_loc, self.stock_loc, state='done',
        )
        self.assertEqual(picking.picking_type_code, 'incoming')
        self.assertFalse(picking._is_fulfillment_admission_eligible())

    def test_not_eligible_when_internal_destination(self):
        # Outgoing type but the destination is not a customer location.
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.stock_loc, state='done',
        )
        self.assertEqual(picking.picking_type_code, 'outgoing')
        self.assertEqual(picking.location_dest_id.usage, 'internal')
        self.assertFalse(picking._is_fulfillment_admission_eligible())

    # ------------------------------------------------------------------
    # _action_done trigger
    # ------------------------------------------------------------------

    def test_action_done_enqueues_picking_admission_when_eligible(self):
        picking = self._deliverable_picking()
        picking.move_ids._action_confirm()
        picking.move_ids._action_assign()
        for line in picking.move_ids.move_line_ids:
            line.quantity = 2.0
            # Odoo 17+ only completes a move on validation when its lines are
            # marked picked; without it the picking stays 'assigned'.
            line.picked = True
        with patch.object(
            type(self.Service), '_enqueue_picking_admission',
        ) as mock_enqueue:
            picking._action_done()
        self.assertEqual(picking.state, 'done')
        self.assertTrue(picking._is_fulfillment_admission_eligible())
        mock_enqueue.assert_called_once()
        # The eligible picking itself is the argument.
        called_picking = mock_enqueue.call_args.args[0]
        self.assertEqual(called_picking, picking)

    # ------------------------------------------------------------------
    # write() tracking seam
    # ------------------------------------------------------------------

    def test_tracking_change_on_bound_picking_enqueues_tracking_admission(self):
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.customer_loc, state='done',
        )
        binding = self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/1',
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })
        with patch.object(
            type(self.Service), '_enqueue_tracking_admission',
        ) as mock_enqueue:
            picking.write({'carrier_tracking_ref': 'TN1'})
        mock_enqueue.assert_called_once()
        called_binding = mock_enqueue.call_args.args[0]
        self.assertEqual(called_binding, binding)

    def test_non_tracking_write_does_not_enqueue_tracking_admission(self):
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.customer_loc, state='done',
        )
        self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/2',
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })
        with patch.object(
            type(self.Service), '_enqueue_tracking_admission',
        ) as mock_enqueue:
            picking.write({'priority': '1'})
        mock_enqueue.assert_not_called()

    # ------------------------------------------------------------------
    # Domain-flag gating
    # ------------------------------------------------------------------

    def test_domain_disabled_enqueues_no_picking_admission(self):
        self.settings.write({'fulfillment_domain_enabled': False})
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.customer_loc, state='done',
        )
        before = self.env['shopify.connector.job'].search_count([
            ('job_type', '=', 'fulfillment_picking_admission'),
        ])
        result = self.Service._enqueue_picking_admission(picking)
        after = self.env['shopify.connector.job'].search_count([
            ('job_type', '=', 'fulfillment_picking_admission'),
        ])
        # An empty recordset is returned and no job row is created.
        self.assertFalse(result)
        self.assertEqual(after, before)

    # ------------------------------------------------------------------
    # Theme A — transaction safety around the two foreground hooks
    # ------------------------------------------------------------------

    def test_second_tracking_write_persists_while_first_job_non_terminal(self):
        # Two sequential tracking-admission writes on the same picking while
        # the first admission job remains non-terminal: the SECOND write's
        # own picking-field change must persist (never discarded by an
        # operation-scope collision poisoning the caller's transaction).
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.customer_loc, state='done',
        )
        self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/SEQ1',
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })
        picking.write({'carrier_tracking_ref': 'TN-FIRST'})
        first_jobs = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'fulfillment_tracking_admission'),
            ('res_model', '=', 'shopify.connector.fulfillment.binding'),
        ])
        self.assertTrue(first_jobs)
        self.assertNotIn(first_jobs[:1].state, ('succeeded', 'failed_final',
                                                  'skipped', 'cancelled'))
        # The second write changes the SAME tracking field to a different
        # value -- a different payload_hash, so it targets a genuinely new
        # operation-scope collision surface if one exists.
        picking.write({'carrier_tracking_ref': 'TN-SECOND'})
        picking.invalidate_recordset()
        # No exception was raised and the picking write is fully persisted --
        # the caller's own transaction was never poisoned by the admission
        # hook's internal enqueue attempt.
        self.assertEqual(picking.carrier_tracking_ref, 'TN-SECOND')

    def test_unexpected_action_done_hook_failure_rolls_back_atomically(self):
        # An unexpected (non-collision) enqueue-hook exception during
        # `_action_done` must propagate, rolling back the whole validation
        # transaction atomically -- never silently preserving the picking.
        picking = self._deliverable_picking()
        picking.move_ids._action_confirm()
        picking.move_ids._action_assign()
        for line in picking.move_ids.move_line_ids:
            line.quantity = 2.0
            line.picked = True
        with patch.object(
            type(self.Service), '_enqueue_picking_admission',
            side_effect=RuntimeError('unexpected admission failure'),
        ):
            with self.assertRaises(RuntimeError):
                picking._action_done()

    def test_unexpected_write_hook_failure_rolls_back_atomically(self):
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.customer_loc, state='done',
        )
        self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/UNEXPECTED-WRITE',
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })
        with patch.object(
            type(self.Service), '_enqueue_tracking_admission',
            side_effect=RuntimeError('unexpected tracking admission failure'),
        ):
            with self.assertRaises(RuntimeError):
                picking.write({'carrier_tracking_ref': 'TN-UNEXPECTED'})

    # ------------------------------------------------------------------
    # Correction P1-3 — an ordinary warehouse user with no connector role
    # ------------------------------------------------------------------

    def test_ordinary_stock_user_denied_direct_connector_model_access(self):
        # ACLs are unchanged: a plain stock user still cannot read connector
        # jobs, order bindings, or fulfillment bindings directly.
        with self.assertRaises(AccessError):
            self.env['shopify.connector.job'].with_user(
                self.stock_user).search([])
        with self.assertRaises(AccessError):
            self.env['shopify.connector.order.binding'].with_user(
                self.stock_user).search([])
        with self.assertRaises(AccessError):
            self.env['shopify.connector.fulfillment.binding'].with_user(
                self.stock_user).search([])

    def test_ordinary_stock_user_validates_delivery_enqueues_one_job(self):
        picking = self._deliverable_picking()
        picking.move_ids._action_confirm()
        picking.move_ids._action_assign()
        for line in picking.move_ids.move_line_ids:
            line.quantity = 2.0
            line.picked = True
        picking.with_user(self.stock_user)._action_done()
        self.assertEqual(picking.state, 'done')
        jobs = self.env['shopify.connector.job'].sudo().search([
            ('job_type', '=', 'fulfillment_picking_admission'),
            ('res_model', '=', 'stock.picking'), ('res_id', '=', picking.id),
        ])
        self.assertEqual(len(jobs), 1)
        # The real initiating actor is preserved -- the enqueue seam is
        # sudo'd for ACL bypass only, never for actor attribution.
        self.assertEqual(jobs.create_uid.id, self.stock_user.id)

    def test_ordinary_stock_user_tracking_write_enqueues_one_job(self):
        picking = self._make_picking(
            'outgoing', self.stock_loc, self.customer_loc, state='done',
        )
        binding = self.env['shopify.connector.fulfillment.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Fulfillment/STOCKUSER-1',
            'picking_id': picking.id,
            'order_binding_id': self.order_binding.id,
        })
        picking.with_user(self.stock_user).write({
            'carrier_tracking_ref': 'TN-STOCKUSER',
        })
        jobs = self.env['shopify.connector.job'].sudo().search([
            ('job_type', '=', 'fulfillment_tracking_admission'),
            ('res_model', '=', 'shopify.connector.fulfillment.binding'),
            ('res_id', '=', binding.id),
        ])
        self.assertEqual(len(jobs), 1)

    def test_ordinary_stock_user_unexpected_hook_failure_rolls_back(self):
        picking = self._deliverable_picking()
        picking.move_ids._action_confirm()
        picking.move_ids._action_assign()
        for line in picking.move_ids.move_line_ids:
            line.quantity = 2.0
            line.picked = True
        with patch.object(
            type(self.Service), '_enqueue_picking_admission',
            side_effect=RuntimeError('unexpected admission failure'),
        ):
            with self.assertRaises(RuntimeError):
                picking.with_user(self.stock_user)._action_done()

    def test_stock_picking_hooks_never_sudo_the_picking_itself(self):
        # `stock_picking.py` DOES sudo() the fulfillment-binding lookup (one
        # of the explicitly sanctioned technical-service seams -- "fulfilment
        # binding lookup"), since there is no admission.py delegation point
        # for that specific read. What it must NEVER do is sudo() the
        # picking recordset itself or its own business validation -- every
        # sudo() call's receiver must be a fresh `self.env[...]` model
        # lookup, never the bare `self`/`picking` name.
        path = (Path(__file__).resolve().parents[1] / 'models'
                / 'stock_picking.py')
        tree = ast.parse(path.read_text('utf-8'))
        violations = []
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'sudo'
            ):
                continue
            receiver = node.func.value
            if isinstance(receiver, ast.Name) and receiver.id in (
                'self', 'picking',
            ):
                violations.append(receiver.id)
        self.assertEqual(
            violations, [],
            'stock_picking.py must never call sudo() on the picking '
            'recordset itself or its own business validation (found sudo() '
            'on: %r)' % (violations,),
        )
