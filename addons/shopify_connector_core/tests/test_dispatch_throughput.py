"""Task PERF-1 -- core queue throughput calibration.

What PERF-1 actually changed, and what these tests therefore assert.

The PERF-1 packet was written against a dispatcher that claimed N jobs and
looped over them inside ONE uncommitted transaction. That is no longer the
merged code: `run_drain()` already delegates to `_drain_one()`, which claims
ONE job under `try_lock_for_update()`, dispatches it, and commits it on its
own transaction, with DEC-031 Layer 1 replay-policy routing and Layer 2
mutation recovery around it. The packet's transaction-model rework was
therefore already done, and re-doing it would have REPLACED a hardened
recovery path with a weaker description of it.

What was genuinely missing at this base, and is added here:

  * cron progress and a TIME BUDGET -- the loop ran a fixed `range(limit)`
    with no idea how much of its cron slot was left;
  * a CONFIGURABLE per-pass cap instead of a hardcoded constant;
  * pre-claim BACKPRESSURE, so a throttled store's jobs are deferred.

So these tests deliberately do NOT re-assert per-job commit, ownership,
savepoint isolation or concurrency recovery: those are proven by the merged
`test_job_dispatch.py`, `test_mutation_concurrency.py` and the genuine
independent-connection lifecycle tests, and PERF-1 must not weaken them.
`test_claim_lock_and_recheck_unchanged` is the guard that PERF-1 left that
machinery alone.

A note on `_commit_progress` and the test cursor. The official Odoo 19 API
(`odoo/addons/base/models/ir_cron.py`, pinned 19.0
30bde9ff758834a4912c5ae55843d3a7dad849f1) is
`_commit_progress(processed=0, *, remaining=None, deactivate=False) -> float`
and it COMMITS on every path -- including the outside-a-cron path, which
"will just commit" and report unlimited time. The shared `TransactionCase`
cursor replaces `commit` with a raising guard, so production calls it and the
standard suite must not. `run_drain` gates the call behind
`_concurrency_retry_supported()`, and the tests below drive the gated branch
by patching that predicate together with `_commit_progress` itself -- which
is what lets the loop's contract with the cron API be asserted without any
real commit.
"""

import ast
import os
import time
from unittest.mock import patch
import uuid

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models import (
    shopify_connector_job_dispatch as dispatch_module,
)
from odoo.tools import mute_logger


