"""Minimal schema bridge for installing W2 over an older installed W1.

W1 remains the canonical owner of these fields and its versioned migration
verifies them when W1 itself is upgraded.  Odoo does not upgrade an already
installed dependency during ``-i shopify_connector_product_webhook`` though,
so this optional addon must make the two additive columns available before the
current W1 registry is loaded.  The bridge is deliberately SQL-only,
idempotent, and limited to the known W1-owned table/columns.
"""

_TABLE = 'shopify_connector_webhook_subscription'
_COLUMNS = (
    'expected_include_fields',
    'actual_include_fields',
)

# Installing an optional W2 addon does not upgrade already-installed W1
# dependencies, although Odoo loads their current Python models into the new
# registry. Keep that registry coherent with the supported old-W1 schema by
# adding only the additive columns introduced since the pinned bridge origin.
# Their owning W1 migrations remain authoritative when those modules upgrade.
_ADDITIVE_COLUMNS = {
    'shopify_connector_store_settings': (
        ('fulfillment_reconciliation_cursor_id', 'integer'),
        ('fulfillment_reconciliation_generation', 'integer'),
        ('fulfillment_reconciliation_observed_through_at', 'timestamp'),
        ('inventory_push_scan_cursor_id', 'integer'),
        ('inventory_push_scan_generation', 'integer'),
        ('product_scan_window_start_at', 'timestamp'),
        ('product_scan_window_end_at', 'timestamp'),
        ('product_scan_cursor', 'varchar'),
        ('product_scan_latest_at', 'timestamp'),
        ('product_scan_page_count', 'integer'),
        ('product_scan_generation', 'integer'),
        ('sale_order_scan_window_start_at', 'timestamp'),
        ('sale_order_scan_window_end_at', 'timestamp'),
        ('sale_order_scan_cursor', 'varchar'),
        ('sale_order_scan_latest_at', 'timestamp'),
        ('sale_order_scan_page_count', 'integer'),
        ('sale_order_scan_generation', 'integer'),
    ),
    'shopify_connector_inventory_level_binding': (
        ('first_push_previewed_at', 'timestamp'),
    ),
    'shopify_connector_order_binding': (
        ('shopify_line_composition_fingerprint', 'varchar'),
        ('review_reason_code', 'varchar'),
        ('review_reason', 'text'),
        ('review_required_action', 'text'),
    ),
    'product_template': (
        ('shopify_export_status_managed', 'boolean'),
    ),
}
_SQL_UDT = {
    'integer': 'int4',
    'timestamp': 'timestamp',
    'varchar': 'varchar',
    'text': 'text',
    'boolean': 'bool',
}


def pre_init_hook(env):
    """Create and verify the W1 evidence columns before registry setup."""
    cr = env.cr
    cr.execute(
        'ALTER TABLE IF EXISTS "%s" '
        'ADD COLUMN IF NOT EXISTS expected_include_fields jsonb, '
        'ADD COLUMN IF NOT EXISTS actual_include_fields jsonb' % _TABLE,
    )
    cr.execute(
        "SELECT column_name, udt_name FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = ANY(%s)",
        (_TABLE, list(_COLUMNS)),
    )
    columns = {row[0]: row[1] for row in cr.fetchall()}
    missing = [name for name in _COLUMNS if name not in columns]
    wrong_type = [
        name for name in _COLUMNS
        if name in columns and columns[name] != 'jsonb'
    ]
    if missing or wrong_type:
        details = []
        if missing:
            details.append('missing: %s' % ', '.join(missing))
        if wrong_type:
            details.append('non-jsonb: %s' % ', '.join(wrong_type))
        raise RuntimeError(
            'W2 cannot install safely over the installed W1 schema (%s).'
            % '; '.join(details)
        )

    for table, columns_to_add in _ADDITIVE_COLUMNS.items():
        cr.execute('SELECT to_regclass(%s)', (table,))
        if not cr.fetchone()[0]:
            # A full fresh install may load this optional addon before an
            # unrelated W1 owner has created its table. That owner will then
            # create the current schema normally. In the W2-over-old-W1 path
            # every W1 table exists and is bridged and verified below.
            continue
        for column, sql_type in columns_to_add:
            cr.execute(
                'ALTER TABLE IF EXISTS "%s" '
                'ADD COLUMN IF NOT EXISTS "%s" %s'
                % (table, column, sql_type),
            )
        cr.execute(
            "SELECT column_name, udt_name FROM information_schema.columns "
            "WHERE table_name = %s AND column_name = ANY(%s)",
            (table, [column for column, _sql_type in columns_to_add]),
        )
        actual = {row[0]: row[1] for row in cr.fetchall()}
        expected = {
            column: _SQL_UDT[sql_type]
            for column, sql_type in columns_to_add
        }
        if actual != expected:
            raise RuntimeError(
                'W2 cannot install safely over the installed W1 schema '
                '(additive bridge mismatch on %s: expected %s, got %s).'
                % (table, expected, actual)
            )

    # Mirror the owning W1 migrations' safe seeds. Existing resumability
    # counters start at zero. Existing unbound products retain the normal
    # explicit-status default, while imported products become Shopify-status
    # unmanaged and inherit a unanimous remote status where one is known.
    cr.execute(
        """
        UPDATE shopify_connector_store_settings
           SET fulfillment_reconciliation_cursor_id = COALESCE(
                   fulfillment_reconciliation_cursor_id, 0
               ),
               fulfillment_reconciliation_generation = COALESCE(
                   fulfillment_reconciliation_generation, 0
               ),
               inventory_push_scan_cursor_id = COALESCE(
                   inventory_push_scan_cursor_id, 0
               ),
               inventory_push_scan_generation = COALESCE(
                   inventory_push_scan_generation, 0
               ),
               product_scan_page_count = COALESCE(product_scan_page_count, 0),
               product_scan_generation = COALESCE(product_scan_generation, 0),
               sale_order_scan_page_count = COALESCE(
                   sale_order_scan_page_count, 0
               ),
               sale_order_scan_generation = COALESCE(
                   sale_order_scan_generation, 0
               )
        """
    )
    cr.execute(
        "UPDATE product_template "
        "SET shopify_export_status_managed = TRUE "
        "WHERE shopify_export_status_managed IS NULL"
    )
    cr.execute(
        "SELECT to_regclass('shopify_connector_product_template_binding')"
    )
    if cr.fetchone()[0]:
        cr.execute(
            """
            WITH imported AS (
                SELECT product_template_id,
                       CASE WHEN COUNT(DISTINCT shopify_status) = 1
                                  AND MIN(shopify_status) IN (
                                      'active', 'draft', 'archived'
                                  )
                            THEN MIN(shopify_status)
                            ELSE NULL
                       END AS agreed_status
                  FROM shopify_connector_product_template_binding
                 GROUP BY product_template_id
            )
            UPDATE product_template AS pt
               SET shopify_export_status = COALESCE(
                       imported.agreed_status, pt.shopify_export_status
                   ),
                   shopify_export_status_managed = FALSE
              FROM imported
             WHERE pt.id = imported.product_template_id
            """
        )
