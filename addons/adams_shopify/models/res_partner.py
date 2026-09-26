# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


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

    def write(self, vals):
        res = super().write(vals)
        # Skip if context flag set (prevents recursion during import)
        if self.env.context.get('shopify_no_auto_export'):
            return res
        # Check for sync-relevant field changes
        sync_fields = {'name', 'email', 'phone', 'street', 'city', 'country_id'}
        if sync_fields & set(vals.keys()):
            bindings = self.env['shopify.customer.binding'].search([
                ('odoo_id', 'in', self.ids),
                ('sync_status', '=', 'synced'),
            ])
            for binding in bindings:
                if binding.backend_id.state == 'connected' and \
                        binding.backend_id.customer_sync_direction in ('export', 'both'):
                    binding.write({'sync_status': 'pending'})
        return res
