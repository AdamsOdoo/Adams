# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for payout and payout transaction queries."""
from .base_handler import paginate_records


def handle_fetch_payouts(env, config, variables):
    """Fetch payouts via shopifyPaymentsAccount.payouts."""
    first = variables.get('first', 50)
    after = variables.get('after')
    payouts = env['sim.shopify.payout'].search(
        [('config_id', '=', config.id)],
        order='payout_date desc, id desc',
    )
    return {
        'shopifyPaymentsAccount': {
            'payouts': paginate_records(payouts, first, after),
        },
    }


def handle_fetch_payout_transactions(env, config, variables):
    """Fetch payout transactions via shopifyPaymentsAccount.payoutTransactions."""
    first = variables.get('first', 50)
    after = variables.get('after')
    transactions = env['sim.shopify.payout.transaction'].search(
        [('config_id', '=', config.id)],
        order='processed_at desc, id desc',
    )
    return {
        'shopifyPaymentsAccount': {
            'payoutTransactions': paginate_records(transactions, first, after),
        },
    }
