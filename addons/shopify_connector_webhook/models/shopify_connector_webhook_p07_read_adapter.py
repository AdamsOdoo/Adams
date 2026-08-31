"""P07 reversible webhook-subscription read call-site extension."""

from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_domain_read_gateway import (
    P07_LEGACY_CONTEXT_KEY,
)


class ShopifyConnectorWebhookP07ReadAdapter(models.AbstractModel):
    _inherit = "shopify.connector.webhook.subscription"

    @api.model
    def _read_actual_subscriptions(self, store, job, lifecycle=False):
        # Preserve the original validation and exception vocabulary before the
        # adapter's authorization boundary is reached.
        if not job or not getattr(job, "id", False):
            raise ValidationError(
                "Webhook subscription reads require a running reconciliation "
                "job and its business admission lease."
            )
        if self.env.context.get(P07_LEGACY_CONTEXT_KEY):
            return super()._read_actual_subscriptions(
                store, job, lifecycle=lifecycle,
            )
        return self.env["shopify.connector.read.gateway"].read_webhook_subscriptions(
            store, job, lifecycle=lifecycle,
        )


__all__ = ["ShopifyConnectorWebhookP07ReadAdapter"]
