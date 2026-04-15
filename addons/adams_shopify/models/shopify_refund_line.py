# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyRefundLine(models.Model):
    _name = 'shopify.refund.line'
    _description = 'Shopify Refund Line Item'

    refund_binding_id = fields.Many2one(
        'shopify.refund.binding', required=True, ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer('Quantity')
    amount = fields.Float('Amount')
    restock_type = fields.Selection([
        ('no_restock', 'No Restock'),
        ('cancel', 'Cancel'),
        ('return', 'Return'),
    ], default='no_restock')
