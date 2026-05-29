# Part of Shopify Simulator. Internal QA tool — not for public distribution.
from odoo import api, fields, models


class SimShopifyImage(models.Model):
    _name = 'sim.shopify.image'
    _description = 'Simulated Shopify Product Image'
    _order = 'sequence, id'

    product_id = fields.Many2one(
        'sim.shopify.product', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Image GID', readonly=True)
    url = fields.Char(
        default='https://cdn.shopify.com/s/files/placeholder.png',
        help='Placeholder URL — real image download tested in staging only',
    )
    alt_text = fields.Char()
    sequence = fields.Integer(default=10)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            product = self.env['sim.shopify.product'].browse(vals.get('product_id'))
            config = product.config_id if product else None
            if config and not vals.get('shopify_gid'):
                vals['shopify_gid'] = config._next_gid('ProductImage')
        return super().create(vals_list)

    def _to_graphql_node(self):
        """Return dict matching Shopify image node: {id, url, altText}."""
        self.ensure_one()
        return {
            'id': self.shopify_gid,
            'url': self.url or '',
            'altText': self.alt_text or '',
        }
