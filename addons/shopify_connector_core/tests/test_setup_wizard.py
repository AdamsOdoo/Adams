"""S1: the 11-step guided setup wizard, server side.

What was missing
----------------
S1 is an accepted MVP screen (premium UX master specification §3, "S1 — Setup
wizard"; DEC-012 §1) and it was recorded as not implemented. There was no
guided setup anywhere in the connector: `shopify.connector.store` carries
`create="false"` on both its list and its form, so there was no route to create
a store at all outside a data import or a `sudo()` call, and every setup
decision -- credential, scopes, directions, source of truth, notifications,
first-push scheduling -- had to be found on separate screens in an order
nobody stated.

What these tests hold
---------------------
The accepted 11 steps exist in the accepted order; the wizard is Administrator
only and refuses everyone else on the SERVER; company isolation holds across
every entry point including a foreign id supplied directly; progress is durable
and resumes where it left off; Back loses nothing; the credential is
write-only and never comes back; no source-of-truth choice is ever pre-selected
into consent; notifications are off by default and take an explicit
consequence-stating confirmation; the first-push guard is scheduled but never
bypassed; and activation starts no synchronisation and writes nothing to
Shopify.

No Shopify request is made anywhere in this file. Step 5's probe is driven
through the module's existing `_send` transport seam with a stand-in, exactly
as the rest of the suite does, so the real client, the real admission gate and
the real response taxonomy all run with only the socket absent.
"""

import json
from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from .test_api_client import FakeResponse, _success_body

from ..models.shopify_connector_setup_wizard import (
    SETUP_STEP_COUNT,
    SETUP_STEPS,
)

DUMMY_TOKEN = 'shpat_SETUPWIZARDDUMMY000000000000000'
SHOP_DOMAIN = 'setup-wizard-test.myshopify.com'


