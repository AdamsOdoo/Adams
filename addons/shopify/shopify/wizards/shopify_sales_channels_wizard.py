from odoo import models, fields, _
from odoo.addons.shopify.models.graphql_queries import (PUBLISH_PRODUCT, UNPUBLISH_PRODUCT, PUBLISH_PRODUCT_VARIANT, UNPUBLISH_PRODUCT_VARIANT, GET_SPECIFIC_PRODUCT_DATA,
                                                        PUBLISH_COLLECTION, UNPUBLISH_COLLECTION, GET_COLLECTION_PUBLICATION_STATE)
from odoo.addons.shopify.models.misc import convert_shopify_datetime_to_utc


class ShopifySalesChannelsWizard(models.TransientModel):
    _name = "shopify.sales.channels.wizard"
    _description = "Publish/Unpublish Product Publications Wizard"

    shopify_sales_channel_ids = fields.Many2many(
        comodel_name="shopify.sales.channels.ts",
        string="Sales Channels",
        relation="shopify_sales_channels_wizard_rel",
        help="Select the Shopify sales channels where this product should be published or unpublished."
    )

    def verify_listing_user_error(self, mk_listing, user_errors, mk_instance_id, mk_log_line_dict):
        """
        Task: T7628 - Added the required logging parameters and implemented logic to remove missing Shopify Sales Channels from Odoo when they no longer exist in Shopify during sales channel updates.
        """
        # Task: T7628 - Delegate to the shared handler on shopify.sales.channels.ts so this flow and
        # the bulk publish flow interpret these userErrors with one implementation.
        self.env['shopify.sales.channels.ts'].handle_shopify_publication_user_errors(
            user_errors, self.shopify_sales_channel_ids, mk_listing, mk_log_line_dict, 'UPDATE LISTING', mk_instance_id=mk_instance_id)
        return False

    def verify_collection_user_error(self, shopify_collection, user_errors, mk_instance_id, mk_log_line_dict):
        """
        Task: T7628 - Added the required logging parameters and implemented logic to remove missing Shopify Sales Channels from Odoo when they no longer exist in Shopify during sales channel updates.
        """
        # Task: T7628 - Delegate to the shared handler on shopify.sales.channels.ts so this flow and
        # the bulk publish flow interpret these userErrors with one implementation.
        self.env['shopify.sales.channels.ts'].handle_shopify_publication_user_errors(
            user_errors, self.shopify_sales_channel_ids, shopify_collection, mk_log_line_dict, 'UPDATE COLLECTION', mk_instance_id=mk_instance_id,
            missing_record_message='Collection does not exist')
        return False

    def shopify_listing_sales_channels(self, sales_channels_ids, mk_listing, mk_instance_id, mk_log_line_dict):
        """
        Task: T7628 - Added the required logging parameters in the 'verify_listing_user_error' method.
        Task: T5963 - Migrate Shopify REST API to Graphql API
        Args:
            sales_channels_ids (list): A list of sales channel IDs to which the product should be published or unpublished.
            mk_listing (object): An instance of the listing to be updated. This object is expected to have methods like `get_shopify_sales_channels`
                                and `shopify_check_is_listing_published` for handling product data.
            mk_instance_id (recordset): The record of the mk.instance model.
        """
        product_id = mk_listing.mk_id
        input_list = [{"publicationId": f"gid://shopify/Publication/{sales_channel_id}"} for sales_channel_id in sales_channels_ids]
        variables_list = {"productId": f"gid://shopify/Product/{product_id}", "input": input_list}

        # publish/unpublish product
        if self.env.context.get("publish_shopify_product", False):
            publish_data = mk_instance_id.execute_graphql_query(PUBLISH_PRODUCT, variables=variables_list)
            if publish_data:
                response = publish_data.get('data', {}).get('publishablePublish', {}) if isinstance(publish_data, dict) else {}
                user_errors = response.get('userErrors', []) if response.get('userErrors', []) else []
                if user_errors:
                    self.verify_listing_user_error(mk_listing, user_errors, mk_instance_id, mk_log_line_dict)
                    return False

        elif self.env.context.get("unpublish_shopify_product", False):
            unpublish_data = mk_instance_id.execute_graphql_query(UNPUBLISH_PRODUCT, variables=variables_list)
            if unpublish_data:
                response = unpublish_data.get('data', {}).get('publishableUnpublish', {}) if isinstance(unpublish_data, dict) else {}
                user_errors = response.get('userErrors', []) if response.get('userErrors', []) else []
                if user_errors:
                    self.verify_listing_user_error(mk_listing, user_errors, mk_instance_id, mk_log_line_dict)
                    return False

        # Fetch updated product data
        variables = {"productId": f"gid://shopify/Product/{product_id}"}
        res = mk_instance_id.execute_graphql_query(GET_SPECIFIC_PRODUCT_DATA, variables)
        result_dict = res.get('data', {}).get('product', {}) if isinstance(res, dict) else {}

        updated_at = convert_shopify_datetime_to_utc(result_dict.get('updatedAt', ""))
        published_at = convert_shopify_datetime_to_utc(result_dict.get('publishedAt', ""))
        shopify_sales_channel_ids, shopify_sales_channel_ids_list = mk_listing.get_shopify_sales_channels(result_dict.get('resourcePublications', {}))
        listing_vals = {
            'listing_publish_date': published_at,
            'listing_update_date': updated_at,
        }
        shopify_sales_channel_ids and listing_vals.update(shopify_sales_channel_ids)

        is_published = mk_listing.shopify_check_is_listing_published(shopify_sales_channel_ids_list)
        listing_vals.update({'is_published': is_published})

        # Update the listing with updated values
        mk_listing.write(listing_vals)

    def shopify_listing_item_sales_channels(self, sales_channels_ids, listing_item, mk_instance_id, mk_log_line_dict):
        """
        Task: T7796 - Publish/unpublish a specific variant using variant-level Shopify GraphQL mutations (PUBLISH_PRODUCT_VARIANT / UNPUBLISH_PRODUCT_VARIANT), then fetch the updated
            resourcePublicationsV2 for that variant and write back only to listing_item.shopify_sales_channel_ids.
        Args:
            sales_channels_ids (list): Shopify publication IDs to publish/unpublish.
            listing_item (recordset): The mk.listing.item record.
            mk_instance_id (recordset): The mk.instance record.
            mk_log_line_dict (dict): Log accumulator.
        """
        listing_item_id = listing_item.mk_id
        input_list = [{"publicationId": f"gid://shopify/Publication/{ch}"} for ch in sales_channels_ids]
        variables_list = {"variantId": f"gid://shopify/ProductVariant/{listing_item_id}", "input": input_list}

        if self.env.context.get("publish_shopify_product", False):
            publish_data = mk_instance_id.execute_graphql_query(PUBLISH_PRODUCT_VARIANT, variables=variables_list)
            if publish_data:
                response = publish_data.get('data', {}).get('publishablePublish', {}) if isinstance(publish_data, dict) else {}
                user_errors = response.get('userErrors', [])
                if user_errors:
                    for user_error in user_errors:
                        error_message = user_error.get("message", "")
                        log_message = _("UPDATE LISTING ITEM: Failed to update sales channels for Listing item %s (%s) ERROR: %s") % (listing_item.name, listing_item.mk_id, error_message)
                        mk_log_line_dict['error'].append({'log_message': log_message})
                    return False
            listing_item.write({'shopify_sales_channel_ids': [(4, channel.id) for channel in self.shopify_sales_channel_ids]})

        elif self.env.context.get("unpublish_shopify_product", False):
            unpublish_data = mk_instance_id.execute_graphql_query(UNPUBLISH_PRODUCT_VARIANT, variables=variables_list)
            if unpublish_data:
                response = unpublish_data.get('data', {}).get('publishableUnpublish', {}) if isinstance(unpublish_data, dict) else {}
                user_errors = response.get('userErrors', [])
                if user_errors:
                    for user_error in user_errors:
                        error_message = user_error.get("message", "")
                        log_message = _("UPDATE LISTING ITEM: Failed to update sales channels for Listing item %s (%s) ERROR: %s") % (listing_item.name, listing_item.mk_id, error_message)
                        mk_log_line_dict['error'].append({'log_message': log_message})
                    return False
            listing_item.write({'shopify_sales_channel_ids': [(3, ch.id) for ch in self.shopify_sales_channel_ids]})

        log_message = _("UPDATE LISTING ITEM: Sales channels updated for %s (%s)") % (listing_item.name, listing_item.mk_id)
        mk_log_line_dict['success'].append({'log_message': log_message})

    def shopify_collection_sales_channels(self, sales_channels_ids, collections, mk_instance_id, mk_log_line_dict):
        """
        Task: T7628 - Added the required logging parameters in the verify_collection_user_error method.
        Task: T5963 - Migrate Shopify REST API to Graphql API
        Task: T7545 - Improvements for 2026-07 version changes and handling deprecated publish/unpublish mutations
        Args:
            sales_channels_ids (list): A list of sales channel IDs to which the product should be published or unpublished.
            collections (object): An instance of the collections to be updated. This object is expected to have methods like `get_shopify_sales_channels_collection`
                                and `shopify_check_is_collection_published` for handling product data.
            mk_instance_id (recordset): The record of the mk.instance model.
        """
        shopify_collection = collections
        collection_id = collections.shopify_collection_id
        input_list = [{"publicationId": f"gid://shopify/Publication/{sales_channel_id}"} for sales_channel_id in sales_channels_ids]

        variables = {"id": f"gid://shopify/Collection/{collection_id}", "publications": input_list}

        # publish/unpublish collection
        if self.env.context.get("publish_shopify_collection", False):
            res = mk_instance_id.execute_graphql_query(PUBLISH_COLLECTION, variables)
            if res:
                response = res.get('data', {}).get('publishablePublish', {}) if isinstance(res, dict) else {}
                user_errors = response.get('userErrors', []) if response and response.get('userErrors', []) else []
                if user_errors:
                    self.verify_collection_user_error(shopify_collection, user_errors, mk_instance_id, mk_log_line_dict)
                    return False

        elif self.env.context.get("unpublish_shopify_collection", False):
            res = mk_instance_id.execute_graphql_query(UNPUBLISH_COLLECTION, variables)
            if res:
                response = res.get('data', {}).get('publishableUnpublish', {}) if isinstance(res, dict) else {}
                user_errors = response.get('userErrors', []) if response and response.get('userErrors', []) else []
                if user_errors:
                    self.verify_collection_user_error(shopify_collection, user_errors, mk_instance_id, mk_log_line_dict)
                    return False

        # Fetch updated collection data. Task: T8887 - read with a plain query, as Shopify refuses the old way.
        variables = {"id": f"gid://shopify/Collection/{collection_id}"}
        res = mk_instance_id.execute_graphql_query(GET_COLLECTION_PUBLICATION_STATE, variables)
        transport_errors = res.get('errors', []) if isinstance(res, dict) else []
        if transport_errors and isinstance(transport_errors, list):
            mk_instance_id.handle_shopify_access_errors(transport_errors, "Collection Publication State")
        result_dict = res.get('data', {}).get('collection', {}) if res.get('data', {}) else {}
        if not result_dict:
            self.verify_collection_user_error(shopify_collection, [{'field': None, 'message': 'Collection does not exist'}], mk_instance_id, mk_log_line_dict)
            return False

        updated_at = convert_shopify_datetime_to_utc(result_dict.get('updatedAt', ""))
        # Task: T7723 - Added instance parameter for instance-wise sales channel fetch.
        shopify_sales_channel_ids, shopify_sales_channel_ids_list = shopify_collection.get_shopify_sales_channels_collection(result_dict, mk_instance_id)
        collection_vals = {
            'shopify_update_date': updated_at,
        }
        shopify_sales_channel_ids and collection_vals.update(shopify_sales_channel_ids)

        is_published = shopify_collection.shopify_check_is_collection_published(shopify_sales_channel_ids_list)
        collection_vals.update({'is_available_in_website': is_published})

        # Update the collection with updated values
        shopify_collection.write(collection_vals)

    def action_manage_shopify_sales_channels(self):
        """
        Task: T7628 - For managing the logging added the required parameters in 'shopify_listing_sales_channels' and 'shopify_collection_sales_channels'.
        Task: T5963 - Migrate Shopify REST API to Graphql API
        Task: T7468 - Raise a redirect warning for the instance with a dynamic error message and open the corresponding instance form view.
        Publishes or unpublishes a Shopify product or collection based on the context.
        The context indicates the target (product or collection) and action (publish or unpublish).
        """
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_record_id')
        active_id = self.env[active_model].browse(active_id)
        mk_instance_id = active_id.sudo().mk_instance_id
        if mk_instance_id.state != 'confirmed':
            error_msg = "You can update a sales channels only with a confirm instance. Please ensure the instance is confirm before updating the sales channels."
            mk_instance_id.show_shopify_instance_redirect_warning(error_msg)

        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
        mk_log_line_dict = {'error': [], 'success': []}
        try:
            mk_instance_id.connection_to_shopify()
            sales_channels_ids = self.shopify_sales_channel_ids.mapped('sales_channel_id')

            if self.env.context.get('active_model') == 'mk.listing':
                self.shopify_listing_sales_channels(sales_channels_ids, active_id, mk_instance_id, mk_log_line_dict)
            elif self.env.context.get('active_model') == 'mk.listing.item':
                self.shopify_listing_item_sales_channels(sales_channels_ids, active_id, mk_instance_id, mk_log_line_dict)
            elif self.env.context.get('active_model') == 'shopify.collection.ts':
                self.shopify_collection_sales_channels(sales_channels_ids, active_id, mk_instance_id, mk_log_line_dict)
        except Exception as e:
            mk_log_line_dict['error'].append({'log_message': f'UPDATE LISTING: Failed to publish/unpublish on Shopify: {e}'})

        self.env['mk.log'].create_update_log(mk_log_id=mk_log_id, mk_instance_id=mk_instance_id, mk_log_line_dict=mk_log_line_dict)
        if mk_log_id and not mk_log_id.log_line_ids:
            mk_log_id.unlink()
        return True
