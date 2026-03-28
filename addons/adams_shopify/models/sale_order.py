from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_bind_ids = fields.One2many(
        'shopify.order.binding', 'odoo_id',
        string='Shopify Bindings',
    )
    shopify_order_name = fields.Char(
        'Shopify Order #', readonly=True,
    )
    shopify_financial_status = fields.Char(
        'Shopify Financial Status', readonly=True,
    )
    shopify_fulfillment_status = fields.Char(
        'Shopify Fulfillment Status', readonly=True,
    )
