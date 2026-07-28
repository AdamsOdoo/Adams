"""U3 display-and-delegate wizards for the export operator surfaces.

Why these exist, and what they are forbidden from doing.

Two sanctioned server actions need an operator surface: requesting a preview
(which needs a store when more than one is connected) and confirming one
(which must show the operator what they are confirming, including what the
connector refused to do). An Odoo `type="object"` button calls a method with
no arguments, so the store choice needs somewhere to live; and a confirmation
that does not display the diff is a click, not a review.

Each wizard does exactly three things: show what is about to happen, collect
the one input the server method needs, and delegate. **No business logic
lives here.** No wizard writes a preview field, decides a payload, interprets
a state, or bypasses a guard — the server method owns all of that, including
its own access checks, so a caller who is not permitted gets an AccessError
with zero side effects. This follows the precedent U1 set with the
fulfillment review-release wizard and U2 with the inventory wizards.
"""

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, MissingError, UserError


class ShopifyConnectorProductExportRequestWizard(models.TransientModel):
    _name = 'shopify.connector.product.export.request.wizard'
    _description = 'Shopify Connector Product Export Preview Request'

    product_template_id = fields.Many2one(
        comodel_name='product.template',
        required=True,
        readonly=True,
    )
    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        string='Shopify Store',
    )
    # Non-stored related reads so the dialog shows current truth rather than a
    # copy of it: a flag flipped between opening and confirming is visible.
    export_enabled = fields.Boolean(
        related='product_template_id.shopify_export_enabled',
        readonly=True,
    )
    export_status = fields.Selection(
        related='product_template_id.shopify_export_status',
        readonly=True,
    )

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'product.template':
            active_id = self.env.context.get('active_id')
            if active_id:
                result['product_template_id'] = active_id
        stores = self.env['shopify.connector.store'].search(
            [('state', '=', 'connected')]
        )
        if len(stores) == 1:
            result['store_id'] = stores.id
        return result

    def action_confirm(self):
        self.ensure_one()
        if not self.store_id:
            raise UserError('Choose the Shopify store to preview against.')
        return self.env[
            'shopify.connector.product.export.service'
        ].enqueue_preview(self.product_template_id, self.store_id)


class ShopifyConnectorProductExportConfirmWizard(models.TransientModel):
    _name = 'shopify.connector.product.export.confirm.wizard'
    _description = 'Shopify Connector Product Export Confirmation'

    preview_id = fields.Many2one(
        comodel_name='shopify.connector.product.export.preview',
        required=True,
        readonly=True,
    )
    product_template_id = fields.Many2one(
        related='preview_id.product_template_id',
        readonly=True,
    )
    export_path = fields.Selection(
        related='preview_id.export_path',
        readonly=True,
    )
    state = fields.Selection(related='preview_id.state', readonly=True)
    has_blocked_differences = fields.Boolean(
        related='preview_id.has_blocked_differences',
        readonly=True,
    )
    # Read-only rendered text rather than a JSON widget: an operator reviewing
    # a destructive-capable change should not have to read raw JSON to find
    # out what will happen.
    changes_summary = fields.Text(
        compute='_compute_summaries',
        readonly=True,
        string='What will change',
    )
    blocked_summary = fields.Text(
        compute='_compute_summaries',
        readonly=True,
        string='What this connector refuses to do',
    )
    untouched_summary = fields.Text(
        compute='_compute_summaries',
        readonly=True,
        string='Left exactly as it is',
    )
    acknowledged = fields.Boolean(
        string='I have reviewed the changes above',
        help='Confirmation is an explicit act. Nothing is exported until this '
             'is ticked and confirmed.',
    )

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get(
            'active_model'
        ) == 'shopify.connector.product.export.preview':
            active_id = self.env.context.get('active_id')
            if active_id:
                result['preview_id'] = active_id
        return result

    @api.depends('preview_id')
    def _compute_summaries(self):
        for wizard in self:
            preview = wizard.preview_id
            diff = preview.diff or {}
            wizard.changes_summary = self._render_changes(preview, diff)
            wizard.blocked_summary = self._render_blocked(preview)
            wizard.untouched_summary = self._render_untouched(diff)

    @api.model
    def _render_changes(self, preview, diff):
        lines = []
        if preview.export_path == 'create':
            lines.append(
                'CREATE a new Shopify product (status %s). New products are '
                'not published by export.' % (
                    preview.product_template_id.shopify_export_status or 'draft',
                )
            )
        for change in diff.get('scalars') or []:
            lines.append('Field %s: %r -> %r' % (
                change.get('field'), change.get('from'), change.get('to'),
            ))
        for entry in diff.get('variants_update') or []:
            fields_changed = ', '.join(
                str(item.get('field')) for item in entry.get('changes') or []
            )
            lines.append('Update variant %s (%s)' % (
                entry.get('display_name'), fields_changed or 'no field',
            ))
        for entry in diff.get('variants_create') or []:
            lines.append('Create variant %s' % (entry.get('display_name'),))
        media = diff.get('media') or {}
        for entry in media.get('appends') or []:
            lines.append('Append image (%s role, checksum %s…)' % (
                entry.get('role'), (entry.get('checksum') or '')[:8],
            ))
        if not diff.get('price_exported', True):
            lines.append(
                'Prices are NOT exported: this store does not declare Odoo as '
                'the price source of truth.'
            )
        return '\n'.join(lines) or 'Nothing to export.'

    @api.model
    def _render_blocked(self, preview):
        items = (preview.blocked_differences or {}).get('items') or []
        if not items:
            return 'Nothing was refused.'
        return '\n'.join(
            '[%s] %s' % (item.get('kind'), item.get('detail'))
            for item in items
        )

    @api.model
    def _render_untouched(self, diff):
        untouched = diff.get('untouched') or {}
        lines = [str(untouched.get('note') or '')]
        for key in ('collections', 'metafields', 'existing_media'):
            if key in untouched:
                lines.append('%s present on Shopify: %s' % (
                    key.replace('_', ' '), 'yes' if untouched[key] else 'no',
                ))
        media = diff.get('media') or {}
        if media.get('reason'):
            lines.append(str(media['reason']))
        return '\n'.join(line for line in lines if line)

    def action_confirm(self):
        self.ensure_one()
        if not self.acknowledged:
            raise UserError(
                'Tick the acknowledgement to confirm this export. Nothing has '
                'been exported.'
            )
        return self.preview_id.action_confirm_export_preview()


