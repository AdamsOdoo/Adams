"""Wave 5 (C): the customer-operable Shopify-location refresh.

WHAT WAS MISSING, AND WHY IT MATTERED

`_enqueue_location_sync` and `_handle_inventory_location_sync` were both
correct, and neither was reachable. There was no control anywhere -- not in
guided setup, not in the Location Mapping workspace -- that admitted a
location-sync job, so the location cache could only ever be populated by the
scheduled cron on an already-activated store. That is a circular gate:
`mapped_location` is an essential readiness check that blocks activation, it
needs a mapping, a mapping needs a Shopify location, and the location list
needed the store to be activated first.

WHAT THESE TESTS HOLD

That the one public route exists, that it goes through the ordinary job queue
and the ordinary dispatcher rather than anywhere near a transport, that it is
gated on role, record visibility, company, domain enablement and verified
credential evidence, that it never admits two refreshes for the same store,
that the four asynchronous states are distinguishable, and that an empty cache
while a refresh is pending or failed is never reported as "Shopify has no
locations".

NO SHOPIFY CONTACT. The transport seam is replaced with a stand-in that FAILS
the test if it is reached, in every test that does not deliberately drive the
dispatcher. The two that do drive it answer `execute` locally, so the real
handler, the real response validation and the real cache upsert all run with
only the socket absent.
"""

from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_inventory.models import (
    shopify_connector_inventory_service as service_module,
)


# Issue #193 / #157 -- Odoo 19 test-phase contract; see
# docs/05-qa/odoo19-test-phase-contract.md.
@tagged('post_install', '-at_install')
class LocationRefreshCase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Service = cls.env['shopify.connector.inventory.service']
        cls.Job = cls.env['shopify.connector.job']
        cls.Setup = cls.env['shopify.connector.setup.wizard']
        cls.company_b = cls.env['res.company'].sudo().create({
            'name': 'Location refresh company B',
        })
        cls.store = cls._make_store(
            'Location Refresh Store', 'location-refresh.myshopify.com',
        )
        cls.user_operator = cls._user('loc_refresh_operator', 'operator')
        cls.user_admin = cls._user('loc_refresh_admin', 'admin')
        cls.user_auditor = cls._user('loc_refresh_auditor', 'auditor')
        cls.admin_b = cls._user(
            'loc_refresh_admin_b', 'admin', company=cls.company_b,
        )

    @classmethod
    def _user(cls, login, role, company=None):
        company = company or cls.env.company
        user = cls.env['res.users'].create({
            'name': login,
            'login': login,
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_%s' % role
                ).id,
            ])],
        })
        user.sudo().write({
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
        })
        return user

    @classmethod
    def _make_store(cls, name, domain, company=None):
        store = cls.env['shopify.connector.store'].create({
            'name': name,
            'shop_domain': domain,
            'api_version': '2026-07',
            'company_id': (company or cls.env.company).id,
        })
        cls.env['shopify.connector.store.settings'].create({
            'store_id': store.id, 'inventory_domain_enabled': True,
        })
        return store

    def setUp(self):
        super().setUp()
        # The credential evidence a read-only setup operation genuinely needs.
        # Written directly rather than through a probe: this suite is about
        # admission, and driving the real probe here would only re-test the
        # api-client suite.
        self.store.sudo().write({
            'credential_present': True,
            'credential_last_verified_at': '2026-07-29 00:00:00',
            'last_test_connection_result': 'pass',
        })

    def _as(self, user):
        return self.Service.with_user(user).with_context(
            allowed_company_ids=user.company_ids.ids,
        )


    def _assert_refused(self, call):
        """Assert a call is refused, without caring which refusal it is.

        Written by hand rather than with `assertRaises((AccessError,
        UserError))`: Odoo's `TransactionCase.assertRaises` override inspects
        its argument with `issubclass`, which a tuple is not, so the tuple
        form raises `TypeError` instead of asserting anything. What matters
        here is that nothing happened, not whether the record rule or the
        explicit company check got there first.
        """
        try:
            call()
        except (AccessError, UserError):
            return True
        raise AssertionError('the call was not refused')

    def _fail_on_contact(self):
        """A transport stand-in that fails the test if anything reaches it."""
        Client = type(self.env['shopify.connector.api.client'])

        def refuse(_self, _store, request, token=None, mutation_context=None):
            raise AssertionError(
                'a location-refresh admission reached the Shopify transport'
            )

        return patch.object(Client, '_send', refuse)


