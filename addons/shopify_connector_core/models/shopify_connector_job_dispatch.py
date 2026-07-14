from datetime import timedelta
import random

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..tools.redaction import redact
from .shopify_connector_job import BUSINESS_JOB_SOURCES, MANUAL_REVIEW_SUBREASON_SELECTION

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
    direct `job.log.create()` call, no `sudo()`, no live Shopify API
    call anywhere in this file.
    """

    _name = 'shopify.connector.job.dispatch'
    _description = 'Shopify Connector Job Dispatch Service'

    # ------------------------------------------------------------------
    # ir.cron entry point
    # ------------------------------------------------------------------

    @api.model
    def run_drain(self, limit=DISPATCH_BATCH_SIZE):
        """Claim and dispatch up to `limit` jobs -- the `ir.cron` target."""
        Job = self.env['shopify.connector.job']
        claimed = Job._claim_for_dispatch(limit)
        for job in claimed:
            self._dispatch_one(job)

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
        either gate: `job.write()` itself still raises exactly as
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
            job.write({
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
        job.write({
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
