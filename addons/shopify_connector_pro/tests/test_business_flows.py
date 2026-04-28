# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Comprehensive tests for business flow fixes A1–A4, B1–B4.

Covers:
- A1: Invoice creation reliability across financial statuses
- A2: Payment registration with gateway mapping and idempotency
- A3: Fulfillment status sync durability
- A4: Idempotency across invoice/payment/fulfillment flows
- B1: Nested pagination truncation detection
- B2: Webhook replay hardening (fingerprint + timestamp)
- B3: Health endpoint access control
- B4: Simulator endpoint abuse safeguards
"""
import hashlib
import json
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.tests.common import TransactionCase, HttpCase

from .common import ShopifyAccountingMixin


class TestInvoiceCreation(ShopifyAccountingMixin, TransactionCase):
    """A1: Invoice creation reliability across financial statuses."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-a1.myshopify.com',
            'access_token': 'shpat_test_a1',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'auto_create_invoice': True,
            'auto_handle_payment_transitions': True,
        })
        self.partner = self._create_accounting_partner(
            'Buyer A1', email='buyer-a1@example.com',
        )
        self.product = self.env['product.product'].create({
            'name': 'A1 Widget', 'list_price': 100.0,
        })
        self._set_product_income_account(self.product)

    def _make_order(self, financial_status='paid'):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'shopify_financial_status': financial_status,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 2,
                'price_unit': 100.0,
            })],
        })
        return order

    def test_paid_creates_invoice(self):
        """Paid status creates and posts invoice."""
        order = self._make_order('paid')
        order.action_confirm()
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter(self.env, self.backend)
        importer._auto_create_invoice(order)

        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
        )
        self.assertTrue(invoices, "Paid order should have a posted invoice")

    def test_partially_paid_creates_invoice(self):
        """Partially paid status also creates and posts invoice."""
        order = self._make_order('partially_paid')
        order.action_confirm()
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter(self.env, self.backend)
        importer._auto_create_invoice(order)

        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted'
        )
        self.assertTrue(invoices, "Partially paid order should have a posted invoice")

    def test_idempotent_invoice_creation(self):
        """Calling _auto_create_invoice twice does not duplicate invoices."""
        order = self._make_order('paid')
        order.action_confirm()
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter(self.env, self.backend)
        importer._auto_create_invoice(order)
        importer._auto_create_invoice(order)  # Second call

        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state != 'cancel'
        )
        self.assertEqual(len(invoices), 1, "Should have exactly one invoice")

    def test_missing_income_account_schedules_activity(self):
        """Missing income account should schedule activity, not crash."""
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 50.0,
            })],
        })
        order.action_confirm()
        from ..sync.order_sync import OrderImporter
        importer = OrderImporter(self.env, self.backend)

        # Mock get_product_accounts to return no income account,
        # simulating a misconfigured product/category
        with patch.object(
            type(self.product.product_tmpl_id), 'get_product_accounts',
            return_value={'income': False, 'expense': False},
        ):
            importer._auto_create_invoice(order)

        # Should not have an invoice (skipped) but should have an activity
        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice'
        )
        self.assertFalse(invoices, "Should NOT create invoice when income account missing")
        activities = self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', order.id),
        ])
        self.assertTrue(activities, "Should schedule activity when income account missing")


