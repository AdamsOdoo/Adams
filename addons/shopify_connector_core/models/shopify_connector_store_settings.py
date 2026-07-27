from odoo import fields, models


class ShopifyConnectorStoreSettings(models.Model):
    """Store-scoped feature flags and domain-enablement configuration.

    Kept as its own model, not folded onto ``shopify.connector.store``,
    so domain modules can cleanly extend it via classic Odoo ``_inherit``
    without adding fields to the busier store record
    (core-naming-schema-planning.md §3/§5).
    """

    _name = 'shopify.connector.store.settings'
    _description = 'Shopify Connector Store Settings'

    store_id = fields.Many2one(
        comodel_name='shopify.connector.store',
        required=True,
        index=True,
        readonly=True,
        ondelete='restrict',
    )
    # SEC-3 (#197): company is inherited from the owning store and is never an
    # independent selector. Stored so record rules, searches and grouped reads
    # filter on it in SQL; readonly so it can never diverge from its store.
    company_id = fields.Many2one(
        comodel_name='res.company',
        related='store_id.company_id',
        store=True,
        index=True,
        readonly=True,
    )
    product_domain_enabled = fields.Boolean(default=False)
    sale_domain_enabled = fields.Boolean(default=False)
    inventory_domain_enabled = fields.Boolean(default=False)
    fulfillment_domain_enabled = fields.Boolean(default=False)
    product_first_sync_source = fields.Selection(
        selection=[
            ('shopify_source', 'Shopify Source'),
            ('odoo_source', 'Odoo Source'),
            ('both_match_first', 'Both, Match First'),
        ],
    )
    price_source_of_truth = fields.Selection(
        selection=[
            ('odoo_authoritative', 'Odoo Authoritative'),
            ('shopify_authoritative', 'Shopify Authoritative'),
        ],
    )
    notification_default_enabled = fields.Boolean(default=False)
    # SEC-2: this was `pii_snapshot_retention_days`, which drove *both* the
    # removed customer-binding masking and the retained log redaction. With
    # masking gone (packet §D Option 1) the setting is renamed to what it
    # actually still governs -- log/audit evidence redaction. No business
    # record is ever rewritten on this schedule.
    log_redaction_retention_days = fields.Integer(
        default=0,
        help=(
            'Number of days to retain unredacted PII-bearing entries inside '
            'stored connector log payloads. Zero retains log payloads '
            'unredacted indefinitely; 365 days is the recommended MVP '
            'operating value. This never alters a customer, order, or '
            'binding record.'
        ),
    )

    # ------------------------------------------------------------------
    # S1: the guided setup wizard's durable progress
    # ------------------------------------------------------------------
    #
    # The wizard keeps NO state of its own. Every durable business choice it
    # collects already has an owning field on this record or on the store, and
    # writing them anywhere else would create a second source of truth that
    # the settings form could silently disagree with.
    #
    # What is genuinely new is the *progress*: which step was last completed,
    # and who finished or re-ran setup. That belongs here for the same reason
    # the flags do -- it is per-store configuration, it inherits the store's
    # company through the related field above, and it is therefore covered by
    # the SEC-3 record rules already on this model. Browser storage is never
    # the source of truth: a resume that lived in localStorage would resume
    # differently on a different machine, and would tell a second
    # administrator nothing about what the first one had already done.
    setup_wizard_step = fields.Integer(
        default=1,
        readonly=True,
        help='The furthest setup-wizard step this store has completed. '
             'Written only by the setup service.',
    )
    setup_completed_at = fields.Datetime(readonly=True)
    setup_completed_uid = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        ondelete='set null',
    )
    setup_last_rerun_at = fields.Datetime(readonly=True)
    setup_last_rerun_uid = fields.Many2one(
        comodel_name='res.users',
        readonly=True,
        ondelete='set null',
    )

    _store_id_uniq = models.Constraint(
        'UNIQUE(store_id)',
        'Only one settings record is allowed per store.',
    )
