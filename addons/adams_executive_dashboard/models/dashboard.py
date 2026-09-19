"""Bounded native analytical report adapters. Enterprise financial mappings pending."""
from datetime import date, datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


# Every source and measure is server-owned. No client-supplied model or domain.
SOURCES = {
    'invoiced_sales': ('account.invoice.report', 'invoice_date',
                       [('state', '=', 'posted'), ('move_type', 'in', ['out_invoice', 'out_refund'])],
                       'price_subtotal:sum', 'account.action_account_invoice_report_all'),
    'confirmed_sales': ('sale.report', 'date', [('state', '=', 'sale')],
                        'price_subtotal:sum', 'sale.action_order_report_all'),
    'orders': ('sale.report', 'date', [('state', '=', 'sale')],
               'order_reference:count_distinct', 'sale.action_order_report_all'),
    'purchases': ('purchase.report', 'date_order', [('state', '=', 'purchase')],
                  'untaxed_total:sum', 'purchase.action_purchase_order_report_all'),
}
SECTIONS = {
    'finance': ['revenue', 'profit', 'cash', 'receivables', 'payables'],
    'sales': ['invoiced_sales', 'confirmed_sales', 'orders'],
    'operations': ['purchases', 'inventory', 'crm', 'hr'],
}


class ExecutiveDashboard(models.AbstractModel):
    _name = 'adams.executive.dashboard'
    _description = 'Adams Executive Dashboard'

    def _authorize(self):
        if not (self.env.user.has_group('adams_executive_dashboard.group_dashboard_user')
                or self.env.user.has_group('base.group_system')):
            raise AccessError(_('You do not have access to the executive dashboard.'))

    def _scope(self, options):
        self._authorize()
        if not isinstance(options, dict) or set(options) != {'company_id', 'date_from', 'date_to', 'as_of'}:
            raise ValidationError(_('Invalid dashboard filters.'))
        company_id = options['company_id']
        if type(company_id) is not int or company_id not in self.env.companies.ids:
            raise AccessError(_('Select an authorized active company.'))
        try:
            dates = [date.fromisoformat(options[key]) for key in ('date_from', 'date_to', 'as_of')]
        except (TypeError, ValueError):
            raise ValidationError(_('Use valid ISO dates.')) from None
        if dates[0] > dates[1] or (dates[1] - dates[0]).days > 1095:
            raise ValidationError(_('Select a period of up to three years with the start before the end.'))
        return self.with_context(allowed_company_ids=[company_id]), dates

    @api.model
    def get_bootstrap(self):
        self._authorize()
        today = fields.Date.context_today(self)
        return {
            'companies': [{'id': c.id, 'name': c.name} for c in self.env.companies],
            'options': {'company_id': self.env.company.id, 'date_from': today.replace(day=1).isoformat(),
                        'date_to': today.isoformat(), 'as_of': today.isoformat()},
        }

    def _native_scope(self, key, dates):
        model, date_field, states, aggregate, action_id = SOURCES[key]
        report = self.env[model]
        report.check_access('read')
        report.check_field_access_rights('read', [date_field, 'company_id', 'state', aggregate.split(':')[0]])
        start, end = dates[:2]
        if report._fields[date_field].type == 'datetime':
            # Inclusive local dates become a half-open UTC range, including DST.
            tz = pytz.timezone(self.env.user.tz or 'UTC')
            start = tz.localize(datetime.combine(start, time.min)).astimezone(pytz.UTC).replace(tzinfo=None)
            end = tz.localize(datetime.combine(end + timedelta(days=1), time.min)).astimezone(pytz.UTC).replace(tzinfo=None)
            bounds = [(date_field, '>=', fields.Datetime.to_string(start)),
                      (date_field, '<', fields.Datetime.to_string(end))]
        else:
            bounds = [(date_field, '>=', start.isoformat()), (date_field, '<=', end.isoformat())]
        domain = [('company_id', '=', self.env.company.id), *states, *bounds]
        return report, domain, aggregate, action_id

    @api.model
    def get_section(self, section, options):
        scoped, dates = self._scope(options)
        if section not in SECTIONS:
            raise ValidationError(_('Unknown dashboard section.'))
        result = []
        for key in SECTIONS[section]:
            item = {'key': key, 'status': 'not_configured', 'value': None}
            if key in SOURCES:
                if SOURCES[key][0] not in scoped.env:
                    item['status'] = 'not_installed'
                else:
                    try:
                        report, domain, aggregate, action_id = scoped._native_scope(key, dates)
                        # __count distinguishes an empty native report from a real zero.
                        rows = report._read_group(domain, aggregates=[aggregate, '__count'])
                        value, count = rows[0]
                        item.update(status='ready' if count else 'empty', value=value if count else None,
                                    source=report._description, measure=aggregate,
                                    date_field=SOURCES[key][1], domain=domain,
                                    drilldown=bool(scoped.env.ref(action_id, raise_if_not_found=False)))
                    except AccessError:
                        item['status'] = 'restricted'
            result.append(item)
        currency = scoped.env.company.currency_id
        return {'items': result, 'company_id': scoped.env.company.id,
                'currency': currency.name, 'digits': currency.decimal_places,
                'generated_at': fields.Datetime.to_string(fields.Datetime.now())}

    @api.model
    def open_report(self, key, options):
        scoped, dates = self._scope(options)
        if key not in SOURCES or SOURCES[key][0] not in scoped.env:
            raise ValidationError(_('This native report is not configured.'))
        report, domain, aggregate, action_id = scoped._native_scope(key, dates)
        action = scoped.env['ir.actions.actions']._for_xml_id(action_id)
        # Discard native default filters that would silently change the chosen scope.
        action.update(domain=domain, context={
            'allowed_company_ids': [scoped.env.company.id],
            'lang': self.env.lang, 'tz': self.env.user.tz or 'UTC',
            'pivot_measures': [aggregate.split(':')[0]],
            'graph_measure': aggregate.split(':')[0],
        })
        return action
