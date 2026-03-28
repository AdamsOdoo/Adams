import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyCustomerBinding(models.Model):
    _name = 'shopify.customer.binding'
    _inherit = 'shopify.binding'
    _description = 'Shopify Customer Binding'

    odoo_id = fields.Many2one(
        'res.partner', string='Odoo Contact',
        required=True, ondelete='cascade', index=True,
    )
    shopify_email = fields.Char('Shopify Email')
    shopify_tags = fields.Char('Shopify Tags')

    _sql_constraints = [
        ('unique_backend_shopify',
         'UNIQUE(backend_id, shopify_id)',
         'A binding already exists for this Shopify customer.'),
    ]

    @api.model
    def run_import(self, backend):
        from ..sync.customer_sync import CustomerSync
        syncer = CustomerSync(self.env, backend)
        syncer.import_customers()

    @api.model
    def process_webhook_event(self, backend, data, topic):
        from ..sync.customer_sync import CustomerSync
        syncer = CustomerSync(self.env, backend)
        syncer.import_single_customer(data)
