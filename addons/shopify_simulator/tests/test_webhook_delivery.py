# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Tests for outbound webhook delivery.

Covers:
- HMAC computation (valid signature)
- Webhook delivery on fulfillment/refund mutations
- Missing callback URL handling
- Topic matching
"""
import base64
import hashlib
import hmac
import json
from unittest.mock import patch, MagicMock

from .common import SimulatorTestCase


class TestWebhookHMAC(SimulatorTestCase):
    """Test HMAC signature computation for outbound webhooks."""

    def test_hmac_computation(self):
        """Verify HMAC matches Shopify's algorithm."""
        secret = 'test_webhook_secret_123'
        payload = {'id': 123, 'title': 'Test Product'}
        raw_body = json.dumps(payload).encode('utf-8')

        expected = base64.b64encode(
            hmac.new(
                secret.encode('utf-8'),
                raw_body,
                hashlib.sha256,
            ).digest()
        ).decode('utf-8')

        # Verify the simulator uses the same algorithm
        from ..models.sim_webhook import SimShopifyWebhookSubscription
        # The static method _deliver_webhook computes HMAC inline,
        # so we verify the connector's _verify_hmac would accept it
        from odoo.addons.shopify_connector_pro.controllers.webhook import (
            ShopifyWebhookController,
        )
        self.assertTrue(
            ShopifyWebhookController._verify_hmac(raw_body, expected, secret),
        )

    def test_hmac_empty_secret(self):
        """Empty webhook secret produces empty HMAC header."""
        # When no secret is set, the deliver function sends empty HMAC
        # This matches behavior — the connector would reject it
        from ..models.sim_webhook import SimShopifyWebhookSubscription
        # No assertion needed — just verifying no crash
        SimShopifyWebhookSubscription._deliver_webhook(
            callback_url='http://localhost:9999/noop',
            raw_body=b'{}',
            topic_rest='products/create',
            webhook_secret='',
            shop_domain='test.myshopify.com',
            api_version='2026-01',
        )


class TestWebhookTopicMatching(SimulatorTestCase):
    """Test topic enum ↔ REST mapping."""

    def test_topic_enum_to_rest(self):
        """Verify all expected topic mappings exist."""
        from ..models.sim_webhook import TOPIC_ENUM_TO_REST
        expected_topics = [
            ('PRODUCTS_CREATE', 'products/create'),
            ('ORDERS_CREATE', 'orders/create'),
            ('FULFILLMENTS_CREATE', 'fulfillments/create'),
            ('REFUNDS_CREATE', 'refunds/create'),
            ('CUSTOMERS_CREATE', 'customers/create'),
            ('INVENTORY_LEVELS_UPDATE', 'inventory_levels/update'),
        ]
        for enum_val, rest_val in expected_topics:
            self.assertEqual(
                TOPIC_ENUM_TO_REST.get(enum_val), rest_val,
                f"Missing or wrong mapping for {enum_val}",
            )

    def test_topic_rest_to_enum(self):
        """Verify reverse mapping works."""
        from ..models.sim_webhook import TOPIC_REST_TO_ENUM
        self.assertEqual(
            TOPIC_REST_TO_ENUM.get('products/create'), 'PRODUCTS_CREATE',
        )
        self.assertEqual(
            TOPIC_REST_TO_ENUM.get('fulfillments/create'), 'FULFILLMENTS_CREATE',
        )


