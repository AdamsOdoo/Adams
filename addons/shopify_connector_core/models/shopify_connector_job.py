from odoo import api, fields, models
from odoo.exceptions import ValidationError

# Shared with shopify_connector_job_log.py (from_state/to_state) so the two
# models can never drift apart on the job state vocabulary (DEC-009).
JOB_STATE_SELECTION = [
    ('draft', 'Draft'),
    ('queued', 'Queued'),
    ('running', 'Running'),
    ('succeeded', 'Succeeded'),
    ('failed_final', 'Failed (Final)'),
    ('skipped', 'Skipped'),
    ('cancelled', 'Cancelled'),
    ('retry_waiting', 'Retry Waiting'),
    ('failed_retryable', 'Failed (Retryable)'),
    ('blocked_manual_review', 'Blocked - Manual Review'),
]

TERMINAL_JOB_STATES = ('succeeded', 'failed_final', 'skipped', 'cancelled')

# The six DEC-009 §D.5.4 confirmation-required error classes, reused as
# both a subset of ERROR_CLASS_SELECTION and the full
# manual_review_subreason vocabulary.
MANUAL_REVIEW_SUBREASON_SELECTION = [
    ('ambiguous_match', 'Ambiguous Match'),
    ('binding_conflict', 'Binding Conflict'),
    ('duplicate_risk', 'Duplicate Risk'),
    ('destructive_write_guard_blocked', 'Destructive-Write Guard Blocked'),
    ('inventory_location_missing', 'Inventory Location Missing'),
    (
        'fulfillment_notification_confirmation_missing',
        'Fulfillment Notification Confirmation Missing',
    ),
]

ERROR_CLASS_SELECTION = [
    ('shopify_throttling_rate_limit', 'Shopify Throttling / Rate Limit'),
    ('shopify_temporary_server_network', 'Shopify Temporary / Server / Network'),
    ('shopify_permission_scope_auth', 'Shopify Permission / Scope / Auth'),
    ('shopify_user_errors_validation', "Shopify userErrors / Validation"),
    ('odoo_validation_configuration', 'Odoo Validation / Configuration'),
    ('mapping_missing', 'Mapping Missing'),
] + MANUAL_REVIEW_SUBREASON_SELECTION + [
    ('financial_total_mismatch', 'Financial Total Mismatch'),
    ('data_shape_schema_mismatch', 'Data Shape / Schema Mismatch'),
    ('concurrency_race_conflict', 'Concurrency / Race Conflict'),
    ('unknown_system_error', 'Unknown / System Error'),
]


