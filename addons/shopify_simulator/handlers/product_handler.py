# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for product queries and mutations."""
import logging

from .base_handler import paginate_records, build_mutation_response

_logger = logging.getLogger(__name__)


def handle_fetch_products(env, config, variables):
    """FETCH_PRODUCTS query — paginated product list."""
    first = variables.get('first', 50)
    after = variables.get('after')
    products = env['sim.shopify.product'].search(
        [('config_id', '=', config.id)],
        order='id asc',
    )
    return {'products': paginate_records(products, first, after)}


def handle_fetch_single_product(env, config, variables):
    """Fetch single product by ID (used in webhook handler)."""
    product_id = variables.get('id', '')
    product = env['sim.shopify.product'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', product_id),
    ], limit=1)
    if not product:
        return {'product': None}
    node = product._to_graphql_node()
    # Single product queries include images in a slightly different shape
    return {'product': node}


def handle_product_set(env, config, variables):
    """PRODUCT_SET_MUTATION — create product with variants."""
    inp = variables.get('input', {})
    product_input = inp if 'title' in inp else inp.get('productSet', inp)

    vals = {
        'config_id': config.id,
        'title': product_input.get('title', 'Untitled'),
        'description_html': product_input.get('descriptionHtml', ''),
        'product_type': product_input.get('productType', ''),
        'vendor': product_input.get('vendor', ''),
        'status': product_input.get('status', 'ACTIVE'),
        'tags': ','.join(product_input.get('tags', [])) if isinstance(product_input.get('tags'), list) else product_input.get('tags', ''),
    }
    if product_input.get('handle'):
        vals['handle'] = product_input['handle']

    product = env['sim.shopify.product'].create(vals)

    # Process variants
    variant_inputs = product_input.get('variants', [])
    if variant_inputs:
        # Delete auto-created default variant
        product.variant_ids.unlink()
        for vi in variant_inputs:
            v_vals = {
                'product_id': product.id,
                'title': vi.get('optionValues', [{}])[0].get('name', 'Default Title') if vi.get('optionValues') else 'Default Title',
                'sku': vi.get('sku', ''),
                'barcode': vi.get('barcode', ''),
                'price': str(vi.get('price', '0.00')),
                'compare_at_price': str(vi.get('compareAtPrice', '')) if vi.get('compareAtPrice') else '',
            }
            # Handle options
            option_values = vi.get('optionValues', [])
            if len(option_values) >= 1:
                v_vals['option1_name'] = option_values[0].get('optionName', 'Title')
                v_vals['option1_value'] = option_values[0].get('name', 'Default')
            if len(option_values) >= 2:
                v_vals['option2_name'] = option_values[1].get('optionName', '')
                v_vals['option2_value'] = option_values[1].get('name', '')
            env['sim.shopify.variant'].create(v_vals)

    # Build response
    node = product._to_graphql_node()
    return build_mutation_response('productSet', {'product': node})


def handle_product_update(env, config, variables):
    """PRODUCT_UPDATE_MUTATION — update product metadata."""
    inp = variables.get('input', {})
    product_id = inp.get('id', '')

    product = env['sim.shopify.product'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', product_id),
    ], limit=1)

    if not product:
        return build_mutation_response('productUpdate', {'product': None}, [
            {'field': ['id'], 'message': f'Product not found: {product_id}'},
        ])

    update_vals = {}
    if 'title' in inp:
        update_vals['title'] = inp['title']
    if 'descriptionHtml' in inp:
        update_vals['description_html'] = inp['descriptionHtml']
    if 'productType' in inp:
        update_vals['product_type'] = inp['productType']
    if 'tags' in inp:
        tags = inp['tags']
        update_vals['tags'] = ','.join(tags) if isinstance(tags, list) else tags
    if 'status' in inp:
        update_vals['status'] = inp['status']

    if update_vals:
        product.write(update_vals)

    node = product._to_graphql_node()
    return build_mutation_response('productUpdate', {'product': node})


def handle_variant_bulk_update(env, config, variables):
    """VARIANT_BULK_UPDATE_MUTATION — bulk update variant SKUs/prices."""
    product_id = variables.get('productId', '')
    variant_inputs = variables.get('variants', [])

    product = env['sim.shopify.product'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', product_id),
    ], limit=1)

    if not product:
        return build_mutation_response('productVariantsBulkUpdate', {
            'productVariants': [],
        }, [
            {'field': ['productId'], 'message': f'Product not found: {product_id}'},
        ])

    updated_variants = []
    for vi in variant_inputs:
        variant_gid = vi.get('id', '')
        variant = env['sim.shopify.variant'].search([
            ('product_id', '=', product.id),
            ('shopify_gid', '=', variant_gid),
        ], limit=1)
        if variant:
            update = {}
            if 'price' in vi:
                update['price'] = str(vi['price'])
            if 'sku' in vi:
                update['sku'] = vi['sku']
            if 'barcode' in vi:
                update['barcode'] = vi['barcode']
            if update:
                variant.write(update)
            updated_variants.append({
                'id': variant.shopify_gid,
                'sku': variant.sku or '',
                'price': variant.price or '0.00',
            })

    return build_mutation_response('productVariantsBulkUpdate', {
        'productVariants': updated_variants,
    })
