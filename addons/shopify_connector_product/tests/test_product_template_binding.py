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
    # 4. Effective matrix after SEC-1: role reads and snapshot writes
    # remain ACL-governed; protected identity create is denied for all.
    # ------------------------------------------------------------------

    def test_access_matrix_across_four_groups(self):
        template = self._make_template('Template E')
        binding = self.TemplateBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/7',
            'product_template_id': template.id,
        })

        for index, (label, user) in enumerate((
            ('auditor', self.user_auditor),
            ('operator', self.user_operator),
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ), start=8):
            view = self.TemplateBinding.with_user(user)
            view.browse(binding.id).read(['shopify_gid'])
            with self.assertRaises(AccessError, msg=label):
                view.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Product/%d' % index,
                    'product_template_id': self._make_template(
                        'Protected Create %s' % label
                    ).id,
                })

        for label, user in (
            ('auditor', self.user_auditor),
            ('operator', self.user_operator),
        ):
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({
                    'shopify_title': '%s Write' % label,
                })

        for label, user in (
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ):
            binding.with_user(user).write({
                'shopify_title': '%s Write' % label,
            })
            self.assertEqual(binding.shopify_title, '%s Write' % label)
