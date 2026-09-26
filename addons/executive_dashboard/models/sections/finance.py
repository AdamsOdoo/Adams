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
# Parts of the open items behind the box's chips: invoices (bills) past due, and unapplied
# credits (receivables) or advances and unmatched payments (payables).
SIDES = ('overdue', 'credits')
# P&L figures and the account types each one adds up, in the order of the Profit and Loss.
PNL_PARTS = {
    'revenue': INCOME,
    'gross_profit': INCOME + DIRECT_COST,
    'net_profit': ('income', 'income_other', 'expense_direct_cost', 'expense', 'expense_depreciation',
                   'expense_other'),
}
TREND_MONTHS = 12

# Standard Enterprise report records, resolved at runtime (never referenced in data files).
PNL_EXPRESSIONS = {
    'revenue': ('account_reports.account_financial_report_revenue0_balance', 'REV'),
    'gross_profit': ('account_reports.account_financial_report_gross_profit0_balance', 'GRP'),
    'net_profit': ('account_reports.account_financial_report_net_profit0_balance', 'NEP'),
}
PNL_REPORT = 'account_reports.profit_and_loss'
BS_REPORT = 'account_reports.balance_sheet'
BANK_LINE = 'account_reports.account_financial_report_bank_view0'
GL_REPORT = 'account_reports.general_ledger_report'
PARTNER_LEDGER = 'account_reports.partner_ledger_report'
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
                'bank_cash_accounts': len(bank['rows']),
                'receivables': open_items['receivables']['total'],
                'payables': open_items['payables']['total'],
                'as_of': fields.Date.to_string(scope['as_of']),
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
                # Net of unapplied credits: the Overdue chip shows the past-due invoices alone.
                ('overdue', _('Past due (net)'), None, day(-1)),
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

    def _fin_args(self, args):
        """Validated drawer/action arguments for the open-items drawer."""
        kind, view, bucket = args.get('kind'), args.get('view', 'aged'), args.get('bucket')
        partner_id, side = args.get('partner_id'), args.get('side')
        if kind not in OPEN_TYPES or view not in VIEWS or (side is not None and side not in SIDES):
            raise ValidationError(self.env._('Unknown detail.'))
        # Bucket ranges count from the balance date of the drawer's period.
        ranges = self._fin_buckets(self._fin_scope(args)['as_of'])
        buckets = {b[0]: b for b in ranges[view] + (ranges['aged_native'] if view == 'aged' else [])}
        if bucket is not None and bucket not in buckets:
            raise ValidationError(self.env._('Unknown detail.'))
        if partner_id is not None and (type(partner_id) is not int or partner_id <= 0):
            raise ValidationError(self.env._('Unknown detail.'))
        return kind, view, buckets.get(bucket), partner_id, side

    def _fin_scope(self, args):
        return self._period_scope('finance', args.get('period') or 'month', args.get('date_from'), args.get('date_to'))

    def _fin_items_action(self, name, domain):
        """Native Journal Items list restricted to ``domain``."""
        action = self.env['ir.actions.act_window']._for_xml_id('account.action_account_moves_all')
        action.update(name=name, display_name=name, domain=list(domain), context={}, target='current')
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

    def _fin_options(self, report, date_from, date_to, single_group=True, **extra):
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
                or (single_group and len(options.get('column_groups', {})) != 1)
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

    def _fin_cash_accounts(self, scope):
        """Every active bank and cash account of the dashboard's companies, with or without entries."""
        return self.env['account.account'].search([
            ('account_type', '=', 'asset_cash'), ('active', '=', True),
            ('company_ids', 'in', scope['companies'].ids),
        ])

    def _fin_bank_cash(self, scope):
        """Every bank and cash account with its balance at the period's end (``as_of``), and the total.

        Accounts without entries are listed with a zero balance; accounts under the Balance Sheet
        line that are not of type Bank and Cash (rare) are listed too, so the rows add up to the total.
        """
        as_of = scope['as_of']
        balances = self._fin_native(lambda: self._fin_bank_cash_report(scope), 'Balance Sheet')
        source = 'report' if balances is not None else 'journal'
        if balances is None:
            balances = {}
            rows = self.env['account.move.line']._read_group(
                self._fin_domain(scope, [('date', '<=', fields.Date.to_string(as_of)),
                                         ('account_id.account_type', '=', 'asset_cash')]),
                ['account_id', 'company_id'], ['balance:sum'])
            for account, company, balance in rows:
                balances[account.id] = balances.get(account.id, 0.0) + self._fin_convert(
                    scope, balance, company, as_of)
        for account in self._fin_cash_accounts(scope):
            balances.setdefault(account.id, 0.0)
        accounts = self.env['account.account'].browse(balances)
        # Account codes are company dependent: show each one in a company it belongs to.
        rows = sorted(({'id': account.id, 'code': self._fin_code(account), 'name': account.name,
                        'balance': balances[account.id], 'can_open': account.account_type == 'asset_cash'}
                       for account in accounts),
                      key=lambda row: (-row['balance'], row['code']))
        # One check of the account's native screen (the same report for every account).
        first = next((row for row in rows if row['can_open']), None)
        if first and not self._target({'key': 'finance.account', 'args': {'account_id': first['id']}}):
            for row in rows:
                row['can_open'] = False
        return {'rows': rows, 'total': sum(balances.values()), 'source': source,
                'as_of': fields.Date.to_string(as_of)}

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
        options = self._fin_options(report, None, scope['as_of'])
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

    def _fin_open_base(self, scope, kind):
        """Posted receivable (or payable) items dated on or before the balance date.

        Trade accounts only, like the default Account filter of the Aged Receivable / Aged Payable
        reports: accounts marked Non Trade (for example a VAT receivable) are left out.
        """
        return self._fin_domain(scope, [
            ('account_id.account_type', '=', OPEN_TYPES[kind]), ('account_id.non_trade', '=', False),
            ('date', '<=', fields.Date.to_string(scope['as_of'])),
        ])

    def _fin_open_sums(self, scope, kind, domain=None, groupby=()):
        """Open amounts at the balance date: ``({(company, *groups, due, debit): residual}, {key: count})``.

        ``groupby`` are journal item fields; ``due`` is the due date (the entry date when there is
        none) and ``debit`` says whether the items are debits (invoices for receivables) or credits.
        Matches dated after the balance date (a later payment, or a post-dated cheque at today) are
        added back to the items they settled, as the native Aged reports do, so the figures are the
        open amounts as they were on that day. ``counts`` counts journal items open today only.
        Amounts are in each company's currency.
        """
        base = self._fin_open_base(scope, kind) & Domain(domain or [])
        Line, Partial = self.env['account.move.line'], self.env['account.partial.reconcile']
        # (model, domain, path to the journal item, measure, sign, debit side or None for split).
        sources = [(Line, base & Domain('reconciled', '=', False), '', 'amount_residual', 1, None)]
        later = Domain('max_date', '>', fields.Date.to_string(scope['as_of']))
        if '_later_matches' not in scope:
            # One cheap check per section: usually nothing is matched after the balance date.
            scope['_later_matches'] = bool(Partial.search_count(
                later & Domain('company_id', 'in', scope['companies'].ids), limit=1))
        if scope['_later_matches']:
            sources += [(Partial, later & Domain('debit_move_id', 'any', base), 'debit_move_id.', 'amount', 1, True),
                        (Partial, later & Domain('credit_move_id', 'any', base), 'credit_move_id.', 'amount', -1, False)]
        sums, counts = defaultdict(float), defaultdict(int)
        for Model, source_domain, path, measure, sign, side in sources:
            sides = [(True, Domain('balance', '>', 0)), (False, Domain('balance', '<=', 0))] \
                if side is None else [(side, Domain.TRUE)]
            for debit, side_domain in sides:
                for due_field in ('date_maturity', 'date'):
                    due_domain = Domain(f'{path}date_maturity', '!=' if due_field == 'date_maturity' else '=', False)
                    specs = [f'{path}company_id', *(f'{path}{g}' for g in groupby), f'{path}{due_field}:day']
                    for *groups, due, amount, count in Model._read_group(
                            source_domain & side_domain & due_domain, specs, [f'{measure}:sum', '__count']):
                        key = (*groups, fields.Date.to_date(due), debit)
                        sums[key] += sign * amount
                        if Model is Line:
                            counts[key] += count
        return sums, counts

    def _fin_open_items(self, scope, kind):
        """Open amount of ``kind`` at the balance date: total, overdue, Aged and Expected buckets.

        Amounts owed are positive (customers owe us, we owe suppliers). ``owed_overdue`` is the part
        of the invoices (bills) past due; ``credits`` the unapplied credits, payments and advances,
        which the net figures subtract.
        """
        as_of = scope['as_of']
        sign = -1 if kind == 'payables' else 1
        owed_side = kind == 'receivables'
        sums, _counts = self._fin_open_sums(scope, kind)
        buckets = self._fin_buckets(as_of)
        totals = {view: dict.fromkeys((b[0] for b in buckets[view]), 0.0) for view in VIEWS}
        owed = owed_overdue = credits = 0.0
        for (company, due, debit), residual in sums.items():
            amount = sign * self._fin_convert(scope, residual, company, as_of)
            for view in VIEWS:
                key = next(b[0] for b in buckets[view] if (not b[2] or due >= b[2]) and (not b[3] or due <= b[3]))
                totals[view][key] += amount
            if debit == owed_side:
                owed += amount
                if due < as_of:
                    owed_overdue += amount
            else:
                credits += amount
        result = {
            view: [{'key': key, 'label': label, 'value': totals[view][key]} for key, label, _f, _l in buckets[view]]
            for view in VIEWS
        }
        result.update(total=sum(totals['expected'].values()), overdue=totals['expected']['overdue'],
                      owed=owed, owed_overdue=owed_overdue, credits=credits, difference=0.0,
                      as_of=fields.Date.to_string(as_of), source='journal', report=False)
        aged = self._fin_native(lambda: self._fin_aged_report(scope, kind, result['total']), 'aged report')
        if aged:
            result.update(aged=aged['buckets'], total=aged['total'], difference=result['total'] - aged['total'],
                          source='report', report=True)
        return result

    def _fin_aged_report(self, scope, kind, journal_total):
        """Native Aged Receivable/Payable total and period columns at the balance date, or None."""
        report_xmlid, total_xmlid = AGED_REPORTS[kind]
        report = self._fin_report(report_xmlid)
        expression = self.env.ref(total_xmlid, raise_if_not_found=False)
        if report is None or expression is None:
            return None
        options = self._fin_options(report, None, scope['as_of'],
                                    aging_based_on='base_on_maturity_date', aging_interval=30)
        totals = self._fin_totals(report, options)
        by_label = {expr.label: expr for expr in expression.report_line_id.expression_ids}
        total = self._fin_number(totals[expression.id]['value'])
        # Both native Aged reports show amounts owed as positive (the payable engine reverses the
        # ledger sign), as the dashboard does: the figure is used as it is, never re-signed.
        sign = 1
        tolerance = max(1.0, abs(journal_total) * 0.001)
        if abs(total - journal_total) > tolerance:
            # The report is still the figure shown; the difference is shown next to it.
            _logger.warning('Executive Dashboard: %s total %s differs from the open journal items %s',
                            report.display_name, total, journal_total)
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

    def _drawer_finance_profit(self, args):
        """Revenue, gross profit or net profit (``figure``) of the period, by account: one group
        per account type (Income, Cost of Revenue, Expenses...) with its subtotal. Amounts add to
        the figure: income is positive, costs and expenses negative."""
        figure = args.get('figure')
        if figure not in PNL_PARTS:
            raise ValidationError(self.env._('Unknown detail.'))
        scope, _ = self._fin_scope(args), self.env._
        currency = scope['company'].currency_id
        types = PNL_PARTS[figure]
        by_account = defaultdict(float)
        for company, account, balance in self.env['account.move.line']._read_group(self._fin_domain(scope, [
                ('date', '>=', fields.Date.to_string(scope['date_from'])),
                ('date', '<=', fields.Date.to_string(scope['date_to'])),
                ('account_id.account_type', 'in', types)]), ['company_id', 'account_id'], ['balance:sum']):
            by_account[account] -= self._fin_convert(scope, balance, company, scope['date_to'])
        labels = dict(self.env['account.account']._fields['account_type']._description_selection(self.env))
        period = self._fin_period_args(args)
        groups = []
        for account_type in types:
            accounts = sorted((a for a in by_account if a.account_type == account_type
                               and not currency.is_zero(by_account[a])), key=lambda a: (-abs(by_account[a]), a.id))
            if accounts:
                subtotal = sum(by_account[a] for a in accounts)
                groups.append({'title': '%s · %s' % (labels.get(account_type, account_type), self._fin_format(subtotal)),
                               'rows': [{'label': a.name, 'sub': self._fin_code(a), 'value': self._fin_format(by_account[a]),
                                         'action': {'key': 'finance.account', 'args': dict(period, account_id=a.id)}}
                                        for a in accounts]})
        total = sum(by_account.values())
        title = {'revenue': _('Revenue'), 'gross_profit': _('Gross profit'), 'net_profit': _('Net profit')}[figure]
        pnl = self._fin_pnl(scope)
        note = _('The Profit and Loss report gives %(amount)s %(currency)s for this figure.',
                 amount=self._fin_format(pnl[figure]), currency=currency.name) \
            if pnl['source'] == 'report' and abs(pnl[figure] - total) >= 1 else False
        return {'title': title, 'note': note,
                'sub': _('Posted entries by account · %(date_from)s – %(date_to)s',
                         date_from=format_date(self.env, scope['date_from'], date_format='d MMM y'),
                         date_to=format_date(self.env, scope['date_to'], date_format='d MMM y')),
                'groups': groups,
                'total': {'label': title, 'value': '%s %s' % (self._fin_format(total), currency.name)},
                'action': {'key': 'finance.pnl', 'args': period},
                'dest': _('Profit and Loss') if self._fin_report(PNL_REPORT) else _('Journal Items')}

    def _fin_as_of_label(self, scope):
        return self.env._('as of %s', format_date(self.env, scope['as_of'], date_format='d MMM y'))

    def _fin_period_args(self, args):
        return {key: args[key] for key in ('period', 'date_from', 'date_to') if args.get(key)}

    def _drawer_finance_bank_cash(self, args):
        scope = self._fin_scope(args)
        bank = self._fin_bank_cash(scope)
        _ = self.env._
        period = self._fin_period_args(args)
        # An account opens its General Ledger at once (no intermediate panel).
        rows = [{'label': row['name'], 'sub': row['code'], 'value': self._fin_format(row['balance']),
                 **({'action': {'key': 'finance.account', 'args': dict(period, account_id=row['id'])}}
                    if row['can_open'] else {})}
                for row in bank['rows']]
        source = _('Balance Sheet › Bank and Cash Accounts') if bank['source'] == 'report' \
            else _('Bank and cash accounts')
        return {'title': _('Bank & Cash'), 'sub': '%s · %s' % (source, self._fin_as_of_label(scope)),
                'rows': rows,
                'total': {'label': _('Total'), 'value': '%s %s' % (self._fin_format(bank['total']),
                                                                   scope['company'].currency_id.name)},
                'action': {'key': 'finance.balance_sheet', 'args': period},
                'dest': _('Balance Sheet') if self._fin_report(BS_REPORT) else _('Journal Items')}

    def _fin_account(self, args):
        """A bank, cash, receivable, payable or profit and loss account of the dashboard's companies."""
        account_id = args.get('account_id')
        if type(account_id) is not int or account_id <= 0:
            raise ValidationError(self.env._('Unknown detail.'))
        account = self.env['account.account'].browse(account_id).exists()
        if not account or account.account_type not in ('asset_cash', *OPEN_TYPES.values(), *PL_TYPES) \
                or not account.company_ids & self.env.companies:
            raise ValidationError(self.env._('Unknown detail.'))
        return account

    def _check_finance_account(self, args):
        return self._fin_account(args)

    def _fin_convert_line(self, scope, company, amount):
        return self._fin_convert(scope, amount, company, scope['as_of'])

    def _fin_open_by(self, scope, kind, domain, field):
        """``[(record, residual, count)]`` of the open amounts grouped by ``field`` (converted)."""
        sums, counts = self._fin_open_sums(scope, kind, domain, [field])
        totals, numbers = defaultdict(float), defaultdict(int)
        for (company, record, _due, _debit), residual in sums.items():
            totals[record] += self._fin_convert_line(scope, company, residual)
            numbers[record] += counts[company, record, _due, _debit]
        return [(record, totals[record], numbers[record]) for record in totals]

    def _fin_side_domain(self, kind, side, as_of):
        """Journal items of a chip: invoices (bills) due before ``as_of``, or the credits."""
        owed = Domain('balance', '>', 0) if kind == 'receivables' else Domain('balance', '<', 0)
        if side == 'overdue':
            return owed & self._fin_due_domain(None, as_of - timedelta(days=1))
        return ~owed

    def _fin_open_items_domain(self, args):
        kind, view, bucket, partner_id, side = self._fin_args(args)
        domain = Domain.TRUE
        if bucket:
            domain &= self._fin_due_domain(bucket[2], bucket[3])
        if partner_id:
            domain &= Domain('partner_id', '=', partner_id)
        if side:
            domain &= self._fin_side_domain(kind, side, self._fin_scope(args)['as_of'])
        return kind, view, bucket, partner_id, side, domain

    def _drawer_finance_open_items(self, args):
        kind, view, bucket, partner_id, side, domain = self._fin_open_items_domain(args)
        _ = self.env._
        scope = self._fin_scope(args)
        sign = -1 if kind == 'payables' else 1
        currency = scope['company'].currency_id
        title = _('Receivables') if kind == 'receivables' else _('Payables')
        if bucket:
            title = '%s · %s' % (title, bucket[1])
        if side:
            title = '%s · %s' % (title, self._fin_side_label(kind, side))
        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            sums, _counts = self._fin_open_sums(scope, kind, domain, ['move_id'])
            by_move, due_of = defaultdict(float), {}
            for (company, move, due, _debit), residual in sums.items():
                by_move[move] += self._fin_convert_line(scope, company, residual)
                due_of[move] = min(due, due_of.get(move, due))
            moves, more = self._drawer_page(sorted((m for m in by_move if not currency.is_zero(by_move[m])),
                                                   key=lambda m: (due_of[m], m.id)))
            rows = [{'label': move.name, 'sub': _('Due %s', format_date(self.env, due_of[move], date_format='d MMM y')),
                     'value': self._fin_format(sign * by_move[move])} for move in moves]
            total = sum(by_move.values())
            sub = partner.display_name
        else:
            groups = [(p, r, c) for p, r, c in self._fin_open_by(scope, kind, domain, 'partner_id')
                      if not currency.is_zero(r)]
            total = sum(r for _p, r, _c in groups)
            groups, more = self._drawer_page(sorted(groups, key=lambda g: (-sign * g[1], g[0].id)))
            rows = [{'label': partner.display_name if partner else _('No partner'),
                     'sub': _('%s open items', count),
                     'value': self._fin_format(sign * residual),
                     **({'open': {'key': 'finance.open_items', 'args': dict(args, partner_id=partner.id),
                                  'crumb': title}} if partner else {})}
                    for partner, residual, count in groups]
            label = self._fin_side_label(kind, side) if side == 'credits' else \
                _('Open customer invoices') if kind == 'receivables' else _('Open vendor bills')
            sub = '%s · %s' % (label, self._fin_as_of_label(scope))
        groups, rows_title = [], False
        if not bucket and not partner_id and not side:
            period = self._fin_period_args(args)
            # An account opens its General Ledger at once (no intermediate panel).
            accounts = [
                {'label': account.name, 'sub': self._fin_code(account), 'value': self._fin_format(sign * residual),
                 'action': {'key': 'finance.account', 'args': dict(period, account_id=account.id)}}
                for account, residual, _count in sorted(self._fin_open_by(scope, kind, domain, 'account_id'),
                                                        key=lambda g: -abs(g[1]))]
            if accounts:
                groups, rows_title = [{'title': _('By account'), 'rows': accounts}], _('By partner')
        return {'title': title, 'sub': sub, 'groups': groups, 'rows_title': rows_title, 'rows': rows, 'more': more,
                'total': {'label': _('Total'), 'value': self._fin_format(sign * total)},
                'action': {'key': 'finance.open_items', 'args': args},
                'dest': self._fin_open_items_dest(kind, bucket, partner_id, side)}

    def _fin_side_label(self, kind, side):
        _ = self.env._
        if side == 'overdue':
            return _('Overdue')
        return _('Unapplied credits') if kind == 'receivables' else _('Advances & unmatched payments')

    def _fin_open_items_dest(self, kind, bucket, partner_id, side=None):
        _ = self.env._
        if partner_id:
            return _('Partner Ledger') if self._fin_report(PARTNER_LEDGER) else _('Journal Items')
        if side != 'credits' and self._fin_report(AGED_REPORTS[kind][0]):
            return _('Aged Receivable') if kind == 'receivables' else _('Aged Payable')
        return _('Journal Items')

    def _fin_year_start(self, day):
        return self.env.company.compute_fiscalyear_dates(day)['date_from']

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
        scope = self._fin_scope(args)
        report = self._fin_report(BS_REPORT)
        if report:
            try:
                return self._fin_report_action(report, self._fin_options(report, None, scope['as_of']))
            except (UnsupportedScope, *ENGINE_ERRORS):
                pass
        return self._fin_items_action(self.env._('Bank and cash items'), self._fin_domain(scope, [
            ('date', '<=', fields.Date.to_string(scope['as_of'])), ('account_id.account_type', '=', 'asset_cash'),
        ]))

    def _fin_account_target(self, account, scope):
        """``(action, destination name)`` of an account: the General Ledger with the account
        unfolded (its entries listed), else its journal items (no Enterprise reports).

        A balance account (bank, cash, receivable, payable) runs from the start of the fiscal
        year to the balance date, with its opening balance, so the ledger ends on the
        dashboard's balance; a profit and loss account lists the period's entries, like its
        figure (the ledger may add an opening balance from the fiscal year start).
        """
        _ = self.env._
        profit_loss = account.account_type in PL_TYPES
        if profit_loss:
            start, end = scope['date_from'], scope['date_to']
        else:
            start, end = self._fin_year_start(scope['as_of']), scope['as_of']
        ledger = self._fin_report(GL_REPORT)
        if ledger:
            try:
                options = self._fin_options(ledger, start, end, single_group=False)
                options['unfolded_lines'] = [ledger._get_generic_line_id('account.account', account.id)]
                return self._fin_report_action(ledger, options), _('General Ledger')
            except (UnsupportedScope, *ENGINE_ERRORS):
                pass
        # Every entry up to the balance date (they add up to the balance), or the period's.
        dates = [('date', '<=', fields.Date.to_string(end))]
        if profit_loss:
            dates.append(('date', '>=', fields.Date.to_string(start)))
        return self._fin_items_action(account.display_name, self._fin_domain(scope, [
            ('account_id', '=', account.id), *dates])), _('Journal Items')

    def _action_finance_account(self, args):
        return self._fin_account_target(self._fin_account(args), self._fin_scope(args))[0]

    def _action_finance_open_items(self, args):
        kind, view, bucket, partner_id, side, domain = self._fin_open_items_domain(args)
        scope = self._fin_scope(args)
        as_of = scope['as_of']
        ledger = self._fin_report(PARTNER_LEDGER) if partner_id else None
        if ledger:
            try:
                options = self._fin_options(ledger, self._fin_year_start(as_of), as_of, partner_ids=[partner_id])
                return self._fin_report_action(ledger, options)
            except (UnsupportedScope, *ENGINE_ERRORS):
                pass
        report = self._fin_report(AGED_REPORTS[kind][0])
        # A bucket or the Overdue chip opens the whole Aged report: its columns show the same
        # ranges. The report does not separate credits, so they open their journal items.
        if report and not partner_id and side != 'credits':
            try:
                options = self._fin_options(report, None, as_of,
                                            aging_based_on='base_on_maturity_date', aging_interval=30)
                return self._fin_report_action(report, options)
            except (UnsupportedScope, *ENGINE_ERRORS):
                pass
        # Journal items can only list the items open today (not an earlier day's open amount):
        # the bucket's range is then counted from today and the list says so.
        today_args = {key: value for key, value in args.items() if key not in ('period', 'date_from', 'date_to')}
        _kind, _view, _bucket, _partner, _side, domain = self._fin_open_items_domain(today_args)
        name = self.env._('Open receivables today') if kind == 'receivables' else self.env._('Open payables today')
        if side:
            name = '%s · %s' % (name, self._fin_side_label(kind, side))
        return self._fin_items_action(name, self._fin_open_base(self._fin_scope({}), kind)
                                      & Domain('reconciled', '=', False) & domain)
