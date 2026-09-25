from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged

from .test_sales_crm import SalesCrmCase


@tagged('post_install', '-at_install')
class TestProcurement(SalesCrmCase):

    required = ('purchase.order',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.buyer = new_test_user(
            cls.env, login='ed_purchase_manager', company_id=cls.company.id, company_ids=[cls.company.id],
            groups='executive_dashboard.group_user,purchase.group_purchase_manager')
        cls.plain = new_test_user(cls.env, login='ed_purchase_plain', groups='executive_dashboard.group_user')
        product_vals = {'name': 'Example Board', 'standard_price': 10.0}
        if 'is_storable' in cls.env['product.template']._fields:
            product_vals.update(type='consu', is_storable=True)
        cls.product = cls.env['product.product'].create(product_vals)
        cls.supplier = cls.env['res.partner'].create({'name': 'Example Supplier'})

    def _order(self, qty=5.0, price=40.0, confirm=True):
        order = self.env['purchase.order'].create({
            'partner_id': self.supplier.id,
            'order_line': [fields.Command.create({'product_id': self.product.id, 'product_qty': qty,
                                                  'price_unit': price, 'tax_ids': [fields.Command.clear()]})],
        })
        if confirm:
            order.button_confirm()
        return order

    def test_widget_keys(self):
        result = self.section(self.buyer, 'procurement')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(set(result['widgets']), {'currency', 'kpis', 'approve', 'late', 'suppliers', 'trend'})
        self.assertEqual(len(result['widgets']['trend']), 12)

    def test_purchases_confirmed_match_native_orders(self):
        self._order(qty=5.0, price=40.0)
        self._order(qty=2.0, price=15.0, confirm=False)
        widgets = self.section(self.buyer, 'procurement')['widgets']
        dashboard = self.env['executive.dashboard'].with_user(self.buyer)
        scope = dashboard._period_scope('procurement', 'month')
        start, end = dashboard._utc_bounds(scope['date_from'], scope['date_to'])
        native = self.env['purchase.order'].search([
            ('state', '=', 'purchase'), ('company_id', '=', self.company.id),
            ('date_approve', '>=', start), ('date_approve', '<', end)])
        self.assertEqual(widgets['kpis']['purchases']['count'], len(native))
        same_currency = native.filtered(lambda o: o.currency_id == self.company.currency_id)
        if same_currency == native:
            self.assertAlmostEqual(widgets['kpis']['purchases']['amount'], sum(native.mapped('amount_untaxed')))
        supplier = next(s for s in widgets['suppliers'] if s['id'] == self.supplier.id)
        self.assertAlmostEqual(supplier['amount'], 200.0)
        self.assertAlmostEqual(widgets['trend'][-1]['amount'], widgets['kpis']['purchases']['amount'])

    def test_to_approve_and_open_value(self):
        order = self._order(qty=4.0, price=50.0)
        waiting = self._order(qty=1.0, price=30.0, confirm=False)
        waiting.write({'state': 'to approve'})
        widgets = self.section(self.buyer, 'procurement')['widgets']
        native = self.env['purchase.order'].search_count([('state', '=', 'to approve')])
        self.assertEqual(widgets['kpis']['approve']['count'], native)
        self.assertIn(waiting.id, [row['id'] for row in widgets['approve']['rows']])
        if 'receipt_status' in order._fields:
            before = widgets['kpis']['open']['amount']
            order.order_line.qty_received = 1.0
            after = self.section(self.buyer, 'procurement')['widgets']['kpis']['open']['amount']
            self.assertAlmostEqual(before - after, 50.0)

    def test_drawers(self):
        order = self._order()
        dashboard = self.env['executive.dashboard'].with_user(self.buyer)
        drawer = dashboard.get_drawer('procurement.orders', {'kind': 'purchases', 'period': 'month'})
        self.assertIn(order.name, [row['label'] for row in drawer['rows']])
        drawer = dashboard.get_drawer('procurement.order', {'order_id': order.id})
        self.assertEqual(len(drawer['rows']), 1)
        action = dashboard.open_action('procurement.order', {'order_id': order.id})
        self.assertEqual((action['res_model'], action['res_id']), ('purchase.order', order.id))
        drawer = dashboard.get_drawer('procurement.supplier', {'period': 'month', 'partner_id': self.supplier.id})
        self.assertEqual(drawer['title'], self.supplier.display_name)
        for bad in ({'order_id': '1'}, {'order_id': -1}, {}):
            with self.assertRaises(ValidationError):
                dashboard.get_drawer('procurement.order', bad)
        with self.assertRaises(ValidationError):
            dashboard.get_drawer('procurement.orders', {'kind': 'other'})

    def test_user_without_purchase_rights_is_restricted(self):
        self.assertEqual(self.section(self.plain, 'procurement')['status'], 'restricted')
        with self.assertRaises(AccessError):
            self.env['executive.dashboard'].with_user(self.plain).get_drawer('procurement.orders', {'kind': 'approve'})

    def test_query_limit(self):
        self._order()
        dashboard = self.env['executive.dashboard'].with_user(self.buyer)
        dashboard.get_section('procurement', 'month', refresh=True)
        self.env.invalidate_all()
        with self.assertQueryCount(**{self.env.user.login: 30}):
            dashboard.get_section('procurement', 'month', refresh=True)


@tagged('post_install', '-at_install')
class TestInventory(SalesCrmCase):

    required = ('stock.quant', 'stock.picking')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.keeper = new_test_user(
            cls.env, login='ed_stock_manager', company_id=cls.company.id, company_ids=[cls.company.id],
            groups='executive_dashboard.group_user,stock.group_stock_manager')
        cls.stock_user = new_test_user(
            cls.env, login='ed_stock_user', company_id=cls.company.id, company_ids=[cls.company.id],
            groups='executive_dashboard.group_user,stock.group_stock_user')
        cls.plain = new_test_user(cls.env, login='ed_stock_plain', groups='executive_dashboard.group_user')
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.company.id)], limit=1)
        cls.location = cls.warehouse.lot_stock_id
        cls.category = cls.env['product.category'].create({'name': 'Example Category'})
        Product = cls.env['product.product']
        vals = {'type': 'consu', 'is_storable': True, 'categ_id': cls.category.id} \
            if 'is_storable' in cls.env['product.template']._fields else {'categ_id': cls.category.id}
        cls.positive = Product.create(dict(vals, name='Example Paint', default_code='EXPAINT'))
        cls.zero = Product.create(dict(vals, name='Example Primer', default_code='EXPRIMER'))
        cls.negative = Product.create(dict(vals, name='Example Brush', default_code='EXBRUSH'))
        Quant = cls.env['stock.quant']
        Quant._update_available_quantity(cls.positive, cls.location, 12.0)
        Quant._update_available_quantity(cls.zero, cls.location, 3.0)
        Quant._update_available_quantity(cls.zero, cls.location, -3.0)
        Quant._update_available_quantity(cls.negative, cls.location, -4.0)
        cls.out_type = cls.warehouse.out_type_id

    def stock(self, user, **args):
        return self.env['executive.dashboard'].with_user(user).get_drawer('inventory.stock', args)

    def test_widget_keys(self):
        result = self.section(self.keeper, 'inventory')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(set(result['widgets']), {'currency', 'kpis', 'deliveries', 'receipts', 'stock'})
        self.assertEqual(result['period']['key'], 'now')

    def test_stock_report_filters_run_on_the_server(self):
        codes = lambda data: {row['code'] for row in data['rows']}  # noqa: E731
        hidden = self.stock(self.keeper, category_id=self.category.id)
        self.assertEqual(codes(hidden), {'EXPAINT'})
        self.assertEqual(hidden['count'], 1)
        shown = self.stock(self.keeper, category_id=self.category.id, hide=False)
        self.assertEqual(codes(shown), {'EXPAINT', 'EXPRIMER', 'EXBRUSH'})
        brush = next(row for row in shown['rows'] if row['code'] == 'EXBRUSH')
        self.assertEqual(brush['on_hand'], -4.0)
        self.assertEqual(codes(self.stock(self.keeper, query='expaint', hide=False)), {'EXPAINT'})
        self.assertEqual(codes(self.stock(self.keeper, query='Example Pri', hide=False)), {'EXPRIMER'})
        other = self.env['stock.warehouse'].create({'name': 'Example Second', 'code': 'EX2',
                                                     'company_id': self.company.id})
        self.assertEqual(self.stock(self.keeper, warehouse_id=other.id, hide=False)['count'], 0)
        mine = self.stock(self.keeper, warehouse_id=self.warehouse.id, category_id=self.category.id)
        self.assertEqual(codes(mine), {'EXPAINT'})
        paint = mine['rows'][0]
        native = sum(self.env['stock.quant'].search([
            ('product_id', '=', self.positive.id), ('location_id.usage', '=', 'internal')]).mapped('quantity'))
        self.assertEqual(paint['on_hand'], native)

    def test_stock_report_pages(self):
        first = self.stock(self.keeper, hide=False)
        per = first['per']
        self.assertLessEqual(len(first['rows']), per)
        pages = -(-first['count'] // per)
        seen = []
        for page in range(pages):
            seen += [(r['product_id'], r['warehouse_id']) for r in self.stock(self.keeper, hide=False, page=page)['rows']]
        self.assertEqual(len(seen), first['count'])
        self.assertEqual(len(set(seen)), first['count'])
        last = self.stock(self.keeper, hide=False, page=pages + 5)
        self.assertEqual(last['page'], max(pages - 1, 0))
        for bad in ({'page': -1}, {'page': '1'}, {'hide': 'yes'}, {'warehouse_id': 'x'}, {'query': 5}):
            with self.assertRaises(ValidationError):
                self.stock(self.keeper, **bad)

    def test_value_only_for_inventory_administrators(self):
        if 'value' not in self.env['stock.quant']._fields:
            self.skipTest('stock_account not installed')
        manager = self.section(self.keeper, 'inventory')['widgets']
        self.assertIsNotNone(manager['kpis']['value'])
        self.assertTrue(manager['stock']['valued'])
        user = self.section(self.stock_user, 'inventory')['widgets']
        self.assertIsNone(user['kpis']['value'])
        self.assertFalse(user['stock']['valued'])
        self.assertIsNone(user['stock']['rows'][0]['value'] if user['stock']['rows'] else None)

    def test_picking_tiles_match_native_filters(self):
        Picking = self.env['stock.picking']
        late = Picking.create({'picking_type_id': self.out_type.id, 'partner_id': self.partner.id,
                               'scheduled_date': fields.Datetime.now() - timedelta(days=3),
                               'move_ids': [fields.Command.create({
                                   'product_id': self.positive.id, 'product_uom_qty': 1.0,
                                   'location_id': self.location.id,
                                   'location_dest_id': self.env.ref('stock.stock_location_customers').id})]})
        late.action_confirm()
        widgets = self.section(self.keeper, 'inventory')['widgets']
        today = fields.Date.context_today(self.env['executive.dashboard'].with_user(self.keeper))
        start, _end = self.env['executive.dashboard'].with_user(self.keeper)._utc_bounds(today, today)
        native_late = Picking.search_count([
            ('picking_type_code', '=', 'outgoing'), ('state', 'in', ('assigned', 'waiting', 'confirmed')),
            ('scheduled_date', '<', start), ('company_id', '=', self.company.id)])
        native_waiting = Picking.search_count([
            ('picking_type_code', '=', 'outgoing'), ('state', 'in', ('confirmed', 'waiting')),
            ('company_id', '=', self.company.id)])
        self.assertEqual(widgets['deliveries']['late'], native_late)
        self.assertEqual(widgets['kpis']['late']['count'], native_late)
        self.assertEqual(widgets['deliveries']['waiting'], native_waiting)
        self.assertGreaterEqual(widgets['kpis']['late']['oldest'], 3)
        dashboard = self.env['executive.dashboard'].with_user(self.keeper)
        drawer = dashboard.get_drawer('inventory.pickings', {'code': 'outgoing', 'bucket': 'late'})
        self.assertIn(late.name, [row['label'] for row in drawer['rows']])
        drawer = dashboard.get_drawer('inventory.picking', {'picking_id': late.id})
        self.assertEqual(len(drawer['rows']), 1)
        action = dashboard.open_action('inventory.pickings', {'code': 'outgoing', 'bucket': 'late'})
        self.assertEqual(Picking.search_count(action['domain']), native_late)
        with self.assertRaises(ValidationError):
            dashboard.get_drawer('inventory.pickings', {'code': 'internal', 'bucket': 'late'})

    def test_product_drawer_and_open_in_odoo(self):
        dashboard = self.env['executive.dashboard'].with_user(self.keeper)
        drawer = dashboard.get_drawer('inventory.product', {'product_id': self.positive.id})
        self.assertEqual(len(drawer['rows']), 1)
        action = dashboard.open_action('inventory.stock', {'query': 'EXPAINT'})
        self.assertEqual(action['res_model'], 'stock.quant')
        self.assertEqual(self.env['stock.quant'].search(action['domain']).product_id, self.positive)

    def test_user_without_stock_rights_is_restricted(self):
        self.assertEqual(self.section(self.plain, 'inventory')['status'], 'restricted')
        with self.assertRaises(AccessError):
            self.stock(self.plain)

    def test_query_limit(self):
        dashboard = self.env['executive.dashboard'].with_user(self.keeper)
        dashboard.get_section('inventory', 'month', refresh=True)
        self.env.invalidate_all()
        # About 35 of them are Odoo's own valuation (stock.quant.value) for the value figures.
        with self.assertQueryCount(**{self.env.user.login: 65}):
            dashboard.get_section('inventory', 'month', refresh=True)
