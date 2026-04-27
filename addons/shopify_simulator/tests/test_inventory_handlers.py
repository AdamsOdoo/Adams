# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for inventory mutation handlers.
"""
from .common import SimulatorTestCase
from ..handlers import inventory_handler


class TestInventorySetQuantities(SimulatorTestCase):
    """Test handle_inventory_set_quantities handler."""

    def test_set_inventory_creates_level(self):
        """Should create inventory level when none exists."""
        product = self._seed_product('Inv Set Product')
        variant = product.variant_ids[0]
        result = self._call_handler(
            inventory_handler.handle_inventory_set_quantities,
            {'input': {
                'reason': 'correction',
                'quantities': [{
                    'inventoryItemId': variant.inventory_item_gid,
                    'locationId': self.primary_location.shopify_gid,
                    'quantity': 42,
                }],
            }},
        )
        resp = result['inventorySetQuantities']
        self.assertEqual(resp['userErrors'], [])
        self.assertEqual(resp['inventoryAdjustmentGroup']['reason'], 'correction')
        # Verify DB
        level = self.env['sim.shopify.inventory.level'].search([
            ('variant_id', '=', variant.id),
            ('location_id', '=', self.primary_location.id),
        ])
        self.assertEqual(level.available, 42)
        variant.invalidate_recordset()
        self.assertEqual(variant.inventory_quantity, 42)

    def test_set_inventory_updates_existing(self):
        """Should update existing inventory level."""
        product = self._seed_product('Inv Update Product')
        variant = product.variant_ids[0]
        self._seed_inventory(variant, available=10)

        self._call_handler(
            inventory_handler.handle_inventory_set_quantities,
            {'input': {
                'reason': 'correction',
                'quantities': [{
                    'inventoryItemId': variant.inventory_item_gid,
                    'locationId': self.primary_location.shopify_gid,
                    'quantity': 99,
                }],
            }},
        )
        level = self.env['sim.shopify.inventory.level'].search([
            ('variant_id', '=', variant.id),
            ('location_id', '=', self.primary_location.id),
        ])
        self.assertEqual(level.available, 99)

    def test_set_inventory_multiple_items(self):
        """Should handle batch set for multiple items."""
        p1 = self._seed_product('P1')
        p2 = self._seed_product('P2')
        v1 = p1.variant_ids[0]
        v2 = p2.variant_ids[0]

        self._call_handler(
            inventory_handler.handle_inventory_set_quantities,
            {'input': {
                'reason': 'correction',
                'quantities': [
                    {'inventoryItemId': v1.inventory_item_gid,
                     'locationId': self.primary_location.shopify_gid,
                     'quantity': 10},
                    {'inventoryItemId': v2.inventory_item_gid,
                     'locationId': self.primary_location.shopify_gid,
                     'quantity': 20},
                ],
            }},
        )
        level1 = self.env['sim.shopify.inventory.level'].search([
            ('variant_id', '=', v1.id),
        ])
        level2 = self.env['sim.shopify.inventory.level'].search([
            ('variant_id', '=', v2.id),
        ])
        self.assertEqual(level1.available, 10)
        self.assertEqual(level2.available, 20)

    def test_set_inventory_unknown_item_silently_skipped(self):
        """Unknown inventory item IDs should be silently ignored."""
        result = self._call_handler(
            inventory_handler.handle_inventory_set_quantities,
            {'input': {
                'reason': 'correction',
                'quantities': [{
                    'inventoryItemId': 'gid://shopify/InventoryItem/999999',
                    'locationId': self.primary_location.shopify_gid,
                    'quantity': 5,
                }],
            }},
        )
        # Should not error
        self.assertEqual(result['inventorySetQuantities']['userErrors'], [])


class TestInventoryAdjustQuantities(SimulatorTestCase):
    """Test handle_inventory_adjust_quantities handler."""

    def test_adjust_creates_level_from_zero(self):
        """Should create inventory level with delta when none exists."""
        product = self._seed_product('Adj New')
        variant = product.variant_ids[0]
        result = self._call_handler(
            inventory_handler.handle_inventory_adjust_quantities,
            {'input': {
                'reason': 'received',
                'changes': [{
                    'inventoryItemId': variant.inventory_item_gid,
                    'locationId': self.primary_location.shopify_gid,
                    'delta': 15,
                }],
            }},
        )
        resp = result['inventoryAdjustQuantities']
        self.assertEqual(resp['userErrors'], [])
        level = self.env['sim.shopify.inventory.level'].search([
            ('variant_id', '=', variant.id),
        ])
        self.assertEqual(level.available, 15)

    def test_adjust_delta_on_existing(self):
        """Should add delta to existing inventory level."""
        product = self._seed_product('Adj Existing')
        variant = product.variant_ids[0]
        self._seed_inventory(variant, available=50)

        self._call_handler(
            inventory_handler.handle_inventory_adjust_quantities,
            {'input': {
                'reason': 'shrinkage',
                'changes': [{
                    'inventoryItemId': variant.inventory_item_gid,
                    'locationId': self.primary_location.shopify_gid,
                    'delta': -10,
                }],
            }},
        )
        level = self.env['sim.shopify.inventory.level'].search([
            ('variant_id', '=', variant.id),
        ])
        self.assertEqual(level.available, 40)

    def test_adjust_returns_changes(self):
        """Response should include change details."""
        product = self._seed_product('Adj Changes')
        variant = product.variant_ids[0]
        variant.write({'sku': 'ADJ-SKU'})
        self._seed_inventory(variant, available=100)

        result = self._call_handler(
            inventory_handler.handle_inventory_adjust_quantities,
            {'input': {
                'reason': 'correction',
                'changes': [{
                    'inventoryItemId': variant.inventory_item_gid,
                    'locationId': self.primary_location.shopify_gid,
                    'delta': -25,
                }],
            }},
        )
        changes = result['inventoryAdjustQuantities']['inventoryAdjustmentGroup']['changes']
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0]['name'], 'ADJ-SKU')
        self.assertEqual(changes[0]['delta'], -25)
