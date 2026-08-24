from odoo import fields, models


class ShopifyConnectorStoreSettingsInventoryExtension(models.Model):
    """Task 013 §4: the two new inventory domain store settings fields.

    Extends the existing `shopify.connector.store.settings` model
    (`inventory_domain_enabled` already exists there, unchanged) with the
    scheduled-push-scan enablement flag and its own checkpoint timestamp.
    """

    _inherit = 'shopify.connector.store.settings'

    inventory_scheduled_sync_enabled = fields.Boolean(default=False)
    # Domain-owned checkpoint (ARCH PD-5): the scheduled push-scan cron's
    # own last-run marker for this store, independent of any other
    # domain's scan checkpoint.
    inventory_last_push_scan_at = fields.Datetime(readonly=True)
    inventory_push_scan_cursor_id = fields.Integer(default=0, readonly=True)
    inventory_push_scan_generation = fields.Integer(default=0, readonly=True)
