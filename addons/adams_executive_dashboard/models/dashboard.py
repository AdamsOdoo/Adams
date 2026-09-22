"""Bounded analytical report adapters. Enterprise financial mappings pending."""
from datetime import date, datetime, time, timedelta
import csv
import hashlib
import io
import json
from urllib.parse import urlencode

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools import html2plaintext


# Every source and measure is server-owned. No client-supplied model or domain.
SOURCES = {
    'invoiced_sales': ('account.invoice.report', 'invoice_date',
                       [('state', '=', 'posted'), ('move_type', 'in', ['out_invoice', 'out_refund'])],
                       'price_subtotal:sum', 'account.action_account_invoice_report_all'),
    'invoiced_margin': ('account.invoice.report', 'invoice_date',
                       [('state', '=', 'posted'), ('move_type', 'in', ['out_invoice', 'out_refund'])],
                       'price_margin:sum', 'account.action_account_invoice_report_all'),
    'confirmed_sales': ('sale.report', 'date', [('state', '=', 'sale')],
                        'price_subtotal:sum', 'sale.action_order_report_all'),
    'quotations': ('sale.report', 'date', [('state', 'in', ['draft', 'sent'])],
                   'price_subtotal:sum', 'sale.action_order_report_all'),
    'orders': ('sale.report', 'date', [('state', '=', 'sale')],
               'order_reference:count_distinct', 'sale.action_order_report_all'),
    'purchases': ('purchase.report', 'date_order', [('state', '=', 'purchase')],
                  'untaxed_total:sum', 'purchase.action_purchase_order_report_all'),
    'crm': ('crm.lead', 'create_date', [('type', '=', 'opportunity'), ('active', '=', True),
                                      ('won_status', '=', 'pending')],
            'prorated_revenue:sum', 'crm.crm_opportunity_report_action'),
    'hr': ('hr.leave.report', 'date_from', [('state', '=', 'validate'), ('leave_type', '=', 'request')],
           'number_of_hours:sum', 'hr_holidays.action_hr_leave_report'),
}
DIMENSIONS = {
    'invoiced_sales': {'customer': 'commercial_partner_id', 'salesperson': 'invoice_user_id', 'product': 'product_id'},
    'invoiced_margin': {'customer': 'commercial_partner_id', 'salesperson': 'invoice_user_id', 'product': 'product_id'},
    'confirmed_sales': {'customer': 'commercial_partner_id', 'salesperson': 'user_id', 'product': 'product_id'},
    'quotations': {'customer': 'commercial_partner_id', 'salesperson': 'user_id', 'product': 'product_id'},
    'orders': {'customer': 'commercial_partner_id', 'salesperson': 'user_id'},
    'purchases': {'vendor': 'partner_id', 'buyer': 'user_id', 'product': 'product_id'},
    'crm': {'stage': 'stage_id', 'salesperson': 'user_id'},
    'hr': {'department': 'department_id'},
}
SECTIONS = {
    'finance': ['revenue', 'profit', 'cash', 'receivables', 'payables'],
    'sales': ['invoiced_sales', 'invoiced_margin', 'confirmed_sales', 'orders', 'quotations'],
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
        # Keep client-injected report flags, currency context and timezone out of
        # native evaluation. Scope derives only from validated filters/user data.
        return self.with_context({}, allowed_company_ids=[company_id],
                                 lang=self.env.user.lang or 'en_US', tz=self.env.user.tz or 'UTC'), dates

    @api.model
    def get_bootstrap(self):
        self._authorize()
        today = fields.Date.context_today(self)
        return {
            'user_id': self.env.uid,
            'companies': [self._company_identity(c) for c in self.env.companies],
            'can_configure': self.env.user.has_group('base.group_system'),
            'options': {'company_id': self.env.company.id, 'date_from': today.replace(day=1).isoformat(),
                        'date_to': today.isoformat(), 'as_of': today.isoformat()},
        }

    def _company_identity(self, company):
        # Only called with a record from the validated company context. Bin-size
        # reads test availability without putting image blobs in RPC responses.
        company.check_access('read')
        values = company.with_context(bin_size=True).read(['name', 'logo', 'write_date'])[0]
        name = values['name']
        version = str(values['write_date'] or '')
        return {'id': company.id, 'name': name,
                'initials': ''.join(part[0] for part in name.split()[:2]).upper(),
                'logo_url': ('/web/image/res.company/%s/logo?%s' %
                             (company.id, urlencode({'unique': version}))) if values['logo'] else False,
                'enabled_sections': self._visible_sections(company)}

    def _visible_sections(self, company=None):
        company = company if company is not None else self.env.company
        return [key for key in ('finance', 'sales', 'crm', 'inventory', 'procurement', 'hr')
                if company[f'adams_dashboard_{key}']]

    def _native_scope(self, key, dates):
        model, date_field, states, aggregate, action_id = SOURCES[key]
        report = self.env[model]
        report.check_access('read')
        report.check_field_access_rights('read', [date_field, 'company_id', aggregate.split(':')[0],
                                                *[term[0] for term in states]])
        bounds = self._date_bounds(report, date_field, dates)
        domain = [('company_id', '=', self.env.company.id), *states, *bounds]
        return report, domain, aggregate, action_id

    def _date_bounds(self, report, date_field, dates):
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
        return bounds

    def _recent_scope(self, kind, dates):
        if kind == 'invoices':
            invoices = self.env['account.move']
            invoices.check_access('read')
            invoices.check_field_access_rights('read', ['company_id', 'state', 'move_type', 'invoice_date'])
            return invoices, [('company_id', '=', self.env.company.id), ('state', '=', 'posted'),
                              ('move_type', 'in', ['out_invoice', 'out_refund']),
                              *self._date_bounds(invoices, 'invoice_date', dates)]
        if kind not in ('orders', 'quotations') or 'sale.order' not in self.env:
            raise ValidationError(_('This list is not configured.'))
        orders = self.env['sale.order']
        orders.check_access('read')
        orders.check_field_access_rights('read', ['company_id', 'state', 'date_order'])
        states = ['sale'] if kind == 'orders' else ['draft', 'sent']
        domain = [('company_id', '=', self.env.company.id), ('state', 'in', states),
                  *self._date_bounds(orders, 'date_order', dates)]
        return orders, domain

    @api.model
    def get_fulfillment(self, options, offset=0):
        scoped, dates = self._scope(options)
        if type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid page.'))
        if 'sale.report' not in scoped.env:
            return {'status': 'not_installed', 'rows': []}
        report, domain, aggregate, action_id = scoped._native_scope('confirmed_sales', dates)
        columns = ['product_id', 'product_uom_id', 'product_uom_qty', 'qty_delivered', 'qty_to_deliver']
        report.check_field_access_rights('read', columns)
        domain = [*domain, ('product_id', '!=', False)]
        rows = report._read_group(domain,
            groupby=['product_id', 'product_uom_id'],
            aggregates=['product_uom_qty:sum', 'qty_delivered:sum', 'qty_to_deliver:sum'],
            order='product_id ASC, product_uom_id ASC', offset=offset, limit=26)
        return {'status': 'ready' if rows else 'empty', 'has_more': len(rows) > 25,
                'rows': [{'id': product.id, 'name': product.display_name, 'unit': unit.display_name, 'unit_id': unit.id,
                          'ordered': ordered, 'delivered': delivered, 'remaining': remaining}
                         for product, unit, ordered, delivered, remaining in rows[:25]],
                'provenance': scoped._provenance('confirmed_sales', domain,
                    'product_uom_qty:sum,qty_delivered:sum,qty_to_deliver:sum')}

    @api.model
    def open_fulfillment(self, options, product_id=None, unit_id=None):
        scoped, dates = self._scope(options)
        if 'sale.report' not in scoped.env:
            raise ValidationError(_('This report is not configured.'))
        report, domain, aggregate, action_id = scoped._native_scope('confirmed_sales', dates)
        measures = ['product_uom_qty', 'qty_delivered', 'qty_to_deliver']
        report.check_field_access_rights('read', ['product_id', 'product_uom_id', *measures])
        domain = [*domain, ('product_id', '!=', False)]
        if product_id is not None or unit_id is not None:
            # A displayed row is a product AND unit group. Never silently open
            # another unit or aggregate incompatible units in its source action.
            if type(product_id) is not int or product_id < 1 or type(unit_id) is not int or unit_id < 1:
                raise ValidationError(_('Choose a valid product and unit from the delivery report.'))
            domain += [('product_id', '=', product_id), ('product_uom_id', '=', unit_id)]
            if not report.search(domain, limit=1):
                raise AccessError(_('The product and unit are unavailable in the selected scope.'))
        action = scoped.env['ir.actions.actions']._for_xml_id(action_id)
        action.update(domain=domain, context={**scoped.env.context,
            'pivot_measures': measures, 'pivot_row_groupby': ['product_id', 'product_uom_id'],
            'graph_measure': 'qty_to_deliver', 'group_by': ['product_id', 'product_uom_id']})
        return action

    @api.model
    def get_recent_sales(self, kind, options, offset=0):
        scoped, dates = self._scope(options)
        if kind not in ('orders', 'quotations', 'invoices') or type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid list or page.'))
        if kind != 'invoices' and 'sale.order' not in scoped.env:
            return {'status': 'not_installed', 'rows': []}
        documents, domain = scoped._recent_scope(kind, dates)
        invoice_list = kind == 'invoices'
        date_field = 'invoice_date' if invoice_list else 'date_order'
        columns = ['name', 'partner_id', 'state', 'amount_untaxed', 'currency_id', date_field]
        columns += ['invoice_user_id', 'move_type'] if invoice_list else ['user_id', 'validity_date']
        if not invoice_list and 'delivery_status' in documents._fields:
            columns.append('delivery_status')
        documents.check_field_access_rights('read', columns)
        records = documents.search(domain, order=f'{date_field} desc, id desc', limit=26, offset=offset)
        rows = records[:25].read(columns)
        states = dict(documents._fields['state']._description_selection(scoped.env))
        delivery_labels = dict(documents._fields['delivery_status']._description_selection(scoped.env)) if 'delivery_status' in columns else {}
        type_labels = dict(documents._fields['move_type']._description_selection(scoped.env)) if invoice_list else {}
        for row, record in zip(rows, records[:25]):
            row['delivery_label'] = delivery_labels.get(row.get('delivery_status'))
            row.update(state_label=states[row['state']], currency=record.currency_id.name,
                       digits=record.currency_id.decimal_places, res_model=documents._name)
            if invoice_list:
                row.update(user_id=row['invoice_user_id'], validity_date=False,
                           document_type_label=type_labels[row['move_type']],
                           date_label=fields.Date.to_string(record.invoice_date))
            else:
                row['date_label'] = fields.Datetime.context_timestamp(record, record.date_order).strftime('%Y-%m-%d %H:%M')
        return {'status': 'ready' if rows else 'empty', 'rows': rows, 'has_more': len(records) > 25,
                'offset': offset, 'date_basis': date_field, 'timezone': scoped.env.user.tz or 'UTC',
                'scope_label': (_('Posted invoices and credit notes · Untaxed document values') if invoice_list
                                else _('Untaxed order values'))}

    @api.model
    def open_recent_sale(self, kind, options, record_id=None):
        scoped, dates = self._scope(options)
        orders, domain = scoped._recent_scope(kind, dates)
        action_id = ('account.action_move_out_invoice_type' if kind == 'invoices'
                     else 'sale.action_orders' if kind == 'orders' else 'sale.action_quotations')
        action = scoped.env['ir.actions.actions']._for_xml_id(action_id)
        context = dict(scoped.env.context)
        if kind == 'invoices':
            context['default_move_type'] = 'out_invoice'
        action.update(domain=domain, context=context)
        if record_id is not None:
            if type(record_id) is not int or record_id < 1:
                raise ValidationError(_('Invalid sales record.'))
            if not orders.search([*domain, ('id', '=', record_id)], limit=1):
                raise AccessError(_('The record is unavailable in the selected scope.'))
            action.update(res_id=record_id, views=[(False, 'form')], view_mode='form')
        return action

    def _provenance(self, key, domain, aggregate):
        scope = {'model': SOURCES[key][0], 'action': SOURCES[key][4], 'domain': domain,
                 'company_id': self.env.company.id, 'tz': self.env.user.tz or 'UTC',
                 'measure': aggregate, 'mapping_version': 1}
        scope['fingerprint'] = hashlib.sha256(json.dumps(scope, sort_keys=True).encode()).hexdigest()
        return scope

    def _search_scope(self, kind, dates, query):
        """Allowlisted documents; ORM ACLs and record rules remain active."""
        if kind in ('orders', 'quotations'):
            records, domain = self._recent_scope(kind, dates)
            date_field = 'date_order'
        elif kind in ('invoices', 'bills'):
            records = self.env['account.move']
            records.check_access('read')
            date_field = 'invoice_date'
            types = ['out_invoice', 'out_refund'] if kind == 'invoices' else ['in_invoice', 'in_refund']
            domain = [('company_id', '=', self.env.company.id), ('state', '=', 'posted'),
                      ('move_type', 'in', types), *self._date_bounds(records, date_field, dates)]
        else:
            raise ValidationError(_('Invalid document type.'))
        records.check_field_access_rights('read', ['name', 'partner_id', date_field, 'company_id', 'state'])
        return records, [*domain, '|', ('name', 'ilike', query), ('partner_id.name', 'ilike', query)], date_field

    @api.model
    def search_records(self, query, options, kind='all', offset=0):
        scoped, dates = self._scope(options)
        if (not isinstance(query, str) or not 2 <= len(query.strip()) <= 100
                or kind not in ('all', 'invoices', 'bills', 'orders', 'quotations')
                or type(offset) is not int or not 0 <= offset <= 10000):
            raise ValidationError(_('Enter 2–100 characters and a valid document type or page.'))
        kinds = ('invoices', 'bills', 'orders', 'quotations') if kind == 'all' else (kind,)
        groups = []
        for entry in kinds:
            group = {'kind': entry, 'rows': [], 'status': 'empty', 'has_more': False}
            groups.append(group)
            if entry in ('orders', 'quotations') and 'sale.order' not in scoped.env:
                group['status'] = 'not_installed'
                continue
            try:
                records, domain, date_field = scoped._search_scope(entry, dates, query.strip())
                page = records.search(domain, limit=26, offset=offset, order=f'{date_field} desc, id desc')
                # read() enforces field access too; never use sudo or reveal hidden counts.
                group['rows'] = [{'id': row['id'], 'name': row['name'],
                                  'partner': row['partner_id'][1] if row['partner_id'] else '',
                                  'date': (fields.Datetime.context_timestamp(records, row[date_field]).strftime('%Y-%m-%d')
                                           if date_field == 'date_order' else str(row[date_field])) if row[date_field] else ''}
                                 for row in page[:25].read(['name', 'partner_id', date_field])]
                group.update(status='ready' if page else 'empty', has_more=len(page) > 25)
            except AccessError:
                group.update(status='restricted', rows=[])
        return {'groups': groups, 'offset': offset, 'has_more': any(g['has_more'] for g in groups)}

    @api.model
    def open_search_record(self, query, options, kind, record_id):
        scoped, dates = self._scope(options)
        if (not isinstance(query, str) or not 2 <= len(query.strip()) <= 100
                or type(record_id) is not int or record_id < 1):
            raise ValidationError(_('Invalid search record.'))
        records, domain, _date_field = scoped._search_scope(kind, dates, query.strip())
        if not records.search([*domain, ('id', '=', record_id)], limit=1):
            raise AccessError(_('The record is unavailable in the selected scope.'))
        return {'type': 'ir.actions.act_window', 'res_model': records._name,
                'res_id': record_id, 'views': [(False, 'form')], 'view_mode': 'form',
                'target': 'current', 'context': dict(scoped.env.context)}

    @api.model
    def export_summary(self, options):
        """Re-evaluate authorized metrics; never accept client values."""
        scoped, dates = self._scope(options)
        if not scoped.env.user.has_group('base.group_allow_export'):
            raise AccessError(_('You do not have export permission.'))
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        writer.writerow([_('Section'), _('Metric'), _('Value'), _('Unit'), _('Status'),
                         _('Company'), _('From'), _('To'), _('Balance as of'), _('Source'),
                         _('Last updated UTC'), _('Scope fingerprint'), _('report warning'), _('Date basis')])
        def safe(value):
            if value is None:
                return ''
            if isinstance(value, (int, float)):
                return value
            value = str(value)
            return "'" + value if value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@')) else value
        labels = {
            'revenue': _('Accounting revenue'),
            'profit': _('Net profit'),
            'cash': _('Bank and cash'),
            'cash_flow': _('Net cash movement'),
            'receivables': _('Receivables'),
            'payables': _('Payables'),
            'receivables_overdue': _('Overdue receivables'),
            'payables_overdue': _('Overdue payables'),
            'gross_profit': _('Gross profit'),
            'operating_expenses': _('Operating expenses'),
            'gross_margin': _('Gross margin'),
            'net_margin': _('Net margin'),
            'assets': _('Assets'),
            'liabilities': _('Liabilities'),
            'equity': _('Equity'),
            'standard_forecast': _('short-term cash forecast'),
            'invoiced_sales': _('Net invoiced sales'),
            'invoiced_margin': _('invoiced commercial margin'),
            'confirmed_sales': _('Confirmed sales'),
            'orders': _('Distinct sales orders'),
            'quotations': _('Draft and sent quotations'),
            'purchases': _('Confirmed purchases'),
            'inventory': _('Inventory valuation'),
            'crm': _('Weighted open pipeline'),
            'hr': _('Approved leave hours (signed)'),
            'supplier_overdue': _('Overdue supplier bills'),
            'supplier_today': _('Supplier bills due today'),
            'supplier_due_7': _('Supplier bills due in 7 days'),
            'supplier_due_30': _('Supplier bills due in 30 days'),
        }
        count = 0
        print_rows = []
        for section, label in [('finance', _('Accounting & Finance')), ('sales', _('Sales')), ('operations', _('Operations'))]:
            enabled = scoped._visible_sections()
            if section in ('finance', 'sales') and section not in enabled:
                continue
            result = scoped.get_section(section, options)
            items = [*result['items'], *result.get('supplier_windows', [])]
            if section == 'finance':
                flow = result.get('cash_flow') or {}
                flow_scope = {'model': 'account.report', 'options': flow.get('options'),
                              'mapping_version': flow.get('mapping_version'), 'measure': 'net_increase',
                              'company_id': scoped.env.company.id}
                items.append({'key': 'cash_flow', 'status': flow.get('status', 'not_installed'),
                              'value': flow.get('bridge', {}).get('net_increase', {}).get('value'),
                              'unit': 'currency', 'date_field': 'period', 'source': flow.get('source'),
                              'has_warnings': flow.get('has_warnings'),
                              'provenance': {'model': 'account.report', 'fingerprint': hashlib.sha256(
                                  json.dumps(flow_scope, sort_keys=True, default=str).encode()).hexdigest()}})
            for item in items:
                provenance = item.get('provenance') or {}
                # Stable metric keys match the source drawer and exported definitions.
                row = [label, labels.get(item['key'], item['key']), item.get('value') if item['status'] == 'ready' else None,
                       result['currency'] if item.get('unit') == 'currency' else {
                           'percentage': '%', 'count': _('Count'), 'hours': _('Hours'),
                       }.get(item.get('unit'), item.get('unit', '')),
                       item['status'], scoped.env.company.name, dates[0], dates[1], dates[2],
                       provenance.get('model') or item.get('source', ''), result.get('generated_at', ''),
                       provenance.get('fingerprint', ''), _('Yes') if item.get('has_warnings') else '', item.get('date_field', '')]
                writer.writerow([safe(value) for value in row])
                print_rows.append({'section': row[0], 'metric': row[1], 'value': row[2],
                                   'unit': row[3], 'digits': 0 if item.get('unit') == 'count' else result['digits'],
                                   'status': row[4], 'warning': bool(item.get('has_warnings'))})
                count += 1
        return {'filename': f'executive-summary-{dates[0]}-{dates[1]}.csv',
                'content': '\ufeff' + output.getvalue(), 'row_count': count,
                'print_rows': print_rows, 'company': scoped.env.company.name,
                'company_identity': scoped._company_identity(scoped.env.company),
                'currency_digits': scoped.env.company.currency_id.decimal_places,
                'scope': dict(options), 'generated_at': fields.Datetime.to_string(fields.Datetime.now())}

    @api.model
    def get_section(self, section, options):
        scoped, dates = self._scope(options)
        if section not in SECTIONS:
            raise ValidationError(_('Unknown dashboard section.'))
        result = []
        enabled = scoped._visible_sections()
        for key in SECTIONS[section]:
            visible_key = ('procurement' if key == 'purchases' else key) if section == 'operations' else section
            if visible_key not in enabled:
                continue
            item = {'key': key, 'status': 'not_configured', 'value': None}
            if key == 'inventory':
                # No company valuation aggregate has been approved for this
                # summary. Preserve the working report entry point explicitly.
                if 'stock.quant' not in scoped.env:
                    item['status'] = 'not_installed'
                else:
                    try:
                        products, _domain = scoped._stock_scope(dates, 'current')
                        item.update(status='source_only', source='stock.action_product_stock_view',
                                    drilldown=True, date_field='current',
                                    description=_('Open the stock report for quantities and valuation.'))
                    except AccessError:
                        item['status'] = 'restricted'
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
                                    drilldown=bool(scoped.env.ref(action_id, raise_if_not_found=False)),
                                    unit='hours' if key == 'hr' else 'count' if key == 'orders' else 'currency',
                                    provenance=scoped._provenance(key, domain, aggregate))
                    except AccessError:
                        item['status'] = 'restricted'
            result.append(item)
        currency = scoped.env.company.currency_id
        return {'items': result, 'company_id': scoped.env.company.id,
                'currency': currency.name, 'digits': currency.decimal_places,
                'generated_at': fields.Datetime.to_string(fields.Datetime.now())}

    @api.model
    def open_report(self, key, options, dimension=None, group_id=None):
        scoped, dates = self._scope(options)
        if key not in SOURCES or SOURCES[key][0] not in scoped.env:
            raise ValidationError(_('This report is not configured.'))
        report, domain, aggregate, action_id = scoped._native_scope(key, dates)
        if dimension is not None:
            field = DIMENSIONS.get(key, {}).get(dimension)
            if not field or (group_id is not False and (type(group_id) is not int or group_id < 1)):
                raise ValidationError(_('Invalid report dimension.'))
            report.check_field_access_rights('read', [field])
            domain = [*domain, (field, '=', group_id)]
        action = scoped.env['ir.actions.actions']._for_xml_id(action_id)
        # Discard native default filters that would silently change the chosen scope.
        action.update(domain=domain, context={
            'allowed_company_ids': [scoped.env.company.id],
            'lang': self.env.lang, 'tz': self.env.user.tz or 'UTC',
            'pivot_measures': [aggregate.split(':')[0]],
            'graph_measure': aggregate.split(':')[0],
        })
        if key == 'crm' and action.get('help'):
            # Dict actions returned by model RPC do not follow the action-load
            # HTML normalization path. Safe plain text avoids literal markup
            # without declaring arbitrary configured HTML trusted.
            action['help'] = html2plaintext(action['help'])
        return action

    @api.model
    def get_breakdown(self, key, dimension, options, offset=0):
        scoped, dates = self._scope(options)
        field = DIMENSIONS.get(key, {}).get(dimension)
        if not field or type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid report dimension or page.'))
        if SOURCES[key][0] not in scoped.env:
            return {'status': 'not_installed', 'rows': []}
        report, domain, aggregate, action_id = scoped._native_scope(key, dates)
        report.check_field_access_rights('read', [field])
        rows = report._read_group(domain, groupby=[field], aggregates=[aggregate],
                                  order=f'{aggregate} DESC, {field} ASC', offset=offset, limit=26)
        # Label resolution uses normal record/field access, including archived history.
        values = [{'id': group.id or False, 'label': group.display_name if group else _('Unassigned'),
                   'value': value} for group, value in rows[:25]]
        return {'status': 'ready' if values else 'empty', 'rows': values,
                'has_more': len(rows) > 25, 'offset': offset,
                'unit': 'hours' if key == 'hr' else 'count' if key == 'orders' else 'currency',
                'currency': scoped.env.company.currency_id.name,
                'digits': scoped.env.company.currency_id.decimal_places,
                'provenance': scoped._provenance(key, domain, aggregate)}

    def _product_quantity_scope(self, dates, unit_id):
        report, domain, aggregate, action_id = self._native_scope('invoiced_sales', dates)
        report.check_field_access_rights('read', ['quantity', 'product_id', 'product_uom_id'])
        units = [unit for unit, in report._read_group(domain, ['product_uom_id'], []) if unit]
        units.sort(key=lambda unit: unit.id)
        if unit_id is not None and unit_id is not False and (type(unit_id) is not int or unit_id not in [unit.id for unit in units]):
            raise ValidationError(_('Choose a unit from this report.'))
        selected = unit_id or (units[0].id if units else False)
        return report, [*domain, ('product_uom_id', '=', selected), ('product_id', '!=', False)], units, selected, action_id

    @api.model
    def get_product_quantity_ranking(self, options, unit_id=False):
        scoped, dates = self._scope(options)
        report, domain, units, selected, action_id = scoped._product_quantity_scope(dates, unit_id)
        unit = next((unit for unit in units if unit.id == selected), None)
        rows = report._read_group(domain, ['product_id'], ['quantity:sum'],
                                  order='quantity:sum DESC, product_id ASC', limit=10) if selected else []
        return {'status': 'ready' if rows else 'empty', 'rows': [{'id': product.id, 'label': product.display_name, 'value': quantity} for product, quantity in rows],
                'units': [{'id': u.id, 'name': u.display_name} for u in units], 'unit_id': selected,
                'currency': unit.display_name if unit else '', 'digits': 2, 'unit': 'quantity'}

    @api.model
    def open_product_quantity_report(self, options, product_id=None, unit_id=None):
        scoped, dates = self._scope(options)
        report, domain, units, selected, action_id = scoped._product_quantity_scope(dates, unit_id)
        if product_id is not None:
            if type(product_id) is not int or product_id < 1:
                raise ValidationError(_('Invalid product.'))
            domain.append(('product_id', '=', product_id))
            if not report.search(domain, limit=1):
                raise AccessError(_('The product is unavailable in the selected scope.'))
        action = scoped.env['ir.actions.actions']._for_xml_id(action_id)
        action.update(domain=domain, context={**scoped.env.context,
                      'pivot_measures': ['quantity'], 'graph_measure': 'quantity'})
        return action

    @api.model
    def get_trend(self, key, options):
        scoped, dates = self._scope(options)
        if key not in SOURCES:
            raise ValidationError(_('Unknown dashboard measure.'))
        if SOURCES[key][0] not in scoped.env:
            return {'status': 'not_installed', 'rows': []}
        report, domain, aggregate, action_id = scoped._native_scope(key, dates)
        field = SOURCES[key][1] + ':month'
        rows = report._read_group(domain, groupby=[field], aggregates=[aggregate], order=field)
        return {'status': 'ready' if rows else 'empty',
                'rows': [{'label': period.strftime('%Y-%m'), 'value': value} for period, value in rows],
                'unit': 'hours' if key == 'hr' else 'count' if key == 'orders' else 'currency',
                'currency': scoped.env.company.currency_id.name,
                'digits': scoped.env.company.currency_id.decimal_places,
                'provenance': scoped._provenance(key, domain, aggregate)}

    @api.model
    def export_breakdown(self, key, dimension, options):
        # Native report export is the full-data route. This bounded CSV explicitly
        # refuses truncation rather than exporting a partial ranking as complete.
        scoped, dates = self._scope(options)
        if not self.env.user.has_group('base.group_allow_export'):
            raise AccessError(_('You do not have export permission.'))
        field = DIMENSIONS.get(key, {}).get(dimension)
        if not field or SOURCES[key][0] not in scoped.env:
            raise ValidationError(_('This report is not configured.'))
        report, domain, aggregate, action_id = scoped._native_scope(key, dates)
        report.check_field_access_rights('read', [field])
        rows = report._read_group(domain, groupby=[field], aggregates=[aggregate],
                                  order=f'{aggregate} DESC, {field} ASC', limit=5001)
        if len(rows) > 5000:
            raise ValidationError(_('Use the report export for more than 5,000 groups.'))
        output = io.StringIO(newline='')
        writer = csv.writer(output)
        generated_at = fields.Datetime.to_string(fields.Datetime.now())
        provenance = scoped._provenance(key, domain, aggregate)
        writer.writerow(['Group', 'Value', 'Unit', 'Company', 'From', 'To', 'Source', 'Measure',
                         'Last updated UTC', 'Definition', 'Scope fingerprint'])
        def safe_text(value):
            value = str(value)
            return "'" + value if value.startswith(('\t', '\r', '\n')) or value.lstrip().startswith(('=', '+', '-', '@')) else value
        for group, value in rows:
            writer.writerow([safe_text(group.display_name if group else _('Unassigned')), value,
                             'hours' if key == 'hr' else 'count' if key == 'orders' else scoped.env.company.currency_id.name,
                             safe_text(scoped.env.company.name), dates[0].isoformat(), dates[1].isoformat(),
                             SOURCES[key][0], aggregate, generated_at, 'v4', provenance['fingerprint']])
        return {'filename': f'adams-{key}-{dimension}.csv', 'content': '\ufeff' + output.getvalue(),
                'row_count': len(rows), 'generated_at': generated_at, 'provenance': provenance}

    @api.model
    def get_cash_directory(self, options, offset=0, search=""):
        scoped, dates = self._scope(options)
        if type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid page.'))
        if not isinstance(search, str) or len(search) > 100:
            raise ValidationError(_('Invalid account search.'))
        search = search.strip()
        accounts = scoped.env['account.account'].with_context(active_test=False)
        journals = scoped.env['account.journal'].with_context(active_test=False)
        accounts.check_access('read')
        journals.check_access('read')
        accounts.check_field_access_rights('read', ['name', 'code', 'active', 'currency_id', 'account_type', 'company_ids'])
        journals.check_field_access_rights('read', ['name', 'default_account_id', 'type', 'company_id'])
        domain = [('company_ids', 'in', [scoped.env.company.id]), ('account_type', '=', 'asset_cash'), ('active', '=', True)]
        if search:
            domain += ['|', ('name', 'ilike', search), ('code', 'ilike', search)]
        total_count = accounts.search_count(domain)
        records = accounts.search(domain, order='id', limit=26, offset=offset)
        linked = journals.search([('company_id', '=', scoped.env.company.id),
                                   ('type', 'in', ['bank', 'cash']),
                                   ('default_account_id', 'in', records[:25].ids)])
        return {'status': 'ready' if records else 'empty', 'has_more': len(records) > 25,
                'rows': [{'id': account.id, 'name': account.name, 'code': account.code,
                          'active': account.active,
                          'currency': (account.currency_id or scoped.env.company.currency_id).name,
                          'journals': linked.filtered(lambda j: j.default_account_id == account).mapped('name'),
                          'balance': None, 'balance_status': 'not_configured'} for account in records[:25]],
                'as_of': dates[2].isoformat(), 'total_count': total_count, 'search': search}

    @api.model
    def get_inventory(self, options, offset=0):
        scoped, dates = self._scope(options)
        if type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid page.'))
        if 'stock.quant' not in scoped.env:
            return {'status': 'not_installed', 'rows': []}
        if not self.env.user.has_group('stock.group_stock_user'):
            raise AccessError(_('Inventory reporting access is required.'))
        products = scoped.env['product.product']
        columns = ['display_name', 'qty_available', 'free_qty', 'virtual_available', 'uom_id']
        products.check_access('read')
        products.check_field_access_rights('read', columns)
        domain = [('is_storable', '=', True), ('company_id', 'in', [False, scoped.env.company.id])]
        records = products.search(domain, order='id', offset=offset, limit=26)
        return {'status': 'ready' if records else 'empty', 'rows': records[:25].read(columns),
                'has_more': len(records) > 25, 'date_basis': 'current',
                'company_id': scoped.env.company.id, 'source': 'stock.action_product_stock_view'}

    @api.model
    def open_inventory(self, options):
        scoped, dates = self._scope(options)
        if 'stock.quant' not in scoped.env or not self.env.user.has_group('stock.group_stock_user'):
            raise AccessError(_('Inventory reporting access is required.'))
        scoped.env['product.product'].check_access('read')
        action = scoped.env['ir.actions.actions']._for_xml_id('stock.action_product_stock_view')
        action.update(domain=[('is_storable', '=', True), ('company_id', 'in', [False, scoped.env.company.id])],
                      context={'allowed_company_ids': [scoped.env.company.id],
                               'lang': scoped.env.lang, 'tz': self.env.user.tz or 'UTC'})
        return action