@tagged('post_install', '-at_install')
class TestLocationRefreshAdmission(LocationRefreshCase):

    def test_the_public_action_admits_a_governed_job(self):
        with self._fail_on_contact():
            job = self._as(self.user_operator).action_refresh_shopify_locations(
                self.store.id,
            )
        self.assertEqual(job.job_type, 'inventory_location_sync')
        self.assertEqual(job.state, 'queued')
        self.assertEqual(job.store_id, self.store)

    def test_a_pre_activation_store_can_refresh_at_all(self):
        """The circular gate, closed.

        The store is `setup_incomplete` -- it has to be, because the whole
        point is that mapping happens BEFORE activation. A business job
        source would be refused outright here, which is exactly why this
        route derives its source from the store's state.
        """
        self.assertEqual(self.store.state, 'setup_incomplete')
        with self._fail_on_contact():
            job = self._as(self.user_admin).action_refresh_shopify_locations(
                self.store.id,
            )
        self.assertEqual(job.job_source, 'setup_readiness_check')
        self.assertEqual(job.state, 'queued')

    def test_a_connected_store_uses_the_business_gated_source(self):
        self.store.sudo().write({'state': 'connected'})
        with self._fail_on_contact():
            job = self._as(self.user_operator).action_refresh_shopify_locations(
                self.store.id,
            )
        self.assertEqual(job.job_source, 'manual_sync')

    def test_a_disconnecting_store_is_refused_rather_than_routed_around(self):
        """The exemption must not become a way past the business gate.

        `setup_readiness_check` is store-state-ungated by design, so routing
        every non-connected store down it would let a refresh start while the
        store is disconnecting -- which the business gate exists to prevent.
        Only `setup_incomplete` takes that path.
        """
        for state in ('reconnect_needed', 'disconnecting', 'disconnected'):
            with self.subTest(state=state):
                self.store.sudo().write({'state': state})
                before = self.Job.sudo().search_count([
                    ('store_id', '=', self.store.id),
                ])
                with self._fail_on_contact():
                    with self.assertRaises(UserError):
                        self._as(
                            self.user_operator
                        ).action_refresh_shopify_locations(self.store.id)
                self.assertEqual(
                    self.Job.sudo().search_count([
                        ('store_id', '=', self.store.id),
                    ]),
                    before,
                    'a refused refresh must admit nothing',
                )
        self.store.sudo().write({'state': 'setup_incomplete'})

    def test_the_action_delegates_to_the_sanctioned_admission_service(self):
        """The route, asserted rather than assumed.

        A refresh that built its own job row would bypass the domain gate,
        the idempotency key and the store-state contract all at once. This
        proves the public action reaches `_enqueue_location_sync`, which is
        the one place a location-sync job is created.
        """
        calls = []
        original = type(self.Service)._enqueue_location_sync

        def spy(self_, store, job_source='scheduled_sync'):
            calls.append(job_source)
            return original(self_, store, job_source=job_source)

        with patch.object(
            type(self.Service), '_enqueue_location_sync', spy,
        ):
            with self._fail_on_contact():
                self._as(self.user_operator).action_refresh_shopify_locations(
                    self.store.id,
                )
        self.assertEqual(calls, ['setup_readiness_check'])

    def test_an_unsanctioned_job_source_is_refused(self):
        with self.assertRaises(Exception):
            self._as(self.user_admin)._enqueue_location_sync(
                self.store, job_source='webhook',
            )

    def test_duplicate_refresh_is_coalesced_not_queued_twice(self):
        with self._fail_on_contact():
            first = self._as(
                self.user_operator
            ).action_refresh_shopify_locations(self.store.id)
            second = self._as(
                self.user_operator
            ).action_refresh_shopify_locations(self.store.id)
        self.assertEqual(first.id, second.id)
        self.assertEqual(
            self.Job.sudo().search_count([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'inventory_location_sync'),
            ]),
            1,
            'a second refresh must not admit a second job',
        )

    def test_a_new_refresh_is_admitted_once_the_previous_one_finished(self):
        with self._fail_on_contact():
            first = self._as(
                self.user_operator
            ).action_refresh_shopify_locations(self.store.id)
            first.sudo().write({'state': 'cancelled'})
            second = self._as(
                self.user_operator
            ).action_refresh_shopify_locations(self.store.id)
        self.assertNotEqual(first.id, second.id)

    # --- authorization --------------------------------------------------

    def test_an_auditor_is_refused(self):
        with self._fail_on_contact():
            with self.assertRaises(AccessError):
                self._as(self.user_auditor).action_refresh_shopify_locations(
                    self.store.id,
                )
        self.assertFalse(self.Job.sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'inventory_location_sync'),
        ]))

    def test_a_foreign_company_administrator_is_refused(self):
        with self._fail_on_contact():
            self._assert_refused(
                lambda: self._as(self.admin_b)
                .action_refresh_shopify_locations(self.store.id)
            )

    def test_a_foreign_and_a_nonexistent_id_refuse_identically(self):
        """No enumeration: the two must be indistinguishable to the caller."""
        def refusal_for(candidate):
            try:
                self._as(self.admin_b).action_refresh_shopify_locations(
                    candidate,
                )
            except (AccessError, UserError) as exc:
                return type(exc), str(exc)
            raise AssertionError('%s was not refused' % candidate)

        with self._fail_on_contact():
            foreign = refusal_for(self.store.id)
            missing = refusal_for(self.store.id + 10 ** 6)
        self.assertEqual(foreign, missing)

    def test_inventory_disabled_is_refused(self):
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', self.store.id)], limit=1,
        )
        settings.sudo().write({'inventory_domain_enabled': False})
        try:
            with self._fail_on_contact():
                with self.assertRaises(UserError):
                    self._as(
                        self.user_operator
                    ).action_refresh_shopify_locations(self.store.id)
        finally:
            settings.sudo().write({'inventory_domain_enabled': True})

    def test_missing_credential_evidence_is_refused_before_admission(self):
        cases = (
            {'credential_present': False},
            {'credential_last_verified_at': False},
            {'last_test_connection_result': 'fail'},
        )
        for overrides in cases:
            with self.subTest(overrides=overrides):
                self.store.sudo().write(dict(overrides))
                before = self.Job.sudo().search_count([
                    ('store_id', '=', self.store.id),
                ])
                with self._fail_on_contact():
                    with self.assertRaises(UserError):
                        self._as(
                            self.user_operator
                        ).action_refresh_shopify_locations(self.store.id)
                self.assertEqual(
                    self.Job.sudo().search_count([
                        ('store_id', '=', self.store.id),
                    ]),
                    before,
                )
                self.store.sudo().write({
                    'credential_present': True,
                    'credential_last_verified_at': '2026-07-29 00:00:00',
                    'last_test_connection_result': 'pass',
                })


