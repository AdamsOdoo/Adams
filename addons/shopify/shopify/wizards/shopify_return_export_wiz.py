import logging
import math

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import (
    GET_RETURNABLE_FULFILLMENTS_FOR_ORDER,
    RETURN_CREATE_FROM_ODOO,
)
from odoo.addons.shopify.models.misc import extract_numeric_id

_logger = logging.getLogger("Teqstars:Shopify")

class ShopifyReturnExportWizard(models.TransientModel):
    _name = "shopify.return.export.wizard"
    _description = "Create a Shopify Return from Odoo"

    picking_id = fields.Many2one('stock.picking', "Source Delivery", readonly=True, help="Delivery order containing the items to be returned.")
    stock_move_id = fields.Many2one('stock.move', "Source Stock Move", readonly=True,
                                    help="Stock move containing the item to be returned. Limits return quantities to what was shipped in this move.")
    sale_order_id = fields.Many2one('sale.order', "Sale Order", required=True, readonly=True, help="Related sales order for the selected delivery.")
    mk_instance_id = fields.Many2one('mk.instance', "Instance", required=True, readonly=True, help="Shopify instance associated with this return.")
    notify_customer = fields.Boolean("Notify Customer", default=False,
                                     help="If enabled, Shopify sends a return confirmation email to the customer.")
    line_ids = fields.One2many('shopify.return.export.wizard.line', 'wizard_id', string="Return Lines",
                               help="Choose the products to return, specify the quantity, and select a return reason.")

    @api.model
    def default_get(self, fields_list):
        """
        Task: T8438 - Added support to open and populate the return wizard directly from a stock move.
        """
        res = super().default_get(fields_list)
        move = self.env['stock.move'].browse(res.get('stock_move_id') or self.env.context.get('default_stock_move_id') or []).exists()
        picking_id = res.get('picking_id') or self.env.context.get('default_picking_id')
        picking = self.env['stock.picking'].browse(picking_id) if picking_id else self.env['stock.picking']
        if not picking and not move:
            return res
        order = picking.sale_id or move.sale_line_id.order_id
        res.setdefault('sale_order_id', order.id)
        res.setdefault('mk_instance_id', order.mk_instance_id.id)
        if not res.get('line_ids'):
            res['line_ids'] = self._build_line_defaults(picking, move=move)
        return res

    @api.model
    def _build_line_defaults(self, picking, move=None):
        """
        Task: T8438 - Added support to show returnable Shopify quantity when the return wizard is opened from a stock move.
        Query Shopify for returnable fulfillment lines and present them as wizard rows.

        We rely on Shopify's ``returnableFulfillments`` query (not a local
        computation) because the marketplace is the source of truth for what
        is still returnable — a customer-side return may have already
        consumed some quantities even if the local Odoo data looks intact.
        Args:
            picking (recordset): Source delivery picking.
            move (recordset): Source stock move.
        Returns:
            list: One2many command values for wizard lines.
        """
        order = picking.sale_id or (move.sale_line_id.order_id if move else self.env['sale.order'])
        if not order or not order.mk_id or not order.mk_instance_id:
            return []
        if order.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % order.mk_instance_id.name)
        order.mk_instance_id.connection_to_shopify()

        reason_obj = self.env['shopify.return.reason.ts']
        default_reason = reason_obj.search([
            ('mk_instance_id', '=', order.mk_instance_id.id),
            ('handle', '=', 'unknown'),
        ], limit=1)
        if not default_reason:
            raise MarketplaceException(_(
                "Return reasons are not available for '%s'. Please sync the return reasons and try again."
            ) % order.mk_instance_id.name)
        variables = {
            "orderGid": f"gid://shopify/Order/{order.mk_id}",
            "maxFulfillments": 50,
        }
        response = order.mk_instance_id.execute_graphql_query(GET_RETURNABLE_FULFILLMENTS_FOR_ORDER, variables)
        errors = (response or {}).get('errors') or []
        if errors:
            messages = ", ".join(err.get('message', str(err)) for err in errors)
            raise MarketplaceException(_(f"Failed to fetch returnable fulfillments from Shopify: {messages}"))
        fulfillments = (((response or {}).get('data') or {}).get('returnableFulfillments') or {}).get('nodes') or []
        loc = self._get_picking_shopify_location_id(picking) if picking else (self._get_move_shopify_location_id(move) if move else False)
        delivered = self._get_picking_delivered_by_line_item(picking, move=move)
        line_vals = []
        for fulfillment_node in fulfillments:
            if loc and str(extract_numeric_id(((fulfillment_node.get('fulfillment') or {}).get('location') or {}).get('id'))) != str(loc):
                continue
            for line_node in (fulfillment_node.get('returnableFulfillmentLineItems') or {}).get('nodes', []) or []:
                ful_line = line_node.get('fulfillmentLineItem') or {}
                line_item = ful_line.get('lineItem') or {}
                if not ful_line.get('id'):
                    continue
                shopify_line_id = extract_numeric_id(line_item.get('id'))
                key = str(shopify_line_id)
                remaining = float(delivered.get(key, 0.0))
                if remaining <= 0:
                    continue
                avail = min(int(line_node.get('quantity') or 0), int(math.floor(remaining + 1e-6)))
                if avail <= 0:
                    continue
                delivered[key] = remaining - avail
                line_vals.append((0, 0, {
                    'fulfillment_line_item_gid': ful_line.get('id'),
                    'shopify_line_item_id': key if shopify_line_id is not None else False,
                    'sku': line_item.get('sku') or '',
                    'title': line_item.get('title') or '',
                    'available_quantity': avail,
                    'quantity_to_return': avail,
                    'return_reason_definition_id': default_reason.id,
                }))
        return line_vals

    @api.model
    def _get_picking_shopify_location_id(self, picking):
        """
        Get the Shopify location for a delivery picking.
        Resolve the Shopify location mapped to the warehouse used by the
        specified picking.
        Args:
            picking (recordset): Delivery picking.
        Returns:
            str | bool: Shopify location ID or False.
        """
        warehouse = picking.picking_type_id.warehouse_id or picking.location_id.warehouse_id
        loc = warehouse and self.env['shopify.location.ts'].search([
            ('order_warehouse_id', '=', warehouse.id), ('mk_instance_id', '=', picking.sale_id.mk_instance_id.id)], limit=1)
        return loc and loc.shopify_location_id or False

    @api.model
    def _get_move_shopify_location_id(self, move):
        """
        Task: T8438 - Added Shopify location handling for stock moves without a picking, including fulfillment split and warehouse mapping.
        Args:
            move (recordset): Source stock move.
        Returns:
            str | bool: Shopify location ID or False.
        """
        order = move.sale_line_id.order_id
        warehouse = move.location_id.warehouse_id or move.warehouse_id
        if not order.mk_instance_id or not warehouse:
            return False
        location_obj = self.env['shopify.location.ts']
        for split in move.sale_line_id._get_shopify_fulfillment_splits('fulfilled'):
            shopify_location = location_obj.browse(split.get('shopify_location_record_id'))
            if shopify_location.exists() and shopify_location.order_warehouse_id == warehouse:
                return shopify_location.shopify_location_id or False
        loc = location_obj.search([
            ('mk_instance_id', '=', order.mk_instance_id.id),
            ('order_warehouse_id', '=', warehouse.id),
        ], limit=1)
        return loc.shopify_location_id or False

    @api.model
    def _get_picking_delivered_by_line_item(self, picking, move=None):
        """
        Task: T8438 - Added move-wise delivered quantity handling for Shopify returns
        Calculate delivered quantities by Shopify line item.
        Compute the delivered quantity for each Shopify order line included in
        the specified picking.
        Args:
            picking (recordset): Delivery picking.
            move (recordset): Optional single stock move. When given, only that move's
                              delivered quantity is counted — this is what caps a
                              move-scoped return.
        Returns:
            dict: Mapping of Shopify line item ID (str) to delivered quantity.
        """
        delivered = {}
        source_moves = move or picking.move_ids
        for source_move in source_moves.filtered(lambda m: m.state == 'done' and m.sale_line_id.mk_id):
            key = str(source_move.sale_line_id.mk_id)
            delivered[key] = delivered.get(key, 0.0) + source_move.quantity
        return delivered

    def action_submit_return(self):
        """
        Task: T8438 - Hide the Create Return in Shopify button on the stock move once nothing is left to return on it.
        Create a Shopify return.
        Validate the selected return lines, create the return in Shopify,
        synchronize the newly created return into Odoo, and open the created
        return record when available.
        Returns:
            dict: Action opening the Shopify return record or a success message.
        """
        self.ensure_one()
        if self.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % self.mk_instance_id.name)
        if not self.line_ids:
            raise MarketplaceException(_("There are no returnable lines to send to Shopify."))
        for line in self.line_ids:
            if line.quantity_to_return < 0:
                raise MarketplaceException(_("Return quantity cannot be negative."))
            if line.available_quantity > 0 and line.quantity_to_return > line.available_quantity:
                raise MarketplaceException(_(
                    f"Cannot return more than the available {line.available_quantity} units of {line.title or line.sku}."))
        active_lines = self.line_ids.filtered(lambda l: l.quantity_to_return > 0)
        if not active_lines:
            raise MarketplaceException(_("Please enter a quantity > 0 for at least one line before submitting."))

        return_line_items = []
        for line in active_lines:
            line_item = {
                "fulfillmentLineItemId": line.fulfillment_line_item_gid,
                "quantity": int(line.quantity_to_return),
                "returnReasonNote": line.return_reason_note or '',
            }
            if line.return_reason_definition_id:
                line_item["returnReasonDefinitionId"] = f"gid://shopify/ReturnReasonDefinition/{line.return_reason_definition_id.shopify_reason_definition_id}"
            else:
                raise MarketplaceException(_("Cannot create the return without a return reason. Please select a return reason and try again."))
            return_line_items.append(line_item)
        return_input = {
            "orderId": f"gid://shopify/Order/{self.sale_order_id.mk_id}",
            "notifyCustomer": self.notify_customer,
            "returnLineItems": return_line_items,
        }

        self.mk_instance_id.connection_to_shopify()
        response = self.mk_instance_id.execute_graphql_query(RETURN_CREATE_FROM_ODOO, {"returnInput": return_input})
        errors = (response or {}).get('errors') or []
        if errors:
            messages = ", ".join(err.get('message', str(err)) for err in errors)
            raise MarketplaceException(_(f"Shopify rejected the return create request: {messages}"))
        block = (((response or {}).get('data') or {}).get('returnCreate') or {})
        user_errors = block.get('userErrors') or []
        if user_errors:
            messages = ", ".join(err.get('message', str(err)) for err in user_errors)
            raise MarketplaceException(_(f"Shopify userErrors on returnCreate: {messages}"))
        return_node = block.get('return') or {}
        return_gid = return_node.get('id')
        if not return_gid:
            raise MarketplaceException(_("Shopify did not return a Return ID."))

        remaining_by_line_item = {}
        for line in self.line_ids.filtered('shopify_line_item_id'):
            key = str(line.shopify_line_item_id)
            remaining_by_line_item[key] = remaining_by_line_item.get(key, 0) + (line.available_quantity - line.quantity_to_return)
        exhausted_keys = {key for key, remaining in remaining_by_line_item.items() if remaining <= 0}
        moves = self.stock_move_id or self.picking_id.move_ids
        moves.filtered(lambda m: str(m.sale_line_id.mk_id or '') in exhausted_keys).write({'shopify_return_exhausted': True})

        # Pull the freshly created return back through our standard import path
        # so the local record is identical in shape to crons-imported returns.
        self.env['shopify.return.ts'].enqueue_return_from_webhook(self.mk_instance_id, return_gid)
        # Process synchronously for immediate UI feedback (not via cron).
        new_queue = self.env['mk.queue.job'].search([
            ('mk_instance_id', '=', self.mk_instance_id.id),
            ('type', '=', 'return'),
        ], order='id desc', limit=1)
        if new_queue:
            new_queue.with_context(hide_notification=True).shopify_return_queue_process()

        local_return = self.env['shopify.return.ts'].search([
            ('mk_instance_id', '=', self.mk_instance_id.id),
            ('shopify_return_id', '=', str(extract_numeric_id(return_gid) or '')),
        ], limit=1)
        if local_return:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Shopify Return'),
                'res_model': 'shopify.return.ts',
                'view_mode': 'form',
                'res_id': local_return.id,
            }
        return {
            'effect': {
                'fadeout': 'slow',
                'message': _("Return created in Shopify. Sync will pick it up shortly."),
                'type': 'rainbow_man',
            }
        }


