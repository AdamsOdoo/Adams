from odoo.tests.common import TransactionCase

from ..sync.checksum import (
    compute_checksum,
    product_checksum,
    shopify_product_checksum,
    shopify_customer_checksum,
)


class TestChecksum(TransactionCase):

    def test_compute_checksum_deterministic(self):
        """Same data should always produce the same checksum."""
        data = {'name': 'Test', 'price': 10.5, 'active': True}
        c1 = compute_checksum(data)
        c2 = compute_checksum(data)
        self.assertEqual(c1, c2)

    def test_compute_checksum_key_order_independent(self):
        """Dict key order should not affect the checksum."""
        data1 = {'b': 2, 'a': 1}
        data2 = {'a': 1, 'b': 2}
        self.assertEqual(compute_checksum(data1), compute_checksum(data2))

    def test_compute_checksum_different_data(self):
        """Different data should produce different checksums."""
        c1 = compute_checksum({'name': 'A'})
        c2 = compute_checksum({'name': 'B'})
        self.assertNotEqual(c1, c2)

    def test_compute_checksum_length(self):
        """Checksum should be 32 characters (truncated SHA-256)."""
        c = compute_checksum({'test': True})
        self.assertEqual(len(c), 32)

    def test_product_checksum(self):
        """Product checksum should work on product.template records."""
        product = self.env['product.template'].create({
            'name': 'Test Product',
            'list_price': 25.0,
            'default_code': 'TEST-001',
            'weight': 1.5,
        })
        c1 = product_checksum(product)
        self.assertEqual(len(c1), 32)

        # Change name → different checksum
        product.name = 'Changed Product'
        c2 = product_checksum(product)
        self.assertNotEqual(c1, c2)

    def test_product_checksum_unchanged(self):
        """Same product state should produce same checksum."""
        product = self.env['product.template'].create({
            'name': 'Stable Product',
            'list_price': 10.0,
        })
        c1 = product_checksum(product)
        c2 = product_checksum(product)
        self.assertEqual(c1, c2)

    def test_shopify_product_checksum(self):
        """Shopify product checksum should work on API data."""
        data = {
            'title': 'Shopify Product',
            'bodyHtml': '<p>Description</p>',
            'vendor': 'Test Vendor',
            'productType': 'Widget',
            'tags': ['tag1', 'tag2'],
            'status': 'ACTIVE',
        }
        c = shopify_product_checksum(data)
        self.assertEqual(len(c), 32)

    def test_shopify_customer_checksum(self):
        """Shopify customer checksum should work on API data."""
        data = {
            'firstName': 'John',
            'lastName': 'Doe',
            'email': 'john@example.com',
            'phone': '+1234567890',
        }
        c = shopify_customer_checksum(data)
        self.assertEqual(len(c), 32)

    def test_shopify_customer_checksum_change(self):
        """Different customer data should produce different checksums."""
        data1 = {'firstName': 'John', 'lastName': 'Doe', 'email': 'john@example.com', 'phone': ''}
        data2 = {'firstName': 'Jane', 'lastName': 'Doe', 'email': 'jane@example.com', 'phone': ''}
        self.assertNotEqual(
            shopify_customer_checksum(data1),
            shopify_customer_checksum(data2),
        )
