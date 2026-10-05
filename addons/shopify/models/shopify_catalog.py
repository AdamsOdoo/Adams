import logging

from odoo.tools import float_compare, split_every

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import GET_IMPORT_CATALOGS, GET_INCLUDED_PRODUCTS_PAGE, GET_CATALOG_PRICES_PAGE, GET_CATALOG_QUANTITY_RULES_PAGE, \
    UPDATE_CATALOG, UPDATE_PUBLICATION, UPDATE_PRICE_LIST, QUANTITY_PRICING_BY_VARIANT_UPDATE, QUANTITY_RULES_DELETE
from odoo.addons.shopify.models.misc import extract_numeric_id
from odoo.addons.shopify.shopify.pyactiveresource.connection import ResourceNotFound

PUBLICATION_PRODUCT_BATCH = 50
PRICING_VARIANT_BATCH = 100

PRICING_NOT_FOUND_RETRIES = 2

_logger = logging.getLogger("Teqstars:Shopify")

CATALOG_TYPES = [
    ('MARKET', 'Market'),
    ('COMPANY_LOCATION', 'Company Location'),
    ('APP', 'App'),
]

CATALOG_STATUSES = [
    ('DRAFT', 'Draft'),
    ('ACTIVE', 'Active'),
    ('ARCHIVED', 'Archived'),
]

ADJUSTMENT_TYPES = [
    ('PERCENTAGE_DECREASE', 'Decrease'),
    ('PERCENTAGE_INCREASE', 'Increase'),
]

_PRICING_VARIANT_DICT_KEYS = ('pricesToAdd', 'quantityRulesToAdd', 'quantityPriceBreaksToAdd')
_PRICING_VARIANT_GID_KEYS = ('pricesToDeleteByVariantId', 'quantityRulesToDeleteByVariantId')