class ShopifyConnectorExportChecksumAckWizard(models.TransientModel):
    """TD-015: the consequence-stating confirmation for the one narrow ack.

    Same display-and-delegate contract as the two wizards above, and for the
    same reason: the authority lives in
    `action_shopify_export_acknowledge_checksum` on the binding, which
    performs the Administrator check, the record-access check, the company
    check and the eligibility check itself. This wizard adds exactly one
    thing the server cannot: the sentence the operator has to read before
    they are allowed to accept anything.

    That sentence is not decoration. The whole risk in this route is an
    operator believing they verified something. So the copy states, in the
    operator's own words, what Shopify DID confirm, what it cannot confirm,
    what they are accepting, and what was NOT changed -- and the server
    refuses the call unless the box beside it is ticked.

    Correction A (independent review, Defect #1). The delegation above is
    real for the two ACTION methods, but this wizard MODEL is its own
    boundary, and it was not equivalent to it: the model's sole ACL row
    grants full CRUD to the whole company-unscoped
    `group_shopify_connector_admin` group with no `ir.rule` anywhere in the
    module (see `security/shopify_connector_product_export_company_rules.xml`
    -- a creator-scoped rule closes that here), and `store_id`/`product_gid`/
    `reconcile_note` are `related=` fields that default to Odoo's
    `compute_sudo=True`, which computes them AS SUPERUSER regardless of who
    is asking -- bypassing the SEC-3 record rule on
    `shopify.connector.product.template.binding` entirely. A Connector
    Administrator of one company could `create({'binding_id': <another
    company's binding id>})` over plain RPC, with no UI involved, and then
    `read(['store_id', 'product_gid', 'reconcile_note'])` and see it.

    Two independent corrections, deliberately both applied:

    1. `related_sudo=False` on the three display fields below, so their
       computation runs as the CALLING user and is therefore subject to the
       same SEC-3 record rule a direct read of the binding already is --
       this is what protects every read path (`read()`, `search_read()`,
       `default_get()`, an onchange), not only the ones this file happens to
       call.
    2. `_resolve_binding_for_ack` re-uses
       `binding._assert_export_reconcile_ack_authority()` -- the EXACT gate
       the two production actions already enforce -- to validate a
       caller-supplied `binding_id` before it becomes this wizard's binding,
       on `create()`, `write()` and default/context-based opening alike. A
       foreign-company binding and one that does not exist collapse to the
       identical refusal, so neither the exception raised nor its message
       discloses which one it was.
    """

    _name = 'shopify.connector.export.checksum.ack.wizard'
    _description = 'Shopify Connector Unprovable Media Checksum Acknowledgement'

    binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.template.binding',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    store_id = fields.Many2one(
        related='binding_id.store_id',
        related_sudo=False,
        readonly=True,
        string='Shopify Store',
    )
    product_gid = fields.Char(
        related='binding_id.shopify_gid',
        related_sudo=False,
        readonly=True,
        string='Shopify Product',
    )
    reconcile_note = fields.Char(
        related='binding_id.export_reconcile_note',
        related_sudo=False,
        readonly=True,
        string='What the reconciliation found',
    )
    verified_summary = fields.Text(
        compute='_compute_summaries',
        readonly=True,
        string='What Shopify confirmed',
    )
    unprovable_summary = fields.Text(
        compute='_compute_summaries',
        readonly=True,
        string='What Shopify cannot confirm',
    )
    consequence_summary = fields.Text(
        compute='_compute_summaries',
        readonly=True,
        string='What acknowledging does',
    )
    confirmed = fields.Boolean(
        string=(
            'I accept that byte correspondence was NOT cryptographically '
            'verified'
        ),
        help='Acknowledgement is an explicit act. Nothing is acknowledged '
             'until this is ticked and confirmed.',
    )

    # ------------------------------------------------------------------
    # Correction A: validate a caller-supplied binding_id before it can
    # become this wizard's binding, on every route that can set it.
    # ------------------------------------------------------------------

    def _resolve_binding_for_ack(self, binding_id):
        """Fail-closed resolution of a caller-supplied binding id.

        Delegates the whole authority, record-access and company decision
        to `_assert_export_reconcile_ack_authority` on the binding -- the
        exact gate `action_shopify_export_open_checksum_ack_wizard` and
        `action_shopify_export_acknowledge_checksum` already enforce -- so
        this wizard can never grant, through `create()`, `write()` or
        `default_get()`, what the binding model itself would refuse.

        A foreign-company binding and one that does not exist are
        deliberately collapsed to the identical refusal: Odoo's own
        `fetch()` raises `AccessError` for the former (the SEC-3 record
        rule excludes it from the query) and `MissingError` for the latter
        (there is no row to exclude), and neither the exception class nor
        the message either produces here may let a caller tell which one it
        was.
        """
        if not binding_id:
            raise AccessError(_(
                'This checksum acknowledgement is not available.'
            ))
        binding = self.env[
            'shopify.connector.product.template.binding'
        ].browse(int(binding_id))
        try:
            binding._assert_export_reconcile_ack_authority()
        except (AccessError, MissingError):
            raise AccessError(_(
                'This checksum acknowledgement is not available.'
            ))
        return binding

    # `@api.constrains` was considered and rejected here: Odoo runs
    # constraint methods with `self` already `sudo()`'d
    # (`_validate_fields`, "run constrains just as sudoed computed-stored
    # fields" — `odoo/orm/models.py` at the pinned `30bde9ff`), so
    # `check_access` inside `_assert_export_reconcile_ack_authority` would
    # silently no-op (`env.su` short-circuits it) and the validation would
    # never actually refuse anything. `create()`/`write()` overrides below
    # run as the genuine calling user and are the correct place for this.

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('binding_id'):
                self._resolve_binding_for_ack(vals['binding_id'])
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('binding_id'):
            self._resolve_binding_for_ack(vals['binding_id'])
        return super().write(vals)

    def default_get(self, fields_list):
        context = self.env.context
        active_id = None
        if context.get(
            'active_model'
        ) == 'shopify.connector.product.template.binding':
            active_id = context.get('active_id')
        # Validated BEFORE `super().default_get()` runs, not after: the base
        # implementation resolves `context['default_binding_id']` (set by
        # `action_shopify_export_open_checksum_ack_wizard`) itself, and if
        # `fields_list` includes the related display fields it computes them
        # against an ephemeral record built from those defaults. Validating
        # only afterward would be too late to stop that computation from
        # ever being attempted on an unauthorised id.
        for candidate in (active_id, context.get('default_binding_id')):
            if candidate:
                self._resolve_binding_for_ack(candidate)
        result = super().default_get(fields_list)
        if active_id:
            result['binding_id'] = active_id
        return result

    @api.depends('binding_id')
    def _compute_summaries(self):
        for wizard in self:
            binding = wizard.binding_id
            files = binding.export_reconcile_evidence_file_gids or ''
            count = len([gid for gid in files.split(',') if gid])
            wizard.verified_summary = (
                'This reconnect re-read Shopify and confirmed:\n'
                '• the connection is bound to the expected Shopify store '
                '(%s);\n'
                '• the expected product still exists and is not archived '
                '(%s);\n'
                '• every bound variant is still present on it;\n'
                '• all %d image File(s) this connector created are still '
                'attached to that product, under the identities it recorded;\n'
                '• none of those Files is in a FAILED state;\n'
                '• the response was complete — nothing was truncated or '
                'left inconclusive.' % (
                    binding.store_id.shop_domain or '',
                    binding.shopify_gid or '',
                    count,
                )
            )
            wizard.unprovable_summary = (
                'Shopify exposes no digest of a stored File\'s bytes. Its '
                'MediaImage and MediaImageOriginalSource types return a file '
                'size, a URL, a status and timestamps — and no checksum. So '
                'the connector CANNOT prove that the bytes stored on Shopify '
                'are the same bytes it uploaded from Odoo. That is the only '
                'thing still unproven here, and no operator action can prove '
                'it either.'
            )
            wizard.consequence_summary = (
                'Acknowledging records that you, by name, accept THAT ONE '
                'uncertainty for THIS binding, against this exact connection, '
                'product and File identity, and this exact local image.\n\n'
                'It does not verify anything. It contacts Shopify not at all: '
                'no product, image or File is created, changed, uploaded, '
                'detached or deleted, and no export runs.\n\n'
                'It is withdrawn automatically if the store is reconnected '
                'again, if the reconciliation runs again, or if any of the '
                'identities or the local image change.'
            )

    def action_confirm(self):
        self.ensure_one()
        if not self.confirmed:
            raise UserError(
                'Tick the acknowledgement to record it. Nothing has been '
                'acknowledged and nothing was changed on Shopify.'
            )
        self.binding_id.action_shopify_export_acknowledge_checksum(
            confirmed=True,
        )
        return {'type': 'ir.actions.act_window_close'}
