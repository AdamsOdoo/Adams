# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Tests closing high-risk coverage gaps (G-1 through G-5).

G-1: Backend cron methods (6 tests)
G-2: End-to-end sync flows (5 tests)
G-3: Multi-company isolation (1 test)
G-5: Import job pagination (2 tests)
"""
from unittest.mock import patch, MagicMock, call

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


# ======================================================================
# G-1: Backend Cron Methods
# ======================================================================

class TestCronMethods(TransactionCase):
    """G-1: Verify all 6 cron methods run without crashing and call
    the right sync classes. Exercises the with_company() fix."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Cron Test Store',
            'shop_url': 'cron-test.myshopify.com',
            'access_token': 'shpat_crontest',
            'company_id': self.env.company.id,
            'state': 'connected',
            'auto_sync_products': True,
            'auto_sync_customers': True,
            'auto_sync_orders': True,
            'auto_sync_collections': True,
        })

    def test_cron_sync_products(self):
        """Product cron calls run_sync on product binding model."""
        with patch.object(
            type(self.env['shopify.product.binding']),
            'run_sync',
        ) as mock_sync:
            self.env['shopify.backend']._cron_sync_products()
            mock_sync.assert_called_once_with(self.backend)
        self.backend.invalidate_recordset()
        self.assertTrue(self.backend.last_sync_date)

    def test_cron_sync_customers_import(self):
        """Customer cron (import direction) calls run_import on customer binding."""
        self.backend.customer_sync_direction = 'import'
        with patch.object(
            type(self.env['shopify.customer.binding']),
            'run_import',
        ) as mock_import:
            self.env['shopify.backend']._cron_sync_customers()
            mock_import.assert_called_once_with(self.backend)

    def test_cron_sync_discounts(self):
        """Discount cron creates DiscountSync with with_company env and exports."""
        with patch(
            'odoo.addons.shopify_connector_pro.sync.discount_sync.DiscountSync',
        ) as MockSync:
            mock_instance = MagicMock()
            MockSync.return_value = mock_instance
            self.env['shopify.backend']._cron_sync_discounts()
            # Verify DiscountSync was instantiated (exercises with_company path)
            MockSync.assert_called_once()
            # Verify export_discounts was called
            mock_instance.export_discounts.assert_called_once()

    def test_cron_sync_collections(self):
        """Collection cron creates CollectionSync and calls import_collections."""
        with patch(
            'odoo.addons.shopify_connector_pro.sync.collection_sync.CollectionSync',
        ) as MockSync:
            mock_instance = MagicMock()
            MockSync.return_value = mock_instance
            self.env['shopify.backend']._cron_sync_collections()
            MockSync.assert_called_once()
            mock_instance.import_collections.assert_called_once()

    def test_cron_import_payouts(self):
        """Payout cron creates PayoutSync and calls import_payouts."""
        with patch(
            'odoo.addons.shopify_connector_pro.sync.payout_sync.PayoutSync',
        ) as MockSync:
            mock_instance = MagicMock()
            MockSync.return_value = mock_instance
            self.env['shopify.backend']._cron_import_payouts()
            MockSync.assert_called_once()
            mock_instance.import_payouts.assert_called_once()

    def test_cron_import_refunds(self):
        """Refund cron creates RefundSync and calls import_refunds."""
        with patch(
            'odoo.addons.shopify_connector_pro.sync.refund_sync.RefundSync',
        ) as MockSync:
            mock_instance = MagicMock()
            MockSync.return_value = mock_instance
            self.env['shopify.backend']._cron_import_refunds()
            MockSync.assert_called_once()
            mock_instance.import_refunds.assert_called_once()


# ======================================================================
# G-2: End-to-End Sync Flows
# ======================================================================

