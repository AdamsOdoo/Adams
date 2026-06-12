# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
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
    ], string='Financial Status', index=True)
    payment_id = fields.Many2one(
        'account.payment', string='Registered Payment',
        ondelete='set null', index=True,
        help='Payment auto-registered when Shopify captures funds. '
             'Used for per-binding idempotency so multi-backend setups '
             'with identical order names do not collide.',
    )
    shopify_fulfillment_status = fields.Char('Fulfillment Status', index=True)
    shopify_refund_count = fields.Integer(
        'Shopify Refund Count', default=0,
        help="Number of refunds on the Shopify order, updated on each "
             "import/sync. Used by reconciliation to detect partially "
             "imported refund sets without an extra API call.",
    )
    shopify_created_at = fields.Datetime('Shopify Created At')
    shopify_total_amount = fields.Float(
        'Shopify Total', digits=0, default=0.0,
        help="Total charged on Shopify (totalPriceSet) in the order's "
             "import currency, stamped at import. The permanent "
             "total-check guard compares computed invoice totals against "
             "it before any automatic posting and blocks on mismatch "
             "(invoice stays in draft with a warning activity). Zero "
             "means no stamp — the guard skips (e.g. bindings created "
             "before this field existed).",
    )
    shopify_url = fields.Char('Shopify URL', compute='_compute_shopify_url')

    _unique_backend_shopify = models.Constraint(
        'UNIQUE(backend_id, shopify_id)',
        'A binding already exists for this Shopify order.',
    )

    @api.depends('shopify_id', 'backend_id.shop_url')
    def _compute_shopify_url(self):
        for rec in self:
            if rec.shopify_id and rec.backend_id.shop_url:
                numeric_id = rec.shopify_id.split('/')[-1] if rec.shopify_id else ''
                base = rec.backend_id.shop_url.rstrip('/')
                if not base.startswith('https://'):
                    base = f"https://{base}"
                rec.shopify_url = f"{base}/admin/orders/{numeric_id}"
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
