# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Simulated Shopify Metafield model.

Metafields store custom key-value data on products, variants, customers, orders.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyMetafield(models.Model):
    _name = 'sim.shopify.metafield'
    _description = 'Simulated Shopify Metafield'
    _order = 'namespace, key'
    _rec_name = 'display_name'

    _unique_owner_ns_key = models.Constraint(
        'UNIQUE(config_id, owner_type, owner_gid, namespace, key)',
        'Metafield namespace+key must be unique per owner.',
    )

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)

    owner_type = fields.Selection([
        ('PRODUCT', 'Product'),
        ('PRODUCTVARIANT', 'Product Variant'),
        ('CUSTOMER', 'Customer'),
        ('ORDER', 'Order'),
    ], required=True, string='Owner Type', index=True)
    owner_gid = fields.Char(
        string='Owner GID', required=True, index=True,
        help='Shopify GID of the resource that owns this metafield.',
    )

    namespace = fields.Char(string='Namespace', required=True)
    key = fields.Char(string='Key', required=True)
    value = fields.Text(string='Value')
    metafield_type = fields.Char(
        string='Type', default='single_line_text_field',
        help='Shopify metafield type: single_line_text_field, number_integer, '
             'json, boolean, url, etc.',
    )
    display_name = fields.Char(
        compute='_compute_display_name', store=True, string='Display Name',
    )

    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now)

    @api.depends('namespace', 'key')
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f'{rec.namespace}.{rec.key}' if rec.namespace else rec.key or ''

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.shopify_gid:
                rec.shopify_gid = rec.config_id._next_gid('Metafield')
        return records

    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ('value', 'metafield_type')):
            for rec in self:
                rec.updated_at = fields.Datetime.now()
        return res

    def _to_graphql_node(self):
        """Build GraphQL node for metafield."""
        return {
            'id': self.shopify_gid,
            'namespace': self.namespace,
            'key': self.key,
            'value': self.value or '',
            'type': self.metafield_type or 'single_line_text_field',
            'ownerType': self.owner_type,
            'createdAt': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }
