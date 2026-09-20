from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import file_open
from odoo.tools.translate import code_translations
import sass
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestExecutiveDashboard(AccountTestInvoicingCommon):
    def test_arabic_web_catalog_is_loaded_by_odoo(self):
        messages = code_translations.get_web_translations('adams_executive_dashboard', 'ar_001')['messages']
        translations = {message['id']: message['string'] for message in messages}
        # Exercise Odoo's actual loader: syntactically valid PO files without
        # odoo-javascript markers silently produced an English dashboard.
        for source in ('Finance', 'Business overview', 'Apply filters', 'Recent orders',
                       'Explore delivery quantities', 'Not configured'):
            with self.subTest(source=source):
                self.assertTrue(translations.get(source))
                self.assertNotEqual(translations[source], source)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}
        cls.reader = new_test_user(
            cls.env, login='dashboard_reader',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=cls.env.company.id, company_ids=[Command.set(cls.env.company.ids)],
        )

    def _invoice(self, amount, move_type='out_invoice', invoice_date='2026-08-15', post=True):
        move = self.env['account.move'].create({
            'move_type': move_type, 'partner_id': self.partner_a.id,
            'invoice_date': invoice_date, 'date': invoice_date,
            'journal_id': self.company_data['default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'name': 'Dashboard fixture', 'quantity': 1, 'price_unit': amount,
                'account_id': self.company_data['default_account_revenue'].id,
                'tax_ids': [Command.clear()],
            })],
        })
        if post:
            move.action_post()
        return move

    def test_dashboard_permission_required_on_every_rpc(self):
        outsider = new_test_user(self.env, login='dashboard_outsider', groups='base.group_user')
        dashboard = self.dashboard.with_user(outsider)
        for method, args in [('get_bootstrap', []), ('get_section', ['sales', self.options]),
                             ('open_report', ['invoiced_sales', self.options]),
                             ('get_breakdown', ['invoiced_sales', 'customer', self.options]),
                             ('get_trend', ['invoiced_sales', self.options]),
                             ('export_breakdown', ['invoiced_sales', 'customer', self.options]),
                             ('get_cash_directory', [self.options]), ('get_inventory', [self.options]),
                             ('open_inventory', [self.options]), ('get_fulfillment', [self.options]),
                             ('open_fulfillment', [self.options]), ('get_recent_sales', ['orders', self.options]),
                             ('open_recent_sale', ['orders', self.options])]:
            with self.assertRaises(AccessError):
                getattr(dashboard, method)(*args)

    def test_company_and_filter_validation(self):
        foreign = self.env['res.company'].create({'name': 'Unauthorized dashboard company'})
        dashboard = self.dashboard.with_user(self.reader)
        with self.assertRaises(AccessError):
            dashboard.get_section('sales', dict(self.options, company_id=foreign.id))
        with self.assertRaises(ValidationError):
            dashboard.get_section('sales', dict(self.options, domain=[]))
        with self.assertRaises(ValidationError):
            dashboard.get_section('sales', dict(self.options, date_to='2026-07-01'))
        with self.assertRaises(ValidationError):
            dashboard.open_report('account.move', self.options)

    def test_dashboard_group_does_not_grant_accounting(self):
        result = self.dashboard.with_user(self.reader).get_section('sales', self.options)
        item = next(item for item in result['items'] if item['key'] == 'invoiced_sales')
        self.assertEqual(item['status'], 'restricted')
        self.assertIsNone(item['value'])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).open_report('invoiced_sales', self.options)

    def test_unconfigured_finance_never_returns_zero(self):
        result = self.dashboard.get_section('finance', self.options)
        self.assertTrue({'revenue', 'profit', 'cash', 'receivables', 'payables'}.issubset(
            {item['key'] for item in result['items']}))
        for item in result['items']:
            self.assertEqual(item['status'], 'not_configured')
            self.assertIsNone(item['value'])

    def test_native_invoiced_sales_refunds_drafts_and_period(self):
        self._invoice(100)
        self._invoice(25, move_type='out_refund')
        self._invoice(999, post=False)
        self._invoice(777, invoice_date='2026-09-01')
        result = self.dashboard.get_section('sales', self.options)
        item = next(item for item in result['items'] if item['key'] == 'invoiced_sales')
        self.assertEqual(item['status'], 'ready')
        self.assertAlmostEqual(item['value'], 75, places=2)
        action = self.dashboard.open_report('invoiced_sales', self.options)
        native = self.env['account.invoice.report'].search(action['domain'])
        self.assertAlmostEqual(sum(native.mapped('price_subtotal')), 75, places=2)
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
        self.assertFalse(any(key.startswith('search_default_') for key in action['context']))

    def test_empty_report_is_not_a_zero_balance(self):
        result = self.dashboard.get_section('sales', dict(self.options, date_from='2090-01-01', date_to='2090-01-31'))
        item = next(item for item in result['items'] if item['key'] == 'invoiced_sales')
        self.assertEqual(item['status'], 'empty')
        self.assertIsNone(item['value'])

    def test_permission_revocation_applies_without_cache(self):
        self.reader.group_ids = [Command.clear(), Command.link(self.env.ref('base.group_user').id)]
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).get_section('finance', self.options)

    def test_grouped_native_values_and_trend_preserve_refund_sign(self):
        self._invoice(100)
        self._invoice(25, move_type='out_refund')
        grouped = self.dashboard.get_breakdown('invoiced_sales', 'customer', self.options)
        self.assertEqual(len(grouped['rows']), 1)
        self.assertEqual(grouped['rows'][0]['id'], self.partner_a.commercial_partner_id.id)
        self.assertAlmostEqual(grouped['rows'][0]['value'], 75)
        trend = self.dashboard.get_trend('invoiced_sales', self.options)
        self.assertEqual(trend['rows'], [{'label': '2026-08', 'value': 75.0}])
        action = self.dashboard.open_report('invoiced_sales', self.options, 'customer', self.partner_a.commercial_partner_id.id)
        self.assertIn(('commercial_partner_id', '=', self.partner_a.commercial_partner_id.id), action['domain'])

    def test_native_scope_rejects_client_report_context(self):
        clean = self.dashboard.get_trend('invoiced_sales', self.options)
        injected = self.dashboard.with_context(tz='Pacific/Honolulu', active_test=False, to_date='1900-01-01').get_trend('invoiced_sales', self.options)
        self.assertEqual(clean['provenance'], injected['provenance'])
        with self.assertRaises(ValidationError):
            self.dashboard.get_breakdown('invoiced_sales', 'bank_account_id', self.options)
        with self.assertRaises(ValidationError):
            self.dashboard.get_breakdown('invoiced_sales', 'customer', self.options, offset=-1)

    def test_export_permission_and_formula_safety(self):
        self.partner_a.name = '=HYPERLINK("https://example.invalid")'
        self._invoice(100)
        result = self.dashboard.export_breakdown('invoiced_sales', 'customer', self.options)
        self.assertEqual(result['row_count'], 1)
        self.assertIn("'=HYPERLINK", result['content'])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).export_breakdown('invoiced_sales', 'customer', self.options)

    def test_cash_discovery_tracks_configuration_without_guessed_balances(self):
        account = self.env['account.account'].create({
            'name': 'Dashboard cash fixture', 'code': '991010', 'account_type': 'asset_cash',
            'company_ids': [Command.set(self.env.company.ids)],
        })
        def find_account():
            offset = 0
            while True:
                page = self.dashboard.get_cash_directory(self.options, offset)
                for row in page['rows']:
                    if row['id'] == account.id:
                        return row
                if not page['has_more']:
                    self.fail('New eligible cash account was not discovered')
                offset += 25
        self.assertIsNone(find_account()['balance'])
        account.write({'name': 'Renamed dashboard cash', 'active': False})
        row = find_account()
        self.assertEqual(row['name'], 'Renamed dashboard cash')
        self.assertFalse(row['active'])

    def test_dashboard_styles_compile_with_odoo_sass(self):
        with file_open('adams_executive_dashboard/static/src/dashboard.scss') as source:
            compiled = sass.compile(string=source.read())
        self.assertIn('.o_adams_dashboard', compiled)
