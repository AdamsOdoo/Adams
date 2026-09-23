"""Thin adapter over the installed Enterprise report engine; no ledger arithmetic."""
from datetime import timedelta
from dateutil.relativedelta import relativedelta

import hashlib
import json
import logging
import math

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .finance_mapping import METRICS, PERIOD_KEYS, RATIO_KEYS, BUDGET_KEYS

_logger = logging.getLogger(__name__)


class UnsupportedFinancialScope(Exception):
    """The engine returned a scope this adapter cannot represent."""


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'adams.executive.dashboard'

    def _finance_access(self):
        self._authorize()
        # Native accounting reports have broad accounting scope. Dashboard
        # membership alone must never confer access to their SQL-backed totals.
        if not self.env.user.has_group('account.group_account_readonly'):
            raise AccessError(_('Accounting report access is required.'))
        self.env['account.report'].check_access('read')
        self.env['account.move.line'].check_access('read')
        # The native report engine can aggregate through SQL. Preserve field-level
        # restrictions as well as its accounting group and model permissions.
        self.env['account.move.line'].check_field_access_rights('read', [
            'balance', 'debit', 'credit', 'amount_currency', 'account_id',
            'date', 'company_id', 'partner_id', 'date_maturity', 'move_id',
        ])

    def _financial_options(self, report, key, dates, previous_extra=None, budget_id=None):
        report.check_access('read')
        if not report.active or report.use_sections:
            raise UnsupportedFinancialScope()
        period = key in PERIOD_KEYS
        cutoff = dates[1] if period else dates[2]
        previous = {
            'selected_variant_id': report.id,
            'date': {'mode': 'range' if period else 'single', 'filter': 'custom',
                     'date_from': dates[0].isoformat() if period else False,
                     'date_to': cutoff.isoformat()},
            'all_entries': False, 'unfold_all': False, 'unfolded_lines': [],
            'comparison': {'filter': 'no_comparison', 'number_period': 0},
        }
        if key in {'receivables', 'payables'}:
            previous.update(aging_based_on='base_on_maturity_date', aging_interval=30)
        if previous_extra:
            previous.update(previous_extra)
        if budget_id:
            previous['budgets'] = [{'id': budget_id, 'selected': True}]
        options = report.get_options(previous)
        if (options.get('report_id') != report.id
                or options.get('date', {}).get('date_to') != cutoff.isoformat()
                or options.get('all_entries')
                or {company['id'] for company in options.get('companies', [])} != {self.env.company.id}
                or (period and options['date'].get('date_from') != dates[0].isoformat())
                or len(options.get('column_groups', {})) != (3 if budget_id else 1)):
            raise UnsupportedFinancialScope()
        if key in {'receivables', 'payables'} and (
                options.get('aging_based_on') != 'base_on_maturity_date'
                or options.get('aging_interval') != 30):
            raise UnsupportedFinancialScope()
        return options

    def _financial_mapping(self, key):
        return self.env['adams.dashboard.finance.mapping'].search([
            ('company_id', '=', self.env.company.id), ('metric', '=', key),
        ], limit=1)

    def _mapping_ready(self, mapping):
        return bool(mapping and mapping.approved_by and
                    mapping.definition_fingerprint == mapping._fingerprint())

    @api.model
    def get_section(self, section, options):
        if section != 'finance':
            return super().get_section(section, options)
        scoped, dates = self._scope(options)
        currency = scoped.env.company.currency_id
        result = {'items': [], 'supplier_windows': [], 'cash_flow': {'status': 'not_configured', 'rows': []},
                  'cash_breakdown': {'status': 'not_configured'}, 'company_id': scoped.env.company.id,
                  'currency': currency.name, 'digits': currency.decimal_places,
                  'generated_at': fields.Datetime.to_string(fields.Datetime.now())}
        if 'finance' not in scoped._visible_sections():
            return result
        try:
            scoped._finance_access()
        except AccessError:
            result['items'] = [{'key': key, 'status': 'restricted', 'value': None} for key, _label in METRICS]
            result['items'].extend(scoped._overdue_items(result['items']))
            result['cash_flow']['status'] = 'restricted'
            result['cash_breakdown']['status'] = 'restricted'
            return result

        evaluations = {}
        mappings = scoped.env['adams.dashboard.finance.mapping'].search([
            ('company_id', '=', scoped.env.company.id),
        ])
        by_key = {mapping.metric: mapping for mapping in mappings}
        for key, _label in METRICS:
            item = {'key': key, 'status': 'not_configured', 'value': None}
            result['items'].append(item)
            mapping = by_key.get(key)
            if not mapping:
                continue
            try:
                if not scoped._mapping_ready(mapping):
                    continue
                report = mapping.report_id
                cache_key = (report.id, key in PERIOD_KEYS)
                if cache_key not in evaluations:
                    prepared = scoped._financial_options(report, key, dates)
                    # One native evaluation supplies all mapped expressions for
                    # this report/scope. No total is made from a paged row set.
                    evaluations[cache_key] = (prepared, report.get_report_information(prepared))
                prepared, information = evaluations[cache_key]
                group_key = next(iter(prepared['column_groups']))
                totals = information['column_groups_totals'].get(group_key, {})
                expression_result = totals.get(mapping.expression_id.id)
                if expression_result is None:
                    raise UnsupportedFinancialScope()
                value = expression_result.get('value')
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise UnsupportedFinancialScope()
                if key in RATIO_KEYS:
                    denominator = totals.get(mapping.denominator_expression_id.id, {}).get('value')
                    if type(denominator) not in (int, float) or not math.isfinite(denominator):
                        raise UnsupportedFinancialScope()
                    if denominator == 0:
                        item['status'] = 'undefined_ratio'
                        continue
                provenance = {
                    'model': 'account.report', 'report_id': report.id,
                    'expression_id': mapping.expression_id.id,
                    'line_code': mapping.expression_id.report_line_id.code,
                    'expression_label': mapping.expression_id.label,
                    'column_group': group_key, 'company_id': scoped.env.company.id,
                    'options': prepared, 'mapping_version': mapping.definition_fingerprint,
                }
                provenance['fingerprint'] = hashlib.sha256(
                    json.dumps(provenance, sort_keys=True, default=str).encode()).hexdigest()
                buckets = []
                if key in {'receivables', 'payables'}:
                    expressions = {expr.label: expr for expr in mapping.expression_id.report_line_id.expression_ids}
                    for column in prepared['columns']:
                        label = column['expression_label']
                        if not (label.startswith('period') and label[6:].isdigit()):
                            continue
                        expression = expressions.get(label)
                        bucket = totals.get(expression.id if expression else None, {}).get('value')
                        if type(bucket) not in (int, float) or not math.isfinite(bucket):
                            raise UnsupportedFinancialScope()
                        buckets.append({'key': label, 'label': column['name'], 'value': bucket,
                                        'expression_id': expression.id})
                    if not buckets:
                        raise UnsupportedFinancialScope()
                item.update(status='ready', value=value, unit='percentage' if key in RATIO_KEYS else 'currency',
                            source_kind='forecast' if key == 'standard_forecast' else 'native_report',
                            source=report.display_name,
                            source_line=mapping.expression_id.report_line_id.display_name,
                            measure=mapping.expression_id.label,
                            date_field='period' if key in PERIOD_KEYS else 'as_of',
                            drilldown=True, provenance=provenance,
                            has_warnings=bool(information.get('warnings')),
                            aging_buckets=buckets,
                            partner_ledger=bool(mapping.partner_ledger_report_id),
                            budget=scoped._budget_data(mapping, dates, evaluations) if key in BUDGET_KEYS else False,
                            definition=mapping.definition_note)
            except AccessError:
                item['status'] = 'restricted'
            except UnsupportedFinancialScope:
                item['status'] = 'unsupported_scope'
            except (UserError, KeyError, TypeError, ValueError) as error:
                # Native definition errors remain unavailable. Never replace
                # them with independent sums or a fabricated zero.
                item['status'] = 'error'
                _logger.warning('Financial dashboard metric=%s category=%s', key, type(error).__name__)
        result['items'].extend(scoped._overdue_items(result['items']))
        cash = next(item for item in result['items'] if item['key'] == 'cash')
        result['cash_breakdown'] = scoped._cash_journal_breakdown(dates, cash)
        result['cash_flow'] = scoped._cash_flow_data(dates)
        result['supplier_windows'] = scoped._supplier_payment_windows(dates)
        return result

    def _overdue_labels(self):
        return {'receivables_overdue': _('Overdue receivables'),
                'payables_overdue': _('Overdue payables')}

    def _overdue_domain(self, cutoff):
        # Native maturity aging uses COALESCE(date_maturity, date). Do not use
        # today's residual/reconciled flag: the native engine owns settlement
        # at the requested historical cutoff, including credits and payments.
        return ['|', ('date_maturity', '<', cutoff.isoformat()),
                '&', ('date_maturity', '=', False), ('date', '<', cutoff.isoformat())]

    def _overdue_options(self, mapping, dates, key):
        if key not in self._overdue_labels() or mapping.metric != key.removesuffix('_overdue'):
            raise ValidationError(_('Unknown overdue report scope.'))
        prepared = self._financial_options(mapping.report_id, mapping.metric, dates)
        prepared['forced_domain'] = self._overdue_domain(dates[2])
        prepared['adams_overdue_metric'] = key
        return prepared

    def _overdue_items(self, items):
        """Approved composition of complete native aging buckets, never ledger sums.

        The standard maturity-based report exposes period0 (not due / due today)
        and period1..5, but no overdue subtotal. The approved mapping fingerprint
        covers the underlying expressions and report handler. Reuse that exact
        evaluation without another report call or a paginated partner sum.
        """
        by_key = {item['key']: item for item in items}
        result = []
        for key, label in self._overdue_labels().items():
            base = by_key.get(key.removesuffix('_overdue'), {})
            item = {'key': key, 'label': label, 'status': base.get('status', 'not_configured'),
                    'value': None, 'unit': 'currency', 'date_field': 'as_of'}
            result.append(item)
            if item['status'] != 'ready':
                continue
            buckets = base.get('aging_buckets', [])
            if (len(buckets) != 6 or {bucket['key'] for bucket in buckets}
                    != {'period0', 'period1', 'period2', 'period3', 'period4', 'period5'}):
                item['status'] = 'unsupported_scope'
                continue
            overdue = [bucket for bucket in buckets if bucket['key'] != 'period0']
            provenance = dict(base['provenance'])
            provenance.pop('fingerprint', None)
            provenance['composition'] = {'operation': 'sum', 'bucket_keys': [b['key'] for b in overdue],
                                         'expression_ids': [b['expression_id'] for b in overdue],
                                         'excluded_bucket': 'period0'}
            provenance['fingerprint'] = hashlib.sha256(
                json.dumps(provenance, sort_keys=True, default=str).encode()).hexdigest()
            item.update(value=sum(bucket['value'] for bucket in overdue), drilldown=True,
                        source_kind='report_derived', source=base['source'],
                        source_line=base['source_line'], measure='overdue', provenance=provenance,
                        has_warnings=base.get('has_warnings', False),
                        definition=_('Signed total of the five overdue buckets in the approved aging report. '
                                     'Amounts due today and not yet due are excluded. '
                                     'Credits, payments and historical settlements retain the report treatment.'))
        return result

    def _supplier_window_domain(self, cutoff, window):
        # Fixed approved windows; no caller-supplied domain or arithmetic.
        domains = {
            'supplier_overdue': [('date_maturity', '<', cutoff.isoformat())],
            'supplier_today': [('date_maturity', '=', cutoff.isoformat())],
            'supplier_due_7': [('date_maturity', '>', cutoff.isoformat()),
                               ('date_maturity', '<=', (cutoff + timedelta(days=7)).isoformat())],
            'supplier_due_30': [('date_maturity', '>', cutoff.isoformat()),
                                ('date_maturity', '<=', (cutoff + timedelta(days=30)).isoformat())],
        }
        if window not in domains:
            raise ValidationError(_('Unknown supplier payment window.'))
        return [('move_id.move_type', '=', 'in_invoice')] + domains[window]

    def _supplier_window_options(self, mapping, dates, window):
        prepared = self._financial_options(mapping.report_id, 'payables', dates)
        # Native aging handles historical settlement, currency and rounding.
        # Standalone vendor credits/payments remain in full native AP aging;
        # only their reconciled effects on the bill enter these bill-only cards.
        prepared['forced_domain'] = self._supplier_window_domain(dates[2], window)
        prepared['adams_supplier_window'] = window
        return prepared

    def _supplier_window_labels(self):
        return [('supplier_overdue', _('Overdue supplier bills')),
                  ('supplier_today', _('Supplier bills due today')),
                  ('supplier_due_7', _('Supplier bills due in 7 days')),
                  ('supplier_due_30', _('Supplier bills due in 30 days'))]

    def _supplier_payment_windows(self, dates):
        labels = self._supplier_window_labels()
        mapping = self._financial_mapping('payables')
        rows = []
        for key, label in labels:
            item = {'key': key, 'label': label, 'status': 'not_configured', 'value': None,
                    'unit': 'currency', 'date_field': 'as_of'}
            rows.append(item)
            if not self._mapping_ready(mapping):
                continue
            try:
                prepared = self._supplier_window_options(mapping, dates, key)
                information = mapping.report_id.get_report_information(prepared)
                group = next(iter(prepared['column_groups']))
                value = information['column_groups_totals'].get(group, {}).get(
                    mapping.expression_id.id, {}).get('value')
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise UnsupportedFinancialScope()
                item.update(status='ready', value=value, drilldown=True,
                            has_warnings=bool(information.get('warnings')),
                            source=mapping.report_id.display_name,
                            definition=_('Posted supplier-bill installments outstanding at the balance cutoff. '
                                         'The 30-day window includes the first 7 days. '
                                         'Standalone credits and unapplied payments remain in full aging.'),
                            provenance={'model': 'account.report', 'report_id': mapping.report_id.id,
                                        'expression_id': mapping.expression_id.id, 'options': prepared,
                                        'company_id': self.env.company.id,
                                        'mapping_version': mapping.definition_fingerprint})
            except AccessError:
                item['status'] = 'restricted'
            except UnsupportedFinancialScope:
                item['status'] = 'unsupported_scope'
            except (UserError, KeyError, TypeError, ValueError) as error:
                item['status'] = 'error'
                _logger.warning('Supplier payment window=%s category=%s', key, type(error).__name__)
        return rows

    def _financial_periods(self, dates):
        start, end = dates[:2]
        periods = []
        while start <= end:
            next_month = start.replace(day=1) + relativedelta(months=1)
            stop = min(end, next_month - timedelta(days=1))
            periods.append((start, stop))
            start = next_month
        return periods

    @api.model
    def get_financial_trend(self, key, options):
        return self.get_financial_trends([key], options)['series'][key]

    @api.model
    def get_financial_trends(self, keys, options):
        """Evaluate each approved report/month once for the requested series."""
        scoped, dates = self._scope(options)
        scoped._finance_access()
        allowed = BUDGET_KEYS | RATIO_KEYS
        if (not isinstance(keys, list) or not keys or len(keys) > len(allowed)
                or any(not isinstance(key, str) or key not in allowed for key in keys)):
            raise ValidationError(_('This financial trend is not configured.'))
        series, evaluations = {}, {}
        currency = scoped.env.company.currency_id
        generated_at = fields.Datetime.to_string(fields.Datetime.now())
        for key in dict.fromkeys(keys):
            mapping = scoped._financial_mapping(key)
            if not scoped._mapping_ready(mapping):
                series[key] = {'status': 'not_configured', 'rows': []}
                continue
            report = mapping.report_id
            rows = []
            for start, stop in scoped._financial_periods(dates):
                cache_key = (report.id, start, stop)
                if cache_key not in evaluations:
                    prepared = scoped._financial_options(report, key, [start, stop, dates[2]])
                    evaluations[cache_key] = (prepared, report.get_report_information(prepared))
                prepared, info = evaluations[cache_key]
                group = next(iter(prepared['column_groups']))
                totals = info['column_groups_totals'].get(group, {})
                value = totals.get(mapping.expression_id.id, {}).get('value')
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise ValidationError(_('The report returned an unsupported scope.'))
                status = 'ready'
                if key in RATIO_KEYS:
                    denominator = totals.get(mapping.denominator_expression_id.id, {}).get('value')
                    if type(denominator) not in (int, float) or not math.isfinite(denominator):
                        raise ValidationError(_('The report returned an unsupported scope.'))
                    if denominator == 0:
                        value, status = None, 'undefined_ratio'
                rows.append({'label': start.strftime('%Y-%m'), 'date_from': start.isoformat(),
                             'date_to': stop.isoformat(), 'value': value, 'status': status,
                             'has_warnings': bool(info.get('warnings'))})
            series[key] = {'status': 'ready', 'rows': rows, 'currency': currency.name,
                           'digits': currency.decimal_places,
                           'unit': 'percentage' if key in RATIO_KEYS else 'currency',
                           'source_kind': 'native_report', 'report_id': report.id,
                           'expression_id': mapping.expression_id.id,
                           'mapping_version': mapping.definition_fingerprint,
                           'generated_at': generated_at}
        return {'series': series, 'company_id': scoped.env.company.id, 'generated_at': generated_at}

    @api.model
    def open_financial_period(self, key, options, period):
        scoped, dates = self._scope(options)
        scoped._finance_access()
        if key not in BUDGET_KEYS | RATIO_KEYS:
            raise ValidationError(_('This financial trend is not configured.'))
        selected = next(((start, end) for start, end in scoped._financial_periods(dates)
                         if start.strftime('%Y-%m') == period), None)
        if not selected:
            raise ValidationError(_('Invalid financial period.'))
        return self.open_report(key, dict(options, date_from=selected[0].isoformat(), date_to=selected[1].isoformat()))

    @api.model
    def open_report(self, key, options, dimension=None, group_id=None):
        if key in {'receivables', 'payables'} and dimension == 'aging_bucket':
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if not isinstance(group_id, str) or group_id not in tuple(f'period{i}' for i in range(6)):
                raise ValidationError(_('Invalid aging bucket.'))
            mapping = scoped._financial_mapping(key)
            if not scoped._mapping_ready(mapping):
                raise ValidationError(_('Review and approve this financial mapping first.'))
            marker = {'metric': key, 'period': group_id}
            report = mapping.report_id.with_context(adams_aging_bucket=marker)
            prepared = scoped._financial_options(report, key, dates)
            return {'type': 'ir.actions.client', 'tag': 'account_report',
                    'name': prepared['report_title'], 'keep_journal_groups_options': True,
                    'context': dict(scoped.env.context, report_id=report.id, adams_aging_bucket=marker),
                    'params': {'options': prepared, 'ignore_session': True}}
        if key in self._overdue_labels():
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if dimension is not None or group_id is not None:
                raise ValidationError(_('Use the financial report filters for further analysis.'))
            mapping = scoped._financial_mapping(key.removesuffix('_overdue'))
            if not scoped._mapping_ready(mapping):
                raise ValidationError(_('Review and approve this financial mapping first.'))
            prepared = scoped._overdue_options(mapping, dates, key)
            return {'type': 'ir.actions.client', 'tag': 'account_report',
                    'name': '%s — %s — %s' % (mapping.report_id.display_name,
                                              scoped._overdue_labels()[key], dates[2].isoformat()),
                    'keep_journal_groups_options': True,
                    'context': dict(scoped.env.context, report_id=mapping.report_id.id,
                                    adams_overdue_metric=key),
                    'params': {'options': prepared, 'ignore_session': True}}
        if key in {'supplier_overdue', 'supplier_today', 'supplier_due_7', 'supplier_due_30'}:
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if dimension is not None or group_id is not None:
                raise ValidationError(_('Use the financial report filters for further analysis.'))
            mapping = scoped._financial_mapping('payables')
            if not scoped._mapping_ready(mapping):
                raise ValidationError(_('Review and approve this financial mapping first.'))
            prepared = scoped._supplier_window_options(mapping, dates, key)
            return {'type': 'ir.actions.client', 'tag': 'account_report',
                    'name': '%s — %s — %s' % (mapping.report_id.display_name,
                                               dict(scoped._supplier_window_labels())[key],
                                               dates[2].isoformat()),
                    'keep_journal_groups_options': True,
                    'context': dict(scoped.env.context, report_id=mapping.report_id.id,
                                    adams_supplier_window=key),
                    'params': {'options': prepared, 'ignore_session': True}}
        if key in {'budget_' + metric for metric in BUDGET_KEYS}:
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if dimension is not None or group_id is not None:
                raise ValidationError(_('Use the financial report filters for further analysis.'))
            mapping = scoped._financial_mapping(key.removeprefix('budget_'))
            if not scoped._mapping_ready(mapping):
                raise ValidationError(_('Review and approve this financial mapping first.'))
            budget = scoped._budget_data(mapping, dates, {})
            if budget['status'] != 'ready':
                raise ValidationError(_('The budget is unavailable for this scope.'))
            return {'type': 'ir.actions.client', 'tag': 'account_report', 'name': mapping.report_id.display_name,
                    'keep_journal_groups_options': True,
                    'context': dict(scoped.env.context, report_id=mapping.report_id.id),
                    'params': {'options': budget['options'], 'ignore_session': True}}
        if key in {'partner_receivables', 'partner_payables'}:
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if dimension is not None or group_id is not None:
                raise ValidationError(_('Use the financial report filters for further analysis.'))
            metric = key.removeprefix('partner_')
            mapping = scoped._financial_mapping(metric)
            if not scoped._mapping_ready(mapping) or not mapping.partner_ledger_report_id:
                raise ValidationError(_('Review and approve this financial mapping first.'))
            aging_options = scoped._financial_options(mapping.report_id, metric, dates)
            report = mapping.partner_ledger_report_id
            prepared = scoped._financial_options(report, 'revenue', dates, {
                'account_type': aging_options['account_type'], 'unreconciled': False, 'partner_ids': [],
            })
            expected = {item['id'] for item in aging_options['account_type'] if item.get('selected')}
            actual = {item['id'] for item in prepared.get('account_type', []) if item.get('selected')}
            if actual != expected or prepared.get('unreconciled') or prepared.get('partner_ids'):
                raise ValidationError(_('The report returned an unsupported scope.'))
            return {'type': 'ir.actions.client', 'tag': 'account_report', 'name': report.display_name,
                    'keep_journal_groups_options': True,
                    'context': dict(scoped.env.context, report_id=report.id),
                    'params': {'options': prepared, 'ignore_session': True}}
        if key == 'cash_flow':
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if dimension is not None or group_id is not None:
                raise ValidationError(_('Use the financial report filters for further analysis.'))
            mapping = scoped._financial_mapping('cash')
            if not scoped._mapping_ready(mapping) or not mapping.cash_flow_report_id:
                raise ValidationError(_('Review and approve this financial mapping first.'))
            prepared = scoped._financial_options(mapping.cash_flow_report_id, 'revenue', dates)
            return {'type': 'ir.actions.client', 'tag': 'account_report',
                    'name': mapping.cash_flow_report_id.display_name,
                    'keep_journal_groups_options': True,
                    'context': dict(scoped.env.context, report_id=mapping.cash_flow_report_id.id),
                    'params': {'options': prepared, 'ignore_session': True}}
        if key == 'cash_account':
            if dimension is not None:
                raise ValidationError(_('Use the financial report filters for further analysis.'))
            return self._open_cash_account(options, group_id)
        if key not in dict(METRICS):
            return super().open_report(key, options, dimension, group_id)
        scoped, dates = self._scope(options)
        scoped._finance_access()
        if dimension is not None or group_id is not None:
            raise ValidationError(_('Use the financial report filters for further analysis.'))
        mapping = scoped._financial_mapping(key)
        if not scoped._mapping_ready(mapping):
            raise ValidationError(_('Review and approve this financial mapping first.'))
        try:
            prepared = scoped._financial_options(mapping.report_id, key, dates)
        except UnsupportedFinancialScope as error:
            raise ValidationError(_('The report returned an unsupported scope.')) from error
        # Verified against account_reports' AccountReportController: explicit
        # options plus ignore_session prevent saved native filters replacing scope.
        return {'type': 'ir.actions.client', 'tag': 'account_report',
                'name': mapping.report_id.display_name,
                'keep_journal_groups_options': True,
                'context': dict(scoped.env.context, report_id=mapping.report_id.id),
                'params': {'options': prepared, 'ignore_session': True}}

    def _cash_detail_mapping(self):
        mapping = self._financial_mapping('cash')
        return mapping if self._mapping_ready(mapping) and mapping.cash_detail_report_id else False

    def _cash_options(self, mapping, dates):
        # GL includes initial balances through its own from_beginning engine.
        # A one-day period at the cutoff produces the native closing balance.
        return self._financial_options(mapping.cash_detail_report_id, 'revenue',
                                       (dates[2], dates[2], dates[2]))

    def _cash_journal_breakdown(self, dates, cash):
        """Classify native closing balances only if the entire report reconciles.

        A journal's default account supplies identity, never a balance. The
        General Ledger engine supplies each signed balance at the same cutoff.
        Ambiguous/unlinked accounts and differing report scope block the split.
        """
        if cash['status'] != 'ready':
            return {'status': cash['status']}
        try:
            mapping = self._cash_detail_mapping()
            if not mapping:
                return {'status': 'not_configured'}
            accounts = self.env['account.account'].with_context(active_test=False)
            journals = self.env['account.journal'].with_context(active_test=False)
            accounts.check_access('read')
            journals.check_access('read')
            accounts.check_field_access_rights('read', ['account_type', 'active', 'company_ids'])
            journals.check_field_access_rights('read', ['active', 'type', 'company_id', 'default_account_id'])
            records = accounts.search([
                ('company_ids', 'in', [self.env.company.id]),
                ('account_type', '=', 'asset_cash'), ('active', '=', True),
            ], order='id', limit=201)
            if len(records) > 200:
                return {'status': 'unsupported_scope', 'reason': 'account_limit'}
            links = journals.search([
                ('company_id', '=', self.env.company.id), ('active', '=', True),
                ('type', 'in', ['bank', 'cash']), ('default_account_id', 'in', records.ids),
            ])
            types = {account.id: set() for account in records}
            for journal in links:
                types[journal.default_account_id.id].add(journal.type)
            unlinked = sum(not kinds for kinds in types.values())
            shared = sum(len(kinds) > 1 for kinds in types.values())
            if unlinked or shared:
                return {'status': 'ambiguous', 'unlinked_accounts': unlinked,
                        'shared_accounts': shared}
            balances = {}
            if records:
                report = mapping.cash_detail_report_id
                expression = mapping.cash_detail_expression_id
                prepared = self._cash_options(mapping, dates)
                prepared['forced_domain'] = [('account_id', 'in', records.ids)]
                self.env.flush_all()
                report._init_currency_table(prepared)
                warnings = {}
                native = report._compute_expression_totals_for_each_column_group(
                    expression, prepared, groupby_to_expand='account_id', warnings=warnings)
                group = next(iter(prepared['column_groups']))
                balances = dict(native[group][expression]['value'])
                for account in records:
                    if account.id not in balances:
                        single = dict(prepared, forced_domain=[('account_id', '=', account.id)])
                        scalar = report._compute_expression_totals_for_each_column_group(
                            expression, single, warnings=warnings)
                        balances[account.id] = scalar[group][expression]['value']
            if any(type(value) not in (int, float) or not math.isfinite(value)
                   for value in balances.values()):
                raise UnsupportedFinancialScope()
            total = sum(balances.values())
            currency = self.env.company.currency_id
            if not currency.is_zero(total - cash['value']):
                return {'status': 'unreconciled', 'reason': 'native_total_mismatch'}
            return {'status': 'ready',
                    'bank': sum(balances[account_id] for account_id, kinds in types.items()
                                if kinds == {'bank'}),
                    'cash': sum(balances[account_id] for account_id, kinds in types.items()
                                if kinds == {'cash'}),
                    'as_of': dates[2].isoformat(), 'currency': currency.name,
                    'source': mapping.cash_detail_report_id.display_name}
        except (AccessError, UnsupportedFinancialScope, UserError, KeyError, TypeError, ValueError) as error:
            _logger.warning('Cash journal breakdown category=%s', type(error).__name__)
            return {'status': 'restricted' if isinstance(error, AccessError) else 'unreconciled'}

    @api.model
    def get_cash_directory(self, options, offset=0, search=""):
        result = super().get_cash_directory(options, offset, search)
        scoped, dates = self._scope(options)
        if not result['rows']:
            return result
        try:
            scoped._finance_access()
            mapping = scoped._cash_detail_mapping()
            if not mapping:
                return result
            report = mapping.cash_detail_report_id
            expression = mapping.cash_detail_expression_id
            prepared = scoped._cash_options(mapping, dates)
            ids = [row['id'] for row in result['rows']]
            prepared['forced_domain'] = [('account_id', 'in', ids)]
            scoped.env.flush_all()
            report._init_currency_table(prepared)
            warnings = {}
            native = report._compute_expression_totals_for_each_column_group(
                expression, prepared, groupby_to_expand='account_id', warnings=warnings)
            group = next(iter(prepared['column_groups']))
            balances = dict(native[group][expression]['value'])
            for row in result['rows']:
                value = balances.get(row['id'])
                if value is None:
                    # Ask the native scalar engine for accounts absent from its
                    # grouped result. Absence is never assumed to mean zero.
                    single = dict(prepared, forced_domain=[('account_id', '=', row['id'])])
                    scalar = report._compute_expression_totals_for_each_column_group(
                        expression, single, warnings=warnings)
                    value = scalar[group][expression]['value']
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise UnsupportedFinancialScope()
                row.update(balance=value, balance_status='ready',
                           balance_currency=scoped.env.company.currency_id.name,
                           balance_digits=scoped.env.company.currency_id.decimal_places,
                           drilldown=True)
            result.update(native_balances=True, source=report.display_name,
                          has_warnings=bool(warnings), definition=mapping.definition_note)
        except (AccessError, UnsupportedFinancialScope, UserError, KeyError, TypeError, ValueError) as error:
            status = 'restricted' if isinstance(error, AccessError) else 'unsupported_scope' if isinstance(error, UnsupportedFinancialScope) else 'error'
            for row in result['rows']:
                row.update(balance=None, balance_status=status, drilldown=False)
        return result

    def _budget_data(self, mapping, dates, evaluations):
        result = {'status': 'not_configured', 'value': None}
        try:
            budget = mapping.budget_id
            if not budget:
                return result
            budget.check_access('read')
            if budget.company_id != self.env.company:
                raise AccessError(_('Accounting report access is required.'))
            # Native budgets are dated items. Missing period coverage must not
            # turn into an invented zero target or linear daily proration.
            if not self.env['account.report.budget.item'].search_count([
                    ('budget_id', '=', budget.id), ('date', '>=', dates[0]), ('date', '<=', dates[1])]):
                return result
            cache_key = ('budget', mapping.report_id.id, budget.id)
            if cache_key not in evaluations:
                options = self._financial_options(mapping.report_id, mapping.metric, dates, budget_id=budget.id)
                selected = {item['id'] for item in options.get('budgets', []) if item.get('selected')}
                if selected != {budget.id}:
                    raise UnsupportedFinancialScope()
                evaluations[cache_key] = (options, mapping.report_id.get_report_information(options))
            options, information = evaluations[cache_key]
            groups = [key for key, group in options['column_groups'].items()
                      if group['forced_options'].get('compute_budget') == budget.id]
            if len(groups) != 1:
                raise UnsupportedFinancialScope()
            value = information['column_groups_totals'][groups[0]][mapping.expression_id.id]['value']
            if type(value) not in (int, float) or not math.isfinite(value):
                raise UnsupportedFinancialScope()
            result.update(status='ready', value=value, name=budget.name, budget_id=budget.id,
                          options=options, has_warnings=bool(information.get('warnings')))
        except (AccessError, UnsupportedFinancialScope, UserError, KeyError, TypeError, ValueError) as error:
            result['status'] = 'restricted' if isinstance(error, AccessError) else 'unsupported_scope' if isinstance(error, UnsupportedFinancialScope) else 'error'
        return result

    def _open_cash_account(self, options, account_id):
        scoped, dates = self._scope(options)
        scoped._finance_access()
        if type(account_id) is not int:
            raise ValidationError(_('Invalid cash account.'))
        account = scoped.env['account.account'].with_context(active_test=False).search([
            ('id', '=', account_id), ('account_type', '=', 'asset_cash'),
            ('company_ids', 'in', [scoped.env.company.id]),
        ], limit=1)
        if not account:
            raise AccessError(_('Cash account access is required.'))
        mapping = scoped._cash_detail_mapping()
        if not mapping:
            raise ValidationError(_('Review and approve this financial mapping first.'))
        report = mapping.cash_detail_report_id
        prepared = scoped._cash_options(mapping, dates)
        action = report.caret_option_open_general_ledger(prepared, {
            'line_id': report._get_generic_line_id('account.account', account.id),
        })
        action['context'] = dict(action.get('context', {}), **scoped.env.context)
        action['keep_journal_groups_options'] = True
        return action

    def _cash_flow_data(self, dates):
        result = {'status': 'not_configured', 'rows': []}
        try:
            mapping = self._financial_mapping('cash')
            if not self._mapping_ready(mapping) or not mapping.cash_flow_report_id:
                return result
            report = mapping.cash_flow_report_id
            prepared = self._financial_options(report, 'revenue', dates)
            information = report.get_report_information(prepared)
            indices = [index for index, column in enumerate(prepared['columns'])
                       if column['expression_label'] == 'balance' and column['figure_type'] == 'monetary']
            if len(indices) != 1:
                raise UnsupportedFinancialScope()
            rows = []
            for line in information['lines']:
                model, _record_id = report._get_model_info_from_id(line['id'])
                if model is not None:
                    continue  # Native account details remain in the native action.
                value = line['columns'][indices[0]]['no_format']
                if type(value) not in (int, float) or not math.isfinite(value):
                    raise UnsupportedFinancialScope()
                rows.append({'key': line['id'], 'label': line['name'], 'value': value,
                             'level': line.get('level', 0)})
            required = {report._get_generic_line_id(None, None, markup=key)
                        for key in ('opening_balance', 'net_increase', 'closing_balance')}
            if not required.issubset({row['key'] for row in rows}) or len(rows) > 100:
                raise UnsupportedFinancialScope()
            difference = report._get_generic_line_id(None, None, markup='unexplained_difference')
            bridge = {key: next(row for row in rows if row['key'] == report._get_generic_line_id(None, None, markup=key))
                      for key in ('opening_balance', 'net_increase', 'closing_balance')}
            result.update(status='ready', rows=rows, bridge=bridge, source=report.display_name,
                          has_warnings=bool(information.get('warnings')) or any(row['key'] == difference for row in rows),
                          options=prepared, mapping_version=mapping.definition_fingerprint)
        except (AccessError, UnsupportedFinancialScope, UserError, KeyError, TypeError, ValueError) as error:
            result['status'] = 'restricted' if isinstance(error, AccessError) else 'unsupported_scope' if isinstance(error, UnsupportedFinancialScope) else 'error'
        return result
