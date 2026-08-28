from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestSetupOrderDefaults(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.store = cls.env['shopify.connector.store'].create({
            'name': 'Orders setup store',
            'shop_domain': 'orders-setup.myshopify.com',
            'company_id': cls.env.company.id,
        })
        cls.settings = cls.env['shopify.connector.store.settings'].create({
            'store_id': cls.store.id,
            'sale_domain_enabled': False,
        })
        cls.term = cls.env['account.payment.term'].create({
            'name': 'Shopify setup test term',
        })
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Shopify setup test pricelist',
            'currency_id': cls.env.company.currency_id.id,
            'company_id': cls.env.company.id,
        })
        cls.fallback = cls.env['res.partner'].create({
            'name': 'Shopify setup fallback customer',
        })
        cls.Readiness = cls.env['shopify.connector.readiness.check']
        cls.admin = new_test_user(
            cls.env,
            login='shopify_order_setup_admin',
            groups=(
                'base.group_user,'
                'shopify_connector_core.group_shopify_connector_admin'
            ),
        )
        cls.Setup = cls.env['shopify.connector.setup.wizard'].with_user(
            cls.admin
        ).with_context(allowed_company_ids=cls.admin.company_ids.ids)

    def test_disabled_orders_marks_defaults_not_applicable(self):
        result = self.Readiness._check_sale_order_defaults(self.store)
        self.assertEqual(result['result'], self.Readiness.RESULT_PASS)
        self.assertTrue(result['not_applicable'])

    def test_enabled_orders_without_required_defaults_fails_readiness(self):
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        result = self.Readiness._check_sale_order_defaults(self.store)
        self.assertEqual(result['tier'], self.Readiness.ESSENTIAL)
        self.assertEqual(result['result'], self.Readiness.RESULT_FAIL)
        self.assertIn('order payment term', result['reason'])
        self.assertIn('order pricelist', result['reason'])
        self.assertIn('fallback customer', result['reason'])

    def test_directions_refuses_orders_without_explicit_term(self):
        with self.assertRaisesRegex(UserError, 'Choose the payment term'):
            self.Setup.save_directions(
                self.store.id, ['sale'], order_payment_term_id=None,
                order_pricelist_id=self.pricelist.id,
                customer_fallback_partner_id=self.fallback.id,
            )
        self.assertFalse(self.settings.sale_domain_enabled)

    def test_directions_refuses_orders_without_explicit_pricelist(self):
        with self.assertRaisesRegex(UserError, 'Choose the active pricelist'):
            self.Setup.save_directions(
                self.store.id, ['sale'], order_pricelist_id=None,
                order_payment_term_id=self.term.id,
                customer_fallback_partner_id=self.fallback.id,
            )
        self.assertFalse(self.settings.sale_domain_enabled)

    def test_legacy_caller_cannot_admit_scheduled_order_import(self):
        self.Setup.save_directions(self.store.id, ['sale'])
        self.assertTrue(self.settings.sale_domain_enabled)
        self.assertFalse(self.settings.order_scheduled_sync_enabled)
        result = self.Readiness._check_sale_order_defaults(self.store)
        self.assertEqual(result['result'], self.Readiness.RESULT_PASS)
        self.assertTrue(result['not_applicable'])

    def test_directions_saves_term_and_readiness_passes(self):
        payload = self.Setup.save_directions(
            self.store.id, ['sale'], order_payment_term_id=self.term.id,
            order_pricelist_id=self.pricelist.id,
            customer_fallback_partner_id=self.fallback.id,
        )
        self.assertTrue(self.settings.sale_domain_enabled)
        self.assertEqual(self.settings.order_payment_term_id, self.term)
        self.assertEqual(self.settings.order_pricelist_id, self.pricelist)
        self.assertEqual(
            payload['order_setup']['payment_term_id'], self.term.id,
        )
        self.assertEqual(
            payload['order_setup']['fallback_partner_id'], self.fallback.id,
        )
        self.assertEqual(
            self.settings.customer_fallback_partner_id, self.fallback,
        )
        result = self.Readiness._check_sale_order_defaults(self.store)
        self.assertEqual(result['result'], self.Readiness.RESULT_PASS)

    def test_payment_term_is_readiness_relevant(self):
        self.settings.sudo().write({'setup_readiness_stale_since': False})
        self.settings.write({'order_payment_term_id': self.term.id})
        self.assertTrue(self.settings.setup_readiness_stale_since)

    def test_fallback_customer_is_readiness_relevant(self):
        self.settings.sudo().write({'setup_readiness_stale_since': False})
        self.settings.write({
            'customer_fallback_partner_id': self.fallback.id,
        })
        self.assertTrue(self.settings.setup_readiness_stale_since)

    def test_pricelist_is_readiness_relevant(self):
        self.settings.sudo().write({'setup_readiness_stale_since': False})
        self.settings.write({'order_pricelist_id': self.pricelist.id})
        self.assertTrue(self.settings.setup_readiness_stale_since)
