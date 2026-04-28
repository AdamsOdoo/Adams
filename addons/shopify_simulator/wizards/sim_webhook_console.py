# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Webhook Test Console.

Allows firing test webhook payloads to the connector's webhook endpoint
directly from the Odoo UI, simulating Shopify webhook deliveries.
"""
import hashlib
import hmac
import json
import logging

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# Standard Shopify webhook topics with sample payloads
_WEBHOOK_TOPICS = [
    ('products/create', 'Product Created'),
    ('products/update', 'Product Updated'),
    ('products/delete', 'Product Deleted'),
    ('orders/create', 'Order Created'),
    ('orders/updated', 'Order Updated'),
    ('orders/cancelled', 'Order Cancelled'),
    ('customers/create', 'Customer Created'),
    ('customers/update', 'Customer Updated'),
    ('refunds/create', 'Refund Created'),
    ('inventory_levels/update', 'Inventory Level Updated'),
    ('fulfillments/create', 'Fulfillment Created'),
    ('app/uninstalled', 'App Uninstalled'),
]


class SimWebhookConsole(models.TransientModel):
    _name = 'sim.webhook.console'
    _description = 'Webhook Test Console'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade',
        string='Simulator Config',
        default=lambda self: self.env.context.get('default_config_id'),
    )

    topic = fields.Selection(
        _WEBHOOK_TOPICS,
        string='Webhook Topic',
        required=True,
        default='products/update',
    )

    # Source record — pick an existing sim record to use as payload
    source_product_id = fields.Many2one(
        'sim.shopify.product', string='Source Product',
        domain="[('config_id', '=', config_id)]",
    )
    source_order_id = fields.Many2one(
        'sim.shopify.order', string='Source Order',
        domain="[('config_id', '=', config_id)]",
    )
    source_customer_id = fields.Many2one(
        'sim.shopify.customer', string='Source Customer',
        domain="[('config_id', '=', config_id)]",
    )

    payload_json = fields.Text(
        string='Webhook Payload (JSON)',
        help='The JSON body that will be sent. Auto-generated from source record, '
             'or you can edit manually.',
    )

    last_response_code = fields.Integer(
        string='Last Response Code', readonly=True,
    )
    last_response_body = fields.Text(
        string='Last Response Body', readonly=True,
    )

    @api.onchange('topic', 'source_product_id', 'source_order_id',
                  'source_customer_id')
    def _onchange_generate_payload(self):
        """Auto-generate payload from the selected source record."""
        if not self.config_id:
            return
        payload = None
        if self.topic in ('products/create', 'products/update') and self.source_product_id:
            payload = self._build_product_payload(self.source_product_id)
        elif self.topic == 'products/delete' and self.source_product_id:
            payload = {'id': self._gid_to_id(self.source_product_id.shopify_gid)}
        elif self.topic in ('orders/create', 'orders/updated', 'orders/cancelled') \
                and self.source_order_id:
            payload = self._build_order_payload(self.source_order_id)
        elif self.topic in ('customers/create', 'customers/update') \
                and self.source_customer_id:
            payload = self._build_customer_payload(self.source_customer_id)
        if payload:
            self.payload_json = json.dumps(payload, indent=2, ensure_ascii=False)

    def action_fire_webhook(self):
        """Send the webhook payload to the connector's endpoint."""
        self.ensure_one()
        if not self.payload_json:
            raise UserError("Payload is empty. Select a source record or enter JSON manually.")

        # Find the webhook callback URL
        backend = self.config_id.backend_id
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        webhook_url = f'{base_url}/shopify/webhook/{backend.id}'

        # Compute HMAC signature using backend's webhook secret
        secret = backend.webhook_secret if hasattr(backend, 'webhook_secret') else ''
        if not secret:
            # Fall back to access token as signing key (simulator mode)
            secret = self.config_id.access_token or ''

        body = self.payload_json.encode('utf-8')
        digest = hmac.new(
            secret.encode('utf-8'), body, hashlib.sha256,
        ).digest()
        import base64
        hmac_header = base64.b64encode(digest).decode('utf-8')

        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Topic': self.topic,
            'X-Shopify-Hmac-Sha256': hmac_header,
            'X-Shopify-Shop-Domain': self.config_id.myshopify_domain or 'simulator.myshopify.com',
            'X-Shopify-API-Version': '2026-01',
        }

        try:
            resp = requests.post(webhook_url, data=body, headers=headers, timeout=30)
            self.write({
                'last_response_code': resp.status_code,
                'last_response_body': resp.text[:2000],
            })
            notif_type = 'success' if resp.status_code == 200 else 'warning'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': f'Webhook Fired — HTTP {resp.status_code}',
                    'message': f'Topic: {self.topic}\n'
                               f'Response: {resp.text[:200]}',
                    'type': notif_type,
                    'sticky': resp.status_code != 200,
                },
            }
        except requests.RequestException as exc:
            self.write({
                'last_response_code': 0,
                'last_response_body': str(exc),
            })
            raise UserError(f"Failed to deliver webhook: {exc}") from exc

    @staticmethod
    def _gid_to_id(gid):
        """Extract numeric ID from a Shopify GID string."""
        if gid and '/' in gid:
            return int(gid.rsplit('/', 1)[-1])
        return 0

    def _build_product_payload(self, product):
        """Build a Shopify-style REST webhook payload for a product."""
        variants = []
        for v in product.variant_ids:
            variants.append({
                'id': self._gid_to_id(v.shopify_gid),
                'product_id': self._gid_to_id(product.shopify_gid),
                'title': v.title or 'Default Title',
                'sku': v.sku or '',
                'price': v.price or '0.00',
                'position': getattr(v, 'position', 1) or 1,
                'option1': v.option1_value,
                'option2': v.option2_value,
                'option3': v.option3_value,
                'inventory_quantity': 0,
                'barcode': v.barcode or None,
            })
        return {
            'id': self._gid_to_id(product.shopify_gid),
            'title': product.title,
            'vendor': product.vendor or '',
            'product_type': product.product_type or '',
            'status': (product.status or 'active').lower(),
            'tags': product.tags or '',
            'variants': variants,
            'admin_graphql_api_id': product.shopify_gid,
        }

    def _build_order_payload(self, order):
        """Build a Shopify-style REST webhook payload for an order."""
        line_items = []
        for li in order.line_item_ids:
            line_items.append({
                'id': self._gid_to_id(li.shopify_gid),
                'title': li.title or '',
                'quantity': li.quantity,
                'sku': li.sku or '',
                'price': str(li.unit_price),
                'variant_id': self._gid_to_id(li.variant_gid),
                'product_id': self._gid_to_id(li.product_gid),
                'admin_graphql_api_id': li.shopify_gid,
            })
        customer_payload = None
        if order.customer_id:
            customer_payload = {
                'id': self._gid_to_id(order.customer_id.shopify_gid),
                'email': order.customer_id.email or '',
                'first_name': order.customer_id.first_name or '',
                'last_name': order.customer_id.last_name or '',
            }
        return {
            'id': self._gid_to_id(order.shopify_gid),
            'name': order.name or '',
            'financial_status': (order.financial_status or 'paid').lower(),
            'fulfillment_status': (
                order.fulfillment_status or 'unfulfilled'
            ).lower() if order.fulfillment_status != 'UNFULFILLED' else None,
            'currency': order.currency_code or 'USD',
            'total_price': str(order.total_price),
            'subtotal_price': str(order.subtotal_price),
            'total_tax': str(order.total_tax),
            'total_discounts': str(order.total_discounts),
            'line_items': line_items,
            'customer': customer_payload,
            'shipping_address': {
                'first_name': order.ship_first_name or '',
                'last_name': order.ship_last_name or '',
                'address1': order.ship_address1 or '',
                'city': order.ship_city or '',
                'province_code': order.ship_province_code or '',
                'country_code': order.ship_country_code or '',
                'zip': order.ship_zip or '',
            } if order.ship_address1 else None,
            'admin_graphql_api_id': order.shopify_gid,
        }

    def _build_customer_payload(self, customer):
        """Build a Shopify-style REST webhook payload for a customer."""
        return {
            'id': self._gid_to_id(customer.shopify_gid),
            'email': customer.email or '',
            'first_name': customer.first_name or '',
            'last_name': customer.last_name or '',
            'phone': customer.phone or '',
            'tags': customer.tags or '',
            'addresses': [{
                'address1': customer.address1 or '',
                'city': customer.city or '',
                'province_code': customer.province_code or '',
                'country_code': customer.country_code or '',
                'zip': customer.zip_code or '',
            }] if customer.address1 else [],
            'admin_graphql_api_id': customer.shopify_gid,
        }
