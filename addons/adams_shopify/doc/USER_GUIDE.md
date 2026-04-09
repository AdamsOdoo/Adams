# Adams Shopify Connector — User Guide

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
11. [Financial Configuration](#financial-configuration)
12. [Promoter and Coupon System](#promoter-and-coupon-system)
13. [Webhooks](#webhooks)
14. [Multi-Store and Multi-Company](#multi-store-and-multi-company)
15. [B2B and Wholesale Isolation](#b2b-and-wholesale-isolation)
16. [Dashboard and Monitoring](#dashboard-and-monitoring)
17. [Scheduled Actions](#scheduled-actions)
18. [Troubleshooting](#troubleshooting)
19. [FAQ](#faq)

---

## Installation

### Prerequisites

- **Odoo 19.0** (Community or Enterprise edition)
- **Shopify store** on Basic plan or above
- **Shopify Custom App** with Admin API access token

### Install the Module

1. Place the `adams_shopify` folder in your Odoo addons path
2. Update the apps list: **Settings > General Settings > Developer Tools > Update Apps List**
3. Search for "Adams Shopify Connector" and click **Install**

The module will automatically install its dependencies: `adams_base`, `sale_management`, `stock`, `account`, and `mail`.

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

### Store Health Dashboard

Access via **Shopify > Dashboard** (kanban view of all stores):

Each store card shows:
- Connection status (Connected / Not Connected / Error)
- Synced counts: products, orders, customers, collections, refunds
- Error counts with badges
- Active promoter count
- Today's sync log count
- Last sync timestamp

### Sync Logs

Access via **Shopify > Logs > Sync Log**:

- View all sync operations with timestamps and duration
- Filter by entity type, operation (import/export), and date
- Graph view for visual trends
- Pivot table for analysis
- Each log entry shows: records processed, successes, errors, and skipped

### Error Investigation

1. Check error counts on the dashboard
2. Click the error badge to see affected bindings
3. Review the error message on each binding record
4. Fix the underlying issue
5. Use the **Bulk Retry Wizard** to re-process failed records

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
