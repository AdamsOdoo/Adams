"""Backfill the additive P15 activation/replay state safely."""


def migrate(cr, version):
    del version
    # Odoo has already added the model columns when this hook runs.  Keep the
    # backfill idempotent because qualification deliberately runs upgrades
    # twice and older dumps may have a partially-created column.
    cr.execute(
        "UPDATE shopify_connector_store "
        "SET activation_state = CASE "
        "WHEN state = 'connected' THEN 'active' "
        "ELSE 'draft' END "
        "WHERE activation_state IS NULL OR activation_state = ''"
    )
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_connector_command_result_scope_idx "
        "ON shopify_connector_command_result "
        "(company_id, scope_key, command_id)"
    )
