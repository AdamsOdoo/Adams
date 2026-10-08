from odoo import api, SUPERUSER_ID


def migrate(cr, version):

    # Task: T7491 - Move existing data from shopify_discount_amount to marketplace_discount_amount.
    # 1. Ensure new column exists
    cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='sale_order_line' 
        AND column_name='marketplace_discount_amount'
    """)
    if not cr.fetchone():
        return

    # 2. Transfer data to new field
    cr.execute("""
        UPDATE sale_order_line
        SET marketplace_discount_amount = shopify_discount_amount_old
        WHERE shopify_discount_amount_old IS NOT NULL
    """)

    # 3. Cleanup temp column
    cr.execute("""
        ALTER TABLE sale_order_line
        DROP COLUMN IF EXISTS shopify_discount_amount_old
    """)
