# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for customer query and mutation handlers.
"""
from .common import SimulatorTestCase
from ..handlers import customer_handler


class TestFetchCustomers(SimulatorTestCase):
    """Test handle_fetch_customers handler."""

    def test_empty_store(self):
        """Empty store should return empty edges."""
        result = self._call_handler(customer_handler.handle_fetch_customers)
        self.assertEqual(result['customers']['edges'], [])

    def test_fetch_customers_returns_all(self):
        """Should return all customers."""
        self._seed_customer('Alice', 'Smith', email='alice@test.com')
        self._seed_customer('Bob', 'Jones', email='bob@test.com')
        result = self._call_handler(
            customer_handler.handle_fetch_customers, {'first': 50},
        )
        edges = result['customers']['edges']
        self.assertEqual(len(edges), 2)
        emails = {e['node']['email'] for e in edges}
        self.assertEqual(emails, {'alice@test.com', 'bob@test.com'})

    def test_customer_node_has_address(self):
        """Customer with address should include defaultAddress in node."""
        self._seed_customer(
            'Carol', 'White',
            email='carol@test.com',
            address1='789 Elm St',
            city='Boston',
            country_code='US',
        )
        result = self._call_handler(
            customer_handler.handle_fetch_customers, {'first': 10},
        )
        node = result['customers']['edges'][0]['node']
        self.assertIsNotNone(node['defaultAddress'])
        self.assertEqual(node['defaultAddress']['city'], 'Boston')


class TestCustomerCreate(SimulatorTestCase):
    """Test handle_customer_create mutation handler."""

    def test_create_customer(self):
        """Should create a customer and return GID."""
        result = self._call_handler(
            customer_handler.handle_customer_create,
            {'input': {
                'firstName': 'New',
                'lastName': 'Customer',
                'email': 'new@example.com',
                'tags': ['vip'],
            }},
        )
        self.assertIn('customerCreate', result)
        self.assertEqual(result['customerCreate']['userErrors'], [])
        self.assertTrue(result['customerCreate']['customer']['id'])
        self.assertEqual(result['customerCreate']['customer']['email'], 'new@example.com')
        # Verify in DB
        customers = self.env['sim.shopify.customer'].search([
            ('config_id', '=', self.sim_config.id),
            ('email', '=', 'new@example.com'),
        ])
        self.assertEqual(len(customers), 1)
        self.assertEqual(customers.first_name, 'New')

    def test_create_customer_with_address(self):
        """Should create customer with address."""
        result = self._call_handler(
            customer_handler.handle_customer_create,
            {'input': {
                'firstName': 'Addr',
                'lastName': 'Test',
                'email': 'addr@test.com',
                'addresses': [{
                    'address1': '123 Main St',
                    'city': 'NYC',
                    'countryCode': 'US',
                    'zip': '10001',
                }],
            }},
        )
        self.assertEqual(result['customerCreate']['userErrors'], [])
        customer = self.env['sim.shopify.customer'].search([
            ('config_id', '=', self.sim_config.id),
            ('email', '=', 'addr@test.com'),
        ])
        self.assertEqual(customer.city, 'NYC')
        self.assertEqual(customer.zip_code, '10001')

    def test_create_customer_arabic_name(self):
        """Unicode names should work correctly."""
        result = self._call_handler(
            customer_handler.handle_customer_create,
            {'input': {
                'firstName': 'أحمد',
                'lastName': 'سعد',
                'email': 'ahmed@test.com',
            }},
        )
        self.assertEqual(result['customerCreate']['userErrors'], [])
        customer = self.env['sim.shopify.customer'].search([
            ('config_id', '=', self.sim_config.id),
            ('email', '=', 'ahmed@test.com'),
        ])
        self.assertEqual(customer.first_name, 'أحمد')


class TestCustomerUpdate(SimulatorTestCase):
    """Test handle_customer_update mutation handler."""

    def test_update_customer(self):
        """Should update customer fields."""
        customer = self._seed_customer('Before', 'Update', email='before@test.com')
        result = self._call_handler(
            customer_handler.handle_customer_update,
            {'input': {
                'id': customer.shopify_gid,
                'firstName': 'After',
                'email': 'after@test.com',
            }},
        )
        resp = result['customerUpdate']
        self.assertEqual(resp['userErrors'], [])
        self.assertEqual(resp['customer']['firstName'], 'After')
        self.assertEqual(resp['customer']['email'], 'after@test.com')
        customer.invalidate_recordset()
        self.assertEqual(customer.first_name, 'After')

    def test_update_nonexistent_customer(self):
        """Should return userErrors for missing customer."""
        result = self._call_handler(
            customer_handler.handle_customer_update,
            {'input': {'id': 'gid://shopify/Customer/999', 'firstName': 'No'}},
        )
        self.assertTrue(result['customerUpdate']['userErrors'])
        self.assertIsNone(result['customerUpdate']['customer'])

    def test_update_tags(self):
        """Should update customer tags."""
        customer = self._seed_customer('Tag', 'Test', tags='old')
        self._call_handler(
            customer_handler.handle_customer_update,
            {'input': {
                'id': customer.shopify_gid,
                'tags': ['new', 'updated'],
            }},
        )
        customer.invalidate_recordset()
        self.assertEqual(customer.tags, 'new,updated')
