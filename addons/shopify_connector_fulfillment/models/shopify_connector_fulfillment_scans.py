import json
import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .shopify_connector_fulfillment_reader import FulfillmentReadError
from .shopify_connector_job import (
    JOB_TYPE_INBOUND_OBSERVATION,
    JOB_TYPE_MODE2_EVALUATION,
    JOB_TYPE_MODE_SWITCH_SCAN,
)

_logger = logging.getLogger(__name__)

# Bounded batch of bound fulfillments refreshed per reconciliation-check run.
RECONCILE_BATCH = 200


class ShopifyConnectorFulfillmentScans(models.AbstractModel):
    """Reconciliation-check, reconnect catch-up, and mode-switch scan handlers.

    All three are read-only + local: no Shopify mutation, no attempt ownership,
    no remote-effect operation scope. Each carries a per-run uuid nonce as its
    payload_hash so repeat/retry runs create no duplicate scan effects."""

    _inherit = 'shopify.connector.fulfillment.service'

    # ------------------------------------------------------------------
    # fulfillment_reconciliation_check (cron; D-014-8)
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_reconciliation_check(self, job):
        store = job.store_id
        Binding = self.env['shopify.connector.fulfillment.binding'].sudo()
        bindings = Binding.search(
            [('store_id', '=', store.id)], limit=RECONCILE_BATCH, order='id asc',
        )
        for binding in bindings:
            try:
                node = self._read_fulfillment(store, binding.shopify_gid)
            except FulfillmentReadError:
                continue
            if not node:
                continue
            self._refresh_binding_snapshot(binding, node)
            if node.get('status') == 'CANCELLED':
                self._flag_cancelled_binding(store, binding)
        # Re-observe bound orders for newly-appeared external fulfillments.
        for order_binding in bindings.mapped('order_binding_id'):
            if order_binding:
                self._enqueue_once(
                    store, 'reconciliation', JOB_TYPE_INBOUND_OBSERVATION,
                    'inbound:%d:%s' % (order_binding.id, uuid.uuid4().hex[:8]),
                    'shopify.connector.order.binding', order_binding.id,
                )
        self._settings(store).sudo().write({
            'fulfillment_last_reconciliation_at': fields.Datetime.now(),
        })

    @api.model
    def _refresh_binding_snapshot(self, binding, node):
        binding.sudo().write({
            'shopify_status_snapshot': node.get('status'),
            'tracking_numbers_snapshot': json.dumps([
                (t or {}).get('number')
                for t in (node.get('trackingInfo') or [])
                if isinstance(t, dict) and t.get('number')
            ]),
            'shopify_last_synced_at': fields.Datetime.now(),
        })

    @api.model
    def _flag_cancelled_binding(self, store, binding):
        # A Shopify-side CANCELLED status is a manual-review signal; nothing
        # auto-changes in Odoo (cancellation never auto-reverses stock).
        Evidence = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].sudo()
        evidence = Evidence.search([
            ('store_id', '=', store.id),
            ('shopify_fulfillment_gid', '=', binding.shopify_gid),
        ], limit=1)
        vals = {
            'reconciled_state': 'review',
            'review_reason': 'cancelled_after_validation',
        }
        if evidence:
            evidence.write(vals)
        else:
            Evidence.create(dict(
                vals,
                store_id=store.id,
                shopify_fulfillment_gid=binding.shopify_gid,
                order_binding_id=binding.order_binding_id.id,
                fulfillment_binding_id=binding.id,
                origin_class='connector',
                origin_confirmed=True,
            ))

    # ------------------------------------------------------------------
    # fulfillment_reconnect_catchup — disconnected-period externals -> review
    # in BOTH modes (Modes §7)
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_reconnect_catchup(self, job):
        store = job.store_id
        Binding = self.env['shopify.connector.order.binding'].sudo()
        order_bindings = Binding.search(
            [('store_id', '=', store.id)], limit=RECONCILE_BATCH, order='id desc',
        )
        for order_binding in order_bindings:
            if not order_binding.shopify_gid:
                continue
            try:
                fulfillments = self._read_order_fulfillments(
                    store, order_binding.shopify_gid,
                )
            except FulfillmentReadError:
                continue
            for node in fulfillments:
                if isinstance(node, dict) and node.get('id'):
                    # Force Mode 1 review: condition 14's live re-read can never
                    # retroactively authorise gap-period interleavings, so
                    # gap-period externals land as review in both modes.
                    self._observe_fulfillment(store, order_binding, node, 'mode1')

    # ------------------------------------------------------------------
    # fulfillment_mode_switch_scan — the Mode 1 -> Mode 2 switch scan
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_mode_switch_scan(self, job):
        store = job.store_id
        settings = self._settings(store)
        if not settings or not settings.fulfillment_switch_in_progress:
            # Idempotent: a re-run after the switch already completed/aborted is
            # a no-op.
            return
        Binding = self.env['shopify.connector.order.binding'].sudo()
        order_bindings = Binding.search(
            [('store_id', '=', store.id)], limit=RECONCILE_BATCH, order='id desc',
        )
        blockers = 0
        for order_binding in order_bindings:
            if not order_binding.shopify_gid:
                continue
            try:
                fulfillments = self._read_order_fulfillments(
                    store, order_binding.shopify_gid,
                )
            except FulfillmentReadError:
                # A read that cannot complete is a scan blocker (fail closed).
                blockers += 1
                continue
            for node in fulfillments:
                if not isinstance(node, dict) or not node.get('id'):
                    continue
                # Read-only classification + dedup; NO stock write during the
                # scan. Pre-existing unresolved externals stay as review cases.
                evidence = self._observe_fulfillment(
                    store, order_binding, node, 'mode1',
                )
                if evidence.reconciled_state == 'review':
                    blockers += 1
        if blockers:
            # Abort back to Mode 1; the switch does not complete.
            settings.sudo().write({
                'fulfillment_switch_in_progress': False,
                'fulfillment_operating_mode': 'mode1',
            })
            job._log_transition(
                'note',
                'Mode-switch scan surfaced %d blocker(s); aborted to Mode 1.'
                % blockers,
            )
            return
        # Scan clean: complete the switch to Mode 2.
        settings.sudo().write({
            'fulfillment_switch_in_progress': False,
            'fulfillment_operating_mode': 'mode2',
            'fulfillment_last_mode_switch_at': fields.Datetime.now(),
        })
        job._log_transition(
            'note', 'Mode-switch scan clean; Mode 2 activated.',
        )

    @api.model
    def _settings(self, store):
        return self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )

    @api.model
    def _cron_enqueue_reconciliation_checks(self):
        """Cron entry point: enqueue one reconciliation-check job (per-run uuid
        nonce) per connected, fulfillment-enabled store."""
        Settings = self.env['shopify.connector.store.settings'].sudo()
        for settings in Settings.search([('fulfillment_domain_enabled', '=', True)]):
            store = settings.store_id
            if store.state != 'connected':
                continue
            from .shopify_connector_job import JOB_TYPE_RECONCILIATION_CHECK
            self._enqueue_once(
                store, 'reconciliation', JOB_TYPE_RECONCILIATION_CHECK,
                'reconciliation_check:%d:%s' % (store.id, uuid.uuid4().hex[:8]),
                'shopify.connector.store', store.id,
            )
        return True


