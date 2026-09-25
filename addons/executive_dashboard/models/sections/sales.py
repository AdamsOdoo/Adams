from odoo import models


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    def _section_sales(self, scope):
        """Sales widgets, keyed by widget name. Filled in by its build phase."""
        return {}
