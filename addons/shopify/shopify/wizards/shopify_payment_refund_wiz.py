from odoo import fields, models, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import REFUND_ORDER


class ShopifyPaymentRefund(models.TransientModel):
    _name = 'shopify.payment.refund'
    _description = 'Shopify Payment Refund'

    is_notify_customer = fields.Boolean("Notify Customer?", help="Shopify will send email to customer regarding refund order.")
    refund_description = fields.Char("Refund Description")
    company_id = fields.Many2one('res.company')
    available_to_refund_amount = fields.Monetary(string='Total Available to refund')
    currency_id = fields.Many2one('res.currency', string="Company Currency", related='company_id.currency_id')
    shopify_order_payment_ids = fields.One2many('shopify.order.payment', 'payment_refund_id', string="Shopify Order Payments")

    def action_do_shopify_refund(self):
        """
        Task: T7183 - Refund in Shopify not working when credit not paid already.
        Improved validation conditions for refund processing.

        Creates a refund for a Shopify order based on the selected credit note.

        This method checks that refund amounts are entered, gathers the related
        sale order, prepares the refund data, and sends a refund request to Shopify
        via GraphQL. It handles API responses and updates the order accordingly
        in Odoo. On success, it returns a confirmation message for the Rainbow.

        Raises:
            MarketplaceException: If no refund amount is entered or
                       Shopify returns user errors.
        Returns:
            dict: Rainbow effect indicating a successful refund.

    """
        active_id = self.env.context.get('active_id')
        credit_note_id = self.env['account.move'].browse(active_id)
        total_refund_amount = round(sum(self.shopify_order_payment_ids.mapped('refund_amount')), 2)
        if not total_refund_amount > 0.0:
            raise MarketplaceException(_("Please enter a refund amount before proceeding with the refund."))

        # Calculate the PAID amount of the Odoo Credit Note (Total - Residual)
        credit_note_total = credit_note_id and credit_note_id.amount_total or 0.0
        credit_note_residual = credit_note_id and credit_note_id.amount_residual or 0.0
        paid_amount = round(credit_note_total - credit_note_residual, 2)

        # Cannot exceed paid credit note
        if total_refund_amount > paid_amount:
            raise MarketplaceException(
                f"⚠️ You are trying to refund {total_refund_amount}, but only {paid_amount} is paid on this credit note. "
                f"Please create or adjust the credit note for the exact amount you want to refund before proceeding."
            )

        order_id = credit_note_id.invoice_line_ids.mapped('sale_line_ids.order_id')[:1]
        refund_vals = order_id.prepare_shopify_refund_data(credit_note_id, self.shopify_order_payment_ids.filtered(lambda x: x.refund_amount > 0), self.is_notify_customer,
                                                           self.refund_description)
        try:
            order_id.mk_instance_id.connection_to_shopify()
            # Deterministic idempotency key per credit note + amount. If the client times out
            # after Shopify already created the refund, retrying sends the SAME key and Shopify's
            # @idempotent guard returns the original refund instead of creating a duplicate.
            idempotency_key = "odoo-refund-%s-%s" % (credit_note_id.id, int(round(total_refund_amount, 2) * 100))
            variables = {'input': refund_vals, 'idempotencyKey': idempotency_key}
            response = order_id.mk_instance_id.execute_graphql_query(REFUND_ORDER, variables)
            refund_data = response.get('data', {}).get('refundCreate', {}).get('refund', {})
            user_errors = response.get('data', {}).get('refundCreate', {}).get("userErrors", [])
        except Exception as e:
            raise MarketplaceException(f"Something went wrong while creating a refund in Shopify for order {order_id.name} : {e}")

        if "errors" in response or user_errors or refund_data is None:
            if user_errors:
                raise MarketplaceException(f"Refund Error: {', '.join([e['message'] for e in user_errors])}")
            elif refund_data is None:
                raise MarketplaceException(f"Refund Error: Refund not created and no userErrors provided.")
            else:
                raise MarketplaceException(response.get('errors')[0].get('message'))

        order_id.post_shopify_refund_update(total_refund_amount, response)
        return {
            'effect': {
                'fadeout': 'slow',
                'message': "Yeah! Order Refunded Successfully.",
                'img_url': '/web/static/img/smile.svg',
                'type': 'rainbow_man',
            }
        }
