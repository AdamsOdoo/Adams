import hashlib
import json
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY


ATTEMPT_WRITE_CONTEXT = 'shopify_layer2_attempt_write_surface'
IDEMPOTENCY_VALIDITY_HOURS = 23
INCONCLUSIVE_RECONCILIATION_CAP = 3
EVIDENCE_MASKED = {'masked': True}

OBSERVED_OUTCOME_SELECTION = [
    ('pending', 'Pending'),
    ('succeeded', 'Succeeded'),
    ('failed_clean', 'Failed Clean'),
    ('uncertain', 'Uncertain'),
]
RESOLUTION_DISPOSITION_SELECTION = [
    ('applied', 'Applied'),
    ('not_applied', 'Not Applied'),
]
RESOLUTION_SOURCE_SELECTION = [
    ('reconciliation_read', 'Reconciliation Read'),
    ('manual_admin', 'Manual Administrator'),
]
WRITE_SURFACES = frozenset((
    '_create_attempt_intent',
    '_record_direct_outcome',
    '_record_reconciliation_result',
    '_record_inconclusive_reconciliation',
    'action_resolve_mutation_attempt',
    '_mask_terminal_evidence',
))


def canonical_sha256(value):
    """Return a stable SHA-256 over JSON-safe normalized data."""
    payload = json.dumps(
        value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


class ShopifyConnectorMutationAttempt(models.Model):
    _name = 'shopify.connector.mutation.attempt'
    _description = 'Shopify Connector Mutation Attempt'
    _order = 'created_at desc, id desc'

    job_id = fields.Many2one(
        'shopify.connector.job',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    attempt_token = fields.Char(required=True, readonly=True)
    mutation_domain = fields.Char(required=True, index=True, readonly=True)
    store_id = fields.Many2one(
        related='job_id.store_id',
        store=True,
        index=True,
        readonly=True,
    )
    expected_connection_generation = fields.Integer(readonly=True)
    expected_store_identity = fields.Char(readonly=True)
    remote_mutation_intent = fields.Json(readonly=True)
    preconditions_snapshot = fields.Json(readonly=True)
    business_intent_fingerprint = fields.Char(readonly=True)
    exact_request_fingerprint = fields.Char(readonly=True)
    shopify_idempotency_key = fields.Char(readonly=True)
    idempotency_valid_until = fields.Datetime(readonly=True)
    transport_attempted = fields.Boolean(default=False, readonly=True)
    observed_outcome = fields.Selection(
        OBSERVED_OUTCOME_SELECTION,
        required=True,
        default='pending',
        readonly=True,
    )
    resolution_disposition = fields.Selection(
        RESOLUTION_DISPOSITION_SELECTION,
        readonly=True,
    )
    resolution_source = fields.Selection(
        RESOLUTION_SOURCE_SELECTION,
        readonly=True,
    )
    resolution_reason = fields.Text(readonly=True)
    resolution_uid = fields.Many2one('res.users', readonly=True)
    resolution_at = fields.Datetime(readonly=True)
    inconclusive_reconciliation_count = fields.Integer(
        default=0,
        readonly=True,
    )
    remote_evidence_refs = fields.Json(readonly=True)
    created_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    transport_at = fields.Datetime(readonly=True)
    resolved_at = fields.Datetime(readonly=True)

    _attempt_token_unique = models.UniqueIndex(
        '(job_id, attempt_token)',
        'The attempt token must be unique for this job.',
    )
    _non_negative_reconciliation_count = models.Constraint(
        'CHECK(inconclusive_reconciliation_count >= 0)',
        'The inconclusive reconciliation count cannot be negative.',
    )

    @api.model
    def _surface(self, name):
        if name not in WRITE_SURFACES:
            raise AccessError('Unknown mutation-attempt write surface.')
        return self.sudo().with_context(**{ATTEMPT_WRITE_CONTEXT: name})

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get(ATTEMPT_WRITE_CONTEXT)
            != '_create_attempt_intent'
        ):
            raise AccessError(
                'Mutation attempts can only be created by the Layer 2 service.'
            )
        return super().create(vals_list)

    def write(self, vals):
        surface = self.env.context.get(ATTEMPT_WRITE_CONTEXT)
        if not self.env.su or surface not in WRITE_SURFACES:
            raise AccessError(
                'Mutation attempts can only be changed by a sanctioned '
                'Layer 2 service.'
            )
        if 'observed_outcome' in vals:
            for attempt in self:
                if attempt.observed_outcome != 'pending':
                    raise ValidationError(
                        'A machine-observed mutation outcome is immutable.'
                    )
                if vals['observed_outcome'] == 'pending':
                    raise ValidationError(
                        'A direct outcome must leave the pending state.'
                    )
        immutable = {
            'job_id', 'attempt_token', 'mutation_domain', 'store_id',
            'expected_connection_generation', 'expected_store_identity',
            'business_intent_fingerprint', 'exact_request_fingerprint',
            'shopify_idempotency_key', 'idempotency_valid_until',
            'transport_attempted', 'created_at', 'transport_at',
        }
        if surface != '_create_attempt_intent' and set(vals) & immutable:
            raise ValidationError('Mutation-attempt identity is immutable.')
        return super().write(vals)

    def unlink(self):
        raise AccessError('Mutation-attempt evidence can never be deleted.')

    @api.model
    def _create_attempt_intent(self, values):
        """C2-only durable intent creation on an owned side cursor."""
        if not self.env.context.get('shopify_layer2_c2_side_cursor'):
            raise ValidationError(
                'Mutation intent creation requires the dedicated C2 side cursor.'
            )
        values = dict(values)
        domain = values.get('mutation_domain')
        strategies = self.env[
            'shopify.connector.job.dispatch'
        ]._get_reconciliation_strategies()
        if domain not in strategies:
            raise ValidationError(
                'No reconciliation strategy is registered for this mutation.'
            )
        now = fields.Datetime.now()
        values.update({
            'transport_attempted': True,
            'observed_outcome': 'pending',
            'created_at': values.get('created_at') or now,
            'transport_at': values.get('transport_at') or now,
            'idempotency_valid_until': (
                values.get('idempotency_valid_until')
                or now + timedelta(hours=IDEMPOTENCY_VALIDITY_HOURS)
            ),
        })
        return self._surface('_create_attempt_intent').create(values)

    def _record_direct_outcome(self, outcome, evidence=None):
        """C3-only immutable machine outcome."""
        self.ensure_one()
        if outcome not in ('succeeded', 'failed_clean', 'uncertain'):
            raise ValidationError('Unknown direct mutation outcome.')
        locked = self.try_lock_for_update()
        if not locked:
            raise UserError('The mutation attempt is owned by another worker.')
        locked.invalidate_recordset()
        locked._surface('_record_direct_outcome').write({
            'observed_outcome': outcome,
            'remote_evidence_refs': evidence or {},
            'resolved_at': fields.Datetime.now(),
        })
        return locked

    def effective_disposition(self):
        self.ensure_one()
        if self.observed_outcome == 'succeeded':
            return 'applied'
        if self.observed_outcome == 'failed_clean':
            return 'not_applied'
        if (
            self.observed_outcome == 'uncertain'
            and self.resolution_disposition
        ):
            return self.resolution_disposition
        return 'unresolved'

    def _apply_disposition_to_job(self, source_message):
        self.ensure_one()
        disposition = self.effective_disposition()
        job = self.job_id
        now = fields.Datetime.now()
        if disposition == 'applied':
            from_state = job.state
            job.sudo().write({
                'state': 'succeeded',
                'finished_at': now,
                'reconciliation_pending_until': False,
            })
            job._log_transition(
                'state_change',
                source_message,
                from_state=from_state,
                to_state='succeeded',
            )
        elif disposition == 'not_applied':
            from_state = job.state
            job.sudo().write({
                'state': 'retry_waiting',
                'next_retry_at': now,
                'finished_at': False,
                'reconciliation_pending_until': False,
            })
            job._log_transition(
                'state_change',
                source_message,
                from_state=from_state,
                to_state='retry_waiting',
            )
        return disposition

    def _record_reconciliation_result(
        self, disposition, reconciliation_job, evidence=None,
    ):
        self.ensure_one()
        if disposition not in ('applied', 'not_applied'):
            raise ValidationError('Unknown reconciliation disposition.')
        locked = self.try_lock_for_update()
        if not locked:
            raise UserError('The mutation attempt is owned by another worker.')
        locked.invalidate_recordset()
        if locked.observed_outcome != 'uncertain':
            raise ValidationError(
                'Only an uncertain attempt may be reconciled.'
            )
        if locked.resolution_disposition:
            raise ValidationError('This mutation attempt is already resolved.')
        now = fields.Datetime.now()
        locked._surface('_record_reconciliation_result').write({
            'resolution_disposition': disposition,
            'resolution_source': 'reconciliation_read',
            'resolution_reason': 'Read-only reconciliation verdict.',
            'resolution_uid': self.env.uid,
            'resolution_at': now,
            'resolved_at': now,
            'remote_evidence_refs': evidence or {},
        })
        locked._apply_disposition_to_job(
            'Mutation attempt resolved by read-only reconciliation: %s.'
            % disposition
        )
        if reconciliation_job:
            from_state = reconciliation_job.state
            reconciliation_job.sudo().write({
                'state': 'succeeded',
                'finished_at': now,
                'reconciliation_pending_until': False,
            })
            reconciliation_job._log_transition(
                'state_change',
                'Reconciliation verdict recorded for mutation attempt %d.'
                % locked.id,
                from_state=from_state,
                to_state='succeeded',
            )
        return True

    def _record_inconclusive_reconciliation(self, reconciliation_job):
        self.ensure_one()
        for attempt_index in range(3):
            try:
                locked = self.try_lock_for_update()
                if not locked:
                    raise UserError(
                        'The mutation attempt is owned by another worker.'
                    )
                locked.invalidate_recordset()
                if locked.observed_outcome != 'uncertain':
                    raise ValidationError(
                        'Only an uncertain attempt may remain inconclusive.'
                    )
                count = locked.inconclusive_reconciliation_count + 1
                locked._surface(
                    '_record_inconclusive_reconciliation'
                ).write({
                    'inconclusive_reconciliation_count': count,
                })
                now = fields.Datetime.now()
                if count >= INCONCLUSIVE_RECONCILIATION_CAP:
                    original = locked.job_id
                    from_state = original.state
                    original.sudo().write({
                        'state': 'blocked_manual_review',
                        'error_class': 'duplicate_risk',
                        'manual_review_subreason': 'duplicate_risk',
                        'finished_at': now,
                        'reconciliation_pending_until': False,
                    })
                    original._log_transition(
                        'state_change',
                        'Mutation reconciliation remained inconclusive at '
                        'the safety cap; manual review is required.',
                        from_state=from_state,
                        to_state='blocked_manual_review',
                    )
                    if reconciliation_job:
                        reconciliation_job.sudo().write({
                            'state': 'succeeded',
                            'finished_at': now,
                        })
                elif reconciliation_job:
                    reconciliation_job.sudo().write({
                        'state': 'retry_waiting',
                        'next_retry_at': now + timedelta(minutes=5),
                    })
                return count
            except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
                self.env.cr.rollback()
                self.env.transaction.reset()
                if attempt_index == 2:
                    raise
        return False

    def action_resolve_mutation_attempt(self, disposition, reason):
        self.ensure_one()
        attempt = self.try_lock_for_update()
        if not attempt:
            raise UserError(
                'The mutation attempt is being reconciled by another worker.'
            )
        attempt.invalidate_recordset()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may resolve a '
                'mutation attempt.'
            )
        if disposition not in ('applied', 'not_applied'):
            raise UserError('Choose applied or not applied.')
        if not isinstance(reason, str) or not reason.strip():
            raise UserError('A non-empty resolution reason is required.')
        if attempt.observed_outcome != 'uncertain':
            raise UserError('Only an uncertain attempt needs manual resolution.')
        if attempt.resolution_disposition:
            raise UserError('This mutation attempt is already resolved.')
        now = fields.Datetime.now()
        attempt._surface('action_resolve_mutation_attempt').write({
            'resolution_disposition': disposition,
            'resolution_source': 'manual_admin',
            'resolution_reason': reason.strip(),
            'resolution_uid': self.env.uid,
            'resolution_at': now,
            'resolved_at': now,
        })
        attempt._apply_disposition_to_job(
            'Mutation attempt manually resolved by actor_uid=%d; '
            'disposition=%s; reason=%s.'
            % (self.env.uid, disposition, reason.strip())
        )
        reconciliation_jobs = self.env['shopify.connector.job'].search([
            ('mutation_attempt_id', '=', attempt.id),
            ('state', 'in', ('queued', 'running', 'retry_waiting')),
        ]).try_lock_for_update()
        for job in reconciliation_jobs:
            from_state = job.state
            job.sudo().write({
                'state': 'cancelled',
                'cancel_reason': 'Attempt resolved manually by Administrator.',
                'finished_at': now,
            })
            job._log_transition(
                'manual_action',
                'Reconciliation job closed after Administrator resolution.',
                from_state=from_state,
                to_state='cancelled',
            )
        return True

    def _mask_terminal_evidence(self):
        for attempt in self:
            if attempt.effective_disposition() == 'unresolved':
                continue
            if (
                attempt.remote_mutation_intent == EVIDENCE_MASKED
                and attempt.preconditions_snapshot == EVIDENCE_MASKED
                and attempt.remote_evidence_refs == EVIDENCE_MASKED
            ):
                continue
            attempt._surface('_mask_terminal_evidence').write({
                'remote_mutation_intent': EVIDENCE_MASKED,
                'preconditions_snapshot': EVIDENCE_MASKED,
                'remote_evidence_refs': EVIDENCE_MASKED,
            })
        return True
