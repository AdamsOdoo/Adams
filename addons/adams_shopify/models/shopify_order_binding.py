import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyOrderBinding(models.Model):
    _name = 'shopify.order.binding'
    _inherit = 'shopify.binding'
    _description = 'Shopify Order Binding'

    odoo_id = fields.Many2one(
        'sale.order', string='Odoo Sale Order',
        ondelete='set null', index=True,
    )
    shopify_order_name = fields.Char('Shopify Order #')
    shopify_financial_status = fields.Selection([
        ('pending', 'Pending'),
        ('authorized', 'Authorized'),
        ('partially_paid', 'Partially Paid'),
        ('paid', 'Paid'),
        ('partially_refunded', 'Partially Refunded'),
        ('refunded', 'Refunded'),
        ('voided', 'Voided'),
    ], string='Financial Status')
    shopify_fulfillment_status = fields.Selection([
        ('unfulfilled', 'Unfulfilled'),
        ('partial', 'Partially Fulfilled'),
        ('fulfilled', 'Fulfilled'),
        ('restocked', 'Restocked'),
    ], string='Fulfillment Status')
    shopify_created_at = fields.Datetime('Shopify Created At')

    _sql_constraints = [
        ('unique_backend_shopify',
         'UNIQUE(backend_id, shopify_id)',
         'A binding already exists for this Shopify order.'),
    ]

    @api.model
    def run_import(self, backend):
        from ..sync.order_sync import OrderSync
        syncer = OrderSync(self.env, backend)
        syncer.import_orders()

    @api.model
    def process_webhook_event(self, backend, data, topic):
        from ..sync.order_sync import OrderSync
        syncer = OrderSync(self.env, backend)
        syncer.import_single_order(data)
