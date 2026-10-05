import base64
import binascii
import hashlib
import logging
import urllib.parse
from types import SimpleNamespace

import requests
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from odoo.tools.image import image_process
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.base_marketplace.models.misc import guess_mimetype
from odoo.addons.shopify.models.graphql_queries import (JOB_STATUS, PUBLISH_COLLECTION, UNPUBLISH_COLLECTION,
                                                        GET_COLLECTION_PRODUCT_AFTER_CURSOR,
                                                        GET_IMPORT_COLLECTIONS_WITH_SOURCES, GET_COLLECTION_WITH_SOURCES,
                                                        EXPORT_COLLECTION_WITH_SOURCES, UPDATE_COLLECTION_WITH_SOURCES,
                                                        GET_COLLECTION_SOURCE_STATE, STORE_CURRENCY,
                                                        CHECK_RECORDS_EXIST, GET_SOURCE_INCLUSION_SELECTIONS_AFTER_CURSOR,
                                                        GET_SOURCE_EXCLUSION_SELECTIONS_AFTER_CURSOR)
from odoo.addons.shopify.models.misc import convert_shopify_datetime_to_utc, extract_numeric_id
from odoo.addons.shopify.models.collections_condition import resolve_condition_spec, RELATION_COMPAT
from odoo.addons.shopify.models.collections_source import default_source_title

_logger = logging.getLogger("Teqstars:Shopify")

SORT_ORDER_SELECTION = [('ALPHA_ASC', 'Alphabetically, in ascending order (A - Z)'),
                        ('ALPHA_DESC', 'Alphabetically, in descending order (Z - A)'),
                        ('BEST_SELLING', 'By best-selling products'),
                        ('CREATED', 'By date created, in ascending order (oldest - newest)'),
                        ('CREATED_DESC', 'By date created, in descending order (newest - oldest)'),
                        ('MANUAL', 'Order created by the shop owner'),
                        ('PRICE_ASC', 'By price, in ascending order (lowest - highest)'),
                        ('PRICE_DESC', 'By price, in descending order (highest - lowest)'),
                        ('MOST_RELEVANT', 'By most relevant products.')]


CONDITION_TYPENAME_TO_COLUMN = {
    'ProductTitle': 'TITLE',
    'ProductType': 'TYPE',
    'ProductVendor': 'VENDOR',
    'ProductTag': 'TAG',
    'ProductStatus': 'PRODUCT_STATUS',
    'ProductCategory': 'PRODUCT_CATEGORY_ID',
    'VariantTitle': 'VARIANT_TITLE',
    'VariantPrice': 'VARIANT_PRICE',
    'VariantCompareAtPrice': 'VARIANT_COMPARE_AT_PRICE',
    'VariantWeight': 'VARIANT_WEIGHT',
    'VariantInventory': 'VARIANT_INVENTORY',
}

EXCLUSION_TYPENAME_TO_COLUMN = {
    'ProductCategory': 'PRODUCT_CATEGORY_ID',
    'ProductTag': 'TAG',
    'ProductType': 'TYPE',
    'ProductVendor': 'VENDOR',
    'Collection': 'EXCLUDE_COLLECTION',
}

CONDITION_COLUMN_LABELS = {
    'TITLE': 'Product Title', 'TYPE': 'Product Type', 'VENDOR': 'Product Vendor',
    'TAG': 'Tag', 'PRODUCT_STATUS': 'Product Status', 'PRODUCT_CATEGORY_ID': 'Product Category',
    'VARIANT_TITLE': 'Variant Title', 'VARIANT_PRICE': 'Price',
    'VARIANT_COMPARE_AT_PRICE': 'Compare at Price', 'VARIANT_WEIGHT': 'Weight',
    'VARIANT_INVENTORY': 'Inventory Stock', 'EXCLUDE_COLLECTION': 'In Collection',
}
CONDITION_TYPE = [('all', 'All Condition'), ('any', 'Any Condition')]


