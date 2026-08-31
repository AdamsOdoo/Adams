"""Durable V2 request/run evidence.

The run model owns the request record and lifecycle transitions.  Pure
metadata validation lives in shopify_connector_run_metadata.py so this
production model remains small without changing its import API.
"""

import uuid

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .shopify_connector_run_metadata import (
    RUN_CREATE_LIFECYCLE_FIELDS,
    RUN_CREATE_SURFACE,
    RUN_FINALIZE_NAME_SURFACE,
    RUN_LEGAL_TRANSITIONS,
    RUN_SERVICE_SENTINEL,
    RUN_SERVICE_SENTINEL_CONTEXT,
    RUN_STATE_KEYS,
    RUN_STATE_SELECTION,
    RUN_SURFACE_FIELDS,
    RUN_TERMINAL_STATES,
    RUN_TRIGGER_SELECTION,
    RUN_WORKFLOW_SELECTION,
    RUN_WRITE_CONTEXT,
    RUN_WRITE_SURFACES,
    _MAX_CONFIGURATION_BYTES,
    _MAX_SUMMARY_CHARS,
    _RUN_NAME_RE,
    _bounded_json,
    _configuration_generation_for_store,
    _generation_for_store,
    _required_text,
    _safe_fingerprint,
    _safe_json,
    _safe_text,
)


