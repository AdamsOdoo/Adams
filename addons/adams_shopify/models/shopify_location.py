from odoo import fields, models


class ShopifyLocation(models.Model):
    _name = 'shopify.location'
    _description = 'Shopify Location'
    _rec_name = 'name'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    shopify_location_id = fields.Char('Shopify Location ID', required=True, index=True)
    name = fields.Char('Location Name', required=True)
    address = fields.Char('Address')
    city = fields.Char('City')
    country_code = fields.Char('Country Code')
    is_active = fields.Boolean('Active on Shopify', default=True)
    is_primary = fields.Boolean('Primary Location')
    warehouse_id = fields.Many2one(
        'stock.warehouse', string='Odoo Warehouse',
        help="Map this Shopify location to an Odoo warehouse for inventory sync.",
    )

    _sql_constraints = [
        ('unique_backend_location', 'UNIQUE(backend_id, shopify_location_id)',
         'Location already exists for this store.'),
    ]
