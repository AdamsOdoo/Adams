"""Registration seams: job types, dispatch strategies, settings, readiness.

Every extension here is classic Odoo `_inherit` with an add-only merge onto
what `super()` returned. No core file is edited by this module.
"""

import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)

from .shopify_connector_export_reconnect import (
    JOB_TYPE_RECONNECT_RECONCILE,
)
from .shopify_connector_media_export_service import (
    JOB_TYPE_MEDIA_ASSOCIATE,
    JOB_TYPE_MEDIA_FILE_CREATE,
    JOB_TYPE_MEDIA_POLL,
    JOB_TYPE_MEDIA_STAGE,
    JOB_TYPE_MEDIA_UPLOAD,
)
from .shopify_connector_product_export_service import (
    ExportPreC2FailClosedError,
    JOB_TYPE_APPLY,
    JOB_TYPE_BINDING_NAMESPACE,
    JOB_TYPE_CREATE,
    JOB_TYPE_MUTATION_RECONCILE,
    JOB_TYPE_PREVIEW,
    JOB_TYPE_UPDATE,
    JOB_TYPE_VARIANTS_CREATE,
    JOB_TYPE_VARIANTS_UPDATE,
)

EXPORT_JOB_TYPES = (
    JOB_TYPE_PREVIEW,
    JOB_TYPE_APPLY,
    JOB_TYPE_BINDING_NAMESPACE,
    JOB_TYPE_CREATE,
    JOB_TYPE_UPDATE,
    JOB_TYPE_VARIANTS_UPDATE,
    JOB_TYPE_VARIANTS_CREATE,
    JOB_TYPE_MEDIA_STAGE,
    JOB_TYPE_MEDIA_UPLOAD,
    JOB_TYPE_MEDIA_FILE_CREATE,
    JOB_TYPE_MEDIA_POLL,
    JOB_TYPE_MEDIA_ASSOCIATE,
    JOB_TYPE_MUTATION_RECONCILE,
    JOB_TYPE_RECONNECT_RECONCILE,
)

JOB_TYPE_LABELS = {
    JOB_TYPE_PREVIEW: 'Product Export Preview',
    JOB_TYPE_APPLY: 'Product Export Apply',
    JOB_TYPE_BINDING_NAMESPACE: 'Product Export Binding Namespace',
    JOB_TYPE_CREATE: 'Product Export Create',
    JOB_TYPE_UPDATE: 'Product Export Update',
    JOB_TYPE_VARIANTS_UPDATE: 'Product Export Variants Update',
    JOB_TYPE_VARIANTS_CREATE: 'Product Export Variants Create',
    JOB_TYPE_MEDIA_STAGE: 'Product Export Media Stage',
    JOB_TYPE_MEDIA_UPLOAD: 'Product Export Media Upload',
    JOB_TYPE_MEDIA_FILE_CREATE: 'Product Export Media File Create',
    JOB_TYPE_MEDIA_POLL: 'Product Export Media Poll',
    JOB_TYPE_MEDIA_ASSOCIATE: 'Product Export Media Associate',
    JOB_TYPE_MUTATION_RECONCILE: 'Product Export Mutation Reconciliation',
    JOB_TYPE_RECONNECT_RECONCILE: 'Product Export Reconnect Reconciliation',
}

# The scopes this domain genuinely needs, and no more.
#
# `write_products` — productSet / productUpdate / productVariantsBulk*.
# `write_files`    — fileCreate AND fileUpdate. `fileCreate` alone would
#                    accept the narrower `write_images`, but `fileUpdate` (the
#                    only 2026-07 mutation that attaches an EXISTING File to
#                    a product, and therefore the only READY-gated
#                    association path) accepts `write_files` or
#                    `write_themes` and not `write_images`.
# `write_themes`   — NEVER requested. It would grant theme write access this
#                    connector has no use for.
REQUIRED_EXPORT_SCOPES = ('write_products',)
REQUIRED_MEDIA_SCOPES = ('write_files',)
FORBIDDEN_SCOPES = ('write_themes',)


