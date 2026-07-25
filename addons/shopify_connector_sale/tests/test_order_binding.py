from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import mute_logger

from .test_order_import_mapping import OrderImportCase


class TestOrderBinding(OrderImportCase):

    EXPECTED_ADDITIONAL_FIELDS = frozenset((
        'shopify_order_name',
        'shopify_legacy_resource_id',
        'shopify_processed_at',
        'shopify_updated_at_snapshot',
        'shopify_created_at',
        'shopify_currency_code',
        'shopify_presentment_currency_code',
        'shopify_taxes_included',
        'shopify_financial_status_snapshot',
        'shopify_previous_financial_status_snapshot',
        'shopify_fulfillment_status_snapshot',
        'shopify_cancelled_at',
        'shopify_cancel_reason',
        'shopify_order_total_amount',
        'shopify_order_total_presentment',
        'shopify_subtotal_amount',
        'shopify_total_tax_amount',
        'shopify_total_discounts_amount',
        'shopify_total_shipping_amount',
        'shopify_total_tip_amount',
        'customer_resolution',
        'shopify_last_imported_at',
        'shopify_last_evidence_refresh_at',
        'financial_status_changed_at',
        'financial_status_trigger_source',
        'manual_gateway_name',
        'manual_gateway_evidence_state',
        'manual_gateway_approval_state',
        'manual_gateway_approved_by_uid',
        'manual_gateway_approved_at',
        'manual_gateway_approved_shopify_updated_at',
        'is_cod',
        'cod_commercial_state',
        'cod_fulfillment_state',
        'cod_collection_state',
        'cod_order_value_amount',
        'cod_fulfilled_value_amount',
        'cod_collected_value_amount',
        'cod_refunded_value_amount',
        'cod_cancelled_value_amount',
    ))
    EXPECTED_PROTECTED_FIELDS = frozenset((
        # SEC-3 (#197): the store-derived company. Protected, not caller input
        # -- a binding's company is whatever its store's company is.
        'company_id',
        # SEC-3 (#197): set only by the upgrade scope sweep and cleared only by
        # the administrative release action. A caller-writable quarantine flag
        # would let exactly the rows it hides unhide themselves.
        'sec3_scope_quarantined',
        'store_id', 'shopify_gid', 'sale_order_id', 'status', 'match_key',
        'matched_by_uid', 'matched_at', 'override_uid', 'override_at',
        'override_previous_candidate',
    )) | EXPECTED_ADDITIONAL_FIELDS
    AUTOMATIC_FIELDS = frozenset((
        'id', 'display_name', 'create_uid', 'create_date',
        'write_uid', 'write_date',
    ))

    def _draft_order(self, name):
        return self.env['sale.order'].create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
            'payment_term_id': self.payment_term.id,
            'origin': name,
        })

    def _binding(self, gid='gid://shopify/Order/Binding'):
        return self.Binding.sudo().create({
            'store_id': self.store.id,
            'shopify_gid': gid,
            'sale_order_id': self._draft_order(gid).id,
            'shopify_updated_at_snapshot': fields.Datetime.now(),
        })

    def test_identity_and_pii_contract(self):
        self.assertEqual(self.Binding._odoo_binding_field_name(), 'sale_order_id')
        self.assertEqual(self.Binding._pii_snapshot_fields(), ())
        self.assertEqual(
            self.Binding._additional_protected_binding_fields(),
            self.EXPECTED_ADDITIONAL_FIELDS,
        )
        self.assertEqual(
            self.Binding._protected_binding_fields(),
            self.EXPECTED_PROTECTED_FIELDS,
        )
        # 50 + SEC-3 `company_id` and `sec3_scope_quarantined` (#197).
        self.assertEqual(len(self.EXPECTED_PROTECTED_FIELDS), 52)

    def test_every_stored_connector_field_is_classified(self):
        stored = {
            name for name, field in self.Binding._fields.items()
            if field.store and name not in self.AUTOMATIC_FIELDS
        }
        self.assertEqual(stored, self.EXPECTED_PROTECTED_FIELDS)
        self.Binding._assert_binding_field_classification()

    def test_required_fields_and_uniqueness(self):
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self.Binding.sudo().create({
                    'shopify_gid': 'gid://shopify/Order/MissingStore',
                    'sale_order_id': self._draft_order('missing-store').id,
                })
        first = self._binding('gid://shopify/Order/Unique')
        original_company = self.settings.order_company_id
        other_company = self.env['res.company'].sudo().create({
            'name': 'Order Binding Immutable Company',
        })
        with self.assertRaises(ValidationError):
            self.settings.write({'order_company_id': other_company.id})
        self.assertEqual(self.settings.order_company_id, original_company)
        with mute_logger('odoo.sql_db'):
            with self.assertRaises(IntegrityError):
                with self.env.cr.savepoint():
                    self.Binding.sudo().create({
                        'store_id': self.store.id,
                        'shopify_gid': first.shopify_gid,
                        'sale_order_id': self._draft_order('duplicate-gid').id,
                    })
            with self.assertRaises(IntegrityError):
                with self.env.cr.savepoint():
                    self.Binding.sudo().create({
                        'store_id': self.store.id,
                        'shopify_gid': 'gid://shopify/Order/Other',
                        'sale_order_id': first.sale_order_id.id,
                    })

    def test_all_roles_cannot_forge_or_clear_protected_fields(self):
        binding = self._binding('gid://shopify/Order/Protected')
        other_order = self._draft_order('protected-other')
        attempts = {
            # SEC-3 (#197): company is store-derived, so supplying it is a
            # forgery attempt like any other protected field -- including the
            # attempt to CLEAR it, which the loop below also exercises.
            'company_id': self.env.company.id,
            # SEC-3 (#197): the scope quarantine is set only by the upgrade
            # sweep and cleared only by the administrative release action, so
            # a caller supplying it is forging exactly like any other
            # protected field -- a writable quarantine flag would let the rows
            # it hides unhide themselves.
            'sec3_scope_quarantined': True,
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Order/Forged',
            'sale_order_id': other_order.id,
            'status': 'review',
            'match_key': 'manual',
            'matched_by_uid': self.roles['admin'].id,
            'matched_at': fields.Datetime.now(),
            'override_uid': self.roles['reviewer'].id,
            'override_at': fields.Datetime.now(),
            'override_previous_candidate': 'sale.order,999',
        }
        attempts.update({
            field_name: (
                True if self.Binding._fields[field_name].type == 'boolean'
                else fields.Datetime.now()
                if self.Binding._fields[field_name].type == 'datetime'
                else self.roles['admin'].id
                if self.Binding._fields[field_name].type == 'many2one'
                else 'forged'
            )
            for field_name in self.EXPECTED_ADDITIONAL_FIELDS
        })
        self.assertEqual(frozenset(attempts), self.EXPECTED_PROTECTED_FIELDS)
        audits_before = self.env['shopify.connector.job'].search_count([
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        for role, user in self.roles.items():
            model = self.Binding.with_user(user)
            for field_name, value in attempts.items():
                with self.assertRaises(AccessError, msg=(role, field_name, 'create')):
                    model.create({field_name: value})
                before = binding.sudo().read([field_name])[0][field_name]
                for attempted, operation in ((value, 'alter'), (False, 'clear')):
                    with self.assertRaises(
                        AccessError, msg=(role, field_name, operation),
                    ):
                        binding.with_user(user).write({field_name: attempted})
                    binding.invalidate_recordset([field_name])
                    self.assertEqual(
                        binding.sudo().read([field_name])[0][field_name], before,
                        (role, field_name, operation),
                    )
        self.assertEqual(
            self.env['shopify.connector.job'].search_count([
                ('job_type', '=', 'core_manual_maintenance'),
            ]),
            audits_before,
        )
