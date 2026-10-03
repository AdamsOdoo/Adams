"""Key metrics: net sales by channel, gross profit %, working capital, OTIF and ROAS.

Net sales are the product lines of posted customer invoices and credit notes in the period
(accounting date), untaxed, after line discounts: invoices minus credit notes (returns and
corrections). Cancelled orders and invoices are never posted, so never counted. The channel
is the Source (``source_id``) of the sales order an invoice line comes from; lines without
a sales order, or whose order has no Source, are "No channel".

Gross profit % is one calculation on the company totals of the period:
(net sales - cost of goods sold) / net sales x 100, where cost of goods sold is the posted
balance of the Cost of Revenue accounts (``expense_direct_cost``). Margins of products or
channels are never averaged.

Working capital is taken at the period's end (never after today): available cash (the Bank
and Cash accounts), inventory at cost (Odoo's stock valuation), receivables and payables
(the Finance figures), and their sum cash + inventory + receivables - payables.

OTIF counts the confirmed sales orders due in the period whose due day has passed: due on
the order's Delivery Date (``commitment_date``), else its expected date. An order is on time
and in full when every ordered goods line was delivered in full by the end of its due day;
there is no tolerance. Service lines are not counted.

ROAS is net sales divided by the posted balance of the advertising expense accounts chosen
in the dashboard settings for the company.
"""
import math
from collections import defaultdict
from datetime import datetime, time, timedelta

import pytz

from odoo import fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools import float_compare
from odoo.tools.misc import format_date, formatLang

from .sales import INVOICE_TYPES
from .finance import DIRECT_COST, OPEN_TYPES

