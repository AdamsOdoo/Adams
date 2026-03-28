from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    shopify_bind_ids = fields.One2many(
        'shopify.customer.binding', 'odoo_id',
        string='Shopify Bindings',
    )
    is_shopify_customer = fields.Boolean(
        'Shopify Customer', default=False,
        help="Indicates this contact was imported from Shopify.",
    )
