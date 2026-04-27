# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Shared test setup for Shopify Simulator tests.

SimulatorTestCase provides:
- A shopify.backend in simulator mode
- A sim.shopify.config linked to the backend
- A primary location
- Helper methods for seeding products, customers, orders
- A method to call the simulator endpoint directly via the controller
"""
import json
import logging

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)


class SimulatorTestCase(TransactionCase):
    """Base class for all Shopify Simulator tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_simulator()

    @classmethod
    def _setup_simulator(cls):
        """Create backend + simulator config + primary location."""
        cls.backend = cls.env['shopify.backend'].create({
            'name': 'Simulator Test Store',
            'shop_url': 'http://localhost:8069/shopify-sim/0',
            'access_token': 'shpat_sim_testtoken123',
            'company_id': cls.env.company.id,
            'use_simulator': True,
        })
        cls.sim_config = cls.env['sim.shopify.config'].create({
            'backend_id': cls.backend.id,
            'shop_name': 'Test Simulator Store',
            'shop_email': 'admin@test-sim.myshopify.com',
            'myshopify_domain': 'test-sim.myshopify.com',
            'access_token': 'shpat_sim_testtoken123',
            'currency_code': 'USD',
        })
        # Update backend with correct simulator URL
        cls.backend.write({
            'shop_url': f'http://localhost:8069/shopify-sim/{cls.sim_config.id}',
            'sim_config_id': cls.sim_config.id,
        })
        # Create a primary location
        cls.primary_location = cls.env['sim.shopify.location'].create({
            'config_id': cls.sim_config.id,
            'name': 'Main Warehouse',
            'address1': '123 Test Street',
            'city': 'Testville',
            'country_code': 'US',
            'is_active': True,
            'is_primary': True,
        })

    # ------------------------------------------------------------------
    # Seed helpers
    # ------------------------------------------------------------------

    @classmethod
    def _seed_product(cls, title='Test Product', **kwargs):
        """Create a simulated product with a default variant."""
        vals = {
            'config_id': cls.sim_config.id,
            'title': title,
            **kwargs,
        }
        return cls.env['sim.shopify.product'].create(vals)

    @classmethod
    def _seed_product_with_variants(cls, title='Multi-Variant Product',
                                     variant_data=None, **kwargs):
        """Create a product then replace auto-variant with custom ones."""
        product = cls._seed_product(title=title, **kwargs)
        if variant_data:
            product.variant_ids.unlink()
            for v in variant_data:
                v['product_id'] = product.id
                cls.env['sim.shopify.variant'].create(v)
        return product

    @classmethod
    def _seed_customer(cls, first_name='Test', last_name='Customer', **kwargs):
        """Create a simulated customer."""
        vals = {
            'config_id': cls.sim_config.id,
            'first_name': first_name,
            'last_name': last_name,
            **kwargs,
        }
        return cls.env['sim.shopify.customer'].create(vals)

    @classmethod
    def _seed_order(cls, name='#1001', customer=None, lines=None,
                    shipping_lines=None, create_fulfillment_orders=True,
                    **kwargs):
        """Create a simulated order with optional line items.

        Args:
            create_fulfillment_orders: If True (default), automatically create
                fulfillment orders for the order lines (matching Shopify behavior).
        """
        vals = {
            'config_id': cls.sim_config.id,
            'name': name,
            **kwargs,
        }
        if customer:
            vals['customer_id'] = customer.id
        order = cls.env['sim.shopify.order'].create(vals)
        if lines:
            for line in lines:
                line['order_id'] = order.id
                cls.env['sim.shopify.order.line'].create(line)
        if shipping_lines:
            for sl in shipping_lines:
                sl['order_id'] = order.id
                cls.env['sim.shopify.shipping.line'].create(sl)
        if create_fulfillment_orders and lines:
            order.action_create_fulfillment_orders()
        return order

    @classmethod
    def _seed_inventory(cls, variant, location=None, available=10):
        """Create an inventory level for a variant at a location."""
        location = location or cls.primary_location
        return cls.env['sim.shopify.inventory.level'].create({
            'config_id': cls.sim_config.id,
            'variant_id': variant.id,
            'location_id': location.id,
            'available': available,
        })

    # ------------------------------------------------------------------
    # Handler call helpers (bypass HTTP, call handler functions directly)
    # ------------------------------------------------------------------

    def _call_handler(self, handler_func, variables=None):
        """Call a handler function directly with the test env and config."""
        return handler_func(self.env, self.sim_config, variables or {})

    def _call_query(self, handler_key, variables=None):
        """Call a query handler by its dispatch key."""
        from ..controllers.graphql_endpoint import _QUERY_HANDLERS
        handler = _QUERY_HANDLERS.get(handler_key)
        self.assertIsNotNone(handler, f'No handler for key: {handler_key}')
        return handler(self.env, self.sim_config, variables or {})

    def _call_mutation(self, handler_key, variables=None):
        """Call a mutation handler by its dispatch key."""
        from ..controllers.graphql_endpoint import _MUTATION_HANDLERS
        handler = _MUTATION_HANDLERS.get(handler_key)
        self.assertIsNotNone(handler, f'No mutation handler for key: {handler_key}')
        return handler(self.env, self.sim_config, variables or {})
