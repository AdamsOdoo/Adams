"""S1: the guided setup wizard, driven in a real browser.

The server tests in `test_setup_wizard.py` prove every step's method is correct
and correctly guarded. They cannot prove there is a control that reaches it.

That distinction is the whole reason S1 was recorded as not implemented while
its pieces existed: a credential service, a readiness registry, settings
fields and an activation contract were all present and correct, and there was
no route through them. A browser is the only place "the operator can get from
nothing to an activated store" is a testable claim.

These tours contact no Shopify store. The full traversal's connection probe is
answered at the existing `_send` transport seam. The two C4 refresh journeys
use Odoo's real-request HttpCase mode, committed fixture cursors and an
independent production dispatcher cursor, so browser RPCs and background work
observe the same durable database state without sharing the test transaction.
"""

import json
import queue
import threading
from unittest.mock import patch

from odoo import SUPERUSER_ID, api, fields
from odoo.sql_db import db_connect
from odoo.tests.common import HttpCase, TransactionCase, new_test_user, tagged

from .test_api_client import FakeResponse
from ..models.shopify_connector_api_client import (
    ShopifyClientError,
    ShopifyQuiescedError,
)

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
        refresh_job = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'inventory_location_sync',
            'state': 'queued',
            'payload_hash': 's1-location-tour-%s' % store.id,
            'expected_connection_generation': store.connection_generation,
        })
        refresh_job.sudo().write({'state': 'running'})
        refresh_job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
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