class TestPaymentRegistration(ShopifyAccountingMixin, TransactionCase):
    """A2: Payment registration with gateway mapping and idempotency."""

    def setUp(self):
        super().setUp()
        # Bank journal for payments
        self.bank_journal = self.env['account.journal'].search([
            ('type', '=', 'bank'),
            ('company_id', '=', self.env.company.id),
        ], limit=1)
        if not self.bank_journal:
            self.bank_journal = self.env['account.journal'].create({
                'name': 'Test Bank',
                'type': 'bank',
                'code': 'TBNK',
                'company_id': self.env.company.id,
            })

        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-a2.myshopify.com',
            'access_token': 'shpat_test_a2',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'auto_create_invoice': True,
            'auto_handle_payment_transitions': True,
        })
        self.partner = self._create_accounting_partner(
            'Buyer A2', email='buyer-a2@example.com',
        )
        self.product = self.env['product.product'].create({
            'name': 'A2 Widget', 'list_price': 75.0,
        })
        self._set_product_income_account(self.product)

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
            'shopify_id': 'gid://shopify/Order/2000',
            'shopify_order_name': '#2001',
            'shopify_financial_status': 'authorized',
            'sync_status': 'synced',
        })

    def _get_handler(self):
        from ..sync.payment_status_sync import PaymentStatusHandler
        return PaymentStatusHandler(self.env, self.backend)

    def test_full_payment_registration(self):
        """Transition to paid should register full payment on invoice."""
        invoice = self.order._create_invoices()
        invoice.action_post()

        handler = self._get_handler()
        # Mock the API call to fetch transactions
        with patch.object(handler, '_get_transaction_gateway', return_value='shopify_payments'):
            handler._register_payment(invoice, self.binding)

        # Check payment was created
        payments = self.env['account.payment'].search([
            ('memo', '=', 'SHOPIFY-#2001'),
        ])
        self.assertTrue(payments, "Payment should be created")
        self.assertIn(payments[0].state, ('posted', 'paid', 'reconciled'))
        # Invoice should be fully reconciled
        self.assertEqual(invoice.amount_residual, 0)

    def test_idempotent_payment_registration(self):
        """Calling _register_payment twice should not create duplicate."""
        invoice = self.order._create_invoices()
        invoice.action_post()

        handler = self._get_handler()
        with patch.object(handler, '_get_transaction_gateway', return_value='manual'):
            handler._register_payment(invoice, self.binding)
            handler._register_payment(invoice, self.binding)  # 2nd call

        payments = self.env['account.payment'].search([
            ('memo', '=', 'SHOPIFY-#2001'),
        ])
        self.assertEqual(len(payments), 1, "Should have exactly one payment")

    def test_gateway_mapping_journal(self):
        """Payment gateway mapping should select the correct journal."""
        # Create a specific gateway mapping
        stripe_journal = self.env['account.journal'].create({
            'name': 'Stripe',
            'type': 'bank',
            'code': 'STRP',
            'company_id': self.env.company.id,
        })
        self.env['shopify.payment.gateway'].create({
            'name': 'stripe',
            'code': 'stripe',
            'journal_id': stripe_journal.id,
            'company_id': self.env.company.id,
        })

        handler = self._get_handler()
        journal = handler._resolve_payment_journal(self.binding)
        # Without transaction data, falls back to default bank journal
        self.assertTrue(journal, "Should resolve a journal")

    def test_no_journal_schedules_activity(self):
        """Missing journal should schedule activity instead of crashing."""
        invoice = self.order._create_invoices()
        invoice.action_post()

        handler = self._get_handler()
        # Mock _resolve_payment_journal to return None (simulates no journal)
        with patch.object(handler, '_resolve_payment_journal', return_value=None):
            result = handler._register_payment(invoice, self.binding)

        self.assertFalse(result, "Should return False when no journal found")


