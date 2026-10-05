import base64
import hashlib
import hmac
import json
import logging
import re
import secrets
import threading
import time
import urllib
import odoo

from odoo.modules.module import get_modules
from datetime import datetime, date
from urllib.parse import urlparse
from uuid import uuid4

from odoo.exceptions import RedirectWarning
from odoo.tools import file_path

from odoo import models, fields, api, tools, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.base_marketplace.models.misc import check_go_live
from odoo.addons.shopify import shopify
from odoo.addons.shopify.models.graphql_queries import DELETE_SHOPIFY_SUBSCRIPTION, GRAPHQL_QUERY_FIND_WEBHOOKS, STORE_CURRENCY, SHOPIFY_ACCESS_SCOPES, GET_PRODUCT_PUBLICATIONS, \
    GET_PRODUCTS_BY_IDS, GET_VARIANT_PUBLICATIONS
from odoo.addons.shopify.models.misc import process_response, extract_numeric_id, convert_html_to_shopify_rich_text, _convert_shopify_rich_text_to_html, \
    convert_shopify_metafield_measurement

_logger = logging.getLogger("Teqstars:Shopify")

ACCOUNT_STATE = [('not_confirmed', 'Not Confirmed'), ('confirmed', 'Confirmed')]
# How many attempts before giving up (rate limit / transient transport failures).
RETRIES = 5
# HTTP status codes that are worth retrying (rate limit + transient server errors).
RETRYABLE_HTTP_STATUS = {429, 430, 500, 502, 503, 504}
# Don’t go below this many “points” before pausing
SAFE_THRESHOLD = 100

SHOPIFY_OWNER_LABELS = {
    'PRODUCT': 'listing',
    'PRODUCTVARIANT': 'listing item',
    'ORDER': 'order',
    'CUSTOMER': 'customer',
}

SHOPIFY_LOG_TITLES = {
    'PRODUCT': 'LISTING',
    'PRODUCTVARIANT': 'LISTING ITEM',
    'ORDER': 'ORDER',
    'CUSTOMER': 'CUSTOMER',
}


