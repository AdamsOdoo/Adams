import uuid
from unittest.mock import patch

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
            'sale_id': self.sale.id,
        })
        self.env['stock.move'].create({
            'name': 'm', 'product_id': self.product.id,
            'product_uom_qty': 2.0, 'product_uom': self.product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
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
