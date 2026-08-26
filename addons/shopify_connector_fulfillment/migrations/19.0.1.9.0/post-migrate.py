"""WP-6 initialize the generation-bound fulfillment scan cursor."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE shopify_connector_store_settings "
        "SET fulfillment_reconciliation_cursor_id = "
        "COALESCE(fulfillment_reconciliation_cursor_id, 0), "
        "fulfillment_reconciliation_generation = "
        "COALESCE(fulfillment_reconciliation_generation, 0) "
        "WHERE fulfillment_reconciliation_cursor_id IS NULL "
        "OR fulfillment_reconciliation_generation IS NULL"
    )