@tagged('post_install', '-at_install', 'shopify_connector_s1')
class TestUiC4LocationRefreshTours(HttpCase):
    """C4 browser proof with real request and dispatcher transactions."""

    registry_test_mode = False
    BOUND_SECONDS = 30
    STATEMENT_TIMEOUT_MS = 20000
    LOCK_TIMEOUT_MS = 10000

    def authenticate(self, user, password, **kwargs):
        """Authenticate from a fresh cursor that sees committed C4 fixtures."""
        auth_cr = self._open_bounded_cursor()
        test_cr, test_env = self.cr, self.env
        try:
            self.cr = auth_cr
            self.env = api.Environment(auth_cr, SUPERUSER_ID, {})
            session = super().authenticate(user, password, **kwargs)
            auth_cr.commit()
            return session
        finally:
            self.cr = test_cr
            self.env = test_env
            # `super()` rebuilds the opener while the auth cursor is current;
            # subsequent HttpCase bookkeeping belongs back on the test cursor.
            self.opener.cr = test_cr
            auth_cr.close()

    def _open_bounded_cursor(self):
        cr = db_connect(self.env.cr.dbname).cursor()
        try:
            cr.execute(
                "SELECT set_config('statement_timeout', %s, true), "
                "set_config('lock_timeout', %s, true)",
                (str(self.STATEMENT_TIMEOUT_MS), str(self.LOCK_TIMEOUT_MS)),
            )
        except BaseException:
            cr.close()
            raise
        return cr

    def _commit_fixture(self, domain, login):
        cr = self._open_bounded_cursor()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            user = new_test_user(
                env, login=login, password=login,
                groups=(
                    'base.group_user,'
                    'shopify_connector_core.group_shopify_connector_admin'
                ),
            )
            user.write({
                'company_id': env.company.id,
                'company_ids': [(6, 0, [env.company.id])],
            })
            store = env['shopify.connector.store'].create({
                'name': 'C4 Real Request Store',
                'shop_domain': domain,
                'company_id': env.company.id,
            })
            settings = env['shopify.connector.store.settings'].create({
                'store_id': store.id,
                'inventory_domain_enabled': True,
                'setup_wizard_step_key': 'location_mapping',
            })
            env[
                'shopify.connector.store.credential'
            ].action_set_token(store, REFRESH_DUMMY_TOKEN)
            scopes = env[
                'shopify.connector.readiness.check'
            ].REQUIRED_MVP_SCOPES
            store.write({
                'credential_last_verified_at': fields.Datetime.now(),
                'last_test_connection_result': 'pass',
                'granted_scopes': json.dumps(sorted(set(scopes) | {
                    'read_locations', 'write_inventory',
                })),
            })
            fixture = {
                'store_id': store.id,
                'user_id': user.id,
                'partner_id': user.partner_id.id,
                'settings_id': settings.id,
                'domain': domain,
                'login': login,
            }
            cr.commit()
            return fixture
        finally:
            cr.close()

    def _cleanup_fixture(self, fixture):
        """Delete committed C4 rows in foreign-key-safe order, then prove zero."""
        cr = self._open_bounded_cursor()
        try:
            store_id = fixture['store_id']
            for table in (
                'shopify_connector_call_lease',
                'shopify_connector_mutation_attempt',
                'shopify_connector_job_log',
                'shopify_connector_location_mapping',
                'shopify_connector_location',
                'shopify_connector_job',
                'shopify_connector_store_access_token',
                'shopify_connector_store_settings',
                'shopify_connector_store_credential',
            ):
                cr.execute(
                    "SELECT to_regclass(%s)", ('public.%s' % table,),
                )
                if cr.fetchone()[0]:
                    cr.execute(
                        'DELETE FROM %s WHERE store_id = %%s' % table,
                        (store_id,),
                    )
            cr.execute(
                'DELETE FROM shopify_connector_store WHERE id = %s',
                (store_id,),
            )
            env = api.Environment(cr, SUPERUSER_ID, {})
            env['res.users'].browse(fixture['user_id']).exists().unlink()
            env['res.partner'].browse(fixture['partner_id']).exists().unlink()
            cr.commit()
        finally:
            cr.close()

        verify = self._open_bounded_cursor()
        try:
            verify.execute(
                'SELECT count(*) FROM shopify_connector_store WHERE id = %s',
                (fixture['store_id'],),
            )
            self.assertEqual(verify.fetchone()[0], 0, 'C4 store residue')
            verify.execute(
                'SELECT count(*) FROM shopify_connector_job WHERE store_id = %s',
                (fixture['store_id'],),
            )
            self.assertEqual(verify.fetchone()[0], 0, 'C4 job residue')
            verify.execute(
                'SELECT count(*) FROM shopify_connector_location '
                'WHERE store_id = %s', (fixture['store_id'],),
            )
            self.assertEqual(verify.fetchone()[0], 0, 'C4 cache residue')
            verify.execute(
                'SELECT count(*) FROM res_users WHERE id = %s',
                (fixture['user_id'],),
            )
            self.assertEqual(verify.fetchone()[0], 0, 'C4 user residue')
        finally:
            verify.rollback()
            verify.close()

    def _patch_process_seam(self, owner, name, replacement):
        original = getattr(owner, name)
        patcher = patch.object(owner, name, replacement)
        patcher.start()

        def restore():
            patcher.stop()
            self.assertIs(
                getattr(owner, name), original,
                'the C4 process seam was not restored',
            )

        self.addCleanup(restore)

    def _install_transport(self, fixture, fail_first):
        Client = type(self.env['shopify.connector.api.client'])
        original_send = Client._send
        transport_calls = []
        lock = threading.Lock()
        warehouse = (
            'Dispatcher Retry Warehouse' if fail_first
            else 'Dispatcher Tour Warehouse'
        )

        def responder(client, store, body, token=None, mutation_context=None):
            if store.shop_domain != fixture['domain']:
                return original_send(
                    client, store, body, token,
                    mutation_context=mutation_context,
                )
            with lock:
                transport_calls.append(store.id)
                attempt = len(transport_calls)
            if fail_first and attempt == 1:
                # A genuine client classification, not a pre-seeded job state.
                return FakeResponse(200, json_body={'data': {}}, headers={})
            return FakeResponse(200, json_body={
                'data': {
                    'locations': {
                        'edges': [{
                            'cursor': 'c4-cursor',
                            'node': {
                                'id': 'gid://shopify/Location/C4REAL',
                                'name': warehouse,
                            },
                        }],
                        'pageInfo': {'hasNextPage': False},
                    },
                },
            })

        self._patch_process_seam(Client, '_send', responder)
        return transport_calls, lock

    def _install_admission_observer(self, fixture, milestones):
        Wizard = type(self.env['shopify.connector.setup.wizard'])
        original_admit = Wizard._setup_refresh_locations
        original_follow = Wizard.follow_location_refresh
        admissions = []
        lock = threading.Lock()

        def observed_admit(wizard, store):
            job = original_admit(wizard, store)
            if store.shop_domain == fixture['domain']:
                with lock:
                    admissions.append(job.id)
            return job

        @api.model
        def observed_follow(wizard, store_id, job_id):
            result = original_follow(wizard, store_id, job_id)
            if store_id == fixture['store_id']:
                with lock:
                    count = len(admissions)
                # This method is a separate browser RPC after refresh_shopify_
                # locations returned. Therefore the admission transaction for
                # `count` is committed before its matching event is released.
                for threshold, event in milestones:
                    if count >= threshold:
                        event.set()
            return result

        self._patch_process_seam(Wizard, '_setup_refresh_locations', observed_admit)
        self._patch_process_seam(Wizard, 'follow_location_refresh', observed_follow)
        return admissions, lock

    def _start_dispatcher(self, fixture, dispatch_events):
        findings = queue.Queue()
        stop = threading.Event()

        def worker():
            threading.current_thread().dbname = self.env.cr.dbname
            try:
                for dispatch_event in dispatch_events:
                    if not dispatch_event.wait(self.BOUND_SECONDS):
                        raise AssertionError('C4 dispatch event timed out')
                    if stop.is_set():
                        return
                    cr = self._open_bounded_cursor()
                    try:
                        env = api.Environment(cr, SUPERUSER_ID, {})
                        other_store_ids = env[
                            'shopify.connector.store'
                        ].search([
                            ('id', '!=', fixture['store_id']),
                        ]).ids
                        handled = env[
                            'shopify.connector.job.dispatch'
                        ]._drain_one(
                            exclude_store_ids=tuple(other_store_ids),
                        )
                        if not handled:
                            raise AssertionError(
                                'the scoped C4 dispatcher claimed no job'
                            )
                    finally:
                        cr.rollback()
                        cr.close()
            except BaseException as exc:
                findings.put((type(exc).__name__, str(exc)))

        thread = threading.Thread(
            target=worker, name='c4-location-dispatcher', daemon=True,
        )
        thread.start()

        def stop_worker():
            stop.set()
            for event in dispatch_events:
                event.set()
            thread.join(self.BOUND_SECONDS)
            self.assertFalse(thread.is_alive(), 'C4 dispatcher worker survived cleanup')

        self.addCleanup(stop_worker)
        return thread, findings

    def _fresh_result(self, fixture):
        cr = self._open_bounded_cursor()
        try:
            env = api.Environment(cr, SUPERUSER_ID, {})
            jobs = env['shopify.connector.job'].search([
                ('store_id', '=', fixture['store_id']),
                ('job_type', '=', 'inventory_location_sync'),
            ])
            locations = env['shopify.connector.location'].search([
                ('store_id', '=', fixture['store_id']),
            ])
            store = env['shopify.connector.store'].browse(fixture['store_id'])
            settings = env[
                'shopify.connector.store.settings'
            ].browse(fixture['settings_id'])
            return {
                'job_ids': jobs.ids,
                'job_state': jobs.state,
                'job_generation': jobs.expected_connection_generation,
                'store_generation': store.connection_generation,
                'location_names': locations.mapped('name'),
                'last_readiness_at': bool(store.last_readiness_at),
                'readiness_stale': bool(settings.setup_readiness_stale_since),
                'resume': settings.setup_wizard_step_key,
            }
        finally:
            cr.rollback()
            cr.close()

    def _assert_worker_clean(self, thread, findings):
        thread.join(self.BOUND_SECONDS)
        self.assertFalse(thread.is_alive(), 'C4 dispatcher did not terminate')
        errors = []
        while not findings.empty():
            errors.append(findings.get_nowait())
        self.assertEqual(errors, [], 'C4 dispatcher findings')

    def test_location_refresh_success_is_followed_and_reloaded(self):
        """Automatic browser admission dispatches, recomputes and reopens."""
        if 'shopify.connector.location.mapping' not in self.env:
            self.skipTest('shopify_connector_inventory is not installed')
        fixture = self._commit_fixture(REFRESH_SHOP_DOMAIN, 's1_refresh_admin')
        self.addCleanup(self._cleanup_fixture, fixture)
        # Odoo's post-install loader holds the registry class lock in this
        # main thread. Real HTTP/worker threads need the same bounded lock
        # decoupling as Odoo's own registry test-mode patch, while retaining
        # mutual exclusion among themselves against the already-built registry.
        self._patch_process_seam(
            type(self.registry), '_lock', threading.RLock(),
        )
        calls, calls_lock = self._install_transport(fixture, fail_first=False)
        dispatch = threading.Event()
        admissions, admissions_lock = self._install_admission_observer(
            fixture, [(1, dispatch)],
        )
        thread, findings = self._start_dispatcher(fixture, [dispatch])

        self.start_tour(
            '/odoo', 'shopify_connector_s1_location_refresh_dispatch_tour',
            login=fixture['login'],
        )
        self._assert_worker_clean(thread, findings)
        with admissions_lock:
            admitted_ids = list(admissions)
        with calls_lock:
            transport_count = len(calls)
        self.assertEqual(
            len(admitted_ids), 1,
            'entering the required step did not admit exactly one automatic run',
        )
        self.assertEqual(transport_count, 1)
        result = self._fresh_result(fixture)
        self.assertEqual(result['job_ids'], [admitted_ids[0]])
        self.assertEqual(result['job_state'], 'succeeded')
        self.assertEqual(result['job_generation'], result['store_generation'])
        self.assertEqual(result['location_names'], ['Dispatcher Tour Warehouse'])
        self.assertTrue(result['last_readiness_at'])
        self.assertFalse(result['readiness_stale'])
        self.assertEqual(result['resume'], 'location_mapping')

    def test_location_refresh_failure_shows_reason_and_retries_same_run(self):
        """A classified dispatched failure retries the same run to success."""
        if 'shopify.connector.location.mapping' not in self.env:
            self.skipTest('shopify_connector_inventory is not installed')
        fixture = self._commit_fixture(
            REFRESH_FAILURE_SHOP_DOMAIN, 's1_refresh_failure_admin',
        )
        self.addCleanup(self._cleanup_fixture, fixture)
        self._patch_process_seam(
            type(self.registry), '_lock', threading.RLock(),
        )
        calls, calls_lock = self._install_transport(fixture, fail_first=True)
        first_dispatch = threading.Event()
        retry_dispatch = threading.Event()
        admissions, admissions_lock = self._install_admission_observer(
            fixture, [(1, first_dispatch), (2, retry_dispatch)],
        )
        thread, findings = self._start_dispatcher(
            fixture, [first_dispatch, retry_dispatch],
        )

        self.start_tour(
            '/odoo', 'shopify_connector_s1_location_refresh_failure_tour',
            login=fixture['login'],
        )
        self._assert_worker_clean(thread, findings)
        with admissions_lock:
            admitted_ids = list(admissions)
        with calls_lock:
            transport_count = len(calls)
        self.assertEqual(
            len(admitted_ids), 2,
            'automatic discovery and the explicit Try again are both required',
        )
        self.assertEqual(
            len(set(admitted_ids)), 1,
            'Try again created an unrelated location-refresh run',
        )
        self.assertEqual(transport_count, 2)
        result = self._fresh_result(fixture)
        self.assertEqual(result['job_ids'], [admitted_ids[0]])
        self.assertEqual(result['job_state'], 'succeeded')
        self.assertEqual(result['location_names'], ['Dispatcher Retry Warehouse'])
        self.assertTrue(result['last_readiness_at'])
        self.assertFalse(result['readiness_stale'])