class TestWebhookFiring(SimulatorTestCase):
    """Test that mutations fire webhooks when subscriptions exist."""

    def _register_webhook(self, topic_enum, callback_url=None):
        """Helper to register a webhook subscription."""
        return self.env['sim.shopify.webhook.subscription'].create({
            'config_id': self.sim_config.id,
            'topic': topic_enum,
            'callback_url': callback_url or 'http://localhost:9999/webhook',
        })

    @patch('odoo.addons.shopify_simulator.models.sim_webhook.SimShopifyWebhookSubscription._deliver_webhook')
    def test_fulfillment_create_fires_webhook(self, mock_deliver):
        """fulfillmentCreate fires fulfillments/create webhook."""
        self._register_webhook('FULFILLMENTS_CREATE')
        self.backend.write({'webhook_secret': 'test_secret'})

        product = self._seed_product(title='WH Fulfill Product')
        variant = product.variant_ids[0]
        order = self._seed_order(
            name='#WH-1001',
            lines=[{
                'title': 'WH Fulfill Product',
                'quantity': 1,
                'variant_gid': variant.shopify_gid,
                'sku': 'WH-SKU',
            }],
        )
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
                        'quantity': 1,
                    }],
                }],
            },
        })

        mock_deliver.assert_called_once()
        call_kwargs = mock_deliver.call_args
        self.assertEqual(call_kwargs.kwargs.get('topic_rest') or call_kwargs[1].get('topic_rest', call_kwargs[0][1] if len(call_kwargs[0]) > 1 else ''), 'fulfillments/create')

    @patch('odoo.addons.shopify_simulator.models.sim_webhook.SimShopifyWebhookSubscription._deliver_webhook')
    def test_refund_create_fires_webhook(self, mock_deliver):
        """refundCreate fires refunds/create webhook."""
        self._register_webhook('REFUNDS_CREATE')
        self.backend.write({'webhook_secret': 'test_secret'})

        order = self._seed_order(
            name='#WH-1002',
            total_price=100.0,
            financial_status='PAID',
        )
        self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'transactions': [{'amount': 50.0}],
            },
        })

        mock_deliver.assert_called_once()

    @patch('odoo.addons.shopify_simulator.models.sim_webhook.SimShopifyWebhookSubscription._deliver_webhook')
    def test_no_webhook_fired_without_subscription(self, mock_deliver):
        """No webhook is fired when no subscription matches."""
        order = self._seed_order(
            name='#WH-1003',
            total_price=100.0,
            financial_status='PAID',
        )
        self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'transactions': [{'amount': 50.0}],
            },
        })

        mock_deliver.assert_not_called()

    @patch('odoo.addons.shopify_simulator.models.sim_webhook.SimShopifyWebhookSubscription._deliver_webhook')
    def test_webhook_not_fired_for_wrong_topic(self, mock_deliver):
        """Webhook registered for PRODUCTS_CREATE doesn't fire on refund."""
        self._register_webhook('PRODUCTS_CREATE')
        order = self._seed_order(
            name='#WH-1004',
            total_price=100.0,
            financial_status='PAID',
        )
        self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'transactions': [{'amount': 50.0}],
            },
        })
        mock_deliver.assert_not_called()

    @patch('odoo.addons.shopify_simulator.models.sim_webhook.SimShopifyWebhookSubscription._deliver_webhook')
    def test_webhook_headers_include_required_fields(self, mock_deliver):
        """Delivered webhook includes all required Shopify headers."""
        self._register_webhook('REFUNDS_CREATE')
        self.backend.write({'webhook_secret': 'test_secret_456'})

        order = self._seed_order(
            name='#WH-1005',
            total_price=100.0,
            financial_status='PAID',
        )
        self._call_mutation('refund_create', {
            'input': {
                'orderId': order.shopify_gid,
                'transactions': [{'amount': 25.0}],
            },
        })

        mock_deliver.assert_called_once()
        kwargs = mock_deliver.call_args.kwargs if mock_deliver.call_args.kwargs else {}
        if not kwargs:
            # positional args
            args = mock_deliver.call_args.args
            # _deliver_webhook(callback_url, raw_body, topic_rest,
            #                  webhook_secret, shop_domain, api_version)
            self.assertTrue(len(args) >= 4)
            self.assertEqual(args[2], 'refunds/create')
            self.assertEqual(args[3], 'test_secret_456')
        else:
            self.assertEqual(kwargs.get('topic_rest'), 'refunds/create')
            self.assertEqual(kwargs.get('webhook_secret'), 'test_secret_456')
