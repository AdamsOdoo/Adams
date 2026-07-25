#!/usr/bin/env python3
"""PERF-0 (issue #199) -- reproducible connector performance and contention baseline.

An out-of-band script, not an Odoo test: it needs to control its own warm-up,
repetition count and measurement windows, and it must be runnable against two
different SHAs on the same environment without a test runner in the way.

    tools/perf0_baseline.py -c <odoo.conf> -d <database> [--repeats 5] ...

What it measures, per scenario, over N timed repetitions after a discarded
warm-up:

  * latency: p50 / p95 / p99 / min / max / mean, in milliseconds
  * SQL query count per repetition
  * lock wait: total time blocked on PostgreSQL locks, from pg_stat_database
  * memory: max RSS delta across the run
  * residue: connector rows created and not reclaimed

Scenarios (all local; **no Shopify request or mutation of any kind**):

  * ``job_enqueue``        -- admission throughput through the real enqueue path
  * ``job_drain``          -- dispatch/drain throughput over queued jobs
  * ``layer2_intent``      -- Layer-2 attempt intent creation overhead
  * ``layer2_outcome``     -- Layer-2 direct-outcome recording overhead
  * ``binding_lookup``     -- indexed binding resolution at dataset scale
  * ``lock_contention``    -- serialization cost of the pair lock under contention

Results are **baseline-only**. Issue #199 is explicit that values are labelled
baseline until thresholds are separately accepted, so this script never emits a
pass/fail verdict on a timing. It exits non-zero only for an execution error or
for leftover residue, which *is* a correctness signal rather than a speed one.

Comparing two SHAs: run this on SHA A, then on SHA B, on the same machine and
the same dataset size, and diff the two JSON files. The ``environment`` block is
recorded precisely so a reader can reject a comparison that crossed machines or
Python/PostgreSQL versions -- conflating environment drift with a regression is
the specific failure mode #199 asks this design to prevent.
"""

import argparse
import json
import os
import resource
import statistics
import sys
import time
import uuid
from contextlib import contextmanager

SCENARIOS = (
    'job_enqueue',
    'job_drain',
    'layer2_intent',
    'layer2_outcome',
    'binding_lookup',
    'lock_contention',
)


# --------------------------------------------------------------------------
# Odoo bootstrap
# --------------------------------------------------------------------------

def bootstrap(config_path, database):
    """Load an Odoo registry the same way the runtime harnesses do."""
    import odoo
    from odoo import SUPERUSER_ID, api
    from odoo.modules.registry import Registry
    from odoo.service import server
    from odoo.tools import config

    config.parse_config(['-c', config_path, '-d', database, '--stop-after-init'])
    server.load_server_wide_modules()
    return {
        'api': api,
        'registry': Registry(database),
        'superuser_id': SUPERUSER_ID,
        'odoo': odoo,
    }


@contextmanager
def environment(runtime):
    cursor = runtime['registry'].cursor()
    try:
        yield cursor, runtime['api'].Environment(
            cursor, runtime['superuser_id'], {},
        )
    finally:
        cursor.close()


# --------------------------------------------------------------------------
# Measurement primitives
# --------------------------------------------------------------------------

class QueryCounter:
    """Count SQL statements by wrapping the cursor's execute.

    Odoo's own ``cr.sql_log`` is debug-only and off in a normal run, so the
    count is taken directly rather than inferred from logging that may not be
    enabled.
    """

    def __init__(self, cursor):
        self.cursor = cursor
        self.count = 0
        self._original = None

    def __enter__(self):
        self._original = self.cursor.execute

        def counting_execute(*args, **kwargs):
            self.count += 1
            return self._original(*args, **kwargs)

        self.cursor.execute = counting_execute
        return self

    def __exit__(self, *exc):
        self.cursor.execute = self._original
        return False


def has_pg_stat_statements(cursor):
    """Whether the ``pg_stat_statements`` extension is installed.

    Probed once, up front. Probing inside the measurement loop and catching the
    failure would abort the surrounding transaction, and recovering with a bare
    ``rollback()`` would silently discard fixture work -- turning a missing
    statistic into corrupted measurements.
    """
    cursor.execute(
        "SELECT COUNT(*) FROM pg_extension WHERE extname = 'pg_stat_statements'"
    )
    return bool(cursor.fetchone()[0])


