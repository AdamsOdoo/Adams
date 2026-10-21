from contextlib import contextmanager

from odoo.exceptions import AccessError, UserError
from odoo.fields import Command
from odoo.tests import Form, new_test_user, tagged

from odoo.addons.stock.tests.common import TestStockCommon

from .common import NOT_ENOUGH


@tagged("post_install", "-at_install")
class TestNoNegativeStock(TestStockCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.group_ids += cls.env.ref("stock.group_production_lot") \
            | cls.env.ref("stock.group_tracking_owner") | cls.env.ref("stock.group_tracking_lot")
        cls.company = cls.env.company
        cls.company.adams_allow_negative_stock = False
        cls.serial_product = cls.env["product.product"].create({"name": "Serialized Device", "is_storable": True, "tracking": "serial"})
        cls.part = cls.env["product.product"].create({"name": "Test Part", "is_storable": True})
        cls.sn_1 = cls.env["stock.lot"].create({"name": "SN-0001", "product_id": cls.serial_product.id})
        cls.sn_2 = cls.env["stock.lot"].create({"name": "SN-0002", "product_id": cls.serial_product.id})
        cls.consignor = cls.env["res.partner"].create({"name": "Consignor"})
        cls.Quant = cls.env["stock.quant"]

    # Helpers ----------------------------------------------------------

    @contextmanager
    def _refused(self):
        """Expect the refusal and roll back what the failed operation did, as the web request would."""
        with self.assertRaisesRegex(UserError, NOT_ENOUGH) as error, self.env.cr.savepoint():
            yield error
        self.env.invalidate_all()

    def _stock(self, product, location, quantity, **kwargs):
        self.Quant._update_available_quantity(product, location, quantity, **kwargs)

    def _on_hand(self, product, location, **kwargs):
        """On-hand quantity, reserved included."""
        quants = self.Quant._gather(product, location, strict=True, **kwargs)
        return sum(quants.filtered(lambda q: q.lot_id == kwargs.get("lot_id", q.lot_id.browse())).mapped("quantity"))

    def _picking(self, picking_type, source, destination, product, quantity, **line_vals):
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": source.id,
            "location_dest_id": destination.id,
            "move_ids": [Command.create({
                "product_id": product.id,
                "product_uom_qty": quantity,
                "location_id": source.id,
                "location_dest_id": destination.id,
            })],
        })
        picking.action_confirm()
        move = picking.move_ids
        move.move_line_ids.unlink()
        # Enter the quantity while the stock is there, then let it go elsewhere, so that the
        # validation check is what refuses (the entry check has its own tests).
        stock_key = {
            name: self.env[model].browse(line_vals[name])
            for name, model in (("lot_id", "stock.lot"), ("package_id", "stock.package"), ("owner_id", "res.partner"))
            if name in line_vals
        }
        missing = 0
        if product.is_storable and source.usage in ("internal", "transit"):
            missing = max(0, quantity - self._on_hand(product, source, **stock_key))
        if missing:
            self._stock(product, source, missing, **stock_key)
        move.move_line_ids = [Command.create({
            "product_id": product.id,
            "quantity": quantity,
            "location_id": source.id,
            "location_dest_id": destination.id,
            **line_vals,
        })]
        if missing:
            self._stock(product, source, -missing, **stock_key)
        move.picked = True
        return picking

    def _deliver(self, product, quantity, source=None, **line_vals):
        return self._picking(self.picking_type_out, source or self.stock_location, self.customer_location,
                             product, quantity, **line_vals)

    def _assert_blocked(self, picking, product):
        with self._refused() as error:
            picking.button_validate()
        self.assertIn(product.display_name, str(error.exception))
        self.assertNotEqual(picking.state, "done")

    # Tests ------------------------------------------------------------

    # A1
    def test_a1_delivery_beyond_stock_is_refused(self):
        """A delivery of more than on hand is refused and changes nothing."""
        self._stock(self.part, self.stock_location, 2)
        picking = self._deliver(self.part, 3)
        self._assert_blocked(picking, self.part)
        self.assertEqual(self._on_hand(self.part, self.stock_location), 2)

        exact = self._deliver(self.part, 2)
        exact.button_validate()
        self.assertEqual(exact.state, "done")
        self.assertEqual(self._on_hand(self.part, self.stock_location), 0)

    # A2
    def test_a2_stock_elsewhere_does_not_count(self):
        """Stock of another serial number, location, owner or package doesn't allow the move."""
        self._stock(self.serial_product, self.shelf_1, 1, lot_id=self.sn_1)
        self._stock(self.serial_product, self.stock_location, 1, lot_id=self.sn_2)
        # SN-0001 is on shelf 1, not in the stock location itself.
        self._assert_blocked(self._deliver(self.serial_product, 1, lot_id=self.sn_1.id), self.serial_product)
        # SN-0002 is in the stock location, but not on shelf 1.
        self._assert_blocked(self._deliver(self.serial_product, 1, source=self.shelf_1, lot_id=self.sn_2.id), self.serial_product)

        # Owner: consigned stock doesn't cover own stock.
        self._stock(self.part, self.stock_location, 5, owner_id=self.consignor)
        self._assert_blocked(self._deliver(self.part, 1), self.part)
        consigned = self._deliver(self.part, 1, owner_id=self.consignor.id)
        consigned.button_validate()
        self.assertEqual(consigned.state, "done")

        # Package: loose stock doesn't cover a package that is empty.
        package = self.env["stock.package"].create({"name": "BOX-1"})
        self._assert_blocked(self._deliver(self.part, 1, owner_id=self.consignor.id, package_id=package.id), self.part)

        # The right serial number in the right place is delivered.
        good = self._deliver(self.serial_product, 1, source=self.shelf_1, lot_id=self.sn_1.id)
        good.button_validate()
        self.assertEqual(good.state, "done")

    # A3
    def test_a3_internal_transfer_is_refused(self):
        self._stock(self.part, self.shelf_1, 1)
        picking = self._picking(self.picking_type_int, self.shelf_1, self.shelf_2, self.part, 2)
        self._assert_blocked(picking, self.part)
        self.assertEqual(self._on_hand(self.part, self.shelf_1), 1)
        self.assertEqual(self._on_hand(self.part, self.shelf_2), 0)

    # A3
    def test_a3_scrap_is_refused(self):
        self._stock(self.part, self.stock_location, 1)
        scrap = self.env["stock.scrap"].create({
            "product_id": self.part.id,
            "scrap_qty": 2,
            "location_id": self.stock_location.id,
        })
        with self._refused():
            scrap.do_scrap()
        self.assertEqual(self._on_hand(self.part, self.stock_location), 1)

    # A3
    def test_a3_inventory_adjustment_below_zero_is_refused(self):
        self._stock(self.part, self.stock_location, 1)
        quant = self.Quant.with_context(inventory_mode=True).create({
            "product_id": self.part.id,
            "location_id": self.stock_location.id,
            "inventory_quantity": -1,
        })
        with self._refused():
            quant.action_apply_inventory()
        self.assertEqual(self._on_hand(self.part, self.stock_location), 1)

        # A count lower than on hand but not negative is applied.
        quant.inventory_quantity = 0
        quant.action_apply_inventory()
        self.assertEqual(self._on_hand(self.part, self.stock_location), 0)

    # A3
    def test_a3_editing_a_done_line_is_refused(self):
        """Raising a done delivery's quantity, or lowering a done receipt's quantity after the
        stock was used, would make stock negative."""
        self._stock(self.part, self.stock_location, 2)
        delivery = self._deliver(self.part, 2)
        delivery.button_validate()
        with self._refused():
            delivery.move_ids.move_line_ids.quantity = 3

        receipt = self._picking(self.picking_type_in, self.supplier_location, self.stock_location, self.part, 5)
        receipt.button_validate()
        self._deliver(self.part, 5).button_validate()
        with self._refused():
            receipt.move_ids.move_line_ids.quantity = 4
        self.assertEqual(self._on_hand(self.part, self.stock_location), 0)

    # A3
    def test_a3_line_added_to_a_done_transfer(self):
        """A line added to a done transfer takes stock at once: refused beyond stock, even when
        other stock of the place was already negative; accepted within stock."""
        self._stock(self.serial_product, self.stock_location, -2)  # untracked, from before the module
        self._stock(self.serial_product, self.stock_location, 1, lot_id=self.sn_1)
        self._stock(self.part, self.stock_location, 1)
        delivery = self._deliver(self.part, 1)
        delivery.button_validate()
        line_vals = {
            "picking_id": delivery.id,
            "product_id": self.serial_product.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "quantity": 1,
        }
        self.env["stock.move.line"].create({**line_vals, "lot_id": self.sn_1.id})
        self.assertEqual(self._on_hand(self.serial_product, self.stock_location, lot_id=self.sn_1), 0)
        with self._refused():
            self.env["stock.move.line"].create({**line_vals, "lot_id": self.sn_2.id})

    # A4
    def test_a4_lot_made_up_from_untracked_stock(self):
        """Standard Odoo takes a missing lot quantity from untracked stock of the same place;
        that isn't negative stock."""
        self._stock(self.serial_product, self.stock_location, 1)
        picking = self._deliver(self.serial_product, 1, lot_id=self.sn_1.id)
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self._on_hand(self.serial_product, self.stock_location), 0)

    # A5
    def test_a5_inter_company_transit_is_not_checked(self):
        """The shared inter-company transit location is received and delivered by two companies
        in any order."""
        transit = self.env.ref("stock.stock_location_inter_company")
        self.assertFalse(transit.company_id)
        picking = self._picking(self.picking_type_in, transit, self.stock_location, self.part, 1)
        picking.button_validate()
        self.assertEqual(picking.state, "done")

    # A4
    def test_a4_receipts_and_returns_work(self):
        """Receipts, customer returns and replenishing stock that is already negative work."""
        receipt = self._picking(self.picking_type_in, self.supplier_location, self.stock_location,
                                self.serial_product, 1, lot_id=self.sn_1.id)
        receipt.button_validate()
        delivery = self._deliver(self.serial_product, 1, lot_id=self.sn_1.id)
        delivery.button_validate()
        self.assertEqual(delivery.state, "done")

        return_wizard = Form(self.env["stock.return.picking"].with_context(
            active_id=delivery.id, active_model="stock.picking")).save()
        return_wizard.product_return_moves.quantity = 1
        customer_return = return_wizard._create_return()
        customer_return.move_ids.picked = True
        customer_return.button_validate()
        self.assertEqual(customer_return.state, "done")
        self.assertEqual(self._on_hand(self.serial_product, self.stock_location, lot_id=self.sn_1), 1)

        # Negative stock from before the module: it can be replenished, not lowered further.
        self._stock(self.part, self.stock_location, -3)
        refill = self._picking(self.picking_type_in, self.supplier_location, self.stock_location, self.part, 1)
        refill.button_validate()
        self.assertEqual(self._on_hand(self.part, self.stock_location), -2)
        self._assert_blocked(self._deliver(self.part, 1), self.part)

    # A5
    def test_a5_out_of_scope_moves_are_not_checked(self):
        """Consumables and moves out of partner or virtual locations aren't checked."""
        consumable = self.env["product.product"].create({"name": "Brochure", "type": "consu"})
        brochures = self._deliver(consumable, 10)
        brochures.button_validate()
        self.assertEqual(brochures.state, "done")

        dropship = self._picking(self.picking_type_out, self.supplier_location, self.customer_location, self.part, 4)
        dropship.button_validate()
        self.assertEqual(dropship.state, "done")

    # A6
    def test_a6_company_bypass(self):
        """With the bypass on, negative stock is allowed for that company only."""
        self.company.adams_allow_negative_stock = True
        picking = self._deliver(self.part, 2)
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self._on_hand(self.part, self.stock_location), -2)

        other_company = self.env["res.company"].create({"name": "Other Company"})
        self.env.user.company_ids += other_company
        other = self.env["stock.warehouse"].search([("company_id", "=", other_company.id)], limit=1)
        self.assertFalse(other_company.adams_allow_negative_stock)
        picking = self.env["stock.picking"].with_company(other_company).create({
            "picking_type_id": other.out_type_id.id,
            "location_id": other.lot_stock_id.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.part.id,
                "product_uom_qty": 1,
                "location_id": other.lot_stock_id.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        picking.action_confirm()
        move = picking.move_ids.with_company(other_company)
        with self._refused():
            move.quantity = 1
        # Validation: the quantity entered while the stock was there, then taken elsewhere.
        self._stock(self.part, other.lot_stock_id, 1)
        move.quantity = 1
        self._stock(self.part, other.lot_stock_id, -1)
        move.picked = True
        with self._refused():
            picking.with_company(other_company).button_validate()
        self.assertEqual(self._on_hand(self.part, other.lot_stock_id), 0)

    # A7
    def test_a7_only_settings_admins_change_the_bypass(self):
        """An Inventory Administrator who isn't a Settings administrator can't turn the bypass on."""
        manager = new_test_user(self.env, login="adams_stock_manager", groups="stock.group_stock_manager")
        with self.assertRaises(AccessError):
            self.company.with_user(manager).adams_allow_negative_stock = True
        with self.assertRaises(AccessError):
            self.company.with_user(manager).adams_pos_allow_negative_stock = True
        self.assertFalse(self.company.adams_allow_negative_stock)

        admin = new_test_user(self.env, login="adams_settings_admin", groups="base.group_system,stock.group_stock_manager")
        settings = self.env["res.config.settings"].with_user(admin).create({})
        settings.adams_allow_negative_stock = True
        settings.execute()
        self.assertTrue(self.company.adams_allow_negative_stock)

    # A12
    def test_a12_quantity_above_stock_is_refused_on_entry(self):
        """Entering a quantity above the stock on hand is refused at once, so the transfer
        doesn't show as available; the reserved part stays as it was."""
        self._stock(self.part, self.stock_location, 1)
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.part.id,
                "product_uom_qty": 3,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        move = picking.move_ids
        self.assertEqual(move.state, "partially_available")
        with self._refused() as error:
            move.quantity = 3
        self.assertIn("Test Part", str(error.exception))
        self.assertEqual(move.quantity, 1)
        self.assertEqual(move.state, "partially_available")

        # Two lines of one transfer taking the same stock count together.
        with self._refused():
            move.move_line_ids = [Command.create({
                "product_id": self.part.id,
                "quantity": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })]
        # A serial number that isn't there can't be entered either.
        serial_picking = self.env["stock.picking"].create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.serial_product.id,
                "product_uom_qty": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        serial_picking.action_confirm()
        with self._refused():
            serial_picking.move_ids.move_line_ids = [Command.create({
                "product_id": self.serial_product.id,
                "lot_id": self.sn_1.id,
                "quantity": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })]

        # Lowering is fine, and the quantity on hand is accepted and validated.
        move.quantity = 0
        move.quantity = 1
        move.picked = True
        picking.with_context(skip_backorder=True, picking_ids_not_to_backorder=picking.ids).button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self._on_hand(self.part, self.stock_location), 0)

    # A12
    def test_a12_standard_flows_are_not_refused(self):
        """Check Availability after more stock arrives, and a quantity in another unit within stock."""
        self._stock(self.part, self.stock_location, 1)
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.part.id,
                "product_uom_qty": 12,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        self.assertEqual(picking.move_ids.quantity, 1)
        self._picking(self.picking_type_in, self.supplier_location, self.stock_location, self.part, 11).button_validate()
        picking.action_assign()
        self.assertEqual(picking.move_ids.state, "assigned")

        # 1 dozen is 12 units: within the 12 on hand, but 2 dozens aren't.
        line = picking.move_ids.move_line_ids
        line.write({"quantity": 1, "product_uom_id": self.uom_dozen.id})
        with self._refused():
            line.quantity = 2

    # A12
    def test_a12_changing_the_serial_is_checked(self):
        """Switching a line to a serial number that isn't there is refused at once."""
        self._stock(self.serial_product, self.stock_location, 1, lot_id=self.sn_1)
        picking = self.env["stock.picking"].create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.serial_product.id,
                "product_uom_qty": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        picking.action_confirm()
        picking.action_assign()
        line = picking.move_ids.move_line_ids
        self.assertEqual(line.lot_id, self.sn_1)
        with self._refused():
            line.lot_id = self.sn_2

    # A12
    def test_a12_bypass_allows_entry(self):
        self.company.adams_allow_negative_stock = True
        picking = self._deliver(self.part, 2)
        picking.move_ids.quantity = 3
        self.assertEqual(picking.move_ids.quantity, 3)

    # A13
    def test_a13_pos_setting_follows_the_company_bypass(self):
        """The Point of Sale checkbox shows ticked while the company-wide bypass is on, without
        changing the company's own Point of Sale choice, which shows again when it's off."""
        settings = self.env["res.config.settings"].create({})
        self.assertFalse(settings.adams_pos_bypass_shown)

        settings = self.env["res.config.settings"].create({"adams_pos_bypass_shown": True})
        settings.execute()
        self.assertTrue(self.company.adams_pos_allow_negative_stock)

        self.company.adams_pos_allow_negative_stock = False
        settings = self.env["res.config.settings"].create({"adams_allow_negative_stock": True})
        self.assertTrue(settings.adams_pos_bypass_shown)
        settings.execute()
        self.assertTrue(self.company.adams_allow_negative_stock)
        self.assertFalse(self.company.adams_pos_allow_negative_stock)

        settings = self.env["res.config.settings"].create({})
        settings.adams_allow_negative_stock = False
        self.assertFalse(settings.adams_pos_bypass_shown)

    # A15
    def test_a15_negative_stock_topped_up_by_count(self):
        """Stock already below zero (from before the module) is corrected by a count, which may
        stay negative if it rises; consuming from it stays refused until it is back above."""
        self._stock(self.part, self.stock_location, -5)
        quant = self.Quant.with_context(inventory_mode=True).create({
            "product_id": self.part.id,
            "location_id": self.stock_location.id,
            "inventory_quantity": -2,
        })
        quant.action_apply_inventory()
        self.assertEqual(self._on_hand(self.part, self.stock_location), -2)

        # A count lower than the stock already negative is refused.
        quant.inventory_quantity = -4
        with self._refused():
            quant.action_apply_inventory()
        self.assertEqual(self._on_hand(self.part, self.stock_location), -2)

        # Consumption from it: refused when entered and when validated.
        delivery = self.env["stock.picking"].create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.part.id,
                "product_uom_qty": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        delivery.action_confirm()
        with self._refused():
            delivery.move_ids.quantity = 1
        self._assert_blocked(self._deliver(self.part, 1), self.part)
        scrap = self.env["stock.scrap"].create({
            "product_id": self.part.id,
            "scrap_qty": 1,
            "location_id": self.stock_location.id,
        })
        with self._refused():
            scrap.do_scrap()
        self.assertEqual(self._on_hand(self.part, self.stock_location), -2)

        # Counted back to a positive quantity, it is delivered.
        quant = self.Quant._gather(self.part, self.stock_location, strict=True)
        quant.with_context(inventory_mode=True).inventory_quantity = 3
        quant.action_apply_inventory()
        self.assertEqual(self._on_hand(self.part, self.stock_location), 3)
        delivery.move_ids.quantity = 1
        delivery.move_ids.picked = True
        delivery.button_validate()
        self.assertEqual(delivery.state, "done")
        self.assertEqual(self._on_hand(self.part, self.stock_location), 2)

    # A17
    def test_a17_check_follows_the_company_of_the_stock(self):
        """The bypass is read from the company the stock belongs to, not from the company the
        user is working in."""
        other_company = self.env["res.company"].create({"name": "Other Company"})
        self.env.user.company_ids += other_company
        other_company.adams_allow_negative_stock = True
        other = self.env["stock.warehouse"].search([("company_id", "=", other_company.id)], limit=1)

        def delivery(company, picking_type, source):
            picking = self.env["stock.picking"].with_company(company).create({
                "picking_type_id": picking_type.id,
                "location_id": source.id,
                "location_dest_id": self.customer_location.id,
                "move_ids": [Command.create({
                    "product_id": self.part.id,
                    "product_uom_qty": 1,
                    "location_id": source.id,
                    "location_dest_id": self.customer_location.id,
                })],
            })
            picking.action_confirm()
            return picking

        # Working in this company (no bypass): the other company's stock may go negative.
        in_this = [self.company.id, other_company.id]
        picking = delivery(other_company, other.out_type_id, other.lot_stock_id).with_context(allowed_company_ids=in_this)
        self.assertEqual(picking.env.company, self.company)
        picking.move_ids.quantity = 1
        picking.move_ids.picked = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")
        self.assertEqual(self._on_hand(self.part, other.lot_stock_id), -1)

        # Working in the other company (bypass on): this company's stock is still protected.
        in_other = [other_company.id, self.company.id]
        picking = delivery(self.company, self.picking_type_out, self.stock_location).with_context(allowed_company_ids=in_other)
        self.assertEqual(picking.env.company, other_company)
        with self._refused():
            picking.move_ids.quantity = 1
        # Validation: the quantity entered while the stock was there, then taken elsewhere.
        self._stock(self.part, self.stock_location, 1)
        picking.move_ids.quantity = 1
        self._stock(self.part, self.stock_location, -1)
        picking.move_ids.picked = True
        with self._refused():
            picking.button_validate()
        self.assertEqual(self._on_hand(self.part, self.stock_location), 0)

    # A8
    def test_a8_message_names_the_product(self):
        self._stock(self.part, self.stock_location, 1)
        picking = self._deliver(self.part, 2)
        with self._refused() as error:
            picking.button_validate()
        message = str(error.exception)
        self.assertIn("Test Part", message)
        self.assertNotIn(self.stock_location.complete_name, message)

    # A8
    def test_a8_message_in_arabic(self):
        """An Arabic user gets the refusal in Arabic, naming the product."""
        self.env["res.lang"]._activate_lang("ar_001")
        self.env["ir.module.module"]._load_module_terms(["adams_stock_no_negative"], ["ar_001"], overwrite=True)
        self._stock(self.part, self.stock_location, 1)
        picking = self._deliver(self.part, 2).with_context(lang="ar_001")
        with self.assertRaisesRegex(UserError, "لا يوجد مخزون كافٍ") as error, self.env.cr.savepoint():
            picking.button_validate()
        self.assertIn("Test Part", str(error.exception))
        self.assertNotIn(NOT_ENOUGH, str(error.exception))


@tagged("post_install", "-at_install")
class TestNoNegativeStockPos(TestStockCommon):
    """Point of Sale is optional: these tests run where it is installed and skip elsewhere."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.adams_allow_negative_stock = False
        cls.part = cls.env["product.product"].create({"name": "Test Part", "is_storable": True})

    def _pos_delivery(self):
        if "pos.config" not in self.env:
            self.skipTest("point_of_sale is not installed")
        config = self.env["pos.config"].create({"name": "Test Shop"})
        picking_type = config.picking_type_id
        picking = self.env["stock.picking"].create({
            "picking_type_id": picking_type.id,
            "location_id": picking_type.default_location_src_id.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.part.id,
                "product_uom_qty": 1,
                "location_id": picking_type.default_location_src_id.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        picking.action_confirm()
        picking.move_ids.quantity = 1
        picking.move_ids.picked = True
        return picking

    # A9
    def test_a9_pos_blocked_by_default(self):
        picking = self._pos_delivery()
        with self.assertRaisesRegex(UserError, NOT_ENOUGH):
            picking.button_validate()

    # A9
    def test_a9_pos_bypass(self):
        """The Point of Sale bypass lets PoS pickings go negative, not other transfers."""
        picking = self._pos_delivery()
        self.env.company.adams_pos_allow_negative_stock = True
        picking.button_validate()
        self.assertEqual(picking.state, "done")

        other = self.env["stock.picking"].create({
            "picking_type_id": self.picking_type_out.id,
            "location_id": self.stock_location.id,
            "location_dest_id": self.customer_location.id,
            "move_ids": [Command.create({
                "product_id": self.part.id,
                "product_uom_qty": 1,
                "location_id": self.stock_location.id,
                "location_dest_id": self.customer_location.id,
            })],
        })
        other.action_confirm()
        with self.assertRaisesRegex(UserError, NOT_ENOUGH), self.env.cr.savepoint():
            other.move_ids.quantity = 1
        self.env.invalidate_all()
        # Validation: the quantity entered while the stock was there, then taken elsewhere.
        quant = self.env["stock.quant"]
        missing = 1 - sum(quant._gather(self.part, self.stock_location).mapped("quantity"))
        quant._update_available_quantity(self.part, self.stock_location, missing)
        other.move_ids.quantity = 1
        quant._update_available_quantity(self.part, self.stock_location, -missing)
        other.move_ids.picked = True
        with self.assertRaisesRegex(UserError, NOT_ENOUGH):
            other.button_validate()


@tagged("post_install", "-at_install")
class TestNoNegativeStockMrp(TestStockCommon):
    """Manufacturing is optional: these tests run where it is installed and skip elsewhere."""

    def _production(self, component_lines):
        if "mrp.production" not in self.env:
            self.skipTest("mrp is not installed")
        self.env.company.adams_allow_negative_stock = False
        kit = self.env["product.product"].create({"name": "Finished Kit", "is_storable": True})
        bom = self.env["mrp.bom"].create({
            "product_tmpl_id": kit.product_tmpl_id.id,
            "product_qty": 1,
            "bom_line_ids": [Command.create({"product_id": product.id, "product_qty": qty})
                             for product, qty in component_lines],
        })
        form = Form(self.env["mrp.production"])
        form.product_id = kit
        form.bom_id = bom
        form.product_qty = 1
        production = form.save()
        production.action_confirm()
        production.location_src_id = self.stock_location
        production.move_raw_ids.location_id = self.stock_location
        return production

    # A10
    def test_a10_manufacturing_consumption_is_refused(self):
        """Components entered while in stock, then taken elsewhere: Produce is refused."""
        component = self.env["product.product"].create({"name": "Test Part", "is_storable": True})
        quant = self.env["stock.quant"]
        quant._update_available_quantity(component, self.stock_location, 2)
        production = self._production([(component, 2)])
        production.qty_producing = 1
        production.move_raw_ids.quantity = 2
        production.move_raw_ids.picked = True
        quant._update_available_quantity(component, self.stock_location, -1)
        with self.assertRaisesRegex(UserError, NOT_ENOUGH):
            production.button_mark_done()

    # A10, A12
    def test_a12_manufacturing_components_counted_together(self):
        """The same component on two lines of one order counts together at entry."""
        component = self.env["product.product"].create({"name": "Test Part", "is_storable": True})
        self.env["stock.quant"]._update_available_quantity(component, self.stock_location, 3)
        production = self._production([(component, 2), (component, 2)])
        first, second = production.move_raw_ids
        first.quantity = 2
        with self.assertRaisesRegex(UserError, NOT_ENOUGH):
            second.quantity = 2
