from odoo.exceptions import UserError

from odoo import fields, models, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException


class AccountMove(models.Model):
    _inherit = "account.move"

    shopify_refund_id = fields.Char("Shopify Refund ID", copy=False, help="Refund ID of the Shopify.")
    shopify_return_id = fields.Many2one('shopify.return.ts', string="Shopify Return", copy=False, ondelete='set null',
                                        help="Set on credit notes linked to a Shopify return (via the return import side-effect).")

    def _compute_show_refund_shopify_button(self):
        user = self.env.user
        is_accounting_user = user.has_group('account.group_account_invoice')
        for move in self:
            show_refund_shopify_button = False
            order_id = move.line_ids.sale_line_ids.order_id
            if not move.is_refunded_in_mk and len(order_id) > 1 and 'shopify' in order_id.mapped("marketplace") and move.move_type == 'out_refund' and move.state == 'posted' and 'REFUNDED' not in order_id.mapped("shopify_financial_status"):
                show_refund_shopify_button = True
            elif len(order_id) == 1 and order_id.marketplace == 'shopify' and move.move_type == 'out_refund' and move.state == 'posted' and order_id.shopify_financial_status != 'REFUNDED' and not move.is_refunded_in_mk:
                show_refund_shopify_button = True
            move.show_refund_shopify_button = show_refund_shopify_button and is_accounting_user

    show_refund_shopify_button = fields.Boolean(compute="_compute_show_refund_shopify_button")

    def action_shopify_refund_register_payment(self):
        """Open the account.payment.register wizard or Shopify refund view based on payment status.

        This method checks if there is an outstanding amount to pay on the selected journal items.
        If so, it opens the 'Register Payment' form; otherwise, it opens the 'Shopify Refund' view.
        """
        self = self.sudo()
        order = self._get_order()
        order.mk_instance_id.connection_to_shopify()
        # Task: T8232 - Improve the refund error message for currency mismatches between Odoo and Shopify.
        payment_details = order.with_context(currency_name=order.currency_id.display_name).fetch_shopify_transactions_details(self.amount_total)
        total_remaining_amount = sum(payment_details.mapped('remaining_amount'))

        if round(total_remaining_amount, 2) == 0:
            order.shopify_financial_status = 'REFUNDED'

        if not self._can_register_payment():
            # Show the refund form if there's nothing left to pay
            return self._open_shopify_refund_view(order, total_remaining_amount, payment_details)

        # Open the 'Register Payment' form by default
        return self._open_register_payment_view(total_remaining_amount, payment_details)

    def _get_order(self):
        """Fetch the associated sales order from the journal entries."""
        order = self.sudo().line_ids.sale_line_ids.order_id
        if not order:
            raise MarketplaceException(_("No associated sales order found."))
        return order

    def _can_register_payment(self):
        """Check if there is anything left to pay on the journal entries."""
        try:
            self.env['account.payment.register'].sudo().with_context(active_model='account.move', active_ids=self.ids, lang='en_US').default_get(['line_ids'])
            return True
        except UserError as e:
            if "nothing left to pay" in e.args[0]:
                return False
            raise e

    def _open_shopify_refund_view(self, order, total_remaining_amount, payment_details):
        """
        Task: T7183 - Refund in Shopify not working when credit not paid already.
        Set a default reason in the refund wizard.

        Open the Shopify Refund view with pre-filled context.
        """
        view = self.sudo().env.ref('shopify.shopify_payment_refund_view_form_view_form')
        refund_description = self.sudo().ref
        return {
            'name': _('Shopify Refund'),
            'res_model': 'shopify.payment.refund',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_available_to_refund_amount': total_remaining_amount,
                'default_shopify_order_payment_ids': [(6, 0, payment_details.ids)],
                'default_company_id': order.company_id.id,
                'default_currency_id': order.currency_id.id,
                'default_refund_description': refund_description.split(",", 1)[1].strip() if refund_description and ',' in refund_description else ''
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

    def _open_register_payment_view(self, total_remaining_amount, payment_details):
        """
        Task: T7183 - Refund in Shopify not working when credit not paid already.
        Set a default reason in the register payment wizard.

        Open the Register Payment view with pre-filled context.
        """
        order_payment_journal_id = self.sudo().line_ids.sale_line_ids.order_id.order_workflow_id.journal_id
        view = self.sudo().env.ref('shopify.view_account_payment_register_form')
        refund_description = self.sudo().ref
        return {
            'name': _('Register Payment'),
            'res_model': 'account.payment.register',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'context': {
                'active_model': 'account.move',
                'active_ids': self.ids,
                'default_journal_id': order_payment_journal_id.id,
                'default_available_to_refund_amount': total_remaining_amount,
                'default_shopify_order_payment_ids': [(6, 0, payment_details.ids)],
                'default_refund_description': refund_description.split(",", 1)[1].strip() if refund_description and ',' in refund_description else ''
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
