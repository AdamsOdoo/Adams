# Part of the Shopify Connector (U0 operator UI foundation).
#
# Transient input wizard for an administrator to resolve an *uncertain*
# Shopify mutation attempt.
#
# This wizard owns NO business rule and writes NO mutation-attempt field
# directly. It collects the administrator's judgement (applied / not applied)
# and a mandatory reason, then calls the existing sanctioned method
# ``shopify.connector.mutation.attempt.action_resolve_mutation_attempt(
# disposition, reason)``, which remains the sole authority on:
#   * Administrator-only permission;
#   * that only an ``uncertain``, not-yet-resolved attempt can be resolved;
#   * applying the validated consequence to the owning job and cancelling
#     any live reconciliation jobs;
#   * redacting and recording the reason as immutable audit evidence.
#
# Resolving a mutation attempt is an audited, irreversible operator judgement.
# The wizard states that plainly; it never re-implements or weakens the rule.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShopifyConnectorMutationResolutionWizard(models.TransientModel):
    _name = 'shopify.connector.mutation.resolution.wizard'
    _description = 'Shopify Connector Mutation Attempt Resolution Wizard'

    mutation_attempt_id = fields.Many2one(
        comodel_name='shopify.connector.mutation.attempt',
        string="Mutation attempt",
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    mutation_domain = fields.Char(related='mutation_attempt_id.mutation_domain', readonly=True)
    observed_outcome = fields.Selection(
        related='mutation_attempt_id.observed_outcome', string="Observed outcome", readonly=True,
    )
    disposition = fields.Selection(
        selection=[
            ('applied', "Applied — the change did take effect in Shopify"),
            ('not_applied', "Not applied — the change did not take effect"),
        ],
        string="Administrator decision",
        required=True,
        help="State whether the uncertain change actually took effect in Shopify.",
    )
    reason = fields.Text(
        string="Reason",
        required=True,
        help="What evidence supports this decision. Recorded as immutable audit evidence.",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if not values.get('mutation_attempt_id'):
            context = self.env.context
            if context.get('active_model') == 'shopify.connector.mutation.attempt' and context.get('active_id'):
                values['mutation_attempt_id'] = context['active_id']
        return values

    def action_confirm(self):
        """Validate inputs, then defer entirely to the sanctioned method."""
        self.ensure_one()
        if not self.disposition:
            raise UserError(_("Choose whether the change was applied or not applied."))
        if not self.reason or not self.reason.strip():
            raise UserError(_("A non-empty resolution reason is required."))
        # Administrator-only permission, the uncertain/not-yet-resolved
        # precondition, and the audit write all live in this sanctioned method.
        self.mutation_attempt_id.action_resolve_mutation_attempt(self.disposition, self.reason)
        return {'type': 'ir.actions.act_window_close'}
