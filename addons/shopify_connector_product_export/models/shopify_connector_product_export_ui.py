"""Read-only projection service behind the U3 export preview/diff surface.

What this is, and what it deliberately is not
---------------------------------------------

The premium UX master specification assigns S7 (the export preview/diff) an
Owl surface. An Owl component needs a shaped, presentation-ready payload; the
alternative is a template that reaches into a raw `Json` field and decides for
itself what a "refusal" or a "removal" is. That is business logic in a
template, and it is exactly what the U3 locked prompt forbids.

So this is one bounded, read-only aggregate — the U0 dashboard pattern
(`shopify.connector.ui.dashboard`) applied to one preview record. It is an
`AbstractModel`: no table, no ACL row, no persistent state. It owns exactly
one public RPC entrypoint, and it is a **pure projection**:

* it performs no write, no `create`, no `unlink`, no `commit` and no enqueue;
* it issues no Shopify request and reads no credential;
* it computes no guard, no payload and no ownership decision — every value it
  returns was already decided and recorded by the export service when the
  preview was taken;
* it runs as the **current user**, so a caller who cannot read a preview
  cannot read it through here either.

Why the sections are shaped here rather than in the component
--------------------------------------------------------------

Two of them carry meaning that must not be re-derived by a renderer:

* **`tag_replacement`** is the one place in the whole export where confirming
  a change *removes* something that exists on Shopify. It arrives with the
  removals already enumerated by name (2026-07 `productUpdate` overwrites the
  tag list), and this service passes them through as their own section with
  their own severity so no template can demote them to a `from -> to` row.
* **`refusals`** are differences the connector will not act on. They are
  never executable and never confirmable. Rendering them next to the
  executable plan without a severity of their own is how a reviewer comes to
  believe the connector is about to do them.

Everything else is labels, counts and ordering.
"""

from odoo import _, api, models
from odoo.exceptions import AccessError
from odoo.tools.translate import LazyTranslate

_lt = LazyTranslate(__name__)

# Plain-language labels for the refusal kinds the export service records.
# Keeping them here rather than in the template means an unknown kind renders
# as itself instead of as a blank row -- an unrecognised refusal must still be
# visible, because a refusal nobody can see is the failure this whole surface
# exists to prevent.
REFUSAL_LABELS = {
    'too_many_options': _lt('More Shopify options than Shopify allows'),
    'too_many_variants': _lt('More variants than one export job carries'),
    'remote_option_divergence': _lt('Shopify option structure differs'),
    'variant_create_withheld': _lt('New variants withheld'),
    'bound_product_missing_remotely': _lt('Bound Shopify product is gone'),
    'bound_variant_missing_remotely': _lt('A bound Shopify variant is gone'),
    'unowned_remote_variant': _lt('Shopify variant this connector does not own'),
    'custom_id_already_bound_remotely': _lt('Already exported to this store'),
    'duplicate_sku_on_shopify': _lt('SKU already exists on Shopify'),
}

# Step -> operator-facing label. The raw job types are internal vocabulary and
# must never be the thing a reviewer reads.
STEP_LABELS = {
    'product_export_binding_namespace': _lt('Establish the connector binding id'),
    'product_export_create': _lt('Create the product on Shopify'),
    'product_export_update': _lt('Update product details'),
    'product_export_variants_update': _lt('Update variants'),
    'product_export_variants_create': _lt('Add new variants'),
    'product_export_media_stage': _lt('Append an image'),
}

STEP_STATE_TONE = {
    'pending': 'neutral',
    'done': 'success',
    'blocked': 'danger',
}


