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
    attention_business_object = fields.Char(
        compute='_compute_operator_presentation', readonly=True,
    )
    attention_event = fields.Char(
        compute='_compute_operator_presentation', readonly=True,
    )
    attention_shopify_state = fields.Char(
        compute='_compute_operator_presentation', readonly=True,
    )
    attention_odoo_state = fields.Char(
        compute='_compute_operator_presentation', readonly=True,
    )
    attention_effect = fields.Char(
        compute='_compute_operator_presentation', readonly=True,
    )
    attention_consequence = fields.Char(
        compute='_compute_operator_presentation', readonly=True,
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
        'mutation_attempt_id', 'res_model', 'res_id',
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
        order_bindings_by_job = {}
        if 'shopify.connector.order.binding' in self.env:
            order_jobs = self.filtered(
                lambda row: row.job_type == 'order_import_sync'
                and row.shopify_target_gid
            )
            if order_jobs:
                bindings = self.env[
                    'shopify.connector.order.binding'
                ].search([
                    ('store_id', 'in', order_jobs.store_id.ids),
                    ('shopify_gid', 'in', order_jobs.mapped(
                        'shopify_target_gid'
                    )),
                ])
                by_identity = {
                    (binding.store_id.id, binding.shopify_gid): binding
                    for binding in bindings
                }
                order_bindings_by_job = {
                    job.id: by_identity.get((
                        job.store_id.id, job.shopify_target_gid,
                    ))
                    for job in order_jobs
                }
        targets = {}
        grouped_targets = {}
        for job in self:
            if job.res_model and job.res_id and job.res_model in self.env:
                grouped_targets.setdefault(job.res_model, set()).add(job.res_id)
        for model_name, ids in grouped_targets.items():
            try:
                records = self.env[model_name].browse(list(ids)).exists()
                records.check_access('read')
            except AccessError:
                continue
            targets.update({
                (model_name, record.id): record for record in records
            })
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
            target = (
                order_bindings_by_job.get(job.id)
                or targets.get((job.res_model, job.res_id))
            )
            job.attention_business_object = (
                target.display_name if target else
                ('%s #%s' % (job.res_model, job.res_id)
                 if job.res_model and job.res_id else 'Connector operation')
            )
            target_reason = (
                target.review_reason
                if target and 'review_reason' in target._fields else False
            )
            target_action = (
                target.review_required_action
                if target and 'review_required_action' in target._fields
                else False
            )
            job.attention_event = target_reason or reason
            financial = (
                target.shopify_financial_status_snapshot
                if target and 'shopify_financial_status_snapshot' in target._fields
                else False
            )
            fulfillment = (
                target.shopify_fulfillment_status_snapshot
                if target and 'shopify_fulfillment_status_snapshot' in target._fields
                else False
            )
            cancelled = (
                target.shopify_cancelled_at
                if target and 'shopify_cancelled_at' in target._fields else False
            )
            shopify_parts = []
            if financial:
                shopify_parts.append('financial=%s' % financial)
            if fulfillment:
                shopify_parts.append('fulfillment=%s' % fulfillment)
            if cancelled:
                shopify_parts.append('cancelled=yes')
            job.attention_shopify_state = (
                ', '.join(shopify_parts)
                or ('Write outcome is shown in preserved evidence.'
                    if has_evidence else 'No Shopify write was attempted.')
            )
            business = (
                target.sale_order_id
                if target and 'sale_order_id' in target._fields else target
            )
            business_state = (
                business.state
                if business and 'state' in business._fields else False
            )
            job.attention_odoo_state = business_state or job.state
            job.attention_effect = (
                'Shopify may have changed; Odoo finalization is not proven.'
                if has_evidence and job.state != 'succeeded' else
                ('Shopify evidence and Odoo finalization are complete.'
                 if has_evidence else
                 'Shopify was read only; Odoo recorded this review case.')
            )
            job.attention_next_action = target_action or next_action
            job.attention_consequence = (
                'Shipment or mutation processing remains stopped until this '
                'case is resolved through its linked business record.'
                if job.state == 'blocked_manual_review' else
                'Correcting the cause permits a new read-safe run; no unsafe '
                'Shopify write is replayed automatically.'
            )

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
