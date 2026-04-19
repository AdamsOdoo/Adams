# Adams Shopify Connector — UX & Configuration Design

> This document defines every screen, menu, button, and user flow. Agents MUST reference this when building views.

---

## 1. Menu Structure

```
Shopify (top-level app menu)
├── Dashboard                    → shopify.dashboard (kanban/custom)
├── Configuration
│   └── Shopify Stores          → shopify.backend (tree → form)
├── Operations
│   ├── Sync Now                → shopify.sync.wizard (wizard)
│   ├── Import Data             → shopify.import.wizard (wizard)
│   └── Register Webhooks       → action on backend
├── Sync Status
│   ├── Products                → shopify.product.binding (tree)
│   ├── Customers               → shopify.customer.binding (tree)
│   ├── Orders                  → shopify.order.binding (tree)
│   └── Inventory               → shopify.inventory.binding (tree)
├── Logs
│   ├── Sync Log                → shopify.sync.log (tree → form)
│   └── Webhook Log             → shopify.webhook.log (tree → form)
```

---

## 2. Dashboard (Landing Page)

The dashboard is the first screen users see. It provides at-a-glance sync health.

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│  ADAMS SHOPIFY CONNECTOR                          [Sync Now ▼]  │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│  Products     │  Customers    │  Orders       │  Inventory      │
│  ✓ 1,245      │  ✓ 3,421      │  ✓ 856        │  ✓ 1,245        │
│  ⚠ 3 errors   │  ✓ 0 errors   │  ⚠ 1 error    │  ✓ 0 errors     │
│  ○ 12 pending │  ○ 0 pending  │  ○ 5 pending  │  ○ 0 pending    │
│  [View All]   │  [View All]   │  [View All]   │  [View All]     │
├───────────────┴───────────────┴───────────────┴─────────────────┤
│  RECENT ACTIVITY                                                │
│  ─────────────────────────────────────────────────────────────  │
│  10:32  ✓ Exported 50 products to "My Store"                    │
│  10:30  ✓ Imported 3 orders from "My Store"                     │
│  10:28  ⚠ Failed to export product "Widget X" — rate limited    │
│  10:15  ✓ Webhook: products/update processed                    │
│  10:01  ✓ Inventory pushed for 120 variants                     │
│                                                    [View Logs]  │
├─────────────────────────────────────────────────────────────────┤
│  CONNECTED STORES                                               │
│  ─────────────────────────────────────────────────────────────  │
│  🟢 My Store (my-store.myshopify.com)  Last sync: 2 min ago    │
│  🟡 EU Store (eu-store.myshopify.com)  Last sync: 15 min ago   │
│                                              [Configure Stores] │
└─────────────────────────────────────────────────────────────────┘
```

### Dashboard Data Points
| Card | Data Source | Color Logic |
|------|-----------|-------------|
| Synced count | binding.search_count(sync_status='synced') | Green number |
| Error count | binding.search_count(sync_status='error') | Red if > 0, green if 0 |
| Pending count | binding.search_count(sync_status='pending') | Gray |
| Store status | backend.state + last_sync_date age | Green < 5min, Yellow < 30min, Red > 30min |

---

## 3. Backend Configuration (shopify.backend form)

This is the most critical configuration screen. Must be intuitive for non-technical users.

### Form Layout — Notebook Tabs

#### Tab 1: Connection
```
┌─────────────────────────────────────────────────────────┐
│  Shopify Store Configuration                            │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Store Name:        [___________________________]       │
│  Shop URL:          [____________].myshopify.com        │
│  Access Token:      [***************************]       │
│  API Version:       [2026-01            ▼]              │
│  Webhook Secret:    [***************************]       │
│                                                         │
│  Company:           [My Company          ▼]             │
│  Warehouse:         [Main Warehouse      ▼]             │
│                                                         │
│  Status:  🟢 Connected                                  │
│                                                         │
│  [Test Connection]  [Register Webhooks]                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Test Connection button**: Calls Shopify API, verifies credentials, shows:
- API version supported: Yes/No
- Scopes available: list
- Shop name from Shopify
- Rate limit info (bucket size, plan detection)