class ShopifyConnectorProductExportUi(models.AbstractModel):
    _name = 'shopify.connector.product.export.ui'
    _description = 'Shopify Connector Export Preview (read-only projection)'

    # ------------------------------------------------------------------
    # Public RPC entrypoint
    # ------------------------------------------------------------------

    @api.model
    def get_export_preview_data(self, preview_id):
        """Project one export preview into a render-ready payload.

        Read as the current user on purpose — `browse` + field access go
        through the ordinary ACL and the SEC-3 company record rules, so this
        cannot become a way to read a preview belonging to another company's
        store.
        """
        # The AUDITOR floor, not the User role — and the difference matters.
        # `group_shopify_connector_user` IMPLIES operator and reviewer, so the
        # implication runs downward: a User is a reviewer, but a reviewer is
        # not a User. Gating this read on `..._user` would refuse the exact
        # role whose job is to review an export. `..._auditor` is the read
        # floor every connector role implies, and is the same gate the U0
        # dashboard aggregate uses for the same reason.
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_auditor'
        ):
            raise AccessError(_(
                'The Shopify export review surface is only available to '
                'Shopify Connector users.'
            ))
        preview = self.env[
            'shopify.connector.product.export.preview'
        ].browse(int(preview_id)).exists()
        if not preview:
            raise AccessError(_('This export preview is not available.'))

        diff = preview.diff or {}
        plan = preview.apply_plan or {}
        refusals = (preview.blocked_differences or {}).get('items') or []

        return {
            'id': preview.id,
            'state': preview.state,
            'state_label': dict(
                preview._fields['state']._description_selection(self.env)
            ).get(preview.state, preview.state),
            'state_tone': self._state_tone(preview.state),
            'export_path': preview.export_path,
            'product_name': preview.product_template_id.display_name,
            'store_name': preview.store_id.display_name,
            'previewed_at': preview.previewed_at,
            'expires_at': preview.expires_at,
            'confirmed_by': preview.confirmed_uid.display_name or '',
            # Rendered as a live fact, not a cached one: an expired preview
            # must never present a confirm affordance, and `_is_expired`
            # is the same predicate the server enforces on confirmation.
            'is_expired': preview._is_expired(),
            'can_confirm': self._can_confirm(preview),
            'sections': self._sections(diff),
            'tag_replacement': self._tag_replacement(diff),
            'media': self._media(diff),
            'untouched': self._untouched(diff),
            'refusals': self._refusals(refusals),
            'plan': self._plan(plan),
        }

    # ------------------------------------------------------------------
    # Projection helpers — labels, tones and ordering only
    # ------------------------------------------------------------------

    @api.model
    def _state_tone(self, state):
        return {
            'previewed': 'warning',
            'confirmed': 'info',
            'applying': 'info',
            'applied': 'success',
            'expired': 'neutral',
            'blocked': 'danger',
        }.get(state, 'neutral')

    @api.model
    def _can_confirm(self, preview):
        """Whether THIS user could confirm THIS preview right now.

        Mirrors `action_confirm_export_preview` rather than guessing: same
        Administrator capability, same state, same expiry, same empty-plan rule. The server
        remains the authority — this only decides whether to render a button
        that would otherwise fail. A UI that offers a control the backend
        refuses is a UI that teaches operators to distrust it.
        """
        if preview.state != 'previewed' or preview._is_expired():
            return False
        if not (preview.apply_plan or {}).get('steps'):
            return False
        return self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        )

    @api.model
    def _sections(self, diff):
        """The executable difference, grouped the way a reviewer reads it."""
        sections = []
        scalars = [
            {
                'field': change.get('field'),
                'from': self._render_value(change.get('from')),
                'to': self._render_value(change.get('to')),
            }
            for change in diff.get('scalars') or []
        ]
        if scalars:
            sections.append({
                'key': 'scalars',
                'title': _('Product details'),
                'rows': scalars,
            })
        variants_update = [
            {
                'name': entry.get('display_name') or '',
                'changes': [
                    {
                        'field': change.get('field'),
                        'from': self._render_value(change.get('from')),
                        'to': self._render_value(change.get('to')),
                    }
                    for change in entry.get('changes') or []
                ],
            }
            for entry in diff.get('variants_update') or []
        ]
        if variants_update:
            sections.append({
                'key': 'variants_update',
                'title': _('Variants to update'),
                'variants': variants_update,
            })
        variants_create = [
            {'name': entry.get('display_name') or ''}
            for entry in diff.get('variants_create') or []
        ]
        if variants_create:
            sections.append({
                'key': 'variants_create',
                'title': _('Variants to add'),
                'variants': variants_create,
            })
        return sections

    @api.model
    def _render_value(self, value):
        """One string per cell, with an empty value that reads as empty.

        A bare `False`/`None` rendered into a diff cell looks like the literal
        word "false" to an operator, which is a different claim than "this
        field is empty".
        """
        if value is None or value is False:
            return _('(empty)')
        if isinstance(value, (list, tuple)):
            return ', '.join(str(item) for item in value) or _('(empty)')
        text = str(value)
        return text if text else _('(empty)')

    @api.model
    def _tag_replacement(self, diff):
        """The one removal this export performs, kept as its own section."""
        raw = diff.get('tag_replacement') or {}
        removed = list(raw.get('removed') or [])
        return {
            'applies': bool(raw.get('applies')),
            # Severity rises only when tags are actually being removed. A tag
            # change that only ADDS is not a removal and must not be dressed
            # as one -- crying wolf on every tag edit is how a real removal
            # stops being read.
            'removes': bool(removed),
            'removed': removed,
            'resulting': list(raw.get('resulting') or []),
            'note': raw.get('note') or '',
        }

    @api.model
    def _media(self, diff):
        media = diff.get('media') or {}
        return {
            'exported': bool(media.get('exported')),
            'reason': media.get('reason') or '',
            'appends': [
                {
                    'filename': entry.get('filename') or '',
                    'role': entry.get('role') or '',
                    'resuming': bool(entry.get('resuming')),
                }
                for entry in media.get('appends') or []
            ],
        }

    @api.model
    def _untouched(self, diff):
        untouched = diff.get('untouched') or {}
        present = []
        for key, label in (
            ('collections', _('Collections')),
            ('metafields', _('Merchant metafields')),
            ('existing_media', _('Existing images')),
        ):
            if key in untouched:
                present.append({
                    'key': key,
                    'label': label,
                    # `True` means the merchant HAS some, which is exactly
                    # when "left untouched" is a claim worth making.
                    'present': bool(untouched.get(key)),
                })
        return {'items': present, 'note': untouched.get('note') or ''}

    @api.model
    def _refusals(self, items):
        rendered = []
        for item in items:
            kind = item.get('kind') or ''
            label = REFUSAL_LABELS.get(kind)
            rendered.append({
                'kind': kind,
                'label': self.env._(label) if label else kind or _('Refused'),
                'detail': item.get('detail') or '',
            })
        return rendered

    @api.model
    def _plan(self, plan):
        steps = plan.get('steps') or []
        rendered = []
        for index, step in enumerate(steps, start=1):
            step_type = step.get('step') or ''
            rendered.append({
                'index': index,
                'step': step_type,
                'label': self.env._(STEP_LABELS[step_type])
                if step_type in STEP_LABELS else step_type,
                'state': step.get('state') or 'pending',
                'tone': STEP_STATE_TONE.get(step.get('state'), 'neutral'),
            })
        done = len([step for step in rendered if step['state'] == 'done'])
        return {
            'steps': rendered,
            'total': len(rendered),
            'done': done,
            # Integer percent, computed here so the template carries no
            # arithmetic and the progress bar cannot disagree with the count.
            'percent': int(round(100.0 * done / len(rendered))) if rendered else 0,
        }
