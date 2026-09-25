from odoo import fields, models


# Profit and loss figures need a period report; bank and cash an "as of" report.
PERIOD_LINES = [('report_id.filter_date_range', '=', True)]
BALANCE_LINES = [('report_id.filter_date_range', '=', False)]


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
        'account.report.line', domain=PERIOD_LINES, string='Dashboard: Revenue line', ondelete='set null')
    executive_dashboard_line_gross_id = fields.Many2one(
        'account.report.line', domain=PERIOD_LINES, string='Dashboard: Gross profit line', ondelete='set null')
    executive_dashboard_line_net_id = fields.Many2one(
        'account.report.line', domain=PERIOD_LINES, string='Dashboard: Net profit line', ondelete='set null')
    executive_dashboard_line_bank_id = fields.Many2one(
        'account.report.line', domain=BALANCE_LINES, string='Dashboard: Bank and cash line', ondelete='set null')


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
