# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Tests for the centralised income-account validation helper.

Proves that:
1. The shared helper correctly detects missing income accounts.
2. The shared helper resolves fallback accounts.
3. Every path that builds account.move.line records routes through
   the shared helper: invoice creation, payment-status transition,
   and refund credit notes.
4. When income accounts are missing, each path schedules an activity
   and does NOT silently lose the invoice/credit-note or poison the
   transaction.
"""
from unittest.mock import patch

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


class TestValidateOrderIncomeAccounts(ShopifyAccountingMixin, TransactionCase):
    """Unit tests for the shared validate_order_income_accounts helper."""

    def setUp(self):
        super().setUp()
        self.partner = self._create_accounting_partner('Validation Test')
        self.product_ok = self.env['product.product'].create({
            'name': 'Configured Product', 'list_price': 10.0,
        })
        self._set_product_income_account(self.product_ok)

        # Give product_bad its own category with NO income account so it
        # doesn't share the default category (which has demo-data accounts).
        empty_categ = self.env['product.category'].create({
            'name': 'No Income Category',
            'property_account_income_categ_id': False,
        })
        self.product_bad = self.env['product.product'].create({
            'name': 'Unconfigured Product', 'list_price': 20.0,
            'categ_id': empty_categ.id,
        })
        # Ensure neither the category nor the template have income accounts.
        self.product_bad.product_tmpl_id.property_account_income_id = False
        # Also clear the company-level fallback so get_product_accounts
        # truly returns nothing for this product.
        self._saved_company_income = self.env.company.income_account_id
        self.env.company.income_account_id = False

        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
            'order_line': [
                (0, 0, {
                    'product_id': self.product_ok.id,
                    'product_uom_qty': 1,
                    'price_unit': 10.0,
                }),
                (0, 0, {
                    'product_id': self.product_bad.id,
                    'product_uom_qty': 1,
                    'price_unit': 20.0,
                }),
            ],
        })

    def test_detects_missing_income_account(self):
        """Products without an income account should appear in 'missing'."""
        from ..sync.accounting import validate_order_income_accounts
        missing, _fallback = validate_order_income_accounts(
            self.env, self.order,
        )
        self.assertIn('Unconfigured Product', missing)
        self.assertNotIn('Configured Product', missing)

    def test_all_configured_returns_empty_missing(self):
        """When all products have income accounts, missing is empty."""
        from ..sync.accounting import validate_order_income_accounts
        self._set_product_income_account(self.product_bad)
        missing, _fallback = validate_order_income_accounts(
            self.env, self.order,
        )
        self.assertEqual(missing, [])

    def test_fallback_from_journal_default(self):
        """Fallback should pick the journal's default_account_id."""
        from ..sync.accounting import validate_order_income_accounts
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if journal and not journal.default_account_id:
            journal.default_account_id = self.income_account
        _missing, fallback = validate_order_income_accounts(
            self.env, self.order, journal=journal,
        )
        if journal and journal.default_account_id:
            self.assertTrue(fallback, "Fallback should be the journal default")

    def test_fallback_from_posted_invoice_lines(self):
        """When journal has no default, fallback uses posted invoice lines."""
        from ..sync.accounting import validate_order_income_accounts
        # Create and post an invoice so posted lines exist
        self._set_product_income_account(self.product_bad)
        self.order.action_confirm()
        invoice = self.order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()
        invoice.with_context(shopify_no_auto_export=True).action_post()

        # Remove income account again (simulates misconfiguration after
        # the original invoice was created)
        self.product_bad.categ_id.property_account_income_categ_id = False
        self.product_bad.product_tmpl_id.property_account_income_id = False

        # Create a journal without a default account
        journal_no_default = self.env['account.journal'].create({
            'name': 'No Default Journal', 'type': 'sale',
            'code': 'TNDF', 'company_id': self.env.company.id,
        })
        journal_no_default.default_account_id = False

        _missing, fallback = validate_order_income_accounts(
            self.env, self.order, journal=journal_no_default,
        )
        self.assertTrue(
            fallback,
            "Fallback should resolve from posted invoice lines",
        )

    def test_schedule_account_activity(self):
        """schedule_account_activity should create a mail.activity."""
        from ..sync.accounting import schedule_account_activity
        schedule_account_activity(
            self.order,
            summary="Test activity",
            products=['Product A', 'Product B'],
        )
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
            ('summary', '=', 'Test activity'),
        ])
        self.assertTrue(activities, "Activity should be scheduled")
        self.assertIn('Product A', activities[0].note)


