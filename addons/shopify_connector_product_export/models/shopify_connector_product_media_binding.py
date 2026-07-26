"""The media ownership registry (D-015B-1), narrowed to append-only.

What this registry can and cannot prove, stated plainly because the
distinction decides the whole posture: a row here proves the connector
*created* a File. It does **not** prove the File is used only by this
product now. The Shopify `File` interface exposes `alt`, `createdAt`,
`fileErrors`, `fileStatus`, `id`, `preview` and `updatedAt` and **no**
reverse-reference connection (re-verified against the 2026-07 reference,
2026-07-26), so there is no official query that could prove exclusive use.

The consequence, per the 2026-07-26 control-room ruling, is stronger than
the packet's detach-only posture: this module is **append-only**. It never
calls `fileDelete`, never detaches an association, and never reorders
media. When an Odoo image changes, the new image is uploaded and appended,
and the superseded row is flagged `orphan_cleanup_candidate` for a later
explicit, operator-driven cleanup capability that does not exist yet and is
not on any automatic path.

Two distinct Shopify identities are stored separately, because the API uses
distinct ones and the ambiguous phrase "Media/File GID" is how they get
conflated:

* `shopify_gid` — the **File GID** returned by `fileCreate`
  (`gid://shopify/MediaImage/...`), the durable asset in the store's Files.
* `shopify_product_media_gid` — the identity observed on the *product's*
  media connection once the association succeeded. Null until then, and
  written only from a read that actually saw it.
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError

MEDIA_ROLE_SELECTION = [
    ('primary', 'Primary Template Image'),
    ('variant', 'Variant Image'),
]

REMOTE_STATUS_SELECTION = [
    ('staged', 'Upload Target Staged'),
    ('uploaded', 'Uploaded'),
    ('processing', 'Processing'),
    ('ready', 'Ready'),
    ('associated', 'Associated'),
    ('failed', 'Failed'),
]

TERMINAL_MEDIA_STATUSES = ('associated', 'failed')
# The statuses whose rows the poll cron still has work for.
POLLABLE_MEDIA_STATUSES = ('uploaded', 'processing')


class ShopifyConnectorProductMediaBinding(models.Model):
    _name = 'shopify.connector.product.media.binding'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Product Media Binding'
    _order = 'id desc'

    product_template_binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.template.binding',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    product_variant_binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.variant.binding',
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    # SHA-256 of the exact bytes this row exported. This is the whole
    # idempotency mechanism: an unchanged Odoo image has the same checksum,
    # finds this row, and becomes a no-op instead of a second upload.
    odoo_image_checksum = fields.Char(required=True, readonly=True)
    media_role = fields.Selection(
        selection=MEDIA_ROLE_SELECTION,
        required=True,
        readonly=True,
    )
    remote_status = fields.Selection(
        selection=REMOTE_STATUS_SELECTION,
        required=True,
        default='staged',
        index=True,
        readonly=True,
    )
    shopify_product_media_gid = fields.Char(readonly=True)
    # The connector-generated filename, deterministic from the template and
    # the checksum, so a verification read after an ambiguous outcome can
    # find what this attempt uploaded without guessing.
    connector_filename = fields.Char(required=True, readonly=True)
    staged_resource_url = fields.Char(readonly=True)
    staged_upload_url = fields.Char(readonly=True)
    staged_upload_parameters = fields.Json(readonly=True)
    remote_failure_note = fields.Text(readonly=True)
    # Set when a newer image for the same role supersedes this row. The File
    # is RETAINED — this flag is the queue for a later explicit cleanup
    # capability, never an instruction any automatic path acts on.
    orphan_cleanup_candidate = fields.Boolean(
        default=False,
        index=True,
        readonly=True,
        help='This connector-created File was superseded by a newer image. '
             'The File is retained: Shopify exposes no reverse-reference '
             'query that could prove it is unused elsewhere, so nothing is '
             'deleted automatically.',
    )
    exported_at = fields.Datetime(readonly=True)
    last_verified_at = fields.Datetime(readonly=True)

    def _odoo_binding_field_name(self):
        # This binding's Odoo-side identity is its parent template/variant
        # binding, not a business record of its own, so the mixin's generic
        # override seam has nothing to point at here.
        return False

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'product_template_binding_id',
            'product_variant_binding_id',
            'odoo_image_checksum',
            'media_role',
            'remote_status',
            'shopify_product_media_gid',
            'connector_filename',
            'staged_resource_url',
            'staged_upload_url',
            'staged_upload_parameters',
            'remote_failure_note',
            'orphan_cleanup_candidate',
            'exported_at',
            'last_verified_at',
        ))

    # `shopify_gid` is the mixin's required File GID. It cannot be known
    # before `fileCreate` returns, so a row in `staged` state carries a
    # deterministic placeholder derived from the connector filename; the
    # uniqueness index below is on the real value once it lands.
    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A product-media binding with this Shopify File GID already exists '
        'for this store.',
    )
    _store_template_role_checksum_uniq = models.UniqueIndex(
        '(store_id, product_template_binding_id, media_role, '
        'odoo_image_checksum) WHERE product_variant_binding_id IS NULL',
        'This template image checksum is already exported for this store.',
    )
    _store_variant_role_checksum_uniq = models.UniqueIndex(
        '(store_id, product_variant_binding_id, media_role, '
        'odoo_image_checksum) WHERE product_variant_binding_id IS NOT NULL',
        'This variant image checksum is already exported for this store.',
    )

    def unlink(self):
        raise AccessError(
            'Media-export ownership evidence can never be deleted: it is the '
            'only proof of which remote Files this connector created.'
        )

    # ------------------------------------------------------------------
    # SEC-3 (#197): same-store consistency with BOTH connector parents.
    # ------------------------------------------------------------------

    @api.model
    def _sec3_parent_scope_relations(self):
        return (
            ('product_template_binding_id', 'store'),
            ('product_variant_binding_id', 'store'),
        )

    @api.constrains(
        'store_id', 'product_template_binding_id', 'product_variant_binding_id',
    )
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()
