import pprint

from odoo.tools.safe_eval import safe_eval
from psycopg2 import OperationalError

from odoo import models, fields, _
from odoo.addons.shopify.models.graphql_queries import GET_ORDERS_BY_ID, GET_CUSTOMERS, GET_SPECIFIC_PRODUCT_DATA
from odoo.addons.shopify.models.misc import extract_numeric_id
from odoo.addons.shopify.models.misc import log_traceback_for_exception


class MkQueueJob(models.Model):
    _inherit = "mk.queue.job"

    def validate_api_graphql_data(self, line, import_data):
        type = self.type
        if type == 'customer' and any(key in import_data for key in ['default_address', 'first_name', 'last_name']):
            log_message = _("PROCESS CUSTOMER: Old data format detected. This queue line uses the deprecated REST API. The connector now uses GraphQL. Marked as 'failed' — please  🔁 Retry Failed Lines.")
            self.env['mk.log'].create_update_log(mk_log_id=line.queue_id.mk_log_id, mk_instance_id=self.mk_instance_id,
                                                 mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': line and line.id or False}]})
            line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
            return False

        return True

    def shopify_customer_queue_process(self, draft_queue_line_id=None):
        res_partner_obj = self.env['res.partner']
        draft_queue_line_ids = draft_queue_line_id if draft_queue_line_id else self.mk_queue_line_ids.filtered(lambda x: x.state in ['draft', 'failed'])
        for line in draft_queue_line_ids:
            customer_name = ''
            try:
                customer_dict = safe_eval(line.data_to_process)
                customer_name = customer_dict.get('name')
                if not self.validate_api_graphql_data(line, customer_dict):
                    continue
                with self.env.cr.savepoint():
                    # Task: T7450 - Fix the parent customer issue from Shopify queue job.
                    partner_id = res_partner_obj.with_context(queue_line_id=line, mk_log_id=line.queue_id.mk_log_id).import_shopify_customer_records(customer_dict, self.mk_instance_id)
                if partner_id:
                    line.write({'state': 'processed', 'processed_date': fields.Datetime.now()})
                else:
                    line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})

            except OperationalError:
                self.env.cr.rollback()
            except Exception as e:
                log_traceback_for_exception()
                self.env.cr.rollback()
                log_message = f"PROCESS CUSTOMER: Error while processing Marketplace Customer {customer_name}, ERROR: {e}"
                self.env['mk.log'].create_update_log(mk_log_id=line.queue_id.mk_log_id, mk_instance_id=self.mk_instance_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': line and line.id or False}]})
                line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
            self.env.cr.commit()

        return True

    def shopify_order_queue_process(self, skip_api_call=None, draft_queue_line_id=None):
        sale_order_obj, mk_instance_id, shopify_location_obj = self.env['sale.order'], self.mk_instance_id, self.env['shopify.location.ts']
        draft_queue_line_ids = draft_queue_line_id if draft_queue_line_id else self.mk_queue_line_ids.filtered(lambda x: x.state in ['draft', 'failed'])
        if not skip_api_call:
            shopify_location_obj.import_location_from_shopify(mk_instance_id)
        for line in draft_queue_line_ids:
            order_name = ''
            try:
                shopify_order_dict = safe_eval(line.data_to_process)
                order_name = shopify_order_dict.get('name')
                with self.env.cr.savepoint():
                    order_id = sale_order_obj.with_context(queue_line_id=line, skip_queue_change_state=True, skip_inventory_sync_commit=True, mk_log_id=line.queue_id.mk_log_id).process_import_order_from_shopify_ts(shopify_order_dict, mk_instance_id)
                if order_id:
                    line.write({'state': 'processed', 'processed_date': fields.Datetime.now(), 'order_id': order_id.id if order_id and not isinstance(order_id, bool) else False})
                else:
                    line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
            except OperationalError:
                self.env.cr.rollback()
            except Exception as e:
                log_traceback_for_exception()
                self.env.cr.rollback()
                log_message = f"PROCESS ORDER: Error while processing Marketplace Order {order_name}, ERROR: {e}"
                self.env['mk.log'].create_update_log(mk_log_id=line.queue_id.mk_log_id, mk_instance_id=mk_instance_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': line and line.id or False}]})
                line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
            self.env.cr.commit()
        if not self.env.context.get('hide_notification', False):
            error_count = self.env['mk.queue.job.line'].search_count([('state', '=', 'failed'), ('id', 'in', draft_queue_line_ids.ids)])
            success_count = self.env['mk.queue.job.line'].search_count([('state', '=', 'processed'), ('id', 'in', draft_queue_line_ids.ids)])
            mk_instance_id.send_smart_notification('is_order_create', 'error', error_count)
            mk_instance_id.send_smart_notification('is_order_create', 'success', success_count)
            if error_count:
                self.create_activity_action("Please check queue job for its fail reason.")

    def shopify_product_queue_process(self, draft_queue_line_id=None):
        """
        Task: T5986 - Populate New Sales Channel Field for Existing Entries
        Raise a validation error when, after migration, the user first tries to update listings without assigning sales channels to all listings.
        """
        mk_instance_id, listing_obj = self.mk_instance_id, self.env['mk.listing']
        if mk_instance_id.need_sync_shopify_sales_channels:
            listing_obj.show_shopify_sales_channel_action_required_warning(self.mk_instance_id)
        draft_queue_line_ids = draft_queue_line_id if draft_queue_line_id else self.mk_queue_line_ids.filtered(lambda x: x.state in ['draft', 'failed'])
        for line in draft_queue_line_ids:
            product_name = ''
            try:
                shopify_product_dict = safe_eval(line.data_to_process)
                product_name = shopify_product_dict.get('title', '')
                mk_id = shopify_product_dict.get('id', '') if shopify_product_dict else False
                product_id = extract_numeric_id(mk_id)
                mk_listing_id = self.env['mk.listing'].search([('mk_instance_id', '=', mk_instance_id.id), ('mk_id', '=', line.mk_id)])
                # Task: T7433 - Implemented import/export control using the ‘Allow Sync’ flag available in the listing  form view, supporting all flows to skip listings during synchronization between Odoo and Shopify.
                if mk_listing_id.skip_listing_sync:
                    log_message = _("IMPORT LISTING: Skipped listing %s(%s) Sync is disabled.") % (product_name, product_id)
                    self.env['mk.log'].create_update_log(mk_log_id=line.queue_id.mk_log_id, mk_instance_id=mk_instance_id,
                                                         mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': line and line.id or False}]})
                    line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
                    continue
                is_update_existing_products = True if not mk_listing_id else line.queue_id.update_existing_product
                update_product_price = True if not mk_listing_id else line.queue_id.update_product_price
                with self.env.cr.savepoint():
                    mk_listing_id = listing_obj.with_context(queue_line_id=line, mk_log_id=line.queue_id.mk_log_id).create_update_shopify_product(shopify_product_dict, mk_instance_id, update_product_price=update_product_price, is_update_existing_products=is_update_existing_products)
                if mk_listing_id:
                    line.write({'state': 'processed', 'processed_date': fields.Datetime.now(), 'mk_listing_id': mk_listing_id.id if mk_listing_id and not isinstance(mk_listing_id, bool) else False})
                else:
                    line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
            except OperationalError:
                self.env.cr.rollback()
            except Exception as e:
                log_traceback_for_exception()
                self.env.cr.rollback()
                log_message = f"PROCESS LISTING: Error while processing Marketplace Listing {product_name}, ERROR: {e}"
                self.env['mk.log'].create_update_log(mk_log_id=line.queue_id.mk_log_id, mk_instance_id=mk_instance_id,
                                                     mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': line and line.id or False}]})
                line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})

            self.env.cr.commit()
        if not self.env.context.get('hide_notification', False):
            success_count = self.env['mk.queue.job.line'].search_count([('state', '=', 'processed'), ('id', 'in', draft_queue_line_ids.ids)])
            error_count = self.env['mk.queue.job.line'].search_count([('state', '=', 'failed'), ('id', 'in', draft_queue_line_ids.ids)])
            mk_instance_id.send_smart_notification('is_product_import', 'error', error_count)
            mk_instance_id.send_smart_notification('is_product_import', 'success', success_count)

    def shopify_product_retry_failed_queue(self):
        failed_queue_line_ids = self.mk_queue_line_ids.filtered(lambda ql: ql.state == 'failed')
        failed_queue_line_ids and failed_queue_line_ids.shopify_product_retry_failed_queue()
        return True

    def shopify_order_retry_failed_queue(self):
        failed_queue_line_ids = self.mk_queue_line_ids.filtered(lambda ql: ql.state == 'failed')
        failed_queue_line_ids and failed_queue_line_ids.shopify_order_retry_failed_queue()
        return True

    def shopify_customer_retry_failed_queue(self):
        failed_queue_line_ids = self.mk_queue_line_ids.filtered(lambda ql: ql.state == 'failed')
        failed_queue_line_ids and failed_queue_line_ids.shopify_customer_retry_failed_queue()
        return True

    def shopify_return_queue_process(self, draft_queue_line_id=None):
        """Process queue lines of type='return'.

        Delegates per-line work to ``shopify.return.ts.process_shopify_return_queue_line``
        which fetches details from Shopify, upserts header/lines, and runs
        the lifecycle side effects (create/validate/cancel pickings).
        """
        return_obj = self.env['shopify.return.ts']
        mk_instance_id = self.mk_instance_id
        draft_queue_line_ids = draft_queue_line_id if draft_queue_line_id else self.mk_queue_line_ids.filtered(lambda x: x.state in ['draft', 'failed'])
        for line in draft_queue_line_ids:
            try:
                with self.env.cr.savepoint():
                    result = return_obj.with_context(skip_inventory_sync_commit=True).process_shopify_return_queue_line(line)
                if result:
                    line.write({'state': 'processed', 'processed_date': fields.Datetime.now()})
                else:
                    line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
            except OperationalError:
                self.env.cr.rollback()
            except Exception as e:
                log_traceback_for_exception()
                self.env.cr.rollback()
                log_message = f"PROCESS RETURN: Error while processing Shopify Return, ERROR: {e}"
                self.env['mk.log'].create_update_log(
                    mk_log_id=line.queue_id.mk_log_id, mk_instance_id=mk_instance_id,
                    mk_log_line_dict={'error': [{'log_message': log_message, 'queue_job_line_id': line and line.id or False}]},
                )
                line.write({'state': 'failed', 'processed_date': fields.Datetime.now()})
            self.env.cr.commit()
        return True

    def shopify_return_retry_failed_queue(self):
        failed_queue_line_ids = self.mk_queue_line_ids.filtered(lambda ql: ql.state == 'failed')
        failed_queue_line_ids and failed_queue_line_ids.shopify_return_retry_failed_queue()
        return True


class MkQueueJobLine(models.Model):
    _inherit = "mk.queue.job.line"

    def shopify_product_retry_failed_queue(self):
        """
        Task: T5836 - Migrate Shopify to v19
        Migrated from Shopify REST API to GraphQL API.
        """
        queue_id = self.mapped('queue_id')
        queue_id.mk_instance_id.connection_to_shopify()
        for line in self.filtered(lambda x: x.mk_id):
            variables = {"productId": f"gid://shopify/Product/{line.mk_id}"}
            product_res = queue_id.mk_instance_id.execute_graphql_query(GET_SPECIFIC_PRODUCT_DATA, variables)
            shopify_product_dict = product_res.get('data', {}).get('product', {}) if isinstance(product_res, dict) else {}
            line.write({'state': 'draft', 'data_to_process': pprint.pformat(shopify_product_dict)})
            line.queue_id.with_context(hide_notification=True).shopify_product_queue_process(draft_queue_line_id=line)
        return True

    def shopify_order_retry_failed_queue(self):
        queue_id = self.mapped('queue_id')
        queue_id.mk_instance_id.connection_to_shopify()
        for line in self.filtered(lambda x: x.mk_id):
            variables = {"orderId": f"gid://shopify/Order/{line.mk_id}"}
            res = queue_id.mk_instance_id.execute_graphql_query(GET_ORDERS_BY_ID, variables)
            order_vals = res.get('data', {}).get('order', {}) if isinstance(res, dict) else {}
            line.write({'state': 'draft', 'data_to_process': pprint.pformat(order_vals)})
            line.queue_id.with_context(hide_notification=True).shopify_order_queue_process(skip_api_call=True, draft_queue_line_id=line)
        return True

    def shopify_customer_retry_failed_queue(self):
        queue_id = self.mapped('queue_id')
        queue_id.mk_instance_id.connection_to_shopify()
        for line in self.filtered(lambda x: x.mk_id):
            variables = {"customerID": f"gid://shopify/Customer/{line.mk_id}"}
            res = self.queue_id.mk_instance_id.execute_graphql_query(GET_CUSTOMERS, variables)
            customers = res.get('data', {}).get('customer', {}) if isinstance(res, dict) else {}
            line.write({'state': 'draft', 'data_to_process': pprint.pformat(customers)})
            line.queue_id.with_context(hide_notification=True).shopify_customer_queue_process(draft_queue_line_id=line)
        return True

    def shopify_return_retry_failed_queue(self):
        """Retry failed return queue lines.

        ``process_shopify_return_queue_line`` always re-fetches details from Shopify
        via ``_fetch_shopify_return_details`` so we only need to flip state back to
        draft and reprocess — no need to pre-bake the payload like other
        queue types do.
        """
        for line in self.filtered(lambda x: x.mk_id):
            line.write({'state': 'draft'})
            line.queue_id.with_context(hide_notification=True).shopify_return_queue_process(draft_queue_line_id=line)
        return True
