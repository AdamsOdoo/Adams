# Part of the Shopify Connector (Store 360 slice 1).
#
# Aggregate correctness of the commercial, trend, product, bridge and
# lifecycle sections: exact arithmetic, exclusion rules, truthful deltas,
# per-currency partitioning, timezone-bounded windows, the goods-subtotal
# share basis, and the load-bearing invariant that EVERY displayed count
# equals the population of its own server-built drill-down domain on the
# SAME model as the SAME user.

from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_order_import_mapping import OrderImportCase


@tagged('post_install', '-at_install')
class TestStore360Aggregates(OrderImportCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.viewer = new_test_user(
            cls.env, login='s360_viewer',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor,'
                   'sales_team.group_sale_salesman_all_leads',
        )
        cls.viewer.tz = 'UTC'
        cls.Dashboard = cls.env[
            'shopify.connector.ui.dashboard'].with_user(cls.viewer)
        cls.SaleOrder = cls.env['sale.order'].sudo()
        cls._suffix = 0

    # ------------------------------------------------------------------
    # fixtures
    # ------------------------------------------------------------------
    @classmethod
    def _imported_order(cls, days_ago=1, amount=100.0, qty=1,
                        store=None, **binding_extra):
        cls._suffix += 1
        order = cls.SaleOrder.create({
            'partner_id': cls.fallback_partner.id,
            'company_id': cls.env.company.id,
            'pricelist_id': cls.pricelist.id,
            'payment_term_id': cls.payment_term.id,
            'date_order': fields.Datetime.now() - timedelta(days=days_ago),
            'user_id': False,
            'order_line': [(0, 0, {
                'product_id': cls.product.id,
                'product_uom_qty': qty,
                'price_unit': amount,
                'shopify_line_item_gid':
                    'gid://shopify/LineItem/AGG%d' % cls._suffix,
            })],
        })
        vals = {
            'store_id': (store or cls.store).id,
            'sale_order_id': order.id,
            'shopify_gid': 'gid://shopify/Order/AGG%d' % cls._suffix,
            'shopify_financial_status_snapshot': 'PAID',
            'shopify_fulfillment_status_snapshot': 'UNFULFILLED',
            'shopify_last_evidence_refresh_at': fields.Datetime.now(),
        }
        vals.update(binding_extra)
        cls.env['shopify.connector.order.binding'].sudo().create(vals)
        return order

    def _payload_360(self, store_id=None, period='30d'):
        return self.Dashboard.get_store_360_data(
            store_id if store_id is not None else self.store.id, period,
        )

    def _assert_every_count_matches_its_drilldown(self, node, path='payload'):
        """Walk the payload: wherever a dict carries both `count` and
        `target`, the count must equal the target-domain population on the
        target model AS THE SAME USER."""
        if isinstance(node, dict):
            if 'count' in node and isinstance(node.get('target'), dict):
                target = node['target']
                model = self.env[target['res_model']].with_user(self.viewer)
                domain = [tuple(term) if isinstance(term, list) else term
                          for term in target['domain']]
                self.assertEqual(
                    node['count'], model.search_count(domain),
                    '%s: displayed count and drill-down population must '
                    'agree (%s)' % (path, target['res_model']),
                )
            for key, value in node.items():
                self._assert_every_count_matches_its_drilldown(
                    value, '%s.%s' % (path, key))
        elif isinstance(node, list):
            for index, value in enumerate(node):
                self._assert_every_count_matches_its_drilldown(
                    value, '%s[%d]' % (path, index))

    # ------------------------------------------------------------------
    # C1–C4 and the exclusion rules
    # ------------------------------------------------------------------
    def test_commercial_arithmetic_and_exclusions(self):
        kept_a = self._imported_order(days_ago=2, amount=100.0, qty=2)
        kept_b = self._imported_order(days_ago=3, amount=50.0, qty=1)
        # Disclosed separately, but excluded from every reconciled value,
        # order, unit, trend, and product aggregate.
        review = self._imported_order(
            days_ago=2, amount=777.0, qty=7, status='review',
        )
        # Excluded: Odoo-cancelled.
        cancelled = self._imported_order(days_ago=2, amount=999.0)
        cancelled.write({'state': 'cancel'})
        # Excluded: Shopify-cancelled after import.
        self._imported_order(
            days_ago=2, amount=999.0,
            shopify_cancelled_at=fields.Datetime.now(),
        )
        # Excluded: quarantined binding.
        self._imported_order(
            days_ago=2, amount=999.0, sec3_scope_quarantined=True,
        )
        # Excluded: not a Shopify order at all.
        self.SaleOrder.create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'order_line': [(0, 0, {
                'product_id': self.product.id,
                'product_uom_qty': 5,
                'price_unit': 999.0,
            })],
        })
        # Out of window.
        self._imported_order(days_ago=200, amount=999.0)

        payload = self._payload_360()
        commercial = payload['commercial']
        self.assertTrue(commercial['available'])
        self.assertEqual(len(commercial['blocks']), 1)
        block = commercial['blocks'][0]
        expected_sales = kept_a.amount_total + kept_b.amount_total
        self.assertAlmostEqual(block['sales'], expected_sales, places=2)
        self.assertAlmostEqual(block['gross'], expected_sales, places=2)
        self.assertAlmostEqual(block['net'], expected_sales, places=2)
        self.assertEqual(block['refunds'], 0.0)
        self.assertEqual(block['orders'], 2)
        self.assertAlmostEqual(
            block['aov'], expected_sales / 2.0, places=2)
        self.assertEqual(commercial['units'], 3)
        self.assertEqual(commercial['awaiting_review']['count'], 1)
        review_block = commercial['awaiting_review']['blocks'][0]
        self.assertEqual(review_block['count'], 1)
        self.assertAlmostEqual(
            review_block['value'], review.amount_total, places=2,
        )

        # The orders drill-down IS the aggregate population.
        model = self.env['sale.order'].with_user(self.viewer)
        domain = [tuple(t) for t in commercial['orders_target']['domain']]
        self.assertEqual(model.search_count(domain), 2)
        self.assertNotIn(review, model.search(domain))
        currency_domain = [tuple(t) for t in block['orders_target']['domain']]
        currency_orders = model.search(currency_domain)
        self.assertEqual(currency_orders, kept_a | kept_b)
        self.assertAlmostEqual(
            sum(currency_orders.mapped('amount_total')),
            block['gross'], places=2,
        )
        review_domain = [
            tuple(t) for t in commercial['awaiting_review']['target']['domain']
        ]
        self.assertEqual(model.search(review_domain), review)
        review_currency_domain = [
            tuple(t) for t in review_block['target']['domain']
        ]
        review_currency_orders = model.search(review_currency_domain)
        self.assertEqual(review_currency_orders, review)
        self.assertAlmostEqual(
            sum(review_currency_orders.mapped('amount_total')),
            review_block['value'], places=2,
        )

    def test_sales_dashboard_is_sales_only_and_keeps_review_separate(self):
        kept = self._imported_order(days_ago=1, amount=125.0, qty=2)
        review = self._imported_order(
            days_ago=1, amount=500.0, qty=5, status='review',
        )
        payload = self.Dashboard.get_sales_dashboard_data(
            self.store.id, '30d'
        )
        self.assertIn('commercial', payload)
        self.assertNotIn('health', payload)
        self.assertNotIn('flows', payload)
        commercial = payload['commercial']
        self.assertEqual(commercial['orders_total'], 1)
        self.assertEqual(commercial['awaiting_review']['count'], 1)
        self.assertEqual(len(commercial['awaiting_review']['blocks']), 1)
        self.assertAlmostEqual(
            commercial['awaiting_review']['blocks'][0]['value'],
            review.amount_total, places=2,
        )
        block = commercial['blocks'][0]
        self.assertAlmostEqual(block['gross'], kept.amount_total, places=2)
        self.assertAlmostEqual(block['net'], kept.amount_total, places=2)
        self.assertEqual(block['refunds'], 0.0)
        self.assertIn('excluded', commercial['refund_scope_note'].lower())

    def test_kpis_equal_drilldowns_with_review_quarantine_and_cancel(self):
        """A3: every commercial KPI reconciles to its exact population."""
        kept = self._imported_order(days_ago=1, amount=125.0, qty=2)
        review = self._imported_order(
            days_ago=1, amount=500.0, qty=5, status='review',
        )
        quarantined = self._imported_order(
            days_ago=1, amount=1000.0, qty=10,
            sec3_scope_quarantined=True,
        )
        cancelled = self._imported_order(days_ago=1, amount=2000.0, qty=20)
        cancelled.write({'state': 'cancel'})

        commercial = self._payload_360()['commercial']
        self.assertEqual(commercial['orders_total'], 1)
        self.assertEqual(commercial['units'], 2)
        self.assertEqual(commercial['awaiting_review']['count'], 1)
        review_block = commercial['awaiting_review']['blocks'][0]
        self.assertAlmostEqual(
            review_block['value'], review.amount_total, places=2,
        )
        self.assertEqual(len(commercial['blocks']), 1)
        block = commercial['blocks'][0]
        self.assertAlmostEqual(block['sales'], kept.amount_total, places=2)

        Order = self.env['sale.order'].with_user(self.viewer)
        Line = self.env['sale.order.line'].with_user(self.viewer)
        order_domain = [
            tuple(term) for term in commercial['orders_target']['domain']
        ]
        line_domain = [
            tuple(term) for term in commercial['units_target']['domain']
        ]
        review_domain = [
            tuple(term)
            for term in commercial['awaiting_review']['target']['domain']
        ]
        reconciled = Order.search(order_domain)
        self.assertEqual(reconciled, kept)
        self.assertAlmostEqual(
            sum(reconciled.mapped('amount_total')), block['sales'], places=2,
        )
        self.assertAlmostEqual(
            sum(Line.search(line_domain).mapped('product_uom_qty')),
            commercial['units'], places=2,
        )
        self.assertEqual(Order.search(review_domain), review)
        review_currency_domain = [
            tuple(term) for term in review_block['target']['domain']
        ]
        review_population = Order.search(review_currency_domain)
        self.assertEqual(review_population, review)
        self.assertAlmostEqual(
            sum(review_population.mapped('amount_total')),
            review_block['value'], places=2,
        )
        self.assertNotIn(quarantined, reconciled)
        self.assertNotIn(cancelled, reconciled)

    def test_zero_orders_never_divides(self):
        payload = self._payload_360()
        self.assertTrue(payload['commercial']['available'])
        self.assertEqual(payload['commercial']['blocks'], [])
        self.assertEqual(payload['commercial']['orders_total'], 0)

    def test_previous_period_zero_gives_no_percentage_basis(self):
        self._imported_order(days_ago=1, amount=100.0)
        payload = self._payload_360(period='7d')
        block = payload['commercial']['blocks'][0]
        self.assertEqual(block['previous']['orders'], 0)
        self.assertEqual(block['previous']['sales'], 0.0)
        self.assertFalse(block['previous']['aov'])

    def test_previous_window_is_the_shifted_equivalent(self):
        self._imported_order(days_ago=1, amount=100.0)          # current 7d
        prior = self._imported_order(days_ago=10, amount=40.0)  # previous 7d
        payload = self._payload_360(period='7d')
        block = payload['commercial']['blocks'][0]
        self.assertEqual(block['orders'], 1)
        self.assertEqual(block['previous']['orders'], 1)
        self.assertAlmostEqual(
            block['previous']['sales'], prior.amount_total, places=2)

    # ------------------------------------------------------------------
    # currencies are never combined
    # ------------------------------------------------------------------
    def test_mixed_currencies_are_partitioned_never_combined(self):
        self._imported_order(days_ago=1, amount=100.0)
        other_currency = self.env.ref('base.GBP').sudo()
        other_currency.active = True
        # currency_id follows the pricelist on sale.order, so the second
        # currency arrives the way production would produce it.
        gbp_pricelist = self.env['product.pricelist'].sudo().create({
            'name': 'S360 GBP', 'currency_id': other_currency.id,
        })
        other = self._imported_order(days_ago=1, amount=70.0)
        other.write({'pricelist_id': gbp_pricelist.id,
                     'currency_id': other_currency.id})
        payload = self._payload_360()
        blocks = payload['commercial']['blocks']
        self.assertEqual(len(blocks), 2)
        names = {block['currency']['name'] for block in blocks}
        self.assertEqual(len(names), 2)
        total_orders = sum(block['orders'] for block in blocks)
        self.assertEqual(payload['commercial']['orders_total'], total_orders)
        # No key anywhere claims a combined monetary total.
        self.assertNotIn('combined_total', payload['commercial'])

    # ------------------------------------------------------------------
    # trend and top products
    # ------------------------------------------------------------------
    def test_trend_buckets_cover_the_window_and_sum_to_c1(self):
        self._imported_order(days_ago=1, amount=100.0)
        self._imported_order(days_ago=1, amount=30.0)
        self._imported_order(days_ago=4, amount=70.0)
        payload = self._payload_360(period='7d')
        trend = payload['commercial']['trend']
        self.assertTrue(trend['available'])
        self.assertEqual(len(trend['buckets']), 7)
        block = payload['commercial']['blocks'][0]
        self.assertAlmostEqual(
            sum(bucket['value'] for bucket in trend['buckets']),
            block['sales'], places=2,
        )

    def test_top_products_share_uses_the_goods_subtotal_basis(self):
        self._imported_order(days_ago=1, amount=100.0, qty=1)
        second_product = self.env['product.product'].sudo().create({
            'name': 'S360 Second Product', 'type': 'consu',
            'list_price': 10.0,
        })
        self._suffix += 1
        order = self.SaleOrder.create({
            'partner_id': self.fallback_partner.id,
            'company_id': self.env.company.id,
            'pricelist_id': self.pricelist.id,
            'payment_term_id': self.payment_term.id,
            'date_order': fields.Datetime.now() - timedelta(days=1),
            'order_line': [(0, 0, {
                'product_id': second_product.id,
                'product_uom_qty': 3,
                'price_unit': 100.0,
                'shopify_line_item_gid':
                    'gid://shopify/LineItem/AGG%d' % self._suffix,
            })],
        })
        self.env['shopify.connector.order.binding'].sudo().create({
            'store_id': self.store.id,
            'sale_order_id': order.id,
            'shopify_gid': 'gid://shopify/Order/AGG%d' % self._suffix,
        })
        payload = self._payload_360()
        products = payload['commercial']['products']
        self.assertTrue(products['available'])
        self.assertLessEqual(len(products['rows']), 5)
        top = products['rows'][0]
        self.assertEqual(top['name'], second_product.display_name)
        # Share basis = untaxed goods subtotal over ALL eligible goods
        # lines, never the tax/shipping-bearing headline (correction §6C).
        self.assertAlmostEqual(
            products['goods_subtotal_total'], 400.0, places=2)
        self.assertAlmostEqual(top['share'], 300.0 / 400.0, places=4)
        # Shares can never exceed 1 in total.
        self.assertLessEqual(
            sum(row['share'] for row in products['rows']), 1.0 + 1e-6)

    # ------------------------------------------------------------------
    # lifecycle strips
    # ------------------------------------------------------------------
    def test_lifecycle_buckets_count_exactly_and_match_their_drilldowns(self):
        self._imported_order(days_ago=1)  # PAID / UNFULFILLED
        self._imported_order(
            days_ago=1,
            shopify_financial_status_snapshot='AUTHORIZED',
        )
        self._imported_order(
            days_ago=1,
            shopify_financial_status_snapshot='PENDING',
        )
        self._imported_order(
            days_ago=1, is_cod=True,
            shopify_financial_status_snapshot='PENDING',
            manual_gateway_approval_state='pending',
            cod_commercial_state='quotation',
            cod_collection_state='nothing_collected',
        )
        self._imported_order(
            days_ago=1, status='review',
            shopify_financial_status_snapshot='PARTIALLY_PAID',
        )
        self._imported_order(
            days_ago=1,
            shopify_fulfillment_status_snapshot='FULFILLED',
        )
        payload = self._payload_360()
        lifecycle = payload['lifecycle']
        self.assertTrue(lifecycle['available'])
        buckets = {b['id']: b['count']
                   for b in lifecycle['payment']['buckets']}
        self.assertEqual(buckets['paid'], 2)
        self.assertEqual(buckets['authorized'], 1)
        self.assertEqual(buckets['pending_non_cod'], 1)
        self.assertEqual(buckets['cod'], 1)
        self.assertEqual(buckets['review'], 1)
        # The unknown value belongs to the separately-disclosed review order;
        # it cannot leak back into the reconciled remainder.
        self.assertEqual(lifecycle['payment']['other'], 0)

        cod = lifecycle['cod']
        self.assertEqual(cod['total'], 1)
        self.assertEqual(cod['approval_pending'], 1)
        self.assertEqual(cod['quotation'], 1)

        progress = {b['id']: b['count']
                    for b in lifecycle['fulfillment_progress']['buckets']}
        self.assertEqual(progress['fulfilled'], 1)
        self.assertEqual(progress['unfulfilled'], 4)
        self.assertEqual(progress['not_observed'], 0)

        self.assertTrue(lifecycle['oldest_paid_unfulfilled'])
        self._assert_every_count_matches_its_drilldown(lifecycle)

    def test_unknown_status_values_fail_closed_into_not_observed(self):
        self._imported_order(
            days_ago=1,
            shopify_fulfillment_status_snapshot='SOME_FUTURE_VALUE',
        )
        payload = self._payload_360()
        progress = {b['id']: b
                    for b in payload['lifecycle']
                    ['fulfillment_progress']['buckets']}
        self.assertEqual(progress['not_observed']['count'], 1)
        self._assert_every_count_matches_its_drilldown(
            payload['lifecycle']['fulfillment_progress'])

    def test_multi_fulfillment_orders_count_once_at_order_grain(self):
        order = self._imported_order(
            days_ago=1,
            shopify_fulfillment_status_snapshot='PARTIALLY_FULFILLED',
        )
        self.assertTrue(order)
        payload = self._payload_360()
        progress = {b['id']: b['count']
                    for b in payload['lifecycle']
                    ['fulfillment_progress']['buckets']}
        # The order-level Shopify rollup is the counted value: one order,
        # one bucket, regardless of how many fulfillments compose it.
        self.assertEqual(progress['partially_fulfilled'], 1)
        self.assertEqual(payload['commercial']['orders_total'], 1)

    # ------------------------------------------------------------------
    # bridge and store filter validation
    # ------------------------------------------------------------------
    def test_bridge_reports_processing_while_a_scan_is_live(self):
        self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'order_import_sync',
            'state': 'queued',
            'payload_hash': 'bridge-g2',
            'expected_connection_generation':
                self.store.connection_generation,
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': 'gid://shopify/Order/BridgeG2',
        })
        payload = self._payload_360()
        bridge = payload['bridge']
        self.assertTrue(bridge['available'])
        self.assertEqual(bridge['g2'], 1)
        self.assertEqual(bridge['state'], 'processing')

    def test_bridge_incomplete_on_failures_drives_the_critical_band(self):
        self.env['shopify.connector.job'].sudo().create({
            'store_id': self.store.id,
            'job_source': 'reconciliation',
            'job_type': 'order_import_sync',
            'state': 'failed_final',
            'payload_hash': 'bridge-g3',
            'finished_at': fields.Datetime.now(),
            'res_model': 'shopify.connector.store',
            'res_id': self.store.id,
            'shopify_target_gid': 'gid://shopify/Order/BridgeG3',
        })
        payload = self._payload_360()
        self.assertEqual(payload['bridge']['state'], 'incomplete')
        self.assertTrue(payload['critical']['active'])

    def test_disabled_order_import_routes_attention_to_settings(self):
        self.settings.sudo().write({
            'sale_domain_enabled': False,
            'sale_order_last_import_checkpoint_at': fields.Datetime.now(),
        })
        payload = self._payload_360()
        bridge = payload['bridge']
        self.assertEqual(bridge['state'], 'incomplete')
        self.assertEqual(bridge['g3'], 0)
        self.assertIn('disabled', bridge['critical_text'])
        self.assertEqual(
            bridge['critical_target']['res_model'],
            'shopify.connector.store.settings',
        )
        self.assertEqual(
            bridge['critical_target']['domain'],
            [['store_id', '=', self.store.id]],
        )

    def test_unvalidated_filters_are_refused(self):
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            self._payload_360(period='13months')
        with self.assertRaises(UserError):
            self._payload_360(store_id=999999)
