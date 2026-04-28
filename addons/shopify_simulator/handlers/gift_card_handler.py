# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handler for gift card queries."""
from .base_handler import paginate_records


def handle_fetch_gift_cards(env, config, variables):
    """FETCH_GIFT_CARDS query — paginated gift card list."""
    first = variables.get('first', 50)
    after = variables.get('after')
    gift_cards = env['sim.shopify.gift.card'].search(
        [('config_id', '=', config.id)],
        order='created_at desc, id desc',
    )
    return {'giftCards': paginate_records(gift_cards, first, after)}
