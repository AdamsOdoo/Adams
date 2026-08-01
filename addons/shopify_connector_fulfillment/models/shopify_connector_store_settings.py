from odoo import fields, models


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

    def _fulfillment_notification_allowed(self):
        """True only when the store has both enabled the default notification
        and confirmed it — else notifications fail closed (RA-009)."""
        self.ensure_one()
        return bool(
            self.notification_default_enabled
            and self.fulfillment_notification_confirmed
        )
