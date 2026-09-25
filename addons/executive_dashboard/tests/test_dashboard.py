from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, freeze_time, new_test_user, tagged

from odoo.addons.executive_dashboard.models import dashboard as dashboard_module


@tagged('post_install', '-at_install')
class TestDashboard(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Dashboard = cls.env['executive.dashboard']
        # Dashboard user with accounting read access, and one without any app rights.
        cls.finance_user = new_test_user(
            cls.env, login='ed_finance', groups='executive_dashboard.group_user,account.group_account_readonly')
        cls.plain_user = new_test_user(cls.env, login='ed_plain', groups='executive_dashboard.group_user')
        cls.outsider = new_test_user(cls.env, login='ed_outsider', groups='base.group_user')

    def setUp(self):
        super().setUp()
        dashboard_module.cache_clear()

    def as_user(self, user):
        return self.Dashboard.with_user(user)

    # -- install -------------------------------------------------------------

    def test_install(self):
        action = self.env.ref('executive_dashboard.action_dashboard')
        self.assertEqual(action.tag, 'executive_dashboard.dashboard')
        self.assertIn(self.env.ref('executive_dashboard.group_user'),
                      self.env.ref('executive_dashboard.menu_root').group_ids)
        self.assertTrue(self.env.ref('base.user_admin').has_group('executive_dashboard.group_manager'))
        self.assertTrue(self.env.company.executive_dashboard_finance)

    # -- access --------------------------------------------------------------

    def test_user_without_dashboard_group_is_refused(self):
        with self.assertRaises(AccessError):
            self.as_user(self.outsider).get_bootstrap()
        with self.assertRaises(AccessError):
            self.as_user(self.outsider).get_section('finance', 'month')

    def test_user_without_app_rights_gets_restricted(self):
        result = self.as_user(self.plain_user).get_section('finance', 'month')
        self.assertEqual(result['status'], 'restricted')
        self.assertEqual(result['widgets'], {})
        self.assertNotIn('finance', [s['key'] for s in self.as_user(self.plain_user).get_bootstrap()['sections']])
        with self.assertRaises(AccessError):
            self.as_user(self.plain_user).get_drawer('finance.anything')

    def test_bootstrap_has_no_figures(self):
        boot = self.as_user(self.finance_user).get_bootstrap()
        self.assertEqual(set(boot), {'user_name', 'company_name', 'company_initials', 'today', 'sections', 'can_configure'})
        self.assertIn({'key': 'finance', 'period': True}, boot['sections'])
        self.assertFalse(boot['can_configure'])

    def test_missing_app_and_disabled_section_are_hidden(self):
        dashboard = self.as_user(self.finance_user)
        for section, spec in dashboard_module.SECTIONS.items():
            if any(name not in self.env for name in spec['models']):
                self.assertEqual(dashboard.get_section(section)['status'], 'hidden', section)
        self.env.company.executive_dashboard_finance = False
        self.assertEqual(dashboard.get_section('finance')['status'], 'hidden')
        self.assertNotIn('finance', [s['key'] for s in dashboard.get_bootstrap()['sections']])

    # -- get_section framework ----------------------------------------------

    def test_section_returns_its_widget_keys(self):
        result = self.as_user(self.finance_user).get_section('finance', 'month')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(set(result), {'section', 'status', 'period', 'widgets', 'generated_at'})
        self.assertIsInstance(result['widgets'], dict)

    @freeze_time('2026-09-25 10:00:00')
    def test_periods(self):
        dashboard = self.as_user(self.finance_user)
        expected = {
            'month': ('2026-09-01', '2026-09-25'),
            'last_month': ('2026-08-01', '2026-08-31'),
            'quarter': ('2026-07-01', '2026-09-25'),
            'ytd': ('2026-01-01', '2026-09-25'),
        }
        for period, (start, end) in expected.items():
            result = dashboard.get_section('finance', period)['period']
            self.assertEqual((result['date_from'], result['date_to']), (start, end), period)
        custom = dashboard.get_section('finance', 'custom', '2026-02-03', '2026-02-10')['period']
        self.assertEqual((custom['key'], custom['date_from'], custom['date_to']), ('custom', '2026-02-03', '2026-02-10'))
        for bad in (('2026-02-10', '2026-02-03'), ('2020-01-01', '2026-01-01'), ('nope', '2026-01-01')):
            with self.assertRaises(ValidationError):
                dashboard.get_section('finance', 'custom', *bad)
        with self.assertRaises(ValidationError):
            dashboard.get_section('finance', 'week')
        with self.assertRaises(ValidationError):
            dashboard.get_section('payroll', 'month')

    def test_period_scope_for_current_position_sections(self):
        scope = self.as_user(self.finance_user)._period_scope('inventory', 'last_month')
        self.assertEqual(scope['period'], 'now')
        self.assertEqual(scope['date_from'], scope['date_to'])
        self.assertIsInstance(scope['date_from'], date)

    def test_cache_and_refresh(self):
        dashboard = self.as_user(self.finance_user)
        first = dashboard.get_section('finance', 'month')
        self.assertIs(dashboard.get_section('finance', 'month'), first)
        self.assertIsNot(dashboard.get_section('finance', 'month', refresh=True), first)
        # Another user never reads this user's entry.
        admin_result = self.Dashboard.with_user(self.env.ref('base.user_admin')).get_section('finance', 'month')
        self.assertIsNot(admin_result, dashboard.get_section('finance', 'month'))

    def test_section_query_limit(self):
        dashboard = self.as_user(self.finance_user)
        dashboard.get_section('finance', 'month')  # warm the ORM caches
        with self.assertQueryCount(__system__=4, ed_finance=4):
            dashboard.get_section('finance', 'month', refresh=True)

    # -- drawers and search --------------------------------------------------

    def test_unknown_drawer_and_action(self):
        dashboard = self.as_user(self.finance_user)
        for key in ('finance.unknown', 'finance', 'finance.__init__', 'Finance.x', None):
            with self.assertRaises(UserError):
                dashboard.get_drawer(key)
        with self.assertRaises(ValidationError):
            dashboard.open_action('finance.unknown')

    def test_search(self):
        partner = self.env['res.partner'].create({'name': 'Executive Search Example'})
        dashboard = self.as_user(self.finance_user)
        self.assertEqual(dashboard.global_search('e'), [])
        groups = dashboard.global_search('search example')
        partners = next(g for g in groups if g['model'] == 'res.partner')
        self.assertIn({'id': partner.id, 'name': partner.display_name}, partners['records'])
        self.assertLessEqual(max(len(g['records']) for g in groups), 5)
        # No group for a model the user may not read.
        self.assertNotIn('account.move', [g['model'] for g in self.as_user(self.plain_user).global_search('INV')])
