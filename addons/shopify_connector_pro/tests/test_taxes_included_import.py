# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


class TestTaxesIncludedImport(ShopifyAccountingMixin, TransactionCase):
    """AUD-018 / AUD-001 (item 3e): honor Shopify ``Order.taxesIncluded``.

    Store semantics × resolved-tax flavor matrix: when the resolved
    taxes' effective price inclusion does not match what Shopify says
    about the order's prices, the unit price is converted (percent
    taxes, uniform flavor) so the booked base, tax and total equal what
    the customer was actually charged — on EVERY company configuration.
    Tax flavors are pinned via price_include_override so each test is
    deterministic on both adams_strict1 and adams_strict_vat.
    """

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'TaxesIncluded Store',
            'shop_url': 'taxinc-test.myshopify.com',
            'access_token': 'shpat_taxinc_test',
            'company_id': self.env.company.id,
            'auto_create_invoice': True,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self._mock_backend_api_client(self.backend)
        self.product = self.env['product.product'].create({
            'name': 'Inclusion Widget',
            'list_price': 50.0,
            'default_code': 'INC-WIDGET-1',
        })
        self._set_product_income_account(self.product)
        pb = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/9100',
            'sync_status': 'synced',
        })
        self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/9200',
            'product_binding_id': pb.id,
            'sync_status': 'synced',
        })
        from ..sync.order_sync import OrderImporter
        self.importer = OrderImporter.__new__(OrderImporter)
        self.importer.env = self.env
        self.importer.backend = self.backend
        self.importer.client = MagicMock()
        self.importer._currency_cache = {}
        self.importer._pricelist_cache = {}
        self.importer._shipping_product = None
        self.importer._country_cache = {}
        self.importer._state_cache = {}

    def _make_tax(self, name, flavor, amount=10.0, sequence=10):
        return self.env['account.tax'].create({
            'name': name,
            'type_tax_use': 'sale',
            'amount_type': 'percent',
            'amount': amount,
            'sequence': sequence,
            'company_id': self.env.company.id,
            'price_include_override': flavor,
        })

    def _node(self, order_id, name, unit_price, total, taxes_included,
              tax_amount='10.00'):
        money = lambda amt: {  # noqa: E731
            'shopMoney': {'amount': amt, 'currencyCode': 'USD'},
        }
        node = {
            'id': order_id,
            'name': name,
            'createdAt': '2026-06-12T01:00:00Z',
            'updatedAt': '2026-06-12T01:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': '',
            'tags': [],
            'totalPriceSet': money(total),
            'customer': {
                'id': 'gid://shopify/Customer/9500',
                'email': 'inclusion-buyer@example.com',
                'firstName': 'Inclusion', 'lastName': 'Buyer',
            },
            'shippingAddress': None,
            'billingAddress': None,
            'lineItems': {'edges': [{'node': {
                'id': 'gid://shopify/LineItem/9001',
                'title': 'Inclusion Widget',
                'quantity': 2,
                'variant': {
                    'id': 'gid://shopify/ProductVariant/9200',
                    'sku': 'INC-WIDGET-1',
                    'product': {'id': 'gid://shopify/Product/9100'},
                },
                'originalUnitPriceSet': money(unit_price),
                'discountAllocations': [],
                'taxLines': [{
                    'title': 'VAT', 'rate': 0.1,
                    'priceSet': money(tax_amount),
                }],
            }}]},
            'shippingLines': {'edges': []},
            'refunds': [],
        }
        if taxes_included is not None:
            node['taxesIncluded'] = taxes_included
        return node

    def _assert_books_match_charge(self, name, expected_taxes):
        """Order imported; invoice POSTED with base 100, tax 10, total
        110 — exactly what the customer was charged."""
        order = self.env['sale.order'].search(
            [('shopify_order_name', '=', name)], limit=1)
        self.assertTrue(order, "Order must be imported")
        line = order.order_line[0]
        self.assertEqual(
            line.tax_ids, expected_taxes,
            "Line must carry the expected tax flavor",
        )
        posted = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted')
        self.assertTrue(
            posted,
            "Invoice must POST — totals must equal the Shopify charge "
            "(draft means the guard caught a mismatch)",
        )
        self.assertAlmostEqual(posted[0].amount_untaxed, 100.0, places=2)
        self.assertAlmostEqual(posted[0].amount_tax, 10.0, places=2)
        self.assertAlmostEqual(posted[0].amount_total, 110.0, places=2)
        return order

    # ── inclusive store (taxesIncluded=true) ──────────────────────────

    def test_inclusive_store_with_included_tax(self):
        """Prices include tax and an included-flavor tax exists: price
        taken as-is, books equal the charge."""
        tax = self._make_tax('VAT 10% incl', 'tax_included')
        self.importer._import_one(self._node(
            'gid://shopify/Order/9001', '#TI-1001',
            unit_price='55.00', total='110.00', taxes_included=True,
        ))
        order = self._assert_books_match_charge('#TI-1001', tax)
        self.assertAlmostEqual(
            order.order_line[0].price_unit, 55.0, places=2,
            msg="Inclusive price + included tax: no conversion",
        )

    def test_inclusive_store_with_only_excluded_tax_aligns_price(self):
        """Prices include tax but only an excluded-flavor 10% tax
        exists: the unit price must be converted to its exclusive
        equivalent so the books still equal the charge."""
        tax = self._make_tax('VAT 10% excl', 'tax_excluded')
        self.importer._import_one(self._node(
            'gid://shopify/Order/9002', '#TI-1002',
            unit_price='55.00', total='110.00', taxes_included=True,
        ))
        order = self._assert_books_match_charge('#TI-1002', tax)
        self.assertAlmostEqual(
            order.order_line[0].price_unit, 50.0, places=2,
            msg="Inclusive price + excluded tax: price converted "
                "(55 / 1.1)",
        )

    # ── exclusive store (taxesIncluded=false) ─────────────────────────

    def test_exclusive_store_with_only_included_tax_aligns_price(self):
        """Prices exclude tax but only an included-flavor 10% tax exists
        (THE AUD-001 scenario — any tax-included company): the unit
        price must be converted to its inclusive equivalent."""
        tax = self._make_tax('VAT 10% incl', 'tax_included')
        self.importer._import_one(self._node(
            'gid://shopify/Order/9003', '#TI-1003',
            unit_price='50.00', total='110.00', taxes_included=False,
        ))
        order = self._assert_books_match_charge('#TI-1003', tax)
        self.assertAlmostEqual(
            order.order_line[0].price_unit, 55.0, places=2,
            msg="Exclusive price + included tax: price converted "
                "(50 × 1.1)",
        )

    def test_flavor_match_preferred_when_both_exist(self):
        """With both flavors available at the same rate, the fallback
        must pick the one matching the store semantics — even when the
        other sorts first — so no price conversion is needed."""
        self._make_tax('VAT 10% excl', 'tax_excluded', sequence=1)
        included = self._make_tax('VAT 10% incl', 'tax_included',
                                  sequence=99)
        self.importer._import_one(self._node(
            'gid://shopify/Order/9004', '#TI-1004',
            unit_price='55.00', total='110.00', taxes_included=True,
        ))
        order = self._assert_books_match_charge('#TI-1004', included)
        self.assertAlmostEqual(
            order.order_line[0].price_unit, 55.0, places=2,
            msg="Flavor match preferred: price untouched",
        )

    # ── backward compatibility ─────────────────────────────────────────

    def test_legacy_payload_without_flag_treated_exclusive(self):
        """Payloads without taxesIncluded (legacy webhook fixtures,
        older captures) must behave exactly as before: exclusive
        semantics (the Shopify default)."""
        tax = self._make_tax('VAT 10% excl', 'tax_excluded')
        self.importer._import_one(self._node(
            'gid://shopify/Order/9005', '#TI-1005',
            unit_price='50.00', total='110.00', taxes_included=None,
        ))
        order = self._assert_books_match_charge('#TI-1005', tax)
        self.assertAlmostEqual(
            order.order_line[0].price_unit, 50.0, places=2,
            msg="No flag: exclusive semantics, price untouched",
        )