# ======================================================================
# Seam 1: shopify.connector.job — job_type registration.
# ======================================================================
class ShopifyConnectorJobProductExportExtension(models.Model):
    _inherit = 'shopify.connector.job'

    job_type = fields.Selection(
        selection_add=[
            (value, JOB_TYPE_LABELS[value]) for value in EXPORT_JOB_TYPES
        ],
        # LC-1 / DEC-030 from the start: a supported uninstall retypes these
        # rows to the permanent core sink instead of losing them, so no
        # retrofit migration is ever needed.
        ondelete={
            value: (lambda recs: recs._reassign_to_historic_job_type())
            for value in EXPORT_JOB_TYPES
        },
    )

    @api.model
    def _domain_flag_for_job_type(self, job_type):
        if job_type in EXPORT_JOB_TYPES:
            return 'product_export_domain_enabled'
        return super()._domain_flag_for_job_type(job_type)


# ======================================================================
# Seam 2: shopify.connector.store.settings — the domain flags.
# ======================================================================
class ShopifyConnectorStoreSettingsProductExport(models.Model):
    _inherit = 'shopify.connector.store.settings'

    # D-015-8: export is opt-in even inside the Full edition. Default False,
    # so installing this module changes nothing about a running store until
    # somebody decides otherwise.
    product_export_domain_enabled = fields.Boolean(default=False)
    # Read-only marker: the connector-owned binding-metafield definition
    # exists on this store. The create path stays closed until it does,
    # because `identifier.customId` cannot resolve without it.
    product_export_binding_namespace_ready = fields.Boolean(
        default=False,
        readonly=True,
    )
    # D-015B-7: no default on purpose. A store with both media import and
    # media export enabled and no declared direction would ping-pong images
    # forever, so the direction must be stated before the first media export
    # rather than inherited from a guess.
    media_source_of_truth = fields.Selection(
        selection=[
            ('odoo', 'Odoo'),
            ('shopify', 'Shopify'),
        ],
        help='Which system owns product images. Media export runs only under '
             '"odoo"; the Task 010B image refresh runs only under "shopify". '
             'Unset blocks media export rather than choosing for you.',
    )


# ======================================================================
# Seam 3: product.template — the per-template opt-in and the connector-owned
# export fields.
#
# These are connector-owned rather than derived from existing Odoo fields on
# purpose. Odoo has no field that means "Shopify vendor" or "Shopify product
# type", and inferring one (from a supplier record, say) would export a guess
# about the merchant's catalog taxonomy. An explicit, empty-by-default field
# exports nothing until somebody fills it in.
# ======================================================================
class ProductTemplateProductExport(models.Model):
    _inherit = 'product.template'

    shopify_export_enabled = fields.Boolean(
        string='Export to Shopify',
        default=False,
        help='When set, this product may be previewed and exported to '
             'Shopify. Export still requires a reviewed, confirmed preview '
             'for every change.',
    )
    shopify_export_status = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('active', 'Active'),
            ('archived', 'Archived'),
        ],
        default='draft',
        string='Shopify Status',
        help='The Shopify product status to export. New products are created '
             'DRAFT so they are not customer-visible before anyone intends '
             'them to be. Publication is a separate, explicit action and is '
             'never a side effect of export.',
    )
    shopify_export_vendor = fields.Char(string='Shopify Vendor')
    shopify_export_product_type = fields.Char(string='Shopify Product Type')
    shopify_export_tags = fields.Char(
        string='Shopify Tags',
        help='Comma-separated. Exported as the complete Shopify tag list for '
             'this product.',
    )

    def action_shopify_export_preview(self):
        """Request a fresh export preview for every enabled store.

        A display-and-delegate action: it resolves the stores this product
        can be exported to and hands each one to the service, which owns the
        permission check and every guard.
        """
        self.ensure_one()
        Store = self.env['shopify.connector.store']
        Service = self.env['shopify.connector.product.export.service']
        stores = Store.search([('state', '=', 'connected')])
        eligible = stores.filtered(
            lambda store: (
                store.company_id == self.company_id
                or not self.company_id
            )
        )
        if not eligible:
            raise UserError(
                'No connected Shopify store in this product\'s company is '
                'available for export.'
            )
        jobs = self.env['shopify.connector.job']
        for store in eligible:
            settings = Service._settings(store)
            if not settings or not settings.product_export_domain_enabled:
                continue
            jobs |= Service.enqueue_preview(self, store)
        if not jobs:
            raise UserError(
                'Product export is not enabled on any connected Shopify '
                'store for this company.'
            )
        return True


