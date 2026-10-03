from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged

from odoo.addons.executive_dashboard.models import dashboard as dashboard_module
from .test_sales_crm import SalesCrmCase


@tagged('post_install', '-at_install')
class TestKeyMetrics(SalesCrmCase):
    """Key metrics (A1-A8 of the section's acceptance criteria, see the build log)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin = new_test_user(cls.env, login='ed_key_admin', company_id=cls.company.id,
                                  company_ids=[cls.company.id], groups='executive_dashboard.group_admin')
        cls.Dashboard = cls.env['executive.dashboard'].with_user(cls.admin)
        cls.today = fields.Date.context_today(cls.Dashboard)
        Account = cls.env['account.account']
        cls.cost_account = Account.create({'name': 'Example cost of goods', 'code': 'EDK510',
                                           'account_type': 'expense_direct_cost'})
        cls.ad_account = Account.create({'name': 'Example online advertising', 'code': 'EDK610',
                                         'account_type': 'expense'})
        cls.other_account = Account.create({'name': 'Example clearing', 'code': 'EDK499',
                                            'account_type': 'liability_current'})
        product_vals = {'name': 'Example Key Tile', 'list_price': 100.0}
        if 'invoice_policy' in cls.env['product.template']._fields:
            product_vals['invoice_policy'] = 'order'
        if 'is_storable' in cls.env['product.template']._fields:
            product_vals.update(type='consu', is_storable=True)
        cls.product = cls.env['product.product'].create(product_vals)

    def widgets(self, period='month', date_from=None, date_to=None):
        dashboard_module.cache_clear()
        result = self.Dashboard.get_section('key_metrics', period, date_from, date_to)
        self.assertEqual(result['status'], 'ok')
        return result['widgets']

    def drawer(self, key, **args):
        return self.Dashboard.get_drawer('key_metrics.' + key, dict({'period': 'month'}, **args))

    def _entry(self, account, amount):
        move = self.env['account.move'].create({
            'move_type': 'entry', 'date': self.today,
            'line_ids': [fields.Command.create({'account_id': account.id, 'debit': amount, 'name': 'Example'}),
                         fields.Command.create({'account_id': self.other_account.id, 'credit': amount, 'name': 'Example'})],
        })
        move.action_post()
        return move

    def _invoice(self, amount):
        move = self.env['account.move'].create({
            'move_type': 'out_invoice', 'partner_id': self.partner.id, 'invoice_date': self.today, 'date': self.today,
            'invoice_line_ids': [fields.Command.create({'product_id': self.product.id, 'quantity': 1,
                                                        'price_unit': amount, 'tax_ids': [fields.Command.clear()]})],
        })
        move.action_post()
        return move

    def _order(self, qty, source=None, commitment=None):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id, 'source_id': source.id if source else False,
            'commitment_date': commitment,
            'order_line': [fields.Command.create({'product_id': self.product.id, 'product_uom_qty': qty,
                                                  'price_unit': 100.0, 'tax_ids': [fields.Command.clear()]})],
        })
        order.action_confirm()
        return order

    def _invoice_order(self, order):
        move = order._create_invoices()
        move.write({'invoice_date': self.today, 'date': self.today})
        move.action_post()
        return move

    def channel(self, widgets, source_id):
        return next((c for c in widgets['net_sales']['channels'] if c['id'] == source_id), None)

    # -- A1 section --------------------------------------------------------------

    def test_a1_section_is_first_and_complete(self):
        keys = [s['key'] for s in self.Dashboard.get_bootstrap()['sections']]
        self.assertEqual(keys[0], 'key_metrics')
        self.assertLess(keys.index('key_metrics'), keys.index('finance'))
        widgets = self.widgets()
        self.assertEqual(set(widgets), {'currency', 'net_sales', 'gross_profit', 'working_capital', 'otif', 'roas'})
        self.company.executive_dashboard_key_metrics = False
        self.assertNotIn('key_metrics', [s['key'] for s in self.Dashboard.get_bootstrap()['sections']])
        with self.assertRaises(AccessError):
            self.drawer('net_sales')

    # -- A2 net sales by channel ---------------------------------------------

    def test_a2_net_sales_match_posted_invoices(self):
        self._invoice(50.0)
        widgets = self.widgets()
        net = widgets['net_sales']
        scope = self.Dashboard._period_scope('key_metrics', 'month')
        moves = self.env['account.move'].search([
            ('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted'),
            ('company_id', '=', self.company.id),
            ('date', '>=', scope['date_from']), ('date', '<=', scope['date_to'])])
        self.assertAlmostEqual(net['total'], sum(moves.mapped('amount_untaxed_signed')), places=2)
        self.assertAlmostEqual(sum(c['net'] for c in net['channels']), net['total'], places=2)
        self.assertAlmostEqual(net['invoiced'] - net['refunds'], net['total'], places=2)

    def test_a2_channels_follow_the_order_source(self):
        if 'sale.order' not in self.env:
            self.skipTest('sale not installed')
        web = self.env['utm.source'].create({'name': 'Example Web'})
        before = self.widgets()
        none_before = self.channel(before, False) or {'net': 0.0}
        self._invoice_order(self._order(3.0, web))
        invoice = self._invoice_order(self._order(2.0, web))
        refund = invoice._reverse_moves([{'date': self.today, 'invoice_date': self.today}])
        refund.invoice_line_ids.quantity = 1.0
        refund.action_post()
        self._invoice(50.0)
        widgets = self.widgets()
        channel = self.channel(widgets, web.id)
        self.assertEqual((channel['invoiced'], channel['refunds'], channel['net']), (500.0, 100.0, 400.0))
        self.assertAlmostEqual(self.channel(widgets, False)['net'] - none_before['net'], 50.0)
        self.assertAlmostEqual(widgets['net_sales']['total'] - before['net_sales']['total'], 450.0)
        # Largest first, "No channel" last.
        named = [c['net'] for c in widgets['net_sales']['channels'] if c['id']]
        self.assertEqual(named, sorted(named, reverse=True))
        self.assertIs(widgets['net_sales']['channels'][-1]['id'], False)
        none = self.drawer('channel', source_id=False)
        self.assertEqual(none['total']['value'].split()[0], self.Dashboard._fin_format(self.channel(widgets, False)['net']))
        # The channel's panel lists its invoices and adds up to the same figure.
        panel = self.drawer('channel', source_id=web.id)
        self.assertEqual(panel['total']['value'].split()[0], '400')
        self.assertEqual(len(panel['rows']), 3)
        # An invoice opens only for users who may open it.
        self.assertFalse(any(row.get('action') for row in panel['rows']))
        billing = new_test_user(self.env, login='ed_key_billing', company_id=self.company.id,
                                company_ids=[self.company.id],
                                groups='executive_dashboard.group_admin,account.group_account_invoice')
        rows = self.Dashboard.with_user(billing).get_drawer(
            'key_metrics.channel', {'period': 'month', 'source_id': web.id})['rows']
        self.assertTrue(all(row['action'] and row['action']['kind'] == 'record' for row in rows))

    # -- A3 gross profit -----------------------------------------------------

    def test_a3_gross_profit_from_combined_totals(self):
        self._invoice(1000.0)
        before = self.widgets()['gross_profit']
        self._entry(self.cost_account, 120.0)
        gp = self.widgets()['gross_profit']
        self.assertAlmostEqual(gp['cogs'] - before['cogs'], 120.0)
        self.assertAlmostEqual(gp['gross_profit'], gp['revenue'] - gp['cogs'])
        self.assertAlmostEqual(gp['percent'], (gp['revenue'] - gp['cogs']) / gp['revenue'] * 100)
        panel = self.drawer('gross_profit')
        # The account rows open the ledger only for users who may open it (this one may not).
        accounts = [row for group in panel['groups'][1:] for row in group['rows']]
        self.assertFalse(any(row.get('action') for row in accounts))
        self.assertTrue(any(row['label'] == self.cost_account.name for row in accounts))

    # -- A4 working capital ------------------------------------------------------

    def test_a4_working_capital_matches_finance(self):
        widgets = self.widgets()
        wc = widgets['working_capital']
        finance = self.Dashboard._elevated()._section_finance(self.Dashboard._period_scope('finance', 'month'))
        self.assertAlmostEqual(wc['cash'], finance['kpis']['bank_cash'])
        self.assertAlmostEqual(wc['receivables'], finance['kpis']['receivables'])
        self.assertAlmostEqual(wc['payables'], finance['kpis']['payables'])
        self.assertAlmostEqual(wc['total'], wc['cash'] + (wc['inventory'] or 0.0) + wc['receivables'] - wc['payables'])
        if 'stock.quant' in self.env and 'value' in self.env['stock.quant']._fields:
            inventory = self.Dashboard._elevated()._inv_value(self.Dashboard._period_scope('inventory', 'month'))
            self.assertAlmostEqual(wc['inventory'], inventory['amount'], places=2)
            panel = self.drawer('inventory')
            self.assertEqual(panel['action']['kind'], 'list')
        else:
            self.assertIsNone(wc['inventory'])
        # Last month: balances at that month's end.
        last = self.widgets('last_month')['working_capital']
        self.assertEqual(last['as_of'], fields.Date.to_string(self.today.replace(day=1) - timedelta(days=1)))
        panel = self.drawer('working_capital')
        self.assertTrue(all(row['open']['key'].startswith('key_metrics.') for row in panel['rows']))
        # Finance panels open under this section even when Finance is hidden for the company.
        self.company.executive_dashboard_finance = False
        receivables = self.drawer('open_items', kind='receivables', view='aged')
        self.assertTrue(receivables['action'] is None or receivables['action']['key'] == 'key_metrics.open_items')
        reader = new_test_user(self.env, login='ed_key_reader', company_id=self.company.id,
                               company_ids=[self.company.id],
                               groups='executive_dashboard.group_admin,account.group_account_readonly')
        rows = self.Dashboard.with_user(reader).get_drawer('key_metrics.bank_cash', {'period': 'month'})['rows']
        self.assertTrue(rows)
        self.assertTrue(all(row['action']['key'] == 'key_metrics.account' for row in rows))

    # -- A5 OTIF -------------------------------------------------------------

    def test_a5_otif(self):
        if not self.Dashboard._key_otif_ready():
            self.skipTest('sale_stock not installed')
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company.id)], limit=1)
        self.env['stock.quant']._update_available_quantity(self.product, warehouse.lot_stock_id, 100.0)
        yesterday = self.today - timedelta(days=1)
        tz_due = self.Dashboard._utc_bounds(yesterday, yesterday)
        due = fields.Datetime.to_datetime(tz_due[0]) + timedelta(hours=12)
        on_time, late = due - timedelta(hours=1), fields.Datetime.to_datetime(tz_due[1]) + timedelta(hours=2)

        def deliver(order, qty, when):
            picking = order.picking_ids
            picking.move_ids.write({'quantity': qty, 'picked': True})
            picking.with_context(cancel_backorder=True)._action_done()
            picking.move_ids.filtered(lambda m: m.state == 'done').write({'date': when})

        ok, late_full, short, waiting, never, partial = (self._order(3.0, commitment=due) for _i in range(6))
        deliver(ok, 3.0, on_time)
        deliver(late_full, 3.0, late)
        deliver(short, 1.0, on_time)
        # Delivered short on time, the rest still to deliver (backorder open).
        partial.picking_ids.move_ids.write({'quantity': 1.0, 'picked': True})
        partial.picking_ids.with_context(cancel_backorder=False)._action_done()
        partial.picking_ids.move_ids.filtered(lambda m: m.state == 'done').write({'date': on_time})
        # Nothing delivered and nothing left to deliver (the delivery was cancelled).
        never.picking_ids.action_cancel()
        args = {'date_from': fields.Date.to_string(yesterday - timedelta(days=1)), 'date_to': fields.Date.to_string(self.today)}
        scope = self.Dashboard._elevated()._period_scope('key_metrics', 'custom', **args)
        kinds = {order: kind for order, _day, kind in self.Dashboard._elevated()._key_otif_orders(scope)}
        self.assertEqual((kinds[ok], kinds[late_full], kinds[short], kinds[waiting], kinds[never], kinds[partial]),
                         ('ok', 'late', 'not_full', 'both', 'both', 'both'))
        otif = self.widgets('custom', **args)['otif']
        self.assertEqual(otif['due'], len(kinds))
        self.assertAlmostEqual(otif['percent'], otif['ok'] / otif['due'] * 100)
        panel = self.Dashboard.get_drawer('key_metrics.otif', dict(args, period='custom', kind='both'))
        self.assertIn(waiting.name, [row['label'] for row in panel['rows']])
        # An order due today is not counted yet.
        self._order(1.0, commitment=fields.Datetime.now() + timedelta(hours=1))
        self.assertEqual(self.widgets('custom', **args)['otif']['due'], otif['due'])

    # -- A6 ROAS -------------------------------------------------------------

    def test_a6_roas(self):
        self._invoice(1000.0)
        self.company.executive_dashboard_ad_account_ids = False
        self.assertIsNone(self.widgets()['roas']['roas'])
        self.company.executive_dashboard_ad_account_ids = self.ad_account
        self._entry(self.ad_account, 50.0)
        widgets = self.widgets()
        self.assertEqual(widgets['roas']['spend'], 50.0)
        self.assertAlmostEqual(widgets['roas']['roas'], widgets['net_sales']['total'] / 50.0)
        panel = self.drawer('roas')
        self.assertEqual([row['label'] for row in panel['rows']], [self.ad_account.name])

    # -- A7 side panels and arguments ------------------------------------------

    def test_a7_every_panel_opens(self):
        for key, args in (('net_sales', {}), ('channel', {'source_id': False}), ('gross_profit', {}),
                          ('working_capital', {}), ('bank_cash', {}), ('roas', {}),
                          ('open_items', {'kind': 'payables', 'view': 'aged'})):
            panel = self.drawer(key, **args)
            self.assertTrue(panel['title'])
        if self.Dashboard._key_otif_ready():
            for kind in (None, 'ok', 'not_full', 'late', 'both'):
                self.drawer('otif', **({'kind': kind} if kind else {}))

    def test_a7_arguments_are_validated(self):
        for key, args in (('channel', {'source_id': 'x'}), ('channel', {'source_id': -1}), ('otif', {'kind': 'x'}),
                          ('open_items', {'kind': 'x'}), ('nothing', {})):
            with self.assertRaises(ValidationError):
                self.drawer(key, **args)
        with self.assertRaises(ValidationError):
            self.Dashboard.open_action('key_metrics.move', {'move_id': 0})
        other = self.env['res.company'].create({'name': 'Example Other Company'})
        account = self.env['account.account'].create({'name': 'Example other', 'code': 'EDK777',
                                                       'account_type': 'expense', 'company_ids': other.ids})
        with self.assertRaises(ValidationError):
            self.Dashboard.open_action('key_metrics.account', {'account_id': account.id})

    # -- A8 performance ---------------------------------------------------------

    def test_a8_query_limit(self):
        self._invoice(100.0)
        if self.Dashboard._fin_engine():
            self.skipTest('Enterprise reports: the native engines add their own queries')
        if 'sale.order' in self.env:
            for name in ('Example A', 'Example B', 'Example C'):
                self._invoice_order(self._order(1.0, self.env['utm.source'].create({'name': name})))
        self.widgets()  # warm the ORM caches (fields, rules)
        dashboard_module.cache_clear()
        self.env.invalidate_all()
        # The number of channels does not change the number of queries.
        with self.assertQueryCount(**{self.env.user.login: 55}):
            self.Dashboard.get_section('key_metrics', 'month')
