from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged

from odoo.addons.executive_dashboard.models import dashboard as dashboard_module


class SalesCrmCase(TransactionCase):
    """Runs only when the app under test is installed (the module depends on web + account)."""

    required = ()

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        missing = [name for name in cls.required if name not in cls.env]
        if missing:
            cls.skipTest(cls, '%s not installed' % ', '.join(missing))
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({'name': 'Example Customer'})

    def setUp(self):
        super().setUp()
        dashboard_module.cache_clear()

    def section(self, user, key, period='month'):
        dashboard_module.cache_clear()
        return self.env['executive.dashboard'].with_user(user).get_section(key, period)


@tagged('post_install', '-at_install')
class TestSales(SalesCrmCase):

    required = ('sale.order',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env, login='ed_sales_manager', company_id=cls.company.id, company_ids=[cls.company.id],
            groups='executive_dashboard.group_user,sales_team.group_sale_manager,account.group_account_readonly')
        cls.salesman = new_test_user(
            cls.env, login='ed_salesman', company_id=cls.company.id, company_ids=[cls.company.id],
            groups='executive_dashboard.group_user,sales_team.group_sale_salesman')
        cls.plain = new_test_user(cls.env, login='ed_sales_plain', groups='executive_dashboard.group_user')
        product_vals = {'name': 'Example Tile', 'list_price': 100.0, 'invoice_policy': 'order'}
        if 'is_storable' in cls.env['product.template']._fields:
            product_vals.update(type='consu', is_storable=True)
        cls.product = cls.env['product.product'].create(product_vals)
        cls.today = fields.Date.context_today(cls.env['executive.dashboard'].with_user(cls.manager))

    def _order(self, qty=3.0, confirm=True):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'order_line': [fields.Command.create({'product_id': self.product.id, 'product_uom_qty': qty,
                                                  'price_unit': 100.0, 'tax_ids': [fields.Command.clear()]})],
        })
        if confirm:
            order.action_confirm()
        return order

    def _invoice(self, move_type, amount, qty=1.0):
        move = self.env['account.move'].create({
            'move_type': move_type, 'partner_id': self.partner.id,
            'invoice_date': self.today, 'date': self.today,
            'invoice_user_id': self.manager.id,
            'invoice_line_ids': [fields.Command.create({
                'product_id': self.product.id, 'quantity': qty, 'price_unit': amount,
                'tax_ids': [fields.Command.clear()]})],
        })
        move.action_post()
        return move

    def test_widget_keys(self):
        result = self.section(self.manager, 'sales')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(set(result['widgets']),
                         {'currency', 'kpis', 'trend', 'salespeople', 'products', 'customers', 'orders'})
        self.assertEqual(set(result['widgets']['kpis']), {'invoiced', 'orders', 'quotations', 'to_invoice'})
        self.assertEqual(len(result['widgets']['trend']['months']), 12)

    def test_invoiced_sales_match_posted_invoices(self):
        self._invoice('out_invoice', 1000.0, qty=4)
        self._invoice('out_refund', 250.0, qty=1)
        widgets = self.section(self.manager, 'sales')['widgets']
        # Native figures: the same posted customer invoices and credit notes, untaxed, signed.
        moves = self.env['account.move'].search([
            ('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted'),
            ('company_id', '=', self.company.id),
            ('date', '>=', self.today.replace(day=1)), ('date', '<=', self.today)])
        currency = self.company.currency_id
        self.assertTrue(currency.is_zero(widgets['kpis']['invoiced']['amount'] - sum(moves.mapped('amount_untaxed_signed'))))
        self.assertEqual(widgets['kpis']['invoiced']['count'], len(moves.filtered(lambda m: m.move_type == 'out_invoice')))
        self.assertTrue(currency.is_zero(widgets['trend']['months'][-1]['amount'] - widgets['kpis']['invoiced']['amount']))
        for person in widgets['salespeople']:
            own = moves.filtered(lambda m: m.invoice_user_id.id == person['id'])
            self.assertTrue(currency.is_zero(person['amount'] - sum(own.mapped('amount_untaxed_signed'))), person)
            self.assertEqual(person['count'], len(own))
        product = next(p for p in widgets['products'] if p['product_id'] == self.product.id)
        self.assertEqual(product['quantity'], 3.0)
        self.assertEqual(product['uom_id'], self.product.uom_id.id)

    def test_orders_match_native_counts(self):
        order = self._order()
        self._order(confirm=False)
        kpis = self.section(self.manager, 'sales')['widgets']['kpis']
        SaleOrder = self.env['sale.order']
        start, end = self.env['executive.dashboard'].with_user(self.manager)._utc_bounds(self.today.replace(day=1), self.today)
        self.assertEqual(kpis['orders']['count'], SaleOrder.search_count(
            [('state', '=', 'sale'), ('date_order', '>=', start), ('date_order', '<', end)]))
        self.assertEqual(kpis['quotations']['count'], SaleOrder.search_count([('state', 'in', ('draft', 'sent'))]))
        self.assertEqual(kpis['to_invoice']['count'], SaleOrder.search_count([('invoice_status', '=', 'to invoice')]))
        self.assertEqual(order.invoice_status, 'to invoice')
        self.assertGreaterEqual(kpis['to_invoice']['amount'], 300.0)

    def test_recent_orders_show_native_delivery_status(self):
        order = self._order()
        widgets = self.section(self.manager, 'sales')['widgets']
        row = next(r for r in widgets['orders']['rows'] if r['id'] == order.id)
        Dashboard = self.env['executive.dashboard'].with_user(self.manager)
        if 'delivery_status' not in order._fields:
            self.assertFalse(widgets['orders']['delivery'])
            self.assertFalse(row['delivery_status'])
            return
        self.assertTrue(widgets['orders']['delivery'])
        self.assertEqual(row['delivery_status'], order.delivery_status)
        labels = dict(order._fields['delivery_status']._description_selection(self.env))
        self.assertEqual(row['delivery_label'], labels[order.delivery_status])
        # The drawer lists the order's delivery orders; Open in Odoo opens them.
        drawer = Dashboard.get_drawer('sales.order', {'order_id': order.id})
        self.assertEqual(drawer['delivery_status'], order.delivery_status)
        self.assertEqual([r['label'] for r in drawer['rows']], order.picking_ids.sorted('scheduled_date').mapped('name'))
        action = Dashboard.open_action('sales.order', {'order_id': order.id})
        self.assertEqual(action['res_model'], 'stock.picking')
        self.assertEqual(action['domain'], [('id', 'in', order.picking_ids.ids)])

    def test_drawers(self):
        self._invoice('out_invoice', 500.0)
        order = self._order()
        Dashboard = self.env['executive.dashboard'].with_user(self.manager)
        args = {'period': 'month'}
        self.assertTrue(Dashboard.get_drawer('sales.invoices', args)['rows'])
        self.assertEqual(Dashboard.open_action('sales.invoices', args)['res_model'], 'account.move')
        drawer = Dashboard.get_drawer('sales.orders', dict(args, kind='orders'))
        self.assertIn(order.name, [r['label'] for r in drawer['rows']])
        self.assertEqual(Dashboard.open_action('sales.orders', dict(args, kind='to_invoice'))['res_model'], 'sale.order')
        self.assertTrue(Dashboard.get_drawer('sales.salesperson', dict(args, user_id=self.manager.id))['rows'])
        self.assertTrue(Dashboard.get_drawer('sales.product', dict(args, product_id=self.product.id,
                                                                   uom_id=self.product.uom_id.id))['rows'])

    def test_drawer_arguments_are_validated(self):
        Dashboard = self.env['executive.dashboard'].with_user(self.manager)
        for key, args in [('sales.order', {'order_id': 'x'}), ('sales.order', {'order_id': 0}),
                          ('sales.order', {'order_id': 10 ** 9}), ('sales.orders', {'kind': 'other'}),
                          ('sales.customer', {'partner_id': None}), ('sales.product', {'product_id': 1})]:
            with self.assertRaises(ValidationError, msg=key):
                Dashboard.get_drawer(key, args)

    def test_salesman_sees_own_documents_only(self):
        mine = self._order()
        mine.user_id = self.salesman
        other = self._order()
        other.user_id = self.manager
        widgets = self.section(self.salesman, 'sales')['widgets']
        ids = [r['id'] for r in widgets['orders']['rows']]
        self.assertIn(mine.id, ids)
        self.assertNotIn(other.id, ids)
        # No accounting rights: payments are not readable, so that widget is left out.
        self.assertIsNone(widgets['customers'])
        self.assertIsNotNone(widgets['kpis']['invoiced'])
        with self.assertRaises(AccessError):
            self.env['executive.dashboard'].with_user(self.salesman).get_drawer('sales.order', {'order_id': other.id})

    def test_user_without_sales_rights_is_restricted(self):
        self.assertEqual(self.section(self.plain, 'sales')['status'], 'restricted')

    def test_query_limit(self):
        self._invoice('out_invoice', 100.0)
        self._order()
        self.section(self.manager, 'sales')  # warm the ORM caches (fields, rules)
        dashboard_module.cache_clear()
        self.env.invalidate_all()
        with self.assertQueryCount(**{self.env.user.login: 35}):
            self.env['executive.dashboard'].with_user(self.manager).get_section('sales', 'month')


