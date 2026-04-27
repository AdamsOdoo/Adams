# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for order query and mutation handlers.
"""
from .common import SimulatorTestCase
from ..handlers import order_handler


class TestFetchOrders(SimulatorTestCase):
    """Test handle_fetch_orders handler."""

    def test_empty_store(self):
        """Empty store should return empty edges."""
        result = self._call_handler(order_handler.handle_fetch_orders)
        self.assertEqual(result['orders']['edges'], [])

    def test_fetch_all_orders(self):
        """Should return all orders."""
        self._seed_order('#1001', total_price=50.00)
        self._seed_order('#1002', total_price=75.00)
        result = self._call_handler(
            order_handler.handle_fetch_orders, {'first': 50},
        )
        self.assertEqual(len(result['orders']['edges']), 2)

    def test_order_node_money_set_shape(self):
        """Order node should have MoneyV2Set structure."""
        self._seed_order('#1001', total_price=99.99, currency_code='EUR')
        result = self._call_handler(
            order_handler.handle_fetch_orders, {'first': 10},
        )
        node = result['orders']['edges'][0]['node']
        total = node['totalPriceSet']
        self.assertIn('shopMoney', total)
        self.assertIn('presentmentMoney', total)
        self.assertEqual(total['shopMoney']['currencyCode'], 'EUR')

    def test_fetch_orders_with_financial_status_filter(self):
        """Should filter orders by financial_status query parameter."""
        self._seed_order('#1001', financial_status='PAID')
        self._seed_order('#1002', financial_status='PENDING')
        self._seed_order('#1003', financial_status='PAID')

        result = self._call_handler(
            order_handler.handle_fetch_orders,
            {'first': 50, 'query': 'financial_status:paid'},
        )
        edges = result['orders']['edges']
        self.assertEqual(len(edges), 2)
        for e in edges:
            self.assertEqual(e['node']['displayFinancialStatus'], 'PAID')


class TestOrderUpdate(SimulatorTestCase):
    """Test handle_order_update mutation handler."""

    def test_update_order_tags(self):
        """Should update order tags."""
        order = self._seed_order('#1001')
        result = self._call_handler(
            order_handler.handle_order_update,
            {'input': {
                'id': order.shopify_gid,
                'tags': ['imported', 'reviewed'],
            }},
        )
        resp = result['orderUpdate']
        self.assertEqual(resp['userErrors'], [])
        self.assertEqual(resp['order']['tags'], ['imported', 'reviewed'])
        order.invalidate_recordset()
        self.assertIn('imported', order.tags)

    def test_update_order_note(self):
        """Should update order note."""
        order = self._seed_order('#1001')
        self._call_handler(
            order_handler.handle_order_update,
            {'input': {'id': order.shopify_gid, 'note': 'Rush order!'}},
        )
        order.invalidate_recordset()
        self.assertEqual(order.note, 'Rush order!')

    def test_update_nonexistent_order(self):
        """Should return userErrors for missing order."""
        result = self._call_handler(
            order_handler.handle_order_update,
            {'input': {'id': 'gid://shopify/Order/999', 'tags': []}},
        )
        self.assertTrue(result['orderUpdate']['userErrors'])
        self.assertIsNone(result['orderUpdate']['order'])

    def test_order_with_line_items_and_shipping(self):
        """Order with line items and shipping lines should have correct shape."""
        customer = self._seed_customer('John', 'Doe')
        product = self._seed_product('Test Widget')
        variant = product.variant_ids[0]
        order = self._seed_order(
            '#1001',
            customer=customer,
            total_price=59.99,
            subtotal_price=49.99,
            total_tax=5.00,
            total_shipping=5.00,
            lines=[{
                'title': 'Test Widget',
                'quantity': 1,
                'sku': variant.sku or 'WDG',
                'variant_gid': variant.shopify_gid,
                'product_gid': product.shopify_gid,
                'unit_price': 49.99,
                'tax_amount': 5.00,
                'tax_rate': 0.10,
            }],
            shipping_lines=[{
                'title': 'Express',
                'code': 'express',
                'price': 5.00,
            }],
        )
        result = self._call_handler(
            order_handler.handle_fetch_orders, {'first': 10},
        )
        node = result['orders']['edges'][0]['node']
        # Line items
        li = node['lineItems']['edges'][0]['node']
        self.assertEqual(li['title'], 'Test Widget')
        self.assertEqual(li['quantity'], 1)
        self.assertIsNotNone(li['variant'])
        self.assertEqual(li['variant']['id'], variant.shopify_gid)
        # Tax lines
        self.assertEqual(len(li['taxLines']), 1)
        self.assertEqual(li['taxLines'][0]['rate'], 0.10)
        # Shipping lines
        self.assertEqual(len(node['shippingLines']), 1)
        self.assertEqual(node['shippingLines'][0]['code'], 'express')
