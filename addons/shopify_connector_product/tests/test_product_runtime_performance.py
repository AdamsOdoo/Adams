import logging
import time
import uuid
from unittest.mock import patch

import odoo
from odoo import api, fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

_logger = logging.getLogger(__name__)

# CORE-R2 Slice 2B: the product importer now issues every Shopify Admin page
# call through the core `execute_business` admission-lease context manager
# (`_send` transport seam), not the legacy value-returning `execute()`. The
# run_drain feasibility test below drives the REAL admission gate; `DUMMY_TOKEN`
# is a non-secret test constant (never a live token). This class also holds a
# genuine separate-connection concurrency test, so registry test mode is entered
# ONLY inside the run_drain test that needs it -- never class-wide -- to leave
# the concurrency test's independent PostgreSQL connections untouched.
DUMMY_TOKEN = 'shpat_DUMMYDUMMYDUMMY0000000000000000'


class _FakeSendResponse:
    """Minimal `requests.Response` stand-in for the `_send` transport seam;
    `_normalize_response` reads `.status_code`, `.json()`, `.headers` and
    `.text` only, and the JSON body is the accepted Task 010B fixture dict."""

    def __init__(self, body, status_code=200, headers=None):
        self._body = body
        self.status_code = status_code
        self.headers = headers or {}
        self.text = ''

    def json(self):
        return self._body


