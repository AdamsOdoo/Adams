from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.executive_dashboard.models import dashboard as dashboard_module


@tagged('post_install', '-at_install')
class TestFinance(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.user = new_test_user(
            cls.env, login='ed_fin', company_id=company.id, company_ids=[company.id],
            groups='executive_dashboard.group_admin,account.group_account_readonly')
        cls.billing = new_test_user(
            cls.env, login='ed_billing', company_id=company.id, company_ids=[company.id],
            groups='executive_dashboard.group_admin,account.group_account_invoice')
        cls.Dashboard = cls.env['executive.dashboard'].with_user(cls.user)
        cls.today = fields.Date.context_today(cls.Dashboard)
        data = cls.company_data
        cls.revenue_account = data['default_account_revenue']
        cls.cost_account = data['default_account_expense'].copy({'account_type': 'expense_direct_cost'})
        cls.partner = cls.env['res.partner'].create({'name': 'Finance Example Customer'})
        cls.vendor = cls.env['res.partner'].create({'name': 'Finance Example Vendor'})

    def setUp(self):
        super().setUp()
        dashboard_module.cache_clear()

    def _move(self, move_type, partner, account, amount, due_in_days, date=None, company=None):
        date = date or self.today
        move = self.env['account.move'].with_company(company or self.env.company).create({
            'move_type': move_type, 'partner_id': partner.id,
            'invoice_date': date, 'date': date,
            'invoice_date_due': self.today + timedelta(days=due_in_days),
            'invoice_line_ids': [fields.Command.create({
                'name': 'Example line', 'account_id': account.id, 'quantity': 1,
                'price_unit': amount, 'tax_ids': [fields.Command.clear()],
            })],
        })
        move.invoice_payment_term_id = False
        move.line_ids.filtered(lambda l: l.display_type == 'payment_term').date_maturity = \
            self.today + timedelta(days=due_in_days)
        move.action_post()
        return move

    def finance(self, period='month'):
        dashboard_module.cache_clear()
        result = self.Dashboard.get_section('finance', period)
        self.assertEqual(result['status'], 'ok')
        return result['widgets']

    # Aged buckets come from the native Aged reports when Enterprise is installed (period0,
    # period1, ...) and from journal items otherwise (not_due, d30, ...); same date ranges.
    NATIVE_AGED = {'not_due': 'period0', 'd30': 'period1', 'd60': 'period2', 'd90': 'period3'}

    @classmethod
    def bucket(cls, widget, view, key):
        keys = {key, cls.NATIVE_AGED.get(key)} if view == 'aged' else {key}
        return next(b['value'] for b in widget[view] if b['key'] in keys)

    # -- widgets -------------------------------------------------------------

    def test_widget_keys(self):
        widgets = self.finance()
        self.assertEqual(set(widgets), {'currency', 'kpis', 'trend', 'bank_cash', 'receivables', 'payables'})
        self.assertEqual(len(widgets['trend']['months']), 12)
        self.assertEqual(widgets['trend']['months'][-1]['month'], fields.Date.to_string(self.today.replace(day=1)))
        self.assertEqual([b['key'] for b in widgets['receivables']['expected']],
                         ['overdue', 'next7', 'd8_30', 'd31_60', 'later'])
        # Community: no Accounting reports engine, so the figures come from journal items.
        if not self.env.ref('account_reports.profit_and_loss', raise_if_not_found=False):
            self.assertEqual(widgets['kpis']['source'], 'journal')
            self.assertEqual([b['key'] for b in widgets['receivables']['aged']],
                             ['not_due', 'd30', 'd60', 'd90', 'older'])

    def test_profit_figures_follow_posted_entries(self):
        before = self.finance()['kpis']
        self._move('out_invoice', self.partner, self.revenue_account, 1000.0, 10)
        self._move('in_invoice', self.vendor, self.cost_account, 400.0, 10)
        draft = self._move('out_invoice', self.partner, self.revenue_account, 50.0, 10)
        draft.button_draft()
        after = self.finance()['kpis']
        currency = self.env.company.currency_id
        self.assertTrue(currency.is_zero(after['revenue'] - before['revenue'] - 1000.0))
        self.assertTrue(currency.is_zero(after['gross_profit'] - before['gross_profit'] - 600.0))
        self.assertTrue(currency.is_zero(after['net_profit'] - before['net_profit'] - 600.0))
        self.assertEqual(after['invoices'], before['invoices'] + 1)
        # The chart's current month is the same source as the This month figures.
        month = self.finance()['trend']['months'][-1]
        self.assertTrue(currency.is_zero(month['revenue'] - after['revenue']))
        self.assertTrue(currency.is_zero(month['net_profit'] - after['net_profit']))

    def test_open_items_match_native_partner_balances(self):
        self._move('out_invoice', self.partner, self.revenue_account, 300.0, -40)
        self._move('in_invoice', self.vendor, self.cost_account, 200.0, 5)
        widgets = self.finance()
        currency = self.env.company.currency_id
        # res.partner credit/debit are Odoo's own open receivable/payable per partner.
        partners = self.env['res.partner'].with_company(self.env.company).search([])
        self.assertTrue(currency.is_zero(widgets['receivables']['total'] - sum(partners.mapped('credit'))))
        self.assertTrue(currency.is_zero(widgets['payables']['total'] - sum(partners.mapped('debit'))))
        partner = self.partner.with_company(self.env.company)
        self.assertEqual(partner.credit, 300.0)
        self.assertEqual(self.vendor.with_company(self.env.company).debit, 200.0)
        receivables, payables = widgets['receivables'], widgets['payables']
        for widget in (receivables, payables):
            for view in ('aged', 'expected'):
                self.assertTrue(currency.is_zero(sum(b['value'] for b in widget[view]) - widget['total']), view)
        self.assertGreaterEqual(self.bucket(receivables, 'aged', 'd60'), 300.0)
        self.assertGreaterEqual(self.bucket(receivables, 'expected', 'overdue'), 300.0)
        self.assertGreaterEqual(receivables['overdue'], 300.0)
        self.assertGreaterEqual(self.bucket(payables, 'aged', 'not_due'), 200.0)
        self.assertGreaterEqual(self.bucket(payables, 'expected', 'next7'), 200.0)

    def test_bank_cash_matches_account_balances(self):
        widgets = self.finance()
        accounts = self.env['account.account'].search([
            ('account_type', '=', 'asset_cash'), ('company_ids', 'in', self.env.company.id)])
        currency = self.env.company.currency_id
        self.assertTrue(currency.is_zero(widgets['bank_cash']['total'] - sum(accounts.mapped('current_balance'))))
        self.assertTrue(currency.is_zero(
            widgets['bank_cash']['total'] - sum(r['balance'] for r in widgets['bank_cash']['rows'])))

    def test_bank_cash_lists_every_account(self):
        """Accounts with a zero balance, or without any entry, are listed too."""
        unused = self.company_data['default_journal_bank'].default_account_id.copy({
            'name': 'Finance Example Unused Bank', 'code': '101999'})
        widgets = self.finance()
        accounts = self.env['account.account'].search([
            ('account_type', '=', 'asset_cash'), ('active', '=', True), ('company_ids', 'in', self.env.company.id)])
        rows = {row['id']: row for row in widgets['bank_cash']['rows']}
        self.assertLessEqual(set(accounts.ids), set(rows))
        self.assertEqual(rows[unused.id]['balance'], 0.0)
        self.assertEqual(widgets['kpis']['bank_cash_accounts'], len(rows))

    def _pay(self, invoice, day):
        self.env['account.payment.register'].with_context(
            active_model='account.move', active_ids=invoice.ids).create({'payment_date': day})._create_payments()

    def test_overdue_counts_invoices_and_credits_are_apart(self):
        """Overdue is the past-due invoices only; an unapplied credit is shown apart, not netted."""
        before = self.finance()['receivables']
        self._move('out_invoice', self.partner, self.revenue_account, 300.0, -40)
        self._move('out_refund', self.partner, self.revenue_account, 500.0, -40)
        after = self.finance()['receivables']
        currency = self.env.company.currency_id
        self.assertTrue(currency.is_zero(after['owed_overdue'] - before['owed_overdue'] - 300.0))
        self.assertTrue(currency.is_zero(after['credits'] - before['credits'] + 500.0))
        self.assertTrue(currency.is_zero(after['total'] - before['total'] + 200.0))
        # The net past-due bucket nets them; the chip figure does not.
        self.assertTrue(currency.is_zero(after['overdue'] - before['overdue'] + 200.0))

    def test_balances_follow_the_period_end(self):
        """Receivables and bank balances are taken at the period's end: an invoice paid after
        it is still open at that date, as in the Aged Receivable report at that date."""
        cutoff = self.today - timedelta(days=10)
        invoice = self._move('out_invoice', self.partner, self.revenue_account, 120.0, -30,
                             date=self.today - timedelta(days=40))
        self._pay(invoice, self.today)
        self.assertIn(invoice.payment_state, ('paid', 'in_payment'))
        period = {'period': 'custom', 'date_from': fields.Date.to_string(cutoff - timedelta(days=30)),
                  'date_to': fields.Date.to_string(cutoff)}
        dashboard_module.cache_clear()
        earlier = self.Dashboard.get_section('finance', **period)['widgets']
        now = self.finance()
        self.assertEqual(earlier['kpis']['as_of'], fields.Date.to_string(cutoff))
        self.assertEqual(earlier['receivables']['as_of'], fields.Date.to_string(cutoff))
        partner_row = lambda drawer: next(  # noqa: E731
            (r for r in drawer['rows'] if r['label'] == self.partner.display_name), None)
        drawer = self.Dashboard.get_drawer('finance.open_items', dict(period, kind='receivables', view='aged'))
        self.assertEqual(partner_row(drawer)['value'], self.Dashboard._fin_format(120.0))
        detail = self.Dashboard.get_drawer('finance.open_items', partner_row(drawer)['open']['args'])
        self.assertEqual([r['label'] for r in detail['rows']], [invoice.name])
        self.assertIsNone(partner_row(self.Dashboard.get_drawer(
            'finance.open_items', {'period': 'month', 'kind': 'receivables', 'view': 'aged'})))
        if not earlier['receivables']['report']:
            # 20 days past due at the cutoff: 1-30 days.
            self.assertGreaterEqual(self.bucket(earlier['receivables'], 'aged', 'd30'), 120.0)
        self.assertGreaterEqual(earlier['receivables']['owed_overdue'] - now['receivables']['owed_overdue'], 0.0)

    def test_post_dated_payment_keeps_the_invoice_open_today(self):
        """An invoice matched today with a payment dated next week is still open today, as in the
        Aged Receivable report at today."""
        before = self.finance()['receivables']
        invoice = self._move('out_invoice', self.partner, self.revenue_account, 90.0, -30,
                             date=self.today - timedelta(days=35))
        self._pay(invoice, self.today + timedelta(days=7))
        self.assertIn(invoice.payment_state, ('paid', 'in_payment'))
        after = self.finance()['receivables']
        currency = self.env.company.currency_id
        self.assertTrue(currency.is_zero(after['total'] - before['total'] - 90.0))
        self.assertTrue(currency.is_zero(after['owed_overdue'] - before['owed_overdue'] - 90.0))
        drawer = self.Dashboard.get_drawer('finance.open_items', {'period': 'month', 'kind': 'receivables'})
        row = next(r for r in drawer['rows'] if r['label'] == self.partner.display_name)
        # Items open today are counted, the add-back of a later match is not an extra item.
        self.assertEqual(row['sub'], '0 open items')

    def test_non_trade_receivables_are_left_out(self):
        """Like the Aged Receivable report's default Account filter, Non Trade accounts are left out."""
        before = self.finance()['receivables']['total']
        non_trade = self.company_data['default_account_receivable'].copy({
            'name': 'Finance Example VAT Receivable', 'code': '100199', 'non_trade': True})
        move = self.env['account.move'].create({'date': self.today, 'line_ids': [
            fields.Command.create({'account_id': non_trade.id, 'debit': 80.0, 'name': 'VAT'}),
            fields.Command.create({'account_id': self.revenue_account.id, 'credit': 80.0, 'name': 'VAT'}),
        ]})
        move.action_post()
        self.assertEqual(self.finance()['receivables']['total'], before)

    # -- access --------------------------------------------------------------

    def test_invoicing_user_sees_every_figure(self):
        self._move('out_invoice', self.partner, self.revenue_account, 250.0, -10)
        billing = self.env['executive.dashboard'].with_user(self.billing)
        result = billing.get_section('finance', 'month')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['widgets'], self.finance())
        self.assertIn('total', billing.get_drawer('finance.bank_cash'))

    def test_other_company_account_is_refused(self):
        data = self.setup_other_company(name='Finance Example Other')
        account = data['default_journal_bank'].default_account_id
        with self.assertRaises(UserError):
            self.Dashboard.open_action('finance.account', {'account_id': account.id})
        # The other company's receivable account is refused too (ValidationError is a UserError).
        receivable = data['default_account_receivable']
        for method in ('get_drawer', 'open_action'):
            with self.assertRaises(UserError):
                getattr(self.Dashboard, method)('finance.account', {'account_id': receivable.id})

    # -- drawers and actions -------------------------------------------------

    def test_drawers(self):
        invoice = self._move('out_invoice', self.partner, self.revenue_account, 300.0, -40)
        revenue = self.Dashboard.get_drawer('finance.revenue', {'period': 'month'})
        self.assertEqual(len(revenue['rows']), 12)
        self.assertEqual(revenue['action']['key'], 'finance.pnl')

        bank = self.Dashboard.get_drawer('finance.bank_cash', {'period': 'month'})
        self.assertIn('total', bank)
        # An account opens its native screen at once: no intermediate "latest journal items" panel.
        self.assertTrue(bank['rows'])
        for row in bank['rows']:
            self.assertNotIn('open', row)
            self.assertEqual(row['action']['key'], 'finance.account')
        with self.assertRaises(ValidationError):
            self.Dashboard.get_drawer('finance.account', bank['rows'][0]['action']['args'])

        args = {'kind': 'receivables', 'view': 'aged', 'bucket': 'd60'}
        bucket = self.Dashboard.get_drawer('finance.open_items', args)
        row = next(r for r in bucket['rows'] if r['label'] == self.partner.display_name)
        detail = self.Dashboard.get_drawer('finance.open_items', row['open']['args'])
        self.assertEqual([r['label'] for r in detail['rows']], [invoice.name])

        # A partner opens the Partner Ledger (Enterprise) or its open journal items.
        action = self.Dashboard.open_action('finance.open_items', row['open']['args'])
        if not self.env.ref('account_reports.partner_ledger_report', raise_if_not_found=False):
            self.assertEqual(action['res_model'], 'account.move.line')
            lines = self.env['account.move.line'].search(action['domain'])
            self.assertEqual(lines.move_id, invoice)
        # Without the Aged report a bucket opens its journal items: nothing in 1-30 days is this invoice's.
        if not self.env.ref('account_reports.aged_receivable_report', raise_if_not_found=False):
            action = self.Dashboard.open_action('finance.open_items', {'kind': 'receivables', 'view': 'aged', 'bucket': 'd30'})
            self.assertFalse(self.env['account.move.line'].search(action['domain']) & invoice.line_ids)

        pnl = self.Dashboard.open_action('finance.pnl', {'period': 'month'})
        self.assertIn(pnl['type'], ('ir.actions.act_window', 'ir.actions.client'))

    def test_accounts_open_the_trial_balance(self):
        """Receivables list their accounts; an account opens the Trial Balance filtered on it
        (Enterprise), else its journal items. A partner opens the Partner Ledger."""
        invoice = self._move('out_invoice', self.partner, self.revenue_account, 250.0, 10)
        account = invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').account_id
        drawer = self.Dashboard.get_drawer('finance.open_items', {'kind': 'receivables', 'view': 'aged'})
        by_account = drawer['groups'][0]['rows']
        row = next(r for r in by_account if r['action']['args']['account_id'] == account.id)
        self.assertEqual(row['action']['key'], 'finance.account')
        self.assertNotIn('open', row)
        action = self.Dashboard.open_action('finance.account', {'account_id': account.id})
        trial = self.env.ref('account_reports.trial_balance_report', raise_if_not_found=False)
        if trial:
            # The Trial Balance itself (not the fallback), searched on the account code.
            self.assertEqual(action['type'], 'ir.actions.client')
            self.assertEqual(action['context']['report_id'], trial.id)
            self.assertEqual(action['params']['options']['filter_search_bar'], account.code)
        else:
            self.assertEqual(action['res_model'], 'account.move.line')
            self.assertEqual(set(self.env['account.move.line'].search(action['domain']).account_id), {account})
        partner_args = {'kind': 'receivables', 'view': 'aged', 'partner_id': self.partner.id}
        action = self.Dashboard.open_action('finance.open_items', partner_args)
        ledger = self.env.ref('account_reports.partner_ledger_report', raise_if_not_found=False)
        if ledger:
            self.assertEqual(action['context']['report_id'], ledger.id)
            self.assertEqual(action['params']['options']['partner_ids'], [self.partner.id])
        else:
            self.assertEqual(self.env['account.move.line'].search(action['domain']).move_id, invoice)

    def test_drawer_arguments_are_validated(self):
        for args in ({'kind': 'assets'}, {'kind': 'receivables', 'view': 'soon'},
                     {'kind': 'receivables', 'bucket': 'd365'}, {'kind': 'receivables', 'partner_id': '1'}):
            with self.assertRaises(ValidationError):
                self.Dashboard.get_drawer('finance.open_items', args)
        income = self.revenue_account
        for args in ({'account_id': income.id}, {'account_id': 'x'}, {}):
            with self.assertRaises(ValidationError):
                self.Dashboard.open_action('finance.account', args)
        with self.assertRaises(ValidationError):
            self.Dashboard.get_drawer('finance.open_items', {'kind': 'receivables', 'period': 'someday'})

    def test_bucket_boundaries_and_cancelled_entries(self):
        before = self.finance()['receivables']
        for days in (0, -1, 7, 8, 30, 31, 61):
            self._move('out_invoice', self.partner, self.revenue_account, 10.0 + days, days)
        self._move('out_invoice', self.partner, self.revenue_account, 1000.0, 3).button_cancel()
        after = self.finance()['receivables']
        delta = lambda view, key: self.bucket(after, view, key) - self.bucket(before, view, key)  # noqa: E731
        self.assertAlmostEqual(delta('expected', 'overdue'), 9.0)            # due yesterday
        self.assertAlmostEqual(delta('expected', 'next7'), 10.0 + 17.0)      # today, +7
        self.assertAlmostEqual(delta('expected', 'd8_30'), 18.0 + 40.0)      # +8, +30
        self.assertAlmostEqual(delta('expected', 'd31_60'), 41.0)            # +31
        self.assertAlmostEqual(delta('expected', 'later'), 71.0)             # +61
        self.assertAlmostEqual(delta('aged', 'd30'), 9.0)
        self.assertAlmostEqual(delta('aged', 'not_due'), 10.0 + 17 + 18 + 40 + 41 + 71)
        self.assertAlmostEqual(after['total'] - before['total'], 206.0)      # the cancelled invoice is not counted

    def test_native_aged_columns_open_their_range(self):
        # The Enterprise Aged reports return period0..period5; each opens the same due-date range.
        invoice = self._move('out_invoice', self.partner, self.revenue_account, 70.0, -100)
        args = {'kind': 'receivables', 'view': 'aged', 'bucket': 'period4', 'partner_id': self.partner.id}
        drawer = self.Dashboard.get_drawer('finance.open_items', args)
        self.assertEqual([r['label'] for r in drawer['rows']], [invoice.name])
        # 61-90 days does not hold this 100-day-old invoice (the panel, on Community and Enterprise).
        drawer = self.Dashboard.get_drawer('finance.open_items', dict(args, bucket='period3'))
        self.assertNotIn(invoice.name, [r['label'] for r in drawer['rows']])
        # Without the Partner Ledger the button opens the same range as journal items.
        if not self.env.ref('account_reports.partner_ledger_report', raise_if_not_found=False):
            action = self.Dashboard.open_action('finance.open_items', dict(args, bucket='period3'))
            self.assertFalse(self.env['account.move.line'].search(action['domain']) & invoice.line_ids)
        with self.assertRaises(ValidationError):
            self.Dashboard.get_drawer('finance.open_items', dict(args, view='expected'))

    def test_other_currency_company_is_converted(self):
        other = self.setup_other_currency('EUR', rates=[('1900-01-01', 2.0)])
        data = self.setup_other_company(name='Finance Example EUR', currency_id=other.id)
        company_b = data['company']
        user = new_test_user(
            self.env, login='ed_fin_two', company_id=self.env.company.id,
            company_ids=[self.env.company.id, company_b.id],
            groups='executive_dashboard.group_admin,account.group_account_readonly')
        dashboard = self.env['executive.dashboard'].with_user(user).with_context(
            allowed_company_ids=[self.env.company.id, company_b.id])
        before = dashboard.get_section('finance', 'month')['widgets']
        self._move('out_invoice', self.partner, data['default_account_revenue'], 100.0, -5, company=company_b)
        dashboard_module.cache_clear()
        after = dashboard.get_section('finance', 'month')['widgets']
        currency = self.env.company.currency_id
        # 100 EUR at 2 EUR per company currency unit.
        self.assertTrue(currency.is_zero(after['kpis']['revenue'] - before['kpis']['revenue'] - 50.0))
        self.assertTrue(currency.is_zero(after['receivables']['total'] - before['receivables']['total'] - 50.0))
        drawer = dashboard.get_drawer('finance.open_items', {'kind': 'receivables', 'view': 'expected'})
        self.assertEqual(drawer['total']['value'], dashboard._fin_format(after['receivables']['total']))
        row = next(r for r in drawer['rows'] if r['label'] == self.partner.display_name)
        detail = dashboard.get_drawer('finance.open_items', row['open']['args'])
        self.assertIn(dashboard._fin_format(50.0), [r['value'] for r in detail['rows']])

    def test_query_limit(self):
        if self.env['executive.dashboard']._fin_engine():
            self.skipTest('Accounting reports installed: the native engines run their own queries.')
        self.finance()  # warm the ORM caches
        # Counted for the test's environment user; the section runs as ``ed_fin``.
        with self.assertQueryCount(**{self.env.user.login: 17}):
            self.Dashboard.get_section('finance', 'month', refresh=True)
