# Part of the Shopify Connector (Store 360 / R-4 slice 1).
#
# Generation-bound fulfillment catch-up: admission, fencing and completion.
#
# This wires the `fulfillment_reconnect_catchup` route that was registered,
# fully implemented (`_handle_fulfillment_reconnect_catchup`,
# shopify_connector_fulfillment_scans.py) and dispatchable at `a1c5931` —
# but had ZERO enqueue sites, a fact the job-type module recorded in-source.
# The disconnected-period external-fulfillment → review guarantee (Modes §7)
# was therefore implemented but unreachable. The reconnect lifecycle hook
# below is the one production admission point, mirroring the accepted
# product-export pattern (`shopify_connector_export_reconnect.py:271`). The
# job type is now scope-prefixed (`FULFILLMENT_SCOPE_PREFIXED_JOB_TYPES`) so
# an in-flight catch-up never collides with a reconciliation check for the
# same store.

import logging
import uuid

from odoo import api, fields, models

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)

from .shopify_connector_job import (
    FULFILLMENT_JOB_TYPES,
    JOB_TYPE_INBOUND_OBSERVATION,
    JOB_TYPE_RECONCILIATION_CHECK,
    JOB_TYPE_RECONNECT_CATCHUP,
)

_logger = logging.getLogger(__name__)

# Read-only observation/scan types an obsolete generation makes pointless:
# admission (`api_client.py:600-603`) will refuse them anyway, so they are
# cancelled at reconnect instead of failing one by one. Mutation-domain and
# LOCAL_ONLY types are deliberately NOT retired here — Layer 2 owns the
# mutation lifecycle, and a local evaluation carries no Shopify call whose
# generation could be stale.
_RETIRE_ON_RECONNECT_JOB_TYPES = (
    JOB_TYPE_RECONCILIATION_CHECK,
    JOB_TYPE_RECONNECT_CATCHUP,
    JOB_TYPE_INBOUND_OBSERVATION,
)

# States in which a FINISHED fulfillment job leaves coverage complete with no
# further proof: `succeeded` did the work; `skipped` is a recorded policy
# decision that the work was not required.
#
# `cancelled` is deliberately NOT here (PR #204 P1-1 correction, 2026-08-01).
# There is no accepted fulfillment resume route in this correction, so a
# cancelled current-generation fulfillment descendant is an unresolved
# coverage hole and BLOCKS the durable stamp. It is cleared only when a later
# reconnect starts a NEW generation and fences the older cancelled lineage
# under the existing generation rules — never by promoting over the cancel. A
# transition TO `cancelled` never itself triggers promotion.
_COVERAGE_COMPLETE_TERMINAL_STATES = ('succeeded', 'skipped')

# A cancel can only add or leave a blocker, never remove the last one, so it
# does not trigger a promotion re-check; only clean completions do.
_PROMOTION_TRIGGER_STATES = ('succeeded', 'skipped')


class ShopifyConnectorStoreFulfillmentReconnect(models.Model):
    _inherit = 'shopify.connector.store'

    def action_reconnect(self):
        before = self.connection_generation
        result = super().action_reconnect()
        self.invalidate_recordset()
        if self.state == 'connected' and self.connection_generation != before:
            self._shopify_connector_admit_fulfillment_catchup()
        return result

    def _shopify_connector_admit_fulfillment_catchup(self):
        """Admit exactly one current-generation fulfillment catch-up.

        `_enqueue_once` is the module's single idempotent enqueue choke
        point: the operation-scope key (now job-type-prefixed for this
        type) makes a second in-flight catch-up for the same store a benign
        collision, so a racing second reconnect coalesces rather than
        duplicating. A store without the fulfillment domain gets no
        catch-up and no stamp — its fulfillment data honestly remains
        non-current (fail-closed, task §8.14).
        """
        self.ensure_one()
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', self.id)], limit=1,
        )
        if not settings or not settings.fulfillment_domain_enabled:
            _logger.info(
                'Store %d reconnected: fulfillment catch-up not admitted '
                '(fulfillment domain disabled); fulfillment freshness '
                'stamps remain at their previous generation.', self.id,
            )
            return False
        self._shopify_connector_retire_stale_fulfillment_jobs()
        Service = self.env['shopify.connector.fulfillment.service']
        job = Service._enqueue_once(
            self, 'reconciliation', JOB_TYPE_RECONNECT_CATCHUP,
            'reconnect_catchup:%d:%s' % (self.id, uuid.uuid4().hex[:8]),
            'shopify.connector.store', self.id,
        )
        _logger.info(
            'Store %d reconnected: fulfillment reconnect catch-up admitted '
            'for generation %d.', self.id, self.connection_generation,
        )
        return job

    def _shopify_connector_retire_stale_fulfillment_jobs(self):
        """Cancel stale-generation read-only fulfillment scan jobs.

        Same rationale and mechanics as the order-side retirement and the
        product-export precedent: a job captured under a generation that no
        longer exists can never be admitted; cancelling records the verdict
        now and frees the operation-scope key for the current-generation
        lineage.
        """
        self.ensure_one()
        stale = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', self.id),
            ('job_type', 'in', list(_RETIRE_ON_RECONNECT_JOB_TYPES)),
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
                'Fulfillment scan job cancelled: the store has reconnected '
                'since it was enqueued, so its captured connection '
                'generation can never be admitted.',
                from_state=from_state, to_state='cancelled',
            )
        return stale


