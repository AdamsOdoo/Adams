"""Batch 2 checkpoint 3: the product enumeration producer.

THE DEFECT THIS CLOSES. `product_import_sync` was registered, handled, replay-
classified and fully implemented -- and nothing in production ever created one.
There was no cron, no button, no service that enumerated a catalog and admitted
per-product work. The importer was a destination with no road to it.

This is that road, and it is deliberately the same road the order scan already
built: a registered scan job type, a bounded cursor-paginated enumeration
through the existing client, per-product children admitted through the existing
enqueue service, and a checkpoint that only advances when the scan finished.
Nothing here is a second queue, a second dispatcher, or a second transport.

VERIFIED AGAINST THE CONFIGURED VERSION, NOT AGAINST `latest`. The connector
speaks `2026-07` (`tools/api_version.py`, a centralized constant). Against that
version's schema:

* `ProductSortKeys` includes `UPDATED_AT`, so the connection can be ordered by
  the same field the checkpoint advances on -- which is what makes a
  cursor-paginated incremental scan coherent at all.
* `ProductStatus` is `ACTIVE`, `ARCHIVED`, `DRAFT` **and `UNLISTED`**, the last
  of which the schema states is "only visible from 2025-10 and up". A scan
  written against the familiar three-value enum would meet a fourth value on
  this version. `status` is therefore carried as an opaque string and never
  matched against a closed set.

WHY THE FILTER CARRIES NO STATUS CLAUSE. The Admin API returns products of
every status unless asked otherwise, so omitting the clause enumerates the
whole catalog. §8.1.8 forbids a default that silently omits old or unchanged
products, and the surest way to honour it is to ask for no narrowing at all
and let the checkpoint -- not a status guess -- decide what is new work.

THE BOUND AND RESUMPTION CONTRACT (WP-6). Each job reads at most
`PRODUCT_SCAN_SLICE_PAGES` pages. The fixed lower/upper window, server cursor,
latest observed timestamp, connection generation, and page count are durable
on Store Settings. A terminal successor resumes that exact window; only its
final page advances the public checkpoint. The legacy 200-page ceiling remains
solely as a defensive bound for explicitly non-resumable internal callers and
is no longer a catalog-size ceiling for scheduled or manual product scans.
"""

import hashlib
import json
import logging
import uuid
from datetime import timedelta

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

PRODUCT_SCAN_TARGET = 'scan:product'
PRODUCT_SCAN_PAGE_SIZE = 100
PRODUCT_SCAN_PAGE_LIMIT = 200
PRODUCT_SCAN_SLICE_PAGES = 10
# A non-resumable caller's defensive ceiling. Scheduled/import scans use
# durable bounded slices and therefore continue beyond this legacy ceiling.
PRODUCT_SCAN_MAX_PRODUCTS = PRODUCT_SCAN_PAGE_SIZE * PRODUCT_SCAN_PAGE_LIMIT

# The exact cron this module installs. Named as a constant so the truthful
# scheduled-state projection resolves one known record rather than searching.
PRODUCT_SCAN_CRON_XMLID = (
    'shopify_connector_product.ir_cron_shopify_connector_product_scan'
)

# The incremental window deliberately reaches slightly BEHIND the checkpoint.
# Shopify's `updated_at` has second resolution and a write landing in the same
# second the previous scan finished would otherwise fall in the gap between
# `>checkpoint` and the next run. Re-enumerating a minute of already-seen
# products is free -- the child admission collides on the existing idempotency
# key and is contained -- whereas missing one is silent and permanent.
PRODUCT_SCAN_OVERLAP = timedelta(minutes=1)

PRODUCT_SCAN_QUERY = """
query ConnectorProductScan($first: Int!, $after: String, $query: String!) {
  products(
    first: $first
    after: $after
    sortKey: UPDATED_AT
    query: $query
  ) {
    edges { cursor node { id updatedAt status } }
    pageInfo { hasNextPage endCursor }
  }
}
"""


