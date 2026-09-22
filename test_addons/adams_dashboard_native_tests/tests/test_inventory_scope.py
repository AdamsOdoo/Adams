"""Native B01/B05 regressions; must run with stock_account installed."""
from lxml import etree

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestDashboardInventoryScope(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('stock.group_stock_manager')
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.location = cls.warehouse.lot_stock_id
        cls.product = cls.env['product.product'].create({'name': 'Scope regression stock', 'is_storable': True})

    def test_location_action_removes_value_columns_without_contaminating_native_view(self):
        self.env['stock.quant']._update_available_quantity(self.product, self.location, 12)
        action = self.dashboard.open_inventory_location(self.options, self.product.id, self.location.id)
        product = self.product.with_context(action['context'])
        view_id = self.env.ref('stock.product_product_stock_tree').id
        view_context = {key: value for key, value in action['context'].items()
                        if key == 'lang' or key.endswith('_view_ref')}
        product_view = self.product.with_context(view_context)
        quantity_view = etree.fromstring(product_view.get_view(view_id, 'list')['arch'])
        self.assertFalse(quantity_view.xpath("//field[@name='total_value' or @name='avg_cost']"))
        self.assertTrue(quantity_view.xpath("//field[@name='qty_available']"))
        self.assertEqual(product.qty_available, 12)
        native_view = etree.fromstring(self.product.get_view(view_id, 'list')['arch'])
        self.assertTrue(native_view.xpath("//field[@name='total_value']"))
        # Inverse call order also must not leak the cached native architecture.
        quantity_again = etree.fromstring(product.get_view(view_id, 'list')['arch'])
        self.assertFalse(quantity_again.xpath("//field[@name='total_value']"))

    def test_valuation_scope_discards_location_and_validates_warehouse(self):
        dashboard = self.dashboard.with_context(location=self.location.id, strict=True, to_date='2000-01-01')
        action = dashboard.open_inventory_valuation(self.options, filters={'warehouse_id': self.warehouse.id}, product_id=self.product.id)
        self.assertEqual(action['context']['warehouse_id'], self.warehouse.id)
        self.assertNotIn('location', action['context'])
        self.assertNotIn('strict', action['context'])
        self.assertNotIn('to_date', action['context'])
        self.assertNotIn('adams_dashboard_quantity_view_ref', action['context'])
        company_action = dashboard.open_inventory_valuation(self.options)
        self.assertNotIn('warehouse_id', company_action['context'])
        with self.assertRaises(AccessError):
            dashboard.open_inventory_valuation(self.options, filters={'warehouse_id': 2147483647})
        with self.assertRaises(ValidationError):
            dashboard.open_inventory_valuation(self.options, product_id=True)

    def test_location_rows_reconcile_native_zero_negative_and_child_quantities(self):
        child = self.env['stock.location'].create({'name': 'Child stock', 'usage': 'internal',
            'location_id': self.location.id, 'company_id': self.env.company.id})
        self.env['stock.quant']._update_available_quantity(self.product, self.location, -2)
        self.env['stock.quant']._update_available_quantity(self.product, child, 12)
        for hide_zero, hide_negative in ((False, False), (True, False), (False, True), (True, True)):
            filters = {'location_id': self.location.id, 'search': self.product.name,
                       'hide_zero': hide_zero, 'hide_negative': hide_negative}
            result = self.dashboard.get_inventory(self.options, filters=filters)
            native = self.product.with_context(location=self.location.id, strict=True).qty_available
            self.assertEqual(native, -2)
            self.assertEqual(result['total_count'], 0 if hide_negative else 1)
            if result['rows']:
                self.assertEqual(result['rows'][0]['qty_available'], native)

    def test_new_valuation_rpc_preserves_dashboard_and_stock_access(self):
        reader = new_test_user(self.env, login='inventory_scope_reader',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_inventory_valuation(self.options)

    def test_global_quantity_sort_spans_locations_pages_and_recovers_shrunken_page(self):
        child = self.env['stock.location'].create({'name': 'Sort child', 'usage': 'internal',
            'location_id': self.location.id, 'company_id': self.env.company.id})
        products = self.env['product.product'].create([
            {'name': f'Dashboard sorting fixture {index:02}', 'is_storable': True}
            for index in range(26)])
        for index, product in enumerate(products):
            self.env['stock.quant']._update_available_quantity(product, self.location, index + 1)
        self.env['stock.quant']._update_available_quantity(products[0], child, 1000)
        self.env.flush_all()
        filters = {'warehouse_id': self.warehouse.id, 'search': 'Dashboard sorting fixture',
                   'hide_zero': True, 'sort': 'qty'}
        first = self.dashboard.get_inventory(self.options, filters=filters)
        second = self.dashboard.get_inventory(self.options, offset=25, filters=filters)
        self.assertEqual(first['total_count'], 27)
        self.assertEqual(first['rows'][0]['location_id'], child.id)
        self.assertEqual(first['rows'][0]['product_id'], products[0].id)
        actual = first['rows'] + second['rows']
        self.assertEqual([row['qty_available'] for row in actual], [1000] + list(range(26, 0, -1)))
        for row in actual:
            native = products.browse(row['product_id']).with_context(location=row['location_id'], strict=True)
            self.assertEqual(row['qty_available'], native.qty_available)
        names = self.dashboard.get_inventory(self.options, filters=dict(filters, sort='name'))
        self.assertEqual([row['product_id'] for row in names['rows'][:2]], [products[0].id, products[0].id])
        # A removed final page returns the last valid page, including its offset.
        for product in products[1:]:
            self.env['stock.quant']._update_available_quantity(product, self.location,
                -product.with_context(location=self.location.id, strict=True).qty_available)
        recovered = self.dashboard.get_inventory(self.options, offset=25, filters=filters)
        self.assertEqual(recovered['offset'], 0)
        self.assertEqual(recovered['total_count'], 2)
        self.assertEqual(len(recovered['rows']), 2)
        with self.assertRaises(ValidationError):
            self.dashboard.get_inventory(self.options, filters=dict(filters, sort='standard_price'))

    def test_global_stock_sources_use_allowed_models_scope_and_permissions(self):
        for route, model in [('history', 'stock.move.line'), ('replenishment', 'stock.warehouse.orderpoint')]:
            action = self.dashboard.open_inventory_source(self.options, route, {'warehouse_id': self.warehouse.id})
            self.assertEqual(action['res_model'], model)
            self.assertIn(('company_id', '=', self.env.company.id), action['domain'])
            self.assertIn(('location_id', 'in', self.env['stock.location'].search([
                ('usage', '=', 'internal'), ('company_id', 'in', [False, self.env.company.id]),
                ('id', 'child_of', self.warehouse.view_location_id.id)], order='complete_name, id').ids), action['domain'])
        with self.assertRaises(ValidationError):
            self.dashboard.open_inventory_source(self.options, 'forecast')
        reader = new_test_user(self.env, login='global_stock_source_reader',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_inventory_source(self.options, 'replenishment')
