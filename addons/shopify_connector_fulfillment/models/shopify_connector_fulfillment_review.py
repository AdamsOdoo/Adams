import json
import logging
import uuid

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from .shopify_connector_job import (
    FULFILLMENT_MUTATION_JOB_TYPES,
    JOB_TYPE_CREATE,
    JOB_TYPE_TRACKING_UPDATE,
)

_logger = logging.getLogger(__name__)


class ShopifyConnectorFulfillmentReviewService(models.AbstractModel):
    """Mode 1 review-case actions + the review-release sanctioned service helper
    (DEC-038 §7.3). The review-release is a public binding action delegating to
    a private helper here; it is NOT a job type. It releases exactly one blocked
    mutation and admits only a permitted pre-C2 / synchronous-clean-rejection
    replacement (manual_sync + empty trigger origin), under lineage."""

    _inherit = 'shopify.connector.fulfillment.service'

    # ------------------------------------------------------------------
    # Review-release sanctioned helper (releases exactly one blocked mutation)
    # ------------------------------------------------------------------

    @api.model
    def _release_blocked_mutation(self, binding, reason):
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_reviewer'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Reviewer or Administrator may release '
                'a blocked fulfillment mutation.'
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError('A non-empty release reason is required.')
        locked = binding.try_lock_for_update()
        if not locked:
            raise UserError('This fulfillment binding is held by another '
                            'operation; try again shortly.')
        locked.invalidate_recordset()
        blocked = self._find_single_blocked_mutation(locked)
        attempt = self.env['shopify.connector.mutation.attempt'].sudo().search(
            [('job_id', '=', blocked.id)], limit=1,
        )
        # Eligible only when nothing was durably sent (no attempt = pre-C2) or a
        # synchronous clean rejection (failed_clean -> not_applied). A post-C2
        # uncertain/duplicate-risk attempt is NEVER eligible for a resend.
        eligible = (not attempt) or attempt.observed_outcome == 'failed_clean'
        if not eligible:
            raise UserError(
                'This blocked mutation is a post-C2 uncertain outcome; a '
                'replacement send is not permitted (reconcile-only). Resolve '
                'it through the mutation-attempt administrator path.'
            )
        safe_reason = binding._audit_safe_reason(reason)
        new_job = self._handoff_replacement(blocked, safe_reason)
        _logger.info(
            'Fulfillment review release by actor_uid=%s: old_job=%s new_job=%s',
            self.env.uid, blocked.id, new_job.id,
        )
        return new_job

    @api.model
    def _find_single_blocked_mutation(self, binding):
        Job = self.env['shopify.connector.job']
        blocked_states = (
            'blocked_manual_review', 'failed_final', 'failed_retryable',
        )
        tracking_jobs = Job.search([
            ('store_id', '=', binding.store_id.id),
            ('state', 'in', blocked_states),
            ('job_type', '=', JOB_TYPE_TRACKING_UPDATE),
            ('res_model', '=', 'shopify.connector.fulfillment.binding'),
            ('res_id', '=', binding.id),
        ])
        create_jobs = Job.search([
            ('store_id', '=', binding.store_id.id),
            ('state', 'in', blocked_states),
            ('job_type', '=', JOB_TYPE_CREATE),
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', binding.picking_id.id),
        ])
        blocked = tracking_jobs | create_jobs
        if len(blocked) != 1:
            raise UserError(
                'Exactly one blocked fulfillment mutation is required for this '
                'binding (found %d).' % len(blocked)
            )
        job = blocked.try_lock_for_update()
        if not job:
            raise UserError('The blocked mutation is held by another operation; '
                            'try again shortly.')
        job.invalidate_recordset()
        if job.job_type not in FULFILLMENT_MUTATION_JOB_TYPES:
            raise UserError('That job is not a fulfillment mutation.')
        return job

    @api.model
    def _handoff_replacement(self, job, cancel_reason):
        """lock -> supersede (cancel) -> flush op-scope -> create the manual_sync
        replacement -> link superseded_by. The replacement always uses
        manual_sync + empty trigger origin (source/origin matrix)."""
        locked = job.try_lock_for_update()
        if not locked:
            raise UserError('The predecessor job is held by another operation.')
        locked.invalidate_recordset()
        from_state = locked.state
        # `failed_final` is terminal and cannot transition to `cancelled`
        # (LEGAL_JOB_TRANSITIONS); its operation scope is already released, so it
        # is superseded in place. A cancellable predecessor (failed_retryable /
        # blocked_manual_review) is cancelled first — which clears its scope —
        # before the replacement is created (no unique-constraint collision).
        if from_state != 'failed_final':
            locked.sudo().write({
                'state': 'cancelled',
                'cancel_reason': cancel_reason,
                'manual_review_subreason': False,
            })
            locked.flush_recordset(['state', 'operation_scope_key'])
        new_job = self.env['shopify.connector.job.enqueue'].enqueue(
            locked.store_id, 'manual_sync', locked.job_type,
            payload_hash='%s:release:%s' % (
                locked.payload_hash or locked.job_type, uuid.uuid4().hex[:12],
            ),
            res_model=locked.res_model, res_id=locked.res_id,
            shopify_target_gid=locked.shopify_target_gid,
            trigger_origin=False,
        )
        locked.sudo().write({'superseded_by_job_id': new_job.id})
        locked.invalidate_recordset()
        locked._log_transition(
            'manual_action',
            'Fulfillment mutation released and superseded by a manual_sync '
            'replacement; predecessor_job_id=%d successor_job_id=%d.' % (
                locked.id, new_job.id,
            ),
            from_state=from_state, to_state=locked.state,
        )
        return new_job

    # ------------------------------------------------------------------
    # Mode 1 review-case action helpers (delegated to by the evidence model)
    # ------------------------------------------------------------------

    @api.model
    def _review_import_tracking(self, evidence):
        picking = self._evidence_delivery_picking(evidence)
        if not picking:
            raise UserError('No Odoo delivery picking resolves for this order.')
        tracking = json.loads(evidence.tracking_snapshot or '[]')
        numbers = [t.get('number') for t in tracking if isinstance(t, dict) and t.get('number')]
        urls = [t.get('url') for t in tracking if isinstance(t, dict) and t.get('url')]
        companies = [t.get('company') for t in tracking if isinstance(t, dict) and t.get('company')]
        vals = {}
        if numbers:
            vals['carrier_tracking_ref'] = ','.join(numbers)
        if urls:
            vals['carrier_tracking_url'] = urls[0]
        if vals:
            # A non-stock write only.
            picking.write(vals)
        evidence.sudo().write({
            'reconciled_state': 'acknowledged',
            'resolution_actor_uid': self.env.uid,
            'resolution_at': fields.Datetime.now(),
        })
        return True

    @api.model
    def _review_acknowledge(self, evidence):
        evidence.sudo().write({
            'reconciled_state': 'acknowledged',
            'resolution_actor_uid': self.env.uid,
            'resolution_at': fields.Datetime.now(),
        })
        return True

    @api.model
    def _review_validate_proposed(self, evidence):
        # The explicit-user path shares the Mode 2 evaluation engine; only a
        # 16/16 pass (with the Q6 carrier guard) applies the local write.
        result = self._evaluate_mode2(evidence)
        if not result['passed']:
            raise UserError(
                'The proposed validation cannot proceed: %s.' % result['reason']
            )
        self._apply_mode2(evidence, result['plan'])
        if evidence.reconciled_state != 'applied':
            raise UserError(
                'The proposed validation was held for review (%s).'
                % (evidence.review_reason or 'unknown')
            )
        return True

    @api.model
    def _evidence_delivery_picking(self, evidence):
        if not evidence.order_binding_id:
            return self.env['stock.picking']
        pickings = evidence.order_binding_id.sale_order_id.picking_ids.filtered(
            lambda p: p.picking_type_code == 'outgoing'
            and p.location_dest_id.usage == 'customer'
        )
        return pickings[:1]


class ShopifyConnectorFulfillmentInboundEvidenceReview(models.Model):
    """Public Mode 1 review actions on the evidence (review case)."""

    _inherit = 'shopify.connector.fulfillment.inbound.evidence'

    def _assert_reviewer(self):
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_reviewer'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Operator, Reviewer, or Administrator '
                'may act on a fulfillment review case.'
            )

    def action_import_tracking(self):
        self.ensure_one()
        self._assert_reviewer()
        return self.env[
            'shopify.connector.fulfillment.service'
        ]._review_import_tracking(self)

    def action_acknowledge_external(self):
        self.ensure_one()
        self._assert_reviewer()
        return self.env[
            'shopify.connector.fulfillment.service'
        ]._review_acknowledge(self)

    def action_validate_proposed(self):
        self.ensure_one()
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_reviewer'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Reviewer or Administrator may '
                'explicitly validate a proposed fulfillment.'
            )
        return self.env[
            'shopify.connector.fulfillment.service'
        ]._review_validate_proposed(self)
