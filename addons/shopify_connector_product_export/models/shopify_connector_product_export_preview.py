"""The export preview record — the only door an apply can come through.

D-015-5 made mechanical. A preview is a *fresh read* of Shopify plus the
computed field-level difference against Odoo, frozen with an expiry. An
apply job refuses to run without a matching `confirmed`, unexpired preview
whose plan it executes step by step, so "review then apply" is not a
convention a caller can skip — there is no other code path to a mutation.

Two things are deliberately stored rather than recomputed at apply time:

* `apply_plan` — the exact ordered mutation steps the operator confirmed.
  Recomputing it at apply would mean the operator confirmed one thing and
  the connector executed another.
* `blocked_differences` — every difference that would require deleting
  something on Shopify. These are never executable. They exist on the
  record so the operator can *see* what the connector refused to do, which
  is the difference between a guard and a silent omission.

The write surface is closed exactly like `shopify.connector.mutation.attempt`:
a named service context, under `sudo()`, or nothing. A preview whose diff or
confirmation could be edited by an ordinary write is not a guard.
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from odoo.addons.shopify_connector_core.tools.redaction import redact

PREVIEW_WRITE_CONTEXT = 'shopify_export_preview_write_surface'

CREATE_SURFACE = '_create_preview'
WRITE_SURFACES = frozenset((
    '_record_confirmation',
    '_record_plan_progress',
    '_record_expiry',
    '_record_applied',
    '_record_created_binding',
))

PREVIEW_STATE_SELECTION = [
    ('previewed', 'Previewed'),
    ('confirmed', 'Confirmed'),
    ('applying', 'Applying'),
    ('applied', 'Applied'),
    ('expired', 'Expired'),
    ('blocked', 'Blocked'),
]

# D-015-5: a preview is stale after this long even if nothing changed. The
# remote `updatedAt` gate (D-015-6) closes the Shopify-side direction and
# the source `write_date` comparison closes the Odoo-side one; this bound
# closes the "nothing changed but the operator's knowledge is a day old"
# direction, which neither of the other two can see.
PREVIEW_VALIDITY_HOURS = 24

EXPORT_PATH_SELECTION = [
    ('create', 'Create'),
    ('update', 'Update'),
]


class ShopifyConnectorProductExportPreview(models.Model):
    _name = 'shopify.connector.product.export.preview'
    _inherit = ['shopify.connector.scope.mixin']
    _description = 'Shopify Connector Product Export Preview'
    _order = 'previewed_at desc, id desc'

    # SEC-3 (#197): opt in to Odoo 19's native company consistency check, so a
    # preview can only ever name a template of its own store's company.
    _check_company_auto = True

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    product_template_id = fields.Many2one(
        comodel_name='product.template',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
        check_company=True,
    )
    # Null on the create path: there is no binding yet, and inventing one
    # before the remote product exists is exactly the duplicate-creating
    # shortcut this module refuses to take.
    product_template_binding_id = fields.Many2one(
        comodel_name='shopify.connector.product.template.binding',
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    export_path = fields.Selection(
        selection=EXPORT_PATH_SELECTION,
        required=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=PREVIEW_STATE_SELECTION,
        required=True,
        default='previewed',
        index=True,
        readonly=True,
    )
    # The operator-facing difference, by section: scalars, variants to
    # update, variants to create, media to append, and the untouched
    # merchant-owned surfaces named explicitly so "not shown" never has to
    # be read as "not affected".
    diff = fields.Json(readonly=True)
    apply_plan = fields.Json(readonly=True)
    blocked_differences = fields.Json(readonly=True)
    # Verbatim Shopify `updatedAt` string at preview time. Char, not
    # Datetime, so the remote value round-trips exactly and the apply-time
    # comparison is a string equality on what Shopify actually said.
    remote_updated_at = fields.Char(readonly=True)
    remote_product_gid = fields.Char(readonly=True)
    source_write_date = fields.Datetime(readonly=True)
    previewed_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        readonly=True,
    )
    expires_at = fields.Datetime(required=True, readonly=True)
    confirmed_uid = fields.Many2one('res.users', readonly=True)
    confirmed_at = fields.Datetime(readonly=True)
    applied_at = fields.Datetime(readonly=True)
    # Set when the diff contains at least one blocked difference. An
    # operator may still confirm the rest; what they may never do is
    # confirm the blocked part, because it is not in `apply_plan`.
    has_blocked_differences = fields.Boolean(readonly=True, default=False)

    _store_template_state_idx = models.Index(
        '(store_id, product_template_id, state)'
    )

    # ------------------------------------------------------------------
    # Closed write surface
    # ------------------------------------------------------------------

    @api.model
    def _preview_surface(self, name):
        if name != CREATE_SURFACE and name not in WRITE_SURFACES:
            raise AccessError('Unknown export-preview write surface.')
        return self.sudo().with_context(**{PREVIEW_WRITE_CONTEXT: name})

    @api.model_create_multi
    def create(self, vals_list):
        if (
            not self.env.su
            or self.env.context.get(PREVIEW_WRITE_CONTEXT) != CREATE_SURFACE
        ):
            raise AccessError(
                'Export previews can only be created by the export service.'
            )
        return super().create(vals_list)

    def write(self, vals):
        surface = self.env.context.get(PREVIEW_WRITE_CONTEXT)
        if not self.env.su or surface not in WRITE_SURFACES:
            raise AccessError(
                'Export previews can only be changed by a sanctioned export '
                'service surface.'
            )
        immutable = {
            'store_id', 'product_template_id', 'export_path', 'diff',
            'blocked_differences', 'source_write_date', 'previewed_at',
            'expires_at', 'has_blocked_differences',
        }
        # The create path learns its binding and its remote identity only
        # once the remote product exists, so those two are writable — but
        # only through the one surface that records a completed create, and
        # only while they are still empty (below).
        if surface != '_record_created_binding':
            immutable |= {
                'product_template_binding_id', 'remote_product_gid',
                'remote_updated_at',
            }
        else:
            for record in self:
                if record.product_template_binding_id or record.remote_product_gid:
                    raise ValidationError(
                        'This preview already names a Shopify product; its '
                        'identity cannot be rewritten.'
                    )
        if set(vals) & immutable:
            raise ValidationError(
                'The reviewed content of an export preview is immutable. '
                'Run a fresh preview instead.'
            )
        return super().write(vals)

    def unlink(self):
        raise AccessError(
            'Export previews are the audit trail of what an operator '
            'confirmed and can never be deleted.'
        )

    # ------------------------------------------------------------------
    # Freshness
    # ------------------------------------------------------------------

    def _is_expired(self, now=None):
        self.ensure_one()
        now = now or fields.Datetime.now()
        if self.expires_at and self.expires_at <= now:
            return True
        # The Odoo-side staleness direction: any write to the template or its
        # variants after the preview was taken invalidates it, because the
        # diff the operator confirmed described the older data.
        current = self._source_write_date(self.product_template_id)
        return bool(
            current and self.source_write_date and current > self.source_write_date
        )

    @api.model
    def _source_write_date(self, template):
        """The latest write across the exported Odoo source surface.

        The template alone is not enough: a price or barcode edit lands on
        `product.product`, leaving the template's own `write_date` untouched
        while changing what would be exported.
        """
        if not template:
            return False
        # Read elevated on purpose. This is an internal freshness computation,
        # not a disclosure: an auditor or reviewer who may see a preview must
        # not be refused it because they cannot read `product.template`, and
        # the only values read are two timestamps.
        template = template.sudo()
        dates = [template.write_date]
        variants = template.product_variant_ids
        if variants:
            dates.extend(variants.mapped('write_date'))
        dates = [value for value in dates if value]
        return max(dates) if dates else False

    # ------------------------------------------------------------------
    # Recorded transitions
    # ------------------------------------------------------------------

    def _record_expiry(self, reason):
        self.ensure_one()
        if self.state in ('applied', 'expired'):
            return self
        self._preview_surface('_record_expiry').write({'state': 'expired'})
        self.store_id._create_lifecycle_audit_job(
            'Export preview expired preview_id=%d template_id=%d reason=%s' % (
                self.id, self.product_template_id.id, redact(reason),
            )
        )
        return self

    def _record_plan_progress(self, plan):
        self.ensure_one()
        self._preview_surface('_record_plan_progress').write({'apply_plan': plan})
        return self

    def _record_applied(self):
        self.ensure_one()
        self._preview_surface('_record_applied').write({
            'state': 'applied',
            'applied_at': fields.Datetime.now(),
        })
        return self

    # ------------------------------------------------------------------
    # The one public confirmation action (D-015-5)
    # ------------------------------------------------------------------

    def action_confirm_export_preview(self):
        """Reviewer/Administrator confirmation. The only door to an apply.

        Re-verified rather than trusted: the preview is re-checked for
        expiry under a row lock at confirmation time, so a preview that
        went stale between rendering and clicking is refused instead of
        being confirmed on the strength of a screen the operator was
        looking at a minute ago.
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
                'Only a Shopify Connector Reviewer or Administrator may '
                'confirm a product export.'
            )
        locked = self.try_lock_for_update()
        if not locked:
            raise UserError(
                'This export preview is being processed by another worker.'
            )
        locked.invalidate_recordset()
        if locked.state != 'previewed':
            raise UserError(
                'Only a previewed, unconfirmed export can be confirmed.'
            )
        if locked._is_expired():
            locked._record_expiry('confirmation_attempt_on_stale_preview')
            raise UserError(
                'This preview is no longer current — the product changed '
                'since it was taken. Run a fresh preview and review it '
                'again.'
            )
        if not (locked.apply_plan or {}).get('steps'):
            raise UserError(
                'This preview contains nothing that can be exported. '
                'Nothing was confirmed.'
            )
        locked._preview_surface('_record_confirmation').write({
            'state': 'confirmed',
            'confirmed_uid': self.env.uid,
            'confirmed_at': fields.Datetime.now(),
        })
        locked.store_id._create_lifecycle_audit_job(
            'Export preview confirmed preview_id=%d template_id=%d '
            'path=%s actor_uid=%d steps=%d blocked=%d' % (
                locked.id,
                locked.product_template_id.id,
                locked.export_path,
                self.env.uid,
                len(locked.apply_plan.get('steps') or []),
                len((locked.blocked_differences or {}).get('items') or []),
            )
        )
        return self.env[
            'shopify.connector.product.export.service'
        ]._enqueue_apply(locked)

    # ------------------------------------------------------------------
    # SEC-3 (#197): same-store consistency with the connector parent.
    # ------------------------------------------------------------------

    @api.model
    def _sec3_parent_scope_relations(self):
        return (('product_template_binding_id', 'store'),)

    @api.constrains('store_id', 'product_template_binding_id')
    def _check_sec3_parent_scope(self):
        self._sec3_check_parent_scope()

    def init(self):
        super().init()
        self._sec3_quarantine_scope_mismatches()
