from odoo import fields, models


from .shopify_connector_fulfillment_webhook import (
    FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
)


class ShopifyConnectorFulfillmentWebhookJob(models.Model):
    """Durable resolver job type; uninstall preserves its history."""

    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[(
            FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE,
            'Fulfillment Webhook Resolve',
        )],
        ondelete={
            FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE:
                lambda recs: recs._reassign_to_historic_job_type(),
        },
    )

    def _domain_flag_for_job_type(self, job_type):
        if job_type == FULFILLMENT_WEBHOOK_RESOLVE_JOB_TYPE:
            return 'fulfillment_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)
