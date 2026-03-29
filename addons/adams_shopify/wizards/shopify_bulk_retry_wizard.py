from odoo import api, fields, models, _


class ShopifyBulkRetryWizard(models.TransientModel):
    _name = 'shopify.bulk.retry.wizard'
    _description = 'Shopify Bulk Retry Failed Records'

    backend_id = fields.Many2one('shopify.backend', string='Store', required=True)
    entity = fields.Selection([
        ('product', 'Products'),
        ('customer', 'Customers'),
        ('order', 'Orders'),
        ('all', 'All Entities'),
    ], default='all', required=True)
    include_permanent = fields.Boolean('Include Permanent Errors', default=False)

    def action_retry(self):
        self.ensure_one()
        status_filter = ['error']
        if self.include_permanent:
            status_filter.append('permanent_error')

        count = 0
        models_to_retry = []
        if self.entity in ('product', 'all'):
            models_to_retry.append('shopify.product.binding')
        if self.entity in ('customer', 'all'):
            models_to_retry.append('shopify.customer.binding')
        if self.entity in ('order', 'all'):
            models_to_retry.append('shopify.order.binding')

        for model_name in models_to_retry:
            bindings = self.env[model_name].search([
                ('backend_id', '=', self.backend_id.id),
                ('sync_status', 'in', status_filter),
            ])
            bindings.action_retry_sync()
            count += len(bindings)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Bulk Retry"),
                'message': _("%d records reset to pending for re-sync.") % count,
                'type': 'success',
                'sticky': False,
            },
        }
