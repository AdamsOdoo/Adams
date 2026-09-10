import json
import logging
import uuid
from datetime import timedelta

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
    JOB_TYPE_RECONCILIATION_CHECK,
)

_logger = logging.getLogger(__name__)

# Theme E correction: the per-page size for local ORM keyset pagination (never
# a hard cap -- every scan below paginates to full completion). A partial pass
# is never reported clean/complete: reaching MAX_SCAN_PAGES before the
# eligible set is exhausted fails closed (JobHandlerError), exactly like the
# reader's own fail-closed page-cap contract (§11.4).
RECONCILE_BATCH = 200
MAX_SCAN_PAGES = 250

# PD-B4: the mode-switch scan's boundary is the earlier of (a) the last
# successful watermark minus a configured overlap, and (b) the oldest
# still-unresolved external-fulfillment evidence boundary -- bounded by a
# default lookback so an admin never accidentally triggers an unbounded
# historic re-scan. `fulfillment-operating-modes.md` §6 rule 2.
MODE_SWITCH_DEFAULT_LOOKBACK_DAYS = 30
MODE_SWITCH_WATERMARK_OVERLAP = timedelta(minutes=15)


class ShopifyConnectorFulfillmentScans(models.AbstractModel):
    """Reconciliation-check, reconnect catch-up, and mode-switch scan handlers.

    All three are read-only + local: no Shopify mutation, no attempt ownership,
    no remote-effect operation scope. Each carries a per-run uuid nonce as its
    payload_hash so repeat/retry runs create no duplicate scan effects."""

    _inherit = 'shopify.connector.fulfillment.service'

    # ------------------------------------------------------------------
    # Shared local-ORM keyset pagination (Theme E)
    # ------------------------------------------------------------------

    @api.model
    def _paginate_local_to_completion(self, Model, domain):
        """Page `Model.search(domain)` to full completion via id-keyset
        pagination (never OFFSET, which is unsafe under concurrent writes).
        Bounded by `MAX_SCAN_PAGES`: a cap reached before the eligible set is
        exhausted fails closed (raises) rather than silently returning a
        partial set that a caller could mistake for the complete population."""
        records = Model.browse()
        cursor_id = 0
        for _page in range(MAX_SCAN_PAGES):
            page = Model.search(
                domain + [('id', '>', cursor_id)],
                order='id asc', limit=RECONCILE_BATCH,
            )
            if not page:
                return records
            records |= page
            cursor_id = max(page.ids)
            if len(page) < RECONCILE_BATCH:
                return records
        raise JobHandlerError(
            'data_shape_schema_mismatch',
            'A fulfillment scan exceeded its fail-closed page cap before '
            'completing; the result is incomplete and cannot be treated as '
            'a full pass.',
        )

    @api.model
    def _mode_switch_scan_boundary(self, store, settings):
        """PD-B4: `boundary = max(floor, min(watermark - overlap, latest
        unresolved evidence boundary))`, using whichever of the two real
        boundaries exist -- the 30-day floor is a lower BOUND only, never a
        candidate inside the `min()` itself (a prior defect made the floor
        win over a later, more precise watermark/evidence boundary whenever
        one existed). The unresolved-evidence boundary is the LATEST (not
        oldest) unresolved external-fulfillment evidence, ordered by
        `first_observed_at desc`."""
        now = fields.Datetime.now()
        floor = now - timedelta(days=MODE_SWITCH_DEFAULT_LOOKBACK_DAYS)
        real_candidates = []
        if settings.fulfillment_last_reconciliation_at:
            real_candidates.append(
                settings.fulfillment_last_reconciliation_at
                - MODE_SWITCH_WATERMARK_OVERLAP
            )
        latest_unresolved = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].sudo().search([
            ('store_id', '=', store.id),
            ('reconciled_state', '=', 'review'),
        ], order='first_observed_at desc', limit=1)
        if latest_unresolved:
            real_candidates.append(latest_unresolved.first_observed_at)
        if not real_candidates:
            return floor
        return max(floor, min(real_candidates))

    # ------------------------------------------------------------------
    # fulfillment_reconciliation_check (cron; D-014-8)
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_reconciliation_check(self, job):
        store = job.store_id
        # Coverage instant for the generation-bound completion stamp: the
        # pass proves fulfillment evidence observed through the moment the
        # traversal STARTED (a conservative claim — reads happen after it).
        settings = self._settings(store)
        generation = job.expected_connection_generation
        if (
            settings.fulfillment_reconciliation_generation == generation
            and settings.fulfillment_reconciliation_observed_through_at
        ):
            cursor_id = settings.fulfillment_reconciliation_cursor_id or 0
            observed_through = (
                settings.fulfillment_reconciliation_observed_through_at
                or fields.Datetime.now()
            )
        else:
            cursor_id = 0
            observed_through = fields.Datetime.now()
            settings._settings_service_write('_fulfillment_scan', {
                'fulfillment_reconciliation_cursor_id': 0,
                'fulfillment_reconciliation_generation': generation,
                'fulfillment_reconciliation_observed_through_at':
                    observed_through,
            })
        Binding = self.env['shopify.connector.fulfillment.binding'].sudo()
        # One bounded keyset page per job keeps the cron window predictable.
        # The cursor belongs to the connection generation and a successor job
        # resumes it; only the final page advances the coverage watermark.
        bindings = Binding.search([
            ('store_id', '=', store.id),
            ('id', '>', cursor_id),
        ], order='id asc', limit=RECONCILE_BATCH)
        # Correction P1-2: a binding read that cannot complete is collected,
        # not silently skipped-and-forgotten -- the pass still processes
        # every OTHER binding it can, but a decision-critical read failure
        # must never let this handler report a successful, complete pass.
        read_failures = 0
        nodes_by_gid = {}
        if len(bindings) == 1:
            try:
                nodes_by_gid[bindings.shopify_gid] = self._read_fulfillment(
                    job, store, bindings.shopify_gid,
                )
            except FulfillmentReadError:
                read_failures = 1
        elif bindings:
            try:
                nodes_by_gid = self._read_fulfillments_batch(
                    job, store, bindings.mapped('shopify_gid'),
                )
            except FulfillmentReadError:
                read_failures = len(bindings)
        for binding in bindings:
            node = nodes_by_gid.get(binding.shopify_gid)
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
        if read_failures:
            # Fail-closed: the watermark is never stamped, and this handler
            # never reports success, when any decision-critical read was
            # incomplete -- partial local changes from the bindings that DID
            # read successfully above are real and kept, but they never
            # masquerade as a completed pass.
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'A fulfillment reconciliation check could not read %d of %d '
                'binding(s); the watermark was not advanced and this pass '
                'is not reported as complete.' % (read_failures, len(bindings)),
            )
        has_more = bool(bindings) and Binding.search_count([
            ('store_id', '=', store.id),
            ('id', '>', max(bindings.ids)),
        ], limit=1)
        if has_more:
            settings._settings_service_write('_fulfillment_scan', {
                'fulfillment_reconciliation_cursor_id': max(bindings.ids),
            })
            job.sudo().write({
                'state': 'succeeded',
                'finished_at': fields.Datetime.now(),
            })
            job._log_transition(
                'state_change',
                'Fulfillment reconciliation slice completed; the durable '
                'cursor was saved and a continuation was queued.',
                from_state='running', to_state='succeeded',
            )
            successor = self._enqueue_once(
                store, 'reconciliation', JOB_TYPE_RECONCILIATION_CHECK,
                'reconciliation_check:%d:%s' % (
                    store.id, uuid.uuid4().hex[:8],
                ),
                'shopify.connector.store', store.id,
            )
            if not successor:
                raise JobHandlerError(
                    'concurrency_race_conflict',
                    'Fulfillment reconciliation cursor was saved but no '
                    'continuation job could be admitted.',
                )
            return
        settings._settings_service_write('_fulfillment_scan', {
            'fulfillment_last_reconciliation_at': fields.Datetime.now(),
            # Store 360 / R-4 pending catch-up lineage: a genuinely complete
            # pass over the known fulfillment population, admitted at this
            # job's captured generation. Promoted to the durable completion
            # stamp by the job-terminal hook once every fulfillment job at
            # the current generation is terminal and non-blocking
            # (shopify_connector_fulfillment_reconnect.py). Only reached
            # with zero read failures — the raise above keeps a partial
            # pass from ever recording a pending claim (fail-closed).
            'fulfillment_catchup_pending_generation':
                job.expected_connection_generation,
            'fulfillment_catchup_pending_observed_through_at':
                observed_through,
            'fulfillment_catchup_pending_job_id': job.id,
            'fulfillment_reconciliation_cursor_id': 0,
            'fulfillment_reconciliation_generation': 0,
            'fulfillment_reconciliation_observed_through_at': False,
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
        observed_through = fields.Datetime.now()
        Binding = self.env['shopify.connector.order.binding'].sudo()
        # Theme E: the complete current population every run, never a fixed
        # 200-row window -- a gap-period external must never be permanently
        # skipped merely for living past an arbitrary cutoff.
        order_bindings = self._paginate_local_to_completion(
            Binding, [('store_id', '=', store.id)],
        )
        # Correction P1-2: a failed order-fulfillment read must not be
        # treated as a successful catch-up -- collect the failure and keep
        # processing every other order binding, but the handler as a whole
        # fails/retries rather than reporting completion, so the affected
        # order is retried, never permanently skipped.
        read_failures = 0
        for order_binding in order_bindings:
            if not order_binding.shopify_gid:
                continue
            try:
                fulfillments = self._read_order_fulfillments(
                    job, store, order_binding.shopify_gid,
                )
            except FulfillmentReadError:
                read_failures += 1
                continue
            for node in fulfillments:
                if isinstance(node, dict) and node.get('id'):
                    # Force Mode 1 review: condition 14's live re-read can never
                    # retroactively authorise gap-period interleavings, so
                    # gap-period externals land as review in both modes.
                    self._observe_fulfillment(store, order_binding, node, 'mode1')
        if read_failures:
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Reconnect catch-up could not read %d of %d order '
                'binding(s); this pass is not reported as a successful '
                'catch-up and the affected orders are retried, never '
                'permanently skipped.' % (read_failures, len(order_bindings)),
            )
        # Store 360 / R-4: this traversal covered EVERY order binding of the
        # store (a superset of the known-fulfillment population, so it also
        # discovers gap-period externals) with zero read failures. Record
        # the pending claim under this job's captured generation; the
        # job-terminal hook promotes it once the store's fulfillment work is
        # quiescent at the current generation. A partial traversal raised
        # above and records nothing (fail-closed, R-4 §6).
        self._settings(store)._settings_service_write('_fulfillment_scan', {
            'fulfillment_catchup_pending_generation':
                job.expected_connection_generation,
            'fulfillment_catchup_pending_observed_through_at':
                observed_through,
            'fulfillment_catchup_pending_job_id': job.id,
        })

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
        # PD-B4: the scan boundary + a complete (never fixed-200) pagination of
        # every order binding touched since that boundary.
        boundary = self._mode_switch_scan_boundary(store, settings)
        Binding = self.env['shopify.connector.order.binding'].sudo()
        try:
            order_bindings = self._paginate_local_to_completion(
                Binding,
                [('store_id', '=', store.id), ('write_date', '>=', boundary)],
            )
        except JobHandlerError:
            # Direct handler callers and the dispatcher must both see a stable,
            # recoverable Mode 1 immediately; the dispatcher will make the same
            # outcome auditable on the exact job after this error is re-raised.
            settings._settings_service_write('_fulfillment_scan', {
                'fulfillment_operating_mode': 'mode1',
                'fulfillment_requested_mode': False,
                'fulfillment_switch_in_progress': False,
                'fulfillment_mode_switch_state': 'failed_retryable',
                'fulfillment_mode_switch_failure_reason': (
                    'The verification population could not be read completely.'
                ),
            })
            raise
        blockers = 0
        for order_binding in order_bindings:
            if not order_binding.shopify_gid:
                continue
            try:
                fulfillments = self._read_order_fulfillments(
                    job, store, order_binding.shopify_gid,
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
        # The scan pass itself (the loop above) completed exhaustively --
        # `_paginate_local_to_completion` would have raised otherwise, and no
        # watermark advancement below is ever reached from a raised exception.
        # Advance the shared watermark on any genuinely completed pass,
        # whether or not blockers were found: only the MODE transition
        # depends on `blockers`, never whether the read pass finished.
        # End fence: rollback may happen while a remote read is running.  Only
        # the exact still-requested job/nonce may publish a terminal outcome;
        # a late worker can never reactivate Mode 2 after recovery.
        settings.invalidate_recordset()
        expected_nonce = (job.payload_hash or '').rsplit(':', 1)[-1]
        if not (
            settings.fulfillment_switch_in_progress
            and settings.fulfillment_requested_mode == 'mode2'
            and settings.fulfillment_mode_switch_job_id == job
            and settings.fulfillment_mode_switch_nonce == expected_nonce
        ):
            return
        now = fields.Datetime.now()
        if blockers:
            # Abort back to Mode 1; the switch does not complete.
            settings._settings_service_write('_fulfillment_scan', {
                'fulfillment_switch_in_progress': False,
                'fulfillment_operating_mode': 'mode1',
                'fulfillment_requested_mode': False,
                'fulfillment_mode_switch_state': 'blocked',
                'fulfillment_mode_switch_failure_reason': (
                    'Verification found unreadable or external fulfillment '
                    'evidence that requires review.'
                ),
                'fulfillment_last_reconciliation_at': now,
            })
            job._log_transition(
                'note',
                'Mode-switch scan surfaced %d blocker(s); aborted to Mode 1.'
                % blockers,
            )
            return
        # Scan clean: complete the switch to Mode 2.
        settings._settings_service_write('_fulfillment_scan', {
            'fulfillment_switch_in_progress': False,
            'fulfillment_operating_mode': 'mode2',
            'fulfillment_requested_mode': False,
            'fulfillment_mode_switch_state': 'succeeded',
            'fulfillment_mode_switch_failure_reason': False,
            'fulfillment_mode_switch_verified_at': now,
            'fulfillment_last_mode_switch_at': now,
            'fulfillment_last_reconciliation_at': now,
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
        nonce) per connected, fulfillment-enabled store.

        The expected `(store, operation_scope_key)` collision is already
        handled inside `_enqueue_once` itself; a genuinely unexpected
        per-store enqueue failure is logged and does not starve the remaining
        stores in the same cron run (Theme A)."""
        Settings = self.env['shopify.connector.store.settings'].sudo()
        for settings in Settings.search([('fulfillment_domain_enabled', '=', True)]):
            store = settings.store_id
            if store.state != 'connected':
                continue
            from .shopify_connector_job import JOB_TYPE_RECONCILIATION_CHECK
            try:
                self._enqueue_once(
                    store, 'reconciliation', JOB_TYPE_RECONCILIATION_CHECK,
                    'reconciliation_check:%d:%s' % (store.id, uuid.uuid4().hex[:8]),
                    'shopify.connector.store', store.id,
                )
            except Exception:
                _logger.exception(
                    'Unexpected failure enqueuing a reconciliation-check job '
                    'for store %d; continuing with the remaining stores.',
                    store.id,
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
        if (
            self.fulfillment_operating_mode == 'mode2'
            and not self.fulfillment_switch_in_progress
        ):
            # Idempotent re-confirm: nothing changes, no duplicate scan.
            return True
        current_job = self.sudo().fulfillment_mode_switch_job_id
        if (
            self.fulfillment_switch_in_progress
            and self.sudo().fulfillment_requested_mode == 'mode2'
            and current_job
            and current_job.state in ('draft', 'queued', 'running', 'retry_waiting')
        ):
            # The confirmation RPC is retry-safe and reuses the exact run.
            return True
        nonce = uuid.uuid4().hex
        try:
            job = self.env[
                'shopify.connector.fulfillment.service'
            ]._enqueue_once(
                self.store_id, 'manual_sync', JOB_TYPE_MODE_SWITCH_SCAN,
                'mode_switch:%d:%s' % (self.store_id.id, nonce),
                'shopify.connector.store', self.store_id.id,
            )
        except UserError:
            job = self.env['shopify.connector.job']
        if not job:
            self._settings_service_write('_fulfillment_mode_switch', {
                'fulfillment_operating_mode': 'mode1',
                'fulfillment_requested_mode': False,
                'fulfillment_switch_in_progress': False,
                'fulfillment_mode_switch_nonce': False,
                'fulfillment_mode_switch_job_id': False,
                'fulfillment_mode_switch_state': 'admission_refused',
                'fulfillment_mode_switch_failure_reason': (
                    'The verification run could not start. Restore the store '
                    'connection and try again.'
                ),
                'fulfillment_mode_switch_verified_at': False,
            })
            return True
        actual_nonce = (job.payload_hash or '').rsplit(':', 1)[-1]
        self._settings_service_write('_fulfillment_mode_switch', {
            'fulfillment_operating_mode': 'mode1',
            'fulfillment_requested_mode': 'mode2',
            'fulfillment_switch_in_progress': True,
            'fulfillment_mode_switch_nonce': actual_nonce,
            'fulfillment_mode_switch_state': job.state,
            'fulfillment_mode_switch_job_id': job.id,
            'fulfillment_mode_switch_failure_reason': False,
            'fulfillment_mode_switch_verified_at': False,
            'fulfillment_last_mode_switch_uid': self.env.uid,
        })
        return True

    def action_retry_mode2_switch(self):
        """Re-arm the exact failed scan; never manufacture a replacement."""
        self.ensure_one()
        self._assert_mode_switch_admin()
        job = self.sudo().fulfillment_mode_switch_job_id
        if not job or job.job_type != JOB_TYPE_MODE_SWITCH_SCAN:
            raise UserError('There is no mode verification run to retry.')
        job.with_user(self.env.user).action_manual_retry()
        self._settings_service_write('_fulfillment_mode_switch', {
            'fulfillment_operating_mode': 'mode1',
            'fulfillment_requested_mode': 'mode2',
            'fulfillment_switch_in_progress': True,
            'fulfillment_mode_switch_state': 'queued',
            'fulfillment_mode_switch_failure_reason': False,
            'fulfillment_mode_switch_verified_at': False,
            'fulfillment_last_mode_switch_uid': self.env.uid,
        })
        return True

    def action_rollback_to_mode1(self):
        """Mode 2 -> Mode 1: always allowed; stops future auto-application.
        In-flight Mode 2 evaluations are cancelled back to review; evidence,
        applied reconciliations, bindings, and audit are untouched; in-flight
        Layer 2 mutation/reconcile jobs are NOT cancelled by the switch."""
        self.ensure_one()
        self._assert_mode_switch_admin()
        self._settings_service_write('_fulfillment_mode_switch', {
            'fulfillment_operating_mode': 'mode1',
            'fulfillment_requested_mode': False,
            'fulfillment_switch_in_progress': False,
            'fulfillment_mode_switch_state': 'recovered',
            'fulfillment_mode_switch_failure_reason': False,
            'fulfillment_last_mode_switch_at': fields.Datetime.now(),
            'fulfillment_last_mode_switch_uid': self.env.uid,
        })
        # A queued/retry-waiting verification has no remote effect and can be
        # cancelled.  A running read is left alone; the end fence above makes
        # its late result inert.
        scan = self.sudo().fulfillment_mode_switch_job_id
        if scan and scan.state in ('queued', 'retry_waiting'):
            scan.sudo().write({
                'state': 'cancelled',
                'cancel_reason': 'Mode switch recovered to Mode 1.',
                'finished_at': fields.Datetime.now(),
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
