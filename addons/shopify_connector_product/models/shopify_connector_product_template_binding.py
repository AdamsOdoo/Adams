from odoo import fields, models


class ShopifyConnectorProductTemplateBinding(models.Model):
    """Binds one Shopify Product to one Odoo ``product.template``.

    Extends the core ``shopify.connector.binding.mixin`` contract
    (DEC-013 per-domain-concrete-on-core-contract shape). Import-only
    (Task 010): every field below is populated by the read-only importer
    service (``shopify_connector_product_importer.py``) -- this model
    itself performs no Shopify call and has no export/write-back
    behaviour.
    """

    _name = 'shopify.connector.product.template.binding'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Product Template Binding'

    product_template_id = fields.Many2one(
        comodel_name='product.template',
        required=True,
        index=True,
        ondelete='restrict',
    )
    # Imported snapshot fields (readonly, informational/audit only --
    # never a second source of truth for matching; matching never reads
    # these, only shopify_gid/default_code/barcode -- MBQ-55 §7.1.D).
    shopify_title = fields.Char(readonly=True)
    shopify_status = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('archived', 'Archived'),
            ('draft', 'Draft'),
            ('unlisted', 'Unlisted'),
        ],
        readonly=True,
    )
    shopify_primary_image_url = fields.Char(readonly=True)
    shopify_last_imported_at = fields.Datetime(readonly=True)
    # D-010B-7 safe-refresh short-circuit: the exact Shopify `updatedAt`
    # timestamp string of the last fully-successful import for this product.
    # Stored verbatim (Char, not Datetime) so the remote value round-trips
    # exactly. When an active binding already records this exact value, the
    # importer short-circuits before any media download or database write.
    # Set only after a complete import succeeds; enqueue-level dedup
    # (payload_hash = updatedAt) is an Area-6 obligation, not this task's.
    shopify_updated_at = fields.Char(readonly=True)
    # D-010B-6 image ownership: the checksum of the image bytes the
    # connector last wrote into product.template.image_1920 for this
    # binding. Empty until the connector writes an image. On refresh it is
    # the ownership proof -- an Odoo image whose current checksum still
    # matches this value is connector-written and may be overwritten; a
    # merchant-replaced image (current checksum differs) is never
    # overwritten. Updated only after a successful connector write.
    shopify_image_checksum = fields.Char(readonly=True)

    def _odoo_binding_field_name(self):
        return 'product_template_id'

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A product-template binding with this Shopify GID already '
        'exists for this store.',
    )
    _store_product_template_uniq = models.Constraint(
        'UNIQUE(store_id, product_template_id)',
        'This product.template is already bound for this store.',
    )
