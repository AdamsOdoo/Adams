import logging

from odoo import models, fields, _, tools
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException

_logger = logging.getLogger("Teqstars:Shopify")

CONTINUE_SELLING = [('CONTINUE', 'Allow'), ('DENY', 'Deny')]
WEIGHT_UNIT = [('g', 'Gram'), ('kg', 'KG'), ('oz', 'Oz'), ('lb', 'LB')]
INVENTORY_MANAGEMENT = [('shopify', 'Track Quantity'), ('dont_track', 'Dont track Inventory')]


class MkListingItem(models.Model):
    _inherit = "mk.listing.item"

    def _get_default_taxable_value(self):
        is_taxable = False
        if self.mk_listing_id:
            is_taxable = self.mk_listing_id.is_taxable
        return is_taxable

    def _get_default_weight_unit(self):
        product_weight_in_lbs_param = self.env['ir.config_parameter'].sudo().get_param('product.weight_in_lbs')
        if product_weight_in_lbs_param == '1':
            return 'lb'
        else:
            return 'kg'

    def _compute_shopify_inventory(self):
        for rec in self:
            # Task: T7653 - Removed is_third_party_location field.
            location_ids = self.env['shopify.location.ts'].search([('mk_instance_id', '=', rec.mk_instance_id.id), ('is_import_export_stock', '=', True)])
            shopify_current_stock = 0.0
            for shopify_location_id in location_ids:
                export_location_ids = shopify_location_id.export_location_ids
                for export_location_id in export_location_ids:
                    variant_quantity = rec.product_id.get_product_stock(rec.export_qty_type, rec.export_qty_value, export_location_id, rec.mk_instance_id.sudo().stock_field_id.name)
                    shopify_current_stock += variant_quantity
            rec.shopify_current_stock = shopify_current_stock

    # Task:- T7796 Added Sales Channel fields.
    shopify_sales_channel_ids = fields.Many2many(comodel_name='shopify.sales.channels.ts',string='Shopify Sales Channels', relation='mk_listing_item_sales_channels_rel',
        column1='listing_item_id',column2='sales_channel_id',)
    skip_listing_sync = fields.Boolean(related='mk_listing_id.skip_listing_sync', string='Skip Listing Sync', readonly=True)

    inventory_item_id = fields.Char('Inventory Item ID')
    shopify_image_id = fields.Char("Shopify Image ID")
    inventory_management = fields.Selection(INVENTORY_MANAGEMENT, default='shopify')
    continue_selling = fields.Selection(CONTINUE_SELLING, help='If true then Customer can place order while product is out of stock.')
    is_taxable = fields.Boolean("Charge tax on this product?", default=_get_default_taxable_value)
    weight_unit = fields.Selection(WEIGHT_UNIT, default=_get_default_weight_unit, help='The unit of measurement that applies to the product variant weight.')
    shopify_last_stock_update_date = fields.Datetime("Shopify Last Stock Updated On", copy=False, help="Date were stock updated to Shopify.")
    shopify_current_stock = fields.Float(string="Shopify Inventory", compute="_compute_shopify_inventory")

    def open_shopify_inventory(self):
        return True

    def write(self, values):
        """
        Raise error when user try to add more than one image in listing item and, add listing and listing item id in Newly added images in listing item.
        """
        res = super(MkListingItem, self).write(values)
        for record in self:
            if values.get('image_ids') and len(record.image_ids) > 1 and record.mk_instance_id.marketplace == 'shopify':
                raise MarketplaceException(_("Shopify only accept one image per variant"))

            if values.get('image_ids') and record.image_ids and (not record.image_ids[0].mk_listing_id or not record.image_ids[0].mk_listing_item_ids) and record.mk_instance_id.marketplace == 'shopify':
                record.image_ids[0].mk_listing_id = record.mk_listing_id.id
                record.image_ids[0].mk_listing_item_ids = record.ids
        return res

    def shopify_open_update_listing_item_view(self):
        """
        Task: T6152 - Add Stock & Price Update Functionality from Listing Items
        This method opens the update listing item operation view for the Shopify. It prepares and returns the action required
        to update stock and price for already exported (listed) Shopify listing items. The method reuses the base marketplace update view and sets the
        appropriate context for performing the update operation.
        Returns:
            dict: Action dictionary to open the Shopify listing item update view.
        """
        action = self.env.ref('base_marketplace.action_update_listing_item_to_marketplace').sudo().read()[0]
        action['name'] = _("Update Listing Item in Shopify")
        action['views'] = [(self.env.ref('shopify.mk_operation_update_listing_item_to_shopify_view').sudo().id, 'form')]
        ctx = self.env.context.copy()
        # Task:- T7796 - Pre-fill sales channels from all selected listing items (single or multi-select).
        active_ids = ctx.get('active_ids') or []
        listing_items = self.browse(active_ids) if active_ids else self
        shopify_sales_channel_ids = listing_items.mapped('shopify_sales_channel_ids').ids
        ctx['default_shopify_sales_channel_ids'] = [(6, 0, shopify_sales_channel_ids)]
        first_item = listing_items[:1]
        ctx['default_mk_instance_id'] = first_item.mk_instance_id.id if first_item else False
        ctx['default_is_publish_or_unpublish'] = True
        action['context'] = ctx
        return action

    def shopify_open_manage_sales_channels_view(self):
        """
        Task: T7796 - Opens the Manage Sales Channels wizard for this listing item.
        Returns:
            dict: Action dictionary to open the Shopify sales channels wizard.
        """
        self.ensure_one()
        action = self.env.ref('shopify.action_shopify_product_publications_wizard').sudo().read()[0]
        action['context'] = {
            'active_model': 'mk.listing.item',
            'active_record_id': self.id,
            'default_mk_instance_id': self.mk_instance_id.id,
            'default_shopify_sales_channel_ids': [(6, 0, self.shopify_sales_channel_ids.ids)],
        }
        return action

    def shopify_update_listing_item_to_mk(self, operation_wizard):
        """
        Task: T6152 - Add Stock & Price Update Functionality from Listing Items
        Task: T7468 - Raise a redirect warning for the location with a dynamic error message and open the corresponding location form view.
        This method performs update of stock quantity and/or price for Shopify listing items.
        The update operation is controlled by the options selected in the operation wizard.
        Args:
            operation_wizard (recordset): Recordset of 'mk.operation'.
        Raises:
            MarketplaceException: If required Shopify locations are missing or misconfigured, or if validation fails before performing the update.
        """
        mk_instance_id = self.mk_instance_id
        location_ids = self.env['shopify.location.ts']
        listing_obj = self.env['mk.listing']
        is_set_quantity = operation_wizard.is_set_quantity
        is_set_price = operation_wizard.is_set_price
        if is_set_quantity:
            # Task: T7653 - Removed is_third_party_location field.
            location_ids = self.env['shopify.location.ts'].search(
                [('mk_instance_id', '=', mk_instance_id.id), ('is_import_export_stock', '=', True)])
            if not location_ids:
                error_msg = _("Please enable at list one Shopify Location for import/export inventory.")
                mk_instance_id.show_shopify_location_redirect_warning(error_msg, location_ids)
            for shopify_location_id in location_ids:
                warehouse_id = shopify_location_id.order_warehouse_id or False
                if not warehouse_id:
                    error_msg = _("Please set Warehouse and Location in the Shopify Location %s") % shopify_location_id.name
                    mk_instance_id.show_shopify_location_redirect_warning(error_msg, shopify_location_id)
        mk_instance_id.connection_to_shopify()
        try:
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
            mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})

            # Task: T7796 - Skip listing items whose parent listing has sync disabled
            skipped_items = self.filtered(lambda item: item.mk_listing_id.skip_listing_sync)
            for item in skipped_items:
                mk_log_line_dict['error'].append({'log_message': _("SKIP: Listing item %s (%s) skipped — parent listing '%s' has sync disabled.") % (item.name, item.mk_id, item.mk_listing_id.name)})
            active_items = self - skipped_items
            if not active_items:
                self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_instance_id=mk_instance_id, mk_log_line_dict=mk_log_line_dict)
                return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log') if mk_log_id.log_line_ids else True
            self = active_items

            for listing_item_batch in tools.split_every(250, self, piece_maker=list):
                filtered_listing_item_ids = []
                price_update_item_ids = []
                for listing_item_id in listing_item_batch:
                    if is_set_price:
                        price_update_item_ids.append(listing_item_id)
                    if is_set_quantity and listing_item_id.inventory_management == 'shopify' and listing_item_id.product_id.is_storable:
                        filtered_listing_item_ids.append(listing_item_id)

                if filtered_listing_item_ids:
                    # Use a separate dict for quantity sync. The bulk inventory worker flushes its own
                    # entries via _handle_shopify_log_creation per batch; sharing the outer dict would
                    # cause those EXPORT STOCK entries to be re-flushed by shopify_update_product_price
                    # (and any later flush), producing duplicate log lines.
                    qty_log_line_dict = {'error': [], 'success': []}
                    formated_listing_items = listing_obj.prepare_bulk_inventory_update_vals(mk_instance_id, filtered_listing_item_ids, location_ids, mk_log_id)
                    listing_obj.with_context(manual_operation=True).run_bulk_shopify_inventory_update_perfect(mk_instance_id, formated_listing_items, mk_log_id, qty_log_line_dict)

                # IMPROVEMENT: Filter the list to only include records that still exist in the database
                valid_price_update_items = [item for item in price_update_item_ids if item.exists()]
                valid_price_update_items and listing_obj.with_context(is_manual_update_price=True).shopify_update_product_price(mk_instance_id, listing_item_ids=valid_price_update_items,
                                                                                                                             mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
                self.env.cr.commit()

            # Task:- T7796 Process Shopify sales channel publish/unpublish operations.
            if operation_wizard.shopify_sales_channel_ids:
                publish = operation_wizard.is_publish_or_unpublish
                ctx_key = 'publish_shopify_product' if publish else 'unpublish_shopify_product'
                sales_channels_wizard = self.env['shopify.sales.channels.wizard'].create({'shopify_sales_channel_ids': [(6, 0, operation_wizard.shopify_sales_channel_ids.ids)]})
                sales_channel_ids_list = operation_wizard.shopify_sales_channel_ids.mapped('sales_channel_id')
                channel_log_line_dict = {'error': [], 'success': []}
                for listing_item in self:
                    sales_channels_wizard.with_context(**{ctx_key: True}).shopify_listing_item_sales_channels(sales_channel_ids_list, listing_item, mk_instance_id, channel_log_line_dict)
                self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_instance_id=mk_instance_id, mk_log_line_dict=channel_log_line_dict)

            if mk_log_id.exists() and mk_log_id.log_line_ids:
                return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
            elif mk_log_id and not mk_log_id.log_line_ids:
                mk_log_id.unlink()
        except Exception as e:
            _logger.info("Stock and Price update failed for one or more listing items. Due to reason: %s" % e)
        return True
