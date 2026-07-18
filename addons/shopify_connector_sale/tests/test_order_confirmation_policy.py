from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_order_importer import (
    OrderFatalSchemaError,
    OrderPendingWait,
    OrderPolicySkip,
)
from .test_order_import_mapping import OrderImportCase


class TestOrderConfirmationPolicy(OrderImportCase):

    def _matrix_outcome(self, status, policy):
        self.settings.write({'order_confirmation_policy': policy})
        payload = self._payload(
            'gid://shopify/Order/Matrix/%s/%s' % (status, policy), status,
        )
        try:
            self.Importer._precreation_gates(payload, self.settings)
            result = self.Importer._confirmation_outcome(
                payload, self.settings,
                self.Importer._classify_manual_gateway(payload),
            )
            if result['binding_status'] == 'review':
                return 'review'
            return 'confirm' if result['confirm'] else 'quotation'
        except OrderPendingWait:
            return 'wait'
        except OrderPolicySkip as exc:
            return 'skip:%s' % exc.skip_reason
        except JobHandlerError as exc:
            return 'hold:%s' % exc.error_class

    def test_complete_eight_state_by_three_policy_matrix(self):
        expected = {
            'PAID': {
                'paid_only': 'confirm',
                'paid_or_authorized': 'confirm',
                'quotations_only': 'quotation',
            },
            'AUTHORIZED': {
                'paid_only': 'quotation',
                'paid_or_authorized': 'confirm',
                'quotations_only': 'quotation',
            },
            'PENDING': {
                'paid_only': 'wait',
                'paid_or_authorized': 'wait',
                'quotations_only': 'quotation',
            },
            'PARTIALLY_PAID': {
                'paid_only': 'hold:financial_total_mismatch',
                'paid_or_authorized': 'hold:financial_total_mismatch',
                'quotations_only': 'review',
            },
            'PARTIALLY_REFUNDED': {
                'paid_only': 'hold:financial_total_mismatch',
                'paid_or_authorized': 'hold:financial_total_mismatch',
                'quotations_only': 'hold:financial_total_mismatch',
            },
            'REFUNDED': {
                'paid_only': 'skip:unsupported_financial_state',
                'paid_or_authorized': 'skip:unsupported_financial_state',
                'quotations_only': 'skip:unsupported_financial_state',
            },
            'VOIDED': {
                'paid_only': 'skip:unsupported_financial_state',
                'paid_or_authorized': 'skip:unsupported_financial_state',
                'quotations_only': 'skip:unsupported_financial_state',
            },
            'EXPIRED': {
                'paid_only': 'skip:unsupported_financial_state',
                'paid_or_authorized': 'skip:unsupported_financial_state',
                'quotations_only': 'skip:unsupported_financial_state',
            },
        }
        self.assertEqual(len(expected), 8)
        for status, policies in expected.items():
            self.assertEqual(len(policies), 3)
            for policy, outcome in policies.items():
                with self.subTest(status=status, policy=policy):
                    self.assertEqual(
                        self._matrix_outcome(status, policy), outcome,
                    )

    def test_authorized_to_paid_refresh_confirms_without_line_rewrite(self):
        self.settings.write({'order_confirmation_policy': 'paid_only'})
        payload = self._payload(
            'gid://shopify/Order/AuthPaid', 'AUTHORIZED',
        )
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.sale_order_id.state, 'draft')
        line_before = binding.sale_order_id.order_line.read([
            'product_id', 'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ])
        payload['displayFinancialStatus'] = 'PAID'
        payload['updatedAt'] = '2026-07-17T12:00:00Z'
        same = self.Importer._apply_import(self.store, payload)
        self.assertEqual(same, binding)
        self.assertEqual(binding.sale_order_id.state, 'sale')
        self.assertEqual(binding.sale_order_id.order_line.read([
            'product_id', 'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ]), line_before)

    def test_post_confirmation_cancellation_is_evidence_only(self):
        payload = self._payload('gid://shopify/Order/CancelledAfter')
        binding = self.Importer._apply_import(self.store, payload)
        order = binding.sale_order_id
        line_before = order.order_line.read([
            'name', 'product_id', 'product_uom_qty', 'price_unit', 'discount',
            'tax_ids',
        ])
        job = self._job(target=payload['id'])
        payload['cancelledAt'] = '2026-07-17T12:00:00Z'
        payload['cancelReason'] = 'CUSTOMER'
        payload['updatedAt'] = '2026-07-17T12:00:00Z'
        self.Importer._apply_import(self.store, payload, job=job)
        self.assertEqual(order.state, 'sale')
        self.assertEqual(order.order_line.read([
            'name', 'product_id', 'product_uom_qty', 'price_unit', 'discount',
            'tax_ids',
        ]), line_before)
        self.assertEqual(
            binding.shopify_cancelled_at,
            fields.Datetime.to_datetime('2026-07-17 12:00:00'),
        )
        logs = self.JobLog.search([
            ('job_id', '=', job.id), ('event_type', '=', 'note'),
        ])
        self.assertEqual(len(logs), 1)

    def test_post_confirmation_payment_evidence_loss_is_note_only(self):
        payload = self._payload('gid://shopify/Order/EvidenceLoss')
        binding = self.Importer._apply_import(self.store, payload)
        order = binding.sale_order_id
        before = order.read(['state', 'amount_untaxed', 'amount_total'])[0]
        lines_before = order.order_line.read([
            'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ])
        job = self._job(target=payload['id'])
        payload['displayFinancialStatus'] = None
        payload['transactions'] = []
        payload['paymentGatewayNames'] = []
        payload['updatedAt'] = '2026-07-17T12:30:00Z'
        self.Importer._apply_import(self.store, payload, job=job)
        self.assertEqual(order.read([
            'state', 'amount_untaxed', 'amount_total',
        ])[0], before)
        self.assertEqual(order.order_line.read([
            'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ]), lines_before)
        self.assertEqual(self.JobLog.search_count([
            ('job_id', '=', job.id), ('event_type', '=', 'note'),
        ]), 1)
        self.assertEqual(binding.status, 'review')

    def test_changed_money_never_confirms_stale_quotation(self):
        self.settings.write({'order_confirmation_policy': 'paid_only'})
        payload = self._payload(
            'gid://shopify/Order/ChangedMoney', 'AUTHORIZED',
        )
        binding = self.Importer._apply_import(self.store, payload)
        line_before = binding.sale_order_id.order_line.read([
            'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ])
        job = self._job(target=payload['id'])
        payload['displayFinancialStatus'] = 'PAID'
        payload['updatedAt'] = '2026-07-17T12:45:00Z'
        for field_name in (
            'totalPriceSet', 'subtotalPriceSet', 'currentTotalPriceSet',
        ):
            payload[field_name] = self._money('101.00')
        self.Importer._apply_import(self.store, payload, job=job)
        binding.invalidate_recordset()
        self.assertEqual(binding.sale_order_id.state, 'draft')
        self.assertEqual(binding.status, 'review')
        self.assertEqual(binding.sale_order_id.order_line.read([
            'product_uom_qty', 'price_unit', 'discount', 'tax_ids',
        ]), line_before)
        self.assertEqual(self.JobLog.search_count([
            ('job_id', '=', job.id), ('event_type', '=', 'note'),
        ]), 1)

    def test_pending_wait_and_expiry_use_existing_job_states(self):
        Dispatch = self.env['shopify.connector.job.dispatch']
        ImporterType = type(self.Importer)
        fixed_now = datetime(2026, 7, 17, 15, 0, 0)
        waiting = self._job(
            target='gid://shopify/Order/PendingWait', state='running',
        )
        waiting.sudo().write({
            'started_at': fixed_now - timedelta(hours=1),
        })

        expired = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': 'order_import_sync',
            'state': 'running',
            'payload_hash': 'pending-expired',
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': 'gid://shopify/Order/PendingExpired',
            'expected_connection_generation': self.store.connection_generation,
            'started_at': fixed_now - timedelta(hours=25),
        })
        self.assertEqual(waiting.state, 'running')
        self.assertEqual(expired.state, 'running')
        with patch.object(fields.Datetime, 'now', return_value=fixed_now):
            with patch.object(
                ImporterType, 'import_order_sync',
                side_effect=OrderPendingWait(24),
            ):
                Dispatch._handle_order_import_sync(waiting)
                Dispatch._handle_order_import_sync(expired)
        self.assertEqual(waiting.state, 'retry_waiting')
        self.assertEqual(
            waiting.next_retry_at, fixed_now + timedelta(minutes=15),
        )
        self.assertEqual(waiting.retry_count, 0)
        self.assertFalse(waiting.error_class)
        self.assertEqual(expired.state, 'skipped')
        self.assertFalse(expired.next_retry_at)
        self.assertFalse(expired.error_class)

    def test_null_status_routes_failed_final_without_handler_replay(self):
        job = self._job(target='gid://shopify/Order/NullStatus')
        Dispatch = self.env['shopify.connector.job.dispatch']
        with patch.object(
            type(self.Importer), 'import_order_sync',
            side_effect=OrderFatalSchemaError('missing status'),
        ) as mocked:
            Dispatch._handle_order_import_sync(job)
        self.assertEqual(job.state, 'failed_final')
        self.assertEqual(job.error_class, 'data_shape_schema_mismatch')
        self.assertEqual(mocked.call_count, 1)
