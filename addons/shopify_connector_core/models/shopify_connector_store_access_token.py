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

This model deliberately grants NO permission in `ir.model.access.csv`. Its
single deny-only marker has all four permission columns disabled and exists
only so Odoo's module validator can distinguish this deliberate policy from an
accidentally forgotten ACL. No connector group can read this table through RPC,
including an Administrator. The token is reachable only through the sanctioned,
store-scoped `sudo()` accessors on `shopify.connector.store.credential`, which
is the single seam the API client already used before this table existed.

The token is stored plain behind that access control. It is **not** encrypted at
rest -- the same honest residual recorded for `access_token` on the credential
row (AR-022/AR-024/AR-025). No copy anywhere in this connector claims otherwise.

PROVENANCE (Batch 1 correction, 2026-07-30)
-------------------------------------------

`credential_id` alone does NOT prove which credential minted a token. A
rotation updates the credential row **in place**, so the relation still points
at the same record afterwards and a token minted from the previous secret keeps
a relation that looks perfectly current. That is the exact shape of the
reproduced obsolete-token defect: a refresh that read secret pair A, was
overtaken by a rotation to pair B, and then inserted a cache row whose
`credential_id` referenced the (now-rotated) row.

`credential_epoch` and `auth_mode` are therefore stored beside the token and
are what every read compares. The epoch is a monotonic counter the credential
service bumps exactly once per sanctioned set/replace/clear/mode switch, in the
same transaction as the mutation, so a token minted from a superseded identity
is structurally unusable rather than merely unlikely: the read predicate
`cache.credential_epoch = credential.credential_epoch` fails, and the caller
gets the fail-closed "no token" answer instead of an obsolete one.

Neither column is a secret. They exist so provenance can be proved without any
code path reading a token or a client secret to answer the question.

No Shopify request is made in this file. The exchange itself belongs to the API
client, which is the one place in this repository allowed to hold transport.
"""

from odoo import api, fields, models

from .shopify_connector_store_credential import AUTH_MODE_SELECTION


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
    # Which credential row minted this token. Necessary but NOT sufficient on
    # its own -- see the PROVENANCE note in the module docstring. Kept for the
    # store-axis SEC-3 relation below and for the cascade.
    credential_id = fields.Many2one(
        comodel_name='shopify.connector.store.credential',
        required=True,
        index=True,
        readonly=True,
        ondelete='cascade',
    )
    # The credential identity this token was actually minted from, captured
    # before the exchange and revalidated against committed state after it.
    # Non-secret. `required=True` with no default: a cache row that cannot say
    # which identity minted it is exactly the unprovable row this correction
    # refuses to create, and the migration deletes the pre-correction rows that
    # could not carry one rather than inventing a value for them.
    credential_epoch = fields.Integer(required=True, readonly=True)
    # The acquisition mode in force at mint time. A token minted under the
    # client-credentials mode must not survive a switch to the offline mode and
    # be served as if it belonged to it, so the mode travels with the token and
    # every read compares it.
    auth_mode = fields.Selection(
        selection=AUTH_MODE_SELECTION,
        required=True,
        readonly=True,
    )
    access_token = fields.Char(readonly=True)
    obtained_at = fields.Datetime(readonly=True)
    expires_at = fields.Datetime(required=True, readonly=True, index=True)
    # The `scope` string Shopify returned WITH THIS TOKEN, verbatim. Non-secret.
    # It describes the token in this row and nothing else: it is not the store's
    # granted-scope evidence (Test Connection records that separately), and it
    # must never be read as a statement about a token this row no longer holds.
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
