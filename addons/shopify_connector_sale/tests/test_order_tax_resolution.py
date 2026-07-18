import json
import unicodedata

from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_tax_mapping import (
    SHOPIFY_TAX_FINGERPRINT_VERSION,
    build_tax_fingerprint,
    canonical_tax_rate,
    safe_tax_preview,
)
from .test_order_import_mapping import OrderImportCase


class TestOrderTaxResolution(OrderImportCase):

    def _tax(self, name='VAT 5', amount=5.0, included=False, **extra):
        company_id = getattr(
            extra.get('company_id', self.env.company.id),
            'id',
            extra.get('company_id', self.env.company.id),
        )
        company = self.env['res.company'].sudo().browse(company_id).exists()
        self.assertTrue(company, 'Tax fixture company must exist')

        explicit_country_id = getattr(
            extra.get('country_id'), 'id', extra.get('country_id'),
        )
        explicit_country = self.env['res.country'].sudo().browse(
            explicit_country_id,
        ).exists() if explicit_country_id else self.env['res.country']
        current_company = self.env.company.sudo()
        country = (
            explicit_country
            or company.account_fiscal_country_id
            or company.country_id
            or current_company.account_fiscal_country_id
            or current_company.country_id
            or self.env.ref('base.us')
        )
        self.assertTrue(country, 'Tax fixture country must be resolved')
        country.ensure_one()

        tax_group = self.env['account.tax.group'].sudo().create({
            'name': '%s Group' % name,
            'company_id': company.id,
            'country_id': country.id,
        })
        values = {
            'name': name,
            'amount': amount,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': tax_group.id,
            'price_include_override': (
                'tax_included' if included else 'tax_excluded'
            ),
            'include_base_amount': False,
        }
        values.update(extra)
        values.update({
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': tax_group.id,
        })
        return self.env['account.tax'].sudo().create(values)

    def _evidence(self, title='VAT', source='Shopify', liable=None):
        return {
            'title': title,
            'source': source,
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': liable,
            'priceSet': {
                'shopMoney': {'amount': '5.00'},
                'presentmentMoney': {'amount': '5.00'},
            },
        }

    def _key(self, evidence=False, included=False):
        evidence = evidence or self._evidence()
        return build_tax_fingerprint(
            evidence['rate'], evidence['ratePercentage'], evidence['title'],
            evidence['source'], evidence['channelLiable'], included,
        )

    def _mapping(self, tax=False, evidence=False, included=False, user=False):
        tax = tax or self._tax(included=included)
        evidence = evidence or self._evidence()
        Model = self.env['shopify.connector.tax.mapping']
        if user:
            Model = Model.with_user(user)
        return Model.create({
            'store_id': self.store.id,
            'shopify_tax_evidence_key': self._key(evidence, included),
            'shopify_tax_fingerprint_version': SHOPIFY_TAX_FINGERPRINT_VERSION,
            'shopify_price_included': included,
            'title_preview': safe_tax_preview(evidence['title'], 80),
            'source_preview': safe_tax_preview(evidence['source'], 48),
            'account_tax_id': tax.id,
        })

    def _order(self):
        return self.env['sale.order'].create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
            'payment_term_id': self.payment_term.id,
        })

    def test_v1_fingerprint_is_full_tuple_versioned_and_fold_free(self):
        evidence = self._evidence()
        base = self._key(evidence)
        self.assertRegex(base, r'^v1:[0-9a-f]{64}$')
        self.assertEqual(canonical_tax_rate(0.05, 5), '5')

        self.assertNotEqual(base, self._key(self._evidence(title='vat')))
        self.assertNotEqual(
            self._key(self._evidence(source=None)),
            self._key(self._evidence(source='')),
        )
        liability_keys = {
            value: self._key(self._evidence(liable=value))
            for value in (None, True, False)
        }
        self.assertNotEqual(liability_keys[None], liability_keys[True])
        self.assertNotEqual(liability_keys[None], liability_keys[False])
        self.assertNotEqual(liability_keys[True], liability_keys[False])
        self.assertNotEqual(base, self._key(evidence, included=True))

        composed = 'Café'
        decomposed = unicodedata.normalize('NFD', composed)
        self.assertNotEqual(composed, decomposed)
        self.assertEqual(
            self._key(self._evidence(title=composed)),
            self._key(self._evidence(title=decomposed)),
        )
        self.assertNotEqual(
            self._key(self._evidence(title='A|B', source='C')),
            self._key(self._evidence(title='A', source='B|C')),
        )

        with self.assertRaises(ValidationError):
            canonical_tax_rate(0.05, 6)
        for invalid in ('false', 0, 1):
            with self.assertRaises(ValidationError):
                build_tax_fingerprint(
                    0.05, 5, 'VAT', 'Shopify', invalid, False,
                )

    def test_previews_are_bounded_and_redacted(self):
        preview = safe_tax_preview(
            'VAT billing@example.invalid +971 50 123 4567 ' + 'x' * 200,
            80,
        )
        self.assertLessEqual(len(preview), 80)
        self.assertNotIn('billing@example.invalid', preview)
        self.assertNotIn('123 4567', preview)
        mapping = self._mapping(evidence=self._evidence(
            title='VAT billing@example.invalid',
            source='+971 50 123 4567',
        ))
        self.assertNotIn('billing@example.invalid', mapping.title_preview)
        self.assertNotIn('123 4567', mapping.source_preview)

    def test_mapping_acl_is_admin_write_create_only_and_no_unlink(self):
        tax = self._tax()
        Model = self.env['shopify.connector.tax.mapping']
        audit_before = self.env['shopify.connector.job'].search_count([
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        for role in ('auditor', 'operator', 'reviewer'):
            with self.assertRaises(AccessError, msg=(role, 'create')):
                self._mapping(tax=tax, user=self.roles[role])
        self.assertFalse(Model.search([]))

        mapping = self._mapping(tax=tax, user=self.roles['admin'])
        for role in ('auditor', 'operator', 'reviewer'):
            with self.assertRaises(AccessError, msg=(role, 'write')):
                mapping.with_user(self.roles[role]).write({
                    'title_preview': role,
                })
            self.assertNotEqual(mapping.title_preview, role)
        mapping.with_user(self.roles['admin']).write({'title_preview': 'Admin'})
        self.assertEqual(mapping.title_preview, 'Admin')
        for role, user in self.roles.items():
            with self.assertRaises(AccessError, msg=(role, 'unlink')):
                mapping.with_user(user).unlink()
            self.assertTrue(mapping.exists())
        self.assertEqual(
            self.env['shopify.connector.job'].search_count([
                ('job_type', '=', 'core_manual_maintenance'),
            ]),
            audit_before,
        )

    def test_mapping_rejects_wrong_company_inactive_or_incompatible_tax(self):
        other_company = self.env['res.company'].sudo().create({
            'name': 'Order Tax Other Company',
        })
        candidates = (
            self._tax(name='Inactive', active=False),
            self._tax(name='Fixed', amount_type='fixed'),
            self._tax(name='Purchase', type_tax_use='purchase'),
            self._tax(name='Compounding', include_base_amount=True),
            self._tax(name='Wrong inclusion', included=True),
            self._tax(name='Other company', company_id=other_company.id),
        )
        wrong_company_tax = candidates[-1]
        self.assertEqual(wrong_company_tax.company_id, other_company)
        for tax in candidates:
            self.assertTrue(tax.country_id, tax.name)
            self.assertTrue(tax.tax_group_id.country_id, tax.name)
            self.assertEqual(
                tax.company_id, tax.tax_group_id.company_id, tax.name,
            )
            self.assertEqual(
                tax.country_id, tax.tax_group_id.country_id, tax.name,
            )

        rows_before = self.env[
            'shopify.connector.tax.mapping'
        ].search_count([])
        audits_before = self.env['shopify.connector.job'].search_count([
            ('job_type', '=', 'core_manual_maintenance'),
        ])
        for index, tax in enumerate(candidates):
            evidence = self._evidence(title='Unsafe %d' % index)
            with self.assertRaises(ValidationError, msg=tax.name):
                with self.env.cr.savepoint():
                    self._mapping(
                        tax=tax, evidence=evidence, included=False,
                        user=self.roles['admin'],
                    )
            self.assertEqual(
                self.env['shopify.connector.tax.mapping'].search_count([]),
                rows_before,
            )
            self.assertEqual(self.env['shopify.connector.job'].search_count([
                ('job_type', '=', 'core_manual_maintenance'),
            ]), audits_before)

    def test_explicit_mapping_only_resolution(self):
        evidence = self._evidence()
        order = self._order()
        tax = self._tax()
        with self.assertRaises(JobHandlerError) as missing:
            self.Importer._resolve_taxes(
                order, self.store, [evidence], False, self.settings,
            )
        self.assertEqual(
            missing.exception.error_class, 'odoo_validation_configuration',
        )
        detail = json.loads(missing.exception.technical_detail)
        self.assertIn(tax.id, detail['suggested_account_tax_ids'])
        self.assertEqual(
            detail['suggestion_basis'],
            'rate_and_inclusion_only_non_binding',
        )
        self.assertFalse(self.env['shopify.connector.tax.mapping'].search([]))
        self._mapping(tax=tax, evidence=evidence)
        taxes, rate, signatures = self.Importer._resolve_taxes(
            order, self.store, [evidence], False, self.settings,
        )
        self.assertEqual(taxes, tax)
        self.assertEqual(str(rate), '5')
        self.assertEqual(signatures, (self._key(evidence),))

    def test_mapping_key_shape_and_uniqueness(self):
        tax = self._tax()
        with self.assertRaises(ValidationError):
            self.env['shopify.connector.tax.mapping'].create({
                'store_id': self.store.id,
                'shopify_tax_evidence_key': 'not-a-full-key',
                'account_tax_id': tax.id,
            })
        mapping = self._mapping(tax=tax)
        original_company = self.settings.order_company_id
        other_company = self.env['res.company'].sudo().create({
            'name': 'Order Tax Mapping Immutable Company',
        })
        with self.assertRaises(ValidationError):
            self.settings.write({'order_company_id': other_company.id})
        self.assertEqual(self.settings.order_company_id, original_company)
        self.assertTrue(mapping.exists())
        with self.assertRaises(IntegrityError):
            with self.env.cr.savepoint():
                self._mapping(tax=tax)
