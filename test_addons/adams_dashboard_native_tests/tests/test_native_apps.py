import csv
import io

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
        self.env.flush_all()
        quotation = next(r for r in self.dashboard.get_section('sales', self.options)['items'] if r['key'] == 'quotations')
        self.assertEqual(quotation['value'], 378)
        orders = self.dashboard.get_recent_sales('orders', self.options)
        self.assertEqual([r['id'] for r in orders['rows']], confirmed.ids)
        self.assertEqual(orders['rows'][0]['amount_untaxed'], 500)
        self.assertEqual(orders['rows'][0]['currency'], confirmed.currency_id.name)
        self.assertEqual(orders['rows'][0]['user_id'][0], confirmed.user_id.id)
        self.assertIn('delivery_label', orders['rows'][0])
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
        rows = list(csv.DictReader(io.StringIO(export['content'].lstrip('\ufeff'))))
        self.assertEqual(len(rows), 27)
        self.assertTrue(export['generated_at'])
        self.assertEqual({row['Last updated UTC'] for row in rows}, {export['generated_at']})
        self.assertEqual({row['Scope fingerprint'] for row in rows}, {export['provenance']['fingerprint']})
        self.assertEqual({row['Definition'] for row in rows}, {'v4'})

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

    def test_fulfillment_reuses_signed_native_product_quantities(self):
        product = self.env['product.product'].create({'name': 'Dashboard delivery service', 'type': 'service'})
        order = self.env['sale.order'].create({'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': product.id, 'product_uom_qty': 5,
                                          'price_unit': 10, 'tax_ids': [Command.clear()]})]})
        order.action_confirm()
        order.date_order = '2026-08-15 12:00:00'
        order.order_line.qty_delivered = 2
        self.env.flush_all()
        result = self.dashboard.get_fulfillment(self.options)
        row = result['rows'][0]
        self.assertEqual((row['ordered'], row['delivered'], row['remaining']), (5, 2, 3))
        self.assertEqual(row['unit'], product.uom_id.display_name)
        action = self.dashboard.open_fulfillment(self.options)
        self.assertEqual(action['domain'], result['provenance']['domain'])
        self.assertEqual(action['context']['pivot_measures'], ['product_uom_qty', 'qty_delivered', 'qty_to_deliver'])
        self.assertEqual(sum(self.env['sale.report'].search(action['domain']).mapped('qty_to_deliver')), 3)
        order.order_line.qty_delivered = 7
        self.env.flush_all()
        self.assertEqual(self.dashboard.get_fulfillment(self.options)['rows'][0]['remaining'], -2)

    def test_historical_stock_native_value_routes_and_scope(self):
        from odoo.exceptions import AccessError, ValidationError
        product = self.env['product.product'].create({
            'name': 'Dated stock fixture', 'is_storable': True, 'standard_price': 10,
            'company_id': self.env.company.id,
        })
        stock = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        supplier = self.env.ref('stock.stock_location_suppliers')
        customer = self.env.ref('stock.stock_location_customers')
        for quantity, source, dest, day in [(12, supplier, stock, '2026-08-10 12:00:00'),
                                            (4, stock, customer, '2026-09-10 12:00:00')]:
            move = self.env['stock.move'].create({
                'product_id': product.id,
                'product_uom_qty': quantity, 'product_uom': product.uom_id.id,
                'location_id': source.id, 'location_dest_id': dest.id,
                'company_id': self.env.company.id,
            })
            move._action_confirm()
            move.quantity = quantity
            move.picked = True
            move._action_done()
            move.date = day
            move.move_line_ids.date = day
        self.env.flush_all()
        def row(mode):
            offset = 0
            while True:
                page = self.dashboard.get_inventory(self.options, offset, mode)
                found = next((r for r in page['rows'] if r['id'] == product.id), None)
                if found:
                    return found, page
                self.assertTrue(page['has_more'])
                offset += 25
        current, _ = row('current')
        past, page = row('historical')
        self.assertEqual(current['qty_available'], 8)
        self.assertEqual(past['qty_available'], 12)
        location_page = self.dashboard.get_inventory(self.options, 0, 'historical', {'location_id': stock.id, 'search': product.name, 'at_date': '2026-08-31', 'hide_zero': True})
        self.assertEqual(location_page['rows'][0]['qty_available'], 12)
        self.assertNotIn('free_qty', location_page['rows'][0])
        self.assertEqual(location_page['as_of'], '2026-08-31')
        self.assertEqual(past['total_value'], 120)
        self.assertNotIn('free_qty', past)
        self.assertNotIn('virtual_available', past)
        self.assertEqual(page['value_status'], 'ready')
        action = self.dashboard.open_inventory(self.options, 'historical')
        native = product.with_context(action['context'])
        self.assertEqual(native.qty_available, 12)
        self.assertEqual(native.total_value, 120)
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
        for route in ('forecast', 'history', 'locations', 'replenishment'):
            action = self.dashboard.open_inventory_product(self.options, product.id, route)
            self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
        product.active = False
        self.assertEqual(row('historical')[0]['qty_available'], 12)
        with self.assertRaises(ValidationError):
            self.dashboard.open_inventory_product(self.options, True, 'forecast')
        with self.assertRaises(ValidationError):
            self.dashboard.get_inventory(self.options, 0, 'invented')
        other_company = self.env['res.company'].create({'name': 'Other inventory company'})
        foreign = self.env['product.product'].with_company(other_company).create({
            'name': 'Other company product', 'is_storable': True,
            'company_id': other_company.id,
        })
        with self.assertRaises(AccessError):
            self.dashboard.open_inventory_product(self.options, foreign.id, 'forecast')

    def test_workforce_current_native_departments_and_restrictions(self):
        from odoo.exceptions import AccessError
        from odoo.tests import new_test_user
        self.env.user.group_ids |= self.env.ref('hr.group_hr_manager')
        department = self.env['hr.department'].create({'name': 'Dashboard workforce', 'company_id': self.env.company.id})
        employees = self.env['hr.employee'].create([
            {'name': 'Workforce one', 'company_id': self.env.company.id, 'department_id': department.id},
            {'name': 'Workforce two', 'company_id': self.env.company.id, 'department_id': department.id},
            {'name': 'Former workforce', 'company_id': self.env.company.id, 'department_id': department.id, 'active': False},
        ])
        page = self.dashboard.get_workforce(self.options)
        row = next(r for r in page['rows'] if r['id'] == department.id)
        self.assertEqual(row['count'], 2)
        self.assertEqual(set(row), {'id', 'name', 'count'})
        action = self.dashboard.open_workforce(self.options, department.id)
        self.assertEqual(self.env['hr.employee'].search(action['domain']), employees[:2])
        self.assertEqual(page['date_basis'], 'current')
        reader = new_test_user(self.env, login='dashboard_ops_restricted',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user')
        for method, args in [('get_workforce', [self.options]), ('open_workforce', [self.options]),
                             ('get_inventory', [self.options]),
                             ('open_inventory_product', [self.options, self.product_a.id, 'forecast'])]:
            with self.assertRaises(AccessError):
                getattr(self.dashboard.with_user(reader), method)(*args)

    def test_native_commercial_margin_uses_current_cost_not_accounting_profit(self):
        product = self.env['product.product'].create({'name': 'Commercial margin fixture', 'standard_price': 30})
        for move_type, quantity in [('out_invoice', 2), ('out_refund', 1)]:
            self.env['account.move'].create({
                'move_type': move_type, 'partner_id': self.partner_a.id,
                'invoice_date': '2026-08-15', 'date': '2026-08-15',
                'journal_id': self.company_data['default_journal_sale'].id,
                'invoice_line_ids': [Command.create({'product_id': product.id, 'quantity': quantity,
                    'price_unit': 100, 'account_id': self.company_data['default_account_revenue'].id,
                    'tax_ids': [Command.clear()]})],
            }).action_post()
        self.env.flush_all()
        def margin():
            return next(item for item in self.dashboard.get_section('sales', self.options)['items'] if item['key'] == 'invoiced_margin')['value']
        self.assertEqual(margin(), 70)
        product.standard_price = 40
        self.env.flush_all()
        self.assertEqual(margin(), 60)
        action = self.dashboard.open_report('invoiced_margin', self.options)
        self.assertEqual(action['context']['pivot_measures'], ['price_margin'])
        self.assertEqual(self.dashboard.get_breakdown('invoiced_margin', 'product', self.options)['rows'][0]['value'], 60)

    def test_native_purchase_current_worklists_do_not_approve(self):
        from odoo.exceptions import AccessError
        from odoo import fields
        from datetime import timedelta
        planned = fields.Datetime.now() - timedelta(days=5)
        order = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.product_a.id, 'product_qty': 2,
                'price_unit': 50, 'date_planned': planned, 'tax_ids': [Command.clear()]})],
        })
        order.state = 'to approve'
        approval = self.dashboard.get_procurement(self.options, kind='approvals')
        self.assertIn(order.id, [row['id'] for row in approval['rows']])
        self.dashboard.open_procurement(self.options, 'approvals', order.id)
        self.assertEqual(order.state, 'to approve')
        order.button_approve()
        order.order_line.date_planned = planned
        self.env.flush_all()
        late = self.dashboard.get_procurement(self.options, kind='late')
        self.assertIn(order.id, [row['id'] for row in late['rows']])
        action = self.dashboard.open_procurement(self.options, 'late', order.id)
        self.assertEqual(action['res_id'], order.id)
        with self.assertRaises(AccessError):
            self.dashboard.open_procurement(self.options, 'approvals', order.id)
        order.order_line.qty_received = 2
        self.env.flush_all()
        self.assertNotIn(order.id, [row['id'] for row in self.dashboard.get_procurement(self.options, kind='late')['rows']])

    def test_location_stock_filters_pages_and_source_scope(self):
        from odoo.exceptions import AccessError, ValidationError
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        parent = warehouse.lot_stock_id
        child = self.env['stock.location'].create({'name': 'Dashboard shelf', 'usage': 'internal',
            'location_id': parent.id, 'company_id': self.env.company.id})
        category = self.env['product.category'].create({'name': 'Dashboard location category'})
        products = self.env['product.product'].create([{'name': f'Location fixture {i:02}', 'is_storable': True,
            'categ_id': category.id} for i in range(27)])
        for product in products:
            self.env['stock.quant']._update_available_quantity(product, parent, 10)
        self.env['stock.quant']._update_available_quantity(products[0], child, -3)
        self.env.flush_all()
        filters = {'warehouse_id': warehouse.id, 'category_id': category.id, 'hide_zero': True, 'hide_negative': False}
        first = self.dashboard.get_inventory(self.options, 0, 'current', filters)
        second = self.dashboard.get_inventory(self.options, 25, 'current', filters)
        rows = first['rows'] + second['rows']
        self.assertEqual(first['total_count'], 28)
        self.assertEqual(len(first['rows']), 25)
        self.assertEqual(len(second['rows']), 3)
        self.assertFalse(second['has_more'])
        quantities = {(r['product_id'], r['location_id']): r['qty_available'] for r in rows}
        self.assertEqual(quantities[products[0].id, parent.id], 10)
        self.assertEqual(quantities[products[0].id, child.id], -3)
        positive = self.dashboard.get_inventory(self.options, 0, 'current', dict(filters, hide_negative=True))
        self.assertEqual(positive['total_count'], 27)
        zeros = self.dashboard.get_inventory(self.options, 0, 'current', dict(filters, location_id=child.id, hide_zero=False, hide_negative=True))
        self.assertEqual(zeros['total_count'], 26)
        self.assertTrue(all(row['qty_available'] == 0 for row in zeros['rows']))
        action = self.dashboard.open_inventory_location(self.options, products[0].id, child.id, 'current', filters)
        self.assertEqual(action['context']['location'], child.id)
        self.assertTrue(action['context']['strict'])
        self.assertEqual(action['context']['allowed_company_ids'], [self.env.company.id])
        self.assertEqual(self.env['product.product'].with_context(action['context']).search(action['domain']), products[0])
        with self.assertRaises(AccessError):
            self.dashboard.open_inventory_location(self.options, products[0].id, child.id, 'current', dict(filters, hide_negative=True))
        for invalid in ({'warehouse_id': True}, {'hide_zero': 'yes'}, {'domain': []}, {'location_id': -1}):
            with self.assertRaises(ValidationError):
                self.dashboard.get_inventory(self.options, 0, 'current', invalid)

    def test_fulfillment_row_action_preserves_product_unit_and_native_measures(self):
        from odoo.exceptions import AccessError, ValidationError
        products = self.env['product.product'].create([
            {'name': 'Delivery row first', 'type': 'service'},
            {'name': 'Delivery row second', 'type': 'service'}])
        order = self.env['sale.order'].create({'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': product.id, 'product_uom_qty': 5,
                                          'price_unit': 10, 'tax_ids': [Command.clear()]})
                           for product in products]})
        order.action_confirm()
        order.date_order = '2026-08-15 12:00:00'
        order.order_line[0].qty_delivered = 7
        self.env.flush_all()
        rows = self.dashboard.get_fulfillment(self.options)['rows']
        row = next(item for item in rows if item['id'] == products[0].id)
        action = self.dashboard.open_fulfillment(self.options, row['id'], row['unit_id'])
        source = self.env['sale.report'].search(action['domain'])
        self.assertEqual(source.product_id, products[0])
        self.assertEqual(source.product_uom_id.id, row['unit_id'])
        for field, key in [('product_uom_qty', 'ordered'), ('qty_delivered', 'delivered'), ('qty_to_deliver', 'remaining')]:
            self.assertEqual(sum(source.mapped(field)), row[key])
        self.assertEqual(row['remaining'], -2)
        self.assertEqual(action['context']['pivot_measures'], ['product_uom_qty', 'qty_delivered', 'qty_to_deliver'])
        with self.assertRaises(ValidationError):
            self.dashboard.open_fulfillment(self.options, row['id'])
        with self.assertRaises(AccessError):
            self.dashboard.open_fulfillment(self.options, row['id'], 2147483647)
