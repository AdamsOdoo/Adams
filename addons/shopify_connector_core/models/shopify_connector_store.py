import json
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.redaction import redact
from .shopify_connector_api_client import (
    ERROR_AUTH,
    LIFECYCLE_PURPOSE_STATES,
    ShopifyClientError,
)
from .shopify_connector_job import BUSINESS_JOB_SOURCES
from .shopify_connector_job_dispatch import (
    DISCONNECT_QUIESCE_TIMEOUT,
    POLL_DELAY,
)

# CORE-R2 Slice 2A: the disconnect controller's `timed_out` escalation snapshot
# records at most this many outstanding holders (opaque lease_key + Integer
# job_id only -- never a token/credential/payload) into the audited
# `disconnect_status_reason`, keeping the operator-facing escalation bounded
# (analysis §16). Named, not an inlined magic number.
_ESCALATION_SNAPSHOT_LIMIT = 20

# The controller cron xml-id (`data/shopify_connector_cron_disconnect.xml`),
# resolved when Phase 1 wakes the controller and when a still-quiescing store
# schedules its delayed re-poll.
_DISCONNECT_CRON_XMLID = (
    'shopify_connector_core.ir_cron_shopify_connector_disconnect_quiesce'
)

# The read-only test-connection query (Task 003) -- confirmed in the
# 2026-07 official reference (Facts #7/#8,
# credential-connection-api-client-planning.md); no mutation, no
# variables needed.
TEST_CONNECTION_QUERY = """
query ConnectorTestConnection {
  shop { id name myshopifyDomain }
  currentAppInstallation { accessScopes { handle } }
}
"""


