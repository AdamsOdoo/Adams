import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ShopifySyncWizard(models.TransientModel):
    _name = 'shopify.sync.wizard'
    _description = 'Shopify Sync Now Wizard'

    backend_id = fields.Many2one(
        'shopify.backend', string='Store', required=True,
        domain=[('state', '=', 'connected')],
    )
    sync_products = fields.Boolean('Products', default=True)
    sync_customers = fields.Boolean('Customers', default=True)
    sync_orders = fields.Boolean('Orders', default=True)
    sync_inventory = fields.Boolean('Inventory', default=True)
    direction = fields.Selection([
        ('export', 'Export (Odoo → Shopify)'),
        ('import', 'Import (Shopify → Odoo)'),
        ('both', 'Both Directions'),
    ], default='both', required=True)
    force_full_sync = fields.Boolean(
        'Force Full Sync',
        help="Ignore checksums and re-sync all records.",
    )

    def action_sync(self):
        """Execute the sync based on wizard configuration."""
        self.ensure_one()
        backend = self.backend_id

        if backend.state != 'connected':
            raise UserError(_("Store is not connected. Please test connection first."))

        results = []

        if self.sync_products:
            if self.direction in ('import', 'both'):
                self.env['shopify.product.binding'].with_company(
                    backend.company_id
                ).run_sync(backend)
                results.append(_("Products synced"))

        if self.sync_customers:
            if self.direction in ('import', 'both'):
                self.env['shopify.customer.binding'].with_company(
                    backend.company_id
                ).run_import(backend)
                results.append(_("Customers imported"))

        if self.sync_orders:
            if self.direction in ('import', 'both'):
                self.env['shopify.order.binding'].with_company(
                    backend.company_id
                ).run_import(backend)
                results.append(_("Orders imported"))

        if self.sync_inventory:
            if self.direction in ('export', 'both'):
                self.env['shopify.inventory.binding'].with_company(
                    backend.company_id
                ).run_export(backend)
                results.append(_("Inventory pushed"))

        backend.last_sync_date = fields.Datetime.now()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Sync Complete"),
                'message': ', '.join(results) if results else _("No sync operations selected."),
                'type': 'success',
                'sticky': False,
            },
        }
