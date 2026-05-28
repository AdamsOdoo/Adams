# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class ShopifyBulkExportWizard(models.TransientModel):
    _name = 'shopify.bulk.export.wizard'
    _description = 'Shopify Bulk Export Wizard'

    backend_id = fields.Many2one(
        'shopify.backend', string='Shopify Store', required=True,
        domain="[('state', '=', 'connected')]",
    )
    entity = fields.Selection([
        ('product', 'Products'),
        ('customer', 'Customers'),
        ('inventory', 'Inventory'),
        ('discount', 'Discount Codes'),
    ], required=True, default='product')

    product_domain = fields.Selection([
        ('all', 'All Products'),
        ('unlinked', 'Not Yet on Shopify'),
        ('modified', 'Modified Since Last Sync'),
    ], default='unlinked', string='Product Filter')

    customer_domain = fields.Selection([
        ('all', 'All Customers'),
        ('unlinked', 'Not Yet on Shopify'),
    ], default='unlinked', string='Customer Filter')

    limit = fields.Integer('Max Records', default=100,
        help="Maximum number of records to export in this batch. 0 = no limit.")

    def action_export(self):
        """Run the bulk export."""
        self.ensure_one()
        backend = self.backend_id

        if self.entity == 'product':
            return self._export_products(backend)
        elif self.entity == 'customer':
            return self._export_customers(backend)
        elif self.entity == 'inventory':
            return self._export_inventory(backend)
        elif self.entity == 'discount':
            return self._export_discounts(backend)

    def _export_products(self, backend):
        from ..sync.product_sync import ProductSync
        syncer = ProductSync(self.with_company(backend.company_id).env, backend)

        if self.product_domain == 'unlinked':
            existing_ids = self.env['shopify.product.binding'].search([
                ('backend_id', '=', backend.id),
            ]).mapped('odoo_id').ids
            domain = [('id', 'not in', existing_ids)]
            products = self.env['product.template'].search(
                domain, limit=self.limit or None,
            )
            for product in products:
                self.env['shopify.product.binding'].create({
                    'backend_id': backend.id,
                    'odoo_id': product.id,
                    'sync_status': 'pending',
                })

        result = syncer.export_products()
        return self._show_result('Products', result)

    def _export_customers(self, backend):
        from ..sync.customer_sync import CustomerSync
        syncer = CustomerSync(self.with_company(backend.company_id).env, backend)

        if self.customer_domain == 'unlinked':
            existing_ids = self.env['shopify.customer.binding'].search([
                ('backend_id', '=', backend.id),
            ]).mapped('odoo_id').ids
            domain = [
                ('id', 'not in', existing_ids),
                ('customer_rank', '>', 0),
                ('parent_id', '=', False),
            ]
            partners = self.env['res.partner'].search(
                domain, limit=self.limit or None,
            )
            for partner in partners:
                self.env['shopify.customer.binding'].create({
                    'backend_id': backend.id,
                    'odoo_id': partner.id,
                    'sync_status': 'pending',
                })

        result = syncer.export_customers()
        return self._show_result('Customers', result)

    def _export_inventory(self, backend):
        from ..sync.inventory_sync import InventorySync
        syncer = InventorySync(self.with_company(backend.company_id).env, backend)
        result = syncer.export_inventory(backend)
        return self._show_result('Inventory', result)

    def _export_discounts(self, backend):
        from ..sync.discount_sync import DiscountSync
        syncer = DiscountSync(self.with_company(backend.company_id).env, backend)
        result = syncer.export_discounts()
        return self._show_result('Discounts', result)

    def _show_result(self, entity, result):
        success, errors, skipped = result
        msg = _(
            "%(entity)s export complete: %(success)d succeeded, "
            "%(errors)d errors, %(skipped)d skipped.",
            entity=entity, success=success, errors=errors, skipped=skipped,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Export Complete"),
                'message': msg,
                'type': 'success' if not errors else 'warning',
                'sticky': False,
            },
        }
