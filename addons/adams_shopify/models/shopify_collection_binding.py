# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyCollectionBinding(models.Model):
    _name = 'shopify.collection.binding'
    _description = 'Shopify Collection Binding'
    _inherit = 'shopify.binding'

    odoo_id = fields.Many2one(
        'product.category', string='Product Category',
        required=True, ondelete='cascade', index=True,
    )
    shopify_handle = fields.Char('Handle')
    shopify_title = fields.Char('Shopify Title')
    product_count = fields.Integer('Products Count')

