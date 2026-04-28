# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for collection queries and mutations."""
from .base_handler import paginate_records, build_mutation_response


def handle_fetch_collections(env, config, variables):
    """FETCH_COLLECTIONS query — paginated collection list."""
    first = variables.get('first', 50)
    after = variables.get('after')
    collections = env['sim.shopify.collection'].search(
        [('config_id', '=', config.id)],
        order='title asc, id asc',
    )
    return {'collections': paginate_records(collections, first, after)}


def handle_collection_create(env, config, variables):
    """collectionCreate mutation."""
    inp = variables.get('input', {})
    vals = {
        'config_id': config.id,
        'title': inp.get('title', 'Untitled Collection'),
        'description_html': inp.get('descriptionHtml', ''),
        'sort_order': inp.get('sortOrder', 'MANUAL'),
    }
    if inp.get('handle'):
        vals['handle'] = inp['handle']

    collection = env['sim.shopify.collection'].create(vals)

    # Link products if specified
    product_gids = inp.get('products', [])
    if product_gids:
        products = env['sim.shopify.product'].search([
            ('config_id', '=', config.id),
            ('shopify_gid', 'in', product_gids),
        ])
        if products:
            collection.write({'product_ids': [(6, 0, products.ids)]})

    return build_mutation_response('collectionCreate', {
        'collection': collection._to_graphql_node(),
    })
