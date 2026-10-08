from odoo import models, fields


class SaleReport(models.Model):
    _inherit = 'sale.report'

    shopify_order_source_name = fields.Char("Shopify Order Source", readonly=True)

    def _select_additional_fields(self):
        """
        TASK T6995 - Set the source Field data inside the Sales reporting (Add the Group By,Direct Search and also available  in pivot view (For the this field Data :shopify_order_source_name ))
        """
        res = super()._select_additional_fields()
        res['shopify_order_source_name'] = "s.shopify_order_source_name"
        return res

    def _group_by_sale(self):
        """
         TASK T6995 - Set the source Field data inside the Sales reporting (Add the Group By,Direct Search and also available  in pivot view (For the this field Data :shopify_order_source_name ))
        """
        res = super()._group_by_sale()
        res += ", s.shopify_order_source_name"
        return res
