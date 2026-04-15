# Part of Adams Shopify Connector. See LICENSE file for full copyright and licensing details.
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
            if move.move_type == 'out_invoice':
                self._shopify_reverse_sync_payment(move)
            elif move.move_type == 'out_refund':
                self._shopify_reverse_sync_refund(move)
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

    def _shopify_reverse_sync_refund(self, move):
        """When a credit note is posted for a Shopify order and
        reverse_sync_refund is enabled, create a refund on Shopify."""
        # Find linked sale orders via the reversed invoice
        reversed_move = move.reversed_entry_id
        if reversed_move:
            sale_orders = reversed_move.line_ids.sale_line_ids.order_id
        else:
            sale_orders = move.line_ids.sale_line_ids.order_id
        if not sale_orders:
            return

        for order in sale_orders:
            if order.sales_channel != 'shopify':
                continue
            for binding in order.shopify_bind_ids:
                if not binding.shopify_id:
                    continue
                backend = binding.backend_id
                if backend.state != 'connected':
                    continue
                if not backend.reverse_sync_refund:
                    continue

                try:
                    from ..shopify_api.client import ShopifyClient
                    from ..shopify_api.queries.refund import REFUND_CREATE
                    client = ShopifyClient(backend)

                    refund_amount = abs(move.amount_total)
                    currency_code = move.currency_id.name or 'USD'

                    refund_input = {
                        'orderId': binding.shopify_id,
                        'note': move.ref or f"Odoo Credit Note {move.name}",
                        'shipping': {'amount': 0, 'fullRefund': False},
                        'transactions': [{
                            'amount': refund_amount,
                            'gateway': 'manual',
                            'kind': 'REFUND',
                            'orderId': binding.shopify_id,
                        }],
                    }
                    client.execute_mutation(
                        REFUND_CREATE,
                        {'input': refund_input},
                        result_key='refundCreate',
                        estimated_cost=10,
                    )
                    _logger.info(
                        "Created Shopify refund for order %s "
                        "(reverse sync from credit note %s, amount: %s %s)",
                        binding.shopify_order_name, move.name,
                        refund_amount, currency_code,
                    )
                except Exception as e:
                    _logger.warning(
                        "Failed to create Shopify refund for order %s: %s",
                        binding.shopify_order_name, e,
                    )
