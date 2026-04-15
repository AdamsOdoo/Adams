# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class ShopifyOrderBindingCancel(models.Model):
    """Adds cancellation tracking fields to shopify.order.binding."""
    _inherit = 'shopify.order.binding'

    shopify_cancelled_at = fields.Datetime('Cancelled At')
    cancel_reason = fields.Selection([
        ('customer', 'Customer Changed Mind'),
        ('fraud', 'Fraudulent Order'),
        ('inventory', 'Items Unavailable'),
        ('declined', 'Payment Declined'),
        ('other', 'Other'),
    ], string='Cancel Reason')

    def action_cancel_in_odoo(self):
        """Cancel the linked Odoo sale order when Shopify order is cancelled."""
        self.ensure_one()
        order = self.odoo_id
        if not order or order.state == 'cancel':
            return
        if order.state in ('draft', 'sent'):
            order.action_cancel()
        elif order.state == 'sale':
            try:
                order.with_context(disable_cancel_warning=True).action_cancel()
            except Exception as e:
                _logger.warning("Could not auto-cancel order %s: %s", order.name, e)
                order.message_post(
                    body=_("Shopify order cancelled but Odoo cancellation failed: %s") % str(e),
                    message_type='notification',
                )
