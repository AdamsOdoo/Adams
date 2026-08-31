"""Short-transaction Odoo repository for the bounded V2 runtime."""

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
from ..runtime.p10_decisions import KNOWN_ERROR_CLASSES, project_run_state
from ..runtime.contracts import (
    NeedsReview,
    NeedsVerification,
    Retryable,
    Skipped,
    Succeeded,
    TerminalFailure,
)
from ..runtime.p10_sql import build_claim_statement
from ..runtime.p10_repository_locks import lock_claim_batch_scopes
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


_HANDLER_KEYS_UNSET = object()


class OdooReadOnlyRuntimeRepository(StaleOwnerRepositoryMixin):
    """Repository port backed by short-lived Odoo side cursors."""

    def __init__(self, env):
        self.env = env

    @contextmanager
    def _transaction(self):
        cursor = self.env.registry.cursor()
        # Public services authorize first; SQL still enforces scope/generation.
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
    def _claim_sql(cls, env, now, limit, handler_keys):
        """Lock a bounded due set with deterministic priority and SKIP LOCKED.

        ``handler_keys`` is intentionally required at this SQL boundary.  The
        caller must derive it from the committed read-only registry before
        asking PostgreSQL to lock anything; a post-claim Python dispatch check
        would leave pre-C2 mutation rows claimable.
        """
        query, params = build_claim_statement(
            now, cls._company_ids(env), limit, handler_keys=handler_keys,
        )
        env.cr.execute(query, params)
        return tuple(row[0] for row in env.cr.fetchall())

    def _registered_read_only_handler_keys(self):
        """Return the current bounded registry snapshot for legacy callers.

        The coordinator always supplies this snapshot explicitly.  Direct
        adapter callers from older domain tests are kept compatible by
        resolving the same model-level registry, never by widening the SQL
        predicate to every V2 job type.
        """
        registry = self.env[
            'shopify.connector.v2.runtime'
        ]._handler_registry()
        return registry.keys()

    def _lock_claim_batch_scopes(self, side_env, job_ids):
        return lock_claim_batch_scopes(side_env, job_ids)

    def claim_due(
        self, *, now, worker_ref, limit, phase,
        handler_keys=_HANDLER_KEYS_UNSET,
    ):
        self._check_phase(phase, CLAIM_TRANSACTION)
        now = _utc(now)
        worker_ref = _worker(worker_ref)
        limit = _positive_limit(limit)
        if handler_keys is _HANDLER_KEYS_UNSET:
            handler_keys = self._registered_read_only_handler_keys()
        claims = []
        with self._transaction() as side_env:
            job_ids = self._claim_sql(
                side_env, now, limit, handler_keys,
            )
            locked_job_ids = set(
                self._lock_claim_batch_scopes(side_env, job_ids)
            )
            Job = side_env['shopify.connector.job']
            Attempt = side_env['shopify.connector.job.attempt']
            for job_id in job_ids:
                job = Job.browse(job_id).exists()
                if not job:
                    continue
                job.ensure_one()
                if job_id not in locked_job_ids:
                    continue
                # The values below are fresh under the deterministic
                # job->attempt->run->store->settings locks and are copied into
                # the immutable handoff object before the cursor commits.
                job.invalidate_recordset()
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
                        'workflow': run.workflow,
                        'operation': run.operation,
                        # Retry inputs are copied while the claim transaction
                        # owns fresh job/run rows.  Handlers must not read
                        # these lifecycle values back through the long-lived
                        # cron environment: a previous side-cursor
                        # finalization may otherwise leave its ORM cache one
                        # retry behind.
                        'retry_count': int(job.retry_count or 0),
                        'run_requested_at': _utc(
                            fields.Datetime.to_datetime(run.requested_at)
                        ).isoformat(),
                        'res_model': job.res_model or None,
                        'res_id': int(job.res_id) if job.res_id else None,
                        'shopify_target_gid': job.shopify_target_gid or None,
                    },
                ))
        return tuple(claims)

    def _lock_claim(self, side_env, claim):
        # Every finalization starts by locking the job row.  The stale-owner
        # sweep follows this same first step, so those two recovery paths never
        # acquire the attempt lock before the job lock.  Detail rows are then
        # locked one at a time, in this exact blocking order:
        # job -> attempt -> run -> store -> settings.  A multi-table
        # ``FOR UPDATE ... SKIP LOCKED`` clause leaves lock acquisition order
        # to the planner and can report a false claim loss when a detail row is
        # briefly held by a legitimate finalizer; blocking after the job lock
        # avoids that failure while retaining non-blocking candidate choice at
        # the job root.
        side_env.cr.execute(
            """
                SELECT id, store_id, run_id
                  FROM shopify_connector_job
                 WHERE id = %s
                 FOR UPDATE SKIP LOCKED
            """,
            [claim.job_id],
        )
        job_row = side_env.cr.fetchone()
        if not job_row:
            raise V2RuntimeClaimLost(
                'The V2 read-only claim is no longer available.'
            )
        _job_id, store_id, run_id = job_row
        side_env.cr.execute(
            """
                SELECT id
                  FROM shopify_connector_job_attempt
                 WHERE job_id = %s
                   AND claim_token = %s
                 FOR UPDATE
            """,
            [claim.job_id, claim.claim_token],
        )
        attempt_row = side_env.cr.fetchone()
        if not attempt_row:
            raise V2RuntimeClaimLost(
                'The V2 read-only claim is no longer available.'
            )
        attempt_id = attempt_row[0]
        side_env.cr.execute(
            """
                SELECT id
                  FROM shopify_connector_run
                 WHERE id = %s
                 FOR UPDATE
            """,
            [run_id],
        )
        if not side_env.cr.fetchone():
            raise V2RuntimeClaimLost(
                'The V2 read-only claim is no longer available.'
            )
        side_env.cr.execute(
            """
                SELECT id
                  FROM shopify_connector_store
                 WHERE id = %s
                 FOR UPDATE
            """,
            [store_id],
        )
        if not side_env.cr.fetchone():
            raise V2RuntimeClaimLost(
                'The V2 read-only claim is no longer available.'
            )
        side_env.cr.execute(
            """
                SELECT id
                  FROM shopify_connector_store_settings
                 WHERE store_id = %s
                 ORDER BY id
                 LIMIT 1
                 FOR UPDATE
            """,
            [store_id],
        )
        settings_row = side_env.cr.fetchone()
        if not settings_row:
            raise V2RuntimeClaimLost(
                'The V2 read-only claim is no longer available.'
            )
        settings_id = settings_row[0]
        # All five rows are now held by this transaction.  This final read
        # only reconstructs the stable scope tuple consumed by
        # ``_scope_mismatch``; it intentionally has no multi-table lock
        # clause of its own.
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
                    ON a.id = %s AND a.job_id = j.id
                       AND a.claim_token = %s
                  JOIN shopify_connector_run r
                    ON r.id = j.run_id
                  JOIN shopify_connector_store s
                    ON s.id = j.store_id
                  JOIN shopify_connector_store_settings ss
                    ON ss.id = %s AND ss.store_id = s.id
                 WHERE j.id = %s
            """,
            [attempt_id, claim.claim_token, settings_id, claim.job_id],
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
                    error_class=(
                        result.error_class
                        if result.error_class in KNOWN_ERROR_CLASSES
                        else 'unknown_system_error'
                    ),
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
            mapped_error_class, subreason = _manual_reason(result.reason_code)
            error_class = (
                _safe_error_class(result.error_class, mapped_error_class)
                if result.error_class else mapped_error_class
            )
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
        # A terminal computed operation scope must reach PostgreSQL before a
        # domain extension admits a same-scope continuation.  The hook stays
        # inside this finalization transaction: hook failure rolls back the
        # attempt outcome, parent transition and any follow-up admission as
        # one unit, while Shopify I/O remains forbidden here.
        job.flush_recordset(['state', 'operation_scope_key'])
        side_env['shopify.connector.v2.runtime']._finalize_v2_read_result(
            job=job,
            run=run,
            claim=claim,
            result=result,
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
