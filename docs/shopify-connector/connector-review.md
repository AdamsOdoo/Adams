# Shopify connector review (Qamah Solutions)

Date: 2026-10-05. Scope: `addons/shopify/base_marketplace` (19.0.1.1.3) and `addons/shopify/shopify` (1.2.10, i.e. 19.0.1.2.10), the uploaded third-party connector, now rebranded to Qamah Solutions.

How this was checked: the code was read file by file, and both modules were installed on a fresh local Odoo 19 Community database with no errors. Nothing was run against a live Shopify store. Runtime behaviour against Shopify is therefore **not verified**. Items marked *inference* are readings of the code that still need a live test.

## 1. Why there are two modules

The original vendor sells about eight marketplace connectors: Shopify, WooCommerce, Bol, BigCommerce, Etsy, eBay, Mirakl and PrestaShop. They put everything those connectors share into one framework, **Base Marketplace**. Each connector is a thin(ner) module on top of it.

| `base_marketplace`: generic, used by every connector | `shopify`: Shopify only |
| --- | --- |
| The `mk.instance` model (one record per store) and its settings tabs: warehouse, pricelist, product matching, stock, orders, taxes, customers | Shopify credentials (token, password or OAuth), API client and GraphQL queries (API version `2026-07`) |
| Listings (`mk.listing`, `mk.listing.item`, `mk.listing.image`) linking Odoo products to marketplace products | Product, variant, image, collection, metafield, metaobject, market, catalog and sales-channel sync |
| Queue engine (`mk.queue.job`), with a cron every 15 min, 3 retries and activities on failure | Order import (financial and fulfilment status, gift cards, tips, duties, fraud) |
| Logs (`mk.log`) and the dashboard, onboarding wizard and scope check | Fulfilment and tracking export, cancellations, refunds, returns, payouts |
| Order workflow (`order.workflow.config.ts`): confirm, invoice, validate, register payment | Webhooks, Shopify locations, payment gateways, financial-workflow mapping |
| Tax auto-creation, product matching by SKU/barcode, Go-Live guard for neutralised (staging) databases | Shopify crons (created per instance) |
| Security groups: Marketplace User / Marketplace Manager | — |

**How they connect**
- `base_marketplace` declares an empty `marketplace` selection field.
- `shopify` adds the value `shopify` to it.
- The base code then calls methods named `shopify_<hook>` by name. Examples are `shopify_test_connection`, `shopify_order_queue_process` and `shopify_import_listings`. About 100 such hooks are implemented.

**What this means for you**
- `shopify` cannot run without `base_marketplace`. It is installed automatically as a dependency.
- Merging the two into one module is possible, but it would gain nothing and would make it harder to take vendor updates.
- If you later add WooCommerce or another channel, it would reuse `base_marketplace`.
- **Recommendation:** keep the two modules.

## 2. Features

### Catalog (products, prices, stock)

**Products, variants and images**
- Directions: Shopify→Odoo and Odoo→Shopify.
- **Import:**
  - Manual, by date range or by Shopify IDs. Date-range imports go through the queue.
  - Also by webhook (`products/create`, `products/update`, `products/delete`).
  - Creates templates, attributes and variants, along with weight, HS code, country of origin, tags, product type and taxonomy category.
- **Export and update:** with GraphQL `productSet`. More than 3 products go through Shopify bulk operations.
- **Matching:** by Shopify ID, then by SKU, barcode, or SKU-then-barcode (instance setting "Sync Product With").

**Prices**
- **Odoo→Shopify:**
  - The price is taken from the instance pricelist.
  - It is sent by a manual export, a daily cron, or in real time when a sale price or pricelist item is written.
- **Shopify→Odoo:** prices are imported into the instance pricelist, not onto the product.

**Inventory**
- **Odoo→Shopify:**
  - Uses `inventorySetQuantities` per Shopify location.
  - The quantity can be a fixed number or a percentage of stock.
  - It is sent every 30 min by cron, or in real time on stock moves (option).
  - Phantom kits are supported.
