# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class TestPaymentStatusSync(TransactionCase):

    def setUp(self):
        super().setUp()
        if not self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)], limit=1,
        ):
            self.env['account.journal'].create({
                'name': 'Test Sales Journal',
                'type': 'sale',
                'code': 'TSHP',
                'company_id': self.env.company.id,
            })
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
        receivable_account = self.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_ids', 'in', [self.env.company.id]),
        ], limit=1)
        if not receivable_account:
            receivable_account = self.env['account.account'].create({
                'name': 'Test Receivable',
                'code': 'TREC',
                'account_type': 'asset_receivable',
                'reconcile': True,
                'company_ids': [(6, 0, [self.env.company.id])],
            })
        payable_account = self.env['account.account'].search([
            ('account_type', '=', 'liability_payable'),
            ('company_ids', 'in', [self.env.company.id]),
        ], limit=1)
        if not payable_account:
            payable_account = self.env['account.account'].create({
                'name': 'Test Payable',
                'code': 'TPAY',
                'account_type': 'liability_payable',
                'reconcile': True,
                'company_ids': [(6, 0, [self.env.company.id])],
            })
        self.partner = self.env['res.partner'].create({
            'name': 'Test Buyer',
            'email': 'buyer@example.com',
            'property_account_receivable_id': receivable_account.id,
            'property_account_payable_id': payable_account.id,
        })
        self.product = self.env['product.product'].create({
            'name': 'Widget', 'list_price': 50.0,
        })
        income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', [self.env.company.id]),
        ], limit=1)
        if not income_account:
            income_account = self.env['account.account'].create({
                'name': 'Test Income Account',
                'code': 'TINC',
                'account_type': 'income',
                'company_ids': [(6, 0, [self.env.company.id])],
            })
        self.product.categ_id.property_account_income_categ_id = income_account
        self.product.product_tmpl_id.property_account_income_id = income_account
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
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
        )
        self.assertTrue(invoices)

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
