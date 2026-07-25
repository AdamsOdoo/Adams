from odoo.tests.common import TransactionCase, tagged
from odoo.tools import float_compare


# Issue #193 / #157 -- Odoo 19 test-phase contract. This class's fixtures insert
# rows into Odoo business tables (res.users/res.partner/product.template/...) whose
# NOT NULL columns are contributed by modules OUTSIDE this module's dependency
# closure (e.g. account.autopost_bills, stock.tracking, mail.notification_type).
# During a warm `-u` run those columns already exist in PostgreSQL, but at at_install
# time the contributing module is not yet in the registry, so the ORM omits them from
# the INSERT and PostgreSQL raises NOT NULL. post_install runs after every module is
# loaded, which is the only phase where the field exists on the model.
# See docs/05-qa/odoo19-test-phase-contract.md. Test-only; no production behaviour.
@tagged('post_install', '-at_install')
class TestProductPriceImport(TransactionCase):
    """D-010B-4: base price import gated by price_source_of_truth, with
    exact additive price_extra decomposition and a safe fallback."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Price Import Test Store',
            'shop_domain': 'price-import-test.myshopify.com',
            'api_version': '2026-07',
        })
        cls.Importer = cls.env['shopify.connector.product.importer']
        cls.Settings = cls.env['shopify.connector.store.settings']

    def _settings(self, source_of_truth=None):
        return self.Settings.create({
            'store_id': self.store.id,
            'price_source_of_truth': source_of_truth,
        })

    def _variant(self, gid, price, selected=None, sku=None, compare_at=None):
        selected = selected or []
        return {
            'gid': gid, 'sku': sku, 'barcode': None, 'price': price,
            'compare_at_price': compare_at,
            'selected_options': selected,
            'option_values': ' / '.join(
                '%s: %s' % (s['name'], s['value']) for s in selected
            ) or None,
            'image_url': None,
        }

    def _payload(self, gid, variants, options=None):
        return {
            'gid': gid, 'title': 'Priced Product', 'status': 'active',
            'updated_at': None, 'image_url': None,
            'options': options or [], 'variants': variants,
        }

    def _ptav_extra(self, template, value_name):
        ptav = template.attribute_line_ids.product_template_value_ids.filtered(
            lambda p: p.product_attribute_value_id.name == value_name
        )
        return ptav.price_extra

    # ------------------------------------------------------------------
    # Source-of-truth gating.
    # ------------------------------------------------------------------

    def test_shopify_authoritative_writes_single_variant_list_price(self):
        self._settings('shopify_authoritative')
        payload = self._payload(
            'gid://shopify/Product/4001',
            variants=[self._variant('gid://shopify/ProductVariant/4001', 24.99,
                                    sku='PR-1')],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertEqual(
            float_compare(template.list_price, 24.99, precision_digits=2), 0,
        )

    def test_odoo_authoritative_does_not_write_price(self):
        self._settings('odoo_authoritative')
        payload = self._payload(
            'gid://shopify/Product/4002',
            variants=[self._variant('gid://shopify/ProductVariant/4002', 24.99,
                                    sku='PR-2')],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertNotEqual(
            float_compare(template.list_price, 24.99, precision_digits=2), 0,
        )

    def test_unset_source_of_truth_does_not_write_price(self):
        # No settings row at all -> defaults, price not authoritative.
        payload = self._payload(
            'gid://shopify/Product/4003',
            variants=[self._variant('gid://shopify/ProductVariant/4003', 24.99,
                                    sku='PR-3')],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertNotEqual(
            float_compare(template.list_price, 24.99, precision_digits=2), 0,
        )

    # ------------------------------------------------------------------
    # Multi-variant minimum + exact price_extra decomposition.
    # ------------------------------------------------------------------

    def _size_payload(self, gid, s_price, m_price):
        return self._payload(
            gid,
            options=[{'name': 'SC010B Price Size', 'position': 1, 'values': ['S', 'M']}],
            variants=[
                self._variant('%s/s' % gid, s_price,
                              [{'name': 'SC010B Price Size', 'value': 'S'}],
                              sku='%s-S' % gid[-4:]),
                self._variant('%s/m' % gid, m_price,
                              [{'name': 'SC010B Price Size', 'value': 'M'}],
                              sku='%s-M' % gid[-4:]),
            ],
        )

    def test_multi_variant_list_price_is_minimum(self):
        self._settings('shopify_authoritative')
        result = self.Importer._apply_import(
            self.store, self._size_payload('gid://shopify/Product/4004', 20.0, 30.0),
        )
        template = result['template_binding'].product_template_id
        self.assertEqual(
            float_compare(template.list_price, 20.0, precision_digits=2), 0,
        )

    def test_exact_price_extra_decomposition_single_option(self):
        self._settings('shopify_authoritative')
        result = self.Importer._apply_import(
            self.store, self._size_payload('gid://shopify/Product/4005', 20.0, 25.0),
        )
        template = result['template_binding'].product_template_id
        self.assertEqual(
            float_compare(template.list_price, 20.0, precision_digits=2), 0,
        )
        self.assertEqual(
            float_compare(self._ptav_extra(template, 'S'), 0.0, precision_digits=2), 0,
        )
        self.assertEqual(
            float_compare(self._ptav_extra(template, 'M'), 5.0, precision_digits=2), 0,
        )

    def test_exact_price_extra_decomposition_two_options(self):
        self._settings('shopify_authoritative')
        gid = 'gid://shopify/Product/4006'
        payload = self._payload(
            gid,
            options=[
                {'name': 'SC010B Price Color', 'position': 1, 'values': ['Red', 'Blue']},
                {'name': 'SC010B Price Size', 'position': 2, 'values': ['S', 'M']},
            ],
            variants=[
                self._variant('%s/rs' % gid, 20.0, [
                    {'name': 'SC010B Price Color', 'value': 'Red'},
                    {'name': 'SC010B Price Size', 'value': 'S'}], sku='RS6'),
                self._variant('%s/rm' % gid, 25.0, [
                    {'name': 'SC010B Price Color', 'value': 'Red'},
                    {'name': 'SC010B Price Size', 'value': 'M'}], sku='RM6'),
                self._variant('%s/bs' % gid, 23.0, [
                    {'name': 'SC010B Price Color', 'value': 'Blue'},
                    {'name': 'SC010B Price Size', 'value': 'S'}], sku='BS6'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        self.assertEqual(
            float_compare(template.list_price, 20.0, precision_digits=2), 0,
        )
        self.assertEqual(
            float_compare(self._ptav_extra(template, 'M'), 5.0, precision_digits=2), 0,
        )
        self.assertEqual(
            float_compare(self._ptav_extra(template, 'Blue'), 3.0, precision_digits=2), 0,
        )
        self.assertFalse(any(
            code == 'price_undecomposable' for code, _ in result['notes']
        ))

    def test_undecomposable_price_falls_back_with_note(self):
        self._settings('shopify_authoritative')
        gid = 'gid://shopify/Product/4007'
        # Full 2x2 cartesian where the additive model cannot fit: (Blue,M)
        # is 40, not the additive-implied 28.
        payload = self._payload(
            gid,
            options=[
                {'name': 'SC010B Price Color', 'position': 1, 'values': ['Red', 'Blue']},
                {'name': 'SC010B Price Size', 'position': 2, 'values': ['S', 'M']},
            ],
            variants=[
                self._variant('%s/rs' % gid, 20.0, [
                    {'name': 'SC010B Price Color', 'value': 'Red'},
                    {'name': 'SC010B Price Size', 'value': 'S'}], sku='URS'),
                self._variant('%s/rm' % gid, 25.0, [
                    {'name': 'SC010B Price Color', 'value': 'Red'},
                    {'name': 'SC010B Price Size', 'value': 'M'}], sku='URM'),
                self._variant('%s/bs' % gid, 23.0, [
                    {'name': 'SC010B Price Color', 'value': 'Blue'},
                    {'name': 'SC010B Price Size', 'value': 'S'}], sku='UBS'),
                self._variant('%s/bm' % gid, 40.0, [
                    {'name': 'SC010B Price Color', 'value': 'Blue'},
                    {'name': 'SC010B Price Size', 'value': 'M'}], sku='UBM'),
            ],
        )
        result = self.Importer._apply_import(self.store, payload)
        template = result['template_binding'].product_template_id
        # Template still gets the minimum; no invented price_extra.
        self.assertEqual(
            float_compare(template.list_price, 20.0, precision_digits=2), 0,
        )
        self.assertEqual(
            float_compare(self._ptav_extra(template, 'M'), 0.0, precision_digits=2), 0,
        )
        self.assertTrue(any(
            code == 'price_undecomposable' for code, _ in result['notes']
        ))

    def test_decimal_precision_decomposition(self):
        """Sub-cent-safe: decomposition uses float_compare at Product-Price
        precision, never binary-float equality."""
        self._settings('shopify_authoritative')
        result = self.Importer._apply_import(
            self.store,
            self._size_payload('gid://shopify/Product/4008', 10.10, 10.30),
        )
        template = result['template_binding'].product_template_id
        self.assertEqual(
            float_compare(self._ptav_extra(template, 'M'), 0.20, precision_digits=2), 0,
        )
        self.assertFalse(any(
            code == 'price_undecomposable' for code, _ in result['notes']
        ))

    def test_snapshots_retain_prices_regardless_of_source_of_truth(self):
        """Even when Odoo is authoritative, the binding snapshots keep the
        exact Shopify prices (audit fidelity)."""
        self._settings('odoo_authoritative')
        result = self.Importer._apply_import(
            self.store,
            self._payload(
                'gid://shopify/Product/4009',
                variants=[self._variant('gid://shopify/ProductVariant/4009', 24.99,
                                        sku='SNAP-1', compare_at=29.99)],
            ),
        )
        binding = result['variant_bindings']
        self.assertEqual(
            float_compare(binding.shopify_price_snapshot, 24.99, precision_digits=2), 0,
        )
        self.assertEqual(
            float_compare(binding.shopify_compare_at_price_snapshot, 29.99,
                          precision_digits=2), 0,
        )
