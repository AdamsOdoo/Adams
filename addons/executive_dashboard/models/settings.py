from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    executive_dashboard_finance = fields.Boolean(string='Dashboard: Finance', default=True)
    executive_dashboard_sales = fields.Boolean(string='Dashboard: Sales', default=True)
    executive_dashboard_crm = fields.Boolean(string='Dashboard: CRM', default=True)
    executive_dashboard_procurement = fields.Boolean(string='Dashboard: Procurement', default=True)
    executive_dashboard_inventory = fields.Boolean(string='Dashboard: Inventory', default=True)
    executive_dashboard_people = fields.Boolean(string='Dashboard: People', default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    executive_dashboard_finance = fields.Boolean(related='company_id.executive_dashboard_finance', readonly=False)
    executive_dashboard_sales = fields.Boolean(related='company_id.executive_dashboard_sales', readonly=False)
    executive_dashboard_crm = fields.Boolean(related='company_id.executive_dashboard_crm', readonly=False)
    executive_dashboard_procurement = fields.Boolean(related='company_id.executive_dashboard_procurement', readonly=False)
    executive_dashboard_inventory = fields.Boolean(related='company_id.executive_dashboard_inventory', readonly=False)
    executive_dashboard_people = fields.Boolean(related='company_id.executive_dashboard_people', readonly=False)
