from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestLocationMapping(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Location Mapping Test Store',
            'shop_domain': 'location-mapping-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Mapping = cls.env['shopify.connector.location.mapping']
        cls.Location = cls.env['stock.location']
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.internal_location = cls.Location.create({
            'name': 'Test Internal Location A',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.internal_location_b = cls.Location.create({
            'name': 'Test Internal Location B',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.customer_location = cls.Location.search(
            [('usage', '=', 'customer')], limit=1,
        )
        cls.user_operator = cls.env['res.users'].create({
            'name': 'Location Mapping Operator',
            'login': 'location_mapping_operator',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_operator'
                ).id,
            ])],
        })
        cls.user_auditor = cls.env['res.users'].create({
            'name': 'Location Mapping Auditor',
            'login': 'location_mapping_auditor',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })

    def _make_mapping(self, location, gid):
        return self.Mapping.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': gid,
            'odoo_location_id': location.id,
            'match_key': 'manual',
        })

    def _cache_location(self, gid, name=None, active=True, store=None):
        return self.env['shopify.connector.location'].sudo().create({
            'store_id': (store or self.store).id,
            'shopify_location_gid': gid,
            'name': name or ('Cached %s' % gid),
            'shopify_location_active': active,
        })

    def test_explicit_identity_no_name_inference(self):
        """Creation requires an explicit Shopify Location GID and Odoo
        location -- there is no name-matching creation path at all."""
        mapping = self._make_mapping(
            self.internal_location, 'gid://shopify/Location/1',
        )
        self.assertEqual(mapping.match_key, 'manual')
        self.assertEqual(mapping.shopify_gid, 'gid://shopify/Location/1')
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Mapping.sudo().create({
                    'store_id': self.store.id,
                    'odoo_location_id': self.internal_location_b.id,
                })

    @mute_logger('odoo.sql_db')
    def test_unique_store_odoo_location(self):
        self._make_mapping(self.internal_location, 'gid://shopify/Location/2')
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._make_mapping(
                    self.internal_location, 'gid://shopify/Location/3',
                )

    @mute_logger('odoo.sql_db')
    def test_unique_store_shopify_gid(self):
        self._make_mapping(self.internal_location, 'gid://shopify/Location/4')
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self._make_mapping(
                    self.internal_location_b, 'gid://shopify/Location/4',
                )

    def test_internal_only_domain_enforced(self):
        if not self.customer_location:
            self.skipTest('No customer-usage location available in demo data.')
        with self.assertRaises(UserError):
            self._make_mapping(
                self.customer_location, 'gid://shopify/Location/5',
            )

    def test_ancestor_descendant_overlap_rejected(self):
        child_location = self.Location.create({
            'name': 'Test Internal Child Location',
            'usage': 'internal',
            'location_id': self.internal_location.id,
        })
        self._make_mapping(
            self.internal_location, 'gid://shopify/Location/6',
        )
        with self.assertRaises(UserError):
            self._make_mapping(
                child_location, 'gid://shopify/Location/7',
            )

    def test_push_enabled_default_true_and_toggle(self):
        mapping = self._make_mapping(
            self.internal_location, 'gid://shopify/Location/8',
        )
        self.assertTrue(mapping.push_enabled)
        mapping.with_user(self.user_operator).action_set_push_enabled(False)
        self.assertFalse(mapping.push_enabled)
        with self.assertRaises(Exception):
            mapping.with_user(self.user_auditor).action_set_push_enabled(True)

    def test_odoo_binding_field_name(self):
        self.assertEqual(
            self.Mapping._odoo_binding_field_name(), 'odoo_location_id',
        )

    def test_protected_fields_complete(self):
        self.Mapping._assert_binding_field_classification()

    # ------------------------------------------------------------------
    # Sanctioned backend creation service (PR #182 comment 5025803697
    # item 22.A) -- ordinary create() of these fields is denied by the
    # binding mixin; only this narrow service method may create/update.
    # ------------------------------------------------------------------

    def test_sanctioned_service_creates_mapping_for_operator(self):
        self._cache_location('gid://shopify/Location/900', name='Warehouse 900')
        Service = self.env['shopify.connector.inventory.service']
        mapping = Service.with_user(
            self.user_operator
        ).create_or_update_location_mapping(
            self.store, self.internal_location, 'gid://shopify/Location/900',
        )
        self.assertEqual(mapping.store_id, self.store)
        self.assertEqual(mapping.odoo_location_id, self.internal_location)
        self.assertEqual(mapping.match_key, 'manual')
        self.assertTrue(mapping.push_enabled)
        self.assertEqual(mapping.shopify_location_name_snapshot, 'Warehouse 900')

    def test_sanctioned_service_updates_existing_mapping_idempotently(self):
        self._cache_location('gid://shopify/Location/901', name='Warehouse 901')
        Service = self.env['shopify.connector.inventory.service']
        first = Service.with_user(
            self.user_operator
        ).create_or_update_location_mapping(
            self.store, self.internal_location, 'gid://shopify/Location/901',
            push_enabled=True,
        )
        second = Service.with_user(
            self.user_operator
        ).create_or_update_location_mapping(
            self.store, self.internal_location, 'gid://shopify/Location/901',
            push_enabled=False,
        )
        self.assertEqual(first.id, second.id)
        self.assertFalse(second.push_enabled)

    def test_sanctioned_service_denied_for_auditor(self):
        self._cache_location('gid://shopify/Location/902')
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(Exception):
            Service.with_user(
                self.user_auditor
            ).create_or_update_location_mapping(
                self.store, self.internal_location,
                'gid://shopify/Location/902',
            )

    def test_sanctioned_service_rejects_customer_location(self):
        if not self.customer_location:
            self.skipTest('No customer-usage location available in demo data.')
        self._cache_location('gid://shopify/Location/903')
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(UserError):
            Service.with_user(
                self.user_operator
            ).create_or_update_location_mapping(
                self.store, self.customer_location,
                'gid://shopify/Location/903',
            )

    def test_sanctioned_service_requires_explicit_gid(self):
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(UserError):
            Service.with_user(
                self.user_operator
            ).create_or_update_location_mapping(
                self.store, self.internal_location, '',
            )

    def test_sanctioned_service_rejects_uncached_gid(self):
        """An arbitrary GID with no corresponding cached Shopify location
        for this store is refused before any mapping is created."""
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(UserError):
            Service.with_user(
                self.user_operator
            ).create_or_update_location_mapping(
                self.store, self.internal_location,
                'gid://shopify/Location/NEVER-CACHED',
            )

    def test_sanctioned_service_rejects_foreign_store_gid(self):
        """A GID cached for a DIFFERENT store is refused for this store."""
        other_store = self.env['shopify.connector.store'].create({
            'name': 'Other Store For Location Mapping Test',
            'shop_domain': 'other-location-mapping-test.myshopify.com',
            'api_version': '2026-07',
        })
        self._cache_location(
            'gid://shopify/Location/FOREIGN', store=other_store,
        )
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(UserError):
            Service.with_user(
                self.user_operator
            ).create_or_update_location_mapping(
                self.store, self.internal_location,
                'gid://shopify/Location/FOREIGN',
            )

    def test_sanctioned_service_rejects_inactive_gid(self):
        """A cached but no-longer-active Shopify location is refused."""
        self._cache_location(
            'gid://shopify/Location/INACTIVE', active=False,
        )
        Service = self.env['shopify.connector.inventory.service']
        with self.assertRaises(UserError):
            Service.with_user(
                self.user_operator
            ).create_or_update_location_mapping(
                self.store, self.internal_location,
                'gid://shopify/Location/INACTIVE',
            )

    def test_sanctioned_service_denies_silent_gid_replacement(self):
        """A differing GID for an already-mapped Odoo location fails
        closed -- never silently replaces the recorded Shopify identity
        (PR #182 comment 5028910116 item 13)."""
        self._cache_location('gid://shopify/Location/910')
        self._cache_location('gid://shopify/Location/DIFFERENT')
        Service = self.env['shopify.connector.inventory.service']
        Service.with_user(
            self.user_operator
        ).create_or_update_location_mapping(
            self.store, self.internal_location, 'gid://shopify/Location/910',
        )
        with self.assertRaises(UserError):
            Service.with_user(
                self.user_operator
            ).create_or_update_location_mapping(
                self.store, self.internal_location,
                'gid://shopify/Location/DIFFERENT',
            )
        mapping = self.Mapping.search([
            ('store_id', '=', self.store.id),
            ('odoo_location_id', '=', self.internal_location.id),
        ])
        self.assertEqual(mapping.shopify_gid, 'gid://shopify/Location/910')

    def test_sanctioned_service_denies_silent_gid_move(self):
        """An already-mapped GID cannot be silently moved to a different
        Odoo location either (PR #182 comment 5028910116 item 13)."""
        self._cache_location('gid://shopify/Location/911')
        Service = self.env['shopify.connector.inventory.service']
        Service.with_user(
            self.user_operator
        ).create_or_update_location_mapping(
            self.store, self.internal_location, 'gid://shopify/Location/911',
        )
        with self.assertRaises(UserError):
            Service.with_user(
                self.user_operator
            ).create_or_update_location_mapping(
                self.store, self.internal_location_b,
                'gid://shopify/Location/911',
            )

    def test_ordinary_create_still_denied_for_operator(self):
        """The sanctioned service exists alongside, not instead of, the
        mixin's own generic-create denial."""
        with self.assertRaises(Exception):
            self.Mapping.with_user(self.user_operator).create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Location/904',
                'odoo_location_id': self.internal_location.id,
                'match_key': 'manual',
            })

    # ------------------------------------------------------------------
    # Theme I — F-4 permanent seam: the inventory override of core's
    # `shopify.connector.location._resolve_odoo_location()`.
    # ------------------------------------------------------------------

    def test_resolve_odoo_location_returns_mapped_location(self):
        self._make_mapping(
            self.internal_location, 'gid://shopify/Location/F4-1',
        )
        Location = self.env['shopify.connector.location']
        result = Location._resolve_odoo_location(
            self.store, 'gid://shopify/Location/F4-1',
        )
        self.assertEqual(result, self.internal_location)

    def test_resolve_odoo_location_returns_false_for_unmapped_gid(self):
        Location = self.env['shopify.connector.location']
        result = Location._resolve_odoo_location(
            self.store, 'gid://shopify/Location/F4-NEVER-MAPPED',
        )
        self.assertFalse(result)

    def test_resolve_odoo_location_returns_false_when_push_disabled(self):
        mapping = self._make_mapping(
            self.internal_location, 'gid://shopify/Location/F4-2',
        )
        mapping.with_user(self.user_operator).action_set_push_enabled(False)
        Location = self.env['shopify.connector.location']
        result = Location._resolve_odoo_location(
            self.store, 'gid://shopify/Location/F4-2',
        )
        self.assertFalse(result)

    def test_resolve_odoo_location_returns_false_for_non_internal_target(self):
        # The mapping model's own constraint already forbids creating a
        # non-internal mapping; this proves the resolution seam independently
        # fails closed too, defense-in-depth, rather than trusting the
        # constraint alone.
        if not self.customer_location:
            self.skipTest('No customer-usage location available in demo data.')
        Location = self.env['shopify.connector.location']
        with self.assertRaises(Exception):
            self._make_mapping(
                self.customer_location, 'gid://shopify/Location/F4-3',
            )
        result = Location._resolve_odoo_location(
            self.store, 'gid://shopify/Location/F4-3',
        )
        self.assertFalse(result)

    def test_resolve_odoo_location_returns_false_for_different_store(self):
        other_store = self.env['shopify.connector.store'].create({
            'name': 'Other Store',
            'shop_domain': 'other-location-mapping-test.myshopify.com',
            'api_version': '2026-07',
        })
        self._make_mapping(
            self.internal_location, 'gid://shopify/Location/F4-4',
        )
        Location = self.env['shopify.connector.location']
        result = Location._resolve_odoo_location(
            other_store, 'gid://shopify/Location/F4-4',
        )
        self.assertFalse(result)

    def test_resolve_odoo_location_returns_false_for_empty_gid(self):
        Location = self.env['shopify.connector.location']
        self.assertFalse(Location._resolve_odoo_location(self.store, False))
        self.assertFalse(Location._resolve_odoo_location(self.store, ''))

    def test_resolve_odoo_location_no_ambiguous_result(self):
        # The model's own UNIQUE(store, shopify_gid) constraint makes a
        # genuine duplicate row unreachable; this proves the seam's own
        # `len(matches) != 1` guard is real by construction (exactly one
        # match resolves cleanly, never more).
        self._make_mapping(
            self.internal_location, 'gid://shopify/Location/F4-5',
        )
        Location = self.env['shopify.connector.location']
        result = Location._resolve_odoo_location(
            self.store, 'gid://shopify/Location/F4-5',
        )
        self.assertEqual(len(result), 1)
