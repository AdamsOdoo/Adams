# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import _, api, fields, models


class ShopifySyncLog(models.Model):
    _name = 'shopify.sync.log'
    _description = 'Shopify Sync Log'
    _order = 'create_date desc'
    _rec_name = 'display_name'

    display_name = fields.Char(compute='_compute_display_name', store=False)
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
        ('abandoned_cart', 'Abandoned Carts'),
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
    error_summary = fields.Char(
        string='Error Summary', compute='_compute_error_summary', store=False,
        help='Brief summary of error_details for list views.',
    )

    @api.depends('error_details', 'error_count')
    def _compute_error_summary(self):
        for rec in self:
            if not rec.error_details:
                rec.error_summary = ''
                continue
            lines = [ln.strip() for ln in rec.error_details.strip().splitlines() if ln.strip()]
            if len(lines) == 1:
                rec.error_summary = lines[0][:120]
            else:
                rec.error_summary = f"{lines[0][:80]} (+{len(lines) - 1} more)"

    @api.depends('entity', 'operation', 'started_at')
    def _compute_display_name(self):
        for rec in self:
            entity = dict(rec._fields['entity'].selection).get(rec.entity, '') if rec.entity else ''
            op = dict(rec._fields['operation'].selection).get(rec.operation, '') if rec.operation else ''
            ts = fields.Datetime.to_string(rec.started_at) if rec.started_at else ''
            rec.display_name = f"{op} {entity} @ {ts}".strip()

    @api.depends('started_at', 'finished_at')
    def _compute_duration(self):
        for rec in self:
            if rec.started_at and rec.finished_at:
                delta = rec.finished_at - rec.started_at
                rec.duration = delta.total_seconds()
            else:
                rec.duration = 0.0

    _entity_model_map = {
        'product': 'shopify.product.binding',
        'customer': 'shopify.customer.binding',
        'order': 'shopify.order.binding',
        'inventory': 'shopify.inventory.binding',
        'collection': 'shopify.collection.binding',
        'refund': 'shopify.refund.binding',
    }

    def action_open_error_bindings(self):
        """Open failed binding records related to this sync log's entity + backend."""
        self.ensure_one()
        model = self._entity_model_map.get(self.entity)
        if not model:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Not Available"),
                    'message': _("No binding model for entity '%s'.") % self.entity,
                    'type': 'info',
                    'sticky': False,
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _("Failed %s Records") % self.entity.capitalize(),
            'res_model': model,
            'view_mode': 'list,form',
            'domain': [
                ('backend_id', '=', self.backend_id.id),
                ('sync_status', 'in', ['error', 'permanent_error']),
            ],
        }

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
