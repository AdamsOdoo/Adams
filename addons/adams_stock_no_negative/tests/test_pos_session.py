from odoo.tests import tagged

from odoo.addons.point_of_sale.tests.common import TestPoSCommon

from .common import skip_unless_installed


@tagged("post_install", "-at_install")
class TestNoNegativeStockPosSession(TestPoSCommon):
    """Point of Sale is optional: these tests run where it is installed and skip elsewhere.

    A real order of a product that isn't in stock, then the session is closed. Standard Point of
    Sale validates its picking in a savepoint, so a refusal leaves the picking open for the stock
    team and the sale and the session close as usual."""

    @classmethod
    def setUpClass(cls):
        skip_unless_installed("point_of_sale", "pos.config")
        super().setUpClass()
        cls.config = cls.basic_config
        cls.company.adams_allow_negative_stock = False
        cls.company.adams_pos_allow_negative_stock = False
        cls.item = cls.create_product("Out of Stock Item", cls.categ_basic, 10.0, 5.0)
        cls.source = cls.config.picking_type_id.default_location_src_id

    def _sell_and_close(self, quantity=2):
        session = self.open_new_session()
        orders = self._create_orders([{"pos_order_lines_ui_args": [(self.item, quantity)]}])
        session.post_closing_cash_details(sum(order.amount_paid for order in orders.values()))
        result = session.close_session_from_ui()
        self.assertTrue(result.get("successful"), result)
        self.assertEqual(session.state, "closed")
        self.assertTrue(session.picking_ids)
        return session

    def _on_hand(self):
        return sum(self.env["stock.quant"]._gather(self.item, self.source).mapped("quantity"))

    # A16
    def test_a16_session_closes_with_the_pos_bypass(self):
        self.company.adams_pos_allow_negative_stock = True
        session = self._sell_and_close()
        self.assertEqual(set(session.picking_ids.mapped("state")), {"done"})
        self.assertFalse(session.failed_pickings)
        self.assertEqual(self._on_hand(), -2)

    # A16
    def test_a16_session_closes_and_leaves_the_picking_open_without_bypass(self):
        session = self._sell_and_close()
        self.assertNotIn("done", session.picking_ids.mapped("state"))
        self.assertTrue(session.failed_pickings)
        self.assertEqual(self._on_hand(), 0)

    # A16
    def test_a16_stock_updated_at_closing(self):
        """Pickings created when the session closes follow the same rule."""
        self.company.point_of_sale_update_stock_quantities = "closing"
        session = self._sell_and_close()
        self.assertTrue(session.update_stock_at_closing)
        self.assertNotIn("done", session.picking_ids.mapped("state"))
        self.assertEqual(self._on_hand(), 0)

        self.company.adams_pos_allow_negative_stock = True
        session = self._sell_and_close()
        self.assertEqual(set(session.picking_ids.mapped("state")), {"done"})
        self.assertEqual(self._on_hand(), -2)
