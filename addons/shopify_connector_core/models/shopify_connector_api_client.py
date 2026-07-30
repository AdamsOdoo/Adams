import logging
import os
import re
import uuid
from contextlib import contextmanager
from datetime import timedelta
from types import SimpleNamespace

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.api_version import (
    API_VERSION_RESPONSE_HEADER,
    SHOPIFY_API_VERSION,
    admin_graphql_endpoint,
)
from ..tools.redaction import redact
from .shopify_connector_mutation_attempt import canonical_sha256

_logger = logging.getLogger(__name__)

# Adjustable planning defaults (not an official Shopify requirement).
_CONNECT_TIMEOUT_SECONDS = 10
_READ_TIMEOUT_SECONDS = 20

# CORE-R2 admission-lease lifetime used to stamp `call.lease.expires_at`. It
# must exceed the transport budget (connect + read timeouts above) plus a
# reconciliation allowance. This is a tuning-only default [Open, analysis §26];
# the disconnect controller / DISCONNECT_QUIESCE_TIMEOUT / POLL_DELAY constants
# that would *consume* expiry live in the dispatcher and are a later CORE-R2
# slice, so no logic in this slice depends on the exact value.
_CALL_LEASE_LIFETIME_SECONDS = 300

# The fixed 16-class error_class registry (DEC-009) -- only the four
# classes below are ever raised by this client; identity-mismatch
# (`odoo_validation_configuration`) is interpreted by
# `action_test_connection()` from a successful `execute()` response, not
# raised here.
ERROR_TEMPORARY = 'shopify_temporary_server_network'
ERROR_AUTH = 'shopify_permission_scope_auth'
ERROR_THROTTLE = 'shopify_throttling_rate_limit'
ERROR_UNKNOWN = 'unknown_system_error'
# The API-version block. Classified as a configuration/API-compatibility
# problem, which is exactly what it is: an operator fixes it (by correcting
# the store's recorded version, or by the connector being upgraded to a
# version Shopify still serves) and then retries. No 17th error class is
# introduced -- this is the existing DEC-009 "manual fix then retry" class.
ERROR_API_VERSION = 'odoo_validation_configuration'

# The five mandatory, pairwise-distinct plain-language reasons for the
# shopify_permission_scope_auth class (AR-027, F1 revision) -- a shared/
# generic string across any two of them is a review failure.
REASON_TOKEN_INVALID = (
    'Your access token appears invalid or was revoked — replace it.'
)
REASON_SHOP_FROZEN = (
    'Shopify has frozen this store, most commonly for a billing/payment '
    'issue — resolve it in Shopify, then retry.'
)
REASON_SHOP_LOCKED = 'This store has been locked by Shopify.'
REASON_SHOP_FRAUDULENT = 'Shopify has flagged this store as fraudulent.'
REASON_SHOP_INACTIVE = 'This store is inactive.'

REASON_TEMPORARY = (
    'Shopify could not be reached right now — this is usually temporary.'
)
# THROTTLED/429 body shape is unofficial/unconfirmed -- see Open question
# #1/#3, credential-connection-api-client-planning.md.
REASON_THROTTLED = 'Shopify is asking us to slow down — try again shortly.'
REASON_UNKNOWN = (
    'Shopify returned a response we could not interpret — try again, '
    'and contact support if it persists.'
)
# Deliberately names no header value, no token and no domain: an
# operator-facing reason has to be safe to paste into a support ticket.
REASON_API_VERSION = (
    'Shopify did not serve the Admin API version this connector is built '
    'for, so the response was refused rather than acted on. This needs a '
    'configuration or connector-version fix, not a retry.'
)

# CORE-R2 (AR-047; analysis §9.1) lifecycle-call purpose -> allowed store
# states. `_admit_lifecycle` (snapshot/gate) and `_send_lifecycle` (transport)
# are the private guarded entry for setup/diagnostic Shopify calls; each
# `purpose` carries a fixed allowed-state matrix (not a generic bypass). A call
# outside its matrix fails closed, and NO lifecycle call is permitted while the
# store is `disconnecting` -- none of the purposes below lists it (frozen
# lifecycle matrix, analysis §8).
LIFECYCLE_PURPOSE_STATES = {
    'test_connection': ('setup_incomplete', 'connected', 'reconnect_needed'),
    'readiness_probe': ('setup_incomplete', 'connected', 'reconnect_needed'),
    'reconnect_probe': ('reconnect_needed', 'disconnected'),
}


class ShopifyClientError(Exception):
    """Normalized error raised by `shopify.connector.api.client.execute()`.

    Attributes: `error_class` (one of the fixed 16), `reason` (the
    plain-language safe message), `technical_detail` (redacted; carries
    `extensions.requestId` when present, otherwise a redacted status/body
    excerpt), and `credential_invalid` (bool, default False -- set only
    for a genuine token-invalid signal, never for a shop-account-state
    condition). `str(exc)` returns `reason` only -- never the technical
    detail, never a header, never the token.
    """

    def __init__(
        self, error_class, reason, technical_detail=False,
        credential_invalid=False,
    ):
        reason = redact(reason)
        super().__init__(reason)
        self.error_class = error_class
        self.reason = reason
        self.technical_detail = (
            redact(technical_detail) if technical_detail else technical_detail
        )
        self.credential_invalid = credential_invalid

    def __str__(self):
        return self.reason


class ShopifyQuiescedError(Exception):
    """Raised by `_admit` when a business Shopify call is refused at admission.

    A fail-closed admission refusal (CORE-R2, AR-047): the store is not
    `connected`, the store's persisted `connection_generation` no longer matches
    the job's captured `expected_connection_generation`, no real job was
    supplied, or the job belongs to another store. It carries no token and no
    payload; `str(exc)` is a safe, generic message. In the full CORE-R2 design a
    dispatcher maps this to a `skipped` job (analysis §18) — that routing is a
    later slice and is not wired here.
    """


