import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        if self.env.context.get('shopify_no_inventory_push'):
            return res
        # Collect products that moved and push inventory for their Shopify bindings
        product_ids = res.mapped('product_id').ids
        if not product_ids:
            return res
        variant_bindings = self.env['shopify.variant.binding'].search([
            ('odoo_id', 'in', product_ids),
            ('shopify_inventory_item_id', '!=', False),
            ('sync_status', '=', 'synced'),
        ])
        # Group by backend and mark for push
        backends_seen = set()
        for vb in variant_bindings:
            backend = vb.backend_id
            if backend.state == 'connected' and backend.auto_sync_inventory:
                backends_seen.add(backend.id)
        # Trigger inventory push for affected backends
        for backend_id in backends_seen:
            backend = self.env['shopify.backend'].browse(backend_id)
            try:
                self.env['shopify.inventory.binding'].with_company(
                    backend.company_id
                ).run_export(backend)
            except Exception as e:
                _logger.warning("Real-time inventory push failed for backend %s: %s", backend_id, e)
        return res