# ======================================================================
# Seam 4: shopify.connector.readiness.check — the export scope checks.
# ======================================================================
class ShopifyConnectorReadinessCheckProductExport(models.AbstractModel):
    _inherit = 'shopify.connector.readiness.check'

    @api.model
    def _get_checks(self, store):
        checks = super()._get_checks(store)
        checks.append(self._check_product_export_scopes(store))
        return checks

    @api.model
    def _accepted_domain_flags(self):
        """Register `product_export_domain_enabled` (independent review,
        Defect #3). Core's `_check_domain_flag_enablement` must recognize a
        store enabling only Catalog export as having a sync domain enabled
        -- an accepted, first-class DEC-003 direction offered at S1 step 7
        -- without this module editing a fixed core tuple."""
        return super()._accepted_domain_flags() + (
            'product_export_domain_enabled',
        )

    @api.model
    def _governed_scope_catalog(self):
        """Add Product Export's own unconditional scope to the S1 step 4
        display list. `write_files` is deliberately NOT added here: it is
        conditional on `media_source_of_truth`, a Store Settings choice S1
        never makes, so listing it unconditionally at step 4 would name a
        scope this specific store might not need."""
        catalog = super()._governed_scope_catalog()
        catalog.append({
            'scope': 'write_products',
            'reason': _(
                'so product changes made in Odoo can be exported to '
                'Shopify'
            ),
        })
        return catalog

    @api.model
    def _check_product_export_scopes(self, store):
        """Pure read-only evaluation — no write, create, unlink or sudo.

        Not applicable (and therefore passing) while the export domain is
        off, so installing the module cannot turn a healthy store red.
        """
        code = 'product_export_scopes'
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings or not settings.product_export_domain_enabled:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_PASS,
                'Not applicable — product export is not enabled for this '
                'store.',
            )
        try:
            scopes = json.loads(store.granted_scopes or '[]')
        except (TypeError, ValueError):
            scopes = []
        if not isinstance(scopes, list):
            scopes = []
        forbidden = [scope for scope in FORBIDDEN_SCOPES if scope in scopes]
        if forbidden:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'The granted scopes include %s, which this connector never '
                'requests and does not need. Re-issue the credential with '
                'least privilege.' % ', '.join(forbidden),
            )
        missing = [
            scope for scope in REQUIRED_EXPORT_SCOPES if scope not in scopes
        ]
        if missing:
            return self._check_result(
                code, self.ESSENTIAL, self.RESULT_FAIL,
                'Product export needs %s in the granted scopes snapshot.'
                % ', '.join(missing),
            )
        if settings.media_source_of_truth == 'odoo':
            media_missing = [
                scope for scope in REQUIRED_MEDIA_SCOPES
                if scope not in scopes
            ]
            if media_missing:
                return self._check_result(
                    code, self.ESSENTIAL, self.RESULT_FAIL,
                    'Media export needs %s in the granted scopes snapshot '
                    '(fileUpdate does not accept write_images).'
                    % ', '.join(media_missing),
                )
        return self._check_result(
            code, self.ESSENTIAL, self.RESULT_PASS,
            'The least-privilege export scopes are granted and no '
            'unnecessary write scope is present.',
        )


