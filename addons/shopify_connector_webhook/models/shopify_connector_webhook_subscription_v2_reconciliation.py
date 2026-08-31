"""P11 V2 subscription planning and readback model extension.

The mutation adapter owns admission and transport; this extension owns the
bounded current-state read, desired-state plan, scope snapshot and
reconciliation projection.  It is imported after the P11 runtime extension so
the same Odoo model inheritance remains one composed service.
"""

import json

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)

from ..integration.shopify.webhook_subscription_mutation_gateway import (
    SHOPIFY_API_VERSION,
)
from ..integration.shopify.webhook_subscription_planner import (
    plan_webhook_subscriptions,
)
from ..integration.shopify.webhook_subscription_planner_contracts import (
    MAX_GRANTED_SCOPES,
    WebhookSubscriptionPlannerError,
    WebhookTopicSpec,
    scopes,
)
from ..integration.shopify.webhook_subscription_read_gateway import (
    SUBSCRIPTIONS_OPERATION,
    SUBSCRIPTIONS_QUERY,
    WebhookSubscriptionReadError,
    WebhookSubscriptionReadGateway,
)
from .shopify_connector_webhook_subscription import CREATE_RETRY_STATES
from .shopify_connector_webhook_subscription_v2_runtime import (
    V2_SUBSCRIPTION_MUTATIONS,
)


class _ReadDelegate:
    """Adapt the durable Odoo business-read lease to the pure P07 gateway."""

    def __init__(self, client, job, attempt, store=None):
        if store is None:
            store = attempt
            attempt = False
        self.client = client
        self.job = job
        self.attempt = attempt
        self.store = store

    def read(self, operation_key, variables):
        if operation_key != SUBSCRIPTIONS_OPERATION:
            raise WebhookSubscriptionReadError(
                'The subscription read operation is not allowlisted.',
                'invalid_operation',
            )
        try:
            call = (
                self.client._execute_v2_reconciliation_read(
                    self.job,
                    self.attempt,
                    self.store,
                    SUBSCRIPTIONS_QUERY,
                    variables,
                )
                if self.attempt else self.client.execute_business(
                    self.job,
                    self.store,
                    SUBSCRIPTIONS_QUERY,
                    variables,
                )
            )
            with call as result:
                return result
        except Exception as exc:
            raise WebhookSubscriptionReadError(
                'Shopify subscription read could not be completed.',
                'shopify_unavailable',
            ) from exc


