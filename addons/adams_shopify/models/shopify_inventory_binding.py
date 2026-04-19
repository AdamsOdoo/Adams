# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyInventoryBinding(models.Model):
    _name = 'shopify.inventory.binding'
    _inherit = 'shopify.binding'
    _description = 'Shopify Inventory Binding'

    variant_binding_id = fields.Many2one(
        'shopify.variant.binding', string='Variant Binding',
        required=True, ondelete='cascade', index=True,
    )
    shopify_inventory_item_id = fields.Char('Inventory Item ID', index=True)
    shopify_location_id = fields.Char('Shopify Location ID')
    last_pushed_qty = fields.Float('Last Pushed Quantity')


    _unique_backend_shopify = models.Constraint(
        'UNIQUE(backend_id, shopify_id)',
        'A binding already exists for this Shopify inventory level.',
    )

    @api.model
    def run_export(self, backend):
        from ..sync.inventory_sync import InventorySync
        syncer = InventorySync(self.env, backend)
        syncer.export_inventory(backend)
