"""Cold-ORM synthetic timings; not customer-volume or browser qualification."""
from datetime import datetime, time, timedelta
import json
import logging
from pathlib import Path
import subprocess
from time import perf_counter

from odoo import api, fields
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

_logger = logging.getLogger(__name__)


@tagged('post_install', '-at_install')
class TestDashboardOperationalPerformance(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('stock.group_stock_manager')
        cls.env.user.tz = 'UTC'
        cls.today = fields.Date.today()
        cls.cutoff = cls.today - timedelta(days=1)
        cls.options = {'company_id': cls.env.company.id,
                       'date_from': (cls.today - timedelta(days=30)).isoformat(),
                       'date_to': cls.today.isoformat(), 'as_of': cls.cutoff.isoformat()}
        try:
            revision = subprocess.run(
                ['git', '-C', str(Path(__file__).resolve().parents[3]), 'rev-parse', 'HEAD'],
                capture_output=True, text=True, timeout=5, check=False)
            cls.source_sha = revision.stdout.strip() if revision.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired):
            cls.source_sha = None

    def _measure(self, name, params, dataset, invoke, verify):
        samples = []
        self.env.flush_all()
        for repetition in range(3):
            # Keep rollback-isolated records in this transaction. Clear all ORM
            # caches before a new Environment; do not claim cold PostgreSQL/OS
            # buffers or include fixture creation/reconciliation in timings.
            self.env.invalidate_all()
            context = dict(self.env.context, allowed_company_ids=[self.env.company.id],
                           operational_measurement=(name, repetition))
            environment = api.Environment(self.cr, self.env.uid, context)
            before_queries = self.cr.sql_log_count
            started = perf_counter()
            result = invoke(environment['adams.executive.dashboard'])
            seconds = perf_counter() - started
            queries = self.cr.sql_log_count - before_queries
            verify(result)
            samples.append({'repetition': repetition + 1, 'backend_seconds': seconds,
                            'query_count': queries, 'status': result.get('status'),
                            'returned_rows': len(result.get('rows', [])),
                            'total_rows': result.get('total_count', result.get('total'))})
        _logger.info('DASHBOARD_OPERATIONAL_PERFORMANCE %s', json.dumps({
            'case': name, 'parameters': params, 'dataset': dataset, 'samples': samples,
            'application_source_sha': self.source_sha, 'user_id': self.env.uid,
            'company_id': self.env.company.id, 'timezone': self.env.user.tz,
            'scope': 'backend ORM method only; no network/browser/concurrency timing',
            'cache_policy': 'invalidate_all before each fresh Environment; DB buffers uncontrolled',
            'synthetic': True, 'customer_volume_qualified': False,
            'performance_threshold_defined': False,
            'audit_dataset_comparison': False,
        }, sort_keys=True))

    def test_inventory_cold_orm_synthetic_measurements(self):
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
        locations = self.env['stock.location'].create([
            {'name': f'Performance shelf {index}', 'usage': 'internal',
             'location_id': warehouse.view_location_id.id, 'company_id': self.env.company.id}
            for index in range(2)])
        category = self.env['product.category'].create({'name': 'Operational performance fixture'})
        products = self.env['product.product'].create([
            {'name': f'Operational performance product {index:03}', 'default_code': f'PERF-{index:03}',
             'is_storable': True, 'company_id': self.env.company.id, 'categ_id': category.id}
            for index in range(250)])
        for index, product in enumerate(products):
            for location, quantity in ((locations[0], index % 11 - 3), (locations[1], index % 7)):
                if quantity:
                    self.env['stock.quant']._update_available_quantity(product, location, quantity)
        # Two native movements establish an actual cutoff difference, in
        # addition to signed/zero quantity fixture rows.
        for quantity, source, destination, day in (
                (10, self.env.ref('stock.stock_location_suppliers'), locations[0], self.cutoff),
                (2, locations[0], self.env.ref('stock.stock_location_customers'), self.today)):
            move = self.env['stock.move'].create({'product_id': products[0].id,
                'product_uom_qty': quantity, 'product_uom': products[0].uom_id.id,
                'location_id': source.id, 'location_dest_id': destination.id,
                'company_id': self.env.company.id})
            move._action_confirm()
            move.quantity = quantity
            move.picked = True
            move._action_done()
            stamp = datetime.combine(day, time.min)
            move.date = stamp
            move.move_line_ids.date = stamp
        self.env.flush_all()
        cutoff = fields.Datetime.to_string(datetime.combine(self.cutoff, time.max).replace(microsecond=0))
        native = {}
        for mode in ('current', 'historical'):
            for location in locations:
                context = {'allowed_company_ids': [self.env.company.id], 'location': location.id, 'strict': True}
                if mode == 'historical':
                    context['to_date'] = cutoff
                native[(mode, location.id)] = {row['id']: row['qty_available']
                    for row in products.with_context(context).read(['qty_available'])}
        self.assertEqual(native[('historical', locations[0].id)][products[0].id]
                         - native[('current', locations[0].id)][products[0].id], 2)
        base = {'category_id': category.id, 'hide_zero': True, 'hide_negative': False, 'sort': 'name'}
        scenarios = [
            ('broad_name_page_1', 0, 'current', base),
            ('broad_name_page_2', 25, 'current', base),
            ('warehouse_name', 0, 'current', dict(base, warehouse_id=warehouse.id)),
            ('single_location_zero_visible', 0, 'current', dict(base, location_id=locations[0].id, hide_zero=False)),
            ('global_quantity_sort', 0, 'current', dict(base, sort='qty')),
            ('historical_name', 0, 'historical', dict(base, at_date=self.cutoff.isoformat())),
            ('historical_quantity_sort', 25, 'historical', dict(base, sort='qty', at_date=self.cutoff.isoformat())),
        ]
        native_products = products.search([('id', 'in', products.ids)], order='name, id')
        native_locations = locations.search([('id', 'in', locations.ids)], order='complete_name, id')
        product_rank = {record.id: index for index, record in enumerate(native_products)}
        location_rank = {record.id: index for index, record in enumerate(native_locations)}
        product_name = {record.id: record.name.casefold() for record in products}
        location_name = {record.id: record.complete_name.casefold() for record in locations}
        dataset = {'products': 250, 'populated_location_candidates': 2,
                   'authorized_internal_locations': self.env['stock.location'].with_context(active_test=False).search_count([
                       ('usage', '=', 'internal'), ('company_id', 'in', [False, self.env.company.id])]),
                   'native_cutoff_movement_difference': 2, 'includes_negative_and_zero': True}
        for case, offset, mode, filters in scenarios:
            expected = []
            for location in locations:
                if filters.get('location_id') and filters['location_id'] != location.id:
                    continue
                for product in products:
                    quantity = native[(mode, location.id)][product.id]
                    if filters['hide_zero'] and not quantity:
                        continue
                    expected.append((location.id, product.id, quantity))
            if filters['sort'] == 'qty':
                expected.sort(key=lambda row: (-row[2], product_name[row[1]], location_name[row[0]], row[0], row[1]))
            else:
                expected.sort(key=lambda row: (product_rank[row[1]], location_rank[row[0]]))
            page = expected[offset:offset + 25]

            def verify(result, expected=expected, page=page, offset=offset):
                self.assertEqual(result['status'], 'ready')
                self.assertEqual(result['total_count'], len(expected))
                self.assertEqual(result['offset'], offset)
                self.assertLessEqual(len(result['rows']), 25)
                self.assertEqual([(row['location_id'], row['product_id'], row['qty_available'])
                                  for row in result['rows']], page)

            self._measure(case, {'offset': offset, 'mode': mode, 'filters': filters, 'options': self.options}, dataset,
                lambda service, offset=offset, mode=mode, filters=filters:
                    service.get_inventory(self.options, offset, mode, dict(filters)), verify)

    def test_hr_cold_orm_synthetic_measurements(self):
        if 'hr.employee' not in self.env:
            _logger.info('DASHBOARD_OPERATIONAL_PERFORMANCE %s', json.dumps({
                'case': 'hr_optional_capability', 'status': 'not_installed', 'synthetic': True}))
            return
        for xmlid in ('hr.group_hr_manager', 'hr_attendance.group_hr_attendance_manager',
                      'hr_holidays.group_hr_holidays_manager', 'planning.group_planning_manager'):
            group = self.env.ref(xmlid, raise_if_not_found=False)
            if group:
                self.env.user.group_ids |= group
        employees = self.env['hr.employee'].create([
            {'name': f'Operational performance employee {index:03}', 'company_id': self.env.company.id}
            for index in range(100)])
        if 'hr.attendance' in self.env:
            self.env['hr.attendance'].create([
                {'employee_id': employee.id, 'check_in': datetime.combine(self.cutoff, time(9)),
                 'check_out': datetime.combine(self.cutoff, time(17)) if index < 40 else False}
                for index, employee in enumerate(employees[:50])])
        self.env.flush_all()
        workforce = self.env['hr.employee'].search_count([('active', '=', True), ('company_id', '=', self.env.company.id)])
        employee_page = self.env['hr.employee'].search([('id', 'in', employees.ids)], order='name, id', offset=25, limit=25).ids
        dataset = {'employees_created': 100, 'authorized_active_workforce': workforce,
                   'attendance_sessions_created': 50 if 'hr.attendance' in self.env else 0,
                   'open_prior_day_sessions_created': 10 if 'hr.attendance' in self.env else 0}

        def verify_overview(result):
            self.assertEqual(result['status'], 'ready')
            count = next(metric for metric in result['metrics'] if metric['key'] == 'employees')
            self.assertEqual(count['status'], 'ready')
            self.assertEqual(count['value'], workforce)
            self.assertTrue(all(len(preview['rows']) <= 5 for preview in result.get('previews', {}).values()))

        def verify_employees(result):
            self.assertEqual(result['total'], 100)
            self.assertEqual([row['id'] for row in result['rows']], employee_page)
            self.assertLessEqual(len(result['rows']), 25)

        def verify_profile(result):
            self.assertEqual(result['status'], 'ready')
            self.assertEqual(result['employee']['id'], employees[0].id)
            self.assertEqual(result['employee']['name'], employees[0].name)
            self.assertTrue(set(result['employee']) <= {'id', 'name', 'active', 'department_id', 'job_id',
                'parent_id', 'work_email', 'work_phone', 'work_location_id', 'resource_calendar_id'})
            attendance = next(summary for summary in result['summaries'] if summary['tab'] == 'attendance')
            if 'hr.attendance' in self.env:
                self.assertEqual(attendance['status'], 'ready')
                self.assertEqual(attendance['count'], 1)

        cases = [
            ('hr_overview', {'tab': 'overview'}, lambda service: service.get_hr_workspace(self.options), verify_overview),
            ('hr_employee_page', {'tab': 'employees', 'offset': 25, 'search': 'Operational performance employee'},
             lambda service: service.get_hr_workspace(self.options, 'employees', {'search': 'Operational performance employee'}, 25), verify_employees),
            ('hr_employee_profile', {'employee_id': employees[0].id},
             lambda service: service.get_employee_profile(self.options, employees[0].id), verify_profile),
        ]
        for name, params, invoke, verify in cases:
            self._measure(name, dict(params, options=self.options), dataset, invoke, verify)

    def test_sparse_locations_with_cross_category_kit_measurements(self):
        if 'mrp.bom' not in self.env:
            self.skipTest('Optional Manufacturing is not installed')
        from functools import wraps
        from unittest.mock import patch
        from odoo import Command
        warehouse = self.env['stock.warehouse'].create({'name': 'Sparse location performance',
            'code': 'SPRF', 'company_id': self.env.company.id})
        location_domain = [('id', 'child_of', warehouse.view_location_id.id), ('usage', '=', 'internal')]
        locations_model = self.env['stock.location'].with_context(active_test=False)
        existing = locations_model.search(location_domain)
        self.assertLess(len(existing), 254)
        locations_model.create([{'name': f'Sparse shelf {index:03}', 'usage': 'internal',
            'location_id': warehouse.view_location_id.id, 'company_id': self.env.company.id}
            for index in range(254 - len(existing))])
        locations = locations_model.search(location_domain, order='complete_name, id')
        self.assertEqual(len(locations), 254)
        category = self.env['product.category'].create({'name': 'Sparse kit category'})
        component_category = self.env['product.category'].create({'name': 'Sparse component category'})
        component = self.env['product.product'].create({'name': 'Sparse kit component', 'is_storable': True,
            'company_id': self.env.company.id, 'categ_id': component_category.id})
        kit = self.env['product.product'].create({'name': 'Sparse quantity kit', 'is_storable': True,
            'company_id': self.env.company.id, 'categ_id': category.id})
        self.env['mrp.bom'].create({'product_tmpl_id': kit.product_tmpl_id.id, 'product_id': kit.id,
            'type': 'phantom', 'product_qty': 1, 'product_uom_id': kit.uom_id.id,
            'company_id': self.env.company.id,
            'bom_line_ids': [Command.create({'product_id': component.id, 'product_qty': 2,
                                            'product_uom_id': component.uom_id.id})]})
        for location in locations[:31]:
            self.env['stock.quant']._update_available_quantity(component, location, 8)
        native = {location.id: kit.with_context(location=location.id, strict=True).qty_available
                  for location in locations}
        eligible = [location.id for location in locations if native[location.id] != 0]
        self.assertEqual(len(eligible), 31)
        filters = {'warehouse_id': warehouse.id, 'category_id': category.id, 'hide_zero': True, 'sort': 'name'}
        calls = []
        products_type = type(self.env['product.product'])
        original = products_type._search_qty_available
        @wraps(original)
        def counted(records, *args, **kwargs):
            calls.append(records.env.context.get('location'))
            return original(records, *args, **kwargs)
        for offset in (0, 25):
            def invoke(dashboard, offset=offset):
                calls.clear()
                return dashboard.get_inventory(self.options, offset=offset, filters=filters)
            def verify(result, offset=offset):
                self.assertEqual(result['total_count'], len(eligible))
                self.assertEqual([row['location_id'] for row in result['rows']], eligible[offset:offset + 25])
                self.assertEqual(len(calls), 31)
                self.assertEqual(set(calls), set(eligible))
                self.assertEqual(len(result['provenance']['location_ids']), 254)
                for row in result['rows']:
                    self.assertEqual(row['product_id'], kit.id)
                    self.assertEqual(row['qty_available'], native[row['location_id']])
            with patch.object(products_type, '_search_qty_available', counted):
                self._measure('sparse_254_locations_31_occupied_kit_page_%s' % offset,
                    {'options': self.options, 'filters': filters, 'offset': offset},
                    {'selected_locations': 254, 'occupied_locations': 31, 'kit_products': 1,
                     'component_products': 1, 'component_category_differs': True}, invoke, verify)
