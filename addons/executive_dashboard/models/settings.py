from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    executive_dashboard_key_metrics = fields.Boolean(string='Dashboard: Key metrics', default=True)
    executive_dashboard_finance = fields.Boolean(string='Dashboard: Finance', default=True)
    executive_dashboard_ad_account_ids = fields.Many2many(
        'account.account', 'executive_dashboard_ad_account_rel', 'company_id', 'account_id',
        string='Dashboard: advertising accounts',
        domain="[('account_type', 'in', ('expense', 'expense_direct_cost', 'expense_other'))]",
        help='Expense accounts whose posted entries are the ad spend of ROAS (Key metrics).')
    executive_dashboard_sales = fields.Boolean(string='Dashboard: Sales', default=True)
    executive_dashboard_crm = fields.Boolean(string='Dashboard: CRM', default=True)
    executive_dashboard_procurement = fields.Boolean(string='Dashboard: Procurement', default=True)
    executive_dashboard_inventory = fields.Boolean(string='Dashboard: Inventory', default=True)
    executive_dashboard_people = fields.Boolean(string='Dashboard: People', default=True)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    executive_dashboard_key_metrics = fields.Boolean(related='company_id.executive_dashboard_key_metrics', readonly=False)
    executive_dashboard_finance = fields.Boolean(related='company_id.executive_dashboard_finance', readonly=False)
    executive_dashboard_ad_account_ids = fields.Many2many(
        related='company_id.executive_dashboard_ad_account_ids', readonly=False)
    executive_dashboard_sales = fields.Boolean(related='company_id.executive_dashboard_sales', readonly=False)
    executive_dashboard_crm = fields.Boolean(related='company_id.executive_dashboard_crm', readonly=False)
    executive_dashboard_procurement = fields.Boolean(related='company_id.executive_dashboard_procurement', readonly=False)
    executive_dashboard_inventory = fields.Boolean(related='company_id.executive_dashboard_inventory', readonly=False)
    executive_dashboard_people = fields.Boolean(related='company_id.executive_dashboard_people', readonly=False)
