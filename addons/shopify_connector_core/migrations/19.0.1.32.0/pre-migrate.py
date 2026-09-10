"""Seed legacy activation before the ORM applies the new field default."""


def migrate(cr, version):
    if not version:
        return
    # The field default is draft for NEW stores. Odoo's _init_column fills
    # existing NULL rows with that default during schema initialization,
    # before post-migrate can distinguish legacy connected stores. Expand
    # and seed the core-owned column here, before that information is lost.
    cr.execute(
        "ALTER TABLE shopify_connector_store "
        "ADD COLUMN IF NOT EXISTS activation_state varchar"
    )
    # A partially upgraded database can already have explicit activation
    # choices. Preserve every nonempty value, especially paused/retired.
    cr.execute(
        "UPDATE shopify_connector_store "
        "SET activation_state = CASE "
        "WHEN state = 'connected' THEN 'active' "
        "ELSE 'draft' END "
        "WHERE activation_state IS NULL OR activation_state = ''"
    )