class ShopifyConnectorApiClient(models.AbstractModel):
    """Read-only Shopify Admin GraphQL transport boundary (Task 003 + CORE-R2).

    Stateless, no table. Public entry points are `execute()` (the pre-existing
    read-only call used by test-connection/readiness) and, added by the CORE-R2
    foundation slice, `execute_business()` — a committed-admission-lease context
    manager (AR-047; analysis §9.1). `_send()` is the only method containing an
    actual HTTP call and is the transport-injection seam tests override. No method
    on this model can construct a request body containing the GraphQL mutation
    keyword followed by a selection/argument — there is no mutation-capable
    method, no retry loop (retry policy belongs to the job layer, DEC-009), and no
    domain-sync method.

    **Credential access is read exactly once per admitted business call.**
    `_admit` reads the token once under a `FOR SHARE` store-row lock and passes
    the in-memory snapshot to `_send(store, body, token)`, which never re-reads
    it. The lease create/release go through normal ACL (no new `sudo()` here); the
    only sanctioned `sudo()` remains the pre-existing Task 002 `_get_access_token`
    the admission calls once.

    **Foundation-slice dormancy.** `execute_business`/`_admit`/`_release_lease`
    and the `call.lease` table are delivered here but no production call site uses
    them yet; the legacy `execute()` path is unchanged and still the only live
    caller. The `_send` token parameter is optional so the unchanged `execute()`
    (and the transport-seam tests that patch `_send(store, body)`) keep working;
    it becomes mandatory when `execute()` is privatized in a later CORE-R2 slice.
    """

    _name = 'shopify.connector.api.client'
    _description = 'Shopify Connector API Client'

    @api.model
    def execute(self, store, query, variables=None):
        """Send one read-only GraphQL query and return its normalized data.

        Returns `{'data': <parsed data>, 'throttle_status': <dict or
        None>, 'served_version': <the verified version string>}`. Raises
        `ShopifyClientError` on any transport or GraphQL-level failure,
        **including** an API-version mismatch or a missing
        `X-Shopify-API-Version` header: under the 2026-07-26 ruling a
        response Shopify served on another version is refused rather than
        returned with a fall-forward marker.
        """
        self._validate_graphql_operation(
            query, variables or {}, mutation_context=None,
        )
        if not store.shop_domain or not store.api_version:
            raise UserError(
                'A shop domain and API version are required before '
                'contacting Shopify.'
            )
        Credential = self.env['shopify.connector.store.credential']
        # Wave 5: obtain/refresh a client-credentials token BEFORE anything is
        # locked. A no-op for the offline mode. Placed here, and not inside the
        # token read below, because obtaining one is itself a network call and
        # no lock in this connector may span a network call.
        #
        # Batch 1 correction: `purpose='setup'`. `execute()` is the legacy
        # read-only entry point, and its live callers are the setup/diagnostic
        # family -- Test Connection and the readiness probe -- whose whole job is
        # to authenticate a store that is NOT yet connected. It is not the
        # business path (that is `execute_business`/`_admit`, which declares
        # `business`), so it must not be gated to `connected` only. It IS gated:
        # `disconnecting` appears in no matrix, so a store mid-disconnect cannot
        # reach the token endpoint through here either.
        Credential._ensure_access_token(store, purpose='setup')
        token = Credential._get_access_token(store)
        if not token:
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                credential_invalid=True,
            )
        body = {'query': query, 'variables': variables or {}}
        try:
            response = self._send(store, body)
        except ShopifyClientError:
            raise
        except requests.exceptions.RequestException as exc:
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail=redact(str(exc)),
            )
        return self._normalize_response(store, response)

    @api.model
    def _admit_lifecycle(self, store, purpose):
        """Atomically bind one lifecycle probe to ONE credential snapshot in a
        short independent side transaction (CORE-R2, AR-047; analysis §9.1;
        reviews 4690804619 #1 + 4691182306 #1).

        **Private on purpose.** `purpose` is a fixed enum selected by the two
        trusted store callers only (`action_test_connection` -> `test_connection`,
        `action_reconnect` -> `reconnect_probe`, both via the store's shared
        `_run_connection_probe`). It is deliberately **not** a public/RPC-exposed
        method, so an arbitrary caller can never drive a caller-controlled purpose
        through RPC (the public API-client surface stays exactly
        `{execute, execute_business}`).

        **Atomic admission (review 4691182306 #1).** The snapshot is captured in
        one owned side transaction so the store-row ``SELECT … FOR SHARE`` lock
        **linearizes** this admission against any generation-changing lifecycle
        transition's ``FOR NO KEY UPDATE`` (disconnect / activation / reconnect /
        connected credential-replace) -- the **same** mechanism as the business
        `_admit`, minus any lease. If ``action_disconnect`` wins first, this
        admission's ``FOR SHARE`` reads the fresh ``disconnecting``/new-generation
        row **before** any network call and refuses; if this admission commits
        first, a later disconnect is caught by the post-network revalidation. The
        ``FOR SHARE`` is **committed (released) before** `_send_lifecycle` runs --
        **no lock spans the network call** -- and **no `call.lease` is created**
        (this is the setup/diagnostic counterpart, not a business admission).

        Sequence (mirrors `_admit`): open an owned ``registry.cursor()`` side
        transaction; ``SELECT state, connection_generation … FOR SHARE`` on the
        store row; **freshly** re-check the fixed purpose->state matrix under that
        lock (no purpose lists ``disconnecting``); read the access token **exactly
        once** (the one sanctioned `_get_access_token`); capture the credential row
        id + version (``id``, ``write_date``); ``commit`` (persists nothing,
        releases the ``FOR SHARE``, completes the admission linearization); close.
        Returns the non-persisted snapshot the caller passes to
        `_send_lifecycle(store, body, token)` (so the transport re-reads **no**
        credential) and later revalidates via `_lifecycle_probe_superseded`.

        Fails closed exactly like the read-only contract: an unknown/absent purpose
        or a state outside the matrix (freshly read under the lock) raises
        `UserError` -- the caller treats a post-pre-check matrix refusal as a probe
        superseded before send; a missing/empty credential raises
        `ShopifyClientError(ERROR_AUTH, REASON_TOKEN_INVALID,
        credential_invalid=True)` -- both before any network. Any side-transaction
        failure rolls back and closes the cursor; no request/main-cursor commit and
        no token is ever logged/persisted.
        """
        allowed_states = LIFECYCLE_PURPOSE_STATES.get(purpose)
        if allowed_states is None:
            raise UserError(
                'An unknown lifecycle purpose was requested; the Shopify '
                'call is refused.'
            )
        # Flush the caller's pending ORM writes (store + credential) so the
        # independent side cursor's raw locking SELECT and the side-env credential
        # reads observe the current state/generation/token. In production the store
        # and credential rows are long committed, so this is effectively a no-op
        # for the side cursor's reads (it sees committed data); it is required for
        # correctness only when the caller created/wrote them within this same
        # transaction (e.g. under registry test mode).
        self.env.flush_all()
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                "SELECT state, connection_generation "
                "FROM shopify_connector_store WHERE id = %s FOR SHARE",
                (store.id,),
            )
            row = side_cr.fetchone()
            if row is None:
                # The store row is not available on an independent transaction
                # (e.g. deleted mid-probe) -- fail closed before any network.
                raise UserError(
                    'This store is no longer available; the Shopify call is '
                    'refused.'
                )
            state, generation = row
            # Fresh matrix re-check UNDER the FOR SHARE lock (defense in depth
            # atop the store's pre-check + the linearization point): a disconnect
            # that won before this lock is observed here and refused before send.
            if state not in allowed_states:
                raise UserError(
                    'This diagnostic is not available while the store is "%s"; '
                    'the Shopify call is refused.' % state
                )
            side_env = api.Environment(side_cr, self.env.uid, self.env.context)
            side_credential = side_env['shopify.connector.store.credential']
            side_store = side_env['shopify.connector.store'].browse(store.id)
            # Single token read under the lock (the one sanctioned
            # `_get_access_token` sudo -- no new sudo introduced here).
            token = side_credential._get_access_token(side_store)
            if not token:
                # A store still inside the matrix but with no usable credential
                # (e.g. a raced direct clear) is an authentication failure -- the
                # accepted API-client taxonomy, before any lease/network.
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            # Credential id + write_date baseline captured under the same locked
            # snapshot (lock=False: the store FOR SHARE is the linearization
            # primitive; the post-network revalidation takes the credential lock).
            version = side_credential._lifecycle_credential_version(
                side_store, lock=False
            )
            snapshot = {
                'token': token,
                # Wave 5: the value the post-network revalidation compares to
                # decide whether the CREDENTIAL changed. For the offline mode it
                # is the token itself, exactly as before. For the
                # client-credentials mode it is the app's `(client_id,
                # client_secret)` pair, because that token rotates every 24
                # hours by design and a scheduled rotation must not be read as
                # a merchant replacing their credential.
                'identity': side_credential._lifecycle_credential_identity(
                    side_store,
                ),
                'credential_id': version[0] if version else False,
                'credential_version': version[1] if version else False,
                'generation': generation,
                'allowed_states': allowed_states,
            }
            # Commit the short admission side transaction: persists NO business
            # data (no lease, no write), releases the FOR SHARE lock, and
            # completes the lifecycle-admission linearization -- all BEFORE the
            # network call in `_send_lifecycle`.
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
        return snapshot

    @api.model
    def _send_lifecycle(self, store, query, token, variables=None):
        """Issue one lifecycle probe using the exact snapshot token (CORE-R2,
        AR-047; review 4690804619 #1).

        The transport half of the lifecycle path. Receives the single token
        snapshot from `_admit_lifecycle` and passes it straight to
        `_send(store, body, token)` -- so the request uses **exactly** that
        snapshot and the transport re-reads **no** credential (unlike the former
        `execute()` delegation, which pre-checked the token and then let `_send`
        read it again). Preserves the accepted read-only contract: the same
        missing-configuration `UserError` (raised before any transport), the
        `RequestException` -> `ShopifyClientError(ERROR_TEMPORARY, REASON_TEMPORARY)`
        mapping, and the shared `_normalize_response` taxonomy. No lock is held
        here; the post-network revalidation lives in the store's probe. Public
        `execute()` (still the two-arg `_send(store, body)` seam) is unchanged.
        """
        self._validate_graphql_operation(
            query, variables or {}, mutation_context=None,
        )
        if not store.shop_domain or not store.api_version:
            raise UserError(
                'A shop domain and API version are required before '
                'contacting Shopify.'
            )
        body = {'query': query, 'variables': variables or {}}
        try:
            response = self._send(store, body, token)
        except ShopifyClientError:
            raise
        except requests.exceptions.RequestException as exc:
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail=redact(str(exc)),
            )
        return self._normalize_response(store, response)

    @contextmanager
    def execute_business(
        self, job, store, query, variables=None, mutation_context=None,
    ):
        """Admit and issue one business Shopify call as a context manager (CORE-R2).

        The single guarded entry point for domain-handler Shopify calls
        (AR-047; analysis §9.1). Used **only** as a context manager::

            with client.execute_business(job, store, query, variables) as result:
                payload = normalize(result)
                apply_import(store, payload)      # local reconciliation

        **API parity with `execute()` (control-room review `4680664964`).**
        `execute_business` preserves the accepted API-client response/error
        contract so a domain call site can replace ``result = client.execute(…)``
        with ``with client.execute_business(job, store, …) as result:`` without
        changing behaviour:

        - the same missing-configuration `UserError` (no `shop_domain` /
          `api_version`), raised **before** any admission, lease, or `_send`;
        - a missing/empty credential raises the accepted
          `ShopifyClientError(ERROR_AUTH, REASON_TOKEN_INVALID,
          credential_invalid=True)` inside `_admit` **before** the lease insert
          and before `_send` (never a `ShopifyQuiescedError`, never a lease);
        - a `requests.RequestException` from `_send` is mapped to
          `ShopifyClientError(ERROR_TEMPORARY, REASON_TEMPORARY, …)` (token/header/
          body redacted);
        - the yielded value is `_normalize_response(store, response)` — the same
          normalized dict `execute()` returns, with the full HTTP/GraphQL/auth/
          throttle/version taxonomy — **not** the raw transport object.

        `__enter__` performs the atomic admission of `_admit` (store-row
        `FOR SHARE` lock -> fresh state/generation gate -> single token read ->
        committed lease), issues the request via `_send(store, body, token)` with
        that one token snapshot, normalizes it, and yields the dict. The committed
        lease is **held for the whole `with` body** (through `_normalize_response`
        and the caller's reconciliation), so it provably outlives reconciliation.

        **Deterministic exception precedence (review `4680664964`).** The
        body/`_send`/normalization failure is always the **primary** exception; a
        simultaneous release failure is **chained** (`raise primary from
        release_error`), never replacing it — so the accepted `ShopifyClientError`
        classification is preserved. On a successful body a release failure
        propagates. The lease is released exactly once (never twice), on both
        normal and exception exit; caller exceptions are never suppressed and
        KeyboardInterrupt/SystemExit still attempt release. A process crash inside
        the body runs no release, leaving the committed lease for the
        (later-slice) direction-C timeout path.

        There is deliberately no value-returning form and no manual release. If
        admission is refused, `__enter__` raises before any lease or call.
        **Dormant in this slice** — no production call site enters this context
        yet.
        """
        # Same configuration precondition as execute() -- fail before any
        # admission, lease, or transport (no lease, no _send).
        variables = variables or {}
        self._validate_graphql_operation(
            query, variables, mutation_context,
        )
        is_mutation = self._graphql_contains_mutation(query)
        if is_mutation:
            job_id = job if isinstance(job, int) else getattr(job, 'id', False)
            store_id = (
                store if isinstance(store, int) else getattr(store, 'id', False)
            )
            lease_key, token, transport_store = self._admit_mutation(
                job_id, store_id, mutation_context,
            )
        else:
            if not store.shop_domain or not store.api_version:
                raise UserError(
                    'A shop domain and API version are required before '
                    'contacting Shopify.'
                )
            lease_key, token = self._admit(job, store)
            transport_store = store
        # _admit reads the token once and raises the accepted taxonomy on a
        # missing credential (ShopifyClientError) or fails closed on the gate
        # (ShopifyQuiescedError) -- in either case before any lease exists, so no
        # release is owed here.
        try:
            body = {'query': query, 'variables': variables}
            try:
                if mutation_context is None:
                    response = self._send(transport_store, body, token)
                else:
                    response = self._send(
                        transport_store,
                        body,
                        token,
                        mutation_context=mutation_context,
                    )
            except ShopifyClientError:
                raise
            except requests.exceptions.RequestException as exc:
                raise ShopifyClientError(
                    error_class=ERROR_TEMPORARY,
                    reason=REASON_TEMPORARY,
                    technical_detail=redact(str(exc)),
                )
            result = self._normalize_response(transport_store, response)
            yield result
        except BaseException as primary_error:
            # Precedence: the primary (body/send/normalization/caller) exception
            # is preserved; a release failure is chained, never substituted. On a
            # successful release, a **bare** ``raise`` re-raises the in-flight
            # exception with its ORIGINAL traceback (identity + classification +
            # the caller-body raise site), adding no new raise frame (review
            # `4681564744`).
            try:
                self._release_lease(lease_key)
            except BaseException as release_error:
                raise primary_error from release_error
            raise
        else:
            # Body succeeded -> release normally; a release failure here has no
            # prior exception to preserve, so it propagates.
            self._release_lease(lease_key)

    def _admit(self, job, store):
        """Atomically admit one business call; return `(lease_key, token)`.

        The exact CORE-R2 admission sequence (analysis §9.2), performed in one
        owned side transaction so the gate read, the single token read, and the
        lease insert all happen under the same `FOR SHARE` lock on the store row
        and commit atomically with it:

          1. open an owned side cursor (independent transaction);
          2. `SELECT ... FOR SHARE` on the store row — a shared lock: concurrent
             admissions do not conflict, but any generation-changing lifecycle
             transition's `FOR NO KEY UPDATE`/`FOR UPDATE` does;
          3. under that lock, freshly read `state` + `connection_generation`;
          4. a real job must be supplied;
          5. the job must belong to this store;
          6. the store must be `connected`;
          7. the store generation must equal the job's captured
             `expected_connection_generation`;
          8. read the access token exactly once (no second lookup anywhere); a
             missing/empty credential raises `ShopifyClientError(ERROR_AUTH,
             REASON_TOKEN_INVALID, credential_invalid=True)` here — before any
             lease insert — never a `ShopifyQuiescedError`;
          9. generate an opaque lease key;
         10. insert the committed lease;
         11. commit — persists the lease and releases the `FOR SHARE` lock
             together;
         12/13. close the side cursor.

        Returns only an opaque lease identity and the in-memory token snapshot —
        never the credential row, never a query, never a payload. Any refusal
        raises `ShopifyQuiescedError`; the side transaction is rolled back
        (releasing the lock) and the cursor is closed. `_send` runs *after* this
        returns, so no lock is ever held across the network call.

        Foundation-slice note: the conflicting lifecycle update-lock on
        `action_disconnect`/reconnect/credential-replace is a later CORE-R2
        slice, so the admission-vs-disconnect linearization is not yet closed end
        to end; this method builds and commits the admission half only.
        """
        # Wave 5: a client-credentials store obtains/refreshes its 24-hour token
        # HERE, before the side cursor opens and therefore before the `FOR
        # SHARE` lock exists. A no-op for the offline mode. The single token
        # read below is unchanged and still reads exactly once, under the lock.
        #
        # Batch 1 correction: `purpose='business'`. This is the business
        # admission path, so the exchange is admitted for `connected` only --
        # the same state this method's own gate enforces a few lines below. The
        # gate was previously unreachable for the exchange, because the exchange
        # ran before it: a `disconnected` or `disconnecting` store contacted the
        # token endpoint and was only then refused the call it needed the token
        # for.
        self.env['shopify.connector.store.credential']._ensure_access_token(
            store, purpose='business',
        )
        lifetime = timedelta(seconds=_CALL_LEASE_LIFETIME_SECONDS)
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                "SELECT state, connection_generation "
                "FROM shopify_connector_store WHERE id = %s FOR SHARE",
                (store.id,),
            )
            row = side_cr.fetchone()
            if row is None:
                raise ShopifyQuiescedError(
                    'This store is no longer available for Shopify calls.'
                )
            state, generation = row
            if not job or not job.id or not job.exists():
                raise ShopifyQuiescedError(
                    'A business Shopify call requires a valid job.'
                )
            if job.store_id.id != store.id:
                raise ShopifyQuiescedError(
                    'This job does not belong to the target store.'
                )
            if state != 'connected':
                raise ShopifyQuiescedError(
                    'This store is not connected; the Shopify call is refused.'
                )
            if generation != job.expected_connection_generation:
                raise ShopifyQuiescedError(
                    'This store was reconnected; the Shopify call is refused.'
                )
            side_env = api.Environment(side_cr, self.env.uid, self.env.context)
            token = side_env[
                'shopify.connector.store.credential'
            ]._get_access_token(
                side_env['shopify.connector.store'].browse(store.id)
            )
            if not token:
                # A connected store with no usable credential is an
                # authentication failure, not a quiescence refusal -- raise the
                # accepted API-client taxonomy BEFORE any lease insert and before
                # `_send`, and without a second credential read. The side txn is
                # rolled back (releasing FOR SHARE) and closed by the handlers
                # below, so no lease is committed.
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            lease_key = uuid.uuid4().hex
            admitted_at = fields.Datetime.now()
            side_env['shopify.connector.call.lease'].create({
                'store_id': store.id,
                'lease_key': lease_key,
                'job_id': job.id,
                'worker_ref': self._lease_worker_ref(),
                'admitted_at': admitted_at,
                'expires_at': admitted_at + lifetime,
            })
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
        return lease_key, token

    def _admit_mutation(self, job_id, store_id, mutation_context):
        """Admit Layer 2 from immutable ids in one owned side transaction."""
        context = dict(mutation_context or {})
        if not isinstance(job_id, int) or not isinstance(store_id, int):
            raise ShopifyQuiescedError(
                'Layer 2 admission requires immutable job/store ids.'
            )
        # Wave 5: same placement and same reason as `_admit` -- obtain/refresh
        # before the side cursor and its row locks exist, never inside them.
        # Batch 1 correction: Layer 2 mutation dispatch is business traffic, so
        # the exchange is admitted for `connected` only, exactly like the
        # snapshot gate below.
        self.env['shopify.connector.store.credential']._ensure_access_token(
            self.env['shopify.connector.store'].browse(store_id),
            purpose='business',
        )
        lifetime = timedelta(seconds=_CALL_LEASE_LIFETIME_SECONDS)
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                "SELECT j.store_id, j.state, j.current_attempt_token, "
                "j.job_type, j.expected_connection_generation, "
                "s.state, s.connection_generation, s.shop_domain, "
                "s.api_version, a.attempt_token, a.mutation_domain, "
                "a.observed_outcome, a.transport_attempted, "
                "a.idempotency_valid_until, "
                "(SELECT count(*) FROM shopify_connector_mutation_attempt "
                "WHERE job_id = j.id) "
                "FROM shopify_connector_job j "
                "JOIN shopify_connector_store s ON s.id = j.store_id "
                "JOIN shopify_connector_mutation_attempt a "
                "ON a.job_id = j.id "
                "WHERE j.id = %s AND a.id = %s FOR SHARE OF s",
                (job_id, context.get('attempt_id')),
            )
            row = side_cr.fetchone()
            now = fields.Datetime.now()
            if (
                not row
                or row[0] != store_id
                or row[1] != 'running'
                or row[2] != context.get('attempt_token')
                or row[3] != context.get('mutation_domain')
                or row[4] != row[6]
                or row[5] != 'connected'
                or row[9] != context.get('attempt_token')
                or row[10] != context.get('mutation_domain')
                or row[11] != 'pending'
                or not row[12]
                or not row[13]
                or row[13] <= now
                or row[14] != 1
            ):
                raise ShopifyQuiescedError(
                    'The Layer 2 admission snapshot is stale or invalid.'
                )
            shop_domain, api_version = row[7], row[8]
            if not shop_domain or not api_version:
                raise UserError(
                    'A shop domain and API version are required before '
                    'contacting Shopify.'
                )
            side_env = api.Environment(side_cr, self.env.uid, self.env.context)
            side_store = side_env['shopify.connector.store'].browse(store_id)
            token = side_env[
                'shopify.connector.store.credential'
            ]._get_access_token(side_store)
            if not token:
                raise ShopifyClientError(
                    error_class=ERROR_AUTH,
                    reason=REASON_TOKEN_INVALID,
                    credential_invalid=True,
                )
            lease_key = uuid.uuid4().hex
            admitted_at = fields.Datetime.now()
            side_env['shopify.connector.call.lease'].create({
                'store_id': store_id,
                'lease_key': lease_key,
                'job_id': job_id,
                'worker_ref': '%s:%s' % (side_cr.dbname, os.getpid()),
                'admitted_at': admitted_at,
                'expires_at': admitted_at + lifetime,
            })
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
        return lease_key, token, SimpleNamespace(
            id=store_id,
            shop_domain=shop_domain,
            api_version=api_version,
        )

    def _release_lease(self, lease_key):
        """Delete exactly the admitted lease on an independent side transaction.

        Runs in `execute_business.__exit__` on both normal and exception exit
        (analysis §9.1). Deletes only the one lease identified by its opaque key,
        commits independently, and always closes its cursor. It never swallows an
        exception (a failed release rolls back and re-raises) and never exposes a
        token or payload — the lease carries neither.
        """
        side_cr = self.env.registry.cursor()
        try:
            side_env = api.Environment(side_cr, self.env.uid, self.env.context)
            side_env['shopify.connector.call.lease'].search(
                [('lease_key', '=', lease_key)]
            ).unlink()
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()

    def _lease_worker_ref(self):
        """An opaque, non-secret diagnostic tag for the admitting worker.

        `<dbname>:<pid>` — never a token, never a credential.
        """
        return '%s:%s' % (self.env.cr.dbname, os.getpid())

    @api.model
    def _graphql_contains_mutation(self, document):
        """Conservative operation detector, not a string-prefix check."""
        if not isinstance(document, str):
            return False
        # Remove GraphQL comments and string literals so a word inside an
        # argument/comment cannot create a false operation classification.
        cleaned = re.sub(r'#[^\r\n]*', ' ', document)
        cleaned = re.sub(r'""".*?"""', ' ', cleaned, flags=re.S)
        cleaned = re.sub(r'"(?:\\.|[^"\\])*"', ' ', cleaned)
        return bool(re.search(r'(?<![A-Za-z0-9_])mutation(?![A-Za-z0-9_])', cleaned))

    @api.model
    def _validate_graphql_operation(
        self, document, variables, mutation_context=None,
    ):
        if not self._graphql_contains_mutation(document):
            return True
        if not isinstance(variables, dict):
            raise UserError('GraphQL mutation variables must be a dict.')
        context = dict(mutation_context or {})
        required = {
            'job_id', 'attempt_id', 'attempt_token', 'mutation_domain',
        }
        if required - set(context):
            raise UserError(
                'A GraphQL mutation requires a valid Layer 2 attempt context.'
            )
        side_cr = self.env.registry.cursor()
        try:
            side_cr.execute(
                "SELECT j.state, j.current_attempt_token, j.job_type, "
                "a.attempt_token, a.mutation_domain, a.transport_attempted, "
                "a.observed_outcome, a.idempotency_valid_until, "
                "a.exact_request_fingerprint, "
                "(SELECT count(*) FROM shopify_connector_mutation_attempt "
                "WHERE job_id = j.id) "
                "FROM shopify_connector_job j "
                "JOIN shopify_connector_mutation_attempt a "
                "ON a.job_id = j.id "
                "WHERE j.id = %s AND a.id = %s",
                (context['job_id'], context['attempt_id']),
            )
            row = side_cr.fetchone()
            expected_fingerprint = canonical_sha256({
                'operation': document,
                'variables': variables,
            })
            if (
                not row
                or row[0] != 'running'
                or row[1] != context['attempt_token']
                or row[2] != context['mutation_domain']
                or row[3] != context['attempt_token']
                or row[4] != context['mutation_domain']
                or not row[5]
                or row[6] != 'pending'
                or not row[7]
                or row[7] <= fields.Datetime.now()
                or row[8] != expected_fingerprint
                or row[9] != 1
            ):
                raise UserError(
                    'The Layer 2 mutation attempt context is stale or invalid.'
                )
            side_env = api.Environment(
                side_cr, self.env.uid, self.env.context,
            )
            if context['mutation_domain'] not in side_env[
                'shopify.connector.job.dispatch'
            ]._get_reconciliation_strategies():
                raise UserError(
                    'The mutation domain has no reconciliation strategy.'
                )
            side_cr.commit()
        except Exception:
            side_cr.rollback()
            raise
        finally:
            side_cr.close()
        return True

    @api.model
    def _send(self, store, body, token=None, mutation_context=None):
        """The only method containing an actual HTTP call.

        Sends an HTTPS POST to the store's versioned GraphQL endpoint
        with bounded timeouts. Returns the raw HTTP response object
        (status, headers, body) or raises a transport-level error (DNS,
        TLS, connect, timeout) that `execute()` normalizes. Never logs
        the request headers or body, and never interpolates the token
        into any raised error.

        `token` is the CORE-R2 single-snapshot contract: `execute_business`
        reads the token exactly once during admission and passes it here, so
        this method performs **no** credential re-read on that path. When
        `token is None` (the legacy `execute()` path, which still reads the
        token once for its own missing-credential pre-check) it is read here
        once, preserving the pre-existing transport-seam signature that tests
        patch as `_send(store, body)`.
        """
        self._validate_graphql_operation(
            body.get('query', ''),
            body.get('variables') or {},
            mutation_context,
        )
        if token is None:
            token = self.env[
                'shopify.connector.store.credential'
            ]._get_access_token(store)
        # The endpoint's version comes from the centralized connector
        # constant, never from the store row. A store whose recorded version
        # disagrees is a configuration block raised BEFORE the request, not a
        # request quietly addressed at a schema nothing here was verified
        # against.
        self._assert_configured_api_version(store)
        url = admin_graphql_endpoint(store.shop_domain)
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': token,
        }
        return requests.post(
            url,
            json=body,
            headers=headers,
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
        )

    # ------------------------------------------------------------------
    # Wave 5: the client-credentials token exchange
    # ------------------------------------------------------------------

    @api.model
    def _exchange_client_credentials(self, store, client_id, client_secret):
        """Exchange a Dev Dashboard app's credentials for an access token.

        Returns `(access_token, expires_at, granted_scope)`. Raises the
        accepted `ShopifyClientError` taxonomy on any failure -- never a bare
        exception, and never one carrying the secret, the token, or a raw
        response body.

        WHY THIS LIVES HERE. This model is the single transport boundary in
        this repository; `test_mutation_source_guards.py` enforces that with a
        repo-wide AST guard whose allowlist names one file, one verb and one
        owning function per sanctioned raw HTTP call. Putting the exchange in
        the credential model would have needed a second allowlist entry in a
        file that holds no other transport, which is precisely the drift the
        guard exists to prevent.

        WHAT THIS IS NOT. It is not OAuth as a distribution mechanism: there is
        no authorization URL, no redirect, no callback route, no controller and
        no state parameter, because the client-credentials grant has none of
        those. Nothing here implements public App Store distribution, billing
        or compliance webhooks, and this method must not grow toward them.

        Verified against Shopify's Dev Dashboard token documentation (accessed
        2026-07-29): POST to `/admin/oauth/access_token` on the shop's own
        domain, `application/x-www-form-urlencoded`, with `client_id`,
        `client_secret` and `grant_type=client_credentials`; the response
        carries `access_token`, `scope` and `expires_in` ("Always 86399").
        """
        if not store.shop_domain:
            raise UserError(
                'A shop domain is required before contacting Shopify.'
            )
        try:
            response = self._send_token_exchange(
                store, client_id, client_secret,
            )
        except requests.exceptions.RequestException as exc:
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail=redact(str(exc)),
            )
        status = getattr(response, 'status_code', 0)
        if 300 <= status < 400:
            # The token endpoint must answer on the validated store domain and
            # nowhere else. `_send_token_exchange` does not follow redirects, so
            # a 3xx arrives here as a response rather than as a secret already
            # re-posted somewhere unvalidated -- and it is refused. Classified
            # TEMPORARY, not AUTH: nothing has been learned about the
            # credential, so marking it invalid would be a false accusation.
            # `technical_detail` names the status only; the `Location` header is
            # deliberately not recorded, because a redirect target chosen by
            # whatever answered is not information this connector should store or
            # display.
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail=(
                    'token endpoint answered with a redirect (HTTP %s), which '
                    'is refused; the client secret was not re-sent' % status
                ),
            )
        if status in (400, 401, 403):
            # The app, the secret, or the app-store organisation pairing is
            # wrong. That is an authentication failure the merchant must fix by
            # correcting the credentials -- not something a retry resolves.
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                credential_invalid=True,
            )
        if status == 429:
            raise ShopifyClientError(
                error_class=ERROR_THROTTLE,
                reason=REASON_THROTTLED,
            )
        if status != 200:
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail='token endpoint returned HTTP %s' % status,
            )
        try:
            payload = response.json()
        except ValueError:
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail='token endpoint returned a non-JSON body',
            )
        token = (payload or {}).get('access_token')
        expires_in = (payload or {}).get('expires_in')
        if not token or not isinstance(token, str):
            raise ShopifyClientError(
                error_class=ERROR_AUTH,
                reason=REASON_TOKEN_INVALID,
                credential_invalid=True,
            )
        try:
            lifetime = int(expires_in)
        except (TypeError, ValueError):
            lifetime = 0
        if lifetime <= 0:
            # A token with no stated lifetime cannot be scheduled around.
            # Refusing it is safer than inventing an expiry the connector would
            # then treat as fact.
            raise ShopifyClientError(
                error_class=ERROR_TEMPORARY,
                reason=REASON_TEMPORARY,
                technical_detail='token endpoint returned no usable expiry',
            )
        expires_at = fields.Datetime.now() + timedelta(seconds=lifetime)
        granted_scope = (payload or {}).get('scope') or ''
        if not isinstance(granted_scope, str):
            granted_scope = ''
        return token, expires_at, granted_scope

    @api.model
    def _send_token_exchange(self, store, client_id, client_secret):
        """The only method containing the token-exchange HTTP call.

        Deliberately separate from `_send` and equally deliberately trivial:
        the repo-wide raw-transport guard allowlists exactly one verb in one
        named function per sanctioned call site, so keeping this to "build the
        request, post it, return the response" is what makes that allowlist
        entry reviewable. It parses nothing and raises nothing of its own --
        the caller owns the taxonomy -- and it is the seam tests patch, so no
        test ever needs a real credential or a live Shopify store.

        The secret travels in the request body over HTTPS and appears in no
        log, no header this connector records, and no exception.

        REDIRECTS ARE REFUSED, EXPLICITLY. `allow_redirects` defaults to **True**
        in Requests, for POST as much as for GET
        (https://requests.readthedocs.io/en/latest/api/, accessed 2026-07-30), so
        the absence of this argument was not a neutral omission: a 307 or 308
        response preserves the method and body, which means Requests would have
        re-POSTED the client secret to whatever `Location` the response named.
        A redirect target is not the validated store domain, and a client secret
        must reach exactly one host. `False` here means the 3xx is returned to
        `_exchange_client_credentials` as an ordinary response, where it is
        classified as a sanitized failure at the existing taxonomy boundary.

        `verify` is left at its default, which is TLS verification ON. It is
        named here only so that a future edit has to be deliberate about it.
        """
        url = 'https://%s/admin/oauth/access_token' % store.shop_domain
        return requests.post(
            url,
            data={
                'client_id': client_id,
                'client_secret': client_secret,
                'grant_type': 'client_credentials',
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
            },
            timeout=(_CONNECT_TIMEOUT_SECONDS, _READ_TIMEOUT_SECONDS),
            allow_redirects=False,
            verify=True,
        )

    @api.model
    def _assert_configured_api_version(self, store):
        """Refuse to send at all when the store's recorded version disagrees.

        Raised before the network call, so a misconfigured store never
        reaches Shopify rather than being caught on the way back. The
        recorded version is never *used* to build the endpoint — this check
        exists so a disagreement is surfaced as the configuration problem it
        is, instead of being silently overridden.
        """
        recorded = getattr(store, 'api_version', None)
        if recorded and recorded != SHOPIFY_API_VERSION:
            raise ShopifyClientError(
                error_class=ERROR_API_VERSION,
                reason=REASON_API_VERSION,
                technical_detail=redact(
                    'store api_version %s != connector %s' % (
                        recorded, SHOPIFY_API_VERSION,
                    )
                ),
                credential_invalid=False,
            )
        return True

    @api.model
    def _assert_served_api_version(self, response):
        """Fail closed on the served version, before any success is reported.

        Two failures, one disposition:

        * a **mismatch** means Shopify executed the request against a schema
          this connector was not verified against, so its response cannot be
          interpreted safely — including a `userErrors: []` that would
          otherwise read as success;
        * a **missing header** is the same uncertainty with no evidence
          either way, and a mutation path may not proceed on "probably the
          right version".

        Only the version strings appear in the diagnostic. No header, token
        or credential value is ever included: `redact()` is applied on top of
        a message that already contains none.
        """
        headers = getattr(response, 'headers', None) or {}
        try:
            served = headers.get(API_VERSION_RESPONSE_HEADER)
        except Exception:
            served = None
        if not served:
            raise ShopifyClientError(
                error_class=ERROR_API_VERSION,
                reason=REASON_API_VERSION,
                technical_detail=redact(
                    'no %s header on the response; expected %s' % (
                        API_VERSION_RESPONSE_HEADER, SHOPIFY_API_VERSION,
                    )
                ),
                credential_invalid=False,
            )
        if served != SHOPIFY_API_VERSION:
            raise ShopifyClientError(
                error_class=ERROR_API_VERSION,
                reason=REASON_API_VERSION,
                technical_detail=redact(
                    'served api version %s != connector %s' % (
                        served, SHOPIFY_API_VERSION,
                    )
                ),
                credential_invalid=False,
            )
        return served

    def _safe_text(self, response):
        try:
            return response.text or ''
        except Exception:
            return ''

    def _technical_detail(self, response, extra=None):
        parts = ['HTTP %s' % getattr(response, 'status_code', 'unknown')]
        if extra:
            parts.append(str(extra))
        body_excerpt = self._safe_text(response)
        if body_excerpt:
            parts.append(body_excerpt)
        return redact(' '.join(parts))

    def _parse_throttle_status(self, body):
        # Verbatim official field names; never hard-coded bucket sizes
        # (MBQ-51 stays untouched -- this only surfaces the signal).
        extensions = body.get('extensions') or {}
        cost = extensions.get('cost') or {}
        throttle_status = cost.get('throttleStatus')
        if not throttle_status:
            return None
        return {
            'maximumAvailable': throttle_status.get('maximumAvailable'),
            'currentlyAvailable': throttle_status.get('currentlyAvailable'),
            'restoreRate': throttle_status.get('restoreRate'),
        }

    def _error_from_graphql_errors(self, errors, response):
        first_error = errors[0] if errors else {}
        extensions = first_error.get('extensions') or {}
        code = extensions.get('code')
        request_id = extensions.get('requestId')
        extra = (
            'requestId=%s' % request_id
            if request_id else first_error.get('message')
        )
        technical_detail = self._technical_detail(response, extra=extra)
        if code == 'ACCESS_DENIED':
            return ShopifyClientError(
                ERROR_AUTH, REASON_TOKEN_INVALID, technical_detail,
                credential_invalid=True,
            )
        if code == 'SHOP_INACTIVE':
            return ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_INACTIVE, technical_detail,
                credential_invalid=False,
            )
        if code == 'THROTTLED':
            return ShopifyClientError(
                ERROR_THROTTLE, REASON_THROTTLED, technical_detail,
                credential_invalid=False,
            )
        if code == 'INTERNAL_SERVER_ERROR':
            return ShopifyClientError(
                ERROR_TEMPORARY, REASON_TEMPORARY, technical_detail,
                credential_invalid=False,
            )
        # MAX_COST_EXCEEDED on this tiny query, and anything unclassifiable
        # (incl. an unknown extensions.code), fall to the single
        # safety-net path per DEC-009 -- no 17th class is introduced.
        return ShopifyClientError(
            ERROR_UNKNOWN, REASON_UNKNOWN, technical_detail,
            credential_invalid=False,
        )

    def _normalize_response(self, store, response):
        status_code = getattr(response, 'status_code', None)
        if status_code == 401:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_TOKEN_INVALID,
                self._technical_detail(response), credential_invalid=True,
            )
        if status_code == 402:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_FROZEN,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code == 423:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_LOCKED,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code == 403:
            raise ShopifyClientError(
                ERROR_AUTH, REASON_SHOP_FRAUDULENT,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code == 429:
            raise ShopifyClientError(
                ERROR_THROTTLE, REASON_THROTTLED,
                self._technical_detail(response), credential_invalid=False,
            )
        if isinstance(status_code, int) and status_code >= 500:
            raise ShopifyClientError(
                ERROR_TEMPORARY, REASON_TEMPORARY,
                self._technical_detail(response), credential_invalid=False,
            )
        if status_code != 200:
            raise ShopifyClientError(
                ERROR_UNKNOWN, REASON_UNKNOWN,
                self._technical_detail(response), credential_invalid=False,
            )

        try:
            body = response.json()
        except ValueError:
            raise ShopifyClientError(
                ERROR_UNKNOWN, REASON_UNKNOWN,
                self._technical_detail(response), credential_invalid=False,
            )
        if not isinstance(body, dict):
            raise ShopifyClientError(
                ERROR_UNKNOWN, REASON_UNKNOWN,
                self._technical_detail(response), credential_invalid=False,
            )

        errors = body.get('errors')
        if errors:
            raise self._error_from_graphql_errors(errors, response)

        # The version gate runs AFTER the transport/GraphQL error taxonomy so
        # a 401 or a THROTTLED response keeps its own accurate
        # classification, and BEFORE any result is returned so no caller can
        # act on a body served by an unverified schema.
        served_version = self._assert_served_api_version(response)
        throttle_status = self._parse_throttle_status(body)
        # TD-014. The single choke point every successful Shopify response
        # passes through, for every domain and both read and mutation
        # paths, so this is where the rate signal becomes durable state.
        # It was parsed here and returned to callers that ignored it,
        # which is why PERF-1's backpressure lever could never fire: no
        # production code had ever written `api_health_state='throttled'`.
        #
        # Recording is best-effort by construction. A store row that
        # cannot be written must never turn a good Shopify response into
        # a failure, so the result is returned regardless.
        if throttle_status and store:
            try:
                store._record_throttle_status(throttle_status)
            except Exception:  # noqa: BLE001 - see above
                _logger.exception(
                    'Could not record Shopify rate head-room for store %s; '
                    'the response itself is unaffected.', store.id,
                )
        return {
            'data': body.get('data'),
            'throttle_status': throttle_status,
            'served_version': served_version,
        }
