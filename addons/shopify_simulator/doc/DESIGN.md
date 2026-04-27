# Shopify Simulator — Design Document

## Purpose

Internal-only Odoo module that acts as a fake Shopify GraphQL Admin API server.
Used for end-to-end testing and UAT of `shopify_connector_pro` without a real Shopify store.

**Not shipped to customers. Not installed in production.**

---

## Operation Inventory

### GraphQL Queries (15 operations)

| # | Variable | Shopify Object | Connector Sync Class | Direction | Simulator Behavior |
|---|----------|---------------|---------------------|-----------|-------------------|
| 1 | SHOP_QUERY | Shop | shopify_backend.action_test_connection | Import | Return shop info from sim.shopify.config |
| 2 | FETCH_PRODUCTS | Product | ProductImporter (product_sync.py) | Import | Paginated sim.shopify.product records |
| 3 | FETCH_ORDERS | Order | OrderImporter (order_sync.py) | Import | Paginated sim.shopify.order records |
| 4 | FETCH_CUSTOMERS | Customer | CustomerImporter (customer_sync.py) | Import | Paginated sim.shopify.customer records |
| 5 | FETCH_COLLECTIONS | Collection | CollectionImporter (collection_sync.py) | Import | Paginated sim.shopify.collection records |
| 6 | FETCH_LOCATIONS | Location | LocationSync (location_sync.py) | Import | Paginated sim.shopify.location records |
| 7 | FETCH_GIFT_CARDS | GiftCard | GiftCardSync (gift_card_sync.py) | Import | Paginated sim.shopify.gift.card records |
| 8 | FETCH_DISCOUNT_CODES | DiscountCode | DiscountImporter (discount_import_sync.py) | Import | Paginated sim.shopify.discount records |
| 9 | FETCH_PAYOUTS | Payout | PayoutSync (payout_sync.py) | Import | Paginated sim.shopify.payout records |
| 10 | FETCH_PAYOUT_TRANSACTIONS | PayoutTransaction | PayoutSync (payout_sync.py) | Import | Paginated sim.shopify.payout.transaction records |
| 11 | FETCH_ABANDONED_CHECKOUTS | AbandonedCheckout | AbandonedCartImporter (abandoned_cart_sync.py) | Import | Paginated sim.shopify.abandoned.cart records |
| 12 | FETCH_REFUNDS | Refund | RefundImporter (refund_sync.py) | Import | Return refunds for a given order |
| 13 | FETCH_PRODUCT_METAFIELDS | Metafield | MetafieldSync (metafield_sync.py) | Import | Return metafields for a given product |
| 14 | FETCH_ORDER_FULFILLMENTS | Fulfillment | FulfillmentSync (fulfillment_sync.py) | Import | Return fulfillment data for an order |
| 15 | WEBHOOK_LIST_QUERY | Webhook | shopify_backend.action_check_webhook_status | Query | List sim.shopify.webhook.subscription records |

### GraphQL Mutations (22 operations)

