import logging
import time

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

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

#: Declared once, here, and imported by the token-cache model so the cache's
#: `auth_mode` column can never drift from the credential's.
AUTH_MODE_SELECTION = [
    (AUTH_MODE_OFFLINE, 'Existing Admin API access token'),
    (AUTH_MODE_CLIENT_CREDENTIALS, 'Dev Dashboard app (Client ID and secret)'),
]

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
#:
#: It is also the primitive that makes an in-flight exchange VISIBLE to the
#: disconnect quiescence controller (`_token_exchange_in_flight`). A call-lease
#: row was considered and rejected for that job: under direction C an
#: expired-but-unreleased lease is treated as live forever and is never
#: reclaimed, so a worker that died mid-exchange would strand the disconnect
#: permanently and starve every later refresher. A transaction-scoped advisory
#: lock is released by PostgreSQL when the backend goes away, which is the
#: crash-recovery behaviour this path needs and a lease row cannot provide.
#:
#: Every acquisition anywhere is `pg_try_advisory_xact_lock` -- never the
#: blocking form. That is what makes the lock deadlock-free against the store
#: row lock: the refresh takes the advisory lock and then waits for the store
#: row, the controller holds the store row and only ever *tries* the advisory
#: lock, and a try-lock cannot be an edge in a wait-for cycle.
TOKEN_REFRESH_ADVISORY_CLASSID = 0x5348_5046  # 'SHPF'
TOKEN_REFRESH_WAIT_ATTEMPTS = 40
TOKEN_REFRESH_WAIT_SECONDS = 0.25

#: Which store states may reach the Shopify token endpoint, by the purpose of
#: the call that needs a token (§7 of the Batch 1 correction). Obtaining a token
#: IS a Shopify network call, so it obeys lifecycle control exactly like every
#: other one instead of running before the gate that would have refused it.
#:
#: `business` is the routine/background family: jobs, drains and Layer 2. It is
#: `connected` only, matching the four business gates
#: (`shopify.connector.job._check_store_state`, the dispatcher's pre-dispatch
#: check, `_admit`'s `FOR SHARE` state check and `_admit_mutation`'s snapshot).
#:
#: `setup` is the explicit operator-driven family: the guided setup's Test
#: Connection and the reconnect probe. Its matrix is the UNION of the
#: `LIFECYCLE_PURPOSE_STATES` purposes that actually need a token, because a
#: merchant configuring a brand-new store or recovering a broken one must be
#: able to authenticate -- that is the whole point of the button they pressed.
#:
#: `disconnecting` and `disconnected` appear in NEITHER family bar the one
#: purpose Shopify-side reconnect evidence requires (`reconnect_probe`, which
#: `LIFECYCLE_PURPOSE_STATES` already admits for `disconnected`). No path may
#: start an exchange for a `disconnecting` store: a disconnect is one-way and
#: is in the middle of clearing the very credential the exchange would use.
TOKEN_EXCHANGE_PURPOSE_STATES = {
    'business': ('connected',),
    'setup': ('setup_incomplete', 'connected', 'reconnect_needed'),
    'reconnect': ('reconnect_needed', 'disconnected'),
}

