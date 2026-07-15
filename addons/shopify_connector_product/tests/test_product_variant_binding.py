from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestProductVariantBinding(TransactionCase):

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
        ):
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({
                    'shopify_option_values': '%s Write' % label,
                })

        for label, user in (
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ):
            binding.with_user(user).write({
                'shopify_option_values': '%s Write' % label,
            })
            self.assertEqual(
                binding.shopify_option_values, '%s Write' % label,
            )
