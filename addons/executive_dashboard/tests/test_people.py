from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged

from .test_sales_crm import SalesCrmCase


@tagged('post_install', '-at_install')
class TestPeople(SalesCrmCase):

    required = ('hr.employee',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        groups = ['executive_dashboard.group_user', 'hr.group_hr_user']
        for xmlid in ('hr_attendance.group_hr_attendance_manager', 'hr_holidays.group_hr_holidays_user'):
            if cls.env.ref(xmlid, raise_if_not_found=False):
                groups.append(xmlid)
        cls.hr_user = new_test_user(cls.env, login='ed_hr_user', company_id=cls.company.id,
                                    company_ids=[cls.company.id], groups=','.join(groups))
        cls.hr_officer = new_test_user(cls.env, login='ed_hr_officer', company_id=cls.company.id,
                                       company_ids=[cls.company.id],
                                       groups='executive_dashboard.group_user,hr.group_hr_user')
        cls.plain = new_test_user(cls.env, login='ed_people_plain', groups='executive_dashboard.group_user')
        cls.department = cls.env['hr.department'].create({'name': 'Example Department', 'company_id': cls.company.id})
        cls.alpha, cls.beta, cls.gamma = cls.env['hr.employee'].create([
            {'name': name, 'department_id': cls.department.id, 'company_id': cls.company.id}
            for name in ('Example Alpha', 'Example Beta', 'Example Gamma')])

    def dashboard(self, user=None):
        return self.env['executive.dashboard'].with_user(user or self.hr_user)

    def today_bounds(self, user=None):
        dashboard = self.dashboard(user)
        scope = dashboard._period_scope('people', 'month')
        return [fields.Datetime.to_datetime(d) for d in dashboard._utc_bounds(scope['today'], scope['today'])]

    def test_widget_keys(self):
        result = self.section(self.hr_user, 'people')
        self.assertEqual(result['status'], 'ok')
        widgets = result['widgets']
        self.assertEqual(set(widgets), {'kpis', 'attendance', 'leave', 'shifts', 'departments', 'directory'})
        if 'planning.slot' not in self.env:
            self.assertIsNone(widgets['shifts'], 'Planning is not installed: Shifts today is hidden')
            self.assertIsNone(widgets['kpis']['shifts'])
        self.assertEqual(widgets['directory']['per'], 10)

    def test_headcount_and_departments_match_native(self):
        widgets = self.section(self.hr_user, 'people')['widgets']
        native = self.env['hr.employee'].search_count([('company_id', '=', self.company.id)])
        self.assertEqual(widgets['kpis']['headcount'], native)
        dept = next(d for d in widgets['departments'] if d['id'] == self.department.id)
        self.assertEqual(dept['count'], 3)
        drawer = self.dashboard().get_drawer('people.department', {'department_id': self.department.id})
        self.assertEqual([row['label'] for row in drawer['rows']], ['Example Alpha', 'Example Beta', 'Example Gamma'])
        action = self.dashboard().open_action('people.department', {'department_id': self.department.id})
        self.assertEqual(self.env['hr.employee'].search_count(action['domain']), 3)
        with self.assertRaises(ValidationError):
            self.dashboard().get_drawer('people.department', {'department_id': 'x'})

    def test_checked_in_today_matches_native_attendance(self):
        if 'hr.attendance' not in self.env:
            self.skipTest('hr_attendance not installed')
        start, _end = self.today_bounds()
        Attendance = self.env['hr.attendance']
        Attendance.create([
            {'employee_id': self.alpha.id, 'check_in': start + timedelta(minutes=1),
             'check_out': start + timedelta(minutes=2)},
            {'employee_id': self.alpha.id, 'check_in': start + timedelta(minutes=3),
             'check_out': start + timedelta(minutes=4)},
            {'employee_id': self.beta.id, 'check_in': start + timedelta(minutes=5)},
            {'employee_id': self.gamma.id, 'check_in': start - timedelta(hours=3),
             'check_out': start - timedelta(hours=2)},
        ])
        widgets = self.section(self.hr_user, 'people')['widgets']
        start, end = self.today_bounds()
        native = Attendance.search([('check_in', '>=', start), ('check_in', '<', end),
                                    ('employee_id.company_id', '=', self.company.id)])
        self.assertEqual(widgets['kpis']['attendance']['count'], len(native.employee_id))
        self.assertEqual(widgets['kpis']['attendance']['still_in'],
                         len(native.filtered(lambda a: not a.check_out).employee_id))
        rows = {row['employee_id']: row for row in widgets['attendance']['rows']}
        if self.alpha.id in rows:
            self.assertEqual(rows[self.alpha.id]['state'], 'out')
        directory = self.dashboard().get_drawer('people.directory', {'department_id': self.department.id})
        states = {row['employee_id']: row['state'] for row in directory['rows']}
        self.assertEqual(states, {self.alpha.id: 'out', self.beta.id: 'in', self.gamma.id: 'none'})
        employee = self.dashboard().get_drawer('people.employee', {'employee_id': self.beta.id})
        self.assertEqual(employee['state'], 'in')
        action = self.dashboard().open_action('people.attendance', {})
        self.assertEqual(Attendance.search_count(action['domain']), len(native))

    def test_time_off_today_and_next_days(self):
        if 'hr.leave' not in self.env:
            self.skipTest('hr_holidays not installed')
        leave_type = self.env['hr.leave.type'].create({'name': 'Example Leave', 'requires_allocation': False,
                                                       'company_id': self.company.id})
        today = self.dashboard()._period_scope('people', 'month')['today']
        leaves = self.env['hr.leave'].create([
            {'employee_id': self.alpha.id, 'holiday_status_id': leave_type.id,
             'request_date_from': today - timedelta(days=1), 'request_date_to': today + timedelta(days=3)},
            {'employee_id': self.beta.id, 'holiday_status_id': leave_type.id,
             'request_date_from': today + timedelta(days=2), 'request_date_to': today + timedelta(days=4)},
        ])
        leaves.sudo().write({'state': 'validate'})
        widgets = self.section(self.hr_user, 'people')['widgets']
        start, end = self.today_bounds()
        native = self.env['hr.leave'].search([('state', '=', 'validate'), ('date_from', '<', end),
                                              ('date_to', '>', start), ('company_id', '=', self.company.id)])
        self.assertEqual(widgets['kpis']['leave']['count'], len(native.employee_id))
        self.assertIn(self.alpha.id, [row['employee_id'] for row in widgets['leave']['today']['rows']])
        self.assertNotIn(self.beta.id, [row['employee_id'] for row in widgets['leave']['today']['rows']])
        self.assertGreaterEqual(widgets['leave']['next']['count'], 1)
        drawer = self.dashboard().get_drawer('people.leave', {})
        self.assertIn('Example Beta', [row['label'] for row in drawer['rows']])
        status = self.dashboard().get_drawer('people.directory', {'department_id': self.department.id})
        self.assertEqual({r['employee_id']: r['state'] for r in status['rows']}[self.alpha.id], 'off')

    def test_directory_filters_and_pages_on_the_server(self):
        dashboard = self.dashboard()
        page = dashboard.get_drawer('people.directory', {'query': 'Example Be'})
        self.assertEqual([row['name'] for row in page['rows']], ['Example Beta'])
        self.assertEqual(page['count'], 1)
        first = dashboard.get_drawer('people.directory', {})
        total = self.env['hr.employee'].search_count([('company_id', '=', self.company.id)])
        self.assertEqual(first['count'], total)
        self.assertLessEqual(len(first['rows']), 10)
        last = dashboard.get_drawer('people.directory', {'page': 999})
        self.assertEqual(last['page'], max(total - 1, 0) // 10)
        with self.assertRaises(ValidationError):
            dashboard.get_drawer('people.directory', {'page': -1})
        action = dashboard.open_action('people.directory', {'query': 'Example Be'})
        self.assertEqual(self.env['hr.employee'].search(action['domain']), self.beta)

    def test_widgets_follow_app_rights(self):
        widgets = self.section(self.hr_officer, 'people')['widgets']
        self.assertIsNone(widgets['attendance'], 'no Attendances rights')
        self.assertIsNone(widgets['leave'], 'no Time Off officer rights')
        self.assertEqual(widgets['kpis']['headcount'],
                         self.env['hr.employee'].search_count([('company_id', '=', self.company.id)]))
        if 'hr.attendance' in self.env:
            with self.assertRaises(AccessError):
                self.dashboard(self.hr_officer).get_drawer('people.attendance', {})

    def test_user_without_hr_rights_is_restricted(self):
        self.assertEqual(self.section(self.plain, 'people')['status'], 'restricted')
        with self.assertRaises(AccessError):
            self.dashboard(self.plain).get_drawer('people.employees', {})

    def test_query_limit(self):
        dashboard = self.dashboard()
        dashboard.get_section('people', 'month', refresh=True)
        self.env.invalidate_all()
        with self.assertQueryCount(**{self.env.user.login: 40}):
            dashboard.get_section('people', 'month', refresh=True)
