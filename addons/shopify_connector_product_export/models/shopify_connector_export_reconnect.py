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

PD-PX-7 also names *media checksums*, and Shopify exposes no digest of a
stored File's bytes, so that third check cannot be satisfied remotely.
A binding claiming an associated media File therefore reaches `review`
with the exact reason rather than `verified` — fail-closed, because no
accepted decision authorises substituting identity-and-association
evidence for the checksum comparison the specification requires. See
`_checksum_unverifiable_divergence`.

Anything missing, archived or materially divergent goes to explicit
review. Nothing is re-created, re-published or repaired: a reconciliation
that silently fixed what it found would be indistinguishable from the
export it is supposed to be gating.
"""

import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from odoo.addons.shopify_connector_core.models.shopify_connector_job import (
    TERMINAL_JOB_STATES,
)
from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from .shopify_connector_product_export_service import REMOTE_MEDIA_PAGE_SIZE

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
    # TD-015 correction. The serialization row for store-level settlement.
    # Its VALUE means nothing; the UPDATE does. See
    # `_serialize_reconcile_settlement` for why a counter and not a lock.
    export_reconcile_settle_seq = fields.Integer(readonly=True, default=0)

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

    def _outstanding_reconcile_jobs(self):
        """Reconcile jobs for this store that have not reached a terminal state.

        These are what a second reconnect collides with. Core's
        `UNIQUE(store_id, operation_scope_key)` holds a scope key only while
        a job is non-terminal, and the key is
        `store|model|res_id|target_gid` -- identical for the old and new
        pass over the same binding. So enqueuing over a live earlier pass
        raises an `IntegrityError`, and a reconnect that fails on a
        constraint is a reconnect that leaves the store unreconciled.
        """
        self.ensure_one()
        return self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', self.id),
            ('job_type', '=', JOB_TYPE_RECONNECT_RECONCILE),
            ('state', 'not in', list(TERMINAL_JOB_STATES)),
        ])

    def _retire_superseded_reconcile_jobs(self):
        """Cancel outstanding jobs from an older connection generation.

        TD-015 correction, requirement 5. Two distinct situations, and
        conflating them is what makes this look like one rule:

        * **A newer reconnect.** The old job's verdict is about a
          connection that no longer exists, so it is cancelled here rather
          than left to be recognised as superseded when it eventually runs.
          Cancelling clears its `operation_scope_key`, which is what lets
          the new pass enqueue at all -- and it removes the job that could
          otherwise release the new block.
        * **A re-run at the same generation.** The outstanding job covers
          exactly the work the re-run wants done, against the same
          connection. It is kept, and its binding is not re-enqueued:
          the re-run COALESCES on it. Cancelling and re-creating would
          discard a verification read that is still valid.

        Returns the binding ids still covered by a kept job.
        """
        self.ensure_one()
        covered = set()
        for job in self._outstanding_reconcile_jobs():
            if job.expected_connection_generation == self.connection_generation:
                covered.add(job.res_id)
                continue
            from_state = job.state
            job.sudo().write({
                'state': 'cancelled',
                'finished_at': fields.Datetime.now(),
                'cancel_reason': (
                    'Superseded by a later reconnect: this job covers '
                    'connection generation %s.'
                    % job.expected_connection_generation
                ),
            })
            job._log_transition(
                'manual_action',
                'Export reconnect reconciliation cancelled: the store has '
                'reconnected again since this job was enqueued.',
                from_state=from_state, to_state='cancelled',
            )
        return covered

    def _enqueue_export_reconcile_jobs(self, bindings):
        self.ensure_one()
        Service = self.env['shopify.connector.product.export.service']
        covered = self._retire_superseded_reconcile_jobs()
        # The cancellations recompute `operation_scope_key` to False; that
        # has to reach the database before the inserts below test the
        # unique constraint against it.
        self.env['shopify.connector.job'].flush_model()
        jobs = self._outstanding_reconcile_jobs()
        for binding in bindings:
            if binding.id in covered:
                continue
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

    def _serialize_reconcile_settlement(self):
        """Serialize concurrent settlement attempts on the store row.

        TD-015 correction, and the mechanism deserves its reasoning.

        Odoo 19's row-lock primitives are both `SKIP LOCKED`
        (`lock_for_update` and `try_lock_for_update`, verified in
        `odoo/orm/models.py` at the pinned 19.0 commit) -- deliberately, so
        a cron batch skips contended rows rather than blocking. That makes
        them the wrong tool here: a settlement that SKIPS is a settlement
        nobody performs, which is the stranding this correction exists to
        remove.

        What is needed instead is a *conflict*, and PostgreSQL under
        REPEATABLE READ -- Odoo's isolation level, set in `odoo/sql_db.py`
        -- provides exactly that. An `UPDATE` of a row that a concurrent
        transaction has already committed an `UPDATE` to raises
        `40001 could not serialize access due to concurrent update`. So an
        unconditional bump of one column on the store row, flushed
        immediately, yields this invariant:

            a transaction that successfully bumps the sequence has a
            snapshot that already contains every previously-committed
            bump -- and therefore every binding verdict committed in the
            same transaction as one.

        Which is precisely what settlement needs: whoever bumps last sees
        every verdict. Any interleaving that would break it aborts with
        40001 instead, and the dispatcher's per-job concurrency boundary
        re-drives the job under its declared
        `remote_read_replay_safe` policy on a fresh snapshot.

        The value is written but never read for meaning. It is a version
        counter whose only job is to make the write conflict.
        """
        self.ensure_one()
        elevated = self.sudo()
        elevated.write({
            'export_reconcile_settle_seq':
                elevated.export_reconcile_settle_seq + 1,
        })
        # Deferring this to the end of the transaction would defer the
        # conflict past the decision it has to gate.
        elevated.flush_recordset(['export_reconcile_settle_seq'])
        return True

    def _settle_export_reconciliation(self, generation=None):
        """Move to a terminal verdict once no binding is still pending.

        `generation` is the connection epoch whose pass is settling. A job
        always passes its own, so a verdict can only ever settle the pass
        it belongs to: an older in-flight job that arrives after a second
        reconnect finds the store already re-armed at a newer generation
        and returns without touching it. Omitting it means "whatever pass
        is current", which is only correct for the enqueue-time path that
        settles an empty scope it just created.
        """
        self.ensure_one()
        if generation is None:
            generation = self.export_reconcile_generation
        # Everything below reads verdicts and decides. Serialize first, so
        # the read that follows is one no concurrent settlement can have
        # invalidated.
        self._serialize_reconcile_settlement()
        self.invalidate_recordset()
        if self.export_reconcile_generation != generation:
            _logger.info(
                'Store %d settlement for generation %s abandoned: the store '
                'is now at generation %s.',
                self.id, generation, self.export_reconcile_generation,
            )
            return False
        if self.export_reconcile_state not in RECONCILE_BLOCKING_STATES:
            # Already terminal for this generation. A second settle must not
            # re-stamp it, and must not report that it did the settling.
            return False
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
            # The generation this verdict actually covers -- not
            # `connection_generation`, which is whatever the store has
            # reached by now. Stamping the live value let an old pass's
            # verdicts be recorded as proof about a newer connection.
            'export_reconcile_generation': generation,
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
        # TD-015 correction, requirements 3 and 4. This job was enqueued
        # for one connection epoch, captured at enqueue in core's
        # `expected_connection_generation`. If the store has been
        # reconnected since, this job's verdict is about a connection that
        # no longer exists -- and worse, writing it would let an old pass
        # release the block a NEWER reconnect just installed. It stops
        # here: no verdict, no settlement, nothing released.
        #
        # `execute_business` refuses a stale-generation transport already,
        # but that is not sufficient on its own. The no-GID branch below
        # reaches a verdict with no Shopify call at all, and a superseded
        # job must be recognised as superseded rather than surface as a
        # transport failure.
        if job.expected_connection_generation != store.connection_generation:
            self._supersede(job, store)
            return
        if not binding.shopify_gid:
            self._record_binding_verdict(
                binding, 'verified', 'No Shopify product is bound.',
            )
            self._finish(job, store, 'nothing to verify')
            return

        result = Service._read_remote_product(store, job, binding.shopify_gid)
        # The reconnect landed on a different Shopify store. This is
        # exactly the scenario PD-PX-7 exists for, and it must never be
        # resolved by writing to that store.
        self._assert_same_store(store, result.get('store_identity'))

        verdict, note = self._verdict_for(binding, result, store=store, job=job)
        self._record_binding_verdict(binding, verdict, note)
        self._finish(job, store, note)

    @api.model
    def _supersede(self, job, store):
        """Terminalise a job whose connection epoch has been replaced."""
        job.sudo().write({
            'state': 'skipped', 'finished_at': fields.Datetime.now(),
        })
        job._log_transition(
            'verification_read',
            'Export reconnect reconciliation superseded: this job covers '
            'connection generation %s and the store is now at %s.' % (
                job.expected_connection_generation,
                store.connection_generation,
            ),
            from_state='running', to_state='skipped',
        )
        _logger.info(
            'Reconcile job %d superseded by a newer reconnect generation.',
            job.id,
        )
        return True

    @api.model
    def _verdict_for(self, binding, result, store=None, job=None):
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

        media_note = self._media_divergence(binding, store=store, job=job)
        if media_note:
            return 'review', media_note
        # Deliberately precise about what "re-verified" covers. Existence,
        # archive state and the governed variant GID set were re-read from
        # Shopify. This branch is reached only when the binding claims no
        # associated Shopify media -- so there is no media checksum for
        # PD-PX-7 to require, and none is implied. A binding that DOES claim
        # an association cannot reach `verified` at all; see
        # `_checksum_unverifiable_divergence`.
        return 'verified', (
            'Product and variants re-verified against Shopify. This binding '
            'claims no associated Shopify media.'
        )

    @api.model
    def _media_divergence(self, binding, store=None, job=None):
        """Requirement 9, proved against the remote store.

        TD-015 correction. This used to read the local registry and
        nothing else -- a row saying `associated` with a File GID and a
        checksum contributed to `verified` without anything having looked
        at Shopify. After a reconnect that is the one thing the local row
        cannot establish: it is a *claim* about a remote object, and the
        reconnect is what put every such claim in doubt. A merchant could
        delete every image between disconnect and reconnect and this
        returned `False`.

        Local state is still read FIRST, because two of its outcomes are
        decidable without a call and must not be paid for with one: a row
        that claims an association it has no File GID for, and a row left
        mid-flight. Both are local contradictions.

        What the remote read then proves, and what it cannot:

        * **Existence and identity of the File** -- proved. The connector
          created it and holds its GID.
        * **Association with the expected product** -- proved. The File
          GID appears as a node on that product's `media` connection,
          which is the same evidence the module's accepted
          `_reconcile_media_associate` verification read already relies on.
        * **`fileStatus`** -- proved. A File that has become `FAILED`
          since it was associated is a divergence.
        * **Connector-owned filename identity** -- proved, by the
          `files(query: "filename:...")` read, for a row whose File GID
          is absent from the product so the connector can distinguish
          "detached" from "gone".
        * **Checksum correspondence -- NOT PROVABLE, so NOT `verified`.**
          The 2026-07 `MediaImage`/`File` interface exposes `alt`,
          `createdAt`, `fileErrors`, `fileStatus`, `id`, `mimeType`,
          `originalSource`, `preview` and `updatedAt`, and no digest of the
          stored bytes (`originalSource.fileSize` is a length, not a
          digest). PD-PX-7 requires the pass to verify *media checksums*
          before exports resume, and no repository decision has ever
          authorised substituting identity-and-association evidence for
          that. So a binding whose association this pass re-read but whose
          checksum it cannot prove is routed to review with the exact
          reason -- see `_checksum_unverifiable_divergence`. A row missing
          its LOCAL checksum is a separate, local contradiction and is
          caught below.

        Returns a divergence note, or `False` only when this binding makes
        no associated-media claim for PD-PX-7 to verify.
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
        associated = rows.filtered(
            lambda row: row.remote_status == 'associated'
        )
        if not associated:
            return False
        if store is None or job is None:
            # Not reachable from the handler, which always passes both. A
            # caller that cannot supply the transport context cannot
            # perform the remote half, and must not be allowed to return
            # the `False` that means "re-verified".
            return (
                'Remote media state was not re-read, so this binding\'s '
                'media claims are unverified.'
            )
        return self._remote_media_divergence(store, job, binding, associated)

    @api.model
    def _remote_media_divergence(self, store, job, binding, rows):
        """The remote half. Read-only; no mutation path exists here."""
        Service = self.env['shopify.connector.product.export.service']
        read = Service._read_remote_product_media(
            store, job, binding.shopify_gid,
        )
        self._assert_same_store(store, read.get('store_identity'))
        if not read.get('exists'):
            # The existence check in `_verdict_for` ran against a separate
            # read. A product that disappeared between the two is still a
            # review, not a media finding.
            return (
                'The Shopify product could not be re-read while verifying '
                'its media.'
            )
        nodes = read.get('nodes') or []
        remote_by_gid = {
            node.get('id'): node for node in nodes if node.get('id')
        }
        failed = [
            row for row in rows
            if (remote_by_gid.get(row.shopify_gid) or {}).get(
                'fileStatus', ''
            ).upper() == 'FAILED'
        ]
        if failed:
            return (
                '%d associated media File(s) are in FAILED state on Shopify.'
                % len(failed)
            )
        absent = [row for row in rows if row.shopify_gid not in remote_by_gid]
        if not absent:
            # Every association was found, with a non-FAILED status, on the
            # expected product. That is as far as a remote read can get --
            # and it is short of what PD-PX-7 requires.
            return self._checksum_unverifiable_divergence(rows)
        if read.get('truncated'):
            # Requirement 5: an unverifiable claim is never reported as
            # verified, and never as a divergence either. The connector
            # did not see the whole list, so "absent" is not established.
            return (
                'This product carries more than %d media items, so %d '
                'connector-owned association(s) could not be re-verified '
                'from a single read.' % (REMOTE_MEDIA_PAGE_SIZE, len(absent))
            )
        return self._absent_media_divergence(store, job, absent)

    @api.model
    def _checksum_unverifiable_divergence(self, rows):
        """PD-PX-7's third check, when the platform cannot answer it.

        The requirement is verbatim: the pass verifies "exists / variant GID
        set / **media checksums**" before exports resume. The first two are
        remotely provable and are proved. The third is not: the 2026-07
        Admin GraphQL `MediaImage` exposes `alt`, `createdAt`, `fileErrors`,
        `fileStatus`, `id`, `image`, `mediaContentType`, `mediaErrors`,
        `mediaWarnings`, `mimeType`, `originalSource`, `preview`, `status`,
        `translations` and `updatedAt`, and none of them is a digest of the
        stored bytes -- `originalSource.fileSize` is a length, which two
        different images can share.

        Two dispositions were available, and this is the one the repository
        actually authorises. Reporting `verified` on identity-and-association
        evidence alone would substitute a narrower proof for the one the
        accepted specification names, and **no accepted decision authorises
        that substitution**: every statement to that effect was written in
        this same unmerged correction cycle, which cannot authorise itself.
        So the pass fails closed -- the operator is told exactly what was
        established and exactly what was not, and decides.

        Read-only, like everything else here: nothing is re-created,
        re-uploaded, detached or deleted. The consequence is a real one and
        is deliberate -- a reconnected store with exported media reaches
        `review_required` rather than `complete`, and an operator must clear
        it before exports resume.
        """
        return (
            '%d media association(s) were re-read on the product with the '
            'expected File identity and non-FAILED status, but Shopify '
            'exposes no digest of the stored bytes, so checksum '
            'correspondence could not be proven. Nothing was changed; an '
            'operator decides.' % len(rows)
        )

    @api.model
    def _absent_media_divergence(self, store, job, rows):
        """Distinguish a detached File from one that is gone entirely.

        Both are divergences and neither is repaired here, but they are
        different findings and an operator resolves them differently: a
        File that still exists under this connector's filename was
        detached from the product, while one that no longer exists at all
        was deleted from the store.
        """
        Service = self.env['shopify.connector.product.export.service']
        detached, vanished, ambiguous = [], [], []
        for row in rows:
            found = Service._search_remote_files_by_filename(
                store, job, row.connector_filename,
            )
            self._assert_same_store(store, found.get('store_identity'))
            nodes = found.get('nodes') or []
            matching = [
                node for node in nodes if node.get('id') == row.shopify_gid
            ]
            if matching:
                detached.append(row)
            elif nodes:
                ambiguous.append(row)
            else:
                vanished.append(row)
        parts = []
        if vanished:
            parts.append(
                '%d connector-created media File(s) no longer exist on '
                'Shopify' % len(vanished)
            )
        if detached:
            parts.append(
                '%d File(s) still exist but are no longer associated with '
                'this product' % len(detached)
            )
        if ambiguous:
            parts.append(
                '%d File(s) carry this connector\'s filename under a '
                'different identity' % len(ambiguous)
            )
        return (
            '%s. Nothing was re-created, re-uploaded or re-attached; an '
            'operator decides.' % '; '.join(parts)
        )

    @api.model
    def _assert_same_store(self, store, observed_identity):
        """A read that landed on another store settles nothing here."""
        if observed_identity and observed_identity != store.shop_domain:
            raise JobHandlerError(
                'store_identity_mismatch',
                'The reconciliation read observed a different Shopify '
                'store identity than this connector is bound to.',
            )
        return True

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

        TD-015 correction, and the ordering here is the whole fix.

        Before: each job wrote its verdict into the ORM cache and then
        searched for pending siblings. Two final jobs in separate
        transactions each saw the other's binding still `pending` -- neither
        verdict was committed yet -- so each declined to settle and both
        committed. Every binding terminal, the store permanently
        `in_progress`, and no job left to notice.

        After, three things in order:

        1. **Flush this verdict.** `_record_binding_verdict` wrote through
           the ORM; the row must actually be in the database before a
           search can find it, or this job cannot see its own work.
        2. **Serialize.** Inside `_settle_export_reconciliation`, so the
           sibling read cannot straddle a concurrent settlement.
        3. **Settle THIS generation.** Passing the job's own epoch is what
           stops an old pass from settling a newer one.
        """
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        job._log_transition(
            'verification_read',
            'Export reconnect reconciliation: %s' % note,
            from_state='running', to_state='succeeded',
        )
        self.env['shopify.connector.product.template.binding'].flush_model()
        store.invalidate_recordset()
        store._settle_export_reconciliation(
            generation=job.expected_connection_generation,
        )
        return True

    @api.model
    def _prepare_local_reconnect_reconcile(self, job):
        return {
            'job_id': job.id,
            'store_id': job.store_id.id,
            'binding_id': job.res_id,
        }