#### Tab 2: Sync Settings
```
┌─────────────────────────────────────────────────────────┐
│  Sync Configuration                                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  PRODUCTS                                               │
│  ☑ Enable product sync                                  │
│  Direction:    [Bidirectional     ▼]                    │
│  Interval:     [15] minutes                             │
│  Auto-export on change: ☑                               │
│                                                         │
│  CUSTOMERS                                              │
│  ☑ Enable customer sync                                 │
│  Direction:    [Shopify → Odoo    ▼]                    │
│  Interval:     [15] minutes                             │
│  Dedup by:     [Email             ▼]                    │
│                                                         │
│  ORDERS                                                 │
│  ☑ Enable order import                                  │
│  Interval:     [5] minutes                              │
│  Auto-create invoice: ☑                                 │
│  Auto-register payment: ☐                               │
│                                                         │
│  INVENTORY                                              │
│  ☑ Enable inventory push                                │
│  Interval:     [10] minutes                             │
│  Quantity type: [Free Quantity     ▼]                    │
│  Push on stock move: ☑                                  │
│                                                         │
│  GENERAL                                                │
│  Batch size:   [50]                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Tab 3: Field Mapping (Advanced)
```
┌─────────────────────────────────────────────────────────┐
│  Product Field Mapping                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Odoo Field        Shopify Field     Direction          │
│  ──────────────    ──────────────    ─────────          │
│  Name              title             ↔ Both             │
│  Description       bodyHtml          ↔ Both             │
│  Internal Ref      sku (variant)     ↔ Both             │
│  Sales Price       price (variant)   → Export           │
│  Weight            weight (variant)  ↔ Both             │
│  Barcode           barcode (variant) ↔ Both             │
│  Category          productType       → Export           │
│  Tags              tags              ↔ Both             │
│  Image             images            ↔ Both             │
│                                                         │
│  Price List:       [Public Pricelist  ▼]                │
│  (Used for export pricing)                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

#### Tab 4: Logs & Status
```
┌─────────────────────────────────────────────────────────┐
│  Sync Status for "My Store"                             │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Last sync:         March 28, 2026 10:32 AM             │
│  Products synced:   1,245 / 1,260                       │
│  Customers synced:  3,421 / 3,421                       │
│  Orders imported:   856 / 857                           │
│                                                         │
│  [View Sync Log]  [View Errors]  [View Webhooks]        │
│                                                         │
│  Recent Errors (3):                                     │
│  ⚠ Product "Widget X" — Shopify API rate limited        │
│    [Retry] [View Details]                               │
│  ⚠ Product "Gadget Y" — Title too long (max 255)       │
│    [Retry] [View Details]                               │
│  ⚠ Order #1057 — Customer not found                    │
│    [Retry] [View Details]                               │
│                                                         │
│  [Retry All Failed]                                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Shopify Tab on Existing Forms

### Product Form — "Shopify" Tab
Added to `product.template` form view via `xpath`.

```
┌─────────────────────────────────────────────────────────┐
│  Shopify Integration                                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ☐ Do not sync this product                             │
│                                                         │
│  Store            Shopify ID        Status    Last Sync │
│  ──────────────   ──────────────    ──────    ───────── │
│  My Store         gid://...123      ✓ Synced  10:32 AM  │
│  EU Store         gid://...456      ⚠ Error   09:15 AM  │
│                                                         │
│  [Sync Now]  [View on Shopify ↗]                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Customer Form — "Shopify" Tab
Added to `res.partner` form view.

```
┌─────────────────────────────────────────────────────────┐
│  Shopify Integration                                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Store            Shopify ID        Status    Last Sync │
│  ──────────────   ──────────────    ──────    ───────── │
│  My Store         gid://...789      ✓ Synced  09:45 AM  │
│                                                         │
│  [Sync Now]  [View on Shopify ↗]                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Sale Order Form — "Shopify" Tab
Added to `sale.order` form view.

```
┌─────────────────────────────────────────────────────────┐
│  Shopify Order Details                                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Shopify Order:     #1057                               │
│  Shopify ID:        gid://shopify/Order/123456          │
│  Financial Status:  Paid                                │
│  Fulfillment:       Unfulfilled                         │
│  Store:             My Store                            │
│  Imported:          March 28, 2026 10:30 AM             │
│                                                         │
│  [View on Shopify ↗]  [Push Fulfillment]                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 5. Sync Log View (shopify.sync.log)

### Tree View
```
Date/Time    | Store     | Entity   | Operation | Records | Status  | Duration
─────────────┼───────────┼──────────┼───────────┼─────────┼─────────┼─────────
10:32 AM     | My Store  | Products | Export    | 50      | ✓ Done  | 12s
10:30 AM     | My Store  | Orders   | Import    | 3       | ✓ Done  | 4s
10:28 AM     | My Store  | Products | Export    | 50      | ⚠ Partial| 8s
10:15 AM     | My Store  | Products | Webhook   | 1       | ✓ Done  | 1s
```