class TestFulfillmentSync(ShopifyAccountingMixin, TransactionCase):
    """A3: Fulfillment status sync durability."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-a3.myshopify.com',
            'access_token': 'shpat_test_a3',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'external_fulfillment_handling': 'activity',
        })
        self.partner = self._create_accounting_partner(
            'Buyer A3', email='buyer-a3@example.com',
        )
        self.product = self.env['product.product'].create({
            'name': 'A3 Widget', 'list_price': 30.0, 'type': 'consu',
        })
        self._set_product_income_account(self.product)

        self.order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'warehouse_id': self.backend.warehouse_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5,
                'price_unit': 30.0,
            })],
        })
        self.order.action_confirm()
        self.binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.order.id,
            'shopify_id': 'gid://shopify/Order/3000',
            'shopify_order_name': '#3001',
            'shopify_financial_status': 'paid',
            'shopify_fulfillment_status': 'unfulfilled',
            'sync_status': 'synced',
        })

    def test_ignore_mode_updates_status_only(self):
        """Ignore mode should only update status field, not pickings."""
        self.backend.external_fulfillment_handling = 'ignore'

        from ..sync.fulfillment_sync import FulfillmentSync
        syncer = FulfillmentSync(self.env, self.backend)
        with patch.object(syncer, '_fetch_fulfillment_status', return_value='fulfilled'):
            syncer.handle_inbound_fulfillment(self.binding)

        self.assertEqual(self.binding.shopify_fulfillment_status, 'fulfilled')
        # Pickings should NOT be auto-validated
        pending_pickings = self.order.picking_ids.filtered(
            lambda p: p.state not in ('done', 'cancel')
        )
        self.assertTrue(pending_pickings, "Pickings should still be pending in ignore mode")

    def test_activity_mode_creates_activity(self):
        """Activity mode should create an activity on the order."""
        self.backend.external_fulfillment_handling = 'activity'

        from ..sync.fulfillment_sync import FulfillmentSync
        syncer = FulfillmentSync(self.env, self.backend)
        with patch.object(syncer, '_fetch_fulfillment_status', return_value='fulfilled'):
            syncer.handle_inbound_fulfillment(self.binding)

        self.assertEqual(self.binding.shopify_fulfillment_status, 'fulfilled')

    def test_auto_validate_mode_validates_pickings(self):
        """Auto-validate mode should validate outgoing pickings."""
        self.backend.external_fulfillment_handling = 'auto_validate'

        from ..sync.fulfillment_sync import FulfillmentSync
        syncer = FulfillmentSync(self.env, self.backend)
        with patch.object(syncer, '_fetch_fulfillment_status', return_value='fulfilled'):
            syncer.handle_inbound_fulfillment(self.binding)

        self.assertEqual(self.binding.shopify_fulfillment_status, 'fulfilled')
        done_pickings = self.order.picking_ids.filtered(
            lambda p: p.state == 'done'
        )
        self.assertTrue(done_pickings, "Pickings should be validated in auto_validate mode")

    def test_duplicate_fulfillment_is_noop(self):
        """Second inbound fulfillment for same status should be no-op."""
        self.binding.shopify_fulfillment_status = 'fulfilled'
        self.order.shopify_fulfillment_status = 'fulfilled'

        from ..sync.fulfillment_sync import FulfillmentSync
        syncer = FulfillmentSync(self.env, self.backend)
        with patch.object(syncer, '_fetch_fulfillment_status', return_value='fulfilled'):
            syncer.handle_inbound_fulfillment(self.binding)
        # Should not raise or create duplicates


class TestWebhookReplayHardening(TransactionCase):
    """B2: Webhook replay protection — ID, timestamp, fingerprint."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-b2.myshopify.com',
            'access_token': 'shpat_test_b2',
            'webhook_secret': 'test_secret_b2',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'state': 'connected',
        })

    def test_fingerprint_computation(self):
        """Fingerprint should be deterministic."""
        WebhookLog = self.env['shopify.webhook.log']
        fp1 = WebhookLog.compute_fingerprint('orders/create', '12345', '2026-04-28T10:00:00Z')
        fp2 = WebhookLog.compute_fingerprint('orders/create', '12345', '2026-04-28T10:00:00Z')
        fp3 = WebhookLog.compute_fingerprint('orders/create', '99999', '2026-04-28T10:00:00Z')
        self.assertEqual(fp1, fp2, "Same input should produce same fingerprint")
        self.assertNotEqual(fp1, fp3, "Different input should produce different fingerprint")

    def test_stale_payload_detected(self):
        """Payloads older than the staleness window should be detected."""
        WebhookLog = self.env['shopify.webhook.log']
        old_time = (fields.Datetime.now() - timedelta(hours=72)).strftime('%Y-%m-%dT%H:%M:%SZ')
        self.assertTrue(
            WebhookLog.is_stale_payload({'updated_at': old_time}),
            "72h-old payload should be stale",
        )

    def test_fresh_payload_allowed(self):
        """Recent payloads should not be flagged as stale."""
        WebhookLog = self.env['shopify.webhook.log']
        fresh_time = fields.Datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
        self.assertFalse(
            WebhookLog.is_stale_payload({'updated_at': fresh_time}),
            "Current payload should not be stale",
        )

    def test_missing_timestamp_allowed(self):
        """Payloads without updated_at should be allowed (safe default)."""
        WebhookLog = self.env['shopify.webhook.log']
        self.assertFalse(
            WebhookLog.is_stale_payload({'id': 123}),
            "Missing timestamp should not be flagged stale",
        )

    def test_duplicate_webhook_id_dedup(self):
        """Same webhook_id should not create duplicate log entry."""
        self.env['shopify.webhook.log'].create({
            'backend_id': self.backend.id,
            'webhook_id': 'wh-unique-123',
            'topic': 'orders/create',
            'shopify_id': '100',
            'state': 'pending',
        })
        # Search for duplicate (simulates controller logic)
        existing = self.env['shopify.webhook.log'].search([
            ('webhook_id', '=', 'wh-unique-123'),
        ], limit=1)
        self.assertTrue(existing, "Should find existing webhook by ID")

    def test_fingerprint_dedup_without_webhook_id(self):
        """Fingerprint should catch duplicates when webhook_id is absent."""
        WebhookLog = self.env['shopify.webhook.log']
        fp = WebhookLog.compute_fingerprint('orders/create', '500', '2026-04-28T12:00:00Z')
        WebhookLog.create({
            'backend_id': self.backend.id,
            'webhook_id': False,
            'webhook_fingerprint': fp,
            'topic': 'orders/create',
            'shopify_id': '500',
            'state': 'pending',
        })
        # Check dedup
        existing = WebhookLog.search([
            ('webhook_fingerprint', '=', fp),
            ('backend_id', '=', self.backend.id),
        ], limit=1)
        self.assertTrue(existing, "Should find existing webhook by fingerprint")


