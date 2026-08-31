"""Stale-owner sweep repository mixin for the V2 runtime.

The sweep intentionally shares the repository transaction and job-first lock
order, but lives separately from claim/finalization to keep the adapter small.
"""

from datetime import datetime, timedelta

from odoo import fields

from ..domain.retry_policy import MAX_SCHEDULED_RETRIES
from ..runtime.p10_coordinator import ClaimedWork
from ..runtime.p10_stale_owner import StaleOwnerInput, StaleOwnerPolicy
from .shopify_connector_v2_runtime_common import (
    V2_RUNTIME_MODE,
    V2_READ_ONLY_RUNTIME_MODES,
    V2_MAX_CLAIM_BATCH,
    _UTC,
    _ACTIVE_RUN_STATES,
    _db_datetime,
    _owner_cleanup,
    _positive_limit,
    _utc,
)


class StaleOwnerRepositoryMixin:
    """Bounded stale-owner recovery operations.

    The host repository supplies _company_ids and _transaction.
    Candidate selection locks jobs first; detail locking then follows the same
    order used by finalization.
    """

    def _finish_cancelled_stale(
        self, side_env, attempt, job, run, finished_at,
    ):
        """Terminalize a stale owner after its run cancellation request.

        Cancellation is an explicit local lifecycle decision.  It does not
        depend on remote-outcome evidence and must never be routed through the
        stale-owner duplicate-risk/verification policy: once the run is
        cancel-requested, the active attempt and its job are durably cancelled
        under the locks acquired by ``_stale_sql``.
        """
        reason = run.cancel_reason or 'Cancellation requested.'
        attempt._finish_service(
            'cancelled',
            safe_message='Read-only work was cancelled before completion.',
            error_class=None,
            error_code='cancellation_requested',
            retry_decision='none',
            next_retry_at=None,
            observations={'cancel_requested': True, 'owner_lost': True},
            finished_at=_db_datetime(finished_at),
        )
        values = _owner_cleanup()
        values.update({
            'state': 'cancelled',
            'error_class': False,
            'next_retry_at': False,
            'cancel_reason': reason,
            'manual_review_subreason': False,
            'finished_at': _db_datetime(finished_at),
        })
        job.sudo().write(values)
        job._log_transition(
            'state_change',
            'Stale V2 read-only owner cancelled by the run request.',
            from_state='running',
            to_state='cancelled',
        )
        # The normal projection reaches the cancelled terminal run once this
        # child is the last active job.  It also preserves the established
        # behavior for a multi-job run whose other children still need their
        # own cancellation sweep pass.
        self._refresh_run_state(side_env, run)

    def _stale_sql(self, env, cutoff, limit, handler_keys):
        # Lock jobs first, then fetch/lock their attempts and scope parents.
        # The first query intentionally locks only ``j``; a multi-table
        # ``FOR UPDATE`` on the candidate scan could let PostgreSQL acquire an
        # attempt before its job and deadlock with finalization.  Once a job is
        # held, detail locks block and follow the same deterministic order as
        # finalization: attempt -> run -> store -> settings.  The final joined
        # read has no lock clause because all five rows are already held.
        companies = self._company_ids(env)
        env.cr.execute(
            """
                SELECT j.id, j.current_attempt_token, j.run_id, j.store_id,
                       j.job_type, j.job_type IN %s AS handler_registered
                  FROM shopify_connector_job j
                  JOIN shopify_connector_job_attempt a ON a.job_id = j.id
                  JOIN shopify_connector_run r
                    ON r.id = j.run_id AND r.store_id = j.store_id
                  JOIN shopify_connector_store s
                    ON s.id = j.store_id AND s.id = r.store_id
                  JOIN shopify_connector_store_settings ss
                    ON ss.store_id = s.id
                 WHERE j.run_id IS NOT NULL
                   AND j.mutation_attempt_id IS NULL
                   AND j.state = 'running'
                   AND j.current_attempt_token = a.claim_token
                   AND a.outcome IN ('claimed', 'running')
                   AND COALESCE(a.heartbeat_at, a.claimed_at) <= %s
                   AND (
                        ss.v2_runtime_mode IN %s
                        OR r.cancel_requested_at IS NOT NULL
                   )
                   AND j.company_id = s.company_id
                   AND r.company_id = s.company_id
                   AND ss.company_id = s.company_id
                   AND s.company_id IN %s
                 ORDER BY COALESCE(a.heartbeat_at, a.claimed_at), a.id
                 LIMIT %s
                 FOR UPDATE OF j SKIP LOCKED
            """,
            [tuple(handler_keys), _db_datetime(cutoff),
             V2_READ_ONLY_RUNTIME_MODES, companies, limit],
        )
        job_rows = tuple(env.cr.fetchall())
        details = []
        for candidate in job_rows:
            job_id = candidate[0]
            # ``current_attempt_token``, ``run_id`` and ``store_id`` were read
            # from the locked job row.  Keeping those identities fixed while
            # acquiring each detail lock prevents a changed relation from
            # making the later scope read lock an unrelated record.
            (
                _job_id, claim_token, run_id, store_id, job_type,
                handler_registered,
            ) = candidate
            env.cr.execute(
                """
                    SELECT id
                      FROM shopify_connector_job_attempt
                     WHERE job_id = %s
                       AND claim_token = %s
                       AND outcome IN ('claimed', 'running')
                       AND COALESCE(heartbeat_at, claimed_at) <= %s
                     FOR UPDATE
                """,
                [job_id, claim_token, _db_datetime(cutoff)],
            )
            attempt_row = env.cr.fetchone()
            if not attempt_row:
                continue
            details.append((
                job_id, claim_token, run_id, store_id, attempt_row[0],
                job_type, bool(handler_registered),
            ))

        if not details:
            return ()
        run_ids = tuple(sorted({row[2] for row in details}))
        store_ids = tuple(sorted({row[3] for row in details}))
        env.cr.execute(
            """SELECT id FROM shopify_connector_run
                 WHERE id IN %s ORDER BY id FOR UPDATE""",
            [run_ids],
        )
        locked_runs = {row[0] for row in env.cr.fetchall()}
        env.cr.execute(
            """SELECT id FROM shopify_connector_store
                 WHERE id IN %s ORDER BY id FOR UPDATE""",
            [store_ids],
        )
        locked_stores = {row[0] for row in env.cr.fetchall()}
        env.cr.execute(
            """SELECT id, store_id
                 FROM shopify_connector_store_settings
                WHERE store_id IN %s
                ORDER BY store_id, id FOR UPDATE""",
            [store_ids],
        )
        settings_by_store = {}
        for settings_id, settings_store_id in env.cr.fetchall():
            settings_by_store.setdefault(settings_store_id, settings_id)

        rows = []
        for (
            job_id, claim_token, run_id, store_id, attempt_id, job_type,
            handler_registered,
        ) in details:
            settings_id = settings_by_store.get(store_id)
            if (
                run_id not in locked_runs
                or store_id not in locked_stores
                or not settings_id
            ):
                continue
            env.cr.execute(
                """
                    SELECT a.id, a.job_id, a.claim_token, a.worker_ref,
                           a.outcome, a.claimed_at, a.heartbeat_at,
                           j.expected_connection_generation,
                           j.expected_configuration_generation,
                           r.id, r.expected_connection_generation,
                           r.expected_configuration_generation,
                           s.connection_generation,
                           ss.configuration_generation, ss.v2_runtime_mode
                      FROM shopify_connector_job j
                      JOIN shopify_connector_job_attempt a
                        ON a.id = %s AND a.job_id = j.id
                       AND a.claim_token = %s
                      JOIN shopify_connector_run r
                        ON r.id = j.run_id AND r.store_id = j.store_id
                      JOIN shopify_connector_store s
                        ON s.id = j.store_id AND s.id = r.store_id
                      JOIN shopify_connector_store_settings ss
                        ON ss.id = %s AND ss.store_id = s.id
                     WHERE j.id = %s
                       AND j.run_id IS NOT NULL
                       AND j.mutation_attempt_id IS NULL
                       AND j.state = 'running'
                       AND j.current_attempt_token = a.claim_token
                       AND a.outcome IN ('claimed', 'running')
                       AND COALESCE(a.heartbeat_at, a.claimed_at) <= %s
                       AND (
                            ss.v2_runtime_mode IN %s
                            OR r.cancel_requested_at IS NOT NULL
                       )
                       AND j.company_id = s.company_id
                       AND r.company_id = s.company_id
                       AND ss.company_id = s.company_id
                       AND s.company_id IN %s
                """,
                [attempt_id, claim_token, settings_id, job_id,
                 _db_datetime(cutoff), V2_READ_ONLY_RUNTIME_MODES, companies],
            )
            row = env.cr.fetchone()
            if row:
                rows.append(row + (job_type, handler_registered))
        return tuple(rows)

    def sweep_stale_read_only(self, *, now=None, limit=V2_MAX_CLAIM_BATCH):
        now = _utc(now or datetime.now(_UTC))
        limit = _positive_limit(limit)
        cutoff = now - timedelta(
            seconds=StaleOwnerPolicy().lease_seconds
            + StaleOwnerPolicy().heartbeat_grace_seconds
        )
        processed = 0
        with self._transaction() as side_env:
            handler_keys = tuple(self._registered_read_only_handler_keys())
            rows = self._stale_sql(side_env, cutoff, limit, handler_keys)
            Attempt = side_env['shopify.connector.job.attempt']
            Job = side_env['shopify.connector.job']
            Run = side_env['shopify.connector.run']
            for row in rows:
                (
                    attempt_id, job_id, token, worker_ref, outcome,
                    claimed_at, heartbeat_at, job_connection,
                    job_configuration, run_id, run_connection,
                    run_configuration, store_connection,
                    settings_configuration, _mode, job_type,
                    handler_registered,
                ) = row
                attempt = Attempt.browse(attempt_id).exists()
                job = Job.browse(job_id).exists()
                run = Run.browse(run_id).exists()
                if not attempt or not job or not run:
                    continue
                store = job.store_id
                settings = side_env[
                    'shopify.connector.store.settings'
                ].search([('store_id', '=', store.id)], limit=1)
                raw_observations = attempt.observations
                observations = (
                    raw_observations
                    if type(raw_observations) is dict else {}
                )
                raw_remote = observations.get('remote_outcome', 'none')
                recovery_count = observations.get('stale_recovery_count', 0)
                if (
                    type(recovery_count) is not int
                    or recovery_count < 0
                ):
                    recovery_count = 999
                scope_stale = (
                    not settings
                    or job.store_id != run.store_id
                    or job.company_id != store.company_id
                    or run.company_id != store.company_id
                    or settings.company_id != store.company_id
                    or store.state != 'connected'
                    or run.state not in _ACTIVE_RUN_STATES
                    or run.cancel_requested_at
                    or _mode not in V2_READ_ONLY_RUNTIME_MODES
                    or job_connection != store_connection
                    or run_connection != store_connection
                    or job_configuration != settings_configuration
                    or run_configuration != settings_configuration
                )
                if run.cancel_requested_at:
                    self._finish_cancelled_stale(
                        side_env, attempt, job, run, now,
                    )
                    processed += 1
                    continue
                if not handler_registered:
                    decision_action = 'quarantine'
                    decision_reason = 'unregistered_read_handler'
                elif type(raw_remote) is not str or raw_remote not in {
                    'none', 'not_attempted', 'pre_send', 'failed_clean',
                    'pending', 'in_flight', 'uncertain', 'succeeded',
                }:
                    decision_action = 'quarantine'
                    decision_reason = 'unknown_remote_outcome'
                else:
                    evidence = StaleOwnerInput(
                        job_id=job_id,
                        attempt_id=attempt_id,
                        attempt_outcome=outcome,
                        claimed_at=_utc(fields.Datetime.to_datetime(claimed_at)),
                        heartbeat_at=(
                            _utc(fields.Datetime.to_datetime(heartbeat_at))
                            if heartbeat_at else None
                        ),
                        now=now,
                        remote_outcome=raw_remote,
                        recovery_count=max(0, recovery_count),
                    )
                    decision = StaleOwnerPolicy().decide(evidence)
                    decision_action = decision.action
                    decision_reason = decision.reason_code
                claim = ClaimedWork(
                    job_id=job_id,
                    store_id=job.store_id.id,
                    company_id=job.company_id.id,
                    run_id=run.id,
                    attempt_no=attempt.attempt_no,
                    claim_token=token,
                    worker_ref=worker_ref,
                    handler_key=job_type,
                    lane=job.lane or 'reconciliation',
                    expected_generation=int(job_connection or 0),
                    expected_configuration_generation=int(
                        job_configuration or 0
                    ),
                )
                if decision_action == 'keep':
                    continue
                if decision_action == 'recover' and not scope_stale:
                    next_count = int(job.retry_count or 0) + 1
                    if next_count > MAX_SCHEDULED_RETRIES:
                        decision_action = 'quarantine'
                        decision_reason = 'stale_recovery_cap_exhausted'
                    else:
                        attempt._finish_service(
                            'owner_lost',
                            safe_message='The previous read worker became stale; '
                            'the read is safely scheduled again.',
                            error_class='shopify_temporary_server_network',
                            error_code=decision_reason,
                            next_retry_at=_db_datetime(now),
                            observations={
                                'stale_recovery_count': next_count,
                                'owner_lost': True,
                            },
                            finished_at=_db_datetime(now),
                        )
                        values = self._owner_cleanup()
                        values.update({
                            'state': 'retry_waiting',
                            'error_class': 'shopify_temporary_server_network',
                            'next_retry_at': _db_datetime(now),
                            'retry_count': next_count,
                            'finished_at': False,
                        })
                        job.sudo().write(values)
                        job._log_transition(
                            'state_change',
                            'Stale V2 read-only owner safely requeued.',
                            from_state='running',
                            to_state='retry_waiting',
                        )
                        self._refresh_run_state(side_env, run)
                        processed += 1
                        continue
                # Verification/quarantine/unknown scope is never replayed as
                # successful work.  It is a bounded manual-review outcome.
                attempt._finish_service(
                    'owner_lost',
                    safe_message='The stale read owner requires operator review.',
                    error_class='duplicate_risk',
                    error_code=decision_reason,
                    retry_decision='review',
                    observations={
                        'owner_lost': True,
                        'stale_action': decision_action,
                        'scope_stale': scope_stale,
                    },
                    finished_at=_db_datetime(now),
                )
                values = self._owner_cleanup()
                values.update({
                    'state': 'blocked_manual_review',
                    'error_class': 'duplicate_risk',
                    'manual_review_subreason': 'duplicate_risk',
                    'finished_at': _db_datetime(now),
                })
                job.sudo().write(values)
                job._log_transition(
                    'state_change',
                    'Stale V2 read-only owner was held for manual review.',
                    from_state='running',
                    to_state='blocked_manual_review',
                )
                self._refresh_run_state(side_env, run)
                processed += 1
        return processed
