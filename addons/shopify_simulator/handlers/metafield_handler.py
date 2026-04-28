# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for metafield queries and mutations."""
from .base_handler import paginate_records, build_mutation_response


def handle_fetch_product_metafields(env, config, variables):
    """Fetch metafields for a specific product."""
    product_id = variables.get('id', '')
    first = variables.get('first', 50)
    after = variables.get('after')

    metafields = env['sim.shopify.metafield'].search([
        ('config_id', '=', config.id),
        ('owner_type', '=', 'PRODUCT'),
        ('owner_gid', '=', product_id),
    ])

    # Return product node with nested metafields connection
    product = env['sim.shopify.product'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', product_id),
    ], limit=1)

    product_node = product._to_graphql_node() if product else {'id': product_id}
    product_node['metafields'] = paginate_records(metafields, first, after)

    return {'product': product_node}


def handle_metafield_set(env, config, variables):
    """metafieldsSet mutation — create or update metafields."""
    metafield_inputs = variables.get('metafields', [])
    created_or_updated = []

    Metafield = env['sim.shopify.metafield']

    for mf in metafield_inputs:
        owner_id = mf.get('ownerId', '')
        namespace = mf.get('namespace', '')
        key = mf.get('key', '')
        value = mf.get('value', '')
        mf_type = mf.get('type', 'single_line_text_field')

        # Determine owner_type from GID
        owner_type = 'PRODUCT'
        if '/ProductVariant/' in owner_id:
            owner_type = 'PRODUCTVARIANT'
        elif '/Customer/' in owner_id:
            owner_type = 'CUSTOMER'
        elif '/Order/' in owner_id:
            owner_type = 'ORDER'

        # Upsert: find existing or create
        existing = Metafield.search([
            ('config_id', '=', config.id),
            ('owner_gid', '=', owner_id),
            ('namespace', '=', namespace),
            ('key', '=', key),
        ], limit=1)

        if existing:
            existing.write({
                'value': value,
                'metafield_type': mf_type,
            })
            created_or_updated.append(existing)
        else:
            record = Metafield.create({
                'config_id': config.id,
                'owner_type': owner_type,
                'owner_gid': owner_id,
                'namespace': namespace,
                'key': key,
                'value': value,
                'metafield_type': mf_type,
            })
            created_or_updated.append(record)

    nodes = [mf._to_graphql_node() for mf in created_or_updated]
    return build_mutation_response('metafieldsSet', {
        'metafields': nodes,
    })


def handle_metafield_delete(env, config, variables):
    """metafieldDelete mutation."""
    inp = variables.get('input', {})
    metafield_id = inp.get('id', '')

    metafield = env['sim.shopify.metafield'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', metafield_id),
    ], limit=1)

    if metafield:
        metafield.unlink()

    return build_mutation_response('metafieldDelete', {
        'deletedId': metafield_id,
    })
