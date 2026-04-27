# Part of Shopify Simulator. Internal QA tool — not for public distribution.
"""
Main GraphQL endpoint controller.

Receives POST requests from ShopifyClient / SimulatorClient and dispatches
to the appropriate handler based on regex matching of the query text.
"""
import json
import logging
import os
import random
import re
import time

from odoo import http
from odoo.http import request

from ..handlers.base_handler import build_response, build_error_response
from ..handlers import (
    shop_handler,
    product_handler,
    customer_handler,
    order_handler,
    inventory_handler,
    location_handler,
    fulfillment_handler,
    refund_handler,
    webhook_handler,
)

_logger = logging.getLogger(__name__)

_RUNNING_ENV = os.environ.get('RUNNING_ENV', os.environ.get('ODOO_STAGE', 'dev'))

# ── Dispatch tables ───────────────────────────────────────
# Ordered: more specific patterns first to avoid ambiguity.

QUERY_DISPATCH = [
    # Payout transactions must match before payouts (both contain shopifyPaymentsAccount)
    (re.compile(r'shopifyPaymentsAccount.*payoutTransactions', re.DOTALL), 'payout_transactions'),
    (re.compile(r'shopifyPaymentsAccount.*payouts', re.DOTALL), 'payouts'),
    # Order sub-queries
    (re.compile(r'order\s*\(.*refunds', re.DOTALL), 'refunds'),
    (re.compile(r'order\s*\(.*fulfillment', re.DOTALL), 'fulfillments'),
    # Product sub-queries
    (re.compile(r'product\s*\(.*metafields', re.DOTALL), 'product_metafields'),
    # Single-resource queries (webhook re-fetch)
    (re.compile(r'query\s+\w*\s*\(\s*\$id\s*:\s*ID!\s*\)\s*\{\s*product\s*\('), 'single_product'),
    (re.compile(r'query\s+\w*\s*\(\s*\$id\s*:\s*ID!\s*\)\s*\{\s*customer\s*\('), 'single_customer'),
    (re.compile(r'query\s+\w*\s*\(\s*\$id\s*:\s*ID!\s*\)\s*\{\s*order\s*\('), 'single_order'),
    # Paginated list queries
    (re.compile(r'products\s*\('), 'products'),
    (re.compile(r'orders\s*\('), 'orders'),
    (re.compile(r'customers\s*\('), 'customers'),
    (re.compile(r'collections\s*\('), 'collections'),
    (re.compile(r'locations\s*\('), 'locations'),
    (re.compile(r'giftCards\s*\('), 'gift_cards'),
    (re.compile(r'codeDiscountNodes\s*\('), 'discount_codes'),
    (re.compile(r'abandonedCheckouts\s*\('), 'abandoned_checkouts'),
    (re.compile(r'webhookSubscriptions\s*\('), 'webhook_list'),
    # Fallback shop query
    (re.compile(r'\bshop\b\s*\{'), 'shop'),
]

MUTATION_DISPATCH = [
    (re.compile(r'productSet\b'), 'product_set'),
    (re.compile(r'productCreate\b'), 'product_create'),
    (re.compile(r'productUpdate\b'), 'product_update'),
    (re.compile(r'productVariantsBulkUpdate\b'), 'variant_bulk_update'),
    (re.compile(r'customerCreate\b'), 'customer_create'),
    (re.compile(r'customerUpdate\b'), 'customer_update'),
    (re.compile(r'orderUpdate\b'), 'order_update'),
    (re.compile(r'inventorySetQuantities\b'), 'inventory_set'),
    (re.compile(r'inventoryAdjustQuantities\b'), 'inventory_adjust'),
    (re.compile(r'collectionCreate\b'), 'collection_create'),
    (re.compile(r'discountCodeBasicCreate\b'), 'discount_basic_create'),
    (re.compile(r'discountCodeBasicUpdate\b'), 'discount_basic_update'),
    (re.compile(r'discountCodeFreeShippingCreate\b'), 'discount_fs_create'),
    (re.compile(r'discountCodeFreeShippingUpdate\b'), 'discount_fs_update'),
    (re.compile(r'discountCodeDelete\b'), 'discount_delete'),
    (re.compile(r'refundCreate\b'), 'refund_create'),
    (re.compile(r'fulfillmentCreate\b'), 'fulfillment_create'),
    (re.compile(r'metafieldsSet\b'), 'metafield_set'),
    (re.compile(r'metafieldDelete\b'), 'metafield_delete'),
    (re.compile(r'webhookSubscriptionCreate\b'), 'webhook_create'),
    (re.compile(r'webhookSubscriptionDelete\b'), 'webhook_delete'),
    (re.compile(r'orderMarkAsPaid\b'), 'order_mark_paid'),
]

# ── Handler registry ──────────────────────────────────────

_QUERY_HANDLERS = {
    'shop': shop_handler.handle_shop_query,
    'products': product_handler.handle_fetch_products,
    'single_product': product_handler.handle_fetch_single_product,
    'customers': customer_handler.handle_fetch_customers,
    'single_customer': customer_handler.handle_fetch_single_customer,
    'orders': order_handler.handle_fetch_orders,
    'single_order': order_handler.handle_fetch_single_order,
    'locations': location_handler.handle_fetch_locations,
    'inventory_set': inventory_handler.handle_inventory_set_quantities,
    # Phase 2: Fulfillments
    'fulfillments': fulfillment_handler.handle_fetch_order_fulfillments,
    # Phase 2: Refunds
    'refunds': refund_handler.handle_fetch_refunds,
    # Phase 2: Webhooks
    'webhook_list': webhook_handler.handle_webhook_list,
}

