# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
"""AUD-020 — order import must never book foreign amounts as company currency.

Fail-before evidence for FINALIZE.md item 2. Policy (Ahmed, 2026-06-11):
auto-activating currencies is allowed, done visibly; never post a financial
document without a usable exchange rate (prefer the rate derivable from the
order's own Shopify money fields, fall back to Odoo rates, else error-state
the order with an actionable message).
"""
from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin
from .common import mute_case_loggers


class TestOrderImportCurrency(ShopifyAccountingMixin, TransactionCase):

    def setUp(self):
        super().setUp()
        mute_case_loggers(self,
                          'odoo.addons.shopify_connector_pro.sync.order_sync')
        self.backend = self.env['shopify.backend'].create({
            'name': 'Currency Test Store',
            'shop_url': 'currency-test.myshopify.com',
            'access_token': 'shpat_currency_test',
            'company_id': self.env.company.id,
            'import_currency_mode': 'presentment',
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.product = self.env['product.product'].create({
            'name': 'Currency Widget',
            'list_price': 50.0,
            'default_code': 'CUR-WIDGET-1',
        })
        # Neutralize the company default sale tax so the currency
        # assertions are exact (the default-tax leak itself is AUD-016,
        # item 3 scope — not under test here).
        self.product.taxes_id = [(5, 0, 0)]
        product_binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/8100',
            'sync_status': 'synced',
        })
        self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/8200',
            'product_binding_id': product_binding.id,
            'sync_status': 'synced',
        })

        # Deterministic starting state: EUR inactive, no EUR rates
        self.eur = self.env['res.currency'].with_context(
            active_test=False,
        ).search([('name', '=', 'EUR')], limit=1)
        self.env['res.currency.rate'].search([
            ('currency_id', '=', self.eur.id),
        ]).unlink()
        if self.eur.active:
            self.eur.active = False

        from ..sync.order_sync import OrderImporter
        self.importer = OrderImporter.__new__(OrderImporter)
        self.importer.env = self.env
        self.importer.backend = self.backend
        self.importer.client = MagicMock()
        self.importer._currency_cache = {}
        self.importer._pricelist_cache = {}
        self.importer._shipping_product = None

    def _make_node(self, order_id, name, presentment_ccy='EUR',
                   presentment_amount='100.0', shop_amount='108.0',
                   unit_presentment='50.0', unit_shop='54.0'):
        """EUR-presentment order on a USD shop: 2 × 50 EUR = 100 EUR
        (108 USD shopMoney) — the rate IS derivable from the money pair."""
        def _set(p_amt, s_amt):
            return {
                'shopMoney': {'amount': s_amt, 'currencyCode': 'USD'},
                'presentmentMoney': {
                    'amount': p_amt, 'currencyCode': presentment_ccy,
                },
            }
        return {
            'id': order_id,
            'name': name,
            'createdAt': '2026-06-01T10:00:00Z',
            'updatedAt': '2026-06-01T10:00:00Z',
            'displayFinancialStatus': 'PENDING',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': '',
            'tags': [],
            'presentmentCurrencyCode': presentment_ccy,
            'totalPriceSet': _set(presentment_amount, shop_amount),
            'customer': {
                'id': 'gid://shopify/Customer/8500',
                'email': 'eur-buyer@example.com',
                'firstName': 'Eur',
                'lastName': 'Buyer',
            },
            'shippingAddress': None,
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/8001',
                        'title': 'Currency Widget',
                        'quantity': 2,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/8200',
                            'sku': 'CUR-WIDGET-1',
                            'product': {'id': 'gid://shopify/Product/8100'},
                        },
                        'originalUnitPriceSet': _set(unit_presentment, unit_shop),
                        'discountAllocations': [],
                        'taxLines': [],
                    }
                }]
            },
            'shippingLines': {'edges': []},
            'refunds': [],
        }

    def _order_for(self, name):
        return self.env['sale.order'].search([
            ('shopify_order_name', '=', name),
        ], limit=1)

    def _binding_for(self, gid):
        return self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', gid),
        ], limit=1)

    def test_inactive_currency_auto_activated_order_in_eur(self):
        """EUR inactive + rate derivable from the order's own money pair:
        the import must activate EUR visibly and book the order in EUR —
        never 100 'EUR' as 100 USD."""
        node = self._make_node('gid://shopify/Order/8001', '#CUR-1001')
        self.importer._import_one(node, None)

        order = self._order_for('#CUR-1001')
        self.assertTrue(order, "Order must be imported")
        self.assertTrue(self.eur.active,
                        "EUR must be auto-activated (visibly)")
        self.assertEqual(
            order.currency_id, self.eur,
            "AUD-020: presentment amounts are EUR; booking them under %s "
            "misstates the books" % order.currency_id.name,
        )
        self.assertAlmostEqual(order.amount_total, 100.0, places=2)
        # Usable exchange rate must exist (derived from the money pair:
        # 100 EUR ↔ 108 USD → ~0.9259 EUR per USD)
        rates = self.env['res.currency.rate'].search([
            ('currency_id', '=', self.eur.id),
            ('company_id', 'in', [self.env.company.id, False]),
        ])
        self.assertTrue(
            rates, "A usable EUR exchange rate must exist after import")
        self.assertAlmostEqual(rates[0].rate, 100.0 / 108.0, places=3)
        # Scoping (verification addition 2): company-scoped and dated to
        # the order, so it cannot leak into another company's conversions
        self.assertEqual(
            rates[0].company_id, self.env.company,
            "Order-pair rate must be company-scoped",
        )
        self.assertEqual(
            str(rates[0].name), '2026-06-01',
            "Order-pair rate must be dated to the order",
        )

    def test_unknown_currency_error_states_order_visibly(self):
        """Unknown currency code: no sale order, error-state binding with an
        actionable message — nothing booked in company currency."""
        node = self._make_node(
            'gid://shopify/Order/8002', '#CUR-1002', presentment_ccy='ZZZ',
        )
        self.importer._import_one(node, None)

        self.assertFalse(
            self._order_for('#CUR-1002'),
            "No sale order may be created with an unresolvable currency",
        )
        binding = self._binding_for('gid://shopify/Order/8002')
        self.assertTrue(binding, "An error binding must record the failure")
        self.assertEqual(binding.sync_status, 'error')
        self.assertFalse(binding.odoo_id)
        self.assertIn('ZZZ', binding.sync_error or '',
                      "Message must name the unresolvable currency")

    def test_company_mode_pair_rate_wins_over_odoo_daily_rate(self):
        """Company mode (CONVERT decision): the order's own money pair
        (shop EUR 100 ↔ presentment USD 108) must win over a differing
        Odoo daily rate (0.92 → would imply 108.70). Exact to currency
        rounding: total is 108.00, Shopify's own conversion."""
        self.backend.import_currency_mode = 'company'
        self.eur.active = True
        self.env['res.currency.rate'].create({
            'currency_id': self.eur.id,
            'rate': 0.92,
            'name': '2026-06-01',
            'company_id': self.env.company.id,
        })
        node = self._make_node('gid://shopify/Order/8004', '#CUR-1004')
        # Shop currency EUR, presentment USD (= company): swap the pair
        node['currencyCode'] = 'EUR'
        for ps in (node['totalPriceSet'],
                   node['lineItems']['edges'][0]['node']['originalUnitPriceSet']):
            shop, pres = ps['shopMoney'], ps['presentmentMoney']
            ps['shopMoney'] = {
                'amount': pres['amount'], 'currencyCode': 'EUR',
            }
            ps['presentmentMoney'] = {
                'amount': shop['amount'], 'currencyCode': 'USD',
            }
        self.importer._import_one(node, None)

        order = self._order_for('#CUR-1004')
        self.assertTrue(order, "Order must be imported")
        self.assertEqual(
            order.currency_id, self.env.company.currency_id,
            "Company mode books in company currency",
        )
        self.assertEqual(
            round(order.amount_total, 2), 108.00,
            "Order-pair conversion (USD presentment side) must win: "
            "108.00, not 108.70 from the 0.92 Odoo daily rate",
        )

    def test_company_mode_converts_via_odoo_rate_when_no_pair(self):
        """Company mode, no money pair (both sides EUR): convert shopMoney
        via the Odoo rate, exact to currency rounding
        (50 / 0.92 = 54.35 per unit → 108.70 total)."""
        self.backend.import_currency_mode = 'company'
        self.eur.active = True
        self.env['res.currency.rate'].create({
            'currency_id': self.eur.id,
            'rate': 0.92,
            'name': '2026-06-01',
            'company_id': self.env.company.id,
        })
        node = self._make_node('gid://shopify/Order/8005', '#CUR-1005')
        node['currencyCode'] = 'EUR'
        for ps in (node['totalPriceSet'],
                   node['lineItems']['edges'][0]['node']['originalUnitPriceSet']):
            ps['shopMoney']['currencyCode'] = 'EUR'
            ps['shopMoney']['amount'] = ps['presentmentMoney']['amount']
            ps['presentmentMoney'] = dict(ps['shopMoney'])
        self.importer._import_one(node, None)

        order = self._order_for('#CUR-1005')
        self.assertTrue(order, "Order must be imported")
        self.assertEqual(order.currency_id, self.env.company.currency_id)
        self.assertEqual(
            round(order.amount_total, 2), 108.70,
            "Odoo-rate conversion: 2 x (50 EUR / 0.92) = 108.70 USD",
        )

    def test_error_then_retry_yields_exactly_one_order(self):
        """Verification addition 1: error-state (no usable rate) → add the
        rate → Retry Sync → exactly ONE sale order, binding linked."""
        self.backend.import_currency_mode = 'shopify'
        node = self._make_node('gid://shopify/Order/8006', '#CUR-1006')
        node['currencyCode'] = 'EUR'
        for ps in (node['totalPriceSet'],
                   node['lineItems']['edges'][0]['node']['originalUnitPriceSet']):
            ps['shopMoney']['currencyCode'] = 'EUR'
            ps['shopMoney']['amount'] = ps['presentmentMoney']['amount']
            ps['presentmentMoney'] = dict(ps['shopMoney'])

        # First import: EUR has no rate and none is derivable → error
        self.importer._import_one(node, None)
        binding = self._binding_for('gid://shopify/Order/8006')
        self.assertEqual(binding.sync_status, 'error')
        self.assertFalse(binding.odoo_id)
        self.assertFalse(self._order_for('#CUR-1006'))

        # Merchant fixes the rate, retries
        self.env['res.currency.rate'].create({
            'currency_id': self.eur.id,
            'rate': 0.92,
            'name': '2026-06-01',
            'company_id': self.env.company.id,
        })
        binding.action_retry_sync()
        self.assertEqual(binding.sync_status, 'pending')
        self.importer._import_one(node, binding)

        orders = self.env['sale.order'].search([
            ('shopify_order_name', '=', '#CUR-1006'),
        ])
        self.assertEqual(
            len(orders), 1,
            "Retry must produce exactly one sale order (no duplicates)",
        )
        self.assertEqual(binding.odoo_id, orders,
                         "Binding must link the created order")
        self.assertEqual(binding.sync_status, 'synced')
        self.assertFalse(binding.sync_error)
        bindings = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/8006'),
        ])
        self.assertEqual(len(bindings), 1,
                         "Retry must not create a second binding")

    def test_no_rate_anywhere_error_states_order_visibly(self):
        """Active-able currency but NO rate derivable (identical money pair
        amounts are fine — here we strip presentment so no pair exists) and
        no Odoo rate: error-state, never company-currency booking."""
        node = self._make_node('gid://shopify/Order/8003', '#CUR-1003')
        # Remove every presentment/shop pair that could yield a rate, keep
        # only EUR shopMoney: shop-currency EUR store, mode 'shopify'.
        self.backend.import_currency_mode = 'shopify'
        node['currencyCode'] = 'EUR'
        for ps in (node['totalPriceSet'],
                   node['lineItems']['edges'][0]['node']['originalUnitPriceSet']):
            ps['shopMoney']['currencyCode'] = 'EUR'
            ps['shopMoney']['amount'] = ps['presentmentMoney']['amount']
            ps['presentmentMoney'] = dict(ps['shopMoney'])

        self.importer._import_one(node, None)

        self.assertFalse(
            self._order_for('#CUR-1003'),
            "No sale order may be created without a usable exchange rate",
        )
        binding = self._binding_for('gid://shopify/Order/8003')
        self.assertTrue(binding, "An error binding must record the failure")
        self.assertEqual(binding.sync_status, 'error')
        self.assertIn('EUR', binding.sync_error or '',
                      "Message must name the currency lacking a rate")
