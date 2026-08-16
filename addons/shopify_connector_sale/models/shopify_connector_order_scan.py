import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)


_logger = logging.getLogger(__name__)

ORDER_SCAN_PAGE_SIZE = 100
ORDER_SCAN_PAGE_LIMIT = 100
ORDER_SCAN_OVERLAP_MINUTES = 30
ORDER_SCAN_TARGET = 'scan:order'
# The exact cron this module installs. Named as a constant so the truthful
# scheduled-state projection resolves one known record rather than searching.
ORDER_SCAN_CRON_XMLID = (
    'shopify_connector_sale.ir_cron_shopify_connector_order_scan'
)

ORDER_SCAN_QUERY = """
query ConnectorOrderScan($first: Int!, $after: String, $query: String!) {
  orders(
    first: $first
    after: $after
    sortKey: UPDATED_AT
    query: $query
  ) {
    edges { cursor node {
      id updatedAt createdAt edited test cancelledAt displayFinancialStatus
    } }
    pageInfo { hasNextPage endCursor }
  }
}
"""


class ShopifyConnectorOrderScan(models.AbstractModel):
    """Enumerates order identities and enqueues the registered importer."""

    _name = 'shopify.connector.order.scan'
    _description = 'Shopify Connector Order Scan Service'

    @api.model
    def run_scan(self, job):
        store = job.store_id
        settings = self._settings(store)
        start = self._incremental_start(settings)
        scan_upper_bound = fields.Datetime.now()
        self._assert_access_window(settings, start)
        counts, latest, _digest = self._enumerate(
            job, store, settings,
            query_filter=self._range_filter(
                'updated_at', start, scan_upper_bound, settings,
            ),
            enqueue=True,
            log_pages=True,
            entity_job_source=job.job_source,
        )
        checkpoint = settings.sale_order_last_import_checkpoint_at
        next_checkpoint = latest
        if not next_checkpoint or (
            checkpoint and next_checkpoint <= checkpoint
        ):
            next_checkpoint = scan_upper_bound
        settings.sudo().write({
            'sale_order_last_import_checkpoint_at': next_checkpoint,
            # Store 360 / R-4 pending catch-up lineage: this traversal
            # enumerated everything updated through `scan_upper_bound` for
            # the generation the job was admitted under. It is only a
            # PENDING claim — the completion stamp is promoted by the
            # job-terminal hook once every descendant import for the store
            # is terminal and non-blocking at the current generation
            # (shopify_connector_order_reconnect.py). Written in the same
            # savepoint as the enumeration and checkpoint advance, so a
            # failed scan records nothing (fail-closed, R-4 §6).
            'sale_order_catchup_pending_generation':
                job.expected_connection_generation,
            'sale_order_catchup_pending_upper_bound_at': scan_upper_bound,
            'sale_order_catchup_pending_scan_job_id': job.id,
        })
        self.env['shopify.connector.job.log']._system_append(
            job,
            'note',
            'Order scan completed and enumerated only; imports remain queued.',
            technical_detail=json.dumps(counts, sort_keys=True),
        )
        return counts

    @api.model
    def preview_backfill(
        self, store, date_from, date_to, job, basis='created_at',
    ):
        self._assert_admin()
        settings = self._settings(store)
        start, end = self._validate_backfill_range(
            store, date_from, date_to, basis,
        )
        counts, _latest, evidence_digest = self._enumerate(
            job, store, settings,
            query_filter=self._range_filter(basis, start, end, settings),
            enqueue=False,
            log_pages=False,
            entity_job_source=False,
        )
        result = dict(counts)
        result['evidence_digest'] = evidence_digest
        result['confirmation_token'] = self._preview_token(
            store, start, end, basis, counts, evidence_digest,
        )
        return result

    @api.model
    def confirm_backfill(
        self, store, date_from, date_to, job, confirmation=False,
        basis='created_at',
    ):
        self._assert_admin()
        settings = self._settings(store)
        start, end = self._validate_backfill_range(
            store, date_from, date_to, basis,
        )
        candidates = []
        preview_counts, _latest, evidence_digest = self._enumerate(
            job, store, settings,
            query_filter=self._range_filter(basis, start, end, settings),
            enqueue=False,
            log_pages=False,
            entity_job_source=False,
            collected_candidates=candidates,
        )
        expected_token = self._preview_token(
            store, start, end, basis, preview_counts, evidence_digest,
        )
        if not isinstance(confirmation, str) or confirmation != expected_token:
            raise UserError(
                'Backfill confirmation must use the current preview token.'
            )
        counts = dict(preview_counts)
        for node in candidates:
            if self._enqueue_order(store, node, 'manual_sync'):
                counts['enqueued'] += 1
            else:
                counts['collided'] += 1
        self.env['shopify.connector.job.log']._system_append(
            job,
            'note',
            'Confirmed order backfill enqueued only the current preview set.',
            technical_detail=json.dumps(counts, sort_keys=True),
        )
        return counts

    @api.model
    def _settings(self, store):
        settings = self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', store.id),
        ], limit=1)
        if not settings or not settings.sale_domain_enabled:
            raise UserError('The sale domain is not enabled for this store.')
        return settings

    @api.model
    def _incremental_start(self, settings):
        checkpoint = settings.sale_order_last_import_checkpoint_at
        if checkpoint:
            return checkpoint - timedelta(minutes=ORDER_SCAN_OVERLAP_MINUTES)
        return fields.Datetime.now() - timedelta(
            days=settings.order_import_window,
        )

    @api.model
    def _validate_backfill_range(self, store, date_from, date_to, basis):
        if basis not in ('created_at', 'updated_at'):
            raise UserError('Backfill basis must be created_at or updated_at.')
        start = self._as_datetime(date_from)
        end = self._as_datetime(date_to)
        if not start or not end or start >= end:
            raise UserError('Backfill requires an increasing date range.')
        settings = self._settings(store)
        self._assert_access_window(settings, start)
        return start, end

    @api.model
    def _assert_access_window(self, settings, start):
        if (
            start < fields.Datetime.now() - timedelta(days=60)
            and 'read_all_orders' not in settings._granted_scope_set()
        ):
            raise UserError(
                'The requested order range extends beyond Shopify\'s latest '
                '60 days. Request and obtain Read all orders in the Partner '
                'Dashboard, then reconnect so read_all_orders is granted; '
                'the connector will not silently truncate this range.'
            )

    @api.model
    def _range_filter(self, basis, start, end, settings):
        clauses = [
            "%s:>'%s'" % (basis, self._iso(start)),
            "%s:<='%s'" % (basis, self._iso(end)),
            'status:any',
        ]
        if not settings.order_import_include_test:
            clauses.append('test:false')
        return ' '.join(clauses)

    @api.model
    def _enumerate(
        self, job, store, settings, query_filter, enqueue, log_pages,
        entity_job_source, collected_candidates=None,
    ):
        client = self.env['shopify.connector.api.client']
        # GraphQL nullable String variables must use JSON null on the first
        # page.  Python ``False`` serializes as JSON false, which Shopify
        # correctly refuses to coerce to ``String`` before executing the
        # query.
        cursor = None
        page_count = 0
        seen_cursors = set()
        seen_gids = set()
        latest = False
        token_evidence = []
        counts = {
            'new': 0,
            'changed': 0,
            'duplicate': 0,
            'skipped': 0,
            'needs_review': 0,
            'enqueued': 0,
            'collided': 0,
            'pages': 0,
        }
        while True:
            if page_count >= ORDER_SCAN_PAGE_LIMIT:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The order scan page ceiling was exceeded.',
                )
            try:
                with client.execute_business(
                    job, store, ORDER_SCAN_QUERY,
                    variables={
                        'first': ORDER_SCAN_PAGE_SIZE,
                        'after': cursor,
                        'query': query_filter,
                    },
                ) as result:
                    if (
                        not isinstance(result, dict)
                        or not isinstance(result.get('data'), dict)
                    ):
                        raise JobHandlerError(
                            'data_shape_schema_mismatch',
                            'Shopify order scan returned an invalid response '
                            'envelope.',
                        )
                    connection = result['data'].get('orders')
                    page = self._validate_page(connection, seen_cursors, seen_gids)
            except ShopifyClientError as exc:
                raise JobHandlerError(
                    exc.error_class, exc.reason, exc.technical_detail,
                ) from exc
            page_count += 1
            counts['pages'] = page_count
            page_counts = {
                'enumerated': len(page['nodes']),
                'enqueued': 0,
                'collided': 0,
            }
            for node in page['nodes']:
                observed = self._as_datetime(node.get('updatedAt'))
                if observed and (not latest or observed > latest):
                    latest = observed
                classification = self._classify_candidate(
                    store, settings, node,
                )
                counts[classification] += 1
                token_evidence.append({
                    'cancelled_at': node.get('cancelledAt'),
                    'classification': classification,
                    'created_at': node.get('createdAt'),
                    'edited': node.get('edited'),
                    'financial_status': node.get('displayFinancialStatus'),
                    'gid': node.get('id'),
                    'test': node.get('test'),
                    'updated_at': node.get('updatedAt'),
                })
                if (
                    collected_candidates is not None
                    and classification in ('new', 'changed', 'needs_review')
                ):
                    collected_candidates.append(dict(node))
                if enqueue and classification in (
                    'new', 'changed', 'needs_review',
                ):
                    if self._enqueue_order(
                        store, node, entity_job_source,
                    ):
                        counts['enqueued'] += 1
                        page_counts['enqueued'] += 1
                    else:
                        counts['collided'] += 1
                        page_counts['collided'] += 1
            if log_pages:
                self.env['shopify.connector.job.log']._system_append(
                    job,
                    'note',
                    'Order scan page enumerated; import jobs were only queued.',
                    technical_detail=json.dumps(page_counts, sort_keys=True),
                )
            if not page['has_next']:
                digest_payload = json.dumps(
                    token_evidence, sort_keys=True, separators=(',', ':'),
                )
                return (
                    counts,
                    latest,
                    hashlib.sha256(digest_payload.encode('utf-8')).hexdigest(),
                )
            if not page['end_cursor'] or page['end_cursor'] == cursor:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The order scan cursor did not make progress.',
                )
            cursor = page['end_cursor']

    @api.model
    def _validate_page(self, connection, seen_cursors, seen_gids):
        if not isinstance(connection, dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order scan evidence omitted the orders connection.',
            )
        edges = connection.get('edges')
        page_info = connection.get('pageInfo')
        if not isinstance(edges, list) or not isinstance(page_info, dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order scan pagination shape was malformed.',
            )
        has_next = page_info.get('hasNextPage')
        if (
            not isinstance(has_next, bool)
            or (
                has_next
                and (
                    not isinstance(page_info.get('endCursor'), str)
                    or not page_info.get('endCursor')
                )
            )
        ):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify order scan pagination metadata was malformed.',
            )
        nodes = []
        for edge in edges:
            cursor = edge.get('cursor') if isinstance(edge, dict) else False
            node = edge.get('node') if isinstance(edge, dict) else False
            gid = node.get('id') if isinstance(node, dict) else False
            updated_at = node.get('updatedAt') if isinstance(node, dict) else False
            if not cursor or not gid or not updated_at or not node.get('createdAt'):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify order scan returned a malformed edge.',
                )
            if (
                not isinstance(node.get('edited'), bool)
                or not isinstance(node.get('test'), bool)
                or (
                    node.get('displayFinancialStatus') is not None
                    and not isinstance(node.get('displayFinancialStatus'), str)
                )
            ):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify order scan returned invalid classification fields.',
                )
            try:
                self._as_datetime(updated_at)
                self._as_datetime(node.get('createdAt'))
                if node.get('cancelledAt'):
                    self._as_datetime(node.get('cancelledAt'))
            except (TypeError, ValueError):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify order scan returned an invalid updatedAt.',
                )
            if cursor in seen_cursors or gid in seen_gids:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify order scan repeated an edge or order identity.',
                )
            seen_cursors.add(cursor)
            seen_gids.add(gid)
            nodes.append(node)
        return {
            'nodes': nodes,
            'has_next': has_next,
            'end_cursor': page_info.get('endCursor'),
        }

    @api.model
    def _classify_candidate(self, store, settings, node):
        binding = self.env['shopify.connector.order.binding'].search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', node['id']),
        ], limit=1)
        if not binding:
            if node.get('edited'):
                return 'skipped'
            if node.get('test') and not settings.order_import_include_test:
                return 'skipped'
            if node.get('cancelledAt'):
                return 'skipped'
            financial = (node.get('displayFinancialStatus') or '').upper()
            if financial in ('REFUNDED', 'VOIDED', 'EXPIRED'):
                return 'skipped'
            if financial not in ('PAID', 'AUTHORIZED', 'PENDING'):
                return 'needs_review'
            return 'new'
        remote_updated = self._as_datetime(node.get('updatedAt'))
        if (
            binding.shopify_updated_at_snapshot
            and remote_updated <= binding.shopify_updated_at_snapshot
        ):
            return 'duplicate'
        if binding.status == 'review':
            return 'needs_review'
        return 'changed'

    @api.model
    def _enqueue_order(self, store, node, job_source):
        try:
            with self.env.cr.savepoint():
                self.env['shopify.connector.job.enqueue'].enqueue(
                    store,
                    job_source=job_source,
                    job_type='order_import_sync',
                    payload_hash=node['updatedAt'],
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=node['id'],
                )
            return True
        except IntegrityError:
            return self._resume_cancelled_order_import(store, node, job_source)

    @api.model
    def _resume_cancelled_order_import(self, store, node, job_source):
        """Re-admit work a CANCELLED import job left provably undone.

        `idempotency_key` persists for the life of a job (job.py:760-763),
        so an import cancelled before it ran — the disconnect quiesce sweep
        (`_sweep_quiescing_business_jobs`) and the reconnect retirement both
        produce exactly this shape — would otherwise collide forever on the
        unchanged `updatedAt` and the order would silently never land
        (R-4 §5/§6: retry/resume must reconcile without duplication, and a
        gap must never persist invisibly).

        Deliberately narrow:
          * only a `cancelled` prior attempt resumes — `succeeded` did the
            work, `skipped` recorded a policy decision this scan must not
            overturn, and `failed_final` is DEC-009's manual-fix state whose
            automatic re-enqueue would defeat the retry taxonomy;
          * only when no binding proves the evidence already landed;
          * with a payload deterministic in the prior attempt's id, so a
            second scan pass collides on the SAME resume key instead of
            growing a job per pass — exactly-once per superseded attempt.

        The cancelled predecessor is linked to its one replacement through
        `superseded_by_job_id` (PR #204 P1-1): the freshness promotion treats
        the cancelled import as a coverage hole until that exact replacement
        SUCCEEDS, so the link makes the "reconsider on the replacement's
        success" contract explicit and one-to-one — whether the replacement
        was just enqueued here or already exists from a prior scan pass.
        """
        Job = self.env['shopify.connector.job'].sudo()
        prior = Job.search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', node['id']),
        ], order='id desc', limit=1)
        if not prior or prior.state != 'cancelled':
            return False
        binding = self.env['shopify.connector.order.binding'].sudo().search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', node['id']),
        ], limit=1)
        if (
            binding
            and binding.shopify_updated_at_snapshot
            and binding.shopify_updated_at_snapshot
            >= self._as_datetime(node.get('updatedAt'))
        ):
            return False
        resume_key = '%s#resume:%d' % (node['updatedAt'], prior.id)
        replacement = False
        try:
            with self.env.cr.savepoint():
                replacement = self.env[
                    'shopify.connector.job.enqueue'
                ].enqueue(
                    store,
                    job_source=job_source,
                    job_type='order_import_sync',
                    payload_hash=resume_key,
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=node['id'],
                )
        except IntegrityError:
            # A prior scan pass already admitted the one deterministic
            # replacement for this cancelled attempt; link to that exact job
            # rather than making a second one (exactly-once per superseded
            # attempt, task §Order-lineage 5/6).
            replacement = Job.search([
                ('store_id', '=', store.id),
                ('job_type', '=', 'order_import_sync'),
                ('shopify_target_gid', '=', node['id']),
                ('payload_hash', '=', resume_key),
            ], limit=1)
        if not replacement:
            return False
        if prior.superseded_by_job_id.id != replacement.id:
            # superseded_by_job_id is a PROTECTED_JOB_FIELDS entry, writable
            # only under sudo — `prior` is already sudo. Not a state field,
            # so no legal-transition check applies.
            prior.write({'superseded_by_job_id': replacement.id})
        return True

    @api.model
    def _preview_token(
        self, store, start, end, basis, counts, evidence_digest,
    ):
        settings = self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', store.id),
        ], limit=1)
        payload = json.dumps({
            'basis': basis,
            'connection_generation': store.connection_generation,
            'counts': counts,
            'date_from': self._iso(start),
            'date_to': self._iso(end),
            'evidence_digest': evidence_digest,
            'include_test_orders': bool(
                settings and settings.order_import_include_test
            ),
            'store_id': store.id,
        }, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    @api.model
    def _assert_admin(self):
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError('Only an Administrator may run order backfill.')

    @api.model
    def _as_datetime(self, value):
        if not value:
            return False
        if isinstance(value, datetime):
            parsed = value
        else:
            parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
        if parsed.tzinfo:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    @api.model
    def _iso(self, value):
        value = self._as_datetime(value)
        return value.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


class ShopifyConnectorJobOrderScanExtension(models.Model):
    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[('order_import_scan', 'Order Import Scan')],
        ondelete={
            'order_import_scan': lambda recs: recs._reassign_to_historic_job_type(),
        },
    )

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        if job_type == 'order_import_scan':
            return 'sale_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)


