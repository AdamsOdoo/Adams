"""Focused W1 tests; live Shopify calls are deliberately not made here."""

import base64
import hashlib
import hmac
from pathlib import Path
from types import SimpleNamespace

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_webhook.controllers.shopify_connector_webhook import (
    MAX_WEBHOOK_BODY_BYTES,
    ShopifyConnectorWebhookController,
)
from odoo.addons.shopify_connector_webhook.models.shopify_connector_webhook_delivery import (
    DELIVERY_STATES,
    WEBHOOK_RETENTION_DAYS,
)
from odoo.addons.shopify_connector_webhook.models.shopify_connector_webhook_registry import (
    MVP_TOPIC_CATALOG,
)
from odoo.addons.shopify_connector_webhook.models.shopify_connector_webhook_credential import (
    WEBHOOK_CLIENT_SECRET_GRACE_HOURS,
)
from odoo.addons.shopify_connector_webhook.models.shopify_connector_webhook_subscription import (
    _bounded_sweep_remaining,
    _create_retry_allowed,
    _scheduled_reconciliation_bucket_ids,
    _scheduled_reconciliation_bucket_limits,
)


@tagged('post_install', '-at_install')
class TestShopifyConnectorWebhookW1(TransactionCase):
    """No-network contracts for ingress, evidence, ACL and dispatch seams."""

    def test_hmac_uses_exact_raw_bytes_and_rejects_missing_or_tampered(self):
        raw = b'{"id":1,"title":"caf\xc3\xa9"}'
        secret = 'client-secret-for-test'
        signature = base64.b64encode(
            hmac.new(secret.encode(), raw, hashlib.sha256).digest()
        ).decode()
        self.assertTrue(
            ShopifyConnectorWebhookController.verify_hmac(
                raw, secret, signature,
            )
        )
        self.assertFalse(
            ShopifyConnectorWebhookController.verify_hmac(
                raw + b' ', secret, signature,
            )
        )
        self.assertFalse(
            ShopifyConnectorWebhookController.verify_hmac(raw, secret, None)
        )
        self.assertFalse(
            ShopifyConnectorWebhookController.verify_hmac(
                raw, secret, signature[:-1] + '0',
            )
        )

    def test_declared_oversize_is_rejected_before_body_read(self):
        class ExplodingStream:
            def read(self, _size):
                raise AssertionError('declared oversize must not be buffered')

        request = type('Request', (), {
            'headers': {'Content-Length': str(MAX_WEBHOOK_BODY_BYTES + 1)},
            'stream': ExplodingStream(),
        })()
        self.assertEqual(
            ShopifyConnectorWebhookController.read_bounded_body(request),
            (False, 413),
        )

    def test_unknown_length_body_is_bounded_in_fixed_chunks(self):
        class ChunkedStream:
            def __init__(self):
                self.calls = []
                self.remaining = MAX_WEBHOOK_BODY_BYTES + 1

            def read(self, size):
                self.calls.append(size)
                amount = min(size, self.remaining)
                self.remaining -= amount
                return b'x' * amount

        stream = ChunkedStream()
        request = type('Request', (), {
            'headers': {}, 'stream': stream,
        })()
        body, status = ShopifyConnectorWebhookController.read_bounded_body(request)
        self.assertFalse(body)
        self.assertEqual(status, 413)
        self.assertTrue(stream.calls)
        self.assertLessEqual(max(stream.calls), 64 * 1024)

    def test_registry_separates_catalog_from_active_subscriptions(self):
        registry = self.env['shopify.connector.webhook.registry']
        active = set(registry.allowed_topics())
        self.assertIn('app/uninstalled', active)
        self.assertIn('products/update', MVP_TOPIC_CATALOG)
        if 'products/update' in active:
            # The optional product-domain addon may extend the active registry
            # after W1 is installed. Its bounded slice activates create/update
            # only; delete remains catalogued but unsubscribable.
            self.assertIn('products/create', active)
            self.assertNotIn('products/delete', active)
            self.assertTrue(registry.topic_spec('products/update'))
        else:
            self.assertEqual(registry.topic_spec('products/update'), False)

    def test_delivery_evidence_has_no_payload_field_and_allowlists_identity(self):
        delivery_model = self.env['shopify.connector.webhook.delivery']
        identity = delivery_model._minimal_resource_identity({
            'id': 123,
            'admin_graphql_api_id': 'gid://shopify/Product/123',
            'title': 'PII or business payload must not persist',
            'email': 'not-stored@example.invalid',
            'line_items': [{'price': '99.00'}],
        })
        self.assertEqual(identity['id'], '123')
        self.assertEqual(
            identity['admin_graphql_api_id'], 'gid://shopify/Product/123',
        )
        self.assertNotIn('title', identity)
        self.assertNotIn('email', identity)
        self.assertNotIn('line_items', identity)
        self.assertNotIn('payload', delivery_model._fields)
        self.assertEqual(
            {state for state, _label in DELIVERY_STATES},
            {'received', 'queued', 'processed', 'ignored', 'failed', 'manual_review'},
        )
        self.assertEqual(WEBHOOK_RETENTION_DAYS, 30)

    def test_callback_token_digest_is_not_a_sequential_store_id(self):
        from odoo.addons.shopify_connector_webhook.models.shopify_connector_webhook_secret import (
            callback_token_digest,
        )
        first = callback_token_digest('random-callback-token-a')
        second = callback_token_digest('random-callback-token-b')
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, second)
        self.assertNotEqual(first, hashlib.sha256(b'1').hexdigest())

    def test_production_path_and_static_guards(self):
        root = Path(__file__).resolve().parents[1]
        controller = (root / 'controllers' / 'shopify_connector_webhook.py').read_text()
        delivery = (root / 'models' / 'shopify_connector_webhook_delivery.py').read_text()
        subscription = (root / 'models' / 'shopify_connector_webhook_subscription.py').read_text()
        dispatch = (root / 'models' / 'shopify_connector_webhook_dispatch.py').read_text()
        self.assertLess(
            controller.index('verify_hmac'), controller.index('json.loads'),
        )
        self.assertIn('read_bounded_body', controller)
        self.assertNotIn('get_data(', controller)
        self.assertIn('Delivery._ingest(', controller)
        self.assertNotIn('process_delivery(', controller)
        self.assertIn('UNIQUE(store_id, delivery_id)', delivery)
        self.assertIn('if api_version != SHOPIFY_API_VERSION:', delivery)
        self.assertIn("'api_version': SHOPIFY_API_VERSION", delivery)
        self.assertIn("'observed_api_version': str(", subscription)
        self.assertNotIn("'api_version': str(node.get('apiVersion')", subscription)
        self.assertIn('execute_business(', subscription)
        self.assertNotIn('client.execute(store', subscription)
        self.assertIn('webhook_subscription_create', dispatch)
        self.assertIn('REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE', dispatch)
        # The API version is owned by the core constant.  This guard must
        # prove that the controller imports and compares that symbol rather
        # than freezing a second literal in the public route.
        self.assertIn(
            'from odoo.addons.shopify_connector_core.tools.api_version import (\n'
            '    SHOPIFY_API_VERSION,\n'
            ')',
            controller,
        )
        self.assertIn('if api_version != SHOPIFY_API_VERSION:', controller)
        self.assertIn(
            'store.api_version != SHOPIFY_API_VERSION', controller,
        )
        self.assertIn(
            'delivered_api_version != SHOPIFY_API_VERSION', controller,
        )
        self.assertNotIn("'2026-07'", controller)
        self.assertNotIn('"2026-07"', controller)
        tour = (root.parent / 'shopify_connector_core' / 'static' / 'src' /
                'js' / 'tours' / 'shopify_connector_s1_setup_tour.js').read_text()
        self.assertIn('.sc_setup__completion_pending', tour)
        self.assertNotIn('.sc_setup__completion_action', tour)
        self.assertNotIn("value='offline_access_token'", tour)
        self.assertIn('#sc_setup_client_id', tour)
        self.assertIn('#sc_setup_client_secret[type=\'password\']', tour)

    def test_setup_activation_defers_completion_until_stored_webhook_proof(self):
        """The installed W1 hook cannot make the setup wizard false-green."""
        addon_root = Path(__file__).resolve().parents[1]
        core_root = addon_root.parent / 'shopify_connector_core'
        core_setup = (core_root / 'models' /
                      'shopify_connector_setup_wizard.py').read_text()
        webhook_setup = (addon_root / 'models' /
                         'shopify_connector_webhook_setup.py').read_text()
        wizard_js = (core_root / 'static' / 'src' / 'js' /
                     'shopify_connector_setup_wizard.js').read_text()
        self.assertIn('def _activation_completion_policy', core_setup)
        self.assertLess(
            core_setup.index('_activation_completion_policy(store, settings)'),
            core_setup.index("'setup_completed_at': fields.Datetime.now()"),
        )
        self.assertIn("'complete': False", webhook_setup)
        self.assertIn("source='setup_readiness_check'", webhook_setup)
        self.assertIn("'setup_completion_state': status['state']", webhook_setup)
        self.assertIn('setup_completion_state', wizard_js)
        self.assertIn('connected_job_proof', webhook_setup)
        self.assertIn('expected_connection_generation', webhook_setup)
        self.assertIn('Setup is waiting for verification',
                      (core_root / 'static' / 'src' / 'xml' /
                       'shopify_connector_setup_wizard.xml').read_text())
        self.assertIn('read-back proof', webhook_setup)

    def test_setup_projection_never_treats_connected_without_proof_as_complete(self):
        """Static fence for the two-stage lifecycle state projection."""
        setup = (Path(__file__).resolve().parents[1] / 'models' /
                 'shopify_connector_webhook_setup.py').read_text()
        self.assertIn("if settings.setup_completed_at:", setup)
        self.assertIn("if store.state != 'connected':", setup)
        self.assertIn("'state': 'pending'", setup)
        self.assertIn("'state': 'ready_to_complete'", setup)
        self.assertIn('job.expected_connection_generation', setup)
        self.assertNotIn("setup_completed_at': fields.Datetime.now()", setup)

    def test_activation_fences_are_fresh_and_client_secret_gate_is_truthful(self):
        store = (Path(__file__).resolve().parents[2] / 'shopify_connector_core' /
                 'models' / 'shopify_connector_store.py').read_text()
        wizard = (Path(__file__).resolve().parents[2] / 'shopify_connector_core' /
                  'models' / 'shopify_connector_setup_wizard.py').read_text()
        setup = (Path(__file__).resolve().parents[1] / 'models' /
                 'shopify_connector_webhook_setup.py').read_text()
        self.assertLess(
            store.index('locked_state, locked_generation ='),
            store.index("if locked_state == 'connected':"),
        )
        self.assertIn('def _activation_preflight', wizard)
        self.assertIn('def _activation_completion_guard', wizard)
        self.assertIn('Credential._lifecycle_credential_version', setup)
        self.assertIn('store._lock_store_for_lifecycle()', setup)
        self.assertIn("'client_secret_required'", setup)
        self.assertIn('Client ID + Client secret', setup)
        self.assertIn("'setup_completion_code': status.get('code', False)", setup)

    def test_setup_reconcile_progression_does_not_reenqueue_child_work(self):
        setup = (Path(__file__).resolve().parents[1] / 'models' /
                 'shopify_connector_webhook_setup.py').read_text()
        subscription = (Path(__file__).resolve().parents[1] / 'models' /
                        'shopify_connector_webhook_subscription.py').read_text()
        self.assertIn('CHILD_SETUP_JOB_TYPES', setup)
        self.assertIn("'child_work_pending'", setup)
        self.assertIn("if status.get('code') == 'child_work_pending'", setup)
        self.assertIn(
            "('expected_connection_generation', '=', store.connection_generation)",
            setup,
        )
        self.assertIn('subscription.last_job_id', setup)
        self.assertIn("if subscription.state == 'active':", setup)
        self.assertIn('Historical job rows remain immutable audit', setup)
        self.assertIn('self._require_hmac_client_secret(store)', subscription)
        self.assertIn('self._require_hmac_client_secret(subscription.store_id)',
                      subscription)
        self.assertIn('def _hmac_epoch_for_admitted_job', subscription)
        self.assertIn('Credential._lifecycle_credential_version', subscription)
        self.assertIn("'hmac_credential_epoch'] = (", subscription)
        self.assertIn('job.expected_connection_generation', subscription)
        self.assertIn('stale active job', setup)
        self.assertIn("'expected_connection_generation', '=',\n                     store.connection_generation", subscription)
        self.assertIn("'state': 'cancelled'", subscription)
        self.assertIn('A stale webhook reconciliation job is in', subscription)

    def test_bootstrap_lifecycle_and_scheduler_guards_are_production_paths(self):
        root = Path(__file__).resolve().parents[1]
        subscription = (root / 'models' /
                        'shopify_connector_webhook_subscription.py').read_text()
        dispatch = (root / 'models' /
                    'shopify_connector_webhook_dispatch.py').read_text()
        readiness = (root / 'models' /
                     'shopify_connector_webhook_readiness.py').read_text()
        secret = (root / 'models' /
                  'shopify_connector_webhook_secret.py').read_text()
        self.assertIn("'webhook_subscription_bootstrap'", dispatch)
        self.assertIn(
            "_admit_lifecycle(\n                store, 'readiness_probe'",
            subscription,
        )
        self.assertIn('bootstrap=True', dispatch)
        self.assertIn('webhook_reconciliation_scheduled_at', subscription)
        self.assertIn('_commit_progress', subscription)
        self.assertIn('not_applicable=True', readiness)
        self.assertIn('rotation is disabled', secret)

    def test_bootstrap_uses_one_snapshot_and_fences_superseded_evidence(self):
        subscription = (Path(__file__).resolve().parents[1] / 'models' /
                        'shopify_connector_webhook_subscription.py').read_text()
        self.assertEqual(
            subscription.count("_admit_lifecycle(\n                store, 'readiness_probe'"),
            1,
        )
        self.assertIn("lifecycle_snapshot['token']", subscription)
        self.assertIn(
            'store._lifecycle_probe_superseded(lifecycle_snapshot)',
            subscription,
        )
        self.assertIn('no evidence was written', subscription)

    def test_duplicate_risk_block_is_a_hard_no_resend_fence(self):
        blocked = SimpleNamespace(
            last_job_id=SimpleNamespace(state='blocked_manual_review'),
        )
        terminal = SimpleNamespace(
            last_job_id=SimpleNamespace(state='failed_final'),
        )
        self.assertFalse(_create_retry_allowed(blocked, 'connected', False))
        self.assertTrue(_create_retry_allowed(terminal, 'connected', False))
        self.assertFalse(_create_retry_allowed(blocked, 'connected', True))

    def test_cron_progress_reports_bounded_batch_remaining_to_zero(self):
        self.assertEqual(_bounded_sweep_remaining(3, 0), 3)
        self.assertEqual(_bounded_sweep_remaining(3, 3), 0)
        self.assertEqual(_bounded_sweep_remaining(20, 20), 0)
        self.assertEqual(_bounded_sweep_remaining(20, 7), 13)
        self.assertEqual(
            _scheduled_reconciliation_bucket_limits(20, 20), (20, 20, 0),
        )
        self.assertEqual(
            _scheduled_reconciliation_bucket_limits(20, 7), (20, 7, 13),
        )
        self.assertEqual(
            _scheduled_reconciliation_bucket_limits(20, 0), (20, 0, 20),
        )
        new_ids = tuple(range(1, 25))
        timestamped_ids = tuple(range(101, 121))
        self.assertEqual(
            _scheduled_reconciliation_bucket_ids(
                new_ids, timestamped_ids, 20,
            ),
            tuple(range(1, 21)),
        )
        self.assertEqual(
            _scheduled_reconciliation_bucket_ids(
                new_ids[20:], timestamped_ids, 20,
            ),
            tuple(range(21, 25)) + tuple(range(101, 117)),
        )
        subscription = (Path(__file__).resolve().parents[1] / 'models' /
                        'shopify_connector_webhook_subscription.py').read_text()
        self.assertIn('_bounded_sweep_remaining(len(stores), processed)', subscription)
        self.assertIn(
            "('webhook_reconciliation_scheduled_at', '=', False)",
            subscription,
        )
        self.assertIn(
            "('webhook_reconciliation_scheduled_at', '!=', False)",
            subscription,
        )
        self.assertIn(
            'Store.browse(_scheduled_reconciliation_bucket_ids(', subscription,
        )
        self.assertNotIn('NULLS FIRST', subscription)
        self.assertNotIn(
            "order='webhook_reconciliation_scheduled_at asc, id asc',\n            limit=max(1, min(int(limit or 20), 100))",
            subscription,
        )
        self.assertNotIn("search_count([\n                    ('state', '=', 'connected')", subscription)

    def test_client_secret_grace_is_durable_and_current_then_previous_only(self):
        credential = (Path(__file__).resolve().parents[1] / 'models' /
                      'shopify_connector_webhook_credential.py').read_text()
        secret = (Path(__file__).resolve().parents[1] / 'models' /
                  'shopify_connector_webhook_secret.py').read_text()
        controller = (Path(__file__).resolve().parents[1] / 'controllers' /
                      'shopify_connector_webhook.py').read_text()
        self.assertGreaterEqual(WEBHOOK_CLIENT_SECRET_GRACE_HOURS, 1)
        self.assertIn("groups='base.group_no_one'", credential)
        self.assertIn('webhook_previous_client_secret_expires_at', credential)
        self.assertIn('def _current_client_secret_locked', credential)
        self.assertIn('_lock_store_for_lifecycle()', credential)
        self.assertIn("fields.Datetime.add(", credential)
        self.assertIn("> fields.Datetime.now()", credential)
        self.assertIn('_hmac_secrets_for_store', secret)
        self.assertIn('for secret in client_secrets', controller)
        self.assertIn('rotation grace window',
                      (Path(__file__).resolve().parents[1] / 'models' /
                       'shopify_connector_webhook_readiness.py').read_text())

    def test_secret_predecessor_capture_obeys_store_then_credential_lock_order(self):
        addon_root = Path(__file__).resolve().parents[1]
        credential = (addon_root / 'models' /
                      'shopify_connector_webhook_credential.py').read_text()
        core_credential = (addon_root.parent / 'shopify_connector_core' /
                           'models' /
                           'shopify_connector_store_credential.py').read_text()
        capture = credential.index('def _current_client_secret_locked')
        lock = credential.index('store._lock_store_for_lifecycle()', capture)
        read = credential.index("self.sudo().search([", lock)
        self.assertLess(lock, read)
        # The extension must preserve the core's global store -> credential
        # ordering. This source invariant is the regression fence for a
        # concurrent rotation that could otherwise capture a non-predecessor.
        self.assertIn(
            'store._lock_store_for_lifecycle()', core_credential,
        )
        self.assertGreaterEqual(
            credential.count('_current_client_secret_locked(store)'), 4,
        )
        self.assertIn(
            'The core mutation service takes this same store -> credential lock',
            credential,
        )

    def test_uncertain_create_requires_full_identity_and_carries_gid(self):
        subscription = (Path(__file__).resolve().parents[1] / 'models' /
                        'shopify_connector_webhook_subscription.py').read_text()
        for field in ('topic', 'uri_digest', 'api_version', 'format',
                      'shopify_subscription_gid', 'domain_payload'):
            self.assertIn(field, subscription)

    def test_installed_module_security_and_retention_contracts_are_declared(self):
        root = Path(__file__).resolve().parents[1]
        acl = (root / 'security' / 'ir.model.access.csv').read_text()
        rules = (root / 'security' /
                 'shopify_connector_webhook_company_rules.xml').read_text()
        cron = (root / 'data' /
                'shopify_connector_webhook_cron.xml').read_text()
        controller = (root / 'controllers' /
                      'shopify_connector_webhook.py').read_text()
        self.assertIn('group_shopify_connector_admin', acl)
        self.assertIn(
            "domain_force\">[('company_id', 'in', company_ids)]", rules,
        )
        self.assertIn('run_retention_sweep', cron)
        self.assertIn("auth='public'", controller)
        self.assertIn("methods=['POST']", controller)

    def test_topic_registry_has_required_assessment_catalog(self):
        self.assertTrue({
            'products/create', 'products/update', 'products/delete',
            'inventory_levels/update', 'orders/create', 'orders/updated',
            'orders/cancelled', 'refunds/create', 'fulfillments/create',
            'fulfillments/update', 'app/uninstalled',
        }.issubset(MVP_TOPIC_CATALOG))
