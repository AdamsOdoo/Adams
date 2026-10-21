from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_assign(self, force_qty=False):
        # Reservation only takes what is there: no entry check on the lines it creates (it
        # would read every line of the transfer again for each move).
        return super(StockMove, self.with_context(adams_reserving=True))._action_assign(force_qty=force_qty)
