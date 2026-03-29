from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_bind_ids = fields.One2many(
        'shopify.order.binding', 'odoo_id',
        string='Shopify Bindings',
    )
    shopify_order_name = fields.Char(
        'Shopify Order #', readonly=True,
    )
    shopify_financial_status = fields.Char(
        'Shopify Financial Status', readonly=True,
    )
    shopify_fulfillment_status = fields.Char(
        'Shopify Fulfillment Status', readonly=True,
    )
    shopify_tags = fields.Char('Shopify Tags')

    def write(self, vals):
        res = super().write(vals)
        # Skip if context flag set (prevents recursion during import)
        if self.env.context.get('shopify_no_auto_export'):
            return res
        # Check for sync-relevant field changes
        sync_fields = {'note', 'shopify_tags'}
        if sync_fields & set(vals.keys()):
            bindings = self.env['shopify.order.binding'].search([
                ('odoo_id', 'in', self.ids),
                ('sync_status', '=', 'synced'),
            ])
            for binding in bindings:
                if binding.backend_id.state == 'connected':
                    binding.write({'sync_status': 'pending'})
        return res