class ShopifyConnectorJobDispatchOrderScanExtension(models.AbstractModel):
    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        handlers['order_import_scan'] = self._handle_order_import_scan
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        policies['order_import_scan'] = REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE
        return policies

    @api.model
    def _handle_order_import_scan(self, job):
        # One savepoint spans enumeration, child-job enqueue, page logs, and
        # checkpoint advancement. The dispatcher may catch a classified failure
        # and commit its routed job state, but no partial scan side effect may
        # survive that failure.
        with self.env.cr.savepoint():
            self.env['shopify.connector.order.scan'].run_scan(job)


class ShopifyConnectorStoreOrderScanExtension(models.Model):
    _inherit = 'shopify.connector.store'

    pending_job_count = fields.Integer(
        compute='_compute_order_job_counts',
        help='Non-terminal connector jobs currently associated with the store.',
    )
    failed_job_count = fields.Integer(
        compute='_compute_order_job_counts',
        help='Connector jobs currently waiting for failure recovery or review.',
    )

    # ------------------------------------------------------------------
    # Batch 2 checkpoint 2: what the operator surface must be able to say
    # ------------------------------------------------------------------
    #
    # These exist so the screen carrying `Import orders now` can state the
    # scheduled position honestly beside it. Before this there was no way for
    # any surface to answer "is order import running on its own?", and a
    # manual button with no such answer beside it invites exactly the wrong
    # conclusion -- that pressing it occasionally is all that is required, or
    # conversely that automation is handling it when the flag is off.
    #
    # Computed, never stored: they are a projection of the settings row and
    # the live job table, and storing them would create a second copy of the
    # truth that could disagree with the cron's own SELECT.
    order_sync_domain_enabled = fields.Boolean(
        compute='_compute_order_sync_state',
        string='Order sync enabled',
    )
    order_sync_scheduled = fields.Boolean(
        compute='_compute_order_sync_state',
        string='Scheduled order import',
    )
    order_sync_last_checkpoint_at = fields.Datetime(
        compute='_compute_order_sync_state',
        string='Discovered up to',
    )
    order_sync_active_scan_count = fields.Integer(
        compute='_compute_order_sync_state',
        string='Order scans in flight',
    )

    def _compute_order_sync_state(self):
        Settings = self.env['shopify.connector.store.settings']
        Job = self.env['shopify.connector.job']
        # Batch 2 correction (F7): the store flag records what the merchant
        # asked for; `_cron_enqueue_order_scans` only runs if the cron this
        # module installed is still active. An administrator who disabled it in
        # Settings -> Technical -> Scheduled Actions has stopped scheduled
        # import, and this surface must say so rather than keep reporting the
        # flag. Read once for the whole recordset.
        scheduler_live = self._connector_scheduler_is_active(
            ORDER_SCAN_CRON_XMLID,
        )
        for store in self:
            settings = Settings.search(
                [('store_id', '=', store.id)], limit=1,
            )
            store.order_sync_domain_enabled = bool(
                settings and settings.sale_domain_enabled
            )
            store.order_sync_scheduled = bool(
                settings and settings.sale_domain_enabled
                and settings.order_scheduled_sync_enabled
                and scheduler_live
            )
            store.order_sync_last_checkpoint_at = (
                settings.sale_order_last_import_checkpoint_at
                if settings else False
            )
            store.order_sync_active_scan_count = Job.search_count([
                ('store_id', '=', store.id),
                ('res_model', '=', 'shopify.connector.store'),
                ('res_id', '=', store.id),
                ('shopify_target_gid', '=', ORDER_SCAN_TARGET),
                ('state', 'not in', (
                    'succeeded', 'failed_final', 'skipped', 'cancelled',
                )),
            ])

    def _compute_order_job_counts(self):
        pending_states = (
            'draft', 'queued', 'running', 'retry_waiting', 'failed_retryable',
            'blocked_manual_review',
        )
        failed_states = (
            'failed_retryable', 'failed_final', 'blocked_manual_review',
        )
        Job = self.env['shopify.connector.job']
        for store in self:
            store.pending_job_count = Job.search_count([
                ('store_id', '=', store.id),
                ('state', 'in', pending_states),
            ])
            store.failed_job_count = Job.search_count([
                ('store_id', '=', store.id),
                ('state', 'in', failed_states),
            ])

    def action_sync_orders_now(self):
        self.ensure_one()
        self._assert_order_sync_operator()
        return self._enqueue_order_scan('manual_sync')

    def _assert_order_sync_operator(self):
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Operator or Administrator may '
                'start an order sync.'
            )

    def _enqueue_order_scan(self, job_source):
        self.ensure_one()
        if self.state != 'connected':
            raise UserError('Only a connected store can start an order scan.')
        settings = self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', self.id),
        ], limit=1)
        if not settings or not settings.sale_domain_enabled:
            raise UserError('The sale domain is not enabled for this store.')
        active = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.id),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', self.id),
            ('shopify_target_gid', '=', ORDER_SCAN_TARGET),
            ('state', 'not in', ('succeeded', 'failed_final', 'skipped', 'cancelled')),
        ], limit=1)
        if active:
            return active
        try:
            with self.env.cr.savepoint():
                return self.env['shopify.connector.job.enqueue'].enqueue(
                    self,
                    job_source=job_source,
                    job_type='order_import_scan',
                    payload_hash=str(uuid.uuid4()),
                    res_model='shopify.connector.store',
                    res_id=self.id,
                    shopify_target_gid=ORDER_SCAN_TARGET,
                )
        except IntegrityError:
            # A concurrent discovery may win after the pre-check. Resolve the
            # winner under the caller's normal environment; never create a
            # second scan or import inline.
            active = self.env['shopify.connector.job'].search([
                ('store_id', '=', self.id),
                ('res_model', '=', 'shopify.connector.store'),
                ('res_id', '=', self.id),
                ('shopify_target_gid', '=', ORDER_SCAN_TARGET),
                ('state', 'not in', (
                    'succeeded', 'failed_final', 'skipped', 'cancelled',
                )),
            ], limit=1)
            return active or False

    @api.model
    def _cron_enqueue_order_scans(self):
        settings_records = self.env[
            'shopify.connector.store.settings'
        ].search([
            ('sale_domain_enabled', '=', True),
            ('order_scheduled_sync_enabled', '=', True),
            ('store_id.state', '=', 'connected'),
        ])
        for settings in settings_records:
            try:
                settings.store_id._enqueue_order_scan('scheduled_sync')
            except Exception as exc:  # cron must continue store-by-store
                _logger.warning(
                    'Order scan enqueue failed for store_id=%s error_type=%s',
                    settings.store_id.id,
                    type(exc).__name__,
                )
        return None


