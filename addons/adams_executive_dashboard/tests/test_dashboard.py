from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.tools import file_open
from odoo.tools.translate import code_translations
import sass
import csv
import io
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestExecutiveDashboard(AccountTestInvoicingCommon):
    def test_arabic_web_catalog_is_loaded_by_odoo(self):
        messages = code_translations.get_web_translations('adams_executive_dashboard', 'ar_001')['messages']
        translations = {message['id']: message['string'] for message in messages}
        server = code_translations.get_python_translations('adams_executive_dashboard', 'ar_001')
        for source in ('Accounting & Finance', 'Accounting revenue', 'Net cash movement', 'Sales', 'Operations', 'Count', 'Hours'):
            self.assertTrue(server.get(source))
            self.assertNotEqual(server[source], source)
        # Exercise Odoo's actual loader: syntactically valid PO files without
        # odoo-javascript markers silently produced an English dashboard.
        for source in ('Finance', 'Business overview', 'Apply filters', 'Recent orders',
                       'Explore delivery quantities', 'Not configured',
                       'View bills →', 'View overdue receivables →', 'Approvals & late receipts →',
                       'Search results', 'Print preview', 'Valuation:', 'Active employees:',
                       'Budget:', 'Matching orders:', 'Sold product ranking', 'Dashboard Settings'):
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
        for method, args in [('search_records', ['Test', self.options]), ('open_search_record', ['Test', self.options, 'invoices', 1]),
                             ('export_summary', [self.options]), ('get_bootstrap', []), ('get_section', ['sales', self.options]),
                             ('open_report', ['invoiced_sales', self.options]),
                             ('get_breakdown', ['invoiced_sales', 'customer', self.options]),
                             ('get_trend', ['invoiced_sales', self.options]),
                             ('export_breakdown', ['invoiced_sales', 'customer', self.options]),
                             ('get_cash_directory', [self.options]), ('get_inventory', [self.options]),
                             ('open_inventory', [self.options]), ('get_workforce', [self.options]), ('get_procurement', [self.options]),
                             ('open_procurement', [self.options]),
                             ('open_workforce', [self.options]), ('open_inventory_product', [self.options, 1, 'forecast']), ('get_fulfillment', [self.options]),
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
            stylesheet = source.read()
        # This variable is supplied by Odoo's native primary-variable bundles.
        for scheme in ('bright', 'dark'):
            compiled = sass.compile(string=f'$o-webclient-color-scheme: {scheme};\n' + stylesheet)
            self.assertIn('.o_adams_dashboard', compiled)
            self.assertIn('color-scheme: ' + ('dark' if scheme == 'dark' else 'light'), compiled)

    def test_cash_directory_search_counts_pages_and_archived_records(self):
        accounts = self.env['account.account'].create([{
            'name': f'Searchable dashboard cash {index:02}', 'code': f'992{index:03}',
            'account_type': 'asset_cash', 'company_ids': [Command.set(self.env.company.ids)],
        } for index in range(27)])
        accounts[-1].active = False
        first = self.dashboard.get_cash_directory(self.options, 0, 'Searchable dashboard cash')
        second = self.dashboard.get_cash_directory(self.options, 25, 'Searchable dashboard cash')
        self.assertEqual(first['total_count'], 26)
        self.assertEqual(len(first['rows']), 25)
        self.assertTrue(first['has_more'])
        self.assertEqual({row['id'] for row in first['rows'] + second['rows']}, set(accounts[:-1].ids))
        self.assertFalse(second['has_more'])
        self.assertEqual(len(second['rows']), 1)
        self.assertTrue(second['rows'][0]['active'])
        exact = self.dashboard.get_cash_directory(self.options, 0, accounts[-1].code)
        self.assertEqual(exact['total_count'], 0)
        self.assertEqual(exact['rows'], [])
        for invalid in (None, {}, ['cash'], 'x' * 101):
            with self.assertRaises(ValidationError):
                self.dashboard.get_cash_directory(self.options, 0, invalid)

    def test_workspace_search_scope_and_access(self):
        included = self._invoice(100)
        draft = self._invoice(999, post=False)
        outside = self._invoice(777, invoice_date='2026-09-01')
        result = self.dashboard.search_records(self.partner_a.name, self.options, 'invoices')
        ids = [row['id'] for row in result['groups'][0]['rows']]
        self.assertIn(included.id, ids)
        self.assertNotIn(draft.id, ids)
        self.assertNotIn(outside.id, ids)
        action = self.dashboard.open_search_record(self.partner_a.name, self.options, 'invoices', included.id)
        self.assertEqual(action['res_id'], included.id)
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
        with self.assertRaises(AccessError):
            self.dashboard.open_search_record(self.partner_a.name, self.options, 'invoices', outside.id)
        restricted = self.dashboard.with_user(self.reader).search_records(self.partner_a.name, self.options, 'invoices')
        self.assertEqual(restricted['groups'][0]['status'], 'restricted')
        self.assertFalse(restricted['groups'][0]['rows'])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).open_search_record(self.partner_a.name, self.options, 'invoices', included.id)
        with self.assertRaises(ValidationError):
            self.dashboard.search_records('a', self.options)
        with self.assertRaises(ValidationError):
            self.dashboard.search_records('Test', self.options, 'res.users')
        with self.assertRaises(ValidationError):
            self.dashboard.search_records('Test', self.options, offset=-1)
        foreign = self.env['res.company'].create({'name': 'Search forbidden company'})
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).search_records('Test', dict(self.options, company_id=foreign.id))

    def test_summary_native_values_unavailable_states_and_export_access(self):
        self._invoice(100)
        self._invoice(25, move_type='out_refund')
        self.env.company.name = '=UNTRUSTED()'
        result = self.dashboard.export_summary(self.options)
        rows = list(csv.DictReader(io.StringIO(result['content'].lstrip('\ufeff'))))
        sales = next(row for row in rows if row['Metric'] == 'Net invoiced sales')
        self.assertEqual(float(sales['Value']), 75)
        printed = next(row for row in result['print_rows'] if row['metric'] == 'Net invoiced sales')
        self.assertEqual(printed['value'], 75)
        self.assertEqual(result['scope'], self.options)
        self.assertEqual(sales['Company'], "'=UNTRUSTED()")
        self.assertEqual(sales['From'], '2026-08-01')
        self.assertTrue(sales['Scope fingerprint'])
        self.assertEqual(sales['Source'], 'account.invoice.report')
        finance = next(row for row in rows if row['Metric'] == 'Accounting revenue')
        self.assertEqual(finance['Value'], '')
        self.assertEqual(finance['Status'], 'not_configured')
        arabic = self.dashboard.with_context(lang='ar_001').export_summary(self.options)
        self.assertIn('المؤشر', arabic['content'])
        self.assertIn('المبيعات', arabic['content'])
        self.assertIn('الإيرادات المحاسبية', arabic['content'])
        self.assertNotIn('Accounting revenue', arabic['content'])
        self.assertTrue(any(row['metric'] == 'الإيرادات المحاسبية' for row in arabic['print_rows']))
        self.reader.group_ids -= self.env.ref('base.group_allow_export')
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).export_summary(self.options)


    def test_company_section_settings_persist_and_scope_summary(self):
        action = self.env.ref('adams_executive_dashboard.action_dashboard_settings')
        self.assertEqual(action.target, 'current')
        company = self.env.company
        company.adams_dashboard_hr = False
        self.assertNotIn('hr', self.dashboard._visible_sections())
        settings = self.env['res.config.settings'].create({'company_id': company.id})
        settings.write({'adams_dashboard_sales': False})
        self.assertFalse(company.adams_dashboard_sales)
        bootstrap = self.dashboard.with_user(self.reader).get_bootstrap()
        current = next(c for c in bootstrap['companies'] if c['id'] == company.id)
        self.assertNotIn('hr', current['enabled_sections'])
        self.assertNotIn('sales', current['enabled_sections'])
        self.assertFalse(bootstrap['can_configure'])
        self.assertFalse(self.dashboard.get_section('sales', self.options)['items'])
        self.assertFalse(any(i['key'] == 'hr' for i in self.dashboard.get_section('operations', self.options)['items']))
        summary = self.dashboard.export_summary(self.options)
        self.assertFalse(any(row['section'] == 'Sales' for row in summary['print_rows']))
        foreign = self.env['res.company'].create({'name': 'Independent visibility company'})
        self.assertIn('hr', self.dashboard._visible_sections(foreign))
        self.assertIn('sales', self.dashboard._visible_sections(foreign))
        with self.assertRaises(AccessError):
            company.with_user(self.reader).write({'adams_dashboard_hr': True})
        settings.write({'adams_dashboard_sales': True})
        self.assertIn('sales', self.dashboard._visible_sections())

    def test_product_ranking_native_refunds_dates_and_drilldown(self):
        products = self.env['product.product'].create([{'name':'Ranked product A'}, {'name':'Ranked product B'}])
        for product, amount, kind, when, post in [(products[0],100,'out_invoice','2026-08-15',True),
                (products[0],25,'out_refund','2026-08-15',True),
                (products[1],10,'out_refund','2026-08-15',True),
                (products[1],999,'out_invoice','2026-09-01',True),
                (products[1],999,'out_invoice','2026-08-15',False)]:
            move = self._invoice(amount, kind, when, post=False)
            move.invoice_line_ids.write({'product_id': product.id, 'price_unit': amount, 'tax_ids': [Command.clear()]})
            if post:
                move.action_post()
        products[0].active = False
        groups = self.dashboard.get_breakdown('invoiced_sales','product',self.options)
        values = {row['id']:row['value'] for row in groups['rows']}
        self.assertEqual(values[products[0].id],75)
        self.assertEqual(values[products[1].id],-10)
        self.assertLess(next(i for i,r in enumerate(groups['rows']) if r['id']==products[0].id),
                        next(i for i,r in enumerate(groups['rows']) if r['id']==products[1].id))
        action = self.dashboard.open_report('invoiced_sales',self.options,'product',products[0].id)
        self.assertIn(('product_id','=',products[0].id),action['domain'])
        self.assertIn(('state','=','posted'),action['domain'])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).get_breakdown('invoiced_sales','product',self.options)

    def test_product_quantity_ranking_retains_refunds_and_separates_units(self):
        products = self.env['product.product'].create([
            {'name': 'Quantity units', 'uom_id': self.env.ref('uom.product_uom_unit').id},
            {'name': 'Quantity weight', 'uom_id': self.env.ref('uom.product_uom_kgm').id},
        ])
        for product, quantity, kind in [(products[0], 8, 'out_invoice'), (products[0], 3, 'out_refund'),
                                         (products[1], 100, 'out_invoice')]:
            move = self._invoice(10, kind, post=False)
            move.invoice_line_ids.write({'product_id': product.id, 'product_uom_id': product.uom_id.id,
                'quantity': quantity, 'price_unit': 10, 'tax_ids': [Command.clear()]})
            move.action_post()
        self.env.flush_all()
        result = self.dashboard.get_product_quantity_ranking(self.options, products[0].uom_id.id)
        self.assertEqual(result['rows'], [{'id': products[0].id, 'label': products[0].display_name, 'value': 5}])
        self.assertEqual({u['id'] for u in result['units']}, set(products.mapped('uom_id').ids))
        weighted = self.dashboard.get_product_quantity_ranking(self.options, products[1].uom_id.id)
        self.assertEqual(weighted['rows'][0]['value'], 100)
        with self.assertRaises(AccessError):
            self.dashboard.with_user(self.reader).get_product_quantity_ranking(self.options)
        with self.assertRaises(ValidationError):
            self.dashboard.get_product_quantity_ranking(self.options, True)
