# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handler for location query."""
from .base_handler import paginate_records


def handle_fetch_locations(env, config, variables):
    """FETCH_LOCATIONS query — paginated location list."""
    first = variables.get('first', 50)
    after = variables.get('after')
    locations = env['sim.shopify.location'].search(
        [('config_id', '=', config.id)],
        order='is_primary desc, id asc',
    )
    return {'locations': paginate_records(locations, first, after)}
