"""WP-6 initialize durable product scan state without moving checkpoints."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "UPDATE shopify_connector_store_settings "
        "SET product_scan_page_count = COALESCE(product_scan_page_count, 0), "
        "product_scan_generation = COALESCE(product_scan_generation, 0) "
        "WHERE product_scan_page_count IS NULL "
        "OR product_scan_generation IS NULL"
    )