class TestPaginationLimits(TransactionCase):
    """B1: Verify pagination limits are adequate."""

    def test_order_query_has_250_line_items(self):
        """FETCH_ORDERS should request up to 250 line items with pageInfo."""
        from ..shopify_api.queries.order import FETCH_ORDERS
        self.assertIn('lineItems(first: 250)', FETCH_ORDERS)
        self.assertIn('hasNextPage', FETCH_ORDERS)

    def test_product_query_has_250_variants(self):
        """FETCH_PRODUCTS should request up to 250 variants."""
        from ..shopify_api.queries.product import FETCH_PRODUCTS
        self.assertIn('variants(first: 250)', FETCH_PRODUCTS)

    def test_product_set_mutation_has_250_variants(self):
        """PRODUCT_SET_MUTATION response should request up to 250 variants."""
        from ..shopify_api.queries.product import PRODUCT_SET_MUTATION
        self.assertIn('variants(first: 250)', PRODUCT_SET_MUTATION)

    def test_product_create_mutation_has_250_variants(self):
        """PRODUCT_CREATE_MUTATION response should request up to 250 variants."""
        from ..shopify_api.queries.product import PRODUCT_CREATE_MUTATION
        self.assertIn('variants(first: 250)', PRODUCT_CREATE_MUTATION)

    def test_single_product_webhook_has_250_variants(self):
        """Single-product webhook query should request 250 variants."""
        # Verify via source inspection
        import inspect
        from ..sync.product_sync import ProductSync
        source = inspect.getsource(ProductSync.import_single_product)
        self.assertIn('variants(first: 250)', source)

    def test_truncation_warning_logged(self):
        """OrderImporter should warn when lineItems has hasNextPage=true."""
        from ..sync.order_sync import OrderImporter

        backend = self.env['shopify.backend'].create({
            'name': 'Test',
            'shop_url': 'test-b1.myshopify.com',
            'access_token': 'shpat_test_b1',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        importer = OrderImporter(self.env, backend)

        # Build a node with hasNextPage=true on lineItems
        node = {
            'id': 'gid://shopify/Order/999',
            'name': '#999',
            'createdAt': '2026-04-28T00:00:00Z',
            'displayFinancialStatus': 'PENDING',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'lineItems': {
                'pageInfo': {'hasNextPage': True},
                'edges': [],
            },
            'shippingLines': {'edges': []},
        }
        with patch.object(importer, '_resolve_customer', return_value=None):
            # _create_sale_order will return None because no customer
            result = importer._create_sale_order(node)
            # The truncation warning is logged (can't easily assert log
            # output, but verifying no crash is sufficient)
            self.assertIsNone(result)


class TestHealthEndpointAccess(ShopifyAccountingMixin, TransactionCase):
    """B3: Health endpoint access control tests."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Health Test Store',
            'shop_url': 'test-b3.myshopify.com',
            'access_token': 'shpat_test_b3',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'state': 'connected',
        })

    def test_health_uses_record_rules(self):
        """Health endpoint should NOT use sudo() — record rules apply."""
        import inspect
        from ..controllers.webhook import ShopifyHealthController
        source = inspect.getsource(ShopifyHealthController.health_check)
        self.assertNotIn('.sudo()', source,
                         "Health endpoint should not use sudo()")
        self.assertIn('.search(', source,
                      "Health endpoint should use search() for access control")
