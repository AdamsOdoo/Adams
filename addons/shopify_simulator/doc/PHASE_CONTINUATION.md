# Shopify Simulator — Phase Continuation Guide

> This document is for starting a new conversation to continue building
> the simulator. Give this file to the new session as context.

## Current State: Phase 2 IN PROGRESS 🔧

**Phase 1:** COMPLETE ✅ (112 tests, 0 failures)
**Phase 2:** Models + Handlers + Tests COMPLETE ✅ (170 tests, 0 failures)
**Connector tests:** 292 tests, 0 failures (backward-compatible)

### What Phase 2 Delivered

1. **New models (6):** `sim.shopify.fulfillment`, `sim.shopify.fulfillment.order`, `sim.shopify.fulfillment.order.line`, `sim.shopify.refund`, `sim.shopify.refund.line`, `sim.shopify.webhook.subscription`
2. **New handlers (3):** `fulfillment_handler.py`, `refund_handler.py`, `webhook_handler.py`
3. **Updated handlers:** `order_handler.py` (added `handle_fetch_single_order`, `handle_order_mark_as_paid`), `customer_handler.py` (added `handle_fetch_single_customer`)
4. **Fulfillment lifecycle:** Auto-create FulfillmentOrders on order creation, fulfillmentCreate with partial/full support, order status transitions (UNFULFILLED → PARTIALLY_FULFILLED → FULFILLED)
5. **Refund lifecycle:** refundCreate with full/partial support, shipping refunds, order financial status updates (PAID → PARTIALLY_REFUNDED → REFUNDED)
6. **Webhook CRUD:** webhookSubscriptionCreate (with duplicate handling), webhookSubscriptionDelete, WEBHOOK_LIST_QUERY
7. **Webhook outbound delivery:** HMAC-SHA256 signing (matches Shopify exactly), threaded async POST, topic matching, fires on fulfillmentCreate/refundCreate
8. **Order lifecycle integration:** Full PENDING → PAID → FULFILLED → REFUNDED flow tested end-to-end
9. **New tests (5 files, 58 new tests):** test_fulfillment_handlers, test_refund_handlers, test_webhook_handlers, test_webhook_delivery, test_order_lifecycle
10. **Security:** ACL entries for all 7 new models (user + admin groups)
11. **Documentation:** User guide (`doc/shopify_simulator_user_guide.md`), updated coverage matrix

### What Phase 1 Delivered

1. **Connector refactor** — `_make_api_client()` factory on `shopify.backend`, 20+ sites updated
2. **Module structure** — `addons/shopify_simulator/` with models, handlers, controllers, lib, views, security, tests, fixtures, doc
3. **Models:** `sim.shopify.config`, `sim.shopify.product`, `sim.shopify.variant`, `sim.shopify.customer`, `sim.shopify.order`, `sim.shopify.order.line`, `sim.shopify.shipping.line`, `sim.shopify.location`, `sim.shopify.inventory.level`
4. **Handlers:** shop, product (fetch/single/set/update/variant_bulk_update), customer (fetch/create/update), order (fetch with filter/update), inventory (set/adjust), location (fetch)
5. **Infrastructure:** SimulatorClient, cursor pagination, extensions/cost block, error modes, production safeguard, regex dispatch (17 query + 22 mutation patterns)
6. **Tests:** 8 test files covering models, dispatch, all handlers, pagination, error modes
7. **Fixtures:** `demo_store.py` with 6 products, 3 customers, 3 orders, 2 locations, inventory

### Key Files to Read First in a New Session

```
addons/shopify_simulator/doc/DESIGN.md          # Full architecture + all 40 operations
addons/shopify_simulator/doc/PHASE_CONTINUATION.md  # This file
addons/shopify_simulator/__manifest__.py
addons/shopify_simulator/controllers/graphql_endpoint.py  # Dispatch tables
addons/shopify_simulator/tests/common.py        # Test base class
CLAUDE.md                                       # Project rules (accounting setup, etc.)
```

---

## Phase 2: Orders + Fulfillments + Refunds + Webhooks

### Goal
Enable full order lifecycle testing: import orders → fulfill → refund → webhook notifications.

### New Models to Create

