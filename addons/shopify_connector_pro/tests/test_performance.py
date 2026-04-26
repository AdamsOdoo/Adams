# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""Performance profiling tests for order import.

These tests measure import throughput with realistic batch sizes to
identify bottlenecks. They use mocked API responses, so they profile
the Odoo ORM layer + sync logic, not network latency.

Run with: odoo-bin --test-tags shopify_connector_pro_performance
"""
import logging
import time
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase, tagged

_logger = logging.getLogger(__name__)


@tagged('shopify_connector_pro_performance', 'post_install', '-at_install', '-standard')
class TestOrderImportPerformance(TransactionCase):
    """Profile batch order import to detect regressions."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure sales journal exists
        if not cls.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', cls.env.company.id)],
            limit=1,
        ):
            cls.env['account.journal'].create({
                'name': 'Perf Sales Journal', 'type': 'sale', 'code': 'TPRF',
                'company_id': cls.env.company.id,
            })

        cls.backend = cls.env['shopify.backend'].create({
            'name': 'Perf Test Store',
            'shop_url': 'perf-test.myshopify.com',
            'access_token': 'shpat_perf_test',
            'company_id': cls.env.company.id,
            'warehouse_id': cls.env['stock.warehouse'].search(
                [('company_id', '=', cls.env.company.id)], limit=1,
            ).id,
            'auto_create_invoice': False,  # Skip invoicing for pure import perf
        })

        # Create a few products with variant bindings
        cls.products = []
        for i in range(5):
            prod = cls.env['product.product'].create({
                'name': f'Perf Widget {i}',
                'list_price': 10.0 + i * 5,
                'default_code': f'PERF-{i:03d}',
            })
            prod_binding = cls.env['shopify.product.binding'].create({
                'backend_id': cls.backend.id,
                'odoo_id': prod.product_tmpl_id.id,
                'shopify_id': f'gid://shopify/Product/{1000 + i}',
                'sync_status': 'synced',
            })
            cls.env['shopify.variant.binding'].create({
                'backend_id': cls.backend.id,
                'odoo_id': prod.id,
                'shopify_id': f'gid://shopify/ProductVariant/{2000 + i}',
                'product_binding_id': prod_binding.id,
                'sync_status': 'synced',
            })
            cls.products.append(prod)

    @classmethod
    def _make_order_node(cls, idx):
        """Generate a realistic order node for testing."""
        product = cls.products[idx % len(cls.products)]
        return {
            'id': f'gid://shopify/Order/{10000 + idx}',
            'name': f'#PERF-{idx:04d}',
            'createdAt': '2026-04-20T10:00:00Z',
            'updatedAt': '2026-04-20T10:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': f'Performance test order {idx}',
            'tags': ['perf-test'],
            'totalPriceSet': {
                'shopMoney': {'amount': str(product.list_price * 2), 'currencyCode': 'USD'},
            },
            'totalDiscountsSet': {
                'shopMoney': {'amount': '0', 'currencyCode': 'USD'},
            },
            'discountCodes': [],
            'customer': {
                'id': f'gid://shopify/Customer/{5000 + (idx % 20)}',
                'email': f'perf-customer-{idx % 20}@example.com',
                'firstName': f'PerfFirst{idx % 20}',
                'lastName': f'PerfLast{idx % 20}',
            },
            'shippingAddress': {
                'address1': f'{100 + idx} Perf Street',
                'address2': '',
                'city': 'Perfville',
                'province': 'California',
                'provinceCode': 'CA',
                'country': 'United States',
                'countryCodeV2': 'US',
                'zip': '90001',
                'phone': '',
                'firstName': f'PerfFirst{idx % 20}',
                'lastName': f'PerfLast{idx % 20}',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': f'gid://shopify/LineItem/{30000 + idx}',
                        'title': product.name,
                        'quantity': 2,
                        'variant': {
                            'id': f'gid://shopify/ProductVariant/{2000 + (idx % len(cls.products))}',
                            'sku': product.default_code,
                            'product': {
                                'id': f'gid://shopify/Product/{1000 + (idx % len(cls.products))}',
                            },
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {
                                'amount': str(product.list_price),
                                'currencyCode': 'USD',
                            },
                        },
                        'discountAllocations': [],
                        'taxLines': [],
                    },
                }],
            },
            'shippingLines': {'edges': []},
        }

    def test_batch_import_50_orders(self):
        """Profile: import 50 orders (typical cron batch)."""
        self._run_batch_import(50)

    def test_batch_import_250_orders(self):
        """Profile: import 250 orders (max batch size)."""
        self._run_batch_import(250)

    def _run_batch_import(self, count):
        from ..sync.order_sync import OrderImporter

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        nodes = [self._make_order_node(i) for i in range(count)]

        t0 = time.time()
        for node in nodes:
            importer._import_one(node, existing_binding=None)
        elapsed = time.time() - t0

        rate = count / elapsed if elapsed else 0
        _logger.info(
            "PERF: Imported %d orders in %.2fs (%.1f orders/sec)",
            count, elapsed, rate,
        )

        # Verify all orders were created
        bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
        ])
        self.assertEqual(len(bindings), count)

        # Basic performance gate: > 2 orders/sec (generous for test envs)
        self.assertGreater(
            rate, 2.0,
            f"Import rate too slow: {rate:.1f} orders/sec (expected > 2.0). "
            f"Investigate ORM/query bottlenecks.",
        )

        # Report query count (captured by Odoo test framework)
        _logger.info(
            "PERF: %d orders → avg %.1f ms/order, rate %.1f orders/sec",
            count, (elapsed / count) * 1000, rate,
        )
