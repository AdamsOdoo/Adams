# Step-by-Step User Guide

Complete walkthrough of every configuration step and every feature workflow in **Shopify Connector Pro**. This guide assumes zero prior knowledge and walks you through every click and field.

## Table of Contents

### Part A — First-Time Setup
1. [Step-by-Step: Install the Module](#step-1--install-the-module)
2. [Step-by-Step: Create Shopify Custom App & Get Access Token](#step-2--create-shopify-custom-app)
3. [Step-by-Step: Add Your First Shopify Store in Odoo](#step-3--add-your-first-shopify-store-in-odoo)
4. [Step-by-Step: Run the Onboarding Wizard](#step-4--run-the-onboarding-wizard)
5. [Step-by-Step: Configure Tax, Payment Gateway & Field Mappings](#step-5--configure-taxes-payment-gateways-and-field-mappings)
6. [Step-by-Step: Register Webhooks](#step-6--register-webhooks)

### Part B — Daily Workflows
7. [Export a Product Odoo → Shopify](#workflow-export-product-to-shopify)
8. [Import a Product Shopify → Odoo](#workflow-import-product-from-shopify)
9. [Import Orders](#workflow-import-orders)
10. [Handle a Refund](#workflow-handle-a-refund)
11. [Manage Inventory](#workflow-manage-inventory)
12. [Recover an Abandoned Cart](#workflow-recover-an-abandoned-cart)
13. [Manage a Promoter & Commission](#workflow-manage-a-promoter)
14. [Retry Failed Records](#workflow-retry-failed-records)
15. [Reconcile Shopify ↔ Odoo](#workflow-reconcile)
16. [Monitor Integration Health](#workflow-monitor-health)

### Part C — Advanced
16. [Multi-Store Configuration](#multi-store-configuration)
17. [Multi-Currency (Shopify Markets)](#multi-currency-shopify-markets)
18. [B2B Isolation](#b2b-isolation)
19. [Generate Demo Data for Testing](#generate-demo-data)

---

# PART A — FIRST-TIME SETUP

## Step 1 — Install the Module

1. **Log in to Odoo** as an administrator.
2. Navigate to **Apps** in the main menu.
3. Click the **Update Apps List** menu item (top-left under Apps).
4. In the search bar at the top, remove the default `Apps` filter tag.
5. Type `Shopify Connector Pro` and press Enter.
6. Find **Shopify Connector Pro** in the results.
7. Click the **Activate** (or Install) button on the module card.
8. Wait for installation to finish. Odoo will redirect you.
9. Confirm success: a new **Shopify** menu appears in the top menu bar.

**Post-install check:**
- Go to **Settings → Users & Companies → Users**.
- Open your admin user.
- Scroll to the **Other Rights** or **Shopify** access group.
- Verify access groups **Shopify / User** and **Shopify / Manager** are visible.
- Assign **Shopify / Manager** to users who will manage sync operations.

---

## Step 2 — Create Shopify Custom App

You need a Shopify Admin API access token. Shopify calls this a **Custom App**.

1. **Log in to your Shopify Admin** at `https://<your-store>.myshopify.com/admin`.
2. In the bottom-left of Shopify Admin, click **Settings**.
3. In the Settings sidebar, click **Apps and sales channels**.
4. At the top of the page, click **Develop apps** (button on the right).
5. If prompted, click **Allow custom app development** → **Allow custom app development** again in the confirmation dialog.
6. Click **Create an app**.
7. Enter:
   - **App name:** `Odoo Connector`
   - **App developer:** your admin email
8. Click **Create app**.
9. On the new app page, click the **Configuration** tab.
10. Under **Admin API integration**, click **Configure**.
11. In the **Admin API access scopes** list, check these scopes:
    - `read_products`, `write_products`
    - `read_product_listings`
    - `read_inventory`, `write_inventory`
    - `read_orders`, `write_orders`
    - `read_all_orders` (required to import historical orders)
    - `read_customers`, `write_customers`
    - `read_fulfillments`, `write_fulfillments`
    - `read_shipping`, `write_shipping`
    - `read_locations`
    - `read_price_rules`, `write_price_rules`
    - `read_discounts`, `write_discounts`
    - `read_gift_cards`, `write_gift_cards`
    - `read_draft_orders`, `write_draft_orders`
    - `read_checkouts`
    - `read_shopify_payments_payouts`
12. Click **Save** (top right).
13. Click the **API credentials** tab.
14. Under **Access tokens**, click **Install app**.
15. In the confirmation dialog, click **Install**.
16. Shopify now displays the **Admin API access token** (starts with `shpat_`). **Click Reveal token once** and **copy it immediately** — you can only see it once.
17. Keep this token somewhere safe. You will paste it into Odoo in Step 3.
18. Also note your **shop URL**: `<your-store>.myshopify.com`.

---

## Step 3 — Add Your First Shopify Store in Odoo

1. In Odoo, click the **Shopify** menu in the top bar.
2. Click **Configuration → Shopify Stores**.
3. Click the **New** button at the top-left.
4. Fill in the form:
   - **Name:** e.g. `My Store`
   - **Shop URL:** `<your-store>.myshopify.com` (no `https://`, no trailing slash)
   - **Access Token:** paste the `shpat_...` token from Step 2
   - **API Version:** leave default (`2026-01`)
   - **Company:** select your Odoo company
   - **Warehouse:** select the default warehouse for Shopify orders
   - **Webhook Secret:** leave blank for now — we'll set this in Step 6
5. Click the **Test Connection** button at the top.
6. If successful:
   - The status changes to **Connected** (green badge).
   - **Shopify Shop Name** and **Shopify Plan** fields are populated automatically.
7. Click **Save** (cloud icon at the top).

**If the test fails:**
- Double-check the shop URL ends with `.myshopify.com` (no `www`, no protocol).
- Re-verify the access token (it must start with `shpat_`).
- Check that your Custom App is still installed in Shopify admin.

---

## Step 4 — Run the Onboarding Wizard

The onboarding wizard prefills sensible defaults and guides you through key settings.

1. In Odoo: **Shopify → Configuration → Setup Wizard**.
2. Step 1 — **Store Selection**: Pick the store you created in Step 3. Click **Next**.
3. Step 2 — **Sync Settings**:
   - Check **Sync Products** if you want product sync.
   - **Product Direction:**
     - Choose **Bidirectional** (recommended for new stores).
     - Choose **Odoo → Shopify** if Odoo is your source of truth.
     - Choose **Shopify → Odoo** if your catalog already lives in Shopify.
   - Check **Sync Customers**.
   - Check **Import Orders**.
   - Check **Push Inventory**.
   - Click **Next**.
4. Step 3 — **Warehouse & Location**:
   - Select your default **Warehouse**.
   - Click **Import Locations from Shopify** button.
   - Once locations are imported, select the **Primary Shopify Location** from the dropdown.
   - Click **Next**.
5. Step 4 — **Payment Gateway Mapping**:
   - The wizard lists payment gateways from your Shopify store.
   - For each, pick a matching Odoo **Journal** (e.g., `Shopify Payments → Bank`).
   - Click **Next**.
6. Step 5 — **Field Mappings**:
   - Click **Initialize Default Mappings** — this creates sensible defaults for products and customers.
   - Click **Next**.
7. Step 6 — **Finish**: Review your settings and click **Finish**.

---

## Step 5 — Configure Taxes, Payment Gateways, and Field Mappings

### 5.1 Tax Mappings

Shopify sends tax line names (e.g. `VAT 20%`) that don't match Odoo tax records by default.

1. **Shopify → Configuration → Tax Mappings**.
2. Click **New**.
3. Fill in:
   - **Backend:** your store
   - **Shopify Tax Name:** e.g. `VAT 20%` (exact name as sent by Shopify)
   - **Shopify Tax Rate:** `20.0`
   - **Odoo Tax:** select the matching Odoo tax record
   - **Country Code:** e.g. `GB` (optional, use when you have country-specific taxes)
4. Click **Save**.
5. Repeat for every tax you want to map. Any unmapped tax falls back to the product's default tax in Odoo.

### 5.2 Payment Gateway Mappings

1. **Shopify → Configuration → Payment Gateways**.
2. You should see gateways auto-discovered during onboarding.
3. For each gateway, click to open it and verify:
   - **Journal:** correct Odoo bank/payment journal
   - **Fee Product:** product used for payment processing fees (optional)
4. Click **Save**.

### 5.3 Field Mappings

Field mappings let you control which Odoo fields map to which Shopify fields.

1. Open your Shopify store in **Shopify → Configuration → Shopify Stores**.
2. Click the **Field Mappings** tab.
3. You'll see default mappings for products and customers.
4. To add a custom mapping, click **Add a line**:
   - **Entity:** Product / Customer / Order
   - **Odoo Field:** e.g. `x_studio_custom_field`
   - **Shopify Field:** e.g. `tags` or `metafields.custom.my_field`
   - **Direction:** Export / Import / Both
5. Click **Save** on the form.

---

## Step 6 — Register Webhooks

Webhooks deliver real-time events from Shopify (orders created, inventory changes, etc.).

### 6.1 Generate a Webhook Secret

1. Open your Shopify store form in Odoo.
2. In the **Webhook Secret** field, enter a long random string (32+ characters). You can generate one with:
   ```
   python -c "import secrets; print(secrets.token_hex(32))"
   ```
3. Click **Save**.

### 6.2 Check Your Public URL

Webhooks require an HTTPS URL accessible from the public internet.

1. Navigate to **Settings → Technical → System Parameters** (developer mode required).
2. Find the parameter `web.base.url`. It must be your **public HTTPS URL** (e.g. `https://mycompany.odoo.com`).
3. If it's wrong, edit it to match your public URL.

> **Important:** Also set `web.base.url.freeze = True` to prevent Odoo from overwriting the URL when an admin logs in.

### 6.3 Register Webhooks

1. Open your Shopify store form.
2. Click the **Webhooks** tab.
3. Click the **Register Webhooks** button.
4. A confirmation dialog reports how many webhooks were registered (e.g. "11 of 11 webhooks registered successfully").
5. Click **Check Webhook Status** to verify all topics are subscribed.

**Topics registered:**
`PRODUCTS_CREATE`, `PRODUCTS_UPDATE`, `PRODUCTS_DELETE`, `ORDERS_CREATE`, `ORDERS_UPDATED`, `ORDERS_CANCELLED`, `CUSTOMERS_CREATE`, `CUSTOMERS_UPDATE`, `INVENTORY_LEVELS_UPDATE`, `FULFILLMENTS_CREATE`, `APP_UNINSTALLED`.

### 6.4 Test the Webhook Endpoint

1. In Shopify admin, trigger a test event (e.g. edit a product and save).
2. In Odoo: **Shopify → Logs → Webhook Log**.
3. A new entry should appear within seconds.
4. Click it to inspect the payload and verify the HMAC signature passed.

---

# PART B — DAILY WORKFLOWS

## Workflow: Export Product to Shopify

### Option A — Automatic (recommended)

1. Open an Odoo product: **Sales → Products → Products**.
2. Edit any field (name, price, description).
3. Click **Save**.
4. If **Auto-export Product on Change** is enabled on the backend, a binding is automatically marked pending.
5. The next product sync cron (every 15 minutes) will push the change to Shopify.

### Option B — Manual

1. Open an Odoo product.
2. Click the **Shopify** tab on the product form.
3. Click **Export to Shopify** button.
4. A confirmation appears when done.
5. Click the **Open in Shopify** button to verify in Shopify admin.

### Option C — Bulk Export

1. **Shopify → Operations → Bulk Export**.
2. Select:
   - **Backend:** your store
   - **Entity:** Products
   - **Filter:** All active / Specific categories / Specific products
3. Click **Start Export**.
4. A sync log is created; monitor progress in **Shopify → Logs → Sync Log**.

---

## Workflow: Import Product from Shopify

### Full catalog import (one-time)

1. **Shopify → Operations → Import Data**.
2. Select:
   - **Backend:** your store
   - **Entity:** Products
   - **Import Mode:** Full
3. Click **Start Import**.
4. A background **Import Job** is created. Monitor under **Shopify → Operations → Import Jobs**.
5. When complete, inspect imported products under **Sales → Products → Products** (they will be tagged with Shopify tags).

### Delta import (daily incremental)

- Delta imports run automatically every 15 minutes when **Sync Products** is enabled.
- To trigger manually: **Shopify → Operations → Sync Now**, select **Products**, click **Sync**.

---

## Workflow: Import Orders

1. Orders are imported automatically every 5 minutes (cron) if **Import Orders** is enabled.
2. To check status: **Shopify → Sync Status → Orders**.
3. You'll see a list of all order bindings with their financial/fulfillment status.
4. Click an order binding to open it:
   - **Shopify ID:** order GID
   - **Financial Status:** paid / pending / refunded etc.
   - **Odoo Order:** link to the created sale.order
   - Click **View Shopify Order** to open in Shopify admin.

### Manual import of a single order

1. **Shopify → Operations → Import Data**.
2. **Entity:** Orders
3. **Import Mode:** Single
4. Paste the Shopify Order GID (e.g. `gid://shopify/Order/4529...`).
5. Click **Start Import**.

### When a new order is imported:

- A `sale.order` is created with `sales_channel = 'shopify'`.
- The customer is resolved (by email or by existing binding).
- All line items are created, matched by Shopify variant ID or SKU.
- Taxes are applied via tax mappings (falling back to product defaults).
- If **Auto-create Invoice** is on and the order is paid, an invoice is created and posted.
- If **Auto-create Invoice** is on and the order is paid, the stock picking is created.

---

## Workflow: Handle a Refund

### Refund initiated in Shopify

1. Issue a refund in Shopify admin as usual.
2. The refund import cron runs every 30 minutes.
3. When imported: **Shopify → Sync Status → Refunds**.
4. Click the refund to see:
   - Linked order binding
   - Refund amount
   - Linked Odoo credit note (account.move)
5. The credit note is created in `draft` state — review and post it manually.

### Refund initiated in Odoo

1. Open the original order: **Sales → Orders → Quotations**.
2. Click **Invoices → Create Credit Note**.
3. Select **Full refund** or **Partial refund**.
4. Post the credit note.
5. If **Reverse Sync: Refund** is enabled on the backend, a matching refund is created on Shopify.

---

## Workflow: Manage Inventory

### Push Odoo inventory → Shopify

1. Inventory push runs every 10 minutes (cron).
2. Inventory is pushed for each `shopify.variant.binding` whose `last_pushed_qty` differs from the current quantity.
3. Only variants that are bound to a Shopify product are pushed.

### Manually push inventory now

1. Open your Shopify store form.
2. Click **Push Inventory Now** button.

### Change the quantity field used

1. Open your Shopify store form.
2. **Sync** tab → **Quantity Type**.
3. Choose between:
   - **Free Quantity** (on hand − reserved) — **recommended** (prevents overselling).
   - **On Hand Quantity** (physical count).

---

## Workflow: Recover an Abandoned Cart

### Enable abandoned cart sync

1. Open your Shopify store form.
2. **Sync** tab → **Abandoned Carts** group.
3. Check **Sync Abandoned Carts**.
4. Optionally check **Auto-create Quotations** to automatically create a draft quotation for each abandoned cart.
5. Click **Save**.

### View abandoned carts

1. **Shopify → Sync Status → Abandoned Carts**.
2. The default filter shows **Not Recovered**.
3. Click a cart to see:
   - Customer email and name
   - Total price and line items
   - Recovery URL (Shopify's native recovery link)

### Create a quotation from an abandoned cart

1. Open the abandoned cart.
2. Click **Create Quotation** button at the top.
3. Odoo:
   - Resolves or creates the customer.
   - Creates a draft `sale.order` with all cart line items.
   - Links the quotation to the abandoned cart.
4. You can now email the quotation from Odoo, or use the Shopify recovery URL.

### Mark as recovered

- **Automatic:** When an order from the same customer is imported after the cart was abandoned, the system auto-marks it as recovered.
- **Manual:** Click **Mark Recovered** on the cart form.

---

## Workflow: Manage a Promoter

### Create a promoter

1. **Shopify → Promoters → Promoters**.
2. Click **New**.
3. Fill in:
   - **Name:** e.g. `Jane Influencer`
   - **Partner:** link to existing res.partner (or create a new one)
   - **Commission Type:** Percentage or Fixed
   - **Commission Rate:** e.g. `10.0` for 10%
4. Click **Save**.

### Create a discount code for the promoter

1. Still on the promoter form, click **Create Discount Code**.
2. Fill in:
   - **Code:** e.g. `JANE10`
   - **Discount Type:** Percentage / Fixed amount
   - **Discount Value:** e.g. `10` for 10% off
   - **Usage Limit:** (optional)
3. Click **Save**. The code is exported to Shopify automatically.

### Track commissions

1. **Shopify → Promoters → Discount Usage**.
2. Each row shows:
   - Discount code used
   - Order bound to it
   - Order total
   - **Commission Amount** auto-calculated from the promoter's rate
3. Filter by date or promoter to compute total commission owed.

---

## Workflow: Retry Failed Records

If a sync fails (network error, Shopify validation error), the binding is marked `error` with the error message.

### Retry one record

1. Open the failed binding (e.g. **Shopify → Sync Status → Products**, filter by **Error**).
2. Click the **Retry Sync** button on the form.
3. The binding is reset to `pending` and will retry on the next cron run.

### Bulk retry

1. **Shopify → Operations → Retry Failed Records**.
2. Select:
   - **Backend:** your store
   - **Entity:** (optional — leave blank for all)
   - **Only records with < 5 retries:** checked (recommended)
3. Click **Reset to Pending**.
4. A confirmation shows how many records were reset.

---

## Workflow: Reconcile

The reconciliation cron runs every 6 hours and compares Odoo and Shopify status.

### Manual reconciliation

1. **Shopify → Logs → Sync Analytics** (or open your store form).
2. Click **Run Reconciliation Now**.
3. Mismatches are listed with:
   - Binding ID
   - Odoo status vs Shopify status
   - Suggested action
4. Click **Auto-fix** to resolve simple mismatches.

---

## Workflow: Monitor Integration Health

The **Health Dashboard** tab on each store form gives you a complete picture of your integration's status without needing to navigate to multiple screens.

### Daily Health Check (2 minutes)

1. Go to **Shopify > Dashboard** (kanban view).
2. Scan your store cards:
   - Green badge = healthy.
   - Orange badge = webhook queue or inventory errors.
   - Red badge = payment mismatches or permanent errors needing attention.
3. If everything is green, you're done.

### Investigating a Warning

1. Click on the store card to open the backend form.
2. Click the **Health Dashboard** tab.
3. Read the **Overall Health Banner** — green (≥ 90 %), yellow (70–89 %), or red (< 70 %).

#### If you see error bindings

1. Scroll to **Section 4 — Sync Counts**. Note which entity has errors (e.g. Products: 3 errors).
2. Click **View Error Details** button (Section 7).
3. Review each error binding. The **Sync Error** field explains what went wrong:
   - `PRODUCT_SET_MUTATION userErrors: Title can't be blank` → Product has no name. Fix the product in Odoo, then retry.
   - `HTTP 429` → Rate limit hit. Will auto-resolve on next cron run.
   - `GraphQL errors: Access denied` → Scope missing on Shopify Custom App. Add the scope and click **Test Connection** to re-verify.
4. Once you've fixed the root causes, click **Retry All Errors** to re-queue all failed bindings at once. They will be processed on the next cron run.

#### If you see payment mismatches

A payment mismatch means an order is marked **paid** on Shopify but has no corresponding **posted invoice** in Odoo.

1. In Section 5, click **View Payment Mismatches**.
2. You'll see a filtered list of order bindings.
3. For each mismatch:
   - Open the binding, then click through to the Odoo sale order.
   - Check: is **Auto-create Invoice** enabled on the backend? If not, enable it and re-import the order.
   - If the setting is correct but the invoice is missing, manually create and post the invoice from the sale order.
4. After fixing, click **Run Reconciliation** to re-check and clear resolved mismatches.

#### If you see fulfillment mismatches

A fulfillment mismatch means an order is marked **fulfilled** on Shopify but the Odoo delivery is still pending.

1. In Section 5, click **View Fulfillment Mismatches**.
2. For each mismatch:
   - Open the binding and click through to the sale order.
   - Check the delivery order (stock.picking). Validate it if the goods were actually shipped.
   - If the fulfillment came from a 3PL or Shopify dropshipper and **Inbound Fulfillment Mode** is set to "Create Activity", check the scheduled activities on the order.
3. Click **Run Reconciliation** after fixing to confirm the mismatches are resolved.

#### If you see permanent errors

Permanent errors are bindings that have been retried 5 times and still fail. They require manual intervention.

1. In Section 5, note the **Permanent Errors** count.
2. Click **View Error Details** and filter by `sync_status = permanent_error`.
3. For each record, read the error and take corrective action (fix data, fix config).
4. Click **Retry Sync** on each binding to reset it to `pending`.

### Webhook Queue Health

If **Webhook Pending** count in Section 6 is growing:

1. Check the cron: **Settings > Technical > Automation > Scheduled Actions**, find "Process Shopify Webhooks" and verify it is running (last execution time, active status).
2. If the cron is stuck, check `/var/log/odoo/odoo.log` for errors.
3. If **Dead Letter** count is > 0, go to **Shopify > Logs > Webhook Log**, filter by "Dead Letter", review each error and click **Retry** after fixing the cause.

### Per-Entity Sync Times (Section 3)

Use the per-entity sync grid to detect stalled crons:

- If "Last Order Sync" is > 30 minutes ago but your order cron runs every 5 minutes → the cron may be failing silently. Check the Odoo scheduled action log.
- If "Last Inventory Sync" is stale → check the delta queue and inventory cron.

Expected freshness by entity:

| Entity | Expected freshness |
|--------|-------------------|
| Orders | < 10 min |
| Inventory | < 15 min |
| Products | < 20 min |
| Customers | < 20 min |
| Fulfillments | < 30 min |
| Collections | < 70 min |

### Automated External Monitoring

For production environments, set up an HTTP monitor on:

```
GET https://<your-odoo>/shopify/health/<backend_id>
```

Alert when:
- HTTP response is not 200
- `sync_health_pct` drops below 80
- `webhook_dead_letter_count` is > 0
- `data_integrity.payment_mismatches` is > 0

---

# PART C — ADVANCED

## Multi-Store Configuration

1. Create multiple `shopify.backend` records — one per Shopify store.
2. Each backend can have its own company (for multi-company setups).
3. Assign different warehouses to different backends.
4. Each binding (product/customer/order) is scoped to a single backend.
5. The same Odoo product can be bound to multiple Shopify stores (one binding per store).

---

## Multi-Currency (Shopify Markets)

If you use Shopify Markets to sell in multiple currencies:

1. Open your Shopify store form.
2. **Sync** tab → **Order Currency Mode**.
3. Choose **Use Customer Currency (Shopify Markets)**.
4. Click **Save**.
5. Now orders are imported using the currency the customer actually paid in (EUR, GBP, etc.), with prices and totals from `presentmentMoney`.
6. Odoo will create a matching pricelist for each new currency it encounters.

---

## B2B Isolation

If you have a B2B / Wholesale channel and don't want those orders to sync to Shopify:

1. Open the sale order.
2. Set **Sales Channel** to `b2b` (or any value other than `shopify`).
3. The connector filters out non-Shopify orders from auto-export.
4. Invoices from B2B orders are not reverse-synced to Shopify.

---

## Generate Demo Data

For development/staging environments only:

1. Enable developer mode: **Settings → Developer Tools → Activate developer mode**.
2. **Shopify → Operations → Generate Demo Data** (visible only to administrators).
3. Configure:
   - **Backend:** your store
   - **Products:** 10
   - **Customers:** 15
   - **Orders:** 20
   - **Abandoned Carts:** 5
   - **Collections:** 6
   - **Promoters:** 4
4. Click **Generate Demo Data**.
5. The wizard creates fake bindings with random states (some synced, some errored) to test the dashboard and workflows.

> **Warning:** Never run this in production — it creates real records in your database.

---

## Getting Help

- **Module logs:** `/var/log/odoo/odoo.log` — filter by `shopify_connector_pro` (technical module name).
- **Sync log:** **Shopify → Logs → Sync Log** — every batch operation is logged here.
- **Webhook log:** **Shopify → Logs → Webhook Log** — every incoming webhook is logged with its payload.
- **Import jobs:** **Shopify → Operations → Import Jobs** — background jobs with progress.
- **Shopify API dashboard:** In your Shopify admin → Settings → Apps → your custom app → API request logs.
