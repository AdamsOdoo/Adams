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

    def _quantity_invoice(self, quantity, move_type='out_invoice', invoice_date='2026-08-15'):
        invoice = self.env['account.move'].create({
            'move_type': move_type, 'partner_id': self.partner_a.id,
            'invoice_date': invoice_date, 'date': invoice_date,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id,
                'quantity': quantity, 'price_unit': 100,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.clear()]})],
        })
        invoice.action_post()
        return invoice

    def test_fulfillment_invalid_page_returns_validation_error(self):
        for offset in (-1, True, '25'):
            with self.subTest(offset=offset), self.assertRaises(ValidationError):
                self.dashboard.get_fulfillment(self.options, offset)

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
        company = self.env['res.company'].create({'name': 'Dashboard secondary identity fixture'})
        self.env.user.company_ids = [Command.link(company.id)]
        result = self.dashboard.with_context(allowed_company_ids=[company.id, self.env.company.id]).get_bootstrap()
        self.assertEqual(result['options']['company_id'], company.id)
        self.assertEqual({entry['id'] for entry in result['companies']}, {company.id, self.env.company.id})

    def test_recent_invoices_reuse_posted_document_scope_and_exact_record_actions(self):
        invoice = self._quantity_invoice(3)
        credit = self._quantity_invoice(1, 'out_refund')
        vendor = self._quantity_invoice(5, 'in_invoice')
        outside = self._quantity_invoice(2, invoice_date='2026-09-01')
        draft = invoice.copy()
        cancelled = invoice.copy()
        cancelled.button_cancel()
        result = self.dashboard.get_recent_sales('invoices', self.options)
        self.assertEqual({row['id'] for row in result['rows']}, {invoice.id, credit.id})
        self.assertEqual(result['date_basis'], 'invoice_date')
        for row in result['rows']:
            record = self.env['account.move'].browse(row['id'])
            self.assertEqual(row['res_model'], 'account.move')
            self.assertEqual(row['state'], 'posted')
            self.assertEqual(row['amount_untaxed'], record.amount_untaxed)
            self.assertEqual(row['currency'], record.currency_id.name)
            self.assertTrue(row['document_type_label'])
            action = self.dashboard.open_recent_sale('invoices', self.options, row['id'])
            self.assertEqual(action['res_model'], 'account.move')
            self.assertEqual(action['res_id'], record.id)
        report = self.dashboard.open_recent_sale('invoices', self.options)
        self.assertEqual(set(self.env['account.move'].search(report['domain']).ids), {invoice.id, credit.id})
        for excluded in (vendor, outside, draft, cancelled):
            with self.assertRaises(AccessError):
                self.dashboard.open_recent_sale('invoices', self.options, excluded.id)
        with self.assertRaises(ValidationError):
            self.dashboard.open_recent_sale('invoices', self.options, True)
        reader = new_test_user(self.env, login='recent_invoice_dashboard_only',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).get_recent_sales('invoices', self.options)

    def test_recent_six_row_pages_recover_after_scope_shrinks(self):
        invoices = [self._quantity_invoice(1) for _ in range(8)]
        first = self.dashboard.get_recent_sales('invoices', self.options, page_size=6)
        second = self.dashboard.get_recent_sales('invoices', self.options, offset=6, page_size=6)
        self.assertEqual((first['total_count'], len(first['rows']), first['has_more']), (8, 6, True))
        self.assertEqual((second['offset'], len(second['rows']), second['has_more']), (6, 2, False))
        self.assertEqual({row['id'] for row in first['rows'] + second['rows']}, {record.id for record in invoices})
        for invoice in invoices[:3]:
            invoice.button_draft()
        recovered = self.dashboard.get_recent_sales('invoices', self.options, offset=6, page_size=6)
        self.assertEqual((recovered['offset'], recovered['total_count'], len(recovered['rows'])), (0, 5, 5))
        empty = self.dashboard.get_recent_sales('invoices', {**self.options, 'date_from':'2026-08-01', 'date_to':'2026-08-02'}, offset=6, page_size=6)
        self.assertEqual((empty['offset'], empty['total_count'], empty['status']), (0, 0, 'empty'))
        for invalid in (True, 0, 7, '6'):
            with self.subTest(page_size=invalid), self.assertRaises(ValidationError):
                self.dashboard.get_recent_sales('invoices', self.options, page_size=invalid)
