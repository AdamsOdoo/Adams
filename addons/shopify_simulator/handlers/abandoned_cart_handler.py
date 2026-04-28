# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handler for abandoned cart (checkout) queries."""
from .base_handler import paginate_records


def handle_fetch_abandoned_checkouts(env, config, variables):
    """FETCH_ABANDONED_CHECKOUTS query — paginated list."""
    first = variables.get('first', 50)
    after = variables.get('after')
    carts = env['sim.shopify.abandoned.cart'].search(
        [('config_id', '=', config.id)],
        order='abandoned_at desc, id desc',
    )
    return {'abandonedCheckouts': paginate_records(carts, first, after)}
