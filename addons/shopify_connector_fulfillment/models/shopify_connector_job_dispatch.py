from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    REPLAY_POLICY_LOCAL_ONLY,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
    REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    INCONCLUSIVE_RECONCILIATION_CAP,
)

from .shopify_connector_fulfillment_create_strategy import (
    FulfillmentPreC2FailClosedError,
)
from .shopify_connector_job import (
    JOB_TYPE_CREATE,
    JOB_TYPE_INBOUND_OBSERVATION,
    JOB_TYPE_MODE2_EVALUATION,
    JOB_TYPE_MODE_SWITCH_SCAN,
    JOB_TYPE_MUTATION_RECONCILE,
    JOB_TYPE_PICKING_ADMISSION,
    JOB_TYPE_RECONCILIATION_CHECK,
    JOB_TYPE_RECONNECT_CATCHUP,
    JOB_TYPE_TRACKING_ADMISSION,
    JOB_TYPE_TRACKING_UPDATE,
)

ERROR_CLASS_TEMPORARY = 'shopify_temporary_server_network'
ERROR_CLASS_DATA_SHAPE = 'data_shape_schema_mismatch'
ERROR_CLASS_NO_STRATEGY = 'no_reconciliation_strategy'
SUBREASON_DUPLICATE_RISK = 'duplicate_risk'
SUBREASON_NO_STRATEGY = 'no_reconciliation_strategy'
SUBREASON_STORE_IDENTITY = 'store_identity_mismatch'
ERROR_CLASS_STORE_IDENTITY = 'store_identity_mismatch'


