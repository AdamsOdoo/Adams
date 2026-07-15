from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestCustomerBinding(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Customer Binding Test Store',
            'shop_domain': 'customer-binding-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.CustomerBinding = cls.env['shopify.connector.customer.binding']
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
            'name': 'Customer Binding Test %s' % label,
            'login': 'customer_binding_test_%s' % label,
            'group_ids': [(6, 0, [group.id])],
        })

    def _make_partner(self, name='Test Partner'):
        return self.env['res.partner'].create({'name': name})

    # ------------------------------------------------------------------
    # 1. Required fields.
    # ------------------------------------------------------------------

    def test_requires_store_id(self):
        partner = self._make_partner()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'shopify_gid': 'gid://shopify/Customer/1',
                    'partner_id': partner.id,
                })

    def test_requires_shopify_gid(self):
        partner = self._make_partner()
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'partner_id': partner.id,
                })

    def test_requires_partner_id(self):
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/2',
                })

    # ------------------------------------------------------------------
    # 2. Uniqueness constraints.
    # ------------------------------------------------------------------

    @mute_logger('odoo.sql_db')
    def test_unique_store_shopify_gid_enforced(self):
        partner_1 = self._make_partner('Partner A')
        partner_2 = self._make_partner('Partner B')
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/3',
            'partner_id': partner_1.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/3',
                    'partner_id': partner_2.id,
                })

    @mute_logger('odoo.sql_db')
    def test_unique_store_partner_enforced(self):
        partner = self._make_partner('Partner C')
        self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/4',
            'partner_id': partner.id,
        })
        with self.assertRaises(Exception):
            with self.env.cr.savepoint():
                self.CustomerBinding.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/5',
                    'partner_id': partner.id,
                })

    # ------------------------------------------------------------------
    # 3. status default.
    # ------------------------------------------------------------------

    def test_status_defaults_to_active(self):
        partner = self._make_partner('Partner D')
        binding = self.CustomerBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/6',
            'partner_id': partner.id,
        })
        self.assertEqual(binding.status, 'active')

    # ------------------------------------------------------------------
    # 4. Effective matrix after SEC-1: role reads and snapshot writes
    # remain ACL-governed; protected identity create is denied for all.
    # ------------------------------------------------------------------

    def test_access_matrix_across_four_groups(self):
        partner = self._make_partner('Partner E')
        binding = self.CustomerBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/7',
            'partner_id': partner.id,
        })

        for index, (label, user) in enumerate((
            ('auditor', self.user_auditor),
            ('operator', self.user_operator),
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ), start=8):
            view = self.CustomerBinding.with_user(user)
            view.browse(binding.id).read(['shopify_gid'])
            with self.assertRaises(AccessError, msg=label):
                view.create({
                    'store_id': self.store.id,
                    'shopify_gid': 'gid://shopify/Customer/%d' % index,
                    'partner_id': self._make_partner(
                        'Protected Create %s' % label
                    ).id,
                })

        for label, user in (
            ('auditor', self.user_auditor),
            ('operator', self.user_operator),
        ):
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({
                    'shopify_display_name': '%s Write' % label,
                })

        for label, user in (
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ):
            binding.with_user(user).write({
                'shopify_display_name': '%s Write' % label,
            })
            self.assertEqual(
                binding.shopify_display_name, '%s Write' % label,
            )
