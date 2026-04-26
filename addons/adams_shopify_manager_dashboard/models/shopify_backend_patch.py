from odoo import models


_BIND_COUNT_FIELDS = (
    'product_bind_count', 'customer_bind_count', 'order_bind_count',
    'product_error_count', 'customer_error_count', 'order_error_count',
    'inventory_bind_count', 'inventory_error_count',
    'total_error_count', 'total_synced_count', 'total_pending_count',
    'permanent_error_count', 'collection_bind_count', 'refund_bind_count',
    'sync_log_today_count', 'promoter_count', 'abandoned_cart_count',
    'payout_count', 'sync_health_pct',
)


class ShopifyBackend(models.Model):
    _inherit = 'shopify.backend'

    def _compute_bind_counts(self):
        # Safety net against older adams_shopify releases whose
        # _compute_bind_counts returns early on empty self.ids and leaves
        # NewId records without any assigned value, which trips Odoo's
        # onchange snapshotting with "Compute method failed to assign ...".
        new_records = self.filtered(lambda r: not isinstance(r.id, int))
        for rec in new_records:
            for fname in _BIND_COUNT_FIELDS:
                # sync_health_pct defaults to 100 (fully healthy) when there
                # are no bindings yet, matching the base compute logic.
                if fname == 'sync_health_pct':
                    setattr(rec, fname, 100)
                else:
                    setattr(rec, fname, 0)
        real_records = self - new_records
        if real_records:
            super(ShopifyBackend, real_records)._compute_bind_counts()
