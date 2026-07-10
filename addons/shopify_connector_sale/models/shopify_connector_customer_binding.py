from odoo import fields, models


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

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        required=True,
        index=True,
        ondelete='restrict',
    )
    # Imported snapshot fields (readonly, informational/audit only --
    # never a second source of truth for matching; matching always reads
    # the live incoming payload against res.partner.email via
    # partner_id, never these snapshots -- MBQ-55 §7.1.D).
    shopify_display_name = fields.Char(readonly=True)
    shopify_email_snapshot = fields.Char(readonly=True)
    shopify_phone_snapshot = fields.Char(readonly=True)
    shopify_last_imported_at = fields.Datetime(readonly=True)

    _store_shopify_gid_uniq = models.Constraint(
        'UNIQUE(store_id, shopify_gid)',
        'A customer binding with this Shopify GID already exists for '
        'this store.',
    )
    _store_partner_uniq = models.Constraint(
        'UNIQUE(store_id, partner_id)',
        'This res.partner is already bound for this store.',
    )
