# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyPaymentGateway(models.Model):
    _name = 'shopify.payment.gateway'
    _description = 'Shopify Payment Gateway'
    _rec_name = 'name'

    name = fields.Char('Gateway Name', required=True)
    code = fields.Char('Gateway Code')
    journal_id = fields.Many2one(
        'account.journal', string='Payment Journal',
        domain="[('type', 'in', ['bank', 'cash'])]",
        help="Journal to use when recording payments from this gateway.",
    )
    company_id = fields.Many2one(
        'res.company', default=lambda self: self.env.company,
    )
    active = fields.Boolean(default=True)