@tagged('post_install', '-at_install')
class TestLocationRefreshState(LocationRefreshCase):

    def _job(self, state):
        job = self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'inventory_location_sync',
            'state': 'queued',
            'payload_hash': 'refresh-state-%s' % state,
        })
        if state != 'queued':
            if state in ('succeeded', 'failed_final', 'skipped'):
                job.sudo().write({'state': 'running'})
            job.sudo().write({'state': state})
        return job

    def test_the_four_states_are_distinguishable(self):
        expected = {
            'queued': 'waiting',
            'running': 'running',
            'succeeded': 'succeeded',
            'failed_final': 'failed',
        }
        for job_state, presented in expected.items():
            with self.subTest(job_state=job_state):
                job = self._job(job_state)
                state = self.Service.location_refresh_state(self.store)
                self.assertEqual(state['state'], presented)
                self.assertEqual(state['job_id'], job.id)
                job.sudo().write(
                    {'state': 'cancelled'}
                    if job_state in ('queued', 'running') else {}
                )
                if job_state in ('succeeded', 'failed_final'):
                    job.sudo().unlink()

    def test_no_refresh_ever_asked_for_is_its_own_state(self):
        state = self.Service.location_refresh_state(self.store)
        self.assertEqual(state['state'], 'none')
        self.assertFalse(state['job_id'])

    def test_an_empty_cache_while_pending_is_not_reported_as_zero_locations(self):
        """The single most dangerous thing this surface could say.

        With a refresh queued and the cache empty, the setup payload must
        report `waiting` and the readiness projection must report the
        mapped-location check as Waiting -- never a statement that this
        merchant's Shopify store has no locations, and never a green pass.
        """
        self._job('queued')
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', self.store.id)], limit=1,
        )
        payload = self.Setup._setup_location_payload(self.store, settings)
        self.assertTrue(payload['available'])
        self.assertEqual(payload['locations'], [])
        self.assertEqual(payload['refresh']['state'], 'waiting')
        self.assertFalse(payload['has_valid_mapping'])

        check = {
            'code': 'mapped_location', 'tier': 'essential',
            'result': 'not_proven', 'not_applicable': False,
            'reason': 'nothing mapped',
        }
        projected = self.Setup._project_readiness_check(
            check, settings, payload, False,
        )
        self.assertEqual(projected['state'], 'waiting')
        self.assertNotEqual(projected['tone'], 'success')
        self.assertIn('not a report', projected['reason'])

    def test_a_failed_refresh_is_never_presented_as_a_success(self):
        self._job('failed_final')
        settings = self.env['shopify.connector.store.settings'].search(
            [('store_id', '=', self.store.id)], limit=1,
        )
        payload = self.Setup._setup_location_payload(self.store, settings)
        self.assertEqual(payload['refresh']['state'], 'failed')
        check = {
            'code': 'mapped_location', 'tier': 'essential',
            'result': 'not_proven', 'not_applicable': False,
            'reason': 'nothing mapped',
        }
        projected = self.Setup._project_readiness_check(
            check, settings, payload, False,
        )
        # A failed refresh cannot prove the required mapping, so the check is
        # Blocking -- and in no circumstance Passed.
        self.assertEqual(projected['state'], 'blocking')
        self.assertNotEqual(projected['tone'], 'success')