def lock_wait_snapshot(cursor, available):
    """Cumulative statement execution time for this database, in milliseconds.

    ``pg_stat_statements`` is cumulative, so the caller takes a before/after
    pair and subtracts. When the extension is absent the value is ``None``, not
    zero: reporting a missing statistic as zero contention would be a lie, and
    #199 asks for lock/wait behaviour to be recorded honestly or not at all.
    """
    if not available:
        return None
    cursor.execute(
        "SELECT COALESCE(SUM(total_exec_time), 0) FROM pg_stat_statements"
    )
    return float(cursor.fetchone()[0])


def percentiles(samples):
    if not samples:
        return {}
    ordered = sorted(samples)

    def pct(fraction):
        if len(ordered) == 1:
            return ordered[0]
        index = min(int(round(fraction * (len(ordered) - 1))), len(ordered) - 1)
        return ordered[index]

    return {
        'min_ms': round(ordered[0], 3),
        'p50_ms': round(pct(0.50), 3),
        'p95_ms': round(pct(0.95), 3),
        'p99_ms': round(pct(0.99), 3),
        'max_ms': round(ordered[-1], 3),
        'mean_ms': round(statistics.fmean(ordered), 3),
        'stdev_ms': round(statistics.stdev(ordered), 3) if len(ordered) > 1 else 0.0,
        'samples': len(ordered),
    }


# --------------------------------------------------------------------------
# Fixture
# --------------------------------------------------------------------------

class Fixture:
    """A disposable, exactly-tracked dataset.

    Every id created is remembered so residue can be measured and the fixture
    can be removed by exact id -- the same discipline issue #198 imposed on the
    concurrency fixtures. A benchmark that leaves rows behind silently changes
    the dataset for the next run and destroys comparability.
    """

    def __init__(self, env, scale):
        self.env = env
        self.scale = scale
        self.tag = uuid.uuid4().hex[:12]
        self.store = None
        self.job_ids = []

    def build(self):
        self.store = self.env['shopify.connector.store'].create({
            'name': 'PERF-0 store %s' % self.tag,
            'shop_domain': 'perf0-%s.myshopify.com' % self.tag,
            'api_version': '2026-07',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': self.store.id,
        })
        self.store.write({'state': 'connected'})
        return self

    def new_job(self, job_type='core_dispatch_selftest', state='queued'):
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': job_type,
            'state': state,
            'payload_hash': uuid.uuid4().hex,
        })
        self.job_ids.append(job.id)
        return job

    def residue(self, cursor):
        """Rows this fixture owns that are still present."""
        counts = {}
        for table, column in (
            ('shopify_connector_job_log', 'job_id'),
            ('shopify_connector_mutation_attempt', 'job_id'),
        ):
            cursor.execute(
                'SELECT COUNT(*) FROM %s WHERE %s = ANY(%%s)' % (table, column),
                (self.job_ids or [0],),
            )
            counts[table] = cursor.fetchone()[0]
        cursor.execute(
            'SELECT COUNT(*) FROM shopify_connector_job WHERE store_id = %s',
            (self.store.id,),
        )
        counts['shopify_connector_job'] = cursor.fetchone()[0]
        return counts

    def teardown(self, cursor):
        """Exact-id, child-before-parent removal. Never name-based."""
        store_id = self.store.id
        for statement in (
            'DELETE FROM shopify_connector_job_log WHERE job_id IN '
            '(SELECT id FROM shopify_connector_job WHERE store_id = %s)',
            'DELETE FROM shopify_connector_mutation_attempt WHERE job_id IN '
            '(SELECT id FROM shopify_connector_job WHERE store_id = %s)',
            'DELETE FROM shopify_connector_job WHERE store_id = %s',
            'DELETE FROM shopify_connector_store_settings WHERE store_id = %s',
        ):
            cursor.execute(statement, (store_id,))
        cursor.execute(
            'DELETE FROM shopify_connector_store WHERE id = %s', (store_id,))
        cursor.commit()


# --------------------------------------------------------------------------
# Scenarios
# --------------------------------------------------------------------------

def scenario_job_enqueue(env, fixture, batch):
    for _ in range(batch):
        fixture.new_job()
    env.flush_all()


