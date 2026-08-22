import hashlib
from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_sale_webhook import (
    ORDER_WEBHOOK_TOPICS,
    canonical_shopify_gid,
)


@tagged('post_install', '-at_install')
class TestShopifyConnectorSaleWebhook(TransactionCase):
    """Exercise the W1 envelope -> order importer production seam."""

    def _store(self, suffix, generation=0):
        store = self.env['shopify.connector.store'].create({
            'name': 'Order webhook %s' % suffix,
            'shop_domain': 'order-webhook-%s.myshopify.com' % suffix,
            'api_version': SHOPIFY_API_VERSION,
            'state': 'connected',
        })
        if generation:
            store.sudo().write({'connection_generation': generation})
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id,
            'sale_domain_enabled': True,
        })
        return store

    def _delivery(
        self, store, suffix, gid, topic='orders/updated', source_updated_at=None,
        identity_id=None, payload_body_suffix=None,
    ):
        source_updated_at = source_updated_at or fields.Datetime.now()
        identity_id = identity_id if identity_id is not None else gid.rsplit('/', 1)[-1]
        payload_body_suffix = payload_body_suffix or suffix
        return self.env[
            'shopify.connector.webhook.delivery'
        ]._ingest(
            store,
            delivery_id='order-webhook-delivery-%s' % suffix,
            event_id='order-webhook-event-%s' % suffix,
            topic=topic,
            shop_domain=store.shop_domain,
            api_version=SHOPIFY_API_VERSION,
            triggered_at=fields.Datetime.now(),
            source_updated_at=source_updated_at,
            payload_digest=hashlib.sha256(
                ('order-webhook-body-%s' % payload_body_suffix).encode('utf-8'),
            ).hexdigest(),
            payload_size=64,
            payload_identity={
                'id': identity_id,
                'admin_graphql_api_id': gid,
            },
        )[0]

    def test_registry_activates_only_assessed_order_topics(self):
        registry = self.env['shopify.connector.webhook.registry']
        active = set(registry.allowed_topics())
        self.assertTrue(set(ORDER_WEBHOOK_TOPICS).issubset(active))
        self.assertNotIn('orders/delete', active)
        self.assertEqual(
            registry.topic_spec('orders/updated')['handler'],
            'order_import_sync',
        )
        self.assertEqual(
            registry.topic_spec('orders/updated')['include_fields'],
            ['admin_graphql_api_id', 'updated_at'],
        )

    def test_exact_gid_requires_explicit_graphql_identity_and_consistent_id(self):
        gid = 'gid://shopify/Order/9001'
        self.assertEqual(canonical_shopify_gid(gid, 'Order'), gid)
        self.assertFalse(canonical_shopify_gid(
            'gid://shopify/Order/9001/extra', 'Order',
        ))
        registry = self.env['shopify.connector.webhook.registry']
        self.assertEqual(
            registry._order_gid_from_delivery(SimpleNamespace(
                resource_identity={
                    'id': '9001', 'admin_graphql_api_id': gid,
                },
                resource_gid=gid,
            )),
            gid,
        )
        self.assertFalse(registry._order_gid_from_delivery(SimpleNamespace(
            resource_identity={
                'id': '9002', 'admin_graphql_api_id': gid,
            },
            resource_gid=gid,
        )))
        self.assertFalse(registry._order_gid_from_delivery(SimpleNamespace(
            resource_identity={'id': '9001'}, resource_gid=gid,
        )))

    def test_delivery_processing_enqueues_one_read_first_import(self):
        store = self._store('enqueue')
        gid = 'gid://shopify/Order/9001'
        first = self._delivery(store, 'one', gid)
        Client = type(self.env['shopify.connector.api.client'])
        with patch.object(
            Client,
            'execute_business',
            side_effect=AssertionError(
                'order webhook processing must not read Shopify'
            ),
        ):
            first._process_queued()
        self.assertEqual(first.state, 'processed')
        Job = self.env['shopify.connector.job']
        child = Job.search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', gid),
        ], limit=1)
        self.assertTrue(child)
        self.assertEqual(child.job_source, 'webhook')
        self.assertEqual(child.trigger_origin_event_ref, first.delivery_id)
        self.assertIn('authoritative Shopify read', first.processing_note)
        self.assertNotIn('cancel', first.processing_note.lower())

    def test_distinct_active_signal_is_durable_manual_review_not_lost(self):
        store = self._store('coalesce')
        gid = 'gid://shopify/Order/9002'
        first = self._delivery(store, 'one', gid)
        second = self._delivery(store, 'two', gid)
        with self.assertNoLogs('odoo.sql_db', level='ERROR'):
            first._process_queued()
            second._process_queued()
        self.assertEqual(first.state, 'processed')
        self.assertEqual(second.state, 'manual_review')
        self.assertEqual(
            self.env['shopify.connector.job'].search_count([
                ('store_id', '=', store.id),
                ('job_type', '=', 'order_import_sync'),
                ('shopify_target_gid', '=', gid),
                ('state', 'not in', (
                    'succeeded', 'failed_final', 'skipped', 'cancelled',
                )),
            ]),
            1,
        )
        self.assertIn('different same-order signal', second.processing_note)
        self.assertIn('scheduled order scan', second.processing_note)

    def test_cancelled_topic_is_evidence_only_and_keeps_child_import_type(self):
        store = self._store('cancelled')
        gid = 'gid://shopify/Order/9003'
        delivery = self._delivery(
            store, 'cancelled', gid, topic='orders/cancelled',
        )
        with patch.object(
            type(self.env['shopify.connector.api.client']),
            'execute_business',
            side_effect=AssertionError(
                'cancelled webhook processing must not read Shopify'
            ),
        ):
            delivery._process_queued()
        self.assertEqual(delivery.state, 'processed')
        self.assertIn('evidence-only', delivery.processing_note)
        child = self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', gid),
        ], limit=1)
        self.assertTrue(child)
        self.assertTrue(child.payload_hash.startswith('webhook_cancelled|'))

    def test_generation_change_fences_delivery_before_child_admission(self):
        store = self._store('generation', generation=1)
        gid = 'gid://shopify/Order/9004'
        delivery = self._delivery(store, 'generation', gid)
        store.sudo().write({'connection_generation': 2})
        delivery._process_queued()
        self.assertEqual(delivery.state, 'manual_review')
        self.assertIn('generation is stale', delivery.processing_note)
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', gid),
        ]))

    def test_cancelled_signal_never_coalesces_into_active_update(self):
        store = self._store('cancel-race')
        gid = 'gid://shopify/Order/9010'
        update = self._delivery(store, 'update-race', gid)
        cancelled = self._delivery(
            store, 'cancel-race', gid, topic='orders/cancelled',
        )
        update._process_queued()
        cancelled._process_queued()
        self.assertEqual(cancelled.state, 'manual_review')
        self.assertIn('different same-order signal', cancelled.processing_note)
        active = self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', gid),
        ])
        self.assertEqual(len(active), 1)
        self.assertFalse(active.payload_hash.startswith('webhook_cancelled|'))

    def test_failed_terminal_exact_job_is_not_a_successful_duplicate(self):
        store = self._store('failed-duplicate')
        gid = 'gid://shopify/Order/9011'
        delivery = self._delivery(store, 'failed-duplicate', gid)
        registry = self.env['shopify.connector.webhook.registry']
        first, disposition = registry._enqueue_order_import(
            store, delivery, gid, delivery.topic,
            store.connection_generation,
        )
        self.assertEqual(disposition, 'enqueued')
        first.sudo().write({
            'state': 'failed_final',
            'error_class': 'unknown_system_error',
            'finished_at': fields.Datetime.now(),
        })
        existing, disposition = registry._enqueue_order_import(
            store, delivery, gid, delivery.topic,
            store.connection_generation,
        )
        self.assertEqual(existing, first)
        self.assertEqual(disposition, 'unsafe_terminal')

    def test_succeeded_terminal_exact_job_is_a_safe_processed_duplicate(self):
        store = self._store('succeeded-duplicate')
        gid = 'gid://shopify/Order/9013'
        source_updated_at = fields.Datetime.to_datetime(
            '2026-08-22 12:34:56',
        )
        first = self._delivery(
            store, 'succeeded-first', gid,
            source_updated_at=source_updated_at,
            payload_body_suffix='identical-success-body',
        )
        second = self._delivery(
            store, 'succeeded-second', gid,
            source_updated_at=source_updated_at,
            payload_body_suffix='identical-success-body',
        )
        first._process_queued()
        importer = self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', gid),
        ], limit=1)
        self.assertTrue(importer)
        # Preserve the model's legal transition contract while isolating this
        # test from Shopify: the behavior under test starts at W1's production
        # delivery handler and is terminal duplicate admission, not importing.
        importer.sudo().write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
        })
        importer.sudo().write({
            'state': 'succeeded',
            'finished_at': fields.Datetime.now(),
        })
        second._process_queued()
        self.assertEqual(second.state, 'processed')
        self.assertIn('existing succeeded job', second.processing_note)
        self.assertEqual(self.env['shopify.connector.job'].search_count([
            ('store_id', '=', store.id),
            ('job_type', '=', 'order_import_sync'),
            ('shopify_target_gid', '=', gid),
        ]), 1)

    def test_updated_at_requires_timezone_qualified_rfc3339(self):
        importer = self.env['shopify.connector.order.importer']
        with self.assertRaises(JobHandlerError) as raised:
            importer._strict_updated_at('2026-08-22T12:00:00')
        self.assertEqual(
            raised.exception.error_class, 'data_shape_schema_mismatch',
        )
        self.assertEqual(
            fields.Datetime.to_string(
                importer._strict_updated_at('2026-08-22T16:00:00+04:00'),
            ),
            '2026-08-22 12:00:00',
        )

    def test_equal_timestamp_changed_webhook_evidence_is_manual_review(self):
        store = self._store('equal-conflict')
        partner = self.env['res.partner'].create({'name': 'Equal partner'})
        sale = self.env['sale.order'].create({
            'partner_id': partner.id,
            'company_id': store.company_id.id,
        })
        binding = self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Order/9012',
            'sale_order_id': sale.id,
            'shopify_updated_at_snapshot': fields.Datetime.to_datetime(
                '2026-08-22 12:00:00',
            ),
            'shopify_financial_status_snapshot': 'PAID',
            'status': 'active',
        })
        job = self.env['shopify.connector.job.enqueue'].enqueue(
            store,
            job_source='webhook',
            job_type='order_import_sync',
            payload_hash='equal-conflict',
            res_model='shopify.connector.store',
            res_id=store.id,
            shopify_target_gid=binding.shopify_gid,
        )
        importer = self.env['shopify.connector.order.importer']
        with patch.object(
            type(importer), '_validate_refresh_evidence', return_value=None,
        ), patch.object(
            type(importer), '_binding_financial_evidence_matches',
            return_value=False,
        ):
            with self.assertRaises(JobHandlerError) as raised:
                importer._refresh_existing(binding, {
                    'updatedAt': '2026-08-22T12:00:00Z',
                    'displayFinancialStatus': 'REFUNDED',
                    'displayFulfillmentStatus': None,
                    'cancelledAt': None,
                    'cancelReason': None,
                }, SimpleNamespace(), job)
        self.assertEqual(raised.exception.error_class, 'ambiguous_match')

    def test_order_import_snapshot_guard_rejects_older_refresh(self):
        store = self._store('snapshot')
        partner = self.env['res.partner'].create({'name': 'Snapshot partner'})
        sale = self.env['sale.order'].create({
            'partner_id': partner.id,
            'company_id': store.company_id.id,
        })
        binding = self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid': 'gid://shopify/Order/9005',
            'sale_order_id': sale.id,
            'shopify_updated_at_snapshot': fields.Datetime.to_datetime(
                '2026-08-22 12:00:00',
            ),
            'status': 'active',
        })
        importer = self.env['shopify.connector.order.importer']
        with patch.object(
            type(importer), '_validate_refresh_evidence', return_value=None,
        ):
            importer._refresh_existing(
                binding,
                {'updatedAt': '2026-08-22T11:00:00Z'},
                SimpleNamespace(),
                False,
            )
        binding.invalidate_recordset()
        self.assertEqual(
            fields.Datetime.to_string(binding.shopify_updated_at_snapshot),
            '2026-08-22 12:00:00',
        )
