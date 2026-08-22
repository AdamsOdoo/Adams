"""Core dispatcher registration for the read-only observation job."""

from odoo import api, models
from odoo.exceptions import ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)

from .constants import INVENTORY_OBSERVATION_JOB_TYPE


class ShopifyConnectorInventoryWebhookDispatchExtension(models.AbstractModel):
    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        service = self.env[
            'shopify.connector.inventory.observation.service'
        ]
        if INVENTORY_OBSERVATION_JOB_TYPE in handlers:
            raise ValidationError(
                'The inventory observation job type already has a handler; '
                'refusing a colliding dispatch registration.'
            )
        handlers[INVENTORY_OBSERVATION_JOB_TYPE] = (
            service._handle_inventory_observation_sync
        )
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        if INVENTORY_OBSERVATION_JOB_TYPE in policies:
            raise ValidationError(
                'The inventory observation job type already has a replay '
                'policy; refusing a colliding dispatch registration.'
            )
        policies[INVENTORY_OBSERVATION_JOB_TYPE] = (
            REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE
        )
        return policies
