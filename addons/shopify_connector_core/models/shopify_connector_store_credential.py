from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class ShopifyConnectorStoreCredential(models.Model):
    """Admin-only Shopify Admin API credential for one store (Task 002).

    Access is default-deny: only `group_shopify_connector_admin` has an
    ACL row on this model -- auditor/operator/reviewer have no row at
    all (deliberate, not an omission), and `access_token` additionally
    carries its own field-level `groups=` as a second, independent
    layer.

    `access_token` is stored plain behind that access control -- it is
    **not encrypted**. It remains readable to any `sudo()`-context code
    path, to direct database access, and to database backups. This is
    the honest residual accepted via AR-022/AR-024/AR-025: masking and
    access control are real protections, encryption-at-rest is not one
    of them here, and no part of this module may claim otherwise.

    `client_id`, `client_secret`, a token cache, and an expiry field are
    deliberately absent: Task 002 supports exactly one credential shape
    (`token_variant='offline_custom_app'`, a single long-lived value).
    This model is the seam a future, separately gated task can extend
    (via `selection_add` plus new fields) once ChatGPT decides the
    MBQ-05 acquisition-path direction -- no migration of this shape is
    required to do so.

    The only sanctioned `sudo()` in this module is inside
    `_get_access_token`, scoped to the one store already being operated
    on (DEC-004).
    """

    _name = 'shopify.connector.store.credential'
    _description = 'Shopify Connector Store Credential'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    access_token = fields.Char(
        copy=False,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    token_variant = fields.Selection(
        selection=[('offline_custom_app', 'Offline Custom App Token')],
        default='offline_custom_app',
    )
    credential_state = fields.Selection(
        selection=[
            ('absent', 'Absent'),
            ('present', 'Present'),
            ('invalid', 'Invalid'),
        ],
        required=True,
        default='absent',
        readonly=True,
    )

    _store_id_uniq = models.Constraint(
        'UNIQUE(store_id)',
        'Only one credential record is allowed per store.',
    )

    @api.model
    def action_set_token(self, store, value):
        """Create-or-update the store's credential value.

        Runs as the calling user (no `sudo()`) so the ACL layer stays
        live: a non-admin caller fails with `AccessError` from the ORM
        itself. Any set/update -- including overwriting an *existing*
        credential row (e.g. re-entering/correcting a token) -- clears
        `credential_last_verified_at`: a token change invalidates
        whatever verification was recorded for the value it replaced,
        closing the Task 005 stale-evidence path at the source instead
        of relying on the credential row's own `write_date` as a
        freshness signal. A `connected` store also moves to
        `reconnect_needed` (and bumps the connection epoch): business-job
        gating and `execute_business` admission key off `store.state` /
        `connection_generation`, so a credential mutation must invalidate
        both, not just the verification mirror. Delegates to the shared
        store->credential-ordered `_mutate_token`.
        """
        return self._mutate_token(store, value, is_replace=False)

    @api.model
    def action_replace_token(self, store, value):
        """Replace the store's credential value and reset verification.

        Stamps `credential_last_replaced_at`; does not touch
        `last_test_connection_*` (Task 003 owns those). A `connected`
        store also moves to `reconnect_needed` (and bumps the connection
        epoch) -- same rationale as `action_set_token`. Delegates to the
        shared store->credential-ordered `_mutate_token`.
        """
        return self._mutate_token(store, value, is_replace=True)

    def _mutate_token(self, store, value, is_replace):
        """Shared store->credential-ordered token mutation (CORE-R2, AR-047;
        review 4690639375 #3).

        The single credential set/replace path. Enforces the global **store ->
        credential** lock order and the frozen lifecycle matrix:

        1. validate the supplied value **before any write** (identical
           `ValidationError` message as before, for both set and replace);
        2. acquire the **conflicting store-row update lock** on the store row
           first (`store._lock_store_for_lifecycle`, `FOR NO KEY UPDATE`), and
           fresh-read `(state, generation)` under it -- so a concurrent admission
           holding `FOR SHARE` linearizes against this mutation and a stale gate
           read can never capture the newly-written token under the old epoch;
        3. if the fresh state is `disconnecting`, **refuse** (`UserError`) --
           without touching the credential, the mirrors, or the generation, and
           without writing any audit that could carry the token (disconnect is
           one-way; the operator replaces after it finalizes);
        4. only then create/update the credential row (normal ACL, **no
           `sudo()`**), under the held store lock;
        5. clear `credential_last_verified_at` (stale-evidence closure) and, for
           a replace, stamp `credential_last_replaced_at`;
        6. if the fresh state is `connected`, atomically move to
           `reconnect_needed` **and increment `connection_generation` exactly
           once** (the connected credential change invalidates both the state and
           the epoch); for any other allowed state, preserve the state and add no
           extra generation bump.

        The token is never logged, never persisted outside `access_token`, and
        never placed in an audit/exception message. This is the only credential
        set/replace path -- no second credential model or service is introduced.
        """
        # (1) value validation BEFORE any write (before the store lock).
        if not isinstance(value, str) or not value:
            raise ValidationError(
                "A non-empty credential value is required."
            )
        # (2) store-row conflicting update lock FIRST (store -> credential global
        # order), then the fresh state/generation read under the lock.
        locked_state, locked_generation = store._lock_store_for_lifecycle()
        # (3) refuse a credential change while a disconnect is in progress --
        # nothing is written (no credential, no mirror, no generation, no audit).
        if locked_state == 'disconnecting':
            raise UserError(
                'Cannot change the credential while a disconnect is in '
                'progress for this store.'
            )
        # (4) credential row create/update, under the held store lock, normal ACL.
        credential = self.search([('store_id', '=', store.id)], limit=1)
        if credential:
            credential.write({
                'access_token': value,
                'credential_state': 'present',
            })
        else:
            credential = self.create({
                'store_id': store.id,
                'access_token': value,
                'credential_state': 'present',
            })
        # (5)/(6) store mirrors + connected-state/epoch invalidation.
        store_vals = {
            'credential_present': True,
            'credential_last_verified_at': False,
        }
        if is_replace:
            store_vals['credential_last_replaced_at'] = fields.Datetime.now()
        if locked_state == 'connected':
            store_vals['state'] = 'reconnect_needed'
            store_vals['connection_generation'] = locked_generation + 1
        store.write(store_vals)
        return None

    @api.model
    def action_clear_token(self, store):
        """Empty the store's credential value, preserving history.

        Idempotent when no credential row exists yet: no error, no row
        created. The credential row itself and
        `credential_last_replaced_at` are never removed (MBQ-08). A
        `connected` or `reconnect_needed` store also moves to
        `disconnected`: with the credential gone, `store.state` must
        not still claim a live/recoverable connection --
        `action_disconnect()` may still write `disconnected` afterward,
        which remains fine and idempotent.
        """
        credential = self.search([('store_id', '=', store.id)], limit=1)
        if credential:
            credential.write({
                'access_token': False,
                'credential_state': 'absent',
            })
        store.write({
            'credential_present': False,
            'credential_last_verified_at': False,
            'credential_last_failure_reason': False,
        })
        if store.state in ('connected', 'reconnect_needed'):
            store.write({'state': 'disconnected'})
        return None

    @api.model
    def _get_access_token(self, store):
        """Internal-only accessor for the store's stored credential value.

        The only sanctioned `sudo()` in this module: scoped to reading
        the single credential row of `store`, for a caller already
        authorized to act on that store (DEC-004 -- this elevation
        never crosses store/record-rule boundaries). Never returns the
        value to logs or exceptions; never invoked by any Task 002
        shipped code path outside tests (its consumer is the future API
        client).
        """
        credential = self.sudo().search(
            [('store_id', '=', store.id)], limit=1
        )
        return credential.access_token if credential else False
