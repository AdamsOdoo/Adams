"""WP-6 make the terminal webhook retention access path explicit."""


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        "CREATE INDEX IF NOT EXISTS shopify_webhook_terminal_retention_idx "
        "ON shopify_connector_webhook_delivery (received_at, id) "
        "WHERE state IN ('processed', 'ignored', 'failed', 'manual_review')"
    )
