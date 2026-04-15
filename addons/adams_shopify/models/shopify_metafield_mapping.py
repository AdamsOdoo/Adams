# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyMetafieldMapping(models.Model):
    _name = 'shopify.metafield.mapping'
    _description = 'Shopify Metafield Mapping'
    _rec_name = 'shopify_key'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    owner_type = fields.Selection([
        ('product', 'Product'),
        ('variant', 'Variant'),
        ('customer', 'Customer'),
    ], required=True, default='product')
    shopify_namespace = fields.Char('Namespace', required=True, default='custom')
    shopify_key = fields.Char('Key', required=True)
    shopify_type = fields.Selection([
        ('single_line_text_field', 'Single Line Text'),
        ('multi_line_text_field', 'Multi Line Text'),
        ('number_integer', 'Integer'),
        ('number_decimal', 'Decimal'),
        ('boolean', 'Boolean'),
        ('json', 'JSON'),
        ('url', 'URL'),
        ('date', 'Date'),
    ], string='Metafield Type', default='single_line_text_field')
    odoo_field = fields.Char('Odoo Field Name', required=True,
        help="Technical name of the Odoo field to sync (e.g. x_custom_field).")
    direction = fields.Selection([
        ('import', 'Shopify to Odoo'),
        ('export', 'Odoo to Shopify'),
        ('both', 'Bidirectional'),
    ], default='both', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_mapping', 'UNIQUE(backend_id, owner_type, shopify_namespace, shopify_key)',
         'Mapping already exists for this metafield.'),
    ]
