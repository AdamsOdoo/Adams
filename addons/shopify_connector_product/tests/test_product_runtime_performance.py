import logging
import time
import uuid
from unittest.mock import patch

import odoo
from odoo import api
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install', '-standard', 'sc010b_performance')
class TestProductRuntimePerformance(TransactionCase):
    """Task 010B opt-in runtime/performance evidence harness (control-room
    parallel authorization `4952270415`, architecture `AR-046`).

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
    SKIP LOCKED` contention) and unlinks every row it committed through a
    third independent connection in a `finally` block, mirroring the
    already-accepted pattern in `test_product_attribute_import.py`'s
    `test_overlapping_transactions_serialize_to_one_global_attribute`.

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

    def _cleanup_lock_perf(self, db, gids, store_ids, option_name):
        cr = db.cursor()
        try:
            env = api.Environment(cr, self.env.uid, {})
            TB = env['shopify.connector.product.template.binding']
            VB = env['shopify.connector.product.variant.binding']
            tbindings = TB.search([('shopify_gid', 'in', gids)])
            templates = tbindings.mapped('product_template_id')
            VB.search(
                [('product_template_binding_id', 'in', tbindings.ids)]
            ).unlink()
            tbindings.unlink()
            templates.exists().unlink()  # cascades variants, lines, PTAVs
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

    def test_sc010b_perf_lock_hold_and_competing_retry(self):
        """LOOP 3C/3D combined (one real scenario, two evidence angles).

        Task step lettering vs local names: task "transaction A" (runs
        first, stays open holding the lock) = `first` below; task
        "transaction B" (conflicts, then retries) = `second` below. This
        mirrors `test_product_attribute_import.py`'s already-accepted
        `test_overlapping_transactions_serialize_to_one_global_attribute`
        (there named B-then-A); the roles and the underlying importer
        behaviour are identical, only the local variable names differ, to
        keep this file self-contained and to line up 1:1 with the task's
        own step numbering.

        Sequence: `first` runs the REAL structured import to completion on
        its own PostgreSQL connection and stays uncommitted -- proving
        (together with `second`'s subsequent conflict) that the singleton
        `shopify.connector.attribute.lock` row is transaction-scoped, not
        released by the per-product `savepoint()` that already closed
        inside `first`'s call. `second` then attempts a genuinely
        overlapping structured import for a DIFFERENT product using the
        SAME new option name; `try_lock_for_update()`'s `SKIP LOCKED`
        semantics make this non-blocking, so `second` immediately raises
        `concurrency_race_conflict` rather than hanging -- and leaves zero
        residue (no attribute, no binding) in its own transaction. `first`
        commits, releasing the lock; `second` is retried in a clean
        transaction (`rollback()` first) and succeeds, reusing `first`'s
        now-committed attribute. Exactly one global attribute and both
        product bindings exist at the end. Every committed row is unlinked
        through a third, independent connection in `finally`.
        """
        option_name = 'SC010B Perf Lock Shade'
        gid_first = 'gid://shopify/Product/sc010b-perf-lock-first'
        gid_second = 'gid://shopify/Product/sc010b-perf-lock-second'
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

        cr_first = db.cursor()
        cr_second = db.cursor()
        try:
            env_first = api.Environment(cr_first, self.env.uid, {})
            env_second = api.Environment(cr_second, self.env.uid, {})
            store_first = env_first['shopify.connector.store'].browse(store_first_id)
            store_second = env_second['shopify.connector.store'].browse(store_second_id)
            importer_first = env_first['shopify.connector.product.importer']
            importer_second = env_second['shopify.connector.product.importer']

            # `first`: real structured import runs to completion and stays
            # uncommitted -- still holding the transaction-scoped lock.
            result_first = importer_first._apply_import(
                store_first,
                self._perf_conc_payload(gid_first, option_name, 'SC010B-PERF-LOCK-A'),
            )
            self.assertTrue(result_first['variant_bindings'])
            first_done_at = time.perf_counter()

            # `second`: overlaps `first`'s open transaction, cannot acquire
            # the lock `first` still holds -- non-blocking, so this must
            # return promptly rather than waiting.
            second_attempt_start = time.perf_counter()
            with self.assertRaises(JobHandlerError) as ctx:
                importer_second._apply_import(
                    store_second,
                    self._perf_conc_payload(gid_second, option_name, 'SC010B-PERF-LOCK-B'),
                )
            second_blocked_elapsed = time.perf_counter() - second_attempt_start
            self.assertEqual(ctx.exception.error_class, 'concurrency_race_conflict')

            # No partial residue from the blocked attempt, visible from
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
            lock_released_at = time.perf_counter()
            lock_hold_duration = lock_released_at - first_done_at

            # `second` retried in a clean transaction -> reuses `first`'s
            # now-committed attribute instead of creating a duplicate.
            cr_second.rollback()
            retry_start = time.perf_counter()
            result_second = importer_second._apply_import(
                store_second,
                self._perf_conc_payload(gid_second, option_name, 'SC010B-PERF-LOCK-B'),
            )
            cr_second.commit()
            retry_elapsed = time.perf_counter() - retry_start
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
                'lock_hold_duration_seconds=%.4f '
                'second_blocked_detect_seconds=%.4f '
                'second_retry_elapsed_seconds=%.4f',
                lock_hold_duration, second_blocked_elapsed, retry_elapsed,
            )
        finally:
            cr_first.close()
            cr_second.close()
            self._cleanup_lock_perf(
                db, [gid_first, gid_second],
                [store_first_id, store_second_id], option_name,
            )

    # ------------------------------------------------------------------
    # E. Multi-job run_drain feasibility: two structured imports inside
    # one real dispatcher transaction, no network.
    # ------------------------------------------------------------------

    def test_sc010b_perf_run_drain_two_structured_imports_one_transaction(self):
        """LOOP 3E: real-dispatcher feasibility check.

        Two `product_import_sync` jobs -- each a genuine structured
        import, the second reusing the first's brand-new option -- are
        processed by one real `run_drain()` call. Feasible entirely
        test-side, no CORE-R2 call-site migration and no live Shopify
        call required: the `shopify.connector.api.client.execute` seam is
        mocked exactly as `test_product_import_matching.py`'s already-
        accepted `test_ambiguous_match_routes_job_to_blocked_manual_
        review` mocks it for one job -- this test only adds a second job
        and a second-GID branch in the fake response.

        Source-verified precondition: neither `shopify_connector_job_
        dispatch.py` nor this module's `_handle_product_import_sync` /
        `import_product_sync` / `_apply_import` call chain contains a
        `self.env.cr.commit()` (grepped: zero occurrences in both
        addons' non-test files). `run_drain()` therefore claims and
        dispatches both jobs inside ONE transaction -- this test's own
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
        above. No duplicate attribute, no duplicate binding, both jobs
        `succeeded`.
        """
        self.store.write({'state': 'connected'})
        self.Settings.create({
            'store_id': self.store.id,
            'product_domain_enabled': True,
            'product_import_media_enabled': False,
        })
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

        def fake_execute(client_self, store, query, variables=None):
            gid = (variables or {}).get('id')
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

        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), 'execute', fake_execute):
            started = time.perf_counter()
            self.Dispatch.run_drain(20)
            elapsed = time.perf_counter() - started

        job_1.invalidate_recordset()
        job_2.invalidate_recordset()
        self.assertEqual(job_1.state, 'succeeded')
        self.assertEqual(job_2.state, 'succeeded')
        self.assertEqual(
            self.Attribute.with_context(active_test=False).search_count(
                [('name', '=', option_name)]), 1,  # reused, not duplicated
        )
        self.assertEqual(
            self.TemplateBinding.search_count([('shopify_gid', '=', gid_1)]), 1)
        self.assertEqual(
            self.TemplateBinding.search_count([('shopify_gid', '=', gid_2)]), 1)

        _logger.info(
            'SC010B_PERF_EVIDENCE run_drain_two_structured_imports '
            'elapsed_seconds=%.4f jobs=2 attributes_created=1',
            elapsed,
        )