@tagged('post_install', '-at_install')
class SetupWizardCase(TransactionCase):
    """Two companies and three roles, because both axes are load-bearing."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Setup = cls.env['shopify.connector.setup.wizard']
        cls.Store = cls.env['shopify.connector.store']
        cls.Settings = cls.env['shopify.connector.store.settings']
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].sudo().create({
            'name': 'S1 company B',
        })
        cls.admin_a = cls._user('s1_admin_a', cls.company_a, 'admin')
        cls.admin_b = cls._user('s1_admin_b', cls.company_b, 'admin')
        cls.user_a = cls._user('s1_user_a', cls.company_a, 'user')
        cls.plain_a = cls._user('s1_plain_a', cls.company_a, None)

    @classmethod
    def _user(cls, login, company, role):
        groups = ['base.group_user']
        if role:
            groups.append(
                'shopify_connector_core.group_shopify_connector_%s' % role
            )
        user = new_test_user(
            cls.env, login=login, password=login, groups=','.join(groups),
        )
        user.sudo().write({
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
        })
        return user

    def setUp(self):
        super().setUp()
        # `_admit_lifecycle` opens its credential snapshot on an independent
        # `registry.cursor()` side transaction and commits it before the
        # network call. Registry test mode makes that a TestCursor sharing the
        # single test connection, so the uncommitted fixtures and the
        # committed admission are visible cross-cursor -- the sanctioned
        # CORE-R2 mechanism the existing lifecycle tests use. Without it the
        # probe cannot see the store it was called for and records nothing.
        self.env.flush_all()
        self.registry_enter_test_mode()

    # ------------------------------------------------------------------
    # Fixtures
    # ------------------------------------------------------------------

    def _as(self, user):
        return self.Setup.with_user(user).with_context(
            allowed_company_ids=user.company_ids.ids,
        )

    def _assert_refused(self, call):
        """Assert a call is refused, without caring which refusal it is.

        Written by hand rather than with `assertRaises((AccessError,
        UserError))`: Odoo's `TransactionCase.assertRaises` override inspects
        its argument with `issubclass`, which a tuple is not, so the tuple form
        raises `TypeError` instead of asserting anything. A refusal is a
        refusal here -- what matters is that nothing happened, not whether the
        record rule or the explicit company check got there first.
        """
        try:
            call()
        except (AccessError, UserError):
            return True
        raise AssertionError('the call was not refused')

    def _make_store(self, user=None, name='S1 Store', domain=SHOP_DOMAIN):
        user = user or self.admin_a
        state = self._as(user).save_store_identity(name, domain)
        return self.Store.browse(state['store']['id'])

    def _settings(self, store):
        return self.Settings.sudo().search(
            [('store_id', '=', store.id)], limit=1,
        )

    def _make_readiness_passable(self):
        """Satisfy the environment-owned essential checks.

        `web.base.url` is an essential readiness check and a test server's
        default is plain HTTP, so an activation test that did not set it would
        be blocked by the ENVIRONMENT rather than by anything the wizard did --
        and could never observe the success path at all.
        """
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'https://s1-test.example.test',
        )

    def _transport(self, ok=True):
        """Stand in for the ONE transport method, nothing above it.

        Reuses the api-client suite's own success body and response
        stand-in, so the real `_normalize_response` taxonomy, the API-version
        header gate and the shop-identity comparison all run exactly as they
        do in production -- only the socket is absent.
        """
        Client = type(self.env['shopify.connector.api.client'])
        if ok:
            # The granted-scope set is the connector's OWN declaration rather
            # than a hand-written list: `required_scopes` is an essential
            # readiness check, so a fixture granting fewer scopes than the
            # connector requires would block activation for a reason that has
            # nothing to do with the wizard.
            response = FakeResponse(200, json_body={
                'data': {
                    'shop': {
                        'id': 'gid://shopify/Shop/1',
                        'name': 'S1 Test Shop',
                        'myshopifyDomain': SHOP_DOMAIN,
                    },
                    'currentAppInstallation': {
                        'accessScopes': [
                            {'handle': scope}
                            for scope in self.env[
                                'shopify.connector.readiness.check'
                            ].REQUIRED_MVP_SCOPES
                        ],
                    },
                },
            })
        else:
            response = FakeResponse(401, json_body={
                'errors': [{'message': 'Invalid API key or access token'}],
            })

        def responder(_self, _store, request, token=None,
                      mutation_context=None):
            return response

        return patch.object(Client, '_send', responder)

    def _ready_store(self, user=None):
        """A store that has passed test connection and readiness.

        Built through the wizard's own steps, so the state under test is one
        the production path can actually produce.
        """
        user = user or self.admin_a
        store = self._make_store(user=user)
        self._as(user).save_credential(store.id, DUMMY_TOKEN)
        with self._transport(ok=True):
            self._as(user).run_test_connection(store.id)
        store.invalidate_recordset()
        return store


@tagged('post_install', '-at_install')
class TestSetupWizardShape(SetupWizardCase):

    def test_the_step_order_is_the_accepted_one(self):
        """The accepted 11 steps, in the accepted order (DEC-012 §1).

        Asserted against the literal list rather than against a count, because
        a reordering is exactly the kind of change that keeps the count and
        breaks the flow -- credentials before store identity, or activation
        before readiness.
        """
        self.assertEqual(SETUP_STEP_COUNT, 11)
        self.assertEqual(
            [key for key, _label in SETUP_STEPS],
            [
                'welcome', 'identity', 'credential', 'scopes',
                'test_connection', 'readiness', 'directions',
                'source_of_truth', 'notification', 'first_push', 'review',
            ],
        )

    def test_the_state_payload_names_every_step_in_order(self):
        state = self._as(self.admin_a).get_setup_state()
        self.assertEqual(state['step_count'], 11)
        self.assertEqual(
            [step['index'] for step in state['steps']], list(range(1, 12)),
        )
        self.assertEqual(state['steps'][0]['key'], 'welcome')
        self.assertEqual(state['steps'][10]['key'], 'review')

    def test_scopes_are_derived_from_the_governed_declaration(self):
        """Not a hand-written list that can go stale on a setup screen."""
        store = self._make_store()
        state = self._as(self.admin_a).get_setup_state(store.id)
        declared = set(
            self.env['shopify.connector.readiness.check'].REQUIRED_MVP_SCOPES
        )
        self.assertEqual(
            {entry['scope'] for entry in state['scopes']}, declared,
        )
        for entry in state['scopes']:
            self.assertTrue(
                entry['reason'],
                'every scope must be explained in business language',
            )

    def test_only_domains_this_install_carries_are_offered(self):
        store = self._make_store()
        state = self._as(self.admin_a).get_setup_state(store.id)
        for domain in state['domains']:
            self.assertIn(domain['field'], self.Settings._fields)
            self.assertTrue(domain['direction'])
            self.assertTrue(domain['happens'])

    def test_no_source_of_truth_choice_is_pre_selected(self):
        """Requirement: a backend default must never become consent."""
        store = self._make_store()
        self._as(self.admin_a).save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative',
        )
        state = self._as(self.admin_a).get_setup_state(store.id)
        # The payload offers the choices and reports the stored answer in the
        # summary -- it never marks one as selected, which is what would let a
        # client render it pre-ticked.
        for choice in state['matching_choices'] + state['price_choices']:
            self.assertNotIn('selected', choice)
            self.assertTrue(choice['consequence'])


@tagged('post_install', '-at_install')
class TestSetupWizardAuthorization(SetupWizardCase):

    def test_a_connector_user_is_refused_on_every_entry_point(self):
        """Server-side, and on the READ too: refusing only the writes would
        leak a store's whole configuration to any connector user."""
        store = self._make_store()
        setup = self._as(self.user_a)
        for call in (
            lambda: setup.get_setup_state(store.id),
            lambda: setup.get_setup_state(),
            lambda: setup.save_store_identity('x', 'y.myshopify.com'),
            lambda: setup.save_credential(store.id, DUMMY_TOKEN),
            lambda: setup.acknowledge_scopes(store.id),
            lambda: setup.run_test_connection(store.id),
            lambda: setup.run_readiness(store.id),
            lambda: setup.save_directions(store.id, ['sale']),
            lambda: setup.save_source_of_truth(
                store.id, 'odoo_source', 'odoo_authoritative'),
            lambda: setup.save_notification(store.id, True, True),
            lambda: setup.save_first_push_schedule(store.id, True),
            lambda: setup.activate(store.id),
            lambda: setup.save_and_exit(store.id, 3),
            lambda: setup.restart_setup(store.id),
            lambda: setup.action_open_setup_wizard(store.id),
        ):
            with self.subTest(call=call):
                with self.assertRaises(AccessError):
                    call()

    def test_a_plain_internal_user_is_refused(self):
        store = self._make_store()
        with self.assertRaises(AccessError):
            self._as(self.plain_a).get_setup_state(store.id)

    def test_a_wrong_company_administrator_is_refused(self):
        """The company axis with the role axis held constant."""
        store = self._make_store()
        setup = self._as(self.admin_b)
        for call in (
            lambda: setup.get_setup_state(store.id),
            lambda: setup.save_credential(store.id, DUMMY_TOKEN),
            lambda: setup.run_readiness(store.id),
            lambda: setup.save_directions(store.id, ['sale']),
            lambda: setup.activate(store.id),
            lambda: setup.restart_setup(store.id),
        ):
            with self.subTest(call=call):
                self._assert_refused(call)

    def test_a_foreign_store_id_supplied_directly_is_refused(self):
        """The RPC shape: an id typed into a call, not a record navigated to."""
        store = self._make_store()
        self._assert_refused(lambda: self._as(self.admin_b).save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative',
        ))
        settings = self._settings(store)
        self.assertFalse(settings.price_source_of_truth)

    def test_the_store_list_offered_is_company_filtered(self):
        """A foreign administrator is not even told the store exists."""
        self._make_store()
        state = self._as(self.admin_b).get_setup_state()
        self.assertEqual(state['stores'], [])
        self.assertFalse(state['store']['id'])

    def test_a_second_company_gets_its_own_store(self):
        """Positive control: without this, the refusals above could pass
        because the wizard is broken for everyone."""
        self._make_store()
        other = self._as(self.admin_b).save_store_identity(
            'B store', 'b-store.myshopify.com',
        )
        self.assertTrue(other['store']['id'])
        store_b = self.Store.browse(other['store']['id'])
        self.assertEqual(store_b.company_id, self.company_b)

    def test_the_store_is_created_in_the_callers_own_company(self):
        store = self._make_store()
        self.assertEqual(store.company_id, self.company_a)
        self.assertEqual(self._settings(store).company_id, self.company_a)


