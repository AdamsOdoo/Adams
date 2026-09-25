"""Finance: revenue and profit, monthly trend, bank & cash, receivables and payables.

With the Enterprise Accounting reports (``account_reports``) installed, the figures come
from the native engines: Profit and Loss (revenue, gross and net profit), the Balance
Sheet line "Bank and Cash Accounts" expanded by account, and the Aged Receivable / Aged
Payable reports. Without them, or when a report cannot represent the dashboard's scope,
the same figures come from posted journal items grouped by account type. The monthly
chart and the Expected view always use posted journal items, as their captions say.

Every total is one grouped query (``_read_group``) or one report evaluation per section.
"""
import logging
import math
from collections import defaultdict
from datetime import timedelta

import psycopg2
from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Domain
from odoo.tools.misc import format_date, formatLang

_logger = logging.getLogger(__name__)

INCOME = ('income',)
DIRECT_COST = ('expense_direct_cost',)
PL_TYPES = ('income', 'income_other', 'expense_direct_cost', 'expense', 'expense_other', 'expense_depreciation')
OPEN_TYPES = {'receivables': 'asset_receivable', 'payables': 'liability_payable'}
VIEWS = ('aged', 'expected')
TREND_MONTHS = 12
DRAWER_ROWS = 25

# Standard Enterprise report records, resolved at runtime (never referenced in data files).
PNL_EXPRESSIONS = {
    'revenue': ('account_reports.account_financial_report_revenue0_balance', 'REV'),
    'gross_profit': ('account_reports.account_financial_report_gross_profit0_balance', 'GRP'),
    'net_profit': ('account_reports.account_financial_report_net_profit0_balance', 'NEP'),
}
PNL_REPORT = 'account_reports.profit_and_loss'
BS_REPORT = 'account_reports.balance_sheet'
BANK_LINE = 'account_reports.account_financial_report_bank_view0'
AGED_REPORTS = {
    'receivables': ('account_reports.aged_receivable_report', 'account_reports.aged_receivable_line_total'),
    'payables': ('account_reports.aged_payable_report', 'account_reports.aged_payable_line_total'),
}
# Errors a report evaluation can raise when it cannot represent the scope; the figure
# then comes from journal items instead.
ENGINE_ERRORS = (UserError, KeyError, TypeError, ValueError, AttributeError, StopIteration, psycopg2.Error)


