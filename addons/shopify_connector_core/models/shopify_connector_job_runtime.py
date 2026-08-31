"""Additive V2 runtime fields on the stable job model.

The legacy dispatcher ignores these nullable columns.  V2 admission supplies
all scheduling values explicitly, so installing this expansion never invents
a run, dependency, lane, or checkpoint for historic work.
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError


V2_PROTECTED_JOB_FIELDS = frozenset((
    'run_id', 'parent_job_id', 'sequence', 'lane', 'lane_priority',
    'available_at', 'blocked_by_job_id',
    'expected_configuration_generation', 'expected_connection_generation',
))


JOB_LANE_SELECTION = [
    ('safety_verification', 'Safety Verification'),
    ('interactive', 'Interactive'),
    ('webhook', 'Webhook'),
    ('odoo_event', 'Odoo Event'),
    ('scheduled', 'Scheduled'),
    ('reconciliation', 'Reconciliation'),
]


class ShopifyConnectorJobRuntime(models.Model):
    _inherit = 'shopify.connector.job'

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.su:
            protected = sorted(set().union(
                *(set(vals) & V2_PROTECTED_JOB_FIELDS for vals in vals_list)
            ))
            if protected:
                raise AccessError(
                    'V2 runtime job fields cannot be supplied through generic '
                    'create(). Use the sanctioned runtime service. Protected '
                    'fields: %s' % ', '.join(protected)
                )
        return super().create(vals_list)

    def write(self, vals):
        protected = sorted(set(vals) & V2_PROTECTED_JOB_FIELDS)
        if protected and not self.env.su:
            raise AccessError(
                'V2 runtime job fields can only be changed through a '
                'sanctioned runtime service. Protected fields: %s'
                % ', '.join(protected)
            )
        return super().write(vals)

    run_id = fields.Many2one(
        comodel_name='shopify.connector.run',
        index=True,
        readonly=True,
        ondelete='set null',
    )
    parent_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    sequence = fields.Integer(readonly=True)
    lane = fields.Selection(
        selection=JOB_LANE_SELECTION,
        index=True,
        readonly=True,
    )
    lane_priority = fields.Integer(index=True, readonly=True)
    available_at = fields.Datetime(index=True, readonly=True)
    # Independent settings epoch captured when a V2 job is admitted.  The
    # claimant compares it with both the parent run and the live canonical
    # settings row; a mode/settings change therefore cannot be crossed by an
    # already queued read.
    expected_configuration_generation = fields.Integer(
        default=0,
        index=True,
        readonly=True,
    )
    blocked_by_job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        index=True,
        readonly=True,
        ondelete='set null',
    )

    @api.constrains(
        'store_id', 'run_id', 'parent_job_id', 'blocked_by_job_id',
        'sequence', 'lane_priority', 'expected_configuration_generation',
        'expected_connection_generation',
    )
    def _check_v2_runtime_scope(self):
        for job in self:
            if job.run_id and job.run_id.store_id != job.store_id:
                raise ValidationError(
                    'A Shopify job and its run must belong to the same store.'
                )
            for relation, label in (
                (job.parent_job_id, 'parent'),
                (job.blocked_by_job_id, 'blocking dependency'),
            ):
                if relation and relation.store_id != job.store_id:
                    raise ValidationError(
                        'A Shopify job and its %s must belong to the same '
                        'store.' % label
                    )
                if relation and relation == job:
                    raise ValidationError(
                        'A Shopify job cannot reference itself as its %s.'
                        % label
                    )
            if job.sequence is not False and job.sequence is not None:
                if job.sequence < 0:
                    raise ValidationError(
                        'A Shopify job sequence cannot be negative.'
                    )
            if job.lane_priority is not False and job.lane_priority is not None:
                if job.lane_priority < 0:
                    raise ValidationError(
                        'A Shopify job lane priority cannot be negative.'
                    )
            value = job.expected_configuration_generation
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(
                    'A Shopify job configuration generation must be an '
                    'integer.'
                )
            if value < 0:
                raise ValidationError(
                    'A Shopify job configuration generation cannot be negative.'
                )
            value = job.expected_connection_generation
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValidationError(
                    'A Shopify job connection generation must be an integer.'
                )
            if value < 0:
                raise ValidationError(
                    'A Shopify job connection generation cannot be negative.'
                )

    @api.constrains('parent_job_id')
    def _check_parent_cycle(self):
        """Reject bounded lineage cycles without an unbounded graph walk."""
        for job in self:
            seen = {job.id} if job.id else set()
            current = job.parent_job_id
            for _depth in range(64):
                if not current:
                    break
                if current.id in seen:
                    raise ValidationError(
                        'A Shopify job parent lineage cannot contain a cycle.'
                    )
                seen.add(current.id)
                current = current.parent_job_id
            else:
                raise ValidationError(
                    'A Shopify job parent lineage exceeds the supported '
                    'depth.'
                )
