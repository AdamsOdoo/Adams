# Part of the Shopify Connector (U0 operator UI foundation).
#
# Transient input wizard for cancelling a Shopify connector job with a reason.
#
# This wizard owns NO business rule. It exists only to collect the mandatory
# free-text cancellation reason from the operator and hand it to the existing
# sanctioned method ``shopify.connector.job.action_cancel(reason)``, which
# remains the sole authority on:
#   * which states may be cancelled (draft / queued / running / retry_waiting);
#   * which role may cancel (Operator or Administrator);
#   * refusing generic cancel on a mutation-evidence-linked job;
#   * redacting and storing the reason on ``job.cancel_reason``.
#
# The wizard duplicates none of that. Its own reason check is a courtesy that
# surfaces the requirement before the server round-trip; the server check is
# still authoritative.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ShopifyConnectorJobCancelWizard(models.TransientModel):
    _name = 'shopify.connector.job.cancel.wizard'
    _description = 'Shopify Connector Job Cancellation Wizard'

    job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        string="Job",
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    job_state = fields.Selection(related='job_id.state', string="Current State", readonly=True)
    reason = fields.Text(
        string="Cancellation reason",
        required=True,
        help="A short, non-technical reason. It is recorded on the job's audit trail.",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if not values.get('job_id'):
            context = self.env.context
            if context.get('active_model') == 'shopify.connector.job' and context.get('active_id'):
                values['job_id'] = context['active_id']
        return values

    def action_confirm(self):
        """Validate presence of a reason, then defer entirely to the job."""
        self.ensure_one()
        if not self.reason or not self.reason.strip():
            # Mirror of the server rule, for immediate feedback only.
            raise UserError(_("A non-empty cancellation reason is required."))
        # The sanctioned method performs the real state / permission /
        # mutation-evidence checks and the redaction. We never write job
        # fields directly.
        self.job_id.action_cancel(self.reason)
        return {'type': 'ir.actions.act_window_close'}
