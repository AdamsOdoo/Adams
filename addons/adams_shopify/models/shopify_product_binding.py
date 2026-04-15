# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ShopifyProductBinding(models.Model):
    _name = 'shopify.product.binding'
    _inherit = 'shopify.binding'
    _description = 'Shopify Product Binding'

    odoo_id = fields.Many2one(
        'product.template', string='Odoo Product',
        required=True, ondelete='cascade', index=True,
    )
    shopify_handle = fields.Char('Shopify Handle')
    shopify_product_type = fields.Char('Shopify Product Type')
    shopify_status = fields.Selection([
        ('active', 'Active'),
        ('archived', 'Archived'),
        ('draft', 'Draft'),
    ], string='Shopify Status')
    variant_binding_ids = fields.One2many(
        'shopify.variant.binding', 'product_binding_id',
        string='Variant Bindings',
    )
    shopify_tags = fields.Char('Shopify Tags')
    no_sync = fields.Boolean(
        'Do Not Sync',
        help="If checked, this product will be excluded from synchronization.",
    )
    shopify_url = fields.Char('Shopify URL', compute='_compute_shopify_url')

    @api.depends('shopify_id', 'backend_id.shop_url')
    def _compute_shopify_url(self):
        for rec in self:
            if rec.shopify_id and rec.backend_id.shop_url:
                # Extract numeric ID from GID
                numeric_id = rec.shopify_id.split('/')[-1] if rec.shopify_id else ''
                base = rec.backend_id.shop_url.rstrip('/')
                if not base.startswith('https://'):
                    base = f"https://{base}"
                rec.shopify_url = f"{base}/admin/products/{numeric_id}"
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
         'A binding already exists for this Shopify product.'),
        ('unique_backend_odoo',
         'UNIQUE(backend_id, odoo_id)',
         'This Odoo product is already linked to this Shopify store.'),
    ]

    @api.model
    def run_sync(self, backend):
        """Run product sync based on backend direction setting."""
        from ..sync.product_sync import ProductSync
        syncer = ProductSync(self.env, backend)
        direction = backend.product_sync_direction
        if direction in ('import', 'both'):
            syncer.import_products()
        if direction in ('export', 'both'):
            syncer.export_products()

    @api.model
    def process_webhook_event(self, backend, data, topic):
        """Process an incoming product webhook."""
        from ..sync.product_sync import ProductSync
        syncer = ProductSync(self.env, backend)
        syncer.import_single_product(data)
