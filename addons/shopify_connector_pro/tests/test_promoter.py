# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase


class TestPromoter(TransactionCase):

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
        })
        self.partner = self.env['res.partner'].create({
            'name': 'John Promoter',
            'email': 'john@example.com',
        })
        self.promoter = self.env['shopify.promoter'].create({
            'name': 'John Promoter',
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
            'commission_type': 'percentage',
            'commission_rate': 10.0,
        })

    def test_promoter_creation(self):
        """Should create a promoter with defaults."""
        self.assertEqual(self.promoter.status, 'active')
        self.assertEqual(self.promoter.commission_type, 'percentage')
        self.assertEqual(self.promoter.commission_rate, 10.0)

    def test_promoter_unique_constraint(self):
        """Should prevent duplicate promoter for same partner + company."""
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['shopify.promoter'].create({
                'name': 'Duplicate',
                'partner_id': self.partner.id,
                'company_id': self.env.company.id,
            })

    def test_discount_code_creation(self):
        """Should create discount codes linked to a promoter."""
        code = self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'promoter_id': self.promoter.id,
            'code': 'JOHN10',
            'discount_type': 'percentage',
            'discount_value': 10.0,
        })
        self.assertEqual(code.code, 'JOHN10')
        self.assertTrue(code.active_on_shopify)
        self.assertEqual(code.promoter_id.id, self.promoter.id)

    def test_discount_code_unique_per_backend(self):
        """Should prevent duplicate codes per backend."""
        self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'promoter_id': self.promoter.id,
            'code': 'UNIQUE10',
            'discount_type': 'percentage',
            'discount_value': 10.0,
        })
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['shopify.discount.code'].create({
                'backend_id': self.backend.id,
                'promoter_id': self.promoter.id,
                'code': 'UNIQUE10',
                'discount_type': 'percentage',
                'discount_value': 5.0,
            })

    def test_usage_tracking(self):
        """Should track discount usage and compute totals."""
        code = self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'promoter_id': self.promoter.id,
            'code': 'TRACK10',
            'discount_type': 'percentage',
            'discount_value': 10.0,
        })

        # Create a mock order binding
        product = self.env['product.product'].create({
            'name': 'Test Product',
            'list_price': 100.0,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
        })
        order_binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': 'gid://shopify/Order/1000',
            'sync_status': 'synced',
        })

        usage = self.env['shopify.discount.usage'].create({
            'discount_code_id': code.id,
            'order_binding_id': order_binding.id,
            'discount_amount': 10.0,
            'order_total': 100.0,
            'commission_amount': 10.0,
        })

        code.invalidate_recordset()
        self.assertEqual(code.usage_count, 1)
        self.assertEqual(code.total_discount_amount, 10.0)
        self.assertEqual(code.total_order_revenue, 100.0)

    def test_promoter_performance_computed(self):
        """Should compute promoter performance from usage records."""
        code = self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'promoter_id': self.promoter.id,
            'code': 'PERF10',
            'discount_type': 'percentage',
            'discount_value': 10.0,
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
        })
        order_binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': 'gid://shopify/Order/2000',
            'sync_status': 'synced',
        })

        self.env['shopify.discount.usage'].create({
            'discount_code_id': code.id,
            'order_binding_id': order_binding.id,
            'discount_amount': 15.0,
            'order_total': 150.0,
            'commission_amount': 15.0,
        })

        self.promoter.invalidate_recordset()
        self.assertEqual(self.promoter.total_orders, 1)
        self.assertEqual(self.promoter.total_revenue, 150.0)
        self.assertEqual(self.promoter.total_discount_given, 15.0)
        self.assertEqual(self.promoter.total_commission, 15.0)

    def test_discount_usage_tracking_on_order_import(self):
        """OrderImporter._track_discount_usage should record promoter usage."""
        from ..sync.order_sync import OrderImporter

        code = self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'promoter_id': self.promoter.id,
            'code': 'IMPORT10',
            'discount_type': 'percentage',
            'discount_value': 10.0,
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
        })
        order_binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': 'gid://shopify/Order/3000',
            'sync_status': 'synced',
        })

        node = {
            'discountCodes': ['IMPORT10'],
            'totalPriceSet': {'shopMoney': {'amount': '200.0'}},
            'totalDiscountsSet': {'shopMoney': {'amount': '20.0'}},
        }

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._track_discount_usage(order_binding, node)

        usages = self.env['shopify.discount.usage'].search([
            ('discount_code_id', '=', code.id),
            ('order_binding_id', '=', order_binding.id),
        ])
        self.assertEqual(len(usages), 1)
        self.assertEqual(usages.discount_amount, 20.0)
        self.assertEqual(usages.order_total, 200.0)
        # 10% commission on 200 = 20
        self.assertEqual(usages.commission_amount, 20.0)

    def test_fixed_commission(self):
        """Fixed commission should use flat rate, not percentage."""
        self.promoter.commission_type = 'fixed'
        self.promoter.commission_rate = 5.0

        from ..sync.order_sync import OrderImporter

        code = self.env['shopify.discount.code'].create({
            'backend_id': self.backend.id,
            'promoter_id': self.promoter.id,
            'code': 'FIXED5',
            'discount_type': 'fixed_amount',
            'discount_value': 5.0,
        })

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'company_id': self.env.company.id,
        })
        order_binding = self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': 'gid://shopify/Order/4000',
            'sync_status': 'synced',
        })

        node = {
            'discountCodes': ['FIXED5'],
            'totalPriceSet': {'shopMoney': {'amount': '500.0'}},
            'totalDiscountsSet': {'shopMoney': {'amount': '5.0'}},
        }

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._track_discount_usage(order_binding, node)

        usage = self.env['shopify.discount.usage'].search([
            ('discount_code_id', '=', code.id),
        ])
        self.assertEqual(usage.commission_amount, 5.0)
