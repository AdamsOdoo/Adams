"""Webhook job handlers and Layer-2 subscription strategy registration."""

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    REPLAY_POLICY_LOCAL_ONLY,
    REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)
from odoo.addons.shopify_connector_core.tools.redaction import redact


class ShopifyConnectorWebhookDispatch(models.AbstractModel):
    """Add-only handler/replay/strategy extension over the core dispatcher."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = super()._get_handlers()
        handlers.update({
            'webhook_delivery_process': self._handle_webhook_delivery_process,
            'webhook_subscription_bootstrap':
                self._handle_webhook_subscription_bootstrap,
            'webhook_subscription_reconcile':
                self._handle_webhook_subscription_reconcile,
            'webhook_subscription_create':
                self._handle_webhook_subscription_mutation_placeholder,
            'webhook_subscription_delete':
                self._handle_webhook_subscription_mutation_placeholder,
            'webhook_subscription_mutation_reconcile':
                self._handle_webhook_subscription_mutation_reconcile,
        })
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = super()._get_replay_policies()
        policies.update({
            'webhook_delivery_process': REPLAY_POLICY_LOCAL_ONLY,
            'webhook_subscription_bootstrap':
                REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            'webhook_subscription_reconcile':
                REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            # Core's generic reconciliation handler performs read-only
            # verification and is safe to replay within its bounded job policy.
            'webhook_subscription_mutation_reconcile':
                REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            # These are Layer-2 mutations.  A concurrent transaction failure
            # must never re-invoke them automatically.
            'webhook_subscription_create':
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            'webhook_subscription_delete':
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
        })
        return policies

    @api.model
    def _get_reconciliation_strategies(self):
        strategies = super()._get_reconciliation_strategies()
        subscription = self.env['shopify.connector.webhook.subscription']
        strategies.update({
            'webhook_subscription_create': {
                'reconciliation_job_type':
                    'webhook_subscription_mutation_reconcile',
                'prepare_local':
                    subscription._prepare_local_subscription_mutation,
                'prepare_preconditions':
                    subscription._prepare_subscription_preconditions,
                'transport': subscription._transport_subscription_mutation,
                'classify_direct_result':
                    subscription._classify_subscription_mutation,
                'reconcile': subscription._reconcile_subscription_mutation,
                'apply_consequence':
                    subscription._apply_subscription_consequence,
            },
            'webhook_subscription_delete': {
                'reconciliation_job_type':
                    'webhook_subscription_mutation_reconcile',
                'prepare_local':
                    subscription._prepare_local_subscription_mutation,
                'prepare_preconditions':
                    subscription._prepare_subscription_preconditions,
                'transport': subscription._transport_subscription_mutation,
                'classify_direct_result':
                    subscription._classify_subscription_mutation,
                'reconcile': subscription._reconcile_subscription_mutation,
                'apply_consequence':
                    subscription._apply_subscription_consequence,
            },
        })
        return strategies

    @api.model
    def _handle_webhook_delivery_process(self, job):
        delivery = self.env[
            'shopify.connector.webhook.delivery'
        ].sudo().browse(job.res_id).exists()
        if (
            not delivery
            or delivery.store_id != job.store_id
            or delivery.job_id != job
        ):
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Webhook delivery job has no matching verified evidence row.',
            )
        try:
            delivery._process_queued()
        except (ValidationError, UserError) as exc:
            try:
                delivery._service_write({
                    'state': 'failed',
                    'processed_at': fields.Datetime.now(),
                    'last_error': redact(str(exc))[:2000],
                    'processing_note': (
                        'The local webhook handler failed; retry the durable '
                        'job or run reconciliation.'
                    ),
                })
            except Exception:
                # The durable job failure remains the source of truth if the
                # evidence-state write itself is unavailable.
                pass
            raise JobHandlerError(
                'data_shape_schema_mismatch',
                'Webhook delivery processing failed; inspect the evidence row.',
                type(exc).__name__,
            )

    @api.model
    def _handle_webhook_subscription_reconcile(self, job):
        subscription = self.env['shopify.connector.webhook.subscription']
        try:
            subscription._reconcile_store(
                job.store_id,
                source=job.job_source or 'scheduled_sync',
                job=job,
            )
        except ShopifyClientError as exc:
            raise JobHandlerError(
                exc.error_class,
                exc.reason,
                exc.technical_detail,
            )
        except ShopifyQuiescedError as exc:
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'Webhook reconciliation was refused by store quiescence.',
                type(exc).__name__,
            )
        except (ValidationError, UserError) as exc:
            raise JobHandlerError(
                'odoo_validation_configuration',
                'Webhook reconciliation could not complete safely.',
                type(exc).__name__,
            )

    @api.model
    def _handle_webhook_subscription_bootstrap(self, job):
        """Run the explicit pre-activation lifecycle read path."""
        subscription = self.env['shopify.connector.webhook.subscription']
        try:
            subscription._reconcile_store(
                job.store_id,
                source='setup_readiness_check',
                job=job,
                bootstrap=True,
            )
        except ShopifyClientError as exc:
            raise JobHandlerError(exc.error_class, exc.reason, exc.technical_detail)
        except ShopifyQuiescedError as exc:
            raise JobHandlerError(
                'shopify_temporary_server_network',
                'Webhook bootstrap was refused by store quiescence.',
                type(exc).__name__,
            )
        except (ValidationError, UserError) as exc:
            raise JobHandlerError(
                'odoo_validation_configuration',
                'Webhook bootstrap could not complete safely.',
                type(exc).__name__,
            )

    @api.model
    def _handle_webhook_subscription_mutation_placeholder(self, job):
        del job
        raise ValidationError(
            'Webhook subscription mutations are admitted only through the '
            'Layer-2 dispatcher protocol.'
        )

    @api.model
    def _handle_webhook_subscription_mutation_reconcile(self, job):
        """Use core's generic read-only mutation reconciliation protocol.

        The core method is strategy-driven despite its historical self-test
        name.  Delegating preserves its attempt identity, store-generation,
        inconclusive-cap, no-resend and atomic-consequence safeguards without
        copying them into this addon.
        """
        return super()._handle_mutation_dispatch_selftest_reconcile(job)
