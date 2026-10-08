import logging

from odoo import models, fields

_logger = logging.getLogger("Qamah:Shopify")

RECOMMENDATION = [('CANCEL', 'Cancel'), ('INVESTIGATE', 'Investigate'), ('ACCEPT', 'Accept'), ('NONE', 'None')]
RISK_LEVELS = [('HIGH', 'HIGH'), ('LOW', 'LOW'), ('MEDIUM', 'MEDIUM'), ('NONE', 'NONE'), ('PENDING', 'PENDING')]


class ShopifyFraudAnalysis(models.Model):
    _name = "shopify.fraud.analysis"
    _description = "Fraud Analysis"

    order_id = fields.Many2one("sale.order", string="Order", copy=False, ondelete="cascade")
    message = fields.Char("Message", copy=False,
                          help="The message that's displayed to the merchant to indicate the results of the fraud check. The message is displayed only if display is set to true.")
    recommendation = fields.Selection(RECOMMENDATION, copy=False, default='CANCEL', help="The recommended action given to the merchant.")
    risk_source = fields.Char("Provider", copy=False, help="The source of the order risk.")
    risk_level = fields.Selection(RISK_LEVELS, copy=False, help="Indicate the risk level of fraud order.")

    def create_fraud_analysis(self, shopify_order_id, odoo_order_id, order_risk):
        """
        Migrated from Shopify REST API to GraphQL API.
        """
        try:
            if not isinstance(order_risk, dict) or not order_risk.get('assessments', []):
                return False
            for assessment in order_risk.get('assessments', []):
                if assessment.get('riskLevel', '') in ['MEDIUM', 'HIGH']:
                    # Extract NEGATIVE descriptions
                    negative_descriptions = [fact.get("description", '') for fact in assessment.get('facts', []) if fact and fact.get("sentiment", '') == "NEGATIVE"]
                    negative_messages = " , ".join(negative_descriptions) if negative_descriptions else "Shopify recommendation"
                    risk_vals = {
                        'message': negative_messages,
                        'recommendation': order_risk.get('recommendation'),
                        'risk_level': assessment.get('riskLevel', ''),
                        'risk_source': assessment.get('provider', {}).get('title', '') if assessment.get('provider', {}) else 'Internal',
                        'order_id': odoo_order_id.id}
                    self.sudo().create(risk_vals)
            return True
        except Exception as e:
            _logger.error(f"Failed to create fraud analysis for Order ID {shopify_order_id}: {str(e)}")
            return False
