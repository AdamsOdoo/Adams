from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class TestInventorySync(TransactionCase):

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
            'shopify_location_id': 'gid://shopify/Location/1',
            'inventory_quantity_field': 'free_qty',
        })
        self.product = self.env['product.product'].create({
            'name': 'Inventory Widget',
            'list_price': 10.0,
            'default_code': 'INV-001',
        })
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
            'shopify_inventory_item_id': 'gid://shopify/InventoryItem/300',
            'sync_status': 'synced',
        })

    def test_export_skips_without_location(self):
        """Should skip export if no Shopify location is configured."""
        from ..sync.inventory_sync import InventorySync

        self.backend.shopify_location_id = False
        syncer = InventorySync.__new__(InventorySync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        success, errors, skipped = syncer.export_inventory(self.backend)
        self.assertEqual(success, 0)
        self.assertEqual(errors, 0)
        self.assertEqual(skipped, 0)
        syncer.client.execute_mutation.assert_not_called()

    def test_export_skips_unchanged_quantity(self):
        """Should skip if last_pushed_qty matches current qty."""
        from ..sync.inventory_sync import InventorySync

        # Create an inventory binding with last_pushed_qty = 0 (matches stock)
        self.env['shopify.inventory.binding'].create({
            'backend_id': self.backend.id,
            'variant_binding_id': self.variant_binding.id,
            'shopify_inventory_item_id': 'gid://shopify/InventoryItem/300',
            'shopify_location_id': 'gid://shopify/Location/1',
            'last_pushed_qty': 0,
            'shopify_id': 'gid://shopify/InventoryItem/300:gid://shopify/Location/1',
            'sync_status': 'synced',
        })

        syncer = InventorySync.__new__(InventorySync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        success, errors, skipped = syncer.export_inventory(self.backend)
        self.assertEqual(skipped, 1)
        syncer.client.execute_mutation.assert_not_called()

    def test_export_pushes_changed_quantity(self):
        """Should push to Shopify when quantity changes."""
        from ..sync.inventory_sync import InventorySync

        # Create inventory binding with old qty
        self.env['shopify.inventory.binding'].create({
            'backend_id': self.backend.id,
            'variant_binding_id': self.variant_binding.id,
            'shopify_inventory_item_id': 'gid://shopify/InventoryItem/300',
            'shopify_location_id': 'gid://shopify/Location/1',
            'last_pushed_qty': 99,  # Different from actual (0)
            'shopify_id': 'gid://shopify/InventoryItem/300:gid://shopify/Location/1',
            'sync_status': 'synced',
        })

        syncer = InventorySync.__new__(InventorySync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        success, errors, skipped = syncer.export_inventory(self.backend)
        self.assertEqual(success, 1)
        self.assertEqual(skipped, 0)
        syncer.client.execute_mutation.assert_called_once()

    def test_inventory_binding_creation(self):
        """Should create inventory binding on first push."""
        self.assertFalse(
            self.env['shopify.inventory.binding'].search([
                ('backend_id', '=', self.backend.id),
                ('variant_binding_id', '=', self.variant_binding.id),
            ])
        )

        from ..sync.inventory_sync import InventorySync

        syncer = InventorySync.__new__(InventorySync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()

        syncer.export_inventory(self.backend)

        inv_binding = self.env['shopify.inventory.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('variant_binding_id', '=', self.variant_binding.id),
        ])
        self.assertTrue(inv_binding)
        self.assertEqual(inv_binding.shopify_location_id, 'gid://shopify/Location/1')

    def test_export_handles_api_error(self):
        """Should count errors when Shopify API call fails."""
        from ..sync.inventory_sync import InventorySync

        syncer = InventorySync.__new__(InventorySync)
        syncer.env = self.env
        syncer.backend = self.backend
        syncer.client = MagicMock()
        syncer.client.execute_mutation.side_effect = Exception("API error")

        success, errors, skipped = syncer.export_inventory(self.backend)
        self.assertEqual(success, 0)
        self.assertGreater(errors, 0)