class ShopifyConnectorProductScan(models.AbstractModel):
    """Enumerates product identities and admits the registered importer."""

    _name = 'shopify.connector.product.scan'
    _description = 'Shopify Connector Product Scan Service'

    @api.model
    def run_scan(self, job):
        store = job.store_id
        settings = self._settings(store)
        self._assert_import_direction_permits_scan(settings)
        generation = job.expected_connection_generation
        if (
            settings.product_scan_window_end_at
            and settings.product_scan_generation == generation
        ):
            start = settings.product_scan_window_start_at or False
            scan_upper_bound = settings.product_scan_window_end_at
            cursor = settings.product_scan_cursor or None
            prior_latest = settings.product_scan_latest_at or False
            prior_pages = settings.product_scan_page_count or 0
        else:
            # A fixed durable window is captured once and reused by every
            # continuation job. A restart can never slide either boundary.
            scan_upper_bound = fields.Datetime.now()
            start = self._incremental_start(settings)
            cursor = None
            prior_latest = False
            prior_pages = 0
            settings.sudo().write({
                'product_scan_window_start_at': start,
                'product_scan_window_end_at': scan_upper_bound,
                'product_scan_cursor': False,
                'product_scan_latest_at': False,
                'product_scan_page_count': 0,
                'product_scan_generation': generation,
            })
        counts, latest, next_cursor, complete = self._enumerate(
            job, store,
            query_filter=self._range_filter(start, scan_upper_bound),
            job_source=job.job_source,
            start_cursor=cursor,
            page_limit=PRODUCT_SCAN_SLICE_PAGES,
            resumable=True,
        )
        latest = max(filter(None, (prior_latest, latest)), default=False)
        total_pages = prior_pages + counts['pages']
        if not complete:
            settings.sudo().write({
                'product_scan_cursor': next_cursor,
                'product_scan_latest_at': latest,
                'product_scan_page_count': total_pages,
            })
            job.sudo().write({
                'state': 'succeeded',
                'finished_at': fields.Datetime.now(),
            })
            self.env['shopify.connector.job.log']._system_append(
                job, 'state_change',
                'Product scan slice completed; durable cursor saved and the '
                'next bounded slice was queued.',
                from_state='running', to_state='succeeded',
                technical_detail=json.dumps(counts, sort_keys=True),
            )
            successor = store._enqueue_product_scan(job.job_source)
            if not successor:
                raise JobHandlerError(
                    'concurrency_race_conflict',
                    'Product scan cursor was saved but no continuation job '
                    'could be admitted.',
                )
            return counts
        checkpoint = settings.product_last_import_checkpoint_at
        next_checkpoint = latest
        if not next_checkpoint or (
            checkpoint and next_checkpoint <= checkpoint
        ):
            next_checkpoint = scan_upper_bound
        # Written only HERE, after every page enumerated and every child was
        # admitted. A failure anywhere above raises out of `run_scan`, the
        # dispatcher's savepoint discards the partial work, and the checkpoint
        # still describes the last scan that genuinely completed -- so the next
        # run re-covers the ground this one did not finish.
        settings.sudo().write({
            'product_last_import_checkpoint_at': next_checkpoint,
            'product_last_import_success_at': scan_upper_bound,
            'product_scan_window_start_at': False,
            'product_scan_window_end_at': False,
            'product_scan_cursor': False,
            'product_scan_latest_at': False,
            'product_scan_page_count': 0,
            'product_scan_generation': 0,
        })
        self.env['shopify.connector.job.log']._system_append(
            job,
            'note',
            'Product scan completed and enumerated only; imports remain '
            'queued.',
            technical_detail=json.dumps(counts, sort_keys=True),
        )
        return counts

    @api.model
    def _settings(self, store):
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings:
            raise JobHandlerError(
                'odoo_validation_configuration',
                'The store has no settings record, so no product scan can '
                'run.',
            )
        return settings

    @api.model
    def _assert_import_direction_permits_scan(self, settings):
        """§8.1.16: the accepted repository semantics, not a hidden widget.

        `product_first_sync_source` states which side the catalog comes from.
        `odoo_source` means Odoo owns it and Shopify is the destination, so
        enumerating Shopify to create Odoo products would import the store's
        own exports back over itself. The refusal is server-side because a
        disabled control is decoration, not a control.
        """
        if not settings.product_domain_enabled:
            raise JobHandlerError(
                'odoo_validation_configuration',
                'The product domain is not enabled for this store.',
            )
        if settings.product_first_sync_source == 'odoo_source':
            raise JobHandlerError(
                'odoo_validation_configuration',
                'This store imports no products: its first sync direction is '
                'Odoo as the source.',
            )

    @api.model
    def _incremental_start(self, settings):
        checkpoint = settings.product_last_import_checkpoint_at
        if not checkpoint:
            # FIRST RUN: no lower bound at all. §8.1.8 -- a "recent changes"
            # default would silently omit every product that has not been
            # edited lately, which on a first import is most of the catalog.
            return False
        return checkpoint - PRODUCT_SCAN_OVERLAP

    @api.model
    def _range_filter(self, start, end):
        clauses = ["updated_at:<='%s'" % self._iso(end)]
        if start:
            clauses.insert(0, "updated_at:>'%s'" % self._iso(start))
        return ' '.join(clauses)

    @api.model
    def _iso(self, value):
        return fields.Datetime.to_string(value).replace(' ', 'T') + 'Z'

    @api.model
    def _enumerate(
        self, job, store, query_filter, job_source, start_cursor=None,
        page_limit=PRODUCT_SCAN_PAGE_LIMIT, resumable=False,
    ):
        client = self.env['shopify.connector.api.client']
        # GraphQL nullable String variables must use JSON null on the first
        # page.  Python ``False`` serializes as JSON false, which Shopify
        # correctly refuses to coerce to ``String`` before executing the
        # query.
        cursor = start_cursor
        page_count = 0
        seen_cursors = set()
        seen_gids = set()
        latest = False
        counts = {
            'enumerated': 0,
            'enqueued': 0,
            'collided': 0,
            'pages': 0,
        }
        while True:
            if page_count >= page_limit:
                if resumable:
                    return counts, latest, cursor, False
                # §8.1.15: visible, never a silent truncation. Stopping here
                # and reporting success would advance the checkpoint past
                # products this scan never looked at.
                #
                # Batch 2 correction (F11): the refusal now STATES the
                # limitation and its consequence. "The product scan page
                # ceiling was exceeded" told an operator nothing about what
                # they had hit, whether their catalog had been imported, or
                # what to do -- and this is not a transient fault they can
                # retry away: every subsequent run enumerates the same
                # unbounded first window and stops in the same place. The
                # bounded resumable enumeration that would fix it is recorded
                # as debt (TD-024) and is deliberately not built here.
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'This catalog is larger than one product scan can '
                    'enumerate. A scan reads %d products per page and stops '
                    'at %d pages, so it covers at most %d products in a '
                    'single run, and this store has more than that in the '
                    'window being scanned. NOTHING WAS IMPORTED and the '
                    'catalog checkpoint has NOT moved, so no product has been '
                    'silently skipped -- but retrying will stop at exactly '
                    'the same place, because the scan restarts from the same '
                    'window every time. Resumable enumeration for catalogs '
                    'above this size is not implemented yet; until it is, '
                    'this store cannot complete an initial product import.'
                    % (
                        PRODUCT_SCAN_PAGE_SIZE,
                        PRODUCT_SCAN_PAGE_LIMIT,
                        PRODUCT_SCAN_MAX_PRODUCTS,
                    ),
                )
            try:
                with client.execute_business(
                    job, store, PRODUCT_SCAN_QUERY,
                    variables={
                        'first': PRODUCT_SCAN_PAGE_SIZE,
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
                            'Shopify product scan returned an invalid '
                            'response envelope.',
                        )
                    page = self._validate_page(
                        result['data'].get('products'),
                        seen_cursors, seen_gids,
                    )
            except ShopifyClientError as exc:
                raise JobHandlerError(
                    exc.error_class, exc.reason, exc.technical_detail,
                ) from exc
            page_count += 1
            counts['pages'] = page_count
            for node in page['nodes']:
                counts['enumerated'] += 1
                observed = self._as_datetime(node.get('updatedAt'))
                if observed and (not latest or observed > latest):
                    latest = observed
                if self._enqueue_product(store, node, job_source):
                    counts['enqueued'] += 1
                else:
                    counts['collided'] += 1
            if not page['has_next']:
                if resumable:
                    return counts, latest, False, True
                return counts, latest
            if not page['end_cursor'] or page['end_cursor'] == cursor:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'The product scan cursor did not make progress.',
                )
            cursor = page['end_cursor']

    @api.model
    def _validate_page(self, connection, seen_cursors, seen_gids):
        """Fail closed on every shape the server should not produce."""
        if not isinstance(connection, dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify product scan evidence omitted the products '
                'connection.',
            )
        edges = connection.get('edges')
        page_info = connection.get('pageInfo')
        if not isinstance(edges, list) or not isinstance(page_info, dict):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Shopify product scan pagination shape was malformed.',
            )
        nodes = []
        for edge in edges:
            if not isinstance(edge, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan returned a malformed edge.',
                )
            edge_cursor = edge.get('cursor')
            if edge_cursor in seen_cursors:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan repeated a page cursor.',
                )
            if edge_cursor:
                seen_cursors.add(edge_cursor)
            node = edge.get('node')
            if not isinstance(node, dict):
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan returned a malformed node.',
                )
            gid = node.get('id')
            updated_at = node.get('updatedAt')
            if not isinstance(gid, str) or not gid:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan returned a product with no id.',
                )
            if not isinstance(updated_at, str) or not updated_at:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan returned a product with no '
                    'updatedAt.',
                )
            if gid in seen_gids:
                raise JobHandlerError(
                    'data_shape_schema_mismatch',
                    'Shopify product scan returned a duplicate product '
                    'identity.',
                )
            seen_gids.add(gid)
            nodes.append(node)
        return {
            'nodes': nodes,
            'has_next': bool(page_info.get('hasNextPage')),
            'end_cursor': page_info.get('endCursor'),
        }

    @api.model
    def _enqueue_product(self, store, node, job_source):
        """One child per product identity, keyed on the exact remote stamp.

        `payload_hash` is the verbatim `updatedAt` string Shopify returned --
        not a parsed datetime and not a hash of one. It is what makes a
        re-enumeration of an unchanged product collide with the work already
        queued for it instead of duplicating it, and re-formatting it would
        break that identity for no gain.
        """
        try:
            with self.env.cr.savepoint():
                self.env['shopify.connector.job.enqueue'].enqueue(
                    store,
                    job_source=job_source,
                    job_type='product_import_sync',
                    payload_hash=node['updatedAt'],
                    res_model='shopify.connector.store',
                    res_id=store.id,
                    shopify_target_gid=node['id'],
                )
            return True
        except IntegrityError:
            return False

    @api.model
    def _as_datetime(self, value):
        if not value:
            return False
        try:
            return fields.Datetime.to_datetime(
                str(value).replace('Z', '').replace('T', ' ')[:19]
            )
        except (TypeError, ValueError):
            return False


