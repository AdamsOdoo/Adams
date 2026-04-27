# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Full order lifecycle integration test.

Tests the complete order flow:
  Create order → Mark as paid → Fulfill → Refund
  Verify webhooks fire at each step, status updates are correct.
"""
from unittest.mock import patch

from .common import SimulatorTestCase


class TestOrderLifecycle(SimulatorTestCase):
    """End-to-end order lifecycle through the simulator."""

    def setUp(self):
        super().setUp()
        # Create a realistic order with products
        self.product = self._seed_product(title='Lifecycle Widget')
        self.variant = self.product.variant_ids[0]
        self.variant.write({'sku': 'LCW-001', 'price': 49.99})
        self.customer = self._seed_customer(
            first_name='Alice', last_name='Test',
            email='alice@test.example.com',
        )

    def _create_order(self, financial_status='PENDING'):
        """Helper to create a test order."""
        return self._seed_order(
            name='#LC-1001',
            customer=self.customer,
            total_price=99.98,
            subtotal_price=99.98,
            financial_status=financial_status,
            lines=[{
                'title': 'Lifecycle Widget',
                'quantity': 2,
                'variant_gid': self.variant.shopify_gid,
                'sku': 'LCW-001',
                'unit_price': 49.99,
            }],
        )

    def test_full_lifecycle_pending_to_paid(self):
        """Order: PENDING → orderMarkAsPaid → PAID."""
        order = self._create_order(financial_status='PENDING')
        self.assertEqual(order.financial_status, 'PENDING')

        result = self._call_mutation('order_mark_paid', {
            'input': {'id': order.shopify_gid},
        })
        omp = result.get('orderMarkAsPaid', {})
        self.assertEqual(omp['userErrors'], [])
        self.assertEqual(omp['order']['displayFinancialStatus'], 'PAID')

        order.invalidate_recordset()
        self.assertEqual(order.financial_status, 'PAID')

    def test_full_lifecycle_paid_to_fulfilled(self):
        """Order: PAID → fulfillmentCreate → FULFILLED."""
        order = self._create_order(financial_status='PAID')

        # Get fulfillment order
        fo = self.env['sim.shopify.fulfillment.order'].search([
            ('order_id', '=', order.id),
        ])
        self.assertTrue(fo, "FulfillmentOrder should be auto-created")
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
                'trackingInfo': {
                    'number': 'TRK-LC-001',
                    'company': 'UPS',
                },
            },
        })
        fc = result.get('fulfillmentCreate', {})
        self.assertEqual(fc['userErrors'], [])

        order.invalidate_recordset()
        self.assertEqual(order.fulfillment_status, 'FULFILLED')

    def test_full_lifecycle_fulfilled_to_refunded(self):
        """Order: FULFILLED → refundCreate → REFUNDED."""
        order = self._create_order(financial_status='PAID')
        order.write({'fulfillment_status': 'FULFILLED'})

        result = self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'note': 'Customer returned items',
                'transactions': [{'amount': 99.98}],
            },
        })
        rc = result.get('refundCreate', {})
        self.assertEqual(rc['userErrors'], [])

        order.invalidate_recordset()
        self.assertEqual(order.financial_status, 'REFUNDED')

    @patch('odoo.addons.shopify_simulator.models.sim_webhook.SimShopifyWebhookSubscription._deliver_webhook')
    def test_full_lifecycle_with_webhooks(self, mock_deliver):
        """Full lifecycle fires webhooks at each step."""
        # Register webhooks
        for topic in ['FULFILLMENTS_CREATE', 'REFUNDS_CREATE']:
            self.env['sim.shopify.webhook.subscription'].create({
                'config_id': self.sim_config.id,
                'topic': topic,
                'callback_url': 'http://localhost:9999/webhook',
            })
        self.backend.write({'webhook_secret': 'lifecycle_secret'})

        order = self._create_order(financial_status='PAID')

        # Step 1: Mark as paid (no webhook for this)
        # (orderMarkAsPaid doesn't have a webhook topic)

        # Step 2: Fulfill
        fo = self.env['sim.shopify.fulfillment.order'].search([
            ('order_id', '=', order.id),
        ])
        fo_line = fo.line_item_ids[0]
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
        self.assertEqual(mock_deliver.call_count, 1)

        # Step 3: Refund
        self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'transactions': [{'amount': 99.98}],
            },
        })
        self.assertEqual(mock_deliver.call_count, 2)

        # Verify final state
        order.invalidate_recordset()
        self.assertEqual(order.fulfillment_status, 'FULFILLED')
        self.assertEqual(order.financial_status, 'REFUNDED')


class TestOrderMarkAsPaid(SimulatorTestCase):
    """Test the orderMarkAsPaid mutation in isolation."""

    def test_mark_pending_as_paid(self):
        """PENDING → PAID."""
        order = self._seed_order(
            name='#OMP-1', financial_status='PENDING',
        )
        result = self._call_mutation('order_mark_paid', {
            'input': {'id': order.shopify_gid},
        })
        self.assertEqual(
            result['orderMarkAsPaid']['order']['displayFinancialStatus'],
            'PAID',
        )

    def test_mark_authorized_as_paid(self):
        """AUTHORIZED → PAID."""
        order = self._seed_order(
            name='#OMP-2', financial_status='AUTHORIZED',
        )
        result = self._call_mutation('order_mark_paid', {
            'input': {'id': order.shopify_gid},
        })
        self.assertEqual(
            result['orderMarkAsPaid']['order']['displayFinancialStatus'],
            'PAID',
        )

    def test_already_paid_stays_paid(self):
        """Already PAID order stays PAID (no error)."""
        order = self._seed_order(
            name='#OMP-3', financial_status='PAID',
        )
        result = self._call_mutation('order_mark_paid', {
            'input': {'id': order.shopify_gid},
        })
        self.assertEqual(
            result['orderMarkAsPaid']['order']['displayFinancialStatus'],
            'PAID',
        )
        self.assertEqual(result['orderMarkAsPaid']['userErrors'], [])

    def test_nonexistent_order(self):
        """Nonexistent order returns error."""
        result = self._call_mutation('order_mark_paid', {
            'input': {'id': 'gid://shopify/Order/999999'},
        })
        self.assertTrue(len(result['orderMarkAsPaid']['userErrors']) > 0)


class TestFetchSingleOrder(SimulatorTestCase):
    """Test the single order query handler."""

    def test_fetch_single_order(self):
        """Fetch a single order by GID."""
        order = self._seed_order(
            name='#SO-1001',
            total_price=50.0,
            financial_status='PAID',
        )
        result = self._call_query('single_order', {'id': order.shopify_gid})
        self.assertIsNotNone(result['order'])
        self.assertEqual(result['order']['id'], order.shopify_gid)
        self.assertEqual(result['order']['name'], '#SO-1001')

    def test_fetch_nonexistent_order(self):
        """Returns None for nonexistent order."""
        result = self._call_query(
            'single_order', {'id': 'gid://shopify/Order/999999'},
        )
        self.assertIsNone(result['order'])
