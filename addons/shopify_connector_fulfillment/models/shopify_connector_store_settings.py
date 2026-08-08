from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ShopifyConnectorStoreSettingsFulfillment(models.Model):
    """Fulfillment settings extension (Modes §6/§10).

    Wave 4 ships both Mode 1 and Mode 2 backend, live and effective; Wave 5
    owns only the mode UI. ``fulfillment_operating_mode`` is Administrator-only
    at the Python field-security layer (Odoo 19 ``groups=``).
    """

    _inherit = 'shopify.connector.store.settings'

    # Mode 1 (default, Odoo-controlled) vs Mode 2 (bidirectional exact
    # reconciliation). Mode 2 auto-applies an external Shopify fulfillment to
    # the Odoo delivery only when the full 16-condition checklist passes.
    fulfillment_operating_mode = fields.Selection(
        selection=[
            ('mode1', 'Mode 1 — Odoo-Controlled'),
            ('mode2', 'Mode 2 — Bidirectional Exact Reconciliation'),
        ],
        default='mode1',
        required=True,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    # True while a Mode 1 -> Mode 2 switch scan is running: Mode 2 auto-apply
    # is suspended until the safe reconciliation scan completes clean
    # (Mode 2 condition 16).
    fulfillment_switch_in_progress = fields.Boolean(
        default=False,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    # Per-run nonce for the idempotent mode-switch scan (D-014-8).
    fulfillment_mode_switch_nonce = fields.Char(
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    # A mode switch is a durable, job-bound request rather than a transient
    # Boolean.  Keep the effective mode separate from the requested mode so a
    # failed verification always falls back to a truthful, recoverable Mode 1
    # while retaining the exact run that produced the outcome.
    fulfillment_requested_mode = fields.Selection(
        selection=[
            ('mode1', 'Mode 1 — Odoo-Controlled'),
            ('mode2', 'Mode 2 — Bidirectional Exact Reconciliation'),
        ],
        readonly=True,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_mode_switch_state = fields.Selection(
        selection=[
            ('queued', 'Queued'),
            ('running', 'Running'),
            ('retry_waiting', 'Waiting to retry'),
            ('failed_retryable', 'Failed — retry available'),
            ('failed_final', 'Failed — review required'),
            ('blocked', 'Blocked by verification'),
            ('admission_refused', 'Could not start'),
            ('succeeded', 'Verified'),
            ('recovered', 'Returned to Mode 1'),
        ],
        readonly=True,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_mode_switch_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        readonly=True,
        ondelete='set null',
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_mode_switch_failure_reason = fields.Char(
        readonly=True,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_mode_switch_next_action = fields.Char(
        compute='_compute_fulfillment_mode_switch_status',
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_mode_switch_next_retry_at = fields.Datetime(
        compute='_compute_fulfillment_mode_switch_status',
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_mode_switch_is_stale = fields.Boolean(
        compute='_compute_fulfillment_mode_switch_status',
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_mode_switch_verified_at = fields.Datetime(
        readonly=True,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_last_mode_switch_at = fields.Datetime(
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    fulfillment_last_mode_switch_uid = fields.Many2one(
        comodel_name='res.users',
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    # Per-store confirmation gate: a customer notification (notifyCustomer) is
    # only ever sent when notification_default_enabled AND this flag are both
    # True; otherwise the fulfillment_notification_confirmation_missing review
    # class applies (RA-009 fail-closed).
    fulfillment_notification_confirmed = fields.Boolean(default=False)
    # Reconciliation-scan watermark (D-014-8) + Mode-2 switch-scan boundary.
    fulfillment_last_reconciliation_at = fields.Datetime()
    # --- Store 360 / R-4: generation-bound fulfillment catch-up stamps ---
    # Same contract as the sale-side order stamps: a successful connection
    # probe never marks fulfillment-derived data current; only a COMPLETE
    # traversal (reconnect catch-up over every order binding, or the
    # reconciliation check over the known fulfillment population) admitted
    # at the CURRENT connection generation, whose fulfillment jobs then all
    # settle terminal and non-blocking, does. Pending fields are written by
    # the two scan handlers (only on a zero-failure pass); the durable pair
    # is promoted by the job-terminal hook in
    # `shopify_connector_fulfillment_reconnect.py`. All readonly connector
    # system state, never caller input.
    fulfillment_catchup_pending_generation = fields.Integer(
        default=0, readonly=True,
    )
    fulfillment_catchup_pending_observed_through_at = fields.Datetime(
        readonly=True,
    )
    fulfillment_catchup_pending_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        readonly=True,
        ondelete='set null',
    )
    fulfillment_catchup_generation = fields.Integer(
        default=0, readonly=True,
        help='Connection generation for which the last complete '
             'fulfillment traversal (catch-up or reconciliation check) '
             'settled with its descendant work terminal and non-blocking.',
    )
    fulfillment_catchup_observed_through_at = fields.Datetime(
        readonly=True,
        help='Shopify fulfillment evidence observed through this instant '
             'by the last complete, current-generation pass.',
    )

    @api.model
    def _sec3_parent_scope_relations(self):
        return super()._sec3_parent_scope_relations() + (
            ('fulfillment_catchup_pending_job_id', 'store'),
            ('fulfillment_mode_switch_job_id', 'store'),
        )

    @api.constrains('fulfillment_catchup_pending_job_id', 'store_id')
    def _check_catchup_job_store(self):
        """SEC-3 same-store agreement for the declared job pointer."""
        for settings in self:
            job = settings.fulfillment_catchup_pending_job_id
            if job and job.store_id != settings.store_id:
                raise ValidationError(
                    'The pending fulfillment catch-up job must belong to '
                    'the settings row\'s own store.'
                )

    @api.constrains('fulfillment_mode_switch_job_id', 'store_id')
    def _check_mode_switch_job_store(self):
        """The surfaced verification run must belong to this exact store."""
        for settings in self:
            job = settings.fulfillment_mode_switch_job_id
            if job and (
                job.store_id != settings.store_id
                or job.job_type != 'fulfillment_mode_switch_scan'
            ):
                raise ValidationError(
                    'The fulfillment mode verification job must be a mode '
                    'switch scan for the settings row\'s own store.'
                )

    @api.depends(
        'fulfillment_switch_in_progress',
        'fulfillment_mode_switch_state',
        'fulfillment_mode_switch_job_id.state',
        'fulfillment_mode_switch_job_id.started_at',
        'fulfillment_mode_switch_job_id.next_retry_at',
    )
    def _compute_fulfillment_mode_switch_status(self):
        """Present one bounded next step and detect an abandoned exact run."""
        stale_before = fields.Datetime.now() - timedelta(minutes=30)
        for settings in self:
            job = settings.fulfillment_mode_switch_job_id
            state = settings.fulfillment_mode_switch_state
            settings.fulfillment_mode_switch_next_retry_at = (
                job.next_retry_at if job and state == 'retry_waiting' else False
            )
            settings.fulfillment_mode_switch_is_stale = bool(
                settings.fulfillment_switch_in_progress
                and (
                    not job
                    or (
                        job.state == 'running'
                        and job.started_at
                        and job.started_at < stale_before
                    )
                )
            )
            if settings.fulfillment_mode_switch_is_stale:
                next_action = 'Return to Mode 1 to recover the stale request.'
            elif state in ('queued', 'running'):
                next_action = 'Wait for the verification run to finish.'
            elif state == 'retry_waiting':
                next_action = 'Wait for the scheduled retry, or return to Mode 1.'
            elif state in ('failed_retryable', 'failed_final'):
                next_action = 'Retry verification, or return to Mode 1.'
            elif state == 'blocked':
                next_action = 'Review the surfaced blockers before retrying.'
            elif state == 'admission_refused':
                next_action = 'Restore the store connection, then try again.'
            else:
                next_action = False
            settings.fulfillment_mode_switch_next_action = next_action

    def _fulfillment_notification_allowed(self):
        """True only when the store has both enabled the default notification
        and confirmed it — else notifications fail closed (RA-009)."""
        self.ensure_one()
        return bool(
            self.notification_default_enabled
            and self.fulfillment_notification_confirmed
        )
