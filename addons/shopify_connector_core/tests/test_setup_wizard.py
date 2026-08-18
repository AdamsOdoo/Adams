"""S1: the 12-step guided setup wizard, server side.

What was missing
----------------
S1 is an accepted MVP screen (premium UX master specification §3, "S1 — Setup
wizard"; DEC-012 §1) and it was recorded as not implemented. There was no
guided setup anywhere in the connector: `shopify.connector.store` carries
`create="false"` on both its list and its form, so there was no route to create
a store at all outside a data import or a `sudo()` call, and every setup
decision -- credential, scopes, directions, source of truth, notifications,
first-push scanning -- had to be found on separate screens in an order
nobody stated.

What these tests hold
---------------------
The accepted 12 steps exist in the accepted order, addressed by SEMANTIC KEY
rather than by position; progress recorded before the semantic key existed is
translated deterministically rather than reset; the wizard is Administrator
only and refuses everyone else on the SERVER; company isolation holds across
every entry point including a foreign id supplied directly; progress is durable
and resumes where it left off; Back loses nothing; the credential is
write-only and never comes back; no source-of-truth choice is ever pre-selected
into consent; notifications are off by default and take an explicit
consequence-stating confirmation; the first-push guard is enabled but never
bypassed; and activation promptly triggers only the selected read-side
producers while writing nothing to Shopify.

No Shopify request is made anywhere in this file. Step 5's probe is driven
through the module's existing `_send` transport seam with a stand-in, exactly
as the rest of the suite does, so the real client, the real admission gate and
the real response taxonomy all run with only the socket absent.
"""

import json
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged

from .test_api_client import FakeResponse, _success_body