| Model | File | Fields |
|-------|------|--------|
| `sim.shopify.fulfillment` | `models/sim_fulfillment.py` | order_id, shopify_gid, status (SUCCESS/CANCELLED/ERROR), tracking_number, tracking_company, tracking_url, line_items (JSON), created_at |
| `sim.shopify.fulfillment.order` | `models/sim_fulfillment.py` | order_id, shopify_gid, status (OPEN/CLOSED/IN_PROGRESS/CANCELLED), assigned_location_id, line_items |
| `sim.shopify.fulfillment.order.line` | `models/sim_fulfillment.py` | fulfillment_order_id, variant_gid, remaining_quantity, fulfillable_quantity |
| `sim.shopify.refund` | `models/sim_refund.py` | order_id, shopify_gid, note, refund_line_items (O2M), created_at |
| `sim.shopify.refund.line` | `models/sim_refund.py` | refund_id, line_item_gid, quantity, restocked |
| `sim.shopify.webhook.subscription` | `models/sim_webhook.py` | config_id, shopify_gid, topic, callback_url, format, include_fields |

### Handlers to Create/Update

| Handler | Operations | File |
|---------|-----------|------|
| `fulfillment_handler.py` | GetFulfillmentOrders, fulfillmentCreate, GetOrderStatus | NEW |
| `refund_handler.py` | FETCH_REFUNDS (sub-query on order), refundCreate | NEW |
| `webhook_handler.py` | webhookSubscriptionCreate, webhookSubscriptionDelete, WEBHOOK_LIST_QUERY | NEW |
| `order_handler.py` | Add fulfillment/refund sub-queries, orderMarkAsPaid | UPDATE |

### Webhook Outbound Delivery

When mutations modify data (product create/update, order create, inventory change, fulfillment create, refund create):

1. Check if a `sim.shopify.webhook.subscription` exists for the relevant topic
2. Build REST-format payload using `_to_webhook_payload()` on the model
3. Compute `HMAC-SHA256(raw_body, webhook_secret)` 
4. POST to `callback_url` with headers:
   - `X-Shopify-Topic: products/update`
   - `X-Shopify-Hmac-Sha256: <base64_hmac>`
   - `X-Shopify-Shop-Domain: <myshopify_domain>`
   - `X-Shopify-Webhook-Id: <uuid>`
   - `X-Shopify-API-Version: 2026-01`
5. Use `threading.Thread` for non-blocking delivery (real Shopify is async)

### Methods to Add on Existing Models

```python
# On sim.shopify.product, sim.shopify.customer, sim.shopify.order:
def _to_webhook_payload(self):
    """Return REST-format dict for webhook body (different from GraphQL node)."""
    ...

def _fire_webhook(self, topic):
    """Check for registered webhooks and deliver if matched."""
    ...
```

### Tests Required

| Test File | Tests |
|-----------|-------|
| `tests/test_fulfillment_handlers.py` | GetFulfillmentOrders, fulfillmentCreate (success, partial, already fulfilled), fulfillment status update |
| `tests/test_refund_handlers.py` | refundCreate (full, partial, restock), FETCH_REFUNDS sub-query |
| `tests/test_webhook_handlers.py` | webhookSubscriptionCreate, Delete, List, duplicate topic handling |
| `tests/test_webhook_delivery.py` | Outbound delivery on product/customer/order mutations, HMAC verification (valid + invalid), missing callback_url, delivery failure handling |
| `tests/test_order_lifecycle.py` | Full lifecycle: create order → fulfill → refund → verify webhooks fired at each step |

### Security Updates

- Add ACL entries for new models in `security/ir.model.access.csv`
- Add `_to_graphql_node()` and `_to_webhook_payload()` to fulfillment, refund, webhook models

### Manifest Updates

```python
'data': [
    ...
    'views/sim_fulfillment_views.xml',  # NEW
    'views/sim_webhook_views.xml',      # NEW
],
```

---

## Phase 3: Bulk Operations + Chaos Engineering

### Goal
Test connector resilience: bulk imports, rate limiting, timeouts, partial failures.

### Features to Implement

