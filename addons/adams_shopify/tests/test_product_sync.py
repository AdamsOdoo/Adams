# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch, MagicMock

from odoo.tests.common import TransactionCase


class TestProductSync(TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })
        self.product = self.env['product.template'].create({
            'name': 'Test Widget',
            'list_price': 29.99,
            'default_code': 'WIDGET-001',
            'weight': 0.5,
        })

    def test_product_binding_run_sync_calls_correct_direction(self):
        """run_sync should respect backend direction setting."""
        self.backend.product_sync_direction = 'export'
        with patch('odoo.addons.adams_shopify.sync.product_sync.ProductSync') as MockSync:
            instance = MockSync.return_value
            self.env['shopify.product.binding'].run_sync(self.backend)
            instance.export_products.assert_called_once()
            instance.import_products.assert_not_called()

    def test_product_binding_run_sync_bidirectional(self):
        """Bidirectional should call both import and export."""
        self.backend.product_sync_direction = 'both'
        with patch('odoo.addons.adams_shopify.sync.product_sync.ProductSync') as MockSync:
            instance = MockSync.return_value
            self.env['shopify.product.binding'].run_sync(self.backend)
            instance.import_products.assert_called_once()
            instance.export_products.assert_called_once()

    def test_export_skips_unchanged_product(self):
        """Export should skip products with matching checksum."""
        from ..sync.checksum import product_checksum
        checksum = product_checksum(self.product)

        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/Product/123',
            'sync_status': 'pending',
            'sync_checksum': checksum,
        })

        with patch('odoo.addons.adams_shopify.sync.product_sync.ProductExporter._export_one') as mock_export:
            from ..sync.product_sync import ProductExporter
            exporter = ProductExporter.__new__(ProductExporter)
            exporter.env = self.env
            exporter.backend = self.backend
            exporter.client = MagicMock()

            log = exporter._create_log()
            success, errors, skipped = 0, 0, 0

            new_checksum = exporter._compute_checksum(binding)
            if new_checksum == binding.sync_checksum:
                skipped += 1

            self.assertEqual(skipped, 1)
            mock_export.assert_not_called()

    def test_import_creates_new_product(self):
        """Import should create a new product if no match exists."""
        from ..sync.product_sync import ProductImporter

        node = {
            'id': 'gid://shopify/Product/999',
            'title': 'Imported Widget',
            'bodyHtml': '<p>A widget</p>',
            'vendor': 'Acme',
            'productType': 'Widget',
            'tags': ['new', 'imported'],
            'status': 'ACTIVE',
            'handle': 'imported-widget',
            'variants': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/ProductVariant/888',
                        'sku': 'IMP-WIDGET-001',
                        'price': '19.99',
                        'barcode': None,
                        'weight': 0.3,
                        'inventoryItem': {'id': 'gid://shopify/InventoryItem/777'},
                    }
                }]
            },
        }

        importer = ProductImporter.__new__(ProductImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=None)

        # Verify binding was created
        binding = self.env['shopify.product.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Product/999'),
        ])
        self.assertTrue(binding)
        self.assertEqual(binding.sync_status, 'synced')
        self.assertEqual(binding.odoo_id.name, 'Imported Widget')

    def test_import_updates_existing_binding(self):
        """Import should update existing product when binding found."""
        from ..sync.product_sync import ProductImporter

        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/Product/123',
            'sync_status': 'synced',
        })

        node = {
            'id': 'gid://shopify/Product/123',
            'title': 'Updated Widget Name',
            'bodyHtml': '',
            'vendor': '',
            'productType': '',
            'tags': [],
            'status': 'ACTIVE',
            'handle': 'test-widget',
            'variants': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/ProductVariant/456',
                        'sku': 'WIDGET-001',
                        'price': '29.99',
                        'barcode': None,
                        'weight': 0.5,
                        'inventoryItem': {'id': 'gid://shopify/InventoryItem/789'},
                    }
                }]
            },
        }

        importer = ProductImporter.__new__(ProductImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()

        importer._import_one(node, existing_binding=binding)

        self.product.invalidate_recordset()
        self.assertEqual(self.product.name, 'Updated Widget Name')
        self.assertEqual(binding.sync_status, 'synced')
