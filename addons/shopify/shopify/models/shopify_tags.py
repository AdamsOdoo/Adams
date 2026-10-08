from odoo import models, fields


class ShopifyTags(models.Model):
    _name = "shopify.tags.ts"
    _description = "Shopify Tags"

    name = fields.Char("Name", required=True)
    sequence = fields.Integer("Sequence")