1. **Import Job Simulation**
   - Handler for `bulkOperationRunQuery` mutation → returns a fake bulk operation GID
   - Polling endpoint for `bulkOperation { status url }` → returns COMPLETED with a fake JSONL URL
   - Serve JSONL at `/shopify-sim/<config_id>/bulk/<operation_id>.jsonl`
   - Test connector's `shopify.import.job` processing

2. **Rate Limit Exhaustion Scenario**
   - Configure `sim.shopify.config` with low `rate_limit_bucket_size` (e.g., 50)
   - Set `rate_limit_restore_rate` to slow value
   - Verify connector's `ShopifyRateLimiter` backs off correctly
   - Verify `extensions.cost.throttleStatus.currentlyAvailable` decreases realistically

3. **Timeout/Retry Scenarios**
   - `error_mode = 'timeout'` already sleeps 35s → verify connector retries
   - Add `error_mode = 'intermittent_timeout'` — timeout on Nth request only
   - Verify circuit breaker behavior (5 consecutive failures → open)

4. **Partial Failure Scenarios**
   - `productSet` mutation succeeds but one variant has a `userError`
   - Inventory batch set: some items succeed, some fail
   - Order import with deleted product variant (variant_gid returns null)

5. **Large Catalog Stress Tests**
   - Seed 500+ products with `demo_store.py` variant
   - Test pagination performance across all pages
   - Test cursor stability (no duplicates, no gaps)

### Tests Required

| Test File | Tests |
|-----------|-------|
| `tests/test_bulk_operations.py` | bulkOperationRunQuery, status polling, JSONL serving, import job processing |
| `tests/test_rate_limiting.py` | Budget exhaustion, restore rate, 429 response, connector retry behavior |
| `tests/test_timeout_retry.py` | Timeout mode, intermittent timeout, circuit breaker open/close |
| `tests/test_partial_failures.py` | Partial variant errors, partial inventory failures, deleted variant handling |
| `tests/test_stress.py` | Large catalog pagination, cursor stability, performance benchmarks |

---

## Phase 4: Remaining Entities + Full Coverage

### Goal
Cover all 40 Shopify operations. Contract test suite. Full documentation.

### New Models

| Model | Shopify Entity |
|-------|---------------|
| `sim.shopify.collection` | Collections (smart + custom) |
| `sim.shopify.discount` | Discount codes (basic, free shipping) |
| `sim.shopify.gift.card` | Gift cards |
| `sim.shopify.payout` | Shopify Payments payouts |
| `sim.shopify.payout.transaction` | Payout transactions |
| `sim.shopify.abandoned.cart` | Abandoned checkouts |
| `sim.shopify.metafield` | Metafields (any owner type) |

### New Handlers

| Handler | Operations |
|---------|-----------|
| `collection_handler.py` | FETCH_COLLECTIONS, collectionCreate |
| `discount_handler.py` | FETCH_DISCOUNT_CODES, discountCodeBasicCreate/Update, discountCodeFreeShippingCreate/Update, discountCodeDelete |
| `gift_card_handler.py` | FETCH_GIFT_CARDS |
| `payout_handler.py` | FETCH_PAYOUTS, FETCH_PAYOUT_TRANSACTIONS |
| `abandoned_cart_handler.py` | FETCH_ABANDONED_CHECKOUTS |
| `metafield_handler.py` | FETCH_PRODUCT_METAFIELDS, metafieldsSet, metafieldDelete |

### Contract Test Suite

For every operation, verify:
1. **Request shape** — the connector sends variables the simulator expects
2. **Response shape** — the simulator returns the exact structure the connector parses
3. **Field-by-field** — every field the connector reads from the response exists and has correct type
4. **Edge cases** — null fields, empty arrays, missing optional fields

```python
class TestProductContract(SimulatorTestCase):
    """Verify connector ↔ simulator contract for products."""
    
    def test_fetch_products_response_has_all_connector_fields(self):
        """Every field ProductImporter reads must exist in simulator response."""
        product = self._seed_product(...)
        node = product._to_graphql_node()
        # These are the fields ProductImporter._parse_product() reads:
        required_fields = ['id', 'title', 'descriptionHtml', 'vendor', 
                          'productType', 'tags', 'status', 'handle',
                          'createdAt', 'updatedAt', 'options', 'variants']
        for field in required_fields:
            self.assertIn(field, node, f"Missing required field: {field}")
```

