"""The cached, short-lived Shopify Admin API access token of ONE store.

WHY THIS IS A SEPARATE TABLE AND NOT TWO MORE COLUMNS ON THE CREDENTIAL

`shopify.connector.store.credential` is the credential's IDENTITY: which app,
which secret, which offline token a merchant configured. CORE-R2's lifecycle
probe treats any change to that row -- its `write_date`, its token value -- as
proof that the identity changed underneath an in-flight Shopify call, and
discards the network result it already has in hand. That rule is correct and is
not being weakened here.

A `dev_dashboard_client_credentials` access token expires after 24 hours
(Shopify: `expires_in` is "Always 86399"), so the connector re-obtains one on a
schedule. A scheduled rotation of an ephemeral token is NOT a change of
credential identity. Writing it onto the credential row would make every
routine refresh indistinguishable from a merchant replacing their secret: probes
would be discarded, connection evidence would be invalidated and a `connected`
store would be pushed to `reconnect_needed` once a day, for nothing.

So the ephemeral value lives here instead, and the identity row stays still.

ACCESS

This model deliberately carries NO row in `ir.model.access.csv`. That is
stronger than the Administrator-only rule on the credential: no connector group
can read this table through RPC at all, including an Administrator. The token is
reachable only through the sanctioned, store-scoped `sudo()` accessors on
`shopify.connector.store.credential`, which is the single seam the API client
already used before this table existed.

The token is stored plain behind that access control. It is **not** encrypted at
rest -- the same honest residual recorded for `access_token` on the credential
row (AR-022/AR-024/AR-025). No copy anywhere in this connector claims otherwise.

No Shopify request is made in this file. The exchange itself belongs to the API
client, which is the one place in this repository allowed to hold transport.
"""

from odoo import api, fields, models


class ShopifyConnectorStoreAccessToken(models.Model):
    _name = 'shopify.connector.store.access.token'
    _description = 'Shopify Connector Store Access Token Cache'
    # Same mixin every store-scoped connector row uses, so the SEC-3 rules and
    # the same-store parent-consistency constraint apply to this table too.
    _inherit = 'shopify.connector.scope.mixin'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='cascade',
    )
    # SEC-3 (#197): company is inherited from the owning store and is never an
    # independent selector.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    # Which credential minted this token. A cache row whose credential row has
    # been replaced is stale by construction; the credential service unlinks it
    # on every mutation, and this relation is what makes that provable rather
    # than assumed.
    credential_id = fields.Many2one(
        comodel_name='shopify.connector.store.credential',
        required=True,
        index=True,
        readonly=True,
        ondelete='cascade',
    )
    access_token = fields.Char(readonly=True)
    obtained_at = fields.Datetime(readonly=True)
    expires_at = fields.Datetime(required=True, readonly=True, index=True)
    # The `scope` string Shopify returns with the token. Non-secret, and the
    # only evidence available about what the exchanged token may actually do,
    # so it is worth keeping next to the token it describes.
    granted_scope_snapshot = fields.Char(readonly=True)

    _store_id_uniq = models.Constraint(
        'UNIQUE(store_id)',
        'Only one cached access token is allowed per store.',
    )

    @api.model
    def _sec3_parent_scope_relations(self):
        # The credential carries its own `store_id`, so the STORE axis is
        # available and is strictly stronger than the company axis: one company
        # may own several stores, and a token row pointing at another store's
        # credential must be refused rather than merely company-checked.
        return super()._sec3_parent_scope_relations() + (
            ('credential_id', 'store'),
        )

    @api.constrains('store_id', 'credential_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()
