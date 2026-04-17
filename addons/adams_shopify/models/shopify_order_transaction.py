# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ShopifyOrderTransaction(models.Model):
    _name = 'shopify.order.transaction'
    _description = 'Shopify Order Transaction'
    _order = 'create_date desc'

    order_binding_id = fields.Many2one(
        'shopify.order.binding', required=True, ondelete='cascade', index=True,
    )
    backend_id = fields.Many2one(
        related='order_binding_id.backend_id', store=True,
    )
    shopify_transaction_id = fields.Char('Shopify Transaction ID', index=True)
    gateway = fields.Char('Gateway')
    kind = fields.Selection([
        ('sale', 'Sale'),
        ('capture', 'Capture'),
        ('authorization', 'Authorization'),
        ('refund', 'Refund'),
        ('void', 'Void'),
    ])
    status = fields.Selection([
        ('success', 'Success'),
        ('pending', 'Pending'),
        ('failure', 'Failure'),
        ('error', 'Error'),
    ])
    amount = fields.Float('Amount')
    currency_code = fields.Char('Currency')
    processed_at = fields.Datetime('Processed At')
    error_code = fields.Char('Error Code')

    _sql_constraints = [
        ('unique_transaction', 'UNIQUE(order_binding_id, shopify_transaction_id)',
         'Transaction already recorded.'),
    ]
