# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ShopifyDiscountUsage(models.Model):
    _name = 'shopify.discount.usage'
    _description = 'Shopify Discount Code Usage'
    _order = 'date desc'

    discount_code_id = fields.Many2one(
        'shopify.discount.code', required=True, ondelete='cascade',
    )
    order_binding_id = fields.Many2one(
        'shopify.order.binding', required=True, ondelete='cascade',
    )
    sale_order_id = fields.Many2one(
        'sale.order', related='order_binding_id.odoo_id', store=True,
    )
    promoter_id = fields.Many2one(
        'shopify.promoter', related='discount_code_id.promoter_id', store=True,
    )
    backend_id = fields.Many2one(
        'shopify.backend', related='discount_code_id.backend_id', store=True,
    )
    discount_amount = fields.Float()
    order_total = fields.Float()
    commission_amount = fields.Float()
    date = fields.Datetime()

    _sql_constraints = [
        ('unique_code_order', 'UNIQUE(discount_code_id, order_binding_id)',
         'This code usage is already recorded for this order.'),
    ]
