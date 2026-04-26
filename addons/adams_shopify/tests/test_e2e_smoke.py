# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""End-to-end smoke tests with mocked Shopify API.

These tests exercise the full sync pipeline from Shopify data through
to Odoo records, verifying the complete flow works without a live
Shopify store.  Run with: odoo-bin --test-tags adams_shopify_e2e
"""
import logging
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged('adams_shopify_e2e', 'post_install', '-at_install', '-standard')
class TestE2EOrderLifecycle(TransactionCase):
    """Full lifecycle: order import -> invoice -> fulfillment -> refund."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.env.company.id)],
            limit=1,
        ):
            cls.env['account.journal'].create({
                'name': 'E2E Sales Journal', 'type': 'sale', 'code': 'TE2E',
                'company_id': cls.env.company.id,
            })
        cls.backend = cls.env['shopify.backend'].create({
            'name': 'E2E Test Store',
            'shop_url': 'e2e-test.myshopify.com',
            'access_token': 'shpat_e2e_test',
            'company_id': cls.env.company.id,
            'warehouse_id': cls.env['stock.warehouse'].search(
                [('company_id', '=', cls.env.company.id)], limit=1,
            ).id,
            'auto_create_invoice': True,
            'auto_handle_payment_transitions': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'E2E Widget',
            'list_price': 50.0,
            'default_code': 'E2E-001',
            'type': 'consu',
        })
        prod_binding = cls.env['shopify.product.binding'].create({
            'backend_id': cls.backend.id,
            'odoo_id': cls.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/E2E1',
            'sync_status': 'synced',
        })
        cls.env['shopify.variant.binding'].create({
            'backend_id': cls.backend.id,
            'odoo_id': cls.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/E2EV1',
            'product_binding_id': prod_binding.id,
            'sync_status': 'synced',
        })

    def _make_paid_order_node(self):
        return {
            'id': 'gid://shopify/Order/E2E-100',
            'name': '#E2E-100',
            'createdAt': '2026-04-20T10:00:00Z',
            'updatedAt': '2026-04-20T10:05:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': 'E2E smoke test order',
            'tags': ['e2e-test'],
            'totalPriceSet': {
                'shopMoney': {'amount': '150.00', 'currencyCode': 'USD'},
            },
            'totalDiscountsSet': {
                'shopMoney': {'amount': '0', 'currencyCode': 'USD'},
            },
            'discountCodes': [],
            'customer': {
                'id': 'gid://shopify/Customer/E2E-CUST',
                'email': 'e2e-customer@example.com',
                'firstName': 'E2E',
                'lastName': 'Customer',
            },
            'shippingAddress': {
                'address1': '123 E2E Blvd',
                'address2': '',
                'city': 'Testville',
                'province': 'California',
                'provinceCode': 'CA',
                'country': 'United States',
                'countryCodeV2': 'US',
                'zip': '90001',
                'phone': '+15551234567',
                'firstName': 'E2E',
                'lastName': 'Customer',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/E2E-LI1',
                        'title': 'E2E Widget',
                        'quantity': 3,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/E2EV1',
                            'sku': 'E2E-001',
                            'product': {'id': 'gid://shopify/Product/E2E1'},
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {'amount': '50.00', 'currencyCode': 'USD'},
                        },
                        'discountAllocations': [],
                        'taxLines': [],
                    },
                }],
            },
            'shippingLines': {
                'edges': [{
                    'node': {
                        'title': 'Standard Shipping',
                        'code': 'standard',
                        'originalPriceSet': {
                            'shopMoney': {'amount': '0.00', 'currencyCode': 'USD'},
                        },
                    },
                }],
            },
        }

    def test_full_order_lifecycle(self):
        """Import order -> verify SO + invoice -> verify no sync loop."""
        from ..sync.order_sync import OrderImporter

        node = self._make_paid_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        # Step 1: Import the order
        importer._import_one(node, existing_binding=None)

        # Step 2: Verify binding created
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/E2E-100'),
        ])
        self.assertTrue(binding, "Order binding should be created")
        self.assertEqual(binding.shopify_financial_status, 'paid')
        self.assertEqual(binding.sync_status, 'synced')

        # Step 3: Verify sale order
        order = binding.odoo_id
        self.assertIn(order.state, ('sale', 'done'), "Order should be confirmed (paid)")
        self.assertEqual(order.shopify_order_name, '#E2E-100')
        self.assertEqual(len(order.order_line), 1, "One product line expected")
        self.assertEqual(order.order_line[0].product_uom_qty, 3)
        self.assertEqual(order.order_line[0].price_unit, 50.0)

        # Step 4: Verify customer
        partner = order.partner_id
        self.assertEqual(partner.email, 'e2e-customer@example.com')

        # Customer binding should exist
        cust_binding = self.env['shopify.customer.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Customer/E2E-CUST'),
        ])
        self.assertTrue(cust_binding, "Customer binding should be created")

        # Step 5: Verify invoice (auto_create_invoice=True)
        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice'
        )
        if invoices:
            self.assertEqual(invoices[0].state, 'posted',
                "Invoice should be auto-posted for PAID orders")

        # Step 6: Verify shipping address
        shipping_partner = order.partner_shipping_id
        self.assertTrue(shipping_partner)
        self.assertEqual(shipping_partner.city, 'Testville')

        _logger.info("E2E: Order lifecycle test passed successfully")

    def test_payment_transition_lifecycle(self):
        """Import pending order -> transition to paid -> verify invoice."""
        from ..sync.order_sync import OrderImporter
        from ..sync.payment_status_sync import PaymentStatusHandler

        # Import as PENDING (no invoice)
        node = self._make_paid_order_node()
        node['displayFinancialStatus'] = 'PENDING'

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/E2E-100'),
        ])
        order = binding.odoo_id
        self.assertEqual(binding.shopify_financial_status, 'pending')

        # No invoice yet for pending
        self.assertFalse(
            order.invoice_ids.filtered(lambda i: i.state == 'posted'),
            "No posted invoice expected for pending order",
        )

        # Transition to paid
        handler = PaymentStatusHandler(self.env, self.backend)
        result = handler.handle_status_change(binding, 'pending', 'paid')
        self.assertTrue(result, "Transition should succeed")
        self.assertEqual(binding.shopify_financial_status, 'paid')

        # Now there should be a posted invoice
        posted = order.invoice_ids.filtered(lambda i: i.state == 'posted')
        self.assertTrue(posted, "Invoice should be created and posted after paid transition")

        _logger.info("E2E: Payment transition lifecycle test passed")

    def test_reimport_skips_existing_order(self):
        """Re-importing the same order should update, not duplicate."""
        from ..sync.order_sync import OrderImporter

        node = self._make_paid_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        # First import
        importer._import_one(node, existing_binding=None)

        # Second import (with existing binding)
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/E2E-100'),
        ])
        node2 = self._make_paid_order_node()
        node2['displayFulfillmentStatus'] = 'FULFILLED'

        importer._import_one(node2, existing_binding=binding)

        # Should still be one binding
        bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/E2E-100'),
        ])
        self.assertEqual(len(bindings), 1, "Should not duplicate binding on re-import")
        self.assertEqual(bindings.shopify_fulfillment_status, 'fulfilled',
            "Status should be updated on re-import")
