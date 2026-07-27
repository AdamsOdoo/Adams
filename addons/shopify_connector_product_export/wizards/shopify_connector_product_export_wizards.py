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

from odoo import api, fields, models
from odoo.exceptions import UserError


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
        readonly=True,
        string='Shopify Store',
    )
    product_gid = fields.Char(
        related='binding_id.shopify_gid',
        readonly=True,
        string='Shopify Product',
    )
    reconcile_note = fields.Char(
        related='binding_id.export_reconcile_note',
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

    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        if self.env.context.get(
            'active_model'
        ) == 'shopify.connector.product.template.binding':
            active_id = self.env.context.get('active_id')
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