@tagged('post_install', '-at_install')
class TestSetupWizardSteps(SetupWizardCase):

    # --- step 2 --------------------------------------------------------

    def test_a_malformed_shop_domain_is_refused(self):
        for bad in ('', 'acme', 'acme.example.com', 'https://acme.myshopify.com',
                    'sub.acme.myshopify.com', 'acme .myshopify.com',
                    '-acme.myshopify.com', 'ACME!.myshopify.com'):
            with self.subTest(domain=bad):
                with self.assertRaises(UserError):
                    self._as(self.admin_a).save_store_identity('Acme', bad)

    def test_a_missing_name_is_refused(self):
        with self.assertRaises(UserError):
            self._as(self.admin_a).save_store_identity('  ', SHOP_DOMAIN)

    def test_a_duplicate_shop_domain_is_refused(self):
        self._make_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).save_store_identity('Again', SHOP_DOMAIN)

    def test_identity_does_not_assert_what_readiness_confirms(self):
        """Shape only. The store-identity check confirms it against Shopify."""
        store = self._make_store()
        self.assertEqual(store.state, 'setup_incomplete')
        self.assertFalse(store.last_readiness_result)

    # --- step 3 --------------------------------------------------------

    def test_the_credential_is_written_and_never_returned(self):
        store = self._make_store()
        state = self._as(self.admin_a).save_credential(store.id, DUMMY_TOKEN)
        self.assertTrue(state['store']['credential_present'])
        self.assertNotIn(DUMMY_TOKEN, json.dumps(state))
        # And no fragment of it either -- a prefix is still a leak.
        self.assertNotIn(DUMMY_TOKEN[:12], json.dumps(state))

    def test_no_setup_payload_ever_carries_the_credential(self):
        """Every read shape, not only the one that wrote it."""
        store = self._ready_store()
        setup = self._as(self.admin_a)
        for payload in (
            setup.get_setup_state(store.id),
            setup.acknowledge_scopes(store.id),
            setup.save_directions(store.id, ['sale']),
            setup.save_notification(store.id, False),
        ):
            serialised = json.dumps(payload)
            self.assertNotIn(DUMMY_TOKEN, serialised)
            self.assertNotIn(DUMMY_TOKEN[:12], serialised)
            self.assertNotIn('access_token', serialised)

    def test_an_empty_credential_is_refused(self):
        store = self._make_store()
        for bad in ('', '   ', None, 42):
            with self.subTest(token=bad):
                with self.assertRaises(UserError):
                    self._as(self.admin_a).save_credential(store.id, bad)

    def test_replacing_a_credential_invalidates_its_verification(self):
        store = self._ready_store()
        self.assertTrue(store.credential_last_verified_at)
        self._as(self.admin_a).save_credential(store.id, DUMMY_TOKEN + 'X')
        store.invalidate_recordset()
        self.assertFalse(
            store.credential_last_verified_at,
            'a new token must not inherit the old token\'s verification',
        )

    # --- step 5 --------------------------------------------------------

    def test_test_connection_requires_a_credential_first(self):
        store = self._make_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).run_test_connection(store.id)

    def test_a_passing_test_connection_advances_the_resume_point(self):
        store = self._ready_store()
        self.assertEqual(store.last_test_connection_result, 'pass')
        self.assertGreaterEqual(self._settings(store).setup_wizard_step, 5)

    def test_a_failing_test_connection_does_not_advance_or_lose_the_token(self):
        """A refusal must not read as a pass, and must not discard the
        credential the operator has just entered."""
        store = self._make_store()
        self._as(self.admin_a).save_credential(store.id, DUMMY_TOKEN)
        before = self._settings(store).setup_wizard_step
        with self._transport(ok=False):
            state = self._as(self.admin_a).run_test_connection(store.id)
        store.invalidate_recordset()
        self.assertNotEqual(state['store']['test_connection_result'], 'pass')
        self.assertEqual(self._settings(store).setup_wizard_step, before)
        self.assertTrue(
            store.credential_present,
            'a failed test must not corrupt an already stored credential',
        )

    # --- step 6 --------------------------------------------------------

    def test_readiness_reports_every_check_independently(self):
        store = self._ready_store()
        state = self._as(self.admin_a).run_readiness(store.id)
        readiness = state['readiness']
        self.assertTrue(readiness['ran'])
        self.assertTrue(readiness['checks'])
        for check in readiness['checks']:
            self.assertIn(check['tier'], ('essential', 'warning'))
            self.assertTrue(check['label'])
            self.assertTrue(check['owner'])
            # Text accompanies every status: the tone is decoration, the
            # tier and result are the meaning.
            self.assertIn(check['tone'], ('success', 'warning', 'danger'))

    def test_a_warning_never_becomes_a_blocking_failure(self):
        store = self._ready_store()
        state = self._as(self.admin_a).run_readiness(store.id)
        for check in state['readiness']['blocking']:
            self.assertEqual(check['tier'], 'essential')

    # --- step 7 --------------------------------------------------------

    def test_enabling_nothing_is_a_valid_connect_only_setup(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, [])
        settings = self._settings(store)
        self.assertFalse(settings.sale_domain_enabled)
        self.assertFalse(settings.product_domain_enabled)

    def test_an_unknown_domain_key_is_refused(self):
        store = self._ready_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).save_directions(
                store.id, ['sale', 'not_a_domain'],
            )
        self.assertFalse(self._settings(store).sale_domain_enabled)

    def test_directions_persist_through_the_owning_settings_seam(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(
            store.id, ['sale', 'inventory'],
        )
        settings = self._settings(store)
        self.assertTrue(settings.sale_domain_enabled)
        self.assertTrue(settings.inventory_domain_enabled)
        self.assertFalse(settings.product_domain_enabled)

    # --- step 8 --------------------------------------------------------

    def test_both_source_of_truth_choices_are_required(self):
        store = self._ready_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).save_source_of_truth(
                store.id, False, 'odoo_authoritative')
        with self.assertRaises(UserError):
            self._as(self.admin_a).save_source_of_truth(
                store.id, 'odoo_source', False)
        with self.assertRaises(UserError):
            self._as(self.admin_a).save_source_of_truth(
                store.id, 'made_up', 'odoo_authoritative')
        settings = self._settings(store)
        self.assertFalse(settings.product_first_sync_source)
        self.assertFalse(settings.price_source_of_truth)

    def test_source_of_truth_persists_where_the_export_reads_it(self):
        store = self._ready_store()
        self._as(self.admin_a).save_source_of_truth(
            store.id, 'both_match_first', 'shopify_authoritative',
        )
        settings = self._settings(store)
        self.assertEqual(settings.product_first_sync_source, 'both_match_first')
        self.assertEqual(
            settings.price_source_of_truth, 'shopify_authoritative')

    # --- step 9 --------------------------------------------------------

    def test_notifications_are_off_by_default(self):
        store = self._ready_store()
        self.assertFalse(self._settings(store).notification_default_enabled)

    def test_opting_in_requires_the_consequence_confirmation(self):
        store = self._ready_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).save_notification(store.id, True)
        self.assertFalse(self._settings(store).notification_default_enabled)

    def test_a_confirmed_opt_in_sets_both_halves_of_the_fail_closed_pair(self):
        """The fulfillment domain refuses to notify unless BOTH are true, so
        setting one would leave a store that looks opted in and is not."""
        store = self._ready_store()
        self._as(self.admin_a).save_notification(store.id, True, True)
        settings = self._settings(store)
        self.assertTrue(settings.notification_default_enabled)
        if 'fulfillment_notification_confirmed' in settings._fields:
            self.assertTrue(settings.fulfillment_notification_confirmed)
            self.assertTrue(settings._fulfillment_notification_allowed())

    def test_advancing_the_step_sends_no_notification_and_queues_nothing(self):
        store = self._ready_store()
        before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', store.id),
        ])
        self._as(self.admin_a).save_notification(store.id, True, True)
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', store.id),
            ]),
            before,
            'the notification step must admit no job of any kind',
        )

    # --- step 10 -------------------------------------------------------

    def test_first_push_scheduling_never_bypasses_the_guard(self):
        """Scheduling flips a scan flag. It does not preview, confirm, admit a
        push job or write a quantity to Shopify."""
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['inventory'])
        before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', store.id),
        ])
        self._as(self.admin_a).save_first_push_schedule(store.id, True)
        settings = self._settings(store)
        if 'inventory_scheduled_sync_enabled' in settings._fields:
            self.assertTrue(settings.inventory_scheduled_sync_enabled)
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', store.id),
            ]),
            before,
            'scheduling must admit no job',
        )

    def test_first_push_passes_through_safely_when_inventory_is_off(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, [])
        state = self._as(self.admin_a).save_first_push_schedule(store.id, True)
        settings = self._settings(store)
        if 'inventory_scheduled_sync_enabled' in settings._fields:
            self.assertFalse(
                settings.inventory_scheduled_sync_enabled,
                'a disabled domain must not be scheduled behind the '
                'operator\'s back',
            )
        self.assertIn('not enabled', state['summary']['first_push'])

    def test_scheduling_is_never_described_as_a_completed_push(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['inventory'])
        state = self._as(self.admin_a).save_first_push_schedule(store.id, True)
        summary = state['summary']['first_push']
        self.assertIn('waits for a preview', summary)
        self.assertNotIn('pushed', summary)


