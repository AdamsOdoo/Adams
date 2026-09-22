"""Keep strict-location quantities distinct from company-valued stock columns."""
from copy import deepcopy

from lxml import etree

from odoo import api, models


class DashboardInventoryProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if (view_type != 'list'
                or self.env.context.get('adams_dashboard_quantity_view_ref') != 'stock.product_product_stock_tree'):
            return result
        # Odoo's view service retains only lang and *_view_ref context keys.
        # This namespaced view selector therefore survives get_views and is
        # included in the web ORM view cache key. Quantity scope remains in
        # the action's location/strict context for actual record reads.
        # The underlying native view may be cached. Never mutate its shared
        # dictionary/architecture or another action's valuation columns.
        result = deepcopy(result)
        arch = etree.fromstring(result['arch'])
        for node in arch.xpath("//field[@name='total_value' or @name='avg_cost' or @name='standard_price']"):
            node.getparent().remove(node)
        result['arch'] = etree.tostring(arch, encoding='unicode')
        return result
