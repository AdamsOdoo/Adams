# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class ShopifyDiscountCode(models.Model):
    _name = 'shopify.discount.code'
    _description = 'Shopify Discount Code'
    _inherit = 'shopify.binding'

    promoter_id = fields.Many2one(
        'shopify.promoter', required=True, ondelete='cascade',
    )
    code = fields.Char(required=True, help="The actual coupon code customers enter")
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ], required=True, default='percentage')
    discount_value = fields.Float('Value', help="10 for 10% or $10")
    minimum_order_amount = fields.Float()
    usage_limit = fields.Integer(help="0 = unlimited")
    one_per_customer = fields.Boolean()
    starts_at = fields.Datetime(default=fields.Datetime.now)
    ends_at = fields.Datetime()
    active_on_shopify = fields.Boolean(default=True)
    usage_ids = fields.One2many('shopify.discount.usage', 'discount_code_id')

    # Computed
    usage_count = fields.Integer(compute='_compute_usage_stats', store=True)
    total_discount_amount = fields.Float(compute='_compute_usage_stats', store=True)
    total_order_revenue = fields.Float(compute='_compute_usage_stats', store=True)


    _unique_backend_code = models.Constraint(
        'UNIQUE(backend_id, code)',
        'This discount code already exists for this store.',
    )
    _unique_backend_shopify = models.Constraint(
        'UNIQUE(backend_id, shopify_id)',
        'A binding already exists for this Shopify discount.',
    )

    @api.depends('usage_ids.discount_amount', 'usage_ids.order_total')
    def _compute_usage_stats(self):
        for rec in self:
            rec.usage_count = len(rec.usage_ids)
            rec.total_discount_amount = sum(rec.usage_ids.mapped('discount_amount'))
            rec.total_order_revenue = sum(rec.usage_ids.mapped('order_total'))

    def action_push_to_shopify(self):
        """Manual push button to create/update discount on Shopify."""
        self.ensure_one()
        self.write({'sync_status': 'pending'})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Push Scheduled"),
                'message': _("Discount code '%s' queued for push to Shopify.") % self.code,
                'type': 'info',
                'sticky': False,
            },
        }
