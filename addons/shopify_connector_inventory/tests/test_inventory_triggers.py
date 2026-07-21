from unittest.mock import patch

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


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

    def test_cron_enqueues_one_typed_scan_job_per_eligible_store(self):
        """Corrected D-013-6b/item 13: the cron entry point only enqueues
        a typed `inventory_push_scan` job per eligible connected store --
        it never scans inline itself."""
        Service = self.env['shopify.connector.inventory.service']
        jobs = Service.run_inventory_push_scan()
        self.assertTrue(jobs)
        self.assertTrue(all(j.job_type == 'inventory_push_scan' for j in jobs))
        self.assertTrue(all(j.state == 'queued' for j in jobs))
        # The cron call itself never touches inventory_last_push_scan_at
        # or enqueues any push_sync job -- that is the scan handler's job.
        self.settings.invalidate_recordset()
        self.assertFalse(self.settings.inventory_last_push_scan_at)
        self.assertFalse(self._open_push_jobs_for_binding(self.binding))

    def _make_scan_job(self):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'inventory_push_scan',
            'state': 'running',
            'expected_connection_generation': self.store.connection_generation,
        })

    def test_scan_handler_enqueues_deltas_only(self):
        """A previously and successfully pushed zero (`last_pushed_at`
        populated) with an unchanged zero target is genuinely unchanged
        -- no delta, no job (PR #182 comment 5028910116 item 5)."""
        Service = self.env['shopify.connector.inventory.service']
        self.binding.sudo().write({
            'last_pushed_available': 0.0,
            'last_pushed_at': '2020-01-01 00:00:00',
        })
        scan_job = self._make_scan_job()
        Service._handle_inventory_push_scan(scan_job)
        self.assertFalse(self._open_push_jobs_for_binding(self.binding))
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.inventory_last_push_scan_at)
        scan_job.invalidate_recordset()
        self.assertEqual(scan_job.state, 'succeeded')

    # ------------------------------------------------------------------
    # Never-pushed-zero scan admission (PR #182 comment 5028910116 item
    # 5): last_pushed_available defaults to 0.0, which alone never
    # distinguishes "never successfully pushed" from "successfully
    # pushed a confirmed zero."
    # ------------------------------------------------------------------

    def test_scan_admits_never_pushed_pair_even_at_zero_target(self):
        Service = self.env['shopify.connector.inventory.service']
        self.assertFalse(self.binding.last_pushed_at)
        self.assertEqual(self.binding.last_pushed_available, 0.0)
        scan_job = self._make_scan_job()
        with patch.object(
            type(Service), '_refresh_pending_target',
            return_value=(0.0, 0.0),
        ):
            Service._handle_inventory_push_scan(scan_job)
        self.assertTrue(self._open_push_jobs_for_binding(self.binding))
        scan_job.invalidate_recordset()
        self.assertEqual(scan_job.state, 'succeeded')

    def test_scan_skips_previously_pushed_zero_unchanged(self):
        Service = self.env['shopify.connector.inventory.service']
        self.binding.sudo().write({
            'last_pushed_available': 0.0,
            'last_pushed_at': '2020-01-01 00:00:00',
        })
        scan_job = self._make_scan_job()
        with patch.object(
            type(Service), '_refresh_pending_target',
            return_value=(0.0, 0.0),
        ):
            Service._handle_inventory_push_scan(scan_job)
        self.assertFalse(self._open_push_jobs_for_binding(self.binding))

    def test_scan_admits_never_pushed_pair_with_positive_target(self):
        Service = self.env['shopify.connector.inventory.service']
        scan_job = self._make_scan_job()
        with patch.object(
            type(Service), '_refresh_pending_target',
            return_value=(5.0, 5.0),
        ):
            Service._handle_inventory_push_scan(scan_job)
        self.assertTrue(self._open_push_jobs_for_binding(self.binding))

    def test_scan_skips_pushed_quantity_unchanged(self):
        Service = self.env['shopify.connector.inventory.service']
        self.binding.sudo().write({
            'last_pushed_available': 7.0,
            'last_pushed_at': '2020-01-01 00:00:00',
        })
        scan_job = self._make_scan_job()
        with patch.object(
            type(Service), '_refresh_pending_target',
            return_value=(7.0, 7.0),
        ):
            Service._handle_inventory_push_scan(scan_job)
        self.assertFalse(self._open_push_jobs_for_binding(self.binding))

    def test_scan_skips_when_domain_disabled(self):
        Service = self.env['shopify.connector.inventory.service']
        self.settings.write({'inventory_domain_enabled': False})
        scan_job = self._make_scan_job()
        Service._handle_inventory_push_scan(scan_job)
        scan_job.invalidate_recordset()
        self.assertEqual(scan_job.state, 'skipped')
        self.assertFalse(self._open_push_jobs_for_binding(self.binding))

    def test_scan_handler_enqueues_push_sync_for_changed_pair(self):
        Service = self.env['shopify.connector.inventory.service']
        self.binding.sudo().write({'last_pushed_available': 999.0})
        scan_job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'scheduled_sync',
            'job_type': 'inventory_push_scan',
            'state': 'running',
            'expected_connection_generation': self.store.connection_generation,
        })
        with patch.object(
            type(Service), '_refresh_pending_target', return_value=(0.0, 0.0),
        ):
            Service._handle_inventory_push_scan(scan_job)
        self.assertTrue(self._open_push_jobs_for_binding(self.binding))
        scan_job.invalidate_recordset()
        self.assertEqual(scan_job.state, 'succeeded')

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
                'tracked': True, 'item_exists': True, 'level_exists': True,
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

    def test_shopify_equals_target_is_never_drift_even_if_differs_from_last_pushed(self):
        """Corrected three-way drift matrix (item 14): Shopify already
        reflecting the CURRENT Odoo target must succeed, never block --
        even when it also differs from last_pushed_available."""
        self.binding.sudo().write({
            'last_pushed_available': 10.0,
            'last_pushed_at': '2020-01-01 00:00:00',
            'pending_target_available': 999.0,
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
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 999.0, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ), patch.object(
            type(Service), '_refresh_pending_target',
            return_value=(999.0, 999.0),
        ):
            Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')

    def test_no_prior_push_known_local_change_enqueues_set_quantities(self):
        """Case 1 of the three-way matrix: no unexplained-drift history
        yet and the Odoo target changed -- enqueue toward it."""
        self.binding.sudo().write({
            'last_pushed_available': 0.0,
            'last_pushed_at': False,
            'pending_target_available': 3.0,
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
                'tracked': True, 'item_exists': True, 'level_exists': True,
                'available': 0.0, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ), patch.object(
            type(Service), '_refresh_pending_target',
            return_value=(3.0, 3.0),
        ):
            Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        new_jobs = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_set_quantities'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertTrue(new_jobs)

    # ------------------------------------------------------------------
    # Missing InventoryItem is never routed to activation (PR #182
    # comment 5028910116 item 1)
    # ------------------------------------------------------------------

    def _make_push_sync_job(self):
        return self.env['shopify.connector.job'].sudo().create({
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

    def test_missing_inventory_item_never_enqueues_activation(self):
        Service = self.env['shopify.connector.inventory.service']
        job = self._make_push_sync_job()
        with patch.object(
            type(Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': None, 'item_exists': False, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(job.manual_review_subreason, 'binding_conflict')
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_activate'),
            ('res_id', '=', self.binding.id),
        ]))

    # ------------------------------------------------------------------
    # Orchestration handoff row lock + rollback atomicity (DEC-037 §5.4
    # handoff A; PR #182 comment 5028910116 item 12)
    # ------------------------------------------------------------------

    def test_push_sync_handoff_raises_when_binding_lock_unavailable(self):
        Service = self.env['shopify.connector.inventory.service']
        job = self._make_push_sync_job()
        empty_binding = self.env['shopify.connector.inventory.level.binding']
        with patch.object(
            type(Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ), patch.object(
            type(self.binding), 'try_lock_for_update',
            return_value=empty_binding,
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        # The lock is acquired BEFORE terminalizing -- a failed lock
        # must never leave the orchestration job succeeded with no
        # child (duplicate-handoff protection).
        self.assertEqual(job.state, 'running')
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_activate'),
            ('res_id', '=', self.binding.id),
        ]))

    def test_push_sync_handoff_rolls_back_on_child_creation_failure(self):
        Service = self.env['shopify.connector.inventory.service']
        job = self._make_push_sync_job()
        with patch.object(
            type(Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ), patch.object(
            type(Service), '_create_inventory_job',
            side_effect=RuntimeError('synthetic child-creation failure'),
        ):
            with self.assertRaises(RuntimeError):
                with self.env.cr.savepoint():
                    Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        self.assertEqual(job.state, 'running')

    def test_push_sync_handoff_logs_predecessor_and_successor_ids(self):
        Service = self.env['shopify.connector.inventory.service']
        job = self._make_push_sync_job()
        with patch.object(
            type(Service), '_read_shopify_inventory_pair',
            return_value={
                'tracked': True, 'item_exists': True, 'level_exists': False,
                'inventory_level_gid': None,
                'available': None, 'updated_at': False,
                'store_identity': self.store.shop_domain,
            },
        ):
            Service._handle_inventory_push_sync(job)
        job.invalidate_recordset()
        successor = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'inventory_activate'),
            ('res_id', '=', self.binding.id),
        ])
        self.assertTrue(successor)
        logs = self.env['shopify.connector.job.log'].search([
            ('job_id', '=', job.id),
        ])
        self.assertTrue(any(
            'predecessor_job_id=%d' % job.id in (log.message or '')
            and 'successor_job_id=%d' % successor.id in (log.message or '')
            for log in logs
        ))
