import logging
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

#: The two credential acquisition modes this connector supports.
#:
#: `offline_access_token` is the original Task 002 shape: one long-lived value
#: the merchant already holds, pasted once. It remains fully supported and is
#: the mode every pre-existing row is migrated onto.
#:
#: `dev_dashboard_client_credentials` is the mode a merchant creating a Shopify
#: app in 2026 actually has. Shopify's Dev Dashboard does not display a
#: permanent Admin API token for copying; the app exchanges its Client ID and
#: Client secret for a 24-hour access token programmatically. Verified against
#: https://shopify.dev/docs/apps/build/dev-dashboard/get-api-access-tokens
#: (accessed 2026-07-29), which states the grant "only works when the app and
#: the store belong to the same Shopify organization" and that `expires_in` is
#: "Always 86399 (24 hours)".
AUTH_MODE_OFFLINE = 'offline_access_token'
AUTH_MODE_CLIENT_CREDENTIALS = 'dev_dashboard_client_credentials'

#: Refresh this many seconds BEFORE the recorded expiry. Shopify's own example
#: refreshes 60s early; this connector uses a far wider margin because an Odoo
#: job can be admitted, queued and drained minutes after the token was checked,
#: and a token that expires mid-drain becomes an auth failure on a mutation
#: rather than a clean refresh.
TOKEN_REFRESH_MARGIN_SECONDS = 900

#: A token whose recorded lifetime is shorter than the margin would refresh on
#: every single call. Clamp the effective margin so a short-lived token still
#: gets used rather than thrashing.
TOKEN_MIN_USABLE_SECONDS = 30

