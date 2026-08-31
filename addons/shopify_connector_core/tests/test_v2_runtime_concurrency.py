"""Genuine PostgreSQL concurrency proofs for the P10 read-only runtime.

The ordinary Odoo test cursor is deliberately shared by ``TransactionCase``.
The support mixin opens pooled ``db_connect`` cursors instead, and these tests
assert distinct backend PIDs before exercising production claim/finalization
transactions.  The suite runner selects this class in its non-standard pass
because the fixtures commit rows and the races need real independent sessions.
"""

from datetime import timedelta
import inspect
import threading
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from ..models.shopify_connector_v2_runtime_repository import (
    OdooReadOnlyRuntimeRepository,
)
from ..runtime.contracts import Succeeded, TerminalFailure
from ..runtime.p10_coordinator import CLAIM_TRANSACTION, FINALIZE_TRANSACTION
from .v2_runtime_concurrency_support import (
    NOW,
    V2RuntimeConcurrencyMixin,
)


@tagged(
    'post_install', '-at_install', '-standard',
    'shopify_connector_v2_runtime_concurrency',
)
class TestV2RuntimeClaimConcurrency(V2RuntimeConcurrencyMixin, TransactionCase):
    """Claim, stale-owner and company-scope proofs on real PostgreSQL PIDs."""

    def test_claim_vs_claim_has_one_owner_and_one_attempt(self):
        """Two concurrent claimers contend on one row; exactly one wins."""
        fixture = self._create_fixture(job_count=1)
        barrier = threading.Barrier(2)
        backend_pids = []
        original_claim_sql = OdooReadOnlyRuntimeRepository._claim_sql

        def synchronized_claim_sql(cls, env, now, limit):
            job_ids = original_claim_sql(env, now, limit)
            # Both callers have executed production's SELECT ... SKIP LOCKED;
            # the winner still holds its row lock while this barrier releases.
            barrier.wait(timeout=self.WORKER_TIMEOUT_SECONDS)
            return job_ids

        def claim_worker(worker_ref):
            cr, env = self._new_env(
                allowed_company_ids=(fixture['stores'][0]['company_id'],),
            )
            try:
                claims = OdooReadOnlyRuntimeRepository(env).claim_due(
                    now=NOW,
                    worker_ref=worker_ref,
                    limit=1,
                    phase=CLAIM_TRANSACTION,
                )
                return tuple(claims)
            finally:
                cr.rollback()
                cr.close()

        # Odoo's preload/test runner holds Registry._lock on the main thread;
        # decouple only that registry lookup for worker Environment creation.
        # PostgreSQL row locks and the production repository remain untouched.
        with patch.object(type(self.registry), '_lock', threading.RLock()), \
             self._real_registry_cursor(backend_pids), patch.object(
                 OdooReadOnlyRuntimeRepository,
                 '_claim_sql',
                 new=classmethod(synchronized_claim_sql),
             ):
            records = self._run_threads({
                'claim-a': lambda: claim_worker('p10-claim-a'),
                'claim-b': lambda: claim_worker('p10-claim-b'),
            })

        self.assertGreaterEqual(len(backend_pids), 2)
        self.assertEqual(
            len(set(backend_pids)), len(backend_pids),
            'concurrent claim transactions reused one PostgreSQL backend',
        )
        claims = [claim for value in records.values() for claim in value]
        self.assertEqual(len(claims), 1, records)
        self.assertEqual(
            sorted(len(value) for value in records.values()), [0, 1],
        )
        job_id = fixture['job_ids'][0]
        observed = self._observe(
            'SELECT state, current_attempt_token, owner_worker_ref '
            'FROM shopify_connector_job WHERE id = %s',
            (job_id,),
        )
        self.assertEqual(observed[0][0], 'running')
        self.assertEqual(observed[0][1], claims[0].claim_token)
        self.assertEqual(observed[0][2], claims[0].worker_ref)
        attempts = self._observe(
            'SELECT attempt_no, claim_token, worker_ref, outcome '
            'FROM shopify_connector_job_attempt WHERE job_id = %s',
            (job_id,),
        )
        self.assertEqual(len(attempts), 1, attempts)
        self.assertEqual(attempts[0][0], 1)
        self.assertEqual(attempts[0][1], claims[0].claim_token)
        self.assertEqual(attempts[0][2], claims[0].worker_ref)
        self.assertEqual(attempts[0][3], 'running')

    def test_finalizer_vs_stale_owner_is_bounded_and_job_first(self):
        """A finalizer holding the job row makes stale sweep skip, not deadlock."""
        fixture = self._create_fixture(job_count=1)
        claims = self._claim_fixture(fixture, limit=1)
        self.assertEqual(len(claims), 1)
        claim = claims[0]

        # Make the committed attempt stale while retaining its real owner
        # token.  The stale policy then has a candidate, and the finalizer can
        # still prove ownership with the same immutable claim handoff.
        stale_at = NOW - timedelta(hours=1)
        cr = self._open_bounded()
        try:
            cr.execute(
                'UPDATE shopify_connector_job_attempt '
                'SET claimed_at = %s, heartbeat_at = %s '
                'WHERE job_id = %s AND claim_token = %s',
                (
                    stale_at.replace(tzinfo=None),
                    stale_at.replace(tzinfo=None),
                    claim.job_id,
                    claim.claim_token,
                ),
            )
            cr.commit()
        finally:
            cr.rollback()
            cr.close()

        finalizer_has_job = threading.Event()
        stale_started = threading.Event()
        original_lock_claim = OdooReadOnlyRuntimeRepository._lock_claim
        original_stale_sql = OdooReadOnlyRuntimeRepository._stale_sql
        lock_source = inspect.getsource(original_lock_claim)
        stale_source = inspect.getsource(original_stale_sql)
        self.assertLess(
            lock_source.index('FOR UPDATE SKIP LOCKED'),
            lock_source.index('FOR UPDATE OF a, r, s, ss SKIP LOCKED'),
            'production finalization must lock the job before detail rows',
        )
        self.assertLess(
            stale_source.index('FOR UPDATE OF j SKIP LOCKED'),
            stale_source.index('FOR UPDATE OF a, r, s, ss SKIP LOCKED'),
            'production stale sweep must lock the job before detail rows',
        )

        def synchronized_lock_claim(repository, side_env, work):
            # Wrap only this connection's execute method.  The original
            # _lock_claim still issues its own first job lock and then its
            # detail lock; the hook pauses after the real first execute has
            # acquired the row lock, before production fetches that result.
            original_execute = side_env.cr.execute
            first_lock_seen = False

            def synchronized_execute(query, *args, **kwargs):
                nonlocal first_lock_seen
                result = original_execute(query, *args, **kwargs)
                normalized = ' '.join(str(query).split()).upper()
                if (
                    not first_lock_seen
                    and 'FROM SHOPIFY_CONNECTOR_JOB' in normalized
                    and 'FOR UPDATE SKIP LOCKED' in normalized
                    and 'FOR UPDATE OF' not in normalized
                ):
                    first_lock_seen = True
                    finalizer_has_job.set()
                    if not stale_started.wait(self.WORKER_TIMEOUT_SECONDS):
                        raise TimeoutError(
                            'stale sweep did not reach its lock query'
                        )
                return result

            with patch.object(
                side_env.cr, 'execute', side_effect=synchronized_execute,
            ):
                return original_lock_claim(repository, side_env, work)

        def synchronized_stale_sql(repository, env, cutoff, limit):
            stale_started.set()
            return original_stale_sql(repository, env, cutoff, limit)

        def finalize_worker():
            cr, env = self._new_env(
                allowed_company_ids=(fixture['stores'][0]['company_id'],),
            )
            try:
                OdooReadOnlyRuntimeRepository(env).finalize_attempt(
                    claim=claim,
                    result=Succeeded({'fixture': 'p10-finalizer'}),
                    finished_at=NOW,
                    phase=FINALIZE_TRANSACTION,
                )
                return 'finalized'
            finally:
                cr.rollback()
                cr.close()

        def stale_worker():
            if not finalizer_has_job.wait(self.WORKER_TIMEOUT_SECONDS):
                raise TimeoutError('finalizer did not acquire the job lock')
            cr, env = self._new_env(
                allowed_company_ids=(fixture['stores'][0]['company_id'],),
            )
            try:
                return OdooReadOnlyRuntimeRepository(env).sweep_stale_read_only(
                    now=NOW, limit=1,
                )
            finally:
                cr.rollback()
                cr.close()

        backend_pids = []
        with patch.object(type(self.registry), '_lock', threading.RLock()), \
             self._real_registry_cursor(backend_pids), patch.object(
                 OdooReadOnlyRuntimeRepository,
                 '_lock_claim',
                 new=synchronized_lock_claim,
             ), patch.object(
                 OdooReadOnlyRuntimeRepository,
                 '_stale_sql',
                 new=synchronized_stale_sql,
             ):
            records = self._run_threads({
                'finalizer': finalize_worker,
                'stale': stale_worker,
            })

        self.assertEqual(records, {
            'finalizer': 'finalized',
            'stale': 0,
        })
        self.assertGreaterEqual(len(backend_pids), 2)
        self.assertEqual(
            len(set(backend_pids)), len(backend_pids),
            'finalizer and stale sweep reused one PostgreSQL backend',
        )
        observed = self._observe(
            'SELECT j.state, a.outcome, r.state '
            'FROM shopify_connector_job j '
            'JOIN shopify_connector_job_attempt a ON a.job_id = j.id '
            'JOIN shopify_connector_run r ON r.id = j.run_id '
            'WHERE j.id = %s',
            (claim.job_id,),
        )
        self.assertEqual(observed, [('succeeded', 'succeeded', 'succeeded')])


