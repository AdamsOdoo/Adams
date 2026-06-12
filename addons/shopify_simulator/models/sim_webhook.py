# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Webhook subscription model.

Simulates Shopify webhook subscriptions created via webhookSubscriptionCreate
and queried via WEBHOOK_LIST_QUERY.

When the simulator receives mutations that modify data, it checks for matching
subscriptions and fires outbound webhook POSTs to the registered callback URLs.
"""
import base64
import hashlib
import hmac as hmac_mod
import json
import logging
import threading
import uuid

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

# Map Shopify GraphQL enum topics to REST webhook topic strings
TOPIC_ENUM_TO_REST = {
    'PRODUCTS_CREATE': 'products/create',
    'PRODUCTS_UPDATE': 'products/update',
    'PRODUCTS_DELETE': 'products/delete',
    'ORDERS_CREATE': 'orders/create',
    'ORDERS_UPDATED': 'orders/updated',
    'ORDERS_CANCELLED': 'orders/cancelled',
    'CUSTOMERS_CREATE': 'customers/create',
    'CUSTOMERS_UPDATE': 'customers/update',
    'INVENTORY_LEVELS_UPDATE': 'inventory_levels/update',
    'FULFILLMENTS_CREATE': 'fulfillments/create',
    'REFUNDS_CREATE': 'refunds/create',
    'APP_UNINSTALLED': 'app/uninstalled',
    'CUSTOMERS_DATA_REQUEST': 'customers/data_request',
    'CUSTOMERS_REDACT': 'customers/redact',
    'SHOP_REDACT': 'shop/redact',
}

TOPIC_REST_TO_ENUM = {v: k for k, v in TOPIC_ENUM_TO_REST.items()}


class SimShopifyWebhookSubscription(models.Model):
    _name = 'sim.shopify.webhook.subscription'
    _description = 'Simulated Shopify Webhook Subscription'
    _order = 'id'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    topic = fields.Char(
        string='Topic (enum)',
        required=True,
        help='Shopify GraphQL enum topic, e.g. PRODUCTS_CREATE.',
    )
    callback_url = fields.Char(
        string='Callback URL', required=True,
        help='URL that receives webhook POST requests.',
    )
    format = fields.Selection([
        ('JSON', 'JSON'),
        ('XML', 'XML'),
    ], default='JSON', string='Format')
    include_fields = fields.Text(
        string='Include Fields',
        help='Comma-separated list of fields to include (not implemented).',
    )
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('shopify_gid'):
                config = self.env['sim.shopify.config'].browse(
                    vals.get('config_id')
                )
                if config:
                    vals['shopify_gid'] = config._next_gid(
                        'WebhookSubscription'
                    )
        return super().create(vals_list)

    def _to_graphql_node(self):
        """Return dict matching Shopify webhookSubscription response shape."""
        self.ensure_one()
        rest_topic = TOPIC_ENUM_TO_REST.get(self.topic, self.topic)
        return {
            'id': self.shopify_gid,
            'topic': rest_topic,
            'endpoint': {
                '__typename': 'WebhookHttpEndpoint',
                'callbackUrl': self.callback_url or '',
            },
            'createdAt': (
                self.created_at.isoformat() + 'Z' if self.created_at else ''
            ),
        }

    # ── Outbound webhook delivery ─────────────────────────────

    @api.model
    def _fire_webhook(self, config, topic_rest, payload_dict):
        """Fire outbound webhook for matching subscriptions.

        Args:
            config: sim.shopify.config record
            topic_rest: REST topic string, e.g. 'products/update'
            payload_dict: dict to be JSON-serialized as the webhook body
        """
        topic_enum = TOPIC_REST_TO_ENUM.get(topic_rest)
        if not topic_enum:
            return

        subscriptions = self.search([
            ('config_id', '=', config.id),
            ('topic', '=', topic_enum),
        ])
        if not subscriptions:
            return

        raw_body = json.dumps(payload_dict).encode('utf-8')
        webhook_secret = config.backend_id.webhook_secret or ''

        for sub in subscriptions:
            if not sub.callback_url:
                continue
            self._deliver_webhook(
                callback_url=sub.callback_url,
                raw_body=raw_body,
                topic_rest=topic_rest,
                webhook_secret=webhook_secret,
                shop_domain=config.myshopify_domain or '',
                api_version='2026-01',
            )

    @staticmethod
    def _deliver_webhook(callback_url, raw_body, topic_rest,
                         webhook_secret, shop_domain, api_version):
        """Deliver a single webhook POST in a background thread.

        Computes HMAC-SHA256 matching Shopify's exact algorithm so the
        connector's _verify_hmac() passes.
        """
        hmac_signature = ''
        if webhook_secret:
            hmac_signature = base64.b64encode(
                hmac_mod.new(
                    webhook_secret.encode('utf-8'),
                    raw_body,
                    hashlib.sha256,
                ).digest()
            ).decode('utf-8')

        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Topic': topic_rest,
            'X-Shopify-Hmac-Sha256': hmac_signature,
            'X-Shopify-Shop-Domain': shop_domain,
            'X-Shopify-Webhook-Id': str(uuid.uuid4()),
            'X-Shopify-API-Version': api_version,
        }

        def _send():
            try:
                resp = requests.post(
                    callback_url,
                    data=raw_body,
                    headers=headers,
                    timeout=10,
                )
                _logger.info(
                    "Simulator webhook delivered: %s → %s (status=%s)",
                    topic_rest, callback_url, resp.status_code,
                )
            except Exception as e:
                _logger.warning(
                    "Simulator webhook delivery failed: %s → %s: %s",
                    topic_rest, callback_url, e,
                )

        # Synchronous under the test runner: a daemon thread outlives
        # the test's logger state (mute/capture) and leaks its
        # connection-failure warning into the build log after the test
        # finished; it also makes delivery assertions racy.
        from odoo.modules import module as odoo_module
        if odoo_module.current_test:
            _send()
            return
        thread = threading.Thread(target=_send, daemon=True)
        thread.start()