class ShopifyConnectorWebhookSubscriptionV2Reconciliation(models.Model):
    """Add bounded planning/readback behavior to the composed subscription model."""

    _inherit = 'shopify.connector.webhook.subscription'

    @api.model
    def _v2_assert_reconciliation_readback(self, attempt, reconciliation_job):
        """Authorize readback from durable C2 lineage, not stale write scope.

        A mode, configuration, cancellation, or original-run change after C2
        must stop another mutation but must not suppress the read-only proof
        needed to resolve the already-attempted remote effect.  The read job
        itself still has to match the live connected store generation.
        """
        if (
            not attempt
            or not attempt.exists()
            or not attempt.run_id
            or attempt.mutation_domain not in V2_SUBSCRIPTION_MUTATIONS
            or not reconciliation_job
            or not reconciliation_job.exists()
        ):
            raise ValidationError(
                'The V2 subscription readback lineage is incomplete.'
            )
        original = attempt.job_id
        store = attempt.store_id
        run = attempt.run_id
        settings = self._v2_settings(store)
        if (
            not original
            or attempt.observed_outcome != 'uncertain'
            or attempt.expected_store_identity != store.shop_domain
            or original.store_id != store
            or run.store_id != store
            or original.company_id != store.company_id
            or run.company_id != store.company_id
            or store.company_id not in self.env.companies
            or store.state != 'connected'
            or not settings
            or settings.company_id != store.company_id
            or reconciliation_job.job_type
            != 'webhook_subscription_mutation_reconcile'
            or reconciliation_job.job_source != 'reconciliation'
            or reconciliation_job.mutation_attempt_id != attempt
            or reconciliation_job.parent_job_id != original
            or reconciliation_job.run_id != run
            or reconciliation_job.store_id != store
            or reconciliation_job.company_id != store.company_id
            or reconciliation_job.state != 'running'
        ):
            raise ValidationError(
                'The V2 subscription readback identity is stale or invalid.'
            )
        return True

    @api.model
    def _v2_readback(self, attempt, reconciliation_job):
        store = attempt.store_id
        collection = WebhookSubscriptionReadGateway(
            _ReadDelegate(
                self.env['shopify.connector.api.client'],
                reconciliation_job,
                attempt,
                store,
            ),
            store_domain=store.shop_domain,
        ).read_all()
        intent = dict(attempt.remote_mutation_intent or {})
        actual = collection.to_legacy_list()
        if intent.get('action') == 'delete':
            target = intent.get('target_gid')
            found = [item for item in actual if item.get('id') == target]
            if not found:
                return {
                    'verdict': 'applied',
                    'observed_store_identity': collection.store_domain,
                    'action': 'succeed',
                    'error_class': False,
                    'manual_review_subreason': False,
                    'message': 'Readback confirmed the exact subscription is absent.',
                    'evidence': {'subscription_present': False},
                }
            return {
                'verdict': 'not_applied',
                'observed_store_identity': collection.store_domain,
                'action': 'block_manual_review',
                'error_class': 'duplicate_risk',
                'manual_review_subreason': 'duplicate_risk',
                'message': 'Readback still finds the exact subscription; no delete resend was issued.',
                'evidence': {'subscription_present': True},
            }
        desired = WebhookTopicSpec(
            intent.get('topic_enum') or intent.get('topic'),
            include_fields=tuple(intent.get('expected_include_fields') or ()),
            api_version=intent.get('expected_api_version', SHOPIFY_API_VERSION),
        )
        plan = plan_webhook_subscriptions(
            [desired],
            collection,
            callback_uri_digest=intent.get('callback_url_digest'),
        )
        keep = next((item for item in plan.decisions if item.action == 'keep'), None)
        if keep and not plan.blocked:
            observed = keep.observed
            return {
                'verdict': 'applied',
                'observed_store_identity': collection.store_domain,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Readback confirmed the exact desired subscription.',
                'evidence': {'subscription_found': True, 'plan': plan.as_dict()},
                'domain_payload': {
                    'shopify_subscription_gid': observed.id,
                    'actual_topic': observed.topic,
                    'actual_uri_digest': observed.uri_digest,
                    'actual_api_version': observed.observed_api_version,
                    'actual_format': observed.format,
                    'actual_include_fields': list(observed.include_fields),
                },
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': collection.store_domain,
            'action': 'block_manual_review',
            'error_class': 'duplicate_risk',
            'manual_review_subreason': 'duplicate_risk',
            'message': 'Readback did not prove the desired subscription; no resend was issued.',
            'evidence': {'subscription_found': False, 'plan': plan.as_dict()},
        }

    @api.model
    def _reconcile_subscription_mutation(self, attempt, reconciliation_job=None):
        if not attempt.run_id:
            return super()._reconcile_subscription_mutation(
                attempt, reconciliation_job,
            )
        try:
            self._v2_assert_reconciliation_readback(
                attempt, reconciliation_job,
            )
            return self._v2_readback(attempt, reconciliation_job)
        except (
            ValidationError,
            WebhookSubscriptionReadError,
            ShopifyClientError,
            ShopifyQuiescedError,
        ):
            return {
                'verdict': 'inconclusive',
                'observed_store_identity': attempt.store_id.shop_domain,
                'action': 'reconcile',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'Subscription readback was unavailable; no mutation resend was issued.',
                'evidence': {'readback_failure': True},
            }

    @api.model
    def _v2_granted_scopes(self, store):
        """Return the last server-confirmed scope snapshot, fail-closed.

        ``granted_scopes`` is an Odoo Text field containing the JSON array
        written by the connection probe.  A missing, malformed, or
        structurally invalid snapshot must not be treated as permission to
        create subscriptions: the planner will consequently block topics
        that require scopes until a fresh valid probe is stored.
        """
        raw = getattr(store, 'granted_scopes', False)
        if not raw:
            return ()
        try:
            snapshot = json.loads(raw)
            return scopes(
                snapshot,
                'granted_scopes',
                maximum=MAX_GRANTED_SCOPES,
            )
        except (TypeError, ValueError, WebhookSubscriptionPlannerError):
            return ()

    @api.model
    def _reconcile_store(self, store, source='scheduled_sync', job=None, bootstrap=False):
        if not self._v2_mode_enabled(store):
            return super()._reconcile_store(
                store, source=source, job=job, bootstrap=bootstrap,
            )
        store.ensure_one()
        self._require_hmac_client_secret(store)
        if store.state != 'connected' or not job:
            raise ValidationError(
                'V2 subscription reconciliation requires a connected store '
                'and a durable read job.'
            )
        Registry = self.env['shopify.connector.webhook.registry']
        expected = self._ensure_expected_for_store(store)
        callback = self.env[
            'shopify.connector.webhook.secret'
        ]._callback_url_for_store(store)
        collection = WebhookSubscriptionReadGateway(
            _ReadDelegate(self.env['shopify.connector.api.client'], job, store),
            store_domain=store.shop_domain,
        ).read_all()
        active_topics = Registry.allowed_topics()
        self._reconcile_registry_removed_subscriptions(
            store, active_topics, collection.to_legacy_list(), source=source,
            epoch=self._credential_epoch(store),
        )
        specs = []
        for topic, value in Registry._get_topic_registry().items():
            specs.append(WebhookTopicSpec(
                value['enum'],
                required_scopes=tuple(value.get('required_scopes') or ()),
                include_fields=tuple(value.get('include_fields') or ()),
            ))
        plan = plan_webhook_subscriptions(
            specs, collection, callback_uri=callback,
            granted_scopes=self._v2_granted_scopes(store),
        )
        by_topic = {record.topic_enum: record for record in expected}
        now = fields.Datetime.now()
        epoch = self._credential_epoch(store)
        if plan.blocked:
            for decision in plan.decisions:
                if decision.action != 'block':
                    continue
                record = by_topic.get(decision.topic)
                if record:
                    record._service_write({
                        'state': 'manual_review',
                        'last_reconciled_at': now,
                        'hmac_credential_epoch': epoch,
                        'last_error': (
                            'Subscription reconciliation requires operator '
                            'review: %s.' % decision.reason_code
                        ),
                    })
            return expected
        executable = {decision.key for decision in plan.require_executable()}
        for decision in plan.decisions:
            record = by_topic.get(decision.topic)
            if not record:
                continue
            observed = decision.observed
            if decision.action == 'keep' and observed:
                record._service_write({
                    'state': 'active',
                    'shopify_subscription_gid': observed.id,
                    'actual_topic': observed.topic,
                    'actual_uri_digest': observed.uri_digest,
                    'actual_api_version': observed.observed_api_version,
                    'actual_format': observed.format,
                    'actual_include_fields': list(observed.include_fields),
                    'last_reconciled_at': now,
                    'hmac_credential_epoch': epoch,
                    'last_error': False,
                    'operator_note': False,
                })
            elif (
                decision.action == 'delete'
                and decision.key in executable
                and observed
            ):
                record._service_write({
                    'state': 'queued',
                    'shopify_subscription_gid': observed.id,
                    'actual_topic': observed.topic,
                    'actual_uri_digest': observed.uri_digest,
                    'actual_api_version': observed.observed_api_version,
                    'actual_format': observed.format,
                    'actual_include_fields': list(observed.include_fields),
                    'last_reconciled_at': now,
                    'hmac_credential_epoch': epoch,
                })
                self._enqueue_subscription_mutation(record, 'delete', source)
            elif (
                decision.action == 'create'
                and decision.key in executable
                and not decision.depends_on
            ):
                record._service_write({
                    'state': 'missing',
                    'last_reconciled_at': now,
                    'hmac_credential_epoch': epoch,
                    'last_error': False,
                })
                if not record.last_job_id or record.last_job_id.state in CREATE_RETRY_STATES:
                    self._enqueue_subscription_mutation(record, 'create', source)
        return expected
