"""Key metrics: net sales by channel, gross profit %, working capital, OTIF and ROAS.

Net sales are the product lines of posted customer invoices and credit notes in the period
(accounting date), untaxed, after line discounts: invoices minus credit notes (returns and
corrections), plus the sales lines of closed POS sessions (orders without an invoice; an
invoiced POS order is in its invoice). Cancelled orders and invoices are never posted, so
never counted. The channel is the Source (``source_id``) of the sales order an invoice line
comes from; POS sessions, and invoices of POS orders without a Source, are "Point of Sale";
other lines without a sales order, or whose order has no Source, are "No channel".

Gross profit % is one calculation on the company totals of the period, from the Profit and
Loss (the same revenue and gross profit as Finance): (revenue - cost of goods sold) /
revenue x 100, where revenue is the Income accounts and cost of goods sold the Cost of
Revenue accounts (``expense_direct_cost``). Both sides cover every posting, so income posted
without an invoice (journal entries) and its costs are on both sides; net sales would leave
that income out but not its costs. Margins of products or channels are never averaged.

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
from odoo.tools import SQL, float_compare
from odoo.tools.misc import format_date, formatLang

from .sales import INVOICE_TYPES
from .finance import DIRECT_COST, INCOME, OPEN_TYPES

OTIF_KINDS = ('ok', 'not_full', 'late', 'both')
# Channel key of POS sales (other channels are a ``utm.source`` id, or False for "No channel").
POS = 'pos'
# Finance drawers and native screens shown from this section, under this section's keys.
FINANCE_KEYS = ('finance.account', 'finance.balance_sheet', 'finance.open_items', 'finance.pnl')


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_key_metrics(self, scope):
        """``currency``, ``net_sales``, ``gross_profit``, ``working_capital``, ``otif`` (None
        without Sales and Inventory), ``roas`` and ``checks``."""
        currency = scope['company'].currency_id
        net = self._key_net_sales(scope)
        pnl = self._fin_pnl(scope)
        spend = self._key_ad_spend(scope)
        bank = self._fin_bank_cash(scope)
        open_items = {kind: self._fin_open_items(scope, kind) for kind in OPEN_TYPES}
        return {
            'currency': {'name': currency.name, 'symbol': currency.symbol,
                         'position': currency.position, 'digits': currency.decimal_places},
            'net_sales': net,
            'gross_profit': self._key_gross_profit(pnl, net['total']),
            'working_capital': self._key_working_capital(scope, bank, open_items),
            'otif': self._key_otif(scope) if self._key_otif_ready() else None,
            'roas': {'sales': net['total'], 'spend': spend['total'], 'accounts': len(spend['accounts']),
                     'roas': self._key_ratio(net['total'], spend['total'])},
            'checks': self._fin_checks(scope, 'key_metrics', pnl, bank, open_items),
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
        """Product lines of posted customer invoices and credit notes in the period, and the
        sales lines of closed POS sessions."""
        sales = Domain([('move_id.move_type', 'in', INVOICE_TYPES), ('display_type', '=', 'product')])
        if self._key_pos_ready():
            sales |= self._key_pos_session_lines()
        return Domain([('parent_state', '=', 'posted'), ('company_id', 'in', scope['companies'].ids),
                       *self._key_dates(scope)]) & sales

    def _key_pos_ready(self):
        return 'pos_session_ids' in self.env['account.move']._fields and 'pos.order' in self.env

    def _key_pos_session_lines(self):
        """Sales lines of POS session entries: orders without an invoice, sales and refunds apart."""
        return Domain([('move_id.pos_session_ids', '!=', False), ('account_id.account_type', 'in', INCOME),
                       ('tax_line_id', '=', False)])

    def _key_channels_ready(self):
        return 'sale_line_ids' in self.env['account.move.line']._fields and 'source_id' in self.env['sale.order']._fields \
            if 'sale.order' in self.env else False

    def _key_channel_domain(self, source_id):
        """Lines of the channel ``source_id``: a Source id, ``POS``, or False (no sales order, or an
        order without a Source, and not from the Point of Sale)."""
        if source_id and source_id != POS:
            return Domain('sale_line_ids.order_id.source_id', '=', source_id)
        unsourced = Domain('sale_line_ids', '=', False) | Domain('sale_line_ids.order_id.source_id', '=', False) \
            if self._key_channels_ready() else Domain.TRUE
        pos = self._key_pos_session_lines() | (Domain('move_id.pos_order_ids', '!=', False) & unsourced) \
            if self._key_pos_ready() else Domain.FALSE
        return pos if source_id == POS else unsourced & ~pos

    def _key_channel_sums(self, scope, by_move=False):
        """``{(company, move_type, channel, move_id or None): balance}`` of the period's sales lines, in one
        query; ``channel`` is a Source id, ``POS`` or False. Each invoice line belongs to exactly one channel:
        the Source of the order of its first sales order line (an invoice line rarely comes from several
        orders), else Point of Sale when the line comes from a POS session or a POS order's invoice. A POS
        session's refund lines (debits) count as credit notes."""
        Line = self.env['account.move.line']
        query = Line._search(self._key_sales_domain(scope))
        self.env.flush_all()
        source = SQL('so.source_id') if self._key_channels_ready() else SQL('NULL::int')
        # Only POS session lines are entries among the sales lines.
        pos = SQL("(am.move_type = 'entry' OR EXISTS (SELECT 1 FROM pos_order po WHERE po.account_move = am.id))") \
            if self._key_pos_ready() else SQL('FALSE')
        joins = SQL("""
            LEFT JOIN LATERAL (SELECT MIN(rel.order_line_id) AS line_id FROM sale_order_line_invoice_rel rel
                               WHERE rel.invoice_line_id = aml.id) first_line ON TRUE
            LEFT JOIN sale_order_line sol ON sol.id = first_line.line_id
            LEFT JOIN sale_order so ON so.id = sol.order_id""") if self._key_channels_ready() else SQL('')
        self.env.cr.execute(SQL("""
            SELECT aml.company_id,
                   CASE WHEN am.move_type = 'entry' AND aml.balance > 0 THEN 'out_refund' ELSE am.move_type END,
                   %(source)s, %(pos)s, %(move)s, SUM(aml.balance)
              FROM account_move_line aml
              JOIN account_move am ON am.id = aml.move_id
              %(joins)s
             WHERE aml.id IN %(ids)s
          GROUP BY 1, 2, 3, 4, 5""", source=source, pos=pos, move=SQL('aml.move_id') if by_move else SQL('NULL::int'),
                                joins=joins, ids=query.subselect()))
        sums = defaultdict(float)
        for company, move_type, source_id, is_pos, move_id, balance in self.env.cr.fetchall():
            sums[company, move_type, source_id or (POS if is_pos else False), move_id] += balance
        return sums

    def _key_signed(self, scope, company_id, move_type, balance):
        """``(invoiced, credit note)`` part of a balance, positive, in the dashboard currency."""
        amount = -self._fin_convert(scope, balance, self.env['res.company'].browse(company_id), scope['date_to'])
        return (0.0, -amount) if move_type == 'out_refund' else (amount, 0.0)

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

    def _key_total(self, scope):
        invoiced, refunds = self._key_split(scope, self._key_sales_domain(scope))
        return invoiced - refunds

    def _key_net_sales(self, scope):
        """Total, invoiced and credit notes, and ``channels``: ``[{id, name, invoiced, refunds, net}]``,
        largest first, "No channel" last."""
        sums = defaultdict(lambda: [0.0, 0.0])
        for (company_id, move_type, source_id, _move), balance in self._key_channel_sums(scope).items():
            inv, ref = self._key_signed(scope, company_id, move_type, balance)
            sums[source_id][0] += inv
            sums[source_id][1] += ref
        sources = self.env['utm.source'].browse([s for s in sums if s and s != POS]) \
            if self._key_channels_ready() else ()
        names = {source.id: source.name for source in sources}
        if POS in sums:
            names[POS] = self.env._('Point of Sale')
        channels = sorted(({'id': key, 'name': name, 'invoiced': sums[key][0], 'refunds': sums[key][1],
                            'net': sums[key][0] - sums[key][1]} for key, name in names.items()),
                          key=lambda c: (-c['net'], c['name']))
        if False in sums:
            channels.append({'id': False, 'name': self.env._('No channel'), 'invoiced': sums[False][0],
                             'refunds': sums[False][1], 'net': sums[False][0] - sums[False][1]})
        invoiced = sum(c['invoiced'] for c in channels)
        refunds = sum(c['refunds'] for c in channels)
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

    def _key_gross_profit(self, pnl, net_sales):
        """Gross profit % from the Profit and Loss figures (Finance's ``_fin_pnl``), with net sales for comparison."""
        revenue, gross = pnl['revenue'], pnl['gross_profit']
        return {'revenue': revenue, 'cogs': revenue - gross, 'gross_profit': gross,
                'percent': self._key_ratio(gross, revenue, 100), 'net_sales': net_sales}

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
            # A date, as the Inventory Valuation report passes it (Odoo takes the end of that day).
            Product = Product.with_context(at_date=scope['as_of'], to_date=scope['as_of'])
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

    def _key_working_capital(self, scope, bank=None, open_items=None):
        """Working capital at the period's end; ``bank`` and ``open_items`` are the Finance
        figures when the caller already has them."""
        bank = bank or self._fin_bank_cash(scope)
        open_items = open_items or {kind: self._fin_open_items(scope, kind) for kind in OPEN_TYPES}
        cash = bank['total']
        inventory = self._key_inventory(scope)
        receivables = open_items['receivables']['total']
        payables = open_items['payables']['total']
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
        kits, late_kits = set(), set()
        for move in self.env['stock.move'].search_fetch(
                [('sale_line_id', 'in', lines.ids), ('state', '=', 'done'), ('location_dest_usage', '=', 'customer')],
                ['sale_line_id', 'product_id', 'date', 'quantity', 'product_uom']):
            line = move.sale_line_id
            late = move.date >= deadline[line.order_id.id]
            if late:
                late_moves.add(line.order_id.id)
            if move.product_id != line.product_id:
                # A kit's components: the line's own delivered quantity counts (Manufacturing computes it).
                kits.add(line)
                if late:
                    late_kits.add(line)
                continue
            qty = move.product_uom._compute_quantity(move.quantity, line.product_uom_id, rounding_method='HALF-UP')
            delivered[line] += qty
            if not late:
                on_time[line] += qty
        for line in kits:
            delivered[line] = line.qty_delivered
            on_time[line] = 0.0 if line in late_kits else line.qty_delivered
        # Deliveries still to do (any route to the customer, dropship included).
        open_orders = {line.order_id.id for line, in self.env['stock.move']._read_group(
            [('sale_line_id', 'in', lines.ids), ('state', 'not in', ('done', 'cancel')),
             ('location_dest_usage', '=', 'customer')], ['sale_line_id'])}
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
        """The channel argument: False ("No channel"), ``POS``, or an existing Source."""
        source_id = args.get('source_id')
        if source_id is False or (source_id == POS and self._key_pos_ready()):
            return source_id
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

    @staticmethod
    def _key_channel_key(source):
        """Channel key of a ``_key_source_arg`` result."""
        return source if source in (False, POS) else source.id

    def _key_lines_domain(self, scope, source):
        domain = self._key_sales_domain(scope)
        return domain if source is None else domain & self._key_channel_domain(self._key_channel_key(source))

    def _drawer_key_metrics_channel(self, args):
        source = self._key_source_arg(args)
        key = self._key_channel_key(source)
        scope, _ = self._key_scope(args), self.env._
        by_move = defaultdict(float)
        invoiced = refunds = 0.0
        for (company_id, move_type, source_id, move_id), balance in self._key_channel_sums(scope, by_move=True).items():
            if source_id == key:
                inv, ref = self._key_signed(scope, company_id, move_type, balance)
                by_move[self.env['account.move'].browse(move_id)] += inv - ref
                invoiced += inv
                refunds += ref
        moves, more = self._drawer_page(sorted(by_move, key=lambda m: (-abs(by_move[m]), m.id)))
        period = self._key_period_args(args)
        rows = [{'label': move.name, 'sub': '%s · %s' % (move.partner_id.display_name or '',
                                                         format_date(self.env, move.date, date_format='d MMM y')),
                 'value': self._fin_format(by_move[move]),
                 'action': {'key': 'key_metrics.move', 'args': {'move_id': move.id}}} for move in moves]
        if key == POS:
            name, note = _('Point of Sale'), _('Closed POS sessions (orders without an invoice) and invoices of POS '
                                               'orders; refunds count as credit notes.')
        elif source:
            name, note = source.name, False
        else:
            name, note = _('No channel'), _('Invoice lines without a sales order, or from an order without a Source.')
        return {'title': name, 'sub': _('Net sales · %s', self._key_period_label(scope)),
                'groups': [{'title': _('Summary'), 'rows': [
                    {'label': _('Invoiced (untaxed)'), 'value': self._fin_format(invoiced)},
                    {'label': _('Credit notes (untaxed)'), 'value': self._fin_format(-refunds)}]}],
                'note': note,
                'rows_title': _('Invoices and credit notes'), 'rows': rows, 'more': more,
                'total': {'label': _('Net sales'), 'value': self._key_money(scope, invoiced - refunds)},
                'action': {'key': 'key_metrics.lines', 'args': dict(period, source_id=key)},
                'dest': _('Journal Items')}

    def _action_key_metrics_lines(self, args):
        scope = self._key_scope(args)
        source = self._key_source_arg(args) if 'source_id' in args else None
        return self._fin_items_action(self.env._('Net sales'), self._key_lines_domain(scope, source))

    def _key_move(self, args):
        move = self.env['account.move'].browse(self._positive_id(args, 'move_id')).exists()
        pos_session = self._key_pos_ready() and move.pos_session_ids
        if not move or (move.move_type not in INVOICE_TYPES and not pos_session):
            raise ValidationError(self.env._('Unknown detail.'))
        return self._check_company(move)

    def _check_key_metrics_move(self, args):
        return self._key_move(args)

    def _action_key_metrics_move(self, args):
        move = self._key_move(args)
        xmlid = 'account.action_move_out_invoice_type' if move.move_type in INVOICE_TYPES \
            else 'account.action_move_journal_line'
        return self._window(xmlid, move.name, 'account.move', [('id', '=', move.id)], res_id=move.id)

    def _drawer_key_metrics_gross_profit(self, args):
        scope, _ = self._key_scope(args), self.env._
        gp = self._key_gross_profit(self._fin_pnl(scope), self._key_total(scope))
        costs = self._key_cogs_rows(scope)
        period = self._key_period_args(args)
        currency = scope['company'].currency_id
        crumb = _('Gross profit %')
        cost_rows = [{'label': account.name, 'sub': self._fin_code(account), 'value': self._fin_format(cost),
                      'action': {'key': 'key_metrics.account', 'args': dict(period, account_id=account.id)}}
                     for account, cost in sorted(costs.items(), key=lambda item: -abs(item[1]))
                     if not currency.is_zero(cost)]
        groups = [{'title': _('Calculation'), 'rows': [
            {'label': _('Revenue (all income accounts)'), 'value': self._fin_format(gp['revenue']),
             'open': {'key': 'key_metrics.revenue', 'args': period, 'crumb': crumb}},
            {'label': _('Cost of goods sold'), 'value': self._fin_format(-gp['cogs'])},
            {'label': _('Gross profit'), 'value': self._fin_format(gp['gross_profit'])}]}]
        if cost_rows:
            groups.append({'title': _('Cost of goods sold by account'), 'rows': cost_rows})
        groups.append({'title': _('For comparison'), 'rows': [
            {'label': _('Net sales (invoices and POS)'), 'value': self._fin_format(gp['net_sales']),
             'open': {'key': 'key_metrics.net_sales', 'args': period, 'crumb': crumb}}]})
        note = _('One calculation on the company totals of the Profit and Loss: (revenue - cost of goods sold) / '
                 'revenue x 100. Product or channel margins are never averaged.')
        if abs(gp['revenue'] - gp['net_sales']) >= 1:
            note = '%s %s' % (note, _('Revenue differs from net sales by %(amount)s %(currency)s, for example income '
                                      'posted by journal entry, or invoice lines on accounts other than Income.',
                                      amount=self._fin_format(gp['revenue'] - gp['net_sales']), currency=currency.name))
        if abs(sum(costs.values()) - gp['cogs']) >= 1:
            note = '%s %s' % (note, _('The Profit and Loss report gives %(amount)s %(currency)s for the cost of goods '
                                      'sold; the accounts above add up to their posted entries.',
                                      amount=self._fin_format(gp['cogs']), currency=currency.name))
        percent = gp['percent']
        return {'title': _('Gross profit %'), 'sub': self._key_period_label(scope),
                'note': note,
                'groups': groups,
                'total': {'label': _('Gross profit %'),
                          'value': '%s%%' % self._key_pct(percent) if percent is not None else '—'},
                'action': {'key': 'key_metrics.pnl', 'args': period},
                'dest': _('Profit and Loss') if self._fin_report('account_reports.profit_and_loss') else _('Journal Items')}

    def _key_pct(self, value):
        return formatLang(self.env, value, digits=1)

    def _drawer_key_metrics_revenue(self, args):
        """Finance's revenue panel (income accounts with their totals) under this section's keys."""
        return self._key_rekey(self._drawer_finance_profit(dict(args, figure='revenue')))

    def _drawer_key_metrics_bank_cash(self, args):
        return self._key_rekey(self.with_context(ed_account_key='key_metrics.account')._drawer_finance_bank_cash(args))

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
        # The plain quants list (``action_view_quants`` would also merge quants).
        return self._window('stock.stock_quant_action', self.env._('Stock'), 'stock.quant', [
            ('location_id.usage', 'in', ('internal', 'transit')), ('company_id', 'in', self.env.companies.ids)])

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
        net = self._key_total(scope)
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
        if account.account_type not in ('asset_cash', *OPEN_TYPES.values(), *INCOME, *DIRECT_COST) \
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
