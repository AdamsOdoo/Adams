# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
import logging

from odoo import _, models

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
            if not order.shopify_reverse_sync:
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
                    client = backend._make_api_client()
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
            if not order.shopify_reverse_sync:
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
                    from ..shopify_api.queries.refund import REFUND_CREATE
                    client = backend._make_api_client()

                    # Shopify expects the amount in the order's own currency.
                    # The credit note may be in a different currency (e.g. company
                    # books in EUR but the Shopify order was captured in USD), so
                    # convert when necessary.
                    order_currency = order.currency_id
                    if move.currency_id and move.currency_id != order_currency:
                        refund_amount = move.currency_id._convert(
                            abs(move.amount_total),
                            order_currency,
                            backend.company_id,
                            move.date,
                        )
                    else:
                        refund_amount = abs(move.amount_total)
                    currency_code = order_currency.name

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

    def button_cancel(self):
        """Override to warn when a Shopify-linked invoice is cancelled."""
        # Collect Shopify-linked posted invoices BEFORE cancel changes state
        shopify_moves = {}
        for move in self:
            if move.state != 'posted' or move.move_type not in ('out_invoice', 'out_refund'):
                continue
            sale_orders = move.line_ids.sale_line_ids.order_id
            for order in sale_orders:
                if order.sales_channel != 'shopify' and not order.shopify_bind_ids:
                    continue
                for binding in order.shopify_bind_ids:
                    if binding.shopify_order_name:
                        shopify_moves[move.id] = (order, binding.shopify_order_name)
                        break

        res = super().button_cancel()

        # Schedule warning activities for Shopify-linked cancellations
        activity_type = self.env.ref('mail.mail_activity_data_warning', raise_if_not_found=False)
        for _move_id, (order, order_name) in shopify_moves.items():
            order.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_("Shopify financial status may be out of sync"),
                note=_(
                    "An invoice linked to Shopify order %(order_name)s was cancelled in "
                    "Odoo, but Shopify still shows the original payment status. If a "
                    "refund is needed, create a credit note and post it — the connector "
                    "will create the refund on Shopify automatically (if reverse sync is "
                    "enabled). If this was an accounting correction only, dismiss this "
                    "activity.",
                    order_name=order_name,
                ),
                user_id=self.env.uid,
            )
        return res
