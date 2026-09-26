# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class ShopifyPromoter(models.Model):
    _name = 'shopify.promoter'
    _description = 'Shopify Promoter'
    _inherit = ['mail.thread']
    _check_company_auto = True

    name = fields.Char(required=True)
    partner_id = fields.Many2one('res.partner', required=True, string='Contact')
    company_id = fields.Many2one(
        'res.company', required=True,
        default=lambda self: self.env.company,
    )
    code_prefix = fields.Char(help="Prefix for generated codes, e.g. JOHN")
    commission_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount per Order'),
    ], default='percentage', required=True)
    commission_rate = fields.Float(
        'Commission Rate',
        help="Percentage or fixed amount",
    )
    discount_code_ids = fields.One2many('shopify.discount.code', 'promoter_id')
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], default='active')
    notes = fields.Text()

    # Computed performance fields
    total_orders = fields.Integer(compute='_compute_performance', store=True)
    total_revenue = fields.Float(compute='_compute_performance', store=True)
    total_discount_given = fields.Float(compute='_compute_performance', store=True)
    total_commission = fields.Float(compute='_compute_performance', store=True)


    _unique_company_partner = models.Constraint(
        'UNIQUE(company_id, partner_id)',
        'A promoter already exists for this contact in this company.',
    )

    @api.depends(
        'discount_code_ids.usage_ids.order_total',
        'discount_code_ids.usage_ids.discount_amount',
        'discount_code_ids.usage_ids.commission_amount',
    )
    def _compute_performance(self):
        for rec in self:
            usages = rec.mapped('discount_code_ids.usage_ids')
            rec.total_orders = len(usages)
            rec.total_revenue = sum(usages.mapped('order_total'))
            rec.total_discount_given = sum(usages.mapped('discount_amount'))
            rec.total_commission = sum(usages.mapped('commission_amount'))

    def action_dummy(self):
        """Placeholder for stat button clicks."""
        pass
