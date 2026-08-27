"""The inventory domain's side of the guided setup's Location mapping step.

WHAT THIS FILE IS
-----------------
Three overrides of the seams `shopify.connector.setup.wizard` declares, in
exactly the shape `_get_checks`, `_accepted_domain_flags` and
`_governed_scope_catalog` already use: ordinary Odoo model inheritance on an
`AbstractModel`, loaded only when this addon is installed.

Core declares the seams and cannot implement them. It owns no mapping concept,
has no `shopify.connector.location.mapping` table, and must not grow either --
a database with `shopify_connector_core` and no inventory addon has to keep
working, and the setup wizard has to keep rendering there. So core's base
implementations say "not available in this database" and this file replaces
them with the real thing.

WHAT THIS FILE DOES NOT DO
--------------------------
It makes no Shopify request and holds no transport. A refresh is a JOB
admission (`action_refresh_shopify_locations`), and the request itself happens
later, on the ordinary dispatcher, inside `_handle_inventory_location_sync`.
It decides no authorization of its own either: every one of the three methods
delegates to the inventory service, which re-checks role, record visibility
and company as the calling user before anything elevates.
"""

import hashlib

from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

#: How many rows the two lists on the Location mapping step will render. A
#: setup screen is a place to make a decision, not a place to page through a
#: warehouse tree: a merchant with more Odoo locations than this maps them
#: from the Location Mapping workspace, which is a list view with search.
#: Named rather than inlined so the limit is visible to a reader and to a test.
SETUP_LOCATION_LIST_LIMIT = 200

#: One page of the mapping step's bounded server-side search (Wave 5). The
#: search -- not the first page -- is what makes every eligible location
#: reachable: the payload above may show a bounded batch, but a merchant with
#: 300 cached Shopify locations or a deep warehouse tree types a few letters
#: and gets the exact rows, paged, instead of a disclosure that the list is
#: incomplete.
SETUP_LOCATION_SEARCH_PAGE = 50


