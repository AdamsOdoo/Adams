"""Wave 5 (D): the guided setup's Location mapping step, end to end.

These run in the INVENTORY module deliberately. Core declares the three seams
and cannot implement them -- it owns no mapping concept and has no mapping
table -- so the only place the seam and its implementation are both present is
here. A core-side test could prove the seam exists; only this can prove it is
wired to the sanctioned service and refuses everything that service refuses.

No Shopify contact anywhere: the transport is replaced with a stand-in that
fails the test if it is reached.
"""

from unittest.mock import patch

from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged


# Issue #193 / #157 -- Odoo 19 test-phase contract; see
# docs/05-qa/odoo19-test-phase-contract.md.
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

    def test_the_setup_refresh_reaches_the_public_guarded_action(self):
        calls = []
        original = type(self.Service).action_refresh_shopify_locations

        def spy(self_, store_id):
            calls.append(store_id)
            return original(self_, store_id)

        with patch.object(
            type(self.Service), 'action_refresh_shopify_locations', spy,
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

    def test_a_mapping_created_in_setup_stales_the_readiness_evidence(self):
        self._cache('gid://shopify/Location/ST1', 'Stale probe')
        self.settings.sudo().write({'setup_readiness_stale_since': False})
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/ST1', self.location_a.id,
        )
        self.settings.invalidate_recordset()
        self.assertTrue(self.settings.setup_readiness_stale_since)

    def test_readiness_requires_a_mapping_while_inventory_is_enabled(self):
        state = self._as().run_readiness(self.store.id)
        checks = {c['code']: c for c in state['readiness']['checks']}
        self.assertEqual(checks['mapped_location']['state'], 'blocking')
        self.assertEqual(
            checks['mapped_location']['action_step_key'], 'location_mapping',
        )
        self._cache('gid://shopify/Location/RD1', 'Readiness probe')
        self._as().save_location_mapping(
            self.store.id, 'gid://shopify/Location/RD1', self.location_a.id,
        )
        state = self._as().run_readiness(self.store.id)
        checks = {c['code']: c for c in state['readiness']['checks']}
        # Still not a pass: `write_inventory` is not in the granted scopes
        # snapshot, which is a different essential requirement -- but it is no
        # longer the missing-mapping one, and it is never a green result for
        # something unproven.
        self.assertNotEqual(checks['mapped_location']['tone'], 'success')