#: Refresh serialization (§11.8). A PostgreSQL advisory lock keyed on this
#: connector-private class id plus the store id, so exactly one worker performs
#: the exchange for a store and the others reuse its result instead of creating
#: a stampede. It is NOT the store row lock: it blocks only other refreshers,
#: never a business admission or a lifecycle transition.
TOKEN_REFRESH_ADVISORY_CLASSID = 0x5348_5046  # 'SHPF'
TOKEN_REFRESH_WAIT_ATTEMPTS = 40
TOKEN_REFRESH_WAIT_SECONDS = 0.25


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
    of them here, and no part of this module may claim otherwise. The
    same is true, unchanged and equally explicitly, of `client_secret`
    and of every cached access token: nothing here is encrypted at rest
    and no copy states otherwise.

    WAVE 5 -- THE SECOND CREDENTIAL MODE.

    Task 002 deliberately shipped one credential shape and named this
    model as "the seam a future, separately gated task can extend (via
    `selection_add` plus new fields) once ChatGPT decides the MBQ-05
    acquisition-path direction". That decision has now been taken for a
    bounded UAT/private-deployment scope, and this is that extension.

    `auth_mode` is the explicit mode. It is a NEW column rather than a
    reinterpretation of `token_variant`, because reusing the old column
    would make an existing offline token's meaning depend on when its row
    was written -- and the one thing a credential migration must never do
    is reinterpret a stored token as something else. Every pre-existing
    row is migrated to `offline_access_token` and behaves exactly as
    before.

    The ephemeral access token of the client-credentials mode does NOT
    live on this row. It lives in `shopify.connector.store.access.token`,
    and that separation is load-bearing rather than tidy: CORE-R2's
    lifecycle probe treats a change to this row's `write_date` or token
    value as proof that the credential IDENTITY changed and discards any
    in-flight probe result. A 24-hour token rotating on schedule is not
    an identity change, and writing it here would make every routine
    refresh look like a credential replacement.

    The sanctioned `sudo()` calls in this module are `_get_access_token`
    and the token-cache accessors beside it, all scoped to the one store
    already being operated on (DEC-004).
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
    # The explicit acquisition mode. Required with a default, so a row that
    # existed before Wave 5 reads as the offline mode it actually is even if a
    # migration has not yet run against it.
    auth_mode = fields.Selection(
        selection=[
            (AUTH_MODE_OFFLINE, 'Existing Admin API access token'),
            (
                AUTH_MODE_CLIENT_CREDENTIALS,
                'Dev Dashboard app (Client ID and secret)',
            ),
        ],
        required=True,
        default=AUTH_MODE_OFFLINE,
    )
    # Not itself a secret -- Shopify shows it in the Dev Dashboard -- but kept
    # behind the same Administrator group as everything else on this row, so a
    # single ACL decision governs the whole credential.
    client_id = fields.Char(
        copy=False,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    # Write-only in exactly the sense `access_token` is: field-level `groups=`
    # on top of the Administrator-only ACL row, never returned by any RPC
    # payload this connector builds, never logged, never placed in an exception.
    client_secret = fields.Char(
        copy=False,
        groups='shopify_connector_core.group_shopify_connector_admin',
    )
    # Non-secret mirrors, safe to render. They exist so the setup and Store
    # Settings surfaces can tell a merchant what state their authentication is
    # in without any code path needing to read a secret to answer.
    #
    # Deliberately NOT here: the token's obtained/expiry stamps. Those change
    # on every routine 24-hour rotation, the rotation runs in an independent
    # side transaction, and a side-transaction write to THIS row breaks the
    # probe revalidation under REPEATABLE READ (see `_write_token_cache`).
    # They live on the cache row and are read through `_token_cache_status`.
    client_credentials_present = fields.Boolean(readonly=True, default=False)
    # Written only by MAIN-transaction writers (`_apply_probe_failure`, the
    # credential mutations) -- never by the refresh side transaction.
    token_last_failure_reason = fields.Char(readonly=True)
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

    def _mutate_token(self, store, value, is_replace, auth_mode=None,
                      client_id=None):
        """Shared store->credential-ordered token mutation (CORE-R2, AR-047;
        review 4690639375 #3).

        WAVE 5. `auth_mode`/`client_id` carry the client-credentials mode
        through this one path rather than around it, so the newer mode inherits
        every invalidation rule the offline mode already had instead of growing
        a second, subtly different lifecycle. When `auth_mode` is
        `dev_dashboard_client_credentials`, `value` is the Client SECRET and is
        written to `client_secret`; `access_token` is cleared, because a stored
        offline token must never survive a switch and be silently reused as if
        it belonged to the new app. Any cached 24-hour token is discarded for
        the same reason: it was minted by the credential being replaced.

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
        if auth_mode == AUTH_MODE_CLIENT_CREDENTIALS:
            values = {
                'auth_mode': AUTH_MODE_CLIENT_CREDENTIALS,
                'client_id': client_id,
                'client_secret': value,
                # Never carried across a mode switch. A leftover offline token
                # would otherwise remain readable and, worse, usable.
                'access_token': False,
                'client_credentials_present': True,
                'credential_state': 'present',
                'token_last_failure_reason': False,
            }
        else:
            values = {
                'auth_mode': AUTH_MODE_OFFLINE,
                'access_token': value,
                'client_id': False,
                'client_secret': False,
                'client_credentials_present': False,
                'credential_state': 'present',
                'token_last_failure_reason': False,
            }
        credential = self.search([('store_id', '=', store.id)], limit=1)
        if credential:
            credential.write(values)
        else:
            credential = self.create(dict(values, store_id=store.id))
        # Any cached 24-hour token belonged to the credential just replaced.
        self._discard_token_cache(store)
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
                # Wave 5: the client-credentials pair is a credential too, and
                # a clear that left it behind would leave the store able to
                # mint a new token for a credential the operator just removed.
                'client_id': False,
                'client_secret': False,
                'client_credentials_present': False,
                'credential_state': 'absent',
            })
        self._discard_token_cache(store)
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
        """Internal-only accessor for the token this store authenticates with.

        The only sanctioned `sudo()` in this module: scoped to reading
        the single credential row of `store`, for a caller already
        authorized to act on that store (DEC-004 -- this elevation
        never crosses store/record-rule boundaries). Never returns the
        value to logs or exceptions.

        Mode-aware since Wave 5, and deliberately still a pure READ:

        * `offline_access_token` -- the stored long-lived value, exactly as
          before. Byte-for-byte the pre-Wave-5 behaviour.
        * `dev_dashboard_client_credentials` -- the currently cached
          24-hour token. This method does **not** obtain or refresh one.
          `_ensure_access_token` does that, and it is called by the API
          client BEFORE any admission lock is taken, because obtaining a
          token is a network call and no lock in this connector may span
          one. A caller that reaches here with an empty or expired cache
          gets `False` and the accepted `REASON_TOKEN_INVALID` auth
          failure, which is the correct fail-closed outcome.
        """
        credential = self.sudo().search(
            [('store_id', '=', store.id)], limit=1
        )
        if not credential:
            return False
        if credential.auth_mode == AUTH_MODE_CLIENT_CREDENTIALS:
            return self._read_cached_token_committed(store)
        return credential.access_token

    @api.model
    def _read_cached_token_committed(self, store):
        """The store's currently valid cached token, from COMMITTED state.

        Read through a fresh independent snapshot on purpose. Odoo cursors run
        REPEATABLE READ, and the refresh that just minted this token committed
        in its own side transaction -- so a caller's main transaction, whose
        snapshot opened before that commit, cannot see the new row at all. An
        ordinary ORM read here would return "no token" immediately after a
        successful refresh, every time, in every fresh transaction.

        Raw SQL for the same reason `_lifecycle_credential_version` uses it:
        two non-secret columns plus the token, selected by the store id the
        caller was already authorized against. The row travels to exactly one
        place -- the in-memory return value -- and is never logged.
        """
        self.env['shopify.connector.store.access.token'].flush_model()
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                "SELECT access_token, expires_at "
                "FROM shopify_connector_store_access_token "
                "WHERE store_id = %s",
                (store.id,),
            )
            row = side_cr.fetchone()
        finally:
            side_cr.rollback()
            side_cr.close()
        if not row or not row[0] or not row[1]:
            return False
        if (row[1] - fields.Datetime.now()).total_seconds() <= 0:
            return False
        return row[0]

    @api.model
    def _token_cache_status(self, store):
        """Non-secret cache facts for surfaces: obtained/expiry stamps only."""
        cached = self._cached_token_row(store)
        if not cached:
            return {'obtained_at': False, 'expires_at': False}
        return {
            'obtained_at': cached.obtained_at,
            'expires_at': cached.expires_at,
        }

    @api.model
    def _committed_token_remaining_seconds(self, store):
        """Seconds of validity left on the COMMITTED cached token, or 0.

        Same fresh-snapshot read as `_read_cached_token_committed`, for the
        same REPEATABLE READ reason -- a decision about whether to refresh must
        see the refresh another worker committed a moment ago, or every worker
        that raced the leader re-decides "expired" from its own stale snapshot.
        """
        self.env['shopify.connector.store.access.token'].flush_model()
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                "SELECT access_token, expires_at "
                "FROM shopify_connector_store_access_token "
                "WHERE store_id = %s",
                (store.id,),
            )
            row = side_cr.fetchone()
        finally:
            side_cr.rollback()
            side_cr.close()
        if not row or not row[0] or not row[1]:
            return 0
        return max(
            0, (row[1] - fields.Datetime.now()).total_seconds(),
        )

    # ------------------------------------------------------------------
    # Wave 5: the client-credentials mode
    # ------------------------------------------------------------------

    @api.model
    def _credential_for(self, store):
        """The store's credential row, elevated and store-scoped, or empty."""
        return self.sudo().search([('store_id', '=', store.id)], limit=1)

    @api.model
    def _auth_mode_of(self, store):
        """The store's acquisition mode, defaulting to the offline shape.

        A store with no credential row yet is reported as the offline mode
        rather than as an error: every surface that asks this question is
        deciding what to SHOW, and a store nobody has configured has not
        chosen the newer mode.
        """
        credential = self._credential_for(store)
        return credential.auth_mode if credential else AUTH_MODE_OFFLINE

    @api.model
    def _cached_token_row(self, store):
        """This store's cached access-token row, elevated, or empty."""
        return self.env[
            'shopify.connector.store.access.token'
        ].sudo().search([('store_id', '=', store.id)], limit=1)

    @api.model
    def _token_is_expired(self, cached, margin=0):
        """True when `cached` is absent, undated, or within `margin` of expiry.

        `margin=0` asks "is it dead", which is the question a read asks.
        `margin=TOKEN_REFRESH_MARGIN_SECONDS` asks "should it be replaced
        now", which is the question the refresher asks. Keeping both in one
        predicate is what stops the two from drifting apart.
        """
        if not cached or not cached.access_token or not cached.expires_at:
            return True
        remaining = (
            cached.expires_at - fields.Datetime.now()
        ).total_seconds()
        return remaining <= margin

    @api.model
    def action_set_client_credentials(self, store, client_id, client_secret):
        """Record the Dev Dashboard app's Client ID and secret for this store.

        Routed through the same `_mutate_token` lifecycle discipline the
        offline path uses -- the store-row lock first, the disconnecting
        refusal, the cleared verification stamp, the `connected` ->
        `reconnect_needed` transition and the single generation bump -- because
        replacing the credentials an app authenticates with is exactly as much
        of a credential change as replacing a token, and the invalidation rules
        must not depend on which mode a merchant chose.

        Setting client credentials also DISCARDS any cached access token: the
        cache was minted by the previous secret and vouches for nothing about
        the new one.
        """
        if not isinstance(client_id, str) or not client_id.strip():
            raise ValidationError(_('A non-empty Client ID is required.'))
        if not isinstance(client_secret, str) or not client_secret.strip():
            raise ValidationError(_('A non-empty Client secret is required.'))
        return self._mutate_token(
            store,
            client_secret.strip(),
            is_replace=True,
            auth_mode=AUTH_MODE_CLIENT_CREDENTIALS,
            client_id=client_id.strip(),
        )

    @api.model
    def _write_token_cache(self, store, credential, access_token, expires_at,
                           granted_scope):
        """Persist one freshly-obtained access token. Elevated, store-scoped.

        WRITES THE CACHE ROW ONLY -- never the credential row. That rule is
        structural, not stylistic. This method runs inside the refresh's
        independent side transaction, and Odoo cursors run REPEATABLE READ:
        the calling request's own transaction opened its snapshot before this
        side transaction commits. If this wrote the credential row, then

        * the probe's post-network revalidation, which takes the credential
          row's `FOR NO KEY UPDATE` lock in the MAIN transaction, would hit a
          PostgreSQL serialization failure the moment it touched a row a
          later-committed transaction had updated, and

        * the credential row's `write_date` would advance on every routine
          24-hour rotation, which the revalidation's version comparison reads
          as "the credential changed underneath this probe" -- a false
          supersession, once a day, forever.

        So the credential row stays byte-for-byte still, and every mirror a
        surface needs (`obtained_at`, `expires_at`, the scope string) lives on
        the cache row, which the main transaction never locks or writes inside
        the same request.
        """
        Cache = self.env['shopify.connector.store.access.token'].sudo()
        existing = Cache.search([('store_id', '=', store.id)], limit=1)
        values = {
            'store_id': store.id,
            'credential_id': credential.id,
            'access_token': access_token,
            'obtained_at': fields.Datetime.now(),
            'expires_at': expires_at,
            'granted_scope_snapshot': granted_scope or False,
        }
        if existing:
            existing.write(values)
        else:
            Cache.create(values)
        return True

    @api.model
    def _discard_token_cache(self, store):
        """Drop this store's cached access token.

        Called only from MAIN-transaction credential mutations (set, replace,
        clear), which already hold the store lifecycle lock -- never from the
        refresh side transaction.
        """
        cached = self._cached_token_row(store)
        if cached:
            cached.unlink()
        return True

    @api.model
    def _ensure_access_token(self, store):
        """Make sure this store has a usable access token, obtaining one if not.

        **Called before any lock, never inside one.** Obtaining a token is an
        HTTPS request, and this connector's whole admission design rests on no
        lock spanning a network call. Every caller -- `execute`,
        `execute_business` and the lifecycle probe -- invokes this first and
        then admits normally, so by the time a store row is locked the token is
        already in hand.

        A no-op for `offline_access_token`: that value does not expire and
        nothing may re-fetch it.

        For `dev_dashboard_client_credentials`:

        1. return immediately when the cache is comfortably valid (the common
           case -- once per 24 hours a store actually refreshes);
        2. otherwise take a per-store PostgreSQL **advisory** lock in an
           independent transaction, so exactly one worker performs the exchange
           (§11.8) and the rest reuse its result rather than each minting a
           token. The lock is connector-private and store-scoped: it blocks
           other refreshers only, never an admission and never a lifecycle
           transition;
        3. the worker that gets the lock re-reads the cache under it -- the
           double-check that makes a queued waiter free rather than a second
           exchange -- and only then exchanges;
        4. a worker that does NOT get the lock waits, bounded, for the leader's
           committed result. If none arrives it raises the accepted TEMPORARY
           taxonomy, which the job layer already treats as retryable. It never
           starts a competing exchange.

        Returns True when a usable token exists afterwards. Raises the accepted
        `ShopifyClientError` taxonomy otherwise -- never a bare exception, and
        never one carrying a secret.
        """
        credential = self._credential_for(store)
        if not credential or credential.auth_mode != AUTH_MODE_CLIENT_CREDENTIALS:
            return True
        remaining = self._committed_token_remaining_seconds(store)
        if remaining > TOKEN_REFRESH_MARGIN_SECONDS:
            return True
        # A token that is still alive but inside the refresh margin is usable
        # RIGHT NOW. Refresh it, but never fail the call because the refresh
        # could not run -- that would turn a healthy store into an outage for
        # the last 15 minutes of every token's life.
        usable_now = remaining > TOKEN_MIN_USABLE_SECONDS
        try:
            self._refresh_access_token(store, credential)
        except Exception:
            if usable_now:
                _logger.warning(
                    'Shopify access-token refresh failed for store %s; the '
                    'current token is still valid and was used.', store.id,
                )
                return True
            raise
        return True

    @api.model
    def _refresh_access_token(self, store, credential):
        """Serialize on the advisory lock, then exchange exactly once."""
        # Imported here rather than at module import time: the API client is an
        # AbstractModel in this same addon and the error taxonomy lives beside
        # it, so a module-level import would be a circular one.
        from .shopify_connector_api_client import (
            ERROR_AUTH, ERROR_TEMPORARY, REASON_TEMPORARY,
            REASON_TOKEN_INVALID, ShopifyClientError,
        )
        self.env.flush_all()
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                'SELECT pg_try_advisory_xact_lock(%s, %s)',
                (TOKEN_REFRESH_ADVISORY_CLASSID, store.id),
            )
            acquired = side_cr.fetchone()[0]
            if not acquired:
                side_cr.rollback()
                return self._await_peer_refresh(store)
            side_env = api.Environment(side_cr, self.env.uid, self.env.context)
            side_self = side_env[self._name]
            side_store = side_env['shopify.connector.store'].browse(store.id)
            side_credential = side_self._credential_for(side_store)
            if not side_credential:
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            # Double-check UNDER the lock. A worker that queued behind the
            # leader arrives here after the leader committed, finds a fresh
            # token, and performs no second exchange.
            if not side_self._token_is_expired(
                side_self._cached_token_row(side_store),
                TOKEN_REFRESH_MARGIN_SECONDS,
            ):
                side_cr.rollback()
                return True
            client_id = side_credential.client_id
            client_secret = side_credential.client_secret
            if not client_id or not client_secret:
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            # A failed exchange writes NOTHING here -- not the credential row,
            # not the cache. The raised taxonomy is the failure evidence, and
            # the CALLER's transaction owns recording it: the connection probe
            # routes it through `_apply_probe_failure` (store mirrors,
            # `credential_state`, reconnect), and a business call routes it
            # through the dispatcher's auth-failure family. A side-transaction
            # write to the credential row would advance its `write_date` and
            # collide with the main transaction's later `FOR NO KEY UPDATE`
            # revalidation lock under REPEATABLE READ -- a serialization
            # failure manufactured out of a failure report.
            token, expires_at, granted_scope = side_env[
                'shopify.connector.api.client'
            ]._exchange_client_credentials(
                side_store, client_id, client_secret,
            )
            side_self._write_token_cache(
                side_store, side_credential, token, expires_at, granted_scope,
            )
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
            # The main environment must not keep serving what it read before
            # the side transaction ran -- on the SUCCESS path that is the
            # pre-refresh token cache, and on the FAILURE path it is the
            # pre-failure `credential_state`/failure-reason mirrors the side
            # transaction just committed. Both re-read correctly only after an
            # invalidation, so it is unconditional.
            self.env['shopify.connector.store.access.token'].invalidate_model()
            self.invalidate_model()
        return True

    @api.model
    def _await_peer_refresh(self, store):
        """Wait, bounded, for another worker's committed token.

        Polls on its own short-lived transactions so it observes the leader's
        COMMIT rather than a snapshot taken before it. Never exchanges, never
        holds a lock, and gives up with the accepted retryable taxonomy instead
        of blocking a worker indefinitely.
        """
        from .shopify_connector_api_client import (
            ERROR_TEMPORARY, REASON_TEMPORARY, ShopifyClientError,
        )
        for _attempt in range(TOKEN_REFRESH_WAIT_ATTEMPTS):
            time.sleep(TOKEN_REFRESH_WAIT_SECONDS)
            poll_cr = self.env.registry.cursor()
            try:
                poll_env = api.Environment(
                    poll_cr, self.env.uid, self.env.context,
                )
                poll_self = poll_env[self._name]
                poll_store = poll_env['shopify.connector.store'].browse(store.id)
                fresh = not poll_self._token_is_expired(
                    poll_self._cached_token_row(poll_store),
                    TOKEN_MIN_USABLE_SECONDS,
                )
            finally:
                poll_cr.rollback()
                poll_cr.close()
            if fresh:
                self.env['shopify.connector.store.access.token'].invalidate_model()
                return True
        raise ShopifyClientError(
            error_class=ERROR_TEMPORARY,
            reason=REASON_TEMPORARY,
            technical_detail='access token refresh did not complete in time',
        )

    @api.model
    def _lifecycle_credential_identity(self, store):
        """The value CORE-R2's probe revalidation compares to prove IDENTITY.

        `_lifecycle_probe_superseded` discards a network result when the
        credential changed underneath it. Before Wave 5 the credential *was*
        the token, so comparing token values answered that question exactly.

        Under the client-credentials mode it no longer does. The access token
        rotates every 24 hours by design; a rotation is not a credential change
        and must not discard an in-flight probe. What actually identifies the
        credential in that mode is the app's own `(client_id, client_secret)`
        pair, so that is what is compared. The offline mode compares the token,
        unchanged.

        The returned value is held in memory for the duration of one probe and
        is never logged, persisted, or placed in an exception -- the same
        contract the token snapshot has always had.
        """
        credential = self._credential_for(store)
        if not credential:
            return False
        if credential.auth_mode == AUTH_MODE_CLIENT_CREDENTIALS:
            return (credential.client_id or '', credential.client_secret or '')
        return credential.access_token
