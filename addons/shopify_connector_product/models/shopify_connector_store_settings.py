from odoo import api, fields, models


class ShopifyConnectorStoreSettingsProduct(models.Model):
    """Product-import store settings (Task 010B, §4).

    Extends the core ``shopify.connector.store.settings`` model via classic
    Odoo ``_inherit`` -- zero edits to any ``shopify_connector_core`` file.
    Adds only the three product-import feature switches Task 010B needs;
    the core price-source-of-truth and domain-enable flags are unchanged.
    """

    _inherit = 'shopify.connector.store.settings'

    @api.model
    def _additional_protected_settings_fields(self):
        """Protect durable product-scan state from generic ORM/RPC writes."""
        return super()._additional_protected_settings_fields() | frozenset((
            'product_last_import_checkpoint_at',
            'product_last_import_success_at',
            'product_scan_window_start_at',
            'product_scan_window_end_at',
            'product_scan_cursor',
            'product_scan_latest_at',
            'product_scan_page_count',
            'product_scan_generation',
        ))

    @api.model
    def _additional_settings_write_surfaces(self):
        """Expose one named service seam for future product scan writers."""
        return super()._additional_settings_write_surfaces() | frozenset((
            '_product_scan',
        ))

    # D-010B-6: per-store off switch for primary/variant image import.
    # Default True (basic image/media import is on by default).
    product_import_media_enabled = fields.Boolean(default=True)

    # D-010B-7: safe-refresh policy for previously imported products.
    # snapshot_only (default) -- merchant-editable Odoo fields are written
    # only at first import; refresh touches bindings/snapshots and applies
    # additive structural changes, never overwriting merchant edits.
    # shopify_fields -- refresh additionally re-applies the Shopify-owned
    # minimal set (source-of-truth prices, connector-owned images).
    product_import_refresh_mode = fields.Selection(
        selection=[
            ('snapshot_only', 'Snapshot Only'),
            ('shopify_fields', 'Shopify Fields'),
        ],
        default='snapshot_only',
    )

    # D-010B-2: how to handle a Shopify option whose name collides with an
    # existing Odoo product.attribute whose create_variant mode is
    # incompatible ('always'/'no_variant'). manual_review (default,
    # fail-closed) routes the product to blocked_manual_review /
    # binding_conflict; connector_owned creates a distinctly named
    # "<name> (Shopify)" dynamic attribute, leaving the merchant's
    # attribute untouched. Under neither setting is an existing attribute's
    # mode changed, and under neither is a phantom cartesian variant made.
    product_import_attribute_conflict_mode = fields.Selection(
        selection=[
            ('manual_review', 'Manual Review'),
            ('connector_owned', 'Connector Owned'),
        ],
        default='manual_review',
    )

    # ------------------------------------------------------------------
    # Batch 2 checkpoint 3: scheduled product import
    # ------------------------------------------------------------------
    #
    # These arrive WITH the producer that makes them real, not before it.
    # Checkpoint 1 deliberately declined to render a scheduled-import switch
    # while nothing in production enumerated a catalog, because a control whose
    # producer does not exist is a control that silently does nothing. The cron
    # in `data/shopify_connector_product_cron.xml` selects on the flag below,
    # so switching it on now genuinely starts scheduled scanning.
    product_scheduled_sync_enabled = fields.Boolean(default=False)

    # Written by the scan service only, and only after a scan completed. The
    # checkpoint is what the next incremental window starts from; the success
    # stamp is the human-facing "when did this last work", which is a
    # different question and deserves a different field -- a scan that failed
    # advances neither.
    product_last_import_checkpoint_at = fields.Datetime(readonly=True)
    product_last_import_success_at = fields.Datetime(readonly=True)
    product_scan_window_start_at = fields.Datetime(readonly=True)
    product_scan_window_end_at = fields.Datetime(readonly=True)
    product_scan_cursor = fields.Char(readonly=True)
    product_scan_latest_at = fields.Datetime(readonly=True)
    product_scan_page_count = fields.Integer(default=0, readonly=True)
    product_scan_generation = fields.Integer(default=0, readonly=True)
