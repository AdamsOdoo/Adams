# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Tests for Phase 3+4 models and handlers.

Covers: Collections, Metafields, Gift Cards, Payouts, Abandoned Carts, Discounts.
"""
import json
import logging

from .common import SimulatorTestCase
from odoo.tools import mute_logger

_logger = logging.getLogger(__name__)


class TestSimCollection(SimulatorTestCase):
    """Test sim.shopify.collection model and handler."""

    def test_collection_create(self):
        coll = self.env['sim.shopify.collection'].create({
            'config_id': self.sim_config.id,
            'title': 'Summer Collection',
        })
        self.assertTrue(coll.shopify_gid)
        self.assertEqual(coll.handle, 'summer-collection')
        self.assertEqual(coll.product_count, 0)

    def test_collection_with_products(self):
        p1 = self._seed_product('Collection Prod 1')
        p2 = self._seed_product('Collection Prod 2')
        coll = self.env['sim.shopify.collection'].create({
            'config_id': self.sim_config.id,
            'title': 'Mixed Collection',
            'product_ids': [(6, 0, [p1.id, p2.id])],
        })
        self.assertEqual(coll.product_count, 2)

    def test_collection_graphql_node(self):
        coll = self.env['sim.shopify.collection'].create({
            'config_id': self.sim_config.id,
            'title': 'Node Test',
            'sort_order': 'ALPHA_ASC',
        })
        node = coll._to_graphql_node()
        self.assertEqual(node['title'], 'Node Test')
        self.assertEqual(node['sortOrder'], 'ALPHA_ASC')
        self.assertIn('productsCount', node)

    def test_fetch_collections_handler(self):
        self.env['sim.shopify.collection'].create({
            'config_id': self.sim_config.id,
            'title': 'Handler Test',
        })
        result = self._call_query('collections', {'first': 10})
        self.assertIn('collections', result)
        self.assertEqual(len(result['collections']['edges']), 1)

    def test_collection_create_handler(self):
        result = self._call_mutation('collection_create', {
            'input': {
                'title': 'Mutation Collection',
                'descriptionHtml': '<p>Test</p>',
            },
        })
        self.assertIn('collectionCreate', result)
        coll = result['collectionCreate']['collection']
        self.assertEqual(coll['title'], 'Mutation Collection')


class TestSimMetafield(SimulatorTestCase):
    """Test sim.shopify.metafield model and handler."""

    def test_metafield_create(self):
        product = self._seed_product('Meta Product')
        mf = self.env['sim.shopify.metafield'].create({
            'config_id': self.sim_config.id,
            'owner_type': 'PRODUCT',
            'owner_gid': product.shopify_gid,
            'namespace': 'custom',
            'key': 'color',
            'value': 'red',
            'metafield_type': 'single_line_text_field',
        })
        self.assertTrue(mf.shopify_gid)
        self.assertEqual(mf.display_name, 'custom.color')

    def test_metafield_set_handler(self):
        product = self._seed_product('Meta Set Product')
        result = self._call_mutation('metafield_set', {
            'metafields': [{
                'ownerId': product.shopify_gid,
                'namespace': 'custom',
                'key': 'material',
                'value': 'cotton',
                'type': 'single_line_text_field',
            }],
        })
        self.assertIn('metafieldsSet', result)
        metafields = result['metafieldsSet']['metafields']
        self.assertEqual(len(metafields), 1)
        self.assertEqual(metafields[0]['key'], 'material')

    def test_metafield_upsert(self):
        """Setting same namespace+key should update, not create duplicate."""
        product = self._seed_product('Upsert Product')
        self._call_mutation('metafield_set', {
            'metafields': [{
                'ownerId': product.shopify_gid,
                'namespace': 'custom',
                'key': 'weight',
                'value': '100',
                'type': 'number_integer',
            }],
        })
        self._call_mutation('metafield_set', {
            'metafields': [{
                'ownerId': product.shopify_gid,
                'namespace': 'custom',
                'key': 'weight',
                'value': '200',
                'type': 'number_integer',
            }],
        })
        count = self.env['sim.shopify.metafield'].search_count([
            ('config_id', '=', self.sim_config.id),
            ('owner_gid', '=', product.shopify_gid),
            ('key', '=', 'weight'),
        ])
        self.assertEqual(count, 1)

    def test_metafield_delete_handler(self):
        product = self._seed_product('Delete Meta Product')
        mf = self.env['sim.shopify.metafield'].create({
            'config_id': self.sim_config.id,
            'owner_type': 'PRODUCT',
            'owner_gid': product.shopify_gid,
            'namespace': 'custom',
            'key': 'to_delete',
            'value': 'bye',
        })
        result = self._call_mutation('metafield_delete', {
            'input': {'id': mf.shopify_gid},
        })
        self.assertIn('metafieldDelete', result)
        self.assertFalse(mf.exists())

    def test_fetch_product_metafields_handler(self):
        product = self._seed_product('Fetch Meta Product')
        self.env['sim.shopify.metafield'].create({
            'config_id': self.sim_config.id,
            'owner_type': 'PRODUCT',
            'owner_gid': product.shopify_gid,
            'namespace': 'custom',
            'key': 'size',
            'value': 'large',
        })
        result = self._call_query('product_metafields', {
            'id': product.shopify_gid, 'first': 10,
        })
        self.assertIn('product', result)
        edges = result['product']['metafields']['edges']
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]['node']['key'], 'size')


class TestSimGiftCard(SimulatorTestCase):
    """Test sim.shopify.gift.card model and handler."""

    def test_gift_card_create(self):
        gc = self.env['sim.shopify.gift.card'].create({
            'config_id': self.sim_config.id,
            'code_masked': '•••• ab12',
            'initial_amount': 50.0,
            'currency_code': 'USD',
        })
        self.assertTrue(gc.shopify_gid)
        self.assertEqual(gc.balance, 50.0)  # Auto-set from initial

    def test_gift_card_graphql_node(self):
        gc = self.env['sim.shopify.gift.card'].create({
            'config_id': self.sim_config.id,
            'code_masked': '•••• zz99',
            'initial_amount': 100.0,
            'balance': 75.0,
        })
        node = gc._to_graphql_node()
        self.assertEqual(node['maskedCode'], '•••• zz99')
        self.assertEqual(node['initialValue']['amount'], '100.0')
        self.assertEqual(node['balance']['amount'], '75.0')

    def test_fetch_gift_cards_handler(self):
        self.env['sim.shopify.gift.card'].create({
            'config_id': self.sim_config.id,
            'code_masked': '•••• test',
            'initial_amount': 25.0,
        })
        result = self._call_query('gift_cards', {'first': 10})
        self.assertIn('giftCards', result)
        self.assertEqual(len(result['giftCards']['edges']), 1)


class TestSimPayout(SimulatorTestCase):
    """Test sim.shopify.payout model and handler."""

    def test_payout_create(self):
        payout = self.env['sim.shopify.payout'].create({
            'config_id': self.sim_config.id,
            'status': 'PAID',
            'amount': 1000.0,
            'gross_amount': 1050.0,
            'fees_amount': 50.0,
        })
        self.assertTrue(payout.shopify_gid)
        self.assertEqual(payout.transaction_count, 0)

    def test_payout_with_transactions(self):
        payout = self.env['sim.shopify.payout'].create({
            'config_id': self.sim_config.id,
            'status': 'PAID',
            'amount': 500.0,
        })
        txn = self.env['sim.shopify.payout.transaction'].create({
            'payout_id': payout.id,
            'transaction_type': 'CHARGE',
            'amount': 500.0,
            'fee': 15.0,
            'net': 485.0,
        })
        self.assertTrue(txn.shopify_gid)
        payout.invalidate_recordset()
        self.assertEqual(payout.transaction_count, 1)

    def test_fetch_payouts_handler(self):
        self.env['sim.shopify.payout'].create({
            'config_id': self.sim_config.id,
            'status': 'PAID',
            'amount': 100.0,
        })
        result = self._call_query('payouts', {'first': 10})
        self.assertIn('shopifyPaymentsAccount', result)
        payouts = result['shopifyPaymentsAccount']['payouts']
        self.assertEqual(len(payouts['edges']), 1)

    def test_fetch_payout_transactions_handler(self):
        payout = self.env['sim.shopify.payout'].create({
            'config_id': self.sim_config.id,
            'status': 'PAID',
            'amount': 100.0,
        })
        self.env['sim.shopify.payout.transaction'].create({
            'payout_id': payout.id,
            'transaction_type': 'CHARGE',
            'amount': 100.0,
        })
        result = self._call_query('payout_transactions', {'first': 10})
        txns = result['shopifyPaymentsAccount']['payoutTransactions']
        self.assertEqual(len(txns['edges']), 1)


class TestSimAbandonedCart(SimulatorTestCase):
    """Test sim.shopify.abandoned.cart model and handler."""

    def test_abandoned_cart_create(self):
        cart = self.env['sim.shopify.abandoned.cart'].create({
            'config_id': self.sim_config.id,
            'customer_email': 'abandon@test.com',
            'customer_name': 'Test Abandoner',
            'total_price': 99.99,
        })
        self.assertTrue(cart.shopify_gid)
        self.assertTrue(cart.checkout_token)
        self.assertIn('recover', cart.recovery_url)
        self.assertEqual(cart.display_name, 'Cart - Test Abandoner')

    def test_abandoned_cart_line_items(self):
        items = json.dumps([
            {'title': 'Widget', 'quantity': 2, 'price': '24.99'},
            {'title': 'Gadget', 'quantity': 1, 'price': '49.99'},
        ])
        cart = self.env['sim.shopify.abandoned.cart'].create({
            'config_id': self.sim_config.id,
            'customer_email': 'items@test.com',
            'line_items_json': items,
            'total_price': 99.97,
        })
        self.assertEqual(cart.line_item_count, 2)

    def test_fetch_abandoned_checkouts_handler(self):
        self.env['sim.shopify.abandoned.cart'].create({
            'config_id': self.sim_config.id,
            'customer_email': 'handler@test.com',
            'total_price': 50.0,
        })
        result = self._call_query('abandoned_checkouts', {'first': 10})
        self.assertIn('abandonedCheckouts', result)
        self.assertEqual(len(result['abandonedCheckouts']['edges']), 1)


class TestSimDiscount(SimulatorTestCase):
    """Test sim.shopify.discount.code model and handlers."""

    def test_discount_create(self):
        dc = self.env['sim.shopify.discount.code'].create({
            'config_id': self.sim_config.id,
            'code': 'SAVE10',
            'discount_type': 'percentage',
            'discount_value': 10.0,
        })
        self.assertTrue(dc.shopify_gid)
        self.assertEqual(dc.title, 'SAVE10')  # Auto-set from code
        self.assertEqual(dc.usage_count, 0)

    @mute_logger('odoo.sql_db')
    def test_discount_unique_code(self):
        self.env['sim.shopify.discount.code'].create({
            'config_id': self.sim_config.id,
            'code': 'UNIQUE1',
        })
        with self.assertRaises(Exception), self.cr.savepoint():
            self.env['sim.shopify.discount.code'].create({
                'config_id': self.sim_config.id,
                'code': 'UNIQUE1',
            })

    def test_discount_graphql_node(self):
        dc = self.env['sim.shopify.discount.code'].create({
            'config_id': self.sim_config.id,
            'code': 'NODE10',
            'discount_type': 'percentage',
            'discount_value': 10.0,
        })
        node = dc._to_graphql_node()
        self.assertEqual(node['id'], dc.shopify_gid)
        cd = node['codeDiscount']
        self.assertEqual(cd['codes']['edges'][0]['node']['code'], 'NODE10')

    def test_fetch_discount_codes_handler(self):
        self.env['sim.shopify.discount.code'].create({
            'config_id': self.sim_config.id,
            'code': 'HANDLER10',
        })
        result = self._call_query('discount_codes', {'first': 10})
        self.assertIn('codeDiscountNodes', result)
        self.assertEqual(len(result['codeDiscountNodes']['edges']), 1)

    def test_discount_basic_create_handler(self):
        result = self._call_mutation('discount_basic_create', {
            'basicCodeDiscount': {
                'code': 'MUT10',
                'title': 'Mutation Discount',
                'customerGets': {
                    'value': {'percentage': 0.1},
                },
            },
        })
        self.assertIn('discountCodeBasicCreate', result)
        node = result['discountCodeBasicCreate']['codeDiscountNode']
        self.assertIn('MUT10', str(node))

    def test_discount_delete_handler(self):
        dc = self.env['sim.shopify.discount.code'].create({
            'config_id': self.sim_config.id,
            'code': 'DELETE_ME',
        })
        result = self._call_mutation('discount_delete', {
            'id': dc.shopify_gid,
        })
        self.assertIn('discountCodeDelete', result)
        self.assertFalse(dc.exists())

    def test_discount_usage(self):
        dc = self.env['sim.shopify.discount.code'].create({
            'config_id': self.sim_config.id,
            'code': 'USAGE_TEST',
        })
        self.env['sim.shopify.discount.usage'].create({
            'discount_code_id': dc.id,
            'order_gid': 'gid://shopify/Order/999',
            'discount_amount': 10.0,
            'order_total': 100.0,
        })
        dc.invalidate_recordset()
        self.assertEqual(dc.usage_count, 1)
