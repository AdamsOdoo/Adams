from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestInventoryLocationCacheSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Location Cache Sync Test Store',
            'shop_domain': 'location-cache-sync-test.myshopify.com',
            'api_version': '2026-07',
        })
        # `inventory_location_sync` is a business-gated `manual_sync` job;
        # core's job-create gate refuses any business job for a store that
        # is not `connected`. The store default is `setup_incomplete`, so
        # the fixture must connect it exactly as the other suites do.
        cls.store.write({'state': 'connected'})
        cls.user_auditor = cls.env['res.users'].create({
            'name': 'Location Cache Sync Auditor',
            'login': 'location_cache_sync_auditor',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })
        cls.user_admin = cls.env['res.users'].create({
            'name': 'Location Cache Sync Admin',
            'login': 'location_cache_sync_admin',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_admin'
                ).id,
            ])],
        })
        cls.user_operator = cls.env['res.users'].create({
            'name': 'Location Cache Sync Operator',
            'login': 'location_cache_sync_operator',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_operator'
                ).id,
            ])],
        })

    def _make_sync_job(self):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': 'inventory_location_sync',
            'state': 'running',
            'expected_connection_generation': self.store.connection_generation,
        })

    def _one_page_response(self, locations):
        return {
            'data': {
                'locations': {
                    'edges': [
                        {'cursor': 'cursor-%d' % index, 'node': loc}
                        for index, loc in enumerate(locations)
                    ],
                    'pageInfo': {'hasNextPage': False},
                },
            },
        }

    def test_no_group_has_direct_create_write_on_location_cache(self):
        """The core cache's read-only ACL posture is unchanged -- no
        connector role may create/write shopify.connector.location
        directly (only this module's own named sudo() elevation may)."""
        for user in (self.user_auditor, self.user_admin):
            with self.assertRaises(AccessError, msg=user.login):
                self.env['shopify.connector.location'].with_user(
                    user
                ).create({
                    'store_id': self.store.id,
                    'shopify_location_gid': 'gid://shopify/Location/999',
                    'name': 'Forged',
                })

    def test_upsert_creates_then_updates_via_named_sudo(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value=self._one_page_response([
                {'id': 'gid://shopify/Location/300', 'name': 'Warehouse A'},
            ]),
        ):
            Service._handle_inventory_location_sync(job)
        location = self.env['shopify.connector.location'].sudo().search([
            ('store_id', '=', self.store.id),
            ('shopify_location_gid', '=', 'gid://shopify/Location/300'),
        ])
        self.assertEqual(len(location), 1)
        self.assertEqual(location.name, 'Warehouse A')
        self.assertEqual(job.state, 'succeeded')

        job2 = self._make_sync_job()
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value=self._one_page_response([
                {'id': 'gid://shopify/Location/300', 'name': 'Warehouse A Renamed'},
            ]),
        ):
            Service._handle_inventory_location_sync(job2)
        location.invalidate_recordset()
        self.assertEqual(
            self.env['shopify.connector.location'].sudo().search_count([
                ('store_id', '=', self.store.id),
                ('shopify_location_gid', '=', 'gid://shopify/Location/300'),
            ]),
            1,
        )
        self.assertEqual(location.name, 'Warehouse A Renamed')

    def test_enqueue_location_sync_admission_service(self):
        """Sanctioned admission path (PR #182 comment 5025803697 item
        22.C) -- previously a dead handler reachable only through direct
        protected-field job creation. Hardened per comment 5028910116
        item 13: private method, explicit Operator/Administrator
        authority required."""
        self.env['shopify.connector.store.settings'].create({
            'store_id': self.store.id, 'inventory_domain_enabled': True,
        })
        self.store.write({'state': 'connected'})
        Service = self.env['shopify.connector.inventory.service']
        job = Service.with_user(
            self.user_operator
        )._enqueue_location_sync(self.store)
        self.assertEqual(job.job_type, 'inventory_location_sync')
        self.assertEqual(job.state, 'queued')

    def test_enqueue_location_sync_denied_when_domain_disabled(self):
        self.env['shopify.connector.store.settings'].create({
            'store_id': self.store.id, 'inventory_domain_enabled': False,
        })
        self.store.write({'state': 'connected'})
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(Exception):
            Service.with_user(self.user_operator)._enqueue_location_sync(
                self.store
            )

    def test_enqueue_location_sync_denied_for_auditor(self):
        self.env['shopify.connector.store.settings'].create({
            'store_id': self.store.id, 'inventory_domain_enabled': True,
        })
        self.store.write({'state': 'connected'})
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(Exception):
            Service.with_user(self.user_auditor)._enqueue_location_sync(
                self.store
            )

    def test_pagination_across_two_pages(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        page_one = {
            'data': {
                'locations': {
                    'edges': [{
                        'cursor': 'c1',
                        'node': {
                            'id': 'gid://shopify/Location/301', 'name': 'A',
                        },
                    }],
                    'pageInfo': {'hasNextPage': True},
                },
            },
        }
        page_two = self._one_page_response([
            {'id': 'gid://shopify/Location/302', 'name': 'B'},
        ])
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            side_effect=[page_one, page_two],
        ) as mocked_execute:
            Service._handle_inventory_location_sync(job)
        self.assertEqual(mocked_execute.call_count, 2)
        cached = self.env['shopify.connector.location'].sudo().search([
            ('store_id', '=', self.store.id),
            ('shopify_location_gid', 'in', [
                'gid://shopify/Location/301', 'gid://shopify/Location/302',
            ]),
        ])
        self.assertEqual(len(cached), 2)

    # ------------------------------------------------------------------
    # Fail-closed response/pagination-shape validation (PR #182 comment
    # 5028910116 item 10): a malformed or partial page must never be
    # silently treated as "zero locations, no next page."
    # ------------------------------------------------------------------

    def test_malformed_response_no_data_raises(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value={'errors': 'no data key'},
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_location_sync(job)
        job.invalidate_recordset()
        self.assertNotEqual(job.state, 'succeeded')

    def test_malformed_response_locations_not_a_dict_raises(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value={'data': {'locations': None}},
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_location_sync(job)
        job.invalidate_recordset()
        self.assertNotEqual(job.state, 'succeeded')

    def test_malformed_response_edges_not_a_list_raises(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value={
                'data': {'locations': {
                    'edges': 'not-a-list', 'pageInfo': {'hasNextPage': False},
                }},
            },
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_location_sync(job)
        job.invalidate_recordset()
        self.assertNotEqual(job.state, 'succeeded')

    def test_malformed_node_missing_gid_raises(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value={
                'data': {'locations': {
                    'edges': [{'cursor': 'c1', 'node': {'name': 'No GID'}}],
                    'pageInfo': {'hasNextPage': False},
                }},
            },
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_location_sync(job)
        job.invalidate_recordset()
        self.assertNotEqual(job.state, 'succeeded')

    def test_missing_page_info_raises(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value={'data': {'locations': {'edges': []}}},
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_location_sync(job)
        job.invalidate_recordset()
        self.assertNotEqual(job.state, 'succeeded')

    def test_invalid_has_next_page_type_raises(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value={
                'data': {'locations': {
                    'edges': [], 'pageInfo': {'hasNextPage': 'yes'},
                }},
            },
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_location_sync(job)
        job.invalidate_recordset()
        self.assertNotEqual(job.state, 'succeeded')

    def test_missing_next_cursor_when_has_next_page_true_raises(self):
        job = self._make_sync_job()
        Service = self.env['shopify.connector.inventory.service']
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value={
                'data': {'locations': {
                    'edges': [{
                        'node': {
                            'id': 'gid://shopify/Location/1', 'name': 'A',
                        },
                    }],
                    'pageInfo': {'hasNextPage': True},
                }},
            },
        ):
            with self.assertRaises(JobHandlerError):
                Service._handle_inventory_location_sync(job)
        job.invalidate_recordset()
        self.assertNotEqual(job.state, 'succeeded')
