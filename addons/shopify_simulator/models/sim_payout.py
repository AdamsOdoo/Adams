# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Simulated Shopify Payout and Payout Transaction models.

Payouts represent periodic financial disbursements from Shopify Payments.
"""
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class SimShopifyPayout(models.Model):
    _name = 'sim.shopify.payout'
    _description = 'Simulated Shopify Payout'
    _order = 'payout_date desc, id desc'
    _rec_name = 'shopify_gid'

    _unique_payout = models.Constraint(
        'UNIQUE(config_id, shopify_gid)',
        'Payout GID must be unique per config.',
    )

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)

    status = fields.Selection([
        ('SCHEDULED', 'Scheduled'),
        ('IN_TRANSIT', 'In Transit'),
        ('PAID', 'Paid'),
        ('FAILED', 'Failed'),
        ('CANCELLED', 'Cancelled'),
    ], default='PAID', string='Status', required=True)

    amount = fields.Float(string='Net Amount', help='Net payout amount.')
    currency_code = fields.Char(string='Currency', default='USD')
    payout_date = fields.Date(string='Payout Date')

    gross_amount = fields.Float(string='Gross Amount')
    fees_amount = fields.Float(string='Fees Amount')
    adjustments_amount = fields.Float(string='Adjustments')
    refunds_amount = fields.Float(string='Refunds')
    charges_amount = fields.Float(string='Charges')

    summary = fields.Text(string='Summary')
    transaction_ids = fields.One2many(
        'sim.shopify.payout.transaction', 'payout_id',
        string='Transactions',
    )
    transaction_count = fields.Integer(
        compute='_compute_transaction_count', string='Transaction Count',
    )

    @api.depends('transaction_ids')
    def _compute_transaction_count(self):
        for rec in self:
            rec.transaction_count = len(rec.transaction_ids)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.shopify_gid:
                rec.shopify_gid = rec.config_id._next_gid('ShopifyPaymentsPayout')
        return records

    def _to_graphql_node(self):
        """Build GraphQL node for payout."""
        def _money(amt):
            return {
                'amount': str(amt or 0.0),
                'currencyCode': self.currency_code or 'USD',
            }
        return {
            'id': self.shopify_gid,
            'status': self.status,
            'net': _money(self.amount),
            'gross': _money(self.gross_amount),
            'fees': _money(self.fees_amount),
            'transactionsSummary': {
                'adjustmentsFee': _money(self.adjustments_amount),
                'refundsFee': _money(self.refunds_amount),
                'chargesFee': _money(self.charges_amount),
            },
            'issuedAt': self.payout_date.isoformat() if self.payout_date else None,
            'summary': self.summary or '',
        }


class SimShopifyPayoutTransaction(models.Model):
    _name = 'sim.shopify.payout.transaction'
    _description = 'Simulated Shopify Payout Transaction'
    _order = 'processed_at desc, id desc'
    _rec_name = 'shopify_gid'

    payout_id = fields.Many2one(
        'sim.shopify.payout', required=True, ondelete='cascade', index=True,
    )
    config_id = fields.Many2one(
        related='payout_id.config_id', store=True, index=True,
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)

    transaction_type = fields.Selection([
        ('CHARGE', 'Charge'),
        ('REFUND', 'Refund'),
        ('DISPUTE', 'Dispute'),
        ('RESERVE', 'Reserve'),
        ('ADJUSTMENT', 'Adjustment'),
        ('PAYOUT', 'Payout'),
    ], string='Type', required=True, default='CHARGE')

    amount = fields.Float(string='Amount')
    fee = fields.Float(string='Fee')
    net = fields.Float(string='Net')
    currency_code = fields.Char(string='Currency', default='USD')

    source_order_gid = fields.Char(
        string='Source Order GID',
        help='Shopify GID of the related order.',
    )
    processed_at = fields.Datetime(
        string='Processed At', default=fields.Datetime.now,
    )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if not rec.shopify_gid:
                config = rec.payout_id.config_id
                rec.shopify_gid = config._next_gid('ShopifyPaymentsPayoutTransaction')
        return records

    def _to_graphql_node(self):
        """Build GraphQL node for payout transaction."""
        def _money(amt):
            return {
                'amount': str(amt or 0.0),
                'currencyCode': self.currency_code or 'USD',
            }
        return {
            'id': self.shopify_gid,
            'type': self.transaction_type,
            'amount': _money(self.amount),
            'fee': _money(self.fee),
            'net': _money(self.net),
            'sourceOrderId': self.source_order_gid,
            'processedAt': self.processed_at.isoformat() + 'Z' if self.processed_at else None,
        }
