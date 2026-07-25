from odoo import api, fields, models


class ShopifyConnectorCustomerBinding(models.Model):
    """Binds one Shopify Customer to one Odoo ``res.partner``.

    Extends the core ``shopify.connector.binding.mixin`` contract
    (DEC-013 per-domain-concrete-on-core-contract shape). Import-only
    (Task 011): every field below is populated by the read-only importer
    service (``shopify_connector_customer_importer.py``) -- this model
    itself performs no Shopify call and has no export/write-back
    behaviour.

    ``status = 'review'`` denotes lifecycle review of an already-real
    binding row that already carries a confirmed ``partner_id`` -- it is
    never a placeholder for an unresolved, still-ambiguous candidate
    selection (MBQ-55 §7.1.A). An ambiguous match never creates a row of
    this model at all (final prompt §8.1 rule 6) -- the outcome is
    represented entirely at the job level instead.
    """

    _name = 'shopify.connector.customer.binding'
    _inherit = 'shopify.connector.binding.mixin'
    _description = 'Shopify Connector Customer Binding'

    # SEC-3 (#197): opt in to Odoo 19's native company consistency check
    # (`odoo/orm/models.py` L451/L4516/L4743). Together with `check_company=True`
    # on the business relation below, a store can only ever bind a record of its
    # own company -- enforced on create AND write, and under `sudo()`.
    _check_company_auto = True

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        required=True,
        index=True,
        ondelete='restrict',
        check_company=True,
    )
    # Imported snapshot fields (readonly, informational/audit only --
    # never a second source of truth for matching; matching always reads
    # the live incoming payload against res.partner.email via
    # partner_id, never these snapshots -- MBQ-55 §7.1.D).
    shopify_display_name = fields.Char(
        readonly=True,
        groups=(
            'shopify_connector_core.group_shopify_connector_reviewer,'
            'shopify_connector_core.group_shopify_connector_admin'
        ),
    )
    shopify_email_snapshot = fields.Char(
        readonly=True,
        groups=(
            'shopify_connector_core.group_shopify_connector_reviewer,'
            'shopify_connector_core.group_shopify_connector_admin'
        ),
    )
    shopify_phone_snapshot = fields.Char(
        readonly=True,
        groups=(
            'shopify_connector_core.group_shopify_connector_reviewer,'
            'shopify_connector_core.group_shopify_connector_admin'
        ),
    )
    pii_snapshot_masked = fields.Char(
        compute='_compute_pii_snapshot_masked',
        compute_sudo=True,
    )
    shopify_last_imported_at = fields.Datetime(readonly=True)

    def _odoo_binding_field_name(self):
        return 'partner_id'

    @api.model
    def _additional_protected_binding_fields(self):
        return super()._additional_protected_binding_fields() | frozenset((
            'shopify_display_name',
            'shopify_email_snapshot',
            'shopify_phone_snapshot',
            'shopify_last_imported_at',
        ))

    def _pii_snapshot_fields(self):
        return [
            'shopify_display_name',
            'shopify_email_snapshot',
            'shopify_phone_snapshot',
        ]

    @api.depends(
        'shopify_display_name',
        'shopify_email_snapshot',
        'shopify_phone_snapshot',
    )
    def _compute_pii_snapshot_masked(self):
        for binding in self:
            email = binding.shopify_email_snapshot or ''
            phone = binding.shopify_phone_snapshot or ''
            display_name = binding.shopify_display_name or ''
            if email and email != '***':
                local, separator, domain = email.partition('@')
                host, dot, suffix = domain.rpartition('.')
                if separator and host:
                    binding.pii_snapshot_masked = '%s***@%s***%s%s' % (
                        local[:1] or '*',
                        host[:1] or '*',
                        dot,
                        suffix,
                    )
                else:
                    binding.pii_snapshot_masked = '%s***' % (
                        email[:1] or '*',
                    )
            elif phone and phone != '***':
                digits = ''.join(char for char in phone if char.isdigit())
                binding.pii_snapshot_masked = '***%s' % digits[-2:]
            elif display_name and display_name != '***':
                binding.pii_snapshot_masked = '%s***' % display_name[:1]
            elif email or phone or display_name:
                binding.pii_snapshot_masked = '***'
            else:
                binding.pii_snapshot_masked = False

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A customer binding with this Shopify GID already exists for '
        'this store.',
    )
    _store_partner_uniq = models.Constraint(
        'UNIQUE(store_id, partner_id)',
        'This res.partner is already bound for this store.',
    )
