"""Append-only product media export (Task 015B).

The pipeline, and why it has this exact shape
---------------------------------------------

D-015B-4 is binding: **no association is ever submitted before the File
reaches `READY`.** That single requirement determines everything else.

`productUpdate(media:)` and `productSet(files:)` both take a *source URL*
and create the media as a side effect — the media object does not exist
until the association call, so there is nothing to poll and no way to be
READY-gated. Only `fileCreate` produces an independently addressable File
whose `fileStatus` can be polled, and in 2026-07 the mutation that attaches
an *existing* File to a product is `fileUpdate(referencesToAdd: [productId])`
("The IDs of the references to add to the file. Currently only accepts
product IDs.").

So the pipeline is four jobs, one remote effect each:

1. `media_stage`    — `stagedUploadsCreate`, returns an upload target
2. `media_upload`   — plain HTTPS upload of the Odoo bytes to that target
                      (no Shopify GraphQL call, no Shopify state change)
3. `media_file_create` — `fileCreate` from the staged resource URL
4. `media_poll`     — read `fileStatus` until `READY` (cron-enqueued)
5. `media_associate` — `fileUpdate(referencesToAdd: [productId])`

Splitting them is not ceremony: Layer 2 permits exactly one mutation
attempt per job for its whole lifetime, and each of steps 1, 3 and 5 is a
distinct remote mutation that needs its own durable attempt record and its
own reconciliation read.

Scope correction, recorded because it revises an earlier conclusion
------------------------------------------------------------------

The 2026-07-26 source-verification record concluded that least privilege
for media is `write_images` + `write_products`, on the evidence that
`fileCreate` accepts `write_images`. That is correct for `fileCreate` and
**insufficient for the pipeline**: `fileUpdate` requires `write_files` or
`write_themes` and does **not** accept `write_images` (2026-07 reference,
read 2026-07-26). Since `write_themes` must never be requested and the
READY gate forbids the association path that would have needed only
`write_products`, the minimal set that actually satisfies the binding
requirements is **`write_files` + `write_products`**. `write_files`
subsumes `write_images` for `fileCreate`, so the set is two scopes, not
three.

Append-only, and what that costs
--------------------------------

Nothing here deletes or detaches. `fileDelete` appears nowhere in this
module, and neither does any detach or reorder mutation. When an Odoo image
changes, the new image is uploaded and appended and the superseded registry
row is flagged `orphan_cleanup_candidate`; the old File and its association
are **retained**. The honest cost is that a replaced image leaves the old
one on the product until an operator removes it, and that limitation is
recorded rather than engineered around — because the alternative needs a
`File` reverse-reference query to prove exclusive use, and 2026-07 exposes
none.
"""

import base64
import hashlib
import logging
import uuid

import requests
from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)
from odoo.addons.shopify_connector_core.tools.api_version import (
    SHOPIFY_API_VERSION,
)
from odoo.addons.shopify_connector_core.tools.search_syntax import (
    search_term,
)

from .shopify_connector_product_export_service import (
    ERROR_CLASS_BINDING_CONFLICT,
    ERROR_CLASS_CONFIGURATION,
    ERROR_CLASS_DATA_SHAPE,
    ERROR_CLASS_DESTRUCTIVE,
    ERROR_CLASS_TEMPORARY,
    ERROR_CLASS_VALIDATION,
    SUBREASON_BINDING_CONFLICT,
    SUBREASON_DESTRUCTIVE,
    SUBREASON_DUPLICATE,
    SUBREASON_STORE_IDENTITY,
)

_logger = logging.getLogger(__name__)

JOB_TYPE_MEDIA_STAGE = 'product_export_media_stage'
JOB_TYPE_MEDIA_UPLOAD = 'product_export_media_upload'
JOB_TYPE_MEDIA_FILE_CREATE = 'product_export_media_file_create'
JOB_TYPE_MEDIA_POLL = 'product_export_media_poll'
JOB_TYPE_MEDIA_ASSOCIATE = 'product_export_media_associate'

MEDIA_MUTATION_DOMAINS = (
    JOB_TYPE_MEDIA_STAGE,
    JOB_TYPE_MEDIA_FILE_CREATE,
    JOB_TYPE_MEDIA_ASSOCIATE,
)
MEDIA_STEP_TYPES = MEDIA_MUTATION_DOMAINS + (
    JOB_TYPE_MEDIA_UPLOAD,
)

# Transport bounds for the staged upload. Mirrors Task 010B's image-download
# rules: HTTPS only, a hard timeout, and a size cap, so a staged target that
# hangs or a pathological image cannot hold a worker.
_UPLOAD_CONNECT_TIMEOUT_SECONDS = 10
_UPLOAD_READ_TIMEOUT_SECONDS = 60
MAX_IMAGE_BYTES = 20 * 1024 * 1024

# TD-011. The two forms core's `(store_id, idempotency_key)` constraint can
# surface as: the friendly `models.Constraint` message, which Odoo
# substitutes only at the HTTP boundary, and the raw index name, which is
# what an inline savepoint flush actually raises. Both are matched, on the
# same reasoning as the inventory module's pair-scope equivalents.
IDEMPOTENCY_CONSTRAINT_MESSAGE = (
    'A job with this idempotency key already exists for this store.'
)
IDEMPOTENCY_CONSTRAINT_NAME = (
    'shopify_connector_job_store_idempotency_key_uniq'
)

# TD-011 correction. The job states that still reach a dispatcher without
# anybody doing anything: a job in one of these will run (or retry) on its
# own, so a second resume request while one is outstanding must COALESCE on
# it rather than admit a parallel attempt at the same image. The remaining
# non-terminal states (`failed_retryable`, `blocked_manual_review`) require a
# deliberate operator act to move, which is exactly what a resume is.
MEDIA_JOB_OUTSTANDING_STATES = ('draft', 'queued', 'running', 'retry_waiting')

