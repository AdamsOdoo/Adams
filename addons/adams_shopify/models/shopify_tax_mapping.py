# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyTaxMapping(models.Model):
    _name = 'shopify.tax.mapping'
    _description = 'Shopify Tax Mapping'
    _rec_name = 'shopify_tax_name'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    shopify_tax_name = fields.Char('Shopify Tax Name', required=True,
        help="Tax title as it appears in Shopify (e.g. 'VAT', 'GST').")
    shopify_tax_rate = fields.Float('Shopify Tax Rate (%)',
        help="Expected tax rate from Shopify for matching.")
    odoo_tax_id = fields.Many2one(
        'account.tax', string='Odoo Tax',
        domain="[('type_tax_use', '=', 'sale')]",
        help="Odoo tax to apply when this Shopify tax is encountered.",
    )
    fiscal_position_id = fields.Many2one(
        'account.fiscal.position', string='Fiscal Position',
        help="Optional: auto-assign this fiscal position on orders with this tax.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('unique_backend_tax', 'UNIQUE(backend_id, shopify_tax_name)',
         'Tax mapping already exists for this name on this store.'),
    ]
