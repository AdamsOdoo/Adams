# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Simulated Shopify Collection model.

Collections group products and are returned by the FETCH_COLLECTIONS query.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyCollection(models.Model):
    _name = 'sim.shopify.collection'
    _description = 'Simulated Shopify Collection'
    _order = 'title asc, id asc'
    _rec_name = 'title'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    title = fields.Char(string='Title', required=True)
    handle = fields.Char(
        string='Handle',
        help='URL-safe handle, e.g. "summer-collection".',
    )
    description_html = fields.Text(string='Description (HTML)')
    sort_order = fields.Selection([
        ('ALPHA_ASC', 'Alphabetically A-Z'),
        ('ALPHA_DESC', 'Alphabetically Z-A'),
        ('BEST_SELLING', 'Best Selling'),
        ('CREATED', 'Date Created (Oldest)'),
        ('CREATED_DESC', 'Date Created (Newest)'),
        ('MANUAL', 'Manual'),
        ('PRICE_ASC', 'Price Low to High'),
        ('PRICE_DESC', 'Price High to Low'),
    ], default='MANUAL', string='Sort Order')
    collection_type = fields.Selection([
        ('custom', 'Custom (Manual)'),
        ('smart', 'Smart (Automated)'),
    ], default='custom', string='Collection Type')

    product_ids = fields.Many2many(
        'sim.shopify.product', 'sim_collection_product_rel',
        'collection_id', 'product_id',
        string='Products',
    )
    product_count = fields.Integer(
        compute='_compute_product_count', string='Products Count', store=True,
    )

    image_url = fields.Char(string='Image URL')
    published = fields.Boolean(default=True, string='Published')
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    updated_at = fields.Datetime(default=fields.Datetime.now)

    @api.depends('product_ids')
    def _compute_product_count(self):
        for rec in self:
            rec.product_count = len(rec.product_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.shopify_gid:
                rec.shopify_gid = rec.config_id._next_gid('Collection')
            if not rec.handle and rec.title:
                rec.handle = rec.title.lower().replace(' ', '-').replace("'", '')
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'title' in vals or 'product_ids' in vals:
            for rec in self:
                rec.updated_at = fields.Datetime.now()
        return res

    def _to_graphql_node(self):
        """Build GraphQL node for collection."""
        return {
            'id': self.shopify_gid,
            'title': self.title,
            'handle': self.handle or '',
            'descriptionHtml': self.description_html or '',
            'sortOrder': self.sort_order or 'MANUAL',
            'productsCount': {'count': self.product_count},
            'image': {'url': self.image_url} if self.image_url else None,
            'updatedAt': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }
