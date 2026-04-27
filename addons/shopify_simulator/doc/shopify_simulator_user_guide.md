# Shopify Simulator — User Guide

> Internal QA / Developer guide for testing the Odoo Shopify Connector Pro
> using the Shopify Simulator module.

**Last updated:** Phase 2 (Orders + Fulfillments + Refunds + Webhooks)

---

## 1. Purpose of the Simulator

### What the simulator is used for
- End-to-end testing of the Shopify Connector Pro without a real Shopify store
- UAT (User Acceptance Testing) of import/export flows
- Testing webhook handling, HMAC validation, and event processing
- Testing error handling, rate limiting, and retry behavior
- Testing fulfillment and refund lifecycle flows
- Regression testing after connector changes

### What it is NOT used for
- Production use (hard-blocked by environment checks)
- Customer-facing deployment (not distributed publicly)
- Performance benchmarking against real Shopify API latency
- Testing Shopify App Store review flows

### ⚠️ Internal/Dev/Test Only
This module is **never installed in production**. It includes hard safeguards:
- `RUNNING_ENV`/`ODOO_STAGE` environment variable checks
- `ValidationError` if anyone tries to enable simulator in production
- Controller returns HTTP 403 in production environments

---

## 2. Prerequisites

- **Odoo branch:** 19.0
- **Required modules:** `shopify_connector_pro` (auto-dependency)
- **Python:** 3.12+
- **Database:** Any Odoo dev/staging database
- **Environment:** `RUNNING_ENV` or `ODOO_STAGE` must NOT be `production`
- **Access rights:** User must belong to `shopify_simulator.group_simulator_admin`

---

## 3. Installation / Upgrade Steps

### Install
```bash
# Via CLI
python3 odoo-bin -d $PGDATABASE --addons-path=$ADDONS_PATH \
    -i shopify_simulator --stop-after-init --no-http

# Via UI: Apps → search "Shopify Simulator" → Install
```

### Upgrade after code changes
```bash
python3 odoo-bin -d $PGDATABASE --addons-path=$ADDONS_PATH \
    -u shopify_simulator --stop-after-init --no-http
```

### Confirm installation
1. Navigate to **Settings → Technical → Modules** → search "shopify_simulator"
2. Status should be "Installed"
3. Navigate to **Shopify → Simulator** menu — should be visible

---

## 4. Backend Configuration Steps

### Enable simulator mode
1. Go to **Shopify → Backends** → select or create a backend
2. Click **"Create Simulator"** button (action_create_simulator)
3. This automatically:
   - Creates a `sim.shopify.config` record
   - Sets `use_simulator = True`
   - Updates `shop_url` to point to the local simulator endpoint
   - Copies the simulator access token to the backend

### Manual configuration
If you prefer manual setup:

| Field | Value |
|-------|-------|
| **Use Simulator** | ☑ Enabled |
| **Shop URL** | `http://localhost:8069/shopify-sim/{config_id}` |
| **Access Token** | Copy from sim config's `access_token` field |
| **Simulator Config** | Link to the sim.shopify.config record |

### Confirm connector points to simulator
1. Check backend's `shop_url` — should contain `/shopify-sim/`
2. Run **Test Connection** — should return the simulated shop name
3. Check backend's `use_simulator` checkbox is enabled

### Webhook secret (for webhook testing)
Set `webhook_secret` on the backend to a known value (e.g., `test_secret_123`).
The simulator uses this same secret when computing HMAC signatures for outbound webhooks.

---

## 5. Seed Data Setup

### Generate demo data programmatically
```python
# In Odoo Shell or test setUp
from odoo.addons.shopify_simulator.fixtures.demo_store import seed_demo_store
config = env['sim.shopify.config'].browse(CONFIG_ID)
seed_demo_store(env, config)
```

This creates:
- 6 products with variants (including edge cases: Unicode, missing SKU)
- 3 customers
- 3 orders (paid, pending, cancelled)
- 2 locations
- Inventory levels

