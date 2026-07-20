from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestInventoryLevelBinding(TransactionCase):

    EXPECTED_PROTECTED_FIELDS = frozenset((
        'store_id',
        'shopify_gid',
        'status',
        'match_key',
        'matched_by_uid',
        'matched_at',
        'override_uid',
        'override_at',
        'override_previous_candidate',
        'product_variant_binding_id',
        'location_mapping_id',
        'shopify_inventory_item_gid',
        'last_pushed_available',
        'last_pushed_at',
        'last_known_shopify_available',
        'pending_target_available',
        'first_push_state',
        'first_push_preview_qty',
        'first_push_confirmed_at',
        'first_push_confirmed_by_uid',
    ))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Inventory Level Binding Test Store',
            'shop_domain': 'inventory-level-binding-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Binding = cls.env['shopify.connector.inventory.level.binding']
        cls.Mapping = cls.env['shopify.connector.location.mapping']
        cls.warehouse = cls.env['stock.warehouse'].search(
            [('company_id', '=', cls.env.company.id)], limit=1,
        )
        cls.location = cls.env['stock.location'].create({
            'name': 'Inventory Binding Test Location',
            'usage': 'internal',
            'location_id': cls.warehouse.view_location_id.id,
        })
        cls.mapping = cls.Mapping.sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Location/100',
            'odoo_location_id': cls.location.id,
            'match_key': 'manual',
        })
        cls.template = cls.env['product.template'].create({
            'name': 'Inventory Binding Test Product',
        })
        cls.template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Product/100',
            'product_template_id': cls.template.id,
        })
        cls.variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/100',
            'product_variant_id': cls.template.product_variant_id.id,
            'product_template_binding_id': cls.template_binding.id,
        })
        cls.user_reviewer = cls.env['res.users'].create({
            'name': 'Inventory Binding Reviewer',
            'login': 'inventory_binding_reviewer',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_reviewer'
                ).id,
            ])],
        })
        cls.user_operator = cls.env['res.users'].create({
            'name': 'Inventory Binding Operator',
            'login': 'inventory_binding_operator',
            'group_ids': [(6, 0, [
                cls.env.ref(
                    'shopify_connector_core.group_shopify_connector_operator'
                ).id,
            ])],
        })

    def _make_binding(self, item_gid='gid://shopify/InventoryItem/100'):
        return self.Binding.sudo().create({
            'store_id': self.store.id,
            'product_variant_binding_id': self.variant_binding.id,
            'location_mapping_id': self.mapping.id,
            'shopify_inventory_item_gid': item_gid,
        })

    def test_required_fields(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Binding.sudo().create({
                    'store_id': self.store.id,
                    'location_mapping_id': self.mapping.id,
                })

    def test_shopify_gid_not_required_at_creation(self):
        binding = self._make_binding()
        self.assertFalse(binding.shopify_gid)

    @mute_logger('odoo.sql_db')
    def test_unique_item_location_ra019_identity(self):
        self._make_binding('gid://shopify/InventoryItem/101')
        other_template = self.env['product.template'].create({
            'name': 'Other RA-019 Product',
        })
        other_template_binding = self.env[
            'shopify.connector.product.template.binding'
        ].create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/101',
            'product_template_id': other_template.id,
        })
        other_variant_binding = self.env[
            'shopify.connector.product.variant.binding'
        ].create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/101',
            'product_variant_id': other_template.product_variant_id.id,
            'product_template_binding_id': other_template_binding.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Binding.sudo().create({
                    'store_id': self.store.id,
                    'product_variant_binding_id': other_variant_binding.id,
                    'location_mapping_id': self.mapping.id,
                    'shopify_inventory_item_gid':
                        'gid://shopify/InventoryItem/101',
                })

    @mute_logger('odoo.sql_db')
    def test_unique_variant_location(self):
        self._make_binding('gid://shopify/InventoryItem/102')
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.Binding.sudo().create({
                    'store_id': self.store.id,
                    'product_variant_binding_id': self.variant_binding.id,
                    'location_mapping_id': self.mapping.id,
                    'shopify_inventory_item_gid':
                        'gid://shopify/InventoryItem/103',
                })

    def test_first_push_default_state(self):
        binding = self._make_binding('gid://shopify/InventoryItem/104')
        self.assertEqual(binding.first_push_state, 'pending')
        self.assertFalse(binding.first_push_confirmed_at)
        self.assertFalse(binding.first_push_confirmed_by_uid)

    def test_confirm_requires_preview_first(self):
        binding = self._make_binding('gid://shopify/InventoryItem/105')
        with self.assertRaises(Exception):
            binding.with_user(self.user_reviewer).action_confirm_first_push()

    def test_confirm_permission_and_record(self):
        binding = self._make_binding('gid://shopify/InventoryItem/106')
        binding.sudo().write({
            'first_push_state': 'previewed',
            'first_push_preview_qty': 12.0,
        })
        with self.assertRaises(Exception):
            binding.with_user(self.user_operator).action_confirm_first_push()
        binding.with_user(self.user_reviewer).action_confirm_first_push()
        self.assertEqual(binding.first_push_state, 'confirmed')
        self.assertEqual(
            binding.first_push_confirmed_by_uid, self.user_reviewer,
        )
        self.assertTrue(binding.first_push_confirmed_at)

    def test_odoo_binding_field_name_non_overridable(self):
        self.assertFalse(self.Binding._odoo_binding_field_name())

    def test_no_binding_owned_idempotency_fields(self):
        stored_fields = set(self.Binding._fields)
        self.assertNotIn('last_push_idempotency_key', stored_fields)
        self.assertNotIn('last_push_params_hash', stored_fields)

    def test_exact_stored_field_classification(self):
        self.assertEqual(
            self.Binding._protected_binding_fields(),
            self.EXPECTED_PROTECTED_FIELDS,
        )
        automatic = frozenset((
            'id', 'display_name', 'create_uid', 'create_date',
            'write_uid', 'write_date',
        ))
        stored_fields = {
            name for name, field in self.Binding._fields.items()
            if field.store and name not in automatic
        }
        self.assertEqual(stored_fields, self.EXPECTED_PROTECTED_FIELDS)

    def test_protected_fields_cannot_be_written_generically(self):
        binding = self._make_binding('gid://shopify/InventoryItem/107')
        with self.assertRaises(Exception):
            binding.with_user(self.user_reviewer).write({
                'last_pushed_available': 999.0,
            })
