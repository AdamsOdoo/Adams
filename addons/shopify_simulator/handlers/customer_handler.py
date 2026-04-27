# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for customer queries and mutations."""
from .base_handler import paginate_records, build_mutation_response


def handle_fetch_customers(env, config, variables):
    """FETCH_CUSTOMERS query — paginated customer list."""
    first = variables.get('first', 50)
    after = variables.get('after')
    customers = env['sim.shopify.customer'].search(
        [('config_id', '=', config.id)],
        order='id asc',
    )
    return {'customers': paginate_records(customers, first, after)}


def handle_fetch_single_customer(env, config, variables):
    """Single customer query — fetch by GID (used by webhook re-fetch)."""
    customer_gid = variables.get('id', '')
    customer = env['sim.shopify.customer'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', customer_gid),
    ], limit=1)

    if not customer:
        return {'customer': None}

    return {'customer': customer._to_graphql_node()}


def handle_customer_create(env, config, variables):
    """CUSTOMER_CREATE_MUTATION."""
    inp = variables.get('input', {})
    vals = {
        'config_id': config.id,
        'first_name': inp.get('firstName', ''),
        'last_name': inp.get('lastName', ''),
        'email': inp.get('email', ''),
        'phone': inp.get('phone', ''),
        'tags': ','.join(inp.get('tags', [])) if isinstance(inp.get('tags'), list) else inp.get('tags', ''),
    }
    # Handle address
    addresses = inp.get('addresses', [])
    if addresses:
        addr = addresses[0]
        vals.update({
            'address1': addr.get('address1', ''),
            'address2': addr.get('address2', ''),
            'city': addr.get('city', ''),
            'province': addr.get('province', ''),
            'province_code': addr.get('provinceCode', ''),
            'country': addr.get('country', ''),
            'country_code': addr.get('countryCode', ''),
            'zip_code': addr.get('zip', ''),
        })

    customer = env['sim.shopify.customer'].create(vals)
    return build_mutation_response('customerCreate', {
        'customer': {
            'id': customer.shopify_gid,
            'email': customer.email or '',
        },
    })


def handle_customer_update(env, config, variables):
    """CUSTOMER_UPDATE_MUTATION."""
    inp = variables.get('input', {})
    customer_id = inp.get('id', '')

    customer = env['sim.shopify.customer'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', customer_id),
    ], limit=1)

    if not customer:
        return build_mutation_response('customerUpdate', {
            'customer': None,
        }, [
            {'field': ['id'], 'message': f'Customer not found: {customer_id}'},
        ])

    update_vals = {}
    if 'firstName' in inp:
        update_vals['first_name'] = inp['firstName']
    if 'lastName' in inp:
        update_vals['last_name'] = inp['lastName']
    if 'email' in inp:
        update_vals['email'] = inp['email']
    if 'phone' in inp:
        update_vals['phone'] = inp['phone']
    if 'tags' in inp:
        tags = inp['tags']
        update_vals['tags'] = ','.join(tags) if isinstance(tags, list) else tags

    if update_vals:
        customer.write(update_vals)

    return build_mutation_response('customerUpdate', {
        'customer': {
            'id': customer.shopify_gid,
            'email': customer.email or '',
            'firstName': customer.first_name or '',
            'lastName': customer.last_name or '',
        },
    })
