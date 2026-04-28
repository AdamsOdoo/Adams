# Shopify Simulator — User Guide

> Internal QA / Developer guide for testing the Odoo Shopify Connector Pro
> using the Shopify Simulator module.

**Last updated:** Phase 3+4 (Full UI, Collections, Metafields, Gift Cards,
Payouts, Abandoned Carts, Discounts, Scenarios, Checklist)

---

## 1. Purpose of the Simulator

### What it does
- End-to-end testing of the Shopify Connector Pro without a real Shopify store
- UAT of import/export flows with full UI controls
- Webhook testing with built-in HMAC signing and payload generation
- Error and chaos testing (rate limits, timeouts, random errors)
- Pre-built scenarios for common test flows
- Validation checklist to verify readiness before sync

### What it is NOT
- Not for production use (hard-blocked by environment checks)
- Not customer-facing (not distributed publicly)
- Not for performance benchmarking

### Safety
- `RUNNING_ENV`/`ODOO_STAGE` checks prevent production use
- Controller returns HTTP 403 in production
- `ValidationError` blocks enabling simulator in production

---

## 2. Prerequisites

- **Odoo:** 19.0
- **Required module:** `shopify_connector_pro` (auto-dependency)
- **Environment:** `RUNNING_ENV` or `ODOO_STAGE` must NOT be `production`
- **Access rights:** User in `shopify_simulator.group_simulator_admin`

---

## 3. Quick Start (UI-First)

### Step 1: Install
**Apps** > search "Shopify Simulator" > **Install**

### Step 2: Create simulator from backend
1. **Shopify > Backends** > select a backend
2. Click **"Create Simulator"** in the header
3. Done — the backend now points to the local simulator

### Step 3: Seed data
1. **Shopify > Simulator > Configurations** > open your config
2. Click **"Seed Demo Store"** to create 6 products, 3 customers, 3 orders
3. Or click **"Advanced Seed Wizard"** for custom quantities

### Step 4: Verify readiness
1. Click **"Run Checklist"** on the config form
2. All checks should pass (green checkmarks)

### Step 5: Test sync
1. Go back to the backend > run **Sync Products** / **Import Orders** / etc.
2. The connector syncs against the simulator instead of real Shopify

---

## 4. UI Navigation

### Menu Structure
```
Shopify > Simulator
  ├── Configurations          — Manage simulator configs
  ├── Seed Data Wizard        — Generate test data (modal)
  ├── Webhook Test Console    — Fire test webhooks (modal)
  ├── Scenario Library        — Pre-built test flows
  ├── Validation Checklist    — Pre-flight checks (modal)
  └── Simulator Records
        ├── Products
        ├── Customers
        ├── Orders
        ├── Locations
        ├── Inventory Levels
        ├── Fulfillments
        ├── Refunds
        ├── Webhook Subscriptions
        ├── Collections
        ├── Metafields
        ├── Gift Cards
        ├── Payouts
        ├── Abandoned Carts
        └── Discount Codes
```

### Config Form Features
- **Header buttons:** Seed Demo Store, Reset All Data, Reset Rate Limit,
  Advanced Seed Wizard, Webhook Console, Run Checklist
- **Stat buttons:** Click any count to jump to filtered list of records
- **Connection group:** Backend link, access token, simulator endpoint URL
- **Error Simulation group:** Error mode selector + rate limit controls

### Backend Form Integration
When `shopify_simulator` is installed:
- **"Create Simulator"** button appears on backends without simulator
- **"Simulator Mode Active"** banner shows on simulator-enabled backends

---

## 5. Seeding Test Data

### Quick seed (one click)
Config form > **"Seed Demo Store"** > creates curated edge-case data:
- 6 products (simple, multi-variant, Arabic title, draft, zero-price, archived)
- 3 customers (US, Saudi Arabia, no-email POS customer)
- 3 orders (paid, pending with discount, fulfilled zero-price)
- 2 locations (US + EU), inventory levels

### Advanced seed wizard
Config form > **"Advanced Seed Wizard"** or **Simulator > Seed Data Wizard**:
- Toggle which data types to seed (products, customers, orders, locations, inventory)
- Set exact quantities and variant count
- Choose **Append** (add to existing) or **Replace** (clear first)
- **Use Curated Demo Store** checkbox for the fixture above

### Manual record creation
Navigate to any **Simulator Records** submenu and create records directly
via the list/form views. All records auto-generate Shopify GIDs on save.

### Reset all data
Config form > **"Reset All Data"** (with confirmation) > deletes all
simulator records for this config and resets the GID counter to 1001.

---

## 6. Scenario Library

Navigate to **Simulator > Scenario Library** for pre-built test flows:

| Scenario | Category | What it does |
|----------|----------|-------------|
| Happy Path — Full Import | Import | Seeds complete demo store |
| Partial Refund Flow | Refunds | Creates order + partial refund |
| Rate Limit Exhaustion | Error Handling | Drains bucket, enables 429 mode |
| Multi-Location Inventory | Inventory | Product across 3 locations |
| Abandoned Cart Recovery | Abandoned Carts | Known + anonymous carts |
| Discount Code Varieties | Discounts | Percentage, fixed, free shipping |

**Run a scenario:** Click the **Run** button on any row (or open the form and
click **Run Scenario** in the header). Results appear as a notification.

---

## 7. Validation Checklist

Navigate to **Simulator > Validation Checklist** or click **"Run Checklist"**
on a config form. Checks include:

