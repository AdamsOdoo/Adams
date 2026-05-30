# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Tests for P3 performance fixes.

Part A — Refund scan pruning (P3-2): proves the two-layer pruning in
RefundSync.import_refunds() correctly avoids unbounded API fan-out
while preserving correctness.

Part B — Webhook write_date regression: proves that processing an
orders/updated webhook advances the order binding's write_date,
keeping partially_refunded orders inside the cron's date window.

Part C — Reconciliation count-based refund detection: proves that
reconciliation flags orders where imported refund bindings < Shopify
refund count, closing the boolean blind spot.
"""
from datetime import timedelta
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.tests.common import TransactionCase


class TestRefundScanPruning(TransactionCase):
    """Fail-before/pass-after tests for RefundSync.import_refunds pruning."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Refund Pruning Test Store',
            'shop_url': 'refund-prune.myshopify.com',
            'access_token': 'shpat_refundprunetest',
            'company_id': self.env.company.id,
            'state': 'connected',
            'reconciliation_order_days': 30,
        })

    def _create_order_binding(self, shopify_id, financial_status):
        """Helper: create an order binding with the given status."""
        return self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': shopify_id,
            'shopify_order_name': '#%s' % shopify_id.split('/')[-1],
            'shopify_financial_status': financial_status,
            'sync_status': 'synced',
        })

    def _create_refund_binding(self, order_binding, refund_id):
        """Helper: create a refund binding linked to an order binding."""
        return self.env['shopify.refund.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': refund_id,
            'order_binding_id': order_binding.id,
            'shopify_order_id': order_binding.shopify_id,
            'refund_amount': 50.0,
            'currency_code': 'USD',
            'sync_status': 'synced',
        })

    def _make_refund_api_response(self, refund_id):
        """Helper: mock API response with one refund."""
        return {
            'data': {
                'order': {
                    'refunds': [{
                        'id': refund_id,
                        'createdAt': '2026-01-15T10:00:00Z',
                        'note': 'Test refund',
                        'totalRefundedSet': {
                            'shopMoney': {
                                'amount': '50.00',
                                'currencyCode': 'USD',
                            },
                        },
                        'refundLineItems': {'edges': []},
                        'refundShippingLines': {'edges': []},
                        'orderAdjustments': [],
                    }],
                },
            },
        }

    # ── Layer 1: fully-refunded + already imported → ZERO API calls ──

    def test_refunded_order_with_binding_skipped(self):
        """A fully-refunded order with an existing refund binding must
        produce ZERO new API calls on re-run.

        This is the primary fail-before/pass-after test.  Before the
        fix, this order would trigger one FETCH_REFUNDS API call every
        cron run forever.
        """
        binding = self._create_order_binding(
            'gid://shopify/Order/SKIP001', 'refunded',
        )
        self._create_refund_binding(binding, 'gid://shopify/Refund/R-SKIP001')

        mock_client = MagicMock()
        from ..sync.refund_sync import RefundSync
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            syncer = RefundSync(self.env, self.backend)
            success, errors, skipped = syncer.import_refunds()

        # The critical assertion: API must NOT be called for this order
        mock_client.execute.assert_not_called()
        self.assertEqual(success, 0)
        self.assertEqual(errors, 0)

    def test_refunded_order_without_binding_fetched(self):
        """A fully-refunded order with NO refund binding must still be
        fetched — this is the first-time import path."""
        binding = self._create_order_binding(
            'gid://shopify/Order/FIRST001', 'refunded',
        )
        # No refund binding — first time seeing this order's refunds

        mock_client = MagicMock()
        mock_client.execute.return_value = self._make_refund_api_response(
            'gid://shopify/Refund/R-FIRST001',
        )

        from ..sync.refund_sync import RefundSync
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            syncer = RefundSync(self.env, self.backend)
            success, errors, skipped = syncer.import_refunds()

        # API must be called exactly once for this order
        mock_client.execute.assert_called_once()
        call_args = mock_client.execute.call_args
        self.assertIn('FIRST001', str(call_args))

    # ── Layer 2: partially_refunded bounded by date window ──

    def test_partially_refunded_inside_window_fetched(self):
        """A partially_refunded order within the write_date window
        must be fetched — new refunds can still appear."""
        binding = self._create_order_binding(
            'gid://shopify/Order/PARTIAL001', 'partially_refunded',
        )
        # Binding was just created → write_date is now → inside window

        mock_client = MagicMock()
        mock_client.execute.return_value = self._make_refund_api_response(
            'gid://shopify/Refund/R-PARTIAL001',
        )

        from ..sync.refund_sync import RefundSync
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            syncer = RefundSync(self.env, self.backend)
            success, errors, skipped = syncer.import_refunds()

        mock_client.execute.assert_called_once()

    def test_partially_refunded_outside_window_skipped(self):
        """A partially_refunded order outside the write_date window
        must NOT be fetched — if a new refund arrives, the webhook
        will advance write_date back into the window."""
        binding = self._create_order_binding(
            'gid://shopify/Order/OLD001', 'partially_refunded',
        )
        # Push write_date beyond the window
        old_date = fields.Datetime.now() - timedelta(days=60)
        self.env.cr.execute(
            "UPDATE shopify_order_binding SET write_date = %s WHERE id = %s",
            (old_date, binding.id),
        )
        self.env.invalidate_all()

        mock_client = MagicMock()
        from ..sync.refund_sync import RefundSync
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            syncer = RefundSync(self.env, self.backend)
            success, errors, skipped = syncer.import_refunds()

        mock_client.execute.assert_not_called()

    # ── Correctness: new refund on partially_refunded → imported ──

    def test_new_refund_on_partially_refunded_imported(self):
        """A partially_refunded order with one existing binding that
        receives a SECOND refund must import the new one.

        This proves the pruning does NOT break correctness: the cron
        still detects new refunds on open-ended orders.
        """
        binding = self._create_order_binding(
            'gid://shopify/Order/MULTI001', 'partially_refunded',
        )
        # First refund already imported
        self._create_refund_binding(
            binding, 'gid://shopify/Refund/R-MULTI001A',
        )

        # API returns TWO refunds — one already imported, one new
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {
                'order': {
                    'refunds': [
                        {
                            'id': 'gid://shopify/Refund/R-MULTI001A',
                            'createdAt': '2026-01-10T10:00:00Z',
                            'note': 'First refund',
                            'totalRefundedSet': {
                                'shopMoney': {
                                    'amount': '30.00',
                                    'currencyCode': 'USD',
                                },
                            },
                            'refundLineItems': {'edges': []},
                            'refundShippingLines': {'edges': []},
                            'orderAdjustments': [],
                        },
                        {
                            'id': 'gid://shopify/Refund/R-MULTI001B',
                            'createdAt': '2026-01-20T10:00:00Z',
                            'note': 'Second refund',
                            'totalRefundedSet': {
                                'shopMoney': {
                                    'amount': '20.00',
                                    'currencyCode': 'USD',
                                },
                            },
                            'refundLineItems': {'edges': []},
                            'refundShippingLines': {'edges': []},
                            'orderAdjustments': [],
                        },
                    ],
                },
            },
        }

        from ..sync.refund_sync import RefundSync
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            syncer = RefundSync(self.env, self.backend)
            success, errors, skipped = syncer.import_refunds()

        # First refund skipped (existing binding), second imported
        self.assertEqual(skipped, 1, "Existing refund must be skipped")
        self.assertEqual(success, 1, "New refund must be imported")

        # Verify the new binding was created
        new_binding = self.env['shopify.refund.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Refund/R-MULTI001B'),
        ])
        self.assertTrue(new_binding, "Second refund binding must exist")

    # ── Mixed scenario: multiple orders, only some pruned ──

    def test_mixed_orders_selective_pruning(self):
        """With a mix of fully-refunded (imported), fully-refunded
        (not imported), and partially-refunded orders, only the
        correct subset triggers API calls."""
        # Order A: refunded + has binding → SKIP
        ob_a = self._create_order_binding(
            'gid://shopify/Order/MIX-A', 'refunded',
        )
        self._create_refund_binding(ob_a, 'gid://shopify/Refund/R-MIX-A')

        # Order B: refunded + NO binding → FETCH
        self._create_order_binding(
            'gid://shopify/Order/MIX-B', 'refunded',
        )

        # Order C: partially_refunded + in window → FETCH
        self._create_order_binding(
            'gid://shopify/Order/MIX-C', 'partially_refunded',
        )

        # Order D: partially_refunded + outside window → SKIP
        ob_d = self._create_order_binding(
            'gid://shopify/Order/MIX-D', 'partially_refunded',
        )
        old_date = fields.Datetime.now() - timedelta(days=60)
        self.env.cr.execute(
            "UPDATE shopify_order_binding SET write_date = %s WHERE id = %s",
            (old_date, ob_d.id),
        )
        self.env.invalidate_all()

        mock_client = MagicMock()
        # Return empty refunds for any order that IS fetched
        mock_client.execute.return_value = {
            'data': {'order': {'refunds': []}},
        }

        from ..sync.refund_sync import RefundSync
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            syncer = RefundSync(self.env, self.backend)
            syncer.import_refunds()

        # Exactly 2 API calls: Order B (refunded, no binding) and
        # Order C (partially_refunded, in window).
        # Orders A and D must be skipped.
        self.assertEqual(
            mock_client.execute.call_count, 2,
            "Only 2 of 4 orders should trigger API calls",
        )

        # Verify which orders were fetched
        called_order_ids = [
            call.args[1]['orderId']
            for call in mock_client.execute.call_args_list
        ]
        self.assertIn('gid://shopify/Order/MIX-B', called_order_ids)
        self.assertIn('gid://shopify/Order/MIX-C', called_order_ids)
        self.assertNotIn('gid://shopify/Order/MIX-A', called_order_ids)
        self.assertNotIn('gid://shopify/Order/MIX-D', called_order_ids)


