from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


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
