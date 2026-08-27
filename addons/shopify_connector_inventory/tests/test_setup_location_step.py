"""Wave 5 (D): the guided setup's Location mapping step, end to end.

These run in the INVENTORY module deliberately. Core declares the three seams
and cannot implement them -- it owns no mapping concept and has no mapping
table -- so the only place the seam and its implementation are both present is
here. A core-side test could prove the seam exists; only this can prove it is
wired to the sanctioned service and refuses everything that service refuses.

No Shopify contact anywhere: the transport is replaced with a stand-in that
fails the test if it is reached.
"""

import json
from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools.safe_eval import safe_eval


# Issue #193 / #157 -- Odoo 19 test-phase contract; see
# docs/05-qa/odoo19-test-phase-contract.md.

#: Distinguishes "the caller passed no continuation" from "the caller
#: deliberately passed None", which the refusal tests need to do.
_UNSET = object()

@tagged('post_install', '-at_install')
class TestSetupLocationStep(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Setup = cls.env['shopify.connector.setup.wizard']
        cls.Service = cls.env['shopify.connector.inventory.service']
        cls.Mapping = cls.env['shopify.connector.location.mapping']
        cls.company_b = cls.env['res.company'].sudo().create({
            'name': 'Setup location company B',
        })
        cls.admin = cls._user('setup_loc_admin', 'admin')
        cls.admin_b = cls._user(
            'setup_loc_admin_b', 'admin', company=cls.company_b,
        )
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.location_a = cls.env['stock.location'].create({
            'name': 'Setup Step Location A',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.location_b = cls.env['stock.location'].create({
            'name': 'Setup Step Location B',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })

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

    def setUp(self):
        super().setUp()
        self.store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Setup Location Store',
            'shop_domain': 'setup-location-step.myshopify.com',
            'api_version': '2026-07',
            'company_id': self.env.company.id,
            'credential_present': True,
            'credential_last_verified_at': '2026-07-29 00:00:00',
            'last_test_connection_result': 'pass',
        })
        self.settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().create({
            'store_id': self.store.id, 'inventory_domain_enabled': True,
        })

    def _as(self, user=None):
        user = user or self.admin
        return self.Setup.with_user(user).with_context(
            allowed_company_ids=user.company_ids.ids,
        )

    def _cache(self, gid, name, active=True, store=None):
        return self.env['shopify.connector.location'].sudo().create({
            'store_id': (store or self.store).id,
            'shopify_location_gid': gid,
            'name': name,
            'shopify_location_active': active,
        })

    def _mark_refresh_succeeded(self):
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'inventory_location_sync',
            'state': 'queued',
            'payload_hash': 'setup-location-current-success',
            'expected_connection_generation':
                self.store.connection_generation,
        })
        job.sudo().write({'state': 'running'})
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        return job


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
        Client = type(self.env['shopify.connector.api.client'])

        def refuse(_self, _store, request, token=None, mutation_context=None):
            raise AssertionError('the setup location step contacted Shopify')

        return patch.object(Client, '_send', refuse)

    # --- the payload ----------------------------------------------------

    def test_permissions_catalog_names_inventory_write_scope(self):
        scopes = {
            entry['scope']
            for entry in self.env[
                'shopify.connector.readiness.check'
            ]._governed_scope_catalog()
        }
        self.assertIn('write_inventory', scopes)

    def test_zero_one_and_many_cached_locations(self):
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        self.assertTrue(payload['available'])
        self.assertEqual(payload['locations'], [])
        self.assertEqual(payload['mapped_count'], 0)
        self.assertEqual(payload['unmapped_count'], 0)

        self._cache('gid://shopify/Location/S1', 'Setup Warehouse One')
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        self.assertEqual(len(payload['locations']), 1)
        self.assertEqual(payload['locations'][0]['name'], 'Setup Warehouse One')
        self.assertFalse(payload['locations'][0]['mapped'])

        self._cache('gid://shopify/Location/S2', 'Setup Warehouse Two')
        self._cache('gid://shopify/Location/S3', 'Setup Warehouse Three')
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        self.assertEqual(len(payload['locations']), 3)
        self.assertEqual(payload['unmapped_count'], 3)

    def test_an_inactive_cached_location_is_not_offered(self):
        self._cache('gid://shopify/Location/ACTIVE', 'Active One')
        self._cache('gid://shopify/Location/GONE', 'Retired One', active=False)
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        gids = [entry['shopify_gid'] for entry in payload['locations']]
        self.assertIn('gid://shopify/Location/ACTIVE', gids)
        self.assertNotIn('gid://shopify/Location/GONE', gids)

    def test_a_foreign_store_location_never_appears(self):
        other = self.env['shopify.connector.store'].sudo().create({
            'name': 'Other Setup Store',
            'shop_domain': 'other-setup-location.myshopify.com',
            'api_version': '2026-07',
        })
        self._cache('gid://shopify/Location/OTHER', 'Foreign', store=other)
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        self.assertEqual(payload['locations'], [])

    def test_every_cached_location_carries_a_mapped_state(self):
        self._cache('gid://shopify/Location/M1', 'Mapped One')
        self._cache('gid://shopify/Location/M2', 'Unmapped One')
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/M1', self.location_a.id,
        )
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        by_gid = {e['shopify_gid']: e for e in payload['locations']}
        self.assertTrue(by_gid['gid://shopify/Location/M1']['mapped'])
        self.assertEqual(
            by_gid['gid://shopify/Location/M1']['odoo_location_name'],
            self.location_a.display_name,
        )
        self.assertFalse(by_gid['gid://shopify/Location/M2']['mapped'])
        self.assertEqual(payload['mapped_count'], 1)
        self.assertEqual(payload['unmapped_count'], 1)

    def test_eligible_odoo_locations_are_internal_and_company_valid(self):
        self._cache('gid://shopify/Location/E1', 'Eligible probe')
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        ids = {entry['id'] for entry in payload['odoo_locations']}
        self.assertIn(self.location_a.id, ids)
        self.assertIn(self.location_b.id, ids)
        offered = self.env['stock.location'].browse(sorted(ids))
        self.assertEqual(set(offered.mapped('usage')), {'internal'})
        for location in offered:
            self.assertIn(
                location.company_id.id,
                (False, self.store.company_id.id),
            )

    def test_map_wizard_domain_follows_store_company_and_keeps_server_fence(self):
        """The modal must not offer an allowed-but-foreign internal location.

        The service remains the authority: this test evaluates the actual
        field domain used by the modal and then proves the same foreign target
        is still rejected by the governed save path.
        """
        foreign = self.env['stock.location'].sudo().create({
            'name': 'Wizard Foreign Company Location',
            'usage': 'internal',
            'company_id': self.company_b.id,
        })
        Wizard = self.env['shopify.connector.location.map.wizard']
        wizard = Wizard.with_user(self.admin).with_context(
            default_store_id=self.store.id,
        ).new({'store_id': self.store.id})
        self.assertEqual(wizard.store_company_id, self.store.company_id)
        domain = safe_eval(
            Wizard._fields['odoo_location_id'].domain,
            {'store_company_id': self.store.company_id.id},
        )
        # Evaluate as sudo so record rules cannot make a missing company
        # predicate look correct by hiding the foreign row first.
        candidates = self.env['stock.location'].sudo().search(domain)
        self.assertIn(self.location_a, candidates)
        self.assertNotIn(foreign, candidates)
        Remap = self.env['shopify.connector.location.remap.wizard']
        self.assertIn(
            'store_company_id',
            Remap._fields['new_location_id'].domain,
        )

        self._cache('gid://shopify/Location/WIZARD-COMPANY', 'Wizard company')
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id,
                'gid://shopify/Location/WIZARD-COMPANY',
                foreign.id,
            )

    def test_a_foreign_company_odoo_location_is_not_offered(self):
        foreign = self.env['stock.location'].sudo().create({
            'name': 'Foreign Company Location',
            'usage': 'internal',
            'company_id': self.company_b.id,
        })
        self._cache('gid://shopify/Location/E2', 'Eligible probe two')
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        ids = {entry['id'] for entry in payload['odoo_locations']}
        self.assertNotIn(foreign.id, ids)

    # --- creation through the sanctioned service ------------------------

    def test_creation_delegates_to_the_sanctioned_service(self):
        self._cache('gid://shopify/Location/D1', 'Delegation probe')
        calls = []
        original = type(self.Service).create_or_update_location_mapping

        def spy(self_, store, odoo_location, gid, push_enabled=True):
            calls.append(gid)
            return original(
                self_, store, odoo_location, gid, push_enabled=push_enabled,
            )

        with patch.object(
            type(self.Service), 'create_or_update_location_mapping', spy,
        ):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/D1', self.location_a.id,
            )
        self.assertEqual(calls, ['gid://shopify/Location/D1'])

    def test_the_name_snapshot_comes_from_the_validated_cache(self):
        self._cache('gid://shopify/Location/N1', 'Cache Owned Name')
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/N1', self.location_a.id,
        )
        mapping = self.Mapping.sudo().search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Location/N1'),
        ])
        self.assertEqual(
            mapping.shopify_location_name_snapshot, 'Cache Owned Name',
        )

    def test_an_exact_repeat_submission_is_idempotent(self):
        self._cache('gid://shopify/Location/I1', 'Idempotent')
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/I1', self.location_a.id,
        )
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/I1', self.location_a.id,
        )
        self.assertEqual(
            self.Mapping.sudo().search_count([
                ('store_id', '=', self.store.id),
                ('shopify_gid', '=', 'gid://shopify/Location/I1'),
            ]),
            1,
        )

    def test_an_arbitrary_gid_typed_by_a_browser_is_refused(self):
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/NEVER-CACHED',
                self.location_a.id,
            )
        self.assertFalse(self.Mapping.sudo().search([
            ('store_id', '=', self.store.id),
        ]))

    def test_a_foreign_store_gid_is_refused(self):
        other = self.env['shopify.connector.store'].sudo().create({
            'name': 'Foreign GID Store',
            'shop_domain': 'foreign-gid-setup.myshopify.com',
            'api_version': '2026-07',
        })
        self._cache('gid://shopify/Location/FGID', 'Foreign', store=other)
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/FGID',
                self.location_a.id,
            )

    def test_an_inactive_gid_is_refused(self):
        self._cache('gid://shopify/Location/IN1', 'Retired', active=False)
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/IN1',
                self.location_a.id,
            )

    def test_a_duplicate_shopify_identity_is_refused(self):
        self._cache('gid://shopify/Location/DUP', 'Duplicate probe')
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/DUP', self.location_a.id,
        )
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/DUP',
                self.location_b.id,
            )

    def test_a_duplicate_odoo_identity_is_refused(self):
        self._cache('gid://shopify/Location/DO1', 'One')
        self._cache('gid://shopify/Location/DO2', 'Two')
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/DO1', self.location_a.id,
        )
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/DO2',
                self.location_a.id,
            )

    def test_a_non_internal_odoo_location_is_refused(self):
        customer = self.env['stock.location'].search(
            [('usage', '=', 'customer')], limit=1,
        )
        if not customer:
            self.skipTest('No customer-usage location in this build.')
        self._cache('gid://shopify/Location/NI1', 'Non-internal probe')
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/NI1', customer.id,
            )

    def test_a_cross_company_odoo_location_is_refused(self):
        foreign = self.env['stock.location'].sudo().create({
            'name': 'Cross Company Location',
            'usage': 'internal',
            'company_id': self.company_b.id,
        })
        self._cache('gid://shopify/Location/CC1', 'Cross-company probe')
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/CC1', foreign.id,
            )

    def test_a_nonexistent_odoo_location_is_refused(self):
        self._cache('gid://shopify/Location/GH1', 'Ghost probe')
        with self.assertRaises(UserError):
            self._as().save_location_mapping(
                self.store.id, 'gid://shopify/Location/GH1',
                self.location_b.id + 10 ** 6,
            )

    def test_no_mapping_is_ever_inferred_from_a_matching_name(self):
        """The Odoo location is called exactly what the Shopify one is called.

        If anything anywhere matched by name, this is where it would show:
        two identically-named records and no explicit pairing. Nothing is
        created, because identity is always explicit.
        """
        twin = self.env['stock.location'].sudo().create({
            'name': 'Name Twin Warehouse',
            'usage': 'internal',
            'location_id': self.warehouse.view_location_id.id,
        })
        self._cache('gid://shopify/Location/TWIN', 'Name Twin Warehouse')
        payload = self._as().get_setup_state(self.store.id)['location_mapping']
        self.assertFalse(payload['locations'][0]['mapped'])
        self.assertFalse(self.Mapping.sudo().search([
            ('store_id', '=', self.store.id),
            ('odoo_location_id', '=', twin.id),
        ]))

    def test_a_protected_field_create_is_still_refused_directly(self):
        """The governed route exists BECAUSE the direct one is refused."""
        with self.assertRaises(AccessError):
            self.Mapping.with_user(self.admin).create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Location/FORGED',
                'odoo_location_id': self.location_a.id,
                'match_key': 'manual',
            })

    # --- authorization on the setup route -------------------------------

    def test_a_foreign_administrator_cannot_map_this_store(self):
        self._cache('gid://shopify/Location/FA1', 'Foreign admin probe')
        self._assert_refused(
            lambda: self._as(self.admin_b).save_location_mapping(
                self.store.id, 'gid://shopify/Location/FA1',
                self.location_a.id,
            )
        )

    def test_the_setup_refresh_reaches_the_private_setup_guard(self):
        calls = []
        original = type(self.Service)._setup_refresh_shopify_locations

        def spy(self_, store_id):
            calls.append(store_id)
            return original(self_, store_id)

        with patch.object(
            type(self.Service), '_setup_refresh_shopify_locations', spy,
        ):
            with self._fail_on_contact():
                self._as().refresh_shopify_locations(self.store.id)
        self.assertEqual(calls, [self.store.id])
        job = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'inventory_location_sync'),
        ])
        self.assertEqual(len(job), 1)
        self.assertEqual(job.state, 'queued')

    def test_continue_requires_a_current_refresh_and_every_mapping(self):
        self._cache('gid://shopify/Location/C1', 'Continue One')
        self._cache('gid://shopify/Location/C2', 'Continue Two')
        with self.assertRaises(UserError):
            self._as().acknowledge_location_mapping(self.store.id)

        self._mark_refresh_succeeded()
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/C1', self.location_a.id,
        )
        with self.assertRaises(UserError) as refusal:
            self._as().acknowledge_location_mapping(self.store.id)
        self.assertIn('1 location', str(refusal.exception))

        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/C2', self.location_b.id,
        )
        state = self._as().acknowledge_location_mapping(self.store.id)
        self.assertTrue(state['location_mapping']['mapping_complete'])

    def test_a_mapping_created_in_setup_recomputes_readiness_immediately(self):
        self._cache('gid://shopify/Location/ST1', 'Stale probe')
        self._as().run_readiness(self.store.id)
        before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_readiness_check'),
        ])

        state = self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/ST1', self.location_a.id,
        )

        self.settings.invalidate_recordset()
        after = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_readiness_check'),
        ])
        self.assertEqual(after, before + 1)
        self.assertFalse(self.settings.setup_readiness_stale_since)
        self.assertTrue(state['readiness']['ran'])
        self.assertFalse(state['readiness']['stale'])

    def test_success_followup_reloads_and_recomputes_readiness(self):
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'inventory_location_sync',
            'state': 'queued',
            'payload_hash': 'setup-followup-success',
            'expected_connection_generation':
                self.store.connection_generation,
        })
        job.sudo().write({'state': 'running'})
        self._cache('gid://shopify/Location/FOLLOW', 'Follow-up Warehouse')
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.settings.sudo()._mark_setup_readiness_stale()
        before = self.env['shopify.connector.job'].sudo().search_count([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'core_readiness_check'),
        ])

        state = self._as().follow_location_refresh(
            self.store.id, job.id,
        )

        self.assertEqual(
            state['location_mapping']['refresh']['state'], 'succeeded',
        )
        self.assertEqual(
            state['location_mapping']['locations'][0]['name'],
            'Follow-up Warehouse',
        )
        self.assertFalse(state['readiness']['stale'])
        self.assertEqual(
            self.env['shopify.connector.job'].sudo().search_count([
                ('store_id', '=', self.store.id),
                ('job_type', '=', 'core_readiness_check'),
            ]),
            before + 1,
        )

    def test_foreign_administrator_cannot_follow_this_stores_refresh(self):
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'inventory_location_sync',
            'state': 'queued',
            'payload_hash': 'foreign-follow-refusal',
            'expected_connection_generation':
                self.store.connection_generation,
        })

        self._assert_refused(
            lambda: self._as(self.admin_b).follow_location_refresh(
                self.store.id, job.id,
            )
        )

    def test_old_generation_location_refresh_blocks_readiness(self):
        self.store.sudo().write({
            'granted_scopes': json.dumps(['write_inventory']),
        })
        self._cache('gid://shopify/Location/OLDGEN', 'Old generation')
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/OLDGEN', self.location_a.id,
        )
        job = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'inventory_location_sync',
            'state': 'queued',
            'payload_hash': 'old-generation-success',
            'expected_connection_generation':
                self.store.connection_generation,
        })
        job.sudo().write({'state': 'running'})
        job.sudo().write({
            'state': 'succeeded', 'finished_at': fields.Datetime.now(),
        })
        self.store.sudo().write({'connection_generation': 1})

        state = self._as().run_readiness(self.store.id)
        check = next(
            row for row in state['readiness']['checks']
            if row['code'] == 'mapped_location'
        )

        self.assertEqual(
            state['location_mapping']['refresh']['state'], 'stale',
        )
        self.assertEqual(check['state'], 'blocking')
        self.assertIn('connection', check['reason'].lower())

    def test_activation_admits_fresh_location_proof_after_generation_change(self):
        """The setup must not strand itself on its pre-connect evidence."""
        old = self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'setup_readiness_check',
            'job_type': 'inventory_location_sync',
            'state': 'queued',
            'payload_hash': 'pre-activation-location-proof',
            'expected_connection_generation': 0,
        })
        self.store.sudo().write({
            'state': 'connected', 'connection_generation': 1,
        })

        with patch.object(
            type(self.Service), '_trigger_dispatch_after_location_refresh',
            lambda _service: True,
        ):
            self._as()._activation_post_transition(
                self.store, self.settings,
            )

        jobs = self.env['shopify.connector.job'].sudo().search([
            ('store_id', '=', self.store.id),
            ('job_type', '=', 'inventory_location_sync'),
        ], order='id asc')
        self.assertEqual(len(jobs), 2)
        self.assertEqual(jobs[0], old)
        self.assertEqual(jobs[1].expected_connection_generation, 1)
        self.assertEqual(jobs[1].job_source, 'manual_sync')
        status = self._as()._activation_requirement_status(
            self.store, self.settings,
        )
        self.assertEqual(status['state'], 'pending')
        self.assertEqual(status['job_id'], jobs[1].id)

    def test_activation_requirement_needs_current_refresh_and_complete_mapping(self):
        self.store.sudo().write({
            'state': 'connected', 'connection_generation': 1,
        })
        stale = self._mark_refresh_succeeded()
        stale.sudo().write({'expected_connection_generation': 0})
        status = self._as()._activation_requirement_status(
            self.store, self.settings,
        )
        self.assertEqual(status['state'], 'action_required')

        current = self._mark_refresh_succeeded()
        self._cache('gid://shopify/Location/ACTIVATION', 'Activation proof')
        status = self._as()._activation_requirement_status(
            self.store, self.settings,
        )
        self.assertEqual(current.expected_connection_generation, 1)
        self.assertEqual(status['state'], 'action_required')

        self._as().save_location_mapping(
            self.store.id,
            'gid://shopify/Location/ACTIVATION',
            self.location_a.id,
        )
        status = self._as()._activation_requirement_status(
            self.store, self.settings,
        )
        self.assertEqual(status['state'], 'ready')

    def test_readiness_requires_a_mapping_while_inventory_is_enabled(self):
        state = self._as().run_readiness(self.store.id)
        checks = {c['code']: c for c in state['readiness']['checks']}
        self.assertEqual(checks['mapped_location']['state'], 'blocking')
        self.assertEqual(
            checks['mapped_location']['action_step_key'], 'location_mapping',
        )
        self._cache('gid://shopify/Location/RD1', 'Readiness probe')
        self._cache('gid://shopify/Location/RD2', 'Readiness probe two')
        self._mark_refresh_succeeded()
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/RD1', self.location_a.id,
        )
        state = self._as().run_readiness(self.store.id)
        checks = {c['code']: c for c in state['readiness']['checks']}
        self.assertEqual(checks['mapped_location']['state'], 'blocking')
        self.assertEqual(
            checks['mapped_location']['reason'],
            '1 active Shopify location(s) still need an explicit Odoo '
            'location mapping.',
        )

        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/RD2', self.location_b.id,
        )
        state = self._as().run_readiness(self.store.id)
        checks = {c['code']: c for c in state['readiness']['checks']}
        # Still not a pass: `write_inventory` is not in the granted scopes
        # snapshot, which is a different essential requirement -- but it is no
        # longer the missing-mapping one, and it is never a green result for
        # something unproven.
        self.assertNotEqual(checks['mapped_location']['tone'], 'success')