# ======================================================================
# Part B — Webhook write_date regression
# ======================================================================

class TestWebhookAdvancesWriteDate(TransactionCase):
    """Regression test for the load-bearing assumption behind Layer 2:
    processing an orders/updated webhook MUST advance write_date on
    the order binding.

    If this test fails, a refactor has broken the webhook → write_date
    chain and partially_refunded orders will silently age out of the
    cron window, dropping refunds.
    """

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Webhook WriteDate Test',
            'shop_url': 'webhook-wd.myshopify.com',
            'access_token': 'shpat_webhookwdtest',
            'company_id': self.env.company.id,
            'state': 'connected',
            'reconciliation_order_days': 30,
        })
        self.binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': 'gid://shopify/Order/98765',
            'shopify_order_name': '#WD001',
            'shopify_financial_status': 'paid',
            'sync_status': 'synced',
        })

    def test_orders_updated_webhook_advances_write_date(self):
        """Processing an orders/updated webhook with a financial status
        change must advance write_date on the order binding, keeping it
        inside the refund cron's date window.

        This exercises the REAL handler path:
        webhook_log._process_event() → _handle_order_webhook() →
        PaymentStatusHandler.handle_status_change() →
        _update_status_fields() → binding.write(...)

        The secondary path (process_webhook_event → import_single_order)
        is mocked out because it requires a live API client, but the
        primary path (Path A) is the one that matters — it fires
        binding.write({'shopify_financial_status': new_status}) which
        advances write_date.
        """
        import json

        # Push write_date far into the past (outside the 30-day window)
        old_date = fields.Datetime.now() - timedelta(days=60)
        self.env.cr.execute(
            "UPDATE shopify_order_binding SET write_date = %s WHERE id = %s",
            (old_date, self.binding.id),
        )
        self.env.invalidate_all()

        # Confirm it's outside the window
        binding = self.env['shopify.order.binding'].browse(self.binding.id)
        self.assertTrue(
            binding.write_date < fields.Datetime.now() - timedelta(days=29),
            "Pre-condition: binding must be outside the 30-day window",
        )

        # Create a webhook log record simulating orders/updated with
        # financial_status changing from 'paid' to 'partially_refunded'
        webhook_log = self.env['shopify.webhook.log'].create({
            'backend_id': self.backend.id,
            'topic': 'orders/updated',
            'webhook_id': 'wh-writedate-test-001',
            'payload': json.dumps({
                'id': 98765,
                'financial_status': 'partially_refunded',
                'fulfillment_status': None,
            }),
            'state': 'pending',
        })

        # Mock the secondary path (import_single_order) which needs
        # a live API client. The primary path (Path A: _handle_order_webhook
        # inline status change) runs unpatched — this is the path we're
        # testing.
        with patch.object(
            type(self.env['shopify.order.binding']),
            'process_webhook_event',
        ):
            webhook_log._process_event()

        # Reload binding and check write_date advanced
        self.env.invalidate_all()
        binding = self.env['shopify.order.binding'].browse(self.binding.id)

        self.assertEqual(
            binding.shopify_financial_status, 'partially_refunded',
            "Webhook must update the financial status",
        )
        self.assertTrue(
            binding.write_date > fields.Datetime.now() - timedelta(minutes=1),
            "write_date must have advanced to ~now (binding is back "
            "inside the date window)",
        )

    def test_webhook_brings_order_back_into_refund_window(self):
        """End-to-end: an order that aged out of the refund cron window
        is brought back in by an orders/updated webhook, and the next
        import_refunds() run includes it.
        """
        import json

        # Push write_date outside the window
        old_date = fields.Datetime.now() - timedelta(days=60)
        self.env.cr.execute(
            "UPDATE shopify_order_binding SET write_date = %s, "
            "shopify_financial_status = 'partially_refunded' "
            "WHERE id = %s",
            (old_date, self.binding.id),
        )
        self.env.invalidate_all()

        # Before webhook: confirm refund cron would NOT include it
        mock_client = MagicMock()
        from ..sync.refund_sync import RefundSync
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            syncer = RefundSync(self.env, self.backend)
            syncer.import_refunds()
        mock_client.execute.assert_not_called()

        # Process the webhook — status changes, write_date advances
        webhook_log = self.env['shopify.webhook.log'].create({
            'backend_id': self.backend.id,
            'topic': 'orders/updated',
            'webhook_id': 'wh-window-test-001',
            'payload': json.dumps({
                'id': 98765,
                'financial_status': 'partially_refunded',
            }),
            'state': 'pending',
        })

        # The webhook handler's Path A writes to the binding when
        # financial_status changes. But here old == new ==
        # partially_refunded, so Path A won't fire. We need the
        # secondary path (import_single_order → _mark_synced) to
        # advance write_date. Mock the API client for that path.
        mock_api_client = MagicMock()
        mock_api_client.execute.return_value = {
            'data': {
                'order': {
                    'id': 'gid://shopify/Order/98765',
                    'name': '#WD001',
                    'createdAt': '2026-01-01T00:00:00Z',
                    'updatedAt': '2026-05-30T00:00:00Z',
                    'displayFinancialStatus': 'PARTIALLY_REFUNDED',
                    'displayFulfillmentStatus': 'UNFULFILLED',
                    'cancelledAt': None,
                    'closed': False,
                    'note': '',
                    'tags': [],
                    'currencyCode': 'USD',
                    'presentmentCurrencyCode': 'USD',
                    'totalPriceSet': {
                        'shopMoney': {'amount': '100.00', 'currencyCode': 'USD'},
                        'presentmentMoney': {'amount': '100.00', 'currencyCode': 'USD'},
                    },
                    'subtotalPriceSet': {
                        'shopMoney': {'amount': '100.00', 'currencyCode': 'USD'},
                        'presentmentMoney': {'amount': '100.00', 'currencyCode': 'USD'},
                    },
                    'totalShippingPriceSet': {
                        'shopMoney': {'amount': '0.00', 'currencyCode': 'USD'},
                        'presentmentMoney': {'amount': '0.00', 'currencyCode': 'USD'},
                    },
                    'totalTaxSet': {
                        'shopMoney': {'amount': '0.00', 'currencyCode': 'USD'},
                        'presentmentMoney': {'amount': '0.00', 'currencyCode': 'USD'},
                    },
                    'totalDiscountsSet': {
                        'shopMoney': {'amount': '0.00', 'currencyCode': 'USD'},
                        'presentmentMoney': {'amount': '0.00', 'currencyCode': 'USD'},
                    },
                    'discountCodes': [],
                    'customer': None,
                    'shippingAddress': None,
                    'billingAddress': None,
                    'lineItems': {'edges': [], 'pageInfo': {'hasNextPage': False}},
                    'shippingLines': {'edges': []},
                    'refunds': [{'id': 'gid://shopify/Refund/R-NEW'}],
                },
            },
        }
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_api_client,
        ):
            webhook_log._process_event()

        self.env.invalidate_all()

        # After webhook: confirm refund cron NOW includes it
        mock_client2 = MagicMock()
        mock_client2.execute.return_value = {
            'data': {'order': {'refunds': []}},
        }
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client2,
        ):
            syncer2 = RefundSync(self.env, self.backend)
            syncer2.import_refunds()

        # The order must now be included in the scan
        mock_client2.execute.assert_called_once()
        called_order_id = mock_client2.execute.call_args[1].get(
            'orderId',
            mock_client2.execute.call_args[0][1].get('orderId', ''),
        ) if mock_client2.execute.call_args else ''
        self.assertIn('98765', str(mock_client2.execute.call_args))


