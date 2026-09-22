"""Retain allowlisted dashboard maturity scopes through report/export rebuilding."""
from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountReport(models.Model):
    _inherit = 'account.report'

    def get_options(self, previous_options):
        options = super().get_options(previous_options)
        bucket = self.env.context.get('adams_aging_bucket')
        if not bucket and (previous_options or {}).get('export_mode') == 'print':
            bucket = previous_options.get('adams_aging_bucket')
        if bucket:
            options['adams_aging_bucket'] = bucket
            options['forced_domain'] = self._adams_bucket_domain(options)
            options['report_title'] = '%s — %s' % (self.name, self._adams_bucket_caption(options))
            return options
        if (previous_options or {}).get('adams_aging_bucket'):
            options.pop('adams_aging_bucket', None)
            options.pop('forced_domain', None)
            options.pop('report_title', None)
        overdue = self.env.context.get('adams_overdue_metric')
        if not overdue and (previous_options or {}).get('export_mode') == 'print':
            overdue = previous_options.get('adams_overdue_metric')
        if overdue:
            if self.env.context.get('adams_supplier_window') or (previous_options or {}).get('adams_supplier_window'):
                raise ValidationError(_('Unsupported overdue report scope.'))
            dashboard = self.env['adams.executive.dashboard']
            self._adams_validate_overdue(options, overdue)
            cutoff = fields.Date.to_date(options['date']['date_to'])
            options['forced_domain'] = dashboard._overdue_domain(cutoff)
            options['adams_overdue_metric'] = overdue
            options['report_title'] = '%s — %s' % (self.name, self._adams_overdue_caption(options))
            return options
        if (previous_options or {}).get('adams_overdue_metric'):
            options.pop('adams_overdue_metric', None)
            options.pop('forced_domain', None)
            options.pop('report_title', None)
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

    def _adams_bucket_domain(self, options):
        marker = options.get('adams_aging_bucket')
        if (not isinstance(marker, dict) or set(marker) != {'metric', 'period'}
                or marker.get('metric') not in ('receivables', 'payables')
                or marker.get('period') not in tuple(f'period{i}' for i in range(6))
                or options.get('adams_overdue_metric') or options.get('adams_supplier_window')
                or self.env.context.get('adams_overdue_metric')
                or self.env.context.get('adams_supplier_window')):
            raise ValidationError(_('Invalid aging bucket.'))
        self._adams_validate_overdue(options, marker['metric'] + '_overdue')
        # Use the installed report's own cell-audit maturity domain. Its native
        # engine still handles historical settlement, currency and signed credits.
        handler = self.env[self.custom_handler_model_id.model]
        native = handler._build_domain_from_period(options, marker['period'])
        return [tuple([term[0], term[1], fields.Date.to_string(term[2])])
                if isinstance(term, (list, tuple)) and hasattr(term[2], 'isoformat')
                else term for term in native]

    def _adams_bucket_caption(self, options):
        if not options.get('adams_aging_bucket'):
            return False
        expected = self._adams_bucket_domain(options)
        actual = [tuple(term) if isinstance(term, (list, tuple)) else term
                  for term in options.get('forced_domain', [])]
        if actual != expected:
            raise ValidationError(_('Invalid aging bucket.'))
        period = options['adams_aging_bucket']['period']
        labels = [column['name'] for column in options['columns']
                  if column.get('expression_label') == period]
        if len(labels) != 1:
            raise ValidationError(_('Invalid aging bucket.'))
        return '%s — %s' % (labels[0], options['date']['date_to'])

    def _adams_validate_overdue(self, options, metric):
        dashboard = self.env['adams.executive.dashboard']
        dashboard._finance_access()
        if metric not in dashboard._overdue_labels():
            raise ValidationError(_('Unsupported overdue report scope.'))
        mapping = dashboard._financial_mapping(metric.removesuffix('_overdue'))
        if (not dashboard._mapping_ready(mapping)
                or mapping.report_id != self or options.get('report_id') != self.id
                or {company['id'] for company in options.get('companies', [])} != {self.env.company.id}
                or options.get('all_entries')
                or options.get('aging_based_on') != 'base_on_maturity_date'
                or options.get('aging_interval') != 30):
            raise ValidationError(_('Unsupported overdue report scope.'))
        return dashboard

    def _adams_overdue_caption(self, options):
        metric = options.get('adams_overdue_metric')
        if not metric:
            return False
        dashboard = self._adams_validate_overdue(options, metric)
        cutoff = fields.Date.to_date(options['date']['date_to'])
        domain = [tuple(term) if isinstance(term, (list, tuple)) else term
                  for term in options.get('forced_domain', [])]
        if domain != dashboard._overdue_domain(cutoff) or options.get('adams_supplier_window'):
            raise ValidationError(_('Unsupported overdue report scope.'))
        return '%s — %s' % (dashboard._overdue_labels()[metric], cutoff.isoformat())

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
        bucket_caption = self._adams_bucket_caption(options)
        overdue_caption = self._adams_overdue_caption(options)
        result = super().get_report_information(options)
        caption = bucket_caption or overdue_caption or self._adams_supplier_caption(options)
        if caption:
            result['report']['name'] = '%s — %s' % (self.name, caption)
        return result

    def get_default_report_filename(self, options, extension):
        name = super().get_default_report_filename(options, extension)
        caption = self._adams_bucket_caption(options) or self._adams_overdue_caption(options) or self._adams_supplier_caption(options)
        return '%s - %s.%s' % (self.name, caption, extension) if caption else name

    def _inject_report_options_into_xlsx_sheet(self, options, sheet, y_offset, options_to_print=None):
        y_offset = super()._inject_report_options_into_xlsx_sheet(
            options, sheet, y_offset, options_to_print=options_to_print)
        caption = self._adams_bucket_caption(options) or self._adams_overdue_caption(options) or self._adams_supplier_caption(options)
        if caption:
            sheet.write(y_offset, 0, _('Aging bucket') if options.get('adams_aging_bucket')
                        else _('Overdue balances') if options.get('adams_overdue_metric')
                        else _('Supplier payment schedule'))
            sheet.write(y_offset, 1, caption)
            return y_offset + 1
        return y_offset