STAGED_RESOURCE = 'PRODUCT_IMAGE'
MEDIA_CONTENT_TYPE = 'IMAGE'
# `fileCreate` requires a content type; the Odoo image pipeline normalises to
# PNG or JPEG and we only ever declare what we actually send.
IMAGE_MIME_PNG = 'image/png'


def image_checksum(binary):
    """SHA-256 of the exact bytes that will be uploaded."""
    return hashlib.sha256(binary).hexdigest()


class ShopifyConnectorMediaExportService(models.AbstractModel):
    _name = 'shopify.connector.media.export.service'
    _description = 'Shopify Connector Product Media Export Service'

    @api.model
    def _media_step_types(self):
        return MEDIA_STEP_TYPES

    # ------------------------------------------------------------------
    # Odoo-side image resolution
    # ------------------------------------------------------------------

    @api.model
    def _decoded_image(self, record, field_name):
        raw = record[field_name]
        if not raw:
            return None
        try:
            binary = base64.b64decode(raw)
        except Exception:
            return None
        if not binary or len(binary) > MAX_IMAGE_BYTES:
            return None
        return binary

    @api.model
    def _connector_filename(self, template_id, checksum):
        """Deterministic, recognisably connector-owned, and checksum-bearing.

        The determinism is what makes a verification read possible after an
        ambiguous outcome: the connector can ask Shopify for the filename it
        would have used instead of guessing which of several uploads was its
        own.
        """
        return 'odoo-%s-%s.png' % (template_id, checksum[:8])

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    @api.model
    def _preview_media(self, store, template, binding):
        """Enumerate the append-only media plan and the untouched remainder.

        Returns `(steps, diff)`. Media export is skipped entirely — with a
        stated reason, never silently — unless the store says Odoo owns
        media (D-015B-7), because a store importing images from Shopify and
        exporting them to Shopify would ping-pong forever.
        """
        settings = self.env['shopify.connector.product.export.service']._settings(
            store
        )
        if not settings or settings.media_source_of_truth != 'odoo':
            return [], {
                'exported': False,
                'reason': (
                    'Media export is off for this store: media_source_of_truth '
                    'is %r, and export runs only under "odoo".' % (
                        settings.media_source_of_truth if settings else None,
                    )
                ),
                'appends': [],
            }
        if not binding or not binding.shopify_gid:
            # Media rides on an existing product. On the create path the
            # product does not exist yet, so media is planned by the next
            # preview after the create bound it — stated rather than implied.
            return [], {
                'exported': False,
                'reason': 'Media is appended once the product exists on '
                          'Shopify. Re-preview after the create completes.',
                'appends': [],
            }

        MediaBinding = self.env['shopify.connector.product.media.binding']
        steps = []
        appends = []
        candidates = [('primary', template, 'image_1920', False)]
        for variant in template.product_variant_ids:
            candidates.append(('variant', variant, 'image_variant_1920', variant))

        VariantBinding = self.env[
            'shopify.connector.product.variant.binding'
        ]
        for role, record, field_name, variant in candidates:
            binary = self._decoded_image(record, field_name)
            if not binary:
                continue
            checksum = image_checksum(binary)
            variant_binding = False
            if role == 'variant':
                variant_binding = VariantBinding.sudo().search([
                    ('store_id', '=', store.id),
                    ('product_variant_id', '=', variant.id),
                ], limit=1)
                if not variant_binding:
                    # An unbound variant has no remote identity to attach to.
                    continue
            domain = [
                ('store_id', '=', store.id),
                ('product_template_binding_id', '=', binding.id),
                ('media_role', '=', role),
                ('odoo_image_checksum', '=', checksum),
            ]
            if variant_binding:
                domain.append(
                    ('product_variant_binding_id', '=', variant_binding.id)
                )
            else:
                domain.append(('product_variant_binding_id', '=', False))
            existing = MediaBinding.sudo().search(domain, limit=1)
            if existing and existing.remote_status == 'associated':
                # Checksum no-op: this exact image is already exported. This
                # is the whole duplicate-prevention mechanism and it costs
                # one local query.
                continue
            appends.append({
                'role': role,
                'checksum': checksum,
                'odoo_variant_id': variant.id if variant else False,
                'filename': self._connector_filename(template.id, checksum),
                'resuming': bool(existing),
            })
            steps.append({
                'step': JOB_TYPE_MEDIA_STAGE,
                'state': 'pending',
                'role': role,
                'checksum': checksum,
                'odoo_variant_id': variant.id if variant else False,
            })
        return steps, {
            'exported': bool(appends),
            'appends': appends,
            'reason': (
                'Every image below is APPENDED. Existing Shopify media — '
                'including images this connector uploaded earlier — is never '
                'replaced, detached, reordered or deleted.'
            ),
        }

    # ------------------------------------------------------------------
    # Registry rows and step enqueue
    # ------------------------------------------------------------------

    @api.model
    def _ensure_media_row(self, preview, step):
        """The durable row is created BEFORE the first remote effect.

        Same principle as a Layer 2 attempt record: if the connector is
        about to touch a merchant's store, the evidence that it intended to
        exists first.
        """
        MediaBinding = self.env['shopify.connector.product.media.binding']
        store = preview.store_id
        binding = preview.product_template_binding_id
        checksum = step['checksum']
        variant_binding = False
        if step.get('odoo_variant_id'):
            variant_binding = self.env[
                'shopify.connector.product.variant.binding'
            ].sudo().search([
                ('store_id', '=', store.id),
                ('product_variant_id', '=', step['odoo_variant_id']),
            ], limit=1)
        domain = [
            ('store_id', '=', store.id),
            ('product_template_binding_id', '=', binding.id),
            ('media_role', '=', step['role']),
            ('odoo_image_checksum', '=', checksum),
            ('product_variant_binding_id', '=',
             variant_binding.id if variant_binding else False),
        ]
        row = MediaBinding.sudo().search(domain, limit=1)
        if row:
            return row
        filename = self._connector_filename(
            preview.product_template_id.id, checksum,
        )
        # `shopify_gid` is required by the binding mixin and the real File
        # GID does not exist until `fileCreate` returns. A deterministic
        # placeholder keeps the row honest about not having one yet, and is
        # unique per (store, filename) so it cannot collide.
        return MediaBinding.sudo().create({
            'store_id': store.id,
            'product_template_binding_id': binding.id,
            'product_variant_binding_id':
                variant_binding.id if variant_binding else False,
            'media_role': step['role'],
            'odoo_image_checksum': checksum,
            'connector_filename': filename,
            'shopify_gid': 'pending:%s' % filename,
            'remote_status': 'staged',
        })

    @api.model
    def _enqueue_media_step(self, preview, step):
        row = self._ensure_media_row(preview, step)
        return self._admit_media_job(
            preview.store_id, step['step'], row,
            preview.remote_product_gid or False,
        )

    @api.model
    def _media_payload_hash(self, row, step_type):
        """TD-011: the payload hash carries the row's resume ordinal.

        Deterministic for a given (step, image, attempt), so re-dispatching
        one admitted job replays under its original identity exactly as
        before. Different across authorised resumes, so a second attempt
        at an image that failed is a genuinely new job rather than a
        permanent `(store_id, idempotency_key)` collision.
        """
        return '%s:%s:%d' % (
            step_type, row.odoo_image_checksum, row.resume_attempt,
        )

    @api.model
    def _admit_media_job(self, store, step_type, row, target_gid):
        """Admit one media job, containing a duplicate collision.

        TD-011 requirement: a duplicate admission must not take down work
        that has nothing to do with it. Without the savepoint the `23505`
        surfaces during the enclosing flush and poisons the whole
        transaction, so a single already-admitted image ends the drain pass
        for every other store in it.

        Only the exact idempotency collision is swallowed, and only after
        re-confirming that the job it collided with really exists. Every
        other error -- store state, domain gating, company, illegal
        transition, an unrelated constraint -- propagates unchanged.
        """
        Service = self.env['shopify.connector.product.export.service']
        payload_hash = self._media_payload_hash(row, step_type)

        def _existing():
            Job = self.env['shopify.connector.job']
            Job.flush_model()
            return Job.sudo().search([
                ('store_id', '=', store.id),
                ('job_type', '=', step_type),
                ('res_model', '=', row._name),
                ('res_id', '=', row.id),
                ('payload_hash', '=', payload_hash),
            ], limit=1)

        existing = _existing()
        if existing:
            return existing
        try:
            with self.env.cr.savepoint():
                return Service._enqueue(
                    store, step_type, 'manual_sync', row._name, row.id,
                    shopify_target_gid=target_gid,
                    payload_hash=payload_hash,
                )
        except (ValidationError, IntegrityError) as exc:
            message = str(exc)
            if (
                IDEMPOTENCY_CONSTRAINT_MESSAGE not in message
                and IDEMPOTENCY_CONSTRAINT_NAME not in message
            ):
                raise
            collided = _existing()
            if not collided:
                raise
            _logger.info(
                'Media step %s for row %d is already admitted under this '
                'attempt identity; coalescing rather than failing the pass.',
                step_type, row.id,
            )
            return collided

    # ------------------------------------------------------------------
    # TD-011: authorised resume of a media export that stopped
    # ------------------------------------------------------------------

    #: Where a resume re-enters the chain, per the row's own remote status.
    #: `staged` restarts at the staging call because a staged target
    #: expires; `uploaded` already has one and needs the File created;
    #: `processing`/`ready` have a File and need the poll or the
    #: association.
    RESUME_ENTRY_STEP = {
        'staged': JOB_TYPE_MEDIA_STAGE,
        'uploaded': JOB_TYPE_MEDIA_FILE_CREATE,
        'processing': JOB_TYPE_MEDIA_POLL,
        'ready': JOB_TYPE_MEDIA_ASSOCIATE,
        'failed': JOB_TYPE_MEDIA_STAGE,
    }

    @api.model
    def _media_resume_blocker(self, row):
        """Why this row may not be resumed, or `False` if it may be.

        The order matters. Association is checked first because it is the
        one irreversible outcome: this pipeline is append-only, so a
        resume that re-ran the association would add a second reference
        to the same File and there is no detach to undo it.

        Ambiguity is checked next. A resume is a new mutation, and a new
        mutation may not be admitted while the previous attempt's outcome
        is unknown -- that is how one uncertain call becomes two real
        ones. An unresolved `uncertain` attempt already has its own
        reconciliation and manual-review boundary; the resume waits for
        it rather than racing it.
        """
        if row.remote_status == 'associated':
            return (
                'This image is already associated with the product. The '
                'media pipeline is append-only, so resuming would add a '
                'second reference to the same File.'
            )
        # A `shopify.connector.mutation.attempt` carries no res_model/res_id
        # of its own -- it belongs to a JOB. So the row's own jobs are the
        # route to its attempts.
        jobs = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', row.store_id.id),
            ('res_model', '=', row._name),
            ('res_id', '=', row.id),
        ])
        if not jobs:
            return False
        attempt = self.env['shopify.connector.mutation.attempt'].sudo().search(
            [('job_id', 'in', jobs.ids)], order='id desc', limit=1,
        )
        if (
            attempt
            and attempt.observed_outcome in ('pending', 'uncertain')
            and not attempt.resolution_disposition
        ):
            return (
                'The previous attempt for this image has no established '
                'outcome yet. It must be reconciled before another mutation '
                'may be admitted.'
            )
        return False

    @api.model
    def _outstanding_media_job(self, row):
        """The job for this row that is still going to run by itself.

        TD-011 correction. Without this, two resume requests in a row --
        an impatient double-click, or an operator returning to a screen
        that still shows the failure -- each incremented `resume_attempt`,
        each produced a DIFFERENT payload hash, and each therefore
        admitted its own job. `_admit_media_job`'s collision handling
        cannot catch that: the two attempts are, by construction, not
        colliding. Two live jobs for one image is exactly the duplicate
        admission the resume ordinal exists to make safe.
        """
        return self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', row.store_id.id),
            ('res_model', '=', row._name),
            ('res_id', '=', row.id),
            ('state', 'in', MEDIA_JOB_OUTSTANDING_STATES),
        ], order='id desc', limit=1)

    @api.model
    def _resume_media_export(self, row):
        """Admit a fresh attempt at an image whose export stopped.

        Returns the admitted job, or an empty recordset when the row is
        not resumable -- in which case `resume_blocked_reason` carries the
        operator-facing explanation. When a previous attempt is still
        outstanding, returns THAT job unchanged: a resume coalesces on
        work already queued instead of racing it.

        The resume gets its OWN durable attempt identity by incrementing
        `resume_attempt`, which the payload hash includes. Nothing about
        the previous attempt is rewritten: its job keeps its
        `idempotency_key`, its logs, its mutation attempts, and the row
        keeps its checksum, its filename and whatever remote GID it had
        reached. A resume adds history; it never edits it.

        The ordinal is consumed ONLY when a new attempt is actually
        admitted. A refused resume and a coalesced one both leave it
        exactly where it was, so the attempt identities stay a faithful
        count of real attempts rather than of button presses.
        """
        row.ensure_one()
        preview = self._preview_for_row(row)
        if not preview:
            row.sudo().write({
                'resume_blocked_reason':
                    'No confirmed, in-progress export authorises a resume '
                    'of this image.',
            })
            return self.env['shopify.connector.job']
        blocker = self._media_resume_blocker(row)
        if blocker:
            row.sudo().write({'resume_blocked_reason': blocker})
            return self.env['shopify.connector.job']
        outstanding = self._outstanding_media_job(row)
        if outstanding:
            row.sudo().write({'resume_blocked_reason': False})
            _logger.info(
                'Media export resume for row %d coalesced on job %d, which '
                'is still outstanding.', row.id, outstanding.id,
            )
            return outstanding
        step_type = self.RESUME_ENTRY_STEP.get(
            row.remote_status, JOB_TYPE_MEDIA_STAGE,
        )
        row.sudo().write({
            'resume_attempt': row.resume_attempt + 1,
            'resume_blocked_reason': False,
        })
        row.invalidate_recordset()
        job = self._admit_media_job(
            preview.store_id, step_type, row,
            preview.remote_product_gid or False,
        )
        _logger.info(
            'Media export resumed for row %d at step %s (attempt %d).',
            row.id, step_type, row.resume_attempt,
        )
        return job

    @api.model
    def _row_for_job(self, job):
        row = self.env[
            'shopify.connector.product.media.binding'
        ].sudo().browse(job.res_id).exists()
        if not row:
            raise ValidationError(
                'This media-export job has no media-binding row.'
            )
        return row

    @api.model
    def _preview_for_row(self, row):
        preview = self.env[
            'shopify.connector.product.export.preview'
        ].sudo().search([
            ('store_id', '=', row.store_id.id),
            ('product_template_binding_id', '=',
             row.product_template_binding_id.id),
            ('state', '=', 'applying'),
        ], limit=1)
        return preview

    @api.model
    def _advance_media(self, row, from_step, next_step_type, completed=True):
        """Advance the export plan and chain the next media step.

        The plan holds ONE step per image — the `media_stage` entry the
        preview created — and the four jobs after it are that step's internal
        chain. So both the completion and the failure of any link resolve the
        SAME plan entry: `_advance_plan` is keyed on `JOB_TYPE_MEDIA_STAGE`
        regardless of which link called. Keying it on the calling job's own
        type would look right and silently do nothing, because
        `media_upload`/`media_file_create`/`media_associate` are not in the
        plan — leaving a failed image's plan entry pending forever.
        """
        del from_step
        Service = self.env['shopify.connector.product.export.service']
        preview = self._preview_for_row(row)
        if not preview:
            return False
        if not completed:
            return Service._advance_plan(preview, JOB_TYPE_MEDIA_STAGE, False)
        if next_step_type:
            self._admit_media_job(
                preview.store_id, next_step_type, row,
                preview.remote_product_gid or False,
            )
            return True
        # The associate step is the last link: only then is the plan entry
        # that started this chain complete.
        return Service._advance_plan(preview, JOB_TYPE_MEDIA_STAGE, True)

    # ------------------------------------------------------------------
    # Mutation domain: stagedUploadsCreate
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_media_stage(self, job):
        row = self._row_for_job(job)
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'row_id': row.id,
            'filename': row.connector_filename,
            'expected_connection_generation':
                job.expected_connection_generation,
            'expected_store_identity': job.store_id.shop_domain,
        }

    @api.model
    def _prepare_preconditions_media_stage(self, local_snapshot, owner_context):
        Service = self.env['shopify.connector.product.export.service']
        row = self.env[
            'shopify.connector.product.media.binding'
        ].sudo().browse(local_snapshot['row_id'])
        preview = self._preview_for_row(row)
        if not preview:
            Service._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'No confirmed, in-progress export authorises this media '
                'upload.',
            )
        # TD-013. `_preview_for_row` proves a preview is `applying`; it does
        # not prove the confirmation behind it is still valid. The media
        # families resolve their preview by row rather than by job, so they
        # never passed through `_assert_confirmed_preview_pre_c2` and were
        # the three mutation families with no expiry re-check at all.
        Service._assert_preview_unexpired_pre_c2(preview)
        settings = Service._settings(
            self.env['shopify.connector.store'].browse(
                local_snapshot['store_id']
            )
        )
        if not settings or settings.media_source_of_truth != 'odoo':
            Service._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'Media export requires this store to declare Odoo as the '
                'media source of truth.',
            )
        operation = (
            'mutation ProductExportMediaStage('
            '$input: [StagedUploadInput!]!) { '
            'stagedUploadsCreate(input: $input) { '
            'stagedTargets { url resourceUrl parameters { name value } } '
            'userErrors { field message } } }'
        )
        variables = {
            'input': [{
                'filename': local_snapshot['filename'],
                'mimeType': IMAGE_MIME_PNG,
                'resource': STAGED_RESOURCE,
                'httpMethod': 'POST',
            }],
        }
        return Service._mutation_request(
            JOB_TYPE_MEDIA_STAGE, self._as_export_snapshot(
                local_snapshot, preview,
            ),
            operation, variables,
            {'filename': local_snapshot['filename']},
            {'filename': local_snapshot['filename'],
             'checksum': row.odoo_image_checksum},
        )

    @api.model
    def _as_export_snapshot(self, local_snapshot, preview):
        """Adapt a media snapshot to the shared request builder's shape."""
        return dict(
            local_snapshot,
            preview_id=preview.id,
            remote_product_gid=preview.remote_product_gid or '',
            binding_id=preview.product_template_binding_id.id,
        )

    @api.model
    def _transport_media_stage(self, request, attempt_context):
        return self.env[
            'shopify.connector.product.export.service'
        ]._transport(request, attempt_context, 'stagedUploadsCreate')

    @api.model
    def _classify_direct_media_stage(self, result):
        def success(payload):
            targets = payload.get('stagedTargets')
            if not isinstance(targets, list) or len(targets) != 1:
                return 'expected exactly one staged target'
            target = targets[0]
            if not isinstance(target, dict):
                return 'malformed staged target'
            if not target.get('url') or not target.get('resourceUrl'):
                return 'staged target is missing url or resourceUrl'
            return True

        def evidence(payload):
            target = (payload.get('stagedTargets') or [{}])[0] or {}
            return {'staged_target': {
                'url': target.get('url'),
                'resourceUrl': target.get('resourceUrl'),
                'parameters': target.get('parameters') or [],
            }}

        return self.env[
            'shopify.connector.product.export.service'
        ]._classify_user_errors(
            result, success, 'Media staged upload', evidence,
        )

    @api.model
    def _reconcile_media_stage(self, attempt, reconciliation_job=None):
        """A staged upload target creates nothing in the store.

        There is no remote state to read back and no way for a lost
        acknowledgement to have changed the merchant's store, so the verdict
        is always `not_applied` — never an assumption that the previous
        target is usable, because staged targets expire and this attempt
        never received its parameters.

        The identity read is still performed rather than assumed. Returning
        `attempt.expected_store_identity` unread would report an identity
        this method never observed, which is the one thing a reconciliation
        verdict must not do: the whole point of the field is that the
        dispatcher can compare what was SEEN against what was expected.
        """
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportMediaStageIdentity { '
            'shop { myshopifyDomain } }'
        )
        with client.execute_business_read(
            reconciliation_job or attempt.job_id,
            attempt.store_id,
            query,
            {},
            purpose='product_export',
        ) as result:
            return self._reconcile_media_stage_result(attempt, result)

    @api.model
    def _reconcile_media_stage_result(self, attempt, result):
        identity = (
            ((result or {}).get('data') or {}).get('shop') or {}
        ).get('myshopifyDomain')
        if identity != attempt.expected_store_identity:
            return self.env[
                'shopify.connector.product.export.service'
            ]._reconcile_identity_mismatch(identity)
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_TEMPORARY,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'The staged-upload target was never received, so no '
                       'upload can follow it. No store state changed. A '
                       'reviewer releases a fresh media export.',
            'evidence': {},
        }

    @api.model
    def _apply_consequence_media_stage(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        row = self._row_for_job(job)
        if consequence['action'] != 'succeed':
            self._advance_media(row, JOB_TYPE_MEDIA_STAGE, None, False)
            return
        payload = (consequence.get('evidence') or {}).get('staged_target') or {}
        row.sudo().write({
            'staged_upload_url': payload.get('url'),
            'staged_resource_url': payload.get('resourceUrl'),
            'staged_upload_parameters': payload.get('parameters') or [],
        })
        self._advance_media(row, JOB_TYPE_MEDIA_STAGE, JOB_TYPE_MEDIA_UPLOAD)

    # ------------------------------------------------------------------
    # Plain HTTPS upload (no Shopify GraphQL call)
    # ------------------------------------------------------------------

    @api.model
    def _handle_product_export_media_upload(self, job):
        """Upload the bytes to the staged target.

        Not a Shopify mutation and not a change to any Shopify resource: the
        staged target is a write-once object-store key. Re-uploading the same
        bytes to the same key is idempotent by construction, which is why
        this step is replay-safe while every step around it is not.
        """
        row = self._row_for_job(job)
        if not row.staged_upload_url or not row.staged_resource_url:
            raise JobHandlerError(
                ERROR_CLASS_CONFIGURATION,
                'No staged upload target is recorded for this media row.',
            )
        if not row.staged_upload_url.lower().startswith('https://'):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'Refusing to upload to a non-HTTPS staged target.',
            )
        binary = self._binary_for_row(row)
        if binary is None:
            raise JobHandlerError(
                ERROR_CLASS_CONFIGURATION,
                'The Odoo image for this media row is no longer available.',
            )
        if image_checksum(binary) != row.odoo_image_checksum:
            # The image changed between preview and upload. Uploading the new
            # bytes under the old checksum's filename would make the registry
            # lie about what is on Shopify.
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'The Odoo image changed after it was previewed; nothing was '
                'uploaded. Re-preview the export.',
            )
        parameters = [
            (entry.get('name'), entry.get('value'))
            for entry in (row.staged_upload_parameters or [])
            if isinstance(entry, dict) and entry.get('name')
        ]
        try:
            response = requests.post(
                row.staged_upload_url,
                data=parameters,
                files={'file': (row.connector_filename, binary, IMAGE_MIME_PNG)},
                timeout=(
                    _UPLOAD_CONNECT_TIMEOUT_SECONDS,
                    _UPLOAD_READ_TIMEOUT_SECONDS,
                ),
            )
        except requests.exceptions.RequestException as exc:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The staged upload could not be completed; retry required.',
                type(exc).__name__,
            )
        status = getattr(response, 'status_code', None)
        if not isinstance(status, int) or status >= 300:
            raise JobHandlerError(
                ERROR_CLASS_TEMPORARY,
                'The staged upload was rejected by the upload target '
                '(HTTP %s).' % (status,),
            )
        row.sudo().write({'remote_status': 'uploaded'})
        self._advance_media(row, JOB_TYPE_MEDIA_UPLOAD,
                            JOB_TYPE_MEDIA_FILE_CREATE)

    @api.model
    def _binary_for_row(self, row):
        if row.media_role == 'variant':
            variant = row.product_variant_binding_id.product_variant_id
            return self._decoded_image(variant, 'image_variant_1920')
        template = row.product_template_binding_id.product_template_id
        return self._decoded_image(template, 'image_1920')

    # ------------------------------------------------------------------
    # Mutation domain: fileCreate
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_media_file_create(self, job):
        return self._prepare_local_media_stage(job)

    @api.model
    def _prepare_preconditions_media_file_create(
        self, local_snapshot, owner_context,
    ):
        Service = self.env['shopify.connector.product.export.service']
        row = self.env[
            'shopify.connector.product.media.binding'
        ].sudo().browse(local_snapshot['row_id'])
        preview = self._preview_for_row(row)
        if not preview:
            Service._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'No confirmed, in-progress export authorises this file '
                'creation.',
            )
        Service._assert_preview_unexpired_pre_c2(preview)  # TD-013
        if row.remote_status != 'uploaded' or not row.staged_resource_url:
            Service._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'The image has not been uploaded to a staged target yet.',
            )
        operation = (
            'mutation ProductExportMediaFileCreate('
            '$files: [FileCreateInput!]!) { '
            'fileCreate(files: $files) { '
            'files { id fileStatus alt } '
            'userErrors { code field message } } }'
        )
        variables = {
            'files': [{
                'originalSource': row.staged_resource_url,
                'contentType': MEDIA_CONTENT_TYPE,
                'filename': row.connector_filename,
                'alt': row.product_template_binding_id.product_template_id.name
                       or '',
            }],
        }
        return Service._mutation_request(
            JOB_TYPE_MEDIA_FILE_CREATE,
            self._as_export_snapshot(local_snapshot, preview),
            operation, variables,
            {'filename': row.connector_filename,
             'checksum': row.odoo_image_checksum},
            {'filename': row.connector_filename,
             'checksum': row.odoo_image_checksum,
             'api_version': SHOPIFY_API_VERSION},
        )

    @api.model
    def _transport_media_file_create(self, request, attempt_context):
        return self.env[
            'shopify.connector.product.export.service'
        ]._transport(request, attempt_context, 'fileCreate')

    @api.model
    def _classify_direct_media_file_create(self, result):
        def success(payload):
            files = payload.get('files')
            if not isinstance(files, list) or len(files) != 1:
                return 'expected exactly one created file'
            created = files[0]
            if not isinstance(created, dict) or not created.get('id'):
                return 'created file has no id'
            return True

        return self.env[
            'shopify.connector.product.export.service'
        ]._classify_user_errors(
            result, success, 'Media fileCreate',
            lambda payload: {'file': (payload.get('files') or [{}])[0]},
        )

    @api.model
    def _reconcile_media_file_create(self, attempt, reconciliation_job=None):
        """Verification read by the connector's own filename.

        The deterministic filename is the only durable handle on a File whose
        creation acknowledgement was lost, and it is why this module can
        adopt instead of re-uploading — a re-upload would leave two Files
        neither of which it could later tell apart.
        """
        store = attempt.store_id
        snapshot = attempt.preconditions_snapshot or {}
        filename = snapshot.get('filename')
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportMediaFind($query: String!) { '
            'files(first: 5, query: $query) { nodes { id fileStatus '
            '... on MediaImage { image { url } } } } '
            'shop { myshopifyDomain } }'
        )
        # Connector-generated and deterministic today (`odoo-<id>-<checksum>`),
        # so this is not a live defect -- it is the same missing encoding as
        # the SKU gate, and it goes through the same helper so it cannot
        # become one if the filename scheme ever admits a wider charset.
        with client.execute_business_read(
            reconciliation_job or attempt.job_id,
            store,
            query,
            {'query': search_term('filename', filename)},
            purpose='product_export',
        ) as result:
            return self._reconcile_media_file_create_result(attempt, result)

    @api.model
    def _reconcile_media_file_create_result(self, attempt, result):
        data = (result or {}).get('data') or {}
        identity = (data.get('shop') or {}).get('myshopifyDomain')
        if identity != attempt.expected_store_identity:
            return self.env[
                'shopify.connector.product.export.service'
            ]._reconcile_identity_mismatch(identity)
        nodes = ((data.get('files') or {}).get('nodes')) or []
        if len(nodes) == 1:
            return {
                'verdict': 'applied',
                'observed_store_identity': identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'The File this attempt uploaded exists; adopting '
                           'it rather than uploading a second copy.',
                'evidence': {'file': nodes[0]},
            }
        if len(nodes) > 1:
            return {
                'verdict': 'not_applied',
                'observed_store_identity': identity,
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_VALIDATION,
                'manual_review_subreason': SUBREASON_DUPLICATE,
                'message': 'More than one File carries this connector '
                           'filename. A reviewer resolves it; this connector '
                           'will not choose, and will not delete either.',
                'evidence': {'file_ids': [node.get('id') for node in nodes]},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_VALIDATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'No File carries this connector filename; the upload '
                       'did not apply.',
            'evidence': {},
        }

    @api.model
    def _apply_consequence_media_file_create(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        row = self._row_for_job(job)
        if consequence['action'] != 'succeed':
            self._advance_media(row, JOB_TYPE_MEDIA_FILE_CREATE, None, False)
            return
        created = (consequence.get('evidence') or {}).get('file') or {}
        file_gid = created.get('id')
        if not file_gid:
            self._advance_media(row, JOB_TYPE_MEDIA_FILE_CREATE, None, False)
            return
        status = (created.get('fileStatus') or '').upper()
        row.sudo().write({
            'shopify_gid': file_gid,
            'remote_status': 'ready' if status == 'READY' else 'processing',
            'exported_at': fields.Datetime.now(),
        })
        row.invalidate_recordset()
        if row.remote_status == 'ready':
            # Already READY: the poll has nothing to wait for, so the
            # association is enqueued directly. The gate is "READY before
            # associate", not "always poll first".
            self._advance_media(
                row, JOB_TYPE_MEDIA_FILE_CREATE, JOB_TYPE_MEDIA_ASSOCIATE,
            )
        else:
            self._advance_media(
                row, JOB_TYPE_MEDIA_FILE_CREATE, JOB_TYPE_MEDIA_POLL,
            )

    # ------------------------------------------------------------------
    # READY poll (read-only)
    # ------------------------------------------------------------------

    @api.model
    def _handle_product_export_media_poll(self, job):
        row = self._row_for_job(job)
        if row.remote_status in ('associated', 'failed'):
            return
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportMediaStatus($id: ID!) { '
            'node(id: $id) { id ... on MediaImage { fileStatus '
            'fileErrors { code details message } } } '
            'shop { myshopifyDomain } }'
        )
        with client.execute_business_read(
            job,
            job.store_id,
            query,
            {'id': row.shopify_gid},
            purpose='product_export',
        ) as result:
            return self._apply_media_poll_result(job, row, result)

    @api.model
    def _apply_media_poll_result(self, job, row, result):
        data = (result or {}).get('data') or {}
        if (data.get('shop') or {}).get(
            'myshopifyDomain'
        ) != job.store_id.shop_domain:
            raise JobHandlerError(
                'store_identity_mismatch',
                'The media status read observed a different Shopify store '
                'identity.',
            )
        node = data.get('node')
        if not isinstance(node, dict):
            raise JobHandlerError(
                ERROR_CLASS_DATA_SHAPE,
                'The media status read returned no File for this GID.',
            )
        status = (node.get('fileStatus') or '').upper()
        if status == 'READY':
            row.sudo().write({
                'remote_status': 'ready',
                'last_verified_at': fields.Datetime.now(),
            })
            self._advance_media(row, JOB_TYPE_MEDIA_POLL,
                                JOB_TYPE_MEDIA_ASSOCIATE)
            return
        if status == 'FAILED':
            errors = node.get('fileErrors') or []
            row.sudo().write({
                'remote_status': 'failed',
                'remote_failure_note': str(
                    [(entry or {}).get('code') for entry in errors]
                )[:500],
            })
            self._advance_media(row, JOB_TYPE_MEDIA_POLL, None, False)
            job._transition_blocked_manual_review(
                ERROR_CLASS_VALIDATION, SUBREASON_BINDING_CONFLICT,
                'Shopify could not process this image. Nothing was '
                'associated to the product.',
            )
            return
        row.sudo().write({
            'remote_status': 'processing',
            'last_verified_at': fields.Datetime.now(),
        })
        # Still processing: the cron re-enqueues. No association is submitted,
        # which is the entire point of the gate.
        self.env['shopify.connector.job.log']._system_append(
            job, 'attempt',
            'Media File is %s; association withheld until READY.' % (
                status or 'in an unreported state',
            ),
        )

    @api.model
    def run_media_status_poll(self):
        """Cron: enqueue one poll job per non-terminal media row."""
        if not self.env.su and not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may start the media '
                'status poll outside the root cron environment.'
            )
        MediaBinding = self.env['shopify.connector.product.media.binding']
        Service = self.env['shopify.connector.product.export.service']
        rows = MediaBinding.sudo().search([
            ('remote_status', 'in', list(('uploaded', 'processing'))),
        ])
        enqueued = 0
        for row in rows:
            if row.store_id.state != 'connected':
                continue
            settings = Service._settings(row.store_id)
            if not settings or not settings.product_export_domain_enabled:
                continue
            try:
                Service._enqueue(
                    row.store_id, JOB_TYPE_MEDIA_POLL, 'scheduled_sync',
                    row._name, row.id,
                    payload_hash=uuid.uuid4().hex,
                )
                enqueued += 1
            except Exception:
                _logger.exception(
                    'Could not enqueue a media status poll for media '
                    'binding %d.', row.id,
                )
        return enqueued

    # ------------------------------------------------------------------
    # Mutation domain: fileUpdate(referencesToAdd) — the only association
    # ------------------------------------------------------------------

    @api.model
    def _prepare_local_media_associate(self, job):
        return self._prepare_local_media_stage(job)

    @api.model
    def _prepare_preconditions_media_associate(
        self, local_snapshot, owner_context,
    ):
        Service = self.env['shopify.connector.product.export.service']
        row = self.env[
            'shopify.connector.product.media.binding'
        ].sudo().browse(local_snapshot['row_id'])
        preview = self._preview_for_row(row)
        if not preview:
            Service._fail_closed_pre_c2(
                ERROR_CLASS_DESTRUCTIVE, SUBREASON_DESTRUCTIVE,
                'No confirmed, in-progress export authorises this media '
                'association.',
            )
        Service._assert_preview_unexpired_pre_c2(preview)  # TD-013
        # THE gate. Checked here, immediately before the request is built,
        # under the fresh pre-C2 read of local state that the poll wrote.
        if row.remote_status != 'ready':
            Service._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'This File is not READY. No association may be submitted '
                'before Shopify reports READY.',
            )
        if not row.shopify_gid or row.shopify_gid.startswith('pending:'):
            Service._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'This media row has no Shopify File GID to associate.',
            )
        if not preview.remote_product_gid:
            Service._fail_closed_pre_c2(
                ERROR_CLASS_CONFIGURATION, SUBREASON_BINDING_CONFLICT,
                'There is no bound Shopify product to associate media with.',
            )
        operation = (
            'mutation ProductExportMediaAssociate('
            '$files: [FileUpdateInput!]!) { '
            'fileUpdate(files: $files) { '
            'files { id fileStatus alt } '
            'userErrors { code field message } } }'
        )
        variables = {
            'files': [{
                'id': row.shopify_gid,
                # referencesToAdd ONLY. `referencesToRemove` is never sent by
                # this module: removing a reference is a detach, and this
                # pipeline is append-only.
                'referencesToAdd': [preview.remote_product_gid],
            }],
        }
        return Service._mutation_request(
            JOB_TYPE_MEDIA_ASSOCIATE,
            self._as_export_snapshot(local_snapshot, preview),
            operation, variables,
            {'file_gid': row.shopify_gid,
             'product_gid': preview.remote_product_gid},
            {'file_gid': row.shopify_gid,
             'product_gid': preview.remote_product_gid,
             'checksum': row.odoo_image_checksum},
        )

    @api.model
    def _transport_media_associate(self, request, attempt_context):
        return self.env[
            'shopify.connector.product.export.service'
        ]._transport(request, attempt_context, 'fileUpdate')

    @api.model
    def _classify_direct_media_associate(self, result):
        def success(payload):
            files = payload.get('files')
            if not isinstance(files, list) or len(files) != 1:
                return 'expected exactly one updated file'
            if not (files[0] or {}).get('id'):
                return 'updated file has no id'
            return True

        return self.env[
            'shopify.connector.product.export.service'
        ]._classify_user_errors(
            result, success, 'Media association',
            lambda payload: {
                'product_media_gid': (
                    (payload.get('files') or [{}])[0] or {}
                ).get('id'),
            },
        )

    @api.model
    def _reconcile_media_associate(self, attempt, reconciliation_job=None):
        """Read the product's media and look for this exact File GID."""
        store = attempt.store_id
        snapshot = attempt.preconditions_snapshot or {}
        client = self.env['shopify.connector.api.client']
        query = (
            'query ProductExportMediaAssociated($id: ID!) { '
            'product(id: $id) { id media(first: 50) { nodes { id '
            '... on MediaImage { id fileStatus } } } } '
            'shop { myshopifyDomain } }'
        )
        with client.execute_business_read(
            reconciliation_job or attempt.job_id,
            store,
            query,
            {'id': snapshot.get('product_gid')},
            purpose='product_export',
        ) as result:
            return self._reconcile_media_associate_result(attempt, result)

    @api.model
    def _reconcile_media_associate_result(self, attempt, result):
        data = (result or {}).get('data') or {}
        identity = (data.get('shop') or {}).get('myshopifyDomain')
        Service = self.env['shopify.connector.product.export.service']
        if identity != attempt.expected_store_identity:
            return Service._reconcile_identity_mismatch(identity)
        product = data.get('product')
        if not isinstance(product, dict):
            return {
                'verdict': 'not_applied',
                'observed_store_identity': identity or '',
                'action': 'block_manual_review',
                'error_class': ERROR_CLASS_BINDING_CONFLICT,
                'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
                'message': 'The bound product could not be read during media '
                           'reconciliation.',
                'evidence': {},
            }
        gids = {
            (node or {}).get('id')
            for node in ((product.get('media') or {}).get('nodes')) or []
        }
        if snapshot.get('file_gid') in gids:
            return {
                'verdict': 'applied',
                'observed_store_identity': identity,
                'action': 'succeed',
                'error_class': False,
                'manual_review_subreason': False,
                'message': 'The File is associated with the product.',
                'evidence': {'product_media_gid': snapshot.get('file_gid')},
            }
        return {
            'verdict': 'not_applied',
            'observed_store_identity': identity,
            'action': 'block_manual_review',
            'error_class': ERROR_CLASS_VALIDATION,
            'manual_review_subreason': SUBREASON_BINDING_CONFLICT,
            'message': 'The File is not associated with the product; the '
                       'association did not apply.',
            'evidence': {},
        }

    @api.model
    def _apply_consequence_media_associate(
        self, job, attempt, phase, consequence, reconciliation_job=False,
    ):
        row = self._row_for_job(job)
        if consequence['action'] != 'succeed':
            self._advance_media(row, JOB_TYPE_MEDIA_ASSOCIATE, None, False)
            return
        row.sudo().write({
            'remote_status': 'associated',
            'shopify_product_media_gid': (
                (consequence.get('evidence') or {}).get('product_media_gid')
                or row.shopify_gid
            ),
            'last_verified_at': fields.Datetime.now(),
        })
        self._flag_superseded_rows(row)
        self._advance_media(row, JOB_TYPE_MEDIA_ASSOCIATE, None, True)

    @api.model
    def _flag_superseded_rows(self, row):
        """Flag older rows for the same role — retain, never delete.

        This is the honest bookkeeping of an append-only design: the older
        File and its association stay on the product, and the flag is the
        queue a future explicit cleanup capability would work from. Nothing
        automatic ever acts on it.
        """
        MediaBinding = self.env['shopify.connector.product.media.binding']
        domain = [
            ('id', '!=', row.id),
            ('store_id', '=', row.store_id.id),
            ('product_template_binding_id', '=',
             row.product_template_binding_id.id),
            ('media_role', '=', row.media_role),
            ('product_variant_binding_id', '=',
             row.product_variant_binding_id.id
             if row.product_variant_binding_id else False),
            ('orphan_cleanup_candidate', '=', False),
        ]
        older = MediaBinding.sudo().search(domain)
        if older:
            older.sudo().write({'orphan_cleanup_candidate': True})
