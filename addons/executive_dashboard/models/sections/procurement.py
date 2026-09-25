from odoo import models


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    def _section_procurement(self, scope):
        """Procurement widgets, keyed by widget name. Filled in by its build phase."""
        return {}
