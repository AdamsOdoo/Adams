"""The SKU duplicate gate must not be defeatable by the SKU itself.

The gate reads an empty result set as "no duplicate exists" and proceeds to
create. So a SKU that re-shapes the search query does not make the gate
fail -- it makes it *open*, which is the one outcome the operating model and
the Task 015 packet both promise can never happen ("never a blind create").

These tests assert on the exact string handed to Shopify, not on a helper's
return value, because the defect lived in the gap between the two.
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.tools.search_syntax import (
    ShopifySearchValueError,
    search_term,
    search_value,
)

from .common import ExportCase, FakeSendResponse

_SKU_GATE_BODY = {'data': {'productVariants': {'nodes': []}}}


@tagged('post_install', '-at_install')
class TestShopifySearchValueEncoding(TransactionCase):
    """The encoder itself, over the charset the grammar calls special."""

    def test_an_ordinary_value_is_quoted(self):
        self.assertEqual(search_value('WIDGET-1'), '"WIDGET-1"')

    def test_whitespace_cannot_split_a_value_into_two_terms(self):
        # Unquoted, `sku:WIDGET 1` is `sku:WIDGET AND 1` -- a different
        # query, which matches nothing, which opens the gate.
        self.assertEqual(search_value('WIDGET 1'), '"WIDGET 1"')

    def test_a_double_quote_is_escaped(self):
        self.assertEqual(search_value('24" monitor'), '"24\\" monitor"')

    def test_a_backslash_is_escaped_before_the_quote_is_added(self):
        self.assertEqual(search_value('A\\B'), '"A\\\\B"')

    def test_a_backslash_before_a_quote_stays_unambiguous(self):
        # Naive ordering would emit `"A\\"` and terminate the value early.
        self.assertEqual(search_value('A\\"B'), '"A\\\\\\"B"')

    def test_a_colon_cannot_introduce_a_second_comparator(self):
        self.assertEqual(search_value('A:B'), '"A:B"')

    def test_parentheses_cannot_open_a_subquery(self):
        self.assertEqual(search_value('A(B)'), '"A(B)"')

    def test_connectives_are_literal_inside_a_value(self):
        for word in ('AND', 'OR', 'NOT'):
            with self.subTest(word=word):
                self.assertEqual(
                    search_value('A %s B' % word), '"A %s B"' % word,
                )

    def test_a_leading_minus_cannot_negate_the_term(self):
        self.assertEqual(search_value('-ABC'), '"-ABC"')

    def test_a_term_places_the_encoded_value_after_the_comparator(self):
        self.assertEqual(search_term('sku', 'A B'), 'sku:"A B"')

    # -- fail closed ----------------------------------------------------

    def test_an_empty_value_fails_closed(self):
        for bad in ('', '   '):
            with self.subTest(value=bad):
                with self.assertRaises(ShopifySearchValueError):
                    search_value(bad)

    def test_a_non_string_fails_closed(self):
        for bad in (None, 17, ['a']):
            with self.subTest(value=bad):
                with self.assertRaises(ShopifySearchValueError):
                    search_value(bad)

    def test_a_newline_fails_closed(self):
        # The grammar has no representation for these, so there is no
        # faithful encoding to fall back on.
        for bad in ('A\nB', 'A\rB', 'A\tB', 'A\x00B'):
            with self.subTest(value=bad):
                with self.assertRaises(ShopifySearchValueError):
                    search_value(bad)


@tagged('post_install', '-at_install')
class TestSkuGateQueryConstruction(ExportCase):
    """What the gate actually puts on the wire."""

    def setUp(self):
        super().setUp()
        self.sent = []

    def _capture(self):
        sent = self.sent

        def responder(client_self, store, body, token=None,
                      mutation_context=None):
            sent.append(body)
            return FakeSendResponse(_SKU_GATE_BODY)

        return self.send_patch(responder)

    def _gate(self, skus):
        job = self.make_job('product_export_preview', 'product.template',
                            self.template.id)
        with self._capture():
            self.Service._search_remote_by_sku(self.store, job, skus)
        return self.sent[-1]['variables']['query']

    def test_a_plain_sku_is_quoted_on_the_wire(self):
        self.assertEqual(self._gate(['WIDGET-1']), 'sku:"WIDGET-1"')

    def test_a_sku_with_a_space_cannot_break_the_term(self):
        self.assertEqual(self._gate(['WIDGET 1']), 'sku:"WIDGET 1"')

    def test_a_sku_carrying_a_connective_is_matched_literally(self):
        self.assertEqual(
            self._gate(['RED OR BLUE']), 'sku:"RED OR BLUE"',
        )

    def test_a_sku_carrying_a_quote_is_escaped(self):
        self.assertEqual(self._gate(['24" rack']), 'sku:"24\\" rack"')

    def test_multiple_skus_stay_or_joined_and_each_is_encoded(self):
        self.assertEqual(
            self._gate(['B 2', 'A:1']), 'sku:"A:1" OR sku:"B 2"',
        )

    def test_an_unencodable_sku_fails_before_transport(self):
        with self.assertRaises(ShopifySearchValueError):
            self._gate(['A\nB'])
        self.assertFalse(
            self.sent, 'nothing may reach the transport for a refused value',
        )
