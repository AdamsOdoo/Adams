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

    def _admin_credential(self):
        """One credential row, created the ONLY way a credential row is created.

        Batch 1 correction: `create()` on this model is refused outright now --
        including for an Administrator -- so a fixture cannot mint a row directly
        any more. That refusal is the subject of
        `test_direct_orm_mutation_cannot_bypass_the_credential_service`; here it
        just means the fixture goes through the sanctioned service, which is what
        production does.
        """
        Credential = self.env['shopify.connector.store.credential']
        Credential.with_user(self.user_admin).action_set_token(
            self.store, 'shpat_ACCESSFIXTURE0000000000000000',
        )
        return Credential.sudo().search(
            [('store_id', '=', self.store.id)], limit=1,
        )

    def test_direct_orm_mutation_cannot_bypass_the_credential_service(self):
        """§9.1: no role, not even Administrator, mutates this row directly.

        The ACL grants an Administrator `create`/`write`, so before this the
        direct route was open and skipped every invalidation the service performs
        -- the token-cache discard, the identity-epoch bump, the cleared
        verification stamp and the `connected` -> `reconnect_needed` demotion. The
        refusal is therefore not an ACL tightening (the ACL is unchanged); it is a
        closed write surface on top of it.
        """
        Credential = self.env['shopify.connector.store.credential']
        credential = self._admin_credential()
        as_admin = Credential.with_user(self.user_admin)
        with self.assertRaises(AccessError):
            as_admin.create({'store_id': self.store.id})
        with self.assertRaises(AccessError):
            as_admin.browse(credential.id).write({'credential_state': 'absent'})
        with self.assertRaises(AccessError):
            as_admin.browse(credential.id).write(
                {'access_token': 'shpat_SMUGGLED000000000000000000000'},
            )
        with self.assertRaises(AccessError):
            as_admin.browse(credential.id).unlink()
        # `sudo()` is not a way round it either: the guard does not key off
        # `env.su`, it keys off the unforgeable service sentinel.
        with self.assertRaises(AccessError):
            Credential.sudo().create({'store_id': self.store.id})
        with self.assertRaises(AccessError):
            credential.sudo().write({'credential_state': 'absent'})
        with self.assertRaises(AccessError):
            credential.sudo().unlink()
        # A forged context cannot open the surface, because the sentinel is a
        # Python object identity and every RPC context value is JSON.
        with self.assertRaises(AccessError):
            Credential.with_user(self.user_admin).with_context(
                shopify_credential_write_surface='_mutate_token',
                shopify_credential_service_sentinel='_mutate_token',
            ).browse(credential.id).write({'credential_state': 'absent'})
        with self.assertRaises(AccessError):
            Credential.with_user(self.user_admin).with_context(
                shopify_credential_write_surface='_mutate_token',
                shopify_credential_service_sentinel=True,
            ).create({'store_id': self.store.id})
        # And an unknown surface name is refused at the seam itself.
        with self.assertRaises(AccessError):
            Credential._credential_surface('_not_a_surface')
        # The sanctioned route still works, and the row is intact.
        Credential.with_user(self.user_admin).action_replace_token(
            self.store, 'shpat_LEGITIMATEREPLACE00000000000000',
        )
        self.assertEqual(credential.credential_state, 'present')

    def test_non_admin_roles_denied_all_crud_and_search(self):
        Credential = self.env['shopify.connector.store.credential']
        admin_credential = self._admin_credential()
        for user in (self.user_auditor, self.user_operator, self.user_reviewer):
            # The sanctioned route is refused for these roles by the ACL, which
            # is the guarantee that actually matters: `action_set_token` runs as
            # the calling user precisely so this check stays live.
            with self.assertRaises(AccessError):
                Credential.with_user(user).action_set_token(
                    self.store, 'shpat_SHOULDNEVERLAND0000000000000',
                )
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

    def test_admin_reads_directly_and_mutates_only_through_the_service(self):
        """The Administrator's real capability, stated exactly.

        Safe metadata remains directly readable, but raw credential values are
        write-only even for an Administrator. MUTATION is service-only (§9.1),
        and `unlink` is refused to everyone including the service, because
        credential history is retained (MBQ-08).
        """
        Credential = self.env['shopify.connector.store.credential']
        credential = self._admin_credential()
        as_admin = Credential.with_user(self.user_admin)
        # Safe metadata: allowed directly.
        metadata = as_admin.browse(credential.id).read(
            ['credential_state', 'auth_mode'],
        )[0]
        self.assertNotIn('access_token', metadata)
        self.assertNotIn('client_secret', metadata)
        self.assertTrue(as_admin.search([('store_id', '=', self.store.id)]))
        search_metadata = as_admin.search_read(
            [('id', '=', credential.id)], ['credential_state', 'auth_mode'],
        )[0]
        self.assertNotIn('access_token', search_metadata)
        self.assertNotIn('client_secret', search_metadata)
        # Raw values: never returned by read, search_read, export, or an
        # unqualified read that would otherwise select every readable field.
        for field in ('access_token', 'client_secret'):
            with self.subTest(field=field):
                with self.assertRaises(AccessError):
                    as_admin.browse(credential.id).read([field])
                with self.assertRaises(AccessError):
                    as_admin.search_read(
                        [('id', '=', credential.id)], [field],
                    )
                with self.assertRaises(AccessError):
                    as_admin.browse(credential.id).export_data([field])
        with self.assertRaises(AccessError):
            as_admin.browse(credential.id).read()
        # A secret must not become a boolean oracle through a domain or a
        # grouped query, either.  These are separate ORM paths from read() and
        # are also used by the web client.
        for domain in (
            [('access_token', '=', 'shpat_ACCESSFIXTURE0000000000000000')],
            ['|', ('store_id', '=', self.store.id),
             ('client_secret', '!=', False)],
        ):
            with self.subTest(domain=domain):
                with self.assertRaises(AccessError):
                    as_admin.search(domain)
                with self.assertRaises(AccessError):
                    as_admin.search_count(domain)
        with self.assertRaises(AccessError):
            as_admin.read_group([], ['access_token:count'], [])
        with self.assertRaises(AccessError):
            as_admin.read_group([], ['credential_state'], ['client_secret'])
        with self.assertRaises(AccessError):
            as_admin.web_read({'access_token': {}})
        with self.assertRaises(AccessError):
            as_admin.web_search_read([], {'client_secret': {}})
        # The existing internal accessor remains the only in-process route to
        # the stored offline token; it is not an ORM projection.
        self.assertEqual(
            Credential._get_access_token(self.store),
            'shpat_ACCESSFIXTURE0000000000000000',
        )
        # The client-secret mode has the same narrow internal accessor.  Set it
        # through the service, then prove the safe projection still contains no
        # raw value while HMAC callers can obtain it in-process.
        as_admin.action_set_client_credentials(
            self.store, 'client-id-for-access-test', 'client-secret-for-test',
        )
        self.assertEqual(
            Credential._get_client_secret(self.store),
            'client-secret-for-test',
        )
        safe_projection = as_admin.browse(credential.id).read(
            ['credential_state', 'auth_mode'],
        )[0]
        self.assertNotIn('access_token', safe_projection)
        self.assertNotIn('client_secret', safe_projection)
        # Mutate: only through the service.
        with self.assertRaises(AccessError):
            as_admin.browse(credential.id).write({'credential_state': 'absent'})
        as_admin.action_clear_token(self.store)
        self.assertEqual(credential.credential_state, 'absent')
        # Delete: never, by any route.
        with self.assertRaises(AccessError):
            as_admin.browse(credential.id).unlink()
        self.assertTrue(credential.exists())

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
        admin_credential = self._admin_credential()
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
        self.assertNotIn('client_secret', exposed_fields)
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
