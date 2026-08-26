"""WP-6 initialize the generation-bound inventory scan cursor."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE shopify_connector_store_settings "
        "SET inventory_push_scan_cursor_id = "
        "COALESCE(inventory_push_scan_cursor_id, 0), "
        "inventory_push_scan_generation = "
        "COALESCE(inventory_push_scan_generation, 0) "
        "WHERE inventory_push_scan_cursor_id IS NULL "
        "OR inventory_push_scan_generation IS NULL"
    )
