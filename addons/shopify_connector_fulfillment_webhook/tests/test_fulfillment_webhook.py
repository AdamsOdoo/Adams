import hashlib
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)

from ..models.shopify_connector_fulfillment_webhook import (
    FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
    FULFILLMENT_WEBHOOK_TOPICS,
    canonical_shopify_gid,
)


@tagged('post_install', '-at_install')
class TestShopifyConnectorFulfillmentWebhook(TransactionCase):
    """Exercise the W1 envelope -> resolver -> inbound observation seam."""

    def _store(self, suffix, generation=0):
        store = self.env['shopify.connector.store'].create({
            'name': 'Fulfillment webhook %s' % suffix,
            'shop_domain': 'fulfillment-webhook-%s.myshopify.com' % suffix,
            'api_version': SHOPIFY_API_VERSION,
            'state': 'connected',
        })
        if generation:
            store.sudo().write({'connection_generation': generation})
        self.env['shopify.connector.store.settings'].create({
            'store_id': store.id,
            'fulfillment_domain_enabled': True,
        })
        return store

    def _delivery(
        self, store, suffix, fulfillment_gid,
        topic='fulfillments/update', identity_id=None,
    ):
        identity = {'admin_graphql_api_id': fulfillment_gid}
        if identity_id is not None:
            identity['id'] = identity_id
        return self.env[
            'shopify.connector.webhook.delivery'
        ]._ingest(
            store,
            delivery_id='fulfillment-webhook-delivery-%s' % suffix,
            event_id='fulfillment-webhook-event-%s' % suffix,
            topic=topic,
            shop_domain=store.shop_domain,
            api_version=SHOPIFY_API_VERSION,
            triggered_at=fields.Datetime.now(),
            source_updated_at=False,
            payload_digest=hashlib.sha256(
                ('fulfillment-webhook-body-%s' % suffix).encode('utf-8'),
            ).hexdigest(),
            payload_size=64,
            payload_identity=identity,
        )[0]

    def test_registry_activates_only_assessed_fulfillment_topics(self):
        registry = self.env['shopify.connector.webhook.registry']
        active = set(registry.allowed_topics())
        self.assertTrue(set(FULFILLMENT_WEBHOOK_TOPICS).issubset(active))
        self.assertNotIn('refunds/create', active)
        self.assertEqual(
            registry.topic_spec('fulfillments/update')['handler'],
            FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
        )
        self.assertEqual(
            registry.topic_spec('fulfillments/update')['include_fields'],
            ['admin_graphql_api_id'],
        )

    def test_numeric_order_id_is_never_used_and_exact_fulfillment_gid_is_required(self):
        fulfillment_gid = 'gid://shopify/Fulfillment/7001'
        self.assertEqual(
            canonical_shopify_gid(fulfillment_gid, 'Fulfillment'),
            fulfillment_gid,
        )
        registry = self.env['shopify.connector.webhook.registry']
        # Shopify's official fulfillment webhook payload includes numeric
        # order_id; the W1 allowlist may retain it as evidence, but this seam
        # never reads it to construct an Order GID.
        self.assertEqual(
            registry._fulfillment_gid_from_delivery(SimpleNamespace(
                resource_identity={
                    'admin_graphql_api_id': fulfillment_gid,
                    'order_id': '9001',
                },
                resource_gid=fulfillment_gid,
            )),
            fulfillment_gid,
        )
        self.assertFalse(registry._fulfillment_gid_from_delivery(SimpleNamespace(
            resource_identity={
                'id': '7002',
                'admin_graphql_api_id': fulfillment_gid,
            },
            resource_gid=fulfillment_gid,
        )))
        self.assertFalse(canonical_shopify_gid(
            'gid://shopify/Fulfillment/7001/extra', 'Fulfillment',
        ))

    def test_delivery_processing_enqueues_read_only_resolver_not_mutation(self):
        store = self._store('enqueue')
        fulfillment_gid = 'gid://shopify/Fulfillment/7001'
        delivery = self._delivery(
            store, 'one', fulfillment_gid, identity_id='7001',
        )
        Client = type(self.env['shopify.connector.api.client'])
        with patch.object(
            Client,
            'execute_business',
            side_effect=AssertionError(
                'fulfillment webhook processing must not call Shopify'
            ),
        ):
            delivery._process_queued()
        self.assertEqual(delivery.state, 'processed')
        resolver = self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE),
            ('shopify_target_gid', '=', fulfillment_gid),
        ], limit=1)
        self.assertTrue(resolver)
        self.assertEqual(resolver.trigger_origin_event_ref, delivery.delivery_id)
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', 'in', (
                'fulfillment_create', 'fulfillment_tracking_update',
            )),
        ]))

    def test_distinct_active_signal_is_durable_manual_review_not_lost(self):
        store = self._store('coalesce')
        gid = 'gid://shopify/Fulfillment/7002'
        first = self._delivery(store, 'one', gid, identity_id='7002')
        second = self._delivery(store, 'two', gid, identity_id='7002')
        with self.assertNoLogs('odoo.sql_db', level='ERROR'):
            first._process_queued()
            second._process_queued()
        self.assertEqual(first.state, 'processed')
        self.assertEqual(second.state, 'manual_review')
        self.assertEqual(
            self.env['shopify.connector.job'].search_count([
                ('store_id', '=', store.id),
                ('job_type', '=', FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE),
                ('shopify_target_gid', '=', gid),
                ('state', 'not in', (
                    'succeeded', 'failed_final', 'skipped', 'cancelled',
                )),
            ]),
            1,
        )
        self.assertIn(
            'different same-fulfillment signal', second.processing_note,
        )
        self.assertIn('scheduled fulfillment', second.processing_note)

    def _order_binding(self, store, order_gid):
        partner = self.env['res.partner'].create({
            'name': 'Fulfillment webhook partner',
        })
        sale = self.env['sale.order'].create({
            'partner_id': partner.id,
            'company_id': store.company_id.id,
        })
        return self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': store.id,
            'shopify_gid': order_gid,
            'sale_order_id': sale.id,
            'status': 'active',
        })

    @contextmanager
    def _read_result(self, data):
        yield {'data': data}

    def _resolver(self, store, fulfillment_gid, delivery_id='delivery'):
        return self.env['shopify.connector.job.enqueue'].enqueue(
            store,
            job_source='webhook',
            job_type=FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
            payload_hash='resolver:%s:%s' % (fulfillment_gid, delivery_id),
            res_model='shopify.connector.store',
            res_id=store.id,
            shopify_target_gid=fulfillment_gid,
            trigger_origin_event_ref=delivery_id,
        )

    def test_resolver_reads_exact_fulfillment_node_then_enqueues_observation(self):
        store = self._store('resolve')
        order_gid = 'gid://shopify/Order/9006'
        self._order_binding(store, order_gid)
        fulfillment_gid = 'gid://shopify/Fulfillment/7003'
        job = self._resolver(store, fulfillment_gid)
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertTrue(dispatch._start_running(job))
        Service = self.env['shopify.connector.fulfillment.service']
        node = {
            'node': {
                '__typename': 'Fulfillment',
                'id': fulfillment_gid,
                'order': {'id': order_gid},
            },
        }
        with patch.object(
            type(Service), '_read_data', return_value=node,
        ) as read:
            with patch.object(
                type(self.env['shopify.connector.api.client']),
                'execute_business',
                side_effect=AssertionError(
                    'resolver must not issue a Shopify mutation'
                ),
            ):
                dispatch._invoke_handler(job)
        self.assertEqual(job.state, 'succeeded')
        read.assert_called_once_with(
            job,
            store,
            Service.FULFILLMENT_NODE_QUERY,
            {'fulfillmentId': fulfillment_gid},
        )
        query = read.call_args.args[2]
        self.assertIn('node(id: $fulfillmentId)', query)
        self.assertIn('... on Fulfillment', query)
        self.assertIn('order { id }', query)
        self.assertNotIn('mutation', query.lower())
        observation = self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'fulfillment_inbound_observation'),
            ('res_model', '=', 'shopify.connector.order.binding'),
        ], limit=1)
        self.assertTrue(observation)
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', 'in', (
                'fulfillment_create', 'fulfillment_tracking_update',
            )),
        ]))

    def test_unbound_resolved_order_becomes_manual_review_evidence(self):
        store = self._store('unbound')
        fulfillment_gid = 'gid://shopify/Fulfillment/7004'
        order_gid = 'gid://shopify/Order/9007'
        job = self._resolver(store, fulfillment_gid, 'unbound')
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertTrue(dispatch._start_running(job))
        node = {
            'node': {
                '__typename': 'Fulfillment',
                'id': fulfillment_gid,
                'order': {'id': order_gid},
            },
        }
        with patch.object(type(
            self.env['shopify.connector.fulfillment.service']
        ), '_read_data', return_value=node):
            dispatch._invoke_handler(job)
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(
            job.error_class,
            'fulfillment_notification_confirmation_missing',
        )
        log = self.env['shopify.connector.job.log'].search([
            ('job_id', '=', job.id),
        ], order='id desc', limit=1)
        self.assertIn('no exact order binding', log.message)

    def test_missing_order_gid_never_falls_back_to_numeric_webhook_id(self):
        store = self._store('bad-node')
        fulfillment_gid = 'gid://shopify/Fulfillment/7005'
        job = self._resolver(store, fulfillment_gid, 'bad-node')
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertTrue(dispatch._start_running(job))
        node = {
            'node': {
                '__typename': 'Fulfillment',
                'id': fulfillment_gid,
                'order': None,
            },
        }
        with patch.object(type(
            self.env['shopify.connector.fulfillment.service']
        ), '_read_data', return_value=node):
            dispatch._invoke_handler(job)
        self.assertEqual(job.state, 'failed_retryable')
        self.assertEqual(job.error_class, 'data_shape_schema_mismatch')

    def test_generation_change_fences_fulfillment_delivery(self):
        store = self._store('generation', generation=1)
        gid = 'gid://shopify/Fulfillment/7006'
        delivery = self._delivery(store, 'generation', gid, identity_id='7006')
        store.sudo().write({'connection_generation': 2})
        delivery._process_queued()
        self.assertEqual(delivery.state, 'manual_review')
        self.assertIn('generation is stale', delivery.processing_note)
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE),
            ('shopify_target_gid', '=', gid),
        ]))

    def test_resolver_replay_policy_is_remote_read_safe(self):
        policies = self.env[
            'shopify.connector.job.dispatch'
        ]._get_replay_policies()
        self.assertEqual(
            policies[FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE],
            REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
        )

    def test_retry_replays_production_resolver_read_and_succeeds_safely(self):
        store = self._store('replay-execution')
        fulfillment_gid = 'gid://shopify/Fulfillment/7015'
        order_gid = 'gid://shopify/Order/9015'
        binding = self._order_binding(store, order_gid)
        job = self._resolver(store, fulfillment_gid, 'replay-execution')
        dispatch = self.env['shopify.connector.job.dispatch']
        Service = self.env['shopify.connector.fulfillment.service']
        node = {
            'node': {
                '__typename': 'Fulfillment',
                'id': fulfillment_gid,
                'order': {'id': order_gid},
            },
        }
        with patch.object(
            type(Service), '_read_data',
            side_effect=[RuntimeError('transient implementation fault'), node],
        ) as read:
            # `_dispatch_one` is the production dispatcher entry point.  The
            # first remote-read attempt takes the bounded unknown-system
            # safety retry; the due retry executes the same read-first handler
            # and may safely finish without admitting a mutation.
            dispatch._dispatch_one(job)
            self.assertEqual(job.state, 'retry_waiting')
            self.assertEqual(job.error_class, 'unknown_system_error')
            self.assertEqual(job.retry_count, 1)
            job.sudo().write({'next_retry_at': fields.Datetime.now()})
            dispatch._dispatch_one(job)
        self.assertEqual(read.call_count, 2)
        self.assertEqual(job.state, 'succeeded')
        self.assertFalse(job.error_class)
        observations = self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'fulfillment_inbound_observation'),
            ('res_model', '=', 'shopify.connector.order.binding'),
            ('res_id', '=', binding.id),
        ])
        self.assertEqual(len(observations), 1)
        self.assertIn(
            observations.state, ('queued', 'running', 'retry_waiting', 'succeeded'),
        )
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', 'in', (
                'fulfillment_create', 'fulfillment_tracking_update',
            )),
        ]))

    def test_unknown_resolver_exception_is_unknown_system_error(self):
        store = self._store('unknown')
        job = self._resolver(
            store, 'gid://shopify/Fulfillment/7010', 'unknown',
        )
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertTrue(dispatch._start_running(job))
        Service = self.env['shopify.connector.fulfillment.service']
        with patch.object(
            type(Service), '_resolve_order_gid',
            side_effect=RuntimeError('implementation defect'),
        ):
            dispatch._invoke_handler(job)
        self.assertEqual(job.error_class, 'unknown_system_error')
        self.assertEqual(job.state, 'retry_waiting')

    def test_generation_race_after_network_read_admits_no_observation(self):
        store = self._store('post-network-generation', generation=4)
        fulfillment_gid = 'gid://shopify/Fulfillment/7011'
        order_gid = 'gid://shopify/Order/9011'
        self._order_binding(store, order_gid)
        job = self._resolver(store, fulfillment_gid, 'post-network')
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertTrue(dispatch._start_running(job))
        Service = self.env['shopify.connector.fulfillment.service']

        def resolve_then_reconnect(*_args):
            store.sudo().write({'connection_generation': 5})
            return order_gid

        with patch.object(
            type(Service), '_resolve_order_gid',
            side_effect=resolve_then_reconnect,
        ):
            dispatch._invoke_handler(job)
        self.assertEqual(job.state, 'retry_waiting')
        self.assertEqual(
            job.error_class, 'shopify_temporary_server_network',
        )
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'fulfillment_inbound_observation'),
        ]))

    def test_binding_lock_deletion_race_fails_closed(self):
        store = self._store('binding-race')
        fulfillment_gid = 'gid://shopify/Fulfillment/7012'
        order_gid = 'gid://shopify/Order/9012'
        binding = self._order_binding(store, order_gid)
        job = self._resolver(store, fulfillment_gid, 'binding-race')
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertTrue(dispatch._start_running(job))
        Service = self.env['shopify.connector.fulfillment.service']
        Binding = type(binding)
        with patch.object(
            type(Service), '_resolve_order_gid', return_value=order_gid,
        ), patch.object(
            Binding, 'try_lock_for_update',
            return_value=self.env['shopify.connector.order.binding'],
        ):
            dispatch._invoke_handler(job)
        self.assertEqual(job.state, 'retry_waiting')
        self.assertEqual(job.error_class, 'concurrency_race_conflict')
        self.assertFalse(self.env['shopify.connector.job'].search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'fulfillment_inbound_observation'),
        ]))

    def test_failed_downstream_observation_is_not_success(self):
        store = self._store('failed-observation')
        fulfillment_gid = 'gid://shopify/Fulfillment/7013'
        order_gid = 'gid://shopify/Order/9013'
        binding = self._order_binding(store, order_gid)
        job = self._resolver(store, fulfillment_gid, 'failed-observation')
        payload_hash = 'webhook:%s:%s' % (
            fulfillment_gid, job.trigger_origin_event_ref,
        )
        observation = self.env['shopify.connector.job.enqueue'].enqueue(
            store,
            job_source='webhook',
            job_type='fulfillment_inbound_observation',
            payload_hash=payload_hash,
            res_model='shopify.connector.order.binding',
            res_id=binding.id,
        )
        observation._transition_failed_retryable(
            'mapping_missing', 'deliberate downstream failure',
        )
        dispatch = self.env['shopify.connector.job.dispatch']
        self.assertTrue(dispatch._start_running(job))
        Service = self.env['shopify.connector.fulfillment.service']
        with patch.object(
            type(Service), '_resolve_order_gid', return_value=order_gid,
        ):
            dispatch._invoke_handler(job)
        self.assertEqual(job.state, 'blocked_manual_review')
        self.assertEqual(
            job.error_class,
            'fulfillment_notification_confirmation_missing',
        )

    def test_failed_terminal_exact_resolver_is_not_successful_duplicate(self):
        store = self._store('failed-resolver')
        gid = 'gid://shopify/Fulfillment/7014'
        delivery = self._delivery(
            store, 'failed-resolver', gid, identity_id='7014',
        )
        registry = self.env['shopify.connector.webhook.registry']
        resolver, disposition = registry._enqueue_resolver(
            store, delivery, gid, store.connection_generation,
        )
        self.assertEqual(disposition, 'enqueued')
        resolver.sudo().write({
            'state': 'cancelled',
            'cancel_reason': 'test cancellation',
            'finished_at': fields.Datetime.now(),
        })
        existing, disposition = registry._enqueue_resolver(
            store, delivery, gid, store.connection_generation,
        )
        self.assertEqual(existing, resolver)
        self.assertEqual(disposition, 'unsafe_terminal')