- **Shopify→Odoo:**
  - Daily cron or manual.
  - Writes "available" into one Odoo location per Shopify location, as an inventory adjustment.

**Collections**
- Import, export and update, including smart-collection conditions and hand-picked items.
- Publish and unpublish to sales channels.

**Markets and B2B catalogs**
- Import markets, catalogs, fixed prices, quantity rules and volume price breaks.
- Update them back to Shopify.
- They cannot be **created** from Odoo.

**Metafields and metaobjects**
- Map Shopify metafields (23 types) to Odoo fields.
- Import and export them.
- Create and update metaobject entries.

**Sales channels:** imported from Shopify. You can publish or unpublish each product.

### Orders, customers and finance

**Order import**
- Runs on a cron every 15 min, by `orders/create` and `orders/updated` webhooks, or manually by date or ID.
- Filters: fulfilment status (Unshipped / Any / …) and an "import after" date.
- Lines covered:
  - discounts per line
  - shipping (matched to an Odoo carrier)
  - gift cards, tips and duties (as products)
  - taxes (auto-created as "title rate Included/Excluded")
  - refunded quantities
- Uses the shop currency or the customer's currency (option).
- Duplicate protection: a database constraint on (Shopify ID, store).

**Automatic order workflow**
- One rule for each pair of payment gateway (e.g. `shopify_payments`, `manual`, COD) and financial status (paid, pending, …).
- The rule chooses whether to confirm the order, create and validate the invoice, register the payment (journal and method) and apply a payment term.
- Picking policy and invoice date are also set per workflow.

**Customers**
- Created from orders, with invoice and delivery addresses and an optional company contact.
- A manual import and the `customers/create` webhook also exist.
- A default customer is used for POS orders that have none.

**Fulfilment**
- **Odoo→Shopify:** when a delivery is validated, a Shopify fulfilment is created with carrier and tracking number, optionally notifying the customer. It runs every 25 min by cron, or manually.
- **Shopify→Odoo:** orders already fulfilled in Shopify get their Odoo pickings validated.
- Store pickup: ready for pickup and picked up.

**Cancellation**
- **Odoo→Shopify:** a wizard with reason, restock and refund.
- **Shopify→Odoo:** orders cancelled in Shopify are cancelled in Odoo.

**Refunds**
- **Odoo→Shopify:** from a credit note, through Register Payment with "Refund in Shopify", or through the refund wizard.
- **Shopify→Odoo:** refunds made in Shopify become credit notes.

**Returns**
- Imported from Shopify by cron every 30 min and by six `returns/*` webhooks.
- Can be approved, declined, processed, closed or cancelled from Odoo.
- Each return creates a return picking and a credit note.

**Payouts (Shopify Payments)**
- Imported daily into Odoo as payouts and a bank statement, with per-transaction-type accounts.
- Auto-reconciliation needs Odoo Enterprise Accounting.

**Fraud analysis:** risk level and recommendations are stored on the order, and an activity is created for risky orders.

**Mark as paid:** optionally marks the Shopify order as paid when the Odoo order is paid.

**Dashboard and reporting**
- A Marketplaces overview: one card per store, with sales graph, counts and failed queues.
- An analytics dashboard: top products and customers, countries, categories.
- The Sales report gains store and marketplace filters.

**Staging safety:** on a neutralised database (Odoo.sh staging or duplicate), API calls and webhooks are blocked until **Go Live** is pressed. Do not press it on staging unless the staging database should really talk to the live store.

### Scheduled jobs

| Job | Interval | Default |
| --- | --- | --- |
| Marketplace: Process Queue Job (global) | 15 min | active |
| Shopify: Process Collection Job (global) | 15 min | active |
| Import Orders | 15 min | inactive (per store) |
| Export Order Status / Tracking | 25 min | inactive |
| Export Inventory | 30 min | inactive |
| Import Inventory | 1 day | inactive |
| Export Price | 1 day | inactive |
| Import Payouts | 1 day | inactive |
| Import Returns | 30 min | inactive |
| Process Pending Cancelled Returns | 25 min | inactive |
| Bulk Queue Status / Bulk Export Result | 15 min | inactive (**enable these if you export many products**) |

