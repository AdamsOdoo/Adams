import uuid

from odoo import fields, models, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import REFUND_ORDER


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    is_shopify_refund = fields.Boolean("Refund in Shopify")
    is_notify_customer = fields.Boolean("Notify Customer?", help="Shopify will send email to customer regarding refund order.")
    refund_description = fields.Char("Refund Description")
    available_to_refund_amount = fields.Monetary(string='Total Available to refund')
    shopify_order_payment_ids = fields.One2many('shopify.order.payment', 'account_payment_id', string="Payment")

    def action_create_payments(self):
        """
        Task: T7183 - Refund in Shopify not working when credit not paid already.
        Improved validation conditions for refund processing.
        """
        payments = super().action_create_payments()
        if not self.is_shopify_refund:
            return payments
        active_id = self.env.context.get('active_id')
        credit_note_id = self.env['account.move'].browse(active_id)
        total_refund_amount = round(sum(self.shopify_order_payment_ids.mapped('refund_amount')), 2)
        if not total_refund_amount > 0.0:
            raise MarketplaceException(_("Please enter a refund amount before proceeding with the refund."))

        credit_note_amount = credit_note_id and round(credit_note_id.amount_total,2) or 0.0

        # Cannot exceed credit note amount
        if total_refund_amount > credit_note_amount:
            raise MarketplaceException(
                f"⚠️ You are trying to refund {total_refund_amount}, but the credit note is only for {credit_note_amount}. "
                f"Please create or adjust the credit note to match the amount you want to refund before proceeding."
            )

        order_id = credit_note_id.invoice_line_ids.mapped('sale_line_ids.order_id')[:1]

        refund_vals = order_id.prepare_shopify_refund_data(credit_note_id, self.shopify_order_payment_ids.filtered(lambda x: x.refund_amount > 0), self.is_notify_customer, self.refund_description)
        try:
            order_id.mk_instance_id.connection_to_shopify()
            # Task: T7545 - implement idempotencyKey for Shopify API 2026-07 version
            variables = {'input': refund_vals, 'idempotencyKey': str(uuid.uuid4())}
            response = order_id.mk_instance_id.execute_graphql_query(REFUND_ORDER, variables)
            refund_data = response.get('data', {}).get('refundCreate', {}).get('refund', {})
            user_errors = response.get('data', {}).get('refundCreate', {}).get("userErrors", [])
        except Exception as e:
            raise MarketplaceException(f"⚠️ Something went wrong while creating a refund in Shopify for order {order_id.name} : {e}")

        if "errors" in response or user_errors or refund_data is None:
            if user_errors:
                raise MarketplaceException(_("Refund Error: %(errors)s") % {'errors': ', '.join([e['message'] for e in user_errors])})
            elif refund_data is None:
                raise MarketplaceException(_("⚠️ Refund Error: Refund not created and no userErrors provided."))
            else:
                raise MarketplaceException(response.get('errors')[0].get('message'))

        order_id.post_shopify_refund_update(total_refund_amount, response)
        if order_id.shopify_financial_status == 'REFUNDED':
            credit_note_id.write({'is_refunded_in_mk': True})

        return payments

    def _create_payments(self):
        """
        Payment creation process to sync payment status with Shopify.
        Returns:
            recordset: The created payments
        """
        res = super(AccountPaymentRegister, self.with_context(is_paid_form_register_payment_wizard=True))._create_payments()
        SHOPIFY_PAYMENT_STATE = ('PAID', 'REFUNDED', 'PARTIALLY_REFUNDED', 'VOIDED')
        for pay in res:
            order_ids = pay.invoice_ids.line_ids.sale_line_ids.order_id.filtered(
                lambda o: o.marketplace == "shopify" and o.shopify_financial_status not in SHOPIFY_PAYMENT_STATE and o.mk_instance_id.mark_order_paid_from_odoo)
            for order_id in order_ids:
                order_id.process_shopify_order_payment_status()
        return res
