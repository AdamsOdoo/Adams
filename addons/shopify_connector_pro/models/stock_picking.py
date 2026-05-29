# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        # Skip if triggered by inbound Shopify fulfillment sync (prevent loop)
        if self.env.context.get('shopify_no_auto_export'):
            return res
        for picking in self:
            if picking.state != 'done':
                continue
            sale_order = picking.sale_id
            if not sale_order:
                continue
            # B2B guard: only sync Shopify-channel orders
            if sale_order.sales_channel != 'shopify':
                continue
            if not sale_order.shopify_reverse_sync:
                continue
            if picking.picking_type_code == 'outgoing':
                self._push_outbound_fulfillment(picking, sale_order)
            elif picking.picking_type_code == 'incoming':
                # Return picking — check if it's a return for a Shopify order
                self._push_return_restock(picking, sale_order)
        return res

    def _push_outbound_fulfillment(self, picking, sale_order):
        """Push fulfillment to Shopify when outgoing picking is validated."""
        for binding in sale_order.shopify_bind_ids:
            if not binding.shopify_id or binding.backend_id.state != 'connected':
                continue
            try:
                from ..sync.fulfillment_sync import FulfillmentSync
                syncer = FulfillmentSync(self.env, binding.backend_id)
                syncer.push_fulfillment(
                    binding,
                    picking=picking,
                    tracking_number=picking.carrier_tracking_ref or '',
                    tracking_company=(
                        picking.carrier_id.name if picking.carrier_id else ''
                    ),
                )
                _logger.info(
                    "Fulfillment pushed for order %s (picking %s)",
                    sale_order.name, picking.name,
                )
            except Exception as e:
                _logger.warning(
                    "Failed to push fulfillment for %s: %s",
                    sale_order.name, e,
                )

    def _push_return_restock(self, picking, sale_order):
        """Notify Shopify about a return when reverse_sync_refund is enabled.

        Note: actual Shopify refund creation is separate (handled by
        account.move credit note reverse sync). This just logs the event.
        """
        for binding in sale_order.shopify_bind_ids:
            if not binding.shopify_id or binding.backend_id.state != 'connected':
                continue
            if not binding.backend_id.reverse_sync_refund:
                continue
            _logger.info(
                "Return picking %s validated for Shopify order %s — "
                "credit note reverse sync will handle Shopify refund if enabled",
                picking.name, sale_order.name,
            )
