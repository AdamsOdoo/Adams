import logging

from odoo import models

_logger = logging.getLogger(__name__)

ORDER_MARK_AS_PAID = """
mutation OrderMarkAsPaid($input: OrderMarkAsPaidInput!) {
  orderMarkAsPaid(input: $input) {
    order {
      id
      displayFinancialStatus
    }
    userErrors {
      field
      message
    }
  }
}
"""


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_post(self):
        res = super().action_post()
        # Skip if triggered by Shopify inbound sync (prevent loop)
        if self.env.context.get('shopify_no_auto_export'):
            return res
        for move in self:
            if move.move_type != 'out_invoice':
                continue
            self._shopify_reverse_sync_payment(move)
        return res

    def _shopify_reverse_sync_payment(self, move):
        """If this invoice belongs to a Shopify order with pending/authorized
        status and reverse sync is enabled, mark it as paid on Shopify."""
        # Find the sale order(s) linked to this invoice
        sale_orders = move.line_ids.sale_line_ids.order_id
        for order in sale_orders:
            if order.sales_channel != 'shopify':
                continue
            for binding in order.shopify_bind_ids:
                if not binding.shopify_id:
                    continue
                backend = binding.backend_id
                if backend.state != 'connected':
                    continue
                if not backend.reverse_sync_payment:
                    continue
                if binding.shopify_financial_status not in ('pending', 'authorized'):
                    continue

                try:
                    from ..shopify_api.client import ShopifyClient
                    client = ShopifyClient(backend)
                    client.execute_mutation(
                        ORDER_MARK_AS_PAID,
                        {'input': {'id': binding.shopify_id}},
                        result_key='orderMarkAsPaid',
                        estimated_cost=10,
                    )
                    binding.write({'shopify_financial_status': 'paid'})
                    order.with_context(shopify_no_auto_export=True).write({
                        'shopify_financial_status': 'paid',
                    })
                    _logger.info(
                        "Marked Shopify order %s as paid (reverse sync from invoice %s)",
                        binding.shopify_order_name, move.name,
                    )
                except Exception as e:
                    _logger.warning(
                        "Failed to mark Shopify order %s as paid: %s",
                        binding.shopify_order_name, e,
                    )
