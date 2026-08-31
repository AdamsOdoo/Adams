"""Durable execution-attempt evidence, separate from mutation intent evidence."""

import uuid

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .shopify_connector_job import ERROR_CLASS_SELECTION
from .shopify_connector_job_attempt_metadata import (
    _MAX_TEXT_CHARS,
    _UUID_RE,
    _bounded_json,
    _non_negative_number,
    _safe_digest,
    _safe_json,
    _safe_text,
    _uuid_token,
)

ATTEMPT_OUTCOME_SELECTION = [
    ('claimed', 'Claimed'),
    ('running', 'Running'),
    ('succeeded', 'Succeeded'),
    ('retry_scheduled', 'Retry Scheduled'),
    ('verification_required', 'Verification Required'),
    ('manual_review', 'Manual Review'),
    ('failed_terminal', 'Failed (Terminal)'),
    ('cancelled', 'Cancelled'),
    ('owner_lost', 'Owner Lost'),
]
ATTEMPT_OUTCOME_KEYS = frozenset(item[0] for item in ATTEMPT_OUTCOME_SELECTION)
ATTEMPT_ACTIVE_OUTCOMES = frozenset(('claimed', 'running'))
ATTEMPT_TERMINAL_OUTCOMES = frozenset(ATTEMPT_OUTCOME_KEYS - ATTEMPT_ACTIVE_OUTCOMES)

ATTEMPT_RETRY_DECISION_SELECTION = [
    ('retry', 'Retry'),
    ('verify', 'Verify'),
    ('review', 'Manual Review'),
    ('terminal', 'Terminal'),
    ('none', 'None'),
]
ATTEMPT_RETRY_DECISION_KEYS = frozenset(item[0] for item in ATTEMPT_RETRY_DECISION_SELECTION)

ATTEMPT_LEGAL_TRANSITIONS = {
    'claimed': frozenset((
        'running', 'cancelled', 'owner_lost',
    )),
    'running': frozenset((
        'succeeded', 'retry_scheduled', 'verification_required',
        'manual_review', 'failed_terminal', 'cancelled', 'owner_lost',
    )),
    'succeeded': frozenset(),
    'retry_scheduled': frozenset(),
    'verification_required': frozenset(),
    'manual_review': frozenset(),
    'failed_terminal': frozenset(),
    'cancelled': frozenset(),
    'owner_lost': frozenset(),
}

ATTEMPT_WRITE_CONTEXT = 'shopify_connector_job_attempt_write_surface'
ATTEMPT_SERVICE_SENTINEL_CONTEXT = (
    'shopify_connector_job_attempt_service_sentinel'
)
ATTEMPT_SERVICE_SENTINEL = object()
ATTEMPT_CREATE_SURFACE = '_create_attempt'
ATTEMPT_WRITE_SURFACES = frozenset((
    ATTEMPT_CREATE_SURFACE,
    '_start_attempt',
    '_heartbeat_attempt',
    '_observe_attempt',
    '_finish_attempt',
    '_mask_terminal_attempt',
))

ATTEMPT_SURFACE_FIELDS = {
    ATTEMPT_CREATE_SURFACE: frozenset(),
    '_start_attempt': frozenset(('outcome', 'started_at', 'heartbeat_at')),
    '_heartbeat_attempt': frozenset(('heartbeat_at',)),
    '_observe_attempt': frozenset((
        'shopify_request_id', 'requested_cost', 'actual_cost',
        'budget_available', 'throttle_delay_ms', 'request_digest',
        'response_digest', 'observations',
    )),
    '_finish_attempt': frozenset((
        'outcome', 'finished_at', 'error_class', 'error_code',
        'safe_message', 'retry_decision', 'next_retry_at',
        'shopify_request_id', 'requested_cost', 'actual_cost',
        'budget_available', 'throttle_delay_ms', 'request_digest',
        'response_digest', 'mutation_attempt_id', 'observations',
    )),
    '_mask_terminal_attempt': frozenset((
        'safe_message', 'observations', 'shopify_request_id',
    )),
}

