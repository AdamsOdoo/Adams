from odoo import api, fields, models


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

    # SEC-3 (#197): opt in to Odoo 19's native company consistency check
    # (`odoo/orm/models.py` L451/L4516/L4743). Together with `check_company=True`
    # on the business relation below, a store can only ever bind a record of its
    # own company -- enforced on create AND write, and under `sudo()`.
    _check_company_auto = True

    product_template_id = fields.Many2one(
        comodel_name='product.template',
        required=True,
        index=True,
        ondelete='restrict',
        check_company=True,
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
    # Complete Shopify source evidence. These are snapshots, not a second
    # matching source of truth; the importer remains the only sanctioned
    # writer and preserves null/empty values exactly enough for safe refresh.
    shopify_description_html = fields.Text(readonly=True)
    shopify_vendor = fields.Char(readonly=True)
    shopify_product_type = fields.Char(readonly=True)
    shopify_tags = fields.Json(readonly=True)
    shopify_last_imported_at = fields.Datetime(readonly=True)
    # False on legacy rows means the old importer never completed the birth
    # phase. The next valid import may initialize missing Odoo values once;
    # subsequent refreshes follow configured ownership instead.
    shopify_birth_initialized = fields.Boolean(readonly=True)
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

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'shopify_title',
            'shopify_status',
            'shopify_primary_image_url',
            'shopify_description_html',
            'shopify_vendor',
            'shopify_product_type',
            'shopify_tags',
            'shopify_last_imported_at',
            'shopify_birth_initialized',
            'shopify_updated_at',
            'shopify_image_checksum',
        ))

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A product-template binding with this Shopify GID already '
        'exists for this store.',
    )
    _store_product_template_uniq = models.Constraint(
        'UNIQUE(store_id, product_template_id)',
        'This product.template is already bound for this store.',
    )
