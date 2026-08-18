"""Focused W1 tests; live Shopify calls are deliberately not made here."""

import base64
import hashlib
import hmac
from pathlib import Path
from types import SimpleNamespace

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)
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
        self.assertEqual(active, {'app/uninstalled'})
        self.assertIn('products/update', MVP_TOPIC_CATALOG)
        self.assertNotIn('products/update', active)
        self.assertEqual(
            registry.topic_spec('products/update'), False,
        )

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
        self.assertIn('execute_business(', subscription)
        self.assertNotIn('client.execute(store', subscription)
        self.assertIn('webhook_subscription_create', dispatch)
        self.assertIn('REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE', dispatch)
        self.assertIn(SHOPIFY_API_VERSION, controller)

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
