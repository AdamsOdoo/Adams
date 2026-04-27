# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Tests for fulfillment-related handlers.

Covers:
- GetFulfillmentOrders query
- GetOrderFulfillments query (full data)
- fulfillmentCreate mutation (success, partial, already fulfilled)
- Fulfillment status updates on orders
- FulfillmentOrder auto-creation
"""
from .common import SimulatorTestCase


class TestFulfillmentOrderAutoCreate(SimulatorTestCase):
    """Test that fulfillment orders are auto-created with orders."""

    def test_fulfillment_orders_created_for_order_with_lines(self):
        """Seeding an order with lines auto-creates fulfillment orders."""
        product = self._seed_product(title='FO Test Product')
        variant = product.variant_ids[0]
        order = self._seed_order(
            name='#FO-1001',
            lines=[{
                'title': 'FO Test Product',
                'quantity': 3,
                'variant_gid': variant.shopify_gid,
                'sku': variant.sku,
                'unit_price': 25.0,
            }],
        )
        fo_records = self.env['sim.shopify.fulfillment.order'].search([
            ('order_id', '=', order.id),
        ])
        self.assertEqual(len(fo_records), 1)
        self.assertEqual(fo_records.status, 'OPEN')
        self.assertEqual(len(fo_records.line_item_ids), 1)
        fo_line = fo_records.line_item_ids
        self.assertEqual(fo_line.remaining_quantity, 3)
        self.assertEqual(fo_line.total_quantity, 3)
        self.assertEqual(fo_line.variant_gid, variant.shopify_gid)

    def test_no_fulfillment_orders_for_order_without_lines(self):
        """Orders without lines do not get fulfillment orders."""
        order = self._seed_order(name='#FO-1002')
        fo_records = self.env['sim.shopify.fulfillment.order'].search([
            ('order_id', '=', order.id),
        ])
        self.assertEqual(len(fo_records), 0)

    def test_no_duplicate_fulfillment_orders(self):
        """Calling action_create_fulfillment_orders twice doesn't duplicate."""
        product = self._seed_product(title='Dup FO Test')
        variant = product.variant_ids[0]
        order = self._seed_order(
            name='#FO-1003',
            lines=[{
                'title': 'Dup FO Test',
                'quantity': 1,
                'variant_gid': variant.shopify_gid,
            }],
        )
        # Call again explicitly
        order.action_create_fulfillment_orders()
        fo_records = self.env['sim.shopify.fulfillment.order'].search([
            ('order_id', '=', order.id),
        ])
        self.assertEqual(len(fo_records), 1)

    def test_multiple_lines_single_fulfillment_order(self):
        """Multiple order lines create one FO with multiple FO lines."""
        p1 = self._seed_product(title='Multi Line A')
        p2 = self._seed_product(title='Multi Line B')
        order = self._seed_order(
            name='#FO-1004',
            lines=[
                {
                    'title': 'Multi Line A',
                    'quantity': 2,
                    'variant_gid': p1.variant_ids[0].shopify_gid,
                    'sku': 'MLA',
                },
                {
                    'title': 'Multi Line B',
                    'quantity': 5,
                    'variant_gid': p2.variant_ids[0].shopify_gid,
                    'sku': 'MLB',
                },
            ],
        )
        fo = self.env['sim.shopify.fulfillment.order'].search([
            ('order_id', '=', order.id),
        ])
        self.assertEqual(len(fo), 1)
        self.assertEqual(len(fo.line_item_ids), 2)
        qtys = sorted(fo.line_item_ids.mapped('remaining_quantity'))
        self.assertEqual(qtys, [2, 5])