| # | Variable | Shopify Object | Connector Sync Class | Direction | Simulator Behavior |
|---|----------|---------------|---------------------|-----------|-------------------|
| 16 | PRODUCT_SET_MUTATION | Product | ProductExporter (product_sync.py) | Export | Create sim product + variants, return GIDs |
| 17 | PRODUCT_CREATE_MUTATION | Product | (unused in current sync) | Export | Create sim product |
| 18 | PRODUCT_UPDATE_MUTATION | Product | ProductExporter (product_sync.py) | Export | Update sim product metadata |
| 19 | VARIANT_BULK_UPDATE_MUTATION | ProductVariant | ProductExporter (product_sync.py) | Export | Update sim variant prices/SKUs |
| 20 | CUSTOMER_CREATE_MUTATION | Customer | CustomerExporter (customer_sync.py) | Export | Create sim customer, return GID |
| 21 | CUSTOMER_UPDATE_MUTATION | Customer | CustomerExporter (customer_sync.py) | Export | Update sim customer |
| 22 | ORDER_UPDATE_MUTATION | Order | OrderExporter (order_sync.py) | Export | Update sim order tags/notes |
| 23 | INVENTORY_SET_QUANTITIES | InventoryLevel | InventorySync (inventory_sync.py) | Export | Update sim inventory levels |
| 24 | INVENTORY_ADJUST_QUANTITIES | InventoryLevel | (available, not primary) | Export | Adjust sim inventory levels |
| 25 | COLLECTION_CREATE_MUTATION | Collection | CollectionExporter (collection_export.py) | Export | Create sim collection |
| 26 | DISCOUNT_CODE_BASIC_CREATE | DiscountCode | DiscountExporter (discount_sync.py) | Export | Create sim basic discount |
| 27 | DISCOUNT_CODE_BASIC_UPDATE | DiscountCode | DiscountExporter (discount_sync.py) | Export | Update sim basic discount |
| 28 | DISCOUNT_CODE_FREE_SHIPPING_CREATE | DiscountCode | DiscountExporter (discount_sync.py) | Export | Create sim free shipping discount |
| 29 | DISCOUNT_CODE_FREE_SHIPPING_UPDATE | DiscountCode | DiscountExporter (discount_sync.py) | Export | Update sim free shipping discount |
| 30 | DISCOUNT_CODE_DELETE | DiscountCode | (available, not primary) | Export | Delete sim discount |
| 31 | REFUND_CREATE | Refund | account_move reverse sync | Export | Create sim refund record |
| 32 | FULFILLMENT_CREATE_MUTATION | Fulfillment | FulfillmentSync (fulfillment_sync.py) | Export | Create sim fulfillment |
| 33 | METAFIELD_SET_MUTATION | Metafield | MetafieldSync (metafield_sync.py) | Export | Set sim metafields |
| 34 | METAFIELD_DELETE_MUTATION | Metafield | MetafieldSync (metafield_sync.py) | Export | Delete sim metafield |
| 35 | WEBHOOK_CREATE_MUTATION | Webhook | shopify_backend.action_register_webhooks | Setup | Create sim webhook subscription |
| 36 | WEBHOOK_DELETE_MUTATION | Webhook | shopify_backend.action_unregister_webhooks | Setup | Delete sim webhook subscription |

### Inline Queries in fulfillment_sync.py (4 operations)

| # | Query Name | Purpose | Simulator Behavior |
|---|-----------|---------|-------------------|
| 37 | GetFulfillmentOrders | Get fulfillment orders for a Shopify order | Return fulfillment order data |
| 38 | GetOrderStatus | Get fulfillment status for display | Return order fulfillment status |
| 39 | (inline in push_fulfillment) | Fetch fulfillment orders before creating | Return open fulfillment orders with line items |
| 40 | (inline in product webhook handler) | Fetch single product by ID | Return single product node |

### Webhook Topics (15 topics)

| # | Topic | Connector Handler | Simulator Trigger |
|---|-------|------------------|-------------------|
| 1 | products/create | _handle_product_webhook | On sim product create |
| 2 | products/update | _handle_product_webhook | On sim product update |
| 3 | products/delete | _handle_product_delete_webhook | On sim product delete |
| 4 | orders/create | _handle_order_webhook | On sim order create |
| 5 | orders/updated | _handle_order_webhook | On sim order update |
| 6 | orders/cancelled | _handle_order_cancel_webhook | On sim order cancel |
| 7 | customers/create | _handle_customer_webhook | On sim customer create |
| 8 | customers/update | _handle_customer_webhook | On sim customer update |
| 9 | inventory_levels/update | _handle_inventory_webhook | On sim inventory change |
| 10 | fulfillments/create | _handle_fulfillment_webhook | On sim fulfillment create |
| 11 | refunds/create | _handle_refund_webhook | On sim refund create |
| 12 | app/uninstalled | _handle_app_uninstalled | Manual trigger |
| 13 | customers/data_request | _handle_gdpr_data_request | Manual trigger |
| 14 | customers/redact | _handle_gdpr_customer_redact | Manual trigger |
| 15 | shop/redact | _handle_gdpr_shop_redact | Manual trigger |