class UnsupportedScope(Exception):
    """The native report cannot give this figure for the dashboard's scope (the message says why);
    the dashboard then uses journal items."""


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_finance(self, scope):
        """Finance widgets: ``kpis``, ``trend``, ``bank_cash``, ``receivables``, ``payables``."""
        currency = scope['company'].currency_id
        pnl = self._fin_pnl(scope)
        bank = self._fin_bank_cash(scope)
        open_items = {kind: self._fin_open_items(scope, kind) for kind in OPEN_TYPES}
        invoices = self.env['account.move'].search_count([
            ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
            ('company_id', 'in', scope['companies'].ids),
            ('date', '>=', scope['date_from']), ('date', '<=', scope['date_to']),
        ])
        return {
            'currency': {'name': currency.name, 'symbol': currency.symbol,
                         'position': currency.position, 'digits': currency.decimal_places},
            'kpis': {
                **{key: pnl[key] for key in ('revenue', 'gross_profit', 'net_profit')},
                'invoices': invoices,
                'bank_cash': bank['total'],
                'bank_cash_accounts': sum(1 for row in bank['rows'] if not currency.is_zero(row['balance'])),
                'receivables': open_items['receivables']['total'],
                'receivables_overdue': open_items['receivables']['overdue'],
                'payables': open_items['payables']['total'],
                'payables_overdue': open_items['payables']['overdue'],
                'source': pnl['source'],
            },
            'trend': self._fin_trend(scope),
            'bank_cash': bank,
            **open_items,
        }

    # ------------------------------------------------------------------ helpers

    def _fin_domain(self, scope, *terms):
        return Domain.AND([
            [('parent_state', '=', 'posted'), ('company_id', 'in', scope['companies'].ids)], *terms,
        ])

    def _fin_convert(self, scope, amount, company, day):
        """``amount`` in ``company``'s currency, in the dashboard company's currency."""
        target = scope['company'].currency_id
        if company.currency_id == target or not amount:
            return amount
        return company.currency_id._convert(amount, target, scope['company'], day)

    def _fin_format(self, amount):
        return formatLang(self.env, amount, digits=0)

    def _fin_buckets(self, today):
        """``{view: [(key, label, first due date, last due date)]}``, bounds inclusive or None."""
        day = lambda n: today + timedelta(days=n)  # noqa: E731
        _ = self.env._
        return {
            'aged': [
                ('not_due', _('Not due'), today, None),
                ('d30', _('1–30 days'), day(-30), day(-1)),
                ('d60', _('31–60 days'), day(-60), day(-31)),
                ('d90', _('61–90 days'), day(-90), day(-61)),
                ('older', _('Over 90 days'), None, day(-91)),
            ],
            # Columns of the native Aged Receivable/Payable reports (30-day interval), same ranges.
            'aged_native': [
                ('period0', _('Not due'), today, None),
                ('period1', _('1–30 days'), day(-30), day(-1)),
                ('period2', _('31–60 days'), day(-60), day(-31)),
                ('period3', _('61–90 days'), day(-90), day(-61)),
                ('period4', _('91–120 days'), day(-120), day(-91)),
                ('period5', _('Over 120 days'), None, day(-121)),
            ],
            'expected': [
                ('overdue', _('Overdue'), None, day(-1)),
                ('next7', _('Next 7 days'), today, day(7)),
                ('d8_30', _('8–30 days'), day(8), day(30)),
                ('d31_60', _('31–60 days'), day(31), day(60)),
                ('later', _('Later'), day(61), None),
            ],
        }

    def _fin_due_domain(self, first, last):
        """Lines due between ``first`` and ``last``; the entry date stands in for a missing due date."""
        def within(fname):
            terms = [(fname, '!=', False)]
            if first:
                terms.append((fname, '>=', fields.Date.to_string(first)))
            if last:
                terms.append((fname, '<=', fields.Date.to_string(last)))
            return Domain.AND([[term] for term in terms])
        return within('date_maturity') | (Domain('date_maturity', '=', False) & within('date'))

    def _fin_open_domain(self, scope, kind):
        return self._fin_domain(scope, [
            ('account_id.account_type', '=', OPEN_TYPES[kind]), ('reconciled', '=', False),
            ('date', '<=', fields.Date.to_string(scope['today'])),
        ])

    def _fin_args(self, args):
        """Validated drawer/action arguments for the open-items drawer."""
        kind, view, bucket = args.get('kind'), args.get('view', 'aged'), args.get('bucket')
        partner_id = args.get('partner_id')
        if kind not in OPEN_TYPES or view not in VIEWS:
            raise ValidationError(self.env._('Unknown detail.'))
        today = fields.Date.context_today(self)
        ranges = self._fin_buckets(today)
        buckets = {b[0]: b for b in ranges[view] + (ranges['aged_native'] if view == 'aged' else [])}
        if bucket is not None and bucket not in buckets:
            raise ValidationError(self.env._('Unknown detail.'))
        if partner_id is not None and (type(partner_id) is not int or partner_id <= 0):
            raise ValidationError(self.env._('Unknown detail.'))
        return kind, view, buckets.get(bucket), partner_id

    def _fin_scope(self, args):
        return self._period_scope('finance', args.get('period') or 'month', args.get('date_from'), args.get('date_to'))

    def _fin_items_action(self, name, domain):
        """Native Journal Items list restricted to ``domain``."""
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all')
        action.update(name=name, domain=list(domain), context={}, target='current')
        return action

    # ------------------------------------------------------------------ native report engine

    def _fin_engine(self):
        """True when the Enterprise report engine (``account_reports``) is installed."""
        return hasattr(self.env['account.report'], 'get_report_information')

    def _fin_native(self, compute, what):
        """Run a native report evaluation in a savepoint; None (journal items instead) on failure."""
        if not self._fin_engine():
            return None
        try:
            with self.env.cr.savepoint():
                return compute()
        except UnsupportedScope as error:
            # Expected: a scope the native report cannot represent; journal items give the figure.
            _logger.info('Executive Dashboard: %s engine not used: %s', what, error)
            return None
        except (AccessError, *ENGINE_ERRORS) as error:
            _logger.warning('Executive Dashboard: %s engine not used (%s: %s)', what, type(error).__name__, error)
            return None

    def _fin_report(self, xmlid):
        """The Enterprise report record ``xmlid`` when its engine is installed, else None."""
        if not self._fin_engine():
            return None
        record = self.env.ref(xmlid, raise_if_not_found=False)
        if record is None or record._name != 'account.report' or not record.active:
            return None
        return record if hasattr(record, 'get_report_information') else None

    def _fin_expression(self, key):
        """Balance expression of Odoo's standard P&L line for ``key`` (None: journal items instead)."""
        xmlid, code = PNL_EXPRESSIONS[key]
        expression = self.env.ref(xmlid, raise_if_not_found=False)
        if expression is not None and expression._name == 'account.report.expression':
            return expression
        report = self._fin_report(PNL_REPORT)
        line = report and report.line_ids.filtered(lambda l: l.code == code)[:1]
        return line and line.expression_ids.filtered(lambda e: e.label == 'balance')[:1]

    def _fin_options(self, report, date_from, date_to, **extra):
        """Native options for these dates and the dashboard's companies (raises UnsupportedScope otherwise)."""
        previous = {
            'selected_variant_id': report.id,
            'date': {'mode': 'range' if date_from else 'single', 'filter': 'custom',
                     'date_from': fields.Date.to_string(date_from) if date_from else False,
                     'date_to': fields.Date.to_string(date_to)},
            'all_entries': False, 'unfold_all': False, 'unfolded_lines': [],
            'comparison': {'filter': 'no_comparison', 'number_period': 0},
            **extra,
        }
        options = report.get_options(previous)
        if (options.get('report_id') != report.id
                or options.get('all_entries')
                or options.get('date', {}).get('date_to') != fields.Date.to_string(date_to)
                or options.get('date', {}).get('mode') != ('range' if date_from else 'single')
                or (date_from and options['date'].get('date_from') != fields.Date.to_string(date_from))
                or {company['id'] for company in options.get('companies', [])} != set(self.env.companies.ids)
                or len(options.get('column_groups', {})) != 1
                or any(options.get(k) != v for k, v in extra.items())):
            raise UnsupportedScope('the report changed the requested dates, companies or columns')
        return options

    def _fin_totals(self, report, options):
        information = report.get_report_information(options)
        group = next(iter(options['column_groups']))
        return information['column_groups_totals'][group]

    @staticmethod
    def _fin_number(value):
        if type(value) not in (int, float) or not math.isfinite(value):
            raise UnsupportedScope('the report returned a non-numeric value')
        return value

    def _fin_report_action(self, report, options):
        return {'type': 'ir.actions.client', 'tag': 'account_report', 'name': report.display_name,
                'context': {'report_id': report.id},
                'params': {'options': options, 'ignore_session': True}}

    # ------------------------------------------------------------------ profit and loss

    def _fin_pl_figures(self, by_type):
        """Revenue, gross and net profit from ``{account_type: balance}`` (credit is negative)."""
        income = lambda types: -sum(by_type.get(t, 0.0) for t in types)  # noqa: E731
        revenue = income(INCOME)
        return {'revenue': revenue, 'gross_profit': revenue + income(DIRECT_COST), 'net_profit': income(PL_TYPES)}

    def _fin_pl_journal(self, scope, date_from, date_to, monthly=False):
        """``{month or None: {account_type: balance}}`` from posted journal items."""
        groupby = ['company_id', 'account_id.account_type'] + (['date:month'] if monthly else [])
        rows = self.env['account.move.line']._read_group(
            self._fin_domain(scope, [
                ('date', '>=', fields.Date.to_string(date_from)), ('date', '<=', fields.Date.to_string(date_to)),
                ('account_id.account_type', 'in', PL_TYPES),
            ]), groupby, ['balance:sum'])
        result = {}
        for company, account_type, *month, balance in rows:
            month = fields.Date.to_date(month[0]) if month else None
            day = min(month + relativedelta(months=1, days=-1), date_to) if month else date_to
            bucket = result.setdefault(month, {})
            bucket[account_type] = bucket.get(account_type, 0.0) + self._fin_convert(scope, balance, company, day)
        return result

    def _fin_pnl(self, scope):
        """Revenue, gross profit and net profit for the period, with their ``source``."""
        native = self._fin_native(lambda: self._fin_pnl_report(scope), 'Profit and Loss')
        if native:
            return dict(native, source='report')
        by_type = self._fin_pl_journal(scope, scope['date_from'], scope['date_to']).get(None, {})
        return dict(self._fin_pl_figures(by_type), source='journal')

    def _fin_pnl_report(self, scope):
        """The three figures from the native P&L lines (one evaluation per report), or None."""
        expressions = {key: self._fin_expression(key) for key in PNL_EXPRESSIONS}
        if not all(expressions.values()):
            return None
        totals = {}
        for expression in expressions.values():
            report = expression.report_line_id.report_id
            if report not in totals:
                if not hasattr(report, 'get_report_information'):
                    return None
                totals[report] = self._fin_totals(
                    report, self._fin_options(report, scope['date_from'], scope['date_to']))
        return {key: self._fin_number(totals[expression.report_line_id.report_id][expression.id]['value'])
                for key, expression in expressions.items()}

    def _fin_trend(self, scope):
        """Revenue and net profit for the 12 months ending with the period's last month."""
        end = scope['date_to']
        start = end.replace(day=1) - relativedelta(months=TREND_MONTHS - 1)
        by_month = self._fin_pl_journal(scope, start, end, monthly=True)
        months = []
        for i in range(TREND_MONTHS):
            month = start + relativedelta(months=i)
            figures = self._fin_pl_figures(by_month.get(month, {}))
            months.append({'month': fields.Date.to_string(month),
                           'revenue': figures['revenue'], 'net_profit': figures['net_profit']})
        last_day = end.replace(day=1) + relativedelta(months=1, days=-1)
        return {'months': months, 'partial': end < last_day}

    # ------------------------------------------------------------------ bank and cash

    def _fin_bank_cash(self, scope):
        """Accounts under "Bank and Cash Accounts" with their balance as of today, and the total."""
        balances = self._fin_native(lambda: self._fin_bank_cash_report(scope), 'Balance Sheet')
        source = 'report' if balances is not None else 'journal'
        if balances is None:
            balances = {}
            rows = self.env['account.move.line']._read_group(
                self._fin_domain(scope, [('date', '<=', fields.Date.to_string(scope['today'])),
                                         ('account_id.account_type', '=', 'asset_cash')]),
                ['account_id', 'company_id'], ['balance:sum'])
            for account, company, balance in rows:
                balances[account.id] = balances.get(account.id, 0.0) + self._fin_convert(
                    scope, balance, company, scope['today'])
        accounts = self.env['account.account'].browse(balances)
        # Account codes are company dependent: show each one in a company it belongs to.
        rows = sorted(({'id': account.id, 'code': self._fin_code(account), 'name': account.name,
                        'balance': balances[account.id]} for account in accounts),
                      key=lambda row: -row['balance'])
        return {'rows': rows, 'total': sum(balances.values()), 'source': source}

    def _fin_code(self, account):
        company = self.env.company if self.env.company in account.company_ids else account.company_ids[:1]
        return account.with_company(company).code or ''

    def _fin_bank_line(self):
        return self.env.ref(BANK_LINE, raise_if_not_found=False)

    def _fin_bank_cash_report(self, scope):
        """``{account_id: balance}`` from the Balance Sheet line expanded by account, or None."""
        line = self._fin_bank_line()
        if line is None or not line or line._name != 'account.report.line':
            return None
        report = line.report_id
        expression = line.expression_ids.filtered(lambda e: e.label == 'balance')[:1]
        if not expression or not hasattr(report, '_compute_expression_totals_for_each_column_group'):
            return None
        options = self._fin_options(report, None, scope['today'])
        self.env.flush_all()
        report._init_currency_table(options)
        native = report._compute_expression_totals_for_each_column_group(
            expression, options, groupby_to_expand='account_id', warnings={})
        group = next(iter(options['column_groups']))
        values = native[group][expression]['value']
        if not isinstance(values, list):
            raise UnsupportedScope('the Bank and Cash line did not expand by account')
        return {account_id: self._fin_number(value) for account_id, value in values}

    # ------------------------------------------------------------------ receivables and payables

    def _fin_open_items(self, scope, kind):
        """Open amount of ``kind`` as of today: total, overdue, Aged and Expected buckets."""
        today = scope['today']
        sign = -1 if kind == 'payables' else 1
        domain = self._fin_open_domain(scope, kind)
        Line = self.env['account.move.line']
        rows = Line._read_group(domain & Domain('date_maturity', '!=', False),
                                ['company_id', 'date_maturity:day'], ['amount_residual:sum'])
        rows += Line._read_group(domain & Domain('date_maturity', '=', False),
                                 ['company_id', 'date:day'], ['amount_residual:sum'])
        buckets = self._fin_buckets(today)
        totals = {view: dict.fromkeys((b[0] for b in buckets[view]), 0.0) for view in VIEWS}
        for company, due, residual in rows:
            amount = sign * self._fin_convert(scope, residual, company, today)
            due = fields.Date.to_date(due)
            for view in VIEWS:
                key = next(b[0] for b in buckets[view] if (not b[2] or due >= b[2]) and (not b[3] or due <= b[3]))
                totals[view][key] += amount
        result = {
            view: [{'key': key, 'label': label, 'value': totals[view][key]} for key, label, _f, _l in buckets[view]]
            for view in VIEWS
        }
        result.update(total=sum(totals['expected'].values()), overdue=totals['expected']['overdue'],
                      source='journal', report=False)
        aged = self._fin_native(lambda: self._fin_aged_report(scope, kind, result['total']), 'aged report')
        if aged:
            result.update(aged=aged['buckets'], total=aged['total'], source='report', report=True)
        return result

    def _fin_aged_report(self, scope, kind, journal_total):
        """Native Aged Receivable/Payable total and period columns as of today, or None."""
        report_xmlid, total_xmlid = AGED_REPORTS[kind]
        report = self._fin_report(report_xmlid)
        expression = self.env.ref(total_xmlid, raise_if_not_found=False)
        if report is None or expression is None:
            return None
        options = self._fin_options(report, None, scope['today'],
                                    aging_based_on='base_on_maturity_date', aging_interval=30)
        totals = self._fin_totals(report, options)
        by_label = {expr.label: expr for expr in expression.report_line_id.expression_ids}
        total = self._fin_number(totals[expression.id]['value'])
        # Both reports cover the same open items as of today as the journal items. Amounts owed
        # are shown positive: accept the native total only when it equals the journal total
        # up to its sign convention; otherwise the figures come from journal items.
        tolerance = max(1.0, abs(journal_total) * 0.001)
        # A near-zero total cannot show the native sign convention: use journal items then.
        if abs(journal_total) < tolerance:
            raise UnsupportedScope('nothing open, the sign convention cannot be checked')
        if abs(abs(total) - abs(journal_total)) > tolerance:
            # Not expected: the same open items should give the same total. Worth a warning.
            _logger.warning('Executive Dashboard: %s total %s differs from the open journal items %s',
                            report.display_name, total, journal_total)
            raise UnsupportedScope('the report total differs from the open journal items')
        sign = -1 if (total > 0) != (journal_total > 0) else 1
        buckets = []
        for column in options['columns']:
            label = column.get('expression_label') or ''
            if label.startswith('period') and label[6:].isdigit() and label in by_label:
                value = self._fin_number(totals[by_label[label].id]['value'])
                buckets.append({'key': label, 'label': column['name'], 'value': sign * value})
        if not buckets:
            raise UnsupportedScope('the report returned no ageing columns')
        return {'total': sign * total, 'buckets': buckets}

    # ------------------------------------------------------------------ drawers

    def _drawer_finance_revenue(self, args):
        scope = self._fin_scope(args)
        trend = self._fin_trend(scope)
        _ = self.env._
        rows = [{
            'label': format_date(self.env, month['month'], date_format='MMMM y'),
            'sub': _('Net profit %s', self._fin_format(month['net_profit'])),
            'value': self._fin_format(month['revenue']),
        } for month in reversed(trend['months'])]
        engine = self._fin_report(PNL_REPORT)
        return {'title': _('Revenue & net profit'), 'sub': _('Posted entries · last 12 months'), 'rows': rows,
                'months': trend['months'], 'partial': trend['partial'],
                'action': {'key': 'finance.pnl', 'args': args},
                'dest': _('Profit and Loss') if engine else _('Journal Items')}

    def _drawer_finance_bank_cash(self, args):
        scope = self._fin_scope(args)
        bank = self._fin_bank_cash(scope)
        _ = self.env._
        crumb = _('Bank & Cash')
        rows = [{'label': row['name'], 'sub': row['code'], 'value': self._fin_format(row['balance']),
                 'open': {'key': 'finance.account', 'args': {'account_id': row['id']}, 'crumb': crumb}}
                for row in bank['rows']]
        return {'title': crumb,
                'sub': _('Balance Sheet › Bank and Cash Accounts · as of today') if bank['source'] == 'report'
                else _('Bank and cash accounts · as of today'),
                'rows': rows,
                'total': {'label': _('Total'), 'value': '%s %s' % (self._fin_format(bank['total']),
                                                                   scope['company'].currency_id.name)},
                'action': {'key': 'finance.balance_sheet', 'args': {}},
                'dest': _('Balance Sheet') if self._fin_report(BS_REPORT) else _('Journal Items')}

    def _fin_account(self, args):
        account_id = args.get('account_id')
        if type(account_id) is not int:
            raise ValidationError(self.env._('Unknown detail.'))
        # Only the accounts the Bank & Cash widget lists.
        if account_id not in {row['id'] for row in self._fin_bank_cash(self._fin_scope({}))['rows']}:
            raise ValidationError(self.env._('Unknown detail.'))
        account = self.env['account.account'].browse(account_id)
        self._check_company(account)
        return account

    def _fin_sum(self, scope, domain, measure):
        """Sum of ``measure`` over ``domain`` in the dashboard company's currency."""
        rows = self.env['account.move.line']._read_group(domain, ['company_id'], [f'{measure}:sum'])
        return sum(self._fin_convert(scope, amount, company, scope['today']) for company, amount in rows)

    def _fin_line_amount(self, scope, line, amount):
        return self._fin_convert(scope, amount, line.company_id, scope['today'])

    def _fin_account_domain(self, account):
        scope = self._fin_scope({})
        return self._fin_domain(scope, [('account_id', '=', account.id),
                                        ('date', '<=', fields.Date.to_string(scope['today']))])

    def _drawer_finance_account(self, args):
        account = self._fin_account(args)
        scope = self._fin_scope({})
        domain = self._fin_account_domain(account)
        balance = self._fin_sum(scope, domain, 'balance')
        lines = self.env['account.move.line'].search(domain, order='date desc, id desc', limit=DRAWER_ROWS)
        _ = self.env._
        return {
            'title': account.name, 'sub': '%s · %s' % (self._fin_code(account), _('Latest journal items')),
            'rows': [{'label': line.move_id.name, 'sub': ' · '.join(filter(None, [
                          fields.Date.to_string(line.date), line.partner_id.display_name, line.name])),
                      'value': self._fin_format(self._fin_line_amount(scope, line, line.balance))}
                     for line in lines],
            'total': {'label': _('Balance'), 'value': self._fin_format(balance or 0.0)},
            'action': {'key': 'finance.account', 'args': {'account_id': account.id}},
            'dest': _('Journal Items'),
        }

    def _fin_open_items_domain(self, args):
        kind, view, bucket, partner_id = self._fin_args(args)
        domain = self._fin_open_domain(self._fin_scope({}), kind)
        if bucket:
            domain &= self._fin_due_domain(bucket[2], bucket[3])
        if partner_id:
            domain &= Domain('partner_id', '=', partner_id)
        return kind, view, bucket, partner_id, domain

    def _drawer_finance_open_items(self, args):
        kind, view, bucket, partner_id, domain = self._fin_open_items_domain(args)
        _ = self.env._
        scope = self._fin_scope({})
        sign = -1 if kind == 'payables' else 1
        Line = self.env['account.move.line']
        title = _('Receivables') if kind == 'receivables' else _('Payables')
        if bucket:
            title = '%s · %s' % (title, bucket[1])
        total = self._fin_sum(scope, domain, 'amount_residual')
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            lines = Line.search(domain, order='date_maturity, id', limit=DRAWER_ROWS)
            rows = [{'label': line.move_id.name,
                     'sub': _('Due %s', fields.Date.to_string(line.date_maturity or line.date)),
                     'value': self._fin_format(sign * self._fin_line_amount(scope, line, line.amount_residual))}
                    for line in lines]
            sub = partner.display_name
        else:
            groups = self._fin_partner_groups(scope, domain, sign)
            rows = [{'label': partner.display_name if partner else _('No partner'),
                     'sub': _('%s open items', count),
                     'value': self._fin_format(sign * residual),
                     **({'open': {'key': 'finance.open_items', 'args': dict(args, partner_id=partner.id),
                                  'crumb': title}} if partner else {})}
                    for partner, residual, count in groups]
            sub = _('Open customer invoices · as of today') if kind == 'receivables' \
                else _('Open vendor bills · as of today')
        return {'title': title, 'sub': sub, 'rows': rows,
                'total': {'label': _('Total'), 'value': self._fin_format(sign * (total or 0.0))},
                'action': {'key': 'finance.open_items', 'args': args},
                'dest': self._fin_open_items_dest(kind, bucket, partner_id)}

    def _fin_partner_groups(self, scope, domain, sign):
        """Largest open amounts by partner: ``[(partner, residual, count)]``, residual converted."""
        Line = self.env['account.move.line']
        if len(scope['companies'].currency_id) == 1:
            # One currency: rank and cut in SQL.
            order = 'amount_residual:sum %s' % ('desc' if sign > 0 else 'asc')
            return [(partner, self._fin_convert(scope, residual, scope['companies'][:1], scope['today']), count)
                    for partner, residual, count in Line._read_group(
                        domain, ['partner_id'], ['amount_residual:sum', '__count'], order=order, limit=DRAWER_ROWS)]
        totals, counts = defaultdict(float), defaultdict(int)
        for partner, company, residual, count in Line._read_group(
                domain, ['partner_id', 'company_id'], ['amount_residual:sum', '__count']):
            totals[partner] += self._fin_convert(scope, residual, company, scope['today'])
            counts[partner] += count
        ranked = sorted(totals, key=lambda partner: -sign * totals[partner])[:DRAWER_ROWS]
        return [(partner, totals[partner], counts[partner]) for partner in ranked]

    def _fin_open_items_dest(self, kind, bucket, partner_id):
        _ = self.env._
        if not bucket and not partner_id and self._fin_report(AGED_REPORTS[kind][0]):
            return _('Aged Receivable') if kind == 'receivables' else _('Aged Payable')
        return _('Journal Items')

    # ------------------------------------------------------------------ native screens

    def _action_finance_pnl(self, args):
        scope = self._fin_scope(args)
        report = self._fin_report(PNL_REPORT)
        if report:
            try:
                return self._fin_report_action(report, self._fin_options(report, scope['date_from'], scope['date_to']))
            except (UnsupportedScope, *ENGINE_ERRORS):
                pass
        return self._fin_items_action(self.env._('Profit and Loss items'), self._fin_domain(scope, [
            ('date', '>=', fields.Date.to_string(scope['date_from'])),
            ('date', '<=', fields.Date.to_string(scope['date_to'])),
            ('account_id.account_type', 'in', PL_TYPES),
        ]))

    def _action_finance_balance_sheet(self, args):
        scope = self._fin_scope({})
        report = self._fin_report(BS_REPORT)
        if report:
            try:
                return self._fin_report_action(report, self._fin_options(report, None, scope['today']))
            except (UnsupportedScope, *ENGINE_ERRORS):
                pass
        return self._fin_items_action(self.env._('Bank and cash items'), self._fin_domain(scope, [
            ('date', '<=', fields.Date.to_string(scope['today'])), ('account_id.account_type', '=', 'asset_cash'),
        ]))

    def _action_finance_account(self, args):
        account = self._fin_account(args)
        return self._fin_items_action(account.display_name, self._fin_account_domain(account))

    def _action_finance_open_items(self, args):
        kind, view, bucket, partner_id, domain = self._fin_open_items_domain(args)
        report = self._fin_report(AGED_REPORTS[kind][0])
        if report and not bucket and not partner_id:
            try:
                options = self._fin_options(report, None, fields.Date.context_today(self),
                                            aging_based_on='base_on_maturity_date', aging_interval=30)
                return self._fin_report_action(report, options)
            except (UnsupportedScope, *ENGINE_ERRORS):
                pass
        name = self.env._('Open receivables') if kind == 'receivables' else self.env._('Open payables')
        return self._fin_items_action(name, domain)
