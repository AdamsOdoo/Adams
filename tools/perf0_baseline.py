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
  * ``order_binding_projection``      -- READ/projection over order bindings
  * ``inventory_pair_projection``     -- READ/projection over inventory pairs
  * ``fulfillment_evidence_projection`` -- READ/projection over evidence rows
  * ``order_scan_admission``          -- the REAL order-scan cron admission path
  * ``inventory_push_scan_admission`` -- the REAL inventory push-scan cron path
  * ``fulfillment_reconciliation_admission``
                                      -- the REAL fulfillment reconciliation-
                                         check cron path
  * ``fulfillment_ledger_reconcile``  -- the REAL per-line reconciled-quantity
                                         ledger computation
  * ``binding_lookup``     -- indexed binding resolution at dataset scale
  * ``lock_skiplocked``    -- uncontended FOR UPDATE SKIP LOCKED acquire (floor)
  * ``job_claim_contention`` -- the REAL production claim path
    (``_claim_for_dispatch``) against a row a second backend holds, plus a raw
    PostgreSQL blocking experiment kept separately as calibration

The three ``*_projection`` scenarios are named for what they do. They were
previously called ``order_scan`` / ``inventory_scan`` / ``fulfillment_scan``,
which read as reconciliation throughput while the bodies performed a
``search`` and a ``read`` -- a projection, not a reconciliation. The genuine
network-free reconciliation/admission paths are the ``*_admission`` and
``fulfillment_ledger_reconcile`` scenarios, which call the production cron
entry points directly.

WHAT IS STILL NOT MEASURED, stated so the gap is not mistaken for coverage:
the per-record reconciliation HANDLERS (`_handle_order_import_scan`,
`_handle_inventory_push_sync`, `_handle_fulfillment_reconciliation_check`)
all perform Shopify reads, so they cannot run here at all. Issue #199's
reconciliation-throughput question is therefore only partly answered by this
harness, and #199 stays open. No fake transport is introduced to manufacture
a number.

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
    'order_binding_projection',
    'inventory_pair_projection',
    'fulfillment_evidence_projection',
    'order_scan_admission',
    'inventory_push_scan_admission',
    'fulfillment_reconciliation_admission',
    'fulfillment_ledger_reconcile',
    'binding_lookup',
    'lock_skiplocked',
    'job_claim_contention',
)

# A domain row expands into several ORM rows (products, bindings, orders,
# evidence and lines). Keep a malformed or accidental CLI value from asking
# Odoo to materialize an unbounded fixture before the first measurement starts.
MAX_DATASET_ROWS = 100_000


def validate_scale(scale):
    """Return ``scale`` when it is a safe, positive integer multiplier."""
    if isinstance(scale, bool) or not isinstance(scale, int):
        raise ValueError('scale must be a positive integer')
    if scale <= 0:
        raise ValueError('scale must be greater than zero')
    if scale > MAX_DATASET_ROWS:
        raise ValueError(
            'scale exceeds the safety limit of %d' % MAX_DATASET_ROWS)
    return scale


def scaled_dataset_rows(base_rows, scale):
    """Return the requested domain rows without allowing an unsafe size.

    ``base_rows`` is the per-operation batch size. Only the seeded domain
    dataset is multiplied; callers continue to use the unscaled batch for
    operation and repetition counts.
    """
    if isinstance(base_rows, bool) or not isinstance(base_rows, int):
        raise ValueError('base dataset rows must be a non-negative integer')
    if base_rows < 0:
        raise ValueError('base dataset rows must be non-negative')
    scale = validate_scale(scale)
    if base_rows > MAX_DATASET_ROWS // scale:
        raise ValueError(
            'requested dataset rows exceed the safety limit of %d'
            % MAX_DATASET_ROWS)
    return base_rows * scale


