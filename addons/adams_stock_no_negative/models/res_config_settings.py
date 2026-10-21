from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    adams_allow_negative_stock = fields.Boolean(
        related="company_id.adams_allow_negative_stock", readonly=False,
    )
    adams_pos_allow_negative_stock = fields.Boolean(
        string="Company's Point of Sale bypass",
        related="company_id.adams_pos_allow_negative_stock", readonly=False,
    )
    # What the Point of Sale checkbox shows: ticked (and read-only in the view) while the
    # company-wide bypass is on, since that bypass covers Point of Sale too. The company's own
    # Point of Sale choice is kept and shows again when the company-wide bypass is turned off.
    adams_pos_bypass_shown = fields.Boolean(
        string="Bypass negative consumption for Point of Sale",
        compute="_compute_adams_pos_bypass_shown",
        inverse="_inverse_adams_pos_bypass_shown",
        help="Allow Point of Sale orders to deliver products that are not in stock.",
    )
    adams_pos_installed = fields.Boolean(string="Point of Sale installed", compute="_compute_adams_pos_installed")

    @api.depends("company_id")
    def _compute_adams_pos_installed(self):
        # Point of Sale is optional: the setting shows only where it is installed.
        self.adams_pos_installed = "pos.config" in self.env

    @api.depends("adams_allow_negative_stock", "adams_pos_allow_negative_stock")
    def _compute_adams_pos_bypass_shown(self):
        for settings in self:
            settings.adams_pos_bypass_shown = settings.adams_allow_negative_stock or settings.adams_pos_allow_negative_stock

    def _inverse_adams_pos_bypass_shown(self):
        for settings in self:
            if not settings.adams_allow_negative_stock:
                settings.adams_pos_allow_negative_stock = settings.adams_pos_bypass_shown