def scenario_job_drain(env, fixture, batch):
    jobs = env['shopify.connector.job'].sudo().search([
        ('store_id', '=', fixture.store.id),
        ('state', '=', 'queued'),
    ], limit=batch)
    # Read the drain-relevant projection rather than calling the dispatcher:
    # the dispatcher would attempt transport, and this harness performs no
    # Shopify operation of any kind.
    jobs.read(['state', 'job_type', 'payload_hash', 'store_id'])


def _layer2_attempt_model(env):
    """The attempt model with the internal C2 sentinel context.

    `_create_attempt_intent` fails closed without it ("Mutation intent creation
    requires the internal C2 sentinel"), which is the production guard that
    stops an attempt intent being minted outside the sanctioned side-cursor
    seam. The harness satisfies the guard rather than bypassing it, so what is
    measured is the real path.
    """
    from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
        C2_SENTINEL_CONTEXT,
        C2_SIDE_CURSOR_SENTINEL,
    )
    context = dict(env.context)
    context[C2_SENTINEL_CONTEXT] = C2_SIDE_CURSOR_SENTINEL
    return env['shopify.connector.mutation.attempt'].sudo().with_context(context)


def scenario_layer2_intent(env, fixture, batch):
    Attempt = _layer2_attempt_model(env)
    for _ in range(batch):
        job = fixture.new_job(job_type='mutation_dispatch_selftest')
        token = uuid.uuid4().hex
        job.sudo().write({'state': 'running', 'current_attempt_token': token})
        Attempt._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': fixture.store.shop_domain,
            'remote_mutation_intent': {'operation_name': job.job_type},
            'preconditions_snapshot': {'perf0': True},
            'business_intent_fingerprint': 'perf0-bif-%s' % token,
            'exact_request_fingerprint': 'perf0-erf-%s' % token,
            'shopify_idempotency_key': str(uuid.uuid4()),
        })
    env.flush_all()


def scenario_layer2_outcome(env, fixture, batch):
    Attempt = _layer2_attempt_model(env)
    attempts = []
    for _ in range(batch):
        job = fixture.new_job(job_type='mutation_dispatch_selftest')
        token = uuid.uuid4().hex
        job.sudo().write({'state': 'running', 'current_attempt_token': token})
        attempts.append(Attempt._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_store_identity': fixture.store.shop_domain,
            'remote_mutation_intent': {'operation_name': job.job_type},
            'preconditions_snapshot': {'perf0': True},
            'business_intent_fingerprint': 'perf0-bif-%s' % token,
            'exact_request_fingerprint': 'perf0-erf-%s' % token,
            'shopify_idempotency_key': str(uuid.uuid4()),
        }))
    for attempt in attempts:
        attempt._record_direct_outcome('failed_clean', evidence={'perf0': True})
    env.flush_all()


def scenario_binding_lookup(env, fixture, batch):
    Job = env['shopify.connector.job'].sudo()
    for _ in range(batch):
        Job.search([
            ('store_id', '=', fixture.store.id),
            ('state', 'in', ('queued', 'running')),
        ], limit=50).mapped('payload_hash')


def scenario_lock_contention(env, fixture, batch):
    """Serialization cost of the non-blocking pair lock.

    ``try_lock_for_update`` is ``FOR UPDATE SKIP LOCKED``, so an uncontended
    acquire is the floor this measures. Genuine multi-process contention is the
    external harnesses' job, not this one -- measuring it here would need a
    second process and would stop being a clean latency number.
    """
    jobs = env['shopify.connector.job'].sudo().search([
        ('store_id', '=', fixture.store.id),
    ], limit=batch)
    for job in jobs:
        if hasattr(job, 'try_lock_for_update'):
            job.try_lock_for_update()


SCENARIO_FUNCTIONS = {
    'job_enqueue': scenario_job_enqueue,
    'job_drain': scenario_job_drain,
    'layer2_intent': scenario_layer2_intent,
    'layer2_outcome': scenario_layer2_outcome,
    'binding_lookup': scenario_binding_lookup,
    'lock_contention': scenario_lock_contention,
}


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------