def _scale_argument(value):
    """Argparse converter that reports scale errors before Odoo bootstrap."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError('scale must be a positive integer')
    try:
        return validate_scale(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error))


# Tables that grow for reasons this harness does not own: framework logging,
# the bus, chatter written as a side effect of creating a business record, and
# the cron/queue bookkeeping Odoo does on its own. They are EXCLUDED from the
# escape-proof sweep and REPORTED separately, never silently dropped -- a
# residue check that quietly ignores tables is how the previous version came to
# claim "zero residue" while partners, products and sale orders survived.
FRAMEWORK_NOISE_TABLES = frozenset((
    'ir_logging', 'ir_attachment', 'ir_cron_trigger', 'ir_cron_progress',
    'bus_bus', 'bus_presence',
    'mail_message', 'mail_followers', 'mail_followers_res_partner_rel',
    'mail_tracking_value', 'mail_notification', 'mail_message_res_partner_rel',
    'mail_message_res_partner_starred_rel', 'mail_message_schedule',
    'mail_push', 'mail_link_preview', 'discuss_channel_member',
    'ir_model_data', 'ir_property', 'ir_default',
))


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
    """A disposable dataset whose every row is tracked by exact id.

    The previous version tracked connector rows only. It created `res.partner`,
    `product.template` (and therefore `product.product`), `sale.order` and
    `sale.order.line` in `build_domain_dataset`, then swept residue across
    store-scoped connector tables and reported "zero residue across all
    scenarios". The business rows were never captured, never deleted and never
    checked -- so the claim was true about the tables it looked at and false
    about the dataset as a whole. Every run left the database slightly
    different from the last, which is exactly what destroys comparability
    between two SHAs.

    Three mechanisms now make that failure mode structural rather than a matter
    of remembering:

      1. `_track()` records the exact ids of every row created, business or
         connector, keyed by model and in creation order.
      2. `teardown()` deletes by those exact ids, children before parents.
         Never by name, never by domain, never model-wide -- a name-based
         delete can reach a row this harness did not create.
      3. `verify_absent()` re-checks every captured id from a NEW transaction,
         and `sweep_new_rows()` additionally looks for ANY row in ANY table
         with an id above the pre-run watermark. The second check is what makes
         a newly added fixture unable to escape quietly: it does not need to
         know what was added.
    """

    # Child-before-parent. Two things make the order non-obvious:
    #   * the job/attempt FK pair is CIRCULAR (job.mutation_attempt_id ->
    #     attempt, attempt.job_id -> job), so the reverse pointer is cleared
    #     before either delete. This exact defect broke the fulfillment harness
    #     the first time it was ever run.
    #   * evidence lines go before evidence even though the FK cascades, so the
    #     verification afterwards is meaningful rather than accidentally
    #     satisfied by the cascade.
    CONNECTOR_TEARDOWN_ORDER = (
        'shopify.connector.fulfillment.inbound.evidence.line',
        'shopify.connector.fulfillment.inbound.evidence',
        'shopify.connector.fulfillment.binding',
        'shopify.connector.inventory.level.binding',
        'shopify.connector.location.mapping',
        'shopify.connector.product.variant.binding',
        'shopify.connector.product.template.binding',
        'shopify.connector.order.binding',
        'shopify.connector.customer.binding',
        'shopify.connector.tax.mapping',
        'shopify.connector.job.log',
        'shopify.connector.mutation.attempt',
        'shopify.connector.job',
        'shopify.connector.call.lease',
        'shopify.connector.location',
        'shopify.connector.store.credential',
        'shopify.connector.store.settings',
        'shopify.connector.store',
    )
    # Business rows are removed through the ORM, not SQL: `sale.order.unlink()`
    # takes its lines and its chatter with it, which SQL would leave behind as
    # exactly the "framework noise" the sweep would then have to excuse.
    BUSINESS_TEARDOWN_ORDER = (
        'sale.order',
        'product.template',
        'res.partner',
    )
    # Removed by their parent's own cascade, never deleted directly -- but
    # still captured and still verified absent by exact id, because "the
    # cascade handles it" is an assumption until something checks.
    CASCADE_VERIFIED_MODELS = (
        'product.product',
        'sale.order.line',
    )
    # Rows written as a SIDE EFFECT of creating a business record, which their
    # parent's unlink does not take with it. `product.value` (stock_account's
    # valuation layer) is the one the escape-proof sweep found on the first
    # honest run of this teardown -- 50 rows per scenario, one per product,
    # invisible to every hand-written table list including this file's own
    # earlier one. Deleted by exact id like everything else.
    SIDE_EFFECT_TEARDOWN_ORDER = (
        'product.value',
    )

    def __init__(self, env, scale):
        self.env = env
        self.scale = validate_scale(scale)
        self.tag = uuid.uuid4().hex[:12]
        self.store = None
        self.job_ids = []
        self.dataset_built = False
        # model -> ordered list of ids created by this fixture
        self.ledger = {}
        self.baseline_max_ids = {}

    # ------------------------------------------------------------------
    # Tracking
    # ------------------------------------------------------------------

    def _track(self, records):
        """Record every id, then return the records unchanged."""
        if records:
            self.ledger.setdefault(records._name, []).extend(records.ids)
        return records

    def _create(self, model, values, company=None, context=None):
        """The ONE create path. Everything it makes is tracked."""
        target = self.env[model].sudo()
        if company is not None:
            target = target.with_company(company)
        if context:
            target = target.with_context(**context)
        return self._track(target.create(values))

    def capture_watermarks(self, cursor):
        """max(id) per table BEFORE anything is created.

        The escape hatch this closes: a fixture added later that writes to a
        table nobody thought to list. Comparing against a per-table watermark
        needs no list at all.
        """
        cursor.execute(
            "SELECT c.relname FROM pg_class c "
            "JOIN pg_namespace n ON n.oid = c.relnamespace "
            "JOIN information_schema.columns col "
            "  ON col.table_name = c.relname AND col.column_name = 'id' "
            "WHERE c.relkind = 'r' AND n.nspname = 'public'"
        )
        tables = [row[0] for row in cursor.fetchall()]
        watermarks = {}
        for table in tables:
            cursor.execute('SELECT COALESCE(MAX(id), 0) FROM "%s"' % table)
            watermarks[table] = cursor.fetchone()[0]
        self.baseline_max_ids = watermarks
        return watermarks

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def build(self):
        self.store = self._create('shopify.connector.store', {
            'name': 'PERF-0 store %s' % self.tag,
            'shop_domain': 'perf0-%s.myshopify.com' % self.tag,
            'api_version': '2026-07',
        })
        # Every domain flag the real cron admission paths gate on. Without
        # them the `*_admission` scenarios would search, find nothing, and
        # report the cost of an empty query as reconciliation admission.
        self._create('shopify.connector.store.settings', {
            'store_id': self.store.id,
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
            'inventory_domain_enabled': True,
            'inventory_scheduled_sync_enabled': True,
            'fulfillment_domain_enabled': True,
        })
        self.store.write({'state': 'connected'})
        return self

    def build_domain_dataset(self, rows):
        """Create the durable rows the projection/reconciliation scenarios read.

        Everything here is local: partners, orders, products, locations and
        connector rows. No Shopify request or mutation of any kind.

        The inventory pair is UNIQUE on (store, variant binding, location
        mapping), so scale comes from N distinct product variants against one
        mapping, not from N copies of one pair.
        """
        if self.dataset_built:
            return
        env = self.env
        company = self.store.company_id
        partner = self._create('res.partner', {
            'name': 'PERF-0 partner %s' % self.tag,
        })

        # Pick a location the STORE's company can actually use. Taking the
        # first internal location regardless of company is how this fixture
        # first built a cross-company pair -- which SEC-3's `_check_company`
        # correctly refused. The benchmark dataset must be a legal dataset.
        location = env['stock.location'].search([
            ('usage', '=', 'internal'),
            '|', ('company_id', '=', False), ('company_id', '=', company.id),
        ], limit=1)

        templates = self._create('product.template', [
            {'name': 'PERF-0 product %s %d' % (self.tag, index), 'type': 'consu'}
            for index in range(rows)
        ])
        # product.product rows are created BY product.template, so they never
        # pass through `_create`. Capture them explicitly -- this is precisely
        # the class of row the previous version left behind.
        self._track(templates.product_variant_ids)

        template_bindings = self._create(
            'shopify.connector.product.template.binding', [
                {
                    'store_id': self.store.id,
                    'shopify_gid':
                        'gid://shopify/Product/perf0-%s-%d' % (self.tag, index),
                    'product_template_id': template.id,
                }
                for index, template in enumerate(templates)
            ])
        variant_bindings = self._create(
            'shopify.connector.product.variant.binding', [
                {
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/ProductVariant/perf0-%s-%d'
                                   % (self.tag, index),
                    'product_variant_id': template.product_variant_id.id,
                    'product_template_binding_id': template_binding.id,
                }
                for index, (template, template_binding)
                in enumerate(zip(templates, template_bindings))
            ])

        if location:
            # `with_company` is required, not incidental: the mapping's own
            # guard `_check_location_company_consistency` fails closed when the
            # mapped location is outside `env.company`, and this harness runs as
            # the framework superuser whose active company need not match.
            mapping = self._create(
                'shopify.connector.location.mapping', {
                    'store_id': self.store.id,
                    'shopify_gid':
                        'gid://shopify/Location/perf0-%s' % self.tag,
                    'odoo_location_id': location.id,
                    'match_key': 'manual',
                }, company=location.company_id or company)
            self._create('shopify.connector.inventory.level.binding', [
                {
                    'store_id': self.store.id,
                    'product_variant_binding_id': variant_binding.id,
                    'location_mapping_id': mapping.id,
                    'shopify_inventory_item_gid':
                        'gid://shopify/InventoryItem/perf0-%s-%d'
                        % (self.tag, index),
                }
                for index, variant_binding in enumerate(variant_bindings)
            ], company=location.company_id or company)

        orders = self._create('sale.order', [
            {'partner_id': partner.id} for _ in range(rows)
        ])
        # Order lines make the dataset a realistic reconciliation target rather
        # than N empty headers, and they are tracked through their order's
        # unlink rather than separately (an order takes its lines with it).
        self._create('sale.order.line', [
            {
                'order_id': order.id,
                'product_id': templates[index % len(templates)].product_variant_id.id,
                'product_uom_qty': 1,
            }
            for index, order in enumerate(orders)
        ] if templates else [])
        self._create('shopify.connector.order.binding', [{
            'store_id': self.store.id,
            'shopify_gid':
                'gid://shopify/Order/perf0-%s-%d' % (self.tag, index),
            'sale_order_id': order.id,
        } for index, order in enumerate(orders)])

        evidence = self._create(
            'shopify.connector.fulfillment.inbound.evidence', [{
                'store_id': self.store.id,
                'shopify_fulfillment_gid':
                    'gid://shopify/Fulfillment/perf0-%s-%d' % (self.tag, index),
            } for index in range(rows)])
        # Ledger lines: `reconciled_quantity_ledger()` is the real per-line
        # reconciliation computation, and it needs lines to compute over.
        self._create(
            'shopify.connector.fulfillment.inbound.evidence.line', [{
                'evidence_id': row.id,
                'fo_line_item_gid':
                    'gid://shopify/FulfillmentOrderLineItem/perf0-%s-%d-%d'
                    % (self.tag, index, line_index),
                'quantity': 1,
                'reconciled_quantity': 1,
            } for index, row in enumerate(evidence) for line_index in range(2)])

        env.flush_all()
        self.dataset_built = True

    def new_job(self, job_type='core_dispatch_selftest', state='queued'):
        job = self._create('shopify.connector.job', {
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': job_type,
            'state': state,
            'payload_hash': uuid.uuid4().hex,
        })
        self.job_ids.append(job.id)
        return job

    # ------------------------------------------------------------------
    # Teardown and verification
    # ------------------------------------------------------------------

    def _table(self, model):
        return self.env[model]._table

    def rows_before_teardown(self, cursor):
        """Exact-id counts, per model, of everything this fixture owns."""
        counts = {}
        for model, ids in self.ledger.items():
            if not ids:
                continue
            cursor.execute(
                'SELECT COUNT(*) FROM "%s" WHERE id IN %%s' % self._table(model),
                (tuple(ids),))
            counts[model] = cursor.fetchone()[0]
        return counts

    def absorb_untracked_rows(self, cursor):
        """Adopt rows the PRODUCTION code paths created during the run.

        `_create` cannot see everything. `_create_attempt_intent` mints
        mutation attempts through the Layer-2 seam, `_system_append` writes job
        logs, and the `*_admission` scenarios exist precisely to make the real
        cron enqueue jobs. Those rows are as much this fixture's residue as the
        ones it created by hand, and the first run of this teardown proved it:
        deleting the tracked jobs failed on an FK from an untracked attempt.

        Adoption is by WATERMARK, and that is what keeps it exact: an id above
        the pre-run maximum cannot belong to a pre-existing record, so this
        can never reach a row the harness did not cause. The ids are read out
        and then deleted individually -- never a domain-wide or model-wide
        delete.
        """
        discovered = {}
        models = (self.CONNECTOR_TEARDOWN_ORDER + self.BUSINESS_TEARDOWN_ORDER
                  + self.CASCADE_VERIFIED_MODELS
                  + self.SIDE_EFFECT_TEARDOWN_ORDER)
        for model in models:
            if model not in self.env:
                continue
            table = self._table(model)
            watermark = self.baseline_max_ids.get(table)
            if watermark is None:
                continue
            cursor.execute(
                'SELECT id FROM "%s" WHERE id > %%s' % table, (watermark,))
            known = set(self.ledger.get(model, ()))
            extra = [row[0] for row in cursor.fetchall() if row[0] not in known]
            if extra:
                self.ledger.setdefault(model, []).extend(extra)
                discovered[model] = len(extra)
        return discovered

    def teardown(self, cursor):
        """Exact-id, FK-safe, child-before-parent removal. Never name-based."""
        self.absorb_untracked_rows(cursor)
        # 1. Break the circular job <-> attempt pointer.
        job_ids = self.ledger.get('shopify.connector.job')
        if job_ids:
            cursor.execute(
                'UPDATE shopify_connector_job SET mutation_attempt_id = NULL '
                'WHERE id IN %s', (tuple(job_ids),))
        # 2. Connector rows, in SQL: several of these models are append-only
        #    evidence whose ORM `unlink()` refuses outright by design, and
        #    widening that contract for a benchmark would be the wrong trade.
        for model in self.CONNECTOR_TEARDOWN_ORDER:
            ids = self.ledger.get(model)
            if not ids:
                continue
            cursor.execute(
                'DELETE FROM "%s" WHERE id IN %%s' % self._table(model),
                (tuple(ids),))
        cursor.commit()
        # 3. Business rows, through the ORM, so their lines and chatter go too.
        for model in self.BUSINESS_TEARDOWN_ORDER:
            ids = self.ledger.get(model)
            if not ids:
                continue
            records = self.env[model].sudo().browse(ids).exists()
            if records:
                records.unlink()
        # 4. Side-effect rows, once their parents are gone.
        for model in self.SIDE_EFFECT_TEARDOWN_ORDER:
            ids = self.ledger.get(model)
            if not ids or model not in self.env:
                continue
            cursor.execute(
                'DELETE FROM "%s" WHERE id IN %%s' % self._table(model),
                (tuple(ids),))
        self.env.flush_all()
        cursor.commit()

    def verify_absent(self, cursor):
        """Every captured id, re-checked from a clean transaction.

        `product.product` is verified here even though nothing deletes it
        directly: it is removed by its template's own cascade, and verifying
        the ids is how that stays a fact rather than an assumption.
        """
        survivors = {}
        for model, ids in self.ledger.items():
            if not ids:
                continue
            cursor.execute(
                'SELECT COUNT(*) FROM "%s" WHERE id IN %%s' % self._table(model),
                (tuple(ids),))
            remaining = cursor.fetchone()[0]
            if remaining:
                survivors[model] = remaining
        return survivors

    def sweep_new_rows(self, cursor):
        """Any row, in any table, created after the watermark and still here.

        This is the escape-proof half. It needs no list of what the fixture
        creates, so a fixture collection added later cannot slip past it.
        """
        leaked, ignored = {}, {}
        for table, watermark in self.baseline_max_ids.items():
            cursor.execute(
                'SELECT COUNT(*) FROM "%s" WHERE id > %%s' % table,
                (watermark,))
            count = cursor.fetchone()[0]
            if not count:
                continue
            if table in FRAMEWORK_NOISE_TABLES:
                ignored[table] = count
            else:
                leaked[table] = count
        return leaked, ignored


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
        'observed_outcome', 'resolution_disposition', 'transport_attempted',
        'job_id', 'store_id',
        'business_intent_fingerprint', 'exact_request_fingerprint',
    ])


def scenario_order_binding_projection(env, fixture, batch):
    """READ/projection over order bindings. Not reconciliation.

    Named for what it does. The previous name (`order_scan`) read as import
    reconciliation throughput while the body performed a `search` and a `read`.
    The real order-scan admission path is `scenario_order_scan_admission`.
    """
    fixture.build_domain_dataset(scaled_dataset_rows(batch, fixture.scale))
    Binding = env['shopify.connector.order.binding'].sudo()
    for _ in range(max(1, batch // 10)):
        Binding.search([
            ('store_id', '=', fixture.store.id),
            ('status', 'in', ('active', 'review')),
        ], limit=batch).read(['shopify_gid', 'status', 'store_id'])


def scenario_inventory_pair_projection(env, fixture, batch):
    """READ/projection over inventory pairs. Not reconciliation."""
    fixture.build_domain_dataset(scaled_dataset_rows(batch, fixture.scale))
    Binding = env['shopify.connector.inventory.level.binding'].sudo()
    for _ in range(max(1, batch // 10)):
        Binding.search([
            ('store_id', '=', fixture.store.id),
        ], limit=batch).read(['shopify_gid', 'status', 'store_id'])


def scenario_fulfillment_evidence_projection(env, fixture, batch):
    """READ/projection over inbound evidence rows. Not reconciliation."""
    fixture.build_domain_dataset(scaled_dataset_rows(batch, fixture.scale))
    Evidence = env['shopify.connector.fulfillment.inbound.evidence'].sudo()
    for _ in range(max(1, batch // 10)):
        Evidence.search([
            ('store_id', '=', fixture.store.id),
        ], limit=batch).read(['store_id', 'last_observed_at'])


# --------------------------------------------------------------------------
# The genuine, network-free reconciliation/admission paths.
#
# Each of these calls the PRODUCTION cron entry point. They are network-free by
# construction, not by our choosing a safe subset: each one searches eligible
# settings, gates on store state, and enqueues a typed job whose handler does
# the Shopify work later. That admission decision is the part that grows with
# the dataset and the part a scheduler runs every few minutes.
#
# The handlers themselves (`_handle_order_import_scan`,
# `_handle_inventory_push_sync`, `_handle_fulfillment_reconciliation_check`)
# all perform Shopify reads and are therefore NOT measured here, by anything,
# at any batch size. That gap is real and #199 stays open for it.
# --------------------------------------------------------------------------

def scenario_order_scan_admission(env, fixture, batch):
    """`_cron_enqueue_order_scans` -- the real order-scan admission path."""
    fixture.build_domain_dataset(scaled_dataset_rows(batch, fixture.scale))
    # The cron lives on `shopify.connector.store` (the sale module extends
    # the store model with it), not on the abstract scan service.
    env['shopify.connector.store'].sudo()._cron_enqueue_order_scans()
    env.flush_all()


def scenario_inventory_push_scan_admission(env, fixture, batch):
    """`run_inventory_push_scan` -- the real inventory push-scan cron path."""
    fixture.build_domain_dataset(scaled_dataset_rows(batch, fixture.scale))
    env['shopify.connector.inventory.service'].sudo().run_inventory_push_scan()
    env.flush_all()


def scenario_fulfillment_reconciliation_admission(env, fixture, batch):
    """`_cron_enqueue_reconciliation_checks` -- the real fulfillment path."""
    fixture.build_domain_dataset(scaled_dataset_rows(batch, fixture.scale))
    env['shopify.connector.fulfillment.service'].sudo(
    )._cron_enqueue_reconciliation_checks()
    env.flush_all()


def scenario_fulfillment_ledger_reconcile(env, fixture, batch):
    """`reconciled_quantity_ledger()` -- the real per-line ledger computation.

    This one IS reconciliation logic, not a projection: it is the duplicate-
    application backstop the fulfillment design relies on, and it runs entirely
    on local evidence rows.
    """
    fixture.build_domain_dataset(scaled_dataset_rows(batch, fixture.scale))
    Evidence = env['shopify.connector.fulfillment.inbound.evidence'].sudo()
    for evidence in Evidence.search([
        ('store_id', '=', fixture.store.id),
    ], limit=batch):
        evidence.reconciled_quantity_ledger()


def scenario_lock_skiplocked(env, fixture, batch):
    """Uncontended ``FOR UPDATE SKIP LOCKED`` acquire -- the floor.

    This is the cost of taking the lock when nobody holds it. It is NOT
    contention, and it is named accordingly.
    """
    jobs = env['shopify.connector.job'].sudo().search([
        ('store_id', '=', fixture.store.id),
    ], limit=batch)
    for job in jobs:
        if hasattr(job, 'try_lock_for_update'):
            job.try_lock_for_update()


def measure_production_claim_contention(runtime, store_id, job_id):
    """The REAL claim path against a row another backend holds.

    `shopify.connector.job._claim_for_dispatch` is the production acquisition
    method. It uses Odoo's `try_lock_for_update()`, i.e. `FOR UPDATE SKIP
    LOCKED`, so under contention it does NOT block -- it skips the locked row
    and returns without it. That no-wait behaviour IS the production result,
    and reporting it as such is the point: measuring a raw blocking `FOR
    UPDATE` and calling it "connector acquisition behaviour" would describe a
    code path the connector does not take.

    Returns a dict; never raises for a lock outcome, because "we could not
    observe it" is a result worth publishing honestly rather than a crash.
    """
    from odoo.sql_db import db_connect

    database = runtime['database']
    holder = db_connect(database).cursor()
    result = {
        'production_method': (
            'shopify.connector.job._claim_for_dispatch -> '
            'try_lock_for_update (FOR UPDATE SKIP LOCKED)'),
        'blocking_expected': False,
        'holder_backend_pid': None,
        'claim_elapsed_ms': None,
        'claimed_ids': None,
        'held_job_claimed': None,
        'conclusive': False,
    }
    try:
        holder.execute('SELECT pg_backend_pid()')
        result['holder_backend_pid'] = holder.fetchone()[0]
        # A second, genuinely separate PostgreSQL backend holds the row.
        holder.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s FOR UPDATE',
            (job_id,))

        with environment(runtime) as (cursor, env):
            Job = env['shopify.connector.job'].sudo().with_context(
                active_test=False)
            started = time.perf_counter()
            claimed = Job.with_context(
                perf0_store=store_id)._claim_for_dispatch(limit=50)
            result['claim_elapsed_ms'] = round(
                (time.perf_counter() - started) * 1000.0, 3)
            result['claimed_ids'] = claimed.ids
            result['held_job_claimed'] = job_id in claimed.ids
            cursor.rollback()

        # Conclusive when the production path returned WITHOUT the held row and
        # WITHOUT waiting for it: that is SKIP LOCKED behaving as designed.
        result['conclusive'] = result['held_job_claimed'] is False
    finally:
        try:
            holder.rollback()
            holder.close()
        except Exception:
            pass
    return result


def measure_database_lock_calibration(runtime, job_id, hold_ms=250):
    """Raw PostgreSQL blocking, kept ONLY as calibration.

    This is NOT connector acquisition behaviour -- the connector never issues a
    blocking `FOR UPDATE` on a job row. It is here so the harness can show that
    the environment does block when asked to, and by roughly how much, which is
    what makes the no-wait production result above meaningful rather than
    indistinguishable from "nothing was locked at all".

      * a HOLDER connection takes `FOR UPDATE` on one job row and waits.
      * a BLOCKER connection attempts the same row with plain `FOR UPDATE`.
        Wall-clock around that call is the blocked duration.
      * an OBSERVER connection reads `pg_stat_activity.wait_event_type` for the
        blocker's backend pid, so the measurement does not rest on our
        stopwatch alone.
      * the SAME row is then attempted with `FOR UPDATE SKIP LOCKED`, which
        must return no row and must not wait.
    """
    from odoo.sql_db import db_connect
    import threading

    database = runtime['database']
    holder = db_connect(database).cursor()
    blocker = db_connect(database).cursor()
    observer = db_connect(database).cursor()
    result = {
        'label': 'database lock calibration -- NOT connector acquisition',
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
        blocker.execute("SET LOCAL statement_timeout = '%d'" % (hold_ms * 20,))
        blocker.execute('SELECT pg_backend_pid()')
        blocked_pid = blocker.fetchone()[0]
        result['blocked_pid'] = blocked_pid

        holder.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s FOR UPDATE',
            (job_id,))

        release = threading.Event()

        def _hold_then_release():
            release.wait(hold_ms / 1000.0)
            holder.rollback()

        releaser = threading.Thread(target=_hold_then_release, daemon=True)
        releaser.start()

        def _observe():
            deadline = time.time() + (hold_ms / 1000.0)
            while time.time() < deadline:
                observer.execute(
                    'SELECT wait_event_type, wait_event FROM pg_stat_activity '
                    'WHERE pid = %s', (blocked_pid,))
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
            (job_id,))
        result['blocked_ms'] = round((time.perf_counter() - started) * 1000.0, 3)
        watcher.join(timeout=1.0)
        releaser.join(timeout=2.0)
        blocker.rollback()

        holder.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s FOR UPDATE',
            (job_id,))
        started = time.perf_counter()
        blocker.execute(
            'SELECT id FROM shopify_connector_job WHERE id = %s '
            'FOR UPDATE SKIP LOCKED', (job_id,))
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


def scenario_job_claim_contention(env, fixture, batch):
    """Repetition body: the ordinary uncontended claim, for a latency series.

    The contended measurements need their own connections and their own
    timing, so they are performed by `measure_production_claim_contention` and
    `measure_database_lock_calibration` in the runner. This body runs the
    production claim path uncontended, giving a comparable floor alongside
    them -- and the two must never be conflated: this series is sub-millisecond
    repetitions of an uncontended claim, not the contended result.
    """
    env['shopify.connector.job'].sudo()._claim_for_dispatch(limit=1)


SCENARIO_FUNCTIONS = {
    'job_enqueue': scenario_job_enqueue,
    'job_drain': scenario_job_drain,
    'layer2_intent': scenario_layer2_intent,
    'layer2_outcome': scenario_layer2_outcome,
    'layer2_reconcile': scenario_layer2_reconcile,
    'order_binding_projection': scenario_order_binding_projection,
    'inventory_pair_projection': scenario_inventory_pair_projection,
    'fulfillment_evidence_projection': scenario_fulfillment_evidence_projection,
    'order_scan_admission': scenario_order_scan_admission,
    'inventory_push_scan_admission': scenario_inventory_push_scan_admission,
    'fulfillment_reconciliation_admission':
        scenario_fulfillment_reconciliation_admission,
    'fulfillment_ledger_reconcile': scenario_fulfillment_ledger_reconcile,
    'binding_lookup': scenario_binding_lookup,
    'lock_skiplocked': scenario_lock_skiplocked,
    'job_claim_contention': scenario_job_claim_contention,
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
        fixture = Fixture(env, args.scale)
        # Watermarks BEFORE anything is created, so the escape-proof sweep has
        # a floor to compare against.
        fixture.capture_watermarks(cursor)
        fixture.build()
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

        # Contention is measured here, on its own connections, because it needs
        # a second backend holding a real lock -- something the
        # single-connection repetition loop above structurally cannot do.
        contention = None
        if name == 'job_claim_contention':
            contention_job = fixture.new_job()
            cursor.commit()
            contention = {
                'production_claim': measure_production_claim_contention(
                    runtime, fixture.store.id, contention_job.id),
                'database_lock_calibration':
                    measure_database_lock_calibration(
                        runtime, contention_job.id),
            }

        adopted = fixture.absorb_untracked_rows(cursor)
        rows_before_teardown = fixture.rows_before_teardown(cursor)
        fixture.teardown(cursor)

    # Re-open a CLEAN connection and re-check. Checking on the same transaction
    # that deleted the rows would prove nothing.
    with environment(runtime) as (cursor, _env):
        survivors = fixture.verify_absent(cursor)
        leaked_tables, ignored_tables = fixture.sweep_new_rows(cursor)

    rss_after = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    result = {
        'scenario': name,
        'batch_size': args.batch,
        'dataset_rows': scaled_dataset_rows(args.batch, args.scale),
        'repeats': args.repeats,
        'warmup_discarded': args.warmup,
        'latency': percentiles(latencies),
        'queries_per_repetition': {
            'min': min(query_counts) if query_counts else None,
            'max': max(query_counts) if query_counts else None,
            'mean': round(statistics.fmean(query_counts), 1) if query_counts else None,
        },
        # NOTE the name. This is statement EXECUTION time, not lock-wait time.
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
        'fixture_rows_by_model': {
            model: len(ids) for model, ids in sorted(fixture.ledger.items())
        },
        'rows_adopted_from_production_paths': adopted,
        'rows_before_teardown': rows_before_teardown,
        'exact_id_survivors': survivors,
        'new_rows_by_table': leaked_tables,
        'framework_noise_rows_by_table': ignored_tables,
        'residue_clean': not survivors and not leaked_tables,
        'threshold_status': 'BASELINE ONLY -- no accepted threshold exists (issue #199)',
    }
    if contention is not None:
        result['contention'] = contention
    return result


def connector_identity():
    """Exact connector SHA and worktree state, read from git.

    Taken from the repository rather than from anything a caller supplies:
    identity that can be typed in by hand is identity that can be wrong. If it
    cannot be proven it is reported as UNPROVEN, never guessed.
    """
    import subprocess
    repository = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    identity = {
        'connector_sha': 'UNPROVEN',
        'connector_worktree_dirty': None,
        'odoo_sha': 'UNPROVEN',
    }
    try:
        identity['connector_sha'] = subprocess.check_output(
            ['git', '-c', 'safe.directory=*', '-C', repository,
             'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL).decode().strip()
        identity['connector_worktree_dirty'] = bool(subprocess.check_output(
            ['git', '-c', 'safe.directory=*', '-C', repository,
             'status', '--porcelain'],
            stderr=subprocess.DEVNULL).decode().strip())
    except Exception:
        pass
    try:
        import odoo
        # `odoo.__file__` is None in Odoo 19 -- the package is a namespace
        # package, so its path comes from `__path__`, not `__file__`.
        odoo_root = os.path.dirname(list(odoo.__path__)[0])
        identity['odoo_sha'] = subprocess.check_output(
            ['git', '-c', 'safe.directory=*', '-C', odoo_root,
             'rev-parse', 'HEAD'],
            stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        pass
    # Cross-check the running Odoo against the repository's immutable pin, so
    # a comparison between two runs cannot silently span two different Odoos.
    try:
        pin_file = os.path.join(repository, 'tools', 'odoo-pin.txt')
        with open(pin_file) as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith('#'):
                    identity['odoo_pin'] = line
                    break
    except Exception:
        identity['odoo_pin'] = 'UNPROVEN'
    identity['odoo_pin_verified'] = (
        identity.get('odoo_pin') == identity['odoo_sha']
        and identity['odoo_sha'] != 'UNPROVEN')
    return identity


def database_identity(runtime):
    with environment(runtime) as (cursor, _env):
        cursor.execute('SELECT version()')
        version = cursor.fetchone()[0]
        cursor.execute('SHOW server_version')
        server_version = cursor.fetchone()[0]
    return {'postgres': version, 'postgres_server_version': server_version}


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
    parser.add_argument('--scale', type=_scale_argument, default=1,
                        help='positive multiplier for domain dataset rows; '
                             'operation batch/repetition counts are unchanged')
    parser.add_argument('--passes', type=int, default=1,
                        help='run the whole scenario set this many times in '
                             'the SAME database; pass 2 proves the second run '
                             'starts from the same clean baseline as the first')
    parser.add_argument('--output', default='-',
                        help='write JSON here; "-" for stdout')
    args = parser.parse_args(argv)

    try:
        requested_dataset_rows = scaled_dataset_rows(args.batch, args.scale)
    except ValueError as error:
        parser.error(str(error))

    requested = [s.strip() for s in args.scenarios.split(',') if s.strip()]
    unknown = set(requested) - set(SCENARIOS)
    if unknown:
        parser.error('unknown scenario(s): %s' % ', '.join(sorted(unknown)))

    runtime = bootstrap(args.config, args.database)
    identity = connector_identity()
    identity.update(database_identity(runtime))

    report = {
        'issue': '199 (PERF-0)',
        'environment': {
            'database': args.database,
            'python': sys.version.split()[0],
            'odoo_version': runtime['odoo'].release.version,
            'pid': os.getpid(),
            **identity,
        },
        'workload': {
            'scenarios': requested,
            'batch_size': args.batch,
            'dataset_rows': requested_dataset_rows,
            'repeats': args.repeats,
            'warmup': args.warmup,
            'scale': args.scale,
            'passes': args.passes,
        },
        'shopify_operations': 'none',
        'not_measured': (
            'Per-record reconciliation HANDLERS perform Shopify reads and are '
            'not measured by this harness at any batch size. Issue #199 stays '
            'open for them; no fake transport was introduced.'),
        'passes': [],
    }

    failures = []
    baseline_watermarks = None
    for pass_index in range(args.passes):
        pass_results = []
        for name in requested:
            result = run_scenario(runtime, name, args)
            result['pass'] = pass_index + 1
            pass_results.append(result)
            # Residue is the one thing this harness DOES judge: a benchmark
            # that leaks rows silently changes the dataset for the next run.
            if result['exact_id_survivors']:
                failures.append(
                    'pass %d: %s left exact-id survivors: %s'
                    % (pass_index + 1, name, result['exact_id_survivors']))
            if result['new_rows_by_table']:
                failures.append(
                    'pass %d: %s left untracked rows: %s'
                    % (pass_index + 1, name, result['new_rows_by_table']))
        report['passes'].append(pass_results)

        # Prove the pass ended where it began: a second pass that starts from a
        # different baseline is not a repeat, it is a different benchmark.
        with environment(runtime) as (cursor, env):
            probe = Fixture(env, args.scale)
            watermarks = probe.capture_watermarks(cursor)
        business = {
            table: value for table, value in watermarks.items()
            if table.startswith('shopify_connector_')
            or table in ('res_partner', 'product_template', 'product_product',
                         'sale_order', 'sale_order_line')
        }
        if baseline_watermarks is None:
            baseline_watermarks = business
            report['baseline_row_ceiling'] = business
        else:
            report['pass_%d_row_ceiling' % (pass_index + 1)] = business

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