## 3. Step-by-step configuration

### A. In Shopify

1. **Plan.** Customer names, addresses and emails are protected customer data. Check that the plan allows API access to them. The vendor states Grow or higher; this is a vendor claim to confirm with Shopify.
2. **Create the app.**
   - Shopify no longer lets you create new custom apps from the store admin. New apps are created in the **Shopify Dev Dashboard** (`dev.shopify.com/dashboard`). This is an inference to confirm with Shopify's current docs. If the store already has a legacy custom app, its Admin API access token still works.
   - **Option 1, existing legacy custom app:** Shopify admin › Settings › Apps and sales channels › Develop apps. Open the app, grant the scopes listed below, install it, and copy the **Admin API access token**. It is shown only once.
   - **Option 2, Dev Dashboard app (OAuth):**
     - Create an app.
     - Set its **Redirect URL** to the one shown on the Odoo instance form: `https://<your-odoo>/external/oauth/callback`.
     - Grant the scopes below.
     - Copy the **Client ID** and **Client secret**.
3. **Grant these Admin API scopes.** The connector checks them on Confirm and lists any that are missing:
   - Customers, discounts and orders: `write_customers`, `write_discounts`, `write_gift_cards`, `write_orders`, `write_price_rules`
   - Products and publishing: `write_products`, `write_product_listings`, `write_publications`, `write_metaobject_definitions`, `write_metaobjects`, `write_markets`
   - Inventory, locations and shipping: `write_inventory`, `write_locations`, `write_shipping`
   - Fulfilment: `write_fulfillments`, `write_assigned_fulfillment_orders`, `write_merchant_managed_fulfillment_orders`, `write_third_party_fulfillment_orders`, `write_custom_fulfillment_services`
   - Returns: `write_returns`
   - Shopify Payments: `read_shopify_payments_payouts`, `read_shopify_payments_accounts`
   - Also add `read_all_orders` if you need orders older than 60 days. It is not in the connector's list, and without it Shopify returns only recent orders (inference to confirm).
4. **Note your store details.** The store URL must be `https://<store>.myshopify.com`, not your custom domain. Also note your locations, payment gateways and shipping methods; you will map them in Odoo.

### B. In Odoo

1. **Install.**
   - Apps › *Odoo Shopify Connector*. Base Marketplace installs with it.
   - The Python packages are already listed in the repository `requirements.txt` for Odoo.sh.
   - Give users **Marketplace User** or **Marketplace Manager** (Settings › Users).
2. **Create the store.** Marketplaces › Overview › Setup Wizard, or Marketplaces › Configuration › Instance › New, Marketplace = Shopify.
   - **Credentials:** Shop URL, then either paste the access token (keep "I have API Access Token" ticked), or enter Client ID and Secret and press **Generate Access Token**. The wizard supports only the token; OAuth is done on the form.
   - **Configuration:** company, warehouse, country, language, log level, queue batch size.
   - **Products:**
     - Sync Product With: SKU / Barcode / Both. Make sure SKUs or barcodes are unique and identical in Odoo and Shopify.
     - Pricelist.
     - Create Odoo Products?
     - Sync Images?
     - Export Sale Price.
     - Real-time Price Sync.
   - **Stock:** Stock Based On (On hand / Forecast…), Validate Inventory Adjustment, Real-time Inventory Sync.
   - **Orders:**
     - Order prefix or Shopify numbering, sales team, salesperson.
     - Import Orders After (your go-live date).
     - Discount and shipping products.
     - Tax system: Odoo taxes, Shopify taxes, or Shopify taxes with fiscal position. Tax accounts and rounding.
     - Fulfilment statuses to import, notify customer, fraud data, mark as paid.
     - In developer mode only: products for gift card, tip, duties and custom items, default POS customer.
   - **Payout:** payout journal and accounts per transaction type.
   - **Customer:** receivable account, create company contact.