# ======================================================================
# Part C — Reconciliation count-based refund detection
# ======================================================================

class TestReconciliationRefundCount(TransactionCase):
    """Tests for the count-based refund reconciliation fix.

    Before the fix, reconciliation used a boolean check:
    ``if not credit_notes and not refund_bindings_exist`` — which
    missed orders with 2 Shopify refunds but only 1 imported.

    After the fix, reconciliation compares imported refund binding
    count against ``shopify_refund_count`` on the order binding.
    """

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Recon Count Test',
            'shop_url': 'recon-count.myshopify.com',
            'access_token': 'shpat_reconcounttest',
            'company_id': self.env.company.id,
            'state': 'connected',
            'reconciliation_order_days': 30,
        })

    def test_partially_imported_refunds_detected(self):
        """An order with 2 Shopify refunds but only 1 imported must be
        flagged by reconciliation.

        This is the fail-before/pass-after test for the boolean blind
        spot: before the count-based fix, this scenario was invisible
        to reconciliation.
        """
        # Create order binding with 2 refunds on Shopify
        binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': 'gid://shopify/Order/RECON001',
            'shopify_order_name': '#RECON001',
            'shopify_financial_status': 'partially_refunded',
            'shopify_refund_count': 2,
            'sync_status': 'synced',
        })

        # Only 1 refund binding imported (of 2)
        self.env['shopify.refund.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': 'gid://shopify/Refund/R-RECON001A',
            'order_binding_id': binding.id,
            'shopify_order_id': binding.shopify_id,
            'refund_amount': 30.0,
            'currency_code': 'USD',
            'sync_status': 'synced',
        })

        # Run reconciliation
        recon = self.env['shopify.reconciliation']
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {'productsCount': {'count': 0}},
        }
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            recon._reconcile_backend(self.backend)

        # Check that a sync log was created flagging the mismatch
        logs = self.env['shopify.sync.log'].search([
            ('backend_id', '=', self.backend.id),
            ('error_details', 'ilike', 'fewer refund bindings'),
        ])
        self.assertTrue(
            logs,
            "Reconciliation must flag order with 2 Shopify refunds "
            "but only 1 imported binding",
        )

    def test_fully_imported_refunds_not_flagged(self):
        """An order with 2 Shopify refunds and 2 imported bindings
        must NOT be flagged."""
        binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': 'gid://shopify/Order/RECON002',
            'shopify_order_name': '#RECON002',
            'shopify_financial_status': 'refunded',
            'shopify_refund_count': 2,
            'sync_status': 'synced',
        })
        for suffix in ('A', 'B'):
            self.env['shopify.refund.binding'].create({
                'backend_id': self.backend.id,
                'shopify_id': f'gid://shopify/Refund/R-RECON002{suffix}',
                'order_binding_id': binding.id,
                'shopify_order_id': binding.shopify_id,
                'refund_amount': 25.0,
                'currency_code': 'USD',
                'sync_status': 'synced',
            })

        recon = self.env['shopify.reconciliation']
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {'productsCount': {'count': 0}},
        }
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            recon._reconcile_backend(self.backend)

        logs = self.env['shopify.sync.log'].search([
            ('backend_id', '=', self.backend.id),
            ('error_details', 'ilike', 'fewer refund bindings'),
        ])
        self.assertFalse(
            logs,
            "Fully imported refunds must NOT be flagged as drifted",
        )

    def test_zero_refund_count_not_flagged(self):
        """Orders with shopify_refund_count=0 (pre-existing data before
        the field was added) must NOT be flagged as drifted — the zero
        default means 'unknown', not 'confirmed zero refunds'."""
        self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'shopify_id': 'gid://shopify/Order/RECON003',
            'shopify_order_name': '#RECON003',
            'shopify_financial_status': 'partially_refunded',
            'shopify_refund_count': 0,  # default / pre-migration
            'sync_status': 'synced',
        })

        recon = self.env['shopify.reconciliation']
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {'productsCount': {'count': 0}},
        }
        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            recon._reconcile_backend(self.backend)

        logs = self.env['shopify.sync.log'].search([
            ('backend_id', '=', self.backend.id),
            ('error_details', 'ilike', 'fewer refund bindings'),
        ])
        self.assertFalse(
            logs,
            "Orders with shopify_refund_count=0 (unknown) must not "
            "be flagged — they predate the field addition",
        )
