# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Simulated Shopify Abandoned Cart (Checkout) model.

Represents checkouts that were started but not completed.
"""
import json
import logging
import uuid

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyAbandonedCart(models.Model):
    _name = 'sim.shopify.abandoned.cart'
    _description = 'Simulated Shopify Abandoned Cart'
    _order = 'abandoned_at desc, id desc'
    _rec_name = 'display_name'

    _unique_checkout_token = models.Constraint(
        'UNIQUE(config_id, checkout_token)',
        'Checkout token must be unique per config.',
    )

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)

    checkout_token = fields.Char(
        string='Checkout Token',
        default=lambda self: uuid.uuid4().hex,
        help='Unique checkout token from Shopify.',
    )
    display_name = fields.Char(
        compute='_compute_display_name', store=True, string='Name',
    )

    abandoned_at = fields.Datetime(
        string='Abandoned At', default=fields.Datetime.now,
    )
    recovery_url = fields.Char(string='Recovery URL')

    customer_email = fields.Char(string='Customer Email')
    customer_phone = fields.Char(string='Customer Phone')
    customer_name = fields.Char(string='Customer Name')
    customer_gid = fields.Char(
        string='Customer GID',
        help='Shopify GID of the customer, if logged in.',
    )

    total_price = fields.Float(string='Total Price', default=0.0)
    subtotal_price = fields.Float(string='Subtotal Price', default=0.0)
    currency_code = fields.Char(string='Currency', default='USD')

    line_items_json = fields.Text(
        string='Line Items (JSON)',
        help='JSON array of line items: [{title, quantity, price, variant_id}]',
    )
    line_item_count = fields.Integer(
        compute='_compute_line_item_count', store=True,
        string='Line Item Count',
    )

    recovered = fields.Boolean(
        default=False, string='Recovered',
        help='Set when this checkout converts to a completed order.',
    )
    recovered_order_gid = fields.Char(string='Recovered Order GID')

    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    @api.depends('customer_name', 'customer_email')
    def _compute_display_name(self):
        for rec in self:
            name = rec.customer_name or rec.customer_email or 'Anonymous'
            rec.display_name = f'Cart - {name}'

    @api.depends('line_items_json')
    def _compute_line_item_count(self):
        for rec in self:
            try:
                items = json.loads(rec.line_items_json or '[]')
                rec.line_item_count = len(items)
            except (json.JSONDecodeError, TypeError):
                rec.line_item_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.shopify_gid:
                rec.shopify_gid = rec.config_id._next_gid('AbandonedCheckout')
            if not rec.recovery_url:
                base = rec.config_id.myshopify_domain or 'simulator.myshopify.com'
                rec.recovery_url = (
                    f'https://{base}/checkouts/{rec.checkout_token}/recover'
                )
        return records

    def _to_graphql_node(self):
        """Build GraphQL node for abandoned checkout."""
        try:
            line_items = json.loads(self.line_items_json or '[]')
        except (json.JSONDecodeError, TypeError):
            line_items = []

        return {
            'id': self.shopify_gid,
            'abandonedCheckoutUrl': self.recovery_url or '',
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'customer': {
                'id': self.customer_gid,
                'email': self.customer_email or '',
                'displayName': self.customer_name or '',
            } if self.customer_gid or self.customer_email else None,
            'totalPriceSet': {
                'shopMoney': {
                    'amount': str(self.total_price),
                    'currencyCode': self.currency_code or 'USD',
                },
            },
            'subtotalPriceSet': {
                'shopMoney': {
                    'amount': str(self.subtotal_price),
                    'currencyCode': self.currency_code or 'USD',
                },
            },
            'lineItems': {
                'edges': [
                    {'node': item} for item in line_items
                ],
            },
            'completedAt': None,  # Abandoned = not completed
        }
