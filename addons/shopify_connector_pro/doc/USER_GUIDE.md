# Shopify Connector Pro — User Guide

## Table of Contents

1. [Installation](#installation)
2. [Initial Setup](#initial-setup)
3. [Connecting Your Shopify Store](#connecting-your-shopify-store)
4. [Onboarding Wizard](#onboarding-wizard)
5. [Product Synchronization](#product-synchronization)
6. [Order Management](#order-management)
7. [Customer Synchronization](#customer-synchronization)
8. [Inventory Management](#inventory-management)
9. [Fulfillment Sync](#fulfillment-sync)
10. [Refund Handling](#refund-handling)
11. [Payment Status Sync](#payment-status-sync)
12. [Financial Configuration](#financial-configuration)
13. [Multi-Currency and Shopify Markets](#multi-currency-and-shopify-markets)
14. [Abandoned Cart Recovery](#abandoned-cart-recovery)
15. [Gift Card Tracking](#gift-card-tracking)
16. [Metafield Synchronization](#metafield-synchronization)
17. [Promoter and Coupon System](#promoter-and-coupon-system)
18. [Webhooks](#webhooks)
19. [Multi-Store and Multi-Company](#multi-store-and-multi-company)
20. [B2B and Wholesale Isolation](#b2b-and-wholesale-isolation)
21. [Dashboard and Monitoring](#dashboard-and-monitoring)
    - [Store Health Kanban](#store-health-kanban-overview)
    - [Health Dashboard Tab](#health-dashboard-backend-form-tab)
    - [API Health Endpoint](#api-health-endpoint)
22. [Manager Dashboard](#manager-dashboard)
23. [Scheduled Actions](#scheduled-actions)
24. [Accounting Prerequisites](#accounting-prerequisites)
25. [Troubleshooting](#troubleshooting)
26. [FAQ](#faq)
27. [Financial Sync Directions & Limitations](#financial-sync-directions--limitations)

---

## Installation

### Prerequisites

- **Odoo 19.0** (Community or Enterprise edition)
- **Shopify store** on Basic plan or above
- **Shopify Custom App** with Admin API access token

### Install the Module

1. Place the `shopify_connector_pro` folder in your Odoo addons path
2. Update the apps list: **Settings > General Settings > Developer Tools > Update Apps List**
3. Search for "Shopify Connector Pro Ultimate Edition" and click **Install**

The module will automatically install its dependencies: Shopify Connector Pro Ultimate Edition — Base, `sale_management`, `stock`, `account`, and `mail`.

---

## Initial Setup

### Creating a Shopify Custom App

Before connecting Odoo, you need a Shopify Custom App with the right API permissions:

1. In your Shopify Admin, go to **Settings > Apps and sales channels > Develop apps**
2. Click **Create an app** and give it a name (e.g., "Odoo Connector")
3. Click **Configure Admin API scopes** and enable these scopes:
   - `read_products`, `write_products`
   - `read_orders`, `write_orders`
   - `read_customers`, `write_customers`
   - `read_inventory`, `write_inventory`
   - `read_fulfillments`, `write_fulfillments`
   - `read_assigned_fulfillment_orders`, `write_assigned_fulfillment_orders`
   - `read_shopify_payments_payouts`
   - `read_all_orders`
   - `read_discounts`, `write_discounts`
   - `read_locations`
4. Click **Install app** and copy the **Admin API access token** (starts with `shpat_`)
5. For webhooks, also note the **API secret key** (used for HMAC verification)

> **Important**: The access token is shown only once. Save it securely.

---

## Connecting Your Shopify Store

1. Navigate to **Shopify > Configuration > Shopify Stores**
2. Click **New** to create a backend record
3. Fill in the required fields:

| Field | Description | Example |
|-------|-------------|---------|
| **Name** | A display name for this store | "My Shopify Store" |
| **Shop URL** | Your myshopify.com domain | `my-store.myshopify.com` |
| **Access Token** | The `shpat_` token from your Custom App | `shpat_abc123...` |
| **Webhook Secret** | API secret key for webhook verification | (from Custom App settings) |
| **Company** | The Odoo company this store belongs to | Your Company |
| **Warehouse** | The warehouse for stock sync | Main Warehouse |

4. Click **Test Connection** in the header
5. If successful, the store status changes to **Connected** and displays your shop name and Shopify plan

---

## Onboarding Wizard

For first-time setup, use the guided wizard:

1. Go to **Shopify > Configuration > Setup Wizard**
2. Follow the 5 steps:

**Step 1 — Connection**: Enter credentials and test the connection

**Step 2 — Settings**: Configure sync preferences:
- Which entities to sync (products, customers, orders, inventory, collections)
- Sync direction for products and customers
- Auto-create invoices for paid orders
- Inventory quantity type (free qty vs. on-hand)

**Step 3 — Webhooks**: Register webhooks for real-time updates (requires a publicly accessible Odoo URL)

**Step 4 — Import**: Run your initial bulk import:
- Products from Shopify
- Customers from Shopify
- Historical orders (configurable: last 7, 30, 90, or 365 days)

**Step 5 — Done**: Review your setup and start using the connector

---

## Product Synchronization

### How It Works

Product sync runs automatically every **15 minutes** (configurable). The sync direction can be set to:

- **Odoo to Shopify**: Products created/updated in Odoo are pushed to Shopify
- **Shopify to Odoo**: Products created/updated on Shopify are pulled into Odoo
- **Bidirectional**: Changes flow in both directions

### Configuration

On the backend form, under the **Sync Settings** tab:

- **Sync Products**: Enable/disable product sync
- **Product Direction**: Choose sync direction
- **Product Interval**: How often to sync (in minutes)
- **Auto-export on Change**: Automatically push changes when a product is saved in Odoo

### What Gets Synced

- Product name and description
- Variants with SKU, barcode, price, and weight
- Product images (multiple per product)
- Attributes and attribute values (size, color, etc.)
- Prices based on the configured pricelist
- Collections/categories

### Bulk Export

To push multiple products at once:

1. Go to **Shopify > Operations > Bulk Export Products**
2. Select the backend (store)
3. Choose a filter:
   - **All products**: Export everything
   - **Unlinked products**: Only products not yet on Shopify
   - **Modified products**: Only products changed since last sync
4. Click **Export**

### Change Detection

Products use checksum-based change detection. If a product hasn't changed since the last sync, it's skipped. This makes sync cycles fast even with large catalogs.

---

## Order Management

### Order Import

Orders are imported automatically every **5 minutes**. Each import cycle:

1. Fetches new/updated orders from Shopify
2. Creates or updates sale orders in Odoo
3. Creates customer records (with deduplication)
4. Maps tax lines to Odoo taxes
5. Creates payment registrations
6. Optionally creates and validates invoices

### Configuration

On the backend form:

- **Import Orders**: Enable/disable order import
- **Order Interval**: How often to check for new orders (default: 5 min)
- **Auto-create Invoice**: Automatically create invoices for paid orders
- **Order Currency Mode**:
  - *Company Currency*: All orders use your Odoo company currency
  - *Shopify Currency*: Orders retain their original Shopify currency

### What Gets Imported

- Customer information (linked or created)
- Line items with product matching (by SKU)
- Taxes and tax mapping
- Discounts (line-level and order-level)
- Shipping lines
- Payment status and financial status
- Gift card payments
- Order tags and notes

### Viewing Imported Orders

- **Shopify > Sync Status > Orders**: View all Shopify order bindings
- Each binding shows the Shopify order ID, sync status, and error details if any
- Click through to the Odoo sale order

---

## Customer Synchronization

### Deduplication Strategy

The connector prevents duplicate customers using a configurable strategy:

| Strategy | How It Works |
|----------|-------------|
| **Email** (default) | Matches customers by email address |
| **Phone** | Matches customers by phone number |
| **Email + Phone** | Matches by email first, then phone if no email match |

Configure this under **Sync Settings > Customer Dedup By**.

### What Gets Synced

- Full name, email, phone
- Shipping and billing addresses (multiple per customer)
- Customer tags (mapped to Odoo partner categories)
- Guest checkout customers are also captured

### Bulk Export

Push Odoo customers to Shopify via **Shopify > Operations > Bulk Export Customers**.

---

## Inventory Management

### How It Works

Inventory sync pushes stock levels from Odoo to Shopify every **10 minutes** (configurable).

### Multi-Location Setup

1. On the backend form, click **Import Locations** to pull all Shopify locations
2. Go to **Shopify > Sync Status > Locations**
3. Map each Shopify location to an Odoo warehouse
4. Inventory is pushed per-location based on these mappings

### Quantity Modes

| Mode | Description |
|------|-------------|
| **Free Quantity** | Available stock after allocations (recommended for DTC) |
| **On Hand Quantity** | Total physical inventory |

### Delta Sync

The connector uses a smart delta queue:

1. When stock moves are completed in Odoo, affected products are queued
2. The inventory cron processes only queued items
3. Only products with actual quantity changes are pushed to Shopify

This is dramatically more efficient than pushing the full catalog each cycle.

---

## Fulfillment Sync

### Odoo to Shopify (Outbound)

When you validate a delivery order in Odoo for a Shopify order:

1. The connector detects the order has a Shopify binding
2. It matches delivery lines to Shopify line items by SKU
3. It creates a fulfillment on Shopify with tracking number and carrier
4. Partial shipments are supported (only shipped items are fulfilled)

### Shopify to Odoo (Inbound)

When fulfillments are created on Shopify (e.g., by a 3PL or dropshipper), the connector handles them based on your configuration:

| Mode | Behavior |
|------|----------|
| **Create Activity** (default) | Creates a scheduled activity for manual review |
| **Auto-validate** | Automatically validates the corresponding delivery in Odoo |
| **Ignore** | Tracks the status but takes no automatic action |

Configure this under the **Status Sync** tab on the backend form.

---

## Refund Handling

### Import (Shopify to Odoo)

Refunds are imported automatically every **30 minutes**:

- Each refund creates a credit note in Odoo
- Partial refunds adjust individual line items
- Full refunds create standard reversal credit notes
- Duplicate refunds are automatically detected and skipped

### Reverse Sync (Odoo to Shopify)

If enabled (**Status Sync > Reverse Sync: Refund**):

- When you post a credit note in Odoo for a Shopify order, a corresponding refund is created on Shopify
- B2B orders (sales channel = "direct") are automatically excluded

---

## Payment Status Sync

### How It Works

The connector tracks Shopify payment status transitions and automatically performs the corresponding accounting actions in Odoo. When Shopify notifies a status change (e.g., `authorized` to `paid`), the connector handles the invoice workflow without manual intervention.

### Supported Transitions

| From | To | Odoo Action |
|------|----|-------------|
| `authorized` | `paid` | Posts the draft invoice (Shopify captured payment) |
| `pending` | `paid` | Creates a new invoice, validates, and posts it |
| `pending` | `partially_paid` | Posts the invoice and creates a scheduled activity for follow-up |
| `pending` / `authorized` | `voided` | Cancels the draft invoice; if the order is unshipped, cancels the order |
| `paid` | `partially_refunded` | Updates status (refund handled separately by Refund Sync) |
| `paid` | `refunded` | Updates status (refund handled separately by Refund Sync) |

### Configuration

On the backend form, under the **Status Sync** tab:

- **Auto-handle Payment Transitions**: Enable/disable automatic invoice actions on payment status changes. When disabled, the status field on the binding still updates, but no invoices are created or posted.
- **Reverse Sync: Payment**: When enabled, posting an invoice in Odoo for a Shopify order calls `orderMarkAsPaid` on Shopify. This is **off by default** to prevent unintended API calls.

### Edge Cases

- **Voided with posted invoice**: If a payment is voided but the invoice is already posted, the connector does **not** auto-cancel the posted invoice (which could have legal/accounting implications). Instead, it creates a scheduled activity alerting the accountant to take manual action.
- **B2B orders excluded**: Payment sync only fires for orders with `sales_channel = 'shopify'`. B2B/direct orders are never affected.

### Prerequisites

For payment status sync to create invoices successfully, your products and partners must have proper accounting configuration:

- Products must have an **income account** set (on the product template or product category)
- Partners must have a **receivable account** (`property_account_receivable_id`)
- A **sales journal** must exist for the company

See [Accounting Prerequisites](#accounting-prerequisites) for setup instructions.

---

## Financial Configuration

### Tax Mapping

Map Shopify tax lines to Odoo taxes:

1. Go to the **Tax Mapping** tab on the backend form
2. Add mapping rules:

| Field | Description |
|-------|-------------|
| **Shopify Tax Name** | The tax name from Shopify (e.g., "VAT", "State Tax") |
| **Shopify Tax Rate** | The tax rate (e.g., 0.20 for 20%) |
| **Odoo Tax** | The corresponding Odoo tax record |
| **Fiscal Position** | Optional fiscal position to apply to the order |

The connector matches by name+rate first, then falls back to name-only. If no mapping is found, it uses Odoo defaults and logs a warning.

### Payment Gateway Mapping

Map Shopify payment gateways to Odoo journals:

1. Go to **Shopify > Configuration > Payment Gateway Mapping**
2. Add entries mapping gateway names (e.g., "shopify_payments", "paypal") to Odoo payment journals

### Payout Tracking

Shopify Payments payouts are imported every **6 hours**:

- View payouts at **Shopify > Sync Status > Payouts**
- Each payout shows: net amount, gross, fees, adjustments, and status
- Transaction-level detail includes: charges, refunds, disputes, reserves
- Each transaction links back to its source order

---

## Multi-Currency and Shopify Markets

### Overview

If you sell internationally using Shopify Markets, customers may pay in their local currency (EUR, GBP, JPY, etc.) while your Shopify store's base currency is different (e.g., USD). The connector supports three currency modes to handle this.

### Currency Modes

On the backend form, under the **Sync Settings** tab:

| Mode | Behavior | Best For |
|------|----------|----------|
| **Company Currency** (default) | All orders use your Odoo company's currency | Single-currency businesses |
| **Shopify Store Currency** | Orders use the Shopify store's base currency | Stores with one currency |
| **Customer Currency (Shopify Markets)** | Orders use the currency the customer actually paid in | International stores using Shopify Markets |

### How Customer Currency Mode Works

When set to **Customer Currency**:

1. The connector reads prices from `presentmentMoney` fields (the customer-facing amounts)
2. It finds or creates an Odoo pricelist for each new currency encountered
3. The sale order is created with the correct currency and presentment prices
4. Invoices inherit the order currency

### Setup

1. Open your Shopify store form in Odoo
2. Go to **Sync Settings** tab > **Order Currency Mode**
3. Select **Use Customer Currency (Shopify Markets)**
4. Ensure all required currencies are **active** in Odoo: **Accounting > Configuration > Currencies**
5. Click **Save**

> **Tip**: The connector activates currencies automatically when it encounters them. However, pre-activating expected currencies ensures exchange rates are configured before the first order arrives.

---

## Abandoned Cart Recovery

### Overview

Recover lost revenue by importing abandoned checkouts from Shopify into Odoo. The connector imports carts that were abandoned (items added but checkout not completed) and lets you follow up with quotations or recovery emails.

### Configuration

1. Open your Shopify store form
2. Go to **Sync Settings** tab > **Abandoned Carts** section
3. Check **Sync Abandoned Carts**
4. Optionally check **Auto-create Quotations** to automatically generate draft quotations
5. Click **Save**

Abandoned carts are imported every **30 minutes** by the cron job.

### Viewing Abandoned Carts

Navigate to **Shopify > Sync Status > Abandoned Carts**:

Each cart shows:
- **Customer Email** and name
- **Total Price** and currency
- **Abandoned At** timestamp
- **Line Items** (JSON detail of what was in the cart)
- **Recovery URL** — Shopify's native checkout recovery link
- **Status** — Not Recovered / Recovered

### Creating a Quotation from an Abandoned Cart

1. Open the abandoned cart record
2. Click **Create Quotation** at the top
3. The connector:
   - Finds or creates the customer in Odoo (using email deduplication)
   - Creates a draft `sale.order` with all cart line items
   - Links the quotation to the abandoned cart record
4. Send the quotation to the customer via email, or share the Shopify recovery URL

### Automatic Recovery Detection

When an order is imported from Shopify for the same customer and overlapping products, the connector automatically marks the abandoned cart as **Recovered** and links it to the new order.

### Manual Recovery

Click **Mark Recovered** on any abandoned cart to flag it manually (e.g., after a phone follow-up).

---

## Gift Card Tracking

### Overview

Shopify gift cards are imported into Odoo as read-only tracking records. This gives your team visibility into outstanding gift card balances without leaving Odoo.

### What Gets Imported

| Field | Description |
|-------|-------------|
| **Code (masked)** | Last 4 characters only (e.g., `••••ABCD`) for security |
| **Initial Amount** | The original gift card value |
| **Current Balance** | Remaining balance |
| **Status** | Active, Disabled, or Expired |
| **Expires On** | Expiration date (if set) |
| **Customer** | Linked to the Odoo partner who received/owns the card |

### Viewing Gift Cards

Navigate to **Shopify > Sync Status > Gift Cards** to see all imported gift cards.

### Import Schedule

Gift cards are imported as part of the regular sync cycle. They are **read-only** in Odoo — all gift card management (issuing, disabling, adjusting balances) happens in Shopify.

### Gift Card Payments on Orders

When a Shopify order is partially or fully paid with a gift card, the connector:
1. Records the gift card payment as a separate payment line on the sale order
2. The remaining balance (if any) is paid by the customer's other payment method
3. Both payments are visible on the order's payment registration

---

## Metafield Synchronization

### Overview

Shopify metafields are custom data fields attached to products, variants, customers, or orders. The connector supports bidirectional metafield sync, allowing you to map Shopify metafields to Odoo fields without writing code.

### Configuration

1. Open your Shopify store form
2. Go to the **Field Mappings** tab
3. Click **Add a line** to create a metafield mapping:

| Field | Description | Example |
|-------|-------------|---------|
| **Entity** | Which Shopify object | Product / Customer / Order |
| **Odoo Field** | The Odoo field to map to | `x_studio_material` (custom field) |
| **Shopify Field** | Metafield namespace.key path | `metafields.custom.material` |
| **Direction** | Sync direction | Export / Import / Both |

4. Click **Save**

### How It Works

- **Import**: When products/customers/orders are imported, the connector reads the mapped metafield values from Shopify and writes them to the corresponding Odoo fields
- **Export**: When records are exported, the connector reads the Odoo field values and creates/updates the metafield on Shopify
- **Change detection**: Metafield values are included in the checksum calculation, so unchanged metafields are not re-synced

### Supported Metafield Types

The connector handles all Shopify metafield types: `single_line_text_field`, `multi_line_text_field`, `number_integer`, `number_decimal`, `boolean`, `date`, `json`, `url`, `color`, and `rich_text_field`.

---

## Promoter and Coupon System

### Setting Up Promoters

1. Go to **Shopify > Promoters**
2. Click **New** and fill in:
   - **Contact**: Link to an Odoo contact
   - **Status**: Active or Inactive
   - **Commission Type**: Percentage or Fixed Amount
   - **Commission Value**: The rate or amount
3. Save the promoter

### Creating Discount Codes

1. On the promoter form, go to the **Discount Codes** tab
2. Click **Add a line** and configure:
   - **Code**: The discount code (or auto-generate with prefix)
   - **Discount Type**: Percentage, Fixed Amount, or Free Shipping
   - **Value**: The discount amount
   - **Minimum Order**: Minimum order amount required
   - **Usage Limit**: Maximum number of uses
   - **Start/End Date**: Activation window

### How Tracking Works

When an imported Shopify order contains a promoter's discount code:

1. The connector automatically detects the code usage
2. Records the usage against the promoter
3. Calculates commission based on the order subtotal
4. Updates the promoter's performance metrics

### Performance Dashboard

Each promoter record shows:

- Total orders using their code
- Total revenue generated
- Total discounts given
- Total commissions earned

---

## Webhooks

### Registration

1. Ensure your Odoo instance is publicly accessible via HTTPS
2. Set the **Webhook Secret** on the backend form (from your Shopify Custom App's API secret key)
3. Click **Register Webhooks** in the backend form header

### Registered Events

| Event | Trigger |
|-------|---------|
| Products create/update/delete | Product changes on Shopify |
| Orders create/update/cancel | Order changes on Shopify |
| Customers create/update | Customer changes on Shopify |
| Inventory levels update | Stock changes on Shopify |
| Fulfillments create | New fulfillments on Shopify |
| App uninstalled | Custom app removed from Shopify |

### Monitoring

- View webhook logs at **Shopify > Logs > Webhook Log**
- Filter by state: Pending, Processing, Done, Error, Dead Letter, Skipped
- Failed webhooks are retried up to 5 times automatically
- After 5 failures, events move to the **Dead Letter** state for manual review

### Dead Letter Recovery

1. Go to **Shopify > Logs > Webhook Log** and filter by "Dead Letter"
2. Review the error message
3. Fix the underlying issue
4. Click **Retry** on the webhook log record

---

## Multi-Store and Multi-Company

### Multiple Shopify Stores

Connect as many Shopify stores as needed:

1. Create a separate backend record for each store
2. Each store has its own sync settings, tax mappings, and payment journals
3. Stores can share the same Odoo product catalog or use separate ones

### Multi-Company Setup

For organizations with multiple Odoo companies:

1. Each backend is linked to a specific Odoo company via the **Company** field
2. All data created by the connector is scoped to that company
3. Record rules enforce strict data isolation between companies
4. Users can only see data for companies they have access to

---

## B2B and Wholesale Isolation

If you sell both B2B (directly through Odoo) and DTC (through Shopify):

### How It Works

- Every sale order has a **Sales Channel** field: "Direct" or "Shopify"
- Orders imported from Shopify are tagged as "Shopify"
- Orders created manually in Odoo default to "Direct"
- All outbound sync actions (fulfillment push, payment sync, inventory updates) check this field
- Only orders with `sales_channel = 'shopify'` trigger sync

### What This Means

- Your B2B/wholesale orders are **never** sent to Shopify
- Delivering a B2B order does **not** push a fulfillment to Shopify
- Posting a B2B invoice does **not** mark anything as paid on Shopify
- Your wholesale pricing remains private

No configuration needed — this works automatically.

---

## Dashboard and Monitoring

### Store Health Kanban (Overview)

Access via **Shopify > Dashboard** — a kanban card for every connected store:

Each card shows at a glance:
- Connection status badge: **Connected** (green) / **Error** (red) / **Not Connected** (grey)
- Synced counts: products, customers, orders, inventory, collections, refunds, payouts
- Error counts with colour-coded badges
- Inventory error indicator (orange badge when inventory bindings have errors)
- Active promoter count
- Today's sync log count
- Last sync timestamp
- **Webhook queue badge** — orange badge showing pending webhook count when > 0
- **Payment mismatch warning** — red badge when Shopify shows paid but no Odoo invoice exists
- **Permanent error badge** — bindings that exhausted all retry attempts

### Health Dashboard (Backend Form Tab)

Open any store record (**Shopify > Configuration > Shopify Stores**) and click the **Health Dashboard** tab for full diagnostic detail.

#### Section 1 — Overall Health Banner

A colour-coded alert bar shows your integration health at a glance:

| Colour | Condition | Meaning |
|--------|-----------|---------|
| Green | Sync health ≥ 90 % | All systems normal |
| Yellow | Sync health 70–89 % | Some records have errors |
| Red | Sync health < 70 % | Significant errors — attention needed |

The health percentage is calculated as: `(synced records) / (synced + errored records) × 100`.

#### Section 2 — Connection & Overall Status

Shows the current backend state, shop name, last sync timestamp, today's sync count, and the overall health percentage score.

#### Section 3 — Per-Entity Last Sync Times

A 2×3 grid showing the most recent successful sync time for each entity type:

| Entity | Field |
|--------|-------|
| Products | Last sync time |
| Customers | Last sync time |
| Orders | Last sync time |
| Inventory | Last sync time |
| Fulfillments | Last sync time |
| Collections | Last sync time |

If a sync time is more than 24 hours ago, it will stand out naturally (Odoo renders old datetimes in a warning colour). Use this to detect stalled crons or connectivity gaps.

#### Section 4 — Sync Counts

Complete binding counts broken down by entity and status:

| Entity | Synced | Errors |
|--------|--------|--------|
| Products | ✓ | ✓ |
| Customers | ✓ | ✓ |
| Orders | ✓ | ✓ |
| Inventory | ✓ | ✓ |
| Collections | ✓ | — |
| Refunds | ✓ | — |
| Payouts | ✓ | — |
| Abandoned Carts | ✓ | — |

#### Section 5 — Data Integrity Alerts

This section is only visible when there are mismatches. It shows:

- **Payment mismatches** — Shopify orders marked `paid` but no posted invoice exists in Odoo. Click **View Payment Mismatches** to open the filtered list and investigate.
- **Fulfillment mismatches** — Shopify orders marked `fulfilled` but the corresponding Odoo delivery is still pending/draft. Click **View Fulfillment Mismatches** to review.
- **Permanent errors** — Bindings that have exhausted all retry attempts (default: 5). These require manual intervention.

> **What to do about mismatches**: Payment mismatches usually indicate an auto-invoice configuration gap or a failed payment registration. Fulfillment mismatches may mean a webhook was lost or the delivery was validated outside of normal flow. Use the "Run Reconciliation" button to auto-fix simple cases.

#### Section 6 — Webhook Queue

Shows the current state of your webhook pipeline:
- **Pending** — events received but not yet processed (processed every 1 minute by cron)
- **Dead Letter** — events that failed all 5 retry attempts

A high pending count indicates the webhook cron may be delayed or not running. Dead-letter events require manual investigation — click **Shopify > Logs > Webhook Log** and filter by "Dead Letter".

#### Section 7 — Quick Actions

| Button | What it does |
|--------|-------------|
| **Test Connection** | Re-tests the API connection and updates status |
| **Retry All Errors** | Resets ALL error bindings across all entity types to `pending`, clearing the error message and retry count. They will be re-processed on the next cron run. |
| **View Sync Logs** | Opens **Shopify > Logs > Sync Log** filtered to this backend |
| **View Error Details** | Opens sync logs filtered to errors for this backend |
| **View Payment Mismatches** | Opens order bindings where Shopify shows paid but no Odoo invoice exists |
| **View Fulfillment Mismatches** | Opens order bindings where Shopify shows fulfilled but Odoo delivery is pending |
| **Run Reconciliation** | Triggers the reconciliation check immediately for this backend (normally runs every 6 hours) |

> **Retry All Errors** is only visible when there are error bindings. **View Error Details** is only visible when errors exist.

### Sync Logs

Access via **Shopify > Logs > Sync Log**:

- View all sync operations with timestamps and duration
- Filter by entity type, operation (import/export), and date
- Graph view for visual trends
- Pivot table for analysis
- Each log entry shows: records processed, successes, errors, and skipped

### API Health Endpoint

A JSON health check endpoint is available for external monitoring:

```
GET /shopify/health/<backend_id>
```

Response includes:
```json
{
  "status": "ok",
  "shop_name": "My Store",
  "state": "connected",
  "sync_health_pct": 97.3,
  "product_bind_count": 412,
  "order_bind_count": 1840,
  "customer_bind_count": 923,
  "inventory_bind_count": 412,
  "errors_by_entity": {
    "product": 2,
    "order": 0,
    "customer": 11
  },
  "last_sync_per_entity": {
    "product": "2026-04-17T10:30:00",
    "order": "2026-04-17T11:15:00",
    "customer": "2026-04-17T10:45:00"
  },
  "data_integrity": {
    "payment_mismatches": 0,
    "fulfillment_mismatches": 2,
    "permanent_errors": 0
  },
  "webhook_pending_count": 0,
  "webhook_dead_letter_count": 0
}
```

Use this endpoint to integrate with Uptime Robot, Datadog, or any HTTP-based monitoring system.

### Error Investigation

1. Check error counts on the Dashboard kanban or the Health Dashboard tab
2. Click **View Error Details** to see affected bindings
3. Review the error message on each binding record
4. Fix the underlying issue (e.g. missing tax mapping, invalid product data)
5. Click **Retry All Errors** to reset all errored bindings, or use the **Bulk Retry Wizard** for selective retry

---

## Manager Dashboard

### Overview

The **Shopify Manager Dashboard** is a companion module (`shopify_connector_pro_dashboard`) that provides a visual, executive-level overview of your Shopify operations. It aggregates data across all connected stores into interactive charts and KPI cards.

### Installation

The Manager Dashboard is a separate module that depends on `shopify_connector_pro`. Install it from **Apps > Search "Shopify Manager Dashboard" > Install**.

### Accessing the Dashboard

Navigate to **Shopify > Manager Dashboard** to open the interactive dashboard view.

### KPI Cards

The dashboard displays the following metrics, filterable by time period (Today, Week-to-Date, Month-to-Date, Year-to-Date, or Custom range):

| KPI | Description |
|-----|-------------|
| **Revenue** | Total sales revenue for the period, with comparison to prior period |
| **Average Order Value** | Revenue divided by order count |
| **Order Count** | Total Shopify orders imported |
| **Customer Count** | New customers created during the period |
| **Refund Rate** | Refund amount as a percentage of revenue |
| **Abandoned Cart Recovery Rate** | Percentage of abandoned carts that converted to orders |

### Charts and Tables

- **Sales Trend**: Line chart showing daily revenue over the selected period
- **Top Products**: Best-selling products by revenue and quantity
- **Top Customers**: Highest-spending customers
- **Delivery Status**: Breakdown of pending, shipped, delivered, and failed deliveries
- **Refund Summary**: Refund count and total amount
- **Payout Overview**: Payout status breakdown and total disbursed amount

### Alerts

The dashboard highlights operational issues requiring attention:

| Alert | Trigger |
|-------|---------|
| **High Refund Rate** | Refund rate exceeds 5% of revenue |
| **Stale Syncs** | Any entity hasn't synced in over 24 hours |
| **Error Spike** | Error count exceeds 10% of total bindings |
| **Webhook Backlog** | More than 50 pending webhooks |

### Access Control

The Manager Dashboard is read-only. All users with the `Shopify User` access group can view it. No data can be modified from the dashboard.

---

## Scheduled Actions

All sync operations run as Odoo scheduled actions (crons). To adjust:

1. Go to **Settings > Technical > Automation > Scheduled Actions**
2. Search for "Shopify"
3. Modify the interval or enable/disable individual crons

| Action | Default Interval | Description |
|--------|-----------------|-------------|
| Process Webhooks | 1 minute | Process queued webhook events |
| Process Import Jobs | 2 minutes | Run background import jobs |
| Import Orders | 5 minutes | Fetch new orders from Shopify |
| Push Inventory | 10 minutes | Push stock level changes |
| Sync Products | 15 minutes | Bidirectional product sync |
| Sync Customers | 15 minutes | Bidirectional customer sync |
| Import Refunds | 30 minutes | Import new refunds |
| Sync Discount Codes | 30 minutes | Export promoter discount codes |
| Sync Collections | 1 hour | Sync product collections |
| Import Payouts | 6 hours | Import Shopify payouts |
| Reconciliation Check | 6 hours | Detect data drift |
| Webhook Log Cleanup | Daily | Purge old webhook logs |

---

## Accounting Prerequisites

For the connector to create and post invoices automatically (e.g., auto-invoice on paid orders, payment status sync), your Odoo accounting configuration must be complete. Missing accounting setup is the **most common cause of invoice creation failures**.

### Required Configuration

#### 1. Chart of Accounts

Your Odoo company must have a chart of accounts installed. This is typically done during initial Odoo setup. Verify by going to **Accounting > Configuration > Chart of Accounts** and confirming accounts exist.

#### 2. Income Account on Products

Every product sold through Shopify must have an income account configured. This can be set at two levels:

**Option A — Product Category (recommended for bulk setup):**
1. Go to **Inventory > Configuration > Product Categories**
2. Open the category used by your Shopify products
3. In the **Account Properties** section, set **Income Account** (e.g., "Product Sales" or "Revenue")
4. All products in this category will inherit the income account

**Option B — Individual Product:**
1. Open the product template
2. Go to the **Accounting** tab
3. Set the **Income Account** field

> **If the income account is missing**, invoice creation will fail with a database constraint error. The connector detects this condition and skips auto-invoicing with a warning log and scheduled activity, but it's best to configure accounts proactively.

#### 3. Receivable Account on Customers

Odoo requires a receivable account on each partner for invoice line creation. In most setups, this is configured automatically via the chart of accounts defaults. Verify by:

1. Opening any customer record
2. Going to the **Accounting** tab (or **Sales & Purchase** tab depending on Odoo version)
3. Confirming **Account Receivable** and **Account Payable** are set

If these are blank, set them to your default receivable/payable accounts, or configure defaults via **Accounting > Configuration > Settings > Default Accounts**.

#### 4. Sales Journal

A sales journal must exist for each company using the connector:

1. Go to **Accounting > Configuration > Journals**
2. Verify a journal with **Type = Sale** exists
3. If not, create one (e.g., "Shopify Sales", code "SHOP", type "Sale")

#### 5. Bank/Payment Journal (for payment registration)

If you want the connector to register payments automatically:

1. Go to **Accounting > Configuration > Journals**
2. Create a journal for each Shopify payment gateway (e.g., "Shopify Payments", type "Bank")
3. Map these journals in **Shopify > Configuration > Payment Gateways**

### Diagnostic Checklist

If auto-invoicing is not working, check these in order:

1. Is **Auto-create Invoice** enabled on the backend? (Sync Settings tab)
2. Does the product have an income account? (Product > Accounting tab, or Product Category)
3. Does the customer have a receivable account? (Partner > Accounting tab)
4. Does a sales journal exist for the company?
5. Check **Shopify > Logs > Sync Log** for invoice-related warnings
6. Check the Odoo server log for `account_move_line_check_accountable_required_fields` errors

---

## Troubleshooting

### Connection Issues

**"Connection failed: 401 Unauthorized"**
- Your access token is invalid or expired
- Generate a new token from your Shopify Custom App settings
- Make sure the token starts with `shpat_`

**"Shop URL must be a valid myshopify.com domain"**
- Enter only the domain: `my-store.myshopify.com`
- Don't include `https://` or trailing paths

**"Circuit breaker open"**
- The Shopify API has been returning errors repeatedly
- Wait 5 minutes for automatic recovery
- If persistent, check Shopify's status page at status.shopify.com

### Sync Issues

**Products not syncing**
1. Check **Shopify > Sync Status > Products** for error bindings
2. Verify the product has required fields (name, at least one variant)
3. Check **Shopify > Logs > Sync Log** for detailed error messages
4. Try a manual sync via **Operations > Manual Sync**

**Orders missing**
1. Verify the order date falls within the import window
2. Check **Shopify > Sync Status > Orders** for the binding
3. Run a manual import from **Operations > Import Data**
4. Check webhook logs if using real-time sync

**Inventory not updating on Shopify**
1. Confirm a Shopify location is configured:
   - Either the legacy `Shopify Location ID` on the backend, or
   - Mapped locations via **Sync Status > Locations**
2. Verify the product variant has a Shopify binding
3. Check that the stock actually changed (delta sync skips unchanged items)

**Duplicate customers**
1. Check the dedup strategy on the backend (**Sync Settings > Customer Dedup By**)
2. For email+phone dedup, ensure customer records in Odoo have matching email/phone fields
3. Manually merge duplicates in Odoo using standard Odoo dedup tools

### Webhook Issues

**Webhooks not arriving**
1. Your Odoo instance must be publicly accessible via HTTPS
2. Check that `web.base.url` system parameter is set correctly
3. Use `ngrok` or similar for development/testing
4. Verify the webhook secret matches your Shopify Custom App

**429 Too Many Requests on webhook endpoint**
- The connector rate-limits incoming webhooks to 200/minute per store
- This protects against abuse; legitimate traffic rarely hits this limit
- If you see this frequently, check for webhook registration duplicates on Shopify

**Dead-letter webhooks accumulating**
1. Go to **Shopify > Logs > Webhook Log** and filter by "Dead Letter"
2. Review error messages — they indicate what went wrong
3. Common causes: missing product mappings, tax configuration issues, data validation errors
4. Fix the root cause, then click **Retry** on the webhook record

### Performance Issues

**Sync taking too long**
1. Reduce `batch_size` on the backend (smaller batches = less memory)
2. Increase sync intervals for non-critical entities
3. Use the **Reconciliation Check** to identify stuck records
4. Check the **Sync Log** for operations that take unusually long

**Rate limit errors (429 from Shopify)**
- The client handles this automatically via adaptive rate limiting
- If persistent, reduce `batch_size` on the backend
- Consider spreading sync across multiple cron windows

### Multi-Company Issues

**Can't see data from another store**
- Each backend is scoped to a company
- Switch to the correct company in your Odoo user menu
- Record rules enforce isolation — this is by design

---

## FAQ

**Q: Does this work with Shopify Basic plan?**
A: Yes. The connector works with all Shopify plans: Basic, Shopify, Advanced, and Plus.

**Q: Can I connect multiple Shopify stores?**
A: Yes. Create a separate backend record for each store. There is no limit on the number of stores.

**Q: Does it work with Odoo Community edition?**
A: Yes. The connector works with both Odoo Community and Enterprise editions.

**Q: What happens if Shopify is down?**
A: The circuit breaker pattern detects API failures and stops sending requests. Once Shopify recovers, sync resumes automatically. No data is lost — pending items are queued.

**Q: Can I sync only specific products?**
A: Products with Shopify bindings are synced. You control which products get bindings via the bulk export wizard or by creating bindings manually.

**Q: How does it handle product deletions?**
A: Product deletions on Shopify are received via webhook. The binding is marked accordingly, but the Odoo product is not deleted (to preserve historical order data).

**Q: Is the sync real-time?**
A: Webhooks provide near real-time sync for most events (products, orders, customers). For entities without webhook support, scheduled crons run at configurable intervals (as low as 1 minute).

**Q: What about Shopify's REST API deprecation?**
A: This connector uses exclusively the GraphQL Admin API (version 2026-01), which is Shopify's current and actively developed API. It is not affected by the REST API deprecation.

**Q: Can I customize which fields are synced?**
A: Yes. Use the **Field Mapping** tab on the backend form to control which fields sync, in which direction, and for which entity types. No code changes required.

**Q: How do I handle taxes for different countries?**
A: Use the **Tax Mapping** tab to create rules that match Shopify tax names/rates to Odoo taxes. You can also assign fiscal positions automatically based on tax mappings.

**Q: Why are invoices not being created for paid orders?**
A: This is almost always a missing accounting configuration. Check that: (1) The product has an income account set on its template or category, (2) The customer has a receivable account, (3) A sales journal exists. See the [Accounting Prerequisites](#accounting-prerequisites) section for detailed setup instructions.

**Q: Does it work with Shopify Markets (multi-currency)?**
A: Yes. Set the **Order Currency Mode** to "Customer Currency" on the backend. Orders will be created using the currency the customer paid in, with prices from Shopify's `presentmentMoney` fields. See [Multi-Currency and Shopify Markets](#multi-currency-and-shopify-markets).

**Q: Can I recover abandoned carts?**
A: Yes. Enable **Sync Abandoned Carts** on the backend. Abandoned checkouts are imported every 30 minutes. You can create Odoo quotations from them or use Shopify's recovery URL. See [Abandoned Cart Recovery](#abandoned-cart-recovery).

**Q: What API does this connector use?**
A: The connector uses exclusively Shopify's **GraphQL Admin API (version 2026-01)** — the only API Shopify actively develops. It does not use the deprecated REST API, making it future-proof against Shopify's ongoing API migration.

**Q: How does it compare to other Shopify connectors on the Odoo App Store?**
A: This connector offers significantly more features than competing connectors, including: payment status sync, reverse payment sync (Odoo to Shopify), payout import with transaction detail, gift card tracking, promoter/affiliate system, abandoned cart recovery, metafield sync, B2B isolation, automated reconciliation, dead-letter webhook queue, and checksum-based change detection. See the Commercial Documentation for a detailed comparison.

**Q: Is there a Manager Dashboard?**
A: Yes. Install the companion module **Shopify Manager Dashboard** for an executive-level view with revenue KPIs, sales trends, top products/customers, delivery status, and refund analytics. See [Manager Dashboard](#manager-dashboard).

**Q: What happens when invoice creation fails due to missing accounts?**
A: The connector uses savepoints to isolate invoice creation failures. If an invoice cannot be created (e.g., missing income account), the order is still imported and confirmed successfully. A warning is logged and a scheduled activity is created on the order, alerting the responsible user to fix the accounting setup and create the invoice manually.

---

## Financial Sync Directions & Limitations

This section documents exactly what financial data flows between Shopify and Odoo, what controls it, and what does NOT sync.

### Automatic Sync: Shopify to Odoo

These flows run automatically via scheduled actions (crons). No user action is required.

| Shopify Event | Odoo Result | Cron Frequency |
|---|---|---|
| Order paid | Invoice created and posted | Every 5 minutes |
| Payment captured | Payment registered and reconciled with invoice | Every 5 minutes |
| Financial status changed to "voided" | Draft invoices cancelled | Every 5 minutes |
| Refund issued | Credit note (out_refund) created | Every 30 minutes |
| Financial status updated | Order binding status updated | Every 5 minutes |

**Prerequisite:** "Auto Create Invoice" must be enabled on the backend for automatic invoice creation.

### Conditional Sync: Odoo to Shopify (Reverse Sync)

These flows are triggered by user actions in Odoo and are controlled by TWO settings that must both be enabled.

| Odoo Action | Shopify Result | Backend Setting Required | Per-Order Toggle Required |
|---|---|---|---|
| Post an invoice | Order marked as paid (orderMarkAsPaid) | "Reverse Sync: Payment" ON | "Sync to Shopify" ON |
| Post a credit note | Refund created (refundCreate, amount only) | "Reverse Sync: Refund" ON | "Sync to Shopify" ON |
| Validate a delivery | Fulfillment created | None (always active) | "Sync to Shopify" ON |

### Control Settings

#### Backend-Level Flags (Settings > Shopify Backend > Sync Settings)

- **Reverse Sync: Payment** (default: OFF) — When enabled, posting an invoice for a Shopify order with "pending" or "authorized" status will mark the order as paid on Shopify.
- **Reverse Sync: Refund** (default: OFF) — When enabled, posting a credit note for a Shopify order will create a monetary refund on Shopify.

These are admin-level policy settings that apply to ALL orders for this backend.

#### Per-Order Toggle (Sale Order > Shopify tab)

- **Sync to Shopify** (default: ON) — Controls whether this specific order participates in Odoo-to-Shopify sync. Visible only on Shopify-channel orders.

#### Precedence Rules

The per-order toggle can only NARROW the backend policy, never override it:

| Backend Flag | Order Toggle | Result |
|---|---|---|
| OFF | OFF | No sync — backend disabled |
| OFF | ON | No sync — backend disabled (toggle cannot override) |
| ON | OFF | No sync — order opted out |
| ON | ON | Sync fires |

**Important:** The per-order toggle affects OUTBOUND sync only (Odoo to Shopify). Inbound sync (Shopify to Odoo) always runs regardless of the toggle setting. Shopify remains the source of truth for order status.

#### Sync Status Indicator

The Shopify tab on the sale order form shows a "Reverse Sync Status" field that displays:
- **Active (payments)** — Reverse payment sync is enabled for this order
- **Active (refunds)** — Reverse refund sync is enabled for this order
- **Active (payments, refunds)** — Both are enabled
- **Disabled for this order** — The per-order toggle is unchecked
- **Disabled on backend** — The backend flags are off (toggle is on but backend prevents sync)

### What Does NOT Sync

| Action in Odoo | Effect on Shopify | Reason |
|---|---|---|
| Register a payment on an invoice | Nothing | Only invoice posting triggers reverse sync, not payment registration |
| Cancel a posted invoice | Nothing (a warning activity is created on the order) | There is no "unpay" API on Shopify; auto-reversing could trigger real refunds |
| Create a partial payment | Nothing | Partial payment registration is not mapped to Shopify status |
| Post a credit note with specific line items | Monetary refund only (no line-item detail) | Shopify's refundCreate accepts an amount but the connector does not map Odoo invoice lines to Shopify line items |
| Create an invoice for a non-Shopify order | Nothing | Only orders with sales_channel = "shopify" are synced |
| Register a split payment (multiple gateways) | Single payment in Odoo | The connector registers one payment per order, not per Shopify transaction |

### Invoice Cancellation Warning

When you cancel a posted invoice that is linked to a Shopify order, the connector schedules a warning activity on the sale order. This activity:

- Explains that Shopify still shows the original payment status
- Advises you to create a credit note if a refund is needed (which the connector will sync to Shopify if reverse sync is enabled)
- Can be dismissed if the cancellation was an accounting correction only

The connector does NOT automatically reverse payments or create refunds on Shopify when an invoice is cancelled. This is a deliberate safety measure — automatic reversal could trigger real money movement on captured payments.

### Quick Reference: If You Do X, Expect Y

| You do this in Odoo | Shopify shows | Toggle ON | Toggle OFF |
|---|---|---|---|
| Post invoice for a pending Shopify order | Order marked as paid | Syncs (if backend flag on) | Skipped |
| Post invoice for an already-paid order | No change | No change | No change |
| Post credit note for a Shopify order | Refund created (amount only) | Syncs (if backend flag on) | Skipped |
| Cancel a posted Shopify invoice | Still shows paid | Activity warns you | Activity warns you |
| Validate delivery for a Shopify order | Fulfillment created | Syncs | Skipped |
| Register payment on invoice | No change | N/A | N/A |
| Edit order note or tags | Updated on Shopify | Updated | Updated (note/tag sync is separate) |
