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

    def _fulfillment_notification_allowed(self):
        """True only when the store has both enabled the default notification
        and confirmed it — else notifications fail closed (RA-009)."""
        self.ensure_one()
        return bool(
            self.notification_default_enabled
            and self.fulfillment_notification_confirmed
        )
