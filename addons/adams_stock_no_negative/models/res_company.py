from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    adams_allow_negative_stock = fields.Boolean(
        string="Bypass negative consumption prevention",
        help="Allow stock operations of this company to take on-hand quantities below zero.",
    )
    adams_pos_allow_negative_stock = fields.Boolean(
        string="Bypass negative consumption for Point of Sale",
        help="Allow Point of Sale orders of this company to deliver products that are not in stock.",
    )