@tagged('post_install', '-at_install')
class TestSetupLocationSearch(TestSetupLocationStep):
    """Wave 5: the mapping step's bounded server-side search.

    The step's lists are bounded pages, and that stays true. What these prove
    is the REACHABILITY contract: every eligible cached Shopify location and
    every eligible internal Odoo location is findable through the search RPC,
    paged, with the store and company filters structural on every page --
    including rows far past the first page's cut.
    """

    def _search(self, side, query='', offset=0, user=None,
                continuation=_UNSET):
        """One page, carrying the continuation the server itself issued.

        Batch 1 correction: a page request past the first is bound to the query
        it continues, so a caller that does not present the matching token is
        refused. Tests that page therefore have to page the way the client does,
        which is the point -- a helper that could skip the token would be testing
        a contract nothing enforces.
        """
        if continuation is _UNSET:
            continuation = (
                self._as(user)._setup_search_continuation(
                    self.store, side, (query or '').strip(),
                ) if offset else None
            )
        return self._as(user).search_location_options(
            self.store.id, side, query=query, offset=offset,
            continuation=continuation,
        )

    # --- the shopify side ------------------------------------------------

    def test_a_location_beyond_the_first_page_is_reachable(self):
        """The TD-gap itself: with more cached locations than the payload's
        first page, a named search finds the row the page cut off."""
        from odoo.addons.shopify_connector_inventory.models.\
            shopify_connector_inventory_setup import (
                SETUP_LOCATION_LIST_LIMIT,
            )
        total = SETUP_LOCATION_LIST_LIMIT + 30
        for index in range(total):
            self._cache(
                'gid://shopify/Location/SEARCH%04d' % index,
                'Search Depot %04d' % index,
            )
        payload = self._as().get_setup_state(store_id=self.store.id)
        listing = payload['location_mapping']
        self.assertTrue(listing['truncated'])
        self.assertEqual(listing['shopify_total'], total)
        self.assertEqual(
            len(listing['locations']), SETUP_LOCATION_LIST_LIMIT,
        )
        # The very last row alphabetically is past the first page --
        # unreachable by scrolling, reachable by search.
        page = self._search('shopify', query='Depot %04d' % (total - 1))
        self.assertEqual(page['total'], 1)
        self.assertEqual(
            page['items'][0]['name'], 'Search Depot %04d' % (total - 1),
        )

    def test_search_pages_through_the_full_eligible_set(self):
        from odoo.addons.shopify_connector_inventory.models.\
            shopify_connector_inventory_setup import (
                SETUP_LOCATION_SEARCH_PAGE,
            )
        total = SETUP_LOCATION_SEARCH_PAGE + 5
        for index in range(total):
            self._cache(
                'gid://shopify/Location/PAGE%04d' % index,
                'Paged Depot %04d' % index,
            )
        first = self._search('shopify', query='Paged Depot')
        self.assertEqual(first['total'], total)
        self.assertEqual(len(first['items']), SETUP_LOCATION_SEARCH_PAGE)
        second = self._search(
            'shopify', query='Paged Depot', offset=SETUP_LOCATION_SEARCH_PAGE,
        )
        self.assertEqual(len(second['items']), 5)
        seen = {item['shopify_gid'] for item in first['items']}
        seen |= {item['shopify_gid'] for item in second['items']}
        self.assertEqual(len(seen), total)

    def test_search_carries_the_mapping_state(self):
        self._cache('gid://shopify/Location/SM1', 'Searchable Mapped')
        self._cache('gid://shopify/Location/SM2', 'Searchable Unmapped')
        self.Service.with_user(self.admin).create_or_update_location_mapping(
            self.store, self.location_a, 'gid://shopify/Location/SM1',
        )
        page = self._search('shopify', query='Searchable')
        by_name = {item['name']: item for item in page['items']}
        self.assertTrue(by_name['Searchable Mapped']['mapped'])
        self.assertEqual(
            by_name['Searchable Mapped']['odoo_location_id'],
            self.location_a.id,
        )
        self.assertFalse(by_name['Searchable Unmapped']['mapped'])

    def test_an_inactive_location_is_not_searchable(self):
        self._cache('gid://shopify/Location/SIN1', 'Searchable Gone',
                    active=False)
        page = self._search('shopify', query='Searchable Gone')
        self.assertEqual(page['total'], 0)

    def test_a_foreign_store_location_is_never_found(self):
        foreign_store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Foreign Search Store',
            'shop_domain': 'foreign-search-store.myshopify.com',
            'api_version': '2026-07',
            'company_id': self.env.company.id,
        })
        self._cache('gid://shopify/Location/SF1', 'Foreign Searchable',
                    store=foreign_store)
        page = self._search('shopify', query='Foreign Searchable')
        self.assertEqual(page['total'], 0)
        self.assertEqual(page['items'], [])

    # --- the odoo side ---------------------------------------------------

    def test_odoo_search_finds_internal_locations_by_name(self):
        page = self._search('odoo', query='Setup Step Location A')
        names = [item['name'] for item in page['items']]
        self.assertTrue(
            any('Setup Step Location A' in name for name in names),
        )
        self.assertTrue(page['total'] >= 1)

    def test_odoo_search_excludes_non_internal_locations(self):
        customer_location = self.env['stock.location'].search(
            [('usage', '=', 'customer')], limit=1,
        )
        if not customer_location:
            self.skipTest('no customer location in this database')
        page = self._search('odoo', query=customer_location.name)
        self.assertNotIn(
            customer_location.id, [item['id'] for item in page['items']],
        )

    def test_odoo_search_excludes_a_foreign_company_location(self):
        foreign = self.env['stock.location'].sudo().create({
            'name': 'Foreign Company Searchable Location',
            'usage': 'internal',
            'company_id': self.company_b.id,
        })
        page = self._search('odoo', query='Foreign Company Searchable')
        self.assertNotIn(foreign.id, [item['id'] for item in page['items']])

    # --- authorization and shape -----------------------------------------

    def test_search_requires_the_setup_authority(self):
        operator = self._user('setup_loc_search_operator', 'operator')
        self._assert_refused(
            lambda: self._search('shopify', query='x', user=operator),
        )

    def test_an_unknown_side_is_refused(self):
        with self.assertRaises(UserError):
            self._as().search_location_options(
                self.store.id, 'everything', query='',
            )

    def test_search_makes_no_shopify_contact(self):
        self._cache('gid://shopify/Location/SNC1', 'No Contact Depot')
        with self._fail_on_contact():
            self._search('shopify', query='No Contact')
            self._search('odoo', query='Location A')

    def test_a_malformed_offset_is_refused_not_clamped(self):
        """Batch 1 correction: fail CLOSED on a position we did not issue.

        This used to clamp a malformed offset to 0 and return the first page,
        which reads as forgiving and is the opposite. The client sends an offset
        only when it is CONTINUING a set, and the reply is APPENDED to what is
        already on screen -- so a silent restart at row 0 duplicates every
        visible row and never reaches the page the operator asked for.
        """
        for bad in ('not-a-number', -1, 10 ** 9, 3.5, True, None, [0]):
            with self.assertRaises(
                UserError,
                msg='offset %r was accepted' % (bad,),
            ):
                self._as().search_location_options(
                    self.store.id, 'shopify', query='', offset=bad,
                    continuation=None,
                )

    def test_a_continuation_does_not_carry_between_queries(self):
        """Paging position must not leak from one result set into another.

        Search A, page into it, then search B and press Load more: with a bare
        offset the server would serve rows 50-100 of B while the client believed
        it held rows 0-50 of B, so 50 locations are silently unreachable and the
        list's whole promise is broken.
        """
        for index in range(60):
            self._cache(
                'gid://shopify/Location/CONT%03d' % index,
                'Continuation Depot %03d' % index,
            )
        first = self._search('shopify', query='Continuation')
        self.assertTrue(first['next_offset'])
        self.assertTrue(first['continuation'])
        # The same query continues fine.
        second = self._as().search_location_options(
            self.store.id, 'shopify', query='Continuation',
            offset=first['next_offset'], continuation=first['continuation'],
        )
        self.assertTrue(second['items'])
        # A DIFFERENT query with the old token is refused.
        with self.assertRaises(UserError):
            self._as().search_location_options(
                self.store.id, 'shopify', query='Something Else',
                offset=first['next_offset'],
                continuation=first['continuation'],
            )
        # So is the other side with the same token.
        with self.assertRaises(UserError):
            self._as().search_location_options(
                self.store.id, 'odoo', query='Continuation',
                offset=first['next_offset'],
                continuation=first['continuation'],
            )
        # And so is a missing one.
        with self.assertRaises(UserError):
            self._as().search_location_options(
                self.store.id, 'shopify', query='Continuation',
                offset=first['next_offset'], continuation=None,
            )

    def test_paging_covers_every_row_exactly_once(self):
        """No skipped rows, no duplicates, across the whole eligible set."""
        names = set()
        for index in range(130):
            name = 'Coverage Depot %03d' % index
            names.add(name)
            self._cache('gid://shopify/Location/COV%03d' % index, name)
        seen, offset, continuation, pages = [], 0, None, 0
        while True:
            page = self._as().search_location_options(
                self.store.id, 'shopify', query='Coverage Depot',
                offset=offset, continuation=continuation,
            )
            seen.extend(row['name'] for row in page['items'])
            pages += 1
            self.assertLess(pages, 20, 'the pager did not terminate')
            if not page['next_offset']:
                break
            offset, continuation = page['next_offset'], page['continuation']
        self.assertEqual(
            len(seen), len(set(seen)),
            'a location was served on two different pages',
        )
        self.assertEqual(
            set(seen), names,
            'paging did not reach every eligible location exactly once',
        )

    def test_the_empty_states_are_distinguishable(self):
        """Four different reasons for an empty list, four different answers."""
        self._cache('gid://shopify/Location/EMPTY1', 'Empty State Depot')
        no_match = self._search('shopify', query='zzz-nothing-matches-zzz')
        self.assertEqual(no_match['items'], [])
        self.assertEqual(no_match['empty_reason'], 'no_results')
        # A store with nothing cached at all is a different statement.
        other = self.env['shopify.connector.store'].sudo().create({
            'name': 'Empty Cache Store',
            'shop_domain': 'empty-cache-store.myshopify.com',
            'api_version': self.store.api_version,
            'company_id': self.store.company_id.id,
        })
        empty = self._as().search_location_options(other.id, 'shopify')
        self.assertEqual(empty['empty_reason'], 'no_cached_locations')
