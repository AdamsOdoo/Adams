# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestShopifyBackend(TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-store.myshopify.com',
            'access_token': 'shpat_test_token_12345',
            'company_id': self.env.company.id,
        })

    def test_backend_creation(self):
        """Backend should be created in draft state."""
        self.assertEqual(self.backend.state, 'draft')
        self.assertEqual(self.backend.api_version, '2026-01')
        self.assertEqual(self.backend.batch_size, 50)

    def test_backend_defaults(self):
        """Check that sync defaults are sensible."""
        self.assertTrue(self.backend.auto_sync_products)
        self.assertTrue(self.backend.auto_sync_customers)
        self.assertTrue(self.backend.auto_sync_orders)
        self.assertTrue(self.backend.auto_sync_inventory)
        self.assertEqual(self.backend.product_sync_direction, 'both')
        self.assertEqual(self.backend.customer_sync_direction, 'import')
        self.assertEqual(self.backend.product_sync_interval, 15)
        self.assertEqual(self.backend.order_sync_interval, 5)
        self.assertEqual(self.backend.inventory_sync_interval, 10)

    def test_register_webhooks_not_connected(self):
        """Should raise error if backend is not connected."""
        with self.assertRaises(UserError):
            self.backend.action_register_webhooks()

    def test_binding_counts_zero(self):
        """Binding counts should be 0 for new backend."""
        self.assertEqual(self.backend.product_bind_count, 0)
        self.assertEqual(self.backend.customer_bind_count, 0)
        self.assertEqual(self.backend.order_bind_count, 0)
        self.assertEqual(self.backend.product_error_count, 0)

    def test_init_field_mappings(self):
        """Should create default field mappings."""
        self.assertFalse(self.backend.field_mapping_ids)
        self.backend.action_init_field_mappings()
        self.assertTrue(self.backend.field_mapping_ids)
        # Should have product + customer mappings
        product_maps = self.backend.field_mapping_ids.filtered(
            lambda m: m.entity == 'product'
        )
        customer_maps = self.backend.field_mapping_ids.filtered(
            lambda m: m.entity == 'customer'
        )
        self.assertGreater(len(product_maps), 0)
        self.assertGreater(len(customer_maps), 0)

    def test_init_field_mappings_idempotent(self):
        """Should not duplicate mappings on second call."""
        self.backend.action_init_field_mappings()
        count1 = len(self.backend.field_mapping_ids)
        self.backend.action_init_field_mappings()
        count2 = len(self.backend.field_mapping_ids)
        self.assertEqual(count1, count2)

    def test_multi_company_isolation(self):
        """Backend should respect multi-company rules."""
        self.assertEqual(self.backend.company_id, self.env.company)


class TestShopifyBinding(TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test-store.myshopify.com',
            'access_token': 'shpat_test_token',
            'company_id': self.env.company.id,
        })
        self.product = self.env['product.template'].create({
            'name': 'Test Product',
            'list_price': 25.0,
        })

    def test_product_binding_creation(self):
        """Should create a product binding."""
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/Product/123',
        })
        self.assertEqual(binding.sync_status, 'pending')
        self.assertEqual(binding.retry_count, 0)

    def test_mark_synced(self):
        """_mark_synced should update status and checksum."""
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
        })
        binding._mark_synced(
            shopify_id='gid://shopify/Product/456',
            checksum='abc123',
        )
        self.assertEqual(binding.sync_status, 'synced')
        self.assertEqual(binding.shopify_id, 'gid://shopify/Product/456')
        self.assertEqual(binding.sync_checksum, 'abc123')
        self.assertTrue(binding.last_sync_date)

    def test_mark_error(self):
        """_mark_error should set error state and message."""
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
        })
        binding._mark_error('API timeout')
        self.assertEqual(binding.sync_status, 'error')
        self.assertEqual(binding.sync_error, 'API timeout')
        self.assertEqual(binding.retry_count, 1)

    def test_mark_permanent_error(self):
        """_mark_error with permanent=True should set permanent_error."""
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
        })
        binding._mark_error('Not found', permanent=True)
        self.assertEqual(binding.sync_status, 'permanent_error')

    def test_retry_sync(self):
        """action_retry_sync should reset error state."""
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'sync_status': 'error',
            'sync_error': 'Old error',
            'retry_count': 3,
        })
        binding.action_retry_sync()
        self.assertEqual(binding.sync_status, 'pending')
        self.assertFalse(binding.sync_error)
        self.assertEqual(binding.retry_count, 0)

    def test_unique_constraint_backend_shopify(self):
        """Should prevent duplicate shopify_id per backend."""
        self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/Product/999',
        })
        product2 = self.env['product.template'].create({
            'name': 'Product 2',
            'list_price': 10.0,
        })
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['shopify.product.binding'].create({
                'backend_id': self.backend.id,
                'odoo_id': product2.id,
                'shopify_id': 'gid://shopify/Product/999',
            })


class TestSyncLog(TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })

    def test_sync_log_creation(self):
        """Should create a sync log in running state."""
        log = self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'operation': 'export',
        })
        self.assertEqual(log.state, 'running')

    def test_sync_log_finalize_success(self):
        """_finalize should set state to done on full success."""
        log = self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'operation': 'export',
        })
        log._finalize(success=10, errors=0, skipped=2)
        self.assertEqual(log.state, 'done')
        self.assertEqual(log.total_records, 12)
        self.assertEqual(log.success_count, 10)

    def test_sync_log_finalize_partial(self):
        """_finalize with some errors should set state to partial."""
        log = self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': 'product',
            'operation': 'export',
        })
        log._finalize(success=8, errors=2, skipped=0, error_details='Some error')
        self.assertEqual(log.state, 'partial')
        self.assertEqual(log.error_count, 2)

    def test_sync_log_finalize_all_errors(self):
        """_finalize with only errors should set state to error."""
        log = self.env['shopify.sync.log'].create({
            'backend_id': self.backend.id,
            'entity': 'order',
            'operation': 'import',
        })
        log._finalize(success=0, errors=5, skipped=0)
        self.assertEqual(log.state, 'error')


class TestWebhookLog(TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
        })

    def test_webhook_log_creation(self):
        """Should create webhook log in pending state."""
        log = self.env['shopify.webhook.log'].create({
            'backend_id': self.backend.id,
            'webhook_id': 'wh_12345',
            'topic': 'products/update',
            'payload': '{"id": 123}',
        })
        self.assertEqual(log.state, 'pending')

    def test_webhook_dedup(self):
        """Should prevent duplicate webhook_id entries."""
        self.env['shopify.webhook.log'].create({
            'backend_id': self.backend.id,
            'webhook_id': 'wh_unique_123',
            'topic': 'products/create',
        })
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['shopify.webhook.log'].create({
                'backend_id': self.backend.id,
                'webhook_id': 'wh_unique_123',
                'topic': 'products/create',
            })
