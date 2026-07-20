from unittest.mock import patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestInventoryLocationCacheSync(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Location Cache Sync Test Store',
            'shop_domain': 'location-cache-sync-test.myshopify.com',
            'api_version': '2026-07',
        })
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