class TestRefundImportE2E(ShopifyAccountingMixin, TransactionCase):
    """G-2: Refund import end-to-end flow."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Refund E2E Store',
            'shop_url': 'refund-test.myshopify.com',
            'access_token': 'shpat_refundtest',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'state': 'connected',
        })
        self.partner = self._create_accounting_partner(
            'Refund Customer', email='refund@example.com',
        )
        self.product = self.env['product.product'].create({
            'name': 'Refund Widget', 'list_price': 100.0,
        })
        self._set_product_income_account(self.product)

    def test_refund_import_creates_credit_note(self):
        """Full refund import: find order with refunded status, fetch refund,
        create credit note and refund binding."""
        # Set up a confirmed order with Shopify binding
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 100.0,
            })],
        })
        order.action_confirm()
        binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': 'gid://shopify/Order/REFUND001',
            'shopify_order_name': '#REFUND001',
            'shopify_financial_status': 'refunded',
            'sync_status': 'synced',
        })

        # Mock API response for refund fetch
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {
                'order': {
                    'refunds': [{
                        'id': 'gid://shopify/Refund/R001',
                        'createdAt': '2026-01-15T10:00:00Z',
                        'note': 'Customer returned item',
                        'totalRefundedSet': {
                            'shopMoney': {'amount': '100.00', 'currencyCode': 'USD'},
                        },
                        'refundLineItems': {'edges': []},
                    }],
                },
            },
        }

        from ..sync.refund_sync import RefundSync
        with patch.object(type(self.backend), '_make_api_client', return_value=mock_client):
            syncer = RefundSync(self.env, self.backend)
            success, errors, skipped = syncer.import_refunds()

        # Should have created a refund binding
        refund_binding = self.env['shopify.refund.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Refund/R001'),
        ])
        self.assertTrue(refund_binding, "Refund binding should be created")
        self.assertEqual(success, 1)


class TestPayoutImportE2E(TransactionCase):
    """G-2: Payout import end-to-end flow."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Payout E2E Store',
            'shop_url': 'payout-test.myshopify.com',
            'access_token': 'shpat_payouttest',
            'company_id': self.env.company.id,
            'state': 'connected',
        })

    def test_payout_import_creates_records(self):
        """Full payout import: fetch payouts, create payout + transaction records."""
        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {
                'shopifyPaymentsAccount': {
                    'payouts': {
                        'edges': [{
                            'node': {
                                'id': 'gid://shopify/ShopifyPaymentsPayout/P001',
                                'legacyResourceId': '111222333',
                                'status': 'PAID',
                                'net': {'amount': '95.00', 'currencyCode': 'USD'},
                                'gross': {'amount': '100.00', 'currencyCode': 'USD'},
                                'fee': {'amount': '5.00', 'currencyCode': 'USD'},
                                'issuedAt': '2026-01-20T00:00:00Z',
                                'summary': {
                                    'chargesFee': {'amount': '3.00'},
                                    'chargesGross': {'amount': '100.00'},
                                    'refundsFee': {'amount': '0.00'},
                                    'refundsFeeGross': {'amount': '0.00'},
                                    'adjustmentsFee': {'amount': '2.00'},
                                    'adjustmentsGross': {'amount': '0.00'},
                                },
                            },
                            'cursor': 'cursor_p1',
                        }],
                        'pageInfo': {'hasNextPage': False, 'endCursor': 'cursor_p1'},
                    },
                },
            },
        }
        # Second call for payout transactions
        mock_client.execute.side_effect = [
            mock_client.execute.return_value,
            {
                'data': {
                    'shopifyPaymentsAccount': {
                        'payoutTransactions': {
                            'edges': [{
                                'node': {
                                    'id': 'gid://shopify/ShopifyPaymentsPayoutTransaction/T001',
                                    'type': 'CHARGE',
                                    'amount': {'amount': '100.00', 'currencyCode': 'USD'},
                                    'fee': {'amount': '3.00', 'currencyCode': 'USD'},
                                    'net': {'amount': '97.00', 'currencyCode': 'USD'},
                                    'transactionDate': '2026-01-19T00:00:00Z',
                                    'sourceOrderTransactionId': 'gid://tx/1',
                                    'sourceType': 'CHARGE',
                                },
                            }],
                            'pageInfo': {'hasNextPage': False},
                        },
                    },
                },
            },
        ]

        from ..sync.payout_sync import PayoutSync
        with patch.object(type(self.backend), '_make_api_client', return_value=mock_client):
            syncer = PayoutSync(self.env, self.backend)
            success, errors = syncer.import_payouts()

        payout = self.env['shopify.payout'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_payout_id', '=', '111222333'),
        ])
        self.assertTrue(payout, "Payout record should be created")
        self.assertEqual(success, 1)


