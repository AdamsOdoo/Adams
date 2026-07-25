import ast
import copy
import json
import re
import uuid
from contextlib import contextmanager
from pathlib import Path

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.shopify_connector_core.models.shopify_connector_job_dispatch import (
    JobHandlerError,
    REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
)

from ..models.shopify_connector_order_importer import (
    ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY,
    ORDER_HEADER_QUERY,
    ORDER_LINE_ITEMS_PAGE_QUERY,
    ORDER_SHIPPING_LINES_PAGE_QUERY,
    REDACTION_EXTENSION,
)


MODULE_ROOT = Path(__file__).resolve().parents[1]
MODELS_ROOT = MODULE_ROOT / 'models'


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
class OrderImportCase(TransactionCase):
    """Reusable, network-free Task-012 fixture substrate."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        label = cls.__name__.lower().replace('_', '-')
        cls.currency = cls.env.company.currency_id
        cls.store = cls.env['shopify.connector.store'].sudo().create({
            'name': 'Order import %s' % cls.__name__,
            'shop_domain': '%s.myshopify.com' % label[:45],
            'api_version': '2026-07',
            'state': 'connected',
            'granted_scopes': json.dumps(['read_orders', 'read_customers']),
        })
        cls.fallback_partner = cls.env['res.partner'].create({
            'name': 'Order Import Fallback',
        })
        cls.payment_term = cls.env.ref(
            'account.account_payment_term_immediate',
            raise_if_not_found=False,
        ) or cls.env['account.payment.term'].create({
            'name': 'Order Import Immediate',
        })
        cls.pricelist = cls.env['product.pricelist'].search([
            ('active', '=', True),
            ('currency_id', '=', cls.currency.id),
            '|', ('company_id', '=', False),
            ('company_id', '=', cls.env.company.id),
        ], order='company_id desc, id', limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env['product.pricelist'].create({
                'name': 'Order Import Pricelist',
                'currency_id': cls.currency.id,
                'company_id': cls.env.company.id,
            })
        cls.settings = cls.env[
            'shopify.connector.store.settings'
        ].sudo().create({
            'store_id': cls.store.id,
            'sale_domain_enabled': True,
            'order_company_id': cls.env.company.id,
            'order_pricelist_id': cls.pricelist.id,
            'order_payment_term_id': cls.payment_term.id,
            'customer_fallback_partner_id': cls.fallback_partner.id,
        })
        cls.product_template = cls.env['product.template'].create({
            'name': 'Order Import Product',
            'type': 'service',
            'company_id': cls.env.company.id,
            'list_price': 100.0,
        })
        cls.product = cls.product_template.product_variant_id
        cls.template_binding = cls.env[
            'shopify.connector.product.template.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/Product/1200',
            'product_template_id': cls.product_template.id,
        })
        cls.variant_binding = cls.env[
            'shopify.connector.product.variant.binding'
        ].sudo().create({
            'store_id': cls.store.id,
            'shopify_gid': 'gid://shopify/ProductVariant/1200',
            'product_variant_id': cls.product.id,
            'product_template_binding_id': cls.template_binding.id,
        })
        cls.Importer = cls.env['shopify.connector.order.importer']
        cls.Binding = cls.env['shopify.connector.order.binding']
        cls.Job = cls.env['shopify.connector.job']
        cls.JobLog = cls.env['shopify.connector.job.log']
        cls.roles = {
            label: cls._role_user(label, xmlid)
            for label, xmlid in (
                ('auditor', 'group_shopify_connector_auditor'),
                ('operator', 'group_shopify_connector_operator'),
                ('reviewer', 'group_shopify_connector_reviewer'),
                ('admin', 'group_shopify_connector_admin'),
            )
        }

    @classmethod
    def _role_user(cls, label, xmlid):
        return cls.env['res.users'].create({
            'name': '%s %s' % (cls.__name__, label),
            'login': '%s_%s' % (cls.__name__.lower(), label),
            'company_id': cls.env.company.id,
            'company_ids': [(6, 0, [cls.env.company.id])],
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('shopify_connector_core.%s' % xmlid).id,
            ])],
        })

    def _money(self, amount, currency=False):
        currency = currency or self.currency.name
        amount = str(amount)
        return {
            'shopMoney': {'amount': amount, 'currencyCode': currency},
            'presentmentMoney': {
                'amount': amount, 'currencyCode': currency,
            },
        }

    def _transaction(
        self, gateway='Cash on Delivery', manual=True, status='PENDING',
        kind='SALE', amount='0',
    ):
        return {
            'id': 'gid://shopify/OrderTransaction/1',
            'gateway': gateway,
            'kind': kind,
            'status': status,
            'manualPaymentGateway': manual,
            'processedAt': '2026-07-17T10:00:00Z',
            'amountSet': self._money(amount),
        }

    def _payload(self, gid='gid://shopify/Order/1200', status='PAID'):
        zero = self._money('0.00')
        total = self._money('100.00')
        return {
            'id': gid,
            'name': '#1200',
            'legacyResourceId': '1200',
            'createdAt': '2026-07-17T09:00:00Z',
            'processedAt': '2026-07-17T10:00:00Z',
            'updatedAt': '2026-07-17T11:00:00Z',
            'edited': False,
            'test': False,
            'confirmed': True,
            'closed': False,
            'closedAt': None,
            'cancelledAt': None,
            'cancelReason': None,
            'currencyCode': self.currency.name,
            'presentmentCurrencyCode': self.currency.name,
            'taxesIncluded': False,
            'displayFinancialStatus': status,
            'displayFulfillmentStatus': 'UNFULFILLED',
            'email': None,
            'customer': None,
            'billingAddress': None,
            'shippingAddress': None,
            'paymentGatewayNames': [],
            'transactions': [],
            'totalPriceSet': total,
            'subtotalPriceSet': total,
            'totalTaxSet': zero,
            'totalDiscountsSet': zero,
            'totalShippingPriceSet': zero,
            'totalTipReceivedSet': zero,
            'currentTotalPriceSet': total,
            'currentTotalTaxSet': zero,
            'currentShippingPriceSet': zero,
            'currentTotalAdditionalFeesSet': None,
            'currentTotalDutiesSet': None,
            'totalCashRoundingAdjustment': {
                'paymentSet': zero,
                'refundSet': zero,
            },
            'taxLines': [],
            'line_items': [{
                'id': 'gid://shopify/LineItem/1200',
                'name': 'Order Import Product',
                'title': 'Order Import Product',
                'variantTitle': None,
                'quantity': 1,
                'currentQuantity': 1,
                'sku': 'ORDER-1200',
                'isGiftCard': False,
                'requiresShipping': False,
                'taxable': False,
                'variant': {'id': self.variant_binding.shopify_gid},
                'product': {'id': self.template_binding.shopify_gid},
                'originalUnitPriceSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'originalTotalSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'discountedUnitPriceSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'discountedTotalSet': {
                    'shopMoney': {'amount': '100.00'},
                },
                'priceAfterAllDiscountsBeforeTaxesSet': total,
                'discountAllocations': [],
                'taxLines': [],
            }],
            'shipping_lines': [],
            'discount_applications': [],
        }

    def _job(self, job_type='order_import_sync', target=False, state='queued'):
        return self.Job.sudo().create({
            'store_id': self.store.id,
            'job_source': 'manual_sync',
            'job_type': job_type,
            'state': state,
            'payload_hash': str(uuid.uuid4()),
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': target or 'gid://shopify/Order/1200',
            'expected_connection_generation': self.store.connection_generation,
        })


@tagged('post_install', '-at_install')
class TestOrderImportMappingStatic(TransactionCase):

    def _source(self, filename):
        return (MODELS_ROOT / filename).read_text(encoding='utf-8')

    def _tree(self, filename):
        return ast.parse(self._source(filename), filename=filename)

    def test_all_five_model_files_are_registered_exactly_once(self):
        tree = ast.parse(
            (MODELS_ROOT / '__init__.py').read_text(encoding='utf-8')
        )
        imported = [
            alias.name
            for node in tree.body if isinstance(node, ast.ImportFrom)
            for alias in node.names
        ]
        for name in (
            'shopify_connector_order_binding',
            'shopify_connector_sale_order_line',
            'shopify_connector_order_importer',
            'shopify_connector_tax_mapping',
            'shopify_connector_order_scan',
        ):
            self.assertEqual(imported.count(name), 1, name)

    def test_four_graphql_operations_are_read_only_and_minimal(self):
        queries = (
            ORDER_HEADER_QUERY,
            ORDER_LINE_ITEMS_PAGE_QUERY,
            ORDER_SHIPPING_LINES_PAGE_QUERY,
            ORDER_DISCOUNT_APPLICATIONS_PAGE_QUERY,
        )
        self.assertEqual(len(queries), 4)
        for query in queries:
            self.assertTrue(query.lstrip().startswith('query '))
            self.assertNotIn('mutation ', query.casefold())
            self.assertIn('edges { cursor node', query)
            self.assertIn('pageInfo { hasNextPage endCursor }', query)
        joined = '\n'.join(queries)
        for excluded in (
            'additionalFees', 'customAttributes', 'vendor', 'tags', 'note',
            'sourceName', 'displayName', 'defaultAddress', 'code', 'custom',
        ):
            self.assertIsNone(
                re.search(r'\b%s\b' % re.escape(excluded), joined), excluded,
            )
        for required in (
            'currentTotalPriceSet', 'currentTotalTaxSet',
            'currentShippingPriceSet', 'currentTotalAdditionalFeesSet',
            'currentTotalDutiesSet', 'totalCashRoundingAdjustment', 'edited',
            'isRemoved', 'currentDiscountedPriceSet',
        ):
            self.assertIn(required, ORDER_HEADER_QUERY)

    def test_execute_business_only_and_no_context_bypass(self):
        for filename in (
            'shopify_connector_order_importer.py',
            'shopify_connector_order_scan.py',
        ):
            tree = self._tree(filename)
            attributes = [
                node.attr for node in ast.walk(tree)
                if isinstance(node, ast.Attribute)
            ]
            self.assertIn('execute_business', attributes, filename)
            self.assertNotIn('execute', attributes, filename)
            self.assertNotIn('with_context', attributes, filename)

    def test_exact_sudo_inventory_and_dispatch_create_guard(self):
        expected = {
            'shopify_connector_order_binding.py': 2,
            'shopify_connector_order_importer.py': 2,
            'shopify_connector_order_scan.py': 1,
            'shopify_connector_tax_mapping.py': 0,
        }
        for filename, count in expected.items():
            tree = self._tree(filename)
            sudo_calls = [
                node for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == 'sudo'
            ]
            self.assertEqual(len(sudo_calls), count, filename)
            for class_node in (
                node for node in tree.body
                if isinstance(node, ast.ClassDef)
                and 'Dispatch' in node.name
            ):
                creates = [
                    node for node in ast.walk(class_node)
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == 'create'
                ]
                self.assertFalse(creates, (filename, class_node.name))
        binding_source = self._source('shopify_connector_order_binding.py')
        self.assertIn(
            "self.sale_order_id.sudo().read(\n"
            "            ['company_id', 'state'],",
            binding_source,
        )

    def test_manifest_dependency_graph_and_registration_contract(self):
        manifest = ast.literal_eval(
            (MODULE_ROOT / '__manifest__.py').read_text(encoding='utf-8')
        )
        self.assertEqual(manifest['version'], '19.0.2.0.0')
        self.assertEqual(
            manifest['depends'],
            ['shopify_connector_core', 'shopify_connector_product', 'sale'],
        )
        self.assertEqual(manifest['data'], [
            'security/ir.model.access.csv',
            'data/shopify_connector_sale_cron.xml',
        ])

    def test_job_types_have_lc1_ondelete_and_replay_policy(self):
        for filename, job_type in (
            ('shopify_connector_order_importer.py', 'order_import_sync'),
            ('shopify_connector_order_scan.py', 'order_import_scan'),
        ):
            source = self._source(filename)
            self.assertIn("selection_add=[('%s'," % job_type, source)
            self.assertIn("'%s': lambda recs:" % job_type, source)
            self.assertIn('_reassign_to_historic_job_type()', source)
            self.assertIn(
                "policies['%s'] = REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE"
                % job_type,
                source,
            )
        self.assertEqual(
            REPLAY_POLICY_REMOTE_READ_REPLAY_SAFE,
            'remote_read_replay_safe',
        )

    def test_no_tax_autocreate_or_shopify_mutation_surface(self):
        importer = self._source('shopify_connector_order_importer.py')
        mapping = self._source('shopify_connector_tax_mapping.py')
        combined = importer + mapping
        self.assertNotIn("env['account.tax'].create", combined)
        self.assertNotIn('order_tax_autocreate', combined)
        self.assertNotIn('orderMarkAsPaid', combined)
        self.assertNotIn('orderCreateManualPayment', combined)
        self.assertNotIn('mutation Connector', combined)

    def test_redaction_extension_covers_direct_order_pii(self):
        self.assertTrue({
            'email', 'phone', 'firstName', 'lastName',
            'billingAddress', 'shippingAddress', 'address1', 'address2',
        }.issubset(REDACTION_EXTENSION))

    @contextmanager
    def _result(self, body):
        yield body

    def test_connection_pagination_collects_once_and_detects_torn_reads(self):
        importer = self.env['shopify.connector.order.importer']
        gid = 'gid://shopify/Order/Paginated'
        first = {
            'edges': [{
                'cursor': 'edge-1',
                'node': {'id': 'gid://shopify/LineItem/1'},
            }],
            'pageInfo': {'hasNextPage': True, 'endCursor': 'page-1'},
        }

        class FakeClient:
            def __init__(client, bodies):
                client.bodies = iter(bodies)

            def execute_business(client, *args, **kwargs):
                return self._result(next(client.bodies))

        second = {'data': {'order': {
            'id': gid,
            'updatedAt': '2026-07-17T11:00:00Z',
            'lineItems': {
                'edges': [{
                    'cursor': 'edge-2',
                    'node': {'id': 'gid://shopify/LineItem/2'},
                }],
                'pageInfo': {'hasNextPage': False, 'endCursor': None},
            },
        }}}
        nodes = importer._collect_connection(
            FakeClient([second]), False, self.env['shopify.connector.store'],
            gid, '2026-07-17T11:00:00Z', first, 'lineItems',
            ORDER_LINE_ITEMS_PAGE_QUERY, 100,
        )
        self.assertEqual(
            [node['id'] for node in nodes],
            ['gid://shopify/LineItem/1', 'gid://shopify/LineItem/2'],
        )

        torn = copy.deepcopy(second)
        torn['data']['order']['updatedAt'] = '2026-07-17T11:01:00Z'
        with self.assertRaises(JobHandlerError) as caught:
            importer._collect_connection(
                FakeClient([torn]), False,
                self.env['shopify.connector.store'], gid,
                '2026-07-17T11:00:00Z', first, 'lineItems',
                ORDER_LINE_ITEMS_PAGE_QUERY, 100,
            )
        self.assertEqual(caught.exception.error_class, 'concurrency_race_conflict')

        with self.assertRaises(JobHandlerError) as ceiling:
            importer._collect_connection(
                FakeClient([]), False,
                self.env['shopify.connector.store'], gid,
                '2026-07-17T11:00:00Z', first, 'lineItems',
                ORDER_LINE_ITEMS_PAGE_QUERY, 1,
            )
        self.assertEqual(
            ceiling.exception.error_class, 'data_shape_schema_mismatch',
        )
        self.assertIn('page ceiling (1)', ceiling.exception.reason)

        repeated_cursor = copy.deepcopy(second)
        repeated_cursor['data']['order']['lineItems']['pageInfo'] = {
            'hasNextPage': True,
            'endCursor': 'page-1',
        }
        with self.assertRaises(JobHandlerError) as stalled:
            importer._collect_connection(
                FakeClient([repeated_cursor]), False,
                self.env['shopify.connector.store'], gid,
                '2026-07-17T11:00:00Z', first, 'lineItems',
                ORDER_LINE_ITEMS_PAGE_QUERY, 100,
            )
        self.assertEqual(
            stalled.exception.error_class, 'data_shape_schema_mismatch',
        )
        self.assertIn('cursor did not make progress', stalled.exception.reason)

    def test_duplicate_node_across_pages_fails_closed(self):
        importer = self.env['shopify.connector.order.importer']
        collected = []
        cursors = set()
        identities = set()
        importer._append_page_edges(
            'lineItems', [{
                'cursor': 'edge-a',
                'node': {'id': 'gid://shopify/LineItem/Duplicate'},
            }], collected, cursors, identities,
        )
        with self.assertRaises(JobHandlerError):
            importer._append_page_edges(
                'lineItems', [{
                    'cursor': 'edge-b',
                    'node': {'id': 'gid://shopify/LineItem/Duplicate'},
                }], collected, cursors, identities,
            )

        shipping = []
        shipping_cursors = set()
        shipping_identities = set()
        importer._append_page_edges(
            'shippingLines', [
                {'cursor': 'ship-a', 'node': {'id': None}},
                {'cursor': 'ship-b', 'node': {'id': None}},
            ], shipping, shipping_cursors, shipping_identities,
        )
        self.assertEqual(len(shipping), 2)
        self.assertEqual(shipping_identities, set())

        discounts = []
        discount_cursors = set()
        discount_identities = set()
        importer._append_page_edges(
            'discountApplications', [{
                'cursor': 'discount-a',
                'node': {'__typename': 'DiscountCodeApplication', 'index': 0},
            }], discounts, discount_cursors, discount_identities,
        )
        with self.assertRaises(JobHandlerError) as repeated_discount:
            importer._append_page_edges(
                'discountApplications', [{
                    'cursor': 'discount-b',
                    'node': {
                        '__typename': 'DiscountCodeApplication', 'index': 0,
                    },
                }], discounts, discount_cursors, discount_identities,
            )
        self.assertEqual(
            repeated_discount.exception.error_class,
            'data_shape_schema_mismatch',
        )


@tagged('post_install', '-at_install')
class TestOrderImportMappingFunctional(OrderImportCase):

    def test_connector_service_products_are_idempotent_and_store_scoped(self):
        second_store = self.env['shopify.connector.store'].sudo().create({
            'name': 'Second Order Store',
            'shop_domain': 'second-order-store.myshopify.com',
            'api_version': '2026-07',
            'state': 'connected',
        })
        second_settings = self.env[
            'shopify.connector.store.settings'
        ].sudo().create({
            'store_id': second_store.id,
            'sale_domain_enabled': True,
            'order_company_id': self.env.company.id,
        })
        first = self.Importer._service_product(
            'SHOPIFY-CUSTOM', 'Shopify Custom Item',
            self.settings, self.store,
        )
        first_again = self.Importer._service_product(
            'SHOPIFY-CUSTOM', 'Shopify Custom Item',
            self.settings, self.store,
        )
        second = self.Importer._service_product(
            'SHOPIFY-CUSTOM', 'Shopify Custom Item',
            second_settings, second_store,
        )

        self.assertEqual(first, first_again)
        self.assertNotEqual(first, second)
        self.assertEqual(first.default_code, 'SHOPIFY-CUSTOM')
        self.assertEqual(second.default_code, 'SHOPIFY-CUSTOM')
        self.assertIn('store %d' % self.store.id, first.name)
        self.assertIn('store %d' % second_store.id, second.name)

        custom_payload = self._payload('gid://shopify/Order/CustomLine')
        custom_item = custom_payload['line_items'][0]
        custom_item.update({
            'variant': None,
            'product': None,
            'sku': '',
            'title': 'Merchant Custom Line',
            'variantTitle': None,
        })
        custom = self.Importer._apply_import(self.store, custom_payload)
        self.assertEqual(custom.sale_order_id.order_line.product_id, first)
        self.assertEqual(
            custom.sale_order_id.order_line.name, 'Merchant Custom Line',
        )

        gift_payload = self._payload('gid://shopify/Order/GiftCardLine')
        gift_item = gift_payload['line_items'][0]
        gift_item.update({
            'variant': None,
            'product': None,
            'sku': '',
            'isGiftCard': True,
            'title': 'Gift Card',
            'variantTitle': None,
        })
        gift_job = self._job(target=gift_payload['id'])
        gift = self.Importer._apply_import(
            self.store, gift_payload, job=gift_job,
        )
        self.assertEqual(gift.sale_order_id.order_line.product_id, first)
        gift_logs = self.JobLog.search([
            ('job_id', '=', gift_job.id),
            ('event_type', '=', 'note'),
        ])
        self.assertEqual(len(gift_logs), 1)
        self.assertIn('no gift-card accounting', gift_logs.message)
        self.assertNotIn('Gift Card', gift_logs.technical_detail)

        missing_payload = self._payload(
            'gid://shopify/Order/MissingProductMapping',
        )
        missing_payload['line_items'][0]['variant'] = {
            'id': 'gid://shopify/ProductVariant/MissingOrderMapping',
        }
        missing_payload['line_items'][0]['product'] = {
            'id': 'gid://shopify/Product/MissingOrderMapping',
        }
        orders_before = self.env['sale.order'].search_count([])
        bindings_before = self.Binding.search_count([])
        with self.assertRaises(JobHandlerError) as missing:
            self.Importer._apply_import(self.store, missing_payload)
        self.assertEqual(missing.exception.error_class, 'mapping_missing')
        self.assertIn(
            'gid://shopify/ProductVariant/MissingOrderMapping',
            missing.exception.technical_detail,
        )
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before)
        self.assertEqual(self.Binding.search_count([]), bindings_before)

        mapped_template = self.env['product.template'].create({
            'name': 'Resolved Missing Order Product',
            'type': 'service',
            'company_id': self.env.company.id,
            'list_price': 100.0,
        })
        mapped_template_binding = self.env[
            'shopify.connector.product.template.binding'
        ].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': 'gid://shopify/Product/MissingOrderMapping',
            'product_template_id': mapped_template.id,
        })
        self.env[
            'shopify.connector.product.variant.binding'
        ].sudo().create({
            'store_id': self.store.id,
            'shopify_gid': (
                'gid://shopify/ProductVariant/MissingOrderMapping'
            ),
            'product_variant_id': mapped_template.product_variant_id.id,
            'product_template_binding_id': mapped_template_binding.id,
        })
        resolved = self.Importer._apply_import(self.store, missing_payload)
        self.assertEqual(
            resolved.sale_order_id.order_line.product_id,
            mapped_template.product_variant_id,
        )
        self.assertEqual(self.env['sale.order'].search_count([]), orders_before + 1)
        self.assertEqual(self.Binding.search_count([]), bindings_before + 1)

    def test_one_hundred_line_order_imports_without_truncation(self):
        payload = self._payload('gid://shopify/Order/HundredLines')
        seed = payload['line_items'][0]
        payload['line_items'] = []
        for index in range(100):
            line = copy.deepcopy(seed)
            line['id'] = 'gid://shopify/LineItem/Hundred/%d' % index
            payload['line_items'].append(line)
        for field_name in (
            'totalPriceSet', 'subtotalPriceSet', 'currentTotalPriceSet',
        ):
            payload[field_name] = self._money('10000.00')
        binding = self.Importer._apply_import(self.store, payload)
        self.assertEqual(len(binding.sale_order_id.order_line), 100)
        self.assertEqual(binding.sale_order_id.amount_total, 10000.0)