class ShopifyCatalog(models.Model):
    _name = "shopify.catalog.ts"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _description = "Shopify Catalog"
    _rec_name = "title"

    title = fields.Char("Title", required=True, size=255)
    active = fields.Boolean(default=True)
    shopify_catalog_id = fields.Char("Shopify Catalog ID", copy=False, index=True)
    publication_shopify_id = fields.Char("Publication Shopify ID", copy=False, help="Cached Publication GID for the catalog; auto-populated on first push.")
    catalog_type = fields.Selection(CATALOG_TYPES, string="Catalog Type", default='MARKET')
    status = fields.Selection(CATALOG_STATUSES, string="Status")
    currency_id = fields.Many2one('res.currency', string='Currency')
    price_list_shopify_id = fields.Char("Price List Shopify ID", copy=False)
    price_list_name = fields.Char("Price List Name")
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade', required=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', related='mk_instance_id.company_id', store=True)
    market_ids = fields.Many2many(comodel_name='shopify.market.ts', relation='shopify_market_catalog_rel', column1='catalog_id', column2='market_id', string="Markets",
                                  domain="[('mk_instance_id', '=', mk_instance_id)]")
    company_location_ids = fields.Many2many(comodel_name='shopify.company.location.ts', relation='shopify_location_catalog_rel', column1='catalog_id', column2='location_id',
                                            string="Company Locations", domain="[('mk_instance_id', '=', mk_instance_id)]")
    app_ids = fields.Many2many(comodel_name='shopify.app.ts', relation='shopify_app_catalog_rel', column1='catalog_id', column2='app_id', string="Apps",
                               domain="[('mk_instance_id', '=', mk_instance_id)]")
    variant_price_ids = fields.One2many('shopify.catalog.variant.price.ts', 'catalog_id', string="Variant Price Overrides")
    quantity_price_break_ids = fields.One2many('shopify.catalog.variant.price.break.ts', 'catalog_id', string="Volume Pricing")
    catalog_product_count = fields.Integer("Imported Product Count", compute='_compute_shopify_catalog_product_count')
    auto_include_new_products = fields.Boolean(string="Automatically include new products", default=False,
                                               help="If checked, newly created products will be added to this catalog automatically.")
    adjustment_value = fields.Float("Price Adjustment (%)",
                                    help="Percentage adjustment applied to the store currency for this catalog's price list (Relative pricing). Leave 0 to keep the catalog on fixed prices.")
    adjustment_type = fields.Selection(ADJUSTMENT_TYPES, string="Adjustment Type")
    include_compare_at_price = fields.Boolean("Include Compare-at Price",
                                              help="When enabled, the same percentage adjustment is applied to compare-at prices (ADJUSTED); otherwise compare-at prices are cleared on the catalog (NULLIFY).")

    _check_unique_shopify_mk_id = models.Constraint("UNIQUE (shopify_catalog_id, mk_instance_id)", "A Shopify Catalog with this ID already exists for this instance.")

    def _compute_shopify_catalog_product_count(self):
        """
        Task: T7700 - Compute the number of imported products for each catalog.
        """
        for rec in self:
            rec.catalog_product_count = len(rec.variant_price_ids.mk_listing_id)

    @api.onchange('adjustment_type')
    def _onchange_shopify_adjustment_type(self):
        """
        Task: T7700 - Mirror Shopify: changing the adjustment type resets the
            percentage to 0 (which re-bases prices off 0% on write).
        """
        for rec in self:
            rec.adjustment_value = 0.0

    @api.onchange('status')
    def _onchange_shopify_adjustment_type(self):
        """
        Task: T7700 - Toggle ``active`` from the status: ARCHIVED archives the
            catalog, ACTIVE/DRAFT keep it active.
        """
        for rec in self:
            if rec.status == 'ARCHIVED':
                rec.active = False
            elif rec.status in ['ACTIVE', 'DRAFT']:
                rec.active = True

    def write(self, vals):
        """ Mirror Shopify's behavior: once a MARKET catalog gets bound to a
            market, Shopify deletes any quantity rules and volume tiers tied to
            its price list. Wipe them locally too so Odoo stays in sync after
            the user assigns markets.
        """
        if 'catalog_type' in vals:
            new_type = vals['catalog_type']
            if new_type == 'MARKET':
                vals.update({'company_location_ids': [(5, 0, 0)], 'app_ids': [(5, 0, 0)]})
            elif new_type == 'COMPANY_LOCATION':
                vals.update({'market_ids': [(5, 0, 0)], 'app_ids': [(5, 0, 0)]})
            elif new_type == 'APP':
                vals.update({'market_ids': [(5, 0, 0)], 'company_location_ids': [(5, 0, 0)]})
        adjustment_changed = bool({'adjustment_value', 'adjustment_type', 'include_compare_at_price'} & set(vals))
        old_factors = {rec.id: rec._shopify_relative_factor() for rec in self} if adjustment_changed else {}
        res = super(ShopifyCatalog, self).write(vals)
        if 'market_ids' in vals:
            for rec in self:
                if rec.catalog_type == 'MARKET' and rec.market_ids:
                    rec._wipe_shopify_quantity_rules()
        if adjustment_changed:
            for rec in self:
                rec.variant_price_ids._apply_relative_pricing(old_factor=old_factors.get(rec.id, 1.0))
        return res

    def _shopify_relative_factor(self):
        """
        Task: T7700 - Multiplier for the catalog's relative adjustment: 1 + v/100
            for an increase, 1 - v/100 for a decrease, 1.0 when no adjustment is set.
        Returns:
            float: The relative pricing factor for this catalog.
        """
        self.ensure_one()
        adjustment_value = self.adjustment_value or 0.0
        if not adjustment_value or not self.adjustment_type:
            return 1.0
        return (1 + adjustment_value / 100.0) if self.adjustment_type == 'PERCENTAGE_INCREASE' else (1 - adjustment_value / 100.0)

    def _wipe_shopify_quantity_rules(self):
        """
        Task: T7700 - Drop quantity-rule fields on every variant_price row and
            unlink all volume tiers under this catalog. Fixed prices (price,
            compare_at_price) are preserved — only rule/tier state is reset.
        """
        self.ensure_one()
        if self.quantity_price_break_ids:
            self.quantity_price_break_ids.sudo().unlink()
        if self.variant_price_ids:
            self.variant_price_ids.write({
                'minimum_quantity': 1,
                'maximum_quantity': 0,
                'increment': 1,
                'is_default': False,
            })

    def prepare_vals_for_shopify_catalog(self, catalog, mk_instance_id, catalog_type='MARKET'):
        """
        Task: T7700 - Build the create/write vals dict for a shopify.catalog.ts
            record from a Shopify catalog payload.
        Args:
            catalog (dict): Shopify catalog node (priceList, publication, status...).
            mk_instance_id (recordset): The mk.instance record.
            catalog_type (str): Local catalog type enum (default 'MARKET').
        Returns:
            dict: Field values ready for create/write.
        """
        gid = catalog.get('id')
        price_list = catalog.get('priceList') or {}
        publication = catalog.get('publication') or {}
        currency_code = price_list.get('currency') or False
        currency_id = self.env['res.currency'].with_context(active_test=False).search([('name', '=', currency_code)], limit=1)
        if currency_id and not currency_id.active:
            currency_id.sudo().active = True
        parent = price_list.get('parent') or {}
        adjustment = parent.get('adjustment') or {}
        settings = parent.get('settings') or {}
        return {
            'title': catalog.get('title') or _('Unnamed Catalog'),
            'shopify_catalog_id': extract_numeric_id(gid),
            'publication_shopify_id': publication.get('id') or False,
            'catalog_type': catalog_type,
            'status': catalog.get('status'),
            'price_list_shopify_id': extract_numeric_id(price_list.get('id')) if price_list else False,
            'price_list_name': price_list.get('name', '') if price_list else False,
            'currency_id': currency_id.id,
            'adjustment_value': adjustment.get('value') or 0.0,
            'adjustment_type': adjustment.get('type') or False,
            'include_compare_at_price': settings.get('compareAtMode') == 'ADJUSTED',
            'mk_instance_id': mk_instance_id.id,
            'active': False if catalog.get('status', 'ACTIVE') == 'ARCHIVED' else True,
        }

    def create_update_shopify_market(self, market_dict, mk_instance_id):
        """ Creates or updates a Shopify market based on the provided dictionary """
        market_numeric_id = extract_numeric_id(market_dict.get('id'))
        if not market_numeric_id:
            return False

        market_vals = {
            'name': market_dict.get('name', 'Unnamed Market'),
            'shopify_market_id': str(market_numeric_id),
            'market_type': market_dict.get('type'),
            'status': market_dict.get('status'),
            'mk_instance_id': mk_instance_id.id,
        }

        shopify_market_id = self.env['shopify.market.ts'].with_context(active_test=False).search(
            [('shopify_market_id', '=', str(market_numeric_id)), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)

        if shopify_market_id:
            shopify_market_id.sudo().write(market_vals)
            return shopify_market_id
        return self.env['shopify.market.ts'].sudo().create(market_vals)

    def process_shopify_catalog_type(self, mk_instance_id, catalog_dict):
        """
        Task: T7700 - Dispatch type-specific import (markets or company locations)
            based on the catalog's Shopify __typename.
        Args:
            mk_instance_id (recordset): The mk.instance record.
            catalog_dict (dict): Shopify catalog node.
        Returns:
            bool: True.
        """
        typename = catalog_dict.get('__typename', '')
        if typename == 'MarketCatalog':
            self.import_shopify_catalog_markets(mk_instance_id, catalog_dict)
        elif typename == 'CompanyLocationCatalog':
            self.import_shopify_catalog_company_locations(mk_instance_id, catalog_dict)
        return True

    def _get_paginated_products_from_shopify_catalog(self, catalog_dict, mk_instance_id):
        """
        Task: T7700 - This method handles the fetching of all products within a given Shopify collection, taking into account pagination.
            It retrieves all products in the collection by iterating over multiple pages if needed.
        Args:
            catalog_dict (dict): The Shopify collection data, containing a list of products.
            mk_instance_id (recordset): The record of the mk.instance model.
        Returns:
           remaining_collection_product(list): A list of all products in the collection, including products across multiple pages.
        Raises:
            MarketplaceException: If an error occurs during the API request or data processing.
        """
        publication_dict = catalog_dict.get('publication') or {}
        publication_id = publication_dict.get('id')
        included_products = publication_dict.get('includedProducts') or {}

        remaining_collection_product = list(included_products.get('nodes') or [])

        page_info = included_products.get('pageInfo') or {}
        cursor = page_info.get('endCursor')
        has_next_page = page_info.get('hasNextPage', False)

        if not has_next_page or not cursor or not publication_id:
            return remaining_collection_product

        while has_next_page and cursor and publication_id:
            try:
                response = mk_instance_id.execute_graphql_query(GET_INCLUDED_PRODUCTS_PAGE, {"id": publication_id, "cursor": cursor})
                user_errors = response.get('errors', []) if isinstance(response, dict) else []
                if user_errors and isinstance(user_errors, list):
                    mk_instance_id.handle_shopify_access_errors(user_errors, "Catalog Publication Products")

                pub_node = (response.get('data') or {}).get('publication') or {}
                products_page = pub_node.get('includedProducts') or {}

                remaining_collection_product.extend(products_page.get('nodes') or [])

                page_info = products_page.get('pageInfo') or {}
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor') if has_next_page else None

            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"Failed to fetch Shopify Catalog Publication Products: {str(e)}")

        return remaining_collection_product

    def _get_paginated_prices_from_shopify_catalog(self, catalog_dict, mk_instance_id):
        """Processes the first page of variant prices directly embedded in catalog_dict,
        and paginates forward if hasNextPage is True via endCursor loops.
        """
        price_list_dict = catalog_dict.get('priceList') or {}
        price_list_id = price_list_dict.get('id')
        prices_connection = price_list_dict.get('prices') or {}

        all_variant_prices = list(prices_connection.get('nodes') or [])

        page_info = prices_connection.get('pageInfo') or {}
        cursor = page_info.get('endCursor')
        has_next_page = page_info.get('hasNextPage', False)

        if not has_next_page or not cursor or not price_list_id:
            return all_variant_prices

        while has_next_page and cursor and price_list_id:
            try:
                response = mk_instance_id.execute_graphql_query(GET_CATALOG_PRICES_PAGE, {"id": price_list_id, "cursor": cursor})
                user_errors = response.get('errors', []) if isinstance(response, dict) else []
                if user_errors and isinstance(user_errors, list):
                    mk_instance_id.handle_shopify_access_errors(user_errors, "Catalog Variant Prices")

                price_list_node = (response.get('data') or {}).get('priceList') or {}
                prices_page = price_list_node.get('prices') or {}

                all_variant_prices.extend(prices_page.get('nodes') or [])

                page_info = prices_page.get('pageInfo') or {}
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor') if has_next_page else None

            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"Failed to fetch Shopify Catalog Price List overrides: {str(e)}")

        return all_variant_prices

    def _get_paginated_quantity_rules_from_shopify_catalog(self, catalog_dict, mk_instance_id):
        """Mirror of _get_paginated_prices_from_shopify_catalog for the quantityRules connection."""
        price_list_dict = catalog_dict.get('priceList') or {}
        price_list_id = price_list_dict.get('id')
        rules_connection = price_list_dict.get('quantityRules') or {}

        all_rules = list(rules_connection.get('nodes') or [])

        page_info = rules_connection.get('pageInfo') or {}
        cursor = page_info.get('endCursor')
        has_next_page = page_info.get('hasNextPage', False)

        if not has_next_page or not cursor or not price_list_id:
            return all_rules

        while has_next_page and cursor and price_list_id:
            try:
                response = mk_instance_id.execute_graphql_query(GET_CATALOG_QUANTITY_RULES_PAGE, {"id": price_list_id, "cursor": cursor})
                user_errors = response.get('errors', []) if isinstance(response, dict) else []
                if user_errors and isinstance(user_errors, list):
                    mk_instance_id.handle_shopify_access_errors(user_errors, "Catalog Quantity Rules")

                price_list_node = (response.get('data') or {}).get('priceList') or {}
                rules_page = price_list_node.get('quantityRules') or {}

                all_rules.extend(rules_page.get('nodes') or [])

                page_info = rules_page.get('pageInfo') or {}
                has_next_page = page_info.get('hasNextPage', False)
                cursor = page_info.get('endCursor') if has_next_page else None

            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"Failed to fetch Shopify Catalog Quantity Rules: {str(e)}")

        return all_rules

    def fetch_all_shopify_catalogs(self, mk_instance_id, mk_catalog_id=False):
        """
        Task: T7700 - Cursor-paginated fetch of catalogs across all CatalogTypes.
        Args:
            mk_instance_id: marketplace instance record.
            mk_catalog_id: optional numeric Shopify Catalog ID. When set,
                the query is narrowed via Shopify's ``query: "id:<numeric>"``
                search syntax, returning at most that one catalog.
        Returns:
            list: Shopify catalog nodes.
        Raises:
            MarketplaceException: On fetch failure or Shopify user errors.
        """
        catalogs = []
        cursor = None
        has_next_page = True

        if mk_catalog_id:
            try:
                # Task: T8975 - Search all given catalogs in one call instead of one call per catalog.
                catalog_ids = []
                for catalog_id in ''.join(mk_catalog_id.split()).split(','):
                    if catalog_id and catalog_id not in catalog_ids:
                        catalog_ids.append(catalog_id)
                for batch_catalog_ids in split_every(250, catalog_ids, piece_maker=list):
                    search_query = " OR ".join(["id:%s" % catalog_id for catalog_id in batch_catalog_ids])
                    has_next_page, cursor = True, None
                    while has_next_page:
                        variables = {"cursor": cursor, "query": search_query}
                        response_data = mk_instance_id.execute_graphql_query(GET_IMPORT_CATALOGS, variables)
                        user_errors = response_data.get('errors', []) if isinstance(response_data, dict) else []
                        if user_errors and isinstance(user_errors, list):
                            err_messages = [e.get('message', str(e)) for e in user_errors]
                            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Catalogs: %s") % ", ".join(err_messages))

                        catalogs_data = response_data.get('data', {}).get('catalogs', {}) if response_data.get('data', {}) else {}
                        nodes = catalogs_data.get('nodes', [])
                        page_info = catalogs_data.get('pageInfo', {})
                        catalogs.extend(nodes)
                        has_next_page = page_info.get('hasNextPage', False)
                        cursor = page_info.get('endCursor') if has_next_page else None
            except ResourceNotFound as e:
                raise MarketplaceException(e.args, f'{e.response.code} - {e.response.msg}')
            except MarketplaceException:
                raise
            except Exception as e:
                log_message = f"IMPORT CATALOG: Error while import catalog to Odoo. ERROR: {e}"
                raise MarketplaceException(log_message, e, additional_context={'show_traceback': True})
            return catalogs

        while has_next_page:
            variables = {"cursor": cursor, "query": None}
            response_data = mk_instance_id.execute_graphql_query(GET_IMPORT_CATALOGS, variables)
            user_errors = response_data.get('errors', []) if isinstance(response_data, dict) else []
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Catalogs: %s") % ", ".join(err_messages))

            catalogs_data = (response_data.get('data') or {}).get('catalogs') or {}
            nodes = catalogs_data.get('nodes') or []
            page_info = catalogs_data.get('pageInfo') or {}
            catalogs.extend(nodes)

            has_next_page = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor') if has_next_page else None
        return catalogs

    def import_catalogs_from_shopify(self, mk_instance_id, mk_catalog_id=False):
        """
        Task: T7700 - Catalog import + reconciliation + inline product import.
            Mirrors the collections-import flow: for every upserted catalog,
            also pulls the catalog's products via its Publication and
            creates missing local listings via the standard listing import.
        Args:
            mk_instance_id: marketplace instance record.
            mk_catalog_id: optional numeric Shopify Catalog ID. When
                empty (default) all catalogs of all CatalogTypes are
                imported. When set, only that one catalog is imported
                and reconciliation is skipped (single-record refresh
                must not deactivate every other local catalog).
        Returns:
            dict|bool: action_open_model_view action when catalogs imported, else True.
        """
        mk_instance_id.connection_to_shopify()
        shopify_catalog_list = self.fetch_all_shopify_catalogs(mk_instance_id, mk_catalog_id=mk_catalog_id)
        catalog_list = []
        for catalog_dict in shopify_catalog_list:
            numeric_id = extract_numeric_id(catalog_dict.get('id'))
            if not numeric_id:
                continue
            try:
                if catalog_dict.get('priceList', {}) is None:
                    continue
                catalog_type = self._derive_shopify_catalog_type_from_typename(catalog_dict.get('__typename'))
                vals = self.prepare_vals_for_shopify_catalog(catalog_dict, mk_instance_id, catalog_type=catalog_type)
                mk_catalog_id = self.with_context(active_test=False).search([('shopify_catalog_id', '=', str(numeric_id)), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)
                if mk_catalog_id:
                    mk_catalog_id.write(vals)
                else:
                    mk_catalog_id = self.create(vals)
                catalog_list.append(mk_catalog_id.id)
                mk_catalog_id and mk_catalog_id.import_shopify_catalog_include_products(mk_instance_id, catalog_dict)
                mk_catalog_id and mk_catalog_id.process_shopify_catalog_type(mk_instance_id, catalog_dict)
                self.env.cr.commit()
            except MarketplaceException:
                raise
            except Exception as e:
                _logger.exception(f"Failed to upsert Shopify Catalog {numeric_id}: {e}")
                continue

        if catalog_list:
            return mk_instance_id.action_open_model_view(catalog_list, 'shopify.catalog.ts', 'Shopify Catalog')
        return True

    @staticmethod
    def _derive_shopify_catalog_type_from_typename(typename):
        """
        Task: T7700 - Map Shopify __typename to the local catalog_type enum.
        Args:
            typename (str): Shopify catalog __typename value.
        Returns:
            str: Local catalog_type enum ('MARKET', 'COMPANY_LOCATION', 'APP').
        """
        mapping = {
            'MarketCatalog': 'MARKET',
            'CompanyLocationCatalog': 'COMPANY_LOCATION',
            'AppCatalog': 'APP',
        }
        return mapping.get(typename, 'MARKET')

    def _prepare_shopify_catalog_product_vals(self, product, listing=None):
        """
        Task: T7700 - Build a (0, 0, vals) command for a catalog-product line
            from a Shopify product node and optional local listing.
        Args:
            product (dict): Shopify product node (legacyResourceId).
            listing (recordset): Optional mk.listing record.
        Returns:
            tuple: An Odoo (0, 0, vals) create command.
        """
        product_id = product.get('legacyResourceId')
        return (0, 0, {
            'catalog_id': self.id,
            'product_shopify_id': product_id,
            'mk_listing_id': listing.id if listing else False,
        })

    def import_shopify_catalog_include_products(self, mk_instance_id, catalog_dict):
        """
        Task: T7700 - Import (or refresh) the product list of each catalog in self.
            For each product node: look up local mk.listing by (mk_id, mk_instance_id);
            if missing, call the existing listing-import flow to create it (mirroring
            the collections sync pattern); then upsert variant prices and quantity rules.
            After all products are processed, deletes variant price rows not seen in
            this sweep (per-catalog reconciliation).
        Args:
            mk_instance_id (recordset): The mk.instance record.
            catalog_dict (dict): Shopify catalog node with publication products.
        Returns:
            bool: True.
        """
        mk_listing_obj = self.env['mk.listing']
        all_catalog_included_products = self._get_paginated_products_from_shopify_catalog(catalog_dict, mk_instance_id)
        publication_dict = catalog_dict.get('publication') or {}
        auto_publish = publication_dict and publication_dict.get('autoPublish', False)

        included_product_ids = set()

        for product in all_catalog_included_products:
            product_numeric_id = product.get('legacyResourceId', '')
            if not product_numeric_id:
                continue

            try:
                mk_listing_id = mk_listing_obj.search([('mk_id', '=', product_numeric_id), ('mk_instance_id', '=', mk_instance_id.id), ], limit=1)
                if not mk_listing_id:
                    mk_listing_obj.shopify_import_listings(mk_instance_id, False, False, mk_listing_id=str(product_numeric_id))
                    mk_listing_id = mk_listing_obj.search([('mk_id', '=', product_numeric_id), ('mk_instance_id', '=', mk_instance_id.id), ], limit=1)
                if not mk_listing_id:
                    numeric_id = extract_numeric_id(catalog_dict.get('id'))
                    log_message = f"Shopify Product {product_numeric_id} not found in Odoo for a Catalog {catalog_dict.get('title', '')}({numeric_id})"
                    _logger.error(log_message)
                    continue

                included_product_ids.add(str(product_numeric_id))
            except Exception as e:
                _logger.exception(f"Catalog {catalog_dict.get('id')}: failed to upsert catalog-product link for {product_numeric_id}: {e}")
                continue

        self.write({'auto_include_new_products': auto_publish})
        active_variant_price_ids = set()
        price_ids = self.import_shopify_catalog_variant_prices(mk_instance_id, catalog_dict, included_product_ids)
        if price_ids:
            active_variant_price_ids.update(price_ids)
        rule_ids = self.import_shopify_catalog_variant_quantity_rules(mk_instance_id, catalog_dict, included_product_ids)
        if rule_ids:
            active_variant_price_ids.update(rule_ids)

        # Delete variant price overrides that were removed from the catalog in Shopify
        all_existing_prices = self.env['shopify.catalog.variant.price.ts'].search([('catalog_id', '=', self.id)])
        stale_prices = all_existing_prices - self.env['shopify.catalog.variant.price.ts'].browse(list(active_variant_price_ids))
        if stale_prices:
            stale_prices.sudo().unlink()

        return True

    def import_shopify_catalog_variant_prices(self, mk_instance_id, catalog_dict, included_product_ids):
        """
        Task: T7700 - Fetch, filter, and track per-variant price overrides and
            quantity price breaks for this catalog's price list.
        Args:
            mk_instance_id (recordset): The mk.instance record.
            catalog_dict (dict): Shopify catalog node with price list prices.
            included_product_ids (set): Numeric product IDs in the catalog scope.
        Returns:
            list: IDs of the active shopify.catalog.variant.price.ts rows.
        """
        self.ensure_one()
        variant_price_obj = self.env['shopify.catalog.variant.price.ts']
        price_break_obj = self.env['shopify.catalog.variant.price.break.ts']
        listing_item_obj = self.env['mk.listing.item']

        all_catalog_prices = self._get_paginated_prices_from_shopify_catalog(catalog_dict, mk_instance_id)
        active_variant_price_ids = []
        seen_break_ids = set()  # Track active breaks for stale deletion

        for node in all_catalog_prices:
            variant_node = node.get('variant') or {}
            variant_numeric_id = variant_node.get('legacyResourceId')

            product_node = variant_node.get('product') or {}
            product_numeric_id = product_node.get('legacyResourceId')

            if not variant_numeric_id or not product_numeric_id:
                continue

            # Strict Filter Constraint: Skip nodes whose parent products aren't in the collection
            if str(product_numeric_id) not in included_product_ids:
                continue

            price_val = float((node.get('price') or {}).get('amount') or 0.0)
            compare_val = float((node.get('compareAtPrice') or {}).get('amount') or 0.0) if node.get('compareAtPrice') else 0.0

            listing_item_id = listing_item_obj.search([('mk_id', '=', str(variant_numeric_id)), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)
            existing_price_rec = variant_price_obj.search([('catalog_id', '=', self.id), ('variant_shopify_id', '=', str(variant_numeric_id))], limit=1)

            vals = {
                'catalog_id': self.id,
                'mk_listing_item_id': listing_item_id.id if listing_item_id else False,
                'mk_listing_id': listing_item_id.mk_listing_id.id if listing_item_id else False,
                'price': price_val,
                'compare_at_price': compare_val,
                'origin_type': node.get('originType') or 'FIXED',
            }

            if existing_price_rec:
                existing_price_rec.write(vals)
                active_variant_price_ids.append(existing_price_rec.id)
                variant_price_rec = existing_price_rec
            else:
                variant_price_rec = variant_price_obj.create(vals)
                active_variant_price_ids.append(variant_price_rec.id)

            # --- PROCESS QUANTITY PRICE BREAKS ---
            breaks_conn = node.get('quantityPriceBreaks') or {}
            for break_node in (breaks_conn.get('nodes') or []):
                break_numeric_id = extract_numeric_id(break_node.get('id'))
                if not break_numeric_id:
                    continue

                break_price_val = float((break_node.get('price') or {}).get('amount') or 0.0)
                min_qty = int(break_node.get('minimumQuantity') or 1)

                break_vals = {
                    'catalog_id': self.id,
                    'variant_price_id': variant_price_rec.id,
                    'shopify_break_id': str(break_numeric_id),
                    'mk_listing_item_id': listing_item_id.id if listing_item_id else False,
                    'minimum_quantity': min_qty,
                    'price': break_price_val,
                }

                existing_break = price_break_obj.search([('catalog_id', '=', self.id), ('shopify_break_id', '=', str(break_numeric_id))], limit=1)
                if existing_break:
                    existing_break.write(break_vals)
                    seen_break_ids.add(existing_break.id)
                else:
                    new_break_rec = price_break_obj.create(break_vals)
                    seen_break_ids.add(new_break_rec.id)

            breaks_page_info = breaks_conn.get('pageInfo') or {}
            if breaks_page_info.get('hasNextPage'):
                _logger.warning("Variant %s on catalog %s has >50 quantity price breaks; remaining tiers will not be imported.", variant_numeric_id, self.id)

        # Stable Shopify GIDs make delete-stale safe: anything in Odoo not seen this sweep is gone in Shopify.
        all_breaks_for_catalog = price_break_obj.search([('catalog_id', '=', self.id)])
        stale = all_breaks_for_catalog - price_break_obj.browse(list(seen_break_ids))
        if stale:
            stale.sudo().unlink()

        return active_variant_price_ids

    def import_shopify_catalog_variant_quantity_rules(self, mk_instance_id, catalog_dict, included_product_ids):
        """
        Task: T7700 - Fetch and persist per-variant quantity rules for this catalog's
            price list. Rules are merged into the same shopify.catalog.variant.price.ts
            row keyed by (catalog_id, variant_shopify_id) — a variant may carry a price
            override, a quantity rule, or both. Strict product-inclusion filter mirrors
            the variant price import to drop nodes outside the catalog's publication scope.
        Args:
            mk_instance_id (recordset): The mk.instance record.
            catalog_dict (dict): Shopify catalog node with price list quantity rules.
            included_product_ids (set): Numeric product IDs in the catalog scope.
        Returns:
            list: IDs of the active shopify.catalog.variant.price.ts rows.
        """
        self.ensure_one()
        variant_price_obj = self.env['shopify.catalog.variant.price.ts']
        listing_item_obj = self.env['mk.listing.item']

        all_quantity_rules = self._get_paginated_quantity_rules_from_shopify_catalog(catalog_dict, mk_instance_id)
        active_rule_ids = []
        for node in all_quantity_rules:
            variant_node = node.get('productVariant') or {}
            variant_numeric_id = variant_node.get('legacyResourceId')

            product_node = variant_node.get('product') or {}
            product_numeric_id = product_node.get('legacyResourceId')

            if not variant_numeric_id or not product_numeric_id:
                continue

            if str(product_numeric_id) not in included_product_ids:
                continue

            rule_vals = {
                'minimum_quantity': int(node.get('minimum') or 1),
                'maximum_quantity': int(node.get('maximum') or 0),
                'increment': int(node.get('increment') or 1),
                'is_default': bool(node.get('isDefault', False)),
            }

            catalog_variant_price_id = variant_price_obj.search([('catalog_id', '=', self.id), ('variant_shopify_id', '=', str(variant_numeric_id))], limit=1)
            if catalog_variant_price_id:
                catalog_variant_price_id.write(rule_vals)
                active_rule_ids.append(catalog_variant_price_id.id)
            else:
                listing_item_id = listing_item_obj.search([('mk_id', '=', str(variant_numeric_id)), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)
                catalog_variant_price_id = variant_price_obj.create({
                    'catalog_id': self.id,
                    'mk_listing_item_id': listing_item_id.id if listing_item_id else False,
                    'mk_listing_id': listing_item_id.mk_listing_id.id if listing_item_id else False,
                    **rule_vals,
                })
            active_rule_ids.append(catalog_variant_price_id.id)
        return active_rule_ids

    def import_shopify_catalog_company_locations(self, mk_instance_id, catalog_dict):
        """
        Task: T7700 - Upsert the company locations embedded in the catalog payload
            and link them to this catalog.
        Args:
            mk_instance_id (recordset): The mk.instance record.
            catalog_dict (dict): Shopify catalog node with companyLocations.
        Returns:
            bool: True.
        """
        self.ensure_one()
        linked_location_ids = []
        locations_page = catalog_dict.get('companyLocations', {})

        for loc_node in locations_page.get('nodes', []):
            loc_numeric_id = extract_numeric_id(loc_node.get('id'))
            company_dict = loc_node.get('company', {})
            company_numeric_id = company_dict and extract_numeric_id(company_dict.get('id'))
            company_name = company_dict and company_dict.get('name', '')
            if not loc_numeric_id:
                continue

            location_record = self.env['shopify.company.location.ts'].search([('shopify_location_id', '=', str(loc_numeric_id)), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)

            vals = {
                'name': loc_node.get('name', 'Unnamed Location'),
                'shopify_location_id': str(loc_numeric_id),
                'shopify_company_id': str(company_numeric_id),
                'shopify_company_name': company_name,
                'mk_instance_id': mk_instance_id.id
            }

            if location_record:
                location_record.sudo().write(vals)
            else:
                location_record = self.env['shopify.company.location.ts'].sudo().create(vals)

            linked_location_ids.append(location_record.id)

        self.write({'company_location_ids': [(6, 0, linked_location_ids)]})
        return True

    def import_shopify_catalog_markets(self, mk_instance_id, catalog_dict):
        """
        Task: T7700 - Link existing local markets to this catalog, create missing
            ones, and update existing ones with the latest data from Shopify.
        Args:
            mk_instance_id (recordset): The mk.instance record.
            catalog_dict (dict): Shopify catalog node with markets.
        Returns:
            bool: True.
        """
        self.ensure_one()

        catalog_gid = catalog_dict.get('id')
        if not catalog_gid:
            return True

        linked_market_ids = []

        # Process the markets embedded in the catalog payload directly (no pagination)
        markets_page = catalog_dict.get('markets') or {}

        for market_node in (markets_page.get('nodes') or []):
            market_record = self.create_update_shopify_market(market_node, mk_instance_id)
            if market_record:
                linked_market_ids.append(market_record.id)

        self.write({'market_ids': [(6, 0, linked_market_ids)]})
        return True

    def update_catalog_to_shopify_ts(self):
        """
        Task: T7700 - Push catalog changes (core attributes, publication, pricing) back to Shopify.
            Mirrors the collection update pattern: per-record loop, per-section mutation,
            user-error short-circuit, instance-state guard.
        Returns:
            bool: True on successful push for every record in self.
        Raises:
            MarketplaceException: On instance not confirmed or unrecoverable mutation failure.
        """
        if not self:
            return True

        for catalog_id in self:
            mk_instance_id = catalog_id.mk_instance_id
            mk_instance_id.connection_to_shopify()
            try:
                # A MARKET catalog bound to markets cannot keep quantity rules/breaks on its price list. Local rules are already wiped in write(); push that deletion to Shopify BEFORE catalogUpdate assigns the market, else Shopify rejects the still-present rules.
                strip_rules_first = catalog_id.catalog_type == 'MARKET' and catalog_id.market_ids
                if strip_rules_first:
                    catalog_id.update_catalog_pricing_to_shopify(mk_instance_id)
                catalog_id.update_catalog_core_shopify(mk_instance_id)
                catalog_id.update_catalog_publication_to_shopify(mk_instance_id)
                catalog_id.update_catalog_price_list_to_shopify(mk_instance_id)
                if not strip_rules_first:
                    catalog_id.update_catalog_pricing_to_shopify(mk_instance_id)
                self.env.cr.commit()
            except MarketplaceException:
                raise
            except Exception as e:
                _logger.exception(f"UPDATE CATALOG: Failed to push catalog {catalog_id.shopify_catalog_id}: {e}")
                raise MarketplaceException(_(f"Error while updating catalog {catalog_id.title}: {e}"))
        return True

    def _prepare_shopify_catalog_update_input(self):
        """
        Task: T7700 - Build the CatalogUpdateInput payload from the local record.
            Skips fields that Shopify forbids changing post-create (currency, app context).
        Returns:
            dict: Input dict for catalogUpdate; empty dict when nothing to push.
        """
        self.ensure_one()
        catalog_input = {}
        if self.title:
            catalog_input.update({'title': self.title})
        if self.status:
            catalog_input.update({'status': self.status})

        context_input = {}
        if self.catalog_type == 'MARKET':
            context_input.update({'marketIds': [f"gid://shopify/Market/{m.shopify_market_id}" for m in self.market_ids if m.shopify_market_id]})
        if self.catalog_type == 'COMPANY_LOCATION' and self.company_location_ids:
            context_input.update({'companyLocationIds': [f"gid://shopify/CompanyLocation/{l.shopify_location_id}" for l in self.company_location_ids if l.shopify_location_id]})
        if context_input:
            catalog_input.update({'context': context_input})
        return catalog_input

    def update_catalog_core_shopify(self, mk_instance_id):
        """
        Task: T7700 - Push title/status/context to Shopify via catalogUpdate.
            AppCatalog context cannot be updated through CatalogContextInput, so we
            send only title/status for that catalog type.
        Args:
            mk_instance_id (recordset): The mk.instance record.
        Returns:
            bool: True on success, False when no catalog id is stored.
        Raises:
            MarketplaceException: On Shopify user errors.
        """
        self.ensure_one()
        if not self.shopify_catalog_id:
            return False
        catalog_input = self._prepare_shopify_catalog_update_input()
        if not catalog_input:
            return True
        variables = {"id": f"gid://shopify/Catalog/{self.shopify_catalog_id}", "input": catalog_input}
        response = mk_instance_id.execute_graphql_query(UPDATE_CATALOG, variables)
        transport_errors = response.get('errors', []) if isinstance(response, dict) else []
        if transport_errors and isinstance(transport_errors, list):
            mk_instance_id.handle_shopify_access_errors(transport_errors, "Update Catalog")
        user_errors = (response.get('data') or {}).get('catalogUpdate', {}).get('userErrors') or []
        if user_errors:
            messages = ", ".join([err.get('message', '') for err in user_errors])
            raise MarketplaceException(_(f"Failed to update Catalog {self.title}: {messages}"))
        return True

    def update_catalog_publication_to_shopify(self, mk_instance_id):
        """
        Task: T7700 - Sync autoPublish flag and included-product membership via publicationUpdate.
            One mutation carries autoPublish + publishablesToAdd + publishablesToRemove together;
            successive pages are emitted only when add/remove counts exceed the 50-item batch cap.
        Args:
            mk_instance_id (recordset): The mk.instance record.
        Returns:
            bool: True on success, False when no publication GID is stored.
        """
        self.ensure_one()
        publication_gid = self.publication_shopify_id
        if not publication_gid:
            _logger.warning(f"UPDATE CATALOG: skipping publication push for {self.title} — no publication GID stored. Run import to populate.")
            return False

        local_product_ids = set(self.variant_price_ids.mk_listing_id.mapped('mk_id'))
        local_product_ids.discard(False)

        remote_product_ids = set()
        cursor = None
        while True:
            live_response = mk_instance_id.execute_graphql_query(GET_INCLUDED_PRODUCTS_PAGE, {"id": publication_gid, "cursor": cursor})
            included = (((live_response.get('data') or {}).get('publication') or {}).get('includedProducts') or {})
            for node in included.get('nodes') or []:
                if node.get('legacyResourceId'):
                    remote_product_ids.add(str(node.get('legacyResourceId')))
            page_info = included.get('pageInfo') or {}
            if not page_info.get('hasNextPage', False):
                break
            cursor = page_info.get('endCursor')
            if not cursor:
                break

        to_add = [f"gid://shopify/Product/{pid}" for pid in local_product_ids - remote_product_ids]
        to_remove = [f"gid://shopify/Product/{pid}" for pid in remote_product_ids - local_product_ids]

        page_count = max(
            (len(to_add) + PUBLICATION_PRODUCT_BATCH - 1) // PUBLICATION_PRODUCT_BATCH,
            (len(to_remove) + PUBLICATION_PRODUCT_BATCH - 1) // PUBLICATION_PRODUCT_BATCH,
            1,
        )
        auto_publish_sent = False
        for page_index in range(page_count):
            add_batch = to_add[page_index * PUBLICATION_PRODUCT_BATCH:(page_index + 1) * PUBLICATION_PRODUCT_BATCH]
            remove_batch = to_remove[page_index * PUBLICATION_PRODUCT_BATCH:(page_index + 1) * PUBLICATION_PRODUCT_BATCH]
            publication_input = {}
            if not auto_publish_sent:
                publication_input.update({"autoPublish": bool(self.auto_include_new_products)})
                auto_publish_sent = True
            if add_batch:
                publication_input.update({"publishablesToAdd": add_batch})
            if remove_batch:
                publication_input.update({"publishablesToRemove": remove_batch})
            if not publication_input:
                continue
            self._call_shopify_publication_update(mk_instance_id, publication_gid, publication_input)
        return True

    def _call_shopify_publication_update(self, mk_instance_id, publication_gid, publication_input):
        """
        Task: T7700 - Execute a single publicationUpdate mutation and surface user
            errors, pruning missing publishable IDs and retrying once when needed.
        Args:
            mk_instance_id (recordset): The mk.instance record.
            publication_gid (str): Publication GID being updated.
            publication_input (dict): publicationUpdate input payload.
        Returns:
            bool: True.
        """
        variables = {"id": publication_gid, "input": publication_input}
        response = mk_instance_id.execute_graphql_query(UPDATE_PUBLICATION, variables)
        transport_errors = response.get('errors', []) if isinstance(response, dict) else []
        if transport_errors and isinstance(transport_errors, list):
            mk_instance_id.handle_shopify_access_errors(transport_errors, "Update Catalog")
        user_errors = (response.get('data') or {}).get('publicationUpdate', {}).get('userErrors') or []
        if user_errors:
            pruned = self._prune_missing_shopify_publication_products(publication_input, user_errors, mk_instance_id)
            if pruned:
                variables = {"id": publication_gid, "input": publication_input}
                response = mk_instance_id.execute_graphql_query(UPDATE_PUBLICATION, variables)
                transport_errors = response.get('errors', []) if isinstance(response, dict) else []
                if transport_errors and isinstance(transport_errors, list):
                    mk_instance_id.handle_shopify_access_errors(transport_errors, "Update Catalog")
                user_errors = (response.get('data') or {}).get('publicationUpdate', {}).get('userErrors') or []

            if user_errors:
                messages = ", ".join([err.get('message', '') for err in user_errors])
                _logger.warning(f"UPDATE CATALOG: publicationUpdate partial errors for {self.title}: {messages}")
        return True

    def _prune_missing_shopify_publication_products(self, publication_input, user_errors, mk_instance_id):
        """
        Task: T7700 - Extract invalid publishable IDs from userErrors, strip them
            from the input payload, and unlink the matching local listings/lines.
        Args:
            publication_input (dict): In-flight publicationUpdate input (mutated).
            user_errors (list): userErrors returned by publicationUpdate.
            mk_instance_id (recordset): The mk.instance record.
        Returns:
            bool: True when something was pruned, else False.
        """
        gids_to_remove = {'publishablesToAdd': set(), 'publishablesToRemove': set()}
        for err in user_errors:
            if err.get('code') == 'INVALID_PUBLISHABLE_ID' or 'publishable id not found' in (err.get('message') or '').lower():
                field = err.get('field') or []
                if len(field) >= 3 and field[1] in ('publishablesToAdd', 'publishablesToRemove') and str(field[2]).isdigit():
                    key = field[1]
                    idx = int(field[2])
                    if idx < len(publication_input.get(key, [])):
                        gids_to_remove[key].add(publication_input[key][idx])

        has_pruned = False
        for key in ('publishablesToAdd', 'publishablesToRemove'):
            if gids_to_remove[key]:
                publication_input[key] = [gid for gid in publication_input[key] if gid not in gids_to_remove[key]]
                has_pruned = True
                for gid in gids_to_remove[key]:
                    numeric_id = extract_numeric_id(gid)
                    mk_listing_id = self.env['mk.listing'].search([('mk_id', '=', str(numeric_id)), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)
                    if mk_listing_id:
                        _logger.warning(f"UPDATE CATALOG PUBLICATION: Removing Listing {mk_listing_id.name} (mk_id={numeric_id}) — Product no longer exists on Shopify.")
                        catalog_lines = self.variant_price_ids.filtered(lambda r: r.mk_listing_id.id == mk_listing_id.id)
                        if catalog_lines:
                            catalog_lines.sudo().unlink()
                        catalog_breaks = self.quantity_price_break_ids.filtered(lambda r: r.mk_listing_item_id.mk_listing_id.id == mk_listing_id.id)
                        if catalog_breaks:
                            catalog_breaks.sudo().unlink()
                        mk_listing_id.sudo().unlink()
        return has_pruned

    def update_catalog_price_list_to_shopify(self, mk_instance_id):
        """
        Task: T7700 - Push the price-list parent adjustment (relative-pricing %) and
            compare-at mode to Shopify via priceListUpdate. Only fires when
            adjustment_type + adjustment_value are both set locally; an unset
            pair means the catalog is operating in fixed-price mode and the
            parent block is left untouched. Note: Shopify rejects relative-
            pricing parent updates on price lists that also carry fixed prices,
            so the user is responsible for keeping the two modes mutually
            exclusive.
        Args:
            mk_instance_id (recordset): The mk.instance record.
        Returns:
            bool: True on success/no-op, False when no price list id is stored.
        Raises:
            MarketplaceException: On Shopify user errors.
        """
        self.ensure_one()
        if not self.price_list_shopify_id:
            return False
        if not (self.adjustment_type and self.adjustment_value):
            return True
        price_list_input = {
            'parent': {
                'adjustment': {
                    'value': self.adjustment_value,
                    'type': self.adjustment_type,
                },
                'settings': {
                    'compareAtMode': 'ADJUSTED' if self.include_compare_at_price else 'NULLIFY',
                },
            },
        }
        variables = {"id": f"gid://shopify/PriceList/{self.price_list_shopify_id}", "input": price_list_input}
        response = mk_instance_id.execute_graphql_query(UPDATE_PRICE_LIST, variables)
        transport_errors = response.get('errors', []) if isinstance(response, dict) else []
        if transport_errors and isinstance(transport_errors, list):
            mk_instance_id.handle_shopify_access_errors(transport_errors, "Update Price List")
        user_errors = (response.get('data') or {}).get('priceListUpdate', {}).get('userErrors') or []
        if user_errors:
            messages = ", ".join([err.get('message', '') for err in user_errors])
            raise MarketplaceException(_(f"Failed to update price list on Catalog {self.title}: {messages}"))
        return True

    def _prepare_shopify_pricing_payload(self, variant_price_ids, remote_breaks_by_variant=None):
        """
        Task: T7700 - Build a QuantityPricingByVariantUpdateInput payload for the given rows.
            Every list field is always present (empty arrays when no data) because
            the Shopify schema declares them as non-null and rejects omitted keys
            with "Expected value to not be null". Each row contributes a fixed-price
            entry, optional quantity rule, and zero-or-more tier breaks.

            For volume tiers we diff the local set against the remote breaks for
            each variant in this batch:
              * tier present on both sides with the same price → skipped (no churn,
                shopify_break_id is preserved);
              * tier only on Shopify → queued in quantityPriceBreaksToDelete (the
                user removed it locally);
              * tier only locally → queued in quantityPriceBreaksToAdd;
              * tier present on both sides but price changed → delete remote + add
                local (Shopify rejects an add with a duplicate (variantId,
                minimumQuantity), so the delete-before-add ordering guarantees a
                clean replacement).
        Args:
            variant_price_ids (recordset): shopify.catalog.variant.price.ts rows for this batch.
            remote_breaks_by_variant (dict): Remote tier breaks keyed by variant id.
        Returns:
            dict: payload ready for the input variable.
        """
        currency = self.currency_id and self.currency_id.name
        rounding = self.currency_id.rounding if self.currency_id else 0.01
        remote_breaks_by_variant = remote_breaks_by_variant or {}
        prices_to_add = []
        rules_to_add = []
        breaks_to_add = []
        breaks_to_delete = []
        rule_variant_resets = []
        catalog_forbids_quantity_rules = self.catalog_type == 'MARKET' and bool(self.market_ids)
        if self.catalog_type == 'MARKET' and bool(self.market_ids):
            catalog_forbids_quantity_rules = True
        elif self.catalog_type == 'COMPANY_LOCATION' and bool(self.company_location_ids):
            catalog_forbids_quantity_rules = False
        for variant_price_id in variant_price_ids:
            if not variant_price_id.variant_shopify_id:
                continue
            variant_gid = f"gid://shopify/ProductVariant/{variant_price_id.variant_shopify_id}"

            if variant_price_id.origin_type != 'RELATIVE':
                price_entry = {
                    "variantId": variant_gid,
                    "price": {"amount": str(variant_price_id.price or 0.0), "currencyCode": currency},
                }
                if variant_price_id.compare_at_price:
                    price_entry.update({"compareAtPrice": {"amount": str(variant_price_id.compare_at_price), "currencyCode": currency}})
                prices_to_add.append(price_entry)

            has_rule = (not catalog_forbids_quantity_rules) and ((variant_price_id.minimum_quantity and variant_price_id.minimum_quantity > 1) or variant_price_id.maximum_quantity or (
                        variant_price_id.increment and variant_price_id.increment > 1))
            if has_rule:
                rule_entry = {
                    "variantId": variant_gid,
                    "minimum": int(variant_price_id.minimum_quantity or 1),
                    "increment": int(variant_price_id.increment or 1),
                }
                if variant_price_id.maximum_quantity:
                    rule_entry.update({"maximum": int(variant_price_id.maximum_quantity)})
                rules_to_add.append(rule_entry)
            elif catalog_forbids_quantity_rules:
                rule_variant_resets.append(variant_gid)
            else:
                rules_to_add.append({"variantId": variant_gid, "minimum": 1, "increment": 1, })

            remote_by_min_qty = {min_qty: (b_gid, b_price) for b_gid, min_qty, b_price in remote_breaks_by_variant.get(str(variant_price_id.variant_shopify_id), [])}
            local_by_min_qty = {int(t.minimum_quantity or 1): float(t.price or 0.0) for t in variant_price_id.quantity_price_break_ids}

            for min_qty, local_price in local_by_min_qty.items():
                if min_qty in remote_by_min_qty:
                    remote_gid, remote_price = remote_by_min_qty[min_qty]
                    if float_compare(local_price, remote_price, precision_rounding=rounding) == 0:
                        continue
                    breaks_to_delete.append(remote_gid)
                breaks_to_add.append({
                    "variantId": variant_gid,
                    "minimumQuantity": min_qty,
                    "price": {"amount": str(local_price), "currencyCode": currency},
                })

            for min_qty, (remote_gid, _remote_price) in remote_by_min_qty.items():
                if min_qty not in local_by_min_qty:
                    breaks_to_delete.append(remote_gid)

        return {
            "pricesToAdd": prices_to_add,
            "pricesToDeleteByVariantId": [],
            "quantityRulesToAdd": rules_to_add,
            "quantityRulesToDeleteByVariantId": rule_variant_resets,
            "quantityPriceBreaksToAdd": breaks_to_add,
            "quantityPriceBreaksToDelete": breaks_to_delete,
        }

    def update_catalog_pricing_to_shopify(self, mk_instance_id):
        """
        Task: T7700 - Push variant prices, quantity rules, volume tiers and stale-reconcile in one mutation.
            quantityPricingByVariantUpdate carries pricesToAdd + quantityRulesToAdd +
            quantityPriceBreaksToAdd alongside pricesToDeleteByVariantId +
            quantityRulesToDeleteByVariantId + quantityPriceBreaksToDelete, so a
            single call per batch handles both upsert and stale-removal — no
            separate priceListFixedPricesDelete needed. For volume tiers we
            collect every remote break upfront so the per-batch payload can drop
            them all and re-add the current local set in the same mutation
            (deletes run before adds), making locally-removed tiers actually
            disappear on Shopify.
        Args:
            mk_instance_id (recordset): The mk.instance record.
        Returns:
            bool: True on success, False when no price list id is stored.
        Raises:
            MarketplaceException: On unrecoverable Shopify user errors.
        """
        self.ensure_one()
        if not self.price_list_shopify_id:
            return False
        price_list_gid = f"gid://shopify/PriceList/{self.price_list_shopify_id}"

        variant_prices = self.variant_price_ids.filtered(lambda r: r.variant_shopify_id)
        local_variant_ids = {rec.variant_shopify_id for rec in variant_prices}

        remote_variant_ids = set()
        remote_breaks_by_variant = {}
        cursor = None
        while True:
            remote_response = mk_instance_id.execute_graphql_query(GET_CATALOG_PRICES_PAGE, {"id": price_list_gid, "cursor": cursor})
            prices_page = (((remote_response.get('data') or {}).get('priceList') or {}).get('prices') or {})
            for node in prices_page.get('nodes') or []:
                variant_legacy = (node.get('variant') or {}).get('legacyResourceId')
                if not variant_legacy:
                    continue
                v_str = str(variant_legacy)
                remote_variant_ids.add(v_str)
                for b in (node.get('quantityPriceBreaks') or {}).get('nodes') or []:
                    b_gid = b.get('id')
                    b_min_qty = b.get('minimumQuantity')
                    b_price = float((b.get('price') or {}).get('amount') or 0.0)
                    if b_gid and b_min_qty is not None:
                        remote_breaks_by_variant.setdefault(v_str, []).append((b_gid, int(b_min_qty), b_price))
            page_info = prices_page.get('pageInfo') or {}
            if not page_info.get('hasNextPage'):
                break
            cursor = page_info.get('endCursor')
            if not cursor:
                break
        stale_vids = remote_variant_ids - local_variant_ids
        stale_gids = [f"gid://shopify/ProductVariant/{vid}" for vid in stale_vids]
        stale_break_gids = [b_gid for vid in stale_vids for b_gid, _min_qty, _price in remote_breaks_by_variant.get(vid, [])]

        remote_rule_gids = set()
        rules_cursor = None
        while True:
            rules_response = mk_instance_id.execute_graphql_query(GET_CATALOG_QUANTITY_RULES_PAGE, {"id": price_list_gid, "cursor": rules_cursor})
            rules_page = (((rules_response.get('data') or {}).get('priceList') or {}).get('quantityRules') or {})
            for node in rules_page.get('nodes') or []:
                if node.get('originType') != 'FIXED':
                    continue
                rule_variant_legacy = (node.get('productVariant') or {}).get('legacyResourceId')
                if rule_variant_legacy:
                    remote_rule_gids.add(f"gid://shopify/ProductVariant/{rule_variant_legacy}")
            rules_page_info = rules_page.get('pageInfo') or {}
            if not rules_page_info.get('hasNextPage'):
                break
            rules_cursor = rules_page_info.get('endCursor')
            if not rules_cursor:
                break

        batch_count = max((len(variant_prices) + PRICING_VARIANT_BATCH - 1) // PRICING_VARIANT_BATCH, 1 if (stale_gids or stale_break_gids or remote_rule_gids) else 0)
        rule_delete_gids = set(remote_rule_gids)
        deletes_attached = False
        user_errors = []
        for batch_index in range(batch_count):
            batch = variant_prices[batch_index * PRICING_VARIANT_BATCH:(batch_index + 1) * PRICING_VARIANT_BATCH]
            payload = self._prepare_shopify_pricing_payload(batch, remote_breaks_by_variant=remote_breaks_by_variant)
            payload["quantityRulesToDeleteByVariantId"] = []
            if not deletes_attached:
                if stale_gids:
                    payload.update({"pricesToDeleteByVariantId": stale_gids})
                if stale_break_gids:
                    payload.update({"quantityPriceBreaksToDelete": list(set(payload["quantityPriceBreaksToDelete"]) | set(stale_break_gids))})
                deletes_attached = True
            variables = {"priceListId": price_list_gid, "input": payload}
            for _attempt in range(PRICING_NOT_FOUND_RETRIES + 1):
                response = mk_instance_id.execute_graphql_query(QUANTITY_PRICING_BY_VARIANT_UPDATE, variables)
                transport_errors = response.get('errors', []) if isinstance(response, dict) else []
                if transport_errors and isinstance(transport_errors, list):
                    mk_instance_id.handle_shopify_access_errors(transport_errors, "Update Catalog Pricing")
                user_errors = (response.get('data') or {}).get('quantityPricingByVariantUpdate', {}).get('userErrors') or []
                if not user_errors:
                    break
                pruned = self.remove_missing_shopify_pricing_variants(payload, user_errors)
                if not pruned:
                    messages = ", ".join([err.get('message', '') for err in user_errors])
                    raise MarketplaceException(_(f"Failed to update pricing on Catalog {self.title}: {messages}"))
                variables = {"priceListId": price_list_gid, "input": payload}
            else:
                messages = ", ".join([err.get('message', '') for err in user_errors])
                raise MarketplaceException(_(f"Failed to update pricing on Catalog {self.title}: {messages}"))

        is_market_catalog = self.catalog_type == 'MARKET' and bool(self.market_ids)
        if rule_delete_gids and is_market_catalog:
            rule_gid_list = list(rule_delete_gids)
            for offset in range(0, len(rule_gid_list), PRICING_VARIANT_BATCH):
                chunk = rule_gid_list[offset:offset + PRICING_VARIANT_BATCH]
                rules_resp = mk_instance_id.execute_graphql_query(QUANTITY_RULES_DELETE, {"priceListId": price_list_gid, "variantIds": chunk})
                rules_transport_errors = rules_resp.get('errors', []) if isinstance(rules_resp, dict) else []
                if rules_transport_errors and isinstance(rules_transport_errors, list):
                    mk_instance_id.handle_shopify_access_errors(rules_transport_errors, "Delete Catalog Quantity Rules")
                rules_user_errors = (rules_resp.get('data') or {}).get('quantityRulesDelete', {}).get('userErrors') or []
                rules_user_errors = [err for err in rules_user_errors if
                                     (err.get('code') or '') not in ('VARIANT_NOT_FOUND', 'QUANTITY_RULE_DOES_NOT_EXIST', 'VARIANT_QUANTITY_RULE_DOES_NOT_EXIST')]
                if rules_user_errors:
                    messages = ", ".join([err.get('message', '') for err in rules_user_errors])
                    raise MarketplaceException(_(f"Failed to delete quantity rules on Catalog {self.title}: {messages}"))

        if any(vp.quantity_price_break_ids for vp in variant_prices):
            self._refresh_shopify_break_ids(mk_instance_id)
        return True

    def _resolve_shopify_pricing_error_variant_gid(self, payload, field):
        """
        Task: T7700 - Map a quantityPricingByVariantUpdate userError ``field`` path back
            to the ProductVariant GID it points at, or False when it doesn't reference a
            variant-bearing entry. Shopify returns paths like
            ['input', 'pricesToAdd', '3', 'variantId'] or
            ['input', 'pricesToDeleteByVariantId', '0'].
        Args:
            payload (dict): The quantityPricingByVariantUpdate input payload.
            field (list): userError field path tokens.
        Returns:
            str|bool: The ProductVariant GID, or False when none is referenced.
        """
        tokens = [str(t) for t in (field or [])]
        for i, token in enumerate(tokens):
            idx = tokens[i + 1] if i + 1 < len(tokens) else None
            if idx is None or not idx.isdigit():
                continue
            idx = int(idx)
            if token in _PRICING_VARIANT_DICT_KEYS:
                entries = payload.get(token) or []
                if idx < len(entries):
                    return (entries[idx] or {}).get('variantId')
            elif token in _PRICING_VARIANT_GID_KEYS:
                entries = payload.get(token) or []
                if idx < len(entries):
                    return entries[idx]
        return False

    def remove_missing_shopify_pricing_variants(self, payload, user_errors):
        """
        Task: T7700 - React to "Variant not found." userErrors the same way the listing-item price push
            does: strip every reference to the missing variant from the in-flight ``payload`` so
            the retry is clean, and when the variant maps to a local catalog row, unlink its
            mk.listing.item (remote-only stale variants just vanish from the delete set). Mutates
            ``payload`` in place and returns the set of removed variant GIDs (empty when no error
            was a recoverable variant-not-found, signalling the caller to raise).
        Args:
            payload (dict): The in-flight quantityPricingByVariantUpdate input (mutated).
            user_errors (list): userErrors returned by the mutation.
        Returns:
            set: Removed variant GIDs (empty when nothing recoverable was pruned).
        """
        missing_gids = set()
        for err in user_errors:
            if 'variant not found' not in (err.get('message') or '').lower():
                continue
            gid = self._resolve_shopify_pricing_error_variant_gid(payload, err.get('field'))
            if gid:
                missing_gids.add(gid)
        if not missing_gids:
            return missing_gids

        for key in _PRICING_VARIANT_DICT_KEYS:
            payload[key] = [entry for entry in (payload.get(key) or []) if (entry or {}).get('variantId') not in missing_gids]
        for key in _PRICING_VARIANT_GID_KEYS:
            payload[key] = [gid for gid in (payload.get(key) or []) if gid not in missing_gids]

        missing_legacy_ids = {str(extract_numeric_id(gid)) for gid in missing_gids}
        variant_price_ids = self.variant_price_ids.filtered(lambda r: r.variant_shopify_id in missing_legacy_ids)
        for variant_price_id in variant_price_ids:
            listing_item_id = variant_price_id.mk_listing_item_id
            if listing_item_id:
                _logger.warning(
                    f"UPDATE CATALOG PRICING: Removing Listing Item {listing_item_id.name} from Catalog {self.title} (variant {listing_item_id.mk_id}) — Variant no longer exists on Shopify.")
                listing_item_id.sudo().unlink()
            else:
                variant_price_id.sudo().unlink()
        return missing_gids

    def _refresh_shopify_break_ids(self, mk_instance_id):
        """
        Task: T7700 - Re-paginate the catalog's price list after a quantityPricingByVariantUpdate
            and back-fill shopify_break_id on local tiers, keyed by (variant_id, minimum_quantity).
            The push always delete-and-re-adds breaks for every touched variant, so every
            local tier ends up with a fresh GID from Shopify; this method makes those
            GIDs round-trip into Odoo so the *next* push's delete-set is built from the
            real current state instead of stale or empty values.
        Args:
            mk_instance_id (recordset): The mk.instance record.
        """
        self.ensure_one()
        if not self.price_list_shopify_id:
            return
        price_list_gid = f"gid://shopify/PriceList/{self.price_list_shopify_id}"
        lookup = {}
        cursor = None
        while True:
            resp = mk_instance_id.execute_graphql_query(GET_CATALOG_PRICES_PAGE, {"id": price_list_gid, "cursor": cursor})
            prices_page = (((resp.get('data') or {}).get('priceList') or {}).get('prices') or {})
            for node in prices_page.get('nodes') or []:
                variant_legacy = (node.get('variant') or {}).get('legacyResourceId')
                if not variant_legacy:
                    continue
                for b in (node.get('quantityPriceBreaks') or {}).get('nodes') or []:
                    b_legacy = extract_numeric_id(b.get('id'))
                    b_min_qty = b.get('minimumQuantity')
                    if b_legacy and b_min_qty is not None:
                        lookup[(str(variant_legacy), int(b_min_qty))] = str(b_legacy)
            page_info = prices_page.get('pageInfo') or {}
            if not page_info.get('hasNextPage'):
                break
            cursor = page_info.get('endCursor')
            if not cursor:
                break
        for vp in self.variant_price_ids.filtered('variant_shopify_id'):
            for tier in vp.quantity_price_break_ids:
                key = (str(vp.variant_shopify_id), int(tier.minimum_quantity or 1))
                new_id = lookup.get(key)
                if new_id and tier.shopify_break_id != new_id:
                    tier.shopify_break_id = new_id

    def action_update_catalog_to_shopify(self):
        """
        Task: T7700 - Form/list-button entry point: push every catalog in self to Shopify
            and notify the user.
        Returns:
            bool: True.
        Raises:
            MarketplaceException: On multi-instance selection or unconfirmed instance.
        """
        if not self:
            return True
        if len(self.mapped('mk_instance_id')) > 1:
            raise MarketplaceException(_('Operation not allowed! Make sure selected catalogs belong to only one instance.'))
        elif any(rec.mk_instance_id.state != 'confirmed' for rec in self):
            raise MarketplaceException(_("You can update a catalog only with a confirmed instance. Please ensure the instance is confirmed before updating the catalog."))
        self.update_catalog_to_shopify_ts()
        if len(self) == 1:
            message = _("The catalog <b>%s</b> has been updated to Shopify.") % self.title
        else:
            message = _("%s catalogs have been updated to Shopify.") % len(self)
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'marketplace_notification', {'title': _('Update Completed'),
                                                                                            'message': message,
                                                                                            'message_is_html': True,
                                                                                            'type': 'info',
                                                                                            'sticky': False, })
        return True

    def action_sync_shopify_catalog_to_odoo(self):
        """
        Task: T7700 - Re-fetch this specific catalog from Shopify and sync its products,
            then notify the user.
        Raises:
            MarketplaceException: If the Shopify fetch fails.
        """
        # Reusing the existing import logic but limiting it to this specific Catalog ID
        self.ensure_one()
        try:
            self.import_catalogs_from_shopify(self.mk_instance_id, mk_catalog_id=self.shopify_catalog_id)
        except MarketplaceException:
            raise
        except Exception as e:
            raise MarketplaceException(f"Failed to fetch Shopify Catalog: {str(e)}")

        message = f'The catalog <b>{self.title}</b> has been updated with the latest data from Shopify.'
        self.env['bus.bus']._sendone(self.env.user.partner_id, 'marketplace_notification', {'title': 'Update Completed',
                                                                                            'message': message,
                                                                                            'message_is_html': True,
                                                                                            'type': 'info',
                                                                                            'sticky': False, })

        return True

    def action_open_shopify_add_listings_wizard(self):
        """
        Task: T7700 - Form-button entry point: open the shared mk.operation wizard scoped
            to this catalog so the user can multi-pick listings and fan them out into
            variant price rows on this catalog.
        Returns:
            dict: An ir.actions.act_window action opening the wizard.
        """
        self.ensure_one()
        return {
            'name': _("Add Listings to Catalog"),
            'type': 'ir.actions.act_window',
            'res_model': 'mk.operation',
            'view_mode': 'form',
            'views': [(self.env.ref('shopify.mk_operation_add_listings_to_catalog_view').id, 'form')],
            'target': 'new',
            'context': {
                'default_shopify_catalog_id': self.id,
                'default_mk_instance_id': self.mk_instance_id.id,
            },
        }

    def action_shopify_catalog_products(self):
        """
        Task: T7700 - Migrate Shopify REST API to Graphql API
            This method returns an action that opens a window displaying the list of products associated with the current collection.
             The list is displayed in the `mk.listing` model with both "list" and "form" view modes, allowing the user to see and edit product details.
        Returns:
           action(dict): An action dictionary used to open a window displaying collection products.
        """
        form_id = self.env.ref('base_marketplace.mk_listing_form_view')
        list_id = self.env.ref('base_marketplace.mk_listing_tree_view')
        action = {
            'name': _('Catalog Products'),
            'view_id': False,
            'res_model': 'mk.listing',
            'domain': [('id', 'in', self.variant_price_ids.mk_listing_id.ids)],
            'context': self.env.context,
            'view_mode': 'list,form',
            'view_type': 'form',
            'views': [(list_id.id, 'list'), (form_id.id, 'form')],
            'type': 'ir.actions.act_window',
        }
        return action

    def open_catalog_in_shopify(self):
        """
        Task: T7700 - Redirect the user directly to the Catalog page in Shopify Admin.
        Args:
            None.
        Returns:
            dict: An ir.actions.act_url action opening the Shopify Admin catalog page.
        """
        self.ensure_one()
        marketplace_url = self.mk_instance_id.shop_url + '/admin/catalogs/' + self.shopify_catalog_id
        return {
            'type': 'ir.actions.act_url',
            'url': marketplace_url,
            'target': 'new',
        }
