import base64
import hashlib
import io
import json
import logging
import os
import pprint
import time
import uuid
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from types import SimpleNamespace

import psycopg2
import pytz
import requests
from PIL import Image
from odoo.exceptions import RedirectWarning
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DF
from odoo.tools import float_is_zero, html_escape
import re

from odoo import models, fields, tools, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import (GET_SPECIFIC_PRODUCT_DATA, GET_SPECIFIC_PRODUCTS_BY_IDS, GET_MULTIPLE_PRODUCTS, GET_PRODUCT_VARIANT_AFTER_CURSOR,
                                                        GET_PRODUCT_PUBLICATION_AFTER_CURSOR, GET_PRODUCT_IMAGE_AFTER_CURSOR, GET_VARIANT_PUBLICATION_AFTER_CURSOR,
                                                        UPDATE_PRODUCT_DATA, PUBLISH_PRODUCT, UNPUBLISH_PRODUCT, ADD_UPDATE_VARIANT_MEDIA, INVENTORY_SET_QUANTITIES, PRICE_UPDATE,
                                                        GET_INVENTORY_LOCATION_WISE, GET_INVENTORY_LOCATION_WISE_AFTER_CURSOR,
                                                        FETCH_PRODUCT_AND_VARIANT_METAFIELDS, GET_REMAINING_PRODUCT_METAFIELD, GET_REMAINING_PRODUCT_VARIANT_METAFIELD, \
                                                        UPDATE_RESOURCE_METAFIELDS, DELETE_SPECIFIC_METAFIELD_VALUE, STAGED_UPLOADS_CREATE,
                                                        BULK_MUTATION_RUN, GET_BULK_OPERATION_BY_ID, BULK_OPERATION_UPDATE_SALES_CHANNEL,
                                                        BULK_OPERATION_UPDATE_SALES_CHANNEL_UNPUBLISH, GET_PRODUCT_MEDIA_BATCH, GET_METAOBJECTS_BY_IDS)
from odoo.addons.shopify.models.misc import convert_shopify_datetime_to_utc, extract_numeric_id, upload_content_to_staged_target

_logger = logging.getLogger("Qamah:Shopify")

INVENTORY_MANAGEMENT = [('shopify', 'Track Quantity'), ('dont_track', 'Dont track Inventory')]
FULFILLMENT_SERVICE = [('manual', 'Manual'), ('shopify', 'shopify'), ('gift_card', 'Gift Card')]
PAGINATED_RESOURCES = [('variants', 'variantsCount', GET_PRODUCT_VARIANT_AFTER_CURSOR), ('resourcePublications', 'resourcePublicationsCount', GET_PRODUCT_PUBLICATION_AFTER_CURSOR),
                       ('media', 'mediaCount', GET_PRODUCT_IMAGE_AFTER_CURSOR)]

# Task: T7609 - metafieldsDelete accepts at most 25 metafield identifiers per call, so the delete bulk is
# chunked by this size. productSet has no such cap: metafields ride inline with the product, however many.
SHOPIFY_METAFIELD_LIMIT = 25
# Task: T7609 - Upper bound of the content-length-range condition in the policy Shopify signs for a staged
# bulk upload (100 MB, documented under "Limitations" of the bulk import guide). Above it GCS answers
# EntityTooLarge instead of the 201 success status.
SHOPIFY_BULK_FILE_SIZE_LIMIT = 100 * 1024 * 1024
# Task: T7609 - Size at which the JSONL payload is cut into another chunk. Kept below the hard limit so a
# payload never sits on the edge, and so the multipart envelope of the upload can never push it over.
SHOPIFY_BULK_CHUNK_SIZE = 90 * 1024 * 1024
# Task: T7609 - Shopify runs at most 5 bulk mutations per shop at the same time. Extra chunks wait in
# QUEUED state and the poll cron starts them as slots free up.
SHOPIFY_MAX_CONCURRENT_BULK = 5

# Task: T7609 - Matching an Odoo image against a Shopify media downloads the ORIGINAL, so the peak memory
# of the step is roughly this many decoded images at once. Kept below MAX_WORKERS on purpose: a shop of
# multi-megapixel photos decodes to width * height * 4 bytes per image.
SHOPIFY_MEDIA_HASH_WORKERS = 4

# Bulk Inventory update variables.
BATCH_SIZE = 250  # 500
MAX_WORKERS = 4  # Number of parallel batches inside each mini-job
MAX_RETRIES = 1
RETRY_SECONDS = 2


