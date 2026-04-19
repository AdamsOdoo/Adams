# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = 'product.product'

    shopify_variant_bind_ids = fields.One2many(
        'shopify.variant.binding', 'odoo_id',
        string='Shopify Variant Bindings',
    )