_MUTATION_HANDLERS = {
    'product_set': product_handler.handle_product_set,
    'product_create': product_handler.handle_product_set,  # Same handler
    'product_update': product_handler.handle_product_update,
    'variant_bulk_update': product_handler.handle_variant_bulk_update,
    'customer_create': customer_handler.handle_customer_create,
    'customer_update': customer_handler.handle_customer_update,
    'order_update': order_handler.handle_order_update,
    'order_mark_paid': order_handler.handle_order_mark_as_paid,
    'inventory_set': inventory_handler.handle_inventory_set_quantities,
    'inventory_adjust': inventory_handler.handle_inventory_adjust_quantities,
    # Phase 2: Fulfillments
    'fulfillment_create': fulfillment_handler.handle_fulfillment_create,
    # Phase 2: Refunds
    'refund_create': refund_handler.handle_refund_create,
    # Phase 2: Webhooks
    'webhook_create': webhook_handler.handle_webhook_create,
    'webhook_delete': webhook_handler.handle_webhook_delete,
}


def _not_implemented(env, config, variables):
    """Placeholder for operations not yet implemented."""
    return {'__simulator': 'not_implemented'}


class ShopifySimulatorController(http.Controller):

    @http.route(
        '/shopify-sim/<int:config_id>/admin/api/<string:api_version>/graphql.json',
        type='http',
        auth='none',
        methods=['POST'],
        csrf=False,
        save_session=False,
    )
    def graphql_endpoint(self, config_id, api_version, **kwargs):
        """Main entry point for simulated Shopify GraphQL API."""
        # ── Production safeguard ──────────────────────────
        if _RUNNING_ENV == 'production':
            return request.make_json_response(
                {'errors': [{'message': 'Simulator disabled in production'}]},
                status=403,
            )

        # ── Load config ───────────────────────────────────
        config = request.env['sim.shopify.config'].sudo().browse(config_id)
        if not config.exists():
            return request.make_json_response(
                build_error_response('Simulator config not found'),
                status=404,
            )

        # ── Validate access token ─────────────────────────
        token = request.httprequest.headers.get('X-Shopify-Access-Token', '')
        if token != config.access_token:
            return request.make_json_response(
                build_error_response('Unauthorized: invalid access token'),
                status=401,
            )

        # ── Check error mode ──────────────────────────────
        error_response = self._check_error_mode(config)
        if error_response is not None:
            return error_response

        # ── Parse request body ────────────────────────────
        try:
            raw = request.httprequest.get_data(as_text=True)
            body = json.loads(raw)
        except (json.JSONDecodeError, TypeError) as e:
            return request.make_json_response(
                build_error_response(f'Invalid JSON: {e}'),
                status=400,
            )

        query_text = body.get('query', '')
        variables = body.get('variables') or {}

        # ── Dispatch ──────────────────────────────────────
        is_mutation = query_text.lstrip().startswith('mutation')
        dispatch_table = MUTATION_DISPATCH if is_mutation else QUERY_DISPATCH
        handler_registry = _MUTATION_HANDLERS if is_mutation else _QUERY_HANDLERS

        handler_key = None
        for pattern, key in dispatch_table:
            if pattern.search(query_text):
                handler_key = key
                break

        if not handler_key:
            extensions = config._build_extensions(1)
            _logger.warning(
                "Simulator: no handler for %s query: %.200s",
                'mutation' if is_mutation else 'query', query_text,
            )
            return request.make_json_response(
                build_response({'__simulator': 'unrecognized'}, extensions),
            )

        handler = handler_registry.get(handler_key, _not_implemented)

        # ── Check userErrors mode for mutations ───────────
        if is_mutation and config.error_mode == 'user_errors':
            extensions = config._build_extensions(10)
            # Return a mutation result with a fake userError
            mutation_key = handler_key
            data = {mutation_key: {'userErrors': [
                {'field': ['id'], 'message': 'Simulated validation error'},
            ]}}
            return request.make_json_response(
                build_response(data, extensions),
            )

        # ── Execute handler ───────────────────────────────
        try:
            env = request.env
            data = handler(env, config, variables)
            estimated_cost = 12 if not is_mutation else 10
            extensions = config._build_extensions(estimated_cost)
            return request.make_json_response(
                build_response(data, extensions),
            )
        except Exception as e:
            _logger.exception("Simulator handler error: %s", handler_key)
            extensions = config._build_extensions(1)
            return request.make_json_response(
                build_response(None, extensions, errors=[{'message': str(e)}]),
                status=200,  # Shopify returns 200 even with GraphQL errors
            )

    def _check_error_mode(self, config):
        """Apply chaos/error mode if configured. Returns a response or None."""
        mode = config.error_mode
        if mode == 'none':
            return None

        extensions = config._build_extensions(10)

        if mode == 'always_error':
            return request.make_json_response(
                build_response(None, extensions, errors=[
                    {'message': 'Simulated server error'},
                ]),
                status=200,
            )

        if mode == 'random_errors':
            if random.randint(1, 100) <= (config.error_rate_pct or 20):
                return request.make_json_response(
                    build_response(None, extensions, errors=[
                        {'message': 'Simulated random error'},
                    ]),
                    status=200,
                )
            return None

        if mode == 'rate_limit':
            if config.rate_limit_available <= 0:
                return request.make_json_response(
                    build_error_response('Throttled'),
                    status=429,
                    headers={'Retry-After': '2.0'},
                )
            return None

        if mode == 'timeout':
            time.sleep(35)
            return request.make_json_response({}, status=504)

        return None  # Unknown mode, proceed normally
