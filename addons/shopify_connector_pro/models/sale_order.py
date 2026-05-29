# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    shopify_bind_ids = fields.One2many(
        'shopify.order.binding', 'odoo_id',
        string='Shopify Bindings',
    )
    sales_channel = fields.Selection([
        ('direct', 'Direct / B2B'),
        ('shopify', 'Shopify'),
    ], default='direct', readonly=True, index=True,
        help="Sales channel that created this order. "
             "Only 'Shopify' orders are synced with Shopify.",
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
    shopify_reverse_sync = fields.Boolean(
        'Sync to Shopify', default=True,
        help="Allow Odoo → Shopify sync for this order. When unchecked, "
             "posting invoices, credit notes, or validating deliveries for "
             "this order will NOT update Shopify, even if reverse sync is "
             "enabled on the backend. Shopify → Odoo sync (status updates, "
             "refund imports) is not affected by this setting.",
    )
    shopify_sync_status_display = fields.Char(
        'Reverse Sync Status', compute='_compute_shopify_sync_status_display',
        help="Shows whether Odoo → Shopify sync is active for this order "
             "and explains why if it is disabled.",
    )

    @api.depends('sales_channel', 'shopify_reverse_sync', 'shopify_bind_ids.backend_id.reverse_sync_payment',
                 'shopify_bind_ids.backend_id.reverse_sync_refund')
    def _compute_shopify_sync_status_display(self):
        for order in self:
            if order.sales_channel != 'shopify' or not order.shopify_bind_ids:
                order.shopify_sync_status_display = ''
                continue
            if not order.shopify_reverse_sync:
                order.shopify_sync_status_display = 'Disabled for this order'
                continue
            # Check if any linked backend has reverse sync enabled
            backends = order.shopify_bind_ids.mapped('backend_id')
            has_payment = any(b.reverse_sync_payment for b in backends)
            has_refund = any(b.reverse_sync_refund for b in backends)
            if has_payment or has_refund:
                parts = []
                if has_payment:
                    parts.append('payments')
                if has_refund:
                    parts.append('refunds')
                order.shopify_sync_status_display = (
                    'Active (%s)' % ', '.join(parts)
                )
            else:
                order.shopify_sync_status_display = (
                    'Disabled on backend'
                )

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
