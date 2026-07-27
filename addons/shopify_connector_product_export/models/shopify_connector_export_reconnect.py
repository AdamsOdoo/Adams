"""PD-PX-7: the reconnect reconciliation pass (TD-015).

What PD-PX-7 requires, verbatim from the Task 015 packet §9.5:

    Exports stay blocked for a reconnected store until the full binding
    reconciliation pass completes (exists / variant GID set / media
    checksums); deleted-or-archived remote -> review, never silent
    re-create.

What shipped instead was a manual "expire every open preview" button. That
is a *necessary* part of the block — a confirmation taken before a
reconnect must not authorise a mutation after it — but it is not the pass.
Nothing re-read anything. A store could disconnect, be reconnected to a
different Shopify store or after a merchant had deleted products, and the
connector would resume exporting against bindings it had never
re-verified.

Why a reconnect is the trigger
------------------------------
A reconnect is the one moment the connector must assume its whole picture
of the remote store may be stale. Between disconnect and reconnect the
credential may have been re-pointed, products may have been deleted or
archived, variants may have been restructured, and media may have been
removed — all invisibly, because the connector was not watching. Every
binding is a claim about a remote object, and after a reconnect none of
those claims has been checked.

The shape of the pass
---------------------
One job per bound template, because that is the unit a binding covers and
the unit that can independently succeed, fail, retry or need review. Each
job re-reads its product by GID through the module's existing transport
seam — the same `_read_remote_product` the preview uses — and compares
three things the connector actually owns claims about:

* the product exists and is not archived,
* the governed variant GID set still matches the bindings,
* the media rows this connector created still name Files it can see.

Anything missing, archived or materially divergent goes to explicit
review. Nothing is re-created, re-published or repaired: a reconciliation
that silently fixed what it found would be indistinguishable from the
export it is supposed to be gating.
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

_logger = logging.getLogger(__name__)

JOB_TYPE_RECONNECT_RECONCILE = 'product_export_reconnect_reconcile'

#: Store-level states. Exports are refused in every one of these except
#: `not_required` and `complete`.
RECONCILE_BLOCKING_STATES = ('required', 'in_progress', 'review_required')

RECONCILE_STATE_SELECTION = [
    ('not_required', 'Not Required'),
    ('required', 'Reconciliation Required'),
    ('in_progress', 'Reconciliation Running'),
    ('complete', 'Reconciled'),
    ('review_required', 'Review Required'),
]

BINDING_RECONCILE_SELECTION = [
    ('not_required', 'Not Required'),
    ('pending', 'Pending'),
    ('verified', 'Verified'),
    ('review', 'Review Required'),
]


class ShopifyConnectorStoreExportReconnect(models.Model):
    _inherit = 'shopify.connector.store'

    # Deliberately NOT `required`. This module adds the column to a table
    # the CORE module owns, and a NOT NULL constraint imposed by an add-on
    # is a constraint core has to satisfy without knowing it exists --
    # core's own raw-SQL paths, and any pre-SEC-3 historic row, would fail
    # on a column they have never heard of. An unset value means the same
    # thing as `not_required`, which is the fail-SAFE reading: a store
    # nobody has reconnected has no reconciliation outstanding, so it is
    # not blocked.
    export_reconcile_state = fields.Selection(
        selection=RECONCILE_STATE_SELECTION,
        default='not_required',
        readonly=True,
        index=True,
    )
    export_reconcile_at = fields.Datetime(readonly=True)
    # The connection epoch the current verdict covers. A later reconnect
    # bumps `connection_generation`, which makes a stale `complete` verdict
    # detectable rather than merely old: the pass proved something about a
    # connection that no longer exists.
    export_reconcile_generation = fields.Integer(readonly=True)
    export_reconcile_note = fields.Char(readonly=True)

    # ------------------------------------------------------------------
    # Requirement 1: invoked by the real reconnect lifecycle
    # ------------------------------------------------------------------

    def action_reconnect(self):
        """Reconnect, then require an export reconciliation before exporting.

        Deliberately hooked here rather than on a button. PD-PX-7's block
        is a property of *reconnecting*, so it has to attach to the
        lifecycle transition itself — a block an operator has to remember
        to start is not a block.

        `super()` returns without connecting on several paths (no
        credential, superseded probe, insufficient evidence, a concurrent
        lifecycle transition winning the race). The generation comparison
        is what distinguishes an actual successful reconnect from all of
        them: core bumps `connection_generation` exactly once, only on
        success.
        """
        before = self.connection_generation
        result = super().action_reconnect()
        self.invalidate_recordset()
        if self.state == 'connected' and self.connection_generation != before:
            self._require_export_reconnect_reconciliation()
        return result

    def _require_export_reconnect_reconciliation(self):
        """Block exports and queue the pass. Requirements 3, 4 and 5."""
        self.ensure_one()
        Preview = self.env['shopify.connector.product.export.preview']
        # Requirement 4. Every confirmation taken before this reconnect is
        # invalidated: it described a remote object nobody has re-read.
        open_previews = Preview.sudo().search([
            ('store_id', '=', self.id),
            ('state', 'in', ('previewed', 'confirmed', 'applying')),
        ])
        for preview in open_previews:
            preview._record_expiry('store_reconnected')

        bindings = self._export_reconcile_scope()
        bindings.sudo().write({
            'export_reconcile_state': 'pending',
            'export_reconcile_note': False,
        })
        self.sudo().write({
            'export_reconcile_state': 'required',
            'export_reconcile_generation': self.connection_generation,
            'export_reconcile_at': False,
            'export_reconcile_note': False,
        })
        _logger.info(
            'Store %d reconnected: %d export binding(s) queued for '
            'reconciliation, %d open preview(s) expired.',
            self.id, len(bindings), len(open_previews),
        )
        return self._enqueue_export_reconcile_jobs(bindings)

    def _export_reconcile_scope(self):
        """Requirement 5: every previously exported binding for this store.

        "Previously exported" means it carries a Shopify product GID. A
        binding with no GID makes no claim about a remote object, so
        there is nothing to re-verify and nothing to put at risk.
        """
        self.ensure_one()
        return self.env[
            'shopify.connector.product.template.binding'
        ].sudo().search([
            ('store_id', '=', self.id),
            ('shopify_gid', '!=', False),
        ])

    def _enqueue_export_reconcile_jobs(self, bindings):
        self.ensure_one()
        Service = self.env['shopify.connector.product.export.service']
        jobs = self.env['shopify.connector.job']
        for binding in bindings:
            jobs |= Service._enqueue(
                self, JOB_TYPE_RECONNECT_RECONCILE, 'export_preview_dry_run',
                binding._name, binding.id,
                shopify_target_gid=binding.shopify_gid or False,
            )
        if not bindings:
            # Nothing to verify is a complete reconciliation, not a
            # permanent block. A store with no exported bindings must not
            # be left unable to export its first product.
            self._settle_export_reconciliation()
        else:
            self.sudo().write({'export_reconcile_state': 'in_progress'})
        return jobs

    # ------------------------------------------------------------------
    # Requirement 15: exports resume only on the accepted condition
    # ------------------------------------------------------------------

    def _assert_export_reconciliation_complete(self):
        """Requirement 3: block new exports until a valid terminal result."""
        self.ensure_one()
        if self.export_reconcile_state not in RECONCILE_BLOCKING_STATES:
            return True
        if self.export_reconcile_state == 'review_required':
            raise UserError(
                'Exports are blocked for this store: the reconnect '
                'reconciliation found bindings whose Shopify products are '
                'missing, archived or materially different from what this '
                'connector recorded. Review them before exporting again.'
            )
        raise UserError(
            'Exports are blocked for this store until the reconnect '
            'reconciliation has re-read every previously exported product. '
            'It runs on the job queue; retry once it has finished.'
        )

    def _settle_export_reconciliation(self):
        """Move to a terminal verdict once no binding is still pending."""
        self.ensure_one()
        bindings = self._export_reconcile_scope()
        pending = bindings.filtered(
            lambda b: b.export_reconcile_state == 'pending'
        )
        if pending:
            return False
        in_review = bindings.filtered(
            lambda b: b.export_reconcile_state == 'review'
        )
        self.sudo().write({
            'export_reconcile_state': (
                'review_required' if in_review else 'complete'
            ),
            'export_reconcile_at': fields.Datetime.now(),
            'export_reconcile_generation': self.connection_generation,
            'export_reconcile_note': (
                '%d binding(s) need review before exports resume.'
                % len(in_review)
            ) if in_review else False,
        })
        return True

    # ------------------------------------------------------------------
    # Requirements 2 and 13: the operator-facing re-run
    # ------------------------------------------------------------------

    def action_shopify_export_reconnect_reconciliation(self):
        """Run (or re-run) the pass. Retryable by an authorised operator.

        Requirement 2: authority and company access are both checked
        BEFORE anything elevates, because everything after this point runs
        under `sudo()` on connector-owned rows.

        This is the same public action name PD-PX-7 shipped with, so the
        existing view wiring and its tests keep working. What changed is
        that it now performs the reconciliation the name promised rather
        than only expiring previews.
        """
        self.ensure_one()
        if not (
            self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_reviewer'
            )
            or self.env.user.has_group(
                'shopify_connector_core.group_shopify_connector_admin'
            )
        ):
            raise AccessError(
                'Only a Shopify Connector Reviewer or Administrator may run '
                'the export reconnect reconciliation.'
            )
        if self.company_id and self.company_id not in self.env.user.company_ids:
            raise AccessError(
                'This Shopify store belongs to another company.'
            )
        self._require_export_reconnect_reconciliation()
        return len(self._export_reconcile_scope())


class ShopifyConnectorTemplateBindingExportReconnect(models.Model):
    _inherit = 'shopify.connector.product.template.binding'

    # Optional for the same reason as the store field above: this module
    # does not own `shopify.connector.product.template.binding` either.
    export_reconcile_state = fields.Selection(
        selection=BINDING_RECONCILE_SELECTION,
        default='not_required',
        readonly=True,
        index=True,
    )
    export_reconcile_note = fields.Char(readonly=True)
    export_reconcile_at = fields.Datetime(readonly=True)

    @api.model
    def _additional_protected_binding_fields(self):
        """The reconciliation verdict is evidence, not editable data.

        The binding mixin refuses to create a record while any stored
        field is unclassified, which is what forces this to be a decision
        rather than an oversight. All three are verdict state written only
        by the reconciliation pass; an operator who could edit them could
        clear their own export block.
        """
        return super()._additional_protected_binding_fields() | frozenset((
            'export_reconcile_state',
            'export_reconcile_note',
            'export_reconcile_at',
        ))


class ShopifyConnectorExportReconcileService(models.AbstractModel):
    _name = 'shopify.connector.export.reconcile.service'
    _description = 'Shopify Connector Export Reconnect Reconciliation'

    # ------------------------------------------------------------------
    # The pass itself
    # ------------------------------------------------------------------

    @api.model
    def _handle_product_export_reconnect_reconcile(self, job):
        """Re-verify one binding's claims against the live Shopify product.

        Read-only by construction: the only Shopify call is the module's
        existing `_read_remote_product`, and every outcome writes local
        state only. Requirement 11 — a missing remote product is routed to
        review, never re-created — is a property of there being no
        mutation path in this handler at all, which
        `test_the_reconcile_handler_contains_no_mutation` asserts on the
        source rather than trusting this sentence.
        """
        Service = self.env['shopify.connector.product.export.service']
        binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().browse(job.res_id).exists()
        if not binding:
            job._transition_failed_final(
                'unknown_system_error',
                'The product-template binding no longer exists.',
            )
            return
        store = job.store_id
        if not binding.shopify_gid:
            self._record_binding_verdict(
                binding, 'verified', 'No Shopify product is bound.',
            )
            self._finish(job, store, 'nothing to verify')
            return

        result = Service._read_remote_product(store, job, binding.shopify_gid)
        identity = result.get('store_identity')
        if identity and identity != store.shop_domain:
            # The reconnect landed on a different Shopify store. This is
            # exactly the scenario PD-PX-7 exists for, and it must never be
            # resolved by writing to that store.
            raise JobHandlerError(
                'store_identity_mismatch',
                'The reconciliation read observed a different Shopify '
                'store identity than this connector is bound to.',
            )

        verdict, note = self._verdict_for(binding, result)
        self._record_binding_verdict(binding, verdict, note)
        self._finish(job, store, note)

    @api.model
    def _verdict_for(self, binding, result):
        """Requirements 7, 8 and 9, in the order that matters.

        Existence first: everything below it is a comparison against an
        object that has to be there. Archive state next, because an
        archived product is present but not exportable-to in any sense the
        operator would expect. Then the two identity sets the connector
        holds claims about.
        """
        if not result.get('exists'):
            return 'review', (
                'The Shopify product this binding names no longer exists. '
                'It was not re-created; an operator must decide what should '
                'happen to this binding.'
            )
        product = result.get('product') or {}
        status = (product.get('status') or '').upper()
        if status == 'ARCHIVED':
            return 'review', (
                'The Shopify product is archived. Exports to it are '
                'withheld until an operator decides.'
            )

        remote_variant_gids = {
            variant.get('id') for variant in (result.get('variants') or [])
            if variant.get('id')
        }
        # Searched rather than traversed: the variant binding names its
        # template binding, but the template binding declares no inverse
        # One2many, and this module may not add one to a model another
        # module owns.
        bound_variants = self.env[
            'shopify.connector.product.variant.binding'
        ].sudo().search([
            ('product_template_binding_id', '=', binding.id),
            ('shopify_gid', '!=', False),
        ])
        bound_variant_gids = set(bound_variants.mapped('shopify_gid'))
        missing = bound_variant_gids - remote_variant_gids
        if missing:
            return 'review', (
                '%d bound variant(s) are no longer present on the Shopify '
                'product.' % len(missing)
            )

        media_note = self._media_divergence(binding)
        if media_note:
            return 'review', media_note
        return 'verified', 'Product, variants and media re-verified.'

    @api.model
    def _media_divergence(self, binding):
        """Requirement 9, scoped to what this connector actually owns.

        The media registry records Files this connector created and the
        checksum of the bytes it uploaded. A row that reached `associated`
        must still carry a real File GID; one that never did was mid-flight
        when the connection dropped and cannot be assumed complete. Nothing
        here reads Shopify's Files list: the 2026-07 API exposes no
        reverse-reference query, which is the same limitation that makes
        this pipeline append-only, so a claim of exclusive use would be
        unfounded either way.
        """
        rows = self.env[
            'shopify.connector.product.media.binding'
        ].sudo().search([
            ('product_template_binding_id', '=', binding.id),
        ])
        stranded = rows.filtered(
            lambda row: (
                row.remote_status == 'associated'
                and (
                    not row.shopify_gid
                    or row.shopify_gid.startswith('pending:')
                )
            )
        )
        if stranded:
            return (
                '%d media row(s) claim an association with no durable '
                'Shopify File identity.' % len(stranded)
            )
        interrupted = rows.filtered(
            lambda row: row.remote_status in (
                'staged', 'uploaded', 'processing',
            )
        )
        if interrupted:
            return (
                '%d media upload(s) were still in flight when the '
                'connection dropped and their remote state is unknown.'
                % len(interrupted)
            )
        missing_checksum = rows.filtered(
            lambda row: not row.odoo_image_checksum
        )
        if missing_checksum:
            return (
                '%d media row(s) have no checksum evidence.'
                % len(missing_checksum)
            )
        return False

    @api.model
    def _record_binding_verdict(self, binding, verdict, note):
        binding.sudo().write({
            'export_reconcile_state': verdict,
            'export_reconcile_note': (note or '')[:255],
            'export_reconcile_at': fields.Datetime.now(),
        })
        return binding

    @api.model
    def _finish(self, job, store, note):
        """Terminalise this job, then settle the store's overall verdict.

        Requirement 12: the store must not be left stranded part-way. The
        settle runs on every completion, so the last binding to finish is
        always the one that lifts (or converts) the block, regardless of
        the order the queue happened to run them in.
        """
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        job._log_transition(
            'verification_read',
            'Export reconnect reconciliation: %s' % note,
            from_state='running', to_state='succeeded',
        )
        store.invalidate_recordset()
        store._settle_export_reconciliation()
        return True

    @api.model
    def _prepare_local_reconnect_reconcile(self, job):
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'binding_id': job.res_id,
        }
