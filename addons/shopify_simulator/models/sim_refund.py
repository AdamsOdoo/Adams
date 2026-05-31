# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Refund and RefundLine models.

Simulates Shopify refund data returned by FETCH_REFUNDS and
created via the refundCreate mutation.

The response shape must match every field the connector's
FETCH_REFUNDS query requests (shopify_api/queries/refund.py):
  - refundLineItems.totalTaxSet
  - refundShippingLines (subtotalAmountSet + taxAmountSet)
  - orderAdjustments (amountSet + taxAmountSet + reason)
"""
import json
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _money_set(amount, currency='USD', presentment_currency=None):
    """Build a Shopify MoneyV2Set (shopMoney + presentmentMoney)."""
    return {
        'shopMoney': {
            'amount': str(amount),
            'currencyCode': currency,
        },
        'presentmentMoney': {
            'amount': str(amount),
            'currencyCode': presentment_currency or currency,
        },
    }


class SimShopifyRefund(models.Model):
    _name = 'sim.shopify.refund'
    _description = 'Simulated Shopify Refund'
    _order = 'create_date desc, id desc'

    config_id = fields.Many2one(
        'sim.shopify.config', required=True, ondelete='cascade', index=True,
    )
    order_id = fields.Many2one(
        'sim.shopify.order', required=True, ondelete='cascade', index=True,
        string='Order',
    )
    shopify_gid = fields.Char(string='Shopify GID', index=True, readonly=True)
    note = fields.Text(string='Refund Note')
    created_at = fields.Datetime(default=fields.Datetime.now, readonly=True)

    total_refunded = fields.Float(
        string='Total Refunded', default=0.0,
        help='Total amount refunded in shop currency.',
    )
    currency_code = fields.Char(default='USD')
    presentment_currency_code = fields.Char(default='USD')

    refund_line_ids = fields.One2many(
        'sim.shopify.refund.line', 'refund_id', string='Refund Lines',
    )

    # ── Shipping refund (inline — one shipping line per refund) ──
    shipping_refund_subtotal = fields.Float(
        string='Shipping Refund Subtotal', default=0.0,
        help='Shipping refund amount (pre-tax) in shop currency.',
    )
    shipping_refund_tax = fields.Float(
        string='Shipping Refund Tax', default=0.0,
        help='Tax on shipping refund in shop currency.',
    )

    # ── Order adjustments (JSON array) ──
    order_adjustments_json = fields.Text(
        string='Order Adjustments (JSON)',
        help='JSON array of {amount, tax_amount, reason} dicts. '
             'Each emits an orderAdjustment node in the FETCH_REFUNDS '
             'response.',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('shopify_gid'):
                config = self.env['sim.shopify.config'].browse(
                    vals.get('config_id')
                    or self.env['sim.shopify.order'].browse(
                        vals.get('order_id')
                    ).config_id.id
                )
                if config:
                    vals['shopify_gid'] = config._next_gid('Refund')
        return super().create(vals_list)

    def _to_graphql_node(self):
        """Return dict matching Shopify FETCH_REFUNDS response shape.

        Must include every field the connector's FETCH_REFUNDS query
        requests — see shopify_api/queries/refund.py.
        """
        self.ensure_one()
        cc = self.currency_code or 'USD'
        pc = self.presentment_currency_code or cc

        refund_line_edges = []
        for line in self.refund_line_ids:
            refund_line_edges.append({'node': line._to_graphql_node(cc, pc)})

        # refundShippingLines: only emit if there's a shipping refund
        shipping_edges = []
        if self.shipping_refund_subtotal or self.shipping_refund_tax:
            shipping_edges.append({
                'node': {
                    'subtotalAmountSet': _money_set(
                        self.shipping_refund_subtotal, cc, pc,
                    ),
                    'taxAmountSet': _money_set(
                        self.shipping_refund_tax, cc, pc,
                    ),
                },
            })

        # orderAdjustments: parse from JSON
        adjustments = []
        if self.order_adjustments_json:
            try:
                raw = json.loads(self.order_adjustments_json)
                for adj in raw:
                    adjustments.append({
                        'amountSet': _money_set(
                            float(adj.get('amount', 0)), cc, pc,
                        ),
                        'taxAmountSet': _money_set(
                            float(adj.get('tax_amount', 0)), cc, pc,
                        ),
                        'reason': adj.get('reason', 'other'),
                    })
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            'id': self.shopify_gid,
            'note': self.note or '',
            'createdAt': (
                self.created_at.isoformat() + 'Z' if self.created_at else ''
            ),
            'totalRefundedSet': _money_set(
                self.total_refunded, cc, pc,
            ),
            'refundLineItems': {
                'edges': refund_line_edges,
            },
            'refundShippingLines': {
                'edges': shipping_edges,
            },
            'orderAdjustments': adjustments,
        }


class SimShopifyRefundLine(models.Model):
    _name = 'sim.shopify.refund.line'
    _description = 'Simulated Shopify Refund Line Item'
    _order = 'id'

    refund_id = fields.Many2one(
        'sim.shopify.refund', required=True, ondelete='cascade', index=True,
    )
    # Link to the original order line item
    line_item_gid = fields.Char(
        string='Line Item GID',
        help='Shopify GID of the original order line item.',
    )
    line_item_title = fields.Char(string='Line Item Title')
    variant_gid = fields.Char(string='Variant GID')
    variant_sku = fields.Char(string='Variant SKU')
    quantity = fields.Integer(default=1, string='Quantity Refunded')
    restock_type = fields.Selection([
        ('NO_RESTOCK', 'No Restock'),
        ('CANCEL', 'Cancel'),
        ('RETURN', 'Return'),
    ], default='NO_RESTOCK', string='Restock Type')
    subtotal = fields.Float(
        default=0.0, string='Subtotal',
        help='Refund amount for this line in shop currency.',
    )
    tax_amount = fields.Float(
        default=0.0, string='Tax Amount',
        help='Tax refunded for this line in shop currency.',
    )

    def _to_graphql_node(self, currency='USD', presentment_currency='USD'):
        """Return dict matching Shopify refundLineItem node shape."""
        self.ensure_one()
        variant_node = None
        if self.variant_gid:
            variant_node = {
                'id': self.variant_gid,
                'sku': self.variant_sku or '',
            }

        return {
            'lineItem': {
                'id': self.line_item_gid or '',
                'title': self.line_item_title or '',
                'variant': variant_node,
            },
            'quantity': self.quantity,
            'restockType': self.restock_type or 'NO_RESTOCK',
            'subtotalSet': _money_set(
                self.subtotal, currency, presentment_currency,
            ),
            'totalTaxSet': _money_set(
                self.tax_amount, currency, presentment_currency,
            ),
        }
