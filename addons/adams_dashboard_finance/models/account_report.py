"""Retain the fixed supplier window through native report option rebuilding."""
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountReport(models.Model):
    _inherit = 'account.report'

    def get_options(self, previous_options):
        options = super().get_options(previous_options)
        window = self.env.context.get('adams_supplier_window')
        # Native PDF/XLSX rebuild options with export_mode=print, without the
        # client action context. Preserve only this explicitly marked export.
        if not window and (previous_options or {}).get('export_mode') == 'print':
            window = previous_options.get('adams_supplier_window')
        if not window:
            if (previous_options or {}).get('adams_supplier_window'):
                options.pop('report_title', None)
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
        options['adams_supplier_window'] = window
        options['report_title'] = '%s — %s' % (self.name, self._adams_supplier_caption(options))
        return options

    def _adams_supplier_caption(self, options):
        window = options.get('adams_supplier_window')
        if not window:
            return False
        dashboard = self.env['adams.executive.dashboard']
        cutoff = fields.Date.to_date(options['date']['date_to'])
        expected = dashboard._supplier_window_domain(cutoff, window)
        if [tuple(term) for term in options.get('forced_domain', [])] != expected:
            raise ValidationError(_('Unsupported supplier payment window scope.'))
        label = dict(dashboard._supplier_window_labels())[window]
        return '%s — %s' % (label, cutoff.isoformat())

    def get_report_information(self, options):
        result = super().get_report_information(options)
        caption = self._adams_supplier_caption(options)
        if caption:
            result['report']['name'] = '%s — %s' % (self.name, caption)
        return result

    def get_default_report_filename(self, options, extension):
        name = super().get_default_report_filename(options, extension)
        caption = self._adams_supplier_caption(options)
        return '%s - %s.%s' % (self.name, caption, extension) if caption else name

    def _inject_report_options_into_xlsx_sheet(self, options, sheet, y_offset, options_to_print=None):
        y_offset = super()._inject_report_options_into_xlsx_sheet(
            options, sheet, y_offset, options_to_print=options_to_print)
        caption = self._adams_supplier_caption(options)
        if caption:
            sheet.write(y_offset, 0, _('Supplier payment schedule'))
            sheet.write(y_offset, 1, caption)
            return y_offset + 1
        return y_offset
