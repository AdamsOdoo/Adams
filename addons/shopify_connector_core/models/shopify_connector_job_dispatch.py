from datetime import timedelta
import logging
import random

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.service.model import PG_CONCURRENCY_EXCEPTIONS_TO_RETRY

from ..tools.redaction import redact
from .shopify_connector_job import BUSINESS_JOB_SOURCES, MANUAL_REVIEW_SUBREASON_SELECTION

_logger = logging.getLogger(__name__)

# Decision E (gate-opening proposal §6) -- a conservative implementation
# default pending live-runtime validation (see docs/07-implementation-
# plan/task-006c-sync-engine-gate-opening-proposal.md §8), well below
# the documented >64-savepoint performance ceiling (SRR-01). Named,
# tunable constant, never an inlined magic number.
DISPATCH_BATCH_SIZE = 20

# Decision C (gate-opening proposal §6 / MBQ-16 implementation-planning
# defaults, restated in DEC-009's own acceptance note as "implementation
# planning defaults, not final production-tuned constants"). Named,
# tunable constants -- a future retuning session can change these
# without an architecture change.
RETRY_MAX_ATTEMPTS = 12
RETRY_BASE_DELAY_SECONDS = 30
RETRY_MULTIPLIER = 2
RETRY_MAX_DELAY_SECONDS = 30 * 60
RETRY_JITTER_FRACTION = 0.2
RETRY_WINDOW_HOURS = 24
# unknown_system_error's own "single safety-net auto-retry, then human"
# posture (architecture gate §E) -- a distinct, smaller attempt budget
# than the general auto-retry classes below.
SAFETY_NET_MAX_ATTEMPTS = 1

# CORE-R2 Slice 2A (AR-047; analysis §14/§16, packet §7/§13) disconnect
# quiescence controller cadence + timeout. Named, tunable constants
# [Open -- tuning only, analysis §26]; a future retuning session can change
# these without an architecture change. The disconnect controller
# (`shopify_connector_store.py::_run_disconnect_quiesce`) imports them.
#
# * DISCONNECT_QUIESCE_TIMEOUT is measured from `store.disconnect_requested_at`
#   and MUST exceed the admission lease lifetime
#   (`shopify_connector_api_client._CALL_LEASE_LIFETIME_SECONDS`, 300s) so a
#   genuinely-live-but-slow admitted call inside its own lifetime is never
#   force-finalized as `timed_out` before it can release its lease.
# * POLL_DELAY is the still-`quiescing` re-poll cadence, scheduled via a
#   delayed `_trigger(at=now+POLL_DELAY)` (never an immediate same-store
#   re-trigger, no busy loop). It is >= 1 minute -- the `ir_cron._trigger`
#   scheduling granularity floor (analysis §14, `ir_cron.py:735`).
DISCONNECT_QUIESCE_TIMEOUT = timedelta(minutes=15)
POLL_DELAY = timedelta(minutes=1)

# DEC-009 §E retry-class taxonomy, applied to the fixed ERROR_CLASS_
# SELECTION registry already encoded in shopify_connector_job.py. This
# module does not introduce a 17th class or alter the registry -- it
# only routes the existing 16 classes to a job-state transition.
AUTO_RETRY_ERROR_CLASSES = (
    'shopify_throttling_rate_limit',
    'shopify_temporary_server_network',
    'concurrency_race_conflict',
)
MANUAL_FIX_THEN_RETRY_ERROR_CLASSES = (
    'shopify_permission_scope_auth',
    'shopify_user_errors_validation',
    'odoo_validation_configuration',
    'mapping_missing',
    'data_shape_schema_mismatch',
)
# "Conservative, never silent" (architecture gate §E) -- stops the job
# without an automatic retry, same as the manual-fix-then-retry family,
# but financial_total_mismatch is not one of the six manual_review_
# subreason values, so it cannot route to blocked_manual_review (the
# job model's own _check_manual_review_subreason_required constraint
# would reject that combination).
CONSERVATIVE_NEVER_SILENT_ERROR_CLASSES = (
    'financial_total_mismatch',
)
# The six DEC-009 §D.5.4 operator-confirmation-required classes double
# as their own manual_review_subreason value -- imported, not
# redeclared, so the two vocabularies can never drift apart.
MANUAL_REVIEW_ERROR_CLASSES = tuple(
    value for value, _label in MANUAL_REVIEW_SUBREASON_SELECTION
)
SAFETY_NET_ERROR_CLASSES = (
    'unknown_system_error',
)

