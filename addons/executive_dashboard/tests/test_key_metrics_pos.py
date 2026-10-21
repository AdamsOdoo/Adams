import unittest

from odoo.modules.registry import Registry
from odoo.tests import new_test_user, tagged
from odoo.tests.common import get_db_name

from odoo.addons.executive_dashboard.models import dashboard as dashboard_module
from odoo.addons.point_of_sale.tests.common import TestPoSCommon


@tagged('post_install', '-at_install')
class TestKeyMetricsPos(TestPoSCommon):
    """Key metrics: POS sales are a net sales channel (runs only with Point of Sale installed)."""

    @classmethod
    def setUpClass(cls):
        if 'pos.order' not in Registry(get_db_name()):
            raise unittest.SkipTest('Point of Sale is not installed')
        super().setUpClass()

    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.product = self.create_product('Example POS Tile', self.categ_basic, 10.0, 5.0)
        user = new_test_user(self.env, login='ed_pos_admin', company_id=self.env.company.id,
                             company_ids=[self.env.company.id], groups='executive_dashboard.group_admin')
        self.Dashboard = self.env['executive.dashboard'].with_user(user)

    def net_sales(self):
        dashboard_module.cache_clear()
        return self.Dashboard.get_section('key_metrics', 'month')['widgets']['net_sales']

    def test_pos_sessions_are_a_channel(self):
        before = self.net_sales()['total']
        session = self.open_new_session()
        self._create_orders([
            {'pos_order_lines_ui_args': [(self.product, 10)], 'payments': [(self.cash_pm1, 100)],
             'uuid': '00100-010-0001'},
            {'pos_order_lines_ui_args': [(self.product, -2)], 'payments': [(self.cash_pm1, -20)],
             'uuid': '00100-010-0002'},
        ])
        session.post_closing_cash_details(80)
        session.close_session_from_ui()
        self.assertTrue(session.move_id)
        net = self.net_sales()
        pos = next(channel for channel in net['channels'] if channel['id'] == 'pos')
        self.assertAlmostEqual(pos['invoiced'], 100.0)
        self.assertAlmostEqual(pos['refunds'], 20.0)
        self.assertAlmostEqual(pos['net'], 80.0)
        self.assertAlmostEqual(net['total'] - before, 80.0)
        self.assertFalse(any(channel['id'] is False and abs(channel['net']) for channel in net['channels']))
        panel = self.Dashboard.get_drawer('key_metrics.channel', {'period': 'month', 'source_id': 'pos'})
        self.assertEqual(panel['title'], 'Point of Sale')
        self.assertIn(session.move_id.name, [row['label'] for row in panel['rows']])
        action = self.Dashboard._elevated()._action_key_metrics_lines({'period': 'month', 'source_id': 'pos'})
        lines = self.env['account.move.line'].search(action['domain'])
        self.assertAlmostEqual(-sum(lines.mapped('balance')), 80.0)
