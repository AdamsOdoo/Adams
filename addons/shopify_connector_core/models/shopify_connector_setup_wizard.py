"""S1: the 12-step guided setup wizard's server side.

What this is
------------
One bounded service behind the S1 Owl client action, in the same shape U0's
dashboard aggregate (`shopify.connector.ui.dashboard`) and U3's export
projection (`shopify.connector.product.export.ui`) already use: an
`AbstractModel` with no table, no ACL row and no persistent state of its own,
exposing a small set of guarded public entry points.

What it deliberately is NOT
---------------------------
It is not a second store-management system, and it owns no business rule. Every
step delegates to the service that already owns the decision:

* the credential is written by `shopify.connector.store.credential.
  action_set_token` -- the one credential path, write-only, never read back;
* the connection is tested by `store.action_test_connection`, which is the
  existing Administrator-gated probe;
* readiness is computed by `shopify.connector.readiness.check.run_for_store`,
  with its accepted essential/warning split;
* activation is `store.action_activate`, which keeps its whole evidence
  contract -- a credential on record, verified after its last change, a
  passing test connection and a readiness result no older than that
  verification;
* every durable choice is written to the field on `shopify.connector.store` or
  `shopify.connector.store.settings` that already owns it.

If this file ever starts deciding whether a credential is valid, whether a
store is ready, or what a direction means, that decision has been duplicated
and the two copies will diverge.

Authorization
-------------
Administrator only, enforced server-side on EVERY entry point, before any read
or write. The client action and the menu are group-gated too, but that is
visibility: `groups=` hides a control and refuses nothing. Company consistency
is checked against `env.companies` -- the switcher selection, which is what
Odoo's own record rules evaluate -- before anything elevates, and the
elevations that remain are the two Odoo's ACLs make unavoidable: creating the
store row and creating its settings row, neither of which carries a create
right for any connector group.

No Shopify request is made anywhere in this file except through
`action_test_connection`, which is step 5's whole purpose and is the existing
read-only probe. Nothing here enqueues a domain job, and activation
deliberately starts no synchronisation.
"""

import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, MissingError, UserError

#: A Shopify permanent shop domain, matched WHOLE. Shopify's shop handle is
#: lowercase alphanumerics and hyphens; anything else -- a scheme, a path, a
#: space, a subdomain -- is not a shop domain, and this value becomes the host
#: every later identity comparison is made against.
SHOP_DOMAIN_RE = re.compile(r'^[a-z0-9][a-z0-9-]*\.myshopify\.com$')

#: The accepted step order (Part A §E.1 / DEC-012 §1, restated in
#: docs/02-product/ui-ux-final-design-spec.md "Setup wizard detailed flow").
#: This tuple IS the order: the client renders from it, the server validates
#: against it, and `test_the_step_order_is_the_accepted_one` asserts it.
#:
#: Wave 5 corrects the ORDER and the addressing at the same time, and the two
#: corrections are the same correction.
#:
#: The order was wrong: readiness ran at position 6, BEFORE the operator had
#: chosen what to sync, which locations to map, where the source of truth
#: lives, whether customers are emailed, or when the first stock push
#: happens. Two of the accepted checks -- `domain_flag_enablement` and
#: `mapped_location` -- read exactly those choices, so the screen an operator
#: was asked to read and act on was evaluating a configuration that did not
#: exist yet. Activation compensated by re-running readiness server-side,
#: which made activation correct and left the operator-facing step
#: misleading. Readiness is now `final_readiness` at position 11, after every
#: choice it reads, and a new `location_mapping` step at position 7 gives the
#: `mapped_location` check something an operator can actually satisfy.
#:
#: The addressing was wrong for the same reason it is now being changed:
#: inserting one step renumbers every later one, so a stored "8" meant
#: `source_of_truth` before this change and `notification` after it. The KEY
#: is authoritative everywhere -- persistence, validation, navigation, deep
#: links, conditional skipping and resume -- and the ordinal is derived from
#: this tuple for display only.
SETUP_STEPS = (
    ('welcome', 'Welcome'),
    ('identity', 'Store identity'),
    ('credential', 'Credentials'),
    ('scopes', 'Permissions'),
    ('test_connection', 'Test connection'),
    ('directions', 'What to sync'),
    ('location_mapping', 'Location mapping'),
    ('source_of_truth', 'Source of truth'),
    ('notification', 'Customer notifications'),
    ('first_push', 'First stock push'),
    ('final_readiness', 'Final readiness'),
    ('review', 'Review and activate'),
)

SETUP_STEP_COUNT = len(SETUP_STEPS)

#: The step keys, in order, and their display ordinals. `SETUP_STEP_ORDER` is
#: the ONLY place a step key becomes a number, and the number it becomes is
#: used for rendering and for monotonic comparison -- never for addressing.
SETUP_STEP_KEYS = tuple(key for key, _label in SETUP_STEPS)
SETUP_STEP_ORDER = {
    key: index for index, key in enumerate(SETUP_STEP_KEYS, start=1)
}

#: The PRE-Wave-5 eleven-step numeric order, and the semantic step each stored
#: number translates to. This table is a one-way compatibility bridge for
#: progress recorded before the semantic key existed; it is never used to
#: WRITE progress and it never grows a new entry.
#:
#: Two entries deserve their reasons stated, because both are judgement calls
#: and a future reader will otherwise assume a typo:
#:
#: * **6 -> `directions`.** Legacy 6 was "Readiness checks", which no longer
#:   exists at that position -- the new flow runs readiness at the END. The
#:   readiness EVIDENCE that store recorded is not discarded: its
#:   `core_readiness_check` job and its `last_readiness_*` mirrors are
#:   untouched, and `final_readiness` re-evaluates them against the current
#:   configuration exactly as it would for a new store. What moves is the
#:   resume POINT, to the first step of the new order the operator has not
#:   answered, which is `directions`.
#: * **8 -> `source_of_truth`.** A legacy store resuming past `directions`
#:   skips the new `location_mapping` step, which it never had. That is not a
#:   silent skip: if its inventory domain is enabled and it has no mapping,
#:   `final_readiness` reports `mapped_location` as Blocking with a
#:   "Fix location mapping" action that deep-links back to the step by key.
LEGACY_NUMERIC_STEP_KEYS = {
    1: 'welcome',
    2: 'identity',
    3: 'credential',
    4: 'scopes',
    5: 'test_connection',
    6: 'directions',
    7: 'directions',
    8: 'source_of_truth',
    9: 'notification',
    10: 'first_push',
    11: 'review',
}

#: The five presentation states the final-readiness step renders. They are a
#: PROJECTION of the readiness service's own `{tier, result}` verdict plus the
#: context the verdict does not carry (is the domain enabled, is a refresh
#: still running, is the evidence older than the configuration it describes).
#: The readiness decision itself stays entirely server-owned in
#: `shopify.connector.readiness.check`; this module never recomputes it.
READINESS_PASSED = 'passed'
READINESS_WARNING = 'warning'
READINESS_BLOCKING = 'blocking'
READINESS_WAITING = 'waiting'
READINESS_NOT_REQUIRED = 'not_required'


def setup_step_index(step_key):
    """The display ordinal of a step key, or 0 for an unknown key."""
    return SETUP_STEP_ORDER.get(step_key, 0)

#: Step 6 (`directions`). Only DEC-003-supported directions appear. An
#: unsupported direction
#: is ABSENT rather than rendered disabled: a disabled control still tells an
#: operator the feature exists and they cannot have it, which is a promise this
#: MVP does not make.
SETUP_DOMAINS = (
    {
        'key': 'product_import',
        'field': 'product_domain_enabled',
        'label': 'Catalog import',
        'direction': 'Shopify to Odoo',
        'happens': 'Products and variants are imported into Odoo and kept '
                   'matched to their Shopify counterparts.',
        'withheld': 'Nothing is written back to Shopify by importing.',
    },
    {
        'key': 'product_export',
        'field': 'product_export_domain_enabled',
        'label': 'Catalog export',
        'direction': 'Odoo to Shopify',
        'happens': 'Product changes made in Odoo can be exported to Shopify.',
        'withheld': 'Every export needs a reviewed, confirmed preview first. '
                    'Nothing is written without one.',
    },
    {
        'key': 'sale',
        'field': 'sale_domain_enabled',
        'label': 'Orders',
        'direction': 'Shopify to Odoo',
        'happens': 'Shopify orders are imported as Odoo sales orders.',
        'withheld': 'Orders are never written back to Shopify.',
    },
    {
        'key': 'inventory',
        'field': 'inventory_domain_enabled',
        'label': 'Inventory',
        'direction': 'Shopify to Odoo, then Odoo to Shopify',
        'happens': 'Stock levels are read in as a baseline, and later Odoo '
                   'stock changes are pushed back.',
        'withheld': 'The first push always waits for a preview you confirm.',
    },
    {
        'key': 'fulfillment',
        'field': 'fulfillment_domain_enabled',
        'label': 'Fulfillment and tracking',
        'direction': 'Odoo to Shopify',
        'happens': 'Delivering in Odoo marks the Shopify order fulfilled and '
                   'carries the tracking reference.',
        'withheld': 'Fulfillments are never read back from Shopify to create '
                    'Odoo deliveries.',
    },
)