### Generate individual records
```python
# Products
product = env['sim.shopify.product'].create({
    'config_id': config.id,
    'title': 'Test Widget',
    'product_type': 'Widgets',
    'vendor': 'Test Vendor',
    'status': 'ACTIVE',
})
# Variants are auto-created (one "Default Title" variant per product)

# Customers
customer = env['sim.shopify.customer'].create({
    'config_id': config.id,
    'first_name': 'Jane',
    'last_name': 'Doe',
    'email': 'jane@example.com',
})

# Orders with line items
order = env['sim.shopify.order'].create({
    'config_id': config.id,
    'name': '#1001',
    'total_price': 99.99,
    'financial_status': 'PAID',
    'customer_id': customer.id,
})
env['sim.shopify.order.line'].create({
    'order_id': order.id,
    'title': 'Test Widget',
    'quantity': 2,
    'variant_gid': product.variant_ids[0].shopify_gid,
    'unit_price': 49.99,
})
# Create fulfillment orders (required for fulfillment testing)
order.action_create_fulfillment_orders()
```

### Reset simulator data
```python
# Delete all data for a config
for model in ['sim.shopify.product', 'sim.shopify.customer',
              'sim.shopify.order', 'sim.shopify.fulfillment',
              'sim.shopify.refund', 'sim.shopify.webhook.subscription',
              'sim.shopify.inventory.level']:
    env[model].search([('config_id', '=', config.id)]).unlink()
```

---

## 6. Product Testing Flow

### Test product import
1. Seed products in the simulator (see §5)
2. Run **Shopify → Backends → [Backend] → Sync Products**
3. Check **Shopify → Products** for imported product bindings

### Test product export
1. Create a product in Odoo with a Shopify binding
2. Trigger export (manual or cron)
3. Check `sim.shopify.product` records for the newly created simulator product

### Validate results
- Product title, vendor, product_type match
- Variants have correct SKU, price, barcode
- Product images are linked (if applicable)

---

## 7. Customer Testing Flow

### Test customer import
1. Seed customers in the simulator
2. Run **Shopify → Backends → [Backend] → Sync Customers**
3. Check **Contacts** for imported customer records

### Validate
- First/last name, email, phone match
- Address fields mapped correctly
- Shopify binding created with correct GID

---

## 8. Order Testing Flow

### Test order import
1. Seed orders with line items in the simulator
2. Run **Shopify → Backends → [Backend] → Import Orders**
3. Check **Sales → Orders** for imported sale orders

### Test paid/pending/cancelled orders
- Seed orders with different `financial_status` values (PAID, PENDING, AUTHORIZED)
- Import and verify correct status mapping in Odoo

### Validate
- Sale order lines match order line items
- Taxes, discounts, shipping lines mapped
- Customer linked correctly
- Financial status reflected in Odoo

---

## 9. Inventory Testing Flow

### Test inventory sync
1. Seed inventory levels at simulator locations
2. Configure warehouse mapping on backend
3. Run inventory sync
4. Check stock quantities in Odoo

### Multi-location
- Seed inventory at multiple `sim.shopify.location` records
- Verify each location maps to correct Odoo warehouse/location

---

## 10. Fulfillment and Refund Testing Flow

### Test fulfillment creation (Odoo → Shopify)
1. Import an order from the simulator
2. Confirm the sale order in Odoo
3. Validate the delivery (stock.picking)
4. The connector's `push_fulfillment()` sends a `fulfillmentCreate` mutation
5. Check `sim.shopify.fulfillment` for the created record
6. Verify order's `fulfillment_status` updated to `FULFILLED` or `PARTIALLY_FULFILLED`

### Test partial fulfillment
1. Create an order with multiple line items or qty > 1
2. Validate a partial delivery (not all items)
3. Verify fulfillment order lines show remaining quantities
4. Verify order status is `PARTIALLY_FULFILLED`

### Test refund
1. Create a refund via the `refundCreate` mutation
2. Verify `sim.shopify.refund` record created
3. Verify order's `financial_status` updated to `PARTIALLY_REFUNDED` or `REFUNDED`

### Validate
- `sim.shopify.fulfillment.order` lines show correct remaining quantities
- Fulfillment records have tracking info
- Refund records have correct amounts and line items
- Order status transitions are correct

