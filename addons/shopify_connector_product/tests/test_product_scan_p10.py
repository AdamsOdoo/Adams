"""Odoo-facing admission and local page-boundary coverage for P10."""

from datetime import datetime, timezone

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.runtime.p10_coordinator import (
    CLAIM_TRANSACTION,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_v2_runtime_repository import (
    OdooReadOnlyRuntimeRepository,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


@tagged('post_install', '-at_install')
class TestProductScanP10(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].sudo().create({
            'name': 'P10 Product Scan Store',
            'shop_domain': 'p10-product-scan.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
        })
        cls.settings = cls.env[
            'shopify.connector.store.settings'
        ].sudo().create({
            'store_id': cls.store.id,
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })
        cls.roles = {
            label: cls.env['res.users'].create({
                'name': 'P10 %s' % label,
                'login': 'p10_product_scan_%s' % label,
                'company_id': cls.env.company.id,
                'company_ids': [(6, 0, [cls.env.company.id])],
                'group_ids': [(6, 0, [
                    cls.env.ref('base.group_user').id,
                    cls.env.ref(
                        'shopify_connector_core.%s' % xmlid,
                    ).id,
                ])],
            })
            for label, xmlid in (
                ('operator', 'group_shopify_connector_operator'),
                ('admin', 'group_shopify_connector_admin'),
            )
        }

    def setUp(self):
        super().setUp()
        # P10 page boundaries deliberately use short registry cursors.  Test
        # mode makes those cursors visible to the transaction fixture while
        # retaining the production side-cursor implementation.
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _enable_v2_read_only(self):
        settings = self.settings.with_user(self.roles['admin'])
        settings._set_v2_modes_service(
            {'v2_runtime_mode': 'read_only'},
            reason='P10 product scan test activation',
            expected_configuration_generation=settings.configuration_generation,
        )
        self.settings.invalidate_recordset()

    def _claimed_scan(self):
        self._enable_v2_read_only()
        job = self.store.with_user(
            self.roles['operator'],
        ).action_sync_products_now()
        self.env.flush_all()
        claims = OdooReadOnlyRuntimeRepository(self.env).claim_due(
            now=datetime.now(timezone.utc),
            worker_ref='worker:p10-product-test',
            limit=1,
            phase=CLAIM_TRANSACTION,
        )
        self.assertEqual(len(claims), 1)
        return job, claims[0]

    @staticmethod
    def _node(number, updated_at='2000-01-01T00:00:00Z'):
        return {
            'id': 'gid://shopify/Product/%d' % number,
            'updatedAt': updated_at,
            'status': 'ACTIVE',
        }

    def test_claim_owned_initialization_persists_fixed_window(self):
        job, claim = self._claimed_scan()
        scanner = self.env['shopify.connector.product.scan.p10']
        window = scanner._initialize_window(claim, job, self.store)

        self.settings.invalidate_recordset()
        self.assertIsNone(window['start'])
        self.assertIsNone(window['cursor'])
        self.assertEqual(window['page_count'], 0)
        self.assertEqual(window['generation'], claim.expected_generation)
        self.assertTrue(window['end'])
        self.assertEqual(
            self.settings.product_scan_window_end_at,
            window['end'],
        )
        self.assertEqual(
            self.settings.product_scan_generation,
            claim.expected_generation,
        )

    def test_claim_owned_terminal_page_coalesces_same_page_children_and_clears_window(self):
        job, claim = self._claimed_scan()
        initial_configuration = claim.expected_configuration_generation
        scanner = self.env['shopify.connector.product.scan.p10']
        window = scanner._initialize_window(claim, job, self.store)
        node = self._node(101)
        counts = scanner._commit_page(
            claim,
            job,
            self.store,
            window,
            [node, dict(node)],
            has_next=False,
            end_cursor=None,
        )

        self.settings.invalidate_recordset()
        children = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_sync'),
            ('shopify_target_gid', '=', node['id']),
        ])
        self.assertEqual(counts['enqueued'], 1)
        self.assertEqual(counts['collided'], 1)
        self.assertEqual(len(children), 1)
        self.assertFalse(children.run_id)
        self.assertTrue(self.settings.product_last_import_checkpoint_at)
        self.assertTrue(self.settings.product_last_import_success_at)
        self.assertFalse(self.settings.product_scan_window_end_at)
        self.assertFalse(self.settings.product_scan_cursor)
        self.assertFalse(self.settings.product_scan_latest_at)
        self.assertEqual(self.settings.product_scan_page_count, 0)
        self.assertEqual(
            self.settings.configuration_generation,
            initial_configuration,
        )

    def test_policy_change_after_claim_rejects_page_before_local_effects(self):
        job, claim = self._claimed_scan()
        scanner = self.env['shopify.connector.product.scan.p10']
        window = scanner._initialize_window(claim, job, self.store)
        settings = self.settings.with_user(self.roles['admin'])
        settings._set_v2_modes_service(
            {'v2_runtime_mode': 'subscriptions'},
            reason='P10 configuration fence regression',
            expected_configuration_generation=(
                claim.expected_configuration_generation
            ),
        )
        with self.assertRaises(ShopifyQuiescedError):
            scanner._commit_page(
                claim,
                job,
                self.store,
                window,
                [self._node(150)],
                has_next=False,
                end_cursor=None,
            )
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_sync'),
            ('shopify_target_gid', '=', 'gid://shopify/Product/150'),
        ]))

    def test_claim_owned_continuation_page_persists_cursor_without_advancing_checkpoint(self):
        job, claim = self._claimed_scan()
        scanner = self.env['shopify.connector.product.scan.p10']
        window = scanner._initialize_window(claim, job, self.store)
        counts = scanner._commit_page(
            claim,
            job,
            self.store,
            window,
            [self._node(202)],
            has_next=True,
            end_cursor='cursor-page-1',
        )

        self.settings.invalidate_recordset()
        self.assertTrue(counts['continuation'])
        self.assertEqual(self.settings.product_scan_cursor, 'cursor-page-1')
        self.assertEqual(self.settings.product_scan_page_count, 1)
        self.assertFalse(self.settings.product_last_import_checkpoint_at)
        self.assertTrue(self.settings.product_scan_latest_at)

    def test_malformed_timestamp_is_rejected_before_any_child_or_checkpoint_write(self):
        job, claim = self._claimed_scan()
        scanner = self.env['shopify.connector.product.scan.p10']
        window = scanner._initialize_window(claim, job, self.store)
        with self.assertRaises(JobHandlerError) as error:
            scanner._commit_page(
                claim,
                job,
                self.store,
                window,
                [self._node(303, updated_at='not-a-timestamp')],
                has_next=False,
                end_cursor=None,
            )

        self.settings.invalidate_recordset()
        self.assertEqual(error.exception.error_class, 'data_shape_schema_mismatch')
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_sync'),
            ('shopify_target_gid', '=', 'gid://shopify/Product/303'),
        ]))
        self.assertFalse(self.settings.product_last_import_checkpoint_at)

    def test_read_only_manual_route_creates_run_before_v2_job(self):
        self._enable_v2_read_only()
        job = self.store.with_user(
            self.roles['operator'],
        ).action_sync_products_now()

        self.assertEqual(job.job_type, 'product_import_scan')
        self.assertTrue(job.run_id)
        self.assertEqual(job.run_id.workflow, 'product')
        self.assertEqual(job.run_id.operation, 'product.import.scan')
        self.assertEqual(job.run_id.trigger, 'user')
        self.assertEqual(job.run_id.actor_uid, self.roles['operator'])
        self.assertEqual(job.sequence, 0)
        self.assertFalse(job.parent_job_id)
        self.assertEqual(job.expected_connection_generation, self.store.connection_generation)
        self.assertEqual(
            job.expected_configuration_generation,
            self.settings.configuration_generation,
        )

    def test_legacy_manual_route_remains_runless(self):
        job = self.store.with_user(
            self.roles['operator'],
        ).action_sync_products_now()
        self.assertEqual(job.job_type, 'product_import_scan')
        self.assertFalse(job.run_id)

    def test_read_only_scheduled_route_records_cron_actor_on_run(self):
        self._enable_v2_read_only()
        self.settings.write({'product_scheduled_sync_enabled': True})
        self.env['shopify.connector.store']._cron_enqueue_product_scans()
        job = self.env['shopify.connector.job'].search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_scan'),
        ], limit=1)

        self.assertTrue(job)
        self.assertTrue(job.run_id)
        self.assertEqual(job.run_id.trigger, 'cron')
        self.assertEqual(job.run_id.actor_uid, self.env.user)

    def test_product_scan_is_registered_in_v2_handler_and_claim_unions(self):
        runtime = self.env['shopify.connector.v2.runtime'].with_user(
            self.roles['admin'],
        )
        spec = runtime._handler_registry().require('product_import_scan')
        self.assertEqual(spec.operation_kind, 'scan')

    def test_non_admin_cannot_enable_v2_runtime_mode(self):
        with self.assertRaises(AccessError):
            self.settings.with_user(self.roles['operator'])._set_v2_modes_service(
                {'v2_runtime_mode': 'read_only'},
                reason='unauthorized P10 test activation',
                expected_configuration_generation=self.settings.configuration_generation,
            )

    def test_direct_orm_write_cannot_forge_product_scan_checkpoint(self):
        settings = self.env[
            'shopify.connector.store.settings'
        ].with_user(self.roles['operator']).browse(self.settings.id)
        with self.assertRaises(AccessError):
            settings.write({'product_scan_cursor': 'forged-cursor'})
