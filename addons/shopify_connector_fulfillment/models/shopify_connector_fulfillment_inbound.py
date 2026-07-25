import json
import logging

from odoo import api, fields, models

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .shopify_connector_fulfillment_reader import FulfillmentReadError
from .shopify_connector_job import (
    JOB_TYPE_MODE2_EVALUATION,
)

_logger = logging.getLogger(__name__)

# The seven Layer-A state families (status model §1), verified against API
# 2026-07. Only the values needed for reconciliation/gating are enumerated for
# normalization; every other observed value is preserved raw and flagged as an
# unknown-future value (never treated as success).
A4_FULFILLMENT_STATUS_KNOWN = {
    'SUCCESS': 'Success',
    'CANCELLED': 'Cancelled',
    'ERROR': 'Error',
    'FAILURE': 'Failure',
    # Deprecated (stored raw + normalized, treated non-final / unknown-not-success).
    'OPEN': 'Legacy: open',
    'PENDING': 'Legacy: pending',
}
A4_SUCCESS_VALUE = 'SUCCESS'
A4_DEPRECATED = frozenset(('OPEN', 'PENDING'))

A5_EVENT_DELIVERED = 'DELIVERED'


class ShopifyConnectorFulfillmentInbound(models.AbstractModel):
    """Inbound observation + origin classification + state normalization.

    Records every observed Shopify Fulfillment as inbound evidence with its raw
    and normalized Layer-A state, classifies its origin from the own-GID ledger
    (the authoritative signal — there is no app-attribution field), and routes
    externally-created fulfillments to a Mode 1 review case or a Mode 2
    evaluation. Never mutates Odoo stock."""

    _inherit = 'shopify.connector.fulfillment.service'

    # ------------------------------------------------------------------
    # State normalization (unknown-future-value contract, status model §7)
    # ------------------------------------------------------------------

    @api.model
    def _normalize_fulfillment_status(self, raw):
        """Return (normalized_label, is_success, is_known)."""
        if raw in A4_FULFILLMENT_STATUS_KNOWN:
            return (
                A4_FULFILLMENT_STATUS_KNOWN[raw],
                raw == A4_SUCCESS_VALUE and raw not in A4_DEPRECATED,
                True,
            )
        # Unknown future value: preserve raw, never success, flag a warning.
        return ('Unknown: %s' % (raw,), False, False)

    # ------------------------------------------------------------------
    # Origin classification (Modes §3)
    # ------------------------------------------------------------------

    @api.model
    def _classify_origin(self, store, order_binding, fulfillment_gid):
        """own-GID ledger is authoritative. Returns (origin_class, confirmed)."""
        own = self.env['shopify.connector.fulfillment.binding'].sudo().search([
            ('store_id', '=', store.id),
            ('shopify_gid', '=', fulfillment_gid),
        ], limit=1)
        if own:
            return ('connector', True)
        # Unknown-pending: an unresolved outbound mutation attempt for this
        # order might still be ours mid-flight — do not confirm external.
        if order_binding and self._has_unresolved_create_attempt(store, order_binding):
            return ('external_unknown', False)
        return ('external_merchant', True)

    @api.model
    def _has_unresolved_create_attempt(self, store, order_binding):
        picking_ids = self.env['stock.picking'].search([
            ('sale_id', '=', order_binding.sale_order_id.id),
        ]).ids
        if not picking_ids:
            return False
        # Theme J: reuse the canonical TERMINAL_JOB_STATES (already imported
        # and used elsewhere in this exact addon) rather than a hand-
        # maintained, divergence-prone local tuple. The prior
        # `('succeeded', 'skipped')` literal missed BOTH `cancelled` and
        # `failed_final`, permanently blocking Mode-2 origin confirmation
        # after an admin/disconnect-sweep cancelled or finally failed a
        # stuck create job with no mutation_attempt.
        jobs = self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'fulfillment_create'),
            ('res_model', '=', 'stock.picking'),
            ('res_id', 'in', picking_ids),
            ('state', 'not in', list(TERMINAL_JOB_STATES)),
        ])
        for job in jobs:
            attempt = job.mutation_attempt_id or self.env[
                'shopify.connector.mutation.attempt'
            ].sudo().search([('job_id', '=', job.id)], limit=1)
            if not attempt or attempt.effective_disposition() == 'unresolved':
                return True
        return False

    # ------------------------------------------------------------------
    # Observation
    # ------------------------------------------------------------------

    @api.model
    def _observe_fulfillment(self, store, order_binding, node, mode):
        """Record/refresh inbound evidence for one observed Fulfillment and
        route it. Returns the evidence record."""
        Evidence = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].sudo()
        fulfillment_gid = node.get('id')
        raw_status = node.get('status')
        label, is_success, is_known = self._normalize_fulfillment_status(raw_status)
        origin_class, origin_confirmed = self._classify_origin(
            store, order_binding, fulfillment_gid,
        )
        evidence = Evidence.search([
            ('store_id', '=', store.id),
            ('shopify_fulfillment_gid', '=', fulfillment_gid),
        ], limit=1)
        now = fields.Datetime.now()
        vals = {
            'order_binding_id': order_binding.id if order_binding else False,
            'shopify_order_gid': order_binding.shopify_gid if order_binding else False,
            'origin_class': origin_class,
            'origin_confirmed': origin_confirmed,
            'fulfillment_status_raw': raw_status,
            'fulfillment_status_normalized': label,
            'fulfillment_status_is_success': is_success,
            'display_status_raw': node.get('displayStatus'),
            'display_status_normalized': node.get('displayStatus'),
            'schema_warning': not is_known,
            'state_snapshot': json.dumps({'A4_FulfillmentStatus': raw_status,
                                          'A7_displayStatus': node.get('displayStatus')}),
            'tracking_snapshot': json.dumps(node.get('trackingInfo') or []),
            'last_observed_at': now,
        }
        if evidence:
            evidence.write(vals)
        else:
            evidence = Evidence.create(dict(
                vals,
                store_id=store.id,
                shopify_fulfillment_gid=fulfillment_gid,
                first_observed_at=now,
                reconciled_state='observed',
            ))
        self._route_observation(evidence, origin_class, origin_confirmed, mode)
        return evidence

    @api.model
    def _route_observation(self, evidence, origin_class, origin_confirmed, mode):
        # A connector-created fulfillment confirms our own outbound op; never
        # re-validated (idempotent by binding + own-GID ledger).
        if origin_class == 'connector':
            if evidence.reconciled_state == 'observed':
                evidence.write({'reconciled_state': 'applied'})
            return
        if evidence.reconciled_state in ('acknowledged', 'applied'):
            return
        if mode == 'mode2' and origin_confirmed:
            # Mode 2: hand off to the 16-condition evaluation job (local write).
            self._enqueue_once(
                evidence.store_id, 'reconciliation', JOB_TYPE_MODE2_EVALUATION,
                'mode2:%d' % evidence.id,
                'shopify.connector.fulfillment.inbound.evidence', evidence.id,
            )
            return
        # Mode 1 (or unconfirmed origin): a review case with zero stock change.
        # Theme H: the routine, everyday "merchant fulfilled in Shopify
        # admin" baseline case is `external_fulfillment_observed` — never the
        # unrelated `remote_state_changed` (Condition 14's own narrow,
        # Mode-2-only live-second-read-changed gate).
        if evidence.reconciled_state != 'review':
            evidence.write({
                'reconciled_state': 'review',
                'review_reason': 'origin_unconfirmed'
                if not origin_confirmed else 'external_fulfillment_observed',
            })

    # ------------------------------------------------------------------
    # Handler
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_inbound_observation(self, job):
        order_binding = self.env['shopify.connector.order.binding'].browse(
            job.res_id
        )
        if not order_binding.exists() or not order_binding.shopify_gid:
            return
        store = job.store_id
        mode = self._store_operating_mode(store)
        try:
            fulfillments = self._read_order_fulfillments(
                store, order_binding.shopify_gid,
            )
        except FulfillmentReadError as exc:
            raise JobHandlerError(exc.error_class, exc.message)
        for node in fulfillments:
            if isinstance(node, dict) and node.get('id'):
                self._observe_fulfillment(store, order_binding, node, mode)

    @api.model
    def _store_operating_mode(self, store):
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        if (
            settings and settings.fulfillment_operating_mode == 'mode2'
            and not settings.fulfillment_switch_in_progress
        ):
            return 'mode2'
        return 'mode1'