@tagged(
    'post_install', '-at_install', '-standard',
    'shopify_connector_v2_runtime_concurrency',
)
class TestV2RuntimeScopeAndProjection(
    V2RuntimeConcurrencyMixin, TransactionCase,
):
    """Company isolation and deterministic terminal projection proofs."""

    def test_company_isolation_excludes_foreign_store_from_claims(self):
        """A company-scoped repository cannot claim another company's job."""
        fixture = self._create_fixture(company_count=2, job_count=1)
        company_a, company_b = fixture['company_ids']
        backend_pids = []
        cr, env = self._new_env(allowed_company_ids=(company_a,))
        try:
            with self._real_registry_cursor(backend_pids):
                claims = OdooReadOnlyRuntimeRepository(env).claim_due(
                    now=NOW,
                    worker_ref='p10-company-a',
                    limit=2,
                    phase=CLAIM_TRANSACTION,
                )
        finally:
            cr.rollback()
            cr.close()

        self.assertEqual(len(backend_pids), 1)
        self.assertEqual(len(claims), 1)
        self.assertEqual(claims[0].company_id, company_a)
        self.assertNotEqual(claims[0].company_id, company_b)
        rows = self._observe(
            'SELECT company_id, state, current_attempt_token '
            'FROM shopify_connector_job WHERE id = ANY(%s) '
            'ORDER BY company_id, id',
            (list(fixture['job_ids']),),
        )
        self.assertEqual(
            rows,
            [(company_a, 'running', claims[0].claim_token),
             (company_b, 'queued', None)],
        )
        attempts = self._observe(
            'SELECT j.company_id, count(a.id) '
            'FROM shopify_connector_job j '
            'LEFT JOIN shopify_connector_job_attempt a ON a.job_id = j.id '
            'WHERE j.id = ANY(%s) '
            'GROUP BY j.company_id ORDER BY j.company_id',
            (list(fixture['job_ids']),),
        )
        self.assertEqual(attempts, [(company_a, 1), (company_b, 0)])

    def test_concurrent_terminal_finalizers_project_partially_succeeded(self):
        """Independent terminal writes converge to one deterministic run state."""
        fixture = self._create_fixture(job_count=2)
        claims = tuple(sorted(
            self._claim_fixture(fixture, limit=2),
            key=lambda claim: claim.job_id,
        ))
        self.assertEqual(len(claims), 2)
        claims_by_job = {claim.job_id: claim for claim in claims}
        succeeded_claim = claims[0]
        failed_claim = claims[1]
        workers_ready = threading.Barrier(2)
        succeeded_done = threading.Event()

        def finalize(work, result, *, wait_for=None, signal=None):
            cr, env = self._new_env(
                allowed_company_ids=(fixture['stores'][0]['company_id'],),
            )
            try:
                workers_ready.wait(timeout=self.WORKER_TIMEOUT_SECONDS)
                if wait_for is not None and not wait_for.wait(
                    self.WORKER_TIMEOUT_SECONDS,
                ):
                    raise TimeoutError(
                        'first terminal finalizer did not commit'
                    )
                OdooReadOnlyRuntimeRepository(env).finalize_attempt(
                    claim=work,
                    result=result,
                    finished_at=NOW,
                    phase=FINALIZE_TRANSACTION,
                )
                return work.job_id
            finally:
                cr.rollback()
                cr.close()
                if signal is not None:
                    signal.set()

        backend_pids = []
        # Both worker environments are opened together.  The second terminal
        # write then waits for the first commit so the shared run lock is
        # handed off deterministically instead of turning SKIP LOCKED into a
        # flaky projection race.
        with patch.object(type(self.registry), '_lock', threading.RLock()), \
             self._real_registry_cursor(backend_pids):
            records = self._run_threads({
                'succeeded': lambda: finalize(
                    succeeded_claim,
                    Succeeded({'terminal': 'success'}),
                    signal=succeeded_done,
                ),
                'failed': lambda: finalize(
                    failed_claim,
                    TerminalFailure(
                        'shopify_user_errors_validation', True,
                        {'terminal': 'failure'},
                    ),
                    wait_for=succeeded_done,
                ),
            })

        self.assertGreaterEqual(len(backend_pids), 2)
        self.assertEqual(
            len(set(backend_pids)), len(backend_pids),
            'terminal finalizers reused one PostgreSQL backend',
        )
        self.assertEqual(records['succeeded'], succeeded_claim.job_id)
        self.assertEqual(records['failed'], failed_claim.job_id)
        projection = self._observe(
            'SELECT state FROM shopify_connector_run WHERE id = %s',
            (fixture['run_ids'][0],),
        )
        self.assertEqual(projection, [('partially_succeeded',)])
        children = self._observe(
            'SELECT id, state, finished_at '
            'FROM shopify_connector_job WHERE run_id = %s ORDER BY id',
            (fixture['run_ids'][0],),
        )
        self.assertEqual(
            [(row[0], row[1], bool(row[2])) for row in children],
            [(succeeded_claim.job_id, 'succeeded', True),
             (failed_claim.job_id, 'failed_final', True)],
        )
        attempts = self._observe(
            'SELECT job_id, outcome, finished_at '
            'FROM shopify_connector_job_attempt '
            'WHERE job_id = ANY(%s) ORDER BY job_id',
            (list(claims_by_job),),
        )
        self.assertEqual(
            [(row[0], row[1], bool(row[2])) for row in attempts],
            [(succeeded_claim.job_id, 'succeeded', True),
             (failed_claim.job_id, 'failed_terminal', True)],
        )


if __name__ == '__main__':
    import unittest

    unittest.main()
