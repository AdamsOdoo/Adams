from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestInventoryFirstPushGuard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'First Push Guard Test Store',
            'shop_domain': 'first-push-guard-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'inventory_domain_enabled': True,
        })
        cls.store.write({'state': 'connected'})
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.location = cls.env['stock.location'].create({
            'name': 'First Push Guard Location',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.mapping = cls.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Location/200',
            'odoo_location_id': cls.location.id,
            'match_key': 'manual',
        })
        cls.template = cls.env['product.template'].create({
            'name': 'First Push Guard Product',
        })
        cls.template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Product/200',
            'product_template_id': cls.template.id,
        })
        cls.variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/200',
            'product_variant_id': cls.template.product_variant_id.id,
            'product_template_binding_id': cls.template_binding.id,
        })
        cls.binding = cls.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'product_variant_binding_id': cls.variant_binding.id,
            'location_mapping_id': cls.mapping.id,
            'shopify_inventory_item_gid': 'gid://shopify/InventoryItem/200',
        })
        cls.user_reviewer = cls.env['res.users'].create({
            'name': 'First Push Guard Reviewer',
            'login': 'first_push_guard_reviewer',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_reviewer'
                ).id,
            ])],
        })
        cls.user_operator = cls.env['res.users'].create({
            'name': 'First Push Guard Operator',
            'login': 'first_push_guard_operator',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_operator'
                ).id,
            ])],
        })

    def _make_push_sync_job(self):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': 'inventory_push_sync',
            'state': 'running',
            'res_model': 'shopify.connector.inventory.level.binding',
            'res_id': self.binding.id,
            'shopify_target_gid': 'inventory_pair:%s:%s:%s' % (
                self.store.id,
                self.binding.shopify_inventory_item_gid,
                self.mapping.shopify_gid,
            ),
            'expected_connection_generation': self.store.connection_generation,
        })

    def test_push_blocked_before_confirm_never_reads_shopify(self):
        """An unconfirmed pair is blocked before any Shopify read is
        attempted -- the guard is checked first."""
        job = self._make_push_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(Service), '_read_shopify_inventory_pair',
        ) as mocked_read:
            Service._handle_inventory_push_sync(job)
        mocked_read.assert_not_called()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(
            job.manual_review_subreason, 'destructive_write_guard_blocked',
        )

    def test_preview_job_records_quantity(self):
        preview_job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'export_preview_dry_run',
            'job_type': 'inventory_first_push_preview',
            'state': 'running',
            'res_model': 'shopify.connector.inventory.level.binding',
            'res_id': self.binding.id,
            'shopify_target_gid': 'inventory_pair:%s:%s:%s' % (
                self.store.id,
                self.binding.shopify_inventory_item_gid,
                self.mapping.shopify_gid,
            ),
            'expected_connection_generation': self.store.connection_generation,
        })
        Service = self.env['shopify.connector.inventory.service']
        Service._handle_inventory_first_push_preview(preview_job)
        self.assertEqual(self.binding.first_push_state, 'previewed')
        self.assertEqual(preview_job.state, 'succeeded')

    def test_confirm_permission_matrix(self):
        self.binding.sudo().write({
            'first_push_state': 'previewed', 'first_push_preview_qty': 5.0,
        })
        with self.assertRaises(Exception):
            self.binding.with_user(
                self.user_operator
            ).action_confirm_first_push()
        self.binding.with_user(
            self.user_reviewer
        ).action_confirm_first_push()
        self.assertEqual(self.binding.first_push_state, 'confirmed')

    def test_guard_error_class_and_subreason(self):
        job = self._make_push_sync_job()
        self.env['shopify.connector.inventory.service']._handle_inventory_push_sync(
            job
        )
        self.assertEqual(job.error_class, 'shopify_user_errors_validation')
        self.assertEqual(
            job.manual_review_subreason, 'destructive_write_guard_blocked',
        )

    def test_enqueue_first_push_preview_admission_service(self):
        """Sanctioned admission path (PR #182 comment 5025803697 item
        22.C) -- previously a dead handler reachable only through direct
        protected-field job creation. Hardened per comment 5028910116
        item 13: private method, explicit Operator/Administrator
        authority required."""
        Service = self.env['shopify.connector.inventory.service']
        job = Service.with_user(
            self.user_operator
        )._enqueue_first_push_preview(self.binding)
        self.assertEqual(job.job_type, 'inventory_first_push_preview')
        self.assertEqual(job.job_source, 'export_preview_dry_run')
        self.assertEqual(job.state, 'queued')
        job.sudo().write({'state': 'running'})
        Service._handle_inventory_first_push_preview(job)
        self.assertEqual(self.binding.first_push_state, 'previewed')

    def test_enqueue_first_push_preview_denied_for_auditor(self):
        auditor = self.env['res.users'].create({
            'name': 'First Push Guard Auditor',
            'login': 'first_push_guard_auditor',
            'group_ids': [(6, 0, [
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(Exception):
            Service.with_user(auditor)._enqueue_first_push_preview(
                self.binding
            )
