# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for refund-related queries and mutations.

Covers:
- FETCH_REFUNDS (query)   — returns refunds for a given order
- refundCreate (mutation)  — create a refund on an order
"""
import logging

from .base_handler import build_mutation_response

_logger = logging.getLogger(__name__)


def handle_fetch_refunds(env, config, variables):
    """FETCH_REFUNDS query — returns all refunds for a given order.

    The connector sends: {'orderId': 'gid://shopify/Order/...'}
    Response shape matches the FETCH_REFUNDS query in refund.py.
    """
    order_gid = variables.get('orderId', '')
    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_gid),
    ], limit=1)

    if not order:
        return {'order': None}

    refunds = env['sim.shopify.refund'].search([
        ('order_id', '=', order.id),
    ], order='id asc')

    refund_nodes = [r._to_graphql_node() for r in refunds]

    return {
        'order': {
            'refunds': refund_nodes,
        },
    }


def handle_refund_create(env, config, variables):
    """refundCreate mutation.

    Accepts the same RefundInput structure the connector sends:
    {
      'input': {
        'orderId': 'gid://shopify/Order/...',
        'note': '...',
        'shipping': {'amount': 0.0, 'fullRefund': False},
        'transactions': [
          {'amount': 50.0, 'gateway': 'manual', 'kind': 'REFUND',
           'orderId': 'gid://shopify/Order/...'}
        ],
      }
    }
    """
    inp = variables.get('input', {})
    order_gid = inp.get('orderId', '')

    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_gid),
    ], limit=1)

    if not order:
        return build_mutation_response('refundCreate', {
            'refund': None,
        }, [
            {'field': ['orderId'], 'message': f'Order not found: {order_gid}'},
        ])

    # Compute total refund amount from transactions
    total_refund = 0.0
    for txn in inp.get('transactions', []):
        total_refund += float(txn.get('amount', 0) or 0)

    # Add shipping refund amount if provided
    shipping = inp.get('shipping', {})
    if shipping:
        if shipping.get('fullRefund'):
            total_refund += order.total_shipping
        elif shipping.get('amount'):
            total_refund += float(shipping['amount'])

    cc = order.currency_code or 'USD'
    pc = order.presentment_currency_code or cc

    refund = env['sim.shopify.refund'].create({
        'config_id': config.id,
        'order_id': order.id,
        'note': inp.get('note', ''),
        'total_refunded': total_refund,
        'currency_code': cc,
        'presentment_currency_code': pc,
    })

    # Update order financial status
    if total_refund >= order.total_price:
        order.write({'financial_status': 'REFUNDED'})
    elif total_refund > 0:
        order.write({'financial_status': 'PARTIALLY_REFUNDED'})

    # Fire webhook if registered
    env['sim.shopify.webhook.subscription']._fire_webhook(
        config, 'refunds/create',
        _build_refund_webhook_payload(refund, order),
    )

    return build_mutation_response('refundCreate', {
        'refund': {
            'id': refund.shopify_gid,
            'totalRefundedSet': {
                'shopMoney': {
                    'amount': str(total_refund),
                    'currencyCode': cc,
                },
            },
        },
    })


def _build_refund_webhook_payload(refund, order):
    """Build REST-format webhook payload for refunds/create."""
    gid = refund.shopify_gid or ''
    numeric_id = gid.split('/')[-1] if '/' in gid else gid

    order_gid = order.shopify_gid or ''
    order_numeric_id = order_gid.split('/')[-1] if '/' in order_gid else order_gid

    return {
        'id': int(numeric_id) if numeric_id.isdigit() else 0,
        'order_id': int(order_numeric_id) if order_numeric_id.isdigit() else 0,
        'note': refund.note or '',
        'created_at': (
            refund.created_at.isoformat() + 'Z' if refund.created_at else ''
        ),
    }
