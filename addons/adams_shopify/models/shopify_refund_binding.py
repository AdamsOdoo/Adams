from odoo import fields, models


class ShopifyRefundBinding(models.Model):
    _name = 'shopify.refund.binding'
    _description = 'Shopify Refund Binding'
    _inherit = 'shopify.binding'

    odoo_id = fields.Many2one(
        'account.move', string='Credit Note', ondelete='cascade', index=True,
    )
    order_binding_id = fields.Many2one(
        'shopify.order.binding', string='Order Binding',
        ondelete='cascade', index=True,
    )
    shopify_order_id = fields.Char('Shopify Order ID')
    refund_note = fields.Text('Refund Note')
    refund_amount = fields.Float('Refund Amount')
    currency_code = fields.Char('Currency')
    refund_line_ids = fields.One2many(
        'shopify.refund.line', 'refund_binding_id', string='Refund Lines',
    )

    _sql_constraints = [
        ('unique_backend_shopify', 'UNIQUE(backend_id, shopify_id)',
         'A binding already exists for this Shopify refund.'),
    ]
