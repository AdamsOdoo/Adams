from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    executive_dashboard_finance = fields.Boolean(string='Dashboard: Finance', default=True)
    executive_dashboard_sales = fields.Boolean(string='Dashboard: Sales', default=True)
    executive_dashboard_crm = fields.Boolean(string='Dashboard: CRM', default=True)
    executive_dashboard_procurement = fields.Boolean(string='Dashboard: Procurement', default=True)
    executive_dashboard_inventory = fields.Boolean(string='Dashboard: Inventory', default=True)
    executive_dashboard_people = fields.Boolean(string='Dashboard: People', default=True)
    # Report lines used by Finance when the Enterprise reports are installed. Empty means
    # the standard line; set one when a localization renames or replaces it.
    executive_dashboard_line_revenue_id = fields.Many2one(
        'account.report.line', string='Dashboard: Revenue line', ondelete='set null')
    executive_dashboard_line_gross_id = fields.Many2one(
        'account.report.line', string='Dashboard: Gross profit line', ondelete='set null')
    executive_dashboard_line_net_id = fields.Many2one(
        'account.report.line', string='Dashboard: Net profit line', ondelete='set null')
    executive_dashboard_line_bank_id = fields.Many2one(
        'account.report.line', string='Dashboard: Bank and cash line', ondelete='set null')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    executive_dashboard_finance = fields.Boolean(related='company_id.executive_dashboard_finance', readonly=False)
    executive_dashboard_sales = fields.Boolean(related='company_id.executive_dashboard_sales', readonly=False)
    executive_dashboard_crm = fields.Boolean(related='company_id.executive_dashboard_crm', readonly=False)
    executive_dashboard_procurement = fields.Boolean(related='company_id.executive_dashboard_procurement', readonly=False)
    executive_dashboard_inventory = fields.Boolean(related='company_id.executive_dashboard_inventory', readonly=False)
    executive_dashboard_people = fields.Boolean(related='company_id.executive_dashboard_people', readonly=False)
    executive_dashboard_line_revenue_id = fields.Many2one(
        related='company_id.executive_dashboard_line_revenue_id', readonly=False)
    executive_dashboard_line_gross_id = fields.Many2one(
        related='company_id.executive_dashboard_line_gross_id', readonly=False)
    executive_dashboard_line_net_id = fields.Many2one(
        related='company_id.executive_dashboard_line_net_id', readonly=False)
    executive_dashboard_line_bank_id = fields.Many2one(
        related='company_id.executive_dashboard_line_bank_id', readonly=False)
