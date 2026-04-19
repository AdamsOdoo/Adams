# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyGiftCard(models.Model):
    _name = 'shopify.gift.card'
    _description = 'Shopify Gift Card'
    _inherit = 'shopify.binding'
    _rec_name = 'code_masked'

    code_masked = fields.Char('Gift Card (Masked)', readonly=True,
        help="Last 4 characters of the gift card code.")
    initial_amount = fields.Float('Initial Amount')
    balance = fields.Float('Current Balance')
    currency_code = fields.Char('Currency')
    status = fields.Selection([
        ('enabled', 'Enabled'),
        ('disabled', 'Disabled'),
    ], default='enabled')
    customer_binding_id = fields.Many2one(
        'shopify.customer.binding', string='Customer',
    )
    order_binding_id = fields.Many2one(
        'shopify.order.binding', string='Created by Order',
        help="Order that originally created this gift card.",
    )
    expires_on = fields.Date('Expires On')