class ShopifyCollection(models.Model):
    _name = "shopify.collection.ts"
    _description = "Collection"

    name = fields.Char("Name", size=255, required=True)
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade')
    marketplace = fields.Selection(related="mk_instance_id.marketplace", string='Marketplace')
    shopify_collection_id = fields.Char("Collection ID", copy=False)
    exported_in_shopify = fields.Boolean("Exported in Shopify", copy=False)
    image = fields.Binary("Image", help="Image associated with the custom collection.")
    handle = fields.Char("Handle", size=255,
                         help="A human-friendly unique string for the custom collection automatically generated from its title. This is used in shop themes by the Liquid templating language to refer to the custom collection.")
    shopify_update_date = fields.Datetime("Update Date", help="The date and time when the custom collection was last modified.")
    sort_order = fields.Selection(SORT_ORDER_SELECTION, "Sort Order", default="MANUAL")
    template_suffix = fields.Char("Template Suffix",
                                  help="The suffix of the liquid template being used. For example, if the value is custom, then the collection is using the "
                                       "collection.custom.liquid template. If the value is null, then the collection is using the default collection.liquid.")
    description = fields.Html('Description', sanitize_attributes=False,
                              help="The description of the custom collection, complete with HTML markup. Many templates display this on their custom collection pages.")
    shopify_sales_channel_ids = fields.Many2many(comodel_name="shopify.sales.channels.ts", string="Shopify Sales Channels", copy=False,
                                                 help="Sales channels/channels where this collections is published.")
    mk_listing_ids = fields.Many2many("mk.listing", "shopify_collection_tmpl_rel", "collection_id", "template_id", "Shopify Product Templates")
    product_count = fields.Integer("Variants", compute='_product_count')
    condition_type = fields.Selection(CONDITION_TYPE, "Condition Type", default="all", help="Whether the product must match all the rules to be included in the smart collection")
    is_disjunctive = fields.Boolean("Disjunctive", default=False,
                                    help="Whether the product must match all the rules to be included in the smart collection.\n"
                                         "True: Products only need to match one or more of the rules to be included in the smart collection.\n"
                                         "False: Products must match all of the rules to be included in the smart collection.")
    source_ids = fields.One2many("shopify.collection.source.ts", "collection_id", string="Sources", help="Groups of products that make up this collection.")
    collection_condition_ids = fields.One2many("shopify.collection.condition.ts", "shopify_collection_id", string="Conditions", domain=[('kind', '=', 'inclusion')])
    collection_job_ids = fields.One2many("shopify.collection.job", "collection_id", string="Collection Job")
    is_available_in_website = fields.Boolean("Available in Website")
    image_url = fields.Char('Image URL')
    hand_picked_listing_ids = fields.Many2many("mk.listing", compute='_compute_hand_picked_listing_ids',
                                               string="Hand-picked Items", help="Whole products added by hand, which can be removed from the collection.")

    @api.depends('source_ids.selection_ids.mk_listing_id', 'source_ids.selection_ids.mk_listing_item_ids',
                 'source_ids.exclusion_listing_ids', 'source_ids.condition_ids', 'source_ids.source_kind',
                 'source_ids.target_type', 'mk_listing_ids')
    def _compute_hand_picked_listing_ids(self):
        """
        Task: T8887 - Find the products that can be removed from the Collection Items tab.
            These are whole products added by hand to a Products source, as Shopify shows its
            remove button only on those. Products added by their variants are left out.
        """
        for collection in self:
            whole_product_listings = variant_level_listings = self.env['mk.listing']
            for source in collection.source_ids.filtered(lambda record: record.source_kind == 'conditions'):
                hand_picked_listings = collection.get_export_selection_listings(source)
                if source.target_type == 'VARIANTS':
                    variant_level_listings |= hand_picked_listings
                    continue
                listings_with_picked_variants = source.selection_ids.filtered('mk_listing_item_ids').mk_listing_id
                whole_product_listings |= hand_picked_listings - listings_with_picked_variants - source.exclusion_listing_ids
            collection.hand_picked_listing_ids = whole_product_listings - variant_level_listings

    def web_read(self, specification):
        """
        Task: T8887 - Read the collection for the form and tell each Collection Items card its collection.
            The card needs it to show its variant count. The form reads the record before it
            knows the record id, so the view cannot pass it.
        Args:
            specification (dict): The fields the form asks for.
        Returns:
            list: The values of the collection for the form.
        """
        if 'mk_listing_ids' in specification and len(self) == 1:
            item_spec = dict(specification['mk_listing_ids'])
            item_spec['context'] = dict(item_spec.get('context') or {}, collection_id=self.id)
            specification = dict(specification, mk_listing_ids=item_spec)
        return super().web_read(specification)

    def get_variant_level_items(self):
        """
        Task: T8887 - Find the products this collection holds with only some of their variants.
        Returns:
            dict: Product listing id as key, and its selected variants as value.
        """
        self.ensure_one()
        held_variants_by_listing = {}
        for source in self.source_ids.filtered(lambda record: record.source_kind == 'conditions'):
            for line in source.selection_ids.filtered('mk_listing_item_ids'):
                if line.mk_listing_id not in self.hand_picked_listing_ids:
                    held_variants_by_listing.setdefault(line.mk_listing_id.id, self.env['mk.listing.item'])
                    held_variants_by_listing[line.mk_listing_id.id] |= line.mk_listing_item_ids
        return held_variants_by_listing

    def remove_hand_picked_items(self, listings):
        """
        Task: T8887 - Remove the given products from every source that holds them as added by hand.
            Products that come from rules stay, as Shopify cannot remove those one by one.
        Args:
            listings (recordset): Products removed on the Collection Items tab.
        Returns:
            bool: True.
        """
        self.ensure_one()
        self.source_ids.selection_ids.filtered(lambda line: line.mk_listing_id in listings).sudo().unlink()
        return True

    def update_hand_picked_items(self, added_listings, removed_listings):
        """
        Task: T8887 - Show the products added or removed by hand on the collection right away, so its Products count is right on save.
            A removed product leaves only when no rule or linked collection can still hold it; otherwise the next sync fixes it.
        Args:
            added_listings (recordset): Products just added by hand.
            removed_listings (recordset): Products just removed by hand.
        Returns:
            bool: True.
        """
        self.ensure_one()
        has_rules = any(source.condition_ids or source.source_kind == 'sub_collections' for source in self.source_ids)
        removed_listings = self.env['mk.listing'] if has_rules else removed_listings - self.source_ids.selection_ids.mk_listing_id
        commands = [(4, listing.id) for listing in added_listings - self.mk_listing_ids]
        commands += [(3, listing.id) for listing in removed_listings & self.mk_listing_ids]
        if commands:
            self.with_context(skip_collection_job=True).write({'mk_listing_ids': commands})
        return True

    @api.depends('mk_listing_ids')
    def _product_count(self):
        for collection_id in self:
            collection_id.product_count = len(collection_id.mk_listing_ids)

    @api.constrains('mk_listing_ids')
    def _check_collection_jobs(self):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            Ensure that products in a collection cannot be modified while collection jobs are active.
        Raises:
            MarketplaceException: If there are active collection jobs associated with the collection, modification of products is not allowed.
        """
        skip_collection_job = self.env.context.get('skip_collection_job', False)
        if self.collection_job_ids and not skip_collection_job:
            raise MarketplaceException(_("You cannot modify products in this collection because there are associated Collection Jobs. Please wait for jobs to complete or remove them."))

    def write(self, vals):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            Override write to update the collection image URL when the image changes.
            This method Revalidates the image binary on update. Detects the image MIME type and enforces supported formats.
        Args:
            vals: dictionary of values to update
        Raises:
            MarketplaceException: Raises an exception for unsupported image types.
        Returns:
            True if the write operation succeeds
        """
        old_listings_by_collection = {}
        if 'mk_listing_ids' in vals and not self.env.context.get('skip_collection_job'):
            old_listings_by_collection = {collection: collection.mk_listing_ids for collection in self}
        res = super(ShopifyCollection, self).write(vals)
        for collection, old_listing_ids in old_listings_by_collection.items():
            removed_listing_ids = old_listing_ids - collection.mk_listing_ids
            if removed_listing_ids:
                collection.remove_hand_picked_items(removed_listing_ids)
        if 'image' not in vals and 'image_url' not in vals:
            return res
        for record in self:
            if 'image_url' in vals:
                super(ShopifyCollection, record).write(vals)
            elif 'image' in vals:
                image_data = vals.get('image')
                if not image_data:
                    record.image_url = False
                if image_data:
                    mimetype, image_types = self.process_collection_image_url(record, image_data)
                    if mimetype in image_types:
                        return res
                    elif mimetype not in image_types:
                        raise MarketplaceException(_("Unsupported image type: %s. Supported: JPEG, PNG, GIF, WebP") % mimetype)
        return res

    @api.model_create_multi
    def create(self, vals):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            Override create to process collection images and generate a public image URL.
            this method Validates the uploaded image binary and detects its MIME type. Allows only supported image formats (JPEG, PNG, GIF, WebP).
        Args:
            vals: list of value dictionaries used to create records
        Raises:
            MarketplaceException: Raises an exception for unsupported image types.
        Returns:
            newly created recordset
        """
        res = super(ShopifyCollection, self).create(vals)
        for data in vals:
            if 'image' not in data:
                return res
        for record in vals:
            image_data = record.get('image')
            if not image_data:
                return res
            if image_data:
                decode_binary = base64.b64decode(image_data, validate=True)

                # Guess the MIME type and determine the image extension
                mimetype = guess_mimetype(decode_binary, default='image/png')
                # jpeg/ jpg, png, gif, WebP - support in collection
                image_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
                if mimetype in image_types:
                    imgext = '.' + mimetype.split('/')[1]
                    if imgext == '.svg+xml':
                        imgext = '.svg'

                    # Generate a safe name for the image URL
                    safe_name = urllib.parse.quote(record.get('name')).replace('/', '-')
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

                    # Construct the image URL
                    shopify_collection_id = record.get('shopify_collection_id', '')
                    db_name = self.env.cr.dbname
                    encoded_id = base64.urlsafe_b64encode(str(shopify_collection_id).encode('utf-8')).decode('utf-8')
                    url = f"{base_url}/shopify/collections/image/{db_name}/{encoded_id}/{safe_name}{imgext}"
                    res.image_url = url
                elif mimetype not in image_types:
                    raise MarketplaceException(_("Unsupported image type: %s. Supported: JPEG, PNG, GIF, WebP") % mimetype)
                return res
        return res

    @api.model
    def _import_notice_key(self, mk_instance_id):
        """
        Task: T8887 - The parameter holding the notice of one Shopify store.
        Args:
            mk_instance_id (int): The instance the form is showing.
        Returns:
            str: Key of the parameter.
        """
        return 'shopify.collection_import_notice.%s' % mk_instance_id

    @api.model
    def get_import_notice(self, mk_instance_id):
        """
        Task: T8887 - Tell the form whether the "import from Shopify first" strip is still due for this store.
        Args:
            mk_instance_id (int): The instance the form is showing.
        Returns:
            bool: True while this store's notice has not been closed.
        """
        if not mk_instance_id:
            return False
        return bool(self.env['ir.config_parameter'].sudo().get_param(self._import_notice_key(mk_instance_id)))

    @api.model
    def dismiss_import_notice(self, mk_instance_id):
        """
        Task: T8887 - Close the "import from Shopify first" strip of this store for good.
        Args:
            mk_instance_id (int): The instance the form is showing.
        Returns:
            bool: True.
        """
        if mk_instance_id:
            self.env['ir.config_parameter'].sudo().set_param(self._import_notice_key(mk_instance_id), False)
        return True

    def process_collection_image_url(self, record, image_data):
        """
        Task: T5963 - Migrate Shopify REST API to GraphQL
         Args:
            record (record_type): The record object that contains the image information.
            image_data (str): Base64-encoded image data for the image associated with the record.
        Returns:
            tuple: A tuple containing:
                mimetype: The MIME type of the decoded image (e.g., 'image/jpeg', 'image/png').
                image_types: A list of supported image MIME types ('image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp').
        Raises:
            MarketplaceException: If the MIME type of the image is unsupported. Only JPEG, PNG, GIF, and WebP are supported.
        """
        decode_binary = base64.b64decode(image_data, validate=True)

        # Guess the MIME type and determine the image extension
        mimetype = guess_mimetype(decode_binary, default='image/png')
        image_types = ["image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"]
        if mimetype in image_types:

            imgext = '.' + mimetype.split('/')[1]
            if imgext == '.svg+xml':
                imgext = '.svg'

            # Generate a safe name for the image URL
            safe_name = urllib.parse.quote(record.name + imgext, safe='').replace('/', '-')
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

            # Stamp the binary's md5 onto the URL as a fragment so prepare_update_collection_vals
            # can detect "image unchanged since last sync" without a new field or extra API call.
            image_hash = hashlib.md5(decode_binary).hexdigest()
            url = base_url + f'/shopify/collections/image/{self.env.cr.dbname}/{base64.urlsafe_b64encode(str(record.id).encode("utf-8")).decode("utf-8")}/{safe_name}#h={image_hash}'
            record.image_url = url
        elif mimetype not in image_types:
            raise MarketplaceException(_("Unsupported image type: %s. Supported: JPEG, PNG, GIF, WebP") % mimetype)
        return mimetype, image_types

    def shopify_open_export_collection_view(self):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
        Prepares and returns an action for exporting a collection to Shopify.
        This method customizes an existing action ('shopify.action_collection_export_to_marketplace') by:
        1. Changing the action's name to "Export Collection to Shopify."
        2. Updating the view to display a form for exporting collections,
           specifically referencing 'shopify.mk_operation_export_collection_to_mk_view'.
        Returns:
            dict: The action dictionary with the updated name, view, and context, ready for execution.
        """
        action = self.env.ref('shopify.action_collection_export_to_marketplace').sudo().read()[0]
        action['name'] = _("Export Collection to Shopify")
        action['views'] = [(self.env.ref('shopify.mk_operation_export_collection_to_mk_view').sudo().id, 'form')]
        ctx = self.env.context.copy()
        active_ids = ctx.get('active_ids')
        if active_ids and len(active_ids) == 1:
            shopify_collection = self.browse(active_ids[0])
            ctx['default_mk_instance_id'] = shopify_collection.mk_instance_id.id
            ctx['default_is_publish_or_unpublish'] = True
        action['context'] = ctx
        return action

    def shopify_open_update_collection_view(self):
        """
        Task: T7628 - Set the default sales channel action as Published.
        Task: T5963 - Migrate Shopify REST API to Graphql API
        Prepares and returns an action for updating a collection in Shopify.
        This method customizes an existing action ('shopify.action_collection_update_to_marketplace') by:
        1. Changing the action's name to "Update Collection in Shopify."
        2. Setting the view to a form for updating collections, specifically
           referencing 'shopify.mk_operation_update_collection_to_shopify_view'.
        Returns:
            dict: The action dictionary with the updated name, view, and context, ready for execution.
        """
        action = self.env.ref('shopify.action_collection_update_to_marketplace').sudo().read()[0]
        action['name'] = _("Update Collection in Shopify")
        action['views'] = [(self.env.ref('shopify.mk_operation_update_collection_to_shopify_view').sudo().id, 'form')]
        ctx = self.env.context.copy()
        active_ids = ctx.get('active_ids')
        if active_ids and len(active_ids) == 1:
            shopify_collection = self.browse(active_ids[0])
            shopify_sales_channel_ids = shopify_collection.shopify_sales_channel_ids.ids
            ctx['default_shopify_sales_channel_ids'] = [(6, 0, shopify_sales_channel_ids)]
            ctx['default_mk_instance_id'] = shopify_collection.mk_instance_id.id
        ctx['default_is_publish_or_unpublish'] = True
        action['context'] = ctx
        return action

    def action_open_collection_operation_view(self):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            This method handles the opening of the operation view for a collection. It determines whether the collection is in a state of being
            exported or updated to Shopify, and opens the appropriate view based on the collection's status.
        Returns:
            action(dict): The action to open the appropriate collection operation view (either export or update).
        Raises:
            MarketplaceException: If the selected collections are mixed with exported and non-exported listings.
        """
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids')
        if active_model == 'shopify.collection.ts' and active_ids:
            collection = self.env[active_model].browse(active_ids)
            mk_instance = collection.mapped('mk_instance_id')
            # making sure we only open marketplace wise view only if selected collection belongs to single instance.
            if len(mk_instance) == 1:
                if len(set(collection.mapped('exported_in_shopify'))) > 1:
                    raise MarketplaceException(
                        _("Please ensure that the selected Collection are intended for either updating or exporting only. Do not mix exported Collection and not exported Collection."),
                        _("Operation not allowed!"))
                if collection[0].exported_in_shopify:
                    if hasattr(self, '%s_open_update_collection_view' % mk_instance.marketplace):
                        return getattr(self, '%s_open_update_collection_view' % mk_instance.marketplace)()
                else:
                    if hasattr(self, '%s_open_export_collection_view' % mk_instance.marketplace):
                        return getattr(self, '%s_open_export_collection_view' % mk_instance.marketplace)()
            collection = self.env[active_model].browse(active_ids)
            if len(collection.mapped('mk_instance_id')) > 1:
                raise MarketplaceException(_('Operation not allowed! Make sure selected collection belongs to only one instance'))
            if collection and collection[0].exported_in_shopify:
                action = self.sudo().env.ref('shopify.action_collection_export_to_marketplace').read()[0]
            else:
                action = self.sudo().env.ref('shopify.action_collection_update_to_marketplace').read()[0]
            context = self.env.context.copy()
            action['context'] = context
            return action

    def action_collection_products(self):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            This method returns an action that opens a window displaying the list of products associated with the current collection.
             The list is displayed in the `mk.listing` model with both "list" and "form" view modes, allowing the user to see and edit product details.
        Returns:
           action(dict): An action dictionary used to open a window displaying collection products.
        """
        form_id = self.env.ref('base_marketplace.mk_listing_form_view')
        list_id = self.env.ref('base_marketplace.mk_listing_tree_view')
        action = {
            'name': _('Collection Products'),
            'view_id': False,
            'res_model': 'mk.listing',
            'domain': [('id', 'in', self.mk_listing_ids.ids)],
            'context': self.env.context,
            'view_mode': 'list,form',
            'view_type': 'form',
            'views': [(list_id.id, 'list'), (form_id.id, 'form')],
            'type': 'ir.actions.act_window',
        }
        return action

    def _get_paginated_products_from_shopify_collection(self, collection, mk_instance_id):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            This method handles the fetching of all products within a given Shopify collection, taking into account pagination.
            It retrieves all products in the collection by iterating over multiple pages if needed.

        Args:
            collection (dict): The Shopify collection data, containing a list of products.
            mk_instance_id (recordset): The record of the mk.instance model.
        Returns:
           remaining_collection_product(list): A list of all products in the collection, including products across multiple pages.
        Raises:
            MarketplaceException: If an error occurs during the API request or data processing.
        """
        all_collection_product = collection.get('products', [])
        remaining_collection_product = []
        collection_id = collection.get('id', '')
        if all_collection_product:
            remaining_collection_product.extend(all_collection_product[:len(all_collection_product) - 1])
            page_info = all_collection_product[-1].get('pageInfo', {})
            cursor = page_info.get('endCursor', None)
            has_next_page = page_info.get('hasNextPage', False)
            if not page_info or not has_next_page:
                return remaining_collection_product
            while has_next_page and cursor:
                try:
                    variables = {"cursor": cursor, "id": collection_id}
                    res = mk_instance_id.execute_graphql_query(GET_COLLECTION_PRODUCT_AFTER_CURSOR, variables)
                    user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                    if user_errors and isinstance(user_errors, list):
                        mk_instance_id.handle_shopify_access_errors(user_errors, "collection pagination")
                    response_data = res.get('data', {}).get('collection', {}).get('products', {}) if res.get("data", {}).get("collection", {}) else {}
                    if response_data:
                        remaining_collection_product.extend(response_data.get('nodes', []))
                        remaining_page_info = response_data.get('pageInfo', {})
                        has_next_page = remaining_page_info.get('hasNextPage', False)
                        cursor = remaining_page_info.get('endCursor', None)
                        if not cursor or not has_next_page:
                            break
                except MarketplaceException:
                    raise
                except Exception as e:
                    raise MarketplaceException(f"Failed to fetch Shopify products: {str(e)}")
            return remaining_collection_product

    def sync_collection_products(self, collection, mk_instance_id=None):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            This method syncs products from a specific Shopify collection to Odoo by checking if each product in the collection exists in Odoo.
            If a product does not exist, it imports the product as a listing in Odoo.
        Args:
            collection (dict): The Shopify collection data.
            mk_instance_id (recordset): The record of the mk.instance model.
        Returns:
            shopify_product_list(list): A list of product IDs that were successfully synced.
        """
        mk_listing_obj = self.env['mk.listing']
        mk_instance_id = self.mk_instance_id or mk_instance_id
        shopify_product_list, all_collection_products = [], []
        collection_id = extract_numeric_id(collection.get('id'))
        all_collection_products = self._get_paginated_products_from_shopify_collection(collection, mk_instance_id)
        if all_collection_products:
            for product in all_collection_products:
                product_id = extract_numeric_id(product.get('id', ''))
                listing_id = mk_listing_obj.search([('mk_id', '=', product_id), ('mk_instance_id', '=', mk_instance_id.id)])
                if not listing_id:
                    mk_listing_obj.shopify_import_listings(mk_instance_id, False, False, mk_listing_id=str(product_id))
                    listing_id = mk_listing_obj.search([('mk_id', '=', product_id), ('mk_instance_id', '=', mk_instance_id.id)])
                if not listing_id:
                    log_message = f"Odoo Product {product_id} not found for a Collection {collection_id}"
                    _logger.error(log_message)
                else:
                    shopify_product_list.append(product_id)
        return shopify_product_list

    @api.model
    def get_condition_column(self, column_name):
        """
        Task: T8887 - Find the condition column for a Shopify condition type, and create it when missing.
        Args:
            column_name (str): Shopify name of the column, e.g. TAG.
        Returns:
            recordset: The condition column.
        """
        column_obj = self.env['shopify.collection.condition.column.ts']
        column = column_obj.search([('shopify_name', '=', column_name)], limit=1)
        if not column:
            column = column_obj.create({'name': CONDITION_COLUMN_LABELS.get(column_name, column_name), 'shopify_name': column_name})
        return column

    @api.model
    def prepare_condition_value_vals(self, condition_dict):
        """
        Task: T8887 - Prepare the value lines of one condition received from Shopify.
            A condition holds a list of texts (tags, titles), a list of categories, one number
            (stock) or an amount with its currency or unit (price, weight). The currency or unit
            is kept apart, so the value stays a plain number.
        Args:
            condition_dict (dict): One condition as received from Shopify.
        Returns:
            list: Values for the condition value lines.
        """
        values = condition_dict.get('values')
        if isinstance(values, list):
            value_vals_list = []
            for index, value in enumerate(values):
                if isinstance(value, dict):
                    reference = value.get('category') or value
                    value_vals_list.append({'sequence': index * 10,
                                            'category_id': reference.get('id') or False,
                                            'category_name': reference.get('name') or reference.get('title') or False,
                                            'include_descendants': bool(value.get('includeDescendants'))})
                else:
                    value_vals_list.append({'sequence': index * 10, 'value': str(value)})
            return [value_vals for value_vals in value_vals_list if value_vals.get('value') or value_vals.get('category_id') or value_vals.get('category_name')]

        value = condition_dict.get('value')
        if isinstance(value, dict):
            amount = value.get('amount') if value.get('amount') is not None else value.get('value')
            unit = value.get('currencyCode') or value.get('unit') or False
            return [{'sequence': 0, 'value': str(amount) if amount is not None else False, 'unit': unit}]
        if value not in (None, False):
            return [{'sequence': 0, 'value': str(value)}]
        return []

    def get_shopify_shop_currency(self):
        """
        Task: T8887 - Get the currency of the Shopify store, for price conditions entered in Odoo.
            The company currency in Odoo can differ from the store currency, so it is used only
            when the store cannot be reached.
        Returns:
            str: Currency code, e.g. EUR.
        """
        self.ensure_one()
        try:
            res = self.mk_instance_id.execute_graphql_query(STORE_CURRENCY)
            currency = res.get('data', {}).get('shop', {}).get('currencyCode') if res.get('data', {}).get('shop', {}) else None
        except Exception as error:
            _logger.warning("Could not read the Shopify store currency: %s", error)
            currency = None
        return currency or self.mk_instance_id.company_id.currency_id.name or 'USD'

    def prepare_condition_input(self, condition, is_exclusion=False, shop_currency=None):
        """
        Task: T8887 - Prepare one condition line in the form Shopify expects.
        Args:
            condition (recordset): The condition line.
            is_exclusion (bool): True for an exclude condition.
            shop_currency (str): Store currency, read once for all price conditions.
        Returns:
            tuple: The prepared condition and an error message; one of the two is always empty.
        """
        column_name, condition_spec = resolve_condition_spec(condition.column_id.shopify_name, 'exclusion' if is_exclusion else 'inclusion')
        if not condition_spec:
            return False, _("Condition '%(column)s' cannot be sent to Shopify yet.") % {'column': condition.column_id.name}
        input_key, shape, _allowed_relations = condition_spec
        relation = RELATION_COMPAT.get(input_key, {}).get(condition.relation, condition.relation)
        match_type = 'ALL' if condition.match_type == 'all' else 'ANY'
        value_records = condition.value_ids
        if not value_records and condition.condition:
            return False, _("Condition '%(column)s' has no values.") % {'column': condition.column_id.name}

        if shape == 'ids':
            reference_list = [value.category_id for value in value_records if value.category_id]
            if not reference_list:
                return False, _("Exclude condition '%(column)s' has no collection selected.") % {'column': condition.column_id.name}
            return {input_key: {'values': reference_list}}, False

        if shape == 'category':
            category_list = [{'categoryId': value.category_id, 'includeDescendants': value.include_descendants} for value in value_records if value.category_id]
            if not category_list:
                return False, _("Condition '%(column)s' has no category selected.") % {'column': condition.column_id.name}
            return {input_key: {'relation': relation, 'matchType': match_type, 'values': category_list}}, False

        if shape in ('strings', 'status'):
            value_list = [(value.value or '').strip() for value in value_records if (value.value or '').strip()]
            if shape == 'status':
                value_list = [value.upper() for value in value_list]
            if not value_list:
                return False, _("Condition '%(column)s' has no values.") % {'column': condition.column_id.name}
            return {input_key: {'relation': relation, 'matchType': match_type, 'values': value_list}}, False

        single_value = value_records[:1]
        raw_value = (single_value.value or '').strip() if single_value else ''
        if not raw_value and relation not in ('IS_SET', 'IS_NOT_SET'):
            return False, _("Condition '%(column)s' has no value.") % {'column': condition.column_id.name}
        if relation in ('IS_SET', 'IS_NOT_SET'):
            return {input_key: {'relation': relation}}, False
        try:
            if shape == 'integer':
                return {input_key: {'relation': relation, 'value': int(float(raw_value))}}, False
            if shape == 'money':
                currency = single_value.unit or shop_currency or self.get_shopify_shop_currency()
                return {input_key: {'relation': relation, 'value': {'amount': str(float(raw_value)), 'currencyCode': currency}}}, False
            if shape == 'weight':
                return {input_key: {'relation': relation, 'value': {'value': float(raw_value), 'unit': single_value.unit or 'KILOGRAMS'}}}, False
        except (TypeError, ValueError):
            return False, _("Condition '%(column)s' expects a number but holds '%(value)s'.") % {'column': condition.column_id.name, 'value': raw_value}
        return False, _("Condition '%(column)s' cannot be sent to Shopify yet.") % {'column': condition.column_id.name}

    def prepare_source_input(self, source):
        """
        Task: T8887 - Prepare the include and exclude conditions of one source for Shopify.
        Args:
            source (recordset): The source.
        Returns:
            tuple: The include conditions and the exclude conditions.
        Raises:
            MarketplaceException: If a condition cannot be sent to Shopify.
        """
        self.ensure_one()
        error_list, inclusion_list, exclusion_list = [], [], []
        # Read the store currency once, and only when a price condition actually needs one.
        needs_currency = any(condition.value_ids and not condition.value_ids[0].unit for condition in source.condition_ids
                             if condition.column_id.shopify_name in ('VARIANT_PRICE', 'VARIANT_COMPARE_AT_PRICE'))
        shop_currency = self.get_shopify_shop_currency() if needs_currency else None
        for condition in source.condition_ids:
            condition_input, error = self.prepare_condition_input(condition, shop_currency=shop_currency)
            (error_list if error else inclusion_list).append(error or condition_input)
        for condition in source.exclusion_condition_ids:
            condition_input, error = self.prepare_condition_input(condition, is_exclusion=True, shop_currency=shop_currency)
            (error_list if error else exclusion_list).append(error or condition_input)
        if error_list:
            raise MarketplaceException(_("Collection %(name)s cannot be sent to Shopify:\n- %(errors)s") % {
                'name': self.name, 'errors': "\n- ".join(error_list)})
        return inclusion_list, exclusion_list

    def check_variants_source_is_exportable(self, source):
        """
        Task: T8887 - Check a Variants source before it is sent to Shopify.
            Such a source cannot have exclude rules or excluded products, and every product
            added by hand must name its variants.
        Args:
            source (recordset): The source.
        Raises:
            MarketplaceException: With what to fix.
        """
        self.ensure_one()
        if source.target_type != 'VARIANTS' or source.source_kind != 'conditions':
            return
        problem_list = []
        if source.exclusion_condition_ids:
            problem_list.append(_("Remove its %s exclusion condition(s).", len(source.exclusion_condition_ids)))
        if source.exclusion_listing_ids:
            problem_list.append(_("Remove its manually excluded products: %s", ", ".join(source.exclusion_listing_ids.mapped('name'))))
        picked_listings = self.get_export_selection_listings(source)
        without_variants = picked_listings - source.selection_item_ids.mk_listing_id
        if without_variants:
            problem_list.append(_("Name the variants to include for: %s", ", ".join(without_variants.mapped('name'))))
        if problem_list:
            raise MarketplaceException(_("A source that targets variants cannot be sent to Shopify as it stands, in collection %(name)s:"
                                         "\n- %(problems)s", name=self.name, problems="\n- ".join(problem_list)))

    def prepare_create_source_input(self, source):
        """
        Task: T8887 - Prepare a whole source for Shopify, for a new collection or a new source.
        Args:
            source (recordset): The source.
        Returns:
            dict: The source data, or False when it has nothing to send.
        """
        self.ensure_one()
        if source.source_kind == 'sub_collections':
            collection_gid_list = [f"gid://shopify/Collection/{collection.shopify_collection_id}" for collection in source.sub_collection_ids if collection.shopify_collection_id]
            if not collection_gid_list:
                return False
            return {'subCollections': {'title': default_source_title(source.source_kind, source.target_type), 'collectionIds': collection_gid_list}}
        self.check_variants_source_is_exportable(source)
        inclusion_list, exclusion_list = self.prepare_source_input(source)
        selection_list = self.prepare_selection_input(source)
        if not inclusion_list and not selection_list:
            return False
        # Shopify takes 250 products in one request; the rest are added right after by send_remaining_selections.
        source_vals = {'title': default_source_title(source.source_kind, source.target_type),
                       'targetType': source.target_type or 'PRODUCTS',
                       'inclusion': {'matchType': 'ALL' if source.inclusion_match_type == 'all' else 'ANY',
                                     'conditions': inclusion_list,
                                     'selections': selection_list[:250]}}
        exclusion_selection_list = [{'productId': f"gid://shopify/Product/{listing.mk_id}"} for listing in source.exclusion_listing_ids if listing.mk_id]
        # Shopify takes no exclusion of any kind on a source targeting variants.
        if source.target_type == 'VARIANTS':
            exclusion_list, exclusion_selection_list = [], []
        if exclusion_list or exclusion_selection_list:
            source_vals['exclusion'] = {'matchType': 'ALL' if source.exclusion_match_type == 'all' else 'ANY', 'conditions': exclusion_list,
                                        'selections': exclusion_selection_list[:250]}
        return {'source': source_vals}

    @api.model
    def diff_selections(self, wanted_selection_list, current_selection_block):
        """
        Task: T8887 - Compare the products added by hand in Odoo with the ones on Shopify.
            A product whose chosen variants changed is removed and added again, as Shopify
            cannot change it in place. At most 250 of each are returned; the rest go in the next request.
        Args:
            wanted_selection_list (list): Products as they should be on Shopify.
            current_selection_block (dict): Products as they are on Shopify now.
        Returns:
            tuple: Products to add and products to remove.
        """
        current_variants_by_product = {}
        for node in (current_selection_block.get('nodes', []) if current_selection_block and current_selection_block.get('nodes', []) else []):
            if not isinstance(node, dict):
                continue
            product_gid = node.get('product', {}).get('id') if node.get('product', {}) else False
            if product_gid:
                current_variants_by_product[product_gid] = set(node.get('variantIds', []) if node.get('variantIds', []) else [])

        to_add, to_remove = [], []
        wanted_product_gid_list = []
        for selection in wanted_selection_list:
            product_gid = selection['productId']
            wanted_product_gid_list.append(product_gid)
            if current_variants_by_product.get(product_gid) == set(selection.get('variantIds', [])):
                continue  # already on Shopify, exactly like this
            if product_gid in current_variants_by_product:
                to_remove.append({'productId': product_gid})
            to_add.append(selection)
        to_remove += [{'productId': product_gid} for product_gid in current_variants_by_product if product_gid not in wanted_product_gid_list]
        # A product still waiting to be removed is added again only in a later request.
        waiting_product_gids = {selection['productId'] for selection in to_remove[250:]}
        to_add = [selection for selection in to_add if selection['productId'] not in waiting_product_gids]
        return to_add[:250], to_remove[:250]

    def prepare_selection_input(self, source):
        """
        Task: T8887 - Prepare the products added by hand to a source, with their chosen variants.
        Args:
            source (recordset): The source.
        Returns:
            list: One entry per product.
        """
        self.ensure_one()
        selection_list = []
        for listing in self.get_export_selection_listings(source):
            if not listing.mk_id:
                continue
            selection = {'productId': f"gid://shopify/Product/{listing.mk_id}"}
            picked_items = source.selection_item_ids.filtered(lambda item: item.mk_listing_id == listing)
            if picked_items:
                selection['variantIds'] = [f"gid://shopify/ProductVariant/{item.mk_id}" for item in picked_items if item.mk_id]
            selection_list.append(selection)
        return selection_list

    def get_export_selection_listings(self, source):
        """
        Task: T8887 - Find the products of a source that are sent to Shopify as added by hand.
            Older collections kept these products on the collection itself; those are still
            used while the source has no rules.
        Args:
            source (recordset): The source.
        Returns:
            recordset: The products.
        """
        self.ensure_one()
        if source.source_kind != 'conditions':
            return self.env['mk.listing']
        if source.selection_listing_ids:
            return source.selection_listing_ids
        conditions_sources = self.source_ids.filtered(lambda record: record.source_kind == 'conditions')
        if not source.condition_ids and len(conditions_sources) <= 1:
            return self.mk_listing_ids
        return self.env['mk.listing']

    def prepare_collection_base_vals(self):
        """
        Task: T8887 - Prepare the main details of the collection: title, description, sort order, template and image.
        Returns:
            dict: The collection details.
        """
        self.ensure_one()
        vals = {'title': self.name}
        if self.description:
            vals['descriptionHtml'] = self.description
        if self.template_suffix:
            vals['templateSuffix'] = self.template_suffix
        if self.sort_order:
            vals['sortOrder'] = self.sort_order
        if self.image_url:
            vals['image'] = {'src': self.image_url.split('#')[0]}
        return vals

    @api.model
    def get_or_create_taxonomy_category(self, category_dict):
        """
        Task: T8887 - Find the Odoo category of a Shopify product category, and create it with its parents when missing.
        Args:
            category_dict (dict): Category ID, name and full name from Shopify.
        Returns:
            recordset: The category.
        """
        category_obj = self.env['shopify.product.category.ts']
        shopify_category_id = (category_dict.get('id') or '').split('/')[-1]  # e.g. 'gid://shopify/TaxonomyCategory/ap-1'
        if not shopify_category_id:
            return category_obj
        category = category_obj.search([('shopify_category_id', '=', shopify_category_id)], limit=1)
        if not category:
            category = self.env['mk.listing'].create_shopify_product_category(dict(category_dict, fullName=category_dict.get('fullName') or category_dict.get('name') or ''))
            if category and not category.shopify_category_id:
                category.shopify_category_id = shopify_category_id
        return category

    @api.model
    def get_supported_condition_column(self, condition_dict, kind):
        """
        Task: T8887 - Find the Odoo column of a condition received from Shopify.
            Conditions Odoo cannot send back, such as metafield conditions, get no column and
            are skipped.
        Args:
            condition_dict (dict): One condition as received from Shopify.
            kind (str): 'inclusion' or 'exclusion'.
        Returns:
            tuple: The condition type and the column name, or None when not supported.
        """
        prefix = 'CollectionSourceInclusionCondition' if kind == 'inclusion' else 'CollectionSourceExclusionCondition'
        mapping = CONDITION_TYPENAME_TO_COLUMN if kind == 'inclusion' else EXCLUSION_TYPENAME_TO_COLUMN
        typename = (condition_dict.get('__typename') or '').replace(prefix, '')
        return typename, mapping.get(typename)

    def prepare_source_conditions_vals(self, source_dict):
        """
        Task: T8887 - Prepare the include and exclude conditions of one source received from Shopify.
            Conditions Odoo does not support are skipped and written to the log; they stay as
            they are on Shopify.
        Args:
            source_dict (dict): One source as received from Shopify.
        Returns:
            tuple: Include lines and exclude lines to write on the source.
        """
        inclusion = source_dict.get('inclusion', {}) if source_dict.get('inclusion', {}) else {}
        exclusion = source_dict.get('exclusion', {}) if source_dict.get('exclusion', {}) else {}
        inclusion_vals, exclusion_vals = [], []
        for kind, condition_list, target in (('inclusion', inclusion.get('conditions', []) if inclusion.get('conditions', []) else [], inclusion_vals),
                                             ('exclusion', exclusion.get('conditions', []) if exclusion.get('conditions', []) else [], exclusion_vals)):
            for condition_dict in condition_list:
                typename, column_name = self.get_supported_condition_column(condition_dict, kind)
                value_vals_list = self.prepare_condition_value_vals(condition_dict)
                if not column_name or not value_vals_list:
                    _logger.warning("IMPORT COLLECTION: %s (%s) - %s condition '%s' is not supported yet and was skipped; "
                                    "it stays as it is on Shopify.", self.name, self.shopify_collection_id, kind, typename or 'Unknown')
                    continue
                for value in (condition_dict.get('values', []) if condition_dict.get('values', []) else []):
                    if isinstance(value, dict) and isinstance(value.get('category'), dict):
                        self.get_or_create_taxonomy_category(value['category'])
                target.append((0, 0, {
                    'kind': kind,
                    'column_id': self.get_condition_column(column_name).id,
                    'relation': condition_dict.get('relation') or False,
                    'match_type': 'all' if condition_dict.get('matchType') == 'ALL' else 'any',
                    'condition': ", ".join(str(vals.get('value') or vals.get('category_name') or vals.get('category_id') or '') for vals in value_vals_list),
                    'value_ids': [(0, 0, value_vals) for value_vals in value_vals_list],
                }))
        return inclusion_vals, exclusion_vals

    def import_linked_collections(self, gid_list):
        """
        Task: T8887 - Import the collections a Collections source takes products from, when they are not in Odoo yet.
            A collection that cannot be read is written to the log, and the import goes on.
        Args:
            gid_list (list): Shopify IDs of the missing collections.
        Returns:
            bool: True.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        for gid in gid_list:
            try:
                with self.env.cr.savepoint():
                    variables = {"id": gid}
                    res = mk_instance_id.execute_graphql_query(GET_COLLECTION_WITH_SOURCES, variables)
                    collection_dict = res.get('data', {}).get('collection', {}) if res.get('data', {}) else {}
                    if not collection_dict:
                        _logger.warning("IMPORT COLLECTION: %s (%s) - linked collection %s is not on Shopify any more.", self.name, self.shopify_collection_id, gid)
                        continue
                    collection = self.create_update_collections(collection_dict, mk_instance_id)
                    shopify_product_list = collection.sync_collection_products(collection_dict, mk_instance_id=mk_instance_id)
                    mk_listing_ids = self.env['mk.listing'].search([('mk_id', 'in', shopify_product_list), ('mk_instance_id', '=', mk_instance_id.id)])
                    collection.with_context(skip_collection_job=True).write({'mk_listing_ids': [(6, 0, mk_listing_ids.ids)]})
            except Exception as error:
                _logger.warning("IMPORT COLLECTION: %s (%s) - could not import linked collection %s: %s", self.name, self.shopify_collection_id, gid, error)
        return True

    def get_listings_from_selections(self, selection_block):
        """
        Task: T8887 - Find the Odoo products and variants of the products added by hand on Shopify.
            Only products already in Odoo are found; this does not create new ones.
        Args:
            selection_block (dict): The products added by hand, as received from Shopify.
        Returns:
            tuple: The products and the variants found in Odoo.
        """
        self.ensure_one()
        listing_obj = self.env['mk.listing']
        item_obj = self.env['mk.listing.item']
        product_id_list, variant_id_list = [], []
        for node in (selection_block.get('nodes', []) if selection_block and selection_block.get('nodes', []) else []):
            if not isinstance(node, dict):
                continue
            product_gid = node.get('product', {}).get('id') if node.get('product', {}) else False
            if product_gid:
                product_id_list.append(extract_numeric_id(product_gid))
            variant_id_list += [extract_numeric_id(gid) for gid in (node.get('variantIds', []) if node.get('variantIds', []) else []) if gid]
        picked_listings = listing_obj.search([('mk_id', 'in', product_id_list),
                                              ('mk_instance_id', '=', self.mk_instance_id.id)]) if product_id_list else listing_obj
        picked_variants = item_obj.search([('mk_id', 'in', variant_id_list),
                                           ('mk_instance_id', '=', self.mk_instance_id.id)]) if variant_id_list else item_obj
        return picked_listings, picked_variants

    def update_conditions_from_sources(self, collection_dict):
        """
        Task: T8887 - Update the sources of the collection from Shopify, with their conditions and products added by hand.
            Sources that are no longer on Shopify are removed from Odoo.
        Args:
            collection_dict (dict): Collection data from Shopify.
        Returns:
            bool: True.
        """
        self.ensure_one()
        sources = [source for source in (collection_dict.get('sources', []) if collection_dict.get('sources', []) else []) if isinstance(source, dict)]
        source_obj = self.env['shopify.collection.source.ts']
        seen_source_ids = []

        for index, source_dict in enumerate(sources):
            if source_dict.get('__typename') == 'CollectionSubCollectionsSource':
                linked_collection_gid_list = [collection.get('id') for collection in (source_dict.get('collections', []) if source_dict.get('collections', []) else []) if isinstance(collection, dict) and collection.get('id')]
                linked_collection_id_list = [str(extract_numeric_id(gid)) for gid in linked_collection_gid_list]
                domain = [('shopify_collection_id', 'in', linked_collection_id_list), ('mk_instance_id', '=', self.mk_instance_id.id)]
                linked_collections = self.search(domain) if linked_collection_id_list else self.browse()
                if len(linked_collections) < len(set(linked_collection_id_list)):
                    found_collection_id_list = linked_collections.mapped('shopify_collection_id')
                    self.import_linked_collections([gid for gid, linked_collection_id in zip(linked_collection_gid_list, linked_collection_id_list)
                                                     if linked_collection_id not in found_collection_id_list])
                    linked_collections = self.search(domain)
                vals = {
                    'collection_id': self.id,
                    'sequence': (index + 1) * 10,
                    'source_kind': 'sub_collections',
                    'target_type': 'PRODUCTS',
                    'shopify_source_id': source_dict.get('id'),
                    'sub_collection_ids': [(6, 0, linked_collections.ids)],
                }
                source = source_obj.search([('collection_id', '=', self.id), ('shopify_source_id', '=', source_dict.get('id'))], limit=1)
                source.write(vals) if source else None
                source = source or source_obj.create(vals)
                seen_source_ids.append(source.id)
                continue
            if source_dict.get('__typename') != 'CollectionConditionsSource':
                # A source made by another app cannot be changed from Odoo, so it is only logged and left on Shopify.
                _logger.warning("IMPORT COLLECTION: %s (%s) - skipped source %s owned by another app, which is not supported yet.",
                                self.name, self.shopify_collection_id, source_dict.get('id'))
                continue
            self.fetch_remaining_selections(source_dict)
            inclusion = source_dict.get('inclusion', {}) if source_dict.get('inclusion', {}) else {}
            exclusion = source_dict.get('exclusion', {}) if source_dict.get('exclusion', {}) else {}
            inclusion_vals, exclusion_vals = self.prepare_source_conditions_vals(source_dict)
            listing_ids, selected_item_ids = self.get_listings_from_selections(inclusion.get('selections'))
            excluded_listing_ids, _unused_items = self.get_listings_from_selections(exclusion.get('selections'))

            vals = {
                'collection_id': self.id,
                'sequence': (index + 1) * 10,
                'target_type': source_dict.get('targetType') or 'PRODUCTS',
                'source_kind': 'conditions',
                'shopify_source_id': source_dict.get('id'),
                'inclusion_match_type': 'all' if inclusion.get('matchType') == 'ALL' else 'any',
                'exclusion_match_type': 'all' if exclusion.get('matchType') == 'ALL' else 'any',
                'condition_ids': [(5, 0, 0)] + inclusion_vals,
                'exclusion_condition_ids': [(5, 0, 0)] + exclusion_vals,
                'selection_listing_ids': [(6, 0, listing_ids.ids)],
                'selection_item_ids': [(6, 0, selected_item_ids.ids)],
                'exclusion_listing_ids': [(6, 0, excluded_listing_ids.ids)],
            }
            source = source_obj.search([('collection_id', '=', self.id), ('shopify_source_id', '=', source_dict.get('id'))], limit=1)
            if source:
                source.write(vals)
            else:
                source = source_obj.create(vals)
            seen_source_ids.append(source.id)

        # Sources Shopify no longer has.
        obsolete = source_obj.search([('collection_id', '=', self.id), ('id', 'not in', seen_source_ids)])
        obsolete.sudo().unlink()

        # The collection keeps the match type of its first source, as a new default source starts from it.
        primary = source_obj.browse(seen_source_ids).filtered(lambda source: source.source_kind == 'conditions')[:1]
        self.with_context(skip_collection_job=True).write({'condition_type': primary.inclusion_match_type or 'any'})
        return True


    def update_shopify_collection_conditions(self, collection_dict):
        """
        Task: T8887 - Update the conditions of the collection from Shopify data.
            Reads the sources of the collection; older data without sources is still read.
        Args:
            collection_dict (dict): Collection data from Shopify.
        Returns:
            bool: True when the conditions were updated.
        """
        if collection_dict and collection_dict.get('sources'):
            return self.update_conditions_from_sources(collection_dict)

        condition_dict = collection_dict and collection_dict.get('ruleSet', {})
        condition_column_obj = self.env['shopify.collection.condition.column.ts']

        if condition_dict:
            condition_vals_list = []
            condition_rules = condition_dict.get('rules', [])
            if condition_rules:
                self.sudo().write({'collection_condition_ids': [(2, line_id.id, False) for line_id in self.collection_condition_ids]})
            for condition_dict in condition_rules:
                column = condition_dict.get('column')
                if condition_dict.get('column') == 'IS_PRICE_REDUCED':
                    column = 'VARIANT_COMPARE_AT_PRICE'
                column_id = condition_column_obj.search([('shopify_name', '=', column)])
                if not column_id:
                    column_id = condition_column_obj.create({'name': CONDITION_COLUMN_LABELS.get(column, column), 'shopify_name': column})
                condition_vals_list.append((0, 0, {'shopify_collection_id': self.id,
                                                   'column_id': column_id.id,
                                                   'relation': condition_dict.get('relation'),
                                                   'condition': condition_dict.get('condition')}))
            self.write({'collection_condition_ids': condition_vals_list})
        return True

    def action_publish_unpublish_shopify_collection(self):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
        Opens Shopify product's manage sales channels wizard.
        """
        action = self.env.ref('shopify.action_shopify_product_publications_wizard').sudo().read()[0]
        ctx = self.env.context.copy()
        shopify_sales_channel_ids = self.shopify_sales_channel_ids.ids
        ctx['mk_instance_id'] = self.id
        model = self._name
        active_id = self.id
        ctx.update({
            'active_model': model,
            'active_record_id': active_id
        })
        ctx['default_shopify_sales_channel_ids'] = [(6, 0, shopify_sales_channel_ids)]
        ctx['default_mk_instance_id'] = self.mk_instance_id.id
        action['context'] = ctx
        return action

    def fetch_all_shopify_collection(self, mk_instance_id):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
          This method retrieves all collections from Shopify by executing a paginated GraphQL query. It ensures that all collections are fetched,
          even if the data is spread across multiple pages.
        Args:
            mk_instance_id (recordset): The record of the mk.instance model.
        Returns:
            shopify_collection_list(list): A list of collections fetched from Shopify. Each collection is represented as a dictionary containing
                  collection details.
        Raises:
            MarketplaceException: If the GraphQL query fails or any error occurs while fetching the collections.
       """
        cursor = None
        shopify_collection_list = []

        while True:
            try:
                variables = {"cursor": cursor}
                res = mk_instance_id.execute_graphql_query(GET_IMPORT_COLLECTIONS_WITH_SOURCES, variables)
                user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    self.mk_instance_id.handle_shopify_access_errors(user_errors, "collections")
                collection_list = res.get('data', {}).get('collections', {}) if res.get("data", {}).get("collections", {}) else []
                if not collection_list:
                    break
                shopify_collection_list.extend(collection_list[:len(collection_list) - 1])
                page_info = collection_list[-1].get('pageInfo', {}) if isinstance(collection_list[-1], dict) else {}
                cursor = page_info.get('endCursor', None)
                if not page_info.get('hasNextPage', False) or not cursor:
                    break
            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"Failed to fetch Shopify Collection: {str(e)}")
        return shopify_collection_list

    def get_shopify_sales_channels_collection(self, collection_dict, mk_instance_id=False):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            This method processes Shopify publication(sales channel) data (fetched via GraphQL) and ensures that corresponding 'shopify.sales.channels.ts' records exist in Odoo.
            If a publication(sales channel) does not exist, it is created. Finally, it returns the IDs in the format required for setting Many2Many shopify publication field in collection.
        Task: T7723 - Added instance parameter for instance-wise sales channel fetch.
        Args:
            collection_dict (dict): Dictionary containing Shopify publication(sales channel) data from the GraphQL API response.
            mk_instance_id (recordset, optional): The mk.instance record. Required when self is an empty recordset (e.g. during collection import where the collection record does not exist yet). Falls back to self.mk_instance_id when not provided.
        Returns:
            Dictionary: Returns dictionary which contains 'shopify_sales_channel_ids' to update/set in collection.
        """
        if not collection_dict:
            return False

        shopify_sales_channel_obj = self.env['shopify.sales.channels.ts'].sudo()
        shopify_sales_channel_list = []
        mk_instance_id = mk_instance_id or self.mk_instance_id

        # Extract the list of publication(sales channel) nodes from the GraphQL response
        channels = collection_dict.get('resourcePublications', {}).get('nodes', []) if collection_dict and collection_dict.get('resourcePublications', {}) and collection_dict.get('resourcePublications', {}).get('nodes', []) else []
        for channel in channels:
            sales_channel_id = str(extract_numeric_id(channel.get('publication', {}).get('id', '')))
            # Find an existing channel record in 'shopify.sales.channels.ts' for this instance.
            shopify_sales_channel_id = shopify_sales_channel_obj.search([("sales_channel_id", "=", sales_channel_id), ("mk_instance_id", "=", mk_instance_id.id)], limit=1)
            # Create channel record if not found in 'shopify.sales.channels.ts'.
            if not shopify_sales_channel_id:
                app_data = channel and channel.get('publication', {}) and channel.get('publication', {}).get('channels', {}) and channel.get('publication', {}).get('channels', {}).get('nodes', [])

                # Since app_data is a dictionary, just get 'title' directly
                publication_name = app_data[0].get('name', '') if app_data else ''

                if publication_name:
                    shopify_sales_channel_id = shopify_sales_channel_obj.create({"name": publication_name or '', "sales_channel_id": sales_channel_id, "mk_instance_id": mk_instance_id.id})
            shopify_sales_channel_list.append(shopify_sales_channel_id.id)
        if self.env.context.get("import_collection", False):
            return [(6, 0, shopify_sales_channel_list)]
        else:
            return {'shopify_sales_channel_ids': [(6, 0, shopify_sales_channel_list)]}, shopify_sales_channel_list

    def shopify_check_is_collection_published(self, resource_publications_list):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
        Added - This method will check weather this product is published on "Online Store" or not.
        Args:
            resource_publications_list (list): List of sales channel ids in which the current product is published.
        Returns:
            bool: Returns True if collection(product) is published on online store.
        """
        if not resource_publications_list:
            return False
        channel_id = self.env['shopify.sales.channels.ts'].search([('name', '=', 'Online Store'), ('mk_instance_id', '=', self.mk_instance_id.id)], limit=1)
        if channel_id and channel_id.id in resource_publications_list:
            return True
        else:
            return False

    def create_update_collections(self, collection_dict, mk_instance_id):
        """
        Task: T8887 - Create the collection in Odoo, or update it when it exists, from Shopify data.
        Args:
            collection_dict (dict): Collection data from Shopify.
            mk_instance_id (recordset): The Shopify instance.
        Returns:
            recordset: The collection.
        """
        resource_publications_list = collection_dict and collection_dict.get('resourcePublications', {}) and collection_dict.get('resourcePublications', {}).get('nodes', [])
        # Task: T7723 - Added instance parameter for instance-wise sales channel fetch.
        shopify_sales_channel_ids = self.with_context(import_collection=True).get_shopify_sales_channels_collection(collection_dict, mk_instance_id)
        is_publish = self.shopify_check_is_collection_published(resource_publications_list)
        shopify_collection_id = extract_numeric_id(collection_dict.get('id', ''))
        if collection_dict.get('sources'):
            condition_type = 'any'
        else:
            condition_type = 'any' if collection_dict.get('ruleSet') and collection_dict.get('ruleSet').get('appliedDisjunctively') else 'all'

        vals = {'shopify_collection_id': shopify_collection_id,
                'name': collection_dict.get('title', ''),
                'handle': collection_dict.get('handle', ''),
                'shopify_update_date': convert_shopify_datetime_to_utc(collection_dict.get('updatedAt', '')),
                'sort_order': collection_dict.get('sortOrder', ''),
                'template_suffix': collection_dict.get('templateSuffix', ''),
                'description': collection_dict.get('descriptionHtml', ''),
                'shopify_sales_channel_ids': shopify_sales_channel_ids,
                'is_available_in_website': True if is_publish else False,
                'exported_in_shopify': True,
                'mk_instance_id': mk_instance_id.id,
                'condition_type': condition_type}
        if collection_dict and collection_dict.get("image", False):
            url = collection_dict.get("image", {}).get('url', '')
            if url:
                url = url.replace('\\', '')
                vals.update({'image': base64.b64encode(requests.get(url).content), 'image_url': url})

        odoo_shopify_collection_id = self.search([('shopify_collection_id', '=', shopify_collection_id), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)
        if odoo_shopify_collection_id:
            odoo_shopify_collection_id.write(vals)
        else:
            odoo_shopify_collection_id = self.create(vals)
        odoo_shopify_collection_id.update_shopify_collection_conditions(collection_dict)
        return odoo_shopify_collection_id

    def import_shopify_collections(self, mk_instance_id):
        """
        Task: T8887 - Import all collections of the store from Shopify, with their sources and products.
        Args:
            mk_instance_id (recordset): The Shopify instance.
        Returns:
            dict: Action showing the imported collections, or True when there were none.
        """
        if mk_instance_id.state != 'confirmed':
            error_msg = _("You can import a collection only with a confirm instance./ Please ensure the instance is confirm before import the collection.")
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)
        mk_listing_obj = self.env['mk.listing']
        mk_instance_id.connection_to_shopify()
        collection_list = []
        shopify_collection_list = self.fetch_all_shopify_collection(mk_instance_id)
        for shopify_collection in shopify_collection_list:
            if not isinstance(shopify_collection, dict) or 'id' not in shopify_collection:
                continue
            collection = self.create_update_collections(shopify_collection, mk_instance_id)
            shopify_product_list = self.sync_collection_products(shopify_collection, mk_instance_id=mk_instance_id)
            mk_listing_ids = mk_listing_obj.search([('mk_id', 'in', shopify_product_list), ('mk_instance_id', '=', mk_instance_id.id)])
            collection.with_context(skip_collection_job=True).write({'mk_listing_ids': [(6, 0, mk_listing_ids.ids)]})
            collection_list.append(collection.id)
            self.env.cr.commit()
        if collection_list:
            return mk_instance_id.action_open_model_view(collection_list, 'shopify.collection.ts', 'Shopify Collection')
        return True

    @api.model
    def walk_error_field(self, field, collection_vals):
        """
        Task: T8887 - Find the value a Shopify error points at, in the data that was sent.
        Args:
            field (list): Where the error is, as given by Shopify.
            collection_vals (dict): The data sent to Shopify.
        Returns:
            The value found, or None.
        """
        if not isinstance(field, list) or not field:
            return None
        value = collection_vals if isinstance(collection_vals, dict) else None
        for part in field[1:]:
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, list) and str(part).isdigit() and int(part) < len(value):
                value = value[int(part)]
            else:
                return None
            if value is None:
                return None
        return value

    def describe_error_field(self, field, collection_vals):
        """
        Task: T8887 - Name the product or record a Shopify error is about, so the error is easy to read.
        Args:
            field (list): Where the error is, as given by Shopify.
            collection_vals (dict): The data sent to Shopify.
        Returns:
            str: A readable name for the error.
        """
        if not isinstance(field, list) or not field:
            return ''
        value = self.walk_error_field(field, collection_vals)
        if not isinstance(value, str) or not value.startswith('gid://shopify/'):
            return " > ".join(str(part) for part in field)
        record_id = extract_numeric_id(value)
        model_name = {'Product': 'mk.listing', 'ProductVariant': 'mk.listing.item', 'Collection': 'shopify.collection.ts'}.get(value.split('/')[-2])
        if not model_name:
            return value
        id_field = 'shopify_collection_id' if model_name == 'shopify.collection.ts' else 'mk_id'
        record = self.env[model_name].search([(id_field, '=', record_id), ('mk_instance_id', '=', self.mk_instance_id.id)], limit=1)
        return f"{record.display_name} ({record_id})" if record else value

    def drop_selections_missing_on_shopify(self):
        """
        Task: T8887 - Remove the products and variants added by hand that no longer exist on Shopify, before the collection is sent.
            Shopify refuses a product it no longer has, but keeps a variant it no longer has in the
            selection, so the collection would hold it for good and count it as one of its items.
        Returns:
            bool: True when a product or a variant was removed.
        """
        self.ensure_one()
        listings = self.env['mk.listing'].browse()
        items = self.env['mk.listing.item'].browse()
        for source in self.source_ids:
            listings |= self.get_export_selection_listings(source) | source.exclusion_listing_ids
            items |= source.selection_ids.mk_listing_item_ids
        gid_list = [f"gid://shopify/Product/{listing.mk_id}" for listing in listings if listing.mk_id]
        gid_list += [f"gid://shopify/ProductVariant/{item.mk_id}" for item in items if item.mk_id]
        if not gid_list:
            return False
        alive = set()
        # Shopify checks at most 250 records in one request.
        for batch_gid_list in tools.split_every(250, gid_list, piece_maker=list):
            variables = {"ids": batch_gid_list}
            res = self.mk_instance_id.execute_graphql_query(CHECK_RECORDS_EXIST, variables)
            nodes = res.get('data', {}).get('nodes', []) if res.get('data', {}) else []
            if not isinstance(nodes, list) or len(nodes) != len(batch_gid_list):
                return False
            alive |= {node.get('id') for node in nodes if node}
        dead_items = items.filtered(lambda item: item.mk_id and f"gid://shopify/ProductVariant/{item.mk_id}" not in alive)
        dead_listings = listings.filtered(lambda listing: listing.mk_id and f"gid://shopify/Product/{listing.mk_id}" not in alive)
        return self.drop_dead_variants(dead_items) | self.delete_dead_listings(dead_listings)

    def drop_dead_variants(self, dead_items):
        """
        Task: T8887 - Take the variants Shopify no longer has out of the products added by hand.
            A product left with none of the variants that were chosen for it goes with them, as
            only those variants put it in the collection.
        Args:
            dead_items (recordset): Variants that are no longer on Shopify.
        Returns:
            bool: True when a variant was taken out.
        """
        self.ensure_one()
        if not dead_items:
            return False
        lines = self.source_ids.selection_ids.filtered(lambda line: line.mk_listing_item_ids & dead_items)
        emptied_lines = lines.filtered(lambda line: not (line.mk_listing_item_ids - dead_items))
        dropped = ", ".join(f"{item.display_name} ({item.mk_id})" for item in dead_items)
        _logger.warning("COLLECTION %s (%s): leaving out %s variant(s) Shopify no longer has: %s",
                        self.name, self.shopify_collection_id, len(dead_items), dropped)
        for line in lines - emptied_lines:
            line.mk_listing_item_ids = [(6, 0, (line.mk_listing_item_ids - dead_items).ids)]
        emptied_lines.sudo().unlink()
        return True

    def delete_dead_listings(self, dead_listings):
        """
        Task: T8887 - Delete the listings whose product no longer exists on Shopify, and write them to the log.
        Args:
            dead_listings (recordset): The listings to delete.
        Returns:
            bool: True when a listing was deleted.
        """
        self.ensure_one()
        if not dead_listings:
            return False
        dropped = ", ".join(f"{listing.name} ({listing.mk_id})" for listing in dead_listings)
        _logger.warning("COLLECTION %s (%s): deleting %s listing(s) Shopify no longer has: %s", self.name, self.shopify_collection_id, len(dead_listings), dropped)
        dead_listings.sudo().unlink()
        return True

    def drop_listings_gone_from_shopify(self, user_errors, collection_vals):
        """
        Task: T8887 - Delete the listings Shopify reports as no longer existing, so the collection can be sent again.
        Args:
            user_errors (list): Errors returned by Shopify.
            collection_vals (dict): The data sent to Shopify.
        Returns:
            bool: True when a listing was deleted.
        """
        self.ensure_one()
        listing_obj = self.env['mk.listing']
        dead_listings = listing_obj
        for error in user_errors:
            if error.get('message') != 'Product does not exist':
                continue
            gid = self.walk_error_field(error.get('field'), collection_vals)
            if not isinstance(gid, str) or '/Product/' not in gid:
                continue
            dead_listings |= listing_obj.search([('mk_id', '=', extract_numeric_id(gid)), ('mk_instance_id', '=', self.mk_instance_id.id)])
        return self.delete_dead_listings(dead_listings)

    def error_points_at_self(self, error, collection_vals):
        """
        Task: T8887 - Check whether a Shopify error is about this collection, and not about one it refers to.
            A Collections source names other collections, and Shopify answers "Collection does not
            exist" for those too. Taken as our own, that answer would remove this collection from Odoo.
        Args:
            error (dict): One error returned by Shopify.
            collection_vals (dict): The data sent to Shopify.
        Returns:
            bool: True when the error is about this collection.
        """
        self.ensure_one()
        gid = self.walk_error_field(error.get('field'), collection_vals)
        if not isinstance(gid, str) or '/Collection/' not in gid:
            return True  # it points at nothing else, so it is about this collection
        return str(extract_numeric_id(gid)) == str(self.shopify_collection_id)

    def drop_collections_gone_from_shopify(self, user_errors, collection_vals):
        """
        Task: T8887 - Remove the collections a source pulls from that Shopify no longer has, so the update can be sent again.
            Such a collection is gone from Shopify, so it is removed from Odoo as well, the way a
            collection missing from Shopify is removed when it is read. A Collections source left
            with nothing to pull from goes with it, as Shopify does not take an empty one. The
            collection being sent is never removed for an error about one it only refers to.
        Args:
            user_errors (list): Errors returned by Shopify.
            collection_vals (dict): The data sent to Shopify.
        Returns:
            bool: True when a collection was removed.
        """
        self.ensure_one()
        dead_collections = self.browse()
        for error in user_errors:
            if error.get('message') != 'Collection does not exist' or self.error_points_at_self(error, collection_vals):
                continue
            gid = self.walk_error_field(error.get('field'), collection_vals)
            dead_collections |= self.search([('shopify_collection_id', '=', str(extract_numeric_id(gid))), ('mk_instance_id', '=', self.mk_instance_id.id)])
        if not dead_collections:
            return False
        # A source that pulls from nothing cannot be sent, so it goes with the last collection it held.
        empty_sources = self.source_ids.filtered(lambda source: source.source_kind == 'sub_collections'
                                                 and not (source.sub_collection_ids - dead_collections))
        _logger.warning("COLLECTION %s (%s): deleting %s collection(s) Shopify no longer has, which its sources pulled from: %s",
                        self.name, self.shopify_collection_id, len(dead_collections), ", ".join(dead_collections.mapped('name')))
        dead_collections.sudo().unlink()
        empty_sources.sudo().unlink()
        return True

    def raise_collection_user_errors(self, user_errors, action_label, collection_vals=None):
        """
        Task: T8887 - Show the errors returned by Shopify in a readable message.
            When Shopify says the collection no longer exists, it is removed from Odoo.
        Args:
            user_errors (list): Errors returned by Shopify.
            action_label (str): Name of the action, e.g. export.
            collection_vals (dict): The data sent to Shopify.
        Returns:
            bool: True when there was no error, False when the collection was removed.
        Raises:
            MarketplaceException: With the errors from Shopify.
        """
        self.ensure_one()
        if not user_errors:
            return True
        message_list = []
        for error in user_errors:
            message = error.get('message', '')
            if message == 'Collection does not exist' and self.error_points_at_self(error, collection_vals):
                _logger.error("%s COLLECTION: Removing %s (%s) - it no longer exists on Shopify.", action_label.upper(), self.name, self.shopify_collection_id)
                self.sudo().unlink()
                return False
            subject = self.describe_error_field(error.get('field'), collection_vals)
            if message == 'Product does not exist':
                message = _("this product is no longer on Shopify. Remove it from the source, " "or re-import your listings to clear it.")
            if message == 'Collection does not exist':
                message = _("this collection is no longer on Shopify. Remove it from the Collections source, " "or send it to Shopify first.")
            message_list.append(f"{subject}: {message}" if subject else message)
        raise MarketplaceException(_("Shopify refused to %(action)s collection %(name)s:\n- %(errors)s") % {
            'action': action_label, 'name': self.name, 'errors': "\n- ".join(message_list)})

    def fetch_collection_source_state(self):
        """
        Task: T8887 - Read the sources of the collection as they are on Shopify now.
            The update needs them to know what to add and what to remove. When the collection
            no longer exists on Shopify, it is removed from Odoo.
        Returns:
            dict: Sources by their Shopify ID, or None when the collection is gone.
        """
        self.ensure_one()
        variables = {"id": f"gid://shopify/Collection/{self.shopify_collection_id}"}
        res = self.mk_instance_id.execute_graphql_query(GET_COLLECTION_SOURCE_STATE, variables)
        transport_errors = res.get('errors', []) if isinstance(res, dict) else []
        if transport_errors and isinstance(transport_errors, list):
            self.mk_instance_id.handle_shopify_access_errors(transport_errors, "Collection Source State")
        collection_data = res.get('data', {}).get('collection', {}) if res.get('data', {}) else {}
        if not collection_data:
            _logger.error("UPDATE COLLECTION: Removing %s (%s) - it no longer exists on Shopify.", self.name, self.shopify_collection_id)
            self.sudo().unlink()
            return None
        sources = collection_data.get('sources', []) if collection_data.get('sources', []) else []
        return {source['id']: self.fetch_remaining_selections(source)
                for source in sources if isinstance(source, dict) and source.get('id')}

    def fetch_remaining_selections(self, source_dict):
        """
        Task: T8887 - Get the rest of the products added by hand to a source, as Shopify sends only 250 at a time.
        Args:
            source_dict (dict): A source as received from Shopify; its products are added to it.
        Returns:
            dict: The same source, with all its products added by hand.
        Raises:
            MarketplaceException: If Shopify cannot be reached.
        """
        self.ensure_one()
        query_by_block = {'inclusion': GET_SOURCE_INCLUSION_SELECTIONS_AFTER_CURSOR, 'exclusion': GET_SOURCE_EXCLUSION_SELECTIONS_AFTER_CURSOR}
        for block_name, query in query_by_block.items():
            block = source_dict.get(block_name, {}) if source_dict.get(block_name, {}) else {}
            selection_block = block.get('selections', {}) if block.get('selections', {}) else {}
            page_info = selection_block.get('pageInfo', {}) if selection_block.get('pageInfo', {}) else {}
            while page_info.get('hasNextPage', False) and page_info.get('endCursor', False):
                variables = {"id": source_dict.get('id'), "cursor": page_info.get('endCursor')}
                res = self.mk_instance_id.execute_graphql_query(query, variables)
                transport_errors = res.get('errors', []) if isinstance(res, dict) else []
                if transport_errors and isinstance(transport_errors, list):
                    self.mk_instance_id.handle_shopify_access_errors(transport_errors, "Collection Source Products")
                source_data = res.get('data', {}).get('node', {}) if res.get('data', {}) and res.get('data', {}).get('node', {}) else {}
                next_block = source_data.get(block_name, {}).get('selections', {}) if source_data.get(block_name, {}) else {}
                next_nodes = next_block.get('nodes', []) if next_block.get('nodes', []) else []
                selection_block['nodes'] = (selection_block.get('nodes', []) if selection_block.get('nodes', []) else []) + next_nodes
                page_info = next_block.get('pageInfo', {}) if next_block.get('pageInfo', {}) else {}
        return source_dict

    def ensure_default_source(self):
        """
        Task: T8887 - Give the collection a source when it has none, and move its old conditions and products into it.
        Returns:
            bool: True.
        """
        condition_obj = self.env['shopify.collection.condition.ts']
        for collection in self:
            orphan_conditions = condition_obj.search([('shopify_collection_id', '=', collection.id), ('source_id', '=', False)])
            # A collection that already has its sources keeps them: its products come from those
            # sources, so building another one from them would send the same products once more.
            if collection.source_ids and not orphan_conditions:
                continue
            source = self.env['shopify.collection.source.ts'].create({
                'collection_id': collection.id,
                'target_type': 'PRODUCTS',
                'inclusion_match_type': collection.condition_type or 'any',
            })
            if orphan_conditions:
                orphan_conditions.source_id = source
            elif collection.mk_listing_ids:
                source.selection_listing_ids = [(6, 0, collection.mk_listing_ids.ids)]
        return True

    def link_sources_from_payload(self, collection_data):
        """
        Task: T8887 - Save the Shopify ID of each source that was just created on Shopify.
        Args:
            collection_data (dict): The collection returned by Shopify.
        Returns:
            bool: True.
        """
        self.ensure_one()
        returned = [source.get('id') for source in (collection_data.get('sources', []) if collection_data.get('sources', []) else [])
                    if isinstance(source, dict) and source.get('__typename') == 'CollectionConditionsSource']
        unlinked = self.source_ids.filtered(lambda source: not source.shopify_source_id)
        spare = [gid for gid in returned if gid not in set(self.source_ids.mapped('shopify_source_id'))]
        # The answer holds only the ID and the kind of each source, so a single new source is the
        # only one that can be told apart with certainty; the rest are matched on their target type.
        if len(unlinked) == 1 and len(spare) == 1:
            unlinked.shopify_source_id = spare[0]
        return True

    def link_sources_from_shopify(self):
        """
        Task: T8887 - Ask Shopify for the sources of the collection and save the ID of the ones Odoo is missing.
        Returns:
            bool: True when a source was given its Shopify ID.
        """
        self.ensure_one()
        if not self.source_ids.filtered(lambda source: not source.shopify_source_id) or not self.shopify_collection_id:
            return False
        variables = {"id": f"gid://shopify/Collection/{self.shopify_collection_id}"}
        res = self.mk_instance_id.execute_graphql_query(GET_COLLECTION_SOURCE_STATE, variables)
        collection_data = res.get('data', {}).get('collection', {}) if res.get('data', {}) else {}
        source_list = collection_data.get('sources', []) if collection_data.get('sources', []) else []
        return self.link_sources_from_state({source_dict['id']: source_dict for source_dict in source_list
                                             if isinstance(source_dict, dict) and source_dict.get('id')})

    def link_sources_from_state(self, source_state):
        """
        Task: T8887 - Give a source with no Shopify ID the one of a source Shopify holds but Odoo does not.
            Shopify does not always answer with the source it has just created, and a request that
            fails later rolls the saved ID back. Without this the source counts as new on the next
            update, which is how the same source ends up on Shopify several times.
        Args:
            source_state (dict): Sources by their Shopify ID, as they are on Shopify now.
        Returns:
            bool: True when a source was given its Shopify ID.
        """
        self.ensure_one()
        known_gid_list = set(self.source_ids.mapped('shopify_source_id'))
        spare = [source_dict for gid, source_dict in (source_state or {}).items()
                 if isinstance(source_dict, dict) and gid not in known_gid_list]
        linked = False
        for source in self.source_ids.filtered(lambda source: not source.shopify_source_id):
            source_dict = next((spare_dict for spare_dict in spare if self.source_matches_shopify_source(source, spare_dict)), False)
            if not source_dict:
                continue
            spare.remove(source_dict)
            source.shopify_source_id = source_dict.get('id')
            linked = True
            _logger.info("UPDATE COLLECTION: %s (%s) - took over source %s, which Shopify already held, instead of creating another one.",
                         self.name, self.shopify_collection_id, source_dict.get('id'))
        return linked

    def source_matches_shopify_source(self, source, source_dict):
        """
        Task: T8887 - Check whether a source on Shopify is the one a source in Odoo stands for.
        Args:
            source (recordset): The source in Odoo.
            source_dict (dict): A source as received from Shopify.
        Returns:
            bool: True when both hold the same kind of rule, on the same products or variants.
        """
        if source.source_kind == 'sub_collections':
            return source_dict.get('__typename') == 'CollectionSubCollectionsSource'
        return (source_dict.get('__typename') == 'CollectionConditionsSource'
                and (source_dict.get('targetType') or source.target_type) == source.target_type)


    def prepare_collection_vals(self):
        """
        Task: T8887 - Prepare the data to create the collection on Shopify, with all its sources.
        Returns:
            dict: The collection data.
        Raises:
            MarketplaceException: If a condition cannot be sent to Shopify.
        """
        self.ensure_one()
        collection_vals = self.prepare_collection_base_vals()
        source_input_list = [vals for vals in (self.prepare_create_source_input(source) for source in self.source_ids) if vals]
        if source_input_list:
            collection_vals['sources'] = source_input_list
        return collection_vals

    def update_odoo_collection(self, result):
        """
        Task: T8887 - Save in Odoo what Shopify returned after the collection was created or updated.
            Saves the handle, image, sales channels, update date and the Shopify ID of new sources.
        Args:
            result (dict): The response from Shopify.
        Returns:
            bool: True when saved, False when Shopify returned no collection.
        """
        self.ensure_one()
        response_data = result.get('data', {}) if isinstance(result, dict) and result.get('data', {}) else {}
        mutation_result = response_data.get('collectionCreate', {}) or response_data.get('collectionUpdate', {})
        collection_data = mutation_result.get('collection', {}) if mutation_result else {}
        if not collection_data:
            return False

        self.link_sources_from_payload(collection_data)
        # Shopify sometimes answers without the source it has just created, so it is looked up
        # before the next update goes out and sends the same source as a new one.
        self.link_sources_from_shopify()
        vals = {
            'handle': collection_data.get('handle', False),
            'exported_in_shopify': True,
            'shopify_collection_id': extract_numeric_id(collection_data.get('id')),
            'shopify_update_date': convert_shopify_datetime_to_utc(collection_data.get('updatedAt')),
        }
        image = collection_data.get('image', {}).get('url') if collection_data.get('image', {}) else False
        if image:
            vals['image_url'] = image
        if collection_data.get('resourcePublications', {}) and collection_data.get('resourcePublications', {}).get('nodes', []):
            shopify_sales_channel_ids, shopify_sales_channel_ids_list = self.get_shopify_sales_channels_collection(collection_data)
            if shopify_sales_channel_ids:
                vals.update(shopify_sales_channel_ids)
            vals['is_available_in_website'] = self.shopify_check_is_collection_published(shopify_sales_channel_ids_list)
        self.with_context(skip_collection_job=True).write(vals)
        return True

    def sales_channel_ids_fetch(self, mk_instance_id, operation_wizard):
        """
         Task: T7628 - Added logic to remove missing Shopify Sales Channels from Odoo when they no longer exist in Shopify during sales channel updates.
         Task: T5963 - Migrate Shopify REST API to Graphql API
            This method processes the sales channel data within the wizard, fetching and writing the sales channels associated with a collection to either publish or unpublish it.
         Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            operation_wizard: The wizard object that provides the sales channels and other related data for publishing or unpublishing the collection.
        """
        collection_id = ''
        export_collection = self.env.context.get("export_collection", False)
        update_collection = self.env.context.get("update_collection", False)

        if export_collection:
            collection_data = self.env.context.get("collection_id") if self.env.context.get("collection_id", False) else {}
            collection_id = extract_numeric_id(collection_data)
        elif update_collection:
            collection_id = self.shopify_collection_id

        sales_channels_ids = operation_wizard.shopify_sales_channel_ids.mapped('sales_channel_id')
        input_list = [{"publicationId": f"gid://shopify/Publication/{sales_channel_id}"} for sales_channel_id in sales_channels_ids]

        is_publishing = operation_wizard.is_publish_or_unpublish
        query = PUBLISH_COLLECTION if is_publishing else UNPUBLISH_COLLECTION
        publish_unpublish_key = "Publish" if is_publishing else "Unpublish"

        variables = {"id": f"gid://shopify/Collection/{collection_id}", "publications": input_list}
        res = mk_instance_id.execute_graphql_query(query, variables)
        publish_error = res and res.get("data", {}) and res.get("data", {}).get('publishablePublish', {})
        if publish_error:
            user_error = publish_error and publish_error.get('userErrors', [])
        else:
            user_error = res and res.get("data", {}) and res.get("data", {}).get('publishableUnpublish', {}) and res.get("data", {}).get('publishableUnpublish', {}).get('userErrors', [])
        update_sales_channel_response_key = 'publishablePublish' if is_publishing else 'publishableUnpublish'
        user_errors = res.get("data", {}).get(update_sales_channel_response_key, {}).get("userErrors", []) if res and res.get("data", {}).get(update_sales_channel_response_key, {}) else []

        if user_errors or user_error:
            for err in user_errors or user_error:
                message = err.get("message")
                log_message = f"EXPORT/UPDATE COLLECTION: Failed to {publish_unpublish_key} Collection ({collection_id}): {message}"
                _logger.warning(log_message)

        if not user_errors and is_publishing:
            response_dict = res.get('data', {}).get('publishablePublish', {}).get('publishable', {}) if res and isinstance(res, dict) else {}
        else:
            response_dict = res.get('data', {}).get('publishableUnpublish', {}).get('publishable', {}) if res and isinstance(res, dict) else {}

        updated_at = convert_shopify_datetime_to_utc(response_dict.get('updatedAt', ""))
        shopify_sales_channel_ids, shopify_sales_channel_ids_list = self.get_shopify_sales_channels_collection(response_dict)
        collection_vals = {'shopify_update_date': updated_at}

        shopify_sales_channel_ids and collection_vals.update(shopify_sales_channel_ids)

        is_published = self.shopify_check_is_collection_published(shopify_sales_channel_ids_list)
        collection_vals.update({'is_available_in_website': is_published})

        # Update the Collection with updated values
        self.write(collection_vals)
        _logger.info(f'EXPORT/UPDATE Collection: Collection {self.name}({collection_id}) has been {publish_unpublish_key} successfully')
        return True

    def get_conditions_to_delete(self, current_block, kind):
        """
        Task: T8887 - List the Shopify conditions to replace; the ones Odoo does not support are kept.
        Args:
            current_block (dict): Include or exclude conditions as they are on Shopify.
            kind (str): 'inclusion' or 'exclusion'.
        Returns:
            list: IDs of the conditions to delete.
        """
        conditions = current_block.get('conditions', []) if current_block.get('conditions', []) else []
        return [condition.get('id') for condition in conditions if condition.get('id') and self.get_supported_condition_column(condition, kind)[1]]

    def prepare_update_collection_vals(self, source_state=None):
        """
        Task: T8887 - Prepare the changes to send to Shopify to update the collection.
            Only what changed is sent for each source. Conditions Odoo does not support, and
            sources or linked collections Odoo does not have, stay as they are on Shopify.
        Args:
            source_state (dict): The sources as they are on Shopify now.
        Returns:
            dict: The changes to send.
        Raises:
            MarketplaceException: If a condition cannot be sent to Shopify.
        """
        self.ensure_one()
        collection_vals = self.prepare_collection_base_vals()
        collection_vals['id'] = f"gid://shopify/Collection/{self.shopify_collection_id}"
        source_state = source_state or {}
        to_create, to_update = [], []

        for source in self.source_ids:
            shopify_source = source_state.get(source.shopify_source_id)
            if not source.shopify_source_id or shopify_source is None:
                # Not on Shopify yet - or gone from it, in which case it is recreated.
                source_input = self.prepare_create_source_input(source)
                if source_input:
                    to_create.append(source_input)
                continue

            if source.source_kind == 'sub_collections':
                collection_gid_list = [f"gid://shopify/Collection/{collection.shopify_collection_id}" for collection in source.sub_collection_ids if collection.shopify_collection_id]
                current_gid_list = [collection.get('id') for collection in (shopify_source.get('collections', []) if shopify_source.get('collections', []) else [])
                                    if isinstance(collection, dict) and collection.get('id')]
                odoo_collection_id_list = self.search([('mk_instance_id', '=', self.mk_instance_id.id), ('shopify_collection_id', 'in', [str(extract_numeric_id(gid)) for gid in current_gid_list])
                                             ]).mapped('shopify_collection_id') if current_gid_list else []
                collection_gid_list += [gid for gid in current_gid_list if str(extract_numeric_id(gid)) not in odoo_collection_id_list and gid not in collection_gid_list]
                to_update.append({'subCollections': {'id': source.shopify_source_id, 'collectionIds': collection_gid_list}})
                continue

            current_target_type = shopify_source.get('targetType')
            if current_target_type and source.target_type != current_target_type:
                raise MarketplaceException(_("The source of collection %(name)s matches %(current)s on Shopify and cannot be changed "
                                             "to %(wanted)s. Delete the source and add a new one of that type instead.", name=self.name,
                                             current=current_target_type.title(), wanted=(source.target_type or '').title()))

            self.check_variants_source_is_exportable(source)
            inclusion_list, exclusion_list = self.prepare_source_input(source)
            if source.target_type == 'VARIANTS':
                exclusion_list = []  # not supported there, and Shopify refuses the whole write
            current_inclusion = shopify_source.get('inclusion', {}) if shopify_source.get('inclusion', {}) else {}
            current_exclusion = shopify_source.get('exclusion', {}) if shopify_source.get('exclusion', {}) else {}
            inclusion_changes, exclusion_changes = self.prepare_selection_changes(source, shopify_source)
            to_update.append({'condition': {
                'id': source.shopify_source_id,
                'inclusion': {
                    'matchType': 'ALL' if source.inclusion_match_type == 'all' else 'ANY',
                    'conditionsToDelete': self.get_conditions_to_delete(current_inclusion, 'inclusion'),
                    'conditionsToCreate': inclusion_list,
                    **inclusion_changes,
                },
                'exclusion': {
                    'matchType': 'ALL' if source.exclusion_match_type == 'all' else 'ANY',
                    'conditionsToDelete': self.get_conditions_to_delete(current_exclusion, 'exclusion'),
                    'conditionsToCreate': exclusion_list,
                    **exclusion_changes,
                },
            }})

        known_gid_list = set(self.source_ids.mapped('shopify_source_id'))
        unknown_source_gids = [gid for gid in source_state if gid not in known_gid_list]
        if unknown_source_gids:
            _logger.warning("UPDATE COLLECTION: %s (%s) - leaving %s source(s) on Shopify that Odoo does not hold: %s",
                            self.name, self.shopify_collection_id, len(unknown_source_gids), ", ".join(unknown_source_gids))
        if to_create:
            collection_vals['sourcesToCreate'] = to_create
        if to_update:
            collection_vals['sourcesToUpdate'] = to_update
        return collection_vals

    def send_collection_update(self, source_state):
        """
        Task: T8887 - Send the update of the collection to Shopify.
            When Shopify reports products that no longer exist, they are deleted and the update
            is sent once more.
        Args:
            source_state (dict): The sources as they are on Shopify now.
        Returns:
            tuple: The response from Shopify (None when the collection no longer exists) and the data sent.
        Raises:
            MarketplaceException: If Shopify refuses the update.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        for is_retry in (False, True):
            collection_vals = self.prepare_update_collection_vals(source_state)
            try:
                variables = {"collection": collection_vals}
                res = mk_instance_id.execute_graphql_query(UPDATE_COLLECTION_WITH_SOURCES, variables)
            except MarketplaceException:
                raise
            except Exception as error:
                raise MarketplaceException(_("Error while trying to update collection %(name)s: %(error)s", name=self.name, error=error))
            transport_errors = res.get('errors', []) if isinstance(res, dict) else []
            if transport_errors and isinstance(transport_errors, list):
                mk_instance_id.handle_shopify_access_errors(transport_errors, "Update Collection")
            update_result = res.get('data', {}).get('collectionUpdate', {}) if res.get('data', {}).get('collectionUpdate', {}) else {}
            user_errors = update_result.get('userErrors', []) if update_result.get('userErrors', []) else []
            if not is_retry and (self.drop_listings_gone_from_shopify(user_errors, collection_vals)
                                 | self.drop_collections_gone_from_shopify(user_errors, collection_vals)):
                continue  # what Shopify no longer has is out of the way, so the same update can go through now
            if not self.raise_collection_user_errors(user_errors, _("update"), collection_vals):
                return None, collection_vals
            return res, collection_vals

    def prepare_selection_changes(self, source, shopify_source):
        """
        Task: T8887 - Find the products added by hand and kept out by hand that must be added or removed on Shopify.
        Args:
            source (recordset): The source.
            shopify_source (dict): The same source as it is on Shopify now.
        Returns:
            tuple: The changes for the included products and the changes for the excluded products.
        """
        self.ensure_one()
        current_inclusion = shopify_source.get('inclusion', {}) if shopify_source.get('inclusion', {}) else {}
        current_exclusion = shopify_source.get('exclusion', {}) if shopify_source.get('exclusion', {}) else {}
        wanted_selection_list = self.prepare_selection_input(source)
        selections_to_add, selections_to_remove = self.diff_selections(wanted_selection_list, current_inclusion.get('selections'))
        wanted_excluded_selection_list = [] if source.target_type == 'VARIANTS' else [
            {'productId': f"gid://shopify/Product/{listing.mk_id}"} for listing in source.exclusion_listing_ids if listing.mk_id]
        exclusions_to_add, exclusions_to_remove = self.diff_selections(wanted_excluded_selection_list, current_exclusion.get('selections'))
        return ({'selectionsToAdd': selections_to_add, 'selectionsToRemove': selections_to_remove},
                {'selectionsToAdd': exclusions_to_add, 'selectionsToRemove': exclusions_to_remove})

    @api.model
    def has_full_selection_list(self, collection_vals):
        """
        Task: T8887 - Tell whether a list of products sent to Shopify was full, so more products may still be waiting.
        Args:
            collection_vals (dict): The data sent to Shopify.
        Returns:
            bool: True when a list held as many products as Shopify takes.
        """
        new_sources = collection_vals.get('sources', []) + collection_vals.get('sourcesToCreate', [])
        source_vals_list = [source.get('source', {}) for source in new_sources]
        source_vals_list += [source.get('condition', {}) for source in collection_vals.get('sourcesToUpdate', [])]
        blocks = [source_vals.get(block_name, {}) for source_vals in source_vals_list for block_name in ('inclusion', 'exclusion')]
        return any(len(block.get(list_name, [])) >= 250
                   for block in blocks for list_name in ('selections', 'selectionsToAdd', 'selectionsToRemove'))

    def prepare_remaining_selection_updates(self, source_state):
        """
        Task: T8887 - Prepare the next products to add or remove on Shopify for each source, leaving its conditions as they are.
        Args:
            source_state (dict): The sources as they are on Shopify now.
        Returns:
            list: The source changes to send; empty when Shopify already has every product.
        """
        self.ensure_one()
        sources_to_update = []
        # A Collections source has no products added by hand, so it gives no change.
        for source in self.source_ids.filtered(lambda source: source.shopify_source_id in source_state):
            inclusion_changes, exclusion_changes = self.prepare_selection_changes(source, source_state[source.shopify_source_id])
            source_vals = {'id': source.shopify_source_id}
            if any(inclusion_changes.values()):
                source_vals['inclusion'] = inclusion_changes
            if any(exclusion_changes.values()):
                source_vals['exclusion'] = exclusion_changes
            if len(source_vals) > 1:
                sources_to_update.append({'condition': source_vals})
        return sources_to_update

    def send_remaining_selections(self, collection_vals):
        """
        Task: T8887 - Send the products that did not fit in the last request, 250 at a time.
            Each time the sources are read from Shopify again, and the next missing products are sent.
        Args:
            collection_vals (dict): The data last sent to Shopify.
        Returns:
            dict: The last response from Shopify, or None when nothing more was sent.
        Raises:
            MarketplaceException: If Shopify refuses a request.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        res = None
        while self.has_full_selection_list(collection_vals):
            source_state = self.fetch_collection_source_state()
            if source_state is None:
                return None  # the collection no longer exists on Shopify and was removed locally
            sources_to_update = self.prepare_remaining_selection_updates(source_state)
            next_collection_vals = {'id': f"gid://shopify/Collection/{self.shopify_collection_id}", 'sourcesToUpdate': sources_to_update}
            if not sources_to_update or next_collection_vals == collection_vals:
                break  # nothing left, or Shopify did not take the last products, so they are not sent again
            collection_vals = next_collection_vals
            variables = {"collection": collection_vals}
            res = mk_instance_id.execute_graphql_query(UPDATE_COLLECTION_WITH_SOURCES, variables)
            transport_errors = res.get('errors', []) if isinstance(res, dict) else []
            if transport_errors and isinstance(transport_errors, list):
                mk_instance_id.handle_shopify_access_errors(transport_errors, "Update Collection")
            update_result = res.get('data', {}).get('collectionUpdate', {}) if res.get('data', {}).get('collectionUpdate', {}) else {}
            user_errors = update_result.get('userErrors', []) if update_result.get('userErrors', []) else []
            if not self.raise_collection_user_errors(user_errors, _("update"), collection_vals):
                return None
        return res

    def check_collection_job_status(self, job_id, product_batch):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
            This method checks the job status for the collection and writes job-related information to the collection if the collection ID exists.
        Args:
            job_id (str): The ID of the job associated with the collection.
            product_batch (str): Marketplace ids of the products the job is recomputing.
       """
        collection_id = self.shopify_collection_id
        if not collection_id:
            raise MarketplaceException(_("Collection ID is missing"))
        if collection_id:
            self.write({'collection_job_ids': [(0, 0, {
                'job_id': job_id,
                'response_data': product_batch,
            })]})

    def process_shopify_collection_job(self):
        """
        Task: T5963 - Migrate Shopify REST API to Graphql API
        This method process for cron every 15 min. If remove product time fail so every 15 min run cron if job status true so remove job_id.
        """
        collections = self.env['shopify.collection.ts'].search([('collection_job_ids', '!=', False)])
        for collection in collections:
            try:
                mk_instance_id = collection.mk_instance_id
                mk_instance_id.connection_to_shopify()
                collection_job_ids = collection.collection_job_ids
                job_finished = False
                for collection_job_id in collection_job_ids:
                    job_id = collection_job_id.job_id
                    variables = {"jobId": job_id}
                    res = mk_instance_id.execute_graphql_query(JOB_STATUS, variables)
                    user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                    if user_errors and isinstance(user_errors, list):
                        err_messages = [e.get('message', str(e)) for e in user_errors]
                        joined_errors = ", ".join(err_messages)
                        logging.error(joined_errors)
                        continue
                    response = res.get('data', {}) and res.get('data', {}).get('job', {}) and res.get('data', {}).get('job', {}).get('done') if res and res.get('data', {}).get('job', {}) else []
                    if response:
                        collection_job_id.sudo().unlink()
                        job_finished = True
                # The job is done, so refresh the Products count, once per collection.
                if job_finished:
                    collection.refresh_listings_from_shopify()
            except Exception as e:
                _logger.error(f"Error while processing collection {collection.name} job status: {e}")
        return True

    def refresh_listings_from_shopify(self, keep_on_empty=False):
        """
        Task: T8887 - Get the products Shopify now holds in this collection, so the Products count is right.
            It runs after Shopify has accepted the change, so an error here is only written to the log.
        Args:
            keep_on_empty (bool): Keep the current products when Shopify returns none.
        Returns:
            bool: True when the products were refreshed.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        if not self.shopify_collection_id:
            return False
        try:
            with self.env.cr.savepoint():
                variables = {"id": f"gid://shopify/Collection/{self.shopify_collection_id}"}
                res = mk_instance_id.execute_graphql_query(GET_COLLECTION_WITH_SOURCES, variables)
                collection_dict = res.get('data', {}).get('collection', {}) if res.get('data', {}) else {}
                if not collection_dict:
                    return False
                shopify_product_list = self.sync_collection_products(collection_dict, mk_instance_id=mk_instance_id)
                if not shopify_product_list and keep_on_empty:
                    return False
                mk_listing_ids = self.env['mk.listing'].search([('mk_id', 'in', shopify_product_list),
                                                                ('mk_instance_id', '=', mk_instance_id.id)])
                self.with_context(skip_collection_job=True).write({'mk_listing_ids': [(6, 0, mk_listing_ids.ids)]})
        except Exception as error:
            _logger.warning("COLLECTION %s (%s): could not refresh its products from Shopify - %s", self.name, self.shopify_collection_id, error)
            return False
        return True

    def export_linked_collections(self):
        """
        Task: T8887 - Create on Shopify the collections a Collections source takes products from, when they exist only in Odoo.
            A collection that cannot be created is written to the log and left out.
        Returns:
            bool: True.
        """
        self.ensure_one()
        exporting_collection_ids = set(self.env.context.get('exporting_collection_ids', ())) | {self.id}
        linked_collections = self.source_ids.filtered(lambda source: source.source_kind == 'sub_collections').sub_collection_ids
        operation_wizard = SimpleNamespace(shopify_sales_channel_ids=False, is_publish_or_unpublish=False)
        for linked_collection in linked_collections:
            if linked_collection.shopify_collection_id:
                continue
            if linked_collection.id in exporting_collection_ids:
                _logger.warning("EXPORT COLLECTION: %s - linked collection %s is being created in this same run; "
                                "it will be linked on the next sync.", self.name, linked_collection.name)
                continue
            try:
                with self.env.cr.savepoint():
                    linked_collection.with_context(exporting_collection_ids=tuple(exporting_collection_ids)).export_collection_to_shopify_ts(operation_wizard)
            except Exception as error:
                _logger.warning("EXPORT COLLECTION: %s - could not create linked collection %s on Shopify, " "so it was left out: %s", self.name, linked_collection.name, error)
        return True

    def export_collection_to_shopify_ts(self, operation_wizard):
        """
        Task: T8887 - Create the collection on Shopify with all its sources.
        Args:
            operation_wizard (object): The operation wizard, with the sales channels to publish to.
        Returns:
            bool: True.
        Raises:
            MarketplaceException: If the instance is not confirmed, the collection has nothing to send or Shopify refuses it.
        """
        if self.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("You can export a collection only with a confirm instance./ Please ensure the instance is confirm before export the collection."))
        for collection in self:
            mk_instance_id = collection.mk_instance_id
            mk_instance_id.connection_to_shopify()
            collection.export_linked_collections()
            collection.ensure_default_source()
            collection.drop_selections_missing_on_shopify()
            if not any(collection.prepare_create_source_input(source) for source in collection.source_ids):
                raise MarketplaceException(_("Collection %(name)s has nothing to send: add a condition, "
                                             "a product or a collection to one of its sources.") % {'name': collection.name})
            for is_retry in (False, True):
                collection_vals = collection.prepare_collection_vals()
                try:
                    variables = {"collection": collection_vals}
                    res = mk_instance_id.execute_graphql_query(EXPORT_COLLECTION_WITH_SOURCES, variables)
                except MarketplaceException:
                    raise
                except Exception as error:
                    raise MarketplaceException(_("Error while trying to export collection %(name)s: %(error)s") % {'name': collection.name, 'error': error})

                transport_errors = res.get('errors', []) if isinstance(res, dict) else []
                if transport_errors and isinstance(transport_errors, list):
                    mk_instance_id.handle_shopify_access_errors(transport_errors, "Export Collection")
                create_result = res.get('data', {}).get('collectionCreate', {}) if res.get('data', {}).get('collectionCreate', {}) else {}
                user_errors = create_result.get('userErrors', []) if create_result.get('userErrors', []) else []
                if not is_retry and (collection.drop_listings_gone_from_shopify(user_errors, collection_vals)
                                     | collection.drop_collections_gone_from_shopify(user_errors, collection_vals)):
                    continue  # what Shopify no longer has is out of the way, so the same export can go through now
                collection.raise_collection_user_errors(user_errors, _("export"), collection_vals)
                break

            collection.with_context(export_collection=True).update_odoo_collection(res)
            collection.send_remaining_selections(collection_vals)
            # A new collection may still be counting its products, so an empty answer keeps the current ones.
            collection.refresh_listings_from_shopify(keep_on_empty=True)
            if operation_wizard and operation_wizard.shopify_sales_channel_ids:
                collection_gid = create_result.get('collection', {}).get('id') if create_result.get('collection', {}) else False
                collection.with_context(export_collection=True, collection_id=collection_gid).sales_channel_ids_fetch(mk_instance_id, operation_wizard)
        return True

    def update_collection_to_shopify_ts(self, operation_wizard):
        """
        Task: T8887 - Update the collection on Shopify with the changes made in Odoo.
        Args:
            operation_wizard (object): The operation wizard, with the sales channels to publish to.
        Returns:
            bool: True.
        Raises:
            MarketplaceException: If the instance is not confirmed, a source is empty or Shopify refuses the update.
        """
        if self.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("You can update a collection only with a confirm instance./ Please ensure the instance is confirm before updating the collection."))
        for collection in self:
            if not collection.exists():
                continue
            mk_instance_id = collection.mk_instance_id
            mk_instance_id.connection_to_shopify()
            collection.export_linked_collections()
            collection.ensure_default_source()
            empty_sources = collection.source_ids.filtered(lambda source: source.source_kind == 'conditions' and not source.condition_ids
                                                           and not collection.get_export_selection_listings(source))
            if empty_sources and empty_sources.filtered('shopify_source_id'):
                raise MarketplaceException(_("Collection %(name)s has a source with neither conditions nor products. "
                                             "Fill it in or remove it before updating Shopify.") % {'name': collection.name})

            collection.drop_selections_missing_on_shopify()
            source_state = collection.fetch_collection_source_state()
            if source_state is None:
                continue
            collection.link_sources_from_state(source_state)

            res, collection_vals = collection.send_collection_update(source_state)
            if res is None:
                continue
            # Saves the Shopify ID of new sources first, as the products that did not fit are sent to them.
            collection.with_context(update_collection=True).update_odoo_collection(res)
            res = collection.send_remaining_selections(collection_vals) or res
            if not collection.exists():
                continue
            update_result = res.get('data', {}).get('collectionUpdate', {}) if res.get('data', {}).get('collectionUpdate', {}) else {}

            job = update_result.get('job', {}) if update_result.get('job', {}) else {}
            if job.get('id') and not job.get('done'):
                collection.check_collection_job_status(
                    job['id'], ", ".join(mk_id for mk_id in collection.source_ids.selection_listing_ids.mapped('mk_id') if mk_id))
            else:
                collection.refresh_listings_from_shopify()
            if operation_wizard and operation_wizard.shopify_sales_channel_ids:
                collection.with_context(update_collection=True).sales_channel_ids_fetch(mk_instance_id, operation_wizard)
        return True

    def action_sync_collection_to_odoo(self):
        """
        Task: T8887 - Get this collection from Shopify again: details, sales channels, sources and products.
        Returns:
            bool: True.
        Raises:
            MarketplaceException: If the collection is not on Shopify yet.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        if mk_instance_id.state != 'confirmed':
            error_msg = _("You can sync a collection only with a confirmed instance. Please ensure the instance is confirmed before syncing the collection.")
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)
        if not self.shopify_collection_id:
            raise MarketplaceException(_("Collection %(name)s is not on Shopify yet. Export it first.") % {'name': self.name})
        mk_instance_id.connection_to_shopify()

        variables = {"id": f"gid://shopify/Collection/{self.shopify_collection_id}"}
        res = mk_instance_id.execute_graphql_query(GET_COLLECTION_WITH_SOURCES, variables)
        transport_errors = res.get('errors', []) if isinstance(res, dict) else []
        if transport_errors and isinstance(transport_errors, list):
            mk_instance_id.handle_shopify_access_errors(transport_errors, "Sync Collection")
        collection_dict = res.get('data', {}).get('collection', {}) if res.get('data', {}) else {}
        if not collection_dict:
            _logger.error("SYNC COLLECTION: Removing %s (%s) - it no longer exists on Shopify.", self.name, self.shopify_collection_id)
            self.sudo().unlink()
            return True

        self.create_update_collections(collection_dict, mk_instance_id)
        shopify_product_list = self.sync_collection_products(collection_dict, mk_instance_id=mk_instance_id)
        mk_listing_ids = self.env['mk.listing'].search([('mk_id', 'in', shopify_product_list), ('mk_instance_id', '=', mk_instance_id.id)])
        self.with_context(skip_collection_job=True).write({'mk_listing_ids': [(6, 0, mk_listing_ids.ids)]})
        self.notify_sync_done(_("The collection has been updated with the latest data from Shopify."))
        return True

    def action_sync_collection_to_shopify(self):
        """
        Task: T8887 - Send this collection to Shopify: create it when new, update it otherwise.
            Sales channels are not changed.
        Returns:
            bool: True.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        if mk_instance_id.state != 'confirmed':
            error_msg = _("You can sync a collection only with a confirmed instance. Please ensure the instance is confirmed before syncing the collection.")
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)
        operation_wizard = SimpleNamespace(shopify_sales_channel_ids=False, is_publish_or_unpublish=False)
        if self.exported_in_shopify and self.shopify_collection_id:
            self.update_collection_to_shopify_ts(operation_wizard)
            message = _("The collection has been synced to Shopify with the latest data from Odoo.")
        else:
            self.export_collection_to_shopify_ts(operation_wizard)
            message = _("The collection has been created on Shopify.")
        self.notify_sync_done(message)
        return True

    def notify_sync_done(self, message):
        """
        Task: T8887 - Show a message on the form after a sync.
        Args:
            message (str): The message to show.
        Returns:
            bool: True.
        """
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'marketplace_notification',
            {'title': _('Sync Completed'), 'message': message, 'message_is_html': False,
             'type': 'info', 'sticky': False},
        )
        return True

    def open_collection_in_shopify(self):
        self.ensure_one()
        marketplace_url = self.mk_instance_id.shop_url + '/admin/collections/' + self.shopify_collection_id
        client_action = {
            'type': 'ir.actions.act_url',
            'name': "Marketplace URL",
            'target': 'new',
            'url': marketplace_url,
        }
        return client_action


class MkListing(models.Model):
    _inherit = "mk.listing"

    collection_image_256 = fields.Image(compute='_compute_collection_image_256', string="Collection Item Image",
                                       help="Listing image shown on the collection's item cards.")
    collection_variant_summary = fields.Char(compute='_compute_collection_variant_summary', string="Variants in Collection", help="How many of this product's variants the collection holds.")

    @api.depends('image_ids.image', 'image_ids.sequence')
    def _compute_collection_image_256(self):
        """
        Task: T8887 - The picture of a Collection Items card: the first image of the listing, as
            Shopify shows it. The ORM only resizes an image field on write, so a computed one is
            resized here; otherwise the card would load the full-size original of every product.
        """
        for listing in self:
            image = listing.image_ids[:1].image
            if not image:
                listing.collection_image_256 = False
                continue
            try:
                # image_process works on the raw bytes, while the field holds them base64 encoded.
                listing.collection_image_256 = base64.b64encode(
                    image_process(base64.b64decode(image), size=(256, 256)) or b'') or False
            except (UserError, ValueError, binascii.Error):
                # A listing image that is not a picture Odoo can read leaves the card without one.
                listing.collection_image_256 = False

    def get_collection_card_context(self):
        """
        Task: T8887 - Find the collection a Collection Items card belongs to.
        Returns:
            recordset: The collection, or empty when it is not known.
        """
        return self.env['shopify.collection.ts'].browse(self.env.context.get('collection_id') or []).exists()

    def get_collection_item_variants(self):
        """
        Task: T8887 - List the variants of this product that the collection holds, for the card's dropdown.
        Returns:
            list: The ID and name of each variant.
        """
        self.ensure_one()
        collection = self.get_collection_card_context()
        held_variants = collection.get_variant_level_items().get(self.id) if collection else None
        return [{'id': variant.id, 'name': variant.name} for variant in held_variants or []]

    @api.depends_context('collection_id')
    def _compute_collection_variant_summary(self):
        """
        Task: T8887 - Compute the text shown on a Collection Items card, e.g. 1 of 3 variants.
        """
        collection = self.get_collection_card_context()
        held_variants_by_listing = collection.get_variant_level_items() if collection else {}
        for listing in self:
            held_variants = held_variants_by_listing.get(listing.id)
            variant_count = len(listing.listing_item_ids)
            listing.collection_variant_summary = _("%(held)s of %(total)s %(label)s", held=len(held_variants), total=variant_count,
                                                   label=_("variant") if variant_count == 1 else _("variants")) if held_variants else False
