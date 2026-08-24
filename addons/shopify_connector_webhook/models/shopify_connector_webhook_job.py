"""Webhook-owned job lineage values."""

from odoo import fields, models


WEBHOOK_JOB_TYPES = (
    'webhook_delivery_process',
    'webhook_subscription_bootstrap',
    'webhook_subscription_reconcile',
    'webhook_subscription_retire_all',
    'webhook_subscription_replace_stale',
    'webhook_subscription_create',
    'webhook_subscription_delete',
    'webhook_subscription_mutation_reconcile',
)


class ShopifyConnectorWebhookJob(models.Model):
    """Add-only job selection extension for the webhook addon."""

    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[
            ('webhook_delivery_process', 'Webhook Delivery Process'),
            ('webhook_subscription_bootstrap',
             'Webhook Subscription Bootstrap'),
            ('webhook_subscription_reconcile',
             'Webhook Subscription Reconciliation'),
            ('webhook_subscription_retire_all',
             'Webhook Subscription Uninstall Preparation'),
            ('webhook_subscription_replace_stale',
             'Webhook Subscription Stale Callback Replacement'),
            ('webhook_subscription_create', 'Webhook Subscription Create'),
            ('webhook_subscription_delete', 'Webhook Subscription Delete'),
            ('webhook_subscription_mutation_reconcile',
             'Webhook Subscription Mutation Reconciliation'),
        ],
        ondelete={
            job_type: lambda records: records._reassign_to_historic_job_type()
            for job_type in WEBHOOK_JOB_TYPES
        },
    )