from ..models.shopify_connector_setup_wizard import (
    LEGACY_NUMERIC_STEP_KEYS,
    READINESS_BLOCKING,
    READINESS_NOT_REQUIRED,
    READINESS_PASSED,
    READINESS_WAITING,
    READINESS_WARNING,
    SETUP_STEP_COUNT,
    SETUP_STEP_KEYS,
    SETUP_STEP_ORDER,
    SETUP_STEPS,
    SETUP_PHASES,
    SETUP_PHASE_COUNT,
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
        """The accepted 12 steps, in the accepted order (DEC-012 §1).

        Asserted against the literal list rather than against a count, because
        a reordering is exactly the kind of change that keeps the count and
        breaks the flow -- credentials before store identity, or readiness
        before the choices it reads, which is precisely the defect Wave 5
        corrects.
        """
        self.assertEqual(SETUP_STEP_COUNT, 12)
        self.assertEqual(
            [key for key, _label in SETUP_STEPS],
            [
                'welcome', 'identity', 'credential', 'scopes',
                'test_connection', 'directions', 'location_mapping',
                'source_of_truth', 'notification', 'first_push',
                'final_readiness', 'review',
            ],
        )

    def test_readiness_runs_after_every_choice_it_reads(self):
        """The ordering defect, asserted as an invariant rather than a list.

        `domain_flag_enablement` reads the domain flags and `mapped_location`
        reads the location mappings, so both of the steps that write those --
        `directions` and `location_mapping` -- must come BEFORE the step that
        evaluates them. This is what actually broke: readiness sat at position
        six and judged a configuration that did not exist yet.
        """
        readiness_at = SETUP_STEP_ORDER['final_readiness']
        for earlier in ('directions', 'location_mapping', 'source_of_truth',
                        'notification', 'first_push'):
            self.assertLess(
                SETUP_STEP_ORDER[earlier], readiness_at,
                '%s must be answered before readiness evaluates it' % earlier,
            )
        self.assertLess(readiness_at, SETUP_STEP_ORDER['review'])

    def test_the_state_payload_names_every_step_in_order(self):
        state = self._as(self.admin_a).get_setup_state()
        self.assertEqual(state['step_count'], 12)
        self.assertEqual(
            [step['index'] for step in state['steps']], list(range(1, 13)),
        )
        self.assertEqual(
            [step['key'] for step in state['steps']], list(SETUP_STEP_KEYS),
        )
        self.assertEqual(state['steps'][0]['key'], 'welcome')
        self.assertEqual(state['steps'][-1]['key'], 'review')
        self.assertEqual(state['resume_step_key'], 'welcome')

    def test_five_merchant_phases_group_every_step_without_changing_keys(self):
        state = self._as(self.admin_a).get_setup_state()
        self.assertEqual(SETUP_PHASE_COUNT, 5)
        self.assertEqual(
            [phase[0] for phase in SETUP_PHASES],
            ['connect', 'choose', 'map', 'protect', 'verify'],
        )
        self.assertEqual(state['phase_count'], 5)
        self.assertEqual(
            [phase['label'] for phase in state['phases']],
            ['Connect', 'Choose', 'Map', 'Protect', 'Verify'],
        )
        grouped = [
            step_key
            for phase in state['phases']
            for step_key in phase['step_keys']
        ]
        self.assertEqual(grouped, list(SETUP_STEP_KEYS))
        self.assertEqual(
            [step['phase_key'] for step in state['steps']],
            [
                'connect', 'connect', 'connect', 'connect', 'connect',
                'choose', 'map', 'protect', 'protect', 'protect',
                'verify', 'verify',
            ],
        )

    def test_scopes_are_derived_from_the_governed_declaration(self):
        """Not a hand-written list that can go stale on a setup screen.

        Correction B: the screen reads `_governed_scope_catalog()`, an
        extensible seam an installed domain module can add its own entries
        to (step 4 runs before step 7's domain choice exists, so it shows
        the full installed superset). `REQUIRED_MVP_SCOPES` is therefore
        asserted as a SUBSET, not an exact match: whichever other connector
        modules happen to be installed alongside core in this test
        environment may legitimately add more.
        """
        store = self._make_store()
        state = self._as(self.admin_a).get_setup_state(store.id)
        declared = set(
            self.env['shopify.connector.readiness.check'].REQUIRED_MVP_SCOPES
        )
        shown = {entry['scope'] for entry in state['scopes']}
        self.assertTrue(
            declared <= shown,
            'every unconditionally-required core scope must be shown',
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
            lambda: setup.get_setup_state(new_store=True),
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

    def test_an_explicit_new_store_flow_does_not_select_or_change_existing(self):
        existing = self._make_store(
            name='Existing store', domain='existing-store.myshopify.com',
        )

        # Normal entry still resumes the only visible store. The explicit
        # flag is the deliberate escape hatch for the second-store path.
        resumed = self._as(self.admin_a).get_setup_state()
        self.assertEqual(resumed['store']['id'], existing.id)
        blank = self._as(self.admin_a).get_setup_state(new_store=True)
        self.assertFalse(blank['store']['id'])
        self.assertEqual(blank['store']['name'], '')
        self.assertEqual(blank['store']['shop_domain'], '')
        self.assertEqual([row['id'] for row in blank['stores']], [existing.id])

        with self.assertRaises(UserError):
            self._as(self.admin_a).get_setup_state(
                store_id=existing.id, new_store=True,
            )

        created = self._as(self.admin_a).save_store_identity(
            'Second store', 'second-store.myshopify.com',
        )
        second = self.Store.browse(created['store']['id'])
        self.assertNotEqual(second, existing)
        self.assertEqual(
            self.Store.search_count([
                ('company_id', '=', self.company_a.id),
            ]),
            2,
        )
        existing.invalidate_recordset()
        self.assertEqual(existing.name, 'Existing store')
        self.assertEqual(existing.shop_domain, 'existing-store.myshopify.com')

    def test_multiple_stores_resume_the_oldest_unless_new_store_is_explicit(self):
        first = self._make_store(
            name='First store', domain='first-store.myshopify.com',
        )
        second_state = self._as(self.admin_a).save_store_identity(
            'Second existing store', 'second-existing.myshopify.com',
        )
        second = self.Store.browse(second_state['store']['id'])

        resumed = self._as(self.admin_a).get_setup_state()
        self.assertEqual(resumed['store']['id'], first.id)
        self.assertEqual(
            [row['id'] for row in resumed['stores']],
            [first.id, second.id],
        )

        blank = self._as(self.admin_a).get_setup_state(new_store=True)
        self.assertFalse(blank['store']['id'])
        self.assertEqual(
            [row['id'] for row in blank['stores']],
            [first.id, second.id],
        )

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
        """Every read shape, not only the one that wrote it.

        Wave 5 sharpened this from a substring scan to a structural walk. The
        payload now legitimately carries the MODE NAME
        `offline_access_token`, whose spelling contains the old forbidden
        substring, so the substring test would flag a mode label while still
        missing a secret under a differently-named key. The walk is stricter
        on what matters: no KEY anywhere in the payload may be a secret field
        name, and no VALUE may be the credential.
        """
        forbidden_keys = {'access_token', 'client_secret'}

        def walk_keys(node):
            if isinstance(node, dict):
                for key, value in node.items():
                    self.assertNotIn(key, forbidden_keys)
                    walk_keys(value)
            elif isinstance(node, (list, tuple)):
                for item in node:
                    walk_keys(item)

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
            walk_keys(payload)

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
        self.assertEqual(
            self._settings(store).setup_wizard_step_key, 'test_connection',
        )

    def test_a_later_pass_supersedes_obsolete_connection_failures(self):
        store = self._ready_store()
        old_failure = self.env['shopify.connector.job'].sudo().create({
            'store_id': store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'core_test_connection',
            'state': 'failed_final',
            'payload_hash': 'obsolete-connection-failure',
            'finished_at': fields.Datetime.now(),
        })

        with self._transport(ok=True):
            self._as(self.admin_a).run_test_connection(store.id)

        old_failure.invalidate_recordset()
        self.assertTrue(old_failure.superseded_by_job_id)
        self.assertEqual(old_failure.superseded_by_job_id.state, 'succeeded')
        self.assertEqual(old_failure.superseded_by_job_id.store_id, store)

    def test_a_failing_test_connection_does_not_advance_or_lose_the_token(self):
        """A refusal must not read as a pass, and must not discard the
        credential the operator has just entered."""
        store = self._make_store()
        self._as(self.admin_a).save_credential(store.id, DUMMY_TOKEN)
        before = self._settings(store).setup_wizard_step_key
        with self._transport(ok=False):
            state = self._as(self.admin_a).run_test_connection(store.id)
        store.invalidate_recordset()
        self.assertNotEqual(state['store']['test_connection_result'], 'pass')
        self.assertEqual(
            self._settings(store).setup_wizard_step_key, before,
        )
        self.assertTrue(
            store.credential_present,
            'a failed test must not corrupt an already stored credential',
        )

    # --- final readiness ------------------------------------------------

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
            # presentation state and its label are the meaning.
            self.assertIn(check['state'], (
                READINESS_PASSED, READINESS_WARNING, READINESS_BLOCKING,
                READINESS_WAITING, READINESS_NOT_REQUIRED,
            ))
            self.assertTrue(check['state_label'])
            self.assertIn(check['tone'], (
                'success', 'warning', 'danger', 'info', 'neutral',
            ))

    def test_a_warning_never_becomes_a_blocking_failure(self):
        store = self._ready_store()
        state = self._as(self.admin_a).run_readiness(store.id)
        for check in state['readiness']['blocking']:
            self.assertEqual(check['tier'], 'essential')
            self.assertEqual(check['state'], READINESS_BLOCKING)

    # --- directions -----------------------------------------------------

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

    def test_selected_read_workflows_enable_their_schedulers(self):
        """Choosing a workflow is the complete onboarding decision."""
        store = self._ready_store()
        self._as(self.admin_a).save_directions(
            store.id, ['product_import', 'sale'],
        )
        settings = self._settings(store)
        if 'product_scheduled_sync_enabled' in settings._fields:
            self.assertTrue(settings.product_scheduled_sync_enabled)
        if 'order_scheduled_sync_enabled' in settings._fields:
            self.assertTrue(settings.order_scheduled_sync_enabled)

        self._as(self.admin_a).save_directions(store.id, [])
        settings.invalidate_recordset()
        if 'product_scheduled_sync_enabled' in settings._fields:
            self.assertFalse(settings.product_scheduled_sync_enabled)
        if 'order_scheduled_sync_enabled' in settings._fields:
            self.assertFalse(settings.order_scheduled_sync_enabled)

    # --- source of truth ------------------------------------------------

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

    # --- customer notifications -----------------------------------------

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

    # --- first stock push -----------------------------------------------

    def test_first_push_scanning_never_bypasses_the_guard(self):
        """Scanning does not preview, confirm, admit or write a quantity."""
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

    def test_inventory_enabled_cannot_silently_disable_first_push_scanning(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['inventory'])
        self._as(self.admin_a).save_first_push_schedule(store.id, False)
        settings = self._settings(store)
        if 'inventory_scheduled_sync_enabled' in settings._fields:
            self.assertTrue(settings.inventory_scheduled_sync_enabled)

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
        self._as(self.admin_a).save_and_exit(store.id, 'directions')
        state = self._as(self.admin_a).get_setup_state(store.id)
        self.assertEqual(state['resume_step_key'], 'directions')
        self.assertEqual(
            state['resume_step'], SETUP_STEP_ORDER['directions'],
            'the ordinal is derived from the key, never stored independently',
        )

    def test_back_does_not_lose_a_saved_choice(self):
        """Back is navigation. Every saved value is already on its owning
        record, so paging back and re-reading returns it unchanged."""
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        self._as(self.admin_a).save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative')
        # Simulate paging back to the directions step and re-reading.
        self._as(self.admin_a).save_and_exit(store.id, 'directions')
        state = self._as(self.admin_a).get_setup_state(store.id)
        enabled = {d['key'] for d in state['domains'] if d['enabled']}
        self.assertEqual(enabled, {'sale'})
        self.assertEqual(state['summary']['price'], 'Odoo is the price authority')

    def test_the_resume_point_never_rewinds(self):
        """Re-reading an earlier step must not discard later progress."""
        store = self._ready_store()
        self._as(self.admin_a).save_and_exit(store.id, 'source_of_truth')
        self._as(self.admin_a).save_and_exit(store.id, 'credential')
        state = self._as(self.admin_a).get_setup_state(store.id)
        self.assertEqual(state['resume_step_key'], 'source_of_truth')

    def test_an_unknown_step_key_is_refused(self):
        store = self._ready_store()
        for bad in ('', 'three', None, 'readiness', 'not_a_step'):
            with self.subTest(step=bad):
                with self.assertRaises(UserError):
                    self._as(self.admin_a).save_and_exit(store.id, bad)

    def test_a_numeric_step_is_refused_rather_than_translated(self):
        """The numeric-navigation regression, made to fail.

        A client that still sends an ordinal is a client built against the
        pre-Wave-5 order. Quietly interpreting `8` as whatever step is eighth
        today would resume an operator on a screen they never asked for --
        before this wave `8` meant Source of truth and now it does not. The
        refusal is the point: it is loud, and a silent mistranslation is not.
        """
        store = self._ready_store()
        for ordinal in (1, 5, 8, 11, 12, 0, -1, 99):
            with self.subTest(ordinal=ordinal):
                with self.assertRaises(UserError):
                    self._as(self.admin_a).save_and_exit(store.id, ordinal)
        # ...and nothing moved.
        self.assertEqual(
            self._settings(store).setup_wizard_step_key, 'test_connection',
        )

    def test_browser_state_is_not_the_source_of_truth(self):
        """The resume point is a column, readable by a second administrator on
        a different machine -- not something in one browser's storage."""
        store = self._ready_store()
        self._as(self.admin_a).save_and_exit(store.id, 'notification')
        settings = self._settings(store)
        self.assertEqual(settings.setup_wizard_step_key, 'notification')
        # The ordinal is kept in step with the key so the two can never
        # disagree, but it is derived from it and is display only.
        self.assertEqual(
            settings.setup_wizard_step, SETUP_STEP_ORDER['notification'],
        )

    def test_a_stale_or_foreign_resume_identifier_fails_closed(self):
        store = self._ready_store()
        with self.assertRaises(UserError):
            self._as(self.admin_a).get_setup_state(store.id + 10 ** 6)
        self._assert_refused(
            lambda: self._as(self.admin_b).get_setup_state(store.id))

    def test_a_foreign_store_id_is_not_a_useful_existence_oracle(self):
        """Correction E (independent review, P3).

        A same-ROLE, cross-COMPANY Administrator supplying a REAL foreign
        store id and one supplying a nonexistent id must receive the
        identical refusal -- same exception class, same message -- so
        neither response lets them learn a foreign id merely exists.
        """
        store = self._ready_store()
        nonexistent_id = store.id + 10 ** 6

        def refusal_for(candidate_id):
            try:
                self._as(self.admin_b).get_setup_state(candidate_id)
            except (AccessError, UserError) as exc:
                return type(exc), str(exc)
            raise AssertionError(
                'candidate_id=%s was not refused' % candidate_id
            )

        foreign_class, foreign_message = refusal_for(store.id)
        missing_class, missing_message = refusal_for(nonexistent_id)
        self.assertEqual(
            foreign_class, missing_class,
            'A foreign store and a nonexistent one must fail the same way.',
        )
        self.assertEqual(
            foreign_message, missing_message,
            'The refusal text must not distinguish "not yours" from '
            '"does not exist".',
        )
        self.assertEqual(foreign_class, UserError)

    def test_a_foreign_store_id_reveals_no_field_of_the_foreign_record(self):
        """The refusal is generic; nothing about the foreign store -- not
        even its own existence, distinctly from a made-up id -- crosses the
        boundary through `get_setup_state`."""
        store = self._ready_store()
        store.sudo().write({'name': 'Correction E Foreign Store Name'})
        try:
            self._as(self.admin_b).get_setup_state(store.id)
        except (AccessError, UserError) as exc:
            self.assertNotIn('Correction E Foreign Store Name', str(exc))
            self.assertNotIn(store.shop_domain, str(exc))
        else:
            raise AssertionError('a foreign store id was not refused')


@tagged('post_install', '-at_install')
class TestSetupWizardActivation(SetupWizardCase):

    def _complete_through_readiness(self, directions=None):
        """Walk steps 2-10 the way an operator does, with a passable
        environment, so the success path is genuinely observable.

        `directions` defaults to `['sale']`, one accepted domain -- not
        because a connect-only (zero-domain) setup is illegitimate (it is
        explicitly accepted; see `test_a_genuine_connect_only_store_can_
        activate` below, which drives that exact path through this same
        production route) but because most callers of this helper are
        testing something else entirely and picking any one valid domain
        keeps their fixture unsurprising.
        """
        self._make_readiness_passable()
        store = self._ready_store()
        setup = self._as(self.admin_a)
        setup.save_directions(
            store.id, ['sale'] if directions is None else directions,
        )
        setup.acknowledge_location_mapping(store.id)
        setup.save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative')
        setup.save_notification(store.id, False)
        setup.save_first_push_schedule(store.id, False)
        # Readiness LAST, which is the whole ordering correction: it now runs
        # against the configuration above rather than before it exists.
        setup.run_readiness(store.id)
        store.invalidate_recordset()
        return store

    def test_activation_re_runs_readiness_when_the_step_was_not_run(self):
        """PR #204 Odoo.sh qualification correction, 2026-07-31.

        The test this replaces asserted `activate()` refuses before the
        `final_readiness` step has run. That held locally only because a
        bare test server's default `web.base.url` is plain HTTP, which the
        essential `web_base_url` check fails on its own -- the refusal it
        observed was an unrelated essential failure, not proof that
        skipping the step blocks activation. On genuine Odoo.sh
        `web.base.url` is a real HTTPS address, that essential check
        passes, and `activate()`'s own server-side rerun (`if store.
        credential_present: run_for_store(...)`, below) then produces a
        genuine pass -- so the old assertion failed three times with
        `UserError not raised`. What is actually true, and load-bearing, is
        the opposite of what that test asserted: activation is safe
        precisely because it always re-proves readiness itself from real
        stored evidence, rather than trusting that an operator ran the step
        first.
        """
        self._make_readiness_passable()
        store = self._ready_store()
        Job = self.env['shopify.connector.job'].sudo()
        jobs_before = Job.search_count([
            ('store_id', '=', store.id),
            ('state', 'in', ('queued', 'running')),
        ])
        readiness_runs_before = Job.search_count([
            ('store_id', '=', store.id),
            ('job_type', '=', 'core_readiness_check'),
        ])
        # Real stored state, not a fabricated payload: the final-readiness
        # step's own progress key has never been written, and no readiness
        # evidence of any kind exists yet.
        self.assertNotEqual(
            self._settings(store).setup_wizard_step_key, 'final_readiness',
            'the final-readiness step must not already have run',
        )
        self.assertFalse(
            store.last_readiness_at,
            'no readiness evidence may exist before activation reruns it',
        )

        Client = type(self.env['shopify.connector.api.client'])

        def refuse(_self, _store, request, token=None, mutation_context=None):
            raise AssertionError('activation contacted Shopify')

        # If activate()'s server-side rerun were ever removed, this call
        # raises UserError ("Run the readiness checks before activating
        # this store.") right here, because last_readiness_at is still
        # falsy -- failing this test at this line rather than downstream.
        with patch.object(Client, '_send', refuse):
            self._as(self.admin_a).activate(store.id)
        store.invalidate_recordset()

        # Genuine evidence, produced through the real run_for_store route.
        self.assertTrue(
            store.last_readiness_at,
            'activation must produce its own readiness evidence',
        )
        self.assertEqual(
            Job.search_count([
                ('store_id', '=', store.id),
                ('job_type', '=', 'core_readiness_check'),
            ]),
            readiness_runs_before + 1,
            'activation must run readiness through the real job route',
        )
        # Connected only because the resulting checks passed: a blocking or
        # not-yet-run result would have raised UserError above instead of
        # reaching this line.
        self.assertIn(store.last_readiness_result, ('pass', 'warning'))
        self.assertEqual(store.state, 'connected')
        self.assertEqual(
            Job.search_count([
                ('store_id', '=', store.id),
                ('state', 'in', ('queued', 'running')),
            ]),
            jobs_before,
            'activation must enqueue no domain job',
        )

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

    def test_activation_admits_no_direct_job_and_writes_nothing_to_shopify(self):
        """The review step only nudges existing read-side cron producers.

        The transport seam is replaced with a responder that FAILS the test if
        it is reached, and no domain job is admitted in the activation
        transaction. The scheduled producers run later through their normal
        eligibility and queue boundaries.
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

    def test_a_genuine_connect_only_store_can_activate(self):
        """Correction B (independent review, Defect #2).

        `docs/02-product/ui-ux-final-design-spec.md` and the wizard's own
        `directions` copy both explicitly promise that skipping every domain is
        an allowed, deliberate outcome ("connect-only setup"). Before this
        correction, `_check_domain_flag_enablement` was an ESSENTIAL check
        that unconditionally failed on zero enabled domains, with no
        exception for that deliberate choice -- an Administrator who
        followed the wizard's own instructions reached the review step and
        could never activate. This drives the exact production route: the
        `directions` step with an empty selection, through to `activate()`.
        """
        store = self._complete_through_readiness(directions=[])
        settings = self._settings(store)
        for flag in (
            'product_domain_enabled', 'sale_domain_enabled',
            'inventory_domain_enabled', 'fulfillment_domain_enabled',
        ):
            self.assertFalse(getattr(settings, flag))
        jobs_before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', store.id),
            ('state', 'in', ('queued', 'running')),
        ])
        Client = type(self.env['shopify.connector.api.client'])

        def refuse(_self, _store, request, token=None, mutation_context=None):
            raise AssertionError('connect-only activation contacted Shopify')

        with patch.object(Client, '_send', refuse):
            self._as(self.admin_a).activate(store.id)
        store.invalidate_recordset()
        self.assertEqual(
            store.state, 'connected',
            'A deliberate connect-only setup must be able to activate.',
        )
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', store.id),
                ('state', 'in', ('queued', 'running')),
            ]),
            jobs_before,
            'connect-only activation must admit no domain job',
        )
        for flag in (
            'product_domain_enabled', 'sale_domain_enabled',
            'inventory_domain_enabled', 'fulfillment_domain_enabled',
        ):
            self.assertFalse(
                getattr(settings, flag),
                'activation must not silently enable a domain',
            )

    def test_the_domain_flag_check_is_non_blocking_not_essential(self):
        """The tier correction directly: WARNING, never ESSENTIAL, so a
        zero-domain result can never by itself fail the aggregate."""
        store = self._ready_store()
        Check = self.env['shopify.connector.readiness.check']
        result = Check._check_domain_flag_enablement(store)
        self.assertEqual(result['tier'], Check.WARNING)

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
        self.assertEqual(state['resume_step_key'], 'welcome')

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
        self.assertEqual(
            self._settings(store).setup_wizard_step_key, 'welcome',
        )

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
        self.assertTrue(
            Dashboard.with_user(self.admin_a).get_sales_dashboard_data()
            ['setup_available'],
        )
        self.assertFalse(
            Dashboard.with_user(self.user_a).get_sales_dashboard_data()
            ['setup_available'],
        )


@tagged('post_install', '-at_install')
class TestSetupWizardSemanticProgress(SetupWizardCase):
    """Wave 5: the semantic key is the authority, and legacy progress moves.

    These are the tests that fail on the pre-Wave-5 head, because on that head
    the field they read does not exist and the order they assert is a
    different order.
    """

    def test_the_semantic_key_is_what_persistence_records(self):
        store = self._ready_store()
        settings = self._settings(store)
        self.assertEqual(settings.setup_wizard_step_key, 'test_connection')
        self.assertEqual(
            settings.setup_wizard_step, SETUP_STEP_ORDER['test_connection'],
        )

    def test_every_legacy_position_translates_to_a_real_step(self):
        """The compatibility table is total over the old range and monotone.

        Monotone matters as much as total: a store that got further under the
        old order must not resume EARLIER than one that got less far, or
        upgrading would shuffle two administrators' progress relative to each
        other for no reason either of them could see.
        """
        self.assertEqual(sorted(LEGACY_NUMERIC_STEP_KEYS), list(range(1, 12)))
        previous = 0
        for legacy in range(1, 12):
            key = LEGACY_NUMERIC_STEP_KEYS[legacy]
            self.assertIn(key, SETUP_STEP_ORDER)
            self.assertGreaterEqual(SETUP_STEP_ORDER[key], previous)
            previous = SETUP_STEP_ORDER[key]

    def test_existing_numeric_progress_resumes_without_being_reset(self):
        """A row written before the key existed still resumes where it was.

        Seeded exactly as a pre-Wave-5 database holds it: a number, and no
        key at all. The read-time translation is what has to work here --
        the migration is the other half, and covers the rows it reaches.
        """
        store = self._make_store()
        settings = self._settings(store)
        for legacy, expected in (
            (2, 'identity'),
            (5, 'test_connection'),
            (6, 'directions'),
            (7, 'directions'),
            (8, 'source_of_truth'),
            (10, 'first_push'),
            (11, 'review'),
        ):
            with self.subTest(legacy=legacy):
                settings.sudo().write({
                    'setup_wizard_step': legacy,
                    'setup_wizard_step_key': False,
                })
                state = self._as(self.admin_a).get_setup_state(store.id)
                self.assertEqual(state['resume_step_key'], expected)

    def test_a_legacy_row_is_upgraded_in_place_and_loses_no_choice(self):
        store = self._ready_store()
        setup = self._as(self.admin_a)
        setup.save_directions(store.id, ['sale'])
        setup.save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative')
        settings = self._settings(store)
        # Rewind to the legacy shape: a number, no key.
        settings.sudo().write({
            'setup_wizard_step': 8, 'setup_wizard_step_key': False,
        })
        setup.acknowledge_location_mapping(store.id)
        settings.invalidate_recordset()
        # The key is now written, and no stored choice was touched.
        self.assertIn(settings.setup_wizard_step_key, SETUP_STEP_ORDER)
        self.assertTrue(settings.sale_domain_enabled)
        self.assertEqual(settings.product_first_sync_source, 'odoo_source')
        self.assertEqual(
            settings.price_source_of_truth, 'odoo_authoritative')

    def test_the_resume_point_is_never_rewound_by_a_legacy_translation(self):
        """A legacy number must not undo progress recorded semantically."""
        store = self._ready_store()
        setup = self._as(self.admin_a)
        setup.save_and_exit(store.id, 'notification')
        settings = self._settings(store)
        # A stale WRITE of the old numeric column alone cannot pull the
        # resume point backwards, because the key is what is read.
        settings.sudo().write({'setup_wizard_step': 2})
        state = setup.get_setup_state(store.id)
        self.assertEqual(state['resume_step_key'], 'notification')


@tagged('post_install', '-at_install')
class TestSetupWizardConditionalLocationStep(SetupWizardCase):
    """The conditional step is present, positioned and explained."""

    def test_the_step_is_never_removed_from_the_list(self):
        store = self._ready_store()
        for directions in ([], ['inventory']):
            with self.subTest(directions=directions):
                self._as(self.admin_a).save_directions(store.id, directions)
                state = self._as(self.admin_a).get_setup_state(store.id)
                keys = [step['key'] for step in state['steps']]
                self.assertEqual(keys, list(SETUP_STEP_KEYS))
                self.assertEqual(len(keys), SETUP_STEP_COUNT)

    def test_inventory_disabled_marks_the_step_not_required_and_explains(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        state = self._as(self.admin_a).get_setup_state(store.id)
        step = next(
            s for s in state['steps'] if s['key'] == 'location_mapping'
        )
        self.assertFalse(step['applicable'])
        self.assertIn('not enabled', step['skipped_reason'])

    def test_inventory_disabled_enqueues_no_location_refresh(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', store.id),
        ])
        self._as(self.admin_a).acknowledge_location_mapping(store.id)
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', store.id),
            ]),
            before,
            'continuing past a not-required step must admit no job',
        )

    def test_continuing_past_the_step_fabricates_no_mapping(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['inventory'])
        with self.assertRaises(UserError):
            self._as(self.admin_a).acknowledge_location_mapping(store.id)
        if 'shopify.connector.location.mapping' in self.env:
            self.assertFalse(
                self.env['shopify.connector.location.mapping'].sudo().search(
                    [('store_id', '=', store.id)],
                ),
                'no mapping may be invented by pressing Continue',
            )

    def test_the_step_records_progress_under_its_own_key(self):
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        self._as(self.admin_a).acknowledge_location_mapping(store.id)
        self.assertEqual(
            self._settings(store).setup_wizard_step_key, 'location_mapping',
        )


@tagged('post_install', '-at_install')
class TestSetupWizardReadinessPresentation(SetupWizardCase):
    """Five presentation states, and no green result for anything unproven."""

    def _checks_by_code(self, state):
        return {check['code']: check for check in state['readiness']['checks']}

    def test_a_not_applicable_check_is_not_required_not_passed(self):
        """A check that examined nothing must not render as a success."""
        self._make_readiness_passable()
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        state = self._as(self.admin_a).run_readiness(store.id)
        checks = self._checks_by_code(state)
        self.assertIn('mapped_location', checks)
        self.assertEqual(
            checks['mapped_location']['state'], READINESS_NOT_REQUIRED,
        )
        self.assertEqual(
            checks['mapped_location']['state_label'], 'Not required',
        )
        self.assertNotEqual(checks['mapped_location']['tone'], 'success')

    def test_the_domain_check_reads_as_a_feature_selection(self):
        self._make_readiness_passable()
        store = self._ready_store()
        state = self._as(self.admin_a).run_readiness(store.id)
        checks = self._checks_by_code(state)
        self.assertEqual(
            checks['domain_flag_enablement']['label'],
            'Sync features selected',
        )

    def test_connect_only_produces_a_non_blocking_warning_in_these_words(self):
        self._make_readiness_passable()
        store = self._ready_store()
        self._as(self.admin_a).save_directions(store.id, [])
        state = self._as(self.admin_a).run_readiness(store.id)
        checks = self._checks_by_code(state)
        entry = checks['domain_flag_enablement']
        self.assertEqual(entry['state'], READINESS_WARNING)
        self.assertEqual(
            entry['reason'],
            'No sync features are enabled. This store will connect without '
            'syncing. You can enable features later from Sync Rules.',
        )
        self.assertNotIn(entry, state['readiness']['blocking'])

    def test_a_readiness_relevant_change_makes_earlier_evidence_stale(self):
        """Changing what a check reads must not leave a green screen behind."""
        self._make_readiness_passable()
        store = self._ready_store()
        state = self._as(self.admin_a).run_readiness(store.id)
        self.assertFalse(state['readiness']['stale'])
        # Enabling a domain changes exactly what `domain_flag_enablement` and
        # `mapped_location` read.
        self._as(self.admin_a).save_directions(store.id, ['inventory'])
        state = self._as(self.admin_a).get_setup_state(store.id)
        self.assertTrue(state['readiness']['stale'])
        for check in state['readiness']['checks']:
            self.assertEqual(check['state'], READINESS_WAITING)
            self.assertNotEqual(check['tone'], 'success')
        self.assertFalse(state['summary']['can_activate'])

    def test_re_running_the_checks_clears_the_staleness(self):
        self._make_readiness_passable()
        store = self._ready_store()
        self._as(self.admin_a).run_readiness(store.id)
        self._as(self.admin_a).save_directions(store.id, ['sale'])
        self.assertTrue(
            self._as(self.admin_a).get_setup_state(store.id)
            ['readiness']['stale'],
        )
        state = self._as(self.admin_a).run_readiness(store.id)
        self.assertFalse(state['readiness']['stale'])

    def test_entering_final_readiness_evaluates_what_is_currently_saved(self):
        """The step's own run reflects the choices above it, not earlier ones.

        Driven through the production route: choose directions, then run the
        step. `mapped_location` is essential and the inventory domain has just
        been enabled with nothing mapped, so a result computed BEFORE that
        choice would still be reporting a pass.
        """
        self._make_readiness_passable()
        store = self._ready_store()
        setup = self._as(self.admin_a)
        setup.run_readiness(store.id)
        before = self._checks_by_code(setup.get_setup_state(store.id))
        self.assertEqual(
            before['mapped_location']['state'], READINESS_NOT_REQUIRED,
        )
        setup.save_directions(store.id, ['inventory'])
        state = setup.run_readiness(store.id)
        after = self._checks_by_code(state)
        self.assertNotEqual(
            after['mapped_location']['state'], READINESS_NOT_REQUIRED,
        )
        self.assertNotEqual(after['mapped_location']['tone'], 'success')

    def test_the_mapped_location_fix_action_deep_links_by_step_key(self):
        self._make_readiness_passable()
        store = self._ready_store()
        setup = self._as(self.admin_a)
        setup.save_directions(store.id, ['inventory'])
        state = setup.run_readiness(store.id)
        entry = self._checks_by_code(state)['mapped_location']
        self.assertEqual(entry['action_step_key'], 'location_mapping')
        self.assertEqual(entry['action_label'], 'Fix location mapping')
        # Addressed by KEY, never by an ordinal that shifts when a step is
        # inserted.
        self.assertNotIsInstance(entry['action_step_key'], int)

    def test_activation_is_refused_while_readiness_is_waiting(self):
        """Activation re-runs readiness, so this has to be produced rather
        than simulated: a stale mark alone is cleared by the re-run. The
        genuine waiting case is an essential check that cannot be proven --
        inventory enabled with nothing mapped -- which is blocking, and the
        refusal must name it."""
        self._make_readiness_passable()
        store = self._ready_store()
        setup = self._as(self.admin_a)
        setup.save_directions(store.id, ['inventory'])
        setup.save_source_of_truth(
            store.id, 'odoo_source', 'odoo_authoritative')
        setup.save_notification(store.id, False)
        setup.save_first_push_schedule(store.id, False)
        setup.run_readiness(store.id)
        with self.assertRaises(UserError) as caught:
            with self._transport(ok=True):
                setup.activate(store.id)
        self.assertIn('location', str(caught.exception).lower())
        store.invalidate_recordset()
        self.assertNotEqual(store.state, 'connected')

    def test_the_credential_step_names_the_two_values_that_are_not_a_token(self):
        """B: the copy is on the shipped template, not only in a docstring.

        Wave 5 split the credential step into two paths, and the expiry rule
        split with it. The OFFLINE path must still make no universal-expiry
        claim -- how long a pasted token lives depends on how it was issued,
        and the copy that says so must stay. The DEV DASHBOARD path is the
        opposite case: Shopify documents that its token "expires after 24
        hours" as a fact, and the screen must state it NEXT TO the automatic
        renewal, never as something the merchant has to manage by hand. And
        no path may tell a Dev Dashboard user a token is "shown once" --
        that is the old flow's copy, and it is false in the current one.
        """
        import pathlib
        template = (
            pathlib.Path(__file__).resolve().parents[1]
            / 'static' / 'src' / 'xml' / 'shopify_connector_setup_wizard.xml'
        ).read_text()
        self.assertIn('Admin API access token', template)
        self.assertIn('not the Client ID', template)
        self.assertIn('Client Secret', template)
        # The offline path's anti-universal-expiry copy, verbatim.
        self.assertIn('How long a token stays valid depends on how it was', template)
        # The Dev Dashboard path: the documented 24-hour fact appears exactly
        # once, and in the same sentence as the automatic renewal.
        self.assertEqual(template.count('24 hours'), 1)
        self.assertIn(
            'lasts 24 hours; Odoo requests a fresh one', template,
        )
        self.assertIn('same Shopify organization', template)
        # Never the old path's "token shown once" claim.
        self.assertNotIn('shown once', template)
        self.assertNotIn('displayed once', template)


@tagged('post_install', '-at_install')
class TestSetupWizardSourceGuards(SetupWizardCase):
    """Static guards: the properties that regress silently if nobody looks."""

    def _asset(self, *parts):
        import pathlib
        return (
            pathlib.Path(__file__).resolve().parents[1].joinpath(*parts)
        ).read_text()

    def _code_only(self, source, kind):
        """The asset with its comments removed.

        A guard that greps prose finds the sentence explaining why the
        forbidden shape is forbidden and reports it as the shape itself. The
        comments in these two files necessarily QUOTE `state.step === 8` --
        that is what they are warning about -- so the scan has to be over
        code. Deliberately conservative: this only removes `//`, `/* */` and
        `<!-- -->`, which is enough here and cannot accidentally delete a
        branch.
        """
        import re
        if kind == 'js':
            source = re.sub(r'/\*.*?\*/', '', source, flags=re.S)
            source = re.sub(r'^\s*//.*$', '', source, flags=re.M)
            return source
        return re.sub(r'<!--.*?-->', '', source, flags=re.S)

    def test_the_client_never_navigates_by_a_numeric_step_position(self):
        """The numeric-navigation regression, as a source invariant.

        A behavioural test can only catch the ordinals somebody happened to
        write a case for. This catches the shape: no comparison of the
        current step against a bare number may exist in the client at all,
        because that is precisely the coupling that made inserting a step
        into the middle of the order silently reroute every later branch.
        """
        import re
        js = self._asset('static', 'src', 'js',
                         'shopify_connector_setup_wizard.js')
        xml = self._asset('static', 'src', 'xml',
                          'shopify_connector_setup_wizard.xml')
        offenders = []
        for name, source in (('js', js), ('xml', xml)):
            code = self._code_only(source, name)
            for pattern in (
                r'state\.step\b(?!Key)',
                r'stepKey\s*[=!]==?\s*\d',
                r'\bcase\s+\d+\s*:',
            ):
                for match in re.finditer(pattern, code):
                    offenders.append('%s: %r' % (name, match.group(0)))
        self.assertFalse(offenders, (
            'the setup client still addresses a step by position; every '
            'branch must compare a semantic step key: %s' % offenders
        ))

    def test_every_step_branch_in_the_template_names_a_real_key(self):
        import re
        xml = self._code_only(
            self._asset('static', 'src', 'xml',
                        'shopify_connector_setup_wizard.xml'),
            'xml',
        )
        used = set(re.findall(r"state\.stepKey === '([a-z_]+)'", xml))
        self.assertTrue(used, 'the template branches on no step key at all')
        unknown = used - set(SETUP_STEP_KEYS)
        self.assertFalse(unknown, (
            'the template renders a step key that does not exist: %s'
            % sorted(unknown)
        ))
        missing = set(SETUP_STEP_KEYS) - used
        self.assertFalse(missing, (
            'these accepted steps have no branch in the template, so they '
            'would render an empty panel: %s' % sorted(missing)
        ))

    def test_a_not_applicable_check_always_declares_itself(self):
        """Every "Not applicable" result must carry the explicit marker.

        The presentation rule reads `not_applicable`, deliberately, rather
        than matching the reason text -- copy is translatable and editable
        and a rule that depends on a phrase inside it breaks the first time
        somebody rewords one. That only holds while every producer sets the
        key, which is what this asserts, across every connector module at
        once.
        """
        import ast
        import pathlib
        addons = pathlib.Path(__file__).resolve().parents[2]
        offenders = []
        for path in sorted(addons.glob('shopify_connector_*/models/*.py')):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                name = getattr(func, 'attr', getattr(func, 'id', None))
                if name != '_check_result':
                    continue
                reason = None
                if len(node.args) >= 4 and isinstance(node.args[3], ast.Constant):
                    reason = node.args[3].value
                elif len(node.args) >= 4:
                    try:
                        reason = ast.literal_eval(node.args[3])
                    except (ValueError, SyntaxError):
                        reason = None
                if not isinstance(reason, str):
                    continue
                if not reason.startswith('Not applicable'):
                    continue
                declared = any(
                    kw.arg == 'not_applicable' for kw in node.keywords
                )
                if not declared:
                    offenders.append(
                        '%s:%d' % (path.name, node.lineno)
                    )
        self.assertFalse(offenders, (
            'these readiness checks return a "Not applicable" result without '
            'declaring `not_applicable=True`, so the setup surface would '
            'render them as a green Passed for something nobody examined: %s'
            % offenders
        ))
