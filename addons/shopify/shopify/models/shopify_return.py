import ast
import logging
import pprint

from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException
from odoo.addons.shopify.models.graphql_queries import (
    LIST_ORDER_RETURNS_BY_DATE,
    GET_SHOPIFY_RETURN_DETAILS,
    RETURN_REQUEST_APPROVE_FROM_ODOO,
    RETURN_REQUEST_DECLINE_FROM_ODOO,
    RETURN_PROCESS_FROM_ODOO,
    RETURN_CLOSE_FROM_ODOO,
    RETURN_CANCEL_FROM_ODOO,
    FETCH_MULTIPLE_RETURN_DETAILS,
)
from odoo.addons.shopify.models.misc import extract_numeric_id, log_traceback_for_exception

_logger = logging.getLogger("Qamah:Shopify")

RETURN_STATUS = [
    ('REQUESTED', 'Requested'),
    ('OPEN', 'Open'),
    ('CLOSED', 'Closed'),
    ('DECLINED', 'Declined'),
    ('CANCELED', 'Canceled'),
]

# Terminal statuses where we should not retry side effects.
SHOPIFY_TERMINAL_RETURN_STATUSES = {'CANCELED'}
SHOPIFY_RETURN_FETCH_CHUNK_SIZE = 100
SHOPIFY_RETURN_STATUSES_SAFE_FROM_ORDER_PAYLOAD = {'REQUESTED', 'OPEN', 'CLOSED', 'DECLINED', 'CANCELED'}
# Identifies incomplete return payloads extracted during order import. Prevents partial order data from overwriting fully fetched return records.
SHOPIFY_PARTIAL_RETURN_PAYLOAD_KEY = 'extracted_from_order_payload'
SHOPIFY_RETURN_PAYLOAD_KEYS_TO_PRESERVE = ('refunds',)
SHOPIFY_RETURN_STATUS_SEARCH_GROUP = ("(return_status:RETURN_REQUESTED OR return_status:IN_PROGRESS OR return_status:RETURNED OR return_status:RETURN_FAILED)")