# DEC-031 Layer 1 (AR-048) -- the fail-closed replay-policy registry's
# fixed three-value vocabulary. Do not add a fourth class here.
REPLAY_POLICY_LOCAL_ONLY = 'local_only'
REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE = 'remote_read_replay_safe'
REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE = 'remote_effect_not_replay_safe'
# Policies for which replaying a recovered job's existing bounded
# concurrency_race_conflict auto-retry (this module's own recovery
# mechanism, unmodified) stays safe: a purely local no-op or a remote
# *read* has no Shopify-side effect, so a further automatic retry after
# recovery cannot cause a duplicate remote effect.
REPLAY_SAFE_RETRY_POLICIES = (
    REPLAY_POLICY_LOCAL_ONLY,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)


class JobHandlerError(Exception):
    """Raised by a registered handler to report a classified failure.

    `error_class` must be one of `shopify.connector.job`'s fixed
    `ERROR_CLASS_SELECTION` values -- the dispatcher routes the job to
    `retry_waiting`/`failed_retryable`/`failed_final`/
    `blocked_manual_review` based on it, per the DEC-009 taxonomy this
    module encodes above. Any other exception a handler raises is
    treated as `unknown_system_error`. Mirrors `ShopifyClientError`'s
    own redact-at-construction discipline: `reason`/`technical_detail`
    are redacted here too, as defense in depth, even though every write
    path this exception reaches also redacts via `_system_append()`.
    """

    def __init__(self, error_class, reason, technical_detail=False):
        reason = redact(reason)
        super().__init__(reason)
        self.error_class = error_class
        self.reason = reason
        self.technical_detail = (
            redact(technical_detail) if technical_detail else technical_detail
        )