| Check | What it validates |
|-------|-------------------|
| Backend Linked | Backend exists and simulator mode is ON |
| Access Token Match | Config token matches backend token |
| Has Products | At least 1 active product exists |
| Has Customers | At least 1 customer exists |
| Has Orders | At least 1 order exists |
| Has Active Locations | At least 1 active location |
| Primary Location Exists | Exactly 1 primary location |
| Has Inventory Levels | At least 1 inventory level |
| Rate Limit Sufficient | Available budget > 100 |
| Error Mode: Normal | Error mode is 'none' |

---

## 8. Webhook Test Console

Navigate to **Simulator > Webhook Test Console** or click **"Webhook Console"**
on a config form.

### Usage
1. Select a **topic** (e.g., `products/update`, `orders/create`)
2. Select a **source record** (product, order, or customer)
3. Payload auto-generates — edit if needed
4. Click **"Fire Webhook"**
5. See response code + body in the **Last Response** tab

### Supported topics
`products/create`, `products/update`, `products/delete`,
`orders/create`, `orders/updated`, `orders/cancelled`,
`customers/create`, `customers/update`, `refunds/create`,
`inventory_levels/update`, `fulfillments/create`, `app/uninstalled`

### HMAC signing
The console signs payloads with `HMAC-SHA256` using the backend's
`webhook_secret` (or config's `access_token` as fallback).

---

## 9. Error and Chaos Testing

Set **Error Mode** on the config form:

| Mode | Behavior |
|------|----------|
| Normal | All requests succeed |
| Random GraphQL Errors | Random errors at configured % rate |
| Always Return Error | Every request returns error |
| Rate Limit Exhausted | Returns HTTP 429 when budget=0 |
| Timeout (35s) | Sleeps 35s per request |
| Return userErrors on Mutations | Mutations get fake validation error |

### Rate limit controls
- **Reset Rate Limit** button restores full budget
- Adjust **Bucket Size** and **Restore Rate** for fine-tuning

---

## 10. Simulated Feature Coverage

### Core Sync (Phase 1-2)
| Feature | Query Handler | Mutation Handler |
|---------|--------------|-----------------|
| Products | `products`, `single_product` | `product_set`, `product_create`, `product_update`, `variant_bulk_update` |
| Customers | `customers`, `single_customer` | `customer_create`, `customer_update` |
| Orders | `orders`, `single_order` | `order_update`, `order_mark_paid` |
| Inventory | — | `inventory_set`, `inventory_adjust` |
| Locations | `locations` | — |
| Fulfillments | `fulfillments` | `fulfillment_create` |
| Refunds | `refunds` | `refund_create` |
| Webhooks | `webhook_list` | `webhook_create`, `webhook_delete` |

### Extended Features (Phase 3+4)
| Feature | Query Handler | Mutation Handler |
|---------|--------------|-----------------|
| Collections | `collections` | `collection_create` |
| Metafields | `product_metafields` | `metafield_set`, `metafield_delete` |
| Gift Cards | `gift_cards` | — |
| Payouts | `payouts`, `payout_transactions` | — |
| Abandoned Carts | `abandoned_checkouts` | — |
| Discount Codes | `discount_codes` | `discount_basic_create/update`, `discount_fs_create/update`, `discount_delete` |

---

## 11. Testing Flows

### Product import
1. Seed products > run **Sync Products** on backend
2. Check **Shopify > Products** for imported bindings

### Order import
1. Seed orders > run **Import Orders** on backend
2. Check **Sales > Orders** for imported sale orders

### Fulfillment push
1. Import order > confirm sale order > validate delivery
2. Connector pushes `fulfillmentCreate` > check `sim.shopify.fulfillment`

### Refund
1. Trigger refund via connector or `refundCreate` mutation
2. Check `sim.shopify.refund` records

### Collection import
1. Create collections via Simulator Records > Collections
2. Run collection sync on backend

### Discount code sync
1. Create discount codes via Simulator Records > Discount Codes
2. Or run the "Discount Code Varieties" scenario

---

## 12. Troubleshooting

| Issue | Fix |
|-------|-----|
| Module install error | Install `shopify_connector_pro` first |
| "Simulator disabled in production" | Use dev/staging environment |
| Test connection fails | Verify config token matches backend token |
| Empty import results | Seed data first (Seed Demo Store button) |
| Rate limit blocking requests | Click "Reset Rate Limit" on config form |
| Error mode left enabled | Set Error Mode back to "Normal" |
| Fulfillment orders missing | Open order form > click "Create Fulfillment Orders" |

---

## 13. Limitations

### Not yet simulated
- Bulk operations (`bulkOperationRunQuery`)
- Circuit breaker testing
- Large catalog stress tests (500+ products)
- GraphQL introspection
- Gift card create/update mutations
- Payout create mutations (read-only simulation)
- Abandoned cart create mutations (read-only simulation)

### Known simplifications
- Webhook delivery is fire-and-forget (no retry on failure)
- Rate limit cost deduction is approximated
- Billing address mirrors shipping address
- Fulfillment orders use single-location simplification

---

## 14. Developer Notes

### Adding a new simulated GraphQL operation
1. **Model:** Create/update in `models/` with `_to_graphql_node()`
2. **Handler:** Create function in `handlers/`
3. **Dispatch:** Add regex to `QUERY_DISPATCH` / `MUTATION_DISPATCH`
4. **Register:** Add to `_QUERY_HANDLERS` / `_MUTATION_HANDLERS`
5. **Security:** Add ACL in `security/ir.model.access.csv`
6. **View:** Create XML view + menu entry
7. **Test:** Add test inheriting `SimulatorTestCase`

### Adding a scenario
Edit `models/sim_scenario.py`:
1. Define a function `_scenario_your_flow(env, config)` returning a message string
2. Add entry to the `SCENARIOS` list
3. Run module upgrade to sync scenarios to DB