class ShopifyReturn(models.Model):
    _name = "shopify.return.ts"
    _description = "Shopify Return"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _order = "id desc"

    name = fields.Char("Return Name", copy=False, tracking=True, help="Name of the Shopify return.")
    shopify_return_id = fields.Char("Shopify Return ID", copy=False, index=True, tracking=True,
                                    help="Numeric Shopify return identifier (extracted from the return GID).")
    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade', required=True, copy=False, help="Shopify instance linked with this return.")
    company_id = fields.Many2one('res.company', related='mk_instance_id.company_id', store=True)
    sale_order_id = fields.Many2one('sale.order', "Sale Order", copy=False, ondelete='set null', tracking=True, help="Sale order linked with this return.")
    status = fields.Selection(RETURN_STATUS, "Return Status", copy=False, tracking=True, default='REQUESTED', help="Current status of the return.")
    total_quantity = fields.Integer("Total Quantity", copy=False, default=0, help="Total quantity of items included in this return.")
    decline_reason = fields.Char("Decline Reason", copy=False, help="Reason why the return request was declined.")
    decline_note = fields.Text("Decline Note", copy=False, help="Additional note added while declining the return.")
    return_line_ids = fields.One2many('shopify.return.line.ts', 'return_id', string="Return Lines", copy=False, help="Return line items included in this Shopify return.")
    picking_ids = fields.One2many('stock.picking', 'shopify_return_id', string="Return Pickings",
                                  help="Incoming pickings created from this Shopify return.")
    picking_count = fields.Integer(compute='_compute_picking_count', help="Number of return pickings linked with this return.")
    credit_note_ids = fields.One2many('account.move', 'shopify_return_id', string="Linked Credit Notes", help="Credit notes linked with this Shopify return.")
    credit_note_count = fields.Integer(compute='_compute_credit_note_count', help="Number of credit notes linked with this return.")
    shopify_payload_json = fields.Text("Raw Payload", copy=False, help="The raw GraphQL payload from Shopify, kept for audit.")
    last_imported_at = fields.Datetime("Last Imported At", copy=False, help="Date and time when this return was last imported from Shopify.")
    is_restock_skipped_in_shopify = fields.Boolean("Restock Skipped on Shopify", copy=False, default=False,
                                                   compute='_compute_is_restock_skipped_in_shopify', store=True,
                                                   help="Set to True when the return is Closed and Shopify did not mark it as Restocked.")
    return_move_ids = fields.One2many('stock.move', 'shopify_return_id', string="Return Moves",
                                      help="Reverse stock moves created for this Shopify return on orders with no return picking (fulfilled-shortcut case).")
    return_move_count = fields.Integer(compute='_compute_return_move_count', help="Number of stock return moves linked with this return.")
    restock_shopify_location_id = fields.Many2one('shopify.location.ts', "Restock Location", copy=False, ondelete='set null', tracking=True,
                                                  domain="[('mk_instance_id', '=', mk_instance_id), ('shopify_location_id', '!=', False)]",
                                                  help="Select the Shopify location where returned items will be restocked. When the return is processed in Odoo, items are marked as restocked at this location in Shopify.")

    _check_unique_shopify_return = models.Constraint(
        "UNIQUE (shopify_return_id, mk_instance_id)",
        "A Shopify return with this ID already exists for this instance.",
    )

    # ------------------------------------------------------------------
    # ORM hooks — propagate side effects on every status transition
    # ------------------------------------------------------------------

    def write(self, vals):
        """
        Trigger ``_apply_shopify_return_status_side_effects`` whenever ``status`` changes. Centralizes the side-effect dispatch so manual button actions
        (close / decline / cancel / process) and queue-driven imports all run the same lifecycle hooks (create picking on OPEN, validate on CLOSED, cancel
        on DECLINED/CANCELED).
        Args:
            vals (dict): values being written.
        Returns:
            bool: result of the parent write.
        """
        if 'status' not in vals:
            return super(ShopifyReturn, self).write(vals)
        before = {record.id: record.status for record in self}
        res = super(ShopifyReturn, self).write(vals)
        changed = self.filtered(lambda r: before.get(r.id) != r.status)
        if changed:
            changed._apply_shopify_return_status_side_effects()
        return res

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------

    def _compute_picking_count(self):
        """Count the return pickings linked to each return."""
        for record in self:
            record.picking_count = len(record.picking_ids)

    def _compute_return_move_count(self):
        """Count the reverse stock moves linked to each return."""
        for record in self:
            record.return_move_count = len(record.return_move_ids)

    def _compute_credit_note_count(self):
        """Count the credit notes linked to each return."""
        for record in self:
            record.credit_note_count = len(record.credit_note_ids)

    # ------------------------------------------------------------------
    # Public entry points (cron / wizard / webhook)
    # ------------------------------------------------------------------

    def import_shopify_returns(self, mk_instance_id, from_date=False, to_date=False, mk_log_id=False):
        """
        Task: T8436 - Implement the logic that redirect to the queue or log view.
        Discover returns updated within the given date range and enqueue them. Each discovered return becomes one queue-job line of type
        'return' so the existing ``mk.queue.job`` infrastructure handles batching, retry, and logging in the same way as orders/products/customers.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model,
            from_date (datetime): only order updated on/after this. Optional.
            to_date (datetime): only order updated on/before this. Optional.
            mk_log_id (recordset): Recorset of mk.log.
        Returns:
            dict/bool: An ir.actions.act_window opening the created return queue (or the import log when nothing was queued), or True when there is nothing to show.
        Raises:
            MarketplaceException: if no instance is provided.
        """
        if not mk_instance_id:
            raise MarketplaceException(_("Please select a Shopify instance to import returns."))

        mk_log_obj = self.env['mk.log']
        mk_instance_id.connection_to_shopify()
        mk_log_id = mk_log_id or mk_log_obj.create_update_log(mk_instance_id=mk_instance_id, operation_type='import')

        date_filter = self._build_shopify_return_date_filter(from_date, to_date)
        try:
            return_entries = self._fetch_shopify_return_ids_for_date_range(mk_instance_id, date_filter)
        except MarketplaceException:
            raise
        except Exception as exc:
            log_traceback_for_exception()
            mk_log_obj.create_update_log(
                mk_instance_id=mk_instance_id,
                mk_log_id=mk_log_id, operation_type='import',
                mk_log_line_dict={'error': [{'log_message': f"IMPORT RETURNS: Failed to fetch return list. ERROR: {exc}"}]},
            )
            if mk_log_id and not mk_log_id.log_line_ids:
                mk_log_id.unlink()
            return False

        if not return_entries:
            mk_log_obj.create_update_log(
                mk_instance_id=mk_instance_id,
                mk_log_id=mk_log_id, operation_type='import',
                mk_log_line_dict={'success': [{'log_message': "IMPORT RETURNS: No new returns found in the selected date range."}]},
            )
            if mk_log_id and not mk_log_id.log_line_ids:
                mk_log_id.unlink()
            if mk_log_id.exists():
                return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
            return True

        # Skip returns already closed on both sides (Shopify CLOSED + local
        # CLOSED) — saves a queue line, an API call to fetch details, and a
        # redundant side-effect run. Logged so the user sees the activity.
        local_returns = self.search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('shopify_return_id', 'in', [str(extract_numeric_id(e['gid']) or '') for e in return_entries]),
        ])
        local_status_by_id = {r.shopify_return_id: r.status for r in local_returns}
        to_queue, skipped_msgs = [], []
        for entry in return_entries:
            numeric = str(extract_numeric_id(entry['gid']) or '')
            local_status = local_status_by_id.get(numeric)
            if entry['status'] == 'CLOSED' and local_status == 'CLOSED':
                label = entry.get('name') or numeric or entry['gid']
                skipped_msgs.append(
                    f"IMPORT RETURNS: Skipped {label} already CLOSED on both Shopify and Odoo."
                )
                continue
            to_queue.append(entry)
        if skipped_msgs:
            mk_log_obj.create_update_log(
                mk_instance_id=mk_instance_id,
                mk_log_id=mk_log_id, operation_type='import',
                mk_log_line_dict={'success': [{'log_message': msg} for msg in skipped_msgs]},
            )
        if not to_queue:
            if mk_log_id and not mk_log_id.log_line_ids:
                mk_log_id.unlink()
            if mk_log_id.exists():
                return mk_instance_id.action_open_model_view(mk_log_id.ids, 'mk.log', 'Log')
            return True

        queue_id = self._create_shopify_return_queue(mk_instance_id, to_queue, mk_log_id, source='import')
        if queue_id:
            return mk_instance_id.action_open_model_view(queue_id.ids, 'mk.queue.job', 'Shopify Return Queue')
        return True

    def enqueue_return_from_webhook(self, mk_instance_id, return_gid, mk_log_id=False):
        """
        Webhook entry point — push a single return GID into the return queue.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            return_gid (str): Shopify Return GID.
            mk_log_id (recordset): Recordset of mk.log model. Optional.
        Returns:
            recordset/bool: Created mk.queue.job recordset, or False if no GID.
        """
        if not return_gid:
            return False
        return self._create_shopify_return_queue(mk_instance_id, [return_gid], mk_log_id, source='webhook')

    @api.model
    def cron_auto_import_shopify_returns(self, mk_instance_id=False):
        """
        Cron entry point — incremental sync since the instance's last import.
`       Args:
            mk_instance_id (recordset/int): Recordset of mk.instance model (or its id), or False for every confirmed Shopify instance.
        Returns:
            bool: Returns True.
        """
        if mk_instance_id:
            instances = self.env['mk.instance'].browse(mk_instance_id) if isinstance(mk_instance_id, int) else mk_instance_id
        else:
            instances = self.env['mk.instance'].search([('marketplace', '=', 'shopify'), ('state', '=', 'confirmed')])
        for instance in instances:
            if instance.state != 'confirmed':
                continue
            from_date = instance.last_return_import_date or False
            to_date = fields.Datetime.now()
            try:
                self.import_shopify_returns(instance, from_date=from_date, to_date=to_date)
                instance.write({'last_return_import_date': to_date})
            except Exception as exc:
                log_traceback_for_exception()
                _logger.error(f"CRON: Auto Import Returns failed for instance {instance.name}. ERROR: {exc}")
        return True

    def cron_process_pending_cancelled_shopify_returns(self, mk_instance_id):
        """
        Periodically checks open Shopify returns in Odoo and updates them when the corresponding return has been cancelled in Shopify.
        Args:
            mk_instance_id (int): Id of the mk.instance to check.
        Returns:
            bool: Returns True.
        """
        mk_instance_id = self.env['mk.instance'].browse(mk_instance_id)
        if mk_instance_id.state == 'confirmed':
            self._process_pending_cancelled_shopify_returns(mk_instance_id)
        return True

    def _process_pending_cancelled_shopify_returns(self, mk_instance_id):
        """
        Fetch the latest return status from Shopify and update pending returns in Odoo when they are cancelled.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
        """
        pending_returns = self.search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('status', 'in', ('REQUESTED', 'OPEN')),
            ('shopify_return_id', '!=', False),
        ])
        if not pending_returns:
            return

        mk_instance_id.connection_to_shopify()
        mk_log_id = self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, operation_type='import')
        local_returns_by_gid = {f"gid://shopify/Return/{r.shopify_return_id}": r for r in pending_returns}

        for start in range(0, len(pending_returns), SHOPIFY_RETURN_FETCH_CHUNK_SIZE):
            chunk = pending_returns[start:start + SHOPIFY_RETURN_FETCH_CHUNK_SIZE]
            try:
                payloads = self._fetch_shopify_returns_by_ids(mk_instance_id, chunk)
            except Exception as error:
                self.env['mk.log'].create_update_log(
                    mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='import',
                    mk_log_line_dict={'error': [{'log_message': f"Failed to fetch Shopify return details for pending cancelled return processing. ERROR: {error}"}]},
                )
                continue
            for payload in payloads:
                self._apply_shopify_return_terminal_change(
                    mk_instance_id, payload, local_returns_by_gid, mk_log_id,
                )

        if not mk_log_id.log_line_ids:
            mk_log_id.unlink()

    def _apply_shopify_return_terminal_change(self, mk_instance_id, payload, local_returns_by_gid, mk_log_id):
        """
        Update and log a local return when Shopify reports it terminal (e.g. canceled).
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            payload (dict): The Shopify Return node.
            local_returns_by_gid (dict): Map of Return GID -> shopify.return.ts recordset.
            mk_log_id (recordset): Recordset of mk.log model.
        """
        remote_status = payload.get('status')
        local_return = local_returns_by_gid.get(payload.get('id'))
        if not local_return or remote_status not in SHOPIFY_TERMINAL_RETURN_STATUSES:
            return
        return_label = payload.get('name') or local_return.shopify_return_id
        try:
            self._upsert_shopify_return_from_payload(mk_instance_id, payload)
            log_lines = {'success': [{'log_message': f"Return {return_label} updated to {remote_status} from Shopify and related pending picking cancelled."}]}
        except Exception as error:
            log_traceback_for_exception()
            log_lines = {'error': [{'log_message': f"Failed to update cancelled Shopify return {return_label}. ERROR: {error}"}]}
        self.env['mk.log'].create_update_log(mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='import', mk_log_line_dict=log_lines)

    def _fetch_shopify_returns_by_ids(self, mk_instance_id, returns_recordset):
        """
        Fetch full Shopify Return payloads for N returns in one GraphQL call.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            returns_recordset (recordset): Recordset of shopify.return.ts model.
        Returns:
            list[dict]: The Shopify Return nodes.
        Raises:
            MarketplaceException: On a top-level GraphQL error.
        """
        if not returns_recordset:
            return []
        return_gids = [
            f"gid://shopify/Return/{return_record.shopify_return_id}"
            for return_record in returns_recordset
        ]
        return self._fetch_shopify_return_payloads_by_gids(mk_instance_id, return_gids)

    def _fetch_shopify_return_payloads_by_gids(self, mk_instance_id, return_gids):
        """
        Task: T8437 - Fetch complete Shopify Return GraphQL node payloads for given Return GIDs.
        Executes chunked batch queries targeting specific return IDs to retrieve detailed payload data.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            return_gids (list): Shopify Return GIDs.
        Returns:
            list[dict]: The Shopify Return nodes.
        Raises:
            MarketplaceException: On a top-level GraphQL error.
        """
        if not return_gids:
            return []
        payloads = []
        for start in range(0, len(return_gids), SHOPIFY_RETURN_FETCH_CHUNK_SIZE):
            chunk = return_gids[start:start + SHOPIFY_RETURN_FETCH_CHUNK_SIZE]
            response = mk_instance_id.execute_graphql_query(FETCH_MULTIPLE_RETURN_DETAILS, {"returnIds": chunk})
            self._raise_on_top_level_errors(response, "fetch Shopify returns by IDs")
            response_nodes = ((response or {}).get('data') or {}).get('nodes') or []
            payloads.extend([
                node for node in response_nodes
                if node and node.get('__typename') == 'Return'
            ])
        return payloads

    def import_shopify_returns_from_order_payload(self, mk_instance_id, shopify_order_dict, mk_log_id=False, queue_line_id=False):
        """
        Task: T8437 - Import returns directly from an order payload.
        Processes returns attached to an order and handles each based on data completeness:
          * Inline:   Created/updated immediately using order data (no extra API calls).
          * Detail:   Fetches missing restock and refund info via GraphQL before processing.
          * Enqueue:  Pushed to the background queue if data is incomplete or truncated.
          * Skip:     Ignored if already up-to-date in Odoo.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            shopify_order_dict (dict): The Shopify order payload.
            mk_log_id (recordset): Recordset of mk.log model. Optional.
            queue_line_id (recordset): Recordset of mk.queue.job.line model. Optional.
        Returns:
            bool: Returns True.
        """
        returns_block = shopify_order_dict.get('returns') or {}
        return_nodes = returns_block.get('nodes') or []
        if not return_nodes:
            return True

        # Only the fields the return sync actually reads out of the order block.
        order_context = {
            'id': shopify_order_dict.get('id'),
            'name': shopify_order_dict.get('name'),
            'taxesIncluded': shopify_order_dict.get('taxesIncluded'),
            'fulfillments': self._normalize_shopify_order_fulfillments(shopify_order_dict.get('fulfillments')),
        }
        # If Shopify has more return pages (hasNextPage is True), the list is incomplete.
        # Queue all returns so the background job can safely fetch every page.
        returns_truncated = bool((returns_block.get('pageInfo') or {}).get('hasNextPage'))

        mk_log_line_dict = {'error': [], 'success': []}
        log_line_id = queue_line_id and queue_line_id.id or False
        to_enqueue, to_process, detail_gids = [], [], []

        for node in return_nodes:
            return_gid = node.get('id')
            if not return_gid:
                continue
            sync_mode = 'enqueue' if returns_truncated else self._shopify_return_sync_mode_from_order_payload(mk_instance_id, node)
            if sync_mode == 'skip':
                continue
            if sync_mode == 'enqueue':
                to_enqueue.append({'gid': return_gid, 'name': node.get('name') or '', 'status': node.get('status') or ''})
                continue
            if sync_mode == 'detail':
                detail_gids.append(return_gid)
                continue
            to_process.append((node, True))

        if detail_gids:
            try:
                for full_payload in self._fetch_shopify_return_payloads_by_gids(mk_instance_id, detail_gids):
                    to_process.append((full_payload, False))
            except Exception as error:
                log_traceback_for_exception()
                mk_log_line_dict['error'].append({
                    'log_message': _("IMPORT RETURN: Could not fetch details for %(count)s return(s) of order %(order)s. ERROR: %(error)s") %
                                   {'count': len(detail_gids),
                                    'order': shopify_order_dict.get('name') or '',
                                    'error': error},
                    'queue_job_line_id': log_line_id})
                to_enqueue.extend([{'gid': gid, 'name': '', 'status': ''} for gid in detail_gids])

        sale_order = self._resolve_sale_order(mk_instance_id, order_context)

        for node, is_partial in to_process:
            payload = dict(node)
            payload['order'] = node.get('order') or order_context
            if is_partial:
                payload[SHOPIFY_PARTIAL_RETURN_PAYLOAD_KEY] = True
                self._preserve_shopify_return_payload_data(mk_instance_id, payload)
            return_record = self.with_context(active_sale_order_id=sale_order.id if sale_order else False)._upsert_shopify_return_from_payload(mk_instance_id, payload)
            return_record.with_context(
                mk_log_line_dict=mk_log_line_dict,
                queue_job_line_id=log_line_id,
            )._apply_shopify_return_status_side_effects()
            return_label = return_record.name or return_record.shopify_return_id
            if is_partial:
                log_message = _("IMPORT RETURN: Return %s synced directly from order import.") % return_label
                mk_log_line_dict['success'].append({'log_message': log_message, 'queue_job_line_id': log_line_id})

        if to_enqueue:
            self._create_shopify_return_queue(mk_instance_id, to_enqueue, mk_log_id, source='import')
            mk_log_line_dict['success'].append({
                'log_message': _("IMPORT RETURN: Queued %(count)s return(s) of order %(order)s for full processing due to incomplete data.") %
                               {'count': len(to_enqueue),
                                'order': shopify_order_dict.get('name') or ''
                                }, 'queue_job_line_id': log_line_id, })

        if mk_log_line_dict['error'] or mk_log_line_dict['success']:
            self.env['mk.log'].create_update_log(
                mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='import',
                mk_log_line_dict=mk_log_line_dict,
            )
        return True

    def _normalize_shopify_order_fulfillments(self, fulfillments):
        """
        Task: T8437 - Convert fulfillment line items from dictionaries to plain lists.
        Ensures order fulfillment data matches the list format expected by return processing.
        Args:
            fulfillments (list): The order payload's ``fulfillments`` block.
        Returns:
            list: Fulfillments whose ``fulfillmentLineItems`` is always a plain list.
        """
        normalized_fulfillments = []
        for fulfillment in fulfillments or []:
            if not isinstance(fulfillment, dict):
                continue
            fulfillment_copy = dict(fulfillment)
            fulfillment_line_items = fulfillment_copy.get('fulfillmentLineItems')
            if isinstance(fulfillment_line_items, dict):
                fulfillment_copy['fulfillmentLineItems'] = fulfillment_line_items.get('nodes') or []
            elif not isinstance(fulfillment_line_items, list):
                fulfillment_copy['fulfillmentLineItems'] = []
            normalized_fulfillments.append(fulfillment_copy)
        return normalized_fulfillments

    def _shopify_return_sync_mode_from_order_payload(self, mk_instance_id, node):
        """
        Task: T8437 - Determine the sync processing mode for a return node inside an order payload.
        Evaluates return status and payload completeness to decide how to process the record:
          * skip    - Already fully synced and unchanged in Odoo.
          * enqueue - Status unsafe or line items paginated; sent to return queue.
          * detail  - Return has restock data, fetch full restock dispositions.
          * inline  - Complete data present; ready for immediate processing.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            node (dict): The nested Shopify Return node taken from the order payload.
        Returns:
            str: One of 'inline', 'enqueue' or 'skip'.
        """
        status = node.get('status') or ''
        numeric_id = extract_numeric_id(node.get('id'))
        existing = self.browse()
        if numeric_id:
            existing = self.with_context(active_test=False).search([
                ('mk_instance_id', '=', mk_instance_id.id),
                ('shopify_return_id', '=', str(numeric_id)),
            ], limit=1)
        if existing and existing.sale_order_id and not existing._shopify_return_payload_is_partial() and existing.status == status:
            return 'skip'
        if status not in SHOPIFY_RETURN_STATUSES_SAFE_FROM_ORDER_PAYLOAD:
            return 'enqueue'
        line_block = node.get('returnLineItems') or {}
        if (line_block.get('pageInfo') or {}).get('hasNextPage'):
            return 'enqueue'
        line_nodes = line_block.get('nodes') or []
        if not line_nodes:
            return 'enqueue'
        rfo_block = node.get('reverseFulfillmentOrders')
        if rfo_block is None:
            return 'detail' if self._shopify_return_may_have_dispositions(node) else 'inline'
        if ((rfo_block or {}).get('pageInfo') or {}).get('hasNextPage'):
            return 'detail'
        for rfo_node in (rfo_block or {}).get('nodes') or []:
            if ((rfo_node.get('lineItems') or {}).get('pageInfo') or {}).get('hasNextPage'):
                return 'detail'
        return 'inline'

    def _shopify_return_may_have_dispositions(self, node):
        """
        Task: T8437 - Check if a return payload likely contains restock dispositions.
        Returns True for CLOSED returns or partially processed OPEN returns that require a full detail fetch.
        Args:
            node (dict): Raw Shopify Return node from the order payload.
        Returns:
            bool: True if full return details are needed to process restocks, else False.
        """
        if (node.get('status') or '') == 'CLOSED':
            return True
        if (node.get('status') or '') != 'OPEN':
            return False
        for line_node in ((node.get('returnLineItems') or {}).get('nodes') or []):
            if int(line_node.get('refundedQuantity') or 0) > 0:
                return True
            refundable_quantity = line_node.get('refundableQuantity')
            if refundable_quantity is not None and int(refundable_quantity) != int(line_node.get('quantity') or 0):
                return True
        return False

    def _preserve_shopify_return_payload_data(self, mk_instance_id, payload):
        """
        Task: T8437 - Retain previously stored return payload keys during order syncs.
        Prevents overwriting critical fields (like refunds) when updating from a partial payload.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            payload (dict): The order-derived Return payload, updated in place.
        Returns:
            dict: The same payload, enriched with any preserved blocks.
        """
        numeric_id = extract_numeric_id(payload.get('id'))
        if not numeric_id:
            return payload
        existing = self.with_context(active_test=False).search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('shopify_return_id', '=', str(numeric_id)),
        ], limit=1)
        if not existing or not existing.shopify_payload_json:
            return payload
        try:
            stored_payload = ast.literal_eval(existing.shopify_payload_json) or {}
        except Exception:
            return payload
        for payload_key in SHOPIFY_RETURN_PAYLOAD_KEYS_TO_PRESERVE:
            if not payload.get(payload_key) and stored_payload.get(payload_key):
                payload[payload_key] = stored_payload[payload_key]
        return payload

    def _shopify_return_payload_is_partial(self):
        """
        Task: T8437 - Check if the stored Shopify return payload is partial.
        Returns:
            bool: True when the stored payload is partial, missing or unreadable.
        """
        self.ensure_one()
        if not self.shopify_payload_json:
            return True
        try:
            payload = ast.literal_eval(self.shopify_payload_json)
        except Exception:
            return True
        return bool((payload or {}).get(SHOPIFY_PARTIAL_RETURN_PAYLOAD_KEY))

    # ------------------------------------------------------------------
    # Queue-line processor (called by mk.queue.job override)
    # ------------------------------------------------------------------

    def process_shopify_return_queue_line(self, queue_line):
        """Process one return queue line: fetch details, upsert it, run side-effects.

        All warnings / successes raised by ``_apply_shopify_return_status_side_effects``
        and its descendants are also captured into the queue's ``mk.log``
        — not just the chatter — so users see the full processing story
        on the queue line without opening the return form.
        Args:
            queue_line (recordset): Recordset of mk.queue.job.line model.
        Returns:
            recordset/bool: Synced shopify.return.ts recordset, or False on failure.
        """
        self.ensure_one() if self else None
        mk_instance_id = queue_line.queue_id.mk_instance_id
        mk_log_id = queue_line.queue_id.mk_log_id
        mk_log_line_dict = {'error': [], 'success': []}

        def _flush():
            if mk_log_line_dict['error'] or mk_log_line_dict['success']:
                self.env['mk.log'].create_update_log(
                    mk_instance_id=mk_instance_id, mk_log_id=mk_log_id, operation_type='import',
                    mk_log_line_dict=mk_log_line_dict,
                )

        return_gid = self._extract_shopify_return_gid_from_queue_line(queue_line)
        if not return_gid:
            mk_log_line_dict['error'].append({
                'log_message': f"PROCESS RETURN: Queue line {queue_line.id} has no return GID payload.",
                'queue_job_line_id': queue_line.id,
            })
            _flush()
            return False

        mk_instance_id.connection_to_shopify()
        try:
            payload = self._fetch_shopify_return_details(mk_instance_id, return_gid)
            if not payload:
                mk_log_line_dict['error'].append({
                    'log_message': f"PROCESS RETURN: Shopify returned no data for {return_gid}.",
                    'queue_job_line_id': queue_line.id,
                })
                _flush()
                return False
            return_record = self._upsert_shopify_return_from_payload(mk_instance_id, payload)
            # Funnel side-effect chatter messages into the queue log.
            return_record.with_context(
                mk_log_line_dict=mk_log_line_dict,
                queue_job_line_id=queue_line.id,
            )._apply_shopify_return_status_side_effects()
            mk_log_line_dict['success'].append({
                'log_message': f"PROCESS RETURN: Synced return {return_record.name or return_record.shopify_return_id}.",
                'queue_job_line_id': queue_line.id,
            })
            _flush()
            return return_record
        except MarketplaceException as exc:
            mk_log_line_dict['error'].append({
                'log_message': f"PROCESS RETURN: {exc}",
                'queue_job_line_id': queue_line.id,
            })
            _flush()
            return False
        except Exception as exc:
            log_traceback_for_exception()
            mk_log_line_dict['error'].append({
                'log_message': f"PROCESS RETURN: Unexpected error syncing {return_gid}. ERROR: {exc}",
                'queue_job_line_id': queue_line.id,
            })
            _flush()
            return False

    # ------------------------------------------------------------------
    # GraphQL helpers
    # ------------------------------------------------------------------

    def _build_shopify_return_date_filter(self, from_date, to_date):
        """
        Compose a Shopify search query string scoped to returns updated in the range.
        Args:
            from_date (datetime): Lower bound. Optional.
            to_date (datetime): Upper bound. Optional.
        Returns:
            str: The Shopify search query.
        """
        terms = [SHOPIFY_RETURN_STATUS_SEARCH_GROUP]
        if from_date:
            terms.append(f'updated_at:>="{fields.Datetime.to_string(from_date)}Z"')
        if to_date:
            terms.append(f'updated_at:<="{fields.Datetime.to_string(to_date)}Z"')
        return " AND ".join(terms) if len(terms) > 1 else terms[0]

    def _fetch_shopify_return_ids_for_date_range(self, mk_instance_id, search_query, page_size=50):
        """
        Walk the paginated returns list and collect each return's gid, name and status.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            search_query (str): Shopify search filter.
            page_size (int): Page size. Defaults to 50.
        Returns:
            list[dict]: Entries with ``gid``, ``name`` and ``status`` (de-duplicated, order kept).
        Raises:
            MarketplaceException: On a top-level GraphQL error.
        """
        seen, results, cursor, has_next = set(), [], None, True
        while has_next:
            variables = {"searchQuery": search_query, "pageSize": page_size, "afterCursor": cursor}
            response = mk_instance_id.execute_graphql_query(LIST_ORDER_RETURNS_BY_DATE, variables)
            self._raise_on_top_level_errors(response, "list returns")
            data = response.get('data', {}).get('orders', {}) if isinstance(response, dict) else {}
            for order_node in data.get('nodes', []) or []:
                returns_block = order_node.get('returns', {}) or {}
                for ret in returns_block.get('nodes', []) or []:
                    gid = ret.get('id')
                    if not gid or gid in seen:
                        continue
                    seen.add(gid)
                    results.append({
                        'gid': gid,
                        'name': ret.get('name') or '',
                        'status': ret.get('status') or '',
                    })
            page_info = data.get('pageInfo', {}) or {}
            has_next = bool(page_info.get('hasNextPage'))
            cursor = page_info.get('endCursor') if has_next else None
        return results

    def _fetch_shopify_return_details(self, mk_instance_id, return_gid):
        """
        Fetch the full Shopify payload for one return.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            return_gid (str): Shopify Return GID.
        Returns:
            dict: The Shopify Return node (empty dict if none).
        Raises:
            MarketplaceException: On a top-level GraphQL error.
        """
        variables = {"returnId": return_gid}
        response = mk_instance_id.execute_graphql_query(GET_SHOPIFY_RETURN_DETAILS, variables)
        self._raise_on_top_level_errors(response, "fetch return details")
        return (response or {}).get('data', {}).get('return') or {}

    @staticmethod
    def _raise_on_top_level_errors(response, action_label):
        """
        Raise if the GraphQL response carries top-level errors.
        Args:
            response (dict): The GraphQL response.
            action_label (str): Action name used in the error message.
        Raises:
            MarketplaceException: If any top-level error is present.
        """
        if not isinstance(response, dict):
            return
        errors = response.get('errors') or []
        if errors and isinstance(errors, list):
            messages = ", ".join(err.get('message', str(err)) for err in errors)
            raise MarketplaceException(f"⚠️ Failed to {action_label}: {messages}")

    @staticmethod
    def _raise_on_user_errors(response, mutation_root, action_label):
        """
        Raise if a mutation returned userErrors.
        Args:
            response (dict): The GraphQL response.
            mutation_root (str): The mutation field to inspect.
            action_label (str): Action name used in the error message.
        Raises:
            MarketplaceException: If any user error is present.
        """
        if not isinstance(response, dict):
            return
        block = (response.get('data') or {}).get(mutation_root) or {}
        user_errors = block.get('userErrors') or []
        if user_errors:
            messages = ", ".join(err.get('message', str(err)) for err in user_errors)
            raise MarketplaceException(f"⚠️ Failed to {action_label}: {messages}")

    # ------------------------------------------------------------------
    # Queue creation
    # ------------------------------------------------------------------

    def _create_shopify_return_queue(self, mk_instance_id, return_entries, mk_log_id, source='import'):
        """
        Build one ``mk.queue.job`` of type='return' with one line per return.
        The queue line ``name`` is set to the actual Shopify return name
        (e.g. ``#1290-R6``) when available, so the queue UI reads like the
        Shopify admin instead of showing only the numeric ID.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            return_entries (list): Dicts with ``gid``/``name``/``status``, or bare GID strings (webhook).
            mk_log_id (recordset): Recordset of mk.log model.
            source (str): 'import' or 'webhook'. Defaults to 'import'.
        Returns:
            recordset: Created mk.queue.job recordset.
        """
        new_queue = mk_instance_id.action_create_queue(type='return')
        if mk_log_id:
            new_queue.write({'mk_log_id': mk_log_id.id})
        for entry in return_entries:
            if isinstance(entry, dict):
                gid = entry.get('gid')
                ret_name = entry.get('name') or ''
            else:
                gid, ret_name = entry, ''
            numeric_id = str(extract_numeric_id(gid) or '')
            if ret_name:
                line_name = f"Shopify Return {ret_name}"
            elif numeric_id:
                line_name = f"Shopify Return {numeric_id}"
            else:
                line_name = f"Shopify Return ({gid})"
            line_vals = {
                'mk_id': numeric_id,
                'state': 'draft',
                'name': line_name,
                'data_to_process': pprint.pformat({'return_gid': gid, 'source': source}),
                'mk_instance_id': mk_instance_id.id,
            }
            new_queue.action_create_queue_lines(line_vals)
        return new_queue

    @staticmethod
    def _extract_shopify_return_gid_from_queue_line(queue_line):
        """
        Re-derive the Shopify return GID from the queue line payload or stored mk_id.
        Args:
            queue_line (recordset): Recordset of mk.queue.job.line model.
        Returns:
            str/bool: The Return GID, or False if it can't be derived.
        """
        try:
            payload = queue_line.data_to_process and ast.literal_eval(queue_line.data_to_process)
        except Exception:
            payload = None
        if isinstance(payload, dict) and payload.get('return_gid'):
            return payload['return_gid']
        if queue_line.mk_id:
            return f"gid://shopify/Return/{queue_line.mk_id}"
        return False

    # ------------------------------------------------------------------
    # Upsert from payload
    # ------------------------------------------------------------------

    def _upsert_shopify_return_from_payload(self, mk_instance_id, payload):
        """
        Create or update a shopify.return.ts (and its lines) from a Shopify Return node.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            payload (dict): The Shopify Return node.
        Returns:
            recordset: Created/updated shopify.return.ts recordset.
        Raises:
            MarketplaceException: If the payload has no Shopify ID.
        """
        self = self.sudo()
        return_gid = payload.get('id')
        numeric_id = extract_numeric_id(return_gid) if return_gid else False
        if not numeric_id:
            raise MarketplaceException(_("Cannot upsert a return with no Shopify ID."))

        order_block = payload.get('order') or {}
        sale_order = self._resolve_sale_order(mk_instance_id, order_block)

        # Fallback to active order from context if order_block was empty
        if not sale_order and self.env.context.get('active_sale_order_id'):
            sale_order = self.env['sale.order'].browse(self.env.context.get('active_sale_order_id'))

        existing = self.with_context(active_test=False).search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('shopify_return_id', '=', str(numeric_id)),
        ], limit=1)
        decline_block = payload.get('decline') or {}

        # If a new sale_order is found, USE IT. Otherwise, preserve existing order.
        resolved_sale_order_id = sale_order.id if sale_order else (existing.sale_order_id.id if existing else False)

        vals = {
            'mk_instance_id': mk_instance_id.id,
            'shopify_return_id': str(numeric_id),
            'name': payload.get('name') or '',
            'status': payload.get('status') or 'REQUESTED',
            'total_quantity': int(payload.get('totalQuantity') or 0),
            'decline_reason': decline_block.get('reason') or False,
            'decline_note': decline_block.get('note') or False,
            'sale_order_id': resolved_sale_order_id,
            'shopify_payload_json': pprint.pformat(payload),
            'last_imported_at': fields.Datetime.now(),
        }
        if existing:
            existing.write(vals)
            return_record = existing
        else:
            return_record = self.create(vals)

        return_record._sync_lines_from_shopify_return_payload(
            payload.get('returnLineItems') or {},
            payload.get('reverseFulfillmentOrders') or {},
        )
        return return_record

    def _resolve_sale_order(self, mk_instance_id, order_block):
        """
        Find the local sale order matching the Shopify order in the payload.
        Args:
            mk_instance_id (recordset): Recordset of mk.instance model.
            order_block (dict): The ``order`` block from the return payload.
        Returns:
            recordset/bool: Matched sale.order recordset, or False.
        """
        order_gid = (order_block or {}).get('id')
        if not order_gid:
            return False
        numeric = extract_numeric_id(order_gid)
        if not numeric:
            return False
        return self.env['sale.order'].search([
            ('mk_instance_id', '=', mk_instance_id.id),
            ('mk_id', '=', str(numeric)),
        ], limit=1) or False

    def _sync_lines_from_shopify_return_payload(self, return_line_items_block, reverse_fulfillment_orders_block=None):
        """
        Create, update or remove this return's lines from the Shopify payload.
        Args:
            return_line_items_block (dict): The ``returnLineItems`` block from the payload.
            reverse_fulfillment_orders_block (dict): The ``reverseFulfillmentOrders`` block, used to attach each line's reverse-fulfillment GID. Optional.
        """
        self.ensure_one()
        line_obj = self.env['shopify.return.line.ts']
        nodes = (return_line_items_block or {}).get('nodes') or []

        # Map: fulfillmentLineItem GID -> reverseFulfillmentOrderLineItem GID
        # so each return line can find its matching RFO line GID for dispositions.
        rfo_map = {}
        for rfo_node in ((reverse_fulfillment_orders_block or {}).get('nodes') or []):
            for rfo_line in (rfo_node.get('lineItems') or {}).get('nodes', []) or []:
                ful_gid = (rfo_line.get('fulfillmentLineItem') or {}).get('id')
                rfo_gid = rfo_line.get('id')
                if ful_gid and rfo_gid:
                    rfo_map[ful_gid] = rfo_gid

        seen_ids = set()
        for node in nodes:
            line_gid = node.get('id')
            if not line_gid:
                continue
            line_numeric = self._normalize_shopify_return_line_id(line_gid)
            seen_ids.add(line_numeric)
            existing = line_obj.search([
                ('return_id', '=', self.id),
                ('shopify_return_line_id', '=', line_numeric),
            ], limit=1)
            line_vals = self._prepare_shopify_return_line_vals(node)
            # Attach RFO line GID by matching on forward fulfillment line GID
            ful_gid = line_vals.get('fulfillment_line_item_gid')
            line_vals['reverse_fulfillment_line_id'] = rfo_map.get(ful_gid) or False
            if existing:
                existing.write(line_vals)
            else:
                line_obj.create(dict(line_vals, return_id=self.id))
        stale = self.return_line_ids.filtered(lambda l: l.shopify_return_line_id not in seen_ids)
        if stale:
            stale.unlink()

    @staticmethod
    def _normalize_shopify_return_line_id(line_gid):
        """
        Return the return line id as a string for the Char field, keeping the GID if it has no numeric part.
        Args:
            line_gid (str): The Shopify return line GID.
        Returns:
            str: The numeric id as a string, or the original GID.
        """
        numeric = extract_numeric_id(line_gid)
        if numeric is not None:
            return str(numeric)
        return line_gid

    def _resolve_shopify_return_reason_definition(self, node):
        """
        Find the matching Shopify return reason in Odoo using the reason definition received from Shopify. If the reason does not exist,
        create it and return the record ID.
        Args:
            node (dict): The Shopify return line node.
        Returns:
            int/bool: Id of the shopify.return.reason.ts record, or False if none.
        """
        definition = node.get('returnReasonDefinition') or {}
        numeric = extract_numeric_id(definition.get('id'))
        if not numeric:
            return False
        reason_obj = self.env['shopify.return.reason.ts'].sudo()
        reason = reason_obj.search([
            ('shopify_reason_definition_id', '=', str(numeric)),
            ('mk_instance_id', '=', self.mk_instance_id.id),
        ], limit=1)
        if not reason:
            reason = reason_obj.create({
                'name': definition.get('name') or '',
                'handle': definition.get('handle') or False,
                'shopify_reason_definition_id': str(numeric),
                'mk_instance_id': self.mk_instance_id.id,
            })
        return reason.id

    def _prepare_shopify_return_line_vals(self, node):
        """
        Prepare Odoo return line values from a Shopify return line.
        Extract the required information from the Shopify return line payload and
        build the values used to create or update the corresponding
        shopify.return.line record. Supports both fulfillment-based return lines
        and unverified return lines.
        Args:
            node (dict): Shopify return line data.
        Returns:
            dict: Values for creating/updating a shopify.return.line record.
        """
        ful_line = node.get('fulfillmentLineItem') or {}
        if ful_line:
            line_item = ful_line.get('lineItem') or {}
        else:
            line_item = node.get('lineItem') or {}
        variant = line_item.get('variant') or {}

        def _id_to_str(gid):
            """Return numeric portion of a GID as a string for Char fields."""
            n = extract_numeric_id(gid)
            return str(n) if n is not None else False

        return {
            'shopify_return_line_id': self._normalize_shopify_return_line_id(node.get('id')),
            'fulfillment_line_item_gid': ful_line.get('id') or False,
            'shopify_line_item_id': _id_to_str(line_item.get('id')),
            'shopify_variant_id': _id_to_str(variant.get('id')),
            'sku': line_item.get('sku') or '',
            'title': line_item.get('title') or '',
            'quantity': int(node.get('quantity') or 0),
            'refundable_quantity': int(node.get('refundableQuantity') or 0),
            'refunded_quantity': int(node.get('refundedQuantity') or 0),
            'return_reason_definition_id': self._resolve_shopify_return_reason_definition(node),
            'return_reason_note': node.get('returnReasonNote') or False,
        }

    # ------------------------------------------------------------------
    # Logging bridge
    # ------------------------------------------------------------------

    def _log_to_queue(self, severity, message):
        """
        Mirror a side-effect message into the queue's ``mk.log`` if the
        current context was set up by ``process_shopify_return_queue_line``.
        Safe no-op outside the queue (e.g. manual button clicks).
        Args:
            severity (str): Log bucket, 'success' or 'error'.
            message (str): The message to record.
        """
        log_dict = self.env.context.get('mk_log_line_dict')
        if not isinstance(log_dict, dict) or severity not in log_dict:
            return
        log_dict[severity].append({
            'log_message': f"PROCESS RETURN: {message}",
            'queue_job_line_id': self.env.context.get('queue_job_line_id'),
        })

    def _restocked_quantities_by_fulfillment_line_gid(self):
        """
        Task: T8436 - Return the restocked quantity per fulfillment line instead of only the line IDs, so partial restocks are honoured.
        Read the stored Shopify return payload and collect how many units Shopify
        actually restocked, keyed by Fulfillment Line Item GID.

        Shopify reports restocking as reverse-fulfillment dispositions, and a line
        can be *partially* restocked: 3 units returned, 1 restocked, 2 discarded as
        damaged. Only ``RESTOCKED`` dispositions put goods back on the shelf; every
        other type means the units did not return to sellable stock.

        Quantities are summed rather than short-circuited, because Shopify emits one
        disposition per restock location and a line can be restocked to several.
        Returns:
            dict: Fulfillment Line Item GID -> total restocked quantity (ints > 0).
        """
        self.ensure_one()
        if not self.shopify_payload_json:
            return {}
        try:
            payload = ast.literal_eval(self.shopify_payload_json)
        except Exception:
            return {}
        restocked = {}
        for rfo_node in (((payload or {}).get('reverseFulfillmentOrders') or {}).get('nodes') or []):
            for rfo_line in (rfo_node.get('lineItems') or {}).get('nodes', []) or []:
                ful_gid = (rfo_line.get('fulfillmentLineItem') or {}).get('id')
                if not ful_gid:
                    continue
                for disp in (rfo_line.get('dispositions') or []):
                    if disp.get('type') != 'RESTOCKED':
                        continue
                    qty = int(disp.get('quantity') or 0)
                    if qty > 0:
                        restocked[ful_gid] = restocked.get(ful_gid, 0) + qty
        return restocked

    def _shopify_restocked_quantity_by_return_line(self):
        """
        Task: T8437 - Map restocked quantities from Shopify fulfillment lines to return lines.
        Allocates restocked units per line, capped at the return line's total quantity.
        Returns:
            dict: shopify.return.line.ts ID -> restocked quantity on Shopify.
        """
        self.ensure_one()
        remaining = dict(self._restocked_quantities_by_fulfillment_line_gid())
        by_line = {}
        for line in self.return_line_ids:
            gid = line.fulfillment_line_item_gid
            take = min(int(line.quantity or 0), remaining.get(gid, 0) if gid else 0)
            if gid and take > 0:
                remaining[gid] -= take
            by_line[line.id] = take
        return by_line

    def _restocked_quantity_by_so_line(self):
        """
        Task: T8437 - Calculate quantities restocked in Odoo per sale order line. Sums completed stock moves and validated return pickings.
        Returns:
            dict: sale.order.line ID -> restocked quantity in Odoo.
        """
        self.ensure_one()
        done_by_so_line = {}
        for move in self.return_move_ids.filtered(lambda m: m.state == 'done' and m.sale_line_id):
            qty = int(move.quantity or move.product_uom_qty or 0)
            done_by_so_line[move.sale_line_id.id] = done_by_so_line.get(move.sale_line_id.id, 0) + qty
        for picking in self.picking_ids.filtered(lambda p: p.state == 'done'):
            for move in picking.move_ids.filtered(lambda m: m.sale_line_id):
                qty = int(move.quantity or 0)
                done_by_so_line[move.sale_line_id.id] = done_by_so_line.get(move.sale_line_id.id, 0) + qty
        return done_by_so_line

    def _get_eligible_force_restock_qty_by_line(self):
        """
        Task: T8437 - Calculate non-restocked line quantities eligible for manual force restocking.
        Computes returned quantity minus Shopify restocked and previously force-restocked units.
        Returns:
            dict: shopify.return.line.ts ID -> remaining quantity eligible to force restock.
        """
        self.ensure_one()
        if self.status not in ('OPEN', 'CLOSED'):
            return {}
        shopify_restocked = self._shopify_restocked_quantity_by_return_line()
        if self.status == 'OPEN' and not any(shopify_restocked.values()):
            return {}
        if sum(shopify_restocked.values()) > sum(self._restocked_quantity_by_so_line().values()):
            return {}
        candidates = {}
        for line in self.return_line_ids:
            missing = int(line.quantity or 0) - shopify_restocked.get(line.id, 0) - int(line.force_restocked_qty or 0)
            if missing > 0:
                candidates[line.id] = missing
        return candidates

    @api.depends('status', 'shopify_payload_json', 'return_line_ids.quantity',
                 'return_line_ids.fulfillment_line_item_gid', 'return_line_ids.force_restocked_qty',
                 'return_move_ids.state', 'return_move_ids.quantity', 'picking_ids.state')
    def _compute_is_restock_skipped_in_shopify(self):
        """
        Task: T8437 - Compute visibility for the Force Restock button.
        Sets the flag to True if any return lines have unrestocked quantities eligible for manual force restock.
        """
        for record in self:
            record.is_restock_skipped_in_shopify = bool(record._get_eligible_force_restock_qty_by_line())

    def shopify_return_payload_has_any_dispositions(self):
        """
        Check whether Shopify return includes disposition data.
        Verify if any reverse fulfillment order line in the stored Shopify return payload contains disposition information.
        Returns:
            bool: True if at least one disposition exists, otherwise False.
        """
        self.ensure_one()
        if not self.shopify_payload_json:
            return False
        try:
            payload = ast.literal_eval(self.shopify_payload_json)
        except Exception:
            return False
        for rfo_node in (((payload or {}).get('reverseFulfillmentOrders') or {}).get('nodes') or []):
            for rfo_line in (rfo_node.get('lineItems') or {}).get('nodes', []) or []:
                if rfo_line.get('dispositions'):
                    return True
        return False

    # ------------------------------------------------------------------
    # Status side effects
    #
    # When a return reaches CLOSED status, generate the incoming picking
    # in Odoo using the standard ``stock.return.picking`` transient wizard
    # — the same code path a user would hit clicking "Return" on a delivery
    # in the Inventory app. This guarantees correct stock moves,
    # reservations, lot/serial behavior, and accounting valuation.
    # ------------------------------------------------------------------

    def _apply_shopify_return_status_side_effects(self):
        """
        Task: T8436 - Create the return picking only when Shopify reports a RESTOCKED disposition, never when the return is approved.
        Apply inventory and accounting actions based on Shopify return status.

        Create, validate, or cancel return pickings and stock moves according to the
        current Shopify return status. Also handles restock tracking, credit note
        creation, and linking of related accounting documents.

        Shopify Return Status behavior:
        - OPEN: Nothing, unless Shopify already published RESTOCKED dispositions
          (a partial process leaves the return OPEN) — then mirror exactly those
          lines. Shopify moves no inventory at approval time, so neither do we.
        - CLOSED: Process restocking or mark returns for manual restock when Shopify closed the return without restocking.
        - DECLINED/CANCELED: Cancel any pending return inventory operations.

        Returns:
            bool: True.
        """
        self = self.sudo()
        for record in self:
            order = record.sale_order_id
            has_source_picking = bool(order and order.picking_ids.filtered(
                lambda p: p.state == 'done' and p.picking_type_id and p.picking_type_id.code == 'outgoing'
            ))
            has_orphan_moves = bool(order and record._get_outgoing_orphan_moves())

            if order and record.status in ('DECLINED', 'CANCELED'):
                own_lines = record.return_line_ids.sale_order_line_id
                candidate_moves = own_lines.move_ids if own_lines else order.order_line.move_ids
                stale_moves = candidate_moves.filtered('shopify_return_exhausted')
                stale_moves and stale_moves.write({'shopify_return_exhausted': False})
                stale_pickings = candidate_moves.picking_id.filtered(
                    lambda p: not p.has_shopify_returnable_qty
                    and p.picking_type_id.code == 'outgoing')
                stale_pickings and stale_pickings.write({'has_shopify_returnable_qty': True})

            if record.status == 'OPEN':
                if record._restocked_quantities_by_fulfillment_line_gid():
                    if not has_source_picking and not has_orphan_moves:
                        record._log_shopify_return_restock_deferred()
                    if has_source_picking:
                        record._ensure_return_picking_via_native_wizard(validate=True)
                    if has_orphan_moves:
                        record._create_pending_shopify_return_moves(validate=True)
                    record._validate_pending_return_pickings()
                    record._validate_pending_shopify_return_moves()

            elif record.status == 'CLOSED':
                had_restock = bool(record._restocked_quantities_by_fulfillment_line_gid())

                if had_restock:
                    if not has_source_picking and not has_orphan_moves:
                        record._log_shopify_return_restock_deferred()
                    # Restock confirmed — create or validate pickings and/or moves.
                    if has_source_picking:
                        record._ensure_return_picking_via_native_wizard(validate=True)
                    if has_orphan_moves:
                        record._create_pending_shopify_return_moves(validate=True)
                    record._validate_pending_return_pickings()
                    record._validate_pending_shopify_return_moves()
                else:
                    # No restock — cancel any waiting picking/move left over from OPEN
                    # auto-create. The cancel helpers preserve any done picking/move
                    # (e.g. Force Restock validated earlier).
                    cancel_reason = _("Shopify closed the return without restocking the items")
                    record._cancel_pending_return_pickings(reason=cancel_reason)
                    record._cancel_pending_shopify_return_moves(reason=cancel_reason)

                    still_has_done_inventory = bool(
                        record.picking_ids.filtered(lambda p: p.state == 'done')
                        or record.return_move_ids.filtered(lambda m: m.state == 'done')
                    )
                    if not still_has_done_inventory:
                        record._log_shopify_return_restock_skipped()

                record._ensure_credit_notes_from_shopify_return_payload()
                record._link_existing_credit_notes()

            elif record.status in ('DECLINED', 'CANCELED'):
                record._cancel_pending_return_pickings()
                record._cancel_pending_shopify_return_moves()
        return True

    def _log_shopify_return_restock_deferred(self):
        """
        Log that Shopify restocked this return but Odoo has nothing to reverse yet.
        Returns:
            bool: Returns True.
        """
        self.ensure_one()
        order_name = self.sale_order_id.name or _("the related order")
        message = _(
            "Return %(return_name)s was not processed in Odoo because the delivery order "
            "for %(order_name)s is not validated yet. Validate the delivery order, then "
            "click 'Resync from Shopify' to process the return."
        ) % {'return_name': self.name or self.shopify_return_id, 'order_name': order_name}
        self.message_post(body=message)
        self._log_to_queue('success', message)
        return True

    def _log_shopify_return_restock_skipped(self):
        """Log a message when Shopify closes a return without restocking the items."""
        self.ensure_one()
        reason = ""
        if self.return_line_ids and not any(line.shopify_variant_id for line in self.return_line_ids):
            reason = _(" The Shopify product variant is no longer available, so these items could not be restocked in Shopify.")
        msg = _(
            "Shopify closed this return without restocking the items. So, no restock was done in Odoo automatically.%(reason)s If the items were actually returned, click Force Restock to restock them manually.") % {
                  'reason': reason}
        self.message_post(body=msg)
        self._log_to_queue('success', msg)

    def _ensure_return_picking_via_native_wizard(self, validate=False):
        """
        Task: T8436 - Trim existing and adopted receipts to Shopify's restocked quantity before validating them.
        Create the incoming return picking by driving Odoo's native wizard.

        Idempotent — bails out silently if a picking is already linked or if
        we cannot resolve a viable source picking.

        Before creating a new picking, attempts to **adopt** any unlinked
        return pickings already present on the order — covers the case
        where the user manually clicked "Return" in Inventory before
        the Shopify return was imported. Adopting prevents duplicate
        return pickings for the same physical goods.

        Args:
            validate: when True, force-validates each freshly created or adopted picking so it lands in ``done`` state.
        Returns:
            recordset: Recordset of stock.picking model (created, adopted or existing; may be empty).
        """
        self.ensure_one()
        existing_pickings = self.picking_ids.filtered(lambda p: p.state != 'cancel')
        missing_qty_by_so_line = {}
        if existing_pickings and not self.env.context.get('force_restock_override'):
            if validate:
                self._trim_pickings_to_allowed_quantities(existing_pickings)
                for picking in existing_pickings:
                    self._force_validate_return_picking(picking)

            so_lines = self.return_line_ids.sale_order_line_id
            if not (self.picking_ids.filtered(lambda p: p.state != 'done') or existing_pickings.backorder_ids
                    or existing_pickings.move_ids.filtered(lambda m: m.state != 'cancel' and (not m.sale_line_id or m.product_uom.compare(m.quantity, m.product_uom_qty) < 0))
                    or self._get_outgoing_orphan_moves()
                    or self.sale_order_id.picking_ids.filtered(
                        lambda p: p.picking_type_id.code == 'incoming' and p.state != 'cancel' and not p.shopify_return_id
                                  and any(m.origin_returned_move_id and m.product_id in so_lines.move_ids.product_id for m in p.move_ids))
                    or any(len(line.move_ids.filtered(lambda m: m.state == 'done' and m.location_dest_id.usage == 'customer').location_id.warehouse_id) > 1 for line in so_lines)
                    or any(len(picking.move_ids.filtered(lambda m: m.product_id == product and m.state != 'cancel')) > 1
                           for picking in self.sale_order_id.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_id.code == 'outgoing')
                           for product in picking.move_ids.product_id)):
                received = self._restocked_quantity_by_so_line()
                missing_qty_by_so_line = {line_id: qty - received.get(line_id, 0) for line_id, qty in self._return_quantities_by_so_line().items()
                                          if qty > received.get(line_id, 0)}
            if not missing_qty_by_so_line:
                return existing_pickings

        adopted = not missing_qty_by_so_line and self._adopt_existing_return_pickings()
        if adopted:
            if validate:
                # An adopted receipt was built by the user for the whole return,
                # before Shopify decided the dispositions. Cut it down the same
                # way an already-linked receipt is cut down, or we restock more
                # than Shopify did.
                self._trim_pickings_to_allowed_quantities(adopted)
                for picking in adopted:
                    self._force_validate_return_picking(picking)
            return adopted

        order = self.sale_order_id
        if not order:
            msg = _("Cannot create return picking: no Odoo sale order linked to this return.")
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
            return self.env['stock.picking']

        source_pickings = order.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_id and p.picking_type_id.code == 'outgoing'
        )
        if not source_pickings:
            msg = _("Cannot create return picking: no done outgoing delivery found on the order.")
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
            return self.env['stock.picking']

        remaining_qty_by_so_line = missing_qty_by_so_line or self._return_quantities_by_so_line()
        if not remaining_qty_by_so_line:
            return self.env['stock.picking']

        self = self.with_context(skip_inventory_sync_commit=True)
        created_pickings = self.env['stock.picking']
        for source_picking in source_pickings:
            allocations = []
            qty_by_product = self._return_quantities_against_picking(source_picking, remaining_qty_by_so_line, allocations)
            if not qty_by_product:
                continue

            for target_location, qty_subset in self._split_qty_by_restock_destination(source_picking, allocations, bool(missing_qty_by_so_line)).items():
                new_picking = self._invoke_native_shopify_return_wizard(source_picking, qty_subset, target_location)
                if new_picking:
                    new_picking.write({
                        'shopify_return_id': self.id,
                        'mk_instance_id': self.mk_instance_id.id,
                    })
                    if validate:
                        self._force_validate_return_picking(new_picking)
                    created_pickings |= new_picking
        if created_pickings:
            done_count = len(created_pickings.filtered(lambda p: p.state == 'done'))
            msg = _("Created %s return picking(s) via Odoo's standard return wizard "
                    "(%s validated automatically).") % (len(created_pickings), done_count)
            self.message_post(body=msg)
            self._log_to_queue('success', msg)
        return created_pickings

    def _adopt_existing_return_pickings(self):
        """Link unlinked manual return pickings on the order to this return.

        Why: a user can click "Return" on the outgoing delivery in
        Inventory before the Shopify return is imported. Without this
        adoption step, the import path would create a *second* return
        picking — duplicating the physical receipt of the same goods
        and pushing the sale-line delivered quantity negative when both
        return pickings are validated.

        Match criteria for adoption:
            - belongs to this return's sale order
            - picking_type_code == 'incoming' (= a return)
            - state != 'cancel' (cancelled returns shouldn't claim
              the goods; ``done`` returns ARE claimed because the
              physical receipt has happened — we only want to mark
              the link, not re-create or re-validate)
            - shopify_return_id is not set (truly manual / not yet linked)
            - has at least one move with origin_returned_move_id set
              (confirms it was created via stock.return.picking, not
              an inbound picking unrelated to a delivery)

        Returns:
            recordset of adopted ``stock.picking`` records (possibly empty).
        """
        self.ensure_one()
        order = self.sale_order_id
        if not order:
            return self.env['stock.picking']
        candidates = order.picking_ids.filtered(lambda p:
                                                p.picking_type_id
                                                and p.picking_type_id.code == 'incoming'
                                                and p.state != 'cancel'
                                                and not p.shopify_return_id
                                                and any(m.origin_returned_move_id for m in p.move_ids)
                                                )
        if not candidates:
            return self.env['stock.picking']
        candidates.write({
            'shopify_return_id': self.id,
            'mk_instance_id': self.mk_instance_id.id,
        })
        done_count = len(candidates.filtered(lambda p: p.state == 'done'))
        msg = _("Adopted %s manual return picking(s) (%s) already created in Odoo "
                "for this order %s already validated. Skipped creating a duplicate."
                ) % (len(candidates), ", ".join(candidates.mapped('name')), done_count)
        self.message_post(body=msg)
        self._log_to_queue('success', msg)
        return candidates

    def _trim_pickings_to_allowed_quantities(self, pickings):
        """
        Task: T8436 - Adjust return picking quantities to match what was restocked in Shopify.
        If a receipt was created for all returned items, but Shopify only restocked
        some of them (marking the rest damaged/discarded), this method reduces the
        Odoo move quantities so we don't over-restock inventory.
        If a picking is already validated ('done') with more units than allowed,
        it logs a warning message so the user can manually adjust their stock.
        Args:
            pickings (recordset): Recordset of stock.picking model to adjust.
        Returns:
            bool: True.
        """
        self.ensure_one()
        allowed_by_product = {}
        for so_line_id, qty in self._return_quantities_by_so_line().items():
            product = self.env['sale.order.line'].browse(so_line_id).product_id
            allowed_by_product[product.id] = allowed_by_product.get(product.id, 0) + qty

        for line in self.return_line_ids.filtered('force_restocked_qty'):
            product_id = line.sale_order_line_id.product_id.id
            if product_id:
                allowed_by_product[product_id] = allowed_by_product.get(product_id, 0) + int(line.force_restocked_qty)

        # Already-validated receipts consume the allowance first. Their stock has
        # moved and cannot be trimmed, so whatever is left over is what a still
        # pending receipt is allowed to take.
        over_received = []
        for picking in pickings.filtered(lambda p: p.state == 'done'):
            for move in picking.move_ids.filtered(lambda m: m.state == 'done'):
                received = move.quantity or move.product_uom_qty
                allowed = allowed_by_product.get(move.product_id.id, 0)
                allowed_by_product[move.product_id.id] = max(allowed - received, 0)
                if received > allowed:
                    over_received.append((picking.name, move.product_id.display_name, received, allowed))

        trimmed = []
        for picking in pickings.filtered(lambda p: p.state not in ('done', 'cancel')):
            for move in picking.move_ids.filtered(lambda m: m.state not in ('done', 'cancel')):
                allowed = allowed_by_product.get(move.product_id.id, 0)
                if allowed >= move.product_uom_qty:
                    allowed_by_product[move.product_id.id] = allowed - move.product_uom_qty
                    continue
                trimmed.append((move.product_id.display_name, move.product_uom_qty, allowed))
                if allowed <= 0:
                    move._action_cancel()
                else:
                    move.product_uom_qty = allowed
                    allowed_by_product[move.product_id.id] = 0

        if trimmed:
            msg = _("Updated return quantities to match what was restocked in Shopify: %s.") % ", ".join("%s (%s → %s)" % (name, was, now) for name, was, now in trimmed)
            self.message_post(body=msg)
            self._log_to_queue('success', msg)

        if over_received:
            details = ", ".join("%s (%s received in Odoo vs %s restocked in Shopify)" % (prod, got, allow) for pick, prod, got, allow in over_received)
            msg = _("⚠️ Stock Mismatch: More items were already received in Odoo than restocked in Shopify [%s]. Please manually move the extra units out of sellable stock.") % details
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
        return True

    def _validate_pending_return_pickings(self):
        """
        Validate any non-done pickings already linked to this return.
        Used when the return progresses ``OPEN → CLOSED`` and the picking
        was already created during the OPEN handler — only validation is
        still needed.
        Returns:
            recordset: Recordset of stock.picking model that was pending.
        """
        self.ensure_one()
        pending = self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        for picking in pending:
            self._force_validate_return_picking(picking)
        return pending

    def _cancel_pending_return_pickings(self, reason=None):
        """
        Cancel any waiting/ready pickings when the return is killed or
        closed without restock.

        Pickings already validated (state=done) are left alone — those
        represent real stock movements that should not be reversed
        automatically. Already-cancelled pickings are skipped.

        Args:
            reason: optional human-readable explanation for the chatter
                message. When omitted, falls back to "the Shopify return
                was set to <status>" (suits the CANCELED/DECLINED callers).
        Returns:
            recordset: Recordset of stock.picking model that was cancelled.
        """
        self.ensure_one()
        pending = self.picking_ids.filtered(lambda p: p.state not in ('done', 'cancel'))
        if not pending:
            return self.env['stock.picking']
        try:
            pending.action_cancel()
        except Exception as exc:
            _logger.warning(
                "Could not cancel pending Shopify return picking(s) %s: %s",
                pending.mapped('name'), exc,
            )
            msg = _("Auto-cancel of return picking(s) %s skipped: %s. "
                    "Please cancel manually.") % (", ".join(pending.mapped('name')), exc)
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
            return pending
        explanation = reason or _("the Shopify return was set to %s") % self.status
        msg = _("Cancelled %s pending return picking(s) because %s.") % (len(pending), explanation)
        self.message_post(body=msg)
        self._log_to_queue('success', msg)
        return pending

    def _force_validate_return_picking(self, picking):
        """
        Task: T8436 - Skip cancelled pickings as well as done ones, since trimming can cancel every move on a receipt.
        Force-validate a return picking by driving each move directly.
        For freshly created return pickings, moves can land in
        ``draft``/``confirmed``/``waiting`` state depending on whether
        the source picking was already done. We progressively move
        each one to ``done``:

            draft/waiting/confirmed → ``_action_confirm`` (idempotent)
            anything not assigned    → ``_action_assign(force_qty)``
            quantity not yet done    → ``_set_quantity_done(qty)``
            still not done           → ``_action_done()``

        If after the per-move loop the picking didn't auto-transition,
        we fall back to ``picking.button_validate()`` and auto-confirm
        any backorder / immediate-transfer wizard it returns.

        Wrapped in a savepoint — failures (lot/serial tracking, no
        stock) leave the picking in its current state; the outer
        status-update transaction is preserved. The actual exception
        message is recorded in chatter and the server log.
        """
        if picking.state in ('done', 'cancel'):
            return picking
        picking = picking.with_context(skip_inventory_sync_commit=True)
        try:
            with self.env.cr.savepoint():
                for move in picking.move_ids:
                    if move.state in ('done', 'cancel'):
                        continue
                    qty = move.product_uom_qty
                    if qty <= 0:
                        continue
                    if move.state in ('draft', 'waiting'):
                        move._action_confirm()
                    if move.state not in ('assigned', 'partially_available'):
                        move._action_assign(force_qty=qty)
                    move._set_quantity_done(qty)
                    move._action_done()

                # Per-move done usually transitions the picking; if not,
                # fall back to the standard validate path with auto
                # backorder/immediate-transfer handling.
                picking.invalidate_recordset(['state'])
                if picking.state != 'done':
                    res = picking.sudo().with_context(
                        skip_backorder=True,
                        picking_ids_not_to_backorder=picking.ids,
                    ).button_validate()
                    if isinstance(res, dict) and res.get('res_model') in (
                            'stock.backorder.confirmation', 'stock.immediate.transfer'
                    ):
                        wiz_ctx = dict(res.get('context') or {})
                        wiz_model = self.env[res['res_model']].sudo().with_context(wiz_ctx)
                        wiz = wiz_model.create({'pick_ids': [(4, picking.id)]})
                        if hasattr(wiz, 'process'):
                            wiz.process()
                        elif hasattr(wiz, 'action_confirm'):
                            wiz.action_confirm()
        except Exception as exc:
            _logger.warning(
                "Could not auto-validate Shopify return picking %s: %s",
                picking.name, exc, exc_info=True,
            )
            msg = _("Auto-validation skipped on %s: %s. Please validate this return picking manually.") % (picking.name, exc)
            picking.message_post(body=msg)
            self._log_to_queue('error', msg)
        return picking

    def _return_quantities_by_so_line(self, by_warehouse=False):
        """
        Task: T8438 - Optionally group the quantities by the warehouse that shipped them.
        Task: T8436 - Limit each line to the quantity Shopify actually restocked instead of the full return line quantity.
        Calculate return quantities per sale order line.

        Build a quantity map grouped by sale order line for use during return
        picking and stock move creation. The quantity included depends on the
        Shopify return status and restock dispositions:

        - Dispositions present: include only the quantity Shopify marked RESTOCKED,
          capped at the return line quantity (a line can be partially restocked).
        - CLOSED without any dispositions: exclude all lines.
        - Force Restock: include all return lines regardless of dispositions.

        Returns:
            dict: Mapping of sale.order.line ID to total return quantity.
        """
        self.ensure_one()
        force_restock = bool(self.env.context.get('force_restock_override'))
        # Only Force Restock bypasses dispositions. The old `status == 'OPEN'`
        # bypass applied to every return and is what caused over-restock on
        # partial dispositions.
        skip_disposition_check = force_restock
        restocked_by_gid = {} if force_restock else self._restocked_quantities_by_fulfillment_line_gid()
        payload_has_any_dispositions = False if force_restock else self.shopify_return_payload_has_any_dispositions()
        force_candidates = self._get_eligible_force_restock_qty_by_line() if force_restock else {}

        qty_by_so_line = {}
        for return_line in self.return_line_ids:
            line_qty = int(return_line.quantity or 0)
            if line_qty <= 0:
                continue
            if skip_disposition_check:
                line_qty = force_candidates.get(return_line.id, 0)
                if line_qty <= 0:
                    continue
            else:
                if not payload_has_any_dispositions:
                    continue
                # Shopify can restock part of a line: 3 returned, 1 restocked,
                # 2 discarded as damaged. Take only what Shopify actually put
                # back on the shelf, never the whole line.
                ful_gid = return_line.fulfillment_line_item_gid
                line_qty = min(line_qty, restocked_by_gid.get(ful_gid, 0) if ful_gid else 0)
                if line_qty <= 0:
                    continue
            so_line = return_line.sale_order_line_id
            if not so_line:
                continue
            key = (so_line.id, self._fulfilled_warehouse_id_for_line(return_line)) if by_warehouse else so_line.id
            qty_by_so_line[key] = qty_by_so_line.get(key, 0) + line_qty
        return qty_by_so_line

    def _return_quantities_against_picking(self, source_picking, remaining_qty_by_so_line, allocations=None):
        """
        Calculate return quantities for a specific delivery picking.

        Determine how much quantity should be returned against the given source
        picking based on the remaining return quantity per sale order line and
        the quantities originally fulfilled from the picking's warehouse.

        The method allocates return quantities warehouse-wise and updates the
        remaining quantities so they are not assigned again to other pickings.
        Args:
            source_picking (recordset): Recordset of stock.picking model (the source delivery).
            remaining_qty_by_so_line (dict): Remaining return quantity grouped by sale order line.
            allocations (list): Optional, appended with (sale order line ID, product recordset,
                                quantity) tuples so the caller can group by restock destination.
        Returns:
            dict: Mapping of product.product records to return quantities.
        """
        self.ensure_one()
        qty_by_product = {}
        picking_warehouse = source_picking.picking_type_id.warehouse_id or source_picking.location_id.warehouse_id
        if not picking_warehouse:
            return qty_by_product
        shopify_location_obj = self.env['shopify.location.ts']
        so_line_to_product = {m.sale_line_id.id: m.product_id for m in source_picking.move_ids if m.sale_line_id}

        for so_line_id, refund_remaining in list(remaining_qty_by_so_line.items()):
            if refund_remaining <= 0 or so_line_id not in so_line_to_product:
                continue
            so_line = self.env['sale.order.line'].browse(so_line_id)
            splits = so_line._get_shopify_fulfillment_splits('fulfilled')
            if splits:
                shipped_from_here = sum(int(s.get('qty') or 0) for s in splits if shopify_location_obj.browse(s.get('shopify_location_record_id')).order_warehouse_id == picking_warehouse)
            else:
                legacy_move = source_picking.move_ids.filtered(lambda m: m.sale_line_id == so_line)[:1]
                shipped_from_here = int(legacy_move.product_uom_qty or 0) if legacy_move else 0

            take = min(refund_remaining, shipped_from_here)
            product = so_line_to_product[so_line_id]
            qty_by_product[product] = qty_by_product.get(product, 0) + take
            if allocations is not None:
                allocations.append((so_line_id, product, take))
            remaining_qty_by_so_line[so_line_id] = refund_remaining - take
        return qty_by_product

    def _split_qty_by_restock_destination(self, source_picking, allocations, exclude_received=False):
        """
        Task: T8437 - Group return allocations by target Odoo stock locations.
        Splits stock quantities across multiple destination locations if Shopify restocked
        items into different warehouses, falling back to default picking locations when unspecified.
        Args:
            source_picking (recordset): Source stock.picking record (outgoing delivery).
            allocations (list): Tuples of (sale_order_line_id, product_record, quantity).
            exclude_received (bool): Whether to exclude quantities already received in Odoo when calculating the Shopify restock destination quantities.
        Returns:
            dict: stock.location record -> {product_record: quantity}.
        """
        self.ensure_one()
        warehouse = source_picking.picking_type_id.warehouse_id or source_picking.location_id.warehouse_id
        fallback_location = self._resolve_restock_stock_location_for_picking(source_picking)
        by_destination = {}
        for so_line_id, product, qty in allocations:
            if qty <= 0:
                continue
            remaining = qty
            for location, split_qty in ((warehouse and self._disposition_restock_location(warehouse, so_line_id, exclude_received)) or {fallback_location: qty}).items():
                if not location:
                    continue
                take = min(split_qty, remaining)
                if take <= 0:
                    break
                remaining -= take
                subset = by_destination.setdefault(location, {})
                subset[product] = subset.get(product, 0) + take
        return by_destination

    def _invoke_native_shopify_return_wizard(self, source_picking, qty_by_product, target_location):
        """
        Create a return picking using Odoo's standard return wizard.
        The wizard's compute pre-fills ``product_return_moves`` with one row
        per move. We override the ``quantity`` on rows we want to return, then
        zero-out the rest. The wizard's own ``action_create_returns`` is then
        called — that is the public API documented for stock-return integration.
        Args:
            source_picking (recordset): Original delivery picking.
            qty_by_product (dict): Return quantity per product.
            target_location (recordset): Destination stock location for the return.
        Returns:
            recordset | bool: Created return picking, or False if no return is created.
        """
        wiz_obj = self.env['stock.return.picking']
        wiz = wiz_obj.with_context(
            active_id=source_picking.id,
            active_ids=[source_picking.id],
            active_model='stock.picking',
        ).create({'picking_id': source_picking.id})

        any_qty_set = False
        for line in wiz.product_return_moves:
            qty = qty_by_product.get(line.product_id, 0)
            if qty > 0:
                line.quantity = qty
                any_qty_set = True
            else:
                line.quantity = 0
        if not any_qty_set:
            return False

        action = wiz.action_create_returns()
        new_picking_id = action.get('res_id') if isinstance(action, dict) else False
        if not new_picking_id:
            return False
        new_picking = self.env['stock.picking'].browse(new_picking_id)

        if target_location and new_picking.location_dest_id != target_location:
            try:
                new_picking.write({'location_dest_id': target_location.id})
                new_picking.move_ids.write({'location_dest_id': target_location.id})
                new_picking.move_ids.move_line_ids.write({'location_dest_id': target_location.id})
            except Exception as exc:
                _logger.warning(f"Could not redirect Shopify return picking {new_picking.name} to {target_location.display_name}: {exc}")
        return new_picking

    def _disposition_restock_location(self, warehouse, so_line_id=False, exclude_received=False):
        """
        Task: T8437 - Identify Odoo restock locations based on Shopify RESTOCKED dispositions.
        Parses reverse fulfillment order dispositions to map restocked quantities to mapped Odoo stock locations.
        Args:
            warehouse (recordset): Target stock.warehouse record to scope the return lines.
            so_line_id (int, optional): Specific sale order line ID to narrow down calculation.
            exclude_received (bool, optional): Leave out what this return already received in each location for the sale line.
        Returns:
            dict: stock.location record -> restocked quantity.
        """
        self.ensure_one()
        if not warehouse:
            return {}
        try:
            payload = ast.literal_eval(self.shopify_payload_json or '{}')
        except Exception:
            return {}
        scoped_gids = {line.fulfillment_line_item_gid for line in self.return_line_ids
                       if line.fulfillment_line_item_gid
                       and self._fulfilled_warehouse_id_for_line(line) == warehouse.id
                       and (not so_line_id or line.sale_order_line_id.id == so_line_id)}
        # Keep the quantity beside each location: Shopify can split one line's units across several locations, which a single destination cannot represent.
        qty_by_location_gid = {}
        for rfo_node in ((payload.get('reverseFulfillmentOrders') or {}).get('nodes') or []):
            for rfo_line in ((rfo_node.get('lineItems') or {}).get('nodes') or []):
                if (rfo_line.get('fulfillmentLineItem') or {}).get('id') not in scoped_gids:
                    continue
                for disposition in (rfo_line.get('dispositions') or []):
                    location_gid = (disposition.get('location') or {}).get('id')
                    quantity = int(disposition.get('quantity') or 0)
                    if disposition.get('type') == 'RESTOCKED' and location_gid and quantity > 0:
                        qty_by_location_gid[location_gid] = qty_by_location_gid.get(location_gid, 0) + quantity

        quantity_by_location = {}
        for location_gid, quantity in qty_by_location_gid.items():
            shopify_location = self.env['shopify.location.ts'].search([
                ('mk_instance_id', '=', self.mk_instance_id.id),
                ('shopify_location_id', '=', str(extract_numeric_id(location_gid) or '')),
            ], limit=1)
            location = shopify_location and (
                shopify_location.restock_warehouse_id.lot_stock_id
                or shopify_location.location_id
                or shopify_location.order_warehouse_id.lot_stock_id
            )
            if location:
                quantity_by_location[location] = quantity_by_location.get(location, 0) + quantity
        if exclude_received and so_line_id and quantity_by_location:
            for move in (self.picking_ids.move_ids | self.return_move_ids).filtered(lambda m: m.state == 'done' and m.sale_line_id.id == so_line_id):
                if move.location_dest_id in quantity_by_location:
                    quantity_by_location[move.location_dest_id] -= int(move.quantity or 0)
            quantity_by_location = {location: qty for location, qty in quantity_by_location.items() if qty > 0} or {False: 0}
        return quantity_by_location

    def _resolve_restock_stock_location_for_picking(self, source_picking):
        """
        Get the restock location for a return picking.
        Mirrors the fulfillment-side priority used in ``_get_move_raw_values_ts``:
            1. The ``shopify.location.ts`` mapped to the picking's warehouse:
               ``restock_warehouse_id.lot_stock_id`` → ``location_id`` →
               ``order_warehouse_id.lot_stock_id``
            2. Picking warehouse's ``lot_stock_id`` (fallback)
        Args:
            source_picking (recordset): Original delivery picking.
        Returns:
            recordset | bool: Restock location or False.
        """
        self.ensure_one()
        warehouse = source_picking.picking_type_id.warehouse_id or source_picking.location_id.warehouse_id
        if not warehouse:
            return False

        disposition_locations = self._disposition_restock_location(warehouse)
        if len(disposition_locations) == 1:
            return next(iter(disposition_locations))

        pinned_location = self.restock_shopify_location_id
        if pinned_location:
            return (pinned_location.restock_warehouse_id.lot_stock_id or pinned_location.location_id
                    or pinned_location.order_warehouse_id.lot_stock_id or warehouse.lot_stock_id)
        shopify_location = self.env['shopify.location.ts'].search([
            ('order_warehouse_id', '=', warehouse.id),
            ('mk_instance_id', '=', self.mk_instance_id.id),
        ], limit=1)
        if shopify_location:
            return (
                    shopify_location.restock_warehouse_id.lot_stock_id
                    or shopify_location.location_id
                    or shopify_location.order_warehouse_id.lot_stock_id
            )
        return warehouse.lot_stock_id

    def _link_existing_credit_notes(self):
        """
        Link related credit notes to the Shopify return.
        Find existing Odoo credit notes created from Shopify refunds and link
        them to the current Shopify return record. This method only creates the
        relationship and does not generate or modify any accounting entries.
        Returns:
            recordset | bool: Linked credit notes, or False if none are found.
        """
        self.ensure_one()
        self = self.sudo()
        if not self.shopify_payload_json:
            return False
        try:
            payload = ast.literal_eval(self.shopify_payload_json)
        except Exception:
            return False
        refund_gids = []
        for refund_node in (((payload or {}).get('refunds') or {}).get('nodes') or []):
            gid = refund_node.get('id')
            if gid:
                refund_gids.append(extract_numeric_id(gid))
        if not refund_gids:
            return False
        refund_strs = [str(rid) for rid in refund_gids if rid]
        credit_notes = self.env['account.move'].search([
            ('shopify_refund_id', 'in', refund_strs),
            ('move_type', '=', 'out_refund'),
        ])
        if credit_notes:
            credit_notes.write({'shopify_return_id': self.id})
        return credit_notes

    def _ensure_credit_notes_from_shopify_return_payload(self):
        """
        Create missing credit notes from Shopify return refunds.
        Check the refunds available in the stored Shopify return payload and
        create the corresponding Odoo credit notes if they do not already exist.
        Uses the standard Shopify refund import flow to keep refund processing consistent with order synchronization.
        Returns:
            bool: True if processed successfully, otherwise False.
        """
        self.ensure_one()
        self = self.sudo()
        if not self.sale_order_id or not self.shopify_payload_json:
            return False
        try:
            payload = ast.literal_eval(self.shopify_payload_json)
        except Exception:
            return False
        if (payload or {}).get(SHOPIFY_PARTIAL_RETURN_PAYLOAD_KEY):
            return False
        refunds = ((payload or {}).get('refunds') or {}).get('nodes') or []
        if not refunds:
            return False

        # Build a minimal shopify_order_dict for the refund pipeline.
        # _create_shopify_credit_note iterates the 'refunds' key and dedupes
        # internally on shopify_refund_id, so a thin wrapper is enough.
        shopify_order_dict = {
            'name': self.sale_order_id.name,
            'taxesIncluded': (payload.get('order') or {}).get('taxesIncluded') or False,
            'refunds': refunds,
        }
        try:
            self.sale_order_id.with_context(
                skip_check_transaction=True,
                credit_note_log_prefix='PROCESS RETURN',
            )._create_shopify_credit_note(shopify_order_dict)

        except Exception as exc:
            log_traceback_for_exception()
            msg = _("Auto credit-note creation from return payload failed: %s. "
                    "Trigger the refund sync from the order if needed.") % exc
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
            return False
        return True

    # ------------------------------------------------------------------
    # Smart-button actions
    # ------------------------------------------------------------------

    def action_view_pickings(self):
        """
         Display the stock pickings linked to this Shopify return.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Pickings'),
            'res_model': 'stock.picking',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.picking_ids.ids)],
        }

    def action_view_return_moves(self):
        """ Display the stock moves created for this Shopify return."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Stock Moves'),
            'res_model': 'stock.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.return_move_ids.ids)],
        }

    def action_view_credit_notes(self):
        """Display the credit notes associated with this Shopify return."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Linked Credit Notes'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.credit_note_ids.ids)],
        }

    # ------------------------------------------------------------------
    # Status-transition mutations (Phase 3)
    # ------------------------------------------------------------------

    def action_approve_shopify_return_request(self):
        """
        Approve a Shopify return request.
        Approve the selected Shopify return request and update the return status in Odoo based on Shopify's response.
        """
        self = self.sudo()
        for record in self:
            if record.mk_instance_id.state != 'confirmed':
                raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % record.mk_instance_id.name)
            if record.status != 'REQUESTED':
                raise MarketplaceException(_(f"Only REQUESTED returns can be approved. Current status: {record.status}."))
            record.mk_instance_id.connection_to_shopify()
            variables = {"input": {"id": record._build_shopify_return_gid()}}
            response = record.mk_instance_id.execute_graphql_query(RETURN_REQUEST_APPROVE_FROM_ODOO, variables)
            self._raise_on_top_level_errors(response, "approve return request")
            self._raise_on_user_errors(response, 'returnApproveRequest', "approve return request")
            new_status = (((response or {}).get('data') or {}).get('returnApproveRequest') or {}).get('return', {}).get('status') or 'OPEN'
            record.write({'status': new_status})
        return True

    def action_decline_shopify_return_request(self):
        """
        Decline a Shopify return request.
        Decline the selected Shopify return request in Shopify and update the return status in Odoo.
        """
        self = self.sudo()
        for record in self:
            if record.mk_instance_id.state != 'confirmed':
                raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % record.mk_instance_id.name)
            if record.status != 'REQUESTED':
                raise MarketplaceException(_(f"Only REQUESTED returns can be declined. Current status: {record.status}."))
            record.mk_instance_id.connection_to_shopify()
            variables = {"input": {"id": record._build_shopify_return_gid(), "declineReason": "OTHER"}}
            response = record.mk_instance_id.execute_graphql_query(RETURN_REQUEST_DECLINE_FROM_ODOO, variables)
            self._raise_on_top_level_errors(response, "decline return request")
            self._raise_on_user_errors(response, 'returnDeclineRequest', "decline return request")
            record.write({'status': 'DECLINED'})
        return True

    def action_cancel(self):
        """
        Task: T8436 - Allow cancelling only OPEN returns, since Shopify requires a requested return to be declined.
        Cancel an open Shopify return and synchronize the updated status back to Odoo.
        """
        self = self.sudo()
        for record in self:
            if record.mk_instance_id.state != 'confirmed':
                raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % record.mk_instance_id.name)
            if record.status != 'OPEN':
                raise MarketplaceException(_("Only OPEN returns can be canceled. Current status: %s. A requested return must be declined instead.") % record.status)
            record.mk_instance_id.connection_to_shopify()
            variables = {"id": record._build_shopify_return_gid()}
            response = record.mk_instance_id.execute_graphql_query(RETURN_CANCEL_FROM_ODOO, variables)
            self._raise_on_top_level_errors(response, "cancel return")
            self._raise_on_user_errors(response, 'returnCancel', "cancel return")
            record.write({'status': 'CANCELED'})
        return True

    def action_process_shopify_return(self, return_line_inputs=None):
        """
        Task: T8436 - Verify the source delivery without creating inventory, and dispatch the status side effects after a partial process.
        Process an open Shopify return.
        Process the return in Shopify using the available return quantities,
        synchronize the latest return data, and update the Odoo return record.
        If all return lines are already processed in Shopify, the method exits
        without raising an error.
        Args:
            return_line_inputs (list, optional): Return line data to send to Shopify. If not provided, the inputs are generated from the latest
            Shopify return information.
        Returns:
            bool: True if the operation completes successfully.
        """
        self.ensure_one()
        self = self.sudo()
        if self.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % self.mk_instance_id.name)
        if self.status != 'OPEN':
            raise MarketplaceException(_(f"Only OPEN returns can be processed. Current status: {self.status}."))

        has_active_inventory = bool(
            self.picking_ids.filtered(lambda p: p.state != 'cancel')
            or self.return_move_ids.filtered(lambda m: m.state != 'cancel')
        )

        if not has_active_inventory:
            order = self.sale_order_id
            outgoing = order and order.picking_ids.filtered(
                lambda p: p.picking_type_id and p.picking_type_id.code == 'outgoing'
            )
            has_orphan_moves = bool(order and self._get_outgoing_orphan_moves())

            if not outgoing and not has_orphan_moves:
                raise MarketplaceException(_(
                    "Cannot process this return: no delivery exists in Odoo for these items. "
                    "Create and validate the delivery order before processing the return."
                ))

            if outgoing and not outgoing.filtered(lambda p: p.state == 'done') and not has_orphan_moves:
                raise MarketplaceException(_(
                    "Cannot process this return: the related delivery order is not validated yet. "
                    "Validate the delivery order before processing the return."
                ))

        self.mk_instance_id.connection_to_shopify()

        # Resync local lines before computing inputs so refundable_quantity
        # reflects the latest Shopify state (covers re-runs after a partial
        # or complete prior process).
        if not return_line_inputs:
            try:
                payload = self._fetch_shopify_return_details(self.mk_instance_id, self._build_shopify_return_gid())
                if payload:
                    self._upsert_shopify_return_from_payload(self.mk_instance_id, payload)
            except Exception as exc:
                _logger.warning(
                    "Pre-process refresh failed for return %s: %s",
                    self.shopify_return_id, exc,
                )
            return_line_inputs = self._build_default_shopify_return_process_line_inputs()

        # All lines already fully processed Shopify-side — nothing to do.
        # Treat as success so the wizard can still proceed to Close.
        if not return_line_inputs:
            self.message_post(body=_(
                "Skipped returnProcess all return lines are already fully "
                "processed on Shopify. Proceeding to close if requested."
            ))
            return True

        process_input = {
            "returnId": self._build_shopify_return_gid(),
            "returnLineItems": return_line_inputs,
        }
        variables = {"input": process_input}
        response = self.mk_instance_id.execute_graphql_query(RETURN_PROCESS_FROM_ODOO, variables)
        self._raise_on_top_level_errors(response, "process return")
        self._raise_on_user_errors(response, 'returnProcess', "process return")
        processed_return = (((response or {}).get('data') or {}).get('returnProcess') or {}).get('return') or {}
        if processed_return:
            if not (processed_return.get('order') or {}).get('fulfillments'):
                try:
                    stored_fulfillments = ((ast.literal_eval(self.shopify_payload_json or '{}') or {}).get('order') or {}).get('fulfillments')
                except Exception:
                    stored_fulfillments = None
                if stored_fulfillments:
                    processed_return['order'] = dict(processed_return.get('order') or {}, fulfillments=stored_fulfillments)
            self._upsert_shopify_return_from_payload(self.mk_instance_id, processed_return)
            self._apply_shopify_return_status_side_effects()
        return True

    def _build_default_shopify_return_process_line_inputs(self):
        """
        Prepare default return process inputs.
        Build the return line payload used for Shopify's returnProcess mutation.
        The payload includes the return quantities and restock disposition details
        so Shopify can process the return and restock the items to the appropriate
        fulfillment location.
        Returns:
            list: Return line inputs formatted for the Shopify returnProcess API.
        """
        self.ensure_one()
        inputs, not_restockable = [], []
        for line in self.return_line_ids:
            if not line.shopify_return_line_id:
                continue
            qty = line.refundable_quantity or max((line.quantity or 0) - (line.refunded_quantity or 0), 0)
            if qty <= 0:
                continue
            line_input = {
                "id": f"gid://shopify/ReturnLineItem/{line.shopify_return_line_id}",
                "quantity": int(qty),
            }
            if line.reverse_fulfillment_line_id and not line.shopify_variant_id:
                not_restockable.append(line.title or line.sku or line.shopify_return_line_id)
            elif line.reverse_fulfillment_line_id:
                location_gid = (self.restock_shopify_location_id.shopify_location_id
                                and f"gid://shopify/Location/{self.restock_shopify_location_id.shopify_location_id}") \
                               or self._resolve_line_fulfilled_location_gid(line)
                if not location_gid:
                    raise MarketplaceException(_(
                        "Cannot process return %(name)s: the fulfillment location for %(line)s could not be "
                        "determined. Set a Restock Location on this return and try again."
                    ) % {'name': self.name or '', 'line': line.title or line.sku or line.shopify_return_line_id})
                line_input["dispositions"] = [{
                    "reverseFulfillmentOrderLineItemId": line.reverse_fulfillment_line_id,
                    "quantity": int(qty),
                    "dispositionType": "RESTOCKED",
                    "locationId": location_gid,
                }]
            inputs.append(line_input)

        if not_restockable and any('dispositions' in line_input for line_input in inputs):
            msg = _(
                "Return processed without restocking the following line(s): %s. "
                "The Shopify product variant is no longer available, so these items could "
                "not be restocked in Shopify. If the items were physically returned, "
                "use Force Restock in Odoo."
            ) % ", ".join(not_restockable)
            self.message_post(body=msg)
            self._log_to_queue('success', msg)
        return inputs

    def _resolve_line_fulfilled_location_gid(self, line):
        """
        Resolve a line's restock location GID = its original fulfillment location.
        Read from the saved payload's ``order.fulfillments`` by matching the
        line's fulfillment line item.
        Args:
            line (recordset): Recordset of shopify.return.line.ts model.
        Returns:
            str/bool: The fulfilled location GID, or False if not found.
        """
        if not (line.fulfillment_line_item_gid and self.shopify_payload_json):
            return False
        try:
            payload_data = ast.literal_eval(self.shopify_payload_json)
        except Exception:
            return False

        fulfillments = ((payload_data or {}).get('order') or {}).get('fulfillments') or []
        for fulfillment_data in fulfillments:
            fulfillment_line_item_gids = {
                fulfillment_line.get('id')
                for fulfillment_line in (fulfillment_data.get('fulfillmentLineItems') or [])
            }

            if line.fulfillment_line_item_gid in fulfillment_line_item_gids:
                fulfilled_location_gid = (fulfillment_data.get('location') or {}).get('id')
                if fulfilled_location_gid:
                    return fulfilled_location_gid

        return False

    def _fulfilled_warehouse_id_for_line(self, return_line):
        """
        Task: T8438 - Warehouse that actually fulfilled this return line.
        Shopify ties each return line to one fulfillment, and a fulfillment has exactly
        one location. Reuses ``_resolve_line_fulfilled_location_gid`` — the same resolver
        already used when pushing dispositions — so both directions agree on the origin.
        Args:
            return_line (recordset): Recordset of shopify.return.line.ts model.
        Returns:
            int | bool: stock.warehouse ID, or False when the location cannot be resolved.
        """
        gid = self._resolve_line_fulfilled_location_gid(return_line)
        if not gid:
            return False
        loc = self.env['shopify.location.ts'].search([
            ('mk_instance_id', '=', self.mk_instance_id.id),
            ('shopify_location_id', '=', str(extract_numeric_id(gid) or '')),
        ], limit=1)
        return loc.order_warehouse_id.id or False

    def action_close_shopify_return(self):
        """
        Close an OPEN return in Shopify and synchronize the updated status in Odoo.
        Returns:
            bool: True.
        """
        self = self.sudo()
        for record in self:
            if record.mk_instance_id.state != 'confirmed':
                raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % record.mk_instance_id.name)
            if record.status not in ('OPEN',):
                raise MarketplaceException(_(f"Only OPEN returns can be closed. Current status: {record.status}."))
            record.mk_instance_id.connection_to_shopify()
            variables = {"id": record._build_shopify_return_gid()}
            response = record.mk_instance_id.execute_graphql_query(RETURN_CLOSE_FROM_ODOO, variables)
            self._raise_on_top_level_errors(response, "close return")
            self._raise_on_user_errors(response, 'returnClose', "close return")
            record.write({'status': 'CLOSED'})
        return True

    def action_open_shopify_return_process_wizard(self):
        """
        Launch the wizard used to process and optionally close a Shopify return.
        Returns:
            dict: Odoo action to open the wizard.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Process Shopify Return'),
            'res_model': 'shopify.return.process.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_return_id': self.id},
        }

    def action_resync_shopify_return_from_shopify(self):
        """Refetch this single return from Shopify and re-upsert header + lines.

        Useful after a schema or sync code change — bypasses the queue and
        cron, calls the GraphQL fetch directly, and writes back into this
        record. Does not trigger any side effects beyond the standard ones
        applied for the resulting status.
        Returns:
            dict: A client notification action.
        Raises:
            MarketplaceException: If the return has no instance, or Shopify returns no data.
        """
        self.ensure_one()
        self = self.sudo()
        if not self.mk_instance_id:
            raise MarketplaceException(_("This return is not linked to a Shopify instance."))
        if self.mk_instance_id.state != 'confirmed':
            raise MarketplaceException(_("The Shopify instance '%s' is not confirmed.") % self.mk_instance_id.name)
        self.mk_instance_id.connection_to_shopify()
        payload = self._fetch_shopify_return_details(self.mk_instance_id, self._build_shopify_return_gid())
        if not payload:
            raise MarketplaceException(_(
                "Shopify returned no data for this return. The return may have "
                "been deleted on Shopify, or the Shopify account no longer has "
                "access to it."
            ))
        self._upsert_shopify_return_from_payload(self.mk_instance_id, payload)
        self._apply_shopify_return_status_side_effects()
        node_count = len(((payload.get('returnLineItems') or {}).get('nodes') or []))
        line_count = len(self.return_line_ids)
        _logger.info(
            "Shopify return resync: return=%s nodes_in_payload=%s lines_after_sync=%s",
            self.shopify_return_id, node_count, line_count,
        )
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success' if line_count else 'warning',
                'title': _("Shopify Return Resync"),
                'message': _("Fetched %s line(s) from Shopify; %s line(s) now stored locally.")
                           % (node_count, line_count),
                'sticky': False,
                'next': {'type': 'ir.actions.client', 'tag': 'reload'},
            },
        }

    def action_force_restock(self):
        """
        Manually create the return picking/moves even though Shopify reported no restock.
        Use when goods physically came back but the merchant didn't tick 'Restock' on Shopify.
        Returns:
            bool: Retuens True.
        Raises:
            MarketplaceException: If Shopify restocked everything already, the order has nothing to reverse, or nothing could be created.
        """
        self.ensure_one()
        self = self.sudo()
        candidates = self._get_eligible_force_restock_qty_by_line()
        if not candidates:
            raise MarketplaceException(_("Nothing to force restock: All unrestocked items are already back in Odoo stock."))

        order = self.sale_order_id
        has_source_picking = bool(order and order.picking_ids.filtered(
            lambda p: p.state == 'done' and p.picking_type_id and p.picking_type_id.code == 'outgoing'
        ))
        has_orphan_moves = bool(order and self._get_outgoing_orphan_moves())

        if not has_source_picking and not has_orphan_moves:
            raise MarketplaceException(_("Cannot force restock: no source delivery or stock moves found to process the return."))
        restocked_before = self._restocked_quantity_by_so_line()

        if has_source_picking:
            self.with_context(force_restock_override=True)._ensure_return_picking_via_native_wizard(validate=True)
            self.with_context(force_restock_override=True)._validate_pending_return_pickings()
        if has_orphan_moves:
            self.with_context(force_restock_override=True)._create_pending_shopify_return_moves(validate=True)
            self.with_context(force_restock_override=True)._validate_pending_shopify_return_moves()

        restocked_after = self._restocked_quantity_by_so_line()
        gained = {}
        for so_line_id in set(restocked_before) | set(restocked_after):
            delta = restocked_after.get(so_line_id, 0) - restocked_before.get(so_line_id, 0)
            if delta > 0:
                gained[so_line_id] = delta
        if not gained:
            raise MarketplaceException(_("Force restock failed: No return pickings or inventory updates were generated."))

        for line in self.return_line_ids:
            wanted = candidates.get(line.id, 0)
            available = gained.get(line.sale_order_line_id.id, 0)
            if wanted <= 0 or available <= 0:
                continue
            take = min(wanted, available)
            gained[line.sale_order_line_id.id] = available - take
            line.force_restocked_qty = int(line.force_restocked_qty or 0) + take
        msg = _("Force Restock was applied manually. The items were restocked in Odoo even though Shopify did not mark the return as restocked.")
        self.message_post(body=msg)
        self._log_to_queue('success', msg)
        return True

    # ------------------------------------------------------------------
    # Misc
    # ------------------------------------------------------------------

    def _build_shopify_return_gid(self):
        """
        Build the Shopify Return GID from the stored numeric id.
        Returns:
            str: The Return GID.
        Raises:
            MarketplaceException: If the return has no Shopify ID.
        """
        self.ensure_one()
        if not self.shopify_return_id:
            raise MarketplaceException(_("Return has no Shopify ID."))
        return f"gid://shopify/Return/{self.shopify_return_id}"

    def _get_outgoing_orphan_moves(self):
        """
        Return done outgoing stock.moves on the source order that are not attached to any picking (fulfilled-shortcut delivery).
        Returns:
            recordset: Recordset of stock.move model (may be empty).
        """
        self.ensure_one()
        if not self.sale_order_id:
            return self.env['stock.move']
        return self.env['stock.move'].search([
            ('sale_line_id', 'in', self.sale_order_id.order_line.ids),
            ('picking_id', '=', False),
            ('location_dest_id.usage', '=', 'customer'),
        ])

    def _resolve_restock_stock_location_for_warehouse(self, warehouse, so_line_id=False):
        """
        Resolve the Odoo target stock location for return inventory.
        Checks dispositions, pinned restock locations, or defaults to the warehouse stock location.
        Args:
            warehouse (recordset): Target warehouse for return moves.
            so_line_id (int, optional): Specific sale order line ID.
        Returns:
            recordset/bool: stock.location record, or False if no warehouse provided.
        """
        self.ensure_one()
        if not warehouse:
            return False
        disposition_locations = self._disposition_restock_location(warehouse, so_line_id)
        if len(disposition_locations) == 1:
            return next(iter(disposition_locations))
        pinned_location = self.restock_shopify_location_id
        if pinned_location:
            return (pinned_location.restock_warehouse_id.lot_stock_id or pinned_location.location_id
                    or pinned_location.order_warehouse_id.lot_stock_id or warehouse.lot_stock_id)
        shopify_location = self.env['shopify.location.ts'].search([
            ('order_warehouse_id', '=', warehouse.id),
            ('mk_instance_id', '=', self.mk_instance_id.id),
        ], limit=1)
        if shopify_location:
            return (
                    shopify_location.restock_warehouse_id.lot_stock_id
                    or shopify_location.location_id
                    or shopify_location.order_warehouse_id.lot_stock_id
            )
        return warehouse.lot_stock_id

    def _create_pending_shopify_return_moves(self, validate=False):
        """
        Task: T8438 - Fixed return stock moves to use the correct warehouse when an order line is shipped from multiple locations.
        Create reverse stock.moves for this Shopify return when the
        source order has no return picking (fulfilled-shortcut case).

        Idempotent — bails out if non-cancelled return moves are already
        linked. Honours Shopify dispositions the same way the picking
        flow does (see ``_return_quantities_against_picking``):

          - status OPEN or force-restock context: include every return line
          - status CLOSED with dispositions in payload: include only RESTOCKED
          - status CLOSED without dispositions: include nothing
            (caller flags the return as restock-skipped instead)

        Args:
            validate: when True, marks the new moves done so inventory updates immediately.
        Returns:
            recordset: Recordset of stock.move model that was created.
        """
        self.ensure_one()
        existing_moves = self.return_move_ids.filtered(lambda m: m.state != 'cancel')
        missing_qty_by_so_line = {}
        if existing_moves and not self.env.context.get('force_restock_override'):
            if validate:
                self._validate_pending_shopify_return_moves()

            so_lines = self.return_line_ids.sale_order_line_id
            if not (self.return_move_ids.filtered(lambda m: m.state != 'done' or not m.sale_line_id or m.product_uom.compare(m.quantity, m.product_uom_qty) < 0)
                    or self.sale_order_id.picking_ids.filtered(lambda p: p.state == 'done' and p.picking_type_id.code == 'outgoing')
                    or self.env['stock.move'].search_count([
                        ('sale_line_id', 'in', self.sale_order_id.order_line.ids), ('picking_id', '=', False), ('state', '!=', 'cancel'),
                        ('origin_returned_move_id', '!=', False), ('shopify_return_id', '=', False), ('product_id', 'in', so_lines.move_ids.product_id.ids)])
                    or any(len(line.move_ids.filtered(lambda m: m.state == 'done' and m.location_dest_id.usage == 'customer').location_id.warehouse_id) > 1 for line in so_lines)):
                received = self._restocked_quantity_by_so_line()
                for key, qty in self._return_quantities_by_so_line(by_warehouse=True).items():
                    used = min(qty, received.get(key[0], 0))
                    received[key[0]] = received.get(key[0], 0) - used
                    if qty > used:
                        missing_qty_by_so_line[key] = qty - used
            if not missing_qty_by_so_line:
                return existing_moves

        order = self.sale_order_id
        if not order:
            msg = _("Cannot create return moves: no Odoo sale order linked to this return.")
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
            return self.env['stock.move']

        source_moves = self._get_outgoing_orphan_moves()
        if not source_moves:
            msg = _("Cannot create return moves: no done outgoing stock moves found on the order.")
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
            return self.env['stock.move']

        remaining_qty_by_so_line = missing_qty_by_so_line or self._return_quantities_by_so_line(by_warehouse=True)
        if not remaining_qty_by_so_line:
            return self.env['stock.move']

        shopify_location_obj = self.env['shopify.location.ts']
        created_moves = self.env['stock.move']

        for warehouse in source_moves.mapped('location_id.warehouse_id'):
            moves_in_warehouse = source_moves.filtered(lambda m: m.location_id.warehouse_id == warehouse)
            for (so_line_id, fulfilled_wh_id), refund_remaining in list(remaining_qty_by_so_line.items()):
                if refund_remaining <= 0:
                    continue
                if fulfilled_wh_id and fulfilled_wh_id != warehouse.id:
                    continue
                target_location = self._resolve_restock_stock_location_for_warehouse(warehouse, so_line_id)
                if not target_location:
                    continue
                so_line = self.env['sale.order.line'].browse(so_line_id)
                if not so_line.exists():
                    continue
                splits = so_line._get_shopify_fulfillment_splits('fulfilled')
                if splits:
                    shipped_from_here = sum(
                        int(s.get('qty') or 0) for s in splits
                        if shopify_location_obj.browse(s.get('shopify_location_record_id')).order_warehouse_id == warehouse
                    )
                else:
                    legacy_move = moves_in_warehouse.filtered(lambda m: m.sale_line_id == so_line)[:1]
                    shipped_from_here = int(legacy_move.product_uom_qty or 0) if legacy_move else 0
                if shipped_from_here <= 0:
                    continue
                take = min(refund_remaining, shipped_from_here)
                source_move = moves_in_warehouse.filtered(lambda m: m.sale_line_id == so_line)[:1]
                if not source_move:
                    continue
                remaining = take
                for destination, split_qty in (self._disposition_restock_location(warehouse, so_line_id, bool(missing_qty_by_so_line)) or {target_location: take}).items():
                    qty = min(split_qty, remaining)
                    if qty <= 0:
                        break
                    remaining -= qty
                    new_move = source_move.copy({
                        'picking_id': False,
                        'product_uom_qty': qty,
                        'location_id': source_move.location_dest_id.id,
                        'location_dest_id': destination.id,
                        'origin_returned_move_id': source_move.id,
                        'shopify_return_id': self.id,
                        'state': 'draft',
                        'procure_method': 'make_to_stock',
                    })
                    new_move._action_confirm()
                    created_moves |= new_move
                remaining_qty_by_so_line[(so_line_id, fulfilled_wh_id)] = refund_remaining - take

        if missing_qty_by_so_line and not created_moves:
            return existing_moves
        leftover = sum(qty for qty in remaining_qty_by_so_line.values() if qty > 0)
        if leftover:
            msg = _("%s unit(s) were not restocked: the fulfilling warehouse has no matching "
                    "delivery move on this order. Check the Shopify Location to Warehouse "
                    "mapping for this instance.") % leftover
            self.message_post(body=msg)
            self._log_to_queue('error', msg)

        if not created_moves:
            return self.env['stock.move']

        if validate:
            self._validate_pending_shopify_return_moves()

        done_count = len(created_moves.filtered(lambda m: m.state == 'done'))
        msg = _("Created %s return stock move(s) for this Shopify return (%s validated automatically).") % (
            len(created_moves), done_count,
        )
        self.message_post(body=msg)
        self._log_to_queue('success', msg)
        return created_moves

    def _validate_pending_shopify_return_moves(self):
        """Validate any pending (non-done, non-cancel) return moves linked
        to this return — marks them done so inventory updates immediately.

        Wrapped in a savepoint — failures (no stock, lot/serial tracking)
        leave the moves in their current state; the outer transaction is
        preserved. The exception is recorded in chatter and the server log.
        Returns:
            recordset: Recordset of stock.move model that was pending.
        """
        self.ensure_one()
        pending = self.return_move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if not pending:
            return pending
        pending = pending.with_context(skip_inventory_sync_commit=True)
        try:
            with self.env.cr.savepoint():
                for move in pending:
                    if move.state == 'draft':
                        move._action_confirm()
                    if move.state not in ('assigned', 'partially_available'):
                        move._action_assign(force_qty=move.product_uom_qty)
                    move._set_quantity_done(move.product_uom_qty)
                    move.picked = True
                    move._action_done()
        except Exception as exc:
            _logger.warning(
                "Could not auto-validate Shopify return stock move(s) %s: %s",
                pending.ids, exc, exc_info=True,
            )
            msg = _("Auto-validation skipped on return stock move(s) %s: %s. "
                    "Please validate manually.") % (pending.ids, exc)
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
        return pending

    def _cancel_pending_shopify_return_moves(self, reason=None):
        """
        Cancel pending return moves when the return is killed or closed without restock.
        Done moves are left untouched (real inventory effects).
        Args:
            reason (str): Explanation for the chatter message. Optional.
        Returns:
            recordset: Recordset of stock.move model that was pending.
        """
        self.ensure_one()
        pending = self.return_move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if not pending:
            return pending
        try:
            pending._action_cancel()
        except Exception as exc:
            _logger.warning(
                "Could not cancel pending Shopify return stock move(s) %s: %s",
                pending.ids, exc,
            )
            msg = _("Auto-cancel of return stock move(s) %s skipped: %s. "
                    "Please cancel manually.") % (pending.ids, exc)
            self.message_post(body=msg)
            self._log_to_queue('error', msg)
            return pending
        explanation = reason or _("the Shopify return was set to %s") % self.status
        msg = _("Cancelled %s pending return stock move(s) because %s.") % (
            len(pending), explanation,
        )
        self.message_post(body=msg)
        self._log_to_queue('success', msg)
        return pending