3. Press **Confirm**. This does the following:
   - checks the scopes
   - creates the pricelist in the shop currency
   - imports Shopify locations, sales channels and return reasons
   - downloads product categories
4. **Locations.** In Marketplaces › Configuration › Locations, for each Shopify location set:
   - Import/Export Stock
   - the Odoo location used for import
   - the Odoo locations whose stock is exported
   - the order warehouse
   - the restock warehouse
5. **Order workflows.** In Marketplaces › Configuration › Marketplace Automation, create the workflows you need. For example:
   - *Prepaid:* confirm, invoice, validate, register payment in the Shopify clearing journal.
   - *COD:* confirm only.
6. **Financial workflow.** On the instance **Workflow** tab, add one line per payment gateway × financial status, pointing to an order workflow and a payment term. Orders whose gateway has no line fail in the queue. New gateways appear automatically the first time they are seen.
7. **Carriers.** Set the **Shopify code** on each delivery method so tracking reaches Shopify with the right carrier name.
8. **Webhooks.**
   - Requires an HTTPS Odoo URL and a database filter (on Odoo.sh this is automatic).
   - On the **Webhook** tab, add the topics and activate them: orders create/updated, customers create, products, returns.
   - Fill the app **secret** so Shopify signatures are verified.
9. **Initial data.** Marketplaces › Overview › Operations, in this order:
   1. Import Listings (products)
   2. Import Inventory (if Shopify is the stock master on day one)
   3. Import Customers
   4. Import Orders from the go-live date
10. **Automatic Jobs tab.** Enable the crons you need: orders, tracking export, inventory export, prices, payouts, returns. Also enable the two bulk crons if you export many products.
11. **Monitor.** Marketplaces › Queues and Logs, and the activities for failed queues.

## 4. Limitations and risks found

Severity: **H** high, **M** medium, **L** low.

### Security

| # | Sev | Finding | Where |
| --- | --- | --- | --- |
| S1 | H | The image URL is public. It names the database in the URL, runs as superuser and serves any listing image by a guessable sequential ID. | `base_marketplace/controllers/main.py:12-29` |
| S2 | H | The dashboard RPC reads instances with `sudo` using a company or instance ID sent by the browser. Any logged-in user can read other companies' sales figures. | `base_marketplace/controllers/dashboard.py` |
| S3 | M | Webhook HMAC is checked only when the app secret is filled. Without it, the random URL is the only protection. | `shopify/controllers/main.py:146-166` |
| S4 | M | Tokens and secrets are stored in plain text, hidden only by group. | `shopify/models/marketplace_instance.py:83-147` |
| S5 | M | Every internal user can open the scope wizard, which can confirm any instance with `sudo`. | `base_marketplace/wizards/marketplace_scope_wizard.py` |
| S6 | M | Record rules exist only for instance, listing and listing item. Queues, logs, payouts, returns and webhooks have none, and product and partner matching is not filtered by company. | `base_marketplace/security/group.xml` |

### Data correctness (code bugs)

| # | Sev | Finding | Where |
| --- | --- | --- | --- |
| D1 | H | Only the **first** shipping line of an order is imported, because the function returns inside its loop. | `shopify/models/sale_order.py:1395` |
| D2 | H | Fulfilment export stops after the first fulfilment order, so orders split across Shopify locations are only partly fulfilled. | `shopify/models/stock.py:713` |
| D3 | H | Partner matching treats "email is empty" as a match. A customer can be attached to an unrelated contact that has no email. | `base_marketplace/models/res_partner.py:29-31` |
| D4 | M | "Fetch webhooks" deactivates webhooks on **all** stores, not just the current one. | `shopify/models/webhook.py:68` |
| D5 | M | The import query filter joins the date and status clauses with no space. This is likely malformed for Shopify search (inference; needs a live test). | `sale_order.py:536-570`, `marketplace_listing.py:435-438` |
| D6 | M | A failed price update, or a "not found" answer, **deletes** the Odoo listing or listing item, so mappings can be lost on temporary errors. | `shopify/models/marketplace_listing.py:2585, 4539-4573` |
| D7 | M | Variant import by ID or webhook may drop variants beyond the first page and then delete their mappings (inference). | `marketplace_listing.py:1269-1339` |
| D8 | M | Order edits made in Shopify after import (lines added, removed or changed) are not applied in Odoo. | `stock.py:727` |
| D9 | M | Which financial-workflow line applies is not deterministic when both a specific status and "Any" exist. | `sale_order.py:1044-1046` |
| D10 | L | Taxes are auto-created by name and rate, with no tax group or tax-report grid. Review them for VAT reporting. | `base_marketplace/models/sale.py:21-146` |