@tagged('post_install', '-at_install')
class TestSetupBusinessReadPolicy(TransactionCase):
    """The setup exception is exact; ordinary and quiesced reads stay shut."""

    def setUp(self):
        super().setUp()
        self.store = self.env['shopify.connector.store'].create({
            'name': 'Setup Business Read Policy',
            'shop_domain': 'setup-business-read-policy.myshopify.com',
            'state': 'setup_incomplete',
        })
        self.env[
            'shopify.connector.store.credential'
        ].action_set_token(self.store, REFRESH_DUMMY_TOKEN)
        self.env.flush_all()
        self.registry_enter_test_mode()

    def _running_job(self, job_type='inventory_location_sync'):
        return self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': job_type,
            'state': 'running',
            'payload_hash': 'setup-business-read-policy-%s' % job_type,
            'started_at': fields.Datetime.now(),
        })

    @staticmethod
    def _send_ok(client, store, body, token=None):
        return FakeResponse(200, json_body={'data': {'shop': {'id': 'gid'}}})

    def test_setup_location_refresh_business_read_is_admitted(self):
        job = self._running_job()
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', self._send_ok):
            with Client.execute_business_read(
                job, self.store, 'query { shop { id } }', purpose='inventory',
            ) as result:
                self.assertEqual(result['data']['shop']['id'], 'gid')
                self.assertEqual(
                    self.env['shopify.connector.call.lease'].search_count([
                        ('job_id', '=', job.id),
                    ]),
                    1,
                )
        self.assertFalse(self.env['shopify.connector.call.lease'].search([
            ('job_id', '=', job.id),
        ]))

    def test_other_setup_inventory_business_read_remains_blocked(self):
        job = self._running_job('inventory_push_scan')
        with self.assertRaises(ShopifyQuiescedError):
            with self.env[
                'shopify.connector.api.client'
            ].execute_business_read(
                job, self.store, 'query { shop { id } }', purpose='inventory',
            ):
                pass
        self.assertFalse(self.env['shopify.connector.call.lease'].search([
            ('job_id', '=', job.id),
        ]))

    def test_setup_location_read_opens_only_setup_and_reconnect_states(self):
        job = self._running_job()
        self.store.write({'state': 'reconnect_needed'})
        self.env.flush_all()
        Client = self.env['shopify.connector.api.client']
        with patch.object(type(Client), '_send', self._send_ok):
            with Client.execute_business_read(
                job, self.store, 'query { shop { id } }', purpose='inventory',
            ) as result:
                self.assertEqual(result['data']['shop']['id'], 'gid')

        for state in ('disconnecting', 'disconnected'):
            with self.subTest(state=state):
                self.store.write({'state': state})
                self.env.flush_all()
                with self.assertRaises(ShopifyQuiescedError):
                    with self.env[
                        'shopify.connector.api.client'
                    ].execute_business_read(
                        job, self.store, 'query { shop { id } }',
                        purpose='inventory',
                    ):
                        pass
                self.assertFalse(
                    self.env['shopify.connector.call.lease'].search([
                        ('job_id', '=', job.id),
                    ])
                )

    def test_setup_business_token_exchange_purpose_is_setup_only(self):
        Credential = self.env['shopify.connector.store.credential']
        self.assertTrue(Credential._assert_token_exchange_allowed(
            self.store, 'setup_business_read',
        ))
        self.store.write({'state': 'reconnect_needed'})
        self.env.flush_all()
        self.assertTrue(Credential._assert_token_exchange_allowed(
            self.store, 'setup_business_read',
        ))
        for state in ('connected', 'disconnecting', 'disconnected'):
            with self.subTest(state=state):
                self.store.write({'state': state})
                self.env.flush_all()
                with self.assertRaises(ShopifyClientError):
                    Credential._assert_token_exchange_allowed(
                        self.store, 'setup_business_read',
                    )