class ShopifyConnectorJobFulfillmentCatchupHook(models.Model):
    """Promotion hook: mirror of the sale-side order-catch-up promotion."""

    _inherit = 'shopify.connector.job'

    def write(self, vals):
        result = super().write(vals)
        if vals.get('state') in _PROMOTION_TRIGGER_STATES:
            stores = self.filtered(
                lambda job: job.job_type in FULFILLMENT_JOB_TYPES
            ).mapped('store_id')
            for store in stores:
                self.env[
                    'shopify.connector.store.settings'
                ]._shopify_connector_promote_fulfillment_catchup(store)
        return result


class ShopifyConnectorStoreSettingsFulfillmentCatchup(models.Model):
    _inherit = 'shopify.connector.store.settings'

    @api.model
    def _shopify_connector_promote_fulfillment_catchup(self, store):
        """Promote the pending fulfillment lineage to the durable stamp.

        Same contract as the order-side promotion
        (`_shopify_connector_promote_order_catchup`): current-generation
        pending claim, its recording job succeeded, and NO fulfillment job at
        the current generation left in a coverage-holing state. Because the
        check spans EVERY fulfillment job type, descendant reconciliation
        work (inbound observations and Mode 2 evaluations the pass enqueued)
        must settle before the stamp advances (task §8.9); a stale-generation
        lineage never stamps a newer generation (§8.5/§8.12).

        Unlike the order side, `cancelled` is UNCONDITIONALLY blocking here:
        there is no fulfillment resume route, so a cancelled current-
        generation fulfillment descendant is an unresolved hole until a later
        reconnect fences it under a new generation (P1-1 correction).
        """
        settings = self.sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings:
            return False
        pending_generation = settings.fulfillment_catchup_pending_generation
        pending_through = (
            settings.fulfillment_catchup_pending_observed_through_at
        )
        pending_job = settings.fulfillment_catchup_pending_job_id
        if not pending_through or not pending_job:
            return False
        if pending_job.state != 'succeeded':
            return False
        store.invalidate_recordset(['connection_generation'])
        current_generation = store.connection_generation
        if pending_generation != current_generation:
            return False
        if (
            settings.fulfillment_catchup_generation == current_generation
            and settings.fulfillment_catchup_observed_through_at
            and settings.fulfillment_catchup_observed_through_at
            >= pending_through
        ):
            return True
        Job = self.env['shopify.connector.job'].sudo()
        # Any current-generation fulfillment job that is not coverage-complete
        # blocks — including `cancelled`, which has no resume route to close
        # its hole (P1-1). Stale-generation cancelled jobs are excluded by the
        # generation filter, so a reconnect's own retirement never self-blocks.
        blocking = Job.search_count([
            ('store_id', '=', store.id),
            ('job_type', 'in', list(FULFILLMENT_JOB_TYPES)),
            ('expected_connection_generation', '=', current_generation),
            ('state', 'not in', list(_COVERAGE_COMPLETE_TERMINAL_STATES)),
        ])
        if blocking:
            return False
        settings.sudo().write({
            'fulfillment_catchup_generation': current_generation,
            'fulfillment_catchup_observed_through_at': pending_through,
        })
        _logger.info(
            'Store %d: fulfillment catch-up complete for generation %d; '
            'fulfillment evidence observed through %s.',
            store.id, current_generation, pending_through,
        )
        return True
