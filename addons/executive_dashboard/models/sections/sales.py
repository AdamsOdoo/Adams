"""Sales: invoiced sales, orders, salespeople, products, customers and recent orders.

Invoiced sales are posted customer invoices and credit notes (``amount_untaxed_signed``,
accounting date in the period), the same documents as Accounting › Customers ›
Invoices. Orders come from ``sale.order``; the Delivery Status is the order's own
``delivery_status`` field (``sale_stock``), shown with Odoo's labels.

Every total is one grouped query (``_read_group``), filtered on the user's current companies.
"""
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz
from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.misc import format_date, formatLang

TREND_MONTHS = 12
TOP_ROWS = 5
RECENT_ROWS = 10
LINE_ROWS = 50
INVOICE_TYPES = ('out_invoice', 'out_refund')


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_sales(self, scope):
        """Sales widgets: ``currency``, ``kpis``, ``trend``, ``salespeople``, ``products``,
        ``customers``, ``orders``, ``quotations``; a widget whose app is missing is ``None``."""
        currency = scope['company'].currency_id
        invoices = self._sal_can_read('account.move')
        orders = self._sal_orders_kpi(scope, self._sal_confirmed_domain(scope))
        quotations = self._sal_orders_kpi(scope, self._sal_quotation_domain(scope))
        return {
            'currency': {'name': currency.name, 'symbol': currency.symbol,
                         'position': currency.position, 'digits': currency.decimal_places},
            'kpis': {
                'invoiced': self._sal_invoiced(scope) if invoices else None,
                'orders': orders,
                'quotations': quotations,
                'to_invoice': self._sal_to_invoice(scope),
            },
            'trend': self._sal_trend(scope) if invoices else None,
            'salespeople': self._sal_salespeople(scope) if invoices else None,
            'products': self._sal_products(scope) if self._sal_can_read('account.move.line') else None,
            'customers': self._sal_customers(scope) if self._sal_can_read('account.move.line') else None,
            'orders': self._sal_recent(scope),
            'quotations': self._sal_recent_quotations(scope),
        }

    # ------------------------------------------------------------------ helpers

    def _sal_can_read(self, model):
        """Whether ``model`` is installed (the dashboard reads with elevated rights)."""
        return model in self.env and self.env[model].has_access('read')

    def _utc_bounds(self, date_from, date_to):
        """Naive UTC datetimes of the user's local midnight at ``date_from`` and after ``date_to``."""
        tz = self.env.tz
        start = tz.localize(datetime.combine(date_from, time.min))
        end = tz.localize(datetime.combine(date_to + timedelta(days=1), time.min))
        return (fields.Datetime.to_string(start.astimezone(pytz.utc).replace(tzinfo=None)),
                fields.Datetime.to_string(end.astimezone(pytz.utc).replace(tzinfo=None)))

    def _in_period(self, fname, scope):
        start, end = self._utc_bounds(scope['date_from'], scope['date_to'])
        return [(fname, '>=', start), (fname, '<', end)]

    def _money(self, scope, rows, day):
        """Sum of ``[(currency, company, amount)]`` in the dashboard company's currency."""
        target = scope['company'].currency_id
        return sum(amount if currency == target or not amount
                   else currency._convert(amount, target, company, day)
                   for currency, company, amount in rows)

    def _ranked(self, scope, model, domain, key, measure, limit, day):
        """``[(group, amount, count)]``, the ``limit`` largest amounts of ``measure`` (company
        currency, per company) by ``key``, converted to the dashboard company's currency."""
        Model = self.env[model]
        if len(scope['companies'].currency_id) == 1:
            company = scope['companies'][:1]
            return [(group, self._fin_convert(scope, amount, company, day), count)
                    for group, amount, count in Model._read_group(
                        domain, [key], [f'{measure}:sum', '__count'], order=f'{measure}:sum desc', limit=limit)]
        totals, counts = defaultdict(float), defaultdict(int)
        for group, company, amount, count in Model._read_group(
                domain, [key, 'company_id'], [f'{measure}:sum', '__count']):
            # Records without a company (e.g. shared leads) count in the dashboard company.
            totals[group] += self._fin_convert(scope, amount, company or scope['company'], day)
            counts[group] += count
        return [(group, totals[group], counts[group])
                for group in sorted(totals, key=lambda g: -totals[g])[:limit]]

    def _window(self, xmlid, name, model, domain, context=None, res_id=None):
        """The native window action ``xmlid`` (views and search panel) on ``domain``, or a plain one."""
        action = self.env['ir.actions.act_window']._for_xml_id(xmlid) \
            if self.env.ref(xmlid, raise_if_not_found=False) else {
                'type': 'ir.actions.act_window', 'res_model': model,
                'views': [[False, 'list'], [False, 'form']]}
        action.update(name=name, display_name=name, domain=list(domain), context=context or {}, target='current')
        if res_id:
            action.update(res_id=res_id, views=[[False, 'form']], view_mode='form')
        return action

    def _sal_scope(self, args):
        return self._period_scope('sales', args.get('period') or 'month', args.get('date_from'), args.get('date_to'))

    def _positive_id(self, args, key, optional=False):
        """A record id from client arguments (``False`` allowed when ``optional``)."""
        value = args.get(key)
        if optional and value is False:
            return False
        if type(value) is not int or value <= 0:
            raise ValidationError(self.env._('Unknown detail.'))
        return value

    def _sal_format(self, amount):
        return formatLang(self.env, amount, digits=0)

    def _sal_selection(self, model, fname, value):
        """Odoo's own (translated) label of a selection value."""
        return dict(self.env[model]._fields[fname]._description_selection(self.env)).get(value, value or '')

    # ------------------------------------------------------------------ domains

    def _sal_invoice_domain(self, scope, date_from=None, date_to=None):
        return Domain([
            ('move_type', 'in', INVOICE_TYPES), ('state', '=', 'posted'),
            ('company_id', 'in', scope['companies'].ids),
            ('date', '>=', fields.Date.to_string(date_from or scope['date_from'])),
            ('date', '<=', fields.Date.to_string(date_to or scope['date_to'])),
        ])

    def _sal_confirmed_domain(self, scope):
        return Domain([('state', '=', 'sale'), ('company_id', 'in', scope['companies'].ids),
                       *self._in_period('date_order', scope)])

    def _sal_quotation_domain(self, scope):
        return Domain([('state', 'in', ('draft', 'sent')), ('company_id', 'in', scope['companies'].ids)])

    def _sal_to_invoice_domain(self, scope):
        return Domain([('invoice_status', '=', 'to invoice'), ('company_id', 'in', scope['companies'].ids)])

    def _sal_collection_domain(self, scope):
        """Receivable (trade) journal items of customers in the period's posted entries."""
        return Domain([
            ('parent_state', '=', 'posted'), ('company_id', 'in', scope['companies'].ids),
            ('date', '>=', fields.Date.to_string(scope['date_from'])),
            ('date', '<=', fields.Date.to_string(scope['date_to'])),
            ('account_id.account_type', '=', 'asset_receivable'), ('account_id.non_trade', '=', False),
            ('partner_id', '!=', False),
        ])

    def _sal_collections(self, scope, partner_id=None):
        """``{partner: {entry: amount}}``: money received from each customer in the period, in the
        dashboard company's currency (refunds paid out are negative).

        The money side is measured, never the receivable side, so a write-off, an early-payment
        discount or withheld tax settled with a payment does not count as money received:
        - customer payments: the payment's own amount (``amount_company_currency_signed``);
        - other entries with a bank or cash line and a customer's receivable line (bank statement
          lines matched to invoices, manual journal entries): the bank and cash lines' balance,
          shared between the entry's customers in proportion to their receivable movement.
        Credit notes and write-offs alone move no money and do not count.
        """
        partners = [('partner_id', '=', partner_id)] if partner_id else []
        result = defaultdict(lambda: defaultdict(float))
        Payment, Line = self.env['account.payment'], self.env['account.move.line']
        for partner, move, company, amount in Payment._read_group([
                ('partner_type', '=', 'customer'), ('partner_id', '!=', False), ('move_id', '!=', False),
                ('state', 'in', ('in_process', 'paid')), ('company_id', 'in', scope['companies'].ids),
                ('date', '>=', fields.Date.to_string(scope['date_from'])),
                ('date', '<=', fields.Date.to_string(scope['date_to'])), *partners],
                ['partner_id', 'move_id', 'company_id'], ['amount_company_currency_signed:sum']):
            result[partner][move] += self._fin_convert(scope, amount, company, scope['date_to'])
        receivable = self._sal_collection_domain(scope) & Domain('move_id.origin_payment_id', '=', False) \
            & Domain('move_id.line_ids', 'any', [('account_id.account_type', '=', 'asset_cash')])
        if partner_id:
            # Every customer of the entries this customer is in, to share the money correctly.
            receivable = self._sal_collection_domain(scope) & Domain('move_id', 'any', Domain.AND([
                Domain('origin_payment_id', '=', False),
                Domain('line_ids', 'any', [('account_id.account_type', '=', 'asset_cash')]),
                Domain('line_ids', 'any', self._sal_collection_domain(scope) & Domain('partner_id', '=', partner_id)),
            ]))
        shares = defaultdict(dict)
        for move, partner, balance in Line._read_group(receivable, ['move_id', 'partner_id'], ['balance:sum']):
            shares[move][partner] = -balance
        if shares:
            moves = self.env['account.move'].union(*shares)
            for move, company, money in Line._read_group(
                    [('move_id', 'in', moves.ids), ('account_id.account_type', '=', 'asset_cash')],
                    ['move_id', 'company_id'], ['balance:sum']):
                total = sum(shares[move].values())
                if not total:
                    continue
                money = self._fin_convert(scope, money, company, scope['date_to'])
                for partner, part in shares[move].items():
                    if not partner_id or partner.id == partner_id:
                        result[partner][move] += money * part / total
        return result

    def _sal_collected(self, scope, partner_id=None):
        """``[(partner, collected, entries)]``, largest first."""
        rows = [(partner, sum(moves.values()), len(moves))
                for partner, moves in self._sal_collections(scope, partner_id).items()]
        return sorted(rows, key=lambda row: (-row[1], row[0].id))

    # ------------------------------------------------------------------ figures

    def _sal_invoiced(self, scope):
        """Untaxed invoiced sales (credit notes deducted) and the number of invoices."""
        rows = self.env['account.move']._read_group(
            self._sal_invoice_domain(scope), ['company_id', 'move_type'], ['amount_untaxed_signed:sum', '__count'])
        return {
            'amount': sum(self._fin_convert(scope, amount, company, scope['date_to']) for company, _t, amount, _c in rows),
            'count': sum(count for _c, move_type, _a, count in rows if move_type == 'out_invoice'),
        }

    def _sal_orders_kpi(self, scope, domain):
        rows = self.env['sale.order']._read_group(
            domain, ['currency_id', 'company_id'], ['amount_untaxed:sum', '__count'])
        day = min(scope['date_to'], scope['today'])
        return {'amount': self._money(scope, [(cur, company, amount) for cur, company, amount, _c in rows], day),
                'count': sum(count for *_r, count in rows)}

    def _sal_to_invoice(self, scope):
        """Orders to invoice: their number and the untaxed amount still to invoice on their lines."""
        count = self.env['sale.order'].search_count(self._sal_to_invoice_domain(scope))
        rows = self.env['sale.order.line']._read_group(
            [('order_id.invoice_status', '=', 'to invoice'), ('company_id', 'in', scope['companies'].ids)],
            ['currency_id', 'company_id'], ['untaxed_amount_to_invoice:sum'])
        return {'amount': self._money(scope, rows, scope['today']), 'count': count}

    def _sal_trend(self, scope):
        """Invoiced sales for the 12 months ending with the period's last month."""
        end = scope['date_to']
        start = end.replace(day=1) - relativedelta(months=TREND_MONTHS - 1)
        by_month = defaultdict(float)
        for company, month, amount in self.env['account.move']._read_group(
                self._sal_invoice_domain(scope, start, end), ['company_id', 'date:month'],
                ['amount_untaxed_signed:sum']):
            month = fields.Date.to_date(month)
            day = min(month + relativedelta(months=1, days=-1), end)
            by_month[month] += self._fin_convert(scope, amount, company, day)
        months = [start + relativedelta(months=i) for i in range(TREND_MONTHS)]
        last_day = end.replace(day=1) + relativedelta(months=1, days=-1)
        return {'months': [{'month': fields.Date.to_string(m), 'amount': by_month[m]} for m in months],
                'partial': end < last_day}

    def _sal_salespeople(self, scope, limit=TOP_ROWS):
        """Salespeople by invoiced sales, the ``limit`` first (every one when None)."""
        rows = self._ranked(scope, 'account.move', self._sal_invoice_domain(scope), 'invoice_user_id',
                            'amount_untaxed_signed', limit, scope['date_to'])
        return [{'id': user.id or False, 'name': user.name or self.env._('No salesperson'),
                 'amount': amount, 'count': count} for user, amount, count in rows]

    def _sal_products(self, scope, limit=TOP_ROWS):
        """Net quantity invoiced per product and unit (credit notes deducted), the ``limit`` largest
        (every one when None); units are never summed."""
        rows = self.env['account.move.line']._read_group(
            [('move_id', 'any', self._sal_invoice_domain(scope)), ('display_type', '=', 'product'),
             ('product_id', '!=', False)],
            ['product_id', 'product_uom_id', 'move_id.move_type'], ['quantity:sum'])
        totals = defaultdict(float)
        for product, uom, move_type, quantity in rows:
            totals[product, uom] += -quantity if move_type == 'out_refund' else quantity
        ranked = sorted((key for key in totals if totals[key] > 0), key=lambda k: (-totals[k], k[0].id, k[1].id))[:limit]
        return [{'product_id': product.id, 'uom_id': uom.id, 'name': product.display_name,
                 'code': product.default_code or '', 'uom': uom.name or '', 'quantity': totals[product, uom]}
                for product, uom in ranked]

    def _sal_customers(self, scope, limit=TOP_ROWS):
        """Customers by money received, the ``limit`` first (every one when None)."""
        rows = self._sal_collected(scope)
        return [{'id': partner.id, 'name': partner.display_name, 'amount': amount, 'count': count}
                for partner, amount, count in rows if amount > 0][:limit]

    def _sal_order_row(self, order, delivery):
        return {
            'id': order.id, 'name': order.name, 'customer': order.partner_id.display_name,
            'date': fields.Date.to_string(fields.Datetime.context_timestamp(self, order.date_order)),
            'amount': order.amount_untaxed, 'currency': order.currency_id.name,
            'delivery_status': (order.delivery_status or False) if delivery else False,
            'delivery_label': self._sal_selection('sale.order', 'delivery_status', order.delivery_status)
            if delivery and order.delivery_status else '',
        }

    def _sal_recent(self, scope):
        """Latest confirmed orders of the period, with their Delivery Status when ``sale_stock`` is installed."""
        SaleOrder = self.env['sale.order']
        domain = self._sal_confirmed_domain(scope)
        delivery = 'delivery_status' in SaleOrder._fields
        orders = SaleOrder.search(domain, order='date_order desc, id desc', limit=RECENT_ROWS)
        return {'rows': [self._sal_order_row(order, delivery) for order in orders],
                'count': SaleOrder.search_count(domain), 'delivery': delivery}

    def _sal_recent_quotations(self, scope):
        """Latest open quotations (draft or sent), as of today like the Open quotations figure."""
        SaleOrder = self.env['sale.order']
        domain = self._sal_quotation_domain(scope)
        quotations = SaleOrder.search(domain, order='date_order desc, id desc', limit=RECENT_ROWS)
        return {'rows': [{
            'id': order.id, 'name': order.name, 'customer': order.partner_id.display_name,
            'date': fields.Date.to_string(fields.Datetime.context_timestamp(self, order.date_order)),
            'validity_date': fields.Date.to_string(order.validity_date) if order.validity_date else False,
            'amount': order.amount_untaxed, 'currency': order.currency_id.name,
            'state': order.state, 'state_label': self._sal_selection('sale.order', 'state', order.state),
        } for order in quotations], 'count': SaleOrder.search_count(domain)}

    # ------------------------------------------------------------------ drawers

    def _sal_search_page(self, model, domain, order):
        """``(records, more)``: one page of ``domain`` for a side-panel list and its "Show more"."""
        Model = self.env[model]
        records = Model.search(domain, order=order, limit=self._drawer_limit())
        more = self._drawer_more(len(records), Model.search_count(domain)) \
            if len(records) == self._drawer_limit() else False
        return records, more

    def _sal_invoice_rows(self, moves):
        return [{'label': move.name, 'sub': ' · '.join(filter(None, [
                    format_date(self.env, move.date), move.partner_id.display_name])),
                 'value': self._sal_format(move.amount_untaxed_signed)} for move in moves]

    def _drawer_sales_invoices(self, args):
        scope = self._sal_scope(args)
        domain = self._sal_invoice_domain(scope)
        _ = self.env._
        moves, more = self._sal_search_page('account.move', domain, 'date desc, id desc')
        invoiced = self._sal_invoiced(scope)
        return {'title': _('Invoiced sales'), 'sub': _('Posted customer invoices and credit notes · untaxed'),
                'rows': self._sal_invoice_rows(moves), 'more': more,
                'total': {'label': _('Total'), 'value': '%s %s' % (
                    self._sal_format(invoiced['amount']), scope['company'].currency_id.name)},
                'action': {'key': 'sales.invoices', 'args': args}, 'dest': _('Customer Invoices')}

    def _action_sales_invoices(self, args):
        scope = self._sal_scope(args)
        return self._window('account.action_move_out_invoice', self.env._('Invoiced sales'),
                            'account.move', self._sal_invoice_domain(scope))

    def _sal_salesperson_domain(self, args):
        scope = self._sal_scope(args)
        user_id = self._positive_id(args, 'user_id', optional=True)
        return scope, user_id, self._sal_invoice_domain(scope) & Domain('invoice_user_id', '=', user_id)

    def _drawer_sales_salesperson(self, args):
        scope, user_id, domain = self._sal_salesperson_domain(args)
        _ = self.env._
        name = self.env['res.users'].browse(user_id).name if user_id else _('No salesperson')
        moves, more = self._sal_search_page('account.move', domain, 'date desc, id desc')
        total = self._ranked(scope, 'account.move', domain, 'invoice_user_id', 'amount_untaxed_signed', 1,
                             scope['date_to'])
        return {'title': name, 'sub': _('Salespeople by invoiced sales'),
                'rows': self._sal_invoice_rows(moves), 'more': more,
                'total': {'label': _('Total'), 'value': self._sal_format(total[0][1] if total else 0.0)},
                'action': {'key': 'sales.salesperson', 'args': args}, 'dest': _('Customer Invoices')}

    def _action_sales_salesperson(self, args):
        _scope, user_id, domain = self._sal_salesperson_domain(args)
        return self._window('account.action_move_out_invoice', self.env._('Invoiced sales'), 'account.move', domain)

    def _sal_product_domain(self, args):
        scope = self._sal_scope(args)
        product_id, uom_id = self._positive_id(args, 'product_id'), self._positive_id(args, 'uom_id')
        return scope, product_id, uom_id, Domain([
            ('move_id', 'any', self._sal_invoice_domain(scope)), ('display_type', '=', 'product'),
            ('product_id', '=', product_id), ('product_uom_id', '=', uom_id)])

    def _drawer_sales_product(self, args):
        scope, product_id, uom_id, domain = self._sal_product_domain(args)
        _ = self.env._
        product = self.env['product.product'].browse(product_id)
        uom = self.env['uom.uom'].browse(uom_id)
        lines, more = self._sal_search_page('account.move.line', domain, 'date desc, id desc')
        rows = [{'label': line.move_id.name,
                 'sub': ' · '.join(filter(None, [format_date(self.env, line.date), line.partner_id.display_name])),
                 'value': '%s %s' % (formatLang(self.env, -line.quantity if line.move_id.move_type == 'out_refund'
                                                else line.quantity, digits=2), uom.name)}
                for line in lines]
        return {'title': product.display_name, 'sub': _('Invoiced quantity · %s', uom.name), 'rows': rows, 'more': more,
                'action': {'key': 'sales.product', 'args': args}, 'dest': _('Customer Invoices')}

    def _action_sales_product(self, args):
        scope, product_id, uom_id, _domain = self._sal_product_domain(args)
        domain = self._sal_invoice_domain(scope) & Domain('invoice_line_ids', 'any', [
            ('product_id', '=', product_id), ('product_uom_id', '=', uom_id)])
        return self._window('account.action_move_out_invoice', self.env._('Invoiced sales'), 'account.move', domain)

    def _sal_customer_args(self, args):
        return self._sal_scope(args), self._positive_id(args, 'partner_id')

    def _drawer_sales_customer(self, args):
        scope, partner_id = self._sal_customer_args(args)
        _ = self.env._
        moves = self._sal_collections(scope, partner_id).get(self.env['res.partner'].browse(partner_id), {})
        ranked, more = self._drawer_page(sorted(moves, key=lambda m: (m.date, m.id), reverse=True))
        return {'title': self.env['res.partner'].browse(partner_id).display_name,
                'sub': _('Money received in the period: payments, bank statement lines and journal entries'),
                'rows': [{'label': move.name,
                          'sub': ' · '.join(filter(None, [format_date(self.env, move.date), move.journal_id.name])),
                          'value': self._sal_format(moves[move])} for move in ranked],
                'more': more, 'total': {'label': _('Total'), 'value': self._sal_format(sum(moves.values()))},
                'action': {'key': 'sales.customer', 'args': args}, 'dest': _('Journal Entries')}

    def _action_sales_customer(self, args):
        scope, partner_id = self._sal_customer_args(args)
        moves = self._sal_collections(scope, partner_id).get(self.env['res.partner'].browse(partner_id), {})
        domain = Domain('id', 'in', [move.id for move in moves])
        return self._window('account.action_move_journal_line', self.env._('Customer collections'),
                            'account.move', domain)

    # "View all" of the ranked lists: every salesperson, product or customer of the period.

    def _drawer_sales_salespeople(self, args):
        scope, _ = self._sal_scope(args), self.env._
        title, period = _('Salespeople by invoiced sales'), self._fin_period_args(args)
        people = self._sal_salespeople(scope, None)
        shown, more = self._drawer_page(people)
        return {'title': title, 'sub': _('Posted customer invoices and credit notes · untaxed'), 'more': more,
                'rows': [{'label': p['name'], 'sub': _('%s invoices', p['count']), 'value': self._sal_format(p['amount']),
                          'open': {'key': 'sales.salesperson', 'args': dict(period, user_id=p['id']), 'crumb': title}}
                         for p in shown],
                'total': {'label': _('Total'), 'value': '%s %s' % (
                    self._sal_format(sum(p['amount'] for p in people)), scope['company'].currency_id.name)},
                'action': {'key': 'sales.invoices', 'args': period}, 'dest': _('Customer Invoices')}

    def _drawer_sales_products(self, args):
        scope, _ = self._sal_scope(args), self.env._
        title, period = _('Top products by quantity'), self._fin_period_args(args)
        shown, more = self._drawer_page(self._sal_products(scope, None))
        return {'title': title, 'sub': _('Invoiced quantity, credit notes deducted'), 'more': more,
                'rows': [{'label': p['name'], 'sub': p['code'],
                          'value': '%s %s' % (formatLang(self.env, p['quantity'], digits=0), p['uom']),
                          'open': {'key': 'sales.product', 'crumb': title,
                                   'args': dict(period, product_id=p['product_id'], uom_id=p['uom_id'])}}
                         for p in shown],
                'action': {'key': 'sales.invoices', 'args': period}, 'dest': _('Customer Invoices')}

    def _drawer_sales_customers(self, args):
        scope, _ = self._sal_scope(args), self.env._
        title, period = _('Top customers by collections'), self._fin_period_args(args)
        customers = self._sal_customers(scope, None)
        shown, more = self._drawer_page(customers)
        return {'title': title,
                'sub': _('Money received in the period: payments, bank statement lines and journal entries'),
                'more': more,
                'rows': [{'label': c['name'], 'sub': _('%s receipts', c['count']), 'value': self._sal_format(c['amount']),
                          'open': {'key': 'sales.customer', 'args': dict(period, partner_id=c['id']), 'crumb': title}}
                         for c in shown],
                'total': {'label': _('Total'), 'value': '%s %s' % (
                    self._sal_format(sum(c['amount'] for c in customers)), scope['company'].currency_id.name)},
                'action': {'key': 'sales.customers', 'args': period}, 'dest': _('Journal Entries')}

    def _action_sales_customers(self, args):
        scope = self._sal_scope(args)
        moves = [move.id for partner, entries in self._sal_collections(scope).items()
                 if sum(entries.values()) > 0 for move in entries]
        return self._window('account.action_move_journal_line', self.env._('Customer collections'),
                            'account.move', Domain('id', 'in', moves))

    def _sal_list_domain(self, args):
        """Order lists behind the three order figures: ``(title, domain, xmlid, destination)``."""
        kind = args.get('kind')
        _ = self.env._
        if kind == 'orders':
            return (_('Confirmed orders'), self._sal_confirmed_domain(self._sal_scope(args)),
                    'sale.action_orders', _('Sales Orders'))
        scope = self._period_scope('sales', 'month')
        if kind == 'quotations':
            return _('Open quotations'), self._sal_quotation_domain(scope), 'sale.action_quotations', _('Quotations')
        if kind == 'to_invoice':
            return (_('Orders to invoice'), self._sal_to_invoice_domain(scope), 'sale.action_orders_to_invoice',
                    _('Orders to Invoice'))
        raise ValidationError(_('Unknown detail.'))

    def _drawer_sales_orders(self, args):
        title, domain, _xmlid, dest = self._sal_list_domain(args)
        _ = self.env._
        SaleOrder = self.env['sale.order']
        delivery = 'delivery_status' in SaleOrder._fields
        orders, more = self._sal_search_page('sale.order', domain, 'date_order desc, id desc')
        count = more['count'] if more else len(orders)
        rows = []
        for order in orders:
            row = self._sal_order_row(order, delivery)
            rows.append({'label': order.name,
                         'sub': ' · '.join(filter(None, [order.partner_id.display_name, row['delivery_label']])),
                         'value': '%s %s' % (self._sal_format(order.amount_untaxed), order.currency_id.name),
                         'open': {'key': 'sales.order', 'args': {'order_id': order.id}, 'crumb': title}})
        return {'title': title, 'sub': _('%s orders', count), 'rows': rows, 'more': more,
                'action': {'key': 'sales.orders', 'args': args}, 'dest': dest}

    def _action_sales_orders(self, args):
        title, domain, xmlid, _dest = self._sal_list_domain(args)
        return self._window(xmlid, title, 'sale.order', domain)

    def _sal_order(self, args):
        order = self.env['sale.order'].browse(self._positive_id(args, 'order_id')).exists()
        if not order:
            raise ValidationError(self.env._('Unknown detail.'))
        self._check_company(order)
        return order

    def _sal_pickings(self, order):
        """The order's delivery orders (``picking_ids`` comes with ``sale_stock``), or None."""
        if 'picking_ids' not in order._fields or not self._sal_can_read('stock.picking'):
            return None
        return order.picking_ids.sorted(lambda p: (p.scheduled_date or datetime.max, p.id))

    def _drawer_sales_order(self, args):
        """One order or quotation: its details, statuses as Odoo stores them, and its lines."""
        order = self._sal_order(args)
        _ = self.env._
        delivery = 'delivery_status' in order._fields
        row = self._sal_order_row(order, delivery)
        pickings = self._sal_pickings(order)
        lines = order.order_line.filtered(lambda l: not l.display_type)
        quotation = order.state in ('draft', 'sent')
        return {
            'title': order.name, 'sub': order.partner_id.display_name,
            'customer': order.partner_id.display_name,
            'date': row['date'],
            'validity_date': fields.Date.to_string(order.validity_date) if order.validity_date else False,
            'salesperson': order.user_id.name or '',
            'untaxed': order.amount_untaxed, 'total': order.amount_total, 'currency': order.currency_id.name,
            'state': order.state, 'state_label': self._sal_selection('sale.order', 'state', order.state),
            'delivery_status': row['delivery_status'], 'delivery_label': row['delivery_label'],
            'invoice_status': order.invoice_status or False,
            'invoice_label': self._sal_selection('sale.order', 'invoice_status', order.invoice_status)
            if order.invoice_status else '',
            'lines': [{
                'name': line.product_id.display_name or line.name,
                'unit': line.product_uom_id.name or '',
                'ordered': line.product_uom_qty, 'delivered': line.qty_delivered, 'invoiced': line.qty_invoiced,
            } for line in lines[:LINE_ROWS]],
            'line_count': len(lines),
            'deliveries': len(pickings) if pickings is not None else None,
            'action': {'key': 'sales.order', 'args': {'order_id': order.id}},
            'dest': _('Quotation') if quotation else _('Sales Order'),
        }

    def _action_sales_order(self, args):
        order = self._sal_order(args)
        if order.state in ('draft', 'sent'):
            return self._window('sale.action_quotations', order.name, 'sale.order', [('id', '=', order.id)],
                                res_id=order.id)
        return self._window('sale.action_orders', order.name, 'sale.order', [('id', '=', order.id)], res_id=order.id)

    def _drawer_sales_deliveries(self, args):
        """The order's delivery orders; each opens in Inventory."""
        order = self._sal_order(args)
        _ = self.env._
        rows = []
        for picking in self._sal_pickings(order) or ():
            done = picking.state == 'done' and picking.date_done
            when = fields.Datetime.context_timestamp(self, done or picking.scheduled_date) \
                if (done or picking.scheduled_date) else None
            rows.append({
                'label': picking.name,
                'sub': (_('Done %s', format_date(self.env, when)) if done else
                        _('Scheduled %s', format_date(self.env, when)) if when else ''),
                'value': self._sal_selection('stock.picking', 'state', picking.state),
                'action': {'key': 'sales.picking', 'args': {'order_id': order.id, 'picking_id': picking.id}},
            })
        return {'title': _('Deliveries'), 'sub': '%s · %s' % (order.name, order.partner_id.display_name),
                'rows': rows}

    def _action_sales_picking(self, args):
        """One delivery order of the order, in Inventory."""
        order = self._sal_order(args)
        picking_id = self._positive_id(args, 'picking_id')
        pickings = self._sal_pickings(order)
        if not pickings or picking_id not in pickings.ids:
            raise ValidationError(self.env._('Unknown detail.'))
        return self._window('stock.action_picking_tree_all', pickings.browse(picking_id).name, 'stock.picking',
                            [('id', '=', picking_id)], res_id=picking_id)
