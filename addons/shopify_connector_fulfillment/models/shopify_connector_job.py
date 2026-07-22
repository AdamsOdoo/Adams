from odoo import api, fields, models

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)

# ----------------------------------------------------------------------
# Frozen ten-job taxonomy (packet §11.2 / DEC-038 §7.3). Exactly ten
# job_type values; one shared reconcile type; no per-domain reconcile;
# `fulfillment_review_release` is NOT a job type; `webhook` is not a Wave 4
# source. No new error_class / manual_review_subreason value is introduced.
# ----------------------------------------------------------------------
JOB_TYPE_PICKING_ADMISSION = 'fulfillment_picking_admission'
JOB_TYPE_CREATE = 'fulfillment_create'
JOB_TYPE_TRACKING_ADMISSION = 'fulfillment_tracking_admission'
JOB_TYPE_TRACKING_UPDATE = 'fulfillment_tracking_update'
JOB_TYPE_MUTATION_RECONCILE = 'fulfillment_mutation_reconcile'
JOB_TYPE_INBOUND_OBSERVATION = 'fulfillment_inbound_observation'
JOB_TYPE_RECONCILIATION_CHECK = 'fulfillment_reconciliation_check'
JOB_TYPE_RECONNECT_CATCHUP = 'fulfillment_reconnect_catchup'
JOB_TYPE_MODE_SWITCH_SCAN = 'fulfillment_mode_switch_scan'
JOB_TYPE_MODE2_EVALUATION = 'fulfillment_mode2_evaluation'

FULFILLMENT_JOB_TYPES = (
    JOB_TYPE_PICKING_ADMISSION,
    JOB_TYPE_CREATE,
    JOB_TYPE_TRACKING_ADMISSION,
    JOB_TYPE_TRACKING_UPDATE,
    JOB_TYPE_MUTATION_RECONCILE,
    JOB_TYPE_INBOUND_OBSERVATION,
    JOB_TYPE_RECONCILIATION_CHECK,
    JOB_TYPE_RECONNECT_CATCHUP,
    JOB_TYPE_MODE_SWITCH_SCAN,
    JOB_TYPE_MODE2_EVALUATION,
)

# The two remote-effect mutation domains (Q1 operation-scope override targets).
MUTATION_DOMAIN_CREATE = JOB_TYPE_CREATE
MUTATION_DOMAIN_TRACKING = JOB_TYPE_TRACKING_UPDATE
FULFILLMENT_MUTATION_JOB_TYPES = (
    MUTATION_DOMAIN_CREATE,
    MUTATION_DOMAIN_TRACKING,
)

# Trigger-origin vocabulary. `fulfillment_picking_validation` is a merged core
# value; `fulfillment_tracking_change` is the DEC-019 extension this module adds
# via selection_add (Q4).
TRIGGER_ORIGIN_PICKING = 'fulfillment_picking_validation'
TRIGGER_ORIGIN_TRACKING = 'fulfillment_tracking_change'


def fulfillment_operation_scope_key(job_type, store_id, res_id, target_gid):
    """The frozen Q1 operation-scope literals (DEC-038 §4 Q1):

    - ``fulfillment_create``          -> (store, Odoo picking, FulfillmentOrder GID)
    - ``fulfillment_tracking_update`` -> (store, fulfillment binding, Fulfillment GID)

    Rendered deterministically with the job_type prefix so the two mutation
    domains never collide even when they reference overlapping records.
    """
    return '%s:%s:%s:%s' % (job_type, store_id, res_id or '', target_gid or '')


