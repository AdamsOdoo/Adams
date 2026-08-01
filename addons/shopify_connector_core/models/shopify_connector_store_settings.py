import logging

from psycopg2 import IntegrityError

from odoo import api, fields, models
from odoo.exceptions import AccessError

_logger = logging.getLogger(__name__)

# The canonical per-store configuration surface (Batch 2 checkpoint 1).
# Referenced by XML id rather than rebuilt as a dict so the menu, the server
# seam and any later caller can only ever open the SAME action -- a
# hand-rolled `{'type': 'ir.actions.act_window', ...}` would silently drift
# from the one the menu binds, and `view_ids` is exactly what makes this
# action resolve its own views instead of falling back to name ordering
# across the four surfaces that now share this model.
CANONICAL_STORE_SETTINGS_ACTION = (
    'shopify_connector_core.action_shopify_connector_store_settings_canonical'
)


class ShopifyConnectorStoreSettings(models.Model):
    """Store-scoped feature flags and domain-enablement configuration.

    Kept as its own model, not folded onto ``shopify.connector.store``,
    so domain modules can cleanly extend it via classic Odoo ``_inherit``
    without adding fields to the busier store record
    (core-naming-schema-planning.md §3/§5).
    """

    _name = 'shopify.connector.store.settings'
    # Store 360 slice 1: the settings row gained connector-to-connector
    # parent pointers (the per-domain catch-up job stamps), and the SEC-3
    # posture the guards encode is "a model that declares connector
    # parents carries the scope mixin" — flag, helpers and remediation
    # action included. The flag is additive (default False) and the
    # settings read rule stays the plain company rule; agreement is
    # enforced at the ORM layer by each domain's own constraint beside
    # its declared pointer.
    _inherit = ['shopify.connector.scope.mixin']
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

    # ------------------------------------------------------------------
    # Batch 2 checkpoint 1: readiness-relevant writes
    # ------------------------------------------------------------------

    @api.model
    def _readiness_relevant_fields(self):
        """The settings fields a readiness check actually consumes.

        Core declares only what CORE's readiness checks read, and it reads
        that from the registry those checks themselves evaluate --
        `shopify.connector.readiness.check._accepted_domain_flags()` -- rather
        than from a second hard-coded tuple beside it. The two would drift:
        Product Export already extends that registry with
        `product_export_domain_enabled`, and a copy here would have gone on
        reporting a store as freshly-checked after a merchant enabled catalog
        export. Deriving it means "what stales readiness" and "what readiness
        is computed over" cannot disagree by construction.

        A domain module extends this the same way it extends the registry:
        override, call `super()`, and union in ONLY the fields its own
        readiness checks consume. It must not add a field merely because it
        owns it -- a watermark or a display-only observation that no check
        reads is not readiness-relevant, and adding it would make every
        ordinary scan advance look like a configuration change.
        """
        return set(
            self.env['shopify.connector.readiness.check']
            ._accepted_domain_flags()
        )

    def _readiness_relevant_change(self, vals):
        """The subset of `self` whose readiness-relevant values genuinely move.

        A no-op write is not a configuration change. Comparing the stored
        value against the incoming one -- rather than trusting the presence
        of a key in `vals` -- is what keeps a form save that touched nothing,
        or a write that re-asserts the value already there, from marking
        perfectly good readiness evidence stale.
        """
        relevant = self._readiness_relevant_fields() & set(vals)
        if not relevant:
            return self.browse()

        def _scalar(value):
            # A Many2one may arrive as a recordset (ORM caller) or as an id
            # (RPC/`write` from the web client); normalise both to a
            # comparable id so neither shape reports a phantom change.
            if isinstance(value, models.BaseModel):
                return value.id or False
            return value

        return self.filtered(lambda record: any(
            _scalar(record[name]) != _scalar(vals[name]) for name in relevant
        ))

    def write(self, vals):
        """Ordinary write path, plus readiness staleness for real changes.

        Deliberately NOT recursive, and deliberately without a re-entrancy
        flag. `_mark_setup_readiness_stale()` writes `setup_readiness_stale_
        since`, which is not a readiness-relevant field, so the nested write
        computes an empty `changed` set and stops. The termination is a
        property of the field partition rather than of a guard somebody has
        to remember to keep correct.
        """
        changed = self._readiness_relevant_change(vals)
        result = super().write(vals)
        if changed:
            changed._mark_setup_readiness_stale()
        return result

    # ------------------------------------------------------------------
    # Batch 2 checkpoint 1: the canonical Store Settings surface
    # ------------------------------------------------------------------

    @api.model
    def _assert_canonical_settings_administrator(self):
        """UI visibility is not authorization (§11.1).

        The menu is Administrator-gated and the action carries `group_ids`,
        but both are chrome: a direct RPC call to this method reaches the
        server regardless of whether any menu was rendered. This is the
        control.
        """
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(
                'Only a Shopify Connector Administrator may open Store '
                'Settings.'
            )

    def _ensure_canonical_settings_rows(self, stores):
        """Ensure one settings row for stores the CALLER already reached.

        The elevation here is deliberately the narrowest possible: `stores`
        is resolved in the caller's own environment before this is called,
        and this method never searches for a store. It takes the ids it is
        given and creates the missing structural rows for exactly those.

        WHY THAT ORDER MATTERS, PRECISELY. `sudo()` does not "keep record
        rules running" -- Odoo's elevation bypasses them outright
        (`odoo/orm/models.py`, `_apply_ir_rules` is skipped when `env.su`).
        So the safety property cannot be "the rules still apply under
        elevation"; it has to be that the authorized set is FIXED before
        elevation begins and can only shrink afterwards. That is what the
        caller establishes and what this signature preserves: ids in, rows
        for those ids out, no discovery in between.

        Idempotent, and safe against a concurrent opener: `UNIQUE(store_id)`
        is the arbiter, each create sits in its own savepoint, and losing the
        race is a no-op rather than an error -- the winner's row is exactly
        the row this call wanted to exist.
        """
        if not stores:
            return True
        Settings = self.env['shopify.connector.store.settings'].sudo()
        existing = Settings.search([('store_id', 'in', stores.ids)])
        missing_ids = set(stores.ids) - set(existing.mapped('store_id').ids)
        for store_id in sorted(missing_ids):
            try:
                with self.env.cr.savepoint():
                    Settings.create({'store_id': store_id})
            except IntegrityError:
                # A concurrent opener won `UNIQUE(store_id)`. Its row is the
                # one we wanted; there is nothing to repair and nothing to
                # report.
                _logger.debug(
                    'Canonical store-settings row for store_id=%s was '
                    'created concurrently.', store_id,
                )
        return True

    @api.model
    def action_open_canonical_store_settings(self):
        """The sanctioned menu-opening seam (§6.7).

        Order is the whole security argument:

        1. reassert the server-side role, so a hidden menu is not the control;
        2. resolve the stores in the CALLER's ordinary environment, where the
           SEC-3 record rules and the company rule are live, so a foreign
           store is never even a candidate;
        3. re-check read access, and REFUSE outright if anything outside the
           caller's active companies made it through -- a tripwire for a
           widened resolution, not a filter that would hide one;
        4. only then elevate, and only to ensure rows for that fixed set.

        Nothing between steps 2 and 4 can widen the set.
        """
        self._assert_canonical_settings_administrator()
        stores = self.env['shopify.connector.store'].search([])
        if stores:
            stores.check_access('read')
            # A REFUSAL, NOT A FILTER, AND THAT DISTINCTION IS THE POINT.
            #
            # `store_company_rule` is `[('company_id', 'in', company_ids)]` --
            # fail-closed, and it already excluded every foreign and every
            # company-less store from the search above. So on the ordinary
            # path this can never fire, and a silent `filtered()` here would
            # be indistinguishable from no check at all: quietly dropping
            # records that were never in the set is a no-op that still passes
            # every test.
            #
            # Raising makes it a tripwire instead. The only way to reach it is
            # for the resolution above to have been widened -- elevated,
            # context-forced, or re-pointed at a different model -- which is
            # exactly the mistake §6.7 forbids and exactly the mistake a
            # filter would absorb in silence.
            allowed_company_ids = set(self.env.companies.ids)
            outside = stores.filtered(
                lambda store: store.company_id.id not in allowed_company_ids
            )
            if outside:
                raise AccessError(
                    'Store Settings resolved %d store(s) outside the active '
                    'companies. Refusing to ensure configuration for them.'
                    % len(outside)
                )
        self._ensure_canonical_settings_rows(stores)
        return self.env['ir.actions.actions']._for_xml_id(
            CANONICAL_STORE_SETTINGS_ACTION
        )
