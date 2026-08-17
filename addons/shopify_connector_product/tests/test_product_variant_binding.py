import ast
import os

from odoo import fields
from odoo.exceptions import AccessError
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
class TestProductVariantBinding(TransactionCase):

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
        'product_variant_id',
        'status',
        'match_key',
        'matched_by_uid',
        'matched_at',
        'override_uid',
        'override_at',
        'override_previous_candidate',
        'product_template_binding_id',
        'shopify_option_values',
        'shopify_price_snapshot',
        'shopify_compare_at_price_snapshot',
        'shopify_sku_snapshot',
        'shopify_barcode_snapshot',
        'shopify_inventory_item_gid',
        'shopify_inventory_tracked',
        'shopify_inventory_tracked_known',
        'shopify_last_imported_at',
        'shopify_birth_initialized',
        'shopify_primary_image_url',
        'shopify_image_checksum',
    ))
    AUTOMATIC_FIELDS = frozenset((
        'id', 'display_name', 'create_uid', 'create_date',
        'write_uid', 'write_date',
    ))

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Product Variant Binding Test Store',
            'shop_domain': 'product-variant-binding-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.user_auditor = cls._create_group_user(
            'auditor', 'group_shopify_connector_auditor'
        )
        cls.user_operator = cls._create_group_user(
            'operator', 'group_shopify_connector_operator'
        )
        cls.user_reviewer = cls._create_group_user(
            'reviewer', 'group_shopify_connector_reviewer'
        )
        cls.user_admin = cls._create_group_user(
            'admin', 'group_shopify_connector_admin'
        )

    @classmethod
    def _create_group_user(cls, label, group_xmlid):
        group = cls.env.ref('shopify_connector_core.%s' % group_xmlid)
        return cls.env['res.users'].create({
            'name': 'Product Variant Binding Test %s' % label,
            'login': 'product_variant_binding_test_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _make_template_binding(self, gid, name='Test Template'):
        template = self.env['product.template'].create({'name': name})
        return self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': gid,
            'product_template_id': template.id,
        })

    # ------------------------------------------------------------------
    # 1. Required fields.
    # ------------------------------------------------------------------

    @mute_logger('odoo.sql_db')
    def test_requires_store_id(self):
        template_binding = self._make_template_binding(
            'gid://shopify/Product/100', 'Template 100',
        )
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.VariantBinding.create({
                    'shopify_gid': 'gid://shopify/ProductVariant/100',
                    'product_variant_id': template_binding.product_template_id.product_variant_id.id,
                    'product_template_binding_id': template_binding.id,
                })

    @mute_logger('odoo.sql_db')
    def test_requires_shopify_gid(self):
        template_binding = self._make_template_binding(
            'gid://shopify/Product/101', 'Template 101',
        )
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.VariantBinding.create({
                    'store_id': self.store.id,
                    'product_variant_id': template_binding.product_template_id.product_variant_id.id,
                    'product_template_binding_id': template_binding.id,
                })

    @mute_logger('odoo.sql_db')
    def test_requires_product_template_binding_id(self):
        """product_template_binding_id is required and never stands in
        for a missing variant binding -- importing a variant always
        creates/links its own variant-binding row."""
        template_binding = self._make_template_binding(
            'gid://shopify/Product/102', 'Template 102',
        )
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.VariantBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/ProductVariant/102',
                    'product_variant_id': template_binding.product_template_id.product_variant_id.id,
                })

    # ------------------------------------------------------------------
    # 2. Uniqueness constraints.
    # ------------------------------------------------------------------

    @mute_logger('odoo.sql_db')
    def test_unique_store_shopify_gid_enforced(self):
        template_binding = self._make_template_binding(
            'gid://shopify/Product/103', 'Template 103',
        )
        other_template = self.env['product.template'].create({
            'name': 'Other Variant Product',
        })
        self.VariantBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/103',
            'product_variant_id': template_binding.product_template_id.product_variant_id.id,
            'product_template_binding_id': template_binding.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.VariantBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/ProductVariant/103',
                    'product_variant_id': other_template.product_variant_id.id,
                    'product_template_binding_id': template_binding.id,
                })

    @mute_logger('odoo.sql_db')
    def test_unique_store_product_variant_enforced(self):
        template_binding = self._make_template_binding(
            'gid://shopify/Product/104', 'Template 104',
        )
        variant = template_binding.product_template_id.product_variant_id
        self.VariantBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/104',
            'product_variant_id': variant.id,
            'product_template_binding_id': template_binding.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.VariantBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/ProductVariant/105',
                    'product_variant_id': variant.id,
                    'product_template_binding_id': template_binding.id,
                })

    # ------------------------------------------------------------------
    # 3. Access matrix.
    # ------------------------------------------------------------------

    def test_access_matrix_across_four_groups(self):
        template_binding = self._make_template_binding(
            'gid://shopify/Product/106', 'Template 106',
        )
        variant = template_binding.product_template_id.product_variant_id
        binding = self.VariantBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/106',
            'product_variant_id': variant.id,
            'product_template_binding_id': template_binding.id,
        })
        other_template = self.env['product.template'].create({
            'name': 'Other Access Product',
        })

        for index, (label, user) in enumerate((
            ('auditor', self.user_auditor),
            ('operator', self.user_operator),
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ), start=107):
            view = self.VariantBinding.with_user(user)
            view.browse(binding.id).read(['shopify_gid'])
            with self.assertRaises(AccessError, msg=label):
                view.create({
                    'store_id': self.store.id,
                    'shopify_gid': (
                        'gid://shopify/ProductVariant/%d' % index
                    ),
                    'product_variant_id': (
                        other_template.product_variant_id.id
                    ),
                    'product_template_binding_id': template_binding.id,
                })

        for label, user in (
            ('auditor', self.user_auditor),
            ('operator', self.user_operator),
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ):
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({
                    'shopify_option_values': '%s Write' % label,
                })

    def _audit_counts(self):
        jobs = self.env['shopify.connector.job'].search([
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        return (
            len(jobs),
            self.env['shopify.connector.job.log'].search_count([
                ('job_id', 'in', jobs.ids),
            ]),
        )

    def test_exact_stored_field_classification_and_protected_set(self):
        self.assertEqual(
            self.VariantBinding._protected_binding_fields(),
            self.EXPECTED_PROTECTED_FIELDS,
        )
        stored_fields = {
            name
            for name, field in self.VariantBinding._fields.items()
            if field.store and name not in self.AUTOMATIC_FIELDS
        }
        self.assertEqual(stored_fields, self.EXPECTED_PROTECTED_FIELDS)

    def test_complete_protected_surface_denies_create_alter_and_clear(self):
        template_binding = self._make_template_binding(
            'gid://shopify/Product/ProtectedVariantTemplate',
            'Protected Variant Template',
        )
        other_template_binding = self._make_template_binding(
            'gid://shopify/Product/ProtectedVariantOtherTemplate',
            'Protected Variant Other Template',
        )
        variant = template_binding.product_template_id.product_variant_id
        other_variant = (
            other_template_binding.product_template_id.product_variant_id
        )
        other_store = self.env['shopify.connector.store'].create({
            'name': 'Protected Variant Target Store',
            'shop_domain': 'protected-variant-target.myshopify.com',
            'api_version': '2026-07',
        })
        # SEC-3 (#197): the binding lives in the SAME store as its template
        # binding. It previously lived in `other_store` while pointing at a
        # template binding in `self.store` -- a cross-store pair that the
        # same-store constraint now refuses outright. `other_store` keeps its
        # role as the forgery TARGET below, which is what the test is actually
        # about.
        binding = self.VariantBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/ProtectedSurface',
            'product_variant_id': variant.id,
            'product_template_binding_id': template_binding.id,
            'status': 'active',
            'match_key': 'sku_reference',
            'matched_by_uid': self.user_admin.id,
            'matched_at': '2000-01-01 00:00:00',
            'override_uid': self.user_reviewer.id,
            'override_at': '2000-01-02 00:00:00',
            'override_previous_candidate': 'product.product,1',
            'shopify_option_values': 'Size=M',
            'shopify_price_snapshot': 10.0,
            'shopify_compare_at_price_snapshot': 12.0,
            'shopify_last_imported_at': '2000-01-03 00:00:00',
            'shopify_primary_image_url': 'https://example.invalid/original',
            'shopify_image_checksum': 'original-checksum',
        })
        attempted_values = {
            # SEC-3 (#197): company is store-derived, so supplying it is a
            # forgery attempt like any other protected field -- including the
            # attempt to CLEAR it, which the loop below also exercises.
            'company_id': self.env.company.id,
            'sec3_scope_quarantined': True,
            'store_id': other_store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/Forged',
            'product_variant_id': other_variant.id,
            'status': 'manually_overridden',
            'match_key': 'manual',
            'matched_by_uid': self.user_reviewer.id,
            'matched_at': fields.Datetime.now(),
            'override_uid': self.user_admin.id,
            'override_at': fields.Datetime.now(),
            'override_previous_candidate': 'product.product,999',
            'product_template_binding_id': other_template_binding.id,
            'shopify_option_values': 'Size=Forged',
            'shopify_price_snapshot': 999.0,
            'shopify_compare_at_price_snapshot': 1000.0,
            'shopify_last_imported_at': fields.Datetime.now(),
            'shopify_primary_image_url': 'https://example.invalid/forged',
            'shopify_image_checksum': 'forged-checksum',
        }
        self.assertEqual(
            frozenset(attempted_values),
            self.EXPECTED_PROTECTED_FIELDS,
        )
        audit_before = self._audit_counts()
        roles = (
            ('auditor', self.user_auditor),
            ('operator', self.user_operator),
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        )
        for label, user in roles:
            model = self.VariantBinding.with_user(user)
            for field_name, attempted in attempted_values.items():
                with self.assertRaises(
                    AccessError, msg=(label, field_name, 'create'),
                ):
                    model.create({field_name: attempted})
                before = binding.sudo().read([field_name])[0][field_name]
                for value, operation in (
                    (attempted, 'alter'),
                    (False, 'clear'),
                ):
                    with self.assertRaises(
                        AccessError, msg=(label, field_name, operation),
                    ):
                        binding.with_user(user).write({field_name: value})
                    binding.invalidate_recordset([field_name])
                    self.assertEqual(
                        binding.sudo().read([field_name])[0][field_name],
                        before,
                        msg=(label, field_name, operation),
                    )
        self.assertEqual(self._audit_counts(), audit_before)

    def test_product_importer_binding_writers_use_exact_sudo_sites(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
            'shopify_connector_product_importer.py',
        )
        with open(path, encoding='utf-8') as source_file:
            tree = ast.parse(source_file.read(), filename=path)

        methods = {
            node.name: node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
        }

        def is_sudo_write(call, record_name):
            if not (
                isinstance(call, ast.Call)
                and isinstance(call.func, ast.Attribute)
                and call.func.attr == 'write'
                and isinstance(call.func.value, ast.Call)
                and isinstance(call.func.value.func, ast.Attribute)
                and call.func.value.func.attr == 'sudo'
                and isinstance(call.func.value.func.value, ast.Name)
            ):
                return False
            return call.func.value.func.value.id == record_name

        # Count only the binding *write* of the snapshot (the sanctioned
        # refresh site). The sibling create path passes ``snapshot_vals`` as
        # the first positional arg to ``dict(...)`` -- that record-building
        # call must not be conflated with the write, so the filter is scoped
        # to ``.write(...)`` attribute calls.
        variant_refreshes = [
            node
            for node in ast.walk(methods['_resolve_one_variant'])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'write'
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == 'snapshot_vals'
        ]
        self.assertEqual(len(variant_refreshes), 1)
        self.assertTrue(is_sudo_write(variant_refreshes[0], 'existing'))

        checksum_writes = []
        for node in ast.walk(methods['_apply_image']):
            if not (
                isinstance(node, ast.Call)
                and node.args
                and isinstance(node.args[0], ast.Dict)
            ):
                continue
            keys = {
                key.value
                for key in node.args[0].keys
                if isinstance(key, ast.Constant)
            }
            if 'shopify_image_checksum' in keys:
                checksum_writes.append(node)
        self.assertEqual(len(checksum_writes), 1)
        self.assertTrue(is_sudo_write(checksum_writes[0], 'binding'))

        direct_checksum_assignments = [
            node
            for node in ast.walk(methods['_apply_image'])
            if isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Attribute)
                and target.attr == 'shopify_image_checksum'
                for target in node.targets
            )
        ]
        self.assertEqual(direct_checksum_assignments, [])
