# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError
from odoo.tests.common import TransactionCase

from ..hooks import _seed_feature_flag_defaults
from ..sync.gift_card_sync import GiftCardSync
from ..sync.metafield_sync import MetafieldSync
from .common import ShopifyAccountingMixin


class TestFeatureFlagMechanism(TransactionCase):
    """Goal 2B feature-flag mechanism, visible skips, and upgrade defaults."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Flag Store',
            'shop_url': 'flags.myshopify.com',
            'access_token': 'shpat_flags',
            'company_id': self.env.company.id,
            'state': 'connected',
        })

    def _latest_log(self, entity):
        return self.env['shopify.sync.log'].search([
            ('backend_id', '=', self.backend.id),
            ('entity', '=', entity),
        ], order='id desc', limit=1)

    def test_new_defaults_preserve_current_optional_behavior(self):
        self.assertTrue(self.backend.enable_promoters)
        self.assertTrue(self.backend.enable_payout_import)
        self.assertTrue(self.backend.enable_gift_cards)
        self.assertFalse(self.backend.enable_metafields)
        self.assertFalse(self.backend.enable_customer_tags)

    def test_admin_only_non_admin_cannot_flip_flags(self):
        group_user = self.env.ref('shopify_connector_pro.group_shopify_user')
        user = self.env['res.users'].create({
            'name': 'Shopify Operator',
            'login': 'shopify_operator_goal2b',
            'email': 'operator.goal2b@example.com',
            'groups_id': [(6, 0, [group_user.id])],
        })
        with self.assertRaises(AccessError):
            self.backend.with_user(user).write({'enable_payout_import': False})

    def test_upgrade_seed_preserves_reused_fields_and_new_defaults(self):
        self.backend.write({
            'reverse_sync_refund': True,
            'external_fulfillment_handling': 'auto_validate',
            'import_currency_mode': 'presentment',
        })
        self.env.cr.execute("""
            UPDATE shopify_backend
               SET enable_promoters = NULL,
                   enable_payout_import = NULL,
                   enable_gift_cards = NULL,
                   enable_metafields = NULL,
                   enable_customer_tags = NULL
             WHERE id = %s
        """, [self.backend.id])
        self.backend.invalidate_recordset()

        _seed_feature_flag_defaults(self.env)
        self.backend.invalidate_recordset()

        self.assertTrue(self.backend.reverse_sync_refund)
        self.assertEqual(self.backend.external_fulfillment_handling, 'auto_validate')
        self.assertEqual(self.backend.import_currency_mode, 'presentment')
        self.assertTrue(self.backend.enable_promoters)
        self.assertTrue(self.backend.enable_payout_import)
        self.assertTrue(self.backend.enable_gift_cards)
        self.assertFalse(self.backend.enable_metafields)
        self.assertFalse(self.backend.enable_customer_tags)

    def test_promoter_cron_off_logs_visible_skip(self):
        self.backend.enable_promoters = False
        with patch('odoo.addons.shopify_connector_pro.sync.discount_sync.DiscountSync.export_discounts') as sync:
            self.env['shopify.backend']._cron_sync_discounts()
        sync.assert_not_called()
        log = self._latest_log('discount')
        self.assertTrue(log)
        self.assertEqual(log.skipped_count, 1)
        self.assertIn('disabled', log.error_details)

    def test_collections_reused_toggle_off_logs_visible_skip(self):
        self.backend.auto_sync_collections = False
        with patch('odoo.addons.shopify_connector_pro.sync.collection_sync.CollectionSync.import_collections') as sync:
            self.env['shopify.backend']._cron_sync_collections()
        sync.assert_not_called()
        log = self._latest_log('collection')
        self.assertTrue(log)
        self.assertEqual(log.skipped_count, 1)

    def test_payout_cron_off_logs_visible_skip(self):
        self.backend.enable_payout_import = False
        with patch('odoo.addons.shopify_connector_pro.sync.payout_sync.PayoutSync.import_payouts') as sync:
            self.env['shopify.backend']._cron_import_payouts()
        sync.assert_not_called()
        log = self._latest_log('payout')
        self.assertTrue(log)
        self.assertEqual(log.skipped_count, 1)

    def test_abandoned_cart_reused_toggle_off_logs_visible_skip(self):
        self.backend.auto_sync_abandoned_carts = False
        with patch('odoo.addons.shopify_connector_pro.sync.abandoned_cart_sync.AbandonedCartSync.import_abandoned_carts') as sync:
            self.env['shopify.backend']._cron_import_abandoned_carts()
        sync.assert_not_called()
        log = self._latest_log('abandoned_cart')
        self.assertTrue(log)
        self.assertEqual(log.skipped_count, 1)

    def test_gift_card_off_logs_skip_before_api_client(self):
        self.backend.enable_gift_cards = False
        with patch.object(type(self.backend), '_make_api_client', return_value=MagicMock()) as client:
            result = GiftCardSync(self.env, self.backend).import_gift_cards()
        client.assert_not_called()
        self.assertEqual(result, (0, 0, 1))
        log = self._latest_log('gift_card')
        self.assertTrue(log)
        self.assertEqual(log.skipped_count, 1)

    def test_metafield_off_logs_skip_before_api_client(self):
        product = self.env['product.product'].create({'name': 'Flag Product'})
        binding = self.env['shopify.product.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': product.id,
            'shopify_id': 'gid://shopify/Product/1',
        })
        with patch.object(type(self.backend), '_make_api_client', return_value=MagicMock()) as client:
            MetafieldSync(self.env, self.backend).import_product_metafields(binding)
        client.assert_not_called()
        log = self._latest_log('metafield')
        self.assertTrue(log)
        self.assertEqual(log.skipped_count, 1)

    def test_menu_actions_filter_disabled_backend_records(self):
        action_expectations = {
            'shopify_connector_pro.shopify_discount_code_action': 'enable_promoters',
            'shopify_connector_pro.shopify_collection_binding_action': 'auto_sync_collections',
            'shopify_connector_pro.shopify_abandoned_cart_action': 'auto_sync_abandoned_carts',
            'shopify_connector_pro.shopify_payout_action': 'enable_payout_import',
            'shopify_connector_pro.shopify_gift_card_action': 'enable_gift_cards',
            'shopify_connector_pro.shopify_metafield_action': 'enable_metafields',
            'shopify_connector_pro.shopify_customer_tag_action': 'enable_customer_tags',
        }
        for xmlid, field_name in action_expectations.items():
            action = self.env.ref(xmlid)
            self.assertIn(field_name, action.domain or '')


class TestFeatureFlagReverseRefundMoneyPath(ShopifyAccountingMixin, TransactionCase):
    """AUD-029: reverse refund push OFF must not call refundCreate."""

    def setUp(self):
        super().setUp()
        self.backend = self.env['shopify.backend'].create({
            'name': 'Refund Flag Store',
            'shop_url': 'refund-flag.myshopify.com',
            'access_token': 'shpat_refund_flags',
            'company_id': self.env.company.id,
            'warehouse_id': self.env['stock.warehouse'].search(
                [('company_id', '=', self.env.company.id)], limit=1,
            ).id,
            'state': 'connected',
            'reverse_sync_refund': False,
        })
        self.partner = self._create_accounting_partner(
            'Refund Flag Customer', email='refund.flag@example.com',
        )
        self.product = self.env['product.product'].create({
            'name': 'Refund Flag Product',
            'list_price': 40.0,
        })
        self._set_product_income_account(self.product)

    def test_aud_029_reverse_refund_off_does_not_call_refund_create(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'sales_channel': 'shopify',
            'shopify_reverse_sync': True,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 1,
                'price_unit': 40.0,
            })],
        })
        order.action_confirm()
        self.env['shopify.order.binding'].create({
            'backend_id': self.backend.id,
            'odoo_id': order.id,
            'shopify_id': 'gid://shopify/Order/2900',
            'shopify_order_name': '#AUD029',
            'shopify_financial_status': 'paid',
            'sync_status': 'synced',
        })
        invoice = order._create_invoices()
        invoice.with_context(shopify_no_auto_export=True).action_post()
        credit_note = invoice._reverse_moves()

        with patch.object(type(self.backend), '_make_api_client', return_value=MagicMock()) as client:
            credit_note.action_post()

        client.assert_not_called()
