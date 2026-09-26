from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    adams_dashboard_finance = fields.Boolean(string='Accounting & Finance', default=True)
    adams_dashboard_sales = fields.Boolean(string='Sales', default=True)
    adams_dashboard_crm = fields.Boolean(string='CRM', default=True)
    adams_dashboard_inventory = fields.Boolean(string='Inventory', default=True)
    adams_dashboard_procurement = fields.Boolean(string='Procurement', default=True)
    adams_dashboard_hr = fields.Boolean(string='Human Resources', default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    adams_dashboard_finance = fields.Boolean(related='company_id.adams_dashboard_finance', readonly=False)
    adams_dashboard_sales = fields.Boolean(related='company_id.adams_dashboard_sales', readonly=False)
    adams_dashboard_crm = fields.Boolean(related='company_id.adams_dashboard_crm', readonly=False)
    adams_dashboard_inventory = fields.Boolean(related='company_id.adams_dashboard_inventory', readonly=False)
    adams_dashboard_procurement = fields.Boolean(related='company_id.adams_dashboard_procurement', readonly=False)
    adams_dashboard_hr = fields.Boolean(related='company_id.adams_dashboard_hr', readonly=False)
