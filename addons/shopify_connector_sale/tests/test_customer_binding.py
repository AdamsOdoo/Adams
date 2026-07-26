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
class TestCustomerBinding(TransactionCase):

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
        'partner_id',
        'status',
        'match_key',
        'matched_by_uid',
        'matched_at',
        'override_uid',
        'override_at',
        'override_previous_candidate',
        'shopify_display_name',
        'shopify_email_snapshot',
        'shopify_phone_snapshot',
        'shopify_last_imported_at',
    ))
    AUTOMATIC_FIELDS = frozenset((
        'id', 'display_name', 'create_uid', 'create_date',
        'write_uid', 'write_date',
    ))

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
    # 4. Effective matrix after SEC-1: reads remain ACL-governed; all
    # connector-owned stored fields are service-maintained and protected.
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
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ):
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({
                    'shopify_display_name': '%s Write' % label,
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
            self.CustomerBinding._protected_binding_fields(),
            self.EXPECTED_PROTECTED_FIELDS,
        )
        stored_fields = {
            name
            for name, field in self.CustomerBinding._fields.items()
            if field.store and name not in self.AUTOMATIC_FIELDS
        }
        self.assertEqual(stored_fields, self.EXPECTED_PROTECTED_FIELDS)
        # SEC-2 removed the masked display entirely. What remains is the
        # non-stored refresh flag for rows the pre-SEC-2 sweep already masked.
        self.assertNotIn('pii_snapshot_masked', self.CustomerBinding._fields)
        self.assertFalse(self.CustomerBinding._fields[
            'pii_snapshot_refresh_required'
        ].store)

    def test_complete_protected_surface_denies_create_alter_and_clear(self):
        partner = self._make_partner('Protected Surface Current')
        other_partner = self._make_partner('Protected Surface Target')
        other_store = self.env['shopify.connector.store'].create({
            'name': 'Protected Customer Target Store',
            'shop_domain': 'protected-customer-target.myshopify.com',
            'api_version': '2026-07',
        })
        binding = self.CustomerBinding.sudo().create({
            'store_id': other_store.id,
            'shopify_gid': 'gid://shopify/Customer/ProtectedSurface',
            'partner_id': partner.id,
            'status': 'active',
            'match_key': 'email',
            'matched_by_uid': self.user_admin.id,
            'matched_at': '2000-01-01 00:00:00',
            'override_uid': self.user_reviewer.id,
            'override_at': '2000-01-02 00:00:00',
            'override_previous_candidate': 'res.partner,1',
            'shopify_display_name': 'Original customer',
            'shopify_email_snapshot': 'original@example.invalid',
            'shopify_phone_snapshot': '+971500000001',
            'shopify_last_imported_at': '2000-01-03 00:00:00',
        })
        attempted_values = {
            # SEC-3 (#197): company is store-derived, so supplying it is a
            # forgery attempt like any other protected field -- including the
            # attempt to CLEAR it, which the loop below also exercises.
            'company_id': self.env.company.id,
            'sec3_scope_quarantined': True,
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Customer/Forged',
            'partner_id': other_partner.id,
            'status': 'manually_overridden',
            'match_key': 'manual',
            'matched_by_uid': self.user_reviewer.id,
            'matched_at': fields.Datetime.now(),
            'override_uid': self.user_admin.id,
            'override_at': fields.Datetime.now(),
            'override_previous_candidate': 'res.partner,999',
            'shopify_display_name': 'Forged customer',
            'shopify_email_snapshot': 'forged@example.invalid',
            'shopify_phone_snapshot': '+971509999999',
            'shopify_last_imported_at': fields.Datetime.now(),
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
            model = self.CustomerBinding.with_user(user)
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
