# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyFieldMapping(models.Model):
    _name = 'shopify.field.mapping'
    _description = 'Shopify Field Mapping'
    _order = 'sequence, id'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade',
    )
    sequence = fields.Integer(default=10)
    entity = fields.Selection([
        ('product', 'Product'),
        ('customer', 'Customer'),
    ], required=True, default='product')
    odoo_field = fields.Char('Odoo Field', required=True)
    shopify_field = fields.Char('Shopify Field', required=True)
    direction = fields.Selection([
        ('export', 'Export Only (Odoo → Shopify)'),
        ('import', 'Import Only (Shopify → Odoo)'),
        ('both', 'Both Directions'),
    ], required=True, default='both')
    active = fields.Boolean(default=True)

    @api.model
    def _get_default_product_mappings(self):
        """Return the default product field mapping configuration."""
        return [
            {'odoo_field': 'name', 'shopify_field': 'title', 'direction': 'both'},
            {'odoo_field': 'description_sale', 'shopify_field': 'bodyHtml', 'direction': 'both'},
            {'odoo_field': 'default_code', 'shopify_field': 'sku', 'direction': 'both'},
            {'odoo_field': 'list_price', 'shopify_field': 'price', 'direction': 'export'},
            {'odoo_field': 'weight', 'shopify_field': 'weight', 'direction': 'both'},
            {'odoo_field': 'barcode', 'shopify_field': 'barcode', 'direction': 'both'},
            {'odoo_field': 'categ_id.name', 'shopify_field': 'productType', 'direction': 'export'},
        ]

    @api.model
    def _get_default_customer_mappings(self):
        """Return the default customer field mapping configuration."""
        return [
            {'odoo_field': 'name', 'shopify_field': 'firstName+lastName', 'direction': 'both'},
            {'odoo_field': 'email', 'shopify_field': 'email', 'direction': 'both'},
            {'odoo_field': 'phone', 'shopify_field': 'phone', 'direction': 'both'},
            {'odoo_field': 'street', 'shopify_field': 'address1', 'direction': 'import'},
            {'odoo_field': 'city', 'shopify_field': 'city', 'direction': 'import'},
            {'odoo_field': 'zip', 'shopify_field': 'zip', 'direction': 'import'},
            {'odoo_field': 'country_id.code', 'shopify_field': 'countryCodeV2', 'direction': 'import'},
        ]
