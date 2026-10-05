from odoo import models, fields


class ShopifyProductType(models.Model):
    _name = "shopify.product.type.ts"
    _description = "Shopify Product Type"

    name = fields.Char("Name", required=True)
