from datetime import timedelta

from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged('adams_shopify_manager_dashboard', 'post_install', '-at_install')
class TestManagerDashboardAggregator(TransactionCase):
    """Isolated tests for `shopify.manager.dashboard.get_data`.

    We seed two backends, a handful of orders across two periods, plus a
    scattering of refunds, abandoned carts, and payouts, and assert the
    aggregator returns the expected shape and values.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Backend = cls.env['shopify.backend']
        cls.SaleOrder = cls.env['sale.order']
        cls.OrderBinding = cls.env['shopify.order.binding']
        cls.CustomerBinding = cls.env['shopify.customer.binding']
        cls.Cart = cls.env['shopify.abandoned.cart']
        cls.Refund = cls.env['shopify.refund.binding']
        cls.Payout = cls.env['shopify.payout']
        cls.Partner = cls.env['res.partner']
        cls.Product = cls.env['product.product']
        cls.Dashboard = cls.env['shopify.manager.dashboard']

        cls.backend_a = cls.Backend.create({
            'name': 'Store A',
            'shop_url': 'store-a.myshopify.com',
            'access_token': 'shpat_test_a',
            'company_id': cls.env.company.id,
        })
        cls.backend_b = cls.Backend.create({
            'name': 'Store B',
            'shop_url': 'store-b.myshopify.com',
            'access_token': 'shpat_test_b',
            'company_id': cls.env.company.id,
        })

        cls.product_a = cls.Product.create({'name': 'Widget A', 'list_price': 100.0})
        cls.product_b = cls.Product.create({'name': 'Widget B', 'list_price': 50.0})

        cls.partner_1 = cls.Partner.create({'name': 'Alice'})
        cls.partner_2 = cls.Partner.create({'name': 'Bob'})

        now = fields.Datetime.now()
        cls.in_window = now - timedelta(days=2)
        cls.out_of_window = now - timedelta(days=45)

        cls._create_order(cls.backend_a, cls.partner_1, cls.product_a, qty=2, when=cls.in_window)
        cls._create_order(cls.backend_a, cls.partner_1, cls.product_b, qty=1, when=cls.in_window)
        cls._create_order(cls.backend_a, cls.partner_2, cls.product_a, qty=1, when=cls.in_window)
        cls._create_order(cls.backend_b, cls.partner_2, cls.product_b, qty=3, when=cls.in_window)
        # One out-of-window order that must NOT leak into MTD.
        cls._create_order(cls.backend_a, cls.partner_1, cls.product_a, qty=5, when=cls.out_of_window)

    @classmethod
    def _create_order(cls, backend, partner, product, qty, when):
        order = cls.SaleOrder.create({
            'partner_id': partner.id,
            'date_order': when,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': qty,
                'price_unit': product.list_price,
            })],
        })
        order.action_confirm()
        order.write({'date_order': when})
        cls.OrderBinding.create({
            'backend_id': backend.id,
            'odoo_id': order.id,
            'shopify_id': f'test-{order.id}',
            'shopify_order_name': order.name,
            'sync_status': 'synced',
        })
        return order

    # ------------------------------------------------------------------

    def test_get_data_shape(self):
        data = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        expected_keys = {
            'backends', 'selected_backend_ids', 'period', 'currency',
            'kpis', 'trend', 'top_products', 'top_customers',
            'deliveries', 'abandoned_carts', 'refunds', 'payouts', 'alerts',
        }
        self.assertTrue(expected_keys.issubset(data.keys()))
        self.assertIn('revenue', data['kpis'])
        self.assertIn('value', data['kpis']['revenue'])
        self.assertIn('delta_pct', data['kpis']['revenue'])

    def test_backend_filter_isolates_data(self):
        data_a = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        data_b = self.Dashboard.get_data(backend_ids=[self.backend_b.id], period='mtd')
        self.assertEqual(data_a['kpis']['orders']['value'], 3)
        self.assertEqual(data_b['kpis']['orders']['value'], 1)

    def test_revenue_excludes_out_of_window(self):
        """The MTD window must exclude the 45-days-ago order on backend A."""
        data = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        # 3 orders x (2*100 + 50 + 100) = 350 for backend_a in window.
        self.assertAlmostEqual(data['kpis']['revenue']['value'], 350.0, places=2)

    def test_top_products_ordering(self):
        data = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        products = data['top_products']
        self.assertGreater(len(products), 0)
        revenues = [p['revenue'] for p in products]
        self.assertEqual(revenues, sorted(revenues, reverse=True))
        # Widget A has higher revenue (2*100 + 100 = 300) than Widget B (50).
        self.assertEqual(products[0]['name'].lower().count('widget a'), 1)

    def test_top_customers_ordering(self):
        data = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        customers = data['top_customers']
        self.assertGreater(len(customers), 0)
        revenues = [c['revenue'] for c in customers]
        self.assertEqual(revenues, sorted(revenues, reverse=True))

    def test_empty_backend_selection_returns_all(self):
        data = self.Dashboard.get_data(backend_ids=[], period='mtd')
        self.assertEqual(data['kpis']['orders']['value'], 4)

    def test_refunds_and_carts_isolation(self):
        """Refund and abandoned-cart sums are scoped by backend_ids and dates."""
        order_binding_a = self.OrderBinding.search(
            [('backend_id', '=', self.backend_a.id)], limit=1,
        )
        # Seed a refund and an abandoned cart on backend A.
        move = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_1.id,
        })
        self.Refund.create({
            'backend_id': self.backend_a.id,
            'shopify_id': 'r-1',
            'refund_amount': 50.0,
            'currency_code': 'USD',
            'order_binding_id': order_binding_a.id,
            'odoo_id': move.id,
            'sync_status': 'synced',
        })
        self.Cart.create({
            'backend_id': self.backend_a.id,
            'shopify_id': 'c-1',
            'abandoned_at': fields.Datetime.now() - timedelta(days=1),
            'total_price': 120.0,
            'recovered': False,
        })
        data = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        self.assertGreaterEqual(data['refunds']['count'], 1)
        self.assertGreaterEqual(data['refunds']['amount'], 50.0)
        self.assertGreaterEqual(data['abandoned_carts']['count'], 1)
        self.assertGreaterEqual(data['abandoned_carts']['recoverable_value'], 120.0)

        # Backend B must not see backend A's refund / cart.
        data_b = self.Dashboard.get_data(backend_ids=[self.backend_b.id], period='mtd')
        self.assertEqual(data_b['refunds']['amount'], 0.0)
        self.assertEqual(data_b['abandoned_carts']['count'], 0)

    def test_payouts_status_breakdown(self):
        self.Payout.create({
            'backend_id': self.backend_a.id,
            'shopify_id': 'p-1',
            'status': 'scheduled',
            'amount': 500.0,
            'payout_date': fields.Date.today() + timedelta(days=3),
        })
        self.Payout.create({
            'backend_id': self.backend_a.id,
            'shopify_id': 'p-2',
            'status': 'paid',
            'amount': 200.0,
            'payout_date': fields.Date.today() - timedelta(days=1),
        })
        data = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        self.assertEqual(data['payouts']['scheduled']['count'], 1)
        self.assertEqual(data['payouts']['scheduled']['amount'], 500.0)
        self.assertEqual(data['payouts']['paid_mtd']['count'], 1)
        self.assertEqual(data['payouts']['paid_mtd']['amount'], 200.0)

    def test_delta_vs_prior_period(self):
        data = self.Dashboard.get_data(backend_ids=[self.backend_a.id], period='mtd')
        # When prior = 0, fallback delta = 100.0 for non-zero current.
        self.assertGreaterEqual(data['kpis']['revenue']['delta_pct'], 0)

    def test_new_backend_onchange_does_not_raise(self):
        """Regression: reading a computed count on a NewId shopify.backend
        must not raise "Compute method failed to assign ..." — the bug that
        broke the Create Store form before we default-initialised the
        bind-count fields."""
        new_rec = self.Backend.new({'name': 'Draft Store'})
        self.assertEqual(new_rec.product_bind_count, 0)
        self.assertEqual(new_rec.order_bind_count, 0)
        self.assertEqual(new_rec.sync_health_pct, 100)
