"""Odoo repository for bounded V2 claim and finalization transactions.

Claim/finalization use short-lived side cursors and lock the job before
attempt or scope rows.  Stale-owner recovery is supplied by the adjacent
repository mixin so each production file stays focused and reviewable.
"""

from contextlib import contextmanager
from datetime import timedelta
import uuid

from odoo import SUPERUSER_ID, api, fields

from ..domain.retry_policy import MAX_SCHEDULED_RETRIES, RETRY_WINDOW_SECONDS
from ..runtime.p10_coordinator import (
    CLAIM_TRANSACTION,
    FINALIZE_TRANSACTION,
    ClaimedWork,
    RuntimeBoundaryError,
)
from ..runtime.p10_decisions import project_run_state
from ..runtime.contracts import (
    NeedsReview,
    NeedsVerification,
    Retryable,
    Skipped,
    Succeeded,
    TerminalFailure,
)
from ..runtime.p10_sql import build_claim_statement
from .shopify_connector_v2_runtime_common import (
    V2_RUNTIME_MODE,
    runtime_mode_includes,
    _ACTIVE_ATTEMPT_OUTCOMES,
    _ACTIVE_RUN_STATES,
    _GENERATION_ERROR_CLASS,
    _GENERATION_SUBREASON,
    _db_datetime,
    _manual_reason,
    _positive_limit,
    _safe_error_class,
    _safe_observations,
    _safe_transition_message,
    _utc,
    _worker,
    V2RuntimeClaimLost,
)
from .shopify_connector_v2_runtime_stale import StaleOwnerRepositoryMixin


