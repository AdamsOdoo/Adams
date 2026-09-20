"""Known amounts evaluated by installed native reports, not mock report totals."""
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestDashboardFinance(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}
        cls.mapping_model = cls.env['adams.dashboard.finance.mapping']
        cls.pnl = cls.env.ref('account_reports.profit_and_loss')
        cls.revenue_expression = cls.env.ref('account_reports.account_financial_report_revenue0_balance')

    def _mapping(self, key='revenue', report=None, expression=None, approve=True, denominator=None):
        mapping = self.mapping_model.create({
            'company_id': self.env.company.id, 'metric': key,
            'report_id': (report or self.pnl).id,
            'expression_id': (expression or self.revenue_expression).id,
            'denominator_expression_id': denominator.id if denominator else False,
            'definition_note': 'Disposable test approval of the exact standard report definition.',
        })
        if approve:
            mapping.action_approve()
        return mapping

    def _invoice(self, amount, move_type='out_invoice', invoice_date='2026-08-10', posted=True, due_date=None):
        purchase = move_type.startswith('in_')
        move = self.env['account.move'].create({
            'move_type': move_type, 'partner_id': self.partner_a.id,
            'invoice_payment_term_id': False,
            'invoice_date': invoice_date, 'date': invoice_date, 'invoice_date_due': due_date or invoice_date,
            'journal_id': self.company_data['default_journal_purchase' if purchase else 'default_journal_sale'].id,
            'invoice_line_ids': [Command.create({
                'name': 'Financial dashboard fixture', 'quantity': 1, 'price_unit': amount,
                'account_id': self.company_data['default_account_expense' if purchase else 'default_account_revenue'].id,
                'tax_ids': [Command.clear()],
            })],
        })
        maturity = due_date or invoice_date
        payment_lines = move.line_ids.filtered(
            lambda line: line.account_id.account_type in ('asset_receivable', 'liability_payable'))
        payment_lines.write({'date_maturity': maturity})
        if posted:
            move.action_post()
            self.assertEqual({str(line.date_maturity) for line in payment_lines}, {maturity})
        return move

    def _item(self, key='revenue', options=None, dashboard=None):
        # Abstract model recordsets are empty/falsy even with a different user.
        # Preserve the supplied environment so permission tests exercise it.
        target = self.dashboard if dashboard is None else dashboard
        result = target.get_section('finance', self.options if options is None else options)
        return next(item for item in result['items'] if item['key'] == key)

    def test_native_pnl_known_refund_and_batch_evaluation(self):
        self._mapping()
        self._mapping('gross_profit', expression=self.env.ref('account_reports.account_financial_report_gross_profit0_balance'))
        self._invoice(100)
        self._invoice(25, 'out_refund')
        self._invoice(999, posted=False)
        self._invoice(777, invoice_date='2026-09-01')
        report_type = type(self.pnl)
        original = report_type.get_report_information
        calls = []

        def evaluate(report, options):
            calls.append(report.id)
            return original(report, options)

        with patch.object(report_type, 'get_report_information', evaluate):
            result = self.dashboard.get_section('finance', self.options)
        items = {item['key']: item for item in result['items']}
        for key in ('revenue', 'gross_profit'):
            self.assertEqual(items[key]['status'], 'ready', items[key])
            self.assertAlmostEqual(items[key]['value'], 75)
        self.assertEqual(calls, [self.pnl.id])

    def test_native_zero_and_signed_negative_are_values(self):
        self._mapping()
        zero = self._item()
        self.assertEqual(zero['status'], 'ready', zero)
        self.assertEqual(zero['value'], 0)
        self._invoice(100)
        self._invoice(125, 'out_refund')
        self.assertAlmostEqual(self._item()['value'], -25)

    def test_native_margin_units_zero_denominator_and_dependency_drift(self):
        summary = self.env.ref('account_reports.executive_summary')
        expression = self.env.ref('account_reports.account_financial_report_executivesummary_gpmargin0_balance')
        denominator = self.env.ref('account_reports.account_financial_report_executivesummary_gpmargin0_opinc')
        self._mapping('gross_margin', report=summary, expression=expression, denominator=denominator)
        empty = self._item('gross_margin')
        self.assertEqual(empty['status'], 'undefined_ratio', empty)
        self.assertIsNone(empty['value'])
        self._invoice(100)
        actual = self._item('gross_margin')
        self.assertEqual(actual['status'], 'ready', actual)
        self.assertEqual(actual['unit'], 'percentage')
        self.assertAlmostEqual(actual['value'], 100)
        # A change in the referenced P&L invalidates approval of the ratio too.
        self.revenue_expression.subformula = 'sum'
        self.assertEqual(self._item('gross_margin')['status'], 'not_configured')

    def test_unapproved_changed_or_archived_mapping_withholds_value(self):
        mapping = self._mapping(approve=False)
        self._invoice(100)
        self.assertIsNone(self._item()['value'])
        mapping.action_approve()
        self.assertEqual(self._item()['value'], 100)
        self.revenue_expression.subformula = 'sum'
        self.assertEqual(self._item()['status'], 'not_configured')
        self.assertIsNone(self._item()['value'])
        with self.assertRaises(ValidationError):
            self.dashboard.open_report('revenue', self.options)
        mapping.write({'definition_note': 'Changed policy; approval must be renewed.'})
        self.assertFalse(mapping.approved_by)
        mapping.active = False
        self.assertIsNone(self._item()['value'])

    def test_approval_fields_cannot_be_forged(self):
        mapping = self._mapping(approve=False)
        with self.assertRaises(AccessError):
            mapping.write({'approved_by': self.env.uid, 'definition_fingerprint': mapping._fingerprint()})
        with self.assertRaises(AccessError):
            self.mapping_model.create({'approved_by': self.env.uid})

    def test_finance_access_and_company_isolation(self):
        mapping = self._mapping()
        self._invoice(100)
        reader = new_test_user(self.env, login='financial_dashboard_no_accounting',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        restricted = self._item(dashboard=self.dashboard.with_user(reader))
        self.assertEqual(restricted['status'], 'restricted')
        self.assertIsNone(restricted['value'])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_report('revenue', self.options)
        with self.assertRaises(AccessError):
            mapping.with_user(reader).action_approve()
        foreign = self.env['res.company'].create({'name': 'Foreign financial fixture'})
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).get_section('finance', dict(self.options, company_id=foreign.id))
        self.env.user.company_ids |= foreign
        foreign_scope = dict(self.options, company_id=foreign.id)
        authorized = self.dashboard.with_context(allowed_company_ids=[self.env.company.id, foreign.id])
        self.assertIsNone(self._item(options=foreign_scope, dashboard=authorized)['value'])

    def test_native_action_keeps_posted_dates_and_ignores_saved_filters(self):
        self._mapping()
        self._invoice(100)
        item = self._item(dashboard=self.dashboard.with_context(all_entries=True, search_default_draft=True))
        self.assertEqual(item['status'], 'ready', item)
        action = self.dashboard.open_report('revenue', self.options)
        self.assertEqual(action['tag'], 'account_report')
        self.assertTrue(action['params']['ignore_session'])
        self.assertTrue(action['keep_journal_groups_options'])
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
        self.assertFalse(action['params']['options'].get('all_entries'))
        self.assertEqual(action['params']['options']['date']['date_from'], '2026-08-01')
        self.assertEqual(action['params']['options']['date']['date_to'], '2026-08-31')
        self.assertEqual(action['params']['options']['report_id'], self.pnl.id)
        self.assertEqual(action['params']['options'], item['provenance']['options'])

    def test_native_aging_preserves_historical_settlement(self):
        aging = self.env.ref('account_reports.aged_receivable_report')
        expression = self.env.ref('account_reports.aged_receivable_line_total')
        self._mapping('receivables', report=aging, expression=expression)
        invoice = self._invoice(100000)
        receivable = invoice.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        settlements = self.env['account.move.line']
        for amount, settlement_date in ((40000, '2026-08-20'), (60000, '2026-09-15')):
            move = self.env['account.move'].create({
                'move_type': 'entry', 'date': settlement_date,
                'journal_id': self.company_data['default_journal_misc'].id,
                'line_ids': [
                    Command.create({'name': 'Settlement fixture', 'partner_id': self.partner_a.id,
                        'account_id': receivable.account_id.id, 'credit': amount, 'date_maturity': settlement_date}),
                    Command.create({'name': 'Settlement counterpart',
                        'account_id': self.company_data['default_account_assets'].id, 'debit': amount}),
                ],
            })
            move.action_post()
            settlements |= move.line_ids.filtered(lambda line: line.account_id == receivable.account_id)
        (receivable + settlements).reconcile()
        self.assertEqual(invoice.amount_residual, 0)
        historical = self._item('receivables')
        self.assertEqual(historical['status'], 'ready', historical)
        self.assertAlmostEqual(historical['value'], 60000)
        current = self._item('receivables', dict(self.options, as_of='2026-09-30'))
        self.assertEqual(current['status'], 'ready', current)
        self.assertAlmostEqual(current['value'], 0)

    def test_mapping_rejects_mismatched_report_and_date_basis(self):
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._mapping('cash')  # P&L is a period, not an as-of balance.
        with self.assertRaises(ValidationError), self.cr.savepoint():
            self._mapping(report=self.env.ref('account_reports.aged_receivable_report'))

    def _cash_mapping(self):
        report = self.env.ref('account_reports.balance_sheet')
        line = self.env.ref('account_reports.account_financial_report_bank_view0')
        expression = line.expression_ids.filtered(lambda item: item.label == 'balance')
        mapping = self._mapping('cash', report=report, expression=expression, approve=False)
        mapping.write({
            'cash_detail_report_id': self.env.ref('account_reports.general_ledger_report').id,
            'cash_detail_expression_id': self.env.ref('account_reports.general_ledger_line_balance').id,
            'cash_flow_report_id': self.env.ref('account_reports.cash_flow_report').id,
        })
        mapping.action_approve()
        return mapping

    def _cash_account(self, code, currency=None):
        return self.env['account.account'].create({
            'name': 'Disposable cash fixture ' + code, 'code': code,
            'account_type': 'asset_cash', 'company_ids': [Command.set(self.env.company.ids)],
            'currency_id': currency.id if currency else False,
        })

    def _cash_entry(self, account, amount, date, foreign_amount=None):
        cash_line = {'account_id': account.id, 'debit': max(amount, 0), 'credit': max(-amount, 0)}
        if foreign_amount is not None:
            cash_line.update(currency_id=account.currency_id.id, amount_currency=foreign_amount)
        move = self.env['account.move'].create({
            'journal_id': self.company_data['default_journal_misc'].id, 'date': date,
            'line_ids': [Command.create(cash_line), Command.create({
                'account_id': self.company_data['default_account_assets'].id,
                'debit': max(-amount, 0), 'credit': max(amount, 0),
            })],
        })
        move.action_post()
        return move

    def test_native_cash_cutoff_zero_negative_archived_and_no_journal(self):
        self._cash_mapping()
        cash = self._cash_account('990081')
        zero = self._cash_account('990082')
        negative = self._cash_account('990083')
        self._cash_entry(cash, 50, '2026-07-01')
        self._cash_entry(cash, 100, '2026-08-10')
        self._cash_entry(cash, -40, '2026-09-10')
        self._cash_entry(negative, -20, '2026-08-10')
        cash.write({'name': 'Renamed archived cash fixture', 'active': False})
        result = self.dashboard.get_cash_directory(self.options)
        rows = {row['id']: row for row in result['rows']}
        self.assertTrue(result.get('native_balances'), result)
        self.assertEqual(rows[cash.id]['balance'], 150)
        self.assertEqual(rows[zero.id]['balance'], 0)
        self.assertEqual(rows[negative.id]['balance'], -20)
        self.assertEqual(rows[cash.id]['name'], 'Renamed archived cash fixture')
        self.assertFalse(rows[cash.id]['active'])
        self.assertEqual(rows[cash.id]['journals'], [])
        later = self.dashboard.get_cash_directory(dict(self.options, as_of='2026-09-30'))
        self.assertEqual(next(row for row in later['rows'] if row['id'] == cash.id)['balance'], 110)
        action = self.dashboard.open_report('cash_account', self.options, group_id=cash.id)
        self.assertEqual(action['tag'], 'account_report')
        self.assertEqual(action['params']['options']['date']['date_to'], '2026-08-31')
        self.assertEqual(action['params']['options']['filter_search_bar'], cash.code)
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])

    def test_native_cash_company_currency_is_distinct_from_account_currency(self):
        self._cash_mapping()
        foreign_currency = self.env.ref('base.EUR')
        self.assertNotEqual(foreign_currency, self.env.company.currency_id)
        account = self._cash_account('990084', foreign_currency)
        self._cash_entry(account, 100, '2026-08-10', foreign_amount=120)
        rows = self.dashboard.get_cash_directory(self.options)['rows']
        row = next(row for row in rows if row['id'] == account.id)
        self.assertEqual(row['balance'], 100, row)
        self.assertEqual(row['currency'], foreign_currency.name)
        self.assertEqual(row['balance_currency'], self.env.company.currency_id.name)

    def test_cash_action_rejects_wrong_type_and_company(self):
        self._cash_mapping()
        for account_id in (True, '1'):
            with self.assertRaises(ValidationError):
                self.dashboard.open_report('cash_account', self.options, group_id=account_id)
        with self.assertRaises(AccessError):
            self.dashboard.open_report('cash_account', self.options,
                                       group_id=self.company_data['default_account_assets'].id)
        foreign = self.env['res.company'].create({'name': 'Foreign cash fixture'})
        foreign_account = self.env['account.account'].create({
            'name': 'Other company cash', 'code': '990085', 'account_type': 'asset_cash',
            'company_ids': [Command.set(foreign.ids)],
        })
        with self.assertRaises(AccessError):
            self.dashboard.open_report('cash_account', self.options, group_id=foreign_account.id)

    def test_native_aging_due_today_boundary_and_signed_credits(self):
        self._mapping('receivables', report=self.env.ref('account_reports.aged_receivable_report'),
                      expression=self.env.ref('account_reports.aged_receivable_line_total'))
        self._invoice(100, invoice_date='2026-08-01', due_date='2026-08-31')
        self._invoice(60, invoice_date='2026-08-01', due_date='2026-08-30')
        self._invoice(25, 'out_refund', invoice_date='2026-08-01', due_date='2026-08-30')
        item = self._item('receivables')
        self.assertEqual(item['status'], 'ready', item)
        self.assertEqual(item['value'], 135)
        buckets = {bucket['key']: bucket['value'] for bucket in item['aging_buckets']}
        self.assertEqual(buckets['period0'], 100)
        self.assertEqual(buckets['period1'], 35)
        self.assertEqual(item['provenance']['options']['aging_based_on'], 'base_on_maturity_date')
        action = self.dashboard.open_report('receivables', self.options)
        self.assertEqual(action['params']['options']['aging_interval'], 30)

    def test_native_payable_buckets_preserve_supplier_refunds(self):
        self._mapping('payables', report=self.env.ref('account_reports.aged_payable_report'),
                      expression=self.env.ref('account_reports.aged_payable_line_total'))
        self._invoice(200, 'in_invoice', due_date='2026-08-31')
        self._invoice(50, 'in_refund', due_date='2026-08-31')
        item = self._item('payables')
        self.assertEqual(item['status'], 'ready', item)
        self.assertEqual(item['value'], 150)
        buckets = {bucket['key']: bucket['value'] for bucket in item['aging_buckets']}
        self.assertEqual(buckets['period0'], 150)
        self.assertEqual(buckets['period1'], 0)

    def test_native_cash_flow_bridge_and_internal_transfer(self):
        self._cash_mapping()
        bank = self.company_data['default_journal_bank'].default_account_id
        other_cash = self.company_data['default_journal_cash'].default_account_id
        self._cash_entry(bank, 50, '2026-07-01')
        self._cash_entry(bank, 100, '2026-08-10')
        self._cash_entry(bank, -20, '2026-08-20')
        self._cash_entry(bank, -40, '2026-09-10')
        transfer = self.env['account.move'].create({
            'date': '2026-08-21', 'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [Command.create({'account_id': bank.id, 'credit': 30}),
                         Command.create({'account_id': other_cash.id, 'debit': 30})],
        })
        transfer.action_post()
        result = self.dashboard.get_section('finance', self.options)['cash_flow']
        self.assertEqual(result['status'], 'ready', result)
        report = self.env.ref('account_reports.cash_flow_report')
        values = {row['key']: row['value'] for row in result['rows']}
        for key, expected in [('opening_balance', 50), ('net_increase', 80), ('closing_balance', 130)]:
            self.assertEqual(values[report._get_generic_line_id(None, None, markup=key)], expected)
            self.assertEqual(result['bridge'][key]['value'], expected)
        # Unclassified activity is shown, not discarded to force a bridge.
        self.assertIn(report._get_generic_line_id(None, None, markup='unclassified_activities'), values)
        action = self.dashboard.open_report('cash_flow', self.options)
        self.assertEqual(action['params']['options'], result['options'])
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])

    def test_native_partner_ledger_keeps_dual_role_balances_separate(self):
        ledger = self.env.ref('account_reports.partner_ledger_report')
        for metric, prefix in [('receivables', 'aged_receivable'), ('payables', 'aged_payable')]:
            mapping = self._mapping(metric, report=self.env.ref(f'account_reports.{prefix}_report'),
                                    expression=self.env.ref(f'account_reports.{prefix}_line_total'), approve=False)
            mapping.partner_ledger_report_id = ledger
            mapping.action_approve()
        self._invoice(100)
        self._invoice(200, 'in_invoice')
        for metric, expected_role, expected_debit, expected_credit, expected_balance in [
            ('receivables', 'trade_receivable', 100, 0, 100),
            ('payables', 'trade_payable', 0, 200, -200),
        ]:
            action = self.dashboard.open_report('partner_' + metric, self.options)
            options = action['params']['options']
            self.assertEqual({item['id'] for item in options['account_type'] if item['selected']}, {expected_role})
            self.assertEqual(options['date']['date_from'], '2026-08-01')
            self.assertEqual(options['date']['date_to'], '2026-08-31')
            self.assertFalse(options['all_entries'])
            native = ledger.with_context(action['context']).get_report_information(options)
            line = next(row for row in native['lines']
                        if ledger._get_model_info_from_id(row['id']) == ('res.partner', self.partner_a.id))
            columns = {column['expression_label']: value['no_format']
                       for column, value in zip(options['columns'], line['columns'])}
            self.assertEqual(columns['debit'], expected_debit)
            self.assertEqual(columns['credit'], expected_credit)
            self.assertEqual(columns['balance'], expected_balance)
        mapping = self._financial_mapping_for_test('receivables')
        mapping.write({'definition_note': 'Needs a renewed review'})
        with self.assertRaises(ValidationError):
            self.dashboard.open_report('partner_receivables', self.options)

    def _financial_mapping_for_test(self, metric):
        return self.mapping_model.search([('company_id', '=', self.env.company.id), ('metric', '=', metric)])

    def test_native_short_term_forecast_retains_its_actual_definition(self):
        self._mapping('standard_forecast', report=self.env.ref('account_reports.executive_summary'),
                      expression=self.env.ref('account_reports.account_financial_report_executivesummary_st_cash_forecast0_balance'))
        self._invoice(50, invoice_date='2026-07-01')
        self._invoice(100)
        self._invoice(200, 'in_invoice')
        self._invoice(999, invoice_date='2026-09-01')
        item = self._item('standard_forecast')
        self.assertEqual(item['status'], 'ready', item)
        self.assertEqual(item['source_kind'], 'forecast')
        self.assertEqual(item['value'], -50)
        self._cash_entry(self.company_data['default_journal_bank'].default_account_id, 1000, '2026-08-10')
        self.assertEqual(self._item('standard_forecast')['value'], -50)

    def test_native_budget_uses_selected_version_and_dates_without_proration(self):
        mapping = self._mapping(approve=False)
        budget = self.env['account.report.budget'].create({
            'name': 'Approved August fixture', 'company_id': self.env.company.id,
            'item_ids': [Command.create({'account_id': self.company_data['default_account_revenue'].id,
                                        'date': '2026-08-01', 'amount': -120}),
                         Command.create({'account_id': self.company_data['default_account_revenue'].id,
                                        'date': '2026-09-01', 'amount': -999})],
        })
        mapping.budget_id = budget
        mapping.action_approve()
        self._invoice(100)
        item = self._item()
        self.assertEqual(item['value'], 100)
        self.assertEqual(item['budget']['status'], 'ready', item['budget'])
        self.assertEqual(item['budget']['value'], 120)
        self.assertEqual(item['budget']['budget_id'], budget.id)
        action = self.dashboard.open_report('budget_revenue', self.options)
        self.assertEqual(action['params']['options'], item['budget']['options'])
        partial = self._item(options=dict(self.options, date_from='2026-08-15'))
        self.assertEqual(partial['budget']['status'], 'not_configured')
        self.assertIsNone(partial['budget']['value'])
        # An explicit native zero target is different from absent period items.
        budget.item_ids.filtered(lambda line: str(line.date) == '2026-08-01').amount = 0
        self.assertEqual(self._item()['budget']['value'], 0)

    def test_financial_trend_native_signed_months_and_clipped_drilldown(self):
        from odoo.exceptions import ValidationError
        self._mapping('revenue')
        self._invoice(100, invoice_date='2026-07-20')
        self._invoice(25, move_type='out_refund', invoice_date='2026-08-15')
        options = dict(self.options, date_from='2026-07-15', date_to='2026-09-10')
        trend = self.dashboard.get_financial_trend('revenue', options)
        self.assertEqual([r['value'] for r in trend['rows']], [100, -25, 0])
        self.assertEqual(trend['rows'][0]['date_from'], '2026-07-15')
        self.assertEqual(trend['rows'][-1]['date_to'], '2026-09-10')
        action = self.dashboard.open_financial_period('revenue', options, '2026-09')
        self.assertEqual(action['params']['options']['date']['date_to'], '2026-09-10')
        self.assertEqual(action['params']['options']['date']['date_from'], '2026-09-01')
        with self.assertRaises(ValidationError):
            self.dashboard.open_financial_period('revenue', options, '2026-10')
