# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Tests for the GraphQL endpoint controller dispatch logic.

These tests verify regex-based dispatch, token validation, and response shapes
WITHOUT going through HTTP — we call handlers directly and test the dispatch
tables independently.
"""
import re

from .common import SimulatorTestCase
from ..controllers.graphql_endpoint import (
    QUERY_DISPATCH,
    MUTATION_DISPATCH,
    _QUERY_HANDLERS,
    _MUTATION_HANDLERS,
)


class TestQueryDispatch(SimulatorTestCase):
    """Test that query patterns match the expected handler keys."""

    def _match_query(self, query_text):
        """Return the dispatch key for a query string."""
        for pattern, key in QUERY_DISPATCH:
            if pattern.search(query_text):
                return key
        return None

    def test_shop_query(self):
        self.assertEqual(
            self._match_query('query { shop { name email } }'),
            'shop',
        )

    def test_products_query(self):
        self.assertEqual(
            self._match_query('query FetchProducts($first: Int!) { products(first: $first) { edges { node { id } } } }'),
            'products',
        )

    def test_single_product_query(self):
        self.assertEqual(
            self._match_query('query GetProduct($id: ID!) { product(id: $id) { id title } }'),
            'single_product',
        )

    def test_customers_query(self):
        self.assertEqual(
            self._match_query('query { customers(first: 50) { edges { node { id } } } }'),
            'customers',
        )

    def test_orders_query(self):
        self.assertEqual(
            self._match_query('query { orders(first: 50, query: "updated_at:>2024-01-01") { edges { node { id } } } }'),
            'orders',
        )

    def test_locations_query(self):
        self.assertEqual(
            self._match_query('query { locations(first: 10) { edges { node { id } } } }'),
            'locations',
        )

    def test_collections_query(self):
        self.assertEqual(
            self._match_query('query { collections(first: 50) { edges { node { id } } } }'),
            'collections',
        )

    def test_gift_cards_query(self):
        self.assertEqual(
            self._match_query('query { giftCards(first: 50) { edges { node { id } } } }'),
            'gift_cards',
        )

    def test_webhook_list_query(self):
        self.assertEqual(
            self._match_query('query { webhookSubscriptions(first: 25) { edges { node { id } } } }'),
            'webhook_list',
        )

    def test_payout_query(self):
        self.assertEqual(
            self._match_query('query { shopifyPaymentsAccount { payouts(first: 10) { edges { } } } }'),
            'payouts',
        )

    def test_payout_transactions_before_payouts(self):
        """Payout transactions pattern should match before payouts pattern."""
        query = 'query { shopifyPaymentsAccount { payouts { payout { payoutTransactions { } } } } }'
        # This should match 'payout_transactions' because it appears first in dispatch and has both keywords
        result = self._match_query(query)
        self.assertEqual(result, 'payout_transactions')


class TestMutationDispatch(SimulatorTestCase):
    """Test that mutation patterns match the expected handler keys."""

    def _match_mutation(self, query_text):
        """Return the dispatch key for a mutation string."""
        for pattern, key in MUTATION_DISPATCH:
            if pattern.search(query_text):
                return key
        return None

    def test_product_set_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { productSet(input: $input) { product { id } } }'),
            'product_set',
        )

    def test_product_update_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { productUpdate(input: $input) { product { id } } }'),
            'product_update',
        )

    def test_variant_bulk_update_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { productVariantsBulkUpdate(productId: $id, variants: $v) { } }'),
            'variant_bulk_update',
        )

    def test_customer_create_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { customerCreate(input: $input) { customer { id } } }'),
            'customer_create',
        )

    def test_customer_update_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { customerUpdate(input: $input) { customer { id } } }'),
            'customer_update',
        )

    def test_order_update_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { orderUpdate(input: $input) { order { id } } }'),
            'order_update',
        )

    def test_inventory_set_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { inventorySetQuantities(input: $input) { } }'),
            'inventory_set',
        )

    def test_inventory_adjust_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { inventoryAdjustQuantities(input: $input) { } }'),
            'inventory_adjust',
        )

    def test_fulfillment_create_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { fulfillmentCreate(fulfillment: $f) { } }'),
            'fulfillment_create',
        )

    def test_refund_create_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { refundCreate(input: $input) { } }'),
            'refund_create',
        )

    def test_webhook_create_mutation(self):
        self.assertEqual(
            self._match_mutation('mutation { webhookSubscriptionCreate(topic: $t, webhookSubscription: $w) { } }'),
            'webhook_create',
        )


class TestHandlerRegistry(SimulatorTestCase):
    """Test that all dispatch keys have handlers registered."""

    def test_all_query_keys_implemented_or_placeholder(self):
        """Every query dispatch key should either have a handler or be unimplemented."""
        # These keys are expected to have real handlers in Phase 1
        phase1_query_keys = {'shop', 'products', 'single_product', 'customers',
                             'orders', 'locations'}
        for key in phase1_query_keys:
            self.assertIn(key, _QUERY_HANDLERS,
                          f"Missing handler for query key: {key}")

    def test_all_mutation_keys_implemented_or_placeholder(self):
        """Phase 1 mutation keys should have handlers."""
        phase1_mutation_keys = {'product_set', 'product_create', 'product_update',
                                'variant_bulk_update', 'customer_create',
                                'customer_update', 'order_update',
                                'inventory_set', 'inventory_adjust'}
        for key in phase1_mutation_keys:
            self.assertIn(key, _MUTATION_HANDLERS,
                          f"Missing handler for mutation key: {key}")

    def test_shop_handler_returns_data(self):
        """Shop handler should return valid data."""
        result = self._call_query('shop')
        self.assertIn('shop', result)
        self.assertEqual(result['shop']['name'], 'Test Simulator Store')
        self.assertEqual(result['shop']['currencyCode'], 'USD')
        self.assertIn('plan', result['shop'])