#: Step 8 (`source_of_truth`). Both choices are required and NEITHER is
#: pre-selected: converting an
#: existing backend default into consent by leaving it selected is exactly the
#: silent-consent shape DEC-012 §1 item 7 forbids.
SETUP_MATCHING_CHOICES = (
    {
        'value': 'shopify_source',
        'label': 'Shopify is the catalog source',
        'consequence': 'Products are created in Odoo from Shopify. Odoo '
                       'products that have no Shopify counterpart are left '
                       'alone.',
    },
    {
        'value': 'odoo_source',
        'label': 'Odoo is the catalog source',
        'consequence': 'Products are exported from Odoo to Shopify after you '
                       'review each change. Shopify products that have no '
                       'Odoo counterpart are left alone.',
    },
    {
        'value': 'both_match_first',
        'label': 'Both, matching existing products first',
        'consequence': 'Existing products are matched to each other before '
                       'anything new is created on either side.',
    },
)

SETUP_PRICE_CHOICES = (
    {
        'value': 'odoo_authoritative',
        'label': 'Odoo is the price authority',
        'consequence': 'Price changes made in Odoo overwrite Shopify prices '
                       'when you confirm an export.',
    },
    {
        'value': 'shopify_authoritative',
        'label': 'Shopify is the price authority',
        'consequence': 'Prices are never exported. Odoo price changes stay in '
                       'Odoo.',
    },
)


