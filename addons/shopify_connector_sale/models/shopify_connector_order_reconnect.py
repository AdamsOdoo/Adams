# Part of the Shopify Connector (Store 360 / R-4 slice 1).
#
# Generation-bound order catch-up: admission, fencing and completion.
#
# WHAT THIS CLOSES. Before this file, `action_reconnect` bumped
# `connection_generation` and stopped: order-side recovery relied on the
# next 15-minute cron scan, whose checkpoint-overlap window does re-cover
# the gap — but nothing recorded that the recovery COMPLETED, so a young
# pre-disconnect checkpoint could read as "current" the moment the probe
# passed (the exact false-green R-4 §4 forbids). The stamps written here
# are the backend prerequisite named by spec §9.3/§9.5: a successful
# connection probe alone never marks Shopify-derived order data current;
# only a COMPLETE current-generation traversal whose descendant imports all
# reached a terminal, non-blocking state does.
#
# THE LINEAGE. `run_scan` records the pending claim (generation, upper
# bound, scan job) in the same savepoint as its enumeration
# (order_scan.py). The job-terminal hook below promotes it to the durable
# completion stamp when — and only when — the pending generation still
# equals the store's CURRENT generation (a second reconnect fences the
# older lineage, R-4 §6) and no order job for that generation is
# non-terminal or in a blocking failure state. Everything runs inside the
# transaction of the transition that made the store quiescent, so the stamp
# can never outrun the work it describes.

import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)

_logger = logging.getLogger(__name__)

ORDER_CATCHUP_JOB_TYPES = ('order_import_scan', 'order_import_sync')

# States that leave order coverage provably complete for a finished job.
# `failed_final` is terminal but BLOCKING (a permanently failed import is a
# coverage hole, spec §9.3 G3); `cancelled` records an explicit operator or
# quiesce decision not to run the work — the resume path in
# `_enqueue_order` re-admits that work at the next scan, and until it lands
# the order simply is not counted imported anywhere, so a cancelled row is
# not itself a standing coverage claim.
_NON_BLOCKING_TERMINAL_STATES = ('succeeded', 'skipped', 'cancelled')


class ShopifyConnectorStoreOrderReconnect(models.Model):
    """Order-domain reaction to the one real reconnect lifecycle hook.

    Same seam as the accepted product-export pattern
    (`shopify_connector_export_reconnect.py:271`): `super()` returns
    without connecting on every non-success path, and core bumps
    `connection_generation` exactly once, only on success — so the
    generation comparison is what distinguishes an actual reconnect.
    """

    _inherit = 'shopify.connector.store'

    def action_reconnect(self):
        before = self.connection_generation
        result = super().action_reconnect()
        self.invalidate_recordset()
        if self.state == 'connected' and self.connection_generation != before:
            self._shopify_connector_admit_order_catchup()
        return result

    def _shopify_connector_admit_order_catchup(self):
        """Admit exactly one current-generation order catch-up lineage.

        Stale-generation order jobs are retired first (their admission
        would be refused anyway — `execute_business` compares the captured
        epoch — cancelling merely records that verdict now instead of
        letting them fail one by one), then one scan is enqueued; the
        in-flight dedup inside `_enqueue_order_scan` coalesces with a scan
        already admitted at the current generation, so a racing cron can
        never produce a second lineage.

        A store whose sale domain is disabled gets no catch-up — and no
        stamp, so its order data honestly remains non-current rather than
        silently green (fail-closed, R-4 §7 / task §8.14).
        """
        self.ensure_one()
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', self.id)], limit=1,
        )
        if not settings or not settings.sale_domain_enabled:
            _logger.info(
                'Store %d reconnected: order catch-up not admitted (sale '
                'domain disabled); order freshness stamps remain at their '
                'previous generation.', self.id,
            )
            return False
        self._shopify_connector_retire_stale_order_jobs()
        try:
            job = self._enqueue_order_scan('reconciliation')
        except UserError as exc:
            # The reconnect itself must not be rolled back by a catch-up
            # admission refusal; the absence of a current-generation stamp
            # already keeps the surface truthful.
            _logger.warning(
                'Store %d reconnected but the order catch-up scan could '
                'not be admitted: %s', self.id, exc,
            )
            return False
        _logger.info(
            'Store %d reconnected: order catch-up scan admitted for '
            'generation %d.', self.id, self.connection_generation,
        )
        return job

    def _shopify_connector_retire_stale_order_jobs(self):
        """Cancel non-terminal order jobs from an older connection generation.

        Mirrors `_retire_superseded_reconcile_jobs` (product export): a job
        captured under a generation that no longer exists can never be
        admitted (`api_client.py:600-603` refuses it), so leaving it queued
        only defers the same verdict into noise. Same-generation jobs are
        kept — the catch-up coalesces on them. The orders a cancelled
        import covered are re-admitted by the catch-up scan through the
        resume path in `_enqueue_order`.
        """
        self.ensure_one()
        stale = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', self.id),
            ('job_type', 'in', list(ORDER_CATCHUP_JOB_TYPES)),
            ('state', 'not in', list(TERMINAL_JOB_STATES)),
            (
                'expected_connection_generation',
                '!=', self.connection_generation,
            ),
        ])
        for job in stale:
            from_state = job.state
            job.sudo().write({
                'state': 'cancelled',
                'finished_at': fields.Datetime.now(),
                'cancel_reason': (
                    'Superseded by a later reconnect: this job covers '
                    'connection generation %s.'
                    % job.expected_connection_generation
                ),
            })
            job._log_transition(
                'manual_action',
                'Order job cancelled: the store has reconnected since it '
                'was enqueued, so its captured connection generation can '
                'never be admitted.',
                from_state=from_state, to_state='cancelled',
            )
        return stale


