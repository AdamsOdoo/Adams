from odoo import models, fields, api, _
from odoo.addons.base_marketplace.models.exceptions import MarketplaceException

FINANCIAL_STATUS = [('AUTHORIZED', 'Order financial is authorized'),
                    ('PENDING', 'Order financial is pending'),
                    ('PAID', 'Order financial is paid'),
                    ('PARTIALLY_PAID', 'Order financial is partially paid'),
                    ('REFUNDED', 'Order financial is refunded'),
                    ('VOIDED', 'Order financial is voided'),
                    ('PARTIALLY_REFUNDED', 'Order financial is partially refunded'),
                    ('ANY', 'Order financial is any'),
                    ('UNPAID', 'Order financial is unpaid')]


class ShopifyFinancialWorkflowConfig(models.Model):
    _name = 'shopify.financial.workflow.config'
    _description = "Shopify Financial Workflow Configuration"

    mk_instance_id = fields.Many2one('mk.instance', "Instance", ondelete='cascade')
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', default=lambda self: self.env.ref('account.account_payment_term_immediate', raise_if_not_found=False), domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', related="mk_instance_id.company_id", store=True, compute_sudo=True)
    order_workflow_id = fields.Many2one("order.workflow.config.ts", "Marketplace Workflow")
    payment_gateway_id = fields.Many2one("shopify.payment.gateway.ts", "Payment Gateway")
    financial_status = fields.Selection(FINANCIAL_STATUS, help="Shopify Order's Financial Status.")

    @api.constrains('mk_instance_id', 'payment_gateway_id', 'financial_status')
    def _check_unique_financial_workflow(self):
        for workflow in self:
            domain = [('id', '!=', workflow.id), ('mk_instance_id', '=', workflow.mk_instance_id.id), ('payment_gateway_id', '=', workflow.payment_gateway_id.id),
                      ('financial_status', '=', workflow.financial_status)]
            if self.search(domain):
                raise MarketplaceException(_('You cannot create duplicate Financial Workflow Configuration!'))
