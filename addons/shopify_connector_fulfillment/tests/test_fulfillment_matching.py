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
                # Odoo 19 removed stock.move.name; the move description is the
                # computed `reference`. Do not pass `name`.
                'product_id': self.product.id,
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

    # ------------------------------------------------------------------
    # Theme C — aggregation across multiple move lines resolving to the
    # SAME FulfillmentOrder line (e.g. a lot/serial-split shipment), and
    # UoM conversion before comparison.
    # ------------------------------------------------------------------

    def _picking_two_lines_same_shopify_item(self, qty_a, qty_b):
        """Two DONE move lines (a lot/serial-split shipment pattern) both
        resolving to the SAME Shopify order line-item GID -- built as two
        separate stock.move/move.line pairs sharing one sale_line."""
        sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': self.product.id,
            'product_uom_qty': qty_a + qty_b,
            'shopify_line_item_gid': 'gid://shopify/LineItem/AGG',
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing')], limit=1,
            ).id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_id': self.sale.id,
        })
        for qty in (qty_a, qty_b):
            move = self.env['stock.move'].create({
                'product_id': self.product.id,
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

    def test_split_lines_each_individually_compliant_but_jointly_exceed(self):
        # Each move line (3, and 3) individually stays under a
        # remainingQuantity of 5, but their AGGREGATE (6) exceeds it -- must
        # be rejected, never split into two payload entries that each pass.
        picking = self._picking_two_lines_same_shopify_item(3.0, 3.0)
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 5,
              'gid://shopify/LineItem/AGG')],
        )]
        with self.assertRaises(FulfillmentReadError) as cm:
            self.Service._match_picking_to_fo_lines(picking, fos)
        self.assertEqual(cm.exception.error_class, 'ambiguous_match')

    def test_split_lines_jointly_equal_to_remaining_are_accepted(self):
        picking = self._picking_two_lines_same_shopify_item(2.0, 3.0)
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 5,
              'gid://shopify/LineItem/AGG')],
        )]
        line_inputs, diagnostics = self.Service._match_picking_to_fo_lines(
            picking, fos,
        )
        # Exactly ONE payload entry for the FO line -- the aggregate, never
        # two separate entries for the same fo_line_id.
        entries = line_inputs['gid://shopify/FulfillmentOrder/1']
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0], {
            'id': 'gid://shopify/FulfillmentOrderLineItem/1', 'quantity': 5,
        })
        self.assertEqual(diagnostics['matched_lines'], 2)

    def test_split_lines_lower_than_remaining_individually_and_jointly(self):
        picking = self._picking_two_lines_same_shopify_item(1.0, 1.0)
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 5,
              'gid://shopify/LineItem/AGG')],
        )]
        line_inputs, _diag = self.Service._match_picking_to_fo_lines(
            picking, fos,
        )
        self.assertEqual(
            line_inputs['gid://shopify/FulfillmentOrder/1'],
            [{'id': 'gid://shopify/FulfillmentOrderLineItem/1', 'quantity': 2}],
        )

    def test_same_product_different_uom_converts_before_comparison(self):
        # The move line ships in a different UoM than the sale line's own
        # UoM (e.g. a "Dozen"-tracked sale line fulfilled via a move in the
        # base "Units" UoM); the compared/aggregated quantity must be
        # UoM-converted to the sale line's own unit, never the raw move
        # quantity compared directly against Shopify's remainingQuantity.
        uom_unit = self.env.ref('uom.product_uom_unit')
        uom_dozen = self.env.ref('uom.product_uom_dozen')
        sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': self.product.id,
            'product_uom_qty': 1.0, 'product_uom': uom_dozen.id,
            'shopify_line_item_gid': 'gid://shopify/LineItem/UOM',
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing')], limit=1,
            ).id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_id': self.sale.id,
        })
        # 12 base units == 1 dozen.
        move = self.env['stock.move'].create({
            'product_id': self.product.id,
            'product_uom_qty': 12.0, 'product_uom': uom_unit.id,
            'picking_id': picking.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_line_id': sale_line.id,
        })
        self.env['stock.move.line'].create({
            'move_id': move.id, 'product_id': self.product.id,
            'quantity': 12.0, 'product_uom_id': uom_unit.id,
            'picking_id': picking.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
        })
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 1,
              'gid://shopify/LineItem/UOM')],
        )]
        line_inputs, _diag = self.Service._match_picking_to_fo_lines(
            picking, fos,
        )
        # Converted to the sale line's own UoM (dozen): 12 units -> 1 dozen,
        # matching the remainingQuantity of 1 -- never rejected as 12 > 1.
        self.assertEqual(
            line_inputs['gid://shopify/FulfillmentOrder/1'],
            [{'id': 'gid://shopify/FulfillmentOrderLineItem/1', 'quantity': 1}],
        )

    def test_lot_serial_split_lines_aggregate_into_one_payload_entry(self):
        # Two lot-tracked move lines (distinct lots) on the SAME move,
        # resolving to the same FO line, must still aggregate to one entry.
        tracked_product = self.env['product.product'].create({
            'name': 'Tracked', 'type': 'consu', 'is_storable': True,
            'tracking': 'lot',
        })
        sale_line = self.env['sale.order.line'].create({
            'order_id': self.sale.id, 'product_id': tracked_product.id,
            'product_uom_qty': 3.0,
            'shopify_line_item_gid': 'gid://shopify/LineItem/LOT',
        })
        picking = self.env['stock.picking'].create({
            'picking_type_id': self.env['stock.picking.type'].search(
                [('code', '=', 'outgoing')], limit=1,
            ).id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_id': self.sale.id,
        })
        move = self.env['stock.move'].create({
            'product_id': tracked_product.id,
            'product_uom_qty': 3.0, 'product_uom': tracked_product.uom_id.id,
            'picking_id': picking.id,
            'location_id': self.stock_loc.id,
            'location_dest_id': self.customer_loc.id,
            'sale_line_id': sale_line.id,
        })
        lot_a = self.env['stock.lot'].create({
            'name': 'LOT-A', 'product_id': tracked_product.id,
        })
        lot_b = self.env['stock.lot'].create({
            'name': 'LOT-B', 'product_id': tracked_product.id,
        })
        for lot, qty in ((lot_a, 1.0), (lot_b, 2.0)):
            self.env['stock.move.line'].create({
                'move_id': move.id, 'product_id': tracked_product.id,
                'quantity': qty, 'lot_id': lot.id,
                'picking_id': picking.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
            })
        fos = [self._fo(
            'gid://shopify/FulfillmentOrder/1',
            [('gid://shopify/FulfillmentOrderLineItem/1', 3,
              'gid://shopify/LineItem/LOT')],
        )]
        line_inputs, diagnostics = self.Service._match_picking_to_fo_lines(
            picking, fos,
        )
        self.assertEqual(
            line_inputs['gid://shopify/FulfillmentOrder/1'],
            [{'id': 'gid://shopify/FulfillmentOrderLineItem/1', 'quantity': 3}],
        )
        self.assertEqual(diagnostics['matched_lines'], 2)

    def test_two_hop_resolution_unaffected_by_aggregation_fix(self):
        # Regression: the existing 2-hop reverse-index build and its
        # single-line happy path are unchanged by the aggregation fix.
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