ATTEMPT_CREATE_FORBIDDEN_FIELDS = frozenset((
    'outcome', 'started_at', 'heartbeat_at', 'finished_at',
    'error_class', 'error_code', 'safe_message', 'retry_decision',
    'next_retry_at', 'actual_cost', 'throttle_delay_ms',
    'shopify_request_id', 'request_digest', 'response_digest',
    'mutation_attempt_id',
))

class ShopifyConnectorJobAttempt(models.Model):
    _name = 'shopify.connector.job.attempt'
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Job Execution Attempt'
    _order = 'claimed_at desc, id desc'

    job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    run_id = fields.Many2one(
        comodel_name='shopify.connector.run',
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        related='job_id.store_id',
        store=True,
        index=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    attempt_no = fields.Integer(required=True, default=1, readonly=True)
    claim_token = fields.Char(required=True, index=True, readonly=True)
    worker_ref = fields.Char(required=True, index=True, readonly=True)
    claimed_at = fields.Datetime(required=True, readonly=True)
    started_at = fields.Datetime(readonly=True)
    heartbeat_at = fields.Datetime(index=True, readonly=True)
    finished_at = fields.Datetime(index=True, readonly=True)
    outcome = fields.Selection(
        selection=ATTEMPT_OUTCOME_SELECTION,
        required=True,
        index=True,
        default='claimed',
        readonly=True,
    )
    error_class = fields.Selection(
        selection=ERROR_CLASS_SELECTION,
        index=True,
        readonly=True,
    )
    error_code = fields.Char(index=True, readonly=True)
    safe_message = fields.Text(readonly=True)
    retry_decision = fields.Selection(
        selection=ATTEMPT_RETRY_DECISION_SELECTION,
        readonly=True,
    )
    next_retry_at = fields.Datetime(index=True, readonly=True)
    shopify_request_id = fields.Char(index=True, readonly=True)
    requested_cost = fields.Float(readonly=True)
    actual_cost = fields.Float(readonly=True)
    budget_available = fields.Float(readonly=True)
    throttle_delay_ms = fields.Integer(readonly=True)
    request_digest = fields.Char(readonly=True)
    response_digest = fields.Char(readonly=True)
    mutation_attempt_id = fields.Many2one(
        comodel_name='shopify.connector.mutation.attempt',
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    observations = fields.Json(default=dict, readonly=True)

    _job_attempt_no_uniq = models.Constraint(
        'UNIQUE(job_id, attempt_no)',
        'An attempt number may occur only once for a job.',
    )
    _job_claim_token_uniq = models.Constraint(
        'UNIQUE(job_id, claim_token)',
        'A claim token may occur only once for a job.',
    )
    _attempt_no_positive = models.Constraint(
        'CHECK(attempt_no > 0)',
        'Attempt numbers must be positive.',
    )
    _costs_non_negative = models.Constraint(
        'CHECK((requested_cost IS NULL OR requested_cost >= 0) AND '
        '(actual_cost IS NULL OR actual_cost >= 0) AND '
        '(budget_available IS NULL OR budget_available >= 0) AND '
        '(throttle_delay_ms IS NULL OR throttle_delay_ms >= 0))',
        'Cost and throttle observations cannot be negative.',
    )
    _terminal_finished = models.Constraint(
        "CHECK((outcome IN ('claimed', 'running') AND finished_at IS NULL) OR "
        "(outcome NOT IN ('claimed', 'running') AND finished_at IS NOT NULL))",
        'A completed attempt outcome requires finished_at.',
    )

    @api.model
    def _surface(self, name):
        if name not in ATTEMPT_WRITE_SURFACES:
            raise AccessError('Unknown job-attempt write surface.')
        return self.sudo().with_context(**{
            ATTEMPT_WRITE_CONTEXT: name,
            ATTEMPT_SERVICE_SENTINEL_CONTEXT: ATTEMPT_SERVICE_SENTINEL,
        })

    @api.model
    def _surface_is_open(self):
        context = self.env.context
        return (
            self.env.su
            and context.get(ATTEMPT_SERVICE_SENTINEL_CONTEXT)
            is ATTEMPT_SERVICE_SENTINEL
            and context.get(ATTEMPT_WRITE_CONTEXT)
            in ATTEMPT_WRITE_SURFACES
        )

    @api.model
    def _prepare_service_values(self, values):
        values = dict(values or {})
        supplied_outcome = values.get('outcome')
        if supplied_outcome not in (None, False, 'claimed'):
            raise ValidationError(
                'A new execution attempt must start in the claimed state.'
            )
        inconsistent = {
            field_name for field_name in ATTEMPT_CREATE_FORBIDDEN_FIELDS
            if field_name != 'outcome'
            if values.get(field_name) not in (None, False, {}, [])
        }
        if inconsistent:
            raise ValidationError(
                'A new claimed attempt cannot include lifecycle or terminal '
                'fields: %s.' % ', '.join(sorted(inconsistent))
            )
        if not values.get('job_id'):
            raise ValidationError('An execution attempt must belong to a job.')
        job = self.env['shopify.connector.job'].sudo().browse(
            values['job_id']
        ).exists()
        if not job:
            raise ValidationError('The execution-attempt job does not exist.')
        job.ensure_one()

        run_id = values.get('run_id')
        if not run_id and 'run_id' in job._fields and job.run_id:
            run_id = job.run_id.id
            values['run_id'] = run_id
        if run_id:
            run = self.env['shopify.connector.run'].sudo().browse(
                run_id
            ).exists()
            if not run:
                raise ValidationError('The execution-attempt run does not exist.')
            run.ensure_one()
            if run.store_id != job.store_id:
                raise ValidationError(
                    'The execution attempt, job, and run must share a store.'
                )

        mutation_id = values.get('mutation_attempt_id')
        if mutation_id:
            mutation = self.env[
                'shopify.connector.mutation.attempt'
            ].sudo().browse(mutation_id).exists()
            if not mutation:
                raise ValidationError(
                    'The referenced mutation attempt does not exist.'
                )
            mutation.ensure_one()
            if mutation.store_id != job.store_id:
                raise ValidationError(
                    'Execution and mutation evidence must share a store.'
                )

        attempt_no = values.get('attempt_no')
        if attempt_no in (None, False):
            previous = self.sudo().search([
                ('job_id', '=', job.id),
            ], order='attempt_no desc', limit=1)
            attempt_no = (previous.attempt_no if previous else 0) + 1
        try:
            attempt_no = int(attempt_no)
        except (TypeError, ValueError) as exc:
            raise ValidationError('Attempt number must be an integer.') from exc
        if attempt_no <= 0:
            raise ValidationError('Attempt number must be positive.')

        values['attempt_no'] = attempt_no
        values['claim_token'] = _uuid_token(
            values.get('claim_token') or str(uuid.uuid4()),
            'The claim token',
        )
        values['worker_ref'] = _safe_text(
            values.get('worker_ref') or 'worker:%s' % self.env.uid,
            128,
        )
        if not values['worker_ref'] or not values['worker_ref'].strip():
            raise ValidationError('A worker reference cannot be blank.')
        values['worker_ref'] = values['worker_ref'].strip()
        values['claimed_at'] = values.get('claimed_at') or fields.Datetime.now()
        values['outcome'] = 'claimed'
        values['observations'] = _bounded_json(values.get('observations'))

        for field_name in (
            'requested_cost', 'actual_cost', 'budget_available',
        ):
            values[field_name] = _non_negative_number(
                values.get(field_name), field_name,
            )
        if values.get('throttle_delay_ms') not in (None, False):
            if isinstance(values['throttle_delay_ms'], bool):
                raise ValidationError(
                    'throttle_delay_ms must be an integer, not boolean.'
                )
            try:
                values['throttle_delay_ms'] = int(values['throttle_delay_ms'])
            except (TypeError, ValueError, OverflowError) as exc:
                raise ValidationError(
                    'throttle_delay_ms must be an integer.'
                ) from exc
            if values['throttle_delay_ms'] < 0:
                raise ValidationError('throttle_delay_ms cannot be negative.')
        if values.get('safe_message'):
            values['safe_message'] = _safe_text(
                values['safe_message'], _MAX_TEXT_CHARS,
            )
        if values.get('error_code'):
            values['error_code'] = _safe_text(values['error_code'], 128)
        if values.get('shopify_request_id'):
            values['shopify_request_id'] = _safe_text(
                values['shopify_request_id'], 256,
            )
        values['request_digest'] = _safe_digest(
            values.get('request_digest'), 'request_digest',
        )
        values['response_digest'] = _safe_digest(
            values.get('response_digest'), 'response_digest',
        )
        return values

    @api.model_create_multi
    def create(self, vals_list):
        if not self._surface_is_open() or (
            self.env.context.get(ATTEMPT_WRITE_CONTEXT)
            != ATTEMPT_CREATE_SURFACE
        ):
            raise AccessError(
                'Execution attempts can only be created by the connector '
                'runtime service.'
            )
        prepared = [self._prepare_service_values(values) for values in vals_list]
        return super().create(prepared)

    def write(self, vals):
        if not self._surface_is_open():
            raise AccessError(
                'Execution attempts can only be changed by the connector '
                'runtime service.'
            )
        surface = self.env.context.get(ATTEMPT_WRITE_CONTEXT)
        allowed = ATTEMPT_SURFACE_FIELDS[surface]
        if surface == ATTEMPT_CREATE_SURFACE:
            raise AccessError(
                'The attempt creation surface cannot mutate an existing '
                'attempt.'
            )
        if allowed is not None and set(vals) - allowed:
            raise AccessError(
                'The selected attempt service surface cannot change these '
                'fields.'
            )
        vals = dict(vals)
        if 'safe_message' in vals and vals['safe_message']:
            vals['safe_message'] = _safe_text(
                vals['safe_message'], _MAX_TEXT_CHARS,
            )
        if 'error_code' in vals and vals['error_code']:
            vals['error_code'] = _safe_text(vals['error_code'], 128)
        if 'shopify_request_id' in vals and vals['shopify_request_id']:
            vals['shopify_request_id'] = _safe_text(
                vals['shopify_request_id'], 256,
            )
        for field_name in (
            'requested_cost', 'actual_cost', 'budget_available',
        ):
            if field_name in vals:
                vals[field_name] = _non_negative_number(
                    vals[field_name], field_name,
                )
        if 'throttle_delay_ms' in vals:
            if vals['throttle_delay_ms'] not in (None, False):
                if isinstance(vals['throttle_delay_ms'], bool):
                    raise ValidationError(
                        'throttle_delay_ms must be an integer, not boolean.'
                    )
                try:
                    vals['throttle_delay_ms'] = int(vals['throttle_delay_ms'])
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ValidationError(
                        'throttle_delay_ms must be an integer.'
                    ) from exc
                if vals['throttle_delay_ms'] < 0:
                    raise ValidationError(
                        'throttle_delay_ms cannot be negative.'
                    )
        if 'request_digest' in vals:
            vals['request_digest'] = _safe_digest(
                vals['request_digest'], 'request_digest',
            )
        if 'response_digest' in vals:
            vals['response_digest'] = _safe_digest(
                vals['response_digest'], 'response_digest',
            )
        if 'observations' in vals:
            vals['observations'] = _bounded_json(vals['observations'])

        immutable = {
            'job_id', 'run_id', 'store_id', 'company_id', 'attempt_no',
            'claim_token', 'worker_ref', 'claimed_at',
        }
        if immutable.intersection(vals):
            raise ValidationError('Execution-attempt identity is immutable.')
        for record in self:
            current = record.outcome
            if surface == '_start_attempt' and current != 'claimed':
                raise ValidationError(
                    'An execution attempt may be started only once.'
                )
            if current in ATTEMPT_TERMINAL_OUTCOMES and surface != (
                '_mask_terminal_attempt'
            ):
                raise ValidationError('A terminal execution attempt is immutable.')
            target = vals.get('outcome', current)
            if target not in ATTEMPT_OUTCOME_KEYS:
                raise ValidationError('Unknown execution-attempt outcome.')
            if target != current and target not in (
                ATTEMPT_LEGAL_TRANSITIONS.get(current, frozenset())
            ):
                raise ValidationError(
                    'Illegal execution-attempt transition %s -> %s.' % (
                        current, target,
                    )
                )
            finished = vals.get('finished_at', record.finished_at)
            if target in ATTEMPT_TERMINAL_OUTCOMES and not finished:
                raise ValidationError(
                    'A terminal execution outcome requires finished_at.'
                )
            if target in ATTEMPT_ACTIVE_OUTCOMES and finished:
                raise ValidationError(
                    'An active execution attempt cannot have finished_at.'
                )
            started = vals.get('started_at', record.started_at)
            if target == 'running' and not started:
                raise ValidationError(
                    'A running execution attempt requires started_at.'
                )
            if 'mutation_attempt_id' in vals:
                if (
                    surface != '_finish_attempt'
                    or current in ATTEMPT_TERMINAL_OUTCOMES
                    or target not in ATTEMPT_TERMINAL_OUTCOMES
                    or record.mutation_attempt_id
                ):
                    raise ValidationError(
                        'Mutation evidence can be linked only once at finish.'
                    )
                mutation = self.env[
                    'shopify.connector.mutation.attempt'
                ].sudo().browse(vals['mutation_attempt_id']).exists()
                if not mutation or mutation.store_id != record.store_id:
                    raise ValidationError(
                        'Execution and mutation evidence must share a store.'
                    )
        return super().write(vals)

    def unlink(self):
        raise AccessError('Execution-attempt evidence can never be deleted.')

    @api.model
    def _create_service(self, values):
        """Claim one job by creating its first durable execution attempt."""
        return self._surface(ATTEMPT_CREATE_SURFACE).create(values)

    def _service_write(self, surface, values):
        if surface not in ATTEMPT_WRITE_SURFACES:
            raise AccessError('Unknown job-attempt service surface.')
        return self._surface(surface).browse(self.ids).write(values)

    def _start_service(self, started_at=None):
        self.ensure_one()
        now = started_at or fields.Datetime.now()
        return self._service_write('_start_attempt', {
            'outcome': 'running',
            'started_at': now,
            'heartbeat_at': now,
        })

    def _heartbeat_service(self, heartbeat_at=None):
        self.ensure_one()
        if self.outcome not in ATTEMPT_ACTIVE_OUTCOMES:
            raise ValidationError(
                'Only an active execution attempt may receive a heartbeat.'
            )
        return self._service_write('_heartbeat_attempt', {
            'heartbeat_at': heartbeat_at or fields.Datetime.now(),
        })

    def _observe_service(self, observations=None, **values):
        self.ensure_one()
        if self.outcome not in ATTEMPT_ACTIVE_OUTCOMES:
            raise ValidationError(
                'Only an active execution attempt may receive observations.'
            )
        existing = dict(self.observations or {})
        incoming = _bounded_json(observations if observations is not None else {})
        if not isinstance(existing, dict) or not isinstance(incoming, dict):
            raise ValidationError('Attempt observations must be JSON objects.')
        existing.update(incoming)
        values['observations'] = existing
        return self._service_write('_observe_attempt', values)

    def _finish_service(
        self, outcome, safe_message=False, error_class=False,
        error_code=False, retry_decision=False, next_retry_at=False,
        finished_at=None, **values
    ):
        self.ensure_one()
        if outcome not in ATTEMPT_TERMINAL_OUTCOMES:
            raise ValidationError('An attempt finish requires a terminal outcome.')
        default_decisions = {
            'succeeded': 'none',
            'retry_scheduled': 'retry',
            'verification_required': 'verify',
            'manual_review': 'review',
            'failed_terminal': 'terminal',
            'cancelled': 'none',
            'owner_lost': 'retry',
        }
        values.update({
            'outcome': outcome,
            'finished_at': finished_at or fields.Datetime.now(),
            'retry_decision': retry_decision or default_decisions[outcome],
        })
        if safe_message is not False:
            values['safe_message'] = safe_message
        if error_class is not False:
            values['error_class'] = error_class
        if error_code is not False:
            values['error_code'] = error_code
        if next_retry_at is not False:
            values['next_retry_at'] = next_retry_at
        return self._service_write('_finish_attempt', values)

    def _mask_terminal_evidence(self):
        """Bounded retention masking; no lifecycle or identity changes."""
        self.ensure_one()
        if self.outcome not in ATTEMPT_TERMINAL_OUTCOMES:
            raise ValidationError(
                'Only terminal execution evidence may be masked.'
            )
        return self._service_write('_mask_terminal_attempt', {
            'safe_message': 'Execution evidence masked for retention.',
            'observations': {'masked': True},
            'shopify_request_id': False,
        })

    @api.constrains(
        'attempt_no', 'claim_token', 'worker_ref', 'outcome',
        'started_at', 'claimed_at', 'finished_at', 'retry_decision',
        'next_retry_at',
    )
    def _check_attempt_lifecycle(self):
        for record in self:
            if record.attempt_no <= 0:
                raise ValidationError('Attempt number must be positive.')
            if not _UUID_RE.match(record.claim_token or ''):
                raise ValidationError('The claim token must be an opaque UUID.')
            if not record.worker_ref:
                raise ValidationError('A worker reference is required.')
            if record.outcome not in ATTEMPT_OUTCOME_KEYS:
                raise ValidationError('Unknown execution-attempt outcome.')
            if (
                record.outcome in ATTEMPT_TERMINAL_OUTCOMES
                and not record.finished_at
            ) or (
                record.outcome in ATTEMPT_ACTIVE_OUTCOMES
                and record.finished_at
            ):
                raise ValidationError(
                    'Attempt finished_at must match its terminal outcome.'
                )
            if record.outcome == 'running' and not record.started_at:
                raise ValidationError(
                    'A running execution attempt requires started_at.'
                )
            if (
                record.retry_decision
                and record.retry_decision not in ATTEMPT_RETRY_DECISION_KEYS
            ):
                raise ValidationError('Unknown retry decision.')

    @api.constrains('job_id', 'run_id', 'mutation_attempt_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()
        for record in self:
            job = record.job_id
            run = record.run_id
            if job and run and job.store_id != run.store_id:
                raise ValidationError(
                    'The execution attempt, job, and run must share a store.'
                )
            if job and 'run_id' in job._fields and job.run_id:
                if not run or job.run_id != run:
                    raise ValidationError(
                        'The execution attempt run must match its job run.'
                    )

    @api.model
    def _sec3_parent_scope_relations(self):
        """All connector parents must resolve to this attempt's store."""
        return (
            ('job_id', 'store'),
            ('run_id', 'store'),
            ('mutation_attempt_id', 'store'),
        )

    def init(self):
        """Quarantine historic scope mismatches before record rules expose them."""
        self._sec3_quarantine_scope_mismatches()
