"""Apply the public-release dispatcher recovery cadence to existing DBs."""

from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    cron = env.ref(
        'shopify_connector_core.ir_cron_shopify_connector_job_dispatch_drain',
        raise_if_not_found=False,
    )
    if cron:
        cron.write({
            'interval_number': 1,
            'interval_type': 'minutes',
        })
