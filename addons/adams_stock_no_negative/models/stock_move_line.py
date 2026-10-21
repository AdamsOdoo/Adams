from collections import defaultdict

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import SQL

CHECKED_USAGES = ("internal", "transit")


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    @api.model_create_multi
    def create(self, vals_list):
        # A line created in a done transfer moves stock at once: read its source before.
        pairs = set()
        for vals in vals_list:
            move = self.env["stock.move"].browse(vals.get("move_id"))
            picking = self.env["stock.picking"].browse(vals.get("picking_id"))
            if move.state != "done" and picking.state != "done":
                continue
            product_id = vals.get("product_id") or move.product_id.id
            for location_id in (vals.get("location_id"), move.location_id.id, picking.location_id.id):
                if product_id and location_id:
                    pairs.add((product_id, location_id))
        before = self._adams_stock_totals(pairs)
        mls = super().create(vals_list)
        done_mls = mls.filtered(lambda ml: ml.state == "done")
        if done_mls:
            done_mls._adams_check_no_negative(done_mls._adams_stock_keys(destination=False), before)
        (mls - done_mls)._adams_check_entry()
        return mls

    def write(self, vals):
        done_mls = self.env["stock.move.line"]
        entry_mls = self.env["stock.move.line"]
        if {"quantity", "product_id", "product_uom_id", "location_id", "location_dest_id", "lot_id",
                "package_id", "result_package_id", "owner_id", "quant_id"} & vals.keys():
            done_mls = self.filtered(lambda ml: ml.move_id.state == "done")
            # A line not done yet is checked when it asks for more, or for other stock.
            if {"product_id", "product_uom_id", "location_id", "lot_id", "package_id", "owner_id", "quant_id"} & vals.keys():
                entry_mls = self - done_mls
            elif "quantity" in vals:
                entry_mls = (self - done_mls).filtered(lambda ml: ml.product_uom_id.compare(vals["quantity"], ml.quantity) > 0)
        if not done_mls:
            res = super().write(vals)
            entry_mls._adams_check_entry()
            return res
        # Editing a done line moves its stock again: the old and new source and destination
        # can fall.
        new_location_ids = [vals[name] for name in ("location_id", "location_dest_id") if vals.get(name)]
        before = self._adams_stock_totals(
            {(ml.product_id.id, location_id) for ml in done_mls
             for location_id in [ml.location_id.id, ml.location_dest_id.id, *new_location_ids]}
        )
        keys = done_mls._adams_stock_keys()
        res = super().write(vals)
        done_mls._adams_check_no_negative(keys | done_mls._adams_stock_keys(), before)
        entry_mls._adams_check_entry()
        return res

    def _action_done(self):
        keys = self._adams_stock_keys()
        before = self._adams_stock_totals({key[:2] for key in keys})
        # While validating, stock has already moved: the check below replaces the entry check.
        res = super(StockMoveLine, self.with_context(adams_validating=True))._action_done()
        # The standard method deletes lines without quantity and can assign lots.
        self._adams_check_no_negative(keys | self.exists()._adams_stock_keys(destination=False), before)
        return res

    # ------------------------------------------------------------------
    # Check
    # ------------------------------------------------------------------

    def _adams_check_entry(self):
        """Refuse a quantity entered above the stock on hand, so the transfer doesn't show as
        available when it can't be validated. Per transfer and stock key: all lines of the
        transfer taking from the same stock count together. Standard reservation never asks for
        more than is there; Point of Sale lines are checked when their picking is validated."""
        if self.env.context.get("adams_validating") or self.env.context.get("adams_reserving"):
            return
        lines = self.filtered(lambda ml: ml.product_id.is_storable and ml.move_id.state not in ("done", "cancel")
                              and not (ml.lot_name and not ml.lot_id) and ml._adams_is_checked(ml.location_id))
        if not lines:
            return
        pos_picking_types = self._adams_pos_picking_types(lines.move_id.picking_type_id | lines.picking_id.picking_type_id)
        lines = lines.filtered(lambda ml: not ml._adams_is_pos_line(pos_picking_types))
        if not lines:
            return

        def key(ml):
            return (ml.product_id.id, ml.location_id.id, ml.lot_id.id or None, ml.package_id.id or None, ml.owner_id.id or None)

        production_field = "raw_material_production_id" if "raw_material_production_id" in self.env["stock.move"]._fields else None

        def transfer(ml):
            picking = ml.picking_id or ml.move_id.picking_id
            if picking:
                return ("picking", picking.id)
            if production_field and ml.move_id[production_field]:
                # Manufacturing (optional app): all components of one order count together.
                return ("production", ml.move_id[production_field].id)
            return ("move", ml.move_id.id)

        wanted = {(transfer(ml), key(ml)) for ml in lines}
        pickings = lines.picking_id | lines.move_id.picking_id
        moves = lines.move_id
        if production_field:
            moves |= lines.move_id[production_field].move_raw_ids
        siblings = self.search([
            ("product_id", "in", lines.product_id.ids),
            ("location_id", "in", lines.location_id.ids),
            ("state", "not in", ("done", "cancel")),
            "|", ("picking_id", "in", pickings.ids), ("move_id", "in", (pickings.move_ids | moves).ids),
        ]).filtered(lambda ml: (transfer(ml), key(ml)) in wanted)
        asked = defaultdict(float)
        for ml in siblings:
            asked[(transfer(ml), key(ml))] += ml.quantity_product_uom
        on_hand = self._adams_stock_totals({k[:2] for _t, k in wanted})
        products = self.env["product.product"]
        for (_transfer, k), quantity in asked.items():
            available = on_hand[k]
            if k[2]:
                # Standard Odoo makes up a missing lot quantity from untracked stock.
                available += max(on_hand[(k[0], k[1], None, k[3], k[4])], 0.0)
            product = self.env["product.product"].browse(k[0])
            if product.uom_id.compare(quantity, available) > 0:
                products |= product
        if products:
            raise UserError(self.env._(
                "Not enough stock of %(products)s. This operation would make the on-hand quantity negative.",
                products=", ".join(products.mapped("display_name")),
            ))

    def _adams_stock_keys(self, destination=True):
        """Stock keys (product, location, lot, package, owner) these lines take from, and give to
        with `destination`, without the ones where negative stock is allowed."""
        keys = set()
        pos_picking_types = None
        for ml in self:
            product = ml.product_id
            if not product.is_storable:
                continue
            if ml._adams_company(ml.location_id).adams_pos_allow_negative_stock:
                if pos_picking_types is None:
                    pos_picking_types = self._adams_pos_picking_types()
                if ml._adams_is_pos_line(pos_picking_types):
                    continue
            locations = [(ml.location_id, ml.package_id)]
            if destination:
                locations.append((ml.location_dest_id, ml.result_package_id))
            for location, package in locations:
                if not ml._adams_is_checked(location):
                    continue
                keys.add((product.id, location.id, ml.lot_id.id or None, package.id or None, ml.owner_id.id or None))
                if ml.lot_id:
                    # Standard Odoo makes up a missing lot quantity from untracked stock.
                    keys.add((product.id, location.id, None, package.id or None, ml.owner_id.id or None))
        return keys

    def _adams_company(self, location):
        return location.company_id or self.company_id

    def _adams_is_checked(self, location):
        if location.usage not in CHECKED_USAGES:
            return False
        if not location.company_id:
            # Shared locations, such as the inter-company transit location: the delivering and
            # the receiving company validate independently, in any order.
            return False
        company = location.company_id
        if company.adams_allow_negative_stock:
            return False
        # Subcontracting (optional app): components are consumed at the subcontracting location,
        # or at a subcontractor's own location under it, which go negative by standard design.
        if "subcontracting_location_id" in company._fields and company.subcontracting_location_id \
                and location._child_of(company.subcontracting_location_id):
            return False
        return True

    def _adams_pos_picking_types(self, picking_types=None):
        """Point of Sale operation types, among `picking_types` when given."""
        if "pos.config" not in self.env:
            return self.env["stock.picking.type"]
        pos_domain = [("picking_type_id", "in", picking_types.ids)] if picking_types is not None else []
        warehouse_domain = [("pos_type_id", "in", picking_types.ids)] if picking_types is not None else []
        return (
            self.env["pos.config"].sudo().with_context(active_test=False).search(pos_domain).picking_type_id
            | self.env["stock.warehouse"].sudo().with_context(active_test=False).search(warehouse_domain).pos_type_id
        )

    def _adams_is_pos_line(self, pos_picking_types):
        """Point of Sale is optional: its pickings are known by their operation type, and
        ship-later orders by the order linked to the move."""
        self.ensure_one()
        if "pos.config" not in self.env:
            return False
        move = self.move_id
        if (move.picking_type_id or self.picking_id.picking_type_id) in pos_picking_types:
            return True
        return bool(move.reference_ids.sudo().pos_order_ids)

    @api.model
    def _adams_stock_totals(self, pairs, lock=False):
        """On-hand quantity per key (product, location, lot, package, owner) of the given
        (product, location) pairs, from the quants."""
        totals = defaultdict(float)
        if not pairs:
            return totals
        self.env["stock.quant"].flush_model(["product_id", "location_id", "lot_id", "package_id", "owner_id", "quantity"])
        pairs = tuple(pairs)
        if lock:
            # Wait for other transactions moving the same stock: the standard method skips
            # locked quants, which would let two users take the same unit.
            self.env.cr.execute(SQL(
                "SELECT id FROM stock_quant WHERE (product_id, location_id) IN %s ORDER BY id FOR NO KEY UPDATE",
                pairs,
            ))
        self.env.cr.execute(SQL(
            """SELECT product_id, location_id, lot_id, package_id, owner_id, COALESCE(SUM(quantity), 0)
                 FROM stock_quant
                WHERE (product_id, location_id) IN %s
             GROUP BY product_id, location_id, lot_id, package_id, owner_id""",
            pairs,
        ))
        for product_id, location_id, lot_id, package_id, owner_id, quantity in self.env.cr.fetchall():
            totals[(product_id, location_id, lot_id, package_id, owner_id)] = quantity
        return totals

    @api.model
    def _adams_check_no_negative(self, keys, before):
        """Refuse when a key ends below zero and lower than before, so stock that was already
        negative can still be replenished."""
        products = self.env["product.product"].browse({key[0] for key in keys})
        uoms = {product.id: product.uom_id for product in products}

        def falling_below_zero(totals):
            return {
                key for key in keys
                if uoms[key[0]].compare(totals[key], 0) < 0
                and uoms[key[0]].compare(totals[key], before.get(key, 0.0)) < 0
            }

        # Lock and read again only where stock falls below zero, so plain receipts don't wait.
        candidates = falling_below_zero(self._adams_stock_totals({key[:2] for key in keys}))
        if not candidates:
            return
        refused = falling_below_zero(self._adams_stock_totals({key[:2] for key in candidates}, lock=True)) & candidates
        if refused:
            raise UserError(self.env._(
                "Not enough stock of %(products)s. This operation would make the on-hand quantity negative.",
                products=", ".join(products.filtered(lambda p: p.id in {key[0] for key in refused}).mapped("display_name")),
            ))
