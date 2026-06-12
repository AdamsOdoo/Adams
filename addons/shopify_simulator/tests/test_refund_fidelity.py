# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Refund response fidelity guard + taxed e2e refund test.

B-6a: Fidelity guard — the simulator refund response must contain
every field the connector's FETCH_REFUNDS query requests.

B-6b: End-to-end — seed a taxed, partially-refunded order in the
simulator, import the refund through the real RefundImporter (no
mocks on the refund data shape), and assert the credit note
matches totalRefundedSet with tax lines present.
"""
import json
from unittest.mock import MagicMock, patch

from odoo.tests.common import TransactionCase


class ShopifyAccountingMixin:
    """Minimal accounting setup for tests that create invoices/credit notes."""

    def _setup_accounting(self):
        company = self.env.company
        # Country + tax group bootstrap for chartless DBs (ENV-1) —
        # mirrors shopify_connector_pro/tests/common.py.
        if not (company.account_fiscal_country_id or company.country_id):
            company.country_id = self.env.ref('base.us')
        if not self.env['account.tax.group'].search(
            [('company_id', '=', company.id)], limit=1,
        ):
            self.env['account.tax.group'].create({
                'name': 'Test Taxes',
                'company_id': company.id,
            })
        if not self.env['account.journal'].search(
            [('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1,
        ):
            self.env['account.journal'].create({
                'name': 'Test Sales Journal', 'type': 'sale',
                'code': 'TRFJ', 'company_id': company.id,
            })
        self.receivable_account = self.env['account.account'].search([
            ('account_type', '=', 'asset_receivable'),
            ('company_ids', 'in', [company.id]),
        ], limit=1)
        if not self.receivable_account:
            self.receivable_account = self.env['account.account'].create({
                'name': 'Test Receivable', 'code': 'TREC',
                'account_type': 'asset_receivable', 'reconcile': True,
                'company_ids': [(6, 0, [company.id])],
            })
        self.payable_account = self.env['account.account'].search([
            ('account_type', '=', 'liability_payable'),
            ('company_ids', 'in', [company.id]),
        ], limit=1)
        if not self.payable_account:
            self.payable_account = self.env['account.account'].create({
                'name': 'Test Payable', 'code': 'TPAY',
                'account_type': 'liability_payable', 'reconcile': True,
                'company_ids': [(6, 0, [company.id])],
            })
        self.income_account = self.env['account.account'].search([
            ('account_type', '=', 'income'),
            ('company_ids', 'in', [company.id]),
        ], limit=1)
        if not self.income_account:
            self.income_account = self.env['account.account'].create({
                'name': 'Test Income Account', 'code': 'TINC',
                'account_type': 'income',
                'company_ids': [(6, 0, [company.id])],
            })
        if not company.transfer_account_id:
            transfer_account = self.env['account.account'].search([
                ('account_type', '=', 'asset_current'),
                ('company_ids', 'in', [company.id]),
            ], limit=1)
            if not transfer_account:
                transfer_account = self.env['account.account'].create({
                    'name': 'Test Transfer Account', 'code': 'TXFR',
                    'account_type': 'asset_current', 'reconcile': True,
                    'company_ids': [(6, 0, [company.id])],
                })
            company.transfer_account_id = transfer_account

    def _set_product_income_account(self, product):
        product.categ_id.property_account_income_categ_id = self.income_account
        product.product_tmpl_id.property_account_income_id = self.income_account


class TestRefundResponseFidelity(TransactionCase):
    """B-6a: Fidelity guard for the simulator refund response shape."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Fidelity Guard Backend',
            'shop_url': 'fidelity.myshopify.com',
            'access_token': 'shpat_fidelity',
            'company_id': self.env.company.id,
        })
        self.sim_config = self.env['sim.shopify.config'].create({
            'backend_id': self.backend.id,
            'shop_name': 'Refund Fidelity Guard',
            'myshopify_domain': 'fidelity.myshopify.com',
        })

    def test_refund_response_contains_all_fetch_refunds_fields(self):
        """The simulator refund node must include every top-level and
        nested field that FETCH_REFUNDS requests.

        If the simulator is missing a field, the connector will get
        None instead of the real Shopify shape — silently breaking
        tax/shipping refund imports.
        """
        sim_order = self.env['sim.shopify.order'].create({
            'config_id': self.sim_config.id,
            'name': '#FID001',
            'financial_status': 'PARTIALLY_REFUNDED',
            'total_price': 120.0,
        })
        sim_refund = self.env['sim.shopify.refund'].create({
            'config_id': self.sim_config.id,
            'order_id': sim_order.id,
            'total_refunded': 125.0,
            'shipping_refund_subtotal': 15.0,
            'shipping_refund_tax': 1.5,
            'order_adjustments_json': json.dumps([
                {'amount': 0.03, 'tax_amount': 0.0, 'reason': 'rounding'},
            ]),
        })
        self.env['sim.shopify.refund.line'].create({
            'refund_id': sim_refund.id,
            'line_item_gid': 'gid://shopify/LineItem/FID1',
            'line_item_title': 'Test Widget',
            'variant_gid': 'gid://shopify/ProductVariant/RF200',
            'variant_sku': 'TAX-W001',
            'quantity': 1,
            'subtotal': 100.0,
            'tax_amount': 10.0,
        })

        node = sim_refund._to_graphql_node()

        # Top-level fields
        for key in ('id', 'note', 'createdAt', 'totalRefundedSet',
                     'refundLineItems', 'refundShippingLines',
                     'orderAdjustments'):
            self.assertIn(key, node, f"Missing top-level field: {key}")

        # totalRefundedSet structure
        trs = node['totalRefundedSet']
        self.assertIn('shopMoney', trs)
        self.assertIn('amount', trs['shopMoney'])
        self.assertIn('currencyCode', trs['shopMoney'])
        self.assertIn('presentmentMoney', trs)

        # refundLineItems.edges[0].node
        edges = node['refundLineItems']['edges']
        self.assertTrue(edges, "refundLineItems must have edges")
        rli = edges[0]['node']
        for key in ('lineItem', 'quantity', 'restockType',
                     'subtotalSet', 'totalTaxSet'):
            self.assertIn(key, rli, f"Missing refundLineItem field: {key}")
        # lineItem sub-fields
        li = rli['lineItem']
        for key in ('id', 'title', 'variant'):
            self.assertIn(key, li, f"Missing lineItem field: {key}")
        self.assertIn('id', li['variant'])
        self.assertIn('sku', li['variant'])
        # totalTaxSet structure
        tts = rli['totalTaxSet']
        self.assertIn('shopMoney', tts)
        self.assertEqual(tts['shopMoney']['amount'], '10.0')

        # refundShippingLines.edges[0].node
        ship_edges = node['refundShippingLines']['edges']
        self.assertTrue(ship_edges, "refundShippingLines must have edges")
        ship_node = ship_edges[0]['node']
        for key in ('subtotalAmountSet', 'taxAmountSet'):
            self.assertIn(key, ship_node,
                          f"Missing refundShippingLine field: {key}")
        self.assertEqual(
            ship_node['subtotalAmountSet']['shopMoney']['amount'], '15.0',
        )
        self.assertEqual(
            ship_node['taxAmountSet']['shopMoney']['amount'], '1.5',
        )

        # orderAdjustments
        adjs = node['orderAdjustments']
        self.assertTrue(adjs, "orderAdjustments must have entries")
        adj = adjs[0]
        for key in ('amountSet', 'taxAmountSet', 'reason'):
            self.assertIn(key, adj,
                          f"Missing orderAdjustment field: {key}")
        self.assertEqual(adj['reason'], 'rounding')


