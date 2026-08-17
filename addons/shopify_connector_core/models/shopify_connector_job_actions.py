from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from ..tools.redaction import redact


MANUAL_RETRY_STATES = (
    'failed_retryable',
    'failed_final',
    'blocked_manual_review',
    'skipped',
)
CANCELLABLE_STATES = ('draft', 'queued', 'running', 'retry_waiting')
HUMAN_ATTENTION_STATES = (
    'blocked_manual_review',
    'failed_final',
    'failed_retryable',
)


class ShopifyConnectorJobActions(models.Model):
    _inherit = 'shopify.connector.job'

    attention_priority = fields.Integer(
        compute='_compute_attention_priority',
        store=True,
        index=True,
        readonly=True,
    )
    attention_owner = fields.Char(
        compute='_compute_operator_presentation',
        readonly=True,
    )
    attention_reason = fields.Char(
        compute='_compute_operator_presentation',
        readonly=True,
    )
    attention_next_action = fields.Char(
        compute='_compute_operator_presentation',
        readonly=True,
    )
    recovery_owner = fields.Char(
        compute='_compute_operator_presentation',
        readonly=True,
    )
    recovery_next_action = fields.Char(
        compute='_compute_operator_presentation',
        readonly=True,
    )
    operator_has_mutation_evidence = fields.Boolean(
        compute='_compute_operator_presentation',
        readonly=True,
    )

    @api.depends('state')
    def _compute_attention_priority(self):
        priorities = {
            'blocked_manual_review': 30,
            'failed_final': 20,
            'failed_retryable': 10,
        }
        for job in self:
            job.attention_priority = priorities.get(job.state, 0)

    @api.depends(
        'state', 'error_class', 'manual_review_subreason', 'next_retry_at',
        'mutation_attempt_id',
    )
    def _compute_operator_presentation(self):
        """Project existing run facts into calm, human-owned recovery copy.

        This is presentation only. It never changes state, chooses a recovery
        consequence, or bypasses the sanctioned retry/review/mutation routes.
        Reverse-owned mutation attempts are read in one bounded query so the
        list remains useful without turning into an N+1 evidence probe.
        """
        attempts_by_job = {}
        if self.ids:
            attempts = self.env['shopify.connector.mutation.attempt'].search(
                [('job_id', 'in', self.ids)], limit=len(self.ids),
            )
            attempts_by_job = {
                attempt.job_id.id: attempt for attempt in attempts
            }
        error_labels = dict(
            self._fields['error_class']._description_selection(self.env)
        )
        review_labels = dict(
            self._fields[
                'manual_review_subreason'
            ]._description_selection(self.env)
        )
        for job in self:
            has_evidence = bool(
                job.mutation_attempt_id or attempts_by_job.get(job.id)
            )
            reason = (
                review_labels.get(job.manual_review_subreason)
                or error_labels.get(job.error_class)
                or 'No recorded failure reason'
            )
            if job.state == 'blocked_manual_review':
                owner = 'Administrator decision'
                next_action = (
                    'An Administrator must review the preserved Shopify '
                    'evidence before deciding.'
                    if has_evidence else
                    'An Administrator must open the affected record, decide '
                    'the case, then resolve it.'
                )
            elif job.state == 'failed_final':
                owner = 'Operator or Administrator'
                next_action = (
                    'Review the reason and preserved evidence before deciding '
                    'whether Retry is safe.'
                    if has_evidence else
                    'Correct the cause, then use Retry only when it is safe.'
                )
            elif job.state == 'failed_retryable':
                owner = 'Operator or Administrator'
                next_action = (
                    'Review the preserved evidence; generic Retry is disabled.'
                    if has_evidence else
                    'Correct the cause, then use Retry to queue a new run.'
                )
            elif job.state == 'retry_waiting':
                owner = 'System'
                next_action = (
                    'An automatic retry is scheduled for %s.'
                    % fields.Datetime.to_string(job.next_retry_at)
                    if job.next_retry_at else
                    'The system is waiting to retry automatically.'
                )
            elif job.state == 'queued':
                owner = 'System'
                next_action = 'Waiting for a worker; nothing has run yet.'
            elif job.state == 'running':
                owner = 'System'
                next_action = 'Background work is running.'
            elif job.state == 'succeeded':
                owner = 'Complete'
                next_action = 'No recovery action is needed.'
            elif job.state == 'cancelled':
                owner = 'Complete'
                next_action = 'Cancelled; open the run for the recorded reason.'
            elif job.state == 'skipped':
                owner = 'Operator or Administrator'
                next_action = 'Review why it was skipped before using Retry.'
            else:
                owner = 'System'
                next_action = 'Waiting for the run to be queued.'

            job.attention_owner = owner
            job.attention_reason = reason
            job.attention_next_action = next_action
            job.recovery_owner = owner
            job.recovery_next_action = next_action
            job.operator_has_mutation_evidence = has_evidence

    def _operator_mutation_attempt(self):
        """Return caller-visible evidence for this exact run, if any."""
        self.ensure_one()
        attempt = self.mutation_attempt_id
        if not attempt:
            attempt = self.env['shopify.connector.mutation.attempt'].search(
                [('job_id', '=', self.id)], limit=1,
            )
        if attempt:
            attempt.check_access('read')
        return attempt

    def _operator_form_action(self, record, name):
        record.ensure_one()
        record.check_access('read')
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': record._name,
            'res_id': record.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_open_recovery_evidence(self):
        """Open immutable Shopify evidence; never infer or apply a decision."""
        self.ensure_one()
        self.check_access('read')
        attempt = self._operator_mutation_attempt()
        if not attempt:
            raise UserError(
                'This run has no Shopify mutation evidence to review.'
            )
        return self._operator_form_action(
            attempt, 'Review Shopify write evidence'
        )

    def action_open_attention_case(self):
        """Route one human-owned case to its domain resolution flow."""
        self.ensure_one()
        self.check_access('read')
        if self.state not in HUMAN_ATTENTION_STATES:
            raise UserError(
                'This run is not waiting on a person. Open it in Runs & '
                'Recovery instead.'
            )
        resolution = self._attention_resolution_action()
        if resolution:
            return resolution
        attempt = self._operator_mutation_attempt()
        if attempt:
            return self._operator_form_action(
                attempt, 'Review Shopify write evidence'
            )
        if self.res_model and self.res_id and self.res_model in self.env:
            target = self.env[self.res_model].browse(self.res_id).exists()
            if target:
                return self._operator_form_action(
                    target, 'Resolve affected record'
                )
        return self._operator_form_action(self, 'Review connector case')

    def _attention_resolution_action(self):
        """Optional-module hook for the case's sanctioned decision UI.

        Product, tax and future domain modules extend this hook.  Keeping the
        dispatch structural prevents core from guessing a route from mutable
        error copy or depending on optional models.
        """
        self.ensure_one()
        return False

    def action_manual_retry(self):
        self.ensure_one()
        if self._has_mutation_attempt_evidence():
            raise UserError(
                'Mutation-evidence-linked jobs may only be resolved through '
                'action_resolve_mutation_attempt.'
            )
        from_state = self.state
        if from_state not in MANUAL_RETRY_STATES:
            raise UserError(
                "A manual retry is not allowed from state %r." % from_state
            )
        if from_state == 'blocked_manual_review':
            # A blocked review is a privileged recovery decision.  Connector
            # Users may retry ordinary transient/permanent failures, but may
            # not resolve or bypass a reviewer-owned state.
            permitted = self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
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
        if self._has_mutation_attempt_evidence():
            raise UserError(
                'Mutation-evidence-linked jobs cannot use generic cancel.'
            )
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

        reason = redact(reason.strip())
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
