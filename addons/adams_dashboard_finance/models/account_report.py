"""Retain the fixed supplier window through native report option rebuilding."""
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountReport(models.Model):
    _inherit = 'account.report'

    def get_options(self, previous_options):
        options = super().get_options(previous_options)
        window = self.env.context.get('adams_supplier_window')
        if not window:
            return options
        dashboard = self.env['adams.executive.dashboard']
        dashboard._finance_access()
        mapping = dashboard._financial_mapping('payables')
        if (not dashboard._mapping_ready(mapping)
                or mapping.report_id != self
                or options.get('report_id') != self.id
                or {company['id'] for company in options.get('companies', [])}
                   != {self.env.company.id}
                or options.get('all_entries')
                or options.get('aging_based_on') != 'base_on_maturity_date'):
            raise ValidationError(_('Unsupported supplier payment window scope.'))
        cutoff = fields.Date.to_date(options['date']['date_to'])
        options['forced_domain'] = dashboard._supplier_window_domain(cutoff, window)
        return options
