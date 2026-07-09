from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestProductTemplateBinding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Product Template Binding Test Store',
            'shop_domain': 'product-template-binding-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
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
            'name': 'Product Template Binding Test %s' % label,
            'login': 'product_template_binding_test_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _make_template(self, name='Test Template'):
        return self.env['product.template'].create({'name': name})

    # ------------------------------------------------------------------
    # 1. Required fields.
    # ------------------------------------------------------------------

    def test_requires_store_id(self):
        template = self._make_template()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.TemplateBinding.create({
                    'shopify_gid': 'gid://shopify/Product/1',
                    'product_template_id': template.id,
                })

    def test_requires_shopify_gid(self):
        template = self._make_template()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.TemplateBinding.create({
                    'store_id': self.store.id,
                    'product_template_id': template.id,
                })

    def test_requires_product_template_id(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.TemplateBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Product/2',
                })

    # ------------------------------------------------------------------
    # 2. Uniqueness constraints.
    # ------------------------------------------------------------------

    @mute_logger('odoo.sql_db')
    def test_unique_store_shopify_gid_enforced(self):
        template_1 = self._make_template('Template A')
        template_2 = self._make_template('Template B')
        self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/3',
            'product_template_id': template_1.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.TemplateBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Product/3',
                    'product_template_id': template_2.id,
                })

    @mute_logger('odoo.sql_db')
    def test_unique_store_product_template_enforced(self):
        template = self._make_template('Template C')
        self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/4',
            'product_template_id': template.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.TemplateBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Product/5',
                    'product_template_id': template.id,
                })

    # ------------------------------------------------------------------
    # 3. status default.
    # ------------------------------------------------------------------

    def test_status_defaults_to_active(self):
        template = self._make_template('Template D')
        binding = self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/6',
            'product_template_id': template.id,
        })
        self.assertEqual(binding.status, 'active')

    # ------------------------------------------------------------------
    # 4. Access matrix: auditor read-only; operator read/create;
    # reviewer read/write; admin full (read/write/create).
    # ------------------------------------------------------------------

    def test_access_matrix_across_four_groups(self):
        template = self._make_template('Template E')
        binding_as_admin = self.TemplateBinding.with_user(
            self.user_admin
        ).create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/7',
            'product_template_id': template.id,
        })

        # Auditor: read-only.
        auditor_view = self.TemplateBinding.with_user(self.user_auditor)
        auditor_view.browse(binding_as_admin.id).read(['shopify_gid'])
        with self.assertRaises(AccessError):
            auditor_view.create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Product/8',
                'product_template_id': self._make_template('Template F').id,
            })
        with self.assertRaises(AccessError):
            auditor_view.browse(binding_as_admin.id).write(
                {'shopify_title': 'Auditor Write'}
            )

        # Operator: read + create, no write.
        operator_view = self.TemplateBinding.with_user(self.user_operator)
        operator_view.browse(binding_as_admin.id).read(['shopify_gid'])
        operator_created = operator_view.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/9',
            'product_template_id': self._make_template('Template G').id,
        })
        with self.assertRaises(AccessError):
            operator_view.browse(binding_as_admin.id).write(
                {'shopify_title': 'Operator Write'}
            )

        # Reviewer: read + write, no create.
        reviewer_view = self.TemplateBinding.with_user(self.user_reviewer)
        reviewer_view.browse(binding_as_admin.id).read(['shopify_gid'])
        reviewer_view.browse(operator_created.id).write(
            {'shopify_title': 'Reviewer Write'}
        )
        with self.assertRaises(AccessError):
            reviewer_view.create({
                'store_id': self.store.id,
                'shopify_gid': 'gid://shopify/Product/10',
                'product_template_id': self._make_template('Template H').id,
            })

        # Admin: full (read/write/create), proven by the create above and:
        binding_as_admin.write({'shopify_title': 'Admin Write'})
        self.assertEqual(binding_as_admin.shopify_title, 'Admin Write')