class ShopifyConnectorSetupWizardInventoryExtension(models.AbstractModel):
    """Seam: the `location_mapping` step's data and its two actions."""

    _inherit = 'shopify.connector.setup.wizard'

    @api.model
    def _activation_post_transition(self, store, settings):
        """Queue current-generation location proof during activation."""
        result = super()._activation_post_transition(store, settings)
        if not settings.inventory_domain_enabled:
            return result
        refresh = self.env[
            'shopify.connector.inventory.service'
        ].location_refresh_state(store)
        if refresh.get('state') != 'succeeded':
            self.env[
                'shopify.connector.inventory.service'
            ]._setup_refresh_shopify_locations(store.id)
        return result

    @api.model
    def _activation_requirement_status(self, store, settings):
        """Require fresh locations and valid mappings in this generation."""
        parent = super()._activation_requirement_status(store, settings)
        if parent.get('state') != 'ready':
            return parent
        if not settings.inventory_domain_enabled:
            return parent
        payload = self._setup_location_payload(store, settings)
        refresh = payload.get('refresh') or {}
        state = refresh.get('state')
        if state in ('waiting', 'running'):
            return {
                'state': 'pending',
                'code': 'location_proof_pending',
                'job_id': refresh.get('job_id'),
                'message': (
                    'Connected; verifying Shopify locations for this '
                    'connection before setup completes. Location job #%s is '
                    '%s.' % (refresh.get('job_id'), state)
                ),
            }
        if state == 'succeeded' and payload.get('mapping_complete'):
            return parent
        if state == 'failed':
            message = refresh.get('reason') or (
                'The Shopify location verification did not finish safely.'
            )
        elif state == 'succeeded':
            message = (
                '%d active Shopify location(s) still need an explicit Odoo '
                'location mapping.' % payload.get('unmapped_count', 0)
            )
        else:
            message = (
                'Shopify locations have not been verified for the current '
                'connection.'
            )
        return {
            'state': 'action_required',
            'code': 'location_proof_required',
            'job_id': refresh.get('job_id'),
            'message': message,
        }

    @api.model
    def _activation_completion_policy(self, store, settings):
        parent = super()._activation_completion_policy(store, settings)
        if parent and not parent.get('complete', True):
            return parent
        status = self._activation_requirement_status(store, settings)
        if status.get('state') == 'ready':
            return parent
        return {
            'complete': False,
            'job_id': status.get('job_id'),
            'message': status.get('message'),
        }

    @api.model
    def _activation_completion_guard(self, store, settings):
        if not super()._activation_completion_guard(store, settings):
            return False
        return self._activation_requirement_status(
            store, settings,
        ).get('state') == 'ready'

    @api.model
    def _setup_location_payload(self, store, settings):
        """Cached Shopify locations, their mapping state, and the Odoo targets.

        Every value here is derived from rows this caller can already see.
        The Shopify side comes from this store's own location cache, which is
        read through the inventory service (elevated, store-scoped, read-only
        -- the cache carries no group create/write by design). The Odoo side
        is searched as the CALLING user, so ordinary record rules and the
        company switcher decide what appears; a location in another company
        is not listed, and would be refused by the creation service anyway.

        Nothing here is authoritative for a decision. Whether a mapping is
        REQUIRED is `mapped_location`'s call on the final-readiness step, and
        this payload only says what is and is not mapped.
        """
        if not store:
            return super()._setup_location_payload(store, settings)
        Service = self.env['shopify.connector.inventory.service']
        Location = self.env['shopify.connector.location']
        Mapping = self.env['shopify.connector.location.mapping']

        active_domain = [
            ('store_id', '=', store.id),
            ('shopify_location_active', '=', True),
        ]
        all_active = Location.sudo().search(
            active_domain, order='name asc, id asc',
        )
        cached = all_active[:SETUP_LOCATION_LIST_LIMIT]
        active_gids = all_active.mapped('shopify_location_gid')
        mappings = Mapping.search([
            ('store_id', '=', store.id),
            ('shopify_gid', 'in', active_gids),
        ]) if active_gids else Mapping.browse()
        by_gid = {mapping.shopify_gid: mapping for mapping in mappings}

        locations = []
        for row in cached:
            mapping = by_gid.get(row.shopify_location_gid)
            locations.append({
                'shopify_gid': row.shopify_location_gid,
                'name': row.name or row.shopify_location_gid,
                'mapped': bool(mapping),
                'mapping_id': mapping.id if mapping else False,
                'odoo_location_id': (
                    mapping.odoo_location_id.id if mapping else False
                ),
                'odoo_location_name': (
                    mapping.odoo_location_id.display_name if mapping else ''
                ),
                'push_enabled': bool(mapping.push_enabled) if mapping else False,
            })
        mapped_count = len(mappings)
        shopify_total = len(all_active)
        unmapped_count = max(shopify_total - mapped_count, 0)
        refresh = Service.location_refresh_state(store)
        mapping_complete = bool(
            refresh.get('state') == 'succeeded'
            and shopify_total
            and not unmapped_count
        )

        return {
            'available': True,
            'reason': '',
            'locations': locations,
            'odoo_locations': self._setup_eligible_odoo_locations(store),
            'refresh': refresh,
            'mapped_count': mapped_count,
            'unmapped_count': unmapped_count,
            # What `mapped_location` needs to pass, restated for the surface
            # so the step and the readiness row cannot disagree about it.
            'has_valid_mapping': mapping_complete,
            'mapping_complete': mapping_complete,
            'truncated': shopify_total > SETUP_LOCATION_LIST_LIMIT,
            # Honest totals for the "Showing X of Y" line and for deciding
            # whether the search affordance is worth surfacing prominently.
            'shopify_total': shopify_total,
            'odoo_total': self._eligible_odoo_location_count(store),
        }

    @api.model
    def _eligible_odoo_location_count(self, store):
        """How many internal Odoo locations this caller could map, in total."""
        domain = [('usage', '=', 'internal')]
        company = store.company_id
        if company:
            domain.append(('company_id', 'in', [False, company.id]))
        try:
            return self.env['stock.location'].search_count(domain)
        except AccessError:
            return 0

    @api.model
    def _setup_eligible_odoo_locations(self, store):
        """Internal Odoo stock locations this caller may map, or an empty list.

        Searched as the calling user on purpose. A Shopify Connector
        Administrator is not necessarily an Odoo Inventory user, and Odoo's
        own `stock.location` access is what decides whether they may see a
        warehouse -- not this connector. When they may not, the list is empty
        and the step says so, which is a truthful screen; it is never
        elevated to show locations the operator has no right to, because the
        creation service would refuse them at the next click anyway and a
        list of unusable choices is worse than an honest empty one.
        """
        Location = self.env['stock.location']
        domain = [('usage', '=', 'internal')]
        company = store.company_id
        if company:
            domain.append(('company_id', 'in', [False, company.id]))
        try:
            locations = Location.search(
                domain,
                order='complete_name asc, id asc',
                limit=SETUP_LOCATION_LIST_LIMIT,
            )
        except AccessError:
            return []
        return [
            {'id': location.id, 'name': location.display_name}
            for location in locations
        ]

    @api.model
    def _setup_refresh_locations(self, store):
        """Admit the governed refresh job. No transport, no direct call."""
        return self.env[
            'shopify.connector.inventory.service'
        ]._setup_refresh_shopify_locations(store.id)

    @api.model
    def _setup_follow_location_refresh(self, store, job_id):
        """Follow the exact admitted run, never whichever run is newest."""
        return self.env[
            'shopify.connector.inventory.service'
        ].location_refresh_state(store, job_id=job_id)

    @api.model
    def _setup_search_locations(self, store, side, query, offset):
        """One bounded page of eligible locations, filtered server-side.

        The reachability route for a store whose location count exceeds the
        step's first page (Wave 5): every ELIGIBLE row -- active cached
        Shopify locations of THIS store, or internal Odoo locations the
        CALLING user may see in this store's company -- is reachable through
        a bounded, paginated, case-insensitive name search. The store and
        company filters are structural on every page: `store_id` is a
        mandatory term on the cache query, and the Odoo side is searched as
        the calling user with the same company domain the payload uses, so
        no page and no query can ever widen scope.

        NOT "INDEXED", AND THE WORD IS DELIBERATELY GONE (Batch 1 correction).
        This previously claimed an indexed search. `shopify.connector.location`
        indexes `store_id`, `company_id` and `shopify_location_gid`; it does NOT
        index `name`, and no btree index can serve `ilike '%term%'` anyway --
        that needs a trigram index, which needs the `pg_trgm` extension, which
        needs privileges this connector does not assume it has on a customer
        database. What actually bounds the work is the `store_id` index plus the
        50-row page: PostgreSQL selects one store's cached locations by index
        and scans only those. That is honest and it is sufficient at the scale
        this surface exists for; claiming an index that is not there would make
        a performance promise nothing in the schema keeps.

        `stock.location.complete_name` is Odoo's own column and whatever index
        it carries is Odoo's business; no claim is made about it here.
        """
        empty = self._setup_search_empty_page(store, side, query, offset)
        if not store:
            return dict(empty, empty_reason='no_store')
        if side == 'shopify':
            Location = self.env['shopify.connector.location']
            Mapping = self.env['shopify.connector.location.mapping']
            domain = [
                ('store_id', '=', store.id),
                ('shopify_location_active', '=', True),
            ]
            if query:
                domain.append(('name', 'ilike', query))
            total = Location.sudo().search_count(domain)
            rows = Location.sudo().search(
                domain, order='name asc, id asc',
                limit=SETUP_LOCATION_SEARCH_PAGE, offset=offset,
            )
            mappings = Mapping.search([
                ('store_id', '=', store.id),
                ('shopify_gid', 'in', [
                    row.shopify_location_gid for row in rows
                ]),
            ])
            by_gid = {m.shopify_gid: m for m in mappings}
            items = []
            for row in rows:
                mapping = by_gid.get(row.shopify_location_gid)
                items.append({
                    'shopify_gid': row.shopify_location_gid,
                    'name': row.name or row.shopify_location_gid,
                    'mapped': bool(mapping),
                    'mapping_id': mapping.id if mapping else False,
                    'odoo_location_id': (
                        mapping.odoo_location_id.id if mapping else False
                    ),
                    'odoo_location_name': (
                        mapping.odoo_location_id.display_name
                        if mapping else ''
                    ),
                    'push_enabled': (
                        bool(mapping.push_enabled) if mapping else False
                    ),
                })
            return self._setup_search_page(
                store, side, query, offset, items, total,
                empty_reason=(
                    'no_results' if (query and not total)
                    else ('no_cached_locations' if not total else False)
                ),
            )
        # side == 'odoo' -- searched as the calling user, deliberately, for
        # the same reason `_setup_eligible_odoo_locations` is: Odoo's own
        # `stock.location` access decides what this operator may see.
        domain = [('usage', '=', 'internal')]
        company = store.company_id
        if company:
            domain.append(('company_id', 'in', [False, company.id]))
        if query:
            domain.append(('complete_name', 'ilike', query))
        Location = self.env['stock.location']
        try:
            total = Location.search_count(domain)
            rows = Location.search(
                domain, order='complete_name asc, id asc',
                limit=SETUP_LOCATION_SEARCH_PAGE, offset=offset,
            )
        except AccessError:
            # DISTINCT from "your search matched nothing". This operator cannot
            # read `stock.location` at all, and the surface must say so rather
            # than let them conclude their warehouse does not exist.
            return dict(empty, empty_reason='no_inventory_permission')
        return self._setup_search_page(
            store, side, query, offset,
            [{'id': row.id, 'name': row.display_name} for row in rows],
            total,
            empty_reason=(
                'no_results' if (query and not total)
                else ('no_eligible_odoo_locations' if not total else False)
            ),
        )

    # ------------------------------------------------------------------
    # The search page contract (Batch 1 correction, §10)
    # ------------------------------------------------------------------

    @api.model
    def _setup_search_continuation(self, store, side, query):
        """A token binding a continuation to the exact query it belongs to.

        `offset` alone is not a continuation. Paging with a bare offset lets a
        client carry position from one result set into another -- change the
        query, or the side, or the store, and page 2 of the new set is fetched
        at page 2 of the OLD one, which skips rows and can repeat them. The
        client must send this token back with every `load more`, and a token
        that does not describe the request it arrives with is refused.

        Non-secret and non-guessable-is-not-the-point: this is an integrity
        binding, not an authorisation. Authorisation is `_resolve_store`, which
        runs on every request regardless of what token is presented.
        """
        return '%s|%s|%s|%s' % (
            store.id if store else 0,
            store.company_id.id if (store and store.company_id) else 0,
            side,
            hashlib.sha256((query or '').encode()).hexdigest()[:16],
        )

    @api.model
    def _setup_search_page(self, store, side, query, offset, items, total,
                           empty_reason=False):
        """One page, with an explicit continuation the client must not compute.

        `next_offset` is the server's own arithmetic and is `False` once the set
        is exhausted. The client previously derived the next offset from the
        LENGTH OF ITS OWN ACCUMULATED ARRAY, which is a different number the
        moment the server returns a short page, a row is removed between pages,
        or a response arrives out of order -- and the failure mode is silently
        skipped or duplicated locations, in a list whose whole purpose is that
        every eligible location is reachable.
        """
        shown = offset + len(items)
        return {
            'items': items,
            'total': total,
            'offset': offset,
            'limit': SETUP_LOCATION_SEARCH_PAGE,
            'next_offset': shown if (items and shown < total) else False,
            'continuation': self._setup_search_continuation(store, side, query),
            'empty_reason': empty_reason,
        }

    @api.model
    def _setup_search_empty_page(self, store, side, query, offset):
        """The fail-closed page. Position 0, no continuation to follow."""
        return {
            'items': [], 'total': 0, 'offset': 0,
            'limit': SETUP_LOCATION_SEARCH_PAGE,
            'next_offset': False,
            'continuation': self._setup_search_continuation(store, side, query),
            'empty_reason': False,
        }

    @api.model
    def _setup_create_location_mapping(
        self, store, shopify_location_gid, odoo_location_id,
    ):
        """Create one mapping through the one sanctioned creation service.

        The Odoo location is browsed and handed over WITHOUT being validated
        here. That is deliberate: `create_or_update_location_mapping` already
        resolves it in the caller's own environment, checks that it exists,
        is internal, is company-compatible and is not already bound, and
        checks that the Shopify GID names an active location of this store.
        Repeating any of that here would create a second copy of a rule that
        must have exactly one.
        """
        if not odoo_location_id:
            raise UserError(_('Choose an Odoo location to map this to.'))
        try:
            odoo_location_id = int(odoo_location_id)
        except (TypeError, ValueError):
            raise UserError(_('That is not an Odoo location.'))
        odoo_location = self.env['stock.location'].browse(odoo_location_id)
        return self.env[
            'shopify.connector.inventory.service'
        ].create_or_update_location_mapping(
            store, odoo_location, shopify_location_gid,
        )