class ShopifyConnectorSetupWizard(models.AbstractModel):
    """The S1 guided setup service."""

    _name = 'shopify.connector.setup.wizard'
    _description = 'Shopify Connector Guided Setup (S1)'

    # ------------------------------------------------------------------
    # Authorization and resolution -- run before EVERY read and write
    # ------------------------------------------------------------------

    @api.model
    def _assert_setup_admin(self):
        """Administrator only, checked on the server, before any side effect.

        Not Reviewer and not Connector User. Under the accepted SEC-2 role
        model `group_shopify_connector_user` implies operator and reviewer, so
        a Reviewer-level gate here would admit every ordinary connector user to
        credential entry and activation.
        """
        if not self.env.user.has_group(
            'shopify_connector_core.group_shopify_connector_admin'
        ):
            raise AccessError(_(
                'Only a Shopify Connector Administrator may run the guided '
                'setup.'
            ))
        return True

    @api.model
    def _resolve_store(self, store_id):
        """Turn a caller-supplied id into a store this caller may act on.

        Two checks, in this order, because each catches something the other
        does not:

        1. **Administrator.** Before anything is read, so an unauthorized
           caller learns nothing -- not even whether the id exists.
        2. **Record access as the calling user.** `browse(id)` bypasses no ACL
           and proves nothing either; `check_access` is what turns "an id
           somebody typed into an RPC call" into "a record they may read". The
           SEC-3 record rule makes a foreign store invisible, so this is where
           a cross-company id is refused. The explicit `env.companies` check
           below it is the same rule's own comparison, restated for the case
           a store's `company_id` is unset -- the switcher selection is what
           Odoo evaluates `company_ids` against in a record rule, not
           `user.company_ids`, which would let a user allowed in two
           companies act on the one they are not currently in.

        Correction E (independent review, P3). `check_access` alone can
        raise either `AccessError` (a foreign-but-real store, excluded by
        the SEC-3 `store_company_rule`) or `MissingError` (a store id that
        was never real: evaluating that rule still requires reading the
        id's own field values, and there are none to read -- the identical
        ambiguity Odoo's own `fetch()` guards against with this same
        two-exception `try`/`except`). The previous version called
        `store.exists()` FIRST, before `check_access` -- and `exists()` is
        a raw physical-row test that the SEC-3 rule does NOT filter, so it
        returned `True` for a foreign store and `False` for a nonexistent
        one. That let a cross-company Administrator learn a foreign store
        id merely EXISTS -- no content, only a boolean -- by which of two
        distinct refusals they received, before the company check had run
        at all. Both outcomes now collapse to one generic refusal, and no
        field of a foreign or nonexistent record is ever read to produce
        it.
        """
        self._assert_setup_admin()
        if not store_id:
            raise UserError(_('No store was selected.'))
        store = self.env['shopify.connector.store'].browse(int(store_id))
        try:
            store.check_access('read')
        except (AccessError, MissingError):
            raise UserError(_('This Shopify store is not available.'))
        if store.company_id and store.company_id not in self.env.companies:
            raise AccessError(_('This Shopify store belongs to another company.'))
        return store

    @api.model
    def _settings_for(self, store):
        """This store's settings row, created on first use.

        Elevated because Odoo's merged ACL grants no connector group `create`
        on `shopify.connector.store.settings` -- deliberately, since a settings
        row is structure rather than data. The elevation happens only after
        `_resolve_store` has established the Administrator role, record access
        and company consistency, and it can never cross a company boundary:
        `company_id` on the settings row is a stored related field through
        `store_id`, so the row's company is the store's company by
        construction rather than by assignment.
        """
        store.ensure_one()
        Settings = self.env['shopify.connector.store.settings']
        settings = Settings.sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        if not settings:
            settings = Settings.sudo().create({'store_id': store.id})
        return settings

    # ------------------------------------------------------------------
    # Durable progress: semantic key authoritative, ordinal derived
    # ------------------------------------------------------------------

    @api.model
    def _resume_key(self, settings):
        """The durable resume point of `settings`, as a semantic step key.

        Three sources, in this order, and the order is the whole point:

        1. the stored semantic key, when it is one this build knows;
        2. otherwise the PRE-Wave-5 numeric column, translated through
           `LEGACY_NUMERIC_STEP_KEYS` -- the identical translation
           `19.0.1.15.0/post-migrate.py` performs, applied at read time so a
           row the migration never reached (an older dump restored later, a
           fixture that wrote the number directly) resumes at the same place
           rather than being silently reset to step 1;
        3. `welcome`, for a store with no progress at all.

        A stored key this build does not recognise falls through to the
        numeric translation rather than raising: a resume point is not worth
        refusing to render a screen over, and every later write repairs it.
        """
        if not settings:
            return SETUP_STEP_KEYS[0]
        stored_key = settings.setup_wizard_step_key
        if stored_key in SETUP_STEP_ORDER:
            return stored_key
        try:
            legacy = int(settings.setup_wizard_step or 1)
        except (TypeError, ValueError):
            legacy = 1
        if legacy in LEGACY_NUMERIC_STEP_KEYS:
            return LEGACY_NUMERIC_STEP_KEYS[legacy]
        if legacy >= max(LEGACY_NUMERIC_STEP_KEYS):
            # A number above the legacy range can only come from a build
            # that already used this order, so it is already an ordinal in
            # THIS tuple; clamp rather than invent.
            return SETUP_STEP_KEYS[min(legacy, SETUP_STEP_COUNT) - 1]
        return SETUP_STEP_KEYS[0]

    @api.model
    def _record_progress(self, settings, step_key):
        """Advance the durable resume point, never rewind it.

        Monotonic on purpose: paging Back to re-read the credential step must
        not throw away the fact that the later steps were already completed,
        or Back would quietly become a destructive control.

        Monotonic ON THE SEMANTIC ORDER, not on the stored integer, because
        the integer is only a rendering of the key and a legacy row's integer
        was produced by a different order entirely. The ordinal is written
        alongside so the two never disagree, and a legacy row is upgraded in
        place the first time any step is completed -- so a store stops
        depending on the read-time translation as soon as it is touched.
        """
        if step_key not in SETUP_STEP_ORDER:
            raise UserError(_('That is not a setup step.'))
        current_key = self._resume_key(settings)
        if SETUP_STEP_ORDER[step_key] > SETUP_STEP_ORDER[current_key]:
            settings.sudo().write({
                'setup_wizard_step_key': step_key,
                'setup_wizard_step': SETUP_STEP_ORDER[step_key],
            })
            return step_key
        if settings.setup_wizard_step_key != current_key:
            settings.sudo().write({
                'setup_wizard_step_key': current_key,
                'setup_wizard_step': SETUP_STEP_ORDER[current_key],
            })
        return current_key

    @api.model
    def _mark_readiness_stale(self, settings):
        """A readiness-relevant choice changed; earlier evidence is stale.

        Called from the two steps whose values readiness actually reads --
        the domain flags, and (through the inventory domain's own service)
        the location mappings. Nothing is invalidated destructively: the
        stored readiness result stays exactly where it is, and the surface
        stops calling it green until a run newer than this stamp exists.
        """
        if settings:
            settings._mark_setup_readiness_stale()
        return True

    @api.model
    def _clear_readiness_stale(self, settings):
        """Readiness has just run here; its evidence is current again."""
        if settings:
            settings._clear_setup_readiness_stale()
        return True

    @api.model
    def _readiness_is_stale(self, store, settings):
        """Is the stored readiness evidence older than the configuration?

        The wizard's own readiness runs clear the mark outright, so this
        comparison is the SAFETY NET for a run performed somewhere else --
        `action_reconnect` runs `run_for_store` too. `>=` rather than `>`
        because Odoo stores `Datetime` at one-second resolution: a change and
        an unrelated readiness run inside the same second are indistinguishable
        here, and treating that tie as stale is the fail-closed direction --
        it asks for one more run, where `>` would silently present evidence
        that may predate the change as current.
        """
        if not settings or not settings.setup_readiness_stale_since:
            return False
        if not store or not store.last_readiness_at:
            return True
        return settings.setup_readiness_stale_since >= store.last_readiness_at

    # ------------------------------------------------------------------
    # Step 4: the required scopes, derived rather than hard-coded
    # ------------------------------------------------------------------

    @api.model
    def _setup_required_scopes(self, store):
        """Governed Shopify scopes with a business reason for each.

        Derived from the governed capability declarations the readiness check
        itself uses, so a scope cannot be added to the connector and stay
        invisible here -- a stale hand-written list on a setup screen is worse
        than no list, because an operator grants exactly what it names.

        Correction B (independent review, §7E). This reads
        `Readiness._governed_scope_catalog()`, NOT `REQUIRED_MVP_SCOPES`
        directly -- the same fixed-constant pattern flagged in Defects
        #2/#3 would otherwise apply here too: step 4 runs before step 7's
        domain choice exists, so it has to show the full installed
        superset an operator might need, and a domain module's own scope
        (e.g. Product Export's `write_products`) would otherwise stay
        invisible on this screen even though the module is installed. The
        domain-extension seam is the same one `_get_checks` uses: a domain
        module overrides `_governed_scope_catalog`, calls `super()`, and
        appends its own entries -- unconditionally, since this is a
        DISPLAY list of what might be needed, not `REQUIRED_MVP_SCOPES`
        (core's own unconditional baseline, read by `_check_required_
        scopes` and never extended here).
        """
        Readiness = self.env['shopify.connector.readiness.check']
        granted = self._granted_scopes(store)
        return [
            dict(entry, granted=entry['scope'] in granted)
            for entry in Readiness._governed_scope_catalog()
        ]

    @api.model
    def _granted_scopes(self, store):
        """The scopes Shopify last reported, as a set. Never a live call.

        `store.granted_scopes` is a JSON array -- `_run_connection_probe`
        writes it with `json.dumps([scope['handle'] ...])`. The previous
        comma-split parsed that JSON as prose, so every element kept a quote
        or a bracket and no scope ever compared equal to its handle: the
        Permissions step's "Granted" badge was unrenderable against real
        evidence (Wave 5 audit, P1). JSON first; the comma fallback stays for
        any legacy row that predates the JSON mirror.
        """
        if not store or not store.granted_scopes:
            return set()
        try:
            parsed = json.loads(store.granted_scopes)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            return {
                scope.strip() for scope in parsed
                if isinstance(scope, str) and scope.strip()
            }
        return {
            token.strip()
            for token in store.granted_scopes.replace('\n', ',').split(',')
            if token.strip()
        }

    # ------------------------------------------------------------------
    # The single read entry point
    # ------------------------------------------------------------------

    @api.model
    def get_setup_state(self, store_id=None):
        """The whole render payload for the wizard, as the current user.

        One bounded round trip per navigation rather than a call per field.
        Every value is either a plain-language label this service owns or a
        field the caller could read anyway -- and the credential is not among
        them: `credential_present` is a boolean, and no token, fragment or
        length ever crosses this boundary.
        """
        self._assert_setup_admin()
        store = False
        if store_id:
            store = self._resolve_store(store_id)
        # A resumable store the caller may act on, offered when the wizard is
        # opened with no explicit target. Bounded and company-filtered by the
        # ordinary record rules, because the search runs as the caller.
        candidates = self.env['shopify.connector.store'].search(
            [], order='id asc', limit=20,
        )
        if not store and len(candidates) == 1:
            store = candidates

        settings = self._settings_for(store) if store else False
        resume_key = self._resume_key(settings)
        locations = self._setup_location_payload(store, settings)
        payload = {
            'steps': self._step_payload(settings, locations),
            'step_count': SETUP_STEP_COUNT,
            # The resume point the client navigates by. The ordinal beside it
            # is what the heading renders ("Step 7 of 12") and is never what
            # the client compares against.
            'resume_step_key': resume_key,
            'resume_step': setup_step_index(resume_key),
            'store': self._store_payload(store, settings),
            'stores': [
                {'id': candidate.id, 'name': candidate.display_name}
                for candidate in candidates
            ],
            'scopes': self._setup_required_scopes(store) if store else [],
            'domains': self._domain_payload(settings),
            'location_mapping': locations,
            'matching_choices': list(SETUP_MATCHING_CHOICES),
            'price_choices': list(SETUP_PRICE_CHOICES),
            'readiness': self._readiness_payload(store, settings, locations),
            'summary': self._summary_payload(store, settings, locations),
        }
        return payload

    @api.model
    def _step_payload(self, settings, locations):
        """Every step, always, with its applicability stated rather than hidden.

        A conditional step is NOT removed from the list when it does not
        apply. Removing it would renumber everything after it -- reintroducing
        exactly the coupling this wave removes -- and would leave an operator
        wondering whether a step they half-remember still exists. It stays in
        place, is rendered as `Not required`, and says why.
        """
        applicable = self._step_applicability(settings, locations)
        return [
            {
                'index': index,
                'key': key,
                'label': label,
                'applicable': applicable.get(key, {}).get('applicable', True),
                'skipped_reason': applicable.get(key, {}).get('reason', ''),
            }
            for index, (key, label) in enumerate(SETUP_STEPS, start=1)
        ]

    @api.model
    def _step_applicability(self, settings, locations):
        """Which steps do not apply to this store, and the reason for each."""
        inventory_on = bool(settings and settings.inventory_domain_enabled)
        result = {}
        if not inventory_on:
            reason = _(
                'Inventory syncing is not enabled for this store, so there '
                'is nothing to map. You can enable it later in Store '
                'Settings and come back to this step.'
            )
            result['location_mapping'] = {
                'applicable': False, 'reason': reason,
            }
            result['first_push'] = {
                'applicable': False,
                'reason': _(
                    'Inventory syncing is not enabled for this store, so '
                    'there is no first stock push to schedule.'
                ),
            }
        elif not locations.get('available'):
            result['location_mapping'] = {
                'applicable': False,
                'reason': locations.get('reason') or '',
            }
        return result

    @api.model
    def _store_payload(self, store, settings):
        if not store:
            return {
                'id': False,
                'name': '',
                'shop_domain': '',
                'state': 'setup_incomplete',
                'credential_present': False,
                'test_connection_result': False,
                'test_connection_reason': '',
                'setup_completed_at': False,
                'setup_completed_by': '',
            }
        return {
            'id': store.id,
            'name': store.name or '',
            'shop_domain': store.shop_domain or '',
            'state': store.state,
            'state_label': dict(
                store._fields['state']._description_selection(self.env)
            ).get(store.state, store.state),
            # A boolean, never the value and never its length. The credential
            # is write-only by design (DEC-004) and this payload is one of the
            # places that could quietly stop being true.
            'credential_present': bool(store.credential_present),
            'credential_verified': bool(store.credential_last_verified_at),
            # Wave 5: which acquisition path this store uses, plus the
            # NON-SECRET mirrors of the client-credentials mode. Mode names and
            # timestamps only -- no token, no secret, no length, ever.
            **self._credential_mode_payload(store),
            'test_connection_result': store.last_test_connection_result or False,
            'test_connection_reason': store.last_test_connection_reason or '',
            'setup_completed_at': (
                fields.Datetime.to_string(settings.setup_completed_at)
                if settings and settings.setup_completed_at else False
            ),
            'setup_completed_by': (
                settings.setup_completed_uid.display_name
                if settings and settings.setup_completed_uid else ''
            ),
        }

    @api.model
    def _credential_mode_payload(self, store):
        """Non-secret credential-mode facts for the setup and settings surfaces.

        Everything here is safe to render: the mode name, presence booleans and
        expiry/failure mirrors. The elevated read is the same store-scoped
        `_credential_for` accessor the credential service itself uses; nothing
        secret leaves it because nothing secret is selected.
        """
        Credential = self.env['shopify.connector.store.credential']
        credential = Credential._credential_for(store)
        cache = Credential._token_cache_status(store)
        return {
            'auth_mode': credential.auth_mode if credential else
                'offline_access_token',
            'client_credentials_present': bool(
                credential.client_credentials_present
            ) if credential else False,
            'token_expires_at': (
                fields.Datetime.to_string(cache['expires_at'])
                if cache['expires_at'] else False
            ),
            'token_last_failure_reason': (
                credential.token_last_failure_reason or ''
            ) if credential else '',
        }

    @api.model
    def _domain_payload(self, settings):
        """Only the domains this install actually carries.

        A domain whose module is not installed has no settings field, so it is
        omitted rather than shown switched off -- offering a toggle for a
        module that is absent is a promise the server cannot keep.
        """
        domains = []
        for domain in SETUP_DOMAINS:
            if settings and domain['field'] not in settings._fields:
                continue
            if not settings and domain['field'] not in self.env[
                'shopify.connector.store.settings'
            ]._fields:
                continue
            domains.append(dict(
                domain,
                enabled=bool(settings[domain['field']]) if settings else False,
            ))
        return domains

    # ------------------------------------------------------------------
    # The location-mapping step's data, through a domain seam
    # ------------------------------------------------------------------

    @api.model
    def _setup_location_payload(self, store, settings):
        """Cached Shopify locations and their mapping state, or "unavailable".

        The domain-extension seam for the `location_mapping` step, in exactly
        the shape `_get_checks` and `_governed_scope_catalog` already use: the
        inventory module overrides this by ordinary model inheritance. Core
        owns no mapping concept and must not grow one -- it does not import
        the inventory models, does not read
        `shopify.connector.location.mapping`, and cannot, because a database
        without the inventory addon has no such table.
        """
        return {
            'available': False,
            'reason': _(
                'Location mapping needs the Shopify Connector Inventory '
                'module, which is not installed in this database.'
            ),
            'locations': [],
            'odoo_locations': [],
            'refresh': {
                'state': 'none', 'job_id': False, 'label': '', 'reason': '',
            },
            'mapped_count': 0,
            'unmapped_count': 0,
            'has_valid_mapping': False,
            'truncated': False,
        }

    @api.model
    def _setup_refresh_locations(self, store):
        """Admit a governed Shopify-location refresh job. Domain seam."""
        raise UserError(_(
            'Location mapping needs the Shopify Connector Inventory module, '
            'which is not installed in this database.'
        ))

    @api.model
    def _setup_follow_location_refresh(self, store, job_id):
        """Read one exact domain-owned refresh run. Domain extension seam."""
        raise UserError(_(
            'Location mapping needs the Shopify Connector Inventory module, '
            'which is not installed in this database.'
        ))

    @api.model
    def _setup_search_locations(self, store, side, query, offset):
        """Bounded server-side location search for the mapping step. Seam.

        Wave 5: the step's two lists are bounded pages, which is right --
        but a bounded page whose tail is REACHABLE only through a different
        screen made every location past the cut effectively unmappable here.
        This seam is the reachability route: the inventory module overrides
        it with a bounded, store-scoped, paginated search over ALL eligible
        cached Shopify locations (`side='shopify'`) or internal Odoo
        locations (`side='odoo'`). ("Indexed" was claimed here and is gone --
        see the override's own docstring for what actually bounds the work.)
        """
        raise UserError(_(
            'Location mapping needs the Shopify Connector Inventory module, '
            'which is not installed in this database.'
        ))

    @api.model
    def _setup_search_continuation(self, store, side, query):
        """Seam: the continuation token binding a page to its query.

        Declared in core beside the RPC that VALIDATES it, so the check exists
        even in a database with no inventory addon -- where the search itself is
        refused anyway, and a token check that silently passed would be a hole
        waiting for the day it is not.
        """
        return False

    #: The furthest a caller may page into one result set. 200 pages of 50 is
    #: 10,000 rows, which is far past any real store's location count and far
    #: short of a number that makes PostgreSQL's OFFSET scan expensive. It exists
    #: so an absurd, overflowed or hand-edited offset is REFUSED rather than
    #: quietly clamped: a clamp turns "page 10^9" into page 0, which the client
    #: then appends to what it already has, silently duplicating every row.
    SETUP_LOCATION_MAX_OFFSET = 10000

    @api.model
    def search_location_options(self, store_id, side, query='', offset=0,
                                continuation=None):
        """The mapping step's search RPC: one bounded page of candidates.

        Same authorization funnel as every other setup entry point
        (`_resolve_store` re-establishes the Administrator role, record
        access and company consistency), then the domain seam. `side` is
        validated here so the seam only ever sees the two values it
        documents.

        BATCH 1 CORRECTION -- the offset is validated, not coerced.

        A non-numeric, negative or absurd offset used to become `0` silently.
        That reads as forgiving and is the opposite: the client sends an offset
        only when it is CONTINUING a set, and a continuation that silently
        restarts at row 0 is appended to the rows already on screen, so the
        operator sees every location twice and the page they were reaching for
        not at all. All three shapes are now refused.

        `continuation` binds a page request to the query it belongs to. It is
        integrity, not authorization -- `_resolve_store` above is authorization,
        and it runs on every call whatever token arrives. What the token
        prevents is paging position leaking between result sets: search "north",
        page to 100, search "south", press Load more, and a bare offset would
        fetch rows 100-150 of the NEW set while the client believed it held rows
        0-100 of it. `None` is accepted for a first page, which is the only
        request that has nothing to continue.
        """
        store = self._resolve_store(store_id)
        if side not in ('shopify', 'odoo'):
            raise UserError(_('Unknown location search side.'))
        if not isinstance(query, str):
            query = ''
        query = query.strip()
        if isinstance(offset, bool) or not isinstance(offset, int):
            # `bool` is an `int` in Python and `True` would otherwise page to
            # row 1. Floats and numeric strings are refused too: an offset is a
            # value this server produced, so anything else is a client that has
            # stopped following the contract.
            raise UserError(_('The location list position is not valid.'))
        if offset < 0 or offset > self.SETUP_LOCATION_MAX_OFFSET:
            raise UserError(_('The location list position is out of range.'))
        if offset and continuation != self._setup_search_continuation(
            store, side, query,
        ):
            raise UserError(_(
                'The location list moved on while you were reading it. '
                'Search again to start from the first page.'
            ))
        return self._setup_search_locations(store, side, query, offset)

    @api.model
    def _setup_create_location_mapping(
        self, store, shopify_location_gid, odoo_location_id,
    ):
        """Create one explicit location mapping. Domain seam."""
        raise UserError(_(
            'Location mapping needs the Shopify Connector Inventory module, '
            'which is not installed in this database.'
        ))

    # ------------------------------------------------------------------
    # Readiness: rendered, never recomputed
    # ------------------------------------------------------------------

    @api.model
    def _readiness_payload(self, store, settings=False, locations=None):
        """The last recorded readiness result, per check, as presentation.

        Stored evidence only -- reading this screen never runs a check and
        never calls Shopify. The `final_readiness` step runs them explicitly.

        The VERDICT is not computed here and never has been: it comes from
        `shopify.connector.readiness.check`, with its accepted
        essential/warning split and its accepted fail-closed aggregation.
        What this adds is the presentation state, which needs three facts the
        verdict does not carry -- whether the check applies at all, whether a
        location refresh is still in flight, and whether the evidence is
        older than the configuration it describes.
        """
        if locations is None:
            locations = self._setup_location_payload(store, settings)
        stale = self._readiness_is_stale(store, settings)
        empty = {
            'ran': False, 'overall': False, 'stale': stale,
            'checks': [], 'blocking': [], 'waiting': [],
        }
        if not store or not store.last_readiness_at:
            return empty
        checks = self._last_readiness_checks(store)
        if not checks:
            return dict(empty, ran=True, overall=store.last_readiness_result)
        projected = [
            self._project_readiness_check(check, settings, locations, stale)
            for check in checks
        ]
        return {
            'ran': True,
            'overall': store.last_readiness_result,
            'stale': stale,
            'checks': projected,
            # `blocking` is what refuses activation and what the review step
            # lists. It is the PROJECTED state, so a check that is waiting on
            # a refresh is not reported as a failure the operator caused, and
            # a not-required check never appears here at all.
            'blocking': [
                check for check in projected
                if check['state'] == READINESS_BLOCKING
            ],
            'waiting': [
                check for check in projected
                if check['state'] == READINESS_WAITING
            ],
        }

    @api.model
    def _project_readiness_check(self, check, settings, locations, stale):
        """One check's presentation state, tone, action and copy."""
        state = self._readiness_state(check, settings, locations, stale)
        action = self._readiness_action(check, state)
        return dict(
            check,
            label=self._readiness_label(check.get('code')),
            state=state,
            tone=self._readiness_tone(state),
            state_label=self._readiness_state_label(state),
            owner=self._readiness_owner(check.get('code')),
            reason=self._readiness_reason(check, state, locations),
            action_label=action.get('label', ''),
            action_step_key=action.get('step_key', ''),
        )

    @api.model
    def _readiness_state(self, check, settings, locations, stale):
        """Map a stored `{tier, result}` verdict onto a presentation state.

        The rules, in the order they are applied, and why each exists:

        1. **Stale beats everything, including Not required.** The order
           matters and is not obvious. "Not applicable" is itself a
           CONCLUSION about a configuration -- `mapped_location` reports it
           because the inventory domain was off when the check ran. Enable
           inventory and that stored conclusion is exactly as out of date as
           any other, so ranking Not required above Waiting would leave the
           one row an operator most needs to re-read looking settled.

        2. **Waiting beats a verdict.** A `mapped_location` check whose
           location refresh has not finished is a result nobody has yet. An
           unfinished check must never read as a success, and it must not
           read as the operator's failure either.

        3. **Not required beats a pass.** A check that examined nothing
           passed because there was nothing to examine. Rendering that as a
           green "Passed" tells an operator something was proven.

        4. **Otherwise the accepted verdict stands**, with essential failures
           Blocking and warning failures Warning -- unchanged from the
           accepted severity split.
        """
        if stale:
            return READINESS_WAITING
        if check.get('not_applicable'):
            return READINESS_NOT_REQUIRED
        code = check.get('code')
        result = check.get('result')
        tier = check.get('tier')
        if code == 'mapped_location':
            refresh_state = (locations or {}).get('refresh', {}).get('state')
            if refresh_state == 'stale':
                return READINESS_BLOCKING
            if result != 'pass' and refresh_state in ('waiting', 'running'):
                # A refresh is genuinely in flight, so "no mapping yet" is
                # not yet a fact about this store. It is also NEVER reported
                # as "Shopify has no locations": an empty cache while a
                # refresh is pending is an unfinished read, not an answer.
                return READINESS_WAITING
        if result == 'pass':
            return READINESS_PASSED
        return (
            READINESS_BLOCKING if tier == 'essential' else READINESS_WARNING
        )

    @api.model
    def _readiness_action(self, check, state):
        """The one control that fixes this check, addressed by STEP KEY.

        Never by ordinal. A deep link built from a number is a link that
        silently points at a different screen the next time a step is added,
        which is the defect this wave exists to close.
        """
        if check.get('code') != 'mapped_location':
            return {}
        if state in (READINESS_PASSED, READINESS_NOT_REQUIRED):
            return {}
        return {
            'label': _('Fix location mapping'),
            'step_key': 'location_mapping',
        }

    @api.model
    def _readiness_reason(self, check, state, locations):
        """The sentence under a check, corrected for what is actually known."""
        if state == READINESS_BLOCKING and check.get('code') == 'mapped_location':
            refresh = (locations or {}).get('refresh', {})
            if refresh.get('state') == 'stale':
                return refresh.get('reason') or _(
                    'The location list belongs to an earlier store connection.'
                )
        if state == READINESS_WAITING and check.get('code') == 'mapped_location':
            refresh = (locations or {}).get('refresh', {})
            if refresh.get('state') in ('waiting', 'running'):
                return _(
                    'The Shopify location list is still being refreshed, so '
                    'whether a location is mapped is not known yet. This is '
                    'not a report that Shopify has no locations.'
                )
        if state == READINESS_WAITING:
            return _(
                'Something this check reads has changed since it last ran, '
                'so this result no longer describes the current settings. '
                'Run the checks again.'
            )
        return check.get('reason') or ''

    @api.model
    def _readiness_state_label(self, state):
        return {
            READINESS_PASSED: _('Passed'),
            READINESS_WARNING: _('Worth checking'),
            READINESS_BLOCKING: _('Must be fixed'),
            READINESS_WAITING: _('Waiting'),
            READINESS_NOT_REQUIRED: _('Not required'),
        }.get(state, _('Waiting'))

    @api.model
    def _last_readiness_checks(self, store):
        """Per-check results from the most recent readiness job's log.

        Elevated to read the connector's own log row, which carries no ACL for
        a payload read -- and bounded to ONE row of ONE job belonging to the
        store the caller has already been authorised for. Nothing merchant-
        facing, no credential and no Shopify response is in this payload: the
        readiness service records only `{code, tier, result, reason}`.
        """
        job = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_readiness_check'),
            ('state', '=', 'succeeded'),
        ], order='id desc', limit=1)
        if not job:
            return []
        log = self.env['shopify.connector.job.log'].sudo().search([
            ('job_id', '=', job.id),
            ('payload_snapshot', '!=', False),
        ], order='id desc', limit=1)
        if not log or not log.payload_snapshot:
            return []
        try:
            raw = json.loads(log.payload_snapshot)
        except (TypeError, ValueError):
            return []
        if not isinstance(raw, list):
            return []
        return [
            {
                'code': entry.get('code') or '',
                'tier': entry.get('tier') or 'warning',
                'result': entry.get('result') or 'not_proven',
                # A snapshot written before Wave 5 carries no
                # `not_applicable` key. `.get()` defaults it to False, which
                # is the safe direction: an old snapshot renders its accepted
                # verdict rather than claiming something is not required.
                'not_applicable': bool(entry.get('not_applicable')),
                'reason': entry.get('reason') or '',
            }
            for entry in raw
            if isinstance(entry, dict)
        ]

    @api.model
    def _readiness_label(self, code):
        return {
            'credential_test_connection': _('The credential works'),
            'required_scopes': _('Every required permission is granted'),
            'api_version_health': _('The Shopify API version is healthy'),
            'store_identity': _('The shop domain matches this store'),
            'web_base_url': _('Odoo knows its own public address'),
            'webhook_hmac': _('Webhook signatures can be verified'),
            # Wave 5 renames. "A Shopify location is mapped to a warehouse"
            # named a mechanism; "Inventory location mapping" names the thing
            # the operator has to go and fix, which is what the row's action
            # deep-links to. "At least one thing is set to sync" was vague
            # enough that a connect-only store read it as an error.
            'mapped_location': _('Inventory location mapping'),
            'cron_queue_health': _('Background jobs are running'),
            'domain_flag_enablement': _('Sync features selected'),
            'product_export_scopes': _('Catalog export permissions'),
            'fulfillment_write_scope': _('Fulfillment write permission'),
            'fulfillment_api_version': _('Fulfillment API version'),
            'fulfillment_staff_permission': _(
                'Shopify staff can fulfill and ship',
            ),
        }.get(code, code or _('Check'))

    @api.model
    def _readiness_owner(self, code):
        return {
            'credential_test_connection': _('Administrator'),
            'required_scopes': _('Shopify admin'),
            'api_version_health': _('Administrator'),
            'store_identity': _('Administrator'),
            'web_base_url': _('Odoo administrator'),
            'webhook_hmac': _('Administrator'),
            'mapped_location': _('Administrator'),
            'cron_queue_health': _('Odoo administrator'),
            'domain_flag_enablement': _('Administrator'),
            'product_export_scopes': _('Shopify admin'),
            'fulfillment_write_scope': _('Shopify admin'),
            'fulfillment_api_version': _('Administrator'),
            'fulfillment_staff_permission': _('Shopify admin'),
        }.get(code, _('Administrator'))

    @api.model
    def _readiness_tone(self, state):
        """Colour follows the presentation state, and never leads it.

        Every row also carries `state_label` as text, so a reader who cannot
        see the colour still gets the same five distinctions.
        """
        return {
            READINESS_PASSED: 'success',
            READINESS_WARNING: 'warning',
            READINESS_BLOCKING: 'danger',
            READINESS_WAITING: 'info',
            READINESS_NOT_REQUIRED: 'neutral',
        }.get(state, 'neutral')

    @api.model
    def _summary_payload(self, store, settings, locations=None):
        """The review step, in plain words rather than as a pass/fail grid."""
        if not store or not settings:
            return {
                'domains': [], 'matching': '', 'price': '',
                'notification': '', 'first_push': '', 'location_mapping': '',
                'can_activate': False, 'blocking': [], 'waiting': [],
                'already_active': False,
            }
        enabled = [
            domain['label'] for domain in self._domain_payload(settings)
            if domain['enabled']
        ]
        matching = dict(
            (choice['value'], choice['label'])
            for choice in SETUP_MATCHING_CHOICES
        ).get(settings.product_first_sync_source, '')
        price = dict(
            (choice['value'], choice['label'])
            for choice in SETUP_PRICE_CHOICES
        ).get(settings.price_source_of_truth, '')
        if locations is None:
            locations = self._setup_location_payload(store, settings)
        readiness = self._readiness_payload(store, settings, locations)
        return {
            'domains': enabled,
            'matching': matching,
            'price': price,
            'notification': self._notification_summary(settings),
            'first_push': self._first_push_summary(settings),
            'location_mapping': self._location_summary(settings, locations),
            # `can_activate` is advisory rendering. Activation itself re-runs
            # readiness server-side and re-decides; this is only what the
            # screen says while the operator is looking at it.
            'can_activate': bool(
                readiness['ran']
                and not readiness['blocking']
                and not readiness['waiting']
                and not readiness['stale']
            ),
            'blocking': readiness['blocking'],
            'waiting': readiness['waiting'],
            'already_active': store.state == 'connected',
        }

    @api.model
    def _location_summary(self, settings, locations):
        if not settings.inventory_domain_enabled:
            return _('Inventory is not enabled, so no location mapping is '
                     'required.')
        if not locations.get('available'):
            return locations.get('reason') or ''
        mapped = locations.get('mapped_count') or 0
        unmapped = locations.get('unmapped_count') or 0
        if not mapped and not unmapped:
            return _('No Shopify locations have been read yet. Refresh the '
                     'list on the Location mapping step.')
        if not mapped:
            return _('No Shopify location is mapped yet. %(unmapped)d '
                     'location(s) are waiting.', unmapped=unmapped)
        if unmapped:
            return _('%(mapped)d location(s) mapped, %(unmapped)d not mapped. '
                     'An unmapped location does not synchronise.',
                     mapped=mapped, unmapped=unmapped)
        return _('%(mapped)d location(s) mapped.', mapped=mapped)

    @api.model
    def _notification_summary(self, settings):
        if settings.notification_default_enabled:
            return _('Shopify will email your customers when a delivery is '
                     'fulfilled.')
        return _('Customers will not be emailed. You can change this later in '
                 'Store Settings.')

    @api.model
    def _first_push_summary(self, settings):
        if not settings.inventory_domain_enabled:
            return _('Inventory is not enabled, so there is no first stock '
                     'push to schedule.')
        if 'inventory_scheduled_sync_enabled' not in settings._fields:
            return _('Inventory scheduling is not available in this install.')
        if settings.inventory_scheduled_sync_enabled:
            return _('Stock scanning is scheduled. The first push still waits '
                     'for a preview you confirm.')
        return _('Stock scanning is off for now. You can turn it on later in '
                 'Store Settings.')

    # ------------------------------------------------------------------
    # Step 2 -- store identity
    # ------------------------------------------------------------------

    @api.model
    def save_store_identity(self, name, shop_domain, store_id=None):
        """Create or rename the store this setup is for.

        The shop domain is validated for SHAPE only. Identity is CONFIRMED at
        readiness by the store-identity check, against what Shopify itself
        reports -- asserting it here would be the wizard claiming a fact it has
        not observed.

        The create is elevated because no connector group holds `create` on
        `shopify.connector.store`; the company is taken from the caller's own
        active company and refused if the caller does not belong to it, so the
        elevation cannot mint a store into a company the caller is outside.
        """
        self._assert_setup_admin()
        name = (name or '').strip()
        shop_domain = (shop_domain or '').strip().lower()
        if not name:
            raise UserError(_('Give this store a name you will recognise.'))
        # Matched as a whole rather than by suffix. A suffix test accepts
        # `https://acme.myshopify.com` and `a b.myshopify.com`, which are not
        # shop domains -- and a bad value here becomes the host every later
        # request is compared against.
        if not SHOP_DOMAIN_RE.match(shop_domain):
            raise UserError(_(
                'Enter the store\'s permanent Shopify domain, which ends in '
                '.myshopify.com — for example acme-supplies.myshopify.com. '
                'Enter the domain alone, with no https:// and no path.'
            ))
        if store_id:
            store = self._resolve_store(store_id)
            if store.shop_domain != shop_domain:
                raise UserError(_(
                    'This store is already connected to %(existing)s. A store '
                    'row is bound to one Shopify shop; set up a second store '
                    'for a different shop.',
                    existing=store.shop_domain,
                ))
            store.write({'name': name})
        else:
            company = self.env.company
            if company not in self.env.user.company_ids:
                raise AccessError(_(
                    'You may only set up a Shopify store for a company you '
                    'belong to.'
                ))
            existing = self.env['shopify.connector.store'].sudo().search(
                [('shop_domain', '=', shop_domain)], limit=1,
            )
            if existing:
                raise UserError(_(
                    'A store already exists for this Shopify shop domain.'
                ))
            store = self.env['shopify.connector.store'].sudo().create({
                'name': name,
                'shop_domain': shop_domain,
                'company_id': company.id,
            })
            store = store.with_env(self.env)
        settings = self._settings_for(store)
        self._record_progress(settings, 'identity')
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Step 3 -- credential entry (write-only)
    # ------------------------------------------------------------------

    @api.model
    def save_credential(self, store_id, token):
        """Hand the token to the credential service and forget it.

        The token is never echoed, never returned, never logged and never put
        into an exception message: the response is the ordinary setup state,
        in which the credential appears as the boolean `credential_present`.
        `action_set_token` runs as the calling user so the Administrator-only
        ACL on the credential model stays live, and it clears the verification
        stamp so the old evidence cannot vouch for a new token.
        """
        store = self._resolve_store(store_id)
        if not isinstance(token, str) or not token.strip():
            raise UserError(_('Paste the Admin API access token to continue.'))
        Credential = self.env['shopify.connector.store.credential']
        if store.credential_present:
            Credential.action_replace_token(store, token.strip())
        else:
            Credential.action_set_token(store, token.strip())
        # Deliberate: the local name is rebound before any other statement, so
        # the value cannot survive into a traceback frame of the code below.
        token = None
        settings = self._settings_for(store)
        self._record_progress(settings, 'credential')
        return self.get_setup_state(store_id=store.id)

    @api.model
    def save_client_credentials(self, store_id, client_id, client_secret):
        """The credential step's OTHER path: a Dev Dashboard app (Wave 5).

        The sibling of `save_credential`, for the merchant Shopify's current
        app-creation flow actually produces: a Dev Dashboard app shows no
        permanent Admin API token to copy, and the connector exchanges the
        app's Client ID and Client secret for a 24-hour token itself
        (client-credentials grant, same-organization apps only).

        Exactly the same secrecy contract as the token path: the secret is
        handed to the credential service, the local name is rebound so no
        traceback frame can carry it, and the response is the ordinary setup
        state in which the credential appears only as booleans and non-secret
        expiry mirrors. No token exchange happens here -- entering credentials
        is configuration; the first exchange happens at Test Connection, which
        is the step that already owns "talk to Shopify and show the result".
        """
        store = self._resolve_store(store_id)
        if not isinstance(client_id, str) or not client_id.strip():
            raise UserError(_("Enter the app's Client ID to continue."))
        if not isinstance(client_secret, str) or not client_secret.strip():
            raise UserError(_("Enter the app's Client secret to continue."))
        self.env['shopify.connector.store.credential'].action_set_client_credentials(
            store, client_id.strip(), client_secret.strip(),
        )
        client_secret = None
        settings = self._settings_for(store)
        self._record_progress(settings, 'credential')
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Steps 4 and 5 -- scopes and test connection
    # ------------------------------------------------------------------

    @api.model
    def acknowledge_scopes(self, store_id):
        """Step 4 records only that the operator has read the list.

        The wizard does not grant scopes and must never imply that it does --
        the operator grants them in Shopify when creating the custom app, and
        the readiness check verifies them.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        self._record_progress(settings, 'scopes')
        return self.get_setup_state(store_id=store.id)

    @api.model
    def run_test_connection(self, store_id):
        """Step 5. The existing guarded probe, unchanged.

        A failure leaves the stored credential exactly as it was:
        `action_test_connection` writes only the non-secret result mirrors, so
        a mistyped token can be corrected by going back a step rather than by
        re-entering a credential that was silently discarded.
        """
        store = self._resolve_store(store_id)
        if not store.credential_present:
            raise UserError(_(
                'Enter the Admin API access token before testing the '
                'connection.'
            ))
        store.action_test_connection()
        store.invalidate_recordset()
        settings = self._settings_for(store)
        if store.last_test_connection_result == 'pass':
            self._record_progress(settings, 'test_connection')
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Step 11 -- final readiness, run against the saved configuration
    # ------------------------------------------------------------------

    @api.model
    def run_readiness(self, store_id):
        """Step 11. The accepted check set, with its accepted severity split.

        It runs LAST now, and that is the whole correction: every choice a
        check reads -- the domain flags, the location mappings -- has already
        been written by the time this executes, so the result describes the
        store the operator is about to activate rather than the empty one
        they started with.

        Nothing here decides readiness. `run_for_store` owns the verdict, and
        it reads stored evidence only: no Shopify request is made.
        """
        store = self._resolve_store(store_id)
        self.env['shopify.connector.readiness.check'].run_for_store(store)
        store.invalidate_recordset()
        settings = self._settings_for(store)
        self._clear_readiness_stale(settings)
        self._record_progress(settings, 'final_readiness')
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Steps 6 to 10 -- the durable choices
    # ------------------------------------------------------------------

    @api.model
    def save_directions(self, store_id, enabled_keys):
        """Step 6. Only accepted domains, and never silently.

        Enabling nothing is a valid outcome -- connect-only setup is
        explicitly permitted -- so this does not require a selection. What it
        does require is that every key it is given is one this install
        actually carries, so a client cannot enable a domain by inventing a
        field name.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        keys = set(enabled_keys or [])
        known = {domain['key'] for domain in self._domain_payload(settings)}
        unknown = keys - known
        if unknown:
            raise UserError(_(
                'This connector does not offer: %(names)s',
                names=', '.join(sorted(unknown)),
            ))
        values = {}
        changed = False
        for domain in self._domain_payload(settings):
            enabled = domain['key'] in keys
            values[domain['field']] = enabled
            if bool(settings[domain['field']]) != enabled:
                changed = True
        settings.sudo().write(values)
        if changed:
            # `domain_flag_enablement` and `mapped_location` both read these
            # flags, so a readiness result recorded before this write no
            # longer describes this store. Marked rather than deleted: the
            # evidence stays, and the surface stops calling it green.
            self._mark_readiness_stale(settings)
        self._record_progress(settings, 'directions')
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Step 7 -- location mapping (conditional on the inventory domain)
    # ------------------------------------------------------------------

    @api.model
    def acknowledge_location_mapping(self, store_id):
        """Step 7's Continue.

        Records progress and nothing else. It deliberately does NOT require a
        mapping to exist: whether a mapping is required is a readiness
        decision, made by `mapped_location` on the final-readiness step with
        the full picture, and duplicating that rule here would give an
        operator two different answers to the same question. It also
        deliberately enqueues nothing -- a step that silently contacted
        Shopify because somebody pressed Continue would be a surprise.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        self._record_progress(settings, 'location_mapping')
        return self.get_setup_state(store_id=store.id)

    @api.model
    def refresh_shopify_locations(self, store_id):
        """Ask Shopify for this store's locations, through the job queue.

        This method admits a JOB. It makes no Shopify request itself, and
        neither does anything else in this file: the request happens later,
        on the ordinary dispatcher, inside
        `_handle_inventory_location_sync`, which is the one governed place
        the `locations` query lives. The setup service, Owl, the wizards and
        the mapping views never hold a transport.

        Every authorization the inventory domain requires is re-checked
        inside the seam it delegates to, as the calling user -- this
        Administrator gate is in addition to those, not instead of them.
        """
        store = self._resolve_store(store_id)
        job = self._setup_refresh_locations(store)
        state = self.get_setup_state(store_id=store.id)
        # Bind the first response to the exact admitted/coalesced run too. The
        # next request echoes this id through `follow_location_refresh`.
        state['location_mapping']['refresh'] = (
            self._setup_follow_location_refresh(store, job.id)
        )
        return state

    @api.model
    def follow_location_refresh(self, store_id, job_id):
        """Follow one exact refresh and refresh readiness after its success."""
        store = self._resolve_store(store_id)
        refresh = self._setup_follow_location_refresh(store, job_id)
        settings = self._settings_for(store)
        if refresh['state'] == 'succeeded' and (
            not store.last_readiness_at
            or self._readiness_is_stale(store, settings)
        ):
            self.env['shopify.connector.readiness.check'].run_for_store(store)
            store.invalidate_recordset()
            self._clear_readiness_stale(settings)
        state = self.get_setup_state(store_id=store.id)
        # `get_setup_state` normally presents the newest refresh. Preserve the
        # exact identity this request followed even if another run now exists.
        state['location_mapping']['refresh'] = refresh
        return state

    @api.model
    def save_location_mapping(
        self, store_id, shopify_location_gid, odoo_location_id,
    ):
        """Map one cached Shopify location to one Odoo internal location.

        Both identities are EXPLICIT and both are validated on the server.
        The Shopify side must be an active location this store's own cache
        actually contains -- a GID typed into an RPC call is not an identity
        -- and the Odoo side must be a location this caller can already see,
        internal, and in a compatible company. None of that is decided here:
        it is decided by `create_or_update_location_mapping`, the one
        sanctioned creation service, which this delegates to through the
        domain seam.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        self._setup_create_location_mapping(
            store, shopify_location_gid, odoo_location_id,
        )
        # A new mapping is exactly what `mapped_location` reads, so any
        # earlier readiness result is now stale.
        self._mark_readiness_stale(settings)
        # The mapping is the evidence `mapped_location` reads. Recompute now so
        # the step never displays a stale readiness verdict after a successful
        # save; this is a local evidence read and makes no Shopify request.
        self.env['shopify.connector.readiness.check'].run_for_store(store)
        store.invalidate_recordset()
        self._clear_readiness_stale(settings)
        self._record_progress(settings, 'location_mapping')
        return self.get_setup_state(store_id=store.id)

    @api.model
    def save_source_of_truth(self, store_id, matching, price):
        """Step 8. Both required, neither defaulted."""
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        valid_matching = {c['value'] for c in SETUP_MATCHING_CHOICES}
        valid_price = {c['value'] for c in SETUP_PRICE_CHOICES}
        if matching not in valid_matching:
            raise UserError(_(
                'Choose which system is the source for your catalog. There is '
                'no default: this decides what happens to products that exist '
                'on only one side.'
            ))
        if price not in valid_price:
            raise UserError(_(
                'Choose which system is the price authority. There is no '
                'default: this decides whether Odoo prices can overwrite '
                'Shopify prices.'
            ))
        settings.sudo().write({
            'product_first_sync_source': matching,
            'price_source_of_truth': price,
        })
        self._record_progress(settings, 'source_of_truth')
        return self.get_setup_state(store_id=store.id)

    @api.model
    def save_notification(self, store_id, enabled, confirmed=False):
        """Step 9. Off by default; opting in takes an explicit confirmation.

        Both flags are written together because the fulfillment domain refuses
        to notify unless `notification_default_enabled` AND
        `fulfillment_notification_confirmed` are true -- the accepted RA-009
        fail-closed pair. Turning it on here without the confirmation would
        leave a store that looks opted-in on this screen and silently is not.

        Nothing is sent and nothing is scheduled by this step.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        enabled = bool(enabled)
        if enabled and not confirmed:
            raise UserError(_(
                'Turning this on means Shopify will email your customers when '
                'a delivery is fulfilled. Confirm that explicitly to enable '
                'it.'
            ))
        values = {'notification_default_enabled': enabled}
        if 'fulfillment_notification_confirmed' in settings._fields:
            values['fulfillment_notification_confirmed'] = enabled
        settings.sudo().write(values)
        self._record_progress(settings, 'notification')
        return self.get_setup_state(store_id=store.id)

    @api.model
    def save_first_push_schedule(self, store_id, schedule_now):
        """Step 10. Scheduling ONLY -- the first-push guard is untouched.

        This flips the scheduled stock-scan flag and nothing else. The scan
        enqueues a preview; the preview waits for an explicit confirmation
        before a single quantity reaches Shopify. Nothing here previews,
        confirms, admits a push job or writes to Shopify, and "scheduled" is
        never presented as "pushed".
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        if (
            settings.inventory_domain_enabled
            and 'inventory_scheduled_sync_enabled' in settings._fields
        ):
            settings.sudo().write({
                'inventory_scheduled_sync_enabled': bool(schedule_now),
            })
        self._record_progress(settings, 'first_push')
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Step 12 -- review and activate
    # ------------------------------------------------------------------

    @api.model
    def activate(self, store_id):
        """Step 12. Delegate to the existing activation, then hand off.

        `action_activate` keeps its whole evidence contract: a credential on
        record, verified after its last change, a passing test connection, and
        a readiness result no older than that verification. This adds one
        thing on top -- it refuses while an essential readiness check is
        failing, with the failing checks named -- because the operator is
        looking at those checks on this screen and a generic refusal here
        would be a worse message than the one they can already see.

        No synchronisation starts. No Shopify mutation occurs. No domain job
        is enqueued. Activation records that setup is complete and the
        dashboard takes over.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        # Re-run readiness against the configuration actually being activated.
        #
        # The step order now puts `final_readiness` after every choice a check
        # reads, so the operator-facing result and this one describe the same
        # store. This re-run stays anyway, and deliberately: the review step
        # is a screen an operator can sit on, and a setting can change in
        # another tab, in another session, or through the store form while
        # they do. `action_activate` requires the readiness result to be no
        # older than the credential verification for the same reason, one
        # level down.
        if store.credential_present:
            self.env['shopify.connector.readiness.check'].run_for_store(store)
            store.invalidate_recordset()
            self._clear_readiness_stale(settings)
        settings.invalidate_recordset()
        readiness = self._readiness_payload(store, settings)
        if not readiness['ran']:
            raise UserError(_(
                'Run the readiness checks before activating this store.'
            ))
        if readiness['blocking']:
            raise UserError(_(
                'These checks must pass before this store can be activated: '
                '%(names)s',
                names='; '.join(
                    check['label'] for check in readiness['blocking']
                ),
            ))
        if readiness['waiting']:
            raise UserError(_(
                'These checks have not finished, so this store cannot be '
                'activated yet: %(names)s',
                names='; '.join(
                    check['label'] for check in readiness['waiting']
                ),
            ))
        if store.state != 'connected':
            store.action_activate()
            store.invalidate_recordset()
        settings.sudo().write({
            'setup_wizard_step_key': 'review',
            'setup_wizard_step': SETUP_STEP_COUNT,
            'setup_completed_at': fields.Datetime.now(),
            'setup_completed_uid': self.env.uid,
        })
        store._create_lifecycle_audit_job(
            'Guided setup completed. actor_uid=%d store_id=%d domains=%s '
            'matching=%s price=%s notifications=%s.' % (
                self.env.uid, store.id,
                ','.join(
                    domain['key']
                    for domain in self._domain_payload(settings)
                    if domain['enabled']
                ) or 'none',
                settings.product_first_sync_source or 'unset',
                settings.price_source_of_truth or 'unset',
                'on' if settings.notification_default_enabled else 'off',
            )
        )
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Save & Exit, and re-run
    # ------------------------------------------------------------------

    @api.model
    def save_and_exit(self, store_id, step_key):
        """Record the last valid step so reopening resumes in the right place.

        Takes the SEMANTIC key and takes nothing else. An ordinal is
        deliberately refused rather than translated: a client that still
        sends `8` is a client built against the old order, and quietly
        interpreting that as whatever step is eighth today would resume an
        operator on a screen they never asked for. Refusing is loud, and
        loud is correct here.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        if not isinstance(step_key, str) or step_key not in SETUP_STEP_ORDER:
            raise UserError(_('That is not a setup step.'))
        recorded = self._record_progress(settings, step_key)
        return {
            'resume_step_key': recorded,
            'resume_step': setup_step_index(recorded),
        }

    @api.model
    def restart_setup(self, store_id):
        """Re-run setup on a store that is already set up.

        Deliberately non-destructive: it moves the resume point back to the
        first step and records who re-ran it. Every stored choice stays exactly
        as it is, so re-running to check one setting cannot silently undo the
        others -- the operator changes what they mean to change and leaves the
        rest alone.
        """
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        settings.sudo().write({
            'setup_wizard_step_key': SETUP_STEP_KEYS[0],
            'setup_wizard_step': 1,
            'setup_last_rerun_at': fields.Datetime.now(),
            'setup_last_rerun_uid': self.env.uid,
        })
        store._create_lifecycle_audit_job(
            'Guided setup re-run started. actor_uid=%d store_id=%d.'
            % (self.env.uid, store.id)
        )
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # The entry points (Dashboard, Configuration, store/settings re-run)
    # ------------------------------------------------------------------

    @api.model
    def action_open_setup_wizard(self, store_id=None):
        """Open the client action. Administrator-gated on the server too."""
        self._assert_setup_admin()
        context = {}
        if store_id:
            self._resolve_store(store_id)
            context['default_setup_store_id'] = int(store_id)
        return {
            'type': 'ir.actions.client',
            'tag': 'shopify_connector_setup_wizard',
            'name': _('Shopify Connector Setup'),
            'target': 'current',
            'context': context,
        }


class ShopifyConnectorStoreSetupEntry(models.Model):
    """The re-run entry point on the store record itself."""

    _inherit = 'shopify.connector.store'

    def action_shopify_rerun_setup(self):
        """Third entry route: re-run setup from the store this store is.

        The Administrator check, record access and company consistency all run
        inside `restart_setup`; this is only the button that reaches it.
        """
        self.ensure_one()
        Setup = self.env['shopify.connector.setup.wizard']
        Setup.restart_setup(self.id)
        return Setup.action_open_setup_wizard(store_id=self.id)