class MkListing(models.Model):
    _inherit = "mk.listing"

    fulfillment_service = fields.Selection(FULFILLMENT_SERVICE, string='Fulfillment Service', default='manual')
    shopify_fulfillment_service = fields.Char("Shopify Fulfillment Service", copy=False)
    tag_ids = fields.Many2many("shopify.tags.ts", "shopify_tags_ts_rel", "product_tmpl_id", "tag_id", "Shopify Tags")
    is_taxable = fields.Boolean("Taxable", default=False)
    shopify_image_ids = fields.One2many('shopify.product.image.ts', 'mk_listing_id', 'Shopify Images')
    collection_id = fields.One2many("shopify.collection.ts", "mk_listing_ids", "Collections")
    shopify_product_type_id = fields.Many2one("shopify.product.type.ts", "Product Type", copy=False, ondelete='cascade')

    shopify_product_category_id = fields.Many2one("shopify.product.category.ts", "Shopify Product Category", copy=False, ondelete='cascade')

    shopify_sales_channel_ids = fields.Many2many(comodel_name="shopify.sales.channels.ts", relation="mk_listing_sales_channels_rel", string="Shopify Sales Channels",
                                                 help="Sales channels/channels where this product is published.")
    skip_listing_sync = fields.Boolean(string="Skip Listing Sync", default=False, help="When enabled, this listing is excluded from all Shopify sync activities: "
                                                                                       "imports, exports, inventory updates, price updates, and scheduled jobs.")
    shopify_collection_count = fields.Integer(string="Collection Count", compute="_compute_shopify_listing_counts", help="Number of Shopify collections this listing belongs to.")
    shopify_catalog_count = fields.Integer(string="Catalog Count", compute="_compute_shopify_listing_counts", help="Number of Shopify catalogs this listing belongs to.")

    def _compute_shopify_listing_counts(self):
        """Task: T7871 - Compute the number of Shopify collections and catalogs linked to each listing."""
        collection_obj = self.env['shopify.collection.ts']
        catalog_obj = self.env['shopify.catalog.ts']
        for listing in self:
            if not listing.id:
                listing.shopify_collection_count = 0
                listing.shopify_catalog_count = 0
                continue
            listing.shopify_collection_count = collection_obj.search_count([('mk_listing_ids', 'in', listing.ids)])
            listing.shopify_catalog_count = catalog_obj.search_count([('variant_price_ids.mk_listing_id', '=', listing.id)])

    def action_view_shopify_collections(self):
        """Task: T7871 - Opens the Shopify collections view from the listing smart button.
            Displays all Shopify collections associated with the current listing.
            Opens the form view directly when a single collection is related, otherwise the list view."""
        self.ensure_one()
        collection_ids = self.env['shopify.collection.ts'].search([('mk_listing_ids', 'in', self.ids)])
        action = {
            'name': _('Collections'),
            'type': 'ir.actions.act_window',
            'res_model': 'shopify.collection.ts',
            'context': {'default_mk_instance_id': self.mk_instance_id.id},
        }
        if len(collection_ids) == 1:
            action.update({'view_mode': 'form', 'res_id': collection_ids.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('id', 'in', collection_ids.ids)]})
        return action

    def action_view_shopify_catalogs(self):
        """Task: T7871 - Opens the Shopify catalogs view from the Catalogs smart button.
            Displays all Shopify catalogs associated with the current listing.
            Opens the form view directly when a single catalog is related, otherwise the list view."""
        self.ensure_one()
        catalog_ids = self.env['shopify.catalog.variant.price.ts'].search([('mk_listing_id', '=', self.id)]).catalog_id
        action = {
            'name': _('Catalogs'),
            'type': 'ir.actions.act_window',
            'res_model': 'shopify.catalog.ts',
            'context': {'default_mk_instance_id': self.mk_instance_id.id},
        }
        if len(catalog_ids) == 1:
            action.update({'view_mode': 'form', 'res_id': catalog_ids.id})
        else:
            action.update({'view_mode': 'list,form', 'domain': [('id', 'in', catalog_ids.ids), ('mk_instance_id', '=', self.mk_instance_id.id)]})
        return action

    def action_sync_listing_to_odoo(self):
        """
        Task: T6197 - Add Shopify Listing Update Button to Sync Listings into Odoo
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.
        This method is used to update the listing by importing the latest data from the shopify.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
        mk_log_line_dict = {'error': [], 'success': []}
        if mk_instance_id.state != 'confirmed':
            error_msg = "You can update a listing only with a confirmed instance. Please ensure the instance is confirmed before updating the listing."
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)
        try:
            # Connect to Shopify
            mk_instance_id.connection_to_shopify()
            # Fetch listing from Shopify
            product_list = self._fetch_single_listings(mk_instance_id, self.mk_id, mk_log_id)
            if not product_list:
                mk_log_id and not mk_log_id.log_line_ids and mk_log_id.unlink()
                return True

            shopify_product_dict = product_list[0]

            mk_instance_id = mk_instance_id.with_context(force_metaobject_entry_refresh=True)
            self.with_context(mk_log_line_dict=mk_log_line_dict, mk_log_id=mk_log_id).create_update_shopify_product(
                shopify_product_dict, mk_instance_id, update_product_price=True, is_update_existing_products=True)

            if mk_log_id and not mk_log_id.log_line_ids:
                mk_log_id.unlink()
                message = _("The listing has been updated with the latest data from the shopify.")
            else:
                message = (
                        _('The listing has been updated with the latest data from Shopify.'
                          '<br/>Please check the log <b><a href="/web#id=%(log_id)s&model=mk.log&view_type=form">'
                          '%(log_name)s</a></b> for details regarding the update.')
                        % {'log_id': mk_log_id.id, 'log_name': html_escape(mk_log_id.name)}
                )

            self.env['bus.bus']._sendone(
                self.env.user.partner_id,
                'marketplace_notification',
                {
                    'title': _('Update Completed'),
                    'message': message,
                    'message_is_html': True,
                    'type': 'info',
                    'sticky': False,
                }
            )

        except Exception as e:
            raise MarketplaceException("Unable to update the listing with the latest data from Shopify. Error: %s" % str(e))

    def action_sync_listing_to_shopify(self):
        """
        Task: T7845 - One-click direct update from Odoo to Shopify without opening the wizard. Updates product details, price, quantity and images.
        Sales channels and publish/unpublish are intentionally skipped.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        if mk_instance_id.state != 'confirmed':
            error_msg = _("You can update a listing only with a confirmed instance. Please ensure the instance is confirmed before updating the listing.")
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)
        # Task: T9096 - Metaobject metafields cannot be synced while Metaobject Functionality is off, so say it up front.
        if mk_instance_id.enable_metafield and not mk_instance_id.enable_metaobject:
            metaobject_mappings = mk_instance_id.metafield_resource_ids.filtered(
                lambda r: r.active_sync and r.shopify_owner_type in ('PRODUCT', 'PRODUCTVARIANT')).mapping_ids.filtered(
                lambda m: 'metaobject_reference' in (m.types or '') and m.active_mapping and m.mapping_status == 'ready')
            if metaobject_mappings:
                mk_instance_id.show_shopify_instance_redirect_warning(_(
                    "UPDATE LISTING: Cannot sync listing %(listing)s (%(mk_id)s) to Shopify for instance (%(instance)s)\n"
                    "Reason: Metaobject Functionality is turned off for this instance, but these metafields link to metaobject entries: %(metafields)s\n"
                    "How to fix:\n"
                    "  • Go to Marketplaces > Configuration > Instance, open the instance, go to the Metafields tab, and turn on Metaobject Functionality\n"
                    "  • Or turn off those metafields in Marketplaces > Shopify > Catalogs > Metafields"
                ) % {'listing': self.product_tmpl_id.display_name, 'mk_id': self.mk_id, 'instance': mk_instance_id.name,
                     'metafields': ', '.join(m.name or m.namespace_and_key for m in metaobject_mappings)})
        operation_wizard = SimpleNamespace(
            is_update_product=True,
            is_set_price=True,
            is_set_quantity=True,
            is_set_images=True,
            shopify_sales_channel_ids=False,
            is_publish_or_unpublish=False)
        self.shopify_update_listing_to_mk(operation_wizard)
        self.env['bus.bus']._sendone(
            self.env.user.partner_id,
            'marketplace_notification',
            {
                'title': _('Sync Completed'),
                'message': _("The listing has been synced to Shopify with the latest data from Odoo."),
                'message_is_html': False,
                'type': 'info',
                'sticky': False,
            }
        )
        return True

    def skip_shopify_listing_sync(self):
        for record in self:
            record.skip_listing_sync = not record.skip_listing_sync
        return True

    def shopify_hide_fields(self):
        return ['listing_publish_date', 'product_category_id']

    def transform_product_webhook_response_to_graphql(self, webhook_response, mk_instance_id=False):
        """
         Task: T5836 - Migrate Shopify to v19
         Transforms a Shopify product webhook response into a dictionary
         that follows the structure of Shopify's GraphQL API product response.
         Args:
            webhook_response (dict): Dictionary containing the Shopify product data received via a REST API webhook.
         Returns:
            graphql_product_dict (dict):  A dictionary formatted similarly to Shopify's GraphQL product response.
        """

        def shopify_utc_iso_format(timestamp_str):
            """
            Helper to convert Shopify's REST timestamp to UTC ISO format (ending in Z).
            Args:
                timestamp_str (str): A datetime string received from a Shopify webhook (e.g., '2025-10-14T09:23:45-04:00').
            Returns:
                date (str): The timestamp converted to UTC in ISO 8601 format (e.g., '2025-10-14T13:23:45Z'), or None if input is invalid.
            """
            if not timestamp_str:
                return None
            dt_object = datetime.fromisoformat(timestamp_str)
            return dt_object.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        media_nodes = []
        variant_media_map = {}
        for media_item in webhook_response.get('media', []):
            media_node = {
                'id': media_item.get('admin_graphql_api_id'),
                'mediaContentType': media_item.get('media_content_type'),
                'preview': {
                    'image': {
                        'url': media_item.get('preview_image').get('src'),
                    }
                },
            }
            media_nodes.append(media_node)
            for variant_id in media_item.get('variant_ids', []):
                if variant_id not in variant_media_map:
                    variant_media_map[variant_id] = []
                variant_media_map[variant_id].append(media_node)

        # Variants
        variant_nodes = []
        for variant in webhook_response.get('variants'):
            variant_media = variant_media_map.get(variant.get('id'), [])
            inventoryItem = {
                'id': f"gid://shopify/InventoryItem/{variant.get('inventory_item_id')}" if variant.get('inventory_item_id') else None,
                'tracked': False,  # wrong mapping due to not found in webHook
                'measurement': {'weight': {'unit': '', 'value': ''}}  # wrong mapping due to not found in webHook
            }
            selected_options = []
            product_options = webhook_response.get('options', [])
            option_values = [variant.get('option1'), variant.get('option2'), variant.get('option3')]
            for i, option_value in enumerate(option_values):
                if option_value and i < len(product_options):
                    selected_options.append({
                        'name': product_options[i].get('name'),
                        'value': option_value
                    })
            variant_dict = {
                'id': variant.get('admin_graphql_api_id', ''),
                'barcode': variant.get('barcode'),
                'sku': variant.get('sku'),
                'price': variant.get('price'),
                'taxable': variant.get('taxable'),
                'title': variant.get('title'),
                'selectedOptions': selected_options,
                'inventoryItem': inventoryItem,
                'inventoryPolicy': variant.get('inventory_policy').upper(),
                'media': {'nodes': variant_media},
                'createdAt': shopify_utc_iso_format(variant.get('created_at')),
                'updatedAt': shopify_utc_iso_format(variant.get('updated_at'))
            }
            variant_nodes.append(variant_dict)

        # category
        category_payload = webhook_response.get('category', {})
        category = {}
        if category_payload:
            category = {
                'id': category_payload.get('admin_graphql_api_id'),
                'fullName': category_payload.get('full_name'),
                'name': category_payload.get('name'),
            }

        # options
        options = [{'name': option.get('name', ''), 'values': option.get('values', [])} for option in webhook_response.get('options', [])]

        # description (not included!)
        graphql_product_dict = {
            'legacyResourceId': webhook_response.get('id'),
            'id': webhook_response.get('admin_graphql_api_id'),
            'title': webhook_response.get('title'),
            'descriptionHtml': webhook_response.get('body_html'),
            'productType': webhook_response.get('product_type'),
            'category': category,
            'tags': [tag.strip() for tag in webhook_response.get('tags', '').split(',') if tag.strip()] or [],
            'variants': {'nodes': variant_nodes},
            'options': options,
            'media': {'nodes': media_nodes},
            'createdAt': shopify_utc_iso_format(webhook_response.get('created_at')),
            'updatedAt': shopify_utc_iso_format(webhook_response.get('updated_at')),
            'resourcePublications': {'nodes': []},
        }

        return graphql_product_dict

    def action_publish_unpublish_shopify_products(self):
        """
        Task: T5836 - Migrate Shopify to v19
        Opens Shopify product's manage sales channels wizard.
        """
        action = self.env.ref('shopify.action_shopify_product_publications_wizard').sudo().read()[0]
        ctx = self.env.context.copy()
        shopify_sales_channel_ids = self.shopify_sales_channel_ids.ids
        model = self._name
        active_id = self.id
        ctx.update({
            'active_model': model,
            'active_record_id': active_id
        })
        ctx['default_mk_instance_id'] = self.mk_instance_id.id
        ctx['default_shopify_sales_channel_ids'] = [(6, 0, shopify_sales_channel_ids)]
        ctx.update({'active_record_id': self.id})
        action['context'] = ctx
        return action

    def get_shopify_sales_channels(self, shopify_sales_channel_dict, mk_instance_id=None):
        """
        Task: T5836 - Migrate Shopify to v19
        This method processes Shopify publication(sales channel) data (fetched via GraphQL) and ensures that corresponding 'shopify.sales.channels.ts' records exist in Odoo.
        If a publication(sales channel) does not exist, it is created. Finally, it returns the IDs in the format required for setting Many2many shopify publication field in listing.
        Args:
            shopify_sales_channel_dict (dict): Dictionary containing Shopify publication(sales channel) data from the GraphQL API response.
            mk_instance_id (record, optional): Marketplace instance the channels belong to. Callers that
                run on an EMPTY recordset (the import flow builds the vals before the listing exists)
                must pass it: falling back to self.mk_instance_id there yields False, which makes the
                lookup below miss every instance-scoped channel and create a duplicate with no instance.
        Returns:
            Dictionary: Returns dictionary which contains 'shopify_sales_channel_ids' to update/set in listing.
        """
        if not shopify_sales_channel_dict:
            return False, []

        shopify_sales_channel_obj = self.env['shopify.sales.channels.ts'].sudo()
        shopify_sales_channel_list = []
        mk_instance_id = mk_instance_id or self.mk_instance_id

        # Extract the list of publication(sales channel) nodes from the GraphQL response
        channels = shopify_sales_channel_dict.get("nodes", {})
        for channel in channels:
            sales_channel_id = str(extract_numeric_id(channel.get('publication', {}).get('id', '')))
            # Find an existing channel record in 'shopify.sales.channels.ts' for this instance.
            shopify_sales_channel_id = shopify_sales_channel_obj.search([("sales_channel_id", "=", sales_channel_id), ("mk_instance_id", "=", mk_instance_id.id)], limit=1)

            # Create channel record if not found in 'shopify.sales.channels.ts'.
            if not shopify_sales_channel_id:
                publication_nodes = channel.get('publication', {}).get('catalog', {}).get('apps', {}).get('nodes', [])
                # Extract publication name from response (each publication_nodes list contains one record so take first instead of iterate over loop)
                publication_name = publication_nodes and publication_nodes[0].get('title', '')
                if publication_name:
                    shopify_sales_channel_id = shopify_sales_channel_obj.create({"name": publication_name or '', "sales_channel_id": sales_channel_id, "mk_instance_id": mk_instance_id.id})
            # Only append a real record: with no match and no publication name this stays an empty
            # recordset, whose .id is False, and False in the (6, 0, ids) command breaks the write.
            if shopify_sales_channel_id:
                shopify_sales_channel_list.append(shopify_sales_channel_id.id)
        return {'shopify_sales_channel_ids': [(6, 0, shopify_sales_channel_list)]}, shopify_sales_channel_list

    def shopify_product_query_filter(self, from_date, to_date, import_date_based_on=None, import_draft_products=False):
        """
        Task: T5836 - Migrate Shopify to v19
        Added this to Generates and returns the filter used in the GraphQL query to import multiple Shopify products.
        Args:
            from_date (datetime): From date to import listing from shopify to odoo.
            to_date (datetime): To date to import listing from shopify to odoo.
            import_date_based_on (str): Indicates based on update date or created date.
            import_draft_products (bool): The boolean value indicate is draft product has been import.
        Returns:
            String (str): String states query filter.
        """
        filters = []
        # Set default to_date to current date if not provided
        to_date = to_date or fields.Datetime.now()
        if from_date:
            from_date = pytz.UTC.localize(from_date)
            to_date = pytz.UTC.localize(to_date)
            # Convert dates to ISO 8601 format (YYYY-MM-DD) as required by the GraphQL query.
            iso_from = from_date.isoformat().replace('+00:00', 'Z')
            iso_to = to_date.isoformat().replace('+00:00', 'Z')
            date_field = 'updated_at' if import_date_based_on == 'updated_at_min' else 'created_at'
            filters.append(f"{date_field}:>='{iso_from}' {date_field}:<='{iso_to}'")
            status = "DRAFT" if import_draft_products else "ACTIVE"
            filters.append(f"status:{status}")
        return "".join(filters)

    def fetch_all_shopify_products(self, from_listing_date, to_listing_date, mk_instance_id, import_date_based_on='updated_at_min', import_draft_products=False):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrate this method that fetches a list of Shopify products using the GraphQL API based on the provided options.
        - New method parameter added 'mk_instance_id'.
        Args:
            from_listing_date (datetime): From date to import listing from shopify to odoo.
            to_listing_date (datetime): To date to import listing from shopify to odoo.
            mk_instance_id (recordset): Recordset of mk.instance model.
        Returns:
            shopify_product_list (list): A list of dictionaries containing Shopify product data.
        Raises:
            MarketplaceException: If the GraphQL query fails or any error occurs during the API request.
        """
        cursor = None
        shopify_product_list = []
        query_filter = self.shopify_product_query_filter(from_listing_date, to_listing_date, import_date_based_on,
                                                         import_draft_products)  # e.g. 'updated_at:>=2025-07-11 updated_at:<=2025-08-05'

        while True:
            try:
                variables = {"productsCursor": cursor, "queryFilter": query_filter}
                res = mk_instance_id.execute_graphql_query(GET_MULTIPLE_PRODUCTS, variables)
                user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Product: %(errors)s") % {'errors': joined_errors})

                product_list = res and res.get('data', {}).get('products', {})

                # Exclude the 'pageInfo' dictionary from the product list, keeping only product entries.
                # Task: T7725 - Added defensive pagination handling for single-page Shopify responses.
                if product_list and isinstance(product_list, list):
                    last_item = product_list[-1]
                    if isinstance(last_item, dict) and set(last_item.keys()) == {'pageInfo'}:
                        shopify_product_list.extend(product_list[:-1])
                        page_info = last_item.get('pageInfo', {})
                    else:
                        shopify_product_list.extend(product_list)
                        page_info = {}
                    if not page_info.get('hasNextPage', False):
                        break

                    cursor = page_info.get('endCursor', None)
            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException("Failed to fetch Shopify products: %s" % str(e))

        return shopify_product_list

    def mapping_shopify_weight_name(self, shopify_weight_name, reverse=False):
        """
        Task: T5836 - Migrate Shopify to v19
        Added this method to maps Shopify's weight unit name to the corresponding base marketplace weight unit abbreviation.
        If True, map abbreviation -> Shopify name.
        Args:
            shopify_weight_name (str): Shopify weight unit name received from the API response (e.g., 'OUNCES').
            reverse (bool): If True, map abbreviation -> Shopify name. e.g. 'oz'(marketplace weight unit) to 'OUNCES' (shopify weight unit).
        Returns:
            shopify_converted_weight_name (str): Corresponding weight unit abbreviation (e.g., 'oz').
        """
        weight_map = {
            'OUNCES': 'oz',
            'GRAMS': 'g',
            'KILOGRAMS': 'kg',
            'POUNDS': 'lb',
        }
        if not shopify_weight_name:
            return ''

        if reverse:
            reverse_map = {v: k for k, v in weight_map.items()}
            return reverse_map.get(shopify_weight_name, '')

        return weight_map.get(shopify_weight_name, '')

    def prepare_attribute_line_vals(self, shopify_product_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        product_attribute_obj = self.env['product.attribute']
        product_attribute_value_obj = self.env['product.attribute.value']
        attribute_line_vals = []
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        shopify_variant_list = shopify_product_dict.get("variants", {}).get('nodes', [])
        if len(shopify_variant_list) >= 1:
            for product_attribute_dict in shopify_product_dict.get("options", ""):
                attribute_name = product_attribute_dict.get("name", "")
                attribute_values = product_attribute_dict.get('values', '')
                product_attribute_id = product_attribute_obj.search([("name", "=ilike", attribute_name)], limit=1)
                if product_attribute_id and product_attribute_id.create_variant != 'always':
                    mk_instance_id = self.env.context.get('mk_instance_id') or mk_log_id.mk_instance_id
                    log_message = _(
                        "IMPORT LISTING ITEM: The Variants Creation Mode for the attribute %s is not set to 'Instantly.' You will need to create products manually to sync products with %s attribute.") % (
                                      product_attribute_id.name, product_attribute_id.name)
                    self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                         mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                    return False
                if not product_attribute_id:
                    product_attribute_id = product_attribute_obj.sudo().create({"name": attribute_name})

                product_attribute_value_id_list = []
                for attribute_value in attribute_values:
                    attrib_value = product_attribute_value_obj.search([("attribute_id", "=", product_attribute_id.id), ("name", "=ilike", attribute_value)], limit=1)
                    if not attrib_value:
                        attrib_value = product_attribute_value_obj.sudo().with_context(active_id=False).create({"attribute_id": product_attribute_id.id, "name": attribute_value})
                    product_attribute_value_id_list.append(attrib_value.id)

                if product_attribute_value_id_list:
                    attribute_line_ids_data = [0, False, {"attribute_id": product_attribute_id.id, "value_ids": [[6, False, product_attribute_value_id_list]]}]
                    attribute_line_vals.append(attribute_line_ids_data)
        return attribute_line_vals

    def all_variants_have_same_price(self, variant_list):
        """
        Check if all variants in the given list have the same price.

        :param variant_list: List of variant dictionaries containing price information.
        :return: True if all variants have the same price, False otherwise.
        """
        # Extract all the prices from the variants
        prices = [variant_item['price'] for variant_item in variant_list]

        # Check if all prices are the same
        return all(price == prices[0] for price in prices)

    def create_odoo_template_for_shopify_product(self, shopify_product_dict, existing_odoo_product, mk_instance_id, shopify_product_category_id, update_product_price):
        """
        Task: T5836 - Migrate Shopify to v19
        Create or update Odoo product templates based on Shopify product data.
        """
        # Prepare basic product template values
        product_template_vals = self._prepare_product_template_vals(shopify_product_dict, mk_instance_id, shopify_product_category_id)
        if not product_template_vals:
            return False

        # Create product template in Odoo
        odoo_template_obj = self.env["product.template"]
        product_tmpl_id = odoo_template_obj.sudo().create(product_template_vals)

        shopify_variant_list = shopify_product_dict.get("variants", {}).get('nodes', [])

        if len(shopify_variant_list) > 1:
            # Handle multiple variants for the created product template
            self._create_variants_for_template(shopify_variant_list, shopify_product_dict, product_tmpl_id, existing_odoo_product, mk_instance_id, update_product_price)
        else:
            # Handle a single variant for the created product template
            self._update_single_variant(shopify_variant_list[0], product_tmpl_id, existing_odoo_product, update_product_price, mk_instance_id)

        return product_tmpl_id

    def _prepare_product_template_vals(self, shopify_product_dict, mk_instance_id, shopify_product_category_id):
        """
        Task: T5836 - Migrate Shopify to v19
        Prepare values for creating a product template in Odoo.
        """
        shopify_product_title = shopify_product_dict.get("title", "")
        attribute_line_vals = self.prepare_attribute_line_vals(shopify_product_dict)

        if not attribute_line_vals:
            return False

        product_template_vals = {
            'name': shopify_product_title,
            'is_storable': True,
            'type': 'consu',
            'attribute_line_ids': attribute_line_vals,
            'description_sale': shopify_product_dict.get("description", ""),
        }

        all_same_price = self.all_variants_have_same_price(shopify_product_dict.get("variants", {}).get('nodes', []))
        if all_same_price:
            template_price = shopify_product_dict.get("variants", {}).get('nodes', []) and shopify_product_dict.get("variants", {}).get('nodes', [])[0]['price']
            product_template_vals['list_price'] = self._convert_price_if_needed(template_price, mk_instance_id)

        if mk_instance_id.is_update_odoo_product_category and shopify_product_category_id:
            odoo_product_category_for_shopify_product = self.env['product.category'].sudo().create_or_get_odoo_category_for_shopify_product(shopify_product_category_id)
            product_template_vals.update({'categ_id': odoo_product_category_for_shopify_product.id})

        return product_template_vals

    def _convert_price_if_needed(self, price, mk_instance_id):
        """
        Convert price if the marketplace currency is different from the company's currency.
        """
        if mk_instance_id.pricelist_id.currency_id.id == mk_instance_id.company_id.currency_id.id:
            return float(price)
        else:
            return mk_instance_id.pricelist_id.currency_id._convert(float(price), mk_instance_id.company_id.currency_id, self.env.user.company_id, fields.Date.today())

    def _create_variants_for_template(self, shopify_variant_list, shopify_product_dict, product_tmpl_id, existing_odoo_product, mk_instance_id, update_product_price):
        """
        Task: T5836 - Migrate Shopify to v19
        Create variants for a product template in Odoo.
        """
        for variant_dict in shopify_variant_list:
            shopify_attribute_dict = self._prepare_shopify_attribute_dict(variant_dict, shopify_product_dict)
            odoo_product_id = self._find_odoo_product_from_marketplace_attribute(shopify_attribute_dict, product_tmpl_id)

            # Prepare values for updating the variant
            product_update_vals = {'default_code': variant_dict.get('sku')}
            barcode = variant_dict.get('barcode')
            if barcode:
                product_update_vals.update({'barcode': barcode})

            odoo_product_id.sudo().write(product_update_vals)
            existing_odoo_product.update({str(extract_numeric_id(variant_dict.get('id'))): odoo_product_id})

    def _prepare_shopify_attribute_dict(self, variant_dict, shopify_product_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Prepare Shopify attribute dictionary from variant and product data.
        """
        shopify_attribute_dict = {}
        for attribute_dict in variant_dict.get('selectedOptions', []):
            shopify_attribute_dict.update({attribute_dict.get('name'): attribute_dict.get('value')})
        return shopify_attribute_dict

    def _update_single_variant(self, variant_dict, product_tmpl_id, existing_odoo_product, update_product_price, mk_instance_id):
        """
        Task: T5836 - Migrate Shopify to v19
        Update the values of a single variant product.
        """
        product_tml_update_vals = {'default_code': variant_dict.get('sku')}
        shopify_weight_dict = variant_dict.get('inventoryItem', {}).get('measurement', {}).get('weight', {})
        if variant_dict.get('barcode'):
            product_tml_update_vals.update({'barcode': variant_dict.get('barcode')})

        # Update price if applicable
        price = variant_dict.get('price')
        if price:
            product_tml_update_vals.update({'list_price': self._convert_price_if_needed(price, mk_instance_id)})

        # Convert and update weight if available
        mapping_shopify_weight_name = self.mapping_shopify_weight_name(shopify_weight_dict.get('unit', ''))
        shopify_converted_weight = self.env['mk.listing']._marketplace_convert_weight(shopify_weight_dict.get('value', ''), mapping_shopify_weight_name)

        if shopify_converted_weight and product_tmpl_id:
            product_tml_update_vals.update({'weight': shopify_converted_weight})

        product_tmpl_id.sudo().write(product_tml_update_vals)
        existing_odoo_product.update({str(extract_numeric_id(variant_dict.get('id'))): product_tmpl_id.product_variant_ids})

    def shopify_check_is_listing_published(self, shopify_sales_channel_ids_list):
        """
        Task: T5836 - Migrate Shopify to v19
        Added - This method will check weather this product is published on "Online Store" or not.
        Args:
            shopify_sales_channel_ids_list (list): List of sales channel ids in which the current product is published.
        Returns:
            bool: Returns True if listing(product) is published on online store.
        """
        if not shopify_sales_channel_ids_list:
            return False
        channel_id = self.env['shopify.sales.channels.ts'].search([('name', '=', 'Online Store'), ('mk_instance_id', '=', self.mk_instance_id.id)], limit=1)
        if channel_id and channel_id.id in shopify_sales_channel_ids_list:
            return True
        else:
            return False

    def prepare_marketplace_listing_vals_for_shopify(self, mk_instance_id, shopify_product_dict, odoo_product_id, shopify_product_category_id, shopify_product_type):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        vals = {}
        mk_id = str(extract_numeric_id(shopify_product_dict.get('id', "")))
        shopify_product_tags = shopify_product_dict.get('tags', [])
        shopify_variant_list = shopify_product_dict.get('variants', {}).get('nodes', [])
        shopify_product_title = shopify_product_dict.get("title", "")
        shopify_product_body_html = shopify_product_dict.get("descriptionHtml", "")
        shopify_product_updated_at = convert_shopify_datetime_to_utc(shopify_product_dict.get("updatedAt", ""))
        shopify_product_created_at = convert_shopify_datetime_to_utc(shopify_product_dict.get("createdAt", ""))

        if shopify_product_category_id:
            vals.update({'shopify_product_category_id': shopify_product_category_id.id})

        vals.update(
            {'name': shopify_product_title,
             'mk_instance_id': mk_instance_id.id,
             'product_tmpl_id': odoo_product_id.product_tmpl_id.id,
             'mk_id': mk_id,
             'listing_create_date': shopify_product_created_at,
             'listing_update_date': shopify_product_updated_at,
             'description': shopify_product_body_html,
             'is_listed': True,
             'number_of_variants_in_mk': len(shopify_variant_list),
             'shopify_product_type_id': shopify_product_type.id if shopify_product_type else False
             })

        shopify_tag_vals = self.prepare_tag_vals(shopify_product_tags)
        if shopify_tag_vals:
            vals.update(shopify_tag_vals)

        # Skip fields if processed via a create/update webhook
        if self.env.context.get('operation_type', 'import') != 'webhook':
            # Set publications
            shopify_publications, shopify_sales_channel_ids_list = self.get_shopify_sales_channels(shopify_product_dict.get('resourcePublications', {}), mk_instance_id)
            shopify_publications and vals.update(shopify_publications)
            is_published = self.shopify_check_is_listing_published(shopify_sales_channel_ids_list)
            vals.update({'is_published': is_published})
        return vals

    def prepare_marketplace_listing_item_vals_for_shopify(self, shopify_product_dict, shopify_variant_dict, mk_instance_id, odoo_product_id, mk_listing_id):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """

        is_webhook_data = False if self.env.context.get('operation_type') == 'webhook' else True
        variant_title = shopify_product_dict.get("title", "") if shopify_variant_dict.get("title", "") == 'Default Title' else shopify_variant_dict.get("title", "")
        variant_inventory_management = shopify_variant_dict.get('inventoryItem', {}).get('tracked', False)
        shopify_variant_weight_unit = self.mapping_shopify_weight_name(shopify_variant_dict.get('inventoryItem', {}).get('measurement', {}).get('weight', {}).get('unit', ''))
        vals = {
            'name': variant_title,
            'product_id': odoo_product_id.id,
            'default_code': shopify_variant_dict.get("sku", ""),
            'barcode': shopify_variant_dict.get("barcode", ""),
            'mk_listing_id': mk_listing_id.id,
            'mk_id': str(extract_numeric_id(shopify_variant_dict.get("id", ""))),
            'mk_instance_id': mk_instance_id.id,
            'item_create_date': convert_shopify_datetime_to_utc(shopify_variant_dict.get("createdAt", "")),
            'item_update_date': convert_shopify_datetime_to_utc(shopify_variant_dict.get("updatedAt", "")),
            'is_listed': True,
            'is_taxable': shopify_variant_dict.get('taxable'),
            'inventory_item_id': str(extract_numeric_id(shopify_variant_dict.get('inventoryItem', {}).get('id', ''))),
            'continue_selling': shopify_variant_dict.get("inventoryPolicy", ""),
        }
        # Task: T7874 - Fix issue where `weight_unit` and `inventory_management` fields are not updated when product data is received from the Shopify webhook.
        if is_webhook_data:
            vals.update({'weight_unit': shopify_variant_weight_unit})

            if variant_inventory_management:
                vals.update({'inventory_management': 'shopify'})
            else:
                vals.update({'inventory_management': 'dont_track'})
        # Task:- T7796  Map Shopify variant publication channels to listing item sales channels.
        resource_publications = shopify_variant_dict.get('resourcePublicationsV2', {})
        item_sales_channels, _ = self.get_shopify_sales_channels(resource_publications, mk_instance_id)
        if item_sales_channels:
            vals.update({'shopify_sales_channel_ids': item_sales_channels['shopify_sales_channel_ids']})

        return vals

    def prepare_tag_vals(self, shopify_product_tags):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        shopify_tag_obj = self.env['shopify.tags.ts']
        shopify_tag_list = []
        sequence = 1
        for tag in shopify_product_tags:
            if len(tag) < 1:
                continue
            shopify_tag_id = shopify_tag_obj.search([('name', '=', tag.strip())], limit=1)
            if not shopify_tag_id:
                shopify_tag_id = shopify_tag_obj.sudo().create({'name': tag.strip(), 'sequence': sequence})
                sequence += 1
            shopify_tag_list.append(shopify_tag_id.id)
        return {'tag_ids': [(6, 0, shopify_tag_list)]}

    def _shopify_image_pixel_md5(self, content):
        """
        Task: T7609 - Identify an image by the md5 of its decoded pixels.

        The md5 of the FILE cannot be used: Shopify re-encodes every upload (48 extra bytes of metadata on
        a PNG), so `image_hex` never equals the md5 of the copy Shopify serves. The decoded pixels are left
        untouched, so their md5 is identical on both sides while - unlike a perceptual hash - two images
        that differ by a single pixel still get two different keys.

        The hash is fed band by band so the pixel buffer of a large image is never materialised as one
        extra copy next to the decoded image itself.
        Args:
            content (bytes): Raw image file, from the Odoo binary or downloaded from the Shopify CDN.
        Returns:
            str: md5 of the RGBA pixel buffer, or an empty string when the file cannot be decoded.
        """
        try:
            with Image.open(io.BytesIO(content)) as image:
                image = image.convert('RGBA')
                hasher = hashlib.md5()
                for top in range(0, image.height, 256):
                    hasher.update(image.crop((0, top, image.width, min(top + 256, image.height))).tobytes())
                return hasher.hexdigest()
        except Exception as e:
            _logger.warning("Could not decode an image while matching it with a Shopify media: %s", e)
            return ''

    def _set_missing_shopify_media_ids(self, shopify_image_response_vals):
        """
        Task: T5836 - Migrate Shopify to v19
        write missing media_id for existing images(in existing listing) by comparing with Shopify images.
        used same method to set media_id while importing or exporting shopify product media.
        Args:
            shopify_image_response_vals (dict): Dictionary contains specific shopify product media.
        Returns:
            True (bool): Returns true on successful.
        """
        try:
            mk_listing_image = self.env['mk.listing.image']
            scope = self.env.context.get('scope', '')

            images_without_media_domain = [
                ('media_id', '=', False),
                ('mk_id', '!=', False),  # only in existing listing do not consider new added
                ('mk_listing_id', '=', self.id)
            ]

            # for first time doesn't have media id and existing if(not have media_id and mk_id for (if user add new image then exclude that))
            images_without_media = mk_listing_image.search(images_without_media_domain)
            if not images_without_media:
                return True

            # Task: T7609 - Hash the Odoo side FIRST, from the filestore: it costs no network, and it is
            # what makes the downloads below skippable. The binaries are read in one attachment search
            # instead of one query and one filestore read per record. A key holds the LIST of images that
            # share it, because two Odoo images may legitimately hold the same binary.
            contents = images_without_media._shopify_read_image_binaries(images_without_media.ids)
            image_ids_by_hash = {}
            for img_rec in images_without_media:
                content = contents.get(img_rec.id)
                if not content:
                    continue
                local_hash = self._shopify_image_pixel_md5(content)
                if local_hash:
                    image_ids_by_hash.setdefault(local_hash, []).append(img_rec.id)

            used_media_ids = set((self.image_ids | self.listing_item_ids.image_ids).mapped('media_id'))
            image_ids_by_media_id = {}
            pending_image_count = sum(len(image_ids) for image_ids in image_ids_by_hash.values())
            #  Now try to map existing images
            for image in shopify_image_response_vals:
                # Every image is matched: nothing left to download.
                if not pending_image_count:
                    break
                if image.get('mediaContentType', '') != 'IMAGE':
                    continue

                image_url = ''
                if scope == 'import':
                    image_url = image.get('preview').get('image', {}).get('url', '')
                elif scope == 'export':
                    image_url = image.get('image', {}).get('url', '')  # at the time of import
                if not image_url:
                    continue

                shopify_image_id = str(extract_numeric_id(image.get('id', "")))
                # Task: T7609 - A media another image of this listing already carries can never be the one
                # a missing image is looking for, so it is skipped before it is downloaded.
                if shopify_image_id in used_media_ids:
                    continue

                # Task: T7609 - The ORIGINAL must be downloaded, never a `?width=` thumbnail: Shopify
                # resamples a thumbnail with its own image pipeline, so its pixels match neither the
                # original nor any local resize of it, and an exact hash would never find them.
                response = requests.get(image_url, stream=True, verify=True, timeout=10)
                if response.status_code != 200:
                    continue
                image_ids = image_ids_by_hash.get(self._shopify_image_pixel_md5(response.content)) or []
                if not image_ids:
                    continue
                used_media_ids.add(shopify_image_id)
                image_ids_by_media_id.setdefault(shopify_image_id, []).append(image_ids.pop(0))
                pending_image_count -= 1

            # Group the writes so each media_id costs a single UPDATE instead of one per image.
            for shopify_media_id, image_ids in image_ids_by_media_id.items():
                images_without_media.browse(image_ids).write({"media_id": shopify_media_id})
            return True

        except Exception as e:
            _logger.error("Error while setting missing Shopify media IDs: %s", str(e))
            return False

    def sync_product_image_from_shopify(self, mk_instance_id, shopify_product_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrate this method to GraphQL API.
        Also remove an image from listing if it removed from shopify.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model,
            shopify_product_dict (dictionary): Dictionary holds shopify product data.
        Returns:
            True (boolean): Returns True.
        """
        shopify_image_response_vals = shopify_product_dict.get('media', {}).get('nodes', [])
        self.with_context(scope='import')._set_missing_shopify_media_ids(shopify_image_response_vals)
        shopify_variant_list = shopify_product_dict.get('variants', {}).get('nodes', [])

        # Map shopify image id with list of shopify variant id
        shopify_image_to_variant_map = {}  # e.g. {28240604987445: [44172041748533], 28540929867829: [44172041715765]}  imageId:variant list
        for variant in shopify_variant_list:
            variant_id = str(extract_numeric_id(variant.get("id", "")))
            for variant_media in variant.get("media", {}).get('nodes', []):
                image_id = str(extract_numeric_id(variant_media.get("id", "")))  # MediaImage
                if image_id and variant_media.get('mediaContentType', '') == 'IMAGE':
                    shopify_image_to_variant_map.setdefault(image_id, []).append(variant_id)

        mk_listing_image = self.env['mk.listing.image']
        mk_listing_item_obj = self.env['mk.listing.item']
        processed_shopify_image_ids = []

        for position, image in enumerate(shopify_image_response_vals, start=1):
            # Include only image type
            if image.get('mediaContentType', '') != 'IMAGE':
                continue

            image_res = image.get('preview', {}).get('image', {})
            image_url = image_res.get('url', '') if image_res else ''
            if image_url:
                shopify_image_id = str(extract_numeric_id(image.get('id', "")))  # MediaImage
                variant_ids = shopify_image_to_variant_map.get(shopify_image_id, [])

                mk_listing_item_ids = mk_listing_item_obj.search([('mk_instance_id', '=', mk_instance_id.id), ('mk_id', 'in', variant_ids)])
                listing_image_id = mk_listing_image.search([('media_id', '=', shopify_image_id)])

                image_binary = base64.b64encode(requests.get(image_url).content)
                shopify_alt_text = image.get('alt', '')
                vals = {
                    'url': image_url,
                    'name': self.name,
                    'mk_id': shopify_image_id,
                    'media_id': shopify_image_id,
                    'sequence': position,
                    'image': image_binary,
                    'mk_listing_id': self.id,
                    'shopify_alt_text': shopify_alt_text,
                    'mk_listing_item_ids': [(6, 0, mk_listing_item_ids.ids)],
                }
                if listing_image_id:
                    listing_image_id.write(vals)
                else:
                    mk_listing_image.create(vals)

                for listing_item in mk_listing_item_ids:
                    listing_item.product_id.sudo().write({'image_1920': image_binary})

                if position == 1:
                    self.product_tmpl_id.sudo().write({'image_1920': image_binary})

                processed_shopify_image_ids.append(shopify_image_id)

        need_to_remove_shopify_listing_image_ids = self.env['mk.listing.image'].search(
            [('mk_listing_id', '=', self.id), ('media_id', 'not in', processed_shopify_image_ids), ('mk_id', '!=', False)])

        need_to_remove_shopify_listing_image_ids and need_to_remove_shopify_listing_image_ids.sudo().unlink()
        return True

    def get_existing_mk_listing_and_odoo_product(self, shopify_variant_list, mk_instance_id):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        existing_mk_product = {}
        existing_odoo_product = {}
        odoo_product_template = self.env['product.template']
        for variant_dict in shopify_variant_list:
            variant_id = str(extract_numeric_id(variant_dict.get("id", "")))
            odoo_product_id, listing_item_id = self.get_odoo_product_variant_and_listing_item(mk_instance_id, variant_id, variant_dict.get("barcode", ""), variant_dict.get("sku", ""))
            if odoo_product_id:
                odoo_product_template |= odoo_product_id.product_tmpl_id
                existing_odoo_product.update({variant_id: odoo_product_id})
            elif listing_item_id and not odoo_product_id:
                existing_odoo_product.update({variant_id: listing_item_id.product_id})
            listing_item_id and existing_mk_product.update({variant_id: listing_item_id})
        return existing_mk_product, existing_odoo_product, odoo_product_template

    def shopify_create_listing_item_in_odoo(self, odoo_product_template, mk_instance_id, shopify_product_dict, variant_dict, existing_odoo_product, shopify_product_category_id, update_product_price, variant_sequence, shopify_product_type):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        - The method parameter product_category_id has been replaced with shopify_product_category_id,
        - New method parameter added 'shopify_product_type'.
        """
        mk_listing_id = self
        variant_id = str(extract_numeric_id(variant_dict.get("id", "")))
        variant_sku = variant_dict.get("sku") or False
        variant_barcode = variant_dict.get("barcode") or False
        odoo_product_id = existing_odoo_product.get(variant_id, False)
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        mk_listing_item_obj = self.env['mk.listing.item']
        if not mk_listing_id:
            if not odoo_product_template and not mk_instance_id.is_create_products:
                log_message = _("IMPORT LISTING: Odoo Product not found for Shopify Product : %s and SKU: %s and Barcode : %s") % (
                    shopify_product_dict.get('title', ''), variant_sku, variant_barcode)
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                return mk_listing_item_obj, mk_listing_id, 'break'
            if not odoo_product_template:
                # Method parameter product_category_id has been replaced with shopify_product_category_id.
                odoo_product_template = self.with_context(mk_instance_id=mk_instance_id).create_odoo_template_for_shopify_product(shopify_product_dict, existing_odoo_product, mk_instance_id,
                                                                                                                                  shopify_product_category_id, update_product_price)
                if not odoo_product_template:
                    return mk_listing_item_obj, mk_listing_id, 'break'
                odoo_product_id = existing_odoo_product.get(variant_id, False)
            if not odoo_product_id:
                log_message = _(
                    "IMPORT LISTING ITEM: Odoo Product %s found but Odoo Product Variant not found for Shopify Product Variant : %s and SKU: %s and Barcode : %s This may be due to SKU or Barcode not configured properly on the Shopify. ") % (
                                  odoo_product_template.name, shopify_product_dict.get('title', ''), variant_sku, variant_barcode)
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                return mk_listing_item_obj, mk_listing_id, 'continue'
            # New method parameter added 'shopify_product_type' and method parameter product_category_id has been replaced with shopify_product_category_id.
            shopify_product_template_vals = self.prepare_marketplace_listing_vals_for_shopify(mk_instance_id, shopify_product_dict, odoo_product_id, shopify_product_category_id,
                                                                                              shopify_product_type)
            mk_listing_id = self.create(shopify_product_template_vals)
            log_message = _('IMPORT LISTING: %s successfully created') % mk_listing_id.name
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'success': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
        if not odoo_product_id:
            if not mk_instance_id.is_create_products:
                log_message = _("IMPORT LISTING ITEM: Odoo Product Variant not found for Shopify Product Variant : %s and SKU: %s and Barcode : %s") % (
                    shopify_product_dict.get('title', ''), variant_sku, variant_barcode)
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                return mk_listing_item_obj, mk_listing_id, 'continue'
            if odoo_product_template.attribute_line_ids:
                shopify_attribute_ids = self.env["product.attribute"]
                odoo_attributes = odoo_product_template.attribute_line_ids.attribute_id
                for attribute in shopify_product_dict.get('options'):
                    attribute_id = self.env["product.attribute"].search([('name', '=ilike', attribute["name"]), ('create_variant', '=', 'always')], limit=1)
                    shopify_attribute_ids |= attribute_id
                if odoo_attributes != shopify_attribute_ids or len(odoo_attributes) != len(shopify_product_dict.get('options')):
                    log_message = _("IMPORT LISTING ITEM: Odoo attribute (%s) isn't matching with Shopify attribute (%s) for Shopify Product : %s") % (
                        ','.join(odoo_attributes.mapped('name')), ','.join(shopify_attribute_ids.mapped('name')), shopify_product_dict.get('title', ''))
                    self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                         mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                    return mk_listing_item_obj, mk_listing_id, 'break'
                else:
                    shopify_attribute_dict = {}
                    for attribute_dict in variant_dict.get('selectedOptions', []):
                        shopify_attribute_dict.update({attribute_dict.get('name'): attribute_dict.get('value')})
                    self.env['product.template.attribute.line'].create_or_update_ptal(shopify_attribute_dict, odoo_product_template)
                    odoo_product_id = self._find_odoo_product_from_marketplace_attribute(shopify_attribute_dict, odoo_product_template)
                    odoo_prod_vals = {'default_code': variant_sku}
                    if variant_barcode:
                        odoo_prod_vals.update({'barcode': variant_barcode})
                    odoo_product_id.sudo().write(odoo_prod_vals)
            if not odoo_product_id:
                log_message = _(
                    "IMPORT LISTING ITEM: Non Variation Odoo Product %s found. \n1. You have to add Attribute and Values in Odoo Product.\n2. Set Sku and Barcode According to the Shopify Variants.\n3. Try to re-sync again.") % odoo_product_template.name
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                return mk_listing_item_obj, mk_listing_id, 'continue'
                # shopify_attribute_dict = {}
                # for index, attribute_dict in enumerate(shopify_product_dict.get('options'), start=1):
                #     attribute_value = variant_dict.get("option{}".format(index))
                #     shopify_attribute_dict.update({attribute_dict.get('name'): attribute_value})
                # attribute_line_vals = self.prepare_attribute_line_vals(shopify_product_dict)
                # self.env['product.template.attribute.line'].create_or_update_ptal(shopify_attribute_dict, odoo_product_template, attribute_line_vals)
                # odoo_product_id = self._find_odoo_product_from_marketplace_attribute(shopify_attribute_dict, odoo_product_template)
                # odoo_prod_vals = {'default_code': variant_sku}
                # if variant_barcode:
                #     odoo_prod_vals.update({'barcode': variant_barcode})
                # odoo_product_id.write(odoo_prod_vals)
        mk_listing_item_vals = self.prepare_marketplace_listing_item_vals_for_shopify(shopify_product_dict, variant_dict, mk_instance_id, odoo_product_id, mk_listing_id)
        mk_listing_item_vals.update({'sequence': variant_sequence})
        shopify_weight_dict = variant_dict.get('inventoryItem', {}).get('measurement', {}).get('weight', {})
        mapping_shopify_weight_name = self.mapping_shopify_weight_name(shopify_weight_dict.get('unit', ''))
        shopify_converted_weight = mk_listing_id._marketplace_convert_weight(shopify_weight_dict.get('value', ''), mapping_shopify_weight_name)
        if shopify_converted_weight and odoo_product_id and not odoo_product_id.weight:
            odoo_product_id.sudo().weight = shopify_converted_weight
        listing_item_id = mk_listing_item_obj.create(mk_listing_item_vals)
        self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={
            'success': [{'log_message': _('IMPORT LISTING ITEM: %s (%s) successfully created') % (mk_listing_id.name, listing_item_id.mk_id),
                         'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
        return listing_item_id, mk_listing_id, 'success'

    def create_shopify_product_category(self, shopify_product_category_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Added this method to recursively creates or gets Shopify product categories based on a Shopify category name.

        shopify_product_category_dict(dict) : A dictionary containing Shopify category details.
        parent(recordset) : The Shopify product category recordset.
        """
        shopify_product_category_obj = self.env['shopify.product.category.ts']
        category_id = shopify_product_category_dict.get('id', '').split('/')[-1]  # e.g. shopify_product_category_dict.get('id', '') : 'gid://shopify/TaxonomyCategory/ap-1'
        category_name = shopify_product_category_dict.get('name', '')
        parent = False

        full_name = shopify_product_category_dict.get('fullName', '')
        category_parts = [category.strip() for category in full_name.split('>')]

        for name in category_parts:
            domain = ['|', ('shopify_category_id', '=ilike', category_id), ('name', '=ilike', name)]
            if parent:
                domain.append(('parent_id', '=', parent.id))
            else:
                domain.append(('parent_id', '=', False))

            category = shopify_product_category_obj.search(domain, limit=1)

            if not category:
                category = self.env['shopify.product.category.ts'].sudo().create({
                    'name': name,
                    'parent_id': parent.id if parent else False,
                })
                if category_name == name.strip():
                    category.write({'shopify_category_id': category_id})
            parent = category

        return parent

    def get_shopify_product_category(self, shopify_product_category_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Added this method to search or create shopify category in 'shopify.product.category.ts' and return recordset of shopify product category.

        shopify_product_category_dict(dict) : A dictionary containing Shopify category details.
        recordset : The Shopify product category recordset.
        """
        if not shopify_product_category_dict:
            return False

        shopify_category_id = shopify_product_category_dict.get('id', '').split('/')[-1]  # e.g. shopify_product_category_dict.get('id', '') : 'gid://shopify/TaxonomyCategory/ap-1'
        shopify_category_name = shopify_product_category_dict.get('name', '')
        shopify_category = self.env['shopify.product.category.ts'].search(['|', ('shopify_category_id', '=ilike', shopify_category_id), ('name', '=ilike', shopify_category_name)], limit=1)
        if shopify_category:
            if not shopify_category.shopify_category_id:
                shopify_category.sudo().write({'shopify_category_id': shopify_category_id})
            return shopify_category
        return self.create_shopify_product_category(shopify_product_category_dict)

    def get_shopify_product_type(self, shopify_product_type):
        """
        Task: T5836 - Migrate Shopify to v19
        Added this method to search or create shopify product type in 'shopify.product.type.ts' model and return recordset of shopify product type.

        shopify_product_type(str) : String indicates shopify product type.
        recordset : The Shopify product type recordset.
        """
        if not shopify_product_type:
            return False
        shopify_product_type_obj = self.env['shopify.product.type.ts']
        shopify_product_type_id = shopify_product_type_obj.search([('name', '=ilike', shopify_product_type)], limit=1)
        if not shopify_product_type_id:
            shopify_product_type_id = shopify_product_type_obj.sudo().create({'name': shopify_product_type})
        return shopify_product_type_id

    def _create_update_shopify_listing_item(self, shopify_product_dict, existing_mk_product, existing_odoo_product, odoo_product_template, mk_instance_id, update_product_price=False):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        - Updated the logic to get or set the Shopify product category in the listing based on the Shopify category, instead of using the Shopify product type.
        - Additionally, the Shopify product type is now set in the listing.
        """
        mk_listing_id = self
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        shopify_variant_list = shopify_product_dict.get('variants', {}).get('nodes', [])
        shopify_product_category_dict = shopify_product_dict.get('category', {})
        shopify_product_category_id = self.get_shopify_product_category(shopify_product_category_dict)
        shopify_product_type = self.get_shopify_product_type(shopify_product_dict.get('productType', ""))

        listing_updated = False
        # enumerate() is used to set variant sequence.
        for variant_sequence, variant_dict in enumerate(shopify_variant_list, start=1):
            variant_id = str(extract_numeric_id(variant_dict.get('id', "")))
            variant_sku = variant_dict.get("sku") or False
            variant_barcode = variant_dict.get("barcode") or False
            variant_price = variant_dict.get('price')
            listing_item_id = existing_mk_product.get(variant_id, False)
            odoo_product_id = existing_odoo_product.get(variant_id, False)
            if not listing_item_id:
                listing_item_id, mk_listing_id, continue_break = mk_listing_id.shopify_create_listing_item_in_odoo(odoo_product_template, mk_instance_id, shopify_product_dict, variant_dict,
                                                                                                                   existing_odoo_product, shopify_product_category_id, update_product_price,
                                                                                                                   variant_sequence, shopify_product_type)
                if continue_break == 'break':
                    break
                if continue_break == 'continue':
                    continue
            else:
                if not listing_updated:
                    listing_vals = self.prepare_marketplace_listing_vals_for_shopify(mk_instance_id, shopify_product_dict, odoo_product_id or listing_item_id.product_id,
                                                                                     shopify_product_category_id, shopify_product_type)
                    mk_listing_id.write(listing_vals)
                    listing_updated = True
                mk_listing_item_vals = self.prepare_marketplace_listing_item_vals_for_shopify(shopify_product_dict, variant_dict, mk_instance_id,
                                                                                              odoo_product_id or listing_item_id.product_id, mk_listing_id)
                listing_item_id.write(mk_listing_item_vals)
                shopify_weight_dict = shopify_variant_list[0].get('inventoryItem', {}).get('measurement', {}).get('weight', {})
                mapping_shopify_weight_name = self.mapping_shopify_weight_name(shopify_weight_dict.get('unit', ''))
                shopify_converted_weight = mk_listing_id._marketplace_convert_weight(shopify_weight_dict.get('value', ''), mapping_shopify_weight_name)
                if shopify_converted_weight and odoo_product_id and not odoo_product_id.weight:
                    odoo_product_id.sudo().weight = shopify_converted_weight
                odoo_product_vals = {}
                if not odoo_product_id.default_code:
                    odoo_product_vals.update({'default_code': variant_sku})
                if not odoo_product_id.barcode:
                    odoo_product_vals.update({'barcode': variant_barcode})
                odoo_product_vals and odoo_product_id.sudo().write(odoo_product_vals)
                # Task: T9096 - Remove only a log created here; the caller's own log is theirs to remove at the end.
                # Deleting it here made later steps open new, untyped and often empty logs (log level Error).
                log_owned = not (mk_log_id and mk_log_id.exists())
                mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='import', mk_log_line_dict={'success': [
                    {'log_message': _('IMPORT LISTING ITEM: %s successfully updated') % listing_item_id.display_name, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
                if log_owned and mk_log_id.exists() and not mk_log_id.log_line_ids:
                    mk_log_id.unlink()
            update_product_price = True if not existing_mk_product else update_product_price
            listing_item_id.with_context(shopify_skip_auto_price_sync=True).create_or_update_pricelist_item(float(variant_price), update_product_price=update_product_price,
                                                                                                            skip_conversion=True)
        return mk_listing_id

    def create_update_shopify_product(self, shopify_product_dict, mk_instance_id, update_product_price=False, is_update_existing_products=True):
        """
        Task: T6290 - Added the functionality to import metafield.
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        Creates or updates a Shopify product in Odoo, handling synchronization of the product, variants, and images.
        Args:
            shopify_product_dict (dict): The Shopify product data.
            mk_instance_id: The marketplace instance object.
            update_product_price (bool): Whether to update the product price.
            is_update_existing_products (bool): Whether to update existing products.
        Returns:
            mk_listing_id: The updated or created listing.
        """
        mk_log_id = self.env.context.get('mk_log_id', False)
        queue_line_id = self.env.context.get('queue_line_id', False)
        mk_id = str(extract_numeric_id(shopify_product_dict.get('id', "")))
        shopify_variant_list = shopify_product_dict.get('variants', {}).get('nodes', [])
        mk_instance_id.connection_to_shopify()

        # After executing the main GraphQL query, there's a possibility of receiving partial data
        # For example, if a product has 10 variants but the query limit is set to 6, only 6 variants will be returned initially.
        # This logic handles such cases by performing an additional query to fetch the remaining variant data and appending it to the existing product dictionary.
        if queue_line_id:
            self.get_all_remaining_shopify_product_data(shopify_product_dict, mk_instance_id)
            shopify_variant_list = shopify_product_dict.get('variants', {}).get('nodes', [])

        # Check if listing already exists and skip if updates are disabled
        mk_listing_id = self.search([('mk_instance_id', '=', mk_instance_id.id), ('mk_id', '=', mk_id)])
        # Task: T7433 - Implemented import/export control using the ‘Allow Sync’ flag available in the listing  form view, supporting all flows to skip listings during synchronization between Odoo and Shopify.
        if mk_listing_id.skip_listing_sync:
            log_message = _("IMPORT LISTING: Skipped %s(%s) Sync is disabled.") % (mk_listing_id.name, mk_listing_id.mk_id)
            self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, operation_type='import', mk_instance_id=mk_instance_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return mk_listing_id
        if mk_listing_id and not is_update_existing_products:
            log_message = _("IMPORT LISTING: Skipped %s as it already exists!") % mk_listing_id.name
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'success': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return mk_listing_id

        # Validate SKUs and barcodes to avoid duplicates
        listing_item_validation_dict = {
            'name': shopify_product_dict.get('title'),
            'id': mk_id,
            'variants': [{'sku': variant.get('sku'), 'barcode': variant.get('barcode'), 'id': str(extract_numeric_id(variant.get('id', '')))} for variant in shopify_variant_list]
        }
        validated, log_message = self.check_for_duplicate_sku_or_barcode_in_marketplace_product(mk_instance_id.sync_product_with, listing_item_validation_dict)
        if not validated:
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False

        # Fetch existing marketplace and Odoo products
        existing_mk_product, existing_odoo_product, odoo_product_template = self.get_existing_mk_listing_and_odoo_product(shopify_variant_list, mk_instance_id)

        # Handle missing Odoo product templates
        if not odoo_product_template and mk_listing_id:
            odoo_product_template = mk_listing_id.product_tmpl_id

        # If listing exists but products are missing, update the listing
        if not mk_listing_id and existing_mk_product:
            listing_item_id = list(existing_mk_product.values())[0] if existing_mk_product.values() else None
            if listing_item_id:
                mk_listing_id = listing_item_id.mk_listing_id

        # Ensure only one Odoo product template is found
        if len(odoo_product_template) > 1:
            log_message = _("IMPORT LISTING: Found multiple Odoo Products (%s) for Shopify Product: %s.") % (
                ', '.join([x.name for x in odoo_product_template]), shopify_product_dict.get('title', ''))
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False

        # Validate the product for import
        validated, log_message = self.check_validation_for_import_product(mk_instance_id.sync_product_with, listing_item_validation_dict, odoo_product_template, existing_odoo_product,
                                                                          existing_mk_product)
        if not validated:
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False}]})
            return False

        # Create or update the Shopify listing
        mk_listing_id = mk_listing_id._create_update_shopify_listing_item(shopify_product_dict, existing_mk_product, existing_odoo_product, odoo_product_template, mk_instance_id,
                                                                          update_product_price)

        # Remove extra listing items if variant count has changed
        if len(shopify_variant_list) != mk_listing_id.item_count:
            mk_id_list = [str(extract_numeric_id(variant.get('id'))) for variant in shopify_variant_list]
            mk_listing_id.remove_extra_listing_item(mk_id_list)

        # Synchronize images if applicable
        if mk_instance_id.is_sync_images and is_update_existing_products and mk_listing_id:
            mk_listing_id.sync_product_image_from_shopify(mk_instance_id, shopify_product_dict)

        # Task: T7393 - Trigger HS code and country of origin update for product templates.
        if mk_listing_id and is_update_existing_products:
            product_tmpl_id = mk_listing_id.product_tmpl_id
            mk_listing_id.import_product_metafield_from_shopify(mk_instance_id, mk_id, product_tmpl_id, mk_log_id, queue_line_id)
            # Skip updating HS code and country of origin if triggered by webhook context
            if self.env.context.get('operation_type', 'import') != 'webhook':
                product_tmpl_id and product_tmpl_id.get_hs_code_and_country_origin(mk_log_id, shopify_product_dict, mk_instance_id)

        return mk_listing_id

    def _fetch_shopify_paginated_nodes(self, mk_instance_id, product_id, page_info, initial_nodes_list, total_count, graphql_query, result_key):
        """
        Task: T5836 - Migrate Shopify to v19
        Added - Helper function to fetch and append paginated nodes from a Shopify GraphQL endpoint.
        Args:
            mk_instance_id: The instance used to execute the GraphQL query.
            product_id (str): The ID of the Shopify product. e.g. 'gid://shopify/Product/7638833201205'
            page_info (dict): The pageInfo dictionary from the initial GraphQL response.
            initial_nodes_list (list): The list of nodes(actual data of resource) from the initial response.
            total_count (int): The total number of resource(e.g. variants, media).
            graphql_query (str): The GraphQL query string to execute.
            result_key (str): The key in the GraphQL response for which we want get its remaining data.(e.g., 'variants', 'media').
        Returns:
            list: A list containing all nodes (initial + fetched).
        """
        if not page_info.get('hasNextPage', False):
            return initial_nodes_list

        limit = total_count - len(initial_nodes_list)
        if limit <= 0:
            return initial_nodes_list

        variables = {
            "productId": product_id,
            "cursor": page_info.get('endCursor', ""),
            "first": limit
        }

        try:
            res = mk_instance_id.execute_graphql_query(graphql_query, variables)
            user_errors = res.get('errors', []) if isinstance(res, dict) else {}
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Product: %(errors)s") % {'errors': joined_errors})

            product_data = res.get('data', {}).get('product', {}) if isinstance(res, dict) else {}
            if product_data:
                remaining_nodes_list = product_data.get(result_key, {}).get('nodes', [])
                return initial_nodes_list + remaining_nodes_list
        except MarketplaceException:
            raise
        except Exception as e:
            _logger.error(f"An error occurred while fetching paginated {result_key}: {e}")

        return initial_nodes_list

    def shopify_fetch_and_update_resource(self, shopify_product_dict, mk_instance_id, product_id, resource_key, count_key, graphql_query):
        """
        Task: T5836 - Migrate Shopify to v19
        Added - A common function to fetch any paginated resource and update the main dictionary.
        Args:
            shopify_product_dict (dict):Dictionary that holds shopify product details.
            product_id (str): Shopify product id. e.g.'gid://shopify/Product/7638833201205'
            mk_instance_id (recordset): Recordset of mk.instance.
            resource_key (str): String that represent resource key. e.g. 'variants'
            count_key (str): String that represent the count key. e.g. 'variant'
            graphql_query (str): String that represents the GraphQL query.
        """
        # Get response data of specific key e.g. variant, media from product dictionary
        resource_data = shopify_product_dict.get(resource_key, {})
        if not resource_data:
            return

        initial_nodes = resource_data.get('nodes', [])
        page_info = resource_data.get('pageInfo', {})
        total_count = shopify_product_dict.get(count_key, {}).get('count', 0)

        # Call the generic worker to get all nodes
        all_nodes = self._fetch_shopify_paginated_nodes(
            mk_instance_id,
            product_id,
            page_info,
            initial_nodes,
            total_count,
            graphql_query,
            resource_key
        )

        # Update the dictionary if new nodes were fetched
        if len(all_nodes) > len(initial_nodes):
            shopify_product_dict[resource_key]['nodes'] = all_nodes

    def get_all_remaining_shopify_product_data(self, shopify_product_dict, mk_instance_id):
        """
        Task: T5836 - Migrate Shopify to v19
        Added - It loops through a predefine list which contain count key,query and key of which want to get remaining data e.g.variants, media. calling a single common function.
        Args:
            shopify_product_dict (dictionary): The product dictionary from Shopify.
            mk_instance_id (recordset): Recordset of mk.instance model.
        Returns:
            dict: The updated shopify_product_dict with all nodes fetched.
        """
        product_id = shopify_product_dict.get('id', "")
        if not product_id:
            return shopify_product_dict

        # Loop through the resource configurations and fetch data for each one
        for resource_key, count_key, graphql_query in PAGINATED_RESOURCES:
            self.shopify_fetch_and_update_resource(
                shopify_product_dict,
                mk_instance_id,
                product_id,
                resource_key,
                count_key,
                graphql_query
            )

        # Task: T7796 - Paginate resourcePublicationsV2 for each variant if hasNextPage is True
        for variant in shopify_product_dict.get('variants', {}).get('nodes', []):
            self.fetch_all_variant_publications(variant, mk_instance_id)

        return shopify_product_dict

    def fetch_all_variant_publications(self, variant_dict, mk_instance_id):
        """
        Task: T7796 - Paginates resourcePublicationsV2 for a single variant when hasNextPage is True.
            Merges all additional publication nodes into variant_dict so that prepare_marketplace_listing_item_vals_for_shopify receives the complete channel list.
        Args:
            variant_dict (dict): Single variant node from the Shopify GraphQL response.
            mk_instance_id (recordset): Recordset of mk.instance model.
        """
        pub_data = variant_dict.get('resourcePublicationsV2', {})
        page_info = pub_data.get('pageInfo', {})
        if not page_info.get('hasNextPage', False):
            return

        variant_id = variant_dict.get('id', '')
        all_nodes = list(pub_data.get('nodes', []))

        while page_info.get('hasNextPage', False):
            variables = {
                'variantId': variant_id,
                'cursor': page_info.get('endCursor', ''),
                'first': 20,
            }
            res = mk_instance_id.execute_graphql_query(GET_VARIANT_PUBLICATION_AFTER_CURSOR, variables)
            variant_data = res.get('data', {}).get('productVariant', {}) if isinstance(res, dict) else {}
            next_pub = variant_data.get('resourcePublicationsV2', {})
            all_nodes.extend(next_pub.get('nodes', []))
            page_info = next_pub.get('pageInfo', {})

        variant_dict['resourcePublicationsV2']['nodes'] = all_nodes

    def show_shopify_sales_channel_action_required_warning(self, mk_instance_id):
        """
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Args:
            mk_instance_id: Recordset of mk.instance.
        Raises:
            RedirectWarning: Raise a validation error when, after migration, the user first tries to update listings without assigning sales channels to all listings.
        """
        mk_instance_form_view_id = self.env.ref('base_marketplace.marketplace_instance_form_view').id
        action_data = {
            'view_mode': 'form',
            'name': _('Project Task'),
            'res_model': 'mk.instance',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', mk_instance_id.id)],
            'views': [[mk_instance_form_view_id, 'form']],
            'res_id': mk_instance_id.id
        }
        error_msg = _(
            "You cannot perform listing operations on the instance %s right now. Since you are migrating from an older version to a newer one, please click the 'Apply Sales Channels, Product Type ,Category to Existing Listings' button and keep pressing it until the button disappears. This ensures that sales channels are applied to all existing listings.\n") % mk_instance_id.name
        raise RedirectWarning(error_msg, action_data, _("Open Instance"))

    def shopify_import_listings(self, mk_instance_id, from_listing_date, to_listing_date, mk_listing_id=False, update_product_price=False, update_existing_product=False, import_draft_products=False):
        """
        Task: T5836 - Migrate Shopify to v19
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.
        Migrated from Shopify REST API to GraphQL API.
        Imports Shopify listings into Odoo, handling product creation or updates based on marketplace data.
        Migrated from Shopify REST API to GraphQL API.
        Raise a validation error when, after migration, the user first tries to update listings without assigning sales channels to all listings.
        Args:
            mk_instance_id: The marketplace instance object.
            from_listing_date (datetime): The start date for importing listings.
            to_listing_date (datetime): The end date for importing listings.
            mk_listing_id (str, optional): If provided, only this listing will be imported.
            update_product_price (bool): Whether to update product prices.
            update_existing_product (bool): Whether to update existing products.
            import_draft_products (bool): Whether to import draft products.
        Returns:
            dict: The action to open the listing or log view.
        """
        if mk_instance_id.need_sync_shopify_sales_channels:
            error_msg = _(
                "You cannot perform listing operations on the instance %s right now. Since you are migrating from an older version to a newer one, please click the 'Apply Sales Channels To Existing Listings' button and keep pressing it until the button disappears. This ensures that sales channels are applied to all existing listings.\n") % mk_instance_id.name
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)

        res_id_list, product_list, action = [], [], False
        mk_instance_id.connection_to_shopify()
        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')

        # Handle specific listings if provided
        if mk_listing_id:
            product_list = self._fetch_single_listings(mk_instance_id, mk_listing_id, mk_log_id)
            return self._process_imported_products(mk_instance_id, product_list, mk_log_id, update_product_price, update_existing_product)

        # Fetch listings in bulk for date range
        shopify_product_list = self.fetch_all_shopify_products(from_listing_date, to_listing_date, mk_instance_id,
                                                               import_date_based_on=self.env.context.get('import_date_based_on', 'updated_at_min'),
                                                               import_draft_products=import_draft_products)
        if shopify_product_list:
            self._queue_import_jobs(mk_instance_id, shopify_product_list, update_product_price, update_existing_product, res_id_list)

        mk_instance_id.last_listing_import_date = fields.Datetime.now()
        # TODO unlink not works
        if not mk_log_id.log_line_ids and mk_log_id:
            mk_log_id.unlink()
        if res_id_list:
            action = mk_instance_id.action_open_model_view(res_id_list, 'mk.queue.job', 'Shopify Listing Queue')
        return action

    def _fetch_single_listings(self, mk_instance_id, mk_listing_id, mk_log_id):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        Task: T8975 - Fetch the given listings 250 at a time instead of one call per listing.
        Fetches and processes a single listing from Shopify.
        """
        product_list = []
        product_ids = []
        for product_id in ''.join(mk_listing_id.split()).split(','):
            if product_id and product_id not in product_ids:
                product_ids.append(product_id)
        shopify_product_ids = [f"gid://shopify/Product/{product_id}" for product_id in product_ids]
        try:
            for batch_product_ids in tools.split_every(250, shopify_product_ids, piece_maker=list):
                variables = {"ids": batch_product_ids}
                res = mk_instance_id.execute_graphql_query(GET_SPECIFIC_PRODUCTS_BY_IDS, variables)
                user_errors = res.get('errors', [])
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Product: %(errors)s") % {'errors': joined_errors})

                batch_product_list = res.get('data', {}).get('nodes', []) if res.get('data', {}) else []
                for product_vals in batch_product_list:
                    if product_vals:
                        product_list.append(product_vals)

            # Delete the Odoo listings whose products are not found in Shopify.
            found_product_ids = [str(extract_numeric_id(product_vals.get('id'))) for product_vals in product_list]
            missing_product_ids = [product_id for product_id in product_ids if product_id not in found_product_ids]
            missing_listing_ids = self.search([('mk_id', 'in', missing_product_ids), ('mk_instance_id', '=', mk_instance_id.id)])
            for missing_listing_id in missing_listing_ids:
                log_message = _("IMPORT LISTING: Listing %s deleted from Odoo as it is not exist in Shopify!") % missing_listing_id.display_name
                missing_listing_id.sudo().unlink()
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'success': [{'log_message': log_message}]})
        except MarketplaceException:
            raise
        except Exception as e:
            log_message = f"IMPORT LISTING: Error while importing listing. ERROR: {e}"
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': log_message}]})

        return product_list

    def _process_imported_products(self, mk_instance_id, product_list, mk_log_id, update_product_price, update_existing_product):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        Processes imported products, updating or creating Shopify listings.
        """
        res_id_list = []
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})

        for shopify_product_dict in product_list:
            mk_listing_id = self.with_context(mk_log_line_dict=mk_log_line_dict, mk_log_id=mk_log_id).create_update_shopify_product(
                shopify_product_dict, mk_instance_id, update_product_price=update_product_price, is_update_existing_products=update_existing_product)
            mk_listing_id and res_id_list.append(mk_listing_id.id)
            if mk_listing_id and mk_instance_id.is_sync_images:
                mk_listing_id.sync_product_image_from_shopify(mk_instance_id, shopify_product_dict)

        if not mk_log_id.log_line_ids and not self.env.context.get('log_id', False):
            mk_log_id.unlink()
        if res_id_list:
            return mk_instance_id.action_open_model_view(res_id_list, 'mk.listing', 'Shopify Listing')
        if mk_log_id.exists():
            return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
        return product_list

    def _queue_import_jobs(self, mk_instance_id, shopify_product_list, update_product_price, update_existing_product, res_id_list):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        Queues Shopify product imports as background jobs.
        """
        batch_size = mk_instance_id.queue_batch_limit or 100
        for shopify_products in tools.split_every(batch_size, shopify_product_list):
            queue_id = mk_instance_id.with_context(update_product_price=update_product_price, update_existing_product=update_existing_product).action_create_queue(type='product')
            for shopify_product_dict in shopify_products:
                line_vals = {
                    'mk_id': str(extract_numeric_id(shopify_product_dict.get('id', ''))) or '',
                    'state': 'draft',
                    'name': shopify_product_dict.get('title', '').strip(),
                    'data_to_process': pprint.pformat(shopify_product_dict),
                    'mk_instance_id': mk_instance_id.id,
                }
                queue_id.action_create_queue_lines(line_vals)
            res_id_list.append(queue_id.id)

    def create_process_inventory_adjustment(self, inventory_level_list, mk_instance_id, shopify_location_id, mk_log_id):
        """
        T5844 - Creates and processes inventory adjustments in Odoo based on Shopify inventory data.
        Args:
            inventory_level_list: A list of dictionaries containing Shopify inventory item details and quantities
            mk_instance_id: The marketplace instance record
            shopify_location_id: The mapped Shopify location record in Odoo containing the target stock location
            mk_log_id: The log record
        Returns:
            tuple(list, recordset): A tuple containing the list of inventory lines and a recordset of updated product variants.
        """
        product_variant_ids, inventory_line_list, quant_obj, qty = self.env['product.product'], [], self.env['stock.quant'], 0
        for inventory_level in inventory_level_list:
            inventory_item = inventory_level.get('item') and extract_numeric_id(inventory_level.get('item').get('id'))
            quantities = inventory_level.get('quantities', [])
            available_qty = 0
            # Safely check if quantities exist before accessing index 0
            if quantities and isinstance(quantities, list):
                # Here quantities[0] static from list because we are only get available qty, so the response is list of dict.
                # If we get available and incoming
                # [
                #     {"name": "available", "quantity": 0 },
                #     { "name": "incoming", "quantity": 0 }
                # ]
                # If we get available so we get a static quantities[0]
                # [
                #     {"name": "available", "quantity": 0 }
                # ]
                available_qty = quantities[0].get('quantity', 0)
            listing_item_id = self.env['mk.listing.item'].search(
                [('product_id.is_storable', '=', True), ('product_id.tracking', '=', 'none'), ('is_listed', '=', True), ('inventory_item_id', '=', inventory_item),
                 ('mk_instance_id', '=', mk_instance_id.id)], limit=1)
            if listing_item_id:
                # Task: T7433 - Implemented import/export control using the ‘Allow Sync’ flag available in the listing  form view, supporting all flows to skip listings during synchronization between Odoo and Shopify.
                if listing_item_id.mk_listing_id.skip_listing_sync:
                    log_message = _("IMPORT STOCK: Skipped listing item %s(%s) as listing %s(%s) Sync is disabled.") % (
                        listing_item_id.name, listing_item_id.mk_id, listing_item_id.mk_listing_id.name, listing_item_id.mk_listing_id.mk_id)
                    self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': log_message}]})
                    continue
                odoo_product_id = listing_item_id.product_id
                if not any([line[2].get('product_id') == odoo_product_id.id for line in inventory_line_list]):
                    product_variant_ids += odoo_product_id
                    quant_obj.create_or_update_inventory_quant(shopify_location_id.location_id.id, odoo_product_id, available_qty,
                                                               name=f"Inventory ({mk_instance_id.name} on {datetime.now().strftime(DF)})",
                                                               auto_validate=mk_instance_id.is_validate_adjustment)
                    log_message = _("IMPORT STOCK: 📦 Product %s updated to %s quantity with %s location.") % (
                        odoo_product_id.display_name, available_qty, shopify_location_id.location_id.display_name)
                    self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_log_line_dict={'success': [{'log_message': log_message}]})
        return inventory_line_list, product_variant_ids

    def shopify_inventory_query_filter(self, last_stock_import_date):
        """
        Task: T5844 - Constructs a filter query for retrieving Shopify inventory updates after a specified date.
         Args:
            last_stock_import_date (datetime.date or datetime.datetime):
                If a `datetime.datetime` object is provided, it is converted to a `date` object before creating the filter.
        Returns:
            str: A filter query string formatted for use with Shopify's inventory API. The query will filter results based on the `updated_at` field.
        """
        filters = []
        if last_stock_import_date:
            if isinstance(last_stock_import_date, datetime):
                last_stock_import_date = last_stock_import_date.date()
            iso_from = last_stock_import_date.isoformat()
            filters.append(f"updated_at:>='{iso_from}'")

        return "".join(filters)

    def prepare_location_inventory_dict(self, locations_data, location_wise_inventory_dict, mk_instance_id, query_filter):
        """
        T5844: Processes Shopify inventory data directly into location-wise dictionary.

        Builds dict directly instead of creating intermediate list

        Args:
            locations_data (list): A list of location data from the Shopify API
            location_wise_inventory_dict (dict): Dictionary to populate (modified in-place)
            mk_instance_id (object): Marketplace instance for API calls
            query_filter (str): Query filter for pagination

        Returns:
            None (modifies location_wise_inventory_dict in-place)
        """
        for location_data in locations_data:
            location_id = location_data.get('id', '')
            location_mk_id = extract_numeric_id(location_id)

            # Initialize location key if not exists
            if location_mk_id not in location_wise_inventory_dict:
                location_wise_inventory_dict[location_mk_id] = []

            # Process initial inventory levels
            for inventory in location_data.get('inventoryLevels', {}).get('nodes', []):
                # Remove location info (already in dict key)
                inventory.pop('location', None)
                location_wise_inventory_dict[location_mk_id].append(inventory)

            # Handle pagination for this location
            page_info = location_data.get('inventoryLevels', {}).get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor', None)

            if not page_info or not has_next_page:
                continue

            # Fetch remaining pages for this location
            while True:
                try:
                    variable = {"id": location_id, "cursor": cursor, "queryFilter": query_filter}

                    res = mk_instance_id.execute_graphql_query(GET_INVENTORY_LOCATION_WISE_AFTER_CURSOR, variable)
                    remaining_levels = res.get('data', {}).get('location', [])

                    if remaining_levels:
                        for inventory in remaining_levels.get('inventoryLevels', {}).get('nodes', []):
                            inventory.pop('location', None)
                            location_wise_inventory_dict[location_mk_id].append(inventory)

                        page_info = remaining_levels.get('inventoryLevels', {}).get('pageInfo', {})
                        has_next_page = page_info.get('hasNextPage', False)
                        cursor = page_info.get('endCursor', None)

                        if not page_info or not has_next_page:
                            break
                except Exception as e:
                    raise MarketplaceException(f"Failed to fetch Shopify inventory location data: {str(e)}")

    def fetch_all_shopify_inventory_level(self, mk_instance_id, shopify_loc_mk_ids):
        """
        Task: T5844 - Fetches all inventory levels from Shopify for the specified locations.
        Args:
            mk_instance_id (object): An instance representing the current marketplace, containing necessary data such as the last stock import date.
            shopify_loc_mk_ids (list): A list of Shopify location IDs (numeric IDs) for which inventory levels need to be fetched.
        Returns: A dictionary where the keys are numeric location IDs and the values are lists of inventory level dictionaries.
        Raises:
            MarketplaceException: If there is an error while fetching the inventory data from Shopify.
        """
        cursor = None
        try:
            # Build location-wise dict directly from API response
            location_wise_inventory_dict = {}

            while True:
                # Dynamically set location variables
                location_variables = {
                    "locationIds": [f"gid://shopify/Location/{location_id}" for location_id in shopify_loc_mk_ids]
                }

                query_filter = self.shopify_inventory_query_filter(mk_instance_id.last_stock_import_date)

                variables = {
                    "cursor": cursor,
                    "inventoryQuery": query_filter,
                    **location_variables
                }

                res = mk_instance_id.execute_graphql_query(GET_INVENTORY_LOCATION_WISE, variables)
                user_errors = res and res.get('errors', [])
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Inventory Level: %(errors)s") % {'errors': joined_errors})

                locations_data = res and res.get('data', {}) and res.get('data', {}).get('nodes', [])

                # Process directly into location-wise dict (no intermediate list)
                self.prepare_location_inventory_dict(locations_data, location_wise_inventory_dict, mk_instance_id, query_filter)

                return location_wise_inventory_dict

        except MarketplaceException:
            raise
        except Exception as e:
            raise MarketplaceException(f"Error fetching Shopify inventory levels: {str(e)}")

    def shopify_import_stock(self, mk_instance_id):
        """
        T5844 - Imports inventory stock data from Shopify into Odoo.
        Args:
            mk_instance_id: Recordset of the marketplace instance
        Returns:
            True if the stock import completes successfully, False if validation fails or an exception occurs.
        """
        # T7417 : Fix issue where importing inventory creates a blank log when no listing items exist in Odoo
        mk_listing_ids = self.search([('mk_instance_id', '=', mk_instance_id.id), ('is_listed', '=', True)])

        if not mk_listing_ids:
            return True

        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
        mk_instance_id.connection_to_shopify()

        shopify_location_ids = self.env['shopify.location.ts'].search([('mk_instance_id', '=', mk_instance_id.id), ('is_import_export_stock', '=', True)])

        if not shopify_location_ids:
            log_message = _("IMPORT STOCK: Please enable at list one Shopify Location for import inventory from menu (Marketplaces > Shopify > Configuration > Locations).")
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': log_message}]})
            return False

        # Validate warehouse and location setup
        for shopify_location_id in shopify_location_ids:
            warehouse_id = shopify_location_id.order_warehouse_id or False
            odoo_location_id = shopify_location_id.location_id or False
            if not warehouse_id or not odoo_location_id:
                log_message = _("IMPORT STOCK: Warehouse / Location is not set for Shopify Location %s. Please set from Marketplace > Shopify > Locations") % shopify_location_id.name
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': log_message}]})
                return False

        shopify_loc_mk_ids = shopify_location_ids.mapped('shopify_location_id')

        # Get location-wise dict directly (no intermediate list conversion)
        location_wise_inventory_dict = self.fetch_all_shopify_inventory_level(mk_instance_id, shopify_loc_mk_ids)

        # Process each location's inventory
        for location_mk_id, inventory_level_list in location_wise_inventory_dict.items():
            try:
                shopify_location_id = self.env['shopify.location.ts'].search([('shopify_location_id', '=', location_mk_id), ('mk_instance_id', '=', mk_instance_id.id)])

                self.with_context(is_import_stock=True).create_process_inventory_adjustment(inventory_level_list, mk_instance_id, shopify_location_id, mk_log_id)
            except Exception as e:
                log_message = f"IMPORT STOCK: Error while Import Stock. ERROR: {e}"
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': log_message}]})
                return False

        if not mk_log_id.log_line_ids and not self.env.context.get('log_id', False):
            mk_log_id.unlink()

        mk_instance_id.last_stock_import_date = fields.Datetime.now()
        return True

    def prepare_update_shopify_variant_input(self, variants, operation_wizard, inline_variant_images=False):
        """
        Task: T5836 - Migrate Shopify to v19
        Task: T7468 - Raise a redirect warning for the location with a dynamic error message and open the corresponding location form view.
        While update/export shopify product, this method will prepare the variant input for query.
        Args:
            variants (list): List that holds dictionary of each variant input.
            operation_wizard (recordset): Recordset of mk.operation.
            inline_variant_images (bool): Default False keeps legacy non-bulk behavior (variant image
                is sent via the separate ADD_UPDATE_VARIANT_MEDIA call after the mutation). When True
                (bulk path), the variant's first image is attached inline via ProductVariantSetInput.file
                so productSet creates+links it in one bulk call.
        Returns:
            variants (list): List of dictionary which holds variant input.
        """
        is_set_price = operation_wizard.is_set_price
        is_update_product = operation_wizard.is_update_product
        mk_instance_id = self.mk_instance_id
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        # Task: T7653 - Removed is_third_party_location field.
        location_ids = self.env['shopify.location.ts'].search([('mk_instance_id', '=', mk_instance_id.id), ('is_import_export_stock', '=', True)])
        if not location_ids:
            error_msg = _("Error while trying to export Inventory, ERROR: Please enable at list one Shopify Location for import/export inventory.")
            mk_instance_id.show_shopify_location_redirect_warning(error_msg, location_ids)

        for listing_item_id in self.listing_item_ids.sorted(key='sequence'):
            variant_vals = {}
            if is_update_product:
                option_values = []
                # For non variant product
                if not self.product_tmpl_id.attribute_line_ids._without_no_variant_attributes():
                    option_values.append({'optionName': "Title", 'name': "Default Title"})
                else:
                    for attrs in listing_item_id.product_id.product_template_attribute_value_ids:
                        option_values.append({
                            "optionName": attrs.attribute_id.name,
                            "name": attrs.name,
                        })
                if option_values:
                    variant_vals["optionValues"] = option_values

                product_id = listing_item_id.product_id
                if listing_item_id.mk_id:
                    variant_vals.update({'id': f"gid://shopify/ProductVariant/{listing_item_id.mk_id}"})
                variant_vals.update({
                    'taxable': listing_item_id.is_taxable or False,
                    'inventoryItem': {
                        #  GraphQL doesn't provide inventory_management, we manage it by tracking field
                        'tracked': True if listing_item_id.inventory_management == 'shopify' else False,
                        # T7393 : Prepare Values for HS Code and Country of Origin
                        'countryCodeOfOrigin': product_id.country_of_origin.code if product_id.country_of_origin and product_id.country_of_origin.code else None,
                        'harmonizedSystemCode': product_id.hs_code if product_id.hs_code else None,
                        'measurement': {'weight': {
                            'unit': self.mapping_shopify_weight_name(listing_item_id.weight_unit, True),
                            'value': self._marketplace_convert_weight(product_id.weight, listing_item_id.weight_unit, reverse=True) or 0.0,
                        }
                        }
                    }
                })
                if listing_item_id.default_code:
                    variant_vals.update({'sku': listing_item_id.default_code})
                if listing_item_id.barcode or product_id.barcode:
                    variant_vals.update({'barcode': listing_item_id.barcode or product_id.barcode})
                if listing_item_id.continue_selling == 'CONTINUE':
                    variant_vals.update({'inventoryPolicy': 'CONTINUE'})
                else:
                    variant_vals.update({'inventoryPolicy': 'DENY'})

            if is_update_product and is_set_price:
                if mk_instance_id.is_export_product_sale_price:
                    listing_item_id.with_context(shopify_skip_auto_price_sync=True).create_or_update_pricelist_item(listing_item_id.product_id.lst_price, update_product_price=True,
                                                                                                                    reversal_convert=True)
                variant_price = mk_instance_id.pricelist_id.with_context(uom=listing_item_id.product_id.uom_id.id)._get_product_price(listing_item_id.product_id, 1.0)
                if not float_is_zero(variant_price, precision_digits=price_unit_prec):
                    variant_vals.update({'price': variant_price})
                if listing_item_id.mk_id:
                    variant_vals.update({'id': f"gid://shopify/ProductVariant/{listing_item_id.mk_id}"})

            # Task: T7609 - Bundle the variant's primary image into productSet (bulk path only).
            if inline_variant_images and variant_vals:
                for img in listing_item_id.image_ids[:1]:
                    if img.media_id:
                        variant_vals.update({
                            "file": {
                                "id": f"gid://shopify/MediaImage/{img.media_id}",
                                "alt": img.shopify_alt_text or '',
                                "contentType": "IMAGE"
                            }
                        })
                    elif img.image:
                        variant_vals.update({
                            'file': {
                                'originalSource': img._shopify_media_source(),
                                'alt': img.shopify_alt_text or '',
                                'contentType': 'IMAGE'
                            }
                        })

            if variant_vals:
                variants.append(variant_vals)
        return variants

    def filter_unused_shopify_option_input_values(self, productOptions, variants):
        """
        Task: T5836 - Migrate Shopify to v19
        Added - This method Filter productOptions values containing only the values that are actually used in the variants.
        Args:
            productOptions (list): A list of product options(attribute) input.
            variants (list):  A list of variants input.
        Returns:
            product_set_input (dict):  Filtered productOptions values containing only the values that are actually used in the variants.
            Any unused values (and entire unused options) will be removed.
        """
        # Collect all used option values grouped by optionName from variant.
        used_values = {}
        for v in variants:
            for opt in v.get("optionValues", []):
                used_values.setdefault(opt["optionName"], set()).add(opt["name"])

        filtered_options_input = []
        for opt in productOptions:
            name = opt["name"]
            if name in used_values:
                valid_vals = [val for val in opt["values"] if val["name"] in used_values[name]]
                if valid_vals:  # keep option only used in variant.
                    filtered_options_input.append({"name": name, "values": valid_vals})
        return filtered_options_input

    def prepare_update_shopify_options_input(self, product_set_input):
        """
        Task: T5836 - Migrate Shopify to v19
        While update/export shopify product, this method will prepare the attribute(option) input for 'UPDATE_PRODUCT_DATA' mutation.
        Args:
            product_set_input (dict): Dictionary that holds 'UPDATE_PRODUCT_DATA' input.
        Returns:
            product_set_input (dict): Updated `product_set_input` dictionary with the product options (attributes).
        """
        attribute_list = []
        # varint input
        variants = product_set_input.get('variants')

        # attribute_position = 1
        attribute_line_ids = self.product_tmpl_id.attribute_line_ids._without_no_variant_attributes()
        # Non variant product
        if not attribute_line_ids:
            attribute_list = [{'name': "Title", 'values': [{'name': "Default Title"}]}]
            product_set_input.update({'productOptions': attribute_list})
            return product_set_input

        for attribute_line_id in attribute_line_ids:
            attribute_id = attribute_line_id.attribute_id
            attribute_name_list = []
            for val in attribute_line_id.value_ids.mapped('name'):
                attribute_name_list.append({'name': val})
            attribute_list.append({'name': attribute_id.name, 'values': attribute_name_list})

        if attribute_list and variants:
            filtered_attribute_list = self.filter_unused_shopify_option_input_values(attribute_list, variants)
            product_set_input.update({'productOptions': filtered_attribute_list})
        return product_set_input

    def update_odoo_shopify_product(self, new_shopify_product):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        self.ensure_one()

        updated_at = convert_shopify_datetime_to_utc(new_shopify_product.get('updatedAt', ""))
        created_at = convert_shopify_datetime_to_utc(new_shopify_product.get('createdAt', ""))

        variants = new_shopify_product.get('variants', {}).get('nodes', [])
        listing_vals = {
            'listing_update_date': updated_at,
            'listing_create_date': created_at,
            'mk_id': str(extract_numeric_id(new_shopify_product.get('id', ""))),
            'is_listed': True,
            'number_of_variants_in_mk': len(variants),
        }
        self.write(listing_vals)

        for shopify_variant_dict in variants:
            variant_id = str(extract_numeric_id(shopify_variant_dict.get("id", "")))
            odoo_product_variant_id, shopify_variant_id = self.get_odoo_product_variant_and_listing_item(self.mk_instance_id, variant_id,
                                                                                                         shopify_variant_dict.get('barcode'), shopify_variant_dict.get('sku'))
            if shopify_variant_id:
                variant_vals = {
                    'mk_id': variant_id,
                    'inventory_item_id': str(extract_numeric_id(shopify_variant_dict.get('inventoryItem', {}).get('id', ''))),
                    'is_listed': True,
                    'item_update_date': convert_shopify_datetime_to_utc(shopify_variant_dict.get("updatedAt")),
                    'item_create_date': convert_shopify_datetime_to_utc(shopify_variant_dict.get("createdAt")),
                }
                # Task: T7796 - Write variant-level sales channels from export/update response
                resource_publications_v2 = shopify_variant_dict.get('resourcePublicationsV2', {})
                item_channels, shopify_sales_channel_ids_list = self.get_shopify_sales_channels(resource_publications_v2)
                if item_channels:
                    variant_vals['shopify_sales_channel_ids'] = item_channels['shopify_sales_channel_ids']
                shopify_variant_id.write(variant_vals)

        return True

    def update_listing_item_qty_in_shopify(self, mk_log_id, mk_log_line_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Task: T7468 - Raise a redirect warning for the location with a dynamic error message and open the corresponding location form view.
        Added - During Export/Update product in shopify this method will set the qty(Inventory) at specific location in shopify for specific product.
        Args:
            mk_log_id (recordSet): RecordSet of mk.log.
            mk_log_line_dict (dict): Dictionary that holds log line data.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id

        # Task: T7653 - Removed is_third_party_location field.
        location_ids = self.env['shopify.location.ts'].search([('mk_instance_id', '=', mk_instance_id.id), ('is_import_export_stock', '=', True)])
        if not location_ids:
            error_msg = _("Error while trying to export Inventory, ERROR: Please enable at list one Shopify Location for import/export inventory.")
            mk_instance_id.show_shopify_location_redirect_warning(error_msg, location_ids)

        for location in location_ids:
            if not location.export_location_ids:
                error_msg = _("Please set Warehouse and Location in the Shopify Location %s") % location.name
                mk_instance_id.show_shopify_location_redirect_warning(error_msg, location)

        filtered_listing_item_ids = self.listing_item_ids.filtered(lambda x: x.inventory_management == 'shopify')
        formated_listing_items = self.prepare_bulk_inventory_update_vals(mk_instance_id, filtered_listing_item_ids, location_ids, mk_log_id)
        self.with_context(manual_operation=True).run_bulk_shopify_inventory_update_perfect(mk_instance_id, formated_listing_items, mk_log_id, mk_log_line_dict)

    def _fetch_shopify_product_media(self):
        """
        Task: T5836 - Migrate Shopify to v19
            Fetch current product media from Shopify.
            Internally delegates to `_fetch_shopify_product_media_batch` so all four
            export/update flows share a single GraphQL operation (GET_PRODUCT_MEDIA_BATCH).
            Signature and return shape are preserved for callers.
         Returns:
            Response (list): List of shopify media.
        """
        self.ensure_one()
        if not self.mk_id:
            return []
        return self._fetch_shopify_product_media_batch().get(self.id, [])

    def _fetch_shopify_product_media_batch(self, batch_size=50):
        """
        Task: T7609 - Fetch Shopify product media for multiple listings in one batched GraphQL call
        instead of one request per listing. Used by bulk export/update flow to avoid N roundtrips.
        Args:
            batch_size (int): Max product GIDs sent per GraphQL request.
        Returns:
            dict: Mapping of {listing.id: [media_node, ...]}. Listings without a Shopify ID get an empty list.
        Raises:
            MarketplaceException: If listings belong to more than one Shopify instance.
        """
        media_by_listing_id = {l.id: [] for l in self}
        if not self:
            return media_by_listing_id

        mk_instance_id = self.mk_instance_id

        dict_of_shopify_id_to_odoo_id = {f"gid://shopify/Product/{l.mk_id}": l.id for l in self}
        list_of_mk_ids = list(dict_of_shopify_id_to_odoo_id.keys())

        for i in range(0, len(list_of_mk_ids), batch_size):
            mk_ids_list = list_of_mk_ids[i:i + batch_size]
            try:
                res = mk_instance_id.execute_graphql_query(GET_PRODUCT_MEDIA_BATCH, {"ids": mk_ids_list})
            except Exception as e:
                raise MarketplaceException(_(f"Batch media fetch Failed {e}")) from e
            user_errors = res.get('errors', []) if isinstance(res, dict) else {}
            if user_errors and isinstance(user_errors, list):
                self.mk_instance_id.handle_shopify_access_errors(user_errors, "Batch Media Fetch")
            nodes = (res or {}).get('data', {}).get('nodes') or []
            for node in nodes:
                if not node:  # null = product not found / deleted in Shopify
                    continue
                shopify_product_id = node.get('id', '')
                listing_id = dict_of_shopify_id_to_odoo_id.get(shopify_product_id)
                if listing_id is None:
                    continue
                media_by_listing_id[listing_id] = (node.get('media') or {}).get('nodes') or []
        return media_by_listing_id

    def _prepare_variable_update_listing_images_in_shopify(self, shopify_product_media, include_variant_images=False):
        """
        Task: T5836 - Migrate Shopify to v19
        Prepares the input for updating/exporting product-level images (listing images) in Shopify.
        Args:
            shopify_product_media (list): List of current product media from Shopify's GraphQL response.
            include_variant_images (bool): Default False keeps the legacy non-bulk behavior intact
                (variant-linked new images are skipped from product-level files because the separate
                variant mutation handles them). When True (bulk path), variant images are kept in
                product-level files and any variant-only images are appended too — Shopify's
                productSet rule requires every variant[].file reference to also appear in input.files.
        Returns:
            list: A list of dictionaries representing the formatted image input for the Shopify 'UPDATE_PRODUCT_DATA' mutation.
        """
        list_of_changed_media_list = []  # file input except either id or url.

        # Keep non-image media as-it-is (video, external_video, 3d)
        for media in shopify_product_media:
            media_type = media.get("mediaContentType")
            if media_type in ("VIDEO", "EXTERNAL_VIDEO", "MODEL_3D"):
                list_of_changed_media_list.append({
                    "id": media.get("id")
                })

        # Get media_id only for images from shopify response
        shopify_media_ids = {str(extract_numeric_id(m['id'])) for m in shopify_product_media if m.get('mediaContentType', '') == 'IMAGE'}
        seen_keys = set()
        for pos, img in enumerate(self.image_ids):
            # Set the media_id for existing images.
            if not img.media_id and shopify_media_ids:
                self.with_context(scope='export')._set_missing_shopify_media_ids(shopify_product_media)

            #  Skip if this image is linked to variant(s) and image is newly created → handle in variant mutation
            #  existing variant image removed from product level images(listing images) then it also remove from variant, so exclude only newly created variant images
            #  because it also added through the variant mutation(to remove redundancy exclude newly added variant image)
            if not include_variant_images and not img.media_id and img in self.listing_item_ids.mapped("image_ids"):
                continue

            entry = None
            # All images removed from shopify, but all new added from odoo
            if not shopify_product_media and img.image:
                entry = {
                    "alt": img.shopify_alt_text or "",
                    "originalSource": img._shopify_media_source(),
                    "contentType": "IMAGE"
                }
            else:
                # Update image variable
                if img.media_id in shopify_media_ids:
                    entry = {
                        'id': f"gid://shopify/MediaImage/{img.media_id}",
                        "alt": img.shopify_alt_text or "",
                        "contentType": "IMAGE"
                    }

                # Create new image variable
                elif not img.media_id and img.image:
                    entry = {
                        "alt": img.shopify_alt_text or "",
                        "originalSource": img._shopify_media_source(),
                        "contentType": "IMAGE"
                    }
            if entry:
                list_of_changed_media_list.append(entry)
                seen_keys.add(entry.get('id') or entry.get('originalSource'))

        # Shopify productSet rule: every variants[].file MUST also be present in input.files.
        # Append any variant image that isn't already covered by self.image_ids above.
        if include_variant_images:
            for variant in self.listing_item_ids:
                for img in variant.image_ids[:1]:
                    if not img.image and not img.media_id:
                        continue
                    # Same key the product-level loop above stored in seen_keys, staged link included -
                    # comparing an Odoo URL against a staged one would append the image a second time.
                    key = f"gid://shopify/MediaImage/{img.media_id}" if img.media_id else img._shopify_media_source()
                    if key in seen_keys:
                        continue
                    if img.media_id:
                        list_of_changed_media_list.append({'id': key, 'alt': img.shopify_alt_text or '', 'contentType': 'IMAGE'})
                    else:
                        list_of_changed_media_list.append({'originalSource': img._shopify_media_source(), 'alt': img.shopify_alt_text or '', 'contentType': 'IMAGE'})
                    seen_keys.add(key)
        return list_of_changed_media_list

    def _prepare_variable_update_listing_item_images_in_shopify(self, shopify_variant_res):
        """
        Task: T5836 - Migrate Shopify to v19
        Prepares the input for updating/exporting variant-level images (listing item images) in Shopify.
        Args:
            shopify_variant_res (list): Shopify GraphQL response containing variants response with their media.
        Returns:
            - list: Variant image update/create inputs (for linking variants to images).
            - list: New media inputs (for creating new media objects in Shopify).
        """
        # Create a mapping from shopify variant media response: {variant_id: [image media id]}
        shopify_variant_media_map = {
            str(extract_numeric_id(variant.get('id'))): [str(extract_numeric_id(m.get('id'))) for m in variant.get('media', {}).get('nodes', []) if m.get('mediaContentType', '') == 'IMAGE']
            for variant in shopify_variant_res}

        variant_media_inputs = []
        variant_input = []

        for variant in self.listing_item_ids:
            shopify_variant_id = variant.mk_id
            media_ids_for_variant = shopify_variant_media_map.get(shopify_variant_id, [])
            for img in variant.image_ids:
                # update listing item image
                if img.media_id and str(img.media_id) in media_ids_for_variant:
                    variant_input.append({
                        "id": f"gid://shopify/ProductVariant/{shopify_variant_id}",
                        "mediaId": f"gid://shopify/MediaImage/{img.media_id}"
                    })
                # create new listing item image
                elif not img.media_id:
                    media_source = img._shopify_media_source()
                    variant_input.append({
                        "id": f"gid://shopify/ProductVariant/{shopify_variant_id}",
                        "mediaSrc": media_source,
                    })
                    variant_media_inputs.append({
                        "originalSource": media_source,
                        "alt": img.shopify_alt_text or "",
                        "mediaContentType": "IMAGE"
                    })
        return variant_input, variant_media_inputs

    def _update_listing_item_images_in_shopify(self, variant_input, variant_media_inputs):
        """
        Task: T5836 - Migrate Shopify to v19
        Executes the Shopify mutation to update variant-level images (listing item images) in shopify.
        Args:
            variant_input (list): Variant-level image inputs for update/create (links variant to image).
            variant_media_inputs (list): New media inputs to create Shopify media objects.
        Returns:
            dict | bool: Shopify GraphQL API response if successful, otherwise False when errors occur.
        """
        variables = {
            "productId": f"gid://shopify/Product/{self.mk_id}",
            "variants": variant_input,
            "media": variant_media_inputs
        }

        res = self.mk_instance_id.execute_graphql_query(ADD_UPDATE_VARIANT_MEDIA, variables)
        user_errors = res and res.get('data', {}) and res.get('data', {}).get('productVariantsBulkUpdate', {}).get('userErrors', [])
        for err in user_errors:
            message = err.get("message")
            log_message = _("❌ Listing Item Image update failed for Product (%s) for Shopify Instance '%s': %s") % (self.mk_id, self.mk_instance_id.name, message)
            _logger.error(log_message)
            return False

        return res

    def update_shopify_product_variant_image_ts(self, updated_shopify_product_res):
        """
        Task: T5836 - Migrate Shopify to v19
        Added this method to export/update variant images in shopify.
        Args:
            updated_shopify_product_res (dict): Dictionary containing the updated product detail.
        """
        # updated_shopify_product_res response return only media_id if updated (it doesn't include the updated media)
        if updated_shopify_product_res:
            shopify_variant_res = updated_shopify_product_res.get('variants', {}).get('nodes', [])

            # prepare a variable to update listing item images
            variant_input, variant_media_inputs = self._prepare_variable_update_listing_item_images_in_shopify(shopify_variant_res)

            # if variant having image
            if variant_input or variant_media_inputs:
                # call api that update the listing item images
                self._update_listing_item_images_in_shopify(variant_input, variant_media_inputs)

    def _set_shopify_media_ids_for_new_images(self, shopify_product_media_after_update):
        """
        Task: T5836 - Migrate Shopify to v19
        Set media_id for newly created images in (listing + listing items).
        Uses the Shopify product media response which includes product and variant images to find
        matching images by comparing hashes.
        Args:
            shopify_product_media_after_update (list): Shopify GraphQL response containing product media (including variant images).
        Returns:
            bool: True if processing is successful, False if an error occurs.
        """
        try:
            mk_listing_image = self.env['mk.listing.image']
            # Need to add listing item bcz in already imported listing newly image does not have listing id.
            new_images = mk_listing_image.search([('media_id', '=', False), '|', ('mk_listing_id', '=', self.id), ('mk_listing_item_ids', 'in', self.listing_item_ids.ids)])
            if not new_images:
                return True

            # Build hash -> [media_id] map from Shopify response.
            # Download + md5 touch NO ORM/cursor -> safe to run in threads; the network wait
            # dominates, so parallelize it. The ORM write stays in the main thread below.
            def _hash_shopify_media(media):
                media_id = str(extract_numeric_id(media.get("id", "")))
                image_url = media.get("image", {}).get("url") if media.get('image') != None else False
                if not (media_id and image_url):
                    return None
                # Task: T7609 - The ORIGINAL must be downloaded, never a `?width=` thumbnail. Shopify
                # resamples a thumbnail with its own image pipeline: its pixels match neither the original
                # nor any local resize of it, so an exact hash would never find them. The peak memory of
                # the step is bounded by SHOPIFY_MEDIA_HASH_WORKERS instead, and _shopify_image_pixel_md5
                # hashes the decoded image band by band rather than as one extra full-size buffer.
                resp = requests.get(f"{image_url}", stream=True, verify=True, timeout=10)
                if resp.status_code != 200:
                    return None
                image_hash = self._shopify_image_pixel_md5(resp.content)
                return (image_hash, media_id) if image_hash else None

            # Task: T7609 - Shopify processes media asynchronously, so only READY media exposes the CDN
            # copy this matching hashes. PROCESSING media is simply not finished yet and a later run picks
            # it up, while FAILED media carries the reason Shopify could not fetch the file - log it,
            # otherwise the image silently stays without a media_id. Media responses that carry no status
            # at all (variant mutation) keep going through the hashing as before.
            ready_media = []
            for media in shopify_product_media_after_update:
                media_status = media.get('status', 'READY')
                if media_status == 'READY':
                    ready_media.append(media)
                elif media_status == 'FAILED':
                    media_errors = "; ".join(error.get('details') or error.get('code') or '' for error in media.get('mediaErrors') or [])
                    _logger.warning("Shopify could not process media %s of listing %s: %s", media.get('id', ''), self.name, media_errors)

            # Task: T7609 - Hash the Odoo side FIRST, from the filestore: it costs no network, and it is
            # what makes the downloads below skippable. The binaries are read in one attachment search
            # instead of one query and one filestore read per record. A key holds the LIST of images that
            # share it, because two Odoo images may legitimately hold the same binary.
            contents = new_images._shopify_read_image_binaries(new_images.ids)
            image_ids_by_hash = {}
            for img_rec in new_images:
                content = contents.get(img_rec.id)
                if not content:
                    continue
                local_hash = self._shopify_image_pixel_md5(content)
                if local_hash:
                    image_ids_by_hash.setdefault(local_hash, []).append(img_rec.id)

            # Task: T7609 - Only media that no image of this listing already carries can belong to a new
            # image, so every other one is dropped before a single byte is downloaded. On an update of a
            # product whose media are already mapped this leaves just the handful that were created by
            # this run, instead of re-downloading the whole gallery.
            used_media_ids = set((self.image_ids | self.listing_item_ids.image_ids).mapped('media_id'))
            candidate_media = [media for media in ready_media if str(extract_numeric_id(media.get('id', ''))) not in used_media_ids]

            # Match Odoo new images with Shopify images. The candidates are downloaded one pool at a time
            # and the loop stops as soon as every new image has found its media, so a product carrying far
            # more media than the run created never downloads the remainder.
            image_ids_by_media_id = {}
            downloaded_media_count = 0
            pending_image_count = sum(len(image_ids) for image_ids in image_ids_by_hash.values())
            with ThreadPoolExecutor(max_workers=SHOPIFY_MEDIA_HASH_WORKERS) as executor:
                for index in range(0, len(candidate_media), SHOPIFY_MEDIA_HASH_WORKERS):
                    if not pending_image_count:
                        break
                    media_pool = candidate_media[index:index + SHOPIFY_MEDIA_HASH_WORKERS]
                    downloaded_media_count += len(media_pool)
                    for result in executor.map(_hash_shopify_media, media_pool):
                        if not result:
                            continue
                        image_hash, shopify_media_id = result
                        image_ids = image_ids_by_hash.get(image_hash) or []
                        if not image_ids or shopify_media_id in used_media_ids:
                            continue
                        used_media_ids.add(shopify_media_id)
                        image_ids_by_media_id.setdefault(shopify_media_id, []).append(image_ids.pop(0))
                        pending_image_count -= 1

            for shopify_media_id, image_ids in image_ids_by_media_id.items():
                new_images.browse(image_ids).write({"media_id": shopify_media_id})

            _logger.info("Matched %s of %s new image(s) of listing %s by downloading %s media of the %s READY on Shopify.",
                         len(image_ids_by_media_id), len(new_images), self.name, downloaded_media_count, len(ready_media))
            return True

        except Exception as e:
            _logger.error("Error while setting Shopify media IDs for new images: %s", str(e))
            return False

    def prepare_update_vals_for_shopify_template_input(self, product_set_input):
        """
        Task: T5836 - Migrate Shopify to v19
        Prepares the product template input values for the Shopify `UPDATE_PRODUCT_DATA` mutation.
        That Updates/Export the basic product details such as title, description, tags, type, category, and vendor.
        Args:
            product_set_input (dict): Dictionary that holds 'UPDATE_PRODUCT_DATA' input.
        Returns:
            dict: Updated `product_set_input` dictionary with product level input values.
        """
        product_set_input.update({
            'descriptionHtml': self.description or '',
            'title': self.name,
            'tags': [tag.name or '' for tag in self.tag_ids],
            'productType': self.shopify_product_type_id.name or '',
            'category': f"gid://shopify/TaxonomyCategory/{self.shopify_product_category_id.shopify_category_id}" if self.shopify_product_category_id.shopify_category_id else None,
        })
        if self.product_tmpl_id.seller_ids:
            product_set_input.update({'vendor': self.product_tmpl_id.seller_ids[0].display_name})
        return product_set_input

    def _sync_shopify_product_publication(self, operation_wizard, mk_instance_id, mk_log_line_dict):
        """
        Task: T7628 - Implemented logic to remove missing Shopify Sales Channels from Odoo when they no longer exist in Shopify during sales channel updates.
        Task: T5836 - Migrate Shopify to v19
        Added - During product export or update to Shopify, this method manages on specific sales channels and updates listing fields (listing_update_date, shopify_sales_channel_ids) accordingly.
        Args:
            operation_wizard (recordset): Recordset of mk.operation.
            mk_instance_id (recordset): Recordset of mk.instance.
            mk_log_line_dict (dict): Dictionary that holds log line data.
        """
        selected_sales_channels = operation_wizard.shopify_sales_channel_ids
        publication_ids = selected_sales_channels.mapped('sales_channel_id')
        # Prepare variables for query
        input_list = [{"publicationId": f"gid://shopify/Publication/{sales_channel_id}"} for sales_channel_id in publication_ids]
        variables = {"productId": f"gid://shopify/Product/{self.mk_id}", "input": input_list}

        # publish/unpublish product
        is_publishing = operation_wizard.is_publish_or_unpublish
        query = PUBLISH_PRODUCT if is_publishing else UNPUBLISH_PRODUCT
        log_message_word = "publish" if is_publishing else "unpublish"

        res = mk_instance_id.execute_graphql_query(query, variables=variables)
        # Identify mutation name to get its error
        update_sales_channel_response_key = 'publishablePublish' if is_publishing else 'publishableUnpublish'
        user_errors = res and res.get("data", {}).get(update_sales_channel_response_key, {}).get("userErrors", [])

        if user_errors:
            # Task: T7628 - Delegate to the shared handler on shopify.sales.channels.ts so the
            # per-record and the bulk publish flow interpret these userErrors with one implementation.
            _missing_channels, is_record_unlinked = self.env['shopify.sales.channels.ts'].handle_shopify_publication_user_errors(user_errors, selected_sales_channels, self, mk_log_line_dict,
                                                                                                                                 'EXPORT/UPDATE LISTING', mk_instance_id=mk_instance_id)
            if is_record_unlinked:
                return True

        if not user_errors:
            variables = {"productId": f"gid://shopify/Product/{self.mk_id}"}
            res = mk_instance_id.execute_graphql_query(GET_SPECIFIC_PRODUCT_DATA, variables)
            user_errors = res.get('errors', [])
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Product: %(errors)s") % {'errors': joined_errors})

            shopify_product = res.get('data', {}).get('product', {}) if isinstance(res, dict) else {}

            updated_at = convert_shopify_datetime_to_utc(shopify_product.get('updatedAt', ""))
            shopify_sales_channel_ids, shopify_sales_channel_ids_list = self.get_shopify_sales_channels(shopify_product.get('resourcePublications', {}))
            listing_vals = {
                'listing_update_date': updated_at,
            }
            shopify_sales_channel_ids and listing_vals.update(shopify_sales_channel_ids)
            is_published = self.shopify_check_is_listing_published(shopify_sales_channel_ids_list)
            listing_vals.update({'is_published': is_published})
            self.write(listing_vals)
            mk_log_line_dict['success'].append({'log_message': _('EXPORT/UPDATE LISTING: Product %s(%s) has been %sed successfully') % (self.name, self.mk_id, log_message_word)})

    def shopify_export_product_limit(self):
        """
        Checking for maximum product export limit to prevent user's process.

        :return: True if selected product isn't more than limit.
        :rtype: bool
        :raise MarketplaceException:
                * if selected products are more than given limit.
        """
        max_limit = 1000
        if self and len(self) > max_limit:
            raise MarketplaceException(_("System will not permits to send out more then 80 items all at once. Please select just 80 items for export."))
        return True

    def shopify_execute_export_or_update_listing_to_mk(self, mk_instance_id, variables, mk_log_line_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Added - Executes the Shopify `UPDATE_PRODUCT_DATA` mutation to either export a new product or update an existing product on Shopify.
        Handles error cases returned by Shopify and logs them accordingly in Odoo.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            variables (dict): Variables to pass to the GraphQL mutation.
            mk_log_line_dict (dict): Dictionary that holds log line data.
        Returns:
            tuple:
                - bool: True if the update/export succeeded, False otherwise.
                - dict: The Shopify API response.
        """
        res = mk_instance_id.execute_graphql_query(UPDATE_PRODUCT_DATA, variables)
        user_errors = res.get('errors', [])
        if user_errors and isinstance(user_errors, list):
            err_messages = [e.get('message', str(e)) for e in user_errors]
            joined_errors = ", ".join(err_messages)
            raise MarketplaceException(_("⚠️ Failed to fetch Shopify Product: %(errors)s") % {'errors': joined_errors})

        user_errors = res and res.get("data", {}).get("productSet", {}).get("userErrors", []) if res.get("data", {}).get("productSet", {}) else []
        errors = res.get('errors') or []
        if not user_errors and not errors:
            return True, res

        product_set_input = variables.get("input", {})
        for err in user_errors:
            code = err.get("code")
            message = err.get("message")

            if code == "INVALID_METAFIELD_VALUE_FOR_LINKED_OPTION":
                # When all attribute removed in odoo and try to update in shopify
                if any(i.get('name') == 'Title' for i in product_set_input.get('productOptions', [])):
                    log_message = _(
                        "Product(%s) update failed for Shopify Instance %s: All product attributes were removed. Shopify requires at least one attribute value for product. Please add at least one attribute and try again.") % (
                                      self.mk_id, mk_instance_id.name)
                else:
                    # Options are included, but not properly variant included.
                    log_message = _(
                        "Product(%s) update failed for Shopify Instance %s: The option was included, but no variant uses it. Please create a variant with this attribute before updating Shopify.") % (
                                      self.mk_id, mk_instance_id.name)
                mk_log_line_dict['error'].append({'log_message': 'UPDATE/EXPORT LISTING: ' + log_message})
            elif code == "NOT_FOUND":
                self.sudo().unlink()
                return False, res
            else:
                log_message = _("Product(%s) update failed for Shopify Instance %s: %s") % (self.mk_id, mk_instance_id.name, message)
                mk_log_line_dict['error'].append({'log_message': 'UPDATE/EXPORT LISTING: ' + log_message})

        for err in errors:
            log_message = err.get('message')
            _logger.error(f"Error while update/export product {self.name}({self.mk_id}): {log_message}")

        return False, res

    def shopify_export_listing_to_mk(self, operation_wizard):
        """
        Task: T6290 - Added the functionality to update metafield in shopify.
        Task: T5836 - Migrate Shopify to v19
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.
        Migrated from Shopify REST API to GraphQL API.
        Raise a validation error when, after migration, the user first tries to export listings without assigning sales channels to all listings.
        """
        mk_instance_id = self.mk_instance_id
        if mk_instance_id.need_sync_shopify_sales_channels:
            error_msg = _(
                "You cannot perform listing operations on the instance %s right now. Since you are migrating from an older version to a newer one, please click the 'Apply Sales Channels To Existing Listings' button and keep pressing it until the button disappears. This ensures that sales channels are applied to all existing listings.\n") % mk_instance_id.name
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)

        # Added this validation because if a user forgot to set Warehouse and Stock Location in the Shopify Location, then as per the code sequence product will be created.
        # However, while going to export qty, it will raise the error and Odoo product didn't update even after it is created in Shopify.
        # Task: T7653 - Removed is_third_party_location field.
        location_ids = self.env['shopify.location.ts'].search([('mk_instance_id', '=', mk_instance_id.id), ('is_import_export_stock', '=', True)])
        if not location_ids:
            error_msg = _("Please enable at list one Shopify Location for import/export inventory.")
            mk_instance_id.show_shopify_location_redirect_warning(error_msg, location_ids)
        for shopify_location_id in location_ids:
            warehouse_id = shopify_location_id.order_warehouse_id or False
            if not warehouse_id:
                error_msg = _("Please set Warehouse and Location in the Shopify Location %s.") % shopify_location_id.name
                mk_instance_id.show_shopify_location_redirect_warning(error_msg, shopify_location_id)

        mk_instance_id.connection_to_shopify()
        # Task: T7609 - Trigger bulk Shopify export when 3 or more listings are selected.
        if len(self) > 3:
            return self.with_context(operation_type_for_listing='export').bulk_export_update_listings_to_shopify(operation_wizard, location_ids, operation_type='export')

        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})

        for listing_id in self:
            if not listing_id.product_tmpl_id._check_barcode_and_sku(listing_id.mk_instance_id):
                raise MarketplaceException(
                    _("Product : %(name)s Internal Reference (SKU) or Barcode is missing in some product(s)! \n\nPlease set the unique internal reference or Barcode in all variants as per your Instance Configuration.") % {
                        'name': listing_id.name})

            try:
                product_set_input = {}
                variants = []

                if operation_wizard.is_set_images:
                    # First set listing level images (in case of export pass empty list)
                    listing_media_input = listing_id._prepare_variable_update_listing_images_in_shopify([])
                    product_set_input.update({'files': listing_media_input})

                listing_id.prepare_update_vals_for_shopify_template_input(product_set_input)

                listing_id.prepare_update_shopify_variant_input(variants, operation_wizard)

                if variants:
                    product_set_input.update({'variants': variants})

                listing_id.prepare_update_shopify_options_input(product_set_input)

                variables = {"input": product_set_input, "synchronous": True, "identifier": None}

                success, final_res = listing_id.shopify_execute_export_or_update_listing_to_mk(mk_instance_id, variables, mk_log_line_dict)

                if success:
                    shopify_product = final_res.get('data', {}).get('productSet', {}).get('product', {})
                    if not shopify_product:
                        _logger.warning(f"Successfully product: {listing_id.name} created, but no product data was returned in the response.")
                    else:
                        product_id = extract_numeric_id(shopify_product.get('id', ''))
                        mk_log_line_dict['success'].append({'log_message': _("EXPORT LISTING: Successfully created product %s(%s)") % (listing_id.name, product_id)})

                        listing_id.update_odoo_shopify_product(shopify_product)

                        if operation_wizard.is_set_quantity and listing_id.product_tmpl_id.is_storable:
                            # Use a separate dict for quantity sync. The bulk inventory worker flushes its
                            # own entries per batch; re-passing the outer dict would cause those entries
                            # to be flushed twice when the trailing _handle_shopify_log_creation runs.
                            qty_log_line_dict = {'error': [], 'success': []}
                            listing_id.update_listing_item_qty_in_shopify(mk_log_id, qty_log_line_dict)

                        if operation_wizard.is_set_images:
                            # export listing item images after product creation
                            listing_id.update_shopify_product_variant_image_ts(shopify_product)
                            time.sleep(
                                1)  # Shopify may take a moment to finish processing images exported from Odoo. Adding a short delay ensures the image is retrieved correctly in the subsequent response.

                            # At least one image does not have media_id
                            if not all(listing_id.image_ids.mapped('media_id')):
                                shopify_product_media_after_update = listing_id._fetch_shopify_product_media()
                                listing_id._set_shopify_media_ids_for_new_images(shopify_product_media_after_update)

                        # After creating the product set sales channel
                        if operation_wizard.shopify_sales_channel_ids:
                            listing_id._sync_shopify_product_publication(operation_wizard, mk_instance_id, mk_log_line_dict)

                        listing_id.shopify_update_listing_metafields_to_mk(mk_log_id)
                else:
                    mk_log_line_dict['error'].append({'log_message': _('EXPORT LISTING: Failed to set product details for product %s') % listing_id.name})
            except Exception as e:
                _logger.error(f"An error occurred while export the product details !! {e}")
                if mk_log_id and mk_log_line_dict:
                    mk_log_line_dict['error'].append({'log_message': _('EXPORT LISTING: Failed to create product %s') % listing_id.name})
            self.env.cr.commit()
        if mk_log_line_dict:
            self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
        if mk_log_id.exists():
            return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
        return True

    def shopify_update_listing_to_mk(self, operation_wizard):
        """
        Task: T6290 - Added the functionality to update metafield in shopify.
        Task: T7042 - Shopify Product Import with different Structure.
        Task: T5836 - Migrate Shopify to v19
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Task: T7468 - Raise a redirect warning for the location and instance with a dynamic error message and open the corresponding location form view.
        Migrated from Shopify REST API to GraphQL API.
        Raise a validation error when, after migration, the user first tries to update listings without assigning sales channels to all listings.
        """
        mk_instance_id = self.mk_instance_id
        is_set_quantity = operation_wizard.is_set_quantity
        is_set_price = operation_wizard.is_set_price
        if mk_instance_id.need_sync_shopify_sales_channels:
            self.show_shopify_sales_channel_action_required_warning(mk_instance_id)

        location_ids = False
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
                    error_msg = _("Please set Warehouse and Location in the Shopify Location %s.") % shopify_location_id.name
                    mk_instance_id.show_shopify_location_redirect_warning(error_msg, shopify_location_id)
        if len(self) > 3:
            return self.with_context(operation_type_for_listing='update').bulk_export_update_listings_to_shopify(operation_wizard, location_ids, operation_type='update')

        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
        mk_log_line_dict = self.env.context.get('mk_log_line_dict', {'error': [], 'success': []})

        mk_instance_id.connection_to_shopify()
        for listing_batch in tools.split_every(50, self, piece_maker=list):
            for listing_id in listing_batch:
                # Task: T7433 - Implemented import/export control using the ‘Allow Sync’ flag available in the listing  form view, supporting all flows to skip listings during synchronization between Odoo and Shopify.
                if listing_id.skip_listing_sync:
                    log_message = _("UPDATE LISTING: Skipped %s(%s) Sync is disabled.") % (listing_id.name, listing_id.mk_id)
                    mk_log_line_dict['error'].append({'log_message': log_message})
                    continue
                try:
                    product_set_input = {}
                    variants = []

                    if operation_wizard.is_set_images:
                        # First set listing level images (in case of update pass shopify media response)
                        shopify_product_media = listing_id._fetch_shopify_product_media()
                        # Prepare a variable for update the listing image
                        listing_media_inputs = listing_id._prepare_variable_update_listing_images_in_shopify(shopify_product_media)
                        product_set_input.update({'files': listing_media_inputs})

                    # Process only price update
                    if is_set_price and not operation_wizard.is_update_product:
                        price_log_line_dict = {'error': [], 'success': []}
                        listing_item_ids = listing_id.listing_item_ids
                        listing_id.with_context(is_manual_update_price=True).shopify_update_product_price(mk_instance_id, listing_item_ids=listing_item_ids, mk_log_id=mk_log_id,
                                                                                                          mk_log_line_dict=price_log_line_dict)
                        # The listing is removed from Odoo when Shopify reports the product as missing, so stop processing it further.
                        if not listing_id.exists():
                            continue

                    if operation_wizard.is_update_product:
                        listing_id.prepare_update_vals_for_shopify_template_input(product_set_input)

                    listing_id.prepare_update_shopify_variant_input(variants, operation_wizard)
                    if variants:
                        product_set_input.update({'variants': variants})

                    if operation_wizard.is_update_product:
                        listing_id.prepare_update_shopify_options_input(product_set_input)

                    if operation_wizard.shopify_sales_channel_ids:
                        listing_id._sync_shopify_product_publication(operation_wizard, mk_instance_id, mk_log_line_dict)

                    if (operation_wizard.is_update_product or operation_wizard.is_set_price or operation_wizard.is_set_images) and product_set_input:
                        variables = {"input": product_set_input, "synchronous": True, "identifier": {"id": f"gid://shopify/Product/{listing_id.mk_id}"}}
                        success, final_res = listing_id.shopify_execute_export_or_update_listing_to_mk(mk_instance_id, variables, mk_log_line_dict)
                        if not listing_id.exists():
                            continue
                        if success:
                            shopify_product = final_res.get('data', {}).get('productSet', {}).get('product', {})
                            if not shopify_product:
                                _logger.warning(f"Product update for {listing_id.mk_id} succeeded, but no product data was returned in the response.")
                            else:
                                listing_id.update_odoo_shopify_product(shopify_product)

                            if operation_wizard.is_set_images:
                                # Export listing item images after product creation
                                listing_id.update_shopify_product_variant_image_ts(shopify_product)
                                time.sleep(
                                    1)  # Shopify may take a moment to finish processing images exported from Odoo. Adding a short delay ensures the image is retrieved correctly in the subsequent response.

                                # Set media_id in newly created images.
                                if not all(listing_id.image_ids.mapped('media_id')):
                                    shopify_product_media_after_update = listing_id._fetch_shopify_product_media()
                                    listing_id._set_shopify_media_ids_for_new_images(shopify_product_media_after_update)
                            mk_log_line_dict['success'].append({'log_message': _('UPDATE LISTING: Successfully updated product %s(%s).') % (listing_id.name, listing_id.mk_id)})
                        else:
                            mk_log_line_dict['error'].append({'log_message': _('UPDATE LISTING: Failed to updated product details for product %s(%s)') % (listing_id.name, listing_id.mk_id)})

                    if is_set_quantity and listing_id.product_tmpl_id.is_storable:
                        # Use a separate dict for quantity sync. The bulk inventory worker flushes its own
                        # entries via _handle_shopify_log_creation per batch, so re-passing the outer dict
                        # would cause those entries to be flushed twice when the trailing
                        # _handle_shopify_log_creation runs at the end of this method.
                        qty_log_line_dict = {'error': [], 'success': []}
                        listing_id.update_listing_item_qty_in_shopify(mk_log_id, qty_log_line_dict)
                        # The listing is removed from Odoo when Shopify reports the product as missing, so stop processing it further.
                        if not listing_id.exists():
                            continue

                    listing_id.shopify_update_listing_metafields_to_mk(mk_log_id=mk_log_id)

                except Exception as e:
                    log_message = f"An error occurred while update the product on shopify !! {e}"
                    _logger.error(log_message)
                    if not mk_log_line_dict and mk_log_id:
                        mk_log_id.unlink()
                    elif listing_id.exists() and mk_log_id and mk_log_line_dict:
                        mk_log_line_dict['error'].append({'log_message': _('UPDATE LISTING: %s') % log_message})
            self.env.cr.commit()

        if mk_log_line_dict:
            # mk_log_id may have been deleted by a helper that flushed empty; use what was written.
            mk_log_id = self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
        if mk_log_id.exists():
            return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
        return True

    def get_mk_listing_item(self, mk_instance_id):
        """
        Task: T6994 - Retrieves MK listing items for a given MK instance, filtered by stock movement states and stock update date.
            Executes two SQL queries to fetch the data and includes BOM filtering if the 'mrp' module is installed.
        Args:
            mk_instance_id(recordset): The record of the mk.instance model.
        Returns:
            Returns unique MK listing item IDs for a given MK instance, filtered by stock movement states and the stock update date.
        """
        if mk_instance_id and mk_instance_id.marketplace == 'shopify':
            operation_wizard = self.env.context.get('operation_wizard', False)
            if operation_wizard and operation_wizard.last_update_stock_date:
                where_clause = "sm.write_date >= %s AND "
            elif not operation_wizard and mk_instance_id.last_stock_update_date:
                where_clause = "sm.write_date >= %s AND "
            else:
                return self.env['mk.listing.item'].search([('mk_instance_id', '=', mk_instance_id.id), ('is_listed', '=', True)])

            query = """
                    SELECT mkli.id
                    FROM stock_move sm
                    JOIN mk_listing_item mkli ON sm.product_id = mkli.product_id 
                        AND mkli.is_listed = TRUE 
                        AND mkli.mk_instance_id = %s
                    WHERE {} state IN ('partially_available', 'assigned', 'done', 'cancel') 
                        AND sm.company_id = %s
            """.format(where_clause)
            if operation_wizard and operation_wizard.last_update_stock_date:
                self.env.cr.execute(query, tuple([mk_instance_id.id, operation_wizard.last_update_stock_date, mk_instance_id.company_id.id]))
            else:
                self.env.cr.execute(query, tuple([mk_instance_id.id, mk_instance_id.last_stock_update_date, mk_instance_id.company_id.id]))
            result = [int(i[0]) for i in self.env.cr.fetchall()]

            mrp = mk_instance_id._is_module_installed('mrp')
            if mrp:
                query = """
                SELECT mkli.id
                FROM (
                    SELECT sm.product_id
                    FROM stock_move AS sm
                    WHERE {} sm.company_id = %s
                      AND sm.state IN ('partially_available', 'assigned', 'done', 'cancel')
                    GROUP BY sm.product_id
                ) AS filtered_moves
                JOIN mrp_bom_line AS mbl ON filtered_moves.product_id = mbl.product_id
                JOIN mrp_bom AS mbom ON mbl.bom_id = mbom.id
                JOIN product_product AS pp ON mbom.product_tmpl_id = pp.product_tmpl_id
                JOIN mk_listing_item AS mkli ON pp.id = mkli.product_id AND mkli.is_listed = true AND mkli.mk_instance_id = %s
                GROUP BY mkli.id;
                """.format(where_clause)
                if operation_wizard and operation_wizard.last_update_stock_date:
                    params = [operation_wizard.last_update_stock_date, mk_instance_id.company_id.id, mk_instance_id.id] if operation_wizard.last_update_stock_date else [
                        mk_instance_id.company_id.id, mk_instance_id.id]
                else:
                    params = [mk_instance_id.last_stock_update_date, mk_instance_id.company_id.id, mk_instance_id.id] if mk_instance_id.last_stock_update_date else [
                        mk_instance_id.company_id.id, mk_instance_id.id]
                self.env.cr.execute(query, tuple(params))
                result += [int(i[0]) for i in self.env.cr.fetchall()]
            return list(set(result))
        else:
            return super(MkListing, self).get_mk_listing_item(mk_instance_id)

    def prepare_data_for_shopify_inventory(self, variants, shopify_location_ids, mk_instance_id):
        """
        Task: T7609 - Build location-wise inventory quantities for Shopify variant payload and
        attach them in-place to each variant dict. Skips variants not managed by Shopify.
        Args:
            variants (list): Shopify variant payload list (modified in place).
            shopify_location_ids (recordset): Shopify location mapping records.
            mk_instance_id (record): Marketplace instance used for stock field lookup.
        Returns:
            None
        """
        self.ensure_one()
        sorted_listing_items_ids = self.listing_item_ids.sorted(key='sequence')
        for idx, variant_vals in enumerate(variants):
            if idx >= len(sorted_listing_items_ids):
                break
            listing_item = sorted_listing_items_ids[idx]
            if listing_item.inventory_management != 'shopify':
                continue
            inventory_quantities = []
            for shopify_location in shopify_location_ids:
                if not shopify_location.export_location_ids:
                    continue
                total_qty = 0
                for odoo_location in shopify_location.export_location_ids:
                    qty = int(
                        listing_item.product_id.get_product_stock(listing_item.export_qty_type, listing_item.export_qty_value, odoo_location, mk_instance_id.sudo().stock_field_id.name, ))
                    total_qty += max(0, qty)
                inventory_quantities.append({
                    "name": "available",
                    "quantity": max(0, total_qty),
                    "locationId": f"gid://shopify/Location/{shopify_location.shopify_location_id}",
                })
            if inventory_quantities:
                variant_vals.update({"inventoryQuantities": inventory_quantities})

    def prepare_jsonl_file_for_shopify_export_listing(self, operation_wizard, mk_instance_id, shopify_location_ids, operation_type, mk_log_id):
        """
        Task: T7609 - Build the JSONL payload for a Shopify bulk export/update.

        Threaded for speed: listings are split into disjoint chunks, and each chunk is built in its
        OWN database cursor/Environment on a worker thread. Separate cursors are the ONLY thread-safe
        way to touch the Odoo ORM from threads - no recordset or cursor is ever shared across threads,
        which is what prevents "could not serialize access / concurrent update" errors. Because
        psycopg2 releases the GIL during each query, the per-variant DB round-trips of different chunks
        run concurrently on Postgres, cutting wall-clock time.

        Task: T7609 - The payload is also cut into files below the Shopify 100 MB bulk limit. Each file is
        stored as an attachment and described by one entry of the returned list, which the caller turns
        into one bulk operation record per file.

        Returns:
            tuple: (payload_chunks, listing_sku_map, listing_barcode_map, skipped_listing_ids), where
                payload_chunks is a list of {'attachment_id', 'listing_ids', 'size'} dictionaries.
        """
        is_export = operation_type == 'export'
        is_update_product = is_export or operation_wizard.is_update_product
        is_set_price = is_export or operation_wizard.is_set_price
        is_set_quantity = operation_wizard.is_set_quantity
        is_set_images = operation_wizard.is_set_images
        is_update_product_variants = is_update_product or is_set_price or is_set_quantity or is_set_images

        # "Nothing to update" is a global decision (the flags are identical for every listing) - handle
        # it once here, never inside the threaded build.
        if not (is_update_product or is_set_price or is_set_quantity or is_update_product_variants or is_set_images) and not is_export:
            # Task: T7609 - Publish-only update (only Sales Channels picked): hand the bulk record back
            # as the sentinel instead of dropping it, so the caller can open it. Previously the record
            # was created but no action was returned, leaving the user on the list with no sign that
            # anything had started.
            publish_record = self.bulk_publish_listings_to_shopify(operation_wizard.shopify_sales_channel_ids, operation_wizard.is_publish_or_unpublish, mk_log_id)
            return publish_record, True, True, True

        # One network call, in the parent, before threading. Result is a plain {listing_id: [media]}
        # dict - safe to hand to workers (no cursor/recordset inside).
        dict_shopify_response_media = self._fetch_shopify_product_media_batch() if (operation_type == 'update' and is_set_images) else {}

        flags = {
            'is_export': is_export, 'is_update_product': is_update_product, 'is_set_price': is_set_price,
            'is_set_quantity': is_set_quantity, 'is_set_images': is_set_images,
            'is_update_product_variants': is_update_product_variants, 'operation_type': operation_type,
        }

        # Commit the parent transaction ONCE so the just-created wizard / log rows are visible to the
        # worker transactions (a new cursor is READ COMMITTED and cannot see the parent's uncommitted
        # rows). The listings themselves already exist and are committed.
        self.env.cr.commit()

        # Task: T7609 - Upload every new image to Shopify's own storage BEFORE the payload is built, so
        # each line carries a Shopify link instead of the Odoo image route. Shopify downloads the media of
        # a bulk payload concurrently, and thousands of parallel hits on the Odoo route are shed by the
        # hosting front with HTTP 429, which Shopify reports back as a FAILED media. Images that could not
        # be staged simply keep their Odoo URL, so an export never depends on the staging succeeding.
        staged_media = {}
        if is_set_images:
            new_image_ids = (self.image_ids | self.listing_item_ids.image_ids).filtered(lambda image: image.image and not image.media_id)
            staged_media = new_image_ids._shopify_stage_media(mk_instance_id) if new_image_ids else {}

        db_registry = self.env.registry
        uid, context = self.env.uid, dict(self.env.context, shopify_staged_media=staged_media)
        wizard_model, wizard_id = operation_wizard._name, operation_wizard.id
        instance_id, location_ids = mk_instance_id.id, shopify_location_ids and shopify_location_ids.ids or []

        CHUNK_SIZE = 50
        MAX_WORKERS = min(4, (os.cpu_count() or 2))  # bounded: caps DB connections + lock contention
        all_ids = self.ids
        chunks = [all_ids[i:i + CHUNK_SIZE] for i in range(0, len(all_ids), CHUNK_SIZE)]

        def _build_chunk_in_own_cursor(chunk_ids):
            # Retry transient serialization/deadlock errors (40001 / 40P01) with backoff - production-safe
            # against the rare case two chunks touch a shared row (e.g. two listings on the same product).
            last_error = None
            for attempt in range(1, 4):
                try:
                    with db_registry.cursor() as cr:
                        env = api.Environment(cr, uid, context)
                        chunk = env['mk.listing'].browse(chunk_ids)
                        wizard = env[wizard_model].browse(wizard_id)
                        instance = env['mk.instance'].browse(instance_id)
                        locations = env['shopify.location.ts'].browse(location_ids)
                        result = chunk._shopify_build_export_chunk(wizard, instance, locations, flags, dict_shopify_response_media)
                        cr.commit()  # persist this chunk's pricelist writes independently
                        return result
                except psycopg2.OperationalError as e:  # serialization failure / deadlock
                    last_error = e
                    time.sleep(0.4 * attempt)
                except Exception as e:
                    _logger.error("EXPORT LISTING: chunk build failed: %s", e)
                    raise
            _logger.error("EXPORT LISTING: chunk build failed after retries: %s", last_error)
            raise last_error

        # Task: T7609 - Shopify refuses a staged JSONL file over 100 MB, so the payload is cut into files
        # below SHOPIFY_BULK_CHUNK_SIZE while it is built and each closed file is written straight to an
        # attachment. Only ONE file worth of lines is ever held in memory, so a 500 MB payload does not
        # load the worker (which previously kept every line of the whole export in a single list).
        filename = self.env.context.get('filename') or ('export_listing.jsonl' if is_export else 'update_listing.jsonl')
        log_prefix = self.env.context.get('log_prefix') or f"{operation_type.upper()} LISTING"
        payload_chunks, sku_dict, barcode_dict, skipped_ids, log_lines = [], {}, {}, [], []
        pending_lines, pending_listing_ids, pending_size = [], [], 0

        def _close_payload_chunk():
            """Persist the lines gathered so far as one bulk file and start a fresh one."""
            nonlocal pending_lines, pending_listing_ids, pending_size
            if not pending_lines:
                return
            payload_chunks.append({
                'attachment_id': self._store_shopify_bulk_jsonl_chunk(mk_instance_id, pending_lines, filename, len(payload_chunks) + 1),
                'listing_ids': pending_listing_ids,
                'size': pending_size,
            })
            pending_lines, pending_listing_ids, pending_size = [], [], 0

        # The results are consumed window by window (never one map over every chunk) so the executor
        # cannot buffer the whole export in memory while the parent is still writing files.
        result_window = MAX_WORKERS * 2
        for window_start in range(0, len(chunks), result_window):
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                # executor.map preserves input order -> deterministic JSONL order, identical to the serial build.
                for res in executor.map(_build_chunk_in_own_cursor, chunks[window_start:window_start + result_window]):
                    if not res:
                        continue
                    sku_dict.update(res['sku'])
                    barcode_dict.update(res['barcode'])
                    skipped_ids.extend(res['skipped'])
                    log_lines.extend(res['log_lines'])
                    for line, line_size, line_listing_id in zip(res['lines'], res['sizes'], res['line_listing_ids']):
                        # One JSONL line is one productSet call and cannot be split any further, so a single
                        # oversized listing is reported and skipped instead of poisoning the whole file.
                        if line_size > SHOPIFY_BULK_CHUNK_SIZE:
                            skipped_ids.append(line_listing_id)
                            log_lines.append({'log_message': _("%s: Listing %s was skipped because its data alone is %s MB, which is over the %s MB Shopify accepts for one bulk file.") % (
                                log_prefix, line_listing_id, round(line_size / (1024 * 1024), 2), SHOPIFY_BULK_CHUNK_SIZE // (1024 * 1024))})
                            continue
                        if pending_size + line_size > SHOPIFY_BULK_CHUNK_SIZE:
                            _close_payload_chunk()
                        pending_lines.append(line)
                        pending_listing_ids.append(line_listing_id)
                        pending_size += line_size
        _close_payload_chunk()

        # Refresh the parent env so it sees the data the workers committed in other cursors.
        self.env.invalidate_all()

        # Write ALL collected skip/error log lines once, from the PARENT cursor only - never log to the
        # same mk.log row from worker threads (that would be a concurrent update on one row).
        if log_lines:
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': log_lines, 'success': []})

        return payload_chunks, sku_dict, barcode_dict, skipped_ids

    def _store_shopify_bulk_jsonl_chunk(self, mk_instance_id, jsonl_lines, filename, sequence):
        """
        Task: T7609 - Persist one JSONL file of a chunked bulk payload as an attachment.
        The payload is kept on disk (filestore) instead of memory or a text column, so a chunk that has to
        wait for a free Shopify bulk slot survives a worker restart and never inflates the record itself.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            jsonl_lines (list): JSONL lines of this file.
            filename (str): Base file name of the operation (e.g. update_listing.jsonl).
            sequence (int): 1-based index of this file inside the payload.
        Returns:
            int: Id of the created ir.attachment.
        """
        base_name = (filename or 'bulk_listing.jsonl').rsplit('.', 1)[0]
        attachment = self.env['ir.attachment'].create({
            'name': f"{base_name}_part_{sequence}.jsonl",
            'type': 'binary',
            'raw': '\n'.join(jsonl_lines).encode('utf-8'),
            'res_model': 'shopify.bulk.query',
            'mimetype': 'application/jsonl',
        })
        _logger.info("BULK LISTING: prepared payload file %s (%s lines) for instance %s", attachment.name, len(jsonl_lines), mk_instance_id.name)
        return attachment.id

    def _shopify_build_export_chunk(self, operation_wizard, mk_instance_id, shopify_location_ids, flags, dict_shopify_response_media):
        """
        Task: T7609 - Build JSONL lines for a chunk of listings (``self``) INSIDE a worker cursor.
        Returns only plain, picklable data (lists/dicts/str) - never recordsets - so results can cross
        the thread boundary safely. All ORM access here uses the worker's own env/cursor.
        """
        # is_export = flags['is_export']
        is_update_product = flags['is_update_product']
        is_set_price = flags['is_set_price']
        is_set_quantity = flags['is_set_quantity']
        is_set_images = flags['is_set_images']
        is_update_product_variants = flags['is_update_product_variants']
        operation_type = flags['operation_type']

        lines, sku, barcode, skipped, log_lines = [], {}, {}, [], []
        # Task: T7609 - Byte size and owning listing of every line, kept parallel to `lines`. The caller
        # needs both to cut the payload into files below the Shopify size limit and to record which
        # listings ended up in which file.
        line_sizes, line_listing_ids = [], []
        # Task: T7609 - One mapping search for the whole chunk; metafields ride along in the same
        # productSet payload, so no extra bulk operation is needed to SET metafield values.
        metafield_mappings = self.prepare_shopify_metafield_mappings_by_owner(mk_instance_id)
        metafield_log_line_dict = {'error': [], 'success': []}
        for listing_id in self:
            if listing_id.skip_listing_sync:
                skipped.append(listing_id.id)
                log_lines.append({'log_message': _("%s LISTING: Skipped %s(%s) Sync is disabled.") % (operation_type.upper(), listing_id.name, listing_id.mk_id or '')})
                continue
            if not listing_id.product_tmpl_id._check_barcode_and_sku(mk_instance_id):
                skipped.append(listing_id.id)
                continue
            if not listing_id.mk_id and operation_type == 'update':
                skipped.append(listing_id.id)
                continue

            prepare_data_dict, list_of_variants = {}, []

            if is_set_images:
                existing_media = dict_shopify_response_media.get(listing_id.id, []) if operation_type == 'update' else []
                prepare_data_dict['files'] = listing_id._prepare_variable_update_listing_images_in_shopify(existing_media, include_variant_images=True)

            if is_update_product:
                listing_id.prepare_update_vals_for_shopify_template_input(prepare_data_dict)

            if is_update_product_variants:
                if is_update_product:
                    listing_id.prepare_update_shopify_variant_input(list_of_variants, operation_wizard, inline_variant_images=is_set_images)
                else:
                    for listing_item_id in listing_id.listing_item_ids.sorted(key='sequence'):
                        if not listing_item_id.mk_id:
                            continue
                        option_values = []
                        if not listing_id.product_tmpl_id.attribute_line_ids:
                            option_values.append({'optionName': "Title", 'name': "Default Title"})
                        else:
                            for attrs in listing_item_id.product_id.product_template_attribute_value_ids:
                                option_values.append({"optionName": attrs.attribute_id.name, "name": attrs.name})
                        variant_vals = {"id": f"gid://shopify/ProductVariant/{listing_item_id.mk_id}", "optionValues": option_values}
                        if is_set_price:
                            if mk_instance_id.is_export_product_sale_price:
                                listing_item_id.with_context(shopify_skip_auto_price_sync=True).create_or_update_pricelist_item(listing_item_id.product_id.lst_price,
                                                                                                                                update_product_price=True, reversal_convert=True)
                            variant_vals["price"] = mk_instance_id.pricelist_id.with_context(uom=listing_item_id.product_id.uom_id.id)._get_product_price(listing_item_id.product_id, 1.0)
                        if is_set_images and listing_item_id.image_ids:
                            img = listing_item_id.image_ids[0]
                            if img.media_id or img.image:
                                file_payload = {'alt': img.shopify_alt_text or '', 'contentType': 'IMAGE'}
                                if img.media_id:
                                    file_payload['id'] = f"gid://shopify/MediaImage/{img.media_id}"
                                else:
                                    file_payload['originalSource'] = img._shopify_media_source()
                                variant_vals['file'] = file_payload
                        list_of_variants.append(variant_vals)

            if is_set_quantity and shopify_location_ids and list_of_variants:
                listing_id.prepare_data_for_shopify_inventory(list_of_variants, shopify_location_ids, mk_instance_id)

            if metafield_mappings.get('PRODUCT') or metafield_mappings.get('PRODUCTVARIANT'):
                listing_id.attach_shopify_bulk_metafields(mk_instance_id, metafield_mappings, prepare_data_dict, list_of_variants, metafield_log_line_dict)

            if list_of_variants:
                prepare_data_dict.update({"variants": list_of_variants})
            listing_id.prepare_update_shopify_options_input(prepare_data_dict)

            line = {"input": prepare_data_dict}
            if operation_type == 'update' and listing_id.mk_id:
                line["identifier"] = {"id": f"gid://shopify/Product/{listing_id.mk_id}"}
            json_line = json.dumps(line)
            lines.append(json_line)
            # Measure the ENCODED length (+1 for the newline the lines are joined with): a value with
            # accented or emoji characters takes 2-4 bytes, so len(str) would under-count and the upload
            # would still be rejected with EntityTooLarge.
            line_sizes.append(len(json_line.encode('utf-8')) + 1)
            line_listing_ids.append(listing_id.id)

            first_item = listing_id.listing_item_ids[:1]
            sku[listing_id.id] = first_item.default_code or ''
            barcode[listing_id.id] = first_item.barcode or first_item.product_id.barcode or ''
        log_lines.extend(metafield_log_line_dict['error'])
        return {'lines': lines, 'sizes': line_sizes, 'line_listing_ids': line_listing_ids, 'sku': sku, 'barcode': barcode, 'skipped': skipped, 'log_lines': log_lines}

    def poll_check_shopify_bulk_operation_status(self, bulk_operation_id, mk_instance_id, max_retries=3):
        """
        Task: T7609 - Poll a Shopify bulk operation until it reaches a terminal status
        (COMPLETED/FAILED/CANCELED/EXPIRED) or retries are exhausted.
        Args:
            bulk_operation_id (str): Shopify bulk operation numeric ID.
            mk_instance_id (record): Marketplace instance used to run the GraphQL query.
            max_retries (int): Maximum number of polling attempts.
        Returns:
            dict: Latest bulk operation node from Shopify, or empty dict if input is missing.
        """
        if not bulk_operation_id or not mk_instance_id:
            return {}
        variable = {"id": f"gid://shopify/BulkOperation/{bulk_operation_id}"}
        current_data = {}
        for attempt in range(1, max_retries + 1):
            try:
                poll_res = mk_instance_id.execute_graphql_query(GET_BULK_OPERATION_BY_ID, variable)
            except Exception as e:
                raise MarketplaceException(_(f"Failed to get poll status {e}"))
            user_errors = poll_res.get('errors', []) if isinstance(poll_res, dict) else []
            if user_errors and isinstance(user_errors, list):
                self.mk_instance_id.handle_shopify_access_errors(user_errors, "Bulk poll status check")
            current_data = (poll_res or {}).get('data', {}).get('node') or {}
            poll_status = current_data.get('status', '')
            _logger.info(f"Poll attempt {attempt}/{max_retries} for bulk {bulk_operation_id}: status={poll_status}")
            if poll_status in ('COMPLETED', 'FAILED', 'CANCELED', 'EXPIRED'):
                return current_data
            if attempt < max_retries:
                time.sleep(2)
        return current_data

    def bulk_export_update_listings_to_shopify(self, operation_wizard, shopify_location_ids, operation_type):
        """
        Task: T7609 - Run a Shopify bulk export/update for selected listings: build the JSONL payload,
        cut it into files below the Shopify 100 MB bulk limit, create one QUEUED bulk operation record per
        file, and let the dispatcher start as many as Shopify accepts concurrently. Remaining files are
        started by the poll cron as slots free up, so the number of selected listings is never a
        limitation the user has to work around.
        Args:
            operation_wizard (record): Wizard with export options.
            shopify_location_ids (recordset): Shopify location records used for inventory.
            operation_type (str): 'export' or 'update'.
        Returns:
            dict: Window action — log view when a single file completed inline, the bulk operation form
                for one file, or the list of the group's files when the payload was split.
        Raises:
            MarketplaceException: If listings span multiple instances, another bulk operation is
                already running, no exportable listings remain, staging fails, or Shopify returns userErrors.
        """
        filename, log_prefix = (('export_listing.jsonl', 'EXPORT LISTING') if operation_type == 'export' else ('update_listing.jsonl', 'UPDATE LISTING'))
        shopify_bulk_query_obj = self.env['shopify.bulk.query']
        mk_instance_id = self.mk_instance_id
        bulk_query_id = shopify_bulk_query_obj.search(
            [('mk_instance_id', '=', mk_instance_id.id), ('shopify_operation_type', 'in', ['export_listing', 'update_listing', 'export_price', 'export_inventory']),
             ('status', 'in', ['RUNNING', 'CANCELING']), ])
        if len(bulk_query_id) > 5:
            raise MarketplaceException(_("A Shopify bulk operation is already running for this instance "
                                         f" Please wait for it to complete before starting another."))

        mk_instance_id.connection_to_shopify()
        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')

        payload_chunks, listing_sku_dict, listing_barcode_dict, skip_listing_list = self.with_context(filename=filename, log_prefix=log_prefix).prepare_jsonl_file_for_shopify_export_listing(
            operation_wizard, mk_instance_id, shopify_location_ids, operation_type, mk_log_id)
        # Task: T7609 - Publish-only update: prepare_jsonl_file_for_shopify_export_listing returns the
        # bulk publish record it created in place of the JSONL lines. Open that record so the user lands
        # on the operation that was started; if it already completed inline, open the log instead.
        if listing_sku_dict is True and listing_barcode_dict is True and skip_listing_list is True:
            publish_record = payload_chunks
            if publish_record and publish_record._name == 'shopify.bulk.query':
                return {
                    'type': 'ir.actions.act_window',
                    'name': _('Shopify Bulk Operation'),
                    'res_model': 'shopify.bulk.query',
                    'res_id': publish_record.id,
                    'view_mode': 'form',
                    'target': 'current',
                }
            return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log') if mk_log_id.exists() else True
        if not payload_chunks:
            # Task: T7433 - Report the real reason. Distinguish listings skipped for "Skip Listing Sync" from
            # those missing SKU/barcode, so the user is not wrongly told to fix SKU/barcode when they only
            # disabled sync.
            sync_disabled = self.filtered('skip_listing_sync')
            if len(sync_disabled) == len(self):
                raise MarketplaceException(_("All selected listings have 'Skip Listing Sync' enabled, so there is nothing to export/update. "
                                             "Turn off 'Allow Sync' on the listing(s) you want to sync and try again."))
            if sync_disabled:
                raise MarketplaceException(_("No exportable listings. %s of %s selected listing(s) were skipped because 'Skip Listing Sync' is enabled; "
                                             "the rest are missing an Internal Reference (SKU) or Barcode. Please check the log for details and try again.") % (
                                               len(sync_disabled), len(self)))
            raise MarketplaceException(_("No exportable listings - all selected records were skipped due to "
                                         "missing SKU or barcode. Please fix the validation errors and try again."))

        # Task: T7609 - One record per payload file. Every record starts QUEUED with its file attached; the
        # dispatcher below stages and runs as many as Shopify allows to run at the same time and the poll
        # cron picks up the rest, so the user can select any number of listings without ever meeting the
        # 100 MB file limit or the 5 concurrent bulk operations limit.
        bulk_group_key = uuid.uuid4().hex
        chunk_total = len(payload_chunks)
        chunk_records = shopify_bulk_query_obj
        for sequence, payload_chunk in enumerate(payload_chunks, start=1):
            pending_payload = {
                'mode': operation_type,
                'listing_ids': payload_chunk['listing_ids'],
                'listing_sku_map': listing_sku_dict,
                'listing_barcode_map': listing_barcode_dict,
                'skipped_ids': skip_listing_list,
                'is_set_images': bool(operation_wizard.is_set_images),
                'is_set_quantity': bool(operation_wizard.is_set_quantity),
                'shopify_sales_channel_ids': operation_wizard.shopify_sales_channel_ids.ids,
            }
            if operation_type == 'update':
                pending_payload.update(
                    {
                        'is_publish_or_unpublish': operation_wizard.is_publish_or_unpublish
                    }
                )
            name = f"{operation_type.title()} Listings" + (f" ({sequence}/{chunk_total})" if chunk_total > 1 else "")
            chunk_records |= shopify_bulk_query_obj.create({
                'name': name,
                'shopify_operation_type': 'export_listing' if operation_type == 'export' else 'update_listing',
                'mk_instance_id': mk_instance_id.id,
                'mk_log_id': mk_log_id.id,
                'status': 'QUEUED',
                'bulk_group_key': bulk_group_key,
                'chunk_sequence': sequence,
                'chunk_total': chunk_total,
                'jsonl_attachment_id': payload_chunk['attachment_id'],
                'export_pending_data': json.dumps(pending_payload, indent=4),
            })
        # Commit before talking to Shopify: a request that succeeds must never be lost because a later
        # error rolls back the record that tracks it.
        self.env.cr.commit()

        shopify_bulk_query_obj.start_shopify_queued_bulk_operations(mk_instance_id, apply_inline=True)

        if chunk_total == 1 and not chunk_records.exists():
            # The single file completed and was applied inline, and the record cleaned itself up.
            return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log') if mk_log_id.exists() else ''
        if chunk_total == 1 and chunk_records.status == 'COMPLETED' and not chunk_records.result_url:
            return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log') if mk_log_id.exists() else ''
        if chunk_total > 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Shopify Bulk Operations'),
                'res_model': 'shopify.bulk.query',
                'domain': [('bulk_group_key', '=', bulk_group_key)],
                'view_mode': 'list,form',
                'target': 'current',
            }
        return {
            'type': 'ir.actions.act_window',
            'name': _('Shopify Bulk Operation'),
            'res_model': 'shopify.bulk.query',
            'res_id': chunk_records.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def bulk_publish_listings_to_shopify(self, add_sales_channel_ids, is_publish_or_unpublish, mk_log_id=False):
        """
        Task: T7609 - Publish or unpublish listings on Shopify sales channels via a bulk operation:
        builds the publish/unpublish JSONL, stages it, runs bulkOperationRunMutation, and either
        applies the completed result or returns the tracking record.
        Args:
            add_sales_channel_ids (recordset): Shopify sales channel (publication) records.
            is_publish_or_unpublish (bool): True to publish, False to unpublish.
            mk_log_id (record, optional): Marketplace log for tracking.
        Returns:
            record: shopify.bulk.query tracking record (empty recordset if completed inline).
        Raises:
            MarketplaceException: If listings span multiple instances, a bulk operation is already
                running, staging fails, or Shopify returns userErrors.
        """
        operation_type = self.env.context.get('operation_type_for_listing')
        shopify_bulk_query_obj = self.env['shopify.bulk.query']
        filename, log_prefix = (('export_listing.jsonl', 'EXPORT LISTING') if operation_type == 'export' else ('update_listing.jsonl', 'UPDATE LISTING'))
        if not self:
            return False
        mk_instance_id = self.mapped('mk_instance_id')
        if len(mk_instance_id) > 1:
            raise MarketplaceException(_("All selected listings must belong to one Shopify instance."))

        publishable_listing_ids = self.filtered(lambda l: l.mk_id)
        if not publishable_listing_ids:
            return False
        if not add_sales_channel_ids:
            return False

        bulk_query_id = shopify_bulk_query_obj.search(
            [('mk_instance_id', '=', mk_instance_id.id), ('shopify_operation_type', 'in', ['export_listing', 'update_listing', 'export_price', 'export_inventory']),
             ('status', 'in', ['RUNNING', 'CANCELING']), ])
        if len(bulk_query_id) > 5:
            raise MarketplaceException(_("A Shopify bulk operation is already running for this instance "
                                         f" Please wait for it to complete before starting another."))

        mk_instance_id.connection_to_shopify()

        publication_inputs = [{"publicationId": f"gid://shopify/Publication/{sc.sales_channel_id}"} for sc in add_sales_channel_ids]

        input_key = "publishInput" if is_publish_or_unpublish else "unpublishInput"
        jsonl_lines = [
            json.dumps({
                "id": f"gid://shopify/Product/{listing.mk_id}",
                input_key: publication_inputs,
            })
            for listing in publishable_listing_ids
        ]

        if not jsonl_lines:
            return False

        filename = self.env.context.get('filename') if not filename else filename
        log_prefix = self.env.context.get('log_prefix') if not log_prefix else log_prefix
        staged_path = self.upload_jsonl_to_shopify(mk_instance_id, jsonl_lines, filename, log_prefix)
        if not staged_path:
            raise MarketplaceException(_("Failed to stage upload to Shopify."))

        client_id = f"odoo-listing-publish-{uuid.uuid4().hex[:12]}"
        try:
            bulk_vars = {
                "mutation": BULK_OPERATION_UPDATE_SALES_CHANNEL.strip() if is_publish_or_unpublish else BULK_OPERATION_UPDATE_SALES_CHANNEL_UNPUBLISH.strip(),
                "stagedUploadPath": staged_path,
                "clientIdentifier": client_id,
            }
            response = mk_instance_id.execute_graphql_query(BULK_MUTATION_RUN, bulk_vars)
        except Exception as e:
            raise MarketplaceException(_(f"Failed publish upload. {e}"))
        user_errors = response.get('errors', []) if isinstance(response, dict) else {}
        if user_errors and isinstance(user_errors, list):
            self.mk_instance_id.handle_shopify_access_errors(user_errors, "Bulk sales chanel query run")
        bulk_run = (response or {}).get('data', {}).get('bulkOperationRunMutation', {}) or {}
        user_errors = bulk_run.get('userErrors') or []
        if user_errors:
            raise MarketplaceException(_(f"Shopify rejected bulk publish operation: {user_errors}"))

        bulk_op = bulk_run.get('bulkOperation') or {}
        bulk_gid = bulk_op.get('id', '')
        bulk_id = extract_numeric_id(bulk_gid) if bulk_gid else ''

        allowed_statuses = {'RUNNING', 'COMPLETED', 'CANCELING', 'CANCELED', 'FAILED', 'EXPIRED'}
        shopify_status = bulk_op.get('status') or 'RUNNING'
        if shopify_status not in allowed_statuses:
            shopify_status = 'RUNNING'

        bulk_vals = {
            'name': f"Publish Listings - {bulk_id}",
            'shopify_operation_type': 'update_listing',
            'bulk_operation_id': bulk_id,
            'mk_instance_id': mk_instance_id.id,
            'mk_log_id': mk_log_id.id if mk_log_id and mk_log_id.exists() else False,
            'export_pending_data': json.dumps({
                'phase': 'publish',
                'sales_channel_ids': add_sales_channel_ids.ids,
                'is_publish_or_unpublish': is_publish_or_unpublish,
            }, indent=4),
        }

        result_url = ''
        if bulk_id and shopify_status not in {'COMPLETED', 'FAILED', 'CANCELED', 'EXPIRED'}:
            poll_data = self.poll_check_shopify_bulk_operation_status(bulk_id, mk_instance_id)
            polled_status = poll_data.get('status', '')
            if polled_status in allowed_statuses:
                shopify_status = polled_status
                result_url = poll_data.get('url', '') or ''

        if shopify_status == 'COMPLETED' and result_url:
            shopify_bulk_query_id = shopify_bulk_query_obj.create(dict(bulk_vals, status=shopify_status))
            try:
                shopify_bulk_query_obj.handle_shopify_bulk_export_listing(shopify_bulk_query_id, mk_instance_id, result_url)
            except Exception as e:
                _logger.error(f"BULK PUBLISH LISTING failed: {e}")
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                     mk_log_line_dict={'error': [{'log_message': f"BULK PUBLISH LISTING failed: {e}"}]})
            return shopify_bulk_query_obj
        # return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log') if mk_log_id.exists() else ''
        return shopify_bulk_query_obj.create(dict(bulk_vals, status=shopify_status))

    def _process_shopify_bulk_publish_result(self, record, mk_instance_id, result_url):
        """
        Task: T7609 - Apply a completed Shopify bulk publish/unpublish result: parse the JSONL,
        update each listing's sales channels and publish state, log success/error per line, and
        finalize the bulk operation record.
        Args:
            record (record): shopify.bulk.query record being processed.
            mk_instance_id (record): Marketplace instance used for listing lookup.
        Returns:
            bool: True if the JSONL was processed, False if it could not be downloaded.
        """
        data = json.loads(record.export_pending_data)
        mk_log_id = record.mk_log_id
        mk_log_line_dict = {'error': [], 'success': []}

        raw_lines = self.get_shopify_bulk_result_of_jsonl(result_url, record, "BULK PUBLISH")
        if raw_lines is None:
            return False

        log_message_word = "publish" if data.get("is_publish_or_unpublish") else "unpublish"
        shopify_user_errors = []

        payload = self.export_shopify_pending_payload(record)
        is_publish_or_unpublish = payload.get('is_publish_or_unpublish', True)
        # Task: T7628 - browse WITHOUT .exists(): a userError points at a channel by its INDEX in the
        # list that was sent to Shopify, so dropping an already-deleted record here would shift the
        # indices and remove the wrong channel.
        sales_channel_records = self.env['shopify.sales.channels.ts'].browse(payload.get('sales_channel_ids') or [])
        sales_channel_ids = set(sales_channel_records.ids)
        # Every product line reports the same dead publication, so collect here and unlink once
        # after the loop instead of one unlink and one log line per product.
        missing_channels_to_unlink = self.env['shopify.sales.channels.ts']
        missing_channel_product_count = {}
        published_at = fields.Datetime.now()

        for raw_line in raw_lines:
            try:
                data = json.loads(raw_line)
            except ValueError:
                continue
            payload_data = (data.get('data') or {}).get('publish') or {} if is_publish_or_unpublish else (data.get('data') or {}).get('unpublish') or {}
            errs = payload_data.get('userErrors') or []
            published = payload_data.get('publishable') or {}
            product_gid = published.get('id', '')
            product_id = extract_numeric_id(product_gid) if product_gid else ''
            listing = self.find_listing_by_shopify_product_id(mk_instance_id, product_id)
            listing_name = listing.name if listing else ''

            failed_channel_ids = set()
            if errs:
                # Task: T7628 - Dead-channel errors repeat on EVERY product line (80 products -> 80
                # identical entries). They are reported once as a summary on the record below, so keep
                # only the other errors here.
                shopify_user_errors.extend([err for err in errs if "Publication does not exist or is not publishable" not in (err.get('message') or '')])
                # Same shared handler the per-record flow uses. unlink_missing_channels is False here:
                # channels are accumulated and removed once after the loop.
                missing_channels, is_record_unlinked = self.env['shopify.sales.channels.ts'].handle_shopify_publication_user_errors(
                    errs, sales_channel_records, listing, mk_log_line_dict, 'EXPORT/UPDATE LISTING', mk_instance_id=mk_instance_id, unlink_missing_channels=False)
                missing_channels_to_unlink |= missing_channels
                failed_channel_ids = set(missing_channels.ids)
                for missing_channel_id in failed_channel_ids:
                    missing_channel_product_count[missing_channel_id] = missing_channel_product_count.get(missing_channel_id, 0) + 1
                if is_record_unlinked:
                    continue
            # Task: T7628 - Run even when there were errors: a single dead publication must not throw
            # away the result for the channels that published fine (the listing would stay marked
            # unpublished in Odoo while it is live on Shopify). Only the failed channels are dropped.
            if published and listing:
                existing_ids = set(listing.shopify_sales_channel_ids.ids)
                good_channel_ids = sales_channel_ids - failed_channel_ids
                # A publish that reached NO channel (every selected one is dead on Shopify) must not be
                # reported as published: only drop the dead channels from the listing.
                is_nothing_published = is_publish_or_unpublish and not good_channel_ids
                listing_vals = {}
                if not is_nothing_published:
                    listing_vals.update({
                        'is_listed': True,
                        'listing_publish_date': published_at,
                    })
                if good_channel_ids and is_publish_or_unpublish:
                    chanel_ids = list((existing_ids | good_channel_ids) - failed_channel_ids)
                    listing_vals['shopify_sales_channel_ids'] = [(6, 0, chanel_ids)]
                    listing_vals['is_published'] = listing.shopify_check_is_listing_published(chanel_ids)
                else:
                    chanel_ids = list(existing_ids - sales_channel_ids - failed_channel_ids)
                    listing_vals['shopify_sales_channel_ids'] = [(6, 0, chanel_ids)]
                    listing_vals['is_published'] = listing.shopify_check_is_listing_published(chanel_ids)
                listing.write(listing_vals)
                if not is_nothing_published:
                    mk_log_line_dict['success'].append({
                        'log_message': f'EXPORT/UPDATE LISTING: Product {listing_name}({product_id}) has been {log_message_word}ed successfully'})

        # Task: T7628 - Build the customer-facing summary BEFORE the unlink (reading name /
        # sales_channel_id afterwards raises MissingError). One readable line per dead channel with the
        # number of products it affected, instead of the same raw Shopify error repeated per product.
        summary_messages = []
        for missing_channel in missing_channels_to_unlink.exists():
            summary_messages.append(_(
                'Sales Channel "%s" (ID: %s) no longer exists in Shopify - it was deleted or its app was uninstalled. '
                'It has been removed from Odoo and %s product(s) could not be %sed to it. '
                'Please select a valid Sales Channel and run the operation again.'
            ) % (missing_channel.name, missing_channel.sales_channel_id, missing_channel_product_count.get(missing_channel.id, 0), log_message_word))

        if missing_channels_to_unlink:
            self.env['shopify.sales.channels.ts'].log_and_unlink_missing_channels(missing_channels_to_unlink, mk_log_line_dict, 'EXPORT/UPDATE LISTING')

        if mk_log_id:
            self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)

        record.write({
            'status': 'COMPLETED',
            'message': '\n'.join(summary_messages + [self.format_shopify_user_error_message(shopify_user_errors)]).strip(),
        })
        return True

    def export_shopify_pending_payload(self, record):
        """
        Task: T7609 - Parse the JSON `export_pending_data` stored on a Shopify bulk operation record.
        Args:
            record (record): shopify.bulk.query record.
        Returns:
            dict: Parsed payload, empty dict if missing or invalid.
        """
        try:
            return json.loads(record.export_pending_data or '{}')
        except (ValueError, TypeError):
            return {}

    def get_shopify_bulk_result_of_jsonl(self, result_url, record, op_label):
        """
        Task: T7609 - Download a Shopify bulk operation result file and return its non-empty JSONL lines.
        Marks the record as FAILED with a log message if the download errors out.
        Args:
            result_url (str): Shopify result file URL.
            record (record): Bulk operation record updated on failure.
            op_label (str): Label used in the failure log.
        Returns:
            list[str] | None: JSONL lines, or None if download failed.
        """
        try:
            response = requests.get(result_url, stream=True, timeout=120)
            response.raise_for_status()
        except Exception as e:
            message = f"{op_label}: failed to download result JSONL - {e}"
            _logger.error(message)
            record.write({'status': 'FAILED', 'message': message})
            return None
        return [raw_line for raw_line in response.iter_lines() if raw_line]

    def prepare_shopify_response_for_the_jsonl_file(self, raw_line):
        """
        Task: T7609 - Parse one productSet response line from a Shopify bulk result JSONL file.
        Args:
            raw_line (str): One raw JSONL line.
        Returns:
            tuple: (product_dict, user_errors_list). Both empty on parse failure.
        """
        try:
            data = json.loads(raw_line)
        except ValueError:
            return {}, []
        product_set_payload = (data.get('data') or {}).get('productSet') or {}
        line_errors = product_set_payload.get('userErrors') or []
        for error in data.get('errors') or []:
            line_errors.append({'field': error.get('path', ''), 'message': error.get('message', '')})
        return product_set_payload.get('product') or {}, line_errors

    def match_shopify_listing_from_bulk_result(self, product, operation_type, listing_ids, sku_to_listing, barcode_to_listing=None, sync_product_with='barcode_or_sku', mk_id_to_listing=None):
        """
        Task: T7609 - Match a Shopify product from a bulk result to an Odoo listing — by Shopify ID
        when updating, or by the instance's sync key (SKU/barcode) when exporting.
        Args:
            product (dict): Shopify product data from the bulk result.
            operation_type (str): 'export' or 'update'.
            listing_ids (recordset): Candidate Odoo listings.
            sku_to_listing (dict): SKU → listing.id mapping used in export mode.
            barcode_to_listing (dict): Barcode → listing.id mapping used in export mode.
            sync_product_with (str): Instance setting - 'barcode', 'sku', or 'barcode_or_sku'.
            mk_id_to_listing (dict): Pre-built str(mk_id) → listing map used in update mode to
                replace an O(n) recordset scan per product with an O(1) lookup.
        Returns:
            record: Matched mk.listing, or an empty recordset if no match.
        """
        if operation_type == 'update':
            shopify_id = extract_numeric_id(product.get('id', ''))
            if mk_id_to_listing is not None:
                return mk_id_to_listing.get(str(shopify_id), self.env['mk.listing'])
            return listing_ids.filtered(lambda l: str(l.mk_id) == str(shopify_id))[:1]
        barcode_to_listing = barcode_to_listing or {}
        variant_nodes = (product.get('variants') or {}).get('nodes') or []
        for node in variant_nodes:
            node = node or {}
            sku, barcode = node.get('sku'), node.get('barcode')
            # Match on the same key the instance syncs with; barcode_or_sku tries SKU first
            # then barcode, mirroring _sync_by_barcode_or_sku in the import flow.
            if sync_product_with == 'barcode':
                if barcode and barcode in barcode_to_listing:
                    return listing_ids.browse(barcode_to_listing[barcode])
            elif sync_product_with == 'sku':
                if sku and sku in sku_to_listing:
                    return listing_ids.browse(sku_to_listing[sku])
            else:
                if sku and sku in sku_to_listing:
                    return listing_ids.browse(sku_to_listing[sku])
                if barcode and barcode in barcode_to_listing:
                    return listing_ids.browse(barcode_to_listing[barcode])
        return self.env['mk.listing']

    def _fetch_remaining_shopify_variants_after_bulk(self, product_dict):
        """
        Task: T7609 - A bulk mutation payload may hold at most one connection, capped at one page of 250
        variants, and a bulk result cannot be paginated. When a product carries more variants than that,
        walk the rest with the normal cursor query so the caller works with the complete variant list.
        Args:
            product_dict (dict): productSet result of one product; its 'variants' entry is updated in place.
        Returns:
            bool: True when the full variant list is known, False when a page failed and the list stayed incomplete.
        """
        self.ensure_one()
        variants_data = product_dict.get('variants') or {}
        page_info = variants_data.get('pageInfo') or {}
        if not page_info.get('hasNextPage'):
            return True

        all_nodes = list(variants_data.get('nodes') or [])
        cursor = page_info.get('endCursor', "")
        product_id = product_dict.get('id', "")
        # Task: T7609 - The bulk apply runs in worker threads and the Shopify session is thread-local,
        # so a worker without its own activated session answers 401 on the first cursor call.
        self.mk_instance_id.connection_to_shopify()
        while cursor:
            try:
                res = self.mk_instance_id.execute_graphql_query(GET_PRODUCT_VARIANT_AFTER_CURSOR, {"productId": product_id, "cursor": cursor, "first": 250})
            except Exception as e:
                _logger.error(f"BULK LISTING: Failed to fetch remaining variants of {self.name}: {e}")
                return False
            page = ((res or {}).get('data', {}).get('product') or {}).get('variants') or {}
            all_nodes += page.get('nodes') or []
            page_info = page.get('pageInfo') or {}
            cursor = page_info.get('endCursor', "") if page_info.get('hasNextPage') else ""

        variants_data['nodes'] = all_nodes
        variants_data['pageInfo'] = {'hasNextPage': False, 'endCursor': ""}
        product_dict['variants'] = variants_data
        return True

    def apply_shopify_bulk_export_result_to_listing(self, listing_id, product_dict, is_set_images, operation_type, mk_log_line_dict, media_cache=None):
        """
        Task: T7609 - Sync a single Shopify bulk result back to its Odoo listing: update product data,
        write media_id for new images, and record a success/error log line.
        Args:
            listing_id (record): Target Odoo listing.
            product_dict (dict): Shopify product data from the bulk result.
            is_set_images (bool): Whether image sync is enabled.
            operation_type (str): 'export' or 'update' (used for log labels).
            mk_log_line_dict (dict): Log collector for success/error messages.
            media_cache (dict, optional): Pre-fetched {listing.id: [media_nodes]} to skip an
                extra per-listing GraphQL call; falls back to the single-record helper on miss.
        Returns:
            bool: True on success, False if post-processing raised.
        """
        try:
            is_variant_list_complete = listing_id._fetch_remaining_shopify_variants_after_bulk(product_dict)
            listing_id.update_odoo_shopify_product(product_dict)
            variant_ids = [f"{extract_numeric_id(v.get('id'))}" for v in product_dict.get("variants", {}).get("nodes", []) if v.get("id", "")]
            listing_item_ids = listing_id.listing_item_ids.filtered(lambda l: l.mk_id not in variant_ids) if is_variant_list_complete else listing_id.browse()
            if listing_item_ids:
                removed_variants = "\n".join(
                    f"  {index}. SKU: {item.default_code or 'N/A'} | Variant: {item.name} | Shopify Variant ID: {item.mk_id or 'N/A'}"
                    for index, item in enumerate(listing_item_ids, start=1))
                log_message = (
                    f"BULK {operation_type.upper()} LISTING: Deleted {len(listing_item_ids)} variant(s) from Odoo.\n"
                    f"Product: {listing_id.name} (Shopify Product ID: {listing_id.mk_id})\n"
                    f"Reason: These variants no longer exist in Shopify. They were removed from the Odoo listing so that "
                    f"both systems stay in sync. No Odoo product was deleted, only the marketplace listing variants.\n"
                    f"Deleted Variants:\n{removed_variants}"
                )
                _logger.info(log_message)
                mk_log_line_dict['error'].append({'log_message': log_message})
                listing_item_ids.unlink()
            if is_set_images:
                # Variant images are now attached inline via productSet's variants[].file (bundled in JSONL).
                # The only remaining post-bulk step is writing back media_id for new images.
                if not all(listing_id.image_ids.mapped('media_id')):
                    if media_cache is not None and listing_id.id in media_cache:
                        media_after = media_cache[listing_id.id]
                    else:
                        media_after = listing_id._fetch_shopify_product_media()
                    listing_id._set_shopify_media_ids_for_new_images(media_after)
            mk_log_line_dict['success'].append({'log_message': f"EXPORT LISTING: Successfully {operation_type} product {listing_id.name}({listing_id.mk_id})"})
            return True
        except Exception as e:
            _logger.error(f"BULK {operation_type.upper()} LISTING post-processing failed for {listing_id.name}: {e}")
            mk_log_line_dict['error'].append({
                'log_message': f"BULK {operation_type.upper()} LISTING post-processing failed for {listing_id.name}: {e}"})
            return False

    def trigger_shopify_bulk_publish_after_export(self, successful_listings, is_publish_or_unpublish, sales_channel_ids, mk_instance_id, mk_log_id):
        """
        Task: T7609 - Kick off a Shopify bulk publish/unpublish for listings that exported successfully.
        No-op when there are no listings or no sales channels.
        Args:
            successful_listings (recordset): Listings that exported without error.
            is_publish_or_unpublish (bool): True to publish, False to unpublish.
            sales_channel_ids (list[int]): Shopify sales channel record IDs.
            mk_instance_id (record): Marketplace instance.
            mk_log_id (record): Marketplace log used to record failures.
        Returns:
            record: shopify.bulk.query record, or empty recordset when skipped/error.
        """
        shopify_bulk_query_obj = self.env['shopify.bulk.query']
        if not (sales_channel_ids and successful_listings):
            return shopify_bulk_query_obj
        # Task: T7628 - Keep only channels that still exist AND belong to this instance, so a channel
        # left without an instance (or owned by another one) is never sent to Shopify as a publication.
        sales_channel_records = self.env['shopify.sales.channels.ts'].browse(sales_channel_ids).exists().filtered(lambda c: c.mk_instance_id == mk_instance_id)
        if not sales_channel_records:
            return shopify_bulk_query_obj
        try:
            return successful_listings.bulk_publish_listings_to_shopify(sales_channel_records, is_publish_or_unpublish, mk_log_id)
        except Exception as e:
            _logger.error(f"Failed to publish products: {e}")
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': f'EXPORT/UPDATE LISTING: Failed to publish products: {e}'}]})
        return shopify_bulk_query_obj

    def prepare_jsonl_file_for_shopify_metafield_delete(self, mk_instance_id, metafield_mappings, mk_log_line_dict):
        """
        Task: T7609 - Build the JSONL payload of the metafieldsDelete bulk operation: one line per owner
        chunk of 25 metafield identifiers. Only metafields whose Odoo value became empty are collected,
        reusing `update_product_metafields_to_shopify` (which returns the delete list).
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            metafield_mappings (dict): Mappings by owner type from prepare_shopify_metafield_mappings_by_owner.
            mk_log_line_dict (dict): Log dictionary to store error messages.
        Returns:
            list: JSONL lines (str).
        """
        jsonl_lines = []
        product_mappings = metafield_mappings.get('PRODUCT')
        variant_mappings = metafield_mappings.get('PRODUCTVARIANT')
        for listing_id in self:
            if not listing_id.mk_id:
                continue
            metafields_to_delete = []
            if product_mappings:
                metafields_to_set, product_metafields_to_delete = listing_id.update_product_metafields_to_shopify(mk_instance_id, listing_id.product_tmpl_id, 'PRODUCT', mk_log_line_dict,
                                                                                                                  listing_id.mk_id, mappings=product_mappings)
                owner_gid = f"gid://shopify/Product/{listing_id.mk_id}"
                metafields_to_delete += [dict(metafield, ownerId=owner_gid) for metafield in product_metafields_to_delete]

            if variant_mappings:
                for listing_item_id in listing_id.listing_item_ids.filtered('mk_id'):
                    metafields_to_set, variant_metafields_to_delete = listing_id.update_product_metafields_to_shopify(mk_instance_id, listing_item_id.product_id, 'PRODUCTVARIANT',
                                                                                                                      mk_log_line_dict, listing_item_id.mk_id, mappings=variant_mappings)
                    owner_gid = f"gid://shopify/ProductVariant/{listing_item_id.mk_id}"
                    metafields_to_delete += [dict(metafield, ownerId=owner_gid) for metafield in variant_metafields_to_delete]

            for index in range(0, len(metafields_to_delete), SHOPIFY_METAFIELD_LIMIT):
                jsonl_lines.append(json.dumps({"metafields": metafields_to_delete[index:index + SHOPIFY_METAFIELD_LIMIT]}))
        return jsonl_lines

    def bulk_delete_listing_metafields_to_shopify(self, mk_instance_id, mk_log_id=False, has_publish_step=False):
        """
        Task: T7609 - Remove metafield values in Shopify whose mapped Odoo field is empty, via a bulk
        metafieldsDelete operation. productSet cannot delete a metafield, so this is the ONLY part of the
        metafield sync that needs its own bulk query; the 'set' side is inlined in the productSet payload.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            mk_log_id (recordset, optional): Marketplace log for tracking.
            has_publish_step (bool): True when a bulk publish record was also chained, so this record must
                not send the "process completed" notification.
        Returns:
            record: shopify.bulk.query tracking record (empty recordset when there is nothing to delete).
        Raises:
            MarketplaceException: If a bulk operation is already running, staging fails, or Shopify returns userErrors.
        """
        shopify_bulk_query_obj = self.env['shopify.bulk.query']
        if not self:
            return shopify_bulk_query_obj

        metafield_mappings = self.prepare_shopify_metafield_mappings_by_owner(mk_instance_id)
        if not (metafield_mappings.get('PRODUCT') or metafield_mappings.get('PRODUCTVARIANT')):
            return shopify_bulk_query_obj

        mk_log_line_dict = {'error': [], 'success': []}
        jsonl_lines = self.prepare_jsonl_file_for_shopify_metafield_delete(mk_instance_id, metafield_mappings, mk_log_line_dict)
        if mk_log_line_dict['error'] and mk_log_id and mk_log_id.exists():
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
        if not jsonl_lines:
            return shopify_bulk_query_obj

        bulk_query_id = shopify_bulk_query_obj.search(
            [('mk_instance_id', '=', mk_instance_id.id), ('shopify_operation_type', 'in', ['export_listing', 'update_listing', 'export_price', 'export_inventory']),
             ('status', 'in', ['RUNNING', 'CANCELING']), ])
        if len(bulk_query_id) > 5:
            raise MarketplaceException(_("A Shopify bulk operation is already running for this instance "
                                         f" Please wait for it to complete before starting another."))

        mk_instance_id.connection_to_shopify()
        staged_path = self.upload_jsonl_to_shopify(mk_instance_id, jsonl_lines, 'delete_listing_metafield.jsonl', 'UPDATE LISTING')
        if not staged_path:
            raise MarketplaceException(_("Failed to stage upload to Shopify."))

        client_id = f"odoo-listing-metafield-{uuid.uuid4().hex[:12]}"
        try:
            bulk_vars = {
                "mutation": DELETE_SPECIFIC_METAFIELD_VALUE.strip(),
                "stagedUploadPath": staged_path,
                "clientIdentifier": client_id,
            }
            response = mk_instance_id.execute_graphql_query(BULK_MUTATION_RUN, bulk_vars)
        except Exception as e:
            raise MarketplaceException(_(f"Failed metafield delete upload. {e}"))
        user_errors = response.get('errors', []) if isinstance(response, dict) else {}
        if user_errors and isinstance(user_errors, list):
            mk_instance_id.handle_shopify_access_errors(user_errors, "Bulk metafield query run")
        bulk_run = (response or {}).get('data', {}).get('bulkOperationRunMutation', {}) or {}
        user_errors = bulk_run.get('userErrors') or []
        if user_errors:
            raise MarketplaceException(_(f"Shopify rejected bulk metafield operation: {user_errors}"))

        bulk_op = bulk_run.get('bulkOperation') or {}
        bulk_gid = bulk_op.get('id', '')
        bulk_id = extract_numeric_id(bulk_gid) if bulk_gid else ''

        allowed_statuses = {'RUNNING', 'COMPLETED', 'CANCELING', 'CANCELED', 'FAILED', 'EXPIRED'}
        shopify_status = bulk_op.get('status') or 'RUNNING'
        if shopify_status not in allowed_statuses:
            shopify_status = 'RUNNING'

        bulk_vals = {
            'name': f"Delete Listing Metafields - {bulk_id}",
            'shopify_operation_type': 'update_listing',
            'bulk_operation_id': bulk_id,
            'mk_instance_id': mk_instance_id.id,
            'mk_log_id': mk_log_id.id if mk_log_id and mk_log_id.exists() else False,
            'export_pending_data': json.dumps({
                'phase': 'metafield_delete',
                'has_publish_step': has_publish_step,
            }, indent=4),
        }

        result_url = ''
        if bulk_id and shopify_status not in {'COMPLETED', 'FAILED', 'CANCELED', 'EXPIRED'}:
            poll_data = self.poll_check_shopify_bulk_operation_status(bulk_id, mk_instance_id)
            polled_status = poll_data.get('status', '')
            if polled_status in allowed_statuses:
                shopify_status = polled_status
                result_url = poll_data.get('url', '') or ''

        if shopify_status == 'COMPLETED' and result_url:
            shopify_bulk_query_id = shopify_bulk_query_obj.create(dict(bulk_vals, status=shopify_status))
            try:
                self._process_shopify_bulk_metafield_delete_result(shopify_bulk_query_id, mk_instance_id, result_url)
            except Exception as e:
                _logger.error(f"BULK METAFIELD DELETE failed: {e}")
                self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                     mk_log_line_dict={'error': [{'log_message': f"BULK METAFIELD DELETE failed: {e}"}]})
            return shopify_bulk_query_obj
        return shopify_bulk_query_obj.create(dict(bulk_vals, status=shopify_status))

    def trigger_shopify_bulk_metafield_delete_after_export(self, successful_listings, mk_instance_id, mk_log_id, operation_type, has_publish_step=False):
        """
        Task: T7609 - Kick off the metafieldsDelete bulk for listings that exported/updated successfully.
        Skipped on export: a brand new Shopify product has no existing metafield value to remove.
        Args:
            successful_listings (recordset): Listings that exported/updated without error.
            mk_instance_id (recordset): Recordset of mk.instance.
            mk_log_id (recordset): Marketplace log used to record failures.
            operation_type (str): 'export' or 'update'.
            has_publish_step (bool): True when a bulk publish record was also chained.
        Returns:
            record: shopify.bulk.query record, or empty recordset when skipped/error.
        """
        shopify_bulk_query_obj = self.env['shopify.bulk.query']
        if operation_type != 'update' or not successful_listings:
            return shopify_bulk_query_obj
        try:
            return successful_listings.bulk_delete_listing_metafields_to_shopify(mk_instance_id, mk_log_id, has_publish_step)
        except Exception as e:
            _logger.error(f"Failed to delete metafields: {e}")
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id,
                                                 mk_log_line_dict={'error': [{'log_message': f'EXPORT/UPDATE LISTING: Failed to delete metafields: {e}'}]})
        return shopify_bulk_query_obj

    def _process_shopify_bulk_metafield_delete_result(self, record, mk_instance_id, result_url):
        """
        Task: T7609 - Apply a completed metafieldsDelete bulk result: count the deleted metafields and
        log the Shopify userErrors, then finalize the bulk operation record.
        Args:
            record (record): shopify.bulk.query record being processed.
            mk_instance_id (recordset): Recordset of mk.instance.
            result_url (str): Shopify bulk result file URL.
        Returns:
            bool: True if the JSONL was processed, False if it could not be downloaded.
        """
        mk_log_id = record.mk_log_id
        mk_log_line_dict = {'error': [], 'success': []}

        raw_lines = self.get_shopify_bulk_result_of_jsonl(result_url, record, "BULK METAFIELD DELETE")
        if raw_lines is None:
            return False

        shopify_user_errors, deleted_metafield_count = [], 0
        for raw_line in raw_lines:
            try:
                data = json.loads(raw_line)
            except ValueError:
                continue
            payload_data = (data.get('data') or {}).get('metafieldsDelete') or {}
            shopify_user_errors.extend(payload_data.get('userErrors') or [])
            deleted_metafield_count += len(payload_data.get('deletedMetafields') or [])

        if deleted_metafield_count:
            mk_log_line_dict['success'].append({'log_message': _("UPDATE LISTING: Successfully deleted %s metafield value(s) in Shopify.") % deleted_metafield_count})
        if mk_log_id and mk_log_id.exists():
            self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)

        record.write({
            'status': 'COMPLETED',
            'message': self.format_shopify_user_error_message(shopify_user_errors),
        })
        return True

    def find_listing_by_shopify_product_id(self, mk_instance_id, product_id):
        """
        Task: T7609 - Search a single mk.listing record for the given Shopify product ID and instance.
        Args:
            mk_instance_id (record): Marketplace instance.
            product_id (str | int): Shopify product numeric ID.
        Returns:
            record: Matching mk.listing, or empty recordset if not found.
        """
        if not product_id:
            return self.env['mk.listing']
        return self.env['mk.listing'].search([('mk_instance_id', '=', mk_instance_id.id), ('mk_id', '=', str(product_id)), ], limit=1)

    def format_shopify_user_error_message(self, user_errors):
        """
        Task: T7609 - Join a list of Shopify userErrors into a newline-separated string for logging.
        Args:
            user_errors (list[dict]): Shopify userErrors entries.
        Returns:
            str: Newline-joined messages, empty string if list is empty.
        """
        if not user_errors:
            return ''
        # Task: T7628 - A bulk result repeats the same userError on every product line, so collapse to
        # one line per distinct message with the number of occurrences instead of N identical lines.
        message_counts = OrderedDict()
        for err in user_errors:
            message = err.get('message', str(err)) if isinstance(err, dict) else str(err)
            message_counts[message] = message_counts.get(message, 0) + 1
        return '\n'.join(f'{message} ({count} products)' if count > 1 else message for message, count in message_counts.items())

    def cron_auto_export_stock(self, mk_instance_id):
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state != 'confirmed':
            return True
        self.update_stock_in_shopify_ts(mk_instance_id)
        return True

    def get_shopify_listing_items(self, mk_instance_id, product_ids):
        return self.env['mk.listing.item'].search([('product_id', 'in', product_ids.ids), ('mk_instance_id', '=', mk_instance_id.id)], order='shopify_last_stock_update_date')

    def update_stock_in_shopify_ts(self, mk_instance_ids):
        """
        Update stock in Shopify for specified Shopify instances.

        :param mk_instance_ids: List or single instance of Shopify instances to update stock.
        :type mk_instance_ids: Record of the Shopify instance
        :return: True if the update process completes successfully.
        :rtype: bool
        """
        if not isinstance(mk_instance_ids, list):
            mk_instance_ids = [mk_instance_ids]
        for mk_instance_id in mk_instance_ids:
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
            mk_log_line_dict = {'error': [], 'success': []}

            # Retrieve Shopify locations for the current instance that support import/export of stock
            # Task: T7653 - Removed is_third_party_location field.
            location_ids = self.env['shopify.location.ts'].search([('mk_instance_id', '=', mk_instance_id.id), ('is_import_export_stock', '=', True)])
            if not location_ids:
                self._handle_shopify_no_location_found(mk_instance_id, mk_log_id, mk_log_line_dict)
                continue

            for location_id in location_ids:
                if not location_id.export_location_ids:
                    log_message = _("Warehouse/Stock Location is not set for Odoo Shopify Location %s") % location_id.name
                    mk_log_line_dict['error'].append({'log_message': 'EXPORT STOCK: ' + log_message})
                    location_ids -= location_id

            listing_item_ids = self.get_mk_listing_item(mk_instance_id)

            # If this is the first time we're exporting inventory, we need to skip listing items that already have a stock export date set.
            # This is because there might be hundreds of listing items to export, and due to server limitations, only some of them might be successfully exported in one go.
            # As a result, already exported items could be re-exported unintentionally in the next attempt.
            # To avoid this, we filter out listing items that already have a 'shopify_last_stock_update_date' set.
            if not mk_instance_id.last_stock_update_date:
                listing_item_ids = listing_item_ids.filtered(lambda x: not x.shopify_last_stock_update_date)

            new_listing_item_ids = self._get_filtered_shopify_listing_items(listing_item_ids, mk_instance_id, mk_log_id, mk_log_line_dict)
            if not new_listing_item_ids:
                continue

            # Add a logger message with the count of listing items and locations
            logger_message = _("🚀 Started inventory export for %s listing items across %s locations for instance %s") % (len(new_listing_item_ids), len(location_ids), mk_instance_id.name)
            _logger.info(logger_message)

            # Establish connection to Shopify
            mk_instance_id.connection_to_shopify()

            formated_listing_items = self.prepare_bulk_inventory_update_vals(mk_instance_id, new_listing_item_ids, location_ids, mk_log_id)
            self.run_bulk_shopify_inventory_update_perfect(mk_instance_id, formated_listing_items, mk_log_id, mk_log_line_dict)
        return True

    def prepare_bulk_inventory_update_vals(self, mk_instance_id, new_listing_item_ids, shopify_location_ids, mk_log_id):
        """
        TASK: T6274 - Enable Multi-Location Stock Export to Shopify Location
        Task: T7545 - Updated for Shopify API 2026-07 and added changeFromQuantity fields.
        """
        item_list = []
        for item in new_listing_item_ids:
            # Task: T7433 - Implemented import/export control using the ‘Allow Sync’ flag available in the listing  form view, supporting all flows to skip listings during synchronization between Odoo and Shopify.
            mk_listing_id = item.mk_listing_id
            if mk_listing_id.skip_listing_sync:
                log_message = _("EXPORT STOCK: Skipped listing item %s(%s) as listing %s(%s) Sync is disabled.") % (item.name, item.mk_id, mk_listing_id.name, mk_listing_id.mk_id)
                self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, operation_type='export', mk_instance_id=mk_instance_id, mk_log_line_dict={'error': [{'log_message': log_message}]})
                continue
            if not item.inventory_item_id:
                continue
            for shopify_location in shopify_location_ids:
                total_quantity = 0
                for shopify_location_id in shopify_location.export_location_ids:
                    quantity = int(item.product_id.get_product_stock(item.export_qty_type, item.export_qty_value, shopify_location_id, mk_instance_id.sudo().stock_field_id.name))
                    total_quantity += max(0, quantity)
                item_list.append({
                    'inventoryItemId': f"gid://shopify/InventoryItem/{item.inventory_item_id}",
                    'locationId': f"gid://shopify/Location/{shopify_location.shopify_location_id}",
                    'quantity': 0 if total_quantity < 0 else total_quantity,
                    'changeFromQuantity': None,
                })
        return item_list

    def update_inventory_batch(self, batch_updates, mk_instance_id, mk_log_line_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        # Task: T7545 - Updated for Shopify API 2026-07, added idempotencyKey, removed ignoreCompareQuantity.
        variables = {
            "input": {
                "name": 'available',
                "reason": "restock",
                "quantities": batch_updates,
            },
            "idempotencyKey": uuid.uuid4().hex,
        }
        mk_instance_id.connection_to_shopify()
        result = mk_instance_id.execute_graphql_query(INVENTORY_SET_QUANTITIES, variables)
        errors = (result or {}).get('errors') or []
        if errors:
            # Task: T7609 - Top-level GraphQL errors (e.g. ACCESS_DENIED for missing write_inventory scope) are instance-level: return them like coded userErrors so the dispatcher logs ONE mk.log line and stops the remaining batches, instead of raising the same error once per batch.
            messages = ", ".join(dict.fromkeys(err.get('message', str(err)) if isinstance(err, dict) else str(err) for err in errors))
            first_error = errors[0] if isinstance(errors[0], dict) else {}
            return True, [{'error': messages, 'code': (first_error.get('extensions') or {}).get('code') or 'GRAPHQL_ERROR'}]

        user_errors = result and result.get('data', {}).get('inventorySetQuantities', {}).get('userErrors', []) or result.get('errors', [])

        failed_items = []
        is_error = False
        for error in user_errors:
            is_error = True
            field_path = error.get('field', [])
            message = error.get('message')
            if error.get('extensions', {}).get('code'):
                return is_error, [{'error': message, 'code': error.get('extensions', {}).get('code')}]
            elif isinstance(field_path, list) and len(field_path) >= 3 and str(field_path[2]).isdigit():
                idx = int(field_path[2])
                if 0 <= idx < len(batch_updates):
                    item = batch_updates[idx]
                    item['error'] = message
                    failed_items.append(item)

                    inventory_item_id = extract_numeric_id(item.get('inventoryItemId', ''))
                    location_id = extract_numeric_id(item.get('locationId', ''))
                    log_message = _("❌ Inventory Export Failed Item Details: Inventory Item ID: %s | Location ID: %s | Quantity: %s. Error= %s") % (
                        inventory_item_id, location_id, item.get('quantity'), message)
                    _logger.warning(log_message)
                    mk_log_line_dict['error'].append({'log_message': 'EXPORT STOCK: ' + log_message})
        return is_error, failed_items

    def batch_inventory_updates(self, updates, batch_size):
        """Split a flat list of inventory update dicts into batches without splitting any single item's updates.

        This function groups all update entries by their `inventoryItemId` (preserving the original order
        of appearance), then assembles batches of up to `batch_size` entries each, ensuring that all
        updates for a given `inventoryItemId` remain together in the same batch.

        If a single `inventoryItemId` has more updates than `batch_size`, that entire group will occupy
        its own (oversized) batch rather than being split across multiple batches.
        Args:
            updates (List[Dict]): List of inventory update dictionaries. Each dict must contain at least:
                - 'inventoryItemId': str, a Shopify GID for the inventory item
                - 'locationId':      str, a Shopify GID for the location
                - 'quantity':        int, the new on-hand quantity
            batch_size (int): Maximum number of update entries per batch.
        Returns:
            List[List[Dict]]: A list of batches, where each batch is a list of update dicts and no
            two dicts for the same `inventoryItemId` appear in different batches.
        """
        # 1) Group by inventoryItemId, preserving order
        id_map = OrderedDict()
        for u in updates:
            id_map.setdefault(u['inventoryItemId'], []).append(u)

        # 2) Build batches without splitting any one ID’s group
        batches = []
        current_batch = []
        current_count = 0

        for item_id, group in id_map.items():
            group_size = len(group)

            # If adding this entire group would overflow the batch, flush the current batch first
            if current_count + group_size > batch_size and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_count = 0

            # Add the whole group
            current_batch.extend(group)
            current_count += group_size

        # Flush any remaining
        if current_batch:
            batches.append(current_batch)

        return batches

    def run_bulk_shopify_inventory_update_perfect(self, mk_instance_id, inventory_updates, mk_log_id, mk_log_line_dict):
        """
        Task: T5836 - Migrate Shopify to v19
        Task: T7653 - Removed Inventory Location Activation and implemented custom fulfillment location related changes.
        Include the functionality to groups failed locations by inventory item and activates them via the Shopify GraphQL inventoryBulkToggleActivation mutation.
        """
        batches = self.batch_inventory_updates(inventory_updates, BATCH_SIZE)
        total_batches = len(batches)
        completed_batches = 0
        failed_batches = []
        now = fields.Datetime.now()
        manual_operation = self.env.context.get('manual_operation', False)
        skip_inventory_sync_commit = self.env.context.get('skip_inventory_sync_commit', False)

        # === Worker function ===
        def process_batch(batch, attempt=1):
            # Task: T7609 - Each worker thread MUST use its own cursor/Environment — the ORM cursor
            # (self.env.cr) is NOT thread-safe. Sharing it across threads caused psycopg2 "no results to
            # fetch". self.pool.cursor() gives this worker its own cursor (auto-commit on clean exit), so the
            # main dispatch loop stays the sole user of self.env.cr. A thread-local env lets MAX_WORKERS > 1 work.
            with self.pool.cursor() as new_cr:
                self_t = self.with_env(api.Environment(new_cr, self.env.uid, self.env.context))
                instance_t = mk_instance_id.with_env(self_t.env)
                clean_batch = []
                try:
                    is_error, failed_items = self_t.update_inventory_batch(batch, instance_t, mk_log_line_dict)
                    if is_error:
                        if [item for item in failed_items if item.get('code')]:
                            failed_batches.append(batch)
                            return failed_items

                        inv_item_ids = [extract_numeric_id(item.get('inventoryItemId', '')) for item in failed_items if
                                        'specified inventory item could not be found' in item.get('error', '')]
                        if inv_item_ids:
                            listing_items = self_t.env['mk.listing.item'].search([('mk_instance_id', '=', instance_t.id), ('inventory_item_id', 'in', inv_item_ids)])
                            # when shopify product removed, at that time remove listing too, while updating the inventory.
                            for listing_item_id in listing_items:
                                delete_listing, log_message = False, ''
                                mk_var_id = listing_item_id.mk_id
                                mk_listing_id = listing_item_id.mk_listing_id
                                if mk_listing_id.number_of_variants_in_mk <= 1:
                                    delete_listing = True
                                if delete_listing:
                                    log_message = _("EXPORT STOCK: Shopify product %s does not exist; deleting Listing %s from Odoo.") % (mk_listing_id.mk_id, mk_listing_id.name)
                                else:
                                    log_message = _("EXPORT STOCK: Removing Listing Item %s from Listing %s (mk_id=%s) – Variant no longer exists on Shopify.") % (
                                        listing_item_id.name, mk_listing_id.name, mk_var_id)
                                mk_log_line_dict['error'].append({'log_message': log_message})
                                not delete_listing and listing_item_id and listing_item_id.sudo().unlink()
                                delete_listing and mk_listing_id.sudo().unlink()

                        # build a set of failed keys
                        failed_keys = {(f.get('inventoryItemId'), f.get('locationId')) for f in failed_items if f.get('inventoryItemId') and f.get('locationId')}

                        # keep only those not in failed_keys
                        clean_batch = [item for item in batch if (item['inventoryItemId'], item['locationId']) not in failed_keys]

                        if clean_batch and attempt <= MAX_RETRIES:
                            _logger.info(f"🔁 Excluded failed inventory items; retrying batch(Attempt {attempt}/{MAX_RETRIES}) in {RETRY_SECONDS} seconds...")
                            time.sleep(RETRY_SECONDS)
                            return process_batch(clean_batch, attempt + 1)
                        else:
                            log_message = _("❌ Batch permanently failed after %s retries.") % MAX_RETRIES
                            _logger.warning(log_message)
                            mk_log_line_dict['error'].append({'log_message': 'EXPORT STOCK: ' + log_message})
                            failed_batches.append(batch)
                        failed_batches.append(batch)
                    return clean_batch or batch
                except Exception as e:
                    log_message = f"❌ Batch crashed permanently: {e}"
                    _logger.warning(log_message)
                    mk_log_line_dict['error'].append({'log_message': f'EXPORT STOCK: {log_message}'})
                    failed_batches.append(batch)
                    return []

        # 4) Dispatch with ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_map = {executor.submit(process_batch, b): b for b in batches}
            for fut in as_completed(future_map):
                try:
                    success_items = fut.result()
                except Exception as e:
                    _logger.error(f"A batch future raised an unhandled exception: {e}")
                    failed_batches.append(future_map[fut])
                    success_items = []

                if isinstance(success_items, list) and success_items and [item for item in success_items if item.get('code')]:
                    code = [item for item in success_items if item.get('code')][0].get('code')
                    error = [item for item in success_items if item.get('code')][0].get('error')
                    log_message = _("❌ Batch permanently failed with Code=%s Error=%s") % (code, error)
                    _logger.warning(log_message)
                    mk_log_line_dict['error'].append({'log_message': 'EXPORT STOCK: ' + log_message})
                    # Task: T7609 - Instance-level failure (e.g. ACCESS_DENIED): flush this line to mk.log now (break skips the shared flush below), cancel not-yet-started batches and stop.
                    self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
                    not skip_inventory_sync_commit and self.env.cr.commit()
                    for pending_future in future_map:
                        pending_future.cancel()
                    break

                if success_items:
                    inventory_item_ids = [extract_numeric_id(item['inventoryItemId']) for item in success_items]
                    listing_items = self.env['mk.listing.item'].search([('mk_instance_id', '=', mk_instance_id.id), ('inventory_item_id', 'in', inventory_item_ids)])
                    _logger.info(f"✅ Successfully updated {len(set(inventory_item_ids))} items...")
                    # listing_items.write({'shopify_last_stock_update_date': now})
                    for success_item in success_items:
                        inventory_item_id = extract_numeric_id(success_item.get('inventoryItemId', ''))
                        location_id = extract_numeric_id(success_item.get('locationId', ''))
                        log_message = _("EXPORT STOCK:✅  Inventory Export Succeeded: Inventory Item ID: %s | Location ID: %s | Quantity: %s.") % (
                            inventory_item_id, location_id, success_item.get('quantity'))
                        mk_log_line_dict['success'].append({'log_message': log_message})

                completed_batches += 1
                self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
                mk_log_line_dict = {'error': [], 'success': []}
                not skip_inventory_sync_commit and self.env.cr.commit()
                _percent = (completed_batches / total_batches) * 100
                _logger.info(f"BulkInventoryExport: {completed_batches}/{total_batches} batches processed ({_percent:.1f}%)")

        # 5) Write back timestamps and cleanup
        if not failed_batches and not manual_operation:
            mk_instance_id.write({'last_stock_update_date': now})
        elif failed_batches:
            message = f"BulkExport: {len(failed_batches)} of {total_batches} batches failed to process completely. The instance's last stock update date will not be updated to allow for reprocessing."
            _logger.error(message)

    def _get_filtered_shopify_listing_items(self, listing_item_ids, mk_instance_id, mk_log_id, mk_log_line_dict):
        """
        Filtered listing items based on inventory management and last stock update date. Returns False if no qualifying items are found.
        """
        if isinstance(listing_item_ids, list):
            listing_item_ids = self.env['mk.listing.item'].browse(listing_item_ids)

        # Filter listing items based on inventory management and shopify_last_stock_update_date is not set.
        new_listing_item_ids = self.env['mk.listing.item'].search(
            [('shopify_last_stock_update_date', '=', False), ('is_listed', '=', True), ('inventory_management', '=', 'shopify'), ('mk_instance_id', '=', mk_instance_id.id),
             ('product_id.is_storable', '=', True)])

        # Filter listing items based on inventory management.
        new_listing_item_ids |= listing_item_ids.filtered(lambda x: x.inventory_management == 'shopify')

        # If no records are found, update last_stock_update_date and handle log creation.
        if not new_listing_item_ids:
            mk_instance_id.last_stock_update_date = fields.Datetime.now()
            self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
            return False
        return new_listing_item_ids

    def _handle_shopify_log_creation(self, mk_instance_id, mk_log_id, mk_log_line_dict):
        """
        Creates or updates a log entry for Shopify-related operations.

        :param mk_instance_id: Record of the Shopify instance
        :param mk_log_id: Record of Log
        :param mk_log_line_dict: Dictionary containing log details (error and success)
        :return: The log that was written to (empty when nothing was left to keep).

        Task: T9096 - Cleans up the log create_update_log actually wrote to, not the one passed in.
        A helper that flushed earlier may already have deleted the passed log (it was empty at that
        point); create_update_log then creates a fresh one, which with log level "error" is empty
        when the run only had success lines. Checking only the passed id left that blank log behind.
        """
        log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
        if log_id.exists() and not log_id.log_line_ids:
            log_id.unlink()
        return log_id.exists()

    def _handle_shopify_no_location_found(self, mk_instance_id, mk_log_id, mk_log_line_dict):
        """
        Handles the scenario when no location is found for a Shopify Instance during the stock update.
        """
        log_message = _("No location found for Shopify Instance %s at the time of Import stock!") % mk_instance_id.name
        mk_log_line_dict['error'].append({'log_message': 'EXPORT STOCK: ' + log_message})
        self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)

    def cron_auto_import_stock(self, mk_instance_id):
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state == 'confirmed':
            self.shopify_import_stock(mk_instance_id)
        return True

    def cron_auto_update_product_price(self, mk_instance_id):
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state == 'confirmed':
            self.shopify_update_product_price(mk_instance_id)
        return True

    def shopify_open_export_listing_view(self):
        action = self.env.ref('base_marketplace.action_product_export_to_marketplace').sudo().read()[0]
        action['name'] = _("Export Product to Shopify")
        action['views'] = [(self.env.ref('shopify.mk_operation_export_listing_to_shopify_view').sudo().id, 'form')]
        ctx = self.env.context.copy()
        active_ids = ctx.get('active_ids')
        mk_listing_id = active_ids and self.browse(active_ids[0])
        ctx['default_is_set_price'] = True
        ctx['default_is_set_quantity'] = True
        ctx['default_is_set_images'] = True
        ctx['default_is_publish_or_unpublish'] = True
        ctx['default_mk_instance_id'] = mk_listing_id.mk_instance_id.id
        action['context'] = ctx
        return action

    def shopify_open_update_listing_view(self):
        """
        Task: T7628 - Set the default sales channel action as Published.
        """
        action = self.env.ref('base_marketplace.action_listing_update_to_marketplace').sudo().read()[0]
        action['name'] = _("Update Listings in Shopify")
        action['views'] = [(self.env.ref('shopify.mk_operation_update_listing_to_shopify_view').sudo().id, 'form')]
        ctx = self.env.context.copy()
        active_ids = ctx.get('active_ids')
        mk_listing_id = active_ids and self.browse(active_ids[0])
        if active_ids and len(active_ids) == 1:
            shopify_sales_channel_ids = mk_listing_id.shopify_sales_channel_ids.ids
            ctx['default_shopify_sales_channel_ids'] = [(6, 0, shopify_sales_channel_ids)]
        ctx['default_mk_instance_id'] = mk_listing_id.mk_instance_id.id
        ctx['default_is_publish_or_unpublish'] = True
        action['context'] = ctx
        return action

    def upload_jsonl_to_shopify(self, mk_instance, jsonl_lines, filename, log_prefix):
        """
        Task: T6152 - Bulk Price Update via shopify bulkOperationRunMutation
        Step 1: Request staged upload credentials from Shopify.
        Step 2: Upload JSONL file to Google Cloud Storage.
        Arg:
            mk_instance - Recordset of mk.instance model.
            jsonl_lines - Mapping of product IDs to their variant price updates.
        Returns: stagedUploadPath (the GCS 'key') or False on failure.
        """
        # Step 1: Get staged upload credentials
        # Task: T7609 - Build the content FIRST and send its exact byte size as `fileSize`. Without it the
        # policy document Shopify signs carries a small default upper bound, and GCS rejects the upload with
        # "EntityTooLarge / Content-length exceeds upper bound on range" as soon as the JSONL grows (for
        # example products carrying many metafields).
        jsonl_content = '\n'.join(jsonl_lines).encode('utf-8')
        if len(jsonl_content) > SHOPIFY_BULK_FILE_SIZE_LIMIT:
            raise MarketplaceException(_("%s: The generated file is %s MB, but Shopify accepts at most %s MB per bulk operation. "
                                         "Please run the operation on fewer listings at a time.") % (
                                           log_prefix, round(len(jsonl_content) / (1024 * 1024), 2), SHOPIFY_BULK_FILE_SIZE_LIMIT // (1024 * 1024)))
        try:
            variables = {
                "input": [{"resource": "BULK_MUTATION_VARIABLES", "filename": filename, "mimeType": "text/jsonl", "httpMethod": "POST", "fileSize": str(len(jsonl_content))}]
            }
            res = mk_instance.execute_graphql_query(STAGED_UPLOADS_CREATE, variables)
        except Exception as e:
            raise MarketplaceException(_(f"Failed Shopify staged upload: {e}")) from e
        user_errors = res.get('errors', []) if isinstance(res, dict) else {}
        if user_errors and isinstance(user_errors, list):
            self.mk_instance_id.handle_shopify_access_errors(user_errors, "Bulk Jsonl Upload")
        staged_data = res and res.get('data', {}) and res.get('data', {}).get('stagedUploadsCreate', {})

        user_errors = staged_data.get('userErrors', [])
        if user_errors:
            _logger.error(f"{log_prefix}: stagedUploadsCreate errors: {user_errors}")
            return False

        targets = staged_data.get('stagedTargets', [])
        if not targets:
            _logger.error(f"{log_prefix}: No staged targets returned from Shopify.")
            return False

        target = targets[0] if isinstance(targets, list) and targets else {}
        params = {p['name']: p['value'] for p in target.get('parameters', [])}
        staged_upload_path = params and params.get('key', '')

        if not staged_upload_path:
            _logger.error(f"{log_prefix}: No 'key' found in staged upload parameters.")
            return False

        # Step 2: Upload JSONL content to GCS via multipart POST
        log_message = upload_content_to_staged_target(target, jsonl_content, filename, 'text/jsonl', log_prefix)
        if log_message:
            _logger.error(log_message)
            raise MarketplaceException(_(log_message))

        _logger.info(f"{log_prefix}: JSONL uploaded successfully. Path: {staged_upload_path}")
        return staged_upload_path

    def bulk_update_listing_item_prices_to_shopify(self, product_id, variants, mk_instance, mk_log_line_dict):
        """
        Task: T6152 - Add Stock & Price Update Functionality from Listing Items
        Executes the Shopify bulk‐update GraphQL.
        If Shopify returns “Product variant does not exist” errors, this will
        unlink the corresponding mk.listing.item record from Odoo.
        Returns:
          - On full success: list of updated variants dicts.
          - On partial failure: dict with 'errors' list.
        """
        variables = {"productId": product_id, "variants": variants}
        resp = mk_instance.execute_graphql_query(PRICE_UPDATE, variables)

        # 1) Transport errors
        if resp and "errors" in resp:
            err_msg = "; ".join(error.get('message', str(error)) for error in resp.get("errors", ''))
            return {'errors': [f"GraphQL error: {err_msg}"]}

        payload = resp and resp.get("data", {}) and resp.get("data", {}).get("productVariantsBulkUpdate")
        if payload is None:
            return {'errors': [f"Empty payload: {resp}"]}

        # 2) User errors
        user_errs = payload.get("userErrors") or []
        if user_errs:
            # 2a) Product‐level error → delete the entire listing
            for err in user_errs:
                if err.get('field', '') == ['productId']:
                    listing_mk_id = extract_numeric_id(product_id)
                    listing = self.env['mk.listing'].search([('mk_id', '=', listing_mk_id), ('mk_instance_id', '=', mk_instance.id)], limit=1)
                    if listing:
                        log_message = _("UPDATE PRICE:❌ Shopify product %s does not exist; deleting Listing %s from Odoo.") % (listing_mk_id, listing.name)
                        _logger.warning(log_message)
                        mk_log_line_dict['error'].append({'log_message': log_message})
                        listing.sudo().unlink()
                    # skip processing any variants for this listing
                    return {}

            # 2b) Variant‐level errors → unlink only those items
            failed_idxs = []
            for err in user_errs:
                fld = err.get('field', '') or []
                if fld and fld[0] == 'variants':
                    try:
                        failed_idxs.append(int(fld[1]))
                    except (ValueError, IndexError):
                        continue

            for idx in set(failed_idxs):
                gid = variants[idx].get('id', '')
                mk_var_id = gid and extract_numeric_id(gid)
                rec = self.env['mk.listing.item'].search([('mk_id', '=', mk_var_id), ('mk_instance_id', '=', mk_instance.id), ], limit=1)
                if rec:
                    log_message = _("UPDATE PRICE: Removing Listing Item %s from Listing %s (mk_id=%s) – Variant no longer exists on Shopify") % (rec.name, rec.mk_listing_id.name, mk_var_id)
                    _logger.warning(log_message)
                    mk_log_line_dict['error'].append({'log_message': log_message})
                    rec.sudo().unlink()

        # 3) Everything’s fine
        return payload.get("productVariants", [])

    def get_mk_listing_item_for_price_update(self, mk_instance_id):
        """
        Task: T6994 - Retrieve marketplace listing items that require a price update for a marketplace instance.

        :param mk_instance_id: Marketplace instance record.
        :return: Recordset of ``mk.listing.item`` requiring price updates.
        """
        if mk_instance_id.marketplace != 'shopify':
            return super().get_mk_listing_item_for_price_update(mk_instance_id)

        pricelist = mk_instance_id.pricelist_id
        operation_wizard = self.env.context.get('operation_wizard', self.env['mk.operation'])
        if operation_wizard:
            last_update = operation_wizard.last_update_price_date
        else:
            last_update = mk_instance_id.last_listing_price_update_date

        if last_update:
            changed_items = pricelist.item_ids.filtered(lambda x: x.write_date > last_update)
        else:
            changed_items = pricelist.item_ids

        if not changed_items:
            return self.env['mk.listing.item']
        product_ids = self.env['product.product']
        all_listed = False
        for item in changed_items:
            if item.applied_on == '0_product_variant' and item.product_id:
                product_ids |= item.product_id
            elif item.applied_on == '1_product' and item.product_tmpl_id:
                product_ids |= item.product_tmpl_id.product_variant_ids
            elif item.applied_on == '2_product_category' and item.categ_id:
                product_ids |= self.env['product.product'].search([('categ_id', 'child_of', item.categ_id.id)])
            elif item.applied_on == '3_global':
                all_listed = True
                break
        if all_listed:
            return self.env['mk.listing.item'].search([('is_listed', '=', True), ('mk_instance_id', '=', mk_instance_id.id)])
        return self.get_mk_listing_item_from_product_variants(product_ids, mk_instance_id)

    def shopify_update_product_price(self, mk_instance_ids, listing_item_ids=False, mk_log_id=False, mk_log_line_dict=False):
        """
        Task: T6152 - Add Stock & Price Update Functionality from Listing Items
        This method updates price of listing items from odoo to shopify.
        Args:
            mk_instance_ids (recordset): Recordset of mk.instance.
            listing_item_ids (list): List of recordset of mk.listing.item.
            mk_log_id (recordset): Recordset of mk.log.
            mk_log_line_dict (dict) : Dictionary contains log details.
        Returns:
            bool: Returns True on successful operation completion.
        """
        last_listing_price_update_date = fields.Datetime.now()

        if not isinstance(mk_instance_ids, list):
            mk_instance_ids = [mk_instance_ids]

        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        for mk_instance_id in mk_instance_ids:
            mk_log_id = mk_log_id if mk_log_id else self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
            mk_log_line_dict = mk_log_line_dict if mk_log_line_dict is not False else {'error': [], 'success': []}
            is_manual_update_price = self.env.context.get('is_manual_update_price', False)
            mk_instance_id.connection_to_shopify()

            # Check for False value
            listing_item_ids = listing_item_ids if listing_item_ids else self.get_mk_listing_item_for_price_update(mk_instance_id)

            # Collect all product variant updates
            product_updates = {}
            for listing_item_id in listing_item_ids:
                mk_listing_id = listing_item_id.mk_listing_id
                # Task: T7433 - Implemented import/export control using the ‘Allow Sync’ flag available in the listing  form view, supporting all flows to skip listings during synchronization between Odoo and Shopify.
                if mk_listing_id.skip_listing_sync:
                    log_message = _("UPDATE PRICE: Skipped listing item %s(%s) as listing %s(%s) Sync is disabled.") % (
                        listing_item_id.name, listing_item_id.mk_id, mk_listing_id.name, mk_listing_id.mk_id)
                    mk_log_line_dict['error'].append({'log_message': log_message})
                    continue
                if not listing_item_id.mk_id:
                    continue
                if mk_instance_id.is_export_product_sale_price:
                    listing_item_id.create_or_update_pricelist_item(listing_item_id.product_id.lst_price, update_product_price=True, reversal_convert=True)
                variant_price = mk_instance_id.pricelist_id.with_context(uom=listing_item_id.product_id.uom_id.id)._get_product_price(listing_item_id.product_id, 1.0)

                if not float_is_zero(variant_price, precision_digits=price_unit_prec):
                    product_id = f"gid://shopify/Product/{listing_item_id.mk_listing_id.mk_id}"
                    if product_id not in product_updates:
                        product_updates[product_id] = []

                    product_updates[product_id].append({"id": f"gid://shopify/ProductVariant/{listing_item_id.mk_id}", "price": variant_price})

            # Add logger message with the count of listing items and locations
            logger_message = _("🚀 Started update price for %s listing items across %s listings for instance %s") % (len(listing_item_ids), len(product_updates), mk_instance_id.name)
            _logger.info(logger_message)

            # commit every N products
            batch_size = 50
            counter = 0
            cr = self.env.cr

            for product_id, variants in product_updates.items():
                if not variants:
                    continue
                try:
                    resp = self.bulk_update_listing_item_prices_to_shopify(product_id, variants, mk_instance_id, mk_log_line_dict)
                    if not resp:
                        continue

                    # Success path: resp is list of updated variants
                    for v in resp:
                        msg = f"UPDATE PRICE: ✅ Successfully updated the Shopify price to {v.get('price', '0.0')} for Listing Item {extract_numeric_id(v.get('id'))} in Listing {extract_numeric_id(product_id)}."
                        mk_log_line_dict['success'].append({'log_message': msg})
                except Exception as e:
                    log_message = f"❌ Error while trying to update price for Listing: {product_id}, ERROR: {e}."
                    mk_log_line_dict['error'].append({'log_message': f'UPDATE PRICE: {log_message}'})

                # increment and commit in batches
                counter += 1
                if counter % batch_size == 0:
                    self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
                    cr.commit()
                    _logger.info(f"UPDATE PRICE: Committed after processing {counter} listings")
            if not is_manual_update_price:
                mk_instance_id.last_listing_price_update_date = last_listing_price_update_date
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
            if mk_log_id.exists() and not mk_log_id.log_line_ids and not is_manual_update_price:
                mk_log_id.unlink()
        return True

    def shopify_open_listing_in_marketplace(self):
        marketplace_url = self.mk_instance_id.shop_url + '/admin/products/' + self.mk_id
        return marketplace_url

    def _fetch_all_shopify_product_remaining_metafields(self, mk_instance_id, resource_mk_id, id_key, response_key, query, page_info, template_id,
                                                        mk_log_line_dict=False, queue_line_id=False):
        """
        T6290 - This method fetches remaining metafield from Shopify using pagination for a given resource.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            resource_mk_id (str): Shopify marketplace ID (product or variant) in GID format.
            id_key (str): GraphQL variable key (e.g., productId, variantId).
            response_key (str): Key used to extract response data (e.g., product, productVariant).
            query (str): GraphQL query used to fetch remaining metafields.
            page_info (dict): Pagination info containing cursor and next page details.
            template_id (recordset): Odoo record (product template or variant) for logging/reference.
            mk_log_line_dict (dict, optional): Dictionary contains log details.
            queue_line_id (recordset): Recordset of mk.queue.job.line.
        Returns:
            tuple: (list of remaining metafields, bool indicating whether pagination completed without errors)
        """
        remaining_metafields = []
        is_complete = True
        mk_id = str(extract_numeric_id(resource_mk_id))

        while page_info.get('hasNextPage'):
            variables = {id_key: resource_mk_id, "cursor": page_info.get('endCursor', ""), "first": 250}
            try:
                response = mk_instance_id.execute_graphql_query(query, variables=variables)
                if response and response.get('errors'):
                    log_message = _("IMPORT LISTING: Error while fetching metafield for %s %s (%s): %s") % (response_key, template_id.display_name, mk_id, response.get('errors'))
                    mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False})
                    is_complete = False
                    break
                remaining_metafield_data = response and response.get('data', {}) and response.get('data', {}).get(response_key, {}) and response.get('data', {}).get(response_key, {}).get(
                    'metafields', [])
                # Task: T7725 - Added defensive pagination handling for single-page Shopify responses.
                if isinstance(remaining_metafield_data, list) and remaining_metafield_data:
                    last_item = remaining_metafield_data[-1]
                    # Detect pageInfo wrapper by content to avoid dropping the last real metafield.
                    if isinstance(last_item, dict) and set(last_item.keys()) == {'pageInfo'}:
                        remaining_metafields.extend(remaining_metafield_data[:-1])
                        page_info = last_item.get('pageInfo', {})
                    else:
                        remaining_metafields.extend(remaining_metafield_data)
                        page_info = {}
                else:
                    page_info = {}
            except Exception as e:
                log_message = f"IMPORT LISTING: Exception occurred during metafield fetch for {response_key} {template_id.display_name} ({mk_id}): {str(e)}"
                mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False})
                is_complete = False
                break
        return remaining_metafields, is_complete

    def _collect_shopify_metafield_values(self, mk_instance_id, shopify_res, resource_mk_id, id_key, response_key, query, odoo_record, mk_log_line_dict,
                                          queue_line_id=False):
        """
        T6290 - This method fetches metafield values from Shopify for a given resource and handles pagination.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            shopify_res (dict): Shopify response node containing metafield data.
            resource_mk_id (str): Shopify GraphQL product ID e.g gid://shopify/Product/1222 or gid://shopify/ProductVariant/45642651959508'.
            id_key (str): GraphQL variable key (e.g., productId, variantId).
            response_key (str): Key used to extract response data (e.g., product, productVariant).
            query (str): GraphQL query used to fetch remaining metafields.
            odoo_record (recordset): Odoo record (product template or variant) for logging/reference.
            mk_log_line_dict (dict): Dictionary contains log details.
            queue_line_id (Recordset): Recordset of mk.queue.line.
        Returns:
            tuple: (list of metafields, bool indicating whether pagination completed without errors)
        """
        metafields = []
        metafield_data = shopify_res.get('metafields', [])

        # Task: T7725 - Added defensive pagination handling for single-page Shopify responses.
        if isinstance(metafield_data, list) and metafield_data:
            last_item = metafield_data[-1]
            # Detect pageInfo wrapper by content to avoid dropping the last real metafield.
            if isinstance(last_item, dict) and set(last_item.keys()) == {'pageInfo'}:
                metafields.extend(metafield_data[:-1])
                page_info = last_item.get('pageInfo', {})
            else:
                metafields.extend(metafield_data)
                page_info = {}
        else:
            page_info = {}

        remaining_metafields, is_complete = self._fetch_all_shopify_product_remaining_metafields(
            mk_instance_id=mk_instance_id,
            resource_mk_id=resource_mk_id,
            id_key=id_key,
            response_key=response_key,
            query=query,
            page_info=page_info,
            template_id=odoo_record,
            mk_log_line_dict=mk_log_line_dict,
            queue_line_id=queue_line_id
        )

        if remaining_metafields:
            metafields.extend(remaining_metafields)

        return metafields, is_complete

    def _get_odoo_variant_from_shopify(self, mk_instance_id, variant_mk_id):
        """
        T6290 - This method fetches the corresponding Odoo product variant using Shopify variant ID.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            variant_mk_id (str): Shopify GraphQL variant ID.
        Returns:
            recordset: Odoo product.product record if found, otherwise False.
        """
        variant_mk_id = str(extract_numeric_id(variant_mk_id))
        listing_item = (self.env['mk.listing.item'].search([
            ('mk_id', '=', variant_mk_id),
            ('mk_instance_id', '=', mk_instance_id.id)
        ], limit=1))
        return listing_item.product_id if listing_item else False

    def import_product_metafield_from_shopify(self, mk_instance_id, mk_id, odoo_product_template, mk_log_id=False, queue_line_id=False):
        """
        T6290 - This method imports product and variant metafield values from Shopify into Odoo.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            mk_id (str): Shopify product ID.
            odoo_product_template (recordset): Recordset of product.template.
            mk_log_id (recordset): Recordset of mk.log.
            queue_line_id (recordset): Recordset of mk.queue.job.line.
        Returns:
            bool: Returns True on successful operation completion, otherwise False.
        """
        resources = mk_instance_id.enable_metafield and mk_instance_id.metafield_resource_ids.filtered(lambda r: r.active_sync and r.shopify_owner_type in ['PRODUCT', 'PRODUCTVARIANT'])
        if not resources:
            return True

        new_log = False
        if not mk_log_id:
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
            new_log = True

        mk_log_line_dict = {'error': [], 'success': []}
        try:
            mk_instance_id.connection_to_shopify()
            graphql_product_id = f"gid://shopify/Product/{mk_id}"
            variables = {"productId": graphql_product_id}
            response = mk_instance_id.execute_graphql_query(FETCH_PRODUCT_AND_VARIANT_METAFIELDS, variables=variables)
            if response and response.get('errors'):
                log_message = _("IMPORT LISTING: Shopify error while fetching product and variant metafield values for %s (%s): %s") % (
                    odoo_product_template.display_name, mk_id, response.get('errors'))
                mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False})
                return False

            product_data = response and response.get('data', {}) and response.get('data', {}).get('product', {})
            if not product_data:
                log_message = _("IMPORT LISTING: Unable to import metafields for product %s (%s) because no metafield data was found in Shopify") % (
                    odoo_product_template.display_name, mk_id)
                mk_log_line_dict['error'].append({
                    'log_message': log_message,
                    'queue_job_line_id': queue_line_id.id if queue_line_id else False,
                })
                return False

            # ==========================================
            # Product Metafields
            # ==========================================
            if resources.filtered(lambda r: r.shopify_owner_type == 'PRODUCT'):
                product_metafields, is_complete_product = self._collect_shopify_metafield_values(
                    mk_instance_id=mk_instance_id,
                    shopify_res=product_data,
                    resource_mk_id=graphql_product_id,
                    id_key="productId",
                    response_key="product",
                    query=GET_REMAINING_PRODUCT_METAFIELD,
                    odoo_record=odoo_product_template,
                    mk_log_line_dict=mk_log_line_dict,
                    queue_line_id=queue_line_id
                )
                if product_metafields or is_complete_product:
                    mk_instance_id.import_specific_type_metafield_from_shopify(
                        odoo_product_template,
                        'PRODUCT',
                        product_metafields,
                        mk_instance_id.set_shopify_reference_metafield_value,
                        mk_log_line_dict=mk_log_line_dict,
                        wipe_unmatched=is_complete_product,
                        queue_line_id=queue_line_id,
                        mk_log_id=mk_log_id,
                        mk_id=mk_id
                    )

            # ==========================================
            # Variant Metafields
            # ==========================================
            if resources.filtered(lambda r: r.shopify_owner_type == 'PRODUCTVARIANT'):
                variants = product_data.get('variants', {}).get('nodes', [])
                for variant_node in variants:
                    variant_mk_id = variant_node.get('id')
                    if not variant_mk_id:
                        continue

                    odoo_variant = self._get_odoo_variant_from_shopify(mk_instance_id, variant_mk_id)

                    if not odoo_variant:
                        continue

                    variant_metafields, is_complete_product = self._collect_shopify_metafield_values(
                        mk_instance_id=mk_instance_id,
                        shopify_res=variant_node,
                        resource_mk_id=variant_mk_id,
                        id_key="variantId",
                        response_key="productVariant",
                        query=GET_REMAINING_PRODUCT_VARIANT_METAFIELD,
                        odoo_record=odoo_variant,
                        mk_log_line_dict=mk_log_line_dict,
                        queue_line_id=queue_line_id
                    )

                    if variant_metafields or is_complete_product:
                        mk_instance_id.import_specific_type_metafield_from_shopify(
                            odoo_variant,
                            'PRODUCTVARIANT',
                            variant_metafields,
                            mk_instance_id.set_shopify_reference_metafield_value,
                            mk_log_line_dict=mk_log_line_dict,
                            wipe_unmatched=is_complete_product,
                            queue_line_id=queue_line_id,
                            mk_log_id=mk_log_id,
                            mk_id=str(extract_numeric_id(variant_mk_id))
                        )

        except Exception as e:
            log_message = f"IMPORT LISTING: Unexpected error while fetching metafields for {odoo_product_template.display_name} ({mk_id}): {str(e)}"
            mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False})

        finally:
            if new_log:
                self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
            else:
                if mk_log_line_dict['error'] or mk_log_line_dict['success']:
                    self.env['mk.log'].create_update_log(
                        mk_instance_id=mk_instance_id,
                        mk_log_id=mk_log_id,
                        mk_log_line_dict=mk_log_line_dict,
                    )
        return True

    def shopify_update_listing_metafields_to_mk(self, mk_log_id=False):
        """
        T6290 - This method updates metafield values from Odoo to Shopify.
        Args:
             mk_log_id (recordset): Recordset of mk.log.
        Returns:
            bool: Returns True on successful operation completion.
        Raises:
            Exception: If an unexpected error occurs during metafield update to Shopify.
        """
        self.ensure_one()
        mk_instance_id = self.mk_instance_id
        resources = mk_instance_id.enable_metafield and mk_instance_id.metafield_resource_ids.filtered(lambda r: r.active_sync and r.shopify_owner_type in ['PRODUCT', 'PRODUCTVARIANT'])
        if not resources:
            return True

        new_log = False
        if not mk_log_id.exists():
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
            new_log = True
        mk_log_line_dict = {'error': [], 'success': []}

        try:
            # Update Product-level Metafields
            if resources.filtered(lambda r: r.shopify_owner_type == 'PRODUCT'):
                self._execute_batched_shopify_metafield_update(
                    mk_instance_id=mk_instance_id,
                    odoo_record=self.product_tmpl_id,
                    owner_type='PRODUCT',
                    mk_record=self,
                    mk_log_line_dict=mk_log_line_dict,
                )

            # Update Variant-level Metafields
            if resources.filtered(lambda r: r.shopify_owner_type == 'PRODUCTVARIANT'):
                for item in self.listing_item_ids:
                    if item.mk_id:
                        self._execute_batched_shopify_metafield_update(
                            mk_instance_id=mk_instance_id,
                            odoo_record=item.product_id,
                            owner_type='PRODUCTVARIANT',
                            mk_record=item,
                            mk_log_line_dict=mk_log_line_dict,
                        )
        except Exception as e:
            log_message = f"UPDATE LISTING: Unexpected error updating metafields for {self.name}: {str(e)}"
            mk_log_line_dict['error'].append({'log_message': log_message})

        finally:
            if new_log:
                self._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
            elif mk_log_line_dict['error'] or mk_log_line_dict['success']:
                self.env['mk.log'].create_update_log(
                    mk_instance_id=mk_instance_id,
                    mk_log_id=mk_log_id,
                    mk_log_line_dict=mk_log_line_dict,
                )

        return True

    def _handle_shopify_metaobject_definition_mismatch_error(self, mk_instance_id, failed_item, error_msg, mk_log_line_dict, owner_label, mk_record, failed_key):
        """Task: T9096 - Detect and recover from a metaobject-reference set failure caused by a deleted entry.

        Shopify rejects a metaobject_reference value with "Value must belong to the
        specified metaobject definition" both when the value truly has the wrong type
        AND when the referenced entry was deleted in Shopify after Odoo last saw it. The
        two cases need different handling, so this re-checks the referenced ids against
        Shopify: any id that no longer resolves is genuinely deleted and is handled via
        handle_deleted_in_shopify; a mismatch is left to the caller's generic error log.

        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            failed_item (dict): The metafield dict from the failed batch (has 'value').
            error_msg (str): The Shopify userErrors message for this field.
            mk_log_line_dict (dict): Log dictionary to store success/error messages.
            owner_label (str): Human label for the owning resource (e.g. "product").
            mk_record (recordset): Recordset of listing/product used for logging.
            failed_key (str): The metafield key that failed.
        Returns:
            bool: True if the failure was a deleted-entry case and has been fully handled
                (caller should skip its own generic error log for this field), else False.
        """
        if 'Value must belong to the specified metaobject definition' not in error_msg:
            return False

        val_str = str(failed_item.get('value', ''))
        entry_mk_ids = re.findall(r'gid://shopify/Metaobject/(\d+)', val_str)
        if not entry_mk_ids:
            return False

        gids_to_check = [f"gid://shopify/Metaobject/{m_id}" for m_id in entry_mk_ids]
        res_check = mk_instance_id.execute_graphql_query(GET_METAOBJECTS_BY_IDS, variables={"ids": gids_to_check})
        nodes = (res_check or {}).get('data', {}).get('nodes', [])

        valid_mk_ids = [str(extract_numeric_id(n['id'])) for n in nodes if n and n.get('id')]
        actually_deleted_mk_ids = [m_id for m_id in entry_mk_ids if m_id not in valid_mk_ids]
        if not actually_deleted_mk_ids:
            return False

        deleted_entries = self.env['shopify.metaobject.entry.ts'].search([
            ('mk_id', 'in', actually_deleted_mk_ids),
            ('mk_instance_id', '=', mk_instance_id.id)
        ])
        if not deleted_entries:
            return False

        deleted_entries.handle_deleted_in_shopify(mk_log_line_dict, owner_label, mk_record, failed_key)
        return True

    def _update_shopify_metafield_values(self, mk_instance_id, resource_id, metafields_to_set, mk_record, mk_log_line_dict, owner_label):
        """
        T6290 - Executes 'Set' mutations in batches of 25. Filters invalid data and retries clean chunks.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            resource_id (str): Shopify resource GID (ownerId).
            metafields_to_set (list): List of metafield dictionaries to update.
            mk_record (recordset): Recordset of listing/product used for logging.
            mk_log_line_dict (dict): Log dictionary to store success/error messages.
        """
        for item in metafields_to_set:
            item['ownerId'] = resource_id

        chunk_size = 25
        for i in range(0, len(metafields_to_set), chunk_size):
            chunk = metafields_to_set[i:i + chunk_size]

            # --- FIRST ATTEMPT ---
            variables = {"metafields": chunk}
            response = mk_instance_id.execute_graphql_query(UPDATE_RESOURCE_METAFIELDS, variables=variables)
            result = response and response.get('data', {}) and response.get('data', {}).get('metafieldsSet', {})
            user_errors = result and result.get('userErrors', [])

            if not user_errors:
                continue

            # --- ERROR HANDLING ---
            failed_indices = []
            for error in user_errors:
                error_field = error.get('field', [])
                if len(error_field) > 1:
                    idx = int(error_field[1])
                    failed_indices.append(idx)
                    failed_key = chunk[idx]['key']
                    error_msg = error.get('message', 'Unknown Error')

                    metafield_label = mk_instance_id.metafield_resource_ids.mapping_ids.filtered(
                        lambda m: m.namespace_and_key == f"{chunk[idx]['namespace']}.{failed_key}")[:1].name or failed_key
                    if self._handle_shopify_metaobject_definition_mismatch_error(
                            mk_instance_id, chunk[idx], error_msg, mk_log_line_dict, owner_label, mk_record, metafield_label):
                        continue
                    log_message = _(
                        "UPDATE LISTING: Failed to update metafield %(metafield)s on %(owner_label)s %(record_name)s (%(mk_id)s)\n"
                        "Reason: Shopify rejected the value: %(error)s\n"
                        "How to fix:\n"
                        "  • Correct the value of %(metafield)s in Odoo, then re-run this metafield update"
                    ) % {'metafield': metafield_label, 'owner_label': owner_label,
                         'record_name': mk_record.display_name, 'mk_id': mk_record.mk_id, 'error': error_msg}
                    mk_log_line_dict['error'].append({'log_message': log_message})

            # --- SECOND ATTEMPT (Cleaned Chunk) ---
            cleaned_chunk = [item for idx, item in enumerate(chunk) if idx not in failed_indices]
            if cleaned_chunk:
                mk_instance_id.execute_graphql_query(UPDATE_RESOURCE_METAFIELDS, variables={"metafields": cleaned_chunk})

    def _delete_shopify_metafield_values(self, mk_instance_id, resource_id, metafields_to_delete, mk_record, mk_log_line_dict):
        """
        T6290 - Executes 'Delete' mutations in batches of 25.
        Delete Shopify metafield values from odoo in batches using GraphQL mutations.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            resource_id (str): Shopify resource GID (ownerId).
            metafields_to_delete (list): List of metafield dictionaries to delete.
            mk_record (recordset): Recordset of listing/product used for logging.
            mk_log_line_dict (dict): Log dictionary to store error messages.
        """
        for item in metafields_to_delete:
            item['ownerId'] = resource_id

        chunk_size = 25
        for i in range(0, len(metafields_to_delete), chunk_size):
            chunk = metafields_to_delete[i:i + chunk_size]
            response = mk_instance_id.execute_graphql_query(DELETE_SPECIFIC_METAFIELD_VALUE, variables={"metafields": chunk})

            user_errors = response.get('data', {}).get('metafieldsDelete', {}).get('userErrors', [])
            # --- ERROR HANDLING ---
            if user_errors:
                for error in user_errors:
                    error_msg = error.get('message', '')
                    log_message = _("UPDATE LISTING: Failed to delete Shopify Metafield on product %s (%s): %s") % (mk_record.display_name, mk_record.mk_id, error_msg)
                    mk_log_line_dict['error'].append({'log_message': log_message})

    def _execute_batched_shopify_metafield_update(self, mk_instance_id, odoo_record, owner_type, mk_record, mk_log_line_dict):
        """
        T6290 - Execute batched Shopify metafield updates (set and delete) for a given record.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            odoo_record (recordset): Odoo record (product/template/variant) used to prepare metafield values.
            owner_type (str): Shopify owner type (e.g., 'PRODUCT', 'PRODUCTVARIANT').
            mk_record (recordset): Recordset of listing or listing item.
            mk_log_line_dict (dict): Log dictionary to store success and error messages.
        Returns:
            bool: True if execution completes.
        """
        metafields_to_set, metafields_to_delete = self.update_product_metafields_to_shopify(mk_instance_id, odoo_record, owner_type, mk_log_line_dict, mk_record.mk_id)
        owner_label = 'listing' if owner_type == 'PRODUCT' else 'listing item'

        if not metafields_to_set and not metafields_to_delete:
            return True
        try:
            resource_type = 'Product' if owner_type == 'PRODUCT' else 'ProductVariant'
            resource_id = f"gid://shopify/{resource_type}/{mk_record.mk_id}"

            # ==========================================
            # PROCESS "UPDATE" MUTATIONS
            # ==========================================
            if metafields_to_set:
                self._update_shopify_metafield_values(mk_instance_id, resource_id, metafields_to_set, mk_record, mk_log_line_dict, owner_label)

            # ==========================================
            # PROCESS "DELETE" MUTATIONS
            # ==========================================
            if metafields_to_delete:
                self._delete_shopify_metafield_values(
                    mk_instance_id, resource_id, metafields_to_delete, mk_record, mk_log_line_dict
                )

            success_msg = _("UPDATE LISTING: Successfully processed metafield(s) for %s %s (%s)") % (owner_label, mk_record.display_name, mk_record.mk_id)
            mk_log_line_dict['success'].append({'log_message': success_msg})

        except Exception as e:
            log_message = f"UPDATE LISTING: Unexpected error while updating metafields for {owner_label} product {mk_record.display_name} ({mk_record.mk_id}): {str(e)}"
            mk_log_line_dict['error'].append({'log_message': log_message})

        return True

    def update_product_metafields_to_shopify(self, mk_instance_id, target_odoo_record, shopify_owner_type, mk_log_line_dict, mk_id=False, mappings=None):
        """
        T6290- Gathers mapped Odoo fields and packages them into Shopify's input format.
        Prepare Shopify metafield data for update and deletion based on Odoo field mappings.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            target_odoo_record (recordset): Odoo record (template/variant) from which values are read.
            shopify_owner_type (str): Shopify owner type (e.g., 'PRODUCT', 'PRODUCTVARIANT').
            mk_log_line_dict (dict): Log dictionary to capture preparation errors.
            mk_id (str): Marketplace id of listing or listing item.
            mappings (recordset): Task: T7609 - Already searched shopify.metafield.mapping.ts records. Passed by the
                bulk flow so the mapping search runs ONCE per batch instead of once per product/variant.
        Returns:
            tuple:
                - list: Metafields to set (update/create in Shopify).
                - list: Metafields to delete from Shopify.
        """
        mappings = mappings if mappings is not None else self.env['shopify.metafield.mapping.ts'].sudo().search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('resource_id.shopify_owner_type', '=', shopify_owner_type),
            ('active_mapping', '=', True),
            ('mapping_status', '=', 'ready'),
            ('odoo_field_id', '!=', False)
        ])

        metafields_to_set, metafields_to_delete = [], []
        owner_label = 'listing' if shopify_owner_type == 'PRODUCT' else 'listing item'
        for mapping in mappings:
            try:
                # Task: T9096 - Checked before the empty-value test below, which would otherwise queue a delete for it.
                if 'metaobject_reference' in (mapping.types or '') and not mk_instance_id.enable_metaobject:
                    mk_log_line_dict['error'].append({'log_message': _(
                        "UPDATE LISTING: Skipped to set metafield %(mapping_name)s on %(owner_label)s %(display_name)s (%(mk_id)s)\n"
                        "Reason: Metaobject Functionality is turned off for instance (%(instance)s), so this value cannot be set in Shopify.\n"
                        "How to fix:\n"
                        "  • Open the instance, go to the Metafields tab, and turn on Metaobject Functionality."
                    ) % {'mapping_name': mapping.name, 'owner_label': owner_label, 'display_name': target_odoo_record.display_name,
                         'mk_id': mk_id, 'instance': mk_instance_id.name}})
                    continue
                raw_value = getattr(target_odoo_record, mapping.odoo_field_id.name)
                key = mapping.namespace_and_key.split('.', 1)[1]
                if not raw_value and (mapping.types != 'boolean'):
                    metafields_to_delete.append({"namespace": mapping.namespace, "key": key})
                    continue
                if mapping.types == 'rating' and ((mapping.scale_min == 0 and mapping.scale_max == 0) or (raw_value == 0)):
                    log_message = _("UPDATE LISTING: Skipped rating metafield %s for %s %s (%s) because the rating scale or value is not properly configured.") % (
                        mapping.name, owner_label, target_odoo_record.display_name, mk_id
                    )
                    mk_log_line_dict['error'].append({'log_message': log_message})
                    continue
                formatted_value = mk_instance_id._prepare_shopify_metafield_value_for_update(target_odoo_record, mapping, raw_value, self.prepare_shopify_reference_value_for_update,
                                                                                             mk_log_line_dict, mk_id)
                if formatted_value is False or formatted_value is None:
                    continue

                # if formatted_value is not None:
                metafields_to_set.append({
                    "namespace": mapping.namespace,
                    "key": key,
                    "type": mapping.types,
                    "value": formatted_value
                })
            except Exception as e:
                log_message = (
                    f"UPDATE LISTING: Error while preparing value for metafield "
                    f"{mapping.name} on {owner_label} {target_odoo_record.display_name} ({mk_id}): "
                    f"Error: {str(e)}"
                )
                mk_log_line_dict['error'].append({'log_message': log_message})
        return metafields_to_set, metafields_to_delete

    def prepare_shopify_metafield_mappings_by_owner(self, mk_instance_id):
        """
        Task: T7609 - Read the active metafield mappings ONCE for a whole bulk batch and split them by
        Shopify owner type, so `update_product_metafields_to_shopify` never searches per product/variant.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
        Returns:
            dict: {'PRODUCT': mappings recordset, 'PRODUCTVARIANT': mappings recordset}.
        """
        metafield_mapping_obj = self.env['shopify.metafield.mapping.ts'].sudo()
        mappings_by_owner = {'PRODUCT': metafield_mapping_obj, 'PRODUCTVARIANT': metafield_mapping_obj}
        resources = mk_instance_id.enable_metafield and mk_instance_id.metafield_resource_ids.filtered(lambda r: r.active_sync and r.shopify_owner_type in ['PRODUCT', 'PRODUCTVARIANT'])
        if not resources:
            return mappings_by_owner

        active_owner_types = resources.mapped('shopify_owner_type')
        metafield_mapping_ids = metafield_mapping_obj.search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('resource_id.shopify_owner_type', 'in', active_owner_types),
            ('active_mapping', '=', True),
            ('mapping_status', '=', 'ready'),
            ('odoo_field_id', '!=', False)
        ])
        for owner_type in active_owner_types:
            mappings_by_owner[owner_type] = metafield_mapping_ids.filtered(lambda m: m.resource_id.shopify_owner_type == owner_type)
        return mappings_by_owner

    def attach_shopify_bulk_metafields(self, mk_instance_id, metafield_mappings, prepare_data_dict, list_of_variants, mk_log_line_dict):
        """
        Task: T7609 - Attach metafield values to the productSet bulk payload of ONE listing.
        ProductSetInput and ProductVariantSetInput both accept `metafields`, so metafield values travel
        with the product/variant data inside the SAME bulk mutation - no separate bulk query is needed
        for the 'set' side, and it also works on export where the Shopify ids do not exist yet.
        Values are prepared by the existing `update_product_metafields_to_shopify` method.
        Deletions are NOT supported by productSet: they are handled by the chained metafieldsDelete bulk.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            metafield_mappings (dict): Mappings by owner type from prepare_shopify_metafield_mappings_by_owner.
            prepare_data_dict (dict): productSet input of this listing, updated in place.
            list_of_variants (list): ProductVariantSetInput dictionaries of this listing, updated in place.
            mk_log_line_dict (dict): Log dictionary to store error messages.
        Returns:
            bool: True when done.
        """
        self.ensure_one()
        product_mappings = metafield_mappings.get('PRODUCT', {})
        variant_mappings = metafield_mappings.get('PRODUCTVARIANT', {})

        if product_mappings:
            metafields_to_set, metafields_to_delete = self.update_product_metafields_to_shopify(mk_instance_id, self.product_tmpl_id, 'PRODUCT', mk_log_line_dict, self.mk_id,
                                                                                                mappings=product_mappings)
            if metafields_to_set:
                prepare_data_dict['metafields'] = metafields_to_set

        if variant_mappings and list_of_variants:
            # The variant input dictionaries are built by different branches (with or without id), so index
            # them by every key that can identify a variant and match the listing item against that index.
            variant_input_by_key = {}
            for variant_vals in list_of_variants:
                for variant_key in [variant_vals.get('id'), variant_vals.get('sku'), variant_vals.get('barcode')]:
                    if variant_key and variant_key not in variant_input_by_key:
                        variant_input_by_key[variant_key] = variant_vals

            for listing_item_id in self.listing_item_ids:
                variant_vals = False
                item_keys = [listing_item_id.mk_id and f"gid://shopify/ProductVariant/{listing_item_id.mk_id}", listing_item_id.default_code,
                             listing_item_id.barcode or listing_item_id.product_id.barcode]
                for variant_key in item_keys:
                    variant_vals = variant_key and variant_input_by_key.get(variant_key)
                    if variant_vals:
                        break
                if not variant_vals:
                    continue
                metafields_to_set, metafields_to_delete = self.update_product_metafields_to_shopify(mk_instance_id, listing_item_id.product_id, 'PRODUCTVARIANT', mk_log_line_dict,
                                                                                                    listing_item_id.mk_id, mappings=variant_mappings)
                if metafields_to_set:
                    variant_vals['metafields'] = metafields_to_set
        return True

    def prepare_shopify_reference_value_for_update(self, target_odoo_record, metafield_value, mapping, mk_log_line_dict, mk_id):
        """
        T6290 - Prepare Shopify reference-type metafield values (product/variant) for update.
        Args:
            target_odoo_record (recordset): The main Odoo product/variant currently being exported.
            metafield_value (recordset/list): Odoo record(s) containing reference values.
            mapping (recordset): Recordset of shopify.metafield.mapping.ts.
            mk_log_line_dict (dict): Log dictionary to capture missing reference warnings.
            mk_id (str): Marketplace id of listing or listing item.
        Returns:
            str | None:
                - JSON string of GIDs for list reference types.
                - Single GID string for single reference types.
                - None if no valid reference is found.
        """
        metafield_type = mapping.types
        is_list = 'list.' in metafield_type

        # --- Metaobject reference: the GID comes from the entry record, not a listing ---
        if 'metaobject_reference' in metafield_type:
            entries = metafield_value if is_list else (metafield_value and [metafield_value] or [])
            gid_list, missing_entries = [], []
            for entry in entries:
                if not entry:
                    continue
                if entry.mk_id:
                    gid_list.append(f"gid://shopify/Metaobject/{entry.mk_id}")
                else:
                    missing_entries.append(f"{entry._shopify_entry_label()} ({entry.definition_id.name})")

            if missing_entries:
                owner_label = 'listing' if mapping.resource_id.shopify_owner_type == 'PRODUCT' else 'listing item'
                mk_log_line_dict['error'].append({'log_message': _(
                    "UPDATE LISTING: Skipped to set metafield %(mapping_name)s on %(owner_label)s %(display_name)s (%(mk_id)s)\n"
                    "Reason: the following metaobject entries have not been synced to Shopify yet:\n"
                    "%(missing)s\n"
                    "How to fix:\n"
                    "  \u2022 Open above mentioned entry in Marketplaces > Shopify > Catalogs > Metaobject Entries, click Sync to Shopify, then re-run this metafield update"
                ) % {'mapping_name': mapping.name, 'owner_label': owner_label, 'display_name': target_odoo_record.display_name,
                     'mk_id': mk_id, 'missing': "  \u2022 " + "\n  \u2022 ".join(missing_entries)}})

            if is_list:
                # Never send a partial list: it would silently shrink the Shopify metafield.
                return False if missing_entries else json.dumps(gid_list)
            return gid_list[0] if gid_list else None

        # Determine Resource Type and Relational Field dynamically
        is_product = 'product_reference' in metafield_type

        resource = 'Product' if is_product else 'ProductVariant'
        relational_field = 'mk_listing_ids' if is_product else 'mk_listing_item_ids'
        owner_label = 'listing' if mapping.resource_id.shopify_owner_type == 'PRODUCT' else 'listing item'
        reference_type = 'product' if is_product else 'variant'
        listing_label = 'listing' if is_product else 'listing item'

        gid_list = []
        missing_records = []

        records = metafield_value if is_list else [metafield_value]
        for rec in records:
            if not rec:
                continue

            # Dynamically fetch either 'mk_listing_ids' or 'mk_listing_item_ids'
            references = getattr(rec, relational_field)
            synced_ref = references.filtered(lambda x: x.mk_instance_id.id == mapping.mk_instance_id.id and x.mk_id)

            if synced_ref:
                gid_list.append(f"gid://shopify/{resource}/{synced_ref[0].mk_id}")
            else:
                missing_records.append(rec.display_name)

        # Handle Warnings globally
        if missing_records:
            log_message = _("UPDATE LISTING: Skipped to set metafield %(mapping_name)s on %(owner_label)s %(display_name)s (%(mk_id)s)\n"
                            "\n"
                            "Reason: The following referenced %(reference_type)s(s) do not have a corresponding %(listing_label)s in Odoo:\n"
                            "%(missing_records)s\n"
                            "\n"
                            "How to fix:\n"
                            "  1. If these %(reference_type)s(s) are new - export them to Shopify.\n"
                            "  2. If they already exist on Shopify - import them into Odoo first.\n"
                            "\n"
                            "Once all referenced %(reference_type)s(s) corresponding %(listing_label)ss are available in Odoo, re-run this metafield update") % {
                              'mapping_name': mapping.name,
                              'owner_label': owner_label,
                              'display_name': target_odoo_record.display_name,
                              'mk_id': mk_id,
                              'reference_type': reference_type,
                              'listing_label': listing_label,
                              'missing_records': "  • " + "\n  • ".join(missing_records),
                          }

            mk_log_line_dict['error'].append({'log_message': log_message})

        # Return the correct format based on the metafield type
        if is_list:
            # Some/all references are missing locally — don't send a partial list, which would silently shrink the Shopify metafield.
            if missing_records:
                return False
            return json.dumps(gid_list)
        else:
            # Return the single string if found, otherwise None
            return gid_list[0] if gid_list else None
