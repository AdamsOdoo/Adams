import hashlib
import logging

from psycopg2 import IntegrityError

from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .shopify_connector_fulfillment_create_strategy import (
    CREATE_FULFILLMENT_ACTION,
    FO_BLOCKING_STATUSES,
    FO_ELIGIBLE_STATUSES,
)
from .shopify_connector_fulfillment_reader import FulfillmentReadError
from .shopify_connector_job import (
    JOB_TYPE_CREATE,
    JOB_TYPE_PICKING_ADMISSION,
    JOB_TYPE_TRACKING_ADMISSION,
    JOB_TYPE_TRACKING_UPDATE,
    TRIGGER_ORIGIN_PICKING,
    TRIGGER_ORIGIN_TRACKING,
)

_logger = logging.getLogger(__name__)

# The exact DB-level identifiers for the
# `shopify.connector.job._store_operation_scope_key_uniq` collision (core) --
# mirrored here, not imported from `shopify_connector_inventory`, per DEC-008's
# dependency direction. Byte-identical to the values
# `shopify_connector_inventory_service.py::_try_enqueue_push_sync` matches for
# the same constraint (decision-lock Decision D.3).
OPERATION_SCOPE_CONSTRAINT_MESSAGE = (
    'A non-terminal job already holds this operation scope for this store.'
)
OPERATION_SCOPE_CONSTRAINT_NAME = (
    'shopify_connector_job_store_operation_scope_key_uniq'
)


