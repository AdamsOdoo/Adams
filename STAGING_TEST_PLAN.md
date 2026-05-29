# Staging Test Plan — Adams Shopify Connector Pro v19.0.1.0.0

**Purpose:** Validate the connector against a real Shopify development store to close
risks that automated tests cannot cover.

**When to run:** After all automated tests pass (472/472), before publication to Odoo App Store.

**Estimated time:** 2-3 hours.

---

## Table of Contents

1. [Pre-Flight Setup](#1-pre-flight-setup)
2. [Token Encryption Verification](#2-token-encryption-verification)
3. [Test 1 — GraphQL Response Shape](#3-test-1--graphql-response-shape)
4. [Test 2 — Rate Limiter Calibration](#4-test-2--rate-limiter-calibration)
5. [Test 3 — Webhook HMAC with Real Payloads](#5-test-3--webhook-hmac-with-real-payloads)
6. [Test 4 — Multi-Currency Precision](#6-test-4--multi-currency-precision)
7. [Test 5 — Real Invoice Creation](#7-test-5--real-invoice-creation)
8. [Results Log Template](#8-results-log-template)

---

## 1. Pre-Flight Setup

### 1.1 Back Up the Odoo Database

1. Open a terminal on your Odoo server.
2. Run:
   ```
   pg_dump -Fc your_database_name > /tmp/odoo_backup_before_staging.dump
   ```
3. Confirm the file exists:
   ```
   ls -lh /tmp/odoo_backup_before_staging.dump
   ```
4. **PASS:** File exists and is larger than 1 MB.

> **Rollback note:** If anything goes wrong during staging, restore with:
> `pg_restore -c -d your_database_name /tmp/odoo_backup_before_staging.dump`

### 1.2 Create a Free Shopify Partner Development Store

1. Go to https://partners.shopify.com and sign in (or create a free account).
2. Click **Stores** in the left sidebar.
3. Click **Add store** → **Create development store**.
4. Choose **Create a store to test and build**.
5. Store name: `adams-staging-test` (or any name you like).
6. Select a development store region close to your Odoo server.
7. Click **Create development store**.
8. Wait for the store to finish provisioning (usually 30-60 seconds).
9. **PASS:** You can access `adams-staging-test.myshopify.com/admin`.

### 1.3 Generate an Admin API Access Token

1. In the Shopify admin, go to **Settings** → **Apps and sales channels**.
2. Click **Develop apps** (top-right corner).
3. Click **Allow custom app development** if prompted, then confirm.
4. Click **Create an app**. Name it `Adams Connector Staging`.
5. Click **Configure Admin API scopes**. Enable ALL of the following scopes:

   | Scope | Why |
   |-------|-----|
   | `read_products` | Product import |
   | `write_products` | Product export |
   | `read_orders` | Order import |
   | `write_orders` | Order status sync (mark as paid, tags) |
   | `read_customers` | Customer import |
   | `write_customers` | Customer export |
   | `read_inventory` | Stock level reads |
   | `write_inventory` | Stock level pushes |
   | `read_fulfillments` | Fulfillment status reads |
   | `write_fulfillments` | Fulfillment creation |
   | `read_locations` | Warehouse/location mapping |
   | `read_merchant_managed_fulfillment_orders` | Fulfillment order data |
   | `read_checkouts` | Abandoned cart import |
   | `write_checkouts` | Abandoned cart operations |
   | `read_gift_cards` | Gift card sync |
   | `read_discounts` | Discount code import |
   | `write_discounts` | Discount code export |
   | `read_metaobjects` | Metafield support |
   | `write_metaobjects` | Metafield support |

6. Click **Save**.
7. Click **Install app** → **Install**.
8. Under **API credentials**, click **Reveal token once**.
9. **Copy the token immediately** — it starts with `shpat_` and is shown only once.
10. **PASS:** You have a token that starts with `shpat_`.

### 1.4 Configure the Connector Backend in Odoo

1. In Odoo, go to **Shopify** → **Configuration** → **Backends**.
2. Click **New**.
3. Fill in:
   - **Name:** `Staging Test`
   - **Company:** Your main company
   - **Shop URL:** `adams-staging-test.myshopify.com` (your actual store domain)
   - **Access Token:** Paste the `shpat_...` token
   - **API Version:** `2026-01` (should be pre-filled)
   - **Warehouse:** Your main warehouse
4. Click **Test Connection**.
5. **PASS:** You see a green success banner with the shop name and Shopify plan info.
6. **FAIL:** If you see a red error — check the shop URL (must be `*.myshopify.com`),
   check the token (must start with `shpat_`), and verify all scopes from step 5 above.

### 1.5 Populate the Shopify Store with Test Data

You need enough data to exercise every code path. Create the following in the Shopify admin:

#### Products (create at least 5)

| # | Product | Variants | Images | Notes |
|---|---------|----------|--------|-------|
| 1 | "Simple T-Shirt" | 1 (no options) | 1 | Simplest case |
| 2 | "Multi-Size Hoodie" | S, M, L, XL (4 variants by Size) | 2 | Multi-variant |
| 3 | "Color+Size Sneaker" | 2 colors × 3 sizes (6 variants) | 3 | Two option axes |
| 4 | "Digital Download" | 1 | 0 (no image) | No image edge case |
| 5 | "Gift Card $25" | 1 | 1 | Gift card type |

- Set SKUs and barcodes on at least 2 variants.
- Set a compare-at price on product #2 (e.g., original $49.99, sale $39.99).
- Add a **metafield** to product #1: go to product page → scroll to Metafields → add
  a text metafield like `care_instructions = "Machine wash cold"`.
- Set product #4 status to **Draft** (not Active) — tests handling of non-active products.

#### Customers (create at least 3)

1. Go to **Customers** → **Add customer**.
2. Create:
   - Customer A: Full name, email, phone, full address (US).
   - Customer B: Email only (no phone, no address) — sparse data edge case.
   - Customer C: International address (e.g., Germany or Japan) — tests address formatting.

#### Orders (create at least 4)

Use the **Drafts** → **Create order** flow in Shopify admin to create test orders:

| # | Order | Line items | Discount | Tax | Shipping | Payment |
|---|-------|-----------|----------|-----|----------|---------|
| 1 | Standard | 2× Simple T-Shirt | None | Auto-calculated | Standard rate | Mark as paid |
| 2 | Discounted | 1× Multi-Size Hoodie (L) | 10% order discount | Auto | Free shipping | Mark as paid |
| 3 | Multi-line | 1× T-Shirt + 1× Sneaker (Red/10) + 1× Digital | $5 fixed discount on sneaker | Auto | Express rate | Mark as paid |
| 4 | Cancelled | 1× Hoodie (M) | None | Auto | Standard | Mark as paid, then cancel in Shopify |

**How to create a test order:**
1. Go to **Orders** → **Drafts** → **Create order**.
2. Add line items from your products.
3. Add a customer from step above.
4. Add shipping (use "Custom" if no rates configured — e.g., "Standard $5.99").
5. Add discount if applicable.
6. Click **Send invoice** or **Collect payment** → **Mark as paid**.
7. For Order #4: After marking as paid, click **More actions** → **Cancel order**.

**PASS:** Shopify admin shows 5 products, 3 customers, 4 orders. Proceed to tests.

---

## 2. Token Encryption Verification

**Goal:** Confirm that the encryption-at-rest feature (shipped in commit `09047ab`) works
correctly in a real environment.

### Step 2.1 — Verify Connection Works with Encryption Active

1. In Odoo, go to **Shopify** → **Configuration** → **Backends** → open your `Staging Test` backend.
2. Click **Test Connection**.
3. **PASS:** Green success banner appears. The connection works even though the token is stored encrypted.

### Step 2.2 — Verify Token is Encrypted in the Database

1. Open a terminal and run a direct SQL query:
   ```
   psql your_database_name -c "
     SELECT id, shop_url,
            _encrypted_access_token,
            LEFT(_encrypted_access_token, 30) AS token_preview
     FROM shopify_backend
     WHERE shop_url LIKE '%staging%';
   "
   ```
2. Look at the `_encrypted_access_token` column.
3. **PASS if ALL of the following are true:**
   - The value is NOT empty/NULL.
   - The value does NOT start with `shpat_` (that would mean it is stored in plaintext).
   - The value starts with `gAAAAA` (this is the Fernet token prefix — base64 of version byte 0x80).
   - The value is significantly longer than the original token (Fernet adds ~90 bytes of overhead).
4. **FAIL:** If the value starts with `shpat_`, encryption is not active. Check
   that the migration ran (`SELECT * FROM ir_module_module WHERE name='shopify_connector_pro'`
   and verify the version).

### Step 2.3 — Verify Encrypted Webhook Secret (if set)

1. If you have already registered webhooks (you will in Test 3), repeat the above query
   but check `_encrypted_webhook_secret`.
2. Same criteria: not null, not plaintext, starts with `gAAAAA`.

### Step 2.4 — Verify Sync Works End-to-End with Encrypted Token

1. In the backend form, click **Sync Products** (or wait for the cron).
2. **PASS:** Products appear in **Shopify** → **Products** list. The connector successfully
   decrypted the token, made a GraphQL call, and processed the response.

---

## 3. Test 1 — GraphQL Response Shape

**Goal:** Confirm that real Shopify GraphQL responses are parsed correctly, and no data is
silently dropped or malformed.

### Step 3.1 — Import Products

1. In the backend form, click **Sync Products** (manual sync button).
2. Wait for the sync to complete (watch the status bar or check **Shopify** → **Sync Log**).
3. Go to **Shopify** → **Products** → **Bindings** (or Product list).
4. Verify each product:

| Check | How to verify | PASS criteria |
|-------|--------------|---------------|
| All 5 products imported | Count rows in the product list | 5 products (or 4 if draft is excluded by filter) |
| Product #1 title | Open product, check Name field | Matches Shopify exactly |
| Product #1 description | Check Description field | HTML preserved (bold, lists, etc.) |
| Product #2 variants | Open product → Variants tab | 4 variants: S, M, L, XL |
| Product #2 compare-at price | Check variant prices | Both regular and compare-at prices present |
| Product #3 variant matrix | Open product → Variants tab | 6 variants (2 colors × 3 sizes) |
| Product #3 images | Check Images section | 3 images downloaded and visible |
| Product #4 (Digital) | Check if imported | Should import (possibly as draft), 0 images |
| SKUs preserved | Check variants for products #2, #3 | SKU field matches Shopify |
| Barcodes preserved | Check variants with barcodes | Barcode field matches Shopify |
| Vendor field | Check product #1 | Vendor matches Shopify value |
| Product type | Check product #1 | Product type matches |
| Tags | Check any product with tags | Tags imported as comma-separated |
| Product weight | Check product #2 or #3 | Weight matches Shopify variant weight (e.g. 0.5 kg) |
| Multi-option attributes | Check product #3 (Color+Size) | 2 attribute lines: Color and Size with correct values |
| Metafield (product #1) | Check for care_instructions metafield | Metafield value visible (if metafield sync enabled) |

**Fields most likely to break:**
- `descriptionHtml` — may contain characters that break XML parsing.
- `images.edges[].node.url` — URL format may vary (CDN domain changes).
- `variants.edges[].node.compareAtPrice` — **nullable field**. If null, should not set a compare-at price rather than setting 0.
- `options` — array of option names. Verify they create Odoo attributes correctly.

### Step 3.2 — Import Customers

1. Click **Sync Customers** in the backend.
2. Go to **Shopify** → **Customers** (or Contacts list filtered by Shopify).
3. Verify:

| Check | PASS criteria |
|-------|---------------|
| Customer A | Full name, email, phone, full address all present |
| Customer B | Email present, no errors from missing phone/address |
| Customer C | International address formatted correctly (country, zip, state) |
| Duplicate handling | Re-running sync does not create duplicate contacts |

**Fields most likely to break:**
- `phone` — nullable, may include country code prefix.
- `addresses` — nested edges. Empty array vs. null both possible.
- International address `province` / `provinceCode` — may be null for countries without states.

### Step 3.3 — Import Orders

1. Click **Import Orders** in the backend.
2. Go to **Sales** → **Orders** (filtered by Shopify backend).
3. Verify each order:

| Check | Order #1 | Order #2 | Order #3 | Order #4 |
|-------|----------|----------|----------|----------|
| Line items count | 1 line (qty 2) | 1 line | 3 lines | 1 line |
| Unit prices match Shopify | Yes | Yes | Yes | Yes |
| Discount applied | No discount line | 10% visible | $5 on sneaker line | — |
| Tax amount matches | Compare to Shopify order page | Same | Same | — |
| Shipping line present | $5.99 (or your amount) | $0 (free) | Express amount | — |
| Customer linked | Customer A or B | Same | Same | — |
| Shipping address | Full address present | Same | Same | — |
| Billing ≠ shipping | Create order with different billing address | Billing partner differs from shipping partner | — | — |
| Order status | Confirmed/Sale | Confirmed/Sale | Confirmed/Sale | Cancelled |
| Financial status | Paid | Paid | Paid | — |
| Order name | Matches Shopify (e.g., #1001) | #1002 | #1003 | #1004 |

**Fields most likely to break:**
- `discountAllocations` on line items — nested array, can be empty (`[]`) or null.
- `taxLines` — each line item can have 0..N tax lines. Amount is string, not float.
- `shippingLines` — `originalPriceSet` nullable if free shipping.
- `cancelledAt` — nullable string. Non-null means cancelled.
- `shippingAddress.phone` — often null even when customer has a phone.

### Step 3.4 — Check for Silent Errors

1. In your Odoo server terminal, check recent logs:
   ```
   grep -i "warning\|error" /var/log/odoo/odoo.log | grep -i shopify | tail -50
   ```
2. Also check **Shopify** → **Sync Log** in the Odoo UI for any error entries.
3. **PASS:** No unexpected warnings or errors related to field parsing, missing keys,
   or type conversion. Warnings about optional features (like metafields not enabled)
   are acceptable.
4. **FAIL:** Any `KeyError`, `TypeError`, `AttributeError`, or "field X not found" in logs.

---

## 4. Test 2 — Rate Limiter Calibration

**Goal:** Confirm the adaptive token bucket handles real Shopify throttling without 429 error
storms, excessive delays, or false circuit-breaker trips.

### Step 4.1 — Set Up Bulk Data

You need enough data to trigger real throttling. In the Shopify admin:

1. Go to **Products** → **Import** (or use the bulk product creation).
2. Create at least **200 products** total. The easiest way:
   - Export the 5 existing products as CSV.
   - Duplicate rows in the CSV, changing titles/handles/SKUs.
   - Import the CSV back into Shopify.
   - Alternatively, use a free Shopify app like "Product CSV Import" to generate test products.
3. Confirm: **Products** page shows 200+ products.

### Step 4.2 — Trigger Bulk Import

1. In Odoo, open the backend and click **Sync Products** (or use the "Full Sync" option if available).
2. **Immediately** open a terminal and start watching the Odoo log in real time:
   ```
   tail -f /var/log/odoo/odoo.log | grep -i "shopify\|rate\|throttl\|429\|bucket\|circuit"
   ```

### Step 4.3 — What to Watch For

Monitor the log output for 5-10 minutes. Look for these patterns:

| Log pattern | What it means | Expected behavior |
|------------|---------------|-------------------|
| `Rate limiter: waiting Xs` | Bucket depleted, sleeping | Should appear occasionally. Wait times should be 1-5 seconds, not 30+. |
| `Throttle status: available=X/Y` | Shopify returned remaining budget | Numbers should fluctuate but not stay at 0. |
| `429 Too Many Requests` | Hard rate limit hit | Should appear 0-2 times max. If frequent (5+), the limiter is too aggressive. |
| `Circuit breaker OPEN` | 5 consecutive failures triggered circuit breaker | Should NOT appear during normal throttling. If it does, the breaker threshold is too sensitive. |
| `Circuit breaker RECOVERED` | Breaker reset after 300s | Only expected if breaker opened. |
| `Retrying (attempt X/3)` | Retry after transient error | OK if occasional. Concerning if constant. |

### Step 4.4 — Measure Throughput

1. Note the time when you clicked **Sync Products**.
2. Note the time when the sync completes (check Sync Log for completion entry).
3. Calculate: `200 products / elapsed minutes = products per minute`.
4. **PASS criteria:**
   - **Throughput:** At least 10 products/minute (200 products in under 20 minutes).
   - **No 429 storms:** Fewer than 3 total `429` responses in logs.
   - **No circuit breaker trip:** Zero `Circuit breaker OPEN` entries.
   - **Reasonable wait times:** Individual waits under 10 seconds; total wait time under 60s.
   - **All products imported:** Final count in Odoo matches Shopify.
5. **FAIL:** If throughput is under 5 products/minute, or 429 count exceeds 5, or the
   circuit breaker opens, or the sync hangs for more than 2 minutes with no progress.

### Step 4.5 — Check Rate Limiter Metrics (Optional)

If the module exposes rate limiter stats in the UI or Sync Log, check:
- `total_requests` — should roughly equal product count / page size (200/50 = 4+ pages).
- `total_cost` — should be in the range of 40-100 (estimated 10-12 per page).
- `total_wait_time` — should be under 60 seconds for a 200-product sync.
- `throttle_count` — number of times the bucket was empty. A few is fine; dozens is a problem.

---

## 5. Test 3 — Webhook HMAC with Real Payloads

**Goal:** Confirm that webhooks registered with Shopify deliver real events that pass HMAC
verification and process end-to-end.

### Step 5.1 — Register Webhooks

1. In Odoo, open the backend form.
2. Look for a **Register Webhooks** button (or similar) and click it.
3. Check the Sync Log or chatter for confirmation that webhooks were registered.
4. **PASS:** Log shows successful webhook subscription creation for topics like
   `products/create`, `products/update`, `orders/create`, `orders/updated`, `orders/cancelled`.
5. If there is no button, webhooks may register automatically on first sync. Check the
   Shopify admin: **Settings** → **Notifications** → **Webhooks** (bottom of page) to see
   registered webhook URLs. They should point to:
   ```
   https://your-odoo-domain.com/shopify/webhook/<backend_id>
   ```

> **Important:** Your Odoo instance must be accessible from the internet for Shopify to
> deliver webhooks. If running locally, use a tunnel like `ngrok http 8069` and update the
> Odoo `web.base.url` system parameter to the ngrok URL.

### Step 5.2 — Fire a Product Update Event

1. In the Shopify admin, open product #1 ("Simple T-Shirt").
2. Change the title to "Simple T-Shirt (Updated)".
3. Click **Save**.
4. Wait 30-60 seconds.
5. In Odoo, check **Shopify** → **Webhook Log** (or Sync Log).
6. **PASS criteria:**
   - A webhook entry appears with topic `products/update`.
   - State is `done` (not `error` or `failed`).
   - The product name in Odoo updates to "Simple T-Shirt (Updated)".
7. **FAIL:** If state is `error` with an HMAC message, the webhook secret may be wrong
   or encoding differs between Shopify and the connector.

### Step 5.3 — Fire an Order Create Event

1. In the Shopify admin, create a new draft order:
   - Add any product, any customer.
   - Mark as paid.
2. Wait 30-60 seconds.
3. Check the Webhook Log in Odoo.
4. **PASS criteria:**
   - A webhook entry appears with topic `orders/create` or `orders/updated`.
   - State is `done`.
   - The new order appears in Odoo Sales Orders.

### Step 5.4 — Fire an Order Cancellation Event

1. In the Shopify admin, open the order you just created.
2. Click **More actions** → **Cancel order** → confirm.
3. Wait 30-60 seconds.
4. Check the Webhook Log in Odoo.
5. **PASS criteria:**
   - A webhook entry appears with topic `orders/cancelled`.
   - State is `done`.
   - The order in Odoo is marked as cancelled.

### Step 5.5 — Verify HMAC Specifically

1. In the terminal, check for HMAC-related log entries:
   ```
   grep -i "hmac\|signature\|verify" /var/log/odoo/odoo.log | grep -i shopify | tail -20
   ```
2. **PASS:** No HMAC verification failures for the events above.
3. **Known risk:** Real Shopify payloads may include Unicode characters, trailing whitespace,
   or different JSON serialization than synthetic tests. If HMAC fails:
   - Check if the raw body encoding is UTF-8.
   - Check if the webhook secret in Odoo matches the one in Shopify app settings.
   - Check if the HMAC is computed on the raw body bytes (not a re-serialized JSON string).

### Step 5.6 — Verify Deduplication

1. If any webhook fires twice (Shopify retries), check that Odoo does not process it twice.
2. The Webhook Log should show the duplicate with a note like "already processed" or
   state `skipped`.
3. **PASS:** No duplicate orders or duplicate product updates created.

---

## 6. Test 4 — Multi-Currency Precision

**Goal:** Verify that orders in a non-base currency import with correct amounts down to the cent.

### Step 6.1 — Enable Multi-Currency in Shopify

1. In the Shopify admin, go to **Settings** → **Markets**.
2. You should see your primary market. Click **Add market**.
3. Add a market for **European Union** (or any non-USD region).
4. Under the new market, click **Currencies** → add **EUR** (Euro).
5. Set a manual exchange rate or let Shopify auto-convert.
6. **PASS:** The Markets page shows two markets with different currencies.

### Step 6.2 — Enable Multi-Currency in Odoo

1. In Odoo, go to **Accounting** → **Configuration** → **Settings**.
2. Enable **Multi-Currency** if not already enabled.
3. Go to **Accounting** → **Configuration** → **Currencies**.
4. Find **EUR** and activate it (toggle the Active checkbox).
5. Set an exchange rate (or use the auto-update feature).
6. **PASS:** EUR currency is active in Odoo with a rate set.

### Step 6.3 — Configure Backend for Presentment Currency

1. Open the Shopify backend in Odoo.
2. Find the **Import Currency Mode** field (or similar setting).
3. Set it to **Presentment Currency** (this uses the customer-facing currency).
4. Save.

### Step 6.4 — Create a Multi-Currency Order in Shopify

1. In the Shopify admin, create a new draft order.
2. Add a product (e.g., "Simple T-Shirt" at $25.00 USD).
3. Add a customer with a European address (so Shopify applies EUR pricing).
4. If Shopify shows the order in EUR — good. If not, you can manually create the order
   through the Storefront with a European billing address to trigger presentment currency.
5. Add shipping ($5.00 / equivalent in EUR).
6. Ensure tax is calculated.
7. Mark as paid.
8. Note the **exact amounts** shown on the Shopify order page:
   - Subtotal in EUR: ___________
   - Tax in EUR: ___________
   - Shipping in EUR: ___________
   - Total in EUR: ___________

### Step 6.5 — Import and Verify in Odoo

1. Click **Import Orders** in the backend (or wait for the cron).
2. Open the newly imported order in Odoo.
3. Verify:

| Field | Shopify value (EUR) | Odoo value | Match? |
|-------|-------------------|------------|--------|
| Currency on order | EUR | Should be EUR | |
| Line item unit price | (from Shopify) | | |
| Line item subtotal | (from Shopify) | | |
| Tax amount | (from Shopify) | | |
| Shipping amount | (from Shopify) | | |
| Order total | (from Shopify) | | |

4. Check that a **Pricelist** was auto-created (e.g., "Shopify EUR") and assigned to the order.
5. **PASS criteria:**
   - Currency is EUR (not USD).
   - Every amount matches Shopify to the cent (0.01 tolerance for rounding).
   - Tax amount matches Shopify's tax calculation.
   - No "currency mismatch" warnings in logs.
6. **FAIL:** If any amount differs by more than 0.01, or if the order is in USD instead of EUR.

### Step 6.6 — Verify Company Currency Mode (Control Test)

1. Change the backend setting to **Company Currency** mode.
2. Import another order (create a new one in Shopify with EUR pricing).
3. **PASS:** The order imports in your company's base currency (USD), with amounts converted.
4. Change the setting back to your preferred mode.

---

## 7. Test 5 — Real Invoice Creation

**Goal:** Verify that importing a paid order creates a valid, postable invoice that reconciles
correctly with a real chart of accounts.

### Step 7.1 — Pre-Requisites in Odoo

1. Ensure your Odoo company has a **Chart of Accounts** installed:
   - Go to **Accounting** → **Configuration** → **Chart of Accounts**.
   - You should see accounts listed. If empty, install a chart (e.g., install the
     `l10n_us` module for US accounts, or `l10n_generic_coa` for a generic chart).
2. Ensure the backend has **Auto-Create Invoice** enabled:
   - Open the backend form.
   - Find the **Auto-Create Invoice** toggle and enable it.
   - Save.
3. Ensure products have an **Income Account**:
   - Go to **Accounting** → **Configuration** → **Settings**.
   - Under **Default Accounts**, check that **Default Income Account** is set.
   - Alternatively, open any Shopify-synced product category and verify
     **Income Account** is set under the Accounting tab.
4. Ensure a **Sales Journal** exists:
   - Go to **Accounting** → **Configuration** → **Journals**.
   - Look for a journal with type "Sales". If none exists, create one.
5. Ensure a **Bank Journal** exists (for payment registration):
   - Look for a journal with type "Bank". Create one if needed.

### Step 7.2 — Standard Paid Order → Invoice

1. Import Order #1 from Shopify (the standard 2× T-Shirt, marked as paid).
2. Open the sale order in Odoo.
3. Check if an invoice was auto-created:
   - Look at the **Invoices** smart button on the sale order.
   - Or go to **Accounting** → **Invoices** and filter by the order reference.
4. Open the invoice. Verify:

| Check | Expected |
|-------|----------|
| Invoice status | **Posted** (not draft) |
| Invoice lines match SO lines | Same products, quantities, unit prices |
| Tax lines present | Tax amount matches the sale order |
| Total matches | Invoice total = SO total = Shopify total |
| Journal | Sales journal |
| Payment status | **In Payment** or **Paid** (if auto-payment is enabled) |

5. If auto-payment is enabled, check that a payment entry exists:
   - Go to **Accounting** → **Payments** and find the payment linked to this invoice.
   - Verify amount matches invoice total.
6. **PASS:** Invoice is posted, amounts match, no accounting errors.
7. **FAIL:** Invoice stuck in draft, missing tax lines, or an error in the chatter/log.

### Step 7.3 — Tax-Exempt Order

1. In Shopify, create a new draft order.
2. Add a product. Under the customer section, check **Tax exempt** on the customer
   (or remove tax from the order manually).
3. Mark as paid.
4. Import into Odoo.
5. **PASS criteria:**
   - Invoice is created with **zero tax**.
   - No tax lines on the invoice.
   - Invoice posts without error.
   - Invoice total matches the tax-free Shopify total.

### Step 7.4 — Fully Discounted Line

1. In Shopify, create a new draft order.
2. Add a product priced at $25.00.
3. Add a 100% discount (or a $25.00 fixed discount) so the line total is $0.00.
4. Add a second product at normal price (so the order total > $0).
5. Mark as paid.
6. Import into Odoo.
7. **PASS criteria:**
   - The discounted line appears with effective price $0.00 (or as a 100% discount line).
   - The invoice posts without error.
   - The invoice total matches Shopify (only the non-discounted line amount + tax + shipping).
8. **FAIL:** If the $0 line causes a division-by-zero error, or the invoice cannot be posted.

### Step 7.5 — Multi-Currency Invoice (EUR)

1. Use the EUR order from Test 4 (or create a new one).
2. Ensure the backend is in **Presentment Currency** mode.
3. Import the order.
4. Open the auto-created invoice.
5. **PASS criteria:**
   - Invoice currency is **EUR**.
   - All amounts match the EUR values from Shopify.
   - Invoice posts without error.
   - The journal entry shows the EUR → USD conversion using the Odoo exchange rate.
   - The accounting is balanced (debits = credits).
6. To verify the journal entry:
   - Open the posted invoice → click **Journal Entry** (or **Journal Items**).
   - Check that the debit/credit amounts in company currency (USD) are correct.
   - Check that the EUR amounts are on the invoice lines.

### Step 7.6 — Verify No Accounting Errors in Logs

1. After all invoice tests, check for SQL-level errors:
   ```
   grep -i "psycopg2\|CheckViolation\|account_id.*null\|constraint" /var/log/odoo/odoo.log | tail -20
   ```
2. **PASS:** Zero `CheckViolation` or constraint errors.
3. **FAIL:** Any `account_move_line_check_accountable_required_fields` violation means
   a product or category is missing its income account. Fix the account setup and re-test.

---

## 8. Results Log Template

Copy this table and fill it in as you run each test. Save the completed version for your records.

```
================================================================
STAGING TEST RESULTS — Adams Shopify Connector Pro v19.0.1.0.0
Date: ____________________
Tester: __________________
Odoo version: 19.0
Shopify store: _________________________.myshopify.com
Odoo URL: _________________________
================================================================

PRE-FLIGHT
--------------------------------------------------------------------------
| # | Test                              | Pass/Fail | Notes              |
|---|-----------------------------------|-----------|--------------------|
| 0a| Database backed up                |           |                    |
| 0b| Shopify dev store created         |           |                    |
| 0c| API token generated (all scopes)  |           |                    |
| 0d| Backend configured + Test Conn.   |           |                    |
| 0e| Store populated with test data    |           |                    |
--------------------------------------------------------------------------

ENCRYPTION VERIFICATION
--------------------------------------------------------------------------
| # | Test                              | Pass/Fail | Notes              |
|---|-----------------------------------|-----------|--------------------|
| E1| Connection works with encryption  |           |                    |
| E2| Token encrypted in DB (gAAAAA...) |           |                    |
| E3| Webhook secret encrypted in DB    |           |                    |
| E4| Sync works end-to-end             |           |                    |
--------------------------------------------------------------------------

TEST 1: GRAPHQL RESPONSE SHAPE
--------------------------------------------------------------------------
| # | Test                              | Pass/Fail | Notes              |
|---|-----------------------------------|-----------|--------------------|
|1.1| All products imported             |           | Count: ___/5       |
|1.2| Variants correct (multi-variant)  |           |                    |
|1.3| Images downloaded                 |           |                    |
|1.4| Compare-at price preserved        |           |                    |
|1.5| SKUs and barcodes preserved       |           |                    |
|1.6| Nullable fields handled (no img)  |           |                    |
|1.7| All customers imported            |           | Count: ___/3       |
|1.8| Sparse customer (email only)      |           |                    |
|1.9| International address formatted   |           |                    |
|1.10| All orders imported              |           | Count: ___/4       |
|1.11| Discounts applied correctly      |           |                    |
|1.12| Tax amounts match Shopify        |           |                    |
|1.13| Shipping lines present           |           |                    |
|1.14| Cancelled order status correct   |           |                    |
|1.15| No silent errors in logs         |           |                    |
--------------------------------------------------------------------------

TEST 2: RATE LIMITER CALIBRATION
--------------------------------------------------------------------------
| # | Test                              | Pass/Fail | Notes              |
|---|-----------------------------------|-----------|--------------------|
|2.1| 200 products created in Shopify   |           |                    |
|2.2| Bulk import completed             |           | Time: ___ min      |
|2.3| Throughput >= 10 products/min     |           | Actual: ___/min    |
|2.4| 429 errors < 3                    |           | Count: ___         |
|2.5| No circuit breaker trip           |           |                    |
|2.6| Wait times reasonable (< 10s ea.) |           | Max wait: ___s     |
--------------------------------------------------------------------------

TEST 3: WEBHOOK HMAC
--------------------------------------------------------------------------
| # | Test                              | Pass/Fail | Notes              |
|---|-----------------------------------|-----------|--------------------|
|3.1| Webhooks registered successfully  |           |                    |
|3.2| Product update event received     |           |                    |
|3.3| Product update HMAC verified      |           |                    |
|3.4| Product updated in Odoo           |           |                    |
|3.5| Order create event received       |           |                    |
|3.6| Order create HMAC verified        |           |                    |
|3.7| Order created in Odoo             |           |                    |
|3.8| Order cancel event received       |           |                    |
|3.9| Order cancelled in Odoo           |           |                    |
|3.10| No duplicate processing          |           |                    |
--------------------------------------------------------------------------

TEST 4: MULTI-CURRENCY PRECISION
--------------------------------------------------------------------------
| # | Test                              | Pass/Fail | Notes              |
|---|-----------------------------------|-----------|--------------------|
|4.1| EUR market added in Shopify       |           |                    |
|4.2| EUR currency active in Odoo       |           |                    |
|4.3| Presentment mode configured       |           |                    |
|4.4| EUR order imported                |           |                    |
|4.5| Currency is EUR (not USD)         |           |                    |
|4.6| Subtotal matches to cent          |           | Shopify:___ Odoo:__|
|4.7| Tax matches to cent               |           | Shopify:___ Odoo:__|
|4.8| Shipping matches to cent          |           | Shopify:___ Odoo:__|
|4.9| Total matches to cent             |           | Shopify:___ Odoo:__|
|4.10| Auto-pricelist created           |           | Name: ___          |
|4.11| Company currency mode works      |           |                    |
--------------------------------------------------------------------------

TEST 5: REAL INVOICE CREATION
--------------------------------------------------------------------------
| # | Test                              | Pass/Fail | Notes              |
|---|-----------------------------------|-----------|--------------------|
|5.1| Chart of accounts installed       |           |                    |
|5.2| Auto-create invoice enabled       |           |                    |
|5.3| Standard order → invoice posted   |           |                    |
|5.4| Invoice amounts match SO + Shopify|           |                    |
|5.5| Payment registered (if enabled)   |           |                    |
|5.6| Tax-exempt → invoice, zero tax    |           |                    |
|5.7| 100% discount line → no errors    |           |                    |
|5.8| EUR invoice → correct currency    |           |                    |
|5.9| EUR journal entry balanced        |           |                    |
|5.10| No CheckViolation in logs        |           |                    |
--------------------------------------------------------------------------

OVERALL RESULT
--------------------------------------------------------------------------
| Total tests: 50  | Passed: ___  | Failed: ___  | Skipped: ___       |
--------------------------------------------------------------------------
| Overall: PASS / FAIL                                                  |
| Blocking issues:                                                      |
|                                                                       |
| Notes:                                                                |
|                                                                       |
--------------------------------------------------------------------------
| Ready for App Store publication?  YES / NO                            |
--------------------------------------------------------------------------
```

---

## What to Do After Staging

- **All PASS:** The connector is ready for publication. Proceed to Odoo App Store submission.
- **Any FAIL:** Document the failure in the results table, fix the code, re-run the
  automated test suite, and re-run only the failed staging tests.
- **Archive this document** and the completed results table in the repository for audit trail.
