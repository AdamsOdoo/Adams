from odoo import api, fields, models

from ..tools.redaction import redact
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
    # Not `required=True`: in Odoo 19 the initial INSERT of a new record
    # happens before its stored-related fields are populated from
    # `related=`, so a NOT NULL column here fails `_system_append()`'s
    # `create()` before `job_id.store_id` is ever read (identical class
    # of issue to `shopify.connector.job.idempotency_key`, a
    # stored-computed field fixed the same way). `job_id` is always
    # required, so `store_id` is always non-empty once the row exists.
    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        related='job_id.store_id',
        store=True,
        index=True,
        readonly=True,
    )
    # SEC-3 (#197): company is inherited from the owning store and is never an
    # independent selector. Stored so record rules, searches and grouped reads
    # filter on it in SQL; readonly so it can never diverge from its store.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
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

    @api.model
    def _system_append(
        self, job, event_type, message,
        technical_detail=False, payload_snapshot=False,
        from_state=False, to_state=False,
    ):
        """The one sanctioned write path for system-appended job.log rows.

        No group holds `perm_create` on this model by design -- rows are
        system-appended, not user-authored (AR-019 §10). This is the only
        `sudo()` this file contains, mirroring the Task 002
        `_get_access_token` precedent: never registered as a user-facing
        action, invoked only from other core/domain service code that
        already holds an ACL-gated reference to `job` (all four roles hold
        `perm_read=1` on both `job` and `job.log` today, so this adds no
        new visibility -- only the ability to append the audit trail that
        ACL alone cannot). Every free-text argument is redacted before the
        row is created; `actor_uid` records the acting user, not the
        elevated context.
        """
        self.sudo().create({
            'job_id': job.id,
            'event_type': event_type,
            'from_state': from_state,
            'to_state': to_state,
            'message': redact(message),
            'technical_detail': redact(technical_detail) if technical_detail else technical_detail,
            'payload_snapshot': redact(payload_snapshot) if payload_snapshot else payload_snapshot,
            'actor_uid': self.env.uid,
        })
