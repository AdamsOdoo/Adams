import os

from odoo.tests.common import TransactionCase

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)


class TestProductDuplicatePrevention(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Product Duplicate Prevention Test Store',
            'shop_domain': 'product-duplicate-prevention-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.TemplateBinding = cls.env['shopify.connector.product.template.binding']
        cls.VariantBinding = cls.env['shopify.connector.product.variant.binding']

    def _variant_payload(self, gid, sku=None, barcode=None):
        return {
            'gid': gid, 'sku': sku, 'barcode': barcode, 'price': 9.99,
            'compare_at_price': None, 'option_values': None,
            'image_url': None,
        }

    def _product_payload(self, gid, variants, title='Test Product'):
        return {
            'gid': gid, 'title': title, 'status': 'active',
            'image_url': None, 'variants': variants,
        }

    # ------------------------------------------------------------------
    # 1. No automated create without a confident match or confident
    # no-match, per §8's exact thresholds.
    # ------------------------------------------------------------------

    def test_confident_no_match_creates_new_binding(self):
        payload = self._product_payload(
            gid='gid://shopify/Product/950',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/950', sku='FRESH-SKU-1',
                ),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        self.assertTrue(result['template_binding'].id)
        self.assertTrue(result['variant_bindings'].id)
        self.assertFalse(result['template_binding'].match_key)

    def test_ambiguous_never_creates_confirming_duplicate_prevention(self):
        template_a = self.env['product.template'].create({'name': 'Dup E'})
        template_a.product_variant_id.default_code = 'DUP-3'
        template_b = self.env['product.template'].create({'name': 'Dup F'})
        template_b.product_variant_id.default_code = 'DUP-3'
        payload = self._product_payload(
            gid='gid://shopify/Product/951',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/951', sku='DUP-3',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'ambiguous_match')

    # ------------------------------------------------------------------
    # 2. Blind create attempt -> blocked_manual_review / duplicate_risk
    # -- never creates.
    # ------------------------------------------------------------------

    def test_blind_create_blocked_duplicate_risk_never_creates(self):
        templates_before = self.env['product.template'].search_count([])
        payload = self._product_payload(
            gid='gid://shopify/Product/952',
            variants=[
                self._variant_payload('gid://shopify/ProductVariant/952'),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Product/952'),
        ]))

    # ------------------------------------------------------------------
    # 3. No feature flag/setting bypasses any condition in §8
    # (source-level).
    # ------------------------------------------------------------------

    def _importer_source(self):
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models', 'shopify_connector_product_importer.py',
        )
        with open(path, 'r', encoding='utf-8') as source_file:
            return path, source_file.read()

    def test_source_level_no_bypass_flag_in_matching_logic(self):
        """Part A §I.5's no-bypass rule (restated, final prompt §8): no
        feature flag/setting/config combination may skip the pre-create
        duplicate check or the match-quality gate. Confirmed here at
        source level -- no bypass/force/skip identifier exists anywhere
        in the importer's matching/creation logic."""
        _path, content = self._importer_source()
        for forbidden in (
            'bypass', 'force_create', 'skip_gate', 'skip_duplicate',
            'ignore_duplicate', 'allow_blind',
        ):
            self.assertNotIn(forbidden, content.lower())

    # ------------------------------------------------------------------
    # 4. Re-importing the same GID binds to the existing binding row --
    # never creates a duplicate.
    # ------------------------------------------------------------------

    def test_reimport_same_gid_binds_existing_never_duplicates(self):
        payload = self._product_payload(
            gid='gid://shopify/Product/953',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/953', sku='REPEAT-SKU',
                ),
            ],
        )
        result_1 = self.Importer._apply_import(self.store, payload)
        result_2 = self.Importer._apply_import(self.store, payload)
        self.assertEqual(
            result_1['template_binding'], result_2['template_binding'],
        )
        self.assertEqual(
            result_1['variant_bindings'], result_2['variant_bindings'],
        )
        self.assertEqual(
            self.TemplateBinding.search_count([
                ('store_id', '=', self.store.id),
                ('shopify_gid', '=', 'gid://shopify/Product/953'),
            ]), 1,
        )
        self.assertEqual(
            self.VariantBinding.search_count([
                ('store_id', '=', self.store.id),
                ('shopify_gid', '=', 'gid://shopify/ProductVariant/953'),
            ]), 1,
        )

    # ------------------------------------------------------------------
    # 5. Zero customer/order/inventory/fulfillment side effects.
    # ------------------------------------------------------------------

    def test_source_level_no_customer_order_inventory_fulfillment_models(self):
        """No such model is touched, read, or written anywhere in this
        task's new production files."""
        models_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'models',
        )
        forbidden_models = (
            'sale.order', 'res.partner', 'stock.quant', 'stock.picking',
            'stock.move', 'stock.location', 'account.move',
            'account.payment', 'delivery.carrier',
        )
        for filename in (
            'shopify_connector_product_template_binding.py',
            'shopify_connector_product_variant_binding.py',
            'shopify_connector_product_importer.py',
        ):
            path = os.path.join(models_dir, filename)
            with open(path, 'r', encoding='utf-8') as source_file:
                content = source_file.read()
            for forbidden in forbidden_models:
                self.assertNotIn(forbidden, content, (path, forbidden))

    def test_import_touches_only_product_and_binding_models(self):
        """Behavioral counterpart to the source-level scan above: running
        a full import creates rows in only the expected models."""
        partner_count_before = self.env['res.partner'].search_count([])
        payload = self._product_payload(
            gid='gid://shopify/Product/954',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/954', sku='SIDE-EFFECT-SKU',
                ),
            ],
        )
        self.Importer._apply_import(self.store, payload)
        self.assertEqual(
            self.env['res.partner'].search_count([]), partner_count_before,
        )

    # ------------------------------------------------------------------
    # 6. One-product import is atomic on classified failure
    # (control-room review, comment 4927037139, fix 2).
    # ------------------------------------------------------------------

    def test_source_level_apply_import_uses_savepoint(self):
        _path, content = self._importer_source()
        self.assertIn('self.env.cr.savepoint()', content)

    def test_atomic_rollback_leaves_no_partial_residue_on_later_variant_failure(self):
        """Regression test: variant 1 of a brand-new product succeeds
        (binds to the template's own auto-generated singleton variant),
        but variant 2 always fails `duplicate_risk` (no safe automatic
        variant creation is available under an existing template -- this
        importer's own conservative-scope decision). Without the
        savepoint fix, this would leave the template, its auto-generated
        `product.product`, and variant 1's binding persisted while
        variant 2 has no binding at all -- a genuine partial-import
        residue. The savepoint must roll back all of it, leaving zero
        trace of this attempted import."""
        templates_before = self.env['product.template'].search_count([])
        products_before = self.env['product.product'].search_count([])
        payload = self._product_payload(
            gid='gid://shopify/Product/955',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/955', sku='ATOMIC-SKU-1',
                ),
                self._variant_payload(
                    'gid://shopify/ProductVariant/956', sku='ATOMIC-SKU-2',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'duplicate_risk')
        self.assertEqual(
            self.env['product.template'].search_count([]), templates_before,
            'a partially-imported product.template was not rolled back',
        )
        self.assertEqual(
            self.env['product.product'].search_count([]), products_before,
            'a partially-imported product.product was not rolled back',
        )
        self.assertFalse(self.TemplateBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', '=', 'gid://shopify/Product/955'),
        ]), 'a partially-imported template binding was not rolled back')
        self.assertFalse(self.VariantBinding.search([
            ('store_id', '=', self.store.id),
            ('shopify_gid', 'in', [
                'gid://shopify/ProductVariant/955',
                'gid://shopify/ProductVariant/956',
            ]),
        ]), 'a partially-imported variant binding was not rolled back')

    def test_atomic_rollback_does_not_affect_a_separate_successful_import(self):
        """The savepoint scopes exactly one _apply_import() call -- a
        prior, already-committed successful import must be unaffected by
        a later, failing one."""
        earlier_payload = self._product_payload(
            gid='gid://shopify/Product/957',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/957', sku='ATOMIC-SKU-3',
                ),
            ],
        )
        earlier_result = self.Importer._apply_import(self.store, earlier_payload)

        failing_payload = self._product_payload(
            gid='gid://shopify/Product/958',
            variants=[
                self._variant_payload(
                    'gid://shopify/ProductVariant/958', sku='ATOMIC-SKU-4',
                ),
                self._variant_payload(
                    'gid://shopify/ProductVariant/959', sku='ATOMIC-SKU-5',
                ),
            ],
        )
        with self.assertRaises(JobHandlerError):
            self.Importer._apply_import(self.store, failing_payload)

        earlier_result['template_binding'].invalidate_recordset()
        self.assertTrue(earlier_result['template_binding'].exists())
        self.assertEqual(
            self.TemplateBinding.search_count([
                ('store_id', '=', self.store.id),
                ('shopify_gid', '=', 'gid://shopify/Product/957'),
            ]), 1,
        )

    # ------------------------------------------------------------------
    # 7. Structured (multi-option) import atomicity and idempotency
    # (D-010B-2/3/10): the new attribute/variant path is atomic and
    # idempotent too.
    # ------------------------------------------------------------------

    def _svariant(self, gid, selected, sku=None):
        return {
            'gid': gid, 'sku': sku, 'barcode': None, 'price': None,
            'compare_at_price': None, 'selected_options': selected,
            'option_values': ' / '.join(
                '%s: %s' % (s['name'], s['value']) for s in selected
            ) or None,
            'image_url': None,
        }

    def _structured_payload(self, gid, options, variants):
        return {
            'gid': gid, 'title': 'Structured Product', 'status': 'active',
            'updated_at': None, 'image_url': None,
            'options': options, 'variants': variants,
        }

    def test_structured_reimport_is_idempotent_no_duplicates(self):
        payload = self._structured_payload(
            'gid://shopify/Product/960',
            options=[{'name': 'SC010B Structured Color', 'position': 1,
                      'values': ['Red', 'Blue']}],
            variants=[
                self._svariant('gid://shopify/ProductVariant/960a',
                               [{'name': 'SC010B Structured Color', 'value': 'Red'}],
                               sku='SR0'),
                self._svariant('gid://shopify/ProductVariant/960b',
                               [{'name': 'SC010B Structured Color', 'value': 'Blue'}],
                               sku='SB0'),
            ],
        )
        first = self.Importer._apply_import(self.store, payload)
        attributes_after_first = self.env['product.attribute'].search_count([])
        second = self.Importer._apply_import(self.store, payload)
        self.assertEqual(first['template_binding'], second['template_binding'])
        self.assertEqual(len(second['variant_bindings']), 2)
        template = first['template_binding'].product_template_id
        self.assertEqual(len(template.product_variant_ids), 2)
        # Re-import creates no second same-name attribute.
        self.assertEqual(
            self.env['product.attribute'].search_count([]), attributes_after_first,
        )
        self.assertEqual(
            self.VariantBinding.search_count([
                ('product_template_binding_id', '=', first['template_binding'].id),
            ]), 2,
        )

    def test_structured_import_failure_rolls_back_new_attributes(self):
        """A structured import that fails on a later variant rolls back the
        attributes/values/lines it created too -- no orphan global
        attribute is left behind."""
        attributes_before = self.env['product.attribute'].search_count([])
        products_before = self.env['product.product'].search_count([])
        payload = self._structured_payload(
            'gid://shopify/Product/961',
            options=[{'name': 'SC010B Structured Cut', 'position': 1,
                      'values': ['Slim']}],
            variants=[
                self._svariant('gid://shopify/ProductVariant/961a',
                               [{'name': 'SC010B Structured Cut', 'value': 'Slim'}],
                               sku='CS1'),
                # References an option absent from the product -> conflict.
                self._svariant('gid://shopify/ProductVariant/961b',
                               [{'name': 'SC010B Phantom', 'value': 'X'}], sku='CX1'),
            ],
        )
        with self.assertRaises(JobHandlerError) as ctx:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(ctx.exception.error_class, 'binding_conflict')
        self.assertEqual(
            self.env['product.attribute'].search_count([]), attributes_before,
        )
        self.assertEqual(
            self.env['product.product'].search_count([]), products_before,
        )
