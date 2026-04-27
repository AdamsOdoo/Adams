# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""Handlers for fulfillment-related queries and mutations.

Covers:
- GetFulfillmentOrders (query)  — used by push_fulfillment before creating
- GetOrderStatus (query)        — fetch displayFulfillmentStatus
- GetOrderFulfillments (query)  — full fulfillment data for an order
- fulfillmentCreate (mutation)  — create a fulfillment from fulfillment order lines
"""
import json
import logging

from .base_handler import build_mutation_response

_logger = logging.getLogger(__name__)


def handle_fetch_fulfillment_orders(env, config, variables):
    """GetFulfillmentOrders query — returns fulfillment orders for an order.

    Used by the connector's push_fulfillment() to discover what lines
    remain to be fulfilled.
    """
    order_gid = variables.get('id', '')
    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_gid),
    ], limit=1)

    if not order:
        return {'order': None}

    fo_records = env['sim.shopify.fulfillment.order'].search([
        ('order_id', '=', order.id),
    ], order='id asc')

    fo_edges = []
    for fo in fo_records:
        fo_edges.append({'node': fo._to_graphql_node()})

    return {
        'order': {
            'fulfillmentOrders': {
                'edges': fo_edges,
            },
        },
    }


def handle_get_order_status(env, config, variables):
    """GetOrderStatus query — returns displayFulfillmentStatus for an order."""
    order_gid = variables.get('id', '')
    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_gid),
    ], limit=1)

    if not order:
        return {'order': None}

    return {
        'order': {
            'displayFulfillmentStatus': order.fulfillment_status or 'UNFULFILLED',
        },
    }


def handle_fetch_order_fulfillments(env, config, variables):
    """GetOrderFulfillments query — returns full fulfillment data for an order.

    This matches the FETCH_ORDER_FULFILLMENTS query structure used by the
    connector's FulfillmentSync when importing fulfillment data.
    """
    order_gid = variables.get('id', '')
    order = env['sim.shopify.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', order_gid),
    ], limit=1)

    if not order:
        return {'order': None}

    # Fulfillment orders
    fo_records = env['sim.shopify.fulfillment.order'].search([
        ('order_id', '=', order.id),
    ], order='id asc')
    fo_edges = [{'node': fo._to_graphql_node()} for fo in fo_records]

    # Fulfillments
    fulfillments = env['sim.shopify.fulfillment'].search([
        ('order_id', '=', order.id),
    ], order='id asc')
    fulfillment_nodes = [f._to_graphql_node() for f in fulfillments]

    return {
        'order': {
            'displayFulfillmentStatus': order.fulfillment_status or 'UNFULFILLED',
            'fulfillmentOrders': {
                'edges': fo_edges,
            },
            'fulfillments': fulfillment_nodes,
        },
    }


def handle_fulfillment_create(env, config, variables):
    """fulfillmentCreate mutation.

    Accepts the same FulfillmentInput structure the connector sends:
    {
      'fulfillment': {
        'lineItemsByFulfillmentOrder': [
          {
            'fulfillmentOrderId': 'gid://shopify/FulfillmentOrder/...',
            'fulfillmentOrderLineItems': [
              {'id': 'gid://shopify/FulfillmentOrderLineItem/...', 'quantity': N},
            ],
          },
        ],
        'trackingInfo': {'number': '...', 'url': '...', 'company': '...'},
      }
    }
    """
    fulfillment_input = variables.get('fulfillment', {})
    line_items_by_fo = fulfillment_input.get('lineItemsByFulfillmentOrder', [])
    tracking_info = fulfillment_input.get('trackingInfo', {})

    if not line_items_by_fo:
        return build_mutation_response('fulfillmentCreate', {
            'fulfillment': None,
        }, [
            {'field': ['fulfillment'], 'message': 'No fulfillment order lines provided'},
        ])

    # Find the order from the first fulfillment order
    first_fo_gid = line_items_by_fo[0].get('fulfillmentOrderId', '')
    fo_record = env['sim.shopify.fulfillment.order'].search([
        ('config_id', '=', config.id),
        ('shopify_gid', '=', first_fo_gid),
    ], limit=1)

    if not fo_record:
        return build_mutation_response('fulfillmentCreate', {
            'fulfillment': None,
        }, [
            {'field': ['fulfillmentOrderId'],
             'message': f'FulfillmentOrder not found: {first_fo_gid}'},
        ])

    order = fo_record.order_id

    # Process each fulfillment order's line items
    all_fulfilled_lines = []
    for fo_block in line_items_by_fo:
        fo_gid = fo_block.get('fulfillmentOrderId', '')
        fo = env['sim.shopify.fulfillment.order'].search([
            ('config_id', '=', config.id),
            ('shopify_gid', '=', fo_gid),
        ], limit=1)
        if not fo:
            continue

        for li_input in fo_block.get('fulfillmentOrderLineItems', []):
            li_gid = li_input.get('id', '')
            qty = li_input.get('quantity', 0)

            fo_line = env['sim.shopify.fulfillment.order.line'].search([
                ('fulfillment_order_id', '=', fo.id),
                ('shopify_gid', '=', li_gid),
            ], limit=1)

            if not fo_line:
                continue

            # Decrease remaining quantity
            new_remaining = max(0, fo_line.remaining_quantity - qty)
            fo_line.write({'remaining_quantity': new_remaining})

            all_fulfilled_lines.append({
                'lineItemId': fo_line.order_line_id.shopify_gid if fo_line.order_line_id else li_gid,
                'quantity': qty,
                'title': fo_line.title or '',
                'variantId': fo_line.variant_gid or '',
                'sku': fo_line.sku or '',
            })

        # Check if all lines are fully fulfilled → close the FO
        all_done = all(
            line.remaining_quantity <= 0 for line in fo.line_item_ids
        )
        if all_done:
            fo.write({'status': 'CLOSED'})

    # Create the fulfillment record
    fulfillment = env['sim.shopify.fulfillment'].create({
        'config_id': config.id,
        'order_id': order.id,
        'tracking_number': tracking_info.get('number', ''),
        'tracking_company': tracking_info.get('company', ''),
        'tracking_url': tracking_info.get('url', ''),
        'line_items_json': json.dumps(all_fulfilled_lines),
    })

    # Update order fulfillment status
    _update_order_fulfillment_status(env, order)

    # Fire webhook if registered
    env['sim.shopify.webhook.subscription']._fire_webhook(
        config, 'fulfillments/create',
        _build_fulfillment_webhook_payload(fulfillment, order),
    )

    tracking_info_list = []
    if tracking_info.get('number'):
        tracking_info_list.append({
            'number': tracking_info.get('number', ''),
            'url': tracking_info.get('url', ''),
            'company': tracking_info.get('company', ''),
        })

    return build_mutation_response('fulfillmentCreate', {
        'fulfillment': {
            'id': fulfillment.shopify_gid,
            'status': fulfillment.status,
            'trackingInfo': tracking_info_list,
        },
    })


def _update_order_fulfillment_status(env, order):
    """Recompute order fulfillment status based on fulfillment order states."""
    fo_records = env['sim.shopify.fulfillment.order'].search([
        ('order_id', '=', order.id),
    ])
    if not fo_records:
        return

    all_closed = all(fo.status == 'CLOSED' for fo in fo_records)

    if all_closed:
        order.write({'fulfillment_status': 'FULFILLED'})
        return

    # Check if any line has been partially fulfilled
    any_partially_fulfilled = False
    for fo in fo_records:
        for line in fo.line_item_ids:
            if line.remaining_quantity < line.total_quantity:
                any_partially_fulfilled = True
                break
        if any_partially_fulfilled:
            break

    if any_partially_fulfilled:
        order.write({'fulfillment_status': 'PARTIALLY_FULFILLED'})


def _build_fulfillment_webhook_payload(fulfillment, order):
    """Build REST-format webhook payload for fulfillments/create."""
    # Extract numeric ID from GID
    gid = fulfillment.shopify_gid or ''
    numeric_id = gid.split('/')[-1] if '/' in gid else gid

    order_gid = order.shopify_gid or ''
    order_numeric_id = order_gid.split('/')[-1] if '/' in order_gid else order_gid

    return {
        'id': int(numeric_id) if numeric_id.isdigit() else 0,
        'order_id': int(order_numeric_id) if order_numeric_id.isdigit() else 0,
        'status': (fulfillment.status or 'success').lower(),
        'tracking_number': fulfillment.tracking_number or None,
        'tracking_company': fulfillment.tracking_company or None,
        'tracking_url': fulfillment.tracking_url or None,
    }
