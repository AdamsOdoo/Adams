from odoo import api, SUPERUSER_ID


def migrate(cr, version):

    # Task: T7491 - Move existing data from shopify_discount_amount to marketplace_discount_amount.
    # 1. Create temp column (correct type)
    cr.execute("""
        ALTER TABLE sale_order_line
        ADD COLUMN IF NOT EXISTS shopify_discount_amount_old DOUBLE PRECISION
    """)

    # 2. Copy data from old field
    cr.execute("""
        UPDATE sale_order_line
        SET shopify_discount_amount_old = shopify_discount_amount
        WHERE shopify_discount_amount IS NOT NULL
    """)
