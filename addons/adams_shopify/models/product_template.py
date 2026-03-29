from odoo import api, fields, models

import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    shopify_bind_ids = fields.One2many(
        'shopify.product.binding', 'odoo_id',
        string='Shopify Bindings',
    )
    shopify_no_sync = fields.Boolean(
        'Exclude from Shopify Sync',
        help="If checked, this product will not be synchronized with any Shopify store.",
    )

    def write(self, vals):
        res = super().write(vals)
        # Skip if context flag set (prevents recursion during import)
        if self.env.context.get('shopify_no_auto_export'):
            return res
        # Check for sync-relevant field changes
        sync_fields = {'name', 'description_sale', 'list_price', 'default_code',
                       'barcode', 'weight', 'categ_id', 'image_1920'}
        if sync_fields & set(vals.keys()):
            bindings = self.env['shopify.product.binding'].search([
                ('odoo_id', 'in', self.ids),
                ('sync_status', '=', 'synced'),
                ('no_sync', '=', False),
            ])
            for binding in bindings:
                if binding.backend_id.auto_export_on_change and binding.backend_id.state == 'connected':
                    binding.write({'sync_status': 'pending'})
        return res
