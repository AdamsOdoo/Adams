"""Installed W2 product webhook contracts; no Shopify network calls."""

import hashlib
import queue
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import ValidationError
from odoo.sql_db import db_connect
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)

from ..models.shopify_connector_product_webhook import (
    PRODUCT_IMPORT_JOB_TYPE,
    PRODUCT_WEBHOOK_TOPICS,
)
from ..pre_init import pre_init_hook


@tagged('post_install', '-at_install')
class TestShopifyConnectorProductWebhookW2(TransactionCase):
    """Exercise the registry, delivery, enqueue and importer seams."""

    def _store(self, suffix):
        store = self.env['shopify.connector.store'].create({
            'name': 'W2 product webhook %s' % suffix,
            'shop_domain': 'w2-product-%s.myshopify.com' % suffix,
            'api_version': SHOPIFY_API_VERSION,
        })
        store.write({'state': 'connected'})
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id,
            'product_domain_enabled': True,
            'product_first_sync_source': 'shopify_source',
        })
        return store

    def _delivery(self, store, suffix, gid, source_updated_at=None):
        digest = hashlib.sha256(
            ('w2-product-body-%s' % suffix).encode('utf-8')
        ).hexdigest()
        source_updated_at = source_updated_at or fields.Datetime.now()
        delivery = self.env[
            'shopify.connector.webhook.delivery'
        ]._ingest(
            store,
            delivery_id='w2-product-delivery-%s' % suffix,
            event_id='w2-product-event-%s' % suffix,
            topic='products/update',
            shop_domain=store.shop_domain,
            api_version=SHOPIFY_API_VERSION,
            triggered_at=fields.Datetime.now(),
            source_updated_at=source_updated_at,
            payload_digest=digest,
            payload_size=64,
            payload_identity={
                'id': '123456',
                'admin_graphql_api_id': gid,
            },
        )[0]
        delivery.invalidate_recordset()
        return delivery

    def test_registry_activates_only_product_create_and_update(self):
        registry = self.env['shopify.connector.webhook.registry']
        active = set(registry.allowed_topics())
        self.assertTrue(set(PRODUCT_WEBHOOK_TOPICS).issubset(active))
        self.assertNotIn('products/delete', active)
        self.assertEqual(
            registry.topic_spec('products/update')['handler'],
            'product_import_sync',
        )
        self.assertIsNotNone(
            registry._get_topic_handlers().get('products/update'),
        )
        self.assertEqual(
            registry.topic_spec('products/update')['include_fields'],
            ['admin_graphql_api_id'],
        )

    def test_registry_extension_is_add_only_and_fails_closed_on_collision(self):
        registry = self.env['shopify.connector.webhook.registry']
        with self.assertRaises(ValidationError):
            registry._extend_product_topic_registry({
                'products/update': {'enum': 'OTHER_HANDLER'},
            })
        with self.assertRaises(ValidationError):
            registry._extend_product_topic_handlers({
                'products/create': object(),
            })

    def test_filtered_subscription_omitting_product_gid_is_not_healthy(self):
        subscription = self.env['shopify.connector.webhook.subscription']
        self.assertFalse(subscription._include_fields_match(
            ['admin_graphql_api_id'], ['id', 'title'],
        ))
        self.assertTrue(subscription._include_fields_match(
            ['admin_graphql_api_id'], [],
        ))
        self.assertTrue(subscription._include_fields_match(
            ['admin_graphql_api_id'], None,
        ))

    def test_w1_owns_schema_before_optional_w2_install(self):
        """Installed W1 exposes both evidence columns before W2 uses them."""
        root = Path(__file__).resolve().parents[1]
        w1_root = root.parent / 'shopify_connector_webhook'
        w1_manifest = (w1_root / '__manifest__.py').read_text()
        w2_manifest = (root / '__manifest__.py').read_text()
        migration = (
            w1_root / 'migrations' / '19.0.1.1.0' / 'post-migrate.py'
        ).read_text()
        runner = (root.parents[1] / 'tools' / 'run_connector_suite.sh').read_text()
        self.assertIn("'version': '19.0.1.1.0'", w1_manifest)
        self.assertIn("'version': '19.0.0.2.0'", w2_manifest)
        self.assertIn('information_schema.columns', migration)
        self.assertIn('expected_include_fields', migration)
        self.assertIn('actual_include_fields', migration)
        self.assertIn(
            'shopify_connector_webhook,shopify_connector_product_webhook',
            runner,
        )
        self.env.cr.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = ANY(%s)",
            (
                'shopify_connector_webhook_subscription',
                ['expected_include_fields', 'actual_include_fields'],
            ),
        )
        self.assertEqual(
            set(row[0] for row in self.env.cr.fetchall()),
            {'expected_include_fields', 'actual_include_fields'},
        )

    def test_w2_only_install_bridge_is_idempotent_and_jsonb(self):
        """Installing W2 alone over old W1 adds only the canonical columns."""
        root = Path(__file__).resolve().parents[1]
        manifest = (root / '__manifest__.py').read_text()
        bridge = (root / 'pre_init.py').read_text()
        runner = (root.parents[1] / 'tools' / 'run_connector_suite.sh').read_text()
        self.assertIn("'pre_init_hook': 'pre_init_hook'", manifest)
        self.assertIn('ALTER TABLE IF EXISTS', bridge)
        self.assertIn('ADD COLUMN IF NOT EXISTS expected_include_fields jsonb', bridge)
        self.assertIn('ADD COLUMN IF NOT EXISTS actual_include_fields jsonb', bridge)
        self.assertIn('7443250ae42a0c3fadba9bf0ef9991e1826b77b5', runner)
        pre_init_hook(self.env)
        self.env.cr.execute(
            "SELECT column_name, udt_name FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = ANY(%s)",
            (
                'shopify_connector_webhook_subscription',
                ['expected_include_fields', 'actual_include_fields'],
            ),
        )
        self.assertEqual(
            {row[0]: row[1] for row in self.env.cr.fetchall()},
            {
                'expected_include_fields': 'jsonb',
                'actual_include_fields': 'jsonb',
            },
        )

    def test_registry_removed_product_topic_queues_exact_gid_cleanup(self):
        """W2 removal leaves no active evidence and queues read-first delete."""
        store = self._store('uninstall')
        Subscription = self.env['shopify.connector.webhook.subscription']
        service = Subscription.sudo().with_context(
            **Subscription._service_context(),
        )
        gid = 'gid://shopify/WebhookSubscription/9001'
        sub = service.create({
            'store_id': store.id,
            'topic': 'products/update',
            'topic_enum': 'PRODUCTS_UPDATE',
            'expected': True,
            'expected_api_version': SHOPIFY_API_VERSION,
            'expected_include_fields': ['admin_graphql_api_id'],
            'state': 'active',
            'shopify_subscription_gid': gid,
        })
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'webhook_subscription_delete',
            'state': 'queued',
            'payload_hash': 'w2-uninstall-delete-fixture',
        })
        SubscriptionModel = type(Subscription)
        actual = [{
            'id': gid,
            'topic': 'PRODUCTS_UPDATE',
            'uri_digest': 'callback-digest',
            'observed_api_version': SHOPIFY_API_VERSION,
            'format': 'JSON',
            'include_fields': ['admin_graphql_api_id'],
        }]
        with patch.object(
            SubscriptionModel, '_require_hmac_client_secret', return_value=True,
        ), patch.object(
            SubscriptionModel, '_enqueue_job_with_recovery',
            return_value=job,
        ):
            Subscription._reconcile_registry_removed_subscriptions(
                store,
                ('app/uninstalled',),
                actual,
                source='scheduled_sync',
                epoch=7,
            )
        sub.invalidate_recordset()
        self.assertFalse(sub.expected)
        self.assertEqual(sub.state, 'queued')
        self.assertEqual(sub.last_job_id, job)
        self.assertFalse(sub.last_error)

    def test_registry_removed_topic_without_gid_is_manual_review_not_guess_delete(self):
        store = self._store('uninstall-no-gid')
        Subscription = self.env['shopify.connector.webhook.subscription']
        service = Subscription.sudo().with_context(
            **Subscription._service_context(),
        )
        sub = service.create({
            'store_id': store.id,
            'topic': 'products/create',
            'topic_enum': 'PRODUCTS_CREATE',
            'expected': True,
            'expected_api_version': SHOPIFY_API_VERSION,
            'expected_include_fields': ['admin_graphql_api_id'],
            'state': 'active',
        })
        Subscription._reconcile_registry_removed_subscriptions(
            store,
            ('app/uninstalled',),
            [{
                'id': 'gid://shopify/WebhookSubscription/other',
                'topic': 'PRODUCTS_CREATE',
                'uri_digest': 'callback-digest',
                'observed_api_version': SHOPIFY_API_VERSION,
                'format': 'JSON',
                'include_fields': ['admin_graphql_api_id'],
            }],
            source='scheduled_sync',
            epoch=7,
        )
        sub.invalidate_recordset()
        self.assertFalse(sub.expected)
        self.assertEqual(sub.state, 'manual_review')
        self.assertFalse(sub.last_job_id)
        self.assertIn('no stored Shopify subscription GID', sub.last_error)

    def test_registry_removed_topic_unknown_remote_gid_is_manual_review(self):
        """A different remote GID is retained, never guessed for deletion."""
        store = self._store('uninstall-unknown-gid')
        Subscription = self.env['shopify.connector.webhook.subscription']
        service = Subscription.sudo().with_context(
            **Subscription._service_context(),
        )
        sub = service.create({
            'store_id': store.id,
            'topic': 'products/update',
            'topic_enum': 'PRODUCTS_UPDATE',
            'expected': True,
            'expected_api_version': SHOPIFY_API_VERSION,
            'expected_include_fields': ['admin_graphql_api_id'],
            'state': 'active',
            'shopify_subscription_gid': (
                'gid://shopify/WebhookSubscription/recorded'
            ),
        })
        Subscription._reconcile_registry_removed_subscriptions(
            store,
            ('app/uninstalled',),
            [{
                'id': 'gid://shopify/WebhookSubscription/unknown',
                'topic': 'PRODUCTS_UPDATE',
                'uri_digest': 'callback-digest',
                'observed_api_version': SHOPIFY_API_VERSION,
                'format': 'JSON',
                'include_fields': ['admin_graphql_api_id'],
            }],
            source='scheduled_sync',
            epoch=7,
        )
        sub.invalidate_recordset()
        self.assertFalse(sub.expected)
        self.assertEqual(sub.state, 'manual_review')
        self.assertFalse(sub.last_job_id)
        self.assertIn('different subscription GID', sub.last_error)
        self.assertEqual(sub.actual_topic, 'PRODUCTS_UPDATE')

    def test_optional_addon_removal_uses_reconcile_not_uninstall_network_call(self):
        source = (
            Path(__file__).resolve().parents[1].parent /
            'shopify_connector_webhook' / 'models' /
            'shopify_connector_webhook_subscription.py'
        ).read_text()
        start = source.index(
            'def _reconcile_registry_removed_subscriptions',
        )
        end = source.index('def _reconcile_store', start)
        helper = source[start:end]
        self.assertIn('_enqueue_subscription_mutation', helper)
        self.assertIn('expected\': False', helper)
        self.assertNotIn('execute_business(', helper)
        self.assertNotIn('client.execute(', helper)

    def test_exact_product_gid_is_required_and_numeric_id_is_never_synthesized(self):
        registry = self.env['shopify.connector.webhook.registry']
        gid = 'gid://shopify/Product/788032119674292922'
        self.assertEqual(
            registry._product_gid_from_delivery(SimpleNamespace(
                resource_identity={'id': '788032119674292922',
                                    'admin_graphql_api_id': gid},
                resource_gid=gid,
            )),
            gid,
        )
        self.assertFalse(registry._product_gid_from_delivery(SimpleNamespace(
            resource_identity={'id': '788032119674292922'},
            resource_gid='gid://shopify/Product/788032119674292922',
        )))
        self.assertFalse(registry._product_gid_from_delivery(SimpleNamespace(
            resource_identity={'admin_graphql_api_id':
                               'gid://shopify/ProductVariant/123'},
            resource_gid='gid://shopify/ProductVariant/123',
        )))

    def test_delivery_processing_enqueues_one_child_and_records_correlation(self):
        store = self._store('enqueue')
        gid = 'gid://shopify/Product/788032119674292922'
        first = self._delivery(store, 'one', gid)
        # A webhook handler is enqueue-only. If it attempted a remote read,
        # this production client seam would fail the test immediately.
        Client = type(self.env['shopify.connector.api.client'])
        with patch.object(
            Client, 'execute_business',
            side_effect=AssertionError('webhook processing must not read Shopify'),
        ):
            first._process_queued()
        self.assertEqual(first.state, 'processed')
        Job = self.env['shopify.connector.job']
        jobs = Job.search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'product_import_sync'),
            ('shopify_target_gid', '=', gid),
        ])
        self.assertEqual(len(jobs), 1)
        child = jobs[0]
        self.assertEqual(child.job_source, 'webhook')
        self.assertEqual(child.res_model, 'shopify.connector.store')
        self.assertEqual(child.res_id, store.id)
        self.assertEqual(child.trigger_origin_event_ref, first.delivery_id)
        self.assertEqual(
            child.payload_hash,
            '%sZ' % fields.Datetime.to_string(
                first.source_updated_at,
            ).replace(' ', 'T'),
        )
        self.assertIn(str(child.id), first.processing_note)
        self.assertIn('authoritative Shopify read', first.processing_note)

        second = self._delivery(store, 'two', gid)
        second._process_queued()
        self.assertEqual(second.state, 'processed')
        self.assertEqual(Job.search_count([
            ('store_id', '=', store.id),
            ('job_type', '=', 'product_import_sync'),
            ('shopify_target_gid', '=', gid),
            ('state', 'not in', (
                'succeeded', 'failed_final', 'skipped', 'cancelled',
            )),
        ]), 1)
        self.assertIn(str(child.id), second.processing_note)
        self.assertIn('coalesced', second.processing_note)

    def test_terminal_old_generation_does_not_suppress_current_import(self):
        """Skipped/cancelled/final-failed old rows never block reconnect work."""
        gid = 'gid://shopify/Product/788032119674292922'
        stamp = '2026-08-17T12:00:00Z'
        JobEnqueue = self.env['shopify.connector.job.enqueue'].sudo()
        Job = self.env['shopify.connector.job'].sudo()
        for state in ('skipped', 'cancelled', 'failed_final'):
            store = self._store('generation-%s' % state)
            store.sudo().write({'connection_generation': 1})
            old = JobEnqueue.enqueue(
                store,
                job_source='scheduled_sync',
                job_type=PRODUCT_IMPORT_JOB_TYPE,
                payload_hash=stamp,
                res_model='shopify.connector.store',
                res_id=store.id,
                shopify_target_gid=gid,
            )
            if state == 'skipped':
                old._transition_skipped('W2 generation regression fixture')
            elif state == 'failed_final':
                old._transition_failed_final(
                    'data_shape_schema_mismatch',
                    'W2 generation regression fixture',
                )
            else:
                old.sudo().write({
                    'state': 'cancelled',
                    'finished_at': fields.Datetime.now(),
                })
            store.sudo().write({
                'connection_generation': 2,
                'state': 'connected',
            })
            delivery = self._delivery(
                store, 'generation-%s' % state, gid,
                fields.Datetime.to_datetime(stamp.replace('Z', '')),
            )
            delivery._process_queued()
            current = Job.search([
                ('store_id', '=', store.id),
                ('job_type', '=', PRODUCT_IMPORT_JOB_TYPE),
                ('shopify_target_gid', '=', gid),
                ('expected_connection_generation', '=', 2),
            ], order='id desc', limit=1)
            self.assertTrue(current, state)
            self.assertNotEqual(current.id, old.id, state)
            self.assertIn('enqueued', delivery.processing_note, state)

    def test_stale_product_snapshot_is_skipped_without_writes(self):
        store = self._store('stale')
        template = self.env['product.template'].create({
            'name': 'W2 stale product fixture',
            'company_id': store.company_id.id,
        })
        gid = 'gid://shopify/Product/9000000001'
        binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().create({
            'store_id': store.id,
            'shopify_gid': gid,
            'product_template_id': template.id,
            'shopify_updated_at': '2026-08-18T00:00:00Z',
            'shopify_birth_initialized': True,
        })
        result = self.env['shopify.connector.product.importer']._apply_import(
            store,
            {
                'gid': gid,
                'status': 'active',
                'updated_at': '2026-08-17T23:59:59Z',
                'variants': [],
            },
        )
        self.assertTrue(result['stale'])
        self.assertTrue(result['out_of_order'])
        binding.invalidate_recordset(['shopify_updated_at'])
        self.assertEqual(binding.shopify_updated_at, '2026-08-18T00:00:00Z')

    def test_production_paths_are_modular_and_remote_read_stays_in_child_job(self):
        root = Path(__file__).resolve().parents[1]
        handler = (root / 'models' /
                   'shopify_connector_product_webhook.py').read_text()
        guard = (root / 'models' /
                 'shopify_connector_product_importer_guard.py').read_text()
        manifest = (root.parent / 'shopify_connector_product_webhook' /
                    '__manifest__.py').read_text()
        runner = (root.parents[1] / 'tools' / 'run_connector_suite.sh').read_text()
        self.assertIn("'products/create', 'products/update'", handler)
        self.assertNotIn('products/delete', handler)
        self.assertIn('admin_graphql_api_id', handler)
        self.assertIn("job_source='webhook'", handler)
        self.assertIn("job_type=PRODUCT_IMPORT_JOB_TYPE", handler)
        self.assertIn('_lock_store_for_lifecycle', handler)
        self.assertIn('expected_connection_generation', handler)
        self.assertIn('already registered by', handler)
        self.assertNotIn('execute_business(', handler)
        self.assertIn('try_lock_for_update', guard)
        self.assertIn('incoming >= stored', guard)
        self.assertIn('shopify_connector_webhook', manifest)
        self.assertIn('shopify_connector_product', manifest)
        self.assertIn('shopify_connector_product_webhook', runner)
        subscription = (
            root.parent / 'shopify_connector_webhook' / 'models' /
            'shopify_connector_webhook_subscription.py'
        ).read_text()
        self.assertIn('includeFields', subscription)
        self.assertIn('_include_fields_match', subscription)
        self.assertIn("'includeFields': (", subscription)


