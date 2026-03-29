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
    shopify_url = fields.Char('Shopify URL', compute='_compute_shopify_url')

    def _compute_shopify_url(self):
        for rec in self:
            if rec.shopify_id and rec.backend_id.shop_url:
                numeric_id = rec.shopify_id.split('/')[-1] if rec.shopify_id else ''
                base = rec.backend_id.shop_url.rstrip('/')
                if not base.startswith('https://'):
                    base = f"https://{base}"
                rec.shopify_url = f"{base}/admin/customers/{numeric_id}"
            else:
                rec.shopify_url = False

    def action_view_on_shopify(self):
        self.ensure_one()
        if self.shopify_url:
            return {
                'type': 'ir.actions.act_url',
                'url': self.shopify_url,
                'target': 'new',
            }

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