---

## 11. Webhook Testing Flow

### Register webhooks
The connector registers webhooks via `webhookSubscriptionCreate` mutation:
1. Go to backend → **Register Webhooks**
2. Verify `sim.shopify.webhook.subscription` records created
3. Check via **WEBHOOK_LIST_QUERY** that all topics appear

### Trigger valid webhooks
When simulator mutations fire (e.g., `fulfillmentCreate`, `refundCreate`),
outbound webhooks are automatically sent to registered callback URLs:
1. Register a webhook for `FULFILLMENTS_CREATE`
2. Create a fulfillment via the simulator
3. Check `shopify.webhook.log` for the received webhook
4. Run webhook processing cron
5. Verify Odoo records updated

### Trigger invalid HMAC webhooks
1. Set a wrong `webhook_secret` on the backend
2. Trigger a mutation that fires a webhook
3. Verify the connector returns HTTP 401

### Trigger duplicate webhooks
The connector deduplicates by `X-Shopify-Webhook-Id`:
1. Send the same webhook twice with the same ID
2. Verify only one `shopify.webhook.log` record exists

### Validate
- Check `shopify.webhook.log` for received webhooks
- Verify `state` transitions: pending → processing → done
- Verify dead_letter state after max retries

---

## 12. Error and Chaos Testing

### Enable error modes
Set `error_mode` on `sim.shopify.config`:

| Mode | Behavior |
|------|----------|
| `none` | Normal operation |
| `random_errors` | Random GraphQL errors at configured rate |
| `always_error` | Every request returns error |
| `rate_limit` | Returns 429 when budget exhausted |
| `timeout` | Sleeps 35s (exceeds client timeout) |
| `user_errors` | Mutations return userErrors |

### Test rate-limit simulation
1. Set `error_mode = 'rate_limit'`
2. Set `rate_limit_available = 0`
3. Make a request → should get HTTP 429
4. Reset: `config._reset_rate_limit()`

### Test retry logic
1. Set `error_mode = 'timeout'`
2. Trigger a sync operation
3. Verify the connector retries (check logs)

### Disable chaos modes
```python
config.write({'error_mode': 'none'})
config._reset_rate_limit()
```

---

## 13. Bulk Operation Testing

> **Status: Planned / Not Yet Implemented (Phase 3)**

Bulk operation simulation is planned for Phase 3:
- `bulkOperationRunQuery` mutation
- Status polling endpoint
- JSONL response serving

---

## 14. Test Coverage and Validation Checklist

| Test Area | Steps | Expected Result | Where to Validate | Status |
|-----------|-------|-----------------|-------------------|--------|
| Product import | Seed products → sync | Products in Odoo | Shopify → Products | ✅ P1 |
| Product export | Create Odoo product → export | Sim product created | sim.shopify.product | ✅ P1 |
| Customer import | Seed customers → sync | Contacts in Odoo | Contacts | ✅ P1 |
| Customer export | Create contact → export | Sim customer created | sim.shopify.customer | ✅ P1 |
| Order import | Seed orders → import | Sale orders in Odoo | Sales → Orders | ✅ P1 |
| Inventory sync | Set inventory → sync | Stock quantities match | Inventory | ✅ P1 |
| Location mapping | Seed locations → sync | Warehouses mapped | Settings → Warehouses | ✅ P1 |
| Fulfillment create | Validate picking → push | Sim fulfillment created | sim.shopify.fulfillment | ✅ P2 |
| Partial fulfillment | Partial pick → push | Remaining qty updated | sim.shopify.fulfillment.order.line | ✅ P2 |
| Refund create | Create refund mutation | Sim refund created | sim.shopify.refund | ✅ P2 |
| Order mark as paid | orderMarkAsPaid mutation | Status → PAID | sim.shopify.order | ✅ P2 |
| Webhook register | Register webhooks | Subscriptions created | sim.shopify.webhook.subscription | ✅ P2 |
| Webhook delivery | Mutation → outbound POST | Webhook log created | shopify.webhook.log | ✅ P2 |
| HMAC validation | Valid/invalid signatures | Accept/reject correctly | Webhook controller | ✅ P2 |
| Rate limit mode | Set error_mode → request | HTTP 429 returned | N/A | ✅ P1 |
| Timeout mode | Set error_mode → request | HTTP 504 (timeout) | N/A | ✅ P1 |
| Bulk operations | Run bulk query | JSONL response | Planned | ⏳ P3 |
| Stress test | 500+ products | Pagination stable | Planned | ⏳ P3 |
| Contract tests | Field-by-field validation | All fields present | Planned | ⏳ P4 |

