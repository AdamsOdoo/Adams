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

    def _financial_options(self, report, key, dates):
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
        options = report.get_options(previous)
        if (options.get('report_id') != report.id
                or options.get('date', {}).get('date_to') != cutoff.isoformat()
                or options.get('all_entries')
                or {company['id'] for company in options.get('companies', [])} != {self.env.company.id}
                or (period and options['date'].get('date_from') != dates[0].isoformat())
                or len(options.get('column_groups', {})) != 1):
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
        result = {'items': [], 'company_id': scoped.env.company.id,
                  'currency': currency.name, 'digits': currency.decimal_places,
                  'generated_at': fields.Datetime.to_string(fields.Datetime.now())}
        try:
            scoped._finance_access()
        except AccessError:
            result['items'] = [{'key': key, 'status': 'restricted', 'value': None} for key, _label in METRICS]
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
                item.update(status='ready', value=value, unit='percentage' if key in RATIO_KEYS else 'currency',
                            source=report.display_name,
                            source_line=mapping.expression_id.report_line_id.display_name,
                            measure=mapping.expression_id.label,
                            date_field='period' if key in PERIOD_KEYS else 'as_of',
                            drilldown=True, provenance=provenance,
                            has_warnings=bool(information.get('warnings')),
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
        return result

    @api.model
    def open_report(self, key, options, dimension=None, group_id=None):
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
