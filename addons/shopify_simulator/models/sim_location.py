# Part of Shopify Simulator. Internal QA tool — not for public distribution.
from odoo import api, fields, models


class SimShopifyLocation(models.Model):
    _name = 'sim.shopify.location'
    _description = 'Simulated Shopify Location'
    _rec_name = 'name'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    name = fields.Char(required=True, default='Main Warehouse')
    address1 = fields.Char()
    city = fields.Char()
    country_code = fields.Char(default='US')
    is_active = fields.Boolean(default=True)
    is_primary = fields.Boolean(default=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            config = self.env['sim.shopify.config'].browse(vals.get('config_id'))
            if config and not vals.get('shopify_gid'):
                vals['shopify_gid'] = config._next_gid('Location')
        return super().create(vals_list)

    def _to_graphql_node(self):
        self.ensure_one()
        return {
            'id': self.shopify_gid,
            'name': self.name or '',
            'address': {
                'address1': self.address1 or '',
                'city': self.city or '',
                'countryCode': self.country_code or '',
            },
            'isActive': self.is_active,
            'isPrimary': self.is_primary,
        }