class ShopifyConnectorJobFulfillmentExtension(models.Model):
    """Seam 1: shopify.connector.job — the ten fulfillment job_type values, the
    DEC-019 `fulfillment_tracking_change` trigger-origin extension with its
    dedicated uninstall normalization callable, the domain-flag gate, and the
    Q1 operation-scope override for the two mutation types only."""

    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[
            (JOB_TYPE_PICKING_ADMISSION, 'Fulfillment Picking Admission'),
            (JOB_TYPE_CREATE, 'Fulfillment Create'),
            (JOB_TYPE_TRACKING_ADMISSION, 'Fulfillment Tracking Admission'),
            (JOB_TYPE_TRACKING_UPDATE, 'Fulfillment Tracking Update'),
            (JOB_TYPE_MUTATION_RECONCILE, 'Fulfillment Mutation Reconciliation'),
            (JOB_TYPE_INBOUND_OBSERVATION, 'Fulfillment Inbound Observation'),
            (JOB_TYPE_RECONCILIATION_CHECK, 'Fulfillment Reconciliation Check'),
            (JOB_TYPE_RECONNECT_CATCHUP, 'Fulfillment Reconnect Catch-up'),
            (JOB_TYPE_MODE_SWITCH_SCAN, 'Fulfillment Mode-Switch Scan'),
            (JOB_TYPE_MODE2_EVALUATION, 'Fulfillment Mode 2 Evaluation'),
        ],
        ondelete={
            JOB_TYPE_PICKING_ADMISSION:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_CREATE:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_TRACKING_ADMISSION:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_TRACKING_UPDATE:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_MUTATION_RECONCILE:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_INBOUND_OBSERVATION:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_RECONCILIATION_CHECK:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_RECONNECT_CATCHUP:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_MODE_SWITCH_SCAN:
                lambda recs: recs._reassign_to_historic_job_type(),
            JOB_TYPE_MODE2_EVALUATION:
                lambda recs: recs._reassign_to_historic_job_type(),
        },
    )
    trigger_origin = fields.Selection(
        selection_add=[
            (TRIGGER_ORIGIN_TRACKING, 'Fulfillment Tracking Change'),
        ],
        ondelete={
            # A DEDICATED trigger-origin normalization callable, NOT the
            # job-type sink `_reassign_to_historic_job_type` (which only
            # retypes job_type and could neither clear nor prove zero residue
            # of the removed trigger-origin value). DEC-038 §7.5.
            TRIGGER_ORIGIN_TRACKING:
                lambda recs:
                    recs._normalize_tracking_change_trigger_origin_on_uninstall(),
        },
    )

    def _normalize_tracking_change_trigger_origin_on_uninstall(self):
        """LC-1 uninstall normalization for the removed
        `fulfillment_tracking_change` trigger-origin value (DEC-038 §7.5).

        For every record still carrying the removed value: append exactly one
        sanitized audited manual-action log preserving the original provenance,
        then replace the value with the permanent core value
        `fulfillment_picking_validation`. The value is normalized (never
        cleared) so the merged `job_source`/`trigger_origin` constraint stays
        satisfied while `job_source='odoo_event'`; `job_source` is never
        changed. Leaves no record carrying the removed value (zero residue) and
        is order-independent with the job-type `ondelete` sink.
        """
        for job in self:
            job._log_transition(
                'manual_action',
                'Trigger origin %r normalized to %r during fulfillment domain '
                'uninstall; original tracking-change provenance preserved, '
                'job_source unchanged.' % (
                    TRIGGER_ORIGIN_TRACKING, TRIGGER_ORIGIN_PICKING,
                ),
            )
            job.sudo().write({'trigger_origin': TRIGGER_ORIGIN_PICKING})
        return True

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        if job_type in FULFILLMENT_JOB_TYPES:
            return 'fulfillment_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)

    @api.depends(
        'state', 'store_id', 'res_model', 'res_id', 'shopify_target_gid',
        'superseded_by_job_id', 'job_type',
    )
    def _compute_operation_scope_key(self):
        """Override the operation-scope key for the two mutation types only
        (the Q1 literals); every other job_type — including the shared
        `fulfillment_mutation_reconcile` — keeps core's default behaviour, so
        the reconcile job owns/inherits no remote-effect scope. Same
        non-terminal/terminal lifecycle rule as core; only a different literal
        for the two mutation types."""
        super()._compute_operation_scope_key()
        for job in self:
            if job.job_type not in FULFILLMENT_MUTATION_JOB_TYPES:
                continue
            if (
                job.state in TERMINAL_JOB_STATES
                or job.superseded_by_job_id
                or not job.shopify_target_gid
                or not job.res_id
            ):
                job.operation_scope_key = False
            else:
                job.operation_scope_key = fulfillment_operation_scope_key(
                    job.job_type,
                    job.store_id.id,
                    job.res_id,
                    job.shopify_target_gid,
                )
