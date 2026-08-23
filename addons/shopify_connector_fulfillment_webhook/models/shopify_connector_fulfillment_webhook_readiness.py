"""Readiness and mutation admission for fulfillment webhook topics."""

import json

from odoo import api, models
from odoo.exceptions import ValidationError


FULFILLMENT_WEBHOOK_READ_SCOPE = 'read_fulfillments'
FULFILLMENT_WEBHOOK_SCOPE_TOPICS = frozenset({
    'fulfillments/create',
    'fulfillments/update',
})


class ShopifyConnectorFulfillmentWebhookReadiness(models.AbstractModel):
    """Add the scope required by the installed fulfillment webhook addon."""

    _inherit = 'shopify.connector.readiness.check'

    @api.model
    def _fulfillment_webhook_domain_enabled(self, store):
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        return bool(settings and settings.fulfillment_domain_enabled)

    @api.model
    def _fulfillment_webhook_enabled(self, store):
        if not self._fulfillment_webhook_domain_enabled(store):
            return False
        active = set(self.env[
            'shopify.connector.webhook.registry'
        ].allowed_topics())
        return FULFILLMENT_WEBHOOK_SCOPE_TOPICS.issubset(active)

    @api.model
    def _check_fulfillment_webhook_read_scope(self, store):
        """Essentially require the Shopify read scope before webhook writes."""
        code = 'fulfillment_webhook_read_scope'
        if not self._fulfillment_webhook_enabled(store):
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Not applicable — fulfillment webhook topics are not active '
                'for this store.',
                not_applicable=True,
            )
        if not store.granted_scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'No granted-scopes snapshot recorded for this store yet.',
            )
        try:
            scopes = json.loads(store.granted_scopes)
        except (TypeError, ValueError):
            scopes = None
        if (
            not isinstance(scopes, list)
            or not scopes
            or any(
                not isinstance(scope, str) or not scope.strip()
                for scope in scopes
            )
        ):
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_NOT_PROVEN,
                'Stored granted-scopes snapshot is empty or malformed.',
            )
        if FULFILLMENT_WEBHOOK_READ_SCOPE not in scopes:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'The %s scope is required to read the active fulfillment '
                'webhook topics.' % FULFILLMENT_WEBHOOK_READ_SCOPE,
            )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'The fulfillment webhook read scope is granted.',
        )

    @api.model
    def _get_checks(self, store):
        checks = super()._get_checks(store)
        checks.append(self._check_fulfillment_webhook_read_scope(store))
        return checks

    @api.model
    def _governed_scope_catalog(self):
        catalog = super()._governed_scope_catalog()
        if not any(
            entry['scope'] == FULFILLMENT_WEBHOOK_READ_SCOPE
            for entry in catalog
        ):
            catalog.append({
                'scope': FULFILLMENT_WEBHOOK_READ_SCOPE,
                'reason': (
                    'so active fulfillments/create and fulfillments/update '
                    'webhooks can be read and reconciled safely'
                ),
            })
        return catalog


class ShopifyConnectorFulfillmentWebhookSubscription(models.Model):
    """Fence only fulfillment webhook creates on read-scope readiness."""

    _inherit = 'shopify.connector.webhook.subscription'

    @api.model
    def _enqueue_subscription_mutation(self, subscription, action, source):
        if (
            action == 'create'
            and subscription.topic in FULFILLMENT_WEBHOOK_SCOPE_TOPICS
        ):
            Readiness = self.env['shopify.connector.readiness.check']
            if not Readiness._fulfillment_webhook_domain_enabled(
                subscription.store_id,
            ):
                raise ValidationError(
                    'Fulfillment webhook subscription creation is blocked '
                    'until the fulfillment domain is enabled.'
                )
            check = Readiness._check_fulfillment_webhook_read_scope(
                subscription.store_id,
            )
            if (
                check['tier'] == Readiness.ESSENTIAL
                and (
                    check['result'] != Readiness.RESULT_PASS
                    or check.get('not_applicable')
                )
            ):
                raise ValidationError(
                    'Fulfillment webhook subscription creation is blocked '
                    'until the fulfillment webhook read-scope readiness '
                    'check passes.'
                )
        return super()._enqueue_subscription_mutation(
            subscription, action, source,
        )
