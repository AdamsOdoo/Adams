import logging

from odoo import models

_logger = logging.getLogger(__name__)

# Post-fulfillment tracking-change trigger fields (stock_delivery).
_TRACKING_TRIGGER_FIELDS = frozenset((
    'carrier_tracking_ref', 'carrier_tracking_url', 'carrier_id',
))


class ShopifyConnectorStockPickingFulfillment(models.Model):
    """Seam: stock.picking — the odoo_event trigger surface (D-014-3).

    `_action_done` enqueues a once-per-validation fulfillment admission for an
    eligible outbound customer delivery (adopting the sale_stock-created
    picking, Q2 — never creating a parallel delivery). A post-fulfillment
    tracking change on a bound picking enqueues a tracking admission. Trigger
    failures never mask the authoritative Odoo stock operation."""

    _inherit = 'stock.picking'

    def _action_done(self, *args, **kwargs):
        result = super()._action_done(*args, **kwargs)
        Service = self.env['shopify.connector.fulfillment.service']
        for picking in self:
            if picking._is_fulfillment_admission_eligible():
                try:
                    Service._enqueue_picking_admission(picking)
                except Exception:
                    # The expected `(store, operation_scope_key)` collision is
                    # already handled inside `_enqueue_once` itself (returns
                    # the existing job). Anything reaching here is genuinely
                    # unexpected: log it durably, then re-raise so the whole
                    # validation transaction rolls back atomically. Never
                    # silently preserve the picking after an unexpected
                    # enqueue-hook failure.
                    _logger.exception(
                        'Unexpected failure enqueuing a fulfillment picking '
                        'admission after validating picking %d; the '
                        'validation transaction is rolled back atomically.',
                        picking.id,
                    )
                    raise
        return result

    def _is_fulfillment_admission_eligible(self):
        """D-014-3: only the final customer-bound outgoing leg of an imported
        order qualifies; each backorder picking is its own independent event."""
        self.ensure_one()
        return bool(
            self.picking_type_code == 'outgoing'
            and self.location_dest_id.usage == 'customer'
            and self.state == 'done'
            and self.sale_id
        )

    def write(self, vals):
        tracking_changed = bool(set(vals) & _TRACKING_TRIGGER_FIELDS)
        result = super().write(vals)
        if tracking_changed:
            Service = self.env['shopify.connector.fulfillment.service']
            Binding = self.env['shopify.connector.fulfillment.binding']
            for picking in self:
                binding = Binding.search(
                    [('picking_id', '=', picking.id)], limit=1,
                )
                if binding:
                    try:
                        Service._enqueue_tracking_admission(binding)
                    except Exception:
                        # See _action_done: the expected operation-scope
                        # collision is already handled inside `_enqueue_once`.
                        # An unexpected failure here is logged durably and
                        # re-raised so the whole write transaction rolls back
                        # atomically -- never silently preserved.
                        _logger.exception(
                            'Unexpected failure enqueuing a fulfillment '
                            'tracking admission after writing picking %d; '
                            'the picking write is rolled back atomically.',
                            picking.id,
                        )
                        raise
        return result
