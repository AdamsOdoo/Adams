from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase


class TestCredentialAccess(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Credential Access Test Store',
            'shop_domain': 'credential-access-test.myshopify.com',
            'api_version': '2026-07',
        })
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
            'name': 'Credential Access Test %s' % label,
            'login': 'credential_access_test_%s' % label,
            'groups_id': [(6, 0, [group.id])],
        })

    def test_non_admin_roles_denied_all_crud_and_search(self):
        Credential = self.env['shopify.connector.store.credential']
        admin_credential = Credential.with_user(self.user_admin).create({
            'store_id': self.store.id,
        })
        for user in (self.user_auditor, self.user_operator, self.user_reviewer):
            credential_as_user = Credential.with_user(user)
            with self.assertRaises(AccessError):
                credential_as_user.search([])
            with self.assertRaises(AccessError):
                credential_as_user.create({'store_id': self.store.id})
            with self.assertRaises(AccessError):
                credential_as_user.browse(admin_credential.id).read(
                    ['credential_state']
                )
            with self.assertRaises(AccessError):
                credential_as_user.browse(admin_credential.id).write(
                    {'credential_state': 'absent'}
                )
            with self.assertRaises(AccessError):
                credential_as_user.browse(admin_credential.id).unlink()
            # Odoo may either raise AccessError or return an empty schema
            # for a model the user has zero access rights on; both mean
            # the credential model's schema is not exposed to this role.
            try:
                exposed_fields = credential_as_user.fields_get()
            except AccessError:
                exposed_fields = {}
            self.assertEqual(exposed_fields, {})

    def test_admin_can_crud_except_unlink(self):
        credential = self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        ).create({'store_id': self.store.id})
        credential.read(['credential_state'])
        credential.write({'credential_state': 'absent'})
        with self.assertRaises(AccessError):
            credential.unlink()

    def test_field_groups_independent_of_model_acl(self):
        model = self.env['ir.model'].search(
            [('model', '=', 'shopify.connector.store.credential')], limit=1
        )
        operator_group = self.env.ref(
            'shopify_connector_core.group_shopify_connector_operator'
        )
        # Temporary, test-transaction-only ACL row simulating a future
        # ACL-widening regression -- rolled back with the rest of the
        # test transaction; the shipped CSV is never touched.
        self.env['ir.model.access'].create({
            'name': 'temp_test_operator_read_credential',
            'model_id': model.id,
            'group_id': operator_group.id,
            'perm_read': True,
            'perm_write': False,
            'perm_create': False,
            'perm_unlink': False,
        })
        Credential = self.env['shopify.connector.store.credential']
        admin_credential = Credential.with_user(self.user_admin).create({
            'store_id': self.store.id,
        })
        credential_as_operator = Credential.with_user(self.user_operator)
        exposed_fields = credential_as_operator.fields_get()
        self.assertNotIn('access_token', exposed_fields)
        with self.assertRaises(AccessError):
            credential_as_operator.browse(admin_credential.id).read(
                ['access_token']
            )

    def test_display_name_never_contains_token(self):
        token = 'shpat_DUMMYDUMMYDUMMY0000000000000000'
        Credential = self.env['shopify.connector.store.credential'].with_user(
            self.user_admin
        )
        Credential.action_set_token(self.store, token)
        credential = Credential.search([('store_id', '=', self.store.id)])
        self.assertNotIn(token, credential.display_name)