OTIF_KINDS = ('ok', 'not_full', 'late', 'both')
# Finance drawers and native screens shown from this section, under this section's keys.
FINANCE_KEYS = ('finance.account', 'finance.balance_sheet', 'finance.open_items', 'finance.pnl')


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_key_metrics(self, scope):
        """``currency``, ``net_sales``, ``gross_profit``, ``working_capital``, ``otif`` (None
        without Sales and Inventory) and ``roas``."""
        currency = scope['company'].currency_id
        net = self._key_net_sales(scope)
        cogs = self._key_cogs(scope)
        spend = self._key_ad_spend(scope)
        return {
            'currency': {'name': currency.name, 'symbol': currency.symbol,
                         'position': currency.position, 'digits': currency.decimal_places},
            'net_sales': net,
            'gross_profit': {'revenue': net['total'], 'cogs': cogs, 'gross_profit': net['total'] - cogs,
                             'percent': self._key_ratio(net['total'] - cogs, net['total'], 100)},
            'working_capital': self._key_working_capital(scope),
            'otif': self._key_otif(scope) if self._key_otif_ready() else None,
            'roas': {'sales': net['total'], 'spend': spend['total'], 'accounts': len(spend['accounts']),
                     'roas': self._key_ratio(net['total'], spend['total'])},
        }

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _key_ratio(part, whole, scale=1):
        return part / whole * scale if whole and math.isfinite(whole) else None

    def _key_scope(self, args):
        return self._period_scope('key_metrics', args.get('period') or 'month', args.get('date_from'),
                                  args.get('date_to'))

    def _key_period_args(self, args):
        return {key: args[key] for key in ('period', 'date_from', 'date_to') if args.get(key)}

    def _key_dates(self, scope):
        return [('date', '>=', fields.Date.to_string(scope['date_from'])),
                ('date', '<=', fields.Date.to_string(scope['date_to']))]

    def _key_period_label(self, scope):
        return '%s – %s' % (format_date(self.env, scope['date_from'], date_format='d MMM y'),
                            format_date(self.env, scope['date_to'], date_format='d MMM y'))

    def _key_rekey(self, value):
        """Finance drawer content with its keys under this section (``finance.x`` -> ``key_metrics.x``),
        so it opens whether or not the Finance section is shown for the company."""
        if isinstance(value, dict):
            result = {k: self._key_rekey(v) for k, v in value.items()}
            if result.get('key') in FINANCE_KEYS:
                result['key'] = 'key_metrics.' + result['key'].split('.', 1)[1]
            return result
        if isinstance(value, list):
            return [self._key_rekey(v) for v in value]
        return value

    # ------------------------------------------------------------------ net sales by channel

    def _key_sales_domain(self, scope):
        """Product lines of posted customer invoices and credit notes in the period."""
        return Domain([
            ('parent_state', '=', 'posted'), ('move_id.move_type', 'in', INVOICE_TYPES),
            ('display_type', '=', 'product'), ('company_id', 'in', scope['companies'].ids),
            *self._key_dates(scope),
        ])

    def _key_channels_ready(self):
        return 'sale_line_ids' in self.env['account.move.line']._fields and 'source_id' in self.env['sale.order']._fields \
            if 'sale.order' in self.env else False

    def _key_channel_domain(self, source_id):
        """Lines of the channel ``source_id`` (False: no sales order, or an order without a Source)."""
        if source_id:
            return Domain('sale_line_ids.order_id.source_id', '=', source_id)
        if not self._key_channels_ready():
            return Domain.TRUE
        return Domain('sale_line_ids', '=', False) | Domain('sale_line_ids.order_id.source_id', '=', False)

    def _key_split(self, scope, domain):
        """``(invoiced, credit notes)`` of ``domain``, untaxed, positive amounts."""
        invoiced = refunds = 0.0
        for company, move_type, balance in self.env['account.move.line']._read_group(
                domain, ['company_id', 'move_id.move_type'], ['balance:sum']):
            amount = -self._fin_convert(scope, balance, company, scope['date_to'])
            if move_type == 'out_refund':
                refunds -= amount
            else:
                invoiced += amount
        return invoiced, refunds

    def _key_net_sales(self, scope):
        """Total, invoiced and credit notes, and ``channels``: ``[{id, name, invoiced, refunds, net}]``,
        largest first, "No channel" last."""
        base = self._key_sales_domain(scope)
        invoiced, refunds = self._key_split(scope, base)
        channels = []
        if self._key_channels_ready():
            sources = [source for source, in self.env['sale.order']._read_group(
                [('source_id', '!=', False), ('order_line.invoice_lines', 'any', base)], ['source_id'])]
            for source in sources:
                inv, ref = self._key_split(scope, base & self._key_channel_domain(source.id))
                channels.append({'id': source.id, 'name': source.name, 'invoiced': inv, 'refunds': ref,
                                 'net': inv - ref})
            channels.sort(key=lambda c: (-c['net'], c['name']))
        # "No channel" is the rest, so the channels always add up to the total.
        rest_inv = invoiced - sum(c['invoiced'] for c in channels)
        rest_ref = refunds - sum(c['refunds'] for c in channels)
        currency = scope['company'].currency_id
        if not (currency.is_zero(rest_inv) and currency.is_zero(rest_ref)):
            channels.append({'id': False, 'name': self.env._('No channel'), 'invoiced': rest_inv, 'refunds': rest_ref,
                             'net': rest_inv - rest_ref})
        return {'total': invoiced - refunds, 'invoiced': invoiced, 'refunds': refunds, 'channels': channels,
                'by_source': self._key_channels_ready()}

    # ------------------------------------------------------------------ gross profit

    def _key_cogs_rows(self, scope):
        """``{account: cost}`` of the period on the Cost of Revenue accounts (costs positive)."""
        costs = defaultdict(float)
        for company, account, balance in self.env['account.move.line']._read_group(self._fin_domain(scope, [
                *self._key_dates(scope), ('account_id.account_type', 'in', DIRECT_COST)]),
                ['company_id', 'account_id'], ['balance:sum']):
            costs[account] += self._fin_convert(scope, balance, company, scope['date_to'])
        return costs

    def _key_cogs(self, scope):
        return sum(self._key_cogs_rows(scope).values())

    # ------------------------------------------------------------------ working capital

    def _key_inventory_ready(self):
        return 'product.product' in self.env and 'total_value' in self.env['product.product']._fields \
            and hasattr(self.env['product.product'], '_with_valuation_context')

    def _key_inventory_products(self, scope, company):
        """Valued products of ``company`` holding stock at the period's end, in that context
        (Odoo's stock valuation: ``total_value`` at the date, as the Inventory Valuation report)."""
        Product = self.env['product.product'].with_company(company).with_context(
            allowed_company_ids=company.ids, skip_kit_qty_available=True)._with_valuation_context()
        if scope['as_of'] < scope['today']:
            # End of the user's day, in UTC.
            end = self.env.tz.localize(datetime.combine(scope['as_of'] + timedelta(days=1), time.min))
            end = end.astimezone(pytz.utc).replace(tzinfo=None)
            Product = Product.with_context(at_date=end, to_date=end)
        domain = Domain(company._get_valuation_product_domain())
        held = Domain('qty_available', '!=', 0)
        if 'lot_valuated' in Product._fields:
            held |= Domain('lot_valuated', '=', True)
        return Product.search(domain & held)

    def _key_inventory(self, scope):
        """Inventory at cost at the period's end, or None without stock valuation."""
        if not self._key_inventory_ready():
            return None
        total = 0.0
        for company in scope['companies']:
            products = self._key_inventory_products(scope, company)
            total += self._fin_convert(scope, sum(products.mapped('total_value')), company, scope['as_of'])
        return total

    def _key_working_capital(self, scope):
        cash = self._fin_bank_cash(scope)['total']
        inventory = self._key_inventory(scope)
        receivables = self._fin_open_items(scope, 'receivables')['total']
        payables = self._fin_open_items(scope, 'payables')['total']
        return {'as_of': fields.Date.to_string(scope['as_of']), 'cash': cash, 'inventory': inventory,
                'receivables': receivables, 'payables': payables,
                'total': cash + (inventory or 0.0) + receivables - payables}

    # ------------------------------------------------------------------ OTIF

    def _key_otif_ready(self):
        return 'sale.order' in self.env and 'stock.move' in self.env \
            and 'sale_line_id' in self.env['stock.move']._fields

    def _key_goods_lines(self, order):
        return order.order_line.filtered(
            lambda line: line.product_id.type == 'consu' and not line.display_type and not line.is_downpayment
            and not line._is_delivery() and line.product_uom_qty > 0)

    def _key_due_day(self, order):
        when = order.commitment_date or order.expected_date
        return fields.Datetime.context_timestamp(self, when).date() if when else None

    def _key_otif_orders(self, scope):
        """``[(order, due day, kind)]`` of the orders due in the period whose due day has passed."""
        last = min(scope['date_to'], scope['today'] - timedelta(days=1))
        if last < scope['date_from']:
            return []
        Order, Line = self.env['sale.order'], self.env['sale.order.line']
        start, end = self._utc_bounds(scope['date_from'], last)
        base = Domain([('state', '=', 'sale'), ('company_id', 'in', scope['companies'].ids)])
        # Without a Delivery Date, the expected date is the order date plus the lines' lead time.
        lead = Line._read_group(Domain('order_id', 'any', base), [], ['customer_lead:max'])[0][0] or 0.0
        earliest = fields.Datetime.to_datetime(start) - timedelta(days=math.ceil(lead) + 1)
        orders = Order.search(base & (
            (Domain('commitment_date', '>=', start) & Domain('commitment_date', '<', end))
            | (Domain('commitment_date', '=', False) & Domain('date_order', '>=', earliest)
               & Domain('date_order', '<', end))), order='id')
        due = {}
        for order in orders:
            day = self._key_due_day(order)
            lines = self._key_goods_lines(order)
            if day and scope['date_from'] <= day <= last and lines:
                due[order] = (day, lines)
        if not due:
            return []
        lines = Line.union(*(lines for _day, lines in due.values()))
        delivered, on_time = defaultdict(float), defaultdict(float)
        late_moves = set()
        deadline = {}
        for order, (day, order_lines) in due.items():
            end_of_day = self.env.tz.localize(datetime.combine(day + timedelta(days=1), time.min))
            deadline[order.id] = end_of_day.astimezone(pytz.utc).replace(tzinfo=None)
        for move in self.env['stock.move'].search_fetch(
                [('sale_line_id', 'in', lines.ids), ('state', '=', 'done'), ('location_dest_usage', '=', 'customer')],
                ['sale_line_id', 'date', 'quantity', 'product_uom']):
            line = move.sale_line_id
            qty = move.product_uom._compute_quantity(move.quantity, line.product_uom_id, rounding_method='HALF-UP')
            delivered[line] += qty
            if move.date < deadline[line.order_id.id]:
                on_time[line] += qty
            else:
                late_moves.add(line.order_id.id)
        open_orders = {order.id for order, in self.env['stock.picking']._read_group(
            [('sale_id', 'in', [o.id for o in due]), ('state', 'not in', ('done', 'cancel')),
             ('picking_type_id.code', '=', 'outgoing')], ['sale_id'])} if 'sale_id' in self.env['stock.picking']._fields else set()
        digits = self.env['decimal.precision'].precision_get('Product Unit')
        full = lambda qty, line: float_compare(qty, line.product_uom_qty, precision_digits=digits) >= 0  # noqa: E731
        result = []
        for order, (day, order_lines) in due.items():
            if all(full(on_time[line], line) for line in order_lines):
                kind = 'ok'
            elif all(full(delivered[line], line) for line in order_lines):
                kind = 'late'
            elif order.id not in late_moves and order.id not in open_orders \
                    and any(delivered[line] > 0 for line in order_lines):
                # Delivered short, on time, and nothing left to deliver.
                kind = 'not_full'
            else:
                kind = 'both'
            result.append((order, day, kind))
        return result

    def _key_otif(self, scope):
        counts = dict.fromkeys(OTIF_KINDS, 0)
        for _order, _day, kind in self._key_otif_orders(scope):
            counts[kind] += 1
        due = sum(counts.values())
        return dict(counts, due=due, percent=self._key_ratio(counts['ok'], due, 100))

    # ------------------------------------------------------------------ ROAS

    def _key_ad_accounts(self, scope):
        return scope['companies'].executive_dashboard_ad_account_ids

    def _key_ad_spend(self, scope):
        """Posted balance of the advertising accounts in the period: ``{total, accounts: {account: spend}}``."""
        accounts = self._key_ad_accounts(scope)
        spend = defaultdict(float)
        if accounts:
            for company, account, balance in self.env['account.move.line']._read_group(self._fin_domain(scope, [
                    *self._key_dates(scope), ('account_id', 'in', accounts.ids)]),
                    ['company_id', 'account_id'], ['balance:sum']):
                spend[account] += self._fin_convert(scope, balance, company, scope['date_to'])
        for account in accounts:
            spend.setdefault(account, 0.0)
        return {'total': sum(spend.values()), 'accounts': spend}

    # ------------------------------------------------------------------ drawers

    def _key_money(self, scope, amount):
        return '%s %s' % (self._fin_format(amount), scope['company'].currency_id.name)

    def _key_source_arg(self, args):
        source_id = args.get('source_id')
        if source_id is False:
            return False
        if type(source_id) is not int or source_id <= 0 or not self._key_channels_ready():
            raise ValidationError(self.env._('Unknown detail.'))
        source = self.env['utm.source'].browse(source_id).exists()
        if not source:
            raise ValidationError(self.env._('Unknown detail.'))
        return source

    def _drawer_key_metrics_net_sales(self, args):
        scope, _ = self._key_scope(args), self.env._
        net = self._key_net_sales(scope)
        period = self._key_period_args(args)
        rows = [{'label': c['name'],
                 'sub': _('Invoiced %(invoiced)s · credit notes %(refunds)s',
                          invoiced=self._fin_format(c['invoiced']), refunds=self._fin_format(c['refunds'])),
                 'value': self._fin_format(c['net']),
                 'open': {'key': 'key_metrics.channel', 'args': dict(period, source_id=c['id']),
                          'crumb': _('Net sales by channel')}}
                for c in net['channels']]
        return {'title': _('Net sales by channel'),
                'sub': _('Excluding VAT · %s', self._key_period_label(scope)),
                'note': _('Posted customer invoices minus credit notes, untaxed, after discounts. '
                          'Channel = Source on the sales order.'),
                'rows': rows, 'total': {'label': _('Net sales'), 'value': self._key_money(scope, net['total'])},
                'action': {'key': 'key_metrics.lines', 'args': period}, 'dest': _('Journal Items')}

    def _key_lines_domain(self, scope, source):
        domain = self._key_sales_domain(scope)
        return domain if source is None else domain & self._key_channel_domain(source.id if source else False)

    def _drawer_key_metrics_channel(self, args):
        source = self._key_source_arg(args)
        scope, _ = self._key_scope(args), self.env._
        domain = self._key_lines_domain(scope, source)
        by_move = defaultdict(float)
        for company, move, balance in self.env['account.move.line']._read_group(
                domain, ['company_id', 'move_id'], ['balance:sum']):
            by_move[move] -= self._fin_convert(scope, balance, company, scope['date_to'])
        moves, more = self._drawer_page(sorted(by_move, key=lambda m: (-abs(by_move[m]), m.id)))
        period = self._key_period_args(args)
        rows = [{'label': move.name, 'sub': '%s · %s' % (move.partner_id.display_name or '',
                                                         format_date(self.env, move.date, date_format='d MMM y')),
                 'value': self._fin_format(by_move[move]),
                 'action': {'key': 'key_metrics.move', 'args': {'move_id': move.id}}} for move in moves]
        invoiced, refunds = self._key_split(scope, domain)
        name = source.name if source else _('No channel')
        return {'title': name, 'sub': _('Net sales · %s', self._key_period_label(scope)),
                'groups': [{'title': _('Summary'), 'rows': [
                    {'label': _('Invoiced (untaxed)'), 'value': self._fin_format(invoiced)},
                    {'label': _('Credit notes (untaxed)'), 'value': self._fin_format(-refunds)}]}],
                'note': False if source else _('Invoice lines without a sales order, or from an order without a Source.'),
                'rows_title': _('Invoices and credit notes'), 'rows': rows, 'more': more,
                'total': {'label': _('Net sales'), 'value': self._key_money(scope, invoiced - refunds)},
                'action': {'key': 'key_metrics.lines', 'args': dict(period, source_id=source.id if source else False)},
                'dest': _('Journal Items')}

    def _action_key_metrics_lines(self, args):
        scope = self._key_scope(args)
        source = self._key_source_arg(args) if 'source_id' in args else None
        return self._fin_items_action(self.env._('Net sales'), self._key_lines_domain(scope, source))

    def _key_move(self, args):
        move = self.env['account.move'].browse(self._positive_id(args, 'move_id')).exists()
        if not move or move.move_type not in INVOICE_TYPES:
            raise ValidationError(self.env._('Unknown detail.'))
        return self._check_company(move)

    def _check_key_metrics_move(self, args):
        return self._key_move(args)

    def _action_key_metrics_move(self, args):
        move = self._key_move(args)
        return self._window('account.action_move_out_invoice_type', move.name, 'account.move',
                            [('id', '=', move.id)], res_id=move.id)

    def _drawer_key_metrics_gross_profit(self, args):
        scope, _ = self._key_scope(args), self.env._
        net = self._key_net_sales(scope)['total']
        costs = self._key_cogs_rows(scope)
        cogs = sum(costs.values())
        period = self._key_period_args(args)
        currency = scope['company'].currency_id
        percent = self._key_ratio(net - cogs, net, 100)
        cost_rows = [{'label': account.name, 'sub': self._fin_code(account), 'value': self._fin_format(cost),
                      'action': {'key': 'key_metrics.account', 'args': dict(period, account_id=account.id)}}
                     for account, cost in sorted(costs.items(), key=lambda item: -abs(item[1]))
                     if not currency.is_zero(cost)]
        groups = [{'title': _('Calculation'), 'rows': [
            {'label': _('Net sales (excluding VAT)'), 'value': self._fin_format(net),
             'open': {'key': 'key_metrics.net_sales', 'args': period, 'crumb': _('Gross profit %')}},
            {'label': _('Cost of goods sold'), 'value': self._fin_format(-cogs)},
            {'label': _('Gross profit'), 'value': self._fin_format(net - cogs)}]}]
        if cost_rows:
            groups.append({'title': _('Cost of goods sold by account'), 'rows': cost_rows})
        return {'title': _('Gross profit %'), 'sub': self._key_period_label(scope),
                'note': _('One calculation on the company totals: (net sales - cost of goods sold) / net sales x 100. '
                          'Product or channel margins are never averaged.'),
                'groups': groups,
                'total': {'label': _('Gross profit %'),
                          'value': '%s%%' % self._key_pct(percent) if percent is not None else '—'},
                'action': {'key': 'key_metrics.pnl', 'args': period},
                'dest': _('Profit and Loss') if self._fin_report('account_reports.profit_and_loss') else _('Journal Items')}

    def _key_pct(self, value):
        return formatLang(self.env, value, digits=1)

    def _drawer_key_metrics_bank_cash(self, args):
        return self._key_rekey(self._drawer_finance_bank_cash(args))

    def _drawer_key_metrics_open_items(self, args):
        return self._key_rekey(self._drawer_finance_open_items(args))

    def _drawer_key_metrics_inventory(self, args):
        if not self._key_inventory_ready():
            raise AccessError(self.env._('This section is not available to you.'))
        scope, _ = self._key_scope(args), self.env._
        by_category = defaultdict(float)
        for company in scope['companies']:
            for product in self._key_inventory_products(scope, company):
                by_category[product.categ_id] += self._fin_convert(scope, product.total_value, company, scope['as_of'])
        currency = scope['company'].currency_id
        categories, more = self._drawer_page(sorted((c for c in by_category if not currency.is_zero(by_category[c])),
                                                    key=lambda c: (-by_category[c], c.id)))
        rows = [{'label': category.complete_name or _('No category'), 'value': self._fin_format(by_category[category])}
                for category in categories]
        today = scope['as_of'] >= scope['today']
        return {'title': _('Inventory at cost'), 'sub': '%s · %s' % (_('Stock valuation'), self._fin_as_of_label(scope)),
                'rows_title': _('By product category'), 'rows': rows, 'more': more,
                'note': False if today else _('The stock list shows today’s quantities and values.'),
                'total': {'label': _('Total'), 'value': self._key_money(scope, sum(by_category.values()))},
                'action': {'key': 'key_metrics.stock', 'args': {}}, 'dest': _('Stock')}

    def _action_key_metrics_stock(self, args):
        if 'stock.quant' not in self.env:
            raise ValidationError(self.env._('Unknown detail.'))
        action = self.env['stock.quant'].action_view_quants()
        action.update(name=self.env._('Stock'), target='current', domain=[
            ('location_id.usage', 'in', ('internal', 'transit')), ('company_id', 'in', self.env.companies.ids)])
        return action

    def _drawer_key_metrics_working_capital(self, args):
        scope, _ = self._key_scope(args), self.env._
        wc = self._key_working_capital(scope)
        period = self._key_period_args(args)
        crumb = _('Working capital')
        rows = [
            {'label': _('Available cash'), 'sub': _('Bank and Cash Accounts'), 'value': '+' + self._fin_format(wc['cash']),
             'open': {'key': 'key_metrics.bank_cash', 'args': period, 'crumb': crumb}},
        ]
        if wc['inventory'] is not None:
            rows.append({'label': _('Inventory at cost'), 'sub': _('Stock valuation'),
                         'value': '+' + self._fin_format(wc['inventory']),
                         'open': {'key': 'key_metrics.inventory', 'args': period, 'crumb': crumb}})
        rows += [
            {'label': _('Accounts receivable'), 'sub': _('Open customer invoices'),
             'value': '+' + self._fin_format(wc['receivables']),
             'open': {'key': 'key_metrics.open_items', 'args': dict(period, kind='receivables', view='aged'),
                      'crumb': crumb}},
            {'label': _('Accounts payable'), 'sub': _('Open vendor bills'), 'value': '−' + self._fin_format(wc['payables']),
             'open': {'key': 'key_metrics.open_items', 'args': dict(period, kind='payables', view='aged'),
                      'crumb': crumb}},
        ]
        return {'title': _('Working capital'), 'sub': self._fin_as_of_label(scope),
                'note': _('Available cash + inventory at cost + receivables - payables, at the end of the period.'),
                'rows': rows, 'total': {'label': _('Working capital'), 'value': self._key_money(scope, wc['total'])},
                # Only the Balance Sheet shows these figures together (no journal items fallback).
                'action': {'key': 'key_metrics.balance_sheet', 'args': period}
                if self._fin_report('account_reports.balance_sheet') else False,
                'dest': _('Balance Sheet')}

    def _drawer_key_metrics_otif(self, args):
        kind = args.get('kind')
        if not self._key_otif_ready() or (kind is not None and kind not in OTIF_KINDS):
            raise ValidationError(self.env._('Unknown detail.'))
        scope, _ = self._key_scope(args), self.env._
        orders = self._key_otif_orders(scope)
        labels = {'ok': _('On time and in full'), 'not_full': _('On time, not in full'),
                  'late': _('In full, late'), 'both': _('Late and not in full')}
        counts = {k: sum(1 for _o, _d, x in orders if x == k) for k in OTIF_KINDS}
        due = len(orders)
        percent = self._key_ratio(counts['ok'], due, 100)
        period = self._key_period_args(args)
        summary = [{'label': labels[k], 'value': str(counts[k]),
                    **({'open': {'key': 'key_metrics.otif', 'args': dict(period, kind=k), 'crumb': _('OTIF')}}
                       if counts[k] and k != kind else {})} for k in OTIF_KINDS]
        shown = sorted((o for o in orders if (o[2] == kind if kind else o[2] != 'ok')), key=lambda o: (o[1], o[0].id))
        shown, more = self._drawer_page(shown)
        rows = [{'label': order.name, 'sub': '%s · %s' % (order.partner_id.display_name or '',
                                                          _('due %s', format_date(self.env, day, date_format='d MMM y'))),
                 'value': labels[k], 'action': {'key': 'key_metrics.order', 'args': {'order_id': order.id}}}
                for order, day, k in shown]
        title = labels[kind] if kind else _('OTIF')
        return {'title': title, 'sub': self._key_period_label(scope),
                'note': _('OTIF % = (orders completed on time and in full / total orders due) x 100. Due = Delivery '
                          'Date, else expected date, in the period and passed. No tolerance; service lines are not '
                          'counted.'),
                'groups': [] if kind else [{'title': _('Orders due · %s', due), 'rows': summary}],
                'rows_title': _('Orders') if kind else _('Orders that missed'), 'rows': rows, 'more': more,
                'total': {'label': _('OTIF'), 'value': '%s%%' % self._key_pct(percent)} if percent is not None
                else False,
                'action': {'key': 'key_metrics.orders', 'args': dict(period, **({'kind': kind} if kind else {}))},
                'dest': _('Sales Orders')}

    def _key_order(self, args):
        if not self._key_otif_ready():
            raise ValidationError(self.env._('Unknown detail.'))
        order = self.env['sale.order'].browse(self._positive_id(args, 'order_id')).exists()
        if not order:
            raise ValidationError(self.env._('Unknown detail.'))
        return self._check_company(order)

    def _check_key_metrics_order(self, args):
        return self._key_order(args)

    def _action_key_metrics_order(self, args):
        order = self._key_order(args)
        return self._window('sale.action_orders', order.name, 'sale.order', [('id', '=', order.id)], res_id=order.id)

    def _action_key_metrics_orders(self, args):
        kind = args.get('kind')
        if not self._key_otif_ready() or (kind is not None and kind not in OTIF_KINDS):
            raise ValidationError(self.env._('Unknown detail.'))
        orders = [o.id for o, _d, k in self._key_otif_orders(self._key_scope(args)) if not kind or k == kind]
        return self._window('sale.action_orders', self.env._('Orders due'), 'sale.order', [('id', 'in', orders)])

    def _drawer_key_metrics_roas(self, args):
        scope, _ = self._key_scope(args), self.env._
        net = self._key_net_sales(scope)['total']
        spend = self._key_ad_spend(scope)
        period = self._key_period_args(args)
        roas = self._key_ratio(net, spend['total'])
        rows = [{'label': account.name, 'sub': self._fin_code(account), 'value': self._fin_format(amount),
                 'action': {'key': 'key_metrics.account', 'args': dict(period, account_id=account.id)}}
                for account, amount in sorted(spend['accounts'].items(), key=lambda item: (-item[1], item[0].id))]
        return {'title': _('ROAS'), 'sub': self._key_period_label(scope),
                'note': _('Net sales / ad spend. Ad spend = posted entries on the advertising expense accounts chosen '
                          'in Executive Dashboard settings.') if rows else
                _('No advertising accounts are chosen. A system administrator chooses them in Executive Dashboard '
                  'settings.'),
                'groups': [{'title': _('Calculation'), 'rows': [
                    {'label': _('Net sales (excluding VAT)'), 'value': self._fin_format(net),
                     'open': {'key': 'key_metrics.net_sales', 'args': period, 'crumb': _('ROAS')}},
                    {'label': _('Ad spend'), 'value': self._fin_format(spend['total'])}]}],
                'rows_title': _('Advertising accounts'), 'rows': rows,
                'total': {'label': _('ROAS'), 'value': ('%s×\u200e' % formatLang(self.env, roas, digits=2)) if roas is not None
                          else '—'}}

    # ------------------------------------------------------------------ native screens of Finance figures

    def _check_key_metrics_account(self, args):
        account = self._fin_account(args)
        if account.account_type not in ('asset_cash', *OPEN_TYPES.values(), *DIRECT_COST) \
                and account not in self._key_ad_accounts(self._key_scope(args)):
            raise ValidationError(self.env._('Unknown detail.'))
        return account

    def _action_key_metrics_account(self, args):
        account = self._check_key_metrics_account(args)
        return self._fin_account_target(account, self._key_scope(args))[0]

    def _action_key_metrics_balance_sheet(self, args):
        return self._action_finance_balance_sheet(args)

    def _action_key_metrics_open_items(self, args):
        return self._action_finance_open_items(args)

    def _action_key_metrics_pnl(self, args):
        return self._action_finance_pnl(args)