# ======================================================================
# Seam 5: shopify.connector.job.dispatch — handlers, replay policies and the
# seven mutation-domain strategies.
# ======================================================================
class ShopifyConnectorJobDispatchProductExport(models.AbstractModel):
    _inherit = 'shopify.connector.job.dispatch'

    @api.model
    def _get_handlers(self):
        handlers = dict(super()._get_handlers())
        Service = self.env['shopify.connector.product.export.service']
        Media = self.env['shopify.connector.media.export.service']
        handlers.update({
            JOB_TYPE_PREVIEW: Service._handle_product_export_preview,
            JOB_TYPE_APPLY: Service._handle_product_export_apply,
            JOB_TYPE_MUTATION_RECONCILE:
                Service._handle_product_export_mutation_reconcile,
            JOB_TYPE_MEDIA_UPLOAD: Media._handle_product_export_media_upload,
            JOB_TYPE_MEDIA_POLL: Media._handle_product_export_media_poll,
            JOB_TYPE_RECONNECT_RECONCILE: self.env[
                'shopify.connector.export.reconcile.service'
            ]._handle_product_export_reconnect_reconcile,
        })
        return handlers

    @api.model
    def _get_replay_policies(self):
        policies = dict(super()._get_replay_policies())
        policies.update({
            JOB_TYPE_PREVIEW: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_APPLY: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_MUTATION_RECONCILE:
                REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_MEDIA_POLL: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            # PD-PX-7 (TD-015). The pass issues one narrow product READ
            # and writes only local verdicts, so replaying it converges
            # rather than repeating a remote effect.
            JOB_TYPE_RECONNECT_RECONCILE:
                REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            # The staged upload writes to a write-once object-store key with
            # the same bytes, so a replay converges rather than duplicating.
            # Every genuine Shopify mutation below is NOT replay-safe.
            JOB_TYPE_MEDIA_UPLOAD: REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            JOB_TYPE_BINDING_NAMESPACE:
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_CREATE: REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_UPDATE: REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_VARIANTS_UPDATE:
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_VARIANTS_CREATE:
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_MEDIA_STAGE:
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_MEDIA_FILE_CREATE:
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
            JOB_TYPE_MEDIA_ASSOCIATE:
                REPLAY_POLICY_REMOTE_EFFECT_NOT_REPLAY_SAFE,
        })
        return policies

    @api.model
    def _get_reconciliation_strategies(self):
        strategies = dict(super()._get_reconciliation_strategies())
        Service = self.env['shopify.connector.product.export.service']
        Media = self.env['shopify.connector.media.export.service']
        for domain, owner, suffix in (
            (JOB_TYPE_BINDING_NAMESPACE, Service, 'binding_namespace'),
            (JOB_TYPE_CREATE, Service, 'create'),
            (JOB_TYPE_UPDATE, Service, 'update'),
            (JOB_TYPE_VARIANTS_UPDATE, Service, 'variants_update'),
            (JOB_TYPE_VARIANTS_CREATE, Service, 'variants_create'),
            (JOB_TYPE_MEDIA_STAGE, Media, 'media_stage'),
            (JOB_TYPE_MEDIA_FILE_CREATE, Media, 'media_file_create'),
            (JOB_TYPE_MEDIA_ASSOCIATE, Media, 'media_associate'),
        ):
            strategies[domain] = {
                'reconciliation_job_type': JOB_TYPE_MUTATION_RECONCILE,
                'prepare_local': getattr(owner, '_prepare_local_%s' % suffix),
                'prepare_preconditions': getattr(
                    owner, '_prepare_preconditions_%s' % suffix,
                ),
                'transport': getattr(owner, '_transport_%s' % suffix),
                'classify_direct_result': getattr(
                    owner, '_classify_direct_%s' % suffix,
                ),
                'reconcile': getattr(owner, '_reconcile_%s' % suffix),
                'apply_consequence': getattr(
                    owner, '_apply_consequence_%s' % suffix,
                ),
            }
        return strategies

    @api.model
    def _recover_pre_c2_failure(self, job_id, token, exc):
        """Domain pre-C2 recovery seam (the Task 013 precedent).

        Only `ExportPreC2FailClosedError` is handled here, and only after
        core's own rollback/reset has already happened, so the disposition is
        applied in a clean transaction. Everything else delegates to
        `super()` unchanged — a genuine transport or precondition failure
        must keep its generic bounded-retry behaviour.
        """
        if not isinstance(exc, ExportPreC2FailClosedError):
            return super()._recover_pre_c2_failure(job_id, token, exc)
        self.env.cr.rollback()
        job = self.env['shopify.connector.job'].browse(job_id).exists()
        if not job:
            self.env.cr.commit()
            return
        job = job.try_lock_for_update()
        if not job:
            self.env.cr.commit()
            return
        job.invalidate_recordset()
        if job.state == 'running' and job.current_attempt_token == token:
            self._block_original_job(
                job, exc.error_class, exc.subreason, exc.message,
            )
        self.env.cr.commit()


# ======================================================================
# Seam 6: shopify.connector.store — the reconnect export block (PD-PX-7).
#
# TD-015 moved this to `shopify_connector_export_reconnect.py`, where the
# pass PD-PX-7 actually specifies now lives. What stood here expired every
# open preview on demand and called that the reconciliation. Expiring the
# previews is necessary — a confirmation taken before a reconnect must not
# authorise a mutation after it — but it re-read nothing, so a store could
# be reconnected to a different Shopify store, or after products had been
# deleted, and resume exporting against bindings it had never verified.
# ======================================================================
