from odoo import models


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    def _section_inventory(self, scope):
        """Inventory widgets, keyed by widget name. Filled in by its build phase."""
        return {}
