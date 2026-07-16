from odoo import api, fields, models


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
    # D-010B-6 image ownership: the checksum of the image bytes the
    # connector last wrote into product.product.image_variant_1920 for this
    # binding. See shopify_connector_product_template_binding.py's own
    # shopify_image_checksum field for the exact ownership semantics.
    shopify_image_checksum = fields.Char(readonly=True)

    def _odoo_binding_field_name(self):
        return 'product_variant_id'

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'product_template_binding_id',
            'shopify_option_values',
            'shopify_price_snapshot',
            'shopify_compare_at_price_snapshot',
            'shopify_last_imported_at',
            'shopify_primary_image_url',
            'shopify_image_checksum',
        ))

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A product-variant binding with this Shopify GID already '
        'exists for this store.',
    )
    _store_product_variant_uniq = models.Constraint(
        'UNIQUE(store_id, product_variant_id)',
        'This product.product is already bound for this store.',
    )
