from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.fields import Domain
from odoo.tools.misc import format_datetime

# Columns the printout may show, in the order of the list view.
PSR_COLUMNS = (
    'date', 'order_id', 'session_id', 'config_id', 'cashier', 'partner_id',
    'product_id', 'product_categ_id', 'qty', 'price_unit', 'total_discount',
    'price_subtotal_excl', 'tax_amount', 'price_total', 'margin',
)
# Columns summed in groups, totals and the summary figures.
PSR_SUMS = ('qty', 'total_discount', 'price_subtotal_excl', 'tax_amount', 'price_total', 'margin')
PSR_MODES = ('summary', 'detailed')
PSR_GRANULARITIES = ('day', 'week', 'month', 'quarter', 'year')
# A detailed print lists every line: above this, Summary or narrower filters are needed.
PSR_MAX_LINES = 5000
# The taxes table runs Odoo's tax computation per line (as the Sales Details report does).
PSR_MAX_TAX_LINES = 20000


class ReportPosOrder(models.Model):
    _inherit = 'report.pos.order'

    cashier = fields.Char(string='Cashier', readonly=True)
    qty = fields.Float(string='Quantity', digits='Product Unit', readonly=True)
    price_unit = fields.Float(string='Unit Price', readonly=True, aggregator=False)
    tax_amount = fields.Float(string='Tax', readonly=True)
    is_refund = fields.Boolean(string='Refund', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)

    def _select(self):
        # Amounts follow the conventions of the standard columns: company currency
        # (divided by the order's rate), rounded like price_total and price_subtotal_excl.
        return super()._select() + """,
                COALESCE(psr_employee.name, psr_partner.name) AS cashier,
                l.qty AS qty,
                l.price_unit / COALESCE(NULLIF(s.currency_rate, 0), 1.0) AS price_unit,
                ROUND((SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal_incl)) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places)
                    - ROUND((SIGN(l.qty) * SIGN(l.price_unit) * ABS(l.price_subtotal)) / COALESCE(NULLIF(s.currency_rate, 0), 1.0), cu.decimal_places) AS tax_amount,
                l.qty < 0 AS is_refund,
                cu.id AS currency_id
        """

    def _from(self):
        return super()._from() + """
                LEFT JOIN hr_employee psr_employee ON (psr_employee.id = s.employee_id)
                LEFT JOIN res_users psr_user ON (psr_user.id = s.user_id)
                LEFT JOIN res_partner psr_partner ON (psr_partner.id = psr_user.partner_id)
        """

    # ------------------------------------------------------------------
    # Printing
    # ------------------------------------------------------------------

    @api.model
    def action_print_sales_report(self, domain, groupby, columns, mode='summary', filters=None):
        """Print the Sales Report as the list shows it: same domain, grouping and visible columns."""
        options = self._psr_options(domain, groupby, columns, mode, filters)
        if options['mode'] == 'detailed':
            self._psr_check_line_count(options['domain'])
        return self.env.ref('adams_pos_sales_report.action_report_pos_sales').report_action(None, data=options)

    @api.model
    def _psr_check_access(self):
        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            raise AccessError(self.env._("Only Point of Sale administrators can print the sales report."))

    @api.model
    def _psr_options(self, domain, groupby, columns, mode, filters):
        """Validate what the client sent; nothing here is trusted as is."""
        self._psr_check_access()
        if mode not in PSR_MODES:
            raise UserError(self.env._("Unknown print mode."))
        if not isinstance(domain, list | tuple):
            raise UserError(self.env._("The report filters are not valid."))
        domain = list(domain)
        # Raises for unknown fields or operators; access rules apply as for the user.
        self.search_count(domain, limit=1)

        groupby = list(groupby or [])
        for spec in groupby:
            fname, _sep, granularity = str(spec).partition(':')
            field = self._fields.get(fname)
            if not field or fname == 'id' or not field._description_groupable(self.env):
                raise UserError(self.env._("The report cannot be grouped by %(field)s.", field=fname))
            if field.type in ('date', 'datetime'):
                if granularity not in PSR_GRANULARITIES:
                    raise UserError(self.env._("The report cannot be grouped by %(field)s.", field=spec))
            elif granularity:
                raise UserError(self.env._("The report cannot be grouped by %(field)s.", field=spec))

        wanted = [c for c in columns or [] if c in PSR_COLUMNS]
        columns = [c for c in PSR_COLUMNS if c in wanted] or list(PSR_COLUMNS)
        if not self._has_field_access(self._fields['margin'], 'read'):
            columns = [c for c in columns if c != 'margin']

        filters = [str(f)[:300] for f in (filters or [])[:20]]
        return {
            'domain': domain,
            'groupby': groupby,
            'columns': columns,
            'mode': mode,
            'filters': filters,
        }

    @api.model
    def _psr_check_line_count(self, domain):
        count = self.search_count(domain)
        if count > PSR_MAX_LINES:
            raise UserError(self.env._(
                "The detailed print is limited to %(max)s lines and these filters select %(count)s. "
                "Print the Summary, or narrow the period or filters.",
                max=PSR_MAX_LINES, count=count,
            ))

    @api.model
    def _psr_report_data(self, options):
        """Everything the PDF template needs, computed as the current user."""
        domain = Domain(options['domain'])
        groupby = options['groupby']
        detailed = options['mode'] == 'detailed' or not groupby
        if detailed:
            self._psr_check_line_count(options['domain'])

        fields_info = self.fields_get(list(PSR_COLUMNS) + groupby_fields(groupby), ['string', 'type', 'selection'])
        # Line columns leave out what the grouping already shows in the group headers.
        grouped = {spec.split(':')[0] for spec in groupby}
        labels = self._psr_labels(fields_info)
        columns = [
            {
                'name': c,
                'label': labels[c],
                'numeric': c in PSR_SUMS or c == 'price_unit',
                'sum': c in PSR_SUMS,
                'money': c not in ('qty',),
            }
            for c in options['columns']
        ]
        line_columns = [c for c in columns if c['numeric'] or c['name'] not in grouped]
        if not detailed:
            line_columns = [c for c in columns if c['sum']]
        label_columns = [c for c in line_columns if not c['numeric']]

        aggregates = [f'{f}:sum' for f in PSR_SUMS]
        groups = self._psr_groups(domain, groupby, 0, aggregates, fields_info, detailed) if groupby else []
        lines = [] if groupby else self._psr_lines(domain)

        totals = dict(zip(PSR_SUMS, self._read_group(domain, [], aggregates)[0]))
        sales_domain = domain & Domain('is_refund', '=', False)
        refund_domain = domain & Domain('is_refund', '=', True)
        orders_count = self._read_group(sales_domain, [], ['order_id:count_distinct'])[0][0]
        refunds = self._read_group(refund_domain, [], ['price_total:sum'])[0][0]

        company = self.env.company
        return {
            'company': company,
            'currency': company.currency_id,
            'mode': 'detailed' if detailed else 'summary',
            'columns': columns,
            'line_columns': line_columns,
            'label_columns': label_columns,
            'value_columns': [c for c in line_columns if c['numeric']],
            'groups': groups,
            'lines': lines,
            'totals': totals,
            'kpis': {
                'orders': orders_count,
                'qty': totals['qty'],
                'net': totals['price_subtotal_excl'],
                'tax': totals['tax_amount'],
                'total': totals['price_total'],
                'discount': totals['total_discount'],
                'refunds': refunds,
                'average': totals['price_total'] / orders_count if orders_count else 0.0,
            },
            'filters': options['filters'],
            'grouping': [self._psr_groupby_label(spec, labels) for spec in groupby],
            'printed_by': self.env.user.name,
            'printed_at': format_datetime(self.env, fields.Datetime.now()),
            'payments': self._psr_payments(domain),
            'taxes': self._psr_taxes(domain),
            'max_tax_lines': PSR_MAX_TAX_LINES,
        }

    @api.model
    def _psr_groups(self, domain, groupby, level, aggregates, fields_info, detailed):
        spec = groupby[level]
        result = []
        for group in self.formatted_read_group(domain, [spec], aggregates + ['__count']):
            group_domain = domain & Domain(group['__extra_domain'])
            node = {
                'label': self._psr_group_label(spec, group[spec], fields_info),
                'level': level,
                'count': group['__count'],
                'sums': {f: group[f'{f}:sum'] for f in PSR_SUMS},
                'children': [],
                'lines': [],
            }
            if level + 1 < len(groupby):
                node['children'] = self._psr_groups(group_domain, groupby, level + 1, aggregates, fields_info, detailed)
            elif detailed:
                node['lines'] = self._psr_lines(group_domain)
            result.append(node)
        return result

    @api.model
    def _psr_lines(self, domain):
        lines = []
        for record in self.search(domain, order='date, id'):
            lines.append({
                'date': format_datetime(self.env, record.date),
                'order_id': record.order_id.display_name or '',
                'session_id': record.session_id.display_name or '',
                'config_id': record.config_id.display_name or '',
                'cashier': record.cashier or '',
                'partner_id': record.partner_id.display_name or '',
                'product_id': record.product_id.display_name or '',
                'product_categ_id': record.product_categ_id.display_name or '',
                'qty': record.qty,
                'price_unit': record.price_unit,
                'total_discount': record.total_discount,
                'price_subtotal_excl': record.price_subtotal_excl,
                'tax_amount': record.tax_amount,
                'price_total': record.price_total,
                'margin': record.margin,
                'is_refund': record.is_refund,
            })
        return lines

    @api.model
    def _psr_group_label(self, spec, value, fields_info):
        info = fields_info[spec.split(':')[0]]
        if info['type'] == 'boolean':
            return self.env._("Yes") if value else self.env._("No")
        if value is False or value is None or value == '':
            return self.env._("None")
        if isinstance(value, tuple | list):
            return str(value[1])
        if info['type'] == 'selection':
            return dict(info['selection']).get(value, value)
        return str(value)

    @api.model
    def _psr_labels(self, fields_info):
        """Column and grouping labels: the field labels, with the words the list view uses."""
        labels = {fname: info['string'] for fname, info in fields_info.items()}
        labels.update({
            'cashier': self.env._("Employee"),
            'total_discount': self.env._("Discount"),
            'price_subtotal_excl': self.env._("Net"),
            'price_total': self.env._("Total"),
        })
        return labels

    @api.model
    def _psr_groupby_label(self, spec, labels):
        fname, _sep, granularity = spec.partition(':')
        label = labels[fname]
        if granularity:
            names = {
                'day': self.env._("Day"), 'week': self.env._("Week"), 'month': self.env._("Month"),
                'quarter': self.env._("Quarter"), 'year': self.env._("Year"),
            }
            return f"{label}: {names[granularity]}"
        return label

    @api.model
    def _psr_payments(self, domain):
        """Payments of the orders in the report, per method, in company currency.

        Read from the payments themselves: an order paid with two methods appears under both.
        """
        orders = self._read_group(domain, [], ['order_id:recordset'])[0][0]
        if not orders:
            return []
        rates = {order.id: order.currency_rate or 1.0 for order in orders}
        by_method = {}
        payments = self.env['pos.payment'].search([('pos_order_id', 'in', orders.ids)], order='payment_method_id, id')
        for payment in payments:
            entry = by_method.setdefault(payment.payment_method_id, {'name': payment.payment_method_id.display_name, 'count': 0, 'amount': 0.0})
            entry['count'] += 1
            entry['amount'] += payment.amount / rates[payment.pos_order_id.id]
        return list(by_method.values())

    @api.model
    def _psr_taxes(self, domain):
        """Taxes per tax with Odoo's own Sales Details computation, in company currency.

        Returns None when the selection is too large to compute line by line.
        """
        ids = self._search(domain)
        lines = self.env['pos.order.line'].search([('id', 'in', ids)])
        if len(lines) > PSR_MAX_TAX_LINES:
            return None
        details = self.env['report.point_of_sale.report_saledetails']
        result = {}
        for line in lines:
            order = line.order_id
            line_taxes = {'base_amount': 0.0, 'taxes': {}}
            details._get_products_and_taxes_dict(line, {}, line_taxes, order.currency_id)
            rate = order.currency_rate or 1.0
            for tax_id, values in line_taxes['taxes'].items():
                entry = result.setdefault(tax_id, {'name': values['name'], 'base_amount': 0.0, 'tax_amount': 0.0})
                entry['base_amount'] += values['base_amount'] / rate
                entry['tax_amount'] += values['tax_amount'] / rate
        return list(result.values())


def groupby_fields(groupby):
    return [spec.split(':')[0] for spec in groupby]
