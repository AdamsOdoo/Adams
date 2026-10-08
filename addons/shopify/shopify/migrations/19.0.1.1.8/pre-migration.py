def migrate(cr, version):
    # Skip if the table doesn't exist yet
    cr.execute("SELECT to_regclass('shopify_return_line_ts')")
    if cr.fetchone()[0] is None:
        return

    # 1. Create temp column
    cr.execute("""
        ALTER TABLE shopify_return_line_ts
        ADD COLUMN IF NOT EXISTS return_reason_old VARCHAR
    """)

    # 2. Copy data from the old field
    cr.execute("""
        UPDATE shopify_return_line_ts
        SET return_reason_old = return_reason
        WHERE return_reason IS NOT NULL
    """)
