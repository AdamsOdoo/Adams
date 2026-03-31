from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase


class TestOrderImport(TransactionCase):

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
        self.product = self.env['product.product'].create({
            'name': 'Test Widget',
            'list_price': 29.99,
            'default_code': 'WIDGET-001',
        })
        # Create variant binding so order can resolve the product
        product_binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/100',
            'sync_status': 'synced',
        })
        self.variant_binding = self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/200',
            'product_binding_id': product_binding.id,
            'sync_status': 'synced',
        })

    def _make_order_node(self, order_id='gid://shopify/Order/1000', name='#1001',
                         financial_status='PAID'):
        return {
            'id': order_id,
            'name': name,
            'createdAt': '2026-03-28T10:00:00Z',
            'updatedAt': '2026-03-28T10:00:00Z',
            'displayFinancialStatus': financial_status,
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': 'Test order',
            'tags': [],
            'totalPriceSet': {'shopMoney': {'amount': '29.99', 'currencyCode': 'USD'}},
            'customer': {
                'id': 'gid://shopify/Customer/500',
                'email': 'buyer@example.com',
                'firstName': 'Test',
                'lastName': 'Buyer',
            },
            'shippingAddress': {
                'address1': '456 Oak Ave',
                'address2': '',
                'city': 'Los Angeles',
                'province': 'California',
                'provinceCode': 'CA',
                'country': 'United States',
                'countryCodeV2': 'US',
                'zip': '90001',
                'phone': '',
                'firstName': 'Test',
                'lastName': 'Buyer',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/1',
                        'title': 'Test Widget',
                        'quantity': 2,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/200',
                            'sku': 'WIDGET-001',
                            'product': {'id': 'gid://shopify/Product/100'},
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {'amount': '29.99', 'currencyCode': 'USD'},
                        },
                        'discountAllocations': [],
                        'taxLines': [],
                    }
                }]
            },
            'shippingLines': {'edges': []},
        }

    def test_import_new_order(self):
        """Should create a sale.order from Shopify order data."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        self.assertTrue(binding)
        self.assertEqual(binding.shopify_order_name, '#1001')
        self.assertEqual(binding.shopify_financial_status, 'paid')
        self.assertTrue(binding.odoo_id)

        order = binding.odoo_id
        self.assertEqual(order.shopify_order_name, '#1001')
        # Order should be confirmed since financial status is PAID
        self.assertIn(order.state, ('sale', 'done'))

    def test_import_order_creates_lines(self):
        """Imported order should have the correct order lines."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        order = binding.odoo_id
        self.assertEqual(len(order.order_line), 1)
        line = order.order_line[0]
        self.assertEqual(line.product_id.id, self.product.id)
        self.assertEqual(line.product_uom_qty, 2)
        self.assertEqual(line.price_unit, 29.99)

    def test_import_order_resolves_customer(self):
        """Should create customer if not found."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        partner = binding.odoo_id.partner_id
        self.assertTrue(partner)
        self.assertEqual(partner.email, 'buyer@example.com')

    def test_import_order_updates_existing(self):
        """Should update financial status on re-import."""
        from ..sync.order_sync import OrderImporter

        # First import
        node = self._make_order_node(financial_status='PENDING')

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        self.assertEqual(binding.shopify_financial_status, 'pending')

        # Second import with updated status
        node2 = self._make_order_node(financial_status='PAID')

        importer._import_one(node2, existing_binding=binding)
        self.assertEqual(binding.shopify_financial_status, 'paid')
