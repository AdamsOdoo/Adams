"""Refresh the noupdate cron code to the model-bound private entry point."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE ir_cron SET code = %s "
        "WHERE id = (SELECT res_id FROM ir_model_data "
        "WHERE module = %s AND name = %s AND model = %s)",
        (
            'model._run_scheduled_observation_fallback(limit=20)',
            'shopify_connector_inventory_webhook',
            'ir_cron_shopify_connector_inventory_observation',
            'ir.cron',
        ),
    )