class ShopifyConnectorJobDispatchFulfillmentExtension(models.AbstractModel):
    """Seam 5: register the fulfillment handlers, replay policies, and the two
    mutation-domain strategies (add-only merges), the shared reconcile handler,
    and the pre-C2 fail-closed recovery seam."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        Service = self.env['shopify.connector.fulfillment.service']
        handlers.update({
            JOB_TYPE_PICKING_ADMISSION:
                Service._handle_fulfillment_picking_admission,
            JOB_TYPE_TRACKING_ADMISSION:
                Service._handle_fulfillment_tracking_admission,
            # The two mutation types are executed by the C1/C2/NET/C3 wrapper
            # (`_drain_mutation_one`), never by these placeholder handlers; they
            # are registered so the build-time handler/replay completeness
            # invariant holds.
            JOB_TYPE_CREATE: self._handle_fulfillment_mutation_placeholder,
            JOB_TYPE_TRACKING_UPDATE: self._handle_fulfillment_mutation_placeholder,
            JOB_TYPE_MUTATION_RECONCILE: self._handle_fulfillment_mutation_reconcile,
            JOB_TYPE_INBOUND_OBSERVATION:
                Service._handle_fulfillment_inbound_observation,
            JOB_TYPE_RECONCILIATION_CHECK:
                Service._handle_fulfillment_reconciliation_check,
            JOB_TYPE_RECONNECT_CATCHUP:
                Service._handle_fulfillment_reconnect_catchup,
            JOB_TYPE_MODE_SWITCH_SCAN:
                Service._handle_fulfillment_mode_switch_scan,
            JOB_TYPE_MODE2_EVALUATION:
                Service._handle_fulfillment_mode2_evaluation,
        })
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        policies.update({
            JOB_TYPE_PICKING_ADMISSION: REPLAY_POLICY_LOCAL_ONLY,
            JOB_TYPE_TRACKING_ADMISSION: REPLAY_POLICY_LOCAL_ONLY,
            JOB_TYPE_CREATE: REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_TRACKING_UPDATE: REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_MUTATION_RECONCILE: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_INBOUND_OBSERVATION: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_RECONCILIATION_CHECK: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_RECONNECT_CATCHUP: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_MODE_SWITCH_SCAN: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_MODE2_EVALUATION: REPLAY_POLICY_LOCAL_ONLY,
        })
        return policies

    @api.model
    def _get_reconciliation_strategies(self):
        strategies = dict(super()._get_reconciliation_strategies())
        Service = self.env['shopify.connector.fulfillment.service']
        strategies[JOB_TYPE_CREATE] = {
            'reconciliation_job_type': JOB_TYPE_MUTATION_RECONCILE,
            'prepare_local': Service._prepare_local_fulfillment_create,
            'prepare_preconditions':
                Service._prepare_preconditions_fulfillment_create,
            'transport': Service._transport_fulfillment_create,
            'classify_direct_result': Service._classify_direct_fulfillment_create,
            'reconcile': Service._reconcile_fulfillment_create,
            'apply_consequence': Service._apply_consequence_fulfillment_create,
        }
        strategies[JOB_TYPE_TRACKING_UPDATE] = {
            'reconciliation_job_type': JOB_TYPE_MUTATION_RECONCILE,
            'prepare_local': Service._prepare_local_fulfillment_tracking_update,
            'prepare_preconditions':
                Service._prepare_preconditions_fulfillment_tracking_update,
            'transport': Service._transport_fulfillment_tracking_update,
            'classify_direct_result':
                Service._classify_direct_fulfillment_tracking_update,
            'reconcile': Service._reconcile_fulfillment_tracking_update,
            'apply_consequence':
                Service._apply_consequence_fulfillment_tracking_update,
        }
        return strategies

    @api.model
    def _handle_fulfillment_mutation_placeholder(self, job):
        raise ValidationError(
            'Fulfillment mutation jobs must be executed by the C1/C2/NET/C3 '
            'wrapper, never a direct handler.'
        )

    # ------------------------------------------------------------------
    # Shared reconcile handler (both mutation domains; dispatch by
    # mutation_domain). Post-C2 acts on APPLIED / INCONCLUSIVE only — never
    # NOT_APPLIED, never a resend.
    # ------------------------------------------------------------------

    @api.model
    def _handle_fulfillment_mutation_reconcile(self, job):
        attempt = job.mutation_attempt_id
        if not attempt:
            job._transition_failed_final(
                'unknown_system_error',
                'The reconciliation job has no mutation-attempt link.',
            )
            return
        original = attempt.job_id
        if attempt.observed_outcome == 'pending':
            self._block_original_job(
                original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'Pending attempt reached reconciliation without recovery.',
            )
            self._complete_reconciliation_job(
                job, 'Pending reconciliation attempt was refused.',
            )
            return
        if attempt.effective_disposition() != 'unresolved':
            self._complete_reconciliation_job(
                job, 'Mutation attempt was already resolved.',
            )
            return
        try:
            strategy = self._validated_mutation_strategy(attempt.mutation_domain)
        except ValidationError:
            self._block_original_job(
                original, ERROR_CLASS_NO_STRATEGY, SUBREASON_NO_STRATEGY,
                'No valid reconciliation strategy is registered.',
            )
            self._complete_reconciliation_job(
                job, 'Missing strategy was routed to the original job.',
            )
            return
        # Read execution and result validation are SEPARATE try blocks: a
        # transient read failure retries the read-safe job; only a genuinely
        # malformed returned structure blocks (LL-013).
        try:
            result = strategy['reconcile'](attempt)
        except JobHandlerError:
            raise
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            raise
        except Exception as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The reconciliation read failed transiently; retry required.',
                type(exc).__name__,
            ) from exc
        # Wave 4 P0 defence in depth: post-C2 has only APPLIED / INCONCLUSIVE. A
        # reconcile callback that (incorrectly) returns `not_applied` is coerced
        # to inconclusive BEFORE validation — a post-C2 read result may never
        # authorize a replacement mutation. (The fulfillment callbacks never
        # emit not_applied; this guards a future/rogue callback.)
        if isinstance(result, dict) and result.get('verdict') == 'not_applied':
            result = dict(
                result, verdict='inconclusive', action=None,
                error_class=None, manual_review_subreason=None,
            )
        try:
            normalized = self._validate_reconciliation_result(result)
        except Exception:
            self._block_original_job(
                original, ERROR_CLASS_DATA_SHAPE, SUBREASON_DUPLICATE_RISK,
                'The reconciliation result was malformed; no resend occurred.',
            )
            self._complete_reconciliation_job(
                job, 'Malformed read result was routed to the original job.',
            )
            return
        if normalized['observed_store_identity'] != attempt.expected_store_identity:
            self._block_original_job(
                original, ERROR_CLASS_STORE_IDENTITY, SUBREASON_STORE_IDENTITY,
                'Reconciliation observed a different Shopify store identity.',
            )
            self._complete_reconciliation_job(
                job, 'Store-identity mismatch was routed without a verdict.',
            )
            return
        # Wave 4 P0 enforcement: post-C2 has only APPLIED / INCONCLUSIVE. A
        # not_applied verdict (which the fulfillment reconcile callbacks never
        # produce) is coerced to inconclusive here — a post-C2 read result may
        # never authorize a replacement mutation.
        if normalized['verdict'] in ('inconclusive', 'not_applied'):
            count = attempt._record_inconclusive_reconciliation(
                normalized['evidence']
            )
            if count >= INCONCLUSIVE_RECONCILIATION_CAP:
                self._block_original_job(
                    original, SUBREASON_DUPLICATE_RISK, SUBREASON_DUPLICATE_RISK,
                    'Reconciliation remained inconclusive at the safety cap.',
                )
                self._complete_reconciliation_job(
                    job, 'Inconclusive reconciliation reached its safety cap.',
                )
            else:
                job._transition_retry_waiting(
                    fields.Datetime.now() + timedelta(minutes=5),
                    job.retry_count + 1,
                    ERROR_CLASS_TEMPORARY,
                    normalized['message'],
                )
            return
        # verdict == 'applied': adopt positive evidence.
        try:
            with self.env.cr.savepoint():
                attempt._record_reconciliation_result(
                    'applied', normalized['evidence'],
                )
                self._apply_validated_consequence(
                    original, attempt, 'reconciliation',
                    normalized['consequence'], strategy,
                    reconciliation_job=job,
                )
                self._complete_reconciliation_job(
                    job, 'Read-only mutation reconciliation completed (applied).',
                )
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            raise
        except Exception as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'Atomic reconciliation consequence failed; read retry required.',
                type(exc).__name__,
            ) from exc

    # ------------------------------------------------------------------
    # Pre-C2 fail-closed recovery seam
    # ------------------------------------------------------------------

    @api.model
    def _recover_pre_c2_failure(self, job_id, token, exc):
        """For FulfillmentPreC2FailClosedError only: route the still-owned job
        by the carried error_class inside the fresh recovery transaction that
        follows core's own rollback/reset (no domain commit inside
        prepare_preconditions). No mutation-attempt row exists (C2 never
        reached) and no transport occurred. Every other exception delegates to
        core's generic bounded-retry recovery."""
        if not isinstance(exc, FulfillmentPreC2FailClosedError):
            return super()._recover_pre_c2_failure(job_id, token, exc)
        self.env.cr.rollback()
        self.env.transaction.reset()
        Job = self.env['shopify.connector.job']
        job = Job.browse(job_id).try_lock_for_update()
        if not job:
            self.env.cr.commit()
            return
        job.invalidate_recordset()
        attempt_exists = bool(
            self.env['shopify.connector.mutation.attempt'].search_count([
                ('job_id', '=', job_id),
            ])
        )
        if (
            not attempt_exists
            and job.current_attempt_token == token
            and job.state == 'running'
        ):
            job.sudo().write(self._owner_cleanup_values())
            self._route_failure(job, exc.error_class, exc.message)
        self.env.cr.commit()
