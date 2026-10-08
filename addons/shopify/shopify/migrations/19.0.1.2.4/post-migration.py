import logging

from odoo import api, SUPERUSER_ID

_logger = logging.getLogger("Qamah:Shopify")

RECOMPUTE_BATCH_SIZE = 1000


def migrate(cr, version):
    """
    Recomputes 'is_restock_skipped_in_shopify' on existing returns during module upgrade.
    """
    if not version:
        return

    # Skip if the table doesn't exist yet (safe for fresh install)
    cr.execute("SELECT to_regclass('shopify_return_ts')")
    if cr.fetchone()[0] is None:
        return

    # Check if dependent column exists (safe for jump-upgrades)
    cr.execute("""
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'shopify_return_line_ts' AND column_name = 'force_restocked_qty'
    """)
    if not cr.fetchone():
        _logger.warning("Migration: force_restocked_qty missing, skipping Restock Skipped on Shopify' recompute.")
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    return_obj = env.get('shopify.return.ts')
    if return_obj is None or 'is_restock_skipped_in_shopify' not in return_obj._fields:
        return

    returns = return_obj.with_context(active_test=False).search([])
    if not returns:
        return

    field = return_obj._fields['is_restock_skipped_in_shopify']
    for index in range(0, len(returns), RECOMPUTE_BATCH_SIZE):
        batch = returns[index:index + RECOMPUTE_BATCH_SIZE]
        env.add_to_compute(field, batch)
        env.flush_all()
        env.invalidate_all()

    _logger.info("Migration: recomputed 'Restock Skipped on Shopify' on %s Shopify return(s).", len(returns))