class TestGiftCardImportE2E(TransactionCase):
    """G-2: Gift card import end-to-end flow."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'GC E2E Store',
            'shop_url': 'gc-test.myshopify.com',
            'access_token': 'shpat_gctest',
            'company_id': self.env.company.id,
            'state': 'connected',
        })

    def test_gift_card_import_creates_binding(self):
        """Full gift card import: fetch cards, create gift card records."""
        mock_client = MagicMock()
        # Use fetch_paginated which returns a generator of nodes
        mock_client.fetch_paginated.return_value = iter([
            {
                'id': 'gid://shopify/GiftCard/GC001',
                'maskedCode': '••••abcd',
                'enabled': True,
                'initialValue': {
                    'amount': '50.00', 'currencyCode': 'USD',
                },
                'balance': {
                    'amount': '35.00', 'currencyCode': 'USD',
                },
                'customer': None,
                'order': None,
                'createdAt': '2026-01-10T10:00:00Z',
            },
        ])

        from ..sync.gift_card_sync import GiftCardSync
        with patch.object(type(self.backend), '_make_api_client', return_value=mock_client):
            syncer = GiftCardSync(self.env, self.backend)
            success, errors, skipped = syncer.import_gift_cards()

        gc = self.env['shopify.gift.card'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/GiftCard/GC001'),
        ])
        self.assertTrue(gc, "Gift card record should be created")
        self.assertEqual(gc.code_masked, '••••abcd')
        self.assertEqual(success, 1)


class TestCollectionExportE2E(TransactionCase):
    """G-2: Collection export end-to-end flow."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Coll E2E Store',
            'shop_url': 'coll-test.myshopify.com',
            'access_token': 'shpat_colltest',
            'company_id': self.env.company.id,
            'state': 'connected',
        })

    def test_collection_export_creates_on_shopify(self):
        """Pending collection binding triggers mutation and gets synced."""
        category = self.env['product.category'].create({'name': 'Export Category'})
        binding = self.env['shopify.collection.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': category.id,
            'sync_status': 'pending',
        })

        mock_client = MagicMock()
        mock_client.execute_mutation.return_value = {
            'collection': {
                'id': 'gid://shopify/Collection/C001',
                'handle': 'export-category',
                'title': 'Export Category',
            },
        }

        from ..sync.collection_export import CollectionExporter
        with patch.object(type(self.backend), '_make_api_client', return_value=mock_client):
            exporter = CollectionExporter(self.env, self.backend)
            success, errors, skipped = exporter.export_collections()

        binding.invalidate_recordset()
        self.assertEqual(binding.shopify_id, 'gid://shopify/Collection/C001')
        self.assertEqual(binding.sync_status, 'synced')
        self.assertEqual(success, 1)