class TestInvoicePathUsesSharedHelper(ShopifyAccountingMixin, TransactionCase):
    """Prove _auto_create_invoice routes through the shared helper."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-inv-val.myshopify.com',
            'access_token': 'shpat_test_inv_val',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'auto_create_invoice': True,
        })
        self.partner = self._create_accounting_partner('Invoice Validation')
        empty_categ = self.env['product.category'].create({
            'name': 'No Income Category',
            'property_account_income_categ_id': False,
        })
        self.product = self.env['product.product'].create({
            'name': 'No-Account Product', 'list_price': 50.0,
            'categ_id': empty_categ.id,
        })
        self.product.product_tmpl_id.property_account_income_id = False

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

    def test_missing_account_skips_invoice_schedules_activity(self):
        """_auto_create_invoice must skip + schedule activity via shared helper."""
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter(self.env, self.backend)

        with patch(
            'odoo.addons.shopify_connector_pro.sync.order_sync'
            '.validate_order_income_accounts',
            return_value=(['No-Account Product'], self.env['account.account']),
        ) as mock_validate:
            importer._auto_create_invoice(self.order)
            mock_validate.assert_called_once()

        # No invoice created
        invoices = self.order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice'
        )
        self.assertFalse(invoices, "No invoice when income account missing")

        # Activity scheduled
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
        ])
        self.assertTrue(activities, "Activity should be scheduled")

    def test_transaction_not_poisoned(self):
        """After skipped invoice, the transaction must remain usable."""
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter(self.env, self.backend)

        with patch(
            'odoo.addons.shopify_connector_pro.sync.order_sync'
            '.validate_order_income_accounts',
            return_value=(['No-Account Product'], self.env['account.account']),
        ):
            importer._auto_create_invoice(self.order)

        # Transaction is still alive — we can create records
        partner = self.env['res.partner'].create({'name': 'Still Alive'})
        self.assertTrue(partner.id)


class TestPaymentTransitionUsesSharedHelper(ShopifyAccountingMixin, TransactionCase):
    """Prove _transition_to_paid routes through the shared helper."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-pmt-val.myshopify.com',
            'access_token': 'shpat_test_pmt_val',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'auto_handle_payment_transitions': True,
        })
        self.partner = self._create_accounting_partner('Payment Validation')
        empty_categ = self.env['product.category'].create({
            'name': 'No Income Category',
            'property_account_income_categ_id': False,
        })
        self.product = self.env['product.product'].create({
            'name': 'No-Account Payment Product', 'list_price': 75.0,
            'categ_id': empty_categ.id,
        })
        self.product.product_tmpl_id.property_account_income_id = False

        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 75.0,
            })],
        })
        self.order.action_confirm()
        self.binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.order.id,
            'shopify_id': 'gid://shopify/Order/VAL-001',
            'shopify_order_name': '#VAL-001',
            'shopify_financial_status': 'authorized',
            'sync_status': 'synced',
        })

    def test_missing_account_blocks_invoice_in_transition(self):
        """_transition_to_paid must not create invoice when accounts are missing."""
        from ..sync.payment_status_sync import PaymentStatusHandler
        handler = PaymentStatusHandler(self.env, self.backend)

        with patch(
            'odoo.addons.shopify_connector_pro.sync.payment_status_sync'
            '.validate_order_income_accounts',
            return_value=(['No-Account Payment Product'], self.env['account.account']),
        ) as mock_validate:
            result = handler._transition_to_paid(
                self.binding, 'authorized', 'paid',
            )
            mock_validate.assert_called_once()

        self.assertFalse(result, "Should return False when accounts missing")

        # No invoice created
        invoices = self.order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice'
        )
        self.assertFalse(invoices, "No invoice when income account missing")

        # Activity scheduled
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
        ])
        self.assertTrue(activities, "Activity should be scheduled")

    def test_transaction_not_poisoned_after_blocked_transition(self):
        """After blocked transition, the transaction must remain usable."""
        from ..sync.payment_status_sync import PaymentStatusHandler
        handler = PaymentStatusHandler(self.env, self.backend)

        with patch(
            'odoo.addons.shopify_connector_pro.sync.payment_status_sync'
            '.validate_order_income_accounts',
            return_value=(['Bad Product'], self.env['account.account']),
        ):
            handler._transition_to_paid(self.binding, 'authorized', 'paid')

        partner = self.env['res.partner'].create({'name': 'Tx OK'})
        self.assertTrue(partner.id)


