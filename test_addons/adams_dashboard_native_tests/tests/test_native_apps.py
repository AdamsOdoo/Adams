from odoo import Command
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestDashboardNativeApps(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
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
        groups = self.dashboard.get_breakdown('crm', 'stage', self.options)
        self.assertAlmostEqual(sum(row['value'] for row in groups['rows']), 250)
        opportunity.action_set_won_rainbowman()
        self.assertEqual(self.dashboard.get_trend('crm', self.options)['rows'], [])

    def test_current_stock_uses_native_product_quantity(self):
        product = self.env['product.product'].create({'name': 'Dashboard stock fixture', 'is_storable': True})
        location = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1).lot_stock_id
        self.env['stock.quant']._update_available_quantity(product, location, 12)
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
