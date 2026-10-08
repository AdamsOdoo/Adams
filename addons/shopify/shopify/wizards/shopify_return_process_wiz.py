import logging

from odoo import models, fields, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException

_logger = logging.getLogger("Qamah:Shopify")


class ShopifyReturnProcessWizard(models.TransientModel):
    _name = "shopify.return.process.wizard"
    _description = "Process and Close a Shopify Return"

    return_id = fields.Many2one('shopify.return.ts', "Return", required=True, readonly=True)
    do_process = fields.Boolean("Mark as Processed", default=True,
                                help="Calls returnProcess on Shopify — confirms received items and updates Shopify financials.")
    do_close = fields.Boolean("Close after Processing", default=True,
                              help="Calls returnClose to mark the return complete in Shopify.")

    def action_run(self):
        self.ensure_one()
        if not (self.do_process or self.do_close):
            raise MarketplaceException(_("Select at least one action (Process or Close) before running."))
        if self.do_process:
            self.return_id.action_process_shopify_return()
        if self.do_close:
            self.return_id.action_close_shopify_return()
        return {
            'effect': {
                'fadeout': 'slow',
                'message': _("Return updated successfully in Shopify."),
                'type': 'rainbow_man',
            }
        }
