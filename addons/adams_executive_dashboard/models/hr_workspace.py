"""Permission-preserving, optional HR worklists; no payroll or duration engine."""
from datetime import date, timedelta
import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


_logger = logging.getLogger(__name__)


HR_MODELS = {'employees': 'hr.employee', 'attendance': 'hr.attendance',
             'time_off': 'hr.leave', 'shifts': 'planning.slot'}
HR_ACTIONS = {'employees': 'hr.open_view_employee_list',
              'attendance': 'hr_attendance.hr_attendance_action',
              'time_off': 'hr_holidays.hr_leave_action_action_approve_department',
              'shifts': 'planning.planning_action_schedule_by_resource'}
HR_FIELDS = {
    'employees': ['name', 'active', 'department_id', 'job_id', 'work_location_id'],
    'attendance': ['employee_id', 'department_id', 'check_in', 'check_out', 'worked_hours'],
    'time_off': ['employee_id', 'department_id', 'holiday_status_id', 'date_from', 'date_to',
                 'state', 'number_of_days', 'number_of_hours', 'request_unit_hours'],
    'shifts': ['employee_id', 'department_id', 'resource_id', 'role_id', 'start_datetime',
               'end_datetime', 'allocated_hours', 'state'],
}


class ExecutiveDashboardHR(models.AbstractModel):
    _inherit = 'adams.executive.dashboard'

    def _hr_filters(self, tab, filters, dates):
        if tab not in (*HR_MODELS, 'overview'):
            raise ValidationError(_('Invalid HR view.'))
        if filters is None:
            filters = {}
        allowed = {'department_unassigned', 'search', 'department_id', 'employee_id', 'status', 'leave_type_id',
                   'assignment', 'view', 'scope', 'date_from', 'date_to'}
        if not isinstance(filters, dict) or set(filters) - allowed:
            raise ValidationError(_('Invalid HR filters.'))
        result = dict(filters)
        search = result.get('search', '')
        if not isinstance(search, str) or len(search) > 100:
            raise ValidationError(_('Enter up to 100 characters.'))
        result['search'] = search.strip()
        for name in ('department_id', 'employee_id', 'leave_type_id'):
            value = result.get(name)
            if value not in (None, False) and (type(value) is not int or value < 1):
                raise ValidationError(_('Invalid HR selection.'))
        if 'department_unassigned' in result and type(result['department_unassigned']) is not bool:
            raise ValidationError(_('Invalid HR selection.'))
        if result.get('department_unassigned') and result.get('department_id'):
            raise ValidationError(_('Invalid HR selection.'))
        statuses = {'employees': ('active', 'archived', 'all'),
                    'attendance': ('all', 'open', 'closed'),
                    'time_off': ('all', 'confirm', 'validate1', 'validate', 'refuse', 'cancel'),
                    'shifts': ('all', 'draft', 'published'), 'overview': ('all',)}
        status = result.setdefault('status', {'employees': 'active', 'shifts': 'published'}.get(tab, 'all'))
        if status not in statuses[tab]:
            raise ValidationError(_('Invalid HR status.'))
        if result.get('assignment', 'all') not in ('all', 'assigned', 'unassigned'):
            raise ValidationError(_('Invalid shift assignment.'))
        if result.get('view', 'list') not in ('list', 'week'):
            raise ValidationError(_('Invalid shift view.'))
        scope = result.get('scope', 'period')
        if scope not in ('period', 'current', 'today', 'no_check_in_today') or (
                scope == 'current' and tab not in ('attendance', 'employees')) or (
                scope == 'today' and tab != 'time_off') or (
                scope == 'no_check_in_today' and (tab != 'employees' or status != 'active')):
            raise ValidationError(_('Invalid HR date scope.'))
        if ('date_from' in result) != ('date_to' in result):
            raise ValidationError(_('Select both HR dates.'))
        if 'date_from' in result:
            try:
                start, end = [date.fromisoformat(result[key]) for key in ('date_from', 'date_to')]
            except (TypeError, ValueError):
                raise ValidationError(_('Use valid ISO dates.')) from None
            if start > end or (end - start).days > 1095:
                raise ValidationError(_('Select a period of up to three years with the start before the end.'))
            dates = [start, end, dates[2]]
        if scope == 'today':
            today = fields.Date.context_today(self)
            dates = [today, today, dates[2]]
        if tab == 'shifts' and result.get('view') == 'week':
            dates = [dates[0], min(dates[1], dates[0] + timedelta(days=6)), dates[2]]
        return result, dates

    def _hr_has_source(self, tab, filters):
        return HR_MODELS[tab] in self.env and (
            filters.get('scope') != 'no_check_in_today' or (
                HR_MODELS['attendance'] in self.env and
                'last_check_in' in self.env['hr.employee']._fields))

    def _hr_source_scope(self, tab, filters, dates):
        """Every caller enters through _scope; native ACLs/rules remain in force."""
        model_name = HR_MODELS[tab]
        source = self.env[model_name].with_context(active_test=False)
        source.check_access('read')
        if tab == 'employees':
            # Preserve the existing private work-directory boundary.
            self._workforce_scope()
            domain = [('company_id', '=', self.env.company.id)]
            if filters['status'] != 'all':
                domain.append(('active', '=', filters['status'] == 'active'))
            if filters.get('scope') == 'no_check_in_today':
                # Native employee snapshot, not subtraction of partially visible sessions.
                source.check_field_access_rights('read', ['last_check_in'])
                today = fields.Date.context_today(self)
                bounds = self._date_bounds(source, 'last_check_in', [today, today, dates[2]])
                domain += ['|', ('last_check_in', '=', False), ('last_check_in', '<', bounds[0][2])]
            employee_path = 'id'
            department_path = 'department_id'
            order = 'name, id'
        else:
            employee_path = 'employee_id'
            department_path = 'employee_id.department_id'
            company_path = 'employee_id.company_id' if tab == 'attendance' else 'company_id'
            domain = [(company_path, '=', self.env.company.id)]
            start_field, end_field = {'attendance': ('check_in', 'check_out'),
                                      'time_off': ('date_from', 'date_to'),
                                      'shifts': ('start_datetime', 'end_datetime')}[tab]
            source.check_field_access_rights('read', [company_path.split('.')[0], start_field, end_field])
            if tab == 'attendance' and filters.get('scope') == 'current':
                domain.append(('check_out', '=', False))
            else:
                bounds = self._date_bounds(source, start_field, dates)
                # Operational overlap lists are deliberately separate from report totals.
                domain.append((start_field, '<', bounds[1][2]))
                if tab == 'attendance':
                    domain += ['|', (end_field, '=', False), (end_field, '>=', bounds[0][2])]
                else:
                    domain.append((end_field, '>', bounds[0][2]))
            status = filters['status']
            if tab == 'attendance' and status != 'all':
                domain.append(('check_out', '=' if status == 'open' else '!=', False))
            elif tab != 'attendance' and status != 'all':
                domain.append(('state', '=', status))
            if tab == 'time_off' and filters.get('leave_type_id'):
                domain.append(('holiday_status_id', '=', filters['leave_type_id']))
            if tab == 'shifts':
                # Planning includes material resources; HR shows employees and vacancies.
                domain += ['|', ('resource_type', '=', 'user'), '&', ('resource_id', '=', False),
                           '|', ('role_id.resource_ids.resource_type', '=', 'user'), ('role_id', '=', False)]
                assignment = filters.get('assignment', 'all')
                if assignment != 'all':
                    domain.append(('resource_id', '=' if assignment == 'unassigned' else '!=', False))
            order = f'{start_field} desc, id desc'
        if filters.get('employee_id'):
            domain.append((employee_path, '=', filters['employee_id']))
        if filters.get('department_unassigned'):
            domain.append((department_path, '=', False))
        if filters.get('department_id'):
            domain.append((department_path, '=', filters['department_id']))
        query = filters['search']
        if query:
            if tab == 'employees':
                domain += ['|', ('name', 'ilike', query), ('job_id.name', 'ilike', query)]
            elif tab == 'shifts':
                domain += ['|', ('employee_id.name', 'ilike', query), ('role_id.name', 'ilike', query)]
            else:
                domain.append(('employee_id.name', 'ilike', query))
        columns = HR_FIELDS[tab]
        source.check_field_access_rights('read', columns)
        # Domain/group/order fields are explicit too; permission failures are not zeros.
        roots = {term[0].split('.')[0] for term in domain if isinstance(term, tuple)}
        source.check_field_access_rights('read', list(roots))
        return source, domain, columns, order

    def _hr_rows(self, tab, records, columns):
        rows = records.read(columns)
        states = (dict(records._fields['state']._description_selection(self.env))
                  if 'state' in columns else {})
        datetime_names = [name for name in columns if records._fields[name].type == 'datetime']
        for row in rows:
            for name in datetime_names:
                value = row[name]
                row[f'{name}_label'] = (fields.Datetime.context_timestamp(
                    self, fields.Datetime.to_datetime(value)).strftime('%Y-%m-%d %H:%M') if value else '')
            if tab == 'attendance':
                row['status'] = 'closed' if row['check_out'] else 'open'
                # Open attendance's computed clock duration is not completed work.
                if not row['check_out']:
                    row['worked_hours'] = None
            elif tab == 'time_off':
                row['duration'] = row['number_of_hours'] if row['request_unit_hours'] else row['number_of_days']
                row['duration_unit'] = 'hours' if row['request_unit_hours'] else 'days'
            elif tab == 'shifts':
                row['assigned'] = bool(row['resource_id'])
            if states:
                row['state_label'] = states.get(row['state'], row['state'])
        return rows

    def _hr_overview(self, dates):
        definitions = [
            ('employees', 'employees', {}, 'employees', 'current'),
            ('checked_in', 'attendance', {'scope': 'current', 'status': 'open'}, 'employees', 'current'),
            ('time_off', 'time_off', {'scope': 'today', 'status': 'validate'}, 'employees', 'today'),
            ('unassigned_shifts', 'shifts', {'status': 'published', 'assignment': 'unassigned'}, 'slots', 'period'),
            ('no_check_in_today', 'employees', {'scope': 'no_check_in_today'}, 'employees', 'today'),
        ]
        metrics = []
        attendance_summary = {}
        departments = []
        previews = {}
        for key, tab, raw_filters, unit, scope in definitions:
            item = {'key': key, 'unit': unit, 'scope': scope, 'tab': tab, 'filters': raw_filters}
            if not self._hr_has_source(tab, raw_filters):
                item['status'] = 'not_installed'
            else:
                try:
                    with self.env.cr.savepoint():
                        filters, scoped_dates = self._hr_filters(tab, raw_filters, dates)
                        source, domain, columns, order = self._hr_source_scope(tab, filters, scoped_dates)
                        if key in ('checked_in', 'time_off'):
                            value, record_count = source._read_group(
                                domain, [], ['employee_id:count_distinct', '__count'])[0]
                        else:
                            value = source.search_count(domain)
                            record_count = value
                        item.update(status='ready', value=value)
                        if key == 'no_check_in_today':
                            item['provenance'] = {
                                'model': source._name, 'field': 'last_check_in', 'domain': domain,
                                'source_kind': 'native_stored_employee_snapshot',
                                'timezone': self.env.user.tz or 'UTC',
                            }
                        if key in ('time_off', 'unassigned_shifts'):
                            records = source.search(domain, order=order, limit=5)
                            previews[key] = {'status': 'ready' if records else 'empty', 'total': record_count,
                                             'rows': self._hr_rows(tab, records, columns)}
                        if key == 'employees':
                            departments = [{'id': dep.id or False, 'name': dep.display_name if dep else _('Unassigned'), 'count': count}
                                           for dep, count in source._read_group(domain, ['department_id'], ['__count'],
                                                                               order='department_id', limit=25)]
                except AccessError:
                    item['status'] = 'restricted'
                except Exception as error:
                    _logger.warning('Dashboard HR source %s failed: %s', tab, type(error).__name__)
                    item['status'] = 'error'
            if key in ('time_off', 'unassigned_shifts') and key not in previews:
                previews[key] = {'status': item['status'], 'rows': []}
            if key == 'no_check_in_today':
                attendance_summary[key] = item
            else:
                metrics.append(item)
        return {'status': 'ready', 'metrics': metrics, 'departments': departments, 'previews': previews,
                'attendance_summary': attendance_summary,
                'today': fields.Date.context_today(self).isoformat()}

    @api.model
    def get_hr_workspace(self, options, tab='overview', filters=None, offset=0):
        scoped, dates = self._scope(options)
        filters, dates = scoped._hr_filters(tab, filters, dates)
        if type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid page.'))
        base = {'tab': tab, 'company_id': scoped.env.company.id, 'timezone': scoped.env.user.tz or 'UTC',
                'date_from': dates[0].isoformat(), 'date_to': dates[1].isoformat(),
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'offset': offset, 'page_size': 25, 'rows': []}
        if tab == 'overview':
            return {**base, **scoped._hr_overview(dates)}
        if not scoped._hr_has_source(tab, filters):
            return {**base, 'status': 'not_installed'}
        try:
            source, domain, columns, order = scoped._hr_source_scope(tab, filters, dates)
            total = source.search_count(domain)
            offset = min(offset, ((total - 1) // 25) * 25) if total else 0
            records = source.search(domain, order=order, limit=25, offset=offset)
            rows = scoped._hr_rows(tab, records, columns)
        except AccessError:
            return {**base, 'status': 'restricted'}
        return {**base, 'status': 'ready' if rows else 'empty', 'rows': rows, 'total': total,
                'offset': offset, 'has_more': offset + len(rows) < total,
                'date_basis': 'current' if tab == 'employees' else filters.get('scope', 'period'),
                'provenance': {'model': source._name, 'domain': domain, 'source_kind': 'operational_records'}}

    @api.model
    def get_employee_profile(self, options, employee_id):
        scoped, dates = self._scope(options)
        if type(employee_id) is not int or employee_id < 1:
            raise ValidationError(_('Invalid employee.'))
        employees, employee_domain = scoped._workforce_scope()
        employee = employees.with_context(active_test=False).search([
            ('id', '=', employee_id), ('company_id', '=', scoped.env.company.id)], limit=1)
        if not employee:
            raise AccessError(_('The employee is unavailable in the selected company.'))
        # Explicit work-only allowlist. Do not return the employee's unrestricted read().
        allowed = []
        for name in ('name', 'active', 'department_id', 'job_id', 'parent_id', 'work_email',
                     'work_phone', 'work_location_id', 'resource_calendar_id'):
            if name in employees._fields:
                try:
                    employees.check_field_access_rights('read', [name])
                except AccessError:
                    continue
                allowed.append(name)
        profile = employee.read(allowed)[0]
        summaries = []
        for tab in ('attendance', 'time_off', 'shifts'):
            item = {'tab': tab}
            if HR_MODELS[tab] not in scoped.env:
                item['status'] = 'not_installed'
            else:
                try:
                    with scoped.env.cr.savepoint():
                        filters, interval = scoped._hr_filters(tab, {'employee_id': employee_id}, dates)
                        source, domain, columns, order = scoped._hr_source_scope(tab, filters, interval)
                        item.update(status='ready', count=source.search_count(domain))
                except AccessError:
                    item['status'] = 'restricted'
                except Exception as error:
                    _logger.warning('Dashboard HR source %s failed: %s', tab, type(error).__name__)
                    item['status'] = 'error'
            summaries.append(item)
        return {'status': 'ready', 'company_id': scoped.env.company.id, 'employee': profile,
                'summaries': summaries, 'date_from': dates[0].isoformat(), 'date_to': dates[1].isoformat()}

    @api.model
    def open_hr_source(self, options, tab, filters=None, record_id=None, report=False):
        scoped, dates = self._scope(options)
        filters, dates = scoped._hr_filters(tab, filters, dates)
        if tab not in HR_MODELS or not scoped._hr_has_source(tab, filters):
            raise ValidationError(_('This HR application is not installed.'))
        if type(report) is not bool:
            raise ValidationError(_('Invalid HR source.'))
        source, domain, columns, order = scoped._hr_source_scope(tab, filters, dates)
        if record_id is not None:
            if type(record_id) is not int or record_id < 1:
                raise ValidationError(_('Invalid HR record.'))
            if not source.search([*domain, ('id', '=', record_id)], limit=1):
                raise AccessError(_('The record is unavailable in the selected scope.'))
        action_id = HR_ACTIONS[tab]
        if report and tab == 'attendance':
            action_id = 'hr_attendance.hr_attendance_reporting'
        elif report and tab == 'time_off':
            # Existing signed report has intentionally different date/measure semantics.
            # Opening the operational worklist is not silently relabelled that report.
            report_options = {**options, 'date_from': dates[0].isoformat(), 'date_to': dates[1].isoformat()}
            action = scoped.open_report('hr', report_options)
            report_model = scoped.env['hr.leave.report']
            for key in ('employee_id', 'department_id'):
                if filters.get(key):
                    report_model.check_field_access_rights('read', [key])
                    action['domain'].append((key, '=', filters[key]))
            if filters.get('department_unassigned'):
                report_model.check_field_access_rights('read', ['employee_id'])
                scoped.env['hr.employee'].check_field_access_rights('read', ['department_id'])
                action['domain'].append(('employee_id.department_id', '=', False))
            return action
        action = scoped.env['ir.actions.actions']._for_xml_id(action_id)
        if action.get('res_model') != source._name:
            raise ValidationError(_('The installed HR source action does not match this view.'))
        action.update(domain=domain, context={**scoped.env.context, 'active_test': False})
        if tab == 'attendance' and report:
            action['context'].update(pivot_measures=['worked_hours'], graph_measure='worked_hours')
        if record_id is not None:
            action.update(res_id=record_id, views=[(False, 'form')], view_mode='form')
        return action
