"""Odoo-level contracts for the P11 subscription runtime cutover.

These tests deliberately use the real registry/model composition and local
fakes at the Shopify boundary.  They do not require a Shopify account: the
purpose is to prove that admission is durable and fenced before a worker can
reach transport, and that uncertain work is settled by readback without a
second mutation.
"""

import hashlib
import json
import uuid
from types import SimpleNamespace
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_webhook.integration.shopify.webhook_subscription_mutation_gateway import (
    SHOPIFY_API_VERSION,
    WebhookSubscriptionMutationGateway,
)
from odoo.addons.shopify_connector_webhook.models.shopify_connector_webhook_subscription import (
    ShopifyConnectorWebhookSubscription,
)
from odoo.addons.shopify_connector_webhook.models.shopify_connector_webhook_subscription_v2_reconciliation import (
    _ReadDelegate,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
    C2_SENTINEL_CONTEXT,
    C2_SIDE_CURSOR_SENTINEL,
    canonical_sha256,
)


@tagged('post_install', '-at_install')
class TestShopifyConnectorWebhookP11(TransactionCase):
    """Exercise the installed P11 model composition without network calls."""

    def _store_and_subscription(self, mode='subscriptions', suffix=None):
        suffix = suffix or uuid.uuid4().hex[:12]
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'https://p11-%s.example.invalid' % suffix,
        )
        Store = self.env['shopify.connector.store'].sudo()
        store = Store._store_service_create('_setup', {
            'name': 'P11 subscription %s' % suffix,
            'shop_domain': 'p11-%s.myshopify.com' % suffix,
            'company_id': self.env.company.id,
        })
        store._store_service_write('_lifecycle', {'state': 'connected'})
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().create({'store_id': store.id})
        settings.sudo()._v2_mode_surface().browse(settings.id).write({
            'v2_runtime_mode': mode,
        })
        subscriptions = self.env[
            'shopify.connector.webhook.subscription'
        ].sudo()._ensure_expected_for_store(store)
        subscription = subscriptions.filtered(
            lambda item: item.topic == 'app/uninstalled',
        )
        self.assertEqual(len(subscription), 1)
        return store, settings, subscription

    @staticmethod
    def _set_mode(settings, mode):
        settings.sudo()._v2_mode_surface().browse(settings.id).write({
            'v2_runtime_mode': mode,
        })

    def _admitted_job(self, mode='subscriptions'):
        store, settings, subscription = self._store_and_subscription(mode)
        Subscription = subscription.sudo()
        with patch.object(
            type(Subscription), '_require_hmac_client_secret',
            return_value=True,
        ):
            job = Subscription._enqueue_subscription_mutation(
                subscription, 'create', 'manual_sync',
            )
        return store, settings, subscription, job

    def test_mode_router_preserves_legacy_and_read_only_paths(self):
        store, settings, subscription = self._store_and_subscription('legacy')
        del store
        model = subscription.sudo()
        with patch.object(
            type(model), '_enqueue_v2_subscription_mutation',
            return_value='v2',
        ) as v2, patch.object(
            ShopifyConnectorWebhookSubscription,
            '_enqueue_subscription_mutation',
            return_value='legacy',
        ) as legacy:
            self.assertEqual(
                model._enqueue_subscription_mutation(
                    subscription, 'create', 'manual_sync',
                ),
                'legacy',
            )
            legacy.assert_called_once()
            v2.assert_not_called()

            self._set_mode(settings, 'read_only')
            self.assertEqual(
                model._enqueue_subscription_mutation(
                    subscription, 'create', 'manual_sync',
                ),
                'legacy',
            )
            self.assertEqual(legacy.call_count, 2)
            v2.assert_not_called()

            self._set_mode(settings, 'subscriptions')
            self.assertEqual(
                model._enqueue_subscription_mutation(
                    subscription, 'create', 'manual_sync',
                ),
                'v2',
            )
            v2.assert_called_once()

    def test_admission_requires_connector_admin_actor(self):
        model = self.env['shopify.connector.webhook.subscription']
        model.sudo()._v2_assert_actor()
        user = self.env['res.users'].sudo().create({
            'name': 'P11 non-admin %s' % uuid.uuid4().hex[:8],
            'login': 'p11-non-admin-%s' % uuid.uuid4().hex[:12],
            'email': 'p11-non-admin@example.invalid',
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        with self.assertRaises(AccessError):
            model.with_user(user)._v2_assert_actor()

    def test_enqueue_creates_one_admitted_run_and_job_without_attempt(self):
        store, settings, subscription, job = self._admitted_job()
        self.assertEqual(job.state, 'queued')
        self.assertEqual(job.run_id.state, 'admitted')
        self.assertEqual(job.run_id.store_id, store)
        self.assertEqual(job.company_id, store.company_id)
        self.assertEqual(
            job.expected_connection_generation,
            store.connection_generation,
        )
        self.assertEqual(
            job.expected_configuration_generation,
            settings.configuration_generation,
        )
        self.assertEqual(job.job_source, 'manual_sync')
        self.assertEqual(job.lane, 'interactive')
        self.assertFalse(job.current_attempt_token)
        self.assertEqual(
            self.env['shopify.connector.mutation.attempt'].sudo().search_count([
                ('job_id', '=', job.id),
            ]),
            0,
        )
        # Repeated admission coalesces the active operation identity.  It does
        # not create a second run, job, or pre-worker attempt row.
        model = subscription.sudo()
        with patch.object(
            type(model), '_require_hmac_client_secret', return_value=True,
        ):
            duplicate = model._enqueue_subscription_mutation(
                subscription, 'create', 'manual_sync',
            )
        self.assertEqual(duplicate, job)
        self.assertEqual(
            self.env['shopify.connector.run'].sudo().search_count([
                ('store_id', '=', store.id),
                ('request_key', '=', job.run_id.request_key),
            ]),
            1,
        )
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('run_id', '=', job.run_id.id),
            ]),
            1,
        )

    def test_admission_fences_generation_and_runtime_mode(self):
        store, settings, _subscription, job = self._admitted_job()
        model = self.env['shopify.connector.webhook.subscription'].sudo()
        self.assertEqual(model._v2_assert_job(job), settings)

        store._store_service_write('_lifecycle', {
            'connection_generation': store.connection_generation + 1,
        })
        store.invalidate_recordset()
        with self.assertRaises(ValidationError):
            model._v2_assert_job(job)

        _store, settings, _subscription, mode_job = self._admitted_job()
        settings.sudo()._v2_mode_surface().browse(settings.id).write({
            'v2_runtime_mode': 'read_only',
            'configuration_generation':
                settings.configuration_generation + 1,
        })
        with self.assertRaises(ValidationError):
            model._v2_assert_job(mode_job)

    def test_admission_rejects_job_from_foreign_company(self):
        foreign = self.env['res.company'].sudo().create({
            'name': 'P11 foreign %s' % uuid.uuid4().hex[:8],
        })
        Store = self.env['shopify.connector.store'].sudo()
        store = Store._store_service_create('_setup', {
            'name': 'P11 foreign store',
            'shop_domain': 'p11-foreign-%s.myshopify.com' % uuid.uuid4().hex[:8],
            'company_id': foreign.id,
        })
        store._store_service_write('_lifecycle', {'state': 'connected'})
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().create({'store_id': store.id})
        self._set_mode(settings, 'subscriptions')
        run = self.env['shopify.connector.run'].sudo()._create_service({
            'store_id': store.id,
            'request_key': 'p11-foreign-run-%s' % uuid.uuid4().hex,
            'workflow': 'webhook',
            'operation': 'webhook.subscription.create',
            'trigger': 'system',
            'scope_summary': 'P11 foreign test',
            'configuration_snapshot': {},
        })
        run._admit_service()
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'run_id': run.id,
            'job_source': 'manual_sync',
            'job_type': 'webhook_subscription_create',
            'state': 'queued',
            'payload_hash': 'p11-foreign-%s' % uuid.uuid4().hex,
            'res_model': 'shopify.connector.webhook.subscription',
            'res_id': 1,
            'expected_connection_generation': store.connection_generation,
            'expected_configuration_generation': settings.configuration_generation,
            'lane': 'interactive',
            'lane_priority': 100,
            'available_at': fields.Datetime.now(),
        })
        model = self.env[
            'shopify.connector.webhook.subscription'
        ].sudo().with_context(
            allowed_company_ids=[self.env.company.id],
        )
        self.assertNotIn(foreign, model.env.companies)
        with self.assertRaises(ValidationError):
            model._v2_assert_job(job)

    def test_readback_proves_create_without_invoking_mutation_again(self):
        store, _settings, subscription = self._store_and_subscription()
        callback = self.env[
            'shopify.connector.webhook.secret'
        ]._callback_url_for_store(store)
        callback_digest = hashlib.sha256(callback.encode()).hexdigest()
        attempt = SimpleNamespace(
            job_id=SimpleNamespace(run_id=True),
            run_id=True,
            store_id=store,
            remote_mutation_intent={
                'action': 'create',
                'topic_enum': subscription.topic_enum,
                'callback_url_digest': callback_digest,
                'expected_api_version': SHOPIFY_API_VERSION,
                'expected_include_fields': [],
            },
        )
        response = {
            'served_version': SHOPIFY_API_VERSION,
            'data': {
                'shop': {'myshopifyDomain': store.shop_domain},
                'webhookSubscriptions': {
                    'nodes': [{
                        'id': 'gid://shopify/WebhookSubscription/901',
                        'topic': subscription.topic_enum,
                        'uri': callback,
                        'apiVersion': {
                            'handle': SHOPIFY_API_VERSION,
                            'displayName': SHOPIFY_API_VERSION,
                            'supported': True,
                        },
                        'format': 'JSON',
                        'includeFields': [],
                    }],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None},
                },
            },
        }
        model = self.env[
            'shopify.connector.webhook.subscription'
        ].sudo()
        with patch.object(_ReadDelegate, 'read', return_value=response), patch.object(
            type(model), '_v2_assert_reconciliation_readback', return_value=True,
        ), patch.object(
            WebhookSubscriptionMutationGateway,
            'execute', side_effect=AssertionError('readback must not resend'),
        ) as mutation:
            result = model._reconcile_subscription_mutation(
                attempt, reconciliation_job=SimpleNamespace(id=1),
            )
        self.assertEqual(result['verdict'], 'applied')
        self.assertEqual(result['action'], 'succeed')
        mutation.assert_not_called()

    def test_readback_missing_create_blocks_without_resend(self):
        store, _settings, subscription = self._store_and_subscription()
        digest = 'a' * 64
        attempt = SimpleNamespace(
            job_id=SimpleNamespace(run_id=True),
            run_id=True,
            store_id=store,
            remote_mutation_intent={
                'action': 'create',
                'topic_enum': subscription.topic_enum,
                'callback_url_digest': digest,
                'expected_api_version': SHOPIFY_API_VERSION,
                'expected_include_fields': [],
            },
        )
        response = {
            'served_version': SHOPIFY_API_VERSION,
            'data': {
                'shop': {'myshopifyDomain': store.shop_domain},
                'webhookSubscriptions': {
                    'nodes': [],
                    'pageInfo': {'hasNextPage': False, 'endCursor': None},
                },
            },
        }
        model = self.env[
            'shopify.connector.webhook.subscription'
        ].sudo()
        with patch.object(_ReadDelegate, 'read', return_value=response), patch.object(
            type(model), '_v2_assert_reconciliation_readback', return_value=True,
        ), patch.object(
            WebhookSubscriptionMutationGateway,
            'execute', side_effect=AssertionError('readback must not resend'),
        ) as mutation:
            result = model._reconcile_subscription_mutation(
                attempt, reconciliation_job=SimpleNamespace(id=1),
            )
        self.assertEqual(result['verdict'], 'not_applied')
        self.assertEqual(result['action'], 'block_manual_review')
        self.assertEqual(result['manual_review_subreason'], 'duplicate_risk')
        mutation.assert_not_called()

    def test_post_c2_scope_drift_still_allows_exact_readback(self):
        store, settings, subscription, job = self._admitted_job()
        token = uuid.uuid4().hex
        job.sudo().write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
            'current_attempt_token': token,
            'owner_worker_ref': 'p11-drift-test',
            'running_since': fields.Datetime.now(),
        })
        intent = {
            'action': 'create',
            'subscription_id': subscription.id,
            'topic_enum': subscription.topic_enum,
            'callback_url_digest': subscription.expected_callback_url_digest,
            'expected_api_version': SHOPIFY_API_VERSION,
            'expected_include_fields': [],
        }
        attempt = self.env[
            'shopify.connector.mutation.attempt'
        ].with_context(**{
            C2_SENTINEL_CONTEXT: C2_SIDE_CURSOR_SENTINEL,
        })._create_attempt_intent({
            'job_id': job.id,
            'attempt_token': token,
            'mutation_domain': job.job_type,
            'expected_connection_generation': store.connection_generation,
            'expected_configuration_generation':
                settings.configuration_generation,
            'expected_store_identity': store.shop_domain,
            'remote_mutation_intent': intent,
            'preconditions_snapshot': {
                'expected_connection_generation':
                    store.connection_generation,
                'expected_configuration_generation':
                    settings.configuration_generation,
            },
            'business_intent_fingerprint': canonical_sha256(intent),
            'exact_request_fingerprint': canonical_sha256({
                'operation': 'P11 drift test', 'variables': {},
            }),
            'shopify_idempotency_key': uuid.uuid4().hex,
        })

        settings.sudo()._v2_mode_surface().browse(settings.id).write({
            'v2_runtime_mode': 'read_only',
            'configuration_generation':
                settings.configuration_generation + 1,
        })
        store._store_service_write('_lifecycle', {
            'connection_generation': store.connection_generation + 1,
        })
        job.run_id._request_cancel_service('P11 post-C2 drift test')
        store.invalidate_recordset()
        settings.invalidate_recordset()
        job.invalidate_recordset()
        attempt.invalidate_recordset()

        Dispatch = self.env['shopify.connector.job.dispatch']
        reconciliation = Dispatch._recover_committed_attempt_to_reconciliation(
            job,
            attempt,
            'post_c2_owner_recovery',
            'dispatcher_recovery',
        )
        self.assertTrue(reconciliation)
        self.assertEqual(reconciliation.run_id, attempt.run_id)
        self.assertEqual(
            reconciliation.expected_connection_generation,
            store.connection_generation,
        )
        self.assertEqual(
            reconciliation.expected_configuration_generation,
            settings.configuration_generation,
        )
        reconciliation.sudo().write({
            'state': 'running',
            'started_at': fields.Datetime.now(),
        })

        callback = self.env[
            'shopify.connector.webhook.secret'
        ]._callback_url_for_store(store)
        response = {
            'served_version': SHOPIFY_API_VERSION,
            'data': {
                'shop': {'myshopifyDomain': store.shop_domain},
                'webhookSubscriptions': {
                    'nodes': [{
                        'id': 'gid://shopify/WebhookSubscription/902',
                        'topic': subscription.topic_enum,
                        'uri': callback,
                        'apiVersion': {
                            'handle': SHOPIFY_API_VERSION,
                            'displayName': SHOPIFY_API_VERSION,
                            'supported': True,
                        },
                        'format': 'JSON',
                        'includeFields': [],
                    }],
                    'pageInfo': {
                        'hasNextPage': False, 'endCursor': None,
                    },
                },
            },
        }
        model = subscription.sudo()
        with patch.object(
            _ReadDelegate, 'read', return_value=response,
        ), patch.object(
            WebhookSubscriptionMutationGateway,
            'execute',
            side_effect=AssertionError('readback must not resend'),
        ) as mutation:
            result = model._reconcile_subscription_mutation(
                attempt, reconciliation_job=reconciliation,
            )
        self.assertEqual(result['verdict'], 'applied')
        mutation.assert_not_called()

    def test_granted_scope_snapshot_is_parsed_fail_closed(self):
        store, _settings, subscription = self._store_and_subscription()
        model = subscription.sudo()
        store.sudo()._store_service_write('_connection_probe', {
            'granted_scopes': json.dumps(['read_products', 'write_products']),
        })
        store.invalidate_recordset()
        self.assertEqual(
            model._v2_granted_scopes(store),
            ('read_products', 'write_products'),
        )
        store.sudo()._store_service_write(
            '_connection_probe', {'granted_scopes': '{malformed'},
        )
        store.invalidate_recordset()
        self.assertEqual(model._v2_granted_scopes(store), ())
