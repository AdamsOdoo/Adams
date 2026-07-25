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
        """Public/manual credential clear -- never bypasses two-phase quiescence
        (CORE-R2, AR-047; reviews 4690804619 #2 + 4690807427).

        Takes the store-row lifecycle lock FIRST (store -> credential global
        order) and fresh-reads the state under it, then routes by that state:

        - `disconnecting`: **refused** (`UserError`) -- a disconnect is already in
          progress and the controller clears the credential when it reaches
          `completed`/`timed_out`; a manual clear must not race it.
        - `connected` / `reconnect_needed`: an already-admitted call lease can
          outlive admission's brief `FOR SHARE`, so a live/recoverable store must
          **quiesce** before its credential is cleared. This delegates to the
          accepted two-phase `action_disconnect` request (`_request_disconnect_
          locked`, one epoch bump, `state -> disconnecting`) and clears **nothing**
          now -- the controller performs the actual clear at finalize. It does
          **not** manufacture a clear-before-quiescence (review 4690807427).
        - `setup_incomplete` / already `disconnected`: no active-business-call
          posture, so the credential is cleared **directly** under the held lock
          via the shared `_clear_token_under_store_lock` primitive.

        Idempotent when no credential row exists yet (direct-clear states): no
        error, no row created. The credential row itself and
        `credential_last_replaced_at` are never removed (MBQ-08). No token is ever
        logged/persisted; runs as the calling user (no `sudo()`), so the ACL layer
        stays live.
        """
        locked_state, locked_generation = store._lock_store_for_lifecycle()
        if locked_state == 'disconnecting':
            raise UserError(
                'Cannot clear the credential while a disconnect is in '
                'progress for this store; it is cleared automatically when '
                'the disconnect completes.'
            )
        if locked_state in ('connected', 'reconnect_needed'):
            # Route through the accepted two-phase disconnect -- clear nothing now.
            store._request_disconnect_locked(locked_state, locked_generation)
            return None
        # setup_incomplete / disconnected: safe to clear directly under the lock.
        self._clear_token_under_store_lock(store)
        return None

    @api.model
    def _clear_token_under_store_lock(self, store):
        """Controller-only credential clear primitive (CORE-R2, AR-047; review
        4690804619 #2).

        Empties the credential value + `credential_state` and the store's
        non-secret credential mirrors, preserving history (the credential row and
        `credential_last_replaced_at` are never removed, MBQ-08). It performs **no
        store-state transition and no epoch bump** and takes **no** lock of its own:
        the caller must already hold the store-row lock -- the quiescence controller
        holds the store `FOR UPDATE` at `_finalize_disconnect_completed` /
        `_finalize_disconnect_timed_out` (and writes `disconnected` itself), and the
        public `action_clear_token` holds `_lock_store_for_lifecycle` for its
        direct-clear states. This keeps the credential present until the controller
        reaches `completed`/`timed_out`, so no path clears before quiescence.
        Idempotent with no credential row. No token logging; no `sudo()`.
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
        return None

    @api.model
    def _lifecycle_credential_version(self, store, lock):
        """Return `(id, write_date)` of the store's credential row, or `None`.

        The credential-version signal for the CORE-R2 lifecycle-probe snapshot +
        post-network revalidation (review 4690804619 #1). `write_date` advances on
        every credential set/replace/clear (the credential service always writes
        the row), so an unchanged `(id, write_date)` pair proves the credential was
        not mutated between the probe snapshot and its revalidation.

        `lock=False` is the non-locking pre-network baseline used by
        `_admit_lifecycle` (a lock there would span the network call). `lock=True`
        takes the blocking `FOR NO KEY UPDATE` credential-row lock used by the
        store's post-network revalidation -- run **after** the store-row lock, so
        the global `store -> credential` order holds. Raw SQL (never `sudo()`) with
        the sanctioned `flush_recordset` / `invalidate_recordset` discipline so the
        read reflects committed state, not a stale ORM cache. Reads only `id` and
        `write_date` -- never the token.
        """
        credential = self.search([('store_id', '=', store.id)], limit=1)
        if not credential:
            return None
        credential.flush_recordset()
        if lock:
            self.env.cr.execute(
                "SELECT id, write_date FROM shopify_connector_store_credential "
                "WHERE id = %s FOR NO KEY UPDATE",
                (credential.id,),
            )
        else:
            self.env.cr.execute(
                "SELECT id, write_date FROM shopify_connector_store_credential "
                "WHERE id = %s",
                (credential.id,),
            )
        row = self.env.cr.fetchone()
        credential.invalidate_recordset()
        return row

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
