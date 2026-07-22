import uuid

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (
    FulfillmentReadError,
)


class TestFulfillmentMatching(TransactionCase):
    """RA-023 explicit 2-hop matching: order LineItem GID -> FO-line
    lineItem.id -> FO-line id, capping the sent quantity at the FO line's
    remainingQuantity. Never fulfils by guess -- an unresolved line is
    `mapping_missing`, an over-remaining or many-to-one line is
    `ambiguous_match`. Null-GID FO lines are skipped, and the result is keyed
    by FulfillmentOrder GID.
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
        cls.product = cls.env['product.product'].create({
            'name': 'P1', 'type': 'consu',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'C'})
        cls.sale = cls.env['sale.order'].create({'partner_id': cls.partner.id})
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _picking(self, line_specs):
        """Build an outbound picking with one shipped move line per spec.

        `line_specs` is a list of (shopify_line_item_gid, quantity); a gid of
        False builds a shipped line carrying no Shopify line-item GID.
        """
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing')], limit=1,
            ).id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_id': self.sale.id,
        })
        for gid, qty in line_specs:
            sale_line = self.env['sale.order.line'].create({
                'order_id': self.sale.id, 'product_id': self.product.id,
                'product_uom_qty': qty, 'shopify_line_item_gid': gid,
            })
            move = self.env['stock.move'].create({
                'name': 'm', 'product_id': self.product.id,
                'product_uom_qty': qty, 'product_uom': self.product.uom_id.id,
                'picking_id': picking.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
                'sale_line_id': sale_line.id,
            })
            self.env['stock.move.line'].create({
                'move_id': move.id, 'product_id': self.product.id,
                'quantity': qty, 'picking_id': picking.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
            })
        return picking

    @staticmethod
    def _fo(fo_id, line_specs):
        """`line_specs` is a list of (fo_line_id, remaining, order_line_gid)."""
        return {
            'id': fo_id,
            'line_items': [
                {'id': fid, 'remainingQuantity': rem, 'lineItem': {'id': li}}
                for (fid, rem, li) in line_specs
            ],
        }

    # ------------------------------------------------------------------
    # Happy path (2-hop + keyed result)
    # ------------------------------------------------------------------

    def test_two_hop_match_returns_line_inputs_keyed_by_fo_gid(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 2,
              'gid://shopify/LineItem/111')],
        )]
        line_inputs, diagnostics = self.Service._match_picking_to_fo_lines(
            picking, fos,
        )
        self.assertEqual(line_inputs, {
            'gid://shopify/FulfillmentOrder/1': [
                {'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                 'quantity': 2},
            ],
        })
        self.assertEqual(diagnostics['matched_lines'], 1)

    def test_quantity_at_remaining_is_accepted(self):
        # Shipped quantity equal to remainingQuantity is fulfillable.
        picking = self._picking([('gid://shopify/LineItem/111', 3.0)])
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 3,
              'gid://shopify/LineItem/111')],
        )]
        line_inputs, _diag = self.Service._match_picking_to_fo_lines(
            picking, fos,
        )
        self.assertEqual(
            line_inputs['gid://shopify/FulfillmentOrder/1'][0]['quantity'], 3,
        )

    # ------------------------------------------------------------------
    # Null-GID FO lines are skipped
    # ------------------------------------------------------------------

    def test_null_gid_fo_lines_are_skipped(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [
                # Null lineItem GID: cannot be matched, must be skipped (not
                # treated as ambiguous against the real matching line).
                ('gid://shopify/FulfillmentOrderLineItem/9', 2, None),
                ('gid://shopify/FulfillmentOrderLineItem/1', 2,
                 'gid://shopify/LineItem/111'),
            ],
        )]
        line_inputs, _diag = self.Service._match_picking_to_fo_lines(
            picking, fos,
        )
        self.assertEqual(line_inputs, {
            'gid://shopify/FulfillmentOrder/1': [
                {'id': 'gid://shopify/FulfillmentOrderLineItem/1',
                 'quantity': 2},
            ],
        })

    # ------------------------------------------------------------------
    # Fail-closed cases
    # ------------------------------------------------------------------

    def test_quantity_over_remaining_raises_ambiguous_match(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 1,
              'gid://shopify/LineItem/111')],
        )]
        with self.assertRaises(FulfillmentReadError) as cm:
            self.Service._match_picking_to_fo_lines(picking, fos)
        self.assertEqual(cm.exception.error_class, 'ambiguous_match')

    def test_move_line_without_gid_raises_mapping_missing(self):
        picking = self._picking([(False, 2.0)])
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 2,
              'gid://shopify/LineItem/111')],
        )]
        with self.assertRaises(FulfillmentReadError) as cm:
            self.Service._match_picking_to_fo_lines(picking, fos)
        self.assertEqual(cm.exception.error_class, 'mapping_missing')

    def test_line_matching_more_than_one_fo_line_raises_ambiguous_match(self):
        picking = self._picking([('gid://shopify/LineItem/111', 2.0)])
        fos = [
            self._fo(
                'gid://shopify/FulfillmentOrder/1',
                [('gid://shopify/FulfillmentOrderLineItem/1', 2,
                  'gid://shopify/LineItem/111')],
            ),
            self._fo(
                'gid://shopify/FulfillmentOrder/2',
                [('gid://shopify/FulfillmentOrderLineItem/2', 2,
                  'gid://shopify/LineItem/111')],
            ),
        ]
        with self.assertRaises(FulfillmentReadError) as cm:
            self.Service._match_picking_to_fo_lines(picking, fos)
        self.assertEqual(cm.exception.error_class, 'ambiguous_match')
