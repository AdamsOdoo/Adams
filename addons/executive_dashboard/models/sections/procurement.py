"""Procurement: purchases confirmed, approvals, late receipts, open value, suppliers, months.

Purchases confirmed are purchase orders in the Purchase Order state (``state = 'purchase'``)
confirmed in the period (``date_approve``), untaxed, converted from the order currency.
To approve is ``state = 'to approve'``. Late receipts are incoming transfers scheduled before
today and not done or cancelled (Inventory's own "Late" filter, see ``inventory.py``). The
open purchase value is what confirmed orders still have to receive (``purchase_stock``).

Every total is one grouped query (``_read_group``); filtered on the user's current companies.
"""
from collections import defaultdict

from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.tools.misc import format_date, formatLang

TREND_MONTHS = 12
TOP_ROWS = 5
PANEL_ROWS = 6
DRAWER_ROWS = 25


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_procurement(self, scope):
        """Procurement widgets: ``currency``, ``kpis``, ``approve``, ``late``, ``suppliers``, ``trend``;
        a widget whose app is missing is ``None``."""
        currency = scope['company'].currency_id
        receipts = self._sal_can_read('stock.picking')
        late = self._inv_pickings_summary(scope, 'incoming', 'late', PANEL_ROWS) if receipts else None
        return {
            'currency': {'name': currency.name, 'symbol': currency.symbol,
                         'position': currency.position, 'digits': currency.decimal_places},
            'kpis': {
                'purchases': self._pro_orders_kpi(scope, self._pro_confirmed_domain(scope)),
                'approve': self._pro_orders_kpi(scope, self._pro_approve_domain(scope)),
                'late': {'count': late['count'], 'partners': late['partners']} if late else None,
                'open': self._pro_open_value(scope),
            },
            'approve': self._pro_approve_rows(scope),
            'late': late,
            'suppliers': self._pro_suppliers(scope),
            'trend': self._pro_trend(scope),
        }

    # ------------------------------------------------------------------ domains

    def _pro_scope(self, args):
        return self._period_scope('procurement', args.get('period') or 'month',
                                  args.get('date_from'), args.get('date_to'))

    def _pro_confirmed_domain(self, scope, date_from=None, date_to=None):
        bounds = {'date_from': date_from or scope['date_from'], 'date_to': date_to or scope['date_to']}
        return Domain([('state', '=', 'purchase'), ('company_id', 'in', scope['companies'].ids),
                       *self._in_period('date_approve', bounds)])

    def _pro_approve_domain(self, scope):
        return Domain([('state', '=', 'to approve'), ('company_id', 'in', scope['companies'].ids)])

    def _pro_open_domain(self, scope):
        """Confirmed orders not fully received; ``None`` without ``purchase_stock`` (no receipts)."""
        if 'receipt_status' not in self.env['purchase.order']._fields:
            return None
        return Domain([('state', '=', 'purchase'), ('receipt_status', 'in', ('pending', 'partial')),
                       ('company_id', 'in', scope['companies'].ids)])

    # ------------------------------------------------------------------ figures

    def _pro_orders_kpi(self, scope, domain):
        rows = self.env['purchase.order']._read_group(
            domain, ['currency_id', 'company_id'], ['amount_untaxed:sum', '__count'])
        day = min(scope['date_to'], scope['today'])
        return {'amount': self._money(scope, [(cur, company, amount) for cur, company, amount, _c in rows], day),
                'count': sum(count for *_r, count in rows)}

    def _pro_open_value(self, scope):
        """Untaxed value still to receive on confirmed orders: each line's subtotal times its
        share not yet received. Only orders not fully received are read."""
        domain = self._pro_open_domain(scope)
        if domain is None:
            return None
        lines = self.env['purchase.order.line'].search_fetch(
            [('order_id', 'any', domain), ('display_type', '=', False), ('product_qty', '>', 0)],
            ['price_subtotal', 'product_qty', 'qty_received', 'currency_id', 'company_id'])
        rows = defaultdict(float)
        for line in lines:
            left = max(line.product_qty - line.qty_received, 0.0) / line.product_qty
            rows[line.currency_id, line.company_id] += line.price_subtotal * left
        return {'amount': self._money(scope, [(cur, company, amount) for (cur, company), amount in rows.items()],
                                      scope['today']),
                'count': self.env['purchase.order'].search_count(domain)}

    def _pro_order_row(self, order):
        return {'id': order.id, 'name': order.name, 'supplier': order.partner_id.display_name,
                'amount': order.amount_untaxed, 'currency': order.currency_id.name,
                'date': fields.Date.to_string(fields.Datetime.context_timestamp(self, order.date_order))}

    def _pro_approve_rows(self, scope):
        """Orders waiting for approval, oldest order date first."""
        PurchaseOrder = self.env['purchase.order']
        domain = self._pro_approve_domain(scope)
        orders = PurchaseOrder.search(domain, order='date_order asc, id asc', limit=PANEL_ROWS)
        return {'rows': [self._pro_order_row(order) for order in orders], 'count': PurchaseOrder.search_count(domain)}

    def _pro_ranked_suppliers(self, scope, domain, limit):
        """``[(partner, amount, count)]`` by untaxed value, converted from each order's currency."""
        totals, counts = defaultdict(float), defaultdict(int)
        day = min(scope['date_to'], scope['today'])
        for partner, currency, company, amount, count in self.env['purchase.order']._read_group(
                domain, ['partner_id', 'currency_id', 'company_id'], ['amount_untaxed:sum', '__count']):
            totals[partner] += self._money(scope, [(currency, company, amount)], day)
            counts[partner] += count
        return [(partner, totals[partner], counts[partner])
                for partner in sorted(totals, key=lambda p: (-totals[p], p.id))[:limit]]

    def _pro_suppliers(self, scope, limit=TOP_ROWS):
        """Suppliers by purchases confirmed in the period, the ``limit`` first (every one when None)."""
        return [{'id': partner.id, 'name': partner.display_name, 'amount': amount, 'count': count}
                for partner, amount, count in self._pro_ranked_suppliers(
                    scope, self._pro_confirmed_domain(scope), limit)]

    def _pro_trend(self, scope):
        """Purchases confirmed in each of the 12 months ending with the period's last month."""
        end = scope['date_to']
        start = end.replace(day=1) - relativedelta(months=TREND_MONTHS - 1)
        by_month = defaultdict(float)
        for currency, company, month, amount in self.env['purchase.order']._read_group(
                self._pro_confirmed_domain(scope, start, end), ['currency_id', 'company_id', 'date_approve:month'],
                ['amount_untaxed:sum']):
            month = fields.Date.to_date(month)
            day = min(month + relativedelta(months=1, days=-1), end, scope['today'])
            by_month[month] += self._money(scope, [(currency, company, amount)], day)
        months = [start + relativedelta(months=i) for i in range(TREND_MONTHS)]
        return [{'month': fields.Date.to_string(m), 'amount': by_month[m]} for m in months]

    # ------------------------------------------------------------------ drawers

    def _pro_format(self, amount):
        return formatLang(self.env, amount, digits=0)

    def _pro_list(self, args):
        """Order lists behind the figures: ``(title, domain, action xml id, destination)``."""
        kind = args.get('kind')
        _ = self.env._
        if kind == 'purchases':
            return (_('Purchases confirmed'), self._pro_confirmed_domain(self._pro_scope(args)),
                    'purchase.purchase_form_action', _('Purchase Orders'))
        scope = self._period_scope('procurement', 'month')
        if kind == 'approve':
            return (_('Waiting for approval'), self._pro_approve_domain(scope), 'purchase.purchase_rfq',
                    _('Requests for Quotation · To Approve'))
        if kind == 'open':
            domain = self._pro_open_domain(scope)
            if domain is not None:
                return (_('Open purchase value'), domain, 'purchase.purchase_form_action',
                        _('Purchase Orders · not fully received'))
        raise ValidationError(_('Unknown detail.'))

    def _pro_order_rows(self, orders, crumb):
        return [{'label': order.name,
                 'sub': ' · '.join(filter(None, [order.partner_id.display_name, format_date(
                     self.env, fields.Datetime.context_timestamp(self, order.date_approve or order.date_order))])),
                 'value': '%s %s' % (self._pro_format(order.amount_untaxed), order.currency_id.name),
                 'open': {'key': 'procurement.order', 'args': {'order_id': order.id}, 'crumb': crumb}}
                for order in orders]

    def _drawer_procurement_orders(self, args):
        title, domain, _xmlid, dest = self._pro_list(args)
        _ = self.env._
        PurchaseOrder = self.env['purchase.order']
        oldest = args.get('kind') == 'approve'
        orders, more = self._sal_search_page('purchase.order', domain, 'date_order asc, id asc' if oldest else
                                             'date_approve desc, id desc')
        count = more['count'] if more else len(orders)
        total = self._pro_orders_kpi(self._pro_scope(args) if args.get('kind') == 'purchases'
                                     else self._period_scope('procurement', 'month'), domain)
        return {'title': title, 'sub': _('%s orders', count), 'rows': self._pro_order_rows(orders, title), 'more': more,
                'total': {'label': _('Total · untaxed'), 'value': '%s %s' % (
                    self._pro_format(total['amount']), self.env.company.currency_id.name)},
                'action': {'key': 'procurement.orders', 'args': args}, 'dest': dest}

    def _action_procurement_orders(self, args):
        title, domain, xmlid, _dest = self._pro_list(args)
        return self._window(xmlid, title, 'purchase.order', domain)

    def _drawer_procurement_suppliers(self, args):
        """'View all' of Top suppliers by purchase value: every supplier with purchases confirmed in the period."""
        scope, _ = self._pro_scope(args), self.env._
        title, period = _('Top suppliers by purchase value'), self._fin_period_args(args)
        suppliers = self._pro_suppliers(scope, None)
        shown, more = self._drawer_page(suppliers)
        return {'title': title, 'sub': _('Purchases confirmed in the period'), 'more': more,
                'rows': [{'label': s['name'], 'sub': _('%s orders', s['count']), 'value': self._pro_format(s['amount']),
                          'open': {'key': 'procurement.supplier', 'args': dict(period, partner_id=s['id']),
                                   'crumb': title}} for s in shown],
                'total': {'label': _('Total · untaxed'), 'value': '%s %s' % (
                    self._pro_format(sum(s['amount'] for s in suppliers)), scope['company'].currency_id.name)},
                'action': {'key': 'procurement.orders', 'args': dict(period, kind='purchases')},
                'dest': _('Purchase Orders')}

    def _pro_supplier_domain(self, args):
        scope = self._pro_scope(args)
        partner_id = self._positive_id(args, 'partner_id')
        return scope, self._pro_confirmed_domain(scope) & Domain('partner_id', '=', partner_id)

    def _drawer_procurement_supplier(self, args):
        scope, domain = self._pro_supplier_domain(args)
        _ = self.env._
        partner = self.env['res.partner'].browse(args['partner_id'])
        orders, more = self._sal_search_page('purchase.order', domain, 'date_approve desc, id desc')
        total = self._pro_orders_kpi(scope, domain)
        return {'title': partner.display_name, 'sub': _('Purchases confirmed in the period'),
                'rows': self._pro_order_rows(orders, partner.display_name), 'more': more,
                'total': {'label': _('Total · untaxed'), 'value': '%s %s' % (
                    self._pro_format(total['amount']), scope['company'].currency_id.name)},
                'action': {'key': 'procurement.supplier', 'args': args}, 'dest': _('Purchase Orders')}

    def _action_procurement_supplier(self, args):
        _scope, domain = self._pro_supplier_domain(args)
        return self._window('purchase.purchase_form_action', self.env._('Purchases confirmed'),
                            'purchase.order', domain)

    def _pro_order(self, args):
        order = self.env['purchase.order'].browse(self._positive_id(args, 'order_id')).exists()
        if not order:
            raise ValidationError(self.env._('Unknown detail.'))
        self._check_company(order)
        return order

    def _drawer_procurement_order(self, args):
        """One purchase order's lines: ordered and received quantities, untaxed subtotal."""
        order = self._pro_order(args)
        _ = self.env._
        rows = [{'label': line.product_id.display_name or line.name,
                 'sub': _('Ordered %(ordered)s · received %(received)s %(unit)s',
                          ordered=formatLang(self.env, line.product_qty, digits=2),
                          received=formatLang(self.env, line.qty_received, digits=2),
                          unit=line.product_uom_id.name or ''),
                 'value': self._pro_format(line.price_subtotal)}
                for line in order.order_line.filtered(lambda l: not l.display_type)[:DRAWER_ROWS]]
        return {'title': order.name, 'sub': '%s · %s' % (
                    order.partner_id.display_name, self._sal_selection('purchase.order', 'state', order.state)),
                'rows': rows,
                'total': {'label': _('Total · untaxed'), 'value': '%s %s' % (
                    self._pro_format(order.amount_untaxed), order.currency_id.name)},
                'action': {'key': 'procurement.order', 'args': {'order_id': order.id}}, 'dest': _('Purchase Order')}

    def _action_procurement_order(self, args):
        order = self._pro_order(args)
        return self._window('purchase.purchase_form_action', order.name, 'purchase.order',
                            [('id', '=', order.id)], res_id=order.id)

    def _drawer_procurement_late(self, args):
        return self._inv_pickings_drawer('incoming', 'late', 'procurement.late')

    def _action_procurement_late(self, args):
        return self._inv_pickings_action('incoming', 'late')
