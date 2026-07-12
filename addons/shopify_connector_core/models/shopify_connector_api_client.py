import os
import uuid
from contextlib import contextmanager
from datetime import timedelta

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.redaction import redact

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
        None>}`, optionally with `version_fallforward`/`served_version`
        keys on an API-version header mismatch (never raised as an
        error). Raises `ShopifyClientError` on any transport or
        GraphQL-level failure.
        """
        if not store.shop_domain or not store.api_version:
            raise UserError(
                'A shop domain and API version are required before '
                'contacting Shopify.'
            )
        token = self.env['shopify.connector.store.credential']._get_access_token(
            store
        )
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

    @contextmanager
    def execute_business(self, job, store, query, variables=None):
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
        if not store.shop_domain or not store.api_version:
            raise UserError(
                'A shop domain and API version are required before '
                'contacting Shopify.'
            )
        # _admit reads the token once and raises the accepted taxonomy on a
        # missing credential (ShopifyClientError) or fails closed on the gate
        # (ShopifyQuiescedError) -- in either case before any lease exists, so no
        # release is owed here.
        lease_key, token = self._admit(job, store)
        try:
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
            result = self._normalize_response(store, response)
            yield result
        except BaseException as primary_error:
            # Precedence: the primary (body/send/normalization/caller) exception
            # is preserved; a release failure is chained, never substituted.
            try:
                self._release_lease(lease_key)
            except BaseException as release_error:
                raise primary_error from release_error
            raise primary_error
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
    def _send(self, store, body, token=None):
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
        if token is None:
            token = self.env[
                'shopify.connector.store.credential'
            ]._get_access_token(store)
        url = 'https://%s/admin/api/%s/graphql.json' % (
            store.shop_domain, store.api_version,
        )
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
        extra = 'requestId=%s' % request_id if request_id else first_error.get('message')
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

        result = {
            'data': body.get('data'),
            'throttle_status': self._parse_throttle_status(body),
        }
        served_version = None
        headers = getattr(response, 'headers', None) or {}
        try:
            served_version = headers.get('X-Shopify-API-Version')
        except Exception:
            served_version = None
        if served_version and served_version != store.api_version:
            result['version_fallforward'] = True
            result['served_version'] = served_version
        return result
