from contextlib import contextmanager
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .test_order_import_mapping import OrderImportCase
from odoo.tools import mute_logger


class TestOrderScanTriggers(OrderImportCase):

    @contextmanager
    def _result(self, body):
        yield body

    def _scan_body(self, nodes, has_next=False, end_cursor=None):
        return {
            'data': {'orders': {
                'edges': [
                    {
                        'cursor': 'cursor-%d' % index,
                        'node': node,
                    }
                    for index, node in enumerate(nodes)
                ],
                'pageInfo': {
                    'hasNextPage': has_next,
                    'endCursor': end_cursor,
                },
            }},
        }

    def _node(self, suffix, **extra):
        node = {
            'id': 'gid://shopify/Order/%s' % suffix,
            'updatedAt': '2026-07-17T12:00:00Z',
            'createdAt': '2026-07-17T10:00:00Z',
            'edited': False,
            'test': False,
            'cancelledAt': None,
            'displayFinancialStatus': 'PAID',
        }
        node.update(extra)
        return node

    def _patch_scan(self, bodies, sent=None):
        bodies = iter(bodies)
        sent = sent if sent is not None else []

        def fake_execute(_client, _job, _store, _query, variables=None):
            sent.append(dict(variables or {}))
            return self._result(next(bodies))

        client = self.env['shopify.connector.api.client']
        return patch.object(
            type(client), 'execute_business', new=fake_execute,
        )

    def test_scan_uses_graphql_null_then_the_server_cursor(self):
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        sent = []
        bodies = [
            self._scan_body(
                [self._node('CursorFirst')],
                has_next=True,
                end_cursor='CUR-1',
            ),
            self._scan_body([]),
        ]
        with self._patch_scan(bodies, sent=sent):
            self.env['shopify.connector.order.scan'].run_scan(job)
        self.assertIsNone(
            sent[0]['after'],
            'the first GraphQL page must send JSON null for an optional '
            'String cursor, never JSON false',
        )
        self.assertEqual(
            sent[1]['after'], 'CUR-1',
            'the second page must use the cursor Shopify returned',
        )

    def test_manual_store_trigger_is_role_gated_enqueue_only_and_idempotent(self):
        for role in ('auditor', 'reviewer'):
            with self.assertRaises(AccessError, msg=role):
                self.store.with_user(
                    self.roles[role]
                ).action_sync_orders_now()
        first = self.store.with_user(
            self.roles['operator']
        ).action_sync_orders_now()
        second = self.store.with_user(
            self.roles['admin']
        ).action_sync_orders_now()
        self.assertEqual(first, second)
        self.assertEqual(first.job_type, 'order_import_scan')
        self.assertEqual(first.job_source, 'manual_sync')
        self.assertEqual(first.shopify_target_gid, 'scan:order')
        self.assertEqual(first.state, 'queued')
        self.assertFalse(self.Binding.search([]))

    def test_selected_binding_trigger_is_enqueue_only_and_collision_safe(self):
        binding = self.Importer._apply_import(
            self.store, self._payload('gid://shopify/Order/Selected'),
        )
        with self.assertRaises(AccessError):
            binding.with_user(self.roles['auditor']).action_sync_selected()
        first = binding.with_user(
            self.roles['operator']
        ).action_sync_selected()
        second = binding.with_user(
            self.roles['admin']
        ).action_sync_selected()
        self.assertEqual(first, second)
        self.assertEqual(first.job_type, 'order_import_sync')
        self.assertEqual(first.shopify_target_gid, binding.shopify_gid)
        self.assertEqual(self.Binding.search_count([
            ('id', '=', binding.id),
        ]), 1)

    @mute_logger('odoo.addons.shopify_connector_sale.models.shopify_connector_order_scan')
    def test_cron_requires_both_flags_and_connected_store(self):
        self.settings.write({'order_scheduled_sync_enabled': False})
        self.env['shopify.connector.store']._cron_enqueue_order_scans()
        self.assertFalse(self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ]))

        self.settings.write({'order_scheduled_sync_enabled': True})
        self.env['shopify.connector.store']._cron_enqueue_order_scans()
        jobs = self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs.job_source, 'scheduled_sync')

        self.settings.write({'order_scheduled_sync_enabled': False})
        self.env['shopify.connector.store']._cron_enqueue_order_scans()
        self.assertEqual(self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ]), 1)

        other_store = self.env['shopify.connector.store'].create({
            'name': 'Order Cron Continue Store',
            'shop_domain': 'order-cron-continue.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
        })
        self.env['shopify.connector.store.settings'].create({
            'store_id': other_store.id,
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        StoreType = type(self.store)
        real_enqueue = StoreType._enqueue_order_scan
        visited = []

        def fail_one_store(record, source):
            visited.append(record.id)
            if record == self.store:
                raise UserError('one store is temporarily unavailable')
            return real_enqueue(record, source)

        with patch.object(
            StoreType, '_enqueue_order_scan', new=fail_one_store,
        ):
            result = self.env[
                'shopify.connector.store'
            ]._cron_enqueue_order_scans()
        self.assertIsNone(result)
        self.assertTrue({self.store.id, other_store.id}.issubset(visited))
        self.assertEqual(self.Job.search_count([
            ('store_id', '=', other_store.id),
            ('job_type', '=', 'order_import_scan'),
            ('state', '=', 'queued'),
        ]), 1)
        self.assertTrue(jobs.exists())

        jobs.sudo().write({'state': 'cancelled'})
        self.settings.write({
            'sale_domain_enabled': False,
            'order_scheduled_sync_enabled': True,
        })
        self.env['shopify.connector.store']._cron_enqueue_order_scans()
        self.assertEqual(self.Job.search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'order_import_scan'),
        ]), 1)

    def test_scan_enumerates_and_enqueues_but_never_imports_inline(self):
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        body = self._scan_body([
            self._node('ScanNew'),
            self._node('ScanTest', test=True),
            self._node('ScanCancelled', cancelledAt='2026-07-17T11:00:00Z'),
            self._node('ScanUnknown', displayFinancialStatus=None),
        ])
        with self._patch_scan([body]):
            with patch.object(
                type(self.Importer), '_apply_import',
                side_effect=AssertionError('scan imported inline'),
            ) as importer:
                counts = self.env[
                    'shopify.connector.order.scan'
                ].run_scan(job)
        self.assertEqual(importer.call_count, 0)
        self.assertEqual(counts['new'], 1)
        self.assertEqual(counts['skipped'], 2)
        self.assertEqual(counts['needs_review'], 1)
        self.assertEqual(counts['enqueued'], 2)
        self.assertEqual(self.Job.search_count([
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', 'in', (
                'gid://shopify/Order/ScanNew',
                'gid://shopify/Order/ScanUnknown',
            )),
        ]), 2)
        logs = self.JobLog.search([
            ('job_id', '=', job.id), ('event_type', '=', 'note'),
        ])
        self.assertEqual(len(logs), 2)
        self.assertIn('enumerated', logs[0].message.lower())

    def test_pagination_and_duplicate_edge_fail_closed(self):
        Scan = self.env['shopify.connector.order.scan']
        seen_cursors = set()
        seen_gids = set()
        connection = self._scan_body([
            self._node('One'), self._node('Two'),
        ])['data']['orders']
        page = Scan._validate_page(connection, seen_cursors, seen_gids)
        self.assertEqual(len(page['nodes']), 2)
        with self.assertRaises(JobHandlerError) as repeated:
            Scan._validate_page(connection, seen_cursors, seen_gids)
        self.assertEqual(
            repeated.exception.error_class, 'data_shape_schema_mismatch',
        )

    def test_store_progress_helpers_are_nonstored_and_state_accurate(self):
        self._job(target='gid://shopify/Order/PendingCount')
        self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_dispatch_selftest',
            'state': 'failed_final',
            'payload_hash': 'failed-count',
        })
        self.store.invalidate_recordset([
            'pending_job_count', 'failed_job_count',
        ])
        self.assertGreaterEqual(self.store.pending_job_count, 1)
        self.assertGreaterEqual(self.store.failed_job_count, 1)
        self.assertFalse(self.store._fields['pending_job_count'].store)
        self.assertFalse(self.store._fields['failed_job_count'].store)

    def test_disconnected_store_and_disabled_domain_refuse_manual_scan(self):
        binding = self.Importer._apply_import(
            self.store, self._payload('gid://shopify/Order/DisabledManual'),
        )
        self.store.sudo().write({'state': 'disconnected'})
        with self.assertRaises(UserError):
            self.store.action_sync_orders_now()
        with self.assertRaises(UserError):
            binding.action_sync_selected()
        self.store.sudo().write({'state': 'connected'})
        self.settings.write({'sale_domain_enabled': False})
        with self.assertRaises(UserError):
            self.store.action_sync_orders_now()
        with self.assertRaises(UserError):
            binding.action_sync_selected()
