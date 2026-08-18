"""Fail-closed readiness projection for the installed webhook foundation."""

from odoo import api, models

from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)


class ShopifyConnectorWebhookReadiness(models.AbstractModel):
    """Replace core's not-applicable webhook check with stored evidence."""

    _inherit = 'shopify.connector.readiness.check'

    @api.model
    def _check_webhook_hmac(self, store):
        if store.state != 'connected':
            return self._check_result(
                'webhook_hmac', self.ESSENTIAL, self.RESULT_PASS,
                'Webhook subscription proof is not applicable before store '
                'activation; use Bootstrap / reconcile webhooks to perform '
                'the explicit lifecycle read, then reconnect if required.',
                not_applicable=True,
            )
        Secret = self.env['shopify.connector.webhook.secret']
        Subscription = self.env['shopify.connector.webhook.subscription']
        Registry = self.env['shopify.connector.webhook.registry']
        secret = Secret.sudo().search([
            ('store_id', '=', store.id), ('active', '=', True),
        ], limit=1)
        if not secret:
            return self._check_result(
                'webhook_hmac', self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'No store-scoped webhook callback token is recorded.',
            )
        if not Secret._client_secret_for_store(store):
            return self._check_result(
                'webhook_hmac', self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'No app client secret is available for webhook HMAC verification.',
            )
        if self.env[
            'shopify.connector.store.credential'
        ]._hmac_rotation_pending(store):
            return self._check_result(
                'webhook_hmac', self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'A previous app client secret remains accepted during its '
                'bounded Shopify rotation grace window; rerun readiness '
                'after the recorded expiry before treating the store as healthy.',
            )
        expected_topics = Registry.allowed_topics()
        subscriptions = Subscription.sudo().search([
            ('store_id', '=', store.id), ('expected', '=', True),
        ])
        if set(subscriptions.mapped('topic')) != set(expected_topics):
            return self._check_result(
                'webhook_hmac', self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'The active webhook topic registry has not been materialized '
                'for this store.',
            )
        try:
            callback_digest = Secret._callback_url_digest_for_store(store)
        except Exception as exc:
            return self._check_result(
                'webhook_hmac', self.ESSENTIAL, self.RESULT_FAIL,
                'The HTTPS callback endpoint is not usable (%s).' % (
                    type(exc).__name__,
                ),
            )
        epoch = Subscription._credential_epoch(store)
        invalid = subscriptions.filtered(lambda sub: (
            sub.state != 'active'
            or sub.expected_api_version != SHOPIFY_API_VERSION
            or sub.actual_api_version != SHOPIFY_API_VERSION
            or sub.actual_topic != sub.topic_enum
            or sub.actual_format != 'JSON'
            or sub.expected_callback_url_digest != callback_digest
            or sub.actual_uri_digest != callback_digest
            or sub.hmac_credential_epoch != epoch
            or not sub.last_reconciled_at
        ))
        if invalid:
            return self._check_result(
                'webhook_hmac', self.ESSENTIAL, self.RESULT_FAIL,
                'Stored webhook subscription read-back evidence is incomplete '
                'or stale for %d topic(s).' % len(invalid),
            )
        return self._check_result(
            'webhook_hmac', self.ESSENTIAL, self.RESULT_PASS,
            'Raw-body HMAC configuration and subscription read-back evidence '
            'are recorded; scheduled reconciliation remains mandatory.',
        )
