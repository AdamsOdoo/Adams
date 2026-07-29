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
    # WHAT IS AUTHORITATIVE, AND WHAT IS ONLY DISPLAY (Wave 5).
    #
    # `setup_wizard_step_key` is the durable resume point. It is a SEMANTIC
    # step key -- `identity`, `location_mapping`, `final_readiness` -- and it
    # is what persistence, validation, navigation, deep links, conditional
    # skipping and resume are all evaluated against.
    #
    # `setup_wizard_step` is the same position as an integer, kept in step
    # with the key by the setup service and retained for DISPLAY and for
    # ordering only. It was the authoritative value before Wave 5, which is
    # exactly the defect being closed: inserting one step into the accepted
    # order silently renumbered every later step, so a stored `8` meant one
    # thing before the change and a different thing after it, and every deep
    # link, guard and resume that compared a number was wrong at once.
    #
    # A row written before Wave 5 has no key. `19.0.1.15.0/post-migrate.py`
    # translates its number through the OLD eleven-step order, and the setup
    # service applies the identical translation at read time for any row the
    # migration did not reach (a database restored from an older dump, a row
    # created by a test fixture). Neither path resets a store or discards a
    # completed choice: every durable choice lives in its own field on this
    # record or on the store, and none of them is touched.
    setup_wizard_step_key = fields.Char(
        readonly=True,
        help='The furthest setup-wizard step this store has completed, as '
             'the stable semantic step key. Authoritative. Written only by '
             'the setup service.',
    )
    setup_wizard_step = fields.Integer(
        default=1,
        readonly=True,
        help='Display-only ordinal of `setup_wizard_step_key` in the '
             'accepted step order. Never the authority for navigation, '
             'validation or resume. Written only by the setup service.',
    )
    # Wave 5: the moment a readiness-RELEVANT choice last changed.
    #
    # Readiness is a decision about a configuration, so a readiness result is
    # only evidence about the configuration that existed when it ran. Enabling
    # inventory, or mapping a location, after a green readiness run leaves a
    # green screen describing a store that no longer exists. Comparing this
    # stamp against `store.last_readiness_at` is what lets the setup surface
    # say "waiting" instead of "passed", and it needs no clearing: ANY later
    # readiness run -- the wizard's, activation's, or `action_reconnect`'s --
    # makes the evidence newer than the change and therefore fresh again.
    setup_readiness_stale_since = fields.Datetime(readonly=True)
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

    def _mark_setup_readiness_stale(self):
        """Record that a readiness-relevant choice just changed.

        Called by every service that changes something a readiness check
        reads -- the domain flags here, and the location mappings in the
        inventory domain. Deliberately a method on this model rather than a
        raw write at each call site: the inventory domain has to be able to
        do it too, and a second copy of "which field means stale" is how the
        two would drift.

        Elevated because the field is `readonly` structure, exactly like the
        setup-progress fields beside it; the caller has already established
        its own authority before reaching here.
        """
        self.sudo().write({
            'setup_readiness_stale_since': fields.Datetime.now(),
        })
        return True

    def _clear_setup_readiness_stale(self):
        """Readiness has just run; the evidence describes the current settings.

        Cleared EXPLICITLY rather than inferred from a timestamp comparison
        alone. Odoo stores `Datetime` at one-second resolution, so a change
        and the readiness run that answers it routinely land in the same
        second -- and a `>` comparison then reports fresh evidence as stale
        forever, while a `>=` reports it as stale for a whole second after it
        was refreshed. Neither is a property anybody should have to reason
        about. The comparison stays as the safety net for a readiness run
        this service did not perform (`action_reconnect`'s, for instance);
        this is what makes the ordinary path exact.
        """
        self.sudo().write({'setup_readiness_stale_since': False})
        return True