#: The closed credential-mutation surface (§9.1 of the Batch 1 correction).
#:
#: Before this, `shopify.connector.store.credential` had no `create`/`write`/
#: `unlink` override at all. The ACL row grants a Connector Administrator
#: `read`/`write`/`create`, so an Administrator -- or anything running as one,
#: including a data import or a plain RPC `write` from a script -- could set or
#: replace a credential value directly and skip EVERY invalidation the service
#: performs: the token-cache discard, the identity-epoch bump, the cleared
#: verification stamp, and the `connected` -> `reconnect_needed` demotion with
#: its generation bump. A rotated secret with a stale `credential_last_verified_
#: at` and a live cached token is exactly the state this correction exists to
#: make impossible, so the direct route has to close too.
#:
#: The guard is modelled on `shopify.connector.mutation.attempt` -- the strongest
#: pattern in this repository -- with ONE deliberate difference: it does not
#: require `env.su`. `_mutate_token` runs as the CALLING user on purpose, so the
#: Administrator-only ACL is still evaluated by the ORM for every credential
#: change (a non-admin gets `AccessError` from Odoo itself, not from here).
#: Requiring `sudo()` would have replaced that live ACL check with a bypass of
#: it, which is a weaker posture, not a stronger one.
#:
#: What makes the surface unforgeable is `CREDENTIAL_SERVICE_SENTINEL`: a
#: module-level `object()` compared with `is`. Odoo's RPC context arrives as
#: JSON, so no remote caller can construct it by any combination of forged
#: context values. The surface NAME is checked as well, so a sanctioned method
#: cannot borrow another method's authorisation.
CREDENTIAL_WRITE_CONTEXT = 'shopify_credential_write_surface'
CREDENTIAL_SERVICE_SENTINEL_CONTEXT = 'shopify_credential_service_sentinel'
CREDENTIAL_SERVICE_SENTINEL = object()
#: Every method allowed to create or change a credential row, by name. Pinned
#: exactly by `test_credential_service.py`, so adding a fourth writer is a
#: decision somebody makes on purpose rather than an implementation detail.
CREDENTIAL_CREATE_SURFACES = frozenset(('_mutate_token',))
CREDENTIAL_WRITE_SURFACES = frozenset((
    '_mutate_token',
    '_clear_token_under_store_lock',
    # The connection probe's authentication-failure record. It writes only
    # `credential_state`/`token_last_failure_reason` -- never a secret, never
    # the epoch -- and it is the reason this set has three members rather than
    # two: `_apply_probe_failure` is a sanctioned lifecycle writer that must not
    # have to route a failure report through the value-mutation path.
    '_apply_probe_failure',
))


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
        selection=AUTH_MODE_SELECTION,
        required=True,
        default=AUTH_MODE_OFFLINE,
    )
    # The credential's IDENTITY VERSION, and the load-bearing column of the
    # Batch 1 obsolete-token correction.
    #
    # WHY NEITHER THE ROW ID NOR `write_date` IS ENOUGH. A rotation updates this
    # row in place, so the id is unchanged and a cache row pointing at it still
    # looks current -- that is precisely how a token minted from the previous
    # secret survived. `write_date` is no better: PostgreSQL fixes
    # `transaction_timestamp()` for a whole transaction, so a replace that lands
    # in the same transaction as the read it must invalidate carries an
    # identical stamp, and Odoo will not advance it at all for a write whose
    # values match. A counter the service bumps EXACTLY ONCE per sanctioned
    # mutation has neither weakness.
    #
    # Bumped only by `_bump_credential_epoch`, only under the store lifecycle
    # lock, always in the same transaction as the mutation it describes. Never
    # written by the refresh side transaction, never caller input (the ORM guard
    # below refuses it), and non-secret -- it is safe in a snapshot, a log or an
    # exception, which is why the probe's identity comparison now uses it
    # instead of holding a client secret in memory.
    credential_epoch = fields.Integer(
        required=True, default=0, readonly=True,
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

    # ------------------------------------------------------------------
    # The closed credential-mutation surface (§9.1)
    # ------------------------------------------------------------------

    @api.model
    def _credential_surface(self, name):
        """The only way to reach `create`/`write` on this model.

        Returns `self` re-bound with the surface name and the unforgeable
        service sentinel in context. Deliberately **not** `sudo()`: see
        `CREDENTIAL_WRITE_CONTEXT`. An unknown name is refused here rather than
        silently granted, so the surface list is the authorisation.
        """
        if (
            name not in CREDENTIAL_CREATE_SURFACES
            and name not in CREDENTIAL_WRITE_SURFACES
        ):
            raise AccessError(_('Unknown credential write surface.'))
        return self.with_context(**{
            CREDENTIAL_WRITE_CONTEXT: name,
            CREDENTIAL_SERVICE_SENTINEL_CONTEXT: CREDENTIAL_SERVICE_SENTINEL,
        })

    @api.model
    def _credential_surface_is_open(self, surfaces):
        """True only inside a sanctioned surface named in `surfaces`."""
        context = self.env.context
        return (
            context.get(CREDENTIAL_SERVICE_SENTINEL_CONTEXT)
            is CREDENTIAL_SERVICE_SENTINEL
            and context.get(CREDENTIAL_WRITE_CONTEXT) in surfaces
        )

    @api.model_create_multi
    def create(self, vals_list):
        """Credential rows exist only where the service puts them.

        A direct `create` -- Administrator RPC, a data import, a script -- would
        establish a credential without the store mirrors, without the identity
        epoch's meaning, and without the token-cache discard, so it is refused
        outright. `_mutate_token` is the one creator.
        """
        if not self._credential_surface_is_open(CREDENTIAL_CREATE_SURFACES):
            raise AccessError(_(
                'Shopify credentials can only be created through the '
                'connector credential service, which invalidates the cached '
                'token, the recorded verification and the connection state '
                'at the same time. Use Stores & Onboarding or Sync Rules.'
            ))
        return super().create(vals_list)

    def write(self, vals):
        """Every credential change routes through a sanctioned service method.

        There is no partial allowance and no "safe field" list. Every column on
        this row is either a secret, the identity the connector authenticates
        with, or a mirror of one of those two -- so a write that skipped the
        service would leave the store's cached token, verification evidence and
        connection generation describing a credential that no longer exists.
        """
        if not self._credential_surface_is_open(CREDENTIAL_WRITE_SURFACES):
            raise AccessError(_(
                'Shopify credentials can only be changed through the '
                'connector credential service, which invalidates the cached '
                'token, the recorded verification and the connection state '
                'at the same time. Use Stores & Onboarding or Sync Rules.'
            ))
        return super().write(vals)

    def unlink(self):
        """Credential history is never deleted (MBQ-08).

        `action_clear_token` empties the row and leaves it in place, so
        `credential_last_replaced_at` and the audit trail survive. Deletion
        would also silently cascade the token cache away, which is the one
        removal that must be a decision rather than a side effect.
        """
        raise AccessError(_(
            'Shopify credential records are never deleted. Clear the '
            'credential instead; the record and its history are retained.'
        ))

    @api.model
    def _next_credential_epoch(self, credential):
        """The identity version the mutation about to happen must write.

        Returned rather than written, deliberately: the caller folds it into the
        SAME `write()`/`create()` as the values it describes, so "the epoch
        changes exactly once, in the same transaction as the mutation" is a
        property of one statement instead of an ordering convention between two.
        A second write would also be a second chance to forget one.

        The caller must already hold the store lifecycle lock -- every sanctioned
        mutation takes it first -- which is what makes the increment
        linearizable per store rather than merely usually-correct.
        """
        return (credential.credential_epoch or 0) + 1 if credential else 1

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
        # "Was there a credential here to replace?" A row that exists but is
        # `absent` is the shape `action_clear_token` leaves behind (MBQ-08 keeps
        # the row and its history); it holds no credential, so setting one on top
        # of it is a first set, not a replacement.
        had_existing_credential = bool(
            credential and credential.credential_state != 'absent'
        )
        # (4a) The identity epoch advances in the SAME statement as the values it
        # describes. Every mode -- offline set, offline replace, client-credential
        # set, client-credential replace, and the mode switch between them -- goes
        # through this one place, so none of them can grow a path that mutates a
        # credential without superseding the identity a cached token was minted
        # from. `_refresh_access_token` compares exactly this number after its
        # network exchange returns.
        values['credential_epoch'] = self._next_credential_epoch(credential)
        surface = self._credential_surface('_mutate_token')
        if credential:
            surface.browse(credential.id).write(values)
        else:
            credential = surface.create(dict(values, store_id=store.id))
        # Any cached 24-hour token belonged to the credential just replaced.
        # Belt AND braces: the epoch bump above already makes any surviving row
        # unreadable, and this removes it outright.
        self._discard_token_cache(store)
        # (5)/(6) store mirrors + connected-state/epoch invalidation.
        store_vals = {
            'credential_present': True,
            'credential_last_verified_at': False,
        }
        # `credential_last_replaced_at` means "an existing credential was
        # replaced". Stamping it when the store had no credential row -- or an
        # empty one, the shape `action_clear_token` leaves behind -- reports a
        # replacement that never happened, and the setup surface renders that
        # stamp to a merchant. A first-ever set is not a replacement, whichever
        # entry point performed it.
        if is_replace and had_existing_credential:
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
            self._credential_surface(
                '_clear_token_under_store_lock',
            ).browse(credential.id).write({
                'access_token': False,
                # Wave 5: the client-credentials pair is a credential too, and
                # a clear that left it behind would leave the store able to
                # mint a new token for a credential the operator just removed.
                'client_id': False,
                'client_secret': False,
                'client_credentials_present': False,
                'credential_state': 'absent',
                # A clear supersedes the identity as decisively as a replace
                # does. Without this bump a refresh that read the pair before
                # the clear could still prove its provenance afterwards, which
                # is the `cache absent + clear` half of the reproduced defect.
                'credential_epoch': self._next_credential_epoch(credential),
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

    #: The provenance predicate, written ONCE and shared by every committed
    #: cache read (§6.9, §9.4). Two readers with two hand-written predicates is
    #: how "the token is checked" becomes "the token is checked on one of the two
    #: paths", so both callers below select through this same string.
    #:
    #: Every clause is a refusal the correction requires:
    #:  * `t.credential_epoch = c.credential_epoch` -- stale provenance. A token
    #:    minted from a rotated, cleared or mode-switched identity fails here.
    #:  * `c.credential_state = 'present'` -- absent or `invalid` credential.
    #:  * `c.auth_mode = %(mode)s AND t.auth_mode = c.auth_mode` -- wrong mode,
    #:    in both directions: the store must still be on the client-credentials
    #:    mode AND the token must have been minted under it.
    #:  * the `client_id`/`client_secret` emptiness tests -- a credential whose
    #:    pair has been emptied cannot vouch for a token, even if the row itself
    #:    still says `present`.
    #:  * `t.sec3_scope_quarantined = FALSE` -- a quarantined row never
    #:    authenticates. The SEC-3 record rules already hide it from ORM readers;
    #:    this is raw SQL, so the rule does not apply and the clause is what
    #:    makes the guarantee hold on this path too.
    #:  * `c.store_id = t.store_id`, `s.company_id = t.company_id`,
    #:    `c.company_id = t.company_id` -- cross-store and cross-company
    #:    inconsistency, refused structurally rather than assumed away.
    #:  * `t.expires_at IS NOT NULL` plus the caller's expiry arithmetic below.
    _TOKEN_CACHE_PROVENANCE_SQL = """
        SELECT t.access_token, t.expires_at, t.obtained_at
          FROM shopify_connector_store_access_token t
          JOIN shopify_connector_store_credential c ON c.id = t.credential_id
          JOIN shopify_connector_store s ON s.id = t.store_id
         WHERE t.store_id = %(store_id)s
           AND COALESCE(t.sec3_scope_quarantined, FALSE) = FALSE
           AND c.store_id = t.store_id
           -- `IS NOT DISTINCT FROM`, not `=`. Both companies are stored related
           -- fields through `store_id`, so they agree by construction -- but a
           -- store with no company yet (a fresh store before
           -- `action_assign_company`, and the shape most fixtures take) has NULL
           -- on all three rows, and `NULL = NULL` is NULL, not TRUE. Plain `=`
           -- would therefore refuse every company-less store's token and break
           -- authentication for stores that are otherwise perfectly operable.
           -- This form means "agree, including both-absent" and still refuses a
           -- genuine divergence, which is the invariant being asserted.
           AND c.company_id IS NOT DISTINCT FROM t.company_id
           AND s.company_id IS NOT DISTINCT FROM t.company_id
           AND c.credential_state = 'present'
           AND c.auth_mode = %(mode)s
           AND t.auth_mode = c.auth_mode
           AND t.credential_epoch = c.credential_epoch
           AND c.client_id IS NOT NULL AND c.client_id <> ''
           AND c.client_secret IS NOT NULL AND c.client_secret <> ''
           AND t.access_token IS NOT NULL AND t.access_token <> ''
           AND t.expires_at IS NOT NULL
    """

    @api.model
    def _read_committed_cache_row(self, store, cr=None):
        """`(access_token, expires_at, obtained_at)` of the PROVABLE cached token.

        Read through a fresh independent snapshot on purpose. Odoo cursors run
        REPEATABLE READ, and the refresh that minted this token committed in its
        own side transaction -- so a caller's main transaction, whose snapshot
        opened before that commit, cannot see the new row at all. An ordinary ORM
        read here would return "no token" immediately after a successful refresh,
        every time, in every fresh transaction.

        Raw SQL for the same reason `_lifecycle_credential_version` uses it, and
        additionally because the provenance predicate is a JOIN against the
        credential row: this question is "does this token belong to the identity
        the store authenticates with RIGHT NOW", and that cannot be asked of the
        cache row alone. Returns `None` when no row satisfies it -- which is the
        fail-closed answer, indistinguishable to the caller from "no token".
        The token travels to exactly one place, the return value, and is never
        logged.

        `cr` lets a caller that ALREADY owns a transaction with a fresh snapshot
        -- the refresh leader under its advisory lock, a waiter's poll -- run the
        identical predicate on its own cursor instead of opening yet another one.
        The predicate is the same string either way, which is the point: there is
        exactly one definition of "a token this store may use".
        """
        params = {'store_id': store.id, 'mode': AUTH_MODE_CLIENT_CREDENTIALS}
        if cr is not None:
            cr.execute(self._TOKEN_CACHE_PROVENANCE_SQL, params)
            return cr.fetchone() or None
        self.env['shopify.connector.store.access.token'].flush_model()
        self.flush_model()
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(self._TOKEN_CACHE_PROVENANCE_SQL, params)
            row = side_cr.fetchone()
        finally:
            side_cr.rollback()
            side_cr.close()
        return row or None

    @api.model
    def _read_cached_token_committed(self, store):
        """The store's currently valid, PROVABLY-current cached token, or False.

        A token that is alive but whose provenance cannot be proved is treated
        exactly like no token at all: the caller raises the accepted
        `REASON_TOKEN_INVALID` authentication failure and a refresh mints a new
        one from the identity that is actually configured. That is the whole
        structural half of the correction -- even if a write path were ever to
        slip an obsolete row in, no reader would serve it.
        """
        row = self._read_committed_cache_row(store)
        if not row:
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
        """Seconds of validity left on the COMMITTED, PROVABLE cached token, or 0.

        The same fresh-snapshot, provenance-checked read `_read_cached_token_
        committed` performs, for the same REPEATABLE READ reason -- a decision
        about whether to refresh must see the refresh another worker committed a
        moment ago, or every worker that raced the leader re-decides "expired"
        from its own stale snapshot.

        Routed through the shared predicate deliberately. When this returned
        remaining time for a row the READ would then refuse, the two disagreed:
        `_ensure_access_token` saw a comfortable margin and returned success,
        and `_get_access_token` immediately answered "no token". Zero is the only
        honest answer for a row that cannot be served.
        """
        return self._committed_token_window(store)[0]

    @api.model
    def _committed_token_window(self, store, cr=None):
        """`(remaining_seconds, refresh_margin_seconds)` for the cached token.

        One read answers both questions the refresher asks -- how much life is
        left, and how early this particular token should be replaced -- so the
        two can never be computed from different rows or different clocks.
        `(0, TOKEN_REFRESH_MARGIN_SECONDS)` for a token that cannot be served,
        which reads as "expired" to every caller.
        """
        row = self._read_committed_cache_row(store, cr=cr)
        if not row:
            return 0, TOKEN_REFRESH_MARGIN_SECONDS
        remaining = max(0, (row[1] - fields.Datetime.now()).total_seconds())
        lifetime = (
            (row[1] - row[2]).total_seconds() if row[2] else 0
        )
        return remaining, self._effective_refresh_margin(lifetime)

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
    def _effective_refresh_margin(self, lifetime_seconds):
        """How early to refresh a token whose whole life is `lifetime_seconds`.

        This is the clamp `TOKEN_MIN_USABLE_SECONDS` always claimed to describe
        and never performed. The margin is a fixed 15 minutes, and Shopify's
        client-credentials tokens live 86399 seconds, so for every real token the
        answer is simply the margin. But a token whose recorded lifetime is
        SHORTER than the margin is inside its own refresh window from the moment
        it is minted, and the previous code re-exchanged on every single call for
        as long as such a token was current -- an uncontrolled exchange loop
        driven by nothing but arithmetic.

        Clamping to half the lifetime makes a short-lived token get used for the
        first half of its life and refreshed in the second, which is the
        behaviour the constant's own comment described. `TOKEN_MIN_USABLE_SECONDS`
        remains the floor below which a token is treated as too close to death to
        rely on at all, and that is now the only thing it means.
        """
        try:
            lifetime = float(lifetime_seconds or 0)
        except (TypeError, ValueError):
            lifetime = 0.0
        if lifetime <= 0:
            return TOKEN_REFRESH_MARGIN_SECONDS
        return min(TOKEN_REFRESH_MARGIN_SECONDS, lifetime / 2.0)

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
    def _write_token_cache(self, store, provenance, access_token, expires_at,
                           granted_scope):
        """Persist one freshly-obtained access token. Elevated, store-scoped.

        `provenance` is `{'credential_id', 'credential_epoch', 'auth_mode'}`,
        supplied by the caller from the values it has just read under the
        credential row lock. Deliberately a plain dict and not a recordset: a
        recordset would have to be read back through the Administrator-only ACL
        -- adding a `sudo()` to this connector's trust surface -- to obtain three
        numbers the caller already holds, and reading them again would also mean
        the values written might not be the values verified.

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

        PROVENANCE. `credential_epoch` and `auth_mode` are written from the
        identity the exchange was actually performed against, which the caller
        has just revalidated against COMMITTED state under the credential row
        lock. They are what every later read compares -- `credential_id` alone
        proves nothing, because a rotation updates that row in place.
        """
        Cache = self.env['shopify.connector.store.access.token'].sudo()
        existing = Cache.search([('store_id', '=', store.id)], limit=1)
        values = {
            'store_id': store.id,
            'credential_id': provenance['credential_id'],
            'credential_epoch': provenance['credential_epoch'],
            'auth_mode': provenance['auth_mode'],
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
    def _ensure_access_token(self, store, purpose='business'):
        """Make sure this store has a usable access token, obtaining one if not.

        **Called before any lock, never inside one.** Obtaining a token is an
        HTTPS request, and this connector's whole admission design rests on no
        lock spanning a network call. Every caller -- `execute`,
        `execute_business` and the lifecycle probe -- invokes this first and
        then admits normally, so by the time a store row is locked the token is
        already in hand.

        A no-op for `offline_access_token`: that value does not expire and
        nothing may re-fetch it.

        `purpose` NAMES THE LIFECYCLE ROUTE (§7 of the Batch 1 correction), and
        it is not optional in spirit even though it has a default. Obtaining a
        token is a Shopify network call, so it obeys the same state control every
        other Shopify call obeys -- and it previously did not: because this ran
        *before* admission (correctly, for the lock reason above) it ran before
        the gate that would have refused it, so a `disconnected` store, or one
        whose generation had moved on, still reached the token endpoint. The
        eligibility check below closes that without moving the call back inside a
        lock: it is a FRESH COMMITTED read of `(state, connection_generation)`,
        taken on its own snapshot, holding no row lock.

        * `business` -- jobs, drains, Layer 2. `connected` only.
        * `setup` -- the guided setup's Test Connection / readiness probe. The
          explicit operator-driven route, which must work on a store that is not
          connected yet; that is what the operator is trying to fix.
        * `reconnect` -- the reconnect probe, the one route valid for a
          `disconnected` store.

        `disconnecting` is in no matrix at all, so no path starts an exchange
        while a disconnect is clearing the credential.

        For `dev_dashboard_client_credentials`:

        1. return immediately when the cache is comfortably valid AND provable
           (the common case -- once per 24 hours a store actually refreshes);
        2. otherwise refresh under the per-store advisory lock, exchange once,
           and revalidate the credential identity against committed state before
           anything is cached (`_refresh_access_token`);
        3. a worker that does not get the lock waits, bounded, for the leader's
           committed result and never starts a competing exchange.

        Returns True when a usable token exists afterwards. Raises the accepted
        `ShopifyClientError` taxonomy otherwise -- never a bare exception, and
        never one carrying a secret.
        """
        credential = self._credential_for(store)
        if not credential or credential.auth_mode != AUTH_MODE_CLIENT_CREDENTIALS:
            return True
        remaining, margin = self._committed_token_window(store)
        if remaining > margin:
            return True
        # Lifecycle admission for the EXCHANGE itself, before any network.
        self._assert_token_exchange_allowed(store, purpose)
        # A token that is still alive but inside the refresh margin is usable
        # RIGHT NOW. Refresh it, but never fail the call because the refresh
        # could not run -- that would turn a healthy store into an outage for
        # the last 15 minutes of every token's life. `TOKEN_MIN_USABLE_SECONDS`
        # is the floor: below it the token is too close to death to lean on, so
        # a failed refresh is a real failure and is raised.
        usable_now = remaining > TOKEN_MIN_USABLE_SECONDS
        try:
            self._refresh_access_token(store, credential, purpose)
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
    def _committed_lifecycle_state(self, store, cr=None):
        """`(state, connection_generation)` of the store, from COMMITTED state.

        A fresh snapshot and **no row lock**: this runs on the path that is about
        to make a network call, and the one invariant this connector never bends
        is that no row lock spans one. What it gives is linearizability against
        anything already committed -- which is exactly what "is this store
        eligible right now" needs -- and the post-exchange revalidation in
        `_refresh_access_token`, which DOES take the lock (after the network),
        catches anything that commits in between.
        """
        if cr is not None:
            cr.execute(
                'SELECT state, connection_generation '
                'FROM shopify_connector_store WHERE id = %s',
                (store.id,),
            )
            return cr.fetchone()
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                'SELECT state, connection_generation '
                'FROM shopify_connector_store WHERE id = %s',
                (store.id,),
            )
            return side_cr.fetchone()
        finally:
            side_cr.rollback()
            side_cr.close()

    @api.model
    def _assert_token_exchange_allowed(self, store, purpose):
        """Refuse a token exchange the store's lifecycle does not permit.

        Fail-closed on an unknown purpose: a caller that has not declared its
        route does not get the most permissive one.
        """
        from .shopify_connector_api_client import (
            ERROR_AUTH, ERROR_TEMPORARY, REASON_TEMPORARY,
            REASON_TOKEN_INVALID, ShopifyClientError,
        )
        allowed = TOKEN_EXCHANGE_PURPOSE_STATES.get(purpose)
        if allowed is None:
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                technical_detail='unknown token-exchange purpose',
            )
        row = self._committed_lifecycle_state(store)
        if not row:
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                credential_invalid=True,
            )
        state, _generation = row
        if state not in allowed:
            # Retryable rather than an authentication failure: nothing is wrong
            # with the credential. The store is simply not in a state where a
            # Shopify call is permitted, and the job layer's existing retry
            # handling is the correct response -- as is the admission refusal
            # this call would have met a moment later anyway.
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail=(
                    'store lifecycle state does not permit a token exchange'
                ),
            )
        return True

    @api.model
    def _token_exchange_in_flight(self, store):
        """True when some worker is mid-token-exchange for this store.

        The disconnect quiescence controller's window into the refresh path
        (§7.4/§7.5). A token exchange holds the store's refresh advisory lock for
        its whole duration and holds no row lock, so it is invisible to every
        lease and row-level signal the controller already consults -- and a
        disconnect that finalized during one would clear the credential while a
        token minted from it was still in flight.

        Uses `pg_try_advisory_xact_lock`, never the blocking form, and that is
        load-bearing rather than incidental: the controller calls this while
        HOLDING the store row `FOR UPDATE`, and the refresh acquires the advisory
        lock before it waits for that same row. A blocking acquisition here would
        close a wait-for cycle and deadlock; a try-lock cannot be an edge in one.

        A `True` result means "not quiesced, poll again". A `False` result leaves
        the lock held by the controller's own transaction, which additionally
        prevents a new exchange from starting while it finalizes -- the correct
        behaviour, not a side effect to work around.
        """
        self.env.cr.execute(
            'SELECT pg_try_advisory_xact_lock(%s, %s)',
            (TOKEN_REFRESH_ADVISORY_CLASSID, store.id),
        )
        return not self.env.cr.fetchone()[0]

    @api.model
    def _refresh_access_token(self, store, credential, purpose='business'):
        """Exchange once under the advisory lock, then cache only what is provable.

        THE DEFECT THIS SHAPE EXISTS TO CLOSE (reproduced by independent review,
        2026-07-30). The previous version did the whole refresh inside ONE side
        transaction: it read the client pair, made the network call, and wrote the
        cache, all on one snapshot. Odoo cursors run REPEATABLE READ, so a
        rotation or a clear that committed DURING the network call was invisible
        to that transaction -- and when the cache row was absent (the ordinary
        first-refresh case) the write was a plain `INSERT` that conflicted with
        nothing. The result was a committed token minted from secret pair A,
        stamped as current, and served for up to 24 hours after the merchant had
        rotated to pair B or cleared the credential outright. `credential_id` did
        not catch it: a rotation updates that row in place, so the relation still
        pointed at it.

        THE SHAPE. Two transactions, and the split is the correction:

        1. `lock_cr` -- takes the per-store refresh advisory lock (`try`, never
           blocking), re-checks the committed cache under it, and CAPTURES the
           identity it is about to exchange against: `(credential id, epoch,
           auth_mode)` plus `(state, generation)`. It holds NO row lock and it
           never writes. It stays open across the network call for one reason
           only: the advisory lock is what stops a second worker exchanging, and
           what makes the exchange visible to disconnect quiescence
           (`_token_exchange_in_flight`).

        2. the network exchange -- outside any row lock, exactly as before.

        3. `write_cr` -- a **NEW** transaction, and therefore a **fresh snapshot**
           that can see whatever committed while the network call was in flight.
           It takes the store lifecycle lock and then the credential row lock (the
           global store -> credential order), compares the captured identity
           against what it now reads under those locks, and only then writes the
           cache. A mismatch discards the token and writes nothing.

        Why a second transaction and not a re-read in the first: a re-read through
        `lock_cr` would return `lock_cr`'s own stale snapshot -- the exact
        "protected by a plain reread" shape that is forbidden, and the reason the
        original defect was invisible to the code that was supposed to catch it.

        Why the locks in `write_cr` are safe: they are taken AFTER the network
        call returns and released microseconds later at commit, so no row lock
        spans the exchange. Their purpose is to make the window between "identity
        verified" and "token cached" empty: a rotation racing that window either
        committed first (we see the new epoch and discard) or blocks on our lock
        until we commit and then discards our cache row itself. Both orders are
        correct; there is no third.
        """
        # Imported here rather than at module import time: the API client is an
        # AbstractModel in this same addon and the error taxonomy lives beside
        # it, so a module-level import would be a circular one.
        from .shopify_connector_api_client import (
            ERROR_AUTH, ERROR_TEMPORARY, REASON_TEMPORARY,
            REASON_TOKEN_INVALID, ShopifyClientError,
        )
        self.env.flush_all()
        lock_cr = self.env.registry.cursor()
        try:
            lock_cr.execute(
                'SELECT pg_try_advisory_xact_lock(%s, %s)',
                (TOKEN_REFRESH_ADVISORY_CLASSID, store.id),
            )
            if not lock_cr.fetchone()[0]:
                # Another worker owns the exchange for this store -- or the
                # disconnect controller owns the store. Either way this worker
                # never competes; it waits, bounded, for a committed result.
                lock_cr.rollback()
                return self._await_peer_refresh(store)
            # (1) Double-check the COMMITTED cache under the lock, on this
            # transaction's own fresh snapshot. A worker that queued behind the
            # leader arrives here after the leader committed, finds a provable
            # token, and performs no second exchange.
            remaining, margin = self._committed_token_window(store, cr=lock_cr)
            if remaining > margin:
                lock_cr.rollback()
                return True
            snapshot = self._capture_exchange_identity(store, purpose, lock_cr)
            # (2) The network call. No row lock is held; the advisory lock is.
            #
            # A failed exchange writes NOTHING -- not the credential row, not the
            # cache. The raised taxonomy is the failure evidence, and the
            # CALLER's transaction owns recording it: the connection probe routes
            # it through `_apply_probe_failure` (store mirrors,
            # `credential_state`, reconnect), and a business call routes it
            # through the dispatcher's auth-failure family.
            token, expires_at, granted_scope = self.env[
                'shopify.connector.api.client'
            ]._exchange_client_credentials(
                store, snapshot['client_id'], snapshot['client_secret'],
            )
            # The secrets have done their single job. Drop the references before
            # anything else can reach them.
            snapshot['client_id'] = None
            snapshot['client_secret'] = None
            # (3) Revalidate against COMMITTED state and cache atomically.
            self._commit_token_if_identity_holds(
                store, snapshot, token, expires_at, granted_scope,
            )
            # COMMIT rather than roll back, even though this transaction wrote
            # nothing. In production the two cursors are independent connections
            # and either would do -- but under Odoo's registry test mode
            # `registry.cursor()` hands out `TestCursor`s layered as NESTED
            # SAVEPOINTS on one connection, so the write cursor's savepoint is
            # nested inside this one. Rolling this back would then discard the
            # cache row that was just committed inside it, and the whole refresh
            # would silently persist nothing while reporting success. Committing
            # releases both savepoints in order and behaves identically on real
            # connections, where it simply ends a read-only transaction and
            # releases the advisory lock.
            lock_cr.commit()
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY as exc:
            # A genuine SQLSTATE 40001/40P01/55P03. Fail CLOSED and normalized:
            # nothing is cached, and the caller sees the connector's own
            # retryable taxonomy rather than a raw psycopg2 exception escaping
            # through a Shopify-facing code path. `technical_detail` carries the
            # SQLSTATE only -- no query, no row, no secret.
            lock_cr.rollback()
            _logger.info(
                'Shopify access-token refresh for store %s hit a PostgreSQL '
                'concurrency failure (SQLSTATE %s); nothing was cached.',
                store.id, getattr(exc, 'pgcode', None),
            )
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail=(
                    'token refresh hit a database concurrency conflict '
                    '(SQLSTATE %s)' % (getattr(exc, 'pgcode', None) or '40001')
                ),
            )
        except Exception:
            lock_cr.rollback()
            raise
        finally:
            lock_cr.close()
            # The main environment must not keep serving what it read before
            # the side transactions ran -- on the SUCCESS path that is the
            # pre-refresh token cache, and on the FAILURE path it is the
            # pre-failure `credential_state`/failure-reason mirrors. Both
            # re-read correctly only after an invalidation, so it is
            # unconditional.
            self.env['shopify.connector.store.access.token'].invalidate_model()
            self.invalidate_model()
        return True

    @api.model
    def _capture_exchange_identity(self, store, purpose, cr):
        """The exact identity and lifecycle position this exchange is bound to.

        Read on `cr`, which holds the advisory lock and a fresh snapshot. The
        secrets are returned for the one call that needs them and are dropped by
        the caller the moment it returns; everything else in the dict is
        non-secret and is what the post-network revalidation compares.
        """
        from .shopify_connector_api_client import (
            ERROR_AUTH, REASON_TOKEN_INVALID, ShopifyClientError,
        )
        cr.execute(
            'SELECT id, credential_epoch, auth_mode, credential_state, '
            'client_id, client_secret '
            'FROM shopify_connector_store_credential WHERE store_id = %s',
            (store.id,),
        )
        row = cr.fetchone()
        if (
            not row
            or row[2] != AUTH_MODE_CLIENT_CREDENTIALS
            or row[3] != 'present'
            or not row[4]
            or not row[5]
        ):
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                credential_invalid=True,
            )
        lifecycle = self._committed_lifecycle_state(store, cr=cr)
        if not lifecycle:
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                credential_invalid=True,
            )
        return {
            'credential_id': row[0],
            'credential_epoch': row[1],
            'auth_mode': row[2],
            'client_id': row[4],
            'client_secret': row[5],
            'state': lifecycle[0],
            'generation': lifecycle[1],
            'purpose': purpose,
        }

    @api.model
    def _commit_token_if_identity_holds(self, store, snapshot, token,
                                        expires_at, granted_scope):
        """Cache the exchanged token, or discard it -- atomically, on fresh state.

        Runs in its OWN transaction so its snapshot begins after the network call
        and can therefore see a rotation, a clear, a mode switch or a lifecycle
        transition that committed while the exchange was in flight. Takes the
        store lifecycle lock and then the credential row lock -- the global
        `store -> credential` order every other path in this connector follows --
        so no such change can interleave between the comparison and the write.

        Discards on ANY of: the credential row gone; a different row id; a bumped
        identity epoch; a changed acquisition mode; a `credential_state` that is
        no longer `present`; an emptied client pair; a store state now ineligible
        for the purpose this exchange was performed for; a changed
        `connection_generation`.

        Nothing is written on the discard path -- no cache row, no credential
        column, no store mirror -- and the token is dropped without ever being
        logged. The caller receives the accepted taxonomy: an authentication
        failure when the credential is gone or unusable, and the retryable class
        when the identity has simply moved on, because a retry against the NEW
        identity is exactly the right next step.
        """
        from .shopify_connector_api_client import (
            ERROR_AUTH, ERROR_TEMPORARY, REASON_TEMPORARY,
            REASON_TOKEN_INVALID, ShopifyClientError,
        )
        write_cr = self.env.registry.cursor()
        try:
            # store -> credential, both blocking, both AFTER the network call.
            write_cr.execute(
                'SELECT state, connection_generation '
                'FROM shopify_connector_store WHERE id = %s FOR NO KEY UPDATE',
                (store.id,),
            )
            store_row = write_cr.fetchone()
            write_cr.execute(
                'SELECT id, credential_epoch, auth_mode, credential_state, '
                '(client_id IS NOT NULL AND client_id <> \'\') AS has_id, '
                '(client_secret IS NOT NULL AND client_secret <> \'\') AS has_secret '
                'FROM shopify_connector_store_credential '
                'WHERE store_id = %s FOR NO KEY UPDATE',
                (store.id,),
            )
            cred_row = write_cr.fetchone()
            if (
                not cred_row
                or cred_row[3] != 'present'
                or not cred_row[4]
                or not cred_row[5]
            ):
                write_cr.rollback()
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            allowed = TOKEN_EXCHANGE_PURPOSE_STATES.get(
                snapshot['purpose'], (),
            )
            if (
                cred_row[0] != snapshot['credential_id']
                or cred_row[1] != snapshot['credential_epoch']
                or cred_row[2] != snapshot['auth_mode']
                or not store_row
                or store_row[0] not in allowed
                or store_row[1] != snapshot['generation']
            ):
                write_cr.rollback()
                _logger.info(
                    'Shopify access token for store %s was discarded: the '
                    'credential identity or store lifecycle changed during the '
                    'exchange. Nothing was cached.', store.id,
                )
                raise ShopifyClientError(
                    error_class=ERROR_TEMPORARY,
                    reason=REASON_TEMPORARY,
                    technical_detail=(
                        'the credential identity was superseded during the '
                        'token exchange'
                    ),
                )
            write_env = api.Environment(
                write_cr, self.env.uid, self.env.context,
            )
            # The provenance written is EXACTLY the provenance just verified
            # under the two locks -- the same three values, not a re-read.
            write_env[self._name]._write_token_cache(
                write_env['shopify.connector.store'].browse(store.id),
                {
                    'credential_id': cred_row[0],
                    'credential_epoch': cred_row[1],
                    'auth_mode': cred_row[2],
                },
                token, expires_at, granted_scope,
            )
            write_cr.commit()
        except Exception:
            write_cr.rollback()
            raise
        finally:
            write_cr.close()
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
                # The SAME provenance predicate every other read uses. A waiter
                # that accepted a row the reader would refuse would report
                # success and then hand its caller "no token" -- and, worse, a
                # waiter that accepted an obsolete-provenance row would be a
                # second way into the defect this correction closes.
                remaining, _margin = poll_self._committed_token_window(
                    poll_store, cr=poll_cr,
                )
                fresh = remaining > TOKEN_MIN_USABLE_SECONDS
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
        credential is the row's own identity EPOCH, which the credential service
        bumps exactly once per sanctioned set, replace, clear or mode switch --
        and never on a token rotation, which writes only the cache row.

        BATCH 1 CORRECTION. This used to return the `(client_id, client_secret)`
        pair for the client-credentials mode and the raw `access_token` for the
        offline mode. Both worked, and both were worse than this:

        * they put a live secret in a snapshot that is carried across a network
          call, for no purpose beyond an equality test;
        * the offline branch compared VALUES, so an operator who re-entered the
          identical token produced an "unchanged" identity even though the
          service had invalidated the store's verification evidence. The epoch
          advances on that write like any other, so a same-value replace is now
          caught rather than missed.

        The epoch is non-secret, so unlike its predecessor the returned value is
        safe in a log or an exception. Nothing logs it anyway; the contract is
        unchanged, the exposure is simply gone.

        Returns `False` for a store with no credential row, which every caller
        already treats as "superseded".
        """
        credential = self._credential_for(store)
        if not credential:
            return False
        return credential.credential_epoch or 0
