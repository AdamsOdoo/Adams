from odoo import models, fields, api


class ShopifyReturnLine(models.Model):
    _name = "shopify.return.line.ts"
    _description = "Shopify Return Line"
    _rec_name = "title"

    return_id = fields.Many2one('shopify.return.ts', "Return", required=True, ondelete='cascade', help="Shopify return linked with this line.")
    mk_instance_id = fields.Many2one('mk.instance', related='return_id.mk_instance_id', store=True)
    sale_order_id = fields.Many2one('sale.order', related='return_id.sale_order_id', store=True, help="Sale order related to this return line.")
    shopify_return_line_id = fields.Char("Shopify Return Line ID", copy=False, index=True, help="Unique return line ID received from Shopify.")
    fulfillment_line_item_gid = fields.Char("Fulfillment Line Item GID", copy=False,
                                            help="Required when exporting an Odoo-initiated return back to Shopify.")
    shopify_line_item_id = fields.Char("Shopify Order Line ID", copy=False, help="Shopify order line item ID linked with this return line.")
    shopify_variant_id = fields.Char("Shopify Variant ID", copy=False, help="Shopify variant ID of the returned product.")
    sku = fields.Char("SKU", copy=False, help="SKU of the returned product.")
    title = fields.Char("Title", copy=False, help="Name of the returned product.")
    quantity = fields.Integer("Quantity", default=0, help="Quantity requested for return.")
    refundable_quantity = fields.Integer("Refundable Qty", default=0, help="Quantity that can still be refunded.")
    refunded_quantity = fields.Integer("Refunded Qty", default=0, help="Quantity already refunded.")
    force_restocked_qty = fields.Integer("Force Restocked Qty", default=0, copy=False,
                                         help="Units manually restocked in Odoo beyond Shopify's count. Stores the merchant override to prevent duplicate restocks during future imports.")
    return_reason_note = fields.Char("Reason Note", help="Provide additional details if 'Other' is selected as the reason.")
    return_reason_definition_id = fields.Many2one('shopify.return.reason.ts', "Reason", help="Choose the most appropriate reason for the return.")
    sale_order_line_id = fields.Many2one('sale.order.line', "Sale Order Line",
                                         compute='_compute_sale_order_line', store=True,
                                         help="Resolved Odoo sale order line, matched by Shopify line item ID.")
    product_id = fields.Many2one('product.product', related='sale_order_line_id.product_id',
                                 store=True, string="Product", help="Product linked with this return line.")
    reverse_fulfillment_line_id = fields.Char("Reverse Fulfillment Order Line ID", copy=False,
                                              help="Shopify ReverseFulfillmentOrderLineItem GID — required by the returnProcess mutation's dispositions input when restocking from Odoo.")

    @api.depends('shopify_line_item_id', 'sale_order_id')
    def _compute_sale_order_line(self):
        """Resolve each return line's Odoo sale order line, matched by Shopify line item id."""
        sol_obj = self.env['sale.order.line']
        for line in self:
            if not (line.sale_order_id and line.shopify_line_item_id):
                line.sale_order_line_id = False
                continue
            line.sale_order_line_id = sol_obj.search([
                ('order_id', '=', line.sale_order_id.id),
                ('mk_id', '=', line.shopify_line_item_id),
            ], limit=1) or False
