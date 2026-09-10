"""Canonical Odoo-loaded webhook read gateway."""

from .webhook_subscription_read_gateway import (
    WebhookSubscriptionReadError,
    WebhookSubscriptionReadGateway,
)

__all__ = ["WebhookSubscriptionReadError", "WebhookSubscriptionReadGateway"]
