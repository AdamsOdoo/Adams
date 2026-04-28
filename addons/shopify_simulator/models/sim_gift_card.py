# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Simulated Shopify Gift Card model.

Gift cards are returned by the FETCH_GIFT_CARDS query and can be created
via the giftCardCreate mutation (not yet implemented).
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyGiftCard(models.Model):
    _name = 'sim.shopify.gift.card'
    _description = 'Simulated Shopify Gift Card'
    _order = 'created_at desc, id desc'
    _rec_name = 'code_masked'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)

    code_masked = fields.Char(
        string='Code (Masked)', required=True,
        help='Last 4 characters of the gift card code, e.g. "•••• d2fg".',
    )
    initial_amount = fields.Float(string='Initial Amount', default=0.0)
    balance = fields.Float(string='Current Balance', default=0.0)
    currency_code = fields.Char(string='Currency', default='USD')
    status = fields.Selection([
        ('ENABLED', 'Enabled'),
        ('DISABLED', 'Disabled'),
    ], default='ENABLED', string='Status', required=True)

    customer_gid = fields.Char(
        string='Customer GID',
        help='Shopify GID of the customer this gift card belongs to.',
    )
    order_gid = fields.Char(
        string='Order GID',
        help='Shopify GID of the order that created this gift card.',
    )
    expires_on = fields.Date(string='Expires On')
    note = fields.Text(string='Note')

    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.shopify_gid:
                rec.shopify_gid = rec.config_id._next_gid('GiftCard')
            # Auto-set balance to initial amount if not specified
            if rec.balance == 0.0 and rec.initial_amount > 0:
                rec.balance = rec.initial_amount
        return records

    def _to_graphql_node(self):
        """Build GraphQL node for gift card."""
        return {
            'id': self.shopify_gid,
            'maskedCode': self.code_masked,
            'initialValue': {
                'amount': str(self.initial_amount),
                'currencyCode': self.currency_code or 'USD',
            },
            'balance': {
                'amount': str(self.balance),
                'currencyCode': self.currency_code or 'USD',
            },
            'enabled': self.status == 'ENABLED',
            'customer': {'id': self.customer_gid} if self.customer_gid else None,
            'order': {'id': self.order_gid} if self.order_gid else None,
            'expiresOn': self.expires_on.isoformat() if self.expires_on else None,
            'note': self.note or '',
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }
