from odoo import models


class ExecutiveDashboard(models.AbstractModel):
    _inherit = 'executive.dashboard'

    def _section_people(self, scope):
        """People widgets, keyed by widget name. Filled in by its build phase."""
        return {}
