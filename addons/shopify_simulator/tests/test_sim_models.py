# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for simulator models: GID generation, auto-defaults, GraphQL node shape.
"""
from odoo.tests.common import TransactionCase
from .common import SimulatorTestCase
from odoo.tools import mute_logger


class TestSimConfig(SimulatorTestCase):
    """Test sim.shopify.config model."""

    def test_config_created(self):
        """Config should be created with valid defaults."""
        self.assertTrue(self.sim_config.id)
        self.assertEqual(self.sim_config.shop_name, 'Test Simulator Store')
        self.assertEqual(self.sim_config.error_mode, 'none')
        self.assertEqual(self.sim_config.rate_limit_bucket_size, 1000.0)

    def test_next_gid_generation(self):
        """GID generation should be sequential and thread-safe."""
        gid1 = self.sim_config._next_gid('Product')
        gid2 = self.sim_config._next_gid('Product')
        self.assertTrue(gid1.startswith('gid://shopify/Product/'))
        self.assertTrue(gid2.startswith('gid://shopify/Product/'))
        # IDs should be sequential
        id1 = int(gid1.split('/')[-1])
        id2 = int(gid2.split('/')[-1])
        self.assertEqual(id2, id1 + 1)

    def test_next_gid_different_types(self):
        """GIDs for different resource types should use the same counter."""
        gid1 = self.sim_config._next_gid('Product')
        gid2 = self.sim_config._next_gid('Customer')
        id1 = int(gid1.split('/')[-1])
        id2 = int(gid2.split('/')[-1])
        self.assertEqual(id2, id1 + 1)
        self.assertIn('/Product/', gid1)
        self.assertIn('/Customer/', gid2)

    def test_build_extensions(self):
        """Extensions block should have correct Shopify cost structure."""
        ext = self.sim_config._build_extensions(10)
        self.assertIn('cost', ext)
        cost = ext['cost']
        self.assertEqual(cost['requestedQueryCost'], 10)
        self.assertEqual(cost['actualQueryCost'], 8.0)  # 10 * 0.8
        self.assertIn('throttleStatus', cost)
        self.assertEqual(
            cost['throttleStatus']['maximumAvailable'],
            self.sim_config.rate_limit_bucket_size,
        )

    def test_build_extensions_decreases_budget(self):
        """Budget should decrease after each call."""
        initial = self.sim_config.rate_limit_available
        self.sim_config._build_extensions(100)
        self.sim_config.invalidate_recordset()
        self.assertLess(self.sim_config.rate_limit_available, initial)

    def test_reset_rate_limit(self):
        """Reset should restore full budget."""
        self.sim_config._build_extensions(100)
        self.sim_config.action_reset_rate_limit()
        self.sim_config.invalidate_recordset()
        self.assertEqual(
            self.sim_config.rate_limit_available,
            self.sim_config.rate_limit_bucket_size,
        )


class TestSimBackendInherit(SimulatorTestCase):
    """Test shopify.backend simulator mode integration."""

    def test_use_simulator_flag(self):
        """Backend should have use_simulator=True."""
        self.assertTrue(self.backend.use_simulator)
        self.assertTrue(self.backend.sim_config_id)

    def test_make_api_client_returns_simulator(self):
        """_make_api_client() should return SimulatorClient in sim mode."""
        from ..lib.simulator_client import SimulatorClient
        client = self.backend._make_api_client()
        self.assertIsInstance(client, SimulatorClient)

    def test_make_api_client_normal_backend(self):
        """A non-simulator backend should return regular ShopifyClient."""
        from odoo.addons.shopify_connector_pro.shopify_api.client import ShopifyClient
        normal_backend = self.env['shopify.backend'].create({
            'name': 'Normal Store',
            'shop_url': 'normal-store.myshopify.com',
            'access_token': 'shpat_normaltoken12345',
            'company_id': self.env.company.id,
        })
        client = normal_backend._make_api_client()
        self.assertIsInstance(client, ShopifyClient)

    def test_action_create_simulator(self):
        """action_create_simulator should set up config and link it."""
        new_backend = self.env['shopify.backend'].create({
            'name': 'New Store For Sim',
            'shop_url': 'new-store.myshopify.com',
            'access_token': 'shpat_newstoretoken123',
            'company_id': self.env.company.id,
        })
        result = new_backend.action_create_simulator()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertTrue(new_backend.use_simulator)
        self.assertTrue(new_backend.sim_config_id)


class TestSimProduct(SimulatorTestCase):
    """Test sim.shopify.product model and GraphQL shape."""

    def test_auto_gid_on_create(self):
        """Product should get a GID automatically."""
        product = self._seed_product('GID Test')
        self.assertTrue(product.shopify_gid)
        self.assertIn('gid://shopify/Product/', product.shopify_gid)

    def test_auto_handle_from_title(self):
        """Handle should be auto-generated from title."""
        product = self._seed_product('My Cool Product')
        self.assertEqual(product.handle, 'my-cool-product')

    def test_auto_default_variant(self):
        """New product should auto-create a default variant."""
        product = self._seed_product('Variant Test')
        self.assertEqual(len(product.variant_ids), 1)
        self.assertEqual(product.variant_ids.title, 'Default Title')
        self.assertTrue(product.variant_ids.shopify_gid)
        self.assertTrue(product.variant_ids.inventory_item_gid)

    def test_graphql_node_shape(self):
        """_to_graphql_node() should return correct Shopify response shape."""
        product = self._seed_product('Shape Test', tags='tag1,tag2')
        node = product._to_graphql_node()
        self.assertEqual(node['id'], product.shopify_gid)
        self.assertEqual(node['title'], 'Shape Test')
        self.assertEqual(node['tags'], ['tag1', 'tag2'])
        self.assertEqual(node['status'], 'ACTIVE')
        self.assertIn('options', node)
        self.assertIn('variants', node)
        self.assertIn('edges', node['variants'])
        self.assertEqual(len(node['variants']['edges']), 1)
        self.assertIn('images', node)
        self.assertTrue(node['createdAt'].endswith('Z'))

    def test_variant_graphql_node_shape(self):
        """Variant node should have correct structure."""
        product = self._seed_product('Variant Shape Test')
        variant = product.variant_ids[0]
        v_node = variant._to_graphql_node()
        self.assertEqual(v_node['id'], variant.shopify_gid)
        self.assertIn('inventoryItem', v_node)
        self.assertEqual(v_node['inventoryItem']['id'], variant.inventory_item_gid)
        self.assertIn('selectedOptions', v_node)
        self.assertIn('product', v_node)
        self.assertEqual(v_node['product']['id'], product.shopify_gid)

    def test_multi_variant_product(self):
        """Product with multiple variants should have all in GraphQL output."""
        product = self._seed_product_with_variants(
            title='T-Shirt',
            variant_data=[
                {'title': 'Small', 'sku': 'TS-S', 'price': '19.99',
                 'option1_name': 'Size', 'option1_value': 'S'},
                {'title': 'Medium', 'sku': 'TS-M', 'price': '19.99',
                 'option1_name': 'Size', 'option1_value': 'M'},
                {'title': 'Large', 'sku': 'TS-L', 'price': '21.99',
                 'option1_name': 'Size', 'option1_value': 'L'},
            ],
        )
        self.assertEqual(len(product.variant_ids), 3)
        node = product._to_graphql_node()
        self.assertEqual(len(node['variants']['edges']), 3)
        # Options should be deduplicated
        self.assertEqual(len(node['options']), 1)
        self.assertEqual(node['options'][0]['name'], 'Size')
        self.assertEqual(len(node['options'][0]['values']), 3)

    def test_unicode_title(self):
        """Product with Arabic/Unicode title should work fine."""
        product = self._seed_product('منتج تجريبي 🎉')
        self.assertEqual(product.title, 'منتج تجريبي 🎉')
        node = product._to_graphql_node()
        self.assertEqual(node['title'], 'منتج تجريبي 🎉')


class TestSimCustomer(SimulatorTestCase):
    """Test sim.shopify.customer model and GraphQL shape."""

    def test_auto_gid_on_create(self):
        """Customer should get a GID automatically."""
        customer = self._seed_customer('Alice', 'Smith')
        self.assertIn('gid://shopify/Customer/', customer.shopify_gid)

    def test_display_name(self):
        """Display name should combine first and last name."""
        customer = self._seed_customer('Alice', 'Smith')
        self.assertEqual(customer.display_name, 'Alice Smith')

    def test_graphql_node_shape(self):
        """_to_graphql_node() should match Shopify customer response shape."""
        customer = self._seed_customer(
            'Alice', 'Smith',
            email='alice@example.com',
            phone='+1234567890',
            address1='100 Main St',
            city='Springfield',
            country_code='US',
            tags='vip,wholesale',
        )
        node = customer._to_graphql_node()
        self.assertEqual(node['id'], customer.shopify_gid)
        self.assertEqual(node['firstName'], 'Alice')
        self.assertEqual(node['lastName'], 'Smith')
        self.assertEqual(node['email'], 'alice@example.com')
        self.assertEqual(node['tags'], ['vip', 'wholesale'])
        self.assertIsNotNone(node['defaultAddress'])
        self.assertEqual(node['defaultAddress']['city'], 'Springfield')
        self.assertEqual(len(node['addresses']), 1)

    def test_customer_without_address(self):
        """Customer with no address should have null defaultAddress."""
        customer = self._seed_customer(
            'Bob', 'NoAddr', email='bob@test.com', country_code=False,
        )
        node = customer._to_graphql_node()
        self.assertIsNone(node['defaultAddress'])
        self.assertEqual(node['addresses'], [])


class TestSimOrder(SimulatorTestCase):
    """Test sim.shopify.order model and GraphQL shape."""

    def test_auto_gid_on_create(self):
        """Order should get a GID automatically."""
        order = self._seed_order('#2001')
        self.assertIn('gid://shopify/Order/', order.shopify_gid)

    def test_order_graphql_node_shape(self):
        """Order node should match Shopify FETCH_ORDERS shape."""
        customer = self._seed_customer('John', 'Doe', email='john@test.com')
        order = self._seed_order(
            name='#1001',
            customer=customer,
            financial_status='PAID',
            fulfillment_status='UNFULFILLED',
            total_price=99.99,
            subtotal_price=89.99,
            total_tax=10.00,
            currency_code='USD',
            ship_first_name='John',
            ship_last_name='Doe',
            ship_address1='456 Oak Ave',
            ship_city='Portland',
            ship_country_code='US',
            lines=[{
                'title': 'Widget',
                'quantity': 2,
                'sku': 'WDG-001',
                'unit_price': 44.995,
            }],
            shipping_lines=[{
                'title': 'Standard Shipping',
                'code': 'standard',
                'price': 5.00,
            }],
        )
        node = order._to_graphql_node()
        # Top-level fields
        self.assertEqual(node['id'], order.shopify_gid)
        self.assertEqual(node['name'], '#1001')
        self.assertEqual(node['displayFinancialStatus'], 'PAID')
        self.assertEqual(node['displayFulfillmentStatus'], 'UNFULFILLED')
        # Money sets
        self.assertIn('totalPriceSet', node)
        self.assertEqual(node['totalPriceSet']['shopMoney']['amount'], '99.99')
        self.assertEqual(node['totalPriceSet']['shopMoney']['currencyCode'], 'USD')
        # Customer
        self.assertIsNotNone(node['customer'])
        self.assertEqual(node['customer']['email'], 'john@test.com')
        # Shipping address
        self.assertIsNotNone(node['shippingAddress'])
        self.assertEqual(node['shippingAddress']['city'], 'Portland')
        # Line items
        self.assertEqual(len(node['lineItems']['edges']), 1)
        line_node = node['lineItems']['edges'][0]['node']
        self.assertEqual(line_node['title'], 'Widget')
        self.assertEqual(line_node['quantity'], 2)
        # Shipping lines (edges/node wrapping, matching real Shopify shape)
        self.assertEqual(len(node['shippingLines']['edges']), 1)
        self.assertEqual(node['shippingLines']['edges'][0]['node']['title'], 'Standard Shipping')


class TestSimLocation(SimulatorTestCase):
    """Test sim.shopify.location model."""

    def test_primary_location_created(self):
        """Primary location should be created during setup."""
        self.assertTrue(self.primary_location.shopify_gid)
        self.assertTrue(self.primary_location.is_primary)

    def test_location_graphql_node_shape(self):
        """Location node should match Shopify shape."""
        node = self.primary_location._to_graphql_node()
        self.assertEqual(node['id'], self.primary_location.shopify_gid)
        self.assertEqual(node['name'], 'Main Warehouse')
        self.assertTrue(node['isPrimary'])
        self.assertTrue(node['isActive'])
        self.assertIn('address', node)
        self.assertEqual(node['address']['countryCode'], 'US')


class TestSimInventory(SimulatorTestCase):
    """Test sim.shopify.inventory.level model."""

    def test_inventory_level_creation(self):
        """Inventory level should link variant, location, and config."""
        product = self._seed_product('Inv Test Product')
        variant = product.variant_ids[0]
        level = self._seed_inventory(variant, available=42)
        self.assertEqual(level.available, 42)
        self.assertEqual(level.variant_id, variant)
        self.assertEqual(level.location_id, self.primary_location)
        self.assertEqual(level.inventory_item_gid, variant.inventory_item_gid)

    @mute_logger('odoo.sql_db')
    def test_unique_variant_location_constraint(self):
        """Cannot create two inventory levels for same variant+location."""
        product = self._seed_product('Uniq Test')
        variant = product.variant_ids[0]
        self._seed_inventory(variant, available=10)
        with self.assertRaises(Exception), self.cr.savepoint():
            self._seed_inventory(variant, available=20)
