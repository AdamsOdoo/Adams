"""U2 display-and-delegate wizard for the order operator surfaces.

`action_approve_manual_gateway_order(reason=False)` accepts an optional
reason. It is collected here and made MANDATORY at the UI layer, which is a
deliberate asymmetry: the server keeps its permissive signature for
programmatic callers, while a human approving a manual-gateway order -- an
irreversible commercial judgement that a payment was really received outside
Shopify's gateway -- is asked to say why. The reason lands on the approval's
audit trail, which is the whole point of having one.

No business logic lives here. The wizard shows the evidence the binding
already holds, collects the reason, and delegates. Every access check,
state guard and audit write stays on the server method.
"""

from odoo import fields, models
from odoo.exceptions import UserError


class ShopifyConnectorManualGatewayApprovalWizard(models.TransientModel):
    _name = 'shopify.connector.manual.gateway.approval.wizard'
    _description = 'Shopify Connector Manual Gateway Approval'

    binding_id = fields.Many2one(
        comodel_name='shopify.connector.order.binding',
        required=True,
        readonly=True,
    )
    # Non-stored related reads, so the dialog can never show a value that
    # changed after it opened.
    shopify_order_name = fields.Char(
        related='binding_id.shopify_order_name',
        readonly=True,
    )
    manual_gateway_name = fields.Char(
        related='binding_id.manual_gateway_name',
        readonly=True,
    )
    manual_gateway_evidence_state = fields.Selection(
        related='binding_id.manual_gateway_evidence_state',
        readonly=True,
    )
    # Char, not Selection/Monetary, because that is what the binding stores.
    # Shopify reports these as strings and the connector does not own them;
    # re-typing them here would assert an ownership the backend refuses.
    shopify_financial_status_snapshot = fields.Char(
        related='binding_id.shopify_financial_status_snapshot',
        readonly=True,
    )
    shopify_order_total_amount = fields.Char(
        related='binding_id.shopify_order_total_amount',
        readonly=True,
    )
    shopify_currency_code = fields.Char(
        related='binding_id.shopify_currency_code',
        readonly=True,
    )
    reason = fields.Char(
        required=True,
        help=(
            'Why this manually-paid order is being approved. Recorded on the '
            'approval audit trail.'
        ),
    )

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get(
            'active_model'
        ) == 'shopify.connector.order.binding':
            active_id = self.env.context.get('active_id')
            if active_id:
                result['binding_id'] = active_id
        return result

    def action_confirm(self):
        self.ensure_one()
        if not self.binding_id:
            raise UserError('Select an order binding first.')
        reason = (self.reason or '').strip()
        if not reason:
            raise UserError(
                'Describe why this manually-paid order is being approved.'
            )
        return self.binding_id.action_approve_manual_gateway_order(
            reason=reason,
        )
