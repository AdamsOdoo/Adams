# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ShopifyBinding(models.AbstractModel):
    _name = 'shopify.binding'
    _description = 'Shopify Binding (Abstract)'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    shopify_id = fields.Char('Shopify ID', index=True)
    sync_checksum = fields.Char('Sync Checksum')
    last_sync_date = fields.Datetime('Last Sync Date')
    sync_status = fields.Selection([
        ('pending', 'Pending'),
        ('synced', 'Synced'),
        ('error', 'Error'),
        ('permanent_error', 'Permanent Error'),
    ], default='pending', index=True)
    sync_error = fields.Text('Last Sync Error')
    retry_count = fields.Integer(default=0)

    def action_retry_sync(self):
        """Reset error status so the record is picked up on next sync."""
        self.write({
            'sync_status': 'pending',
            'sync_error': False,
            'retry_count': 0,
        })

    def _mark_synced(self, shopify_id=None, checksum=None):
        vals = {
            'sync_status': 'synced',
            'sync_error': False,
            'last_sync_date': fields.Datetime.now(),
            'retry_count': 0,
        }
        if shopify_id:
            vals['shopify_id'] = shopify_id
        if checksum:
            vals['sync_checksum'] = checksum
        self.write(vals)

    def _mark_error(self, error_message, permanent=False):
        self.write({
            'sync_status': 'permanent_error' if permanent else 'error',
            'sync_error': error_message,
            'retry_count': self.retry_count + 1 if not permanent else self.retry_count,
        })
