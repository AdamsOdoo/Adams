from odoo import fields, models


class ShopifyConnectorStoreSettingsProduct(models.Model):
    """Product-import store settings (Task 010B, §4).

    Extends the core ``shopify.connector.store.settings`` model via classic
    Odoo ``_inherit`` -- zero edits to any ``shopify_connector_core`` file.
    Adds only the three product-import feature switches Task 010B needs;
    the core price-source-of-truth and domain-enable flags are unchanged.
    """

    _inherit = 'shopify.connector.store.settings'

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