### Reliability and performance

- **Real-time stock and price sync makes HTTP calls inside picking validation.** It sleeps on retries and writes through separate database cursors. A slow Shopify response therefore slows warehouse users, and Shopify can be updated even when the Odoo transaction is rolled back.
- **Webhooks return 200 immediately and process in a background thread.** If the worker restarts, the event is lost and Shopify will not retry. The order cron catches up through its `updated_at` window.
- **There are 44 explicit `cr.commit()` calls.** Partial data can remain after an error.
- **Some HTTP calls have no timeout:** the bundled Shopify client, image downloads and the OAuth exchange. A hung request blocks a worker until Odoo kills it.
- **Large queries may exceed Shopify's single-query cost limit:** `products(first:250)` and `orders(first:250)` with nested data (inference; needs a live store).
- **The Shopify API version `2026-07` is hard-coded.** Shopify supports each version for about 12 months, so the module needs an update roughly every year.
- **The bulk crons are inactive by default.** Large exports stay "queued" until they are enabled.
- **There are no automated tests** in either module.
- **Heavy, unused dependencies.** `numpy`, `scipy`, `PyWavelets` and `imagehash` are required at install, but no code uses them; image de-duplication uses MD5. They make Odoo.sh builds slower and larger.
- **No refresh-token handling.** If Shopify moves this app type to expiring tokens, the connection will stop until the token is regenerated (open question).

### Functional gaps

- **No real B2B orders.** Shopify company and company location are not used on orders; the "company" is taken from the address text. B2B catalogs can be updated but not created, and their prices are kept by hand, not from Odoo pricelists.
- **No product bundles or combined listings.**
- **One price per variant.** There is no compare-at price on product export, and no per-market prices from Odoo pricelists.
- **Product status, handle, SEO fields, cost and "requires shipping" are not exported.** The Shopify "vendor" field is filled with the first supplier's name.
- **Incomplete webhook coverage.** No inventory webhook (Shopify→Odoo stock is daily only). No `orders/cancelled`, `refunds/create`, `fulfillments/*`, `customers/update` or `app/uninstalled` webhooks.
- **Refunds through Register Payment are amount-only.** Line-level refunds with restock exist only in the cancel and return flows.
- **Historical orders may be limited without `read_all_orders`.**
- **Customer and order translations.** Arabic files exist. Some strings built with `_(f"...")` are never translated.

## 5. Suggested development backlog (in priority order)

1. **Security fixes S1, S2, S5 and S6.**
   - Image endpoint: require login, or use signed tokens.
   - Dashboard: company check and no `sudo`.
   - Scope wizard: restrict to managers.
   - Add record rules.
   - These are small and local.
2. **Order correctness D1–D4, D9.**
   - All shipping lines.
   - All fulfilment orders.
   - Partner matching by Shopify customer ID.
   - Per-store webhook fetch.
   - Deterministic workflow line.
3. **Make webhook HMAC mandatory**, and process webhooks through the queue (a stored job) instead of a thread.
4. **Move real-time stock and price pushes out of the user transaction**, into a queued job executed after commit.
5. **Stop deleting mappings on API errors (D6, D7).** Mark the record as an exception instead.
6. **Add an `inventory_levels/update` webhook** for Shopify→Odoo stock, if Shopify can also be a stock master.
7. **Add a test suite**, mocking the Shopify API: order import, taxes, workflows, fulfilment, refunds.
8. **Remove the unused `imagehash`, `numpy`, `scipy` and `PyWavelets` dependencies.** This needs care: removing the vendored package and the manifest entries diverges further from the vendor's code.
9. **B2B orders and per-market prices**, if the business sells B2B or across several markets.

