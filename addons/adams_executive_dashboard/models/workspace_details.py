"""Standard-source detail panels for the procurement and CRM workspaces."""
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

_logger = logging.getLogger(__name__)


class ExecutiveDashboardWorkspaceDetails(models.AbstractModel):
    _inherit = 'adams.executive.dashboard'

    def _workspace_record_scope(self, section, dates):
        if section == 'procurement':
            if not self.env.user.has_group('purchase.group_purchase_user'):
                raise AccessError(_('Purchase reporting access is required.'))
            source = self.env['purchase.order']
            source.check_access('read')
            columns = ['name', 'partner_id', 'date_order', 'date_planned',
                       'amount_untaxed', 'currency_id', 'state']
            source.check_field_access_rights('read', ['company_id', *columns])
            domain = [('company_id', '=', self.env.company.id), ('state', '=', 'purchase'),
                      *self._date_bounds(source, 'date_order', dates)]
            return source, domain, columns, 'date_order desc, id desc', 'purchase.purchase_form_action'
        source, domain, _, action_id = self._native_scope('crm', dates)
        columns = ['name', 'partner_id', 'user_id', 'stage_id', 'expected_revenue',
                   'prorated_revenue', 'probability', 'date_deadline', 'create_date']
        source.check_field_access_rights('read', columns)
        return source, domain, columns, 'expected_revenue desc, id desc', action_id

    def _workspace_record_rows(self, source, records, columns):
        rows = records.read(columns)
        dates = [name for name in columns if source._fields[name].type == 'datetime']
        states = dict(source._fields['state']._description_selection(self.env)) if 'state' in columns else {}
        currencies = {currency.id: (currency.name, currency.decimal_places) for currency in records.currency_id} if 'currency_id' in columns else {}
        for row in rows:
            for name in dates:
                row[f'{name}_label'] = (fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(row[name])).strftime('%Y-%m-%d %H:%M') if row[name] else '')
            if states:
                row['state_label'] = states.get(row['state'], row['state'])
            if 'currency_id' in row:
                currency, digits = currencies[row['currency_id'][0]]
                row.update(currency=currency, digits=digits)
        return rows

    def _workspace_records(self, section, dates, offset):
        source, domain, columns, order, _ = self._workspace_record_scope(section, dates)
        total = source.search_count(domain)
        offset = min(offset, ((total - 1) // 25) * 25) if total else 0
        records = source.search(domain, order=order, offset=offset, limit=25)
        return {'status': 'ready' if records else 'empty',
                'rows': self._workspace_record_rows(source, records, columns),
                'total': total, 'offset': offset, 'page_size': 25, 'has_more': offset + len(records) < total,
                'provenance': {'model': source._name, 'domain': domain, 'source_kind': 'operational_records'}}

    def _workspace_amount(self, key, dates, measure=None):
        source, domain, aggregate, _ = self._native_scope(key, dates)
        aggregate = measure or aggregate
        source.check_field_access_rights('read', [aggregate.split(':')[0]])
        value, count = source._read_group(domain, [], [aggregate, '__count'])[0]
        return {'status': 'ready' if count else 'empty', 'value': value if count else None,
                'provenance': self._provenance(key, domain, aggregate)}

    def _workspace_attention(self, kind):
        source, domain = self._procurement_scope(kind)
        columns = ['name', 'partner_id', 'date_order', 'date_planned', 'amount_untaxed', 'currency_id', 'state']
        source.check_field_access_rights('read', columns)
        records = source.search(domain, order='date_planned, id', limit=5)
        return {'status': 'ready' if records else 'empty', 'total': source.search_count(domain),
                'rows': self._workspace_record_rows(source, records, columns), 'date_basis': 'current',
                'provenance': {'model': source._name, 'domain': domain, 'source_kind': 'operational_records'}}

    def _workspace_panel(self, callback):
        try:
            with self.env.cr.savepoint():
                return callback()
        except AccessError:
            return {'status': 'restricted', 'rows': []}
        except Exception as error:
            # Keep sibling workspaces usable; do not expose underlying record data.
            _logger.warning('Dashboard workspace source failed: %s', type(error).__name__)
            return {'status': 'error', 'rows': []}

    @api.model
    def get_workspace_details(self, options, section, offset=0):
        scoped, dates = self._scope(options)
        if section not in ('procurement', 'crm') or type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid workspace or page.'))
        base = {'status': 'ready', 'company_id': scoped.env.company.id,
                'currency': scoped.env.company.currency_id.name,
                'digits': scoped.env.company.currency_id.decimal_places,
                'timezone': scoped.env.user.tz or 'UTC', 'date_from': dates[0].isoformat(),
                'date_to': dates[1].isoformat(), 'generated_at': fields.Datetime.to_string(fields.Datetime.now())}
        model = 'purchase.order' if section == 'procurement' else 'crm.lead'
        if model not in scoped.env:
            return {**base, 'status': 'not_installed', 'rows': []}
        if section == 'crm':
            rows = scoped._workspace_panel(lambda: scoped._workspace_records(section, dates, offset))
            amount = scoped._workspace_panel(lambda: scoped._workspace_amount('crm', dates, 'expected_revenue:sum'))
            return {**base, **rows, 'unweighted': amount}
        return {**base,
                'summary': scoped._workspace_panel(lambda: scoped._workspace_amount('purchases', dates)),
                'approvals': scoped._workspace_panel(lambda: scoped._workspace_attention('approvals')),
                'late': scoped._workspace_panel(lambda: scoped._workspace_attention('late')),
                'recent': scoped._workspace_panel(lambda: scoped._workspace_records(section, dates, offset))}

    @api.model
    def open_workspace_record(self, options, section, record_id=None):
        scoped, dates = self._scope(options)
        if section not in ('procurement', 'crm'):
            raise ValidationError(_('Invalid workspace.'))
        model = 'purchase.order' if section == 'procurement' else 'crm.lead'
        if model not in scoped.env:
            raise ValidationError(_('This application is not installed.'))
        source, domain, _, _, action_id = scoped._workspace_record_scope(section, dates)
        if record_id is not None:
            if type(record_id) is not int or record_id < 1:
                raise ValidationError(_('Invalid source record.'))
            if not source.search([*domain, ('id', '=', record_id)], limit=1):
                raise AccessError(_('The record is unavailable in the selected scope.'))
        action = scoped.env['ir.actions.actions']._for_xml_id(action_id)
        if action.get('res_model') != source._name:
            raise ValidationError(_('The installed source action does not match this workspace.'))
        action.update(domain=domain, context=dict(scoped.env.context))
        if record_id is not None:
            action.update(res_id=record_id, views=[(False, 'form')], view_mode='form')
        return action
