"""Refresh the noupdate cron code to the model-bound private entry point."""

from odoo import SUPERUSER_ID, api

TARGET_CODE = 'model._run_scheduled_observation_fallback(limit=20)'


def migrate(cr, version):
    if not version:
        return
    # Odoo 19 delegates ``ir.cron`` to ``ir.actions.server``.  Use the ORM's
    # delegated field so both sides of that relation and the migration
    # environment's cache stay coherent; a raw UPDATE of ir_act_server would
    # leave an already-resolved cron record stale for the remainder of the
    # upgrade transaction.  Missing or malformed XMLIDs are intentionally a
    # no-op: this migration must never retarget an unrelated scheduled action.
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref(
        'shopify_connector_inventory_webhook.'
        'ir_cron_shopify_connector_inventory_observation',
        raise_if_not_found=False,
    )
    if not cron:
        return
    cron = cron.exists()
    if not cron or cron._name != 'ir.cron' or len(cron) != 1:
        return
    if cron.code != TARGET_CODE:
        cron.write({'code': TARGET_CODE})