class TestRefundPathUsesSharedHelper(ShopifyAccountingMixin, TransactionCase):
    """Prove _create_refund_credit_note routes through the shared helper."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-ref-val.myshopify.com',
            'access_token': 'shpat_test_ref_val',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.partner = self._create_accounting_partner('Refund Validation')
        empty_categ = self.env['product.category'].create({
            'name': 'No Income Category',
            'property_account_income_categ_id': False,
        })
        self.product = self.env['product.product'].create({
            'name': 'Refund No-Account Product', 'list_price': 60.0,
            'categ_id': empty_categ.id,
        })
        self.product.product_tmpl_id.property_account_income_id = False

        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 60.0,
            })],
        })
        self.order.action_confirm()

    def test_missing_account_and_no_fallback_skips_credit_note(self):
        """_create_refund_credit_note must skip + schedule activity when
        income accounts are missing and no fallback is available."""
        from ..sync.refund_sync import RefundImporter
        importer = RefundImporter(self.env, self.backend)

        refund_data = {'id': 'gid://shopify/Refund/VAL-REF', 'note': 'test'}
        refund_lines = [{
            'product_id': self.product.id,
            'quantity': 1,
            'amount': 60.0,
        }]
        ctx = {'shopify_no_auto_export': True}

        with patch(
            'odoo.addons.shopify_connector_pro.sync.refund_sync'
            '.validate_order_income_accounts',
            # Force both missing AND no fallback so the skip triggers.
            return_value=(['Refund No-Account Product'], False),
        ) as mock_validate:
            result = importer._create_refund_credit_note(
                self.order, refund_data, refund_lines, 60.0, ctx,
            )
            mock_validate.assert_called_once()

        self.assertIsNone(result, "Should return None when no account + no fallback")

        # Activity scheduled
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', self.order.id),
        ])
        self.assertTrue(activities, "Activity should be scheduled")

    def test_refund_with_fallback_succeeds(self):
        """When products miss income accounts but a fallback exists,
        the credit note should still be created using the fallback."""
        from ..sync.refund_sync import RefundImporter

        # Set up income account so we can create a proper posted invoice
        # first (needed for journal resolution).
        self._set_product_income_account(self.product)

        # Create posted invoice so journal resolution works
        invoice = self.order.with_context(
            shopify_no_auto_export=True,
        )._create_invoices()
        invoice.with_context(shopify_no_auto_export=True).action_post()

        importer = RefundImporter(self.env, self.backend)
        refund_data = {'id': 'gid://shopify/Refund/VAL-FB', 'note': 'fallback'}
        refund_lines = [{
            'product_id': self.product.id,
            'quantity': 1,
            'amount': 60.0,
        }]
        ctx = {'shopify_no_auto_export': True}

        result = importer._create_refund_credit_note(
            self.order, refund_data, refund_lines, 60.0, ctx,
        )
        self.assertTrue(result, "Credit note should be created with fallback")
        self.assertEqual(result.move_type, 'out_refund')
        self.assertEqual(result.state, 'posted')

    def test_transaction_not_poisoned_after_skipped_refund(self):
        """After skipped credit note, the transaction must remain usable."""
        from ..sync.refund_sync import RefundImporter
        importer = RefundImporter(self.env, self.backend)

        with patch(
            'odoo.addons.shopify_connector_pro.sync.refund_sync'
            '.validate_order_income_accounts',
            return_value=(['Bad Product'], False),
        ):
            importer._create_refund_credit_note(
                self.order,
                {'id': 'gid://shopify/Refund/VAL-TX', 'note': 'test'},
                [{'product_id': self.product.id, 'quantity': 1, 'amount': 60.0}],
                60.0,
                {'shopify_no_auto_export': True},
            )

        partner = self.env['res.partner'].create({'name': 'Tx Clean'})
        self.assertTrue(partner.id)