### Cron Jobs (14 crons)

| Cron | Model | Method | Interval | Simulator Coverage |
|------|-------|--------|----------|-------------------|
| Sync Products | shopify.backend | _cron_sync_products | 15 min | Phase 1 |
| Import Orders | shopify.backend | _cron_import_orders | 5 min | Phase 2 |
| Sync Inventory | shopify.backend | _cron_sync_inventory | 10 min | Phase 1 |
| Sync Customers | shopify.backend | _cron_sync_customers | 15 min | Phase 1 |
| Process Webhooks | shopify.webhook.log | _cron_process_pending | 1 min | Phase 2 |
| Sync Discounts | shopify.backend | _cron_sync_discounts | 30 min | Phase 4 |
| Sync Collections | shopify.backend | _cron_sync_collections | 1 hour | Phase 4 |
| Import Refunds | shopify.backend | _cron_import_refunds | 30 min | Phase 2 |
| Import Payouts | shopify.backend | _cron_import_payouts | 6 hours | Phase 4 |
| Process Import Jobs | shopify.import.job | _cron_process_import_jobs | 2 min | Phase 3 |
| Reconciliation | shopify.reconciliation | _cron_reconcile | 6 hours | Phase 4 |
| Abandoned Carts | shopify.backend | _cron_import_abandoned_carts | 30 min | Phase 4 |
| Error Digest | shopify.backend | _cron_error_digest | 1 day | N/A (chatter) |
| Cleanup Webhooks | shopify.webhook.log | _cron_cleanup_old_logs | 1 day | N/A (cleanup) |

---

## Architecture

### How the Connector Points to the Simulator (No Monkey Patching)

**Strategy: Client Factory Method on shopify.backend**

The connector is refactored with a minimal, explicit change:

1. Add `_make_api_client(self)` method to `shopify.backend` that returns `ShopifyClient(self)`
2. Replace all `ShopifyClient(backend)` calls across sync classes and models with `backend._make_api_client()`
3. The simulator inherits `shopify.backend` and overrides `_make_api_client()`:
   - When `use_simulator=True`: returns `SimulatorClient(self)` (routes to local Odoo controller)
   - When `use_simulator=False`: calls `super()._make_api_client()` (original behavior)

This is standard Odoo model inheritance, not monkey-patching. The factory method is explicit and documented.

```python
# In shopify_connector_pro/models/shopify_backend.py (added)
def _make_api_client(self):
    """Factory method for creating the Shopify API client.

    Override this in test/simulator modules to substitute
    a different client implementation.
    """
    from ..shopify_api.client import ShopifyClient
    return ShopifyClient(self)

# In shopify_simulator/models/sim_backend_inherit.py
def _make_api_client(self):
    if self.use_simulator:
        return SimulatorClient(self)
    return super()._make_api_client()
```

### SimulatorClient

`SimulatorClient` is a subclass of `ShopifyClient` that:
- Skips the `_SHOPIFY_HOST_RE` domain validation
- Points to `{web.base.url}/shopify-sim/{config_id}/admin/api/{version}/graphql.json`
- Mounts `http://` adapter (since local Odoo is HTTP)
- Preserves ALL other behavior (rate limiter, circuit breaker, retries, error handling)

This means the connector's full request pipeline (rate limiting, retry logic, error parsing,
response extension handling) is exercised against the simulator.

### Dev-Only Safeguards

1. `__manifest__.py`: `'category': 'Hidden/Tools'`, not listed in public App Store categories
2. Backend field `use_simulator` ONLY editable when `running_env != 'production'`
   (checked via `ir.config_parameter` or `os.environ`)
