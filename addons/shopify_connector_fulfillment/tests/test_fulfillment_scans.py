import uuid
from unittest.mock import patch

from odoo.tests.common import TransactionCase


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

    # ------------------------------------------------------------------
    # Reconnect catch-up: gap-period externals -> review in BOTH modes
    # ------------------------------------------------------------------

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
