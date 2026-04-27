# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for product query and mutation handlers.
"""
from .common import SimulatorTestCase
from ..handlers import product_handler


class TestFetchProducts(SimulatorTestCase):
    """Test handle_fetch_products handler."""

    def test_empty_store(self):
        """Empty store should return empty edges."""
        result = self._call_handler(product_handler.handle_fetch_products)
        self.assertIn('products', result)
        self.assertEqual(result['products']['edges'], [])
        self.assertFalse(result['products']['pageInfo']['hasNextPage'])

    def test_fetch_products_returns_all(self):
        """Should return all products in the store."""
        self._seed_product('Product A')
        self._seed_product('Product B')
        self._seed_product('Product C')
        result = self._call_handler(
            product_handler.handle_fetch_products,
            {'first': 50},
        )
        edges = result['products']['edges']
        self.assertEqual(len(edges), 3)
        titles = [e['node']['title'] for e in edges]
        self.assertIn('Product A', titles)
        self.assertIn('Product B', titles)
        self.assertIn('Product C', titles)

    def test_fetch_products_node_shape(self):
        """Each product node should have expected Shopify fields."""
        self._seed_product('Shape Product', vendor='TestVendor', tags='a,b')
        result = self._call_handler(
            product_handler.handle_fetch_products, {'first': 10},
        )
        node = result['products']['edges'][0]['node']
        self.assertIn('id', node)
        self.assertIn('title', node)
        self.assertIn('vendor', node)
        self.assertIn('tags', node)
        self.assertIn('variants', node)
        self.assertIn('options', node)
        self.assertEqual(node['vendor'], 'TestVendor')
        self.assertEqual(node['tags'], ['a', 'b'])

    def test_fetch_products_with_cursor(self):
        """Pagination should work with after cursor."""
        for i in range(5):
            self._seed_product(f'Prod-{i}')
        # Fetch first 2
        result1 = self._call_handler(
            product_handler.handle_fetch_products, {'first': 2},
        )
        self.assertEqual(len(result1['products']['edges']), 2)
        self.assertTrue(result1['products']['pageInfo']['hasNextPage'])
        end_cursor = result1['products']['pageInfo']['endCursor']
        # Fetch next 2
        result2 = self._call_handler(
            product_handler.handle_fetch_products,
            {'first': 2, 'after': end_cursor},
        )
        self.assertEqual(len(result2['products']['edges']), 2)
        # IDs should not overlap
        ids1 = {e['node']['id'] for e in result1['products']['edges']}
        ids2 = {e['node']['id'] for e in result2['products']['edges']}
        self.assertTrue(ids1.isdisjoint(ids2))


class TestFetchSingleProduct(SimulatorTestCase):
    """Test handle_fetch_single_product handler."""

    def test_existing_product(self):
        """Should return product node by GID."""
        product = self._seed_product('Single Fetch Test')
        result = self._call_handler(
            product_handler.handle_fetch_single_product,
            {'id': product.shopify_gid},
        )
        self.assertIn('product', result)
        self.assertEqual(result['product']['id'], product.shopify_gid)
        self.assertEqual(result['product']['title'], 'Single Fetch Test')

    def test_nonexistent_product(self):
        """Should return null for unknown GID."""
        result = self._call_handler(
            product_handler.handle_fetch_single_product,
            {'id': 'gid://shopify/Product/999999'},
        )
        self.assertIsNone(result['product'])


class TestProductSet(SimulatorTestCase):
    """Test handle_product_set mutation handler."""

    def test_create_simple_product(self):
        """Should create a product with basic fields."""
        result = self._call_handler(
            product_handler.handle_product_set,
            {'input': {
                'title': 'New Via Mutation',
                'vendor': 'MutationVendor',
                'productType': 'Widget',
                'tags': ['sale', 'new'],
                'status': 'ACTIVE',
            }},
        )
        self.assertIn('productSet', result)
        self.assertEqual(result['productSet']['userErrors'], [])
        product_node = result['productSet']['product']
        self.assertIsNotNone(product_node['id'])
        self.assertEqual(product_node['title'], 'New Via Mutation')
        self.assertEqual(product_node['vendor'], 'MutationVendor')

    def test_create_product_with_variants(self):
        """Should create product with explicit variants."""
        result = self._call_handler(
            product_handler.handle_product_set,
            {'input': {
                'title': 'Multi-V Product',
                'variants': [
                    {'sku': 'MV-S', 'price': '10.00',
                     'optionValues': [{'optionName': 'Size', 'name': 'Small'}]},
                    {'sku': 'MV-M', 'price': '12.00',
                     'optionValues': [{'optionName': 'Size', 'name': 'Medium'}]},
                ],
            }},
        )
        product_node = result['productSet']['product']
        variants = product_node['variants']['edges']
        self.assertEqual(len(variants), 2)
        skus = {v['node']['sku'] for v in variants}
        self.assertEqual(skus, {'MV-S', 'MV-M'})


class TestProductUpdate(SimulatorTestCase):
    """Test handle_product_update mutation handler."""

    def test_update_existing_product(self):
        """Should update product fields."""
        product = self._seed_product('Before Update')
        result = self._call_handler(
            product_handler.handle_product_update,
            {'input': {
                'id': product.shopify_gid,
                'title': 'After Update',
                'tags': ['updated'],
            }},
        )
        self.assertEqual(result['productUpdate']['userErrors'], [])
        self.assertEqual(result['productUpdate']['product']['title'], 'After Update')
        # Verify in DB
        product.invalidate_recordset()
        self.assertEqual(product.title, 'After Update')

    def test_update_nonexistent_product(self):
        """Should return userErrors for missing product."""
        result = self._call_handler(
            product_handler.handle_product_update,
            {'input': {'id': 'gid://shopify/Product/999999', 'title': 'No'}},
        )
        self.assertTrue(result['productUpdate']['userErrors'])
        self.assertIsNone(result['productUpdate']['product'])

    def test_update_status(self):
        """Should update product status."""
        product = self._seed_product('Status Test', status='ACTIVE')
        self._call_handler(
            product_handler.handle_product_update,
            {'input': {'id': product.shopify_gid, 'status': 'ARCHIVED'}},
        )
        product.invalidate_recordset()
        self.assertEqual(product.status, 'ARCHIVED')


class TestVariantBulkUpdate(SimulatorTestCase):
    """Test handle_variant_bulk_update mutation handler."""

    def test_bulk_update_variant_sku_price(self):
        """Should update SKU and price on variants."""
        product = self._seed_product_with_variants(
            title='Bulk Update Test',
            variant_data=[
                {'title': 'V1', 'sku': 'OLD-1', 'price': '10.00'},
                {'title': 'V2', 'sku': 'OLD-2', 'price': '20.00'},
            ],
        )
        v1, v2 = product.variant_ids.sorted('id')
        result = self._call_handler(
            product_handler.handle_variant_bulk_update,
            {
                'productId': product.shopify_gid,
                'variants': [
                    {'id': v1.shopify_gid, 'sku': 'NEW-1', 'price': '15.00'},
                    {'id': v2.shopify_gid, 'sku': 'NEW-2'},
                ],
            },
        )
        response = result['productVariantsBulkUpdate']
        self.assertEqual(response['userErrors'], [])
        self.assertEqual(len(response['productVariants']), 2)
        # Verify DB
        v1.invalidate_recordset()
        v2.invalidate_recordset()
        self.assertEqual(v1.sku, 'NEW-1')
        self.assertEqual(v1.price, '15.00')
        self.assertEqual(v2.sku, 'NEW-2')

    def test_bulk_update_nonexistent_product(self):
        """Should return userErrors for missing product."""
        result = self._call_handler(
            product_handler.handle_variant_bulk_update,
            {'productId': 'gid://shopify/Product/999', 'variants': []},
        )
        self.assertTrue(result['productVariantsBulkUpdate']['userErrors'])