@tagged('post_install', '-at_install')
class TestSetupWizardProgress(SetupWizardCase):

    def test_progress_is_durable_and_resumes_where_it_stopped(self):
        store = self._ready_store()
        self._as(self.admin_a).save_and_exit(store.id, 5)
        state = self._as(self.admin_a).get_setup_state(store.id)
        self.assertGreaterEqual(state['resume_step'], 5)

    def test_back_does_not_lose_a_saved_choice(self):
        """Back is navigation. Every saved value is already on its owning
        record, so paging back and re-reading returns it unchanged."""
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        self._as(self.admin_a).save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative')
        # Simulate paging back to step 7 and re-reading.
        self._as(self.admin_a).save_and_exit(store.id, 7)
        state = self._as(self.admin_a).get_setup_state(store.id)
        enabled = {d['key'] for d in state['domains'] if d['enabled']}
        self.assertEqual(enabled, {'sale'})
        self.assertEqual(state['summary']['price'], 'Odoo is the price authority')

    def test_the_resume_point_never_rewinds(self):
        """Re-reading an earlier step must not discard later progress."""
        store = self._ready_store()
        self._as(self.admin_a).save_and_exit(store.id, 8)
        self._as(self.admin_a).save_and_exit(store.id, 3)
        state = self._as(self.admin_a).get_setup_state(store.id)
        self.assertEqual(state['resume_step'], 8)

    def test_an_out_of_range_step_is_refused(self):
        store = self._ready_store()
        for bad in (0, -1, 12, 'three', None):
            with self.subTest(step=bad):
                with self.assertRaises(UserError):
                    self._as(self.admin_a).save_and_exit(store.id, bad)

    def test_browser_state_is_not_the_source_of_truth(self):
        """The resume point is a column, readable by a second administrator on
        a different machine -- not something in one browser's storage."""
        store = self._ready_store()
        self._as(self.admin_a).save_and_exit(store.id, 6)
        self.assertEqual(self._settings(store).setup_wizard_step, 6)

    def test_a_stale_or_foreign_resume_identifier_fails_closed(self):
        store = self._ready_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).get_setup_state(store.id + 10 ** 6)
        self._assert_refused(
            lambda: self._as(self.admin_b).get_setup_state(store.id))


