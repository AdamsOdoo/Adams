"""Thin adapters for stock services and authorized workforce aggregates."""
from datetime import datetime, time, timedelta

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class ExecutiveDashboardOperations(models.AbstractModel):
    _inherit = 'adams.executive.dashboard'

    def _stock_scope(self, dates, mode):
        if mode not in ('current', 'historical'):
            raise ValidationError(_('Invalid inventory mode.'))
        if 'stock.quant' not in self.env or not self.env.user.has_group('stock.group_stock_user'):
            raise AccessError(_('Inventory reporting access is required.'))
        products = self.env['product.product'].with_context(active_test=False)
        context = dict(products.env.context)
        if mode == 'historical':
            if dates[2] > fields.Date.context_today(self):
                raise ValidationError(_('Historical inventory requires a cutoff no later than today.'))
            # Match the native Inventory at Date wizard's UTC datetime contract.
            tz = pytz.timezone(self.env.user.tz or 'UTC')
            cutoff = tz.localize(datetime.combine(dates[2] + timedelta(days=1), time.min))
            cutoff = cutoff.astimezone(pytz.UTC).replace(tzinfo=None) - timedelta(seconds=1)
            context['to_date'] = fields.Datetime.to_string(cutoff)
        products = products.with_context(context)
        products.check_access('read')
        products.check_field_access_rights('read', ['is_storable', 'company_id', 'display_name', 'uom_id', 'qty_available'])
        self.env['stock.quant'].check_access('read')
        self.env['stock.move'].check_access('read')
        domain = [('is_storable', '=', True), ('company_id', 'in', [False, self.env.company.id])]
        return products, domain

    def _inventory_filter_scope(self, options, mode, filters):
        scoped, dates = self._scope(options)
        if not isinstance(filters, dict) or set(filters) - {'warehouse_id', 'category_id', 'location_id', 'hide_zero', 'hide_negative', 'search', 'at_date'}:
            raise ValidationError(_('Invalid stock filters.'))
        filters = dict(filters)
        if mode == 'historical' and filters.get('at_date'):
            try:
                dates = (*dates[:2], fields.Date.to_date(filters['at_date']))
            except (TypeError, ValueError):
                raise ValidationError(_('Choose a valid inventory date.'))
        products, domain = scoped._stock_scope(dates, mode)
        for key in ('hide_zero', 'hide_negative'):
            if key in filters and type(filters[key]) is not bool:
                raise ValidationError(_('Invalid quantity filter.'))
        for key in ('warehouse_id', 'category_id', 'location_id'):
            if filters.get(key) and (type(filters[key]) is not int or filters[key] < 1):
                raise ValidationError(_('Invalid stock filter.'))
        locations = scoped.env['stock.location'].with_context(active_test=False)
        locations.check_access('read')
        locations.check_field_access_rights('read', ['complete_name', 'usage', 'company_id', 'parent_path'])
        warehouses = scoped.env['stock.warehouse'].search([('company_id', '=', scoped.env.company.id)])
        location_domain = [('usage', '=', 'internal'), ('company_id', 'in', [False, scoped.env.company.id])]
        if filters.get('warehouse_id'):
            warehouse = warehouses.filtered(lambda w: w.id == filters['warehouse_id'])
            if not warehouse:
                raise AccessError(_('This warehouse is unavailable in the selected company.'))
            location_domain.append(('id', 'child_of', warehouse.view_location_id.id))
        if filters.get('location_id'):
            location_domain.append(('id', '=', filters['location_id']))
        locations = locations.search(location_domain, order='complete_name, id')
        if filters.get('location_id') and not locations:
            raise AccessError(_('This location is unavailable in the selected scope.'))
        if filters.get('category_id'):
            category = scoped.env['product.category'].search([('id', '=', filters['category_id'])], limit=1)
            if not category:
                raise AccessError(_('This product category is unavailable.'))
            domain.append(('categ_id', 'child_of', category.id))
        search = filters.get('search', '')
        if not isinstance(search, str) or len(search) > 100:
            raise ValidationError(_('Enter a product name or reference of up to 100 characters.'))
        if search.strip():
            domain += ['|', ('name', 'ilike', search.strip()), ('default_code', 'ilike', search.strip())]
        if filters.get('hide_zero') and filters.get('hide_negative'):
            domain.append(('qty_available', '>', 0))
        elif filters.get('hide_zero'):
            domain.append(('qty_available', '!=', 0))
        elif filters.get('hide_negative'):
            domain.append(('qty_available', '>=', 0))
        return scoped, dates, products, domain, locations, warehouses

    def _get_inventory_locations(self, options, offset, mode, filters):
        scoped, dates, products, domain, locations, warehouses = self._inventory_filter_scope(options, mode, filters)
        columns = ['display_name', 'default_code', 'qty_available', 'uom_id', 'active', 'categ_id']
        if mode == 'current':
            columns += ['free_qty', 'incoming_qty', 'outgoing_qty', 'virtual_available']
        products.check_field_access_rights('read', columns)
        rows, total = [], 0
        # Page product/location pairs, never product totals. Odoo computes and filters
        # the quantities with strict location semantics, including historical moves.
        for location in locations:
            scoped_products = products.with_context(location=location.id, strict=True)
            count = scoped_products.search_count(domain)
            local_offset = max(0, offset - total)
            if len(rows) < 25 and local_offset < count:
                selected = scoped_products.search(domain, order='default_code, id', offset=local_offset, limit=25 - len(rows))
                for row in selected.read(columns):
                    row['product_id'] = row['id']
                    row['id'] = f"{row['id']}:{location.id}"
                    row['location_id'] = location.id
                    row['location_name'] = location.complete_name
                    row['warehouse_name'] = ', '.join(warehouses.filtered(
                        lambda w: location.parent_path.startswith(w.view_location_id.parent_path)).mapped('name'))
                    rows.append(row)
            total += count
        return {'status': 'ready' if rows else 'empty', 'rows': rows, 'offset': offset,
                'total_count': total, 'has_more': offset + len(rows) < total, 'mode': mode,
                'filters': filters, 'by_location': True, 'date_basis': mode,
                'as_of': dates[2].isoformat() if mode == 'historical' else False,
                'company_id': scoped.env.company.id, 'currency': scoped.env.company.currency_id.name,
                'digits': scoped.env.company.currency_id.decimal_places,
                'warehouses': [{'id': w.id, 'name': w.display_name} for w in warehouses],
                'categories': [{'id': c.id, 'name': c.display_name} for c in scoped.env['product.category'].search([], order='complete_name')],
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'provenance': {'model': 'product.product', 'measure': columns,
                               'domain': domain, 'context': dict(products.env.context), 'location_ids': locations.ids}}

    @api.model
    def open_inventory_location(self, options, product_id, location_id, mode='current', filters=None):
        if type(product_id) is not int or product_id < 1:
            raise ValidationError(_('Invalid product.'))
        filters = dict(filters or {}, location_id=location_id)
        scoped, dates, products, domain, locations, warehouses = self._inventory_filter_scope(options, mode, filters)
        products = products.with_context(location=location_id, strict=True)
        domain = [*domain, ('id', '=', product_id)]
        if not products.search(domain, limit=1):
            raise AccessError(_('The product is unavailable in the selected scope.'))
        action = scoped.env['ir.actions.actions']._for_xml_id('stock.action_product_stock_view')
        action.update(domain=domain, context=dict(products.env.context))
        return action

    @api.model
    def get_inventory(self, options, offset=0, mode='current', filters=None):
        scoped, dates = self._scope(options)
        if type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid page.'))
        if 'stock.quant' not in scoped.env:
            return {'status': 'not_installed', 'rows': [], 'mode': mode}
        if filters is not None:
            return self._get_inventory_locations(options, offset, mode, filters)
        products, domain = scoped._stock_scope(dates, mode)
        columns = ['display_name', 'qty_available', 'uom_id', 'active']
        if mode == 'current':
            columns += ['free_qty', 'virtual_available']
        products.check_field_access_rights('read', columns)
        records = products.search(domain, order='id', offset=offset, limit=26)
        rows = records[:25].read(columns)
        value_status = 'not_installed'
        if 'total_value' in products._fields:
            try:
                products.check_field_access_rights('read', ['total_value', 'company_currency_id'])
                values = {r['id']: r for r in records[:25].read(['total_value', 'company_currency_id'])}
                for row in rows:
                    row['total_value'] = values[row['id']]['total_value']
                value_status = 'ready'
            except AccessError:
                value_status = 'restricted'
        return {'status': 'ready' if rows else 'empty', 'rows': rows,
                'has_more': len(records) > 25, 'date_basis': mode, 'mode': mode,
                'value_status': value_status, 'currency': scoped.env.company.currency_id.name,
                'digits': scoped.env.company.currency_id.decimal_places,
                'company_id': scoped.env.company.id, 'source': 'stock.action_product_stock_view',
                'as_of': dates[2].isoformat() if mode == 'historical' else False,
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'provenance': {'model': 'product.product', 'source_kind': 'native_report',
                    'backend_kind': 'operational_service', 'domain': domain,
                    'context': dict(products.env.context), 'measure': columns + (['total_value'] if value_status == 'ready' else [])}}

    @api.model
    def open_inventory(self, options, mode='current'):
        scoped, dates = self._scope(options)
        products, domain = scoped._stock_scope(dates, mode)
        action = scoped.env['ir.actions.actions']._for_xml_id('stock.action_product_stock_view')
        action.update(domain=domain, context=dict(products.env.context))
        return action

    @api.model
    def open_inventory_product(self, options, product_id, route):
        scoped, dates = self._scope(options)
        products, domain = scoped._stock_scope(dates, 'current')
        if type(product_id) is not int or product_id < 1 or route not in ('forecast', 'history', 'locations', 'replenishment'):
            raise ValidationError(_('Invalid inventory route.'))
        product = products.search([*domain, ('id', '=', product_id)], limit=1)
        if not product:
            raise AccessError(_('The record is unavailable in the selected scope.'))
        if route == 'forecast':
            action = product.action_product_forecast_report()
            action['context'] = {**scoped.env.context, 'active_id': product.id,
                                 'active_model': 'product.product', 'default_product_id': product.id}
            return action
        if route == 'replenishment':
            # The native method opens orderpoints; it does not order or replenish.
            scoped.env['stock.warehouse.orderpoint'].check_access('read')
            action = product.action_view_orderpoints()
            action['context'] = {**action['context'], **scoped.env.context}
            action['domain'] = [('product_id', '=', product.id), ('company_id', '=', scoped.env.company.id)]
            return action
        model, xmlid = ('stock.move.line', 'stock.stock_move_line_action') if route == 'history' else ('stock.quant', 'stock.action_view_quants')
        scoped.env[model].check_access('read')
        action = scoped.env['ir.actions.actions']._for_xml_id(xmlid)
        action.update(domain=[('product_id', '=', product.id), ('company_id', '=', scoped.env.company.id)],
                      context={**scoped.env.context, 'active_test': False})
        return action

    def _workforce_scope(self):
        if 'hr.employee' not in self.env or not self.env.user.has_group('hr.group_hr_user'):
            raise AccessError(_('HR reporting access is required.'))
        employees = self.env['hr.employee']
        employees.check_access('read')
        employees.check_field_access_rights('read', ['active', 'company_id', 'department_id'])
        return employees, [('active', '=', True), ('company_id', '=', self.env.company.id)]

    @api.model
    def get_workforce(self, options, offset=0):
        scoped, dates = self._scope(options)
        if type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid page.'))
        if 'hr.employee' not in scoped.env:
            return {'status': 'not_installed', 'rows': []}
        employees, domain = scoped._workforce_scope()
        groups = employees._read_group(domain, ['department_id'], ['__count'], order='department_id', limit=26, offset=offset)
        return {'status': 'ready' if groups else 'empty',
                'rows': [{'id': department.id or False, 'name': department.display_name if department else _('Unassigned'),
                          'count': count} for department, count in groups[:25]],
                'total': employees.search_count(domain), 'has_more': len(groups) > 25,
                'date_basis': 'current', 'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'provenance': {'model': 'hr.employee', 'source_kind': 'operational_records',
                    'domain': domain, 'measure': '__count', 'groupby': 'department_id', 'context': dict(scoped.env.context)}}

    @api.model
    def open_workforce(self, options, department_id=None):
        scoped, dates = self._scope(options)
        employees, domain = scoped._workforce_scope()
        if department_id is not None:
            if department_id is not False and (type(department_id) is not int or department_id < 1):
                raise ValidationError(_('Invalid report dimension.'))
            domain += [('department_id', '=', department_id)]
        action = scoped.env['ir.actions.actions']._for_xml_id('hr.open_view_employee_list')
        action.update(domain=domain, context=dict(scoped.env.context))
        return action

    def _procurement_scope(self, kind):
        if kind not in ('approvals', 'late') or 'purchase.order' not in self.env:
            raise ValidationError(_('This list is not configured.'))
        if not self.env.user.has_group('purchase.group_purchase_user'):
            raise AccessError(_('Purchase reporting access is required.'))
        orders = self.env['purchase.order']
        orders.check_access('read')
        orders.check_field_access_rights('read', ['company_id', 'state', 'is_late'])
        domain = [('company_id', '=', self.env.company.id)]
        domain += [('state', '=', 'to approve')] if kind == 'approvals' else [('state', '=', 'purchase'), ('is_late', '=', True)]
        return orders, domain

    @api.model
    def get_procurement(self, options, offset=0, kind='late'):
        scoped, dates = self._scope(options)
        if type(offset) is not int or not 0 <= offset <= 100000:
            raise ValidationError(_('Invalid page.'))
        if 'purchase.order' not in scoped.env:
            return {'status': 'not_installed', 'rows': [], 'mode': kind}
        orders, domain = scoped._procurement_scope(kind)
        columns = ['name', 'partner_id', 'date_order', 'date_planned', 'amount_untaxed', 'currency_id', 'state']
        orders.check_field_access_rights('read', columns)
        records = orders.search(domain, order='date_planned, id', offset=offset, limit=26)
        rows = records[:25].read(columns)
        for row, order in zip(rows, records[:25]):
            row.update(currency=order.currency_id.name, digits=order.currency_id.decimal_places,
                       date_label=fields.Datetime.context_timestamp(order, order.date_planned).strftime('%Y-%m-%d %H:%M') if order.date_planned else False)
        return {'status': 'ready' if rows else 'empty', 'rows': rows, 'mode': kind,
                'has_more': len(records) > 25, 'total': orders.search_count(domain), 'date_basis': 'current',
                'generated_at': fields.Datetime.to_string(fields.Datetime.now()),
                'provenance': {'model': 'purchase.order', 'source_kind': 'operational_records',
                               'domain': domain, 'context': dict(scoped.env.context)}}

    @api.model
    def open_procurement(self, options, kind='late', record_id=None):
        scoped, dates = self._scope(options)
        orders, domain = scoped._procurement_scope(kind)
        action = scoped.env['ir.actions.actions']._for_xml_id('purchase.purchase_form_action')
        action.update(domain=domain, context=dict(scoped.env.context))
        if record_id is not None:
            if type(record_id) is not int or record_id < 1:
                raise ValidationError(_('Invalid purchase record.'))
            if not orders.search([*domain, ('id', '=', record_id)], limit=1):
                raise AccessError(_('The record is unavailable in the selected scope.'))
            action.update(res_id=record_id, views=[(False, 'form')], view_mode='form')
        return action
