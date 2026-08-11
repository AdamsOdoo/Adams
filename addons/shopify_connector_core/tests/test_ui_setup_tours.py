"""S1: the guided setup wizard, driven in a real browser.

The server tests in `test_setup_wizard.py` prove every step's method is correct
and correctly guarded. They cannot prove there is a control that reaches it.

That distinction is the whole reason S1 was recorded as not implemented while
its pieces existed: a credential service, a readiness registry, settings
fields and an activation contract were all present and correct, and there was
no route through them. A browser is the only place "the operator can get from
nothing to an activated store" is a testable claim.

These tours contact no Shopify store. Connection probes are answered by a
stand-in installed on the module's existing `_send` transport seam. Location
refresh execution and admission leases have dedicated server and lifecycle
tests; the browser tests seed their terminal records and prove the operator can
see the result, recover the same failed run, and reopen the refreshed state.
"""

import json
from unittest.mock import patch

from odoo import fields
from odoo.tests.common import HttpCase, new_test_user, tagged

from .test_api_client import FakeResponse

TOUR_SHOP_DOMAIN = 's1-tour.myshopify.com'
RESUME_SHOP_DOMAIN = 's1-resume.myshopify.com'
REFRESH_SHOP_DOMAIN = 's1-refresh.myshopify.com'
REFRESH_FAILURE_SHOP_DOMAIN = 's1-refresh-failure.myshopify.com'
REFRESH_DUMMY_TOKEN = 'shpat_S1REFRESH0000000000000000000000'


