# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ShopifyMetafield(models.Model):
    _name = 'shopify.metafield'
    _description = 'Shopify Metafield'
    _rec_name = 'display_name'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    owner_type = fields.Selection([
        ('product', 'Product'),
        ('variant', 'Variant'),
        ('customer', 'Customer'),
        ('order', 'Order'),
    ], required=True, index=True)
    owner_binding_id = fields.Integer('Owner Binding ID', index=True,
        help="ID of the binding record that owns this metafield.")
    shopify_metafield_id = fields.Char('Shopify Metafield ID', index=True)

    namespace = fields.Char('Namespace', required=True)
    key = fields.Char('Key', required=True)
    value = fields.Text('Value')
    metafield_type = fields.Char('Type',
        help="Shopify metafield type (e.g. single_line_text_field, number_integer).")

    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('namespace', 'key')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.namespace}.{rec.key}"

    _sql_constraints = [
        ('unique_metafield', 'UNIQUE(backend_id, owner_type, owner_binding_id, namespace, key)',
         'Metafield already exists for this owner.'),
    ]
