import re

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from ..tools.redaction import redact


_AUDIT_EMAIL_RE = re.compile(
    r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
)
_AUDIT_PHONE_RE = re.compile(r'(?<!\w)\+?\d[\d\s().-]{6,}\d(?!\w)')

_AUTOMATIC_BINDING_FIELDS = frozenset((
    'id',
    'display_name',
    'create_uid',
    'create_date',
    'write_uid',
    'write_date',
))
_COMMON_PROTECTED_BINDING_FIELDS = frozenset((
    'store_id',
    'shopify_gid',
    'status',
    'match_key',
    'matched_by_uid',
    'matched_at',
    'override_uid',
    'override_at',
    'override_previous_candidate',
))


class ShopifyConnectorBindingMixin(models.AbstractModel):
    """The per-domain-concrete-on-core-contract shape (DEC-013)."""

    _name = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Binding Mixin'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        ondelete='restrict',
    )
    shopify_gid = fields.Char(required=True, index=True, readonly=True)
    status = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('stale', 'Stale'),
            ('manually_overridden', 'Manually Overridden'),
            ('review', 'Review'),
        ],
        required=True,
        index=True,
        default='active',
    )
    match_key = fields.Selection(
        selection=[
            ('existing_binding', 'Existing Binding'),
            ('sku_reference', 'SKU Reference'),
            ('barcode', 'Barcode'),
            ('email', 'Email'),
            ('manual', 'Manual'),
        ],
        readonly=True,
    )
    matched_by_uid = fields.Many2one(comodel_name='res.users', readonly=True)
    matched_at = fields.Datetime(readonly=True)
    override_uid = fields.Many2one(comodel_name='res.users', readonly=True)
    override_at = fields.Datetime(readonly=True)
    override_previous_candidate = fields.Char(readonly=True)

    @api.model
    def _odoo_binding_field_name(self):
        """Concrete binding's fixed Odoo-record Many2one, or fail closed."""
        return False

    @api.model
    def _pii_snapshot_fields(self):
        """PII-bearing snapshots declared by a concrete binding model."""
        return []

    @api.model
    def _additional_protected_binding_fields(self):
        """Concrete structural and system-maintained snapshot fields.

        Every concrete binding must return all of its additional stored
        connector fields here. Generic non-su create/write is denied for
        the resulting union, and an omitted stored field fails closed.
        """
        return frozenset()

    @api.model
    def _protected_binding_fields(self):
        fields_set = set(_COMMON_PROTECTED_BINDING_FIELDS)
        odoo_field = self._odoo_binding_field_name()
        if odoo_field:
            fields_set.add(odoo_field)
        fields_set.update(self._additional_protected_binding_fields())
        return frozenset(fields_set)

    @api.model
    def _assert_binding_field_classification(self):
        """Fail closed when a concrete binding omits a stored field.

        Odoo's automatic access-log fields are ORM-maintained. Every other
        stored field on a concrete binding is identity/structure or connector
        system state/provenance/snapshot and therefore must be protected.
        Computed non-stored fields are not a generic write surface.
        """
        protected_fields = self._protected_binding_fields()
        unknown_fields = protected_fields - set(self._fields)
        unclassified_fields = {
            field_name
            for field_name, field in self._fields.items()
            if field.store
            and field_name not in _AUTOMATIC_BINDING_FIELDS
            and field_name not in protected_fields
        }
        if unknown_fields or unclassified_fields:
            details = []
            if unknown_fields:
                details.append(
                    'unknown protected fields: %s'
                    % ', '.join(sorted(unknown_fields))
                )
            if unclassified_fields:
                details.append(
                    'unclassified stored fields: %s'
                    % ', '.join(sorted(unclassified_fields))
                )
            raise UserError(
                "Binding field classification is incomplete (%s)."
                % '; '.join(details)
            )

    @api.model_create_multi
    def create(self, vals_list):
        self._assert_binding_field_classification()
        if not self.env.su:
            protected_fields = self._protected_binding_fields()
            touched = sorted(set().union(
                *(set(vals) & protected_fields for vals in vals_list)
            ))
            if touched:
                raise AccessError(
                    "Binding identity, structure, system state, provenance, "
                    "and imported snapshots cannot be supplied through "
                    "generic create(). Use a sanctioned connector service. "
                    "Protected fields: %s" % ', '.join(touched)
                )
        return super().create(vals_list)

    def write(self, vals):
        self._assert_binding_field_classification()
        protected = sorted(set(vals) & self._protected_binding_fields())
        if protected and not self.env.su:
            raise AccessError(
                "Binding identity, structure, system state, provenance, and "
                "imported snapshots can only be changed through a sanctioned "
                "connector service. "
                "Protected fields: %s" % ', '.join(protected)
            )
        return super().write(vals)

    @api.model
    def _audit_safe_reason(self, reason):
        safe = redact(reason.strip())
        safe = _AUDIT_EMAIL_RE.sub('[redacted-email]', safe)
        safe = _AUDIT_PHONE_RE.sub('[redacted-phone]', safe)
        return safe[:500]

    def action_override_binding(self, new_record_id, reason=False):
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
                "Only a Shopify Connector Reviewer or Administrator may "
                "override a binding."
            )
        if not isinstance(reason, str) or not reason.strip():
            raise UserError("A non-empty binding-override reason is required.")
        if (
            isinstance(new_record_id, bool)
            or not isinstance(new_record_id, int)
            or new_record_id <= 0
        ):
            raise UserError("The new bound-record id must be a positive integer.")

        field_name = self._odoo_binding_field_name()
        if not field_name or field_name not in self._fields:
            raise UserError("This binding's identity is not overridable.")
        field = self._fields[field_name]
        if field.type != 'many2one' or not field.comodel_name:
            raise UserError("The binding identity seam is not a fixed Many2one.")

        current_record = self[field_name]
        target = self.env[field.comodel_name].browse(new_record_id).exists()
        if not target:
            raise UserError(
                "The requested record does not exist in %s." % field.comodel_name
            )
        target.ensure_one()

        current_company = (
            current_record.company_id
            if current_record and 'company_id' in current_record._fields
            else False
        )
        target_company = (
            target.company_id if 'company_id' in target._fields else False
        )
        for label, company in (
            ('current bound record', current_company),
            ('proposed target record', target_company),
        ):
            if company and company != self.env.company:
                raise UserError(
                    "The %s belongs to a different company." % label
                )
        if (
            current_company
            and target_company
            and current_company != target_company
        ):
            raise UserError(
                "Current and proposed binding records belong to different "
                "companies."
            )

        collision = self.search([
            ('id', '!=', self.id),
            ('store_id', '=', self.store_id.id),
            (field_name, '=', target.id),
        ], limit=1)
        if collision:
            raise UserError(
                "The proposed record is already bound for this Shopify store."
            )

        old_record_id = current_record.id
        safe_reason = self._audit_safe_reason(reason)
        self.sudo().write({
            field_name: target.id,
            'status': 'manually_overridden',
            'match_key': 'manual',
            'override_previous_candidate': '%s,%d' % (
                field.comodel_name, old_record_id,
            ),
            'override_uid': self.env.uid,
            'override_at': fields.Datetime.now(),
        })
        self.store_id._create_lifecycle_audit_job(
            'Binding override model=%s binding_id=%d old_record_id=%d '
            'new_record_id=%d actor_uid=%d reason=%s' % (
                self._name,
                self.id,
                old_record_id,
                target.id,
                self.env.uid,
                safe_reason,
            )
        )
        return True
