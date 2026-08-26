"""Fail-closed webhook uninstall boundary."""

from odoo.exceptions import UserError


def uninstall_hook(env):
    """Allow uninstall only after remote cleanup has completed safely.

    Shopify mutation calls never run inside the module-uninstall transaction.
    Administrators must first use ``Prepare webhook uninstall``; that path
    performs a fresh read and queues exact-GID deletes through the unchanged
    Layer-2 commit-before-send machinery.  This hook then proves that no
    subscription identity or active webhook job is being abandoned.
    """
    Subscription = env['shopify.connector.webhook.subscription'].sudo()
    outstanding = Subscription.search([
        '|', ('expected', '=', True),
        ('shopify_subscription_gid', '!=', False),
    ], limit=1)
    active_jobs = env['shopify.connector.job'].sudo().search([
        ('job_type', '=like', 'webhook_%'),
        ('state', 'not in', ('succeeded', 'failed_final', 'skipped', 'cancelled')),
    ], limit=1)
    if outstanding or active_jobs:
        raise UserError(
            'Webhook uninstall is blocked. Run “Prepare webhook uninstall”, '
            'drain the resulting reconciliation and deletion jobs, resolve '
            'any Needs Attention result, and retry. This prevents dangling '
            'Shopify subscriptions and abandoned webhook work.'
        )
    for row in Subscription.search([]):
        row._service_write({
            'expected': False,
            'state': 'missing',
            'last_error': False,
        })
