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

        cached = Location.sudo().search(
            [
                ('store_id', '=', store.id),
                ('shopify_location_active', '=', True),
            ],
            order='name asc, id asc',
            limit=SETUP_LOCATION_LIST_LIMIT,
        )
        mappings = Mapping.search([('store_id', '=', store.id)])
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
        mapped_count = sum(1 for entry in locations if entry['mapped'])

        return {
            'available': True,
            'reason': '',
            'locations': locations,
            'odoo_locations': self._setup_eligible_odoo_locations(store),
            'refresh': Service.location_refresh_state(store),
            'mapped_count': mapped_count,
            'unmapped_count': len(locations) - mapped_count,
            # What `mapped_location` needs to pass, restated for the surface
            # so the step and the readiness row cannot disagree about it.
            'has_valid_mapping': bool(mappings),
            'truncated': len(cached) >= SETUP_LOCATION_LIST_LIMIT,
            # Honest totals for the "Showing X of Y" line and for deciding
            # whether the search affordance is worth surfacing prominently.
            'shopify_total': Location.sudo().search_count([
                ('store_id', '=', store.id),
                ('shopify_location_active', '=', True),
            ]),
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
        ].action_refresh_shopify_locations(store.id)

    @api.model
    def _setup_search_locations(self, store, side, query, offset):
        """One bounded page of eligible locations, filtered server-side.

        The reachability route for a store whose location count exceeds the
        step's first page (Wave 5): every ELIGIBLE row -- active cached
        Shopify locations of THIS store, or internal Odoo locations the
        CALLING user may see in this store's company -- is reachable through
        an indexed, paginated, case-insensitive name search. The store and
        company filters are structural on every page: `store_id` is a
        mandatory term on the cache query, and the Odoo side is searched as
        the calling user with the same company domain the payload uses, so
        no page and no query can ever widen scope.
        """
        if not store:
            return {'items': [], 'total': 0, 'offset': 0,
                    'limit': SETUP_LOCATION_SEARCH_PAGE}
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
            return {'items': items, 'total': total, 'offset': offset,
                    'limit': SETUP_LOCATION_SEARCH_PAGE}
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
            return {'items': [], 'total': 0, 'offset': 0,
                    'limit': SETUP_LOCATION_SEARCH_PAGE}
        return {
            'items': [
                {'id': row.id, 'name': row.display_name} for row in rows
            ],
            'total': total,
            'offset': offset,
            'limit': SETUP_LOCATION_SEARCH_PAGE,
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
