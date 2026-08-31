"""P11 V2 subscription adapter over the accepted Layer-2 dispatcher.

This inheritance is deliberately additive.  Legacy and read-only stores keep
their existing subscription service; only stores whose settings explicitly say
``subscriptions`` create V2 runs/jobs and use the P07/P08 contracts.
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from odoo.addons.shopify_connector_core.domain.immutability import to_plain
from odoo.addons.shopify_connector_core.domain.runtime_modes import (
    runtime_mode_includes,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)

from ..integration.shopify.webhook_subscription_mutation_gateway import (
    SHOPIFY_API_VERSION,
    WebhookSubscriptionMutationGateway,
)
from .shopify_connector_webhook_subscription import (
    _uri_digest,
)


V2_SUBSCRIPTION_MUTATIONS = frozenset((
    'webhook_subscription_create',
    'webhook_subscription_delete',
))
V2_SUBSCRIPTION_JOB_TYPES = V2_SUBSCRIPTION_MUTATIONS | frozenset((
    'webhook_subscription_mutation_reconcile',
))
_TERMINAL_JOB_STATES = frozenset((
    'succeeded', 'failed_final', 'skipped', 'cancelled',
))


class _NoopDelegate:
    """Build-only delegate; it cannot perform a transport call."""

    def execute(self, operation, variables):
        del operation, variables
        raise AssertionError('the build-only gateway delegate was called')


class _MutationDelegate:
    def __init__(self, client, job, store, context):
        self.client = client
        self.job = job
        self.store = store
        self.context = dict(context)

    def execute(self, operation, variables):
        try:
            with self.client.execute_business(
                self.job,
                self.store,
                operation.document,
                variables,
                mutation_context=self.context,
            ) as result:
                return result
        except ShopifyClientError as exc:
            # The Layer-2 attempt is already committed.  The client does not
            # prove whether the socket reached Shopify, so the gateway must
            # preserve uncertainty without exposing exception text.
            from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
                MutationTransportError,
            )
            raise MutationTransportError(
                after_send=None,
                code=exc.error_class,
            ) from exc
        except ShopifyQuiescedError as exc:
            from odoo.addons.shopify_connector_core.integration.shopify.mutation_contracts import (
                MutationTransportError,
            )
            raise MutationTransportError(after_send=None) from exc


class ShopifyConnectorWebhookSubscriptionV2(models.Model):
    _inherit = 'shopify.connector.webhook.subscription'

    @api.model
    def _v2_settings(self, store):
        return self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )

    @api.model
    def _v2_mode_enabled(self, store):
        settings = self._v2_settings(store)
        return bool(
            settings
            and 'v2_runtime_mode' in settings._fields
            and runtime_mode_includes(
                settings.v2_runtime_mode, 'subscriptions',
            )
        )

    @api.model
    def _v2_assert_actor(self):
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may admit a V2 '
                'subscription mutation.'
            )

    @api.model
    def _v2_assert_job(self, job, *, reconciliation=False):
        if not job or not job.exists() or job.job_type not in (
            V2_SUBSCRIPTION_JOB_TYPES if reconciliation
            else V2_SUBSCRIPTION_MUTATIONS
        ) or not job.run_id:
            raise ValidationError('The V2 subscription job identity is invalid.')
        store = job.store_id
        run = job.run_id
        settings = self._v2_settings(store)
        if (
            not settings
            or not runtime_mode_includes(
                settings.v2_runtime_mode, 'subscriptions',
            )
            or store.state != 'connected'
            or job.company_id != store.company_id
            or run.store_id != store
            or run.company_id != store.company_id
            or settings.company_id != store.company_id
            or store.company_id not in self.env.companies
            or run.cancel_requested_at
            or run.state not in ('admitted', 'running', 'waiting')
            or job.expected_connection_generation != store.connection_generation
            or run.expected_connection_generation != store.connection_generation
            or job.expected_configuration_generation
            != settings.configuration_generation
            or run.expected_configuration_generation
            != settings.configuration_generation
        ):
            raise ValidationError(
                'The V2 subscription job is stale, out of scope, or its '
                'subscriptions mode is no longer enabled.'
            )
        return settings

    @api.model
    def _v2_job_for_subscription(self, subscription, action):
        job_type = (
            'webhook_subscription_create'
            if action == 'create' else 'webhook_subscription_delete'
        )
        Job = self.env['shopify.connector.job'].sudo()
        target = subscription.shopify_subscription_gid if action == 'delete' else False
        active = Job.search([
            ('store_id', '=', subscription.store_id.id),
            ('job_type', '=', job_type),
            ('res_model', '=', self._name),
            ('res_id', '=', subscription.id),
            ('shopify_target_gid', '=', target),
            ('state', 'not in', tuple(_TERMINAL_JOB_STATES)),
        ], order='id asc', limit=1)
        if active:
            return active
        return Job.browse()

    @api.model
    def _enqueue_v2_subscription_mutation(self, subscription, action, source):
        self._v2_assert_actor()
        store = subscription.store_id
        settings = self._v2_settings(store)
        if (
            not settings
            or not runtime_mode_includes(
                settings.v2_runtime_mode, 'subscriptions',
            )
            or store.state != 'connected'
            or store.company_id not in self.env.companies
        ):
            raise ValidationError(
                'V2 subscription admission requires a connected store in '
                'subscriptions mode.'
            )
        self._require_hmac_client_secret(store)
        if action not in ('create', 'delete'):
            raise ValidationError('Unsupported V2 subscription mutation.')
        if action == 'create':
            self._validate_subscription_create_preconditions(subscription)
        target = subscription.shopify_subscription_gid if action == 'delete' else False
        payload = {
            'store_id': store.id,
            'subscription_id': subscription.id,
            'action': action,
            'topic': subscription.topic_enum,
            'target_gid': target,
            'callback_uri_digest': subscription.expected_callback_url_digest,
            'configuration_generation': settings.configuration_generation,
        }
        # Keep the dependency-free canonical hash service already used by the
        # V1 model; admission creates no mutation-attempt row.  C2 creates the
        # immutable attempt only after the worker owns the job.
        from odoo.addons.shopify_connector_core.models.shopify_connector_mutation_attempt import (
            canonical_sha256,
        )
        payload_hash = canonical_sha256(payload)
        job_type = (
            'webhook_subscription_create'
            if action == 'create' else 'webhook_subscription_delete'
        )
        existing = self._v2_job_for_subscription(subscription, action)
        if existing:
            return existing
        Run = self.env['shopify.connector.run'].sudo()
        request_key = 'v2-subscription:%s:%s:%s' % (
            subscription.id, action, payload_hash,
        )
        run = Run.search([
            ('store_id', '=', store.id), ('request_key', '=', request_key),
        ], limit=1)
        if run and run.state in ('requested', 'admitted', 'running', 'waiting'):
            job = self.env['shopify.connector.job'].sudo().search(
                [('run_id', '=', run.id)], order='id asc', limit=1,
            )
            if job:
                return job
        if run:
            request_key = '%s:retry:%s' % (request_key, fields.Datetime.now())
        trigger = 'user' if source == 'manual_sync' else 'cron'
        run = Run._create_service({
            'store_id': store.id,
            'request_key': request_key,
            'workflow': 'webhook',
            'operation': 'webhook.subscription.%s' % action,
            'trigger': trigger,
            'scope_summary': 'Webhook subscription %s' % action,
            'scope_fingerprint': payload_hash,
            'configuration_snapshot': {
                'runtime_mode': settings.v2_runtime_mode,
                'configuration_generation': settings.configuration_generation,
                'topic': subscription.topic_enum,
                'action': action,
            },
            'expected_connection_generation': store.connection_generation,
            'expected_configuration_generation': settings.configuration_generation,
        })
        run._admit_service()
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'run_id': run.id,
            'job_source': source,
            'job_type': job_type,
            'state': 'queued',
            'payload_hash': payload_hash,
            'res_model': self._name,
            'res_id': subscription.id,
            'shopify_target_gid': target,
            'expected_connection_generation': store.connection_generation,
            'expected_configuration_generation': settings.configuration_generation,
            'lane': 'interactive' if source == 'manual_sync' else 'scheduled',
            'lane_priority': 100,
            'available_at': fields.Datetime.now(),
        })
        subscription._service_write({
            'state': 'queued',
            'last_job_id': job.id,
            'last_action_at': fields.Datetime.now(),
            'last_error': False,
        })
        cron = self.env.ref(
            'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain',
            raise_if_not_found=False,
        )
        if cron:
            cron.sudo()._trigger()
        return job

    @api.model
    def _enqueue_subscription_mutation(self, subscription, action, source):
        if self._v2_mode_enabled(subscription.store_id):
            return self._enqueue_v2_subscription_mutation(
                subscription, action, source,
            )
        return super()._enqueue_subscription_mutation(
            subscription, action, source,
        )

    @api.model
    def _v2_mutation_subscription(self, job):
        self._v2_assert_job(job)
        subscription = self.browse(job.res_id).exists()
        if not subscription or subscription.store_id != job.store_id:
            raise ValidationError('The V2 subscription target is invalid.')
        active_topic = subscription.topic in self.env[
            'shopify.connector.webhook.registry'
        ].allowed_topics()
        if job.job_type == 'webhook_subscription_delete':
            if not subscription.shopify_subscription_gid:
                raise ValidationError('A V2 delete requires an exact Shopify GID.')
            removed_cleanup = not subscription.expected
            stale_callback_cleanup = (
                subscription.expected
                and subscription.state == 'queued'
                and bool(subscription.actual_uri_digest)
                and subscription.actual_uri_digest
                != subscription.expected_callback_url_digest
            )
            connector_owned = (
                bool(subscription.actual_uri_digest)
                and subscription.actual_uri_digest
                == subscription.expected_callback_url_digest
            )
            removed_cleanup_owned = removed_cleanup and connector_owned
            if not active_topic and not removed_cleanup:
                raise ValidationError('The V2 subscription topic is not active.')
            if not (
                removed_cleanup_owned
                or stale_callback_cleanup
                or connector_owned
            ):
                raise ValidationError(
                    'A V2 delete cannot remove a callback identity that is '
                    'not connector-owned.'
                )
        elif not active_topic:
            raise ValidationError('The V2 subscription topic is not active.')
        return subscription

    @api.model
    def _prepare_local_subscription_mutation(self, job):
        if not self.env[
            'shopify.connector.job.dispatch'
        ]._is_v2_mutation_job(job):
            return super()._prepare_local_subscription_mutation(job)
        subscription = self._v2_mutation_subscription(job)
        action = (
            'create' if job.job_type == 'webhook_subscription_create'
            else 'delete'
        )
        return {
            'mutation_domain': job.job_type,
            'job_id': job.id,
            'subscription_id': subscription.id,
            'store_id': subscription.store_id.id,
            'expected_connection_generation': job.expected_connection_generation,
            'expected_configuration_generation': job.expected_configuration_generation,
            'expected_store_identity': subscription.store_id.shop_domain,
            'action': action,
            'topic': subscription.topic,
            'topic_enum': subscription.topic_enum,
            'callback_url_digest': subscription.expected_callback_url_digest,
            'expected_api_version': subscription.expected_api_version,
            'expected_include_fields': list(subscription.expected_include_fields or []),
            'shopify_subscription_gid': subscription.shopify_subscription_gid or False,
            'operation_scope_key': job.operation_scope_key or (
                'webhook_subscription:%s' % subscription.id
            ),
        }

    @api.model
    def _v2_request(self, local_snapshot, owner_context, callback_uri=None):
        gateway = WebhookSubscriptionMutationGateway(_NoopDelegate())
        business = {
            'action': local_snapshot['action'],
            'subscription_id': local_snapshot['subscription_id'],
            'store_id': local_snapshot['store_id'],
            'topic': local_snapshot['topic'],
            'topic_enum': local_snapshot['topic_enum'],
            'callback_url_digest': local_snapshot['callback_url_digest'],
            'expected_api_version': local_snapshot['expected_api_version'],
            'expected_include_fields': list(local_snapshot.get('expected_include_fields') or []),
            'target_gid': local_snapshot.get('shopify_subscription_gid') or False,
        }
        preconditions = {
            'expected_connection_generation': local_snapshot['expected_connection_generation'],
            'expected_configuration_generation': local_snapshot['expected_configuration_generation'],
            'expected_store_identity': local_snapshot['expected_store_identity'],
            'expected_api_version': local_snapshot['expected_api_version'],
            'expected_include_fields': list(local_snapshot.get('expected_include_fields') or []),
        }
        key = 'webhook-subscription:%s:%s:%s' % (
            local_snapshot['subscription_id'],
            local_snapshot['action'],
            local_snapshot['callback_url_digest'],
        )
        if local_snapshot['action'] == 'create':
            request = gateway.build_create(
                local_snapshot['topic_enum'],
                callback_uri,
                include_fields=local_snapshot.get('expected_include_fields'),
                expected_api_version=local_snapshot['expected_api_version'],
                idempotency_key=key,
                operation_scope_key=local_snapshot['operation_scope_key'],
                business_intent=business,
                preconditions_snapshot=preconditions,
            )
        else:
            key = '%s:%s' % (key, local_snapshot['shopify_subscription_gid'])
            request = gateway.build_delete(
                local_snapshot['shopify_subscription_gid'],
                topic=local_snapshot['topic_enum'],
                idempotency_key=key,
                operation_scope_key=local_snapshot['operation_scope_key'],
                business_intent=business,
                preconditions_snapshot=preconditions,
            )
        return request

    @api.model
    def _prepare_subscription_preconditions(self, local_snapshot, owner_context):
        if not owner_context.get('job_id'):
            return super()._prepare_subscription_preconditions(
                local_snapshot, owner_context,
            )
        job = self.env['shopify.connector.job'].browse(owner_context['job_id'])
        if not self.env[
            'shopify.connector.job.dispatch'
        ]._is_v2_mutation_job(job):
            return super()._prepare_subscription_preconditions(
                local_snapshot, owner_context,
            )
        self._v2_assert_job(job)
        callback_uri = None
        if local_snapshot['action'] == 'create':
            callback_uri = self.env[
                'shopify.connector.webhook.secret'
            ]._callback_url_for_store(job.store_id)
            if _uri_digest(callback_uri) != local_snapshot['callback_url_digest']:
                raise ValidationError('The callback identity changed before send.')
        request = self._v2_request(local_snapshot, owner_context, callback_uri)
        return {
            'mutation_domain': owner_context['mutation_domain'],
            'operation': request.operation.document,
            'operation_key': request.operation_key,
            'variables': to_plain(request.variables),
            'business_intent': to_plain(request.intent.business_intent),
            'remote_mutation_intent': to_plain(request.intent.business_intent),
            'preconditions_snapshot': to_plain(request.intent.preconditions_snapshot),
            'expected_connection_generation': local_snapshot['expected_connection_generation'],
            'expected_store_identity': local_snapshot['expected_store_identity'],
            'shopify_idempotency_key': request.intent.idempotency_key,
        }

    @api.model
    def _transport_subscription_mutation(self, request, attempt_context):
        if not attempt_context.get('job_id'):
            return super()._transport_subscription_mutation(request, attempt_context)
        job = self.env['shopify.connector.job'].browse(attempt_context['job_id'])
        attempt = self.env['shopify.connector.mutation.attempt'].browse(
            attempt_context.get('attempt_id'),
        ).exists()
        if not self.env[
            'shopify.connector.job.dispatch'
        ]._is_v2_mutation_job(job, attempt=attempt):
            return super()._transport_subscription_mutation(request, attempt_context)
        try:
            self._v2_assert_job(job)
            local = dict(request['business_intent'])
            local.update({
                'expected_connection_generation': request['expected_connection_generation'],
                'expected_configuration_generation': request['preconditions_snapshot'].get('expected_configuration_generation', 0),
                'expected_store_identity': request['expected_store_identity'],
                'operation_scope_key': request['preconditions_snapshot'].get('operation_scope_key') or 'webhook_subscription:%s' % local['subscription_id'],
                'expected_api_version': local.get('expected_api_version', SHOPIFY_API_VERSION),
                'shopify_subscription_gid': local.get('target_gid') or False,
            })
            # The callback URI is ephemeral and exists only in the request
            # variables.  It is never copied into intent/evidence.
            callback_uri = None
            if local['action'] == 'create':
                callback_uri = request['variables']['webhookSubscription']['uri']
            gateway = WebhookSubscriptionMutationGateway(
                _MutationDelegate(
                    self.env['shopify.connector.api.client'],
                    job,
                    job.store_id,
                    attempt_context,
                )
            )
            built = self._v2_request(local, attempt_context, callback_uri)
            result = gateway.execute(built)
            return {'gateway_result': result}
        except ValidationError as exc:
            return {
                'outcome': 'uncertain',
                'error_class': 'store_identity_mismatch',
                'message': 'The subscription scope changed before transport; readback is required.',
                'evidence': {'transport': 'admission_refused', 'error_class': type(exc).__name__},
            }

    @api.model
    def _classify_subscription_mutation(self, raw_result):
        result = raw_result.get('gateway_result') if isinstance(raw_result, dict) else None
        if result is None:
            return super()._classify_subscription_mutation(raw_result)
        evidence = dict(to_plain(result.evidence))
        evidence.update({
            'operation_key': result.operation_key,
            'gateway_outcome': result.outcome,
        })
        if result.user_errors:
            evidence['user_error_count'] = len(result.user_errors)
        if result.outcome == 'failed_clean':
            return {
                'observed_outcome': 'failed_clean',
                'error_class': 'shopify_user_errors_validation',
                'manual_review_subreason': False,
                'action': 'fail_final',
                'message': 'Shopify rejected the subscription mutation.',
                'evidence': evidence,
            }
        domain_payload = {}
        payload = to_plain(result.payload)
        if isinstance(payload.get('subscription'), dict):
            node = payload['subscription']
            domain_payload = {
                'shopify_subscription_gid': node.get('id'),
                'actual_topic': node.get('topic'),
                'actual_uri_digest': node.get('uri_digest'),
                'actual_api_version': node.get('api_version'),
                'actual_format': node.get('format'),
                'actual_include_fields': node.get('include_fields') or [],
            }
        if isinstance(payload.get('deleted_subscription_gid'), str):
            domain_payload['deleted_subscription_gid'] = payload[
                'deleted_subscription_gid'
            ]
        return {
            'observed_outcome': 'uncertain',
            'error_class': result.error_code or 'shopify_temporary_server_network',
            'manual_review_subreason': False,
            'action': 'reconcile',
            'message': 'The subscription mutation requires exact Shopify readback; no resend is allowed.',
            'evidence': evidence,
            'domain_payload': domain_payload,
        }