class ShopifyConnectorJobOrderCatchupHook(models.Model):
    """Promotion hook: the completion stamp rides the LAST terminal write.

    Every job state change flows through `write()` (all `_transition_*`
    helpers and the dispatcher's succeeded write), so observing terminal
    transitions here covers every path a job can finish by — including
    manual cancel and review resolution — without touching the dispatcher.
    """

    _inherit = 'shopify.connector.job'

    def write(self, vals):
        result = super().write(vals)
        if vals.get('state') in _NON_BLOCKING_TERMINAL_STATES:
            stores = self.filtered(
                lambda job: job.job_type in ORDER_CATCHUP_JOB_TYPES
            ).mapped('store_id')
            for store in stores:
                self.env[
                    'shopify.connector.store.settings'
                ]._shopify_connector_promote_order_catchup(store)
        return result


class ShopifyConnectorStoreSettingsOrderCatchup(models.Model):
    _inherit = 'shopify.connector.store.settings'

    @api.model
    def _shopify_connector_promote_order_catchup(self, store):
        """Promote the pending lineage to the durable completion stamp.

        Conditions, all evaluated inside the transaction of the transition
        that triggered the check (task §8.8):
          * a pending lineage exists and its scan job succeeded;
          * the pending generation equals the store's CURRENT generation —
            an older lineage never stamps a newer generation (§8.5/§8.12);
          * zero current-generation order jobs are non-terminal or in a
            blocking failure state (`failed_retryable`, `failed_final`,
            `blocked_manual_review` — §8.8's enumeration; `retry_waiting`,
            `queued`, `running`, `draft` are non-terminal and block by
            construction).

        Steady state promotes too: every completed 15-minute scan cycle
        whose imports settle re-stamps the current generation and advances
        the synchronized-through instant, which is what lets a store that
        merely upgraded (no reconnect) reach "current" within one cycle.
        """
        settings = self.sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings:
            return False
        pending_generation = settings.sale_order_catchup_pending_generation
        pending_upper = settings.sale_order_catchup_pending_upper_bound_at
        scan_job = settings.sale_order_catchup_pending_scan_job_id
        if not pending_upper or not scan_job:
            return False
        if scan_job.state != 'succeeded':
            return False
        store.invalidate_recordset(['connection_generation'])
        current_generation = store.connection_generation
        if pending_generation != current_generation:
            # Fenced: the lineage belongs to a connection that no longer
            # exists. The stamp stays at its previous value; the reconnect
            # hook has already admitted a fresh lineage.
            return False
        if (
            settings.sale_order_catchup_generation == current_generation
            and settings.sale_order_catchup_synced_through_at
            and settings.sale_order_catchup_synced_through_at
            >= pending_upper
        ):
            return True  # already promoted
        Job = self.env['shopify.connector.job'].sudo()
        blocking = Job.search_count([
            ('store_id', '=', store.id),
            ('job_type', 'in', list(ORDER_CATCHUP_JOB_TYPES)),
            ('expected_connection_generation', '=', current_generation),
            ('state', 'not in', list(_NON_BLOCKING_TERMINAL_STATES)),
        ])
        if blocking:
            return False
        settings.sudo().write({
            'sale_order_catchup_generation': current_generation,
            'sale_order_catchup_synced_through_at': pending_upper,
        })
        _logger.info(
            'Store %d: order catch-up complete for generation %d; Shopify '
            'order data synchronized through %s.',
            store.id, current_generation, pending_upper,
        )
        return True
