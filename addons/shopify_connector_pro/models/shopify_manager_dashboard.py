from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models


class ShopifyManagerDashboard(models.AbstractModel):
    """Read-only aggregator feeding the Shopify Manager Dashboard client action.

    Every query uses `_read_group` against existing shopify_connector_pro models. This
    model stores nothing, inherits nothing, and adds no fields to other models.
    """

    _name = 'shopify.manager.dashboard'
    _description = 'Shopify Manager Dashboard Aggregator'

    # ------------------------------------------------------------------ #
    # Public RPC
    # ------------------------------------------------------------------ #

    @api.model
    def get_data(self, backend_ids=None, period='mtd', date_from=None, date_to=None):
        backends = self._resolve_backends(backend_ids)
        if not backends:
            return self._empty_payload()

        start, end = self._resolve_period(period, date_from, date_to)
        prior_start, prior_end = self._prior_period(start, end)
        currency = self._resolve_currency(backends)

        order_ids, prior_order_ids = self._orders_in_windows(
            backends.ids, start, end, prior_start, prior_end,
        )

        kpis = self._compute_kpis(
            backends, order_ids, prior_order_ids, start, end, prior_start, prior_end,
        )
        return {
            'backends': [{'id': b.id, 'name': b.name} for b in backends],
            'selected_backend_ids': backends.ids,
            'period': period,
            'date_from': fields.Datetime.to_string(start),
            'date_to': fields.Datetime.to_string(end),
            'currency': {
                'id': currency.id,
                'symbol': currency.symbol or currency.name,
                'position': currency.position,
                'decimal_places': currency.decimal_places,
            },
            'kpis': kpis,
            'trend': self._compute_trend(order_ids, start, end),
            'top_products': self._compute_top_products(order_ids),
            'top_customers': self._compute_top_customers(order_ids),
            'deliveries': self._compute_deliveries(backends.ids, start, end),
            'abandoned_carts': self._compute_abandoned_carts(backends.ids, start, end),
            'refunds': self._compute_refunds(backends.ids, start, end, kpis['revenue']['value']),
            'payouts': self._compute_payouts(backends.ids, start, end),
            'alerts': self._compute_alerts(backends),
        }

    @api.model
    def get_backends(self):
        backends = self.env['shopify.backend'].sudo().search([])
        return [{'id': b.id, 'name': b.name} for b in backends]

    # ------------------------------------------------------------------ #
    # Inputs
    # ------------------------------------------------------------------ #

    def _resolve_backends(self, backend_ids):
        Backend = self.env['shopify.backend'].sudo()
        if backend_ids:
            return Backend.browse(backend_ids).exists()
        return Backend.search([])

    def _resolve_currency(self, backends):
        if 'currency_id' in backends._fields:
            currencies = backends.mapped('currency_id')
            if len(currencies) == 1 and currencies:
                return currencies
        companies = backends.mapped('company_id') if 'company_id' in backends._fields else self.env.company
        company_currencies = companies.mapped('currency_id') if companies else self.env.company.currency_id
        if len(company_currencies) == 1 and company_currencies:
            return company_currencies
        return self.env.company.currency_id

    def _resolve_period(self, period, date_from, date_to):
        # fields.Datetime.now() truncates microseconds to zero and Odoo's
        # domain serialisation (Datetime.to_string) also drops them, yet
        # create_date / write_date are stored with full µs precision.
        # Adding one second ensures ``('create_date', '<', end)`` captures
        # every record created during the current wall-clock second.
        now = fields.Datetime.now() + timedelta(seconds=1)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if period == 'custom' and date_from and date_to:
            return fields.Datetime.to_datetime(date_from), fields.Datetime.to_datetime(date_to)
        if period == 'today':
            return today_start, now
        if period == 'wtd':
            return today_start - timedelta(days=today_start.weekday()), now
        if period == 'mtd':
            return today_start.replace(day=1), now
        if period == 'ytd':
            return today_start.replace(month=1, day=1), now
        if period == 'last_30':
            return today_start - timedelta(days=30), now
        if period == 'last_90':
            return today_start - timedelta(days=90), now
        return today_start.replace(day=1), now

    def _prior_period(self, start, end):
        span = end - start
        return start - span, start

    def _empty_payload(self):
        currency = self.env.company.currency_id
        return {
            'backends': [],
            'selected_backend_ids': [],
            'period': 'mtd',
            'currency': {
                'id': currency.id,
                'symbol': currency.symbol or currency.name,
                'position': currency.position,
                'decimal_places': currency.decimal_places,
            },
            'kpis': {k: {'value': 0, 'prior': 0, 'delta_pct': 0} for k in
                     ('revenue', 'orders', 'aov', 'new_customers', 'refund_rate')},
            'trend': [],
            'top_products': [],
            'top_customers': [],
            'deliveries': {
                'unfulfilled': 0, 'ready_to_ship': 0,
                'shipped_total': 0, 'shipped_today': 0,
                'avg_fulfill_hours': 0, 'daily_breakdown': [],
            },
            'abandoned_carts': {
                'count': 0, 'value_total': 0, 'recoverable_value': 0,
                'recovery_rate_pct': 0, 'recent': [],
            },
            'refunds': {'count': 0, 'amount': 0, 'refund_rate_pct': 0, 'recent': []},
            'payouts': {
                'scheduled': {'amount': 0, 'count': 0},
                'in_transit': {'amount': 0, 'count': 0},
                'paid_mtd': {'amount': 0, 'count': 0},
                'next_payout_date': False, 'recent': [],
            },
            'alerts': {
                'payment_mismatches': 0, 'fulfillment_mismatches': 0,
                'webhook_pending': 0, 'permanent_errors': 0,
            },
        }

    # ------------------------------------------------------------------ #
    # Orders in window (shared base for KPIs / trend / top lists)
    # ------------------------------------------------------------------ #

    def _orders_in_windows(self, backend_ids, start, end, prior_start, prior_end):
        SaleOrder = self.env['sale.order'].sudo()
        base_domain = [
            ('shopify_bind_ids.backend_id', 'in', backend_ids),
            ('state', 'in', ('sale', 'done')),
        ]
        current = SaleOrder.search(
            base_domain + [('date_order', '>=', start), ('date_order', '<', end)]
        ).ids
        prior = SaleOrder.search(
            base_domain + [('date_order', '>=', prior_start), ('date_order', '<', prior_end)]
        ).ids
        return current, prior

    # ------------------------------------------------------------------ #
    # KPIs
    # ------------------------------------------------------------------ #

    def _compute_kpis(self, backends, order_ids, prior_order_ids, start, end, prior_start, prior_end):
        SaleOrder = self.env['sale.order'].sudo()

        revenue_current, orders_current = self._sum_order_totals(SaleOrder, order_ids)
        revenue_prior, orders_prior = self._sum_order_totals(SaleOrder, prior_order_ids)

        aov_current = (revenue_current / orders_current) if orders_current else 0
        aov_prior = (revenue_prior / orders_prior) if orders_prior else 0

        new_cust_current = self._count_new_customers(backends.ids, start, end)
        new_cust_prior = self._count_new_customers(backends.ids, prior_start, prior_end)

        refund_amt_current = self._sum_refunds(backends.ids, start, end)
        refund_amt_prior = self._sum_refunds(backends.ids, prior_start, prior_end)
        refund_rate_current = (refund_amt_current / revenue_current * 100) if revenue_current else 0
        refund_rate_prior = (refund_amt_prior / revenue_prior * 100) if revenue_prior else 0

        return {
            'revenue': self._kpi(revenue_current, revenue_prior),
            'orders': self._kpi(orders_current, orders_prior),
            'aov': self._kpi(aov_current, aov_prior),
            'new_customers': self._kpi(new_cust_current, new_cust_prior),
            'refund_rate': self._kpi(refund_rate_current, refund_rate_prior),
        }

    def _kpi(self, value, prior):
        if prior:
            delta = (value - prior) / prior * 100
        else:
            delta = 100.0 if value else 0.0
        return {
            'value': round(float(value), 2),
            'prior': round(float(prior), 2),
            'delta_pct': round(float(delta), 1),
        }

    def _sum_order_totals(self, SaleOrder, order_ids):
        if not order_ids:
            return 0.0, 0
        groups = SaleOrder._read_group(
            [('id', 'in', order_ids)],
            groupby=[],
            aggregates=['amount_total:sum', '__count'],
        )
        total, count = groups[0] if groups else (0.0, 0)
        return float(total or 0.0), int(count or 0)

    def _count_new_customers(self, backend_ids, start, end):
        # A customer is "new" if their shopify.customer.binding was created in the window.
        CustomerBinding = self.env['shopify.customer.binding'].sudo()
        return CustomerBinding.search_count([
            ('backend_id', 'in', backend_ids),
            ('create_date', '>=', start),
            ('create_date', '<', end),
        ])

    def _sum_refunds(self, backend_ids, start, end):
        Refund = self.env['shopify.refund.binding'].sudo()
        groups = Refund._read_group(
            [
                ('backend_id', 'in', backend_ids),
                ('create_date', '>=', start),
                ('create_date', '<', end),
            ],
            groupby=[],
            aggregates=['refund_amount:sum'],
        )
        return float((groups[0][0] if groups else 0.0) or 0.0)

    # ------------------------------------------------------------------ #
    # Trend
    # ------------------------------------------------------------------ #

    def _compute_trend(self, order_ids, start, end):
        if not order_ids:
            return []
        SaleOrder = self.env['sale.order'].sudo()
        groups = SaleOrder._read_group(
            [('id', 'in', order_ids)],
            groupby=['date_order:day'],
            aggregates=['amount_total:sum', '__count'],
        )
        rows = []
        for day, revenue, count in groups:
            day_str = fields.Date.to_string(day) if day else None
            if not day_str:
                continue
            rows.append({
                'date': day_str,
                'revenue': round(float(revenue or 0.0), 2),
                'orders': int(count or 0),
            })
        rows.sort(key=lambda r: r['date'])
        return rows

    # ------------------------------------------------------------------ #
    # Top lists
    # ------------------------------------------------------------------ #

    def _compute_top_products(self, order_ids, limit=10):
        if not order_ids:
            return []
        Line = self.env['sale.order.line'].sudo()
        groups = Line._read_group(
            [
                ('order_id', 'in', order_ids),
                ('product_id', '!=', False),
                ('display_type', '=', False),
            ],
            groupby=['product_id'],
            aggregates=['price_subtotal:sum', 'product_uom_qty:sum'],
            order='price_subtotal:sum desc',
            limit=limit,
        )
        return [{
            'product_id': product.id,
            'name': product.display_name,
            'revenue': round(float(revenue or 0.0), 2),
            'units': round(float(qty or 0.0), 2),
        } for product, revenue, qty in groups]

    def _compute_top_customers(self, order_ids, limit=10):
        if not order_ids:
            return []
        SaleOrder = self.env['sale.order'].sudo()
        groups = SaleOrder._read_group(
            [('id', 'in', order_ids), ('partner_id', '!=', False)],
            groupby=['partner_id'],
            aggregates=['amount_total:sum', '__count'],
            order='amount_total:sum desc',
            limit=limit,
        )
        return [{
            'partner_id': partner.id,
            'name': partner.display_name,
            'revenue': round(float(revenue or 0.0), 2),
            'orders': int(count or 0),
        } for partner, revenue, count in groups]

    # ------------------------------------------------------------------ #
    # Deliveries
    # ------------------------------------------------------------------ #

    def _compute_deliveries(self, backend_ids, start, end):
        Picking = self.env['stock.picking'].sudo()
        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fourteen_days_ago = today_start - timedelta(days=14)

        base_domain = [
            ('sale_id.shopify_bind_ids.backend_id', 'in', backend_ids),
            ('picking_type_code', '=', 'outgoing'),
        ]

        state_groups = Picking._read_group(
            base_domain,
            groupby=['state'],
            aggregates=['__count'],
        )
        by_state = {state: count for state, count in state_groups}

        unfulfilled = by_state.get('waiting', 0) + by_state.get('confirmed', 0)
        ready_to_ship = by_state.get('assigned', 0)
        shipped_total = by_state.get('done', 0)

        shipped_today = Picking.search_count(
            base_domain + [('state', '=', 'done'), ('date_done', '>=', today_start)]
        )

        # Avg fulfillment time (hours) for pickings done inside the window.
        window_done = Picking.search([
            ('sale_id.shopify_bind_ids.backend_id', 'in', backend_ids),
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
            ('date_done', '>=', start),
            ('date_done', '<', end),
        ], limit=500)
        durations = []
        for p in window_done:
            if p.date_done and p.create_date:
                delta = p.date_done - p.create_date
                durations.append(delta.total_seconds() / 3600.0)
        avg_hours = round(sum(durations) / len(durations), 1) if durations else 0

        # Last 14 days stacked breakdown by state on date_done (done) or
        # scheduled_date (open). Two queries.
        daily = defaultdict(lambda: {'done': 0, 'pending': 0, 'cancel': 0})
        done_groups = Picking._read_group(
            base_domain + [('state', '=', 'done'), ('date_done', '>=', fourteen_days_ago)],
            groupby=['date_done:day'],
            aggregates=['__count'],
        )
        for day, count in done_groups:
            if day:
                daily[fields.Date.to_string(day)]['done'] = count

        pending_groups = Picking._read_group(
            base_domain + [
                ('state', 'in', ('waiting', 'confirmed', 'assigned')),
                ('scheduled_date', '>=', fourteen_days_ago),
            ],
            groupby=['scheduled_date:day'],
            aggregates=['__count'],
        )
        for day, count in pending_groups:
            if day:
                daily[fields.Date.to_string(day)]['pending'] = count

        cancel_groups = Picking._read_group(
            base_domain + [('state', '=', 'cancel'), ('write_date', '>=', fourteen_days_ago)],
            groupby=['write_date:day'],
            aggregates=['__count'],
        )
        for day, count in cancel_groups:
            if day:
                daily[fields.Date.to_string(day)]['cancel'] = count

        daily_breakdown = [
            {'date': d, **vals} for d, vals in sorted(daily.items())
        ]

        return {
            'unfulfilled': unfulfilled,
            'ready_to_ship': ready_to_ship,
            'shipped_total': shipped_total,
            'shipped_today': shipped_today,
            'avg_fulfill_hours': avg_hours,
            'daily_breakdown': daily_breakdown,
        }

    # ------------------------------------------------------------------ #
    # Abandoned carts
    # ------------------------------------------------------------------ #

    def _compute_abandoned_carts(self, backend_ids, start, end):
        Cart = self.env['shopify.abandoned.cart'].sudo()
        domain = [
            ('backend_id', 'in', backend_ids),
            ('abandoned_at', '>=', start),
            ('abandoned_at', '<', end),
        ]
        groups = Cart._read_group(
            domain,
            groupby=['recovered'],
            aggregates=['__count', 'total_price:sum'],
        )
        count_recovered = value_recovered = 0
        count_lost = value_lost = 0
        for recovered, count, total in groups:
            total = float(total or 0.0)
            if recovered:
                count_recovered, value_recovered = count, total
            else:
                count_lost, value_lost = count, total
        total_count = count_recovered + count_lost
        total_value = value_recovered + value_lost
        recovery_rate = (count_recovered / total_count * 100) if total_count else 0

        recent = Cart.search(domain + [('recovered', '=', False)], limit=5, order='abandoned_at desc')
        # Unrecovered carts almost never have sale_order_id (it is only set
        # when a user manually creates a quotation from the cart). Fall back
        # to the customer_name / customer_email fields that the importer
        # populates directly from the Shopify checkout payload so the row
        # is never labelled with an empty string.
        recent_rows = [{
            'id': c.id,
            'abandoned_at': fields.Datetime.to_string(c.abandoned_at) if c.abandoned_at else False,
            'total_price': round(float(c.total_price or 0.0), 2),
            'partner_name': (
                (c.sale_order_id.partner_id.display_name if c.sale_order_id and c.sale_order_id.partner_id else '')
                or c.customer_name
                or c.customer_email
                or ''
            ),
            'recovery_url': c.recovery_url or '',
        } for c in recent]

        return {
            'count': total_count,
            'value_total': round(total_value, 2),
            'recoverable_value': round(value_lost, 2),
            'recovery_rate_pct': round(recovery_rate, 1),
            'recent': recent_rows,
        }

    # ------------------------------------------------------------------ #
    # Refunds
    # ------------------------------------------------------------------ #

    def _compute_refunds(self, backend_ids, start, end, period_revenue):
        Refund = self.env['shopify.refund.binding'].sudo()
        domain = [
            ('backend_id', 'in', backend_ids),
            ('create_date', '>=', start),
            ('create_date', '<', end),
        ]
        groups = Refund._read_group(
            domain,
            groupby=[],
            aggregates=['__count', 'refund_amount:sum'],
        )
        count, amount = (groups[0] if groups else (0, 0.0))
        amount = float(amount or 0.0)
        rate = (amount / period_revenue * 100) if period_revenue else 0

        recent = Refund.search(domain, limit=5, order='create_date desc')
        recent_rows = []
        for r in recent:
            order_name = ''
            if r.order_binding_id and r.order_binding_id.odoo_id:
                order_name = r.order_binding_id.odoo_id.name
            recent_rows.append({
                'id': r.id,
                'order_name': order_name,
                'refund_amount': round(float(r.refund_amount or 0.0), 2),
                'currency': r.currency_code or '',
                'create_date': fields.Datetime.to_string(r.create_date) if r.create_date else False,
            })

        return {
            'count': int(count or 0),
            'amount': round(amount, 2),
            'refund_rate_pct': round(rate, 2),
            'recent': recent_rows,
        }

    # ------------------------------------------------------------------ #
    # Payouts
    # ------------------------------------------------------------------ #

    def _compute_payouts(self, backend_ids, start, end):
        Payout = self.env['shopify.payout'].sudo()
        today_start = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = today_start.replace(day=1)

        status_groups = Payout._read_group(
            [('backend_id', 'in', backend_ids)],
            groupby=['status'],
            aggregates=['__count', 'amount:sum'],
        )
        status_map = {status: {'count': int(c or 0), 'amount': round(float(a or 0.0), 2)}
                      for status, c, a in status_groups}

        paid_mtd_groups = Payout._read_group(
            [
                ('backend_id', 'in', backend_ids),
                ('status', '=', 'paid'),
                ('payout_date', '>=', month_start.date()),
            ],
            groupby=[],
            aggregates=['__count', 'amount:sum'],
        )
        paid_mtd = {'count': 0, 'amount': 0.0}
        if paid_mtd_groups:
            c, a = paid_mtd_groups[0]
            paid_mtd = {'count': int(c or 0), 'amount': round(float(a or 0.0), 2)}

        next_payout = Payout.search(
            [('backend_id', 'in', backend_ids), ('status', 'in', ('scheduled', 'in_transit'))],
            order='payout_date asc',
            limit=1,
        )
        next_date = fields.Date.to_string(next_payout.payout_date) if next_payout and next_payout.payout_date else False

        recent = Payout.search(
            [('backend_id', 'in', backend_ids)],
            order='payout_date desc',
            limit=5,
        )
        recent_rows = [{
            'id': p.id,
            'payout_date': fields.Date.to_string(p.payout_date) if p.payout_date else False,
            'status': p.status,
            'amount': round(float(p.amount or 0.0), 2),
        } for p in recent]

        return {
            'scheduled': status_map.get('scheduled', {'count': 0, 'amount': 0.0}),
            'in_transit': status_map.get('in_transit', {'count': 0, 'amount': 0.0}),
            'paid_mtd': paid_mtd,
            'next_payout_date': next_date,
            'recent': recent_rows,
        }

    # ------------------------------------------------------------------ #
    # Alerts — read-only sum of existing computed fields on shopify.backend
    # ------------------------------------------------------------------ #

    def _compute_alerts(self, backends):
        def total(field):
            return sum(getattr(b, field, 0) or 0 for b in backends)

        return {
            'payment_mismatches': total('payment_mismatch_count'),
            'fulfillment_mismatches': total('fulfillment_mismatch_count'),
            'webhook_pending': total('webhook_pending_count'),
            'permanent_errors': total('permanent_error_count'),
        }