### Form View — Detail
```
Sync Operation Detail
─────────────────────
Store:       My Store
Entity:      Products
Operation:   Export
Started:     March 28, 2026 10:28:00 AM
Finished:    March 28, 2026 10:28:08 AM
Duration:    8 seconds

Results:
  Total:     50
  Success:   48
  Errors:    2
  Skipped:   0 (unchanged)

Error Details:
  Product "Widget X" (ID: 42) — 429 Too Many Requests
  Product "Gadget Y" (ID: 87) — Title exceeds 255 characters

[Retry Failed Records]
```

---

## 6. Wizards

### Sync Now Wizard
```
┌─────────────────────────────────────────────────────────┐
│  Sync Now                                               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Store:    [My Store              ▼]                    │
│                                                         │
│  What to sync:                                          │
│  ☑ Products                                             │
│  ☑ Customers                                            │
│  ☑ Orders                                               │
│  ☑ Inventory                                            │
│                                                         │
│  Direction:                                             │
│  ○ Export (Odoo → Shopify)                              │
│  ○ Import (Shopify → Odoo)                              │
│  ● Both directions                                      │
│                                                         │
│  Options:                                               │
│  ☐ Force full sync (ignore checksums)                   │
│  ☐ Include archived/draft records                       │
│                                                         │
│                          [Cancel]  [Start Sync]         │
└─────────────────────────────────────────────────────────┘
```

### Import Data Wizard (Initial Setup)
```
┌─────────────────────────────────────────────────────────┐
│  Import from Shopify                                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Store:    [My Store              ▼]                    │
│                                                         │
│  Import:                                                │
│  ☑ Products (estimated: 1,260 products)                 │
│  ☑ Customers (estimated: 3,500 customers)               │
│  ☑ Orders — last [60 ▼] days (estimated: 450 orders)   │
│  ☐ Locations                                            │
│                                                         │
│  ⚠ Initial import may take several minutes for large    │
│    stores. Products and customers are imported in        │
│    batches of 50. You can continue working while the    │
│    import runs in the background.                       │
│                                                         │
│                          [Cancel]  [Start Import]       │
└─────────────────────────────────────────────────────────┘
```

---

## 7. User Flows

### First-Time Setup Flow
```
1. Install adams_shopify module
2. Navigate to Shopify → Configuration → Shopify Stores
3. Click "Create"
4. Enter Shop URL + Access Token
5. Click "Test Connection" → see green status + shop info
6. Configure sync settings (Tab 2) — defaults are sensible
7. Click "Register Webhooks" → webhooks created on Shopify
8. Go to Shopify → Operations → Import Data
9. Select entities to import → click "Start Import"
10. Watch Dashboard for progress
11. Initial import complete → scheduled sync takes over
```

### Daily Operation Flow
```
1. Open Shopify → Dashboard
2. See sync health at a glance (green = good, red = needs attention)
3. If errors: click error count → see error list → click "Retry" or "View Details"
4. For manual sync: Shopify → Operations → Sync Now
5. For individual records: open product/customer/order → Shopify tab → "Sync Now"
```

### Error Resolution Flow
```
1. Dashboard shows "3 errors" on Products card
2. Click "View All" → see binding list filtered to status=error
3. Click a binding → see error message, last attempt time
4. Fix the issue (e.g., add missing required field)
5. Click "Retry" on the binding
6. Or: Backend → Logs tab → "Retry All Failed"
```

---

## 8. Design Principles for Views

1. **Sensible defaults**: Sync settings should work out of the box. User shouldn't need to configure 20 fields before first sync.
2. **Progressive disclosure**: Basic settings visible, advanced settings in separate tabs or behind "Show Advanced" toggle.
3. **Immediate feedback**: Every action (test connection, sync, retry) shows result immediately. No silent failures.
4. **Error transparency**: Errors show WHAT failed, WHY, and HOW TO FIX. Not just "Sync failed."
5. **One-click recovery**: Every failed record has a "Retry" button. Bulk retry for batch failures.
6. **Shopify links**: Every synced record has "View on Shopify ↗" link that opens the Shopify admin page.
7. **Non-blocking operations**: Sync and import run in background. User can continue working. Dashboard shows progress.
8. **Multi-store clarity**: Always clear which store a record belongs to. Store name visible in all list views.
