from odoo import models, api, fields, _


class ShopifyOrderPayment(models.TransientModel):
    _name = "shopify.order.payment"
    _description = "Shopify Order Payment"
    _rec_name = "payment_gateway_id"

    payment_gateway_id = fields.Many2one("shopify.payment.gateway.ts")
    total_amount = fields.Float(string="Total Amount")
    remaining_amount = fields.Float(string="Available to Refund")
    refund_amount = fields.Float(string="Refund Amount")
    parent_transaction_id = fields.Char(string="Parent Transaction ID")
    payment_refund_id = fields.Many2one("shopify.payment.refund", string="Refund")
    account_payment_id = fields.Many2one("account.payment.register", string="Payment")

    @api.onchange("refund_amount")
    def onchange_validate_order(self):
        for record in self:
            if record.refund_amount > record.remaining_amount:
                record.refund_amount = record.remaining_amount
