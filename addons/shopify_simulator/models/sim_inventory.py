# Part of Shopify Simulator. Internal QA tool — not for public distribution.
from odoo import api, fields, models


class SimShopifyInventoryLevel(models.Model):
    _name = 'sim.shopify.inventory.level'
    _description = 'Simulated Shopify Inventory Level'
    _rec_name = 'display_name'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    variant_id = fields.Many2one(
        'sim.shopify.variant', required=True, ondelete='cascade', index=True,
    )
    location_id = fields.Many2one(
        'sim.shopify.location', required=True, ondelete='cascade', index=True,
    )
    inventory_item_gid = fields.Char(
        related='variant_id.inventory_item_gid', store=True, index=True,
    )
    location_gid = fields.Char(
        related='location_id.shopify_gid', store=True, index=True,
    )
    available = fields.Integer(default=0)

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('variant_id.sku', 'location_id.name', 'available')
    def _compute_display_name(self):
        for rec in self:
            sku = rec.variant_id.sku or rec.variant_id.shopify_gid or '?'
            loc = rec.location_id.name or '?'
            rec.display_name = f'{sku} @ {loc}: {rec.available}'

    _unique_variant_location = models.Constraint(
        'UNIQUE(variant_id, location_id)',
        'One inventory level per variant per location.',
    )
