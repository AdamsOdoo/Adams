from odoo import api, fields, models


class ShopifySyncLog(models.Model):
    _name = 'shopify.sync.log'
    _description = 'Shopify Sync Log'
    _order = 'create_date desc'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    entity = fields.Selection([
        ('product', 'Products'),
        ('customer', 'Customers'),
        ('order', 'Orders'),
        ('inventory', 'Inventory'),
        ('fulfillment', 'Fulfillments'),
        ('collection', 'Collections'),
        ('discount', 'Discounts'),
        ('refund', 'Refunds'),
        ('metafield', 'Metafields'),
        ('location', 'Locations'),
    ], required=True)
    operation = fields.Selection([
        ('export', 'Export'),
        ('import', 'Import'),
        ('webhook', 'Webhook'),
    ], required=True)
    state = fields.Selection([
        ('running', 'Running'),
        ('done', 'Done'),
        ('partial', 'Partial'),
        ('error', 'Error'),
    ], default='running')
    started_at = fields.Datetime(default=fields.Datetime.now)
    finished_at = fields.Datetime()
    duration = fields.Float(compute='_compute_duration', store=True)
    total_records = fields.Integer()
    success_count = fields.Integer()
    error_count = fields.Integer()
    skipped_count = fields.Integer()
    error_details = fields.Text()

    @api.depends('started_at', 'finished_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.finished_at:
                delta = rec.finished_at - rec.started_at
                rec.duration = delta.total_seconds()
            else:
                rec.duration = 0.0

    def _finalize(self, success=0, errors=0, skipped=0, error_details=None):
        state = 'done'
        if errors and success:
            state = 'partial'
        elif errors and not success:
            state = 'error'
        self.write({
            'state': state,
            'finished_at': fields.Datetime.now(),
            'total_records': success + errors + skipped,
            'success_count': success,
            'error_count': errors,
            'skipped_count': skipped,
            'error_details': error_details,
        })