@tagged('post_install', '-at_install')
class TestSetupWizardActivation(SetupWizardCase):

    def _complete_through_readiness(self):
        """Walk steps 2-10 the way an operator does, with a passable
        environment, so the success path is genuinely observable."""
        self._make_readiness_passable()
        store = self._ready_store()
        setup = self._as(self.admin_a)
        setup.run_readiness(store.id)
        # At least one sync domain, because `domain_flag_enablement` is an
        # essential check and a connect-only store legitimately fails it.
        setup.save_directions(store.id, ['sale'])
        setup.save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative')
        setup.save_notification(store.id, False)
        setup.save_first_push_schedule(store.id, False)
        store.invalidate_recordset()
        return store

    def test_activation_is_refused_before_readiness_has_run(self):
        store = self._ready_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).activate(store.id)
        store.invalidate_recordset()
        self.assertNotEqual(store.state, 'connected')

    def test_activation_is_refused_while_an_essential_check_fails(self):
        """A genuine essential failure, produced rather than simulated.

        `web.base.url` without HTTPS is a real essential failure the accepted
        check set already recognises, so this makes the environment produce
        one instead of patching the readiness payload -- a patched payload
        would prove only that the wizard reads its own mock.
        """
        store = self._complete_through_readiness()
        self.env['ir.config_parameter'].sudo().set_param(
            'web.base.url', 'http://not-https.example.test',
        )
        with self.assertRaises(UserError) as caught:
            with self._transport(ok=True):
                self._as(self.admin_a).activate(store.id)
        self.assertIn(
            'public address', str(caught.exception),
            'the refusal must name the checks that are blocking it',
        )
        store.invalidate_recordset()
        self.assertNotEqual(store.state, 'connected')

    def test_activation_starts_no_sync_and_writes_nothing_to_shopify(self):
        """The whole safety claim of step 11, observed rather than asserted.

        The transport seam is replaced with a responder that FAILS the test if
        it is reached, so a request of any kind would be caught -- not only a
        mutation.
        """
        store = self._complete_through_readiness()
        jobs_before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', store.id),
            ('state', 'in', ('queued', 'running')),
        ])
        # Activation re-runs readiness, which reads STORED evidence only and
        # issues no Shopify call. So the transport stand-in is the strict one:
        # any request at all fails the test, not merely a mutation.
        Client = type(self.env['shopify.connector.api.client'])

        def refuse(_self, _store, request, token=None, mutation_context=None):
            raise AssertionError('activation contacted Shopify')

        with patch.object(Client, '_send', refuse):
            self._as(self.admin_a).activate(store.id)
        store.invalidate_recordset()
        self.assertEqual(store.state, 'connected')
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', store.id),
                ('state', 'in', ('queued', 'running')),
            ]),
            jobs_before,
            'activation must enqueue no domain job',
        )
        settings = self._settings(store)
        self.assertTrue(settings.setup_completed_at)
        self.assertEqual(settings.setup_completed_uid, self.admin_a)

    def test_completion_is_audited_with_the_actor(self):
        store = self._complete_through_readiness()
        self._as(self.admin_a).activate(store.id)
        audits = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        logs = self.env['shopify.connector.job.log'].sudo().search([
            ('job_id', 'in', audits.ids),
        ])
        message = ' '.join(logs.mapped('message') or [])
        self.assertIn('Guided setup completed', message)
        self.assertIn('actor_uid=%d' % self.admin_a.id, message)
        self.assertNotIn(DUMMY_TOKEN, message)


