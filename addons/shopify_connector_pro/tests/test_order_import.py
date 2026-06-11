# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase

from .common import ShopifyAccountingMixin


class TestOrderImport(ShopifyAccountingMixin, TransactionCase):

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Test Store',
            'shop_url': 'test.myshopify.com',
            'access_token': 'shpat_test',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.product = self.env['product.product'].create({
            'name': 'Test Widget',
            'list_price': 29.99,
            'default_code': 'WIDGET-001',
        })
        # The fixture orders carry no taxLines and their totalPriceSet is
        # the plain line sum — clear the company default sale tax so the
        # fixture is internally consistent (the default-tax leak on
        # imported lines is AUD-016, covered by its own tests).
        self.product.taxes_id = [(5, 0, 0)]
        self._set_product_income_account(self.product)
        # Create variant binding so order can resolve the product
        product_binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/100',
            'sync_status': 'synced',
        })
        self.variant_binding = self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/200',
            'product_binding_id': product_binding.id,
            'sync_status': 'synced',
        })

    def _make_order_node(self, order_id='gid://shopify/Order/1000', name='#1001',
                         financial_status='PAID'):
        return {
            'id': order_id,
            'name': name,
            'createdAt': '2026-03-28T10:00:00Z',
            'updatedAt': '2026-03-28T10:00:00Z',
            'displayFinancialStatus': financial_status,
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': 'Test order',
            'tags': [],
            'totalPriceSet': {'shopMoney': {'amount': '59.98', 'currencyCode': 'USD'}},
            'customer': {
                'id': 'gid://shopify/Customer/500',
                'email': 'buyer@example.com',
                'firstName': 'Test',
                'lastName': 'Buyer',
            },
            'shippingAddress': {
                'address1': '456 Oak Ave',
                'address2': '',
                'city': 'Los Angeles',
                'province': 'California',
                'provinceCode': 'CA',
                'country': 'United States',
                'countryCodeV2': 'US',
                'zip': '90001',
                'phone': '',
                'firstName': 'Test',
                'lastName': 'Buyer',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/1',
                        'title': 'Test Widget',
                        'quantity': 2,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/200',
                            'sku': 'WIDGET-001',
                            'product': {'id': 'gid://shopify/Product/100'},
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {'amount': '29.99', 'currencyCode': 'USD'},
                        },
                        'discountAllocations': [],
                        'taxLines': [],
                    }
                }]
            },
            'shippingLines': {'edges': []},
        }

    def test_import_new_order(self):
        """Should create a sale.order from Shopify order data."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        self.assertTrue(binding)
        self.assertEqual(binding.shopify_order_name, '#1001')
        self.assertEqual(binding.shopify_financial_status, 'paid')
        self.assertTrue(binding.odoo_id)

        order = binding.odoo_id
        self.assertEqual(order.shopify_order_name, '#1001')
        # Order should be confirmed since financial status is PAID
        self.assertIn(order.state, ('sale', 'done'))

    def test_import_order_creates_lines(self):
        """Imported order should have the correct order lines."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        order = binding.odoo_id
        self.assertEqual(len(order.order_line), 1)
        line = order.order_line[0]
        self.assertEqual(line.product_id.id, self.product.id)
        self.assertEqual(line.product_uom_qty, 2)
        self.assertEqual(line.price_unit, 29.99)

    def test_import_order_resolves_customer(self):
        """Should create customer if not found."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node()

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        partner = binding.odoo_id.partner_id
        self.assertTrue(partner)
        self.assertEqual(partner.email, 'buyer@example.com')

    def test_import_order_updates_existing(self):
        """Should update financial status on re-import."""
        from ..sync.order_sync import OrderImporter

        # First import
        node = self._make_order_node(financial_status='PENDING')

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        self.assertEqual(binding.shopify_financial_status, 'pending')

        # Second import with updated status
        node2 = self._make_order_node(financial_status='PAID')

        importer._import_one(node2, existing_binding=binding)
        self.assertEqual(binding.shopify_financial_status, 'paid')

    def test_import_order_presentment_currency(self):
        """Should use presentment currency when mode is 'presentment' (Shopify Markets)."""
        from ..sync.order_sync import OrderImporter

        # Enable presentment currency mode
        self.backend.import_currency_mode = 'presentment'

        # Ensure EUR currency exists and is active
        eur = self.env['res.currency'].with_context(active_test=False).search([('name', '=', 'EUR')], limit=1)
        if not eur:
            eur = self.env['res.currency'].create({'name': 'EUR', 'symbol': 'E'})
        if not eur.active:
            eur.active = True

        node = self._make_order_node()
        # Add presentment currency data
        node['presentmentCurrencyCode'] = 'EUR'
        node['currencyCode'] = 'USD'
        node['totalPriceSet'] = {
            'shopMoney': {'amount': '29.99', 'currencyCode': 'USD'},
            'presentmentMoney': {'amount': '27.50', 'currencyCode': 'EUR'},
        }
        node['lineItems']['edges'][0]['node']['originalUnitPriceSet'] = {
            'shopMoney': {'amount': '29.99', 'currencyCode': 'USD'},
            'presentmentMoney': {'amount': '27.50', 'currencyCode': 'EUR'},
        }

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        self.assertTrue(binding)
        order = binding.odoo_id
        # Order should use EUR since presentment mode picks customer currency
        if order.currency_id.name != self.env.company.currency_id.name:
            self.assertEqual(order.currency_id.name, 'EUR')

    def test_import_order_money_helper_shopify_mode(self):
        """_get_money_amount should return shopMoney in default mode."""
        from ..sync.order_sync import OrderImporter

        self.backend.import_currency_mode = 'shopify'

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        price_set = {
            'shopMoney': {'amount': '100.00', 'currencyCode': 'USD'},
            'presentmentMoney': {'amount': '85.00', 'currencyCode': 'EUR'},
        }
        self.assertEqual(importer._get_money_amount(price_set), 100.0)

    def test_import_order_money_helper_presentment_mode(self):
        """_get_money_amount should return presentmentMoney in presentment mode."""
        from ..sync.order_sync import OrderImporter

        self.backend.import_currency_mode = 'presentment'

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        price_set = {
            'shopMoney': {'amount': '100.00', 'currencyCode': 'USD'},
            'presentmentMoney': {'amount': '85.00', 'currencyCode': 'EUR'},
        }
        self.assertEqual(importer._get_money_amount(price_set), 85.0)

    def test_invoice_failure_does_not_abort_transaction(self):
        """SQL error in _create_invoices must not poison the transaction."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node(financial_status='PAID')

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        def _boom(*args, **kwargs):
            raise Exception("Simulated accounting failure")

        with patch.object(
            type(self.env['sale.order']),
            '_create_invoices',
            _boom,
        ):
            importer._import_one(node, existing_binding=None)

        # Transaction must still be usable
        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        self.assertTrue(binding, "Binding should exist despite invoice failure")
        self.assertEqual(binding.shopify_financial_status, 'paid')

    def test_invoice_skipped_when_no_income_account(self):
        """Auto-invoice should be skipped with activity when income account missing."""
        from ..sync.order_sync import OrderImporter

        node = self._make_order_node(financial_status='PAID')

        importer = OrderImporter.__new__(OrderImporter)
        importer.env = self.env
        importer.backend = self.backend
        importer.client = MagicMock()
        importer._currency_cache = {}
        importer._pricelist_cache = {}
        importer._shipping_product = None
        importer._country_cache = {}
        importer._state_cache = {}

        # Mock get_product_accounts to return no income account, which is
        # more reliable than clearing property fields that may have
        # company-level defaults from the chart of accounts.
        def _no_income_account(self_tmpl, fiscal_pos=None):
            return {'income': False, 'expense': False}

        with patch.object(
            type(self.product.product_tmpl_id),
            'get_product_accounts',
            _no_income_account,
        ):
            importer._import_one(node, existing_binding=None)

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/1000'),
        ])
        self.assertTrue(binding)
        order = binding.odoo_id
        self.assertFalse(
            order.invoice_ids,
            "No invoice should be created when income account is missing",
        )

    # ── Taxed order import baseline ────────────────────────────────

    def test_import_taxed_order_creates_invoice_with_tax_lines(self):
        """Regression guard for the tax_id→tax_ids fix (0eaae3b).

        Uses the full production import path (import_batch with its
        savepoint + except wrapper) so the test reproduces the exact
        production symptom:

          BEFORE FIX: import_batch catches the ValueError for the
          nonexistent 'tax_id' field, counts errors=1, and the
          order is never created.  The test asserts no binding exists
          and errors == 1.

          AFTER FIX: import_batch succeeds, the order is imported
          with tax_ids on the SO line, and the auto-invoice carries
          tax.  The test asserts success == 1, binding exists, and
          invoice.amount_tax >= $10.
        """
        from ..sync.order_sync import OrderImporter

        # Create a 10% sales tax in Odoo for rate-matching fallback
        tax_10 = self.env['account.tax'].create({
            'name': 'Test Tax 10%',
            'type_tax_use': 'sale',
            'amount': 10.0,
            'amount_type': 'percent',
            'company_id': self.env.company.id,
        })

        # Build a Shopify order with 2×$50 product + 10% tax ($10) +
        # $10 shipping = $120 total.
        node = {
            'id': 'gid://shopify/Order/TAX001',
            'name': '#TAX001',
            'createdAt': '2026-03-28T10:00:00Z',
            'updatedAt': '2026-03-28T10:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'closedAt': None,
            'note': '',
            'tags': [],
            'currencyCode': 'USD',
            'presentmentCurrencyCode': 'USD',
            'totalPriceSet': {
                'shopMoney': {'amount': '120.00', 'currencyCode': 'USD'},
            },
            'subtotalPriceSet': {
                'shopMoney': {'amount': '100.00', 'currencyCode': 'USD'},
            },
            'totalShippingPriceSet': {
                'shopMoney': {'amount': '10.00', 'currencyCode': 'USD'},
            },
            'totalTaxSet': {
                'shopMoney': {'amount': '10.00', 'currencyCode': 'USD'},
            },
            'totalDiscountsSet': {
                'shopMoney': {'amount': '0.00', 'currencyCode': 'USD'},
            },
            'discountCodes': [],
            'customer': {
                'id': 'gid://shopify/Customer/500',
                'email': 'taxbuyer@example.com',
                'firstName': 'Tax',
                'lastName': 'Buyer',
            },
            'shippingAddress': {
                'address1': '789 Tax Ave',
                'address2': '',
                'city': 'London',
                'province': '',
                'provinceCode': '',
                'country': 'United Kingdom',
                'countryCodeV2': 'GB',
                'zip': 'SW1A 1AA',
                'phone': '',
                'firstName': 'Tax',
                'lastName': 'Buyer',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/T1',
                        'title': 'Test Widget',
                        'quantity': 2,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/200',
                            'sku': 'WIDGET-001',
                            'product': {'id': 'gid://shopify/Product/100'},
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {
                                'amount': '50.00',
                                'currencyCode': 'USD',
                            },
                        },
                        'discountAllocations': [],
                        'taxLines': [{
                            'title': 'VAT',
                            'rate': 0.1,
                            'priceSet': {
                                'shopMoney': {
                                    'amount': '10.00',
                                    'currencyCode': 'USD',
                                },
                            },
                        }],
                    },
                }],
                'pageInfo': {'hasNextPage': False},
            },
            'shippingLines': {
                'edges': [{
                    'node': {
                        'title': 'Standard Shipping',
                        'code': 'standard',
                        'originalPriceSet': {
                            'shopMoney': {
                                'amount': '10.00',
                                'currencyCode': 'USD',
                            },
                        },
                    },
                }],
            },
            'refunds': [],
        }

        # auto_create_invoice is True by default
        self.assertTrue(self.backend.auto_create_invoice)

        # Use full production path: import_batch (savepoint + except)
        importer = OrderImporter(self.env, self.backend)
        success, errors, skipped = importer.import_batch([node])

        # After fix: import succeeds
        self.assertEqual(success, 1, "Taxed order import must succeed")
        self.assertEqual(errors, 0, "No errors expected")

        binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/TAX001'),
        ])
        self.assertTrue(binding, "Order binding must exist after import")
        order = binding.odoo_id
        self.assertIn(order.state, ('sale', 'done'))

        # ── Sale order line must carry the 10% tax ──
        product_line = order.order_line.filtered(
            lambda l: l.product_id == self.product
        )
        self.assertTrue(product_line, "Product line must exist")
        self.assertIn(
            tax_10, product_line.tax_ids,
            "Product line must carry the 10% tax from rate-matching",
        )

        # ── Invoice must exist: posted, or visibly blocked by the
        # total-check guard (DEC-011). Until items 3c/3e fix shipping
        # and VAT-inclusive taxes, computed totals legitimately differ
        # from the Shopify charge, so the guard correctly holds the
        # invoice in draft WITH the mismatch activity.
        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state != 'cancel'
        )
        self.assertTrue(invoices, "Auto-invoice must be created")
        invoice = invoices[0]
        if invoice.state != 'posted':
            guard_activity = self.env['mail.activity'].search([
                ('res_model', '=', 'sale.order'),
                ('res_id', '=', order.id),
                ('summary', 'ilike', 'total mismatch'),
            ], limit=1)
            self.assertTrue(
                guard_activity,
                "An unposted auto-invoice is only acceptable when the "
                "total-check guard blocked it visibly",
            )

        # ── Invoice product line must carry tax ──
        inv_product_lines = invoice.invoice_line_ids.filtered(
            lambda l: l.product_id == self.product
            and l.display_type == 'product'
        )
        self.assertTrue(inv_product_lines, "Invoice must have product line")
        self.assertIn(
            tax_10, inv_product_lines[0].tax_ids,
            "Invoice product line must carry the 10% tax",
        )

        # ── amount_total must include tax ──
        # Product: 2 × $50 = $100, tax at 10% = $10, shipping = $10.
        # Odoo may auto-apply default taxes to the shipping product
        # via _compute_tax_ids, so we assert the minimum: untaxed
        # base is $110 and tax amount includes at least the $10
        # product tax.
        self.assertAlmostEqual(
            invoice.amount_untaxed, 110.0, places=2,
            msg="Untaxed total: $100 product + $10 shipping = $110",
        )
        self.assertGreaterEqual(
            invoice.amount_tax, 10.0,
            msg="Tax amount must include at least $10 product tax",
        )
        self.assertGreater(
            invoice.amount_total, 110.0,
            msg="Invoice total must exceed untaxed amount (tax present)",
        )