class ShopifyConnectorJobDispatch(models.AbstractModel):
    """The core job-dispatch service (Decision D): the `ir.cron`-driven
    drain-loop entry point, the handler-registry seam, the dispatcher,
    and the retry-scheduling sweep.

    Stateless, no table (`AbstractModel`, mirroring
    `shopify_connector_readiness_check.py` -- no new ACL row needed).
    Every write path here goes through `shopify.connector.job`'s own
    `write()`/state-transition-helper methods and
    `job.log._system_append()` -- no second job-log write path, no
    direct `job.log.create()` call, and no live Shopify API
    call anywhere in this file.
    """

    _name = 'shopify.connector.job.dispatch'
    _description = 'Shopify Connector Job Dispatch Service'

    # ------------------------------------------------------------------
    # ir.cron entry point
    # ------------------------------------------------------------------

    @api.model
    def run_drain(self, limit=DISPATCH_BATCH_SIZE):
        """Claim and dispatch up to ``limit`` jobs -- the ``ir.cron`` target.

        Each job is claimed, dispatched, and committed on its own per-job
        transaction (see :meth:`_drain_one`). The dispatcher deliberately does
        NOT wrap the handler in ``odoo.service.model.retrying``: that boundary
        automatically RE-INVOKES the complete handler after a rollback, which
        -- once a Shopify transport has already occurred -- risks a duplicate
        request, and it re-drives the job by a bare id without ever
        reacquiring the row-lock claim the rollback released. Instead a genuine
        PostgreSQL serialization/deadlock/lock failure (SQLSTATE
        40001/40P01/55P03) is caught at the per-job outer boundary, which rolls
        back, resets the environment, REACQUIRES the exact job under a real
        ``FOR UPDATE SKIP LOCKED`` row lock, revalidates its claimable state
        under that lock, and -- only if the job is still safely owned and
        claimable -- routes it ONCE through its declared DEC-031 Layer 1
        (AR-048) replay policy WITHOUT the recovery call itself re-invoking
        the handler: a ``local_only`` or ``remote_read_replay_safe`` job may
        be scheduled for a later bounded ``concurrency_race_conflict`` retry,
        while a ``remote_effect_not_replay_safe`` or undeclared job is routed
        to manual review instead of any automatic retry. This routing is
        policy-gated and makes no exactly-once claim. Per-job commit keeps one
        racing (or failing) job from rolling back the work of jobs already
        committed in the same drain (batch integrity); and because the claim is
        only a transaction-scoped row lock, a rolled-back job is never
        re-exposed by a bare re-browse -- after any rollback the job MUST be
        re-locked before any dispatch or state transition
        (:meth:`_recover_after_concurrency_conflict`).
        """
        for _slot in range(limit):
            if not self._drain_one():
                break

    @api.model
    def _drain_one(self):
        """Claim and dispatch a single job on its own per-job transaction.

        The claim (``shopify.connector.job._claim_for_dispatch``) is a
        transaction-scoped ``FOR UPDATE SKIP LOCKED`` row lock, NOT a durable
        state flag: it is held only until this transaction commits or rolls
        back. On the success path the whole dispatch (start -> handler ->
        outcome) runs and commits under that one held claim, so the job is
        never dispatched or transitioned without a currently-held lock, and a
        later job's rollback can never undo it. On a genuine PostgreSQL
        concurrency failure the aborted transaction has lost BOTH the claim and
        every uncommitted write; recovery re-locks the job before touching it
        (:meth:`_recover_after_concurrency_conflict`), which itself never
        re-invokes the handler and instead routes the still-owned job once
        through its declared DEC-031 Layer 1 replay policy (a bounded retry
        for ``local_only``/``remote_read_replay_safe`` jobs, manual review
        for ``remote_effect_not_replay_safe``/undeclared ones).

        Returns ``True`` when a job was claimed and handled (whether it
        succeeded, was refused, routed, recovered, or left to another worker),
        ``False`` when no claimable job remains so ``run_drain`` can stop early.
        """
        claimed = self.env['shopify.connector.job']._claim_for_dispatch(1)
        if not claimed:
            return False
        job_id = claimed.id

        if not self._concurrency_retry_supported():
            # The shared in-test transaction cursor forbids commit/rollback, so
            # the per-job transaction boundary below cannot run here. The
            # standard suite exercises normal dispatch and classified-failure
            # routing; a genuine PostgreSQL serialization failure cannot occur
            # on its single shared connection anyway. The genuine
            # independent-connection lifecycle tests drive the real boundary
            # below on real pooled cursors.
            self._dispatch_one(claimed)
            return True

        try:
            # Dispatch the claimed job ONCE, under the currently-held claim.
            # Flush inside the guard so a deferred serialization failure (Odoo
            # runs REPEATABLE READ, where 40001 surfaces at statement/flush
            # time) is caught here -- never after the commit, where it would
            # escape as a raw concurrency error.
            self._dispatch_one(claimed)
            self.env.cr.flush()
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY as exc:
            # A genuine 40001/40P01/55P03 aborted this transaction AFTER a
            # transport may already have occurred. The recovery call does NOT
            # replay the handler: reset, reacquire the exact job under a real
            # row lock, and -- only if we still own it -- route it once
            # through its declared DEC-031 Layer 1 replay policy (a bounded
            # conflict retry for replay-safe jobs, manual review otherwise).
            # Record the SQLSTATE (operationally useful, and the observable
            # evidence that a genuine PostgreSQL concurrency failure -- not an
            # injected exception -- drove this recovery).
            _logger.info(
                "Job %s hit a PostgreSQL concurrency failure (SQLSTATE %s) "
                "after dispatch; rolling back and reacquiring the job under a "
                "fresh row lock before any routing -- the handler is not "
                "replayed.",
                job_id, getattr(exc, 'pgcode', None),
            )
            self._recover_after_concurrency_conflict(job_id)
        else:
            # Commit this job's own outcome so a later job's rollback can never
            # undo it and it is never re-exposed to a duplicate call.
            self.env.cr.commit()
        return True

    @api.model
    def _recover_after_concurrency_conflict(self, job_id):
        """Recover ownership after a genuine PostgreSQL concurrency failure
        aborted a dispatch transaction, WITHOUT replaying the handler.

        The aborted transaction has already lost BOTH the original claim (a
        transaction-scoped ``FOR UPDATE`` row lock the rollback released) AND
        every uncommitted write (``state`` -> ``running``, any handler write).
        A Shopify transport MAY already have occurred, so the handler is never
        re-invoked here. Ownership contract (every reset loses the claim):

        1. roll back the aborted transaction and reset the environment, so the
           cursor is usable and no stale claim, lock, or cache (including the
           rolled-back ``running`` write) survives;
        2. reacquire the EXACT job under the real non-blocking
           ``try_lock_for_update`` (``FOR UPDATE SKIP LOCKED``) claim -- an
           empty result means another worker holds it (or the row is gone), so
           we own nothing and must not touch it;
        3. revalidate its CLAIMABLE state under that lock -- a job another
           worker already moved to ``running``/terminal/etc. is not claimable
           and must never be overwritten;
        4. only a still-owned, still-claimable job is routed ONCE, in this
           clean transaction we own, through its declared DEC-031 Layer 1
           (AR-048) replay policy -- never by re-invoking the handler: a
           ``local_only`` or ``remote_read_replay_safe`` job may be scheduled
           for a later bounded ``concurrency_race_conflict`` retry
           (``retry_waiting``, or ``failed_final`` once the bounded budget is
           exhausted), while a ``remote_effect_not_replay_safe`` or undeclared
           job is routed to manual review (``duplicate_risk``) instead of any
           automatic retry. The routing is policy-gated and makes no
           exactly-once claim.

        Every exit commits the (owned or empty) transaction so the row lock, if
        any, is released and the next ``_drain_one`` claim starts clean. Another
        worker winning the post-rollback claim, or having already transitioned
        the job, is a valid outcome -- never an error.
        """
        Job = self.env['shopify.connector.job']
        # (1) Make the aborted cursor usable again and drop all stale ORM state
        # (recordset caches, to-compute/to-flush) so nothing from the lost
        # transaction leaks into the recovery transaction.
        self.env.cr.rollback()
        self.env.transaction.reset()
        # (2) Reacquire the exact job under a real FOR UPDATE SKIP LOCKED row
        # lock. Empty => another worker holds it (or the row is gone): we own
        # nothing, so we do nothing.
        locked = Job.browse(job_id).try_lock_for_update()
        if not locked:
            self.env.cr.commit()
            return
        # (3) Revalidate CLAIMABLE state UNDER the lock (mirrors
        # ``_claim_for_dispatch``): only a still-queued or genuinely-due
        # retry_waiting job may be routed; a running/terminal/otherwise
        # non-claimable job is owned or finished by another worker and must
        # never be overwritten.
        locked.invalidate_recordset()
        claimable = locked.filtered(lambda job: job.state == 'queued' or (
            job.state == 'retry_waiting'
            and job.next_retry_at
            and job.next_retry_at <= fields.Datetime.now()
        ))
        if not claimable:
            self.env.cr.commit()
            return
        # (4) We hold the lock and the job is still safely claimable: route
        # it WITHOUT replaying the handler -- so no second Shopify transport
        # is issued -- through whichever path its declared replay policy
        # (DEC-031 Layer 1, AR-048) allows.
        policy = self._get_replay_policy(claimable.job_type)
        if policy in REPLAY_SAFE_RETRY_POLICIES:
            self._route_failure(
                claimable, 'concurrency_race_conflict',
                'A concurrent-update conflict aborted the dispatch '
                'transaction after a transport may have occurred; the job '
                'was re-locked and routed once to a bounded retry without '
                'replaying its handler.',
            )
        else:
            # remote_effect_not_replay_safe, or any undeclared/unexpected
            # policy (fail-closed default -- never a read-safe default): an
            # automatic retry here could re-issue a Shopify-side effect, so
            # this never reaches concurrency_race_conflict's auto-retry.
            # Routed instead through the existing blocked_manual_review /
            # duplicate_risk vocabulary -- no new error class, no automatic
            # retry, never retry_waiting.
            self._route_failure(
                claimable, 'duplicate_risk',
                'A concurrent-update conflict aborted the dispatch '
                'transaction for a job whose remote effect is not declared '
                'replay-safe. After the rollback, a prior remote effect '
                'cannot be safely ruled out -- this does not claim a '
                'Shopify mutation occurred, nor exactly-once execution. '
                'The job was re-locked and routed to manual review instead '
                'of an automatic retry.',
            )
        self.env.cr.commit()

    @api.model
    def _concurrency_retry_supported(self):
        """Whether the per-job transaction boundary (:meth:`_drain_one`) can
        manage its own commit/rollback on the current cursor.

        That boundary commits each job on success and rolls back + recovers on
        a genuine concurrency failure. The Odoo test runner replaces the shared
        ``TransactionCase`` cursor's ``commit`` with a guard that raises, so the
        boundary runs on production and on the genuine independent-connection
        lifecycle tests (real pooled ``db_connect`` cursors) and is bypassed on
        the shared in-test cursor -- where a genuine PostgreSQL serialization
        failure cannot occur on the single shared connection anyway. Detected by
        the forbidden-commit guard rather than ``in_test_mode()``, because the
        genuine tests are themselves in test mode yet legitimately commit on
        their own real cursors.
        """
        commit = getattr(self.env.cr, 'commit', None)
        return getattr(commit, '__name__', '') != 'forbidden'

    # ------------------------------------------------------------------
    # Registry / domain-extension seam (Decision B)
    # ------------------------------------------------------------------

    @api.model
    def _get_handlers(self):
        """`job_type` -> handler mapping.

        Domain-extension seam: override via classic Odoo inheritance
        (`_inherit = 'shopify.connector.job.dispatch'`), calling
        `super()._get_handlers()` and updating the returned dict with
        additional `job_type` -> handler entries -- never removing or
        overwriting a core-owned entry. Adapts (does not copy) the
        `_get_checks()` inheritance-append precedent
        (`shopify_connector_readiness_check.py`): a job routes to
        exactly one handler by `job_type` key lookup -- it does not
        aggregate every registered handler the way `_get_checks()`
        aggregates independently-evaluated checks.
        """
        return {
            'core_dispatch_selftest': self._handle_core_dispatch_selftest,
        }

    @api.model
    def _handle_core_dispatch_selftest(self, job):
        """No-op diagnostic handler for `core_dispatch_selftest`
        (Decision F) -- exercises the registry/dispatch mechanism only.
        Never calls Shopify, never represents domain sync."""
        return None

    @api.model
    def _get_replay_policies(self):
        """`job_type` -> replay policy (DEC-031 Layer 1, AR-048).

        Same domain-extension seam shape as `_get_handlers()`: override
        via classic Odoo inheritance, calling
        `super()._get_replay_policies()` and updating the returned dict
        with additional `job_type` -> policy entries -- never removing
        or overwriting a core-owned entry. Every key `_get_handlers()`
        returns must have an explicit entry here (build-time
        completeness invariant, `test_job_dispatch.py`); the runtime
        lookup (`_get_replay_policy`) independently stays fail-closed
        for any undeclared `job_type` regardless of that test.
        """
        return {
            'core_dispatch_selftest': REPLAY_POLICY_LOCAL_ONLY,
        }

    @api.model
    def _get_replay_policy(self, job_type):
        """Fail-closed replay-policy lookup for a single `job_type`.

        Returns the explicitly registered policy
        (:meth:`_get_replay_policies`) when present; defaults any
        unexpected or undeclared `job_type` to the conservative
        `remote_effect_not_replay_safe` -- never a read-safe default.
        """
        return self._get_replay_policies().get(
            job_type, REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
        )

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    @api.model
    def _dispatch_one(self, job):
        """Start a claimed job, then invoke its registered handler."""
        if not self._start_running(job):
            return
        self._invoke_handler(job)

    @api.model
    def _start_running(self, job):
        """Checkpoint 2: the `state` -> `running` transition, through
        `shopify.connector.job`'s own `write()` (the unmodified
        store-state gate plus the new domain-flag gate).

        If a gating check blocks the start, the job is routed to
        `failed_retryable` with `error_class='odoo_validation_
        configuration'` -- a visible, audited outcome (via the existing
        `_transition_failed_retryable()` helper, logged exclusively
        through `_system_append()`) rather than silently remaining
        `queued`/`retry_waiting` forever. This does not bypass or weaken
        either gate: the sanctioned protected write still raises exactly as
        before -- this only makes an already-blocked start observable,
        as a configuration/state problem an operator can correct and
        retry later (the same DEC-009 "manual fix then retry" class
        `odoo_validation_configuration` already routes to via
        `_route_failure()`). Never raises out of the drain loop, so one
        blocked job never stops the rest of the batch -- `write()`
        either succeeds (returns `True`) or is caught here and routed
        to `failed_retryable` (returns `False`).
        """
        JobLog = self.env['shopify.connector.job.log']
        from_state = job.state
        try:
            job.sudo().write({
                'state': 'running',
                'started_at': job.started_at or fields.Datetime.now(),
            })
        except ValidationError as exc:
            job._transition_failed_retryable(
                error_class='odoo_validation_configuration',
                message=(
                    'Job could not start: a start-time gating check '
                    'blocked it (%s).' % str(exc)
                ),
            )
            return False
        JobLog._system_append(
            job, 'attempt', 'Dispatch attempt started.',
            from_state=from_state, to_state='running',
        )
        return True

    @api.model
    def _invoke_handler(self, job):
        """Checkpoint 3 (SRR-03 narrowing) + handler invocation +
        outcome routing.

        Re-checks store state immediately before invoking the handler --
        this narrows, but per the Task 006C gate-opening proposal's own
        explicit framing never claims to close, the disconnect/
        in-flight-job race (Decision A / implementation-scope §F item
        9). A job whose `job_type` has no registered handler fails
        safely (never hangs, never silently drops).
        """
        if job.job_type == 'historic_domain_job':
            # LC-1 / DEC-030: this permanent sink has no handler by design.
            # The ondelete conversion leaves only terminal rows, but a
            # directly-created/malformed non-terminal row must still fail
            # closed instead of falling into any future domain handler.
            job._transition_failed_final(
                error_class='unknown_system_error',
                message=(
                    'Historic domain jobs are audit-only and cannot be '
                    'dispatched.'
                ),
            )
            return

        store = job.store_id
        store.invalidate_recordset()
        if (
            job.job_source in BUSINESS_JOB_SOURCES
            and store.state != 'connected'
        ):
            job._transition_skipped(
                'Store is no longer connected immediately before '
                'dispatch -- skipped without invoking a handler.'
            )
            return

        handler = self._get_handlers().get(job.job_type)
        if handler is None:
            job._transition_failed_final(
                error_class='unknown_system_error',
                message='No handler is registered for job_type %r.' % (
                    job.job_type,
                ),
            )
            return

        try:
            handler(job)
        except PG_CONCURRENCY_EXCEPTIONS_TO_RETRY:
            # A genuine PostgreSQL concurrency failure (SQLSTATE
            # 40001/40P01/55P03) has aborted the transaction. It must NEVER
            # be caught and routed through an ORM write here: that write
            # would run inside the already-aborted transaction and fail as
            # InFailedSqlTransaction, masking the real conflict. Re-raise it
            # unchanged so the drain's per-job outer boundary rolls back,
            # resets the environment, REACQUIRES the exact job under a real
            # row lock and -- without the recovery call re-invoking this
            # handler -- routes it once through its declared DEC-031 Layer 1
            # replay policy (``_drain_one`` /
            # ``_recover_after_concurrency_conflict``): a bounded
            # ``concurrency_race_conflict`` retry only for
            # ``local_only``/``remote_read_replay_safe`` jobs, manual review
            # for ``remote_effect_not_replay_safe``/undeclared ones.
            # (Classified handler
            # conflicts a handler can detect BEFORE poisoning the transaction
            # still raise ``JobHandlerError('concurrency_race_conflict', ...)``
            # and route below.)
            raise
        except JobHandlerError as exc:
            self._route_failure(
                job, exc.error_class, exc.reason, exc.technical_detail,
            )
            return
        except Exception as exc:  # fail-safe dispatcher boundary
            self._route_failure(
                job, 'unknown_system_error', str(exc), repr(exc),
            )
            return

        JobLog = self.env['shopify.connector.job.log']
        from_state = job.state
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        JobLog._system_append(
            job, 'attempt', 'Dispatch succeeded.',
            from_state=from_state, to_state='succeeded',
        )

    # ------------------------------------------------------------------
    # Retry / failure routing (DEC-009 taxonomy)
    # ------------------------------------------------------------------

    @api.model
    def _route_failure(self, job, error_class, reason, technical_detail=False):
        """Route a classified handler failure to the correct terminal/
        loop-back job state, per the DEC-009 error-class taxonomy
        encoded in this module's constants above."""
        if error_class in MANUAL_REVIEW_ERROR_CLASSES:
            job._transition_blocked_manual_review(
                error_class=error_class,
                manual_review_subreason=error_class,
                message=reason, technical_detail=technical_detail,
            )
            return
        if (
            error_class in MANUAL_FIX_THEN_RETRY_ERROR_CLASSES
            or error_class in CONSERVATIVE_NEVER_SILENT_ERROR_CLASSES
        ):
            job._transition_failed_retryable(
                error_class=error_class, message=reason,
                technical_detail=technical_detail,
            )
            return
        if error_class in AUTO_RETRY_ERROR_CLASSES:
            self._schedule_retry_or_fail(
                job, error_class, reason, technical_detail,
                max_attempts=RETRY_MAX_ATTEMPTS,
            )
            return
        if error_class in SAFETY_NET_ERROR_CLASSES:
            self._schedule_retry_or_fail(
                job, error_class, reason, technical_detail,
                max_attempts=SAFETY_NET_MAX_ATTEMPTS,
            )
            return
        # Unclassified error_class (should never happen -- the fixed
        # 16-class registry is exhaustive) -- fail safe, never hang.
        job._transition_failed_final(
            error_class='unknown_system_error', message=reason,
            technical_detail=technical_detail,
        )

    @api.model
    def _schedule_retry_or_fail(
        self, job, error_class, reason, technical_detail, max_attempts,
    ):
        """Bounded retries only -- no infinite retries under any
        circumstance (DEC-009). Fails permanently once either the
        attempt budget or the 24-hour retry window is exhausted,
        whichever comes first."""
        new_retry_count = job.retry_count + 1
        started_at = job.started_at or fields.Datetime.now()
        elapsed = fields.Datetime.now() - started_at
        if (
            new_retry_count > max_attempts
            or elapsed > timedelta(hours=RETRY_WINDOW_HOURS)
        ):
            # The job did attempt and fail again -- persist the
            # exhausted attempt count (one more than its last recorded
            # retry_count), not just the terminal state.
            job._transition_failed_final(
                error_class=error_class, message=reason,
                technical_detail=technical_detail,
                retry_count=new_retry_count,
            )
            return
        delay_seconds = self._retry_delay_seconds(new_retry_count - 1)
        next_retry_at = fields.Datetime.now() + timedelta(seconds=delay_seconds)
        job._transition_retry_waiting(
            next_retry_at=next_retry_at, retry_count=new_retry_count,
            error_class=error_class, message=reason,
            technical_detail=technical_detail,
        )

    @api.model
    def _retry_delay_seconds(self, attempt_index):
        """Jittered exponential backoff (Decision C): base 30s, x2 per
        attempt, capped at 30 minutes, +/-20% jitter. `attempt_index` is
        zero-based (0 = first retry).

        Tests may patch `random.uniform` for a deterministic value, or
        assert bounds on the returned delay -- this must never be
        flaky by relying on unseeded randomness or wall-clock timing for
        a pass/fail result.
        """
        capped = min(
            RETRY_BASE_DELAY_SECONDS * (RETRY_MULTIPLIER ** attempt_index),
            RETRY_MAX_DELAY_SECONDS,
        )
        jitter_amount = capped * RETRY_JITTER_FRACTION
        return capped + random.uniform(-jitter_amount, jitter_amount)
