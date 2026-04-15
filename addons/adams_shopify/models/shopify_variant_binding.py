# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyVariantBinding(models.Model):
    _name = 'shopify.variant.binding'
    _inherit = 'shopify.binding'
    _description = 'Shopify Variant Binding'

    odoo_id = fields.Many2one(
        'product.product', string='Odoo Variant',
        required=True, ondelete='cascade', index=True,
    )
    product_binding_id = fields.Many2one(
        'shopify.product.binding', string='Product Binding',
        ondelete='cascade', index=True,
    )
    shopify_inventory_item_id = fields.Char('Inventory Item ID')
    shopify_sku = fields.Char('Shopify SKU')

    _sql_constraints = [
        ('unique_backend_shopify',
         'UNIQUE(backend_id, shopify_id)',
         'A binding already exists for this Shopify variant.'),
        ('unique_backend_odoo',
         'UNIQUE(backend_id, odoo_id)',
         'This Odoo variant is already linked to this Shopify store.'),
    ]
