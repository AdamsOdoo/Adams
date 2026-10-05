from odoo import fields, models


class ShopifyPayoutAccountConfig(models.Model):
    _name = 'shopify.payout.account.config'
    _description = 'Shopify Payout Account Config'

    mk_instance_id = fields.Many2one('mk.instance', string="Instance", ondelete="cascade")
    company_id = fields.Many2one('res.company', related="mk_instance_id.company_id", store=True, compute_sudo=True)
    account_id = fields.Many2one('account.account', string='Account', domain="[('active', '=', True)]", company_dependent=True)
    transaction_type_id = fields.Many2one('shopify.payout.transaction.type', help="The type of the resource leading to the transaction.", string="Transaction Type")

    _check_unique_transaction_type = models.Constraint("UNIQUE (transaction_type_id, mk_instance_id)", "You cannot create multiple configuration for same transaction type.")
