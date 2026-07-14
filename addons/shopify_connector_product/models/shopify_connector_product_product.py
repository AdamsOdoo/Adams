from odoo import fields, models


class ProductProduct(models.Model):
    """Connector-owned compare-at price mirror on ``product.product``
    (Task 010B, D-010B-5).

    The Shopify ``ProductVariant.compareAtPrice`` (verified against the
    2026-07 Shopify Admin GraphQL ``ProductVariant`` reference: "The
    compare-at price of the variant in the default shop currency.", type
    ``Money``) is imported into this field, per Odoo product variant. The
    field is connector-maintained (written by the read-only importer),
    carries Shopify shop-currency semantics, and is added here (not on the
    core binding models) because the future product-export task reads it
    from the variant.

    Import-only in Task 010B: no export or write-back to Shopify. The
    binding-level ``shopify_compare_at_price_snapshot`` audit field is
    unchanged and remains the immutable per-import snapshot; this field is
    the current connector-maintained value on the master variant record.
    """

    _inherit = 'product.product'

    shopify_compare_at_price = fields.Float(
        string='Shopify Compare-at Price',
        digits='Product Price',
        help="Compare-at price imported from Shopify for this variant, in "
             "the Shopify shop currency. Connector-maintained by the "
             "product import; not exported or written back to Shopify by "
             "this module.",
    )
