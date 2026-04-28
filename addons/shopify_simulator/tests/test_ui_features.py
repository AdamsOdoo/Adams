# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Tests for UI wizard and action features (Step 1-3).

Covers:
- Computed fields on sim.shopify.config (counts, URL)
- Action buttons (seed, reset, rate limit)
- Stat button actions
- Seed Data Wizard (sim.seed.data.wizard)
- Webhook Test Console (sim.webhook.console)
"""
import json
import logging

from .common import SimulatorTestCase

_logger = logging.getLogger(__name__)


class TestConfigComputedFields(SimulatorTestCase):
    """Test computed fields on sim.shopify.config."""

    def test_record_counts_empty(self):
        """All counts should be zero on a fresh config (except primary location)."""
        self.sim_config.invalidate_recordset()
        self.assertEqual(self.sim_config.product_count, 0)
        self.assertEqual(self.sim_config.customer_count, 0)
        self.assertEqual(self.sim_config.order_count, 0)
        self.assertEqual(self.sim_config.fulfillment_count, 0)
        self.assertEqual(self.sim_config.refund_count, 0)
        self.assertEqual(self.sim_config.webhook_count, 0)
        # Primary location is created in setUp
        self.assertEqual(self.sim_config.location_count, 1)

    def test_record_counts_after_seed(self):
        """Counts should reflect seeded data."""
        self._seed_product('Count Product 1')
        self._seed_product('Count Product 2')
        self._seed_customer('Test', 'User')
        self.sim_config.invalidate_recordset()
        self.assertEqual(self.sim_config.product_count, 2)
        self.assertEqual(self.sim_config.customer_count, 1)

    def test_simulator_url(self):
        """Simulator URL should contain the config ID."""
        self.sim_config.invalidate_recordset()
        url = self.sim_config.simulator_url
        self.assertIn(str(self.sim_config.id), url)
        self.assertIn('graphql.json', url)
        self.assertIn('2026-01', url)


class TestConfigActions(SimulatorTestCase):
    """Test action buttons on sim.shopify.config."""

    def test_action_reset_rate_limit(self):
        """Reset rate limit should restore available to bucket size."""
        self.sim_config.write({'rate_limit_available': 100.0})
        result = self.sim_config.action_reset_rate_limit()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.sim_config.invalidate_recordset()
        self.assertEqual(
            self.sim_config.rate_limit_available,
            self.sim_config.rate_limit_bucket_size,
        )

    def test_action_seed_demo_store(self):
        """Seed demo store should create records and return notification."""
        result = self.sim_config.action_seed_demo_store()
        self.assertEqual(result['type'], 'ir.actions.client')
        self.assertEqual(result['tag'], 'display_notification')
        self.assertIn('success', result['params']['type'])
        # Verify records were created
        self.sim_config.invalidate_recordset()
        self.assertGreater(self.sim_config.product_count, 0)
        self.assertGreater(self.sim_config.customer_count, 0)
        self.assertGreater(self.sim_config.order_count, 0)

    def test_action_reset_all_data(self):
        """Reset all data should clear all sim records."""
        # First seed some data
        self._seed_product('Reset Test')
        self._seed_customer('Reset', 'Me')
        self.sim_config.invalidate_recordset()
        self.assertGreater(self.sim_config.product_count, 0)

        # Now reset
        result = self.sim_config.action_reset_all_data()
        self.assertEqual(result['params']['type'], 'warning')
        self.sim_config.invalidate_recordset()
        self.assertEqual(self.sim_config.product_count, 0)
        self.assertEqual(self.sim_config.customer_count, 0)
        self.assertEqual(self.sim_config.next_gid, 1001)

    def test_action_open_seed_wizard(self):
        """Open seed wizard should return act_window for the wizard model."""
        result = self.sim_config.action_open_seed_wizard()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'sim.seed.data.wizard')
        self.assertEqual(result['target'], 'new')
        self.assertEqual(result['context']['default_config_id'], self.sim_config.id)

    def test_action_open_webhook_console(self):
        """Open webhook console should return act_window for the console model."""
        result = self.sim_config.action_open_webhook_console()
        self.assertEqual(result['type'], 'ir.actions.act_window')
        self.assertEqual(result['res_model'], 'sim.webhook.console')
        self.assertEqual(result['target'], 'new')


class TestStatButtons(SimulatorTestCase):
    """Test stat button actions return correct domain and context."""

    def test_stat_button_products(self):
        result = self.sim_config.action_view_products()
        self.assertEqual(result['res_model'], 'sim.shopify.product')
        self.assertEqual(result['domain'], [('config_id', '=', self.sim_config.id)])
        self.assertEqual(result['context']['default_config_id'], self.sim_config.id)

    def test_stat_button_customers(self):
        result = self.sim_config.action_view_customers()
        self.assertEqual(result['res_model'], 'sim.shopify.customer')

    def test_stat_button_orders(self):
        result = self.sim_config.action_view_orders()
        self.assertEqual(result['res_model'], 'sim.shopify.order')

    def test_stat_button_fulfillments(self):
        result = self.sim_config.action_view_fulfillments()
        self.assertEqual(result['res_model'], 'sim.shopify.fulfillment')

    def test_stat_button_refunds(self):
        result = self.sim_config.action_view_refunds()
        self.assertEqual(result['res_model'], 'sim.shopify.refund')

    def test_stat_button_webhooks(self):
        result = self.sim_config.action_view_webhooks()
        self.assertEqual(result['res_model'], 'sim.shopify.webhook.subscription')

    def test_stat_button_locations(self):
        result = self.sim_config.action_view_locations()
        self.assertEqual(result['res_model'], 'sim.shopify.location')

    def test_stat_button_inventory(self):
        result = self.sim_config.action_view_inventory()
        self.assertEqual(result['res_model'], 'sim.shopify.inventory.level')


class TestSeedDataWizard(SimulatorTestCase):
    """Test sim.seed.data.wizard transient model."""

    def _create_wizard(self, **kwargs):
        vals = {
            'config_id': self.sim_config.id,
            **kwargs,
        }
        return self.env['sim.seed.data.wizard'].create(vals)

    def test_wizard_defaults(self):
        """Wizard should have sensible defaults."""
        wiz = self._create_wizard()
        self.assertTrue(wiz.seed_products)
        self.assertTrue(wiz.seed_customers)
        self.assertTrue(wiz.seed_orders)
        self.assertTrue(wiz.seed_locations)
        self.assertTrue(wiz.seed_inventory)
        self.assertEqual(wiz.seed_mode, 'append')
        self.assertFalse(wiz.use_demo_store)

    def test_seed_random_products_only(self):
        """Seeding only products should create products but no customers/orders."""
        wiz = self._create_wizard(
            seed_products=True, product_count=3, variants_per_product=1,
            seed_customers=False, seed_orders=False,
            seed_locations=False, seed_inventory=False,
        )
        result = wiz.action_seed()
        self.assertEqual(result['params']['type'], 'success')
        self.sim_config.invalidate_recordset()
        self.assertEqual(self.sim_config.product_count, 3)
        self.assertEqual(self.sim_config.customer_count, 0)

    def test_seed_multi_variant_products(self):
        """Seeding products with multiple variants should create variants."""
        wiz = self._create_wizard(
            seed_products=True, product_count=2, variants_per_product=3,
            seed_customers=False, seed_orders=False,
            seed_locations=False, seed_inventory=False,
        )
        wiz.action_seed()
        products = self.env['sim.shopify.product'].search([
            ('config_id', '=', self.sim_config.id),
        ])
        self.assertEqual(len(products), 2)
        for prod in products:
            self.assertEqual(len(prod.variant_ids), 3)

    def test_seed_demo_store_mode(self):
        """Using demo store mode should call the curated fixture."""
        wiz = self._create_wizard(use_demo_store=True)
        result = wiz.action_seed()
        self.assertEqual(result['params']['type'], 'success')
        self.sim_config.invalidate_recordset()
        # Demo store creates 6 products, 3 customers, 3 orders
        self.assertEqual(self.sim_config.product_count, 6)
        self.assertEqual(self.sim_config.customer_count, 3)

    def test_seed_replace_mode(self):
        """Replace mode should clear existing data before seeding."""
        # Pre-seed some data
        self._seed_product('Old Product')
        self.sim_config.invalidate_recordset()
        self.assertEqual(self.sim_config.product_count, 1)

        wiz = self._create_wizard(
            seed_mode='replace',
            seed_products=True, product_count=2,
            seed_customers=False, seed_orders=False,
            seed_locations=False, seed_inventory=False,
        )
        wiz.action_seed()
        self.sim_config.invalidate_recordset()
        # Old product should be gone, only new ones remain
        self.assertEqual(self.sim_config.product_count, 2)

    def test_seed_with_orders(self):
        """Seeding with orders requires products and customers."""
        wiz = self._create_wizard(
            seed_products=True, product_count=2,
            seed_customers=True, customer_count=2,
            seed_orders=True, order_count=3,
            seed_locations=True, location_count=1,
            seed_inventory=True,
        )
        result = wiz.action_seed()
        self.assertEqual(result['params']['type'], 'success')
        self.sim_config.invalidate_recordset()
        self.assertGreater(self.sim_config.order_count, 0)

    def test_seed_nothing(self):
        """Disabling all seed options should do nothing."""
        wiz = self._create_wizard(
            seed_products=False, seed_customers=False, seed_orders=False,
            seed_locations=False, seed_inventory=False,
        )
        result = wiz.action_seed()
        self.assertIn('Nothing', result['params']['message'])


class TestWebhookConsole(SimulatorTestCase):
    """Test sim.webhook.console transient model."""

    def _create_console(self, **kwargs):
        vals = {
            'config_id': self.sim_config.id,
            **kwargs,
        }
        return self.env['sim.webhook.console'].create(vals)

    def test_console_defaults(self):
        """Console should default to products/update topic."""
        console = self._create_console()
        self.assertEqual(console.topic, 'products/update')

    def test_build_product_payload(self):
        """Product payload should contain correct fields."""
        product = self._seed_product('Payload Test', vendor='TestVendor')
        console = self._create_console(topic='products/create')
        payload = console._build_product_payload(product)
        self.assertEqual(payload['title'], 'Payload Test')
        self.assertEqual(payload['vendor'], 'TestVendor')
        self.assertIn('variants', payload)
        self.assertIn('admin_graphql_api_id', payload)
        self.assertEqual(payload['admin_graphql_api_id'], product.shopify_gid)

    def test_build_order_payload(self):
        """Order payload should contain line items and customer."""
        customer = self._seed_customer('Console', 'Test')
        product = self._seed_product('Order Payload Test')
        variant = product.variant_ids[0]
        order = self._seed_order(
            name='#9001', customer=customer,
            lines=[{
                'title': 'Test Item',
                'quantity': 2,
                'sku': 'TST-001',
                'unit_price': 25.0,
                'variant_gid': variant.shopify_gid,
                'product_gid': product.shopify_gid,
            }],
            financial_status='PAID',
        )
        console = self._create_console(topic='orders/create')
        payload = console._build_order_payload(order)
        self.assertEqual(payload['name'], '#9001')
        self.assertEqual(len(payload['line_items']), 1)
        self.assertEqual(payload['customer']['first_name'], 'Console')
        self.assertIsNotNone(payload['admin_graphql_api_id'])

    def test_build_customer_payload(self):
        """Customer payload should contain address data."""
        customer = self._seed_customer(
            'Webhook', 'Customer',
            email='webhook@test.com',
            address1='456 Test Ave',
            city='Testburg',
            country_code='US',
        )
        console = self._create_console(topic='customers/create')
        payload = console._build_customer_payload(customer)
        self.assertEqual(payload['first_name'], 'Webhook')
        self.assertEqual(payload['email'], 'webhook@test.com')
        self.assertEqual(len(payload['addresses']), 1)
        self.assertEqual(payload['addresses'][0]['city'], 'Testburg')

    def test_gid_to_id(self):
        """GID parser should extract numeric ID."""
        self.assertEqual(
            self.env['sim.webhook.console']._gid_to_id(
                'gid://shopify/Product/12345',
            ),
            12345,
        )
        self.assertEqual(
            self.env['sim.webhook.console']._gid_to_id(None),
            0,
        )

    def test_fire_webhook_empty_payload(self):
        """Firing with empty payload should raise UserError."""
        from odoo.exceptions import UserError
        console = self._create_console(payload_json='')
        with self.assertRaises(UserError):
            console.action_fire_webhook()
