"""Additive V2 identity and admission fences for mutation evidence.

The original mutation-attempt model is a protected Layer-2 evidence store.
This inheritance owns the nullable V2 identity columns and their fences so
the legacy model remains source-size stable and run-less rows retain their
old behaviour.
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError


V2_MUTATION_RUNTIME_MODES = frozenset((
    'subscriptions',
    'inventory',
    'product_export',
    'fulfillment',
    'all',
))
V2_ACTIVE_RUN_STATES = frozenset(('admitted', 'running', 'waiting'))


class ShopifyConnectorMutationAttemptV2Runtime(models.Model):
    """Store the server-derived run/configuration snapshot on C2 evidence."""

    _inherit = 'shopify.connector.mutation.attempt'

    run_id = fields.Many2one(
        comodel_name='shopify.connector.run',
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    expected_configuration_generation = fields.Integer(
        default=0,
        index=True,
        readonly=True,
    )

    _non_negative_configuration_generation = models.Constraint(
        'CHECK(expected_configuration_generation >= 0)',
        'The expected configuration generation cannot be negative.',
    )

    def write(self, vals):
        if set(vals) & {
            'run_id', 'expected_configuration_generation',
        }:
            raise ValidationError('Mutation-attempt V2 identity is immutable.')
        return super().write(vals)

    def _lock_with_original_job(self, original_job):
        """Lock one mutation lineage in the canonical job -> attempt order."""
        self.ensure_one()
        Job = self.env['shopify.connector.job']
        locked_job = Job.browse(original_job.id).sudo().try_lock_for_update()
        if not locked_job:
            return False
        locked_job.invalidate_recordset()
        locked_attempt = self.sudo().try_lock_for_update()
        if not locked_attempt:
            return False
        locked_attempt.invalidate_recordset()
        if locked_attempt.job_id != locked_job:
            return False
        return locked_job, locked_attempt

    @api.model
    def _create_attempt_intent(self, values):
        """Derive V2 identity from the locked job before the C2 create.

        The base method performs the rest of the C2 validation and the
        sanctioned side-cursor create.  This wrapper only canonicalizes the
        two new fields while the job owner row is locked, so a worker cannot
        choose a different run or configuration generation.
        """
        values = dict(values)
        job = self.env['shopify.connector.job'].browse(
            values.get('job_id'),
        ).try_lock_for_update()
        if job:
            job.invalidate_recordset()
            dispatch = self.env['shopify.connector.job.dispatch']
            if not getattr(job, 'run_id', False):
                if dispatch._is_v2_mutation_job(job):
                    raise ValidationError(
                        'The V2 mutation job lost its run before C2.'
                    )
                if values.get('run_id') not in (None, False):
                    raise ValidationError(
                        'A legacy mutation attempt cannot carry a V2 run.'
                    )
                supplied_configuration = values.get(
                    'expected_configuration_generation',
                )
                if supplied_configuration not in (None, False, 0):
                    raise ValidationError(
                        'A legacy mutation attempt cannot carry a V2 '
                        'configuration generation.'
                    )
                values['run_id'] = False
                values['expected_configuration_generation'] = 0
                return super()._create_attempt_intent(values)
            scope = self._v2_locked_scope(job)
            if not scope:
                raise ValidationError(
                    'The mutation job scope is unavailable at C2.'
                )
            job, _attempt, _run, store, _settings = scope
            run = getattr(job, 'run_id', False)
            if run:
                if not dispatch._v2_admit_mutation_job(job, phase='c2'):
                    raise ValidationError(
                        'The V2 mutation admission fence failed at C2.'
                    )
                expected_connection = store.connection_generation
                supplied_connection = values.get(
                    'expected_connection_generation',
                )
                if isinstance(supplied_connection, bool):
                    raise ValidationError(
                        'The expected connection generation must be an '
                        'integer.'
                    )
                try:
                    supplied_connection = int(supplied_connection)
                except (TypeError, ValueError) as exc:
                    raise ValidationError(
                        'The expected connection generation must be an '
                        'integer.'
                    ) from exc
                if supplied_connection != expected_connection:
                    raise ValidationError(
                        'The mutation attempt connection snapshot is stale.'
                    )
                supplied_store_identity = values.get(
                    'expected_store_identity',
                )
                if supplied_store_identity != store.shop_domain:
                    raise ValidationError(
                        'The mutation attempt store identity is stale.'
                    )
                values['expected_connection_generation'] = (
                    expected_connection
                )
                values['expected_store_identity'] = store.shop_domain
                supplied_run = values.get('run_id')
                supplied_run_id = getattr(supplied_run, 'id', supplied_run)
                if supplied_run_id not in (None, False, run.id):
                    raise ValidationError(
                        'The mutation attempt run must match its owning job.'
                    )
                expected_configuration = (
                    job.expected_configuration_generation or 0
                )
                supplied_configuration = values.get(
                    'expected_configuration_generation',
                )
                if supplied_configuration not in (None, False):
                    if isinstance(supplied_configuration, bool):
                        raise ValidationError(
                            'The expected configuration generation must be '
                            'an integer.'
                        )
                    try:
                        supplied_configuration = int(supplied_configuration)
                    except (TypeError, ValueError) as exc:
                        raise ValidationError(
                            'The expected configuration generation must be '
                            'an integer.'
                        ) from exc
                    if supplied_configuration != expected_configuration:
                        raise ValidationError(
                            'The mutation attempt configuration snapshot is '
                            'stale.'
                        )
                values['run_id'] = run.id
                values['expected_configuration_generation'] = (
                    expected_configuration
                )
        return super()._create_attempt_intent(values)

    @api.model
    def _v2_locked_scope(self, job, *, attempt=False):
        """Lock V2 scope rows in one fixed order and return fresh records.

        The order is job -> attempt -> run -> store -> settings.  C2, C3,
        transport admission, and stale recovery all use this order so a
        generation or mode change cannot race a final transport decision.
        """
        locked_job = job.sudo().try_lock_for_update() if job else job
        if not locked_job:
            return None
        locked_job.invalidate_recordset()
        locked_attempt = attempt
        if locked_attempt:
            locked_attempt = locked_attempt.sudo().try_lock_for_update()
            if not locked_attempt:
                return None
            locked_attempt.invalidate_recordset()
        run = (
            getattr(locked_attempt, 'run_id', False)
            if locked_attempt else False
        ) or getattr(locked_job, 'run_id', False)
        if run:
            run = run.sudo().try_lock_for_update()
            if not run:
                return None
            run.invalidate_recordset()
        store = getattr(locked_job, 'store_id', False)
        if store:
            store = store.sudo().try_lock_for_update()
            if not store:
                return None
            store.invalidate_recordset()
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([
            ('store_id', '=', store.id if store else False),
        ], limit=1)
        if settings:
            settings = settings.try_lock_for_update()
            settings.invalidate_recordset()
        return locked_job, locked_attempt, run, store, settings

    @api.model
    def _v2_scope_mismatch(self, job, *, attempt=False, lock=True):
        """Return a local V2 scope failure, or ``None`` for legacy work."""
        if not job or not job.exists():
            return 'run_identity' if attempt else None
        if (
            not getattr(job, 'run_id', False)
            and not (attempt and getattr(attempt, 'run_id', False))
        ):
            return None
        if lock:
            scope = self._v2_locked_scope(job, attempt=attempt)
            if not scope:
                return 'scope_row_missing'
            job, attempt, run, store, settings = scope
            if not run or not store or not settings:
                return 'scope_row_missing'
        else:
            run = job.run_id
            store = job.store_id
            settings = self.env[
                'shopify.connector.store.settings'
            ].sudo().search([('store_id', '=', store.id)], limit=1)
            if not settings:
                return 'scope_row_missing'

        company_ids = tuple(self.env.companies.ids) or (self.env.company.id,)
        if store.company_id.id not in company_ids:
            return 'company_scope'
        if (
            job.store_id != store
            or run.store_id != store
            or job.company_id != store.company_id
            or run.company_id != store.company_id
            or settings.company_id != store.company_id
        ):
            return 'company_identity'
        if store.state != 'connected' or run.state not in V2_ACTIVE_RUN_STATES:
            return 'store_state'
        if run.cancel_requested_at:
            return 'cancel_requested'
        if settings.v2_runtime_mode not in V2_MUTATION_RUNTIME_MODES:
            return 'runtime_mode'
        expected_connection = (
            attempt.expected_connection_generation if attempt
            else job.expected_connection_generation
        )
        expected_configuration = (
            attempt.expected_configuration_generation if attempt
            else job.expected_configuration_generation
        )
        if (
            job.expected_connection_generation != store.connection_generation
            or run.expected_connection_generation != store.connection_generation
            or expected_connection != store.connection_generation
        ):
            return 'connection_generation'
        if (
            job.expected_configuration_generation
            != settings.configuration_generation
            or run.expected_configuration_generation
            != settings.configuration_generation
            or expected_configuration != settings.configuration_generation
        ):
            return 'configuration_generation'
        if attempt:
            if (
                attempt.job_id != job
                or attempt.run_id != run
                or job.run_id != run
            ):
                return 'run_identity'
            if attempt.mutation_domain != job.job_type:
                return 'mutation_domain'
            if attempt.expected_store_identity != store.shop_domain:
                return 'store_identity'
        return None

    @api.constrains(
        'job_id', 'run_id', 'expected_connection_generation',
        'expected_configuration_generation',
    )
    def _check_v2_runtime_identity(self):
        for attempt in self:
            job = attempt.job_id
            run = getattr(job, 'run_id', False) if job else False
            if not run:
                if attempt.run_id:
                    raise ValidationError(
                        'A legacy mutation attempt cannot carry a V2 run.'
                    )
                continue
            if attempt.run_id != run:
                raise ValidationError(
                    'The mutation attempt run must match its owning job.'
                )
            if (
                attempt.expected_configuration_generation
                != job.expected_configuration_generation
            ):
                raise ValidationError(
                    'The mutation attempt configuration generation must match '
                    'its owning job.'
                )

    @api.model
    def _sec3_parent_scope_relations(self):
        return tuple(super()._sec3_parent_scope_relations()) + (
            ('run_id', 'store'),
        )

    @api.constrains('store_id', 'job_id', 'run_id')
    def _check_v2_sec3_parent_scope(self):
        self._sec3_check_parent_scope()