## 6. Rebranding to Qamah Solutions (done in this change)

Every text reference to TeqStars was removed or replaced; `grep -i teq` now finds only image file names.

**Manifests**
- Author and maintainer are now Qamah Solutions, with a new summary.
- TeqStars website, support email, demo URL and Odoo Apps price were removed.
- Versions were bumped so that Odoo.sh updates the changed views: `base_marketplace` 19.0.1.1.3, `shopify` 1.2.10.

**App descriptions (`static/description/index.html`)**
- TeqStars name replaced by Qamah Solutions.
- Removed, because they describe TeqStars' own services or customers:
  - the TeqStars logo block
  - "We set it up with you" booking
  - free install-session offers
  - private sandbox demo and QR code
  - customer testimonials
  - the "TeqStars vs Others" comparison tab with their prices
  - the video tutorials and AI documentation links (TeqStars' YouTube and website)
  - the 60-day support FAQ
  - "Email us" links
  - "Suggested apps" (their other connectors)

**In-app help**
- Links to `docs.teqstars.com` and `teqstars.com` were removed. That covers the instance form, the operations wizard and the onboarding panel "Documentation" button.
- The example shop URL is now `your-store.myshopify.com`.

**Code and translations**
- Logger names are now `Qamah:…`.
- GraphQL operation names are now `qamah…`; Shopify sees these in its API logs.
- Translation file headers were updated, and the example URL in all languages.

**Not changed: images.** Replace these yourself if you want them gone:

| Image | What it contains |
| --- | --- |
| `shopify/static/description/img/teqstars_odoo.svg` | TeqStars logo. No longer shown on the page. |
| `shopify/static/description/img/teqstars_odoo_summer_sale_banner.png` | TeqStars sale banner. Not used by the page. |
| `base_marketplace/static/description/img/teqstars_odoo.svg`, `base_marketplace/static/description/teqstars_main_logo.png` | TeqStars logos. No longer shown on the page. |
| `shopify/static/description/img/screenshots/*-teqstars*.png` (16 files) | Product screenshots, still shown on the Screenshots tab. The file names contain "teqstars", and the images probably show the TeqStars demo store and branding. |
| `shopify/static/description/img/shopify_connector_info_animation.gif`, `marketplace_dashboard.png`, `shopify_quick_onboarding_demo.gif`, `img/tutorials/*.png`, `img/onboarding/*.png` | Marketing and tutorial images; likely to carry TeqStars branding. The first two are still shown. |
| `shopify/static/description/shopify_banner.png`, `icon.png`, `base_marketplace/static/description/base_marketplace_odoo.png`, `icon.png` | App banner and icons shown in the Apps menu; possibly TeqStars-styled. |
| `img/scan_quick_demo.png` | QR code to the TeqStars demo. No longer shown. |
| `img/slideshow/*` (both modules) | Banners for TeqStars' other connectors. No longer shown. |

**Kept on purpose**
- The licence stays `OPL-1`. That is the original author's licence, and a rebrand does not change it. See the note below.
- Technical names were not renamed: `base_marketplace`, `shopify`, the `*.ts` model names and the `_ts` suffixes. Renaming them would break installed databases and future vendor updates.

### Licence note (please read)

The connector is sold under the **Odoo Proprietary License v1.0 (OPL-1)**. That licence:
- allows you to use and modify the code for your own Odoo databases;
- forbids publishing, distributing, sublicensing or selling the code or modified copies.

Two consequences follow:
- **This GitHub repository is public**, so the purchased code is currently published. Consider making the repository private, or removing the connector from the public history.
- Changing the author to Qamah Solutions is fine for internal use. **Reselling or distributing it as a Qamah Solutions product would break the licence.** Please confirm your agreement with the vendor before doing either.
