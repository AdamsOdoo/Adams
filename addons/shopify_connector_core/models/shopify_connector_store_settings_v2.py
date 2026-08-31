"""Temporary, audited store-scoped V2 migration controls.

These fields select coexistence paths; they never weaken authorization,
mutation verification, API-version pinning, or tenant/generation fences.
They are removed only after the documented all-V2 soak period.
"""

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError

from ..tools.redaction import redact


V2_UI_MODE_SELECTION = [
    ('legacy', 'Legacy'),
    ('pilot', 'V2 Pilot'),
    ('default', 'V2 Default'),
]
V2_GATEWAY_MODE_SELECTION = [
    ('legacy', 'Legacy'),
    ('compare_reads', 'Compare Reads'),
    ('v2', 'V2'),
]
V2_RUNTIME_MODE_SELECTION = [
    ('legacy', 'Legacy'),
    ('read_only', 'Read Only'),
    ('subscriptions', 'Subscriptions'),
    ('inventory', 'Inventory'),
    ('product_export', 'Product Export'),
    ('fulfillment', 'Fulfillment'),
    ('all', 'All V2'),
]

V2_MODE_FIELDS = frozenset((
    'v2_ui_mode', 'v2_gateway_mode', 'v2_runtime_mode',
    'configuration_generation',
))
V2_MODE_KEYS = {
    'v2_ui_mode': frozenset(key for key, _label in V2_UI_MODE_SELECTION),
    'v2_gateway_mode': frozenset(
        key for key, _label in V2_GATEWAY_MODE_SELECTION
    ),
    'v2_runtime_mode': frozenset(
        key for key, _label in V2_RUNTIME_MODE_SELECTION
    ),
}
_V2_MODE_SENTINEL_KEY = 'shopify_v2_mode_service_sentinel'
_V2_MODE_SENTINEL = object()


class ShopifyConnectorStoreSettingsV2(models.Model):
    _inherit = 'shopify.connector.store.settings'

    configuration_generation = fields.Integer(
        required=True,
        default=0,
        index=True,
        readonly=True,
    )
    v2_ui_mode = fields.Selection(
        selection=V2_UI_MODE_SELECTION,
        required=True,
        default='legacy',
        readonly=True,
    )
    v2_gateway_mode = fields.Selection(
        selection=V2_GATEWAY_MODE_SELECTION,
        required=True,
        default='legacy',
        readonly=True,
    )
    v2_runtime_mode = fields.Selection(
        selection=V2_RUNTIME_MODE_SELECTION,
        required=True,
        default='legacy',
        readonly=True,
    )

    _configuration_generation_non_negative = models.Constraint(
        'CHECK(configuration_generation >= 0)',
        'The connector configuration generation cannot be negative.',
    )

    @api.model
    def _v2_mode_surface(self):
        return self.sudo().with_context(**{
            _V2_MODE_SENTINEL_KEY: _V2_MODE_SENTINEL,
        })

    @api.model
    def _v2_mode_surface_is_open(self):
        return (
            self.env.su
            and self.env.context.get(_V2_MODE_SENTINEL_KEY)
            is _V2_MODE_SENTINEL
        )

    def write(self, vals):
        protected = V2_MODE_FIELDS.intersection(vals)
        if protected and not self._v2_mode_surface_is_open():
            raise AccessError(
                'V2 migration modes and their generation can only be '
                'changed by the audited connector service.'
            )
        return super().write(vals)

    def _set_v2_modes_service(
        self, values, *, reason, expected_configuration_generation
    ):
        """Apply one audited compare-and-set mode change.

        This private service is intentionally the only mutation surface.  It
        checks the caller before elevating, locks the one settings row, and
        increments a configuration generation so already-admitted work can
        reject a policy change instead of silently crossing it.
        """
        self.ensure_one()
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may change V2 modes.'
            )
        if self.company_id != self.env.company:
            raise AccessError(
                'V2 modes can only be changed in the store active company.'
            )
        if not isinstance(values, dict) or not values:
            raise ValidationError('At least one V2 mode change is required.')
        unknown = set(values) - set(V2_MODE_KEYS)
        if unknown:
            raise ValidationError(
                'Unknown V2 mode field: %s.' % ', '.join(sorted(unknown))
            )
        normalized = {}
        for field_name, value in values.items():
            if value not in V2_MODE_KEYS[field_name]:
                raise ValidationError(
                    'Unsupported value for %s.' % field_name
                )
            normalized[field_name] = value
        if isinstance(expected_configuration_generation, bool):
            raise ValidationError(
                'The expected configuration generation must be an integer.'
            )
        try:
            expected = int(expected_configuration_generation)
        except (TypeError, ValueError) as exc:
            raise ValidationError(
                'The expected configuration generation must be an integer.'
            ) from exc
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError('A V2 mode-change reason is required.')
        safe_reason = redact(reason.strip())[:512]

        self.env.cr.execute(
            'SELECT configuration_generation '
            'FROM shopify_connector_store_settings '
            'WHERE id = %s FOR UPDATE',
            [self.id],
        )
        row = self.env.cr.fetchone()
        if not row:
            raise ValidationError('The store settings record no longer exists.')
        current_generation = int(row[0] or 0)
        if current_generation != expected:
            raise ValidationError(
                'The store configuration changed; reload before changing '
                'migration modes.'
            )
        self.invalidate_recordset(
            list(V2_MODE_KEYS) + ['configuration_generation'],
        )
        changed = {
            field_name: value
            for field_name, value in normalized.items()
            if getattr(self, field_name) != value
        }
        if not changed:
            return self

        before = {
            field_name: getattr(self, field_name)
            for field_name in sorted(changed)
        }
        next_generation = current_generation + 1
        changed['configuration_generation'] = next_generation
        self._v2_mode_surface().browse(self.id).write(changed)
        after = {
            field_name: normalized[field_name]
            for field_name in sorted(normalized)
            if field_name in before
        }
        self.store_id._create_lifecycle_audit_job(
            'V2 migration modes changed by actor_uid=%d generation=%d '
            'before=%s after=%s reason=%s' % (
                self.env.uid,
                next_generation,
                before,
                after,
                safe_reason,
            )
        )
        return self