class ShopifyReturnExportWizardLine(models.TransientModel):
    _name = "shopify.return.export.wizard.line"
    _description = "Shopify Return Export Wizard Line"

    wizard_id = fields.Many2one('shopify.return.export.wizard', required=True, ondelete='cascade', help="Return wizard belongs to this line.")
    fulfillment_line_item_gid = fields.Char("Fulfillment Line Item GID", required=True, help="Shopify fulfillment line item used to create the return.")
    shopify_line_item_id = fields.Char("Shopify Order Line ID", help="Shopify order line associated with this return line.")
    sku = fields.Char("SKU", help="Reference code used to identify the product.")
    title = fields.Char("Product", help="Name of the product being returned.")
    available_quantity = fields.Integer("Returnable Qty",
                                        help="Quantity currently available to return in Shopify.")
    quantity_to_return = fields.Integer("Quantity to Return", default=0, help="Quantity to include in the Shopify return.")
    return_reason_handle = fields.Char(related='return_reason_definition_id.handle', help="Internal Shopify return reason identifier.")
    return_reason_note = fields.Char("Reason Note", help="Provide additional details if 'Other' is selected as the reason.")
    return_reason_definition_id = fields.Many2one('shopify.return.reason.ts', "Reason", help="Choose the most appropriate reason for the return.")