# Part of Shopify Connector Pro. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ShopifyPayout(models.Model):
    _name = 'shopify.payout'
    _description = 'Shopify Payout'
    _order = 'payout_date desc'

    backend_id = fields.Many2one(
        'shopify.backend', required=True, ondelete='cascade', index=True,
    )
    shopify_payout_id = fields.Char('Shopify Payout ID', required=True, index=True)
    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_transit', 'In Transit'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], index=True)
    amount = fields.Monetary('Net Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    payout_date = fields.Date('Payout Date')

    # Breakdown
    gross_amount = fields.Monetary('Gross Amount', currency_field='currency_id')
    fees_amount = fields.Monetary('Fees', currency_field='currency_id')
    adjustments_amount = fields.Monetary('Adjustments', currency_field='currency_id')
    refunds_amount = fields.Monetary('Refunds', currency_field='currency_id')
    charges_amount = fields.Monetary('Charges', currency_field='currency_id')

    summary = fields.Text('Summary')

    # Link to bank journal entry
    journal_entry_id = fields.Many2one(
        'account.move', string='Journal Entry',
        help="Accounting journal entry created for this payout.",
    )

    transaction_ids = fields.One2many(
        'shopify.payout.transaction', 'payout_id',
        string='Transactions',
    )
    transaction_count = fields.Integer(compute='_compute_transaction_count')


    _unique_payout = models.Constraint(
        'UNIQUE(backend_id, shopify_payout_id)',
        'This payout has already been imported.',
    )

    @api.depends('transaction_ids')
    def _compute_transaction_count(self):
        for rec in self:
            rec.transaction_count = len(rec.transaction_ids)


class ShopifyPayoutTransaction(models.Model):
    _name = 'shopify.payout.transaction'
    _description = 'Shopify Payout Transaction'
    _order = 'processed_at desc'

    payout_id = fields.Many2one(
        'shopify.payout', required=True, ondelete='cascade', index=True,
    )
    backend_id = fields.Many2one(
        related='payout_id.backend_id', store=True,
    )
    shopify_transaction_id = fields.Char('Transaction ID', index=True)
    transaction_type = fields.Selection([
        ('charge', 'Charge'),
        ('refund', 'Refund'),
        ('dispute', 'Dispute'),
        ('reserve', 'Reserve'),
        ('adjustment', 'Adjustment'),
        ('payout', 'Payout'),
    ])
    source_type = fields.Selection([
        ('charge', 'Charge'),
        ('refund', 'Refund'),
        ('dispute', 'Dispute'),
        ('reserve', 'Reserve'),
        ('adjustment', 'Adjustment'),
        ('payout', 'Payout'),
    ])
    amount = fields.Monetary('Amount', currency_field='currency_id')
    fee = fields.Monetary('Fee', currency_field='currency_id')
    net = fields.Monetary('Net', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency')
    source_order_id = fields.Char('Source Order ID')
    processed_at = fields.Datetime('Processed At')
