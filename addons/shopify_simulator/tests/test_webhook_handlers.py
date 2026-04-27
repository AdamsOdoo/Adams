# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Tests for webhook subscription CRUD handlers.

Covers:
- webhookSubscriptionCreate (success, duplicate, missing fields)
- webhookSubscriptionDelete (success, nonexistent)
- WEBHOOK_LIST_QUERY (list, pagination)
"""
from .common import SimulatorTestCase


class TestWebhookCreate(SimulatorTestCase):
    """Test the webhookSubscriptionCreate mutation handler."""

    def test_create_webhook(self):
        """Create a new webhook subscription."""
        result = self._call_mutation('webhook_create', {
            'topic': 'PRODUCTS_CREATE',
            'url': 'https://odoo.example.com/shopify/webhook/1',
        })
        wc = result.get('webhookSubscriptionCreate', {})
        self.assertEqual(wc['userErrors'], [])
        sub = wc['webhookSubscription']
        self.assertIsNotNone(sub)
        self.assertEqual(sub['topic'], 'products/create')
        self.assertEqual(sub['endpoint']['callbackUrl'],
                         'https://odoo.example.com/shopify/webhook/1')
        self.assertIn('id', sub)

    def test_create_webhook_duplicate_topic(self):
        """Creating a webhook with duplicate topic updates existing."""
        self._call_mutation('webhook_create', {
            'topic': 'ORDERS_CREATE',
            'url': 'https://odoo.example.com/shopify/webhook/1',
        })
        # Create again with different URL
        result = self._call_mutation('webhook_create', {
            'topic': 'ORDERS_CREATE',
            'url': 'https://odoo.example.com/shopify/webhook/2',
        })
        wc = result.get('webhookSubscriptionCreate', {})
        self.assertEqual(wc['userErrors'], [])
        self.assertEqual(
            wc['webhookSubscription']['endpoint']['callbackUrl'],
            'https://odoo.example.com/shopify/webhook/2',
        )
        # Only one subscription for this topic
        count = self.env['sim.shopify.webhook.subscription'].search_count([
            ('config_id', '=', self.sim_config.id),
            ('topic', '=', 'ORDERS_CREATE'),
        ])
        self.assertEqual(count, 1)

    def test_create_webhook_missing_topic(self):
        """Missing topic returns userError."""
        result = self._call_mutation('webhook_create', {
            'topic': '',
            'url': 'https://odoo.example.com/shopify/webhook/1',
        })
        wc = result.get('webhookSubscriptionCreate', {})
        self.assertTrue(len(wc['userErrors']) > 0)

    def test_create_webhook_missing_url(self):
        """Missing URL returns userError."""
        result = self._call_mutation('webhook_create', {
            'topic': 'PRODUCTS_UPDATE',
            'url': '',
        })
        wc = result.get('webhookSubscriptionCreate', {})
        self.assertTrue(len(wc['userErrors']) > 0)

    def test_create_multiple_topics(self):
        """Create webhooks for different topics."""
        topics = ['PRODUCTS_CREATE', 'ORDERS_CREATE', 'CUSTOMERS_CREATE']
        for topic in topics:
            self._call_mutation('webhook_create', {
                'topic': topic,
                'url': f'https://odoo.example.com/shopify/webhook/1',
            })
        count = self.env['sim.shopify.webhook.subscription'].search_count([
            ('config_id', '=', self.sim_config.id),
        ])
        self.assertEqual(count, len(topics))


class TestWebhookDelete(SimulatorTestCase):
    """Test the webhookSubscriptionDelete mutation handler."""

    def _create_subscription(self, topic='PRODUCTS_CREATE'):
        return self.env['sim.shopify.webhook.subscription'].create({
            'config_id': self.sim_config.id,
            'topic': topic,
            'callback_url': 'https://odoo.example.com/shopify/webhook/1',
        })

    def test_delete_webhook(self):
        """Delete an existing webhook subscription."""
        sub = self._create_subscription()
        gid = sub.shopify_gid

        result = self._call_mutation('webhook_delete', {'id': gid})
        wd = result.get('webhookSubscriptionDelete', {})
        self.assertEqual(wd['userErrors'], [])
        self.assertEqual(wd['deletedWebhookSubscriptionId'], gid)

        # Verify deleted
        exists = self.env['sim.shopify.webhook.subscription'].search([
            ('shopify_gid', '=', gid),
        ])
        self.assertFalse(exists)

    def test_delete_nonexistent_webhook(self):
        """Delete nonexistent webhook returns error."""
        result = self._call_mutation('webhook_delete', {
            'id': 'gid://shopify/WebhookSubscription/999999',
        })
        wd = result.get('webhookSubscriptionDelete', {})
        self.assertTrue(len(wd['userErrors']) > 0)


class TestWebhookList(SimulatorTestCase):
    """Test the WEBHOOK_LIST_QUERY handler."""

    def test_list_empty(self):
        """Empty store returns no webhooks."""
        result = self._call_query('webhook_list', {'first': 50})
        edges = result['webhookSubscriptions']['edges']
        self.assertEqual(len(edges), 0)

    def test_list_webhooks(self):
        """List all registered webhooks."""
        for topic in ['PRODUCTS_CREATE', 'ORDERS_CREATE']:
            self.env['sim.shopify.webhook.subscription'].create({
                'config_id': self.sim_config.id,
                'topic': topic,
                'callback_url': 'https://odoo.example.com/shopify/webhook/1',
            })
        result = self._call_query('webhook_list', {'first': 50})
        edges = result['webhookSubscriptions']['edges']
        self.assertEqual(len(edges), 2)

        topics = {e['node']['topic'] for e in edges}
        self.assertIn('products/create', topics)
        self.assertIn('orders/create', topics)

    def test_webhook_node_shape(self):
        """Verify webhook node has all required fields."""
        sub = self.env['sim.shopify.webhook.subscription'].create({
            'config_id': self.sim_config.id,
            'topic': 'FULFILLMENTS_CREATE',
            'callback_url': 'https://odoo.example.com/webhook/1',
        })
        node = sub._to_graphql_node()
        required_fields = ['id', 'topic', 'endpoint', 'createdAt']
        for field in required_fields:
            self.assertIn(field, node, f"Missing field: {field}")
        self.assertEqual(node['endpoint']['__typename'], 'WebhookHttpEndpoint')
        self.assertIn('callbackUrl', node['endpoint'])