@tagged('post_install', '-at_install')
class TestLocationRefreshDispatch(LocationRefreshCase):
    """The admitted job reaches the production handler through the dispatcher."""

    def test_the_ordinary_dispatcher_routes_the_admitted_job(self):
        handlers = self.env['shopify.connector.job.dispatch']._get_handlers()
        self.assertIn('inventory_location_sync', handlers)
        self.assertEqual(
            handlers['inventory_location_sync'].__name__,
            '_handle_inventory_location_sync',
        )

    def test_the_admitted_job_populates_the_cache_through_the_handler(self):
        """End to end, minus the socket.

        The job is admitted by the real public action and executed by the
        real handler, with only `execute` answered locally. The assertion is
        a DATABASE consequence -- cached rows that were not there before --
        not that a method was called.
        """
        with self._fail_on_contact():
            job = self._as(self.user_operator).action_refresh_shopify_locations(
                self.store.id,
            )
        response = {
            'data': {
                'locations': {
                    'edges': [
                        {'cursor': 'c1', 'node': {
                            'id': 'gid://shopify/Location/RF1',
                            'name': 'Refresh Warehouse One'}},
                        {'cursor': 'c2', 'node': {
                            'id': 'gid://shopify/Location/RF2',
                            'name': 'Refresh Warehouse Two'}},
                    ],
                    'pageInfo': {'hasNextPage': False},
                },
            },
        }
        job.sudo().write({'state': 'running'})
        with patch.object(
            type(self.env['shopify.connector.api.client']), 'execute',
            return_value=response,
        ):
            self.Service._handle_inventory_location_sync(job)
        cached = self.env['shopify.connector.location'].sudo().search([
            ('store_id', '=', self.store.id),
        ])
        self.assertEqual(len(cached), 2)
        self.assertEqual(
            set(cached.mapped('shopify_location_gid')),
            {'gid://shopify/Location/RF1', 'gid://shopify/Location/RF2'},
        )
        job.invalidate_recordset()
        self.assertEqual(job.state, 'succeeded')
        state = self.Service.location_refresh_state(self.store)
        self.assertEqual(state['state'], 'succeeded')

    def test_the_location_sync_job_type_is_domain_gated_at_start(self):
        """Inventory must be enabled for the job to run, whatever admitted it."""
        self.assertEqual(
            self.Job._domain_flag_for_job_type('inventory_location_sync'),
            'inventory_domain_enabled',
        )

    def test_the_location_sync_replay_policy_is_read_safe(self):
        policies = self.env[
            'shopify.connector.job.dispatch'
        ]._get_replay_policies()
        self.assertEqual(
            policies['inventory_location_sync'],
            service_module.REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
        )


@tagged('post_install', '-at_install')
class TestLocationRefreshHasNoTransportShortcut(LocationRefreshCase):
    """No UI surface may hold a Shopify request. Asserted from the sources."""

    def _sources(self, *globs):
        import pathlib
        addons = pathlib.Path(__file__).resolve().parents[2]
        found = []
        for glob in globs:
            for path in sorted(addons.glob(glob)):
                found.append((path, path.read_text()))
        return found

    def test_no_wizard_view_or_setup_surface_calls_the_api_client(self):
        offenders = []
        for path, source in self._sources(
            'shopify_connector_*/wizards/*.py',
            'shopify_connector_core/models/shopify_connector_setup_wizard.py',
            'shopify_connector_inventory/models/'
            'shopify_connector_inventory_setup.py',
            'shopify_connector_*/controllers/*.py',
        ):
            for marker in (
                "shopify.connector.api.client",
                "_send(",
                "requests.post",
                "requests.get",
            ):
                if marker in source:
                    offenders.append('%s: %s' % (path.name, marker))
        self.assertFalse(offenders, (
            'a setup, wizard or controller surface reaches the Shopify '
            'transport directly instead of admitting a governed job: %s'
            % offenders
        ))

    def test_the_owl_client_holds_no_shopify_request(self):
        offenders = []
        for path, source in self._sources(
            'shopify_connector_*/static/src/js/*.js',
            'shopify_connector_*/static/src/xml/*.xml',
        ):
            for marker in ('myshopify.com/admin', 'graphql.json', 'X-Shopify'):
                if marker in source:
                    offenders.append('%s: %s' % (path.name, marker))
        self.assertFalse(offenders, (
            'a browser asset carries a Shopify endpoint or header: %s'
            % offenders
        ))