@tagged('post_install', '-at_install', 'shopify_connector_s1')
class TestUiSetupTours(HttpCase):

    def _admin(self, login):
        user = new_test_user(
            self.env, login=login, password=login,
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_admin',
        )
        user.sudo().write({
            'company_id': self.env.company.id,
            'company_ids': [(6, 0, [self.env.company.id])],
        })
        return user

    def _transport(self, domain):
        """Answer the ONE transport method locally, for exactly one domain.

        The granted-scope set is the connector's OWN declaration rather than a
        hand-written list: the traversal has to reach activation, and
        `required_scopes` is an essential readiness check, so a fixture that
        granted fewer scopes than the connector requires would block the tour
        for a reason that has nothing to do with the wizard.
        """
        Client = type(self.env['shopify.connector.api.client'])
        scopes = self.env[
            'shopify.connector.readiness.check'
        ].REQUIRED_MVP_SCOPES
        response = FakeResponse(200, json_body={
            'data': {
                'shop': {
                    'id': 'gid://shopify/Shop/1',
                    'name': 'S1 Tour Shop',
                    'myshopifyDomain': domain,
                },
                'currentAppInstallation': {
                    'accessScopes': [
                        {'handle': scope} for scope in scopes
                    ],
                },
            },
        })

        def responder(_self, _store, request, token=None,
                      mutation_context=None):
            return response

        return patch.object(Client, '_send', responder)

    def _make_readiness_passable(self):
        """Satisfy the environment-owned essential checks.

        `web.base.url` is an essential check and a test server's default is
        plain HTTP, so without this the traversal is blocked by the ENVIRONMENT
        rather than by anything the wizard did -- and a tour that can never
        reach activation cannot prove activation is reachable.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'https://s1-tour.example.test',
        )

    def test_setup_wizard_traverses_all_twelve_steps(self):
        """Nothing to an activated store, through the browser, in order.

        The tour asserts the step COUNT as well as each step's name at every
        stop ("Step 4 of 12"), so a dropped, added or reordered step fails
        here rather than passing quietly. It also asserts the two Wave 5
        corrections that only exist on screen: that the conditional location
        step is rendered as Not required rather than removed, and that
        readiness runs after the choices it reads rather than before them.
        """
        self._admin('s1_tour_admin')
        self._make_readiness_passable()
        self.env.flush_all()
        with self._transport(TOUR_SHOP_DOMAIN):
            self.start_tour(
                '/odoo', 'shopify_connector_s1_setup_tour',
                login='s1_tour_admin',
            )
        store = self.env['shopify.connector.store'].sudo().search(
            [('shop_domain', '=', TOUR_SHOP_DOMAIN)], limit=1,
        )
        self.assertTrue(store, 'the browser traversal created no store')
        self.assertEqual(
            store.state, 'connected',
            'the traversal did not reach an activated store',
        )
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        self.assertTrue(settings.setup_completed_at)
        self.assertEqual(settings.setup_completed_uid.login, 's1_tour_admin')
        self.assertTrue(
            settings.sale_domain_enabled,
            'the direction chosen in the browser did not persist',
        )
        self.assertEqual(settings.product_first_sync_source, 'odoo_source')
        self.assertEqual(settings.price_source_of_truth, 'odoo_authoritative')
        self.assertFalse(
            settings.notification_default_enabled,
            'the notification default must stay off unless opted into',
        )
        # Activation starts nothing.
        self.assertFalse(
            self.env['shopify.connector.job'].sudo().search([
                ('store_id', '=', store.id),
                ('state', 'in', ('queued', 'running')),
            ]),
            'activation enqueued a job',
        )
        # And the credential never came back out.
        logs = self.env['shopify.connector.job.log'].sudo().search([
            ('store_id', '=', store.id),
        ])
        blob = ' '.join(
            (logs.mapped('message') or [])
            + [str(v) for v in logs.mapped('technical_detail') if v]
            + [str(v) for v in logs.mapped('payload_snapshot') if v]
        )
        self.assertNotIn('shpat_', blob, 'a token reached the audit trail')

    def test_the_dashboard_empty_state_opens_setup(self):
        """Entry route 1 of 3, clicked rather than asserted from a payload."""
        self._admin('s1_dash_admin')
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_dashboard_entry_tour',
            login='s1_dash_admin',
        )

    def _seed_resumable_store(self):
        """A store left mid-setup under the PRE-Wave-5 numeric progress.

        Seeded exactly as an existing database holds it: `setup_wizard_step`
        set, `setup_wizard_step_key` absent. That is deliberate -- it makes
        this tour the browser-level proof of the warm progress translation as
        well as of resume, since legacy 7 has to reappear as the `directions`
        step under the new order rather than as whatever is seventh now.
        """
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'S1 Resume Store',
            'shop_domain': RESUME_SHOP_DOMAIN,
            'company_id': self.env.company.id,
        })
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'sale_domain_enabled': True,
            'setup_wizard_step': 7,
        })
        return store

    def test_setup_resumes_at_the_step_it_was_left_on(self):
        """Save & Exit and resume, observed in the browser.

        Durable progress is only durable if the NEXT session sees it, which is
        why the resume point is a column on the settings record rather than
        anything in this browser's storage.
        """
        self._admin('s1_resume_admin')
        store = self._seed_resumable_store()
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_resume_tour',
            login='s1_resume_admin',
        )
        settings = self.env['shopify.connector.store.settings'].sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )
        self.assertEqual(
            settings.setup_wizard_step_key, 'directions',
            'Save & Exit rewound the resume point, or the legacy numeric '
            'progress was not translated',
        )
        self.assertTrue(
            settings.sale_domain_enabled,
            'resuming discarded a saved choice',
        )

    def test_setup_is_operable_by_keyboard_alone(self):
        """Full keyboard traversal, and focus moves to the step heading.

        Asserted in the page rather than inferred from the stylesheet: a
        `tabindex` that exists in the template and a heading that actually
        receives focus after an advance are different claims.
        """
        self._admin('s1_keyboard_admin')
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_keyboard_tour',
            login='s1_keyboard_admin',
        )

    # ------------------------------------------------------------------
    # Wave 5: the location step and the readiness deep link, in a browser
    # ------------------------------------------------------------------

    LOCATION_SHOP_DOMAIN = 's1-location.myshopify.com'
    READINESS_SHOP_DOMAIN = 's1-readiness.myshopify.com'

    def _seed_inventory_store(self, domain, cached, mapped_gid=None,
                              resume='location_mapping'):
        """A store with inventory on, its cache populated, and a resume point.

        The Shopify location cache is seeded as ROWS rather than fetched: the
        governed refresh route has its own server tests, and a tour that
        admitted a job would be waiting on a dispatcher it does not control.
        What only a browser can show is the RENDERING -- mapped versus
        unmapped, the visible identity, the refresh state and the create
        control -- which is what these two tours are for.
        """
        store = self.env['shopify.connector.store'].sudo().create({
            'name': 'S1 Location Store',
            'shop_domain': domain,
            'company_id': self.env.company.id,
            'credential_present': True,
            'credential_last_verified_at': fields.Datetime.now(),
            'last_test_connection_result': 'pass',
        })
        self.env['shopify.connector.store.settings'].sudo().create({
            'store_id': store.id,
            'inventory_domain_enabled': True,
            'setup_wizard_step_key': resume,
        })
        for gid, name in cached:
            self.env['shopify.connector.location'].sudo().create({
                'store_id': store.id,
                'shopify_location_gid': gid,
                'name': name,
                'shopify_location_active': True,
            })
        if mapped_gid:
            warehouse = self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            )
            location = self.env['stock.location'].sudo().create({
                'name': 'S1 Tour Odoo Location',
                'usage': 'internal',
                'location_id': warehouse.view_location_id.id,
            })
            # A second internal location that is deliberately left UNMAPPED, so
            # an eligible target provably exists on ANY database -- including a
            # clean install with no demo data, where the only other internal
            # locations belong to the warehouse itself. Without it the tour's
            # "choose an Odoo location" step depended on whichever location the
            # database happened to offer first, and on a clean install that was
            # the one already mapped above: `UNIQUE(store_id, odoo_location_id)`
            # refused the create, and the substring assertion in the tour passed
            # anyway. Determinism here, exactness in the tour, and the database
            # assertion below are the three halves of that one defect.
            self.env['stock.location'].sudo().create({
                'name': 'S1 Tour Spare Odoo Location',
                'usage': 'internal',
                'location_id': warehouse.view_location_id.id,
            })
            self.env['shopify.connector.location.mapping'].sudo().create({
                'store_id': store.id,
                'shopify_gid': mapped_gid,
                'odoo_location_id': location.id,
                'match_key': 'manual',
                'shopify_location_name_snapshot': dict(cached)[mapped_gid],
            })
        return store

    def test_the_location_step_shows_every_cached_location_and_maps_one(self):
        if 'shopify.connector.location.mapping' not in self.env:
            self.skipTest('shopify_connector_inventory is not installed')
        self._admin('s1_location_admin')
        store = self._seed_inventory_store(
            self.LOCATION_SHOP_DOMAIN,
            cached=[
                ('gid://shopify/Location/TOURA', 'Tour Warehouse A'),
                ('gid://shopify/Location/TOURB', 'Tour Warehouse B'),
                ('gid://shopify/Location/TOURC', 'Tour Warehouse C'),
            ],
            mapped_gid='gid://shopify/Location/TOURA',
        )
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_location_tour',
            login='s1_location_admin',
        )
        # The DATABASE consequence, not merely the screen: the browser
        # traversal created a second mapping through the sanctioned service.
        mappings = self.env['shopify.connector.location.mapping'].sudo().search(
            [('store_id', '=', store.id)],
        )
        self.assertEqual(len(mappings), 2)
        self.assertIn(
            'gid://shopify/Location/TOURB', mappings.mapped('shopify_gid'),
        )
        created = mappings.filtered(
            lambda m: m.shopify_gid == 'gid://shopify/Location/TOURB'
        )
        self.assertEqual(
            created.shopify_location_name_snapshot, 'Tour Warehouse B',
            'the name snapshot must come from the validated cache row',
        )
        self.assertEqual(created.match_key, 'manual')
        # The mapping must point at a DIFFERENT Odoo location than the one
        # already mapped. This is the assertion the previous version could not
        # make: the tour chose the first offered option, which on a clean
        # install is the location Warehouse A already occupies, and
        # `UNIQUE(store_id, odoo_location_id)` then refused the create.
        pre_existing = mappings.filtered(
            lambda m: m.shopify_gid == 'gid://shopify/Location/TOURA'
        )
        self.assertTrue(pre_existing.odoo_location_id)
        self.assertNotEqual(
            created.odoo_location_id, pre_existing.odoo_location_id,
            'the browser must have chosen an ELIGIBLE Odoo location, not the '
            'one another Shopify location is already mapped to',
        )
        self.assertEqual(created.odoo_location_id.usage, 'internal')

    def test_a_blocking_readiness_row_deep_links_by_step_key(self):
        if 'shopify.connector.location.mapping' not in self.env:
            self.skipTest('shopify_connector_inventory is not installed')
        self._admin('s1_readiness_admin')
        self._make_readiness_passable()
        store = self._seed_inventory_store(
            self.READINESS_SHOP_DOMAIN,
            cached=[('gid://shopify/Location/RDY', 'Readiness Warehouse')],
            resume='final_readiness',
        )
        # Inventory is on and nothing is mapped, so `mapped_location` is a
        # genuine essential failure -- produced, not simulated.
        self.env['shopify.connector.readiness.check'].run_for_store(store)
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_readiness_tour',
            login='s1_readiness_admin',
        )

    # ------------------------------------------------------------------
    # C4 / A2: exact location-refresh follow-through in a real browser
    # ------------------------------------------------------------------

    def _seed_refresh_store(self, domain):
        store = self._seed_inventory_store(domain, cached=[])
        self.env[
            'shopify.connector.store.credential'
        ].action_set_token(store, REFRESH_DUMMY_TOKEN)
        scopes = self.env[
            'shopify.connector.readiness.check'
        ].REQUIRED_MVP_SCOPES
        store.sudo().write({
            'credential_last_verified_at': fields.Datetime.now(),
            'last_test_connection_result': 'pass',
            'granted_scopes': json.dumps(sorted(set(scopes) | {
                'read_locations', 'write_inventory',
            })),
        })
        return store

    def test_location_refresh_terminal_success_reloads_in_the_browser(self):
        """A terminal refresh and its cache are visible across UI sessions."""
        if 'shopify.connector.location.mapping' not in self.env:
            self.skipTest('shopify_connector_inventory is not installed')
        user = self._admin('s1_refresh_admin')
        store = self._seed_refresh_store(REFRESH_SHOP_DOMAIN)
        job = self.env[
            'shopify.connector.setup.wizard'
        ].with_user(user)._setup_refresh_locations(store)
        job.sudo().write({
            'state': 'running', 'started_at': fields.Datetime.now(),
        })
        self.env['shopify.connector.location'].sudo().create({
            'store_id': store.id,
            'shopify_location_gid': 'gid://shopify/Location/REALTOUR',
            'name': 'Dispatcher Tour Warehouse',
            'shopify_location_active': True,
            'last_synced_at': fields.Datetime.now(),
        })
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.env['shopify.connector.readiness.check'].run_for_store(store)
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_location_refresh_dispatch_tour',
            login='s1_refresh_admin',
        )

        jobs = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'inventory_location_sync'),
        ])
        self.assertEqual(
            len(jobs), 1,
            'duplicate browser confirmation admitted a second refresh run',
        )
        self.assertEqual(jobs.state, 'succeeded')
        self.assertEqual(
            jobs.expected_connection_generation,
            store.connection_generation,
        )
        cached = self.env['shopify.connector.location'].sudo().search([
            ('store_id', '=', store.id),
        ])
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached.name, 'Dispatcher Tour Warehouse')
        readiness = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_readiness_check'),
        ])
        self.assertTrue(readiness, 'terminal success did not recompute readiness')
        settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().search([('store_id', '=', store.id)], limit=1)
        self.assertFalse(settings.setup_readiness_stale_since)
        self.assertEqual(settings.setup_wizard_step_key, 'location_mapping')

    def test_location_refresh_failure_shows_reason_and_retries_same_run(self):
        """A recorded failure preserves identity and offers browser Retry."""
        if 'shopify.connector.location.mapping' not in self.env:
            self.skipTest('shopify_connector_inventory is not installed')
        user = self._admin('s1_refresh_failure_admin')
        store = self._seed_refresh_store(REFRESH_FAILURE_SHOP_DOMAIN)
        job = self.env[
            'shopify.connector.setup.wizard'
        ].with_user(user)._setup_refresh_locations(store)
        job.sudo().write({
            'state': 'running', 'started_at': fields.Datetime.now(),
        })
        job.sudo()._transition_failed_retryable(
            error_class='odoo_validation_configuration',
            message='The recorded location refresh reason is actionable.',
        )
        self.env.flush_all()
        self.start_tour(
            '/odoo', 'shopify_connector_s1_location_refresh_failure_tour',
            login='s1_refresh_failure_admin',
        )

        jobs = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'inventory_location_sync'),
        ])
        self.assertEqual(len(jobs), 1)
        self.assertEqual(
            jobs.state, 'queued',
            'the browser Retry must requeue the same failed run',
        )
        self.assertEqual(
            jobs.error_class, 'odoo_validation_configuration',
        )