class OdooReadOnlyRuntimeRepository(StaleOwnerRepositoryMixin):
    """Repository port backed by short-lived Odoo side-cursor transactions.

    ``claim_due`` and ``finalize_attempt`` each open, lock, write, commit and
    close their own cursor.  Consequently the coordinator cannot accidentally
    hold an Odoo row lock while a read handler performs Shopify I/O.  The
    explicit commit/rollback hooks are validating no-ops for the pure
    coordinator boundary because this adapter has already closed its side
    cursor before returning.
    """

    def __init__(self, env):
        self.env = env

    @contextmanager
    def _transaction(self):
        cursor = self.env.registry.cursor()
        # All ORM service surfaces used below are intentionally privileged only
        # after the public model service has checked its administrator/cron
        # boundary.  Scope and generation checks remain explicit SQL predicates
        # and are never delegated to sudo/record-rule visibility.  Building
        # the side environment as the Odoo superuser is the supported
        # equivalent of elevating a recordset; ``Environment`` itself is not a
        # recordset and must not rely on a version-specific ``env.sudo()``.
        side_env = api.Environment(cursor, SUPERUSER_ID, dict(self.env.context))
        try:
            yield side_env
            side_env.flush_all()
            cursor.commit()
        except Exception:
            cursor.rollback()
            raise
        finally:
            cursor.close()

    @staticmethod
    def _check_phase(phase, expected):
        if phase != expected:
            raise RuntimeBoundaryError(
                'unexpected runtime transaction phase: %s' % phase
            )

    def commit(self, *, phase):
        """Validate a boundary already closed by the side-cursor adapter."""
        if phase not in (CLAIM_TRANSACTION, FINALIZE_TRANSACTION):
            raise RuntimeBoundaryError('unknown runtime commit phase')

    def rollback(self, *, phase):
        if phase not in (CLAIM_TRANSACTION, FINALIZE_TRANSACTION):
            raise RuntimeBoundaryError('unknown runtime rollback phase')

    @staticmethod
    def _company_ids(env):
        ids = tuple(env.companies.ids)
        return ids or (env.company.id,)

    @classmethod
    def _claim_sql(cls, env, now, limit):
        """Lock a bounded due set with deterministic priority and SKIP LOCKED."""
        query, params = build_claim_statement(
            now, cls._company_ids(env), limit,
        )
        env.cr.execute(query, params)
        return tuple(row[0] for row in env.cr.fetchall())

    def claim_due(self, *, now, worker_ref, limit, phase):
        self._check_phase(phase, CLAIM_TRANSACTION)
        now = _utc(now)
        worker_ref = _worker(worker_ref)
        limit = _positive_limit(limit)
        claims = []
        with self._transaction() as side_env:
            job_ids = self._claim_sql(side_env, now, limit)
            Job = side_env['shopify.connector.job']
            Attempt = side_env['shopify.connector.job.attempt']
            for job_id in job_ids:
                job = Job.browse(job_id).exists()
                if not job:
                    continue
                job.ensure_one()
                # The SQL row lock includes the run/store/settings rows.  The
                # values below are fresh under that lock and are copied into
                # the immutable handoff object before the cursor commits.
                run = job.run_id
                store = job.store_id
                settings = side_env[
                    'shopify.connector.store.settings'
                ].search([('store_id', '=', store.id)], limit=1)
                if not run or not settings:
                    continue
                if (
                    job.company_id != store.company_id
                    or run.company_id != store.company_id
                    or settings.company_id != store.company_id
                    or store.company_id.id not in self._company_ids(side_env)
                    or store.state != 'connected'
                    or not runtime_mode_includes(
                        settings.v2_runtime_mode, V2_RUNTIME_MODE,
                    )
                    or job.expected_connection_generation
                    != store.connection_generation
                    or run.expected_connection_generation
                    != store.connection_generation
                    or job.expected_configuration_generation
                    != settings.configuration_generation
                    or run.expected_configuration_generation
                    != settings.configuration_generation
                    or run.cancel_requested_at
                    or job.state not in ('queued', 'retry_waiting')
                ):
                    continue
                token = str(uuid.uuid4())
                claimed_at = _db_datetime(now)
                attempt = Attempt._create_service({
                    'job_id': job.id,
                    'run_id': run.id,
                    'claim_token': token,
                    'worker_ref': worker_ref,
                    'claimed_at': claimed_at,
                    'observations': {
                        'runtime': 'v2_read_only',
                        'connection_generation': int(
                            store.connection_generation or 0
                        ),
                        'configuration_generation': int(
                            settings.configuration_generation or 0
                        ),
                    },
                })
                # Mark the attempt running before the claim commit.  The
                # transient claimed state is still durable if this transaction
                # fails, because the whole claim rolls back atomically.
                attempt._start_service(started_at=claimed_at)
                from_state = job.state
                job.sudo().write({
                    'state': 'running',
                    'started_at': claimed_at,
                    'current_attempt_token': token,
                    'owner_worker_ref': worker_ref,
                    'running_since': claimed_at,
                })
                job._log_transition(
                    'attempt',
                    'V2 read-only attempt claimed by the bounded runtime.',
                    from_state=from_state,
                    to_state='running',
                )
                if run.state in ('admitted', 'waiting'):
                    run._transition_service('running')
                claims.append(ClaimedWork(
                    job_id=job.id,
                    store_id=store.id,
                    company_id=store.company_id.id,
                    run_id=run.id,
                    attempt_no=attempt.attempt_no,
                    claim_token=token,
                    worker_ref=worker_ref,
                    handler_key=job.job_type,
                    lane=job.lane,
                    expected_generation=int(
                        store.connection_generation or 0
                    ),
                    expected_configuration_generation=int(
                        settings.configuration_generation or 0
                    ),
                    operation_scope_key=job.operation_scope_key or None,
                    payload={
                        'job_type': job.job_type,
                        'operation': run.operation,
                        'res_model': job.res_model or None,
                        'res_id': int(job.res_id) if job.res_id else None,
                        'shopify_target_gid': job.shopify_target_gid or None,
                    },
                ))
        return tuple(claims)

    def _lock_claim(self, side_env, claim):
        # Every finalization starts by locking the job row.  The stale-owner
        # sweep follows this same first step, so those two recovery paths never
        # acquire the attempt lock before the job lock.  The second query then
        # locks the attempt and its scope parents after ownership of the job is
        # established.  Keeping the order explicit matters because a single
        # multi-table ``FOR UPDATE`` clause does not guarantee planner lock
        # order and can otherwise deadlock finalization against stale sweep.
        side_env.cr.execute(
            """
                SELECT id
                  FROM shopify_connector_job
                 WHERE id = %s
                 FOR UPDATE SKIP LOCKED
            """,
            [claim.job_id],
        )
        if not side_env.cr.fetchone():
            raise V2RuntimeClaimLost(
                'The V2 read-only claim is no longer available.'
            )
        side_env.cr.execute(
            """
                SELECT j.id, j.store_id, j.company_id, j.run_id,
                       j.state, j.current_attempt_token,
                       j.owner_worker_ref, j.expected_connection_generation,
                       j.expected_configuration_generation,
                       a.id, a.outcome, a.attempt_no,
                       r.store_id, r.company_id, r.state,
                       r.cancel_requested_at, r.cancel_reason,
                       r.expected_connection_generation,
                       r.expected_configuration_generation,
                       s.company_id, s.state, s.connection_generation,
                       ss.company_id, ss.configuration_generation,
                       ss.v2_runtime_mode
                  FROM shopify_connector_job j
                  JOIN shopify_connector_job_attempt a
                    ON a.job_id = j.id AND a.claim_token = %s
                  JOIN shopify_connector_run r
                    ON r.id = j.run_id
                  JOIN shopify_connector_store s
                    ON s.id = j.store_id
                  JOIN shopify_connector_store_settings ss
                    ON ss.store_id = s.id
                 WHERE j.id = %s
                 FOR UPDATE OF a, r, s, ss SKIP LOCKED
            """,
            [claim.claim_token, claim.job_id],
        )
        row = side_env.cr.fetchone()
        if not row:
            raise V2RuntimeClaimLost(
                'The V2 read-only claim is no longer available.'
            )
        return row

    @staticmethod
    def _scope_mismatch(row, claim, company_ids):
        (
            job_id, store_id, job_company_id, run_id, job_state, token,
            owner, job_connection_generation, job_configuration_generation,
            attempt_id, attempt_outcome, _attempt_no,
            run_store_id, run_company_id, run_state, cancel_requested,
            _cancel_reason, run_connection_generation,
            run_configuration_generation, store_company_id, store_state,
            store_connection_generation, settings_company_id,
            settings_configuration_generation, settings_mode,
        ) = row
        if job_id != claim.job_id or run_id != claim.run_id:
            return 'run_identity'
        if store_id != claim.store_id or run_store_id != claim.store_id:
            return 'store_identity'
        if claim.company_id is None or claim.company_id not in company_ids:
            return 'company_scope'
        if not (
            job_company_id == store_company_id == run_company_id
            == settings_company_id
        ):
            return 'company_identity'
        if claim.company_id != store_company_id:
            return 'company_identity'
        if not runtime_mode_includes(settings_mode, V2_RUNTIME_MODE):
            return 'runtime_mode'
        if store_state != 'connected' or run_state not in _ACTIVE_RUN_STATES:
            return 'store_state'
        if job_state != 'running' or token != claim.claim_token:
            return 'owner'
        if owner != claim.worker_ref or attempt_outcome not in _ACTIVE_ATTEMPT_OUTCOMES:
            return 'owner'
        if (
            job_connection_generation != claim.expected_generation
            or run_connection_generation != claim.expected_generation
            or store_connection_generation != claim.expected_generation
        ):
            return 'connection_generation'
        if (
            job_configuration_generation
            != claim.expected_configuration_generation
            or run_configuration_generation
            != claim.expected_configuration_generation
            or settings_configuration_generation
            != claim.expected_configuration_generation
        ):
            return 'configuration_generation'
        return None

    @staticmethod
    def _owner_cleanup():
        return {
            'current_attempt_token': False,
            'owner_worker_ref': False,
            'running_since': False,
            'reconciliation_pending_until': False,
        }

    def _finish_scope_mismatch(
        self, side_env, row, claim, reason, finished_at,
    ):
        Attempt = side_env['shopify.connector.job.attempt']
        Job = side_env['shopify.connector.job']
        Run = side_env['shopify.connector.run']
        attempt = Attempt.browse(row[9]).exists()
        job = Job.browse(claim.job_id).exists()
        run = Run.browse(claim.run_id).exists()
        if not attempt or not job or not run:
            raise V2RuntimeClaimLost('V2 claim evidence disappeared.')
        attempt._finish_service(
            'manual_review',
            safe_message=(
                'Read-only work was held because its store or configuration '
                'generation changed before finalization.'
            ),
            error_class=_GENERATION_ERROR_CLASS,
            error_code='stale_generation',
            observations={
                'scope_mismatch': reason,
                'connection_generation': claim.expected_generation,
                'configuration_generation': (
                    claim.expected_configuration_generation
                ),
            },
            finished_at=_db_datetime(finished_at),
        )
        values = self._owner_cleanup()
        values.update({
            'state': 'blocked_manual_review',
            'error_class': _GENERATION_ERROR_CLASS,
            'manual_review_subreason': _GENERATION_SUBREASON,
            'finished_at': _db_datetime(finished_at),
        })
        job.sudo().write(values)
        job._log_transition(
            'state_change',
            'V2 read-only work was blocked by a stale scope generation.',
            from_state='running',
            to_state='blocked_manual_review',
        )
        self._refresh_run_state(side_env, run)

    def _finish_cancelled(self, side_env, row, claim, finished_at):
        Attempt = side_env['shopify.connector.job.attempt']
        Job = side_env['shopify.connector.job']
        Run = side_env['shopify.connector.run']
        attempt = Attempt.browse(row[9]).exists()
        job = Job.browse(claim.job_id).exists()
        run = Run.browse(claim.run_id).exists()
        if not attempt or not job or not run:
            raise V2RuntimeClaimLost('V2 cancellation evidence disappeared.')
        attempt._finish_service(
            'cancelled',
            safe_message='Read-only work was cancelled before completion.',
            error_code='cancellation_requested',
            observations={'cancel_requested': True},
            finished_at=_db_datetime(finished_at),
        )
        values = self._owner_cleanup()
        values.update({
            'state': 'cancelled',
            'cancel_reason': run.cancel_reason or 'Cancellation requested.',
            'manual_review_subreason': False,
            'finished_at': _db_datetime(finished_at),
        })
        job.sudo().write(values)
        job._log_transition(
            'state_change',
            'V2 read-only work cancelled by the run request.',
            from_state='running',
            to_state='cancelled',
        )
        self._refresh_run_state(side_env, run)

    def _finish_result(self, side_env, row, claim, result, finished_at):
        Attempt = side_env['shopify.connector.job.attempt']
        Job = side_env['shopify.connector.job']
        Run = side_env['shopify.connector.run']
        attempt = Attempt.browse(row[9]).exists()
        job = Job.browse(claim.job_id).exists()
        run = Run.browse(claim.run_id).exists()
        if not attempt or not job or not run:
            raise V2RuntimeClaimLost('V2 finalization evidence disappeared.')

        observations = _safe_observations(result)
        now_db = _db_datetime(finished_at)
        values = self._owner_cleanup()
        job_outcome = 'succeeded'
        attempt_outcome = 'succeeded'
        error_class = False
        error_code = False
        safe_message = 'V2 read-only operation completed.'
        retry_decision = 'none'
        next_retry_at = False

        if isinstance(result, Succeeded):
            job_outcome = 'succeeded'
        elif isinstance(result, Skipped):
            job_outcome = 'skipped'
            observations['job_outcome'] = 'skipped'
            observations['skip_reason'] = result.reason
            safe_message = 'V2 read-only operation was skipped: %s' % result.reason
        elif isinstance(result, Retryable):
            error_class = _safe_error_class(result.error_class)
            retry_time = _utc(result.retry_at)
            run_requested = _utc(
                fields.Datetime.to_datetime(run.requested_at)
            )
            retry_number = int(job.retry_count or 0) + 1
            if (
                error_class != result.error_class
                or retry_number > MAX_SCHEDULED_RETRIES
                or retry_time <= _utc(finished_at)
                or retry_time > run_requested + timedelta(
                    seconds=RETRY_WINDOW_SECONDS
                )
            ):
                result = NeedsReview(
                    'retry_cap_or_schedule_invalid',
                    'Review the read operation retry evidence before retrying.',
                    observations,
                )
            else:
                job_outcome = 'retry_waiting'
                attempt_outcome = 'retry_scheduled'
                retry_decision = 'retry'
                next_retry_at = _db_datetime(retry_time)
                safe_message = 'V2 read-only operation scheduled for retry.'
                observations['retry_number'] = retry_number
        if isinstance(result, NeedsVerification):
            # A P10 handler is non-mutation by construction.  A verification
            # result that names mutation evidence is therefore a contract
            # violation, never an invitation to admit a mutation handler.
            result = NeedsReview(
                'read_only_verification_unsupported',
                'Review the read handler contract; mutation verification is not '
                'admitted by the read-only runtime.',
                observations,
            )
        if isinstance(result, NeedsReview):
            error_class, subreason = _manual_reason(result.reason_code)
            job_outcome = 'blocked_manual_review'
            attempt_outcome = 'manual_review'
            retry_decision = 'review'
            safe_message = result.required_action
            error_code = result.reason_code[:128]
            observations['manual_review'] = True
            values['manual_review_subreason'] = subreason
        elif isinstance(result, TerminalFailure):
            error_class = _safe_error_class(result.error_class)
            if error_class != result.error_class:
                error_code = 'unknown_error_class'
            job_outcome = 'failed_final'
            attempt_outcome = 'failed_terminal'
            retry_decision = 'terminal'
            safe_message = 'V2 read-only operation failed permanently.'
        elif isinstance(result, (Succeeded, Skipped)):
            values['manual_review_subreason'] = False
        elif isinstance(result, Retryable):
            # Valid retry path was handled above.  The converted NeedsReview
            # path is handled by the branch immediately preceding this one.
            if job_outcome != 'retry_waiting':
                error_class, subreason = _manual_reason(
                    'retry_cap_or_schedule_invalid'
                )
                job_outcome = 'blocked_manual_review'
                attempt_outcome = 'manual_review'
                retry_decision = 'review'
                error_code = 'retry_cap_or_schedule_invalid'
                values['manual_review_subreason'] = subreason
                safe_message = (
                    'Review the read operation retry evidence before retrying.'
                )

        # Handler-provided reasons/actions are untrusted operator text.  The
        # attempt model applies its own field sanitizer, but this local value
        # is also sent to the append-only job log below, whose legacy redactor
        # does not cover email/phone patterns or length bounds.
        safe_message = _safe_transition_message(
            safe_message,
            'The V2 read-only operation requires operator review.',
        )
        if attempt_outcome == 'retry_scheduled':
            attempt._finish_service(
                attempt_outcome,
                safe_message=safe_message,
                error_class=error_class,
                error_code=error_code,
                retry_decision=retry_decision,
                next_retry_at=next_retry_at,
                observations=observations,
                finished_at=now_db,
            )
            values.update({
                'state': 'retry_waiting',
                'error_class': error_class,
                'next_retry_at': next_retry_at,
                'retry_count': int(job.retry_count or 0) + 1,
                'finished_at': False,
            })
        else:
            attempt._finish_service(
                attempt_outcome,
                safe_message=safe_message,
                error_class=error_class,
                error_code=error_code,
                retry_decision=retry_decision,
                observations=observations,
                finished_at=now_db,
            )
            values.update({
                'state': job_outcome,
                'error_class': error_class or False,
                'next_retry_at': False,
                'finished_at': now_db,
            })
        job.sudo().write(values)
        job._log_transition(
            'state_change',
            safe_message,
            from_state='running',
            to_state=job_outcome,
        )
        self._refresh_run_state(side_env, run)

    def finalize_attempt(
        self, *, claim, result, finished_at, phase,
    ):
        self._check_phase(phase, FINALIZE_TRANSACTION)
        if not isinstance(claim, ClaimedWork):
            raise TypeError('claim must be a ClaimedWork value')
        if not isinstance(
            result,
            (Succeeded, Skipped, Retryable, NeedsVerification,
             NeedsReview, TerminalFailure),
        ):
            raise TypeError('result must be a typed read-handler outcome')
        finished_at = _utc(finished_at)
        with self._transaction() as side_env:
            row = self._lock_claim(side_env, claim)
            mismatch = self._scope_mismatch(
                row, claim, self._company_ids(side_env),
            )
            if mismatch == 'owner':
                raise V2RuntimeClaimLost(
                    'The V2 read-only claim owner changed before finalization.'
                )
            if mismatch:
                self._finish_scope_mismatch(
                    side_env, row, claim, mismatch, finished_at,
                )
                return
            if row[15]:  # run.cancel_requested_at
                self._finish_cancelled(side_env, row, claim, finished_at)
                return
            self._finish_result(side_env, row, claim, result, finished_at)

    @staticmethod
    def _refresh_run_state(side_env, run):
        if not run or not run.exists() or run.state in (
            'succeeded', 'partially_succeeded', 'failed_terminal', 'cancelled',
        ):
            return
        side_env.cr.execute(
            """
                SELECT state, COUNT(*)
                  FROM shopify_connector_job
                 WHERE run_id = %s
                 GROUP BY state
            """,
            [run.id],
        )
        counts = {state: int(count) for state, count in side_env.cr.fetchall()}
        target = project_run_state(
            counts, cancel_requested=bool(run.cancel_requested_at),
        )
        if target == run.state:
            return
        if target in (
            'succeeded', 'partially_succeeded', 'failed_terminal', 'cancelled',
        ):
            run._finish_service(target, finished_at=fields.Datetime.now())
        else:
            run._transition_service(target)