class TestTaxedRefundE2E(ShopifyAccountingMixin, TransactionCase):
    """B-6b: End-to-end taxed partial refund through the simulator."""

    def setUp(self):
        super().setUp()
        self._setup_accounting()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Refund E2E Test',
            'shop_url': 'refund-e2e.myshopify.com',
            'access_token': 'shpat_refund_e2e',
            'company_id': self.env.company.id,
            'state': 'connected',
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
        })
        self.product = self.env['product.product'].create({
            'name': 'Taxed Widget', 'list_price': 100.0,
            'default_code': 'TAX-W001',
        })
        self._set_product_income_account(self.product)
        product_binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.product_tmpl_id.id,
            'shopify_id': 'gid://shopify/Product/RF100',
            'sync_status': 'synced',
        })
        self.variant_binding = self.env['shopify.variant.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': self.product.id,
            'shopify_id': 'gid://shopify/ProductVariant/RF200',
            'product_binding_id': product_binding.id,
            'sync_status': 'synced',
        })
        # 10% tax for rate-matching
        self.tax_10 = self.env['account.tax'].create({
            'name': 'Test Tax 10%',
            'type_tax_use': 'sale',
            'amount': 10.0,
            'amount_type': 'percent',
            'company_id': self.env.company.id,
        })
        # The fixture charges untaxed shipping; pre-create the shipping
        # product WITHOUT the company default sale tax so the computed
        # invoice matches the Shopify charge and the total-check guard
        # (DEC-011) lets it post. The shipping default-tax leak itself is
        # AUD-015 (item 3c) with its own coverage — not under test here.
        if not self.env['product.product'].search(
            [('default_code', '=', 'SHOPIFY-SHIPPING')], limit=1,
        ):
            self.env['product.product'].create({
                'name': 'Shopify Shipping',
                'default_code': 'SHOPIFY-SHIPPING',
                'type': 'service',
                'list_price': 0,
                'taxes_id': [(5, 0, 0)],
            })

    def test_taxed_partial_refund_e2e_through_simulator(self):
        """Seed a taxed order, build a partial refund from the
        simulator model's _to_graphql_node(), import through the
        real RefundImporter, and assert credit-note correctness.
        """
        from odoo.addons.shopify_connector_pro.sync.refund_sync import (
            RefundImporter,
        )
        from odoo.addons.shopify_connector_pro.sync.order_sync import (
            OrderImporter,
        )

        # ── Step 1: Import a taxed order ──
        order_node = {
            'id': 'gid://shopify/Order/RFUND001',
            'name': '#RFUND001',
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
                'shopMoney': {'amount': '235.00', 'currencyCode': 'USD'},
            },
            'subtotalPriceSet': {
                'shopMoney': {'amount': '200.00', 'currencyCode': 'USD'},
            },
            'totalShippingPriceSet': {
                'shopMoney': {'amount': '15.00', 'currencyCode': 'USD'},
            },
            'totalTaxSet': {
                'shopMoney': {'amount': '20.00', 'currencyCode': 'USD'},
            },
            'totalDiscountsSet': {
                'shopMoney': {'amount': '0.00', 'currencyCode': 'USD'},
            },
            'discountCodes': [],
            'customer': {
                'id': 'gid://shopify/Customer/RF500',
                'email': 'taxrefund@example.com',
                'firstName': 'Tax', 'lastName': 'Refund',
            },
            'shippingAddress': {
                'address1': '10 Tax Lane', 'address2': '',
                'city': 'London', 'province': '', 'provinceCode': '',
                'country': 'United Kingdom', 'countryCodeV2': 'GB',
                'zip': 'EC1A 1BB', 'phone': '',
                'firstName': 'Tax', 'lastName': 'Refund',
            },
            'billingAddress': None,
            'lineItems': {
                'edges': [{
                    'node': {
                        'id': 'gid://shopify/LineItem/RFT1',
                        'title': 'Taxed Widget',
                        'quantity': 2,
                        'variant': {
                            'id': 'gid://shopify/ProductVariant/RF200',
                            'sku': 'TAX-W001',
                            'product': {'id': 'gid://shopify/Product/RF100'},
                        },
                        'originalUnitPriceSet': {
                            'shopMoney': {
                                'amount': '100.00',
                                'currencyCode': 'USD',
                            },
                        },
                        'discountAllocations': [],
                        'taxLines': [{
                            'title': 'VAT',
                            'rate': 0.1,
                            'priceSet': {
                                'shopMoney': {
                                    'amount': '20.00',
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
                                'amount': '15.00',
                                'currencyCode': 'USD',
                            },
                        },
                    },
                }],
            },
            'refunds': [{'id': 'gid://shopify/Refund/RFT-001'}],
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

        importer._import_one(order_node, existing_binding=None)

        order_binding = self.env['shopify.order.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Order/RFUND001'),
        ])
        self.assertTrue(order_binding)
        order = order_binding.odoo_id

        posted = order.invoice_ids.filtered(
            lambda i: i.state == 'posted' and i.move_type == 'out_invoice'
        )
        self.assertTrue(posted, "Posted invoice required for refund test")

        # ── Step 2: Build refund from simulator model ──
        sim_config = self.env['sim.shopify.config'].create({
            'backend_id': self.backend.id,
            'shop_name': 'E2E Refund Config',
            'myshopify_domain': 'refund-e2e.myshopify.com',
        })
        sim_order = self.env['sim.shopify.order'].create({
            'config_id': sim_config.id,
            'shopify_gid': 'gid://shopify/Order/RFUND001',
            'name': '#RFUND001',
            'financial_status': 'PARTIALLY_REFUNDED',
            'total_price': 235.0,
        })
        sim_refund = self.env['sim.shopify.refund'].create({
            'config_id': sim_config.id,
            'order_id': sim_order.id,
            'shopify_gid': 'gid://shopify/Refund/RFT-001',
            'total_refunded': 125.0,
            'shipping_refund_subtotal': 15.0,
            'shipping_refund_tax': 0.0,
        })
        self.env['sim.shopify.refund.line'].create({
            'refund_id': sim_refund.id,
            'line_item_gid': 'gid://shopify/LineItem/RFT1',
            'line_item_title': 'Taxed Widget',
            'variant_gid': 'gid://shopify/ProductVariant/RF200',
            'variant_sku': 'TAX-W001',
            'quantity': 1,
            'subtotal': 100.0,
            'tax_amount': 10.0,
        })

        # Get the simulator-built response (NOT a hand-built mock)
        refund_node = sim_refund._to_graphql_node()

        # ── Step 3: Feed through the real RefundImporter ──
        mock_api_response = {
            'data': {
                'order': {
                    'refunds': [refund_node],
                },
            },
        }
        mock_client = MagicMock()
        mock_client.execute.return_value = mock_api_response

        with patch.object(
            type(self.backend), '_make_api_client',
            return_value=mock_client,
        ):
            refund_importer = RefundImporter(self.env, self.backend)
            success, errors, skipped = refund_importer.import_refunds_for_order(
                order_binding,
            )

        self.assertEqual(success, 1, "One refund must be imported")
        self.assertEqual(errors, 0, "No errors expected")

        # ── Step 4: Assert credit note correctness ──
        refund_binding = self.env['shopify.refund.binding'].search([
            ('backend_id', '=', self.backend.id),
            ('shopify_id', '=', 'gid://shopify/Refund/RFT-001'),
        ])
        self.assertTrue(refund_binding)
        self.assertEqual(refund_binding.sync_status, 'synced')

        cn = refund_binding.odoo_id
        self.assertTrue(cn, "Credit note must exist")
        self.assertEqual(cn.move_type, 'out_refund')
        self.assertEqual(cn.state, 'posted')

        # amount_total must match totalRefundedSet ($125)
        self.assertAlmostEqual(
            cn.amount_total, 125.0, places=2,
            msg="Credit note must match totalRefundedSet ($125 = "
                "$100 product + $10 tax + $15 shipping)",
        )

        # Product line must carry tax
        product_lines = cn.invoice_line_ids.filtered(
            lambda l: l.product_id == self.product
            and l.display_type == 'product'
        )
        self.assertTrue(product_lines, "Must have a product refund line")
        self.assertTrue(
            product_lines[0].tax_ids,
            "Product refund line must carry tax_ids",
        )

        # Shipping line must exist
        shipping_product = self.env['product.product'].search(
            [('default_code', '=', 'SHOPIFY-SHIPPING')], limit=1,
        )
        if shipping_product:
            shipping_lines = cn.invoice_line_ids.filtered(
                lambda l: l.product_id == shipping_product
                and l.display_type == 'product'
            )
            self.assertTrue(
                shipping_lines,
                "Credit note must have a shipping refund line",
            )
            self.assertAlmostEqual(
                shipping_lines[0].price_unit, 15.0, places=2,
                msg="Shipping refund must be $15",
            )
