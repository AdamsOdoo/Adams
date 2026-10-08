from odoo import models, fields, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import GET_ALL_PRODUCT_PUBLICATIONS
from odoo.addons.shopify.models.misc import extract_numeric_id


class ShopifySalesChannels(models.Model):
    _name = "shopify.sales.channels.ts"
    _description = "Shopify Sales Channels"

    name = fields.Char("Name", required=True)
    sales_channel_id = fields.Char("Sales Channel ID", required=True)
    mk_instance_id = fields.Many2one('mk.instance', string='Marketplace Instance', ondelete='cascade', index=True)

    def import_shopify_sales_channels(self, mk_instance_id):
        """
        Task: T4887 - Migrate Shopify REST API to Graphql API
        This method will import all publications(sales channel) from shopify to 'shopify.sales.channels.ts' model.
        Args:
            mk_instance_id (record): Recordset of mk.instance model.
        Raises:
            MarketplaceException: If the GraphQL query fails or any error occurs during the API request.
        """
        self = self.sudo()
        try:
            res = mk_instance_id.execute_graphql_query(GET_ALL_PRODUCT_PUBLICATIONS)
            user_errors = res.get('errors', []) if isinstance(res, dict) else {}
            if user_errors and isinstance(user_errors, list):
                err_messages = [e.get('message', str(e)) for e in user_errors]
                joined_errors = ", ".join(err_messages)
                raise MarketplaceException(_("⚠️ Failed to fetch Shopify Sales Channel: %(errors)s") % {'errors': joined_errors})

            if res:
                sales_channels = res and res.get("data", {}) and res.get("data", {}).get("catalogs", [])
                for channel in sales_channels:

                    publication = channel.get("publication", False)
                    if not publication:
                        continue

                    sales_channel_id = str(extract_numeric_id(publication.get("id", "")))

                    nodes = publication.get("catalog", {}).get("apps", {}).get("nodes", [])
                    channel_name = nodes[0].get("title") if nodes else False

                    if not channel_name:
                        continue

                    if not self.search([("sales_channel_id", "=", sales_channel_id), ("mk_instance_id", "=", mk_instance_id.id)], limit=1):
                        self.create({
                            "name": channel_name,
                            "sales_channel_id": sales_channel_id,
                            "mk_instance_id": mk_instance_id.id,
                        })
        except MarketplaceException:
            raise
        except Exception as e:
            raise MarketplaceException(_(f"Error while importing the shopify sales channel: {e}"))

    def handle_shopify_publication_user_errors(self, user_errors, sales_channel_records, mk_record, mk_log_line_dict, log_prefix, mk_instance_id=None,
                                               missing_record_message="Resource does not exist", unlink_missing_channels=True):
        """
        Task: T7628 - Single place that interprets publish/unpublish userErrors for listings and
        collections, used by both the per-record flow and the bulk publish flow so the handling is
        never duplicated.
        Args:
            user_errors (list): Shopify userErrors entries.
            sales_channel_records (recordset): Channels IN THE SAME ORDER that was sent to Shopify -
                an error points at a channel by its index (field: ['input', '<index>', 'publicationId']).
            mk_record (record): mk.listing or shopify.collection.ts the errors belong to.
            mk_log_line_dict (dict): Log collector for success/error messages.
            log_prefix (str): Log label, e.g. 'EXPORT/UPDATE LISTING' or 'UPDATE COLLECTION'.
            mk_instance_id (record, optional): Instance, used only to name the instance in logs.
            missing_record_message (str): Message meaning the record itself is gone on Shopify.
            unlink_missing_channels (bool): False for the bulk flow, which accumulates across JSONL
                lines and calls log_and_unlink_missing_channels() once after its loop.
        Returns:
            tuple: (missing_channel_records, is_record_unlinked)
        """
        missing_channels = self.browse()
        is_record_unlinked = False
        record_name = mk_record.name if mk_record else ''
        record_mk_id = (mk_record.mk_id if 'mk_id' in mk_record._fields else mk_record.shopify_collection_id) if mk_record else ''
        instance_name = mk_instance_id.name if mk_instance_id else ''

        for user_error in user_errors:
            message = user_error.get("message") or ""
            field = user_error.get("field") or []

            if message == missing_record_message and mk_record:
                log_message = _("Removing %s (%s) from Instance %s - it no longer exists on Shopify") % (record_name, record_mk_id, instance_name)
                mk_log_line_dict['error'].append({'log_message': f'{log_prefix}: {log_message}'})
                mk_record.sudo().unlink()
                is_record_unlinked = True
                continue

            if "Publication does not exist or is not publishable" in message:
                try:
                    sales_channel_index = int(field[1])
                    # Prevent IndexError if field list is too short
                    if 0 <= sales_channel_index < len(sales_channel_records):
                        missing_channels |= sales_channel_records[sales_channel_index].exists()
                        continue
                except Exception as e:
                    log_message = f"Exception occurred while processing missing Shopify Sales Channel for {record_name} ({record_mk_id}) in Instance {instance_name}: {e}"
                    mk_log_line_dict['error'].append({'log_message': f'{log_prefix}: {log_message}'})

            log_message = _("❌ Sales Channel update failed for %s (%s) in Instance %s: %s") % (record_name, record_mk_id, instance_name, message)
            mk_log_line_dict['error'].append({'log_message': f'{log_prefix}: {log_message}'})

        if missing_channels and unlink_missing_channels:
            self.log_and_unlink_missing_channels(missing_channels, mk_log_line_dict, log_prefix)
        return missing_channels, is_record_unlinked

    def log_and_unlink_missing_channels(self, missing_channels, mk_log_line_dict, log_prefix):
        """
        Task: T7628 - Log then remove the sales channels that no longer exist on Shopify.
        Logging happens BEFORE the unlink: reading name/sales_channel_id afterwards raises MissingError.
        Args:
            missing_channels (recordset): Channels to remove.
            mk_log_line_dict (dict): Log collector for success/error messages.
            log_prefix (str): Log label, e.g. 'EXPORT/UPDATE LISTING'.
        Returns:
            bool: Always True.
        """
        missing_channels = missing_channels.exists()
        for channel in missing_channels:
            log_message = _("Removed Sales Channel %s (%s) as it no longer exists in Shopify") % (channel.name, channel.sales_channel_id)
            mk_log_line_dict['error'].append({'log_message': f'{log_prefix}: {log_message}'})
        missing_channels.sudo().unlink()
        return True
