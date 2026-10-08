import ast
import json
from urllib.parse import quote
from unittest.mock import patch

from odoo import api
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

from odoo.addons.adams_pos_sales_report.models import report_pos_order as psr

ACTION_DOMAIN = [('state', 'in', ('paid', 'done'))]


@tagged('post_install', '-at_install')
class TestPosSalesReport(TestPoSCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.basic_config
        cls.coffee = cls.create_product('PSR Coffee', cls.categ_basic, 100.0, 60.0, tax_ids=cls.taxes['tax9'].ids)
        cls.water = cls.create_product('PSR Water', cls.categ_basic, 50.0, 20.0)
        cls.sara = cls.env['hr.employee'].sudo().create({'name': 'Sara Cashier'})
        cls.manager = new_test_user(cls.env, login='psr_manager', groups='point_of_sale.group_pos_manager')
        cls.pos_user = new_test_user(cls.env, login='psr_user', groups='point_of_sale.group_pos_user')

    def setUp(self):
        super().setUp()
        self.session = self.open_new_session()
        orders = self._create_orders([
            # A: Sara, 2 coffees at 10% discount, paid cash: net 180, tax 16.20.
            {'pos_order_lines_ui_args': [(self.coffee, 2, 10)], 'uuid': 'psr-a'},
            # B: no employee, 3 waters, paid 100 cash + 50 bank.
            {'pos_order_lines_ui_args': [(self.water, 3)], 'uuid': 'psr-b',
             'payments': [(self.cash_pm1, 100.0), (self.bank_pm1, 50.0)]},
            # R: Sara, one coffee returned: net -100, tax -9.
            {'pos_order_lines_ui_args': [(self.coffee, -1)], 'uuid': 'psr-r',
             'payments': [(self.cash_pm1, -109.0)]},
        ])
        self.order_a, self.order_b, self.order_r = orders['psr-a'], orders['psr-b'], orders['psr-r']
        (self.order_a | self.order_r).employee_id = self.sara
        self.draft = self.env['pos.order'].create({
            'session_id': self.session.id,
            'amount_total': 50.0, 'amount_tax': 0.0, 'amount_paid': 0.0, 'amount_return': 0.0,
            'lines': [(0, 0, {'product_id': self.water.id, 'qty': 1, 'price_unit': 50.0,
                              'price_subtotal': 50.0, 'price_subtotal_incl': 50.0})],
        })
        self.env.flush_all()
        self.domain = [('session_id', '=', self.session.id)] + ACTION_DOMAIN
        self.Report = self.env['report.pos.order'].with_user(self.manager)

    def _options(self, groupby=(), columns=psr.PSR_COLUMNS, mode='summary', filters=None):
        return self.Report._psr_options(self.domain, list(groupby), list(columns), mode, filters)

    # A2, A3, A4: one row per sold line, employee with fallback, refunds negative.
    def test_lines_columns(self):
        lines = self.Report.search(self.domain)
        self.assertEqual(len(lines), 3, "the draft order is left out")
        line_a = lines.filtered(lambda l: l.order_id == self.order_a)
        line_b = lines.filtered(lambda l: l.order_id == self.order_b)
        line_r = lines.filtered(lambda l: l.order_id == self.order_r)
        self.assertEqual(line_a.cashier, 'Sara Cashier')
        self.assertEqual(line_b.cashier, self.order_b.user_id.name, "no employee: the order's user")
        self.assertEqual((line_a.qty, line_a.price_unit, line_a.total_discount), (2.0, 100.0, 20.0))
        self.assertAlmostEqual(line_a.price_subtotal_excl, 180.0)
        self.assertAlmostEqual(line_a.tax_amount, 16.2)
        self.assertAlmostEqual(line_a.tax_amount, line_a.price_total - line_a.price_subtotal_excl)
        self.assertTrue(line_r.is_refund)
        self.assertFalse(line_a.is_refund)
        self.assertAlmostEqual(line_r.price_total, -109.0)

    # A2: the action shows sales only (paid and posted).
    def test_action_excludes_draft_orders(self):
        action = self.env.ref('adams_pos_sales_report.action_pos_sales_report')
        domain = [('session_id', '=', self.session.id)] + ast.literal_eval(action.domain)
        self.assertNotIn(self.draft, self.Report.search(domain).order_id)

    # A6: the figures are those of the orders themselves (same source as Orders Analysis).
    def test_totals_match_orders(self):
        orders = self.order_a | self.order_b | self.order_r
        data = self.Report._psr_report_data(self._options())
        self.assertAlmostEqual(data['totals']['price_total'], sum(orders.mapped('amount_total')))
        self.assertAlmostEqual(data['totals']['tax_amount'], sum(orders.mapped('amount_tax')))
        self.assertEqual(data['kpis']['orders'], 2, "the refund order is not a sale")
        self.assertAlmostEqual(data['kpis']['refunds'], -109.0)
        self.assertAlmostEqual(data['kpis']['average'], data['totals']['price_total'] / 2)

    # A1: POS Administrators only, both for the button and the report URL.
    def test_access_pos_user_denied(self):
        with self.assertRaises(AccessError):
            self.env['report.pos.order'].with_user(self.pos_user).action_print_sales_report(self.domain, [], [], 'summary')
        with self.assertRaises(AccessError):
            self.env['report.adams_pos_sales_report.report_pos_sales'].with_user(self.pos_user)._get_report_values(
                [], {'domain': self.domain, 'groupby': [], 'columns': [], 'mode': 'summary'})
        action = self.Report.action_print_sales_report(self.domain, ['cashier'], ['qty'], 'summary', ['Order Date: October 2026'])
        self.assertEqual(action['type'], 'ir.actions.report')
        self.assertEqual(action['data']['groupby'], ['cashier'])

    # A7: summary follows the grouping and the visible columns.
    def test_summary_groups(self):
        data = self.Report._psr_report_data(self._options(['cashier', 'product_id'], ['product_id', 'qty', 'price_unit', 'price_total']))
        self.assertEqual(data['mode'], 'summary')
        self.assertEqual([c['name'] for c in data['value_columns']], ['qty', 'price_total'], "unit price is not summed")
        self.assertEqual(data['label_columns'], [])
        by_label = {g['label']: g for g in data['groups']}
        sara = by_label['Sara Cashier']
        self.assertEqual(sara['count'], 2)
        self.assertAlmostEqual(sara['sums']['price_total'], 196.2 - 109.0)
        self.assertEqual([c['label'] for c in sara['children']], [self.coffee.display_name])
        self.assertFalse(sara['children'][0]['lines'], "summary prints no lines")
        self.assertEqual(data['grouping'], ['Employee', 'Product'])

    # A7: detailed prints the lines under their group, without the grouped column.
    def test_detailed_lines(self):
        data = self.Report._psr_report_data(self._options(['date:day'], ['date', 'order_id', 'product_id', 'price_total'], 'detailed'))
        self.assertEqual([c['name'] for c in data['label_columns']], ['order_id', 'product_id'])
        self.assertEqual(len(data['groups']), 1)
        lines = data['groups'][0]['lines']
        self.assertEqual(len(lines), 3)
        self.assertEqual(sorted(l['is_refund'] for l in lines), [False, False, True])
        # No grouping: Detailed lists every line, Summary only the figures and totals.
        data = self.Report._psr_report_data(self._options([], ['product_id', 'qty'], 'detailed'))
        self.assertEqual(len(data['lines']), 3)
        data = self.Report._psr_report_data(self._options([], ['product_id', 'qty']))
        self.assertEqual((data['mode'], data['lines'], data['groups']), ('summary', [], []))
        self.assertAlmostEqual(data['totals']['qty'], 4.0)

    # A7: payments come from the payments: a split order appears under both methods.
    def test_payments_and_taxes(self):
        data = self.Report._psr_report_data(self._options())
        payments = {p['name']: p for p in data['payments']}
        self.assertAlmostEqual(payments[self.bank_pm1.display_name]['amount'], 50.0)
        self.assertEqual(payments[self.bank_pm1.display_name]['count'], 1)
        self.assertAlmostEqual(sum(p['amount'] for p in data['payments']), data['totals']['price_total'])
        taxes = {t['name']: t for t in data['taxes']}
        tax9 = taxes[self.taxes['tax9'].name]
        self.assertAlmostEqual(tax9['base_amount'], 80.0)
        self.assertAlmostEqual(tax9['tax_amount'], 7.2)

    # A8: what the browser sends is validated.
    def test_invalid_input(self):
        options = self._options([], ['qty', 'name', 'partner_id.email'])
        self.assertEqual(options['columns'], ['qty'], "unknown columns are dropped")
        for groupby in (['no_such_field'], ['date'], ['cashier:day'], ['id']):
            with self.subTest(groupby=groupby), self.assertRaises(UserError):
                self._options(groupby)
        with self.assertRaises(UserError):
            self._options(mode='everything')
        with self.assertRaises(UserError):
            self.Report._psr_options("[('id', '>', 0)]", [], [], 'summary', None)

    # A11: a detailed print over the limit is refused with a clear message; summary still works.
    def test_detailed_limit(self):
        with patch.object(psr, 'PSR_MAX_LINES', 2):
            with self.assertRaises(UserError):
                self.Report.action_print_sales_report(self.domain, ['cashier'], [], 'detailed')
            action = self.Report.action_print_sales_report(self.domain, ['cashier'], [], 'summary')
            self.assertEqual(action['data']['mode'], 'summary')
            # Summary without grouping prints no lines, so the limit does not apply.
            html, _type = self.env['ir.actions.report'].with_user(self.manager)._render_qweb_html(
                'adams_pos_sales_report.action_report_pos_sales', [], data=self._options([], ['qty', 'price_total']))
            self.assertIn('Grand total', html.decode())

    # A1: the menu is for POS Administrators only.
    def test_menu_restricted(self):
        menu = self.env.ref('adams_pos_sales_report.menu_pos_sales_report')
        self.assertEqual(menu.group_ids, self.env.ref('point_of_sale.group_pos_manager'))

    # A6: amounts of different currencies are never added up under one currency.
    def test_several_currencies_refused(self):
        other = self.env['res.company'].create({'name': 'PSR Other Co', 'currency_id': self.other_currency.id})
        self.manager.company_ids |= other
        # Move one order to the other company at the database level: the view reads its currency from there.
        self.env.cr.execute("UPDATE pos_order SET company_id = %s WHERE id = %s", [other.id, self.order_b.id])
        self.env.invalidate_all()
        Report = self.Report.with_context(allowed_company_ids=[self.env.company.id, other.id])
        with self.assertRaises(UserError):
            Report.action_print_sales_report(self.domain, [], [], 'summary')
        # One company selected: its own currency is printed.
        Report = self.Report.with_context(allowed_company_ids=[other.id])
        data = Report._psr_report_data(Report._psr_options(self.domain, [], [], 'summary', None))
        self.assertEqual(data['currency'], self.other_currency)

    # A4, A7: a filtered print with nested groups renders the filtered lines only.
    def test_filtered_nested_print(self):
        domain = self.domain + [('is_refund', '=', False)]
        options = self.Report._psr_options(domain, ['cashier', 'product_id'], ['product_id', 'qty', 'price_total'], 'detailed', ['Exclude refunds'])
        data = self.Report._psr_report_data(options)
        self.assertFalse(data['kpis']['refunds'])
        self.assertAlmostEqual(data['totals']['price_total'], 196.2 + 150.0)
        html, _type = self.env['ir.actions.report'].with_user(self.manager)._render_qweb_html(
            'adams_pos_sales_report.action_report_pos_sales', [], data=options)
        html = html.decode()
        for text in ('Sara Cashier', self.coffee.display_name, self.water.display_name, 'Exclude refunds'):
            self.assertIn(text, html)

    # A7: the template renders the data (HTML; the PDF itself is checked on Odoo.sh).
    def test_render_html(self):
        options = self._options(['cashier'], ['product_id', 'qty', 'price_total'], 'detailed', ['Order Date: October 2026'])
        html, _type = self.env['ir.actions.report'].with_user(self.manager)._render_qweb_html(
            'adams_pos_sales_report.action_report_pos_sales', [], data=options)
        html = html.decode()
        for text in ('POS Sales Report', 'Sara Cashier', 'Order Date: October 2026', 'Grand total', self.bank_pm1.name):
            self.assertIn(text, html)
        # Landscape on the company's own paper format and document layout, also after an update.
        report = self.env.ref('adams_pos_sales_report.action_report_pos_sales')
        self.assertFalse(report.paperformat_id)
        self.assertEqual(report.get_paperformat(), self.env.company.paperformat_id or self.env.ref('base.paperformat_euro'))
        self.assertIn('data-report-landscape', html)


@tagged('post_install', '-at_install')
class TestPosSalesReportTour(HttpCase):

    # A1: the report URL refuses a POS user.
    def test_report_url_denied(self):
        new_test_user(self.env, login='psr_url_user', password='psr_url_user', groups='point_of_sale.group_pos_user')
        self.authenticate('psr_url_user', 'psr_url_user')
        options = json.dumps({'domain': [], 'groupby': [], 'columns': ['qty'], 'mode': 'summary', 'filters': []})
        with mute_logger('odoo.http'):
            response = self.url_open('/report/html/adams_pos_sales_report.report_pos_sales?options=' + quote(options))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('Grand total', response.text)

    # A7: the Print button sends what the screen shows (default grouping, visible columns, filters).
    def test_print_follows_screen(self):
        self.env.ref('base.user_admin').group_ids |= self.env.ref('point_of_sale.group_pos_manager')
        calls = []

        @api.model
        def fake_print(model, domain, groupby, columns, mode='summary', filters=None):
            calls.append({'domain': domain, 'groupby': groupby, 'columns': columns, 'mode': mode, 'filters': filters})
            return {'type': 'ir.actions.client', 'tag': 'display_notification',
                    'params': {'message': 'PSR print requested', 'type': 'success'}}

        Report = type(self.env['report.pos.order'])
        with patch.object(Report, 'action_print_sales_report', fake_print, create=False):
            self.start_tour('/odoo/pos-sales-report', 'adams_pos_sales_report_print', login='admin')
        self.assertEqual(len(calls), 1)
        call = calls[0]
        self.assertEqual(call['mode'], 'summary')
        self.assertEqual(call['groupby'], ['date:day'])
        self.assertEqual(call['columns'], [
            'date', 'order_id', 'cashier', 'product_id', 'qty', 'price_unit',
            'total_discount', 'price_subtotal_excl', 'tax_amount', 'price_total',
        ])
        self.assertIn(['state', 'in', ['paid', 'done']], call['domain'])
        self.assertTrue(any(f.startswith('Order Date') for f in call['filters']))
