from odoo import fields, models


class ShopifyConnectorCallLease(models.Model):
    """Committed admission-lease for one in-flight business Shopify call (CORE-R2).

    The independently-committed, cross-transaction quiescence signal from the
    merged CORE-R2 design (AR-047; analysis §10, packet §7/§9). One row is
    written on an owned side transaction *before* a business call is admitted
    (`shopify.connector.api.client._admit`) and deleted *after* the call and its
    local reconciliation finish (`_release_lease`, driven by the
    `execute_business` context-manager `__exit__`). Because the row is committed
    on its own transaction under a `FOR SHARE` lock on the store row, it is
    visible to any other connection (a future disconnect controller) and survives
    a crash of the admitting worker — a job-state `running` flag cannot provide
    either property (analysis §3).

    This table is deliberately **secret-free and payload-free**. It carries only
    the coordination minimum: which store, an opaque lease key, a plain-Integer
    diagnostic job id (never a Many2one — a job FK would take a `FOR KEY SHARE`
    lock on a drain-locked job row and block admission, analysis §10/§14), an
    opaque worker tag, and the admit/expiry timestamps. It never stores a token,
    a credential, a GraphQL query, request variables, a payload, or any
    customer/product data, and it is never logged.

    **Foundation slice (Slice 1) scope.** The model, its ACL, the admission that
    writes it, and the context-managed release that clears it are delivered here
    and remain dormant — no production call site creates a lease yet. The
    disconnect controller that *reads* the lease count, the `disconnecting`
    lifecycle, `expires_at`-based `timed_out`/`completed` finalization, and the
    direction-C cleanup are deliberately NOT in this slice (they arrive in a later
    CORE-R2 slice). `expires_at` is therefore recorded but not yet consumed.
    """

    _name = 'shopify.connector.call.lease'
    _description = 'Shopify Connector Call Lease'
    _rec_name = 'lease_key'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='cascade',
    )
    # Opaque UUID key generated at admission; the only stable handle used to
    # release exactly one lease. Opacity is a property of the value written by
    # `_admit` (a bare uuid4 hex), never derived from store/job/token.
    lease_key = fields.Char(required=True, index=True, readonly=True)
    # A plain Integer for diagnostics only -- deliberately NOT a Many2one to
    # `shopify.connector.job`: a job FK would acquire a `FOR KEY SHARE` lock on a
    # row a concurrent drain may hold `FOR NO KEY UPDATE`, blocking admission
    # (analysis §10/§14). No referential action, no join, no lock coupling.
    job_id = fields.Integer(required=True, readonly=True)
    # Opaque server/pid/db diagnostic tag; non-secret, never a token.
    worker_ref = fields.Char(readonly=True)
    admitted_at = fields.Datetime(required=True, readonly=True)
    # Recorded at admission (admitted_at + MAX_CALL_LIFETIME). Under direction C
    # an expired-but-unreleased lease is treated as unknown/live and is never a
    # completion trigger; the controller that would consult this field is a later
    # slice, so the value is inert here (indexed for that future expiry lookup).
    expires_at = fields.Datetime(required=True, index=True, readonly=True)

    _lease_key_uniq = models.Constraint(
        'UNIQUE(lease_key)',
        'A call lease with this key already exists.',
    )
