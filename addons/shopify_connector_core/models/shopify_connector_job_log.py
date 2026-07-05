from odoo import fields, models

from .shopify_connector_job import JOB_STATE_SELECTION


class ShopifyConnectorJobLog(models.Model):
    """Append-only child record per attempt/state-transition/manual-action.

    Kept separate from ``shopify.connector.job`` so retrying a job never
    overwrites or loses its own history (core-naming-schema-planning.md
    §6). ``job_id`` uses ``ondelete='restrict'``, not ``cascade`` -- a
    job's log rows are its audit history, not disposable children.
    """

    _name = 'shopify.connector.job.log'
    _description = 'Shopify Connector Job Log'

    job_id = fields.Many2one(
        comodel_name='shopify.connector.job',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        related='job_id.store_id',
        store=True,
        required=True,
        index=True,
        readonly=True,
    )
    event_type = fields.Selection(
        selection=[
            ('attempt', 'Attempt'),
            ('state_change', 'State Change'),
            ('verification_read', 'Verification Read'),
            ('manual_action', 'Manual Action'),
            ('note', 'Note'),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    from_state = fields.Selection(selection=JOB_STATE_SELECTION, readonly=True)
    to_state = fields.Selection(selection=JOB_STATE_SELECTION, readonly=True)
    message = fields.Text(required=True, readonly=True)
    technical_detail = fields.Text(readonly=True)
    payload_snapshot = fields.Text(readonly=True)
    actor_uid = fields.Many2one(comodel_name='res.users', readonly=True)
    occurred_at = fields.Datetime(
        required=True,
        index=True,
        default=fields.Datetime.now,
        readonly=True,
    )
