from datetime import timedelta

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException

SHOPIFY_OPERATIONS = [('import', 'Import'),
                      ('export', 'Export')]

SHOPIFY_IMPORT_OPERATIONS = [('import_customers', 'Import Customers'),
                             ('import_orders', 'Import Orders'),
                             ('import_listings', 'Import Listings'),
                             ('import_stock', 'Import Inventory'),
                             ('import_payout_report', 'Import Payout Report'),
                             ('import_collections', 'Import Collections'),
                             ('import_catalogs', 'Import Catalogs'),
                             ('import_returns', 'Import Returns')
                             ]

SHOPIFY_EXPORT_OPERATIONS = [('export_listings', 'Export Listings'),
                             ('update_listings', 'Update Listings'),
                             ('update_prices', 'Export Prices'),
                             ('update_stock', 'Export Inventory'),
                             ('update_order_status', 'Export Tracking Details'),
                             ('export_collections', 'Export Collections'),
                             ('update_collections', 'Update Collections'),
                             ('update_catalogs', 'Update Catalogs')]


class MarketplaceOperation(models.TransientModel):
    _inherit = "mk.operation"

    def _get_default_listing_from_date(self):
        mk_instance_id = self.env.context.get('active_id')
        mk_instance_id = self.env['mk.instance'].search([('id', '=', mk_instance_id)], limit=1)
        from_date = mk_instance_id.last_listing_import_date if mk_instance_id.last_listing_import_date else fields.Datetime.now() - timedelta(30)
        from_date = fields.Datetime.to_string(from_date)
        return from_date

    def _get_default_listing_to_date(self):
        to_date = fields.Datetime.now()
        to_date = fields.Datetime.to_string(to_date)
        return to_date

    def _get_default_payout_from_date(self):
        mk_instance_id = self.env.context.get('active_id')
        mk_instance_id = self.env['mk.instance'].search([('id', '=', mk_instance_id)], limit=1)
        from_date = mk_instance_id.payout_report_last_sync_date if mk_instance_id.payout_report_last_sync_date else fields.Datetime.now() - timedelta(3)
        from_date = fields.Date.to_string(from_date)
        return from_date

    def _get_default_payout_to_date(self):
        to_date = fields.Datetime.now().date()
        to_date = fields.Date.to_string(to_date)
        return to_date

    def _get_default_return_from_date(self):
        mk_instance_id = self.env.context.get('active_id')
        mk_instance_id = self.env['mk.instance'].search([('id', '=', mk_instance_id)], limit=1)
        from_date = mk_instance_id.last_return_import_date if mk_instance_id.last_return_import_date else fields.Datetime.now() - timedelta(7)
        return fields.Datetime.to_string(from_date)

    def _get_default_return_to_date(self):
        return fields.Datetime.to_string(fields.Datetime.now())

    shopify_operations = fields.Selection(SHOPIFY_OPERATIONS, string="Shopify Operation", default='import')

    # Marketplace Import Fields
    import_collections = fields.Boolean("Import Collections")
    shopify_import_operations = fields.Selection(SHOPIFY_IMPORT_OPERATIONS, string="Shopify Import Operation", default='import_customers')
    from_listing_date = fields.Datetime("Shopify From Listing Date", default=_get_default_listing_from_date)
    to_listing_date = fields.Datetime("Shopify To Listing Date", default=_get_default_listing_to_date)
    import_date_based_on = fields.Selection([("created_at_min", "Create Date"), ("updated_at_min", "Update Date")], default="updated_at_min", string="Shopify Based On")

    # Marketplace Export Fields
    is_export_collection = fields.Boolean("Export Collections?")
    is_update_collection = fields.Boolean("Update Collections?")
    shopify_export_operations = fields.Selection(SHOPIFY_EXPORT_OPERATIONS, string="Shopify Export Operation", default='export_listings')

    # Shopify Payout Fields
    from_payout_date = fields.Date("Shopify From Payout Date", default=_get_default_payout_from_date)
    to_payout_date = fields.Date("Shopify To Payout Date", default=_get_default_payout_to_date)

    # Shopify Return Fields
    from_return_date = fields.Datetime("Shopify From Return Date", default=_get_default_return_from_date)
    to_return_date = fields.Datetime("Shopify To Return Date", default=_get_default_return_to_date)

    # Shopify Customer Fields
    mk_customer_id = fields.Char("Marketplace Customer ID", help="Used to import specific Customer from Marketplace using Marketplace ID.")

    # Shopify Customer Fields
    shopify_import_draft_products = fields.Boolean("Shopify Import Only Draft Products?", help="When enabled, connector will only import draft products from Shopify.")

    # shopify publications
    shopify_sales_channel_ids = fields.Many2many(
        comodel_name="shopify.sales.channels.ts",
        string="Shopify Sales Channels",
        relation="mk_operation_shopify_sales_channel_wizard_rel",
        help="Select the Shopify sales channels (publications)."
    )

    #  publish or unpublish
    is_publish_or_unpublish = fields.Boolean(string="Shopify Publish/Unpublish",
                                             help="Enable to publish the product to the sales channels selected above. Disable to unpublish it from those sales channels.")
    last_update_price_date = fields.Datetime(string="Last price updated On", related='mk_instance_id.last_listing_price_update_date', readonly=False,
                                             help='This is the date when the price was last updated. The export will use this date to fetch the latest price.')
    last_update_stock_date = fields.Datetime(string="Last stock updated On", related='mk_instance_id.last_stock_update_date', readonly=False,
                                             help='This is the date when the stock was last updated. The export will use this date to fetch the most recent stock data.')
    # Shopify Markets / Catalogs fields
    mk_catalog_id = fields.Char("Marketplace Catalog ID", help="Used to import specific Catalog from Marketplace using Marketplace ID. Leave empty to import all catalogs.")
    shopify_catalog_id = fields.Many2one('shopify.catalog.ts', string="Catalog",
                                         help="Catalog that the picked listings will be attached to as variant price rows.")
    add_listing_ids = fields.Many2many('mk.listing', relation='mk_operation_add_listing_catalog_rel',
                                       column1='operation_id', column2='listing_id', string="Listings to Add",
                                       help="Every variant of each selected listing will be added to the target catalog.")

    collection_source_id = fields.Many2one('shopify.collection.source.ts', string="Collection Source", help="Source the selected items are added to.")
    add_selection_listing_ids = fields.Many2many('mk.listing', relation='mk_operation_source_selection_rel', column1='operation_id', column2='listing_id', string="Products to Include",
                                                 help="Products to add to this source by hand.")
    add_selection_item_ids = fields.Many2many('mk.listing.item', relation='mk_operation_source_selection_item_rel', column1='operation_id', column2='item_id', string="Variants to Include",
                                              help="Variants to add to this source.")
    add_sub_collection_ids = fields.Many2many('shopify.collection.ts', relation='mk_operation_source_collection_rel', column1='operation_id', column2='collection_id', string="Collections to Add",
                                              help="Collections whose products are added to this source.")

    def action_add_products_to_source(self):
        """
        Task: T8887 - Save the products chosen in the popup as the products added by hand to the source.
            A product removed in the popup is removed from the source too.
        Returns:
            dict: Action that closes the popup.
        Raises:
            MarketplaceException: If no source is given or the products belong to another instance.
        """
        self.ensure_one()
        source = self.collection_source_id
        if not source:
            raise MarketplaceException(_("Please select a target source."))
        listings = self.add_selection_listing_ids.filtered(lambda listing: listing.mk_instance_id == source.mk_instance_id)
        if self.add_selection_listing_ids and not listings:
            raise MarketplaceException(_("The selected products belong to another instance than the collection."))
        kept_variants = source.selection_item_ids.filtered(lambda item: item.mk_listing_id in listings)
        source.selection_listing_ids = [(6, 0, listings.ids)]
        source.selection_item_ids = [(6, 0, kept_variants.ids)]
        return {'type': 'ir.actions.act_window_close'}

    def action_add_variants_to_source(self):
        """
        Task: T8887 - Save the variants chosen in the popup as the variants added by hand to the source.
            The product of each variant is added with it.
        Returns:
            dict: Action that closes the popup.
        Raises:
            MarketplaceException: If no source is given or the variants belong to another instance.
        """
        self.ensure_one()
        source = self.collection_source_id
        if not source:
            raise MarketplaceException(_("Please select a target source."))
        picked_variants = self.add_selection_item_ids.filtered(lambda item: item.mk_instance_id == source.mk_instance_id)
        if self.add_selection_item_ids and not picked_variants:
            raise MarketplaceException(_("The selected variants belong to another instance than the collection."))
        source.selection_listing_ids = [(6, 0, picked_variants.mk_listing_id.ids)]
        source.selection_item_ids = [(6, 0, picked_variants.ids)]
        return {'type': 'ir.actions.act_window_close'}

    def action_add_collections_to_source(self):
        """
        Task: T8887 - Save the collections chosen in the popup as the collections this source takes products from.
        Returns:
            dict: Action that closes the popup.
        Raises:
            MarketplaceException: If no source is given or a collection belongs to another instance.
        """
        self.ensure_one()
        source = self.collection_source_id
        if not source:
            raise MarketplaceException(_("Please select a target source."))
        collections = self.add_sub_collection_ids.filtered(lambda collection: collection.mk_instance_id == source.mk_instance_id) - source.collection_id
        if not collections:
            raise MarketplaceException(_("A Collections source needs at least one collection of the same instance, " "and a collection cannot pull from itself."))
        source.sub_collection_ids = [(6, 0, collections.ids)]
        return {'type': 'ir.actions.act_window_close'}

    def action_add_listings_to_catalog(self):
        """ Fan out each picked listing's variants into shopify.catalog.variant.price.ts
            rows under the target catalog. Skip variants already on the catalog, variants
            without a marketplace ID, and listings outside the catalog's instance. Seeds
            price from mk.listing.item.sale_price (instance pricelist).
        """
        self.ensure_one()
        catalog = self.shopify_catalog_id
        if not catalog:
            raise MarketplaceException(_("Please select a target catalog."))
        if not self.add_listing_ids:
            raise MarketplaceException(_("Please select at least one listing."))

        variant_price_obj = self.env['shopify.catalog.variant.price.ts']
        existing_item_ids = set(catalog.variant_price_ids.mk_listing_item_id.ids)

        rows = []
        for listing in self.add_listing_ids:
            if listing.mk_instance_id != catalog.mk_instance_id:
                continue
            for item in listing.listing_item_ids:
                if not item.mk_id or item.id in existing_item_ids:
                    continue
                rows.append({
                    'catalog_id': catalog.id,
                    'mk_listing_id': listing.id,
                    'mk_listing_item_id': item.id,
                    'price': item.sale_price or 0.0,
                    'origin_type': 'RELATIVE',
                })
                existing_item_ids.add(item.id)

        if rows:
            variant_price_obj.create(rows)
        return {'type': 'ir.actions.act_window_close'}

    @api.onchange("shopify_operations", "shopify_import_operations", "shopify_export_operations")
    def onchange_shopify_operations(self):
        if not self.mk_instance_id:
            raise True
        if self.marketplace == 'shopify':
            if self.shopify_operations == 'import':
                selected_operation = self.shopify_import_operations
            else:
                selected_operation = self.shopify_export_operations
            self.do_check_cron_status(self.shopify_operations, selected_operation)

    @api.model
    def default_get(self, default_fields):
        # T7796: Ensure selected listing items belong to a single marketplace instance.
        res = super(MarketplaceOperation, self).default_get(default_fields)
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if active_model == 'mk.listing.item' and active_ids:
            listing_item = self.env[active_model].browse(active_ids)
            if len(listing_item.mapped('mk_instance_id')) > 1:
                raise MarketplaceException(_('Operation not allowed! Make sure selected listing item belongs to only one instance'))
        return res

    def do_shopify_operations(self):
        instance = self.mk_instance_id
        if not instance:
            raise MarketplaceException(_("Please select marketplace instance to process."))

        if self.shopify_operations == 'import':
            action = self.handle_shopify_import_operations(instance)
        else:
            action = self.handle_shopify_export_operations(instance)
        return action

    def handle_shopify_import_operations(self, instance):
        action = {}
        if self.shopify_import_operations == 'import_customers':
            action = self.env['res.partner'].shopify_import_customers(instance, mk_customer_id=self.mk_customer_id)
        if self.shopify_import_operations == 'import_listings':
            action = self.env['mk.listing'].with_context(import_date_based_on=self.import_date_based_on).shopify_import_listings(
                instance, self.from_listing_date, self.to_listing_date, mk_listing_id=self.mk_listing_id, update_product_price=self.update_product_price,
                update_existing_product=self.update_existing_product, import_draft_products=self.shopify_import_draft_products)
        if self.shopify_import_operations == 'import_stock':
            self.env['mk.listing'].shopify_import_stock(instance)
        if self.shopify_import_operations == 'import_orders':
            action = self.env['sale.order'].with_context(from_import_screen=True).shopify_import_orders(instance, self.from_date, self.to_date, mk_order_id=self.mk_order_id)
        if self.shopify_import_operations == 'import_collections':
            action = self.env['shopify.collection.ts'].import_shopify_collections(instance)
        if self.shopify_import_operations == 'import_payout_report':
            action = self.env['shopify.payout'].shopify_import_payout_report(instance, self.from_payout_date, self.to_payout_date)
        if self.shopify_import_operations == 'import_catalogs':
            action = self.env['shopify.catalog.ts'].import_catalogs_from_shopify(instance, mk_catalog_id=self.mk_catalog_id)
        if self.shopify_import_operations == 'import_returns':
            action = self.env['shopify.return.ts'].import_shopify_returns(instance, from_date=self.from_return_date, to_date=self.to_return_date)
        if action and type(action) == dict:
            return action
        return action

    def handle_shopify_export_operations(self, instance):
        if self.shopify_export_operations == 'export_listings':
            self.is_set_price = True
            self.is_update_product = True
            self.is_set_images = True
            return self.export_listing_to_mk()
        if self.shopify_export_operations == 'update_listings':
            return self.update_listing_to_mk()
        if self.shopify_export_operations == 'update_prices':
            self.env["mk.listing"].with_context(operation_wizard=self).shopify_update_product_price(instance)
        if self.shopify_export_operations == 'update_stock':
            self.env["mk.listing"].with_context(operation_wizard=self).update_stock_in_shopify_ts(instance)
        if self.shopify_export_operations == 'update_order_status':
            self.env['sale.order'].shopify_update_order_status(instance)
        if self.shopify_export_operations == 'export_collections':
            collection_obj = self.env["shopify.collection.ts"]
            collection_domain = [('mk_instance_id', '=', instance.id), ('exported_in_shopify', '=', False)]
            collection_ids = collection_obj.search(collection_domain)
            collection_ids and collection_ids.export_collection_to_shopify_ts(self)
        if self.shopify_export_operations == 'update_collections':
            collection_obj = self.env["shopify.collection.ts"]
            collection_domain = [('mk_instance_id', '=', instance.id), ('exported_in_shopify', '=', True)]
            collection_ids = collection_obj.search(collection_domain)
            collection_ids and collection_ids.update_collection_to_shopify_ts(self)
        if self.shopify_export_operations == 'update_catalogs':
            catalog_domain = [('mk_instance_id', '=', instance.id), ('shopify_catalog_id', '!=', False)]
            catalog_ids = self.env["shopify.catalog.ts"].search(catalog_domain)
            catalog_ids and catalog_ids.update_catalog_to_shopify_ts()
        return True

    # Export update collection button method

    def export_collection_to_mk(self):
        """
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.
        """
        self.ensure_one()
        shopify_collection_obj = self.env['shopify.collection.ts']
        if self.env.context.get('active_model') == 'shopify.collection.ts' and self.env.context.get('active_ids', []):
            collection_to_export = shopify_collection_obj.search([('id', 'in', self.env.context.get('active_ids', [])), ('exported_in_shopify', '=', False)])
        else:
            collection_to_export = shopify_collection_obj.search([('mk_instance_id', '=', self.mk_instance_id.id), ('exported_in_shopify', '=', False)])
        if not collection_to_export:
            raise MarketplaceException(_("Could not find any collection for export."))
        if len(collection_to_export.mapped('mk_instance_id')) > 1:
            raise MarketplaceException(_("Operation not allowed! Make sure selected listing belongs to only one instance."))
        instance_id = collection_to_export[0].mk_instance_id
        if instance_id.state != 'confirmed':
            error_msg = "You can export a collection only with a confirm instance. Please ensure the instance is confirm before export the collection."
            self.mk_instance_id.show_shopify_instance_redirect_warning(error_msg)
        if hasattr(collection_to_export, 'export_collection_to_shopify_ts'):
            collection_to_export.export_collection_to_shopify_ts(self)
        return True

    def update_collection_to_mk(self):
        """
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.
        """
        self.ensure_one()
        shopify_collection_obj = self.env['shopify.collection.ts']
        if self.env.context.get('active_model') == 'shopify.collection.ts' and self.env.context.get('active_ids', []):
            collection_to_update = shopify_collection_obj.search([('id', 'in', self.env.context.get('active_ids', [])), ('exported_in_shopify', '=', True)])
        else:
            collection_to_update = shopify_collection_obj.search([('mk_instance_id', '=', self.mk_instance_id.id), ('exported_in_shopify', '=', True)])
        if len(collection_to_update.mapped('mk_instance_id')) > 1:
            raise MarketplaceException(_("Operation not allowed! Make sure selected collection belongs to only one instance."))
        if collection_to_update[0].mk_instance_id.state != 'confirmed':
            error_msg = "You can update a collection only with a confirm instance. Please ensure the instance is confirm before updating the collection."
            self.mk_instance_id.show_shopify_instance_redirect_warning(error_msg)
        if hasattr(collection_to_update, 'update_collection_to_shopify_ts'):
            collection_to_update.update_collection_to_shopify_ts(self)
        return True

    def shopify_get_active_cron_operation_wise(self):
        ir_cron_sudo = self.env['ir.cron'].sudo().with_context(active_test=False)
        mk_instance_id = self.mk_instance_id
        return {
            'shopify': {
                'import': {
                    'import_orders': ir_cron_sudo.search([('code', '=', f"model.cron_auto_import_shopify_orders({mk_instance_id.id})")]),
                    'import_payout_report': ir_cron_sudo.search([('code', '=', f"model.cron_auto_import_shopify_payout_report({mk_instance_id.id})")]),
                    'import_stock': ir_cron_sudo.search([('code', '=', f"model.cron_auto_import_stock({mk_instance_id.id})")]),
                    'import_returns': ir_cron_sudo.search([('code', '=', f"model.cron_auto_import_shopify_returns({mk_instance_id.id})")]),
                    'process_pending_cancelled_returns': ir_cron_sudo.search([('code', '=', f"model.cron_process_pending_cancelled_shopify_returns({mk_instance_id.id})")]),
                },
                'export': {
                    'update_order_status': ir_cron_sudo.search([('code', '=', f"model.cron_auto_update_order_status({mk_instance_id.id})")]),
                    'update_stock': ir_cron_sudo.search([('code', '=', f"model.cron_auto_export_stock({mk_instance_id.id})")]),
                    'update_prices': ir_cron_sudo.search([('code', '=', f"model.cron_auto_update_product_price({mk_instance_id.id})")])
                },
            }
        }