class TestDiscountExportE2E(TransactionCase):
    """G-2: Discount export verifies correct GraphQL mutation input."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Disc E2E Store',
            'shop_url': 'disc-test.myshopify.com',
            'access_token': 'shpat_disctest',
            'company_id': self.env.company.id,
            'state': 'connected',
        })

    def test_discount_export_builds_correct_input(self):
        """Verify the GraphQL mutation input has correct structure."""
        partner = self.env['res.partner'].create({
            'name': 'Test Promoter', 'email': 'promo@test.com',
        })
        promoter = self.env['shopify.promoter'].create({
            'name': 'Test Promoter',
            'partner_id': partner.id,
            'company_id': self.env.company.id,
            'commission_rate': 10.0,
        })
        discount = self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'promoter_id': promoter.id,
            'code': 'SAVE20',
            'discount_type': 'percentage',
            'discount_value': 20.0,
            'one_per_customer': True,
            'sync_status': 'pending',
        })

        mock_client = MagicMock()
        mock_client.execute_mutation.return_value = {
            'codeDiscountNode': {
                'id': 'gid://shopify/DiscountCodeNode/D001',
                'codeDiscount': {
                    'codes': {'edges': [{'node': {'code': 'SAVE20'}}]},
                },
            },
        }

        from ..sync.discount_sync import DiscountExporter
        with patch.object(type(self.backend), '_make_api_client', return_value=mock_client):
            exporter = DiscountExporter(self.env, self.backend)
            exporter._export_one(discount)

        # Verify the mutation was called
        self.assertTrue(mock_client.execute_mutation.called)
        mutation_call = mock_client.execute_mutation.call_args
        variables = mutation_call[0][1]  # Second positional arg
        discount_input = variables.get('basicCodeDiscount', {})
        self.assertEqual(discount_input.get('code'), 'SAVE20')
        self.assertTrue(discount_input.get('appliesOncePerCustomer'))
        # Check customerGets has percentage value
        customer_gets = discount_input.get('customerGets', {})
        self.assertAlmostEqual(
            customer_gets.get('value', {}).get('percentage', 0),
            0.2,  # 20% → 0.2
        )


# ======================================================================
# G-3: Multi-Company Isolation
# ======================================================================

class TestMultiCompanyIsolation(TransactionCase):
    """G-3: Record rules enforce company-based isolation."""

    def test_multi_company_record_isolation(self):
        """Company A's bindings are invisible to Company B's user."""
        # Create Company B with its own warehouse
        company_b = self.env['res.company'].create({
            'name': 'Company B',
            'currency_id': self.env.company.currency_id.id,
        })
        warehouse_b = self.env['stock.warehouse'].search(
            [('company_id', '=', company_b.id)], limit=1,
        )
        if not warehouse_b:
            warehouse_b = self.env['stock.warehouse'].create({
                'name': 'WH B', 'code': 'WHB',
                'company_id': company_b.id,
            })

        # Create backends for each company
        backend_a = self.env['shopify.backend'].create({
            'name': 'Store A',
            'shop_url': 'store-a.myshopify.com',
            'access_token': 'shpat_a',
            'company_id': self.env.company.id,
            'state': 'connected',
        })
        backend_b = self.env['shopify.backend'].create({
            'name': 'Store B',
            'shop_url': 'store-b.myshopify.com',
            'access_token': 'shpat_b',
            'company_id': company_b.id,
            'warehouse_id': warehouse_b.id,
            'state': 'connected',
        })

        # Create product bindings in each company
        product = self.env['product.template'].create({'name': 'Shared Product'})
        binding_a = self.env['shopify.product.binding'].create({
            'backend_id': backend_a.id,
            'odoo_id': product.id,
            'shopify_id': 'gid://shopify/Product/A1',
            'sync_status': 'synced',
        })
        binding_b = self.env['shopify.product.binding'].create({
            'backend_id': backend_b.id,
            'odoo_id': product.id,
            'shopify_id': 'gid://shopify/Product/B1',
            'sync_status': 'synced',
        })

        # Create user in Company B
        user_b = self.env['res.users'].create({
            'name': 'User B',
            'login': 'user_b_isolation_test',
            'company_id': company_b.id,
            'company_ids': [(6, 0, [company_b.id])],
            'group_ids': [(4, self.env.ref(
                'shopify_connector_pro.group_shopify_user',
            ).id)],
        })

        # User B should only see their own backend
        backends_visible = self.env['shopify.backend'].with_user(user_b).search([])
        self.assertIn(backend_b, backends_visible)
        self.assertNotIn(backend_a, backends_visible)

        # User B should only see Company B's bindings
        bindings_visible = self.env['shopify.product.binding'].with_user(
            user_b
        ).search([])
        self.assertIn(binding_b, bindings_visible)
        self.assertNotIn(binding_a, bindings_visible)


# ======================================================================
# G-5: Import Job Pagination
# ======================================================================

class TestImportJobPagination(TransactionCase):
    """G-5: Import job processes multiple pages and advances cursor."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Pagination Store',
            'shop_url': 'page-test.myshopify.com',
            'access_token': 'shpat_pagetest',
            'company_id': self.env.company.id,
            'state': 'connected',
        })

    def test_import_job_processes_multiple_pages(self):
        """Job should process all pages until hasNextPage is False."""
        job = self.env['shopify.import.job'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'page_size': 2,
            'state': 'pending',
        })

        mock_client = MagicMock()
        # Page 1: hasNextPage=True, endCursor='cursor_page2'
        page1_response = {
            'data': {
                'products': {
                    'edges': [
                        {'node': {'id': 'gid://shopify/Product/P1', 'title': 'P1',
                                  'descriptionHtml': '', 'vendor': '', 'productType': '',
                                  'tags': [], 'status': 'ACTIVE', 'handle': 'p1',
                                  'variants': {'edges': []}, 'images': {'edges': []}}},
                    ],
                    'pageInfo': {'hasNextPage': True, 'endCursor': 'cursor_page2'},
                },
            },
        }
        # Page 2: hasNextPage=False
        page2_response = {
            'data': {
                'products': {
                    'edges': [
                        {'node': {'id': 'gid://shopify/Product/P2', 'title': 'P2',
                                  'descriptionHtml': '', 'vendor': '', 'productType': '',
                                  'tags': [], 'status': 'ACTIVE', 'handle': 'p2',
                                  'variants': {'edges': []}, 'images': {'edges': []}}},
                    ],
                    'pageInfo': {'hasNextPage': False, 'endCursor': 'cursor_page2_end'},
                },
            },
        }
        mock_client.execute.side_effect = [page1_response, page2_response]

        with patch.object(type(self.backend), '_make_api_client', return_value=mock_client):
            # Process page 1
            has_more = job._process_next_page()
            self.assertTrue(has_more, "Should indicate more pages after page 1")

            # Process page 2
            has_more = job._process_next_page()
            self.assertFalse(has_more, "Should indicate no more pages after page 2")

        job.invalidate_recordset()
        self.assertEqual(job.processed_pages, 2)

    def test_import_job_advances_cursor(self):
        """After first page, cursor should be set to endCursor from response."""
        job = self.env['shopify.import.job'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'page_size': 5,
            'state': 'pending',
        })

        mock_client = MagicMock()
        mock_client.execute.return_value = {
            'data': {
                'products': {
                    'edges': [
                        {'node': {'id': 'gid://shopify/Product/C1', 'title': 'C1',
                                  'descriptionHtml': '', 'vendor': '', 'productType': '',
                                  'tags': [], 'status': 'ACTIVE', 'handle': 'c1',
                                  'variants': {'edges': []}, 'images': {'edges': []}}},
                    ],
                    'pageInfo': {'hasNextPage': True, 'endCursor': 'abc123cursor'},
                },
            },
        }

        with patch.object(type(self.backend), '_make_api_client', return_value=mock_client):
            job._process_next_page()

        job.invalidate_recordset()
        self.assertEqual(job.cursor, 'abc123cursor', "Cursor should advance to endCursor")