class ShopifyConnectorJobProductScan(models.Model):
    """Register `product_import_scan` beside the existing per-product type."""

    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[('product_import_scan', 'Product Import Scan')],
        ondelete={
            'product_import_scan':
                lambda recs: recs._reassign_to_historic_job_type(),
        },
    )

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        if job_type == 'product_import_scan':
            return 'product_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)


class ShopifyConnectorJobDispatchProductScan(models.AbstractModel):
    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        handlers['product_import_scan'] = self._handle_product_import_scan
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        policies['product_import_scan'] = (
            REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE
        )
        return policies

    @api.model
    def _handle_product_import_scan(self, job):
        """Enumeration, child admission and checkpoint in ONE savepoint.

        §8.1.13: the dispatcher may catch a classified failure and commit the
        job's routed state, but no partial scan side effect may survive that
        failure. Either the whole scan happened -- children admitted and
        checkpoint advanced together -- or none of it did.
        """
        with self.env.cr.savepoint():
            self.env['shopify.connector.product.scan'].run_scan(job)


class ShopifyConnectorStoreProductScanExtension(models.Model):
    _inherit = 'shopify.connector.store'

    product_sync_domain_enabled = fields.Boolean(
        compute='_compute_product_sync_state',
        string='Product sync enabled',
    )
    product_sync_scheduled = fields.Boolean(
        compute='_compute_product_sync_state',
        string='Scheduled product import',
    )
    product_sync_last_checkpoint_at = fields.Datetime(
        compute='_compute_product_sync_state',
        string='Catalog scanned up to',
    )
    product_sync_active_scan_count = fields.Integer(
        compute='_compute_product_sync_state',
        string='Product scans in flight',
    )

    def _compute_product_sync_state(self):
        Settings = self.env['shopify.connector.store.settings']
        Job = self.env['shopify.connector.job']
        # Batch 2 correction (F7): the store flag is an INTENTION; the cron is
        # what actually runs. Read once for the whole recordset -- it is one
        # `ir.model.data` resolution and one field read, and it is the same
        # answer for every store in the database.
        scheduler_live = self._connector_scheduler_is_active(
            PRODUCT_SCAN_CRON_XMLID,
        )
        for store in self:
            settings = Settings.search(
                [('store_id', '=', store.id)], limit=1,
            )
            enabled = bool(settings and settings.product_domain_enabled)
            store.product_sync_domain_enabled = enabled
            store.product_sync_scheduled = bool(
                enabled
                and settings.product_scheduled_sync_enabled
                and scheduler_live
            )
            store.product_sync_last_checkpoint_at = (
                settings.product_last_import_checkpoint_at
                if settings else False
            )
            store.product_sync_active_scan_count = Job.search_count([
                ('store_id', '=', store.id),
                ('res_model', '=', 'shopify.connector.store'),
                ('res_id', '=', store.id),
                ('shopify_target_gid', '=', PRODUCT_SCAN_TARGET),
                ('state', 'not in', (
                    'succeeded', 'failed_final', 'skipped', 'cancelled',
                )),
            ])

    def action_sync_products_now(self):
        self.ensure_one()
        self._assert_product_sync_operator()
        return self._enqueue_product_scan('manual_sync')

    def _assert_product_sync_operator(self):
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
                'start a product import.'
            )

    def _enqueue_product_scan(self, job_source):
        """Admit at most one non-terminal product scan per store."""
        self.ensure_one()
        if self.state != 'connected':
            raise UserError(
                'Only a connected store can start a product import.'
            )
        settings = self.env['shopify.connector.store.settings'].search([
            ('store_id', '=', self.id),
        ], limit=1)
        if not settings or not settings.product_domain_enabled:
            raise UserError(
                'The product domain is not enabled for this store.'
            )
        if settings.product_first_sync_source == 'odoo_source':
            raise UserError(
                'This store imports no products: its first sync direction is '
                'Odoo as the source.'
            )
        active = self._active_product_scan()
        if active:
            return active
        try:
            with self.env.cr.savepoint():
                return self.env['shopify.connector.job.enqueue'].enqueue(
                    self,
                    job_source=job_source,
                    job_type='product_import_scan',
                    payload_hash=str(uuid.uuid4()),
                    res_model='shopify.connector.store',
                    res_id=self.id,
                    shopify_target_gid=PRODUCT_SCAN_TARGET,
                )
        except IntegrityError:
            # A concurrent opener won after the pre-check. Resolve the winner
            # in the caller's ordinary environment; never create a second scan
            # and never run an import inline.
            return self._active_product_scan() or False

    def _active_product_scan(self):
        self.ensure_one()
        return self.env['shopify.connector.job'].search([
            ('store_id', '=', self.id),
            ('res_model', '=', 'shopify.connector.store'),
            ('res_id', '=', self.id),
            ('shopify_target_gid', '=', PRODUCT_SCAN_TARGET),
            ('state', 'not in', (
                'succeeded', 'failed_final', 'skipped', 'cancelled',
            )),
        ], limit=1)

    @api.model
    def _cron_enqueue_product_scans(self):
        settings_records = self.env[
            'shopify.connector.store.settings'
        ].search([
            ('product_domain_enabled', '=', True),
            ('product_scheduled_sync_enabled', '=', True),
            ('store_id.state', '=', 'connected'),
        ])
        for settings in settings_records:
            try:
                settings.store_id._enqueue_product_scan('scheduled_sync')
            except Exception as exc:  # cron must continue store-by-store
                _logger.warning(
                    'Product scan enqueue failed for store_id=%s '
                    'error_type=%s',
                    settings.store_id.id, type(exc).__name__,
                )
        return None
