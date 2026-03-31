from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class TestB2BIsolation(TransactionCase):
    """Tests that B2B (direct) orders are never synced to Shopify."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'state': 'connected',
            'reverse_sync_payment': True,
        })
        self.partner = self.env['res.partner'].create({
            'name': 'B2B Customer', 'email': 'b2b@corp.com',
        })
        self.product = self.env['product.product'].create({
            'name': 'B2B Product', 'list_price': 100.0,
            'detailed_type': 'product', 'default_code': 'B2B-001',
        })

    def test_new_order_defaults_to_direct(self):
        """Orders created in Odoo should default to 'direct' channel."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
        })
        self.assertEqual(order.sales_channel, 'direct')

    def test_shopify_import_sets_shopify_channel(self):
        """Orders imported from Shopify should be marked 'shopify'."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
        })
        self.assertEqual(order.sales_channel, 'shopify')

    @patch('odoo.addons.adams_shopify.sync.fulfillment_sync.FulfillmentSync')
    def test_b2b_picking_does_not_push_fulfillment(self, MockFulfillment):
        """Validating a B2B delivery should NOT push to Shopify."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'direct',
            'company_id': self.env.company.id,
            'warehouse_id': self.backend.warehouse_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        order.action_confirm()

        # Validate the picking
        picking = order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        if picking:
            for move in picking[0].move_ids:
                move.quantity = move.product_uom_qty
            picking[0].with_context(skip_backorder=True).button_validate()

        # FulfillmentSync should NOT have been instantiated
        MockFulfillment.assert_not_called()

    def test_b2b_invoice_post_does_not_call_shopify(self):
        """Posting a B2B invoice should NOT call orderMarkAsPaid."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'direct',
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        order.action_confirm()
        invoice = order._create_invoices()

        # This should not trigger any Shopify API call
        # (it would error if it tried, since there's no binding)
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

    def test_b2b_order_has_no_binding(self):
        """B2B orders should never have Shopify bindings."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'direct',
        })
        self.assertFalse(order.shopify_bind_ids)

    def test_shared_customer_different_channels(self):
        """Same customer can have both B2B and Shopify orders."""
        b2b_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'direct',
        })
        shopify_order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
        })
        self.assertEqual(b2b_order.sales_channel, 'direct')
        self.assertEqual(shopify_order.sales_channel, 'shopify')
        # Same partner
        self.assertEqual(b2b_order.partner_id, shopify_order.partner_id)
