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

    # SEC-3 (#197): opt in to Odoo 19's native company consistency check
    # (`odoo/orm/models.py` L451/L4516/L4743). Together with `check_company=True`
    # on the business relation below, a store can only ever bind a record of its
    # own company -- enforced on create AND write, and under `sudo()`.
    _check_company_auto = True

    product_variant_id = fields.Many2one(
        comodel_name='product.product',
        required=True,
        index=True,
        ondelete='restrict',
        check_company=True,
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

    # ------------------------------------------------------------------
    # SEC-3 (#197): same-store consistency with the connector parent.
    #
    # Company equality is NOT enough here. One Odoo company may own several
    # Shopify stores, so a row in store A pointing at a parent in store B is
    # company-consistent and store-inconsistent -- two different shops' records
    # mixed together, which no company check can see. `init()` additionally
    # quarantines rows written before this constraint existed; it never guesses
    # which half is wrong and never re-homes anything.
    # ------------------------------------------------------------------

    @api.model
    def _sec3_parent_scope_relations(self):
        return (('product_template_binding_id', 'store'),)

    @api.constrains('store_id', 'product_template_binding_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()
