"""Explicit company policy; report definitions and arithmetic remain in Odoo."""
import hashlib
import json
import re

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


# Date interpretation is server-owned, never chosen through a dashboard RPC.
METRICS = [
    ('revenue', 'Accounting revenue'), ('gross_profit', 'Gross profit'),
    ('profit', 'Net profit'), ('operating_expenses', 'Operating expenses'),
    ('gross_margin', 'Gross margin'), ('net_margin', 'Net margin'),
    ('cash', 'Bank and cash'), ('assets', 'Assets'),
    ('liabilities', 'Liabilities'), ('equity', 'Equity'),
    ('receivables', 'Receivables'), ('payables', 'Payables'),
]
PERIOD_KEYS = {'revenue', 'gross_profit', 'profit', 'operating_expenses', 'gross_margin', 'net_margin'}
RATIO_KEYS = {'gross_margin', 'net_margin'}


class FinanceMapping(models.Model):
    _name = 'adams.dashboard.finance.mapping'
    _description = 'Executive Dashboard Financial Mapping'
    _rec_name = 'metric'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    metric = fields.Selection(METRICS, required=True)
    report_id = fields.Many2one('account.report', required=True, ondelete='restrict')
    expression_id = fields.Many2one('account.report.expression', required=True, ondelete='restrict')
    denominator_expression_id = fields.Many2one('account.report.expression', ondelete='restrict',
        help='Native denominator result used only to detect an undefined ratio; the native engine calculates the percentage.')
    cash_detail_report_id = fields.Many2one('account.report', ondelete='restrict')
    cash_detail_expression_id = fields.Many2one('account.report.expression', ondelete='restrict')
    cash_flow_report_id = fields.Many2one('account.report', ondelete='restrict')
    partner_ledger_report_id = fields.Many2one('account.report', ondelete='restrict')
    definition_note = fields.Text(required=True, help='Explain the chosen native definition, variant, currency and reporting policy.')
    approved_by = fields.Many2one('res.users', readonly=True, copy=False)
    approved_at = fields.Datetime(readonly=True, copy=False)
    definition_fingerprint = fields.Char(readonly=True, copy=False)
    active = fields.Boolean(default=True)

    _metric_company_unique = models.Constraint('unique(company_id, metric)', 'Map each metric only once per company.')

    @api.constrains('expression_id', 'denominator_expression_id', 'report_id', 'company_id', 'metric',
                    'cash_detail_report_id', 'cash_detail_expression_id', 'cash_flow_report_id', 'partner_ledger_report_id')
    def _check_definition(self):
        for mapping in self:
            if mapping.expression_id.report_line_id.report_id != mapping.report_id:
                raise ValidationError(_('Select an expression belonging to the chosen report.'))
            if mapping.metric in RATIO_KEYS and (
                    not mapping.denominator_expression_id
                    or mapping.denominator_expression_id.report_line_id.report_id != mapping.report_id):
                raise ValidationError(_('Select the native denominator expression for this ratio.'))
            if mapping.report_id.use_sections:
                raise ValidationError(_('Select the specific report section, not its composite parent.'))
            if mapping.report_id.filter_date_range != (mapping.metric in PERIOD_KEYS):
                raise ValidationError(_('The report date mode does not match this metric.'))
            expected = 'percentage' if mapping.metric in RATIO_KEYS else 'monetary'
            columns = mapping.report_id.column_ids.filtered(lambda c: c.expression_label == mapping.expression_id.label)
            figure_types = {mapping.expression_id.figure_type or column.figure_type for column in columns}
            if not columns or figure_types != {expected}:
                raise ValidationError(_('Choose a native report column with the correct monetary or percentage unit.'))
            if mapping.cash_detail_report_id or mapping.cash_detail_expression_id:
                detail = mapping.cash_detail_expression_id
                ledger = self.env.ref('account_reports.general_ledger_report')
                if (mapping.metric != 'cash' or not detail
                        or mapping.cash_detail_report_id != ledger
                        or detail != self.env.ref('account_reports.general_ledger_line_balance')):
                    raise ValidationError(_('Cash detail requires the native General Ledger balance expression.'))
            if mapping.cash_flow_report_id and (mapping.metric != 'cash' or
                    mapping.cash_flow_report_id != self.env.ref('account_reports.cash_flow_report')):
                raise ValidationError(_('Select the native Cash Flow Statement for the cash mapping.'))
            if mapping.partner_ledger_report_id and (mapping.metric not in {'receivables', 'payables'} or
                    mapping.partner_ledger_report_id != self.env.ref('account_reports.partner_ledger_report')):
                raise ValidationError(_('Select the native Partner Ledger for a receivable or payable mapping.'))

    def _fingerprint(self):
        self.ensure_one()
        report = self.report_id
        # Changes to native accounting data flow through on refresh. Changes to
        # report definitions require explicit review, including dependent lines.
        reports = report | self.cash_detail_report_id | self.cash_flow_report_id | self.partner_ledger_report_id
        pending = reports
        while pending:
            dependencies = self.env['account.report']
            for expression in pending.line_ids.expression_ids:
                for reference in re.findall(r'cross_report\(([^)]+)\)', expression.subformula or ''):
                    dependency = self.env.ref(reference, raise_if_not_found=False)
                    if not dependency or dependency._name != 'account.report':
                        raise ValidationError(_('A dependent native report could not be resolved.'))
                    dependencies |= dependency
            pending = dependencies - reports
            reports |= pending
        definitions = [
            (expression.id, expression.report_line_id.code, expression.report_line_id.groupby, expression.label,
             expression.engine, expression.formula, expression.subformula,
             expression.date_scope, expression.figure_type)
            for expression in reports.line_ids.expression_ids.sorted('id')
        ]
        value = [self.company_id.id, self.company_id.currency_id.id,
                 self.company_id.account_fiscal_country_id.id, self.metric, report.id, self.expression_id.id,
                 report.root_report_id.id, report.country_id.id, report.filter_date_range,
                 self.definition_note, self.denominator_expression_id.id,
                 self.cash_detail_report_id.id, self.cash_detail_expression_id.id,
                 self.cash_flow_report_id.id, self.partner_ledger_report_id.id, definitions,
                 [(r.id, r.root_report_id.id, r.country_id.id, r.filter_date_range,
                   r.filter_multi_company, r.filter_account_type, r.only_tax_exigible,
                   r.custom_handler_model_id.id,
                   [(c.id, c.expression_label, c.figure_type) for c in r.column_ids.sorted('id')])
                  for r in reports.sorted('id')]]
        return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

    @api.model_create_multi
    def create(self, vals_list):
        if any(set(vals) & {'approved_by', 'approved_at', 'definition_fingerprint'} for vals in vals_list):
            raise AccessError(_('Use the review action to approve a financial mapping.'))
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) & {'approved_by', 'approved_at', 'definition_fingerprint'}:
            raise AccessError(_('Use the review action to approve a financial mapping.'))
        return super().write(dict(vals, approved_by=False, approved_at=False, definition_fingerprint=False))

    def action_approve(self):
        self.check_access('write')
        if not self.env.user.has_group('account.group_account_manager'):
            raise AccessError(_('Only accounting managers can approve financial mappings.'))
        for mapping in self:
            mapping._check_definition()
            super(FinanceMapping, mapping).write({
                'approved_by': self.env.uid, 'approved_at': fields.Datetime.now(),
                'definition_fingerprint': mapping._fingerprint(),
            })
        return True
