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

    def test_enabled_orders_without_term_fails_readiness(self):
        self.settings.write({
            'sale_domain_enabled': True,
            'order_scheduled_sync_enabled': True,
        })
        result = self.Readiness._check_sale_order_defaults(self.store)
        self.assertEqual(result['tier'], self.Readiness.ESSENTIAL)
        self.assertEqual(result['result'], self.Readiness.RESULT_FAIL)
        self.assertIn('order payment term', result['reason'])

    def test_directions_refuses_orders_without_explicit_term(self):
        with self.assertRaisesRegex(UserError, 'Choose the payment term'):
            self.Setup.save_directions(
                self.store.id, ['sale'], order_payment_term_id=None,
            )
        self.assertFalse(self.settings.sale_domain_enabled)

    def test_legacy_caller_cannot_bypass_backend_readiness(self):
        self.Setup.save_directions(self.store.id, ['sale'])
        result = self.Readiness._check_sale_order_defaults(self.store)
        self.assertEqual(result['result'], self.Readiness.RESULT_FAIL)

    def test_directions_saves_term_and_readiness_passes(self):
        payload = self.Setup.save_directions(
            self.store.id, ['sale'], order_payment_term_id=self.term.id,
        )
        self.assertTrue(self.settings.sale_domain_enabled)
        self.assertEqual(self.settings.order_payment_term_id, self.term)
        self.assertEqual(
            payload['order_setup']['payment_term_id'], self.term.id,
        )
        result = self.Readiness._check_sale_order_defaults(self.store)
        self.assertEqual(result['result'], self.Readiness.RESULT_PASS)

    def test_payment_term_is_readiness_relevant(self):
        self.settings.sudo().write({'setup_readiness_stale_since': False})
        self.settings.write({'order_payment_term_id': self.term.id})
        self.assertTrue(self.settings.setup_readiness_stale_since)
