# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Item 4 (visibility batch): silent-degradation paths must surface.

AUD-003/004 — refund/payout cron counters reach the backend chatter.
AUD-005    — a crashed order webhook enters the retry/dead-letter
             machine instead of being marked 'done'.
AUD-006    — reverse-sync failures (orderMarkAsPaid / refundCreate)
             schedule a warning activity on the sale order.
AUD-007/008/011/012/013 — same-file minors: reconcile failure,
             voided-cancel failures, unexpected raises and the activity
             helper itself degrade visibly (activity and/or ERROR log).
"""
import json

from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


def _failing_client(exc=None):
    client = MagicMock()
    err = exc or ConnectionError("simulated Shopify API failure")
    client.execute.side_effect = err
    client.execute_mutation.side_effect = err
    return client


class VisibilityFixtureMixin(ShopifyAccountingMixin):

    def _make_backend(self, **extra):
        vals = {
            'name': 'Visibility Store',
            'shop_url': 'visibility-test.myshopify.com',
            'access_token': 'shpat_visibility_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'state': 'connected',
        }
        vals.update(extra)
        return self.env['shopify.backend'].create(vals)

    def _make_order_with_binding(self, backend, financial_status='paid',
                                 shopify_id='gid://shopify/Order/4000'):
        partner = self._create_accounting_partner(
            'Visibility Buyer', email='visibility@example.com',
        )
        product = self.env['product.product'].create({
            'name': 'Visibility Widget', 'list_price': 50.0,
        })
        self._set_product_income_account(product)
        order = self.env['sale.order'].create({
            'partner_id': partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        order.action_confirm()
        binding = self.env['shopify.order.binding'].create({
            'backend_id': backend.id,
            'odoo_id': order.id,
            'shopify_id': shopify_id,
            'shopify_order_name': '#VIS-1001',
            'shopify_financial_status': financial_status,
            'sync_status': 'synced',
        })
        return order, binding

    def _activities(self, order, exclude_summary=None):
        acts = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', order.id),
        ])
        if exclude_summary:
            acts = acts.filtered(
                lambda a: exclude_summary not in (a.summary or '').lower())
        return acts


class TestCronCounterVisibility(VisibilityFixtureMixin, TransactionCase):
    """AUD-003/004: error counters returned by refund/payout sync must
    reach the merchant (backend chatter via _notify_sync_error), not be
    discarded by the cron."""

    def test_refund_cron_surfaces_fetch_errors(self):
        backend = self._make_backend(auto_sync_orders=True)
        self._make_order_with_binding(backend, financial_status='refunded')
        before = backend.message_ids
        with patch.object(type(backend), '_make_api_client',
                          return_value=_failing_client()):
            self.env['shopify.backend']._cron_import_refunds()
        new_msgs = (backend.message_ids - before).mapped('body')
        self.assertTrue(
            any('refund' in b.lower() and 'sync alert' in b.lower()
                for b in new_msgs),
            "AUD-003: a refund fetch failure must post a Sync Alert to "
            "the backend chatter (got %s)" % new_msgs,
        )

    def test_payout_cron_surfaces_fetch_errors(self):
        backend = self._make_backend()
        before = backend.message_ids
        with patch.object(type(backend), '_make_api_client',
                          return_value=_failing_client()):
            self.env['shopify.backend']._cron_import_payouts()
        new_msgs = (backend.message_ids - before).mapped('body')
        self.assertTrue(
            any('payout' in b.lower() and 'sync alert' in b.lower()
                for b in new_msgs),
            "AUD-004: a payout fetch failure must post a Sync Alert to "
            "the backend chatter (got %s)" % new_msgs,
        )


class TestWebhookOrderRetry(VisibilityFixtureMixin, TransactionCase):
    """AUD-005: an orders/create webhook whose import crashes must NOT
    be recorded as done — it enters the retry → dead-letter machine."""

    def test_failed_order_webhook_enters_retry(self):
        backend = self._make_backend()
        log = self.env['shopify.webhook.log'].create({
            'backend_id': backend.id,
            'topic': 'orders/create',
            'webhook_id': 'wh_aud005_1',
            'payload': json.dumps({'id': 424242}),
            'state': 'pending',
        })
        with patch.object(type(backend), '_make_api_client',
                          return_value=_failing_client()):
            self.env['shopify.webhook.log']._cron_process_pending()
        self.assertEqual(
            log.state, 'error',
            "AUD-005: a crashed order import must put the webhook in "
            "'error' for retry, not '%s'" % log.state,
        )
        self.assertEqual(log.retry_count, 1)
        self.assertTrue(log.error_message,
                        "The failure reason must be recorded")


class TestReverseSyncFailureVisibility(VisibilityFixtureMixin,
                                       TransactionCase):
    """AUD-006: Odoo→Shopify divergence (mark-as-paid / refundCreate
    failures) must schedule a warning activity on the sale order."""

    def test_mark_as_paid_failure_schedules_activity(self):
        backend = self._make_backend(reverse_sync_payment=True)
        order, _binding = self._make_order_with_binding(
            backend, financial_status='pending')
        invoice = order._create_invoices()
        with patch.object(type(backend), '_make_api_client',
                          return_value=_failing_client()):
            invoice.action_post()
        acts = self._activities(order)
        self.assertTrue(
            acts,
            "AUD-006: failed orderMarkAsPaid must schedule an activity",
        )
        notes = ' '.join((a.note or '') + (a.summary or '') for a in acts)
        self.assertIn('paid', notes.lower(),
                      "Activity must say the mark-as-paid sync failed")

    def test_refund_create_failure_schedules_activity(self):
        backend = self._make_backend(reverse_sync_refund=True)
        order, _binding = self._make_order_with_binding(
            backend, financial_status='paid')
        invoice = order._create_invoices()
        invoice.with_context(shopify_no_auto_export=True).action_post()
        reversal = invoice._reverse_moves(
            default_values_list=[{'ref': 'AUD-006 test refund'}],
            cancel=False,
        )
        with patch.object(type(backend), '_make_api_client',
                          return_value=_failing_client()):
            reversal.action_post()
        acts = self._activities(order)
        self.assertTrue(
            acts,
            "AUD-006: failed Shopify refundCreate must schedule an "
            "activity — Odoo has a posted credit note Shopify knows "
            "nothing about",
        )
        notes = ' '.join((a.note or '') + (a.summary or '') for a in acts)
        self.assertIn('refund', notes.lower(),
                      "Activity must say the Shopify refund failed")


class TestPaymentPathMinorVisibility(VisibilityFixtureMixin,
                                     TransactionCase):
    """AUD-007/008/012/013: minor silent branches in the payment path."""

    def _handler(self, backend):
        from ..sync.payment_status_sync import PaymentStatusHandler
        return PaymentStatusHandler(self.env, backend)

    def test_reconcile_failure_schedules_activity(self):
        """AUD-007: payment posts but reconciliation fails — 'manual
        reconciliation required' must reach a human."""
        backend = self._make_backend()
        order, binding = self._make_order_with_binding(backend)
        invoice = order._create_invoices()
        invoice.with_context(shopify_no_auto_export=True).action_post()
        with patch.object(type(backend), '_make_api_client',
                          return_value=_failing_client()):
            handler = self._handler(backend)
            with patch.object(type(self.env['account.move.line']),
                              'reconcile',
                              side_effect=Exception('simulated lock')):
                handler._register_payment(invoice, binding)
        acts = self._activities(order)
        self.assertTrue(
            any('reconcil' in ((a.note or '') + (a.summary or '')).lower()
                for a in acts),
            "AUD-007: reconcile failure must schedule a manual-review "
            "activity (got %s)" % acts.mapped('summary'),
        )

    def test_voided_draft_invoice_cancel_failure_schedules_activity(self):
        """AUD-008: voided transition where the draft invoice cannot be
        cancelled must be visible, not WARNING-only."""
        backend = self._make_backend(auto_handle_payment_transitions=True)
        order, binding = self._make_order_with_binding(
            backend, financial_status='authorized')
        invoice = order._create_invoices()
        self.assertEqual(invoice.state, 'draft')
        with patch.object(type(backend), '_make_api_client',
                          return_value=_failing_client()):
            handler = self._handler(backend)
            with patch.object(type(self.env['account.move']),
                              'button_cancel',
                              side_effect=Exception('simulated lock')):
                handler._transition_to_voided(binding, 'authorized',
                                              'voided')
        acts = self._activities(order)
        self.assertTrue(
            any('invoice' in ((a.note or '') + (a.summary or '')).lower()
                and 'cancel' in ((a.note or '') + (a.summary or '')).lower()
                for a in acts),
            "AUD-008: failed DRAFT-INVOICE cancel on void must schedule "
            "an activity naming the invoice — the generic SO-cancel "
            "activity is not enough (got %s)" % acts.mapped('summary'),
        )

    def test_auto_register_payment_unexpected_raise_is_visible(self):
        """AUD-012: an unexpected raise in _auto_register_payment means
        a captured payment was never registered — ERROR + activity."""
        backend = self._make_backend()
        order, binding = self._make_order_with_binding(backend)
        invoice = order._create_invoices()
        invoice.with_context(shopify_no_auto_export=True).action_post()
        self.assertGreater(invoice.amount_residual, 0)

        from ..sync.order_sync import OrderImporter
        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = backend
        importer.client = MagicMock()

        with patch(
            'odoo.addons.shopify_connector_pro.sync.payment_status_sync.'
            'PaymentStatusHandler._register_payment',
            side_effect=Exception('simulated programming error'),
        ):
            with self.assertLogs(
                'odoo.addons.shopify_connector_pro.sync.order_sync',
                level='ERROR',
            ):
                importer._auto_register_payment(order, binding)
        acts = self._activities(order)
        self.assertTrue(
            any('payment' in ((a.note or '') + (a.summary or '')).lower()
                for a in acts),
            "AUD-012: swallowed registration failure must schedule an "
            "activity (got %s)" % acts.mapped('summary'),
        )

    def test_status_change_unexpected_raise_logs_error(self):
        """AUD-011: an unexpected raise in the bulk-import payment
        transition wrapper must log at ERROR with traceback (persistent
        programming errors must not repeat as quiet warnings)."""
        backend = self._make_backend()
        order, binding = self._make_order_with_binding(
            backend, financial_status='pending')
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = backend
        importer.client = MagicMock()
        node = {
            'id': binding.shopify_id,
            'name': binding.shopify_order_name,
            'updatedAt': '2026-06-12T02:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'refunds': [],
        }
        with patch(
            'odoo.addons.shopify_connector_pro.sync.payment_status_sync.'
            'PaymentStatusHandler.handle_status_change',
            side_effect=Exception('simulated programming error'),
        ):
            with self.assertLogs(
                'odoo.addons.shopify_connector_pro.sync.order_sync',
                level='ERROR',
            ):
                importer._import_one(node, binding)

    def test_activity_helper_failure_logs_error(self):
        """AUD-013: when the visibility mechanism itself fails, support
        must be able to detect it — ERROR with traceback, not WARNING."""
        backend = self._make_backend()
        handler = self._handler(backend)
        stub = MagicMock()
        stub.activity_schedule.side_effect = Exception('no activity type')
        stub.configure_mock(name='SO-STUB')
        with self.assertLogs(
            'odoo.addons.shopify_connector_pro.sync.payment_status_sync',
            level='ERROR',
        ):
            handler._schedule_activity(stub, 'note text')
