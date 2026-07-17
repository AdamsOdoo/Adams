from odoo import fields, models


class ShopifyConnectorSaleOrderLine(models.Model):
    """Adds immutable Shopify line-item traceability; not a binding model."""

    _inherit = 'sale.order.line'

    shopify_line_item_gid = fields.Char(index=True, readonly=True)
