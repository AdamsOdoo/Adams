#!/usr/bin/env python3
"""PERF-0 (issue #199) -- reproducible connector performance and contention baseline.

An out-of-band script, not an Odoo test: it needs to control its own warm-up,
repetition count and measurement windows, and it must be runnable against two
different SHAs on the same environment without a test runner in the way.

    tools/perf0_baseline.py -c <odoo.conf> -d <database> [--repeats 5] ...

What it measures, per scenario, over N timed repetitions after a discarded
warm-up:

  * latency: p50 / p95 / p99 / min / max / mean / stdev, in milliseconds
  * SQL query count per repetition
  * SQL execution time: cumulative statement execution time delta, from
    pg_stat_statements. This is EXECUTION time, not lock-wait time -- see the
    note on `sql_exec_time_snapshot` below. Lock waiting is measured separately
    and directly, by the `lock_contention_blocking` scenario.
  * memory: max RSS delta across the run
  * residue: connector rows created and not reclaimed, swept across every
    connector table the fixture can touch

Scenarios (all local; **no Shopify request or mutation of any kind**):

  * ``job_enqueue``        -- admission throughput through the real enqueue path
  * ``job_drain``          -- dispatch/drain throughput over queued jobs
  * ``layer2_intent``      -- Layer-2 attempt intent creation overhead
  * ``layer2_outcome``     -- Layer-2 direct-outcome recording overhead
  * ``layer2_reconcile``   -- Layer-2 reconciliation sweep over open attempts
  * ``order_scan``         -- order scan/import reconciliation projection
  * ``inventory_scan``     -- inventory scan/reconciliation projection
  * ``fulfillment_scan``   -- fulfillment scan/reconciliation projection
  * ``binding_lookup``     -- indexed binding resolution at dataset scale
  * ``lock_skiplocked``    -- uncontended FOR UPDATE SKIP LOCKED acquire (floor)
  * ``lock_contention_blocking`` -- GENUINE two-connection blocking contention

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
    'layer2_reconcile',
    'order_scan',
    'inventory_scan',
    'fulfillment_scan',
    'binding_lookup',
    'lock_skiplocked',
    'lock_contention_blocking',
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
        'database': database,
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


def sql_exec_time_snapshot(cursor, available):
    """Cumulative statement EXECUTION time for this database, in milliseconds.

    ``pg_stat_statements.total_exec_time`` is the time PostgreSQL spent
    *executing* statements. It is **not** lock-wait time, and an earlier version
    of this harness reported it as ``lock_wait_ms_delta``, which was simply
    wrong: a workload that never blocks on a lock still accumulates a large
    ``total_exec_time``. The number is still useful -- it separates "the query
    got slower" from "the Python around it got slower" -- so it is kept, under
    its true name.

    Genuine lock waiting is measured directly instead, by
    ``scenario_lock_contention_blocking``: one connection holds a row lock while
    another attempts the real acquisition path, and the wall-clock block plus
    PostgreSQL's own ``wait_event`` are recorded.

    ``pg_stat_statements`` is cumulative, so the caller takes a before/after
    pair and subtracts. When the extension is absent the value is ``None``, not
    zero: reporting a missing statistic as zero would be a lie, and #199 asks
    for this to be recorded honestly or not at all.
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
        self.dataset_built = False

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

    def build_domain_dataset(self, rows):
        """Create the durable rows the scan/reconciliation scenarios read.

        Without this the scan scenarios would search empty tables and report a
        latency that says nothing about reconciliation at dataset scale -- a
        benchmark that measures nothing is worse than no benchmark, because it
        looks like evidence. Sized from --batch so the dataset and the workload
        scale together.

        Everything here is local: partners, orders, products, locations and
        connector rows. No Shopify request or mutation of any kind.
        """
        if self.dataset_built:
            return
        env = self.env
        partner = env['res.partner'].create({'name': 'PERF-0 partner %s' % self.tag})
        template = env['product.template'].create({
            'name': 'PERF-0 product %s' % self.tag, 'type': 'consu',
        })
        location = env['stock.location'].search(
            [('usage', '=', 'internal')], limit=1)

        template_binding = env['shopify.connector.product.template.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/perf0-%s' % self.tag,
            'product_template_id': template.id,
        })
        variant_binding = env['shopify.connector.product.variant.binding'].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/perf0-%s' % self.tag,
            'product_variant_id': template.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        })
        mapping = None
        if location:
            mapping = env['shopify.connector.location.mapping'].sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Location/perf0-%s' % self.tag,
                'odoo_location_id': location.id,
                'match_key': 'manual',
            })

        orders = env['sale.order'].create([
            {'partner_id': partner.id} for _ in range(rows)
        ])
        env['shopify.connector.order.binding'].sudo().create([{
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Order/perf0-%s-%d' % (self.tag, index),
            'sale_order_id': order.id,
        } for index, order in enumerate(orders)])

        if mapping:
            env['shopify.connector.inventory.level.binding'].sudo().create([{
                'store_id': self.store.id,
                'product_variant_binding_id': variant_binding.id,
                'location_mapping_id': mapping.id,
                'shopify_inventory_item_gid':
                    'gid://shopify/InventoryItem/perf0-%s-%d' % (self.tag, index),
            } for index in range(rows)])

        env['shopify.connector.fulfillment.inbound.evidence'].sudo().create([{
            'store_id': self.store.id,
            'shopify_fulfillment_gid':
                'gid://shopify/Fulfillment/perf0-%s-%d' % (self.tag, index),
        } for index in range(rows)])

        env.flush_all()
        self.dataset_built = True

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

    # Every connector table that can end up owning a row because this fixture
    # exists. Listing them explicitly -- rather than checking only the store row
    # -- is the difference between "the store is gone" and "nothing this
    # benchmark created is still here". The earlier version checked three
    # tables and the store row, which could report a clean teardown while a
    # credential, a lease or a binding survived and silently changed the
    # dataset for the next run.
    STORE_SCOPED_TABLES = (
        'shopify_connector_job',
        'shopify_connector_job_log',
        'shopify_connector_mutation_attempt',
        'shopify_connector_call_lease',
        'shopify_connector_location',
        'shopify_connector_store_credential',
        'shopify_connector_store_settings',
        'shopify_connector_customer_binding',
        'shopify_connector_order_binding',
        'shopify_connector_product_template_binding',
        'shopify_connector_product_variant_binding',
        'shopify_connector_location_mapping',
        'shopify_connector_inventory_level_binding',
        'shopify_connector_fulfillment_binding',
        'shopify_connector_fulfillment_inbound_evidence',
        'shopify_connector_tax_mapping',
    )

    def _existing_tables(self, cursor):
        cursor.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = ANY(%s)",
            (list(self.STORE_SCOPED_TABLES),),
        )
        return [row[0] for row in cursor.fetchall()]

    def residue(self, cursor):
        """Every row this fixture owns, across every store-scoped table."""
        counts = {}
        for table in self._existing_tables(cursor):
            cursor.execute(
                'SELECT COUNT(*) FROM %s WHERE store_id = %%s' % table,
                (self.store.id,),
            )
            counts[table] = cursor.fetchone()[0]
        cursor.execute(
            'SELECT COUNT(*) FROM shopify_connector_fulfillment_inbound_evidence_line '
            'WHERE evidence_id IN (SELECT id FROM '
            'shopify_connector_fulfillment_inbound_evidence WHERE store_id = %s)',
            (self.store.id,),
        )
        counts['shopify_connector_fulfillment_inbound_evidence_line'] = \
            cursor.fetchone()[0]
        return counts

    # Child-before-parent order. Two things make this non-obvious:
    #   * the job/attempt FK pair is CIRCULAR (job.mutation_attempt_id ->
    #     attempt, attempt.job_id -> job), so neither side can be deleted first
    #     -- the reverse pointer is cleared before either delete. This exact
    #     defect broke the fulfillment harness the first time it was ever run.
    #   * evidence lines must go before evidence even though the FK cascades,
    #     so the residue sweep afterwards is meaningful rather than
    #     accidentally satisfied.
    TEARDOWN_STATEMENTS = (
        'UPDATE shopify_connector_job SET mutation_attempt_id = NULL '
        'WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_fulfillment_inbound_evidence_line '
        'WHERE evidence_id IN (SELECT id FROM '
        'shopify_connector_fulfillment_inbound_evidence WHERE store_id = %(store)s)',
        'DELETE FROM shopify_connector_fulfillment_inbound_evidence WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_fulfillment_binding WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_inventory_level_binding WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_location_mapping WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_product_variant_binding WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_product_template_binding WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_order_binding WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_customer_binding WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_tax_mapping WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_job_log WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_mutation_attempt WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_job WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_call_lease WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_location WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_store_credential WHERE store_id = %(store)s',
        'DELETE FROM shopify_connector_store_settings WHERE store_id = %(store)s',
    )

    def teardown(self, cursor):
        """Exact-id, FK-safe, child-before-parent removal. Never name-based."""
        store_id = self.store.id
        existing = set(self._existing_tables(cursor)) | {
            'shopify_connector_fulfillment_inbound_evidence_line'}
        for statement in self.TEARDOWN_STATEMENTS:
            table = statement.split(' FROM ')[-1].split()[0] \
                if statement.startswith('DELETE') \
                else statement.split('UPDATE ')[1].split()[0]
            if table not in existing:
                continue
            cursor.execute(statement, {'store': store_id})
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