@tagged('post_install', '-at_install')
class TestSetupWizardRerun(SetupWizardCase):

    def test_setup_remains_re_runnable_and_undoes_nothing(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        self._as(self.admin_a).save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative')
        self._as(self.admin_a).save_notification(store.id, True, True)

        state = self._as(self.admin_a).restart_setup(store.id)
        self.assertEqual(state['resume_step'], 1)

        settings = self._settings(store)
        self.assertTrue(
            settings.sale_domain_enabled,
            're-running setup must not silently undo an active setting',
        )
        self.assertEqual(settings.product_first_sync_source, 'odoo_source')
        self.assertTrue(settings.notification_default_enabled)
        self.assertEqual(settings.setup_last_rerun_uid, self.admin_a)

    def test_the_store_rerun_button_reaches_the_client_action(self):
        """Entry route 3 of 3, from the store record itself."""
        store = self._ready_store()
        action = store.with_user(self.admin_a).with_context(
            allowed_company_ids=self.admin_a.company_ids.ids,
        ).action_shopify_rerun_setup()
        self.assertEqual(action['type'], 'ir.actions.client')
        self.assertEqual(action['tag'], 'shopify_connector_setup_wizard')
        self.assertEqual(
            action['context']['default_setup_store_id'], store.id,
        )
        self.assertEqual(self._settings(store).setup_wizard_step, 1)

    def test_the_store_rerun_button_refuses_a_connector_user(self):
        store = self._ready_store()
        with self.assertRaises(AccessError):
            store.with_user(self.user_a).action_shopify_rerun_setup()

    def test_the_store_rerun_button_refuses_a_foreign_administrator(self):
        store = self._ready_store()
        self._assert_refused(lambda: store.with_user(self.admin_b).with_context(
            allowed_company_ids=self.company_b.ids,
        ).action_shopify_rerun_setup())

    def test_the_dashboard_offers_setup_only_to_an_administrator(self):
        """Entry route 1 of 3, and the flag that gates it."""
        Dashboard = self.env['shopify.connector.ui.dashboard']
        self.assertTrue(
            Dashboard.with_user(self.admin_a).get_dashboard_data()
            ['setup_available'],
        )
        self.assertFalse(
            Dashboard.with_user(self.user_a).get_dashboard_data()
            ['setup_available'],
        )