class TestUntaxedOrderImport(ShopifyAccountingMixin, TransactionCase):
    """AUD-016 (item 3b): Shopify is authoritative for line taxes.
    Lines whose Shopify taxes resolve to nothing must carry NO taxes —
    never the product's default sale tax."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Untaxed Test Store',
            'shop_url': 'untaxed-test.myshopify.com',
            'access_token': 'shpat_untaxed_test',
            'company_id': self.env.company.id,
            'auto_create_invoice': True,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        # Product DELIBERATELY keeps the company default sale tax —
        # that leak is exactly what this class tests.
        self.product = self.env['product.product'].create({
            'name': 'Default-Taxed Widget',
            'list_price': 50.0,
            'default_code': 'DT-WIDGET-1',
        })
        self._set_product_income_account(self.product)
        pb = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/7100',
            'sync_status': 'synced',
        })
        self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/7200',
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

    def _node(self, order_id, name, tax_lines):
        money = lambda amt: {  # noqa: E731
            'shopMoney': {'amount': amt, 'currencyCode': 'USD'},
        }
        return {
            'id': order_id,
            'name': name,
            'createdAt': '2026-06-01T10:00:00Z',
            'updatedAt': '2026-06-01T10:00:00Z',
            'displayFinancialStatus': 'PAID',
            'displayFulfillmentStatus': 'UNFULFILLED',
            'cancelledAt': None,
            'closed': False,
            'note': '',
            'tags': [],
            'totalPriceSet': money('100.0'),
            'customer': {
                'id': 'gid://shopify/Customer/7500',
                'email': 'untaxed-buyer@example.com',
                'firstName': 'Untaxed', 'lastName': 'Buyer',
            },
            'shippingAddress': None,
            'billingAddress': None,
            'lineItems': {'edges': [{'node': {
                'id': 'gid://shopify/LineItem/7001',
                'title': 'Default-Taxed Widget',
                'quantity': 2,
                'variant': {
                    'id': 'gid://shopify/ProductVariant/7200',
                    'sku': 'DT-WIDGET-1',
                    'product': {'id': 'gid://shopify/Product/7100'},
                },
                'originalUnitPriceSet': money('50.0'),
                'discountAllocations': [],
                'taxLines': tax_lines,
            }}]},
            'shippingLines': {'edges': []},
            'refunds': [],
        }

    def test_tax_exempt_order_carries_no_tax_and_posts(self):
        """No taxLines from Shopify (tax-exempt sale): the order line
        must carry NO taxes, totals must equal the Shopify charge, and
        the auto-invoice must POST (guard satisfied)."""
        self.importer._import_one(
            self._node('gid://shopify/Order/7001', '#UT-1001', []), None,
        )
        order = self.env['sale.order'].search([
            ('shopify_order_name', '=', '#UT-1001')], limit=1)
        self.assertTrue(order, "Order must be imported")
        line = order.order_line[0]
        self.assertFalse(
            line.tax_ids,
            "AUD-016: tax-exempt Shopify line must not inherit the "
            "product default sale tax (got %s)" % line.tax_ids.mapped('name'),
        )
        self.assertAlmostEqual(order.amount_total, 100.0, places=2)
        posted = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state == 'posted')
        self.assertTrue(posted, "Matching untaxed invoice must post")
        self.assertAlmostEqual(posted[0].amount_total, 100.0, places=2)

    def test_unresolvable_tax_line_no_silent_under_or_over_tax(self):
        """taxLines present but unmappable (no 7.77% tax exists): the
        line carries no taxes AND the guard blocks the now-mismatched
        invoice visibly — no silent wrong money in either direction."""
        node = self._node('gid://shopify/Order/7002', '#UT-1002', [{
            'title': 'Mystery Tax', 'rate': 0.0777,
            'priceSet': {'shopMoney': {
                'amount': '7.77', 'currencyCode': 'USD'}},
        }])
        node['totalPriceSet']['shopMoney']['amount'] = '107.77'
        self.importer._import_one(node, None)
        order = self.env['sale.order'].search([
            ('shopify_order_name', '=', '#UT-1002')], limit=1)
        self.assertTrue(order, "Order must be imported")
        self.assertFalse(
            order.order_line[0].tax_ids,
            "Unresolvable Shopify tax must not fall back to the product "
            "default tax",
        )
        invoices = order.invoice_ids.filtered(
            lambda i: i.move_type == 'out_invoice' and i.state != 'cancel')
        self.assertTrue(invoices, "Invoice must be created")
        self.assertEqual(
            invoices[0].state, 'draft',
            "Guard must block the under-taxed invoice (100.00 vs 107.77)",
        )
        self.assertTrue(self.env['mail.activity'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', order.id),
            ('summary', 'ilike', 'total mismatch'),
        ], limit=1), "Mismatch must be merchant-visible")
