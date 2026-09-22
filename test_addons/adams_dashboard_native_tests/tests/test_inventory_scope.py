"""Native B01/B05 regressions; must run with stock_account installed."""
from lxml import etree
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import new_test_user, tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged('post_install', '-at_install')
class TestDashboardInventoryScope(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids |= cls.env.ref('stock.group_stock_manager')
        cls.dashboard = cls.env['adams.executive.dashboard']
        cls.options = {'company_id': cls.env.company.id, 'date_from': '2026-08-01',
                       'date_to': '2026-08-31', 'as_of': '2026-08-31'}
        cls.warehouse = cls.env['stock.warehouse'].search([('company_id', '=', cls.env.company.id)], limit=1)
        cls.location = cls.warehouse.lot_stock_id
        cls.product = cls.env['product.product'].create({'name': 'Scope regression stock', 'is_storable': True})

    def test_location_action_removes_value_columns_without_contaminating_native_view(self):
        self.env['stock.quant']._update_available_quantity(self.product, self.location, 12)
        action = self.dashboard.open_inventory_location(self.options, self.product.id, self.location.id)
        product = self.product.with_context(action['context'])
        view_id = self.env.ref('stock.product_product_stock_tree').id
        view_context = {key: value for key, value in action['context'].items()
                        if key == 'lang' or key.endswith('_view_ref')}
        product_view = self.product.with_context(view_context)
        original_arch = self.product.get_view(view_id, 'list')['arch']
        quantity_view = etree.fromstring(product_view.get_view(view_id, 'list')['arch'])
        self.assertFalse(quantity_view.xpath("//field[@name='total_value' or @name='avg_cost']"))
        self.assertTrue(quantity_view.xpath("//field[@name='qty_available']"))
        self.assertEqual(product.qty_available, 12)
        self.assertEqual(self.product.get_view(view_id, 'list')['arch'], original_arch)
        native_view = etree.fromstring(original_arch)
        self.assertTrue(native_view.xpath("//field[@name='total_value']"))
        # Inverse call order also must not leak the cached native architecture.
        quantity_again = etree.fromstring(product.get_view(view_id, 'list')['arch'])
        self.assertFalse(quantity_again.xpath("//field[@name='total_value']"))

    def test_valuation_scope_discards_location_and_validates_warehouse(self):
        dashboard = self.dashboard.with_context(location=self.location.id, strict=True, to_date='2000-01-01')
        action = dashboard.open_inventory_valuation(self.options, filters={'warehouse_id': self.warehouse.id}, product_id=self.product.id)
        self.assertEqual(action['context']['warehouse_id'], self.warehouse.id)
        self.assertNotIn('location', action['context'])
        self.assertNotIn('strict', action['context'])
        self.assertNotIn('to_date', action['context'])
        self.assertNotIn('adams_dashboard_quantity_view_ref', action['context'])
        company_action = dashboard.open_inventory_valuation(self.options)
        self.assertNotIn('warehouse_id', company_action['context'])
        with self.assertRaises(AccessError):
            dashboard.open_inventory_valuation(self.options, filters={'warehouse_id': 2147483647})
        with self.assertRaises(ValidationError):
            dashboard.open_inventory_valuation(self.options, product_id=True)

    def test_location_rows_reconcile_native_zero_negative_and_child_quantities(self):
        child = self.env['stock.location'].create({'name': 'Child stock', 'usage': 'internal',
            'location_id': self.location.id, 'company_id': self.env.company.id})
        self.env['stock.quant']._update_available_quantity(self.product, self.location, -2)
        self.env['stock.quant']._update_available_quantity(self.product, child, 12)
        for hide_zero, hide_negative in ((False, False), (True, False), (False, True), (True, True)):
            filters = {'location_id': self.location.id, 'search': self.product.name,
                       'hide_zero': hide_zero, 'hide_negative': hide_negative}
            result = self.dashboard.get_inventory(self.options, filters=filters)
            native = self.product.with_context(location=self.location.id, strict=True).qty_available
            self.assertEqual(native, -2)
            self.assertEqual(result['total_count'], 0 if hide_negative else 1)
            if result['rows']:
                self.assertEqual(result['rows'][0]['qty_available'], native)

    def test_new_valuation_rpc_preserves_dashboard_and_stock_access(self):
        reader = new_test_user(self.env, login='inventory_scope_reader',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_inventory_valuation(self.options)

    def test_global_quantity_sort_spans_locations_pages_and_recovers_shrunken_page(self):
        child = self.env['stock.location'].create({'name': 'Sort child', 'usage': 'internal',
            'location_id': self.location.id, 'company_id': self.env.company.id})
        products = self.env['product.product'].create([
            {'name': f'Dashboard sorting fixture {index:02}', 'is_storable': True}
            for index in range(26)])
        for index, product in enumerate(products):
            self.env['stock.quant']._update_available_quantity(product, self.location, index + 1)
        self.env['stock.quant']._update_available_quantity(products[0], child, 1000)
        self.env.flush_all()
        filters = {'warehouse_id': self.warehouse.id, 'search': 'Dashboard sorting fixture',
                   'hide_zero': True, 'sort': 'qty'}
        first = self.dashboard.get_inventory(self.options, filters=filters)
        second = self.dashboard.get_inventory(self.options, offset=25, filters=filters)
        self.assertEqual(first['total_count'], 27)
        self.assertEqual(first['rows'][0]['location_id'], child.id)
        self.assertEqual(first['rows'][0]['product_id'], products[0].id)
        actual = first['rows'] + second['rows']
        self.assertEqual([row['qty_available'] for row in actual], [1000] + list(range(26, 0, -1)))
        for row in actual:
            native = products.browse(row['product_id']).with_context(location=row['location_id'], strict=True)
            self.assertEqual(row['qty_available'], native.qty_available)
        names = self.dashboard.get_inventory(self.options, filters=dict(filters, sort='name'))
        self.assertEqual([row['product_id'] for row in names['rows'][:2]], [products[0].id, products[0].id])
        # A removed final page returns the last valid page, including its offset.
        for product in products[1:]:
            self.env['stock.quant']._update_available_quantity(product, self.location,
                -product.with_context(location=self.location.id, strict=True).qty_available)
        recovered = self.dashboard.get_inventory(self.options, offset=25, filters=filters)
        self.assertEqual(recovered['offset'], 0)
        self.assertEqual(recovered['total_count'], 2)
        self.assertEqual(len(recovered['rows']), 2)
        with self.assertRaises(ValidationError):
            self.dashboard.get_inventory(self.options, filters=dict(filters, sort='standard_price'))

    def test_global_stock_sources_use_allowed_models_scope_and_permissions(self):
        # Warehouse input/output locations can be archived when its steps are
        # changed. Their historical movements must remain reachable. Scope is
        # internal usage and selected company/warehouse, not active-only.
        archived = self.env['stock.location'].create({'name': 'Archived source shelf', 'usage': 'internal',
            'location_id': self.warehouse.view_location_id.id, 'company_id': self.env.company.id, 'active': False})
        external = self.env['stock.location'].create({'name': 'External source fixture', 'usage': 'supplier',
            'location_id': self.warehouse.view_location_id.id, 'company_id': self.env.company.id})
        expected_locations = self.env['stock.location'].with_context(active_test=False).search([
            ('usage', '=', 'internal'), ('company_id', 'in', [False, self.env.company.id]),
            ('id', 'child_of', self.warehouse.view_location_id.id)], order='complete_name, id')
        self.assertIn(archived, expected_locations)
        self.assertNotIn(external, expected_locations)
        for route, model in [('history', 'stock.move.line'), ('replenishment', 'stock.warehouse.orderpoint')]:
            action = self.dashboard.open_inventory_source(self.options, route, {'warehouse_id': self.warehouse.id})
            self.assertEqual(action['res_model'], model)
            self.assertIn(('company_id', '=', self.env.company.id), action['domain'])
            self.assertIn(('location_id', 'in', expected_locations.ids), action['domain'])
            if route == 'history':
                self.assertIn(('location_dest_id', 'in', expected_locations.ids), action['domain'])
        with self.assertRaises(ValidationError):
            self.dashboard.open_inventory_source(self.options, 'forecast')
        reader = new_test_user(self.env, login='global_stock_source_reader',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id, company_ids=[Command.set(self.env.company.ids)])
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_inventory_source(self.options, 'replenishment')

    def test_name_sort_reads_only_page_window_and_matches_native_collation(self):
        prefix = 'Dashboard bounded read fixture'
        products = self.env['product.product'].create([
            {'name': f'{prefix} {name} {index:02}', 'is_storable': True}
            for index, name in enumerate(['A', 'a', 'Á', 'آ', 'Z'] * 12)])
        native = products.search([('id', 'in', products.ids)], order='name, id')
        product_class = type(self.env['product.product'])
        original_search = product_class.search
        reads = []

        def tracked_search(records, domain, *args, **kwargs):
            if any(isinstance(term, (tuple, list)) and len(term) == 3
                   and term[0] == 'name' and term[2] == prefix for term in domain):
                reads.append((kwargs.get('offset', 0), kwargs.get('limit')))
            return original_search(records, domain, *args, **kwargs)

        filters = {'location_id': self.location.id, 'search': prefix,
                   'hide_zero': False, 'hide_negative': False, 'sort': 'name'}
        with patch.object(product_class, 'search', tracked_search):
            page = self.dashboard.get_inventory(self.options, offset=25, filters=filters)
        self.assertEqual(page['total_count'], 60)
        self.assertEqual([row['product_id'] for row in page['rows']], native[25:50].ids)
        self.assertEqual(reads, [(25, 25)],
                         'Name sort without quantity predicates must read one product page, not the catalog')

    def test_current_reservations_reconcile_native_quants_and_exact_source(self):
        category = self.env['product.category'].create({'name': 'Reservation category'})
        self.product.categ_id = category
        child = self.env['stock.location'].create({'name': 'Reservation child', 'usage': 'internal',
            'location_id': self.location.id, 'company_id': self.env.company.id})
        quants = self.env['stock.quant']
        quants._update_available_quantity(self.product, self.location, 12)
        quants._update_reserved_quantity(self.product, self.location, 3)
        quants._update_available_quantity(self.product, child, 20)
        quants._update_reserved_quantity(self.product, child, 7)
        filters = {'location_id': self.location.id, 'search': self.product.name, 'hide_zero': False}
        result = self.dashboard.get_inventory(self.options, filters=filters)
        self.assertEqual(len(result['rows']), 1)
        row = result['rows'][0]
        self.assertEqual(row['categ_id'][0], self.product.categ_id.id)
        self.assertEqual(row['reserved_quantity'], 3)
        self.assertEqual(row['free_qty'], self.product.with_context(location=self.location.id, strict=True).free_qty)
        action = self.dashboard.open_inventory_reservations(self.options, self.product.id, self.location.id, filters)
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.quant')
        source = quants.with_context(action['context']).search(action['domain'])
        self.assertEqual(source.location_id, self.location)
        self.assertEqual(source.product_id, self.product)
        self.assertEqual(sum(source.mapped('reserved_quantity')), row['reserved_quantity'])
        view = etree.fromstring(quants.get_view(action['views'][0][0], 'list')['arch'])
        self.assertTrue(view.xpath("//field[@name='reserved_quantity']"))
        historical = self.dashboard.get_inventory(self.options, mode='historical', filters=filters)
        self.assertTrue(historical['rows'])
        self.assertNotIn('reserved_quantity', historical['rows'][0])
        # Category is optional in this native build: preserve its empty value.
        self.product.categ_id = False
        uncategorized = self.dashboard.get_inventory(self.options, filters=filters)['rows'][0]
        self.assertFalse(uncategorized['categ_id'])
        self.assertEqual(uncategorized['reserved_quantity'], 3)
        with self.assertRaises(ValidationError):
            self.dashboard.open_inventory_reservations(self.options, True, self.location.id)
        with self.assertRaises(AccessError):
            self.dashboard.open_inventory_reservations(self.options, self.product.id, 2147483647)
        reader = new_test_user(self.env, login='reservation_denied',
            groups='base.group_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id)
        with self.assertRaises(AccessError):
            self.dashboard.with_user(reader).open_inventory_reservations(self.options, self.product.id, self.location.id)

    def test_kit_reservations_are_direct_quants_not_derived_availability(self):
        if 'mrp.bom' not in self.env:
            self.skipTest('Optional Manufacturing is not installed')
        component = self.env['product.product'].create({'name': 'Reservation component', 'is_storable': True})
        kit = self.env['product.product'].create({'name': 'Direct reservation kit', 'is_storable': True})
        self.env['mrp.bom'].create({'product_tmpl_id': kit.product_tmpl_id.id, 'product_id': kit.id,
            'type': 'phantom', 'product_qty': 1, 'product_uom_id': kit.uom_id.id,
            'company_id': self.env.company.id,
            'bom_line_ids': [Command.create({'product_id': component.id, 'product_qty': 1,
                                            'product_uom_id': component.uom_id.id})]})
        self.env['stock.quant']._update_available_quantity(component, self.location, 12)
        self.env['stock.quant']._update_reserved_quantity(component, self.location, 3)
        row = self.dashboard.get_inventory(self.options, filters={'location_id': self.location.id,
            'search': kit.name, 'hide_zero': False})['rows'][0]
        native = kit.with_context(location=self.location.id, strict=True)
        self.assertEqual(row['qty_available'], native.qty_available)
        self.assertEqual(row['free_qty'], native.free_qty)
        self.assertGreater(row['qty_available'] - row['free_qty'], 0)
        self.assertEqual(row['reserved_quantity'], 0)
        action = self.dashboard.open_inventory_reservations(self.options, kit.id, self.location.id)
        self.assertFalse(self.env['stock.quant'].search(action['domain']))
        kit.categ_id = self.env['product.category'].create({'name': 'Kit category only'})
        component.categ_id = self.env['product.category'].create({'name': 'Different component category'})
        filtered = self.dashboard.get_inventory(self.options, filters={'location_id': self.location.id,
            'category_id': kit.categ_id.id, 'hide_zero': True})
        self.assertEqual(filtered['total_count'], 1)
        self.assertEqual(filtered['rows'][0]['product_id'], kit.id)
        self.assertEqual(filtered['rows'][0]['qty_available'], native.qty_available)

    def test_legacy_product_locations_returns_scoped_window_not_server_action(self):
        other = self.env['product.product'].create({'name': 'Excluded location product', 'is_storable': True})
        quants = self.env['stock.quant']
        quants._update_available_quantity(self.product, self.location, 4)
        quants._update_available_quantity(other, self.location, 9)
        action = self.dashboard.open_inventory_product(self.options, self.product.id, 'locations')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'stock.quant')
        self.assertEqual(action['views'], [(self.env.ref('stock.view_stock_quant_tree').id, 'list')])
        self.assertIn(('company_id', '=', self.env.company.id), action['domain'])
        records = quants.with_context(action['context']).search(action['domain'])
        self.assertTrue(records)
        self.assertEqual(records.product_id, self.product)
        self.assertEqual(records.company_id, self.env.company)
        self.assertFalse(action['context']['edit'])
        self.assertFalse(action['context']['create'])
        self.assertFalse(action['context']['delete'])
        with self.assertRaises(AccessError):
            self.dashboard.open_inventory_product(self.options, 2147483647, 'locations')

    def test_empty_location_prefilter_preserves_native_signs_zero_modes_and_fallback(self):
        locations = self.env['stock.location'].create([
            {'name': 'Existence %s' % label, 'usage': 'internal', 'location_id': self.location.id,
             'company_id': self.env.company.id} for label in ('positive', 'negative', 'zero', 'empty')])
        for location, quantity in zip(locations[:3], (4, -2, 0)):
            self.env['stock.quant']._update_available_quantity(self.product, location, quantity)
        scoped, dates = self.dashboard._scope(self.options)
        products, _domain = scoped._stock_scope(dates, 'current')
        candidates = scoped._inventory_nonzero_locations(products, locations, 'current', {'hide_zero': True})
        self.assertEqual(candidates, locations[:3])  # Zero quants are not interpreted or summed.
        self.assertEqual(scoped._inventory_nonzero_locations(products, locations, 'current',
                         {'hide_zero': False, 'hide_negative': True}), locations)
        for location in locations:
            for hide_zero, hide_negative in ((True, False), (True, True), (False, True)):
                filters = {'location_id': location.id, 'search': self.product.name,
                           'hide_zero': hide_zero, 'hide_negative': hide_negative}
                native = self.product.with_context(location=location.id, strict=True).qty_available
                expected = not ((hide_zero and native == 0) or (hide_negative and native < 0))
                result = self.dashboard.get_inventory(self.options, filters=filters)
                self.assertEqual(result['total_count'], int(expected))
                self.assertEqual(result['provenance']['location_ids'], [location.id])
                if expected:
                    self.assertEqual(result['rows'][0]['qty_available'], native)
        # An unknown installed adapter must retain the old full native path.
        original = type(products)._compute_quantities_dict
        def custom_quantities(records, *args, **kwargs):
            return original(records, *args, **kwargs)
        with patch.object(type(products), '_compute_quantities_dict', custom_quantities):
            self.assertEqual(scoped._inventory_nonzero_locations(products, locations, 'current',
                             {'hide_zero': True}), locations)
        reader = new_test_user(self.env, login='existence_no_stock', groups='base.group_user',
                               company_id=self.env.company.id)
        with self.assertRaises(AccessError):
            scoped.with_user(reader)._inventory_nonzero_locations(products.with_user(reader), locations,
                                                                  'current', {'hide_zero': True})

    def test_historical_prefilter_retains_done_move_location_without_current_quants(self):
        location = self.env['stock.location'].create({'name': 'Historical empty now', 'usage': 'internal',
            'location_id': self.location.id, 'company_id': self.env.company.id})
        quants = self.env['stock.quant']
        quants._update_available_quantity(self.product, location, 7)
        move = self.env['stock.move'].create({'product_id': self.product.id, 'product_uom_qty': 7,
            'product_uom': self.product.uom_id.id, 'location_id': location.id,
            'location_dest_id': self.env.ref('stock.stock_location_customers').id,
            'company_id': self.env.company.id})
        move._action_confirm()
        move.quantity = 7
        move.picked = True
        move._action_done()
        move.date = '2026-09-01 12:00:00'
        move.move_line_ids.date = move.date
        emptied = quants.search([('product_id', '=', self.product.id), ('location_id', '=', location.id)])
        self.assertTrue(all(quant.quantity == 0 and quant.reserved_quantity == 0 for quant in emptied))
        emptied.unlink()
        filters = {'location_id': location.id, 'search': self.product.name, 'hide_zero': True,
                   'at_date': '2026-08-31'}
        self.assertEqual(self.dashboard.get_inventory(self.options, filters=filters)['total_count'], 0)
        historical = self.dashboard.get_inventory(self.options, mode='historical', filters=filters)
        action = self.dashboard.open_inventory_location(self.options, self.product.id, location.id,
                                                        mode='historical', filters=filters)
        native = self.product.with_context(action['context']).qty_available
        self.assertEqual(native, 7)
        self.assertEqual(historical['total_count'], 1)
        self.assertEqual(historical['rows'][0]['qty_available'], native)

    def test_prefilter_falls_back_for_rebound_field_and_unknown_quant_delegate(self):
        scoped, dates = self.dashboard._scope(self.options)
        products, _domain = scoped._stock_scope(dates, 'current')
        location = self.env['stock.location'].create({'name': 'Unknown quantity source', 'usage': 'internal',
            'location_id': self.location.id, 'company_id': self.env.company.id})
        field = products._fields['qty_available']
        for binding, replacement in (('compute', '_custom_quantity_compute'), ('search', '_custom_quantity_search')):
            with patch.object(field, binding, replacement):
                self.assertEqual(scoped._inventory_nonzero_locations(products, location, 'current',
                                 {'hide_zero': True}), location)
        original = type(products)._search_field_by_quants
        def custom_delegate(records, *args, **kwargs):
            return original(records, *args, **kwargs)
        with patch.object(type(products), '_search_field_by_quants', custom_delegate):
            self.assertEqual(scoped._inventory_nonzero_locations(products, location, 'current',
                             {'hide_zero': True}), location)

    def test_prefilter_does_not_convert_denied_quantity_field_into_empty_result(self):
        reader = new_test_user(self.env, login='existence_restricted_field',
            groups='base.group_user,stock.group_stock_user,adams_executive_dashboard.group_dashboard_user',
            company_id=self.env.company.id)
        self.assertFalse(reader.has_group('base.group_system'))
        location = self.env['stock.location'].create({'name': 'Restricted quantity empty location',
            'usage': 'internal', 'location_id': self.location.id, 'company_id': self.env.company.id})
        dashboard = self.dashboard.with_user(reader)
        filters = {'location_id': location.id, 'search': self.product.name, 'hide_zero': True}
        # Scope itself is allowed and empty. The quantity field restriction
        # must still raise instead of allowing the prefilter to report zero.
        self.assertEqual(dashboard.get_inventory(self.options, filters=filters)['total_count'], 0)
        for model_name, field_name, mode in (
                ('stock.quant', 'quantity', 'current'),
                ('stock.quant', 'reserved_quantity', 'current'),
                ('stock.move', 'quantity', 'historical')):
            source = self.env[model_name].with_user(reader)
            field = source._fields[field_name]
            with patch.object(field, 'groups', 'base.group_system'):
                with self.assertRaises(AccessError):
                    source.check_field_access_rights('read', [field_name])
                with self.assertRaises(AccessError):
                    dashboard.get_inventory(self.options, mode=mode, filters=filters)
