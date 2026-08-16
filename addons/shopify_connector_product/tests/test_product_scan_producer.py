"""Batch 2 checkpoint 3 -- the product enumeration producer.

Every test drives a production route: the store action, the real cron entry
point, and the registered dispatcher handler. Transport is patched at
`execute_business`, the same seam the order scan's tests use, so no test can
reach Shopify even by accident.
"""

import json
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from ..models.shopify_connector_product_scan import (
    PRODUCT_SCAN_CRON_XMLID,
    PRODUCT_SCAN_MAX_PRODUCTS,
    PRODUCT_SCAN_OVERLAP,
    PRODUCT_SCAN_PAGE_LIMIT,
    PRODUCT_SCAN_PAGE_SIZE,
    PRODUCT_SCAN_TARGET,
)
from odoo.tools import mute_logger

VIEWS_ROOT = Path(__file__).resolve().parent.parent / 'views'
MODELS_ROOT = Path(__file__).resolve().parent.parent / 'models'


@tagged('post_install', '-at_install')
class TestProductScanProducer(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].sudo().create({
            'name': 'Product Scan Producer Store',
            'shop_domain': 'product-scan-producer.myshopify.com',
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
        cls.Job = cls.env['shopify.connector.job']
        cls.Scan = cls.env['shopify.connector.product.scan']
        cls.Dispatch = cls.env['shopify.connector.job.dispatch']
        cls.roles = {
            label: cls._role_user(label, xmlid)
            for label, xmlid in (
                ('auditor', 'group_shopify_connector_auditor'),
                ('operator', 'group_shopify_connector_operator'),
                ('admin', 'group_shopify_connector_admin'),
            )
        }

    @classmethod
    def _role_user(cls, label, xmlid):
        return cls.env['res.users'].create({
            'name': 'Product scan %s' % label,
            'login': 'product_scan_%s' % label,
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('shopify_connector_core.%s' % xmlid).id,
            ])],
        })

    # ------------------------------------------------------------------
    # transport fixtures
    # ------------------------------------------------------------------

    @contextmanager
    def _result(self, body):
        yield body

    def _page(self, nodes, has_next=False, end_cursor=None, cursor_prefix='c'):
        return {
            'data': {'products': {
                'edges': [
                    {
                        'cursor': '%s-%s' % (cursor_prefix, index),
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

    def _node(self, suffix, updated_at='2026-07-17T12:00:00Z',
              status='ACTIVE'):
        return {
            'id': 'gid://shopify/Product/%s' % suffix,
            'updatedAt': updated_at,
            'status': status,
        }

    def _patch_scan(self, bodies):
        """Patch the transport and record the variables each page was sent."""
        bodies = iter(bodies)
        sent = []

        def fake_execute(_client, _job, _store, query, variables=None):
            sent.append(dict(variables or {}))
            self.assertIn('products(', query)
            return self._result(next(bodies))

        client = self.env['shopify.connector.api.client']
        return patch.object(
            type(client), 'execute_business', new=fake_execute,
        ), sent

    def _run_scan(self, bodies, job=None):
        job = job or self.store.with_user(
            self.roles['operator']
        ).action_sync_products_now()
        patcher, sent = self._patch_scan(bodies)
        with patcher:
            self.Dispatch._handle_product_import_scan(job)
        return job, sent

    def _children(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_sync'),
        ])

    def _scans(self):
        return self.Job.search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'product_import_scan'),
        ])

    # ------------------------------------------------------------------
    # §8.1 -- admission routes
    # ------------------------------------------------------------------

    def test_manual_route_enqueues_the_real_scan_job(self):
        job = self.store.with_user(
            self.roles['operator']
        ).action_sync_products_now()
        self.assertEqual(job.job_type, 'product_import_scan')
        self.assertEqual(job.job_source, 'manual_sync')
        self.assertEqual(job.shopify_target_gid, PRODUCT_SCAN_TARGET)
        self.assertEqual(job.state, 'queued')

    def test_scheduled_route_enqueues_the_real_scan_job(self):
        self.settings.write({'product_scheduled_sync_enabled': True})
        self.env['shopify.connector.store']._cron_enqueue_product_scans()
        scans = self._scans()
        self.assertEqual(len(scans), 1)
        self.assertEqual(scans.job_source, 'scheduled_sync')

    def test_scheduling_off_admits_nothing(self):
        self.settings.write({'product_scheduled_sync_enabled': False})
        self.env['shopify.connector.store']._cron_enqueue_product_scans()
        self.assertFalse(self._scans())

    def test_exactly_one_non_terminal_scan_per_store(self):
        first = self.store.with_user(
            self.roles['operator']
        ).action_sync_products_now()
        self.settings.write({'product_scheduled_sync_enabled': True})
        self.env['shopify.connector.store']._cron_enqueue_product_scans()
        again = self.store.with_user(
            self.roles['admin']
        ).action_sync_products_now()
        self.assertEqual(again, first)
        self.assertEqual(len(self._scans()), 1)

    def test_manual_route_is_role_gated(self):
        with self.assertRaises(AccessError):
            self.store.with_user(
                self.roles['auditor']
            ).action_sync_products_now()

    def test_domain_direction_and_state_gates(self):
        self.settings.write({'product_domain_enabled': False})
        with self.assertRaises(UserError):
            self.store.with_user(
                self.roles['operator']
            ).action_sync_products_now()
        self.settings.write({
            'product_domain_enabled': True,
            'product_first_sync_source': 'odoo_source',
        })
        with self.assertRaises(UserError):
            self.store.with_user(
                self.roles['operator']
            ).action_sync_products_now()
        self.settings.write({'product_first_sync_source': 'shopify_source'})
        self.store.sudo().write({'state': 'reconnect_needed'})
        with self.assertRaises(UserError):
            self.store.with_user(
                self.roles['operator']
            ).action_sync_products_now()
        self.assertFalse(self._scans())

    def test_no_view_calls_the_importer_directly(self):
        """Structural: about what the views INVOKE, not what they mention.

        A substring check over the raw file is defeated by a comment saying
        the importer is deliberately not called -- and, worse, would pass for
        a view that invoked it under a different spelling. This reads the
        `name` of every button and every `object`-type element instead.
        """
        from lxml import etree
        for view_file in VIEWS_ROOT.glob('*.xml'):
            root = etree.parse(str(view_file)).getroot()
            invoked = {
                node.get('name')
                for node in root.iter('button')
                if node.get('name')
            }
            self.assertNotIn(
                'import_product_sync', invoked,
                '%s invokes the per-product importer directly' % (
                    view_file.name,
                ),
            )
        controls = etree.parse(str(
            VIEWS_ROOT / 'shopify_connector_product_controls_views.xml'
        )).getroot()
        self.assertIn(
            'action_sync_products_now',
            {n.get('name') for n in controls.iter('button')},
        )

    # ------------------------------------------------------------------
    # §8.1 -- enumeration behaviour
    # ------------------------------------------------------------------

    def test_initial_scan_has_no_time_lower_bound(self):
        """§8.1.8: an old, never-edited product must not be silently omitted."""
        _job, sent = self._run_scan([
            self._page([self._node('1', '2019-01-01T00:00:00Z')]),
        ])
        query = sent[0]['query']
        self.assertNotIn(
            "updated_at:>", query,
            'The first scan must enumerate the whole catalog, not a recent '
            'window.',
        )
        self.assertIn("updated_at:<=", query)
        self.assertEqual(len(self._children()), 1)

    def test_initial_scan_admits_archived_and_draft_products(self):
        self._run_scan([
            self._page([
                self._node('10', status='ACTIVE'),
                self._node('11', status='ARCHIVED'),
                self._node('12', status='DRAFT'),
                # 2026-07 adds UNLISTED; the scan carries status as an opaque
                # string precisely so a fourth value is not a crash.
                self._node('13', status='UNLISTED'),
            ]),
        ])
        self.assertEqual(len(self._children()), 4)

    def test_incremental_scan_reaches_behind_the_checkpoint(self):
        checkpoint = fields.Datetime.to_datetime('2026-07-17 12:00:00')
        self.settings.sudo().write({
            'product_last_import_checkpoint_at': checkpoint,
        })
        _job, sent = self._run_scan([self._page([])])
        query = sent[0]['query']
        expected = (checkpoint - PRODUCT_SCAN_OVERLAP).strftime(
            '%Y-%m-%dT%H:%M:%S'
        )
        self.assertIn(
            "updated_at:>'%sZ'" % expected, query,
            'the incremental window must overlap the checkpoint, or a write '
            'landing in the same second is lost for good',
        )

    def test_pagination_advances_by_server_cursor(self):
        _job, sent = self._run_scan([
            self._page([self._node('1')], has_next=True, end_cursor='CUR-1'),
            self._page([self._node('2')], cursor_prefix='d'),
        ])
        self.assertEqual(sent[0]['after'], False)
        self.assertEqual(
            sent[1]['after'], 'CUR-1',
            'the second page must be requested with the cursor the SERVER '
            'issued, never one derived locally',
        )
        self.assertEqual(len(self._children()), 2)

    def test_non_progressing_cursor_fails_closed(self):
        with self.assertRaises(JobHandlerError):
            self._run_scan([
                self._page([self._node('1')], has_next=True, end_cursor=None),
            ])

    def test_repeated_cursor_fails_closed(self):
        with self.assertRaises(JobHandlerError):
            self._run_scan([
                self._page([self._node('1')], has_next=True,
                           end_cursor='CUR-1'),
                self._page([self._node('2')], cursor_prefix='c'),
            ])

    def test_duplicate_identity_fails_closed(self):
        with self.assertRaises(JobHandlerError):
            self._run_scan([
                self._page([self._node('1'), self._node('1')]),
            ])

    def test_malformed_shapes_fail_closed(self):
        malformed = (
            {'data': {}},
            {'data': {'products': {'edges': 'nope', 'pageInfo': {}}}},
            {'data': {'products': {'edges': [{'node': {}}],
                                   'pageInfo': {}}}},
            {'data': {'products': {
                'edges': [{'cursor': 'c', 'node': {'id': 'gid://x'}}],
                'pageInfo': {},
            }}},
        )
        for body in malformed:
            job = self.store.sudo()._enqueue_product_scan('manual_sync')
            patcher, _sent = self._patch_scan([body])
            with self.assertRaises(JobHandlerError, msg=json.dumps(body)):
                with patcher:
                    self.Dispatch._handle_product_import_scan(job)
            job.with_user(self.roles['admin']).action_cancel(
                reason='malformed-shape fixture cleanup',
            )

    def test_page_ceiling_fails_visibly(self):
        pages = [
            self._page([self._node(str(index))], has_next=True,
                       end_cursor='CUR-%d' % index,
                       cursor_prefix='p%d' % index)
            for index in range(PRODUCT_SCAN_PAGE_LIMIT + 1)
        ]
        with self.assertRaises(JobHandlerError) as ceiling:
            self._run_scan(pages)
        reason = ceiling.exception.reason
        # Batch 2 correction (F11): the refusal must state the LIMIT, its
        # CONSEQUENCE and the fact that retrying will not help. "The product
        # scan page ceiling was exceeded" told an operator none of those, and
        # the honest answer is not obtainable from anywhere else on screen.
        self.assertIn(str(PRODUCT_SCAN_PAGE_SIZE), reason)
        self.assertIn(str(PRODUCT_SCAN_PAGE_LIMIT), reason)
        self.assertIn(str(PRODUCT_SCAN_MAX_PRODUCTS), reason)
        self.assertIn('NOTHING WAS IMPORTED', reason)
        self.assertIn('has NOT moved', reason)
        self.assertIn('same place', reason)
        self.assertEqual(
            PRODUCT_SCAN_MAX_PRODUCTS,
            PRODUCT_SCAN_PAGE_SIZE * PRODUCT_SCAN_PAGE_LIMIT,
        )
        self.assertEqual(PRODUCT_SCAN_MAX_PRODUCTS, 20000)
        # ...and it really is a fail-closed refusal: no checkpoint moved.
        self.settings.invalidate_recordset()
        self.assertFalse(self.settings.product_last_import_checkpoint_at)
        self.assertFalse(self.settings.product_last_import_success_at)

    # ------------------------------------------------------------------
    # Batch 2 correction (F7): "scheduled" means the real cron is on.
    # ------------------------------------------------------------------

    def test_scheduled_state_is_false_while_the_real_cron_is_disabled(self):
        """The store flag is an INTENTION; `ir.cron.active` is the fact.

        `_cron_enqueue_product_scans` is the only thing that ever admits a
        scheduled scan, and it runs only while the cron this module installed
        is active. An administrator can disable that cron in Settings ->
        Technical -> Scheduled Actions, and the store page went on saying
        "Scheduled product import" was on -- which reads as "the catalog is
        being kept current" while nothing is enqueued at all.
        """
        cron = self.env.ref(PRODUCT_SCAN_CRON_XMLID)
        self.settings.write({'product_scheduled_sync_enabled': True})
        self.store.invalidate_recordset()
        self.assertTrue(cron.active)
        self.assertTrue(self.store.product_sync_scheduled)

        cron.sudo().write({'active': False})
        self.store.invalidate_recordset()
        self.assertFalse(
            self.store.product_sync_scheduled,
            'the store still claims scheduled product import while the cron '
            'that would perform it is disabled',
        )
        self.assertTrue(
            self.store.product_sync_domain_enabled,
            'the domain is still enabled; only the schedule claim changed',
        )

        cron.sudo().write({'active': True})
        self.store.invalidate_recordset()
        self.assertTrue(self.store.product_sync_scheduled)

    def test_the_domain_flag_still_governs_the_scheduled_claim(self):
        self.settings.write({
            'product_domain_enabled': False,
            'product_scheduled_sync_enabled': True,
        })
        self.store.invalidate_recordset()
        self.assertFalse(self.store.product_sync_scheduled)

    def test_manual_import_survives_a_disabled_cron_and_stays_role_gated(self):
        """Truthfulness must not remove the manual route, or its guard."""
        self.env.ref(PRODUCT_SCAN_CRON_XMLID).sudo().write({'active': False})
        self.settings.write({'product_scheduled_sync_enabled': True})
        self.store.invalidate_recordset()
        self.assertFalse(self.store.product_sync_scheduled)
        job = self.store.with_user(
            self.roles['operator']
        ).action_sync_products_now()
        self.assertTrue(job)
        self.assertEqual(job.job_type, 'product_import_scan')
        with self.assertRaises(AccessError):
            self.store.with_user(
                self.roles['auditor']
            ).action_sync_products_now()

    def test_an_absent_cron_reads_as_not_scheduled_rather_than_as_scheduled(self):
        """Fail closed. An unprovable scheduler is a disabled one."""
        Store = self.env['shopify.connector.store']
        self.assertFalse(
            Store._connector_scheduler_is_active(
                'shopify_connector_product.ir_cron_that_does_not_exist',
            ),
        )
        # A resolvable external id that is not a cron at all is also refused,
        # rather than read for an `active` field that would mean something
        # else entirely.
        self.assertFalse(
            Store._connector_scheduler_is_active(
                'shopify_connector_core.model_shopify_connector_store',
            ),
        )

    # ------------------------------------------------------------------
    # §8.1 -- child admission and checkpoint coherence
    # ------------------------------------------------------------------

    def test_child_payload_hash_is_the_exact_remote_stamp(self):
        self._run_scan([
            self._page([self._node('55', '2026-07-19T08:30:00Z')]),
        ])
        child = self._children()
        self.assertEqual(len(child), 1)
        self.assertEqual(child.job_type, 'product_import_sync')
        self.assertEqual(
            child.shopify_target_gid, 'gid://shopify/Product/55',
        )
        self.assertEqual(
            child.payload_hash, '2026-07-19T08:30:00Z',
            'the child identity must be the verbatim remote stamp',
        )

    @mute_logger('odoo.sql_db')
    def test_repeated_enumeration_of_an_unchanged_product_coalesces(self):
        node = self._node('77', '2026-07-19T08:30:00Z')
        self._run_scan([self._page([node])])
        first = self._children()
        self.assertEqual(len(first), 1)
        # Second scan, same product, same stamp: the child must collide with
        # the work already queued rather than duplicate it. The first scan is
        # cancelled through the sanctioned action so a second one may be
        # admitted -- the state machine refuses queued -> succeeded outright.
        self._scans().with_user(self.roles['admin']).action_cancel(
            reason='making room for a second scan in this test',
        )
        self._run_scan([self._page([node])])
        self.assertEqual(self._children(), first)

    def test_a_failed_scan_does_not_advance_the_checkpoint(self):
        """§8.1.13, the property that makes a retry safe.

        The scan raises on its second page, after the first page's children
        were already admitted. The dispatcher's savepoint must discard the
        partial work AND leave the checkpoint where it was, so the next run
        re-covers the ground this one abandoned.
        """
        self.assertFalse(self.settings.product_last_import_checkpoint_at)
        job = self.store.sudo()._enqueue_product_scan('manual_sync')
        patcher, _sent = self._patch_scan([
            self._page([self._node('1')], has_next=True, end_cursor='CUR-1'),
            {'data': {'products': {'edges': 'malformed', 'pageInfo': {}}}},
        ])
        with self.assertRaises(JobHandlerError):
            with patcher:
                self.Dispatch._handle_product_import_scan(job)
        self.settings.invalidate_recordset()
        self.assertFalse(
            self.settings.product_last_import_checkpoint_at,
            'a scan that did not finish must not claim ground it never '
            'covered',
        )
        self.assertFalse(self._children())

    def test_a_successful_scan_advances_checkpoint_and_success_stamp(self):
        self._run_scan([
            self._page([self._node('1', '2026-07-19T08:30:00Z')]),
        ])
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.product_last_import_checkpoint_at)
        self.assertTrue(self.settings.product_last_import_success_at)

    def test_the_scan_performs_no_shopify_mutation(self):
        source = (
            MODELS_ROOT / 'shopify_connector_product_scan.py'
        ).read_text(encoding='utf-8')
        import ast
        tree = ast.parse(source)
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
        }
        # Purely structural: about the calls the module makes. An earlier
        # version also asserted the word 'mutation' was absent from the body,
        # which any comment using it defeats -- including one added by a
        # mutation-testing run, which is exactly how that coupling surfaced.
        for forbidden in (
            'execute_mutation', 'import_product_sync', '_send',
            '_send_lifecycle', '_send_token_exchange',
        ):
            self.assertNotIn(forbidden, called, forbidden)
        self.assertIn(
            'execute_business', called,
            'the scan must read through the existing governed client',
        )
