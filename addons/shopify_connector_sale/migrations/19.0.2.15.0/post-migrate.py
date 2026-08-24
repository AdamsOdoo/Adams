"""WP-6 initialize durable order scan state without moving checkpoints."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE shopify_connector_store_settings "
        "SET sale_order_scan_page_count = "
        "COALESCE(sale_order_scan_page_count, 0), "
        "sale_order_scan_generation = "
        "COALESCE(sale_order_scan_generation, 0) "
        "WHERE sale_order_scan_page_count IS NULL "
        "OR sale_order_scan_generation IS NULL"
    )
