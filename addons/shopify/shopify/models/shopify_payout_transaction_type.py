from odoo import fields, models


class ShopifyPayoutTransactionType(models.Model):
    _name = 'shopify.payout.transaction.type'
    _description = 'Shopify Payout Transaction Type'

    name = fields.Text('Transaction Type Name', help="The type of the balance transaction")
    transaction_type_code = fields.Text(help="The type of the resource leading to the transaction.", string="Transaction Type Code")