class ShopifyConnectorStore(models.Model):
    """The DEC-006 store-scoping anchor every other core model references.

    Holds connection lifecycle, API version/health, and readiness
    metadata, plus non-secret credential status mirrors only. This
    model stores no secret value itself: the credential presence flag,
    replacement/verification timestamps, failure reason, and
    granted-scope snapshot below are all non-secret status mirrors,
    written only by the credential service (Task 002). The actual
    secret credential value is persisted exclusively on the dedicated
    Admin-only `shopify.connector.store.credential` model.
    """

    _name = 'shopify.connector.store'
    _description = 'Shopify Connector Store'

    name = fields.Char(required=True)
    shop_domain = fields.Char(required=True, index=True, readonly=True)
    state = fields.Selection(
        selection=[
            ('setup_incomplete', 'Setup Incomplete'),
            ('connected', 'Connected'),
            ('reconnect_needed', 'Reconnect Needed'),
            # CORE-R2 (AR-047): the two-phase disconnect intermediate state. A
            # store enters `disconnecting` at Phase-1 `action_disconnect` and is
            # finalized to `disconnected` by the quiescence controller once its
            # committed admission-lease count reaches zero (`completed`) or the
            # bounded timeout fires (`timed_out`). Non-startable and
            # non-enqueueable for business jobs, and lifecycle-mutation-refusing,
            # exactly like the never-connected states (analysis §8/§13).
            ('disconnecting', 'Disconnecting'),
            ('disconnected', 'Disconnected'),
        ],
        required=True,
        index=True,
        default='setup_incomplete',
        readonly=True,
    )
    api_version = fields.Char(required=True)
    api_health_state = fields.Selection(
        selection=[
            ('normal', 'Normal'),
            ('throttled', 'Throttled'),
            ('degraded', 'Degraded'),
        ],
        readonly=True,
    )
    api_health_reason = fields.Char(readonly=True)
    webhook_ready = fields.Boolean(default=False, readonly=True)
    last_test_connection_result = fields.Selection(
        selection=[('pass', 'Pass'), ('fail', 'Fail')],
        readonly=True,
    )
    last_test_connection_at = fields.Datetime(readonly=True)
    last_test_connection_reason = fields.Char(readonly=True)
    last_readiness_result = fields.Selection(
        selection=[('pass', 'Pass'), ('fail', 'Fail'), ('warning', 'Warning')],
        readonly=True,
    )
    last_readiness_at = fields.Datetime(readonly=True)
    credential_present = fields.Boolean(default=False, readonly=True)
    credential_last_verified_at = fields.Datetime(readonly=True)
    credential_last_replaced_at = fields.Datetime(readonly=True)
    credential_last_failure_reason = fields.Char(readonly=True)
    granted_scopes = fields.Text(readonly=True)
    granted_scopes_checked_at = fields.Datetime(readonly=True)
    # CORE-R2 (AR-047) persisted connection epoch. Monotonic per store; a
    # business job captures it at enqueue (`expected_connection_generation`) and
    # `execute_business` admission refuses any call whose captured epoch no longer
    # matches this value. Additive and inert in this foundation slice: it is read
    # by admission and captured at enqueue, but NO lifecycle transition bumps it
    # yet and NO state change is introduced here — the disconnect/reconnect
    # generation-bump protocol is a later CORE-R2 slice. Existing rows backfill to
    # 0 (matching a never-cycled store, analysis §22).
    connection_generation = fields.Integer(
        default=0,
        required=True,
        readonly=True,
    )
    # CORE-R2 (AR-047; analysis §11) two-phase disconnect status + escalation
    # snapshot fields. All additive and non-secret. `disconnect_status` is the
    # controller-observable lifecycle sub-state; the `*_lease_count` /
    # `*_oldest_admitted_at` pair is the escalation snapshot the controller
    # writes each pass; the `*_requested_at`/`*_by` pair records the Phase-1
    # request; `*_completed_at` stamps the `completed`/`timed_out` finalize.
    # Existing rows backfill to `disconnect_status='none'` (a never-disconnected
    # store) and the rest empty/zero.
    disconnect_status = fields.Selection(
        selection=[
            ('none', 'None'),
            ('requested', 'Requested'),
            ('quiescing', 'Quiescing'),
            ('completed', 'Completed'),
            ('timed_out', 'Timed Out'),
        ],
        default='none',
        required=True,
        readonly=True,
    )
    disconnect_status_reason = fields.Char(readonly=True)
    disconnect_open_lease_count = fields.Integer(default=0, readonly=True)
    disconnect_oldest_admitted_at = fields.Datetime(readonly=True)
    disconnect_requested_at = fields.Datetime(readonly=True)
    disconnect_requested_by = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        ondelete='set null',
    )
    disconnect_completed_at = fields.Datetime(readonly=True)

    _shop_domain_uniq = models.Constraint(
        'UNIQUE(shop_domain)',
        'A store already exists for this Shopify shop domain.',
    )

    def action_test_connection(self):
        """Run one read-only Shopify test-connection check (Task 003).

        Admin-invoked (store write access is Admin-only per the merged
        ACL, so this is enforced by the existing ACL, not a new guard).
        Thin public wrapper over the shared `_run_connection_probe` with the
        INTERNAL purpose `'test_connection'` -- never a caller/RPC-controlled
        purpose. The frozen matrix refuses it while the store is `disconnecting`
        **or** `disconnected` (analysis §8/§9.1); `reconnect_probe` is the sibling
        purpose used by `action_reconnect` for the finalized `disconnected` state.
        """
        self.ensure_one()
        # `_run_connection_probe` returns `'superseded'` when a concurrent
        # lifecycle/credential change discarded the result; Test Connection has no
        # further step, so return None (the accepted RPC contract) either way.
        self._run_connection_probe('test_connection')
        return None

    def _run_connection_probe(self, purpose):
        """Shared read-only connection probe (Task 003 + CORE-R2; reviews
        4690639375 #2 + 4690804619 #1).

        The single implementation behind `action_test_connection`
        (`purpose='test_connection'`) and `action_reconnect`
        (`purpose='reconnect_probe'`). `purpose` is a fixed INTERNAL enum chosen
        by those two trusted callers -- it is **not** a caller/RPC-controlled
        value. Identical transport, normalization, mirror, and audit behavior for
        both purposes; only the allowed-state matrix differs
        (`LIFECYCLE_PURPOSE_STATES`): `test_connection` excludes `disconnected`,
        `reconnect_probe` permits it (reconnect after completed disconnect,
        matrix §8), and neither permits `disconnecting`.

        **One credential snapshot per probe (review 4690804619 #1).** The probe
        binds to exactly one credential snapshot via `_admit_lifecycle` (a single
        token read + the credential id/version + the store generation) and issues
        the request through `_send_lifecycle(store, query, token)` with that exact
        token -- the transport re-reads **no** credential. After the network
        result (success **or** failure), `_lifecycle_probe_superseded` acquires the
        store->credential locks and revalidates state, generation, and credential
        version; if a lifecycle or credential change won during the call the
        response is **discarded** and the probe is audited as **superseded**
        (job cancelled, **no** verification/failure mirror and **no** credential
        state written). No lock spans the network call. Returns `'superseded'` in
        that case (so `action_reconnect` aborts), else `None`.

        The matrix is pre-checked here **before** any audit job is created (so a
        refused probe never leaves a dangling `running` job) and re-enforced in
        `_admit_lifecycle` as defense in depth. Creates exactly one
        `job_type='core_test_connection'` job per run with a fresh UUID4
        `payload_hash` nonce; writes only the store mirrors, the credential's
        `credential_state` (only for a genuine token-invalid signal), and the
        job/job.log rows -- never the token.
        """
        self.ensure_one()
        allowed_states = LIFECYCLE_PURPOSE_STATES.get(purpose)
        if allowed_states is None:
            raise UserError(
                'An unknown connection-probe purpose was requested.'
            )
        if self.state not in allowed_states:
            raise UserError(
                'A connection check is not available while the store is '
                '"%s".' % self.state
            )
        if not self.credential_present:
            raise UserError(
                'Enter a credential before testing the connection.'
            )
        Client = self.env['shopify.connector.api.client']
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job = Job.create({
            'store_id': self.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_test_connection',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', 'Test connection attempt started.',
        )

        # CORE-R2 (review 4690804619 #1): bind the probe to ONE credential
        # snapshot and send with exactly that token (no second credential read on
        # the transport). A missing-token/bad-state admit failure is pre-network
        # (no snapshot, no stale result); a transport ShopifyClientError still
        # goes through the post-network revalidation below.
        snapshot = None
        try:
            snapshot = Client._admit_lifecycle(self, purpose)
            result = Client._send_lifecycle(
                self, TEST_CONNECTION_QUERY, snapshot['token'],
            )
            probe_error = None
        except ShopifyClientError as exc:
            result = None
            probe_error = exc

        # Post-network revalidation: discard a result the snapshot no longer
        # backs, and audit it as superseded -- writing NO mirror/credential state.
        if snapshot is not None and self._lifecycle_probe_superseded(snapshot):
            self._audit_probe_superseded(job)
            return 'superseded'

        if probe_error is not None:
            self._apply_probe_failure(job, probe_error)
            return None

        data = result.get('data') or {}
        shop = data.get('shop') or {}
        if shop.get('myshopifyDomain') != self.shop_domain:
            reason = (
                "The connected Shopify store does not match this "
                "store's configured domain — check the domain and "
                "reconnect."
            )
            self.write({
                'last_test_connection_result': 'fail',
                'last_test_connection_at': fields.Datetime.now(),
                'last_test_connection_reason': redact(reason),
            })
            job.write({
                'error_class': 'odoo_validation_configuration',
                'state': 'failed_final',
                'finished_at': fields.Datetime.now(),
            })
            JobLog._system_append(
                job, 'attempt', redact(reason),
                from_state='running', to_state='failed_final',
            )
            return None

        access_scopes = (
            data.get('currentAppInstallation') or {}
        ).get('accessScopes') or []
        self.write({
            'last_test_connection_result': 'pass',
            'last_test_connection_at': fields.Datetime.now(),
            'last_test_connection_reason': False,
            'credential_last_verified_at': fields.Datetime.now(),
            'granted_scopes': json.dumps(
                [scope['handle'] for scope in access_scopes]
            ),
            'granted_scopes_checked_at': fields.Datetime.now(),
        })
        if result.get('version_fallforward'):
            self.write({
                'api_health_state': 'degraded',
                'api_health_reason': redact(
                    'Shopify served API version %s instead of the '
                    'configured %s.' % (
                        result.get('served_version'), self.api_version,
                    )
                ),
            })
        else:
            # D-R1-5 (Task CORE-R1): a fully successful test connection
            # with no API-version fall-forward is the healthy API state --
            # record 'normal' so the unchanged _check_api_version_health
            # readiness check can pass on real evidence (no merged path
            # wrote 'normal' before this, leaving the field NULL and
            # readiness permanently fail-closed). Also clear any stale
            # api_health_reason a prior fall-forward 'degraded' write left
            # behind, so a recovered store never keeps contradictory,
            # operator-facing degradation evidence. The 'degraded'
            # fall-forward path above is untouched.
            self.write({
                'api_health_state': 'normal',
                'api_health_reason': False,
            })
        job.write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt',
            'Connection verified with %s.' % shop.get('name'),
            from_state='running', to_state='succeeded',
        )
        return None

    def _apply_probe_failure(self, job, exc):
        """Write the shared probe-failure mirrors + job/log for a
        `ShopifyClientError` (CORE-R2; extracted from `_run_connection_probe`).

        Runs only after the post-network revalidation confirmed the snapshot still
        holds (never from a superseded result). Writes the fail mirrors, flips the
        credential's `credential_state` to `invalid` **only** on a genuine
        token-invalid signal, and -- for any auth/permission/scope class (Task 005 /
        DEC-022 §4.7), not only a token-invalid one -- moves the store to
        `reconnect_needed` via the TOCTOU-safe `action_mark_reconnect_needed`
        (which itself refuses to overwrite a one-way disconnect). Never logs the
        token.
        """
        self.ensure_one()
        JobLog = self.env['shopify.connector.job.log']
        self.write({
            'last_test_connection_result': 'fail',
            'last_test_connection_at': fields.Datetime.now(),
            'last_test_connection_reason': redact(exc.reason),
        })
        if exc.credential_invalid:
            credential = self.env[
                'shopify.connector.store.credential'
            ].search([('store_id', '=', self.id)], limit=1)
            if credential:
                credential.write({'credential_state': 'invalid'})
        if exc.credential_invalid or exc.error_class == ERROR_AUTH:
            self.action_mark_reconnect_needed(reason=exc.reason)
        job.write({
            'error_class': exc.error_class,
            'state': 'failed_final',
            'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', redact(exc.reason),
            technical_detail=exc.technical_detail,
            from_state='running', to_state='failed_final',
        )
        return None

    def _lifecycle_probe_superseded(self, snapshot):
        """Return True if a lifecycle/credential change superseded the probe
        (CORE-R2, AR-047; review 4690804619 #1).

        Runs **after** the network result. Acquires the store-row lifecycle lock
        first (`_lock_store_for_lifecycle`, `FOR NO KEY UPDATE`), then the
        credential-row lock (`_lifecycle_credential_version(lock=True)`) -- the
        global `store -> credential` order -- and compares the freshly-locked
        values against the pre-network `snapshot`:

        - the locked state left the `purpose`'s allowed matrix (e.g. a disconnect
          moved it to `disconnecting`);
        - the `connection_generation` changed (an activation/reconnect/disconnect
          or a connected credential replace won the race);
        - the credential row vanished, or its identity/version (`id`,
          `write_date`) changed (a set/replace/clear happened);
        - the credential **value** changed from the snapshot token -- the
          definitive signal for a same-row replace whose `write_date` PostgreSQL
          may fix to the transaction timestamp (so an equal-value or same-txn
          replacement is still caught).

        Any of these means the network response no longer describes the current
        credential/store, so the caller discards it. The lock is taken only here
        (after the network), never across the network call, and -- once acquired --
        is held to the request-boundary commit so the subsequent mirror write is
        TOCTOU-safe. The token compared here is the in-memory snapshot value; it is
        never logged or persisted.
        """
        self.ensure_one()
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if locked_state not in snapshot['allowed_states']:
            return True
        if locked_generation != snapshot['generation']:
            return True
        Credential = self.env['shopify.connector.store.credential']
        current = Credential._lifecycle_credential_version(self, lock=True)
        if not current:
            return True
        if current[0] != snapshot['credential_id']:
            return True
        if current[1] != snapshot['credential_version']:
            return True
        # Value revalidation under the held credential-row lock: any set/replace
        # changes the stored value even when its write_date is transaction-fixed.
        if Credential._get_access_token(self) != snapshot['token']:
            return True
        return False

    def _audit_probe_superseded(self, job):
        """Cancel a superseded probe job; write NO store/credential mirror
        (CORE-R2, AR-047; review 4690804619 #1).

        Uses the existing terminal `cancelled` state + `cancel_reason` taxonomy
        (writes to `cancelled` are never store-state-gated) with the required
        empty `manual_review_subreason`, and appends the audit log row. Deliberately
        writes **no** verification/failure mirror and **no** credential state -- the
        whole point of a superseded probe is that its result must not touch the
        store's connection evidence.
        """
        self.ensure_one()
        JobLog = self.env['shopify.connector.job.log']
        reason = (
            'Connection probe superseded by a lifecycle or credential '
            'change; rerun it.'
        )
        job.write({
            'state': 'cancelled',
            'cancel_reason': reason,
            'finished_at': fields.Datetime.now(),
            'manual_review_subreason': False,
        })
        JobLog._system_append(
            job, 'state_change', reason,
            from_state='running', to_state='cancelled',
        )
        return None

    # ------------------------------------------------------------------
    # Task 005: connection lifecycle actions (DEC-022 / gate document)
    # ------------------------------------------------------------------

    def _create_lifecycle_audit_job(self, message):
        """Create + close one audited `core_manual_maintenance` job.

        The single sanctioned audit-trail path every lifecycle action
        below funnels through. `job_source='setup_readiness_check'` keeps
        this on the existing core/diagnostic source vocabulary (so it is
        never itself business-job-gated); a fresh UUID4 `payload_hash`
        nonce mirrors the already-accepted `action_test_connection`/
        `run_for_store` pattern so repeat lifecycle actions never collide
        on `store_idempotency_key_uniq` (the TD-001 class of issue); every
        log row goes through the existing `_system_append` path -- no new
        job type, no second log-creation path, no `sudo()`.
        """
        self.ensure_one()
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        job = Job.create({
            'store_id': self.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_manual_maintenance',
            'state': 'running',
            'payload_hash': str(uuid.uuid4()),
            'started_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'manual_action', message,
            from_state='running', to_state='succeeded',
        )
        job.write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        return job

    def action_activate(self):
        """Transition to `connected` -- only on real Task 003/004 evidence.

        Never infers success: requires a credential currently on record
        (not merely a stale pass mirror left over from before a
        disconnect -- `action_disconnect` clears `credential_present`
        but does not reset `last_test_connection_result`/
        `last_readiness_result`, so this check is the guard against
        re-activating a credential-less store on old evidence) and that
        the current credential has actually been verified
        (`credential_last_verified_at` truthy). `action_set_token` and
        `action_replace_token` both clear this stamp on every token
        set/update, closing the stale-evidence path at the credential-
        service source. This method deliberately does **not** compare
        the credential row's own `write_date` -- an earlier revision did,
        but real DB write timing on Odoo.sh proved that guard brittle,
        rejecting valid activations. It also requires the stored
        readiness result to be at least as fresh as that verification
        (`last_readiness_at` truthy and not older than
        `credential_last_verified_at`) -- otherwise a readiness pass
        recorded *before* the current credential was verified could
        incorrectly count as evidence for it. Neither the credential-row
        search nor anything else here reads or logs `access_token`, nor
        uses `sudo()` -- the search runs as the calling (Admin) user,
        exactly as the rest of this model's credential-adjacent reads
        already do. If any check fails, raises `UserError` and leaves
        the state untouched -- never calls Shopify, never runs OAuth,
        and never claims VAL-B2 has passed or that MBQ-05 is resolved
        (DEC-022 §4.4).
        """
        self.ensure_one()
        # CORE-R2 (AR-047; review 4690639375 #1): take the conflicting store-row
        # update lock FIRST, then validate every state-dependent precondition
        # against the fresh state read UNDER that lock (TOCTOU-safe). A disconnect
        # that won the race is observed here and refused -- disconnect is one-way,
        # activation must never overwrite `disconnecting`/`disconnected`. No
        # Shopify call is made while the lock is held (only stored evidence is
        # read); `connection_generation` is bumped exactly once, only on success.
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if locked_state in ('disconnecting', 'disconnected'):
            raise UserError(
                'Cannot activate: a disconnect is in progress or has completed '
                'for this store.'
            )
        if not self.credential_present:
            raise UserError(
                'Cannot activate: no credential is present for this '
                'store -- enter a credential first.'
            )
        credential = self.env['shopify.connector.store.credential'].search(
            [('store_id', '=', self.id)], limit=1
        )
        if not credential:
            raise UserError(
                'Cannot activate: no credential record exists for this '
                'store -- enter a credential first.'
            )
        if not self.credential_last_verified_at:
            raise UserError(
                'Cannot activate: the current credential has not been '
                'verified yet — run Test Connection first.'
            )
        if self.last_test_connection_result != 'pass':
            raise UserError(
                'Cannot activate: no passing test-connection result is '
                'recorded for this store yet -- run Test Connection first.'
            )
        if self.last_readiness_result not in ('pass', 'warning'):
            raise UserError(
                'Cannot activate: no passing or warning-tier readiness '
                'result is recorded for this store yet -- run the '
                'readiness check first.'
            )
        if (
            not self.last_readiness_at
            or self.last_readiness_at < self.credential_last_verified_at
        ):
            raise UserError(
                'Cannot activate: readiness has not been checked after '
                'the current credential was verified — run the '
                'readiness check first.'
            )
        # Consume the generation read under the held lock and bump it exactly
        # once -- the single successful-activation transition (analysis §8/§9.2).
        self.write({
            'state': 'connected',
            'connection_generation': locked_generation + 1,
        })
        self._create_lifecycle_audit_job(
            'Store activated (test-connection: %s, readiness: %s).' % (
                self.last_test_connection_result, self.last_readiness_result,
            )
        )
        return None

    # ------------------------------------------------------------------
    # CORE-R2 (AR-047): generation-changing lifecycle store-row lock
    # ------------------------------------------------------------------

    def _lock_store_for_lifecycle(self):
        """Acquire the conflicting store-row update lock and fresh-read under it.

        The lifecycle half of the CORE-R2 store-row lock protocol (analysis
        §9.2 / INV-2L). Every generation-changing lifecycle transition
        (disconnect request, activation, reconnect) runs this first, on the
        **request/main cursor**, to take a **blocking** ``SELECT … FOR NO KEY
        UPDATE`` on this store row: it conflicts with -- and therefore waits for
        -- any in-flight admission's brief ``FOR SHARE`` (`_admit`), and
        conflicts with any other lifecycle/finalize update lock, so admission and
        every generation-changing transition **linearize** on the row. Unlike
        Odoo's ``lock_for_update`` (which issues ``FOR UPDATE SKIP LOCKED`` and
        would silently skip a locked row) this waits, because a lifecycle
        transition must not be skipped. A prior ``flush_recordset`` guarantees the
        raw ``SELECT`` observes this transaction's own pending state/generation
        writes; ``invalidate_recordset`` afterwards forces the subsequent field
        reads to come from the freshly-locked row. The lock is released by the
        natural RPC/cron-boundary commit -- **never** an explicit main-cursor
        ``commit`` -- and is never held across a Shopify network call. Only the
        store row is locked here; a path that also touches the credential row
        locks **store first, then credential** (one global order -> deadlock-free,
        §9.2). Returns the fresh ``(state, connection_generation)`` read under the
        lock.
        """
        self.ensure_one()
        # Flush this store's pending ORM writes so the raw locking SELECT below
        # observes the current transaction's own state/generation, then
        # invalidate afterwards so subsequent field reads come from the freshly
        # locked row (the sanctioned Odoo raw-SQL discipline).
        self.flush_recordset()
        self.env.cr.execute(
            "SELECT state, connection_generation "
            "FROM shopify_connector_store WHERE id = %s FOR NO KEY UPDATE",
            (self.id,),
        )
        row = self.env.cr.fetchone()
        self.invalidate_recordset()
        return row

    def _sweep_quiescing_business_jobs(self, reason):
        """Non-blocking A/B sweep of this store's cancellable business jobs.

        Cancels only the **queued** / **retry_waiting** business jobs (the A/B
        rows of the in-flight taxonomy, analysis §3) that can be row-locked
        **without blocking**, via ``try_lock_for_update`` (``FOR UPDATE SKIP
        LOCKED``). A job a concurrent drain holds (row C -- claimed/running) is
        **skipped**, never blocked and never written, so the sweep issues **no**
        write to a locked running/claimed job row (INV-9, packet §6/§14). All job
        history is preserved (cancel, never delete); a job leaving
        ``blocked_manual_review`` -- not swept here, but guarded regardless -- has
        its ``manual_review_subreason`` cleared so the terminal transition never
        violates ``_check_manual_review_subreason_required``. Runs in Phase 1 and
        again in each controller pass; both are non-blocking and idempotent.
        """
        self.ensure_one()
        Job = self.env['shopify.connector.job']
        JobLog = self.env['shopify.connector.job.log']
        candidates = Job.search([
            ('store_id', '=', self.id),
            ('job_source', 'in', list(BUSINESS_JOB_SOURCES)),
            ('state', 'in', ('queued', 'retry_waiting')),
        ])
        if not candidates:
            return
        locked = candidates.try_lock_for_update()
        if not locked:
            return
        locked.invalidate_recordset()
        for job in locked:
            if job.state not in ('queued', 'retry_waiting'):
                continue
            from_state = job.state
            job.write({
                'state': 'cancelled',
                'cancel_reason': reason,
                'finished_at': fields.Datetime.now(),
                'manual_review_subreason': False,
            })
            JobLog._system_append(
                job, 'state_change', 'Job cancelled: %s' % reason,
                from_state=from_state, to_state='cancelled',
            )

    def _trigger_disconnect_controller(self, at=None):
        """Wake the disconnect quiescence controller cron.

        A one-shot wake after a Phase-1 request (``at=None`` -> immediate) or a
        **delayed** re-poll for a still-quiescing store (``at=now+POLL_DELAY``,
        analysis §14). Never an immediate same-store re-trigger from within a
        quiescing pass (that would busy-loop); duplicate triggers are harmless
        (each controller pass re-selects under SKIP LOCKED and finalize is
        idempotent). Missing-cron tolerant so a lifecycle action never hard-fails
        if the cron record is absent (e.g. in a stripped test registry).
        """
        self.ensure_one()
        cron = self.env.ref(_DISCONNECT_CRON_XMLID, raise_if_not_found=False)
        if not cron:
            return
        if at is None:
            cron._trigger()
        else:
            cron._trigger(at=at)

    def action_disconnect(self):
        """Phase 1 of the two-phase CORE-R2 disconnect (AR-047; analysis §4/§6/§8).

        Requests quiescence -- it does **not** complete the disconnect. On a
        store that is not already `disconnecting`/`disconnected`:

        1. take the conflicting store-row update lock and fresh-read under it
           (`_lock_store_for_lifecycle`);
        2. bump `connection_generation` exactly once -- so **no new business
           Shopify call can be admitted** (the `execute_business` epoch gate
           refuses any job whose captured epoch no longer matches) and no
           business job can start;
        3. transition `state` -> `disconnecting`, `disconnect_status` ->
           `requested`, and stamp `disconnect_requested_at`/`_by`;
        4. run **one** non-blocking A/B (queued/retry_waiting) business-job sweep;
        5. wake the quiescence controller and return "request accepted".

        It deliberately does **not** clear the credential, does **not** wait for
        lease holders, does **not** write a locked running job row, and issues no
        explicit main-cursor commit. The controller (`_run_disconnect_quiesce`)
        later finalizes to `completed` (zero committed leases) or `timed_out`
        (leases still present at the deadline) and clears the credential **then**
        (analysis §15). A repeated disconnect while already
        `disconnecting`/`disconnected` is an **audited idempotent no-op**
        (matrix §8). Disconnect is one-way.
        """
        self.ensure_one()
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if locked_state in ('disconnecting', 'disconnected'):
            self._create_lifecycle_audit_job(
                'Disconnect requested; store already %s -- audited no-op.'
                % locked_state
            )
            return None
        self._request_disconnect_locked(locked_state, locked_generation)
        return None

    def _request_disconnect_locked(self, locked_state, locked_generation):
        """Phase-1 disconnect request body, run UNDER the held store lifecycle
        lock (CORE-R2, AR-047; reviews 4690804619 §11 + 4690807427).

        The caller must already hold `_lock_store_for_lifecycle` and pass the
        `(state, generation)` it read under that lock; this consumes them directly
        -- bumping `connection_generation` to **`locked_generation + 1`** (the
        value returned under the lock, never an indirect re-read of the field) --
        so **no new business Shopify call can be admitted** and no business job can
        start. It then transitions to `disconnecting`/`requested`, stamps the
        request, runs **one** non-blocking A/B (queued/retry_waiting) business-job
        sweep, records the audit, and wakes the quiescence controller. It clears
        **no** credential and issues no explicit commit; the controller finalizes.

        Shared by `action_disconnect` (the direct request) and the public
        `action_clear_token` when it routes a `connected`/`reconnect_needed` store
        through the accepted two-phase disconnect instead of clearing immediately
        (review 4690807427) -- both take the lock, then call this once.
        """
        self.ensure_one()
        new_generation = locked_generation + 1
        self.write({
            'state': 'disconnecting',
            'connection_generation': new_generation,
            'disconnect_status': 'requested',
            'disconnect_status_reason': False,
            'disconnect_requested_at': fields.Datetime.now(),
            'disconnect_requested_by': self.env.uid,
            'disconnect_completed_at': False,
            'disconnect_open_lease_count': 0,
            'disconnect_oldest_admitted_at': False,
        })
        self._sweep_quiescing_business_jobs('Store disconnecting.')
        self._create_lifecycle_audit_job(
            'Store disconnect requested (state=disconnecting; connection '
            'generation bumped to %d).' % new_generation
        )
        self._trigger_disconnect_controller()
        return None

    # ------------------------------------------------------------------
    # CORE-R2 (AR-047): disconnect quiescence controller (analysis §14/§16)
    # ------------------------------------------------------------------

    @api.model
    def _run_disconnect_quiesce(self):
        """The disconnect quiescence controller cron entry point.

        Processes **exactly one** `disconnecting` store per invocation/transaction
        (analysis §14, packet §13). Selects the next **unlocked** store with the
        corrected ``search(order=…).try_lock_for_update(limit=1)`` idiom (``FOR
        UPDATE SKIP LOCKED LIMIT 1``): a locked first row does **not** block later
        ones, and an all-locked set is a **documented no-op** for this pass (a
        later pass handles them). The held ``FOR UPDATE`` conflicts with
        admission's ``FOR SHARE``, so no new lease can commit for this store while
        it is checked and finalized -- both the duplicate-finalization guard and
        the count-stability guarantee. No explicit main-cursor commit: the natural
        cron-boundary commit persists the finalize and releases the lock together.
        """
        stores = self.search(
            [('state', '=', 'disconnecting')],
            order='disconnect_requested_at, id',
        )
        if not stores:
            return
        store = stores.try_lock_for_update(limit=1)
        if not store:
            # Every eligible row is locked by a concurrent controller -> safe
            # no-op this pass (analysis §14); a later pass handles them.
            return
        store._process_disconnect_quiesce()

    def _process_disconnect_quiesce(self):
        """One quiescence pass for a single locked `disconnecting` store.

        Runs under the controller's held store ``FOR UPDATE`` (no new ``FOR
        SHARE`` admission can commit a lease meanwhile, so the count is stable
        through finalize). Re-checks the state under the lock, runs the
        non-blocking A/B sweep, then applies **direction C** (analysis §10/§16):
        count **all** committed lease rows (an expired-but-unreleased lease still
        counts -- it is unknown/live, never reaped into `completed`); write the
        escalation snapshot; then **zero rows -> `completed`**, **rows within the
        timeout -> `quiescing`** (schedule a delayed re-poll), **rows at/past
        `DISCONNECT_QUIESCE_TIMEOUT` -> `timed_out`**.
        """
        self.ensure_one()
        if self.state != 'disconnecting':
            # Re-checked under the lock: a concurrent pass already finalized it.
            return
        self._sweep_quiescing_business_jobs('Store disconnecting.')
        Lease = self.env['shopify.connector.call.lease']
        leases = Lease.search([('store_id', '=', self.id)])
        count = len(leases)
        oldest = min(leases.mapped('admitted_at')) if leases else False
        self.write({
            'disconnect_open_lease_count': count,
            'disconnect_oldest_admitted_at': oldest,
        })
        if count == 0:
            # Direction C: `completed` requires exactly zero lease rows -- every
            # admitted holder has actually released.
            self._finalize_disconnect_completed()
            return
        requested_at = self.disconnect_requested_at or fields.Datetime.now()
        elapsed = fields.Datetime.now() - requested_at
        if elapsed >= DISCONNECT_QUIESCE_TIMEOUT:
            self._finalize_disconnect_timed_out(leases)
        else:
            self.write({
                'disconnect_status': 'quiescing',
                'disconnect_status_reason': (
                    '%d in-flight call lease(s) outstanding; waiting for '
                    'quiescence.' % count
                ),
            })
            self._trigger_disconnect_controller(
                at=fields.Datetime.now() + POLL_DELAY
            )

    def _finalize_disconnect_completed(self):
        """Finalize a fully-quiesced disconnect (zero committed lease rows).

        Reachable **only** at zero lease rows (INV-3, direction C). Clears the
        credential via the controller-only `_clear_token_under_store_lock`
        primitive **under the controller's held store ``FOR UPDATE``**
        (store->credential global lock order, §9.2/§15) -- never the public
        `action_clear_token`, which refuses a `disconnecting` store (review
        4690804619 #2). No admission can slip in during the clear; this finalize
        then sets `disconnected` / `disconnect_status='completed'` and stamps
        completion. All job/log history is preserved. `completed` is provably
        distinct from `timed_out` (this path is the zero-rows condition only).
        """
        self.ensure_one()
        self.env[
            'shopify.connector.store.credential'
        ]._clear_token_under_store_lock(self)
        self.write({
            'state': 'disconnected',
            'disconnect_status': 'completed',
            'disconnect_status_reason': (
                'Disconnect completed: all in-flight call leases released.'
            ),
            'disconnect_open_lease_count': 0,
            'disconnect_oldest_admitted_at': False,
            'disconnect_completed_at': fields.Datetime.now(),
        })
        self._create_lifecycle_audit_job(
            'Store disconnect completed (0 outstanding call leases).'
        )

    def _finalize_disconnect_timed_out(self, leases):
        """Finalize a disconnect that reached the timeout with lease rows present.

        Direction C (analysis §16): with **any** lease rows still present (expired
        or live) at `DISCONNECT_QUIESCE_TIMEOUT`, record a **bounded, secret-free**
        escalation snapshot (count, oldest-admitted age, and at most
        ``_ESCALATION_SNAPSHOT_LIMIT`` opaque `lease_key`s / Integer `job_id`s --
        never a token/credential/payload), clear the credential (the bounded set
        of already-admitted holders may finish with their **already-captured
        in-memory token**; clearing the row does not invalidate sent bytes), and
        set `disconnected` / `disconnect_status='timed_out'` -- a status **distinct
        from `completed`**. Job/log history is preserved. The residual lease rows
        are cleaned up **only after** this `timed_out` finalization (never before,
        never on the `completed` path) -- the only sanctioned cleanup point.
        """
        self.ensure_one()
        count = len(leases)
        oldest = min(leases.mapped('admitted_at')) if leases else False
        snapshot = [
            {'lease_key': lease.lease_key, 'job_id': lease.job_id}
            for lease in leases[:_ESCALATION_SNAPSHOT_LIMIT]
        ]
        reason = (
            'Disconnect timed out with %d outstanding call lease(s) at the '
            'quiescence deadline; credential cleared. Outstanding holders '
            '(bounded to %d): %s'
            % (count, _ESCALATION_SNAPSHOT_LIMIT, json.dumps(snapshot))
        )
        # Controller-only clear primitive under the held store FOR UPDATE (review
        # 4690804619 #2); this finalize sets `disconnected`/`timed_out` itself.
        self.env[
            'shopify.connector.store.credential'
        ]._clear_token_under_store_lock(self)
        self.write({
            'state': 'disconnected',
            'disconnect_status': 'timed_out',
            'disconnect_status_reason': reason,
            'disconnect_open_lease_count': count,
            'disconnect_oldest_admitted_at': oldest,
            'disconnect_completed_at': fields.Datetime.now(),
        })
        self._create_lifecycle_audit_job(
            'Store disconnect timed out (%d outstanding call lease(s); '
            'credential cleared; distinct from completed).' % count
        )
        # Direction C: residual lease rows are cleaned up ONLY AFTER the
        # `timed_out` finalization -- never before, never on the `completed`
        # path -- since the store is now `timed_out`, not `completed`.
        leases.unlink()

    def action_reconnect(self):
        """Re-run the existing Task 003/004 substrate; connect only on evidence.

        Service/model layer only -- no OAuth, no setup wizard, no new
        credential-input mechanism; token re-entry goes through the
        existing Task 002 credential service exactly as `activate`/
        initial setup already do. Never infers `connected` from
        credential presence alone: transitions to `connected` only if the
        freshly re-run test-connection and readiness substrate both
        actually support it, otherwise remains/transitions to
        `reconnect_needed` (DEC-022 §4.6).

        With no credential present: this method does not call Shopify,
        does not run readiness, does not clear the credential, and does
        not auto-reconnect -- it only persists the reconnect_needed
        state and its audit job, then returns `None`. It deliberately
        does not raise afterward: in normal Odoo RPC/service execution a
        raised exception can roll back the ORM writes made earlier in
        the same call, which would silently discard the very
        state/audit write this branch exists to guarantee. A caller
        that needs to distinguish "reconnect actually connected" from
        "reconnect left the store in reconnect_needed" should check
        `self.state` after calling, not rely on an exception.
        """
        self.ensure_one()
        # CORE-R2 (AR-047; analysis §8): reconnect is refused while the store is
        # `disconnecting` (disconnect is one-way; reconnect is only from the
        # finalized `disconnected` state). No credential/state/audit is written.
        if self.state == 'disconnecting':
            raise UserError(
                'Cannot reconnect: a disconnect is in progress for this '
                'store.'
            )
        if not self.credential_present:
            self.write({'state': 'reconnect_needed'})
            self._create_lifecycle_audit_job(
                'Reconnect attempted with no stored credential; remains '
                'reconnect_needed.'
            )
            return None
        # CORE-R2 (AR-047; review 4690639375 #1): capture the connection epoch at
        # reconnect start. The probe/readiness below run UNLOCKED, so a disconnect
        # (or any other generation-changing transition) winning the race during
        # them will change this epoch; the finalize then refuses rather than
        # overwriting it. Capturing the epoch -- not a blanket `disconnected`
        # refusal -- is what lets a *legitimate* reconnect from the finalized
        # `disconnected` state (its epoch unchanged during the probe) still
        # succeed, while a disconnect that WON during the probe is refused.
        initial_generation = self.connection_generation
        # CORE-R2 (AR-047; review 4690639375 #2): reconnect probes via the shared
        # `_run_connection_probe` with the INTERNAL purpose `'reconnect_probe'`,
        # which the frozen matrix permits from the finalized `disconnected` state
        # (reconnect after completed disconnect) -- unlike `'test_connection'`,
        # which excludes `disconnected`. The probe issues the Shopify call, then
        # revalidates its one credential snapshot under the store->credential locks.
        probe_status = self._run_connection_probe('reconnect_probe')
        if probe_status == 'superseded':
            # A lifecycle/credential change won during the probe; it was already
            # audited as superseded and wrote no mirrors. Do not run readiness or
            # finalize on a store that has moved on -- abort the reconnect.
            return None
        self.invalidate_recordset()
        # If the probe just failed with an auth/permission/scope signal,
        # `_run_connection_probe`'s own handler already called
        # action_mark_reconnect_needed() (which is itself TOCTOU-safe and refuses
        # to overwrite a one-way disconnect). Detect it via the fresh job's
        # error_class to avoid doubling the audit trail for one logical attempt.
        already_marked_reconnect_needed = False
        if self.last_test_connection_result != 'pass':
            last_test_job = self.env['shopify.connector.job'].search([
                ('store_id', '=', self.id),
                ('job_type', '=', 'core_test_connection'),
            ], order='id desc', limit=1)
            already_marked_reconnect_needed = (
                last_test_job.error_class == ERROR_AUTH
            )
        self.env['shopify.connector.readiness.check'].run_for_store(self)
        self.invalidate_recordset()
        reconnect_ok = (
            self.last_test_connection_result == 'pass'
            and self.last_readiness_result in ('pass', 'warning')
        )
        # CORE-R2 (AR-047; review 4690639375 #1): finalize the reconnect state
        # transition UNDER the conflicting update lock, revalidating the fresh
        # state read under it. Refuse -- never overwriting -- if a disconnect is
        # in progress (`disconnecting`) OR if the connection epoch changed since
        # reconnect start (a disconnect, activation, or credential change won the
        # race during the unlocked probe/readiness). A store that was already
        # `disconnected` at reconnect start with an unchanged epoch is a
        # legitimate reconnect and proceeds.
        locked_state, locked_generation = self._lock_store_for_lifecycle()
        if (
            locked_state == 'disconnecting'
            or locked_generation != initial_generation
        ):
            self._create_lifecycle_audit_job(
                'Reconnect aborted: a concurrent lifecycle transition won '
                'during the probe; store remains %s.' % locked_state
            )
            return None
        if reconnect_ok:
            # A successful reconnect is a generation-changing transition -- bump
            # the epoch exactly once, consuming the generation read under the lock.
            self.write({
                'state': 'connected',
                'connection_generation': locked_generation + 1,
            })
            self._create_lifecycle_audit_job(
                'Store reconnected (test-connection: %s, readiness: '
                '%s).' % (
                    self.last_test_connection_result,
                    self.last_readiness_result,
                )
            )
        elif not already_marked_reconnect_needed:
            self.write({'state': 'reconnect_needed'})
            self._create_lifecycle_audit_job(
                'Reconnect evidence insufficient; remains reconnect_needed '
                '(test-connection: %s, readiness: %s).' % (
                    self.last_test_connection_result,
                    self.last_readiness_result,
                )
            )
        return None

    def action_mark_reconnect_needed(self, reason=False):
        """Move to `reconnect_needed`; never auto-clears the credential or reconnects.

        Only an explicit `action_reconnect`/`action_disconnect`, taken by
        an operator, may move the store away from this state -- no
        automatic reconnect is ever attempted here or anywhere else
        (DEC-022 §4.7). Idempotent: calling this on a store already in
        `reconnect_needed` is a safe, audited no-op re-record, never an
        error.

        CORE-R2 (AR-047; review 4690639375 #1): this is called both directly and
        from `_run_connection_probe`'s auth-failure handler, so it takes the
        conflicting store-row update lock and fresh-reads the state first; it
        **never overwrites a one-way disconnect** (`disconnecting`/`disconnected`
        -> audited no-op). Moving to `reconnect_needed` is an auth-failure
        degradation, not a generation-changing reconnect, so it does **not** bump
        the epoch.
        """
        self.ensure_one()
        locked_state, _generation = self._lock_store_for_lifecycle()
        if locked_state in ('disconnecting', 'disconnected'):
            self._create_lifecycle_audit_job(
                'Reconnect-needed signal ignored: store is %s (disconnect is '
                'one-way).' % locked_state
            )
            return None
        self.write({'state': 'reconnect_needed'})
        message = 'Store marked reconnect_needed.'
        if reason:
            message = 'Store marked reconnect_needed: %s' % redact(reason)
        self._create_lifecycle_audit_job(message)
        return None
