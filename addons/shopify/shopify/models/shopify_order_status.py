from odoo import models, fields

STATUS_SELECTION = [('unshipped', 'Unshipped'),
                    ('shipped', 'Shipped'),
                    ('partial', 'Partial'),
                    ('scheduled', 'Scheduled'),
                    ('on_hold', 'On Hold'),
                    ('request_declined', 'Request Declined'),
                    ('any', 'Any')]


class ShopifyOrderStatus(models.Model):
    _name = 'shopify.order.status'
    _description = "Shopify Order Status"

    name = fields.Char("Name", required=True)
    status = fields.Selection(STATUS_SELECTION, "Fulfillment Status")
