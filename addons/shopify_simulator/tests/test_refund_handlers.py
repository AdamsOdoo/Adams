# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Tests for refund-related handlers.

Covers:
- FETCH_REFUNDS query
- refundCreate mutation (full, partial, restock types)
- Order financial status updates after refund
"""
from .common import SimulatorTestCase


class TestFetchRefunds(SimulatorTestCase):
    """Test the FETCH_REFUNDS query handler."""

    def _make_order_with_refund(self):
        """Create an order with a refund for testing."""
        product = self._seed_product(title='Refund Product')
        variant = product.variant_ids[0]
        order = self._seed_order(
            name='#REF-1001',
            total_price=100.0,
            subtotal_price=100.0,
            financial_status='PAID',
            lines=[{
                'title': 'Refund Product',
                'quantity': 2,
                'variant_gid': variant.shopify_gid,
                'sku': 'REF-SKU',
                'unit_price': 50.0,
            }],
        )
        refund = self.env['sim.shopify.refund'].create({
            'config_id': self.sim_config.id,
            'order_id': order.id,
            'note': 'Test refund',
            'total_refunded': 50.0,
            'currency_code': 'USD',
        })
        self.env['sim.shopify.refund.line'].create({
            'refund_id': refund.id,
            'line_item_gid': order.line_item_ids[0].shopify_gid,
            'line_item_title': 'Refund Product',
            'variant_gid': variant.shopify_gid,
            'variant_sku': 'REF-SKU',
            'quantity': 1,
            'restock_type': 'RETURN',
            'subtotal': 50.0,
        })
        return order, refund, variant

    def test_fetch_refunds_returns_data(self):
        """FETCH_REFUNDS returns refund data with line items."""
        order, refund, variant = self._make_order_with_refund()
        result = self._call_query('refunds', {'orderId': order.shopify_gid})

        self.assertIn('order', result)
        refunds = result['order']['refunds']
        self.assertEqual(len(refunds), 1)

        r = refunds[0]
        self.assertEqual(r['id'], refund.shopify_gid)
        self.assertEqual(r['note'], 'Test refund')
        self.assertEqual(
            r['totalRefundedSet']['shopMoney']['amount'], '50.0',
        )
        self.assertIn('refundLineItems', r)

        edges = r['refundLineItems']['edges']
        self.assertEqual(len(edges), 1)
        node = edges[0]['node']
        self.assertEqual(node['quantity'], 1)
        self.assertEqual(node['restockType'], 'RETURN')
        self.assertEqual(node['lineItem']['variant']['sku'], 'REF-SKU')

    def test_fetch_refunds_empty(self):
        """Order with no refunds returns empty list."""
        order = self._seed_order(name='#REF-1002', financial_status='PAID')
        result = self._call_query('refunds', {'orderId': order.shopify_gid})
        self.assertEqual(result['order']['refunds'], [])

    def test_fetch_refunds_nonexistent_order(self):
        """Nonexistent order returns None."""
        result = self._call_query(
            'refunds', {'orderId': 'gid://shopify/Order/999999'},
        )
        self.assertIsNone(result['order'])

    def test_refund_graphql_node_shape(self):
        """Verify refund node has all required fields."""
        order, refund, _ = self._make_order_with_refund()
        node = refund._to_graphql_node()
        required_fields = [
            'id', 'note', 'createdAt', 'totalRefundedSet', 'refundLineItems',
        ]
        for field in required_fields:
            self.assertIn(field, node, f"Missing field: {field}")
        self.assertIn('shopMoney', node['totalRefundedSet'])
        self.assertIn('presentmentMoney', node['totalRefundedSet'])

    def test_refund_line_graphql_node_shape(self):
        """Verify refund line node has all required fields."""
        order, refund, _ = self._make_order_with_refund()
        line = refund.refund_line_ids[0]
        node = line._to_graphql_node('USD', 'USD')
        required_fields = [
            'lineItem', 'quantity', 'restockType', 'subtotalSet',
        ]
        for field in required_fields:
            self.assertIn(field, node, f"Missing field: {field}")


class TestRefundCreate(SimulatorTestCase):
    """Test the refundCreate mutation handler."""

    def _make_paid_order(self, total=100.0):
        product = self._seed_product(title='Refund Create Product')
        variant = product.variant_ids[0]
        order = self._seed_order(
            name='#RC-1001',
            total_price=total,
            subtotal_price=total,
            financial_status='PAID',
            lines=[{
                'title': 'Refund Create Product',
                'quantity': 2,
                'variant_gid': variant.shopify_gid,
                'unit_price': total / 2,
            }],
        )
        return order

    def test_full_refund(self):
        """Full refund sets order to REFUNDED."""
        order = self._make_paid_order(total=100.0)
        result = self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'note': 'Full refund',
                'transactions': [{
                    'amount': 100.0,
                    'gateway': 'manual',
                    'kind': 'REFUND',
                    'orderId': order.shopify_gid,
                }],
            },
        })
        rc = result.get('refundCreate', {})
        self.assertEqual(rc['userErrors'], [])
        self.assertIsNotNone(rc['refund'])
        self.assertEqual(rc['refund']['totalRefundedSet']['shopMoney']['amount'], '100.0')

        order.invalidate_recordset()
        self.assertEqual(order.financial_status, 'REFUNDED')

    def test_partial_refund(self):
        """Partial refund sets order to PARTIALLY_REFUNDED."""
        order = self._make_paid_order(total=100.0)
        result = self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'note': 'Partial refund',
                'transactions': [{
                    'amount': 30.0,
                    'gateway': 'manual',
                    'kind': 'REFUND',
                    'orderId': order.shopify_gid,
                }],
            },
        })
        rc = result.get('refundCreate', {})
        self.assertEqual(rc['userErrors'], [])
        self.assertEqual(rc['refund']['totalRefundedSet']['shopMoney']['amount'], '30.0')

        order.invalidate_recordset()
        self.assertEqual(order.financial_status, 'PARTIALLY_REFUNDED')

    def test_refund_nonexistent_order(self):
        """Refund returns error for nonexistent order."""
        result = self._call_mutation('refund_create', {
            'input': {
                'orderId': 'gid://shopify/Order/999999',
                'transactions': [{'amount': 10.0}],
            },
        })
        rc = result.get('refundCreate', {})
        self.assertTrue(len(rc['userErrors']) > 0)

    def test_refund_with_shipping(self):
        """Refund with shipping amount adds to total."""
        order = self._seed_order(
            name='#RC-1002',
            total_price=110.0,
            total_shipping=10.0,
            financial_status='PAID',
        )
        result = self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'note': 'With shipping',
                'shipping': {'amount': 10.0, 'fullRefund': False},
                'transactions': [{'amount': 100.0}],
            },
        })
        rc = result.get('refundCreate', {})
        self.assertEqual(rc['userErrors'], [])
        # Total = 100 (transactions) + 10 (shipping) = 110
        self.assertEqual(rc['refund']['totalRefundedSet']['shopMoney']['amount'], '110.0')

    def test_refund_with_full_shipping_refund(self):
        """Refund with fullRefund shipping adds order's total_shipping."""
        order = self._seed_order(
            name='#RC-1003',
            total_price=120.0,
            total_shipping=20.0,
            financial_status='PAID',
        )
        result = self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'shipping': {'fullRefund': True},
                'transactions': [{'amount': 100.0}],
            },
        })
        rc = result.get('refundCreate', {})
        self.assertEqual(rc['userErrors'], [])
        # Total = 100 (transactions) + 20 (full shipping) = 120
        self.assertEqual(rc['refund']['totalRefundedSet']['shopMoney']['amount'], '120.0')

    def test_refund_creates_record(self):
        """refundCreate creates a sim.shopify.refund record."""
        order = self._make_paid_order(total=50.0)
        before = self.env['sim.shopify.refund'].search_count([
            ('order_id', '=', order.id),
        ])
        self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'transactions': [{'amount': 25.0}],
            },
        })
        after = self.env['sim.shopify.refund'].search_count([
            ('order_id', '=', order.id),
        ])
        self.assertEqual(after, before + 1)

    def test_refund_no_transactions(self):
        """Refund with empty transactions creates zero-amount refund."""
        order = self._make_paid_order(total=100.0)
        result = self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'note': 'No money back',
                'transactions': [],
            },
        })
        rc = result.get('refundCreate', {})
        self.assertEqual(rc['userErrors'], [])
        # Order stays PAID (0 amount refund doesn't change status)
        order.invalidate_recordset()
        self.assertEqual(order.financial_status, 'PAID')
