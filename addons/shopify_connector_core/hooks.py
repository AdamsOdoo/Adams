"""Fail-closed full connector uninstall boundary."""

from odoo.exceptions import UserError


def uninstall_hook(env):
    """Require completed disconnect and cleared local credentials first."""
    stores = env['shopify.connector.store'].sudo().search([
        ('state', '!=', 'disconnected'),
    ], limit=1)
    credentials = env['shopify.connector.store.credential'].sudo().search([
        ('credential_state', '!=', 'absent'),
    ], limit=1)
    active_jobs = env['shopify.connector.job'].sudo().search([
        ('state', 'not in', ('succeeded', 'failed_final', 'skipped', 'cancelled')),
    ], limit=1)
    unresolved = env['shopify.connector.mutation.attempt'].sudo().search([
        ('resolution_disposition', '=', False),
        ('observed_outcome', 'not in', ('succeeded', 'failed_clean')),
    ], limit=1)
    if stores or credentials or active_jobs or unresolved:
        raise UserError(
            'Connector uninstall is blocked. Disconnect every store, let '
            'quiescence complete, clear every credential, drain or resolve '
            'all work, and resolve every uncertain mutation first. Merchant '
            'custom-app token revocation in Shopify remains required.'
        )