@tagged('post_install', '-at_install')
class TestCrm(SalesCrmCase):

    required = ('crm.lead',)

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.manager = new_test_user(
            cls.env, login='ed_crm_manager', company_id=cls.company.id, company_ids=[cls.company.id],
            groups='executive_dashboard.group_user,sales_team.group_sale_manager')
        cls.plain = new_test_user(cls.env, login='ed_crm_plain', groups='executive_dashboard.group_user')
        cls.stage = cls.env['crm.stage'].search([('is_won', '=', False)], limit=1)
        cls.today = fields.Date.context_today(cls.env['executive.dashboard'].with_user(cls.manager))

    def _opportunity(self, revenue, probability=50.0, days=10):
        return self.env['crm.lead'].create({
            'name': 'Example opportunity %s' % revenue, 'type': 'opportunity', 'partner_id': self.partner.id,
            'expected_revenue': revenue, 'probability': probability, 'stage_id': self.stage.id,
            'user_id': self.manager.id, 'date_deadline': self.today + timedelta(days=days),
            'company_id': self.company.id,
        })

    def test_widget_keys(self):
        result = self.section(self.manager, 'crm')
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(set(result['widgets']), {'currency', 'kpis', 'stages', 'salespeople', 'closing'})

    def test_pipeline_matches_native_opportunities(self):
        self._opportunity(1000.0, 40.0)
        won = self._opportunity(600.0)
        won.action_set_won()
        lost = self._opportunity(300.0)
        lost.action_set_lost()
        widgets = self.section(self.manager, 'crm')['widgets']
        Lead = self.env['crm.lead']
        native = Lead.search([('type', '=', 'opportunity'), ('won_status', '=', 'pending'),
                              ('company_id', 'in', [False, self.company.id])])
        currency = self.company.currency_id
        self.assertTrue(currency.is_zero(widgets['kpis']['pipeline'] - sum(native.mapped('expected_revenue'))))
        self.assertTrue(currency.is_zero(widgets['kpis']['weighted'] - sum(native.mapped('prorated_revenue'))))
        self.assertEqual(widgets['kpis']['opportunities'], len(native))
        self.assertGreaterEqual(widgets['kpis']['won'], 600.0)
        self.assertGreaterEqual(widgets['kpis']['won_count'], 1)
        self.assertGreaterEqual(widgets['kpis']['new_leads'], 3)
        stage = next(s for s in widgets['stages'] if s['id'] == self.stage.id)
        in_stage = native.filtered(lambda lead: lead.stage_id == self.stage)
        self.assertTrue(currency.is_zero(stage['amount'] - sum(in_stage.mapped('expected_revenue'))))
        self.assertEqual(stage['count'], len(in_stage))
        self.assertNotIn(won.id, [r['id'] for r in widgets['closing']])

    def test_drawers_open_opportunities(self):
        lead = self._opportunity(900.0, days=1)
        Dashboard = self.env['executive.dashboard'].with_user(self.manager)
        pipeline = Dashboard.get_drawer('crm.pipeline', {})
        stage_row = next(r for r in pipeline['rows'] if r['label'] == self.stage.name)
        stage = Dashboard.get_drawer(stage_row['open']['key'], stage_row['open']['args'])
        row = next(r for r in stage['rows'] if r['open']['args']['lead_id'] == lead.id)
        detail = Dashboard.get_drawer(row['open']['key'], row['open']['args'])
        self.assertEqual(detail['title'], lead.name)
        action = Dashboard.open_action('crm.opportunity', {'lead_id': lead.id})
        self.assertEqual((action['res_model'], action['res_id']), ('crm.lead', lead.id))
        for kind in ('leads', 'won', 'closing'):
            self.assertEqual(Dashboard.open_action('crm.list', {'period': 'month', 'kind': kind})['res_model'], 'crm.lead')
        with self.assertRaises(ValidationError):
            Dashboard.get_drawer('crm.list', {'kind': 'stage', 'stage_id': 'x'})

    def test_user_without_crm_rights_is_restricted(self):
        self.assertEqual(self.section(self.plain, 'crm')['status'], 'restricted')

    def test_query_limit(self):
        self._opportunity(100.0)
        self.section(self.manager, 'crm')
        dashboard_module.cache_clear()
        self.env.invalidate_all()
        with self.assertQueryCount(**{self.env.user.login: 20}):
            self.env['executive.dashboard'].with_user(self.manager).get_section('crm', 'month')
