import logging
import time

from odoo.addons.base_marketplace.models.exceptions import MarketplaceException

from odoo import models, api, fields, _
from odoo.addons.shopify.models.graphql_queries import UPDATE_PICKUP_STATUS, GET_ORDERS_BY_ID, CREATE_FULFILLMENT, CHANGE_LOCATION_OF_FULFILLMENT_ORDER, FETCH_FULFILLMENT, \
    INVENTORY_BULK_TOGGLE_ACTIVATION
from odoo.addons.shopify.models.misc import extract_numeric_id

_logger = logging.getLogger("Qamah:Shopify")


class StockMove(models.Model):
    _inherit = "stock.move"

    shopify_return_id = fields.Many2one('shopify.return.ts', "Shopify Return", index=True, ondelete='set null',
                                        help="Set when this move was created as a reverse move for a Shopify return on an order with no return picking (fulfilled-shortcut case).")
    shopify_return_exhausted = fields.Boolean(string="Shopify Return Exhausted?", default=False, copy=False, help="True when there is no quantity left to return in Shopify.")
    is_shopify_returnable_move = fields.Boolean(string="Is Shopify Returnable Move?", compute='_compute_is_shopify_returnable_move', compute_sudo=True,
                                                help="True when this move can be returned in Shopify.")

    def _compute_is_shopify_returnable_move(self):
        """
        Task: T8438 - Check whether a stock move can be returned through Shopify and updates ``is_shopify_returnable_move`` for each stock move.
        """
        for move in self:
            order = move.sale_line_id.order_id
            picking = move.picking_id
            if picking:
                is_delivery = move.picking_code == 'outgoing'
                is_fulfilled = picking.updated_in_marketplace and (not picking.sale_id_is_pickup_order or picking.is_picked_up_in_marketplace)
                still_returnable = not picking.shopify_return_id
            else:
                is_delivery = move.location_dest_id.usage == 'customer'
                is_fulfilled = order.updated_in_marketplace
                still_returnable = True
            move.is_shopify_returnable_move = bool(
                move.state == 'done'
                and is_delivery
                and is_fulfilled
                and still_returnable
                and not move.shopify_return_exhausted
                and not move.origin_returned_move_id
                and not move.shopify_return_id
                and move.quantity > 0
                and move.sale_line_id.mk_id
                and order.marketplace == 'shopify'
                and order.mk_id
                and order.mk_instance_id.state == 'confirmed'
            )

    def action_open_shopify_return_export_wiz(self):
        """
        Task: T8438 - Open the Shopify return wizard for this stock move.
        Returns:
            dict: Action opening the return wizard, or a warning notification.
        """
        self.ensure_one()
        order = self.sale_line_id.order_id
        if order.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % order.mk_instance_id.name)
        if not self.is_shopify_returnable_move:
            raise MarketplaceException(_(
                "This move cannot be returned in Shopify. It must be a delivered (done) move of a "
                "Shopify order that has already been fulfilled in Shopify."))
        line_commands = self.env['shopify.return.export.wizard']._build_line_defaults(self.picking_id, move=self)
        if not line_commands:
            self.shopify_return_exhausted = True
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': _("Nothing to Return"),
                    'message': _("Shopify reports no returnable quantity left for this product. "
                                 "The Create Return in Shopify button will be hidden."),
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
                },
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Return in Shopify'),
            'res_model': 'shopify.return.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_stock_move_id': self.id,
                'default_picking_id': self.picking_id.id or False,
                'default_sale_order_id': order.id,
                'default_mk_instance_id': order.mk_instance_id.id,
                'default_line_ids': line_commands,
            },
        }

    def _assign_picking_post_process(self, new=False):
        res = super(StockMove, self)._assign_picking_post_process(new=new)
        order_id = self.sale_line_id.order_id
        if new and order_id.marketplace == 'shopify' and order_id.fulfillment_status == 'FULFILLED':
            picking_id = self.mapped('picking_id')
            picking_id and picking_id.write({'updated_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False})
        return res

    def _action_assign(self, *args, **kwargs):
        """
       Task: T7454 - Trigger Shopify inventory sync on stock reservation.

       Extends `_action_assign` to sync inventory when stock is reserved
       (assigned or partially available state).

       - Skips execution during stock import.
       - Calls `_execute_inventory` for relevant moves.

       Returns:
        """
        res = super()._action_assign(*args, **kwargs)
        is_import_stock = self.env.context.get('is_import_stock', False)
        if not is_import_stock:
            try:
                moves = self.exists().filtered(lambda m: m.state in ['assigned', 'partially_available'] and m.product_id.is_storable)
                if moves:
                    self._process_shopify_inventory_sync(moves)
            except Exception as e:
                _logger.error(f"Inventory sync failed: {e}")

        return res

    def _action_cancel(self, *args, **kwargs):
        """
        Task: T7454 - Trigger Shopify inventory sync on stock Cancel.

        Trigger Shopify inventory sync when stock reservation is cancelled.
        (e.g., Sale Order cancellation)
        """

        res = super(StockMove, self)._action_cancel()

        is_import_stock = self.env.context.get('is_import_stock', False)
        if not is_import_stock:
            try:
                moves = self.exists().filtered(lambda m: m.product_id.is_storable)
                if moves:
                    self._process_shopify_inventory_sync(moves)
            except Exception as e:
                _logger.error(f"Inventory sync failed: {e}")
        return res

    def _action_confirm(self, *args, **kwargs):
        """
        Task: T7454 - Sync Shopify inventory on incoming stock confirmation.

        Extends `_action_confirm` to trigger inventory updates when incoming
        stock moves are confirmed.

        - Processes only storable products.
        - Applies only to incoming pickings.
        - Skips execution during stock import (`is_import_stock` context).
        - Delegates inventory handling to `_execute_inventory`.

        Returns:
            result: Super method result.
        """
        res = super()._action_confirm(*args, **kwargs)

        if not self.env.context.get('is_import_stock', False):
            try:
                moves = self.exists().filtered(lambda m: m.product_id.is_storable and m.picking_code == 'incoming')
                if moves:
                    self._process_shopify_inventory_sync(moves)
            except Exception as e:
                _logger.error(f"Inventory sync failed: {e}")
        return res

    def _action_done(self, *args, **kwargs):
        """
        Task: T7454 - Sync Shopify inventory after stock move completion.

        Extends `_action_done` to trigger inventory updates for Shopify when
        stock moves are completed.

        - Processes only storable products in 'done' state.
        - Skips execution during stock import (`is_import_stock` context).
        - Delegates inventory preparation and sync to `_execute_inventory`.

        Returns:
            result: Super method result.
        """

        res = super(StockMove, self)._action_done(*args, **kwargs)

        is_import_stock = self.env.context.get('is_import_stock', False)
        if not is_import_stock:
            try:
                moves = self.exists().filtered(lambda m: m.state == 'done' and m.product_id.is_storable)
                if moves:
                    self._process_shopify_inventory_sync(moves)
            except Exception as e:
                _logger.error(f"Inventory sync failed: {e}")

        return res

    def _process_shopify_inventory_sync(self, moves):
        """
        Task: T7454 - Prepare and execute Shopify inventory updates.

        Processes stock moves to:
        - Fetch related Shopify listing items.
        - Identify valid Shopify locations.
        - Prepare bulk inventory update data.
        - Group updates per marketplace instance.
        - Trigger bulk inventory sync.

        Args:
            moves (recordset): Stock moves to process.
        """
        self = self.sudo()
        instance_inventory_payload_map, has_inventory_updates = {}, False
        for move in moves:
            listing_item_rows = self.get_shopify_listing_items(move)
            listing_item_ids_list = [row[0] for row in listing_item_rows]
            listing_item_ids = self.env['mk.listing.item'].browse(listing_item_ids_list)

            for listing_item_id in listing_item_ids:
                mk_instance_id = listing_item_id.mk_instance_id
                source_location = move.location_id.usage
                destination_location = move.location_dest_id.usage
                location_id = (move.location_id if source_location == 'internal' else False or move.location_dest_id if destination_location == 'internal' else False)

                shopify_location_ids = self.env['shopify.location.ts'].search([('mk_instance_id', '=', mk_instance_id.id), ('is_import_export_stock', '=', True), '|', ('export_location_ids', 'child_of', location_id.id), ('export_location_ids', 'parent_of', location_id.id), ])
                if not shopify_location_ids:
                    continue

                inventory_updates = self.env['mk.listing'].prepare_bulk_inventory_update_vals(mk_instance_id, listing_item_id, shopify_location_ids, mk_log_id=False)
                instance_inventory_payload_map.setdefault(mk_instance_id, []).extend(inventory_updates)
                has_inventory_updates = True

        if has_inventory_updates:
            self._execute_inventory_updates(instance_inventory_payload_map)

    def get_shopify_listing_items(self, move):
        """
        Task: T7454 - Fetch Shopify listing items for a product using optimized SQL.

        Retrieves listing items linked to the given product that:
                - Are listed on Shopify (is_listed = TRUE)
                - Use Shopify inventory management
                - Belong to confirmed Shopify instances
                - Have auto inventory sync enabled

        Kit/phantom BoM parents are only resolved when the `mrp` module is installed;
        otherwise the CTE is skipped so this method is safe without MRP.

        Args:
            move (record): Stock move record.

        Returns:
           list: List of tuples (listing_item_id, mk_instance_id).
       """
        product_id = move.product_id.id
        mrp_installed = self.env['mk.instance']._is_module_installed('mrp')

        if mrp_installed:
            query = """
            WITH RECURSIVE kit_tree AS (
                SELECT pp.id AS product_id
                FROM mrp_bom_line bl
                JOIN mrp_bom b ON bl.bom_id = b.id
                JOIN product_template pt ON b.product_tmpl_id = pt.id
                JOIN product_product pp ON pp.product_tmpl_id = pt.id
                WHERE bl.product_id = %s AND b.type = 'phantom'

                UNION

                SELECT pp.id
                FROM kit_tree kt
                JOIN mrp_bom_line bl ON bl.product_id = kt.product_id
                JOIN mrp_bom b ON bl.bom_id = b.id
                JOIN product_template pt ON b.product_tmpl_id = pt.id
                JOIN product_product pp ON pp.product_tmpl_id = pt.id
                WHERE b.type = 'phantom'
            )
            SELECT DISTINCT mkli.id, mkli.mk_instance_id
            FROM mk_listing_item mkli
            JOIN mk_instance mi ON mkli.mk_instance_id = mi.id
            WHERE (mkli.product_id = %s OR mkli.product_id IN (SELECT product_id FROM kit_tree))
              AND mkli.is_listed = TRUE
              AND mkli.inventory_management = 'shopify'
              AND mi.marketplace = 'shopify'
              AND mi.state = 'confirmed'
              AND mi.auto_sync_inventory_to_shopify = TRUE
            """
            params = (product_id, product_id)
        else:
            query = """
            SELECT DISTINCT mkli.id, mkli.mk_instance_id
            FROM mk_listing_item mkli
            JOIN mk_instance mi ON mkli.mk_instance_id = mi.id
            WHERE mkli.product_id = %s
              AND mkli.is_listed = TRUE
              AND mkli.inventory_management = 'shopify'
              AND mi.marketplace = 'shopify'
              AND mi.state = 'confirmed'
              AND mi.auto_sync_inventory_to_shopify = TRUE
            """
            params = (product_id,)

        # Savepoint protects the outer transaction: if this query ever fails
        # (e.g. missing table in a partial upgrade), the base stock flow is
        # not left with an aborted PG transaction.
        with self.env.cr.savepoint(flush=False):
            self.env.cr.execute(query, params)
            results = self.env.cr.fetchall()
        return results

    def _execute_inventory_updates(self, inventory_updates_list_dict):
        """
        Task: T7454 - Execute bulk Shopify inventory updates per instance.

        Iterates over prepared inventory updates grouped by marketplace instance,
        creates logs, and triggers bulk inventory sync to Shopify.

        """
        for mk_instance_id, updates_list in inventory_updates_list_dict.items():
            if updates_list:
                updates_list = list({(i['inventoryItemId'], i['locationId']): i for i in updates_list}.values())
                mk_log_line_dict = {'error': [], 'success': []}
                mk_log_id = self.env['mk.log'].create_update_log(mk_log_id=False, mk_instance_id=mk_instance_id, operation_type='export', mk_log_line_dict=mk_log_line_dict)
                self.env['mk.listing'].with_context(manual_operation=True).run_bulk_shopify_inventory_update_perfect(mk_instance_id, updates_list, mk_log_id, mk_log_line_dict)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    shopify_fulfillment_id = fields.Char(string='Shopify Fulfillment ID', copy=False)
    is_picked_up_in_marketplace = fields.Boolean(string="Picked Up in Shopify", default=False, copy=False, help="Indicates whether this order has been marked as picked up in shopify or not?")
    sale_id_is_pickup_order = fields.Boolean(related='sale_id.is_pickup', string='Is Pickup Sale Order', store=True)
    shopify_return_id = fields.Many2one('shopify.return.ts', string='Shopify Return',
                                        copy=False, ondelete='set null',
                                        help="Set on incoming pickings auto-created from a Shopify return.")
    is_shopify_return_picking = fields.Boolean(compute='_compute_is_shopify_return_picking',
                                               string="Is Shopify Return?",
                                               help="Outgoing 'done' picking that has at least one return move OR an incoming picking that traces back to a Shopify return.")
    has_shopify_returnable_qty = fields.Boolean(
        string="Has Shopify Returnable Qty?", default=True, copy=False,
        help="Set to False when a Shopify returnableFulfillments check found "
             "nothing left to return for this picking. Used to hide the "
             "Create Return in Shopify button.")

    @api.depends('shopify_return_id', 'move_ids.origin_returned_move_id')
    def _compute_is_shopify_return_picking(self):
        for picking in self:
            picking.is_shopify_return_picking = bool(picking.shopify_return_id) or any(
                move.origin_returned_move_id for move in picking.move_ids
            )

    def action_open_shopify_return_export_wiz(self):
        self.ensure_one()
        if self.sale_id.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % self.sale_id.mk_instance_id.name)
        wizard_obj = self.env['shopify.return.export.wizard']
        line_commands = wizard_obj._build_line_defaults(self)
        if not line_commands:
            if self.has_shopify_returnable_qty:
                self.has_shopify_returnable_qty = False
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'title': _("Nothing to Return"),
                    'message': _("Shopify reports no returnable items for this delivery. "
                                 "The Create Return in Shopify button will be hidden."),
                    'sticky': False,
                    'next': {'type': 'ir.actions.client', 'tag': 'soft_reload'},
                },
            }
        if not self.has_shopify_returnable_qty:
            self.has_shopify_returnable_qty = True
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Return in Shopify',
            'res_model': 'shopify.return.export.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_sale_order_id': self.sale_id.id,
                'default_mk_instance_id': self.sale_id.mk_instance_id.id,
                'default_line_ids': line_commands,
            },
        }

    def action_open_shopify_return(self):
        self.ensure_one()
        if not self.shopify_return_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Shopify Return',
            'res_model': 'shopify.return.ts',
            'view_mode': 'form',
            'res_id': self.shopify_return_id.id,
        }

    def shopify_update_order_status_to_marketplace(self):
        self.mk_instance_id.connection_to_shopify()
        self.process_update_order_status_shopify(manual_process=True)
        return True

    def do_marked_as_updated_in_odoo(self):
        res = super(StockPicking, self).do_marked_as_updated_in_odoo()
        if self.marketplace == 'shopify' and self.sale_id_is_pickup_order:
            self.is_picked_up_in_marketplace = True
        return res

    def _activate_shopify_location_for_fulfillment(self, mk_instance_id, pickup_location_id, item_ids):
        """
        T7441 - Activate a Shopify location for given inventory items.
        Ensures that all products (variants) are available at the pickup location before attempting fulfillment order transfer.
        :param recordset mk_instance_id: Recordset of the mk.instance model.
        :param str pickup_location_id: The Shopify Location ID to activate.
        :param list item_ids: Shopify variant IDs.
        :return: True if successfully activated, False otherwise.
        :rtype: bool
        """
        if not isinstance(item_ids, list):
            item_ids = [item_ids]

        # 1. Find all Marketplace Listing Items using the Shopify Line Item IDs
        listing_item_ids = self.env['mk.listing.item'].search([('mk_id', 'in', item_ids), ('mk_instance_id', '=', mk_instance_id.id)])

        all_activated = True

        # 2. Execute the activation mutation for EACH inventory item
        for listing_item_id in listing_item_ids:
            inventory_item_id = listing_item_id.inventory_item_id
            if not inventory_item_id:
                _logger.warning(f"No Shopify Inventory Item ID on listing: {listing_item_id.mk_id}")
                continue

            activation_variables = {
                "inventoryItemId": f"gid://shopify/InventoryItem/{inventory_item_id}",
                "inventoryItemUpdates": [
                    {
                        "locationId": f"gid://shopify/Location/{pickup_location_id}",
                        "activate": True
                    }
                ]
            }

            activation_resp = mk_instance_id.execute_graphql_query(INVENTORY_BULK_TOGGLE_ACTIVATION, activation_variables)
            data = activation_resp.get("data", {}) if activation_resp else {}
            bulk_toggle = data and data.get("inventoryBulkToggleActivation", {})
            activation_errors = bulk_toggle and bulk_toggle.get("userErrors", [])

            if activation_errors:
                error_message = ", ".join(error['message'] for error in activation_errors)
                _logger.error(f"Failed to activate location {pickup_location_id} for inventory item {inventory_item_id}: {error_message}")
                all_activated = False
            else:
                _logger.info(f"Successfully activated location {pickup_location_id} for inventory item {inventory_item_id}.")

        return all_activated

    def update_pickup_order_status_to_shopify(self, mk_instance_id, fulfillment_order_ids):
        """
        Update the pickup status for the given fulfillment orders in Shopify.

        :param recordset mk_instance_id: Recordset of the mk.instance model.
        :param list fulfillment_order_ids: List of Shopify Fulfillment Order IDs.
        :return: Tuple containing a boolean indicating full success, and an error message string.
        :rtype: tuple(bool, str)
        """
        is_fully_updated, error = True, ""
        for fulfillment_order_id in fulfillment_order_ids:

            variables = {"fulfillmentOrderId": f"gid://shopify/FulfillmentOrder/{fulfillment_order_id}"}
            response = mk_instance_id.execute_graphql_query(UPDATE_PICKUP_STATUS, variables)
            user_errors = response.get("data") and response.get('data', {}).get('fulfillmentOrderLineItemsPreparedForPickup', {}).get('userErrors', [])
            # Parse the response
            if user_errors:
                error_message = ", ".join(error['message'] for error in user_errors)
                is_fully_updated = False
                error = _("UPDATE ORDER STATUS: Errors for fulfillment order %s: %s") % (fulfillment_order_id, error_message)
        return is_fully_updated, error

    def process_update_order_status_shopify(self, manual_process=False):
        """
        T6100 - Click & Collect Orders(Pickup Order)
        Modify this method to update pickup order status in shopify.
        """
        self.ensure_one()
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        order_id = self.sale_id
        if not order_id:
            log_message = _('UPDATE ORDER STATUS: There is no Sale Order not linked with this Delivery.')
            not manual_process and mk_log_line_dict['error'].append({'log_message': log_message})
            self.write({'is_marketplace_exception': True, 'exception_message': log_message})
            return False
        if not order_id.mk_id:
            log_message = _('UPDATE ORDER STATUS: Cannot find Marketplace Identification in Sale order %s.') % order_id.name
            not manual_process and mk_log_line_dict['error'].append({'log_message': log_message})
            self.write({'is_marketplace_exception': True, 'exception_message': log_message})
            return False
        try:
            variables = {"orderId": f"gid://shopify/Order/{order_id.mk_id}"}
            res = order_id.mk_instance_id.execute_graphql_query(GET_ORDERS_BY_ID, variables)
            user_errors = res and res.get('errors', [])
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify customers: %(errors)s") % {'errors': joined_errors})

            shopify_order_dict = res and res.get('data', {}) and res.get('data', {}).get('order', {}) if isinstance(res, dict) else {}
            if not shopify_order_dict:
                log_message = _('UPDATE ORDER STATUS: Order %s not found in Shopify using Shopify ID %s.') % (order_id.name, order_id.mk_id)
                self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                not manual_process and mk_log_line_dict['error'].append({'log_message': log_message})
                self.env.cr.commit()
                return False

            if shopify_order_dict and shopify_order_dict.get('cancelledAt') and shopify_order_dict.get('cancelReason'):
                log_message = _('UPDATE ORDER STATUS: Shopify order %s is already cancelled in Shopify.') % order_id.name
                self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                not manual_process and mk_log_line_dict['error'].append({'log_message': log_message})
                self.env.cr.commit()
                return False

            if shopify_order_dict and shopify_order_dict.get('displayFulfillmentStatus') == 'FULFILLED':
                self.write({'updated_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False})
                order_id.write({'updated_in_marketplace': True, 'fulfillment_status': 'FULFILLED'})
                not manual_process and mk_log_line_dict['success'].append({'log_message': _('UPDATE ORDER STATUS: Shopify order %s is already updated in Shopify.') % order_id.name})
                self.env.cr.commit()
                return True

            if shopify_order_dict and shopify_order_dict.get('displayFinancialStatus') == 'REFUNDED':
                log_message = _('UPDATE ORDER STATUS: You cannot fulfill Shopify order %s because it is refunded in Shopify.') % order_id.name
                self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                not manual_process and mk_log_line_dict['error'].append({'log_message': log_message})
                self.env.cr.commit()
                return False

            # Update dictionary by including is_pickup order or not and include the pickup location
            order_id.fetch_order_fulfillment_location_from_shopify(order_id.mk_instance_id, shopify_order_dict)
            if order_id.is_pickup:
                self.process_pickup_order_status_shopify(order_id, shopify_order_dict, manual_process, mk_log_line_dict)

            not order_id.is_pickup and order_id.update_shopify_order_line_location(shopify_order_dict)
            not order_id.is_pickup and self.process_picking_for_update_order_status_in_shopify(order_id, shopify_order_dict, manual_process)
        except MarketplaceException:
            raise
        except Exception as e:
            not manual_process and mk_log_line_dict['error'].append({'log_message': f'UPDATE ORDER STATUS: Shopify order {order_id.name}, ERROR: {e}.'})
            return False
        
        pickings = order_id.order_line.mapped('move_ids').mapped('picking_id').filtered(lambda p: p.location_dest_id.usage == 'customer')
        done_pickings = pickings.filtered(lambda p: p.updated_in_marketplace)
        if pickings and pickings == done_pickings and not order_id.is_pickup:
            order_id.write({'fulfillment_status': 'FULFILLED', 'updated_in_marketplace': True})
        elif done_pickings and not order_id.is_pickup:
            order_id.write({'fulfillment_status': 'PARTIALLY_FULFILLED'})
        self.env.cr.commit()
        return True


    def process_pickup_order_status_shopify(self, order_id, shopify_order_dict, manual_process, mk_log_line_dict):
        """
        T6100 - Click & Collect Orders(Pickup Order)
        Helper method to handle specific logic for Pickup orders.
        Args:
            order_id (recordset): Recordset of sale.order.
            shopify_order_dict (dict): Dictionary containing Shopify order details
            manual_process (boolean): Boolean flag indicating if this is a manual trigger (affects logging).
            mk_log_line_dict (dict): Dictionary containing log details (error and success)
        Returns:
            True/False (boolean): True if the process completed successfully, False otherwise.
        """
        line_item_mk_ids_list = [int(move.sale_line_id.mk_id) for move in self.move_ids if move.sale_line_id and move.sale_line_id.mk_id]

        # Change location in fulfillment if location is different that pickup location
        is_fully_changed, location_changed = self.change_pickup_location_for_shopify_fulfillment_order(order_id.mk_instance_id, shopify_order_dict, manual_process, mk_log_line_dict, line_item_mk_ids_list=line_item_mk_ids_list)
        location_changed and time.sleep(5)  # Allow some time for the fulfillment transfer to the pickup location to be properly reflected in the response.
        # Re-fetch fulfillment data
        order_id.fetch_order_fulfillment_location_from_shopify(order_id.mk_instance_id, shopify_order_dict)
        if is_fully_changed:
            # Identify Fulfillment Orders strictly related to this picking (Split into: All IDs for Backorders vs Updateable Fulfillment Order IDs for API)
            all_fulfillment_order_id_list = []  # For Backorders (Includes everything)
            fulfillment_order_id_list = []  # For API Call (Excludes already ready items)

            # NOTE: Using shopify_order_dict here. If location change generated NEW IDs,
            # ideally we should re-fetch 'fulfillmentOrders' via GraphQL here.
            # Assuming shopify_order_dict is still valid or updated by reference:
            line_items = shopify_order_dict.get('lineItems', {}).get('nodes', [])

            for line in line_items:
                if line.get('shipping_method') == 'PICK_UP' and extract_numeric_id(line.get('id')) in set(line_item_mk_ids_list):
                    all_fulfillment_order_id_list.append(line.get('fulfillment_order_id'))  # Always track for Backorder logic
                    if line.get('fulfillment_order_status') != 'IN_PROGRESS':  # Only track for API Update if not already ready
                        fulfillment_order_id_list.append(line.get('fulfillment_order_id'))

            all_fulfillment_order_id_list = list(set(all_fulfillment_order_id_list))

            # Mark fulfillment as ready for the pickup
            if fulfillment_order_id_list:
                is_fully_updated, log_message = self.update_pickup_order_status_to_shopify(order_id.mk_instance_id, list(set(fulfillment_order_id_list)))
                if not is_fully_updated:
                    self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                    not manual_process and mk_log_line_dict['success'].append({'log_message': log_message})
                    self.env.cr.commit()
                    return False

            # Mark current picking as updated_in_marketplace, means it marks fulfillment order related to current picking as a ready for pickup
            self.write({'updated_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False})

            # 5. Handle Backorders (Using ALL relevant Fulfillment Order IDs)
            # Find other Shopify Line IDs that belong to the same Fulfillment Orders
            processed_fo_ids = set(all_fulfillment_order_id_list)
            other_affected_line_ids = [
                extract_numeric_id(line.get('id'))
                for line in line_items
                if line.get('fulfillment_order_id') in processed_fo_ids
            ]
            self._update_backorder_fulfillment_status(affected_line_mk_ids=set(other_affected_line_ids), values={'updated_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False})

            # Update Main Order Status
            if all(order_id.order_line.mapped('move_ids').mapped('picking_id').mapped('updated_in_marketplace')):
                detected = order_id._detect_pickup_status_from_shopify(shopify_order_dict)
                order_id.write({'pickup_status': detected or 'ready_to_pickup'})

            return True
        return False  # Location change failed

    def process_picking_for_update_order_status_in_shopify(self, order_id, shopify_order_dict, manual_process=False):
        """
        Task: T5966 - Migrate remaining fulfillment from API to GraphQL in v19
        Migrated from Shopify REST API to GraphQL API.
        """
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        picking_vals = {'updated_in_marketplace': True, 'is_marketplace_exception': False, 'exception_message': False}
        if not order_id.is_pickup:
            if not order_id.order_line.mapped('mk_id'):
                log_message = _('Cannot update order status because Shopify Order Line ID not found in Order %s') % order_id.name
                mk_log_line_dict['error'].append({'log_message': 'UPDATE ORDER STATUS: ' + log_message})
                self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                return False

            fulfillment_result = self.update_fulfillment_value_to_shopify(order_id, shopify_order_dict)
            fulfillment_id = fulfillment_result.get('data', {}).get('fulfillmentCreate', {}).get('fulfillment').get('id') if isinstance(fulfillment_result, dict) and fulfillment_result.get('data', {}) else {}
            if not fulfillment_id:
                self.write({'is_marketplace_exception': True})
                return False
            picking_vals.update({'shopify_fulfillment_id': extract_numeric_id(fulfillment_id) if fulfillment_id else ""})

            self.write(picking_vals)
            if not manual_process:
                mk_log_line_dict['success'].append({'log_message': _('UPDATE ORDER STATUS: Successfully updated Shopify order %s') % order_id.name})
        return True

    def update_fulfillment_value_to_shopify(self, shopify_order_id, shopify_order_dict):
        """
        Task: T5966 - Migrate remaining fulfillment from API to GraphQL in v19
        Migrated from Shopify REST API to GraphQL API.
        """
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})
        line_item_dict = self.shopify_prepare_fulfillment_line_vals(shopify_order_dict)
        if not line_item_dict:
            log_message = _('Order lines not found for Shopify Order %s while trying to update Order status') % shopify_order_id.name
            mk_log_line_dict['error'].append({'log_message': 'UPDATE ORDER STATUS: ' + log_message})
            self.write({'is_marketplace_exception': True, 'exception_message': log_message})
            return False

        tracking_info = {"number": self.carrier_tracking_ref or '',
                         "url": self.carrier_tracking_url or None,
                         "company": self.carrier_id and self.carrier_id.shopify_code or self.carrier_id.name or ''}
        for fulfillment_order_id in line_item_dict:
            line_item_list = line_item_dict.get(fulfillment_order_id)
            # location_name_list.append(location_id)
            # thanks to https://stackoverflow.com/a/9427216
            # below line is used to remove duplicate dict because in Kit type product it may be possible that duplicate line dict will be created.
            line_item_list = [dict(t) for t in {tuple(d.items()) for d in line_item_list}]
            try:
                variables = {
                    "fulfillment": {
                        "notifyCustomer": shopify_order_id.mk_instance_id.is_notify_customer,
                        "trackingInfo": tracking_info,
                        "lineItemsByFulfillmentOrder": [{
                            "fulfillmentOrderId": fulfillment_order_id,
                            "fulfillmentOrderLineItems": line_item_list
                        }]
                    }
                }
                fulfillment_result = shopify_order_id.mk_instance_id.execute_graphql_query(CREATE_FULFILLMENT, variables)

                errors = fulfillment_result and fulfillment_result.get('errors', [])
                for error in errors:
                    log_message = _('Shopify Order %s is not updated due to some issue. REASON: %s') % (shopify_order_id.name, error.get("message"))
                    mk_log_line_dict['error'].append({'log_message': 'UPDATE ORDER STATUS: ' + log_message})
                    self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                    return False

                user_errors = fulfillment_result and fulfillment_result['data']['fulfillmentCreate']['userErrors']
                if fulfillment_result and user_errors:
                    error_messages = []
                    for err in user_errors:
                        log_message = _('Shopify Order %s is not updated due to some issue. REASON: %s') % (shopify_order_id.name, err.get("message"))
                        mk_log_line_dict['error'].append({'log_message': 'UPDATE ORDER STATUS: ' + log_message})
                        error_messages.append(log_message)
                    self.write({'is_marketplace_exception': True, 'exception_message': " | ".join(error_messages)})
                    return False

                elif fulfillment_result and not user_errors:
                    return fulfillment_result
            except Exception as e:
                log_message = f'Error while trying to update Order status of Shopify Order {shopify_order_id}.ERROR: {e}'
                mk_log_line_dict['error'].append({'log_message': f'UPDATE ORDER STATUS: {log_message}'})
                self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                return False

    def shopify_prepare_fulfillment_line_vals(self, shopify_order_dict):
        """
        Task: T5966 - Migrate remaining fulfillment from API to GraphQL in v19
        Migrated from Shopify REST API to GraphQL API.
        """
        self.ensure_one()
        line_item_dict = {}
        mrp = self.mk_instance_id._is_module_installed('mrp')
        # refund_line_item_dict = self._get_shopify_refund_line_ids(shopify_order_dict) # Try to manage removed line or quantity, but as from odoo it many possible that multiple pickings are created for the fulfillment, so we can't manage removed or adjusted (Edited Orders).
        for move in self.move_ids:
            line_mk_id = move.sale_line_id.mk_id and int(move.sale_line_id.mk_id) or False
            if int(move.quantity) <= 0 or not line_mk_id:
                continue
            if mrp and self.env['mrp.bom'].sudo()._bom_find(move.sale_line_id.product_id, bom_type='phantom'):
                quantity = int(move.sale_line_id.product_uom_qty)
            else:
                quantity = int(move.quantity)
            for fulfillment_order_id, fulfillment_order_line_item_id, fulfillable_quantity in self._get_shopify_fulfillment_line_data(move, shopify_order_dict, line_mk_id):
                if quantity <= 0:
                    break
                fulfillment_quantity = min(quantity, int(fulfillable_quantity or 0))
                if not (fulfillment_order_id and fulfillment_order_line_item_id and fulfillment_quantity > 0):
                    continue
                fo_gid = f"gid://shopify/FulfillmentOrder/{fulfillment_order_id}"
                fo_line_item_gid = f"gid://shopify/FulfillmentOrderLineItem/{fulfillment_order_line_item_id}"
                line_item_dict.setdefault(fo_gid, []).append({'id': fo_line_item_gid, 'quantity': fulfillment_quantity})
                quantity -= fulfillment_quantity
        return line_item_dict

    def _get_shopify_fulfillment_line_data(self, move, shopify_order_dict, line_mk_id):
        """
        Task T7767 - Get the Shopify fulfillment order ID and fulfillment order line item ID for a stock move by matching the move location with stored Shopify
        fulfillment split details. Falls back to the default Shopify line fulfillment data when no split match is found.
        Args:
            move (recordset): Stock move being fulfilled.
            shopify_order_dict (dict): Shopify order data.
            line_mk_id (int): Shopify order line item ID.
        Returns:
            tuple: (fulfillment_order_id, fulfillment_order_line_item_id) or (False, False) if no matching fulfillment data is found.
        """
        pending_states = move.sale_line_id.SHOPIFY_FULFILLMENT_ORDER_PENDING_STATES
        splits = move.sale_line_id.shopify_fulfillment_locations or []
        move_warehouse_id = move.warehouse_id or move.picking_id.picking_type_id.warehouse_id or move.location_id.warehouse_id
        pending_splits = [s for s in splits
                          if s.get('fulfillment_order_status') in pending_states
                          and s.get('fulfillment_order_id') and s.get('fulfillment_order_line_item_id')
                          and s.get('qty', 0) > 0]
        matched = []
        for split in pending_splits:
            loc = self.env['shopify.location.ts'].browse(split.get('shopify_location_record_id'))
            if move_warehouse_id and loc.order_warehouse_id and loc.order_warehouse_id == move_warehouse_id:
                matched.append(split)
        use_splits = matched or pending_splits
        if use_splits:
            return [(s.get('fulfillment_order_id'), s.get('fulfillment_order_line_item_id'), s.get('qty', 0)) for s in use_splits]
        fulfilment_line = [li for li in shopify_order_dict.get('lineItems', {}).get('nodes', [])
                           if extract_numeric_id(li.get('id')) == line_mk_id
                           and li.get('fulfillment_order_status') in pending_states]
        if fulfilment_line:
            li = fulfilment_line[0]
            return [(li.get('fulfillment_order_id'), li.get('fulfillment_order_line_item_id'), li.get('currentQuantity') or li.get('quantity') or 0)]
        return []

    def change_pickup_location_for_shopify_fulfillment_order(self, mk_instance_id, shopify_order_dict, manual_process, mk_log_line_dict, line_item_mk_ids_list=None):
        """
        T6100 - Click & Collect Orders(Pickup Order)
        T7441 - Ensure all items are stocked at the destination BEFORE the transfer products to pickup location.
        Updates the pickup location for fulfillment order in a Shopify order based on the provided `pickup_location_id`,
        only if the fulfillment order requires a transfer to the pickup location.
        Args:
            mk_instance_id (recordset): A recordset of the `mk.instance` model,
            shopify_order_dict (dict): Dictionary contains shopify order details.
            line_item_mk_ids_list (list): List of Shopify line item IDs for the current picking (used to filter fulfillment orders).
        Returns:
            bool: True if all requested fulfillment order locations were successfully updated, False otherwise.
        """
        pickup_location_id = shopify_order_dict.get('pickup_location_id', False) and extract_numeric_id(shopify_order_dict.get('pickup_location_id', False))
        if not pickup_location_id:
            return False

        is_fully_changed, location_changed = True, False
        if line_item_mk_ids_list is None:
            line_item_mk_ids_list = []

        # 1. Create a dictionary mapping fulfillment orders to their locations and ALL variant IDs
        fulfillment_order_map = {}
        for shopify_order_line_item in shopify_order_dict.get('lineItems', {}).get('nodes', []):
            fulfillment_order_id = shopify_order_line_item.get('fulfillment_order_id', False)
            shopify_line_id = extract_numeric_id(shopify_order_line_item.get('id'))

            # Only process this line if it exists in the current picking.
            if line_item_mk_ids_list and shopify_line_id not in line_item_mk_ids_list:
                continue

            if not fulfillment_order_id:
                continue

            # Initialize the dict key if it doesn't exist
            if fulfillment_order_id not in fulfillment_order_map:
                fulfillment_order_map[fulfillment_order_id] = {
                    'current_location_id': shopify_order_line_item.get('location_id', False),
                    'variant_ids': []
                }

            # Append every variant_id to the list
            variant_id = shopify_order_line_item.get('variant', {}) and shopify_order_line_item.get('variant', {}).get('id', '')
            if variant_id:
                fulfillment_order_map[fulfillment_order_id]['variant_ids'].append(extract_numeric_id(variant_id))

        # 2. Process the GraphQL calls based on the grouped dictionary
        for fulfillment_order_id, data in fulfillment_order_map.items():
            fulfillment_location_id = data.get('current_location_id')
            item_ids = data.get('variant_ids')

            if pickup_location_id and fulfillment_location_id and fulfillment_location_id != pickup_location_id:
                # T7441 - Ensure all items are stocked at the destination BEFORE the move products to pickup location
                _logger.info(f"Proactively activating location {pickup_location_id} for items: {item_ids}")
                self._activate_shopify_location_for_fulfillment(mk_instance_id, pickup_location_id, item_ids)

                variables = {
                    "id": f"gid://shopify/FulfillmentOrder/{fulfillment_order_id}",
                    "newLocationId": f"gid://shopify/Location/{pickup_location_id}"
                }

                # Execute the move once all items are guaranteed to be active
                response = mk_instance_id.execute_graphql_query(CHANGE_LOCATION_OF_FULFILLMENT_ORDER, variables)
                location_changed = True

                # Parse responses
                data_resp = response.get("data") if response else {}
                user_errors = data_resp and data_resp.get('fulfillmentOrderMove', {}).get('userErrors', [])

                # Handle Final Errors (these should now only be non-inventory errors, e.g., permissions)
                if user_errors:
                    error_message = ", ".join(error['message'] for error in user_errors)
                    is_fully_changed, location_changed = False, False
                    log_message = _("UPDATE FULFILLMENT ORDER LOCATION: Errors for fulfillment order %s: %s") % (fulfillment_order_id, error_message)
                    not manual_process and mk_log_line_dict['success'].append({'log_message': log_message})
                    self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                    _logger.error(log_message)
                elif response and response.get("errors"):
                    messages = ", ".join(err.get("message", "") for err in response["errors"])
                    is_fully_changed, location_changed = False, False
                    log_message = _("GraphQL Errors while updating pickup location for fulfillment order %s: %s") % (fulfillment_order_id, messages)
                    not manual_process and mk_log_line_dict['success'].append({'log_message': log_message})
                    self.write({'is_marketplace_exception': True, 'exception_message': log_message})
                    _logger.error(log_message)

        return is_fully_changed, location_changed

    def action_already_picked_up(self):
        """
        T6100 - Click & Collect Orders(Pickup Order)
        Mark a Shopify order as picked up.
        This method checks the current fulfillment status of a Shopify order and updates the corresponding Odoo sale order and mark marketplace order as fulfilled.
        Returns:
            bool: True if the Shopify order were successfully updated, False if an error occurred.
        """
        self.ensure_one()
        order_id = self.sale_id
        mk_instance_id = order_id.mk_instance_id
        mk_instance_id.connection_to_shopify()
        try:
            # Create a set of Shopify Line Item IDs present in the current picking.
            line_mk_ids_set = {
                int(move.sale_line_id.mk_id)
                for move in self.move_ids
                if move.sale_line_id and move.sale_line_id.mk_id
            }
            variables = {"orderId": f"gid://shopify/Order/{order_id.mk_id}"}
            res = mk_instance_id.execute_graphql_query(GET_ORDERS_BY_ID, variables)
            shopify_order_dict = res.get('data', {}).get('order', {}) if isinstance(res, dict) else {}

            if shopify_order_dict.get('cancelledAt') and shopify_order_dict.get('cancelReason'):
                _logger.error(f"Cannot mark order {order_id.name} as picked up — the order is already cancelled in Shopify.")
                self.env.cr.commit()
                return False
            if shopify_order_dict.get('displayFulfillmentStatus') == 'FULFILLED':
                _logger.error(f"Order {order_id.name} is already fulfilled in Shopify. Marking as 'already picked up' in Odoo.")
                order_id.write({'fulfillment_status': 'FULFILLED', 'updated_in_marketplace': True, 'pickup_status': 'already_pickup'})
                self.write({'is_picked_up_in_marketplace': True})
                self.env.cr.commit()
                return True
            if shopify_order_dict.get('displayFinancialStatus') == 'REFUNDED':
                _logger.error(f"You cannot Marking shopify order as 'already picked up' {order_id.name} because it is refunded in Shopify.")
                self.env.cr.commit()
                return False
            if not order_id:
                _logger.error(f'There is no Sale Order found while processing pickup update for order: {order_id.name}')
                return False
            if not order_id.mk_id:
                _logger.error(f'Cannot find Marketplace Identification in Sale order while processing pickup update for order: {order_id.name}')
                return False

            response = mk_instance_id.execute_graphql_query(FETCH_FULFILLMENT, variables)
            fulfillment_data_list = response.get('data', {}).get('order', {}).get('fulfillmentOrders', [])
            fulfillment_order_id_list = []
            for fulfillment in fulfillment_data_list:
                if fulfillment and fulfillment.get('status', '') not in ['SUCCESS', 'OPEN', 'PENDING', 'IN_PROGRESS']:
                    continue

                # Check if this fulfillment order contains ANY line items from our current picking
                line_items = fulfillment.get('lineItems', {})
                is_match = any(extract_numeric_id(item.get('lineItem', {}).get('id')) in line_mk_ids_set for item in line_items)
                is_match and fulfillment_order_id_list.append(extract_numeric_id(fulfillment.get('id')))

            if not isinstance(fulfillment_order_id_list, list):
                fulfillment_order_id_list = [fulfillment_order_id_list]
            fulfillment_order_id_list = list(set(fulfillment_order_id_list))
            is_fully_updated = self.mark_order_as_picked_up_in_shopify(mk_instance_id, fulfillment_order_id_list)
            if is_fully_updated:
                self.write({'is_picked_up_in_marketplace': True})
                # Shopify marks ALL items in a Fulfillment Order as fulfilled when it is picked up.
                # Find all line items from the processed Fulfillment Orders so related backorders can also be marked as picked up.

                affected_line_ids = {
                    extract_numeric_id(fulfillment_line_item.get('lineItem', {}).get('id'))
                    for fulfillment in fulfillment_data_list
                    if extract_numeric_id(fulfillment.get('id')) in fulfillment_order_id_list
                    for fulfillment_line_item in fulfillment.get('lineItems', [])
                    if extract_numeric_id(fulfillment_line_item.get('lineItem', {}).get('id'))
                }

                affected_line_ids and self._update_backorder_fulfillment_status(affected_line_mk_ids=affected_line_ids, values={'is_picked_up_in_marketplace': True})

                if all(order_id.order_line.mapped('move_ids').mapped('picking_id').mapped('is_picked_up_in_marketplace')):
                    order_id.write({'fulfillment_status': 'FULFILLED', 'updated_in_marketplace': True, 'pickup_status': 'already_pickup'})
            else:
                _logger.error(f"Failed to mark Shopify order {order_id.name} as picked up — fulfillment update unsuccessful.")
                return False
            return True
        except Exception as e:
            _logger.error(f'Exception while marking Shopify order {order_id.name} as picked up, ERROR: {e}.')
            return False

    def mark_order_as_picked_up_in_shopify(self, mk_instance_id, fulfillment_order_ids):
        """
        T6100 - Click & Collect Orders(Pickup Order)
        Mark Shopify fulfillment orders as picked up (fulfilled) for Click & Collect.
        Args:
            mk_instance_id (recordset): A recordset of the `mk.instance` model,
            fulfillment_order_ids (list): A list of Shopify fulfillment order IDs that should be marked as picked up (fulfilled).
        Returns:
            is_fully_updated (bool):
                    - True if all fulfillment orders were successfully updated(mark as picked up),
                    - False if one or more updates failed.
        """
        is_fully_updated = True
        for fulfillment_order_id in fulfillment_order_ids:
            variables = {
                "fulfillment": {
                    "lineItemsByFulfillmentOrder": [
                        {
                            "fulfillmentOrderId": f"gid://shopify/FulfillmentOrder/{fulfillment_order_id}"
                        }
                    ]
                }
            }
            response = mk_instance_id.execute_graphql_query(CREATE_FULFILLMENT, variables)

            data = response.get("data", {})
            user_errors = data.get("fulfillmentCreate", {}).get("userErrors", [])
            if user_errors:
                messages = ", ".join(e.get("message", "") for e in user_errors)
                is_fully_updated = False
                _logger.error(f"Failed to mark fulfillment order {fulfillment_order_id} as picked up. Shopify returned user errors: {messages}")
            elif response.get("errors"):
                messages = ", ".join(err.get("message", "") for err in response["errors"])
                is_fully_updated = False
                _logger.error(f"GraphQL error while marking fulfillment order {fulfillment_order_id} as picked up: {messages}")
        return is_fully_updated

    def _update_backorder_fulfillment_status(self, affected_line_mk_ids, values):
        """
        T6100 - Click & Collect Orders(Pickup Order)
        Common logic to update backorders if they share items with a Shopify Fulfillment Order that was just processed.
        Args:
            affected_line_mk_ids (set): Set of Shopify Line Item IDs (integers) processed in the main order.
            values (dict): Dictionary of values to write to the matching backorders.
        Returns:
            updated_pickings (recordset): Recordset of updated pickings.
        """
        updated_pickings = self.env['stock.picking']

        backorder_domain = [('sale_id', '=', self.sale_id.id), ('id', '!=', self.id), ('state', '!=', 'cancel')]

        if values and values.get('is_picked_up_in_marketplace', False):
            backorder_domain.append(('is_picked_up_in_marketplace', '=', False))
        elif values and values.get('updated_in_marketplace', False):
            backorder_domain.append(('updated_in_marketplace', '=', False))

        backorders = self.env['stock.picking'].search(backorder_domain)

        for picking in backorders:
            # Check if this picking contains any of the affected Shopify Line IDs
            if any(move.sale_line_id.mk_id and int(move.sale_line_id.mk_id) in affected_line_mk_ids for move in picking.move_ids):
                picking.write(values)
                updated_pickings |= picking

        return updated_pickings

    def _send_confirmation_email(self):
        newself = self
        for stock_pick in self.filtered(lambda p: p.company_id.stock_move_email_validation and p.picking_type_id.code == 'outgoing'):
            if stock_pick.sale_id.marketplace == 'shopify' and stock_pick.sale_id.mk_instance_id.is_notify_customer:
                newself -= stock_pick
        return super(StockPicking, newself)._send_confirmation_email()
