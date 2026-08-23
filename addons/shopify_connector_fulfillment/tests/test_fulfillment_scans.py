import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_fulfillment.models.shopify_connector_fulfillment_reader import (  # noqa: E501
    FulfillmentReadError,
)
from odoo.tools import mute_logger


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestFulfillmentScans(TransactionCase):
    """Reconciliation-check cron + handler, and reconnect catch-up (D-014-8).

    The cron enqueues one fulfillment_reconciliation_check per connected,
    fulfillment-enabled store (per-run uuid nonce payload_hash). The check
    handler refreshes each bound fulfillment's snapshot and turns a Shopify-side
    CANCELLED status into a review case (cancelled_after_validation) without
    changing Odoo stock, then stamps the reconciliation watermark. Reconnect
    catch-up forces gap-period externals to review in BOTH operating modes.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.fulfillment.service']
        cls.Job = cls.env['shopify.connector.job']
        cls.Binding = cls.env['shopify.connector.fulfillment.binding']
        cls.Evidence = cls.env['shopify.connector.fulfillment.inbound.evidence']
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'FUL Test',
            'shop_domain': 'ful-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id, 'fulfillment_domain_enabled': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'P1', 'type': 'consu',
        })
        cls.partner = cls.env['res.partner'].create({'name': 'C'})
        cls.sale = cls.env['sale.order'].create({'partner_id': cls.partner.id})
        cls.order_binding = cls.env['shopify.connector.order.binding'].sudo().create({
            'store_id': cls.store.id, 'shopify_gid': 'gid://shopify/Order/900',
            'sale_order_id': cls.sale.id, 'status': 'active',
        })
        cls.stock_loc = cls.env.ref('stock.stock_location_stock')
        cls.customer_loc = cls.env.ref('stock.stock_location_customers')
        cls.pt_out = cls.env['stock.picking.type'].search(
            [('code', '=', 'outgoing')], limit=1,
        )
        cls.picking = cls.env['stock.picking'].create({
            'picking_type_id': cls.pt_out.id,
            'location_id': cls.stock_loc.id,
            'location_dest_id': cls.customer_loc.id,
            'sale_id': cls.sale.id,
        })

    # ------------------------------------------------------------------
    # Fixture builders
    # ------------------------------------------------------------------

    def _fulfillment_binding(self, fulfillment_gid):
        return self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': fulfillment_gid,
            'picking_id': self.picking.id,
            'order_binding_id': self.order_binding.id,
            'status': 'active',
        })

    def _scan_job(self, job_type):
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': job_type,
            'state': 'queued',
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'payload_hash': uuid.uuid4().hex,
        })

    def _reconciliation_check_jobs(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'fulfillment_reconciliation_check'),
        ], order='id asc')

    # ------------------------------------------------------------------
    # Cron enqueue: one check per connected, fulfillment-enabled store
    # ------------------------------------------------------------------

    def test_cron_enqueues_one_check_per_store_with_nonce(self):
        self.Service._cron_enqueue_reconciliation_checks()
        jobs = self._reconciliation_check_jobs()
        self.assertEqual(len(jobs), 1)
        job_a = jobs
        self.assertEqual(job_a.job_source, 'reconciliation')
        self.assertTrue(
            job_a.payload_hash.startswith('reconciliation_check:%d:' % self.store.id)
        )
        # Terminalize so the operation scope clears (flush it to the DB before
        # the next enqueue, or the UNIQUE(store, operation_scope_key) index would
        # reject the replacement), then re-run: the per-run uuid nonce yields a
        # fresh, distinct job (never a duplicate effect).
        job_a.sudo().write({'state': 'cancelled', 'cancel_reason': 't'})
        job_a.flush_recordset(['state', 'operation_scope_key'])
        self.Service._cron_enqueue_reconciliation_checks()
        jobs2 = self._reconciliation_check_jobs()
        self.assertEqual(len(jobs2), 2)
        job_b = jobs2 - job_a
        self.assertNotEqual(job_a.payload_hash, job_b.payload_hash)

    def test_cron_skips_disconnected_store(self):
        self.store.sudo().write({'state': 'disconnecting'})
        self.Service._cron_enqueue_reconciliation_checks()
        self.assertFalse(self._reconciliation_check_jobs())

    # ------------------------------------------------------------------
    # Reconciliation-check handler: CANCELLED -> review, no stock change
    # ------------------------------------------------------------------

    def test_cancelled_after_validation_opens_review_no_stock_change(self):
        binding = self._fulfillment_binding('gid://shopify/Fulfillment/RC1')
        job = self._scan_job('fulfillment_reconciliation_check')
        cancelled_node = {
            'id': binding.shopify_gid,
            'status': 'CANCELLED',
            'trackingInfo': [{'number': 'TNX', 'url': '', 'company': 'UPS'}],
        }
        before_state = self.picking.state
        with patch.object(
            type(self.Service), '_read_fulfillment', return_value=cancelled_node,
        ):
            self.Service._handle_fulfillment_reconciliation_check(job)
        binding.invalidate_recordset()
        self.assertEqual(binding.shopify_status_snapshot, 'CANCELLED')
        evidence = self.Evidence.search([
            ('store_id', '=', self.store.id),
            ('shopify_fulfillment_gid', '=', binding.shopify_gid),
        ], limit=1)
        self.assertTrue(evidence)
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertEqual(evidence.review_reason, 'cancelled_after_validation')
        # A Shopify cancellation never auto-reverses Odoo stock.
        self.picking.invalidate_recordset()
        self.assertEqual(self.picking.state, before_state)

    # ------------------------------------------------------------------
    # Correction P1-2 — a read failure must never masquerade as a pass
    # ------------------------------------------------------------------

    def test_reconciliation_check_read_failure_leaves_watermark_unchanged_and_raises(self):
        self._fulfillment_binding('gid://shopify/Fulfillment/RCFAIL')
        job = self._scan_job('fulfillment_reconciliation_check')
        before = self.settings.sudo().fulfillment_last_reconciliation_at
        with patch.object(
            type(self.Service), '_read_fulfillment',
            side_effect=FulfillmentReadError(
                'data_shape_schema_mismatch', 'boom'),
        ):
            with self.assertRaises(JobHandlerError):
                self.Service._handle_fulfillment_reconciliation_check(job)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sudo().fulfillment_last_reconciliation_at, before,
        )

    def test_reconnect_catchup_read_failure_raises_never_successful_completion(self):
        job = self._scan_job('fulfillment_reconnect_catchup')
        with patch.object(
            type(self.Service), '_read_order_fulfillments',
            side_effect=FulfillmentReadError(
                'data_shape_schema_mismatch', 'boom'),
        ):
            with self.assertRaises(JobHandlerError):
                self.Service._handle_fulfillment_reconnect_catchup(job)

    def test_reconciliation_check_sets_watermark(self):
        self._fulfillment_binding('gid://shopify/Fulfillment/RC2')
        job = self._scan_job('fulfillment_reconciliation_check')
        node = {'id': 'gid://shopify/Fulfillment/RC2', 'status': 'SUCCESS',
                'trackingInfo': []}
        with patch.object(
            type(self.Service), '_read_fulfillment', return_value=node,
        ):
            self.Service._handle_fulfillment_reconciliation_check(job)
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.fulfillment_last_reconciliation_at)

    def test_reconciliation_check_is_bounded_and_resumable(self):
        first = self._fulfillment_binding(
            'gid://shopify/Fulfillment/RC-SLICE-1'
        )
        self._fulfillment_binding('gid://shopify/Fulfillment/RC-SLICE-2')
        job = self._scan_job('fulfillment_reconciliation_check')
        job.sudo().write({'state': 'running'})
        node = {'id': first.shopify_gid, 'status': 'SUCCESS',
                'trackingInfo': []}
        with patch(
            'odoo.addons.shopify_connector_fulfillment.models.'
            'shopify_connector_fulfillment_scans.RECONCILE_BATCH', 1,
        ), patch.object(
            type(self.Service), '_read_fulfillment', return_value=node,
        ):
            self.Service._handle_fulfillment_reconciliation_check(job)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.fulfillment_reconciliation_cursor_id, first.id,
        )
        self.assertFalse(self.settings.fulfillment_last_reconciliation_at)
        successor = self._reconciliation_check_jobs().filtered(
            lambda row: row.id > job.id and row.state == 'queued'
        )
        self.assertEqual(len(successor), 1)

    def test_reconciliation_batches_multiple_fulfillment_reads(self):
        first = self._fulfillment_binding(
            'gid://shopify/Fulfillment/RC-BATCH-1'
        )
        second = self._fulfillment_binding(
            'gid://shopify/Fulfillment/RC-BATCH-2'
        )
        job = self._scan_job('fulfillment_reconciliation_check')
        observed = {
            first.shopify_gid: {
                'id': first.shopify_gid, 'status': 'SUCCESS',
                'trackingInfo': [],
            },
            second.shopify_gid: {
                'id': second.shopify_gid, 'status': 'SUCCESS',
                'trackingInfo': [],
            },
        }
        with patch.object(
            type(self.Service), '_read_fulfillments_batch',
            return_value=observed,
        ) as batched, patch.object(
            type(self.Service), '_read_fulfillment',
            side_effect=AssertionError('per-binding read must not run'),
        ):
            self.Service._handle_fulfillment_reconciliation_check(job)
        batched.assert_called_once()

    def test_batched_reader_requires_exact_requested_identity(self):
        gids = [
            'gid://shopify/Fulfillment/BATCH-1',
            'gid://shopify/Fulfillment/BATCH-2',
        ]
        nodes = [
            {'id': gid, 'status': 'SUCCESS', 'trackingInfo': []}
            for gid in gids
        ]
        job = self._scan_job('fulfillment_reconciliation_check')
        with patch.object(
            type(self.Service), '_read_data', return_value={'nodes': nodes},
        ):
            result = self.Service._read_fulfillments_batch(
                job, self.store, gids,
            )
        self.assertEqual(set(result), set(gids))
        with patch.object(
            type(self.Service), '_read_data',
            return_value={'nodes': list(reversed(nodes))},
        ):
            with self.assertRaises(FulfillmentReadError):
                self.Service._read_fulfillments_batch(
                    job, self.store, gids,
                )

    # ------------------------------------------------------------------
    # Reconnect catch-up: gap-period externals -> review in BOTH modes
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Theme A — per-store isolation in the cron entry point
    # ------------------------------------------------------------------

    @mute_logger(
        'odoo.addons.shopify_connector_fulfillment.models.'
        'shopify_connector_fulfillment_scans'
    )
    def test_cron_one_store_unexpected_failure_does_not_starve_other_stores(self):
        store_2 = self.env['shopify.connector.store'].create({
            'name': 'FUL Test 2',
            'shop_domain': 'ful2-%s.myshopify.com' % uuid.uuid4().hex,
            'api_version': '2026-07', 'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': store_2.id, 'fulfillment_domain_enabled': True,
        })
        real_enqueue_once = type(self.Service)._enqueue_once

        def _flaky_enqueue_once(service_self, store, *args, **kwargs):
            if store.id == self.store.id:
                raise RuntimeError('simulated unexpected failure for store 1')
            return real_enqueue_once(service_self, store, *args, **kwargs)

        with patch.object(
            type(self.Service), '_enqueue_once', _flaky_enqueue_once,
        ):
            self.Service._cron_enqueue_reconciliation_checks()
        jobs_2 = self.Job.search([
            ('store_id', '=', store_2.id),
            ('job_type', '=', 'fulfillment_reconciliation_check'),
        ])
        self.assertTrue(jobs_2)
        self.assertFalse(self._reconciliation_check_jobs())

    # ------------------------------------------------------------------
    # Theme E — complete pagination beyond the old fixed 200-row window
    # ------------------------------------------------------------------

    def test_reconciliation_check_processes_more_than_200_bindings(self):
        for i in range(201):
            picking = self.env['stock.picking'].create({
                'picking_type_id': self.pt_out.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
                'sale_id': self.sale.id,
            })
            self.Binding.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Fulfillment/BULK-%d' % i,
                'picking_id': picking.id,
                'order_binding_id': self.order_binding.id,
            })
        job = self._scan_job('fulfillment_reconciliation_check')
        with patch.object(
            type(self.Service), '_read_fulfillment',
            return_value={'id': 'x', 'status': 'SUCCESS', 'trackingInfo': []},
        ):
            self.Service._handle_fulfillment_reconciliation_check(job)
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.fulfillment_last_reconciliation_at)
        # Every binding's snapshot was refreshed -- not just the first 200 of
        # a fixed window; row 201+ is proven reached.
        refreshed = self.Binding.search_count([
            ('store_id', '=', self.store.id),
            ('shopify_status_snapshot', '=', 'SUCCESS'),
        ])
        self.assertGreaterEqual(refreshed, 201)

    def test_reconciliation_check_incomplete_pass_fails_closed_never_advances_watermark(self):
        # A safety-cap-exceeding pass must fail closed (raise), never
        # advance the watermark and never be silently reported as complete.
        for i in range(3):
            picking = self.env['stock.picking'].create({
                'picking_type_id': self.pt_out.id,
                'location_id': self.stock_loc.id,
                'location_dest_id': self.customer_loc.id,
                'sale_id': self.sale.id,
            })
            self.Binding.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Fulfillment/CAP-%d' % i,
                'picking_id': picking.id,
                'order_binding_id': self.order_binding.id,
            })
        job = self._scan_job('fulfillment_reconciliation_check')
        before = self.settings.sudo().fulfillment_last_reconciliation_at
        with patch(
            'odoo.addons.shopify_connector_fulfillment.models.'
            'shopify_connector_fulfillment_scans.MAX_SCAN_PAGES', 1,
        ), patch(
            'odoo.addons.shopify_connector_fulfillment.models.'
            'shopify_connector_fulfillment_scans.RECONCILE_BATCH', 2,
        ), patch.object(
            type(self.Service), '_read_fulfillment',
            return_value={'id': 'x', 'status': 'SUCCESS', 'trackingInfo': []},
        ):
            with self.assertRaises(JobHandlerError):
                self.Service._handle_fulfillment_reconciliation_check(job)
        self.settings.invalidate_recordset()
        self.assertEqual(
            self.settings.sudo().fulfillment_last_reconciliation_at, before,
        )

    def test_reconnect_catchup_processes_more_than_200_order_bindings(self):
        OrderBinding = self.env['shopify.connector.order.binding']
        for i in range(201):
            sale = self.env['sale.order'].create({
                'partner_id': self.partner.id,
            })
            OrderBinding.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Order/BULK-%d' % i,
                'sale_order_id': sale.id,
                'status': 'active',
            })
        job = self._scan_job('fulfillment_reconnect_catchup')
        node = {
            'id': 'gid://shopify/Fulfillment/BULK-CATCHUP',
            'status': 'SUCCESS', 'displayStatus': 'FULFILLED',
            'trackingInfo': [],
        }
        call_count = {'n': 0}
        real_read = self.Service._read_order_fulfillments

        def _counting_read(read_job, store, order_gid):
            call_count['n'] += 1
            return [dict(node, id='%s-%d' % (node['id'], call_count['n']))]

        with patch.object(
            type(self.Service), '_read_order_fulfillments',
            side_effect=_counting_read,
        ):
            self.Service._handle_fulfillment_reconnect_catchup(job)
        # Every one of the 201 order bindings (beyond the old 200-row
        # window) was reached -- proven by the read being invoked 201 times,
        # once per order binding with a Shopify GID.
        self.assertGreaterEqual(call_count['n'], 201)

    def test_reconnect_catchup_incomplete_pass_fails_closed(self):
        OrderBinding = self.env['shopify.connector.order.binding']
        for i in range(3):
            sale = self.env['sale.order'].create({
                'partner_id': self.partner.id,
            })
            OrderBinding.sudo().create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Order/CAP-%d' % i,
                'sale_order_id': sale.id,
                'status': 'active',
            })
        job = self._scan_job('fulfillment_reconnect_catchup')
        with patch(
            'odoo.addons.shopify_connector_fulfillment.models.'
            'shopify_connector_fulfillment_scans.MAX_SCAN_PAGES', 1,
        ), patch(
            'odoo.addons.shopify_connector_fulfillment.models.'
            'shopify_connector_fulfillment_scans.RECONCILE_BATCH', 2,
        ), patch.object(
            type(self.Service), '_read_order_fulfillments', return_value=[],
        ):
            with self.assertRaises(JobHandlerError):
                self.Service._handle_fulfillment_reconnect_catchup(job)

    def test_reconnect_catchup_external_is_review_even_in_mode2(self):
        # The store is nominally in Mode 2 ...
        self.settings.sudo().write({
            'fulfillment_operating_mode': 'mode2',
            'fulfillment_switch_in_progress': False,
        })
        self.assertEqual(
            self.settings.sudo().fulfillment_operating_mode, 'mode2',
        )
        job = self._scan_job('fulfillment_reconnect_catchup')
        external_gid = 'gid://shopify/Fulfillment/GAP1'
        external_node = {
            'id': external_gid,
            'status': 'SUCCESS',
            'displayStatus': 'FULFILLED',
            'trackingInfo': [],
        }
        with patch.object(
            type(self.Service), '_read_order_fulfillments',
            return_value=[external_node],
        ):
            self.Service._handle_fulfillment_reconnect_catchup(job)
        evidence = self.Evidence.search([
            ('store_id', '=', self.store.id),
            ('shopify_fulfillment_gid', '=', external_gid),
        ], limit=1)
        self.assertTrue(evidence)
        # A gap-period external can never be retroactively auto-applied.
        self.assertEqual(evidence.reconciled_state, 'review')
        self.assertNotEqual(evidence.reconciled_state, 'applied')
