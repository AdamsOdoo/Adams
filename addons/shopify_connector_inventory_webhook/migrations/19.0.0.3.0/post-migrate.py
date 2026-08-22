"""Refresh the noupdate cron code to the model-bound private entry point."""


def migrate(cr, version):
    if not version:
        return
    # Odoo 19 delegates ``ir.cron`` to ``ir.actions.server`` via
    # ``ir_actions_server_id``; ``code`` is stored on ``ir_act_server`` and
    # is not an ``ir_cron`` column.  Resolve the noupdate XMLID through the
    # relation so an existing installation is updated without changing any
    # scheduling or security fields.  The DISTINCT predicate keeps repeated
    # upgrades idempotent.
    cr.execute(
        """
        UPDATE ir_act_server
           SET code = %(code)s
          FROM ir_cron, ir_model_data
         WHERE ir_model_data.module = 'shopify_connector_inventory_webhook'
           AND ir_model_data.name =
               'ir_cron_shopify_connector_inventory_observation'
           AND ir_model_data.model = 'ir.cron'
           AND ir_cron.id = ir_model_data.res_id
           AND ir_act_server.id = ir_cron.ir_actions_server_id
           AND ir_act_server.code IS DISTINCT FROM %(code)s
        """,
        {'code': 'model._run_scheduled_observation_fallback(limit=20)'},
    )
