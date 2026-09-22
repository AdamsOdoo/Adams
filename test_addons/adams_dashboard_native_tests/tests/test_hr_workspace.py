"""Independent ORM fixtures for HR adapter boundaries and native durations."""
from datetime import date, timedelta
from unittest.mock import patch

from odoo import Command, fields
from odoo.addons.adams_executive_dashboard.models.hr_workspace import HR_MODELS
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestDashboardHRWorkspace(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= (cls.env.ref('hr.group_hr_manager')
                                  | cls.env.ref('hr_attendance.group_hr_attendance_manager')
                                  | cls.env.ref('hr_holidays.group_hr_holidays_manager')
                                  | cls.env.ref('adams_executive_dashboard.group_dashboard_user'))
        cls.env.user.tz = 'UTC'
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}
        cls.employee = cls.env['hr.employee'].create({'name': 'Workspace staff',
                           'company_id': cls.env.company.id, 'work_email': 'staff@example.test'})
        cls.reader = new_test_user(cls.env, login='hr_workspace_reader',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=cls.env.company.id, company_ids=[Command.set(cls.env.company.ids)])

    def test_dashboard_and_private_hr_boundaries(self):
        outsider = new_test_user(self.env, login='hr_workspace_outsider', groups='base.group_user')
        service = self.dashboard.with_user(outsider)
        for method, args in [('get_hr_workspace', (self.options,)),
                             ('get_employee_profile', (self.options, self.employee.id)),
                             ('open_hr_source', (self.options, 'employees'))]:
            with self.subTest(method=method), self.assertRaises(AccessError):
                getattr(service, method)(*args)
        service = self.dashboard.with_user(self.reader)
        self.assertEqual(service.get_hr_workspace(self.options, 'employees')['status'], 'restricted')
        with self.assertRaises(AccessError):
            service.get_employee_profile(self.options, self.employee.id)
        with self.assertRaises(AccessError):
            service.open_hr_source(self.options, 'employees', record_id=self.employee.id)

    def test_employee_current_archived_pages_and_private_profile_fields(self):
        employees = self.env['hr.employee'].create([
            {'name': f'Bounded staff {n:02}', 'company_id': self.env.company.id} for n in range(27)])
        filters = {'search': 'Bounded staff'}
        first = self.dashboard.get_hr_workspace(self.options, 'employees', filters)
        last = self.dashboard.get_hr_workspace(self.options, 'employees', filters, 25)
        self.assertEqual(first['total'], 27)
        self.assertEqual(len(first['rows']), 25)
        self.assertEqual(len(last['rows']), 2)
        employees[1:].active = False
        shrunk = self.dashboard.get_hr_workspace(self.options, 'employees', filters, 25)
        self.assertEqual(shrunk['offset'], 0)
        self.assertEqual([row['id'] for row in shrunk['rows']], employees[:1].ids)
        archived = self.dashboard.get_hr_workspace(self.options, 'employees', {**filters, 'status': 'archived'})
        self.assertEqual(archived['total'], 26)
        profile = self.dashboard.get_employee_profile(self.options, self.employee.id)['employee']
        self.assertEqual(profile['work_email'], 'staff@example.test')
        self.assertFalse(set(profile) & {'private_email', 'private_phone', 'bank_account_id',
                                         'identification_id', 'ssnid', 'contract_id', 'wage'})

    def test_employee_exact_id_company_and_revocation(self):
        other = self.env['res.company'].create({'name': 'Other HR company'})
        foreign = self.env['hr.employee'].with_company(other).create({
            'name': self.employee.name, 'company_id': other.id})
        with self.assertRaises(AccessError):
            self.dashboard.get_employee_profile(self.options, foreign.id)
        with self.assertRaises(AccessError):
            self.dashboard.open_hr_source(self.options, 'employees', record_id=foreign.id)
        foreign_attendance = self.env['hr.attendance'].with_company(other).create({
            'employee_id': foreign.id, 'check_in': '2026-08-12 09:00:00',
            'check_out': '2026-08-12 10:00:00'})
        result = self.dashboard.get_hr_workspace(self.options, 'attendance', {'employee_id': foreign.id})
        self.assertEqual(result['status'], 'empty')
        self.assertEqual(result['total'], 0)
        with self.assertRaises(AccessError):
            self.dashboard.open_hr_source(self.options, 'attendance', record_id=foreign_attendance.id)
        with self.assertRaises(ValidationError):
            self.dashboard.get_employee_profile(self.options, True)
        officer = new_test_user(self.env, login='hr_workspace_officer',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user,hr.group_hr_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        service = self.dashboard.with_user(officer)
        self.assertEqual(service.get_employee_profile(self.options, self.employee.id)['employee']['id'], self.employee.id)
        officer.group_ids -= self.env.ref('hr.group_hr_user')
        with self.assertRaises(AccessError):
            service.get_employee_profile(self.options, self.employee.id)

    def test_department_selection_and_unassigned_actions_reconcile(self):
        department = self.env['hr.department'].create({
            'name': 'Workspace department', 'company_id': self.env.company.id})
        assigned = self.env['hr.employee'].create({
            'name': 'Department fixture assigned', 'company_id': self.env.company.id,
            'department_id': department.id})
        unassigned = self.env['hr.employee'].create({
            'name': 'Department fixture unassigned', 'company_id': self.env.company.id,
            'department_id': False})
        for selection, expected in (({'department_id': department.id}, assigned),
                                    ({'department_unassigned': True}, unassigned),
                                    ({'department_unassigned': False}, assigned | unassigned)):
            filters = {'search': 'Department fixture', **selection}
            with self.subTest(selection=selection):
                result = self.dashboard.get_hr_workspace(self.options, 'employees', filters)
                self.assertEqual(set(row['id'] for row in result['rows']), set(expected.ids))
                self.assertEqual(result['total'], len(expected))
                action = self.dashboard.open_hr_source(self.options, 'employees', filters)
                self.assertEqual(set(self.env['hr.employee'].search(action['domain']).ids),
                                 set(expected.ids))
        for filters in ({'department_unassigned': value} for value in (0, 1, 'true', None)):
            with self.subTest(filters=filters), self.assertRaises(ValidationError):
                self.dashboard.get_hr_workspace(self.options, 'employees', filters)
        for filters in ({'department_id': True}, {'department_id': str(department.id)},
                        {'department_id': -1},
                        {'department_id': department.id, 'department_unassigned': True}):
            with self.subTest(filters=filters), self.assertRaises(ValidationError):
                self.dashboard.open_hr_source(self.options, 'employees', filters)

    def test_attendance_overlap_native_duration_and_prior_day_open_snapshot(self):
        attendance = self.env['hr.attendance']
        closed = attendance.create({'employee_id': self.employee.id, 'check_in': '2026-07-31 22:00:00',
                                    'check_out': '2026-08-01 05:00:00'})
        session = attendance.create({'employee_id': self.employee.id, 'check_in': '2026-08-01 10:00:00',
                                     'check_out': '2026-08-01 11:00:00'})
        opened = attendance.create({'employee_id': self.employee.id,
                                     'check_in': fields.Datetime.now() - timedelta(days=2)})
        result = self.dashboard.get_hr_workspace(self.options, 'attendance', {'employee_id': self.employee.id})
        by_id = {row['id']: row for row in result['rows']}
        self.assertIn(closed.id, by_id)
        self.assertAlmostEqual(by_id[closed.id]['worked_hours'], closed.worked_hours)
        self.assertAlmostEqual(by_id[session.id]['worked_hours'], session.worked_hours)
        current = self.dashboard.get_hr_workspace(self.options, 'attendance',
                   {'employee_id': self.employee.id, 'scope': 'current', 'status': 'open'})
        self.assertEqual([row['id'] for row in current['rows']], opened.ids)
        self.assertIsNone(current['rows'][0]['worked_hours'])
        action = self.dashboard.open_hr_source(self.options, 'attendance',
                    {'employee_id': self.employee.id, 'scope': 'current', 'status': 'open'}, opened.id)
        self.assertEqual(action['res_id'], opened.id)
        self.assertEqual(attendance.search(action['domain']), opened)
        self.assertFalse(any(key.startswith('search_default_') for key in action['context']))

    def test_attendance_sessions_are_not_workforce_or_current_open_employee_counts(self):
        attendance = self.env['hr.attendance']
        employee = self.env['hr.employee'].create({
            'name': 'Session count fixture', 'company_id': self.env.company.id})
        closed = attendance.create([
            {'employee_id': employee.id, 'check_in': '2026-08-01 08:00:00',
             'check_out': '2026-08-01 10:00:00'},
            {'employee_id': employee.id, 'check_in': '2026-08-01 11:00:00',
             'check_out': '2026-08-01 13:00:00'}])
        opened = attendance.create({'employee_id': employee.id, 'check_in': '2026-08-02 08:00:00'})
        with patch.object(fields.Date, 'context_today', return_value=date(2026, 8, 3)):
            overview = self.dashboard.get_hr_workspace(self.options)
        metric = next(item for item in overview['metrics'] if item['key'] == 'checked_in')
        # Independent source grouping: current open records, without any period cutoff.
        native_open = attendance.search([('employee_id.company_id', '=', self.env.company.id),
                                         ('check_out', '=', False)])
        self.assertIn(opened, native_open)
        self.assertEqual(metric['unit'], 'employees')
        self.assertEqual(metric['scope'], 'current')
        self.assertEqual(metric['value'], len(native_open.employee_id))
        worklist = self.dashboard.get_hr_workspace(self.options, 'attendance', {'employee_id': employee.id})
        self.assertEqual(worklist['total'], 3)
        self.assertEqual(set(row['id'] for row in worklist['rows']), set((closed | opened).ids))
        self.assertIsNone(next(row['worked_hours'] for row in worklist['rows'] if row['id'] == opened.id))
        # A historical period does not hide a current open session that began later.
        historical = {**self.options, 'date_from': '2026-07-01', 'date_to': '2026-07-31'}
        current = self.dashboard.get_hr_workspace(historical, 'attendance',
            {'employee_id': employee.id, 'scope': 'current', 'status': 'open'})
        self.assertEqual([row['id'] for row in current['rows']], opened.ids)

    def test_attendance_own_and_assigned_officer_record_rules(self):
        own_employee = self.env['hr.employee'].create({
            'name': 'Own attendance employee', 'company_id': self.env.company.id,
            'user_id': self.reader.id})
        managed_employee = self.env['hr.employee'].create({
            'name': 'Managed attendance employee', 'company_id': self.env.company.id})
        records = self.env['hr.attendance'].create([
            {'employee_id': employee.id, 'check_in': '2026-08-12 09:00:00',
             'check_out': '2026-08-12 10:00:00'}
            for employee in (own_employee, managed_employee, self.employee)])
        service = self.dashboard.with_user(self.reader)
        for officer, expected in ((False, records[:1]), (True, records[:2])):
            if officer:
                # Native assignment grants the officer group; keep the first case own-only.
                managed_employee.attendance_manager_id = self.reader
            with self.subTest(assigned_officer=officer):
                result = service.get_hr_workspace(self.options, 'attendance')
                native = self.env['hr.attendance'].with_user(self.reader).search([
                    ('id', 'in', records.ids)])
                self.assertEqual(set(native.ids), set(expected.ids))
                self.assertEqual(set(row['id'] for row in result['rows']), set(expected.ids))
                self.assertEqual(result['total'], len(expected))
                for record in records - expected:
                    with self.assertRaises(AccessError):
                        service.open_hr_source(self.options, 'attendance', record_id=record.id)
                self.assertEqual(service.get_hr_workspace(self.options, 'employees')['status'], 'restricted')
                with self.assertRaises(AccessError):
                    service.get_employee_profile(self.options, managed_employee.id)

    def test_time_off_overlap_keeps_full_native_request_and_signed_report(self):
        leave_type = self.env['hr.leave.type'].create({'name': 'Workspace leave',
                            'requires_allocation': False, 'leave_validation_type': 'no_validation'})
        leave = self.env['hr.leave'].create({'employee_id': self.employee.id,
            'holiday_status_id': leave_type.id, 'request_date_from': '2026-07-30',
            'request_date_to': '2026-08-04'})
        result = self.dashboard.get_hr_workspace(self.options, 'time_off', {'employee_id': self.employee.id})
        row = next(row for row in result['rows'] if row['id'] == leave.id)
        self.assertEqual(row['duration_unit'], 'days')
        self.assertEqual(row['duration'], leave.number_of_days)
        action = self.dashboard.open_hr_source(self.options, 'time_off', {'employee_id': self.employee.id})
        self.assertIn(leave, self.env['hr.leave'].search(action['domain']))
        signed = self.dashboard.open_hr_source(self.options, 'time_off', {'employee_id': self.employee.id}, report=True)
        self.assertEqual(signed['res_model'], 'hr.leave.report')
        self.assertIn(('employee_id', '=', self.employee.id), signed['domain'])
        self.assertIn(('state', '=', 'validate'), signed['domain'])
        self.assertIn(('leave_type', '=', 'request'), signed['domain'])
        self.assertEqual(signed['context']['pivot_measures'], ['number_of_hours'])
        unassigned = self.dashboard.open_hr_source(self.options, 'time_off',
            {'department_unassigned': True}, report=True)
        self.assertIn(('employee_id.department_id', '=', False), unassigned['domain'])
        if leave.state != 'validate':
            leave.action_validate()
        with patch.object(fields.Date, 'context_today', return_value=date(2026, 8, 3)):
            overview = self.dashboard.get_hr_workspace(self.options)
        preview = overview['previews']['time_off']
        self.assertEqual(preview['status'], 'ready')
        self.assertLessEqual(len(preview['rows']), 5)
        self.assertIn(leave.id, [row['id'] for row in preview['rows']])
        self.assertFalse(any('private_name' in row or 'notes' in row for row in preview['rows']))

    def test_approved_leave_headline_counts_employees_and_worklist_counts_requests(self):
        leave_type = self.env['hr.leave.type'].create({
            'name': 'Concurrent approved requests', 'requires_allocation': False,
            'leave_validation_type': 'no_validation', 'request_unit': 'hour'})
        self.employee.resource_id.tz = 'UTC'
        # Two separate valid sessions overlap the same reporting day, not each other.
        leaves = self.env['hr.leave'].create([
            {'employee_id': self.employee.id, 'holiday_status_id': leave_type.id,
             'request_date_from': '2026-08-03', 'request_date_to': '2026-08-03',
             'request_hour_from': 9.0, 'request_hour_to': 10.0},
            {'employee_id': self.employee.id, 'holiday_status_id': leave_type.id,
             'request_date_from': '2026-08-03', 'request_date_to': '2026-08-03',
             'request_hour_from': 14.0, 'request_hour_to': 15.0}])
        self.assertTrue(all(leave.state == 'validate' for leave in leaves))
        with patch.object(fields.Date, 'context_today', return_value=date(2026, 8, 3)):
            overview = self.dashboard.get_hr_workspace(self.options)
            worklist = self.dashboard.get_hr_workspace(self.options, 'time_off',
                {'scope': 'today', 'status': 'validate', 'employee_id': self.employee.id})
        metric = next(item for item in overview['metrics'] if item['key'] == 'time_off')
        native = self.env['hr.leave'].search([
            ('company_id', '=', self.env.company.id), ('state', '=', 'validate'),
            ('date_from', '<', '2026-08-04 00:00:00'), ('date_to', '>', '2026-08-03 00:00:00')])
        self.assertEqual(metric['unit'], 'employees')
        self.assertEqual(metric['value'], len(native.employee_id))
        self.assertEqual(overview['previews']['time_off']['total'], len(native))
        self.assertEqual(worklist['total'], 2)
        self.assertEqual(set(row['id'] for row in worklist['rows']), set(leaves.ids))
        self.assertGreater(len(native), len(native.employee_id))

    def test_filters_reject_injection_and_dates_keep_timezone(self):
        for filters in ({'model': 'res.users'}, {'employee_id': True}, {'status': 'arbitrary'},
                        {'date_from': '2026-08-01'}, {'date_from': '2026-09-01', 'date_to': '2026-08-01'}):
            with self.subTest(filters=filters), self.assertRaises(ValidationError):
                self.dashboard.get_hr_workspace(self.options, 'attendance', filters)
        self.env.user.tz = 'America/New_York'
        result = self.dashboard.get_hr_workspace(self.options, 'attendance',
            {'date_from': '2026-03-08', 'date_to': '2026-03-08'})
        self.assertEqual(result['timezone'], 'America/New_York')
        self.assertIn(('check_in', '<', '2026-03-09 04:00:00'), result['provenance']['domain'])
        self.assertIn(('check_out', '>=', '2026-03-08 05:00:00'), result['provenance']['domain'])
        attendance = self.env['hr.attendance']
        records = attendance.create([
            {'employee_id': self.employee.id, 'check_in': start, 'check_out': end}
            for start, end in [('2026-03-08 04:00:00', '2026-03-08 04:59:00'),
                               ('2026-03-08 05:00:00', '2026-03-08 06:00:00'),
                               ('2026-03-09 04:00:00', '2026-03-09 05:00:00')]])
        filters = {'date_from': '2026-03-08', 'date_to': '2026-03-08',
                   'employee_id': self.employee.id}
        result = self.dashboard.get_hr_workspace(self.options, 'attendance', filters)
        self.assertEqual([row['id'] for row in result['rows']], records[1].ids)
        action = self.dashboard.open_hr_source(self.options, 'attendance', filters, report=True)
        self.assertEqual(attendance.search(action['domain']), records[1])
        self.assertEqual(action['context']['pivot_measures'], ['worked_hours'])

    def test_optional_planning_distinguishes_missing_from_empty(self):
        result = self.dashboard.get_hr_workspace(self.options, 'shifts')
        if 'planning.slot' not in self.env:
            self.assertEqual(result['status'], 'not_installed')
            self.assertNotIn('total', result)
        else:
            self.assertIn(result['status'], ('ready', 'empty', 'restricted'))

    def test_missing_optional_capability_and_runtime_failure_do_not_become_zero(self):
        # Exercise capability loss without uninstalling any business application.
        with patch.dict(HR_MODELS, {'attendance': 'adams.test.absent.attendance'}):
            result = self.dashboard.get_hr_workspace(self.options, 'attendance')
            self.assertEqual(result['status'], 'not_installed')
            self.assertNotIn('total', result)
            overview = self.dashboard.get_hr_workspace(self.options)
            metric = next(m for m in overview['metrics'] if m['key'] == 'checked_in')
            self.assertEqual(metric['status'], 'not_installed')
            self.assertNotIn('value', metric)
            with self.assertRaises(ValidationError):
                self.dashboard.open_hr_source(self.options, 'attendance')
        with patch.object(type(self.dashboard), '_hr_source_scope', side_effect=RuntimeError('Controlled failure')):
            with self.assertRaises(RuntimeError):
                self.dashboard.get_hr_workspace(self.options, 'attendance')
        recovered = self.dashboard.get_hr_workspace(self.options, 'attendance', {'employee_id': self.employee.id})
        self.assertEqual(recovered['status'], 'empty')
        self.assertEqual(recovered['total'], 0)

    def test_overview_does_not_inherit_hidden_worklist_filters(self):
        plain = self.dashboard.get_hr_workspace(self.options)
        filtered = self.dashboard.get_hr_workspace(self.options, 'overview', {'search': 'NO MATCH'})
        self.assertEqual(plain['metrics'], filtered['metrics'])
        employees = next(item for item in plain['metrics'] if item['key'] == 'employees')
        expected = self.env['hr.employee'].search_count([
            ('active', '=', True), ('company_id', '=', self.env.company.id)])
        self.assertEqual(employees['value'], expected)

    def test_independent_hr_period_changes_records_but_not_current_snapshots(self):
        attendance = self.env['hr.attendance']
        august = attendance.create({'employee_id': self.employee.id,
            'check_in': '2026-08-10 09:00:00', 'check_out': '2026-08-10 10:00:00'})
        september = attendance.create({'employee_id': self.employee.id,
            'check_in': '2026-09-10 09:00:00', 'check_out': '2026-09-10 10:00:00'})
        opened = attendance.create({'employee_id': self.employee.id,
            'check_in': '2026-09-11 09:00:00'})
        filters = {'date_from': '2026-09-10', 'date_to': '2026-09-10',
                   'employee_id': self.employee.id}
        result = self.dashboard.get_hr_workspace(self.options, 'attendance', filters)
        self.assertEqual([row['id'] for row in result['rows']], september.ids)
        action = self.dashboard.open_hr_source(self.options, 'attendance', filters)
        self.assertEqual(attendance.search(action['domain']), september)
        global_result = self.dashboard.get_hr_workspace(self.options, 'attendance',
            {'employee_id': self.employee.id})
        self.assertEqual([row['id'] for row in global_result['rows']], august.ids)
        current = self.dashboard.get_hr_workspace(self.options, 'attendance',
            {**filters, 'scope': 'current', 'status': 'open'})
        self.assertEqual([row['id'] for row in current['rows']], opened.ids)
        baseline = self.dashboard.get_hr_workspace(self.options)
        changed = self.dashboard.get_hr_workspace(self.options, 'overview', filters)
        for key in ('employees', 'checked_in', 'time_off'):
            self.assertEqual(next(m for m in baseline['metrics'] if m['key'] == key),
                             next(m for m in changed['metrics'] if m['key'] == key))

    def test_profile_omits_individually_denied_work_field(self):
        employee_type = type(self.env['hr.employee'])
        original = employee_type.check_field_access_rights

        def restricted(model, operation, field_names):
            if 'work_email' in field_names:
                raise AccessError('Field denied by fixture')
            return original(model, operation, field_names)

        with patch.object(employee_type, 'check_field_access_rights', restricted):
            profile = self.dashboard.get_employee_profile(self.options, self.employee.id)['employee']
        self.assertNotIn('work_email', profile)
        self.assertEqual(profile['name'], self.employee.name)

    def test_no_check_in_today_uses_authorized_native_employee_snapshot(self):
        self.env.user.tz = 'America/New_York'
        employees = self.env['hr.employee'].create([
            {'name': f'Snapshot fixture {label}', 'company_id': self.env.company.id}
            for label in ('no history', 'prior open', 'today', 'future only', 'archived')])
        employees[-1].active = False
        now = fields.Datetime.to_datetime('2026-08-03 16:00:00')
        with patch.object(fields.Datetime, 'now', return_value=now), \
                patch.object(fields.Date, 'context_today', return_value=date(2026, 8, 3)):
            self.env['hr.attendance'].create([
                {'employee_id': employees[1].id, 'check_in': '2026-08-03 03:59:00'},
                {'employee_id': employees[2].id, 'check_in': '2026-08-03 04:00:00',
                 'check_out': '2026-08-03 05:00:00'},
                {'employee_id': employees[3].id, 'check_in': '2026-08-04 09:00:00'}])
            filters = {'scope': 'no_check_in_today', 'search': 'Snapshot fixture'}
            result = self.dashboard.get_hr_workspace(self.options, 'employees', filters)
            self.assertEqual(set(row['id'] for row in result['rows']),
                             set((employees[0] | employees[1] | employees[3]).ids))
            self.assertIn(('last_check_in', '<', '2026-08-03 04:00:00'), result['provenance']['domain'])
            action = self.dashboard.open_hr_source(self.options, 'employees', filters)
            self.assertEqual(set(self.env['hr.employee'].search(action['domain']).ids),
                             set(row['id'] for row in result['rows']))
            with self.assertRaises(AccessError):
                self.dashboard.open_hr_source(self.options, 'employees', filters, employees[2].id)
            overview = self.dashboard.get_hr_workspace(self.options)
            self.assertEqual(len(overview['metrics']), 4)
            metric = overview['attendance_summary']['no_check_in_today']
            native = self.env['hr.employee'].search([
                ('company_id', '=', self.env.company.id), ('active', '=', True),
                '|', ('last_check_in', '=', False), ('last_check_in', '<', '2026-08-03 04:00:00')])
            self.assertEqual(metric['value'], len(native))
            self.assertEqual(metric['unit'], 'employees')
            self.assertEqual(metric['filters'], {'scope': 'no_check_in_today'})
            # Directory/field rights, not dashboard membership, authorize this summary.
            restricted = self.dashboard.with_user(self.reader).get_hr_workspace(self.options)
            self.assertEqual(restricted['attendance_summary']['no_check_in_today']['status'], 'restricted')
            employee_type = type(self.env['hr.employee'])
            original = employee_type.check_field_access_rights

            def denied(model, operation, names):
                if 'last_check_in' in names:
                    raise AccessError('Controlled field denial')
                return original(model, operation, names)

            with patch.object(employee_type, 'check_field_access_rights', denied):
                denied_result = self.dashboard.get_hr_workspace(self.options)
                self.assertEqual(denied_result['attendance_summary']['no_check_in_today']['status'], 'restricted')
                with self.assertRaises(AccessError):
                    self.dashboard.open_hr_source(self.options, 'employees', filters)
            with patch.dict(HR_MODELS, {'attendance': 'adams.test.absent.attendance'}):
                missing = self.dashboard.get_hr_workspace(self.options)
                self.assertEqual(missing['attendance_summary']['no_check_in_today']['status'], 'not_installed')
        for tab, filters in (('attendance', {'scope': 'no_check_in_today'}),
                             ('employees', {'scope': 'no_check_in_today', 'status': 'archived'})):
            with self.subTest(tab=tab, filters=filters), self.assertRaises(ValidationError):
                self.dashboard.get_hr_workspace(self.options, tab, filters)

    def test_overview_optional_failure_keeps_other_sources(self):
        service_type = type(self.dashboard)
        original = service_type._hr_source_scope

        def failed(model, tab, filters, dates):
            if tab == 'attendance':
                raise RuntimeError('Controlled adapter failure')
            return original(model, tab, filters, dates)

        with patch.object(service_type, '_hr_source_scope', failed):
            result = self.dashboard.get_hr_workspace(self.options)
        metrics = {item['key']: item for item in result['metrics']}
        self.assertEqual(metrics['checked_in']['status'], 'error')
        self.assertNotIn('value', metrics['checked_in'])
        self.assertEqual(metrics['employees']['status'], 'ready')

    def test_planning_week_overlap_native_allocation_and_material_exclusion(self):
        if 'planning.slot' not in self.env:
            self.skipTest('Enterprise Planning is not installed in this native test database')
        self.env.user.group_ids |= self.env.ref('planning.group_planning_manager')
        slot_model = self.env['planning.slot']
        common = {'company_id': self.env.company.id, 'state': 'published'}
        continuing = slot_model.create({**common, 'resource_id': self.employee.resource_id.id,
            'start_datetime': '2026-07-31 23:00:00', 'end_datetime': '2026-08-01 06:00:00'})
        vacancy = slot_model.create({**common, 'start_datetime': '2026-08-04 09:00:00',
                                      'end_datetime': '2026-08-04 17:00:00'})
        later = slot_model.create({**common, 'start_datetime': '2026-08-20 09:00:00',
                                    'end_datetime': '2026-08-20 17:00:00'})
        material = self.env['resource.resource'].create({'name': 'Material', 'resource_type': 'material',
                                                        'company_id': self.env.company.id})
        excluded = slot_model.create({**common, 'resource_id': material.id,
            'start_datetime': '2026-08-04 09:00:00', 'end_datetime': '2026-08-04 17:00:00'})
        week = self.dashboard.get_hr_workspace(self.options, 'shifts', {'view': 'week'})
        ids = {row['id'] for row in week['rows']}
        self.assertTrue({continuing.id, vacancy.id}.issubset(ids))
        self.assertFalse({later.id, excluded.id} & ids)
        self.assertEqual(next(row['allocated_hours'] for row in week['rows'] if row['id'] == continuing.id),
                         continuing.allocated_hours)
        month = self.dashboard.get_hr_workspace(self.options, 'shifts', {'view': 'list'})
        self.assertIn(later.id, [row['id'] for row in month['rows']])
        unassigned = self.dashboard.get_hr_workspace(self.options, 'shifts', {'assignment': 'unassigned'})
        self.assertTrue(all(not row['assigned'] for row in unassigned['rows']))
        with self.assertRaises(AccessError):
            self.dashboard.open_hr_source(self.options, 'shifts', record_id=excluded.id)

    def test_nonattendance_overlap_excludes_end_at_period_start(self):
        if 'planning.slot' not in self.env:
            self.skipTest('Enterprise Planning is not installed in this native test database')
        self.env.user.group_ids |= self.env.ref('planning.group_planning_manager')
        common = {'company_id': self.env.company.id, 'state': 'published',
                  'resource_id': self.employee.resource_id.id,
                  'start_datetime': '2026-07-31 22:00:00'}
        slots = self.env['planning.slot']
        ended = slots.create({**common, 'end_datetime': '2026-08-01 00:00:00'})
        continuing = slots.create({**common, 'end_datetime': '2026-08-01 00:01:00'})
        filters = {'employee_id': self.employee.id, 'view': 'week'}
        result = self.dashboard.get_hr_workspace(self.options, 'shifts', filters)
        self.assertEqual([row['id'] for row in result['rows']], continuing.ids)
        self.assertEqual(result['total'], 1)
        action = self.dashboard.open_hr_source(self.options, 'shifts', filters)
        self.assertEqual(slots.search(action['domain']), continuing)
        with self.assertRaises(AccessError):
            self.dashboard.open_hr_source(self.options, 'shifts', filters, ended.id)
        leave_type = self.env['hr.leave.type'].create({'name': 'Boundary leave',
            'requires_allocation': False, 'leave_validation_type': 'hr', 'request_unit': 'hour'})
        self.employee.resource_id.tz = 'Asia/Dubai'
        leave = self.env['hr.leave'].create({'employee_id': self.employee.id,
            'holiday_status_id': leave_type.id, 'request_date_from': '2026-08-01',
            'request_date_to': '2026-08-01', 'request_hour_from': 2.0, 'request_hour_to': 4.0})
        self.assertEqual(leave.state, 'confirm')
        self.assertEqual(leave.date_to, fields.Datetime.to_datetime('2026-08-01 00:00:00'))
        result = self.dashboard.get_hr_workspace(self.options, 'time_off', {'employee_id': self.employee.id})
        self.assertEqual(result['total'], 0)
        # Edit the pending request through native request-hour fields, preserving approval checks.
        leave.request_hour_to = 4.0 + 1.0 / 60.0
        self.assertEqual(leave.date_to, fields.Datetime.to_datetime('2026-08-01 00:01:00'))
        result = self.dashboard.get_hr_workspace(self.options, 'time_off', {'employee_id': self.employee.id})
        self.assertEqual([row['id'] for row in result['rows']], leave.ids)

    def test_planning_own_reader_cannot_see_other_employee_or_drafts(self):
        if 'planning.slot' not in self.env:
            self.skipTest('Enterprise Planning is not installed in this native test database')
        self.env.user.group_ids |= self.env.ref('planning.group_planning_manager')
        own_employee = self.env['hr.employee'].create({'name': 'Reader employee',
            'company_id': self.env.company.id, 'user_id': self.reader.id})
        common = {'company_id': self.env.company.id, 'start_datetime': '2026-08-10 09:00:00',
                  'end_datetime': '2026-08-10 17:00:00', 'state': 'published'}
        slots = self.env['planning.slot']
        own = slots.create({**common, 'resource_id': own_employee.resource_id.id})
        other = slots.create({**common, 'resource_id': self.employee.resource_id.id})
        draft = slots.create({**common, 'resource_id': own_employee.resource_id.id, 'state': 'draft',
                              'start_datetime': '2026-08-11 09:00:00', 'end_datetime': '2026-08-11 17:00:00'})
        service = self.dashboard.with_user(self.reader)
        response = service.get_hr_workspace(self.options, 'shifts', {'status': 'all'})
        self.assertEqual(response['status'], 'ready')
        ids = {row['id'] for row in response['rows']}
        self.assertIn(own.id, ids)
        self.assertNotIn(other.id, ids)
        self.assertNotIn(draft.id, ids)
        for record in (other, draft):
            with self.subTest(record=record.id), self.assertRaises(AccessError):
                service.open_hr_source(self.options, 'shifts', {'status': 'all'}, record.id)
