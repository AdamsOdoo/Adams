"""Job-lineage registration for the read-only inventory observation child."""

from odoo import api, fields, models

from .constants import INVENTORY_OBSERVATION_JOB_TYPE


class ShopifyConnectorJobInventoryWebhookExtension(models.Model):
    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[
            (INVENTORY_OBSERVATION_JOB_TYPE, 'Inventory Observation Sync'),
        ],
        ondelete={
            INVENTORY_OBSERVATION_JOB_TYPE:
                lambda records: records._reassign_to_historic_job_type(),
        },
    )

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        if job_type == INVENTORY_OBSERVATION_JOB_TYPE:
            return 'inventory_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)
