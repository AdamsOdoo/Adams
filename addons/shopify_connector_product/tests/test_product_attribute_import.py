import odoo
from odoo import api
from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


class TestProductAttributeImport(TransactionCase):
    """D-010B-2: options -> attributes -> values -> lines, the existing
    attribute compatibility gate, and the DB-backed global serialization
    lock (with a real concurrent-transaction proof)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Attribute Import Test Store',
            'shop_domain': 'attribute-import-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']
        cls.Settings = cls.env['shopify.connector.store.settings']
        cls.Attribute = cls.env['product.attribute']
        cls.AttributeValue = cls.env['product.attribute.value']

    # ------------------------------------------------------------------
    # Payload builders (normalized shape consumed by _apply_import).
    # ------------------------------------------------------------------

    def _option(self, name, values, position=1):
        return {'name': name, 'position': position, 'values': list(values)}

    def _variant(self, gid, selected, sku=None, barcode=None, price=None,
                 compare_at=None, image_url=None):
        return {
            'gid': gid, 'sku': sku, 'barcode': barcode, 'price': price,
            'compare_at_price': compare_at,
            'selected_options': selected,
            'option_values': ' / '.join(
                '%s: %s' % (s['name'], s['value']) for s in selected
            ) or None,
            'image_url': image_url,
        }

    def _payload(self, gid, options, variants, title='Structured Product',
                 status='active', image_url=None):
        return {
            'gid': gid, 'title': title, 'status': status, 'updated_at': None,
            'image_url': image_url, 'options': options, 'variants': variants,
        }

    def _set_conflict_mode(self, mode):
        self.Settings.create({
            'store_id': self.store.id,
            'product_import_attribute_conflict_mode': mode,
        })

    # ------------------------------------------------------------------
    # Attribute/value/line construction.
    # ------------------------------------------------------------------

    def test_create_new_dynamic_attribute_and_line(self):
        payload = self._payload(
            'gid://shopify/Product/2001',
            options=[self._option('Fabric', ['Cotton', 'Wool'])],
            variants=[
                self._variant('gid://shopify/ProductVariant/2001a',
                              [{'name': 'Fabric', 'value': 'Cotton'}], sku='F-COT'),
                self._variant('gid://shopify/ProductVariant/2001b',
                              [{'name': 'Fabric', 'value': 'Wool'}], sku='F-WOOL'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        attribute = self.Attribute.search([('name', '=', 'Fabric')])
        self.assertEqual(len(attribute), 1)
        self.assertEqual(attribute.create_variant, 'dynamic')
        template = result['template_binding'].product_template_id
        self.assertEqual(len(template.attribute_line_ids), 1)
        self.assertEqual(template.attribute_line_ids.attribute_id, attribute)
        self.assertEqual(
            set(template.attribute_line_ids.value_ids.mapped('name')),
            {'Cotton', 'Wool'},
        )
        self.assertEqual(len(result['variant_bindings']), 2)

    def test_case_insensitive_compatible_dynamic_reuse(self):
        existing = self.Attribute.create({
            'name': 'Color', 'create_variant': 'dynamic',
        })
        payload = self._payload(
            'gid://shopify/Product/2002',
            options=[self._option('color', ['Red', 'Blue'])],  # different case
            variants=[
                self._variant('gid://shopify/ProductVariant/2002a',
                              [{'name': 'color', 'value': 'Red'}], sku='CI-RED'),
                self._variant('gid://shopify/ProductVariant/2002b',
                              [{'name': 'color', 'value': 'Blue'}], sku='CI-BLUE'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertEqual(template.attribute_line_ids.attribute_id, existing)
        # No second Color attribute was created.
        self.assertEqual(
            self.Attribute.with_context(active_test=False).search_count(
                [('name', '=ilike', 'color')]
            ), 1,
        )

    def test_additive_value_reuses_existing_value_case_insensitive(self):
        attribute = self.Attribute.create({
            'name': 'Shade', 'create_variant': 'dynamic',
        })
        self.AttributeValue.create({'name': 'Red', 'attribute_id': attribute.id})
        payload = self._payload(
            'gid://shopify/Product/2003',
            options=[self._option('Shade', ['red', 'Green'])],  # 'red' reuses 'Red'
            variants=[
                self._variant('gid://shopify/ProductVariant/2003a',
                              [{'name': 'Shade', 'value': 'red'}], sku='SH-RED'),
                self._variant('gid://shopify/ProductVariant/2003b',
                              [{'name': 'Shade', 'value': 'Green'}], sku='SH-GRN'),
            ],
        )
        self.Importer._apply_import(self.store, payload)
        self.assertEqual(
            self.AttributeValue.search_count([
                ('attribute_id', '=', attribute.id),
                ('name', '=ilike', 'red'),
            ]), 1,
        )
        self.assertTrue(self.AttributeValue.search([
            ('attribute_id', '=', attribute.id), ('name', '=', 'Green'),
        ]))

    def test_default_title_creates_no_attribute_structure(self):
        payload = self._payload(
            'gid://shopify/Product/2004',
            options=[self._option('Title', ['Default Title'])],
            variants=[
                self._variant('gid://shopify/ProductVariant/2004',
                              [{'name': 'Title', 'value': 'Default Title'}],
                              sku='DT-1'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertFalse(template.attribute_line_ids)
        self.assertEqual(len(template.product_variant_ids), 1)
        self.assertEqual(len(result['variant_bindings']), 1)

    def test_option_position_order_preserved(self):
        # Normalization sorts options by position; a structured import
        # builds one line per option in that order.
        payload = self._payload(
            'gid://shopify/Product/2005',
            options=[
                self._option('Size', ['S'], position=2),
                self._option('Color', ['Red'], position=1),
            ],
            variants=[
                self._variant(
                    'gid://shopify/ProductVariant/2005',
                    [{'name': 'Color', 'value': 'Red'},
                     {'name': 'Size', 'value': 'S'}], sku='POS-1'),
            ],
        )
        # Pass options in position order (as _normalize_options would).
        payload['options'] = sorted(payload['options'], key=lambda o: o['position'])
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertEqual(len(template.attribute_line_ids), 2)
        self.assertEqual(
            template.attribute_line_ids[0].attribute_id.name, 'Color',
        )

    def test_normalize_options_sorts_by_position(self):
        options = self.Importer._normalize_options([
            {'name': 'Size', 'position': 3, 'optionValues': [{'name': 'S'}]},
            {'name': 'Color', 'position': 1, 'optionValues': [{'name': 'Red'}]},
            {'name': 'Fit', 'position': 2, 'optionValues': [{'name': 'Slim'}]},
        ])
        self.assertEqual([o['name'] for o in options], ['Color', 'Fit', 'Size'])

    # ------------------------------------------------------------------
    # Existing-attribute compatibility gate.
    # ------------------------------------------------------------------

    def _incompatible_payload(self, gid, option_name):
        return self._payload(
            gid,
            options=[self._option(option_name, ['Red', 'Blue'])],
            variants=[
                self._variant('%s/a' % gid, [{'name': option_name, 'value': 'Red'}],
                              sku='%s-RED' % option_name),
                self._variant('%s/b' % gid, [{'name': option_name, 'value': 'Blue'}],
                              sku='%s-BLUE' % option_name),
            ],
        )

    def test_existing_always_attribute_routes_manual_review_by_default(self):
        merchant = self.Attribute.create({
            'name': 'Color', 'create_variant': 'always',
        })
        templates_before = self.env['product.template'].search_count([])
        payload = self._incompatible_payload('gid://shopify/Product/2006', 'Color')
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        # Merchant attribute is never reused or mutated.
        self.assertEqual(merchant.create_variant, 'always')
        self.assertEqual(merchant.name, 'Color')
        # No phantom variants / partial import.
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )

    def test_existing_no_variant_attribute_routes_manual_review_by_default(self):
        merchant = self.Attribute.create({
            'name': 'Size', 'create_variant': 'no_variant',
        })
        payload = self._incompatible_payload('gid://shopify/Product/2007', 'Size')
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertEqual(merchant.create_variant, 'no_variant')

    def test_connector_owned_creates_distinct_shopify_attribute(self):
        merchant = self.Attribute.create({
            'name': 'Color', 'create_variant': 'always',
        })
        self._set_conflict_mode('connector_owned')
        payload = self._incompatible_payload('gid://shopify/Product/2008', 'Color')
        result = self.Importer._apply_import(self.store, payload)
        connector_attr = self.Attribute.search([('name', '=', 'Color (Shopify)')])
        self.assertEqual(len(connector_attr), 1)
        self.assertEqual(connector_attr.create_variant, 'dynamic')
        # Merchant attribute untouched.
        self.assertEqual(merchant.create_variant, 'always')
        self.assertEqual(merchant.name, 'Color')
        template = result['template_binding'].product_template_id
        self.assertEqual(template.attribute_line_ids.attribute_id, connector_attr)
        self.assertEqual(len(result['variant_bindings']), 2)

    def test_brownfield_incompatible_attribute_makes_no_phantom_variants(self):
        self.Attribute.create({'name': 'Color', 'create_variant': 'always'})
        products_before = self.env['product.product'].search_count([])
        payload = self._incompatible_payload('gid://shopify/Product/2009', 'Color')
        with self.assertRaises(JobHandlerError):
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(
            self.env['product.product'].search_count([]), products_before,
        )

    # ------------------------------------------------------------------
    # connector_owned refresh mapping (review 4950202231 item 6): refresh
    # must resolve the exact Shopify-name or exact "<name> (Shopify)" line.
    # ------------------------------------------------------------------

    def _run_connector_owned_refresh(self, gid, refresh_mode):
        self.Attribute.create({'name': 'Color', 'create_variant': 'always'})
        self.Settings.create({
            'store_id': self.store.id,
            'product_import_attribute_conflict_mode': 'connector_owned',
            'product_import_refresh_mode': refresh_mode,
        })
        first = self.Importer._apply_import(self.store, self._payload(
            gid,
            options=[self._option('Color', ['Red'])],
            variants=[self._variant('%s/r' % gid,
                                    [{'name': 'Color', 'value': 'Red'}], sku='%s-R' % gid[-4:])],
        ))
        template = first['template_binding'].product_template_id
        connector_attr = self.Attribute.search([('name', '=', 'Color (Shopify)')])
        self.assertEqual(template.attribute_line_ids.attribute_id, connector_attr)
        # Refresh: a new remote value + variant must extend Color (Shopify).
        second = self.Importer._apply_import(self.store, self._payload(
            gid,
            options=[self._option('Color', ['Red', 'Blue'])],
            variants=[
                self._variant('%s/r' % gid,
                              [{'name': 'Color', 'value': 'Red'}], sku='%s-R' % gid[-4:]),
                self._variant('%s/b' % gid,
                              [{'name': 'Color', 'value': 'Blue'}], sku='%s-B' % gid[-4:]),
            ],
        ))
        self.assertEqual(len(second['variant_bindings']), 2)
        self.assertEqual(len(template.product_variant_ids), 2)  # no phantom
        self.assertEqual(
            set(connector_attr.value_ids.mapped('name')), {'Red', 'Blue'},
        )
        # Merchant Color is never modified.
        merchant = self.Attribute.search([('name', '=', 'Color')])
        self.assertEqual(merchant.create_variant, 'always')
        self.assertFalse(merchant.value_ids)

    def test_connector_owned_refresh_extends_shopify_attribute_snapshot_only(self):
        self._run_connector_owned_refresh('gid://shopify/Product/2020', 'snapshot_only')

    def test_connector_owned_refresh_extends_shopify_attribute_shopify_fields(self):
        self._run_connector_owned_refresh('gid://shopify/Product/2021', 'shopify_fields')

    def test_refresh_fails_closed_when_both_plain_and_shopify_lines_exist(self):
        color = self.Attribute.create({'name': 'Color', 'create_variant': 'dynamic'})
        color_shopify = self.Attribute.create({
            'name': 'Color (Shopify)', 'create_variant': 'dynamic',
        })
        template = self.env['product.template'].create({
            'name': 'Ambiguous Color Lines',
            'attribute_line_ids': [
                (0, 0, {'attribute_id': color.id, 'value_ids': [
                    (0, 0, {'name': 'Red', 'attribute_id': color.id})]}),
                (0, 0, {'attribute_id': color_shopify.id, 'value_ids': [
                    (0, 0, {'name': 'Red', 'attribute_id': color_shopify.id})]}),
            ],
        })
        binding = self.TemplateBinding.create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/2022',
            'product_template_id': template.id,
            'match_key': 'manual',
        })
        payload = self._payload(
            'gid://shopify/Product/2022',
            options=[self._option('Color', ['Red', 'Blue'])],
            variants=[self._variant('gid://shopify/ProductVariant/2022b',
                                    [{'name': 'Color', 'value': 'Blue'}], sku='AMB-B')],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertTrue(binding.exists())

    # ------------------------------------------------------------------
    # DB-backed global serialization lock (D-010B-2) -- exercised on the REAL
    # product-import path across two independent, OVERLAPPING PostgreSQL
    # transactions (reviews 4950202231 item 7, 4950339305 item 5), not a
    # same-cursor test and not simultaneous execution: transaction B finishes
    # its import and stays uncommitted holding the lock, THEN transaction A
    # runs and contends for it.
    # ------------------------------------------------------------------

    def test_attribute_lock_row_is_seeded(self):
        self.assertTrue(
            self.env['shopify.connector.attribute.lock'].search([], limit=1)
        )

    def _conc_payload(self, gid, option_name, sku):
        return self._payload(
            gid,
            options=[self._option(option_name, ['Red'])],
            variants=[self._variant('%s/v' % gid,
                                    [{'name': option_name, 'value': 'Red'}], sku=sku)],
        )

    def _cleanup_concurrency(self, db, gids, store_ids, option_name):
        cr = db.cursor()
        try:
            env = api.Environment(cr, self.env.uid, {})
            TB = env['shopify.connector.product.template.binding']
            VB = env['shopify.connector.product.variant.binding']
            tbindings = TB.search([('shopify_gid', 'in', gids)])
            templates = tbindings.mapped('product_template_id')
            VB.search(
                [('product_template_binding_id', 'in', tbindings.ids)]
            ).unlink()
            tbindings.unlink()
            templates.exists().unlink()  # cascades variants, lines, PTAVs
            attrs = env['product.attribute'].with_context(active_test=False).search(
                ['|', ('name', '=ilike', option_name),
                 ('name', '=ilike', '%s (Shopify)' % option_name)])
            attrs.unlink()  # cascades its values
            env['shopify.connector.store.settings'].search(
                [('store_id', 'in', store_ids)]).unlink()
            env['shopify.connector.store'].browse(store_ids).exists().unlink()
            cr.commit()
        finally:
            cr.close()

    def test_overlapping_transactions_serialize_to_one_global_attribute(self):
        """Two independent, OVERLAPPING PostgreSQL transactions run the REAL
        `_apply_import` path for two products that use the same brand-new
        option name. This is deliberately NOT simultaneous full-import
        execution: transaction B completes its import first and stays open
        (uncommitted) holding the lock, and only THEN does transaction A run
        and contend for it.

        A `TransactionCase` cannot use `self.registry.cursor()` for this: in
        test mode it returns a `TestCursor` layered on the one test
        connection, so `FOR UPDATE SKIP LOCKED` would never contend. This
        test uses `odoo.sql_db.db_connect(...).cursor()` for separate PG
        backends, and a committed two-store setup visible to both.

        Transaction B runs a full import to completion and remains
        uncommitted, so it still holds the transaction-scoped singleton
        attribute lock (its per-product savepoint has been released, but --
        per review `4950339305` item 5 -- that does NOT release the row
        lock, which PostgreSQL holds until B commits). Transaction A then
        runs its own full import and cannot acquire the lock, so
        `_apply_import` raises `concurrency_race_conflict` (no duplicate
        attribute). After B commits and releases the lock, A is retried in a
        clean transaction, re-resolves, and reuses B's committed attribute.
        Exactly ONE global `product.attribute` exists, both product imports
        produce their bindings, and every committed synthetic record is
        cleaned up durably.
        """
        option_name = 'ConcFullImportShadeZZZ'
        gid_a = 'gid://shopify/Product/conc-a'
        gid_b = 'gid://shopify/Product/conc-b'
        self.assertFalse(
            self.Attribute.with_context(active_test=False).search(
                [('name', '=ilike', option_name)]))
        db = odoo.sql_db.db_connect(self.env.cr.dbname)

        # Committed synthetic stores, visible to both independent backends.
        cr_setup = db.cursor()
        try:
            env_setup = api.Environment(cr_setup, self.env.uid, {})
            Store = env_setup['shopify.connector.store']
            store_a_id = Store.create({
                'name': 'Conc Store A',
                'shop_domain': 'conc-a-test.myshopify.com',
                'api_version': '2026-07'}).id
            store_b_id = Store.create({
                'name': 'Conc Store B',
                'shop_domain': 'conc-b-test.myshopify.com',
                'api_version': '2026-07'}).id
            cr_setup.commit()
        finally:
            cr_setup.close()

        cr_a = db.cursor()
        cr_b = db.cursor()
        try:
            env_a = api.Environment(cr_a, self.env.uid, {})
            env_b = api.Environment(cr_b, self.env.uid, {})
            store_a = env_a['shopify.connector.store'].browse(store_a_id)
            store_b = env_b['shopify.connector.store'].browse(store_b_id)
            importer_a = env_a['shopify.connector.product.importer']
            importer_b = env_b['shopify.connector.product.importer']

            # B: full import runs to completion FIRST and stays uncommitted,
            # still holding the transaction-scoped attribute lock.
            result_b = importer_b._apply_import(
                store_b, self._conc_payload(gid_b, option_name, 'CONC-B'))
            self.assertTrue(result_b['variant_bindings'])

            # A: its import now overlaps B's open transaction and cannot
            # acquire the lock B still holds.
            with self.assertRaises(JobHandlerError) as ctx:
                importer_a._apply_import(
                    store_a, self._conc_payload(gid_a, option_name, 'CONC-A'))
            self.assertEqual(
                ctx.exception.error_class, 'concurrency_race_conflict')

            # B commits -> attribute committed, lock released.
            cr_b.commit()

            # A retried in a clean transaction -> reuses B's attribute.
            cr_a.rollback()
            result_a = importer_a._apply_import(
                store_a, self._conc_payload(gid_a, option_name, 'CONC-A'))
            cr_a.commit()
            self.assertTrue(result_a['variant_bindings'])

            # Exactly ONE global attribute; both products bound, no dupes.
            self.assertEqual(
                env_a['product.attribute'].with_context(active_test=False)
                .search_count([('name', '=', option_name)]), 1)
            TB = env_a['shopify.connector.product.template.binding']
            self.assertEqual(TB.search_count([('shopify_gid', '=', gid_a)]), 1)
            self.assertEqual(TB.search_count([('shopify_gid', '=', gid_b)]), 1)
        finally:
            cr_a.close()
            cr_b.close()
            self._cleanup_concurrency(
                db, [gid_a, gid_b], [store_a_id, store_b_id], option_name)

    def test_sequential_reresolve_is_idempotent(self):
        """A second resolve of the same new option name (same transaction)
        reuses the first attribute -- the get-or-create is idempotent."""
        first = self.Importer._resolve_or_create_attribute('Material', 'manual_review')
        second = self.Importer._resolve_or_create_attribute('material', 'manual_review')
        self.assertEqual(first, second)
        self.assertEqual(
            self.Attribute.with_context(active_test=False).search_count(
                [('name', '=ilike', 'material')]
            ), 1,
        )
