import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import psycopg2
import requests

from odoo import api, models, fields, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import GET_BULK_OPERATION_BY_ID, BULK_MUTATION_RUN, BULK_OPERATION_PRODUCT_SET
from odoo.addons.shopify.models.marketplace_listing import SHOPIFY_MAX_CONCURRENT_BULK
from odoo.addons.shopify.models.misc import convert_shopify_datetime_to_utc, extract_numeric_id

_logger = logging.getLogger("Teqstars:Shopify")

MAX_RETRIES = 3


class ShopifyBulkQuery(models.Model):
    _name = "shopify.bulk.query"
    _description = "Shopify Bulk Query Operation"
    _rec_name = "name"
    _order = 'id desc'

    name = fields.Char(string="Title")
    shopify_operation_type = fields.Selection(selection=[('import_listing', 'Import Listing'), ('import_inventory', 'Import Inventory'), ('export_listing', 'Export Listing'), ('update_listing', 'Update Listing'), ('export_price', 'Export Price'), ('export_inventory', 'Export Inventory')], string="Operation Type")
    bulk_operation_id = fields.Char(string="Bulk Operation ID", help="Shopify Bulk Operation ID (e.g. gid://shopify/BulkOperation/123)")
    mk_instance_id = fields.Many2one("mk.instance", string="Instance", ondelete='cascade')
    mk_log_id = fields.Many2one('mk.log', string='Log')
    status = fields.Selection(
        selection=[('QUEUED', 'Queued'), ('RUNNING', 'Running'), ('COMPLETED', 'Completed'), ('CANCELING', 'Canceling'), ('CANCELED', 'Canceled'), ('FAILED', 'Failed'),
                   ('EXPIRED', 'Expired'), ], string="Status", help=("QUEUED: Waiting for a free Shopify bulk operation slot.\n"
                                                                     "RUNNING: Operation is currently running.\n"
                                                                     "COMPLETED: Operation has successfully completed.\n" "CANCELING: Cancellation has been initiated (short delay before fully canceled).\n" "CANCELED: Operation has been canceled.\n"
                                                                     "FAILED: Operation has failed. Check errorCode for details.\n" "EXPIRED: The result URL has expired."))
    no_of_retry_count = fields.Integer(string="Retry Count", default=0, help="Number of times the cron has polled this bulk operation.")
    message = fields.Text(string="Message")
    export_pending_data = fields.Text(string="Export Pending Data")
    result_url = fields.Char(string="Result URL", help="Shopify bulk result file URL, processed by the batch cron.")
    result_attachment_id = fields.Many2one('ir.attachment', string="Result File", ondelete='set null', help="Shopify bulk result JSONL downloaded once and kept until the whole process finishes (no URL-expiry risk).")
    batch_offset = fields.Integer(string="Batch Offset", default=0, help="Products already applied to Odoo (resume point for the batch cron).")
    bulk_group_key = fields.Char(string="Group Reference", index=True, help="Groups the bulk operations that were created from one export/update request.")
    chunk_sequence = fields.Integer(string="File Number", default=1, help="Position of this file inside the request payload.")
    chunk_total = fields.Integer(string="Total Files", default=1, help="Number of files the request payload was split into.")
    jsonl_attachment_id = fields.Many2one('ir.attachment', string="Payload File", ondelete='set null',
                                          help="JSONL payload waiting to be uploaded to Shopify. Removed once the bulk operation has been started.")

    def action_click_on_retry_count(self):
        """
        Task: T7568 - Handle click action for the Retry Count smart button.
        """
        return True

    @api.autovacuum
    def _auto_vacuum_shopify_bulk_data(self):
        """
        Task: T7609 - Drop completed Shopify bulk records older than 10 days.
        For export_listing / update_listing also require result_url to be empty.
        """
        threshold = fields.Datetime.now() - timedelta(days=10)
        self.search([('status', '=', 'COMPLETED'), ('create_date', '<', threshold), '|', ('shopify_operation_type', 'not in', ('export_listing', 'update_listing')), '&', ('shopify_operation_type', 'in', ('export_listing', 'update_listing')), ('result_url', '=', False), ]).unlink()

    def _get_shopify_bulk_access_denied_message(self, user_errors):
        """
        Task: T7609 - Build ONE friendly instance-level message when bulk result lines failed due to a
        missing Shopify app access scope (e.g. write_products); returns empty string when no access error found.
        Args:
            user_errors (list): Flat list of error dicts collected from the bulk result lines.
        Returns:
            str: Friendly instance-level message, or '' when no access error.
        """
        for error in user_errors:
            message = error.get('message', '') if isinstance(error, dict) else str(error)
            if 'Access denied' in message or 'access scope' in message:
                return f"{message}"
        return ''

    def _count_running_shopify_bulk_operations(self, mk_instance_id):
        """
        Task: T7609 - Count the bulk operations that currently occupy a Shopify slot for one instance.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
        Returns:
            int: Number of operations Shopify still considers in progress.
        """
        return self.search_count([('mk_instance_id', '=', mk_instance_id.id), ('shopify_operation_type', 'in', ['export_listing', 'update_listing', 'export_price', 'export_inventory']), ('status', 'in', ['RUNNING', 'CANCELING'])])

    def start_shopify_queued_bulk_operations(self, mk_instance_id, apply_inline=False):
        """
        Task: T7609 - Start queued payload files while Shopify has a free bulk slot.
        A request whose payload was split waits in QUEUED state; this dispatcher uploads and runs the next
        files, so a 500 MB payload becomes as many bulk operations as needed without ever exceeding the
        concurrent-operations limit. It runs from the poll cron and right after a request is created.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance.
            apply_inline (bool): True when called from the user's request, so a single file that finishes
                during the short poll is applied immediately instead of waiting for the cron.
        Returns:
            recordset: The bulk operations that were started.
        """
        started_records = self.browse()
        if not mk_instance_id:
            return started_records

        # Cheapest check first: a request that was never split has nothing queued, so this costs one
        # indexed count and the caller pays nothing else - no slot count, no Shopify connection.
        if not self.search_count([('mk_instance_id', '=', mk_instance_id.id), ('status', '=', 'QUEUED')]):
            return started_records

        free_slots = SHOPIFY_MAX_CONCURRENT_BULK - self._count_running_shopify_bulk_operations(mk_instance_id)
        if free_slots <= 0:
            return started_records

        mk_instance_id.connection_to_shopify()
        for _slot in range(free_slots):
            # Lock ONE queued file at a time and skip rows another worker already took: two cron workers
            # (or a cron and the user's own request) must never upload the same payload twice.
            self.env.cr.execute("""
                SELECT id
                  FROM shopify_bulk_query
                 WHERE mk_instance_id = %s
                   AND status = 'QUEUED'
                   AND jsonl_attachment_id IS NOT NULL
                 ORDER BY bulk_group_key, chunk_sequence, id
                 LIMIT 1
                   FOR UPDATE SKIP LOCKED
            """, (mk_instance_id.id,))
            queued_row = self.env.cr.fetchone()
            if not queued_row:
                break

            record = self.browse(queued_row[0])
            try:
                if record._start_shopify_queued_bulk_chunk(apply_inline=apply_inline):
                    started_records |= record
                self.env.cr.commit()
            except Exception as e:
                # Roll back first: the failure must not leave a half-written record, and the file has to be
                # marked FAILED in its own transaction or the cron would retry it forever.
                self.env.cr.rollback()
                message = f"Failed to start bulk operation for payload file: {e}"
                _logger.error("BULK LISTING: %s", message)
                record.write({'status': 'FAILED', 'message': message})
                if record.mk_log_id and record.mk_log_id.exists():
                    self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=record.mk_log_id,
                                                         mk_log_line_dict={'error': [{'log_message': f"BULK LISTING: {message}"}], 'success': []})
                self.env.cr.commit()
        return started_records

    def _start_shopify_queued_bulk_chunk(self, apply_inline=False):
        """
        Task: T7609 - Upload one queued payload file and run its bulk mutation.
        Args:
            apply_inline (bool): Apply the result immediately when this is the only file of the request and
                Shopify already finished it during the short poll.
        Returns:
            bool: True when Shopify accepted the operation.
        Raises:
            MarketplaceException: If staging fails or Shopify rejects the bulk operation.
        """
        self.ensure_one()
        mk_listing_obj = self.env['mk.listing']
        mk_instance_id = self.mk_instance_id
        log_prefix = 'EXPORT LISTING' if self.shopify_operation_type == 'export_listing' else 'UPDATE LISTING'

        attachment = self.jsonl_attachment_id
        jsonl_lines = [line.decode('utf-8') for line in (attachment.raw or b'').splitlines() if line] if attachment else []
        if not jsonl_lines:
            message = f"{log_prefix}: The payload file of this bulk operation is missing or empty."
            _logger.error(message)
            self.write({'status': 'FAILED', 'message': message})
            return False

        staged_path = mk_listing_obj.upload_jsonl_to_shopify(mk_instance_id, jsonl_lines, attachment.name, log_prefix)
        if not staged_path:
            raise MarketplaceException(_("%s: Failed to stage the payload file %s to Shopify. Check logs for details.") % (log_prefix, attachment.name))

        variable = {
            "mutation": BULK_OPERATION_PRODUCT_SET.strip(),
            "stagedUploadPath": staged_path,
            "clientIdentifier": f"odoo-listing-{uuid.uuid4().hex[:12]}",
        }
        response = mk_instance_id.execute_graphql_query(BULK_MUTATION_RUN, variable)
        query_errors = response.get('errors', []) if isinstance(response, dict) else []
        if query_errors and isinstance(query_errors, list):
            mk_instance_id.handle_shopify_access_errors(query_errors, "Bulk Query Run")
        bulk_run = (response or {}).get('data', {}).get('bulkOperationRunMutation', {}) or {}
        user_errors = bulk_run.get('userErrors') or []
        if user_errors:
            raise MarketplaceException(_("Shopify rejected bulk operation: %s") % user_errors)

        bulk_operation = bulk_run.get('bulkOperation') or {}
        bulk_id = extract_numeric_id(bulk_operation.get('id', '')) if bulk_operation.get('id') else ''
        allowed_statuses = {'RUNNING', 'COMPLETED', 'CANCELING', 'CANCELED', 'FAILED', 'EXPIRED'}
        shopify_status = bulk_operation.get('status') or 'RUNNING'
        if shopify_status not in allowed_statuses:
            shopify_status = 'RUNNING'

        # The payload is on Shopify now, so the local copy is dead weight - drop it before it can pile up
        # in the filestore for a big multi-file request.
        self.write({'status': shopify_status, 'bulk_operation_id': bulk_id, 'jsonl_attachment_id': False})
        attachment.unlink()
        _logger.info("%s: started bulk operation %s (file %s/%s).", log_prefix, bulk_id, self.chunk_sequence, self.chunk_total)

        if apply_inline and self.chunk_total <= 1 and bulk_id and shopify_status not in ('COMPLETED', 'FAILED', 'CANCELED', 'EXPIRED'):
            poll_data = mk_listing_obj.poll_check_shopify_bulk_operation_status(bulk_id, mk_instance_id)
            polled_status = poll_data.get('status', '')
            result_url = poll_data.get('url', '') or ''
            if polled_status == 'COMPLETED' and result_url:
                self.write({'status': polled_status})
                try:
                    self.handle_shopify_bulk_export_listing(self, mk_instance_id, result_url)
                except Exception as e:
                    _logger.error("%s: applying the bulk result failed: %s", log_prefix, e)
                    if self.mk_log_id and self.mk_log_id.exists():
                        self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=self.mk_log_id,
                                                             mk_log_line_dict={'error': [{'log_message': f"{log_prefix}: applying the bulk result failed: {e}"}], 'success': []})
            elif polled_status in allowed_statuses:
                self.write({'status': polled_status})
        return True

    def _shopify_bulk_group_records(self):
        """
        Task: T7609 - All bulk operations created from the same export/update request.
        Returns:
            recordset: Every file of the group, or just this record when the payload was not split.
        """
        self.ensure_one()
        if not self.bulk_group_key:
            return self
        return self.search([('bulk_group_key', '=', self.bulk_group_key)])

    def _is_last_shopify_bulk_chunk(self):
        """
        Task: T7609 - Tell whether this file is the last one of its request still to be applied.
        The follow-up steps (publish, metafield delete) must run ONCE for the whole request, not once per
        file, so they are only triggered from the file that finishes last.
        Returns:
            bool: True when no other file of the group is still queued, running or waiting to be applied.
        """
        self.ensure_one()
        if not self.bulk_group_key or self.chunk_total <= 1:
            return True
        siblings = self._shopify_bulk_group_records().filtered(lambda record: record.id != self.id)
        return not siblings.filtered(lambda record: record.status in ('QUEUED', 'RUNNING', 'CANCELING') or (record.status == 'COMPLETED' and record.result_url))

    def _shopify_bulk_group_listing_ids(self):
        """
        Task: T7609 - Listings of EVERY file of the request, so the follow-up steps cover the whole
        selection and not only the listings of the file that happened to finish last.
        Returns:
            recordset: mk.listing records of the group that still exist.
        """
        self.ensure_one()
        mk_listing_obj = self.env['mk.listing']
        listing_ids = []
        for record in self._shopify_bulk_group_records():
            listing_ids.extend(mk_listing_obj.export_shopify_pending_payload(record).get('listing_ids') or [])
        return mk_listing_obj.browse(list(dict.fromkeys(listing_ids))).exists()

    def handle_shopify_bulk_export_listing(self, shopify_bulk_query_id, mk_instance_id, result_url):
        """
        Task: T7609 - Apply a completed Shopify bulk export/update result: parse the JSONL, match
        each product to its Odoo listing, sync data and images, log per-line outcomes, and chain
        a bulk publish run if sales channels were requested.
        Args:
            shopify_bulk_query_id (record): shopify.bulk.query record being processed.
            mk_instance_id (record): Marketplace instance.
            result_url (str): Shopify bulk result file URL.
        Returns:
            bool: True on success, False if the JSONL could not be downloaded or publish branch was taken.
        """
        mk_listing_obj = self.env['mk.listing']
        payload = mk_listing_obj.export_shopify_pending_payload(shopify_bulk_query_id)
        if payload.get('phase') == 'publish':
            return mk_listing_obj._process_shopify_bulk_publish_result(shopify_bulk_query_id, mk_instance_id, result_url)
        # Task: T7609 - Metafield delete phase: productSet cannot delete a metafield, so emptied values
        # are removed by their own chained metafieldsDelete bulk record.
        if payload.get('phase') == 'metafield_delete':
            return mk_listing_obj._process_shopify_bulk_metafield_delete_result(shopify_bulk_query_id, mk_instance_id, result_url)

        operation_type = payload.get('mode', 'export')
        listing_ids = payload.get('listing_ids', [])
        sku_map = payload.get('listing_sku_map', {})
        barcode_map = payload.get('listing_barcode_map', {})
        is_set_images = payload.get('is_set_images')
        sales_channel_ids = payload.get('shopify_sales_channel_ids', [])
        is_publish_or_unpublish = payload.get('is_publish_or_unpublish', True) if operation_type == 'update' else True

        listings = mk_listing_obj.browse(listing_ids).exists()
        mk_log_id = shopify_bulk_query_id.mk_log_id or self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
        mk_log_line_dict = {'error': [], 'success': []}
        sku_to_listing = {sku: int(lid) for lid, sku in sku_map.items() if sku}
        barcode_to_listing = {bc: int(lid) for lid, bc in barcode_map.items() if bc}

        raw_lines = mk_listing_obj.get_shopify_bulk_result_of_jsonl(result_url, shopify_bulk_query_id, f"BULK {operation_type.upper()} LISTING")
        if raw_lines is None:
            return False

        successful_listings = mk_listing_obj
        shopify_user_errors = []
        returned_ids = set()

        # Pre-parse JSONL: match each result to its listing and write mk_id for export
        # listings so the post-bulk media batch fetch can resolve them in ONE GraphQL
        # call instead of falling back to per-listing requests inside the apply loop.
        to_apply = []
        for raw_line in raw_lines:
            product, errors = mk_listing_obj.prepare_shopify_response_for_the_jsonl_file(raw_line)
            if errors:
                shopify_user_errors.append(errors)
            if not product:
                continue
            if product.get('id'):
                returned_ids.add(str(extract_numeric_id(product.get('id'))))

            listing = mk_listing_obj.match_shopify_listing_from_bulk_result(product, operation_type, listings, sku_to_listing, barcode_to_listing, mk_instance_id.sync_product_with)
            if not listing:
                mk_log_line_dict['error'].append({
                    'log_message': f"BULK {operation_type.upper()} LISTING: result {product.get('id')} could not be matched to an Odoo listing"})
                continue
            if operation_type == 'export' and not listing.mk_id and product.get('id'):
                listing.mk_id = str(extract_numeric_id(product.get('id')))
            to_apply.append((listing, product))

        # Task: T7609 - Access scope errors are instance-level, not per-product: log ONE line and STOP here.
        # Skip the apply loop, the update-mode missing-product unlink and the publish step - products came back empty because of the scope error, NOT because they were deleted on Shopify.
        access_denied_message = self._get_shopify_bulk_access_denied_message([error for errors in shopify_user_errors for error in errors])
        if access_denied_message:
            mk_log_line_dict['error'].append({'log_message': access_denied_message})
            mk_listing_obj._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)
            shopify_bulk_query_id.write({'status': 'COMPLETED', 'message': access_denied_message})
            return False

        media_cache = {}
        if is_set_images and to_apply:
            listings_needing_media = mk_listing_obj
            for listing, _ in to_apply:
                if listing.mk_id and listing.image_ids and not all(listing.image_ids.mapped('media_id')):
                    listings_needing_media |= listing
            if listings_needing_media:
                # Task: T7609 - Media fetch failure (e.g. missing read_products scope) is instance-level: log ONE line, skip image sync for ALL listings (is_set_images=False also stops the per-listing fallback fetch) and keep applying product data.
                try:
                    media_cache = listings_needing_media._fetch_shopify_product_media_batch()
                except MarketplaceException as e:
                    is_set_images = False
                    mk_log_line_dict['error'].append({'log_message': f"BULK {operation_type.upper()} LISTING: Image sync skipped for all listings - {e}"})

        for listing, product in to_apply:
            if mk_listing_obj.apply_shopify_bulk_export_result_to_listing(listing, product, is_set_images, operation_type, mk_log_line_dict, media_cache=media_cache):
                successful_listings |= listing
            self.env.cr.commit()

        # Update mode: listings whose Shopify product did not come back were deleted on Shopify - remove from Odoo.
        # Task: T7433 - Exclude skipped_ids (Skip Listing Sync / missing SKU-barcode): they were never in the JSONL,
        # so their absence from the result does NOT mean they were deleted on Shopify - never unlink them.
        if operation_type == 'update':
            skipped_ids = set(payload.get('skipped_ids') or [])
            missing_listing_ids = listings.filtered(lambda l: l.mk_id and l.mk_id not in returned_ids and l.id not in skipped_ids)
            if missing_listing_ids and not access_denied_message:
                for missing_listing_id in missing_listing_ids:
                    mk_log_line_dict['error'].append({'log_message': f"BULK UPDATE LISTING: Product '{missing_listing_id.name} ({missing_listing_id.mk_id})' was deleted from Odoo along with its variants, because it was deleted in Shopify."})
                missing_listing_ids.sudo().unlink()

        mk_listing_obj._handle_shopify_log_creation(mk_instance_id, mk_log_id, mk_log_line_dict)

        # _handle_shopify_log_creation unlinks the log when it has no lines (e.g. log_level='error'
        # with only successes). Drop the stale reference so the publish step doesn't write a dangling
        # mk_log_id foreign key; the publish flow creates its own log when one is needed.
        if mk_log_id and not mk_log_id.exists():
            mk_log_id = self.env['mk.log']

        # Task: T7609 - Single-file request (the normal case) keeps the exact same path as before: no extra
        # query, no extra work. Only a payload that had to be split pays for the group lookup, and there the
        # publish / metafield steps run ONCE, from the file that finishes last, for every listing of the group.
        chain_listings = successful_listings
        if shopify_bulk_query_id.chunk_total > 1:
            chain_listings = shopify_bulk_query_id._shopify_bulk_group_listing_ids() if shopify_bulk_query_id._is_last_shopify_bulk_chunk() else mk_listing_obj

        publish_bulk_record = mk_listing_obj.trigger_shopify_bulk_publish_after_export(chain_listings, is_publish_or_unpublish, sales_channel_ids, mk_instance_id, mk_log_id)
        metafield_bulk_record = mk_listing_obj.trigger_shopify_bulk_metafield_delete_after_export(chain_listings, mk_instance_id, mk_log_id, operation_type, has_publish_step=bool(publish_bulk_record))

        shopify_bulk_query_id.write({
            'status': 'COMPLETED',
            'message': access_denied_message or ('\n'.join(e.get('message', '') for errs in shopify_user_errors for e in errs) if shopify_user_errors else ''),
        })

        if publish_bulk_record or metafield_bulk_record:
            time.sleep(3)
            self.process_shopify_bulk_query(mk_instance_id, pending_records=publish_bulk_record | metafield_bulk_record)
        return True

    def process_shopify_bulk_export_results_cron(self, mk_instance_id):
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state == 'confirmed':
            self.process_shopify_bulk_export_result(mk_instance_id)
        return True

    def process_shopify_bulk_query_status_cron(self, mk_instance_id=None):
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state == 'confirmed':
            self.process_shopify_bulk_query(mk_instance_id, pending_records=None)
            # Task: T7609 - Poll first, then fill the slots that just freed up with the queued payload files
            # of a split request.
            self.start_shopify_queued_bulk_operations(mk_instance_id)
        return True

    def action_fetch_shopify_bulk_query_status(self):
        """
        Task: T7568 - Manual button: poll the Shopify status of this bulk operation.
        The retry count is NOT touched, because the user asked for it, it is not a cron attempt.
        Returns:
            bool: Always True.
        """
        for record in self:
            mk_instance_id = record.mk_instance_id
            if not mk_instance_id:
                raise MarketplaceException(_("No instance is set on this bulk operation."))
            mk_instance_id.connection_to_shopify()
            self.process_shopify_bulk_query(mk_instance_id, pending_records=record, skip_retry_count=True)
        return True

    def action_process_shopify_bulk_export_result(self):
        """
        Task: T7568 - Manual button: apply the Shopify bulk export/update result of this record.
        Returns:
            bool: Always True.
        """
        for record in self:
            mk_instance_id = record.mk_instance_id
            if not mk_instance_id:
                raise MarketplaceException(_("No instance is set on this bulk operation."))
            if not record.result_url and not record.result_attachment_id:
                raise MarketplaceException(_("The result of this bulk operation is not available yet. Fetch the status first."))
            record._apply_shopify_bulk_export_result()
        return True

    def process_shopify_bulk_query(self, mk_instance_id, pending_records=None, skip_retry_count=False):
        """
        Task: T7568 - Cron Job: Poll pending Shopify bulk operations and process completed ones.
        Max 3 retries in a single cron run — unlink if URL not available after 3 attempts.
        When ``pending_records`` is provided, only those records are processed.
        When ``mk_instance_id`` is provided (per-instance cron), only that instance's records are processed.
        When ``skip_retry_count`` is True (manual poll from the form button), the retry count is left untouched.
        """
        if pending_records is None:
            domain = [('status', 'in', ['RUNNING', 'CANCELING']), '|', ('no_of_retry_count', '<', 3), ('no_of_retry_count', '=', False)]
            if mk_instance_id:
                domain.append(('mk_instance_id', '=', mk_instance_id if isinstance(mk_instance_id, int) else mk_instance_id.id))
            pending_records = self.search(domain)
        for record in pending_records:
            try:
                mk_instance_id = record.mk_instance_id
                if not mk_instance_id:
                    _logger.warning(f"No marketplace instance found for bulk operation {record.bulk_operation_id}, skipping.")
                    continue
                mk_instance_id.connection_to_shopify()
                if not skip_retry_count:
                    attempt = record.no_of_retry_count or 0
                    increment_attempt = attempt + 1
                    record.write({'no_of_retry_count': increment_attempt})
                    _logger.info(f"Attempt {increment_attempt}/{MAX_RETRIES} for bulk operation {record.bulk_operation_id}")

                variable = {"id": f"gid://shopify/BulkOperation/{record.bulk_operation_id}"}
                poll_res = mk_instance_id.execute_graphql_query(GET_BULK_OPERATION_BY_ID, variable)
                current_data = poll_res and poll_res.get('data', {}) and poll_res.get('data', {}).get('node', {})
                error_code = current_data and current_data.get('errorCode', None)
                poll_status = current_data and current_data.get('status', '')
                _logger.info(f"Bulk operation {record.bulk_operation_id} status: {poll_status}")

                if poll_status == 'COMPLETED':
                    result_url = current_data.get('url', '')
                    if result_url:
                        record.write({'status': 'COMPLETED'})
                        shopify_operation_type = record.shopify_operation_type
                        # Task: T7609 - Download the result once into an attachment; the batch cron applies it in chunks.
                        if shopify_operation_type in ('export_listing', 'update_listing'):
                            record._store_shopify_bulk_result(result_url)
                        continue
                    if not result_url:
                        message = "Bulk operation completed but no result URL returned."
                        _logger.warning(message)
                        record.write({'status': poll_status, 'message': message})
                        continue
                elif poll_status in ['FAILED', 'CANCELED']:
                    message = f"Bulk operation {record.bulk_operation_id} terminal status: {poll_status}."
                    _logger.error(message)
                    record.write({'status': poll_status, 'message': message})
                    break
                if error_code:
                    message = error_code
                    record.write({'status': poll_status, 'message': message})
            except Exception as e:
                _logger.error(f"Error processing bulk operation {record.bulk_operation_id}: {str(e)}")
                continue

    def process_shopify_bulk_export_result(self, mk_instance_id):
        """
        Task: T7609 - Cron entry: walk completed export/update bulk records and apply each in
        time-budgeted, resumable chunks.
        When ``mk_instance_id`` is provided (per-instance cron), only that instance's records are processed.
        Returns:
            bool: Always True (cron contract).
        """
        domain = [('shopify_operation_type', 'in', ('export_listing', 'update_listing')), ('status', '=', 'COMPLETED'), ('result_url', '!=', False), ]

        if mk_instance_id:
            domain.append(('mk_instance_id', '=', mk_instance_id if isinstance(mk_instance_id, int) else mk_instance_id.id))
        shopify_bulk_query_ids = self.search(domain, order='id asc')
        for record in shopify_bulk_query_ids:
            # Capture the id up front: the publish step can cascade-delete the record (mk_log_id is ondelete='cascade'), and reading a field on a deleted record raises MissingError.
            bulk_operation_id = record.bulk_operation_id
            if not record.mk_instance_id:
                _logger.warning(f"Bulk export result: no instance for bulk {bulk_operation_id}, skipping.")
                continue
            try:
                record._apply_shopify_bulk_export_result()
            except Exception as e:
                self.env.cr.rollback()
                _logger.error(f"Bulk export result error for bulk {bulk_operation_id}: {e}")
        return True

    def _apply_shopify_bulk_export_result(self):
        """
        Task: T7609 - Apply one bulk result to Odoo. Publish phase runs in one shot;
        export/update phase processes 80 products per commit with a 10-min wall budget, resuming
        on the next cron tick, and triggers the follow-up publish step when fully applied.

        Media, matching and ORM-cache warming are scoped to the current 80-product offset window.
        Within each window the per-product apply is fanned out across a bounded ThreadPoolExecutor,
        where EACH task runs in its OWN cursor/Environment - the only thread-safe way to write through
        the ORM, so parallel listings never share cursor state and cannot raise "concurrent update".
        Returns:
            None
        """
        self.ensure_one()

        mk_listing_obj = self.env['mk.listing']
        mk_instance_id = self.mk_instance_id
        mk_instance_id.connection_to_shopify()
        payload = mk_listing_obj.export_shopify_pending_payload(self)

        # Publish result (its own record) - light, no batching. The whole process ends here, so notify.
        if payload.get('phase') == 'publish':
            mk_listing_obj._process_shopify_bulk_publish_result(self, mk_instance_id, self.result_url)
            self._cleanup_shopify_bulk_result()
            self.env.cr.commit()
            self._notify_shopify_bulk_done()
            return

        # Task: T7609 - Metafield delete result (its own record) - light, no batching. Notify only when no
        # publish record was chained too, otherwise the publish step is the end of the whole process.
        if payload.get('phase') == 'metafield_delete':
            mk_listing_obj._process_shopify_bulk_metafield_delete_result(self, mk_instance_id, self.result_url)
            self._cleanup_shopify_bulk_result()
            self.env.cr.commit()
            if not payload.get('has_publish_step'):
                self._notify_shopify_bulk_done()
            return

        raw_lines = self._read_shopify_bulk_result_lines()
        if raw_lines is None:
            return
        operation_type = payload and payload.get('mode', 'export')
        # Task: T7609 - Stream the JSONL once, keeping only lightweight aggregates (valid-line indices,
        # update-mode returned ids, access-scope errors) instead of every parsed product dict. The
        # window loop below re-parses only its own 80-line slice on demand, so peak memory stays
        # bounded to one window instead of the whole result (which hit the server memory limit and
        # forced a cron reload).
        valid_line_indices, returned_ids, access_error_list = [], set(), []
        for line_index, raw_line in enumerate(raw_lines):
            product, errors = mk_listing_obj.prepare_shopify_response_for_the_jsonl_file(raw_line)
            if errors:
                access_error_list.extend(errors)
            if not product:
                continue
            valid_line_indices.append(line_index)
            if operation_type == 'update' and product.get('id'):
                returned_ids.add(str(extract_numeric_id(product.get('id'))))
        total_product_of_response = len(valid_line_indices)
        listing_ids = mk_listing_obj.browse(payload.get('listing_ids', [])).exists()
        is_set_images = payload.get('is_set_images', False)
        sku_to_listing = {sku: int(lid) for lid, sku in payload.get('listing_sku_map', {}).items() if sku}
        barcode_to_listing = {bc: int(lid) for lid, bc in payload.get('listing_barcode_map', {}).items() if bc}
        mk_id_to_listing = {str(l.mk_id): l for l in listing_ids if l.mk_id}
        mk_log_id = self.mk_log_id or self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='export')
        if not self.mk_log_id:
            self.mk_log_id = mk_log_id

        # Task: T7609 - Access scope errors are instance-level, not per-product: log ONE line and STOP here.
        # Skip the apply loop, the update-mode missing-product unlink and the publish step - products came back empty because of the scope error, NOT because they were deleted on Shopify.
        # Cleanup clears result_url so this record leaves the cron domain and is not re-processed forever.
        access_denied_message = self._get_shopify_bulk_access_denied_message(access_error_list)
        if access_denied_message:
            self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': access_denied_message}], 'success': []})
            self.write({'message': access_denied_message})
            self._cleanup_shopify_bulk_result()
            self.env.cr.commit()
            self._notify_shopify_bulk_done()
            return

        # Threaded apply setup (once). Each worker opens its OWN cursor from this registry; bounded to
        # keep DB connections + lock contention in check (check the cron worker's db_maxconn).
        db_registry = self.env.registry
        worker_uid, worker_ctx = self.env.uid, dict(self.env.context)
        MAX_APPLY_WORKERS = min(4, (os.cpu_count() or 2))

        start, offset = time.time(), self.batch_offset
        while offset < total_product_of_response and time.time() - start < 600:
            mk_log_line_dict = {'error': [], 'success': []}

            # ---- PARENT cursor only: match this window, warm cache, fetch media once. For export set
            # mk_id here so the media fetch can resolve the Shopify product. ----
            batch_pairs, batch_listings = [], mk_listing_obj
            for line_index in valid_line_indices[offset:offset + 80]:
                product_dict, _errors = mk_listing_obj.prepare_shopify_response_for_the_jsonl_file(raw_lines[line_index])
                if not product_dict:
                    continue
                listing_id = mk_listing_obj.match_shopify_listing_from_bulk_result(product_dict, operation_type, listing_ids, sku_to_listing, barcode_to_listing, mk_instance_id.sync_product_with, mk_id_to_listing)
                if not listing_id:
                    continue
                if operation_type == 'export' and not listing_id.mk_id and product_dict.get('id'):
                    listing_id.mk_id = str(extract_numeric_id(product_dict.get('id')))
                    mk_id_to_listing[str(listing_id.mk_id)] = listing_id
                batch_pairs.append((listing_id, product_dict))
                batch_listings |= listing_id

            # Warm the ORM cache for THIS window only (~80 listings).
            batch_listings.mapped('listing_item_ids.mk_id')
            batch_listings.mapped('image_ids.media_id')

            # Fetch post-bulk media for the WHOLE offset window in ONE batched GraphQL call.
            media_cache = {}
            if is_set_images:
                media_listings = batch_listings.filtered('mk_id')
                if media_listings:
                    # Media fetch failure (e.g. missing read_products scope) is instance-level:
                    # log ONE line, stop image sync for the rest of the run, keep applying product data.
                    try:
                        media_cache = media_listings._fetch_shopify_product_media_batch()
                    except MarketplaceException as e:
                        is_set_images = False
                        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict={'error': [{'log_message': f"BULK {operation_type.upper()} LISTING: Image sync skipped for all listings - {e}"}], 'success': []})

            # ---- Build PLAIN tasks (ids + dicts only). Do the "unchanged product" skip HERE so workers
            # only do real work. No recordset ever crosses the thread boundary. ----
            tasks = []
            for listing_id, product_dict in batch_pairs:
                shop_upd = convert_shopify_datetime_to_utc(product_dict.get('updatedAt', ""))
                if operation_type == 'update' and shop_upd and listing_id.listing_update_date == shop_upd:
                    continue
                tasks.append((listing_id.id, product_dict))

            # Persist the parent's in-flight writes (e.g. the export mk_id set above) so the worker
            # transactions - separate cursors, READ COMMITTED - can actually see them.
            self.env.cr.commit()

            def _apply_one(task, _media_cache=media_cache, _is_set_images=is_set_images):
                """Apply ONE product in its own cursor/env. Retries transient serialization / deadlock /
                unique-violation (two workers creating the same sales channel) with backoff."""
                listing_db_id, product = task
                for attempt in range(1, 4):
                    try:
                        with db_registry.cursor() as cr:
                            env = api.Environment(cr, worker_uid, worker_ctx)
                            listing = env['mk.listing'].browse(listing_db_id)
                            if not listing.exists():
                                return {'error': [], 'success': []}
                            local_log = {'error': [], 'success': []}
                            env['mk.listing'].apply_shopify_bulk_export_result_to_listing(listing, product, _is_set_images, operation_type, local_log, media_cache=_media_cache)
                            cr.commit()
                            return local_log
                    except psycopg2.Error as e:
                        _logger.warning("BULK %s LISTING: apply retry %s/3 for listing %s: %s", operation_type.upper(), attempt, listing_db_id, e)
                        time.sleep(0.4 * attempt)
                return {'error': [{'log_message': f"BULK {operation_type.upper()} LISTING: apply failed after retries for listing id {listing_db_id}"}], 'success': []}

            if tasks:
                with ThreadPoolExecutor(max_workers=MAX_APPLY_WORKERS) as executor:
                    for local_log in executor.map(_apply_one, tasks):  # map preserves order
                        mk_log_line_dict['error'].extend(local_log.get('error', []))
                        mk_log_line_dict['success'].extend(local_log.get('success', []))

            # Workers committed in other cursors; refresh the parent env so it (and the end-of-run missing-unlink below) sees their data.
            self.env.invalidate_all()

            # Append lines directly (never route through _handle_shopify_log_creation, which unlinks
            # an empty log and would drop this run's log lines).
            mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=mk_log_line_dict)
            offset += 80
            self.write({'batch_offset': offset})
            self.env.cr.commit()
            # Task: T7609 - Drop the window's ORM record cache after each commit so it does not keep
            # growing across all windows (the accumulating cache pushed the cron over the memory limit).
            self.env.invalidate_all()

        if offset >= total_product_of_response:
            # Update mode: any listing whose Shopify product did not come back in the result no longer
            # exists on Shopify (deleted there) - remove it from Odoo and log it.
            if operation_type == 'update':
                # Task: T7433 - Exclude skipped_ids (Skip Listing Sync / missing SKU-barcode): never in the JSONL,
                # so their absence does NOT mean they were deleted on Shopify - never unlink them.
                skipped_ids = set(payload.get('skipped_ids') or [])
                missing_listing_ids = listing_ids.filtered(lambda l: l.mk_id and l.mk_id not in returned_ids and l.id not in skipped_ids)
                if missing_listing_ids:
                    miss_dict = {'error': [{'log_message': f"BULK UPDATE LISTING: Product '{l.name}' ({l.mk_id}) was deleted from Odoo along with its variants, because it was deleted in Shopify."} for l in missing_listing_ids], 'success': []}
                    mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, mk_log_line_dict=miss_dict)
                    missing_listing_ids.sudo().unlink()
                    listing_ids = listing_ids.exists()

            # All products applied -> trigger publish as its own record (poll cron will store its url).
            sales_channel_ids = payload.get('shopify_sales_channel_ids', [])
            is_publish_or_unpublish = payload.get('is_publish_or_unpublish', True) if operation_type == 'update' else True
            # Task: T7609 - Single-file request keeps the exact same path as before. A split payload only
            # chains the follow-up steps from the file that finishes last, for the whole group.
            chain_listings = listing_ids
            if self.chunk_total > 1:
                chain_listings = self._shopify_bulk_group_listing_ids() if self._is_last_shopify_bulk_chunk() else mk_listing_obj

            publish_record = mk_listing_obj.trigger_shopify_bulk_publish_after_export(
                chain_listings, is_publish_or_unpublish, sales_channel_ids, mk_instance_id, mk_log_id if mk_log_id.exists() else self.env['mk.log'])
            metafield_record = mk_listing_obj.trigger_shopify_bulk_metafield_delete_after_export(
                chain_listings, mk_instance_id, mk_log_id if mk_log_id.exists() else self.env['mk.log'], operation_type, has_publish_step=bool(publish_record))
            self._cleanup_shopify_bulk_result()
            self.env.cr.commit()
            # A slot just freed up: start the next queued file of this (or any) request right away instead
            # of waiting for the next poll cron tick.
            self.start_shopify_queued_bulk_operations(mk_instance_id)
            if not publish_record and not metafield_record and self._is_last_shopify_bulk_chunk():  # end of the whole process
                self._notify_shopify_bulk_done()
        return True

    def _notify_shopify_bulk_done(self):
        """
        Task: T7609 - Send a `marketplace_notification` bus message to the user who started the
        bulk operation, with a link to the related mk.log.
        Returns:
            None
        """
        self.ensure_one()
        message = 'Your Shopify listing process has completed.'
        if self.mk_log_id and self.mk_log_id.exists() and self.mk_log_id.log_line_ids:
            message += (
                f'<br/>Please check the log <b><a href="/web#id={self.mk_log_id.id}&model=mk.log&view_type=form">'
                f'{self.mk_log_id.name}</a></b> for details.'
            )
        elif self.mk_log_id.exists() and not self.mk_log_id.log_line_ids:
            self.mk_log_id.unlink()
        self.env['bus.bus']._sendone(self.create_uid.partner_id, 'marketplace_notification', {
            'title': 'Update Completed',
            'message': message,
            'message_is_html': True,
            'type': 'success',
            'sticky': False,
        })

    def _store_shopify_bulk_result(self, result_url):
        """
        Task: T7609 - Download the Shopify bulk result JSONL once and store it as an attachment on
        the record so later URL expiry can't break processing.
        Args:
            result_url (str): Shopify bulk result file URL.
        Returns:
            None
        """
        self.ensure_one()
        vals = {'result_url': result_url}
        try:
            response = requests.get(result_url, timeout=300)
            response.raise_for_status()
            attachment_id = self.env['ir.attachment'].create({
                'name': f"shopify_bulk_result_{self.bulk_operation_id}.jsonl",
                'type': 'binary',
                'raw': response.content,
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/jsonl',
            })
            vals['result_attachment_id'] = attachment_id.id
        except Exception as e:
            _logger.error(f"Bulk result download failed for {self.bulk_operation_id}: {e}")
        self.write(vals)

    def _read_shopify_bulk_result_lines(self):
        """
        Task: T7609 - Read the stored bulk result attachment and return its non-empty JSONL lines;
        falls back to a fresh URL download if the attachment is missing.
        Returns:
            list[bytes] | None: JSONL lines, or None when the URL fallback fails.
        """
        self.ensure_one()
        if self.result_attachment_id:
            content = self.result_attachment_id.raw or b''
            return [line for line in content.splitlines() if line]
        return self.env['mk.listing'].get_shopify_bulk_result_of_jsonl(self.result_url, self, 'BULK LISTING')

    def _cleanup_shopify_bulk_result(self):
        """
        Task: T7609 - Clear `result_url` and delete the stored bulk result attachment after the
        whole process for this record is complete.
        Returns:
            None
        """
        self.ensure_one()
        # Task: T7609 - Drop the payload file too: it only survives here when the operation never started
        # (failed request), and it must not stay behind in the filestore.
        attachments = self.result_attachment_id | self.jsonl_attachment_id
        self.write({'result_url': False, 'result_attachment_id': False, 'jsonl_attachment_id': False})
        if attachments:
            attachments.unlink()
