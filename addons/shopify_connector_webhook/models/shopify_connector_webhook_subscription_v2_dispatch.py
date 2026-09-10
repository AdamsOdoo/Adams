"""P11 subscription runtime cutover on the established job dispatcher.

The core Layer-2 dispatcher remains the single claim/C1/C2/transport/C3
protocol.  This addon only admits its subscription jobs, keeps V2 rows out of
the legacy/read-only paths, and attaches V2 reconciliation evidence to the
same run.  There is no second queue, transport loop, or retry implementation.
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.shopify_connector_core.runtime.p10_decisions import (
    project_run_state,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
)

from .shopify_connector_webhook_subscription_v2_runtime import (
    V2_SUBSCRIPTION_JOB_TYPES,
    V2_SUBSCRIPTION_MUTATIONS,
)


class ShopifyConnectorWebhookSubscriptionV2Dispatch(models.AbstractModel):
    """Route only subscription V2 rows through the existing Layer-2 seam."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _claimable_domain(self, now=False, exclude_store_ids=()):
        # The core V2 dispatcher owns the single claimable-domain seam.  Its
        # additive job-type hook already preserves the legacy ``run_id IS
        # NULL`` branch and admits only registered V2 rows.  Keeping this
        # method as a transparent inheritance point prevents P11 from
        # narrowing a later inventory/product/fulfillment union.
        return super()._claimable_domain(
            now=now, exclude_store_ids=exclude_store_ids,
        )

    @api.model
    def _get_v2_job_types(self):
        return frozenset(super()._get_v2_job_types()) | V2_SUBSCRIPTION_JOB_TYPES

    @api.model
    def _get_v2_mutation_job_types(self):
        return (
            frozenset(super()._get_v2_mutation_job_types())
            | V2_SUBSCRIPTION_MUTATIONS
        )

    @api.model
    def _v2_subscription(self):
        return self.env['shopify.connector.webhook.subscription']

    @api.model
    def _v2_admit_job(self, job, *, reconciliation=False):
        """Validate the store/run/mode fence before C1 or readback."""
        if (
            not getattr(job, 'run_id', False)
            or job.job_type not in (
                V2_SUBSCRIPTION_JOB_TYPES if reconciliation
                else V2_SUBSCRIPTION_MUTATIONS
            )
        ):
            return True
        try:
            self._v2_subscription()._v2_assert_job(
                job, reconciliation=reconciliation,
            )
        except (AccessError, ValidationError):
            self._block_original_job(
                job,
                'store_identity_mismatch',
                'store_identity_mismatch',
                'V2 subscription admission is stale or outside the current '
                'store, company, generation, or runtime mode.',
            )
            return False
        return True

    @api.model
    def _v2_validate_mutation_job(self, job, *, phase='c1'):
        # Only P11 subscription mutations receive the exact subscriptions
        # mode assertion.  Foreign V2 domains pass through this hook to their
        # own additive validator instead of being interpreted as webhooks.
        if job.job_type in V2_SUBSCRIPTION_MUTATIONS:
            self._v2_subscription()._v2_assert_job(job)
        return super()._v2_validate_mutation_job(job, phase=phase)

    @api.model
    def _v2_mark_run_running(self, job):
        run = getattr(job, 'run_id', False)
        if run and run.state in ('admitted', 'waiting'):
            run._transition_service('running')

    @api.model
    def _drain_mutation_one(self, job):
        if (
            not getattr(job, 'run_id', False)
            or job.job_type not in V2_SUBSCRIPTION_MUTATIONS
        ):
            return super()._drain_mutation_one(job)
        if not self._v2_admit_mutation_job(job, phase='c1'):
            self._block_v2_admission(job)
            self.env.cr.commit()
            return
        self._v2_mark_run_running(job)
        return super()._drain_mutation_one(job)

    @api.model
    def _v2_project_run(self, run):
        """Project one run from its durable child-job states.

        Callers that own a V2 job/attempt already hold those rows in the
        established job -> attempt -> run order.  This method is the final
        serializer in that order: unlike the non-blocking worker claim, the
        run projection must wait for another projector to finish before it
        reads child states and transitions the shared run row.
        """
        if not run or not run.exists():
            return False
        # Flush any already-owned child-job transitions before taking the run
        # lock.  A delayed child UPDATE must never acquire a job row lock
        # after this method has acquired the run row; that would reverse the
        # established job -> attempt -> run order.
        self.env['shopify.connector.job'].flush_model()
        run_id = run.id
        self.env.cr.execute(
            'SELECT id FROM shopify_connector_run '
            'WHERE id = %s FOR UPDATE',
            [run_id],
        )
        if not self.env.cr.fetchone():
            return False
        run = self.env['shopify.connector.run'].sudo().browse(run_id)
        run.invalidate_recordset(['state', 'cancel_requested_at'])
        if run.state in (
            'succeeded', 'partially_succeeded', 'failed_terminal', 'cancelled',
        ):
            return False
        self.env.cr.execute(
            'SELECT state, COUNT(*) FROM shopify_connector_job '
            'WHERE run_id = %s GROUP BY state',
            [run.id],
        )
        counts = {state: int(count) for state, count in self.env.cr.fetchall()}
        target = project_run_state(
            counts, cancel_requested=bool(run.cancel_requested_at),
        )
        if target == run.state:
            return False
        if target in (
            'succeeded', 'partially_succeeded', 'failed_terminal', 'cancelled',
        ):
            run._finish_service(target)
        else:
            run._transition_service(target)
        return True

    @api.model
    def _block_original_job(self, job, error_class, subreason, message):
        result = super()._block_original_job(
            job, error_class, subreason, message,
        )
        run = getattr(job, 'run_id', False)
        if run:
            self._v2_project_run(run)
        return result

    @api.model
    def _apply_validated_consequence(
        self, job, attempt, phase, consequence, strategy,
        reconciliation_job=False,
    ):
        result = super()._apply_validated_consequence(
            job, attempt, phase, consequence, strategy,
            reconciliation_job=reconciliation_job,
        )
        run = getattr(attempt, 'run_id', False) or getattr(
            job, 'run_id', False,
        )
        if run:
            self._v2_project_run(run)
        return result

    @api.model
    def _complete_reconciliation_job(self, job, message):
        result = super()._complete_reconciliation_job(job, message)
        attempt = getattr(job, 'mutation_attempt_id', False)
        original = getattr(attempt, 'job_id', False)
        run = getattr(attempt, 'run_id', False) or getattr(
            original, 'run_id', False,
        )
        if run:
            self._v2_project_run(run)
        return result

    @api.model
    def _ensure_reconciliation_job(self, original_job, attempt, strategy=None):
        Job = self.env['shopify.connector.job']
        # A reconciliation child is created from an immutable original job
        # and attempt pair.  Lock the original first, then the attempt; this
        # is the same order used by C2/C3 and means every original-job write
        # below is protected by the job root rather than occurring while only
        # an attempt lock is held.
        locked_original_job = Job.browse(
            original_job.id
        ).sudo().try_lock_for_update()
        if not locked_original_job:
            return Job.browse()
        locked_original_job.invalidate_recordset()
        locked_attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].browse(attempt.id).sudo().try_lock_for_update()
        if not locked_attempt:
            return Job.browse()
        locked_attempt.invalidate_recordset()
        if locked_attempt.job_id != locked_original_job:
            self._block_original_job(
                locked_original_job,
                'store_identity_mismatch',
                'store_identity_mismatch',
                'The durable V2 attempt is not owned by the original job.',
            )
            return Job.browse()
        run = getattr(locked_attempt, 'run_id', False) or getattr(
            locked_original_job, 'run_id', False,
        )
        if not run:
            return super()._ensure_reconciliation_job(
                locked_original_job, locked_attempt, strategy,
            )
        try:
            strategy = strategy or self._validated_mutation_strategy(
                locked_attempt.mutation_domain,
            )
        except ValidationError:
            self._block_original_job(
                locked_original_job,
                'no_reconciliation_strategy',
                'no_reconciliation_strategy',
                'No valid reconciliation strategy exists for this V2 attempt.',
            )
            return self.env['shopify.connector.job']
        Job = Job.sudo()
        existing = Job.search([
            ('mutation_attempt_id', '=', locked_attempt.id),
        ], limit=1)
        if existing:
            if (
                existing.state in ('succeeded', 'failed_final', 'cancelled')
                and locked_attempt.effective_disposition() == 'unresolved'
                and locked_original_job.state != 'blocked_manual_review'
            ):
                self._block_original_job(
                    locked_original_job,
                    'duplicate_risk',
                    'duplicate_risk',
                    'The V2 reconciliation job is terminal while the '
                    'mutation remains unresolved.',
                )
            return existing
        store = locked_attempt.store_id
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        if (
            not store
            or run.store_id != store
            or locked_original_job.store_id != store
            or not settings
            or settings.company_id != store.company_id
        ):
            self._block_original_job(
                locked_original_job,
                'store_identity_mismatch',
                'store_identity_mismatch',
                'The durable V2 attempt cannot be linked to a safe '
                'reconciliation scope.',
            )
            return Job.browse()
        return Job.create({
            'store_id': store.id,
            'run_id': run.id,
            'parent_job_id': locked_original_job.id,
            'job_source': 'reconciliation',
            'job_type': strategy['reconciliation_job_type'],
            'state': 'queued',
            'payload_hash': 'reconcile:%s' % locked_attempt.attempt_token,
            'mutation_attempt_id': locked_attempt.id,
            'expected_connection_generation':
                store.connection_generation,
            'expected_configuration_generation':
                settings.configuration_generation,
            'lane': 'safety_verification',
            'lane_priority': 1000,
            'available_at': fields.Datetime.now(),
        })


class ShopifyConnectorWebhookSubscriptionV2StaleSweep(models.AbstractModel):
    """Recover stale V2 owners without replaying an uncertain mutation."""

    _inherit = 'shopify.connector.stale.owner.sweep'

    @api.model
    def _sweep_v2_subscription_owners(self):
        return super()._sweep_v2_mutation_owners(
            job_types=V2_SUBSCRIPTION_MUTATIONS,
        )

    @api.model
    def run_sweep(self):
        # The shared core sweep invokes the additive mutation hook once.  Do
        # not run a second subscription-only loop: that would race the shared
        # recovery and could create a duplicate reconciliation job.
        return super().run_sweep()


__all__ = [
    'ShopifyConnectorWebhookSubscriptionV2Dispatch',
    'ShopifyConnectorWebhookSubscriptionV2StaleSweep',
]
