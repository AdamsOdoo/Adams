from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestDashboardNativeApps(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # AccountTestInvoicingCommon creates a finance administrator, not a Sales
        # administrator. Grant fixture roles explicitly; application ACLs stay unchanged.
        cls.env.user.group_ids |= (
            cls.env.ref('sales_team.group_sale_manager')
            | cls.env.ref('purchase.group_purchase_manager')
            | cls.env.ref('stock.group_stock_manager')
            | cls.env.ref('hr_holidays.group_hr_holidays_manager')
        )
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}

    def test_sale_native_distinct_orders_and_multiline_amount(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_a.id,
                            'product_uom_qty': 1, 'price_unit': amount,
                            'tax_ids': [Command.clear()]}) for amount in [40, 60]],
        })
        order.action_confirm()
        order.date_order = '2026-08-15 12:00:00'
        self.env.flush_all()
        items = {item['key']: item for item in self.dashboard.get_section('sales', self.options)['items']}
        self.assertEqual(items['orders']['value'], 1)
        self.assertAlmostEqual(items['confirmed_sales']['value'], 100)
        action = self.dashboard.open_report('confirmed_sales', self.options)
        native = self.env['sale.report'].search(action['domain'])
        self.assertAlmostEqual(sum(native.mapped('price_subtotal')), 100)
        self.assertEqual(len(set(native.mapped('order_reference'))), 1)

    def test_purchase_native_confirmed_scope_and_vendor_groups(self):
        purchase = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id, 'date_order': '2026-08-15 12:00:00',
            'order_line': [Command.create({'product_id': self.product_a.id, 'product_qty': 2,
                           'price_unit': 50, 'date_planned': '2026-08-25 12:00:00',
                           'tax_ids': [Command.clear()]})],
        })
        purchase.button_confirm()
        purchase.date_order = '2026-08-15 12:00:00'
        self.assertEqual(purchase.state, 'purchase')
        self.env.flush_all()
        groups = self.dashboard.get_breakdown('purchases', 'vendor', self.options)
        self.assertEqual(len(groups['rows']), 1)
        self.assertEqual(groups['rows'][0]['id'], self.partner_a.id)
        self.assertAlmostEqual(groups['rows'][0]['value'], 100)
        action = self.dashboard.open_report('purchases', self.options)
        self.assertAlmostEqual(sum(self.env['purchase.report'].search(action['domain']).mapped('untaxed_total')), 100)

    def test_crm_native_weighted_open_pipeline_excludes_won(self):
        opportunity = self.env['crm.lead'].create({
            'name': 'Dashboard opportunity', 'type': 'opportunity', 'company_id': self.env.company.id,
            'expected_revenue': 1000, 'probability': 25,
        })
        # Creation date is immutable in normal workflows; fixed test-only clock fixture.
        self.env.cr.execute('UPDATE crm_lead SET create_date = %s WHERE id = %s', ['2026-08-15 12:00:00', opportunity.id])
        opportunity.invalidate_recordset(['create_date'])
        self.env.flush_all()
        groups = self.dashboard.get_breakdown('crm', 'stage', self.options)
        self.assertAlmostEqual(sum(row['value'] for row in groups['rows']), 250)
        opportunity.action_set_won_rainbowman()
        self.env.flush_all()
        self.assertEqual(self.dashboard.get_trend('crm', self.options)['rows'], [])

    def test_current_stock_uses_native_product_quantity(self):
        product = self.env['product.product'].create({'name': 'Dashboard stock fixture', 'is_storable': True})
        location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        self.env['stock.quant']._update_available_quantity(product, location, 12)
        self.env.flush_all()
        rows = []
        offset = 0
        while True:
            page = self.dashboard.get_inventory(self.options, offset)
            rows += page['rows']
            if not page['has_more']:
                break
            offset += 25
        row = next(row for row in rows if row['id'] == product.id)
        self.assertAlmostEqual(row['qty_available'], 12)
        self.assertAlmostEqual(row['free_qty'], 12)
        self.assertEqual(page['date_basis'], 'current')
        self.assertEqual(self.dashboard.open_inventory(self.options)['res_model'], 'product.product')

    def test_hr_native_report_scope_is_request_not_allocation(self):
        action = self.dashboard.open_report('hr', self.options)
        self.assertEqual(action['res_model'], 'hr.leave.report')
        self.assertIn(('leave_type', '=', 'request'), action['domain'])
        self.assertIn(('state', '=', 'validate'), action['domain'])
        self.assertEqual(action['context']['pivot_measures'], ['number_of_hours'])

    def _sale(self, partner=None, company=None, confirmed=False, amount=10):
        order = self.env['sale.order'].with_company(company or self.env.company).create({
            'partner_id': (partner or self.partner_a).id,
            'date_order': '2026-08-15 12:00:00',
            'order_line': [Command.create({'product_id': self.product_a.id, 'product_uom_qty': 1,
                                          'price_unit': amount, 'tax_ids': [Command.clear()]})],
        })
        if confirmed:
            order.action_confirm()
            order.date_order = '2026-08-15 12:00:00'
        return order

    def test_recent_sales_pages_states_and_drilldown_scope(self):
        from odoo.exceptions import AccessError, ValidationError
        quotes = self.env['sale.order']
        for index in range(27):
            quotes |= self._sale(amount=index + 1)
        confirmed = self._sale(confirmed=True, amount=500)
        outside = self._sale()
        outside.date_order = '2026-09-01 12:00:00'
        first = self.dashboard.get_recent_sales('quotations', self.options)
        second = self.dashboard.get_recent_sales('quotations', self.options, 25)
        self.assertEqual(len(first['rows']), 25)
        self.assertTrue(first['has_more'])
        self.assertEqual(len(second['rows']), 2)
        self.assertFalse(second['has_more'])
        self.assertEqual([r['id'] for r in first['rows'] + second['rows']], sorted(quotes.ids, reverse=True))
        orders = self.dashboard.get_recent_sales('orders', self.options)
        self.assertEqual([r['id'] for r in orders['rows']], confirmed.ids)
        self.assertEqual(orders['rows'][0]['amount_untaxed'], 500)
        self.assertEqual(orders['rows'][0]['currency'], confirmed.currency_id.name)
        action = self.dashboard.open_recent_sale('orders', self.options, confirmed.id)
        self.assertEqual(action['res_id'], confirmed.id)
        self.assertEqual(action['views'], [(False, 'form')])
        for record in (quotes[0], outside):
            with self.assertRaises(AccessError):
                self.dashboard.open_recent_sale('orders', self.options, record.id)
        with self.assertRaises(ValidationError):
            self.dashboard.get_recent_sales('arbitrary', self.options)
        with self.assertRaises(ValidationError):
            self.dashboard.open_recent_sale('orders', self.options, True)

    def test_paged_groups_never_truncate_headline_or_export(self):
        for index in range(27):
            partner = self.env['res.partner'].create({'name': f'Dashboard customer {index:02}'})
            self._sale(partner=partner, confirmed=True, amount=index + 1)
        self.env.flush_all()
        first = self.dashboard.get_breakdown('confirmed_sales', 'customer', self.options)
        second = self.dashboard.get_breakdown('confirmed_sales', 'customer', self.options, 25)
        self.assertEqual(len(first['rows']), 25)
        self.assertTrue(first['has_more'])
        self.assertEqual(len(second['rows']), 2)
        self.assertFalse(second['has_more'])
        self.assertEqual(sum(r['value'] for r in first['rows'] + second['rows']), 378)
        items = {r['key']: r for r in self.dashboard.get_section('sales', self.options)['items']}
        self.assertEqual(items['confirmed_sales']['value'], 378)
        self.assertEqual(items['orders']['value'], 27)
        export = self.dashboard.export_breakdown('confirmed_sales', 'customer', self.options)
        self.assertEqual(export['row_count'], 27)

    def test_sales_only_user_and_cross_company_record_isolation(self):
        from odoo.exceptions import AccessError
        from odoo.tests import new_test_user
        reader = new_test_user(self.env, login='dashboard_sales_only',
            groups='base.group_user,sales_team.group_sale_salesman,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        mine = self._sale(confirmed=True, amount=75)
        mine.user_id = reader
        other = self._sale(confirmed=True, amount=925)
        other.user_id = self.env.user
        reader.group_ids -= self.env.ref('base.group_allow_export')
        dashboard = self.dashboard.with_user(reader)
        self.env.flush_all()
        self.assertEqual([r['id'] for r in dashboard.get_recent_sales('orders', self.options)['rows']], mine.ids)
        with self.assertRaises(AccessError):
            dashboard.open_recent_sale('orders', self.options, other.id)
        with self.assertRaises(AccessError):
            dashboard.export_breakdown('confirmed_sales', 'customer', self.options)
        foreign = self.env['res.company'].create({'name': 'Dashboard other company'})
        foreign_order = self._sale(company=foreign, amount=400)
        both = self.dashboard.with_context(allowed_company_ids=[self.env.company.id, foreign.id])
        self.assertEqual(both.get_recent_sales('quotations', self.options)['rows'], [])
        foreign_options = dict(self.options, company_id=foreign.id)
        self.assertEqual([r['id'] for r in both.get_recent_sales('quotations', foreign_options)['rows']], foreign_order.ids)
        with self.assertRaises(AccessError):
            both.open_recent_sale('quotations', self.options, foreign_order.id)
        with self.assertRaises(AccessError):
            dashboard.get_recent_sales('quotations', foreign_options)

    def test_hr_native_signed_hours_numeric_fixture(self):
        calendar = self.env['resource.calendar'].create({'name': 'Dashboard four-hour Monday', 'tz': 'UTC',
            'attendance_ids': [Command.clear(), Command.create({'name': 'Monday', 'dayofweek': '0',
                'hour_from': 8, 'hour_to': 12, 'day_period': 'morning'})]})
        employee = self.env['hr.employee'].create({'name': 'Dashboard leave fixture', 'company_id': self.env.company.id})
        employee.version_id.write({'date_version': '2026-01-01', 'resource_calendar_id': calendar.id})
        leave_type = self.env['hr.leave.type'].create({'name': 'Dashboard no-allocation leave',
            'requires_allocation': False, 'leave_validation_type': 'no_validation', 'request_unit': 'day'})
        leave = self.env['hr.leave'].create({'employee_id': employee.id, 'holiday_status_id': leave_type.id,
            'request_date_from': '2026-08-17', 'request_date_to': '2026-08-17'})
        if leave.state != 'validate':
            leave.action_approve()
        self.assertEqual(leave.state, 'validate')
        self.assertEqual(leave.number_of_hours, 4)
        self.env.flush_all()
        groups = self.dashboard.get_breakdown('hr', 'department', self.options)
        self.assertEqual(sum(row['value'] for row in groups['rows']), -4)
        self.assertEqual(self.dashboard.get_trend('hr', self.options)['rows'], [{'label': '2026-08', 'value': -4.0}])
        employee.active = False
        self.env.flush_all()
        self.assertEqual(self.dashboard.get_trend('hr', self.options)['rows'], [])
