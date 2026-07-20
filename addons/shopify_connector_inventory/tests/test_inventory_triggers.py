from unittest.mock import patch

from odoo.tests.common import TransactionCase


class TestInventoryTriggers(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Inventory Triggers Test Store',
            'shop_domain': 'inventory-triggers-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'inventory_domain_enabled': True,
            'inventory_scheduled_sync_enabled': True,
        })
        cls.store.write({'state': 'connected'})
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.mapped_location = cls.env['stock.location'].create({
            'name': 'Trigger Test Mapped Location',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.unmapped_location = cls.env['stock.location'].create({
            'name': 'Trigger Test Unmapped Location',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.mapping = cls.env['shopify.connector.location.mapping'].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Location/400',
            'odoo_location_id': cls.mapped_location.id,
            'match_key': 'manual',
        })
        cls.template = cls.env['product.template'].create({
            'name': 'Trigger Test Product',
            'type': 'consu', 'is_storable': True,
        })
        cls.template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Product/400',
            'product_template_id': cls.template.id,
        })
        cls.variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/400',
            'product_variant_id': cls.template.product_variant_id.id,
            'product_template_binding_id': cls.template_binding.id,
        })
        cls.binding = cls.env[
            'shopify.connector.inventory.level.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'product_variant_binding_id': cls.variant_binding.id,
            'location_mapping_id': cls.mapping.id,
            'shopify_inventory_item_gid': 'gid://shopify/InventoryItem/400',
            'first_push_state': 'confirmed',
        })
        cls.user_operator = cls.env['res.users'].create({
            'name': 'Trigger Test Operator',
            'login': 'trigger_test_operator',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_operator'
                ).id,
            ])],
        })
        cls.user_auditor = cls.env['res.users'].create({
            'name': 'Trigger Test Auditor',
            'login': 'trigger_test_auditor',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })

    def _open_push_jobs_for_binding(self, binding):
        return self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_push_sync'),
            ('res_model', '=', 'shopify.connector.inventory.level.binding'),
            ('res_id', '=', binding.id),
        ])

    def test_odoo_event_enqueues_only_mapped_pairs(self):
        supplier_location = self.env.ref('stock.stock_location_suppliers')
        move = self.env['stock.move'].create({
            'name': 'Trigger Test Receipt',
            'product_id': self.template.product_variant_id.id,
            'product_uom_qty': 5.0,
            'product_uom': self.template.uom_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.mapped_location.id,
        })
        move._action_confirm()
        move._action_assign()
        for line in move.move_line_ids:
            line.quantity = 5.0
        move._action_done()
        jobs = self._open_push_jobs_for_binding(self.binding)
        self.assertTrue(jobs, 'A push_sync job should be enqueued for the mapped pair.')

        # A move into an unmapped location must not enqueue anything for
        # this pair a second time via that path.
        before_count = len(jobs)
        move2 = self.env['stock.move'].create({
            'name': 'Trigger Test Unmapped Receipt',
            'product_id': self.template.product_variant_id.id,
            'product_uom_qty': 3.0,
            'product_uom': self.template.uom_id.id,
            'location_id': supplier_location.id,
            'location_dest_id': self.unmapped_location.id,
        })
        move2._action_confirm()
        move2._action_assign()
        for line in move2.move_line_ids:
            line.quantity = 3.0
        move2._action_done()
        jobs_after = self._open_push_jobs_for_binding(self.binding)
        self.assertEqual(len(jobs_after), before_count)

    def test_scan_enqueues_deltas_only(self):
        Service = self.env['shopify.connector.inventory.service']
        self.binding.sudo().write({'last_pushed_available': 0.0})
        with patch.object(
            type(Service), '_read_shopify_inventory_pair',
        ):
            Service.run_inventory_push_scan()
        # free_qty is 0 (no stock moved in this test) and
        # last_pushed_available is already 0 -- no delta, no job.
        self.assertFalse(self._open_push_jobs_for_binding(self.binding))
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.inventory_last_push_scan_at)

    def test_manual_push_requires_operator_or_admin(self):
        with self.assertRaises(Exception):
            self.store.with_user(self.user_auditor).action_push_inventory_now()
        self.store.with_user(self.user_operator).action_push_inventory_now()
        self.assertTrue(self._open_push_jobs_for_binding(self.binding))

    def test_unexplained_drift_blocks_and_is_logged(self):
        self.binding.sudo().write({
            'last_pushed_available': 10.0,
            'last_pushed_at': '2020-01-01 00:00:00',
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
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
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True,
                'available': 999.0,
                'updated_at': '2020-06-01 00:00:00',
                'store_identity': self.store.shop_domain,
            },
        ):
            Service._handle_inventory_push_sync(job)
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'binding_conflict')
        logs = self.env['shopify.connector.job.log'].search([
            ('job_id', '=', job.id),
        ])
        self.assertTrue(any('drift' in (log.message or '').lower() for log in logs))