class ShopifyConnectorJob(models.Model):
    """The job/log/error/retry substrate (core-naming-schema-planning.md §4.5).

    One record per logical sync operation, carrying current state, error
    class, retry counters, the idempotency key, and the DB-backed
    serialization-guard key. No Shopify API call, webhook, or domain sync
    logic is implemented here -- only the shared state-machine schema.
    """

    _name = 'shopify.connector.job'
    _description = 'Shopify Connector Job'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    job_source = fields.Selection(
        selection=[
            ('webhook', 'Webhook'),
            ('manual_sync', 'Manual Sync'),
            ('scheduled_sync', 'Scheduled Sync'),
            ('reconciliation', 'Reconciliation'),
            ('setup_readiness_check', 'Setup Readiness Check'),
            ('export_preview_dry_run', 'Export Preview Dry Run'),
            ('odoo_event', 'Odoo Event'),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    trigger_origin = fields.Selection(
        selection=[
            ('inventory_stock_change', 'Inventory Stock Change'),
            ('fulfillment_picking_validation', 'Fulfillment Picking Validation'),
        ],
        readonly=True,
    )
    trigger_origin_event_ref = fields.Char(readonly=True)
    trigger_origin_event_at = fields.Datetime(readonly=True)
    job_type = fields.Selection(
        selection=[
            ('core_readiness_check', 'Core Readiness Check'),
            ('core_manual_maintenance', 'Core Manual Maintenance'),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=JOB_STATE_SELECTION,
        required=True,
        index=True,
        default='draft',
        readonly=True,
    )
    error_class = fields.Selection(
        selection=ERROR_CLASS_SELECTION,
        index=True,
        readonly=True,
    )
    manual_review_subreason = fields.Selection(
        selection=MANUAL_REVIEW_SUBREASON_SELECTION,
        readonly=True,
    )
    retry_count = fields.Integer(default=0, readonly=True)
    next_retry_at = fields.Datetime(readonly=True)
    res_model = fields.Char(index=True, readonly=True)
    res_id = fields.Integer(index=True, readonly=True)
    shopify_target_gid = fields.Char(index=True, readonly=True)
    payload_hash = fields.Char(readonly=True)
    idempotency_key = fields.Char(
        compute='_compute_idempotency_key',
        store=True,
        required=True,
        index=True,
        readonly=True,
    )
    operation_scope_key = fields.Char(
        compute='_compute_operation_scope_key',
        store=True,
        index=True,
        readonly=True,
    )
    enqueue_decisions = fields.Text(readonly=True)
    superseded_by_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        readonly=True,
    )
    cancel_reason = fields.Char(readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)

    _sql_constraints = [
        (
            'store_idempotency_key_uniq',
            'unique(store_id, idempotency_key)',
            'A job with this idempotency key already exists for this store.',
        ),
        (
            'store_operation_scope_key_uniq',
            'unique(store_id, operation_scope_key)',
            'A non-terminal job already holds this operation scope for this store.',
        ),
    ]

    @api.depends(
        'store_id', 'job_type', 'res_model', 'res_id',
        'shopify_target_gid', 'payload_hash',
    )
    def _compute_idempotency_key(self):
        # Answers "is this the same operation, same target, same payload,
        # already known?" (core-naming-schema-planning.md §8). Persists
        # for the life of the job -- never recomputed to a falsy value.
        for job in self:
            job.idempotency_key = '|'.join(
                str(part) if part else ''
                for part in (
                    job.store_id.id,
                    job.job_type,
                    job.res_model,
                    job.res_id,
                    job.shopify_target_gid,
                    job.payload_hash,
                )
            )

    @api.depends(
        'state', 'store_id', 'res_model', 'res_id', 'shopify_target_gid',
        'superseded_by_job_id',
    )
    def _compute_operation_scope_key(self):
        # The DB-backed serialization guard key (§8): populated only
        # while the job is non-terminal and has a known target; cleared
        # on reaching a terminal state or being superseded, so a
        # terminal-or-superseded job never collides with a new job under
        # the (store_id, operation_scope_key) unique constraint.
        for job in self:
            if (
                job.state in TERMINAL_JOB_STATES
                or job.superseded_by_job_id
                or not job.res_model
            ):
                job.operation_scope_key = False
            else:
                job.operation_scope_key = '|'.join(
                    str(part) if part else ''
                    for part in (
                        job.store_id.id,
                        job.res_model,
                        job.res_id,
                        job.shopify_target_gid,
                    )
                )

    @api.constrains('job_source', 'trigger_origin')
    def _check_trigger_origin_required(self):
        for job in self:
            if job.job_source == 'odoo_event' and not job.trigger_origin:
                raise ValidationError(
                    "trigger_origin is required when job_source is 'odoo_event'."
                )
            if job.job_source != 'odoo_event' and job.trigger_origin:
                raise ValidationError(
                    "trigger_origin must be empty unless job_source is 'odoo_event'."
                )

    @api.constrains('state', 'manual_review_subreason')
    def _check_manual_review_subreason_required(self):
        for job in self:
            if job.state == 'blocked_manual_review' and not job.manual_review_subreason:
                raise ValidationError(
                    "manual_review_subreason is required when state is "
                    "'blocked_manual_review'."
                )
            if job.state != 'blocked_manual_review' and job.manual_review_subreason:
                raise ValidationError(
                    "manual_review_subreason must be empty unless state is "
                    "'blocked_manual_review'."
                )
