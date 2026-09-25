"""Inventory: value, deliveries and receipts, and the stock report (current position).

Transfers come from ``stock.picking`` by operation type code (``outgoing`` deliveries,
``incoming`` receipts) among the open states ``waiting``, ``confirmed`` and ``assigned``:
Late = scheduled before today (Inventory's "Late" filter), Due today, Next 7 days
(tomorrow to seven days ahead) and Waiting (Inventory's "Waiting" filter). Days are the
user's.

The stock report groups ``stock.quant`` on internal locations by product and warehouse
(never ``qty_available``); filters, "Hide zero and negative stock" and paging run in the
query. Values are Odoo 19's own quant valuation (``stock.quant.value``, ``stock_account``),
shown only to users who may read it (Inventory Administrator).
"""
from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.fields import Domain
from odoo.tools.misc import format_date, formatLang

OPEN_STATES = ('waiting', 'confirmed', 'assigned')
WAITING_STATES = ('waiting', 'confirmed')
BUCKETS = ('late', 'today', 'week', 'waiting')
CODES = ('outgoing', 'incoming')
DRAWER_ROWS = 25
STOCK_PAGE = 10
QUERY_MAX = 100
OPTION_LIMIT = 200


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    # ------------------------------------------------------------------ section

    def _section_inventory(self, scope):
        """Inventory widgets: ``currency``, ``kpis``, ``deliveries``, ``receipts``, ``stock``
        (first page and filter options); ``kpis.value`` is ``None`` when not readable."""
        currency = scope['company'].currency_id
        tiles = self._inv_tiles(scope)
        late = self._inv_pickings_summary(scope, 'outgoing', 'late', 0)
        today = self._inv_pickings_summary(scope, 'incoming', 'today', 0)
        return {
            'currency': {'name': currency.name, 'symbol': currency.symbol,
                         'position': currency.position, 'digits': currency.decimal_places},
            'kpis': {
                'value': self._inv_value(scope),
                'late': {'count': late['count'], 'oldest': late['oldest']},
                'today': {'count': tiles['outgoing']['today'], 'ready': self._inv_ready_today(scope)},
                'receipts': {'count': today['count'], 'partners': today['partners']},
            },
            'deliveries': tiles['outgoing'],
            'receipts': tiles['incoming'],
            'stock': dict(self._inv_stock(scope, {}), options=self._inv_stock_options(scope)),
        }

    # ------------------------------------------------------------------ transfers

    def _inv_day_bounds(self, scope, first, last):
        """UTC bounds of the user's days ``today + first`` through ``today + last``."""
        today = scope['today']
        return self._utc_bounds(today + timedelta(days=first), today + timedelta(days=last))

    def _inv_picking_domain(self, scope, code, bucket):
        if code not in CODES or bucket not in BUCKETS:
            raise ValidationError(self.env._('Unknown detail.'))
        domain = Domain([('picking_type_id.code', '=', code), ('company_id', 'in', scope['companies'].ids)])
        if bucket == 'waiting':
            return domain & Domain('state', 'in', WAITING_STATES)
        domain &= Domain('state', 'in', OPEN_STATES)
        if bucket == 'late':
            start, _end = self._inv_day_bounds(scope, 0, 0)
            return domain & Domain('scheduled_date', '<', start)
        start, end = self._inv_day_bounds(scope, 0, 0) if bucket == 'today' else self._inv_day_bounds(scope, 1, 7)
        return domain & Domain('scheduled_date', '>=', start) & Domain('scheduled_date', '<', end)

    def _inv_tiles(self, scope):
        """``{code: {bucket: count}}``: one grouped count per bucket."""
        Picking = self.env['stock.picking']
        return {code: {bucket: Picking.search_count(self._inv_picking_domain(scope, code, bucket))
                       for bucket in BUCKETS} for code in CODES}

    def _inv_ready_today(self, scope):
        domain = self._inv_picking_domain(scope, 'outgoing', 'today') & Domain('state', '=', 'assigned')
        return self.env['stock.picking'].search_count(domain)

    def _inv_days_late(self, scope, picking):
        day = fields.Datetime.context_timestamp(self, picking.scheduled_date).date()
        return max((scope['today'] - day).days, 0)

    def _inv_picking_row(self, scope, picking):
        when = fields.Datetime.context_timestamp(self, picking.scheduled_date) if picking.scheduled_date else None
        return {'id': picking.id, 'name': picking.name, 'partner': picking.partner_id.display_name or '',
                'origin': picking.origin or '', 'date': fields.Date.to_string(when) if when else False,
                'days': self._inv_days_late(scope, picking) if when else 0, 'state': picking.state,
                'state_label': self._sal_selection('stock.picking', 'state', picking.state)}

    def _inv_pickings_summary(self, scope, code, bucket, limit):
        """Count, distinct partners, the oldest delay in days and the first ``limit`` rows (oldest first)."""
        Picking = self.env['stock.picking']
        domain = self._inv_picking_domain(scope, code, bucket)
        partners = Picking._read_group(domain, ['partner_id'], ['__count', 'scheduled_date:min'])
        count = sum(n for _p, n, _d in partners)
        first = min((d for _p, _n, d in partners if d), default=None)
        oldest = max((scope['today'] - fields.Datetime.context_timestamp(self, first).date()).days, 0) if first else 0
        rows = Picking.search(domain, order='scheduled_date asc, id asc', limit=limit) if limit else Picking
        return {'count': count, 'partners': len([p for p, _n, _d in partners if p]), 'oldest': oldest,
                'rows': [self._inv_picking_row(scope, p) for p in rows]}

    def _inv_bucket_title(self, code, bucket):
        _ = self.env._
        if code not in CODES or bucket not in BUCKETS:
            raise ValidationError(_('Unknown detail.'))
        return {
            ('outgoing', 'late'): _('Late deliveries'), ('outgoing', 'today'): _('Deliveries due today'),
            ('outgoing', 'week'): _('Deliveries · next 7 days'), ('outgoing', 'waiting'): _('Deliveries waiting'),
            ('incoming', 'late'): _('Late receipts'), ('incoming', 'today'): _('Receipts due today'),
            ('incoming', 'week'): _('Receipts · next 7 days'), ('incoming', 'waiting'): _('Receipts waiting'),
        }[code, bucket]

    def _inv_pickings_drawer(self, code, bucket, key):
        if not self._sal_can_read('stock.picking'):
            raise AccessError(self.env._('This section is not available to you.'))
        _ = self.env._
        scope = self._period_scope('inventory', 'month')
        title = self._inv_bucket_title(code, bucket)
        summary = self._inv_pickings_summary(scope, code, bucket, DRAWER_ROWS)
        rows = []
        for row in summary['rows']:
            late = bucket == 'late'
            rows.append({
                'label': row['name'],
                'sub': ' · '.join(filter(None, [row['partner'], row['origin'],
                                                format_date(self.env, row['date']) if row['date'] else ''])),
                'value': _('%s days', row['days']) if late else row['state_label'],
                'open': {'key': 'inventory.picking' if key.startswith('inventory.') else 'procurement.picking',
                         'args': {'picking_id': row['id']}, 'crumb': title},
            })
        return {'title': title, 'sub': _('%s transfers', summary['count']), 'rows': rows,
                'action': {'key': key, 'args': {'code': code, 'bucket': bucket}},
                'dest': _('Receipts') if code == 'incoming' else _('Deliveries')}

    def _inv_pickings_action(self, code, bucket):
        if not self._sal_can_read('stock.picking'):
            raise AccessError(self.env._('This section is not available to you.'))
        scope = self._period_scope('inventory', 'month')
        xmlid = 'stock.action_picking_tree_incoming' if code == 'incoming' else 'stock.action_picking_tree_outgoing'
        action = self._window(xmlid, self._inv_bucket_title(code, bucket), 'stock.picking',
                              self._inv_picking_domain(scope, code, bucket))
        action['context'] = {'restricted_picking_type_code': code}
        return action

    def _drawer_inventory_pickings(self, args):
        return self._inv_pickings_drawer(args.get('code'), args.get('bucket'), 'inventory.pickings')

    def _action_inventory_pickings(self, args):
        return self._inv_pickings_action(args.get('code'), args.get('bucket'))

    def _inv_picking(self, args):
        if not self._sal_can_read('stock.picking'):
            raise AccessError(self.env._('This section is not available to you.'))
        picking = self.env['stock.picking'].browse(self._positive_id(args, 'picking_id')).exists()
        if not picking:
            raise ValidationError(self.env._('Unknown detail.'))
        picking.check_access('read')
        return picking

    def _inv_picking_drawer(self, args, key):
        """One transfer's products and quantities."""
        picking = self._inv_picking(args)
        scope = self._period_scope('inventory', 'month')
        row = self._inv_picking_row(scope, picking)
        rows = [{'label': move.product_id.display_name,
                 'value': '%s %s' % (formatLang(self.env, move.product_uom_qty, digits=2), move.product_uom.name)}
                for move in picking.move_ids[:DRAWER_ROWS]]
        return {'title': picking.name,
                'sub': ' · '.join(filter(None, [row['partner'], row['state_label'],
                                                format_date(self.env, row['date']) if row['date'] else ''])),
                'rows': rows, 'action': {'key': key, 'args': {'picking_id': picking.id}},
                'dest': self.env._('Transfer')}

    def _inv_picking_action(self, args):
        picking = self._inv_picking(args)
        return self._window('stock.action_picking_tree_all', picking.name, 'stock.picking',
                            [('id', '=', picking.id)], res_id=picking.id)

    def _drawer_inventory_picking(self, args):
        return self._inv_picking_drawer(args, 'inventory.picking')

    def _action_inventory_picking(self, args):
        return self._inv_picking_action(args)

    def _drawer_procurement_picking(self, args):
        return self._inv_picking_drawer(args, 'procurement.picking')

    def _action_procurement_picking(self, args):
        return self._inv_picking_action(args)

    # ------------------------------------------------------------------ value

    def _inv_value_readable(self):
        field = self.env['stock.quant']._fields.get('value')
        return bool(field) and self.env['stock.quant']._has_field_access(field, 'read')

    def _inv_value(self, scope):
        """Inventory value as of today: Odoo's quant valuation on valued locations, per company."""
        if not self._inv_value_readable():
            return None
        rows = self.env['stock.quant']._read_group(
            [('location_id.usage', 'in', ('internal', 'transit')), ('company_id', 'in', scope['companies'].ids)],
            ['company_id'], ['value:sum'])
        return {'amount': sum(self._fin_convert(scope, value or 0.0, company, scope['today'])
                              for company, value in rows if company)}

    # ------------------------------------------------------------------ stock report

    def _inv_stock_options(self, scope):
        warehouses = self.env['stock.warehouse'].search_fetch(
            [('company_id', 'in', scope['companies'].ids)], ['name'], limit=OPTION_LIMIT)
        categories = self.env['product.category'].search_fetch([], ['complete_name'], limit=OPTION_LIMIT) \
            if self.env['product.category'].has_access('read') else self.env['product.category']
        return {'warehouses': [{'id': w.id, 'name': w.name} for w in warehouses],
                'categories': [{'id': c.id, 'name': c.complete_name} for c in categories]}

    def _inv_stock_filters(self, args):
        """Validated filters: warehouse id, category id, search text, hide flag, page."""
        warehouse_id = self._positive_id(args, 'warehouse_id', optional=True) if args.get('warehouse_id') else False
        category_id = self._positive_id(args, 'category_id', optional=True) if args.get('category_id') else False
        query = args.get('query') or ''
        hide = args.get('hide', True)
        page = args.get('page', 0)
        if not isinstance(query, str) or not isinstance(hide, bool) or type(page) is not int or page < 0:
            raise ValidationError(self.env._('Unknown detail.'))
        return warehouse_id, category_id, query.strip()[:QUERY_MAX], hide, page

    def _inv_stock_domain(self, scope, warehouse_id, category_id, query):
        domain = Domain([('location_id.usage', '=', 'internal'), ('company_id', 'in', scope['companies'].ids)])
        if warehouse_id:
            domain &= Domain('location_id.warehouse_id', '=', warehouse_id)
        if category_id:
            domain &= Domain('product_id.categ_id', 'child_of', category_id)
        if query:
            domain &= Domain('product_id', 'any', ['|', ('name', 'ilike', query), ('default_code', 'ilike', query)])
        return domain

    def _inv_stock(self, scope, args):
        """One page of on-hand stock by product and warehouse, with the number of lines."""
        warehouse_id, category_id, query, hide, page = self._inv_stock_filters(args)
        Quant = self.env['stock.quant']
        domain = self._inv_stock_domain(scope, warehouse_id, category_id, query)
        groupby = ['product_id', 'location_id.warehouse_id']
        having = [('quantity:sum', '>', 0)] if hide else []
        count = len(Quant._read_group(domain, groupby, having=having))
        page = min(page, max(count - 1, 0) // STOCK_PAGE)
        groups = Quant._read_group(
            domain, groupby, ['quantity:sum', 'reserved_quantity:sum'], having=having,
            order='product_id, location_id.warehouse_id', offset=page * STOCK_PAGE, limit=STOCK_PAGE)
        values = {}
        valued = self._inv_value_readable()
        if valued and groups:
            products = self.env['product.product'].union(*(product for product, *_r in groups))
            for product, warehouse, company, value in Quant._read_group(
                    domain & Domain('product_id', 'in', products.ids), groupby + ['company_id'], ['value:sum']):
                values[product, warehouse] = values.get((product, warehouse), 0.0) + \
                    self._fin_convert(scope, value or 0.0, company, scope['today'])
        names = {p.id: p.display_name for p in self.env['product.product'].union(
            *(product for product, *_r in groups)).with_context(display_default_code=False)}
        rows = [{
            'product_id': product.id, 'warehouse_id': warehouse.id or False,
            'code': product.default_code or '', 'name': names[product.id], 'category': product.categ_id.complete_name,
            'warehouse': warehouse.name or self.env._('No warehouse'), 'on_hand': on_hand, 'reserved': reserved,
            'available': on_hand - reserved, 'unit': product.uom_id.name,
            'value': values.get((product, warehouse), 0.0) if valued else None,
        } for product, warehouse, on_hand, reserved in groups]
        return {'rows': rows, 'count': count, 'page': page, 'per': STOCK_PAGE, 'valued': valued,
                'filters': {'warehouse_id': warehouse_id, 'category_id': category_id, 'query': query, 'hide': hide}}

    def _drawer_inventory_stock(self, args):
        """A page of the stock report (filters and paging from the section's controls)."""
        return self._inv_stock(self._period_scope('inventory', 'month'), args)

    def _action_inventory_stock(self, args):
        """Odoo's stock (quants) list on the same filters."""
        scope = self._period_scope('inventory', 'month')
        warehouse_id, category_id, query, _hide, _page = self._inv_stock_filters(args)
        action = self.env['stock.quant'].action_view_quants()
        action.update(name=self.env._('Stock'), target='current',
                      domain=list(self._inv_stock_domain(scope, warehouse_id, category_id, query)))
        return action

    def _inv_product(self, args):
        product = self.env['product.product'].browse(self._positive_id(args, 'product_id')).exists()
        if not product:
            raise ValidationError(self.env._('Unknown detail.'))
        product.check_access('read')
        return product

    def _drawer_inventory_product(self, args):
        """One product's on-hand, reserved and available quantities by warehouse."""
        product = self._inv_product(args)
        scope = self._period_scope('inventory', 'month')
        _ = self.env._
        domain = self._inv_stock_domain(scope, False, False, '') & Domain('product_id', '=', product.id)
        unit = product.uom_id.name
        fmt = lambda q: formatLang(self.env, q, digits=2)  # noqa: E731
        rows = [{'label': warehouse.name or _('No warehouse'),
                 'sub': _('Reserved %(reserved)s · available %(available)s',
                          reserved=fmt(reserved), available=fmt(on_hand - reserved)),
                 'value': '%s %s' % (fmt(on_hand), unit)}
                for warehouse, on_hand, reserved in self.env['stock.quant']._read_group(
                    domain, ['location_id.warehouse_id'], ['quantity:sum', 'reserved_quantity:sum'],
                    order='location_id.warehouse_id')]
        return {'title': product.display_name, 'sub': _('On hand by warehouse'), 'rows': rows,
                'action': {'key': 'inventory.product', 'args': {'product_id': product.id}},
                'dest': _('Stock')}

    def _action_inventory_product(self, args):
        product = self._inv_product(args)
        scope = self._period_scope('inventory', 'month')
        action = self.env['stock.quant'].action_view_quants()
        action.update(name=product.display_name, target='current', domain=list(
            self._inv_stock_domain(scope, False, False, '') & Domain('product_id', '=', product.id)))
        return action
