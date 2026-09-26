from xml.etree import ElementTree
import io
import zipfile
import json
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

    def test_restricted_financial_field_blocks_sql_report_and_routes(self):
        self._mapping()
        self._invoice(100)
        reader = new_test_user(self.env, login='dashboard_finance_field_reader',
            groups='base.group_user,account.group_account_readonly,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        dashboard = self.dashboard.with_user(reader)
        self.assertEqual(self._item(dashboard=dashboard)['value'], 100)
        # A real field restriction, not a mocked report result or denied RPC.
        with patch.object(self.env['account.move.line']._fields['balance'], 'groups', 'base.group_system'):
            self.assertEqual(self._item(dashboard=dashboard)['status'], 'restricted')
            self.assertIsNone(self._item(dashboard=dashboard)['value'])
            with self.assertRaises(AccessError):
                dashboard.open_report('revenue', self.options)
            with self.assertRaises(AccessError):
                dashboard.get_financial_trend('revenue', self.options)
            with self.assertRaises(AccessError):
                dashboard.get_financial_trends(['revenue', 'gross_profit'], self.options)
        reader.group_ids -= self.env.ref('account.group_account_readonly')
        self.assertEqual(self._item(dashboard=dashboard)['status'], 'restricted')

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
        self.assertAlmostEqual(self._item('receivables_overdue')['value'], 60000)
        current = self._item('receivables', dict(self.options, as_of='2026-09-30'))
        self.assertEqual(current['status'], 'ready', current)
        self.assertAlmostEqual(current['value'], 0)
        self.assertAlmostEqual(self._item('receivables_overdue', dict(self.options, as_of='2026-09-30'))['value'], 0)

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
        cash.write({'name': 'Renamed cash fixture'})
        result = self.dashboard.get_cash_directory(self.options)
        rows = {row['id']: row for row in result['rows']}
        self.assertTrue(result.get('native_balances'), result)
        self.assertEqual(rows[cash.id]['balance'], 150)
        self.assertEqual(rows[zero.id]['balance'], 0)
        self.assertEqual(rows[negative.id]['balance'], -20)
        self.assertEqual(rows[cash.id]['name'], 'Renamed cash fixture')
        self.assertTrue(rows[cash.id]['active'])
        self.assertEqual(rows[cash.id]['journals'], [])
        filtered = self.dashboard.get_cash_directory(self.options, 0, 'Renamed cash fixture')
        self.assertEqual(filtered['total_count'], 1)
        self.assertEqual(filtered['rows'][0]['balance'], 150)
        cash.active = False
        archived = self.dashboard.get_cash_directory(self.options, 0, cash.code)
        self.assertEqual(archived['total_count'], 0)
        self.assertEqual(archived['rows'], [])
        cash.active = True
        later = self.dashboard.get_cash_directory(dict(self.options, as_of='2026-09-30'))
        self.assertEqual(next(row for row in later['rows'] if row['id'] == cash.id)['balance'], 110)
        action = self.dashboard.open_report('cash_account', self.options, group_id=cash.id)
        self.assertEqual(action['tag'], 'account_report')
        self.assertEqual(action['params']['options']['date']['date_to'], '2026-08-31')
        self.assertEqual(action['params']['options']['filter_search_bar'], cash.code)
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])

    def test_cash_journal_breakdown_refuses_unlinked_account(self):
        self._cash_mapping()
        account = self._cash_account('990091')
        self._cash_entry(account, 37, '2026-08-10')
        result = self.dashboard.get_section('finance', self.options)
        cash = next(item for item in result['items'] if item['key'] == 'cash')
        self.assertEqual(cash['status'], 'ready', cash)
        breakdown = result['cash_breakdown']
        self.assertEqual(breakdown['status'], 'ambiguous', breakdown)
        self.assertGreaterEqual(breakdown['unlinked_accounts'], 1)
        self.assertNotIn('bank', breakdown)
        self.assertNotIn('cash', breakdown)

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
        summary = self.dashboard.export_summary(self.options)
        printed_flow = next(row for row in summary['print_rows'] if row['metric'] == 'Net cash movement')
        self.assertEqual(printed_flow['value'], 80)
        self.assertIn('Net cash movement,80', summary['content'])
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

    def test_native_aging_installments_and_later_settlement(self):
        self._mapping('receivables', report=self.env.ref('account_reports.aged_receivable_report'),
                      expression=self.env.ref('account_reports.aged_receivable_line_total'))
        terms = self.env['account.payment.term'].create({
            'name': 'Dashboard fixture 40 percent now, 60 after 60 days',
            'line_ids': [Command.clear(),
                         Command.create({'value': 'percent', 'value_amount': 40, 'nb_days': 0}),
                         Command.create({'value': 'percent', 'value_amount': 60, 'nb_days': 60})],
        })
        invoice = self._invoice(100, invoice_date='2026-08-01', posted=False)
        invoice.invoice_payment_term_id = terms
        invoice.action_post()
        receivable = invoice.line_ids.filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        self.assertEqual(sorted((str(line.date_maturity), line.balance) for line in receivable),
                         [('2026-08-01', 40), ('2026-09-30', 60)])
        historical = self._item('receivables')
        buckets = {bucket['key']: bucket['value'] for bucket in historical['aging_buckets']}
        self.assertEqual(historical['value'], 100)
        self.assertEqual(buckets['period0'], 60)
        self.assertEqual(buckets['period1'], 40)
        self.assertEqual(self._item('receivables_overdue')['value'], 40)
        settlement = self.env['account.move'].create({
            'date': '2026-09-10', 'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [Command.create({'partner_id': self.partner_a.id,
                'account_id': receivable.account_id.id, 'credit': 40, 'date_maturity': '2026-09-10'}),
                Command.create({'account_id': self.company_data['default_account_assets'].id, 'debit': 40})],
        })
        settlement.action_post()
        (receivable.filtered(lambda line: line.balance == 40) +
         settlement.line_ids.filtered(lambda line: line.account_id == receivable.account_id)).reconcile()
        self.assertEqual(invoice.amount_residual, 60)
        after_settlement = self._item('receivables')
        self.assertEqual(after_settlement['value'], 100)
        self.assertEqual({bucket['key']: bucket['value'] for bucket in after_settlement['aging_buckets']}, buckets)
        self.assertEqual(self._item('receivables_overdue')['value'], 40)
        current = self._item('receivables', dict(self.options, as_of='2026-09-30'))
        self.assertEqual(current['value'], 60)
        self.assertEqual(current['aging_buckets'][0]['value'], 60)
        self.assertEqual(self._item('receivables_overdue', dict(self.options, as_of='2026-09-30'))['value'], 0)

    def test_native_foreign_invoice_currency_and_backdated_recognition(self):
        self._mapping()
        currency = self.env.ref('base.EUR')
        currency.active = True
        self.assertNotEqual(currency, self.env.company.currency_id)
        rates = self.env['res.currency.rate']
        for target, rate in [(self.env.company.currency_id, 1), (currency, 2)]:
            domain = [('currency_id', '=', target.id), ('company_id', '=', self.env.company.id),
                      ('name', '=', '2026-08-01')]
            existing = rates.search(domain)
            if existing:
                existing.rate = rate
            else:
                rates.create({'currency_id': target.id, 'company_id': self.env.company.id,
                              'name': '2026-08-01', 'rate': rate})
        invoice = self._invoice(100, posted=False)
        invoice.currency_id = currency
        invoice.action_post()
        self.assertEqual(invoice.amount_total, 100)
        self.assertEqual(invoice.amount_total_signed, 50)
        self.assertEqual(self._item()['value'], 50)
        # A general journal recognition adjustment changes accounting revenue,
        # independently of the posted invoice analysis measure.
        adjustment = self.env['account.move'].create({
            'date': '2026-08-05', 'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [Command.create({'account_id': self.company_data['default_account_revenue'].id, 'credit': 7}),
                         Command.create({'account_id': self.company_data['default_account_assets'].id, 'debit': 7})],
        })
        adjustment.action_post()
        self.assertEqual(self._item()['value'], 57)
        sales = self.dashboard.get_section('sales', self.options)
        self.assertEqual(next(item for item in sales['items'] if item['key'] == 'invoiced_sales')['value'], 50)

    def test_supplier_windows_boundaries_posted_bill_scope_and_native_actions(self):
        report = self.env.ref('account_reports.aged_payable_report')
        expression = self.env.ref('account_reports.aged_payable_line_total')
        self._mapping('payables', report=report, expression=expression)
        for amount, due in [(40, '2026-08-30'), (50, '2026-08-31'),
                            (10, '2026-09-01'), (70, '2026-09-07'),
                            (80, '2026-09-08'), (300, '2026-09-30'),
                            (310, '2026-10-01')]:
            self._invoice(amount, 'in_invoice', due_date=due)
        self._invoice(999, 'in_invoice', due_date='2026-09-01', posted=False)
        self._invoice(777, 'in_invoice', invoice_date='2026-09-01', due_date='2026-09-01')
        self._invoice(25, 'in_refund', due_date='2026-09-01')
        self._invoice(555, 'out_invoice', due_date='2026-09-01')
        self.env.flush_all()
        result = self.dashboard.get_section('finance', self.options)
        windows = {item['key']: item for item in result['supplier_windows']}
        expected = {'supplier_overdue': 40, 'supplier_today': 50,
                    'supplier_due_7': 80, 'supplier_due_30': 460}
        for key, value in expected.items():
            self.assertEqual(windows[key]['status'], 'ready', windows[key])
            self.assertEqual(windows[key]['value'], value)
            action = self.dashboard.open_report(key, self.options)
            self.assertEqual(action['params']['options'], windows[key]['provenance']['options'])
            rebuilt = report.with_context(action['context']).get_options(action['params']['options'])
            self.assertEqual(rebuilt['forced_domain'], action['params']['options']['forced_domain'])
            self.assertFalse(report.get_options(rebuilt).get('forced_domain'))
            self.assertFalse(report.get_options(rebuilt).get('report_title'))
            # RPC and native export serialize tuple domains to JSON lists.
            serialized = json.loads(json.dumps(rebuilt))
            native = report.get_report_information(serialized)
            group = next(iter(rebuilt['column_groups']))
            self.assertEqual(native['column_groups_totals'][group][expression.id]['value'], value)
            self.assertIn(windows[key]['label'], native['report']['name'])
            self.assertIn(windows[key]['label'], report.get_default_report_filename(rebuilt, 'xlsx'))
            self.assertIn('2026-08-31', report.get_default_report_filename(rebuilt, 'xlsx'))
            printable = report.get_options(dict(serialized, export_mode='print'))
            html = report._get_pdf_export_html(printable, report._get_lines(printable))
            self.assertIn(windows[key]['label'], str(html))
            self.assertIn('2026-08-31', str(html))
            exported = report.export_to_xlsx(serialized)
            with zipfile.ZipFile(io.BytesIO(exported['file_content'])) as archive:
                strings = archive.read('xl/sharedStrings.xml').decode()
                sheet = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
                ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                numbers = [float(c.find('x:v', ns).text) for c in sheet.findall('.//x:c', ns)
                           if c.get('t') not in ('s', 'inlineStr') and c.find('x:v', ns) is not None]
                self.assertEqual(numbers[-1], value, 'Native XLSX must retain the payment-window total')
            self.assertIn(windows[key]['label'], strings)
            self.assertIn('2026-08-31', strings)
            self.assertTrue(action['params']['ignore_session'])
        # Full native AP preserves standalone credit notes; window cards do not
        # silently use them to net unrelated supplier bills.
        self.assertEqual(next(i for i in result['items'] if i['key'] == 'payables')['value'], 835)
        with self.assertRaises(ValidationError):
            self.dashboard.open_report('supplier_due_7', self.options, 'invented')
        reader = new_test_user(self.env, login='payment_window_denied',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user')
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_report('supplier_due_7', self.options)
        other = self.env['res.company'].create({'name': 'Other payment window company'})
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).get_section('finance', dict(self.options, company_id=other.id))

    def test_supplier_windows_installments_and_historical_settlement(self):
        self._mapping('payables', report=self.env.ref('account_reports.aged_payable_report'),
                      expression=self.env.ref('account_reports.aged_payable_line_total'))
        terms = self.env['account.payment.term'].create({
            'name': 'Payment windows 40 percent now and 60 after 30 days',
            'line_ids': [Command.clear(),
                         Command.create({'value': 'percent', 'value_amount': 40, 'nb_days': 0}),
                         Command.create({'value': 'percent', 'value_amount': 60, 'nb_days': 30})],
        })
        bill = self._invoice(100, 'in_invoice', invoice_date='2026-08-31', posted=False)
        bill.invoice_payment_term_id = terms
        bill.action_post()
        payable = bill.line_ids.filtered(lambda line: line.account_id.account_type == 'liability_payable')
        self.assertEqual(sorted((str(line.date_maturity), line.balance) for line in payable),
                         [('2026-08-31', -40), ('2026-09-30', -60)])
        settlement = self.env['account.move'].create({
            'date': '2026-09-10', 'journal_id': self.company_data['default_journal_misc'].id,
            'line_ids': [Command.create({'partner_id': self.partner_a.id,
                'account_id': payable.account_id.id, 'debit': 40, 'date_maturity': '2026-09-10'}),
                Command.create({'account_id': self.company_data['default_account_assets'].id, 'credit': 40})],
        })
        settlement.action_post()
        (payable.filtered(lambda line: line.balance == -40) +
         settlement.line_ids.filtered(lambda line: line.account_id == payable.account_id)).reconcile()
        self.assertEqual(bill.amount_residual, 60)
        windows = {i['key']: i['value'] for i in self.dashboard.get_section('finance', self.options)['supplier_windows']}
        self.assertEqual(windows, {'supplier_overdue': 0, 'supplier_today': 40,
                                  'supplier_due_7': 0, 'supplier_due_30': 60})
        after = {i['key']: i['value'] for i in self.dashboard.get_section(
            'finance', dict(self.options, as_of='2026-09-30'))['supplier_windows']}
        self.assertEqual(after, {'supplier_overdue': 0, 'supplier_today': 60,
                                'supplier_due_7': 0, 'supplier_due_30': 0})

    def test_full_overdue_native_buckets_boundaries_credits_and_maturity_fallback(self):
        for metric, prefix, move_type, refund_type, account_key, debit, credit in [
            ('receivables', 'aged_receivable', 'out_invoice', 'out_refund',
             'default_account_receivable', 7, 0),
            ('payables', 'aged_payable', 'in_invoice', 'in_refund',
             'default_account_payable', 0, 7),
        ]:
            report = self.env.ref(f'account_reports.{prefix}_report')
            expression = self.env.ref(f'account_reports.{prefix}_line_total')
            self._mapping(metric, report=report, expression=expression)
            for amount, due in [(10, '2026-08-30'), (20, '2026-07-31'),
                                (30, '2026-07-01'), (40, '2026-06-01'), (50, '2026-05-01'),
                                (80, '2026-08-31'), (90, '2026-09-01')]:
                self._invoice(amount, move_type, invoice_date='2026-01-01', due_date=due)
            self._invoice(200, refund_type, due_date='2026-08-30')
            self._invoice(999, move_type, posted=False, due_date='2026-08-30')
            self._invoice(888, move_type, invoice_date='2026-09-01', due_date='2026-09-01')
            # A standalone journal item has no maturity. Its native fallback is
            # the accounting date; do not exclude it as an invoice-only scope.
            account = self.company_data[account_key]
            entry = self.env['account.move'].create({
                'date': '2026-08-29', 'journal_id': self.company_data['default_journal_misc'].id,
                'line_ids': [Command.create({'partner_id': self.partner_a.id,
                    'account_id': account.id, 'debit': debit, 'credit': credit,
                    'date_maturity': '2026-08-29'}),
                    Command.create({'account_id': self.company_data['default_account_assets'].id,
                                    'debit': credit, 'credit': debit})],
            })
            entry.action_post()
            # The ORM requires maturity on AR/AP lines. Use a rolled-back SQL
            # legacy-data fixture solely to exercise the report's explicit NULL
            # fallback (not production code or a dashboard calculation).
            line = entry.line_ids.filtered(lambda row: row.account_id == account)
            self.env.flush_all()
            self.cr.execute('UPDATE account_move_line SET date_maturity = NULL WHERE id = %s', [line.id])
            line.invalidate_recordset(['date_maturity'])
            key = metric + '_overdue'
            item = self._item(key)
            self.assertEqual(item['status'], 'ready', item)
            self.assertEqual(item['value'], -43)
            self.assertEqual(item['source_kind'], 'report_derived')
            self.assertEqual(item['provenance']['composition']['excluded_bucket'], 'period0')
            self.assertEqual(len(item['provenance']['composition']['expression_ids']), 5)
            self.assertEqual(self._item(metric)['value'], 127)
            action = self.dashboard.open_report(key, self.options)
            self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
            self.assertTrue(action['params']['ignore_session'])
            rebuilt = report.with_context(action['context']).get_options(action['params']['options'])
            serialized = json.loads(json.dumps(rebuilt))
            native = report.get_report_information(serialized)
            group = next(iter(rebuilt['column_groups']))
            self.assertEqual(native['column_groups_totals'][group][expression.id]['value'], -43)
            self.assertIn(item['label'], native['report']['name'])
            # Leaving the scoped action must restore ordinary full aging.
            full = report.get_options(serialized)
            self.assertFalse(full.get('forced_domain'))
            self.assertFalse(full.get('adams_overdue_metric'))
            self.assertFalse(full.get('report_title'))
            full_native = report.get_report_information(full)
            self.assertEqual(full_native['column_groups_totals'][next(iter(full['column_groups']))][expression.id]['value'], 127)
            printable = report.get_options(dict(serialized, export_mode='print'))
            self.assertEqual(printable['forced_domain'], rebuilt['forced_domain'])
            html = report._get_pdf_export_html(printable, report._get_lines(printable))
            self.assertIn(item['label'], str(html))
            exported = report.export_to_xlsx(serialized)
            with zipfile.ZipFile(io.BytesIO(exported['file_content'])) as archive:
                strings = archive.read('xl/sharedStrings.xml').decode()
                sheet = ElementTree.fromstring(archive.read('xl/worksheets/sheet1.xml'))
                ns = {'x': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                numbers = [float(c.find('x:v', ns).text) for c in sheet.findall('.//x:c', ns)
                           if c.get('t') not in ('s', 'inlineStr') and c.find('x:v', ns) is not None]
            self.assertEqual(numbers[-1], -43)
            self.assertIn(item['label'], strings)
            if metric == 'payables':
                windows = self.dashboard.get_section('finance', self.options)['supplier_windows']
                self.assertEqual(next(row['value'] for row in windows if row['key'] == 'supplier_overdue'), 150)
        summary = self.dashboard.export_summary(self.options)
        for label in ('Overdue receivables', 'Overdue payables'):
            self.assertEqual(next(row['value'] for row in summary['print_rows'] if row['metric'] == label), -43)
            self.assertIn(label + ',-43', summary['content'])

    def test_native_aging_bucket_actions_reconcile_and_preserve_export_scope(self):
        for metric, prefix, move_type, refund_type in [
            ('receivables', 'aged_receivable', 'out_invoice', 'out_refund'),
            ('payables', 'aged_payable', 'in_invoice', 'in_refund'),
        ]:
            report = self.env.ref(f'account_reports.{prefix}_report')
            expression = self.env.ref(f'account_reports.{prefix}_line_total')
            self._mapping(metric, report=report, expression=expression)
            for amount, due in [(80, '2026-08-31'), (10, '2026-08-30'),
                                (20, '2026-07-31'), (30, '2026-07-01'),
                                (40, '2026-06-01'), (50, '2026-05-01')]:
                self._invoice(amount, move_type, invoice_date='2026-01-01', due_date=due)
            self._invoice(25, refund_type, due_date='2026-08-30')
            self._invoice(999, move_type, posted=False, due_date='2026-08-30')
            expected = {bucket['key']: bucket['value'] for bucket in self._item(metric)['aging_buckets']}
            for period, value in expected.items():
                action = self.dashboard.open_report(metric, self.options, 'aging_bucket', period)
                self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
                rebuilt = report.with_context(action['context']).get_options(action['params']['options'])
                serialized = json.loads(json.dumps(rebuilt))
                native = report.get_report_information(serialized)
                group = next(iter(serialized['column_groups']))
                self.assertEqual(native['column_groups_totals'][group][expression.id]['value'], value)
                printable = report.get_options(dict(serialized, export_mode='print'))
                self.assertEqual(printable['forced_domain'], rebuilt['forced_domain'])
                self.assertIn('2026-08-31', report.get_default_report_filename(printable, 'xlsx'))
                full = report.get_options(serialized)
                self.assertFalse(full.get('adams_aging_bucket'))
                self.assertFalse(full.get('forced_domain'))
                for changes in [{'forced_domain': []}, {'aging_interval': 15},
                                {'companies': []}, {'all_entries': True},
                                {'adams_supplier_window': 'supplier_today'}]:
                    with self.assertRaises(ValidationError):
                        report.get_report_information(dict(serialized, **changes))
        for period in (True, [], 'period6', 'total'):
            with self.assertRaises(ValidationError):
                self.dashboard.open_report('receivables', self.options, 'aging_bucket', period)
        reader = new_test_user(self.env, login='aging_bucket_denied',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user')
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_report('receivables', self.options, 'aging_bucket', 'period1')

    def test_full_overdue_rejects_changed_scope_mapping_and_denied_user(self):
        report = self.env.ref('account_reports.aged_receivable_report')
        mapping = self._mapping('receivables', report=report,
                                expression=self.env.ref('account_reports.aged_receivable_line_total'))
        self.assertEqual(self._item('receivables_overdue')['value'], 0)
        action = self.dashboard.open_report('receivables_overdue', self.options)
        options = action['params']['options']
        for changes in [{'all_entries': True}, {'aging_based_on': 'base_on_invoice_date'},
                        {'aging_interval': 15}, {'forced_domain': []},
                        {'adams_overdue_metric': 'supplier_overdue'},
                        {'companies': []}]:
            with self.assertRaises(ValidationError):
                report.get_report_information(dict(options, **changes))
        with self.assertRaises(ValidationError):
            self.dashboard.open_report('receivables_overdue', self.options, 'partner_id', self.partner_a.id)
        reader = new_test_user(self.env, login='full_overdue_denied',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user')
        denied = self._item('receivables_overdue', dashboard=self.dashboard.with_user(reader))
        self.assertEqual(denied['status'], 'restricted')
        self.assertIsNone(denied['value'])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_report('receivables_overdue', self.options)
        with self.assertRaises(AccessError):
            report.with_user(reader).get_report_information(options)
        mapping.definition_note = 'Definition changed; approval must be renewed.'
        self.assertEqual(self._item('receivables_overdue')['status'], 'not_configured')
        with self.assertRaises(ValidationError):
            self.dashboard.open_report('receivables_overdue', self.options)
        with self.assertRaises(ValidationError):
            report.get_report_information(options)

    def test_financial_trends_batch_shares_native_report_month_and_preserves_values(self):
        self._mapping('revenue')
        self._mapping('gross_profit', expression=self.env.ref('account_reports.account_financial_report_gross_profit0_balance'))
        self._invoice(100, invoice_date='2026-07-20')
        self._invoice(25, 'out_refund', invoice_date='2026-08-15')
        options = dict(self.options, date_from='2026-07-15', date_to='2026-09-10')
        report_type = type(self.pnl)
        original = report_type.get_report_information
        calls = []

        def evaluate(report, prepared):
            calls.append((report.id, prepared['date']['date_from'], prepared['date']['date_to']))
            return original(report, prepared)

        with patch.object(report_type, 'get_report_information', evaluate):
            result = self.dashboard.get_financial_trends(['revenue', 'gross_profit', 'profit'], options)
        self.assertEqual(calls, [(self.pnl.id, '2026-07-15', '2026-07-31'),
                                 (self.pnl.id, '2026-08-01', '2026-08-31'),
                                 (self.pnl.id, '2026-09-01', '2026-09-10')])
        self.assertEqual(result['company_id'], self.env.company.id)
        for key in ('revenue', 'gross_profit'):
            self.assertEqual([row['value'] for row in result['series'][key]['rows']], [100, -25, 0])
            self.assertEqual(result['series'][key]['generated_at'], result['generated_at'])
        self.assertEqual(result['series']['profit'], {'status': 'not_configured', 'rows': []})
        # No persistent cache: native changes are visible on the next request.
        self._invoice(20, invoice_date='2026-08-20')
        self.assertEqual(self.dashboard.get_financial_trends(['revenue'], options)['series']['revenue']['rows'][1]['value'], -5)
        for invalid in ([], 'revenue', ['payables'], [True], ['revenue'] * 7):
            with self.assertRaises(ValidationError):
                self.dashboard.get_financial_trends(invalid, options)
