import logging
from odoo import api, models

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()
        # After successful validation, check if this is a delivery for a Shopify order
        for picking in self:
            if picking.picking_type_code != 'outgoing':
                continue
            if picking.state != 'done':
                continue
            sale_order = picking.sale_id
            if not sale_order:
                continue
            shopify_bindings = sale_order.shopify_bind_ids
            for binding in shopify_bindings:
                if binding.shopify_id and binding.backend_id.state == 'connected':
                    try:
                        from ..sync.fulfillment_sync import FulfillmentSync
                        syncer = FulfillmentSync(self.env, binding.backend_id)
                        syncer.push_fulfillment(
                            binding,
                            tracking_number=picking.carrier_tracking_ref or '',
                            tracking_company=picking.carrier_id.name if picking.carrier_id else '',
                        )
                        _logger.info("Fulfillment pushed for order %s", sale_order.name)
                    except Exception as e:
                        _logger.warning("Failed to push fulfillment for %s: %s", sale_order.name, e)
        return res