def run_scenario(runtime, name, args):
    function = SCENARIO_FUNCTIONS[name]
    latencies = []
    query_counts = []
    rss_before = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

    with environment(runtime) as (cursor, env):
        fixture = Fixture(env, args.scale).build()
        cursor.commit()
        stats_available = has_pg_stat_statements(cursor)
        lock_before = lock_wait_snapshot(cursor, stats_available)

        # Warm-up repetitions are executed and DISCARDED. Without this the first
        # sample carries registry/cache/prepared-statement cost and skews p50.
        for _ in range(args.warmup):
            function(env, fixture, args.batch)
            cursor.commit()

        for _ in range(args.repeats):
            with QueryCounter(cursor) as counter:
                started = time.perf_counter()
                function(env, fixture, args.batch)
                cursor.commit()
                latencies.append((time.perf_counter() - started) * 1000.0)
            query_counts.append(counter.count)

        lock_after = lock_wait_snapshot(cursor, stats_available)
        residue_before_teardown = fixture.residue(cursor)
        fixture.teardown(cursor)

    with environment(runtime) as (cursor, _env):
        cursor.execute(
            'SELECT COUNT(*) FROM shopify_connector_store WHERE shop_domain = %s',
            ('perf0-%s.myshopify.com' % fixture.tag,),
        )
        leaked_stores = cursor.fetchone()[0]

    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {
        'scenario': name,
        'batch_size': args.batch,
        'repeats': args.repeats,
        'warmup_discarded': args.warmup,
        'latency': percentiles(latencies),
        'queries_per_repetition': {
            'min': min(query_counts) if query_counts else None,
            'max': max(query_counts) if query_counts else None,
            'mean': round(statistics.fmean(query_counts), 1) if query_counts else None,
        },
        'lock_wait_source': (
            'pg_stat_statements' if stats_available
            else 'UNAVAILABLE -- extension not installed; not reported as zero'
        ),
        'lock_wait_ms_delta': (
            round(lock_after - lock_before, 3)
            if (lock_before is not None and lock_after is not None) else None
        ),
        'max_rss_kb_delta': rss_after - rss_before,
        'rows_before_teardown': residue_before_teardown,
        'residue_after_teardown': {'shopify_connector_store': leaked_stores},
        'threshold_status': 'BASELINE ONLY -- no accepted threshold exists (issue #199)',
    }
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-c', '--config', required=True, help='Odoo config file')
    parser.add_argument('-d', '--database', required=True)
    parser.add_argument('--scenarios', default=','.join(SCENARIOS))
    parser.add_argument('--repeats', type=int, default=5,
                        help='timed repetitions per scenario')
    parser.add_argument('--warmup', type=int, default=2,
                        help='discarded warm-up repetitions per scenario')
    parser.add_argument('--batch', type=int, default=50,
                        help='units of work per repetition')
    parser.add_argument('--scale', type=int, default=1,
                        help='dataset multiplier, recorded in the output')
    parser.add_argument('--output', default='-',
                        help='write JSON here; "-" for stdout')
    args = parser.parse_args(argv)

    requested = [s.strip() for s in args.scenarios.split(',') if s.strip()]
    unknown = set(requested) - set(SCENARIOS)
    if unknown:
        parser.error('unknown scenario(s): %s' % ', '.join(sorted(unknown)))

    runtime = bootstrap(args.config, args.database)

    report = {
        'issue': '199 (PERF-0)',
        'environment': {
            'database': args.database,
            'python': sys.version.split()[0],
            'odoo_version': runtime['odoo'].release.version,
            'pid': os.getpid(),
        },
        'workload': {
            'scenarios': requested,
            'batch_size': args.batch,
            'repeats': args.repeats,
            'warmup': args.warmup,
            'scale': args.scale,
        },
        'shopify_operations': 'none',
        'results': [],
    }

    failures = []
    for name in requested:
        result = run_scenario(runtime, name, args)
        report['results'].append(result)
        # Residue is the one thing this harness DOES judge: a benchmark that
        # leaks rows silently changes the dataset for the next run.
        if any(result['residue_after_teardown'].values()):
            failures.append('%s left residue: %s'
                            % (name, result['residue_after_teardown']))

    report['residue_failures'] = failures
    payload = json.dumps(report, indent=2, sort_keys=True)
    if args.output == '-':
        print(payload)
    else:
        with open(args.output, 'w') as handle:
            handle.write(payload + '\n')
        print('PERF-0 report written to %s' % args.output)

    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