@tagged('post_install', '-at_install')
class TestShopifyConnectorProductWebhookGenerationRace(TransactionCase):
    """Genuine two-cursor proof for parent validation + child admission."""

    BOUND_SECONDS = 15

    def _open_cursor(self):
        cursor = db_connect(self.env.cr.dbname).cursor()
        cursor.execute(
            "SELECT set_config('statement_timeout', %s, true), "
            "set_config('lock_timeout', %s, true)",
            ('10000', '8000'),
        )
        return cursor

    def _committed_fixture(self):
        cr = self._open_cursor()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            store = env['shopify.connector.store'].create({
                'name': 'W2 product webhook race fixture',
                'shop_domain': 'w2-product-race-%s.myshopify.com' % store_id_seed(),
                'api_version': SHOPIFY_API_VERSION,
                'state': 'connected',
            })
            env['shopify.connector.store.settings'].create({
                'store_id': store.id,
                'product_domain_enabled': True,
                'product_first_sync_source': 'shopify_source',
            })
            gid = 'gid://shopify/Product/788032119674292922'
            delivery = env[
                'shopify.connector.webhook.delivery'
            ]._ingest(
                store,
                delivery_id='w2-product-race-delivery-%s' % store.id,
                event_id='w2-product-race-event-%s' % store.id,
                topic='products/update',
                shop_domain=store.shop_domain,
                api_version=SHOPIFY_API_VERSION,
                triggered_at=fields.Datetime.now(),
                source_updated_at=fields.Datetime.now(),
                payload_digest=hashlib.sha256(b'w2-product-race').hexdigest(),
                payload_size=32,
                payload_identity={
                    'id': '123456',
                    'admin_graphql_api_id': gid,
                },
            )[0]
            cr.commit()
            return store.id, delivery.id
        finally:
            cr.close()

    def _cleanup_fixture(self, store_id):
        cr = self._open_cursor()
        try:
            cr.execute(
                'DELETE FROM shopify_connector_job_log '
                'WHERE job_id IN (SELECT id FROM shopify_connector_job '
                'WHERE store_id = %s)', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_webhook_delivery '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_job WHERE store_id = %s',
                (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store_settings '
                'WHERE store_id = %s', (store_id,),
            )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            cr.commit()
        finally:
            cr.close()

    def test_lifecycle_lock_blocks_reconnect_until_child_admission(self):
        store_id, delivery_id = self._committed_fixture()
        entered = threading.Event()
        release = threading.Event()
        lifecycle_started = threading.Event()
        lifecycle_done = threading.Event()
        results = queue.Queue()
        registry_cls = type(
            self.env['shopify.connector.webhook.registry']
        )
        original = registry_cls._enqueue_product_import

        def parked_enqueue(registry, store, delivery, gid, generation=None):
            entered.set()
            if not release.wait(self.BOUND_SECONDS):
                raise AssertionError('bounded child-admission gate timed out')
            return original(
                registry, store, delivery, gid, generation=generation,
            )

        def run_delivery():
            cr = None
            try:
                cr = self._open_cursor()
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['shopify.connector.webhook.delivery'].browse(
                    delivery_id,
                )._process_queued()
                cr.commit()
                results.put(('delivery', None))
            except BaseException as exc:
                results.put(('delivery', type(exc).__name__))
            finally:
                if cr is not None:
                    cr.rollback()
                    cr.close()

        def run_lifecycle_probe():
            cr = None
            try:
                cr = self._open_cursor()
                env = api.Environment(cr, SUPERUSER_ID, {})
                lifecycle_started.set()
                env['shopify.connector.store'].browse(
                    store_id,
                )._lock_store_for_lifecycle()
                cr.rollback()
                lifecycle_done.set()
                results.put(('lifecycle', None))
            except BaseException as exc:
                results.put(('lifecycle', type(exc).__name__))
            finally:
                if cr is not None:
                    cr.rollback()
                    cr.close()

        delivery_thread = threading.Thread(target=run_delivery, daemon=True)
        lifecycle_thread = threading.Thread(
            target=run_lifecycle_probe, daemon=True,
        )
        try:
            with patch.object(
                registry_cls, '_enqueue_product_import', parked_enqueue,
            ):
                delivery_thread.start()
                self.assertTrue(entered.wait(self.BOUND_SECONDS))
                lifecycle_thread.start()
                self.assertTrue(lifecycle_started.wait(self.BOUND_SECONDS))
                time.sleep(0.2)
                self.assertFalse(
                    lifecycle_done.is_set(),
                    'a concurrent lifecycle cursor must wait for the child '
                    'admission lock, not observe a stale generation',
                )
                release.set()
                delivery_thread.join(self.BOUND_SECONDS)
                lifecycle_thread.join(self.BOUND_SECONDS)
        finally:
            release.set()
            delivery_thread.join(self.BOUND_SECONDS)
            lifecycle_thread.join(self.BOUND_SECONDS)
            self._cleanup_fixture(store_id)
        self.assertFalse(delivery_thread.is_alive())
        self.assertFalse(lifecycle_thread.is_alive())
        outcomes = [results.get_nowait(), results.get_nowait()]
        self.assertEqual(
            sorted(outcomes),
            [('delivery', None), ('lifecycle', None)],
        )


def store_id_seed():
    """Return a non-sensitive unique suffix for the committed race fixture."""
    import uuid
    return uuid.uuid4().hex[:12]
