"""S1: the 11-step guided setup wizard's server side.

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
SETUP_STEPS = (
    ('welcome', 'Welcome'),
    ('identity', 'Store identity'),
    ('credential', 'Credentials'),
    ('scopes', 'Permissions'),
    ('test_connection', 'Test connection'),
    ('readiness', 'Readiness checks'),
    ('directions', 'What to sync'),
    ('source_of_truth', 'Source of truth'),
    ('notification', 'Customer notifications'),
    ('first_push', 'First stock push'),
    ('review', 'Review and activate'),
)

SETUP_STEP_COUNT = len(SETUP_STEPS)

#: Step 7. Only DEC-003-supported directions appear. An unsupported direction
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

#: Step 8. Both choices are required and NEITHER is pre-selected: converting an
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

    @api.model
    def _record_progress(self, settings, step_index):
        """Advance the durable resume point, never rewind it.

        Monotonic on purpose: paging Back to re-read step 4 must not throw away
        the fact that steps 5 and 6 were already completed, or Back would
        quietly become a destructive control.
        """
        if step_index > settings.setup_wizard_step:
            settings.sudo().write({'setup_wizard_step': step_index})
        return settings.setup_wizard_step

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
        """The scopes Shopify last reported, as a set. Never a live call."""
        if not store or not store.granted_scopes:
            return set()
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
        payload = {
            'steps': [
                {'index': index, 'key': key, 'label': label}
                for index, (key, label) in enumerate(SETUP_STEPS, start=1)
            ],
            'step_count': SETUP_STEP_COUNT,
            'resume_step': settings.setup_wizard_step if settings else 1,
            'store': self._store_payload(store, settings),
            'stores': [
                {'id': candidate.id, 'name': candidate.display_name}
                for candidate in candidates
            ],
            'scopes': self._setup_required_scopes(store) if store else [],
            'domains': self._domain_payload(settings),
            'matching_choices': list(SETUP_MATCHING_CHOICES),
            'price_choices': list(SETUP_PRICE_CHOICES),
            'readiness': self._readiness_payload(store),
            'summary': self._summary_payload(store, settings),
        }
        return payload

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

    @api.model
    def _readiness_payload(self, store):
        """The last recorded readiness result, per check.

        Stored evidence only -- reading this screen never runs a check and
        never calls Shopify. Step 6 runs them explicitly.
        """
        empty = {
            'ran': False, 'overall': False, 'checks': [], 'blocking': [],
        }
        if not store or not store.last_readiness_at:
            return empty
        checks = self._last_readiness_checks(store)
        if not checks:
            return dict(empty, ran=True, overall=store.last_readiness_result)
        return {
            'ran': True,
            'overall': store.last_readiness_result,
            'checks': checks,
            'blocking': [
                check for check in checks
                if check['tier'] == 'essential' and check['result'] != 'pass'
            ],
        }

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
                'label': self._readiness_label(entry.get('code')),
                'tier': entry.get('tier') or 'warning',
                'result': entry.get('result') or 'not_proven',
                'tone': self._readiness_tone(
                    entry.get('tier'), entry.get('result'),
                ),
                'reason': entry.get('reason') or '',
                'owner': self._readiness_owner(entry.get('code')),
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
            'mapped_location': _('A Shopify location is mapped to a warehouse'),
            'cron_queue_health': _('Background jobs are running'),
            'domain_flag_enablement': _('At least one thing is set to sync'),
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
        }.get(code, _('Administrator'))

    @api.model
    def _readiness_tone(self, tier, result):
        if result == 'pass':
            return 'success'
        return 'danger' if tier == 'essential' else 'warning'

    @api.model
    def _summary_payload(self, store, settings):
        """Step 11, in plain words rather than as a pass/fail grid."""
        if not store or not settings:
            return {
                'domains': [], 'matching': '', 'price': '',
                'notification': '', 'first_push': '', 'can_activate': False,
                'blocking': [],
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
        readiness = self._readiness_payload(store)
        return {
            'domains': enabled,
            'matching': matching,
            'price': price,
            'notification': self._notification_summary(settings),
            'first_push': self._first_push_summary(settings),
            'can_activate': bool(
                readiness['ran'] and not readiness['blocking']
            ),
            'blocking': readiness['blocking'],
            'already_active': store.state == 'connected',
        }

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
        self._record_progress(settings, 2)
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
        self._record_progress(settings, 3)
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Steps 4, 5 and 6 -- scopes, test connection, readiness
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
        self._record_progress(settings, 4)
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
            self._record_progress(settings, 5)
        return self.get_setup_state(store_id=store.id)

    @api.model
    def run_readiness(self, store_id):
        """Step 6. The accepted check set, with its accepted severity split."""
        store = self._resolve_store(store_id)
        self.env['shopify.connector.readiness.check'].run_for_store(store)
        store.invalidate_recordset()
        settings = self._settings_for(store)
        self._record_progress(settings, 6)
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Steps 7 to 10 -- the durable choices
    # ------------------------------------------------------------------

    @api.model
    def save_directions(self, store_id, enabled_keys):
        """Step 7. Only accepted domains, and never silently.

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
        for domain in self._domain_payload(settings):
            values[domain['field']] = domain['key'] in keys
        settings.sudo().write(values)
        self._record_progress(settings, 7)
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
        self._record_progress(settings, 8)
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
        self._record_progress(settings, 9)
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
        self._record_progress(settings, 10)
        return self.get_setup_state(store_id=store.id)

    # ------------------------------------------------------------------
    # Step 11 -- review and activate
    # ------------------------------------------------------------------

    @api.model
    def activate(self, store_id):
        """Step 11. Delegate to the existing activation, then hand off.

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
        # The accepted step order puts readiness at 6 and the domain, ownership
        # and notification choices at 7-10, so the result an operator saw on
        # step 6 describes a store that did not yet have any of them. Two of
        # the accepted checks -- `domain_flag_enablement` and `mapped_location`
        # -- read exactly those choices, so judging activation on the step-6
        # run would judge it on stale evidence. `action_activate` requires the
        # readiness result to be no older than the credential verification for
        # the same reason, one level down.
        if store.credential_present:
            self.env['shopify.connector.readiness.check'].run_for_store(store)
            store.invalidate_recordset()
        readiness = self._readiness_payload(store)
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
        if store.state != 'connected':
            store.action_activate()
            store.invalidate_recordset()
        settings.sudo().write({
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
    def save_and_exit(self, store_id, step_index):
        """Record the last valid step so reopening resumes in the right place."""
        store = self._resolve_store(store_id)
        settings = self._settings_for(store)
        try:
            step_index = int(step_index)
        except (TypeError, ValueError):
            raise UserError(_('That is not a setup step.'))
        if not 1 <= step_index <= SETUP_STEP_COUNT:
            raise UserError(_('That is not a setup step.'))
        self._record_progress(settings, step_index)
        return {'resume_step': settings.setup_wizard_step}

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
