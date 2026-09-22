"""Quantity drilldown and standard company identity regressions."""
from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestDashboardSourceIdentity(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}

    def _quantity_invoice(self, quantity, move_type='out_invoice'):
        invoice = self.env['account.move'].create({
            'move_type': move_type, 'partner_id': self.partner_a.id,
            'invoice_date': '2026-08-15', 'date': '2026-08-15',
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id,
                'quantity': quantity, 'price_unit': 100,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.clear()]})],
        })
        invoice.action_post()
        return invoice

    def test_quantity_action_matches_signed_native_ranking_and_measure(self):
        self._quantity_invoice(68)
        self._quantity_invoice(2, 'out_refund')
        self.env.flush_all()
        unit_id = self.product_a.uom_id.id
        ranking = self.dashboard.get_product_quantity_ranking(self.options, unit_id)
        value = next(row['value'] for row in ranking['rows'] if row['id'] == self.product_a.id)
        action = self.dashboard.open_product_quantity_report(self.options, self.product_a.id, unit_id)
        self.assertEqual(action['context']['pivot_measures'], ['quantity'])
        self.assertEqual(action['context']['graph_measure'], 'quantity')
        self.assertIn(('product_uom_id', '=', unit_id), action['domain'])
        source = self.env['account.invoice.report'].search(action['domain'])
        self.assertAlmostEqual(sum(source.mapped('quantity')), value)
        self.assertAlmostEqual(value, 66)
        self.assertNotAlmostEqual(sum(source.mapped('price_subtotal')), value)

    def test_quantity_action_rejects_invalid_units_products_and_access(self):
        with self.assertRaises(ValidationError):
            self.dashboard.open_product_quantity_report(self.options, unit_id=True)
        with self.assertRaises(ValidationError):
            self.dashboard.open_product_quantity_report(self.options, product_id=True)
        with self.assertRaises(AccessError):
            self.dashboard.open_product_quantity_report(self.options, product_id=self.product_a.id)
        outsider = new_test_user(self.env, login='quantity_source_outsider', groups='base.group_user')
        with self.assertRaises(AccessError):
            self.dashboard.with_user(outsider).open_product_quantity_report(self.options)

    def test_bootstrap_uses_standard_company_name_and_refreshes_after_edit(self):
        company = self.env.company
        company.name = 'شركة Example & Company'
        first = self.dashboard.get_bootstrap()
        identity = next(row for row in first['companies'] if row['id'] == company.id)
        self.assertEqual(identity['name'], company.name)
        self.assertEqual(first['options']['company_id'], company.id)
        self.assertEqual(identity['initials'], 'شE')
        if identity['logo_url']:
            self.assertTrue(identity['logo_url'].startswith(f'/web/image/res.company/{company.id}/logo?unique='))
        company.name = 'Updated company'
        second = self.dashboard.get_bootstrap()
        self.assertEqual(next(row['name'] for row in second['companies'] if row['id'] == company.id), 'Updated company')

    def test_company_metadata_respects_active_company_context(self):
        company = self.company_data_2['company']
        result = self.dashboard.with_context(allowed_company_ids=[company.id, self.env.company.id]).get_bootstrap()
        self.assertEqual(result['options']['company_id'], company.id)
        self.assertEqual({entry['id'] for entry in result['companies']}, {company.id, self.env.company.id})
