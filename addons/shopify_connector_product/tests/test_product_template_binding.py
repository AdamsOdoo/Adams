from unittest.mock import patch

from odoo import fields
from odoo.exceptions import AccessError, UserError
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
class TestProductTemplateBinding(TransactionCase):

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
        'product_template_id',
        'status',
        'match_key',
        'matched_by_uid',
        'matched_at',
        'override_uid',
        'override_at',
        'override_previous_candidate',
        'shopify_title',
        'shopify_status',
        'shopify_primary_image_url',
        'shopify_last_imported_at',
        'shopify_updated_at',
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
    # 4. Effective matrix after SEC-1: reads remain ACL-governed; all
    # connector-owned stored fields are service-maintained and protected.
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
            ('reviewer', self.user_reviewer),
            ('admin', self.user_admin),
        ):
            with self.assertRaises(AccessError, msg=label):
                binding.with_user(user).write({
                    'shopify_title': '%s Write' % label,
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

    #: Fields another installed module contributes to this binding, and the
    #: module that owns each. The guard below stays EXACT rather than being
    #: loosened to a subset check: an unclassified stored field is precisely
    #: what it exists to catch, and a tolerant assertion would stop catching
    #: it. What it must not do is assume this module is the only contributor.
    #:
    #: `shopify_connector_product_export` adds the PD-PX-7 reconnect
    #: reconciliation verdict (TD-015). It is per-binding because a binding
    #: is exactly the claim being re-verified, and it is protected binding
    #: evidence: an operator who could write it could clear their own export
    #: block.
    #: TD-015 operator resolution (2026-07-27) adds three groups of fields:
    #: the machine-readable verdict reason, the evidence that verdict rests
    #: on, and the acknowledgement plus exactly what it accepted. They are
    #: protected for a sharper reason than the verdict was: they are precisely
    #: the values `_export_reconcile_ack_is_valid` consults, so a caller who
    #: could write one could manufacture a valid acknowledgement and lift
    #: their own export block without any of the checks.
    OPTIONAL_MODULE_FIELDS = {
        'shopify_connector_product_export': frozenset((
            'export_reconcile_state',
            'export_reconcile_note',
            'export_reconcile_at',
            'export_reconcile_reason',
            'export_reconcile_evidence_generation',
            'export_reconcile_evidence_product_gid',
            'export_reconcile_evidence_file_gids',
            'export_reconcile_evidence_claim_digest',
            'export_reconcile_ack_at',
            'export_reconcile_ack_uid',
            'export_reconcile_ack_reason',
            'export_reconcile_ack_generation',
            'export_reconcile_ack_product_gid',
            'export_reconcile_ack_file_gids',
            'export_reconcile_ack_claim_digest',
            'export_reconcile_ack_verdict_at',
        )),
    }

    def _expected_protected_fields(self):
        """The exact set for the modules actually installed here."""
        expected = set(self.EXPECTED_PROTECTED_FIELDS)
        installed = self.env['ir.module.module'].sudo().search([
            ('name', 'in', list(self.OPTIONAL_MODULE_FIELDS)),
            ('state', '=', 'installed'),
        ]).mapped('name')
        for name in installed:
            expected |= self.OPTIONAL_MODULE_FIELDS[name]
        return frozenset(expected)

    def test_exact_stored_field_classification_and_protected_set(self):
        expected = self._expected_protected_fields()
        self.assertEqual(
            self.TemplateBinding._protected_binding_fields(), expected,
        )
        stored_fields = {
            name
            for name, field in self.TemplateBinding._fields.items()
            if field.store and name not in self.AUTOMATIC_FIELDS
        }
        self.assertEqual(stored_fields, expected)

    def test_future_stored_field_omission_fails_closed(self):
        binding = self.TemplateBinding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/FutureContract',
            'product_template_id': self._make_template(
                'Future Contract'
            ).id,
        })
        incomplete = (
            self.TemplateBinding._additional_protected_binding_fields()
            - {'shopify_title'}
        )
        with patch.object(
            type(self.TemplateBinding),
            '_additional_protected_binding_fields',
            return_value=incomplete,
        ):
            with self.assertRaises(UserError):
                binding.sudo().write({})

    def test_complete_protected_surface_denies_create_alter_and_clear(self):
        template = self._make_template('Protected Surface Current')
        other_template = self._make_template('Protected Surface Target')
        other_store = self.env['shopify.connector.store'].create({
            'name': 'Protected Surface Target Store',
            'shop_domain': 'protected-template-target.myshopify.com',
            'api_version': '2026-07',
        })
        binding = self.TemplateBinding.sudo().create({
            'store_id': other_store.id,
            'shopify_gid': 'gid://shopify/Product/ProtectedSurface',
            'product_template_id': template.id,
            'status': 'active',
            'match_key': 'sku_reference',
            'matched_by_uid': self.user_admin.id,
            'matched_at': '2000-01-01 00:00:00',
            'override_uid': self.user_reviewer.id,
            'override_at': '2000-01-02 00:00:00',
            'override_previous_candidate': 'product.template,1',
            'shopify_title': 'Original title',
            'shopify_status': 'active',
            'shopify_primary_image_url': 'https://example.invalid/original',
            'shopify_last_imported_at': '2000-01-03 00:00:00',
            'shopify_updated_at': '2026-07-16T00:00:00Z',
            'shopify_image_checksum': 'original-checksum',
        })
        attempted_values = {
            # SEC-3 (#197): company is store-derived, so supplying it is a
            # forgery attempt like any other protected field -- including the
            # attempt to CLEAR it, which the loop below also exercises.
            'company_id': self.env.company.id,
            'sec3_scope_quarantined': True,
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/Forged',
            'product_template_id': other_template.id,
            'status': 'manually_overridden',
            'match_key': 'manual',
            'matched_by_uid': self.user_reviewer.id,
            'matched_at': fields.Datetime.now(),
            'override_uid': self.user_admin.id,
            'override_at': fields.Datetime.now(),
            'override_previous_candidate': 'product.template,999',
            'shopify_title': 'Forged title',
            'shopify_status': 'archived',
            'shopify_primary_image_url': 'https://example.invalid/forged',
            'shopify_last_imported_at': fields.Datetime.now(),
            'shopify_updated_at': '2026-07-17T00:00:00Z',
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
            model = self.TemplateBinding.with_user(user)
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
