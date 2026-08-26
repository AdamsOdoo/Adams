from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)

from .shopify_connector_fulfillment_webhook import (
    FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
)


class ShopifyConnectorFulfillmentWebhookDispatch(models.AbstractModel):
    """Register the read-only resolver with the shared dispatcher."""

    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        if FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE in handlers:
            raise ValidationError(
                'A fulfillment webhook resolver handler collision was detected.',
            )
        Service = self.env['shopify.connector.fulfillment.service']
        handlers[FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE] = (
            Service._handle_fulfillment_webhook_resolve
        )
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        policies[FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE] = (
            REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE
        )
        return policies
