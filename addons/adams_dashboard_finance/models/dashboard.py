"""Thin adapter over the installed Enterprise report engine; no ledger arithmetic."""
import hashlib
import json
import logging
import math

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .finance_mapping import METRICS, PERIOD_KEYS, RATIO_KEYS

_logger = logging.getLogger(__name__)


class UnsupportedFinancialScope(Exception):
    """The native engine returned a scope this adapter cannot represent."""


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

    def _financial_options(self, report, key, dates, previous_extra=None):
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
        options = report.get_options(previous)
        if (options.get('report_id') != report.id
                or options.get('date', {}).get('date_to') != cutoff.isoformat()
                or options.get('all_entries')
                or {company['id'] for company in options.get('companies', [])} != {self.env.company.id}
                or (period and options['date'].get('date_from') != dates[0].isoformat())
                or len(options.get('column_groups', {})) != 1):
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
        result = {'items': [], 'cash_flow': {'status': 'not_configured', 'rows': []}, 'company_id': scoped.env.company.id,
                  'currency': currency.name, 'digits': currency.decimal_places,
                  'generated_at': fields.Datetime.to_string(fields.Datetime.now())}
        try:
            scoped._finance_access()
        except AccessError:
            result['items'] = [{'key': key, 'status': 'restricted', 'value': None} for key, _label in METRICS]
            result['cash_flow']['status'] = 'restricted'
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
                        buckets.append({'key': label, 'label': column['name'], 'value': bucket})
                    if not buckets:
                        raise UnsupportedFinancialScope()
                item.update(status='ready', value=value, unit='percentage' if key in RATIO_KEYS else 'currency',
                            source=report.display_name,
                            source_line=mapping.expression_id.report_line_id.display_name,
                            measure=mapping.expression_id.label,
                            date_field='period' if key in PERIOD_KEYS else 'as_of',
                            drilldown=True, provenance=provenance,
                            has_warnings=bool(information.get('warnings')),
                            aging_buckets=buckets,
                            partner_ledger=bool(mapping.partner_ledger_report_id),
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
        result['cash_flow'] = scoped._cash_flow_data(dates)
        return result

    @api.model
    def open_report(self, key, options, dimension=None, group_id=None):
        if key in {'partner_receivables', 'partner_payables'}:
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if dimension is not None or group_id is not None:
                raise ValidationError(_('Use the native financial report filters for further analysis.'))
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
                raise ValidationError(_('The native report returned an unsupported scope.'))
            return {'type': 'ir.actions.client', 'tag': 'account_report', 'name': report.display_name,
                    'keep_journal_groups_options': True,
                    'context': dict(scoped.env.context, report_id=report.id),
                    'params': {'options': prepared, 'ignore_session': True}}
        if key == 'cash_flow':
            scoped, dates = self._scope(options)
            scoped._finance_access()
            if dimension is not None or group_id is not None:
                raise ValidationError(_('Use the native financial report filters for further analysis.'))
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
                raise ValidationError(_('Use the native financial report filters for further analysis.'))
            return self._open_cash_account(options, group_id)
        if key not in dict(METRICS):
            return super().open_report(key, options, dimension, group_id)
        scoped, dates = self._scope(options)
        scoped._finance_access()
        if dimension is not None or group_id is not None:
            raise ValidationError(_('Use the native financial report filters for further analysis.'))
        mapping = scoped._financial_mapping(key)
        if not scoped._mapping_ready(mapping):
            raise ValidationError(_('Review and approve this financial mapping first.'))
        try:
            prepared = scoped._financial_options(mapping.report_id, key, dates)
        except UnsupportedFinancialScope as error:
            raise ValidationError(_('The native report returned an unsupported scope.')) from error
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

    @api.model
    def get_cash_directory(self, options, offset=0):
        result = super().get_cash_directory(options, offset)
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
            result.update(status='ready', rows=rows, source=report.display_name,
                          has_warnings=bool(information.get('warnings')) or any(row['key'] == difference for row in rows),
                          options=prepared, mapping_version=mapping.definition_fingerprint)
        except (AccessError, UnsupportedFinancialScope, UserError, KeyError, TypeError, ValueError) as error:
            result['status'] = 'restricted' if isinstance(error, AccessError) else 'unsupported_scope' if isinstance(error, UnsupportedFinancialScope) else 'error'
        return result