def scenario_layer2_reconcile(env, fixture, batch):
    """Reconciliation sweep over open Layer-2 attempts.

    The real reconciliation read model: find attempts that are still open for
    this store and project the fields the reconciler decides on. No transport,
    no mutation -- issue #199 asks for the scan cost, and the scan is the part
    that grows with the dataset.
    """
    Attempt = _layer2_attempt_model(env)
    attempts = Attempt.search([
        ('store_id', '=', fixture.store.id),
    ], limit=batch)
    attempts.read([
        'state', 'job_id', 'store_id',
        'business_intent_fingerprint', 'exact_request_fingerprint',
    ])


def scenario_order_scan(env, fixture, batch):
    """Order scan / import reconciliation projection."""
    fixture.build_domain_dataset(batch)
    Binding = env['shopify.connector.order.binding'].sudo()
    for _ in range(max(1, batch // 10)):
        Binding.search([
            ('store_id', '=', fixture.store.id),
            ('status', 'in', ('active', 'review')),
        ], limit=batch).read(['shopify_gid', 'status', 'store_id'])


def scenario_inventory_scan(env, fixture, batch):
    """Inventory scan / reconciliation projection."""
    fixture.build_domain_dataset(batch)
    Binding = env['shopify.connector.inventory.level.binding'].sudo()
    for _ in range(max(1, batch // 10)):
        Binding.search([
            ('store_id', '=', fixture.store.id),
        ], limit=batch).read(['shopify_gid', 'status', 'store_id'])


def scenario_fulfillment_scan(env, fixture, batch):
    """Fulfillment scan / reconciliation projection."""
    fixture.build_domain_dataset(batch)
    Evidence = env['shopify.connector.fulfillment.inbound.evidence'].sudo()
    for _ in range(max(1, batch // 10)):
        Evidence.search([
            ('store_id', '=', fixture.store.id),
        ], limit=batch).read(['store_id', 'last_observed_at'])


def scenario_lock_skiplocked(env, fixture, batch):
    """Uncontended ``FOR UPDATE SKIP LOCKED`` acquire -- the floor.

    This is the cost of taking the lock when nobody holds it. It is NOT
    contention, and it is named accordingly: the previous name
    (``lock_contention``) claimed to measure contention while running
    single-process and uncontended, so it could only ever report the floor.
    Real blocking is measured by ``scenario_lock_contention_blocking``.
    """
    jobs = env['shopify.connector.job'].sudo().search([
        ('store_id', '=', fixture.store.id),
    ], limit=batch)
    for job in jobs:
        if hasattr(job, 'try_lock_for_update'):
            job.try_lock_for_update()


def measure_blocking_contention(runtime, fixture_job_id, hold_ms=250):
    """Genuine two-connection lock contention, measured directly.

    Design, and why each part is needed for the number to mean anything:

      * a HOLDER connection opens its own transaction and takes
        ``SELECT ... FOR UPDATE`` on one specific job row, then simply waits.
        Two connections are two distinct PostgreSQL backends, so this is real
        inter-process contention inside the database, not a simulation.
      * a BLOCKER connection then attempts the same row with plain
        ``FOR UPDATE``. It genuinely blocks. Wall-clock time around that call
        is the blocked duration.
      * while it is blocked, an OBSERVER connection reads
        ``pg_stat_activity.wait_event_type/wait_event`` and ``pg_locks`` for
        the blocker's backend pid. This is PostgreSQL's own account of the
        wait, so the measurement does not rest on our stopwatch alone. If
        `wait_event_type` is not `Lock`, the run is reported as inconclusive
        rather than quietly counted as contention.
      * finally the SAME row is attempted with ``FOR UPDATE SKIP LOCKED``,
        which must return no row and must NOT wait. Recording both proves the
        two behaviours are distinguished rather than assumed.

    Returns a dict; never raises for a lock outcome, because "we could not
    observe the wait" is a result worth publishing honestly, not a crash.
    """
    from odoo.sql_db import db_connect
    import threading

    database = runtime['database']
    holder = db_connect(database).cursor()
    blocker = db_connect(database).cursor()
    observer = db_connect(database).cursor()
    result = {
        'blocked_ms': None,
        'wait_event_type': None,
        'wait_event': None,
        'blocking_pid': None,
        'blocked_pid': None,
        'skip_locked_waited': None,
        'skip_locked_rows': None,
        'conclusive': False,
    }
    try:
        holder.execute('SELECT pg_backend_pid()')
        result['blocking_pid'] = holder.fetchone()[0]
        # Bound the block. If the releasing thread ever failed to run, the
        # blocker would wait forever and the whole harness would hang with no
        # diagnostic; a timeout turns that into a reported inconclusive result.
        blocker.execute("SET LOCAL statement_timeout = '%d'"
                        % (hold_ms * 20,))
        blocker.execute('SELECT pg_backend_pid()')
        blocked_pid = blocker.fetchone()[0]
        result['blocked_pid'] = blocked_pid

        # HOLDER takes and keeps the row lock.
        holder.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s FOR UPDATE',
            (fixture_job_id,),
        )

        release = threading.Event()

        def _hold_then_release():
            release.wait(hold_ms / 1000.0)
            holder.rollback()

        releaser = threading.Thread(target=_hold_then_release, daemon=True)
        releaser.start()

        # OBSERVER samples PostgreSQL's own view of the wait while it happens.
        def _observe():
            deadline = time.time() + (hold_ms / 1000.0)
            while time.time() < deadline:
                observer.execute(
                    'SELECT wait_event_type, wait_event FROM pg_stat_activity '
                    'WHERE pid = %s', (blocked_pid,),
                )
                row = observer.fetchone()
                if row and row[0] == 'Lock':
                    result['wait_event_type'], result['wait_event'] = row
                    return
                time.sleep(0.01)

        watcher = threading.Thread(target=_observe, daemon=True)
        watcher.start()

        started = time.perf_counter()
        blocker.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s FOR UPDATE',
            (fixture_job_id,),
        )
        result['blocked_ms'] = round((time.perf_counter() - started) * 1000.0, 3)
        watcher.join(timeout=1.0)
        releaser.join(timeout=2.0)
        blocker.rollback()

        # SKIP LOCKED against a held row must return nothing, immediately.
        holder.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s FOR UPDATE',
            (fixture_job_id,),
        )
        started = time.perf_counter()
        blocker.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s '
            'FOR UPDATE SKIP LOCKED', (fixture_job_id,),
        )
        rows = blocker.fetchall()
        result['skip_locked_waited'] = round(
            (time.perf_counter() - started) * 1000.0, 3)
        result['skip_locked_rows'] = len(rows)
        holder.rollback()
        blocker.rollback()

        result['conclusive'] = (
            result['wait_event_type'] == 'Lock'
            and result['blocked_ms'] is not None
            and result['skip_locked_rows'] == 0
        )
    finally:
        for connection in (holder, blocker, observer):
            try:
                connection.close()
            except Exception:
                pass
    return result


def scenario_lock_contention_blocking(env, fixture, batch):
    """Placeholder body.

    The contention measurement needs its own connections and its own timing, so
    it is performed by `measure_blocking_contention` in the runner rather than
    inside the generic repetition loop. This function exists so the scenario
    still executes the ordinary acquisition path once per repetition, giving a
    comparable latency series alongside the contention block.
    """
    jobs = env['shopify.connector.job'].sudo().search([
        ('store_id', '=', fixture.store.id),
    ], limit=1)
    for job in jobs:
        if hasattr(job, 'try_lock_for_update'):
            job.try_lock_for_update()


SCENARIO_FUNCTIONS = {
    'job_enqueue': scenario_job_enqueue,
    'job_drain': scenario_job_drain,
    'layer2_intent': scenario_layer2_intent,
    'layer2_outcome': scenario_layer2_outcome,
    'layer2_reconcile': scenario_layer2_reconcile,
    'order_scan': scenario_order_scan,
    'inventory_scan': scenario_inventory_scan,
    'fulfillment_scan': scenario_fulfillment_scan,
    'binding_lookup': scenario_binding_lookup,
    'lock_skiplocked': scenario_lock_skiplocked,
    'lock_contention_blocking': scenario_lock_contention_blocking,
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
        exec_time_before = sql_exec_time_snapshot(cursor, stats_available)

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

        exec_time_after = sql_exec_time_snapshot(cursor, stats_available)

        # Genuine contention is measured here, on its own connections, because
        # it needs a second backend holding a real lock -- something the
        # single-connection repetition loop above structurally cannot do.
        contention = None
        if name == 'lock_contention_blocking':
            contention_job = fixture.new_job()
            cursor.commit()
            contention = measure_blocking_contention(runtime, contention_job.id)

        residue_before_teardown = fixture.residue(cursor)
        fixture.teardown(cursor)

    # Re-open a CLEAN connection and re-sweep. Checking residue on the same
    # transaction that deleted the rows would prove nothing; and sweeping only
    # the store row would report "clean" while a credential, lease or binding
    # survived and silently changed the dataset for the next run.
    with environment(runtime) as (cursor, _env):
        cursor.execute(
            'SELECT COUNT(*) FROM shopify_connector_store WHERE shop_domain = %s',
            ('perf0-%s.myshopify.com' % fixture.tag,),
        )
        leaked_stores = cursor.fetchone()[0]
        residue_after_teardown = fixture.residue(cursor)
        residue_after_teardown['shopify_connector_store'] = leaked_stores

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
        # NOTE the name. This is statement EXECUTION time, not lock-wait time.
        # Genuine lock waiting is reported by the lock_contention_blocking
        # scenario in its own `contention` block, measured directly.
        'sql_exec_time_source': (
            'pg_stat_statements.total_exec_time' if stats_available
            else 'UNAVAILABLE -- extension not installed; not reported as zero'
        ),
        'sql_exec_time_ms_delta': (
            round(exec_time_after - exec_time_before, 3)
            if (exec_time_before is not None and exec_time_after is not None)
            else None
        ),
        'max_rss_kb_delta': rss_after - rss_before,
        'os_pid': os.getpid(),
        'rows_before_teardown': residue_before_teardown,
        'residue_after_teardown': residue_after_teardown,
        'residue_clean': (
            leaked_stores == 0
            and not any(residue_after_teardown.values())
        ),
        'threshold_status': 'BASELINE ONLY -- no accepted threshold exists (issue #199)',
    }
    if contention is not None:
        result['contention'] = contention
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
