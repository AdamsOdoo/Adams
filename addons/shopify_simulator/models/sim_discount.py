# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Simulated Shopify Discount Code and Discount Usage models.

Discount codes are returned by the codeDiscountNodes query and
managed via discountCodeBasicCreate/Update mutations.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyDiscountCode(models.Model):
    _name = 'sim.shopify.discount.code'
    _description = 'Simulated Shopify Discount Code'
    _order = 'code asc'
    _rec_name = 'code'

    _unique_code = models.Constraint(
        'UNIQUE(config_id, code)',
        'Discount code must be unique per config.',
    )

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)

    code = fields.Char(string='Code', required=True)
    title = fields.Char(
        string='Title',
        help='Internal title for this discount (not shown to customers).',
    )
    discount_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed_amount', 'Fixed Amount'),
        ('free_shipping', 'Free Shipping'),
    ], required=True, default='percentage', string='Discount Type')
    discount_value = fields.Float(
        string='Value',
        help='The discount value: e.g. 10 for 10%% or $10.',
    )
    minimum_order_amount = fields.Float(
        string='Minimum Order', default=0.0,
    )
    usage_limit = fields.Integer(
        string='Usage Limit', default=0,
        help='0 = unlimited.',
    )
    one_per_customer = fields.Boolean(
        string='Once Per Customer', default=False,
    )
    starts_at = fields.Datetime(
        string='Starts At', default=fields.Datetime.now,
    )
    ends_at = fields.Datetime(string='Ends At')
    active_on_shopify = fields.Boolean(
        string='Active', default=True,
    )
    usage_count = fields.Integer(
        compute='_compute_usage_count', string='Times Used', store=True,
    )
    usage_ids = fields.One2many(
        'sim.shopify.discount.usage', 'discount_code_id',
        string='Usage Records',
    )

    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now)

    @api.depends('usage_ids')
    def _compute_usage_count(self):
        for rec in self:
            rec.usage_count = len(rec.usage_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.shopify_gid:
                rec.shopify_gid = rec.config_id._next_gid('DiscountCodeNode')
            if not rec.title:
                rec.title = rec.code
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('code', 'discount_type', 'discount_value',
                                    'active_on_shopify', 'ends_at')):
            for rec in self:
                rec.updated_at = fields.Datetime.now()
        return res

    def _to_graphql_node(self):
        """Build GraphQL node for discount code (codeDiscountNode shape)."""
        # Shopify wraps discount codes in a codeDiscount union type
        value_node = {}
        if self.discount_type == 'percentage':
            value_node = {
                '__typename': 'DiscountPercentage',
                'percentage': self.discount_value,
            }
        elif self.discount_type == 'fixed_amount':
            value_node = {
                '__typename': 'DiscountAmount',
                'amount': {
                    'amount': str(self.discount_value),
                    'currencyCode': self.config_id.currency_code or 'USD',
                },
            }
        elif self.discount_type == 'free_shipping':
            value_node = {
                '__typename': 'DiscountOnFreeShipping',
            }

        return {
            'id': self.shopify_gid,
            'codeDiscount': {
                '__typename': 'DiscountCodeBasic' if self.discount_type != 'free_shipping'
                              else 'DiscountCodeFreeShipping',
                'title': self.title or self.code,
                'status': 'ACTIVE' if self.active_on_shopify else 'EXPIRED',
                'codes': {
                    'edges': [{
                        'node': {'code': self.code},
                    }],
                },
                'startsAt': self.starts_at.isoformat() + 'Z' if self.starts_at else None,
                'endsAt': self.ends_at.isoformat() + 'Z' if self.ends_at else None,
                'usageLimit': self.usage_limit if self.usage_limit > 0 else None,
                'asyncUsageCount': self.usage_count,
                'customerSelection': {
                    '__typename': 'DiscountCustomerAll',
                },
                'customerGets': {
                    'value': value_node,
                },
                'appliesOncePerCustomer': self.one_per_customer,
                'minimumRequirement': {
                    '__typename': 'DiscountMinimumSubtotal',
                    'greaterThanOrEqualToSubtotal': {
                        'amount': str(self.minimum_order_amount),
                        'currencyCode': self.config_id.currency_code or 'USD',
                    },
                } if self.minimum_order_amount > 0 else {
                    '__typename': 'DiscountMinimumQuantity',
                    'greaterThanOrEqualToQuantity': '0',
                },
            },
        }


class SimShopifyDiscountUsage(models.Model):
    _name = 'sim.shopify.discount.usage'
    _description = 'Simulated Shopify Discount Code Usage'
    _order = 'date desc'

    discount_code_id = fields.Many2one(
        'sim.shopify.discount.code', required=True, ondelete='cascade',
        string='Discount Code', index=True,
    )
    config_id = fields.Many2one(
        related='discount_code_id.config_id', store=True, index=True,
    )
    order_gid = fields.Char(string='Order GID')
    discount_amount = fields.Float(string='Discount Amount')
    order_total = fields.Float(string='Order Total')
    date = fields.Datetime(
        string='Used At', default=fields.Datetime.now,
    )
