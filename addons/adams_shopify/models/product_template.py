from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_bind_ids = fields.One2many(
        'shopify.product.binding', 'odoo_id',
        string='Shopify Bindings',
    )
    shopify_no_sync = fields.Boolean(
        'Exclude from Shopify Sync',
        help="If checked, this product will not be synchronized with any Shopify store.",
    )
