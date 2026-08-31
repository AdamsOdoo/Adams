"""Webhook-owned P07 typed gateway registration."""

from odoo import api, models

from odoo.addons.shopify_connector_core.models.shopify_connector_api_client import (
    ShopifyClientError,
)

from ..integration.shopify.webhook_subscription_read_gateway import (
    WebhookSubscriptionReadError,
    WebhookSubscriptionReadGateway,
)
from .shopify_connector_webhook_subscription import ShopifyWebhookSchemaError


class ShopifyConnectorWebhookP07Gateway(models.AbstractModel):
    """Provide the subscription gateway through the owning addon."""

    _inherit = "shopify.connector.read.gateway"

    @api.model
    def _p07_gateway(self, family: str):
        if family == "webhook":
            return WebhookSubscriptionReadGateway, dict(
                WebhookSubscriptionReadGateway.operation_documents
            )
        return super()._p07_gateway(family)

    @api.model
    def _p07_raise_typed_error(self, family: str, exc: Exception):
        if family != "webhook" or not isinstance(
            exc, WebhookSubscriptionReadError,
        ):
            return super()._p07_raise_typed_error(family, exc)
        if isinstance(exc.__cause__, ShopifyClientError):
            raise exc.__cause__ from exc
        raise ShopifyWebhookSchemaError(
            "Shopify webhook subscription evidence was malformed or incomplete."
        ) from exc


__all__ = ["ShopifyConnectorWebhookP07Gateway"]