class ShopifyConnectorFulfillmentAdmission(models.AbstractModel):
    """Outbound admission / orchestration (no Shopify mutation).

    `fulfillment_picking_admission` decomposes a validated outbound picking into
    exactly one `fulfillment_create` child (a picking is one physical shipment
    → one Shopify fulfillment, UNIQUE(store, picking); a backorder chain
    produces separate pickings → separate fulfillments).
    `fulfillment_tracking_admission` enqueues a `fulfillment_tracking_update` for
    a post-fulfillment tracking change on a bound picking.
    """

    _inherit = 'shopify.connector.fulfillment.service'

    # ------------------------------------------------------------------
    # Enqueue seams (called from stock.picking._action_done and manual actions)
    # ------------------------------------------------------------------

    @api.model
    def _fulfillment_settings(self, store):
        return self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )

    @api.model
    def _enqueue_picking_admission(
        self, picking, job_source='odoo_event',
        trigger_origin=TRIGGER_ORIGIN_PICKING,
    ):
        store = self._picking_store(picking)
        if not store:
            return self.env['shopify.connector.job']
        settings = self._fulfillment_settings(store)
        if not settings or not settings.fulfillment_domain_enabled:
            return self.env['shopify.connector.job']
        return self._enqueue_once(
            store, job_source, JOB_TYPE_PICKING_ADMISSION,
            'admission:%d' % picking.id, 'stock.picking', picking.id,
            trigger_origin=trigger_origin,
        )

    @api.model
    def _enqueue_tracking_admission(
        self, binding, job_source='odoo_event',
        trigger_origin=TRIGGER_ORIGIN_TRACKING,
    ):
        store = binding.store_id
        settings = self._fulfillment_settings(store)
        if not settings or not settings.fulfillment_domain_enabled:
            return self.env['shopify.connector.job']
        digest = self._tracking_payload_hash(binding.picking_id)
        return self._enqueue_once(
            store, job_source, JOB_TYPE_TRACKING_ADMISSION,
            'tracking_admission:%d:%s' % (binding.id, digest),
            'shopify.connector.fulfillment.binding', binding.id,
            trigger_origin=trigger_origin,
        )

    @api.model
    def _picking_store(self, picking):
        binding = self.env['shopify.connector.order.binding'].search([
            ('sale_order_id', '=', picking.sale_id.id),
        ], limit=1)
        return binding.store_id if binding else False

    @api.model
    def _tracking_payload_hash(self, picking):
        raw = '%s|%s|%s' % (
            picking.carrier_tracking_ref or '',
            getattr(picking, 'carrier_tracking_url', '') or '',
            picking.carrier_id.name or '',
        )
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]

    @api.model
    def _enqueue_once(
        self, store, job_source, job_type, payload_hash, res_model, res_id,
        shopify_target_gid=False, trigger_origin=False,
    ):
        """Enqueue idempotently: an existing job with the same identity
        (a stable payload_hash keyed to the operation) is never duplicated. A
        business job is only enqueued for a connected store.

        Enforces the merged source/origin invariant at the single enqueue choke
        point: a non-`odoo_event` source can never carry a trigger origin (the
        core `_check_trigger_origin_required` constraint), so any caller-supplied
        trigger origin is cleared for such sources.

        Centralizes the expected `(store_id, operation_scope_key)` collision
        recovery once, here, for every one of this addon's call sites
        (decision-lock Decision D.1): the fast idempotency-key search above is
        a plain optimization keyed on payload_hash; the actual serialization
        guard is the DB-level `_store_operation_scope_key_uniq` constraint,
        which does not depend on payload_hash. The create attempt below runs
        inside a savepoint (mirroring the established
        `shopify_connector_inventory_service.py::_try_enqueue_push_sync`
        precedent) so a benign collision never poisons the caller's own
        enclosing transaction. Only the exact operation-scope collision is
        ever swallowed: it is matched against the constraint's own message
        AND its raw DB constraint name (Odoo only substitutes the friendly
        text at the HTTP boundary, not inside an inline savepoint flush), then
        independently re-verified by re-querying for the actual non-terminal
        job now holding this exact operation identity before being treated as
        benign. Every other exception — including a genuine ambiguity where
        the constraint matched but no such job is found — propagates
        unchanged, never silently absorbed.
        """
        if store.state != 'connected':
            return self.env['shopify.connector.job']
        if job_source != 'odoo_event':
            trigger_origin = False
        Job = self.env['shopify.connector.job']
        existing = Job.search([
            ('store_id', '=', store.id),
            ('job_type', '=', job_type),
            ('res_model', '=', res_model),
            ('res_id', '=', res_id),
            ('payload_hash', '=', payload_hash),
        ], limit=1)
        if existing:
            return existing
        try:
            with self.env.cr.savepoint():
                return self.env['shopify.connector.job.enqueue'].enqueue(
                    store, job_source, job_type,
                    payload_hash=payload_hash,
                    res_model=res_model, res_id=res_id,
                    shopify_target_gid=shopify_target_gid,
                    trigger_origin=trigger_origin,
                )
        except (ValidationError, IntegrityError) as exc:
            message = str(exc)
            if (
                OPERATION_SCOPE_CONSTRAINT_MESSAGE not in message
                and OPERATION_SCOPE_CONSTRAINT_NAME not in message
            ):
                raise
            scope_holder = Job.search([
                ('store_id', '=', store.id),
                ('job_type', '=', job_type),
                ('res_model', '=', res_model),
                ('res_id', '=', res_id),
                ('shopify_target_gid', '=', shopify_target_gid),
                ('state', 'not in', list(TERMINAL_JOB_STATES)),
            ], limit=1)
            if not scope_holder:
                raise
            return scope_holder

    # ------------------------------------------------------------------
    # Picking-admission handler
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_picking_admission(self, job):
        picking = self.env['stock.picking'].browse(job.res_id)
        store = job.store_id
        binding = self.env['shopify.connector.order.binding'].search([
            ('store_id', '=', store.id),
            ('sale_order_id', '=', picking.sale_id.id),
        ], limit=1)
        if not binding or not binding.shopify_gid:
            raise JobHandlerError(
                'mapping_missing',
                'The picking has no resolvable Shopify order binding.',
            )
        # Idempotent: a picking is one fulfillment event.
        if self.env['shopify.connector.fulfillment.binding'].search_count([
            ('store_id', '=', store.id), ('picking_id', '=', picking.id),
        ]):
            return
        try:
            fos = self._read_fulfillment_orders(store, binding.shopify_gid)
        except FulfillmentReadError as exc:
            raise JobHandlerError(exc.error_class, exc.message)

        eligible = []
        for fo in fos:
            status = fo.get('status')
            if status in FO_BLOCKING_STATUSES:
                raise JobHandlerError(
                    'ambiguous_match',
                    'A FulfillmentOrder is %s; the connector never places or '
                    'releases holds.' % status,
                )
            if status in FO_ELIGIBLE_STATUSES:
                actions = {
                    (a or {}).get('action')
                    for a in (fo.get('supportedActions') or [])
                }
                if CREATE_FULFILLMENT_ACTION in actions:
                    eligible.append(fo)
        if not eligible:
            raise JobHandlerError(
                'ambiguous_match',
                'No eligible FulfillmentOrder supports CREATE_FULFILLMENT.',
            )
        try:
            line_inputs, _diag = self._match_picking_to_fo_lines(picking, eligible)
            shipped_fos = [fo for fo in eligible if fo.get('id') in line_inputs]
            self._resolve_single_location(store, shipped_fos)
        except FulfillmentReadError as exc:
            raise JobHandlerError(exc.error_class, exc.message)

        # Notification-confirmation gate (RA-009): if the store wants
        # notifications but has not confirmed, surface it rather than silently
        # not notifying.
        settings = self._fulfillment_settings(store)
        if (
            settings and settings.notification_default_enabled
            and not settings.fulfillment_notification_confirmed
        ):
            raise JobHandlerError(
                'fulfillment_notification_confirmation_missing',
                'Customer notification is enabled but not confirmed for this '
                'store; fulfillment is held for confirmation.',
            )

        representative_fo_gid = min(line_inputs)
        self._enqueue_once(
            store, job.job_source, JOB_TYPE_CREATE,
            'create:%d' % picking.id, 'stock.picking', picking.id,
            shopify_target_gid=representative_fo_gid,
            trigger_origin=job.trigger_origin or False,
        )
        job._log_transition(
            'note',
            'Fulfillment picking admission enqueued a fulfillment_create for '
            '%d FulfillmentOrder(s).' % len(line_inputs),
        )

    # ------------------------------------------------------------------
    # Tracking-admission handler
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_tracking_admission(self, job):
        binding = self.env['shopify.connector.fulfillment.binding'].browse(
            job.res_id
        )
        if not binding.exists() or not binding.shopify_gid:
            raise JobHandlerError(
                'binding_conflict',
                'The fulfillment binding to update no longer exists.',
            )
        self._enqueue_once(
            job.store_id, job.job_source, JOB_TYPE_TRACKING_UPDATE,
            'tracking_update:%d:%s' % (
                binding.id, self._tracking_payload_hash(binding.picking_id),
            ),
            'shopify.connector.fulfillment.binding', binding.id,
            shopify_target_gid=binding.shopify_gid,
            trigger_origin=job.trigger_origin or False,
        )
        job._log_transition(
            'note',
            'Fulfillment tracking admission enqueued a '
            'fulfillment_tracking_update.',
        )