---

## 15. Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Module installation error | Missing `shopify_connector_pro` | Install the connector first |
| "Simulator disabled in production" | `RUNNING_ENV=production` | Use a dev/staging environment |
| Test connection fails | Wrong access token or URL | Verify sim config token matches backend token |
| Connector still pointing to real Shopify | `use_simulator` not enabled | Check backend settings, re-run Create Simulator |
| Invalid webhook HMAC | `webhook_secret` mismatch | Ensure backend and simulator use same secret |
| Empty import results | No seed data in simulator | Run `seed_demo_store()` or create records manually |
| Pagination issues | Cursor encoding mismatch | Check `first` and `after` variables |
| Queue jobs not running | Cron not triggered | Manually run the cron or call the method directly |
| Cron not triggered | Module not upgraded | Upgrade the module: `-u shopify_simulator` |
| Missing mapping records | Products/customers not imported first | Import the base entities before orders |
| Rate-limit mode left enabled | `error_mode = 'rate_limit'` | Set `error_mode = 'none'` and call `_reset_rate_limit()` |
| Simulator data not reset | Old data persists | Unlink all sim records for the config |
| Fulfillment orders missing | `action_create_fulfillment_orders()` not called | Call it after creating order lines |

---

## 16. Limitations

### Not yet simulated (Phase 3+)
- Bulk operations (`bulkOperationRunQuery`)
- Intermittent timeout mode
- Circuit breaker testing
- Partial failure scenarios (some variants fail, others succeed)
- Large catalog stress tests (500+ products)

### Not yet simulated (Phase 4)
- Collections (smart + custom)
- Discount codes
- Gift cards
- Payouts and payout transactions
- Abandoned checkouts/carts
- Metafields
- Contract test suite (field-by-field validation)

### Known gaps
- Webhook outbound delivery is fire-and-forget (no retry on failure)
- Simulator doesn't enforce Shopify API rate limits realistically
  (cost deduction is approximated)
- No GraphQL introspection support
- Billing address always mirrors shipping address (simplification)
- Fulfillment orders use single-location simplification (one FO per order)

---

## 17. Developer Notes

### Add a new simulated GraphQL operation

1. **Model:** Create or update a model in `models/` with `_to_graphql_node()`
2. **Handler:** Create a handler function in `handlers/`
3. **Dispatch:** Add regex pattern to `QUERY_DISPATCH` or `MUTATION_DISPATCH`
   in `controllers/graphql_endpoint.py`
4. **Register:** Add the handler to `_QUERY_HANDLERS` or `_MUTATION_HANDLERS`
5. **Security:** Add ACL entry in `security/ir.model.access.csv`
6. **Test:** Add test in `tests/`

### Add a new webhook scenario

1. Add the topic to `TOPIC_ENUM_TO_REST` in `models/sim_webhook.py`
2. In the mutation handler, call:
   ```python
   env['sim.shopify.webhook.subscription']._fire_webhook(
       config, 'topic/name', payload_dict,
   )
   ```
3. Add a test verifying the webhook fires

### Add a fixture

Edit `fixtures/demo_store.py` and add records to the `seed_demo_store()` function.

### Add a test

1. Create a test file in `tests/` inheriting from `SimulatorTestCase`
2. Use `_seed_product()`, `_seed_customer()`, `_seed_order()` helpers
3. Use `_call_query()` / `_call_mutation()` to test handlers
4. Register in `tests/__init__.py`

### Update the coverage matrix

Update the table in `doc/PHASE_CONTINUATION.md` and this guide's §14 checklist.
