from odoo import models, fields, _
from odoo.addons.shopify.models.shopify_financial_workflow_config import FINANCIAL_STATUS


class MKLogLine(models.Model):
    _inherit = "mk.log.line"

    payment_gateway_id = fields.Many2one("shopify.payment.gateway.ts", "Shopify Payment Gateway")
    financial_status = fields.Selection(FINANCIAL_STATUS, help="Shopify Order's Financial Status.")
    is_configure_workflow = fields.Boolean("Shopify Configure Workflow?", compute='_compute_configure_workflow')

    def _compute_configure_workflow(self):
        for record in self:
            if record.payment_gateway_id and record.financial_status and record.mk_instance_id.marketplace == 'shopify':
                workflow_id = self.env['shopify.financial.workflow.config'].search(
                    [('mk_instance_id', '=', record.mk_instance_id.id), ('payment_gateway_id', '=', record.payment_gateway_id.id), ('financial_status', '=', record.financial_status)])
                record.is_configure_workflow = True if workflow_id else False
            else:
                record.is_configure_workflow = True

    def do_configure_shopify_order_workflow(self):
        workflow_id = self.env['shopify.financial.workflow.config'].search(
            [('mk_instance_id', '=', self.mk_instance_id.id), ('payment_gateway_id', '=', self.payment_gateway_id.id), ('financial_status', '=', self.financial_status)])
        if workflow_id:
            self.payment_gateway_id = False
            self.financial_status = ''
            return True
        return {
            'name': _('Order Workflow Configuration'),
            'res_model': 'shopify.financial.workflow.config',
            'view_mode': 'form',
            'context': {
                'default_mk_instance_id': self.mk_instance_id.id,
                'default_payment_gateway_id': self.payment_gateway_id.id,
                'default_financial_status': self.financial_status,
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