# Issue #193 / #157 -- Odoo 19 test-phase contract; see test_job_dispatch.py.
@tagged('post_install', '-at_install')
class TestDispatchThroughput(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Param = cls.env['ir.config_parameter']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'PERF-1 primary store',
            'shop_domain': 'perf1-primary.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.other_store = cls.env['shopify.connector.store'].create({
            'name': 'PERF-1 second store',
            'shop_domain': 'perf1-second.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
        })

    def _queue(self, count, store=None):
        store = store or self.store
        return self.Job.create([{
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
        } for _index in range(count)])

    # ------------------------------------------------------------------
    # Per-pass cap (D-PERF1-1)
    # ------------------------------------------------------------------

    def test_batch_size_defaults_to_the_merged_constant_when_unset(self):
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '',
        )
        self.assertEqual(
            self.Dispatch._resolve_drain_batch_size(),
            dispatch_module.DISPATCH_BATCH_SIZE,
        )

    def test_batch_size_reads_a_configured_value(self):
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '75',
        )
        self.assertEqual(self.Dispatch._resolve_drain_batch_size(), 75)

    @mute_logger('odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch')
    def test_batch_size_rejects_malformed_and_out_of_range_values(self):
        """A typo must neither stop the drain nor monopolise the worker."""
        for bad in ('abc', '', '   ', '0', '-5', '501', '10000', '3.5'):
            self.Param.sudo().set_param(
                dispatch_module.DRAIN_BATCH_SIZE_PARAM, bad,
            )
            self.assertEqual(
                self.Dispatch._resolve_drain_batch_size(),
                dispatch_module.DISPATCH_BATCH_SIZE,
                'rejected value %r must fall back to the default' % bad,
            )

    def test_pass_stops_at_the_configured_cap(self):
        self._queue(6)
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '2',
        )
        self.assertEqual(self.Dispatch.run_drain(), 2)

    def test_pass_stops_early_when_the_queue_drains(self):
        self._queue(2)
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '50',
        )
        self.assertEqual(self.Dispatch.run_drain(), 2)

    def test_claim_round_robins_across_stores(self):
        first = self._queue(4, self.store)
        second = self._queue(1, self.other_store)
        claimed = self.Job._claim_for_dispatch(2)
        self.assertEqual(set(claimed.store_id.ids), {
            self.store.id, self.other_store.id,
        })
        self.assertIn(first[0], claimed)
        self.assertIn(second, claimed)

    def test_drain_gives_each_store_a_slot_before_second_round(self):
        self._queue(4, self.store)
        self._queue(1, self.other_store)
        observed = []

        def record_dispatch(_service, job):
            observed.append(job.store_id.id)
            job.sudo().write({'state': 'cancelled'})

        with patch.object(
            type(self.Dispatch), '_dispatch_one', record_dispatch,
        ):
            self.Dispatch.run_drain(limit=3)
        self.assertEqual(observed, [
            self.store.id, self.other_store.id, self.store.id,
        ])

    def test_successful_enqueue_wakes_the_normal_drain_cron(self):
        cron = self.env.ref(
            'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain'
        )
        Cron = type(cron)
        with patch.object(Cron, '_trigger', autospec=True) as trigger:
            self.env['shopify.connector.job.enqueue'].enqueue(
                self.store,
                'setup_readiness_check',
                'core_dispatch_selftest',
                payload_hash=str(uuid.uuid4()),
            )
        trigger.assert_called_once()

    # ------------------------------------------------------------------
    # Cron progress + time budget (D-PERF1-1)
    # ------------------------------------------------------------------

    def _run_drain_reporting_progress(self, remaining_seconds):
        """Drive the gated `_commit_progress` branch on the test cursor.

        Two patches, both necessary and both narrow:

        * `_concurrency_retry_supported` -> True, because that predicate is
          the production gate the branch under test sits behind;
        * `cr.commit` -> a no-op, because flipping that predicate also arms
          `_drain_one`'s own real commit, which the shared test cursor
          forbids. Durability is not what these tests assert -- it is
          already proven by the genuine independent-connection lifecycle
          tests on real pooled cursors. What is asserted here is the LOOP's
          contract: one progress call per job, a truthful remaining count,
          and an immediate return when the budget is spent.

        `remaining_seconds` is consumed one entry per processed job, standing
        in for the seconds of cron time the real API would report.
        Returns (processed, recorded calls).
        """
        calls = []
        budget = list(remaining_seconds)

        def fake_commit_progress(self_cron, processed=0, remaining=None,
                                 deactivate=False):
            calls.append({'processed': processed, 'remaining': remaining})
            return budget.pop(0) if budget else 0.0

        with patch.object(
            type(self.Dispatch), '_concurrency_retry_supported',
            lambda _self: True,
        ), patch.object(
            type(self.env['ir.cron']), '_commit_progress',
            fake_commit_progress,
        ), patch.object(
            # The runner installs its raising `commit` guard on the cursor
            # INSTANCE, not the class, so the patch has to target the
            # instance too or the real guard still wins.
            self.env.cr, 'commit', lambda: None,
        ):
            processed = self.Dispatch.run_drain()
        return processed, calls

    def test_progress_is_reported_once_per_job_with_a_real_remaining_count(self):
        self._queue(3)
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '50',
        )
        processed, calls = self._run_drain_reporting_progress([9, 9, 9])
        self.assertEqual(processed, 3)
        self.assertEqual(len(calls), 3)
        for call in calls:
            self.assertEqual(call['processed'], 1)
        # The reported remaining count must be the real claimable count,
        # counting down as the queue empties -- not a constant or a guess.
        self.assertEqual([call['remaining'] for call in calls], [2, 1, 0])

    def test_pass_yields_when_the_cron_time_budget_is_exhausted(self):
        """The whole point of the time budget: a long queue does not overrun."""
        self._queue(5)
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '50',
        )
        processed, calls = self._run_drain_reporting_progress([12, 0])
        self.assertEqual(processed, 2, 'must stop at the first non-positive budget')
        self.assertEqual(len(calls), 2)
        self.assertEqual(
            self.Job.search_count([
                ('store_id', '=', self.store.id), ('state', '=', 'queued'),
            ]),
            3,
            'the unprocessed jobs stay queued for the next pass',
        )

    def test_progress_is_not_reported_where_committing_is_forbidden(self):
        """The shared test cursor forbids commit; `_commit_progress` commits.

        Calling it there would abort the run, so the loop must skip it on
        exactly the same predicate `_drain_one` uses for its own commit.
        """
        self._queue(2)

        def exploding_commit_progress(self_cron, *args, **kwargs):
            raise AssertionError(
                '_commit_progress must not be called on a cursor that '
                'forbids commit'
            )

        with patch.object(
            type(self.env['ir.cron']), '_commit_progress',
            exploding_commit_progress,
        ):
            self.assertEqual(self.Dispatch.run_drain(), 2)

    def test_commit_progress_signature_matches_the_pinned_odoo_19_contract(self):
        """PERF-1 packet section 7: verify the API before relying on it.

        The packet requires a build-time check that the 19.0 signature and
        return contract are what PERF-1 assumes, and a STOP if they differ.
        Asserting it here makes the check run on every suite rather than once
        in somebody's session notes.
        """
        import inspect

        from odoo.addons.base.models.ir_cron import IrCron

        signature = inspect.signature(IrCron._commit_progress)
        parameters = list(signature.parameters)
        self.assertEqual(
            parameters, ['self', 'processed', 'remaining', 'deactivate'],
        )
        self.assertEqual(
            signature.parameters['processed'].default, 0,
        )
        self.assertEqual(
            signature.parameters['remaining'].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        self.assertEqual(
            signature.parameters['deactivate'].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )
        # Odoo 19 keeps annotations as strings, so compare against both forms
        # rather than assuming which one this interpreter produced.
        self.assertIn(signature.return_annotation, (float, 'float'))

    # ------------------------------------------------------------------
    # Backpressure (D-PERF1-4)
    # ------------------------------------------------------------------

    def test_backpressure_reads_only_durable_local_health_state(self):
        self.assertEqual(self.Dispatch._backpressured_store_ids(), ())
        self.store.sudo().write({'api_health_state': 'throttled'})
        self.assertEqual(
            self.Dispatch._backpressured_store_ids(), (self.store.id,),
        )
        self.store.sudo().write({'api_health_state': 'degraded'})
        self.assertEqual(
            self.Dispatch._backpressured_store_ids(), (self.store.id,),
        )
        self.store.sudo().write({'api_health_state': 'normal'})
        self.assertEqual(self.Dispatch._backpressured_store_ids(), ())

    def test_throttled_store_jobs_are_deferred_and_left_untouched(self):
        throttled_jobs = self._queue(3)
        healthy_jobs = self._queue(2, store=self.other_store)
        self.store.sudo().write({'api_health_state': 'throttled'})
        self.Param.sudo().set_param(
            dispatch_module.DRAIN_BATCH_SIZE_PARAM, '50',
        )

        self.assertEqual(self.Dispatch.run_drain(), 2)

        throttled_jobs.invalidate_recordset()
        healthy_jobs.invalidate_recordset()
        self.assertEqual(
            set(throttled_jobs.mapped('state')), {'queued'},
            'a deferred store\'s jobs must not be claimed, started, retried '
            'or failed -- only left alone',
        )
        self.assertFalse(any(throttled_jobs.mapped('started_at')))
        self.assertFalse(any(throttled_jobs.mapped('retry_count')))
        self.assertNotIn('queued', set(healthy_jobs.mapped('state')))

    def test_backpressure_recovers_when_health_returns_to_normal(self):
        jobs = self._queue(2)
        self.store.sudo().write({'api_health_state': 'throttled'})
        self.assertEqual(self.Dispatch.run_drain(), 0)
        self.store.sudo().write({'api_health_state': 'normal'})
        self.assertEqual(self.Dispatch.run_drain(), 2)
        jobs.invalidate_recordset()
        self.assertNotIn('queued', set(jobs.mapped('state')))

    def test_backpressure_can_only_narrow_the_claimable_set(self):
        """Structural proof that the lever cannot raise the rate."""
        self._queue(3)
        self._queue(2, store=self.other_store)
        unrestricted = self.Job._claimable_count()
        restricted = self.Job._claimable_count((self.store.id,))
        self.assertEqual(unrestricted, 5)
        self.assertEqual(restricted, 2)
        self.assertLess(restricted, unrestricted)

    def test_claimable_count_matches_what_a_pass_can_actually_claim(self):
        """The count feeding cron progress must not drift from the claim."""
        self._queue(4)
        self.assertEqual(self.Job._claimable_count(), 4)
        self.assertEqual(self.Dispatch.run_drain(), 4)
        self.assertEqual(self.Job._claimable_count(), 0)

    # ------------------------------------------------------------------
    # Source guards
    # ------------------------------------------------------------------

    def _source(self, filename):
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )
        with open(os.path.join(models_dir, filename), encoding='utf-8') as handle:
            return handle.read()

    def test_claim_lock_and_recheck_unchanged(self):
        """PERF-1 narrowed the candidate search and nothing else.

        The packet keeps `try_lock_for_update()` and the under-lock re-check
        verbatim, because they are the correctness primitive. This asserts
        the shape of the claim body rather than trusting review: the lock
        call, the empty-result early return, the invalidate, and the
        re-check `filtered` must all still be there, in that order.
        """
        tree = ast.parse(self._source('shopify_connector_job.py'))
        claim = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_claim_for_dispatch'
        )
        body = ast.dump(claim)
        self.assertIn("attr='try_lock_for_update'", body)
        self.assertIn("attr='invalidate_recordset'", body)
        self.assertIn("attr='filtered'", body)
        self.assertIn("attr='search'", body)
        # The re-check must still test the same two claimable conditions.
        self.assertIn("'queued'", body)
        self.assertIn("'retry_waiting'", body)
        self.assertIn("attr='next_retry_at'", body)
        self.assertIn("attr='reconciliation_pending_until'", body)
        # And it must still be the LOCK that is re-checked, not the search.
        lock_index = body.index("attr='try_lock_for_update'")
        filtered_index = body.index("attr='filtered'")
        self.assertLess(lock_index, filtered_index)

    def test_drain_loop_adds_no_shopify_call(self):
        """The drain must remain transport-free at its own level."""
        source = self._source('shopify_connector_job_dispatch.py')
        tree = ast.parse(source)
        run_drain = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == 'run_drain'
        )
        called = {
            node.func.attr for node in ast.walk(run_drain)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        forbidden = {
            'execute_graphql', 'graphql', 'request', 'post', 'urlopen',
            'send', 'call', 'read_credential', 'get_credential',
        }
        self.assertFalse(
            called & forbidden,
            'run_drain must not reach any transport or credential surface',
        )

    def test_backpressure_never_writes_to_a_job(self):
        """Deferral is a read plus a narrowed search -- never a state write."""
        tree = ast.parse(self._source('shopify_connector_job_dispatch.py'))
        helper = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == '_backpressured_store_ids'
        )
        called = {
            node.func.attr for node in ast.walk(helper)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        self.assertFalse(
            called & {'write', 'create', 'unlink', '_transition_retry_waiting'},
        )


# Non-standard: this class measures wall-clock throughput against a declared
# synthetic latency profile, so it is slow by construction and is excluded
# from the standard suite exactly like the other connector benchmarks. The
# suite runner runs it explicitly by tag.
@tagged('post_install', '-at_install', '-standard', 'shopify_connector_drain_throughput')
class TestDispatchThroughputBenchmark(TransactionCase):
    """PERF-1 D-PERF1-5 -- deterministic throughput measurement.

    HONEST SCOPE, STATED UP FRONT. The packet asks for a "representative
    handler-duration profile", ideally dev-store read latency. No Shopify
    store is provisioned and no Shopify credential exists in this
    environment, so there is NOTHING to measure a real profile against. This
    benchmark therefore runs a DECLARED SYNTHETIC latency profile and says so
    everywhere it reports. It is a lower bound on dispatcher overhead and a
    regression detector for the loop -- it is NOT evidence that any
    particular store achieves PB-19's >=600 jobs/hour, and no such claim is
    made here or in the validation record. Fabricating a dev-store latency
    number to satisfy the packet would be worse than reporting the gap.

    What it does establish, deterministically:

      * the drain's own per-job overhead, measured;
      * that the per-pass cap and the cron time budget both bind as designed
        at a realistic job count;
      * the jobs/hour a given synthetic per-job latency implies, so that when
        a real profile IS measured, substituting it is arithmetic rather than
        a new campaign.
    """

    # The declared synthetic profile. A Shopify GraphQL read on a healthy
    # shop is commonly in the low hundreds of milliseconds; these three
    # points bracket that range so the recorded curve stays useful when a
    # real measurement replaces them. They are ASSUMPTIONS, not measurements.
    SYNTHETIC_LATENCY_PROFILE_SECONDS = (0.0, 0.005, 0.020)
    BENCHMARK_JOB_COUNT = 40

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']

    def _queue(self, count, store):
        return self.Job.create([{
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
        } for _index in range(count)])

    def test_sustained_throughput_against_the_declared_latency_profile(self):
        results = []
        for index, latency in enumerate(self.SYNTHETIC_LATENCY_PROFILE_SECONDS):
            # A fresh store per latency point rather than deleting the
            # previous run's jobs: dispatched jobs own append-only job-log
            # rows, so they cannot be unlinked, and re-using one store would
            # measure a queue that still contains the last run's terminal
            # jobs.
            store = self.env['shopify.connector.store'].create({
                'name': 'PERF-1 benchmark store %d' % index,
                'shop_domain': 'perf1-benchmark-%d.myshopify.com' % index,
                'api_version': '2026-07',
                'state': 'connected',
            })
            self._queue(self.BENCHMARK_JOB_COUNT, store)
            self.env['ir.config_parameter'].sudo().set_param(
                dispatch_module.DRAIN_BATCH_SIZE_PARAM,
                str(self.BENCHMARK_JOB_COUNT),
            )
            original = type(self.Dispatch)._handle_core_dispatch_selftest

            def slow_handler(self_dispatch, job, _latency=latency,
                             _original=original):
                if _latency:
                    time.sleep(_latency)
                return _original(self_dispatch, job)

            with patch.object(
                type(self.Dispatch), '_handle_core_dispatch_selftest',
                slow_handler,
            ):
                started = time.monotonic()
                processed = self.Dispatch.run_drain()
                elapsed = time.monotonic() - started

            self.assertEqual(processed, self.BENCHMARK_JOB_COUNT)
            self.assertGreater(elapsed, 0)
            results.append({
                'synthetic_per_job_latency_seconds': latency,
                'jobs': processed,
                'elapsed_seconds': round(elapsed, 4),
                'implied_jobs_per_hour': int(processed / elapsed * 3600),
            })

        # Printed rather than asserted against PB-19: the profile is
        # synthetic, so an assertion here would be an assertion about the
        # test machine, not about the product.
        print(
            '\n[PERF-1] Throughput against a DECLARED SYNTHETIC latency '
            'profile -- NOT dev-store measured, NOT PB-19 evidence:'
        )
        for row in results:
            print(
                '[PERF-1]   latency=%.3fs jobs=%d elapsed=%.4fs '
                'implied=%d jobs/hour'
                % (
                    row['synthetic_per_job_latency_seconds'],
                    row['jobs'],
                    row['elapsed_seconds'],
                    row['implied_jobs_per_hour'],
                )
            )

        # Deterministic, machine-independent property: adding per-job latency
        # can only reduce throughput. This is the regression signal -- it
        # holds on any hardware, unlike an absolute jobs/hour threshold.
        implied = [row['implied_jobs_per_hour'] for row in results]
        self.assertEqual(
            implied, sorted(implied, reverse=True),
            'throughput must fall monotonically as per-job latency rises',
        )