### Coverage Matrix (Final)

| Operation | Model | Handler | Tests | Contract |
|-----------|-------|---------|-------|----------|
| SHOP_QUERY | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| FETCH_PRODUCTS | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| FETCH_ORDERS | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| FETCH_CUSTOMERS | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| FETCH_LOCATIONS | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| FETCH_COLLECTIONS | P4 | P4 | P4 | P4 |
| FETCH_GIFT_CARDS | P4 | P4 | P4 | P4 |
| FETCH_DISCOUNT_CODES | P4 | P4 | P4 | P4 |
| FETCH_PAYOUTS | P4 | P4 | P4 | P4 |
| FETCH_PAYOUT_TRANSACTIONS | P4 | P4 | P4 | P4 |
| FETCH_ABANDONED_CHECKOUTS | P4 | P4 | P4 | P4 |
| FETCH_REFUNDS | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| FETCH_PRODUCT_METAFIELDS | P4 | P4 | P4 | P4 |
| FETCH_ORDER_FULFILLMENTS | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| WEBHOOK_LIST_QUERY | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| PRODUCT_SET_MUTATION | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| PRODUCT_UPDATE_MUTATION | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| VARIANT_BULK_UPDATE | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| CUSTOMER_CREATE | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| CUSTOMER_UPDATE | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| ORDER_UPDATE | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| INVENTORY_SET | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| INVENTORY_ADJUST | ✅ P1 | ✅ P1 | ✅ P1 | P4 |
| COLLECTION_CREATE | P4 | P4 | P4 | P4 |
| DISCOUNT_BASIC_CREATE/UPDATE | P4 | P4 | P4 | P4 |
| DISCOUNT_FS_CREATE/UPDATE | P4 | P4 | P4 | P4 |
| DISCOUNT_DELETE | P4 | P4 | P4 | P4 |
| REFUND_CREATE | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| FULFILLMENT_CREATE | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| METAFIELD_SET/DELETE | P4 | P4 | P4 | P4 |
| WEBHOOK_CREATE/DELETE | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| ORDER_MARK_AS_PAID | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| GetFulfillmentOrders | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| Webhook delivery (outbound) | ✅ P2 | ✅ P2 | ✅ P2 | P4 |
| Bulk operations | P3 | P3 | P3 | P4 |
| Rate limit stress | P3 | — | P3 | — |
| Timeout/retry | P3 | — | P3 | — |
| Partial failures | P3 | P3 | P3 | — |

---

## Important Rules (from CLAUDE.md)

1. **No monkey patching** — all customization via `_make_api_client()` factory override
2. **No production use** — `RUNNING_ENV`/`ODOO_STAGE` checks everywhere
3. **Every feature needs tests** — no phase is complete without passing tests
4. **Do not jump phases** — current phase must be implemented, tested, documented first
5. **Odoo 19 specifics** — `models.Constraint` not `_sql_constraints`, `company_ids` not `company_id` on accounts, `privilege_id` not `category_id` on groups
6. **Test accounting setup** — see CLAUDE.md §1 for receivable/payable/income account requirements

## How to Run Tests

```bash
# Simulator tests only (fast, ~5s)
python3 /home/odoo/src/odoo/odoo-bin -d "$PGDATABASE" --addons-path="$ADDONS_PATH" \
    -u shopify_simulator --test-enable --stop-after-init --no-http

# Connector + Simulator tests
python3 /home/odoo/src/odoo/odoo-bin -d "$PGDATABASE" --addons-path="$ADDONS_PATH" \
    -u shopify_connector_pro,shopify_simulator --test-enable --stop-after-init --no-http

# Check for hidden SQL errors
python3 ... 2>&1 | grep -E "(FAIL|ERROR|psycopg2)"
```

## Environment

- **Odoo version:** 19.0
- **Platform:** Odoo.sh
- **Database:** `$PGDATABASE` (env var)
- **Addons path:** `$ADDONS_PATH` (env var)
- **Python:** 3.12
- **ODOO_STAGE:** dev
