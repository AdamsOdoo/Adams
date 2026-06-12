# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


class TestTaxFallbackFlavor(ShopifyAccountingMixin, TransactionCase):
    """AUD-017 (item 3d): the rate fallback must only ever match PERCENT
    taxes — a fixed-amount tax of 10.0 currency units must not satisfy a
    10% rate lookup. And per the AUD-016 remainder, a dropped tax line
    must degrade VISIBLY (warning activity on the order), never
    server-log-only."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Tax Flavor Store',
            'shop_url': 'taxflavor-test.myshopify.com',
            'access_token': 'shpat_taxflavor_test',
            'company_id': self.env.company.id,
            'auto_create_invoice': True,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self._mock_backend_api_client(self.backend)
        self.product = self.env['product.product'].create({
            'name': 'Flavor Widget',
            'list_price': 50.0,
            'default_code': 'FLAVOR-WIDGET-1',
        })
        self._set_product_income_account(self.product)
        pb = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/8100',
            'sync_status': 'synced',
        })
        self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/8200',
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

    def _make_tax(self, name, amount, amount_type='percent', sequence=10):
        # price_include_override pinned tax-excluded so assertions hold
        # identically on the tax-included profile (adams_strict_vat) —
        # inclusive-pricing import semantics are item 3e's surface.
        return self.env['account.tax'].create({
            'name': name,
            'type_tax_use': 'sale',
            'amount_type': amount_type,
            'amount': amount,
            'sequence': sequence,
            'company_id': self.env.company.id,
            'price_include_override': 'tax_excluded',
        })

    def _node(self, order_id, name, tax_lines, total='110.00',
              shipping_lines=None, extra_line_items=None):
        money = lambda amt: {  # noqa: E731
            'shopMoney': {'amount': amt, 'currencyCode': 'USD'},
        }
        line_items = [{'node': {
            'id': 'gid://shopify/LineItem/8001',
            'title': 'Flavor Widget',
            'quantity': 2,
            'variant': {
                'id': 'gid://shopify/ProductVariant/8200',
                'sku': 'FLAVOR-WIDGET-1',
                'product': {'id': 'gid://shopify/Product/8100'},
            },
            'originalUnitPriceSet': money('50.0'),
            'discountAllocations': [],
            'taxLines': tax_lines,
        }}]
        if extra_line_items:
            line_items.extend(extra_line_items)
        return {
            'id': order_id,
            'name': name,
            'createdAt': '2026-06-11T10:00:00Z',
            'updatedAt': '2026-06-11T10:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': '',
            'tags': [],
            'totalPriceSet': money(total),
            'customer': {
                'id': 'gid://shopify/Customer/8500',
                'email': 'flavor-buyer@example.com',
                'firstName': 'Flavor', 'lastName': 'Buyer',
            },
            'shippingAddress': None,
            'billingAddress': None,
            'lineItems': {'edges': line_items},
            'shippingLines': {'edges': shipping_lines or []},
            'refunds': [],
        }

    def _order(self, name):
        return self.env['sale.order'].search(
            [('shopify_order_name', '=', name)], limit=1)

    def _dropped_tax_activities(self, order):
        return self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', order.id),
            ('summary', 'ilike', 'tax'),
        ]).filtered(lambda a: 'total mismatch' not in (a.summary or '').lower())

    # ── AUD-017: amount_type filter ────────────────────────────────────

    def test_fixed_amount_tax_never_matches_rate_lookup(self):
        """A fixed-amount sale tax of 10.0 must NOT be applied for a
        Shopify 10% rate lookup. With no percent match the line drops
        the tax — visibly — and carries no tax at all."""
        fixed_tax = self._make_tax('Fixed Fee 10', 10.0, amount_type='fixed')

        node = self._node('gid://shopify/Order/8001', '#TF-1001', [{
            'title': 'VAT', 'rate': 0.1,
            'priceSet': {'shopMoney': {
                'amount': '10.00', 'currencyCode': 'USD'}},
        }])
        self.importer._import_one(node)

        order = self._order('#TF-1001')
        self.assertTrue(order, "Order must be imported")
        line = order.order_line[0]
        self.assertNotIn(
            fixed_tax, line.tax_ids,
            "AUD-017: a fixed-amount tax must never satisfy a percent "
            "rate lookup",
        )
        self.assertFalse(
            line.tax_ids,
            "With no percent match the Shopify tax line must be dropped, "
            "not substituted (got %s)" % line.tax_ids.mapped('name'),
        )
        self.assertTrue(
            self._dropped_tax_activities(order),
            "Dropping the tax line must be merchant-visible",
        )

    def test_percent_tax_preferred_over_fixed_same_amount(self):
        """When a fixed 10.0 tax sorts BEFORE a percent 10% tax, the
        fallback must still pick the percent tax, and the invoice must
        post with the exact Shopify totals."""
        self._make_tax('Fixed Fee 10', 10.0, amount_type='fixed', sequence=1)
        percent_tax = self._make_tax('VAT 10%', 10.0, sequence=99)

        node = self._node('gid://shopify/Order/8002', '#TF-1002', [{
            'title': 'VAT', 'rate': 0.1,
            'priceSet': {'shopMoney': {
                'amount': '10.00', 'currencyCode': 'USD'}},
        }])
        self.importer._import_one(node)

        order = self._order('#TF-1002')
        self.assertTrue(order, "Order must be imported")
        self.assertEqual(
            order.order_line[0].tax_ids, percent_tax,
            "Rate fallback must resolve the PERCENT tax even when a "
            "same-amount fixed tax sorts first",
        )
        posted = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted')
        self.assertTrue(posted, "Correctly-taxed invoice must post")
        self.assertAlmostEqual(posted[0].amount_total, 110.0, places=2)
        self.assertAlmostEqual(posted[0].amount_tax, 10.0, places=2)

    def test_same_rate_percent_taxes_resolve_deterministically(self):
        """Contract: with several percent taxes at the same rate, the
        fallback picks the first by account.tax ordering (sequence, id —
        odoo/addons/account/models/account_tax.py:75). Merchants steer
        the choice with the tax sequence or an explicit mapping."""
        later = self._make_tax('VAT 10% B', 10.0, sequence=20)
        first = self._make_tax('VAT 10% A', 10.0, sequence=5)
        self.assertGreater(later.id, 0)

        node = self._node('gid://shopify/Order/8003', '#TF-1003', [{
            'title': 'VAT', 'rate': 0.1,
            'priceSet': {'shopMoney': {
                'amount': '10.00', 'currencyCode': 'USD'}},
        }])
        self.importer._import_one(node)

        order = self._order('#TF-1003')
        self.assertEqual(
            order.order_line[0].tax_ids, first,
            "Same-rate ties must resolve by (sequence, id) — lowest first",
        )

    # ── AUD-016 remainder: dropped tax lines degrade visibly ──────────

    def test_dropped_tax_line_schedules_actionable_activity(self):
        """A tax line that matches nothing must schedule a warning
        activity on the order naming the tax title and rate with an
        actionable instruction — not just a server-log line."""
        node = self._node('gid://shopify/Order/8004', '#TF-1004', [{
            'title': 'Bavaria Beverage Tax', 'rate': 0.0777,
            'priceSet': {'shopMoney': {
                'amount': '7.77', 'currencyCode': 'USD'}},
        }], total='107.77')
        self.importer._import_one(node)

        order = self._order('#TF-1004')
        self.assertTrue(order, "Order must be imported")
        activities = self._dropped_tax_activities(order)
        self.assertTrue(
            activities,
            "AUD-016: dropping a Shopify tax line must be visible to the "
            "merchant as an activity on the order",
        )
        note = activities[0].note or ''
        self.assertIn('Bavaria Beverage Tax', note,
                      "Activity must name the unmapped tax")
        self.assertIn('7.77', note, "Activity must name the rate")
        self.assertIn('mapping', note.lower(),
                      "Activity must tell the merchant what to do")

    def test_multiple_dropped_lines_one_deduplicated_activity(self):
        """Several lines (product and shipping) dropping the same and
        different unmappable taxes must produce exactly ONE activity per
        order, naming each distinct tax once."""
        money = lambda amt: {  # noqa: E731
            'shopMoney': {'amount': amt, 'currencyCode': 'USD'},
        }
        mystery = [{
            'title': 'Mystery Levy', 'rate': 0.0333,
            'priceSet': money('3.33'),
        }]
        extra = [{'node': {
            'id': 'gid://shopify/LineItem/8002',
            'title': 'Flavor Widget',
            'quantity': 1,
            'variant': {
                'id': 'gid://shopify/ProductVariant/8200',
                'sku': 'FLAVOR-WIDGET-1',
                'product': {'id': 'gid://shopify/Product/8100'},
            },
            'originalUnitPriceSet': money('50.0'),
            'discountAllocations': [],
            'taxLines': mystery,
        }}]
        shipping = [{'node': {
            'title': 'Standard Shipping',
            'code': 'standard',
            'originalPriceSet': money('10.00'),
            'taxLines': [{
                'title': 'Shipping Levy', 'rate': 0.05,
                'priceSet': money('0.50'),
            }],
        }}]
        node = self._node(
            'gid://shopify/Order/8005', '#TF-1005', mystery,
            total='168.83', shipping_lines=shipping,
            extra_line_items=extra,
        )
        self.importer._import_one(node)

        order = self._order('#TF-1005')
        self.assertTrue(order, "Order must be imported")
        activities = self._dropped_tax_activities(order)
        self.assertEqual(
            len(activities), 1,
            "Dropped taxes must aggregate into ONE activity per order, "
            "got %s" % activities.mapped('summary'),
        )
        note = activities[0].note or ''
        self.assertEqual(
            note.count('Mystery Levy'), 1,
            "Identical dropped taxes on several lines must be named once",
        )
        self.assertIn('Shipping Levy', note,
                      "Shipping tax drops must be reported too")
