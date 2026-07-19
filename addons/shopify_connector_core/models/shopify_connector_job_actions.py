from odoo import fields, models
from odoo.exceptions import AccessError, UserError


MANUAL_RETRY_STATES = (
    'failed_retryable',
    'failed_final',
    'blocked_manual_review',
    'skipped',
)
CANCELLABLE_STATES = ('draft', 'queued', 'running', 'retry_waiting')


class ShopifyConnectorJobActions(models.Model):
    _inherit = 'shopify.connector.job'

    def action_manual_retry(self):
        self.ensure_one()
        if self.mutation_attempt_id or self.manual_review_subreason == 'duplicate_risk':
            raise UserError(
                'Mutation duplicate-risk jobs may only be resolved through '
                'action_resolve_mutation_attempt.'
            )
        from_state = self.state
        if from_state not in MANUAL_RETRY_STATES:
            raise UserError(
                "A manual retry is not allowed from state %r." % from_state
            )
        if from_state == 'blocked_manual_review':
            permitted = (
                self.env.user.has_group(
                    'shopify_connector_core.'
                    'group_shopify_connector_reviewer'
                )
                or self.env.user.has_group(
                    'shopify_connector_core.group_shopify_connector_admin'
                )
            )
        else:
            permitted = (
                self.env.user.has_group(
                    'shopify_connector_core.'
                    'group_shopify_connector_operator'
                )
                or self.env.user.has_group(
                    'shopify_connector_core.group_shopify_connector_admin'
                )
            )
        if not permitted:
            raise AccessError(
                "Your Shopify Connector role cannot retry this job."
            )

        values = {
            'state': 'queued',
            'retry_count': 0,
            'finished_at': False,
        }
        if from_state == 'blocked_manual_review':
            values['manual_review_subreason'] = False
        self.sudo().write(values)
        self._log_transition(
            'manual_action',
            'Job manually re-queued by %s.' % self.env.user.display_name,
            from_state=from_state,
            to_state='queued',
        )
        return True

    def action_cancel(self, reason=False):
        self.ensure_one()
        if not isinstance(reason, str) or not reason.strip():
            raise UserError("A non-empty cancellation reason is required.")
        from_state = self.state
        if from_state not in CANCELLABLE_STATES:
            raise UserError(
                "Cancellation is not allowed from state %r." % from_state
            )
        permitted = (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        )
        if not permitted:
            raise AccessError(
                "Your Shopify Connector role cannot cancel this job."
            )

        reason = reason.strip()
        self.sudo().write({
            'state': 'cancelled',
            'cancel_reason': reason,
            'finished_at': fields.Datetime.now(),
            'manual_review_subreason': False,
        })
        self._log_transition(
            'manual_action',
            'Job manually cancelled by %s: %s' % (
                self.env.user.display_name,
                reason,
            ),
            from_state=from_state,
            to_state='cancelled',
        )
        return True
