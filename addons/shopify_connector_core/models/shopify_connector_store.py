import json
import uuid

from odoo import api, fields, models
from odoo.exceptions import UserError

from ..tools.redaction import redact
from .shopify_connector_api_client import ERROR_AUTH, ShopifyClientError
from .shopify_connector_job import BUSINESS_JOB_SOURCES, TERMINAL_JOB_STATES
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
        Creates exactly one `job_type='core_test_connection'` job per
        run, with a fresh UUID4 `payload_hash` nonce so repeat runs never
        collide on `store_idempotency_key_uniq` --
        `core_readiness_check`'s identical latent exposure is untouched
        (TD-001). Writes only the store mirrors, the credential's
        `credential_state` (only for a genuine token-invalid signal), and
        the job/job.log rows -- never the token, never a raw response
        body outside the client's already-redacted `technical_detail`.
        """
        self.ensure_one()
        # CORE-R2 (AR-047; analysis §8/§9.1): Test Connection is a lifecycle
        # diagnostic and is refused while the store is `disconnecting` (before
        # any audit job is created). `execute_lifecycle`'s purpose→state matrix
        # is the second, in-transport guard for the same rule.
        if self.state == 'disconnecting':
            raise UserError(
                'Test Connection is not available while a disconnect is in '
                'progress.'
            )
        if not self.credential_present:
            raise UserError(
                'Enter a credential before testing the connection.'
            )
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

        try:
            # CORE-R2 (analysis §9.3): the core store test-connection call site
            # migrates to the guarded `execute_lifecycle` lifecycle entry
            # (purpose='test_connection'; plain call, no lease). Same transport,
            # normalization, and error taxonomy as the pre-existing `execute()`.
            result = self.env[
                'shopify.connector.api.client'
            ].execute_lifecycle(
                self, TEST_CONNECTION_QUERY, purpose='test_connection',
            )
        except ShopifyClientError as exc:
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
                # Task 005 / DEC-022 §4.7: any auth/permission/scope
                # invalidation signal -- not only a genuine token-invalid
                # one -- moves the store to reconnect_needed. Human/admin
                # action (reconnect/disconnect) is the only way out; this
                # never auto-reconnects.
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
        # CORE-R2 (AR-047; analysis §8): activation is refused while the store
        # is `disconnecting` (disconnect is one-way; the matrix permits no
        # lifecycle mutation during quiescence).
        if self.state == 'disconnecting':
            raise UserError(
                'Cannot activate: a disconnect is in progress for this store.'
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
        # CORE-R2 (AR-047; analysis §8/§9.2): activation is a generation-changing
        # transition -- take the conflicting store-row update lock, fresh-read
        # under it, and bump the epoch exactly once so any admission racing this
        # activation linearizes on the row.
        self._lock_store_for_lifecycle()
        self.write({
            'state': 'connected',
            'connection_generation': self.connection_generation + 1,
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
        state, _generation = self._lock_store_for_lifecycle()
        if state in ('disconnecting', 'disconnected'):
            self._create_lifecycle_audit_job(
                'Disconnect requested; store already %s -- audited no-op.'
                % state
            )
            return None
        self.write({
            'state': 'disconnecting',
            'connection_generation': self.connection_generation + 1,
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
            'generation bumped to %d).' % self.connection_generation
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
        credential via the existing Task 002 service **under the controller's held
        store ``FOR UPDATE``** (store->credential global lock order, §9.2/§15) --
        no admission can slip in during the clear -- then sets `disconnected` /
        `disconnect_status='completed'` and stamps completion. All job/log history
        is preserved. `completed` is provably distinct from `timed_out` (this path
        is the zero-rows condition only).
        """
        self.ensure_one()
        self.env['shopify.connector.store.credential'].action_clear_token(self)
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
        self.env['shopify.connector.store.credential'].action_clear_token(self)
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
        self.action_test_connection()
        self.invalidate_recordset()
        # If test-connection just failed with an auth/permission/scope
        # signal, action_test_connection()'s own exception handler
        # already called action_mark_reconnect_needed() -- its state
        # write and audit job are already recorded. Re-running that same
        # write/audit below would double the audit trail for one logical
        # reconnect attempt, so detect it via the fresh job's error_class
        # (the same condition action_test_connection() itself used) and
        # skip the redundant re-write. Every other failure path (identity
        # mismatch, temporary/throttle/unknown errors, or a readiness
        # failure with a passing test-connection) still falls through to
        # this method's own reconnect_needed write/audit below, since
        # action_test_connection() does not handle those itself.
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
        if (
            self.last_test_connection_result == 'pass'
            and self.last_readiness_result in ('pass', 'warning')
        ):
            # CORE-R2 (AR-047; analysis §8/§9.2): a successful reconnect is a
            # generation-changing transition -- take the conflicting store-row
            # update lock, fresh-read under it, and bump the epoch exactly once.
            self._lock_store_for_lifecycle()
            self.write({
                'state': 'connected',
                'connection_generation': self.connection_generation + 1,
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
        """
        self.ensure_one()
        self.write({'state': 'reconnect_needed'})
        message = 'Store marked reconnect_needed.'
        if reason:
            message = 'Store marked reconnect_needed: %s' % redact(reason)
        self._create_lifecycle_audit_job(message)
        return None
