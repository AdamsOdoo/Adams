"""People: headcount, attendance today, time off, shifts today, departments and directory.

Current position only (no period). Days are the user's (``_utc_bounds``).

- Headcount: active ``hr.employee`` of the current companies, by ``department_id`` (a field
  of ``hr.version`` reached through ``_inherits``; Odoo groups employees on it itself).
- Attendance today (Attendances): ``hr.attendance`` with ``check_in`` today, one line per
  employee: first check-in, last check-out, worked hours (``worked_hours`` of closed
  attendances plus the time since check-in of an open one). Still in = an open attendance.
  Shown to Attendance officers and above; record rules apply.
- Time off (Time Off): approved ``hr.leave`` (``state = 'validate'``) overlapping today, and
  those starting in the next 7 days. Shown to Time Off officers and responsibles.
- Shifts today (Planning, Enterprise): published ``planning.slot`` overlapping today,
  grouped by time slot. ``None`` when Planning is not installed or not readable.
- Directory: employees paged on the server (department and name filters), with today's
  attendance status.
"""
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools.misc import format_date, formatLang

PANEL_ROWS = 9
LEAVE_ROWS = 5
SHIFT_ROWS = 6
SHIFT_SLOTS = 4
DRAWER_ROWS = 50
DIRECTORY_PAGE = 10
QUERY_MAX = 100
LEAVE_DAYS = 7
ATTENDANCE_GROUPS = ('hr_attendance.group_hr_attendance_officer',)
LEAVE_GROUPS = ('hr_holidays.group_hr_holidays_user', 'hr_holidays.group_hr_holidays_responsible')


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_people(self, scope):
        """People widgets: ``kpis``, ``attendance``, ``leave``, ``shifts``, ``departments``,
        ``directory``; a widget whose app is missing or that the user may not read is ``None``."""
        attendance = self._ppl_attendance(scope, PANEL_ROWS) if self._ppl_can('attendance') else None
        leave = self._ppl_leave(scope, LEAVE_ROWS) if self._ppl_can('leave') else None
        shifts = self._ppl_shifts(scope, SHIFT_ROWS) if self._ppl_can('shifts') else None
        departments = self._ppl_departments(scope)
        return {
            'kpis': {
                'headcount': sum(d['count'] for d in departments),
                'attendance': attendance and {k: attendance[k] for k in ('count', 'still_in', 'checked_out')},
                'leave': leave and {'count': leave['today']['count']},
                'shifts': shifts and {'count': shifts['count'], 'slots': len(shifts['slots'])},
            },
            'attendance': attendance,
            'leave': leave,
            'shifts': shifts,
            'departments': departments,
            'directory': dict(self._ppl_directory(scope, {}), options=[
                {'id': d['id'], 'name': d['name']} for d in departments if d['id']]),
        }

    # ------------------------------------------------------------------ access

    def _ppl_can(self, widget):
        """Whether the app behind ``widget`` is installed and the user may read it."""
        if widget == 'attendance':
            return self._sal_can_read('hr.attendance') and self._ppl_in_groups(ATTENDANCE_GROUPS)
        if widget == 'leave':
            return self._sal_can_read('hr.leave') and self._ppl_in_groups(LEAVE_GROUPS)
        if widget == 'shifts':
            if not self._sal_can_read('planning.slot'):
                return False
            names = self.env['planning.slot']._fields
            return all(name in names for name in ('start_datetime', 'end_datetime', 'resource_id'))
        raise ValidationError(self.env._('Unknown detail.'))

    def _ppl_in_groups(self, groups):
        user = self.env.user
        return self.env.is_superuser() or any(
            self.env.ref(group, raise_if_not_found=False) and user.has_group(group) for group in groups)

    def _ppl_check(self, widget):
        if not self._ppl_can(widget):
            raise AccessError(self.env._('This section is not available to you.'))

    def _ppl_scope(self):
        return self._period_scope('people', 'month')

    def _ppl_today(self, scope):
        return self._utc_bounds(scope['today'], scope['today'])

    def _ppl_time(self, value):
        """Local time of a UTC datetime as ``HH:MM``, or ``False``."""
        return fields.Datetime.context_timestamp(self, value).strftime('%H:%M') if value else False

    # ------------------------------------------------------------------ employees

    def _ppl_employee_domain(self, scope, department_id=False, query=''):
        domain = Domain([('active', '=', True), ('company_id', 'in', scope['companies'].ids)])
        if department_id:
            domain &= Domain('department_id', '=', department_id)
        if query:
            domain &= Domain('name', 'ilike', query)
        return domain

    def _ppl_departments(self, scope):
        """``[{id, name, count}]`` of active employees by department, largest first."""
        groups = self.env['hr.employee']._read_group(
            self._ppl_employee_domain(scope), ['department_id'], ['__count'], order='__count desc')
        return [{'id': dept.id or False, 'name': dept.display_name if dept else self.env._('No department'),
                 'count': count} for dept, count in groups]

    def _ppl_employee(self, args):
        employee = self.env['hr.employee'].browse(self._positive_id(args, 'employee_id')).exists()
        if not employee:
            raise ValidationError(self.env._('Unknown detail.'))
        employee.check_access('read')
        return employee

    def _ppl_department_id(self, args):
        """A department id from client arguments (``False`` = employees without a department)."""
        return self._positive_id(args, 'department_id', optional=True)

    def _ppl_status(self, scope, employees):
        """``{employee_id: {'in', 'out', 'state'}}`` for today; state is ``in`` (open attendance),
        ``out`` (checked out), ``off`` (approved time off today) or ``none``."""
        status = {e.id: {'in': False, 'out': False, 'state': 'none'} for e in employees}
        if not employees:
            return status
        if self._ppl_can('leave'):
            for employee, in self.env['hr.leave']._read_group(
                    self._ppl_leave_domain(scope, 0, 0) & Domain('employee_id', 'in', employees.ids), ['employee_id']):
                status[employee.id]['state'] = 'off'
        if self._ppl_can('attendance'):
            domain = self._ppl_attendance_domain(scope) & Domain('employee_id', 'in', employees.ids)
            for line in self._ppl_attendance_lines(domain, len(employees), 0):
                status[line['employee_id']].update({'in': line['in'], 'out': line['out'], 'state': line['state']})
        return status

    # ------------------------------------------------------------------ attendance

    def _ppl_attendance_domain(self, scope):
        start, end = self._ppl_today(scope)
        return Domain([('check_in', '>=', start), ('check_in', '<', end),
                       ('employee_id.company_id', 'in', scope['companies'].ids)])

    def _ppl_attendance_lines(self, domain, limit, offset):
        """One line per employee (first check-in first): times, worked hours and state."""
        Attendance = self.env['hr.attendance']
        groups = Attendance._read_group(domain, ['employee_id'], ['check_in:min', 'check_out:max', 'worked_hours:sum'],
                                        order='check_in:min asc, employee_id', limit=limit, offset=offset)
        employees = self.env['hr.employee'].union(*(employee for employee, *_r in groups))
        now = fields.Datetime.now()
        open_since = dict(Attendance._read_group(
            domain & Domain('check_out', '=', False) & Domain('employee_id', 'in', employees.ids),
            ['employee_id'], ['check_in:max']))
        lines = []
        for employee, first, last, worked in groups:
            since = open_since.get(employee)
            if since:
                worked = (worked or 0.0) + max((now - since).total_seconds(), 0) / 3600
            lines.append({
                'employee_id': employee.id, 'name': employee.name, 'department': employee.department_id.name or '',
                'in': self._ppl_time(first), 'out': False if since else self._ppl_time(last),
                'hours': round(worked or 0.0, 2), 'state': 'in' if since else 'out',
            })
        return lines

    def _ppl_attendance(self, scope, limit):
        """Employees checked in today (still in / checked out) and the first ``limit`` lines."""
        Attendance = self.env['hr.attendance']
        domain = self._ppl_attendance_domain(scope)
        count = len(Attendance._read_group(domain, ['employee_id']))
        still_in = len(Attendance._read_group(domain & Domain('check_out', '=', False), ['employee_id']))
        return {'count': count, 'still_in': still_in, 'checked_out': count - still_in,
                'rows': self._ppl_attendance_lines(domain, limit, 0)}

    def _drawer_people_attendance(self, args):
        self._ppl_check('attendance')
        _ = self.env._
        data = self._ppl_attendance(self._ppl_scope(), DRAWER_ROWS)
        return {'title': _('Attendance today'),
                'sub': _('%(count)s checked in · %(in)s still in', count=data['count'], **{'in': data['still_in']}),
                'rows': data['rows'], 'count': data['count'],
                'action': {'key': 'people.attendance', 'args': {}}, 'dest': _('Attendances')}

    def _action_people_attendance(self, args):
        self._ppl_check('attendance')
        return self._window('hr_attendance.hr_attendance_action', self.env._('Attendance today'), 'hr.attendance',
                            self._ppl_attendance_domain(self._ppl_scope()))

    # ------------------------------------------------------------------ time off

    def _ppl_leave_domain(self, scope, first, last):
        """Approved time off overlapping the user's days ``today + first`` to ``today + last``."""
        start, end = self._utc_bounds(scope['today'] + timedelta(days=first), scope['today'] + timedelta(days=last))
        return Domain([('state', '=', 'validate'), ('date_from', '<', end), ('date_to', '>', start),
                       ('company_id', 'in', scope['companies'].ids)])

    def _ppl_upcoming_domain(self, scope):
        """Approved time off starting in the next 7 days (tomorrow to today + 7)."""
        start = self._ppl_today(scope)[1]
        end = self._utc_bounds(scope['today'], scope['today'] + timedelta(days=LEAVE_DAYS))[1]
        return Domain([('state', '=', 'validate'), ('date_from', '>=', start), ('date_from', '<', end),
                       ('company_id', 'in', scope['companies'].ids)])

    def _ppl_leave_rows(self, domain, limit):
        leaves = self.env['hr.leave'].search(domain, order='date_from asc, id asc', limit=limit)
        rows = []
        for leave in leaves:
            first, last = leave.request_date_from, leave.request_date_to
            dates = format_date(self.env, first) if first and (not last or first == last) else \
                '%s – %s' % (format_date(self.env, first), format_date(self.env, last)) if first else ''
            rows.append({'id': leave.id, 'employee_id': leave.employee_id.id, 'name': leave.employee_id.name or '',
                         'type': leave.holiday_status_id.name or '', 'dates': dates})
        return rows

    def _ppl_leave(self, scope, limit):
        """Approved time off today and starting in the next 7 days (count and first rows each)."""
        Leave = self.env['hr.leave']
        today = self._ppl_leave_domain(scope, 0, 0)
        upcoming = self._ppl_upcoming_domain(scope)
        return {
            'today': {'count': len(Leave._read_group(today, ['employee_id'])), 'rows': self._ppl_leave_rows(today, limit)},
            'next': {'count': Leave.search_count(upcoming), 'rows': self._ppl_leave_rows(upcoming, limit)},
        }

    def _drawer_people_leave(self, args):
        self._ppl_check('leave')
        _ = self.env._
        data = self._ppl_leave(self._ppl_scope(), DRAWER_ROWS)
        rows = []
        for group, label in (('today', _('Today')), ('next', _('Next 7 days'))):
            for row in data[group]['rows']:
                rows.append({'label': row['name'], 'sub': ' · '.join(filter(None, [row['type'], row['dates']])),
                             'value': label,
                             'open': {'key': 'people.employee', 'args': {'employee_id': row['employee_id']},
                                      'crumb': _('Time off'), 'sec': 'people'}})
        return {'title': _('Time off'), 'sub': _('Today and the next 7 days'), 'rows': rows,
                'action': {'key': 'people.leave', 'args': {}}, 'dest': _('Time Off')}

    def _action_people_leave(self, args):
        self._ppl_check('leave')
        scope = self._ppl_scope()
        domain = self._ppl_leave_domain(scope, 0, 0) | self._ppl_upcoming_domain(scope)
        return self._window('hr_holidays.hr_leave_action_action_approve_department', self.env._('Time off'),
                            'hr.leave', domain)

    # ------------------------------------------------------------------ shifts (Planning, Enterprise)

    def _ppl_shift_domain(self, scope):
        start, end = self._ppl_today(scope)
        Slot = self.env['planning.slot']
        domain = Domain([('start_datetime', '<', end), ('end_datetime', '>', start)])
        if 'state' in Slot._fields:
            domain &= Domain('state', '=', 'published')
        if 'company_id' in Slot._fields:
            domain &= Domain('company_id', 'in', scope['companies'].ids)
        return domain

    def _ppl_shift_row(self, slot):
        employee = slot['employee_id'] if 'employee_id' in slot._fields else self.env['hr.employee']
        role = slot['role_id'].display_name if 'role_id' in slot._fields and slot['role_id'] else ''
        return {'id': slot.id, 'employee_id': employee.id or False,
                'name': employee.name or slot.resource_id.name or self.env._('Open shift'), 'role': role,
                'time': '%s–%s' % (self._ppl_time(slot.start_datetime), self._ppl_time(slot.end_datetime))}

    def _ppl_shifts(self, scope, limit):
        """Published shifts today: count, the largest time slots and the first ``limit`` shifts."""
        Slot = self.env['planning.slot']
        domain = self._ppl_shift_domain(scope)
        # _read_group cannot group a datetime without a granularity, and hour/day would merge
        # distinct shifts; one day's shifts are few, so read their exact times once and tally.
        today = Slot.search_fetch(domain, ['start_datetime', 'end_datetime'], order='start_datetime asc, id asc')
        slots = {}
        for slot in today:
            label = '%s–%s' % (self._ppl_time(slot.start_datetime), self._ppl_time(slot.end_datetime))
            slots[label] = slots.get(label, 0) + 1
        ranked = sorted(slots.items(), key=lambda item: (-item[1], item[0]))[:SHIFT_SLOTS]
        rows = today[:limit]
        return {'count': sum(slots.values()), 'slots': [{'time': t, 'count': n} for t, n in ranked],
                'rows': [self._ppl_shift_row(slot) for slot in rows]}

    def _drawer_people_shifts(self, args):
        self._ppl_check('shifts')
        _ = self.env._
        data = self._ppl_shifts(self._ppl_scope(), DRAWER_ROWS)
        rows = [{'label': row['name'], 'sub': row['role'], 'value': row['time'],
                 'open': {'key': 'people.employee', 'args': {'employee_id': row['employee_id']},
                          'crumb': _('Shifts today'), 'sec': 'people'} if row['employee_id'] else None}
                for row in data['rows']]
        return {'title': _('Shifts today'), 'sub': _('%s shifts', data['count']), 'rows': rows,
                'action': {'key': 'people.shifts', 'args': {}}, 'dest': _('Planning')}

    def _action_people_shifts(self, args):
        self._ppl_check('shifts')
        return self._window('planning.planning_action_schedule_by_resource', self.env._('Shifts today'),
                            'planning.slot', self._ppl_shift_domain(self._ppl_scope()))

    # ------------------------------------------------------------------ departments

    def _drawer_people_employees(self, args):
        """Headcount by department; a department opens its employees."""
        _ = self.env._
        departments = self._ppl_departments(self._ppl_scope())
        rows = [{'label': d['name'], 'value': formatLang(self.env, d['count'], digits=0),
                 'open': {'key': 'people.department', 'args': {'department_id': d['id']}, 'crumb': _('People'),
                          'sec': 'people'}} for d in departments]
        return {'title': _('Employees'), 'sub': _('%s active employees', sum(d['count'] for d in departments)),
                'rows': rows, 'action': {'key': 'people.employees', 'args': {}}, 'dest': _('Employees')}

    def _action_people_employees(self, args):
        return self._window('hr.open_view_employee_list_my', self.env._('Employees'), 'hr.employee',
                            self._ppl_employee_domain(self._ppl_scope()))

    def _drawer_people_department(self, args):
        """One department's active employees (name and job title)."""
        department_id = self._ppl_department_id(args)
        _ = self.env._
        Employee = self.env['hr.employee']
        domain = self._ppl_employee_domain(self._ppl_scope()) & Domain('department_id', '=', department_id)
        count = Employee.search_count(domain)
        employees = Employee.search(domain, order='name, id', limit=DRAWER_ROWS)
        name = self.env['hr.department'].browse(department_id).display_name if department_id else _('No department')
        return {'title': name, 'sub': _('%s employees', count),
                'rows': [{'label': e.name, 'sub': e.job_title or '',
                          'open': {'key': 'people.employee', 'args': {'employee_id': e.id}, 'crumb': name,
                                   'sec': 'people'}} for e in employees],
                'action': {'key': 'people.department', 'args': {'department_id': department_id}},
                'dest': _('Employees')}

    def _action_people_department(self, args):
        department_id = self._ppl_department_id(args)
        domain = self._ppl_employee_domain(self._ppl_scope()) & Domain('department_id', '=', department_id)
        return self._window('hr.open_view_employee_list_my', self.env._('Employees'), 'hr.employee', domain)

    # ------------------------------------------------------------------ employee

    def _drawer_people_employee(self, args):
        """One employee: department, job, today's check-in/out and status."""
        employee = self._ppl_employee(args)
        _ = self.env._
        scope = self._ppl_scope()
        status = self._ppl_status(scope, employee)[employee.id]
        rows = [{'label': _('Department'), 'value': employee.department_id.name or '—'}]
        if self._ppl_can('attendance'):
            rows += [{'label': _('Check in'), 'value': status['in'] or '—'},
                     {'label': _('Check out'), 'value': status['out'] or '—'}]
        if employee.work_email:
            rows.append({'label': _('Work email'), 'value': employee.work_email})
        if employee.work_phone or employee.mobile_phone:
            rows.append({'label': _('Work phone'), 'value': employee.work_phone or employee.mobile_phone})
        return {'title': employee.name, 'sub': employee.job_title or '', 'rows': rows, 'state': status['state'],
                'action': {'key': 'people.employee', 'args': {'employee_id': employee.id}}, 'dest': _('Employee')}

    def _action_people_employee(self, args):
        employee = self._ppl_employee(args)
        return self._window('hr.open_view_employee_list_my', employee.name, 'hr.employee',
                            [('id', '=', employee.id)], res_id=employee.id)

    # ------------------------------------------------------------------ directory

    def _ppl_directory_filters(self, args):
        department_id = self._positive_id(args, 'department_id', optional=True) if args.get('department_id') else False
        query = args.get('query') or ''
        page = args.get('page', 0)
        if not isinstance(query, str) or type(page) is not int or page < 0:
            raise ValidationError(self.env._('Unknown detail.'))
        return department_id, query.strip()[:QUERY_MAX], page

    def _ppl_directory(self, scope, args):
        """One page of active employees with today's attendance status, and the number of employees."""
        department_id, query, page = self._ppl_directory_filters(args)
        Employee = self.env['hr.employee']
        domain = self._ppl_employee_domain(scope, department_id, query)
        count = Employee.search_count(domain)
        page = min(page, max(count - 1, 0) // DIRECTORY_PAGE)
        employees = Employee.search(domain, order='name, id', offset=page * DIRECTORY_PAGE, limit=DIRECTORY_PAGE)
        status = self._ppl_status(scope, employees)
        rows = [{'employee_id': e.id, 'name': e.name, 'job': e.job_title or '', 'department': e.department_id.name or '',
                 'in': status[e.id]['in'], 'state': status[e.id]['state']} for e in employees]
        return {'rows': rows, 'count': count, 'page': page, 'per': DIRECTORY_PAGE,
                'attendance': self._ppl_can('attendance'),
                'filters': {'department_id': department_id, 'query': query}}

    def _drawer_people_directory(self, args):
        """A page of the employees directory (filters and paging from the section's controls)."""
        return self._ppl_directory(self._ppl_scope(), args)

    def _action_people_directory(self, args):
        department_id, query, _page = self._ppl_directory_filters(args)
        return self._window('hr.open_view_employee_list_my', self.env._('Employees'), 'hr.employee',
                            self._ppl_employee_domain(self._ppl_scope(), department_id, query))
