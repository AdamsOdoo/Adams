# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for order queries and mutations."""
from .base_handler import paginate_records, build_mutation_response


def handle_fetch_orders(env, config, variables):
    """FETCH_ORDERS query — paginated order list with optional query filter."""
    first = variables.get('first', 50)
    after = variables.get('after')
    query_filter = variables.get('query', '')

    domain = [('config_id', '=', config.id)]

    # Parse basic Shopify query filters
    if query_filter:
        # Support: updated_at:>'2024-01-01' and financial_status:paid
        if 'financial_status:' in query_filter:
            parts = query_filter.split('financial_status:')
            if len(parts) > 1:
                status = parts[1].strip().split()[0].upper()
                domain.append(('financial_status', '=', status))

    orders = env['sim.shopify.order'].search(domain, order='id asc')
    return {'orders': paginate_records(orders, first, after)}


def handle_fetch_single_order(env, config, variables):
    """Single order query — fetch order by GID (used by webhook re-fetch)."""
    order_gid = variables.get('id', '')
    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_gid),
    ], limit=1)

    if not order:
        return {'order': None}

    return {'order': order._to_graphql_node()}


def handle_order_update(env, config, variables):
    """ORDER_UPDATE_MUTATION — update order tags and notes."""
    inp = variables.get('input', {})
    order_id = inp.get('id', '')

    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_id),
    ], limit=1)

    if not order:
        return build_mutation_response('orderUpdate', {
            'order': None,
        }, [
            {'field': ['id'], 'message': f'Order not found: {order_id}'},
        ])

    update_vals = {}
    if 'note' in inp:
        update_vals['note'] = inp['note']
    if 'tags' in inp:
        tags = inp['tags']
        update_vals['tags'] = ','.join(tags) if isinstance(tags, list) else tags

    if update_vals:
        order.write(update_vals)

    return build_mutation_response('orderUpdate', {
        'order': {
            'id': order.shopify_gid,
            'tags': [t.strip() for t in (order.tags or '').split(',') if t.strip()],
            'note': order.note or '',
        },
    })


def handle_order_mark_as_paid(env, config, variables):
    """orderMarkAsPaid mutation — mark an order as paid.

    The connector sends: {'input': {'id': 'gid://shopify/Order/...'}}
    """
    inp = variables.get('input', {})
    order_gid = inp.get('id', '')

    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_gid),
    ], limit=1)

    if not order:
        return build_mutation_response('orderMarkAsPaid', {
            'order': None,
        }, [
            {'field': ['id'], 'message': f'Order not found: {order_gid}'},
        ])

    # Only mark as paid if currently pending/authorized
    if order.financial_status in ('PENDING', 'AUTHORIZED'):
        order.write({'financial_status': 'PAID'})

    return build_mutation_response('orderMarkAsPaid', {
        'order': {
            'id': order.shopify_gid,
            'displayFinancialStatus': order.financial_status,
        },
    })
