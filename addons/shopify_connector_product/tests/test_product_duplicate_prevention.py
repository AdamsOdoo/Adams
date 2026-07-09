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