class MkInstance(models.Model):
    _inherit = "mk.instance"

    def _get_mk_kanban_counts(self):
        super(MkInstance, self)._get_mk_kanban_counts()
        for mk_instance_id in self:
            mk_instance_id.shopify_collection_count = len(mk_instance_id.shopify_collection_ids)
            mk_instance_id.shopify_location_count = len(mk_instance_id.shopify_location_ids)
            mk_instance_id.shopify_payout_count = len(mk_instance_id.shopify_payout_ids)
            mk_instance_id.shopify_catalog_count = len(mk_instance_id.shopify_catalog_ids)

    def _get_default_fulfillment_status(self):
        fulfillment_status_id = self.env.ref('shopify.shopify_order_status_unshipped', raise_if_not_found=False)
        return [(6, 0, [fulfillment_status_id.id])] if fulfillment_status_id else False

    def _get_shopify_discount_product(self):
        return self.env.ref('shopify.shopify_discount', raise_if_not_found=False) or False

    def _get_shopify_delivery_product(self):
        return self.env.ref('shopify.shopify_delivery', raise_if_not_found=False) or False

    def shopify_mk_default_api_limit(self):
        return 250

    def shopify_shown_in_onboarding_picker(self):
        return True

    marketplace = fields.Selection(selection_add=[('shopify', "Shopify")], string='Marketplace')
    password = fields.Char("Password", copy=False, groups="base_marketplace.group_base_marketplace_manager")
    shop_url = fields.Char("Shopify Shop URL", copy=False, help="Exp. https://teqstars.myshopify.com")
    is_token = fields.Boolean("I have API Access Token", default=True, help="You can find Admin API Access token from Shopify Apps.", copy=False)
    api_token = fields.Char("API access token", copy=False, groups="base_marketplace.group_base_marketplace_manager")

    # Sale Orders Fields
    fulfillment_status_ids = fields.Many2many('shopify.order.status', 'marketplace_order_status_rel', 'mk_instance_id', 'status_id', "Shopify Fulfillment Status",
                                              default=_get_default_fulfillment_status, help="Filter orders by their fulfillment status at the time of Import Orders.")
    financial_workflow_config_ids = fields.One2many("shopify.financial.workflow.config", "mk_instance_id", "Shopify Financial Workflow Configuration")
    is_fetch_fraud_analysis_data = fields.Boolean("Fetch Fraud Analysis Data?", default=True, help="It will fetch detail of Fraud Analysis and show in the Order Form view.")
    shopify_import_after_order = fields.Datetime("Shopify Import Order After", copy=False, help="Orders will be import after this date.")
    custom_product_id = fields.Many2one('product.product', string='Shopify Custom Product', ondelete="restrict",
                                        help="Shopify order with having custom item will be imported with this product in order.")
    custom_storable_product_id = fields.Many2one('product.product', string='Shopify Custom Storable Product', ondelete="restrict",
                                                 help="Shopify order with having custom fulfillable item will be imported with this product in order.")
    default_pos_customer_id = fields.Many2one('res.partner', string='Default POS Customer', ondelete="restrict",
                                              domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('customer_rank','>', 0)]",
                                              help="If customer is not found in POS Orders then set this customer.")
    gift_card_product_id = fields.Many2one('product.product', string='Shopify Gift Card Product', domain=[('type', '=', 'service')], ondelete="restrict",
                                           help="Shopify gift card orders will be imported with this product (Only Service type product).")
    tip_product_id = fields.Many2one('product.product', string='Tip Product', domain=[('type', '=', 'service')], ondelete="restrict",
                                     help="Shopify Tip order line will be imported with this product (Only Service type product).")
    duties_product_id = fields.Many2one('product.product', string='Duties Product', domain=[('type', '=', 'service')], ondelete="restrict",
                                        help="Shopify Duties order line will be imported with this product (Only Service type product).")
    special_tax_label = fields.Char("Special State Tax Label", copy=False, help="")
    mark_order_paid_from_odoo = fields.Boolean("Mark Order as Paid?", default=False, copy=False,
                                               help="Use this feature to allow marking the order as paid in Shopify from Odoo when Odoo order is fully paid. Disable it if the payment status should only be updated automatically from Shopify.")

    # Email & Notification
    is_notify_customer = fields.Boolean("Shopify Notify Customer?", default=False,
                                        help="Whether the customer should be notified. If set to true, then an email will be sent when the fulfillment is created or updated.")

    # Webhook
    webhook_url = fields.Char("Shopify Webhook URL", copy=False)
    webhook_ids = fields.One2many("shopify.webhook.ts", "mk_instance_id", "Shopify Webhooks")
    webhook_uuid = fields.Char(string="Shopify Webhook UUID", readonly=True, copy=False, groups="base_marketplace.group_base_marketplace_manager")

    # Dashboard fields
    shopify_collection_ids = fields.One2many('shopify.collection.ts', 'mk_instance_id', string="Collections")
    shopify_collection_count = fields.Integer("Collection Count", compute='_get_mk_kanban_counts')
    shopify_location_ids = fields.One2many('shopify.location.ts', 'mk_instance_id', string="Shopify Locations")
    shopify_location_count = fields.Integer("Shopify Location Count", compute='_get_mk_kanban_counts')
    shopify_payout_ids = fields.One2many('shopify.payout', 'mk_instance_id', string="Payouts")
    shopify_payout_count = fields.Integer("Payout Count", compute='_get_mk_kanban_counts')
    shopify_catalog_ids = fields.One2many('shopify.catalog.ts', 'mk_instance_id', string="Catalogs")
    shopify_catalog_count = fields.Integer("Catalog Count", compute='_get_mk_kanban_counts')

    # Customer Fields.
    is_create_company_contact = fields.Boolean("Shopify Create Company Contact?", default=False, help="It will create company contact if found company while creating Customer.")

    # Returns Fields
    last_return_import_date = fields.Datetime("Shopify Last Return Imported On",
                                              help="Last successful Shopify return import. Future imports start from this date.")

    # Payout Fields
    payout_report_last_sync_date = fields.Date("Payout Last Sync Date")
    payout_journal_id = fields.Many2one('account.journal', string='Payout Journal', domain="[('company_id', '=', company_id)]")
    is_payout_auto_process = fields.Boolean("Auto Process Payout Report?",
                                            help="System will automatically process/reconcile payout report with invoice at the time of import payout process.")
    payout_account_config_ids = fields.One2many('shopify.payout.account.config', 'mk_instance_id', string="Payout Account Config")

    need_sync_shopify_sales_channels = fields.Boolean(string="Need Sync Sales Channels?", default=False, help="Automatically enabled when listings without a Sales Channel are found and need to be updated after migration. Disabled once all listings are updated.")
    need_sync_shopify_sales_channels_item = fields.Boolean(string="Need Sync Sales Channels for Listing Items?", default=False, help="Automatically enabled when listing items without a Sales Channel are found and need to be updated after migration. Disabled once all listing items are updated.")
    client_id = fields.Char(string='Shopify Client ID', copy=False, groups="base_marketplace.group_base_marketplace_manager", help="The API Client ID provided by Shopify when you create a Custom App.")
    secret_id = fields.Char(string='Shopify Secret', copy=False, groups="base_marketplace.group_base_marketplace_manager", help="The API Secret provided by Shopify when you create a Custom App.")
    redirect_url = fields.Char(string='Shopify Redirect URL', copy=False, help="The URL where Shopify redirects after authentication. Format: https://<your-domain>/external/oauth/callback.")
    auto_sync_inventory_to_shopify = fields.Boolean(string="Real-Time Inventory Sync to Shopify?", default=False, help="Enable this option to automatically sync product inventory from Odoo to Shopify in real-time whenever stock levels change.")

    enable_metafield = fields.Boolean(string="Enable Metafield Functionality?", help="Toggle to reveal configuration options for syncing Metafields.")
    enable_metaobject = fields.Boolean(string="Enable Metaobject Functionality?",
                                       help="Enable this to sync and manage Shopify Metaobjects for this instance, including fetching definitions and entries, creating or deleting entries, and importing referenced metaobjects from metafields. When disabled, these operations are skipped and logged.")
    metafield_resource_ids = fields.One2many('shopify.metafield.resource.ts', 'mk_instance_id', string="Metafield Resources")
    auto_sync_price_to_shopify = fields.Boolean(string="Real-Time Price Sync to Shopify", default=False, help="Enable this option to automatically update product prices in Shopify in real-time whenever prices are changed in Odoo (including sale price or pricelist updates).")

    def show_shopify_instance_redirect_warning(self, error_msg):
        """
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.
        Args:
            error_msg: Message to display in the warning.
        Raises:
            RedirectWarning: Opens the instance form view with the provided message.
        """
        mk_instance_form_view_id = self.env.ref('base_marketplace.marketplace_instance_form_view').id

        action_data = {
            'view_mode': 'form',
            'name': _('Instance'),
            'res_model': 'mk.instance',
            'type': 'ir.actions.act_window',
            'domain': [('id', '=', self.id)],
            'views': [[mk_instance_form_view_id, 'form']],
            'res_id': self.id,
            'context': self.env.context
        }

        raise RedirectWarning(error_msg, action_data, _("Open Instance"))

    def show_shopify_location_redirect_warning(self, error_msg, shopify_location_id):
        """
        Task: T7468 - Raise a redirect warning for the location with a dynamic error message and open the corresponding location form view.
        Args:
            error_msg : Message to display in the warning.
            shopify_location_id:
        Raises:
            RedirectWarning: Opens the location form view with the provided message.
        """
        location_tree_view_id = self.env.ref('shopify.shopify_location_tree_view').id
        location_form_view_id = self.env.ref('shopify.shopify_location_form_view').id

        action_data = {
            'res_model': 'shopify.location.ts',
            'type': 'ir.actions.act_window',
            'context': {'default_mk_instance_id': self.id}
        }

        if shopify_location_id and len(shopify_location_id) == 1:
            res_id = shopify_location_id.id
            action_data.update({
                'view_mode': 'form',
                'views': [(location_form_view_id, 'form')],
                'res_id': res_id,
            })
        else:
            action_data.update({
                'name': _('Locations'),
                'views': [
                    (location_tree_view_id, 'list'),
                    (location_form_view_id, 'form')
                ],
                'view_mode': 'list,form',
                'domain': [('mk_instance_id', '=', self.id)]
            })

        raise RedirectWarning(error_msg, action_data, _("Open Locations"))

    def action_apply_shopify_sales_channel_type_category(self):
        """
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Assigns sales channels to existing listings that are currently listed but do not have any sales channels assigned.
        Returns:
            bool: True when sales channels have been successfully applied to all listings.
        """
        config_param_model = self.env['ir.config_parameter']
        config_param_key = f'shopify.last_processed_listing_id_{self.id}'
        last_listing_id = int(config_param_model.get_param(config_param_key, 0))

        self.env.cr.execute("""
            SELECT id
            FROM mk_listing l
            WHERE l.mk_instance_id = %s
              AND l.is_listed = TRUE
              AND l.id > %s
              AND l.mk_id IS NOT NULL
              AND (
                  NOT EXISTS (
                  SELECT 1
                  FROM mk_listing_sales_channels_rel rel
                  WHERE rel.mk_listing_id = l.id
                  )
                  OR l.shopify_product_type_id IS NULL
                  OR l.shopify_product_category_id IS NULL
              )
            ORDER BY l.id ASC
        """, (self.id, last_listing_id))

        records = self.env.cr.fetchall()  # e.g. [(1,),(3,)]

        listings = [x[0] for x in records]
        listing_ids = self.env['mk.listing'].browse(listings)
        self.set_shopify_sales_channels_type_category_to_listing(listing_ids, config_param_key)

        self.need_sync_shopify_sales_channels = False
        # Task: T8254 -  set product type & category during sales-channel migration.
        self.env['shopify.product.category.ts'].fetch_category_from_shopify()
        param_record = config_param_model.search([('key', '=', config_param_key)], limit=1)
        param_record and param_record.unlink()
        return True

    def action_apply_shopify_sales_channel_item(self):
        """
        Task: T7796 - Populate Sales Channel field for existing Listing Items.
        Fetches listing items without sales channels and calls set_shopify_sales_channels_to_listing_item
        to assign channels via Shopify GraphQL. Supports resumption via config_param_key.
        Returns:
            bool: True when sales channels have been successfully applied to all listing items.
        """
        config_param_model = self.env['ir.config_parameter']
        config_param_key = f'shopify.last_processed_listing_item_id_{self.id}'
        last_listing_item_id = int(config_param_model.get_param(config_param_key, 0))

        self.env.cr.execute("""
            SELECT mli.id
            FROM mk_listing_item mli
            JOIN mk_listing ml ON ml.id = mli.mk_listing_id
            WHERE ml.mk_instance_id = %s
              AND mli.is_listed = TRUE
              AND mli.mk_id IS NOT NULL
              AND mli.id > %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM mk_listing_item_sales_channels_rel rel
                  WHERE rel.listing_item_id = mli.id
              )
            ORDER BY mli.id ASC
        """, (self.id, last_listing_item_id))

        listing_item_ids = self.env['mk.listing.item'].browse([row[0] for row in self.env.cr.fetchall()])
        self.set_shopify_sales_channels_to_listing_item(listing_item_ids, config_param_key)
        self.need_sync_shopify_sales_channels_item = False
        param_record = config_param_model.search([('key', '=', config_param_key)], limit=1)
        param_record and param_record.unlink()
        return True

    def set_shopify_sales_channels_to_listing_item(self, listing_item_ids, config_param_key):
        """
        Task: T7796 - Populate Sales Channel field for existing Listing Items via GraphQL.
        Fetches resourcePublicationsV2 for each variant in batches of 200 and writes the matching shopify.sales.channels.ts records to listing_item.shopify_sales_channel_ids.
        Args:
            listing_item_ids (recordset): Recordset of mk.listing.item.
            config_param_key (str): The configuration parameter key used to store the last processed listing item ID for batch tracking and resumption.
        Returns:
            bool: True after successfully processing all listing items.
        """
        self.connection_to_shopify()
        sales_channel_obj = self.env['shopify.sales.channels.ts']
        listing_item_batch_size = 200
        for listing_item_batch in tools.split_every(listing_item_batch_size, listing_item_ids):
            variant_dict = {item.mk_id: item for item in listing_item_batch if item.mk_id}
            if not variant_dict:
                continue
            id_filter = " OR ".join([f"id:{mk_id}" for mk_id in variant_dict.keys()])
            variables = {"queryFilter": id_filter}
            try:
                res = self.execute_graphql_query(GET_VARIANT_PUBLICATIONS, variables)
                user_errors = res and res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify listing item Sales Channels: %(errors)s") % {'errors': ", ".join(err_messages)})
            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"⚠️ Failed to fetch Shopify listing item Sales Channels: {e}")

            shopify_variant_list = res and res.get('data', {}) and res.get('data', {}).get('productVariants', {}) and res.get('data', {}).get('productVariants', {}).get('nodes', [])
            for shopify_variant_dict in shopify_variant_list:
                mk_id = extract_numeric_id(shopify_variant_dict.get('id', ''))
                listing_item = variant_dict.get(str(mk_id))
                if not listing_item:
                    continue
                channel_ids = []
                variant_publication = shopify_variant_dict and shopify_variant_dict.get('resourcePublicationsV2', {}) and shopify_variant_dict.get('resourcePublicationsV2', {}).get('nodes', [])
                for node in variant_publication:
                    sales_channel_id = str(extract_numeric_id(node.get('publication', {}).get('id', '')))
                    if not sales_channel_id:
                        continue
                    channel = sales_channel_obj.search([('sales_channel_id', '=', sales_channel_id), ('mk_instance_id', '=', self.id)], limit=1)
                    if channel:
                        channel_ids.append(channel.id)
                if channel_ids:
                    listing_item.write({'shopify_sales_channel_ids': [(6, 0, channel_ids)]})

            self.env['ir.config_parameter'].set_param(config_param_key, listing_item_batch[-1].id)
            self.env.cr.commit()
        return True

    def set_shopify_sales_channels_type_category_to_listing(self, listing_ids, config_param_key):
        """
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Updates Shopify listings with their corresponding sales channels based on product publication data from Shopify.
        Args:
            listing_ids (recordset): Recordset of mk.listing.
            config_param_key (str): The configuration parameter key used to store the last processed listing ID for batch tracking and resumption.
        Returns:
            bool: True after successfully assigning sales channels and publication statuses to all listings in the provided batch.
        """
        self.connection_to_shopify()
        listing_batch_size = 250
        for listing_batch in tools.split_every(listing_batch_size, listing_ids):
            # Dictionary: {mk_id: listing_record}
            product_dict = {prd.mk_id: prd for prd in listing_batch}
            # Query filter string: id:8002183757877 OR id:9840218375787
            id_filter = " OR ".join([f"id:{id}" for id in product_dict.keys()])
            variables = {
                "queryFilter": id_filter
            }
            try:
                res = self.execute_graphql_query(GET_PRODUCT_PUBLICATIONS, variables)
                user_errors = res.get('errors', []) if isinstance(res, dict) else {}
                if user_errors and isinstance(user_errors, list):
                    err_messages = [e.get('message', str(e)) for e in user_errors]
                    joined_errors = ", ".join(err_messages)
                    raise MarketplaceException(_("⚠️ Failed to fetch Shopify Product Sales Channels: %(errors)s") % {'errors': joined_errors})
            except MarketplaceException:
                raise
            except Exception as e:
                raise MarketplaceException(f"⚠️ Failed to fetch Shopify Product Sales Channels: {e}")

            shopify_product_data = res and res.get('data', {}).get('products', {}) if isinstance(res, dict) else {}
            shopify_product_list = shopify_product_data and shopify_product_data.get('nodes', [])
            for shopify_product_dict in shopify_product_list:
                mk_id = extract_numeric_id(shopify_product_dict.get('id', ''))
                listing = product_dict.get(str(mk_id))
                if not listing:
                    continue
                vals = {}
                # Set sales channels only when the product has publication data
                resource_publications = shopify_product_dict.get('resourcePublications', {})
                if resource_publications and resource_publications.get('nodes', []):
                    shopify_publications, shopify_sales_channel_ids_list = listing.get_shopify_sales_channels(resource_publications)
                    shopify_publications and vals.update(shopify_publications)
                    is_published = listing.shopify_check_is_listing_published(shopify_sales_channel_ids_list)
                    vals.update({'is_published': is_published})
                # Task: T8254 -  set product type & category during sales-channel migration.
                shopify_product_type = listing.get_shopify_product_type(shopify_product_dict.get('productType'))
                if shopify_product_type:
                    vals['shopify_product_type_id'] = shopify_product_type.id
                shopify_product_category = listing.get_shopify_product_category(shopify_product_dict.get('category'))
                if shopify_product_category:
                    vals['shopify_product_category_id'] = shopify_product_category.id
                listing.write(vals)
            self.env['ir.config_parameter'].set_param(config_param_key, listing_batch[-1].id)
            self.env.cr.commit()

    def _get_shopify_webhook_url(self):
        odoo_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        instance_url = f"{self.env.cr.dbname}/{self.id}"
        # webhook_uuid is a manager-restricted field; read via sudo so URL builds regardless of user.
        webhook_uuid = self.sudo().webhook_uuid
        instance_url = webhook_uuid and f"{instance_url}/{webhook_uuid}" or instance_url
        return odoo_url + '/shopify/webhook/notification/' + instance_url

    def _get_shopify_redirect_url(self):
        odoo_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return odoo_url + '/external/oauth/callback'

    def _validate_shopify_shop_url(self, shop_url):
        """Validate and normalize a Shopify shop URL.

        Returns:
            tuple: (error_message_or_None, normalized_url)
        """
        shop_url = (shop_url or '').strip()
        if not shop_url:
            return None, shop_url
        if shop_url.endswith('/'):
            shop_url = shop_url[:-1]
        if not urlparse(shop_url).scheme:
            return _("URL must include http or https!"), shop_url
        if urlparse(shop_url).hostname and urlparse(shop_url).hostname.startswith('www.'):
            return _("URL must not contain www!"), shop_url
        if not shop_url.endswith('.myshopify.com'):
            return _("URL Must end with the: myshopify.com"), shop_url
        return None, shop_url

    @api.model_create_multi
    def create(self, vals_list):
        """
        T6294 - Added logic to create the Customer resource while creating a new instance.
        T6293 - Added logic to create the Order resource while creating a new instance.
        T6290 - creates metafield resource when a Shopify instance is created.
        """
        for instance in vals_list:
            if instance.get('marketplace', '') == 'shopify':
                # Draft onboarding creates the row with only marketplace; URL is filled in the wizard.
                error, normalized_url = self._validate_shopify_shop_url(instance.get('shop_url'))
                if error:
                    raise MarketplaceException(error)
                if normalized_url:
                    instance['shop_url'] = normalized_url
        res = super(MkInstance, self).create(vals_list)
        for instance_id in res:
            if instance_id.marketplace == 'shopify':
                instance_id.onchange_shopify_product_id()
                instance_id.webhook_uuid = str(uuid4())
                instance_id.webhook_url = instance_id._get_shopify_webhook_url()
                instance_id.shopify_set_default_pos_customer()
                instance_id.redirect_url = instance_id._get_shopify_redirect_url()

                self.env['shopify.metafield.resource.ts'].create({
                    'mk_instance_id': instance_id.id,
                    'name': 'Product Metafields',
                    'resource_name': 'product',
                    'shopify_owner_type': 'PRODUCT',
                    'dashboard_icon': 'fa fa-cube',  # The Icon
                    'odoo_model_id': self.env['ir.model'].sudo().search(
                        [('model', '=', 'product.template')], limit=1
                    ).id
                })

                # Create Variant Card
                self.env['shopify.metafield.resource.ts'].create({
                    'mk_instance_id': instance_id.id,
                    'name': 'Variant Metafields',
                    'resource_name': 'product_variant',
                    'shopify_owner_type': 'PRODUCTVARIANT',
                    'dashboard_icon': 'fa fa-tags',
                    'odoo_model_id': self.env['ir.model'].sudo().search(
                        [('model', '=', 'product.product')], limit=1
                    ).id
                })

                # Create Order Card
                self.env['shopify.metafield.resource.ts'].create({
                    'mk_instance_id': instance_id.id,
                    'name': 'Order Metafields',
                    'resource_name': 'order',
                    'shopify_owner_type': 'ORDER',
                    'dashboard_icon': 'fa fa-shopping-cart',
                    'odoo_model_id': self.env['ir.model'].sudo().search(
                        [('model', '=', 'sale.order')], limit=1
                    ).id
                })

                # Create Customer Card
                self.env['shopify.metafield.resource.ts'].create({
                    'mk_instance_id': instance_id.id,
                    'name': 'Customer Metafields',
                    'resource_name': 'customer',
                    'shopify_owner_type': 'CUSTOMER',
                    'dashboard_icon': 'fa fa-users',
                    'odoo_model_id': self.env['ir.model'].sudo().search(
                        [('model', '=', 'res.partner')], limit=1
                    ).id
                })

        return res

    def write(self, vals):
        # Task: T7715 - Allow Auto Process Payout only for Enterprise users.
        # Task: T8238 - Fix the error where an unsupported auto process payout error pop up occurs in the Enterprise version.
        if vals.get('is_payout_auto_process'):

            # Check if running Odoo is Enterprise
            is_enterprise_edition = '+e' in odoo.release.version

            # Check if account_accountant module exists on addons path
            is_accountant_available = 'account_accountant' in get_modules()

            # Check if account_accountant is installed in database
            is_accountant_installed = self._is_module_installed('account_accountant')

            # Community or Enterprise code not available
            if not is_enterprise_edition or not is_accountant_available:
                raise MarketplaceException(
                    _("⚠️ Auto Process Payout Report is not supported in Community.")
                )

            # Enterprise available but module is not installed
            if not is_accountant_installed:
                raise MarketplaceException(
                    _("⚠️ Please install the Account Accountant module to use Auto Process Payout.")
                )
        for rec in self:
            if vals.get('marketplace') == 'shopify' or rec.marketplace == 'shopify':
                webhook_url = rec._get_shopify_webhook_url()
                redirect_url = rec._get_shopify_redirect_url()
                vals.update({'webhook_url': webhook_url,
                             'redirect_url': redirect_url})
                if 'shop_url' in vals:
                    error, normalized_url = rec._validate_shopify_shop_url(vals.get('shop_url'))
                    if error:
                        raise MarketplaceException(error)
                    vals['shop_url'] = normalized_url
        res = super(MkInstance, self).write(vals)
        for rec in self:
            if rec.marketplace == 'shopify':
                rec.shopify_set_default_pos_customer()
                rec.onchange_shopify_product_id()
        return res

    @api.onchange('gift_card_product_id', 'tip_product_id', 'duties_product_id', 'custom_product_id', 'custom_storable_product_id', 'marketplace')
    def onchange_shopify_product_id(self):
        if not self.gift_card_product_id and self.marketplace == 'shopify':
            self.gift_card_product_id = self.env.ref('shopify.shopify_gift_card_product', False) or False
        if not self.tip_product_id and self.marketplace == 'shopify':
            self.tip_product_id = self.env.ref('shopify.shopify_tip_product', False) or False
        if not self.duties_product_id and self.marketplace == 'shopify':
            self.duties_product_id = self.env.ref('shopify.shopify_duties_product', False) or False
        if not self.custom_product_id and self.marketplace == 'shopify':
            self.custom_product_id = self.env.ref('shopify.shopify_custom_line_product', raise_if_not_found=False) or False
        if not self.custom_storable_product_id and self.marketplace == 'shopify':
            self.custom_storable_product_id = self.env.ref('shopify.shopify_custom_storable_line_product', raise_if_not_found=False) or False

    @api.onchange("is_token", "marketplace")
    def _onchange_redirect_url(self):
        """
        Task: T7473 - onchange the redirect URL for the instance.
        This method Automatically sets the redirect URL for Shopify instances when a valid token is available; otherwise, it clears the URL.
        """
        if self.marketplace == 'shopify':
            self.redirect_url = self._get_shopify_redirect_url()
        else:
            self.redirect_url = False

    def shopify_set_default_pos_customer(self):
        if not self.default_pos_customer_id:
            partner_obj = self.env['res.partner'].sudo()
            pos_customer_id = partner_obj.search(
                ['|', ('company_id', '=', False), ('company_id', '=', self.company_id.id), ('name', '=', 'POS Customer ({})'.format(self.name)), ('customer_rank', '>', 0)])
            if not pos_customer_id:
                partner_vals = {'name': 'POS Customer ({})'.format(self.name), 'customer_rank': 1}
                pos_customer_id = partner_obj.create(partner_vals)
            self.default_pos_customer_id = pos_customer_id.id
        return True

    def shopify_mk_kanban_badge_color(self):
        return "#64943E"

    def shopify_mk_kanban_image(self):
        return file_path('shopify/static/description/shopify_logo.png')

    @check_go_live()
    def connection_to_shopify(self):
        # Credential fields are restricted to Marketplace managers (field-level groups). Read them
        # via sudo so scheduled/sync jobs running under a non-manager user can still open the session.
        instance_sudo = self.sudo()
        session = shopify.Session(instance_sudo.shop_url, '2026-07', instance_sudo.api_token if instance_sudo.is_token else instance_sudo.password)
        shopify.ShopifyResource.activate_session(session)
        return True

    def handle_shopify_access_errors(self, user_errors, name):
        """
        Task: T6711 - Handles errors related to access rights during Shopify data fetching.
        Args:
            user_errors: A list of error objects or dictionaries containing error messages.
            name (str): The name of the Shopify resource (e.g., product, order) being fetched.
        Raises:
            MarketplaceException: If errors occur while fetching the Shopify data, an exception is raised with a detailed error message.
        """
        err_messages = [e.get('message', str(e)) for e in user_errors]
        joined_errors = ", ".join(err_messages)
        raise MarketplaceException(_("⚠️ %(name)s: %(errors)s") % {'name': name, 'errors': joined_errors})

    @check_go_live()
    def execute_graphql_query(self, query, variables=None):
        """
        Execute a Shopify GraphQL query with smart throttling:
          - Retries on HTTP 429
          - Pauses when remaining budget < SAFE_THRESHOLD
        Returns the parsed JSON response on success (which may still carry non-throttle
        GraphQL ``errors`` for the caller to handle).

        Raises MarketplaceException when the request cannot be completed after RETRIES
        attempts (rate limit / transport failure). It never returns None, so that a
        throttled or failed page can never be mistaken for "no more data" and silently
        advance a sync watermark on partial results.
        """
        client = shopify.GraphQL()
        last_error = None

        for attempt in range(1, RETRIES + 1):
            # 1) Fire the request. The vendored client raises urllib HTTPError on non-2xx.
            try:
                raw_response = client.execute(query, variables=variables)
            except Exception as e:
                status = getattr(e, 'code', None)
                last_error = e
                # Non-retryable HTTP errors (auth/permission/bad request) -> fail fast.
                if status is not None and status not in RETRYABLE_HTTP_STATUS:
                    raise MarketplaceException(_("Shopify API HTTP error %(code)s: %(err)s") % {'code': status, 'err': e})
                wait = min(2 ** attempt, 30)
                _logger.warning("Shopify GraphQL request failed (attempt %s/%s, status=%s): %s. Retrying in %ss.", attempt, RETRIES, status, e, wait)
                time.sleep(wait)
                continue

            data = process_response(raw_response)

            # 2) GraphQL-level throttling (HTTP 200 with THROTTLED) -> back off and retry.
            errors = data.get('errors') if isinstance(data, dict) else None
            if errors and any(isinstance(err, dict) and (err.get('extensions', {}) or {}).get('code') == 'THROTTLED' for err in errors):
                last_error = errors
                wait = min(2 ** attempt, 30)
                _logger.warning("Shopify GraphQL THROTTLED (attempt %s/%s). Retrying in %ss.", attempt, RETRIES, wait)
                time.sleep(wait)
                continue

            # 3) Success: pace against the remaining cost budget before returning.
            throttle = (data.get('extensions', {}) or {}).get('cost', {}).get('throttleStatus', {}) if isinstance(data, dict) else {}
            available = throttle.get('currentlyAvailable')
            restore = throttle.get('restoreRate')
            if available is not None and restore:
                if available < SAFE_THRESHOLD:
                    secs = max((SAFE_THRESHOLD - available) / restore, 2)
                    _logger.info("Low Shopify budget (%s pts). Pacing %.1fs.", available, secs)
                    time.sleep(secs)

            op_type = "mutation" if "mutation" in query.lower() else "query"
            match = re.search(r'\b(query|mutation)\s+(\w+)', query)
            operation_name = match.group(2) if match else '[unknown]'
            _logger.info("✅  Executed %s : %s successfully.", op_type.upper(), operation_name)
            return data

        # 4) All attempts exhausted -> raise so callers abort (never advance the watermark on partial data).
        raise MarketplaceException(_("Shopify API request failed after %(n)s attempts (rate limit or transport error). Last error: %(err)s") % {'n': RETRIES, 'err': last_error})

    def shopify_required_access_scopes(self):
        """
        Task: T4565 - Marketplace Access Rights Check
        This method returns set of predefined required access scopes for shopify.
        Returns:
            set: Return set of predefined required access scopes for shopify.
        """
        required_scopes = {
            'write_assigned_fulfillment_orders',
            'write_customers',
            'write_discounts',
            'write_fulfillments',
            'write_gift_cards',
            'write_inventory',
            'write_locations',
            'write_merchant_managed_fulfillment_orders',
            'write_metaobject_definitions',
            'write_metaobjects',
            'write_orders',
            'write_price_rules',
            'write_product_listings',
            'write_products',
            'write_publications',
            'write_returns',
            'write_shipping',
            'read_shopify_payments_payouts',
            'read_shopify_payments_accounts',
            'write_third_party_fulfillment_orders',
            'write_custom_fulfillment_services',
            'write_markets',
        }
        return set(required_scopes)

    def shopify_granted_access_scopes(self):
        """
        Task: T4565 - Marketplace Access Rights Check
        This method retrieves the granted scopes from the shopify app and returns them.
        Returns:
            set: Return set of granted scopes.
        Raises:
            Exception: Raise user error if exception occurs.
        """
        self.connection_to_shopify()
        try:
            # call an access scope api to get the scopes from the shopify app.it returns collection e.g. [access_scope(None), access_scope(None), access_scope(None), access_scope(None), access_scope(None), access_scope(None), acces...(None)]
            res = self.execute_graphql_query(SHOPIFY_ACCESS_SCOPES)
            access_scope_list = res and res.get('data') and res.get('data', {}).get('appInstallation', {}).get('accessScopes', [])

            # prepare a list to store granted scope that get from shopify app.
            granted_scopes = []

            # Iterate over each access scopes.
            for scope in access_scope_list:
                granted_scopes.append(scope.get('handle', ''))
            return set(granted_scopes)
        except Exception as e:
            raise MarketplaceException(f"Something went wrong while retrieves the granted scopes from the shopify: Error {e}")

    def shopify_confirm_connection(self):
        """
        Task: T4565 - Marketplace Access Rights Check
        This method establishes a connection to the shopify, sets the pricelist, and imports location from shopify.
        Raises:
            Exception: Raise an access error if exception occurs.
        """
        if self.is_token and not self.api_token:
            raise MarketplaceException(_('Please generate Access Token by clicking Generate Access Token.'))

        self.connection_to_shopify()
        try:
            shop_currency = self.execute_graphql_query(STORE_CURRENCY)
            db_name = self.env.cr.dbname
            self.set_pricelist(shop_currency.get('data', {}).get('shop', {}).get('currencyCode', ''))
            self.env['shopify.location.ts'].import_location_from_shopify(self)
            self.env['shopify.sales.channels.ts'].import_shopify_sales_channels(self)
            self._sync_shopify_return_reasons()
            self.write({'state': 'confirmed'})
            order_thread = threading.Thread(target=self.env['shopify.product.category.ts'].import_category_from_shopify, args=(db_name,))
            order_thread.start()
        except Exception as e:
            raise MarketplaceException(e)

    def shopify_action_confirm(self):
        """
        Task: T4565 - Marketplace Access Rights Check
        This method get requested and granted access scopes.if any missing scope present, then opens the permission wizard otherwise establishes a connection to the shopify.
        :required_access_scopes is set of predefined access scope e.g. { 'write_customers','write_discounts',...}
        :granted_access_scopes is set of granted scope in shopify app e.g. {'write_customers',...}
        :missing_scope it shows set of missing scopes e.g. {'write_discounts'}
        Returns:
            action (dictionary): Return the access scope permission wizard, if find any missing scope.
        Raises:
            Exception: Raise an access error if exception occurs.
        """
        instance_sudo = self.sudo()
        if instance_sudo.is_token and not instance_sudo.api_token:
            raise MarketplaceException(_('Please generate Access Token by clicking Generate Access Token.'))

        try:
            required_access_scopes = instance_sudo.shopify_required_access_scopes()
            granted_access_scopes = instance_sudo.shopify_granted_access_scopes()
            missing_scope = required_access_scopes - granted_access_scopes
            # If any missing scope present, then opens the permission wizard otherwise establishes a connection to the shopify.
            if missing_scope:
                action = self.env.ref('base_marketplace.action_marketplace_scope_wizard').sudo().read()[0]
                action['context'] = {'mk_instance_id': instance_sudo.id, 'default_mk_instance_name': instance_sudo.marketplace}
                return action
            else:
                instance_sudo.confirm_connection()
        except MarketplaceException:
            raise
        except Exception as e:
            raise MarketplaceException(e)

    def shopify_test_connection(self):
        """
        Task: T4565 - Marketplace Access Rights Check
        If connection established to the shopify then show rainbow man effect.
        Returns:
            effect (dictionary): Returns rainbow man effect if successfully connected to shopify.
        Raises:
            Exception: Returns False if exception occurs.
        """
        instance_sudo = self.sudo()
        if instance_sudo.is_token and not instance_sudo.api_token:
            raise MarketplaceException(_('Please generate Access Token by clicking Generate Access Token.'))

        instance_sudo.connection_to_shopify()
        try:
            shopify.Shop.current()
            return {
                'effect': {
                    'fadeout': 'slow',
                    'message': _("Successfully Connected."),
                    'type': 'rainbow_man',
                }
            }
        except Exception:
            return False

    def _sync_shopify_return_reasons(self):
        """Fetch and update return reasons from Shopify."""
        try:
            self.env['shopify.return.reason.ts'].sudo().import_return_reasons_from_shopify(self)
        except Exception as e:
            _logger.warning("Could not sync Shopify return reasons for %s: %s", self.name, e)

    def shopify_hide_instance_field(self):
        return ['fbm_order_prefix', 'api_limit', 'environment']

    def reset_to_draft(self):
        res = super(MkInstance, self).reset_to_draft()

        if self.marketplace == 'shopify':
            self.connection_to_shopify()
            for webhook in self.webhook_ids.filtered(lambda x: x.active_webhook):
                webhook.shopify_delete_webhook()
        return res

    def shopify_marketplace_operation_wizard(self):
        """
        Task: T5836 - Migrate Shopify to v19
        Modified method to set default value for is_publish_or_unpublish boolean field in operation wizard.
        """
        action = self.env.ref('base_marketplace.action_marketplace_operation').sudo().read()[0]
        action['views'] = [(self.env.ref('shopify.shopify_mk_operation_form_view').sudo().id, 'form')]
        # is_publish_or_unpublish (pass default true in case of export)
        ctx = self.env.context.copy()
        ctx['default_is_publish_or_unpublish'] = True
        ctx['default_mk_instance_id'] = self.id
        action['context'] = ctx
        return action

    def fetch_shopify_webhook(self):
        self.env['shopify.webhook.ts'].fetch_all_webhook_from_shopify(self)
        return True

    def delete_shopify_webhook(self):
        """
        Task: T6079 - Migrate the Rest_api to Graphql
                Deleting the webhook subscription from Shopify, and also false active_webhook and set null for the wehbook_id.
        """
        if self.webhook_ids.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("You can Delete a all webhook only with a confirmed instance. Please ensure the Instance is confirmed Before Deleting a all Webhook."))
        self.connection_to_shopify()
        variables = {
            "count": 250
        }
        webhooks = self.webhook_ids.mk_instance_id.execute_graphql_query(GRAPHQL_QUERY_FIND_WEBHOOKS, variables)
        webhooks_response_dict = webhooks and webhooks.get('data', {}).get('webhookSubscriptions', {})
        odoo_url = self.get_base_url()
        odoo_url = urlparse(odoo_url).hostname
        for webhook in webhooks_response_dict:
            webhook_uri = webhook.get('uri', {})
            address = urlparse(webhook_uri).hostname
            if odoo_url == address:
                variables = {"id": webhook.get('id', {})}
                extract_wehbook_id = extract_numeric_id(webhook.get('id', ''))
                self.webhook_ids.mk_instance_id.execute_graphql_query(DELETE_SHOPIFY_SUBSCRIPTION, variables)
                webhook_context = self.env['shopify.webhook.ts'].search([('webhook_id', '=', extract_wehbook_id)])
                webhook_context.with_context(skip_write=True).write({'active_webhook': False, 'webhook_id': ''})

        return True

    def get_shopify_cron_list(self, mk_instance_id):
        """
        Generate the default list of scheduled actions (crons) for Shopify.
        Args:
            mk_instance_id: The Shopify marketplace instance object
        Returns:
            list: A list of dictionaries defining crons for Shopify
        """
        cron_list = [
            {'cron_name': "Shopify [%s] : Import Order" % mk_instance_id.name, 'method_name': 'cron_auto_import_shopify_orders', 'model_name': 'sale.order', 'interval_type': 'minutes',
             'interval_number': 15},
            {'cron_name': "Shopify [%s] : Export Order Status/Tracking Information" % mk_instance_id.name, 'method_name': 'cron_auto_update_order_status', 'model_name': 'sale.order',
             'interval_type': 'minutes', 'interval_number': 25},
            {'cron_name': "Shopify [%s] : Export Product's Inventory" % mk_instance_id.name, 'method_name': 'cron_auto_export_stock', 'model_name': 'mk.listing',
             'interval_type': 'minutes', 'interval_number': 30},
            {'cron_name': "Shopify [%s] : Import Product's Inventory" % mk_instance_id.name, 'method_name': 'cron_auto_import_stock', 'model_name': 'mk.listing',
             'interval_type': 'days', 'interval_number': 1},
            {'cron_name': "Shopify [%s] : Export Product's Price" % mk_instance_id.name, 'method_name': 'cron_auto_update_product_price', 'model_name': 'mk.listing',
             'interval_type': 'days', 'interval_number': 1},
            {'cron_name': "Shopify [%s] : Import Payout Reports" % mk_instance_id.name, 'method_name': 'cron_auto_import_shopify_payout_report', 'model_name': 'shopify.payout',
             'interval_type': 'days', 'interval_number': 1},
            {'cron_name': 'Shopify [{}] : Import Returns'.format(mk_instance_id.name), 'method_name': 'cron_auto_import_shopify_returns', 'model_name': 'shopify.return.ts',
             'interval_type': 'minutes', 'interval_number': 30},
            {'cron_name': 'Shopify [{}] : Process Pending Cancelled Returns'.format(mk_instance_id.name), 'method_name': 'cron_process_pending_cancelled_shopify_returns',
             'model_name': 'shopify.return.ts', 'interval_type': 'minutes', 'interval_number': 25},
            {'cron_name': 'Shopify [{}] : Process Bulk Queue Status'.format(mk_instance_id.name), 'method_name': 'process_shopify_bulk_query_status_cron', 'model_name': 'shopify.bulk.query',
             'interval_type': 'minutes', 'interval_number': 15},
            {'cron_name': 'Shopify [{}] : Process Bulk Export/Update Result'.format(mk_instance_id.name), 'method_name': 'process_shopify_bulk_export_results_cron',
             'model_name': 'shopify.bulk.query', 'interval_type': 'minutes', 'interval_number': 15}
        ]
        return cron_list

    def shopify_setup_schedule_actions(self, mk_instance_id):
        cron_obj = self.env['ir.cron'].sudo()
        shopify_cron_ids = cron_obj.search([('mk_instance_id', '=', self.id), '|', ('active', '=', True), ('active', '=', False)])

        # Get the list of crons
        cron_list = self.get_shopify_cron_list(mk_instance_id)

        for cron_dict in cron_list:
            shopify_cron_ids -= cron_obj.create_marketplace_cron(mk_instance_id,
                cron_dict['cron_name'], method_name=cron_dict['method_name'], model_name=cron_dict['model_name'], interval_type=cron_dict['interval_type'], interval_number=cron_dict['interval_number'])
        if shopify_cron_ids:
            shopify_cron_ids.unlink()
        return True

    def action_shopify_rotate_webhook_uuid(self):
        """
        Task :T6079 - When webhook url was a changed then  delete the webhook event which is a true and crete new with the new url.
        """
        if self.state != 'confirmed':
            raise MarketplaceException(_("You can Rotate Secret only with a confirmed instance. Please ensure the Instance is confirmed Before Rotating Secret a Webhook."))
        for mk_instance_id in self:
            mk_instance_id.webhook_uuid = str(uuid4())
            mk_instance_id.webhook_url = mk_instance_id._get_shopify_webhook_url()
            active_webhook_ids = self.webhook_ids.filtered(lambda x: x.active_webhook)
            for webhook_id in active_webhook_ids:
                webhook_id.shopify_delete_webhook()
                if not webhook_id.active_webhook:
                    response = webhook_id.create_webhook_in_shopify()
                    if isinstance(response, dict):
                        if response.get('data', {}).get('webhookSubscriptionCreate', {}).get('webhookSubscription', {}).get('id', {}):
                            webhook_id.with_context(skip_create=True).write({'active_webhook': True})

    def _get_oauth_signing_secret(self):
        """
        Task 6480 - Fetches the secret from System Parameters.
        Generates a new one if it doesn't exist.
        """
        param_model = self.env['ir.config_parameter'].sudo()
        secret = param_model.get_param('shopify.oauth_signing_secret')

        if not secret:
            # Generate a new secure secret automatically
            secret = secrets.token_hex(32)
            param_model.set_param('shopify.oauth_signing_secret', secret)

        return secret

    def build_state(self, mk_instance_id):
        """
        Task 6480 - Build a secure OAuth `state` parameter for Shopify authentication.

        Args:
            mk_instance_id: ID of the mk.instance initiating the OAuth flow
        Returns:
            URL-safe Base64 encoded string containing the signed state payload.
        """
        payload = json.dumps({"mk_instance_id": mk_instance_id})
        secret = self._get_oauth_signing_secret()
        sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()

    def action_get_shopify_access_token(self):
        """
        Task 6480 - Initiates the Shopify OAuth authentication process.
        Validates the necessary credentials (Client ID, Secret) and constructs
        the authorization URL required to request an Access Token from Shopify.

        Raises:
            MarketplaceException: If any required field (Client ID, Secret, or Shop URL) is missing.
        Returns:
            A dictionary action that redirects the user to the Shopify OAuth URL.
        """
        self.ensure_one()
        client_id = self.client_id
        redirect_uri = self.redirect_url
        shop_url = self.shop_url

        if not shop_url:
            raise MarketplaceException(_("Please configure the Shop URL first."))
        if not client_id:
            raise MarketplaceException(_("Please enter the Shopify Client ID."))
        if not self.secret_id:
            raise MarketplaceException(_("Please enter the Shopify Secret."))
        if not redirect_uri:
            raise MarketplaceException(_("Please enter the Redirect URL."))

        # Ensure we have the domain for the URL construction
        if not shop_url.startswith('http'):
            shop_url = f"https://{shop_url}"

        parsed = urlparse(shop_url)
        shop_domain = parsed.netloc

        base_url = f"https://{shop_domain}/admin/oauth/authorize"

        # Added read_all_orders to the scopes
        required_access_scopes = self.shopify_required_access_scopes()

        state = self.build_state(self.id)
        params = {
            'client_id': client_id,
            'scope': ",".join(required_access_scopes),
            'redirect_uri': redirect_uri,
            'state': state
        }

        return {
            'type': 'ir.actions.act_url',
            'url': f"{base_url}?{urllib.parse.urlencode(params)}",
            'target': 'new',
        }

    def shopify_get_onboarding_steps(self):
        return [
            {
                'title': _('Connect Your Store'),
                'icon': 'fa-plug',
                'template': 'shopify.MarketplaceOnboarding_shopify_step_1',
                'image': '/shopify/static/description/img/onboarding/shopify_onboarding_step_one.png',
            },
            {
                'title': _('Product Settings'),
                'icon': 'fa-cubes',
                'template': 'shopify.MarketplaceOnboarding_shopify_step_2',
                'image': '/shopify/static/description/img/onboarding/shopify_onboarding_step_two.png',
            },
            {
                'title': _('Order Configuration'),
                'icon': 'fa-shopping-cart',
                'template': 'shopify.MarketplaceOnboarding_shopify_step_3',
                'image': '/shopify/static/description/img/onboarding/shopify_onboarding_step_three.png',
            },
            {
                'title': _('Review & Confirm'),
                'description': _('Review your setup before saving'),
                'icon': 'fa-check-circle',
                'template': 'shopify.MarketplaceOnboarding_shopify_step_4',
                'image': '/shopify/static/description/img/onboarding/shopify_onboarding_step_four.png',
            },
        ]

    def _shopify_import_order_after_for_onboarding_input(self):
        """Format stored UTC datetime for HTML ``datetime-local`` in the user timezone."""
        if not self.import_order_after_date:
            return ''
        dt = fields.Datetime.context_timestamp(self, self.import_order_after_date)
        return dt.strftime('%Y-%m-%dT%H:%M')

    def _shopify_parse_onboarding_import_order_after(self, raw):
        if not raw:
            return False
        s = str(raw).strip().replace('T', ' ')
        if len(s) == 16:
            s += ':00'
        try:
            return fields.Datetime.to_datetime(s)
        except Exception:
            return False

    def shopify_get_onboarding_values(self):
        sync_pairs = self._fields['sync_product_with']._description_selection(self.env)
        tax_pairs = self._fields['tax_system']._description_selection(self.env)
        sync_sel = dict(sync_pairs)
        tax_sel = dict(tax_pairs)
        fulfillment_records = self.env['shopify.order.status'].sudo().search_read([], ['id', 'name'], order='name')
        tax_account_options = self.get_onboarding_tax_account_options()
        # Default to "Any" fulfillment status for new instances
        any_status_id = self.env.ref('shopify.shopify_order_status_any', raise_if_not_found=False)
        default_fulfillment_ids = [any_status_id.id] if any_status_id and not self.fulfillment_status_ids else self.fulfillment_status_ids.ids
        return {
            'name': self.name or '',
            'import_order_after_date': self._shopify_import_order_after_for_onboarding_input(),
            'shop_url': self.shop_url or '',
            'api_token': self.api_token or '',
            'password': self.password or '',
            'is_token': self.is_token if self.is_token else True,  # Default to True for onboarding
            'sync_product_with': self.sync_product_with or 'barcode_or_sku',
            'sync_product_with_label': sync_sel.get(self.sync_product_with, ''),
            'is_create_products': self.is_create_products,
            'tax_system': self.tax_system or 'according_to_marketplace',
            'tax_system_label': tax_sel.get(self.tax_system, ''),
            'tax_system_options': [{'value': k, 'label': v} for k, v in tax_pairs],
            'sync_product_with_options': [{'value': k, 'label': v} for k, v in sync_pairs],
            'tax_account_id': self.tax_account_id.id if self.tax_account_id else False,
            'tax_refund_account_id': self.tax_refund_account_id.id if self.tax_refund_account_id else False,
            'tax_account_options': tax_account_options,
            'fulfillment_status_ids': default_fulfillment_ids,
            'fulfillment_status_options': [{'id': r['id'], 'name': r['name']} for r in fulfillment_records],
        }

    def shopify_validate_onboarding_step_1(self, data):
        name = (data.get('name') or '').strip()
        if not name:
            return {'valid': False, 'error': _('Instance name is required.')}
        shop_url = (data.get('shop_url') or '').strip()
        if not shop_url:
            return {'valid': False, 'error': _('Shop URL is required.')}
        url_error, _normalized_url = self._validate_shopify_shop_url(shop_url)
        if url_error:
            return {'valid': False, 'error': url_error}
        is_token = data.get('is_token', True)
        if is_token:
            if not (data.get('api_token') or '').strip():
                return {'valid': False, 'error': _('API access token is required.')}
        else:
            if not (data.get('password') or '').strip():
                return {'valid': False, 'error': _('Password is required when not using an API access token.')}
        return {'valid': True}

    def shopify_validate_onboarding_step_2(self, data):
        sync_product_with = data.get('sync_product_with')
        valid_keys = dict(self._fields['sync_product_with']._description_selection(self.env))
        if sync_product_with not in valid_keys:
            return {'valid': False, 'error': _('Please select a valid product sync method.')}
        return {'valid': True}

    def shopify_validate_onboarding_step_3(self, data):
        tax_system = data.get('tax_system')
        valid_tax = dict(self._fields['tax_system']._description_selection(self.env))
        if tax_system not in valid_tax:
            return {'valid': False, 'error': _('Please select a valid tax configuration.')}
        if tax_system != 'default':
            tax_acc = data.get('tax_account_id')
            tax_ref = data.get('tax_refund_account_id')
            if not tax_acc or not tax_ref:
                return {
                    'valid': False,
                    'error': _('Please select Tax Account and Tax Account on Credit Notes for this tax configuration.'),
                }
            company = self.company_id or self.env.company
            Account = self.env['account.account'].with_company(company).sudo()
            domain = self._mk_onboarding_tax_account_domain(company)
            if (
                Account.search_count(domain + [('id', '=', int(tax_acc))]) != 1
                or Account.search_count(domain + [('id', '=', int(tax_ref))]) != 1
            ):
                return {'valid': False, 'error': _('One or more selected tax accounts are not valid for this company.')}
        status_ids = data.get('fulfillment_status_ids') or []
        if isinstance(status_ids, list) and not status_ids:
            return {
                'valid': False,
                'error': _('Please select Fulfillment statuses.'),
            }
        elif not isinstance(status_ids, list):
            return {'valid': False, 'error': _('Invalid fulfillment status selection.')}
        if status_ids:
            existing = self.env['shopify.order.status'].sudo().search_count([('id', 'in', status_ids)])
            if existing != len(set(status_ids)):
                return {'valid': False, 'error': _('One or more fulfillment statuses are invalid.')}
        return {'valid': True}

    def _shopify_apply_onboarding_vals(self, values):
        """Write the Shopify onboarding form values onto the instance (no scope check / confirm)."""
        values = values or {}
        vals = {}
        if 'name' in values:
            vals['name'] = (values.get('name') or '').strip()
        if 'import_order_after_date' in values:
            vals['import_order_after_date'] = self._shopify_parse_onboarding_import_order_after(
                values.get('import_order_after_date')
            )
        if 'shop_url' in values:
            vals['shop_url'] = (values.get('shop_url') or '').strip()
        if 'is_token' in values:
            vals['is_token'] = bool(values.get('is_token'))
        new_tok = values.get('api_token')
        if new_tok is not None:
            if new_tok:
                vals['api_token'] = new_tok
        new_pw = values.get('password')
        if new_pw is not None:
            if new_pw:
                vals['password'] = new_pw
        if 'sync_product_with' in values:
            vals['sync_product_with'] = values['sync_product_with']
        if 'is_create_products' in values:
            vals['is_create_products'] = bool(values.get('is_create_products'))
        if 'tax_system' in values:
            vals['tax_system'] = values['tax_system']
        ts = vals.get('tax_system', self.tax_system)
        if ts == 'default':
            vals['tax_account_id'] = False
            vals['tax_refund_account_id'] = False
        else:
            if 'tax_account_id' in values:
                vals['tax_account_id'] = values['tax_account_id'] or False
            if 'tax_refund_account_id' in values:
                vals['tax_refund_account_id'] = values['tax_refund_account_id'] or False
        if 'fulfillment_status_ids' in values:
            ids = [int(x) for x in (values.get('fulfillment_status_ids') or [])]
            vals['fulfillment_status_ids'] = [(6, 0, ids)]
        if vals:
            self.write(vals)
        # Same as Confirm on the instance form: connect, check API scopes, then confirm or open scope wizard.
    def shopify_save_onboarding_data(self, values):
        self._shopify_apply_onboarding_vals(values)
        # Onboarding: connect, then check API scopes. If any are missing, return them
        # so the Shopify Summary step shows them inline (instead of opening the popup wizard).
        self.action_test_connection()
        scope_check = self.get_onboarding_scope_check()
        if scope_check.get('missing'):
            return {'scope_check': scope_check}
        self.confirm_connection()
        return {}

    def get_onboarding_scope_check(self):
        """Shopify onboarding: required vs granted API scopes for inline display in the Summary step.

        Returns dict: {'missing': [...], 'granted': [...]} (sorted lists).
        """
        self.ensure_one()
        required = self.shopify_required_access_scopes()
        granted = self.shopify_granted_access_scopes()
        missing = required - granted
        return {
            'missing': sorted(missing),
            'granted': sorted(required - missing),
        }

    def onboarding_ignore_scopes_and_confirm(self, values=None):
        """Shopify onboarding: save the latest form values, ignore the missing scopes,
        and establish the connection (confirm the instance)."""
        self.ensure_one()
        self._shopify_apply_onboarding_vals(values)
        self.confirm_connection()
        return {'success': True}

    def import_specific_type_metafield_from_shopify(self, target_odoo_record, shopify_owner_type, metafields_list, reference_handler_func=None, mk_log_line_dict=None, wipe_unmatched=True,
                                                    queue_line_id=False, mk_log_id=False, mk_id=False):
        """
        T6293 - Made log labels and owner labels dynamic to support all resources.
        T6290 - This method imports Shopify metafield values into the given Odoo record based on configured mappings. It converts values to Odoo format,
        updates the record, and clears values for metafields that are no longer present in Shopify.
        Args:
            target_odoo_record (recordset): Odoo record (product template or variant) where values will be updated.
            shopify_owner_type (str): Shopify resource type ('PRODUCT' or 'PRODUCTVARIANT').
            metafields_list (list): List of metafield dictionaries received from Shopify.
            reference_handler_func (function, optional): Function to handle reference-type metafields.
            mk_log_line_dict (dict, optional): Dictionary used to collect error and success log messages.
            wipe_unmatched (bool): Wipe value of empty fields in odoo (only when fetch was complete — partial fetch would corrupt data).
            queue_line_id (Recordset): Recordset of mk.queue.line.
            mk_log_id (Recordset): Recordset of mk.log.
            mk_id (str): Marketplace id of listing or listing item.
        Returns:
            bool: Returns True after processing all metafields.
        Raises:
            Exception: Errors are handled internally and logged (if log dict is provided).
        """
        if metafields_list is None:
            return True
        target_odoo_record = target_odoo_record.sudo().with_company(self.company_id or self.env.company)

        if mk_log_line_dict is None:
            mk_log_line_dict = {'error': [], 'success': []}

        mappings = self.env['shopify.metafield.mapping.ts'].sudo().search([
            ('mk_instance_id', '=', self.id),
            ('resource_id.shopify_owner_type', '=', shopify_owner_type),
            ('active_mapping', '=', True),
            ('mapping_status', '=', 'ready'),
            ('odoo_field_id', '!=', False)
        ])

        if not mappings:
            return True

        mapping_dict = {m.namespace_and_key: m for m in mappings}
        received_keys = set()
        update_vals = {}
        owner_label = SHOPIFY_OWNER_LABELS.get(shopify_owner_type, '')
        log_label = SHOPIFY_LOG_TITLES.get(shopify_owner_type, '')

        if self.env.context.get('force_metaobject_entry_refresh') and self.enable_metaobject:
            refresh_gids, refresh_metafields = [], []
            for metafield in metafields_list:
                namespace_and_key = f"{metafield.get('namespace')}.{metafield.get('key')}"
                mapping = mapping_dict.get(namespace_and_key)
                if not mapping or 'metaobject_reference' not in mapping.types:
                    continue
                value = metafield.get('value')
                if not value:
                    continue
                if mapping.types.startswith('list.'):
                    try:
                        refresh_gids.extend(gid for gid in json.loads(value) if gid)
                    except (json.JSONDecodeError, TypeError):
                        continue
                else:
                    refresh_gids.append(value)
                refresh_metafields.append(f"{mapping.name} ({mapping.metaobject_definition_id.name})")
            if refresh_gids:
                self.env['shopify.metaobject.entry.ts'].sudo().with_context(
                    mk_log_id=mk_log_id, shopify_metafield=', '.join(dict.fromkeys(refresh_metafields))
                ).resolve_shopify_metaobject_gids(refresh_gids, self, mk_log_line_dict=mk_log_line_dict)

        for metafield in metafields_list:
            namespace_and_key = f"{metafield.get('namespace')}.{metafield.get('key')}"
            mapping = mapping_dict.get(namespace_and_key)
            if not mapping:
                continue

            received_keys.add(namespace_and_key)
            metafield_value = metafield.get('value')
            metafield_type = mapping.types

            try:
                if metafield_type == 'link':
                    link_data = json.loads(metafield_value) if isinstance(metafield_value, str) else metafield_value
                    update_vals[mapping.odoo_field_id.name] = link_data.get('url')
                    if mapping.odoo_alt_text_field_id:
                        update_vals[mapping.odoo_alt_text_field_id.name] = link_data.get('text')

                elif metafield_type == 'json':
                    parsed_data = json.loads(metafield_value) if isinstance(metafield_value, str) else metafield_value
                    if parsed_data is None:
                        update_vals[mapping.odoo_field_id.name] = False
                        continue
                    if mapping.odoo_field_id.ttype == 'json':
                        update_vals[mapping.odoo_field_id.name] = parsed_data  # native Python object
                    else:
                        update_vals[mapping.odoo_field_id.name] = json.dumps(  # readable text
                            parsed_data, ensure_ascii=False
                        )

                elif metafield_type in ('weight', 'volume'):
                    measurement_data = json.loads(metafield_value) if isinstance(metafield_value, str) else metafield_value
                    raw_value = measurement_data.get('value', 0.0)
                    shopify_unit = measurement_data.get('unit', '')
                    measurement_vals = self.import_shopify_measurement_metafield(
                        m_type=metafield_type,
                        value=float(raw_value),
                        unit=shopify_unit,
                        mapping=mapping,
                        target_odoo_record=target_odoo_record,
                        mk_id=mk_id,
                        mk_log_line_dict=mk_log_line_dict,
                        queue_line_id=queue_line_id,
                    )
                    update_vals.update(measurement_vals)

                elif metafield_type == 'money':
                    money_data = json.loads(metafield_value) if isinstance(metafield_value, str) else metafield_value
                    update_vals[mapping.odoo_field_id.name] = float(money_data.get('amount'))
                    if mapping.odoo_field_id.ttype == 'monetary':
                        field_def = self.env[target_odoo_record._name]._fields.get(mapping.odoo_field_id.name)
                        # Find the name of the linked currency field (defaults to 'currency_id')
                        if field_def and hasattr(field_def, 'currency_field') and field_def.currency_field:
                            currency_field_name = field_def.currency_field
                            # Set it to the instance's pricelist currency
                            pricelist_currency = self.pricelist_id.currency_id
                            if pricelist_currency:
                                update_vals[currency_field_name] = pricelist_currency.id

                elif metafield_type == 'rating':
                    rating_data = json.loads(metafield_value) if isinstance(metafield_value, str) else metafield_value
                    update_vals[mapping.odoo_field_id.name] = float(rating_data.get('value'))

                elif metafield_type == 'number_integer':
                    update_vals[mapping.odoo_field_id.name] = int(metafield_value) if metafield_value not in (None, '') else 0

                elif metafield_type == 'number_decimal':
                    update_vals[mapping.odoo_field_id.name] = float(metafield_value) if metafield_value not in (None, '') else 0.0

                elif metafield_type == 'date_time':
                    try:
                        formatted_datetime_str = metafield_value.replace('+00:00', 'Z')
                        update_vals[mapping.odoo_field_id.name] = datetime.strptime(formatted_datetime_str, "%Y-%m-%dT%H:%M:%SZ")
                    except Exception as e:
                        log_message = f"IMPORT {log_label}: Failed to import date and time metafield {mapping.name} for {target_odoo_record.display_name} ({mk_id}). Due to an invalid value: {metafield_value}. Error: {e}"
                        mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False})

                elif metafield_type == 'rich_text_field':
                    rich_text_data = json.loads(metafield_value) if isinstance(metafield_value, str) else metafield_value
                    update_vals[mapping.odoo_field_id.name] = _convert_shopify_rich_text_to_html(rich_text_data)

                elif metafield_type == 'boolean':
                    update_vals[mapping.odoo_field_id.name] = str(metafield_value).strip().lower() == 'true'

                elif 'reference' in metafield_type:
                    if reference_handler_func:
                        update_vals[mapping.odoo_field_id.name] = reference_handler_func(
                            metafield_value, mapping, self,
                            mk_log_id=mk_log_id,
                            target_odoo_record=target_odoo_record,
                            mk_log_line_dict=mk_log_line_dict,
                            queue_line_id=queue_line_id,
                            mk_id=mk_id
                        )
                else:
                    update_vals[mapping.odoo_field_id.name] = metafield_value
            except Exception as e:
                # Catch ANY parsing or conversion errors for this specific metafield and log it
                log_message = f"IMPORT {log_label}: Metafield {mapping.name} for {target_odoo_record.display_name} ({mk_id}) could not be converted to Odoo format and was skipped. Error: {e}"
                mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id and queue_line_id.id or False})

        # Remove value of empty fields
        if wipe_unmatched:
            wiped_keys = []
            for namespace_and_key, mapping in mapping_dict.items():
                if namespace_and_key not in received_keys:
                    field_name = mapping.odoo_field_id.name
                    # In odoo if field is empty
                    if not target_odoo_record[field_name]:
                        continue

                    update_vals[field_name] = False
                    if mapping.odoo_unit_field_id:
                        update_vals[mapping.odoo_unit_field_id.name] = False
                    if mapping.odoo_alt_text_field_id:
                        update_vals[mapping.odoo_alt_text_field_id.name] = False
                    wiped_keys.append(mapping.name)
            if wiped_keys and mk_log_line_dict is not None:
                log_message = (
                    f"IMPORT {log_label}: Cleared metafield values in Odoo for {owner_label} "
                    f"{target_odoo_record.display_name} ({mk_id}) because the following metafield(s) values "
                    f"were not available in Shopify: {', '.join(wiped_keys)}"
                )
                mk_log_line_dict['success'].append({
                    'log_message': log_message,
                    'queue_job_line_id': queue_line_id.id if queue_line_id else False,
                })

        if update_vals:
            try:
                with self.env.cr.savepoint():
                    target_odoo_record.write(update_vals)
            except Exception as e:
                record_name = target_odoo_record.display_name

                mk_log_line_dict['error'].append({
                    'log_message': (
                        f"IMPORT {log_label}: Bulk update failed for {owner_label} "
                        f"{record_name}. Falling back to field-level update. "
                        f"Error: {str(e)}"
                    ),
                    'queue_job_line_id': queue_line_id.id if queue_line_id else False
                })

                # Fallback: per-field write
                for field_name, value in update_vals.items():
                    try:
                        with self.env.cr.savepoint():
                            target_odoo_record.write({field_name: value})
                    except Exception as e:
                        record_name = target_odoo_record.display_name
                        mk_log_line_dict['error'].append({
                            'log_message': (
                                f"IMPORT {log_label}: Failed to update odoo field {field_name} "
                                f"for {owner_label} {record_name}. Error: {str(e)}"
                            ),
                            'queue_job_line_id': queue_line_id.id if queue_line_id else False
                        })

    def _prepare_shopify_metafield_value_for_update(self, target_odoo_record, mapping, raw_value, reference_handler_func, mk_log_line_dict, mk_id):
        """
        T6293 - Made log labels and owner labels dynamic to support all resources.
        T6290 - Converts raw Odoo values into the exact format required by Shopify metafield update API.
        Args:
            target_odoo_record (recordset): Recordset from where values will be updated (e.g., product.template or product.product).
            mapping (recordset): Recordset of shopify.metafield.mapping.ts.
            raw_value (any): Value fetched from the Odoo field.
            reference_handler_func (function): Handler function for reference-type metafields.
            mk_log_line_dict (dict): Dictionary to store log messages.
            mk_id (str): Marketplace if of listing or listing item.
        Returns:
            str | None: Formatted value ready for Shopify, or None if conversion fails.
        Raises:
            Exception: Errors are handled internally and logged.
        """
        m_type = mapping.types

        owner_label = SHOPIFY_OWNER_LABELS.get(mapping.resource_id.shopify_owner_type, '')
        log_label = SHOPIFY_LOG_TITLES.get(mapping.resource_id.shopify_owner_type, '')

        try:
            if m_type in ('single_line_text_field', 'multi_line_text_field', 'url', 'color', 'id', 'number_integer', 'number_decimal'):
                return str(raw_value)
            elif m_type == 'boolean':
                return "true" if raw_value else "false"
            elif m_type == 'date':
                if isinstance(raw_value, (datetime, date)): return raw_value.strftime("%Y-%m-%d")
                return str(raw_value)[:10]
            elif m_type == 'date_time':
                if isinstance(raw_value, datetime):
                    return raw_value.strftime("%Y-%m-%dT%H:%M:%S")
                return str(raw_value).replace(" ", "T")[:19]
            elif m_type == 'json':
                return json.dumps(raw_value) if not isinstance(raw_value, str) else raw_value
            elif m_type in ('weight', 'volume'):
                if not mapping.odoo_unit_field_id:
                    log_message = _("UPDATE %s: Skipped updating metafield %s for %s %s (%s) because the unit field is not configured in the metafield configuration") % (
                        log_label, mapping.name, owner_label, target_odoo_record.display_name, mk_id
                    )

                    mk_log_line_dict['error'].append({'log_message': log_message})
                    return False

                odoo_value = getattr(target_odoo_record, mapping.odoo_field_id.name)
                odoo_unit = getattr(target_odoo_record, mapping.odoo_unit_field_id.name)

                if not odoo_unit:
                    log_message = _("UPDATE %s: Skipped updating metafield %s for %s %s (%s) because the unit field value is missing") % (
                        log_label, mapping.name, owner_label, target_odoo_record.display_name, mk_id
                    )
                    mk_log_line_dict['error'].append({'log_message': log_message})
                    return False

                converted_value, shopify_unit = self.update_measurement_metafield_to_shopify(m_type=m_type, value=odoo_value, unit=odoo_unit)
                return json.dumps({"value": converted_value, "unit": shopify_unit or ""})
            elif m_type == 'money':
                currency_code = self.pricelist_id.currency_id.name
                return json.dumps({"amount": str(raw_value), "currency_code": currency_code})
            elif m_type == 'rating':
                return json.dumps({"value": str(raw_value), "scale_min": mapping.scale_min, "scale_max": mapping.scale_max})
            elif m_type == 'link':
                alt_text = getattr(target_odoo_record, mapping.odoo_alt_text_field_id.name) if mapping.odoo_alt_text_field_id else ""
                return json.dumps({"url": str(raw_value), "text": str(alt_text) if alt_text else ""})
            elif m_type == 'rich_text_field':
                return convert_html_to_shopify_rich_text(raw_value)
            elif 'reference' in m_type:
                if reference_handler_func:
                    return reference_handler_func(target_odoo_record, raw_value, mapping, mk_log_line_dict, mk_id)
        except Exception as e:
            log_message = (
                f"UPDATE {log_label}: Exception while preparing update metafield value for {mapping.name} "
                f"for {owner_label} {target_odoo_record.display_name} ({mk_id}). Error: {str(e)}"
            )
            mk_log_line_dict['error'].append({'log_message': log_message})
            return False
        return str(raw_value)

    def import_shopify_measurement_metafield(self, m_type, value, unit, mapping, target_odoo_record=None, mk_id=None, mk_log_line_dict=None, queue_line_id=False):
        """
        T6293 - Made log labels and owner labels dynamic to support all resources.
        T6290 - This method imports measurement metafield values (e.g., weight, volume) from Shopify to Odoo by converting the value to Odoo format and storing
        both the converted value and original unit on the record.
        Args:
            m_type (str): Measurement type.
            value (float): Shopify Measurement field value.
            unit (str): Shopify Measurement field unit.
            mapping (recordset): Recordset of shopify.metafield.mapping.ts.
            mk_log_id (Recordset): Recordset of mk.log.
            mk_id (str): Marketplace id of listing or listing item.
            queue_line_id (Recordset): Recordset of mk.queue.line.
        Returns:
            update_vals (dict): Dictionary contains weight/volumn metafield value.
        """
        if not mapping.odoo_unit_field_id:
            if mk_log_line_dict is not None:
                owner_label = SHOPIFY_OWNER_LABELS.get(mapping.resource_id.shopify_owner_type, '')
                log_label = SHOPIFY_LOG_TITLES.get(mapping.resource_id.shopify_owner_type, '')
                log_message = _("IMPORT %s: Skipped metafield %s on %s %s (%s) unit field is not configured on the metafield configuration") % (
                    log_label, mapping.name, owner_label, target_odoo_record.display_name, mk_id
                )
                mk_log_line_dict['error'].append({'log_message': log_message, 'queue_job_line_id': queue_line_id.id if queue_line_id else False, })
            return {}

        converted = convert_shopify_metafield_measurement(
            env=self.env, m_type=m_type, value=value, shopify_unit=unit, reverse=False
        )
        update_vals = {mapping.odoo_field_id.name: converted}
        update_vals[mapping.odoo_unit_field_id.name] = unit
        return update_vals

    def update_measurement_metafield_to_shopify(self, m_type, value, unit):
        """
        T6290 - This method exports measurement values (e.g., weight, volume) from Odoo to Shopify
        by converting them into Shopify format using the given unit.
        Args:
            m_type (str): Measurement type.
            value (float): Odoo field value.
            unit (str): Unit to use for Shopify.
        Returns:
            tuple: Returns tuple of converted value and unit.
        """
        # Fallback if product was created in Odoo and lacks a twin-field unit
        converted = convert_shopify_metafield_measurement(
            env=self.env,
            m_type=m_type,
            value=value,
            shopify_unit=unit,
            reverse=True
        )

        return round(converted, 6), unit

    def set_shopify_reference_metafield_value(self, metafield_value, mapping, mk_instance_id, mk_log_id=False, target_odoo_record=False, mk_log_line_dict=None, queue_line_id=False,
                                              mk_id=False):
        """
        T6293 - Shifted the method to make it reusable as a generic method for all resources.
        T6290 - Converts Shopify reference metafield values into corresponding Odoo records.
        Handles both product and variant references (single and list). For product references,
        missing listings can be auto-imported from Shopify during the import process.
        Args:
            metafield_value (str): Shopify metafield value (GID or JSON list of GIDs).
            mapping (recordset): Recordset of shopify.metafield.mapping.ts.
            mk_instance_id (recordset): Recordset of mk.instance.
            mk_log_id (recordset, optional): Recordset of mk.log.
            target_odoo_record (recordset, optional): Parent Odoo record (product/listing).
            mk_log_line_dict (dict, optional): Dictionary to collect log messages.
            queue_line_id (recordset, optional): Recordset of mk.queue.job.line.
            mk_id (str, optional): Marketplace ID of listing or listing item.
        Returns:
            int | list | bool:
                - Returns Odoo record ID for single reference.
                - Returns ORM command [(6, 0, ids)] for list references.
                - Returns [(5, 0, 0)] if invalid JSON for list type.
                - Returns False if reference cannot be resolved.
        """

        metafield_type = mapping.types
        skip_auto_import = self.env.context.get('skip_metafield_reference_auto_import')
        origin_record_name = target_odoo_record.display_name if target_odoo_record else 'unknown'

        log_label = SHOPIFY_LOG_TITLES.get(mapping.resource_id.shopify_owner_type, '')
        owner_label = SHOPIFY_OWNER_LABELS.get(mapping.resource_id.shopify_owner_type, '')

        if mk_log_line_dict is None:
            mk_log_line_dict = {'error': [], 'success': []}

        # -------------------------------
        # Single Product Reference
        # -------------------------------
        if metafield_type == 'product_reference':
            listing_id = str(extract_numeric_id(metafield_value))

            domain = [('mk_id', '=', listing_id), ('mk_instance_id', '=', mk_instance_id.id)]
            listing_record = self.env['mk.listing'].search(domain, limit=1)

            if not listing_record and not skip_auto_import:
                self._import_missing_shopify_metafield_references(
                    [metafield_value],
                    mk_log_id=mk_log_id,
                    mk_log_line_dict=mk_log_line_dict,
                    queue_line_id=queue_line_id,
                    target_odoo_record=target_odoo_record,
                    mk_id=mk_id
                )
                listing_record = self.env['mk.listing'].search(domain, limit=1)

            if listing_record:
                return listing_record.product_tmpl_id.id

            self._log_missing_shopify_metafield_references(
                mapping,
                [listing_id],
                listing_record,  # empty recordset OK
                origin_record_name,
                mk_log_line_dict,
                queue_line_id,
                ref_type="product",
                mk_id=mk_id
            )
            return False

        # -------------------------------
        # List Product Reference
        # -------------------------------
        if metafield_type == 'list.product_reference':
            try:
                gid_list = json.loads(metafield_value)
            except (json.JSONDecodeError, TypeError):
                msg = (
                    f"IMPORT {log_label}: Failed to read reference data for "
                    f"{mapping.name} on {owner_label} {origin_record_name} ({mk_id})"
                )
                mk_log_line_dict['error'].append({
                    'log_message': msg,
                    'queue_job_line_id': queue_line_id.id if queue_line_id else False,
                })
                return [(5, 0, 0)]

            listing_ids = [str(extract_numeric_id(gid)) for gid in gid_list if gid]

            domain = [('mk_id', 'in', listing_ids), ('mk_instance_id', '=', mk_instance_id.id)]
            listing_records = self.env['mk.listing'].search(domain)

            found_ids = set(listing_records.mapped('mk_id'))
            missing_ids = [lid for lid in listing_ids if lid not in found_ids]

            if missing_ids and not skip_auto_import:
                missing_gids = [gid for gid in gid_list if str(extract_numeric_id(gid)) in missing_ids]

                self._import_missing_shopify_metafield_references(
                    missing_gids,
                    mk_log_id=mk_log_id,
                    mk_log_line_dict=mk_log_line_dict,
                    queue_line_id=queue_line_id,
                    target_odoo_record=target_odoo_record,
                    mk_id=mk_id
                )

                listing_records = self.env['mk.listing'].search(domain)
                found_ids = set(listing_records.mapped('mk_id'))
                missing_ids = [lid for lid in listing_ids if lid not in found_ids]

            if missing_ids:
                self._log_missing_shopify_metafield_references(
                    mapping,
                    missing_ids,
                    listing_records,
                    origin_record_name,
                    mk_log_line_dict,
                    queue_line_id,
                    ref_type="product",
                    mk_id=mk_id
                )

            return [(6, 0, listing_records.product_tmpl_id.ids)]

        # -------------------------------
        # Task: T9096 Metaobject Reference (single + list)
        # -------------------------------
        if 'metaobject_reference' in metafield_type:
            entry_obj = self.env['shopify.metaobject.entry.ts'].sudo().with_context(
                mk_log_id=mk_log_id, shopify_metafield=f"{mapping.name} ({mapping.metaobject_definition_id.name})")
            is_list = metafield_type.startswith('list.')

            if not mk_instance_id.enable_metaobject:
                mk_log_line_dict['error'].append({
                    'log_message': _(
                        "IMPORT %(log_label)s: Skipped metafield %(mapping_name)s on %(owner_label)s %(origin_name)s (%(mk_id)s)\n"
                        "Reason: Metaobject Functionality is turned off for instance (%(instance)s), so the linked metaobject entry cannot be read or stored.\n"
                        "How to fix:\n"
                        "  • Open the instance, go to the Metafields tab, and turn on Metaobject Functionality.") % {
                        'log_label': log_label, 'mapping_name': mapping.name, 'owner_label': owner_label,
                        'origin_name': origin_record_name, 'mk_id': mk_id, 'instance': mk_instance_id.name},
                    'queue_job_line_id': queue_line_id.id if queue_line_id else False})
                return [(5, 0, 0)] if is_list else False
            if is_list:
                try:
                    gid_list = json.loads(metafield_value)
                except (json.JSONDecodeError, TypeError):
                    mk_log_line_dict['error'].append({
                        'log_message': _(
                            "IMPORT %(log_label)s: Skipped metafield %(mapping_name)s on %(owner_label)s %(origin_name)s (%(mk_id)s)\n"
                            "Reason: Shopify sent the list of linked metaobject entries in a format Odoo could not read, so no entry was linked.") % {
                            'log_label': log_label, 'mapping_name': mapping.name, 'owner_label': owner_label,
                            'origin_name': origin_record_name, 'mk_id': mk_id},
                        'queue_job_line_id': queue_line_id.id if queue_line_id else False, })
                    return [(5, 0, 0)]
            else:
                gid_list = [metafield_value] if metafield_value else []

            entry_ids = [str(extract_numeric_id(gid)) for gid in gid_list if gid]
            domain = [('mk_id', 'in', entry_ids), ('mk_instance_id', '=', mk_instance_id.id)]
            entries = entry_obj.search(domain)

            missing_ids = [eid for eid in entry_ids if eid not in set(entries.mapped('mk_id'))]
            if missing_ids and not skip_auto_import:
                missing_gids = [gid for gid in gid_list if str(extract_numeric_id(gid)) in missing_ids]
                entry_obj.resolve_shopify_metaobject_gids(missing_gids, mk_instance_id, mk_log_line_dict=mk_log_line_dict)
                entries = entry_obj.search(domain)
                missing_ids = [eid for eid in entry_ids if eid not in set(entries.mapped('mk_id'))]

            if missing_ids:
                self._log_missing_shopify_metafield_references(
                    mapping, missing_ids, entries, origin_record_name, mk_log_line_dict,
                    queue_line_id, ref_type="metaobject entry", mk_id=mk_id)

            if is_list:
                return [(6, 0, entries.ids)]
            return entries[0].id if entries else False

        # -------------------------------
        # Variant Reference
        # -------------------------------
        mk_listing_item_obj = self.env['mk.listing.item']

        if metafield_type == 'variant_reference':
            listing_item_id = str(extract_numeric_id(metafield_value))

            listing_item = mk_listing_item_obj.search([('mk_id', '=', listing_item_id), ('mk_instance_id', '=', mk_instance_id.id)], limit=1)

            if listing_item:
                return listing_item.product_id.id

            self._log_missing_shopify_metafield_references(
                mapping,
                [listing_item_id],
                listing_item,
                origin_record_name,
                mk_log_line_dict,
                queue_line_id,
                ref_type="variant",
                mk_id=mk_id
            )
            return False

        # -------------------------------
        # List Variant Reference
        # -------------------------------
        if metafield_type == 'list.variant_reference':
            try:
                gid_list = json.loads(metafield_value)
            except (json.JSONDecodeError, TypeError):
                msg = (
                    f"IMPORT {log_label}: Failed to read reference data for "
                    f"{mapping.name} on {owner_label} {origin_record_name} ({mk_id})"
                )
                mk_log_line_dict['error'].append({
                    'log_message': msg,
                    'queue_job_line_id': queue_line_id.id if queue_line_id else False,
                })
                return [(5, 0, 0)]

            listing_item_ids = [str(extract_numeric_id(gid)) for gid in gid_list if gid]

            listing_items = mk_listing_item_obj.search(
                [('mk_id', 'in', listing_item_ids), ('mk_instance_id', '=', mk_instance_id.id)]
            )

            found_ids = set(listing_items.mapped('mk_id'))
            missing_ids = [lid for lid in listing_item_ids if lid not in found_ids]

            if missing_ids:
                self._log_missing_shopify_metafield_references(
                    mapping,
                    missing_ids,
                    listing_items,
                    origin_record_name,
                    mk_log_line_dict,
                    queue_line_id,
                    ref_type="variant",
                    mk_id=mk_id
                )

            return [(6, 0, listing_items.product_id.ids)]

        return False

    def _import_missing_shopify_metafield_references(self, missing_gids, mk_log_id=False, mk_log_line_dict=None, queue_line_id=False, target_odoo_record=False, mk_id=False):
        """
        T6293 - Shifted the method to make it reusable as a generic method for all resources.
        T6290 - This method auto-imports missing Shopify product references used in metafields.
        Args:
            missing_gids (list): List of Shopify product GIDs to be imported.
            mk_log_id (recordset): Recordset of mk.log.
            mk_log_line_dict (dict): Dictionary to store log messages.
            queue_line_id (recordset): Recordset of mk.queue.job.line.
            target_odoo_record (recordset): Record (e.g., product.template) for which metafield is being processed.
        Returns:
            bool: Returns False if no data to process or request fails, otherwise True after processing.
        """
        if not missing_gids or self.env.context.get('skip_metafield_reference_auto_import'):
            return False

        if mk_log_line_dict is None:
            mk_log_line_dict = {'error': [], 'success': []}

        origin_record_name = target_odoo_record.display_name if target_odoo_record else 'unknown'

        response = self.execute_graphql_query(GET_PRODUCTS_BY_IDS, variables={"ids": missing_gids})
        if not response:
            return False

        shopify_res = response.get('data', {}) and response.get('data', {}).get('nodes') or []

        processed_listing_ids = set()
        products_to_import = []

        for shopify_product_dict in shopify_res:
            if not shopify_product_dict:
                continue
            listing_gid = shopify_product_dict.get('id')
            if listing_gid and listing_gid not in processed_listing_ids:
                processed_listing_ids.add(listing_gid)
                products_to_import.append(shopify_product_dict)

        ctx = {
            'skip_metafield_reference_auto_import': True,
            'mk_log_id': mk_log_id,
            'queue_line_id': queue_line_id,
        }

        for product_dict in products_to_import:
            try:
                self.env['mk.listing'].with_context(**ctx).create_update_shopify_product(
                    product_dict, self
                )
            except Exception as e:
                product_name = product_dict.get('title', '') or product_dict.get('id', '')
                msg = (
                    f"IMPORT LISTING: Failed to auto-import product {product_name} "
                    f"(required for {origin_record_name} ({mk_id})): {str(e)}"
                )
                mk_log_line_dict['error'].append({
                    'log_message': msg,
                    'queue_job_line_id': queue_line_id and queue_line_id.id or False,
                })

    def _log_missing_shopify_metafield_references(self, mapping, ref_ids, records, origin_name, mk_log_line_dict, queue_line_id, ref_type="product", mk_id=False):
        """
        T6293 - Shifted the method to make it reusable as a generic method for all resources.
        T6290 - Logs missing product/variant metafield references with readable details.
        Args:
            mapping (recordset): Recordset of shopify.metafield.mapping.ts.
            ref_ids (list): List of missing shopify reference IDs.
            records (recordset): Recordset of matched listings/listing items.
            origin_name (str): Name of the parent Odoo record (e.g., product).
            mk_log_line_dict (dict): Dictionary to collect log messages.
            queue_line_id (recordset): Recordset of mk.queue.job.line.
            ref_type (str): Type of reference ('product' or 'variant').
            mk_id (str): Marketplace id of listing or listing item.
        """
        if not mk_log_line_dict:
            mk_log_line_dict = {'error': [], 'success': []}

        owner_label = SHOPIFY_OWNER_LABELS.get(mapping.resource_id.shopify_owner_type, '')
        log_label = SHOPIFY_LOG_TITLES.get(mapping.resource_id.shopify_owner_type, '')

        if ref_type == "product":
            record_map = {rec.mk_id: rec.product_tmpl_id.display_name for rec in records}
            listing_label = "listing"
        # Task: T9096
        elif ref_type == "metaobject entry":
            record_map = {rec.mk_id: rec.display_name_ts or rec.handle for rec in records}
            listing_label = "metaobject entry"
        else:
            record_map = {rec.mk_id: rec.product_id.display_name for rec in records}
            listing_label = "listing item"

        readable_refs = [record_map.get(rid, f"{rid}") for rid in ref_ids]
        bulleted_records = "  • " + "\n  • ".join(readable_refs)

        msg = _("IMPORT %(log_label)s: Skipped metafield %(mapping_name)s on %(owner_label)s %(origin_name)s (%(mk_id)s)\n"
                "\n"
                "Reason: The following referenced %(ref_type)s(s) do not have a corresponding %(listing_label)s in Odoo:\n"
                "%(bulleted_records)s\n"
                "\n"
                "How to fix:\n"
                "  1. Import the referenced %(ref_type)s(s) from Shopify into Odoo\n"
                "\n"
                "Once the corresponding %(listing_label)s(s) for all referenced %(ref_type)s(s) are available in Odoo, re-run this metafield import") % {
            'log_label': log_label,
            'mapping_name': mapping.name,
            'owner_label': owner_label,
            'origin_name': origin_name,
            'mk_id': mk_id,
            'ref_type': ref_type,
            'listing_label': listing_label,
            'bulleted_records': bulleted_records,
        }

        mk_log_line_dict['error'].append({
            'log_message': msg,
            'queue_job_line_id': queue_line_id.id if queue_line_id else False,
        })

    def _get_shopify_automatic_jobs_note(self):
        return _(
            "<ul>"
            "<li>We create <strong>variant-level</strong> pricelist rules in Odoo while importing <strong>products/listings</strong> from the marketplace.</li>"
            "<li><strong>Export/Update Product's Price in marketplace</strong> supports all pricelist rule levels - <strong>Variant, Product, Category and Global</strong> - with priority handled by Odoo's standard pricelist function.</li>"
            "<li>The system will no longer update the product prices in the marketplace if the price is set to zero.</li>"
            "</ul>"
        )
