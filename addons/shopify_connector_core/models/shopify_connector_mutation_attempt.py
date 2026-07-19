import hashlib
import json
import re
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..tools.redaction import redact


ATTEMPT_WRITE_CONTEXT = 'shopify_layer2_attempt_write_surface'
C2_SENTINEL_CONTEXT = 'shopify_layer2_c2_internal_sentinel'
C2_SIDE_CURSOR_SENTINEL = object()
IDEMPOTENCY_VALIDITY_HOURS = 23
INCONCLUSIVE_RECONCILIATION_CAP = 3
EVIDENCE_MASKED = {'masked': True}
RECOVERY_EVIDENCE_CAP = 4
RECONCILIATION_EVIDENCE_CAP = 4
MANUAL_RESOLUTION_EVIDENCE_CAP = 1
RECOVERY_WINDOWS = frozenset((
    'c2_discovered_during_pre_c2_recovery',
    'post_c2_owner_recovery',
    'stale_owner_post_c2',
))
RECOVERY_SOURCES = frozenset((
    'dispatcher_recovery',
    'stale_owner_sweep',
))
EMAIL_PATTERN = re.compile(
    r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
)
PHONE_PATTERN = re.compile(r'(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)')

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
CREATE_SURFACE = '_create_attempt_intent'
WRITE_SURFACES = frozenset((
    '_record_direct_outcome',
    '_record_recovery_uncertain',
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


def _redact_manual_reason(value):
    safe = redact(value)
    safe = EMAIL_PATTERN.sub('***', safe)
    safe = PHONE_PATTERN.sub('***', safe)
    return safe[:512]


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
    _one_attempt_per_job = models.UniqueIndex(
        '(job_id)',
        'A mutation job may own only one attempt for its entire lifetime.',
    )
    _non_negative_reconciliation_count = models.Constraint(
        'CHECK(inconclusive_reconciliation_count >= 0)',
        'The inconclusive reconciliation count cannot be negative.',
    )

    @api.model
    def _surface(self, name):
        if name != CREATE_SURFACE and name not in WRITE_SURFACES:
            raise AccessError('Unknown mutation-attempt write surface.')
        return self.sudo().with_context(**{ATTEMPT_WRITE_CONTEXT: name})

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get(ATTEMPT_WRITE_CONTEXT) != CREATE_SURFACE
            or self.env.context.get(C2_SENTINEL_CONTEXT)
            is not C2_SIDE_CURSOR_SENTINEL
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
        immutable = {
            'job_id', 'attempt_token', 'mutation_domain', 'store_id',
            'expected_connection_generation', 'expected_store_identity',
            'business_intent_fingerprint', 'exact_request_fingerprint',
            'shopify_idempotency_key', 'idempotency_valid_until',
            'transport_attempted', 'created_at', 'transport_at',
        }
        if set(vals) & immutable:
            raise ValidationError('Mutation-attempt identity is immutable.')
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
        return super().write(vals)

    def unlink(self):
        raise AccessError('Mutation-attempt evidence can never be deleted.')

    @api.constrains(
        'observed_outcome', 'resolution_disposition', 'resolution_source',
        'resolution_reason', 'resolution_uid', 'resolution_at', 'resolved_at',
    )
    def _check_resolution_consistency(self):
        for attempt in self:
            resolution_values = (
                attempt.resolution_disposition,
                attempt.resolution_source,
                attempt.resolution_reason,
                attempt.resolution_uid,
                attempt.resolution_at,
            )
            has_any_resolution = any(resolution_values)
            has_complete_resolution = all(resolution_values)
            if has_any_resolution != has_complete_resolution:
                raise ValidationError(
                    'Mutation resolution fields must be complete or empty.'
                )
            if has_complete_resolution and attempt.observed_outcome != 'uncertain':
                raise ValidationError(
                    'Only an uncertain mutation attempt may carry a resolution.'
                )
            should_be_resolved = attempt.observed_outcome in (
                'succeeded', 'failed_clean',
            ) or (
                attempt.observed_outcome == 'uncertain'
                and has_complete_resolution
            )
            if bool(attempt.resolved_at) != bool(should_be_resolved):
                raise ValidationError(
                    'resolved_at must reflect the effective disposition.'
                )

    @api.model
    def _create_attempt_intent(self, values):
        """C2-only durable intent creation on the internal side cursor."""
        if (
            self.env.context.get(C2_SENTINEL_CONTEXT)
            is not C2_SIDE_CURSOR_SENTINEL
        ):
            raise ValidationError(
                'Mutation intent creation requires the internal C2 sentinel.'
            )
        values = dict(values)
        job_id = values.get('job_id')
        domain = values.get('mutation_domain')
        token = values.get('attempt_token')
        strategies = self.env[
            'shopify.connector.job.dispatch'
        ]._get_reconciliation_strategies()
        if domain not in strategies:
            raise ValidationError(
                'No reconciliation strategy is registered for this mutation.'
            )
        job = self.env['shopify.connector.job'].browse(
            job_id
        ).try_lock_for_update()
        if not job:
            raise ValidationError('The mutation job is unavailable at C2.')
        job.invalidate_recordset()
        if (
            job.state != 'running'
            or job.current_attempt_token != token
            or job.job_type != domain
        ):
            raise ValidationError(
                'C2 job state, owner token, and mutation domain must match.'
            )
        if self.search_count([('job_id', '=', job.id)]):
            raise ValidationError(
                'A mutation attempt already exists for this job.'
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
            'resolved_at': False,
        })
        return self._surface(CREATE_SURFACE).create(values)

    def _record_direct_outcome(self, outcome, evidence=None):
        """C3-only immutable machine outcome with separate evidence."""
        self.ensure_one()
        if outcome not in ('succeeded', 'failed_clean', 'uncertain'):
            raise ValidationError('Unknown direct mutation outcome.')
        locked = self.try_lock_for_update()
        if not locked:
            raise UserError('The mutation attempt is owned by another worker.')
        locked.invalidate_recordset()
        locked._surface('_record_direct_outcome').write({
            'observed_outcome': outcome,
            'remote_evidence_refs': {
                'direct': dict(evidence or {}),
                'recovery': [],
                'reconciliation': [],
                'manual_resolution': [],
            },
            'resolved_at': (
                fields.Datetime.now()
                if outcome in ('succeeded', 'failed_clean') else False
            ),
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

    def _evidence_sections(self):
        """Return the four bounded evidence sections, including old rows."""
        self.ensure_one()
        current = dict(self.remote_evidence_refs or {})
        known = {
            'direct', 'recovery', 'reconciliation', 'manual_resolution',
        }
        direct = dict(current.get('direct') or {})
        if not direct and current and not (set(current) & known):
            direct = current
        return {
            'direct': direct,
            'recovery': list(current.get('recovery') or [])[
                -RECOVERY_EVIDENCE_CAP:
            ],
            'reconciliation': list(
                current.get('reconciliation') or []
            )[-RECONCILIATION_EVIDENCE_CAP:],
            'manual_resolution': list(
                current.get('manual_resolution') or []
            )[-MANUAL_RESOLUTION_EVIDENCE_CAP:],
        }

    def _evidence_with_recovery(self, recovery_window, recovery_source):
        self.ensure_one()
        if recovery_window not in RECOVERY_WINDOWS:
            raise ValidationError('Unknown Layer 2 recovery window.')
        if recovery_source not in RECOVERY_SOURCES:
            raise ValidationError('Unknown Layer 2 recovery source.')
        sections = self._evidence_sections()
        identity = {
            'window': redact(recovery_window),
            'source': redact(recovery_source),
            'job_id': self.job_id.id,
            'attempt_id': self.id,
        }
        if any(
            all(entry.get(key) == value for key, value in identity.items())
            for entry in sections['recovery']
            if isinstance(entry, dict)
        ):
            return sections
        entry = dict(identity)
        entry['at'] = fields.Datetime.to_string(fields.Datetime.now())
        sections['recovery'] = (
            sections['recovery'] + [entry]
        )[-RECOVERY_EVIDENCE_CAP:]
        return sections

    def _record_recovery_uncertain(
        self, recovery_window, recovery_source,
    ):
        """Closed recovery-only pending -> uncertain transition."""
        self.ensure_one()
        locked = self.try_lock_for_update()
        if not locked:
            raise UserError('The mutation attempt is owned by another worker.')
        locked.invalidate_recordset()
        if locked.observed_outcome in ('succeeded', 'failed_clean'):
            raise ValidationError(
                'A resolved direct mutation attempt cannot be recovered.'
            )
        if (
            locked.observed_outcome != 'pending'
            and not (
                locked.observed_outcome == 'uncertain'
                and not locked.resolution_disposition
            )
        ):
            raise ValidationError(
                'Only pending or unresolved uncertain attempts may recover.'
            )
        evidence = locked._evidence_with_recovery(
            recovery_window, recovery_source,
        )
        values = {'remote_evidence_refs': evidence}
        if locked.observed_outcome == 'pending':
            values.update({
                'observed_outcome': 'uncertain',
                'resolved_at': False,
            })
        if evidence != locked.remote_evidence_refs or len(values) > 1:
            locked._surface('_record_recovery_uncertain').write(values)
        return locked

    def _evidence_with_reconciliation(self, verdict, evidence):
        self.ensure_one()
        sections = self._evidence_sections()
        entries = sections['reconciliation']
        entries.append({
            'verdict': verdict,
            'at': fields.Datetime.to_string(fields.Datetime.now()),
            'evidence': dict(evidence or {}),
        })
        sections['reconciliation'] = entries[
            -RECONCILIATION_EVIDENCE_CAP:
        ]
        return sections

    def _evidence_with_manual_resolution(
        self, disposition, safe_reason,
    ):
        self.ensure_one()
        sections = self._evidence_sections()
        sections['manual_resolution'] = [{
            'actor_uid': self.env.uid,
            'disposition': disposition,
            'at': fields.Datetime.to_string(fields.Datetime.now()),
            'reason': safe_reason,
        }][-MANUAL_RESOLUTION_EVIDENCE_CAP:]
        return sections

    def _record_reconciliation_result(
        self, disposition, evidence=None,
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
            'remote_evidence_refs': locked._evidence_with_reconciliation(
                disposition, evidence,
            ),
        })
        return locked

    def _record_inconclusive_reconciliation(self, evidence=None):
        self.ensure_one()
        locked = self.try_lock_for_update()
        if not locked:
            raise UserError('The mutation attempt is owned by another worker.')
        locked.invalidate_recordset()
        if (
            locked.observed_outcome != 'uncertain'
            or locked.resolution_disposition
        ):
            raise ValidationError(
                'Only an unresolved uncertain attempt may remain inconclusive.'
            )
        count = locked.inconclusive_reconciliation_count + 1
        locked._surface('_record_inconclusive_reconciliation').write({
            'inconclusive_reconciliation_count': count,
            'remote_evidence_refs': locked._evidence_with_reconciliation(
                'inconclusive', evidence,
            ),
        })
        return count

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
        safe_reason = _redact_manual_reason(reason.strip())
        attempt._surface('action_resolve_mutation_attempt').write({
            'resolution_disposition': disposition,
            'resolution_source': 'manual_admin',
            'resolution_reason': safe_reason,
            'resolution_uid': self.env.uid,
            'resolution_at': now,
            'resolved_at': now,
            'remote_evidence_refs':
                attempt._evidence_with_manual_resolution(
                    disposition, safe_reason,
                ),
        })
        strategy = self.env[
            'shopify.connector.job.dispatch'
        ]._validated_mutation_strategy(attempt.mutation_domain)
        consequence = {
            'observed_outcome': 'uncertain',
            'error_class': (
                False if disposition == 'applied' else 'duplicate_risk'
            ),
            'manual_review_subreason': (
                False if disposition == 'applied' else 'duplicate_risk'
            ),
            'action': (
                'succeed' if disposition == 'applied'
                else 'block_manual_review'
            ),
            'message': 'Mutation attempt manually resolved by actor_uid=%d.'
            % self.env.uid,
            'evidence': {},
            'domain_payload': {'disposition': disposition},
        }
        self.env['shopify.connector.job.dispatch']._apply_validated_consequence(
            attempt.job_id,
            attempt,
            'manual_resolution',
            consequence,
            strategy,
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
            if (
                not attempt.resolved_at
                or attempt.effective_disposition() not in (
                    'applied', 'not_applied',
                )
            ):
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
