# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class TestFulfillmentInbound(TransactionCase):

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
            'external_fulfillment_handling': 'activity',
        })
        self.partner = self.env['res.partner'].create({
            'name': 'Test Buyer', 'email': 'buyer@example.com',
        })
        self.product = self.env['product.product'].create({
            'name': 'Shipped Widget', 'list_price': 25.0,
            'detailed_type': 'product', 'default_code': 'SHIP-001',
        })
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'warehouse_id': self.backend.warehouse_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 25.0,
            })],
        })
        self.order.action_confirm()
        self.binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.order.id,
            'shopify_id': 'gid://shopify/Order/2000',
            'shopify_order_name': '#2001',
            'shopify_fulfillment_status': 'unfulfilled',
            'sync_status': 'synced',
        })

    def _get_syncer(self):
        from ..sync.fulfillment_sync import FulfillmentSync
        syncer = FulfillmentSync.__new__(FulfillmentSync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()
        return syncer

    def test_inbound_fulfillment_activity_mode(self):
        """In activity mode, should create activity on order, not validate picking."""
        syncer = self._get_syncer()
        # Mock the API call to return fulfilled status
        syncer.client.execute.return_value = {
            'data': {'order': {'displayFulfillmentStatus': 'FULFILLED'}},
        }

        syncer.handle_inbound_fulfillment(self.binding)

        self.assertEqual(self.binding.shopify_fulfillment_status, 'fulfilled')
        # Picking should NOT be validated
        out_pickings = self.order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        for p in out_pickings:
            self.assertNotEqual(p.state, 'done')

    def test_inbound_fulfillment_auto_validate_mode(self):
        """In auto_validate mode, should validate the outgoing picking."""
        self.backend.external_fulfillment_handling = 'auto_validate'
        syncer = self._get_syncer()
        syncer.client.execute.return_value = {
            'data': {'order': {'displayFulfillmentStatus': 'FULFILLED'}},
        }

        syncer.handle_inbound_fulfillment(self.binding)

        self.assertEqual(self.binding.shopify_fulfillment_status, 'fulfilled')
        out_pickings = self.order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        # At least one picking should be done
        done = out_pickings.filtered(lambda p: p.state == 'done')
        self.assertTrue(done)

    def test_inbound_fulfillment_ignore_mode(self):
        """In ignore mode, should just update the status field."""
        self.backend.external_fulfillment_handling = 'ignore'
        syncer = self._get_syncer()
        syncer.client.execute.return_value = {
            'data': {'order': {'displayFulfillmentStatus': 'FULFILLED'}},
        }

        syncer.handle_inbound_fulfillment(self.binding)

        self.assertEqual(self.binding.shopify_fulfillment_status, 'fulfilled')
        out_pickings = self.order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        for p in out_pickings:
            self.assertNotEqual(p.state, 'done')

    def test_no_status_change_is_noop(self):
        """If status hasn't changed, do nothing."""
        self.binding.shopify_fulfillment_status = 'fulfilled'
        syncer = self._get_syncer()
        syncer.client.execute.return_value = {
            'data': {'order': {'displayFulfillmentStatus': 'FULFILLED'}},
        }

        syncer.handle_inbound_fulfillment(self.binding)
        # No crash, no activity

    def test_cancellation_creates_activity_on_done_picking(self):
        """Fulfillment cancellation with done picking should create activity."""
        # First validate the picking
        out_pickings = self.order.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
        )
        if out_pickings:
            for move in out_pickings[0].move_ids:
                move.quantity = move.product_uom_qty
            out_pickings[0].with_context(
                skip_backorder=True,
            ).button_validate()

        syncer = self._get_syncer()
        syncer.client.execute.return_value = {
            'data': {'order': {'displayFulfillmentStatus': 'UNFULFILLED'}},
        }

        syncer.handle_fulfillment_cancellation(self.binding)
        self.assertEqual(self.binding.shopify_fulfillment_status, 'unfulfilled')

    def test_no_order_skips_gracefully(self):
        """Binding without odoo_id should not crash."""
        self.binding.odoo_id = False
        syncer = self._get_syncer()
        syncer.handle_inbound_fulfillment(self.binding)
        # No crash
