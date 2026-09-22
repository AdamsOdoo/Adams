from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestDashboardWorkspaceDetails(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= (cls.env.ref('purchase.group_purchase_manager')
                                  | cls.env.ref('sales_team.group_sale_manager'))
        cls.env.company.adams_dashboard_crm = True
        cls.env.user.tz = 'UTC'
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}

    def _opportunity(self, amount=1000, probability=25, created='2026-08-15 12:00:00'):
        lead = self.env['crm.lead'].create({'name': 'Workspace opportunity', 'type': 'opportunity',
            'company_id': self.env.company.id, 'expected_revenue': amount, 'probability': probability})
        self.env.cr.execute('UPDATE crm_lead SET create_date = %s WHERE id = %s', [created, lead.id])
        lead.invalidate_recordset(['create_date'])
        return lead

    def _purchase(self, confirmed=True, date='2026-08-15 12:00:00'):
        purchase = self.env['purchase.order'].create({'partner_id': self.partner_a.id,
            'date_order': date, 'order_line': [Command.create({'product_id': self.product_a.id,
                'product_qty': 2, 'price_unit': 50, 'date_planned': '2026-08-25 12:00:00',
                'tax_ids': [Command.clear()]})]})
        if confirmed:
            purchase.button_confirm()
            purchase.date_order = date
        return purchase

    def test_crm_unweighted_matches_same_native_scope_and_real_records(self):
        included = self._opportunity()
        outside = self._opportunity(created='2026-07-15 12:00:00')
        won = self._opportunity()
        won.action_set_won_rainbowman()
        result = self.dashboard.get_workspace_details(self.options, 'crm')
        self.assertEqual(result['status'], 'ready')
        self.assertEqual(result['unweighted']['value'], included.expected_revenue)
        self.assertEqual([row['id'] for row in result['rows']], included.ids)
        self.assertEqual(result['rows'][0]['prorated_revenue'], included.prorated_revenue)
        weighted = next(row for row in self.dashboard.get_section('operations', self.options)['items'] if row['key'] == 'crm')
        self.assertEqual(weighted['value'], included.prorated_revenue)
        action = self.dashboard.open_workspace_record(self.options, 'crm', included.id)
        self.assertEqual(action['res_id'], included.id)
        self.assertEqual(action['res_model'], 'crm.lead')
        for excluded in (outside, won):
            with self.subTest(record=excluded.id), self.assertRaises(AccessError):
                self.dashboard.open_workspace_record(self.options, 'crm', excluded.id)

    def test_purchase_summary_reconciles_native_report_and_recent_is_period_scoped(self):
        included = self._purchase()
        draft = self._purchase(confirmed=False)
        outside = self._purchase(date='2026-07-15 12:00:00')
        self.env.flush_all()
        result = self.dashboard.get_workspace_details(self.options, 'procurement')
        self.assertEqual(result['summary']['status'], 'ready')
        native = self.env['purchase.report'].search([('company_id', '=', self.env.company.id),
                   ('state', '=', 'purchase'), ('date_order', '>=', '2026-08-01 00:00:00'),
                   ('date_order', '<', '2026-09-01 00:00:00')])
        self.assertAlmostEqual(result['summary']['value'], sum(native.mapped('untaxed_total')))
        self.assertEqual([row['id'] for row in result['recent']['rows']], included.ids)
        self.assertEqual(result['recent']['rows'][0]['amount_untaxed'], included.amount_untaxed)
        self.assertEqual(result['approvals']['date_basis'], 'current')
        self.assertEqual(result['late']['date_basis'], 'current')
        action = self.dashboard.open_workspace_record(self.options, 'procurement', included.id)
        self.assertEqual(action['res_id'], included.id)
        for excluded in (draft, outside):
            with self.subTest(record=excluded.id), self.assertRaises(AccessError):
                self.dashboard.open_workspace_record(self.options, 'procurement', excluded.id)

    def test_crm_pagination_and_filter_shrink(self):
        leads = self.env['crm.lead']
        for number in range(27):
            leads |= self._opportunity(amount=number + 1)
        first = self.dashboard.get_workspace_details(self.options, 'crm')
        second = self.dashboard.get_workspace_details(self.options, 'crm', 25)
        self.assertEqual(first['total'], 27)
        self.assertEqual(len(first['rows']), 25)
        self.assertEqual(len(second['rows']), 2)
        self.assertFalse(second['has_more'])
        leads[1:].active = False
        shrunk = self.dashboard.get_workspace_details(self.options, 'crm', 25)
        self.assertEqual(shrunk['offset'], 0)
        self.assertEqual(shrunk['total'], 1)
        self.assertEqual([row['id'] for row in shrunk['rows']], leads[:1].ids)

    def test_source_permissions_and_invalid_rpc_are_enforced(self):
        outsider = new_test_user(self.env, login='workspace_outsider', groups='base.group_user')
        for method, args in [('get_workspace_details', (self.options, 'crm')),
                             ('open_workspace_record', (self.options, 'procurement', 1))]:
            with self.subTest(method=method), self.assertRaises(AccessError):
                getattr(self.dashboard.with_user(outsider), method)(*args)
        reader = new_test_user(self.env, login='workspace_reader',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        result = self.dashboard.with_user(reader).get_workspace_details(self.options, 'procurement')
        self.assertEqual(result['recent']['status'], 'restricted')
        self.assertEqual(result['approvals']['status'], 'restricted')
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_workspace_record(self.options, 'procurement')
        with self.assertRaises(ValidationError):
            self.dashboard.get_workspace_details(self.options, 'res.users')
        with self.assertRaises(ValidationError):
            self.dashboard.open_workspace_record(self.options, 'crm', True)
