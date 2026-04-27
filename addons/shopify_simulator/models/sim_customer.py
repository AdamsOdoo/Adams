# Part of Shopify Simulator. Internal QA tool — not for public distribution.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyCustomer(models.Model):
    _name = 'sim.shopify.customer'
    _description = 'Simulated Shopify Customer'
    _order = 'create_date desc, id desc'
    _rec_name = 'display_name'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    first_name = fields.Char()
    last_name = fields.Char()
    email = fields.Char()
    phone = fields.Char()
    tags = fields.Char(help='Comma-separated tags')
    state = fields.Selection([
        ('DISABLED', 'Disabled'),
        ('ENABLED', 'Enabled'),
        ('INVITED', 'Invited'),
        ('DECLINED', 'Declined'),
    ], default='ENABLED')
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now)

    # Default address
    address1 = fields.Char(string='Street')
    address2 = fields.Char(string='Street 2')
    city = fields.Char()
    province = fields.Char()
    province_code = fields.Char()
    country = fields.Char()
    country_code = fields.Char(default='US')
    zip_code = fields.Char(string='ZIP')
    company_name = fields.Char(string='Company')

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('first_name', 'last_name', 'email')
    def _compute_display_name(self):
        for rec in self:
            parts = [rec.first_name or '', rec.last_name or '']
            name = ' '.join(p for p in parts if p)
            rec.display_name = name or rec.email or f'Customer #{rec.id}'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            config = self.env['sim.shopify.config'].browse(vals.get('config_id'))
            if config and not vals.get('shopify_gid'):
                vals['shopify_gid'] = config._next_gid('Customer')
        return super().create(vals_list)

    def write(self, vals):
        if 'updated_at' not in vals:
            vals['updated_at'] = fields.Datetime.now()
        return super().write(vals)

    def _to_graphql_node(self):
        """Return dict matching Shopify FETCH_CUSTOMERS GraphQL response shape."""
        self.ensure_one()
        default_address = None
        if self.address1 or self.city or self.country_code:
            default_address = {
                'address1': self.address1 or '',
                'address2': self.address2 or '',
                'city': self.city or '',
                'province': self.province or '',
                'provinceCode': self.province_code or '',
                'country': self.country or '',
                'countryCodeV2': self.country_code or '',
                'zip': self.zip_code or '',
                'company': self.company_name or '',
                'firstName': self.first_name or '',
                'lastName': self.last_name or '',
                'phone': self.phone or '',
            }
        addresses = [default_address] if default_address else []

        return {
            'id': self.shopify_gid,
            'firstName': self.first_name or '',
            'lastName': self.last_name or '',
            'email': self.email or '',
            'phone': self.phone or '',
            'tags': [t.strip() for t in (self.tags or '').split(',') if t.strip()],
            'state': self.state or 'ENABLED',
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else '',
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else '',
            'defaultAddress': default_address,
            'addresses': addresses,
        }
