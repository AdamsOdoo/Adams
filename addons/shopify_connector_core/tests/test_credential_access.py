from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase, tagged


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
            'group_ids': [(6, 0, [group.id])],
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
            # fields_get() is a schema call, not gated by ir.model.access
            # CRUD rows in Odoo -- it may legitimately return the model's
            # field metadata (names/types) even for a role with zero ACL
            # rows on the model, so it must not be used as a security
            # oracle here. Security is instead proven above by the five
            # actual operations (search/create/read/write/unlink), all of
            # which raise AccessError for every non-admin role -- that is
            # the real guarantee that no credential data, including
            # `access_token`, is ever reachable by these roles. The
            # `access_token` field's own independent field-level `groups=`
            # protection (which fields_get() *does* honor) is separately
            # covered by test_field_groups_independent_of_model_acl below.

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
        # Unlike test_non_admin_roles_denied_all_crud_and_search above,
        # this fields_get() call is not standing in for a model-ACL check
        # -- with model read access now temporarily widened, the only
        # thing left protecting `access_token` is its own field-level
        # `groups=` attribute, which fields_get() *does* honor (it hides
        # any field the caller's groups don't satisfy). The real proof is
        # still the actual-operation read() below; this assertion is a
        # supplementary check of that specific, independent mechanism.
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
