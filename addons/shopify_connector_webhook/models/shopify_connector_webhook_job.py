"""Webhook-owned job lineage values."""

from odoo import api, fields, models


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

    @api.depends(
        'state', 'store_id', 'job_type', 'res_model', 'res_id',
        'shopify_target_gid', 'superseded_by_job_id',
    )
    def _compute_operation_scope_key(self):
        """Keep the read-first replacement distinct from its delete successor.

        The parent must pin the same exact Shopify GID that its mutation
        successor will delete, but it is a remote-read admission job rather
        than the mutation itself. Giving only that parent type a namespaced
        scope preserves one-parent-per-target serialization while leaving the
        shared mutation scope and every existing job type unchanged.
        """
        super()._compute_operation_scope_key()
        for job in self.filtered(
            lambda item: (
                item.operation_scope_key
                and item.job_type == 'webhook_subscription_replace_stale'
            )
        ):
            job.operation_scope_key = '%s|read-first-replacement' % (
                job.operation_scope_key,
            )
