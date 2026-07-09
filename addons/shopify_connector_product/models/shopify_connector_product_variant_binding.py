from odoo import fields, models


class ShopifyConnectorProductVariantBinding(models.Model):
    """Binds one Shopify ProductVariant to one Odoo ``product.product``.

    Always linked to its parent template binding via
    ``product_template_binding_id`` -- a template binding never stands
    in for its variants' bindings, and a variant's own identity
    (``shopify_gid``, SKU, barcode) is independent of its parent
    template's identity (DEC-006 §A.7). Import-only (Task 010): every
    field below is populated by the read-only importer service -- this
    model itself performs no Shopify call and has no export/write-back
    behaviour.
    """

    _name = 'shopify.connector.product.variant.binding'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Product Variant Binding'

    product_variant_id = fields.Many2one(
        comodel_name='product.product',
        required=True,
        index=True,
        ondelete='restrict',
    )
    product_template_binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.template.binding',
        required=True,
        index=True,
        ondelete='restrict',
    )
    # Imported snapshot fields (readonly, exact types -- fixed on
    # control-room review, final prompt §7.2). No Monetary/currency
    # field: read-only price snapshots only, no write-back, no
    # price_source_of_truth enforcement in Task 010.
    shopify_option_values = fields.Text(readonly=True)
    shopify_price_snapshot = fields.Float(readonly=True)
    shopify_compare_at_price_snapshot = fields.Float(readonly=True)
    shopify_last_imported_at = fields.Datetime(readonly=True)
    shopify_primary_image_url = fields.Char(readonly=True)

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A product-variant binding with this Shopify GID already '
        'exists for this store.',
    )
    _store_product_variant_uniq = models.Constraint(
        'UNIQUE(store_id, product_variant_id)',
        'This product.product is already bound for this store.',
    )
