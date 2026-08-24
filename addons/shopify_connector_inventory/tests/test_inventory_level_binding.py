from odoo.exceptions import AccessError, UserError
from odoo.tests.common import TransactionCase, tagged
from odoo.tools import mute_logger


# Runs post_install: the cross-company tests create a fresh res.company,
# whose required Odoo-19 base field res.company.inventory_period is
# contributed by a module that sorts after shopify_connector_inventory in
# the install graph. At at_install time that field is not yet on the model
# (create-without hits the NOT NULL column; create-with is rejected as an
# unknown field); post_install guarantees the complete registry so the
# field and its default are available. Every other test in this class is
# timing-agnostic and passes identically under post_install.
@tagged('post_install', '-at_install')
class TestInventoryLevelBinding(TransactionCase):

    EXPECTED_PROTECTED_FIELDS = frozenset((
        # SEC-3 (#197): the store-derived company. Protected, not caller input
        # -- a binding's company is whatever its store's company is.
        'company_id',
        # SEC-3 (#197): set only by the upgrade scope sweep and cleared only by
        # the administrative release action. A caller-writable quarantine flag
        # would let exactly the rows it hides unhide themselves.
        'sec3_scope_quarantined',
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
        'first_push_previewed_at',
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
                    'shopify_connector_core.group_shopify_connector_admin'
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

    @mute_logger('odoo.sql_db')
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
        protected_fields = self.Binding._protected_binding_fields()
        automatic = frozenset((
            'id', 'display_name', 'create_uid', 'create_date',
            'write_uid', 'write_date',
        ))
        base_closure = frozenset((
            'shopify_connector_core',
            'shopify_connector_inventory',
        ))
        base_stored_fields = {
            name for name, field in self.Binding._fields.items()
            if field.store
            and name not in automatic
            and base_closure.intersection(field._modules or ())
        }
        # Field._modules is Odoo 19's live provenance for declarations and
        # extensions. This keeps the base assertion exact without naming an
        # optional addon that may extend the concrete model.
        self.assertEqual(
            base_stored_fields, self.EXPECTED_PROTECTED_FIELDS,
        )
        stored_fields = {
            name for name, field in self.Binding._fields.items()
            if field.store and name not in automatic
        }
        self.assertEqual(stored_fields, protected_fields)
        extension_stored_fields = (
            stored_fields - self.EXPECTED_PROTECTED_FIELDS
        )
        self.assertTrue(
            extension_stored_fields <=
            self.Binding._additional_protected_binding_fields()
        )

    def test_protected_fields_cannot_be_written_generically(self):
        binding = self._make_binding('gid://shopify/InventoryItem/107')
        with self.assertRaises(Exception):
            binding.with_user(self.user_reviewer).write({
                'last_pushed_available': 999.0,
            })

    # ------------------------------------------------------------------
    # SEC-1 composite-binding company consistency (PR #182 comment
    # 5025803697 item 21)
    # ------------------------------------------------------------------

    def test_company_neutral_records_remain_valid(self):
        # cls.template/cls.location carry no explicit company -- valid.
        binding = self._make_binding('gid://shopify/InventoryItem/108')
        self.assertTrue(binding)

    def test_cross_company_location_rejected(self):
        other_company = self.env['res.company'].create({
            'name': 'Inventory Binding Other Co',
        })
        # A top-level internal location owned by the other company. It must
        # not be parented under this company's warehouse view location, or
        # stock's own _check_company rejects the cross-company parentage
        # before the mapping's own company-consistency guard is reached.
        other_location = self.env['stock.location'].create({
            'name': 'Other Co Location',
            'usage': 'internal',
            'company_id': other_company.id,
        })
        # The location-mapping's _check_location_company_consistency guard is
        # the enforcement point for a cross-company Odoo location: a binding
        # can only ever reference a company-consistent mapping, so mapping a
        # location owned by a different company than the owning store must
        # be rejected outright.
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                self.Mapping.sudo().create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Location/101',
                    'odoo_location_id': other_location.id,
                    'match_key': 'manual',
                })

    def test_cross_company_product_rejected(self):
        other_company = self.env['res.company'].create({
            'name': 'Inventory Binding Other Co 2',
        })
        other_template = self.env['product.template'].create({
            'name': 'Other Co Product', 'company_id': other_company.id,
        })
        # SEC-3 (#197) moved this refusal EARLIER. A store belongs to exactly
        # one company, so a foreign-company product can no longer be bound to
        # this store at all -- the template binding itself is now refused by
        # Odoo's `_check_company`, before an inventory pair could ever be
        # attempted. Assert at the point the refusal now happens; the pair-level
        # guard is still proven by `test_cross_company_location_rejected` and by
        # the SQL-planted historic pairs in test_sec3_company_isolation.py.
        with self.assertRaises(UserError):
            with self.env.cr.savepoint():
                self.env[
                    'shopify.connector.product.template.binding'
                ].create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Product/109',
                    'product_template_id': other_template.id,
                })

    # ------------------------------------------------------------------
    # Sanctioned binding-ensure service (PR #182 comment 5025803697 item
    # 22.B)
    # ------------------------------------------------------------------

    def test_sanctioned_service_creates_binding_for_administrator(self):
        Service = self.env['shopify.connector.inventory.service']
        binding = Service.with_user(
            self.user_reviewer
        ).ensure_inventory_level_binding(
            self.variant_binding, self.mapping,
            'gid://shopify/InventoryItem/111',
        )
        self.assertEqual(
            binding.shopify_inventory_item_gid,
            'gid://shopify/InventoryItem/111',
        )

    def test_sanctioned_service_ensure_is_idempotent(self):
        Service = self.env['shopify.connector.inventory.service']
        first = Service.with_user(
            self.user_reviewer
        ).ensure_inventory_level_binding(
            self.variant_binding, self.mapping,
            'gid://shopify/InventoryItem/112',
        )
        second = Service.with_user(
            self.user_reviewer
        ).ensure_inventory_level_binding(
            self.variant_binding, self.mapping,
            'gid://shopify/InventoryItem/112',
        )
        self.assertEqual(first.id, second.id)

    def test_sanctioned_service_denied_for_operator(self):
        Service = self.env['shopify.connector.inventory.service']
        before = self.Binding.search_count([
            ('store_id', '=', self.store.id),
        ])
        with self.assertRaises(AccessError):
            Service.with_user(self.user_operator).ensure_inventory_level_binding(
                self.variant_binding, self.mapping,
                'gid://shopify/InventoryItem/113',
            )
        self.assertEqual(
            self.Binding.search_count([('store_id', '=', self.store.id)]),
            before,
        )

    def test_sanctioned_service_denied_for_auditor(self):
        auditor = self.env['res.users'].create({
            'name': 'Level Binding Auditor',
            'login': 'level_binding_auditor_only',
            'group_ids': [(6, 0, [
                self.env.ref(
                    'shopify_connector_core.group_shopify_connector_auditor'
                ).id,
            ])],
        })
        Service = self.env['shopify.connector.inventory.service']
        before = self.Binding.search_count([
            ('store_id', '=', self.store.id),
        ])
        with self.assertRaises(AccessError):
            Service.with_user(auditor).ensure_inventory_level_binding(
                self.variant_binding, self.mapping,
                'gid://shopify/InventoryItem/114',
            )
        self.assertEqual(
            self.Binding.search_count([('store_id', '=', self.store.id)]),
            before,
        )
