"""Fulfillment operating-mode switch confirmation wizard.

DISPLAY-AND-DELEGATE ONLY (D-P1-5, frozen by the U1 Gate-A acceptance).

What this wizard MAY do:
  * show the current mode, the requested mode and the switch-in-progress flag,
    all read straight off `shopify.connector.store.settings`;
  * show STATIC consequence copy -- the same text every time, never computed
    from the store's data;
  * show bounded, ACL-safe, explicitly NON-AUTHORITATIVE informational counts;
  * on confirm, call `action_start_mode2_switch()` or `action_rollback_to_mode1()`.

What this wizard MUST NOT do, and does not:
  * decide, propose or alter the target mode -- the target is derived once, from
    the current mode, and the sanctioned action re-checks everything;
  * determine eligibility, blockers, or whether a review is required;
  * predict whether the switch will succeed;
  * alter an action argument (neither sanctioned action takes one);
  * create a Job, write a protected or snapshot field, or perform any mutation;
  * call Shopify or read a credential.

The counts below exist so an administrator is not confirming blind. They are
labelled non-authoritative in the view because SEC-3 record rules exclude rows
withheld for an administrator review, so no count reachable from a UI read is a
complete count.
"""

from odoo import api, fields, models


class ShopifyConnectorFulfillmentModeSwitchWizard(models.TransientModel):
    """Confirmation screen for the Mode 1 <-> Mode 2 switch."""

    _name = 'shopify.connector.fulfillment.mode.switch.wizard'
    _description = 'Shopify Connector Fulfillment Mode Switch Wizard'

    settings_id = fields.Many2one(
        comodel_name='shopify.connector.store.settings',
        required=True,
        readonly=True,
    )
    store_id = fields.Many2one(
        related='settings_id.store_id',
        readonly=True,
    )
    # Read-only mirrors of the current state. These are Administrator-only
    # fields on the settings model; a non-Administrator never reaches this
    # wizard because `action_start_mode2_switch` / `action_rollback_to_mode1`
    # raise AccessError, and the buttons that open it are Administrator-gated.
    current_mode = fields.Selection(
        related='settings_id.fulfillment_operating_mode',
        readonly=True,
    )
    switch_in_progress = fields.Boolean(
        related='settings_id.fulfillment_switch_in_progress',
        readonly=True,
    )
    last_switch_at = fields.Datetime(
        related='settings_id.fulfillment_last_mode_switch_at',
        readonly=True,
    )

    # The requested target. Derived ONCE from the current mode and never chosen
    # by the operator -- there are only two modes, so "the other one" is not a
    # decision. Readonly in the view; the sanctioned action is still the
    # authority and re-checks the current mode itself (and no-ops if already
    # in the target mode).
    target_mode = fields.Selection(
        selection=[
            ('mode1', 'Mode 1 - Odoo-Controlled'),
            ('mode2', 'Mode 2 - Bidirectional Exact Reconciliation'),
        ],
        readonly=True,
    )

    # Bounded, ACL-safe, NON-AUTHORITATIVE informational counts.
    open_review_count = fields.Integer(
        readonly=True,
        help='Indicative only. Records withheld for an administrator review are '
             'excluded, so this is not a complete count, and it never decides '
             'whether the switch may proceed.',
    )
    in_flight_job_count = fields.Integer(
        readonly=True,
        help='Indicative only. It never decides whether the switch may proceed.',
    )

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        settings_id = self.env.context.get('default_settings_id')
        if not settings_id:
            return result
        settings = self.env['shopify.connector.store.settings'].browse(settings_id)
        store = settings.store_id
        # "The other mode". Not a recommendation and not an eligibility
        # decision -- the sanctioned action re-derives and re-checks.
        result['target_mode'] = (
            'mode2' if settings.fulfillment_operating_mode == 'mode1' else 'mode1'
        )
        # Bounded reads through the CALLER's own rights -- no sudo(), so record
        # rules (including the SEC-3 fail-closed rules) apply exactly as they do
        # everywhere else. `limit` keeps an unbounded scan off a confirmation
        # screen.
        result['open_review_count'] = self.env[
            'shopify.connector.fulfillment.inbound.evidence'
        ].search_count(
            [('store_id', '=', store.id), ('reconciled_state', '=', 'review')],
            limit=1000,
        )
        result['in_flight_job_count'] = self.env['shopify.connector.job'].search_count(
            [
                ('store_id', '=', store.id),
                ('state', 'in', ('queued', 'running', 'retry_waiting')),
            ],
            limit=1000,
        )
        return result

    def action_confirm(self):
        """Call the sanctioned action for the target mode. Nothing else.

        The branch below selects which public action to call; it does not decide
        whether the switch is allowed. Both actions enforce the Administrator
        gate server-side and raise `AccessError` otherwise, and
        `action_start_mode2_switch` is an idempotent no-op when the store is
        already in Mode 2.
        """
        self.ensure_one()
        if self.target_mode == 'mode2':
            return self.settings_id.action_start_mode2_switch()
        return self.settings_id.action_rollback_to_mode1()
