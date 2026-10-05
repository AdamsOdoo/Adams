import time

from odoo import models, api, fields, _
from odoo.addons.shopify import shopify
from odoo.addons.shopify.models.misc import extract_numeric_id
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import CANCEL_ORDER, GET_ORDER_REFUNDS

CANCEL_REASON = [('CUSTOMER', 'Customer changed/canceled order'),
                 ('INVENTORY', 'Item unavailable'),
                 ('FRAUD', 'Fraudulent order'),
                 ('DECLINED', 'Payment declined'),
                 ('OTHER', 'Other'),
                 ('STAFF', 'Staff error')]

RESTOCK_TYPE = [('no_restock', 'No Restock'),
                ('cancel', 'Cancel'),
                ('return', 'Return')]


class MKCancelOrder(models.TransientModel):
    _inherit = "mk.cancel.order"

    @api.depends('shopify_refund_payment_lines.price_subtotal', 'shopify_refund_payment_lines.refund_price_unit', 'shopify_shipping_amount')
    def _amount_all(self):
        for record in self:
            shopify_amount_subtotal_to_refund, shopify_tax_amount, order_id = 0.0, 0.0, False
            for line in record.shopify_refund_payment_lines:
                order_id = line.order_line_id.order_id
                shopify_tax_amount += _get_amount_tax(line)
                shopify_amount_subtotal_to_refund += line.refund_price_unit * line.to_refund_qty
            if order_id and self.shopify_shipping_amount > 0.0:
                shipping_line = order_id.order_line.filtered(lambda x: x.is_delivery)
                shipping_taxes = shipping_line.tax_id.compute_all(shipping_line.price_unit, order_id.currency_id, 1, product=shipping_line.product_id,
                                                                  partner=order_id.partner_shipping_id)
                shipping_taxes_total = sum(t.get('amount', 0.0) for t in shipping_taxes.get('taxes', []))
                shopify_tax_amount += min(shipping_taxes_total,record.shopify_remaining_shipping_tax_amount)
            shopify_amount_subtotal = round(shopify_amount_subtotal_to_refund, 2)
            shopify_tax_amount = round(shopify_tax_amount, 2)
            shopify_manual_refund_amount = min(shopify_amount_subtotal + shopify_tax_amount + record.shopify_shipping_amount, record.shopify_amount_total)
            record.update({
                'shopify_tax_amount': shopify_tax_amount,
                'shopify_amount_subtotal': shopify_amount_subtotal,
                'shopify_manual_refund_amount': 0.0 if shopify_manual_refund_amount < 0 else shopify_manual_refund_amount
            })

    shopify_cancel_reason = fields.Selection(CANCEL_REASON, "Shopify Cancel Reason", default="CUSTOMER")
    shopify_is_notify_customer = fields.Boolean("Notify Customer?", default=False, help="Whether to send an email to the customer notifying them of the cancellation.")
    shopify_refund_payment_lines = fields.One2many("shopify.refund.payment.line", "wizard_id", string="Shopify Refund payments")
    shopify_amount_total = fields.Monetary(string='Shopify Total Available to refund')
    shopify_amount_subtotal = fields.Monetary(string='Shopify Subtotal', store=True, readonly=True, compute='_amount_all')
    shopify_remaining_shipping_amount = fields.Monetary(string='Shopify Remaining shipping amount to Refund')
    shopify_remaining_shipping_tax_amount = fields.Monetary(string='Remaining shipping tax amount to Refund')
    shopify_shipping_amount = fields.Monetary(string='Shopify Shipping')
    shopify_tax_amount = fields.Monetary(string="Shopify Tax", store=True, compute='_amount_all')
    shopify_manual_refund_amount = fields.Monetary(string='Refund Amount')
    shopify_txn_id = fields.Char("Transaction ID")
    shopify_gateway = fields.Char("Transaction Gateway")
    shopify_gift_card_amount = fields.Monetary(string='Gift Card Amount')
    duties_warning = fields.Boolean("Duties Warning", default=False)
    shopify_restock_type = fields.Selection(RESTOCK_TYPE, "Restock Type", default="no_restock", help="How this refund line item affects inventory levels. \n "
                                                                                                     "Valid values : \n"
                                                                                                     "no_restock : Refunding these items won't affect inventory. The number of fulfillable units for this line item will remain unchanged. For example, a refund payment can be issued but no items will be returned or made available for sale again. \n"
                                                                                                     "cancel : The items have not yet been fulfilled. The canceled quantity will be added back to the available count. The number of fulfillable units for this line item will decrease. \n"
                                                                                                     "return : The items were already delivered, and will be returned to the merchant. The returned quantity will be added back to the available count. The number of fulfillable units for this line item will remain unchanged.")
    shopify_is_restock_inventory = fields.Boolean("Restock Inventory", default=False, help="Enable this to restock inventory when order is canceled")
    invisible_shopify_restock_inventory = fields.Boolean("Hide/Show Restock Inventory", help="This will make visible or invisible Restock Inventory field.", default=True)
    shopify_is_refund_payments = fields.Boolean("Shopify Refund Payments", help="Enable this to refund payments when order is canceled", default=False)
    invisible_shopify_is_refund_payments = fields.Boolean("Shopify Hide/Show Refund Payments", help="This will make visible or invisible Refund Payments field.", default=False)

    @api.model
    def default_get(self, fields):
        defaults = super(MKCancelOrder, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        order_id = self.env['sale.order'].browse(active_id)

        # when shopify order payment status is refunded and fulfillment status is fulfilled or payment status is paid and fulfillment status is partial then make 'Restock Inventory' field invisible.
        if order_id and (order_id.shopify_financial_status == 'REFUNDED' and order_id.fulfillment_status == 'FULFILLED') or (
                order_id.shopify_financial_status == 'PAID' and order_id.fulfillment_status == 'PARTIALLY_FULFILLED'):
            defaults['invisible_shopify_restock_inventory'] = False

            # when shopify order payment status is paid and fulfillment status is unfulfilled or payment status is partially_paid and fulfillment status is unfulfilled then make 'Refund Payments' field visible.
        if order_id and (order_id.shopify_financial_status == 'PAID' and order_id.fulfillment_status == 'UNFULFILLED') or (
                order_id.shopify_financial_status == 'PARTIALLY_PAID' and order_id.fulfillment_status == 'UNFULFILLED') or (
                order_id.shopify_financial_status == 'PARTIALLY_REFUNDED' and order_id.fulfillment_status == 'UNFULFILLED'):
            defaults['invisible_shopify_is_refund_payments'] = True
        return defaults

    @api.onchange('shopify_manual_refund_amount')
    def onchange_shopify_manual_refund_amount(self):
        if self.shopify_manual_refund_amount > self.shopify_amount_total:
            self.shopify_manual_refund_amount = self.shopify_amount_total
        return {}

    @api.onchange('shopify_shipping_amount')
    def onchange_shopify_shipping_amount(self):
        if not self.shopify_remaining_shipping_amount and self.shopify_shipping_amount:
            self.shopify_shipping_amount = False
        if self.shopify_shipping_amount > self.shopify_remaining_shipping_amount:
            self.shopify_shipping_amount = self.shopify_remaining_shipping_amount
        return {}

    def fetch_shopify_transactions_details(self, order_id):
        shopify_transactions = shopify.Transaction().find(order_id=order_id.mk_id)
        gateway, parent_id, gift_card_amount = '', '', 0.0
        for transaction in shopify_transactions:
            transaction_dict = transaction.to_dict()
            transaction_type = transaction_dict.get('transaction', {}).get('kind') or transaction_dict.get('kind')
            transaction_status = transaction_dict.get('transaction', {}).get('status', '') or transaction_dict.get('status', '')
            if transaction_type in ['sale', 'capture'] and transaction_status == 'success':
                if transaction_dict.get('gateway', '') == 'gift_card':
                    gift_card_amount += (float(transaction_dict.get('amount', 0.0)) * -1)
                    continue
                parent_id = transaction_dict.get('transaction', {}).get('id') or transaction_dict.get('id')
                gateway = transaction_dict.get('transaction', {}).get('gateway') or transaction_dict.get('gateway')
        return parent_id, gateway, gift_card_amount

    def shopify_refund_wizard_default_get(self, order_id):
        # TODO This method is no longer in use.
        shopify_refund_payment_line_ids = self.env['shopify.refund.payment.line']
        order_id.mk_instance_id.connection_to_shopify()
        try:
            refunds = shopify.Refund.find(order_id=order_id.mk_id)
        except Exception as e:
            raise MarketplaceException(e)
        transaction_status = ''
        refund_dict_qty_wise = {}
        total_amount_refunded = 0.0
        total_shipping_refunded = 0.0
        total_shipping_tax_refunded = 0.0
        for refund in refunds:
            refund_dict = refund.to_dict()
            for transaction in refund_dict.get('transactions'):
                if transaction.get('status') == 'failure':
                    transaction_status = 'failure'
            if transaction_status == 'failure':
                break
            for refund_line in refund.refund_line_items:
                if refund_dict_qty_wise.get(refund_line.line_item_id, False):
                    refund_dict_qty_wise[refund_line.line_item_id] += refund_line.quantity
                else:
                    refund_dict_qty_wise.update({refund_line.line_item_id: refund_line.quantity})
            for adjustment in refund.order_adjustments:
                if adjustment.kind == 'shipping_refund':
                    if order_id.mk_instance_id.use_marketplace_currency:
                        total_shipping_refunded += float(adjustment.amount_set.presentment_money.amount)
                        total_shipping_tax_refunded += float(adjustment.tax_amount_set.presentment_money.amount)
                    else:
                        total_shipping_refunded += float(adjustment.amount_set.shop_money.amount)
                        total_shipping_tax_refunded += float(adjustment.tax_amount_set.shop_money.amount)
            for transaction in refund.transactions:
                if transaction.kind == 'refund':
                    total_amount_refunded += float(transaction.amount)

        remaining_shipping_to_refund, remaining_shipping_tax_to_refund, duties_warning = 0.0, 0.0, False
        for line in order_id.order_line:
            if line.price_subtotal <= 0:
                continue
            if line.product_id == order_id.mk_instance_id.duties_product_id:
                duties_warning = True
                continue
            if line.is_delivery:
                shipping_taxes = line.tax_id.compute_all(line.price_unit, order_id.currency_id, 1, product=line.product_id, partner=order_id.partner_shipping_id)
                shipping_taxes_total = sum(t.get('amount', 0.0) for t in shipping_taxes.get('taxes', []))
                remaining_shipping_tax_to_refund = shipping_taxes_total + total_shipping_tax_refunded
                if any(line.tax_id.mapped('price_include')):
                    remaining_shipping_to_refund = line.price_unit + total_shipping_refunded + line.related_disc_sale_line_id.price_unit + total_shipping_tax_refunded
                else:
                    remaining_shipping_to_refund = line.price_subtotal + total_shipping_refunded + line.related_disc_sale_line_id.price_subtotal
                continue
            if refund_dict_qty_wise.get(int(line.mk_id), False):
                available_qty = line.product_uom_qty - refund_dict_qty_wise.get(int(line.mk_id))
            else:
                available_qty = line.product_uom_qty
            if not available_qty:
                continue

            if any(line.tax_id.mapped('price_include')):
                price_unit = line.price_reduce_taxexcl - abs(line.related_disc_sale_line_id.price_reduce_taxexcl)
            else:
                price_unit = (line.price_subtotal / line.product_uom_qty) - abs((line.related_disc_sale_line_id.price_subtotal / line.product_uom_qty))
            shopify_refund_payment_line_ids |= self.env['shopify.refund.payment.line'].create({
                'product_id': line.product_id.id,
                'available_qty': available_qty,
                'to_refund_qty': available_qty,
                'price_unit': price_unit,
                'refund_price_unit': price_unit,
                'order_line_id': line.id,
            })

        parent_id, gateway, gift_card_amount = self.fetch_shopify_transactions_details(order_id)
        create_refund_option_visible = True if order_id.invoice_ids.filtered(lambda x: x.move_type == 'out_invoice' and x.payment_state in ['paid', 'in_payment']) else False
        return {'shopify_refund_payment_lines': [(6, 0, shopify_refund_payment_line_ids.ids)],
                'shopify_remaining_shipping_amount': remaining_shipping_to_refund,
                'shopify_remaining_shipping_tax_amount': remaining_shipping_tax_to_refund,
                'shopify_shipping_amount': remaining_shipping_to_refund,
                'shopify_amount_total': order_id.amount_total - total_amount_refunded + gift_card_amount,
                'shopify_txn_id': parent_id,
                'shopify_gateway': gateway,
                'duties_warning':duties_warning,
                'shopify_gift_card_amount': gift_card_amount,
                'currency_id': order_id.currency_id.id,
                'create_refund_option_visible': create_refund_option_visible}

    def do_cancel_in_shopify(self, order):
        """
        Task: T4859 - Check restock inventory while cancel order from Odoo
        Cancels an order in Shopify from Odoo, based on the user inputs provided in the wizard.It supports restocking inventory and optional customer notification and refund payments depending on the selected options.
        Args:
            order(recordset): Recordset of sale.order model.
        Returns:
            dictionary: That contains error message.
        Raises:
            MarketplaceException: If there's an exception during call cancel api.
        """
        mk_instance_id = order.mk_instance_id
        mk_instance_id.connection_to_shopify()
        #  Task: T7545 - Shopify API 2026-07 updates.
        refund_method = None
        if self.shopify_is_refund_payments:
            refund_method = {"originalPaymentMethodsRefund": True}

        variables = {
            "notifyCustomer": self.shopify_is_notify_customer,
            "orderId": f"gid://shopify/Order/{order.mk_id}",
            "reason": self.shopify_cancel_reason,
            "restock": self.shopify_is_restock_inventory,
            "refundMethod": refund_method
        }
        res = mk_instance_id.execute_graphql_query(CANCEL_ORDER, variables)

        user_errors = res.get('data', {}).get('orderCancel', {}).get('orderCancelUserErrors', [])
        graphql_errors = res.get('errors', [])

        err_messages = [e.get('message', str(e)) for e in graphql_errors]
        user_error_messages = [e.get('message', '') for e in user_errors]

        already_canceled_msg = 'Cannot cancel an order that has already been canceled'
        if already_canceled_msg in user_error_messages and len(user_error_messages) == 1 and not graphql_errors:
            body = _("This Shopify order has already been canceled and cannot be canceled again.")
            order.write({'canceled_in_marketplace': True})
            order.message_post(body=body)
            return

        err_messages.extend([msg for msg in user_error_messages if msg != already_canceled_msg])

        if err_messages:
            error_log = "\n".join(f"GraphQL error: {msg}" for msg in err_messages)
            raise MarketplaceException(error_log)

        order.write({'canceled_in_marketplace': True})
        return True

    def do_refund_in_shopify(self):
        # TODO : No longer in use
        active_id = self.env.context.get('active_id')
        order_id = self.env['sale.order'].browse(active_id)
        if self.env.context.get('force_refund'):
            order_id.shopify_force_refund = True
            return True
        if not order_id:
            raise MarketplaceException(_("Can't find order to cancel. Please go back to order list, open order and try again!"))
        # if self.shopify_refund_payment_lines and float_compare((self.shopify_amount_subtotal + self.shopify_shipping_amount + self.shopify_tax_amount) - abs(self.shopify_gift_card_amount),
        #                                                        self.shopify_manual_refund_amount, 2) != 0:
        #     raise UserError(_("Subtotal + Shipping + Tax isn't matching with the Refund Amount. Please adjust refund unit price!"))
        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=order_id.mk_instance_id, operation_type='export')
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        refund_item_list, restock_type = [], self.shopify_restock_type
        order_id.mk_instance_id.connection_to_shopify()
        for line in self.shopify_refund_payment_lines.filtered(lambda x: x.to_refund_qty):
            refund_item_dict = {'line_item_id': line.order_line_id.mk_id,
                                'quantity': int(line.to_refund_qty),
                                'restock_type': restock_type}
            if restock_type in ['cancel', 'return']:
                shopify_location_id = line.order_line_id.shopify_location_id
                if not shopify_location_id:
                    shopify_location_id = self.env['shopify.location.ts'].search([('is_default_location', '=', True), ('mk_instance_id', '=', order_id.mk_instance_id.id)])
                    if not shopify_location_id:
                        mk_log_line_dict['error'].append(
                            {'log_message': _('Default Shopify Location not found in Odoo while trying to Refund in Shopify. Order: %s') % order_id.name})
                refund_item_dict.update({'location_id': shopify_location_id.shopify_location_id})
            refund_item_list.append(refund_item_dict)
        if not refund_item_list and not self.shopify_amount_total and not self.shopify_manual_refund_amount:
            return False
        vals = {'notify': self.shopify_is_notify_customer,
                'note': self.refund_description or '',
                'order_id': order_id.mk_id,
                'refund_line_items': refund_item_list,
                'currency': order_id.currency_id.name,
                'transactions': [
                    {
                        'parent_id': int(self.shopify_txn_id),
                        'amount': self.shopify_manual_refund_amount,
                        'kind': 'refund',
                        'gateway': self.shopify_gateway,
                    }]}
        if self.shopify_shipping_amount:
            vals.update({'shipping': {'amount': self.shopify_shipping_amount}})
        try:
            response = shopify.Refund().create(vals)
        except Exception as e:
            raise MarketplaceException(f"Something went wrong while creating a refund in Shopify for order {order_id.name} : {e}")

        if response.errors and response.errors.errors:
            errors = response.errors.errors
            raise MarketplaceException(f"{errors}")

        shopify_order = shopify.Order.find(order_id.mk_id)
        order_id.write({'shopify_financial_status': shopify_order.financial_status})
        body = _("This order is refunded in Shopify with amount %s") % self.shopify_manual_refund_amount
        order_id.message_post(body=body)
        self.env['mk.log'].create_update_log(mk_instance_id=order_id.mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
        if not mk_log_id.log_line_ids and not self.env.context.get('log_id', False):
            mk_log_id.unlink()
        if self.is_create_refund:
            # self.create_shopify_refund_in_odoo(order_id)
            invoice_id = order_id.invoice_ids.filtered(lambda x: x.move_type == 'out_invoice')
            order_id.with_context(refund_journal_id=self.payment_journal_id.id, date=self.date_invoice)._create_shopify_credit_note_and_adjust_amount(shopify_order.to_dict(), response.to_dict(), invoice_id)
        return True

    def cancel_and_refund_in_shopify(self):
        """
        Task: T4611 - Check restock inventory while cancel order from Odoo
        Cancels an order in Shopify from Odoo, based on the user inputs provided in the wizard.
        Returns:
            boolean: Returns true if successfully cancel order in shopify.
        Raises:
            MarketplaceException: If there's an exception during order cancellation process.
        """
        active_id = self.env.context.get('active_id')
        order_id = self.env['sale.order'].browse(active_id)

        if not order_id:
            raise MarketplaceException(_("Can't find order to cancel. Please go back to order list, open order and try again!"))
        if order_id.shopify_financial_status == 'PAID' and order_id.fulfillment_status == 'FULFILLED':
            raise MarketplaceException(_("Orders that are paid and have fulfillments can't be canceled in Shopify."))

        # Cancel order in shopify
        self.do_cancel_in_shopify(order_id)

        # Find posted credit note
        posted_credit_note = order_id.invoice_ids.filtered(lambda x: x.move_type == 'out_refund' and x.state == 'posted')

        # If the 'Refund Payments' option is enabled and no posted refunds are found, a credit note will be automatically created in Odoo.
        if self.shopify_is_refund_payments and not posted_credit_note:
            try:
                time.sleep(2)
                # Get refund response of current cancelled order from shopify.
                variables = {"orderId": f"gid://shopify/Order/{order_id.mk_id}"}
                response = order_id.mk_instance_id.execute_graphql_query(GET_ORDER_REFUNDS, variables)
                user_errors = response.get('errors', []) if isinstance(response, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Order: %(errors)s") % {'errors': joined_errors})

                shopify_order = response.get('data', {}).get('order', {})
                refunds = shopify_order.get('refunds', [])
            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(e)
            return self.cancel_and_refund_in_shopify_transaction(order_id, refunds, shopify_order)

    def cancel_and_refund_in_shopify_transaction(self, order_id, refunds, shopify_order):
        """
        Processes successful Shopify refund transactions by creating corresponding credit notes in Odoo.

        Filters refunds to only include those with successful transactions,
        avoids duplicating credit notes for already processed refunds,
        and adjusts invoice amounts accordingly.

        Args:
            order_id: The sale order record to update.
            refunds (list): List of refund data from Shopify.
            shopify_order (dict): Shopify order data related to the refund.
        Returns:
            bool: True when processing is complete.
        """

        invoice_id = order_id.invoice_ids.filtered(lambda x: x.move_type == 'out_invoice' and x.state == 'posted')
        filtered_refunds = []

        for refund in refunds:
            transactions = refund.get('transactions', {}).get('nodes', [])
            successful_transactions = [txn for txn in transactions if isinstance(txn, dict) and txn.get('status') == 'SUCCESS']

            if successful_transactions:
                refund['transactions']['nodes'] = successful_transactions
                filtered_refunds.append(refund)

        for refund in filtered_refunds:
            refund_id = extract_numeric_id(refund.get('id'))
            existing_refund_id = self.env['account.move'].search([("shopify_refund_id", "=", refund_id), ("mk_instance_id", "=", order_id.mk_instance_id.id)])
            if existing_refund_id:
                continue
            # Create credit note in odoo.
            order_id._create_shopify_credit_note_and_adjust_amount(shopify_order, refund, invoice_id)

        return True

    # def create_shopify_refund_in_odoo(self, order_id):
    #     invoice_id = order_id.invoice_ids.filtered(lambda x: x.move_type == 'out_invoice' and x.payment_state in ['paid', 'in_payment'])
    #     if invoice_id:
    #         move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice_id.ids).create({
    #             'reason': self.refund_description or "Shopify Refund",
    #             'refund_method': 'refund',
    #             'date': self.date_invoice or datetime.now(),
    #             'journal_id': invoice_id.journal_id.id
    #         })
    #         reversal = move_reversal.reverse_moves()
    #         refund_invoice = self.env['account.move'].browse(reversal['res_id'])
    #         to_remove_lines = refund_invoice.invoice_line_ids
    #         new_move = move_reversal.new_move_ids
    #         for line in self.shopify_refund_payment_lines.filtered(lambda x: x.to_refund_qty):
    #             for inv_line in refund_invoice.invoice_line_ids.filtered(lambda x: x.product_id == line.order_line_id.product_id):
    #                 if line.refund_price_unit < line.order_line_id.price_subtotal:
    #                     price_unit = line.refund_price_unit
    #                 else:
    #                     price_unit = line.refund_price_unit
    #                 if any(line.order_line_id.tax_id.mapped('price_include')):
    #                     price_unit += (line.amount_tax / line.order_line_id.product_uom_qty)
    #                 inv_line.with_context(check_move_validity=False).write({'quantity': line.to_refund_qty, 'price_unit': price_unit})
    #                 to_remove_lines -= inv_line
    #         if self.shopify_shipping_amount:
    #             shipping_line = order_id.order_line.filtered(lambda x: x.is_delivery)
    #             shipping_product_id = shipping_line.mapped('product_id')
    #             for inv_line in refund_invoice.invoice_line_ids.filtered(lambda x: x.product_id == shipping_product_id):
    #                 shopify_shipping_amount = self.shopify_shipping_amount
    #                 if any(shipping_line.tax_id.mapped('price_include')):
    #                     shopify_shipping_amount += shipping_line.price_tax
    #                 inv_line.with_context(check_move_validity=False).write({'quantity': 1, 'price_unit': shopify_shipping_amount})
    #                 to_remove_lines -= inv_line
    #         if to_remove_lines:
    #             to_remove_lines.with_context(check_move_validity=False).unlink()
    #         new_move.with_context(**{'check_move_validity': False})._sync_dynamic_lines({'records': new_move})
    #         refund_invoice.action_post()
    #         self.env['account.payment.register'].with_context(active_model='account.move', active_ids=refund_invoice.ids).create(
    #             {'journal_id': self.payment_journal_id.id})._create_payments()
    #         return reversal
    #     return True


def _get_amount_tax(line):
    taxes = line.order_line_id.tax_id.compute_all(line.order_line_id.price_unit, line.order_line_id.order_id.currency_id, line.to_refund_qty, product=line.product_id,
                                                  partner=line.order_line_id.order_id.partner_shipping_id)
    amount_tax = sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
    related_disc_sale_line_id = line.order_line_id.related_disc_sale_line_id
    if related_disc_sale_line_id:
        taxes = related_disc_sale_line_id.tax_id.compute_all(related_disc_sale_line_id.price_unit, related_disc_sale_line_id.order_id.currency_id, line.to_refund_qty,
                                                             product=related_disc_sale_line_id.product_id, partner=related_disc_sale_line_id.order_id.partner_shipping_id)
        amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
    return amount_tax


class ShopifyRefundPaymentLines(models.TransientModel):
    _name = "shopify.refund.payment.line"
    _description = "Shopify Refund Line"

    @api.depends('to_refund_qty', 'refund_price_unit')
    def _compute_amount(self):
        for line in self:
            price_subtotal = line.refund_price_unit * line.to_refund_qty
            amount_tax = _get_amount_tax(line)
            line.update({'price_subtotal': price_subtotal,
                         'amount_tax': amount_tax})

    product_id = fields.Many2one('product.product', string='Product', ondelete='cascade', required=True)
    order_line_id = fields.Many2one('sale.order.line', string="Order Line", ondelete='cascade')
    available_qty = fields.Float(string='Available Quantity', digits='Product Unit', required=True, default=1.0)
    to_refund_qty = fields.Float(string='To Refund Quantity', digits='Product Unit', required=True, default=1.0)
    price_unit = fields.Float('Original Unit Price', required=True, digits='Product Price', default=0.0)
    refund_price_unit = fields.Float('Refund Unit Price', required=True, digits='Product Price', default=0.0)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True, compute_sudo=True)
    amount_tax = fields.Monetary(compute='_compute_amount', string='Total Tax', store=True, compute_sudo=True)
    wizard_id = fields.Many2one('mk.cancel.order', 'Wizard')
    currency_id = fields.Many2one('res.currency', 'Currency', readonly=True, related='wizard_id.currency_id', store=True)

    @api.onchange('to_refund_qty')
    def onchange_refund_qty(self):
        res = {}
        if not self.available_qty and self.to_refund_qty:
            self.to_refund_qty = False
        if self.to_refund_qty > self.available_qty:
            self.to_refund_qty = self.available_qty
        return res

    @api.onchange('refund_price_unit')
    def onchange_refund_price_unit(self):
        res = {}
        if self.refund_price_unit > self.price_unit:
            self.refund_price_unit = self.price_unit
        return res