class TestGetFulfillmentOrders(SimulatorTestCase):
    """Test the GetFulfillmentOrders query handler."""

    def _make_order_with_fo(self):
        product = self._seed_product(title='FO Query Product')
        variant = product.variant_ids[0]
        order = self._seed_order(
            name='#FOQ-1001',
            lines=[{
                'title': 'FO Query Product',
                'quantity': 4,
                'variant_gid': variant.shopify_gid,
                'sku': 'FOQ-SKU',
                'unit_price': 10.0,
            }],
        )
        return order, product, variant

    def test_fetch_fulfillment_orders_returns_data(self):
        """GetFulfillmentOrders returns open FOs with line items."""
        order, product, variant = self._make_order_with_fo()
        from ..handlers.fulfillment_handler import handle_fetch_fulfillment_orders
        result = self._call_handler(
            handle_fetch_fulfillment_orders,
            {'id': order.shopify_gid},
        )
        self.assertIn('order', result)
        fo_edges = result['order']['fulfillmentOrders']['edges']
        self.assertEqual(len(fo_edges), 1)
        fo_node = fo_edges[0]['node']
        self.assertEqual(fo_node['status'], 'OPEN')
        li_edges = fo_node['lineItems']['edges']
        self.assertEqual(len(li_edges), 1)
        li = li_edges[0]['node']
        self.assertEqual(li['remainingQuantity'], 4)
        self.assertIn('lineItem', li)
        self.assertEqual(li['lineItem']['variant']['sku'], 'FOQ-SKU')

    def test_fetch_fulfillment_orders_nonexistent_order(self):
        """Returns None for nonexistent order."""
        from ..handlers.fulfillment_handler import handle_fetch_fulfillment_orders
        result = self._call_handler(
            handle_fetch_fulfillment_orders,
            {'id': 'gid://shopify/Order/999999'},
        )
        self.assertIsNone(result['order'])

    def test_dispatch_via_query_handler(self):
        """Verify the fulfillments dispatch key works."""
        order, _, _ = self._make_order_with_fo()
        result = self._call_query('fulfillments', {'id': order.shopify_gid})
        self.assertIn('order', result)
        self.assertIn('fulfillmentOrders', result['order'])


