# Part of the Shopify Connector (Store 360 slice 1).
#
# The adversarial record-rule suite (handoff §8, extended by the final-tail
# rulings): the aggregate model, the rule model and the drill-down model
# are the same model, so a caller restricted by ANY sale.order /
# sale.order.line / stock.picking / connector rule sees aggregates over
# exactly the records their own native list shows — no count, product
# label, status, timestamp, record id or drill-down may expose a record
# forbidden on the metric's governing model. Plus the runtime source
# guards for the provider files (no sudo, no raw SQL, no mutation in the
# dashboard read path) and the payload leak walk.

import os
import re
from datetime import timedelta

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from .test_order_import_mapping import OrderImportCase

_FORBIDDEN_PAYLOAD_TOKENS = (
    'access_token', 'client_secret', 'shpat_', 'password',
    'payload_snapshot', 'technical_detail',
)


@tagged('post_install', '-at_install')
class TestStore360Security(OrderImportCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.SaleOrder = cls.env['sale.order'].sudo()
        cls._suffix = 0
        # The restricted caller: connector auditor + ordinary salesman
        # (OWN documents only — the native personal record rule).
        cls.restricted = new_test_user(
            cls.env, login='s360_restricted',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor,'
                   'sales_team.group_sale_salesman',
        )
        cls.restricted.tz = 'UTC'
        cls.unrestricted = new_test_user(
            cls.env, login='s360_unrestricted',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor,'
                   'sales_team.group_sale_salesman_all_leads',
        )
        cls.unrestricted.tz = 'UTC'

    @classmethod
    def _imported_order(cls, salesperson=None, amount=100.0,
                        product=None, **binding_extra):
        cls._suffix += 1
        product = product or cls.product
        order = cls.SaleOrder.create({
            'partner_id': cls.fallback_partner.id,
            'company_id': cls.env.company.id,
            'pricelist_id': cls.pricelist.id,
            'payment_term_id': cls.payment_term.id,
            'date_order': fields.Datetime.now() - timedelta(days=1),
            'user_id': salesperson.id if salesperson else False,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'product_uom_qty': 1,
                'price_unit': amount,
                'shopify_line_item_gid':
                    'gid://shopify/LineItem/SEC%d' % cls._suffix,
            })],
        })
        vals = {
            'store_id': cls.store.id,
            'sale_order_id': order.id,
            'shopify_gid': 'gid://shopify/Order/SEC%d' % cls._suffix,
            'shopify_financial_status_snapshot': 'PAID',
            'shopify_fulfillment_status_snapshot': 'UNFULFILLED',
            'shopify_last_evidence_refresh_at': fields.Datetime.now(),
        }
        vals.update(binding_extra)
        cls.env['shopify.connector.order.binding'].sudo().create(vals)
        return order

    def _payload_as(self, user):
        return self.env['shopify.connector.ui.dashboard'].with_user(
            user).get_store_360_data(self.store.id, '30d')

    @staticmethod
    def _walk_strings(node, sink):
        if isinstance(node, dict):
            for key, value in node.items():
                sink.append(str(key))
                TestStore360Security._walk_strings(value, sink)
        elif isinstance(node, (list, tuple)):
            for value in node:
                TestStore360Security._walk_strings(value, sink)
        else:
            sink.append(str(node))

    # ------------------------------------------------------------------
    # restrictive sale.order rule: the personal salesman rule
    # ------------------------------------------------------------------
    def test_restricted_caller_aggregates_only_their_own_rule_population(self):
        mine = self._imported_order(salesperson=self.restricted,
                                    amount=100.0)
        hidden_product = self.env['product.product'].sudo().create({
            'name': 'S360 Hidden Widget', 'type': 'consu',
        })
        self._imported_order(salesperson=self.unrestricted, amount=999.0,
                             product=hidden_product)

        restricted_orders = self.env['sale.order'].with_user(self.restricted)
        visible = restricted_orders.search_count(
            [('shopify_connector_store_id', '=', self.store.id)])

        payload = self._payload_as(self.restricted)
        commercial = payload['commercial']
        self.assertTrue(commercial['available'])
        self.assertEqual(
            commercial['orders_total'], visible,
            'the aggregate must equal the caller\'s own rule-visible '
            'population, never the company-wide one',
        )
        block = commercial['blocks'][0]
        self.assertAlmostEqual(block['sales'], mine.amount_total, places=2)

        # The hidden order's product label must be nowhere in the payload.
        strings = []
        self._walk_strings(payload, strings)
        joined = ' '.join(strings)
        self.assertNotIn('Hidden Widget', joined)
        # And the hidden amount is not recoverable from any monetary total.
        for candidate in commercial['blocks']:
            self.assertLess(candidate['sales'], 999.0)

    def test_restricted_drilldowns_agree_with_their_counts(self):
        self._imported_order(salesperson=self.restricted)
        self._imported_order(salesperson=self.unrestricted)
        payload = self._payload_as(self.restricted)

        def walk(node, path='payload'):
            if isinstance(node, dict):
                if 'count' in node and isinstance(node.get('target'), dict):
                    target = node['target']
                    model = self.env[target['res_model']].with_user(
                        self.restricted)
                    domain = [tuple(t) if isinstance(t, list) else t
                              for t in target['domain']]
                    self.assertEqual(
                        node['count'], model.search_count(domain),
                        '%s: count/drill-down disagreement for the '
                        'restricted caller' % path)
                for key, value in node.items():
                    walk(value, '%s.%s' % (path, key))
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, '%s[%d]' % (path, index))

        walk(payload)

    def test_restricted_line_rule_governs_units_and_products(self):
        self._imported_order(salesperson=self.restricted)
        hidden_product = self.env['product.product'].sudo().create({
            'name': 'S360 Hidden Line Product', 'type': 'consu',
        })
        self._imported_order(salesperson=self.unrestricted,
                             product=hidden_product, amount=500.0)
        payload = self._payload_as(self.restricted)
        Line = self.env['sale.order.line'].with_user(self.restricted)
        visible_units = sum(
            Line.search([
                ('shopify_line_item_gid', '!=', False),
                ('order_id.shopify_connector_store_id', '=', self.store.id),
            ]).mapped('product_uom_qty'))
        self.assertEqual(payload['commercial']['units'], visible_units)
        names = [row['name']
                 for row in payload['commercial']['products']['rows']]
        self.assertNotIn(hidden_product.display_name, names)

    def test_caller_without_sale_access_gets_the_honest_refusal(self):
        auditor_only = new_test_user(
            self.env, login='s360_auditor_only',
            groups='base.group_user,'
                   'shopify_connector_core.group_shopify_connector_auditor',
        )
        self._imported_order(salesperson=self.unrestricted)
        payload = self._payload_as(auditor_only)
        self.assertFalse(payload['commercial']['available'])
        self.assertEqual(payload['commercial']['reason'], 'no_permission')
        self.assertFalse(payload['lifecycle']['available'])
        # Connector health is unaffected.
        self.assertIn('health', payload)
        self.assertIn('state', payload['health'])

    def test_non_connector_caller_is_refused_outright(self):
        outsider = new_test_user(
            self.env, login='s360_outsider', groups='base.group_user',
        )
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self._payload_as(outsider)

    # ------------------------------------------------------------------
    # payload hygiene
    # ------------------------------------------------------------------
    def test_payload_carries_no_secret_or_internal_token(self):
        self._imported_order(salesperson=self.unrestricted)
        payload = self._payload_as(self.unrestricted)
        strings = []
        self._walk_strings(payload, strings)
        joined = ' '.join(strings).lower()
        for token in _FORBIDDEN_PAYLOAD_TOKENS:
            self.assertNotIn(token.lower(), joined)

    # ------------------------------------------------------------------
    # runtime source guards for the provider files (handoff §10.2)
    # ------------------------------------------------------------------
    def _provider_sources(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sale_models = os.path.join(base, 'models')
        paths = [os.path.join(
            sale_models, 'shopify_connector_ui_store360_sale.py')]
        fulfillment = os.path.join(
            os.path.dirname(base), 'shopify_connector_fulfillment',
            'models', 'shopify_connector_ui_store360_fulfillment.py')
        if os.path.exists(fulfillment):
            paths.append(fulfillment)
        return {path: open(path, encoding='utf-8').read() for path in paths}

    @staticmethod
    def _strip_comments(text):
        """Guard the CODE, not the prose: docstrings and comments name the
        forbidden constructs on purpose (they document why they are
        forbidden)."""
        text = re.sub(r'#[^\n]*', '', text)
        text = re.sub(r'"""[\s\S]*?"""', '', text)
        return text

    def test_provider_files_use_no_sudo_and_no_raw_sql(self):
        for path, text in self._provider_sources().items():
            name = os.path.basename(path)
            body = self._strip_comments(text)
            self.assertNotIn('sudo(', body,
                             '%s: the dashboard read path must run as the '
                             'current user' % name)
            self.assertNotIn('cr.execute', body,
                             '%s: no raw SQL in the runtime aggregate '
                             'path' % name)

    def test_provider_files_perform_no_write_or_enqueue_or_transport(self):
        forbidden = ('.create(', '.write(', '.unlink(', 'enqueue',
                     'execute_business', '_send(', 'action_')
        for path, text in self._provider_sources().items():
            name = os.path.basename(path)
            body = self._strip_comments(text)
            for token in forbidden:
                self.assertNotIn(
                    token, body,
                    '%s: the dashboard read path must not contain %r'
                    % (name, token))

    def test_provider_reads_are_orm_grouped_reads_or_counts(self):
        for path, text in self._provider_sources().items():
            body = re.sub(r'#[^\n]*', '', text)
            self.assertTrue(
                ('_read_group(' in body) or ('search_count(' in body),
                '%s: expected ORM grouped reads' % os.path.basename(path))
