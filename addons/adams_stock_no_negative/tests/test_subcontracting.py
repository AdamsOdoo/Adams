from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.mrp_subcontracting.tests.common import TestMrpSubcontractingCommon

from .common import NOT_ENOUGH, skip_unless_installed


@tagged("post_install", "-at_install")
class TestNoNegativeStockSubcontracting(TestMrpSubcontractingCommon):
    """Subcontracting is optional: these tests run where it is installed and skip elsewhere.

    A subcontracted receipt consumes the components at the subcontracting location, or at the
    subcontractor's own location under it, which standard Odoo lets go negative when the
    subcontractor uses components they hold themselves. Those locations aren't checked; our own
    stock, from which components are sent to the subcontractor, stays checked."""

    @classmethod
    def setUpClass(cls):
        skip_unless_installed("mrp_subcontracting", "res.company", "subcontracting_location_id")
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.adams_allow_negative_stock = False
        cls.warehouse = cls.env["stock.warehouse"].search([("company_id", "=", cls.company.id)], limit=1)
        cls.Quant = cls.env["stock.quant"]

    def _receipt(self, quantity=1):
        form = Form(self.env["stock.picking"])
        form.picking_type_id = self.warehouse.in_type_id
        form.partner_id = self.subcontractor_partner1
        with form.move_ids.new() as move:
            move.product_id = self.finished
            move.product_uom_qty = quantity
        receipt = form.save()
        receipt.action_confirm()
        return receipt

    def _validate(self, receipt):
        receipt.move_ids.quantity = receipt.move_ids.product_uom_qty
        receipt.move_ids.picked = True
        receipt.button_validate()
        self.assertEqual(receipt.state, "done")

    def _component_qty(self, product, location):
        return self.Quant._get_available_quantity(product, location, allow_negative=True)

    # A14
    def test_a14_subcontract_receipt_is_not_refused(self):
        """Nothing was sent to the subcontractor: the receipt is validated and the components go
        negative at the subcontracting location, as in standard Odoo."""
        location = self.subcontractor_partner1.property_stock_subcontractor
        self.assertEqual(location, self.company.subcontracting_location_id)
        receipt = self._receipt(2)
        self._validate(receipt)
        production = self.env["mrp.production"].search([("bom_id", "=", self.bom.id)])
        self.assertEqual(production.state, "done")
        self.assertEqual(self._component_qty(self.comp1, location), -2)
        self.assertEqual(self._component_qty(self.comp2, location), -2)
        self.assertEqual(self._component_qty(self.finished, self.warehouse.lot_stock_id), 2)

    # A14
    def test_a14_subcontractor_own_location(self):
        """A subcontractor with a location of its own, under the subcontracting location."""
        location = self.env["stock.location"].create({
            "name": "Subcontractor A",
            "location_id": self.company.subcontracting_location_id.id,
        })
        self.subcontractor_partner1.property_stock_subcontractor = location
        receipt = self._receipt()
        self._validate(receipt)
        self.assertEqual(self._component_qty(self.comp1, location), -1)
        self.assertEqual(self._component_qty(self.finished, self.warehouse.lot_stock_id), 1)

    # A14
    def test_a14_recorded_components_are_not_refused(self):
        """Recording more components than the subcontractor holds is accepted, and the receipt is
        validated (standard Odoo then consumes what the produced quantity needs)."""
        receipt = self._receipt()
        receipt.move_ids.quantity = 1
        receipt.move_ids.picked = True
        production = self.env["mrp.production"].search([("bom_id", "=", self.bom.id)])
        component = production.move_raw_ids.filtered(lambda m: m.product_id == self.comp1)
        component.quantity = 3
        component.picked = True
        self.assertEqual(component.quantity, 3)
        receipt.button_validate()
        self.assertEqual(receipt.state, "done")
        self.assertEqual(production.state, "done")
        location = self.subcontractor_partner1.property_stock_subcontractor
        self.assertLess(self._component_qty(self.comp1, location), 0)

    # A14
    def test_a14_resupply_from_our_stock_is_checked(self):
        """Components sent to the subcontractor leave our stock, which can't go below zero."""
        self.Quant._update_available_quantity(self.comp1, self.warehouse.lot_stock_id, 1)
        picking_type = self.warehouse.subcontracting_resupply_type_id
        destination = self.subcontractor_partner1.property_stock_subcontractor
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": self.warehouse.lot_stock_id.id,
            "location_dest_id": destination.id,
            "move_ids": [Command.create({
                "product_id": self.comp1.id,
                "product_uom_qty": 2,
                "location_id": self.warehouse.lot_stock_id.id,
                "location_dest_id": destination.id,
            })],
        })
        picking.action_confirm()
        with self.assertRaisesRegex(UserError, NOT_ENOUGH), self.env.cr.savepoint():
            picking.move_ids.quantity = 2
        self.env.invalidate_all()
        picking.move_ids.quantity = 1
        picking.move_ids.picked = True
        picking.with_context(skip_backorder=True, picking_ids_not_to_backorder=picking.ids).button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self._component_qty(self.comp1, destination), 1)
