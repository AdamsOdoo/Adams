import json
from types import SimpleNamespace

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
)

from ..models.shopify_connector_order_importer import (
    OrderFatalSchemaError,
    OrderPolicySkip,
)
from ..models.shopify_connector_tax_mapping import (
    SHOPIFY_TAX_FINGERPRINT_VERSION,
    build_tax_fingerprint,
)
from .test_order_import_mapping import OrderImportCase


class TestOrderTotalsGuard(OrderImportCase):

    def _tax_evidence(self, amount='5.00', presentment=True):
        price_set = {'shopMoney': {'amount': amount}}
        if presentment:
            price_set['presentmentMoney'] = {'amount': amount}
        return {
            'title': 'VAT 5',
            'source': 'Shopify',
            'rate': 0.05,
            'ratePercentage': 5.0,
            'channelLiable': None,
            'priceSet': price_set,
        }

    def _map_tax(self, included=False):
        company = self.env.company.sudo()
        current_company = self.env.company.sudo()
        country = (
            company.account_fiscal_country_id
            or company.country_id
            or current_company.account_fiscal_country_id
            or current_company.country_id
            or self.env.ref('base.us')
        )
        self.assertTrue(country, 'Order totals tax fixture country must resolve')
        country.ensure_one()

        tax_group = self.env['account.tax.group'].sudo().create({
            'name': 'Order guard VAT 5 %s Group'
                    % ('included' if included else 'excluded'),
            'company_id': company.id,
            'country_id': country.id,
        })
        tax = self.env['account.tax'].sudo().create({
            'name': 'Order guard VAT 5 %s' % ('included' if included else 'excluded'),
            'amount': 5.0,
            'amount_type': 'percent',
            'type_tax_use': 'sale',
            'company_id': company.id,
            'country_id': country.id,
            'tax_group_id': tax_group.id,
            'price_include_override': (
                'tax_included' if included else 'tax_excluded'
            ),
            'include_base_amount': False,
        })
        self.assertTrue(tax.country_id)
        self.assertTrue(tax.tax_group_id.country_id)
        self.assertEqual(tax.company_id, tax.tax_group_id.company_id)
        self.assertEqual(tax.country_id, tax.tax_group_id.country_id)

        evidence = self._tax_evidence()
        key = build_tax_fingerprint(
            evidence['rate'], evidence['ratePercentage'], evidence['title'],
            evidence['source'], evidence['channelLiable'], included,
        )
        self.env['shopify.connector.tax.mapping'].create({
            'store_id': self.store.id,
            'shopify_tax_evidence_key': key,
            'shopify_tax_fingerprint_version': SHOPIFY_TAX_FINGERPRINT_VERSION,
            'shopify_price_included': included,
            'account_tax_id': tax.id,
        })
        return evidence

    def _taxed_payload(self, gid, included=False):
        order_evidence = self._map_tax(included=included)
        payload = self._payload(gid)
        payload['taxesIncluded'] = included
        payload['taxLines'] = [order_evidence]
        payload['line_items'][0]['taxable'] = True
        payload['line_items'][0]['taxLines'] = [
            self._tax_evidence(presentment=False)
        ]
        payload['totalTaxSet'] = self._money('5.00')
        payload['currentTotalTaxSet'] = self._money('5.00')
        payload['totalPriceSet'] = self._money('105.00')
        payload['currentTotalPriceSet'] = self._money('105.00')
        if included:
            for field_name in (
                'originalUnitPriceSet', 'originalTotalSet',
                'discountedUnitPriceSet', 'discountedTotalSet',
            ):
                payload['line_items'][0][field_name]['shopMoney'][
                    'amount'
                ] = '105.00'
        return payload

    def _assert_precreation_failure(self, payload, exception, reason=False):
        orders_before = self.env['sale.order'].search_count([])
        bindings_before = self.Binding.search_count([])
        with self.assertRaises(exception) as caught:
            self.Importer._precreation_gates(payload, self.settings)
        if reason:
            value = getattr(caught.exception, 'skip_reason', None)
            value = value or getattr(caught.exception, 'error_class', None)
            self.assertEqual(value, reason)
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)
        self.assertEqual(self.Binding.search_count([]), bindings_before)

    def test_null_financial_status_is_fatal_schema_mismatch(self):
        payload = self._payload()
        payload['displayFinancialStatus'] = None
        self._assert_precreation_failure(payload, OrderFatalSchemaError)

    def test_null_original_tax_is_schema_mismatch_even_when_current_zero(self):
        payload = self._payload()
        payload['totalTaxSet'] = None
        self._assert_precreation_failure(
            payload, JobHandlerError, 'data_shape_schema_mismatch',
        )

    def test_edit_refund_and_shipping_gates_hold_whole_order(self):
        cases = []
        edited = self._payload()
        edited['edited'] = True
        cases.append((edited, 'unsupported_order_edit'))

        quantity = self._payload()
        quantity['line_items'][0]['currentQuantity'] = 0
        cases.append((quantity, 'refunded_or_removed_quantity'))

        total = self._payload()
        total['currentTotalPriceSet'] = self._money('99.00')
        cases.append((total, 'refunded_or_removed_quantity'))

        shipping = self._payload()
        shipping['totalPriceSet'] = self._money('110.00')
        shipping['currentTotalPriceSet'] = self._money('110.00')
        shipping['totalShippingPriceSet'] = self._money('10.00')
        shipping['currentShippingPriceSet'] = self._money('4.00')
        shipping['shipping_lines'] = [{
            'id': 'gid://shopify/ShippingLine/1',
            'isRemoved': False,
            'title': 'Delivery',
            'discountedPriceSet': self._money('10.00'),
            'currentDiscountedPriceSet': self._money('4.00'),
            'taxLines': [],
        }]
        cases.append((shipping, 'refunded_or_removed_shipping'))

        for payload, reason in cases:
            with self.subTest(reason=reason):
                self._assert_precreation_failure(
                    payload, OrderPolicySkip, reason,
                )

    def test_duty_first_fee_cash_rounding_and_tip_gates(self):
        duty = self._payload()
        duty['currentTotalDutiesSet'] = self._money('2.00')
        duty['currentTotalAdditionalFeesSet'] = self._money('3.00')

        fee = self._payload()
        fee['currentTotalDutiesSet'] = self._money('0.00')
        fee['currentTotalAdditionalFeesSet'] = self._money('3.00')

        rounding = self._payload()
        rounding['totalCashRoundingAdjustment']['refundSet'] = self._money('-0.01')

        tip = self._payload()
        tip['totalTipReceivedSet'] = self._money('1.00')

        for payload, reason in (
            (duty, 'unsupported_duties'),
            (fee, 'unsupported_additional_fees'),
            (rounding, 'unsupported_cash_rounding'),
            (tip, 'unsupported_tip_tax_treatment'),
        ):
            with self.subTest(reason=reason):
                self._assert_precreation_failure(payload, OrderPolicySkip, reason)

    def test_currency_gate_checks_both_moneybag_sides(self):
        divergent = self._payload()
        divergent['presentmentCurrencyCode'] = 'ZZZ'
        for field_name in (
            'totalPriceSet', 'subtotalPriceSet', 'totalTaxSet',
            'totalDiscountsSet', 'totalShippingPriceSet',
            'totalTipReceivedSet', 'currentTotalPriceSet',
            'currentTotalTaxSet', 'currentShippingPriceSet',
            'currentTotalDutiesSet', 'currentTotalAdditionalFeesSet',
        ):
            if divergent[field_name] is not None:
                divergent[field_name]['presentmentMoney']['currencyCode'] = 'ZZZ'
        for field_name in ('paymentSet', 'refundSet'):
            divergent['totalCashRoundingAdjustment'][field_name][
                'presentmentMoney'
            ]['currencyCode'] = 'ZZZ'
        self._assert_precreation_failure(
            divergent, OrderPolicySkip, 'divergent_presentment_currency',
        )

        mismatched = self._payload()
        mismatched['totalPriceSet']['presentmentMoney']['amount'] = '99.00'
        self._assert_precreation_failure(
            mismatched, JobHandlerError, 'data_shape_schema_mismatch',
        )

        malformed = self._payload()
        malformed['currentTotalTaxSet']['shopMoney']['amount'] = 'NaN'
        self._assert_precreation_failure(
            malformed, JobHandlerError, 'data_shape_schema_mismatch',
        )

    def test_original_and_current_money_amounts_must_match(self):
        payload = self._payload()
        payload['currentTotalPriceSet'] = self._money('99.00')
        self._assert_precreation_failure(
            payload, OrderPolicySkip, 'refunded_or_removed_quantity',
        )

        payload = self._payload()
        payload['currentTotalTaxSet'] = self._money('0.01')
        self._assert_precreation_failure(
            payload, OrderPolicySkip, 'refunded_or_removed_quantity',
        )

    def test_basic_tax_free_order_reconciles_exactly(self):
        team = self.env['crm.team'].create({
            'name': 'Order Import Team',
            'company_id': self.env.company.id,
        })
        partner_term = self.payment_term.copy({
            'name': 'Partner Default Must Not Override Store Term',
        })
        self.fallback_partner.property_payment_term_id = partner_term
        self.settings.write({'order_sales_team_id': team.id})
        binding = self.Importer._apply_import(self.store, self._payload())
        order = binding.sale_order_id
        self.assertEqual(order.company_id, self.settings.order_company_id)
        self.assertEqual(order.pricelist_id, self.settings.order_pricelist_id)
        self.assertEqual(
            order.payment_term_id, self.settings.order_payment_term_id,
        )
        self.assertNotEqual(
            order.payment_term_id,
            self.fallback_partner.property_payment_term_id,
        )
        self.assertEqual(order.team_id, team)
        self.assertEqual(order.amount_untaxed, 100.0)
        self.assertEqual(order.amount_tax, 0.0)
        self.assertEqual(order.amount_total, 100.0)
        self.assertEqual(order.state, 'sale')
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(
            order.order_line.shopify_line_item_gid,
            'gid://shopify/LineItem/1200',
        )

        with self.assertRaises(JobHandlerError) as epd:
            self.Importer._validate_payment_term(SimpleNamespace(
                early_discount=True,
                early_pay_discount_computation='mixed',
                discount_percentage=2,
            ))
        self.assertEqual(
            epd.exception.error_class, 'odoo_validation_configuration',
        )
        self.assertEqual(
            epd.exception.technical_detail,
            'unsupported_early_payment_discount_payment_term',
        )

        self.settings.write({'order_payment_term_id': False})
        orders_before = self.env['sale.order'].search_count([])
        bindings_before = self.Binding.search_count([])
        with self.assertRaises(JobHandlerError) as unset_term:
            self.Importer._apply_import(
                self.store,
                self._payload('gid://shopify/Order/UnsetPaymentTerm'),
            )
        self.assertEqual(
            unset_term.exception.error_class,
            'odoo_validation_configuration',
        )
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)
        self.assertEqual(self.Binding.search_count([]), bindings_before)
        self.settings.write({'order_payment_term_id': self.payment_term.id})

        self.settings.write({'order_pricelist_id': False})
        fallback_pricelist = self.Importer._apply_import(
            self.store,
            self._payload('gid://shopify/Order/FallbackPricelist'),
        ).sale_order_id.pricelist_id
        self.assertEqual(fallback_pricelist.currency_id, self.currency)
        self.assertIn(
            fallback_pricelist.company_id,
            (self.env['res.company'], self.env.company),
        )
        matching = self.env['product.pricelist'].search([
            ('active', '=', True),
            ('currency_id', '=', self.currency.id),
            '|', ('company_id', '=', False),
            ('company_id', '=', self.env.company.id),
        ])
        self.assertIn(fallback_pricelist, matching)
        matching.write({'active': False})
        orders_before = self.env['sale.order'].search_count([])
        bindings_before = self.Binding.search_count([])
        with self.assertRaises(JobHandlerError) as no_pricelist:
            self.Importer._apply_import(
                self.store,
                self._payload('gid://shopify/Order/MissingPricelist'),
            )
        self.assertEqual(
            no_pricelist.exception.error_class,
            'odoo_validation_configuration',
        )
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)
        self.assertEqual(self.Binding.search_count([]), bindings_before)

    def test_exact_all_discount_line_is_not_double_subtracted(self):
        payload = self._payload('gid://shopify/Order/Discount')
        payload['name'] = '#DISCOUNT'
        payload['totalPriceSet'] = self._money('90.00')
        payload['currentTotalPriceSet'] = self._money('90.00')
        payload['subtotalPriceSet'] = self._money('90.00')
        payload['totalDiscountsSet'] = self._money('10.00')
        line = payload['line_items'][0]
        line['discountedUnitPriceAfterAllDiscountsSet'] = self._money('90.00')
        line['discountedTotalSet']['shopMoney']['amount'] = '100.00'
        line['discountedUnitPriceSet']['shopMoney']['amount'] = '100.00'
        line['discountAllocations'] = [{
            'allocatedAmountSet': {
                'shopMoney': {'amount': '10.00'},
                'presentmentMoney': {'amount': '10.00'},
            },
            'discountApplication': {
                '__typename': 'DiscountCodeApplication',
                'index': 0,
                'allocationMethod': 'ACROSS',
                'targetType': 'LINE_ITEM',
                'targetSelection': 'ALL',
            },
        }]
        payload['discount_applications'] = [{
            '__typename': 'DiscountCodeApplication',
            'index': 0,
            'allocationMethod': 'ACROSS',
            'targetType': 'LINE_ITEM',
            'targetSelection': 'ALL',
        }]
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.sale_order_id.amount_untaxed, 90.0)
        self.assertEqual(binding.sale_order_id.amount_total, 90.0)

    def test_discounted_unit_price_is_derived_to_the_whole_line(self):
        payload = self._payload('gid://shopify/Order/TwoUnits')
        payload['name'] = '#TWO-UNITS'
        payload['totalPriceSet'] = self._money('180.00')
        payload['subtotalPriceSet'] = self._money('180.00')
        payload['currentTotalPriceSet'] = self._money('180.00')
        payload['totalDiscountsSet'] = self._money('20.00')
        line = payload['line_items'][0]
        line['quantity'] = 2
        line['currentQuantity'] = 2
        line['originalTotalSet'] = self._money('200.00')
        line['discountedTotalSet'] = self._money('180.00')
        line['discountedUnitPriceAfterAllDiscountsSet'] = self._money('90.00')
        line['discountAllocations'] = [{
            'allocatedAmountSet': self._money('20.00'),
            'discountApplication': {
                '__typename': 'DiscountCodeApplication',
                'index': 0,
                'allocationMethod': 'ACROSS',
                'targetType': 'LINE_ITEM',
                'targetSelection': 'ALL',
            },
        }]
        payload['discount_applications'] = [{
            '__typename': 'DiscountCodeApplication',
            'index': 0,
            'allocationMethod': 'ACROSS',
            'targetType': 'LINE_ITEM',
            'targetSelection': 'ALL',
        }]
        binding = self.Importer._apply_import(self.store, payload)
        line = binding.sale_order_id.order_line.filtered(
            lambda candidate: candidate.shopify_line_item_gid
        )
        self.assertEqual(line.product_uom_qty, 2.0)
        self.assertEqual(line.price_unit, 100.0)
        self.assertEqual(line.discount, 10.0)
        self.assertEqual(binding.sale_order_id.amount_total, 180.0)

    def test_financial_mismatch_rolls_back_order_and_binding(self):
        payload = self._payload('gid://shopify/Order/BadTotal')
        payload['totalPriceSet'] = self._money('101.00')
        payload['currentTotalPriceSet'] = self._money('101.00')
        payload['subtotalPriceSet'] = self._money('90.00')
        payload['totalDiscountsSet'] = self._money('10.00')
        line = payload['line_items'][0]
        line['discountedUnitPriceAfterAllDiscountsSet'] = self._money('90.00')
        line['discountAllocations'] = [{
            'allocatedAmountSet': {
                'shopMoney': {'amount': '10.00'},
                'presentmentMoney': {'amount': '10.00'},
            },
            'discountApplication': {
                '__typename': 'DiscountCodeApplication',
                'index': 0,
                'allocationMethod': 'ACROSS',
                'targetType': 'LINE_ITEM',
                'targetSelection': 'ALL',
            },
        }]
        payload['discount_applications'] = [{
            '__typename': 'DiscountCodeApplication',
            'index': 0,
            'allocationMethod': 'ACROSS',
            'targetType': 'LINE_ITEM',
            'targetSelection': 'ALL',
        }]
        orders_before = self.env['sale.order'].search_count([])
        bindings_before = self.Binding.search_count([])
        with self.assertRaises(JobHandlerError) as caught:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(caught.exception.error_class, 'financial_total_mismatch')
        evidence = json.loads(caught.exception.technical_detail)
        line_evidence = evidence['line_evidence'][
            'product:gid://shopify/LineItem/1200:base'
        ]
        self.assertEqual(line_evidence['source_target_amount'], '90.00')
        self.assertEqual(
            line_evidence['discount_allocations'][0]['shop_amount'], '10.00',
        )
        self.assertEqual(
            line_evidence['discount_allocations'][0]['application_type'],
            'DiscountCodeApplication',
        )
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)
        self.assertEqual(self.Binding.search_count([]), bindings_before)

    def test_tax_excluded_and_tax_included_orders_use_mapped_engine_taxes(self):
        for included in (False, True):
            with self.subTest(included=included):
                payload = self._taxed_payload(
                    'gid://shopify/Order/Tax/%s' % included,
                    included=included,
                )
                binding = self.Importer._apply_import(self.store, payload)
                self.assertEqual(binding.sale_order_id.amount_untaxed, 100.0)
                self.assertEqual(binding.sale_order_id.amount_tax, 5.0)
                self.assertEqual(binding.sale_order_id.amount_total, 105.0)

    def test_order_and_source_tax_fingerprints_must_reconcile(self):
        payload = self._taxed_payload(
            'gid://shopify/Order/TaxFingerprintMismatch', included=False,
        )
        payload['taxLines'][0]['title'] = 'Different order-level tax identity'
        orders_before = self.env['sale.order'].search_count([])
        with self.assertRaises(JobHandlerError) as caught:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(caught.exception.error_class, 'financial_total_mismatch')
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)

    def test_unknown_order_liability_accepts_known_line_liability(self):
        payload = self._taxed_payload(
            'gid://shopify/Order/TaxAggregateUnknownLiability',
            included=True,
        )
        self.assertIsNone(payload['taxLines'][0]['channelLiable'])
        line_evidence = payload['line_items'][0]['taxLines'][0]
        line_evidence['channelLiable'] = False
        aggregate_mapping = self.env['shopify.connector.tax.mapping'].search([
            ('store_id', '=', self.store.id),
            ('shopify_price_included', '=', True),
        ], limit=1)
        self.assertTrue(aggregate_mapping)
        self.env['shopify.connector.tax.mapping'].create({
            'store_id': self.store.id,
            'shopify_tax_evidence_key': build_tax_fingerprint(
                line_evidence['rate'], line_evidence['ratePercentage'],
                line_evidence['title'], line_evidence['source'],
                line_evidence['channelLiable'], True,
            ),
            'shopify_tax_fingerprint_version': SHOPIFY_TAX_FINGERPRINT_VERSION,
            'shopify_price_included': True,
            'account_tax_id': aggregate_mapping.account_tax_id.id,
        })
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.sale_order_id.amount_tax, 5.0)

    def test_known_order_liability_still_rejects_known_line_disagreement(self):
        payload = self._taxed_payload(
            'gid://shopify/Order/TaxKnownLiabilityMismatch', included=False,
        )
        payload['taxLines'][0]['channelLiable'] = True
        payload['line_items'][0]['taxLines'][0]['channelLiable'] = False
        orders_before = self.env['sale.order'].search_count([])
        with self.assertRaises(JobHandlerError) as caught:
            self.Importer._apply_import(self.store, payload)
        self.assertEqual(caught.exception.error_class, 'financial_total_mismatch')
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)

    def test_high_value_discount_uses_exact_negative_tax_preserving_residual(self):
        payload = self._payload('gid://shopify/Order/DiscountResidual')
        payload['totalPriceSet'] = self._money('666.67')
        payload['currentTotalPriceSet'] = self._money('666.67')
        payload['subtotalPriceSet'] = self._money('666.67')
        payload['totalDiscountsSet'] = self._money('333.33')
        line = payload['line_items'][0]
        for field_name in (
            'originalUnitPriceSet', 'originalTotalSet',
            'discountedUnitPriceSet', 'discountedTotalSet',
        ):
            line[field_name]['shopMoney']['amount'] = '1000.00'
        line['discountedUnitPriceAfterAllDiscountsSet'] = self._money('666.67')
        line['discountAllocations'] = [{
            'allocatedAmountSet': {
                'shopMoney': {'amount': '333.33'},
                'presentmentMoney': {'amount': '333.33'},
            },
            'discountApplication': {
                '__typename': 'DiscountCodeApplication',
                'index': 0,
                'allocationMethod': 'ACROSS',
                'targetType': 'LINE_ITEM',
                'targetSelection': 'ALL',
            },
        }]
        payload['discount_applications'] = [{
            '__typename': 'DiscountCodeApplication',
            'index': 0,
            'allocationMethod': 'ACROSS',
            'targetType': 'LINE_ITEM',
            'targetSelection': 'ALL',
        }]
        binding = self.Importer._apply_import(self.store, payload)
        lines = binding.sale_order_id.order_line
        residual = lines.filtered(
            lambda value: value.product_id.default_code
            == 'SHOPIFY-ORDER-DISCOUNT'
        )
        self.assertEqual(len(residual), 1)
        self.assertLess(residual.price_subtotal, 0)
        self.assertEqual(residual.name, 'Shopify Order Discount')
        self.assertEqual(binding.sale_order_id.amount_untaxed, 666.67)
        self.assertEqual(binding.sale_order_id.amount_total, 666.67)

    def test_zero_decimal_currency_imports_but_three_decimal_is_held(self):
        Currency = self.env['res.currency'].with_context(active_test=False)
        jpy = Currency.search([('name', '=', 'JPY')], limit=1)
        self.assertTrue(jpy)
        jpy.sudo().write({'active': True})
        pricelist = self.env['product.pricelist'].create({
            'name': 'Order Import JPY',
            'currency_id': jpy.id,
            'company_id': self.env.company.id,
        })
        self.settings.write({'order_pricelist_id': pricelist.id})
        payload = self._payload('gid://shopify/Order/JPY')
        payload['currencyCode'] = 'JPY'
        payload['presentmentCurrencyCode'] = 'JPY'
        for field_name in (
            'totalPriceSet', 'subtotalPriceSet', 'currentTotalPriceSet',
        ):
            payload[field_name] = self._money('3000', 'JPY')
        for field_name in (
            'totalTaxSet', 'totalDiscountsSet', 'totalShippingPriceSet',
            'totalTipReceivedSet', 'currentTotalTaxSet',
            'currentShippingPriceSet',
        ):
            payload[field_name] = self._money('0', 'JPY')
        payload['totalCashRoundingAdjustment'] = {
            'paymentSet': self._money('0', 'JPY'),
            'refundSet': self._money('0', 'JPY'),
        }
        line = payload['line_items'][0]
        for field_name in (
            'originalUnitPriceSet', 'originalTotalSet',
            'discountedUnitPriceSet', 'discountedTotalSet',
        ):
            line[field_name]['shopMoney']['amount'] = '3000'
        line['discountedUnitPriceAfterAllDiscountsSet'] = self._money('3000', 'JPY')
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(binding.sale_order_id.amount_total, 3000.0)

        bhd = Currency.search([('name', '=', 'BHD')], limit=1)
        self.assertTrue(bhd)
        self.assertLess(bhd.rounding, 0.01)
        bhd.sudo().write({'active': True})
        payload = self._payload('gid://shopify/Order/BHD')
        payload['currencyCode'] = 'BHD'
        payload['presentmentCurrencyCode'] = 'BHD'
        for field_name in (
            'totalPriceSet', 'subtotalPriceSet', 'totalTaxSet',
            'totalDiscountsSet', 'totalShippingPriceSet',
            'totalTipReceivedSet', 'currentTotalPriceSet',
            'currentTotalTaxSet', 'currentShippingPriceSet',
        ):
            payload[field_name] = self._money(
                '10.000' if 'Price' in field_name or 'subtotal' in field_name
                else '0.000',
                'BHD',
            )
        payload['totalCashRoundingAdjustment'] = {
            'paymentSet': self._money('0.000', 'BHD'),
            'refundSet': self._money('0.000', 'BHD'),
        }
        self._assert_precreation_failure(
            payload, JobHandlerError, 'odoo_validation_configuration',
        )