class ShopifyConnectorRun(models.Model):
    """One durable request spanning one or more connector jobs."""

    _name = 'shopify.connector.run'
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Run'
    _order = 'requested_at desc, id desc'

    # `name` is a human reference, not an idempotency key.  It is assigned
    # from the database id after insert so concurrent requests cannot produce
    # the same displayed sequence.
    name = fields.Char(required=True, readonly=True, index=True)
    request_key = fields.Char(required=True, index=True, readonly=True)
    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    # A stored related field is the only company authority.  It is intentionally
    # not independently writable or selectable.  Existing V1 models document
    # that Odoo may insert the row before a stored related value is evaluated;
    # therefore the physical column stays nullable while the relation itself
    # is always derived from required store_id.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    expected_connection_generation = fields.Integer(
        required=True,
        default=0,
        readonly=True,
    )
    expected_configuration_generation = fields.Integer(
        required=True,
        default=0,
        readonly=True,
    )
    workflow = fields.Selection(
        selection=RUN_WORKFLOW_SELECTION,
        required=True,
        index=True,
        readonly=True,
    )
    operation = fields.Char(required=True, index=True, readonly=True)
    trigger = fields.Selection(
        selection=RUN_TRIGGER_SELECTION,
        required=True,
        index=True,
        readonly=True,
    )
    actor_uid = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        ondelete='restrict',
    )
    requested_at = fields.Datetime(
        required=True,
        index=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    admitted_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(index=True, readonly=True)
    state = fields.Selection(
        selection=RUN_STATE_SELECTION,
        required=True,
        index=True,
        default='requested',
        readonly=True,
    )
    scope_summary = fields.Char(required=True, readonly=True)
    scope_fingerprint = fields.Char(index=True, readonly=True)
    configuration_snapshot = fields.Json(
        required=True,
        default=dict,
        readonly=True,
    )
    result_summary = fields.Text(readonly=True)
    cancel_requested_at = fields.Datetime(readonly=True)
    cancel_requested_by = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        ondelete='restrict',
    )
    cancel_reason = fields.Char(readonly=True)
    correlation_id = fields.Char(required=True, index=True, readonly=True)

    _store_request_key_uniq = models.Constraint(
        'UNIQUE(store_id, request_key)',
        'A run with this request key already exists for this store.',
    )
    _generation_non_negative = models.Constraint(
        'CHECK(expected_connection_generation >= 0 AND '
        'expected_configuration_generation >= 0)',
        'Expected connection/configuration generations cannot be negative.',
    )
    _name_format = models.Constraint(
        "CHECK(name ~ '^RUN-[0-9]{8}-[0-9]+$')",
        'The run reference must use the RUN-YYYYMMDD-sequence format.',
    )
    _terminal_finished = models.Constraint(
        "CHECK((state IN ('succeeded', 'partially_succeeded', "
        "'failed_terminal', 'cancelled') AND finished_at IS NOT NULL) OR "
        "(state NOT IN ('succeeded', 'partially_succeeded', "
        "'failed_terminal', 'cancelled') AND finished_at IS NULL))",
        'Only terminal runs may have a finished timestamp.',
    )

    @api.model
    def _surface(self, name):
        if name not in RUN_WRITE_SURFACES:
            raise AccessError('Unknown Shopify run write surface.')
        return self.sudo().with_context(**{
            RUN_WRITE_CONTEXT: name,
            RUN_SERVICE_SENTINEL_CONTEXT: RUN_SERVICE_SENTINEL,
        })

    @api.model
    def _surface_is_open(self):
        context = self.env.context
        return (
            self.env.su
            and context.get(RUN_SERVICE_SENTINEL_CONTEXT)
            is RUN_SERVICE_SENTINEL
            and context.get(RUN_WRITE_CONTEXT) in RUN_WRITE_SURFACES
        )

    @api.model
    def _prepare_service_values(self, values):
        values = dict(values or {})
        if values.get('state') not in (None, False, 'requested'):
            raise ValidationError(
                'A new run must start in the requested state.'
            )
        inconsistent = {
            field_name for field_name in RUN_CREATE_LIFECYCLE_FIELDS
            if values.get(field_name) not in (None, False, {}, [])
        }
        if inconsistent:
            raise ValidationError(
                'A new requested run cannot include lifecycle or result '
                'fields: %s.' % ', '.join(sorted(inconsistent))
            )
        if not values.get('store_id'):
            raise ValidationError('A run must belong to a Shopify store.')
        store = self.env['shopify.connector.store'].sudo().browse(
            values['store_id']
        ).exists()
        if not store:
            raise ValidationError('The run store does not exist.')

        values.setdefault('request_key', str(uuid.uuid4()))
        values.setdefault('correlation_id', 'run:%s' % uuid.uuid4())
        values.setdefault('requested_at', fields.Datetime.now())
        values.setdefault('state', 'requested')
        values.setdefault('expected_connection_generation',
                          _generation_for_store(store))
        values.setdefault(
            'expected_configuration_generation',
            _configuration_generation_for_store(self.env, store),
        )
        values.setdefault('configuration_snapshot', {})
        values.setdefault('scope_summary', 'Connector operation')
        if values.get('trigger') != 'system' and not values.get('actor_uid'):
            values['actor_uid'] = self.env.uid

        if not values.get('workflow') or not values.get('operation'):
            raise ValidationError('Run workflow and operation are required.')
        if not values.get('trigger'):
            raise ValidationError('Run trigger is required.')
        values['request_key'] = _required_text(
            values['request_key'], 'request_key', 128,
        )
        values['correlation_id'] = _required_text(
            values['correlation_id'], 'correlation_id', 128,
        )
        values['operation'] = _required_text(
            values['operation'], 'operation', 128,
        )
        values['scope_summary'] = _required_text(
            values['scope_summary'], 'scope_summary', 512,
        )
        actor_id = values.get('actor_uid')
        if values['trigger'] != 'system' and not actor_id:
            raise ValidationError(
                'Non-system runs require an actor identity.'
            )
        if actor_id:
            try:
                actor_id = int(actor_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError('actor_uid must reference a user.') from exc
            if not self.env['res.users'].sudo().browse(actor_id).exists():
                raise ValidationError('actor_uid must reference an existing user.')
            values['actor_uid'] = actor_id
        values['scope_fingerprint'] = _safe_fingerprint(
            values.get('scope_fingerprint'),
        )
        if values.get('result_summary'):
            values['result_summary'] = _safe_text(
                values['result_summary'], _MAX_SUMMARY_CHARS,
            )
        generation = values.get('expected_connection_generation', 0)
        try:
            generation = int(generation)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                'The expected connection generation must be an integer.'
            ) from exc
        if generation < 0:
            raise ValidationError(
                'The expected connection generation cannot be negative.'
            )
        values['expected_connection_generation'] = generation

        configuration_generation = values.get(
            'expected_configuration_generation', 0,
        )
        if isinstance(configuration_generation, bool):
            raise ValidationError(
                'The expected configuration generation must be an integer.'
            )
        try:
            configuration_generation = int(configuration_generation)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                'The expected configuration generation must be an integer.'
            ) from exc
        if configuration_generation < 0:
            raise ValidationError(
                'The expected configuration generation cannot be negative.'
            )
        values['expected_configuration_generation'] = configuration_generation

        # Keep the two epochs in the allowlisted snapshot as well as in their
        # immutable columns.  This makes run evidence self-explanatory without
        # permitting callers to smuggle secrets or raw configuration through
        # the snapshot sanitizer.
        snapshot = values.get('configuration_snapshot')
        if snapshot is None:
            snapshot = {}
        if not isinstance(snapshot, dict):
            raise ValidationError(
                'The run configuration snapshot must be a JSON object.'
            )
        snapshot = dict(snapshot)
        snapshot.setdefault(
            'connection_generation', generation,
        )
        snapshot.setdefault(
            'configuration_generation', configuration_generation,
        )
        values['configuration_snapshot'] = _bounded_json(
            snapshot,
            'The run configuration snapshot',
            _MAX_CONFIGURATION_BYTES,
        )

        # The placeholder itself satisfies the format constraint.  `create`
        # replaces it with the final database-id sequence after the insert.
        if not values.get('name'):
            requested = fields.Datetime.to_datetime(values['requested_at'])
            values['name'] = 'RUN-%s-0000000000' % requested.strftime(
                '%Y%m%d'
            )
        else:
            values['name'] = _safe_text(values['name'], 128)
        if not _RUN_NAME_RE.match(values['name']):
            raise ValidationError(
                'The run reference must use RUN-YYYYMMDD-sequence format.'
            )
        return values

    @api.model_create_multi
    def create(self, vals_list):
        if not self._surface_is_open() or (
            self.env.context.get(RUN_WRITE_CONTEXT) != RUN_CREATE_SURFACE
        ):
            raise AccessError(
                'Runs can only be created by the connector runtime service.'
            )
        prepared = [self._prepare_service_values(values) for values in vals_list]
        records = super().create(prepared)
        # The id is a database-serialized sequence and is therefore safe under
        # concurrent workers without a second sequence table or global lock.
        for record, values in zip(records, prepared):
            if values['name'].endswith('-0000000000'):
                requested = fields.Datetime.to_datetime(record.requested_at)
                record._surface(RUN_FINALIZE_NAME_SURFACE).write({
                    'name': 'RUN-%s-%06d' % (
                        requested.strftime('%Y%m%d'), record.id,
                    ),
                })
        return records

    def write(self, vals):
        if not self._surface_is_open():
            raise AccessError(
                'Runs can only be changed by the connector runtime service.'
            )
        surface = self.env.context.get(RUN_WRITE_CONTEXT)
        allowed = RUN_SURFACE_FIELDS[surface]
        if surface == RUN_CREATE_SURFACE:
            raise AccessError(
                'The run creation surface cannot mutate an existing run.'
            )
        if allowed is not None and set(vals) - allowed:
            raise AccessError(
                'The selected run service surface cannot change these fields.'
            )
        vals = dict(vals)
        if 'scope_summary' in vals:
            vals['scope_summary'] = _safe_text(vals['scope_summary'], 512)
        if 'result_summary' in vals and vals['result_summary']:
            vals['result_summary'] = _safe_text(
                vals['result_summary'], _MAX_SUMMARY_CHARS,
            )
        if 'configuration_snapshot' in vals:
            vals['configuration_snapshot'] = _bounded_json(
                vals['configuration_snapshot'],
                'The run configuration snapshot',
                _MAX_CONFIGURATION_BYTES,
            )
        if surface == RUN_FINALIZE_NAME_SURFACE:
            if set(vals) != {'name'}:
                raise AccessError(
                    'The run-name surface can change only name.'
                )
            name = _required_text(vals['name'], 'name', 128)
            if not _RUN_NAME_RE.match(name):
                raise ValidationError(
                    'The run reference must use RUN-YYYYMMDD-sequence format.'
                )
            for record in self:
                if record.state != 'requested' or not record.name.endswith(
                    '-0000000000'
                ):
                    raise ValidationError(
                        'A run name can only be finalized once at creation.'
                    )
            return super().write({'name': name})
        immutable = {
            'request_key', 'store_id', 'company_id',
            'expected_connection_generation',
            'expected_configuration_generation', 'workflow', 'operation',
            'trigger', 'actor_uid', 'requested_at', 'scope_fingerprint',
            'correlation_id', 'configuration_snapshot', 'scope_summary',
            'name',
        }
        if immutable.intersection(vals):
            raise ValidationError('Run identity and configuration are immutable.')
        for record in self:
            if record.state in RUN_TERMINAL_STATES:
                raise ValidationError('A terminal run is immutable.')
            if surface == '_request_cancel' and record.cancel_requested_at:
                raise ValidationError(
                    'A run cancellation request is append-only.'
                )
            if 'state' in vals:
                target = vals['state']
                if target not in RUN_STATE_KEYS or target not in (
                    RUN_LEGAL_TRANSITIONS.get(record.state, frozenset())
                ):
                    raise ValidationError(
                        'Illegal run transition %s -> %s.' % (
                            record.state, target,
                        )
                    )
            target_state = vals.get('state', record.state)
            finished = vals.get('finished_at', record.finished_at)
            if target_state in RUN_TERMINAL_STATES and not finished:
                raise ValidationError(
                    'A terminal run requires finished_at in the same service write.'
                )
            if target_state not in RUN_TERMINAL_STATES and finished:
                raise ValidationError(
                    'Only a terminal run may have finished_at.'
                )
        return super().write(vals)

    def unlink(self):
        raise AccessError('Run evidence can never be deleted.')

    @api.model
    def _create_service(self, values):
        """Create one run through the opaque internal service surface."""
        values = dict(values or {})
        if values.get('trigger') != 'system':
            actor_id = values.get('actor_uid') or self.env.uid
            try:
                actor_id = int(actor_id)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    'Non-system runs require a valid actor identity.'
                ) from exc
            if actor_id != self.env.uid:
                raise AccessError(
                    'A non-system run actor must be the calling user.'
                )
            values['actor_uid'] = actor_id
        return self._surface(RUN_CREATE_SURFACE).create(values)

    def _service_write(self, surface, values):
        if surface not in RUN_WRITE_SURFACES:
            raise AccessError('Unknown Shopify run service surface.')
        return self._surface(surface).browse(self.ids).write(values)

    def _admit_service(self, admitted_at=None):
        self.ensure_one()
        return self._service_write('_admit_run', {
            'state': 'admitted',
            'admitted_at': admitted_at or fields.Datetime.now(),
        })

    def _transition_service(self, state, result_summary=False):
        self.ensure_one()
        values = {'state': state}
        if result_summary is not False:
            values['result_summary'] = result_summary
        return self._service_write('_transition_run', values)

    def _finish_service(self, state, result_summary=False, finished_at=None):
        self.ensure_one()
        if state not in RUN_TERMINAL_STATES:
            raise ValidationError('A run finish must use a terminal state.')
        values = {
            'state': state,
            'finished_at': finished_at or fields.Datetime.now(),
        }
        if result_summary is not False:
            values['result_summary'] = result_summary
        return self._service_write('_finish_run', values)

    def _request_cancel_service(self, reason):
        self.ensure_one()
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError('A cancellation reason is required.')
        return self._service_write('_request_cancel', {
            'cancel_requested_at': fields.Datetime.now(),
            'cancel_requested_by': self.env.uid,
            'cancel_reason': _safe_text(reason.strip(), 512),
        })

    @api.constrains(
        'trigger', 'actor_uid', 'cancel_requested_at',
        'cancel_requested_by', 'cancel_reason',
    )
    def _check_run_metadata(self):
        for record in self:
            for field_name in (
                'request_key', 'correlation_id', 'operation', 'scope_summary',
            ):
                if not (getattr(record, field_name) or '').strip():
                    raise ValidationError(
                        '%s cannot be blank.' % field_name
                    )
            if record.trigger != 'system' and not record.actor_uid:
                raise ValidationError(
                    'Only a system-triggered run may omit actor_uid.'
                )
            cancellation = (
                record.cancel_requested_at,
                record.cancel_requested_by,
                record.cancel_reason,
            )
            if any(cancellation) and not all(cancellation):
                raise ValidationError(
                    'Cancellation metadata must be complete or empty.'
                )

    @api.constrains(
        'expected_connection_generation',
        'expected_configuration_generation',
    )
    def _check_expected_generations(self):
        for record in self:
            for field_name in (
                'expected_connection_generation',
                'expected_configuration_generation',
            ):
                value = getattr(record, field_name)
                if isinstance(value, bool) or not isinstance(value, int):
                    raise ValidationError(
                        '%s must be an integer.' % field_name
                    )
                if value < 0:
                    raise ValidationError(
                        '%s cannot be negative.' % field_name
                    )

    @api.constrains('scope_fingerprint')
    def _check_scope_fingerprint(self):
        for record in self:
            if record.scope_fingerprint:
                _safe_fingerprint(record.scope_fingerprint)

    @api.constrains('state', 'finished_at')
    def _check_terminal_timestamp(self):
        for record in self:
            if (
                record.state in RUN_TERMINAL_STATES
                and not record.finished_at
            ) or (
                record.state not in RUN_TERMINAL_STATES
                and record.finished_at
            ):
                raise ValidationError(
                    'Run finished_at must exactly match terminal state.'
                )

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()
