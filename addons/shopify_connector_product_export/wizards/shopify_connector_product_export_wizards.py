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
