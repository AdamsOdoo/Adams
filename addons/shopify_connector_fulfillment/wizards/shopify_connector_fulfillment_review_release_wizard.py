"""Release-blocked-mutation wizard (display-and-delegate only).

SCOPE NOTE -- DECLARED DEVIATION FROM THE U1 LOCKED ALLOWED-FILE LIST.
`u1-locked-implementation-prompt.md` lists exactly one wizard module
(`..._mode_switch_wizard.py`), but `u1-implementation-task-breakdown.md` S4
requires the review workspace to expose
`fulfillment.binding.action_release_fulfillment_review`, and that action takes a
MANDATORY operator-supplied reason (the server raises `UserError` on an empty
one). There is no way to collect free text without a transient form, and the
core job-cancel / mutation-resolution wizards are bound to their own models and
cannot be reused. The omission is a defect in the packet's allowed-file list,
not a decision to drop the action, so this file is added deliberately and is
declared as a deviation in the PR and in `ui-u1-validation-results.md` for the
control room to ratify or reject.

This wizard adds NO business logic. It collects a reason, shows the operator
what the server will and will not do, and calls the public sanctioned action.
It never decides eligibility, never inspects or classifies the blocked mutation,
never creates a job, never writes a protected or snapshot field, and never
touches Shopify.
"""

from odoo import fields, models
from odoo.exceptions import UserError


class ShopifyConnectorFulfillmentReviewReleaseWizard(models.TransientModel):
    """Collect the mandatory reason, then delegate to the sanctioned action."""

    _name = 'shopify.connector.fulfillment.review.release.wizard'
    _description = 'Shopify Connector Fulfillment Review Release Wizard'

    binding_id = fields.Many2one(
        comodel_name='shopify.connector.fulfillment.binding',
        required=True,
        readonly=True,
    )
    # Display-only context. Read straight off the binding, never re-derived.
    store_id = fields.Many2one(
        related='binding_id.store_id',
        readonly=True,
    )
    picking_id = fields.Many2one(
        related='binding_id.picking_id',
        readonly=True,
    )
    reason = fields.Text(
        required=True,
        help='Recorded on the audit trail. The server refuses an empty reason.',
    )

    def action_confirm(self):
        """Delegate to the public sanctioned action. No local decision.

        Everything that could refuse this -- role, "exactly one blocked
        mutation", the pre-C2 / `failed_clean` precondition, the post-C2
        uncertain-outcome refusal, and lock contention -- is decided by the
        server. This method neither pre-checks nor second-guesses any of it; it
        lets the server's `AccessError` / `UserError` surface to the operator.
        """
        self.ensure_one()
        # Guard the wizard's own required field only. This is a form-level
        # nicety, not an authorization or eligibility decision: the server
        # applies the same check and is the authority.
        if not (self.reason or '').strip():
            raise UserError('Enter why this fulfilment mutation is being released.')
        return self.binding_id.action_release_fulfillment_review(
            reason=self.reason.strip(),
        )
