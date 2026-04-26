# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ShopifyImportWizard(models.TransientModel):
    _name = 'shopify.import.wizard'
    _description = 'Shopify Initial Import Wizard'

    backend_id = fields.Many2one(
        'shopify.backend', string='Store', required=True,
        domain=[('state', '=', 'connected')],
    )
    import_products = fields.Boolean('Products', default=True)
    import_customers = fields.Boolean('Customers', default=True)
    import_orders = fields.Boolean('Orders', default=True)
    order_days = fields.Integer(
        'Import Orders from Last N Days', default=60,
    )

    def action_import(self):
        """Run initial bulk import from Shopify."""
        self.ensure_one()
        backend = self.backend_id

        if backend.state != 'connected':
            raise UserError(_("Store is not connected. Please test connection first."))

        results = []

        if self.import_products:
            try:
                self.env['shopify.product.binding'].with_company(
                    backend.company_id
                ).run_sync(backend)
                results.append(_("Products imported"))
            except Exception as e:
                _logger.exception("Product import failed")
                results.append(_("Product import failed: %s") % str(e))

        if self.import_customers:
            try:
                self.env['shopify.customer.binding'].with_company(
                    backend.company_id
                ).run_import(backend)
                results.append(_("Customers imported"))
            except Exception as e:
                _logger.exception("Customer import failed")
                results.append(_("Customer import failed: %s") % str(e))

        if self.import_orders:
            try:
                self.env['shopify.order.binding'].with_company(
                    backend.company_id
                ).run_import(backend)
                results.append(_("Orders imported"))
            except Exception as e:
                _logger.exception("Order import failed")
                results.append(_("Order import failed: %s") % str(e))

        backend.last_sync_date = fields.Datetime.now()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Import Complete"),
                'message': '\n'.join(results),
                'type': 'success',
                'sticky': True,
            },
        }
