from odoo import fields, models


class ShopifyCustomerTag(models.Model):
    _name = 'shopify.customer.tag'
    _description = 'Shopify Customer Tag'
    _rec_name = 'name'

    name = fields.Char('Tag Name', required=True, index=True)
    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    partner_ids = fields.Many2many(
        'res.partner', string='Customers',
        relation='shopify_customer_tag_partner_rel',
    )
    partner_count = fields.Integer(compute='_compute_partner_count')
    color = fields.Integer('Color')

    def _compute_partner_count(self):
        for rec in self:
            rec.partner_count = len(rec.partner_ids)

    _sql_constraints = [
        ('unique_backend_tag', 'UNIQUE(backend_id, name)',
         'Tag already exists for this store.'),
    ]
