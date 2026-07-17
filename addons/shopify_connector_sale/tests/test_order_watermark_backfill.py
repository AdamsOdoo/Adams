from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_order_scan import ORDER_SCAN_OVERLAP_MINUTES
from .test_order_import_mapping import OrderImportCase


class TestOrderWatermarkBackfill(OrderImportCase):

    @contextmanager
    def _result(self, body):
        yield body

    def _body(self, entries, has_next=False, end_cursor=None):
        return {'data': {'orders': {
            'edges': [
                {'cursor': cursor, 'node': node}
                for cursor, node in entries
            ],
            'pageInfo': {
                'hasNextPage': has_next,
                'endCursor': end_cursor,
            },
        }}}

    def _node(self, suffix, updated='2026-07-17T12:00:00Z', **extra):
        node = {
            'id': 'gid://shopify/Order/%s' % suffix,
            'updatedAt': updated,
            'createdAt': '2026-07-17T10:00:00Z',
            'edited': False,
            'test': False,
            'cancelledAt': None,
            'displayFinancialStatus': 'PAID',
        }
        node.update(extra)
        return node

    def _patch_bodies(self, bodies):
        bodies = iter(bodies)

        def execute(_client, _job, _store, _query, variables=None):
            body = next(bodies)
            if isinstance(body, Exception):
                raise body
            return self._result(body)

        client = self.env['shopify.connector.api.client']
        return patch.object(type(client), 'execute_business', new=execute)

    def _draft_order(self, label):
        return self.env['sale.order'].create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
            'payment_term_id': self.payment_term.id,
            'origin': label,
        })

    def _binding(self, suffix, updated, status='active'):
        return self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Order/%s' % suffix,
            'sale_order_id': self._draft_order(suffix).id,
            'status': status,
            'shopify_updated_at_snapshot': fields.Datetime.to_datetime(updated),
        })

    def test_watermark_uses_thirty_minute_overlap(self):
        checkpoint = datetime(2026, 7, 17, 12, 0, 0)
        self.settings.write({
            'sale_order_last_import_checkpoint_at': checkpoint,
        })
        start = self.env[
            'shopify.connector.order.scan'
        ]._incremental_start(self.settings)
        self.assertEqual(
            start, checkpoint - timedelta(minutes=ORDER_SCAN_OVERLAP_MINUTES),
        )
        self.assertEqual(ORDER_SCAN_OVERLAP_MINUTES, 30)

    def test_watermark_advances_only_after_complete_pagination(self):
        old = datetime(2026, 7, 17, 9, 0, 0)
        self.settings.write({'sale_order_last_import_checkpoint_at': old})
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        first = self._body([
            ('cursor-a', self._node('PageA', '2026-07-17T11:00:00Z')),
        ], has_next=True, end_cursor='page-a-end')
        second = self._body([
            ('cursor-b', self._node('PageB', '2026-07-17T12:00:00Z')),
        ])
        with self._patch_bodies([first, second]):
            counts = self.env['shopify.connector.order.scan'].run_scan(job)
        self.settings.invalidate_recordset([
            'sale_order_last_import_checkpoint_at',
        ])
        self.assertEqual(counts['pages'], 2)
        self.assertEqual(
            self.settings.sale_order_last_import_checkpoint_at,
            datetime(2026, 7, 17, 12, 0, 0),
        )

    def test_partial_page_failure_holds_watermark_and_remains_resumable(self):
        old = datetime(2026, 7, 17, 9, 0, 0)
        self.settings.write({'sale_order_last_import_checkpoint_at': old})
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        first = self._body([
            ('cursor-first', self._node('PartialFirst')),
        ], has_next=True, end_cursor='partial-end')
        malformed = {'data': {'orders': None}}
        with self._patch_bodies([first, malformed]):
            with self.assertRaises(JobHandlerError):
                self.env['shopify.connector.order.scan'].run_scan(job)
        self.settings.invalidate_recordset([
            'sale_order_last_import_checkpoint_at',
        ])
        self.assertEqual(
            self.settings.sale_order_last_import_checkpoint_at, old,
        )
        self.assertEqual(self.Job.search_count([
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', 'gid://shopify/Order/PartialFirst'),
        ]), 1)

    def test_preview_classifies_all_buckets_and_creates_nothing(self):
        self._binding('Duplicate', '2026-07-17 12:00:00')
        self._binding('Changed', '2026-07-17 11:00:00')
        self._binding('Review', '2026-07-17 11:00:00', status='review')
        nodes = [
            ('c-new', self._node('New')),
            ('c-test', self._node('Test', test=True)),
            ('c-cancel', self._node(
                'Cancelled', cancelledAt='2026-07-17T11:00:00Z',
            )),
            ('c-unknown', self._node('Unknown', displayFinancialStatus=None)),
            ('c-dup', self._node('Duplicate')),
            ('c-change', self._node('Changed')),
            ('c-review', self._node('Review')),
        ]
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        jobs_before = self.Job.search_count([])
        logs_before = self.JobLog.search_count([])
        orders_before = self.env['sale.order'].search_count([])
        bindings_before = self.Binding.search_count([])
        for role in ('auditor', 'operator', 'reviewer'):
            user = self.roles[role]
            with self.assertRaises(AccessError, msg=role):
                self.env[
                    'shopify.connector.order.scan'
                ].with_user(user).preview_backfill(
                    self.store.with_user(user), '2026-07-17 00:00:00',
                    '2026-07-18 00:00:00', job.with_user(user),
                )
            self.assertEqual(self.Job.search_count([]), jobs_before)
            self.assertEqual(self.JobLog.search_count([]), logs_before)
            self.assertEqual(
                self.env['sale.order'].search_count([]), orders_before,
            )
            self.assertEqual(self.Binding.search_count([]), bindings_before)
        with self._patch_bodies([self._body(nodes)]):
            result = self.env[
                'shopify.connector.order.scan'
            ].preview_backfill(
                self.store, '2026-07-17 00:00:00',
                '2026-07-18 00:00:00', job,
            )
        self.assertEqual({key: result[key] for key in (
            'new', 'changed', 'duplicate', 'skipped', 'needs_review',
            'enqueued', 'collided', 'pages',
        )}, {
            'new': 1, 'changed': 1, 'duplicate': 1, 'skipped': 2,
            'needs_review': 2, 'enqueued': 0, 'collided': 0, 'pages': 1,
        })
        self.assertRegex(result['confirmation_token'], r'^[0-9a-f]{64}$')
        self.assertRegex(result['evidence_digest'], r'^[0-9a-f]{64}$')
        self.assertEqual(self.Job.search_count([]), jobs_before)
        self.assertEqual(self.JobLog.search_count([]), logs_before)
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)
        self.assertEqual(self.Binding.search_count([]), bindings_before)

    def test_confirm_requires_exact_current_preview_token_then_enqueues(self):
        nodes = [('c-new', self._node('ConfirmedBackfill'))]
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        Scan = self.env['shopify.connector.order.scan']
        with self._patch_bodies([self._body(nodes)]):
            preview = Scan.preview_backfill(
                self.store, '2026-07-17 00:00:00',
                '2026-07-18 00:00:00', job,
            )
        jobs_before = self.Job.search_count([])
        with self._patch_bodies([self._body(nodes)]):
            result = Scan.confirm_backfill(
                self.store, '2026-07-17 00:00:00',
                '2026-07-18 00:00:00', job,
                confirmation=preview['confirmation_token'],
            )
        self.assertEqual(result['enqueued'], 1)
        self.assertEqual(self.Job.search_count([]), jobs_before + 1)
        entity = self.Job.search([
            ('shopify_target_gid', '=', 'gid://shopify/Order/ConfirmedBackfill'),
        ])
        self.assertEqual(entity.job_source, 'manual_sync')

    def test_stale_or_boolean_confirmation_never_enqueues(self):
        nodes = [('c-new', self._node('StaleToken'))]
        changed = nodes + [('c-newer', self._node('NewerToken'))]
        same_count_changed_identity = [(
            'c-replaced', self._node('ReplacedToken'),
        )]
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        Scan = self.env['shopify.connector.order.scan']
        with self._patch_bodies([self._body(nodes)]):
            preview = Scan.preview_backfill(
                self.store, '2026-07-17 00:00:00',
                '2026-07-18 00:00:00', job,
            )
        before = self.Job.search_count([])
        for confirmation, body in (
            (True, self._body(nodes)),
            (preview['confirmation_token'], self._body(changed)),
            (
                preview['confirmation_token'],
                self._body(same_count_changed_identity),
            ),
        ):
            with self._patch_bodies([body]):
                with self.assertRaises(UserError):
                    Scan.confirm_backfill(
                        self.store, '2026-07-17 00:00:00',
                        '2026-07-18 00:00:00', job,
                        confirmation=confirmation,
                    )
            self.assertEqual(self.Job.search_count([]), before)

        self.store.sudo().write({
            'connection_generation': self.store.connection_generation + 1,
        })
        with self._patch_bodies([self._body(nodes)]):
            with self.assertRaises(UserError):
                Scan.confirm_backfill(
                    self.store, '2026-07-17 00:00:00',
                    '2026-07-18 00:00:00', job,
                    confirmation=preview['confirmation_token'],
                )
        self.assertEqual(self.Job.search_count([]), before)

    def test_read_all_orders_honesty_never_silently_truncates(self):
        Scan = self.env['shopify.connector.order.scan']
        job = self._job(
            job_type='order_import_scan', target='scan:order', state='running',
        )
        old = fields.Datetime.now() - timedelta(days=61)
        with self.assertRaisesRegex(UserError, 'Partner Dashboard'):
            Scan.preview_backfill(
                self.store, old, fields.Datetime.now(), job,
            )
        self.store.sudo().write({
            'granted_scopes': '["read_orders", "read_all_orders"]',
        })
        with self._patch_bodies([self._body([])]):
            result = Scan.preview_backfill(
                self.store, old, fields.Datetime.now(), job,
            )
        self.assertEqual(result['pages'], 1)
        self.assertEqual(result['enqueued'], 0)