class TestFulfillmentCreate(SimulatorTestCase):
    """Test the fulfillmentCreate mutation handler."""

    def _make_fulfillable_order(self, qty=3, sku='FC-SKU'):
        product = self._seed_product(title='Fulfill Product')
        variant = product.variant_ids[0]
        variant.write({'sku': sku})
        order = self._seed_order(
            name='#FC-1001',
            lines=[{
                'title': 'Fulfill Product',
                'quantity': qty,
                'variant_gid': variant.shopify_gid,
                'sku': sku,
                'unit_price': 20.0,
            }],
        )
        fo = self.env['sim.shopify.fulfillment.order'].search([
            ('order_id', '=', order.id),
        ])
        return order, fo, variant

    def test_full_fulfillment(self):
        """fulfillmentCreate fulfills all remaining quantity."""
        order, fo, variant = self._make_fulfillable_order(qty=3)
        fo_line = fo.line_item_ids[0]

        result = self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': fo.shopify_gid,
                    'fulfillmentOrderLineItems': [{
                        'id': fo_line.shopify_gid,
                        'quantity': 3,
                    }],
                }],
                'trackingInfo': {
                    'number': 'TRACK123',
                    'url': 'https://track.example.com/TRACK123',
                    'company': 'FedEx',
                },
            },
        })

        fc = result.get('fulfillmentCreate', {})
        self.assertEqual(fc['userErrors'], [])
        self.assertIsNotNone(fc['fulfillment'])
        self.assertEqual(fc['fulfillment']['status'], 'SUCCESS')
        self.assertEqual(fc['fulfillment']['trackingInfo'][0]['number'], 'TRACK123')

        # Verify FO line remaining is 0
        fo_line.invalidate_recordset()
        self.assertEqual(fo_line.remaining_quantity, 0)
        # Verify FO is closed
        fo.invalidate_recordset()
        self.assertEqual(fo.status, 'CLOSED')
        # Verify order is FULFILLED
        order.invalidate_recordset()
        self.assertEqual(order.fulfillment_status, 'FULFILLED')

    def test_partial_fulfillment(self):
        """fulfillmentCreate with partial quantity leaves remaining."""
        order, fo, variant = self._make_fulfillable_order(qty=5)
        fo_line = fo.line_item_ids[0]

        result = self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': fo.shopify_gid,
                    'fulfillmentOrderLineItems': [{
                        'id': fo_line.shopify_gid,
                        'quantity': 2,
                    }],
                }],
            },
        })

        fc = result.get('fulfillmentCreate', {})
        self.assertEqual(fc['userErrors'], [])
        # FO line still has remaining
        fo_line.invalidate_recordset()
        self.assertEqual(fo_line.remaining_quantity, 3)
        # FO stays OPEN
        fo.invalidate_recordset()
        self.assertEqual(fo.status, 'OPEN')
        # Order is PARTIALLY_FULFILLED
        order.invalidate_recordset()
        self.assertEqual(order.fulfillment_status, 'PARTIALLY_FULFILLED')

    def test_fulfillment_nonexistent_fo(self):
        """fulfillmentCreate returns error for nonexistent FO."""
        result = self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': 'gid://shopify/FulfillmentOrder/999999',
                    'fulfillmentOrderLineItems': [],
                }],
            },
        })
        fc = result.get('fulfillmentCreate', {})
        self.assertTrue(len(fc['userErrors']) > 0)

    def test_fulfillment_no_lines_provided(self):
        """fulfillmentCreate returns error when no lines given."""
        result = self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [],
            },
        })
        fc = result.get('fulfillmentCreate', {})
        self.assertTrue(len(fc['userErrors']) > 0)

    def test_fulfillment_creates_record(self):
        """fulfillmentCreate creates a sim.shopify.fulfillment record."""
        order, fo, variant = self._make_fulfillable_order(qty=1)
        fo_line = fo.line_item_ids[0]

        before_count = self.env['sim.shopify.fulfillment'].search_count([
            ('order_id', '=', order.id),
        ])
        self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': fo.shopify_gid,
                    'fulfillmentOrderLineItems': [{
                        'id': fo_line.shopify_gid,
                        'quantity': 1,
                    }],
                }],
            },
        })
        after_count = self.env['sim.shopify.fulfillment'].search_count([
            ('order_id', '=', order.id),
        ])
        self.assertEqual(after_count, before_count + 1)

    def test_fulfillment_without_tracking(self):
        """fulfillmentCreate works without trackingInfo."""
        order, fo, variant = self._make_fulfillable_order(qty=1)
        fo_line = fo.line_item_ids[0]

        result = self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': fo.shopify_gid,
                    'fulfillmentOrderLineItems': [{
                        'id': fo_line.shopify_gid,
                        'quantity': 1,
                    }],
                }],
            },
        })
        fc = result.get('fulfillmentCreate', {})
        self.assertEqual(fc['userErrors'], [])
        self.assertEqual(fc['fulfillment']['status'], 'SUCCESS')

    def test_two_step_fulfillment(self):
        """Two partial fulfillments: first partial, then complete."""
        order, fo, variant = self._make_fulfillable_order(qty=4)
        fo_line = fo.line_item_ids[0]

        # Step 1: fulfill 2 of 4
        self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': fo.shopify_gid,
                    'fulfillmentOrderLineItems': [{
                        'id': fo_line.shopify_gid,
                        'quantity': 2,
                    }],
                }],
            },
        })
        order.invalidate_recordset()
        self.assertEqual(order.fulfillment_status, 'PARTIALLY_FULFILLED')

        # Step 2: fulfill remaining 2
        self._call_mutation('fulfillment_create', {
            'fulfillment': {
                'lineItemsByFulfillmentOrder': [{
                    'fulfillmentOrderId': fo.shopify_gid,
                    'fulfillmentOrderLineItems': [{
                        'id': fo_line.shopify_gid,
                        'quantity': 2,
                    }],
                }],
            },
        })
        order.invalidate_recordset()
        self.assertEqual(order.fulfillment_status, 'FULFILLED')
        fo.invalidate_recordset()
        self.assertEqual(fo.status, 'CLOSED')


class TestGetOrderStatus(SimulatorTestCase):
    """Test the GetOrderStatus query (displayFulfillmentStatus)."""

    def test_unfulfilled_order(self):
        """New order returns UNFULFILLED status."""
        order = self._seed_order(name='#OS-1001')
        from ..handlers.fulfillment_handler import handle_get_order_status
        result = self._call_handler(
            handle_get_order_status,
            {'id': order.shopify_gid},
        )
        self.assertEqual(
            result['order']['displayFulfillmentStatus'], 'UNFULFILLED',
        )

    def test_fulfilled_order(self):
        """Fulfilled order returns FULFILLED status."""
        order = self._seed_order(
            name='#OS-1002', fulfillment_status='FULFILLED',
        )
        from ..handlers.fulfillment_handler import handle_get_order_status
        result = self._call_handler(
            handle_get_order_status,
            {'id': order.shopify_gid},
        )
        self.assertEqual(
            result['order']['displayFulfillmentStatus'], 'FULFILLED',
        )

    def test_nonexistent_order(self):
        """Nonexistent order returns None."""
        from ..handlers.fulfillment_handler import handle_get_order_status
        result = self._call_handler(
            handle_get_order_status,
            {'id': 'gid://shopify/Order/999999'},
        )
        self.assertIsNone(result['order'])