@tagged('post_install', '-at_install', '-standard', 'sc010b_performance')
class TestProductRuntimePerformance(TransactionCase):
    """Task 010B opt-in runtime/performance evidence harness (control-room
    parallel authorization `4952270415`, architecture `AR-046`).

    **Session 2 correction (control-room reviews `4680634735` /
    `4680644496`):** the lock-hold/competing-retry test's timing labels
    previously overstated what was measured, its cleanup had no bounded
    timeout or independent post-cleanup verification, and the run_drain
    test used an unbounded `limit=20` with no precondition/postcondition
    proof of isolation. All three are corrected below -- see each test's
    docstring for the exact honest semantics. No production file is
    touched by this correction.

    NOT part of the standard suite. `@tagged('post_install', '-at_install',
    '-standard', 'sc010b_performance')` yields a final `test_tags` of
    exactly `{'post_install', 'sc010b_performance'}`: `post_install` avoids
    Odoo's "neither at_install nor post_install" warning, the absence of
    both `at_install` and `standard` means a default/standard install-time
    or `+standard` CI run never selects this class, and the unique
    `sc010b_performance` tag is the only way to opt in (e.g. `--test-tags
    sc010b_performance` or `--test-tags /shopify_connector_product:
    TestProductRuntimePerformance`) for a deliberate Odoo.sh performance
    run.

    No live Shopify call and no media download anywhere in this file:
    every payload/variant carries `image_url=None`, so `_prepare_media()`
    returns before any `requests.get()` (verified against
    `shopify_connector_product_importer.py`: `_plan_one_image` returns
    `None` immediately when `url` is falsy). Every fixture name is
    `SC010B`-prefixed and task-unique (never collides with standard Odoo
    demo data or another Task 010B test file, mirroring the `SC010B `
    fixture-isolation convention introduced by the runtime correction in
    `docs/05-qa/task-010b-validation-results.md` §0d). Three of the four
    tests run entirely inside this `TransactionCase`'s own automatically
    rolled-back cursor -- the same durable-cleanup convention every other
    test in this addon already relies on, since no path exercised here
    ever calls `self.env.cr.commit()` (verified by source read of
    `shopify_connector_job_dispatch.py` and
    `shopify_connector_product_importer.py`: zero occurrences). The
    lock-hold/competing-retry test genuinely commits through independent
    PostgreSQL connections (the only way to exercise real `FOR UPDATE
    SKIP LOCKED` contention), applies bounded transaction-local timeouts
    to every cleanup/verification connection so a stuck lock can never
    hang an Odoo.sh run, and proves durable cleanup with a THIRD,
    freshly-opened connection opened only after the deleting connection
    has already committed and closed.

    No arbitrary machine-dependent latency SLA is asserted anywhere in
    this file (none exists in the accepted packet or performance-budgets
    doc for these exact scenarios). Every test instead asserts
    correctness, boundedness (exact row/duplicate counts), and completion,
    and logs its timing/query-count measurement as durable evidence via
    the standard `logging` module under the `SC010B_PERF_EVIDENCE` marker
    so it appears verbatim in the Odoo.sh test-run log.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'SC010B Perf Test Store',
            'shop_domain': 'sc010b-perf-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.Job = cls.env['shopify.connector.job']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.Settings = cls.env['shopify.connector.store.settings']
        cls.Attribute = cls.env['product.attribute']

    # ------------------------------------------------------------------
    # Deterministic, no-network, no-media payload builders. `image_url` is
    # always `None` here -- never a real or fake URL -- so `_prepare_media`
    # cannot stage or fetch anything regardless of store settings.
    # ------------------------------------------------------------------

    def _variant(self, gid, selected, sku):
        return {
            'gid': gid, 'sku': sku, 'barcode': None, 'price': '9.99',
            'compare_at_price': None, 'selected_options': selected,
            'option_values': ' / '.join(
                '%s: %s' % (s['name'], s['value']) for s in selected
            ) or None,
            'image_url': None,
        }

    def _option(self, name, values, position=1):
        return {'name': name, 'position': position, 'values': list(values)}

    def _payload(self, gid, options, variants, title):
        return {
            'gid': gid, 'title': title, 'status': 'active', 'updated_at': None,
            'image_url': None, 'options': options, 'variants': variants,
        }

    def _query_count_delta(self, count_before):
        """Best-effort query-count evidence. `sql_log_count` is only
        populated when the running Odoo.sh test invocation enables SQL
        logging; when the attribute is absent this returns `None` rather
        than asserting or fabricating a count (task instruction: "query
        count when reliably available")."""
        count_after = getattr(self.env.cr, 'sql_log_count', None)
        if count_before is None or count_after is None:
            return None
        return count_after - count_before

    # ------------------------------------------------------------------
    # A. 100-variant DB-phase measurement.
    # ------------------------------------------------------------------

    def test_sc010b_perf_100_variant_db_phase_measurement(self):
        """LOOP 3A: local DB/reconciliation-phase timing for a genuinely
        structured 100-variant product, calling `_apply_import()` directly
        with a fully pre-normalized in-memory payload -- no HTTP, no media,
        no `shopify.connector.api.client` call anywhere on this path -- so
        the entire measured window is Odoo ORM + PostgreSQL work only."""
        total = 100
        option_name = 'SC010B Perf100 Size'
        values = ['Size%03d' % i for i in range(total)]
        option = self._option(option_name, values)
        variants = [
            self._variant(
                'gid://shopify/ProductVariant/sc010b-perf100-%d' % i,
                [{'name': option_name, 'value': values[i]}],
                'SC010B-PERF100-%03d' % i,
            )
            for i in range(total)
        ]
        payload = self._payload(
            'gid://shopify/Product/sc010b-perf100', [option], variants,
            'SC010B Perf100 Product',
        )
        self.assertFalse(
            self.Attribute.with_context(active_test=False).search(
                [('name', '=', option_name)]))

        count_before = getattr(self.env.cr, 'sql_log_count', None)
        started = time.perf_counter()
        result = self.Importer._apply_import(self.store, payload)
        elapsed = time.perf_counter() - started
        query_count = self._query_count_delta(count_before)

        template = result['template_binding'].product_template_id
        variant_bindings = result['variant_bindings']
        self.assertEqual(len(variant_bindings), total)
        self.assertEqual(len(template.product_variant_ids), total)
        gids = {vb.shopify_gid for vb in variant_bindings}
        self.assertEqual(len(gids), total)  # no duplicate GIDs
        self.assertEqual(
            self.Attribute.with_context(active_test=False).search_count(
                [('name', '=', option_name)]), 1,  # exactly one attribute
        )

        _logger.info(
            'SC010B_PERF_EVIDENCE 100_variant_db_phase elapsed_seconds=%.4f '
            'query_count=%s templates_created=1 variants_created=%d '
            'variant_bindings=%d attributes_created=1',
            elapsed, query_count, total, len(variant_bindings),
        )

    # ------------------------------------------------------------------
    # B. 2,048-variant DB-phase measurement (exact platform ceiling).
    # ------------------------------------------------------------------

    def test_sc010b_perf_2048_variant_db_phase_measurement(self):
        """LOOP 3B: local DB/reconciliation-phase timing at exactly the
        2,048-variant `MAX_ACCUMULATED_VARIANTS` ceiling, using TWO options
        whose declared cartesian space (64 x 33 = 2,112) is strictly
        larger than the 2,048 variants actually instantiated. An equal
        variant/template count at that size proves genuine sparse,
        explicit variant creation -- not a reversion to Odoo's `always`-
        mode cartesian auto-generation (D-010B-3) -- because a cartesian
        bug at this fixture would produce 2,112 variants, not 2,048."""
        total = 2048
        color_count, size_count = 64, 33  # 64 * 33 = 2112 > 2048 (sparse)
        self.assertLess(total, color_count * size_count)
        color_name = 'SC010B Perf2048 Color'
        size_name = 'SC010B Perf2048 Size'
        color_values = ['Color%03d' % i for i in range(color_count)]
        size_values = ['Size%03d' % i for i in range(size_count)]
        options = [
            self._option(color_name, color_values, position=1),
            self._option(size_name, size_values, position=2),
        ]
        # Deterministic bijection i -> (i % color_count, i // color_count)
        # onto a proper subset of the declared color x size grid: every
        # pair is unique (no duplicate combination -> no duplicate-binding
        # risk) and size index stays in [0, 31], leaving declared size
        # value #32 unused -- the "declared but never selected" case the
        # real importer's value union (declared u variant-used) supports.
        pairs = [(i % color_count, i // color_count) for i in range(total)]
        self.assertEqual(len(set(pairs)), total)
        self.assertLess(max(s for _c, s in pairs), size_count)

        variants = [
            self._variant(
                'gid://shopify/ProductVariant/sc010b-perf2048-%d' % i,
                [
                    {'name': color_name, 'value': color_values[c]},
                    {'name': size_name, 'value': size_values[s]},
                ],
                'SC010B-PERF2048-%04d' % i,
            )
            for i, (c, s) in enumerate(pairs)
        ]
        payload = self._payload(
            'gid://shopify/Product/sc010b-perf2048', options, variants,
            'SC010B Perf2048 Product',
        )
        self.assertFalse(
            self.Attribute.with_context(active_test=False).search(
                [('name', 'in', [color_name, size_name])]))

        count_before = getattr(self.env.cr, 'sql_log_count', None)
        started = time.perf_counter()
        result = self.Importer._apply_import(self.store, payload)
        elapsed = time.perf_counter() - started
        query_count = self._query_count_delta(count_before)

        template = result['template_binding'].product_template_id
        variant_bindings = result['variant_bindings']
        self.assertEqual(len(variant_bindings), total)
        self.assertEqual(len(template.product_variant_ids), total)
        gids = {vb.shopify_gid for vb in variant_bindings}
        self.assertEqual(len(gids), total)  # no duplicate GIDs
        self.assertEqual(
            self.Attribute.with_context(active_test=False).search_count(
                [('name', '=', color_name)]), 1,
        )
        self.assertEqual(
            self.Attribute.with_context(active_test=False).search_count(
                [('name', '=', size_name)]), 1,
        )

        _logger.info(
            'SC010B_PERF_EVIDENCE 2048_variant_db_phase elapsed_seconds=%.4f '
            'query_count=%s templates_created=1 variants_created=%d '
            'variant_bindings=%d declared_cartesian_space=%d '
            'attributes_created=2',
            elapsed, query_count, total, len(variant_bindings),
            color_count * size_count,
        )

    # ------------------------------------------------------------------
    # C/D. Lock-hold duration + competing-import retry, on genuinely
    # independent PostgreSQL connections (never `self.registry.cursor()`,
    # which in a `TransactionCase` returns a `TestCursor` sharing this
    # test's one underlying connection and could never exercise real
    # `FOR UPDATE SKIP LOCKED` contention).
    # ------------------------------------------------------------------

    def _perf_conc_payload(self, gid, option_name, sku):
        return self._payload(
            gid, [self._option(option_name, ['Red'])],
            [self._variant('%s/v' % gid, [{'name': option_name, 'value': 'Red'}], sku)],
            'SC010B Perf Lock Product',
        )

    def _open_paired_cursors(self, db):
        """Open two independent cursors, closing the first if opening the
        second raises, so a later cursor-creation failure can never leak
        an already-open connection."""
        first = db.cursor()
        try:
            second = db.cursor()
        except Exception:
            first.close()
            raise
        return first, second

    def _apply_bounded_timeouts(self, cr, lock_timeout_ms=5000, statement_timeout_ms=30000):
        """Transaction-local `lock_timeout`/`statement_timeout` (`SET
        LOCAL` semantics via `set_config(..., true)`, never a session-wide
        setting) so a cleanup or verification connection can never hang an
        Odoo.sh run indefinitely if a row is unexpectedly still locked or a
        query misbehaves. Parameterized (no string-formatted SQL)."""
        cr.execute(
            "SELECT set_config('lock_timeout', %s, true)",
            (str(lock_timeout_ms),),
        )
        cr.execute(
            "SELECT set_config('statement_timeout', %s, true)",
            (str(statement_timeout_ms),),
        )

    def _cleanup_lock_perf(self, db, gid_first, gid_second, store_ids, option_name, skus):
        """Bounded, durable cleanup on an independent connection.

        Applies transaction-local timeouts before any delete, removes
        every synthetic row this test can create in FK-safe order, and
        commits. Deliberately does NOT catch/swallow any exception raised
        during deletion or commit -- a failed cleanup must fail loudly
        (surface as a test failure) rather than silently leave residue."""
        cr = db.cursor()
        try:
            self._apply_bounded_timeouts(cr)
            env = api.Environment(cr, self.env.uid, {})
            variant_gids = ['%s/v' % gid_first, '%s/v' % gid_second]
            product_gids = [gid_first, gid_second]

            env['shopify.connector.product.variant.binding'].search(
                [('shopify_gid', 'in', variant_gids)]).unlink()
            tbindings = env['shopify.connector.product.template.binding'].search(
                [('shopify_gid', 'in', product_gids)])
            templates = tbindings.mapped('product_template_id')
            tbindings.unlink()
            # Explicit SKU-keyed product cleanup: independent of the
            # binding-derived template lookup above (defense in depth).
            env['product.product'].with_context(active_test=False).search(
                [('default_code', 'in', list(skus))]).unlink()
            templates.exists().unlink()  # cascades any remaining variants/lines/PTAVs
            env['product.attribute'].with_context(active_test=False).search(
                ['|', ('name', '=', option_name),
                 ('name', '=ilike', '%s (Shopify)' % option_name)],
            ).unlink()  # cascades its values; also catches a connector_owned variant
            env['shopify.connector.store.settings'].search(
                [('store_id', 'in', store_ids)]).unlink()
            env['shopify.connector.store'].browse(store_ids).exists().unlink()
            cr.commit()
        finally:
            cr.close()

    def _assert_zero_residue(
        self, db, gid_first, gid_second, store_first_id, store_second_id,
        option_name, skus, template_title,
    ):
        """Fresh, independent connection opened only AFTER the cleanup
        connection has already committed and closed -- proves the cleanup
        was durable on its own terms, not merely that the deleting
        transaction's own (potentially stale) view looked clean. Bounded
        timeouts are applied here too. No raw SQL, path, or exception text
        is included in any assertion message -- only fixed, generic
        labels."""
        cr = db.cursor()
        try:
            self._apply_bounded_timeouts(cr)
            env = api.Environment(cr, self.env.uid, {})
            variant_gids = ['%s/v' % gid_first, '%s/v' % gid_second]
            product_gids = [gid_first, gid_second]
            store_ids = [store_first_id, store_second_id]

            self.assertFalse(
                env['shopify.connector.product.template.binding'].search(
                    [('shopify_gid', 'in', product_gids)]),
                'zero-residue verification failed: template binding(s) remain')
            self.assertFalse(
                env['shopify.connector.product.variant.binding'].search(
                    [('shopify_gid', 'in', variant_gids)]),
                'zero-residue verification failed: variant binding(s) remain')
            self.assertFalse(
                env['product.product'].with_context(active_test=False).search(
                    [('default_code', 'in', list(skus))]),
                'zero-residue verification failed: product(s) remain')
            self.assertFalse(
                env['product.template'].with_context(active_test=False).search(
                    [('name', '=', template_title)]),
                'zero-residue verification failed: product template(s) remain')
            self.assertFalse(
                env['shopify.connector.store'].search(
                    [('id', 'in', store_ids)]),
                'zero-residue verification failed: store(s) remain')
            self.assertFalse(
                env['shopify.connector.store.settings'].search(
                    [('store_id', 'in', store_ids)]),
                'zero-residue verification failed: store settings remain')
            self.assertFalse(
                env['product.attribute'].with_context(active_test=False).search(
                    [('name', '=', option_name)]),
                'zero-residue verification failed: attribute remains')
            self.assertFalse(
                env['product.attribute'].with_context(active_test=False).search(
                    [('name', '=ilike', '%s (Shopify)' % option_name)]),
                'zero-residue verification failed: connector-owned attribute remains')
        finally:
            cr.close()

    def test_sc010b_perf_lock_hold_and_competing_retry(self):
        """LOOP 3C/3D combined (one real scenario, two evidence angles).

        Task step lettering vs local names: task "transaction A" (runs
        first, stays open holding the lock) = `first` below; task
        "transaction B" (conflicts, then retries) = `second` below. This
        mirrors `test_product_attribute_import.py`'s already-accepted
        `test_overlapping_transactions_serialize_to_one_global_attribute`
        (there named B-then-A); the roles and the underlying importer
        behaviour are identical, only the local variable names differ.

        Sequence: `first` runs the REAL structured import to completion on
        its own PostgreSQL connection and stays uncommitted. `second` then
        attempts a genuinely overlapping structured import for a DIFFERENT
        product using the SAME new option name; `try_lock_for_update()`'s
        `SKIP LOCKED` semantics are non-blocking -- `second` never waits or
        blocks, it immediately raises `concurrency_race_conflict` -- and
        leaves zero residue (no attribute, no binding) in its own
        transaction. `first` commits, releasing the lock; `second` is
        retried in a clean transaction (`rollback()` first) and succeeds,
        reusing `first`'s now-committed attribute. Exactly one global
        attribute and both product bindings exist before cleanup. Every
        committed row is then deleted on a bounded, independent cleanup
        connection, and zero residue is proven on a THIRD, freshly-opened
        connection.

        **Honest timing semantics (control-room reviews `4680634735` /
        `4680644496`).** Three timestamps are captured:
        `first_import_started_at` (immediately before `first`'s
        `_apply_import()` call), `first_import_completed_at` (immediately
        after that call returns -- i.e. after `first`'s per-product
        savepoint has already been released internally), and
        `first_commit_completed_at` (immediately after `cr_first.commit()`
        returns). Two durations are derived and logged, never asserted
        against any threshold:

        - `first_import_to_commit_upper_bound_seconds` = commit - started.
          This is an UPPER BOUND covering the whole import (including work
          before and after the actual internal lock acquisition) PLUS the
          open-transaction retention interval -- it is NOT a measurement of
          the lock-hold duration alone.
        - `post_import_lock_retention_seconds` = commit - import_completed.
          Because nothing else runs on `first`'s connection in that window,
          this interval is a direct, honest proof that the row lock
          remains held strictly AFTER `first`'s per-product savepoint has
          already exited -- released only at the outer transaction's
          commit, not at the savepoint. It is a lower bound on the
          post-savepoint retention, not the total lock-hold time either.

        No test-only hook exists at the exact internal `try_lock_for_
        update()` call site inside `_create_structured_template()`, so the
        true instant of lock acquisition cannot be measured directly from
        outside the importer; these two metrics are the honest bounds
        obtainable from the test boundary alone.

        `second`'s non-blocking conflict-detection latency is captured as
        `second_conflict_detection_seconds` -- `SKIP LOCKED` is
        non-blocking, so this measures how fast the conflict is detected
        and raised, never a "blocked"/"waiting" duration (that concept
        does not apply here and is never used to describe it).
        """
        option_name = 'SC010B Perf Lock Shade'
        gid_first = 'gid://shopify/Product/sc010b-perf-lock-first'
        gid_second = 'gid://shopify/Product/sc010b-perf-lock-second'
        skus = ('SC010B-PERF-LOCK-A', 'SC010B-PERF-LOCK-B')
        template_title = 'SC010B Perf Lock Product'
        self.assertFalse(
            self.Attribute.with_context(active_test=False).search(
                [('name', '=', option_name)]))

        db = odoo.sql_db.db_connect(self.env.cr.dbname)
        cr_setup = db.cursor()
        try:
            env_setup = api.Environment(cr_setup, self.env.uid, {})
            Store = env_setup['shopify.connector.store']
            store_first_id = Store.create({
                'name': 'SC010B Perf Lock Store First',
                'shop_domain': 'sc010b-perf-lock-first.myshopify.com',
                'api_version': '2026-07'}).id
            store_second_id = Store.create({
                'name': 'SC010B Perf Lock Store Second',
                'shop_domain': 'sc010b-perf-lock-second.myshopify.com',
                'api_version': '2026-07'}).id
            cr_setup.commit()
        finally:
            cr_setup.close()

        cr_first, cr_second = self._open_paired_cursors(db)
        try:
            env_first = api.Environment(cr_first, self.env.uid, {})
            env_second = api.Environment(cr_second, self.env.uid, {})
            store_first = env_first['shopify.connector.store'].browse(store_first_id)
            store_second = env_second['shopify.connector.store'].browse(store_second_id)
            importer_first = env_first['shopify.connector.product.importer']
            importer_second = env_second['shopify.connector.product.importer']

            # `first`: real structured import runs to completion and stays
            # uncommitted -- still holding the transaction-scoped lock.
            first_import_started_at = time.perf_counter()
            result_first = importer_first._apply_import(
                store_first,
                self._perf_conc_payload(gid_first, option_name, skus[0]),
            )
            first_import_completed_at = time.perf_counter()
            self.assertTrue(result_first['variant_bindings'])

            # `second`: overlaps `first`'s open transaction, cannot acquire
            # the lock `first` still holds. SKIP LOCKED is non-blocking --
            # this is conflict detection, never a blocked/waiting wait.
            second_conflict_check_started_at = time.perf_counter()
            with self.assertRaises(JobHandlerError) as ctx:
                importer_second._apply_import(
                    store_second,
                    self._perf_conc_payload(gid_second, option_name, skus[1]),
                )
            second_conflict_detection_seconds = (
                time.perf_counter() - second_conflict_check_started_at
            )
            self.assertEqual(ctx.exception.error_class, 'concurrency_race_conflict')

            # No partial residue from the conflicting attempt, visible from
            # `second`'s own (about-to-rollback) transaction: the lock
            # acquisition fails before any attribute/template/binding
            # write, and `first`'s row is not yet committed to any other
            # observer.
            self.assertFalse(
                env_second['shopify.connector.product.template.binding'].search(
                    [('shopify_gid', '=', gid_second)]))
            self.assertFalse(
                env_second['product.attribute'].with_context(active_test=False)
                .search([('name', '=', option_name)]))

            # `first` commits -> attribute committed, lock released.
            cr_first.commit()
            first_commit_completed_at = time.perf_counter()
            first_import_to_commit_upper_bound_seconds = (
                first_commit_completed_at - first_import_started_at
            )
            post_import_lock_retention_seconds = (
                first_commit_completed_at - first_import_completed_at
            )

            # `second` retried in a clean transaction -> reuses `first`'s
            # now-committed attribute instead of creating a duplicate.
            cr_second.rollback()
            retry_start = time.perf_counter()
            result_second = importer_second._apply_import(
                store_second,
                self._perf_conc_payload(gid_second, option_name, skus[1]),
            )
            cr_second.commit()
            second_retry_elapsed_seconds = time.perf_counter() - retry_start
            self.assertTrue(result_second['variant_bindings'])

            # Exactly ONE global attribute; both products bound, no dupes.
            self.assertEqual(
                env_first['product.attribute'].with_context(active_test=False)
                .search_count([('name', '=', option_name)]), 1)
            TB = env_first['shopify.connector.product.template.binding']
            self.assertEqual(TB.search_count([('shopify_gid', '=', gid_first)]), 1)
            self.assertEqual(TB.search_count([('shopify_gid', '=', gid_second)]), 1)

            _logger.info(
                'SC010B_PERF_EVIDENCE lock_hold_and_competing_retry '
                'first_import_to_commit_upper_bound_seconds=%.4f '
                'post_import_lock_retention_seconds=%.4f '
                'second_conflict_detection_seconds=%.4f '
                'second_retry_elapsed_seconds=%.4f',
                first_import_to_commit_upper_bound_seconds,
                post_import_lock_retention_seconds,
                second_conflict_detection_seconds,
                second_retry_elapsed_seconds,
            )
        finally:
            cr_first.close()
            cr_second.close()
            self._cleanup_lock_perf(
                db, gid_first, gid_second,
                [store_first_id, store_second_id], option_name, skus,
            )
            self._assert_zero_residue(
                db, gid_first, gid_second, store_first_id, store_second_id,
                option_name, skus, template_title,
            )

    # ------------------------------------------------------------------
    # E. Multi-job run_drain feasibility: two structured imports inside
    # one real dispatcher transaction, no network, deterministically
    # isolated from any other claimable job.
    # ------------------------------------------------------------------

    def _claimable_job_domain(self):
        """Exactly the domain `shopify.connector.job._claim_for_dispatch()`
        uses to select claimable jobs (`queued`, or due `retry_waiting`),
        copied verbatim in shape so this test proves isolation against the
        real dispatcher's own selection criterion, not an approximation
        of it."""
        now = fields.Datetime.now()
        return [
            '|',
            ('state', '=', 'queued'),
            '&', ('state', '=', 'retry_waiting'), ('next_retry_at', '<=', now),
        ]

    def _patch_send(self, fake_execute):
        """Route an accepted normalized-response `fake_execute(self, store,
        query, variables=None)` fixture through the real `execute_business`
        gate by patching only the `_send` transport seam (never the network)."""
        Client = self.env['shopify.connector.api.client']

        def fake_send(client_self, store, body, token=None):
            body = body or {}
            outcome = fake_execute(
                client_self, store, body.get('query'), body.get('variables'),
            )
            return _FakeSendResponse(outcome)

        return patch.object(type(Client), '_send', fake_send)

    def test_sc010b_perf_run_drain_two_structured_imports_one_transaction(self):
        """LOOP 3E: real-dispatcher feasibility check, deterministically
        isolated (control-room reviews `4680634735` / `4680644496`).

        Two `product_import_sync` jobs -- each a genuine structured
        import, the second reusing the first's brand-new option -- are
        processed by one real `run_drain(2)` call (limit == exactly the
        number of synthetic jobs this test creates, never an arbitrary
        larger batch size). Feasible entirely test-side, no CORE-R2
        call-site migration and no live Shopify call required: the
        `shopify.connector.api.client.execute` seam is mocked exactly as
        `test_product_import_matching.py`'s already-accepted
        `test_ambiguous_match_routes_job_to_blocked_manual_review` mocks
        it for one job -- this test only adds a second job, a second-GID
        branch in the fake response, and a call-list instrumenting the
        seam. `requests.sessions.Session.request` is additionally patched
        to raise if invoked at all, for the duration of the drain call --
        an explicit, structural proof that no network transport can occur
        outside the patched `execute` seam (belt-and-suspenders on top of
        every payload already carrying `image_url=None`).

        Isolation is proven, not assumed: before creating any fixture,
        this test asserts the dispatcher's own claimable-job domain
        (`_claimable_job_domain()`, copied from `shopify_connector_job.py`
        `_claim_for_dispatch()`) is already empty in this transaction.
        After creating the two jobs, it asserts the claimable set is
        EXACTLY `{job_1.id, job_2.id}` -- no unrelated claimable job
        exists for `run_drain(2)` to have picked up instead. After the
        drain call, it asserts exactly two `execute` calls occurred for
        exactly `{gid_1, gid_2}`, both jobs `succeeded`, no claimable job
        remains, and exactly one attribute / one template binding per
        product / one variant binding per variant exist -- no duplicate.

        Source-verified precondition: neither `shopify_connector_job_
        dispatch.py` nor this module's `_handle_product_import_sync` /
        `import_product_sync` / `_apply_import` call chain contains a
        `self.env.cr.commit()` (grepped: zero occurrences in both
        addons' non-test files), so `run_drain()` claims and dispatches
        both jobs inside ONE transaction -- this test's own
        `TransactionCase` cursor -- with no commit between them, which is
        exactly the `run_drain`-batch lock-persistence scenario documented
        in `shopify_connector_attribute_lock.py`'s docstring. Because both
        jobs share that one transaction, the second job's attribute-lock
        acquisition is a same-transaction re-lock (PostgreSQL never
        self-blocks a transaction on a row it already holds), so it
        succeeds immediately and reuses the first job's attribute -- never
        raising `concurrency_race_conflict` against itself. That failure
        mode is only produced by a genuinely SEPARATE transaction, proven
        separately by `test_sc010b_perf_lock_hold_and_competing_retry`
        above. This test calls only the real `run_drain()` entry point --
        it never calls a handler directly.

        CORE-R2 Slice 2B: each job's product import now flows through the
        `execute_business` admission gate + `_send` transport seam. The store is
        given a credential (while `setup_incomplete`, so generation stays 0) and
        registry test mode is entered (only here) so the admission side cursor
        observes the fixture. The `_send` seam is stubbed and
        `requests.sessions.Session.request` is still asserted never to fire --
        so no live Shopify transport occurs.
        """
        # Seed the credential BEFORE connecting so no generation bump occurs;
        # jobs then admit at generation 0. Enter registry test mode for this
        # test only (this class also runs a genuine separate-connection test).
        self.env['shopify.connector.store.credential'].action_set_token(
            self.store, DUMMY_TOKEN,
        )
        self.registry_enter_test_mode()
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id,
            'product_domain_enabled': True,
            'product_import_media_enabled': False,
        })

        # Precondition: this transaction has no claimable job at all yet.
        self.assertFalse(self.Job.search(self._claimable_job_domain()))

        option_name = 'SC010B Perf RunDrain Color'
        gid_1 = 'gid://shopify/Product/sc010b-perf-rundrain-1'
        gid_2 = 'gid://shopify/Product/sc010b-perf-rundrain-2'

        def _node(gid, sku):
            return {
                'id': gid, 'title': 'SC010B RunDrain Product %s' % sku,
                'status': 'ACTIVE', 'featuredImage': None,
                'options': [{
                    'id': 'opt-%s' % sku, 'name': option_name, 'position': 1,
                    'optionValues': [{'id': 'v-%s' % sku, 'name': 'Red'}],
                }],
                'variants': {
                    'nodes': [{
                        'id': '%s/v' % gid, 'sku': sku, 'barcode': None,
                        'price': '9.99', 'compareAtPrice': None,
                        'selectedOptions': [{'name': option_name, 'value': 'Red'}],
                        'image': None, 'inventoryItem': None,
                    }],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None},
                },
            }

        nodes_by_gid = {
            gid_1: _node(gid_1, 'SC010B-PERF-RD-1'),
            gid_2: _node(gid_2, 'SC010B-PERF-RD-2'),
        }
        api_calls = []

        def fake_execute(client_self, store, query, variables=None):
            gid = (variables or {}).get('id')
            api_calls.append(gid)
            return {'data': {'product': nodes_by_gid[gid]}}

        job_1 = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': gid_1,
        })
        job_2 = self.Job.create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'product_import_sync',
            'state': 'queued',
            'payload_hash': str(uuid.uuid4()),
            'shopify_target_gid': gid_2,
        })

        # Postcondition on fixture creation, precondition on the drain
        # call: the claimable set is EXACTLY these two jobs.
        claimable_before = self.Job.search(self._claimable_job_domain())
        self.assertEqual(set(claimable_before.ids), {job_1.id, job_2.id})

        # Flush so the admission side cursor (registry test mode) sees the
        # connected store, settings, and both queued jobs.
        self.env.flush_all()
        with self._patch_send(fake_execute), patch(
            'requests.sessions.Session.request',
            side_effect=AssertionError(
                'unexpected network transport during the sc010b_performance '
                'run_drain test -- only the patched api.client._send '
                'transport seam is permitted'
            ),
        ):
            started = time.perf_counter()
            self.Dispatch.run_drain(2)
            elapsed = time.perf_counter() - started

        job_1.invalidate_recordset()
        job_2.invalidate_recordset()
        self.assertEqual(job_1.state, 'succeeded')
        self.assertEqual(job_2.state, 'succeeded')
        self.assertEqual(len(api_calls), 2)
        self.assertEqual(set(api_calls), {gid_1, gid_2})
        # No claimable synthetic job remains (both succeeded; nothing else
        # was ever claimable, so nothing else could have been consumed).
        self.assertFalse(self.Job.search(self._claimable_job_domain()))
        self.assertEqual(
            self.Attribute.with_context(active_test=False).search_count(
                [('name', '=', option_name)]), 1,  # reused, not duplicated
        )
        self.assertEqual(
            self.TemplateBinding.search_count([('shopify_gid', '=', gid_1)]), 1)
        self.assertEqual(
            self.TemplateBinding.search_count([('shopify_gid', '=', gid_2)]), 1)
        self.assertEqual(
            self.VariantBinding.search_count(
                [('shopify_gid', '=', '%s/v' % gid_1)]), 1)
        self.assertEqual(
            self.VariantBinding.search_count(
                [('shopify_gid', '=', '%s/v' % gid_2)]), 1)

        _logger.info(
            'SC010B_PERF_EVIDENCE run_drain_two_structured_imports '
            'elapsed_seconds=%.4f jobs=2 api_calls=%d attributes_created=1',
            elapsed, len(api_calls),
        )