class ShopifyConnectorOrderBindingSyncExtension(models.Model):
    _inherit = 'shopify.connector.order.binding'

    def action_sync_selected(self):
        self.ensure_one()
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Operator or Administrator may '
                'refresh an order.'
            )
        if self.store_id.state != 'connected':
            raise UserError('Only a connected store can refresh an order.')
        settings = self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', self.store_id.id),
        ], limit=1)
        if not settings or not settings.sale_domain_enabled:
            raise UserError('The sale domain is not enabled for this store.')
        active_domain = [
            ('store_id', '=', self.store_id.id),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', self.store_id.id),
            ('shopify_target_gid', '=', self.shopify_gid),
            ('state', 'not in', (
                'succeeded', 'failed_final', 'skipped', 'cancelled',
            )),
        ]
        active = self.env['shopify.connector.job'].search(
            active_domain, limit=1,
        )
        if active:
            return active
        try:
            with self.env.cr.savepoint():
                return self.env['shopify.connector.job.enqueue'].enqueue(
                    self.store_id,
                    job_source='manual_sync',
                    job_type='order_import_sync',
                    payload_hash='manual:%s' % uuid.uuid4(),
                    res_model='shopify.connector.store',
                    res_id=self.store_id.id,
                    shopify_target_gid=self.shopify_gid,
                )
        except IntegrityError:
            winner = self.env['shopify.connector.job'].search(
                active_domain, limit=1,
            )
            return winner or False
