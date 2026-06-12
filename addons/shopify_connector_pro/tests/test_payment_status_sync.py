# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin
from odoo.tools import mute_logger


class TestPaymentStatusSync(ShopifyAccountingMixin, TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'auto_handle_payment_transitions': True,
        })
        self._mock_backend_api_client(self.backend)
        self.partner = self._create_accounting_partner(
            'Test Buyer', email='buyer@example.com',
        )
        self.product = self.env['product.product'].create({
            'name': 'Widget', 'list_price': 50.0,
        })
        self._set_product_income_account(self.product)
        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        self.order.action_confirm()
        self.binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.order.id,
            'shopify_id': 'gid://shopify/Order/1000',
            'shopify_order_name': '#1001',
            'shopify_financial_status': 'authorized',
            'sync_status': 'synced',
        })

    def _get_handler(self):
        from ..sync.payment_status_sync import PaymentStatusHandler
        return PaymentStatusHandler(self.env, self.backend)

    def test_authorized_to_paid_posts_draft_invoice(self):
        """When Shopify captures payment, draft invoice should be posted."""
        invoice = self.order._create_invoices()
        self.assertEqual(invoice.state, 'draft')

        handler = self._get_handler()
        result = handler.handle_status_change(self.binding, 'authorized', 'paid')

        self.assertTrue(result)
        self.assertEqual(invoice.state, 'posted')
        self.assertEqual(self.binding.shopify_financial_status, 'paid')

    def test_pending_to_paid_creates_and_posts_invoice(self):
        """When pending order is paid, invoice should be created + posted."""
        self.binding.shopify_financial_status = 'pending'
        handler = self._get_handler()
        result = handler.handle_status_change(self.binding, 'pending', 'paid')

        self.assertTrue(result)
        invoices = self.order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice'
        )
        self.assertEqual(
            len(invoices), 1,
            "Exactly one invoice should be created (not zero, not duplicates)",
        )
        self.assertEqual(invoices.state, 'posted')
        self.assertEqual(
            invoices.amount_total, self.order.amount_total,
            "Invoice total must match the sale order total",
        )

    def test_pending_to_voided_cancels_draft_invoice(self):
        """When payment is voided, draft invoice should be cancelled."""
        invoice = self.order._create_invoices()
        handler = self._get_handler()
        result = handler.handle_status_change(self.binding, 'pending', 'voided')

        self.assertTrue(result)
        self.assertEqual(invoice.state, 'cancel')
        self.assertEqual(self.binding.shopify_financial_status, 'voided')

    def test_voided_with_posted_invoice_creates_activity(self):
        """When voided but invoice is posted, should create activity (not cancel)."""
        invoice = self.order._create_invoices()
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

        handler = self._get_handler()
        result = handler.handle_status_change(self.binding, 'paid', 'voided')

        # Should return False (manual intervention needed)
        # Invoice should still be posted (never auto-cancel posted)
        self.assertEqual(invoice.state, 'posted')

    def test_same_status_is_noop(self):
        """No-op when old and new status are the same."""
        handler = self._get_handler()
        result = handler.handle_status_change(self.binding, 'paid', 'paid')
        self.assertTrue(result)

    def test_disabled_transitions_still_updates_status(self):
        """When transitions disabled, status field still updates."""
        self.backend.auto_handle_payment_transitions = False
        handler = self._get_handler()
        handler.handle_status_change(self.binding, 'authorized', 'paid')
        self.assertEqual(self.binding.shopify_financial_status, 'paid')

    def test_refund_transition_delegates_to_refund_sync(self):
        """Refund transitions should just update status, not create credit notes."""
        self.binding.shopify_financial_status = 'paid'
        handler = self._get_handler()
        result = handler.handle_status_change(self.binding, 'paid', 'partially_refunded')
        self.assertTrue(result)
        self.assertEqual(self.binding.shopify_financial_status, 'partially_refunded')

    def test_partially_paid_posts_invoice_and_creates_activity(self):
        """Partial payment should post invoice + schedule activity."""
        invoice = self.order._create_invoices()
        self.binding.shopify_financial_status = 'pending'
        handler = self._get_handler()
        result = handler.handle_status_change(self.binding, 'pending', 'partially_paid')
        self.assertTrue(result)
        self.assertEqual(invoice.state, 'posted')

    def _make_poisoning_action_post(self, invoice):
        """Return a replacement for action_post that triggers a real
        DB-level CHECK-constraint violation, genuinely poisoning the
        PostgreSQL cursor (InFailedSqlTransaction on all subsequent
        queries) — exactly the production failure mode.

        The INSERT violates ``account_move_line_check_accountable_required_fields``
        (``account_id IS NOT NULL`` for product-display lines).  This is the
        same constraint that fires in production when a draft invoice's
        line loses its income account between draft creation and posting.

        A Python-only mock (raise Exception) would NOT poison the cursor,
        so the test would pass even without the savepoint fix.
        """
        def poisoning_post(self_move):
            self_move.env.cr.execute(
                "INSERT INTO account_move_line "
                "(display_type, account_id, move_id, currency_id) "
                "VALUES ('product', NULL, %s, %s)",
                [invoice.id, invoice.currency_id.id],
            )
        return poisoning_post

    @mute_logger('odoo.sql_db',
                 'odoo.addons.shopify_connector_pro.sync.payment_status_sync')
    def test_paid_draft_post_failure_no_cursor_poison(self):
        """action_post() failure on a draft must NOT poison the cursor.

        Regression test for P0-2: when action_post() triggers a DB-level
        failure (e.g. CheckViolation), PostgreSQL aborts the transaction.
        Without a savepoint, _update_status_fields() and every subsequent
        ORM call fails with InFailedSqlTransaction.

        After the fix the action_post() is wrapped in a savepoint, so:
        (a) the cursor remains healthy,
        (b) status is NOT advanced to a success-implying state, and
        (c) an activity is scheduled for manual intervention.
        """
        invoice = self.order._create_invoices()
        self.assertEqual(invoice.state, 'draft')

        handler = self._get_handler()
        poisoning_post = self._make_poisoning_action_post(invoice)

        with patch.object(type(invoice), 'action_post', poisoning_post):
            result = handler.handle_status_change(
                self.binding, 'authorized', 'paid',
            )

        # (a) Cursor is healthy — force a real DB round-trip (not cache)
        self.binding.invalidate_recordset()
        status = self.binding.read(['shopify_financial_status'])[0]

        # (b) Status must NOT advance to 'paid'
        self.assertEqual(
            status['shopify_financial_status'], 'authorized',
            "Status must stay at old value when invoice posting fails",
        )
        self.assertFalse(result, "Handler must return False on post failure")

        # (c) Activity scheduled
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
        ])
        self.assertTrue(activities, "Activity must be scheduled on failure")

    @mute_logger('odoo.sql_db',
                 'odoo.addons.shopify_connector_pro.sync.payment_status_sync')
    def test_partially_paid_draft_post_failure_no_cursor_poison(self):
        """action_post() failure on partially_paid must NOT poison cursor.

        Same bug class as the paid-path test above, but on the
        _transition_to_partially_paid branch which also calls
        action_post() on a pre-existing draft outside a savepoint.
        """
        invoice = self.order._create_invoices()
        self.assertEqual(invoice.state, 'draft')

        self.binding.shopify_financial_status = 'pending'
        handler = self._get_handler()
        poisoning_post = self._make_poisoning_action_post(invoice)

        with patch.object(type(invoice), 'action_post', poisoning_post):
            result = handler.handle_status_change(
                self.binding, 'pending', 'partially_paid',
            )

        # (a) Cursor is healthy — force a real DB round-trip (not cache)
        self.binding.invalidate_recordset()
        status = self.binding.read(['shopify_financial_status'])[0]

        # (b) Status must NOT advance to 'partially_paid'
        self.assertEqual(
            status['shopify_financial_status'], 'pending',
            "Status must stay at old value when invoice posting fails",
        )
        self.assertFalse(result, "Handler must return False on post failure")

        # (c) Activity scheduled (the partial-payment notice should
        #     NOT fire if posting failed; only the failure activity)
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
        ])
        self.assertTrue(activities, "Activity must be scheduled on failure")
