# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for discount code queries and mutations."""
from .base_handler import paginate_records, build_mutation_response


def handle_fetch_discount_codes(env, config, variables):
    """codeDiscountNodes query — paginated discount code list."""
    first = variables.get('first', 50)
    after = variables.get('after')
    codes = env['sim.shopify.discount.code'].search(
        [('config_id', '=', config.id)],
        order='code asc',
    )
    return {'codeDiscountNodes': paginate_records(codes, first, after)}


def _create_or_update_discount(env, config, variables, mutation_key):
    """Shared logic for creating/updating discount codes."""
    inp = variables.get('basicCodeDiscount', variables.get('freeShippingCodeDiscount', {}))
    code_val = inp.get('code', '')
    title = inp.get('title', code_val)

    # Determine type
    is_free_shipping = 'freeShipping' in mutation_key.lower()
    discount_type = 'free_shipping' if is_free_shipping else 'percentage'
    discount_value = 0.0

    if not is_free_shipping:
        customer_gets = inp.get('customerGets', {})
        value_data = customer_gets.get('value', {})
        if 'percentage' in value_data:
            discount_type = 'percentage'
            discount_value = float(value_data.get('percentage', 0)) * 100
        elif 'discountAmount' in value_data:
            discount_type = 'fixed_amount'
            amount_data = value_data.get('discountAmount', {}).get('amount', {})
            discount_value = float(amount_data.get('amount', 0) if isinstance(amount_data, dict) else amount_data)

    # Minimum requirement
    min_amount = 0.0
    min_req = inp.get('minimumRequirement', {})
    subtotal = min_req.get('subtotal', {})
    if subtotal:
        min_amount = float(subtotal.get('greaterThanOrEqualToSubtotal', 0))

    vals = {
        'config_id': config.id,
        'code': code_val,
        'title': title,
        'discount_type': discount_type,
        'discount_value': discount_value,
        'minimum_order_amount': min_amount,
        'one_per_customer': inp.get('appliesOncePerCustomer', False),
        'active_on_shopify': True,
    }

    if inp.get('usageLimit'):
        vals['usage_limit'] = int(inp['usageLimit'])
    if inp.get('startsAt'):
        vals['starts_at'] = inp['startsAt']
    if inp.get('endsAt'):
        vals['ends_at'] = inp['endsAt']

    return vals


def handle_discount_basic_create(env, config, variables):
    """discountCodeBasicCreate mutation."""
    vals = _create_or_update_discount(env, config, variables, 'basic')
    discount = env['sim.shopify.discount.code'].create(vals)
    return build_mutation_response('discountCodeBasicCreate', {
        'codeDiscountNode': discount._to_graphql_node(),
    })


def handle_discount_basic_update(env, config, variables):
    """discountCodeBasicUpdate mutation."""
    gid = variables.get('id', '')
    discount = env['sim.shopify.discount.code'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', gid),
    ], limit=1)

    if not discount:
        return build_mutation_response('discountCodeBasicUpdate', {
            'codeDiscountNode': None,
        }, user_errors=[{'field': ['id'], 'message': 'Discount not found'}])

    vals = _create_or_update_discount(env, config, variables, 'basic')
    vals.pop('config_id', None)
    discount.write(vals)
    return build_mutation_response('discountCodeBasicUpdate', {
        'codeDiscountNode': discount._to_graphql_node(),
    })


def handle_discount_fs_create(env, config, variables):
    """discountCodeFreeShippingCreate mutation."""
    vals = _create_or_update_discount(env, config, variables, 'freeShipping')
    vals['discount_type'] = 'free_shipping'
    discount = env['sim.shopify.discount.code'].create(vals)
    return build_mutation_response('discountCodeFreeShippingCreate', {
        'codeDiscountNode': discount._to_graphql_node(),
    })


def handle_discount_fs_update(env, config, variables):
    """discountCodeFreeShippingUpdate mutation."""
    gid = variables.get('id', '')
    discount = env['sim.shopify.discount.code'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', gid),
    ], limit=1)

    if not discount:
        return build_mutation_response('discountCodeFreeShippingUpdate', {
            'codeDiscountNode': None,
        }, user_errors=[{'field': ['id'], 'message': 'Discount not found'}])

    vals = _create_or_update_discount(env, config, variables, 'freeShipping')
    vals.pop('config_id', None)
    vals['discount_type'] = 'free_shipping'
    discount.write(vals)
    return build_mutation_response('discountCodeFreeShippingUpdate', {
        'codeDiscountNode': discount._to_graphql_node(),
    })


def handle_discount_delete(env, config, variables):
    """discountCodeDelete mutation."""
    gid = variables.get('id', '')
    discount = env['sim.shopify.discount.code'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', gid),
    ], limit=1)

    deleted_id = gid
    if discount:
        discount.unlink()

    return build_mutation_response('discountCodeDelete', {
        'deletedCodeDiscountId': deleted_id,
    })