3. Controller returns 403 if `running_env == 'production'`
4. Module depends on `shopify_connector_pro` (won't install without the connector)
5. Security group `shopify_simulator.group_simulator_admin` — only internal users with explicit access

### Module Structure

```
addons/shopify_simulator/
    __init__.py
    __manifest__.py
    controllers/
        __init__.py
        graphql_endpoint.py          # Main GraphQL route + dispatch
    models/
        __init__.py
        sim_backend_inherit.py       # Inherit shopify.backend: use_simulator, _make_api_client override
        sim_config.py                # Simulator config per backend (auth, error modes)
        sim_product.py               # Product + Variant + Option + Image
        sim_customer.py              # Customer + Address
        sim_order.py                 # Order + LineItem + ShippingLine
        sim_inventory.py             # Inventory levels per location per variant
        sim_location.py              # Fulfillment locations
        sim_collection.py            # Product collections (Phase 4)
        sim_discount.py              # Discount codes (Phase 4)
        sim_fulfillment.py           # Fulfillment records (Phase 2)
        sim_refund.py                # Refund records (Phase 2)
        sim_webhook_sub.py           # Webhook subscriptions (Phase 2)
        sim_metafield.py             # Metafields (Phase 4)
        sim_payout.py                # Payouts + transactions (Phase 4)
        sim_abandoned_cart.py        # Abandoned carts (Phase 4)
    handlers/
        __init__.py
        base_handler.py              # Pagination, response wrapper, extensions, money helpers
        shop_handler.py              # SHOP_QUERY
        product_handler.py           # Product queries and mutations
        customer_handler.py          # Customer queries and mutations
        order_handler.py             # Order queries and mutations
        inventory_handler.py         # Inventory mutations
        location_handler.py          # Location query
        webhook_handler.py           # Webhook CRUD (Phase 2)
        fulfillment_handler.py       # Fulfillment queries/mutations (Phase 2)
        refund_handler.py            # Refund queries/mutations (Phase 2)
    lib/
        __init__.py
        simulator_client.py          # SimulatorClient(ShopifyClient) subclass
    fixtures/
        demo_store.py                # Seed data creator (realistic Shopify store)
    security/
        shopify_sim_security.xml
        ir.model.access.csv
    views/
        sim_config_views.xml
        sim_product_views.xml
        sim_order_views.xml
        sim_customer_views.xml
        sim_menu.xml
    data/
        sim_sequences.xml            # ir.sequence for GID generation
        sim_demo_data.xml            # Default demo data
    tests/
        __init__.py
        common.py                    # Test base class with simulator setup
        test_graphql_endpoint.py     # Controller/dispatch tests
        test_product_sync.py         # Product import/export through simulator
        test_customer_sync.py        # Customer import/export through simulator
        test_order_sync.py           # Order import through simulator (Phase 2)
        test_inventory_sync.py       # Inventory export through simulator
        test_pagination.py           # Cursor pagination tests
        test_error_modes.py          # Chaos/error mode tests (Phase 3)
        test_webhooks.py             # Webhook generation/HMAC tests (Phase 2)
```

### Simulator Models

Each model stores data representing the Shopify-side state. Every model has:
- `config_id` → links to the simulator config (which links to backend)
- `shopify_gid` → auto-generated Shopify GID (e.g., `gid://shopify/Product/1001`)
- `_to_graphql_node()` → returns exact Shopify GraphQL response shape (dict)
- `_to_webhook_payload()` → returns Shopify REST webhook payload (Phase 2)

### GraphQL Dispatch

Regex-based operation detection (no full GraphQL parser):

```python
# Check mutation vs query
is_mutation = query_text.lstrip().startswith('mutation')

# Ordered regex patterns — more specific first
MUTATION_PATTERNS = [
    (r'productSet\b', handle_product_set),
    (r'productUpdate\b', handle_product_update),
    (r'productVariantsBulkUpdate\b', handle_variant_bulk_update),
    ...
]
QUERY_PATTERNS = [
    (r'shopifyPaymentsAccount.*payoutTransactions', handle_payout_transactions),
    (r'shopifyPaymentsAccount.*payouts', handle_payouts),
    (r'products\s*\(', handle_fetch_products),
    ...
]
```

### Cursor-Based Pagination

Base64-encoded offset cursor matching Shopify format:

```python
def encode_cursor(offset):
    return base64.b64encode(f'eyJsYXN0X2lkIjp7offset}}'.encode()).decode()

def paginate(records, first, after=None):
    offset = decode_cursor(after) if after else 0
    page = records[offset:offset + first]
    has_next = (offset + first) < len(records)
    return {
        'edges': [{'cursor': encode_cursor(offset + i), 'node': rec._to_graphql_node()} for i, rec in enumerate(page)],
        'pageInfo': {'hasNextPage': has_next, 'endCursor': encode_cursor(offset + len(page) - 1) if page else None},
    }
```

### Rate Limit / Extensions Simulation

Every response includes realistic `extensions.cost`:

```python
{
    'extensions': {
        'cost': {
            'requestedQueryCost': estimated_cost,
            'actualQueryCost': actual_cost,
            'throttleStatus': {
                'maximumAvailable': 1000.0,
                'currentlyAvailable': available,
                'restoreRate': 50.0,
            }
        }
    }
}
```

### Error/Chaos Mode Simulation

`sim.shopify.config.error_mode` field:
- `none` — Normal operation
- `random_errors` — Random GraphQL errors at configurable rate
- `always_error` — Every request returns error
- `rate_limit` — Return 429 after configurable number of requests
- `timeout` — Sleep beyond client timeout (35s > 30s read timeout)

### Webhook Simulation (Phase 2)

When mutations create/update data and webhooks are registered:
1. Build REST-format payload (Shopify webhooks use REST format, not GraphQL)
2. Compute HMAC-SHA256 of raw body using the registered webhook secret
3. POST to `{callback_url}` with proper headers:
   - `X-Shopify-Topic`, `X-Shopify-Hmac-Sha256`, `X-Shopify-Shop-Domain`, `X-Shopify-Webhook-Id`
4. Delivery via background thread (non-blocking)

### Fixture Strategy

Fixtures provide realistic data including edge cases:
- Products with variants, options, images, metafields
- Products with missing SKUs, duplicate SKUs, Unicode/Arabic titles
- Orders with discount codes, shipping lines, taxes, multi-currency
- Partially fulfilled orders, refunded orders, cancelled orders
- Multi-location inventory
- Guest orders (no customer account)

### Test Strategy

Every simulator feature requires:
1. **Controller test** — verify GraphQL endpoint returns correct response shape
2. **Response validation** — verify response matches Shopify API contract
3. **Connector integration test** — run actual sync through simulator, verify Odoo DB state
4. **Error test** — verify error/edge cases
5. **Database state test** — verify Odoo records match simulator state after sync

---

## Phase Breakdown

### Phase 1 (Current): Core Infrastructure + Products + Customers + Inventory
- GraphQL controller with dispatch
- SimulatorClient + factory method
- Product, Variant, Customer, Location, Inventory models
- Product import/export, Customer import/export, Inventory export
- Cursor pagination
- Rate limit extensions
- Seed demo store
- Automated tests

### Phase 2: Orders + Fulfillments + Refunds + Webhooks
- Order model + import
- Fulfillment model + bidirectional sync
- Refund model + import
- Webhook subscription CRUD + outbound delivery
- HMAC valid/invalid tests
- Duplicate/out-of-order webhook tests

### Phase 3: Bulk Operations + Chaos Engineering
- Import job processing
- Rate limit simulation
- Timeout/retry scenarios
- Large catalog stress tests
- Partial failure scenarios

### Phase 4: Remaining Entities + Full Coverage
- Collections, Discounts, Gift Cards, Payouts, Abandoned Carts, Metafields
- Contract test suite
- Coverage matrix
- QA documentation