class ShopifyConnectorStoreSettingsModeSwitch(models.Model):
    """Admin-only mode-switch state-machine actions (Modes §6)."""

    _inherit = 'shopify.connector.store.settings'

    def _assert_mode_switch_admin(self):
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may change the '
                'fulfillment operating mode.'
            )

    def action_start_mode2_switch(self):
        """Mode 1 -> Switching_to_2: confirm, run the safe reconciliation scan;
        Mode 2 evaluation starts only after a clean scan completes. In-flight
        Layer 2 jobs are NOT cancelled."""
        self.ensure_one()
        self._assert_mode_switch_admin()
        if self.fulfillment_operating_mode == 'mode2':
            # Idempotent re-confirm: nothing changes, no duplicate scan.
            return True
        nonce = uuid.uuid4().hex
        self.sudo().write({
            'fulfillment_switch_in_progress': True,
            'fulfillment_mode_switch_nonce': nonce,
            'fulfillment_last_mode_switch_uid': self.env.uid,
        })
        self.env['shopify.connector.fulfillment.service']._enqueue_once(
            self.store_id, 'manual_sync', JOB_TYPE_MODE_SWITCH_SCAN,
            'mode_switch:%d:%s' % (self.store_id.id, nonce),
            'shopify.connector.store', self.store_id.id,
        )
        return True

    def action_rollback_to_mode1(self):
        """Mode 2 -> Mode 1: always allowed; stops future auto-application.
        In-flight Mode 2 evaluations are cancelled back to review; evidence,
        applied reconciliations, bindings, and audit are untouched; in-flight
        Layer 2 mutation/reconcile jobs are NOT cancelled by the switch."""
        self.ensure_one()
        self._assert_mode_switch_admin()
        self.sudo().write({
            'fulfillment_operating_mode': 'mode1',
            'fulfillment_switch_in_progress': False,
            'fulfillment_last_mode_switch_at': fields.Datetime.now(),
            'fulfillment_last_mode_switch_uid': self.env.uid,
        })
        # Cancel in-flight Mode 2 evaluation jobs back to review (local only).
        Job = self.env['shopify.connector.job'].sudo()
        in_flight = Job.search([
            ('store_id', '=', self.store_id.id),
            ('job_type', '=', JOB_TYPE_MODE2_EVALUATION),
            ('state', 'in', ('queued', 'retry_waiting')),
        ])
        for job in in_flight:
            if job.state in ('queued', 'retry_waiting'):
                job.write({
                    'state': 'cancelled',
                    'cancel_reason': 'Mode 2 disabled by rollback to Mode 1.',
                    'finished_at': fields.Datetime.now(),
                })
        return True
