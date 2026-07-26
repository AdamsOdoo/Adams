from odoo import api, fields, models

# The sentinel the pre-SEC-2 retention sweep wrote over customer snapshots.
# SEC-2 removed the code that writes it; this constant exists only so already
# masked rows can be *recognised* and flagged for refresh (packet §E). It is
# never written to a business record by any code path.
LEGACY_MASKED_PII_VALUE = '***'


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
    # SEC-2 (packet §C): both customer-facing roles read the raw operational
    # snapshot. The former field-level `groups=` restriction is removed --
    # access is now governed by the ordinary ACL / record-rule / company
    # checks alone, and there is no masked display variant of these fields.
    shopify_display_name = fields.Char(readonly=True)
    shopify_email_snapshot = fields.Char(readonly=True)
    shopify_phone_snapshot = fields.Char(readonly=True)
    shopify_last_imported_at = fields.Datetime(readonly=True)
    # SEC-2 §E: masking was irreversible, so rows masked before SEC-2 cannot
    # be restored. They are marked as requiring refresh/re-import rather than
    # reconstructed -- no original value is ever inferred from a masked
    # string. Non-stored: it is a live read of the snapshot fields, so it can
    # never disagree with them.
    pii_snapshot_refresh_required = fields.Boolean(
        string='Snapshot Refresh Required',
        compute='_compute_pii_snapshot_refresh_required',
        # Searchable so the operator surface can filter to exactly the rows
        # that need a re-import. Without this the flag is visible one record
        # at a time, which is useless for remediating a sweep that may have
        # touched thousands. The search seam is read-only and adds no state.
        search='_search_pii_snapshot_refresh_required',
        help=(
            'This customer snapshot was irreversibly masked by the '
            'pre-SEC-2 retention sweep. The original values cannot be '
            'recovered; re-import the customer from Shopify to restore them.'
        ),
    )

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
    def _compute_pii_snapshot_refresh_required(self):
        masked_sentinel = LEGACY_MASKED_PII_VALUE
        for binding in self:
            binding.pii_snapshot_refresh_required = any(
                binding[field_name] == masked_sentinel
                for field_name in binding._pii_snapshot_fields()
            )

    def _search_pii_snapshot_refresh_required(self, operator, value):
        """Translate the computed flag into a domain over the real columns.

        Deliberately derived from `_pii_snapshot_fields()` rather than a
        hardcoded list, so the search can never fall out of step with the
        compute above or with a future snapshot field.
        """
        if operator not in ('=', '!='):
            raise NotImplementedError(
                'Only equality is supported on this flag.'
            )
        masked = [
            (field_name, '=', LEGACY_MASKED_PII_VALUE)
            for field_name in self._pii_snapshot_fields()
        ]
        # "any field is masked" -> an OR chain over the field terms.
        any_masked = ['|'] * (len(masked) - 1) + masked
        wants_masked = bool(value) == (operator == '=')
        return any_masked if wants_masked else ['!'] + any_masked

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A customer binding with this Shopify GID already exists for '
        'this store.',
    )
    _store_partner_uniq = models.Constraint(
        'UNIQUE(store_id, partner_id)',
        'This res.partner is already bound for this store.',
    )
