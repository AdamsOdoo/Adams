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
    # TD-011. The durable identity of the CURRENT attempt at exporting this
    # image, and the only thing that distinguishes "the substrate is
    # re-dispatching the job I already admitted" from "an operator has
    # authorised a fresh attempt after the last one failed".
    #
    # Core derives `idempotency_key` from `payload_hash` and never clears
    # it -- unlike `operation_scope_key`, it survives the job reaching a
    # terminal state, which is exactly what makes it a durable replay
    # guard. The media steps built their `payload_hash` from
    # `<step>:<checksum>` alone, so every attempt at the same image
    # produced the identical key forever. The first failure was therefore
    # permanent: a second attempt collided on
    # `(store_id, idempotency_key)`, the row could not be unlinked (it is
    # ownership evidence), and the checksum index refused a replacement
    # row. Including this ordinal in the hash gives each authorised resume
    # its own key while leaving replay of a single admitted job perfectly
    # deterministic -- and without weakening the constraint for anything
    # else in the system.
    resume_attempt = fields.Integer(
        default=0,
        readonly=True,
        help='Incremented once per authorised resume of this image export. '
             'Part of the job payload hash, so each resume gets its own '
             'durable idempotency identity while a re-dispatch of the same '
             'job keeps its original one.',
    )
    # Set when a resume is refused because the previous attempt's outcome
    # could not be established. Retained as the operator-facing reason.
    resume_blocked_reason = fields.Char(readonly=True)

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
            'resume_attempt',
            'resume_blocked_reason',
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
    # TD-011: the production route to the resume service
    # ------------------------------------------------------------------

    def action_shopify_resume_media_export(self):
        """Resume a stopped image export. The operator-facing entrance.

        TD-011 shipped `_resume_media_export` with no production caller: a
        leading-underscore service helper reachable only from tests, which
        makes it a capability the repository *describes* and an operator
        cannot use. This is that capability's one door -- a public action
        on the registry that already owns this surface, wired to the button
        on its form.

        Authority is derived from the repository's own accepted matrix, not
        chosen here. `action_manual_retry` admits **Operator or
        Administrator** for every retry state except
        `blocked_manual_review`, and `enqueue_preview` -- the other place
        work is admitted into the export pipeline -- admits the same two.
        A resume is a retry that admits work, so it takes that pair.
        `blocked_manual_review` is not reachable through this door at all:
        an unresolved mutation outcome is refused below, and its
        resolution stays on the Reviewer's `action_resolve_mutation_attempt`
        surface where it already lives.

        Both checks that bound the elevation run BEFORE it, in the order
        that matters:

        1. **Role.** Checked first so an unauthorised user learns nothing
           about whether the row exists.
        2. **Record access + company.** `check_access('read')` re-runs the
           model ACL *and* the two company record rules for THIS user on
           THIS row, which is what keeps SEC-3 store scoping intact -- the
           service that runs next is entirely `sudo()`, so this is the last
           point at which the acting user's own access is consulted.

           `read`, not `write`, and deliberately: the Operator's ACL row on
           this model is `1,0,0,0` and every column here is a protected
           binding field no role may write directly. Demanding `write`
           would refuse the exact role the accepted matrix admits, and
           granting it would broaden an ACL to satisfy a check rather
           than a need. This follows core's own pattern -- an Operator
           has read-only ACL on `shopify.connector.job` and still invokes
           `action_manual_retry`, whose writes go through `sudo()` after
           the role gate.

        No Shopify traffic occurs here. The resume ADMITS a job; the
        dispatcher runs it later, on its own transaction, through the same
        transport every other media step uses.
        """
        self.ensure_one()
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_operator'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Operator or Administrator may '
                'resume a media export.'
            )
        # Deliberately the un-elevated recordset: `self` here is browsed as
        # the acting user, so this is a real ACL/record-rule evaluation and
        # not a formality performed on a sudo() recordset.
        self.check_access('read')
        store = self.store_id.sudo()
        if store.company_id and store.company_id not in self.env.user.company_ids:
            raise AccessError(
                'This Shopify store belongs to another company.'
            )

        Media = self.env['shopify.connector.media.export.service']
        outstanding = Media._outstanding_media_job(self)
        before = self.resume_attempt
        job = Media._resume_media_export(self)
        self.invalidate_recordset()
        if not job:
            # The service has recorded the reason durably on the row. A
            # raise would roll that write back, so the refusal is reported
            # as a sticky notification instead -- the operator sees it now
            # AND the registry keeps it.
            return self._resume_notification(
                'danger',
                'Media export not resumed',
                self.resume_blocked_reason or (
                    'This image export cannot be resumed.'
                ),
            )
        if outstanding and job == outstanding:
            return self._resume_notification(
                'warning',
                'Already in progress',
                'This image export is already queued as job %d (attempt %d). '
                'Nothing further was admitted.' % (job.id, before),
            )
        return self._resume_notification(
            'success',
            'Media export resumed',
            'Attempt %d admitted as job %d, starting at step "%s". It runs '
            'on the job queue; no Shopify call has been made yet.' % (
                self.resume_attempt, job.id, job.job_type,
            ),
        )

    def _resume_notification(self, tone, title, message):
        """One operator-visible result, success or refusal alike."""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': tone,
                'title': title,
                'message': message,
                'sticky': tone != 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }

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
